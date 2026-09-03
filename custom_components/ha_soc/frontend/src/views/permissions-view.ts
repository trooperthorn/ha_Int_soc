import { html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  HaSocUser,
  fetchUsers,
  fetchDashboards,
  fetchDashboardConfig,
  setViewVisibility,
  setDashboardFlags,
  checkDrift,
} from "../data/ha-soc-ws";

interface ViewRow {
  path: string;
  title: string;
  visibleUserIds: string[] | null; // null = visible to everyone
}

@customElement("ha-soc-permissions-view")
export class HaSocPermissionsView extends HaSocCustomizableView {
  protected get viewId() {
    return "permissions";
  }

  static styles = sharedStyles;

  @state() private _users: HaSocUser[] = [];
  @state() private _dashboards: Record<string, any>[] = [];
  @state() private _selected: string | null | undefined = undefined;
  @state() private _views: ViewRow[] = [];
  @state() private _loading = true;
  // Non-null when the users/dashboards load failed; rendered distinctly, never an empty matrix.
  @state() private _error: string | null = null;
  @state() private _drift: Record<string, unknown>[] = [];
  @state() private _viewsError: string | null = null;
  // The server's reason for the most recent rejected action; rendered inline above the matrix.
  @state() private _writeError: string | null = null;
  @state() private _sort: SortState | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      const [users, dashboards] = await Promise.all([
        fetchUsers(this.hass),
        fetchDashboards(this.hass),
      ]);
      this._users = users.filter((u) => u.is_active);
      this._dashboards = dashboards;
      if (this._selected === undefined && dashboards.length) {
        this._selected = (dashboards[0].url_path as string | null) ?? null;
      }
      if (this._selected !== undefined) await this._loadViews();
    } catch (e: any) {
      this._error = e?.message ?? String(e);
    } finally {
      this._loading = false;
    }
  }

  private async _loadViews() {
    // fetchDashboardConfig rejects with `not_found` for a dashboard with no saved config (e.g. the auto-generated default).
    this._viewsError = null;
    try {
      const config = await fetchDashboardConfig(this.hass, this._selected ?? null);
      const views = (config?.views as any[]) ?? [];
      this._views = views.map((v, i) => ({
        path: v.path ?? String(i),
        title: v.title ?? v.path ?? `View ${i + 1}`,
        visibleUserIds: Array.isArray(v.visible) ? v.visible.map((x: any) => x.user) : null,
      }));
    } catch (e: any) {
      this._views = [];
      this._viewsError =
        e?.code === "not_found"
          ? "This dashboard has no saved layout yet — Home Assistant is showing an auto-generated default until someone opens and customizes it in the dashboard editor. There's nothing here for the permissions matrix to manage until then."
          : `Could not load this dashboard's views: ${e?.message ?? e}`;
    }
  }

  private async _onSelectDashboard(e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    this._selected = value === "__default__" ? null : value;
    await this._loadViews();
  }

  private async _onToggleUser(e: Event, view: ViewRow, userId: string) {
    const box = e.target as HTMLInputElement;
    const current = view.visibleUserIds ?? this._users.map((u) => u.id);
    const wasVisible = current.includes(userId);
    const next = wasVisible ? current.filter((id) => id !== userId) : [...current, userId];
    // Writing back the full user list (== "everyone") resets to visible-to-all.
    const userIds = next.length === this._users.length ? [] : next;
    this._writeError = null;
    try {
      await setViewVisibility(this.hass, this._selected ?? null, view.path, userIds);
      await this._loadViews();
    } catch (err: any) {
      // Reset the DOM checkbox directly: the bound value never changed, so a re-render would leave the toggle standing.
      box.checked = wasVisible;
      this._writeError = `The visibility change for "${view.title}" was rejected: ${
        err?.message ?? err?.code ?? "unknown error"
      }. The checkbox was restored to the saved state.`;
    }
  }

  private async _onToggleFlag(
    e: Event,
    dashboardId: string,
    flag: "require_admin" | "show_in_sidebar",
    value: boolean
  ) {
    const box = e.target as HTMLInputElement;
    this._writeError = null;
    try {
      await setDashboardFlags(this.hass, dashboardId, { [flag]: value });
      await this._load();
    } catch (err: any) {
      // Same rollback as _onToggleUser: reset the DOM checkbox itself.
      box.checked = !value;
      this._writeError = `The ${flag} change was rejected: ${
        err?.message ?? err?.code ?? "unknown error"
      }. The checkbox was restored to the saved state.`;
    }
  }

  private async _onCheckDrift() {
    this._writeError = null;
    try {
      this._drift = await checkDrift(this.hass);
    } catch (err: any) {
      // A failed drift check must not look like "no drift"; say it failed.
      this._writeError = `Drift check failed: ${err?.message ?? err}`;
    }
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading dashboards…</div>`;
    if (this._error)
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the Permissions Matrix</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;

    const current = this._dashboards.find(
      (d) => ((d.url_path as string | null) ?? null) === (this._selected ?? null)
    );

    const sections: LayoutSection[] = [
      {
        id: "permissions",
        title: "Permissions Matrix",
        hideable: false,
        render: () => html`
      <div class="card">
        <h3>Permissions Matrix</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          <span class="tag cosmetic">UI-only</span> View/card visibility and
          <code>require_admin</code> change what a user's own frontend renders — any
          authenticated user can still fetch a dashboard's full config over the
          websocket API. The only real access-control lever is a user's
          admin/non-admin group, managed in the Users &amp; Access tab.
        </p>
        <div class="toolbar">
          <select .value=${this._selected ?? "__default__"} @change=${this._onSelectDashboard}>
            ${this._dashboards.map(
              (d) =>
                html`<option value=${(d.url_path as string | null) ?? "__default__"}>
                  ${d.title ?? d.url_path ?? "Overview"}
                </option>`
            )}
          </select>
          ${current
            ? html`
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${!!current.require_admin}
                    @change=${(e: Event) =>
                      this._onToggleFlag(
                        e,
                        current.id as string,
                        "require_admin",
                        (e.target as HTMLInputElement).checked
                      )}
                  />
                  require_admin
                </label>
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${current.show_in_sidebar !== false}
                    @change=${(e: Event) =>
                      this._onToggleFlag(
                        e,
                        current.id as string,
                        "show_in_sidebar",
                        (e.target as HTMLInputElement).checked
                      )}
                  />
                  show in sidebar
                </label>
              `
            : nothing}
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onCheckDrift}>Check drift</button>
        </div>

        ${this._writeError
          ? html`<p style="font-size:12.5px;color:var(--error-color,#db4437);">
              ${this._writeError}
            </p>`
          : nothing}
        ${this._drift.length
          ? html`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`
          : nothing}

        ${!this._views.length
          ? html`<div class="empty">
              ${this._viewsError ?? "This dashboard has no views, or is YAML-managed (read-only)."}
            </div>`
          : (() => {
              // Accessors are built inline because the user columns are
              // dynamic. With no sort chosen the dashboard's own view order
              // stands (it is the order users see in the dashboard itself);
              // a user column sorts by that user's visibility flag so
              // "what can user X see" groups together.
              const accessors: Record<string, (v: ViewRow) => unknown> = {
                view: (v) => v.title,
              };
              for (const u of this._users) {
                accessors[`user:${u.id}`] = (v) =>
                  v.visibleUserIds === null || v.visibleUserIds.includes(u.id);
              }
              const rows = sortRows(this._views, this._sort, accessors);
              const s = this._sort;
              const on = (n: SortState) => (this._sort = n);
              return html`
              <table>
                <thead>
                  <tr>
                    ${sortableTh("View", "view", s, on)}
                    ${this._users.map((u) => sortableTh(u.name ?? u.id, `user:${u.id}`, s, on))}
                  </tr>
                </thead>
                <tbody>
                  ${rows.map(
                    (v) => html`
                      <tr>
                        <td>${v.title}</td>
                        ${this._users.map((u) => {
                          const visible = v.visibleUserIds === null || v.visibleUserIds.includes(u.id);
                          return html`
                            <td>
                              <input
                                type="checkbox"
                                .checked=${visible}
                                @change=${(e: Event) => this._onToggleUser(e, v, u.id)}
                              />
                            </td>
                          `;
                        })}
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `;
            })()}
      </div>
        `,
      },
    ];
    return this._renderSections(sections);
  }
}
