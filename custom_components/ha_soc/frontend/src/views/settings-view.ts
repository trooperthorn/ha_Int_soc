import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { HaSocSettings, fetchSettings, updateSettings } from "../data/ha-soc-ws";

const MB = 1024 * 1024;

@customElement("ha-soc-settings-view")
export class HaSocSettingsView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _saved: HaSocSettings | null = null;
  @state() private _draft: HaSocSettings | null = null;
  @state() private _loading = true;
  @state() private _saving = false;
  @state() private _justSaved = false;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      const settings = await fetchSettings(this.hass);
      this._saved = settings;
      this._draft = { ...settings };
    } finally {
      this._loading = false;
    }
  }

  private _set<K extends keyof HaSocSettings>(key: K, value: HaSocSettings[K]) {
    if (!this._draft) return;
    this._draft = { ...this._draft, [key]: value };
    this._justSaved = false;
  }

  private get _dirty(): boolean {
    if (!this._draft || !this._saved) return false;
    return (Object.keys(this._draft) as (keyof HaSocSettings)[]).some(
      (k) => this._draft![k] !== this._saved![k]
    );
  }

  private async _onSave() {
    if (!this._draft || !this._dirty) return;
    this._saving = true;
    try {
      const saved = await updateSettings(this.hass, this._draft);
      this._saved = saved;
      this._draft = { ...saved };
      this._justSaved = true;
    } finally {
      this._saving = false;
    }
  }

  private _onDiscard() {
    if (!this._saved) return;
    this._draft = { ...this._saved };
    this._justSaved = false;
  }

  render() {
    if (this._loading || !this._draft) return html`<div class="empty">Loading settings…</div>`;
    const d = this._draft;

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
            .value=${d.access_level}
            @change=${(e: Event) =>
              this._set("access_level", (e.target as HTMLSelectElement).value as HaSocSettings["access_level"])}
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
            .value=${d.mfa_policy}
            @change=${(e: Event) =>
              this._set("mfa_policy", (e.target as HTMLSelectElement).value as HaSocSettings["mfa_policy"])}
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
            .value=${String(d.mfa_grace_period_days)}
            ?disabled=${d.mfa_policy !== "auto_deactivate"}
            @change=${(e: Event) =>
              this._set("mfa_grace_period_days", Number((e.target as HTMLInputElement).value))}
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
            .value=${d.nvd_api_key ?? ""}
            @change=${(e: Event) => this._set("nvd_api_key", (e.target as HTMLInputElement).value || null)}
          />
        </label>
        <label class="settings-row">
          <span>Risk-scoring learning period (days)</span>
          <input
            type="number"
            min="1"
            max="90"
            .value=${String(d.risk_learning_period_days)}
            @change=${(e: Event) =>
              this._set("risk_learning_period_days", Number((e.target as HTMLInputElement).value))}
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
            .checked=${d.scanner_enabled}
            @change=${(e: Event) => this._set("scanner_enabled", (e.target as HTMLInputElement).checked)}
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
            .checked=${d.scanner_network_checks_enabled}
            @change=${(e: Event) =>
              this._set("scanner_network_checks_enabled", (e.target as HTMLInputElement).checked)}
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
            .value=${String(d.audit_retention_days)}
            @change=${(e: Event) =>
              this._set("audit_retention_days", Number((e.target as HTMLInputElement).value))}
          />
        </label>
        <label class="settings-row">
          <span>Maximum size (MB)</span>
          <input
            type="number"
            min="1"
            .value=${String(Math.round(d.audit_max_bytes / MB))}
            @change=${(e: Event) =>
              this._set("audit_max_bytes", Math.round(Number((e.target as HTMLInputElement).value) * MB))}
          />
        </label>
      </div>

      <div class="card">
        <h3>Roadmap</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">not yet implemented</span> An optional, HAOS-only
          companion add-on for real socket-level port scanning of the host — the one
          check that genuinely needs a separate container. Everything else once
          considered alongside it (SSH-add-on exposure, HA config-check issues) turned
          out to already be reachable from inside this integration and does not need
          one. See the README for the current design notes. There is no toggle for this
          here because there is nothing yet for a toggle to control.
        </p>
      </div>

      <div class="toolbar" style="position:sticky;bottom:0;background:var(--primary-background-color);padding:12px 0;">
        ${this._justSaved && !this._dirty
          ? html`<span class="muted" style="font-size:12.5px;">Saved.</span>`
          : nothing}
        <span class="spacer"></span>
        <button class="ha-btn" ?disabled=${!this._dirty || this._saving} @click=${this._onDiscard}>
          Discard changes
        </button>
        <button class="ha-btn" ?disabled=${!this._dirty || this._saving} @click=${this._onSave}>
          ${this._saving ? "Saving…" : "Save changes"}
        </button>
      </div>
    `;
  }
}
