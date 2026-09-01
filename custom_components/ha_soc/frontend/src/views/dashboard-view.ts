import { html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { SortState, sortRows, sortableTh } from "../sortable";
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

// Sort rank for the Issues table's Severity column. The key order of
// ISSUE_CATEGORY_LABELS already runs worst to mildest, so the index in
// that object is the rank; deriving it here means there is no second
// list that could drift out of sync with the labels.
const ISSUE_CATEGORY_RANK: Record<IntegrationIssueCategory, number> = Object.fromEntries(
  Object.keys(ISSUE_CATEGORY_LABELS).map((key, i) => [key, i])
) as Record<IntegrationIssueCategory, number>;

const DEVICE_PAGE_SIZE_OPTIONS: (number | "all")[] = [10, 20, 50, 100, "all"];
const INTEGRATION_PAGE_SIZE_OPTIONS: (number | "all")[] = [10, 20, 50, 100, "all"];

@customElement("ha-soc-dashboard-view")
export class HaSocDashboardView extends HaSocCustomizableView {
  protected get viewId() {
    return "dashboard";
  }
  static styles = [
    sharedStyles,
    css`
      h2.section-title {
        font-size: 18px;
        letter-spacing: -0.01em;
        color: var(--primary-text-color);
        margin: 30px 0 4px;
        font-weight: 650;
      }
      h2.section-title:first-child {
        margin-top: 0;
      }

      .row3 {
        display: grid;
        grid-template-columns: minmax(320px, 1.35fr) repeat(3, minmax(190px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .row2 {
        display: grid;
        grid-template-columns: minmax(0, 1.65fr) minmax(300px, 1fr);
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

      .section-subtitle {
        color: var(--secondary-text-color);
        font-size: 13px;
        line-height: 1.45;
        margin: 0 0 14px;
      }
      .command-grid {
        display: grid;
        grid-template-columns: minmax(280px, 0.85fr) minmax(0, 2fr);
        gap: 12px;
        margin-bottom: 12px;
      }
      .posture-card {
        margin: 0;
        border-left: 5px solid var(--status-critical);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 142px;
      }
      .posture-card.good {
        border-left-color: var(--status-good);
      }
      .posture-card.warning {
        border-left-color: var(--status-warning);
      }
      .posture-kicker,
      .metric-label {
        color: var(--secondary-text-color);
        font-size: 11px;
        font-weight: 650;
        letter-spacing: 0.055em;
        text-transform: uppercase;
      }
      .posture-main {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin: 8px 0 14px;
      }
      .posture-grade {
        font-size: 52px;
        font-weight: 750;
        letter-spacing: -0.045em;
        line-height: 0.9;
      }
      .posture-score {
        font-size: 18px;
        font-weight: 650;
      }
      .score-track,
      .severity-track,
      .mfa-track {
        height: 7px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09);
      }
      .score-fill,
      .mfa-fill {
        height: 100%;
        border-radius: inherit;
        background: var(--primary-color);
      }
      .priority-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(120px, 1fr));
        gap: 10px;
      }
      button.priority-item {
        appearance: none;
        font: inherit;
        color: var(--primary-text-color);
        text-align: left;
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color);
        border-radius: var(--ha-card-border-radius, 12px);
        padding: 15px;
        cursor: pointer;
        min-height: 142px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: border-color 0.12s ease, transform 0.12s ease;
      }
      button.priority-item:hover,
      button.priority-item:focus-visible {
        border-color: var(--primary-color);
        transform: translateY(-1px);
        outline: none;
      }
      .priority-value {
        font-size: 31px;
        font-weight: 720;
        line-height: 1;
        margin: 10px 0 5px;
        font-variant-numeric: tabular-nums;
      }
      .priority-value.critical {
        color: var(--status-critical);
      }
      .priority-value.warning {
        color: var(--status-serious);
      }
      .priority-help {
        color: var(--secondary-text-color);
        font-size: 11.5px;
        line-height: 1.35;
      }
      .summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .summary-grid > .card {
        margin: 0;
      }
      .card-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 14px;
      }
      .card-head h3 {
        margin: 0;
      }
      .metric-number {
        font-size: 34px;
        font-weight: 720;
        line-height: 1;
        letter-spacing: -0.025em;
        font-variant-numeric: tabular-nums;
      }
      .metric-context {
        color: var(--secondary-text-color);
        font-size: 12px;
        margin-top: 5px;
      }
      .severity-track {
        display: flex;
        margin: 16px 0 12px;
      }
      .severity-track > span {
        min-width: 2px;
      }
      .compact-legend {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 7px 12px;
        font-size: 12px;
      }
      .compact-legend .item {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .compact-legend .item strong {
        margin-left: auto;
        font-variant-numeric: tabular-nums;
      }
      .compact-legend .swatch {
        width: 8px;
        height: 8px;
        border-radius: 2px;
      }
      .identity-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
      }
      .identity-stat {
        border: 1px solid var(--divider-color);
        border-radius: 10px;
        padding: 12px;
      }
      .identity-stat .value {
        font-size: 24px;
        font-weight: 700;
        margin-top: 5px;
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
        border-top: 3px solid var(--status-warning);
      }
      .status-tile.unavailable {
        border-top: 3px solid var(--status-critical);
      }
      .status-tile.unavailable .value {
        color: var(--status-critical);
      }
      .status-tile.disabled {
        border-top: 3px solid var(--cat-other);
      }
      .status-tile.no_entities {
        border-top: 3px solid var(--primary-color);
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
        gap: 8px;
        margin-top: 8px;
      }
      .security-source-tile {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 9px 11px;
      }
      .security-source-tile .label {
        font-size: 12px;
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .security-source-tile .value {
        font-size: 18px;
        font-weight: 700;
      }
      .security-source-tile .sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      @media (max-width: 1100px) {
        .command-grid {
          grid-template-columns: 1fr;
        }
        .priority-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        button.priority-item {
          min-height: 116px;
        }
      }
      @media (max-width: 900px) {
        .summary-grid,
        .identity-grid {
          grid-template-columns: 1fr;
        }
      }
      @media (max-width: 560px) {
        .priority-grid {
          grid-template-columns: 1fr 1fr;
        }
        .status-tiles {
          grid-template-columns: repeat(2, 1fr);
        }
      }
    `,
  ];

  @state() private _summary: DashboardSummary | null = null;
  @state() private _deviceOverview: DeviceOverview | null = null;
  @state() private _integrationOverview: IntegrationOverview | null = null;
  @state() private _peripherals: PeripheralOverview | null = null;
  @state() private _security: SecurityOverview | null = null;
  @state() private _detections: Detection[] = [];
  @state() private _risk: Record<string, RiskResult> = {};
  @state() private _users: HaSocUser[] = [];
  @state() private _loading = true;
  // Non-null when the load failed: rendered as a distinct could-not-load
  // state carrying the server's message, never a blank dashboard (work
  // plan item 4.12).
  @state() private _error: string | null = null;
  @state() private _deviceSearch = "";
  @state() private _deviceStatusFilter: DeviceStatus | null = null;
  // Same default order the view has always had: riskiest devices first.
  @state() private _deviceSort: SortState | null = { key: "risk_score", dir: -1 };
  @state() private _devicePageSize: number | "all" = 10;
  @state() private _integrationSearch = "";
  @state() private _integrationSort: SortState | null = null;
  @state() private _integrationPageSize: number | "all" = 10;
  @state() private _detectionSort: SortState | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  updated(): void {
    this.classList.toggle("dark", !!this.hass?.themes?.darkMode);
  }

  private async _load() {
    this._loading = true;
    this._error = null;
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
    } catch (err: any) {
      // One rejected fetch fails the whole Promise.all; showing a partial
      // dashboard would misrepresent which numbers are current, so store
      // the server's message and render the could-not-load state.
      this._error = err?.message ?? String(err);
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

  private _onStatusTileClick(status: DeviceStatus) {
    this._deviceStatusFilter = this._deviceStatusFilter === status ? null : status;
    this.renderRoot.querySelector("#devices-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Accessors for sortRows on the All Devices table. Health sorts by the
  // STATUS_TILES order (healthiest first when ascending) rather than the
  // raw status string, so alphabetical accidents like "disabled" landing
  // between "available" and "unavailable" cannot happen. Severity is one
  // composite number so a single column orders by critical, then high,
  // then medium, then low; 1e9/1e6/1e3 spacing holds as long as no tier
  // count reaches 1000, far above anything a real scan produces.
  private static readonly DEVICE_SORT: Record<string, (r: DeviceOverviewRow) => unknown> = {
    status: (r) => STATUS_TILES.findIndex((t) => t.key === r.status),
    name: (r) => r.name,
    vendor: (r) => r.vendor,
    risk_score: (r) => r.risk_score,
    total_findings: (r) => r.total_findings,
    severity: (r) =>
      r.severity_counts.critical * 1e9 +
      r.severity_counts.high * 1e6 +
      r.severity_counts.medium * 1e3 +
      r.severity_counts.low,
  };

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
    return sortRows(filtered, this._deviceSort, HaSocDashboardView.DEVICE_SORT);
  }

  // Severity sorts by issue-category rank; sortRows is stable, so rows in
  // the same category keep the backend's error_count_24h desc order.
  private static readonly INTEGRATION_SORT: Record<string, (r: IntegrationIssueRow) => unknown> = {
    title: (r) => r.title,
    severity: (r) => ISSUE_CATEGORY_RANK[r.issue_category],
  };

  private _filteredIntegrations(): IntegrationIssueRow[] {
    const integrations = this._integrationOverview?.integrations ?? [];
    const q = this._integrationSearch.trim().toLowerCase();
    // With no sort chosen, the backend's error_count_24h desc order is
    // kept; filtering alone must not reorder rows.
    const filtered = q
      ? integrations.filter(
          (row) => row.title.toLowerCase().includes(q) || row.domain.toLowerCase().includes(q)
        )
      : integrations;
    return sortRows(filtered, this._integrationSort, HaSocDashboardView.INTEGRATION_SORT);
  }

  // Human labels for the posture terms named by missing_terms (work item
  // 3.4, D-10). An unknown term falls back to its raw id.
  private static readonly POSTURE_TERM_LABELS: Record<string, string> = {
    p_user: "user risk",
    p_vuln: "device vulnerabilities",
    p_misconfig: "misconfigurations",
    p_integration: "integration health",
    p_detection: "detections",
  };

  private _renderPostureCard() {
    const posture = this._summary?.posture;
    const summary = this._summary;
    const devices = this._deviceOverview;
    if (!posture || !summary || !devices) return nothing;
    const missing = (posture.missing_terms ?? []).map(
      (t) => HaSocDashboardView.POSTURE_TERM_LABELS[t] ?? t
    );
    const openDetections = this._detections.filter((det) => det.status === "open").length;
    const criticalVulnerabilities = devices.devices.reduce(
      (total, device) => total + device.severity_counts.critical,
      0
    );
    const unavailableDevices = devices.status_counts.unavailable ?? 0;
    const noMfa = summary.mfa_counts.disabled ?? 0;
    const scoreClass = posture.score >= 85 ? "good" : posture.score >= 70 ? "warning" : "critical";
    return html`
      <h2 class="section-title">Security command overview</h2>
      <p class="section-subtitle">The conditions most likely to require action, with direct paths to investigate them.</p>
      <div class="command-grid">
        <div class="card posture-card ${scoreClass}">
          <div>
            <div class="posture-kicker">Overall posture</div>
            <div class="posture-main">
              <div class="posture-grade">${posture.grade}</div>
              <div>
                <div class="posture-score">${posture.score} / 100</div>
                ${posture.provisional
                  ? html`<span class="tag cosmetic" title="Waiting on: ${missing.join(", ")}">provisional</span>`
                  : html`<span class="tag enforced">fully calculated</span>`}
              </div>
            </div>
          </div>
          <div class="score-track" aria-label="Posture score ${posture.score} out of 100">
            <div class="score-fill" style="width:${Math.max(0, Math.min(100, posture.score))}%"></div>
          </div>
        </div>
        <div class="priority-grid">
          <button class="priority-item" type="button" @click=${() => this._goto("audit")}>
            <span class="metric-label">Open detections</span>
            <span class="priority-value ${openDetections ? "critical" : ""}">${openDetections}</span>
            <span class="priority-help">Review active security signals</span>
          </button>
          <button class="priority-item" type="button" @click=${() => this._goto("scanner")}>
            <span class="metric-label">Critical CVEs</span>
            <span class="priority-value ${criticalVulnerabilities ? "critical" : ""}">${criticalVulnerabilities.toLocaleString()}</span>
            <span class="priority-help">Across inventoried devices</span>
          </button>
          <button class="priority-item" type="button" @click=${() => this._onStatusTileClick("unavailable")}>
            <span class="metric-label">Unavailable devices</span>
            <span class="priority-value ${unavailableDevices ? "warning" : ""}">${unavailableDevices}</span>
            <span class="priority-help">Filter the investigation queue</span>
          </button>
          <button class="priority-item" type="button" @click=${() => this._goto("users")}>
            <span class="metric-label">Accounts without MFA</span>
            <span class="priority-value ${noMfa ? "warning" : ""}">${noMfa}</span>
            <span class="priority-help">Close identity protection gaps</span>
          </button>
        </div>
      </div>
    `;
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
    if (this._loading) {
      return html`<div class="empty">Loading dashboard…</div>`;
    }
    if (this._error || !this._summary || !this._deviceOverview || !this._integrationOverview) {
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the dashboard</h3>
          <p style="font-size:13px;">
            ${this._error ?? "The server returned an incomplete dashboard payload."}
          </p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;
    }
    const s = this._summary;
    const d = this._deviceOverview;
    const integ = this._integrationOverview;
    // Accessors live inline because the User column sorts by the resolved
    // display name, which needs this._users, not by the raw user_id.
    const openDetections = sortRows(
      this._detections.filter((det) => det.status === "open"),
      this._detectionSort,
      {
        time: (det) => det.last_seen,
        rule: (det) => det.title,
        // Ranked so ascending reads worst first. "info" is not in
        // SEVERITY_ORDER, and indexOf's -1 would float it above
        // "critical"; it must sink below "low" instead.
        severity: (det) => {
          const i = SEVERITY_ORDER.indexOf(det.severity as (typeof SEVERITY_ORDER)[number]);
          return i === -1 ? SEVERITY_ORDER.length : i;
        },
        user: (det) => this._nameFor(det.user_id),
      }
    );
    const onDetectionSort = (next: SortState) => {
      this._detectionSort = next;
    };

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

    const entityCounts = s.entity_state_counts ?? { unavailable: 0, unknown: 0, total: 0 };
    const failedUnknownTotal = entityCounts.unavailable + entityCounts.unknown;

    const allFilteredDevices = this._sortedFilteredDevices();
    const shownDevices =
      this._devicePageSize === "all" ? allFilteredDevices : allFilteredDevices.slice(0, this._devicePageSize);
    // Both cards below truncate to the first N rows rather than paging, so
    // there is no page index to reset on a sort change; the slice always
    // shows the top of the new order.
    const onDeviceSort = (next: SortState) => {
      this._deviceSort = next;
    };
    const onIntegrationSort = (next: SortState) => {
      this._integrationSort = next;
    };

    const allFilteredIntegrations = this._filteredIntegrations();
    const shownIntegrations =
      this._integrationPageSize === "all"
        ? allFilteredIntegrations
        : allFilteredIntegrations.slice(0, this._integrationPageSize);

    const detSegments = [
      { key: "critical", color: "var(--status-critical)", value: s.detection_severity_counts.critical ?? 0 },
      { key: "high", color: "var(--status-serious)", value: s.detection_severity_counts.high ?? 0 },
      { key: "medium", color: "var(--status-warning)", value: s.detection_severity_counts.medium ?? 0 },
      { key: "low", color: "var(--status-good)", value: s.detection_severity_counts.low ?? 0 },
    ];

    const sections: LayoutSection[] = [
      {
        id: "posture_security",
        title: "Posture & Security",
        hideable: false,
        render: () => html`${this._renderPostureCard()} ${this._renderSecurityCard()}`,
      },
      {
        id: "device_vuln_overview",
        title: "Device & Vulnerability Overview",
        render: () => html`
      <h2 class="section-title">Exposure at a glance</h2>
      <p class="section-subtitle">Availability, vulnerability concentration, and entity reliability without the chart clutter.</p>
      <div class="summary-grid">
        <div class="card device-status-card">
          <div class="card-head">
            <div>
              <h3>Device availability</h3>
              <div class="metric-context">${d.devices.length.toLocaleString()} inventoried devices</div>
            </div>
          </div>
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
          <div class="card-head">
            <div>
              <h3>Vulnerability exposure</h3>
              <div class="metric-context">Weighted risk score ${d.combined_risk_score.toFixed(1)} / 10</div>
            </div>
            <div class="metric-number">${vulnTotal.toLocaleString()}</div>
          </div>
          <div class="severity-track" aria-label="Vulnerability findings by severity">
            ${vulnSegments.map(
              (seg) => html`<span style="width:${vulnTotal ? (seg.value / vulnTotal) * 100 : 0}%;background:${seg.color}"></span>`
            )}
          </div>
          <div class="compact-legend">
            ${vulnSegments.map(
              (seg) => html`
                <div class="item">
                  <span class="swatch" style="background:${seg.color}"></span>${seg.label}
                  <strong>${seg.value.toLocaleString()}</strong>
                </div>
              `
            )}
          </div>
        </div>

        <div class="card clickable" @click=${() => this._goto("entity_remap")} title="Fix broken entity references">
          <div class="card-head">
            <div>
              <h3>Entity reliability</h3>
              <div class="metric-context">Failed and unknown entity states</div>
            </div>
            <div class="metric-number">${failedUnknownTotal.toLocaleString()}</div>
          </div>
          <div class="identity-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));">
            <div class="identity-stat">
              <div class="metric-label">Unavailable</div>
              <div class="value" style="color:var(--status-critical)">${entityCounts.unavailable.toLocaleString()}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">Unknown</div>
              <div class="value" style="color:var(--status-warning)">${entityCounts.unknown.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>
        `,
      },
      {
        id: "users_detections",
        title: "Users & Detections",
        render: () => html`
      <h2 class="section-title">Identity and active detections</h2>
      <p class="section-subtitle">Account protection and the security signals that need review.</p>
      <div class="row2">
        <div class="card clickable" @click=${() => this._goto("users")} title="View users">
          <div class="card-head">
            <div>
              <h3>Identity protection</h3>
              <div class="metric-context">MFA adoption across eligible accounts</div>
            </div>
            <div class="metric-number">
              ${s.mfa_counts.enabled + s.mfa_counts.disabled > 0
                ? `${Math.round((s.mfa_counts.enabled / (s.mfa_counts.enabled + s.mfa_counts.disabled)) * 100)}%`
                : "—"}
            </div>
          </div>
          <div class="mfa-track" aria-label="MFA adoption">
            <div
              class="mfa-fill"
              style="width:${s.mfa_counts.enabled + s.mfa_counts.disabled > 0
                ? (s.mfa_counts.enabled / (s.mfa_counts.enabled + s.mfa_counts.disabled)) * 100
                : 0}%"
            ></div>
          </div>
          <div class="identity-grid" style="margin-top:14px;">
            <div class="identity-stat">
              <div class="metric-label">Users</div>
              <div class="value">${s.total_users_count}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">High / critical risk</div>
              <div class="value">${(s.risk_band_counts.high ?? 0) + (s.risk_band_counts.critical ?? 0)}</div>
            </div>
            <div class="identity-stat">
              <div class="metric-label">No MFA</div>
              <div class="value" style="color:var(--status-serious)">${s.mfa_counts.disabled}</div>
            </div>
          </div>
        </div>

        <div class="card clickable" @click=${() => this._goto("audit")} title="View audit / detections">
          <div class="card-head">
            <div>
              <h3>Detection coverage</h3>
              <div class="metric-context">${openDetections.length} currently open</div>
            </div>
            <div class="metric-number">${this._detections.length}</div>
          </div>
          <div class="severity-track" aria-label="Detections by severity">
            ${detSegments.map(
              (seg) => html`<span style="width:${this._detections.length ? (seg.value / this._detections.length) * 100 : 0}%;background:${seg.color}"></span>`
            )}
          </div>
          <div class="compact-legend">
            ${detSegments.map(
              (seg) => html`
                <div class="item">
                  <span class="swatch" style="background:${seg.color}"></span>${seg.key}
                  <strong>${seg.value}</strong>
                </div>
              `
            )}
          </div>
        </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <div>
            <h3>Active investigation queue</h3>
            <div class="metric-context">Open detections, newest activity first</div>
          </div>
        </div>
        ${!openDetections.length
          ? html`<div class="empty">No open detections. The active queue is clear.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    ${sortableTh("Time", "time", this._detectionSort, onDetectionSort)}
                    ${sortableTh("Rule", "rule", this._detectionSort, onDetectionSort)}
                    ${sortableTh("Severity", "severity", this._detectionSort, onDetectionSort)}
                    ${sortableTh("User", "user", this._detectionSort, onDetectionSort)}
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
        `,
      },
      {
        id: "devices_integrations",
        title: "Devices & Integrations",
        render: () => html`
      <h2 class="section-title">Investigation queues</h2>
      <p class="section-subtitle">The highest-risk devices and integration failures, sorted for triage.</p>
      <div class="row2">
        <div class="card" id="devices-card">
          <div class="card-head">
            <div>
              <h3>Highest-risk devices</h3>
              <div class="metric-context">Select a row to open the Home Assistant device record</div>
            </div>
          </div>
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
                        ${sortableTh("Health", "status", this._deviceSort, onDeviceSort)}
                        ${sortableTh("Device", "name", this._deviceSort, onDeviceSort)}
                        ${sortableTh("Vendor", "vendor", this._deviceSort, onDeviceSort)}
                        ${sortableTh("Risk Score", "risk_score", this._deviceSort, onDeviceSort, { numeric: true })}
                        ${sortableTh("Total", "total_findings", this._deviceSort, onDeviceSort, { numeric: true })}
                        ${sortableTh("Severity", "severity", this._deviceSort, onDeviceSort)}
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
                            <td>
                              <span
                                class="health-dot"
                                title=${device.status.replace("_", " ")}
                                aria-label=${device.status.replace("_", " ")}
                                style="background:${this._statusDotColor(device.status)}"
                              ></span>
                            </td>
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
          <div class="card-head">
            <div>
              <h3>Integration issues</h3>
              <div class="metric-context">Setup, credential, communication, and logging health</div>
            </div>
          </div>
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
                              ${sortableTh("Integration", "title", this._integrationSort, onIntegrationSort)}
                              ${sortableTh("Severity", "severity", this._integrationSort, onIntegrationSort)}
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
                                      ${row.error_count_24h
                                        ? html`<span class="num">${row.error_count_24h} error${row.error_count_24h === 1 ? "" : "s"}</span>`
                                        : nothing}
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
        `,
      },
    ];
    return this._renderSections(sections);
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
        <div class="card-head">
          <div>
            <h3>Security-source health</h3>
            <div class="metric-context">Locks, sirens, valves, and local peripherals</div>
          </div>
          ${sec.problem_count || sec.low_battery_count
            ? html`<span class="tag" style="background:rgba(219,68,55,0.15);color:var(--error-color,#db4437);">
                ${sec.problem_count} problem${sec.problem_count === 1 ? "" : "s"} · ${sec.low_battery_count} low battery
              </span>`
            : html`<span class="tag enforced">all clear</span>`}
        </div>
        <div class="security-health-grid">
          ${Object.entries(SECURITY_ENTITY_DOMAIN_LABELS)
            .filter(([domain]) => sec.sources_enabled[domain] ?? true)
            .map(([domain, label]) => {
              const rows = entitiesByDomain[domain] ?? [];
              const problemRows = rows.filter((r) => r.problem);
              const problems = problemRows.length;
              const lowBattery = rows.filter((r) => r.low_battery).length;
              // The tooltip names each problem entity with the server's
              // reason field, so "no state (integration not loaded)" is
              // distinguishable from a plain unavailable/jammed state
              // without leaving the tile (work plan item 4.5).
              const reasonLines = problemRows
                .slice(0, 8)
                .map((r) => `${r.entity_id}: ${r.reason ?? r.state ?? "problem"}`);
              if (problems > 8) reasonLines.push(`and ${problems - 8} more`);
              const tileTitle = rows.length
                ? [
                    `View ${label.toLowerCase()} in Home Assistant's Devices page`,
                    ...reasonLines,
                  ].join("\n")
                : "";
              return html`
                <div
                  class="security-source-tile ${rows.length ? "clickable" : ""}"
                  title=${tileTitle}
                  @click=${() => rows.length && navigateToHaPath(devicesForDomainPath(domain))}
                >
                  <div class="label">${label}</div>
                  <div class="value" style="color:${problems ? "var(--error-color,#db4437)" : "inherit"}">
                    ${problems}
                  </div>
                  <div class="sub">
                    ${rows.length} total${lowBattery ? `, ${lowBattery} low battery` : ""}
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
          ${p.total_count ? p.unassigned_count : 0}
        </div>
        <div class="sub">
          ${p.total_count ? `${p.total_count} total` : "no USB serial devices detected"}
        </div>
      </div>
    `;
  }
}
