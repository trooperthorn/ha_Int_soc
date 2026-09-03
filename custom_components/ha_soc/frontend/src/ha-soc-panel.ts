import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { HomeAssistant, PanelInfo } from "./types";
import {
  SOC_WORKSPACES,
  workspaceForTab,
  type HaSocNavigateDetail,
  type SocTab,
} from "./nav";
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

@customElement("ha-soc-panel")
export class HaSocPanel extends LitElement {
  static styles = css`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100vh;
      container-type: inline-size;
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
    .subtabs {
      display: flex;
      gap: 4px;
      padding: 7px max(16px, calc((100% - 1400px) / 2));
      overflow-x: auto;
      background: var(--primary-background-color);
      border-bottom: 1px solid var(--divider-color);
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
    .subtab {
      appearance: none;
      border: 0;
      border-radius: 7px;
      padding: 7px 10px;
      background: transparent;
      color: var(--secondary-text-color);
      cursor: pointer;
      font: inherit;
      font-size: 12.5px;
      white-space: nowrap;
    }
    .subtab:hover,
    .subtab:focus-visible {
      color: var(--primary-text-color);
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.045);
    }
    .subtab.active {
      color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.09);
      font-weight: 600;
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
    .access-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--success-color, #0f9d58);
      font-size: 12px;
      white-space: nowrap;
    }
    .access-indicator::before {
      content: "";
      width: 8px;
      height: 10px;
      border: 1.5px solid currentColor;
      border-radius: 5px 5px 4px 4px;
      clip-path: polygon(50% 0, 100% 18%, 90% 72%, 50% 100%, 10% 72%, 0 18%);
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
    :host([narrow]) .header {
      padding-top: 12px;
    }
    :host([narrow]) .access-indicator .access-indicator-label {
      display: none;
    }
    :host([narrow]) .brand-title {
      font-size: 15px;
    }
    :host([narrow]) .brand-context {
      font-size: 11px;
    }
    :host([narrow]) .customize-btn {
      padding: 7px 10px;
    }
    @container (max-width: 420px) {
      .header {
        padding-top: 12px;
      }
      .customize-btn {
        padding: 7px 10px;
      }
    }
  `;

  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean, reflect: true }) narrow = false;
  @property({ attribute: false }) panel?: PanelInfo;

  @state() private _tab: TabId = "dashboard";
  @state() private _access: AccessInfo | null = null;
  @state() private _version: string | null = null;
  @state() private _probe: ProbeOverview | null = null;
  // Transient "Customize" edit mode; not persisted, reset on tab change.
  @state() private _customizeMode = false;
  // One-shot client filter from a ha-soc-navigate event (nav.ts); cleared once the Network tab consumes it.
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
      // A rejected callWS (e.g. this admin is already locked out) is treated as allowed:false.
      this._access = { is_owner: false, access_level: "owner_only", allowed: false };
    }
  }

  private async _loadFooterInfo() {
    // Plain require_admin commands, reachable even when access_level locks this admin out; best-effort.
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
    const activeWorkspace = workspaceForTab(this._tab);
    return html`
      <div class="header">
        <div class="brand">
          <span class="brand-mark">SOC</span>
          <span>
            <span class="brand-title">HA SOC Security Console</span>
            <span class="brand-context">Protected detail workspace</span>
          </span>
        </div>
        <span
          class="access-indicator"
          title=${this._access.is_owner ? "Owner access" : "Administrator access"}
          aria-label=${this._access.is_owner ? "Owner access" : "Administrator access"}
        >
          <span class="access-indicator-label"
            >${this._access.is_owner ? "Owner access" : "Administrator access"}</span
          >
        </span>
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
      <nav class="tabs" aria-label="HA SOC workspaces">
        ${SOC_WORKSPACES.map((workspace) => {
          const locked = !!workspace.ownerOnly && !this._access?.is_owner;
          if (locked) {
            return html`
              <button type="button" class="tab disabled" title="Only available to the account owner" disabled>
                ${workspace.label}<span class="lock">🔒</span>
              </button>
            `;
          }
          return html`
            <button
              type="button"
              class="tab ${activeWorkspace.id === workspace.id ? "active" : ""}"
              aria-current=${activeWorkspace.id === workspace.id ? "page" : "false"}
              @click=${() => this._selectTab(workspace.defaultTab)}
            >
              ${workspace.label}
            </button>
          `;
        })}
      </nav>
      ${activeWorkspace.tabs.length > 1
        ? html`
            <nav class="subtabs" aria-label="${activeWorkspace.label} views">
              ${activeWorkspace.tabs.map(
                (item) => html`
                  <button
                    type="button"
                    class="subtab ${this._tab === item.id ? "active" : ""}"
                    aria-current=${this._tab === item.id ? "page" : "false"}
                    @click=${() => this._selectTab(item.id)}
                  >
                    ${item.label}
                  </button>
                `
              )}
            </nav>
          `
        : html``}
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
        // Defense in depth: the owner-only WS commands would reject a non-owner anyway.
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
