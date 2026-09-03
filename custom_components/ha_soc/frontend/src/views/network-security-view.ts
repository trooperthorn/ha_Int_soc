import { html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { navigate } from "../nav";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  AclReport,
  AclRule,
  FirewallPoliciesReport,
  FirewallPolicy,
  NetworkSecurityFinding,
  NetworkSecurityOverview,
  PiHoleOverview,
  ServerPortsReport,
  fetchNetworkSecurityOverview,
} from "../data/ha-soc-ws";
import { matchClientsForEntries } from "../device-match";
import { buildZoneMatrix } from "../firewall-matrix";

// Security-audit surface: findings, Firewall Policies (zone-based), ACL Rules, HA server ports, Pi-hole.
@customElement("ha-soc-network-security-view")
export class HaSocNetworkSecurityView extends HaSocCustomizableView {
  protected get viewId() {
    return "network_security";
  }

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
      .badge-custom {
        display: inline-block;
        margin-left: 6px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        padding: 1px 7px;
        border-radius: 100px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.15);
        color: var(--primary-color);
        vertical-align: middle;
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
      .view-toggle {
        display: inline-flex;
        border: 1px solid var(--divider-color);
        border-radius: 100px;
        overflow: hidden;
        margin-bottom: 10px;
      }
      .view-toggle button {
        border: none;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
        font-size: 12px;
        font-weight: 600;
        padding: 5px 14px;
        cursor: pointer;
      }
      .view-toggle button.active {
        background: var(--primary-color);
        color: #fff;
      }
      .device-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
        color: var(--primary-color);
        border: none;
        border-radius: 100px;
        padding: 1px 8px;
        font-size: 10.5px;
        cursor: pointer;
        margin: 2px 3px 0 0;
      }
      .device-chip:hover {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.2);
      }
      .matrix-wrap {
        overflow-x: auto;
      }
      table.zone-matrix {
        border-collapse: collapse;
      }
      table.zone-matrix th,
      table.zone-matrix td {
        border: 1px solid var(--divider-color);
        padding: 6px;
        text-align: center;
        font-size: 11.5px;
      }
      table.zone-matrix th {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
        font-weight: 600;
      }
      table.zone-matrix th.corner {
        background: transparent;
        border: none;
      }
      table.zone-matrix td.cell {
        cursor: pointer;
        min-width: 64px;
      }
      table.zone-matrix td.cell:hover {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      table.zone-matrix td.cell.allow {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      table.zone-matrix td.cell.block {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      table.zone-matrix td.cell.mixed {
        background: rgba(var(--status-warning, #fab219), 0.18);
        color: #9a6a00;
      }
      table.zone-matrix td.cell.none {
        color: var(--secondary-text-color);
      }
      .zone-pair-filter {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12.5px;
        margin-bottom: 10px;
      }
    `,
  ];

  @state() private _overview: NetworkSecurityOverview | null = null;
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _aclSort: SortState | null = null;
  @state() private _firewallPolicySort: SortState | null = null;
  @state() private _portSort: SortState | null = null;
  // Firewall Policies card: Table vs Matrix; a matrix cell filters the table to one zone pair (null clears).
  @state() private _fwViewMode: "table" | "matrix" = "table";
  @state() private _fwZonePairFilter: { src: string; dst: string } | null = null;

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

    const sections: LayoutSection[] = [
      { id: "findings", title: "Suggestions", render: () => this._renderFindings(o.findings) },
      {
        id: "firewall_policies",
        title: "Firewall Policies",
        render: () => this._renderFirewallPolicies(o.firewall_policies),
      },
      { id: "acl", title: "ACL Rules", render: () => this._renderAcl(o.acl) },
      { id: "server_ports", title: "Home Assistant Server Ports", render: () => this._renderServerPorts(o.server_ports) },
      { id: "pihole", title: "Pi-hole DNS", render: () => this._renderPihole(o.pihole) },
    ];
    return html`
      <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
        <button class="ha-btn" @click=${() => this._load()}>Refresh</button>
        <span class="muted" style="font-size:12px;">
          Advisory only — nothing on this tab changes UniFi or Pi-hole configuration.
        </span>
      </div>
      ${this._renderSections(sections)}
    `;
  }


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


  // metadata.origin USER_DEFINED marks a rule the owner created; a null origin renders nothing, not "not custom".
  private _renderCustomBadge(custom: boolean | null) {
    return custom ? html`<span class="badge-custom">custom</span>` : nothing;
  }

  private _customCountLabel(rows: { custom: boolean | null }[]): string {
    const known = rows.filter((r) => r.custom != null);
    if (!known.length) return "";
    const customCount = known.filter((r) => r.custom).length;
    return ` · ${customCount} custom / ${rows.length} total`;
  }

  // Resolve a rule/policy's IP/subnet/MAC entries against the Network tab's client list.

  private _renderDeviceChips(entries: string[]) {
    const clients = this._overview?.clients ?? [];
    const all = matchClientsForEntries(entries, clients);
    const matches = all.slice(0, 6);
    if (!matches.length) return nothing;
    const overflow = all.length - matches.length;
    return html`
      <span class="sub" style="display:block;margin-top:3px;">
        ${matches.map(
          (m) => html`
            <button
              class="device-chip"
              title="Jump to ${m.name} on the Network tab"
              @click=${() => navigate(this, "network", m.matchedOn)}
            >
              📟 ${m.name}
            </button>
          `
        )}${overflow > 0 ? html`<span class="muted" style="font-size:10.5px;">+${overflow} more</span>` : nothing}
      </span>
    `;
  }

  private _policyActionClass(action: string | null): string {
    const a = (action ?? "").toLowerCase();
    if (a === "allow") return "healthy";
    if (a === "block" || a === "reject") return "failing";
    return "other";
  }

  private _renderFirewallPolicies(fw: FirewallPoliciesReport) {
    const rows = this._fwZonePairFilter
      ? fw.rules.filter(
          (r) =>
            r.source.zone === this._fwZonePairFilter!.src &&
            r.destination.zone === this._fwZonePairFilter!.dst
        )
      : fw.rules;
    return html`
      <div class="card">
        <h3>
          Firewall Policies — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— UniFi's default zone-based allow/deny view; order matters, evaluated top
            to bottom${this._customCountLabel(fw.rules)}</span
          >
        </h3>
        ${!fw.available
          ? html`
              <div class="note" style="font-size:13px;">
                Couldn't read Firewall Policies from this controller.${
                  fw.error ? html` ${fw.error}` : ""
                }
              </div>
            `
          : !fw.rules.length
            ? html`<div class="empty">No Firewall Policies configured.</div>`
            : html`
                <div class="view-toggle">
                  <button
                    class=${this._fwViewMode === "table" ? "active" : ""}
                    @click=${() => (this._fwViewMode = "table")}
                  >
                    Table
                  </button>
                  <button
                    class=${this._fwViewMode === "matrix" ? "active" : ""}
                    @click=${() => (this._fwViewMode = "matrix")}
                  >
                    Zone Matrix
                  </button>
                </div>
                ${this._fwViewMode === "matrix"
                  ? this._renderZoneMatrix(fw)
                  : this._renderFirewallPolicyTable(rows)}
              `}
      </div>
    `;
  }

  private _renderFirewallPolicyTable(rows: FirewallPolicy[]) {
    return html`
      ${this._fwZonePairFilter
        ? html`
            <div class="zone-pair-filter">
              <span class="chip"
                >${this._fwZonePairFilter.src} → ${this._fwZonePairFilter.dst}</span
              >
              <button
                style="cursor:pointer;border:none;background:none;color:var(--primary-color);font-size:12px;"
                @click=${() => (this._fwZonePairFilter = null)}
              >
                Clear filter
              </button>
            </div>
          `
        : nothing}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${sortableTh("#", "order", this._firewallPolicySort, (n) => (this._firewallPolicySort = n), {
                numeric: true,
              })}
              ${sortableTh("Name", "name", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Action", "action", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Source zone", "source_zone", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Dest. zone", "dest_zone", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Protocol", "protocol", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Ports", "ports", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Enabled", "enabled", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
            </tr>
          </thead>
          <tbody>
            ${rows.length
              ? sortRows(rows.slice(), this._firewallPolicySort, {
                  order: (r) => r.order,
                  name: (r) => r.name,
                  action: (r) => r.action,
                  source_zone: (r) => r.source.zone,
                  dest_zone: (r) => r.destination.zone,
                  protocol: (r) => r.protocol,
                  ports: (r) => r.ports.length,
                  enabled: (r) => r.enabled,
                }).map((r: FirewallPolicy, i) => this._renderFirewallPolicyRow(r, i))
              : html`<tr><td colspan="8"><div class="empty">No policies for this zone pair.</div></td></tr>`}
          </tbody>
        </table>
      </div>
      <div class="note">
        Every policy is scoped to a source/destination zone pair; the detail line under
        each name shows any additional network/IP/MAC/domain narrowing the controller
        reported, and a resolved device chip when it matches a known client.
      </div>
    `;
  }

  private _renderZoneMatrix(fw: FirewallPoliciesReport) {
    if (!fw.zones.length) {
      return html`<div class="empty">No firewall zones reported by this controller.</div>`;
    }
    const matrix = buildZoneMatrix(fw.zones, fw.rules);
    const zoneNames = fw.zones.map((z) => z.name);
    return html`
      <div class="matrix-wrap">
        <table class="zone-matrix">
          <thead>
            <tr>
              <th class="corner"></th>
              ${zoneNames.map((n) => html`<th>${n}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${matrix.map(
              (row, ri) => html`
                <tr>
                  <th>${zoneNames[ri]}</th>
                  ${row.map(
                    (cell) => html`
                      <td
                        class="cell ${cell.dominant}"
                        title="${cell.policies.length} polic${cell.policies.length === 1 ? "y" : "ies"}"
                        @click=${() => this._selectZonePair(cell.srcZone, cell.dstZone)}
                      >
                        ${cell.dominant === "none"
                          ? "—"
                          : cell.dominant === "mixed"
                            ? "mixed"
                            : cell.dominant === "allow"
                              ? "allow"
                              : "block"}${cell.policies.length ? html`<br /><span style="font-size:10px;">${cell.policies.length}</span>` : nothing}
                      </td>
                    `
                  )}
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
      <div class="note">
        Rows are the source zone, columns the destination zone. Click a cell to see its
        policies. "mixed" means both allow and block/reject policies exist for that pair
        — which one actually governs a given connection depends on evaluation order and
        UniFi's own implicit-deny fallback, neither of which this project models; open
        the filtered table to read the real order.
      </div>
    `;
  }

  private _selectZonePair(src: string, dst: string) {
    this._fwZonePairFilter = { src, dst };
    this._fwViewMode = "table";
  }

  private _renderFirewallPolicyRow(r: FirewallPolicy, i: number) {
    const detailFor = (side: FirewallPolicy["source"]) => {
      const bits: string[] = [];
      if (side.networks.length) bits.push(`networks: ${side.networks.join(", ")}`);
      if (side.ip_or_subnets.length) bits.push(`IP: ${side.ip_or_subnets.join(", ")}`);
      if (side.macs.length) bits.push(`MAC: ${side.macs.join(", ")}`);
      if (side.domains.length) bits.push(`domains: ${side.domains.join(", ")}`);
      if (side.applications.length) bits.push(`${side.applications.length} app(s)`);
      if (side.application_categories.length) bits.push(`${side.application_categories.length} app categor${side.application_categories.length === 1 ? "y" : "ies"}`);
      if (!bits.length && side.filter_type) bits.push(side.filter_type.toLowerCase().replace(/_/g, " "));
      return bits.join(" · ");
    };
    const srcDetail = detailFor(r.source);
    const dstDetail = detailFor(r.destination);
    const detail = [srcDetail && `from ${srcDetail}`, dstDetail && `to ${dstDetail}`].filter(Boolean).join(" · ");
    const deviceEntries = [
      ...r.source.ip_or_subnets,
      ...r.source.macs,
      ...r.destination.ip_or_subnets,
      ...r.destination.macs,
    ];
    return html`
      <tr>
        <td class="num">${r.order ?? i + 1}</td>
        <td style="font-weight:600;">
          ${r.name ?? "—"}${this._renderCustomBadge(r.custom)}${
            detail ? html`<span class="sub">${detail}</span>` : nothing
          }${this._renderDeviceChips(deviceEntries)}
        </td>
        <td>
          ${r.action
            ? html`<span class="match ${this._policyActionClass(r.action)}">${r.action}</span>`
            : html`<span class="muted">—</span>`}${
              r.allow_return_traffic
                ? html`<span class="sub">+ mirrored return-traffic policy</span>`
                : nothing
            }
        </td>
        <td>${r.source.zone ?? html`<span class="muted">—</span>`}</td>
        <td>${r.destination.zone ?? html`<span class="muted">—</span>`}</td>
        <td>${r.protocol ?? html`<span class="muted">any</span>`}</td>
        <td>
          ${r.ports.length
            ? html`<span class="mono">${r.ports.join(", ")}</span>`
            : r.source.ports_from_list || r.destination.ports_from_list
              ? html`<span class="muted">traffic matching list</span>`
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
            }${this._customCountLabel(acl.rules)}</span
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
    const deviceEntries = [
      ...r.source.ip_or_subnets,
      ...r.source.macs,
      ...r.destination.ip_or_subnets,
      ...r.destination.macs,
    ];
    return html`
      <tr>
        <td class="num">${r.order ?? i + 1}</td>
        <td style="font-weight:600;">
          ${r.name ?? "—"}${this._renderCustomBadge(r.custom)}${
            detail ? html`<span class="sub">${detail}</span>` : nothing
          }${this._renderDeviceChips(deviceEntries)}
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
