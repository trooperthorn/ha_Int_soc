import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { navigateToHaPath, devicesForIntegrationPath } from "../nav";
import {
  DetectionThresholdTable,
  HaSocSettings,
  SecurityOverview,
  fetchDetectionThresholds,
  fetchSecurityHealth,
  fetchSettings,
  resetDetectionThresholds,
  updateSettings,
} from "../data/ha-soc-ws";

const MB = 1024 * 1024;
const formatTimestamp = (value: string) => new Date(value).toLocaleString();

const ENTITY_DOMAIN_SOURCE_LABELS: { domain: string; label: string }[] = [
  { domain: "lock", label: "Lock entities (any integration)" },
  { domain: "siren", label: "Siren entities (any integration)" },
  { domain: "valve", label: "Valve entities (any integration)" },
];

const NAMED_INTEGRATION_SOURCE_LABELS: { domain: string; label: string }[] = [
  { domain: "kidde_homesafe", label: "Kidde HomeSafe" },
  { domain: "elkm1", label: "Elk-M1 Security" },
  { domain: "unifiprotect", label: "UniFi Protect" },
  { domain: "keymaster", label: "Keymaster" },
  { domain: "emporia_vue", label: "Emporia Vue" },
];

// Display names for the detection rules whose thresholds render below.
// Any rule id the backend adds later still renders, falling back to the
// raw id, so this list can lag without hiding a control.
const DETECTION_RULE_LABELS: Record<string, string> = {
  brute_force_ip: "Brute force (per source IP)",
  success_after_failures: "Success after failed logins",
  new_ip_login: "Login from a new network",
  off_hours_anomaly: "Off-hours activity burst",
  dormant_revival: "Dormant account revival",
  mass_entity_burst: "Mass entity control burst",
  token_minting_anomaly: "Token minting anomaly",
  disabled_user_activity: "Disabled-user activity",
  privilege_escalation: "Privilege escalation",
};

@customElement("ha-soc-settings-view")
export class HaSocSettingsView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _settings: HaSocSettings | null = null;
  @state() private _security: SecurityOverview | null = null;
  @state() private _thresholds: DetectionThresholdTable | null = null;
  @state() private _loading = true;
  // Non-null when fetchSettings itself failed (the security/threshold
  // sub-loads already degrade independently below). Without this, a
  // failed load left the page reading "Loading settings..." forever,
  // which looks like a stuck page rather than a failure (work plan item
  // 4.12).
  @state() private _error: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      this._settings = await fetchSettings(this.hass);
      // Fetched separately: a failure here (e.g. the security_health
      // websocket command erroring) must never block settings from
      // loading — it only means the Integrations Loaded status/link
      // below degrades to "not installed" until the next successful load,
      // not that the whole page gets stuck on "Loading settings…".
      try {
        this._security = await fetchSecurityHealth(this.hass);
      } catch {
        this._security = null;
      }
      // Same isolation for the threshold table: without it the card
      // degrades to a short "could not load" line, not a stuck page.
      try {
        this._thresholds = await fetchDetectionThresholds(this.hass);
      } catch {
        this._thresholds = null;
      }
    } catch (err: any) {
      // Unlike the two isolated sub-loads above, fetchSettings itself
      // failing must not be swallowed: the whole page has nothing to
      // show without it, and "Loading settings..." forever looks like a
      // stuck page rather than a failure.
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  private async _updateThreshold(rule: string, param: string, value: number | boolean) {
    // Sends only the touched field; the server merges per field and
    // audits a per-field diff (work item 3.0).
    await updateSettings(this.hass, {
      detection_thresholds: { [rule]: { [param]: value } },
    } as Partial<HaSocSettings>);
    this._thresholds = await fetchDetectionThresholds(this.hass);
  }

  private async _resetThresholds() {
    this._thresholds = await resetDetectionThresholds(this.hass);
  }

  // Applies immediately, like every other tab's toggles (permissions-view's
  // require_admin/show_in_sidebar, scanner-view's status selects) — no
  // separate Save step to forget. A control that only stages a change
  // locally can't survive a tab switch (each view remounts fresh from the
  // backend), which read as "my selection didn't take" even though it
  // technically just wasn't saved yet.
  private async _update<K extends keyof HaSocSettings>(key: K, value: HaSocSettings[K]) {
    if (!this._settings) return;
    const previous = this._settings;
    this._settings = { ...this._settings, [key]: value };
    try {
      this._settings = await updateSettings(this.hass, { [key]: value });
    } catch (e) {
      this._settings = previous;
      throw e;
    }
  }

  private _updateSecuritySource(domain: string, enabled: boolean) {
    if (!this._settings) return;
    this._update("security_sources_enabled", { ...this._settings.security_sources_enabled, [domain]: enabled });
  }

  // Secret fields are never pre-filled with their value (the backend only
  // ever sends a mask). An empty, untouched field never fires @change, so
  // it can't accidentally clear a stored secret; typing a value sets it.
  private _renderSecretField(
    label: string,
    key:
      | "nvd_api_key"
      | "github_token"
      | "unifi_network_api_key"
      | "unifi_protect_api_key"
      | "pihole_api_key"
      | "snmp_auth_passphrase"
      | "snmp_priv_passphrase",
    isSet: boolean
  ) {
    return html`
      <label class="settings-row">
        <span>${label}</span>
        <input
          type="password"
          placeholder=${isSet ? "configured — type to replace" : "unset"}
          @change=${(e: Event) => {
            const v = (e.target as HTMLInputElement).value;
            this._update(key, v ? v : null);
          }}
        />
      </label>
    `;
  }

  private _renderIntegrationRow(domain: string, label: string) {
    const s = this._settings!;
    const rows = this._security?.integrations.filter((i) => i.domain === domain) ?? [];
    const installed = rows.some((r) => r.installed);
    const bad = rows.some((r) => r.installed && r.state !== "loaded");
    const entryId = rows.find((r) => r.installed)?.entry_id ?? null;
    const statusText = !installed ? "not installed" : bad ? rows.find((r) => r.state !== "loaded")!.state : "loaded";

    return html`
      <div class="settings-row">
        <span>${label}</span>
        <span
          class="muted ${installed && entryId ? "clickable" : ""}"
          style="font-size:12px;${bad ? "color:var(--error-color,#db4437);" : ""}"
          title=${installed && entryId ? "View in Home Assistant's Devices page" : ""}
          @click=${() => installed && entryId && navigateToHaPath(devicesForIntegrationPath(entryId))}
          >${statusText}</span
        >
        <input
          type="checkbox"
          .checked=${s.security_sources_enabled?.[domain] ?? true}
          @change=${(e: Event) => this._updateSecuritySource(domain, (e.target as HTMLInputElement).checked)}
        />
      </div>
    `;
  }

  private _renderThresholdsCard(s: HaSocSettings) {
    return html`
      <div class="card">
        <h3>Detection Thresholds</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every detection rule's tunable parameters, each accepted only within the
          range shown. The secure defaults are the most sensitive values that do not
          alert on ordinary same-network activity - they miss the fewest attacks, at
          the cost of more alerts. Changes apply from the next analysis pass and are
          audited with a per-field diff.
        </p>
        <label class="settings-row">
          <span>
            Evidence retention (days)
            <span class="muted" style="display:block;font-size:11.5px;"
              >Resolved detections and resolved/dismissed findings older than this are
              pruned; open and acknowledged items never expire.</span
            >
          </span>
          <input
            type="number"
            min="30"
            max="3650"
            .value=${String(s.evidence_retention_days)}
            @change=${(e: Event) =>
              this._update("evidence_retention_days", Number((e.target as HTMLInputElement).value))}
          />
        </label>
        ${!this._thresholds
          ? html`<p class="muted" style="font-size:12.5px;">Could not load the threshold table.</p>`
          : Object.entries(this._thresholds).map(
              ([rule, params]) => html`
                <h4
                  style="margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:0.03em;color:var(--secondary-text-color);"
                >
                  ${DETECTION_RULE_LABELS[rule] ?? rule}
                </h4>
                ${Object.entries(params).map(([param, spec]) =>
                  spec.type === "bool"
                    ? html`
                        <label class="settings-row">
                          <span>
                            ${param}
                            <span class="muted" style="display:block;font-size:11.5px;"
                              >secure default: ${spec.default ? "on" : "off"}</span
                            >
                          </span>
                          <input
                            type="checkbox"
                            .checked=${Boolean(spec.value)}
                            @change=${(e: Event) =>
                              this._updateThreshold(rule, param, (e.target as HTMLInputElement).checked)}
                          />
                        </label>
                      `
                    : html`
                        <label class="settings-row">
                          <span>
                            ${param}
                            <span class="muted" style="display:block;font-size:11.5px;"
                              >${spec.min} to ${spec.max}, secure default ${spec.default}</span
                            >
                          </span>
                          <input
                            type="number"
                            min=${String(spec.min)}
                            max=${String(spec.max)}
                            step=${spec.type === "float" ? "any" : "1"}
                            .value=${String(spec.value)}
                            @change=${(e: Event) =>
                              this._updateThreshold(rule, param, Number((e.target as HTMLInputElement).value))}
                          />
                        </label>
                      `
                )}
              `
            )}
        <div class="toolbar" style="margin-top:12px;">
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._resetThresholds}>Reset to secure defaults</button>
        </div>
      </div>
    `;
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading settings…</div>`;
    if (this._error || !this._settings) {
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Settings</h3>
          <p style="font-size:13px;">${this._error ?? "The server returned no settings."}</p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;
    }
    const s = this._settings;

    return html`
      ${!s.github_token_set
        ? html`
            <div
              style="background:#fdf6d8;color:#6b5300;border:1px solid #e8d071;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13.5px;line-height:1.5;"
            >
              <strong>No GitHub API key configured.</strong> The Integration Security tab
              can still classify every integration and run local checks, but the
              GitHub-derived provenance signals — release vs. branch, identity assurance,
              maintenance recency, popularity, and archived status — stay
              <em>“not collected”</em> until a token is set below. A token also raises
              GitHub's rate limit from 60 to 5,000 requests/hour.
            </div>
          `
        : ""}

      <div class="card">
        <h3>Access Control</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Checked server-side on every
          <code>ha_soc/*</code> command, not just on whether the panel is visible in the
          sidebar — a locked-out admin still sees the SOC panel entry (Home Assistant's
          sidebar has no finer-grained hook than admin/non-admin) but every request it
          makes is rejected until this is opened up.
        </p>
        <label class="settings-row">
          <span>Who can use this panel</span>
          <select
            .value=${s.access_level}
            @change=${(e: Event) =>
              this._update("access_level", (e.target as HTMLSelectElement).value as HaSocSettings["access_level"])}
          >
            <option value="owner_only">Account owner only</option>
            <option value="owner_and_admins">Owner and all administrators</option>
          </select>
        </label>
      </div>

      <div class="card">
        <h3>MFA Non-Compliance Policy</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant core has no hook to <em>require</em> a second factor at login —
          this can only ever <span class="tag cosmetic">audit</span> that gap, or take the
          one real action core does expose:
          <span class="tag enforced">enforced</span> deactivating an admin account that
          stays out of compliance past the grace period below. The account owner is never
          evaluated or deactivated by this policy.
        </p>
        <label class="settings-row">
          <span>Policy for admins without MFA enabled</span>
          <select
            .value=${s.mfa_policy}
            @change=${(e: Event) =>
              this._update("mfa_policy", (e.target as HTMLSelectElement).value as HaSocSettings["mfa_policy"])}
          >
            <option value="audit_only">Audit only — flag via Repairs, never act</option>
            <option value="auto_deactivate">Deactivate after grace period</option>
          </select>
        </label>
        <label class="settings-row">
          <span>Grace period (days)</span>
          <input
            type="number"
            min="1"
            max="365"
            .value=${String(s.mfa_grace_period_days)}
            ?disabled=${s.mfa_policy !== "auto_deactivate"}
            @change=${(e: Event) =>
              this._update("mfa_grace_period_days", Number((e.target as HTMLInputElement).value))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Device Vulnerability Scanning</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">best-effort</span> CVE correlation is a heuristic
          vendor/model match against NVD, not a confirmed exploit — absence of a match is
          not evidence a device is secure.
        </p>
        <label class="settings-row">
          <span>
            Look up device CVEs against NIST's NVD
            <span class="muted" style="display:block;font-size:11.5px;"
              >While on, device manufacturer and model strings are sent to
              NIST's NVD (the U.S. National Vulnerability Database) to find
              candidate CVEs. Turning this off stops that lookup entirely.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.nvd_lookups_enabled}
            @change=${(e: Event) =>
              this._update("nvd_lookups_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
        ${this._renderSecretField(
          "NVD API key (optional — raises the public rate limit)",
          "nvd_api_key",
          !!s.nvd_api_key_set
        )}
      </div>

      ${this._renderThresholdsCard(s)}

      <div class="card">
        <h3>Integration Security (Provenance)</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A <strong>provenance</strong> signal, not a safety verdict — it reflects how much
          is known about where an integration's code comes from, never that the code is safe
          to run. A GitHub token (a fine-grained token with public read access is enough)
          lets the Integration Security tab collect release, signing, maintenance,
          popularity, and archived-status signals for integrations with a known GitHub repo.
        </p>
        ${this._renderSecretField("GitHub API token (optional)", "github_token", !!s.github_token_set)}
      </div>

      <div class="card">
        <h3>UniFi Network</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a UniFi console over your LAN with a
          <strong>local API key</strong> (UniFi OS → Settings → Control Plane →
          Integrations) to populate the <strong>Network</strong> tab — status, WAN
          throughput, clients, and network devices. Read-only; nothing is ever changed
          on the controller, and no data leaves your network.
        </p>
        <label class="settings-row">
          <span>Controller host or IP</span>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1"
            .value=${s.unifi_network_host ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("unifi_network_host", v ? v : null);
            }}
          />
        </label>
        ${this._renderSecretField("Local API key", "unifi_network_api_key", !!s.unifi_network_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — UniFi consoles ship a self-signed certificate.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.unifi_network_verify_ssl}
            @change=${(e: Event) =>
              this._update("unifi_network_verify_ssl", (e.target as HTMLInputElement).checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>UniFi Protect</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A second local API key for a UniFi Protect console, surfaced as a compact
          camera-status card on the Network tab. Same local-only, read-only posture as
          Network above.
        </p>
        <label class="settings-row">
          <span>Protect host or IP</span>
          <input
            type="text"
            placeholder="e.g. 192.168.1.1"
            .value=${s.unifi_protect_host ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("unifi_protect_host", v ? v : null);
            }}
          />
        </label>
        ${this._renderSecretField("Local API key", "unifi_protect_api_key", !!s.unifi_protect_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — UniFi consoles ship a self-signed certificate.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.unifi_protect_verify_ssl}
            @change=${(e: Event) =>
              this._update("unifi_protect_verify_ssl", (e.target as HTMLInputElement).checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>Pi-hole</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a Pi-hole v6 instance over your LAN with its
          <strong>app password</strong> (Pi-hole → Settings → API → App password) to
          populate the <strong>Network Security</strong> tab's DNS section — blocking
          status, query totals, and whether the IoT subnet below has its own Pi-hole
          client group. Read-only; nothing is ever toggled or reassigned on Pi-hole.
        </p>
        <label class="settings-row">
          <span>Pi-hole host or IP</span>
          <input
            type="text"
            placeholder="e.g. pi.hole or 192.168.1.5"
            .value=${s.pihole_host ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("pihole_host", v ? v : null);
            }}
          />
        </label>
        ${this._renderSecretField("App password", "pihole_api_key", !!s.pihole_api_key_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — most home Pi-hole instances are plain HTTP on the LAN.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.pihole_verify_ssl}
            @change=${(e: Event) => this._update("pihole_verify_ssl", (e.target as HTMLInputElement).checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            IoT network CIDR
            <span class="muted" style="display:block;font-size:11.5px;"
              >The subnet whose DNS your UniFi gateway forwards to Pi-hole, e.g.
              192.168.50.0/24. Used only to check whether it has a dedicated Pi-hole
              client group — never to configure DNS itself.</span
            >
          </span>
          <input
            type="text"
            placeholder="e.g. 192.168.50.0/24"
            .value=${s.pihole_iot_cidr ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("pihole_iot_cidr", v ? v : null);
            }}
          />
        </label>
      </div>

      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static analysis of every installed integration's source, run on the weekly
          sweep below or on demand from the Scanner tab.
        </p>
        <label class="settings-row">
          <span>Run the weekly scan automatically</span>
          <input
            type="checkbox"
            .checked=${s.scanner_enabled}
            @change=${(e: Event) => this._update("scanner_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            Include network-reachability checks
            <span class="muted" style="display:block;font-size:11.5px;"
              >Best-effort connectivity probes against configured device hosts — off by
              default since it makes outbound requests.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.scanner_network_checks_enabled}
            @change=${(e: Event) =>
              this._update("scanner_network_checks_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
      </div>

      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag enforced">enforced</span> Hash-chained JSONL, rotated on
          whichever of these two limits is hit first — see the Audit Log tab's
          <code>Verify chain</code> action.
        </p>
        <label class="settings-row">
          <span>Retention (days)</span>
          <input
            type="number"
            min="7"
            max="3650"
            .value=${String(s.audit_retention_days)}
            @change=${(e: Event) =>
              this._update("audit_retention_days", Number((e.target as HTMLInputElement).value))}
          />
        </label>
        <label class="settings-row">
          <span>Maximum size (MB)</span>
          <input
            type="number"
            min="1"
            .value=${String(Math.round(s.audit_max_bytes / MB))}
            @change=${(e: Event) =>
              this._update("audit_max_bytes", Math.round(Number((e.target as HTMLInputElement).value) * MB))}
          />
        </label>
      </div>

      <div class="card">
        <h3>SIEM / Syslog Export</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Exports finalized hash-chained audit records as RFC 5424 with JSON or
          CEF 0, or as bare canonical JSON for collectors that explicitly require
          it. TCP and TLS retain RFC 6587 octet framing. This stays disabled until
          a destination is configured.
        </p>
        <label class="settings-row">
          <span>
            Payload format
            <span class="muted" style="display:block;font-size:11.5px;"
              >Independent of the UDP, TCP, or TLS transport below.</span
            >
          </span>
          <select
            .value=${s.syslog_format}
            @change=${(e: Event) =>
              this._update(
                "syslog_format",
                (e.target as HTMLSelectElement).value as HaSocSettings["syslog_format"]
              )}
          >
            <option value="rfc5424_json">RFC 5424 + Raw audit JSON (default)</option>
            <option value="cef">RFC 5424 + CEF 0</option>
            <option value="raw_json">Bare Raw JSON (collector compatibility)</option>
          </select>
        </label>
        ${s.syslog_format === "raw_json"
          ? html`<p class="muted" style="font-size:12px;color:var(--warning-color,#ffa600);">
              Bare Raw JSON has no RFC 5424 envelope. Use it only when the receiver
              explicitly requires JSON-only input; RFC 5424 + JSON remains the
              standards-based default.
            </p>`
          : ""}
        <label class="settings-row">
          <span>Transport</span>
          <select
            .value=${s.syslog_transport}
            @change=${(e: Event) =>
              this._update(
                "syslog_transport",
                (e.target as HTMLSelectElement).value as HaSocSettings["syslog_transport"]
              )}
          >
            <option value="disabled">Disabled</option>
            <option value="udp">UDP (unencrypted fallback)</option>
            <option value="tcp">TCP (unencrypted fallback)</option>
            <option value="tls">TLS over TCP</option>
          </select>
        </label>
        ${s.syslog_transport === "udp" || s.syslog_transport === "tcp"
          ? html`<p class="muted" style="font-size:12px;color:var(--warning-color,#ffa600);">
              UDP/TCP Syslog is unencrypted. Restrict it to a dedicated management
              VLAN or VPN path and migrate to TLS when certificates are assigned.
            </p>`
          : ""}
        <label class="settings-row">
          <span>SIEM host or IP</span>
          <input
            type="text"
            placeholder="e.g. sem.example.lan"
            .value=${s.syslog_host ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("syslog_host", v ? v : null);
            }}
          />
        </label>
        <label class="settings-row">
          <span>Port <span class="muted" style="display:block;font-size:11.5px;">Common: 514 UDP/TCP, 6514 TLS</span></span>
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(s.syslog_port)}
            @change=${(e: Event) => this._update("syslog_port", Number((e.target as HTMLInputElement).value))}
          />
        </label>
        <label class="settings-row">
          <span>Facility</span>
          <select
            .value=${String(s.syslog_facility)}
            @change=${(e: Event) => this._update("syslog_facility", Number((e.target as HTMLSelectElement).value))}
          >
            ${Array.from({ length: 8 }, (_, i) => html`<option value=${String(16 + i)}>local${i}</option>`)}
          </select>
        </label>
        ${s.syslog_transport === "tls"
          ? html`<label class="settings-row">
              <span>
                Verify SIEM TLS certificate
                <span class="muted" style="display:block;font-size:11.5px;"
                  >On by default. Turn off only while the receiver uses a self-signed
                  certificate, then re-enable after certificate assignment.</span
                >
              </span>
              <input
                type="checkbox"
                .checked=${s.syslog_tls_verify}
                @change=${(e: Event) =>
                  this._update("syslog_tls_verify", (e.target as HTMLInputElement).checked)}
              />
            </label>`
          : ""}
        ${s.syslog_status
          ? html`<p class="muted" style="font-size:12px;">
              Status: ${s.syslog_status.last_error
                ? `error — ${s.syslog_status.last_error}`
                : s.syslog_status.connected
                  ? "connected"
                  : s.syslog_status.enabled
                    ? "waiting for first delivery"
                    : "disabled"}.
              Sent ${s.syslog_status.sent}; queued ${s.syslog_status.queued}; dropped
              ${s.syslog_status.dropped}. Format ${s.syslog_status.format}.
            </p>`
          : ""}
      </div>

      <div class="card">
        <h3>Security Integrations Health</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          What shows up in the always-present Dashboard security card. A source stays on
          by default — a device or integration you haven't installed just reports "not
          installed" rather than being hidden, and turning a toggle off here only affects
          this dashboard section, nothing else.
        </p>
        ${ENTITY_DOMAIN_SOURCE_LABELS.map(
          ({ domain, label }) => html`
            <label class="settings-row">
              <span>${label}</span>
              <input
                type="checkbox"
                .checked=${s.security_sources_enabled?.[domain] ?? true}
                @change=${(e: Event) =>
                  this._updateSecuritySource(domain, (e.target as HTMLInputElement).checked)}
              />
            </label>
          `
        )}
        <h4 style="margin:16px 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:0.03em;color:var(--secondary-text-color);">
          Integrations Loaded
        </h4>
        ${NAMED_INTEGRATION_SOURCE_LABELS.map(({ domain, label }) => this._renderIntegrationRow(domain, label))}
      </div>

      <div class="card">
        <h3>Host Probe Add-on</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Real socket-level port visibility on the Home Assistant host needs the optional
          <strong>HA SOC Probe</strong> companion add-on — see the Scanner tab's Host
          Probe card for its current status, and the project README for install steps.
          The add-on's own scan interval is set from its add-on Configuration tab.
        </p>
      </div>

      <div class="card">
        <h3>SNMPv3 Telemetry</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Optional read-only Net-SNMP service in the HA SOC Probe for monitoring and
          observability tools. Only SNMPv3 USM <strong>AuthPriv</strong> is supported,
          using SHA-256 authentication and AES-128 privacy. SNMPv1/v2c, write access,
          and wildcard listeners are not available.
        </p>
        <label class="settings-row">
          <span>
            Listener IP
            <span class="muted" style="display:block;font-size:11.5px;"
              >An exact Home Assistant address, such as 192.168.30.3; never 0.0.0.0.</span
            >
          </span>
          <input
            type="text"
            placeholder="e.g. 192.168.30.3"
            .value=${s.snmp_listen_address ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("snmp_listen_address", v ? v : null);
            }}
          />
        </label>
        <label class="settings-row">
          <span>Port</span>
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(s.snmp_port)}
            @change=${(e: Event) => this._update("snmp_port", Number((e.target as HTMLInputElement).value))}
          />
        </label>
        <label class="settings-row">
          <span>Security name</span>
          <input
            type="text"
            placeholder="e.g. solarwinds_sem"
            .value=${s.snmp_username ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("snmp_username", v ? v : null);
            }}
          />
        </label>
        ${this._renderSecretField(
          "Authentication passphrase (20+ characters)",
          "snmp_auth_passphrase",
          !!s.snmp_auth_passphrase_set
        )}
        ${this._renderSecretField(
          "Privacy passphrase (20+ characters, different)",
          "snmp_priv_passphrase",
          !!s.snmp_priv_passphrase_set
        )}
        <p class="muted" style="font-size:11.5px;">
          Accepted credential characters: letters, numbers, and
          <code>._~!@$%^&amp;*+=:,-</code>. Restrict UDP/161 to your management or
          monitoring VLAN at the network firewall.
        </p>
        <label class="settings-row">
          <span>
            Enable SNMPv3
            <span class="muted" style="display:block;font-size:11.5px;"
              >The Probe must be installed and running. Complete every field above first.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.snmp_enabled}
            @change=${(e: Event) => this._update("snmp_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
        ${s.snmp_status
          ? html`<p class="muted" style="font-size:12px;">
              Probe status: ${s.snmp_status.error
                ? `error — ${s.snmp_status.error}`
                : s.snmp_status.running
                  ? `running on ${s.snmp_status.listen_address}:${s.snmp_status.port}`
                  : s.snmp_status.enabled
                    ? "enabled, waiting for snmpd"
                    : "disabled"}.
              ${s.snmp_status.reported_at ? ` Last report ${formatTimestamp(s.snmp_status.reported_at)}.` : ""}
            </p>`
          : html`<p class="muted" style="font-size:12px;">No SNMP status has been reported by the Probe yet.</p>`}
      </div>
    `;
  }
}
