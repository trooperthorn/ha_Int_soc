import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { FaultLogOverview, HaLogEntry, fetchFaultLog, fetchSystemLog } from "../data/ha-soc-ws";

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

// Dedicated log-level palette — deliberately NOT the same `.pill.critical/
// high/medium/low` classes finding severity uses elsewhere in this panel.
// A log LEVEL and a finding SEVERITY are different axes that happen to
// share adjectives; conflating them made ERROR and CRITICAL render
// identically (both mapped to the same red) with no way to tell them
// apart at a glance, which is exactly the problem this fixes. Five tiers,
// Debug through Critical, each visually distinct.
const LOG_LEVEL_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

function logLevelClass(level: string): string {
  const normalized = level.toUpperCase();
  return LOG_LEVEL_ORDER.includes(normalized) ? normalized.toLowerCase() : "info";
}

@customElement("ha-soc-logs-view")
export class HaSocLogsView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .log-level {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.02em;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .log-level .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        flex: none;
      }
      .log-level.debug {
        background: rgba(154, 160, 166, 0.16);
        color: var(--secondary-text-color);
      }
      .log-level.debug .dot {
        background: var(--cat-other, #9aa0a6);
      }
      .log-level.info {
        background: rgba(42, 120, 214, 0.14);
        color: var(--cat-1, #2a78d6);
      }
      .log-level.info .dot {
        background: var(--cat-1, #2a78d6);
      }
      .log-level.warning {
        background: rgba(250, 178, 25, 0.16);
        color: #7a5200;
      }
      .log-level.warning .dot {
        background: var(--status-warning, #fab219);
      }
      .log-level.error {
        background: rgba(236, 131, 90, 0.18);
        color: var(--status-serious, #ec835a);
      }
      .log-level.error .dot {
        background: var(--status-serious, #ec835a);
      }
      .log-level.critical {
        background: rgba(208, 59, 59, 0.18);
        color: var(--status-critical, #d03b3b);
      }
      .log-level.critical .dot {
        background: var(--status-critical, #d03b3b);
      }
      :host(.dark) .log-level.warning {
        color: var(--status-warning, #fab219);
      }
      .fault-log pre {
        white-space: pre-wrap;
        font-size: 11.5px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
        padding: 10px;
        border-radius: 6px;
        margin: 0;
        max-height: 400px;
        overflow-y: auto;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _entries: HaLogEntry[] = [];
  @state() private _fault: FaultLogOverview | null = null;
  @state() private _loading = true;
  @state() private _domainFilter = "";
  @state() private _levelFilter = "";
  @state() private _expanded: Set<number> = new Set();

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      const [entries, fault] = await Promise.all([fetchSystemLog(this.hass), fetchFaultLog(this.hass)]);
      this._entries = entries;
      this._fault = fault;
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

  private get _levels(): string[] {
    const present = new Set(this._entries.map((e) => e.level.toUpperCase()));
    return LOG_LEVEL_ORDER.filter((l) => present.has(l));
  }

  private get _filtered(): HaLogEntry[] {
    return this._entries.filter((e) => {
      if (this._domainFilter && domainFor(e.name) !== this._domainFilter) return false;
      if (this._levelFilter && e.level.toUpperCase() !== this._levelFilter) return false;
      return true;
    });
  }

  private _renderFaultLogCard() {
    const fault = this._fault;
    if (!fault) return nothing;

    return html`
      <div class="card fault-log">
        <h3>
          Home Assistant Crash Log
          ${fault.exists && fault.content?.trim()
            ? html`<span class="log-level critical"><span class="dot"></span>crash detected</span>`
            : html`<span class="tag enforced">none detected</span>`}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <code>home-assistant.log.fault</code> — Python's own faulthandler dump. This
          file is only ever written when Home Assistant Core itself crashes at a fatal,
          low level (segfault, abort, illegal instruction) — a normal Python exception
          never creates it, and it's separate from the WARNING/ERROR table below. Home
          Assistant appends to this file across restarts and only deletes it automatically
          after a clean run finds it empty, so old content can persist here until it's
          cleared by hand on the host — this view is read-only and never touches the file.
        </p>
        ${!fault.exists || !fault.content?.trim()
          ? html`<div class="empty">No crash detected.</div>`
          : html`
              <p class="muted" style="font-size:12px;">
                Last written ${new Date(fault.modified_at!).toLocaleString()} —
                ${fault.size_bytes.toLocaleString()} byte(s) total${fault.truncated
                  ? ", showing the most recent 64 KB"
                  : ""}.
              </p>
              <pre>${fault.content}</pre>
            `}
      </div>
    `;
  }

  render() {
    const filtered = this._filtered;

    return html`
      ${this._renderFaultLogCard()}

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
          <select @change=${(e: Event) => (this._levelFilter = (e.target as HTMLSelectElement).value)}>
            <option value="" ?selected=${this._levelFilter === ""}>All levels</option>
            ${this._levels.map(
              (l) => html`<option value=${l} ?selected=${l === this._levelFilter}>${l}</option>`
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
                          <span class="log-level ${logLevelClass(entry.level)}"
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
