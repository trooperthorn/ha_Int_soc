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
  @state() private _busyUserId: string | null = null;
  @state() private _sort: SortState | null = null;
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
    try {
      const [users, risk, access] = await Promise.all([
        fetchUsers(this.hass),
        fetchRisk(this.hass),
        fetchAccessInfo(this.hass).catch(() => ({ is_owner: false })),
      ]);
      this._users = users;
      this._risk = risk;
      this._isOwner = !!access.is_owner;
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

  private async _onResetPassword(userId: string) {
    const pw = prompt("New password for this user (owner-only action):");
    if (!pw) return;
    this._busyUserId = userId;
    try {
      const res: any = await setPassword(this.hass, userId, pw);
      if (res && res.ok === false) {
        alert("Could not set password — only the account owner can reset another user's password.");
      }
    } finally {
      this._busyUserId = null;
    }
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading users…</div>`;
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
                        @click=${() => this._onResetPassword(u.id)}
                      >
                        Reset password
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
              `;
            })}
          </tbody>
        </table>
      </div>
    `;
  }
}
