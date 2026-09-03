import { html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import { HaSocCustomizableView } from "../customizable-view";
import type { LayoutSection } from "../customize";
import { SortState, sortRows, sortableTh } from "../sortable";
import {
  Finding,
  OpenPort,
  ProbeOverview,
  FirewallRule,
  FirewallRuleAction,
  FirewallRuleProto,
  FirewallRuleFamily,
  FirewallStatus,
  FirewallPendingTest,
  ScannerDomainCoverage,
  fetchScannerListing,
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

// Confidence ranks semantically per table vocabulary (scanner.py, vulns.py); unknown returns null and sinks.
function confidenceRank(order: readonly string[], confidence: unknown): number | null {
  const i = order.indexOf(String(confidence));
  return i === -1 ? null : i;
}

const SCANNER_CONFIDENCE_ORDER = ["high", "medium", "advisory"] as const;
const VULN_CONFIDENCE_ORDER = ["exact_cpe", "curated_map", "keyword", "heuristic"] as const;

// Pre-dual-stack records carry no family; absent displays as "both", matching the server.
function familyLabel(family?: FirewallRuleFamily): string {
  if (family === "4") return "IPv4";
  if (family === "6") return "IPv6";
  return "IPv4+IPv6";
}

// Mirrors the server's derivation: a colon means IPv6, otherwise IPv4; null means no source, no pin.
function familyForSource(source: string): FirewallRuleFamily | null {
  if (!source) return null;
  return source.includes(":") ? "6" : "4";
}

// True for an RFC 1918 IPv4 address (10/8, 172.16/12, 192.168/16); loopback/link-local are handled separately.
function isRfc1918(addr: string): boolean {
  const m = addr.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!m) return false;
  const [a, b] = [Number(m[1]), Number(m[2])];
  if (a === 10) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  return false;
}

// Bind-address sort class: 0.0.0.0, then public, private, loopback/link-local, unresolved (IPv6 not decoded).
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
export class HaSocScannerView extends HaSocCustomizableView {
  protected get viewId() {
    return "scanner";
  }

  static styles = sharedStyles;

  @state() private _scannerFindings: Finding[] = [];
  // Per-domain coverage; null means an older backend sent no map. A domain without a record renders "not scanned".
  @state() private _coverage: Record<string, ScannerDomainCoverage> | null = null;
  @state() private _vulnFindings: Finding[] = [];
  @state() private _misconfigFindings: Finding[] = [];
  @state() private _probe: ProbeOverview | null = null;
  @state() private _loading = true;
  // Non-null when the load failed; rendered as a could-not-load state, never empty tables.
  @state() private _error: string | null = null;
  @state() private _scanning = false;
  @state() private _scanError: string | null = null;
  @state() private _exportNotice: string | null = null;

  @state() private _firewall: FirewallStatus | null = null;
  @state() private _fwDraftRules: FirewallRule[] = [
    { action: "allow", proto: "tcp", port: 0, source: "", family: "both" },
  ];
  @state() private _fwBackupAck = false;
  @state() private _fwSubmitting = false;
  @state() private _fwError: string | null = null;
  private _fwPollHandle: number | null = null;
  // The firewall feature is owner-only server-side; defaults false and stays false on a failed lookup (fail closed).
  @state() private _isOwner = false;

  // Column sort state per table; null keeps each table's default order.
  @state() private _misconfigSort: SortState | null = null;
  @state() private _scannerSort: SortState | null = null;
  @state() private _vulnSort: SortState | null = null;
  @state() private _portSort: SortState | null = null;
  @state() private _fwRulesSort: SortState | null = null;
  @state() private _coverageSort: SortState | null = null;

  private static readonly MISCONFIG_SORT: Record<string, (f: Finding) => unknown> = {
    check: (f) => f.check,
    // Ascending reads worst first, matching the default; split-severity findings stay distinct rows.
    severity: (f) => severityRank(String(f.severity)),
    summary: (f) => f.summary,
  };

  // Coverage sort accessors; scanned_at is ISO and compares as a string.
  private static readonly COVERAGE_SORT: Record<
    string,
    (r: { domain: string; cov: ScannerDomainCoverage }) => unknown
  > = {
    domain: (r) => r.domain,
    files: (r) => r.cov.scanned_files,
    oversize: (r) => r.cov.skipped_oversize,
    over_cap: (r) => r.cov.skipped_over_cap,
    parse_failures: (r) => r.cov.parse_failures,
    scanned_at: (r) => r.cov.scanned_at,
  };

  private static readonly SCANNER_SORT: Record<string, (f: Finding) => unknown> = {
    domain: (f) => f.domain,
    pattern: (f) => f.pattern,
    // file plus line in one string; numeric localeCompare keeps line 9 before line 23.
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
    // null source displays as "any" and sorts as that word, since "any" is a definite value.
    source: (r) => r.source ?? "any",
    // Sorted by display label so IPv4 < IPv4+IPv6 < IPv6; an absent family sorts as dual-stack.
    family: (r) => familyLabel(r.family),
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
    this._error = null;
    try {
      const [scanner, vulns, health, probe, access] = await Promise.all([
        fetchScannerListing(this.hass),
        fetchVulns(this.hass),
        fetchHealth(this.hass),
        fetchProbeStatus(this.hass),
        // A failed access lookup reads as "not the owner"; the server gate enforces.
        fetchAccessInfo(this.hass).catch(() => ({ is_owner: false })),
      ]);
      this._scannerFindings = scanner.findings;
      this._coverage = scanner.coverage ?? null;
      this._vulnFindings = vulns;
      this._misconfigFindings = health.misconfig_findings;
      this._probe = probe;
      this._isOwner = !!access.is_owner;
      // ha_soc/firewall/status is owner-only; not asked as a non-owner.
      this._firewall = this._isOwner
        ? await fetchFirewallStatus(this.hass).catch(() => null)
        : null;
      this._maybeManageFirewallPolling();
    } catch (err: any) {
      // One rejected fetch fails the whole load; an empty findings table would read as a clean scan.
      this._error = err?.message ?? String(err);
    } finally {
      this._loading = false;
    }
  }

  // Polls ha_soc/firewall/status every 2s while any test is in flight; stops itself when nothing is pending.
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

  // A resolved test consumed its acknowledgment; require a fresh one for the next proposal.
  private _applyFirewallStatus(status: FirewallStatus) {
    const hadPending = this._firewall?.pending != null;
    this._firewall = status;
    if (hadPending && !status.pending) {
      this._fwBackupAck = false;
    }
    this._maybeManageFirewallPolling();
  }

  private _fwRuleValid(r: FirewallRule): boolean {
    const family = r.family ?? "both";
    // A sourced rule's family must match its source pin; this only catches a state bug, matching the server.
    const pinned = familyForSource(r.source ?? "");
    return (
      Number.isInteger(r.port) &&
      r.port >= 1 &&
      r.port <= 65535 &&
      (r.action === "allow" || r.action === "deny") &&
      (r.proto === "tcp" || r.proto === "udp") &&
      (family === "4" || family === "6" || family === "both") &&
      (pinned === null || pinned === family)
    );
  }

  private _fwUpdateRule(index: number, changes: Partial<FirewallRule>) {
    this._fwDraftRules = this._fwDraftRules.map((r, i) => (i === index ? { ...r, ...changes } : r));
  }

  private _fwAddRule() {
    this._fwDraftRules = [
      ...this._fwDraftRules,
      { action: "allow", proto: "tcp", port: 0, source: "", family: "both" },
    ];
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
        // The server re-derives a sourced rule's family; sending the builder's value keeps the payload explicit.
        family: r.family ?? "both",
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

  // Owner-only discard for an add-on gone silent; offered only once the countdown has lapsed.
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
    this._scanError = null;
    try {
      await scanIntegrationNow(this.hass);
      await this._load();
    } catch (err: any) {
      // A rejected scan request shows the server's reason next to the button.
      this._scanError = `Integration scan failed: ${err?.message ?? err}`;
    } finally {
      this._scanning = false;
    }
  }

  private async _onScanVulns() {
    this._scanning = true;
    this._scanError = null;
    try {
      await scanVulnsNow(this.hass);
      await this._load();
    } catch (err: any) {
      this._scanError = `Device vulnerability scan failed: ${err?.message ?? err}`;
    } finally {
      this._scanning = false;
    }
  }

  private async _onVulnStatus(id: string, status: string) {
    this._scanError = null;
    try {
      await setVulnStatus(this.hass, id, status);
    } catch (err: any) {
      // The reload re-renders the select from stored state, so a rejection restores the old status.
      this._scanError = `Status change failed: ${err?.message ?? err}`;
    }
    await this._load();
  }

  // The GHSA export is copy-to-clipboard only; the confirmation names the snippet and integration. See docs/security.md.
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
    this._scanError = null;
    try {
      await setMisconfigStatus(this.hass, id, status);
    } catch (err: any) {
      this._scanError = `Status change failed: ${err?.message ?? err}`;
    }
    await this._load();
  }

  // One header row per device, worst-first; sorting reorders within groups only, except CVE which also orders groups by name.
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
      // Worst severity computed before any user sort, so the group order stays stable.
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

  // Coverage per domain from the last completed pass; renders nothing when the backend sent no map.
  private _renderScannerCoverage() {
    if (!this._coverage) return nothing;
    const coveredDomains = new Set(Object.keys(this._coverage));
    const findingDomains = new Set(this._scannerFindings.map((f: any) => String(f.domain)));
    const notScanned = Array.from(findingDomains)
      .filter((d) => !coveredDomains.has(d))
      .sort((a, b) => a.localeCompare(b));
    const rows = Object.entries(this._coverage).map(([domain, cov]) => ({ domain, cov }));
    const sorted = this._coverageSort
      ? sortRows(rows, this._coverageSort, HaSocScannerView.COVERAGE_SORT)
      : rows.slice().sort((a, b) => a.domain.localeCompare(b.domain));

    return html`
      <h4 class="fw-subhead">Scan coverage</h4>
      <p class="muted" style="font-size:12px;margin-top:-6px;">
        What the most recent completed pass over each domain actually looked at.
        A domain is never implied clean by an absent record.
      </p>
      ${!rows.length
        ? html`<div class="empty">No domain has completed a scan yet.</div>`
        : html`
            <table>
              <thead>
                <tr>
                  ${sortableTh("Domain", "domain", this._coverageSort, (n) => (this._coverageSort = n))}
                  ${sortableTh("Files scanned", "files", this._coverageSort, (n) => (this._coverageSort = n), {
                    numeric: true,
                  })}
                  ${sortableTh(
                    "Skipped (too large)",
                    "oversize",
                    this._coverageSort,
                    (n) => (this._coverageSort = n),
                    { numeric: true }
                  )}
                  ${sortableTh(
                    "Skipped (over cap)",
                    "over_cap",
                    this._coverageSort,
                    (n) => (this._coverageSort = n),
                    { numeric: true }
                  )}
                  ${sortableTh(
                    "Parse failures",
                    "parse_failures",
                    this._coverageSort,
                    (n) => (this._coverageSort = n),
                    { numeric: true }
                  )}
                  ${sortableTh("Scanned at", "scanned_at", this._coverageSort, (n) => (this._coverageSort = n))}
                </tr>
              </thead>
              <tbody>
                ${sorted.map(
                  (r) => html`
                    <tr>
                      <td>${r.domain}</td>
                      <td class="num">${r.cov.scanned_files}</td>
                      <td class="num">${r.cov.skipped_oversize}</td>
                      <td class="num">${r.cov.skipped_over_cap}</td>
                      <td class="num">${r.cov.parse_failures}</td>
                      <td>${new Date(r.cov.scanned_at).toLocaleString()}</td>
                    </tr>
                  `
                )}
              </tbody>
            </table>
          `}
      ${notScanned.length
        ? html`<p style="font-size:12.5px;margin-top:8px;">
            <strong>Not scanned this pass:</strong> ${notScanned.join(", ")}.
            ${notScanned.length === 1 ? "Its" : "Their"} existing findings above were not
            re-verified in the most recent run.
          </p>`
        : nothing}
    `;
  }

  private _renderStatusSelect(id: string, current: string, onChange: (s: string) => void) {
    return html`
      <select @change=${(e: Event) => onChange((e.target as HTMLSelectElement).value)}>
        ${STATUS_OPTIONS.map((s) => html`<option value=${s} ?selected=${s === current}>${s}</option>`)}
      </select>
    `;
  }

  // Severity-descending is the default until the user picks a column.
  private _sortedMisconfigFindings(): Finding[] {
    if (this._misconfigSort) {
      return sortRows(this._misconfigFindings, this._misconfigSort, HaSocScannerView.MISCONFIG_SORT);
    }
    return [...this._misconfigFindings].sort((a, b) => severityRank(a.severity) - severityRank(b.severity));
  }

  render() {
    if (this._loading) return html`<div class="empty">Loading findings…</div>`;
    if (this._error)
      return html`
        <div class="card" style="border:1px solid var(--error-color,#db4437);">
          <h3>Could not load the Scanner tab</h3>
          <p style="font-size:13px;">${this._error}</p>
          <button class="ha-btn" @click=${() => this._load()}>Retry</button>
        </div>
      `;

    const sections: LayoutSection[] = [
      {
        id: "misconfig",
        title: "Misconfiguration Findings",
        render: () => html`
      <div class="card">
        <h3>Misconfiguration Findings</h3>
        ${!this._misconfigFindings.length
          ? html`<div class="empty">No findings.</div>`
          : html`
              <table>
                <thead>
                  <tr>
                    ${sortableTh("Check", "check", this._misconfigSort, (n) => (this._misconfigSort = n))}
                    ${sortableTh("Severity", "severity", this._misconfigSort, (n) => (this._misconfigSort = n))}
                    ${sortableTh("Summary", "summary", this._misconfigSort, (n) => (this._misconfigSort = n))}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${this._sortedMisconfigFindings().map(
                    (f: any) => html`
                      <tr>
                        <td>${f.check}</td>
                        <td><span class="pill ${f.severity}"><span class="dot"></span>${f.severity}</span></td>
                        <td>${f.summary}</td>
                        <td>
                          ${f.acknowledged_by_design
                            ? html`<span class="tag enforced" title=${f.acknowledged_reason ?? "Acknowledged by design"}
                                >acknowledged by design</span
                              >`
                            : this._renderStatusSelect(f.id, f.status, (s) => this._onMisconfigStatus(f.id, s))}
                        </td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>
        `,
      },
      {
        id: "integration_scanner",
        title: "Integration Security Scanner",
        render: () => html`
      <div class="card">
        <h3>Integration Security Scanner</h3>
        <p class="muted" style="margin-top:-8px;font-size:12.5px;">
          Static AST/regex analysis of every installed integration's source — core and
          custom. Every finding is advisory and needs a human to confirm; Home
          Assistant's own quality tooling (hassfest) never checks for these patterns and
          never runs against custom_components at all. These rules find unobfuscated
          pattern instances only; a dynamically constructed call, a string-built
          decorator, or a renamed import will not be detected.
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
        ${this._renderScannerCoverage()}
      </div>
        `,
      },
      {
        id: "device_vulns",
        title: "Device Vulnerabilities",
        render: () => html`
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
        `,
      },
      { id: "host_probe", title: "Host Probe", render: () => this._renderProbeCard() },
      { id: "firewall_rules", title: "Firewall Rules", render: () => this._renderFirewallCard() },
    ];
    return html`
      ${this._scanError
        ? html`<div class="card" style="border:1px solid var(--error-color,#db4437);">
            <p style="font-size:13px;color:var(--error-color,#db4437);margin:0;">${this._scanError}</p>
          </div>`
        : nothing}
      ${this._renderSections(sections)}
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

  // Firewall coverage per address family; a null bind address is an IPv6 listener matched by port and protocol only.
  private _fwRuleCoveringPort(p: OpenPort): FirewallRule | null {
    const rules = this._firewall?.known_rules;
    if (!rules?.length) return null;
    const rowFamily: FirewallRuleFamily = p.address ? "4" : "6";
    const matches = rules.filter((r) => {
      const fam = r.family ?? "both";
      return r.port === p.port && r.proto === p.proto && (fam === "both" || fam === rowFamily);
    });
    if (!matches.length) return null;
    // Deny beats allow; among equals an any-source rule beats a source-scoped one.
    matches.sort((a, b) => {
      if (a.action !== b.action) return a.action === "deny" ? -1 : 1;
      return (a.source ? 1 : 0) - (b.source ? 1 : 0);
    });
    return matches[0];
  }

  private _renderPortRuleCell(p: OpenPort) {
    const rule = this._fwRuleCoveringPort(p);
    // An IPv6 listener's bind address is null, so its match rests on port and protocol alone.
    const ipv6Caveat = !p.address
      ? " IPv6 bind addresses are not decoded by the add-on, so this correlation is by port and protocol only."
      : "";
    if (!rule) {
      return html`<td class="muted"><span title=${"No HA_SOC_RULES entry matches this port and protocol for this listener's address family." + ipv6Caveat}>no rule</span></td>`;
    }
    const scope = rule.source ? `from ${rule.source}` : "any source";
    return html`
      <td>
        <span
          class="pill ${rule.action === "allow" ? "good" : "critical"}"
          title=${`Covered by the ${rule.action} ${rule.proto}/${rule.port} rule (${familyLabel(rule.family)}, ${scope}).` +
          (rule.source ? " Source-scoped: traffic from other sources is not affected by it." : "") +
          ipv6Caveat}
          ><span class="dot"></span>${rule.action}${!p.address ? " (by port)" : ""}</span
        >
      </td>
    `;
  }

  // Ports grouped by bind address in fixed notability order; sorting reorders within groups only. See docs/design.md.
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

    // Coverage column renders only when known rules exist; an empty column would read as "nothing covered".
    const showRuleCol = !!this._firewall?.known_rules?.length;
    const colCount = showRuleCol ? 4 : 3;

    return html`
      <table>
        <thead>
          <tr>
            ${sortableTh("Port", "port", this._portSort, (n) => (this._portSort = n))}
            ${sortableTh("Protocol", "proto", this._portSort, (n) => (this._portSort = n))}
            ${sortableTh("Interface", "interface", this._portSort, (n) => (this._portSort = n))}
            ${showRuleCol ? html`<th>Covered by rule</th>` : nothing}
          </tr>
        </thead>
        ${ordered.map(([key, groupPorts]) => {
          const addr = key === "__unresolved__" ? null : key;
          const info = bindClass(addr);
          return html`
            <tbody>
              <tr>
                <td colspan=${colCount} style="background:rgba(var(--rgb-primary-text-color,0,0,0),0.04);">
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
                      ${showRuleCol ? this._renderPortRuleCell(p) : nothing}
                    </tr>
                  `
                )}
            </tbody>
          `;
        })}
      </table>
    `;
  }

  // Family cell shared by the active and proposed tables, with the server's partial marker.
  private _renderFamilyCell(r: FirewallRule) {
    return html`
      <td>
        ${familyLabel(r.family)}
        ${r.partially_applied
          ? html`<span
              class="pill high"
              style="margin-left:6px;"
              title="The host kernel does not support ip6tables, so the IPv6 half of this rule is not applied. Only its IPv4 half (if any) is live."
              ><span class="dot"></span>IPv6 not applied</span
            >`
          : nothing}
      </td>
    `;
  }

  // Latest archived test's failure reason, rendered only when the newest history entry carries one.
  private _renderLastOutcomeReason(fw: FirewallStatus) {
    const latest = fw.history.length ? fw.history[fw.history.length - 1] : null;
    if (!latest?.reason) return nothing;
    return html`
      <p style="color:var(--error-color,#db4437);font-size:12.5px;margin:8px 0 0;">
        Last test (${latest.test_id.slice(0, 8)}) ended ${latest.status}: ${latest.reason}
      </p>
    `;
  }

  private _renderFirewallCard() {
    const probe = this._probe;
    const fw = this._firewall;
    // Same prerequisite as Host Probe: the add-on must be running.
    if (!probe?.supervisor || !probe?.installed) return nothing;
    // Owner-only in its entirety; the server refuses every firewall command for a non-owner admin.
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
          automatically once its test window closes. Rules are dual-stack by default:
          a rule with no source applies to IPv4 and IPv6 alike, and a source address
          pins the rule to that address's own family.
        </p>
        ${fw.ipv6_supported === false
          ? html`
              <p
                style="color:var(--error-color,#db4437);font-size:12.5px;border:1px solid var(--error-color,#db4437);border-radius:4px;padding:8px 10px;"
              >
                IPv6 rules not applied: the host kernel does not support ip6tables.
                Rules with family IPv6 are not live at all, and dual-stack rules are
                live for IPv4 only.
              </p>
            `
          : nothing}

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
                    ${sortableTh("Family", "family", this._fwRulesSort, (n) => (this._fwRulesSort = n))}
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
                        ${this._renderFamilyCell(r)}
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
        ${this._renderLastOutcomeReason(fw)}
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
    // Discard appears only once the countdown lapses, which is when the server stops refusing it.
    const countdownLapsed = Date.now() >= new Date(pending.expires_at).getTime();
    const statusLabel: Record<string, string> = {
      testing: pending.applied_at ? "Testing — live on the host" : "Queued — waiting for the add-on to apply",
      confirmed: "Confirmed — waiting for the add-on to acknowledge",
      reverted: "Reverting — waiting for the add-on to acknowledge",
      // Window closed, add-on has not confirmed the revert; the record blocks new proposals until it does.
      expired_unreported: "Window expired, the add-on has not confirmed the revert yet",
      // Pre-rename spelling of expired_unreported, possibly persisted by an older version.
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
            <th>Family</th>
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
                ${this._renderFamilyCell(r)}
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

  // blockedReason is non-null while a pending test holds the server's single slot; Test is disabled and says why.
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
            <th>Family</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${this._fwDraftRules.map((r, i) => {
            // A source address pins the family (the server derives and
            // enforces exactly this), so the selector locks to the
            // derived value while a source is present and is free
            // (default both) otherwise.
            const pinned = familyForSource(r.source ?? "");
            const family = pinned ?? r.family ?? "both";
            return html`
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
                    placeholder="e.g. 192.168.10.0/24 or fd00::/8"
                    .value=${r.source ?? ""}
                    style="width:170px;"
                    @input=${(e: Event) => {
                      const source = (e.target as HTMLInputElement).value;
                      const derived = familyForSource(source);
                      // Entering a source pins the family to it; clearing
                      // the source returns to the dual-stack default
                      // rather than silently keeping the pin.
                      this._fwUpdateRule(i, { source, family: derived ?? "both" });
                    }}
                  />
                </td>
                <td>
                  <select
                    ?disabled=${pinned !== null}
                    title=${pinned !== null
                      ? "Locked: the source address pins this rule to its own address family."
                      : "IPv4+IPv6 writes the rule into both tables; pick one family to scope it."}
                    @change=${(e: Event) =>
                      this._fwUpdateRule(i, {
                        family: (e.target as HTMLSelectElement).value as FirewallRuleFamily,
                      })}
                  >
                    <option value="both" ?selected=${family === "both"}>IPv4+IPv6</option>
                    <option value="4" ?selected=${family === "4"}>IPv4</option>
                    <option value="6" ?selected=${family === "6"}>IPv6</option>
                  </select>
                </td>
                <td><button class="ha-btn danger" @click=${() => this._fwRemoveRule(i)}>Remove</button></td>
              </tr>
            `;
          })}
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
