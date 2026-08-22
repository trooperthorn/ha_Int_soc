import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { PeripheralOverview, fetchPeripherals, setPeripheralIgnored } from "../data/ha-soc-ws";

@customElement("ha-soc-peripherals-view")
export class HaSocPeripheralsView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _overview: PeripheralOverview | null = null;
  @state() private _loading = true;
  @state() private _busyKey: string | null = null;
  @state() private _showIgnored = false;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      this._overview = await fetchPeripherals(this.hass);
    } finally {
      this._loading = false;
    }
  }

  private async _onToggleIgnore(key: string, ignored: boolean, rawName: string) {
    this._busyKey = key;
    try {
      await setPeripheralIgnored(this.hass, key, ignored, rawName);
      await this._load();
    } finally {
      this._busyKey = null;
    }
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading peripherals…</div>`;
    const overview = this._overview;

    if (!overview || !overview.available) {
      return html`
        <div class="card">
          <h3>Local Peripherals</h3>
          <p class="muted" style="font-size:12.5px;">
            Home Assistant's own USB discovery component (<code>usb</code>) isn't
            available — it's part of every default install, so this usually only
            happens if it's been explicitly disabled. This view has nothing to read
            without it.
          </p>
        </div>
      `;
    }

    const active = overview.devices.filter((d) => !d.ignored);
    const ignored = overview.devices.filter((d) => d.ignored);

    return html`
      <div class="card">
        <h3>Local Peripherals</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          USB serial devices Home Assistant itself can see — the same discovery data
          core uses to auto-detect a Zigbee/Z-Wave USB stick, so no add-on is involved.
          This only covers serial (<code>/dev/ttyUSB*</code>/<code>/dev/ttyACM*</code>)
          devices, not every USB peripheral. "Assigned integration" is a best-effort
          match against every config entry's stored data — a miss doesn't prove a
          device is unused, only that this couldn't find it.
        </p>
        ${!overview.devices.length
          ? html`<div class="empty">
              No USB serial devices detected. If you're expecting one here, confirm
              Home Assistant actually has access to it — automatic on Home Assistant
              OS for devices your system exposes; a Container/Core install needs the
              device passed through explicitly (e.g. Docker's <code>--device</code>).
            </div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Raw Name</th>
                    <th>/dev/tty Path</th>
                    <th>Assigned Integration</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${active.map(
                    (d) => html`
                      <tr>
                        <td>${d.raw_name}</td>
                        <td class="muted">${d.tty_path}</td>
                        <td>
                          ${d.assigned_integration
                            ? html`${d.assigned_integration.title}
                                <span class="muted">(${d.assigned_integration.domain})</span>`
                            : html`<span class="pill medium"><span class="dot"></span>unassigned</span>`}
                        </td>
                        <td>
                          ${!d.assigned_integration
                            ? html`
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey === d.key}
                                  @click=${() => this._onToggleIgnore(d.key, true, d.raw_name)}
                                >
                                  Ignore
                                </button>
                              `
                            : nothing}
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      ${ignored.length
        ? html`
            <div class="card">
              <h3 style="cursor:pointer;" @click=${() => (this._showIgnored = !this._showIgnored)}>
                Ignored (${ignored.length}) ${this._showIgnored ? "▲" : "▼"}
              </h3>
              ${this._showIgnored
                ? html`
                    <table>
                      <thead>
                        <tr>
                          <th>Raw Name</th>
                          <th>/dev/tty Path</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        ${ignored.map(
                          (d) => html`
                            <tr class="row-disabled">
                              <td>${d.raw_name}</td>
                              <td class="muted">${d.tty_path}</td>
                              <td>
                                <button
                                  class="ha-btn"
                                  ?disabled=${this._busyKey === d.key}
                                  @click=${() => this._onToggleIgnore(d.key, false, d.raw_name)}
                                >
                                  Un-ignore
                                </button>
                              </td>
                            </tr>
                          `
                        )}
                      </tbody>
                    </table>
                  `
                : nothing}
            </div>
          `
        : nothing}
    `;
  }
}
