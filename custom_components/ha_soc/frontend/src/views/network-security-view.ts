import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  AclReport,
  AclRule,
  NetworkSecurityFinding,
  NetworkSecurityOverview,
  PiHoleOverview,
  ServerPortsReport,
  fetchNetworkSecurityOverview,
} from "../data/ha-soc-ws";

// The ACL Rules card, the HA-server-port correlation, and the Pi-hole DNS
// section used to live scattered across the Network tab; this view is the
// dedicated security-audit surface the Network tab's ACL card moved into,
// plus the two new pieces (server-port coverage, Pi-hole) tied together
// with the advisory findings list this project derives from all three.
@customElement("ha-soc-network-security-view")
export class HaSocNetworkSecurityView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .table-wrap {
        overflow-x: auto;
      }
      td.num,
      th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }
      .mono {
        font-family: var(--code-font-family, monospace);
        font-size: 12px;
      }
      .match {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .match.failing {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      .match.healthy {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      .match.other {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        color: var(--secondary-text-color);
      }
      .chips {
        display: inline-flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .chip {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        border-radius: 100px;
        padding: 2px 8px;
        font-size: 11px;
      }
      .sub {
        display: block;
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
      .finding {
        display: flex;
        gap: 12px;
        padding: 10px 0;
        border-top: 1px solid var(--divider-color);
      }
      .finding:first-of-type {
        border-top: none;
      }
      .sev {
        flex: 0 0 auto;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 6px;
      }
      .sev.high {
        background: var(--status-critical, #d03b3b);
      }
      .sev.medium {
        background: var(--status-warning, #fab219);
      }
      .sev.info {
        background: var(--cat-other, #9aa0a6);
      }
      .finding-title {
        font-weight: 600;
        font-size: 13.5px;
      }
      .finding-detail {
        font-size: 12.5px;
        color: var(--secondary-text-color);
        margin-top: 3px;
        line-height: 1.5;
      }
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 4px;
      }
      .stat-tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .stat-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--secondary-text-color);
      }
      .stat-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
      }
      .domain-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12.5px;
        max-height: 220px;
        overflow-y: auto;
      }
      .domain-list .row {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 3px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .domain-list .row:last-child {
        border-bottom: none;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _overview: NetworkSecurityOverview | null = null;
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _aclSort: SortState | null = null;
  @state() private _portSort: SortState | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      this._overview = await fetchNetworkSecurityOverview(this.hass);
    } catch (e) {
      this._error = e instanceof Error ? e.message : String(e);
      this._overview = null;
    } finally {
      this._loading = false;
    }
  }

  render() {
    if (this._loading) return html`<div class="card">Loading…</div>`;
    if (this._error) {
      return html`<div class="card"><div class="alert">${this._error}</div></div>`;
    }
    const o = this._overview;
    if (!o) return html`<div class="card">No data.</div>`;

    return html`
      <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
        <button class="ha-btn" @click=${() => this._load()}>Refresh</button>
        <span class="muted" style="font-size:12px;">
          Advisory only — nothing on this tab changes UniFi or Pi-hole configuration.
        </span>
      </div>
      ${this._renderFindings(o.findings)}
      ${this._renderAcl(o.acl)}
      ${this._renderServerPorts(o.server_ports)}
      ${this._renderPihole(o.pihole)}
    `;
  }

  // -- Findings ---------------------------------------------------------

  private _renderFindings(findings: NetworkSecurityFinding[]) {
    return html`
      <div class="card">
        <h3>Suggestions</h3>
        ${findings.length
          ? html`${findings.map(
              (f) => html`
                <div class="finding">
                  <div class="sev ${f.severity}" title=${f.severity}></div>
                  <div>
                    <div class="finding-title">${f.title}</div>
                    <div class="finding-detail">${f.detail}</div>
                  </div>
                </div>
              `
            )}`
          : html`<div class="empty">Nothing stood out — no advisory findings right now.</div>`}
      </div>
    `;
  }

  // -- ACL rules ----------------------------------------------------------

  private _aclActionClass(action: string | null): string {
    const a = (action ?? "").toLowerCase();
    if (["allow", "accept", "permit"].some((x) => a.includes(x))) return "healthy";
    if (["deny", "drop", "block", "reject"].some((x) => a.includes(x))) return "failing";
    return "other";
  }

  private _renderAcl(acl: AclReport) {
    return html`
      <div class="card" id="acl-card">
        <h3>
          ACL Rules — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— order matters; rules are evaluated top to bottom${
              acl.endpoint ? ` · source: ${acl.endpoint}` : ""
            }</span
          >
        </h3>
        ${!acl.available
          ? html`
              <div class="note" style="font-size:13px;">
                This controller's Integration API didn't return ACL rules. Endpoints tried:
                <code>${acl.endpoints_tried.join(", ") || "—"}</code>.${
                  acl.error ? html` Last response: ${acl.error}.` : ""
                }
              </div>
            `
          : !acl.rules.length
            ? html`<div class="empty">No ACL rules configured (endpoint: ${acl.endpoint}).</div>`
            : html`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${sortableTh("#", "order", this._aclSort, (n) => (this._aclSort = n), { numeric: true })}
                        ${sortableTh("Name", "name", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Action", "action", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Protocols", "protocols", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Networks", "networks", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Ports", "ports", this._aclSort, (n) => (this._aclSort = n), { numeric: true })}
                        ${sortableTh("Enabled", "enabled", this._aclSort, (n) => (this._aclSort = n))}
                      </tr>
                    </thead>
                    <tbody>
                      ${sortRows(acl.rules.slice(), this._aclSort, {
                        order: (r) => r.order,
                        name: (r) => r.name,
                        action: (r) => r.action,
                        protocols: (r) => r.protocols.join(", ") || null,
                        networks: (r) => r.networks.join(", ") || null,
                        ports: (r) => r.ports.length,
                        enabled: (r) => r.enabled,
                      }).map((r: AclRule, i) => this._renderAclRow(r, i))}
                    </tbody>
                  </table>
                </div>
                <div class="note">
                  Order reflects evaluation precedence as returned by the controller. Source
                  and destination detail (IP/subnet, MAC, port scoping) is shown under each
                  rule's name when the controller reported it.
                </div>
              `}
      </div>
    `;
  }

  private _renderAclRow(r: AclRule, i: number) {
    const srcBits: string[] = [];
    if (r.source.ip_or_subnets.length) srcBits.push(`from ${r.source.ip_or_subnets.join(", ")}`);
    if (r.source.macs.length) srcBits.push(`MAC ${r.source.macs.join(", ")}`);
    const dstBits: string[] = [];
    if (r.destination.ip_or_subnets.length) dstBits.push(`to ${r.destination.ip_or_subnets.join(", ")}`);
    if (r.destination.macs.length) dstBits.push(`MAC ${r.destination.macs.join(", ")}`);
    const detail = [...srcBits, ...dstBits].join(" · ");
    return html`
      <tr>
        <td class="num">${r.order ?? i + 1}</td>
        <td style="font-weight:600;">
          ${r.name ?? "—"}${detail ? html`<span class="sub">${detail}</span>` : nothing}
        </td>
        <td>
          ${r.action
            ? html`<span class="match ${this._aclActionClass(r.action)}">${r.action}</span>`
            : html`<span class="muted">—</span>`}
        </td>
        <td>${r.protocols.length ? r.protocols.join(", ") : html`<span class="muted">any</span>`}</td>
        <td>
          ${r.networks.length
            ? html`<span class="chips">${r.networks.map((n) => html`<span class="chip">${n}</span>`)}</span>`
            : html`<span class="muted">any / —</span>`}
        </td>
        <td>
          ${r.ports.length
            ? html`<span class="mono">${r.ports.join(", ")}</span>`
            : html`<span class="muted">any</span>`}
        </td>
        <td>
          ${r.enabled == null
            ? html`<span class="muted">—</span>`
            : r.enabled
              ? "yes"
              : html`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `;
  }

  // -- HA server ports ------------------------------------------------------

  private _portStatusClass(status: string): string {
    if (status === "covered") return "healthy";
    if (status === "uncovered") return "failing";
    return "other";
  }

  private _renderServerPorts(sp: ServerPortsReport) {
    return html`
      <div class="card">
        <h3>
          Home Assistant Server Ports
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— cross-referenced against the ACL rules above</span
          >
        </h3>
        ${!sp.available
          ? html`
              <div class="empty">
                No listening-port report from the HA SOC Probe add-on yet, or none of its
                reported bind addresses are real LAN addresses. Install/enable the Probe
                add-on to populate this.
              </div>
            `
          : html`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${sortableTh("Port", "port", this._portSort, (n) => (this._portSort = n), {
                        numeric: true,
                      })}
                      ${sortableTh("Proto", "proto", this._portSort, (n) => (this._portSort = n))}
                      ${sortableTh("Address", "address", this._portSort, (n) => (this._portSort = n))}
                      ${sortableTh("Process", "process", this._portSort, (n) => (this._portSort = n))}
                      ${sortableTh("Coverage", "status", this._portSort, (n) => (this._portSort = n))}
                    </tr>
                  </thead>
                  <tbody>
                    ${sortRows(sp.ports.slice(), this._portSort, {
                      port: (p) => p.port,
                      proto: (p) => p.proto,
                      address: (p) => p.address,
                      process: (p) => p.process,
                      status: (p) => p.status,
                    }).map(
                      (p) => html`
                        <tr>
                          <td class="num">${p.port}</td>
                          <td>${p.proto ?? "—"}</td>
                          <td class="mono">${p.address ?? "—"}</td>
                          <td>${p.process ?? "—"}</td>
                          <td>
                            <span class="match ${this._portStatusClass(p.status)}">
                              ${p.status === "covered"
                                ? `covered by ${p.covered_by.join(", ")}`
                                : p.status === "network_scoped"
                                  ? `network-scoped: ${p.network_scoped_by.join(", ")}`
                                  : "uncovered"}
                            </span>
                          </td>
                        </tr>
                      `
                    )}
                  </tbody>
                </table>
              </div>
              <div class="note">
                "Uncovered" means no enabled ACL rule names this server's IP/subnet as a
                destination for that port — it does not by itself mean the port is reachable
                from every network; UniFi's own default zone policy still applies.
                "Network-scoped" means a rule covers it by network/zone rather than by IP,
                which this project can't independently verify covers this server.
              </div>
            `}
      </div>
    `;
  }

  // -- Pi-hole --------------------------------------------------------------

  private _renderPihole(p: PiHoleOverview) {
    if (!p.configured) {
      return html`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="empty">
            Not connected. Add a Pi-hole host and app password in Settings to see blocking
            status, IoT client group scoping, and recently blocked domains here.
          </div>
        </div>
      `;
    }
    if (!p.reachable) {
      return html`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="alert">${p.error ?? "Pi-hole is not reachable."}</div>
        </div>
      `;
    }
    return html`
      <div class="card">
        <h3>Pi-hole DNS</h3>
        <div class="stat-row">
          <div class="stat-tile">
            <span class="label">Blocking</span>
            <span class="value">${p.blocking_enabled ? "On" : "Off"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Queries (24h window)</span>
            <span class="value">${p.summary?.total ?? "—"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Blocked</span>
            <span class="value"
              >${p.summary?.blocked ?? "—"}${
                p.summary?.percent_blocked != null ? ` (${p.summary.percent_blocked.toFixed(1)}%)` : ""
              }</span
            >
          </div>
          <div class="stat-tile">
            <span class="label">IoT subnet scoped</span>
            <span class="value">
              ${p.iot_cidr == null
                ? html`<span class="muted" style="font-size:16px;">not set</span>`
                : p.iot_clients_scoped
                  ? "Yes"
                  : html`<span style="color:var(--status-warning, #fab219);">No</span>`}
            </span>
          </div>
        </div>
        ${p.top_blocked_domains.length || p.recent_blocked.length
          ? html`
              <div class="stat-row" style="margin-top:12px;">
                ${p.top_blocked_domains.length
                  ? html`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Top blocked domains</span>
                        <div class="domain-list">
                          ${p.top_blocked_domains.map(
                            (d) => html`<div class="row"><span>${d.domain}</span><span>${d.count}</span></div>`
                          )}
                        </div>
                      </div>
                    `
                  : nothing}
                ${p.recent_blocked.length
                  ? html`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Recently blocked</span>
                        <div class="domain-list">
                          ${p.recent_blocked.map((d) => html`<div class="row"><span>${d}</span></div>`)}
                        </div>
                      </div>
                    `
                  : nothing}
              </div>
            `
          : nothing}
      </div>
    `;
  }
}
