import { html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { navigate } from "../nav";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  ApLogAnalysis,
  IpsBlockLog,
  IpsBlockRow,
  IpsPosture,
  SshAnalysis,
  StoredIpsPosture,
  AclReport,
  AclRule,
  FirewallPoliciesReport,
  FirewallPolicy,
  NetworkSecurityFinding,
  LedgerDrift,
  NetworkSecurityOverview,
  SshRunResult,
  SshStatus,
  clearSshKey,
  fetchSshStatus,
  forgetSshHostKey,
  generateSshKey,
  runSshCommands,
  PiHoleOverview,
  ServerPortsReport,
  UnifiLedgerState,
  acceptUnifiBaseline,
  fetchAccessInfo,
  fetchNetworkSecurityOverview,
  fetchUnifiLedger,
  setSuggestionDecision,
  applySuggestion,
} from "../data/ha-soc-ws";

// Section ids are the ledger's own; the labels are the panel's.
const LEDGER_SECTION_LABELS: Record<string, string> = {
  networks: "Networks",
  zones: "Firewall zones",
  firewall_policies: "Firewall policies",
  acl_rules: "ACL rules",
  devices: "Devices",
};
import { matchClientsForEntries } from "../device-match";
import { buildZoneMatrix } from "../firewall-matrix";

// Security-audit surface: findings, Firewall Policies (zone-based), ACL Rules, HA server ports, Pi-hole.
@customElement("ha-soc-network-security-view")
export class HaSocNetworkSecurityView extends HaSocCustomizableView {
  protected get viewId() {
    return "network_security";
  }

  static styles = [
    sharedStyles,
    css`
      .ssh-key,
      .ssh-out {
        background: rgba(127, 127, 127, 0.1);
        border: 1px solid var(--divider-color, #444);
        border-radius: 4px;
        padding: 8px;
        font-size: 11.5px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-all;
        overflow-x: auto;
        max-height: 320px;
      }
      .ssh-out.ssh-err {
        border-color: var(--error-color, #db4437);
      }
      .pill-pass {
        background: var(--success-color, #43a047);
        color: #fff;
      }
      .pill-fail {
        background: var(--error-color, #db4437);
        color: #fff;
      }
      .pill-unknown {
        background: var(--warning-color, #ffa600);
        color: #000;
      }
      .table-wrap {
        overflow-x: auto;
      }
      td.num,
      th.num {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }
      .mono {
        font-family: var(--code-font-family, monospace);
        font-size: 12px;
      }
      .match {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 100px;
      }
      .match.failing {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      .match.healthy {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      .match.other {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        color: var(--secondary-text-color);
      }
      .chips {
        display: inline-flex;
        flex-wrap: wrap;
        gap: 4px;
      }
      .chip {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.06);
        border-radius: 100px;
        padding: 2px 8px;
        font-size: 11px;
      }
      .badge-custom {
        display: inline-block;
        margin-left: 6px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        padding: 1px 7px;
        border-radius: 100px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.15);
        color: var(--primary-color);
        vertical-align: middle;
      }
      .sub {
        display: block;
        font-size: 11px;
        color: var(--secondary-text-color);
        margin-top: 2px;
      }
      .note {
        font-size: 11.5px;
        color: var(--secondary-text-color);
        margin-top: 8px;
        line-height: 1.5;
      }
      .finding {
        display: flex;
        gap: 12px;
        padding: 10px 0;
        border-top: 1px solid var(--divider-color);
      }
      .finding:first-of-type {
        border-top: none;
      }
      .sev {
        flex: 0 0 auto;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 6px;
      }
      .sev.high {
        background: var(--status-critical, #d03b3b);
      }
      .sev.medium {
        background: var(--status-warning, #fab219);
      }
      .sev.info {
        background: var(--cat-other, #9aa0a6);
      }
      .finding-title {
        font-weight: 600;
        font-size: 13.5px;
      }
      .finding-detail {
        font-size: 12.5px;
        color: var(--secondary-text-color);
        margin-top: 3px;
        line-height: 1.5;
      }
      .stat-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 4px;
      }
      .stat-tile {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 2px rgba(0, 0, 0, 0.08));
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .stat-tile .label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--secondary-text-color);
      }
      .stat-tile .value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
      }
      .domain-list {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12.5px;
        max-height: 220px;
        overflow-y: auto;
      }
      .domain-list .row {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 3px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .domain-list .row:last-child {
        border-bottom: none;
      }
      .view-toggle {
        display: inline-flex;
        border: 1px solid var(--divider-color);
        border-radius: 100px;
        overflow: hidden;
        margin-bottom: 10px;
      }
      .view-toggle button {
        border: none;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
        font-size: 12px;
        font-weight: 600;
        padding: 5px 14px;
        cursor: pointer;
      }
      .view-toggle button.active {
        background: var(--primary-color);
        color: #fff;
      }
      .device-chip {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.1);
        color: var(--primary-color);
        border: none;
        border-radius: 100px;
        padding: 1px 8px;
        font-size: 10.5px;
        cursor: pointer;
        margin: 2px 3px 0 0;
      }
      .device-chip:hover {
        background: rgba(var(--rgb-primary-color, 3, 155, 229), 0.2);
      }
      .matrix-wrap {
        overflow-x: auto;
      }
      table.zone-matrix {
        border-collapse: collapse;
      }
      table.zone-matrix th,
      table.zone-matrix td {
        border: 1px solid var(--divider-color);
        padding: 6px;
        text-align: center;
        font-size: 11.5px;
      }
      table.zone-matrix th {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.03);
        font-weight: 600;
      }
      table.zone-matrix th.corner {
        background: transparent;
        border: none;
      }
      table.zone-matrix td.cell {
        cursor: pointer;
        min-width: 64px;
      }
      table.zone-matrix td.cell:hover {
        outline: 2px solid var(--primary-color);
        outline-offset: -2px;
      }
      table.zone-matrix td.cell.allow {
        background: rgba(67, 160, 71, 0.15);
        color: var(--success-color, #43a047);
      }
      table.zone-matrix td.cell.block {
        background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15);
        color: var(--error-color, #db4437);
      }
      table.zone-matrix td.cell.mixed {
        background: rgba(var(--status-warning, #fab219), 0.18);
        color: #9a6a00;
      }
      table.zone-matrix td.cell.none {
        color: var(--secondary-text-color);
      }
      .zone-pair-filter {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12.5px;
        margin-bottom: 10px;
      }
    `,
  ];

  @state() private _overview: NetworkSecurityOverview | null = null;
  @state() private _loading = true;
  @state() private _error: string | null = null;
  @state() private _aclSort: SortState | null = null;
  @state() private _firewallPolicySort: SortState | null = null;
  @state() private _portSort: SortState | null = null;
  // Firewall Policies card: the policy table or the suggested-changes tab; the Zone Matrix is its own section
  // and a matrix cell filters the table to one zone pair (null clears).
  @state() private _fwViewMode: "table" | "suggestions" = "table";
  @state() private _fwZonePairFilter: { src: string; dst: string } | null = null;
  @state() private _suggestionBusy: string | null = null;
  @state() private _suggestionError: string | null = null;
  @state() private _ledger: UnifiLedgerState | null = null;
  @state() private _ledgerBusy = false;
  @state() private _ledgerError: string | null = null;
  // Cosmetic: the Accept command is owner-gated on the server regardless.
  @state() private _isOwner = false;
  @state() private _ssh: SshStatus | null = null;
  @state() private _sshHost = "";
  @state() private _sshSelected: string[] = ["whoami"];
  @state() private _sshRun: SshRunResult | null = null;
  @state() private _sshBusy = false;
  @state() private _sshError: string | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      this._overview = await fetchNetworkSecurityOverview(this.hass);
    } catch (e) {
      this._error = e instanceof Error ? e.message : String(e);
      this._overview = null;
    } finally {
      this._loading = false;
    }
    // The ledger and the owner check load independently: either failing must
    // not take the rest of the tab down with it.
    try {
      this._isOwner = !!(await fetchAccessInfo(this.hass)).is_owner;
    } catch {
      this._isOwner = false;
    }
    if (this._isOwner) {
      try {
        this._ssh = await fetchSshStatus(this.hass);
      } catch {
        this._ssh = null;
      }
    }
    try {
      this._ledger = await fetchUnifiLedger(this.hass);
    } catch (e) {
      this._ledger = {
        available: false,
        error: e instanceof Error ? e.message : String(e),
        application_version: null,
        baseline: null,
        current: null,
        drift: null,
        history: [],
      };
    }
  }

  render() {
    if (this._loading) return html`<div class="card">Loading…</div>`;
    if (this._error) {
      return html`<div class="card"><div class="alert">${this._error}</div></div>`;
    }
    const o = this._overview;
    if (!o) return html`<div class="card">No data.</div>`;

    const sections: LayoutSection[] = [
      { id: "findings", title: "Suggestions", render: () => this._renderFindings(o.findings) },
      {
        id: "firewall_policies",
        title: "Firewall Policies",
        render: () => this._renderFirewallPolicies(o.firewall_policies, o.findings, o.write_enabled),
      },
      { id: "zone_matrix", title: "Zone Matrix", render: () => this._renderZoneMatrixCard(o.firewall_policies) },
      { id: "acl", title: "ACL Rules", render: () => this._renderAcl(o.acl) },
      {
        id: "config_ledger",
        title: "Configuration Baseline",
        render: () => this._renderConfigLedger(),
      },
      { id: "device_ssh", title: "Device SSH", render: () => this._renderDeviceSsh() },
      { id: "server_ports", title: "Home Assistant Server Ports", render: () => this._renderServerPorts(o.server_ports) },
      { id: "pihole", title: "Pi-hole DNS", render: () => this._renderPihole(o.pihole) },
    ];
    return html`
      <div class="toolbar" style="margin-bottom:12px;display:flex;gap:8px;align-items:center;">
        <button class="ha-btn" @click=${() => this._load()}>Refresh</button>
        <span class="muted" style="font-size:12px;">
          ${o.write_enabled
            ? "Advisory, except Apply on the Suggested changes tab, which disables the named rule or policy on the controller through the write-scoped key."
            : "Advisory only — nothing on this tab changes UniFi or Pi-hole configuration."}
        </span>
      </div>
      ${this._renderSections(sections)}
    `;
  }




  private _renderDeviceSsh() {
    const status = this._ssh;
    if (!this._isOwner) {
      return html`
        <div class="card">
          <h3>Device SSH</h3>
          <p class="muted">Owner only. Every ha_soc/ssh command is refused for other accounts.</p>
        </div>
      `;
    }
    if (!status) {
      return html`<div class="card"><h3>Device SSH</h3><p class="muted">Loading…</p></div>`;
    }

    return html`
      <div class="card">
        <h3>Device SSH</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Read-only. Commands come from a fixed allowlist in the integration, so there is no
          way to send an arbitrary string to a device. Output is shown here and nowhere else:
          it is not stored, and the audit record keeps the outcomes, not the text. The one
          exception is the parsed Threat Management posture from ips_config, which is kept
          so the Suggestions above can use it between runs.
        </p>
        ${this._renderStoredIpsPosture()}

        ${!status.enabled
          ? html`<p class="muted">
              Collection is off. Turn it on under Settings, Device SSH Collection.
            </p>`
          : nothing}

        <h4 style="margin:14px 0 6px;font-size:13px;">Key</h4>
        ${status.has_keypair
          ? html`
              <p class="muted" style="font-size:12px;">
                Paste this into the controller under Device Authentication, SSH Keys, then wait
                for the devices to re-provision. The private half stays in the secret store.
              </p>
              <pre class="ssh-key">${status.public_key}</pre>
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button class="ha-btn" ?disabled=${this._sshBusy} @click=${() => this._sshKey("generate")}>
                  Replace keypair
                </button>
                <button class="ha-btn" ?disabled=${this._sshBusy} @click=${() => this._sshKey("clear")}>
                  Delete keypair
                </button>
              </div>
              <p class="muted" style="font-size:11.5px;">
                Replacing or deleting locks HA SOC out of every device until the controller
                pushes the new key.
              </p>
            `
          : html`
              <p class="muted" style="font-size:12px;">No keypair yet.</p>
              <button class="ha-btn" ?disabled=${this._sshBusy} @click=${() => this._sshKey("generate")}>
                Generate keypair
              </button>
            `}

        <h4 style="margin:16px 0 6px;font-size:13px;">Run</h4>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;">
          <input
            type="text"
            placeholder="Device address"
            .value=${this._sshHost}
            @input=${(e: Event) => (this._sshHost = (e.target as HTMLInputElement).value)}
            style="padding:6px 8px;min-width:180px;"
          />
          <button
            class="ha-btn"
            ?disabled=${!status.enabled ||
            !status.has_keypair ||
            !this._sshHost.trim() ||
            !this._sshSelected.length ||
            this._sshBusy}
            @click=${() => this._runSsh()}
          >
            ${this._sshBusy ? "Running…" : "Run selected"}
          </button>
          ${this._sshError
            ? html`<span class="alert" style="font-size:12px;">${this._sshError}</span>`
            : nothing}
        </div>

        <div style="display:grid;gap:4px;margin-bottom:10px;">
          ${status.commands.map(
            (c) => html`
              <label style="display:flex;gap:8px;align-items:flex-start;font-size:12.5px;">
                <input
                  type="checkbox"
                  .checked=${this._sshSelected.includes(c.id)}
                  @change=${(e: Event) =>
                    this._toggleSshCommand(c.id, (e.target as HTMLInputElement).checked)}
                />
                <span>
                  <code>${c.argv}</code>
                  ${c.verified
                    ? nothing
                    : html`<span class="pill" style="margin-left:6px;">unverified</span>`}
                  <span class="muted" style="display:block;font-size:11.5px;">${c.description}</span>
                </span>
              </label>
            `
          )}
        </div>

        ${this._sshRun ? this._renderSshRun(this._sshRun) : nothing}
        ${Object.keys(status.host_keys).length
          ? html`
              <h4 style="margin:16px 0 6px;font-size:13px;">Pinned host keys</h4>
              <table class="tbl">
                <thead><tr><th>Device</th><th>Fingerprint</th><th>Pinned</th><th></th></tr></thead>
                <tbody>
                  ${Object.entries(status.host_keys).map(
                    ([host, entry]) => html`
                      <tr>
                        <td>${host}</td>
                        <td style="font-family:monospace;font-size:11.5px;">${entry.fingerprint}</td>
                        <td>${new Date(entry.pinned_at).toLocaleString()}</td>
                        <td>
                          <button class="ha-btn" @click=${() => this._forgetHostKey(host)}>Forget</button>
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `
          : nothing}
      </div>
    `;
  }

  // The access point's own record of who tried to join and what stopped them.
  // No controller API carries this; see unifi_ap_log.py.
  private _renderApLogAnalysis(a: ApLogAnalysis) {
    if (!a.wireless_activity) {
      return html`
        <div class="alert" style="margin:6px 0;">
          This log contains no wireless events, so it says nothing about who tried to join.
          ${a.controller_unreachable
            ? html`It is also full of failed controller informs
                (${a.inform_failures} in this excerpt), which is what an access point that
                cannot reach the controller produces.`
            : nothing}
        </div>
      `;
    }
    if (!a.clients.length) {
      return html`<p class="muted" style="margin:6px 0;font-size:12px;">
        Wireless activity present, but no station-tracker records in this excerpt.
      </p>`;
    }
    return html`
      <table style="margin:6px 0;">
        <thead>
          <tr>
            <th>Client</th>
            <th>SSID VAP</th>
            <th>Attempts</th>
            <th>Stopped at</th>
            <th>Signal</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          ${a.clients.map(
            (c) => html`
              <tr>
                <td class="mono">${c.mac}</td>
                <td>${c.vap ?? "—"}</td>
                <td>
                  ${c.attempts}
                  ${c.failures
                    ? html`<span class="muted">(${c.failures} failed)</span>`
                    : nothing}
                </td>
                <td>
                  ${c.failures && !c.ever_succeeded
                    ? html`<span class="pill pill-fail">${c.last_stage}</span>`
                    : html`<span class="muted">${c.last_outcome}</span>`}
                </td>
                <td>
                  ${c.worst_rssi !== null ? `${c.worst_rssi} dBm` : "—"}
                </td>
                <td>${c.last_reason ?? (c.last_reason_code ?? "—")}</td>
              </tr>
            `
          )}
        </tbody>
      </table>
    `;
  }

  private _renderStoredIpsPosture() {
    const stored: StoredIpsPosture | null | undefined = this._overview?.ips_posture;
    if (!stored) {
      return html`<p class="muted" style="font-size:12px;">
        Threat Management has not been read yet. Run ips_config against the gateway to add
        the IDS coverage checks to Suggestions.
      </p>`;
    }
    return html`<p class="muted" style="font-size:12px;">
      Threat Management posture last read from <span class="mono">${stored.host}</span> at
      <span class="mono">${stored.collected_at.replace("T", " ").slice(0, 19)}</span>:
      ${stored.posture.mode}${stored.posture.exempt_networks.length
        ? `, ${stored.posture.exempt_networks.length} network(s) never alerted on`
        : ""}. Run ips_config again after changing the gateway.
    </p>`;
  }

  // Every analysis carries `kind`; the access point log predates the field
  // and is the default.
  private _renderAnalysis(a: SshAnalysis) {
    if (a.kind === "ips_config") return this._renderIpsPosture(a);
    if (a.kind === "ips_block_log") return this._renderIpsBlockLog(a);
    return this._renderApLogAnalysis(a as ApLogAnalysis);
  }

  // The gateway's Threat Management posture. The findings that follow from
  // it (the server exempted, HOME_NET not covering it, Detect-only, off)
  // are computed server-side and appear under Suggestions after the next
  // refresh; this is the evidence they rest on.
  private _renderIpsPosture(p: IpsPosture) {
    const missing = Object.entries(p.parsed)
      .filter(([, ok]) => !ok)
      .map(([name]) => name);
    const modeClass =
      p.mode === "prevent" ? "good" : p.mode === "detect" ? "medium" : p.mode === "off" ? "high" : "info";
    const yesNo = (v: boolean | null) => (v === null ? "unknown" : v ? "yes" : "no");
    return html`
      ${missing.length
        ? html`<div class="alert" style="margin:6px 0;">
            ${missing.length} of 6 files did not come back (${missing.join(", ")}). The lists
            below that depend on them are unknown, not empty.
          </div>`
        : nothing}
      <table style="margin:6px 0;">
        <tbody>
          <tr>
            <th>Mode</th>
            <td>
              <span class="pill ${modeClass}"><span class="dot"></span>${p.mode}</span>
              ${p.mode === "prevent"
                ? html`<span class="muted"> ${p.drop_categories.length} categories block${
                    p.block_time_seconds !== null ? `, ${p.block_time_seconds} s per block` : ""
                  }</span>`
                : p.mode === "detect"
                  ? html`<span class="muted"> ${p.alert_categories.length} categories alert, none block</span>`
                  : nothing}
            </td>
          </tr>
          <tr>
            <th>Threat logging</th>
            <td>${yesNo(p.logging_threat_event)}</td>
          </tr>
          <tr>
            <th>SSL inspection</th>
            <td>${yesNo(p.ssl_inspection)}${p.suricata_version !== null ? html`<span class="muted"> · Suricata ${p.suricata_version}</span>` : nothing}</td>
          </tr>
          <tr>
            <th>Never alerted on</th>
            <td>
              ${p.parsed.reputation || p.parsed.threshold
                ? p.exempt_networks.length || p.suppressed_networks.length
                  ? html`<span class="mono">${[...new Set([...p.exempt_networks, ...p.suppressed_networks])].join(", ")}</span>
                      <span class="muted"> (allowlisted in both directions for every signature)</span>`
                  : "none"
                : "unknown"}
            </td>
          </tr>
          <tr>
            <th>HOME_NET</th>
            <td>${p.parsed.homenet ? html`<span class="mono">${p.home_networks.join(", ")}</span>` : "unknown"}</td>
          </tr>
          <tr>
            <th>Inspected interfaces</th>
            <td>${p.parsed.interfaces ? html`<span class="mono">${p.interfaces.map((i) => i.interface).join(", ")}</span>` : "unknown"}</td>
          </tr>
        </tbody>
      </table>
    `;
  }

  // The controller's own record of what it blocked. No signature column: the
  // gateway does not persist one, and a column of dashes would imply it might.
  private _renderIpsBlockLog(b: IpsBlockLog) {
    if (!b.rows.length) {
      return html`<p class="muted" style="margin:6px 0;font-size:12px;">
        No threat or firewall-policy blocks in the controller's alert collection${
          b.unparsed ? ` (${b.unparsed} line(s) could not be read)` : ""
        }.
      </p>`;
    }
    const endpoint = (e: IpsBlockRow["source"]) =>
      e.name
        ? html`${e.name}<span class="muted"> ${e.address ?? e.mac ?? ""}</span>`
        : html`<span class="mono">${e.address ?? e.mac ?? "—"}</span>`;
    return html`
      <p class="muted" style="margin:6px 0;font-size:12px;">
        Last 24 h: ${b.threat_blocks_24h} threat block(s), ${b.firewall_blocks_24h} policy block(s),
        ${b.sources_24h.length} distinct source(s). Showing the newest ${b.rows.length}.
        ${b.unparsed ? `${b.unparsed} line(s) could not be read.` : ""}
      </p>
      <div class="table-wrap">
        <table style="margin:6px 0;">
          <thead>
            <tr>
              <th>When</th>
              <th>What</th>
              <th>Severity</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Policy</th>
            </tr>
          </thead>
          <tbody>
            ${b.rows.map(
              (r) => html`
                <tr>
                  <td class="mono">${r.time ? r.time.replace("T", " ").slice(0, 19) : "—"}</td>
                  <td>${r.kind === "threat" ? "Threat" : r.kind === "firewall" ? "Policy" : r.key}</td>
                  <td>${r.severity ? html`<span class="pill ${r.severity === "VERY_HIGH" || r.severity === "HIGH" ? "high" : "medium"}"><span class="dot"></span>${r.severity.toLowerCase().replace("_", " ")}</span>` : "—"}</td>
                  <td>${endpoint(r.source)}</td>
                  <td>${endpoint(r.destination)}</td>
                  <td>${r.policy ?? "—"}</td>
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
    `;
  }

  private _renderSshRun(run: SshRunResult) {
    return html`
      <p class="muted" style="font-size:12px;">
        ${run.host} as ${run.username} &middot; host key ${run.host_key_fingerprint}
        ${run.host_key_pinned_now ? " (pinned on this connection)" : ""}
      </p>
      ${run.results.map(
        (r) => html`
          <div style="margin-bottom:10px;">
            <div style="display:flex;gap:8px;align-items:center;">
              <span class="pill pill-${r.state}">${r.state}</span>
              <code>${r.argv}</code>
              ${r.exit_status !== null
                ? html`<span class="muted" style="font-size:11.5px;">exit ${r.exit_status}</span>`
                : nothing}
            </div>
            ${r.analysis ? this._renderAnalysis(r.analysis) : nothing}
            ${r.stdout ? html`<pre class="ssh-out">${r.stdout}</pre>` : nothing}
            ${r.stderr ? html`<pre class="ssh-out ssh-err">${r.stderr}</pre>` : nothing}
          </div>
        `
      )}
    `;
  }

  private _toggleSshCommand(id: string, on: boolean) {
    this._sshSelected = on
      ? [...this._sshSelected, id]
      : this._sshSelected.filter((c) => c !== id);
  }

  private async _sshKey(action: "generate" | "clear") {
    this._sshBusy = true;
    this._sshError = null;
    try {
      if (action === "generate") {
        await generateSshKey(this.hass);
      } else {
        await clearSshKey(this.hass);
      }
      this._ssh = await fetchSshStatus(this.hass);
    } catch (e) {
      this._sshError = (e as { message?: string }).message || String(e);
    } finally {
      this._sshBusy = false;
    }
  }

  private async _forgetHostKey(host: string) {
    try {
      await forgetSshHostKey(this.hass, host);
      this._ssh = await fetchSshStatus(this.hass);
    } catch (e) {
      this._sshError = (e as { message?: string }).message || String(e);
    }
  }

  private async _runSsh() {
    this._sshBusy = true;
    this._sshError = null;
    this._sshRun = null;
    try {
      this._sshRun = await runSshCommands(this.hass, this._sshHost.trim(), this._sshSelected);
      this._ssh = await fetchSshStatus(this.hass);
    } catch (e) {
      const err = e as { code?: string; message?: string };
      this._sshError = err.message || String(e);
    } finally {
      this._sshBusy = false;
    }
  }

  private _renderConfigLedger() {
    const state = this._ledger;
    if (!state) {
      return html`<div class="card"><h3>Configuration Baseline</h3><p class="muted">Loading…</p></div>`;
    }
    if (!state.available) {
      return html`
        <div class="card">
          <h3>Configuration Baseline</h3>
          <p class="muted">
            ${state.error ||
            "The controller configuration could not be read completely, so no comparison is made."}
            A partial read is not compared: rules that failed to load would look deleted.
          </p>
        </div>
      `;
    }

    const drift = state.drift;
    const changed = drift && drift.total > 0;

    return html`
      <div class="card">
        <h3>
          Configuration Baseline
          ${state.application_version
            ? html`<span class="muted" style="font-weight:400;font-size:12px;">
                &nbsp;UniFi Network ${state.application_version}</span>`
            : nothing}
        </h3>

        ${!state.baseline
          ? html`
              <p class="muted">
                No baseline accepted yet. Review the networks, zones, policies, and ACL rules
                below, then accept them; every later change is compared against that record.
              </p>
            `
          : html`
              <p class="muted">
                Baseline accepted ${new Date(state.baseline.accepted_at).toLocaleString()}.
                ${changed
                  ? html`<strong>${drift!.total}</strong> change${drift!.total === 1 ? "" : "s"} since.`
                  : "The controller matches it."}
              </p>
            `}

        ${changed ? this._renderDriftTable(drift!) : nothing}

        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:12px;">
          <button
            class="ha-btn"
            ?disabled=${!this._isOwner || this._ledgerBusy || !state.current}
            @click=${() => this._acceptBaseline()}
          >
            ${state.baseline ? "Accept current as new baseline" : "Accept current as baseline"}
          </button>
          ${!this._isOwner
            ? html`<span class="muted" style="font-size:12px;">Owner only.</span>`
            : nothing}
          ${this._ledgerError
            ? html`<span class="alert" style="font-size:12px;">${this._ledgerError}</span>`
            : nothing}
        </div>

        ${state.history.length
          ? html`
              <h4 style="margin:16px 0 6px;font-size:13px;">Recorded changes</h4>
              <table class="tbl">
                <thead>
                  <tr><th>Observed</th><th>Changes</th><th>Sections</th></tr>
                </thead>
                <tbody>
                  ${state.history.map(
                    (h) => html`
                      <tr>
                        <td>${new Date(h.at).toLocaleString()}</td>
                        <td>${h.total}</td>
                        <td class="muted">
                          ${Object.entries(h.sections)
                            .map(([name, n]) => `${LEDGER_SECTION_LABELS[name] || name} (${n})`)
                            .join(", ")}
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `
          : nothing}
      </div>
    `;
  }

  private _renderDriftTable(drift: LedgerDrift) {
    const rows = Object.entries(drift.sections).filter(([, s]) => s.count > 0);
    return html`
      <table class="tbl">
        <thead>
          <tr><th>Section</th><th>Added</th><th>Removed</th><th>Changed</th><th>Order</th></tr>
        </thead>
        <tbody>
          ${rows.map(
            ([name, s]) => html`
              <tr>
                <td>${LEDGER_SECTION_LABELS[name] || name}</td>
                <td>${s.added.length || ""}</td>
                <td>${s.removed.length || ""}</td>
                <td>${s.changed.length || ""}</td>
                <td>${s.ordering_changed ? "changed" : ""}</td>
              </tr>
            `
          )}
        </tbody>
      </table>
      ${rows.map(([name, s]) =>
        s.changed.length
          ? html`
              <div style="margin-top:10px;">
                <div class="muted" style="font-size:12px;font-weight:600;">
                  ${LEDGER_SECTION_LABELS[name] || name}
                </div>
                ${s.changed.map(
                  (row) => html`
                    <div style="font-size:12.5px;margin-top:4px;">
                      ${row.name || row.id}:
                      ${row.changes
                        .map((c) => `${c.field} ${JSON.stringify(c.from)} → ${JSON.stringify(c.to)}`)
                        .join("; ")}
                    </div>
                  `
                )}
              </div>
            `
          : nothing
      )}
    `;
  }

  private async _acceptBaseline() {
    const current = this._ledger?.current;
    if (!current) return;
    this._ledgerBusy = true;
    this._ledgerError = null;
    try {
      await acceptUnifiBaseline(this.hass, current.digest);
      this._ledger = await fetchUnifiLedger(this.hass);
    } catch (e) {
      const err = e as { code?: string; message?: string };
      this._ledgerError =
        err.code === "stale_snapshot"
          ? "The configuration changed while this page was open. Refresh, review the change, then accept."
          : err.message || String(e);
    } finally {
      this._ledgerBusy = false;
    }
  }

  private _renderFindings(findings: NetworkSecurityFinding[]) {
    const visible = findings.filter((f) => f.decision?.status !== "ignored");
    const ignored = findings.length - visible.length;
    return html`
      <div class="card">
        <h3>
          Suggestions
          ${ignored
            ? html`<span class="muted" style="font-weight:400;font-size:12px;"
                >— ${ignored} ignored (see Suggested changes under Firewall Policies)</span
              >`
            : nothing}
        </h3>
        ${visible.length
          ? html`${visible.map(
              (f) => html`
                <div class="finding">
                  <div class="sev ${f.severity}" title=${f.severity}></div>
                  <div>
                    <div class="finding-title">
                      ${f.title}${this._renderDecisionBadge(f)}
                    </div>
                    <div class="finding-detail">${f.detail}</div>
                  </div>
                </div>
              `
            )}`
          : html`<div class="empty">Nothing stood out — no advisory findings right now.</div>`}
      </div>
    `;
  }

  private _renderDecisionBadge(f: NetworkSecurityFinding) {
    const status = f.decision?.status;
    if (!status) return nothing;
    const label = status === "applied" ? "applied" : status === "planned" ? "planned" : "ignored";
    return html`<span class="badge-custom" style="margin-left:6px;">${label}</span>`;
  }

  private async _onSuggestionDecision(f: NetworkSecurityFinding, status: "planned" | "ignored" | null) {
    this._suggestionError = null;
    this._suggestionBusy = f.id;
    try {
      await setSuggestionDecision(this.hass, f.id, status);
      await this._load();
    } catch (e) {
      this._suggestionError = e instanceof Error ? e.message : String(e);
    } finally {
      this._suggestionBusy = null;
    }
  }

  private async _onSuggestionApply(f: NetworkSecurityFinding) {
    if (!f.remediation) return;
    const ok = window.confirm(
      `${f.remediation.label} on the UniFi controller now?\n\n` +
        `This is a real configuration change made with the write-scoped key. ` +
        `To undo: ${f.remediation.reversible}`
    );
    if (!ok) return;
    this._suggestionError = null;
    this._suggestionBusy = f.id;
    try {
      await applySuggestion(this.hass, f.id);
      await this._load();
    } catch (e) {
      this._suggestionError = e instanceof Error ? e.message : String(e);
    } finally {
      this._suggestionBusy = null;
    }
  }

  // The Suggested changes tab: every suggestion as a row the owner can plan, ignore, or (write-back on) apply.
  private _renderSuggestedChanges(findings: NetworkSecurityFinding[], writeEnabled: boolean) {
    if (!findings.length) {
      return html`<div class="empty">No suggested changes right now.</div>`;
    }
    return html`
      <p class="muted" style="font-size:12px;margin:0 0 8px;">
        Plan marks a change you intend to make by hand; Ignore hides it from the Suggestions card until
        you clear it. ${writeEnabled
          ? "Apply performs the named change on the controller with the write-scoped key and reads it back."
          : "Apply becomes available when suggestion write-back is enabled in Settings with a write-scoped key."}
      </p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Severity</th>
              <th>Suggestion</th>
              <th>Change</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${findings.map((f) => {
              const status = f.decision?.status ?? null;
              const busy = this._suggestionBusy === f.id;
              return html`
                <tr>
                  <td><span class="match ${f.severity === "high" ? "failing" : f.severity === "medium" ? "other" : "healthy"}">${f.severity}</span></td>
                  <td style="font-weight:600;">
                    ${f.title}<span class="sub">${f.detail}</span>
                  </td>
                  <td>
                    ${f.remediation
                      ? html`${f.remediation.label}<span class="sub">Undo: ${f.remediation.reversible}</span>`
                      : html`<span class="muted">manual — see the suggestion text</span>`}
                  </td>
                  <td>
                    ${status
                      ? html`${status}${f.decision?.at ? html`<span class="sub">${new Date(f.decision.at).toLocaleString()}</span>` : nothing}`
                      : html`<span class="muted">open</span>`}
                  </td>
                  <td style="white-space:nowrap;">
                    ${status === "applied"
                      ? nothing
                      : html`
                          ${status !== "planned"
                            ? html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._onSuggestionDecision(f, "planned")}>Plan</button>`
                            : nothing}
                          ${status !== "ignored"
                            ? html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._onSuggestionDecision(f, "ignored")}>Ignore</button>`
                            : nothing}
                          ${status
                            ? html`<button class="ha-btn" ?disabled=${busy} @click=${() => this._onSuggestionDecision(f, null)}>Clear</button>`
                            : nothing}
                          ${f.remediation && writeEnabled
                            ? html`<button class="ha-btn danger" ?disabled=${busy} @click=${() => this._onSuggestionApply(f)}>Apply</button>`
                            : nothing}
                        `}
                  </td>
                </tr>
              `;
            })}
          </tbody>
        </table>
      </div>
      ${this._suggestionError
        ? html`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:8px;">${this._suggestionError}</p>`
        : nothing}
    `;
  }


  // metadata.origin USER_DEFINED marks a rule the owner created; a null origin renders nothing, not "not custom".
  private _renderCustomBadge(custom: boolean | null) {
    return custom ? html`<span class="badge-custom">custom</span>` : nothing;
  }

  private _customCountLabel(rows: { custom: boolean | null }[]): string {
    const known = rows.filter((r) => r.custom != null);
    if (!known.length) return "";
    const customCount = known.filter((r) => r.custom).length;
    return ` · ${customCount} custom / ${rows.length} total`;
  }

  // Resolve a rule/policy's IP/subnet/MAC entries against the Network tab's client list.

  private _renderDeviceChips(entries: string[]) {
    const clients = this._overview?.clients ?? [];
    const all = matchClientsForEntries(entries, clients);
    const matches = all.slice(0, 6);
    if (!matches.length) return nothing;
    const overflow = all.length - matches.length;
    return html`
      <span class="sub" style="display:block;margin-top:3px;">
        ${matches.map(
          (m) => html`
            <button
              class="device-chip"
              title="Jump to ${m.name} on the Network tab"
              @click=${() => navigate(this, "network", m.matchedOn)}
            >
              📟 ${m.name}
            </button>
          `
        )}${overflow > 0 ? html`<span class="muted" style="font-size:10.5px;">+${overflow} more</span>` : nothing}
      </span>
    `;
  }

  private _policyActionClass(action: string | null): string {
    const a = (action ?? "").toLowerCase();
    if (a === "allow") return "healthy";
    if (a === "block" || a === "reject") return "failing";
    return "other";
  }

  private _renderFirewallPolicies(
    fw: FirewallPoliciesReport,
    findings: NetworkSecurityFinding[],
    writeEnabled: boolean
  ) {
    const rows = this._fwZonePairFilter
      ? fw.rules.filter(
          (r) =>
            r.source.zone === this._fwZonePairFilter!.src &&
            r.destination.zone === this._fwZonePairFilter!.dst
        )
      : fw.rules;
    return html`
      <div class="card">
        <h3>
          Firewall Policies — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— UniFi's default zone-based allow/deny view; order matters, evaluated top
            to bottom${this._customCountLabel(fw.rules)}</span
          >
        </h3>
        <div class="view-toggle">
          <button
            class=${this._fwViewMode === "table" ? "active" : ""}
            @click=${() => (this._fwViewMode = "table")}
          >
            Table
          </button>
          <button
            class=${this._fwViewMode === "suggestions" ? "active" : ""}
            @click=${() => (this._fwViewMode = "suggestions")}
          >
            Suggested changes${findings.length ? ` (${findings.length})` : ""}
          </button>
        </div>
        ${this._fwViewMode === "suggestions"
          ? this._renderSuggestedChanges(findings, writeEnabled)
          : !fw.available
            ? html`
                <div class="note" style="font-size:13px;">
                  Couldn't read Firewall Policies from this controller.${
                    fw.error ? html` ${fw.error}` : ""
                  }
                </div>
              `
            : !fw.rules.length
              ? html`<div class="empty">No Firewall Policies configured.</div>`
              : this._renderFirewallPolicyTable(rows)}
      </div>
    `;
  }

  // The Zone Matrix as its own section; a cell click filters the policy table in the Firewall Policies section.
  private _renderZoneMatrixCard(fw: FirewallPoliciesReport) {
    return html`
      <div class="card">
        <h3>
          Zone Matrix
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— dominant policy per source and destination zone; click a cell to filter the policy table</span
          >
        </h3>
        ${!fw.available
          ? html`<div class="note" style="font-size:13px;">Couldn't read Firewall Policies from this controller.</div>`
          : !fw.zones.length
            ? html`<div class="empty">No zones reported by this controller.</div>`
            : this._renderZoneMatrix(fw)}
      </div>
    `;
  }

  private _renderFirewallPolicyTable(rows: FirewallPolicy[]) {
    return html`
      ${this._fwZonePairFilter
        ? html`
            <div class="zone-pair-filter">
              <span class="chip"
                >${this._fwZonePairFilter.src} → ${this._fwZonePairFilter.dst}</span
              >
              <button
                style="cursor:pointer;border:none;background:none;color:var(--primary-color);font-size:12px;"
                @click=${() => (this._fwZonePairFilter = null)}
              >
                Clear filter
              </button>
            </div>
          `
        : nothing}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              ${sortableTh("#", "order", this._firewallPolicySort, (n) => (this._firewallPolicySort = n), {
                numeric: true,
              })}
              ${sortableTh("Name", "name", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Action", "action", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Source zone", "source_zone", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Dest. zone", "dest_zone", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Protocol", "protocol", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Ports", "ports", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
              ${sortableTh("Enabled", "enabled", this._firewallPolicySort, (n) => (this._firewallPolicySort = n))}
            </tr>
          </thead>
          <tbody>
            ${rows.length
              ? sortRows(rows.slice(), this._firewallPolicySort, {
                  order: (r) => r.order,
                  name: (r) => r.name,
                  action: (r) => r.action,
                  source_zone: (r) => r.source.zone,
                  dest_zone: (r) => r.destination.zone,
                  protocol: (r) => r.protocol,
                  ports: (r) => r.ports.length,
                  enabled: (r) => r.enabled,
                }).map((r: FirewallPolicy, i) => this._renderFirewallPolicyRow(r, i))
              : html`<tr><td colspan="8"><div class="empty">No policies for this zone pair.</div></td></tr>`}
          </tbody>
        </table>
      </div>
      <div class="note">
        Every policy is scoped to a source/destination zone pair; the detail line under
        each name shows any additional network/IP/MAC/domain narrowing the controller
        reported, and a resolved device chip when it matches a known client.
      </div>
    `;
  }

  private _renderZoneMatrix(fw: FirewallPoliciesReport) {
    if (!fw.zones.length) {
      return html`<div class="empty">No firewall zones reported by this controller.</div>`;
    }
    const matrix = buildZoneMatrix(fw.zones, fw.rules);
    const zoneNames = fw.zones.map((z) => z.name);
    return html`
      <div class="matrix-wrap">
        <table class="zone-matrix">
          <thead>
            <tr>
              <th class="corner"></th>
              ${zoneNames.map((n) => html`<th>${n}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${matrix.map(
              (row, ri) => html`
                <tr>
                  <th>${zoneNames[ri]}</th>
                  ${row.map(
                    (cell) => html`
                      <td
                        class="cell ${cell.dominant}"
                        title="${cell.policies.length} polic${cell.policies.length === 1 ? "y" : "ies"}"
                        @click=${() => this._selectZonePair(cell.srcZone, cell.dstZone)}
                      >
                        ${cell.dominant === "none"
                          ? "—"
                          : cell.dominant === "mixed"
                            ? "mixed"
                            : cell.dominant === "allow"
                              ? "allow"
                              : "block"}${cell.policies.length ? html`<br /><span style="font-size:10px;">${cell.policies.length}</span>` : nothing}
                      </td>
                    `
                  )}
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
      <div class="note">
        Rows are the source zone, columns the destination zone. Click a cell to see its
        policies. "mixed" means both allow and block/reject policies exist for that pair
        — which one actually governs a given connection depends on evaluation order and
        UniFi's own implicit-deny fallback, neither of which this project models; open
        the filtered table to read the real order.
      </div>
    `;
  }

  private _selectZonePair(src: string, dst: string) {
    this._fwZonePairFilter = { src, dst };
    this._fwViewMode = "table";
  }

  private _renderFirewallPolicyRow(r: FirewallPolicy, i: number) {
    const detailFor = (side: FirewallPolicy["source"]) => {
      const bits: string[] = [];
      if (side.networks.length) bits.push(`networks: ${side.networks.join(", ")}`);
      if (side.ip_or_subnets.length) bits.push(`IP: ${side.ip_or_subnets.join(", ")}`);
      if (side.macs.length) bits.push(`MAC: ${side.macs.join(", ")}`);
      if (side.domains.length) bits.push(`domains: ${side.domains.join(", ")}`);
      if (side.applications.length) bits.push(`${side.applications.length} app(s)`);
      if (side.application_categories.length) bits.push(`${side.application_categories.length} app categor${side.application_categories.length === 1 ? "y" : "ies"}`);
      if (!bits.length && side.filter_type) bits.push(side.filter_type.toLowerCase().replace(/_/g, " "));
      return bits.join(" · ");
    };
    const srcDetail = detailFor(r.source);
    const dstDetail = detailFor(r.destination);
    const detail = [srcDetail && `from ${srcDetail}`, dstDetail && `to ${dstDetail}`].filter(Boolean).join(" · ");
    const deviceEntries = [
      ...r.source.ip_or_subnets,
      ...r.source.macs,
      ...r.destination.ip_or_subnets,
      ...r.destination.macs,
    ];
    return html`
      <tr>
        <td class="num">${r.order ?? i + 1}</td>
        <td style="font-weight:600;">
          ${r.name ?? "—"}${this._renderCustomBadge(r.custom)}${
            detail ? html`<span class="sub">${detail}</span>` : nothing
          }${this._renderDeviceChips(deviceEntries)}
        </td>
        <td>
          ${r.action
            ? html`<span class="match ${this._policyActionClass(r.action)}">${r.action}</span>`
            : html`<span class="muted">—</span>`}${
              r.allow_return_traffic
                ? html`<span class="sub">+ mirrored return-traffic policy</span>`
                : nothing
            }
        </td>
        <td>${r.source.zone ?? html`<span class="muted">—</span>`}</td>
        <td>${r.destination.zone ?? html`<span class="muted">—</span>`}</td>
        <td>${r.protocol ?? html`<span class="muted">any</span>`}</td>
        <td>
          ${r.ports.length
            ? html`<span class="mono">${r.ports.join(", ")}</span>`
            : r.source.ports_from_list || r.destination.ports_from_list
              ? html`<span class="muted">traffic matching list</span>`
              : html`<span class="muted">any</span>`}
        </td>
        <td>
          ${r.enabled == null
            ? html`<span class="muted">—</span>`
            : r.enabled
              ? "yes"
              : html`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `;
  }


  private _aclActionClass(action: string | null): string {
    const a = (action ?? "").toLowerCase();
    if (["allow", "accept", "permit"].some((x) => a.includes(x))) return "healthy";
    if (["deny", "drop", "block", "reject"].some((x) => a.includes(x))) return "failing";
    return "other";
  }

  private _renderAcl(acl: AclReport) {
    return html`
      <div class="card" id="acl-card">
        <h3>
          ACL Rules — Security Audit
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— order matters; rules are evaluated top to bottom${
              acl.endpoint ? ` · source: ${acl.endpoint}` : ""
            }${this._customCountLabel(acl.rules)}</span
          >
        </h3>
        ${!acl.available
          ? html`
              <div class="note" style="font-size:13px;">
                This controller's Integration API didn't return ACL rules. Endpoints tried:
                <code>${acl.endpoints_tried.join(", ") || "—"}</code>.${
                  acl.error ? html` Last response: ${acl.error}.` : ""
                }
              </div>
            `
          : !acl.rules.length
            ? html`<div class="empty">No ACL rules configured (endpoint: ${acl.endpoint}).</div>`
            : html`
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        ${sortableTh("#", "order", this._aclSort, (n) => (this._aclSort = n), { numeric: true })}
                        ${sortableTh("Name", "name", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Action", "action", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Protocols", "protocols", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Networks", "networks", this._aclSort, (n) => (this._aclSort = n))}
                        ${sortableTh("Ports", "ports", this._aclSort, (n) => (this._aclSort = n), { numeric: true })}
                        ${sortableTh("Enabled", "enabled", this._aclSort, (n) => (this._aclSort = n))}
                      </tr>
                    </thead>
                    <tbody>
                      ${sortRows(acl.rules.slice(), this._aclSort, {
                        order: (r) => r.order,
                        name: (r) => r.name,
                        action: (r) => r.action,
                        protocols: (r) => r.protocols.join(", ") || null,
                        networks: (r) => r.networks.join(", ") || null,
                        ports: (r) => r.ports.length,
                        enabled: (r) => r.enabled,
                      }).map((r: AclRule, i) => this._renderAclRow(r, i))}
                    </tbody>
                  </table>
                </div>
                <div class="note">
                  Order reflects evaluation precedence as returned by the controller. Source
                  and destination detail (IP/subnet, MAC, port scoping) is shown under each
                  rule's name when the controller reported it.
                </div>
              `}
      </div>
    `;
  }

  private _renderAclRow(r: AclRule, i: number) {
    const srcBits: string[] = [];
    if (r.source.ip_or_subnets.length) srcBits.push(`from ${r.source.ip_or_subnets.join(", ")}`);
    if (r.source.macs.length) srcBits.push(`MAC ${r.source.macs.join(", ")}`);
    const dstBits: string[] = [];
    if (r.destination.ip_or_subnets.length) dstBits.push(`to ${r.destination.ip_or_subnets.join(", ")}`);
    if (r.destination.macs.length) dstBits.push(`MAC ${r.destination.macs.join(", ")}`);
    const detail = [...srcBits, ...dstBits].join(" · ");
    const deviceEntries = [
      ...r.source.ip_or_subnets,
      ...r.source.macs,
      ...r.destination.ip_or_subnets,
      ...r.destination.macs,
    ];
    return html`
      <tr>
        <td class="num">${r.order ?? i + 1}</td>
        <td style="font-weight:600;">
          ${r.name ?? "—"}${this._renderCustomBadge(r.custom)}${
            detail ? html`<span class="sub">${detail}</span>` : nothing
          }${this._renderDeviceChips(deviceEntries)}
        </td>
        <td>
          ${r.action
            ? html`<span class="match ${this._aclActionClass(r.action)}">${r.action}</span>`
            : html`<span class="muted">—</span>`}
        </td>
        <td>${r.protocols.length ? r.protocols.join(", ") : html`<span class="muted">any</span>`}</td>
        <td>
          ${r.networks.length
            ? html`<span class="chips">${r.networks.map((n) => html`<span class="chip">${n}</span>`)}</span>`
            : html`<span class="muted">any / —</span>`}
        </td>
        <td>
          ${r.ports.length
            ? html`<span class="mono">${r.ports.join(", ")}</span>`
            : html`<span class="muted">any</span>`}
        </td>
        <td>
          ${r.enabled == null
            ? html`<span class="muted">—</span>`
            : r.enabled
              ? "yes"
              : html`<span class="muted">disabled</span>`}
        </td>
      </tr>
    `;
  }


  private _portStatusClass(status: string): string {
    if (status === "covered") return "healthy";
    if (status === "uncovered") return "failing";
    return "other";
  }

  private _renderServerPorts(sp: ServerPortsReport) {
    return html`
      <div class="card">
        <h3>
          Home Assistant Server Ports
          <span class="muted" style="font-weight:400;font-size:12px;"
            >— cross-referenced against the ACL rules above</span
          >
        </h3>
        ${!sp.available
          ? html`
              <div class="empty">
                No listening-port report from the HA SOC Probe add-on yet, or none of its
                reported bind addresses are real LAN addresses. Install/enable the Probe
                add-on to populate this.
              </div>
            `
          : html`
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr>
                      ${sortableTh("Port", "port", this._portSort, (n) => (this._portSort = n), {
                        numeric: true,
                      })}
                      ${sortableTh("Proto", "proto", this._portSort, (n) => (this._portSort = n))}
                      ${sortableTh("Address", "address", this._portSort, (n) => (this._portSort = n))}
                      ${sortableTh("Process", "process", this._portSort, (n) => (this._portSort = n))}
                      ${sortableTh("Coverage", "status", this._portSort, (n) => (this._portSort = n))}
                    </tr>
                  </thead>
                  <tbody>
                    ${sortRows(sp.ports.slice(), this._portSort, {
                      port: (p) => p.port,
                      proto: (p) => p.proto,
                      address: (p) => p.address,
                      process: (p) => p.process,
                      status: (p) => p.status,
                    }).map(
                      (p) => html`
                        <tr>
                          <td class="num">${p.port}</td>
                          <td>${p.proto ?? "—"}</td>
                          <td class="mono">${p.address ?? "—"}</td>
                          <td>${p.process ?? "—"}</td>
                          <td>
                            <span class="match ${this._portStatusClass(p.status)}">
                              ${p.status === "covered"
                                ? `covered by ${p.covered_by.join(", ")}`
                                : p.status === "network_scoped"
                                  ? `network-scoped: ${p.network_scoped_by.join(", ")}`
                                  : "uncovered"}
                            </span>
                          </td>
                        </tr>
                      `
                    )}
                  </tbody>
                </table>
              </div>
              <div class="note">
                "Uncovered" means no enabled ACL rule names this server's IP/subnet as a
                destination for that port — it does not by itself mean the port is reachable
                from every network; UniFi's own default zone policy still applies.
                "Network-scoped" means a rule covers it by network/zone rather than by IP,
                which this project can't independently verify covers this server.
              </div>
            `}
      </div>
    `;
  }


  private _renderPihole(p: PiHoleOverview) {
    if (!p.configured) {
      return html`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="empty">
            Not connected. Add a Pi-hole host and app password in Settings to see blocking
            status, IoT client group scoping, and recently blocked domains here.
          </div>
        </div>
      `;
    }
    if (!p.reachable) {
      return html`
        <div class="card">
          <h3>Pi-hole DNS</h3>
          <div class="alert">${p.error ?? "Pi-hole is not reachable."}</div>
        </div>
      `;
    }
    return html`
      <div class="card">
        <h3>Pi-hole DNS</h3>
        <div class="stat-row">
          <div class="stat-tile">
            <span class="label">Blocking</span>
            <span class="value">${p.blocking_enabled ? "On" : "Off"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Queries (24h window)</span>
            <span class="value">${p.summary?.total ?? "—"}</span>
          </div>
          <div class="stat-tile">
            <span class="label">Blocked</span>
            <span class="value"
              >${p.summary?.blocked ?? "—"}${
                p.summary?.percent_blocked != null ? ` (${p.summary.percent_blocked.toFixed(1)}%)` : ""
              }</span
            >
          </div>
          <div class="stat-tile">
            <span class="label">IoT subnet scoped</span>
            <span class="value">
              ${p.iot_cidr == null
                ? html`<span class="muted" style="font-size:16px;">not set</span>`
                : p.iot_clients_scoped
                  ? "Yes"
                  : html`<span style="color:var(--status-warning, #fab219);">No</span>`}
            </span>
          </div>
        </div>
        ${p.top_blocked_domains.length || p.recent_blocked.length
          ? html`
              <div class="stat-row" style="margin-top:12px;">
                ${p.top_blocked_domains.length
                  ? html`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Top blocked domains</span>
                        <div class="domain-list">
                          ${p.top_blocked_domains.map(
                            (d) => html`<div class="row"><span>${d.domain}</span><span>${d.count}</span></div>`
                          )}
                        </div>
                      </div>
                    `
                  : nothing}
                ${p.recent_blocked.length
                  ? html`
                      <div class="stat-tile" style="grid-column: span 2;">
                        <span class="label">Recently blocked</span>
                        <div class="domain-list">
                          ${p.recent_blocked.map((d) => html`<div class="row"><span>${d}</span></div>`)}
                        </div>
                      </div>
                    `
                  : nothing}
              </div>
            `
          : nothing}
      </div>
    `;
  }
}
