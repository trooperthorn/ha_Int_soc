import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { AuditEvent, HaSocUser, fetchUsers, queryAudit, verifyAuditChain } from "../data/ha-soc-ws";

const CATEGORIES = [
  "",
  "service_call",
  "login_ok",
  "login_fail",
  "token_created",
  "user_added",
  "user_updated",
  "user_removed",
  "lovelace_change",
  "entity_registry_change",
];

@customElement("ha-soc-audit-view")
export class HaSocAuditView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _events: AuditEvent[] = [];
  @state() private _users: HaSocUser[] = [];
  @state() private _loading = true;
  @state() private _category = "";
  @state() private _userId = "";
  @state() private _verifyResult: { ok: boolean; records_checked: number } | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._loadUsers();
    this._load();
  }

  private async _loadUsers() {
    // Independent of _load()'s filtered event query — this is just the
    // lookup table for rendering names and populating the filter, loaded
    // once rather than re-fetched on every filter change.
    this._users = await fetchUsers(this.hass);
  }

  private async _load() {
    this._loading = true;
    try {
      this._events = await queryAudit(this.hass, {
        category: this._category || undefined,
        user_id: this._userId || undefined,
        limit: 200,
      });
    } finally {
      this._loading = false;
    }
  }

  private _nameFor(userId: string | null): string {
    if (!userId) return "—";
    return this._users.find((u) => u.id === userId)?.name ?? userId;
  }

  private async _onVerify() {
    this._verifyResult = await verifyAuditChain(this.hass);
  }

  private _onCategoryChange(e: Event) {
    this._category = (e.target as HTMLSelectElement).value;
    this._load();
  }

  private _onUserChange(e: Event) {
    this._userId = (e.target as HTMLSelectElement).value;
    this._load();
  }

  render() {
    return html`
      <div class="card">
        <h3>Audit Log</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Every user-attributed service call, user/dashboard change, and
          best-effort login signal. Failed logins carry only a source IP — Home
          Assistant never logs the attempted username on a failed login.
        </p>
        <div class="toolbar">
          <select @change=${this._onCategoryChange}>
            ${CATEGORIES.map(
              (c) => html`<option value=${c} ?selected=${c === this._category}>${c || "All categories"}</option>`
            )}
          </select>
          <select @change=${this._onUserChange}>
            <option value="" ?selected=${this._userId === ""}>All users</option>
            ${this._users.map(
              (u) => html`<option value=${u.id} ?selected=${u.id === this._userId}>${u.name ?? u.id}</option>`
            )}
          </select>
          <span class="spacer"></span>
          <button class="ha-btn" @click=${this._onVerify}>Verify chain integrity</button>
          <button class="ha-btn" @click=${this._load}>Refresh</button>
        </div>
        ${this._verifyResult
          ? html`<p class="${this._verifyResult.ok ? "muted" : ""}" style="font-size:12.5px;">
              ${this._verifyResult.ok
                ? `Chain intact — ${this._verifyResult.records_checked} records checked.`
                : `Chain broken — see logs for the first mismatched record.`}
            </p>`
          : null}
        ${this._loading
          ? html`<div class="empty">Loading…</div>`
          : !this._events.length
          ? html`<div class="empty">No matching events.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Category</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._events.map(
                    (e) => html`
                      <tr>
                        <td>${new Date(e.ts).toLocaleString()}</td>
                        <td><span class="tag cosmetic">${e.category}</span></td>
                        <td>${this._nameFor(e.user_id)}</td>
                        <td>${e.domain ? `${e.domain}.${e.service}` : ""} ${
                          e.entity_ids?.length ? `(${e.entity_ids.join(", ")})` : ""
                        }</td>
                        <td>${e.ip ?? "—"}</td>
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
