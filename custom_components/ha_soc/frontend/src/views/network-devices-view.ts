import { html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { SortState, sortRows, sortableTh } from "../sortable";
import { deviceDetailPath, navigateToHaPath } from "../nav";
import {
  InventoryChange,
  InventoryDevice,
  InventoryOverview,
  InventoryVerdict,
  fetchInventory,
  setInventoryLabel,
  setInventoryWatch,
  updateSettings,
  setInventoryVerdict,
} from "../data/ha-soc-ws";

const SOURCE_LABELS: Record<string, string> = {
  probe_arp: "Probe (ARP table)",
  probe_tcp: "Probe (TCP connect)",
  ha_registry: "Home Assistant registry",
  unifi: "UniFi controller",
};

const NAME_SOURCE_LABELS: Record<string, string> = {
  label: "your label",
  ha_registry: "Home Assistant registry",
  unifi: "UniFi controller",
  dhcp: "DHCP hostname",
  tracker: "router tracker",
  cert: "certificate subject",
};

/** Design and limits: docs/NETWORK-INVENTORY-DESIGN.md. Every command behind this view is owner-only. */
@customElement("ha-soc-network-devices-view")
export class HaSocNetworkDevicesView extends HaSocCustomizableView {
  protected get viewId() {
    return "network_devices";
  }

  static styles = sharedStyles;

  @state() private _overview: InventoryOverview | null = null;
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _busyId: string | null = null;
  @state() private _filter: "all" | InventoryVerdict = "all";
  @state() private _sort: SortState | null = null;
  @state() private _ignoredSort: SortState | null = null;
  // The device whose label is being edited, and the draft text.
  @state() private _editingId: string | null = null;
  @state() private _labelDraft = "";

  private static readonly DEVICE_SORT: Record<string, (d: InventoryDevice) => unknown> = {
    name: (d) => d.display_name?.value ?? null,
    vendor: (d) => d.vendor?.value ?? null,
    address: (d) => d.addresses[0]?.ip ?? null,
    mac: (d) => d.macs[0] ?? null,
    first_seen: (d) => d.first_seen,
    last_seen: (d) => d.last_seen,
    verdict: (d) => d.verdict,
  };

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      this._overview = await fetchInventory(this.hass);
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  private async _setEventSetting(
    key: "network_events_enabled" | "network_events_include_addresses",
    value: boolean
  ) {
    try {
      await updateSettings(this.hass, { [key]: value });
      await this._load();
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    }
  }

  private _renderEventSettings(overview: InventoryOverview) {
    return html`
      <details style="margin:8px 0;font-size:13px;">
        <summary>Automations and notifications</summary>
        <p class="muted" style="font-size:12.5px;">
          HA SOC can fire a Home Assistant event when a new device is recorded and when a watched device stops
          answering or answers again (ha_soc_network_device_new, ha_soc_network_device_down,
          ha_soc_network_device_back). Any automation on this system can read an event, so by default it carries
          only the inventory id and your label. Two blueprints that send these to a phone are in the repository
          under blueprints/automation/ha_soc.
        </p>
        <label style="display:block;">
          <input
            type="checkbox"
            .checked=${overview.events.enabled}
            @change=${(e: Event) =>
              this._setEventSetting("network_events_enabled", (e.target as HTMLInputElement).checked)}
          />
          Fire events for automations
        </label>
        <label style="display:block;">
          <input
            type="checkbox"
            .checked=${overview.events.include_addresses}
            ?disabled=${!overview.events.enabled}
            @change=${(e: Event) =>
              this._setEventSetting("network_events_include_addresses", (e.target as HTMLInputElement).checked)}
          />
          Include the MAC and IP address in each event
        </label>
      </details>
    `;
  }

  private async _setVerdict(device: InventoryDevice, verdict: InventoryVerdict) {
    this._busyId = device.id;
    try {
      await setInventoryVerdict(this.hass, device.id, verdict);
      await this._load();
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    } finally {
      this._busyId = null;
    }
  }

  private async _setWatch(device: InventoryDevice, watched: boolean) {
    this._busyId = device.id;
    try {
      await setInventoryWatch(this.hass, device.id, watched);
      await this._load();
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    } finally {
      this._busyId = null;
    }
  }

  /** Presence is only known for devices the Probe sees, on cycles from a Probe that reports it. */
  private _renderPresence(d: InventoryDevice) {
    const last = d.presence[d.presence.length - 1];
    const judged = d.missed_cycles !== undefined;
    return html`
      <div class="muted" style="font-size:12px;">${this._when(d.last_seen)}</div>
      ${!judged
        ? html`<div class="muted" style="font-size:11.5px;">presence unknown</div>`
        : d.down_since
          ? html`<span class="pill medium"><span class="dot"></span>not answering since ${this._when(d.down_since)}</span>`
          : d.missed_cycles === 0
            ? html`<span class="pill good"><span class="dot"></span>answering</span>`
            : html`<div class="muted" style="font-size:11.5px;">
                no answer for ${d.missed_cycles} scan(s)${last ? `, last answered ${this._when(last.to)}` : ""}
              </div>`}
      ${d.rtt_ms !== undefined
        ? html`<div class="muted" style="font-size:11.5px;" title="Time for a TCP connection to be accepted or refused. Not a ping.">
            TCP connect ${d.rtt_ms} ms
          </div>`
        : nothing}
      ${d.watched ? html`<div style="font-size:11.5px;">watched</div>` : nothing}
    `;
  }

  private _startLabelEdit(device: InventoryDevice) {
    this._editingId = device.id;
    this._labelDraft = device.label ?? "";
  }

  private async _saveLabel(device: InventoryDevice) {
    this._busyId = device.id;
    try {
      await setInventoryLabel(this.hass, device.id, this._labelDraft.trim() || null);
      this._editingId = null;
      await this._load();
    } catch (err: any) {
      this._error = err?.message ?? String(err);
    } finally {
      this._busyId = null;
    }
  }

  private _when(iso: string | null): string {
    if (!iso) return "unknown";
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? "unknown" : date.toLocaleString();
  }

  private _learningEnds(overview: InventoryOverview): Date | null {
    if (!overview.learning_started_at) return null;
    const start = new Date(overview.learning_started_at).getTime();
    if (Number.isNaN(start)) return null;
    return new Date(start + overview.learning_hours * 3600 * 1000);
  }

  private _renderName(d: InventoryDevice) {
    if (this._editingId === d.id) {
      return html`
        <input
          type="text"
          maxlength="64"
          aria-label="Label for this device"
          .value=${this._labelDraft}
          @input=${(ev: Event) => (this._labelDraft = (ev.target as HTMLInputElement).value)}
          @keydown=${(ev: KeyboardEvent) => {
            if (ev.key === "Enter") this._saveLabel(d);
            if (ev.key === "Escape") this._editingId = null;
          }}
        />
        <button class="ha-btn" ?disabled=${this._busyId === d.id} @click=${() => this._saveLabel(d)}>Save</button>
        <button class="ha-btn" @click=${() => (this._editingId = null)}>Cancel</button>
      `;
    }
    const name = d.display_name;
    return html`
      ${name
        ? html`${name.value}
            <div
              class="muted"
              style="font-size:11.5px;"
              title=${d.names.map((n) => `${n.value} (${NAME_SOURCE_LABELS[n.source] ?? n.source}, ${this._when(n.ts)})`).join("\n")}
            >
              from ${NAME_SOURCE_LABELS[name.source] ?? name.source}${d.names.length > 1
                ? `, ${d.names.length} names known`
                : ""}
            </div>`
        : html`<span class="muted">no name known</span>`}
      ${d.roles.length
        ? html`<div class="muted" style="font-size:11.5px;">
            ${d.roles.map((r) => (r === "gateway" ? "gateway (default route)" : "DNS server")).join(", ")}
          </div>`
        : nothing}
      ${d.ha_device_id
        ? html`<div>
            <button class="ha-btn" style="font-size:11.5px;" @click=${() => navigateToHaPath(deviceDetailPath(d.ha_device_id!))}>
              Open in Home Assistant
            </button>
          </div>`
        : nothing}
    `;
  }

  private _renderIdentity(d: InventoryDevice) {
    if (d.identity === "address") {
      return html`<span class="pill medium"><span class="dot"></span>address-keyed, weak identity</span>`;
    }
    return html`
      <span style="font-size:12px;">${d.macs[0] ?? "unknown"}</span>
      ${d.mac_kind === "local"
        ? html`<div class="muted" style="font-size:11.5px;">randomized address</div>`
        : nothing}
    `;
  }

  private _changeText(change: InventoryChange): string {
    switch (change.kind) {
      case "port_opened":
        return `Port ${change.port} opened`;
      case "port_closed":
        return `Port ${change.port} closed`;
      case "cert_changed":
        return `Certificate on port ${change.port} changed`;
      case "cert_renewed":
        return `Certificate on port ${change.port} renewed`;
      case "duplicate_address":
        return "Swapping its address with another device";
      case "device_down":
        return "Stopped answering";
      case "device_back":
        return change.minutes_away != null ? `Answering again after ${change.minutes_away} min` : "Answering again";
      case "identity_shift":
        return (change.reasons ?? []).includes("two_addresses")
          ? "Answered at two addresses at once"
          : "Ports and certificate changed together";
    }
  }

  private _renderPorts(d: InventoryDevice) {
    const certs = this._overview?.certs ?? {};
    const open = Object.entries(d.ports)
      .filter(([, record]) => !record.closed_at)
      .sort(([a], [b]) => Number(a) - Number(b));
    return html`
      ${open.length === 0
        ? html`<span class="muted">none open</span>`
        : open.map(([port, record]) => {
            const cert = record.cert_sha256 ? certs[record.cert_sha256] : undefined;
            const title = cert
              ? [
                  cert.unreadable ? "certificate could not be read" : null,
                  cert.subject && `subject: ${cert.subject}`,
                  cert.issuer && `issuer: ${cert.issuer}`,
                  cert.not_after && `expires: ${this._when(cert.not_after)}`,
                  `sha256: ${cert.sha256}`,
                ]
                  .filter(Boolean)
                  .join("\n")
              : record.cert_sha256
                ? `sha256: ${record.cert_sha256}`
                : "";
            return html`<span class="pill info" title=${title} style="margin:0 4px 2px 0;"
              >${port}${record.service ? ` ${record.service}` : ""}${record.cert_sha256 ? " (cert)" : ""}</span
            >`;
          })}
      ${d.recent_changes.map(
        (change) => html`
          <div style="font-size:11.5px;" class=${change.alert ? "" : "muted"}>
            ${this._changeText(change)}, ${this._when(change.ts)}${change.alert ? " (detection raised)" : ""}
          </div>
        `
      )}
    `;
  }

  private _renderVerdict(d: InventoryDevice) {
    const cls = d.verdict === "acknowledged" ? "good" : d.verdict === "ignored" ? "info" : "medium";
    return html`
      <span class="pill ${cls}"><span class="dot"></span>${d.verdict}</span>
      ${d.baseline && d.verdict === "unacknowledged"
        ? html`<div class="muted" style="font-size:11.5px;">present during learning</div>`
        : nothing}
    `;
  }

  private _renderActions(d: InventoryDevice) {
    const busy = this._busyId === d.id;
    return html`
      ${d.verdict !== "acknowledged"
        ? html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._setVerdict(d, "acknowledged")}>
            Acknowledge
          </button>`
        : html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._setVerdict(d, "unacknowledged")}>
            Withdraw
          </button>`}
      ${d.verdict !== "ignored"
        ? html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._setVerdict(d, "ignored")}>Ignore</button>`
        : html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._setVerdict(d, "unacknowledged")}>
            Restore
          </button>`}
      <button class="ha-btn" ?disabled=${busy} @click=${() => this._startLabelEdit(d)}>Label</button>
      ${d.watched
        ? html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._setWatch(d, false)}>Unwatch</button>`
        : d.mac_kind === "local"
          ? nothing
          : html`<button
              class="ha-btn"
              ?disabled=${busy}
              title="Raise a detection when this device stops answering, and close it when it answers again"
              @click=${() => this._setWatch(d, true)}
            >
              Watch
            </button>`}
    `;
  }

  private _renderTable(rows: InventoryDevice[], sort: SortState | null, setSort: (n: SortState) => void) {
    return html`
      <table>
        <thead>
          <tr>
            ${sortableTh("Device", "name", sort, setSort)}
            ${sortableTh("Vendor", "vendor", sort, setSort)}
            ${sortableTh("Address", "address", sort, setSort)}
            ${sortableTh("MAC", "mac", sort, setSort)}
            ${sortableTh("First seen", "first_seen", sort, setSort)}
            ${sortableTh("Last seen", "last_seen", sort, setSort)}
            <th>Open ports and recent changes</th>
            <th>Seen by</th>
            ${sortableTh("Verdict", "verdict", sort, setSort)}
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${sortRows(rows, sort, HaSocNetworkDevicesView.DEVICE_SORT).map(
            (d) => html`
              <tr class=${d.verdict === "ignored" ? "row-disabled" : ""}>
                <td>${this._renderName(d)}</td>
                <td class="muted">${d.vendor?.value ?? (d.mac_kind === "local" ? "not looked up" : "unknown")}</td>
                <td>
                  ${d.addresses[0]?.ip ?? "unknown"}
                  ${d.addresses.length > 1
                    ? html`<div class="muted" style="font-size:11.5px;">
                        also seen at: ${d.addresses.slice(1).map((a) => a.ip).join(", ")}
                      </div>`
                    : nothing}
                </td>
                <td>${this._renderIdentity(d)}</td>
                <td class="muted" style="font-size:12px;">${this._when(d.first_seen)}</td>
                <td>${this._renderPresence(d)}</td>
                <td>${this._renderPorts(d)}</td>
                <td class="muted" style="font-size:12px;">
                  ${d.sources.map((s) => SOURCE_LABELS[s] ?? s).join(", ") || "unknown"}
                  ${d.sources.includes("unifi") && !d.sources.some((s) => s.startsWith("probe_"))
                    ? html`<div>seen by UniFi only, not probed</div>`
                    : nothing}
                  ${d.unifi && (d.unifi.ssid || d.unifi.vlan !== null)
                    ? html`<div>
                        ${[d.unifi.ssid && `SSID ${d.unifi.ssid}`, d.unifi.vlan !== null && `VLAN ${d.unifi.vlan}`]
                          .filter(Boolean)
                          .join(", ")}
                      </div>`
                    : nothing}
                </td>
                <td>${this._renderVerdict(d)}</td>
                <td>${this._renderActions(d)}</td>
              </tr>
            `
          )}
        </tbody>
      </table>
    `;
  }

  render() {
    if (this._loading && !this._overview) return html`<div class="empty">Loading network devices…</div>`;
    if (this._error && !this._overview) {
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load Network devices</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;
    }
    const overview = this._overview!;
    const active = overview.devices.filter((d) => d.verdict !== "ignored");
    const ignored = overview.devices.filter((d) => d.verdict === "ignored");
    const shown = this._filter === "all" ? active : active.filter((d) => d.verdict === this._filter);
    const learningEnds = this._learningEnds(overview);
    const learning = learningEnds !== null && learningEnds.getTime() > Date.now();

    const sections: LayoutSection[] = [
      {
        id: "network_devices",
        title: "Network devices",
        hideable: false,
        render: () => html`
          <div class="card">
            <h3>Network devices</h3>
            <p class="muted" style="margin-top:-8px;font-size:12.5px;">
              One record per device the Probe's network scan has seen, kept across address changes. A device is
              identified by its MAC address, which a device can set to anything it likes: "acknowledged" means you
              recognized this MAC once, not that the device is authenticated. A device that appears after the
              learning window raises a detection until you acknowledge or ignore it.
            </p>
            ${this._error
              ? html`<p style="font-size:13px;color:var(--error-color,#db4437);">${this._error}</p>`
              : nothing}
            ${!overview.netscan_enabled
              ? html`<p style="font-size:13px;">
                  <span class="pill medium"><span class="dot"></span>not scanning</span>
                  The network scan is off, so nothing new is being recorded. Turn it on under Settings; it needs the
                  HA SOC Probe app.
                </p>`
              : nothing}
            ${overview.cycles === 0
              ? html`<p class="muted" style="font-size:13px;">
                  No scan cycle has been merged yet. This is "not scanned", not "no devices".
                </p>`
              : html`<p class="muted" style="font-size:12.5px;">
                  ${overview.cycles} scan cycles merged, the last at ${this._when(overview.last_cycle_at)}.
                  ${learning
                    ? html`Learning until ${learningEnds!.toLocaleString()}: devices seen until then are recorded
                        without a detection.`
                    : nothing}
                </p>`}
            ${overview.cap_reached_at
              ? html`<p style="font-size:13px;">
                  <span class="pill high"><span class="dot"></span>cap reached</span>
                  The inventory reached its limit of ${overview.cap} records at
                  ${this._when(overview.cap_reached_at)}. The oldest records nobody acknowledged or labeled were
                  removed to make room.
                </p>`
              : nothing}
            ${this._renderEventSettings(overview)}
            <p class="muted" style="font-size:12.5px;">
              Gateway: ${overview.network.gateway_ip ?? "not known"}${overview.network.roles_source
                ? ` (from the ${overview.network.roles_source === "probe" ? "Probe's route table" : "Supervisor's network settings"})`
                : ""}.
              DNS servers this host uses:
              ${overview.network.dns_servers.length ? overview.network.dns_servers.join(", ") : "not known"}. Internet
              side:
              ${overview.network.wan === null
                ? "not available without a UniFi controller"
                : overview.network.wan.kind === "public"
                  ? "public address on the gateway"
                  : overview.network.wan.kind === "cgnat"
                    ? "carrier-grade NAT"
                    : "behind another router (double NAT)"}.
            </p>
            <div style="display:flex;gap:6px;flex-wrap:wrap;margin:8px 0;">
              ${(
                [
                  ["all", `All (${active.length})`],
                  ["unacknowledged", `Unacknowledged (${overview.counts.unacknowledged})`],
                  ["acknowledged", `Acknowledged (${overview.counts.acknowledged})`],
                ] as const
              ).map(
                ([id, label]) => html`
                  <button
                    class="ha-btn ${this._filter === id ? "ha-btn-active" : ""}"
                    aria-pressed=${this._filter === id ? "true" : "false"}
                    @click=${() => (this._filter = id)}
                  >
                    ${label}
                  </button>
                `
              )}
              <button class="ha-btn" @click=${() => this._load()}>Refresh</button>
            </div>
            ${shown.length
              ? this._renderTable(shown, this._sort, (n) => (this._sort = n))
              : html`<div class="empty">No devices in this view.</div>`}
          </div>
        `,
      },
      {
        id: "ignored_network_devices",
        title: "Ignored network devices",
        render: () =>
          ignored.length
            ? html`
                <div class="card">
                  <h3>Ignored (${ignored.length})</h3>
                  <p class="muted" style="margin-top:-8px;font-size:12.5px;">
                    Ignored devices are still recorded and are left out of the counts. They raise no detection.
                  </p>
                  ${this._renderTable(ignored, this._ignoredSort, (n) => (this._ignoredSort = n))}
                </div>
              `
            : nothing,
      },
    ];
    return this._renderSections(sections);
  }
}
