import { html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  IntegrationSecurityOverview,
  IntegrationSecurityRow,
  IntegrationTier,
  ContainerResourceOverview,
  ContainerResource,
  WatchdogAction,
  WatchdogStatus,
  fetchIntegrationSecurity,
  refreshIntegrationSecurity,
  fetchContainerResources,
  fetchWatchdogStatus,
  setWatchdog,
} from "../data/ha-soc-ws";

const TIER_LABEL: Record<IntegrationTier, string> = {
  core: "Core",
  hacs: "HACS",
  custom: "Custom",
};
// Provenance tone: core is strongest-known, custom (unmanaged) weakest-known.
const TIER_TONE: Record<IntegrationTier, string> = {
  core: "good",
  hacs: "medium",
  custom: "high",
};
// Ascending goes strongest-known to weakest-known provenance, matching the tier pills.
const TIER_RANK: Record<IntegrationTier, number> = {
  core: 0,
  hacs: 1,
  custom: 2,
};

const FLAG_LABEL: Record<string, string> = {
  custom_repo: "Custom repo",
  custom_source_list: "Custom source-list",
};

const PAGE_SIZE = 25;

@customElement("ha-soc-integration-security-view")
export class HaSocIntegrationSecurityView extends HaSocCustomizableView {
  protected get viewId() {
    return "integration_security";
  }

  static styles = sharedStyles;

  @state() private _overview: IntegrationSecurityOverview | null = null;
  @state() private _loading = true;
  // Non-null when the load failed; otherwise the page would stick on "Loading integrations...".
  @state() private _error: string | null = null;
  @state() private _refreshing = false;
  @state() private _search = "";
  @state() private _tierFilter = "all";
  @state() private _limit = PAGE_SIZE;
  @state() private _intSort: SortState | null = null;
  @state() private _containerSort: SortState | null = null;
  @state() private _containers: ContainerResourceOverview | null = null;
  @state() private _containersLoading = true;
  @state() private _watchdog: WatchdogStatus | null = null;
  @state() private _editSlug: string | null = null;
  @state() private _wdError: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
    this._loadContainers();
    this._loadWatchdog();
  }

  private async _loadWatchdog() {
    try {
      this._watchdog = await fetchWatchdogStatus(this.hass);
    } catch {
      this._watchdog = null;
    }
  }

  // Owner-gated server-side; surface the rejection as a message.
  private async _setWatchdog(changes: Parameters<typeof setWatchdog>[1]) {
    this._wdError = null;
    try {
      this._watchdog = await setWatchdog(this.hass, changes);
    } catch (e) {
      this._wdError =
        e && typeof e === "object" && "code" in (e as Record<string, unknown>) && (e as { code: string }).code === "unauthorized"
          ? "Watchdog and cap configuration are available to the account owner only."
          : `Could not save: ${e instanceof Error ? e.message : JSON.stringify(e)}`;
    }
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      this._overview = await fetchIntegrationSecurity(this.hass);
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  private async _loadContainers() {
    this._containersLoading = true;
    try {
      this._containers = await fetchContainerResources(this.hass);
    } catch {
      this._containers = null;
    } finally {
      this._containersLoading = false;
    }
  }

  private async _onRefresh() {
    this._refreshing = true;
    try {
      await refreshIntegrationSecurity(this.hass);
      await this._load();
    } finally {
      this._refreshing = false;
    }
  }

  // Accessors for sortRows; nulls sink to the bottom per the shared helper.
  private static readonly INTEGRATION_SORT: Record<string, (r: IntegrationSecurityRow) => unknown> = {
    name: (r) => r.name,
    tier: (r) => TIER_RANK[r.tier],
    quality: (r) => r.quality_scale,
    license: (r) => r.license_present,
    scanner: (r) => r.scanner_findings,
    signed: (r) => r.github?.commit_verified ?? null,
    // Release composite: tagged release (0), branch-HEAD (1), archived (2); unknown sinks.
    release: (r) => {
      const g = r.github;
      if (!g) return null;
      if (g.archived) return 2;
      if (g.has_release === null) return null;
      return g.has_release ? 0 : 1;
    },
    stars: (r) => r.github?.stars ?? null,
    // ISO 8601 timestamps compare correctly as strings.
    pushed: (r) => r.github?.pushed_at ?? null,
  };

  private _filtered(): IntegrationSecurityRow[] {
    const rows = this._overview?.integrations ?? [];
    const q = this._search.trim().toLowerCase();
    const filtered = rows
      .filter((r) => this._tierFilter === "all" || r.tier === this._tierFilter)
      .filter((r) => !q || r.name.toLowerCase().includes(q) || r.domain.toLowerCase().includes(q));
    // Name-ascending is the default until a header is clicked.
    if (!this._intSort) return filtered.sort((a, b) => a.name.localeCompare(b.name));
    return sortRows(filtered, this._intSort, HaSocIntegrationSecurityView.INTEGRATION_SORT);
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading integrations…</div>`;
    if (this._error || !this._overview) {
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Integration Security</h3>
          <p style="font-size:13px;">${this._error ?? "The server returned no data."}</p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;
    }
    const o = this._overview;
    const filtered = this._filtered();
    const shown = filtered.slice(0, this._limit);
    const s = this._intSort;
    // A new sort re-ranks the whole filtered set, so pagination resets to page one.
    const on = (next: SortState) => {
      this._intSort = next;
      this._limit = PAGE_SIZE;
    };

    const sections: LayoutSection[] = [
      {
        id: "integration_security",
        title: "Integration Security",
        hideable: false,
        render: () => html`
      <div class="card">
        <h3>Integration Security</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">provenance, not safety</span> This measures how much is
          known about where each integration's code came from and how it's maintained — it
          is <strong>not</strong> a verdict that the code is safe to run. Home Assistant
          runs integrations in-process with no sandbox; a high-provenance integration can
          still do anything a low-provenance one can.
        </p>

        <div class="toolbar" style="margin-top:12px;">
          <div class="pill" style="--tone-unused:0">
            <span class="dot" style="background:var(--success-color,#43a047);"></span>
            Core ${o.tier_counts.core}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--warning-color,#ffa600);"></span>
            HACS ${o.tier_counts.hacs}
          </div>
          <div class="pill">
            <span class="dot" style="background:var(--error-color,#db4437);"></span>
            Custom ${o.tier_counts.custom}
          </div>
          <span class="spacer"></span>
          <button class="ha-btn" ?disabled=${this._refreshing || !o.github_configured} @click=${this._onRefresh}>
            ${this._refreshing ? "Refreshing…" : "Refresh GitHub signals"}
          </button>
        </div>

        ${!o.github_configured
          ? html`<p class="muted" style="font-size:12px;margin:0 0 4px;">
              GitHub-derived signals are <strong>not collected</strong> — set a GitHub token
              in the owner-only Settings tab to enable them.
            </p>`
          : o.refreshed_at
            ? html`<p class="muted" style="font-size:12px;margin:0 0 4px;">
                GitHub signals last refreshed ${new Date(o.refreshed_at).toLocaleString()}.
              </p>`
            : nothing}
        ${o.hacs_installed && !o.hacs_source_introspectable
          ? html`<p class="muted" style="font-size:12px;margin:0;">
              HACS is installed but its per-repository source (default store vs. custom
              repo) isn't readable here, so HACS-managed content is shown as
              <em>Custom</em> and source flags are unverified.
            </p>`
          : nothing}
      </div>

      <div class="card">
        <div class="toolbar">
          <input
            type="text"
            placeholder="Search integrations…"
            .value=${this._search}
            @input=${(e: Event) => {
              this._search = (e.target as HTMLInputElement).value;
              this._limit = PAGE_SIZE;
            }}
            style="flex:1 1 220px;"
          />
          <select
            .value=${this._tierFilter}
            @change=${(e: Event) => {
              this._tierFilter = (e.target as HTMLSelectElement).value;
              this._limit = PAGE_SIZE;
            }}
          >
            <option value="all">All tiers</option>
            <option value="core">Core</option>
            <option value="hacs">HACS</option>
            <option value="custom">Custom</option>
          </select>
        </div>

        ${!filtered.length
          ? html`<div class="empty">No integrations match.</div>`
          : html`
              <div style="overflow-x:auto;">
                <table>
                  <thead>
                    <tr>
                      ${sortableTh("Integration", "name", s, on)}
                      ${sortableTh("Source", "tier", s, on)}
                      ${sortableTh("Quality", "quality", s, on)}
                      ${sortableTh("License", "license", s, on)}
                      ${sortableTh("Scanner", "scanner", s, on)}
                      ${sortableTh("Signed", "signed", s, on)}
                      ${sortableTh("Release", "release", s, on)}
                      ${sortableTh("Stars", "stars", s, on)}
                      ${sortableTh("Last push", "pushed", s, on)}
                    </tr>
                  </thead>
                  <tbody>
                    ${shown.map((r) => this._renderRow(r))}
                  </tbody>
                </table>
              </div>
              ${filtered.length > this._limit
                ? html`
                    <div class="toolbar" style="justify-content:center;margin-top:12px;">
                      <button class="ha-btn" @click=${() => (this._limit += PAGE_SIZE)}>
                        Show more (${filtered.length - this._limit} more)
                      </button>
                    </div>
                  `
                : nothing}
              <p class="muted" style="font-size:11.5px;margin-top:8px;">
                Showing ${Math.min(this._limit, filtered.length)} of ${filtered.length}.
              </p>
            `}
      </div>
        `,
      },
      { id: "container_resources", title: "Container Resource Usage", render: () => this._renderContainers() },
    ];
    return this._renderSections(sections);
  }

  private _notCollected() {
    return html`<span class="muted" title="No GitHub token, or no repo URL discovered">—</span>`;
  }

  private _fmtBytes(n: number | null): string {
    if (n == null) return "—";
    if (n < 1024) return `${n} B`;
    const units = ["KB", "MB", "GB", "TB"];
    let v = n / 1024;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
  }

  private _pctCell(pct: number | null, flagged: boolean) {
    if (pct == null) return html`<span class="muted">—</span>`;
    const color = flagged ? "var(--status-critical)" : pct >= 60 ? "var(--status-warning)" : "inherit";
    return html`<span style="font-weight:600;color:${color};font-variant-numeric:tabular-nums;"
      >${pct.toFixed(1)}%</span
    >`;
  }

  // The backend pre-sorts suspicious containers first; a null sort state keeps that order.
  private static readonly CONTAINER_SORT: Record<string, (r: ContainerResource) => unknown> = {
    name: (r) => r.name,
    // Mirrors the State cell: Core and Supervisor read "running", a stopped add-on "stopped".
    state: (r) => (r.state === "started" || r.kind !== "addon" ? "running" : (r.state ?? "stopped")),
    cpu: (r) => r.cpu_percent,
    memory: (r) => r.memory_percent,
    usage: (r) => r.memory_usage,
    // Net and Disk sort by combined throughput; neither direction reported sinks as unknown.
    net: (r) => (r.network_rx == null && r.network_tx == null ? null : (r.network_rx ?? 0) + (r.network_tx ?? 0)),
    disk: (r) => (r.blk_read == null && r.blk_write == null ? null : (r.blk_read ?? 0) + (r.blk_write ?? 0)),
    flags: (r) => r.flags.length,
  };

  private _renderContainers() {
    const c = this._containers;
    const cs = this._containerSort;
    const onC = (next: SortState) => (this._containerSort = next);
    return html`
      <div class="card">
        <div class="toolbar">
          <h3 style="margin:0;flex:1;">Container Resource Usage</h3>
          <button class="ha-btn" ?disabled=${this._containersLoading} @click=${() => this._loadContainers()}>
            ${this._containersLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        <p class="muted" style="margin-top:-4px;font-size:12.5px;">
          Live per-container CPU and memory for every add-on plus Home Assistant Core and
          the Supervisor. A container sitting near its <strong>memory limit</strong> (or
          pinning CPU) is the usual signal for the one that's OOM-killing / restart-looping
          and dragging the host down — those float to the top and are flagged.
        </p>
        ${this._renderWatchdogBar()}
        ${this._containersLoading && !c
          ? html`<div class="empty">Loading container stats…</div>`
          : !c || !c.available
            ? html`<div class="empty">
                ${c?.reason === "not_supervisor"
                  ? "Per-container stats need a Supervisor-based install (Home Assistant OS or Supervised). This install doesn't run under Supervisor, so there are no add-on containers to measure."
                  : "Container stats aren't available right now."}
              </div>`
            : !c.containers.length
              ? html`<div class="empty">No containers reported.</div>`
              : html`
                  <div style="overflow-x:auto;">
                    <table>
                      <thead>
                        <tr>
                          ${sortableTh("Container", "name", cs, onC)}
                          ${sortableTh("State", "state", cs, onC)}
                          ${sortableTh("CPU", "cpu", cs, onC, { numeric: true })}
                          ${sortableTh("Memory", "memory", cs, onC, { numeric: true })}
                          ${sortableTh("Used / Limit", "usage", cs, onC)}
                          ${sortableTh("Net ↓/↑", "net", cs, onC)}
                          ${sortableTh("Disk R/W", "disk", cs, onC)}
                          ${sortableTh("Flags", "flags", cs, onC)}
                          <th>Watchdog / Cap</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${sortRows(
                          c.containers,
                          cs,
                          HaSocIntegrationSecurityView.CONTAINER_SORT
                        ).map((row) => this._renderContainerRow(row))}
                      </tbody>
                    </table>
                  </div>
                  ${this._renderEditor()}
                  ${this._renderWatchdogActivity()}
                  <p class="muted" style="font-size:11.5px;margin-top:8px;">
                    Updated ${new Date(c.generated_at).toLocaleTimeString()}. CPU/memory are
                    an instantaneous sample — click Refresh to re-poll.
                  </p>
                `}
      </div>
    `;
  }


  private _renderWatchdogBar() {
    const w = this._watchdog;
    if (!w) return nothing;
    const cfg = w.config;
    return html`
      <div
        style="border:1px solid var(--divider-color);border-radius:10px;padding:10px 14px;margin-bottom:12px;"
      >
        <div class="toolbar" style="margin-bottom:${cfg.enabled ? "8px" : "0"};">
          <label style="display:inline-flex;align-items:center;gap:8px;font-weight:600;font-size:13.5px;cursor:pointer;">
            <input
              type="checkbox"
              .checked=${cfg.enabled}
              @change=${(e: Event) => this._setWatchdog({ enabled: (e.target as HTMLInputElement).checked })}
            />
            Resource Watchdog
          </label>
          <span class="muted" style="font-size:12px;">
            ${cfg.enabled
              ? `sampling every ${cfg.interval_seconds}s — acts after ${cfg.sustained_samples} sustained breaches`
              : "off — no automatic detection or action (owner-only setting)"}
          </span>
        </div>
        ${cfg.enabled
          ? html`
              <div class="toolbar" style="gap:14px;margin-bottom:0;">
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  CPU ≥
                  <input type="number" min="10" max="100" style="width:64px;" .value=${String(cfg.default_cpu_percent)}
                    @change=${(e: Event) => this._setWatchdog({ default_cpu_percent: Number((e.target as HTMLInputElement).value) })} />%
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Memory ≥
                  <input type="number" min="10" max="100" style="width:64px;" .value=${String(cfg.default_memory_percent)}
                    @change=${(e: Event) => this._setWatchdog({ default_memory_percent: Number((e.target as HTMLInputElement).value) })} />%
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Default action
                  <select .value=${cfg.default_action}
                    @change=${(e: Event) => this._setWatchdog({ default_action: (e.target as HTMLSelectElement).value as WatchdogAction })}>
                    <option value="alert" ?selected=${cfg.default_action === "alert"}>Alert only</option>
                    <option value="restart" ?selected=${cfg.default_action === "restart"}>Restart add-on</option>
                    <option value="stop" ?selected=${cfg.default_action === "stop"}>Stop add-on</option>
                  </select>
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Sustained samples
                  <input type="number" min="1" max="30" style="width:56px;" .value=${String(cfg.sustained_samples)}
                    @change=${(e: Event) => this._setWatchdog({ sustained_samples: Number((e.target as HTMLInputElement).value) })} />
                </label>
              </div>
              <p class="muted" style="font-size:11.5px;margin:6px 0 0;">
                Home Assistant Core and the Supervisor are always alert-only — the watchdog
                never auto-restarts them, whatever the default. After 3 enforcement actions
                on one container within an hour it downgrades that container to alert-only
                (a restart loop needs a human, not more restarts).
              </p>
            `
          : nothing}
        ${this._wdError
          ? html`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin:6px 0 0;">${this._wdError}</p>`
          : nothing}
      </div>
    `;
  }


  private _wdCell(r: ContainerResource) {
    const w = this._watchdog;
    if (!w) return html`<span class="muted">—</span>`;
    const cfg = w.config;
    const ov = cfg.overrides?.[r.slug] ?? {};
    const cpu = ov.cpu_percent ?? cfg.default_cpu_percent;
    const mem = ov.memory_percent ?? cfg.default_memory_percent;
    const action = r.kind === "addon" ? (ov.action ?? cfg.default_action) : "alert";
    const cap = cfg.hard_limits?.[r.slug];
    const capState = w.hard_limit_state?.[r.slug];
    const capChip = cap
      ? capState
        ? html`<span
            class="pill ${capState.status === "applied" ? "good" : "high"}"
            title=${capState.detail ?? capState.status}
            ><span class="dot"></span>cap ${capState.status}</span
          >`
        : html`<span class="pill medium" title="Configured; waiting for the Probe to apply"
            ><span class="dot"></span>cap pending</span
          >`
      : nothing;
    return html`
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
        ${cfg.enabled && ov.enabled !== false
          ? html`<span class="muted" style="font-size:11px;" title="Thresholds → action">
              ${cpu}%/${mem}% → ${action}
            </span>`
          : html`<span class="muted" style="font-size:11px;">off</span>`}
        ${capChip}
        <button
          class="ha-btn"
          style="padding:2px 8px;font-size:11.5px;"
          @click=${() => (this._editSlug = this._editSlug === r.slug ? null : r.slug)}
        >
          ${this._editSlug === r.slug ? "Close" : "Edit"}
        </button>
      </div>
    `;
  }

  private _renderEditor() {
    const slug = this._editSlug;
    const w = this._watchdog;
    const c = this._containers;
    if (!slug || !w || !c) return nothing;
    const row = c.containers.find((x) => x.slug === slug);
    if (!row) return nothing;
    const ov = w.config.overrides?.[slug] ?? {};
    const cap = w.config.hard_limits?.[slug] ?? { memory_mb: null, cpus: null };
    const isAddon = row.kind === "addon";
    return html`
      <div
        style="border:1px solid var(--primary-color);border-radius:10px;padding:12px 14px;margin-top:10px;"
      >
        <div style="font-weight:600;font-size:13.5px;margin-bottom:8px;">
          ${row.name} <span class="muted" style="font-weight:400;">— per-container watchdog & cap</span>
        </div>
        <div class="toolbar" style="gap:14px;">
          <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
            CPU ≥
            <input type="number" min="10" max="100" style="width:64px;"
              placeholder=${String(w.config.default_cpu_percent)}
              .value=${ov.cpu_percent != null ? String(ov.cpu_percent) : ""}
              @change=${(e: Event) => {
                const v = (e.target as HTMLInputElement).value;
                this._setWatchdog({ override: { slug, cpu_percent: v ? Number(v) : null } });
              }} />%
          </label>
          <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
            Memory ≥
            <input type="number" min="10" max="100" style="width:64px;"
              placeholder=${String(w.config.default_memory_percent)}
              .value=${ov.memory_percent != null ? String(ov.memory_percent) : ""}
              @change=${(e: Event) => {
                const v = (e.target as HTMLInputElement).value;
                this._setWatchdog({ override: { slug, memory_percent: v ? Number(v) : null } });
              }} />%
          </label>
          ${isAddon
            ? html`
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Action
                  <select .value=${ov.action ?? w.config.default_action}
                    @change=${(e: Event) =>
                      this._setWatchdog({ override: { slug, action: (e.target as HTMLSelectElement).value as WatchdogAction } })}>
                    <option value="alert" ?selected=${(ov.action ?? w.config.default_action) === "alert"}>Alert only</option>
                    <option value="restart" ?selected=${(ov.action ?? w.config.default_action) === "restart"}>Restart</option>
                    <option value="stop" ?selected=${(ov.action ?? w.config.default_action) === "stop"}>Stop</option>
                  </select>
                </label>
              `
            : html`<span class="muted" style="font-size:12px;">action: alert only (never auto-restarted)</span>`}
          <button class="ha-btn" style="font-size:11.5px;" @click=${() => this._setWatchdog({ override: { slug, clear: true } })}>
            Reset to defaults
          </button>
        </div>
        ${isAddon
          ? html`
              <div class="toolbar" style="gap:14px;margin-top:8px;margin-bottom:0;">
                <span style="font-size:12.5px;font-weight:600;">Hard cap (Docker):</span>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  Memory
                  <input type="number" min="64" step="64" style="width:84px;" placeholder="unlimited"
                    .value=${cap.memory_mb != null ? String(cap.memory_mb) : ""}
                    @change=${(e: Event) => {
                      const v = (e.target as HTMLInputElement).value;
                      this._setWatchdog({ hard_limit: { slug, memory_mb: v ? Number(v) : null, cpus: cap.cpus } });
                    }} /> MB
                </label>
                <label class="muted" style="font-size:12px;display:inline-flex;align-items:center;gap:6px;">
                  CPUs
                  <input type="number" min="0.1" step="0.1" style="width:70px;" placeholder="unlimited"
                    .value=${cap.cpus != null ? String(cap.cpus) : ""}
                    @change=${(e: Event) => {
                      const v = (e.target as HTMLInputElement).value;
                      this._setWatchdog({ hard_limit: { slug, memory_mb: cap.memory_mb, cpus: v ? Number(v) : null } });
                    }} />
                </label>
                <button class="ha-btn" style="font-size:11.5px;"
                  @click=${() => this._setWatchdog({ hard_limit: { slug, memory_mb: null, cpus: null } })}>
                  Remove cap
                </button>
              </div>
              <p class="muted" style="font-size:11.5px;margin:6px 0 0;">
                ⚠ Hard caps are real Docker limits applied by the HA SOC Probe add-on. They
                require the Probe's <strong>Protection Mode to be disabled</strong> — a
                root-equivalent grant to that add-on (its security rating drops
                accordingly) — and are re-applied automatically every ~60s so they survive
                Supervisor recreating the container on updates. A memory cap means the
                kernel OOM-kills the add-on's process when it exceeds the cap — Supervisor's
                own add-on watchdog then restarts it if enabled.
              </p>
            `
          : nothing}
      </div>
    `;
  }

  private _renderWatchdogActivity() {
    const w = this._watchdog;
    if (!w) return nothing;
    const outcomes = Object.entries(w.containers)
      .filter(([, s]) => s.last_outcome)
      .map(([slug, s]) => ({ slug, text: s.last_outcome as string }));
    if (!outcomes.length) return nothing;
    return html`
      <div style="margin-top:10px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          RECENT WATCHDOG ACTIVITY
        </div>
        ${outcomes.map(
          (o) => html`
            <div class="muted" style="font-size:12px;font-family:var(--code-font-family,monospace);">
              ${o.slug}: ${o.text}
            </div>
          `
        )}
      </div>
    `;
  }

  private _renderContainerRow(r: ContainerResource) {
    const highMem = r.flags.includes("high_memory");
    const highCpu = r.flags.includes("high_cpu");
    const kindLabel = r.kind === "addon" ? "Add-on" : r.kind === "core" ? "Core" : "Supervisor";
    return html`
      <tr>
        <td>
          <div style="font-weight:600;">${r.name}</div>
          <div class="muted" style="font-size:11.5px;">${kindLabel}${r.slug ? ` · ${r.slug}` : ""}</div>
        </td>
        <td>
          ${r.state === "started" || r.kind !== "addon"
            ? html`<span class="muted">running</span>`
            : html`<span class="pill high"><span class="dot"></span>${r.state ?? "stopped"}</span>`}
        </td>
        <td class="num">${this._pctCell(r.cpu_percent, highCpu)}</td>
        <td class="num">${this._pctCell(r.memory_percent, highMem)}</td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(r.memory_usage)} / ${this._fmtBytes(r.memory_limit)}
        </td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(r.network_rx)} / ${this._fmtBytes(r.network_tx)}
        </td>
        <td class="muted" style="font-size:12px;">
          ${this._fmtBytes(r.blk_read)} / ${this._fmtBytes(r.blk_write)}
        </td>
        <td>
          ${r.flags.length
            ? html`<div class="chips">
                ${r.flags.map(
                  (f) => html`<span class="pill high"><span class="dot"></span>${
                    f === "high_memory" ? "high memory" : f === "high_cpu" ? "high CPU" : f.replace("_", " ")
                  }</span>`
                )}
              </div>`
            : html`<span class="muted">—</span>`}
        </td>
        <td>${this._wdCell(r)}</td>
      </tr>
    `;
  }

  private _renderRow(r: IntegrationSecurityRow) {
    const g = r.github;
    return html`
      <tr>
        <td>
          <div style="font-weight:600;">${r.name}</div>
          <div class="muted" style="font-size:11.5px;">
            ${r.domain}${r.version ? html` · v${r.version}` : ""}
          </div>
          ${r.flags.length
            ? html`<div class="chips" style="margin-top:3px;">
                ${r.flags.map(
                  (f) => html`<span class="pill high"><span class="dot"></span>${FLAG_LABEL[f] ?? f}</span>`
                )}
              </div>`
            : nothing}
        </td>
        <td>
          <span class="pill ${TIER_TONE[r.tier]}"><span class="dot"></span>${TIER_LABEL[r.tier]}</span>
        </td>
        <td class="muted">${r.quality_scale ?? "—"}</td>
        <td>
          ${r.license_present === null
            ? html`<span class="muted">—</span>`
            : r.license_present
              ? html`<span class="muted" title="License file present">yes</span>`
              : html`<span class="pill medium" title="No license file found"><span class="dot"></span>none</span>`}
        </td>
        <td>
          ${r.scanner_findings > 0
            ? html`<span class="pill high"><span class="dot"></span>${r.scanner_findings}</span>`
            : html`<span class="muted">0</span>`}
        </td>
        <td>
          ${!g
            ? this._notCollected()
            : g.commit_verified === null
              ? html`<span class="muted">?</span>`
              : g.commit_verified
                ? html`<span class="pill good" title="Default-branch head commit is signed/verified"
                    ><span class="dot"></span>signed</span
                  >`
                : html`<span class="muted" title="No verified signature on the head commit">unsigned</span>`}
        </td>
        <td>
          ${!g
            ? this._notCollected()
            : g.archived
              ? html`<span class="pill high" title="Repository is archived"><span class="dot"></span>archived</span>`
              : g.has_release === null
                ? html`<span class="muted">?</span>`
                : g.has_release
                  ? html`<span class="muted" title=${g.latest_release_tag ?? ""}>tagged</span>`
                  : html`<span class="pill medium" title="No published release — installs branch HEAD"
                      ><span class="dot"></span>branch</span
                    >`}
        </td>
        <td class="muted">${!g ? this._notCollected() : (g.stars ?? "—")}</td>
        <td class="muted" style="font-size:11.5px;">
          ${!g ? this._notCollected() : g.pushed_at ? new Date(g.pushed_at).toLocaleDateString() : "—"}
        </td>
      </tr>
    `;
  }
}
