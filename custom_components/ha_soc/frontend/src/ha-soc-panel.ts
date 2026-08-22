import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HomeAssistant, PanelInfo } from "./types";
import type { HaSocNavigateDetail, SocTab } from "./nav";
import { AccessInfo, fetchAccessInfo } from "./data/ha-soc-ws";

import "./views/users-view";
import "./views/audit-view";
import "./views/permissions-view";
import "./views/scanner-view";
import "./views/dashboard-view";
import "./views/logs-view";
import "./views/peripherals-view";
import "./views/entity-remap-view";
import "./views/settings-view";

type TabId = SocTab;

const TABS: { id: TabId; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "entity_remap", label: "Entity ReMap" },
  { id: "users", label: "Users & Access" },
  { id: "permissions", label: "Permissions" },
  { id: "audit", label: "Audit Log" },
  { id: "peripherals", label: "Local Peripherals" },
  { id: "scanner", label: "Scanner" },
  { id: "logs", label: "Logs" },
  { id: "settings", label: "Settings" },
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
      gap: 4px;
      border-bottom: 1px solid var(--divider-color);
      padding: 0 16px;
      background: var(--card-background-color, #fff);
      overflow-x: auto;
    }
    .tab {
      padding: 14px 16px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: var(--secondary-text-color);
      border-bottom: 2px solid transparent;
      white-space: nowrap;
    }
    .tab.active {
      color: var(--primary-color);
      border-bottom-color: var(--primary-color);
    }
    .header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px 0;
      font-size: 20px;
      font-weight: 500;
      color: var(--primary-text-color);
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
  `;

  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) narrow?: boolean;
  @property({ attribute: false }) panel?: PanelInfo;

  @state() private _tab: TabId = "dashboard";
  @state() private _access: AccessInfo | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._loadAccess();
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
      `;
    }
    return html`
      <div class="header">🛡️ HA SOC</div>
      <div class="tabs">
        ${TABS.map(
          (t) => html`
            <div class="tab ${this._tab === t.id ? "active" : ""}" @click=${() => (this._tab = t.id)}>
              ${t.label}
            </div>
          `
        )}
      </div>
      <div @ha-soc-navigate=${this._onNavigate}>${this._renderTab()}</div>
    `;
  }

  private _onNavigate(ev: CustomEvent<HaSocNavigateDetail>) {
    this._tab = ev.detail.tab;
  }

  private _renderTab() {
    switch (this._tab) {
      case "users":
        return html`<ha-soc-users-view .hass=${this.hass}></ha-soc-users-view>`;
      case "audit":
        return html`<ha-soc-audit-view .hass=${this.hass}></ha-soc-audit-view>`;
      case "permissions":
        return html`<ha-soc-permissions-view .hass=${this.hass}></ha-soc-permissions-view>`;
      case "scanner":
        return html`<ha-soc-scanner-view .hass=${this.hass}></ha-soc-scanner-view>`;
      case "logs":
        return html`<ha-soc-logs-view .hass=${this.hass}></ha-soc-logs-view>`;
      case "peripherals":
        return html`<ha-soc-peripherals-view .hass=${this.hass}></ha-soc-peripherals-view>`;
      case "entity_remap":
        return html`<ha-soc-entity-remap-view .hass=${this.hass}></ha-soc-entity-remap-view>`;
      case "settings":
        return html`<ha-soc-settings-view .hass=${this.hass}></ha-soc-settings-view>`;
      case "dashboard":
      default:
        return html`<ha-soc-dashboard-view .hass=${this.hass}></ha-soc-dashboard-view>`;
    }
  }
}
