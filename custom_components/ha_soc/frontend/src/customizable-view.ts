import { LitElement, html } from "lit";
import { property, state } from "lit/decorators.js";
import type { HomeAssistant } from "./types";
import { EMPTY_LAYOUT, LayoutSection, LayoutState, effectiveOrder } from "./customize";
import "./customize";
import { fetchLayout, saveLayout } from "./data/ha-soc-ws";

/**
 * Base class for card-based views that participate in "Customize" (see
 * customize.ts): implement `viewId` and build a `LayoutSection[]` from the
 * cards the view already renders.
 */
export abstract class HaSocCustomizableView extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean }) customizeMode = false;

  @state() protected _layout: LayoutState = EMPTY_LAYOUT;

  /** Stable id for this view's stored layout, one per SocTab, see nav.ts. */
  protected abstract get viewId(): string;

  connectedCallback(): void {
    super.connectedCallback();
    this._loadLayout();
  }

  private async _loadLayout() {
    try {
      this._layout = await fetchLayout(this.hass, this.viewId);
    } catch {
      // Best-effort: a failed load falls back to declared default order, nothing hidden.
      this._layout = EMPTY_LAYOUT;
    }
  }

  protected _onLayoutChange = (e: CustomEvent<LayoutState>): void => {
    this._layout = e.detail;
    // Fire-and-forget: a failed save only means the change does not survive a refresh.
    saveLayout(this.hass, this.viewId, e.detail).catch(() => {});
  };

  /**
   * Render the view's sections in stored order, or the shared editor in
   * Customize mode. Section templates render here, in the view's own shadow
   * root, because sharedStyles and the view's styles apply only inside it;
   * see docs/design.md.
   */
  protected _renderSections(sections: LayoutSection[]) {
    if (this.customizeMode) {
      return html`
        <ha-soc-customize-list
          .sections=${sections}
          .layout=${this._layout}
          @layout-change=${this._onLayoutChange}
        ></ha-soc-customize-list>
      `;
    }
    const hidden = new Set(this._layout.hidden);
    return html`${effectiveOrder(sections, this._layout)
      .filter((section) => !hidden.has(section.id))
      .map((section) => section.render())}`;
  }
}
