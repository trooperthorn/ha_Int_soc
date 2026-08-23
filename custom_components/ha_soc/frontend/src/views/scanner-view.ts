import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  Finding,
  ProbeOverview,
  FirewallRule,
  FirewallRuleAction,
  FirewallRuleProto,
  FirewallStatus,
  FirewallPendingTest,
  fetchScannerFindings,
  scanIntegrationNow,
  fetchVulns,
  scanVulnsNow,
  setVulnStatus,
  setMisconfigStatus,
  fetchHealth,
  fetchProbeStatus,
  fetchFirewallStatus,
  proposeFirewallTest,
  confirmFirewallTest,
  cancelFirewallTest,
} from "../data/ha-soc-ws";

const STATUS_OPTIONS = ["new", "confirmed", "dismissed", "resolved"];
const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

function severityRank(severity: string): number {
  const i = SEVERITY_ORDER.indexOf(severity);
  return i === -1 ? SEVERITY_ORDER.length : i;
}

@customElement("ha-soc-scanner-view")
export class HaSocScannerView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _scannerFindings: Finding[] = [];
  @state() private _vulnFindings: Finding[] = [];
  @state() private _misconfigFindings: Finding[] = [];
  @state() private _probe: ProbeOverview | null = null;
  @state() private _loading = true;
  @state() private _scanning = false;

  @state() private _firewall: FirewallStatus | null = null;
  @state() private _fwDraftRules: FirewallRule[] = [{ action: "allow", proto: "tcp", port: 0, source: "" }];
  @state() private _fwBackupAck = false;
  @state() private _fwSubmitting = false;
  @state() private _fwError: string | null = null;
  private _fwPollHandle: number | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._fwPollHandle !== null) {
      window.clearInterval(this._fwPollHandle);
      this._fwPollHandle = null;
    }
  }

  private async _load() {
    this._loading = true;
    try {
      const [scanner, vulns, health, probe, firewall] = await Promise.all([
        fetchScannerFindings(this.hass),
        fetchVulns(this.hass),
        fetchHealth(this.hass),
        fetchProbeStatus(this.hass),
        fetchFirewallStatus(this.hass),
      ]);
      this._scannerFindings = scanner;
      this._vulnFindings = vulns;
      this._misconfigFindings = health.misconfig_findings;
      this._probe = probe;
      this._firewall = firewall;
      this._maybeManageFirewallPolling();
    } finally {
      this._loading = false;
    }
  }

  // Polls ha_soc/firewall/status every 2s for as long as any test is
  // in flight — from "queued" through the add-on actually resolving it —
  // so the countdown and the eventual confirmed/reverted outcome show up
  // without the user having to reload the page. Stops itself the instant
  // there's nothing pending, rather than running unconditionally.
  private _maybeManageFirewallPolling() {
    const isLive = this._firewall?.pending != null;
    if (isLive && this._fwPollHandle === null) {
      this._fwPollHandle = window.setInterval(() => this._pollFirewallStatus(), 2000);
    } else if (!isLive && this._fwPollHandle !== null) {
      window.clearInterval(this._fwPollHandle);
      this._fwPollHandle = null;
    }
  }

  private async _pollFirewallStatus() {
    this._applyFirewallStatus(await fetchFirewallStatus(this.hass));
  }

  // A test that just resolved (pending -> null) means whatever the user
  // acknowledged applied to THAT proposal — require a fresh acknowledgment
  // for the next one rather than leaving the checkbox silently checked.
  private _applyFirewallStatus(status: FirewallStatus) {
    const hadPending = this._firewall?.pending != null;
    this._firewall = status;
    if (hadPending && !status.pending) {
      this._fwBackupAck = false;
    }
    this._maybeManageFirewallPolling();
  }

  private _fwRuleValid(r: FirewallRule): boolean {
    return (
      Number.isInteger(r.port) &&
      r.port >= 1 &&
      r.port <= 65535 &&
      (r.action === "allow" || r.action === "deny") &&
      (r.proto === "tcp" || r.proto === "udp")
    );
  }

  private _fwUpdateRule(index: number, changes: Partial<FirewallRule>) {
    this._fwDraftRules = this._fwDraftRules.map((r, i) => (i === index ? { ...r, ...changes } : r));
  }

  private _fwAddRule() {
    this._fwDraftRules = [...this._fwDraftRules, { action: "allow", proto: "tcp", port: 0, source: "" }];
  }

  private _fwRemoveRule(index: number) {
    this._fwDraftRules = this._fwDraftRules.filter((_, i) => i !== index);
  }

  private async _onProposeTest() {
    this._fwError = null;
    this._fwSubmitting = true;
    try {
      const rules = this._fwDraftRules.map((r) => ({
        action: r.action,
        proto: r.proto,
        port: r.port,
        source: r.source ? r.source : null,
      }));
      await proposeFirewallTest(this.hass, rules, this._fwBackupAck);
      this._applyFirewallStatus(await fetchFirewallStatus(this.hass));
    } catch (err: any) {
      this._fwError = err?.message ?? "Failed to propose the firewall change.";
    } finally {
      this._fwSubmitting = false;
    }
  }

  private async _onConfirmTest() {
    if (!this._firewall?.pending) return;
    this._fwError = null;
    this._fwSubmitting = true;
    try {
      await confirmFirewallTest(this.hass, this._firewall.pending.test_id);
      this._applyFirewallStatus(await fetchFirewallStatus(this.hass));
    } catch (err: any) {
      this._fwError = err?.message ?? "Failed to confirm the firewall change.";
    } finally {
      this._fwSubmitting = false;
    }
  }

  private async _onCancelTest() {
    if (!this._firewall?.pending) return;
    this._fwError = null;
    this._fwSubmitting = true;
    try {
      await cancelFirewallTest(this.hass, this._firewall.pending.test_id);
      this._applyFirewallStatus(await fetchFirewallStatus(this.hass));
    } catch (err: any) {
      this._fwError = err?.message ?? "Failed to cancel the firewall change.";
    } finally {
      this._fwSubmitting = false;
    }
  }

  private async _onScanIntegrations() {
    this._scanning = true;
    try {
      await scanIntegrationNow(this.hass);
      await this._load();
    } finally {
      this._scanning = false;
    }
  }

  private async _onScanVulns() {
    this._scanning = true;
    try {
      await scanVulnsNow(this.hass);
      await this._load();
    } finally {
      this._scanning = false;
    }
  }

  private async _onVulnStatus(id: string, status: string) {
    await setVulnStatus(this.hass, id, status);
    await this._load();
  }

  private async _onMisconfigStatus(id: string, status: string) {
    await setMisconfigStatus(this.hass, id, status);
    await this._load();
  }

  // One header row per device instead of repeating the device name on
  // every CVE row — devices ordered by their own worst finding first,
  // findings within a device also worst-first, so both the grouping and
  // the reading order lead with what needs attention most.
  private _groupedVulnFindings(): { device_name: string; findings: Finding[] }[] {
    const byDevice = new Map<string, Finding[]>();
    for (const f of this._vulnFindings) {
      const name = String(f.device_name ?? "Unknown device");
      const list = byDevice.get(name);
      if (list) list.push(f);
      else byDevice.set(name, [f]);
    }
    const groups = Array.from(byDevice.entries()).map(([device_name, findings]) => ({
      device_name,
      findings: [...findings].sort((a, b) => severityRank(a.severity) - severityRank(b.severity)),
    }));
    groups.sort((a, b) => severityRank(a.findings[0].severity) - severityRank(b.findings[0].severity));
    return groups;
  }

  private _renderStatusSelect(id: string, current: string, onChange: (s: string) => void) {
    return html`
      <select @change=${(e: Event) => onChange((e.target as HTMLSelectElement).value)}>
        ${STATUS_OPTIONS.map((s) => html`<option value=${s} ?selected=${s === current}>${s}</option>`)}
      </select>
    `;
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading findings…</div>`;

    return html`
      <div class="card">
        <h3>Misconfiguration Findings</h3>
        ${!this._misconfigFindings.length
          ? html`<div class="empty">No findings.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Check</th>
                    <th>Summary</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._misconfigFindings.map(
                    (f: any) => html`
                      <tr>
                        <td><span class="pill ${f.severity}"><span class="dot"></span>${f.check}</span></td>
                        <td>${f.summary}</td>
                        <td>${this._renderStatusSelect(f.id, f.status, (s) => this._onMisconfigStatus(f.id, s))}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static AST/regex analysis of every installed integration's source — core and
          custom. Every finding is advisory and needs a human to confirm; Home
          Assistant's own quality tooling (hassfest) never checks for these patterns and
          never runs against custom_components at all.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanIntegrations}>
            Scan all integrations now
          </button>
        </div>
        ${!this._scannerFindings.length
          ? html`<div class="empty">No findings.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>Pattern</th>
                    <th>Location</th>
                    <th>Confidence</th>
                    <th>CWE</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._scannerFindings.map(
                    (f: any) => html`
                      <tr>
                        <td>${f.domain}</td>
                        <td><span class="pill ${f.severity}"><span class="dot"></span>${f.pattern}</span></td>
                        <td>${f.file}:${f.line}</td>
                        <td>${f.confidence}</td>
                        <td>${f.cwe}</td>
                        <td>${this._renderStatusSelect(f.id, f.status, (s) => this._onVulnStatus(f.id, s))}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      <div class="card">
        <h3>Device Vulnerabilities</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Matches monitored devices against NVD by manufacturer/model — a heuristic
          match, never a confirmed exploit. Absence of a match is not evidence a device
          is secure.
        </p>
        <div class="toolbar">
          <button class="ha-btn" ?disabled=${this._scanning} @click=${this._onScanVulns}>
            Scan devices now
          </button>
        </div>
        ${!this._vulnFindings.length
          ? html`<div class="empty">No findings.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>CVE</th>
                    <th>CVSS</th>
                    <th>Confidence</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._groupedVulnFindings().map(
                    (group) => html`
                      <tr>
                        <td colspan="4" style="font-weight:600;background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                          ${group.device_name}
                          <span class="muted" style="font-weight:400;font-size:11.5px;"
                            >(${group.findings.length} finding${group.findings.length === 1 ? "" : "s"})</span
                          >
                        </td>
                      </tr>
                      ${group.findings.map(
                        (f: any) => html`
                          <tr>
                            <td>${f.cve_id ?? "—"}</td>
                            <td><span class="pill ${f.severity}"><span class="dot"></span>${f.cvss ?? "unscored"}</span></td>
                            <td>${f.confidence}</td>
                            <td>${this._renderStatusSelect(f.id, f.status, (s) => this._onVulnStatus(f.id, s))}</td>
                          </tr>
                        `
                      )}
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

      ${this._renderProbeCard()}
      ${this._renderFirewallCard()}
    `;
  }

  private _renderProbeCard() {
    const probe = this._probe;
    if (!probe) return nothing;

    if (!probe.supervisor) {
      return html`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not available</span></h3>
          <p class="muted" style="font-size:12.5px;">
            Real socket-level port scanning of the host needs a companion add-on with
            host-network access — something a Python integration structurally cannot do
            on its own, even on Home Assistant OS. This install isn't running under
            Supervisor (Core/Container), so this feature has nothing to attach to here.
          </p>
        </div>
      `;
    }

    if (!probe.installed) {
      return html`
        <div class="card">
          <h3>Host Probe <span class="tag cosmetic">not installed</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The optional <strong>HA SOC Probe</strong> add-on isn't installed. It's the
            only way to see the host's actual listening ports — this integration alone
            can't reach past its own container. Add its repository under
            Settings → Add-ons → Add-on Store → ⋮ → Repositories, then install
            "HA SOC Probe". See the README for the exact URL.
          </p>
        </div>
      `;
    }

    const result = probe.result;
    return html`
      <div class="card">
        <h3>
          Host Probe
          <span class="tag ${probe.running ? "enforced" : "cosmetic"}">
            ${probe.running ? "running" : "installed, not running"}
          </span>
          ${probe.update_available ? html`<span class="tag cosmetic">update available</span>` : nothing}
        </h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Version ${probe.version ?? "unknown"}. Reports the host's real listening TCP
          ports — process-name attribution isn't included: identifying which process
          owns a port needs the add-on to also see the host's process list
          (<code>host_pid</code>), a privilege this add-on deliberately doesn't request.
        </p>
        ${!result
          ? html`<div class="empty">No scan reported yet.</div>`
          : html`
              <p class="muted" style="font-size:12px;">
                Last reported ${new Date(result.reported_at).toLocaleString()}
              </p>
              ${!result.open_ports.length
                ? html`<div class="empty">No listening ports reported.</div>`
                : html`
                    <table>
                      <thead>
                        <tr>
                          <th>Port</th>
                          <th>Protocol</th>
                          <th>Bind address</th>
                          <th>Interface</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${result.open_ports
                          .slice()
                          .sort((a, b) => a.port - b.port)
                          .map(
                            (p) => html`
                              <tr>
                                <td>${p.port}</td>
                                <td>${p.proto}</td>
                                <td class="muted">${p.address ?? "—"}</td>
                                <td>
                                  ${p.interface === "(all interfaces)"
                                    ? html`<span class="pill high"
                                        ><span class="dot"></span>all interfaces</span
                                      >`
                                    : html`<span class="muted">${p.interface ?? "—"}</span>`}
                                </td>
                              </tr>
                            `
                          )}
                      </tbody>
                    </table>
                  `}
            `}
      </div>
    `;
  }

  private _renderFirewallCard() {
    const probe = this._probe;
    const fw = this._firewall;
    // Same prerequisite as Host Probe: without the add-on actually
    // running, there is nothing that could apply these rules — the Host
    // Probe card above already explains why in that case.
    if (!probe?.supervisor || !probe?.installed || !fw) return nothing;

    return html`
      <div class="card">
        <h3>Firewall Rules</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Reads, and — if you propose a change — writes the host's firewall via the HA
          SOC Probe add-on's <code>NET_ADMIN</code> capability. Every proposed change is
          backed up first and applied to a dedicated chain this project owns outright,
          never the host's raw INPUT chain. An unconfirmed change reverts itself
          automatically once its test window closes.
        </p>

        <h4 class="fw-subhead">Active rules</h4>
        ${!fw.known_rules || !fw.known_rules.length
          ? html`<div class="empty">
              No rules reported yet${fw.known_rules === null ? " — waiting for the add-on's first report." : "."}
            </div>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Protocol</th>
                    <th>Port</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  ${fw.known_rules.map(
                    (r) => html`
                      <tr>
                        <td>
                          <span class="pill ${r.action === "allow" ? "good" : "critical"}"
                            ><span class="dot"></span>${r.action}</span
                          >
                        </td>
                        <td>${r.proto}</td>
                        <td>${r.port}</td>
                        <td class="muted">${r.source ?? "any"}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
        ${fw.known_rules_reported_at
          ? html`<p class="muted" style="font-size:11.5px;margin:6px 0 0;">
              Last reported ${new Date(fw.known_rules_reported_at).toLocaleString()}
            </p>`
          : nothing}
        ${fw.pending ? this._renderFirewallPending(fw.pending) : this._renderFirewallBuilder()}
        ${this._fwError
          ? html`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">${this._fwError}</p>`
          : nothing}
      </div>
    `;
  }

  private _renderFirewallPending(pending: FirewallPendingTest) {
    const remaining = Math.max(0, Math.round((new Date(pending.expires_at).getTime() - Date.now()) / 1000));
    const statusLabel: Record<string, string> = {
      testing: pending.applied_at ? "Testing — live on the host" : "Queued — waiting for the add-on to apply",
      confirmed: "Confirmed — waiting for the add-on to acknowledge",
      reverted: "Reverting — waiting for the add-on to acknowledge",
      expired: "Window expired — reverting automatically",
    };

    return html`
      <h4 class="fw-subhead">Proposed rules — ${statusLabel[pending.status] ?? pending.status}</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Protocol</th>
            <th>Port</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          ${pending.proposed_rules.map(
            (r) => html`
              <tr>
                <td>
                  <span class="pill ${r.action === "allow" ? "good" : "critical"}"
                    ><span class="dot"></span>${r.action}</span
                  >
                </td>
                <td>${r.proto}</td>
                <td>${r.port}</td>
                <td class="muted">${r.source ?? "any"}</td>
              </tr>
            `
          )}
        </tbody>
      </table>
      <div class="toolbar" style="margin-top:12px;">
        <button
          class="ha-btn"
          ?disabled=${this._fwSubmitting || pending.status !== "testing"}
          @click=${this._onConfirmTest}
        >
          Apply${pending.status === "testing" ? html` (${remaining}s to auto-revert)` : nothing}
        </button>
        <button
          class="ha-btn danger"
          ?disabled=${this._fwSubmitting || pending.status !== "testing"}
          @click=${this._onCancelTest}
        >
          Cancel now
        </button>
      </div>
    `;
  }

  private _renderFirewallBuilder() {
    const canSubmit =
      this._fwBackupAck && this._fwDraftRules.length > 0 && this._fwDraftRules.every((r) => this._fwRuleValid(r));

    return html`
      <h4 class="fw-subhead">Propose a change</h4>
      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>Protocol</th>
            <th>Port</th>
            <th>Source (optional)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._fwDraftRules.map(
            (r, i) => html`
              <tr>
                <td>
                  <select
                    @change=${(e: Event) =>
                      this._fwUpdateRule(i, { action: (e.target as HTMLSelectElement).value as FirewallRuleAction })}
                  >
                    <option value="allow" ?selected=${r.action === "allow"}>allow</option>
                    <option value="deny" ?selected=${r.action === "deny"}>deny</option>
                  </select>
                </td>
                <td>
                  <select
                    @change=${(e: Event) =>
                      this._fwUpdateRule(i, { proto: (e.target as HTMLSelectElement).value as FirewallRuleProto })}
                  >
                    <option value="tcp" ?selected=${r.proto === "tcp"}>tcp</option>
                    <option value="udp" ?selected=${r.proto === "udp"}>udp</option>
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    min="1"
                    max="65535"
                    .value=${r.port ? String(r.port) : ""}
                    style="width:90px;"
                    @input=${(e: Event) =>
                      this._fwUpdateRule(i, { port: parseInt((e.target as HTMLInputElement).value, 10) || 0 })}
                  />
                </td>
                <td>
                  <input
                    type="text"
                    placeholder="e.g. 192.168.10.0/24"
                    .value=${r.source ?? ""}
                    style="width:170px;"
                    @input=${(e: Event) => this._fwUpdateRule(i, { source: (e.target as HTMLInputElement).value })}
                  />
                </td>
                <td><button class="ha-btn danger" @click=${() => this._fwRemoveRule(i)}>Remove</button></td>
              </tr>
            `
          )}
        </tbody>
      </table>
      <div class="toolbar" style="margin-top:8px;">
        <button class="ha-btn" @click=${this._fwAddRule}>+ Add rule</button>
      </div>

      <label style="display:flex;align-items:flex-start;gap:8px;font-size:12.5px;margin-top:12px;cursor:pointer;">
        <input
          type="checkbox"
          style="margin-top:2px;"
          .checked=${this._fwBackupAck}
          @change=${(e: Event) => (this._fwBackupAck = (e.target as HTMLInputElement).checked)}
        />
        <span>
          I understand the current ruleset will be backed up before this change is
          applied, and that an unconfirmed change reverts to that backup automatically
          once the test window closes.
        </span>
      </label>

      <div class="toolbar" style="margin-top:12px;">
        <button class="ha-btn" ?disabled=${!canSubmit || this._fwSubmitting} @click=${this._onProposeTest}>
          Test
        </button>
      </div>
    `;
  }
}
