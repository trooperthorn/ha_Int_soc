import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { navigate, navigateToHaPath, devicesForIntegrationPath } from "../nav";
import {
  NetworkOverview,
  NetworkClientRow,
  NetworkDeviceRow,
  UniFiBandwidth,
  fetchNetworkOverview,
} from "../data/ha-soc-ws";

const PAGE_SIZE_OPTIONS: (number | "all")[] = [25, 50, 100, "all"];

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
  @state() private _deviceSearch = "";
  @state() private _devicePage = 0;
  @state() private _devicePageSize: number | "all" = 25;

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
      ${this._renderClientsTable(o)} ${this._renderDevicesTable(o)} ${this._renderProtectCard(o)}
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

  private _renderSsid(o: NetworkOverview) {
    if (!o.clients_per_ssid.length) return nothing;
    const max = Math.max(...o.clients_per_ssid.map((s) => s.count), 1);
    return html`
      <div class="card">
        <h3>Clients per SSID</h3>
        <div class="ssid-list">
          ${o.clients_per_ssid.map(
            (s) => html`
              <div class="ssid-row">
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

  private _colHeaders(extra: { model?: boolean } = {}) {
    return html`
      <tr>
        <th>${extra.model ? "Device" : "Client"}</th>
        <th>IPv4</th>
        <th>IPv6</th>
        <th>MAC</th>
        <th class="num">VLAN</th>
        <th>SSID</th>
        ${extra.model ? html`<th>Model</th>` : nothing}
        <th class="num">Uptime</th>
        <th>Bandwidth</th>
        <th>Last Seen</th>
        <th>Integration</th>
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
    const filtered = this._filter(o.clients, this._clientSearch);
    const page = this._paginate(filtered, this._clientPage, this._clientPageSize);
    return html`
      <div class="card">
        <h3>Clients (${filtered.length})</h3>
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

  private _renderDevicesTable(o: NetworkOverview) {
    const filtered = this._filter(o.devices, this._deviceSearch);
    const page = this._paginate(filtered, this._devicePage, this._devicePageSize);
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
                    ${this._colHeaders({ model: true })}
                  </thead>
                  <tbody>
                    ${page.map((r) => this._renderRow(r, { model: true }))}
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
    return html`
      <div class="card">
        <h3>UniFi Protect</h3>
        ${!p.reachable
          ? html`<div class="muted" style="font-size:13px;">
              Configured but not reachable${p.error ? html` — ${p.error}` : ""}.
            </div>`
          : html`
              <div class="stat-row" style="margin-bottom:0;">
                <div class="stat-tile">
                  <div class="label">Cameras Online</div>
                  <div class="value">
                    <span class="dot ${p.cameras_online === p.camera_count ? "good" : "bad"}"></span>${
                      p.cameras_online
                    } / ${p.camera_count}
                  </div>
                </div>
              </div>
            `}
      </div>
    `;
  }
}
