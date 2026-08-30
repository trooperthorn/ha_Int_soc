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
}

export interface RiskFactor {
  name: string;
  points: number;
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

export interface FirewallRule {
  action: FirewallRuleAction;
  proto: FirewallRuleProto;
  port: number;
  source?: string | null;
}

// "expired_unreported" is the display-only status a timed-out pending test
// carries until the add-on's own report archives it; "expired" is the same
// state's pre-rename spelling, kept so a record persisted by an older
// version still type-checks.
export type FirewallTestStatus = "testing" | "confirmed" | "reverted" | "expired" | "expired_unreported";

export interface FirewallPendingTest {
  test_id: string;
  proposed_rules: FirewallRule[];
  status: FirewallTestStatus;
  requested_by: string;
  requested_at: string;
  // null until the add-on's poll actually picks this up and applies it —
  // still "testing" but not live on the host yet.
  applied_at: string | null;
  expires_at: string;
  window_seconds: number;
  resolved_at?: string;
  resolved_by?: string;
}

export interface FirewallStatus {
  known_rules: FirewallRule[] | null;
  known_rules_reported_at: string | null;
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
  scanner_enabled: boolean;
  scanner_network_checks_enabled: boolean;
  // Secret fields come back masked ("[redacted]" when set, "" when unset);
  // the companion *_set booleans say whether one is configured. Send a new
  // value to change it; send nothing (or the placeholder) to leave it.
  nvd_api_key: string | null;
  nvd_api_key_set?: boolean;
  github_token?: string | null;
  github_token_set?: boolean;
  risk_learning_period_days: number;
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

// Mirrors unifi.py's _normalize_acl_rule — an order-preserving ACL/firewall
// rule for the security-audit report. Field availability depends on the
// controller's Integration API version (see acl.available / endpoint).
export interface AclRule {
  order: number;
  id: string | null;
  name: string | null;
  action: string | null;
  enabled: boolean | null;
  direction: string | null;
  protocol: string | null;
  source: string | null;
  destination: string | null;
  networks: string[];
}

export interface AclReport {
  available: boolean;
  error: string | null;
  endpoint: string | null;
  endpoints_tried: string[];
  rules: AclRule[];
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
  failing_endpoint_count: number;
  generated_at: string;
  protect: ProtectStatus;
}

// Mirrors security_health.py's async_security_overview().
export interface SecurityEntityRow {
  entity_id: string;
  name: string | null;
  domain: string;
  state: string;
  device_class: string | null;
  problem: boolean;
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

export const setPassword = (hass: HomeAssistant, userId: string, password: string) =>
  ws(hass, { type: "ha_soc/users/set_password", user_id: userId, password });

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

export const fetchScannerFindings = (hass: HomeAssistant) =>
  ws<{ findings: Finding[] }>(hass, { type: "ha_soc/scanner/list" }).then((r) => r.findings);

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

export const fetchIntegrationSecurity = (hass: HomeAssistant) =>
  ws<IntegrationSecurityOverview>(hass, { type: "ha_soc/integration_security/list" });

export const refreshIntegrationSecurity = (hass: HomeAssistant) =>
  ws<{ ok: boolean; reason?: string; refreshed?: number; skipped?: number }>(hass, {
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
