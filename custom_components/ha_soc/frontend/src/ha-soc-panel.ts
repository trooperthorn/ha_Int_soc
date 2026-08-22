import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HomeAssistant, PanelInfo } from "./types";
import type { HaSocNavigateDetail, SocTab } from "./nav";

import "./views/users-view";
import "./views/audit-view";
import "./views/permissions-view";
import "./views/scanner-view";
import "./views/dashboard-view";

type TabId = SocTab;

const TABS: { id: TabId; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "users", label: "Users & Access" },
  { id: "audit", label: "Audit Log" },
  { id: "permissions", label: "Permissions" },
  { id: "scanner", label: "Scanner" },
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
  `;

  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) narrow?: boolean;
  @property({ attribute: false }) panel?: PanelInfo;

  @state() private _tab: TabId = "dashboard";

  render() {
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
      case "dashboard":
      default:
        return html`<ha-soc-dashboard-view .hass=${this.hass}></ha-soc-dashboard-view>`;
    }
  }
}
