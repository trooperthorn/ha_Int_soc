import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  navigate,
  navigateToHaPath,
  deviceDetailPath,
  devicesForIntegrationPath,
  devicesForDomainPath,
  SocTab,
} from "../nav";
import {
  DashboardSummary,
  Detection,
  RiskResult,
  HaSocUser,
  DeviceOverview,
  DeviceOverviewRow,
  DeviceStatus,
  IntegrationOverview,
  IntegrationIssueCategory,
  IntegrationIssueRow,
  PeripheralOverview,
  SecurityOverview,
  fetchDashboardSummary,
  fetchDashboardDevices,
  fetchDashboardIntegrations,
  fetchDetections,
  fetchRisk,
  fetchUsers,
  fetchPeripherals,
  fetchSecurityHealth,
  setDetectionStatus,
} from "../data/ha-soc-ws";

const SECURITY_ENTITY_DOMAIN_LABELS: Record<string, string> = {
  lock: "Locks",
  siren: "Sirens",
  valve: "Valves",
};

type DeviceSortKey = "name" | "vendor" | "risk_score" | "total_findings";

const STATUS_TILES: { key: DeviceStatus; label: string }[] = [
  { key: "available", label: "Available" },
  { key: "partial", label: "Partial" },
  { key: "unavailable", label: "Unavailable" },
  { key: "disabled", label: "Disabled" },
  { key: "no_entities", label: "No Entities" },
];

const SEVERITY_ORDER: (keyof DeviceOverviewRow["severity_counts"])[] = [
  "critical",
  "high",
  "medium",
  "low",
];

const ISSUE_CATEGORY_LABELS: Record<IntegrationIssueCategory, string> = {
  failing: "Failing",
  credential: "Credential issue",
  communication: "Communication issue",
  collection: "Collection issue",
  errors: "Logging errors",
  debug_logging: "Debug logging enabled",
  disabled: "Disabled",
};

// Issue category -> the same operational-status vocabulary the Device
// Status tiles above already use (available/partial/unavailable/
// disabled/no_entities), extended with "Warning" for the two categories
// that are informational rather than a functional failure. Every
// category short of "disabled" that actually stops the integration from
// working (a failed setup, bad credentials, no communication, or a
// device-collection ratio bad enough to flag) reads as Unavailable —
// deliberately not split into finer severities, since this project has
// no independent signal to rank them against each other and a false
// precision there would be worse than an honest, coarser bucket.
const ISSUE_STATUS: Record<IntegrationIssueCategory, { label: string; colorVar: string }> = {
  failing: { label: "Unavailable", colorVar: "var(--status-critical)" },
  credential: { label: "Unavailable", colorVar: "var(--status-critical)" },
  communication: { label: "Unavailable", colorVar: "var(--status-critical)" },
  collection: { label: "Unavailable", colorVar: "var(--status-critical)" },
  errors: { label: "Warning", colorVar: "var(--status-warning)" },
  debug_logging: { label: "Warning", colorVar: "var(--status-warning)" },
  disabled: { label: "Disabled", colorVar: "var(--cat-other)" },
};

const DEVICE_PAGE_SIZE_OPTIONS: (number | "all")[] = [20, 50, 100, "all"];
const INTEGRATION_PAGE_SIZE_OPTIONS: (number | "all")[] = [20, 50, 100, "all"];

@customElement("ha-soc-dashboard-view")
export class HaSocDashboardView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      h2.section-title {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--secondary-text-color);
        margin: 28px 0 12px;
        font-weight: 600;
      }
      h2.section-title:first-child {
        margin-top: 0;
      }

      .row3 {
        display: grid;
        grid-template-columns: 1.3fr 1fr 1fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }
      .row2 {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }
      .donuts-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      @media (max-width: 900px) {
        .row3,
        .row2,
        .donuts-row {
          grid-template-columns: 1fr;
        }
      }

      .clickable {
        cursor: pointer;
        transition: transform 0.08s ease, box-shadow 0.08s ease;
      }
      .clickable:hover {
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
        transform: translateY(-1px);
      }

      /* -- Status tiles -------------------------------------------------- */
      /* Stretches to fill whatever height row3's tallest sibling card
         (the donut / gauge cards) ends up at, rather than sizing to its
         own short content and leaving dead space below. */
      .device-status-card {
        display: flex;
        flex-direction: column;
      }
      .status-tiles {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        flex: 1;
      }
      .status-tile {
        border-radius: 10px;
        padding: 10px 6px;
        text-align: center;
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }
      .status-tile.active {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      .status-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        opacity: 0.85;
      }
      .status-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.3;
      }
      .status-tile.partial {
        background: var(--status-warning);
        color: #3a2900;
      }
      .status-tile.unavailable {
        background: var(--status-critical);
        color: #fff;
      }
      .status-tile.disabled {
        background: var(--cat-other);
        color: #fff;
      }
      .status-tile.no_entities {
        background: var(--primary-color);
        color: #fff;
      }

      .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        background: var(--primary-color);
        color: #fff;
        padding: 4px 10px;
        border-radius: 100px;
        cursor: pointer;
        margin-bottom: 10px;
      }

      /* -- Donut ----------------------------------------------------------- */
      .donut-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .donut {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        position: relative;
        flex: none;
      }
      .donut::after {
        content: "";
        position: absolute;
        inset: 22%;
        border-radius: 50%;
        background: var(--card-background-color, #fff);
      }
      .donut .center {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        z-index: 1;
      }
      .legend {
        font-size: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        flex: 1;
        min-width: 0;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .legend .sw {
        width: 9px;
        height: 9px;
        border-radius: 2px;
        flex: none;
      }
      .legend .val {
        margin-left: auto;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }

      /* -- Risk gauge ------------------------------------------------------ */
      .gauge-card .gauge-value {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 10px;
      }
      .gauge-track {
        position: relative;
        height: 12px;
        border-radius: 6px;
        background: linear-gradient(
          90deg,
          var(--status-good) 0%,
          var(--status-warning) 40%,
          var(--status-serious) 70%,
          var(--status-critical) 100%
        );
      }
      .gauge-marker {
        position: absolute;
        top: -10px;
        width: 0;
        height: 0;
        border-left: 7px solid transparent;
        border-right: 7px solid transparent;
        border-top: 9px solid var(--primary-text-color);
        transform: translateX(-50%);
      }
      .gauge-caption {
        margin-top: 10px;
        font-size: 11.5px;
        color: var(--secondary-text-color);
      }

      /* -- All Devices table --------------------------------------------------- */
      .devices-toolbar {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
      }
      .devices-toolbar input {
        flex: 1;
        font: inherit;
        font-size: 13px;
        padding: 7px 10px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }
      th.sortable {
        cursor: pointer;
        user-select: none;
      }
      th.sortable .arrow {
        opacity: 0.6;
        margin-left: 3px;
      }
      .health-dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
      }
      .sev-cell {
        display: inline-flex;
        gap: 8px;
        font-variant-numeric: tabular-nums;
        font-size: 11.5px;
      }
      .sev-cell span {
        display: inline-flex;
        align-items: center;
        gap: 3px;
      }
      .sev-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
      }

      /* -- All Devices pagination ------------------------------------------ */
      .devices-footer {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 10px;
        font-size: 12.5px;
        color: var(--secondary-text-color);
      }
      .devices-footer select {
        margin-left: auto;
      }

      /* -- Security Integrations Health card --------------------------------- */
      .security-health-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-top: 8px;
      }
      .security-source-tile {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 10px 12px;
      }
      .security-source-tile .label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .security-source-tile .value {
        font-size: 20px;
        font-weight: 700;
      }
      .security-source-tile .sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _summary: DashboardSummary | null = null;
  @state() private _deviceOverview: DeviceOverview | null = null;
  @state() private _integrationOverview: IntegrationOverview | null = null;
  @state() private _peripherals: PeripheralOverview | null = null;
  @state() private _security: SecurityOverview | null = null;
  @state() private _detections: Detection[] = [];
  @state() private _risk: Record<string, RiskResult> = {};
  @state() private _users: HaSocUser[] = [];
  @state() private _loading = true;
  @state() private _deviceSearch = "";
  @state() private _deviceStatusFilter: DeviceStatus | null = null;
  @state() private _deviceSort: { key: DeviceSortKey; dir: "asc" | "desc" } = {
    key: "risk_score",
    dir: "desc",
  };
  @state() private _devicePageSize: number | "all" = 20;
  @state() private _integrationSearch = "";
  @state() private _integrationPageSize: number | "all" = 20;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  updated(): void {
    this.classList.toggle("dark", !!this.hass?.themes?.darkMode);
  }

  private async _load() {
    this._loading = true;
    try {
      const [summary, deviceOverview, integrationOverview, peripherals, security, detections, risk, users] =
        await Promise.all([
          fetchDashboardSummary(this.hass),
          fetchDashboardDevices(this.hass),
          fetchDashboardIntegrations(this.hass),
          fetchPeripherals(this.hass),
          fetchSecurityHealth(this.hass),
          fetchDetections(this.hass),
          fetchRisk(this.hass),
          fetchUsers(this.hass),
        ]);
      this._summary = summary;
      this._deviceOverview = deviceOverview;
      this._integrationOverview = integrationOverview;
      this._peripherals = peripherals;
      this._security = security;
      this._detections = detections;
      this._risk = risk;
      this._users = users;
    } finally {
      this._loading = false;
    }
  }

  private async _onAck(id: string) {
    await setDetectionStatus(this.hass, id, "ack");
    await this._load();
  }

  private async _onResolve(id: string) {
    await setDetectionStatus(this.hass, id, "resolved");
    await this._load();
  }

  private _nameFor(userId: string | null): string {
    if (!userId) return "unknown";
    return this._users.find((u) => u.id === userId)?.name ?? userId;
  }

  private _goto(tab: SocTab) {
    navigate(this, tab);
  }

  private _donutGradient(segments: { color: string; value: number }[]): string {
    const total = segments.reduce((s, x) => s + x.value, 0) || 1;
    let acc = 0;
    const parts = segments.map((s) => {
      const start = (acc / total) * 100;
      acc += s.value;
      const end = (acc / total) * 100;
      return `${s.color} ${start}% ${end}%`;
    });
    return `conic-gradient(${parts.join(", ")})`;
  }

  private _onSort(key: DeviceSortKey) {
    this._deviceSort =
      this._deviceSort.key === key
        ? { key, dir: this._deviceSort.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "name" || key === "vendor" ? "asc" : "desc" };
  }

  private _onStatusTileClick(status: DeviceStatus) {
    this._deviceStatusFilter = this._deviceStatusFilter === status ? null : status;
    this.renderRoot.querySelector("#devices-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  private _sortedFilteredDevices(): DeviceOverviewRow[] {
    const devices = this._deviceOverview?.devices ?? [];
    const q = this._deviceSearch.trim().toLowerCase();
    const filtered = devices.filter((d) => {
      if (this._deviceStatusFilter && d.status !== this._deviceStatusFilter) return false;
      if (!q) return true;
      return (
        d.name.toLowerCase().includes(q) ||
        d.vendor.toLowerCase().includes(q) ||
        d.os.toLowerCase().includes(q)
      );
    });

    const { key, dir } = this._deviceSort;
    const sorted = [...filtered].sort((a, b) => {
      const av = a[key];
      const bv = b[key];
      const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
      return dir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }

  private _filteredIntegrations(): IntegrationIssueRow[] {
    const integrations = this._integrationOverview?.integrations ?? [];
    const q = this._integrationSearch.trim().toLowerCase();
    if (!q) return integrations;
    // Backend already sorts by error_count_24h desc — filtering preserves
    // that order rather than re-sorting, same as the search box above.
    return integrations.filter(
      (row) => row.title.toLowerCase().includes(q) || row.domain.toLowerCase().includes(q)
    );
  }

  private _statusDotColor(status: string): string {
    switch (status) {
      case "unavailable":
        return "var(--status-critical)";
      case "partial":
        return "var(--status-warning)";
      case "disabled":
        return "var(--cat-other)";
      case "no_entities":
        return "var(--primary-color)";
      default:
        return "var(--status-good)";
    }
  }

  render() {
    if (this._loading || !this._summary || !this._deviceOverview || !this._integrationOverview) {
      return html`<div class="empty">Loading dashboard…</div>`;
    }
    const s = this._summary;
    const d = this._deviceOverview;
    const integ = this._integrationOverview;
    const openDetections = this._detections.filter((det) => det.status === "open");

    const vulnSeverityTotals = d.devices.reduce(
      (acc, device) => {
        acc.critical += device.severity_counts.critical;
        acc.high += device.severity_counts.high;
        acc.medium += device.severity_counts.medium;
        acc.low += device.severity_counts.low;
        return acc;
      },
      { critical: 0, high: 0, medium: 0, low: 0 }
    );
    const vulnTotal =
      vulnSeverityTotals.critical + vulnSeverityTotals.high + vulnSeverityTotals.medium + vulnSeverityTotals.low;

    const vulnSegments = [
      { key: "critical", label: "Critical", color: "var(--status-critical)", value: vulnSeverityTotals.critical },
      { key: "high", label: "High", color: "var(--status-serious)", value: vulnSeverityTotals.high },
      { key: "medium", label: "Medium", color: "var(--status-warning)", value: vulnSeverityTotals.medium },
      { key: "low", label: "Low", color: "var(--status-good)", value: vulnSeverityTotals.low },
    ];

    const riskGaugePercent = Math.max(0, Math.min(100, (d.combined_risk_score / 10) * 100));

    const entityCounts = s.entity_state_counts ?? { unavailable: 0, unknown: 0, total: 0 };
    const failedUnknownTotal = entityCounts.unavailable + entityCounts.unknown;
    const failedUnknownSegments = [
      { key: "unavailable", label: "Failed (unavailable)", color: "var(--status-critical)", value: entityCounts.unavailable },
      { key: "unknown", label: "Unknown", color: "var(--status-warning)", value: entityCounts.unknown },
    ];

    const allFilteredDevices = this._sortedFilteredDevices();
    const shownDevices =
      this._devicePageSize === "all" ? allFilteredDevices : allFilteredDevices.slice(0, this._devicePageSize);

    const allFilteredIntegrations = this._filteredIntegrations();
    const shownIntegrations =
      this._integrationPageSize === "all"
        ? allFilteredIntegrations
        : allFilteredIntegrations.slice(0, this._integrationPageSize);

    const riskSegments = [
      { key: "low", color: "var(--status-good)", value: s.risk_band_counts.low ?? 0 },
      { key: "moderate", color: "var(--status-warning)", value: s.risk_band_counts.moderate ?? 0 },
      { key: "high", color: "var(--status-serious)", value: s.risk_band_counts.high ?? 0 },
      { key: "critical", color: "var(--status-critical)", value: s.risk_band_counts.critical ?? 0 },
    ];
    const mfaSegments = [
      { key: "enabled", color: "var(--cat-1)", value: s.mfa_counts.enabled },
      { key: "disabled", color: "var(--cat-2)", value: s.mfa_counts.disabled },
    ];
    const detSegments = [
      { key: "critical", color: "var(--status-critical)", value: s.detection_severity_counts.critical ?? 0 },
      { key: "high", color: "var(--status-serious)", value: s.detection_severity_counts.high ?? 0 },
      { key: "medium", color: "var(--status-warning)", value: s.detection_severity_counts.medium ?? 0 },
      { key: "low", color: "var(--status-good)", value: s.detection_severity_counts.low ?? 0 },
    ];

    return html`
      ${this._renderSecurityCard()}

      <h2 class="section-title">Device &amp; Vulnerability Overview</h2>
      <div class="row3">
        <div class="card device-status-card">
          <h3>Device Status</h3>
          <div class="status-tiles">
            ${STATUS_TILES.map(
              (t) => html`
                <div
                  class="status-tile clickable ${t.key} ${this._deviceStatusFilter === t.key ? "active" : ""}"
                  title="Filter the devices table below"
                  @click=${() => this._onStatusTileClick(t.key)}
                >
                  <div class="label">${t.label}</div>
                  <div class="value">${d.status_counts[t.key] ?? 0}</div>
                </div>
              `
            )}
          </div>
        </div>

        <div class="card clickable" @click=${() => this._goto("scanner")} title="View vulnerability findings">
          <h3>Vulnerability Count by Severity</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(vulnSegments)}">
              <div class="center">${vulnTotal.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${vulnSegments.map(
                (seg) => html`
                  <div class="row">
                    <span class="sw" style="background:${seg.color}"></span>${seg.label}
                    <span class="val">${seg.value.toLocaleString()}</span>
                  </div>
                `
              )}
            </div>
          </div>
        </div>

        <div class="card gauge-card clickable" @click=${() => this._goto("scanner")} title="View vulnerability findings">
          <h3>Risk Score</h3>
          <div class="gauge-value">${d.combined_risk_score.toFixed(1)}</div>
          <div class="gauge-track">
            <div class="gauge-marker" style="left:${riskGaugePercent}%"></div>
          </div>
          <div class="gauge-caption">
            Combined risk score of all devices — weighted so higher-severity CVEs count more.
          </div>
        </div>

        <div class="card clickable" @click=${() => this._goto("entity_remap")} title="Fix broken entity references">
          <h3>Failed / Unknown Entities</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(failedUnknownSegments)}">
              <div class="center">${failedUnknownTotal.toLocaleString()}</div>
            </div>
            <div class="legend">
              ${failedUnknownSegments.map(
                (seg) => html`
                  <div class="row">
                    <span class="sw" style="background:${seg.color}"></span>${seg.label}
                    <span class="val">${seg.value.toLocaleString()}</span>
                  </div>
                `
              )}
            </div>
          </div>
        </div>
      </div>

      <h2 class="section-title">Users &amp; Detections</h2>
      <div class="donuts-row">
        <div class="card clickable" @click=${() => this._goto("users")} title="View users">
          <h3>Users by Risk Band</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(riskSegments)}">
              <div class="center">${s.total_users_count}</div>
            </div>
            <div class="legend">
              ${riskSegments.map(
                (seg) => html`
                  <div class="row">
                    <span class="sw" style="background:${seg.color}"></span>${seg.key}
                    <span class="val">${seg.value}</span>
                  </div>
                `
              )}
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${() => this._goto("users")} title="View users">
          <h3>MFA Adoption</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(mfaSegments)}">
              <div class="center">
                ${s.mfa_counts.enabled + s.mfa_counts.disabled > 0
                  ? `${Math.round((s.mfa_counts.enabled / (s.mfa_counts.enabled + s.mfa_counts.disabled)) * 100)}%`
                  : "—"}
              </div>
            </div>
            <div class="legend">
              <div class="row"><span class="sw" style="background:var(--cat-1)"></span>Enabled<span class="val">${s.mfa_counts.enabled}</span></div>
              <div class="row"><span class="sw" style="background:var(--cat-2)"></span>No MFA<span class="val">${s.mfa_counts.disabled}</span></div>
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${() => this._goto("audit")} title="View audit / detections">
          <h3>Detections by Severity</h3>
          <div class="donut-wrap">
            <div class="donut" style="background:${this._donutGradient(detSegments)}">
              <div class="center">${this._detections.length}</div>
            </div>
            <div class="legend">
              ${detSegments.map(
                (seg) => html`
                  <div class="row">
                    <span class="sw" style="background:${seg.color}"></span>${seg.key}
                    <span class="val">${seg.value}</span>
                  </div>
                `
              )}
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Recent suspicious activity</h3>
        ${!openDetections.length
          ? html`<div class="empty">No open detections.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Rule</th>
                    <th>Severity</th>
                    <th>User</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${openDetections.map(
                    (det) => html`
                      <tr>
                        <td>${new Date(det.last_seen).toLocaleString()}</td>
                        <td>${det.title}</td>
                        <td><span class="pill ${det.severity}"><span class="dot"></span>${det.severity}</span></td>
                        <td>${this._nameFor(det.user_id)}</td>
                        <td>
                          <button class="ha-btn" @click=${() => this._onAck(det.id)}>Ack</button>
                          <button class="ha-btn" @click=${() => this._onResolve(det.id)}>Resolve</button>
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      <h2 class="section-title">Devices &amp; Integrations</h2>
      <div class="row2">
        <div class="card" id="devices-card">
          <h3>All Devices</h3>
          ${this._deviceStatusFilter
            ? html`
                <div class="filter-chip" @click=${() => (this._deviceStatusFilter = null)}>
                  ${STATUS_TILES.find((t) => t.key === this._deviceStatusFilter)?.label} ✕
                </div>
              `
            : nothing}
          <div class="devices-toolbar">
            <input
              type="text"
              placeholder="Search devices…"
              .value=${this._deviceSearch}
              @input=${(e: Event) => (this._deviceSearch = (e.target as HTMLInputElement).value)}
            />
          </div>
          ${allFilteredDevices.length === 0
            ? html`<div class="empty">No devices found.</div>`
            : html`
                <div style="overflow-x:auto;">
                  <table>
                    <thead>
                      <tr>
                        <th>Health</th>
                        <th class="sortable" @click=${() => this._onSort("name")}>
                          Device${this._sortArrow("name")}
                        </th>
                        <th class="sortable" @click=${() => this._onSort("vendor")}>
                          Vendor${this._sortArrow("vendor")}
                        </th>
                        <th class="sortable" @click=${() => this._onSort("risk_score")}>
                          Risk Score${this._sortArrow("risk_score")}
                        </th>
                        <th class="sortable" @click=${() => this._onSort("total_findings")}>
                          Total${this._sortArrow("total_findings")}
                        </th>
                        <th>Severity</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${shownDevices.map(
                        (device) => html`
                          <tr
                            class="clickable"
                            title="Open in Home Assistant's Devices page"
                            @click=${() => navigateToHaPath(deviceDetailPath(device.device_id))}
                          >
                            <td><span class="health-dot" style="background:${this._statusDotColor(device.status)}"></span></td>
                            <td>${device.name}</td>
                            <td class="muted">${device.vendor}</td>
                            <td class="num">${device.risk_score.toFixed(1)}</td>
                            <td class="num">${device.total_findings}</td>
                            <td>
                              <span class="sev-cell">
                                ${SEVERITY_ORDER.map(
                                  (sev) => html`
                                    <span>
                                      <span
                                        class="sev-dot"
                                        style="background:${sev === "critical"
                                          ? "var(--status-critical)"
                                          : sev === "high"
                                          ? "var(--status-serious)"
                                          : sev === "medium"
                                          ? "var(--status-warning)"
                                          : "var(--status-good)"}"
                                      ></span
                                      >${device.severity_counts[sev]}
                                    </span>
                                  `
                                )}
                              </span>
                            </td>
                          </tr>
                        `
                      )}
                    </tbody>
                  </table>
                </div>
                <div class="devices-footer">
                  <span
                    >Showing ${shownDevices.length} of ${allFilteredDevices.length} device${allFilteredDevices.length === 1 ? "" : "s"}</span
                  >
                  <select
                    .value=${String(this._devicePageSize)}
                    @change=${(e: Event) => {
                      const v = (e.target as HTMLSelectElement).value;
                      this._devicePageSize = v === "all" ? "all" : Number(v);
                    }}
                  >
                    ${DEVICE_PAGE_SIZE_OPTIONS.map(
                      (opt) => html`
                        <option value=${String(opt)} ?selected=${opt === this._devicePageSize}>
                          ${opt === "all" ? "Show all" : `Show ${opt}`}
                        </option>
                      `
                    )}
                  </select>
                </div>
              `}
        </div>

        <div class="card">
          <h3>Issues by Integration</h3>
          ${integ.integrations.length === 0
            ? html`<div class="empty">No integration issues detected.</div>`
            : html`
                <div class="devices-toolbar">
                  <input
                    type="text"
                    placeholder="Search integrations…"
                    .value=${this._integrationSearch}
                    @input=${(e: Event) => (this._integrationSearch = (e.target as HTMLInputElement).value)}
                  />
                </div>
                ${allFilteredIntegrations.length === 0
                  ? html`<div class="empty">No integration matches "${this._integrationSearch}".</div>`
                  : html`
                      <div style="overflow-x:auto;">
                        <table>
                          <thead>
                            <tr>
                              <th>Integration</th>
                              <th>Severity</th>
                            </tr>
                          </thead>
                          <tbody>
                            ${shownIntegrations.map((row) => {
                              const status = ISSUE_STATUS[row.issue_category];
                              return html`
                                <tr
                                  class="clickable"
                                  title="${row.title} — ${ISSUE_CATEGORY_LABELS[row.issue_category]}. Open in Home Assistant's Devices page"
                                  @click=${() => navigateToHaPath(devicesForIntegrationPath(row.entry_id))}
                                >
                                  <td>${row.title}</td>
                                  <td>
                                    <span class="sev-cell">
                                      <span class="sev-dot" style="background:${status.colorVar}"></span>
                                      ${status.label}
                                      <span class="num">${row.error_count_24h}</span>
                                    </span>
                                  </td>
                                </tr>
                              `;
                            })}
                          </tbody>
                        </table>
                      </div>
                      <div class="devices-footer">
                        <span
                          >Showing ${shownIntegrations.length} of ${allFilteredIntegrations.length} integration${allFilteredIntegrations.length === 1 ? "" : "s"}</span
                        >
                        <select
                          .value=${String(this._integrationPageSize)}
                          @change=${(e: Event) => {
                            const v = (e.target as HTMLSelectElement).value;
                            this._integrationPageSize = v === "all" ? "all" : Number(v);
                          }}
                        >
                          ${INTEGRATION_PAGE_SIZE_OPTIONS.map(
                            (opt) => html`
                              <option value=${String(opt)} ?selected=${opt === this._integrationPageSize}>
                                ${opt === "all" ? "Show all" : `Show ${opt}`}
                              </option>
                            `
                          )}
                        </select>
                      </div>
                    `}
              `}
        </div>
      </div>
    `;
  }

  private _sortArrow(key: DeviceSortKey) {
    if (this._deviceSort.key !== key) return nothing;
    return html`<span class="arrow">${this._deviceSort.dir === "asc" ? "▲" : "▼"}</span>`;
  }

  private _renderSecurityCard() {
    const sec = this._security;
    if (!sec) return nothing;

    const entitiesByDomain: Record<string, typeof sec.entities> = {};
    for (const e of sec.entities) {
      (entitiesByDomain[e.domain] ??= []).push(e);
    }

    return html`
      <div class="card">
        <h3>
          Security Integrations Health
          ${sec.problem_count || sec.low_battery_count
            ? html`<span class="tag" style="background:rgba(219,68,55,0.15);color:var(--error-color,#db4437);">
                ${sec.problem_count} problem${sec.problem_count === 1 ? "" : "s"}, ${sec.low_battery_count} low
                battery
              </span>`
            : html`<span class="tag enforced">all clear</span>`}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every lock/siren/valve entity regardless of integration, plus local USB/serial
          peripherals. The curated security-integration health list (Kidde, Elk-M1, UniFi
          Protect, Keymaster, Emporia Vue) moved to Settings — configurable there too.
        </p>
        <div class="security-health-grid">
          ${Object.entries(SECURITY_ENTITY_DOMAIN_LABELS)
            .filter(([domain]) => sec.sources_enabled[domain] ?? true)
            .map(([domain, label]) => {
              const rows = entitiesByDomain[domain] ?? [];
              const problems = rows.filter((r) => r.problem).length;
              const lowBattery = rows.filter((r) => r.low_battery).length;
              return html`
                <div
                  class="security-source-tile ${rows.length ? "clickable" : ""}"
                  title=${rows.length ? `View ${label.toLowerCase()} in Home Assistant's Devices page` : ""}
                  @click=${() => rows.length && navigateToHaPath(devicesForDomainPath(domain))}
                >
                  <div class="label">${label}</div>
                  <div class="value" style="color:${problems ? "var(--error-color,#db4437)" : "inherit"}">
                    ${rows.length}
                  </div>
                  <div class="sub">
                    ${problems ? `${problems} problem${problems === 1 ? "" : "s"}` : "none reporting a problem"}${lowBattery ? `, ${lowBattery} low battery` : ""}
                  </div>
                </div>
              `;
            })}
          ${this._renderPeripheralsTile()}
        </div>
      </div>
    `;
  }

  private _renderPeripheralsTile() {
    const p = this._peripherals;
    if (!p || !p.available) return nothing;

    return html`
      <div
        class="security-source-tile clickable"
        title="View Local Peripherals"
        @click=${() => this._goto("peripherals")}
      >
        <div class="label">Local Peripherals</div>
        <div class="value" style="color:${p.unassigned_count ? "var(--status-warning)" : "inherit"}">
          ${p.total_count}
        </div>
        <div class="sub">
          ${p.total_count
            ? p.unassigned_count
              ? `${p.unassigned_count} unassigned`
              : "none unassigned"
            : "no USB serial devices detected"}
        </div>
      </div>
    `;
  }
}
