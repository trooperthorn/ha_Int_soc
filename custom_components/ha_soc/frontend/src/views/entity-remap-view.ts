import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  BrokenEntityReference,
  EntityRegistryEntry,
  EntityRemapApplyResult,
  EntityRemapReferenceItem,
  EntityRemapReport,
  applyEntityRemap,
  fetchBrokenEntityReferences,
  fetchEntityRegistry,
  findEntityRemapReferences,
} from "../data/ha-soc-ws";

const KIND_LABELS: Record<string, string> = {
  automation: "Automations",
  script: "Scripts",
  scene: "Scenes",
  dashboard: "Views (dashboards)",
  helper: "Helpers",
  other: "Other (review manually)",
};

@customElement("ha-soc-entity-remap-view")
export class HaSocEntityRemapView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _entities: EntityRegistryEntry[] = [];
  @state() private _oldEntityId = "";
  @state() private _newEntityId = "";
  @state() private _report: EntityRemapReport | null = null;
  @state() private _finding = false;
  @state() private _applying = false;
  @state() private _applyResult: EntityRemapApplyResult | null = null;
  @state() private _broken: BrokenEntityReference[] = [];
  @state() private _brokenLoading = true;
  @state() private _brokenFilter: string | null = null;
  // Pre-selected: constrain the New/replacement suggestions to the same
  // entity domain as the Old entity (binary_sensor→binary_sensor, etc.).
  @state() private _filterSameType = true;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    const [entities, broken] = await Promise.all([
      fetchEntityRegistry(this.hass),
      fetchBrokenEntityReferences(this.hass),
    ]);
    this._entities = entities;
    this._broken = broken;
    this._brokenLoading = false;
  }

  private _labelFor(entityId: string): string {
    const entry = this._entities.find((e) => e.entity_id === entityId);
    const name = entry?.name || entry?.original_name;
    return name ? `${name} (${entityId})` : entityId;
  }

  private async _onFind() {
    if (!this._oldEntityId) return;
    this._finding = true;
    this._applyResult = null;
    try {
      this._report = await findEntityRemapReferences(this.hass, this._oldEntityId);
      this._brokenFilter = this._oldEntityId;
    } finally {
      this._finding = false;
    }
  }

  private _onFixBroken(entityId: string) {
    this._oldEntityId = entityId;
    this._newEntityId = "";
    this._report = null;
    this._applyResult = null;
    this._onFind();
  }

  // Selecting a broken entity id enters it into the Old/broken field (without
  // running the search yet), so the operator can pick a same-type replacement
  // first. Scrolls the remap card into view.
  private _selectOld(entityId: string) {
    this._oldEntityId = entityId;
    this._newEntityId = "";
    this._report = null;
    this._applyResult = null;
    this.updateComplete.then(() => {
      this.renderRoot?.querySelector("#remap-card")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  private _domainOf(entityId: string): string {
    return entityId.includes(".") ? entityId.split(".", 1)[0] : "";
  }

  // New/replacement suggestions, optionally constrained to the Old entity's
  // domain when "Filter by same Entity Type" is on.
  private _newEntityOptions(): EntityRegistryEntry[] {
    const domain = this._domainOf(this._oldEntityId);
    if (this._filterSameType && domain) {
      return this._entities.filter((e) => this._domainOf(e.entity_id) === domain);
    }
    return this._entities;
  }

  private _onClearBrokenFilter() {
    this._brokenFilter = null;
  }

  private _filteredBroken(): BrokenEntityReference[] {
    if (!this._brokenFilter) return this._broken;
    return this._broken.filter((b) => b.entity_id === this._brokenFilter);
  }

  private async _onApply() {
    if (!this._oldEntityId || !this._newEntityId) return;
    this._applying = true;
    try {
      const result = await applyEntityRemap(this.hass, this._oldEntityId, this._newEntityId);
      // _onFind() clears _applyResult as part of a fresh search — refresh
      // the report/broken list first, then set the result last so it isn't
      // wiped out before it ever gets a chance to render.
      await this._onFind();
      this._broken = await fetchBrokenEntityReferences(this.hass);
      this._applyResult = result;
    } finally {
      this._applying = false;
    }
  }

  private _renderKind(kind: string, items: EntityRemapReferenceItem[]) {
    if (!items.length) return nothing;
    return html`
      <div style="margin-bottom:12px;">
        <div style="font-size:12px;font-weight:600;color:var(--secondary-text-color);margin-bottom:4px;">
          ${KIND_LABELS[kind] ?? kind} (${items.length})
        </div>
        <table>
          <tbody>
            ${items.map(
              (item) => html`
                <tr>
                  <td>${item.name}</td>
                  <td>
                    <span class="tag ${item.editable ? "enforced" : "cosmetic"}">
                      ${item.editable ? "will fix" : "manual review"}
                    </span>
                  </td>
                  <td class="muted" style="font-size:12px;">${item.reason ?? ""}</td>
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
    `;
  }

  render() {
    const report = this._report;
    const canApply =
      !!report && report.editable_count > 0 && !!this._newEntityId && this._newEntityId !== this._oldEntityId;

    return html`
      <div class="card" id="remap-card">
        <h3>Entity ReMap</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Home Assistant has no built-in way to do this: renaming or replacing an entity
          only ever touches the entity registry — every automation, script, scene,
          dashboard, and helper that still references the old entity_id keeps that exact
          string and silently breaks. Pick the broken/old entity and its replacement below
          to find every reference and fix the ones that are safely, structurally editable.
          A reference that only exists inside a template (<code>{{ states('...') }}</code>)
          is never rewritten automatically — it's flagged for you to fix by hand instead,
          since a text rewrite there risks corrupting the template or missing a dynamic
          reference.
        </p>

        <div class="toolbar" style="align-items:flex-end;">
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">Old / broken entity</div>
            <input
              list="ha-soc-remap-old-entities"
              style="width:320px;"
              .value=${this._oldEntityId}
              placeholder="sensor.old_entity_id"
              @change=${(e: Event) => (this._oldEntityId = (e.target as HTMLInputElement).value.trim())}
            />
          </div>
          <div>
            <div class="muted" style="font-size:11px;margin-bottom:2px;">New / replacement entity</div>
            <input
              list="ha-soc-remap-new-entities"
              style="width:320px;"
              .value=${this._newEntityId}
              placeholder="sensor.new_entity_id"
              @change=${(e: Event) => (this._newEntityId = (e.target as HTMLInputElement).value.trim())}
            />
          </div>
          <button class="ha-btn" ?disabled=${!this._oldEntityId || this._finding} @click=${() => this._onFind()}>
            ${this._finding ? "Searching…" : "Find references"}
          </button>
          <label
            class="muted"
            style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;"
            title="Only suggest replacement entities in the same domain (binary_sensor, sensor, weather, …) as the old entity"
          >
            <input
              type="checkbox"
              .checked=${this._filterSameType}
              @change=${(e: Event) => (this._filterSameType = (e.target as HTMLInputElement).checked)}
            />
            Filter by same Entity Type
          </label>
          <!-- Old/broken entity only offers entities this page already knows are
               referenced-but-missing — picking from the full entity registry made
               no sense here, since a genuinely broken entity isn't in it. -->
          <datalist id="ha-soc-remap-old-entities">
            ${this._broken.map((b) => html`<option value=${b.entity_id}>${this._labelFor(b.entity_id)}</option>`)}
          </datalist>
          <!-- New/replacement entity picks from currently-registered entities,
               constrained to the old entity's domain when the checkbox is on. -->
          <datalist id="ha-soc-remap-new-entities">
            ${this._newEntityOptions().map(
              (e) => html`<option value=${e.entity_id}>${e.name ?? e.original_name ?? ""}</option>`
            )}
          </datalist>
        </div>

        ${report
          ? html`
              <div style="margin-top:12px;">
                ${report.total_count === 0
                  ? html`<div class="empty">No references to ${report.entity_id} found anywhere.</div>`
                  : html`
                      <p class="muted" style="font-size:12.5px;">
                        ${report.total_count} reference(s) found — ${report.editable_count} can be fixed
                        automatically, the rest need a manual look.
                      </p>
                      ${this._renderKind("automation", report.automation)}
                      ${this._renderKind("script", report.script)}
                      ${this._renderKind("scene", report.scene)}
                      ${this._renderKind("dashboard", report.dashboard)}
                      ${this._renderKind("helper", report.helper)}
                      ${this._renderKind("other", report.other)}
                    `}
                <button class="ha-btn" ?disabled=${!canApply || this._applying} @click=${() => this._onApply()}>
                  ${this._applying
                    ? "Applying…"
                    : `Apply remap (${report.editable_count} reference${report.editable_count === 1 ? "" : "s"})`}
                </button>
              </div>
            `
          : nothing}

        ${this._applyResult
          ? html`
              <div class="card" style="margin-top:12px;background:rgba(67,160,71,0.08);">
                <strong>Applied.</strong> ${Object.entries(this._applyResult.fixed)
                  .filter(([, count]) => count > 0)
                  .map(([kind, count]) => `${count} ${KIND_LABELS[kind] ?? kind}`)
                  .join(", ") || "Nothing needed changing."}
                ${this._applyResult.errors.length
                  ? html`<div style="color:var(--error-color);margin-top:6px;">
                      ${this._applyResult.errors.length} error(s): ${this._applyResult.errors.join("; ")}
                    </div>`
                  : nothing}
              </div>
            `
          : nothing}
      </div>

      <div class="card">
        <h3>
          Entities referenced but not found (${this._filteredBroken().length}${this._brokenFilter
            ? html` of ${this._broken.length}`
            : nothing})
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          A proactive sweep of every automation, script, scene, and structured helper —
          any entity_id they reference that doesn't correspond to a known entity right now.
          Dashboards aren't swept here (there's no equivalent core-provided index to walk
          cheaply); use the search above for a specific entity_id to also cover those.
        </p>
        ${this._brokenFilter
          ? html`
              <div class="toolbar" style="margin-bottom:8px;">
                <span class="muted" style="font-size:12px;">
                  Filtered to <code>${this._brokenFilter}</code>
                </span>
                <button class="ha-btn" @click=${() => this._onClearBrokenFilter()}>Clear filter</button>
              </div>
            `
          : nothing}
        ${this._brokenLoading
          ? html`<div class="empty">Loading…</div>`
          : !this._broken.length
            ? html`<div class="empty">Nothing found — no dangling entity references detected.</div>`
            : !this._filteredBroken().length
              ? html`<div class="empty">No broken reference matches <code>${this._brokenFilter}</code>.</div>`
              : html`
                <table>
                  <thead>
                    <tr>
                      <th>Entity ID</th>
                      <th>Referenced by</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this._filteredBroken().map(
                      (b) => html`
                        <tr>
                          <td>
                            <code
                              style="cursor:pointer;color:var(--primary-color);"
                              title="Select as the Old / broken entity"
                              @click=${() => this._selectOld(b.entity_id)}
                              >${b.entity_id}</code
                            >
                          </td>
                          <td class="muted" style="font-size:12px;">
                            ${b.referenced_by.map((r) => `${r.name} (${r.kind})`).join(", ")}
                          </td>
                          <td>
                            <button class="ha-btn" @click=${() => this._onFixBroken(b.entity_id)}>Fix…</button>
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
