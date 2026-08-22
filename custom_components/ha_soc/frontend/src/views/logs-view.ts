import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { HaLogEntry, fetchSystemLog } from "../data/ha-soc-ws";

// Same core/custom logger-name convention health.py uses for its own
// per-domain error attribution — anything that doesn't match either
// prefix falls back to its own top-level module name (e.g. "aiohttp"),
// which is still a useful, real bucket to filter noisy libraries by.
function domainFor(loggerName: string): string {
  const core = loggerName.match(/^homeassistant\.components\.([^.]+)/);
  if (core) return core[1];
  const custom = loggerName.match(/^custom_components\.([^.]+)/);
  if (custom) return custom[1];
  return loggerName.split(".")[0];
}

function levelPillClass(level: string): string {
  switch (level) {
    case "CRITICAL":
      return "critical";
    case "ERROR":
      return "high";
    case "WARNING":
      return "medium";
    default:
      return "low";
  }
}

@customElement("ha-soc-logs-view")
export class HaSocLogsView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _entries: HaLogEntry[] = [];
  @state() private _loading = true;
  @state() private _domainFilter = "";
  @state() private _expanded: Set<number> = new Set();

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      this._entries = await fetchSystemLog(this.hass);
    } finally {
      this._loading = false;
    }
  }

  private _toggleExpanded(index: number) {
    const next = new Set(this._expanded);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    this._expanded = next;
  }

  private get _domains(): string[] {
    return Array.from(new Set(this._entries.map((e) => domainFor(e.name)))).sort();
  }

  private get _filtered(): HaLogEntry[] {
    if (!this._domainFilter) return this._entries;
    return this._entries.filter((e) => domainFor(e.name) === this._domainFilter);
  }

  render() {
    const filtered = this._filtered;

    return html`
      <div class="card">
        <h3>Home Assistant Logs</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          The same WARNING/ERROR/CRITICAL buffer as Settings → System → Logs
          (<code>/config/logs</code>) — deduplicated, most recent first. This shows Home
          Assistant's own captured log records only;
          <strong>add-on container logs aren't included</strong> — they're a separate
          stream Supervisor captures per-container, not part of Home Assistant's Python
          logging, so there's nothing for this view to filter. Check an add-on's own
          Log tab (Settings → Add-ons → the add-on → Log) for those.
        </p>
        <div class="toolbar">
          <select @change=${(e: Event) => (this._domainFilter = (e.target as HTMLSelectElement).value)}>
            <option value="" ?selected=${this._domainFilter === ""}>All integrations</option>
            ${this._domains.map(
              (d) => html`<option value=${d} ?selected=${d === this._domainFilter}>${d}</option>`
            )}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._loading
          ? html`<div class="empty">Loading…</div>`
          : !filtered.length
          ? html`<div class="empty">No matching log entries.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Level</th>
                    <th>Integration</th>
                    <th>Message</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  ${filtered.map((entry, i) => {
                    const expanded = this._expanded.has(i);
                    return html`
                      <tr
                        class=${entry.exception ? "clickable" : ""}
                        title=${entry.exception ? "Click to show/hide the traceback" : ""}
                        @click=${() => entry.exception && this._toggleExpanded(i)}
                      >
                        <td>${new Date(entry.first_occurred * 1000).toLocaleString()}</td>
                        <td>
                          <span class="pill ${levelPillClass(entry.level)}"
                            ><span class="dot"></span>${entry.level}</span
                          >
                        </td>
                        <td class="muted">${domainFor(entry.name)}</td>
                        <td>
                          ${entry.message[entry.message.length - 1]}
                          ${entry.source ? html`<div class="muted" style="font-size:11px;">${entry.source[0]}:${entry.source[1]}</div>` : nothing}
                        </td>
                        <td class="num">${entry.count}</td>
                      </tr>
                      ${expanded && entry.exception
                        ? html`
                            <tr>
                              <td colspan="5">
                                <pre
                                  style="white-space:pre-wrap;font-size:11.5px;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);padding:10px;border-radius:6px;margin:0;"
                                >
${entry.exception}</pre
                                >
                              </td>
                            </tr>
                          `
                        : nothing}
                    `;
                  })}
                </tbody>
              </table>
            `}
      </div>
    `;
  }
}
