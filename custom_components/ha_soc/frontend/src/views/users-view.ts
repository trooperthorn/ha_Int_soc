import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  HaSocUser,
  RiskResult,
  fetchAccessInfo,
  fetchUsers,
  fetchRisk,
  deactivateUser,
  revokeAllSessions,
  setPassword,
} from "../data/ha-soc-ws";

// Core's admin group id (homeassistant.auth.const.GROUP_ID_ADMIN). The
// server's D-23 gate keys on admin-GROUP membership, not the is_admin
// flag, because is_admin reads false for a deactivated admin; matching
// that here keeps the disabled buttons aligned with what the server will
// actually refuse.
const ADMIN_GROUP_ID = "system-admin";

@customElement("ha-soc-users-view")
export class HaSocUsersView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _users: HaSocUser[] = [];
  @state() private _risk: Record<string, RiskResult> = {};
  @state() private _loading = true;
  // Non-null when the load itself failed: rendered as a distinct
  // could-not-load state with the server's message, never an empty table
  // (work plan item 4.12).
  @state() private _error: string | null = null;
  @state() private _busyUserId: string | null = null;
  @state() private _sort: SortState | null = null;
  // In-panel password reset state (work plan item 4.12): the user id
  // whose reset panel is open, the masked field's value, whether the
  // owner opted OUT of the default session revocation, and the server's
  // rejection message when the write bounced.
  @state() private _pwUserId: string | null = null;
  @state() private _pwValue = "";
  @state() private _pwKeepSessions = false;
  @state() private _pwError: string | null = null;
  @state() private _pwNotice: string | null = null;
  // Whether the viewer is the account owner (from ha_soc/access/info).
  // Defaults to false and stays false when the lookup fails, so the
  // admin-target buttons below fail closed like the server gate they mirror.
  @state() private _isOwner = false;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      const [users, risk, access] = await Promise.all([
        fetchUsers(this.hass),
        fetchRisk(this.hass),
        fetchAccessInfo(this.hass).catch(() => ({ is_owner: false })),
      ]);
      this._users = users;
      this._risk = risk;
      this._isOwner = !!access.is_owner;
    } catch (err: any) {
      // A failed load must never render as an empty user list; store the
      // server's message and show the could-not-load state instead.
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  // D-23: acting on an admin-group user (deactivate, revoke sessions) is
  // owner-only server-side. The server resolves the target from hass.auth
  // and enforces regardless; disabling here only stops dead clicks.
  private _adminTargetLocked(u: HaSocUser): boolean {
    return !this._isOwner && (u.is_owner || u.groups.includes(ADMIN_GROUP_ID));
  }

  private _fmtDate(iso: string | null): string {
    if (!iso) return "never";
    const d = new Date(iso);
    return d.toLocaleString();
  }

  private async _onDeactivate(userId: string) {
    if (!confirm("Deactivate this user? All their sessions will be revoked.")) return;
    this._busyUserId = userId;
    try {
      await deactivateUser(this.hass, userId);
      await this._load();
    } finally {
      this._busyUserId = null;
    }
  }

  private async _onRevokeAll(userId: string) {
    if (!confirm("Revoke every interactive session for this user? Long-lived tokens are kept.")) return;
    this._busyUserId = userId;
    try {
      await revokeAllSessions(this.hass, userId);
      await this._load();
    } finally {
      this._busyUserId = null;
    }
  }

  // Opens (or closes) the in-panel reset row for one user. A masked
  // in-panel field replaces the old prompt() so the password is typed
  // into a real password input, never a plain-text browser dialog
  // (work plan item 4.12).
  private _onToggleResetPanel(userId: string) {
    this._pwUserId = this._pwUserId === userId ? null : userId;
    this._pwValue = "";
    this._pwKeepSessions = false;
    this._pwError = null;
    this._pwNotice = null;
  }

  private async _onSubmitPassword(userId: string) {
    if (!this._pwValue) return;
    this._busyUserId = userId;
    this._pwError = null;
    this._pwNotice = null;
    try {
      const res = await setPassword(this.hass, userId, this._pwValue, !this._pwKeepSessions);
      this._pwNotice =
        res.sessions_revoked > 0
          ? `Password set. ${res.sessions_revoked} interactive session${
              res.sessions_revoked === 1 ? "" : "s"
            } revoked; long-lived tokens were kept.`
          : this._pwKeepSessions
            ? "Password set. Existing sessions were kept at your request."
            : "Password set. No interactive sessions were active.";
      this._pwUserId = null;
      this._pwValue = "";
      this._pwKeepSessions = false;
    } catch (err: any) {
      // The server rejects with its own reason (owner_required and
      // friends); render that message in the panel instead of a silent
      // failure or a browser alert.
      this._pwError = err?.message ?? "Could not set the password.";
    } finally {
      this._busyUserId = null;
    }
  }

  // The expanded reset row for one user: a masked in-panel field, the
  // honest statement of the default session revocation, and an explicit
  // unchecked-by-default opt-out wired to revoke_sessions: false.
  private _renderPasswordPanel(u: HaSocUser) {
    return html`
      <tr>
        <td colspan="7" style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.03);">
          <div style="display:flex;flex-direction:column;gap:8px;max-width:560px;">
            <div style="font-weight:600;font-size:13px;">
              Set a new password for ${u.name ?? u.id}
            </div>
            <div class="muted" style="font-size:12.5px;line-height:1.5;">
              Setting the password also revokes every interactive session this user
              holds, so anyone signed in with the old password is signed out
              immediately. Long-lived access tokens are kept either way. Owner-only
              action, recorded in the audit log.
            </div>
            <input
              type="password"
              autocomplete="new-password"
              placeholder="New password"
              style="max-width:280px;"
              .value=${this._pwValue}
              @input=${(e: Event) => (this._pwValue = (e.target as HTMLInputElement).value)}
            />
            <label
              style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;"
            >
              <input
                type="checkbox"
                .checked=${this._pwKeepSessions}
                @change=${(e: Event) =>
                  (this._pwKeepSessions = (e.target as HTMLInputElement).checked)}
              />
              Also keep this user's current sessions (not recommended: whoever holds
              the old password stays signed in)
            </label>
            ${this._pwError
              ? html`<div style="color:var(--error-color,#db4437);font-size:12.5px;">
                  ${this._pwError}
                </div>`
              : nothing}
            <div class="toolbar" style="margin:0;">
              <button
                class="ha-btn"
                ?disabled=${!this._pwValue || this._busyUserId === u.id}
                @click=${() => this._onSubmitPassword(u.id)}
              >
                ${this._busyUserId === u.id ? "Setting…" : "Set password"}
              </button>
              <button class="ha-btn" @click=${() => this._onToggleResetPanel(u.id)}>Cancel</button>
            </div>
          </div>
        </td>
      </tr>
    `;
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading users…</div>`;
    if (this._error)
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Users &amp; Access</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;
    if (!this._users.length) return html`<div class="empty">No users found.</div>`;

    // Accessors live here (not in a static map) because Risk needs this._risk.
    // Last login sorts by the parsed timestamp, never the locale string;
    // Risk sorts by the numeric score; MFA/Role sort so like values group.
    const s = this._sort;
    const on = (next: SortState) => {
      this._sort = next;
    };
    const users = sortRows(this._users, s, {
      user: (u) => u.name ?? u.id,
      role: (u) => `${u.is_admin ? "Admin" : "User"}${u.local_only ? " · local only" : ""}`,
      mfa: (u) => u.mfa_enabled,
      risk: (u) => this._risk[u.id]?.score ?? null,
      last_login: (u) => (u.last_login_at ? Date.parse(u.last_login_at) : null),
      tokens: (u) => u.llat_count,
    });

    return html`
      <div class="card">
        <h3>Users &amp; Access</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Last login is derived from refresh-token activity — a background token
          refresh looks the same as a fresh interactive login. MFA status is read
          directly from the auth store but cannot be enforced by Home Assistant.
        </p>
        ${this._pwNotice
          ? html`<p class="muted" style="font-size:12.5px;">${this._pwNotice}</p>`
          : nothing}
        <table>
          <thead>
            <tr>
              ${sortableTh("User", "user", s, on)}
              ${sortableTh("Role", "role", s, on)}
              ${sortableTh("MFA", "mfa", s, on)}
              ${sortableTh("Risk", "risk", s, on)}
              ${sortableTh("Last login", "last_login", s, on)}
              ${sortableTh("Tokens", "tokens", s, on)}
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${users.map((u) => {
              const risk = this._risk[u.id];
              return html`
                <tr class=${u.is_active ? "" : "row-disabled"}>
                  <td>
                    <div>${u.name ?? u.id}</div>
                    ${u.is_owner ? html`<span class="tag enforced">owner</span>` : nothing}
                    ${!u.is_active ? html`<span class="tag cosmetic">deactivated</span>` : nothing}
                  </td>
                  <td>${u.is_admin ? "Admin" : "User"}${u.local_only ? " · local only" : ""}</td>
                  <td>
                    ${u.mfa_enabled
                      ? html`<span class="pill good"><span class="dot"></span>enabled</span>`
                      : u.mfa_assessable === false
                        ? html`<span
                            class="muted"
                            title="Every credential this user has comes from an external auth provider (SSO/header proxy, trusted networks, or a command-line provider). Home Assistant cannot see a second factor enforced upstream, so MFA cannot be assessed for this account."
                            >not assessable</span
                          >`
                        : html`<span class="pill high"><span class="dot"></span>none</span>`}
                  </td>
                  <td>
                    ${risk
                      ? html`<span class="pill ${risk.band === "critical" || risk.band === "high" ? "high" : risk.band === "moderate" ? "medium" : "good"}">
                          <span class="dot"></span>${risk.score}
                        </span>`
                      : html`<span class="muted">—</span>`}
                  </td>
                  <td>
                    <div>${this._fmtDate(u.last_login_at)}</div>
                    ${u.last_login_ip ? html`<div class="muted">${u.last_login_ip}</div>` : nothing}
                  </td>
                  <td>
                    ${u.llat_count > 0
                      ? html`<span class="chip">${u.llat_count} long-lived</span>`
                      : html`<span class="muted">none</span>`}
                  </td>
                  <td>
                    <div class="toolbar" style="margin:0;">
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId === u.id || u.is_owner}
                        @click=${() => this._onToggleResetPanel(u.id)}
                      >
                        ${this._pwUserId === u.id ? "Close" : "Reset password"}
                      </button>
                      <button
                        class="ha-btn"
                        ?disabled=${this._busyUserId === u.id || this._adminTargetLocked(u)}
                        title=${this._adminTargetLocked(u)
                          ? "This user is in the admin group; only the account owner can revoke an administrator's sessions."
                          : ""}
                        @click=${() => this._onRevokeAll(u.id)}
                      >
                        Revoke sessions
                      </button>
                      <button
                        class="ha-btn danger"
                        ?disabled=${this._busyUserId === u.id || u.is_owner || this._adminTargetLocked(u)}
                        title=${this._adminTargetLocked(u)
                          ? "This user is in the admin group; only the account owner can deactivate an administrator."
                          : ""}
                        @click=${() => this._onDeactivate(u.id)}
                      >
                        Deactivate
                      </button>
                    </div>
                  </td>
                </tr>
                ${this._pwUserId === u.id ? this._renderPasswordPanel(u) : nothing}
              `;
            })}
          </tbody>
        </table>
      </div>
    `;
  }
}
