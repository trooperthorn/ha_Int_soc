import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { navigate, navigateToHaPath, devicesForIntegrationPath } from "../nav";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  NetworkOverview,
  NetworkClientRow,
  NetworkDeviceRow,
  ProtectCamera,
  ProtectEvent,
  UniFiBandwidth,
  fetchNetworkOverview,
} from "../data/ha-soc-ws";

const PAGE_SIZE_OPTIONS: (number | "all")[] = [25, 50, 100, "all"];

// Client-side scheme gate for every external href this view binds (work
// plan item 4.12). The camera and thumbnail links are built server-side
// from controller-supplied host strings, so a hostile or misconfigured
// controller could hand back a javascript: or data: URL; only http(s)
// may ever reach an anchor's href. Anything else returns null and the
// caller renders plain text instead of a link.
function safeExternalHref(href: string | null): string | null {
  if (!href) return null;
  try {
    const scheme = new URL(href).protocol;
    return scheme === "http:" || scheme === "https:" ? href : null;
  } catch {
    // Not parseable as an absolute URL: refuse it rather than let the
    // browser resolve it into something this check never saw.
    return null;
  }
}

// Kept close to the Dashboard view's language on purpose — the user asked
// the Network tab to "look close to identical to Dashboard View". Same stat
// tiles up top, same searchable/paginated table styling below.
@customElement("ha-soc-network-view")
export class HaSocNetworkView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
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
      .stat-tile .sub {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
      }
      .dot.good {
        background: var(--status-good);
      }
      .dot.bad {
        background: var(--status-critical);
      }
      .dot.unknown {
        background: var(--cat-other);
      }
      .ssid-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .ssid-row {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
      }
      .ssid-row .name {
        min-width: 140px;
        font-weight: 600;
      }
      .ssid-row .bar {
        flex: 1;
        height: 8px;
        border-radius: 4px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        overflow: hidden;
      }
      .ssid-row .bar > span {
        display: block;
        height: 100%;
        background: var(--primary-color);
      }
      .ssid-row .count {
        min-width: 32px;
        text-align: right;
        font-variant-numeric: tabular-nums;
        font-weight: 700;
      }
      .ssid-row.clickable {
        cursor: pointer;
        border-radius: 6px;
        padding: 4px 6px;
        margin: -4px -6px;
      }
      .ssid-row.clickable:hover {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
      }
      .ssid-row.active {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.12);
      }
      .ssid-row.active .name {
        color: var(--primary-color);
      }
      .filters {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .filters label {
        font-size: 12px;
        color: var(--secondary-text-color);
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .active-filter {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
      }
      .thumb-link {
        color: var(--primary-color);
        cursor: pointer;
        text-decoration: none;
      }
      .plate {
        font-family: var(--code-font-family, monospace);
        font-weight: 700;
        letter-spacing: 0.06em;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        padding: 2px 6px;
        border-radius: 4px;
      }
      .table-wrap {
        overflow-x: auto;
      }
      .toolbar input {
        flex: 1;
        min-width: 180px;
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
        cursor: pointer;
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
      .alert {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.1);
        border: 1px solid var(--error-color, #db4437);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 13.5px;
        color: var(--primary-text-color);
        line-height: 1.5;
      }
      .footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .footer select {
        margin-left: auto;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _overview: NetworkOverview | null = null;
  @state() private _loading = true;
  @state() private _error: string | null = null;

  @state() private _clientSearch = "";
  @state() private _clientPage = 0;
  @state() private _clientPageSize: number | "all" = 25;
  @state() private _clientVlanFilter = "";
  @state() private _clientSsidFilter = "";
  @state() private _clientSort: SortState | null = null;
  @state() private _deviceSearch = "";
  @state() private _devicePage = 0;
  @state() private _devicePageSize: number | "all" = 25;
  @state() private _deviceSort: SortState | null = null;
  @state() private _protectSort: SortState | null = null;
  @state() private _eventSort: SortState | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      this._overview = await fetchNetworkOverview(this.hass);
    } catch (e) {
      this._error = e instanceof Error ? e.message : String(e);
      this._overview = null;
    } finally {
      this._loading = false;
    }
  }

  // -- formatting helpers ---------------------------------------------------
  private _fmtBytes(n: number | null | undefined): string {
    if (n == null) return "—";
    if (n < 1024) return `${n} B`;
    const units = ["KB", "MB", "GB", "TB", "PB"];
    let v = n / 1024;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
  }

  private _fmtRate(bps: number | null | undefined): string {
    if (bps == null) return "—";
    const bits = bps * 8;
    if (bits < 1000) return `${bits} bps`;
    const units = ["kbps", "Mbps", "Gbps"];
    let v = bits / 1000;
    let i = 0;
    while (v >= 1000 && i < units.length - 1) {
      v /= 1000;
      i++;
    }
    return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
  }

  private _fmtBandwidth(b: UniFiBandwidth | null): string {
    if (!b) return "—";
    return `↓ ${this._fmtBytes(b.rx_bytes)} · ↑ ${this._fmtBytes(b.tx_bytes)}`;
  }

  private _fmtUptime(seconds: number | null): string {
    if (seconds == null) return "—";
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  private _fmtLastSeen(epoch: number | null): string {
    if (epoch == null) return "—";
    const now = Date.now() / 1000;
    const diff = Math.max(0, now - epoch);
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 86400 * 30) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(epoch * 1000).toLocaleDateString();
  }

  private _fmtVlan(v: number | string | null): string {
    if (v == null || v === "") return "—";
    return String(v);
  }

  // -- match cell -----------------------------------------------------------
  private _renderMatch(row: NetworkClientRow) {
    const m = row.integration_match;
    if (!m) return html`<span class="muted">—</span>`;
    const cls = m.failing ? "failing" : m.healthy ? "healthy" : "other";
    const icon = m.failing ? "⚠" : m.healthy ? "●" : "○";
    const title = `${m.domain} — config entry state: ${m.state}. Click to open in Home Assistant.`;
    return html`
      <span
        class="match ${cls}"
        title=${title}
        @click=${() => navigateToHaPath(devicesForIntegrationPath(m.entry_id))}
      >
        ${icon} ${m.domain}${m.failing ? " failing" : ""}
      </span>
    `;
  }

  private _filter<T extends NetworkClientRow>(rows: T[], q: string): T[] {
    const s = q.trim().toLowerCase();
    if (!s) return rows;
    return rows.filter((r) =>
      [r.name, r.ipv4, r.ipv6, r.mac, r.ssid, r.integration_match?.domain]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(s))
    );
  }

  private _paginate<T>(rows: T[], page: number, size: number | "all"): T[] {
    if (size === "all") return rows;
    return rows.slice(page * size, page * size + size);
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading network…</div>`;
    if (this._error)
      return html`<div class="alert">Could not load the Network overview: ${this._error}</div>`;
    const o = this._overview;
    if (!o) return html`<div class="empty">No network data.</div>`;

    if (!o.configured) {
      return html`
        <div class="card">
          <h3>UniFi Network not configured</h3>
          <p class="muted" style="font-size:13px;line-height:1.6;">
            Add a UniFi Network controller host and a local API key in
            <strong>Settings</strong> (owner only) to see status, WAN throughput,
            wireless clients, and the client / device tables here. The API key is a
            local one generated on the console under
            <em>Settings → Control Plane → Integrations</em>; nothing leaves your LAN.
          </p>
          <button class="ha-btn" @click=${() => navigate(this, "settings")}>
            Open Settings
          </button>
        </div>
        ${this._renderProtectCard(o)}
      `;
    }

    if (!o.reachable) {
      return html`
        <div class="alert">
          <strong>UniFi Network is configured but not reachable.</strong><br />
          ${o.error ?? "Unknown error."}
        </div>
        <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        ${this._renderProtectCard(o)}
      `;
    }

    return html`
      ${this._renderFailingBanner(o)} ${this._renderStats(o)} ${this._renderSsid(o)}
      ${this._renderClientsTable(o)} ${this._renderDevicesTable(o)}
      ${this._renderProtectCard(o)}
      <div class="footer">
        <span>Last updated ${new Date(o.generated_at).toLocaleTimeString()}</span>
        <button class="ha-btn" style="margin-left:auto;" @click=${() => this._load()}>
          Refresh
        </button>
      </div>
    `;
  }

  private _renderFailingBanner(o: NetworkOverview) {
    if (!o.failing_endpoint_count) return nothing;
    return html`
      <div class="alert">
        <strong>⚠ ${o.failing_endpoint_count} Home Assistant integration${
          o.failing_endpoint_count === 1 ? "" : "s"
        } with a failing config entry ${
          o.failing_endpoint_count === 1 ? "is" : "are"
        } still present on the network.</strong>
        An integration whose device is online (a live client below) but whose config
        entry is in a setup-error/retry state is exactly the "an integration IP is
        failing" case — the device is reachable, so the fault is the integration, not
        the network. Look for the red <span class="match failing" style="cursor:default;"
        >⚠ failing</span> tags in the Integration column.
      </div>
    `;
  }

  private _renderStats(o: NetworkOverview) {
    const statusGood = o.status === "online";
    const inet = o.internet_connected;
    return html`
      <div class="stat-row">
        <div class="stat-tile">
          <div class="label">Network Status</div>
          <div class="value">
            <span class="dot ${statusGood ? "good" : "bad"}"></span>${
              statusGood ? "Online" : "Offline"
            }
          </div>
          <div class="sub">${o.site_id ? `site ${o.site_id}` : ""}</div>
        </div>
        <div class="stat-tile">
          <div class="label">Internet</div>
          <div class="value">
            <span class="dot ${inet === true ? "good" : inet === false ? "bad" : "unknown"}"></span>${
              inet === true ? "Connected" : inet === false ? "Down" : "Unknown"
            }
          </div>
          <div class="sub">${o.wan.ip ? `WAN ${o.wan.ip}` : o.wan.port ? o.wan.port : "—"}</div>
        </div>
        <div class="stat-tile">
          <div class="label">WAN Bandwidth</div>
          <div class="value" style="font-size:18px;">
            ↓ ${this._fmtRate(o.wan.rx_rate_bps)}
          </div>
          <div class="sub">↑ ${this._fmtRate(o.wan.tx_rate_bps)}${o.wan.port ? ` · ${o.wan.port}` : ""}</div>
        </div>
        <div class="stat-tile">
          <div class="label">Wireless Clients</div>
          <div class="value">${o.wireless_client_count}</div>
          <div class="sub">${o.wired_client_count} wired</div>
        </div>
        <div class="stat-tile">
          <div class="label">Total Clients</div>
          <div class="value">${o.total_client_count}</div>
          <div class="sub">${o.devices.length} network devices</div>
        </div>
      </div>
    `;
  }

  // Clicking an SSID here drives the Clients table's SSID filter (toggle
  // off if it's already the active one), then jumps down to the table.
  private _selectSsid(ssid: string) {
    this._clientSsidFilter = this._clientSsidFilter === ssid ? "" : ssid;
    this._clientPage = 0;
    if (this._clientSsidFilter) {
      this.updateComplete.then(() => {
        this.renderRoot?.querySelector("#clients-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  private _renderSsid(o: NetworkOverview) {
    if (!o.clients_per_ssid.length) return nothing;
    const max = Math.max(...o.clients_per_ssid.map((s) => s.count), 1);
    return html`
      <div class="card">
        <h3>Clients per SSID <span class="muted" style="font-weight:400;font-size:12px;">— click to filter the table</span></h3>
        <div class="ssid-list">
          ${o.clients_per_ssid.map(
            (s) => html`
              <div
                class="ssid-row clickable ${this._clientSsidFilter === s.ssid ? "active" : ""}"
                @click=${() => this._selectSsid(s.ssid)}
                title="Filter Clients to ${s.ssid}"
              >
                <span class="name">${s.ssid}</span>
                <span class="bar"><span style="width:${(s.count / max) * 100}%"></span></span>
                <span class="count">${s.count}</span>
              </div>
            `
          )}
        </div>
      </div>
    `;
  }

  // Accessors shared by sortRows for the clients table. IP addresses sort
  // via localeCompare with numeric:true (so 10.0.0.9 < 10.0.0.10).
  private static readonly CLIENT_SORT: Record<string, (r: NetworkClientRow) => unknown> = {
    name: (r) => r.name,
    ipv4: (r) => r.ipv4,
    ipv6: (r) => r.ipv6,
    mac: (r) => r.mac,
    vlan: (r) => (r.vlan == null || r.vlan === "" ? null : Number(r.vlan)),
    ssid: (r) => r.ssid ?? (r.wired ? "wired" : null),
    uptime: (r) => r.uptime,
    bandwidth: (r) => r.bandwidth?.total_bytes ?? null,
    last_seen: (r) => r.last_seen,
    integration: (r) => r.integration_match?.domain ?? null,
  };

  private _colHeaders() {
    const s = this._clientSort;
    const on = (next: SortState) => {
      this._clientSort = next;
      this._clientPage = 0;
    };
    return html`
      <tr>
        ${sortableTh("Client", "name", s, on)}
        ${sortableTh("IPv4", "ipv4", s, on)}
        ${sortableTh("IPv6", "ipv6", s, on)}
        ${sortableTh("MAC", "mac", s, on)}
        ${sortableTh("VLAN", "vlan", s, on, { numeric: true })}
        ${sortableTh("SSID", "ssid", s, on)}
        ${sortableTh("Uptime", "uptime", s, on, { numeric: true })}
        ${sortableTh("Bandwidth", "bandwidth", s, on)}
        ${sortableTh("Last Seen", "last_seen", s, on)}
        ${sortableTh("Integration", "integration", s, on)}
      </tr>
    `;
  }

  private _renderRow(row: NetworkClientRow | NetworkDeviceRow, opts: { model?: boolean } = {}) {
    const dev = row as NetworkDeviceRow;
    return html`
      <tr>
        <td>
          <div style="font-weight:600;">${row.name}</div>
          ${!opts.model && !row.wired
            ? html`<div class="muted" style="font-size:11px;">wireless</div>`
            : opts.model && dev.state
              ? html`<div class="muted" style="font-size:11px;">${dev.state.toLowerCase()}</div>`
              : nothing}
        </td>
        <td class="mono">${row.ipv4 ?? "—"}</td>
        <td class="mono">${row.ipv6 ?? "—"}</td>
        <td class="mono">${row.mac ?? "—"}</td>
        <td class="num">${this._fmtVlan(row.vlan)}</td>
        <td>${row.ssid ?? (row.wired ? html`<span class="muted">wired</span>` : "—")}</td>
        ${opts.model ? html`<td>${dev.model ?? "—"}</td>` : nothing}
        <td class="num">${this._fmtUptime(row.uptime)}</td>
        <td>${this._fmtBandwidth(row.bandwidth)}</td>
        <td>${this._fmtLastSeen(row.last_seen)}</td>
        <td>${this._renderMatch(row)}</td>
      </tr>
    `;
  }

  private _renderClientsTable(o: NetworkOverview) {
    // Distinct VLAN / SSID option lists, drawn from the live client set.
    const vlans = Array.from(
      new Set(o.clients.map((c) => (c.vlan == null || c.vlan === "" ? null : String(c.vlan))).filter(Boolean))
    ).sort((a, b) => Number(a) - Number(b)) as string[];
    const ssids = Array.from(
      new Set(o.clients.map((c) => c.ssid).filter(Boolean))
    ).sort() as string[];

    let filtered = this._filter(o.clients, this._clientSearch);
    if (this._clientVlanFilter)
      filtered = filtered.filter((c) => String(c.vlan ?? "") === this._clientVlanFilter);
    if (this._clientSsidFilter) filtered = filtered.filter((c) => c.ssid === this._clientSsidFilter);
    filtered = sortRows(filtered, this._clientSort, HaSocNetworkView.CLIENT_SORT);

    const page = this._paginate(filtered, this._clientPage, this._clientPageSize);
    return html`
      <div class="card" id="clients-card">
        <h3>Clients (${filtered.length})</h3>
        <div class="filters">
          <label
            >VLAN
            <select
              .value=${this._clientVlanFilter}
              @change=${(e: Event) => {
                this._clientVlanFilter = (e.target as HTMLSelectElement).value;
                this._clientPage = 0;
              }}
            >
              <option value="">All</option>
              ${vlans.map((v) => html`<option value=${v} ?selected=${v === this._clientVlanFilter}>${v}</option>`)}
            </select>
          </label>
          <label
            >SSID
            <select
              .value=${this._clientSsidFilter}
              @change=${(e: Event) => {
                this._clientSsidFilter = (e.target as HTMLSelectElement).value;
                this._clientPage = 0;
              }}
            >
              <option value="">All</option>
              ${ssids.map((s) => html`<option value=${s} ?selected=${s === this._clientSsidFilter}>${s}</option>`)}
            </select>
          </label>
          ${this._clientVlanFilter
            ? html`<span class="active-filter" @click=${() => (this._clientVlanFilter = "")}
                >VLAN ${this._clientVlanFilter} ✕</span
              >`
            : nothing}
          ${this._clientSsidFilter
            ? html`<span class="active-filter" @click=${() => (this._clientSsidFilter = "")}
                >SSID ${this._clientSsidFilter} ✕</span
              >`
            : nothing}
        </div>
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search client, IP, MAC, SSID, integration…"
            .value=${this._clientSearch}
            @input=${(e: Event) => {
              this._clientSearch = (e.target as HTMLInputElement).value;
              this._clientPage = 0;
            }}
          />
        </div>
        ${filtered.length === 0
          ? html`<div class="empty">No clients match.</div>`
          : html`
              <div class="table-wrap">
                <table>
                  <thead>
                    ${this._colHeaders()}
                  </thead>
                  <tbody>
                    ${page.map((r) => this._renderRow(r))}
                  </tbody>
                </table>
              </div>
              ${this._renderPager(
                filtered.length,
                this._clientPage,
                this._clientPageSize,
                (p) => (this._clientPage = p),
                (s) => {
                  this._clientPageSize = s;
                  this._clientPage = 0;
                }
              )}
            `}
        <div class="note">
          Columns shown as “—” aren't reported by this controller's API for that row.
          VLAN, IPv6, SSID, bandwidth, and last-seen availability depend on the UniFi
          firmware/API version.
        </div>
      </div>
    `;
  }

  private static readonly DEVICE_SORT: Record<string, (r: NetworkDeviceRow) => unknown> = {
    name: (r) => r.name,
    ipv4: (r) => r.ipv4,
    mac: (r) => r.mac,
    vlan: (r) => (r.vlan == null || r.vlan === "" ? null : Number(r.vlan)),
    model: (r) => r.model,
    firmware: (r) => r.firmware_updatable,
    bandwidth: (r) => r.bandwidth?.total_bytes ?? null,
    last_seen: (r) => r.last_seen,
    integration: (r) => r.integration_match?.domain ?? null,
  };

  private _renderDevicesTable(o: NetworkOverview) {
    const filtered = sortRows(
      this._filter(o.devices, this._deviceSearch),
      this._deviceSort,
      HaSocNetworkView.DEVICE_SORT
    );
    const page = this._paginate(filtered, this._devicePage, this._devicePageSize);
    const s = this._deviceSort;
    const on = (next: SortState) => {
      this._deviceSort = next;
      this._devicePage = 0;
    };
    return html`
      <div class="card">
        <h3>Network Devices (${filtered.length})</h3>
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search device, IP, MAC, integration…"
            .value=${this._deviceSearch}
            @input=${(e: Event) => {
              this._deviceSearch = (e.target as HTMLInputElement).value;
              this._devicePage = 0;
            }}
          />
        </div>
        ${filtered.length === 0
          ? html`<div class="empty">No network devices match.</div>`
          : html`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${sortableTh("Device", "name", s, on)}
                      ${sortableTh("IPv4", "ipv4", s, on)}
                      ${sortableTh("MAC", "mac", s, on)}
                      ${sortableTh("VLAN", "vlan", s, on, { numeric: true })}
                      ${sortableTh("Model", "model", s, on)}
                      ${sortableTh("Firmware", "firmware", s, on)}
                      ${sortableTh("Bandwidth", "bandwidth", s, on)}
                      ${sortableTh("Last Seen", "last_seen", s, on)}
                      ${sortableTh("Integration", "integration", s, on)}
                    </tr>
                  </thead>
                  <tbody>
                    ${page.map((r) => this._renderDeviceRow(r))}
                  </tbody>
                </table>
              </div>
              ${this._renderPager(
                filtered.length,
                this._devicePage,
                this._devicePageSize,
                (p) => (this._devicePage = p),
                (s) => {
                  this._devicePageSize = s;
                  this._devicePage = 0;
                }
              )}
            `}
      </div>
    `;
  }

  private _renderFirmware(u: boolean | null) {
    if (u == null) return html`<span class="muted">—</span>`;
    return u
      ? html`<span style="color:var(--status-warning);font-weight:600;">Update available</span>`
      : html`<span class="muted">Up to date</span>`;
  }

  private _renderDeviceRow(d: NetworkDeviceRow) {
    return html`
      <tr>
        <td>
          <div style="font-weight:600;">${d.name}</div>
          ${d.state ? html`<div class="muted" style="font-size:11px;">${d.state.toLowerCase()}</div>` : nothing}
        </td>
        <td class="mono">${d.ipv4 ?? "—"}</td>
        <td class="mono">${d.mac ?? "—"}</td>
        <td class="num">${this._fmtVlan(d.vlan)}</td>
        <td>${d.model ?? "—"}</td>
        <td>${this._renderFirmware(d.firmware_updatable)}</td>
        <td>${this._fmtBandwidth(d.bandwidth)}</td>
        <td>${this._fmtLastSeen(d.last_seen)}</td>
        <td>${this._renderMatch(d)}</td>
      </tr>
    `;
  }

  private _renderPager(
    total: number,
    page: number,
    size: number | "all",
    setPage: (p: number) => void,
    setSize: (s: number | "all") => void
  ) {
    const pages = size === "all" ? 1 : Math.max(1, Math.ceil(total / size));
    return html`
      <div class="footer">
        <button class="ha-btn" ?disabled=${page <= 0} @click=${() => setPage(page - 1)}>Prev</button>
        <span>Page ${page + 1} of ${pages}</span>
        <button class="ha-btn" ?disabled=${page >= pages - 1} @click=${() => setPage(page + 1)}>
          Next
        </button>
        <select
          @change=${(e: Event) => {
            const v = (e.target as HTMLSelectElement).value;
            setSize(v === "all" ? "all" : Number(v));
          }}
        >
          ${PAGE_SIZE_OPTIONS.map(
            (opt) => html`<option value=${String(opt)} ?selected=${opt === size}>${
              opt === "all" ? "All" : `${opt} / page`
            }</option>`
          )}
        </select>
      </div>
    `;
  }

  private _renderProtectCard(o: NetworkOverview) {
    const p = o.protect;
    if (!p.configured) return nothing;
    if (!p.reachable)
      return html`
        <div class="card">
          <h3>UniFi Protect</h3>
          <div class="muted" style="font-size:13px;">
            Configured but not reachable${p.error ? html` — ${p.error}` : ""}.
          </div>
        </div>
      `;
    return html`
      <div class="card">
        <h3>
          UniFi Protect
          <span class="muted" style="font-weight:400;font-size:12px;">
            —
            <span class="dot ${p.cameras_online === p.camera_count ? "good" : "bad"}"></span>
            ${p.cameras_online} / ${p.camera_count} cameras online
          </span>
        </h3>
        ${this._renderProtectDevices(p.cameras)}
      </div>
      ${this._renderProtectEvents(p)}
    `;
  }

  private _renderProtectDevices(cameras: ProtectCamera[]) {
    if (!cameras.length) return html`<div class="empty">No Protect devices reported.</div>`;
    const s = this._protectSort;
    const on = (n: SortState) => (this._protectSort = n);
    const rows = sortRows(cameras.slice(), s, {
      name: (c) => c.name,
      ip: (c) => c.ip,
      mac: (c) => c.mac,
      recording: (c) => c.is_recording,
      last_ring: (c) => c.last_ring,
      channels: (c) => c.channel_count,
    });
    return html`
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${sortableTh("Name", "name", s, on)}
              ${sortableTh("IP", "ip", s, on)}
              ${sortableTh("MAC", "mac", s, on)}
              ${sortableTh("Recording", "recording", s, on)}
              ${sortableTh("Last Ring", "last_ring", s, on)}
              ${sortableTh("Channels", "channels", s, on)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((c) => {
              // One scheme check serves both cells for this camera row.
              const link = safeExternalHref(c.link);
              return html`
                <tr>
                  <td>
                    <div style="font-weight:600;">
                      ${link
                        ? html`<a class="thumb-link" href=${link} target="_blank" rel="noopener"
                            >${c.name} ↗</a
                          >`
                        : c.name}
                    </div>
                    ${c.state
                      ? html`<div class="muted" style="font-size:11px;">${c.state.toLowerCase()}</div>`
                      : nothing}
                  </td>
                  <td class="mono">${c.ip ?? "—"}</td>
                  <td class="mono">${c.mac ?? "—"}</td>
                  <td>
                    ${c.is_recording == null
                      ? html`<span class="muted">—</span>`
                      : c.is_recording
                        ? html`<span class="dot bad"></span>Recording`
                        : html`<span class="muted">Off</span>`}
                  </td>
                  <td>${this._fmtLastSeen(c.last_ring)}</td>
                  <td title=${c.channels.join(", ")}>
                    ${c.channel_count
                      ? `${c.channel_count}${c.channels.length ? ` (${c.channels.join(", ")})` : ""}`
                      : "—"}
                  </td>
                  <td>
                    ${link
                      ? html`<a class="thumb-link" href=${link} target="_blank" rel="noopener">Open ↗</a>`
                      : nothing}
                  </td>
                </tr>
              `;
            })}
          </tbody>
        </table>
      </div>
      <div class="note">
        Device names link to that camera on the Protect console
        (<code>https://&lt;host&gt;/protect/dashboard/devices/&lt;id&gt;</code>).
      </div>
    `;
  }

  private _fmtDuration(seconds: number | null): string {
    if (seconds == null) return "—";
    if (seconds < 60) return `${seconds}s`;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    if (m < 60) return `${m}m ${s}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  }

  private _renderProtectEvents(p: NetworkOverview["protect"]) {
    return html`
      <div class="card">
        <h3>Events &amp; AI Smart Detections <span class="muted" style="font-weight:400;font-size:12px;">— last 24h</span></h3>
        ${p.events_error
          ? html`<div class="note" style="font-size:13px;">${p.events_error}</div>`
          : !p.events.length
            ? html`<div class="empty">No events in the last 24 hours.</div>`
            : html`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${sortableTh("Type", "type", this._eventSort, (n) => (this._eventSort = n))}
                        ${sortableTh("Smart Detections", "detections", this._eventSort, (n) => (this._eventSort = n))}
                        ${sortableTh("Score", "score", this._eventSort, (n) => (this._eventSort = n), { numeric: true })}
                        ${sortableTh("Start", "start", this._eventSort, (n) => (this._eventSort = n))}
                        ${sortableTh("Duration", "duration", this._eventSort, (n) => (this._eventSort = n), { numeric: true })}
                        <th>Thumbnail</th>
                        ${sortableTh("License Plate", "plate", this._eventSort, (n) => (this._eventSort = n))}
                      </tr>
                    </thead>
                    <tbody>
                      ${sortRows(p.events.slice(), this._eventSort, {
                        type: (e) => e.type,
                        detections: (e) => e.smart_detect_types.join(", ") || null,
                        score: (e) => e.score,
                        start: (e) => e.start,
                        duration: (e) => e.duration,
                        plate: (e) => e.license_plate,
                      }).map(
                        (e) => html`
                          <tr>
                            <td>${e.type ?? "—"}</td>
                            <td>
                              ${e.smart_detect_types.length
                                ? html`<span class="chips"
                                    >${e.smart_detect_types.map((t) => html`<span class="chip">${t}</span>`)}</span
                                  >`
                                : html`<span class="muted">—</span>`}
                            </td>
                            <td class="num">${e.score == null ? "—" : e.score}</td>
                            <td>${this._fmtLastSeen(e.start)}</td>
                            <td class="num">${this._fmtDuration(e.duration)}</td>
                            <td>
                              ${safeExternalHref(e.thumbnail_link)
                                ? html`<a
                                    class="thumb-link"
                                    href=${safeExternalHref(e.thumbnail_link)!}
                                    target="_blank"
                                    rel="noopener"
                                    >view ↗</a
                                  >`
                                : e.thumbnail
                                  ? html`<span class="muted" title="Thumbnail exists but needs an authenticated fetch">available</span>`
                                  : html`<span class="muted">—</span>`}
                            </td>
                            <td>${e.license_plate ? html`<span class="plate">${e.license_plate}</span>` : html`<span class="muted">—</span>`}</td>
                          </tr>
                        `
                      )}
                    </tbody>
                  </table>
                </div>
              `}
      </div>
    `;
  }
}
