import { LitElement, html, css, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";

/**
 * Shared "Customize" layout — per-user card order/visibility for every
 * card-based view in the panel (Dashboard, Network, Network Security,
 * etc.). One component (<ha-soc-customize-list>) owns all the reorder/
 * show-hide mechanics so each view only needs to describe its own cards
 * as a plain array and wire up load/save; see network-security-view.ts
 * for the reference usage.
 *
 * Interaction model, deliberately: editMode shows a compact, reorderable
 * CHROME list (title + drag handle + Up/Down buttons + Show/Hide toggle)
 * rather than live-dragging each card's full rendered content. Cards in
 * this panel can be large tables; re-rendering/measuring them on every
 * dragover would be slow and janky for no real benefit — the title alone
 * is enough to recognize and reorder a section. Exiting edit mode renders
 * the actual cards in the arranged order, respecting hidden sections.
 *
 * Reordering has two equivalent paths so this is fully keyboard-usable,
 * not mouse/touch-only the way native HTML5 drag-and-drop alone would be:
 * Up/Down buttons (real <button>s, tab/Enter/Space all work for free) and
 * native drag via the handle as a progressive-enhancement shortcut. Both
 * converge on the same _move()/emitChange() path.
 */

export interface LayoutSection {
  id: string;
  title: string;
  // `unknown`, not TemplateResult: a section's render method is usually
  // one of a view's existing private _renderX() methods, several of which
  // legitimately return lit's `nothing` sentinel (a unique symbol, not a
  // TemplateResult) when there's nothing to show — the same value any
  // ${...} expression inside an html`` template already accepts.
  render: () => unknown;
  // false for a section central enough to the page that hiding it would
  // leave the tab pointless (e.g. a single-card view's only card) — still
  // freely reorderable, just never offered a Hide button.
  hideable?: boolean;
}

export interface LayoutState {
  order: string[];
  hidden: string[];
}

export const EMPTY_LAYOUT: LayoutState = { order: [], hidden: [] };

/**
 * Every declared section, in the user's stored order where they've
 * customized it, falling back to each view's own declared array order —
 * and a section id in stored order that the view no longer declares (an
 * old id from a since-removed card) is silently dropped, never rendered
 * as a blank slot. A section the view added AFTER the user last
 * customized (an id absent from stored order) is appended at the end
 * rather than vanishing, so a future new card is never silently hidden
 * by a stale layout.
 */
export function effectiveOrder(sections: LayoutSection[], layout: LayoutState): LayoutSection[] {
  const byId = new Map(sections.map((s) => [s.id, s]));
  const seen = new Set<string>();
  const ordered: LayoutSection[] = [];
  for (const id of layout.order) {
    const s = byId.get(id);
    if (s && !seen.has(id)) {
      ordered.push(s);
      seen.add(id);
    }
  }
  for (const s of sections) {
    if (!seen.has(s.id)) {
      ordered.push(s);
      seen.add(s.id);
    }
  }
  return ordered;
}

@customElement("ha-soc-customize-list")
export class HaSocCustomizeList extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
    .customize-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 16px;
      padding: 10px;
      border-radius: var(--ha-card-border-radius, 12px);
      background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.06);
      border: 1px dashed rgba(var(--rgb-primary-color, 3, 155, 229), 0.35);
    }
    .customize-hint {
      font-size: 12px;
      color: var(--secondary-text-color);
      margin: 0 0 4px 2px;
    }
    .customize-row {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--card-background-color, #fff);
      border-radius: 8px;
      padding: 8px 10px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    }
    .customize-row.dragging {
      opacity: 0.4;
    }
    .customize-row.row-hidden {
      opacity: 0.55;
    }
    .handle {
      cursor: grab;
      color: var(--secondary-text-color);
      font-size: 16px;
      line-height: 1;
      user-select: none;
    }
    .row-title {
      flex: 1;
      font-size: 13.5px;
      font-weight: 600;
    }
    .row-hidden .row-title {
      text-decoration: line-through;
      color: var(--secondary-text-color);
    }
    .icon-btn {
      background: none;
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      padding: 3px 8px;
      color: var(--primary-text-color);
    }
    .icon-btn:hover {
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.05);
    }
    .icon-btn:disabled {
      opacity: 0.3;
      cursor: default;
    }
    .icon-btn.visibility-on {
      color: var(--primary-color);
      border-color: var(--primary-color);
    }
  `;

  @property({ attribute: false }) sections: LayoutSection[] = [];
  @property({ attribute: false }) layout: LayoutState = EMPTY_LAYOUT;
  @property({ type: Boolean }) editMode = false;

  private _dragId: string | null = null;

  render() {
    const ordered = effectiveOrder(this.sections, this.layout);
    const hiddenSet = new Set(this.layout.hidden);
    if (!this.editMode) {
      return html`${ordered.filter((s) => !hiddenSet.has(s.id)).map((s) => s.render())}`;
    }
    return html`
      <div class="customize-list">
        <p class="customize-hint">
          Drag the handle, or use ▲/▼, to reorder. Hide a section to remove it from this
          page without losing its data — you can bring it back here anytime.
        </p>
        ${ordered.map((s, i) => this._renderEditRow(s, i, ordered.length, hiddenSet.has(s.id)))}
      </div>
    `;
  }

  private _renderEditRow(section: LayoutSection, index: number, total: number, hidden: boolean) {
    return html`
      <div
        class="customize-row ${hidden ? "row-hidden" : ""} ${this._dragId === section.id ? "dragging" : ""}"
        draggable="true"
        @dragstart=${(e: DragEvent) => this._onDragStart(e, section.id)}
        @dragover=${(e: DragEvent) => e.preventDefault()}
        @drop=${(e: DragEvent) => this._onDrop(e, section.id)}
        @dragend=${() => this._onDragEnd()}
      >
        <span class="handle" aria-hidden="true" title="Drag to reorder">⠿⠿</span>
        <span class="row-title">${section.title}</span>
        <button
          type="button"
          class="icon-btn"
          title="Move up"
          ?disabled=${index === 0}
          @click=${() => this._move(section.id, -1)}
        >
          ▲
        </button>
        <button
          type="button"
          class="icon-btn"
          title="Move down"
          ?disabled=${index === total - 1}
          @click=${() => this._move(section.id, 1)}
        >
          ▼
        </button>
        ${section.hideable === false
          ? nothing
          : html`
              <button
                type="button"
                class="icon-btn ${hidden ? "" : "visibility-on"}"
                title=${hidden ? "Show this section" : "Hide this section"}
                @click=${() => this._toggleHidden(section.id)}
              >
                ${hidden ? "Show" : "Hide"}
              </button>
            `}
      </div>
    `;
  }

  private _move(id: string, direction: -1 | 1) {
    const order = effectiveOrder(this.sections, this.layout).map((s) => s.id);
    const idx = order.indexOf(id);
    const newIdx = idx + direction;
    if (idx < 0 || newIdx < 0 || newIdx >= order.length) return;
    [order[idx], order[newIdx]] = [order[newIdx], order[idx]];
    this._emitChange(order, this.layout.hidden);
  }

  private _toggleHidden(id: string) {
    const hidden = this.layout.hidden.includes(id)
      ? this.layout.hidden.filter((h) => h !== id)
      : [...this.layout.hidden, id];
    const order = effectiveOrder(this.sections, this.layout).map((s) => s.id);
    this._emitChange(order, hidden);
  }

  private _onDragStart(e: DragEvent, id: string) {
    this._dragId = id;
    e.dataTransfer?.setData("text/plain", id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
    this.requestUpdate();
  }

  private _onDrop(e: DragEvent, targetId: string) {
    e.preventDefault();
    const draggedId = this._dragId;
    if (!draggedId || draggedId === targetId) return;
    const order = effectiveOrder(this.sections, this.layout).map((s) => s.id);
    const from = order.indexOf(draggedId);
    const to = order.indexOf(targetId);
    if (from < 0 || to < 0) return;
    order.splice(from, 1);
    order.splice(to, 0, draggedId);
    this._emitChange(order, this.layout.hidden);
  }

  private _onDragEnd() {
    this._dragId = null;
    this.requestUpdate();
  }

  private _emitChange(order: string[], hidden: string[]) {
    this.dispatchEvent(
      new CustomEvent<LayoutState>("layout-change", {
        detail: { order, hidden },
        bubbles: true,
        composed: true,
      })
    );
  }
}
