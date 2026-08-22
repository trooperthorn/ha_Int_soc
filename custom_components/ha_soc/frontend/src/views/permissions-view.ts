import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
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
export class HaSocPermissionsView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _users: HaSocUser[] = [];
  @state() private _dashboards: Record<string, any>[] = [];
  @state() private _selected: string | null | undefined = undefined;
  @state() private _views: ViewRow[] = [];
  @state() private _loading = true;
  @state() private _drift: Record<string, unknown>[] = [];
  @state() private _viewsError: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
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
    } finally {
      this._loading = false;
    }
  }

  private async _loadViews() {
    // fetchDashboardConfig rejects (ha_soc/permissions/dashboard_config sends
    // a `not_found` error, not an empty result) whenever the dashboard has no
    // saved config yet — most commonly the default dashboard when nobody has
    // ever opened its editor, so Home Assistant is showing an auto-generated
    // layout instead. Left uncaught, that rejection used to bubble out of
    // _load() as an unhandled promise rejection: _views silently stayed
    // empty with no indication why, which read as "the page is broken until
    // you reselect the dashboard" even though reselecting the same
    // unconfigured dashboard can't actually fix anything.
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

  private async _onToggleUser(view: ViewRow, userId: string) {
    const current = view.visibleUserIds ?? this._users.map((u) => u.id);
    const next = current.includes(userId)
      ? current.filter((id) => id !== userId)
      : [...current, userId];
    // Writing back the full user list (== "everyone") resets to visible-to-all.
    const userIds = next.length === this._users.length ? [] : next;
    await setViewVisibility(this.hass, this._selected ?? null, view.path, userIds);
    await this._loadViews();
  }

  private async _onToggleFlag(dashboardId: string, flag: "require_admin" | "show_in_sidebar", value: boolean) {
    await setDashboardFlags(this.hass, dashboardId, { [flag]: value });
    await this._load();
  }

  private async _onCheckDrift() {
    this._drift = await checkDrift(this.hass);
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading dashboards…</div>`;

    const current = this._dashboards.find(
      (d) => ((d.url_path as string | null) ?? null) === (this._selected ?? null)
    );

    return html`
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
                      this._onToggleFlag(current.id as string, "require_admin", (e.target as HTMLInputElement).checked)}
                  />
                  require_admin
                </label>
                <label style="font-size:12.5px;display:flex;align-items:center;gap:4px;">
                  <input
                    type="checkbox"
                    .checked=${current.show_in_sidebar !== false}
                    @change=${(e: Event) =>
                      this._onToggleFlag(
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

        ${this._drift.length
          ? html`<p style="font-size:12.5px;color:var(--warning-color);">
              ${this._drift.length} view(s) no longer match the policy last applied here — likely edited directly in the dashboard editor.
            </p>`
          : nothing}

        ${!this._views.length
          ? html`<div class="empty">
              ${this._viewsError ?? "This dashboard has no views, or is YAML-managed (read-only)."}
            </div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>View</th>
                    ${this._users.map((u) => html`<th>${u.name ?? u.id}</th>`)}
                  </tr>
                </thead>
                <tbody>
                  ${this._views.map(
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
                                @change=${() => this._onToggleUser(v, u.id)}
                              />
                            </td>
                          `;
                        })}
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
