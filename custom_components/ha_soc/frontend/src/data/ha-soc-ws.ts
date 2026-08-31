import type { HomeAssistant } from "../types";

/** Thin typed wrappers over hass.callWS for every ha_soc/* command. */

export interface HaSocUser {
  id: string;
  name: string | null;
  is_owner: boolean;
  is_admin: boolean;
  is_active: boolean;
  local_only: boolean;
  groups: string[];
  mfa_enabled: boolean;
  last_login_at: string | null;
  last_login_ip: string | null;
  llat_count: number;
  llat_oldest_days: number | null;
  account_age_days: number | null;
  auth_provider_types: string[];
  // False when every credential comes from a non-homeassistant auth
  // provider (SSO/header proxy, trusted_networks, command line): HA
  // cannot observe a second factor enforced upstream, so the Users view
  // renders "MFA not assessable" instead of a red "none" (D-18).
  mfa_assessable: boolean;
}

export interface RiskFactor {
  name: string;
  // Pre-clamp contribution. applied_points is this factor's share of the
  // final 0-100 score after clamping; the applied_points of a result's
  // factors sum exactly to its score (work item 3.5). Optional so a
  // result computed by an older backend still renders.
  points: number;
  applied_points?: number;
  detail: string;
}

export interface RiskResult {
  user_id: string;
  score: number;
  band: "low" | "moderate" | "high" | "critical";
  factors: RiskFactor[];
}

export interface PostureResult {
  score: number;
  grade: "A" | "B" | "C" | "D" | "F";
  // Provisional posture (work item 3.4, D-10): true until every posture
  // term has computed from real data at least once ever; missing_terms
  // lists the ones still waiting, and term_computed_at carries each
  // term's first-computed timestamp (null while missing).
  provisional: boolean;
  missing_terms: string[];
  term_computed_at?: Record<string, string | null>;
  breakdown: Record<string, number>;
}

export interface Detection {
  id: string;
  rule_id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  user_id: string | null;
  ip: string | null;
  ts: string;
  last_seen: string;
  status: "open" | "ack" | "resolved";
  title: string;
  detail: Record<string, unknown>;
}

export interface AuditEvent {
  ts: string;
  user_id: string | null;
  category: string;
  domain: string | null;
  service: string | null;
  entity_ids: string[];
  ip: string | null;
  attempted_user: string | null;
  detail: Record<string, unknown>;
}

export interface Finding {
  id: string;
  severity: string;
  status: string;
  first_seen: string;
  last_seen: string;
  [key: string]: unknown;
}

export interface DashboardSummary {
  posture: PostureResult;
  posture_history: { date: string; score: number; grade: string }[];
  open_detections_count: number;
  users_at_risk_count: number;
  total_users_count: number;
  critical_high_vuln_count: number;
  risk_band_counts: Record<string, number>;
  mfa_counts: { enabled: number; disabled: number };
  detection_severity_counts: Record<string, number>;
  entity_state_counts: { unavailable: number; unknown: number; total: number };
}

// Mirrors vulns.py's DEVICE_STATUS_* — a device's live availability, a
// separate axis from vulnerability severity. See that module's docstring.
export type DeviceStatus = "available" | "partial" | "unavailable" | "disabled" | "no_entities";

export interface DeviceOverviewRow {
  device_id: string;
  name: string;
  vendor: string;
  os: string;
  risk_score: number;
  total_findings: number;
  severity_counts: { critical: number; high: number; medium: number; low: number };
  status: DeviceStatus;
}

export interface DeviceOverview {
  devices: DeviceOverviewRow[];
  status_counts: Record<DeviceStatus, number>;
  by_vendor: Record<string, number>;
  combined_risk_score: number;
}

// Mirrors health.py's ISSUE_CATEGORY_* — at most one category per
// integration, priority-ordered (credential > failing > communication >
// collection > errors > debug_logging > disabled). An integration with
// none of these doesn't appear at all.
export type IntegrationIssueCategory =
  | "credential"
  | "failing"
  | "communication"
  | "collection"
  | "errors"
  | "debug_logging"
  | "disabled";

export interface IntegrationIssueRow {
  entry_id: string;
  domain: string;
  title: string;
  state: string;
  reason: string | null;
  disabled_by: string | null;
  error_count_24h: number;
  unavailable_ratio: number;
  retry_transitions_24h: number;
  issue_category: IntegrationIssueCategory;
}

export interface IntegrationOverview {
  integrations: IntegrationIssueRow[];
  category_counts: Record<IntegrationIssueCategory, number>;
}

// Mirrors probe.py's async_probe_overview() — an honest three-way answer,
// never silently-empty data mistakeable for "scanned, nothing found".
export interface OpenPort {
  port: number;
  proto: "tcp" | "udp";
  process?: string | null;
  // Absent/null on a report from an older add-on version, or when the
  // bind address is IPv6 (decoding that correctly wasn't worth the risk
  // of silently showing a wrong address — see run.sh).
  address?: string | null;
  interface?: string | null;
}

export interface HostProbeResult {
  open_ports: OpenPort[];
  scanner_version: string | null;
  reported_at: string;
}

export interface ProbeOverview {
  supervisor: boolean;
  installed: boolean;
  running: boolean;
  version: string | null;
  update_available: boolean;
  result: HostProbeResult | null;
}

// Mirrors firewall.py's RULE_SCHEMA / pending-test state machine. See that
// module's docstring for the full read/write safety design — Core only
// ever proposes and displays; the add-on is the only thing that actually
// touches iptables, and its own report (known_rules) is always the final
// word on what's really active.
export type FirewallRuleAction = "allow" | "deny";
export type FirewallRuleProto = "tcp" | "udp";
// Address family a rule targets (work item 2.4): "4" is written with
// iptables, "6" with ip6tables, "both" mirrored into both tables. The
// server derives the family from a rule's source address (an IPv4 source
// pins "4", an IPv6 source pins "6") and rejects a contradicting explicit
// value; a rule with no source defaults to "both".
export type FirewallRuleFamily = "4" | "6" | "both";

export interface FirewallRule {
  action: FirewallRuleAction;
  proto: FirewallRuleProto;
  port: number;
  source?: string | null;
  // Optional because records persisted before the dual-stack change carry
  // no family; the server treats an absent value as "both".
  family?: FirewallRuleFamily;
  // Set by the server, at read time, on every "6"/"both" rule while the
  // add-on reports ipv6_supported=false: the IPv6 half of this rule is
  // not on the host, and the card must say so rather than showing a
  // silent IPv4-only success.
  partially_applied?: boolean;
}

// "expired_unreported" is the display-only status a timed-out pending test
// carries until the add-on's own report archives it; "expired" is the same
// state's pre-rename spelling, kept so a record persisted by an older
// version still type-checks. "discarded_unreported" is the terminal status
// of a history entry the owner discarded after the add-on went silent
// mid-test (ha_soc/firewall/discard_pending); it never appears on a live
// pending record.
export type FirewallTestStatus =
  | "testing"
  | "confirmed"
  | "reverted"
  | "expired"
  | "expired_unreported"
  | "discarded_unreported";

export interface FirewallPendingTest {
  test_id: string;
  proposed_rules: FirewallRule[];
  status: FirewallTestStatus;
  requested_by: string;
  requested_at: string;
  // null until the add-on's poll actually picks this up and applies it —
  // still "testing" but not live on the host yet.
  applied_at: string | null;
  // Until the apply is handed to the add-on this is propose time plus the
  // window (the staleness bound for a proposal never picked up); the
  // moment applied_at is set the server re-anchors it to applied_at plus
  // window_seconds, so the countdown rendered from it tracks the add-on's
  // real local revert timer instead of running up to one poll interval
  // ahead of it.
  expires_at: string;
  window_seconds: number;
  resolved_at?: string;
  resolved_by?: string;
  // The add-on's bounded explanation of a resolution (carried protocol
  // item): "backup_failed", or the failing rule and family when an apply
  // failed in either table. Only ever present on archived history
  // records, because it arrives with the resolution report that archives
  // them.
  reason?: string | null;
}

export interface FirewallStatus {
  known_rules: FirewallRule[] | null;
  known_rules_reported_at: string | null;
  // Whether ip6tables works on the host, as last reported by the add-on
  // (from `ip6tables -S` succeeding); null/absent until any report has
  // carried the field. When false, the server flags every "6"/"both"
  // rule partially_applied and the card shows the honest banner.
  ipv6_supported?: boolean | null;
  pending: FirewallPendingTest | null;
  history: FirewallPendingTest[];
}

// Mirrors peripherals.py's async_peripheral_overview() — reuses Home
// Assistant core's own USB discovery data (the same source that already
// auto-detects a Zigbee/Z-Wave USB stick), so this is available on any
// install where core itself can see the device, not just Supervisor ones.
export interface AssignedIntegration {
  entry_id: string;
  domain: string;
  title: string;
}

export interface PeripheralDevice {
  key: string;
  raw_name: string;
  tty_path: string;
  by_id_path: string | null;
  vid: string;
  pid: string;
  serial_number: string | null;
  assigned_integration: AssignedIntegration | null;
  ignored: boolean;
}

export interface PeripheralOverview {
  available: boolean;
  devices: PeripheralDevice[];
  total_count: number;
  unassigned_count: number;
}

// Mirrors store.py's SettingsData exactly — the same object backs both
// this Settings tab and the native "Configure" options-flow dialog.
export type AccessLevel = "owner_only" | "owner_and_admins";
export type MfaPolicy = "audit_only" | "auto_deactivate";

export interface HaSocSettings {
  audit_retention_days: number;
  audit_max_bytes: number;
  // Work item 3.3 (D-6): retention for resolved/dismissed detections and
  // findings, distinct from the audit log's own retention above.
  evidence_retention_days: number;
  scanner_enabled: boolean;
  scanner_network_checks_enabled: boolean;
  // D-12: device manufacturer and model strings are sent to NIST's NVD
  // only while this is on.
  nvd_lookups_enabled: boolean;
  // Secret fields come back masked ("[redacted]" when set, "" when unset);
  // the companion *_set booleans say whether one is configured. Send a new
  // value to change it; send nothing (or the placeholder) to leave it.
  nvd_api_key: string | null;
  nvd_api_key_set?: boolean;
  github_token?: string | null;
  github_token_set?: boolean;
  // Work item 3.0 (D-9): sparse per-rule threshold overrides; send only
  // the fields being changed and the server merges per field. Effective
  // values, secure defaults, and ranges come from fetchDetectionThresholds.
  // The old risk_learning_period_days setting was replaced by the two
  // per-rule learning_days parameters in here.
  detection_thresholds: Record<string, Record<string, number | boolean>>;
  access_level: AccessLevel;
  mfa_policy: MfaPolicy;
  mfa_grace_period_days: number;
  security_sources_enabled: Record<string, boolean>;
  // UniFi Network / Protect connections. Hosts + verify_ssl round-trip
  // plainly; the two API keys are secrets (masked like nvd/github above).
  unifi_network_host: string | null;
  unifi_network_api_key?: string | null;
  unifi_network_api_key_set?: boolean;
  unifi_network_verify_ssl: boolean;
  unifi_protect_host: string | null;
  unifi_protect_api_key?: string | null;
  unifi_protect_api_key_set?: boolean;
  unifi_protect_verify_ssl: boolean;
  // Pi-hole v6 connection (Network Security tab). Same host/verify_ssl/
  // masked-secret shape as the UniFi fields above; iot_cidr is plain.
  pihole_host: string | null;
  pihole_api_key?: string | null;
  pihole_api_key_set?: boolean;
  pihole_verify_ssl: boolean;
  pihole_iot_cidr: string | null;
}

// Mirrors integration_security.py's async_integration_security_overview().
// PROVENANCE, not safety — the view must never imply "safe to run".
export type IntegrationTier = "core" | "hacs" | "custom";

export interface IntegrationGithubSignals {
  stars: number | null;
  forks: number | null;
  archived: boolean;
  pushed_at: string | null;
  commit_verified: boolean | null;
  has_release: boolean | null;
  latest_release_tag: string | null;
  collected_at: string;
  error?: string;
}

export interface IntegrationSecurityRow {
  domain: string;
  name: string;
  tier: IntegrationTier;
  is_custom: boolean;
  quality_scale: string | null;
  integration_type: string | null;
  version: string | null;
  license_present: boolean | null;
  repo_url: string | null;
  flags: string[];
  scanner_findings: number;
  github: IntegrationGithubSignals | null;
}

export interface IntegrationSecurityOverview {
  github_configured: boolean;
  hacs_installed: boolean;
  hacs_source_introspectable: boolean;
  tier_counts: Record<IntegrationTier, number>;
  integrations: IntegrationSecurityRow[];
  refreshed_at: string | null;
}

// Mirrors containers.py's async_container_resources(). Per-container live
// CPU/memory (add-ons + Core + Supervisor) for spotting a crashing/starving
// container. Stat fields are null when the Supervisor doesn't report them.
export interface ContainerResource {
  slug: string;
  name: string;
  kind: "addon" | "core" | "supervisor";
  state: string | null;
  version: string | null;
  update_available: boolean;
  cpu_percent: number | null;
  memory_usage: number | null; // bytes
  memory_limit: number | null; // bytes
  memory_percent: number | null;
  network_rx: number | null;
  network_tx: number | null;
  blk_read: number | null;
  blk_write: number | null;
  flags: string[];
}

export interface ContainerResourceOverview {
  available: boolean;
  reason: string | null;
  containers: ContainerResource[];
  generated_at: string;
}

// Mirrors resource_watchdog.py. Watchdog = sustained-breach detection +
// per-container action (alert/restart/stop — add-ons only; Core/Supervisor
// are clamped to alert server-side). hard_limits = Docker caps applied by
// the Probe add-on (requires its Protection Mode disabled).
export type WatchdogAction = "alert" | "restart" | "stop";

export interface WatchdogOverride {
  cpu_percent?: number | null;
  memory_percent?: number | null;
  action?: WatchdogAction;
  enabled?: boolean;
}

export interface WatchdogHardLimit {
  memory_mb: number | null;
  cpus: number | null;
}

export interface WatchdogConfig {
  enabled: boolean;
  default_cpu_percent: number;
  default_memory_percent: number;
  default_action: WatchdogAction;
  sustained_samples: number;
  interval_seconds: number;
  overrides: Record<string, WatchdogOverride>;
  hard_limits: Record<string, WatchdogHardLimit>;
}

export interface WatchdogHistorySample {
  ts: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  memory_usage: number | null;
}

export interface WatchdogContainerState {
  breach_count: number;
  last_outcome: string | null;
  history: WatchdogHistorySample[];
}

export interface WatchdogHardLimitState {
  status: string; // applied | failed | denied | unknown
  detail: string | null;
  at: string;
}

export interface WatchdogStatus {
  config: WatchdogConfig;
  hard_limit_state: Record<string, WatchdogHardLimitState>;
  running: boolean;
  containers: Record<string, WatchdogContainerState>;
}

export interface WatchdogSetPayload {
  enabled?: boolean;
  default_cpu_percent?: number;
  default_memory_percent?: number;
  default_action?: WatchdogAction;
  sustained_samples?: number;
  interval_seconds?: number;
  override?: {
    slug: string;
    cpu_percent?: number | null;
    memory_percent?: number | null;
    action?: WatchdogAction;
    enabled?: boolean;
    clear?: boolean;
  };
  hard_limit?: { slug: string; memory_mb?: number | null; cpus?: number | null };
}

// Mirrors unifi.py's normalized contract. Every per-row field is nullable
// on purpose: the exact UniFi field names could not be verified against a
// live controller, so anything the console doesn't return comes through as
// null and renders "—" rather than a guessed value. See unifi.py's docstring.
export interface UniFiIntegrationMatch {
  domain: string;
  title: string;
  entry_id: string;
  state: string;
  healthy: boolean;
  failing: boolean;
}

export interface UniFiBandwidth {
  rx_bytes: number;
  tx_bytes: number;
  total_bytes: number;
}

export interface NetworkClientRow {
  name: string;
  ipv4: string | null;
  ipv6: string | null;
  mac: string | null;
  vlan: number | string | null;
  ssid: string | null;
  wired: boolean;
  uptime: number | null; // seconds
  bandwidth: UniFiBandwidth | null;
  last_seen: number | null; // epoch seconds
  integration_match: UniFiIntegrationMatch | null;
}

export interface NetworkDeviceRow extends NetworkClientRow {
  model: string | null;
  state: string | null;
  // Devices table drops IPv6/Uptime; firmware_updatable replaces uptime.
  firmware_updatable: boolean | null;
}

// Mirrors unifi.py's _normalize_acl_filter — one side (source or
// destination) of an ACL rule.
export interface AclFilter {
  match_type: string | null;
  ip_or_subnets: string[];
  ports: number[];
  networks: string[];
  macs: string[];
}

// Mirrors unifi.py's _normalize_acl_rule — an order-preserving ACL rule for
// the security-audit report, following the verified UniFi ACL Rule schema
// (action/protocolFilter/sourceFilter/destinationFilter). Field availability
// depends on the controller's Integration API version (see acl.available /
// endpoint).
export interface AclRule {
  order: number;
  id: string | null;
  name: string | null;
  // "IPV4" | "MAC" — which endpoint-filter shape sourceFilter/
  // destinationFilter use.
  rule_type: string | null;
  action: string | null;
  enabled: boolean | null;
  // metadata.origin verbatim ("USER_DEFINED" | "SYSTEM_DEFINED" |
  // "DERIVED"), plus the derived custom flag (true only for
  // USER_DEFINED; null when origin itself wasn't reported).
  origin: string | null;
  custom: boolean | null;
  protocols: string[];
  networks: string[];
  ports: number[];
  source: AclFilter;
  destination: AclFilter;
}

export interface AclReport {
  available: boolean;
  error: string | null;
  endpoint: string | null;
  endpoints_tried: string[];
  rules: AclRule[];
}

// Mirrors unifi.py's _normalize_firewall_traffic_filter — one side (source
// or destination) of a Firewall Policy. Genuinely richer than an ACL rule's
// filter: a required zone, plus an optional typed traffic filter narrowing
// it further (network/IP/MAC/port, or — destination only — domain/
// application/application category). REGION/VPN_SERVER/
// SITE_TO_SITE_VPN_TUNNEL/IPV6_IID filters are represented by filter_type
// alone (see unifi.py's docstring for why).
export interface FirewallTrafficFilter {
  zone: string | null;
  filter_type: string | null;
  networks: string[];
  ip_or_subnets: string[];
  macs: string[];
  domains: string[];
  applications: number[];
  application_categories: number[];
  match_opposite: boolean | null;
  ports: string[];
  ports_from_list: boolean;
}

// Mirrors unifi.py's _normalize_firewall_policy — one Firewall Policy, the
// zone-based default allow/deny mechanism UniFi shows by default (Settings
// -> Security -> Create Policy), genuinely separate from ACL Rules above.
export interface FirewallPolicy {
  order: number;
  id: string | null;
  name: string | null;
  description: string | null;
  enabled: boolean | null;
  action: string | null;
  // ALLOW-only: whether UniFi auto-creates a mirrored policy on the
  // reverse zone pair to allow the matching return traffic. null for
  // BLOCK/REJECT, where the field doesn't apply.
  allow_return_traffic: boolean | null;
  origin: string | null;
  custom: boolean | null;
  logging_enabled: boolean | null;
  ip_version: string | null;
  protocol: string | null;
  connection_state_filter: string[] | null;
  scheduled: boolean;
  networks: string[];
  ports: string[];
  source: FirewallTrafficFilter;
  destination: FirewallTrafficFilter;
}

export interface FirewallZone {
  id: string;
  name: string;
  networks: string[];
}

export interface FirewallPoliciesReport {
  available: boolean;
  error: string | null;
  rules: FirewallPolicy[];
  zones: FirewallZone[];
}

// Mirrors unifi.py's correlate_server_ports_with_rules — the HA server's
// own open ports cross-referenced against the ACL rules and Firewall
// Policies above.
export interface ServerPort {
  port: number;
  proto: string | null;
  address: string | null;
  process: string | null;
  covered_by: string[];
  network_scoped_by: string[];
  status: "covered" | "network_scoped" | "uncovered";
}

export interface ServerPortsReport {
  available: boolean;
  server_ips: string[];
  ports: ServerPort[];
}

export interface NetworkWan {
  port: string | null;
  up: boolean | null;
  rx_rate_bps: number | null;
  tx_rate_bps: number | null;
  ip: string | null;
}

export interface ProtectCamera {
  id: string | null;
  name: string;
  ip: string | null;
  mac: string | null;
  is_recording: boolean | null;
  last_ring: number | null; // epoch seconds
  channels: string[];
  channel_count: number;
  state: string | null;
  online: boolean | null;
  // Deep link into the Protect console, e.g.
  // https://192.168.30.2/protect/dashboard/devices/<id>
  link: string | null;
}

export interface ProtectEvent {
  id: string | null;
  type: string | null;
  smart_detect_types: string[];
  score: number | null;
  start: number | null; // epoch seconds
  end: number | null; // epoch seconds
  duration: number | null; // seconds
  thumbnail: boolean;
  thumbnail_link: string | null;
  license_plate: string | null;
  camera: string | null;
}

export interface ProtectStatus {
  configured: boolean;
  reachable: boolean;
  error: string | null;
  host: string | null;
  camera_count: number;
  cameras_online: number;
  cameras: ProtectCamera[];
  events: ProtectEvent[];
  events_error: string | null;
}

export interface NetworkOverview {
  configured: boolean;
  reachable: boolean;
  error: string | null;
  site_id: string | null;
  status: string;
  internet_connected: boolean | null;
  wan: NetworkWan;
  wireless_client_count: number;
  wired_client_count: number;
  total_client_count: number;
  clients_per_ssid: { ssid: string; count: number }[];
  clients: NetworkClientRow[];
  devices: NetworkDeviceRow[];
  acl: AclReport;
  firewall_policies: FirewallPoliciesReport;
  server_ports: ServerPortsReport;
  failing_endpoint_count: number;
  generated_at: string;
  protect: ProtectStatus;
}

// Mirrors pihole.py's async_pihole_overview().
export interface PiHoleGroup {
  id: number | null;
  name: string | null;
  enabled: boolean | null;
  comment: string | null;
}

export interface PiHoleClient {
  client: string | null;
  name: string | null;
  comment: string | null;
  group_ids: number[];
  group_names: string[];
  default_group_only: boolean;
}

export interface PiHoleSummary {
  total: number | null;
  blocked: number | null;
  percent_blocked: number | null;
  unique_domains: number | null;
}

export interface PiHoleOverview {
  configured: boolean;
  reachable: boolean;
  error: string | null;
  blocking_enabled: boolean | null;
  summary: PiHoleSummary | null;
  groups: PiHoleGroup[];
  clients: PiHoleClient[];
  iot_cidr: string | null;
  iot_clients_scoped: boolean | null;
  top_blocked_domains: { domain: string | null; count: number | null }[];
  recent_blocked: string[];
  generated_at: string;
}

// Mirrors network_security.py's build_findings().
export interface NetworkSecurityFinding {
  id: string;
  severity: string;
  category: string;
  title: string;
  detail: string;
}

// Mirrors network_security.py's async_network_security_overview().
export interface NetworkSecurityOverview {
  acl: AclReport;
  firewall_policies: FirewallPoliciesReport;
  server_ports: ServerPortsReport;
  unifi_reachable: boolean;
  unifi_error: string | null;
  pihole: PiHoleOverview;
  findings: NetworkSecurityFinding[];
  generated_at: string;
}

// Mirrors security_health.py's async_security_overview().
export interface SecurityEntityRow {
  entity_id: string;
  name: string | null;
  domain: string;
  // Null on a registry entity with no state object at all (work plan
  // item 4.5): its integration never loaded it. Such a row always has
  // problem true and reason "no state (integration not loaded)".
  state: string | null;
  device_class: string | null;
  problem: boolean;
  // Why problem is true: the problem state itself ("unavailable",
  // "unknown", "jammed") or the no-state explanation above; null on a
  // healthy row.
  reason: string | null;
  battery_entity_id: string | null;
  battery_level: number | null;
  low_battery: boolean;
  config_entry_id: string | null;
  platform: string | null;
}

export interface SecurityIntegrationRow {
  entry_id: string | null;
  domain: string;
  title: string | null;
  state: string | null;
  installed: boolean;
}

export interface SecurityOverview {
  entities: SecurityEntityRow[];
  integrations: SecurityIntegrationRow[];
  problem_count: number;
  low_battery_count: number;
  sources_enabled: Record<string, boolean>;
}

// Mirrors homeassistant/components/system_log's LogEntry.to_dict() exactly
// (name/message/level/source/timestamp/exception/count/first_occurred) —
// the same WARNING+ dedup buffer that backs Home Assistant's own
// Settings > System > Logs page (/config/logs). Called directly rather
// than proxied through ha_soc/* like every other command here: it's a
// genuine core command (system_log/list, admin-gated on its own), the
// same way HA's own frontend calls core commands directly without a
// per-integration passthrough — and the panel already gates all tab
// content on ha_soc/access/info before a Logs tab is ever reachable.
export interface HaLogEntry {
  name: string;
  message: string[];
  level: string;
  source: [string, number];
  timestamp: number;
  exception: string;
  count: number;
  first_occurred: number;
}

// Mirrors entity_remap.py's async_find_references()/async_apply_remap().
// Every reference item is honestly labeled editable/not — nothing implies a
// fix happened until an explicit apply call returns.
export type EntityRemapKind = "automation" | "script" | "scene" | "dashboard" | "helper" | "other";

export interface EntityRemapReferenceItem {
  kind: EntityRemapKind;
  id: string;
  name: string;
  editable: boolean;
  reason: string | null;
  template_only: boolean;
}

export interface EntityRemapReport {
  entity_id: string;
  automation: EntityRemapReferenceItem[];
  script: EntityRemapReferenceItem[];
  scene: EntityRemapReferenceItem[];
  dashboard: EntityRemapReferenceItem[];
  helper: EntityRemapReferenceItem[];
  other: EntityRemapReferenceItem[];
  total_count: number;
  editable_count: number;
  paths: { automation: string; script: string; scene: string };
}

export interface EntityRemapApplyResult {
  old_entity_id: string;
  new_entity_id: string;
  fixed: Record<EntityRemapKind, number>;
  errors: string[];
  // Pre-rewrite snapshot paths under .storage/ha_soc_remap/ (kept 30 days).
  // Optional so a response from an older backend still renders.
  backups?: string[];
}

export interface BrokenEntityReference {
  entity_id: string;
  referenced_by: { kind: string; name: string }[];
}

export interface AccessInfo {
  is_owner: boolean;
  access_level: AccessLevel;
  allowed: boolean;
}

export interface VersionInfo {
  version: string | null;
}

const ws = <T>(hass: HomeAssistant, msg: Record<string, unknown>) => hass.callWS<T>(msg);

export const fetchUsers = (hass: HomeAssistant) =>
  ws<{ users: HaSocUser[] }>(hass, { type: "ha_soc/users/list" }).then((r) => r.users);

export const fetchUserDetail = (hass: HomeAssistant, userId: string) =>
  ws(hass, { type: "ha_soc/users/detail", user_id: userId });

export const createUser = (
  hass: HomeAssistant,
  name: string,
  groupIds?: string[],
  localOnly?: boolean
) => ws(hass, { type: "ha_soc/users/create", name, group_ids: groupIds, local_only: localOnly });

export const updateUser = (hass: HomeAssistant, userId: string, changes: Record<string, unknown>) =>
  ws(hass, { type: "ha_soc/users/update", user_id: userId, ...changes });

export const deactivateUser = (hass: HomeAssistant, userId: string) =>
  ws(hass, { type: "ha_soc/users/deactivate", user_id: userId });

export const deleteUser = (hass: HomeAssistant, userId: string) =>
  ws(hass, { type: "ha_soc/users/delete", user_id: userId });

export const revokeToken = (hass: HomeAssistant, userId: string, tokenId: string) =>
  ws(hass, { type: "ha_soc/users/revoke_token", user_id: userId, token_id: tokenId });

export const revokeAllSessions = (hass: HomeAssistant, userId: string) =>
  ws<{ revoked: number }>(hass, { type: "ha_soc/users/revoke_all_sessions", user_id: userId });

// revoke_sessions defaults true server-side (work plan item 4.12):
// whoever held the old password must be signed out, or the reset changes
// nothing for an attacker with a live session. Long-lived tokens are
// spared either way. The client always sends the flag explicitly so the
// audit record reflects a deliberate choice, never a schema default.
export const setPassword = (
  hass: HomeAssistant,
  userId: string,
  password: string,
  revokeSessions: boolean
) =>
  ws<{ ok: boolean; sessions_revoked: number }>(hass, {
    type: "ha_soc/users/set_password",
    user_id: userId,
    password,
    revoke_sessions: revokeSessions,
  });

export const fetchLiveSessions = (hass: HomeAssistant) =>
  ws<{ sessions: Record<string, unknown>[] }>(hass, { type: "ha_soc/sessions/list" }).then(
    (r) => r.sessions
  );

export const queryAudit = (
  hass: HomeAssistant,
  params: { since?: string; until?: string; user_id?: string; category?: string; ip?: string; limit?: number } = {}
) => ws<{ events: AuditEvent[] }>(hass, { type: "ha_soc/audit/query", ...params }).then((r) => r.events);

export const verifyAuditChain = (hass: HomeAssistant) =>
  ws<{
    ok: boolean;
    records_checked: number;
    first_break_seq: number | null;
    // 1 when the whole chain was re-checked; greater when retention has
    // expired the prefix and verification restarted at the stored anchor.
    verified_from_seq: number;
    expired_through: string | null;
  }>(hass, {
    type: "ha_soc/audit/verify_chain",
  });

// Per-category record counts and byte shares for the newest audit day,
// so the owner can see what produces the log's bulk. Newest day only.
export interface AuditCategoryStat {
  category: string;
  records: number;
  bytes: number;
  byte_share: number;
}

export interface AuditCategoryStats {
  day: string | null;
  files: number;
  total_records: number;
  total_bytes: number;
  categories: AuditCategoryStat[];
}

export const fetchAuditCategoryStats = (hass: HomeAssistant) =>
  ws<AuditCategoryStats>(hass, { type: "ha_soc/audit/category_stats" });

export const fetchDashboards = (hass: HomeAssistant) =>
  ws<{ dashboards: Record<string, unknown>[] }>(hass, { type: "ha_soc/permissions/dashboards/list" }).then(
    (r) => r.dashboards
  );

export const fetchDashboardConfig = (hass: HomeAssistant, urlPath: string | null) =>
  ws<{ config: Record<string, unknown> }>(hass, {
    type: "ha_soc/permissions/dashboard_config",
    url_path: urlPath,
  }).then((r) => r.config);

export const setViewVisibility = (
  hass: HomeAssistant,
  urlPath: string | null,
  viewPath: string,
  userIds: string[]
) =>
  ws(hass, {
    type: "ha_soc/permissions/view_visibility/set",
    url_path: urlPath,
    view_path: viewPath,
    user_ids: userIds,
  });

export const setDashboardFlags = (
  hass: HomeAssistant,
  dashboardId: string,
  flags: { require_admin?: boolean; show_in_sidebar?: boolean }
) => ws(hass, { type: "ha_soc/permissions/dashboard_flags/set", dashboard_id: dashboardId, ...flags });

export const pushSidebarPolicy = (hass: HomeAssistant, userId: string, hiddenPaths: string[]) =>
  ws(hass, {
    type: "ha_soc/permissions/sidebar/push",
    user_id: userId,
    hidden_dashboard_paths: hiddenPaths,
  });

export const checkDrift = (hass: HomeAssistant) =>
  ws<{ drift: Record<string, unknown>[] }>(hass, { type: "ha_soc/permissions/drift/check" }).then(
    (r) => r.drift
  );

export const fetchRisk = (hass: HomeAssistant) =>
  ws<{ risk: Record<string, RiskResult> }>(hass, { type: "ha_soc/risk/list" }).then((r) => r.risk);

export const fetchPosture = (hass: HomeAssistant) =>
  ws<PostureResult>(hass, { type: "ha_soc/risk/posture" });

export const fetchDetections = (hass: HomeAssistant, status?: string) =>
  ws<{ detections: Detection[] }>(hass, { type: "ha_soc/detections/list", status }).then(
    (r) => r.detections
  );

export const setDetectionStatus = (hass: HomeAssistant, detectionId: string, status: string) =>
  ws(hass, { type: "ha_soc/detections/set_status", detection_id: detectionId, status });

// Work item 3.3: one action, one audit record carrying the id list.
export const bulkSetDetectionStatus = (hass: HomeAssistant, detectionIds: string[], status: string) =>
  ws<{ updated: number; missing: string[] }>(hass, {
    type: "ha_soc/detections/bulk_set_status",
    detection_ids: detectionIds,
    status,
  });

// Work item 3.0 (D-9): the tunable-threshold table. Per rule and
// parameter: the effective value, the secure default, the inclusive
// min/max (null for booleans), and the type the input should render as.
export interface DetectionThresholdParam {
  value: number | boolean;
  default: number | boolean;
  min: number | null;
  max: number | null;
  type: "int" | "float" | "bool";
}

export type DetectionThresholdTable = Record<string, Record<string, DetectionThresholdParam>>;

export const fetchDetectionThresholds = (hass: HomeAssistant) =>
  ws<{ rules: DetectionThresholdTable }>(hass, { type: "ha_soc/detections/thresholds" }).then(
    (r) => r.rules
  );

// Owner-only, audited with a per-field diff server-side.
export const resetDetectionThresholds = (hass: HomeAssistant) =>
  ws<{ rules: DetectionThresholdTable }>(hass, { type: "ha_soc/detections/thresholds_reset" }).then(
    (r) => r.rules
  );

export const fetchVulns = (hass: HomeAssistant) =>
  ws<{ findings: Finding[] }>(hass, { type: "ha_soc/vulns/list" }).then((r) => r.findings);

export const fetchSystemLog = (hass: HomeAssistant) => ws<HaLogEntry[]>(hass, { type: "system_log/list" });

// Mirrors logs.py's async_fault_log_overview() — home-assistant.log.fault,
// Python's faulthandler dump, only ever non-empty after a genuine fatal
// (segfault-class) crash, never a normal Python exception.
export interface FaultLogOverview {
  exists: boolean;
  content: string | null;
  size_bytes: number;
  modified_at: string | null;
  truncated: boolean;
}

export const fetchFaultLog = (hass: HomeAssistant) =>
  ws<FaultLogOverview>(hass, { type: "ha_soc/logs/fault" });

// Container (app/add-on) logs, served by the Supervisor's journald gateway
// through logs.py. available=false on a non-Supervisor install, in which case
// the Logs tab simply doesn't offer the selector.
export interface ContainerLogTarget {
  id: string; // "core" | "supervisor" | "host" | "addon:<slug>"
  name: string;
}

export interface ContainerLogTargets {
  available: boolean;
  targets: ContainerLogTarget[];
}

export interface ContainerLog {
  available: boolean;
  target: string;
  content: string | null;
  truncated: boolean;
  error: string | null;
  fetched_at: string;
}

export const fetchLogTargets = (hass: HomeAssistant) =>
  ws<ContainerLogTargets>(hass, { type: "ha_soc/logs/targets" });

export const fetchContainerLog = (hass: HomeAssistant, target: string) =>
  ws<ContainerLog>(hass, { type: "ha_soc/logs/container", target });

// Real core command, called directly for the same reason fetchSystemLog is:
// a genuine, already-admin-gated core command, not something worth proxying
// through ha_soc/* just to relabel it.
export interface EntityRegistryEntry {
  entity_id: string;
  name: string | null;
  original_name: string | null;
  platform: string;
  disabled_by: string | null;
}

export const fetchEntityRegistry = (hass: HomeAssistant) =>
  ws<EntityRegistryEntry[]>(hass, { type: "config/entity_registry/list" });

export const scanVulnsNow = (hass: HomeAssistant) =>
  ws<{ findings: Finding[] }>(hass, { type: "ha_soc/vulns/scan_now" }).then((r) => r.findings);

export const setVulnStatus = (hass: HomeAssistant, findingId: string, status: string, note?: string) =>
  ws(hass, { type: "ha_soc/vulns/set_status", finding_id: findingId, status, note });

// Mirrors scanner.py's scan_directory_report coverage record: what one
// completed pass over a domain really looked at (work plan item 4.8). A
// domain with no record has never been scanned and must render as "not
// scanned", never as an implied-clean zero findings.
export interface ScannerDomainCoverage {
  scanned_files: number;
  skipped_oversize: number;
  skipped_over_cap: number;
  parse_failures: number;
  scanned_at: string;
}

// Mirrors IntegrationScanner.listing_payload. coverage is optional so a
// backend still serving the pre-coverage findings-only payload parses;
// its absence renders the same way as an empty table: nothing scanned.
export interface ScannerListing {
  findings: Finding[];
  coverage?: Record<string, ScannerDomainCoverage>;
}

export const fetchScannerListing = (hass: HomeAssistant) =>
  ws<ScannerListing>(hass, { type: "ha_soc/scanner/list" });

export const scanIntegrationNow = (hass: HomeAssistant, domain?: string) =>
  ws(hass, { type: "ha_soc/scanner/scan_now", domain });

export const exportFinding = (hass: HomeAssistant, findingId: string) =>
  ws(hass, { type: "ha_soc/scanner/export", finding_id: findingId });

export const fetchHealth = (hass: HomeAssistant) =>
  ws<{ integrations: Record<string, unknown>[]; misconfig_findings: Finding[] }>(hass, {
    type: "ha_soc/health/list",
  });

export const setMisconfigStatus = (hass: HomeAssistant, findingId: string, status: string, note?: string) =>
  ws(hass, { type: "ha_soc/misconfig/set_status", finding_id: findingId, status, note });

export const fetchDashboardSummary = (hass: HomeAssistant) =>
  ws<DashboardSummary>(hass, { type: "ha_soc/dashboard/summary" });

export const fetchDashboardDevices = (hass: HomeAssistant) =>
  ws<DeviceOverview>(hass, { type: "ha_soc/dashboard/devices" });

export const fetchDashboardIntegrations = (hass: HomeAssistant) =>
  ws<IntegrationOverview>(hass, { type: "ha_soc/dashboard/integrations" });

export const fetchAccessInfo = (hass: HomeAssistant) =>
  ws<AccessInfo>(hass, { type: "ha_soc/access/info" });

export const fetchVersion = (hass: HomeAssistant) => ws<VersionInfo>(hass, { type: "ha_soc/version/get" });

export const fetchProbeStatus = (hass: HomeAssistant) =>
  ws<ProbeOverview>(hass, { type: "ha_soc/probe/status" });

export const fetchFirewallStatus = (hass: HomeAssistant) =>
  ws<FirewallStatus>(hass, { type: "ha_soc/firewall/status" });

export const proposeFirewallTest = (hass: HomeAssistant, rules: FirewallRule[], backupAcknowledged: boolean) =>
  ws<FirewallPendingTest>(hass, {
    type: "ha_soc/firewall/test",
    rules,
    backup_acknowledged: backupAcknowledged,
  });

export const confirmFirewallTest = (hass: HomeAssistant, testId: string) =>
  ws<{ ok: boolean }>(hass, { type: "ha_soc/firewall/confirm", test_id: testId });

export const cancelFirewallTest = (hass: HomeAssistant, testId: string) =>
  ws<{ ok: boolean }>(hass, { type: "ha_soc/firewall/cancel", test_id: testId });

// Owner-only escape hatch for an add-on gone silent mid-test: archives the
// pending record as discarded_unreported and clears the slot. The server
// refuses it while the countdown is still running, so the panel only
// offers the button once the countdown has lapsed.
export const discardFirewallPending = (hass: HomeAssistant) =>
  ws<{ ok: boolean }>(hass, { type: "ha_soc/firewall/discard_pending" });

export const fetchIntegrationSecurity = (hass: HomeAssistant) =>
  ws<IntegrationSecurityOverview>(hass, { type: "ha_soc/integration_security/list" });

// Mirrors github_provenance.py's async_refresh_github_signals summary.
// reason is "no_github_token" (nothing ran) or "rate_limited" (the loop
// stopped early, keeping what it had fetched). invalid_slugs is a COUNT
// of malformed owner/repo slugs refused a request, not a list; the slug
// strings themselves go to the server log only. cache_fresh counts repos
// skipped because their cached signals are younger than the TTL. The
// three count fields are absent on the no_github_token early return.
export const refreshIntegrationSecurity = (hass: HomeAssistant) =>
  ws<{
    ok: boolean;
    reason?: string;
    refreshed?: number;
    skipped?: number;
    cache_fresh?: number;
    invalid_slugs?: number;
  }>(hass, {
    type: "ha_soc/integration_security/refresh",
  });

export const fetchContainerResources = (hass: HomeAssistant) =>
  ws<ContainerResourceOverview>(hass, { type: "ha_soc/containers/resources" });

export const fetchWatchdogStatus = (hass: HomeAssistant) =>
  ws<WatchdogStatus>(hass, { type: "ha_soc/watchdog/status" });

export const setWatchdog = (hass: HomeAssistant, changes: WatchdogSetPayload) =>
  ws<WatchdogStatus>(hass, { type: "ha_soc/watchdog/set", ...changes });

export const fetchPeripherals = (hass: HomeAssistant) =>
  ws<PeripheralOverview>(hass, { type: "ha_soc/peripherals/list" });

export const setPeripheralIgnored = (hass: HomeAssistant, key: string, ignored: boolean, rawName: string) =>
  ws(hass, { type: "ha_soc/peripherals/set_ignored", key, ignored, raw_name: rawName });

export const findEntityRemapReferences = (hass: HomeAssistant, entityId: string) =>
  ws<EntityRemapReport>(hass, { type: "ha_soc/entity_remap/find_references", entity_id: entityId });

// backup_acknowledged is vol.Required server-side; omitting it made every
// apply fail schema validation, so the whole feature was unreachable from
// the panel (work plan item 0.4, UI-1). tests/test_ws_contract.py now
// guards this whole class of missing-required-key bug.
export const applyEntityRemap = (
  hass: HomeAssistant,
  oldEntityId: string,
  newEntityId: string,
  backupAcknowledged: boolean
) =>
  ws<EntityRemapApplyResult>(hass, {
    type: "ha_soc/entity_remap/apply",
    old_entity_id: oldEntityId,
    new_entity_id: newEntityId,
    backup_acknowledged: backupAcknowledged,
  });

export const fetchBrokenEntityReferences = (hass: HomeAssistant) =>
  ws<{ broken: BrokenEntityReference[] }>(hass, { type: "ha_soc/entity_remap/broken_references" }).then(
    (r) => r.broken
  );

export const fetchSecurityHealth = (hass: HomeAssistant) =>
  ws<SecurityOverview>(hass, { type: "ha_soc/security_health/list" });

export const fetchNetworkOverview = (hass: HomeAssistant) =>
  ws<NetworkOverview>(hass, { type: "ha_soc/network/overview" });

export const fetchNetworkSecurityOverview = (hass: HomeAssistant) =>
  ws<NetworkSecurityOverview>(hass, { type: "ha_soc/network_security/overview" });

export const fetchSettings = (hass: HomeAssistant) =>
  ws<HaSocSettings>(hass, { type: "ha_soc/settings/get" });

export const updateSettings = (hass: HomeAssistant, changes: Partial<HaSocSettings>) =>
  ws<HaSocSettings>(hass, { type: "ha_soc/settings/set", ...changes });

export const subscribeTopic = (
  hass: HomeAssistant,
  topic: string,
  callback: () => void
): Promise<() => Promise<void>> =>
  hass.connection.subscribeMessage<Record<string, unknown>>(() => callback(), {
    type: "ha_soc/subscribe",
    topic,
  });
