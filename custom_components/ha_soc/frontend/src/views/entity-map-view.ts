import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { DEFAULT_OPTIONS, MapOptions, fetchEntityMap } from "../data/ha-graph";
import type { Dataset, Layout, ViewId } from "../graph/types";
import { layoutArc } from "../graph/arc";
import { layoutForce } from "../graph/force";
import {
  Camera,
  fitCamera,
  pickNode,
  render,
  screenToWorld,
} from "../graph/renderer";

/**
 * Entity relationship map.
 *
 * Two readings of the same registry data, drawn by the vendored graph engine in ../graph:
 * "Relationships" is the force layout over device/entity/area/integration links with devices
 * pinned at the centre, and "Activity" is the arc layout over the last day of logbook events.
 *
 * Everything is read through the plain Home Assistant websocket API with the signed-in
 * admin's own session, so this view adds no backend and no new permission.
 */
@customElement("ha-soc-entity-map-view")
export class HaSocEntityMapView extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _dataset: Dataset | null = null;
  @state() private _error: string | null = null;
  @state() private _loading = true;
  @state() private _view: ViewId = "web";
  @state() private _options: MapOptions = DEFAULT_OPTIONS;
  @state() private _activeGroups = new Set<string>();
  @state() private _activeKinds = new Set<string>();
  @state() private _scopeIds = new Set<string>();
  @state() private _selected: string | null = null;
  @state() private _hovered: string | null = null;
  @state() private _sizeScale = 1;
  @state() private _showLabels = true;

  private _layout: Layout = { nodes: [], dots: [], links: [], axis: [] };
  private _camera: Camera = { x: 0, y: 0, k: 1 };
  private _size = { w: 800, h: 600 };
  private _drag: { x: number; y: number; cam: Camera; moved: number } | null = null;
  private _observer?: ResizeObserver;

  static styles = [
    sharedStyles,
    css`
      .map {
        position: relative;
        height: calc(100vh - 220px);
        min-height: 420px;
        border: 1px solid var(--divider-color, #2a3442);
        border-radius: 8px;
        overflow: hidden;
        background: #05070a;
      }
      canvas {
        display: block;
        width: 100%;
        height: 100%;
        cursor: grab;
      }
      canvas.dragging {
        cursor: grabbing;
      }
      .bar {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .bar .grow {
        flex: 1;
      }
      .overlay {
        position: absolute;
        background: rgba(19, 26, 36, 0.94);
        border: 1px solid #2a3442;
        border-radius: 8px;
        padding: 10px 12px;
        color: #e8eef6;
        font-size: 12px;
        max-height: calc(100% - 24px);
        overflow: auto;
      }
      .legend {
        top: 12px;
        left: 12px;
        min-width: 180px;
      }
      .details {
        top: 12px;
        right: 12px;
        width: 260px;
      }
      .legend h4 {
        margin: 0 0 6px;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8b97a8;
      }
      .legend h4 + h4 {
        margin-top: 12px;
      }
      .legend .row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 3px 4px;
        border-radius: 4px;
        cursor: pointer;
      }
      .legend .row:hover {
        background: rgba(255, 255, 255, 0.05);
      }
      .legend .row.off {
        opacity: 0.38;
      }
      .legend .swatch {
        width: 10px;
        height: 10px;
        border-radius: 3px;
        flex: none;
      }
      .legend .line {
        width: 16px;
        height: 3px;
        border-radius: 2px;
        flex: none;
      }
      .legend .count {
        margin-left: auto;
        color: #8b97a8;
        font-variant-numeric: tabular-nums;
      }
      .details h3 {
        margin: 0 0 2px;
        font-size: 14px;
      }
      .details dl {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 3px 10px;
        margin: 8px 0 0;
      }
      .details dt {
        color: #8b97a8;
      }
      .details dd {
        margin: 0;
        text-align: right;
        word-break: break-word;
      }
      .hint {
        bottom: 12px;
        left: 12px;
        right: 12px;
        color: #8b97a8;
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._observer?.disconnect();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      const dataset = await fetchEntityMap(this.hass, this._options);
      this._dataset = dataset;
      this._activeGroups = new Set(dataset.groups.map((g) => g.id));
      this._activeKinds = new Set(dataset.relationKinds.map((k) => k.id));
      const last = [...dataset.scopes].sort((a, b) => b.ordinal - a.ordinal)[0];
      this._scopeIds = new Set(dataset.scopes.map((s) => s.id));
      if (!this._scopeIds.size && last) this._scopeIds = new Set([last.id]);
      this._selected = null;
    } catch (err) {
      this._error = err instanceof Error ? err.message : String(err);
    } finally {
      this._loading = false;
      this.requestUpdate();
      await this.updateComplete;
      this._attachCanvas();
      this._rebuild(true);
    }
  }

  private get _canvas(): HTMLCanvasElement | null {
    return this.renderRoot.querySelector("canvas");
  }

  private _attachCanvas() {
    const canvas = this._canvas;
    if (!canvas) return;
    this._observer?.disconnect();
    this._observer = new ResizeObserver(() => {
      const rect = canvas.getBoundingClientRect();
      this._size = { w: Math.max(1, rect.width), h: Math.max(1, rect.height) };
      this._rebuild(true);
    });
    this._observer.observe(canvas);
    canvas.addEventListener("wheel", this._onWheel, { passive: false });
  }

  /** Recompute the layout, optionally refitting the camera, then paint. */
  private _rebuild(refit: boolean) {
    const dataset = this._dataset;
    if (!dataset) return;
    const entities = dataset.entities.filter((e) => this._activeGroups.has(e.group));
    const ids = new Set(entities.map((e) => e.id));
    const relations = dataset.relations.filter(
      (r) => this._activeKinds.has(r.kind) && ids.has(r.source) && ids.has(r.target),
    );

    if (this._view === "arc") {
      const scopes = dataset.scopes
        .filter((s) => this._scopeIds.has(s.id))
        .sort((a, b) => a.ordinal - b.ordinal);
      this._layout = layoutArc({
        entities,
        events: dataset.events,
        scopes,
        groups: dataset.groups,
        width: this._size.w,
        height: this._size.h,
        sizeScale: this._sizeScale,
        axis: dataset.axis,
      });
    } else {
      this._layout = layoutForce({
        entities,
        relations,
        groups: dataset.groups,
        relationKinds: dataset.relationKinds,
        width: this._size.w,
        height: this._size.h,
        sizeScale: this._sizeScale,
        anchors: entities.filter((e) => e.emphasis).map((e) => e.id),
      });
    }
    if (refit) this._camera = fitCamera(this._layout, this._size.w, this._size.h);
    this._paint();
  }

  private _paint() {
    const canvas = this._canvas;
    const dataset = this._dataset;
    if (!canvas || !dataset) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(this._size.w * dpr);
    canvas.height = Math.round(this._size.h * dpr);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let focus: Set<string> | null = null;
    if (this._selected) {
      focus = new Set([this._selected]);
      if (this._view === "web") {
        for (const r of dataset.relations) {
          if (!this._activeKinds.has(r.kind)) continue;
          if (r.source === this._selected) focus.add(r.target);
          if (r.target === this._selected) focus.add(r.source);
        }
      }
    }

    render(ctx, this._size.w, this._size.h, {
      layout: this._layout,
      entities: new Map(dataset.entities.map((e) => [e.id, e])),
      camera: this._camera,
      showLabels: this._showLabels,
      hovered: this._hovered,
      selected: this._selected,
      focus,
      dpr,
    });
  }

  private _onWheel = (ev: WheelEvent) => {
    ev.preventDefault();
    const canvas = this._canvas;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const px = ev.clientX - rect.left;
    const py = ev.clientY - rect.top;
    const k = Math.min(12, Math.max(0.05, this._camera.k * Math.pow(0.999, ev.deltaY)));
    this._camera = {
      k,
      x: px - ((px - this._camera.x) / this._camera.k) * k,
      y: py - ((py - this._camera.y) / this._camera.k) * k,
    };
    this._paint();
  };

  private _onPointerDown = (ev: PointerEvent) => {
    (ev.currentTarget as HTMLCanvasElement).setPointerCapture(ev.pointerId);
    this._drag = { x: ev.clientX, y: ev.clientY, cam: this._camera, moved: 0 };
  };

  private _onPointerMove = (ev: PointerEvent) => {
    const canvas = ev.currentTarget as HTMLCanvasElement;
    const rect = canvas.getBoundingClientRect();
    if (this._drag) {
      const dx = ev.clientX - this._drag.x;
      const dy = ev.clientY - this._drag.y;
      this._drag.moved = Math.max(this._drag.moved, Math.hypot(dx, dy));
      this._camera = {
        k: this._drag.cam.k,
        x: this._drag.cam.x + dx,
        y: this._drag.cam.y + dy,
      };
      this._paint();
      return;
    }
    const [wx, wy] = screenToWorld(this._camera, ev.clientX - rect.left, ev.clientY - rect.top);
    const hit = pickNode(this._layout, wx, wy);
    if (hit !== this._hovered) {
      this._hovered = hit;
      this._paint();
    }
  };

  private _onPointerUp = (ev: PointerEvent) => {
    const drag = this._drag;
    this._drag = null;
    if (!drag || drag.moved > 4) return;
    const canvas = ev.currentTarget as HTMLCanvasElement;
    const rect = canvas.getBoundingClientRect();
    const [wx, wy] = screenToWorld(this._camera, ev.clientX - rect.left, ev.clientY - rect.top);
    const hit = pickNode(this._layout, wx, wy);
    this._selected = hit && hit !== this._selected ? hit : null;
    this._paint();
  };

  private _toggle(set: Set<string>, id: string, then: (next: Set<string>) => void) {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    then(next);
    this._rebuild(true);
  }

  private _exportPng() {
    const canvas = this._canvas;
    if (!canvas) return;
    const a = document.createElement("a");
    a.download = `ha-entity-map-${this._view}.png`;
    a.href = canvas.toDataURL("image/png");
    a.click();
  }

  private _renderLegend(dataset: Dataset) {
    const groupCounts: Record<string, number> = {};
    for (const e of dataset.entities) groupCounts[e.group] = (groupCounts[e.group] ?? 0) + 1;
    const kindCounts: Record<string, number> = {};
    for (const r of dataset.relations) kindCounts[r.kind] = (kindCounts[r.kind] ?? 0) + 1;

    return html`
      <div class="overlay legend">
        <h4>Shown &middot; click to filter</h4>
        ${dataset.groups.map(
          (g) => html`
            <div
              class="row ${this._activeGroups.has(g.id) ? "" : "off"}"
              @click=${() =>
                this._toggle(this._activeGroups, g.id, (n) => (this._activeGroups = n))}
            >
              <span class="swatch" style="background:${g.color}"></span>
              <span>${g.label}</span>
              <span class="count">${groupCounts[g.id] ?? 0}</span>
            </div>
          `,
        )}
        ${this._view === "web"
          ? html`
              <h4>Links &middot; click to filter</h4>
              ${dataset.relationKinds.map(
                (k) => html`
                  <div
                    class="row ${this._activeKinds.has(k.id) ? "" : "off"}"
                    @click=${() =>
                      this._toggle(this._activeKinds, k.id, (n) => (this._activeKinds = n))}
                  >
                    <span class="line" style="background:${k.color}"></span>
                    <span>${k.label}</span>
                    <span class="count">${kindCounts[k.id] ?? 0}</span>
                  </div>
                `,
              )}
            `
          : nothing}
      </div>
    `;
  }

  private _renderDetails(dataset: Dataset) {
    const entity = dataset.entities.find((e) => e.id === this._selected);
    if (!entity) return nothing;
    const links = dataset.relations.filter(
      (r) => r.source === entity.id || r.target === entity.id,
    );
    const byId = new Map(dataset.entities.map((e) => [e.id, e]));
    return html`
      <div class="overlay details">
        <h3>${entity.name}</h3>
        <div style="color:#8b97a8">${entity.kind ?? entity.group}</div>
        <dl>
          ${Object.entries(entity.meta ?? {}).map(
            ([k, v]) => html`<dt>${k}</dt>
              <dd>${String(v)}</dd>`,
          )}
          <dt>Links</dt>
          <dd>${links.length}</dd>
        </dl>
        ${links.slice(0, 40).map((r) => {
          const other = byId.get(r.source === entity.id ? r.target : r.source);
          if (!other) return nothing;
          return html`<div style="display:flex;gap:6px;align-items:center;padding:2px 0">
            <span style="color:#8b97a8">${r.label ?? r.kind}</span>
            <button
              style="margin-left:auto"
              @click=${() => {
                this._selected = other.id;
                this._paint();
              }}
            >
              ${other.name}
            </button>
          </div>`;
        })}
        <div style="margin-top:8px">
          <button @click=${() => ((this._selected = null), this._paint())}>Clear</button>
        </div>
      </div>
    `;
  }

  render() {
    if (this._loading) return html`<div class="card"><p>Loading registries...</p></div>`;
    if (this._error) {
      return html`<div class="card">
        <p>Could not build the map: ${this._error}</p>
        <button @click=${() => this._load()}>Retry</button>
      </div>`;
    }
    const dataset = this._dataset;
    if (!dataset) return nothing;

    return html`
      <div class="card">
        <div class="bar">
          <strong>${dataset.title}</strong>
          <span style="color:#8b97a8">${dataset.subtitle}</span>
          <span class="grow"></span>
          <label>
            Window
            <select
              @change=${(e: Event) => {
                const hours = Number((e.target as HTMLSelectElement).value);
                this._options = { ...this._options, hours };
                this._load();
              }}
            >
              ${[6, 12, 24, 48].map(
                (h) =>
                  html`<option value=${h} ?selected=${h === this._options.hours}>${h}h</option>`,
              )}
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              .checked=${this._options.includeHidden}
              @change=${(e: Event) => {
                const includeHidden = (e.target as HTMLInputElement).checked;
                this._options = { ...this._options, includeHidden };
                this._load();
              }}
            />
            Hidden and disabled
          </label>
          <label>
            Size
            <input
              type="range"
              min="0.4"
              max="2.2"
              step="0.05"
              .value=${String(this._sizeScale)}
              @input=${(e: Event) => {
                this._sizeScale = Number((e.target as HTMLInputElement).value);
                this._rebuild(false);
              }}
            />
          </label>
          <button
            @click=${() => {
              this._showLabels = !this._showLabels;
              this._paint();
            }}
          >
            ${this._showLabels ? "Hide labels" : "Show labels"}
          </button>
          <button
            @click=${() => {
              this._camera = fitCamera(this._layout, this._size.w, this._size.h);
              this._paint();
            }}
          >
            Fit
          </button>
          <button @click=${() => this._exportPng()}>Export PNG</button>
          <button
            @click=${() => {
              this._view = this._view === "arc" ? "web" : "arc";
              this._rebuild(true);
            }}
          >
            View: ${this._view === "arc" ? dataset.viewLabels?.arc : dataset.viewLabels?.web}
          </button>
          <button @click=${() => this._load()}>Refresh</button>
        </div>

        <div class="map">
          <canvas
            class=${this._drag ? "dragging" : ""}
            @pointerdown=${this._onPointerDown}
            @pointermove=${this._onPointerMove}
            @pointerup=${this._onPointerUp}
            @pointerleave=${() => ((this._hovered = null), this._paint())}
          ></canvas>
          ${this._renderLegend(dataset)} ${this._renderDetails(dataset)}
          <div class="overlay hint">
            ${this._view === "arc" ? dataset.arcHint : dataset.webHint} Drag to pan, wheel to
            zoom, click a node to focus.
          </div>
        </div>
      </div>
    `;
  }
}
