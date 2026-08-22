import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { navigateToHaPath, devicesForIntegrationPath } from "../nav";
import { HaSocSettings, SecurityOverview, fetchSettings, fetchSecurityHealth, updateSettings } from "../data/ha-soc-ws";

const MB = 1024 * 1024;

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

@customElement("ha-soc-settings-view")
export class HaSocSettingsView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _settings: HaSocSettings | null = null;
  @state() private _security: SecurityOverview | null = null;
  @state() private _loading = true;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
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
    } finally {
      this._loading = false;
    }
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

  render() {
    if (this._loading || !this._settings) return html`<div class="empty">Loading settings…</div>`;
    const s = this._settings;

    return html`
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
          <span>NVD API key (optional — raises the public rate limit)</span>
          <input
            type="password"
            placeholder="unset"
            .value=${s.nvd_api_key ?? ""}
            @change=${(e: Event) => this._update("nvd_api_key", (e.target as HTMLInputElement).value || null)}
          />
        </label>
        <label class="settings-row">
          <span>Risk-scoring learning period (days)</span>
          <input
            type="number"
            min="1"
            max="90"
            .value=${String(s.risk_learning_period_days)}
            @change=${(e: Event) =>
              this._update("risk_learning_period_days", Number((e.target as HTMLInputElement).value))}
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
          Nothing to configure here; the add-on's own scan interval is set from its own
          add-on Configuration tab.
        </p>
      </div>
    `;
  }
}
