import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { navigateToHaPath, devicesForIntegrationPath } from "../nav";
import {
  ConnectionTestResult,
  DetectionThresholdTable,
  DiscoveredCandidate,
  HaSocSettings,
  SecurityOverview,
  discoverContainerCandidates,
  fetchDetectionThresholds,
  fetchSecurityHealth,
  fetchSettings,
  ProbeRestartResult,
  resetDetectionThresholds,
  restartProbe,
  testPiholeConnection,
  testTechnitiumConnection,
  testUnifiNetworkConnection,
  testUnifiProtectConnection,
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

// Display names for detection rules; an unknown id falls back to the raw id.
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
  // Non-null when fetchSettings failed; the sub-loads degrade independently.
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
      // Fetched separately: a failure only degrades the Integrations Loaded status, never blocks settings.
      try {
        this._security = await fetchSecurityHealth(this.hass);
      } catch {
        this._security = null;
      }
      // Same isolation: the threshold card degrades to a "could not load" line.
      try {
        this._thresholds = await fetchDetectionThresholds(this.hass);
      } catch {
        this._thresholds = null;
      }
    } catch (err: any) {
      // fetchSettings failing must not be swallowed; the page has nothing to show without it.
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  private async _updateThreshold(rule: string, param: string, value: number | boolean) {
    // Sends only the touched field; the server merges and audits a per-field diff.
    await updateSettings(this.hass, {
      detection_thresholds: { [rule]: { [param]: value } },
    } as Partial<HaSocSettings>);
    this._thresholds = await fetchDetectionThresholds(this.hass);
  }

  private async _resetThresholds() {
    this._thresholds = await resetDetectionThresholds(this.hass);
  }

  // Applies immediately like every other tab's toggles; a staged-only change would not survive a tab switch.
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

  // Per-card open/closed persistence. Default OPEN for every card; a missing
  // or unreadable localStorage entry is treated as open, never as closed.
  @state() private _closedCards: Set<string> = new Set();

  private _cardStorageKey(cardKey: string) {
    return `ha-soc-settings-card-open:${cardKey}`;
  }

  private _isOpen(cardKey: string): boolean {
    if (this._closedCards.has(cardKey)) return false;
    try {
      const stored = localStorage.getItem(this._cardStorageKey(cardKey));
      if (stored === "false") {
        this._closedCards.add(cardKey);
        return false;
      }
    } catch {
      // Ignore: private windows, cleared storage, etc. — default stays open.
    }
    return true;
  }

  private _onToggle(cardKey: string, e: Event) {
    const open = (e.target as HTMLDetailsElement).open;
    if (open) {
      this._closedCards.delete(cardKey);
    } else {
      this._closedCards.add(cardKey);
    }
    try {
      localStorage.setItem(this._cardStorageKey(cardKey), String(open));
    } catch {
      // Ignore: nothing to persist to in this environment.
    }
  }

  // Green = configured (host + credential set), and — where a live status
  // object exists — that it is working. For UniFi Network/Protect, Pi-hole,
  // and Technitium there is no live status field this phase, so Green there
  // means only "configured", not "verified reachable".
  private _statusPill(s: HaSocSettings, kind: "unifi_network" | "unifi_protect" | "pihole" | "technitium" | "snmpv3") {
    let host = false;
    let credential = false;
    let color = "var(--status-critical)";
    let label = "not configured";

    if (kind === "unifi_network") {
      host = !!s.unifi_network_host;
      credential = !!s.unifi_network_api_key_set;
    } else if (kind === "unifi_protect") {
      host = !!s.unifi_protect_host;
      credential = !!s.unifi_protect_api_key_set;
    } else if (kind === "pihole") {
      host = !!s.pihole_host;
      credential = !!s.pihole_api_key_set;
    } else if (kind === "technitium") {
      host = !!s.technitium_host;
      credential = !!s.technitium_api_token_set;
    } else if (kind === "snmpv3") {
      host = !!s.snmp_listen_address && !!s.snmp_username;
      credential = !!s.snmp_auth_passphrase_set && !!s.snmp_priv_passphrase_set;
    }

    if (host && credential) {
      color = "var(--status-good)";
      label = "configured";
      if (kind === "snmpv3" && s.snmp_status) {
        if (s.snmp_status.error) {
          color = "var(--status-critical)";
          label = "error";
        } else if (s.snmp_status.running) {
          color = "var(--status-good)";
          label = "running";
        } else {
          color = "var(--status-warning)";
          label = s.snmp_status.enabled ? "waiting" : "disabled";
        }
      }
    } else if (host || credential) {
      color = "var(--status-warning)";
      label = "partially configured";
    }

    return html`<span class="pill" style="background:none;" title=${label}
      ><span class="dot" style="background:${color};"></span>${label}</span
    >`;
  }

  // Test Connection buttons: keyed by service name ("unifi_network",
  // "unifi_protect", "pihole", "technitium"). "pending" while in flight.
  @state() private _connectionTests: Map<string, ConnectionTestResult | "pending"> = new Map();

  private async _testConnection(
    service: "unifi_network" | "unifi_protect" | "pihole" | "technitium"
  ) {
    this._connectionTests = new Map(this._connectionTests).set(service, "pending");
    let result: ConnectionTestResult;
    try {
      if (service === "unifi_network") result = await testUnifiNetworkConnection(this.hass);
      else if (service === "unifi_protect") result = await testUnifiProtectConnection(this.hass);
      else if (service === "pihole") result = await testPiholeConnection(this.hass);
      else result = await testTechnitiumConnection(this.hass);
    } catch (e: any) {
      result = { ok: false, reachable: false, error: e?.message ?? String(e) };
    }
    this._connectionTests = new Map(this._connectionTests).set(service, result);
  }

  private _renderTestConnection(service: "unifi_network" | "unifi_protect" | "pihole" | "technitium") {
    const state = this._connectionTests.get(service);
    const pending = state === "pending";
    let resultHtml = html``;
    if (state && state !== "pending") {
      resultHtml = state.reachable
        ? html`<span style="color:var(--status-good);font-size:12.5px;margin-left:8px;">&#x2713; Reachable</span>`
        : html`<span style="color:var(--status-critical);font-size:12.5px;margin-left:8px;"
            >&#x2717; ${state.error ?? "unreachable"}</span
          >`;
    }
    return html`
      <div class="settings-row">
        <button class="ha-btn" ?disabled=${pending} @click=${() => this._testConnection(service)}>
          ${pending ? "Testing…" : "Test connection"}
        </button>
        ${resultHtml}
      </div>
    `;
  }

  // Restart Probe add-on: single-key Map ("probe") mirroring the Test
  // Connection pending/result pattern above.
  @state() private _probeRestart: Map<string, ProbeRestartResult | "pending"> = new Map();

  private async _restartProbe() {
    this._probeRestart = new Map(this._probeRestart).set("probe", "pending");
    let result: ProbeRestartResult;
    try {
      result = await restartProbe(this.hass);
    } catch (e: any) {
      result = { ok: false, reason: "restart_failed", error: e?.message ?? String(e) };
    }
    this._probeRestart = new Map(this._probeRestart).set("probe", result);
  }

  private _renderProbeRestart() {
    const state = this._probeRestart.get("probe");
    const pending = state === "pending";
    let resultHtml = html``;
    if (state && state !== "pending") {
      resultHtml = state.ok
        ? html`<span style="color:var(--status-good);font-size:12.5px;"
            >&#x2713; Restart requested</span
          >`
        : html`<span style="color:var(--status-critical);font-size:12.5px;"
            >&#x2717; ${state.error ?? state.reason ?? "restart failed"}</span
          >`;
    }
    return html`
      <div class="probe-error-actions">
        <button class="ha-btn" ?disabled=${pending} @click=${() => this._restartProbe()}>
          ${pending ? "Restarting…" : "Restart Probe add-on"}
        </button>
        <span class="muted" style="font-size:12px;"
          >Or restart it yourself: Settings → Add-ons → HA SOC Probe → Restart.</span
        >
        ${resultHtml}
      </div>
    `;
  }

  // Discover candidates: keyed by service name ("pihole", "technitium").
  @state() private _discoverCandidates: Map<string, DiscoveredCandidate[] | "pending"> = new Map();

  private async _discover(service: "pihole" | "technitium") {
    this._discoverCandidates = new Map(this._discoverCandidates).set(service, "pending");
    try {
      const result = await discoverContainerCandidates(this.hass);
      this._discoverCandidates = new Map(this._discoverCandidates).set(service, result[service]);
    } catch {
      this._discoverCandidates = new Map(this._discoverCandidates).set(service, []);
    }
  }

  private _renderDiscover(service: "pihole" | "technitium", hostKey: "pihole_host" | "technitium_host") {
    const state = this._discoverCandidates.get(service);
    const pending = state === "pending";
    let listHtml = html``;
    if (state && state !== "pending") {
      if (state.length === 0) {
        listHtml = html`<div class="muted" style="font-size:11.5px;margin-top:4px;">
          No candidates found — run a network scan from the Scanner tab first, or make sure
          Network Scan is enabled in Settings.
        </div>`;
      } else {
        listHtml = html`
          <div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:6px;">
            ${state.map(
              (c) => html`
                <span
                  class="pill clickable"
                  style="background:none;cursor:pointer;"
                  title="Confidence: ${c.confidence}"
                  @click=${() => this._update(hostKey, c.ip)}
                  >${c.ip} <span class="muted" style="font-size:10.5px;">(${c.confidence})</span></span
                >
              `
            )}
          </div>
        `;
      }
    }
    return html`
      <div style="margin-top:4px;">
        <button class="ha-btn" ?disabled=${pending} @click=${() => this._discover(service)}>
          ${pending ? "Discovering…" : "Discover"}
        </button>
        ${listHtml}
      </div>
    `;
  }

  private _updateSecuritySource(domain: string, enabled: boolean) {
    if (!this._settings) return;
    this._update("security_sources_enabled", { ...this._settings.security_sources_enabled, [domain]: enabled });
  }

  // Secrets are never pre-filled; an untouched empty field never fires @change, so it cannot clear a secret.
  private _renderSecretField(
    label: string,
    key:
      | "nvd_api_key"
      | "github_token"
      | "unifi_network_api_key"
      | "unifi_network_write_api_key"
      | "unifi_protect_api_key"
      | "pihole_api_key"
      | "technitium_api_token"
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
      <details class="card" ?open=${this._isOpen("detection-thresholds")} @toggle=${(e: Event) => this._onToggle("detection-thresholds", e)}>
        <summary class="card-summary"><h3>Detection Thresholds</h3></summary>
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
      </details>
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

      <div class="settings-grid">
        <div class="card" style="grid-column:1/-1;">
          <div class="settings-row" style="border-bottom:none;padding-top:0;">
            <span>
              <h3 style="margin:0;">External Connections</h3>
              <span class="muted" style="display:block;font-size:11.5px;margin-top:4px;"
                >Informational master switch for this phase only — it does not gate any
                integration's runtime behavior yet.
                ${s.external_connections_changed_at
                  ? html`${s.external_connections_enabled ? "Enabled" : "Disabled"}
                    ${formatTimestamp(s.external_connections_changed_at)}`
                  : "never changed"}</span
              >
            </span>
            <label style="display:flex;align-items:center;gap:6px;">
              <span>Enable external connections</span>
              <input
                type="checkbox"
                .checked=${s.external_connections_enabled}
                @change=${(e: Event) =>
                  this._update("external_connections_enabled", (e.target as HTMLInputElement).checked)}
              />
            </label>
          </div>
        </div>

      <details class="card" ?open=${this._isOpen("access-control")} @toggle=${(e: Event) => this._onToggle("access-control", e)}>
        <summary class="card-summary"><h3>Access Control</h3></summary>
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
      </details>

      <details class="card" ?open=${this._isOpen("mfa-policy")} @toggle=${(e: Event) => this._onToggle("mfa-policy", e)}>
        <summary class="card-summary"><h3>MFA Non-Compliance Policy</h3></summary>
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
      </details>

      <details class="card" ?open=${this._isOpen("vulnerability-scanning")} @toggle=${(e: Event) => this._onToggle("vulnerability-scanning", e)}>
        <summary class="card-summary"><h3>Device Vulnerability Scanning</h3></summary>
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
      </details>

      ${this._renderThresholdsCard(s)}

      <details class="card" ?open=${this._isOpen("integration-security-provenance")} @toggle=${(e: Event) => this._onToggle("integration-security-provenance", e)}>
        <summary class="card-summary"><h3>Integration Security (Provenance)</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A <strong>provenance</strong> signal, not a safety verdict — it reflects how much
          is known about where an integration's code comes from, never that the code is safe
          to run. A GitHub token (a fine-grained token with public read access is enough)
          lets the Integration Security tab collect release, signing, maintenance,
          popularity, and archived-status signals for integrations with a known GitHub repo.
        </p>
        ${this._renderSecretField("GitHub API token (optional)", "github_token", !!s.github_token_set)}
      </details>

      <details class="card" ?open=${this._isOpen("unifi-network")} @toggle=${(e: Event) => this._onToggle("unifi-network", e)}>
        <summary class="card-summary"><h3>UniFi Network</h3>${this._statusPill(s, "unifi_network")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a UniFi console over your LAN with a
          <strong>local API key</strong> (UniFi OS → Settings → Control Plane →
          Integrations) to populate the <strong>Network</strong> tab — status, WAN
          throughput, clients, and network devices. Read-only with this key; nothing is
          changed on the controller unless write-back below is enabled with its own key, and
          no data leaves your network.
        </p>
        ${this._renderTestConnection("unifi_network")}
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
            <span class="tag enforced">enforced</span> Allow suggestion write-back
            <span class="muted" style="display:block;font-size:11.5px;"
              >Lets the owner apply a Network Security suggestion (disable a broad ACL rule or
              Firewall Policy) from the panel. Uses the separate write key below, never the
              read key; each apply is audited and read back from the controller. Off by
              default.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.unifi_network_write_enabled}
            @change=${(e: Event) =>
              this._update("unifi_network_write_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
        ${this._renderSecretField(
          "Write-scoped API key (write-back only)",
          "unifi_network_write_api_key",
          !!s.unifi_network_write_api_key_set
        )}
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
      </details>

      <details class="card" ?open=${this._isOpen("unifi-protect")} @toggle=${(e: Event) => this._onToggle("unifi-protect", e)}>
        <summary class="card-summary"><h3>UniFi Protect</h3>${this._statusPill(s, "unifi_protect")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A second local API key for a UniFi Protect console, surfaced as a compact
          camera-status card on the Network tab. Same local-only, read-only posture as
          Network above.
        </p>
        ${this._renderTestConnection("unifi_protect")}
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
      </details>

      <details class="card" ?open=${this._isOpen("pihole")} @toggle=${(e: Event) => this._onToggle("pihole", e)}>
        <summary class="card-summary"><h3>Pi-hole</h3>${this._statusPill(s, "pihole")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a Pi-hole v6 instance over your LAN with its
          <strong>app password</strong> (Pi-hole → Settings → API → App password) to
          populate the <strong>Network Security</strong> tab's DNS section — blocking
          status, query totals, and whether the IoT subnet below has its own Pi-hole
          client group. Read-only; nothing is ever toggled or reassigned on Pi-hole.
        </p>
        ${this._renderTestConnection("pihole")}
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
        ${this._renderDiscover("pihole", "pihole_host")}
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
      </details>

      <details class="card" ?open=${this._isOpen("technitium")} @toggle=${(e: Event) => this._onToggle("technitium", e)}>
        <summary class="card-summary"><h3>Technitium DNS Server</h3>${this._statusPill(s, "technitium")}</summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Connects directly to a Technitium DNS Server instance over your LAN with an
          <strong>API token</strong> (Technitium → Administration → Sessions → Create token) to
          populate the <strong>Network Security</strong> tab's DNS section — blocking
          status, query totals, and the zone/record inventory. Read-only; nothing is ever
          toggled or edited on Technitium. Independent of Pi-hole above — configure either,
          both, or neither.
        </p>
        ${this._renderTestConnection("technitium")}
        <label class="settings-row">
          <span>Technitium host or IP</span>
          <input
            type="text"
            placeholder="e.g. dns.local or 192.168.1.6"
            .value=${s.technitium_host ?? ""}
            @change=${(e: Event) => {
              const v = (e.target as HTMLInputElement).value.trim();
              this._update("technitium_host", v ? v : null);
            }}
          />
        </label>
        ${this._renderDiscover("technitium", "technitium_host")}
        ${this._renderSecretField("API token", "technitium_api_token", !!s.technitium_api_token_set)}
        <label class="settings-row">
          <span>
            Verify TLS certificate
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default — most home Technitium instances are plain HTTP on the LAN.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.technitium_verify_ssl}
            @change=${(e: Event) =>
              this._update("technitium_verify_ssl", (e.target as HTMLInputElement).checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("integration-security-scanner")} @toggle=${(e: Event) => this._onToggle("integration-security-scanner", e)}>
        <summary class="card-summary"><h3>Integration Security Scanner</h3></summary>
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
      </details>

      <details class="card" ?open=${this._isOpen("unused-installs")} @toggle=${(e: Event) => this._onToggle("unused-installs", e)}>
        <summary class="card-summary"><h3>Unused Installs</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Informational hygiene checks for code that is present but that nothing uses:
          custom integrations with no config entry, entries with no entities, HACS
          downloads that never load, and dashboard resources no dashboard references.
        </p>
        <label class="settings-row">
          <span>
            Scan YAML-mode dashboard files
            <span class="muted" style="display:block;font-size:11.5px;"
              >Reads each YAML dashboard through Home Assistant's own loader so cards in
              included files count as used. Only card types are read; nothing is written.
              Off by default because it reads files from the configuration directory. With
              it off, the unused-resource check cannot evaluate while any YAML dashboard
              exists.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.hygiene_scan_yaml_dashboards}
            @change=${(e: Event) =>
              this._update("hygiene_scan_yaml_dashboards", (e.target as HTMLInputElement).checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("dashboard-files")} @toggle=${(e: Event) => this._onToggle("dashboard-files", e)}>
        <summary class="card-summary"><h3>Dashboard Files</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Lets administrators edit the YAML files under the configuration directory's
          <code>dashboards</code> folder from the Assets workspace. No other directory is
          reachable, files can only be modified (never created, renamed, or deleted), and
          every write is backed up and audited with the reason the operator gave.
        </p>
        <label class="settings-row">
          <span>
            Allow editing dashboard YAML files
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default. While it is off the panel shows nothing and the server
              refuses every read and write, whichever access level is set. While it is on,
              who may edit still follows the SOC access level: owner only, or owner and
              administrators.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.dashboard_edit_enabled}
            @change=${(e: Event) =>
              this._update("dashboard_edit_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("device-ssh")} @toggle=${(e: Event) => this._onToggle("device-ssh", e)}>
        <summary class="card-summary"><h3>Device SSH Collection</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Lets HA SOC open read-only SSH sessions to UniFi devices using a keypair the
          controller distributes to every adopted device. Commands come from a fixed
          allowlist in the integration; nothing configures or restarts a device. Used for
          the facts the UniFi API does not expose at any endpoint, such as per-port VLAN
          handling and the inform URL a device actually holds.
        </p>
        <label class="settings-row">
          <span>
            Allow read-only SSH to devices
            <span class="muted" style="display:block;font-size:11.5px;"
              >Off by default. While it is off the server refuses every run. Generate the
              keypair and paste the public key into the controller under Device
              Authentication, SSH Keys, then wait for the devices to re-provision.</span
            >
          </span>
          <input
            type="checkbox"
            .checked=${s.ssh_collection_enabled}
            @change=${(e: Event) =>
              this._update("ssh_collection_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
        <label class="settings-row">
          <span>
            Device SSH username
            <span class="muted" style="display:block;font-size:11.5px;"
              >The site-wide account set in the controller's Device Authentication panel.</span
            >
          </span>
          <input
            type="text"
            .value=${s.ssh_username || ""}
            @change=${(e: Event) =>
              this._update("ssh_username", (e.target as HTMLInputElement).value || null)}
          />
        </label>
      </details>

      <details class="card" ?open=${this._isOpen("audit-log")} @toggle=${(e: Event) => this._onToggle("audit-log", e)}>
        <summary class="card-summary"><h3>Audit Log</h3></summary>
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
      </details>

      <details class="card" ?open=${this._isOpen("siem-syslog")} @toggle=${(e: Event) => this._onToggle("siem-syslog", e)}>
        <summary class="card-summary"><h3>SIEM / Syslog Export</h3></summary>
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

        <div class="syslog-subsection-divider" role="separator"></div>
        <h4 class="syslog-subsection-heading">Syslog Receiver (opposite direction)</h4>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          Receives forwarded logs over UDP instead of sending HA SOC's own audit
          records out — compatible with the "logspout" HA add-on, which forwards
          every Docker container's stdout/stderr on this host. UDP only this
          phase; TCP/TLS receive is a documented follow-up. Point logspout's
          <code>syslog+udp://</code> target at this host and the port below.
        </p>
        <label class="settings-row">
          <span>Enable syslog receiver</span>
          <input
            type="checkbox"
            .checked=${s.syslog_receiver_enabled}
            @change=${(e: Event) =>
              this._update("syslog_receiver_enabled", (e.target as HTMLInputElement).checked)}
          />
        </label>
        <label class="settings-row">
          <span
            >Listen port
            <span class="muted" style="display:block;font-size:11.5px;"
              >Distinct from the exporter's port above and from SNMP's; the HA SOC
              Probe add-on binds this port (host networking).</span
            ></span
          >
          <input
            type="number"
            min="1"
            max="65535"
            .value=${String(s.syslog_receiver_port)}
            @change=${(e: Event) =>
              this._update("syslog_receiver_port", Number((e.target as HTMLInputElement).value))}
          />
        </label>
        ${s.syslog_receiver_status
          ? html`<p class="muted" style="font-size:12px;">
              Status: ${s.syslog_receiver_status.error
                ? `error — ${s.syslog_receiver_status.error}`
                : s.syslog_receiver_status.running
                  ? "listening"
                  : s.syslog_receiver_status.enabled
                    ? "starting"
                    : "disabled"}.
              ${s.syslog_receiver_status.entry_count != null
                ? html`Buffered ${s.syslog_receiver_status.entry_count} entries.`
                : ""}
              ${s.syslog_receiver_status.last_received_at
                ? html`Last received ${s.syslog_receiver_status.last_received_at}.`
                : ""}
            </p>`
          : ""}
      </details>

      <details class="card" ?open=${this._isOpen("security-integrations-health")} @toggle=${(e: Event) => this._onToggle("security-integrations-health", e)}>
        <summary class="card-summary"><h3>Security Integrations Health</h3></summary>
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
      </details>

      <details class="card" ?open=${this._isOpen("host-probe")} @toggle=${(e: Event) => this._onToggle("host-probe", e)}>
        <summary class="card-summary"><h3>Host Probe Add-on</h3></summary>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Real socket-level port visibility on the Home Assistant host needs the optional
          <strong>HA SOC Probe</strong> companion add-on — see the Scanner tab's Host
          Probe card for its current status, and the project README for install steps.
          The add-on's own scan interval is set from its add-on Configuration tab.
        </p>
      </details>

      <details class="card" ?open=${this._isOpen("snmpv3")} @toggle=${(e: Event) => this._onToggle("snmpv3", e)}>
        <summary class="card-summary"><h3>SNMPv3 Telemetry</h3>${this._statusPill(s, "snmpv3")}</summary>
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
        ${s.snmp_status?.error
          ? html`
              <div class="probe-error-notice">
                <div class="probe-error-text">${s.snmp_status.error}</div>
                <p class="probe-error-hint">
                  This usually means the Probe add-on hit a startup or permission problem.
                  Restarting the add-on re-runs its setup; if the error persists after a
                  restart, check the add-on's log (Settings → Add-ons → HA SOC Probe → Log)
                  for the full detail.
                </p>
                ${this._renderProbeRestart()}
              </div>
            `
          : ""}
      </details>
      </div>
    `;
  }
}
