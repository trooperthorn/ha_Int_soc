import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  Finding,
  fetchScannerFindings,
  scanIntegrationNow,
  fetchVulns,
  scanVulnsNow,
  setVulnStatus,
  setMisconfigStatus,
  fetchHealth,
} from "../data/ha-soc-ws";

const STATUS_OPTIONS = ["new", "confirmed", "dismissed", "resolved"];

@customElement("ha-soc-scanner-view")
export class HaSocScannerView extends LitElement {
  static styles = sharedStyles;

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _scannerFindings: Finding[] = [];
  @state() private _vulnFindings: Finding[] = [];
  @state() private _misconfigFindings: Finding[] = [];
  @state() private _loading = true;
  @state() private _scanning = false;

  connectedCallback(): void {
    super.connectedCallback();
    this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      const [scanner, vulns, health] = await Promise.all([
        fetchScannerFindings(this.hass),
        fetchVulns(this.hass),
        fetchHealth(this.hass),
      ]);
      this._scannerFindings = scanner;
      this._vulnFindings = vulns;
      this._misconfigFindings = health.misconfig_findings;
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
                    <th>Device</th>
                    <th>CVE</th>
                    <th>CVSS</th>
                    <th>Confidence</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._vulnFindings.map(
                    (f: any) => html`
                      <tr>
                        <td>${f.device_name}</td>
                        <td>${f.cve_id ?? "—"}</td>
                        <td><span class="pill ${f.severity}"><span class="dot"></span>${f.cvss ?? "unscored"}</span></td>
                        <td>${f.confidence}</td>
                        <td>${this._renderStatusSelect(f.id, f.status, (s) => this._onVulnStatus(f.id, s))}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>

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
    `;
  }
}
