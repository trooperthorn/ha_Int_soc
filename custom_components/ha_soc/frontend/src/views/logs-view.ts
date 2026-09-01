import { html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  ContainerLog,
  ContainerLogTargets,
  FaultLogOverview,
  HaLogEntry,
  fetchContainerLog,
  fetchFaultLog,
  fetchLogTargets,
  fetchSystemLog,
} from "../data/ha-soc-ws";

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

// The captured-records table, the view's default source. Container targets
// (Supervisor journald streams) are raw text and render in a <pre> instead.
const SOURCE_SYSTEM = "system";

@customElement("ha-soc-logs-view")
export class HaSocLogsView extends HaSocCustomizableView {
  protected get viewId() {
    return "logs";
  }

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
      .fault-log pre,
      .rawlog {
        white-space: pre-wrap;
        font-size: 11.5px;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
        padding: 10px;
        border-radius: 6px;
        margin: 0;
        max-height: 400px;
        overflow-y: auto;
      }
      .rawlog {
        max-height: 600px;
        font-family: var(--code-font-family, monospace);
      }
    `,
  ];

  @state() private _entries: HaLogEntry[] = [];
  @state() private _fault: FaultLogOverview | null = null;
  @state() private _loading = true;
  // Non-null when the captured-records load failed: rendered as a
  // distinct could-not-load state, never an empty "no matching log
  // entries" (work plan item 4.12). The container-log path already
  // reports its own failures inline (async_fetch_container_log never
  // raises), so this covers only the system-log source.
  @state() private _error: string | null = null;
  @state() private _domainFilter = "";
  @state() private _levelFilter = "";
  @state() private _expanded: Set<number> = new Set();
  @state() private _sort: SortState | null = null;
  @state() private _targets: ContainerLogTargets | null = null;
  @state() private _source = SOURCE_SYSTEM;
  @state() private _containerLog: ContainerLog | null = null;
  @state() private _containerLoading = false;

  // Sort accessors for the captured-records table. Time and count are the
  // underlying numbers, never the locale strings; level sorts by severity
  // rank (Debug lowest) with unknown levels sinking as null.
  private static readonly LOG_SORT: Record<string, (e: HaLogEntry) => unknown> = {
    time: (e) => e.first_occurred,
    level: (e) => {
      const rank = LOG_LEVEL_ORDER.indexOf(e.level.toUpperCase());
      return rank === -1 ? null : rank;
    },
    integration: (e) => domainFor(e.name),
    message: (e) => e.message[e.message.length - 1],
    count: (e) => e.count,
  };

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      const [entries, fault, targets] = await Promise.all([
        fetchSystemLog(this.hass),
        fetchFaultLog(this.hass),
        // Selector population is best-effort: a failure (e.g. command missing
        // during a live upgrade) must not take down the whole Logs tab.
        fetchLogTargets(this.hass).catch(() => null),
      ]);
      this._entries = entries;
      this._fault = fault;
      this._targets = targets;
    } catch (err: any) {
      // system_log/list or the fault-log fetch itself failing must not
      // read as "no log entries"; the fault card and table both stay
      // hidden until the next successful load.
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  private async _loadContainer(target: string) {
    this._containerLoading = true;
    try {
      this._containerLog = await fetchContainerLog(this.hass, target);
    } catch (err) {
      this._containerLog = {
        available: false,
        target,
        content: null,
        truncated: false,
        error: String(err),
        fetched_at: new Date().toISOString(),
      };
    } finally {
      this._containerLoading = false;
    }
  }

  private _onSourceChange(e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    this._source = value;
    this._containerLog = null;
    if (value !== SOURCE_SYSTEM) this._loadContainer(value);
  }

  private _refresh() {
    if (this._source === SOURCE_SYSTEM) this._load();
    else this._loadContainer(this._source);
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
    const filtered = this._entries.filter((e) => {
      if (this._domainFilter && domainFor(e.name) !== this._domainFilter) return false;
      if (this._levelFilter && e.level.toUpperCase() !== this._levelFilter) return false;
      return true;
    });
    // With no sort chosen the backend order stands (most recent first).
    return sortRows(filtered, this._sort, HaSocLogsView.LOG_SORT);
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

  private _renderContainerLog() {
    const log = this._containerLog;
    const name =
      this._targets?.targets.find((t) => t.id === this._source)?.name ?? this._source;
    if (this._containerLoading && !log) return html`<div class="empty">Loading ${name} logs…</div>`;
    if (!log) return html`<div class="empty">Select a source.</div>`;
    if (!log.available)
      return html`<div class="empty">
        Couldn't load ${name} logs${log.error ? html`<br /><span class="muted">${log.error}</span>` : nothing}
      </div>`;
    return html`
      <p class="muted" style="font-size:12px;">
        Fetched ${new Date(log.fetched_at).toLocaleString()}${log.truncated
          ? ", showing the most recent 128 KB (older lines are in the add-on's own Log tab)"
          : ""}.
        This is the container's live journald stream via Supervisor, point-in-time, use
        Refresh for new lines.
      </p>
      <pre class="rawlog">${log.content?.trim() ? log.content : "(log is empty)"}</pre>
    `;
  }

  render() {
    const filtered = this._filtered;
    const s = this._sort;
    const on = (next: SortState) => {
      this._sort = next;
      // Expanded tracebacks are keyed by row position; a re-sort reorders
      // rows, so collapse them rather than attach to the wrong entries.
      this._expanded = new Set();
    };
    const showingSystem = this._source === SOURCE_SYSTEM;

    const sections: LayoutSection[] = [
      { id: "fault_log", title: "Home Assistant Crash Log", render: () => this._renderFaultLogCard() },
      {
        id: "logs",
        title: "Logs",
        hideable: false,
        render: () => html`
      <div class="card">
        <h3>Logs</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          ${showingSystem
            ? html`The same WARNING/ERROR/CRITICAL buffer as Settings → System → Logs
                (<code>/config/logs</code>), deduplicated, most recent first. This shows Home
                Assistant's own captured log records only. For an app or add-on's full
                container output, pick it from the source selector.`
            : html`Raw container output captured by the Supervisor, the same stream as the
                add-on's own Log tab. ANSI colors are stripped server-side.`}
        </p>
        <div class="toolbar">
          ${this._targets?.available
            ? html`
                <select @change=${this._onSourceChange} aria-label="Log source">
                  <option value=${SOURCE_SYSTEM} ?selected=${showingSystem}>
                    Integration logs (captured records)
                  </option>
                  ${this._targets.targets.map(
                    (t) => html`<option value=${t.id} ?selected=${t.id === this._source}>${t.name}</option>`
                  )}
                </select>
              `
            : nothing}
          ${showingSystem
            ? html`
                <select
                  aria-label="Filter by integration"
                  @change=${(e: Event) => {
                    this._domainFilter = (e.target as HTMLSelectElement).value;
                    this._expanded = new Set();
                  }}
                >
                  <option value="" ?selected=${this._domainFilter === ""}>All integrations</option>
                  ${this._domains.map(
                    (d) => html`<option value=${d} ?selected=${d === this._domainFilter}>${d}</option>`
                  )}
                </select>
                <select
                  aria-label="Filter by level"
                  @change=${(e: Event) => {
                    this._levelFilter = (e.target as HTMLSelectElement).value;
                    this._expanded = new Set();
                  }}
                >
                  <option value="" ?selected=${this._levelFilter === ""}>All levels</option>
                  ${this._levels.map(
                    (l) => html`<option value=${l} ?selected=${l === this._levelFilter}>${l}</option>`
                  )}
                </select>
              `
            : nothing}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._refresh} ?disabled=${this._containerLoading}>
            ${this._containerLoading ? "Loading…" : "Refresh"}
          </button>
        </div>
        ${!showingSystem
          ? this._renderContainerLog()
          : this._loading
          ? html`<div class="empty">Loading…</div>`
          : this._error
          ? html`
              <div style="border:1px solid var(--error-color,#db4437);border-radius:6px;padding:10px 12px;">
                <p style="font-size:13px;margin:0 0 8px;">${this._error}</p>
                <button class="ha-btn" @click=${() => this._load()}>Retry</button>
              </div>
            `
          : !filtered.length
          ? html`<div class="empty">No matching log entries.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    ${sortableTh("Time", "time", s, on)}
                    ${sortableTh("Level", "level", s, on)}
                    ${sortableTh("Integration", "integration", s, on)}
                    ${sortableTh("Message", "message", s, on)}
                    ${sortableTh("Count", "count", s, on, { numeric: true })}
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
        `,
      },
    ];
    return this._renderSections(sections);
  }
}
