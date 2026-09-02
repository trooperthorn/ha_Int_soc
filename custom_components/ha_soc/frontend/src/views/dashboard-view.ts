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
      @container (max-width: 900px) {
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
      .overview-heading {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 16px;
      }
      .overview-heading .section-subtitle {
        margin-bottom: 0;
      }
      .overview-heading h2.section-title {
        margin-top: 0;
      }
      .overview-state {
        flex: 0 0 auto;
        padding: 6px 11px;
        border: 1px solid var(--soc-border);
        border-radius: 999px;
        color: var(--soc-text-muted);
        background: var(--soc-surface);
        font-size: 11.5px;
        white-space: nowrap;
      }
      .overview-kpis {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 12px;
      }
      .overview-kpi {
        appearance: none;
        min-width: 0;
        min-height: 126px;
        padding: 16px;
        border: 1px solid var(--soc-border);
        border-radius: var(--soc-card-radius);
        background: var(--soc-surface);
        color: var(--soc-text);
        font: inherit;
        text-align: left;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      button.overview-kpi {
        cursor: pointer;
      }
      button.overview-kpi:hover,
      button.overview-kpi:focus-visible {
        border-color: var(--primary-color);
        outline: none;
      }
      .overview-kpi-value {
        display: block;
        margin: 10px 0 4px;
        font-size: 34px;
        font-weight: 720;
        line-height: 1;
        font-variant-numeric: tabular-nums;
      }
      .overview-kpi-context {
        color: var(--secondary-text-color);
        font-size: 11.5px;
        line-height: 1.35;
      }
      .overview-visuals {
        display: grid;
        grid-template-columns: minmax(280px, 0.8fr) minmax(0, 1.7fr);
        gap: 12px;
        margin-bottom: 16px;
      }
      .overview-card {
        margin-bottom: 12px;
      }
      .posture-visual-card,
      .trend-card {
        margin: 0;
      }
      .posture-ring-wrap {
        display: grid;
        grid-template-columns: 132px minmax(0, 1fr);
        align-items: center;
        gap: 16px;
      }
      .posture-ring {
        width: 126px;
        aspect-ratio: 1;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: conic-gradient(
          var(--posture-color) 0 var(--posture-angle),
          rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09) var(--posture-angle) 360deg
        );
        position: relative;
      }
      .posture-ring::before {
        content: "";
        position: absolute;
        inset: 13px;
        border-radius: 50%;
        background: var(--soc-surface);
      }
      .posture-ring-value {
        position: relative;
        z-index: 1;
        text-align: center;
      }
      .posture-ring-value strong {
        display: block;
        font-size: 32px;
        line-height: 1;
      }
      .posture-ring-value span {
        display: block;
        margin-top: 4px;
        color: var(--secondary-text-color);
        font-size: 11px;
      }
      .posture-grade-line {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 8px;
      }
      .posture-description {
        color: var(--secondary-text-color);
        font-size: 12px;
        line-height: 1.45;
      }
      .posture-trend {
        width: 100%;
        height: 142px;
        display: block;
      }
      .posture-trend .grid-line {
        stroke: var(--divider-color);
        stroke-width: 1;
      }
      .posture-trend .trend-area {
        fill: rgba(var(--rgb-primary-color, 3, 155, 229), 0.14);
      }
      .posture-trend .trend-line {
        fill: none;
        stroke: var(--primary-color);
        stroke-width: 3;
        stroke-linecap: round;
        stroke-linejoin: round;
      }
      .posture-trend text {
        fill: var(--secondary-text-color);
        font-size: 10px;
      }
      .metric-label {
        color: var(--secondary-text-color);
        font-size: 11px;
        font-weight: 650;
        letter-spacing: 0.055em;
        text-transform: uppercase;
      }
      .severity-track,
      .mfa-track {
        height: 7px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09);
      }
      .mfa-fill {
        height: 100%;
        border-radius: inherit;
        background: var(--primary-color);
      }
      .summary-grid {
        display: grid;
        grid-template-columns: minmax(420px, 1.5fr) repeat(2, minmax(240px, 1fr));
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
      .donut-layout {
        display: grid;
        grid-template-columns: 126px minmax(0, 1fr);
        gap: 15px;
        align-items: center;
      }
      .donut-layout .compact-legend {
        grid-template-columns: 1fr;
      }
      .severity-donut {
        width: 126px;
        aspect-ratio: 1;
        border-radius: 50%;
        display: grid;
        place-items: center;
        position: relative;
      }
      .severity-donut::before {
        content: "";
        position: absolute;
        inset: 16px;
        border-radius: 50%;
        background: var(--soc-surface);
      }
      .severity-donut strong {
        position: relative;
        z-index: 1;
        font-size: 28px;
        font-variant-numeric: tabular-nums;
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
        text-align: left;
        background: var(--soc-surface-subtle);
        border: 1px solid transparent;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: center;
        gap: 6px;
      }
      .status-tile.active {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      .status-tile .label {
        font-size: 11.5px;
        font-weight: 600;
        opacity: 0.85;
      }
      .status-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.3;
      }
      .status-tile.available {
        background: rgba(12, 163, 12, 0.11);
        color: var(--status-good);
      }
      .priority-table-wrap {
        overflow-x: auto;
      }
      .priority-table-wrap table {
        min-width: 680px;
      }
      .priority-actions {
        display: flex;
        gap: 6px;
        white-space: nowrap;
      }
      .status-tile.partial {
        background: rgba(250, 178, 25, 0.15);
        color: var(--status-warning);
      }
      .status-tile.unavailable {
        background: rgba(208, 59, 59, 0.12);
        color: var(--status-critical);
      }
      .status-tile.no_entities {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.09);
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
      @container (max-width: 1100px) {
        .overview-kpis {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .overview-visuals {
          grid-template-columns: 1fr;
        }
      }
      @container (max-width: 900px) {
        .summary-grid,
        .identity-grid {
          grid-template-columns: 1fr;
        }
      }
      @container (max-width: 560px) {
        .overview-heading {
          display: block;
        }
        .overview-state {
          display: inline-flex;
          margin-top: 10px;
        }
        .overview-kpis {
          grid-template-columns: 1fr;
        }
        .posture-ring-wrap,
        .donut-layout {
          grid-template-columns: 1fr;
          justify-items: center;
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

  private _postureTrendGeometry(history: DashboardSummary["posture_history"], currentScore: number) {
    const samples = history
      .filter((item) => Number.isFinite(item.score))
      .map((item) => ({ ...item, score: Math.max(0, Math.min(100, item.score)) }));
    if (!samples.length) {
      samples.push({ date: "Current", score: currentScore, grade: this._summary?.posture.grade ?? "—" });
    }
    if (samples.length === 1) samples.push({ ...samples[0], date: "Current" });

    const scores = samples.map((item) => item.score);
    let minScore = Math.max(0, Math.min(...scores) - 4);
    let maxScore = Math.min(100, Math.max(...scores) + 4);
    if (maxScore <= minScore) {
      minScore = Math.max(0, minScore - 1);
      maxScore = Math.min(100, maxScore + 1);
    }

    const left = 12;
    const right = 548;
    const top = 12;
    const bottom = 118;
    const xFor = (index: number) => left + (index / (samples.length - 1)) * (right - left);
    const yFor = (score: number) => bottom - ((score - minScore) / (maxScore - minScore)) * (bottom - top);
    const points = samples.map((item, index) => `${xFor(index).toFixed(1)},${yFor(item.score).toFixed(1)}`).join(" ");
    const area = `${left},${bottom} ${points} ${right},${bottom}`;
    const formatDate = (value: string) => {
      // Posture history stores a local calendar date (YYYY-MM-DD), not a
      // UTC timestamp. Parsing that form directly with new Date(value)
      // treats it as UTC and can display the previous day west of UTC.
      const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
      const parsed = dateOnly
        ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]))
        : new Date(value);
      return Number.isNaN(parsed.getTime())
        ? value
        : parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    };
    return {
      points,
      area,
      firstLabel: formatDate(samples[0].date),
      lastLabel: formatDate(samples[samples.length - 1].date),
      delta: samples[samples.length - 1].score - samples[0].score,
    };
  }

  private _renderReferenceOverview() {
    const posture = this._summary?.posture;
    const summary = this._summary;
    const devices = this._deviceOverview;
    if (!posture || !summary || !devices) return nothing;

    const missing = (posture.missing_terms ?? []).map(
      (term) => HaSocDashboardView.POSTURE_TERM_LABELS[term] ?? term
    );
    const openDetections = this._detections
      .filter((detection) => detection.status === "open")
      .sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime());
    const highPriorityDetections = openDetections.filter(
      (detection) => detection.severity === "critical" || detection.severity === "high"
    ).length;
    const criticalHighFindings = devices.devices.reduce(
      (total, device) => total + device.severity_counts.critical + device.severity_counts.high,
      0
    );
    const severity = devices.devices.reduce(
      (counts, device) => {
        counts.critical += device.severity_counts.critical;
        counts.high += device.severity_counts.high;
        counts.medium += device.severity_counts.medium;
        counts.low += device.severity_counts.low;
        return counts;
      },
      { critical: 0, high: 0, medium: 0, low: 0 }
    );
    const findingTotal = severity.critical + severity.high + severity.medium + severity.low;
    const findingSegments = [
      { label: "Critical", color: "var(--status-critical)", value: severity.critical },
      { label: "High", color: "var(--status-serious)", value: severity.high },
      { label: "Medium", color: "var(--status-warning)", value: severity.medium },
      { label: "Low", color: "var(--cat-1)", value: severity.low },
    ];
    let findingCursor = 0;
    const findingStops = findingSegments.map((segment) => {
      const start = findingCursor;
      findingCursor += findingTotal ? (segment.value / findingTotal) * 100 : 0;
      return `${segment.color} ${start}% ${findingCursor}%`;
    });
    const findingDonut = findingTotal
      ? `conic-gradient(${findingStops.join(", ")})`
      : "rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.09)";
    const sourceStates = Object.values(this._security?.sources_enabled ?? {});
    const enabledSources = sourceStates.filter(Boolean).length;
    const sourceTotal = sourceStates.length;
    const scoreClass = posture.score >= 85 ? "good" : posture.score >= 70 ? "warning" : "critical";
    const postureColor =
      scoreClass === "good"
        ? "var(--status-good)"
        : scoreClass === "warning"
        ? "var(--status-warning)"
        : "var(--status-critical)";
    const trend = this._postureTrendGeometry(summary.posture_history, posture.score);
    const trendDelta = `${trend.delta >= 0 ? "+" : ""}${trend.delta.toFixed(0)}`;

    return html`
      <div class="overview-heading">
        <div>
          <h2 class="section-title">Security overview</h2>
          <p class="section-subtitle">What needs attention now, with operational health kept separate from risk.</p>
        </div>
        <span class="overview-state">${posture.provisional ? "Provisional posture" : "Live protected data"}</span>
      </div>

      <div class="overview-kpis">
        <div class="overview-kpi">
          <span class="metric-label">Posture score</span>
          <span class="overview-kpi-value">${posture.score}</span>
          <span class="overview-kpi-context">Grade ${posture.grade}${posture.provisional ? " · provisional" : " · stable"}</span>
        </div>
        <button class="overview-kpi" type="button" @click=${() => this._goto("audit")}>
          <span class="metric-label">Open detections</span>
          <span class="overview-kpi-value" style="color:${openDetections.length ? "var(--status-critical)" : "inherit"}">${openDetections.length}</span>
          <span class="overview-kpi-context">${highPriorityDetections} high priority</span>
        </button>
        <button class="overview-kpi" type="button" @click=${() => this._goto("scanner")}>
          <span class="metric-label">Critical / high findings</span>
          <span class="overview-kpi-value" style="color:${criticalHighFindings ? "var(--status-serious)" : "inherit"}">${criticalHighFindings.toLocaleString()}</span>
          <span class="overview-kpi-context">Across ${devices.devices.length.toLocaleString()} assets</span>
        </button>
        <div class="overview-kpi">
          <span class="metric-label">Telemetry sources</span>
          <span class="overview-kpi-value">${enabledSources} / ${sourceTotal}</span>
          <span class="overview-kpi-context">${sourceTotal ? "Configured source categories" : "No source categories configured"}</span>
        </div>
      </div>

      <div class="card device-status-card overview-card">
        <div class="card-head">
          <div>
            <h3>Asset availability</h3>
            <div class="metric-context">Operational condition only—not vulnerability severity</div>
          </div>
        </div>
        <div class="status-tiles">
          ${STATUS_TILES.map(
            (tile) => html`
              <div
                class="status-tile clickable ${tile.key} ${this._deviceStatusFilter === tile.key ? "active" : ""}"
                title="Filter the devices investigation queue"
                @click=${() => this._onStatusTileClick(tile.key)}
              >
                <div class="label">${tile.label}</div>
                <div class="value">${devices.status_counts[tile.key] ?? 0}</div>
              </div>
            `
          )}
        </div>
      </div>

      <div class="card posture-visual-card overview-card">
        <div class="card-head">
          <div><h3>Posture</h3><div class="metric-context">Current weighted security posture</div></div>
        </div>
        <div class="posture-ring-wrap">
          <div
            class="posture-ring"
            role="img"
            aria-label="Posture score ${posture.score} out of 100"
            style="--posture-angle:${Math.max(0, Math.min(100, posture.score)) * 3.6}deg;--posture-color:${postureColor};"
          >
            <div class="posture-ring-value"><strong>${posture.score}</strong><span>of 100</span></div>
          </div>
          <div>
            <div class="posture-grade-line">Grade ${posture.grade}</div>
            ${posture.provisional
              ? html`<span class="tag cosmetic" title="Waiting on: ${missing.join(", ")}">provisional</span>`
              : html`<span class="tag enforced">Healthy</span>`}
            <p class="posture-description">
              ${trend.delta < 0
                ? "Posture declined over the displayed period. Review the priority queue below."
                : "No downward posture trend in the displayed period."}
            </p>
          </div>
        </div>
      </div>

      <div class="card overview-card clickable" @click=${() => this._goto("scanner")} title="View vulnerability findings">
        <div class="card-head">
          <div><h3>Finding severity</h3><div class="metric-context">Current vulnerability findings by severity</div></div>
        </div>
        <div class="donut-layout">
          <div
            class="severity-donut"
            role="img"
            aria-label="${findingTotal.toLocaleString()} findings by severity"
            style="background:${findingDonut}"
          ><strong>${findingTotal.toLocaleString()}</strong></div>
          <div class="compact-legend">
            ${findingSegments.map(
              (segment) => html`
                <div class="item">
                  <span class="swatch" style="background:${segment.color}"></span>${segment.label}
                  <strong>${segment.value.toLocaleString()}</strong>
                </div>
              `
            )}
          </div>
        </div>
      </div>

      <div class="card trend-card overview-card">
        <div class="card-head">
          <div><h3>Posture trend</h3><div class="metric-context">${summary.posture_history.length ? "Thirty-day score history" : "History begins after the first completed posture calculation"}</div></div>
          <span class="tag ${trend.delta >= 0 ? "enforced" : "cosmetic"}">${trendDelta}</span>
        </div>
        <svg class="posture-trend" viewBox="0 0 560 142" role="img" aria-label="Posture score trend, ${trendDelta} points">
          <line class="grid-line" x1="12" y1="22" x2="548" y2="22"></line>
          <line class="grid-line" x1="12" y1="70" x2="548" y2="70"></line>
          <line class="grid-line" x1="12" y1="118" x2="548" y2="118"></line>
          <polygon class="trend-area" points=${trend.area}></polygon>
          <polyline class="trend-line" points=${trend.points}></polyline>
          <text x="12" y="138">${trend.firstLabel}</text>
          <text x="548" y="138" text-anchor="end">${trend.lastLabel}</text>
        </svg>
      </div>

      <div class="card overview-card">
        <div class="card-head">
          <div>
            <h3>Priority queue</h3>
            <div class="metric-context">Protected details; acknowledgement and remediation stay in this console</div>
          </div>
        </div>
        ${!openDetections.length
          ? html`<div class="empty">No open detections. The priority queue is clear.</div>`
          : html`
              <div class="priority-table-wrap">
                <table>
                  <thead>
                    <tr><th>Priority</th><th>Finding</th><th>User</th><th>Status</th><th>Last seen</th><th></th></tr>
                  </thead>
                  <tbody>
                    ${openDetections.map(
                      (detection) => html`
                        <tr>
                          <td><span class="pill ${detection.severity}"><span class="dot"></span>${detection.severity}</span></td>
                          <td>${detection.title}</td>
                          <td>${this._nameFor(detection.user_id)}</td>
                          <td>Open</td>
                          <td>${new Date(detection.last_seen).toLocaleString()}</td>
                          <td>
                            <span class="priority-actions">
                              <button class="ha-btn" @click=${() => this._onAck(detection.id)}>Ack</button>
                              <button class="ha-btn" @click=${() => this._onResolve(detection.id)}>Resolve</button>
                            </span>
                          </td>
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
    const openDetections = this._detections.filter((det) => det.status === "open");

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
        render: () => this._renderReferenceOverview(),
      },
      {
        id: "device_vuln_overview",
        title: "Device & Vulnerability Overview",
        render: () => html`
      <h2 class="section-title">Operational detail</h2>
      <p class="section-subtitle">Entity-state reliability and security-source health behind the overview.</p>
      <div class="row2">
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
        ${this._renderSecurityCard()}
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
