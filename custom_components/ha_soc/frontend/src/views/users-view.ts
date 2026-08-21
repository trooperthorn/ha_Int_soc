import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  HaSocUser,
  RiskResult,
  fetchUsers,
  fetchRisk,
  deactivateUser,
  revokeAllSessions,
  setPassword,
} from "../data/ha-soc-ws";

@customElement("ha-soc-users-view")
export class HaSocUsersView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _users: HaSocUser[] = [];
  @state() private _risk: Record<string, RiskResult> = {};
  @state() private _loading = true;
  @state() private _busyUserId: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      const [users, risk] = await Promise.all([fetchUsers(this.hass), fetchRisk(this.hass)]);
      this._users = users;
      this._risk = risk;
    } finally {
      this._loading = false;
    }
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
              <th>User</th>
              <th>Role</th>
              <th>MFA</th>
              <th>Risk</th>
              <th>Last login</th>
              <th>Tokens</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${this._users.map((u) => {
              const risk = this._risk[u.id];
              return html`
                <tr>
                  <td>
                    <div>${u.name ?? u.id}</div>
                    ${u.is_owner ? html`<span class="tag enforced">owner</span>` : nothing}
                    ${!u.is_active ? html`<span class="tag cosmetic">disabled</span>` : nothing}
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
                        ?disabled=${this._busyUserId === u.id}
                        @click=${() => this._onRevokeAll(u.id)}
                      >
                        Revoke sessions
                      </button>
                      <button
                        class="ha-btn danger"
                        ?disabled=${this._busyUserId === u.id || u.is_owner}
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
