import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  DashboardSummary,
  Detection,
  RiskResult,
  HaSocUser,
  fetchDashboardSummary,
  fetchDetections,
  fetchRisk,
  fetchUsers,
  setDetectionStatus,
} from "../data/ha-soc-ws";

@customElement("ha-soc-dashboard-view")
export class HaSocDashboardView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .tiles {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
      }
      .tile .label {
        font-size: 11px;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        font-weight: 600;
      }
      .tile .value {
        font-size: 26px;
        font-weight: 700;
        margin-top: 4px;
      }
      .tile .value.crit {
        color: var(--error-color, #db4437);
      }
      .donut-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .donut-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .donut {
        width: 96px;
        height: 96px;
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
        font-size: 16px;
        z-index: 1;
      }
      .legend {
        font-size: 12px;
        display: flex;
        flex-direction: column;
        gap: 5px;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .legend .sw {
        width: 8px;
        height: 8px;
        border-radius: 2px;
      }
      .legend .val {
        margin-left: auto;
        font-weight: 600;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _summary: DashboardSummary | null = null;
  @state() private _detections: Detection[] = [];
  @state() private _risk: Record<string, RiskResult> = {};
  @state() private _users: HaSocUser[] = [];
  @state() private _loading = true;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      const [summary, detections, risk, users] = await Promise.all([
        fetchDashboardSummary(this.hass),
        fetchDetections(this.hass),
        fetchRisk(this.hass),
        fetchUsers(this.hass),
      ]);
      this._summary = summary;
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

  render() {
    if (this._loading || !this._summary) return html`<div class="empty">Loading dashboard…</div>`;
    const s = this._summary;
    const openDetections = this._detections.filter((d) => d.status === "open");

    const riskSegments = [
      { key: "low", color: "var(--success-color, #43a047)" },
      { key: "moderate", color: "var(--warning-color, #ffa600)" },
      { key: "high", color: "#ec6a3a" },
      { key: "critical", color: "var(--error-color, #db4437)" },
    ].map((x) => ({ ...x, value: s.risk_band_counts[x.key] ?? 0 }));

    return html`
      <div class="tiles">
        <div class="tile">
          <div class="label">Security posture</div>
          <div class="value">${s.posture.score} <span style="font-size:14px;">(${s.posture.grade})</span></div>
        </div>
        <div class="tile">
          <div class="label">Open detections</div>
          <div class="value ${s.open_detections_count ? "crit" : ""}">${s.open_detections_count}</div>
        </div>
        <div class="tile">
          <div class="label">Users at risk</div>
          <div class="value">${s.users_at_risk_count} <span style="font-size:14px;">of ${s.total_users_count}</span></div>
        </div>
        <div class="tile">
          <div class="label">Critical/high vulns</div>
          <div class="value">${s.critical_high_vuln_count}</div>
        </div>
      </div>

      <div class="donut-row">
        <div class="card">
          <h3>Users by risk band</h3>
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

        <div class="card">
          <h3>Posture breakdown</h3>
          <table>
            <tbody>
              ${Object.entries(s.posture.breakdown).map(
                ([k, v]) => html`<tr><td>${k}</td><td class="muted">${(v as number).toFixed(1)}</td></tr>`
              )}
            </tbody>
          </table>
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
                    (d) => html`
                      <tr>
                        <td>${new Date(d.last_seen).toLocaleString()}</td>
                        <td>${d.title}</td>
                        <td><span class="pill ${d.severity}"><span class="dot"></span>${d.severity}</span></td>
                        <td>${this._nameFor(d.user_id)}</td>
                        <td>
                          <button class="ha-btn" @click=${() => this._onAck(d.id)}>Ack</button>
                          <button class="ha-btn" @click=${() => this._onResolve(d.id)}>Resolve</button>
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>
    `;
  }
}
