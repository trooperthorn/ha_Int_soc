import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HomeAssistant, PanelInfo } from "./types";
import type { HaSocNavigateDetail, SocTab } from "./nav";
import { AccessInfo, ProbeOverview, fetchAccessInfo, fetchProbeStatus, fetchVersion } from "./data/ha-soc-ws";

import "./views/users-view";
import "./views/audit-view";
import "./views/permissions-view";
import "./views/scanner-view";
import "./views/dashboard-view";
import "./views/network-view";
import "./views/network-security-view";
import "./views/logs-view";
import "./views/peripherals-view";
import "./views/entity-remap-view";
import "./views/integration-security-view";
import "./views/settings-view";

type TabId = SocTab;

// ownerOnly tabs render disabled (with an "only available to owner"
// tooltip) for a non-owner admin — matching the owner-only WS gate on
// their commands, so a non-owner never lands on a tab that would just
// error underneath.
const TABS: { id: TabId; label: string; ownerOnly?: boolean }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "network", label: "Network" },
  { id: "network_security", label: "Network Security" },
  { id: "entity_remap", label: "Entity ReMap" },
  { id: "integration_security", label: "Integration Security" },
  { id: "users", label: "Users & Access" },
  { id: "permissions", label: "Permissions" },
  { id: "audit", label: "Audit Log" },
  { id: "peripherals", label: "Local Peripherals" },
  { id: "scanner", label: "Scanner" },
  { id: "logs", label: "Logs" },
  { id: "settings", label: "Settings", ownerOnly: true },
];

@customElement("ha-soc-panel")
export class HaSocPanel extends LitElement {
  static styles = css`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100vh;
    }
    .tabs {
      display: flex;
      gap: 6px;
      border-top: 1px solid var(--divider-color);
      border-bottom: 1px solid var(--divider-color);
      padding: 9px max(16px, calc((100% - 1400px) / 2));
      background: var(--card-background-color, #fff);
      overflow-x: auto;
      position: sticky;
      top: 0;
      z-index: 5;
      scrollbar-width: thin;
    }
    .tab {
      appearance: none;
      font: inherit;
      background: transparent;
      border: 1px solid transparent;
      border-radius: 9px;
      padding: 8px 11px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 550;
      color: var(--secondary-text-color);
      white-space: nowrap;
    }
    .tab:hover,
    .tab:focus-visible {
      color: var(--primary-text-color);
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.045);
      outline: none;
    }
    .tab.active {
      color: var(--primary-color);
      border-color: rgba(var(--rgb-primary-color, 3, 155, 229), 0.24);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
    }
    .tab.disabled {
      color: var(--disabled-text-color, #b0b0b0);
      cursor: not-allowed;
    }
    .tab.disabled .lock {
      font-size: 11px;
      margin-left: 4px;
      opacity: 0.8;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 17px max(16px, calc((100% - 1400px) / 2)) 14px;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
    }
    .brand-mark {
      width: 34px;
      height: 34px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      background: var(--primary-color);
      color: #fff;
      font-size: 12px;
      font-weight: 750;
      letter-spacing: 0.04em;
    }
    .brand-title {
      display: block;
      font-size: 18px;
      font-weight: 680;
      line-height: 1.15;
    }
    .brand-context {
      display: block;
      margin-top: 2px;
      color: var(--secondary-text-color);
      font-size: 11.5px;
    }
    .customize-btn {
      font-size: 13px;
      font-weight: 500;
      padding: 7px 14px;
      border-radius: 100px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      cursor: pointer;
    }
    .customize-btn.active {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: #fff;
    }
    .denied {
      max-width: 480px;
      margin: 15vh auto 0;
      padding: 32px;
      text-align: center;
      color: var(--primary-text-color);
    }
    .denied .icon {
      font-size: 40px;
    }
    .denied h2 {
      margin: 12px 0 4px;
      font-size: 18px;
    }
    .denied p {
      color: var(--secondary-text-color);
      font-size: 13.5px;
      line-height: 1.5;
    }
    .footer {
      padding: 10px 16px 14px;
      font-size: 11px;
      color: var(--secondary-text-color);
      text-align: center;
    }
    @media (max-width: 600px) {
      .header {
        padding-top: 12px;
      }
      .brand-context {
        display: none;
      }
      .customize-btn {
        padding: 7px 10px;
      }
    }
  `;

  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) narrow?: boolean;
  @property({ attribute: false }) panel?: PanelInfo;

  @state() private _tab: TabId = "dashboard";
  @state() private _access: AccessInfo | null = null;
  @state() private _version: string | null = null;
  @state() private _probe: ProbeOverview | null = null;
  // "Customize" mode — reorder/show/hide the cards on the current view.
  // Not persisted itself (it's a transient editing mode, not a layout
  // choice); each view persists its own resulting order/hidden list via
  // ha_soc/layout/*. Reset on tab change so leaving a tab always exits
  // edit mode rather than carrying it somewhere it wasn't turned on.
  @state() private _customizeMode = false;
  // Set by a ha-soc-navigate event carrying clientFilter (see nav.ts);
  // consumed once by the Network tab's Clients table search box, then
  // cleared so navigating there again without a filter doesn't reapply
  // a stale one.
  @state() private _pendingNetworkFilter: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._loadAccess();
    this._loadFooterInfo();
  }

  private async _loadAccess() {
    try {
      this._access = await fetchAccessInfo(this.hass);
    } catch {
      // A denied WS call (e.g. this admin is already locked out) surfaces
      // as a rejected callWS, not a normal result — treat it the same as
      // an explicit allowed:false rather than leaving the panel loading
      // forever or, worse, rendering tabs that will just 401 underneath.
      this._access = { is_owner: false, access_level: "owner_only", allowed: false };
    }
  }

  private async _loadFooterInfo() {
    // Both plain @websocket_api.require_admin (see websocket_api.py) —
    // reachable even when access_level has this admin locked out of
    // every other ha_soc/* command, so the footer still renders on the
    // "Access restricted" screen too. Best-effort: a failure here just
    // means the footer stays blank, never blocks the rest of the panel.
    try {
      this._version = (await fetchVersion(this.hass)).version;
    } catch {
      this._version = null;
    }
    try {
      this._probe = await fetchProbeStatus(this.hass);
    } catch {
      this._probe = null;
    }
  }

  private _renderFooter() {
    if (!this._version) return html``;
    const probeText =
      this._probe?.installed && this._probe.version ? ` · HA SOC Probe v${this._probe.version}` : "";
    return html`<div class="footer">HA SOC v${this._version}${probeText}</div>`;
  }

  render() {
    if (this._access === null) {
      return html`<div class="header">🛡️ HA SOC</div>`;
    }
    if (!this._access.allowed) {
      return html`
        <div class="denied">
          <div class="icon">🛡️🚫</div>
          <h2>Access restricted</h2>
          <p>
            HA SOC is currently set to <strong>account owner only</strong>. Your account
            is an administrator, but not the account owner, so this panel and its data
            aren't reachable from here.
          </p>
          <p>
            The owner can open this up to every administrator from
            <strong>Settings → Devices &amp; Services → HA SOC → Configure</strong>, or
            from this panel's own Settings tab once they've signed in.
          </p>
        </div>
        ${this._renderFooter()}
      `;
    }
    const activeTabLabel = TABS.find((tab) => tab.id === this._tab)?.label ?? "Dashboard";
    return html`
      <div class="header">
        <div class="brand">
          <span class="brand-mark">SOC</span>
          <span>
            <span class="brand-title">HA SOC</span>
            <span class="brand-context">${activeTabLabel}</span>
          </span>
        </div>
        ${this._tab === "settings"
          ? html``
          : html`
              <button
                type="button"
                class="customize-btn ${this._customizeMode ? "active" : ""}"
                @click=${() => (this._customizeMode = !this._customizeMode)}
              >
                ${this._customizeMode ? "Done" : "Customize"}
              </button>
            `}
      </div>
      <div class="tabs">
        ${TABS.map((t) => {
          const locked = !!t.ownerOnly && !this._access?.is_owner;
          if (locked) {
            return html`
              <button type="button" class="tab disabled" title="Only available to the account owner" disabled>
                ${t.label}<span class="lock">🔒</span>
              </button>
            `;
          }
          return html`
            <button
              type="button"
              class="tab ${this._tab === t.id ? "active" : ""}"
              aria-pressed=${this._tab === t.id ? "true" : "false"}
              @click=${() => this._selectTab(t.id)}
            >
              ${t.label}
            </button>
          `;
        })}
      </div>
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
      ${this._renderFooter()}
    `;
  }

  private _selectTab(id: TabId) {
    this._tab = id;
    this._customizeMode = false;
  }

  private _onNavigate(ev: CustomEvent<HaSocNavigateDetail>) {
    this._tab = ev.detail.tab;
    this._customizeMode = false;
    if (ev.detail.clientFilter) this._pendingNetworkFilter = ev.detail.clientFilter;
  }

  private _renderTab() {
    const cm = this._customizeMode;
    switch (this._tab) {
      case "users":
        return html`<ha-soc-users-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-users-view>`;
      case "audit":
        return html`<ha-soc-audit-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-audit-view>`;
      case "permissions":
        return html`<ha-soc-permissions-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-permissions-view>`;
      case "scanner":
        return html`<ha-soc-scanner-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-scanner-view>`;
      case "logs":
        return html`<ha-soc-logs-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-logs-view>`;
      case "peripherals":
        return html`<ha-soc-peripherals-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-peripherals-view>`;
      case "network":
        return html`<ha-soc-network-view
          .hass=${this.hass}
          .customizeMode=${cm}
          .initialClientFilter=${this._pendingNetworkFilter}
          @client-filter-consumed=${() => (this._pendingNetworkFilter = null)}
        ></ha-soc-network-view>`;
      case "network_security":
        return html`<ha-soc-network-security-view
          .hass=${this.hass}
          .customizeMode=${cm}
        ></ha-soc-network-security-view>`;
      case "entity_remap":
        return html`<ha-soc-entity-remap-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-entity-remap-view>`;
      case "integration_security":
        return html`<ha-soc-integration-security-view
          .hass=${this.hass}
          .customizeMode=${cm}
        ></ha-soc-integration-security-view>`;
      case "settings":
        // Defense in depth: even if a non-owner reached this tab, the
        // owner-only WS commands would reject them — so never render it.
        if (!this._access?.is_owner) {
          return html`<div class="denied"><div class="icon">🔒</div><h2>Owner only</h2>
            <p>The Settings tab is available to the account owner only.</p></div>`;
        }
        return html`<ha-soc-settings-view .hass=${this.hass}></ha-soc-settings-view>`;
      case "dashboard":
      default:
        return html`<ha-soc-dashboard-view .hass=${this.hass} .customizeMode=${cm}></ha-soc-dashboard-view>`;
    }
  }
}
