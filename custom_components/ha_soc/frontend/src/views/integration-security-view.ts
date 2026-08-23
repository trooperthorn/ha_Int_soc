import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  IntegrationSecurityOverview,
  IntegrationSecurityRow,
  IntegrationTier,
  fetchIntegrationSecurity,
  refreshIntegrationSecurity,
} from "../data/ha-soc-ws";

const TIER_LABEL: Record<IntegrationTier, string> = {
  core: "Core",
  hacs: "HACS",
  custom: "Custom",
};
// Provenance tone: core is strongest-known, custom (unmanaged) weakest-known.
const TIER_TONE: Record<IntegrationTier, string> = {
  core: "good",
  hacs: "medium",
  custom: "high",
};

const FLAG_LABEL: Record<string, string> = {
  custom_repo: "Custom repo",
  custom_source_list: "Custom source-list",
};

const PAGE_SIZE = 25;

@customElement("ha-soc-integration-security-view")
export class HaSocIntegrationSecurityView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _overview: IntegrationSecurityOverview | null = null;
  @state() private _loading = true;
  @state() private _refreshing = false;
  @state() private _search = "";
  @state() private _tierFilter = "all";
  @state() private _limit = PAGE_SIZE;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      this._overview = await fetchIntegrationSecurity(this.hass);
    } finally {
      this._loading = false;
    }
  }

  private async _onRefresh() {
    this._refreshing = true;
    try {
      await refreshIntegrationSecurity(this.hass);
      await this._load();
    } finally {
      this._refreshing = false;
    }
  }

  private _filtered(): IntegrationSecurityRow[] {
    const rows = this._overview?.integrations ?? [];
    const q = this._search.trim().toLowerCase();
    return rows
      .filter((r) => this._tierFilter === "all" || r.tier === this._tierFilter)
      .filter((r) => !q || r.name.toLowerCase().includes(q) || r.domain.toLowerCase().includes(q))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  render() {
    if (this._loading || !this._overview) return html`<div class="empty">Loading integrations…</div>`;
    const o = this._overview;
    const filtered = this._filtered();
    const shown = filtered.slice(0, this._limit);

    return html`
      <div class="card">
        <h3>Integration Security</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">provenance, not safety</span> This measures how much is
          known about where each integration's code came from and how it's maintained — it
          is <strong>not</strong> a verdict that the code is safe to run. Home Assistant
          runs integrations in-process with no sandbox; a high-provenance integration can
          still do anything a low-provenance one can.
        </p>

        <div class="toolbar" style="margin-top:12px;">
          <div class="pill" style="--tone-unused:0">
            <span class="dot" style="background:var(--success-color,#43a047);"></span>
            Core ${o.tier_counts.core}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--warning-color,#ffa600);"></span>
            HACS ${o.tier_counts.hacs}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--error-color,#db4437);"></span>
            Custom ${o.tier_counts.custom}
          </div>
          <span class="spacer"></span>
          <button class="ha-btn" ?disabled=${this._refreshing || !o.github_configured} @click=${this._onRefresh}>
            ${this._refreshing ? "Refreshing…" : "Refresh GitHub signals"}
          </button>
        </div>

        ${!o.github_configured
          ? html`<p class="muted" style="font-size:12px;margin:0 0 4px;">
              GitHub-derived signals are <strong>not collected</strong> — set a GitHub token
              in the owner-only Settings tab to enable them.
            </p>`
          : o.refreshed_at
            ? html`<p class="muted" style="font-size:12px;margin:0 0 4px;">
                GitHub signals last refreshed ${new Date(o.refreshed_at).toLocaleString()}.
              </p>`
            : nothing}
        ${o.hacs_installed && !o.hacs_source_introspectable
          ? html`<p class="muted" style="font-size:12px;margin:0;">
              HACS is installed but its per-repository source (default store vs. custom
              repo) isn't readable here, so HACS-managed content is shown as
              <em>Custom</em> and source flags are unverified.
            </p>`
          : nothing}
      </div>

      <div class="card">
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search integrations…"
            .value=${this._search}
            @input=${(e: Event) => {
              this._search = (e.target as HTMLInputElement).value;
              this._limit = PAGE_SIZE;
            }}
            style="flex:1 1 220px;"
          />
          <select
            .value=${this._tierFilter}
            @change=${(e: Event) => {
              this._tierFilter = (e.target as HTMLSelectElement).value;
              this._limit = PAGE_SIZE;
            }}
          >
            <option value="all">All tiers</option>
            <option value="core">Core</option>
            <option value="hacs">HACS</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        ${!filtered.length
          ? html`<div class="empty">No integrations match.</div>`
          : html`
              <div style="overflow-x:auto;">
                <table>
                  <thead>
                    <tr>
                      <th>Integration</th>
                      <th>Source</th>
                      <th>Quality</th>
                      <th>License</th>
                      <th>Scanner</th>
                      <th>Signed</th>
                      <th>Release</th>
                      <th>Stars</th>
                      <th>Last push</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${shown.map((r) => this._renderRow(r))}
                  </tbody>
                </table>
              </div>
              ${filtered.length > this._limit
                ? html`
                    <div class="toolbar" style="justify-content:center;margin-top:12px;">
                      <button class="ha-btn" @click=${() => (this._limit += PAGE_SIZE)}>
                        Show more (${filtered.length - this._limit} more)
                      </button>
                    </div>
                  `
                : nothing}
              <p class="muted" style="font-size:11.5px;margin-top:8px;">
                Showing ${Math.min(this._limit, filtered.length)} of ${filtered.length}.
              </p>
            `}
      </div>
    `;
  }

  private _notCollected() {
    return html`<span class="muted" title="No GitHub token, or no repo URL discovered">—</span>`;
  }

  private _renderRow(r: IntegrationSecurityRow) {
    const g = r.github;
    return html`
      <tr>
        <td>
          <div style="font-weight:600;">${r.name}</div>
          <div class="muted" style="font-size:11.5px;">
            ${r.domain}${r.version ? html` · v${r.version}` : ""}
          </div>
          ${r.flags.length
            ? html`<div class="chips" style="margin-top:3px;">
                ${r.flags.map(
                  (f) => html`<span class="pill high"><span class="dot"></span>${FLAG_LABEL[f] ?? f}</span>`
                )}
              </div>`
            : nothing}
        </td>
        <td>
          <span class="pill ${TIER_TONE[r.tier]}"><span class="dot"></span>${TIER_LABEL[r.tier]}</span>
        </td>
        <td class="muted">${r.quality_scale ?? "—"}</td>
        <td>
          ${r.license_present === null
            ? html`<span class="muted">—</span>`
            : r.license_present
              ? html`<span class="muted" title="License file present">yes</span>`
              : html`<span class="pill medium" title="No license file found"><span class="dot"></span>none</span>`}
        </td>
        <td>
          ${r.scanner_findings > 0
            ? html`<span class="pill high"><span class="dot"></span>${r.scanner_findings}</span>`
            : html`<span class="muted">0</span>`}
        </td>
        <td>
          ${!g
            ? this._notCollected()
            : g.commit_verified === null
              ? html`<span class="muted">?</span>`
              : g.commit_verified
                ? html`<span class="pill good" title="Default-branch head commit is signed/verified"
                    ><span class="dot"></span>signed</span
                  >`
                : html`<span class="muted" title="No verified signature on the head commit">unsigned</span>`}
        </td>
        <td>
          ${!g
            ? this._notCollected()
            : g.archived
              ? html`<span class="pill high" title="Repository is archived"><span class="dot"></span>archived</span>`
              : g.has_release === null
                ? html`<span class="muted">?</span>`
                : g.has_release
                  ? html`<span class="muted" title=${g.latest_release_tag ?? ""}>tagged</span>`
                  : html`<span class="pill medium" title="No published release — installs branch HEAD"
                      ><span class="dot"></span>branch</span
                    >`}
        </td>
        <td class="muted">${!g ? this._notCollected() : (g.stars ?? "—")}</td>
        <td class="muted" style="font-size:11.5px;">
          ${!g ? this._notCollected() : g.pushed_at ? new Date(g.pushed_at).toLocaleDateString() : "—"}
        </td>
      </tr>
    `;
  }
}
