import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  Finding,
  OpenPort,
  ProbeOverview,
  FirewallRule,
  FirewallRuleAction,
  FirewallRuleProto,
  FirewallStatus,
  FirewallPendingTest,
  fetchScannerFindings,
  scanIntegrationNow,
  exportFinding,
  fetchVulns,
  scanVulnsNow,
  setVulnStatus,
  setMisconfigStatus,
  fetchHealth,
  fetchAccessInfo,
  fetchProbeStatus,
  fetchFirewallStatus,
  proposeFirewallTest,
  confirmFirewallTest,
  cancelFirewallTest,
  discardFirewallPending,
} from "../data/ha-soc-ws";

const STATUS_OPTIONS = ["new", "confirmed", "dismissed", "resolved"];
const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

function severityRank(severity: string): number {
  const i = SEVERITY_ORDER.indexOf(severity);
  return i === -1 ? SEVERITY_ORDER.length : i;
}

// Confidence values are ranked semantically, not alphabetically (the
// alphabet would put the scanner's "advisory" ahead of "high"). Each table
// has its own vocabulary: the integration scanner emits high/medium/advisory
// (scanner.py), the vulnerability correlator emits exact_cpe/curated_map/
// keyword/heuristic strongest-first (vulns.py). Unknown values return null
// so sortRows sinks them like any other unknown.
function confidenceRank(order: readonly string[], confidence: unknown): number | null {
  const i = order.indexOf(String(confidence));
  return i === -1 ? null : i;
}

const SCANNER_CONFIDENCE_ORDER = ["high", "medium", "advisory"] as const;
const VULN_CONFIDENCE_ORDER = ["exact_cpe", "curated_map", "keyword", "heuristic"] as const;

// True if an IPv4 dotted-quad is in an RFC 1918 private range
// (10/8, 172.16/12, 192.168/16). Loopback/link-local are handled separately.
function isRfc1918(addr: string): boolean {
  const m = addr.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const [a, b] = [Number(m[1]), Number(m[2])];
  if (a === 10) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  return false;
}

// Bind-address sort/grouping class for the Host Probe report. Lower priority
// sorts first: 0.0.0.0 (every interface) → routable/public (NOT RFC1918) →
// private (RFC1918) → loopback/link-local → unresolved (IPv6 not decoded).
// A port bound to 0.0.0.0 or a public address is the security-notable case,
// so those float to the top.
function bindClass(addr: string | null | undefined): {
  priority: number;
  label: string;
  cls: "high" | "medium" | "low" | "good" | "info";
} {
  if (addr === "0.0.0.0") return { priority: 0, label: "all interfaces", cls: "high" };
  if (!addr) return { priority: 4, label: "unresolved (IPv6)", cls: "info" };
  if (addr.startsWith("127.") || addr.startsWith("169.254."))
    return { priority: 3, label: "loopback / link-local", cls: "good" };
  if (isRfc1918(addr)) return { priority: 2, label: "private (RFC 1918)", cls: "low" };
  return { priority: 1, label: "public / routable", cls: "high" };
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
  @state() private _exportNotice: string | null = null;

  @state() private _firewall: FirewallStatus | null = null;
  @state() private _fwDraftRules: FirewallRule[] = [{ action: "allow", proto: "tcp", port: 0, source: "" }];
  @state() private _fwBackupAck = false;
  @state() private _fwSubmitting = false;
  @state() private _fwError: string | null = null;
  private _fwPollHandle: number | null = null;
  // The whole firewall feature is owner-only server-side (D-4), status
  // command included, so the card renders for the owner alone and a
  // non-owner admin sees the owner-only note instead. Defaults to false
  // and stays false when the access lookup fails: fail closed, exactly
  // like the WS gate underneath.
  @state() private _isOwner = false;

  // Column sort state, one per table (see sortable.ts). null means "no
  // user choice yet", in which case each table keeps its original default
  // ordering (severity-descending for findings, port-ascending for ports).
  @state() private _misconfigSort: SortState | null = null;
  @state() private _scannerSort: SortState | null = null;
  @state() private _vulnSort: SortState | null = null;
  @state() private _portSort: SortState | null = null;
  @state() private _fwRulesSort: SortState | null = null;

  private static readonly MISCONFIG_SORT: Record<string, (f: Finding) => unknown> = {
    check: (f) => f.check,
    summary: (f) => f.summary,
  };

  private static readonly SCANNER_SORT: Record<string, (f: Finding) => unknown> = {
    domain: (f) => f.domain,
    pattern: (f) => f.pattern,
    // file plus line in one string; localeCompare's numeric option keeps
    // line 9 before line 23 within the same file.
    location: (f) => `${f.file}:${f.line}`,
    confidence: (f) => confidenceRank(SCANNER_CONFIDENCE_ORDER, f.confidence),
    cwe: (f) => f.cwe,
  };

  private static readonly VULN_SORT: Record<string, (f: Finding) => unknown> = {
    cve: (f) => f.cve_id,
    cvss: (f) => {
      if (f.cvss == null) return null;
      const v = Number(f.cvss);
      return Number.isNaN(v) ? null : v;
    },
    confidence: (f) => confidenceRank(VULN_CONFIDENCE_ORDER, f.confidence),
  };

  private static readonly PORT_SORT: Record<string, (p: OpenPort) => unknown> = {
    port: (p) => p.port,
    proto: (p) => p.proto,
    interface: (p) => p.interface,
  };

  private static readonly FW_RULE_SORT: Record<string, (r: FirewallRule) => unknown> = {
    action: (r) => r.action,
    proto: (r) => r.proto,
    port: (r) => r.port,
    // null source displays as "any"; sort it as that word rather than
    // sinking it as unknown, since "any" is a definite value here.
    source: (r) => r.source ?? "any",
  };

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
      const [scanner, vulns, health, probe, access] = await Promise.all([
        fetchScannerFindings(this.hass),
        fetchVulns(this.hass),
        fetchHealth(this.hass),
        fetchProbeStatus(this.hass),
        // A failed access lookup reads as "not the owner" rather than
        // failing the whole tab; the server gate is what actually enforces.
        fetchAccessInfo(this.hass).catch(() => ({ is_owner: false })),
      ]);
      this._scannerFindings = scanner;
      this._vulnFindings = vulns;
      this._misconfigFindings = health.misconfig_findings;
      this._probe = probe;
      this._isOwner = !!access.is_owner;
      // ha_soc/firewall/status is owner-only (D-4); asking as a non-owner
      // would just bounce off the gate, so it is not asked at all.
      this._firewall = this._isOwner
        ? await fetchFirewallStatus(this.hass).catch(() => null)
        : null;
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

  // Owner-only escape hatch for an add-on gone silent mid-test: archives
  // the pending record as discarded_unreported. Offered only once the
  // countdown has lapsed (the server refuses it earlier), and it never
  // unblocks anything automatically; this click is the deliberate act.
  private async _onDiscardPending() {
    if (!this._firewall?.pending) return;
    const ok = confirm(
      "Discard this unreported firewall test?\n\n" +
        "The add-on never reported its outcome, so HA SOC does not know " +
        "what is live on the host. The record is archived as " +
        "'discarded_unreported' and new tests become possible again. " +
        "Nothing is changed on the host by discarding."
    );
    if (!ok) return;
    this._fwError = null;
    this._fwSubmitting = true;
    try {
      await discardFirewallPending(this.hass);
      this._applyFirewallStatus(await fetchFirewallStatus(this.hass));
    } catch (err: any) {
      this._fwError = err?.message ?? "Failed to discard the pending firewall test.";
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

  // The GHSA export is a copy-to-clipboard convenience, never a submission
  // channel (the server only shapes text; nothing is sent anywhere). The
  // confirmation names the stored snippet and the target integration
  // because the copied text is the one thing in this view designed to
  // leave the instance, and the operator should see exactly what code
  // excerpt and whose name it carries before it lands on the clipboard.
  private async _onExportFinding(f: any) {
    const ok = confirm(
      `Copy a GHSA-shaped advisory draft to the clipboard?\n\n` +
        `Integration: ${f.domain}\n` +
        `Matched code: ${f.snippet}\n\n` +
        `Nothing is submitted anywhere. The text is only placed on your ` +
        `clipboard for you to review and paste yourself.`
    );
    if (!ok) return;
    this._exportNotice = null;
    try {
      const ghsa = (await exportFinding(this.hass, f.id)) as {
        title: string;
        description: string;
        severity: string;
        cwe: string;
        affected: { ecosystem: string; package: string; version: string };
        references: string[];
      };
      const text = [
        `Title: ${ghsa.title}`,
        `Severity: ${ghsa.severity}`,
        `CWE: ${ghsa.cwe}`,
        `Package: ${ghsa.affected.package} (${ghsa.affected.ecosystem})`,
        ``,
        ghsa.description,
      ].join("\n");
      await navigator.clipboard.writeText(text);
      this._exportNotice = `Copied the advisory draft for ${f.domain} (${f.file}:${f.line}) to the clipboard.`;
    } catch (err: any) {
      this._exportNotice = `Export failed: ${err?.message ?? "could not copy to the clipboard"}`;
    }
  }

  private async _onMisconfigStatus(id: string, status: string) {
    await setMisconfigStatus(this.hass, id, status);
    await this._load();
  }

  // One header row per device instead of repeating the device name on
  // every CVE row — devices ordered by their own worst finding first,
  // findings within a device also worst-first, so both the grouping and
  // the reading order lead with what needs attention most.
  //
  // Column sorting reorders rows WITHIN each device group only; the group
  // header rows stay put. The one exception is the first (CVE) column:
  // sorting it also reorders the groups themselves by device name, giving
  // an alphabetical device listing in one click. Other columns keep the
  // default worst-first group order.
  private _groupedVulnFindings(): { device_name: string; findings: Finding[] }[] {
    const byDevice = new Map<string, Finding[]>();
    for (const f of this._vulnFindings) {
      const name = String(f.device_name ?? "Unknown device");
      const list = byDevice.get(name);
      if (list) list.push(f);
      else byDevice.set(name, [f]);
    }
    const sort = this._vulnSort;
    const groups = Array.from(byDevice.entries()).map(([device_name, findings]) => ({
      device_name,
      // Worst severity computed before any user sort reorders the rows,
      // so the default group order stays stable whatever column is active.
      worst: Math.min(...findings.map((f) => severityRank(f.severity))),
      findings: sort
        ? sortRows(findings, sort, HaSocScannerView.VULN_SORT)
        : [...findings].sort((a, b) => severityRank(a.severity) - severityRank(b.severity)),
    }));
    if (sort?.key === "cve") {
      groups.sort(
        (a, b) =>
          a.device_name.localeCompare(b.device_name, undefined, { sensitivity: "base", numeric: true }) *
          sort.dir
      );
    } else {
      groups.sort((a, b) => a.worst - b.worst);
    }
    return groups;
  }

  private _renderStatusSelect(id: string, current: string, onChange: (s: string) => void) {
    return html`
      <select @change=${(e: Event) => onChange((e.target as HTMLSelectElement).value)}>
        ${STATUS_OPTIONS.map((s) => html`<option value=${s} ?selected=${s === current}>${s}</option>`)}
      </select>
    `;
  }

  // Severity-descending (worst first) is the default until the user picks
  // a column; from then on the shared helper owns the order.
  private _sortedMisconfigFindings(): Finding[] {
    if (this._misconfigSort) {
      return sortRows(this._misconfigFindings, this._misconfigSort, HaSocScannerView.MISCONFIG_SORT);
    }
    return [...this._misconfigFindings].sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
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
                    ${sortableTh("Check", "check", this._misconfigSort, (n) => (this._misconfigSort = n))}
                    ${sortableTh("Summary", "summary", this._misconfigSort, (n) => (this._misconfigSort = n))}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._sortedMisconfigFindings().map(
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
                    ${sortableTh("Domain", "domain", this._scannerSort, (n) => (this._scannerSort = n))}
                    ${sortableTh("Pattern", "pattern", this._scannerSort, (n) => (this._scannerSort = n))}
                    ${sortableTh("Location", "location", this._scannerSort, (n) => (this._scannerSort = n))}
                    ${sortableTh("Confidence", "confidence", this._scannerSort, (n) => (this._scannerSort = n))}
                    ${sortableTh("CWE", "cwe", this._scannerSort, (n) => (this._scannerSort = n))}
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${sortRows(this._scannerFindings, this._scannerSort, HaSocScannerView.SCANNER_SORT).map(
                    (f: any) => html`
                      <tr>
                        <td>${f.domain}</td>
                        <td><span class="pill ${f.severity}"><span class="dot"></span>${f.pattern}</span></td>
                        <td>${f.file}:${f.line}</td>
                        <td>${f.confidence}</td>
                        <td>${f.cwe}</td>
                        <td>${this._renderStatusSelect(f.id, f.status, (s) => this._onVulnStatus(f.id, s))}</td>
                        <td><button class="ha-btn" @click=${() => this._onExportFinding(f)}>Export</button></td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
              ${this._exportNotice
                ? html`<p class="muted" style="font-size:12px;margin:6px 0 0;">${this._exportNotice}</p>`
                : nothing}
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
                    ${sortableTh("CVE", "cve", this._vulnSort, (n) => (this._vulnSort = n))}
                    ${sortableTh("CVSS", "cvss", this._vulnSort, (n) => (this._vulnSort = n))}
                    ${sortableTh("Confidence", "confidence", this._vulnSort, (n) => (this._vulnSort = n))}
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
                : this._renderPortsByBindAddress(result.open_ports)}
            `}
      </div>
    `;
  }

  // Group the host's listening ports by bind address. Group order is fixed
  // by security notability: 0.0.0.0 first, then public/routable
  // (non-RFC1918), then private (RFC1918), then loopback/link-local, then
  // unresolved. Column sorting never reorders the groups themselves; it
  // only reorders ports within each group (default: port ascending).
  private _renderPortsByBindAddress(ports: OpenPort[]) {
    const groups = new Map<string, OpenPort[]>();
    for (const p of ports) {
      const key = p.address ?? "__unresolved__";
      const arr = groups.get(key);
      if (arr) arr.push(p);
      else groups.set(key, [p]);
    }
    const ordered = Array.from(groups.entries()).sort((a, b) => {
      const ca = bindClass(a[0] === "__unresolved__" ? null : a[0]);
      const cb = bindClass(b[0] === "__unresolved__" ? null : b[0]);
      if (ca.priority !== cb.priority) return ca.priority - cb.priority;
      return a[0].localeCompare(b[0]);
    });

    return html`
      <table>
        <thead>
          <tr>
            ${sortableTh("Port", "port", this._portSort, (n) => (this._portSort = n))}
            ${sortableTh("Protocol", "proto", this._portSort, (n) => (this._portSort = n))}
            ${sortableTh("Interface", "interface", this._portSort, (n) => (this._portSort = n))}
          </tr>
        </thead>
        ${ordered.map(([key, groupPorts]) => {
          const addr = key === "__unresolved__" ? null : key;
          const info = bindClass(addr);
          return html`
            <tbody>
              <tr>
                <td colspan="3" style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
                  <strong>${addr ?? "unresolved (IPv6)"}</strong>
                  <span class="pill ${info.cls}" style="margin-left:8px;"
                    ><span class="dot"></span>${info.label}</span
                  >
                  <span class="muted" style="margin-left:8px;font-size:12px;"
                    >${groupPorts.length} port${groupPorts.length === 1 ? "" : "s"}</span
                  >
                </td>
              </tr>
              ${(this._portSort
                ? sortRows(groupPorts, this._portSort, HaSocScannerView.PORT_SORT)
                : groupPorts.slice().sort((a, b) => a.port - b.port)
              ).map(
                  (p) => html`
                    <tr>
                      <td>${p.port}</td>
                      <td>${p.proto}</td>
                      <td>
                        ${p.interface === "(all interfaces)"
                          ? html`<span class="pill high"><span class="dot"></span>all interfaces</span>`
                          : html`<span class="muted">${p.interface ?? "—"}</span>`}
                      </td>
                    </tr>
                  `
                )}
            </tbody>
          `;
        })}
      </table>
    `;
  }

  private _renderFirewallCard() {
    const probe = this._probe;
    const fw = this._firewall;
    // Same prerequisite as Host Probe: without the add-on actually
    // running, there is nothing that could apply these rules — the Host
    // Probe card above already explains why in that case.
    if (!probe?.supervisor || !probe?.installed) return nothing;
    // Owner-only in its entirety (D-4), the same one-line note treatment
    // the Settings tab gets: the server refuses every firewall command,
    // status included, for a non-owner admin, so rendering anything more
    // here would only be a card full of dead controls.
    if (!this._isOwner) {
      return html`
        <div class="card">
          <h3>Firewall Rules <span class="tag cosmetic">owner only</span></h3>
          <p class="muted" style="font-size:12.5px;">
            The firewall is available to the account owner only.
          </p>
        </div>
      `;
    }
    if (!fw) return nothing;

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
                    ${sortableTh("Action", "action", this._fwRulesSort, (n) => (this._fwRulesSort = n))}
                    ${sortableTh("Protocol", "proto", this._fwRulesSort, (n) => (this._fwRulesSort = n))}
                    ${sortableTh("Port", "port", this._fwRulesSort, (n) => (this._fwRulesSort = n))}
                    ${sortableTh("Source", "source", this._fwRulesSort, (n) => (this._fwRulesSort = n))}
                  </tr>
                </thead>
                <tbody>
                  ${sortRows(fw.known_rules, this._fwRulesSort, HaSocScannerView.FW_RULE_SORT).map(
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
        ${fw.pending
          ? html`
              ${this._renderFirewallPending(fw.pending)}
              ${this._renderFirewallBuilder(
                "A proposed change is still pending. A new test can only be proposed once the add-on has reported the outcome of the current one."
              )}
            `
          : this._renderFirewallBuilder(null)}
        ${this._fwError
          ? html`<p style="color:var(--error-color,#db4437);font-size:12.5px;margin-top:10px;">${this._fwError}</p>`
          : nothing}
      </div>
    `;
  }

  private _renderFirewallPending(pending: FirewallPendingTest) {
    const remaining = Math.max(0, Math.round((new Date(pending.expires_at).getTime() - Date.now()) / 1000));
    // The discard escape hatch appears only once the countdown has lapsed
    // (which is also exactly when the server stops refusing it): before
    // that, the add-on's report or its local timer may still resolve the
    // test the honest way. expires_at is re-anchored to applied_at server-
    // side, so "lapsed" here means the add-on's own timer has fired too,
    // if the add-on is alive at all.
    const countdownLapsed = Date.now() >= new Date(pending.expires_at).getTime();
    const statusLabel: Record<string, string> = {
      testing: pending.applied_at ? "Testing — live on the host" : "Queued — waiting for the add-on to apply",
      confirmed: "Confirmed — waiting for the add-on to acknowledge",
      reverted: "Reverting — waiting for the add-on to acknowledge",
      // The window has closed but the add-on has not confirmed the revert
      // yet; the record stays here (and blocks new proposals) until it does.
      expired_unreported: "Window expired, the add-on has not confirmed the revert yet",
      // Pre-rename spelling of the same state, possibly persisted by an
      // older version of the integration.
      expired: "Window expired, the add-on has not confirmed the revert yet",
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
        ${countdownLapsed
          ? html`
              <button
                class="ha-btn danger"
                ?disabled=${this._fwSubmitting}
                title="The add-on never reported this test's outcome. Discard archives it as 'discarded_unreported' so a new test can be proposed; nothing on the host is changed."
                @click=${this._onDiscardPending}
              >
                Discard unreported test
              </button>
            `
          : nothing}
      </div>
    `;
  }

  // blockedReason is non-null while a pending test still occupies the
  // one-at-a-time slot server-side; the builder stays visible so a next
  // ruleset can be drafted, but the Test button is disabled and says why,
  // matching the server's test_pending_unreported refusal instead of
  // letting the click bounce off it.
  private _renderFirewallBuilder(blockedReason: string | null) {
    const canSubmit =
      blockedReason === null &&
      this._fwBackupAck &&
      this._fwDraftRules.length > 0 &&
      this._fwDraftRules.every((r) => this._fwRuleValid(r));

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
      ${blockedReason
        ? html`<p class="muted" style="font-size:12px;margin:6px 0 0;">${blockedReason}</p>`
        : nothing}
    `;
  }
}
