import { LitElement, html } from "lit";
import { property, state } from "lit/decorators.js";
import type { HomeAssistant } from "./types";
import { EMPTY_LAYOUT, LayoutSection, LayoutState } from "./customize";
import "./customize";
import { fetchLayout, saveLayout } from "./data/ha-soc-ws";

/**
 * Base class for every card-based view that participates in "Customize"
 * (see customize.ts for the mechanics). Handles the boilerplate every
 * such view needs identically — loading/saving its own layout, and
 * rendering its declared sections through <ha-soc-customize-list> — so
 * each view only has to implement `viewId` and build a `LayoutSection[]`
 * from the cards it already renders.
 *
 * A view that does NOT want to participate (Settings: its cards are a
 * config form, not browsable resources — hiding one would hide controls,
 * not decorate a table) simply keeps extending LitElement directly
 * instead of this class, same as before this existed.
 */
export abstract class HaSocCustomizableView extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean }) customizeMode = false;

  @state() protected _layout: LayoutState = EMPTY_LAYOUT;

  /** Stable id for this view's stored layout — one per SocTab, see nav.ts. */
  protected abstract get viewId(): string;

  connectedCallback(): void {
    super.connectedCallback();
    this._loadLayout();
  }

  private async _loadLayout() {
    try {
      this._layout = await fetchLayout(this.hass, this.viewId);
    } catch {
      // Best-effort: a failed load just means "use each section's own
      // declared default order, nothing hidden" for this session.
      this._layout = EMPTY_LAYOUT;
    }
  }

  protected _onLayoutChange = (e: CustomEvent<LayoutState>): void => {
    this._layout = e.detail;
    // Fire-and-forget: a failed save costs nothing worse than the
    // rearrangement not surviving a refresh; it stays applied right now.
    saveLayout(this.hass, this.viewId, e.detail).catch(() => {});
  };

  /** Wrap a view's declared sections in the shared reorder/show-hide list. */
  protected _renderSections(sections: LayoutSection[]) {
    return html`
      <ha-soc-customize-list
        .sections=${sections}
        .layout=${this._layout}
        .editMode=${this.customizeMode}
        @layout-change=${this._onLayoutChange}
      ></ha-soc-customize-list>
    `;
  }
}
