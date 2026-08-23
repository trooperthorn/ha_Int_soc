import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  Finding,
  ProbeOverview,
  fetchScannerFindings,
  scanIntegrationNow,
  fetchVulns,
  scanVulnsNow,
  setVulnStatus,
  setMisconfigStatus,
  fetchHealth,
  fetchProbeStatus,
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

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      const [scanner, vulns, health, probe] = await Promise.all([
        fetchScannerFindings(this.hass),
        fetchVulns(this.hass),
        fetchHealth(this.hass),
        fetchProbeStatus(this.hass),
      ]);
      this._scannerFindings = scanner;
      this._vulnFindings = vulns;
      this._misconfigFindings = health.misconfig_findings;
      this._probe = probe;
    } finally {
      this._loading = false;
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
}
