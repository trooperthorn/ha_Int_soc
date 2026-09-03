import type { HomeAssistant } from "../types";
import type { LayoutState } from "../customize";

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
  // False when no credential comes from the homeassistant auth provider; the Users view renders "MFA not assessable".
  mfa_assessable: boolean;
}

export interface RiskFactor {
  name: string;
  // Pre-clamp contribution; applied_points is the post-clamp share, optional for older backends. See docs/protocol.md.
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
  // Provisional until every posture term has computed from real data at least once; see docs/protocol.md.
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

// Mirrors vulns.py's DEVICE_STATUS_*: live availability, a separate axis from severity.
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

// Mirrors health.py's ISSUE_CATEGORY_*: at most one category per integration, priority-ordered.
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

// Mirrors probe.py's async_probe_overview(): a three-way answer, never silently-empty data.
export interface OpenPort {
  port: number;
  proto: "tcp" | "udp";
  process?: string | null;
  // Absent/null from an older add-on, or when the bind address is IPv6 (not decoded, see run.sh).
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

// Mirrors firewall.py's RULE_SCHEMA / pending-test state machine; the add-on's report (known_rules) is the final word.
export type FirewallRuleAction = "allow" | "deny";
export type FirewallRuleProto = "tcp" | "udp";
// Address family a rule targets; the server derives it from the source address and rejects a contradiction.
export type FirewallRuleFamily = "4" | "6" | "both";

export interface FirewallRule {
  action: FirewallRuleAction;
  proto: FirewallRuleProto;
  port: number;
  source?: string | null;
  // Optional: records persisted before the dual-stack change carry no family; absent means "both".
  family?: FirewallRuleFamily;
  // Set by the server at read time on every "6"/"both" rule while the add-on reports ipv6_supported=false.
  partially_applied?: boolean;
}

// "expired" is the pre-rename spelling of "expired_unreported"; "discarded_unreported" appears only on history entries.
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
  // null until the add-on's poll applies it; still "testing" but not live on the host yet.
  applied_at: string | null;
  // Propose time plus window until applied_at is set, then re-anchored to applied_at plus window_seconds.
  expires_at: string;
  window_seconds: number;
  resolved_at?: string;
  resolved_by?: string;
  // The add-on's bounded reason for a resolution; only present on archived history records.
  reason?: string | null;
}

export interface FirewallStatus {
  known_rules: FirewallRule[] | null;
  known_rules_reported_at: string | null;
  // Whether ip6tables works on the host per the add-on's last report (`ip6tables -S`); null until a report carried it.
  ipv6_supported?: boolean | null;
  pending: FirewallPendingTest | null;
  history: FirewallPendingTest[];
}

// Mirrors peripherals.py's async_peripheral_overview(), built on core's own USB discovery data.
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

// Mirrors store.py's SettingsData exactly; the same object backs the native options-flow dialog.
export type AccessLevel = "owner_only" | "owner_and_admins";
export type MfaPolicy = "audit_only" | "auto_deactivate";
export type SyslogTransport = "disabled" | "udp" | "tcp" | "tls";
export type SyslogPayloadFormat = "rfc5424_json" | "cef" | "raw_json";

export interface HaSocSettings {
  audit_retention_days: number;
  audit_max_bytes: number;
  syslog_transport: SyslogTransport;
  syslog_format: SyslogPayloadFormat;
  syslog_host: string | null;
  syslog_port: number;
  syslog_tls_verify: boolean;
  syslog_facility: number;
  syslog_status?: {
    enabled: boolean;
    transport: SyslogTransport;
    format: SyslogPayloadFormat;
    host_configured: boolean;
    connected: boolean;
    queued: number;
    sent: number;
    dropped: number;
    last_sent_at: string | null;
    last_error: string | null;
  };
  // Retention for resolved/dismissed detections and findings, distinct from audit retention.
  evidence_retention_days: number;
  scanner_enabled: boolean;
  scanner_network_checks_enabled: boolean;
  // Device manufacturer and model strings go to NIST's NVD only while this is on.
  nvd_lookups_enabled: boolean;
  // Secrets come back masked ("[redacted]" or ""); send a new value to change one, nothing or the placeholder to leave it.
  nvd_api_key: string | null;
  nvd_api_key_set?: boolean;
  github_token?: string | null;
  github_token_set?: boolean;
  // Sparse per-rule threshold overrides: send only the changed fields, the server merges per field.
  detection_thresholds: Record<string, Record<string, number | boolean>>;
  access_level: AccessLevel;
  mfa_policy: MfaPolicy;
  mfa_grace_period_days: number;
  security_sources_enabled: Record<string, boolean>;
  // UniFi Network / Protect connections; the API keys are masked secrets like nvd/github above.
  unifi_network_host: string | null;
  unifi_network_api_key?: string | null;
  unifi_network_api_key_set?: boolean;
  unifi_network_verify_ssl: boolean;
  unifi_protect_host: string | null;
  unifi_protect_api_key?: string | null;
  unifi_protect_api_key_set?: boolean;
  unifi_protect_verify_ssl: boolean;
  // Pi-hole v6 connection; same host/verify_ssl/masked-secret shape as UniFi.
  pihole_host: string | null;
  pihole_api_key?: string | null;
  pihole_api_key_set?: boolean;
  pihole_verify_ssl: boolean;
  pihole_iot_cidr: string | null;
  // Optional Probe-hosted SNMPv3 AuthPriv listener; passphrases are masked and never returned.
  snmp_enabled: boolean;
  snmp_listen_address: string | null;
  snmp_port: number;
  snmp_username: string | null;
  snmp_auth_passphrase?: string | null;
  snmp_auth_passphrase_set?: boolean;
  snmp_priv_passphrase?: string | null;
  snmp_priv_passphrase_set?: boolean;
  snmp_status?: {
    enabled: boolean;
    running: boolean;
    generation?: string | null;
    listen_address?: string | null;
    port?: number | null;
    error?: string | null;
    reported_at?: string;
  } | null;
}

// Mirrors integration_security.py's async_integration_security_overview(): provenance, not safety.
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

// Mirrors containers.py's async_container_resources(); stat fields are null when the Supervisor omits them.
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

// Mirrors resource_watchdog.py; see docs/RESOURCE-WATCHDOG.md.
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

// Mirrors unifi.py's normalized contract; every per-row field is nullable and renders as a dash when absent.
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

// Mirrors unifi.py's _normalize_acl_filter: one side of an ACL rule.
export interface AclFilter {
  match_type: string | null;
  ip_or_subnets: string[];
  ports: number[];
  networks: string[];
  macs: string[];
}

// Mirrors unifi.py's _normalize_acl_rule; field availability depends on the controller's Integration API version.
export interface AclRule {
  order: number;
  id: string | null;
  name: string | null;
  // "IPV4" | "MAC": the endpoint-filter shape sourceFilter/destinationFilter use.
  rule_type: string | null;
  action: string | null;
  enabled: boolean | null;
  // metadata.origin verbatim, plus derived custom (true only for USER_DEFINED; null when origin was not reported).
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

// Mirrors unifi.py's _normalize_firewall_traffic_filter: one side of a Firewall Policy. See docs/protocol.md.
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

// Mirrors unifi.py's _normalize_firewall_policy: one zone-based Firewall Policy, separate from ACL Rules.
export interface FirewallPolicy {
  order: number;
  id: string | null;
  name: string | null;
  description: string | null;
  enabled: boolean | null;
  action: string | null;
  // ALLOW-only: whether UniFi auto-creates the mirrored return-traffic policy; null for BLOCK/REJECT.
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

// Mirrors unifi.py's correlate_server_ports_with_rules.
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
  // Deep link into the Protect console (https://<host>/protect/dashboard/devices/<id>).
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

// Mirrors network_security.py's _client_summaries(): a lightweight projection of the Network tab's client rows.
export interface NetworkSecurityClient {
  name: string | null;
  ipv4: string | null;
  ipv6: string | null;
  mac: string | null;
  vlan: string | number | null;
}

// Mirrors network_security.py's async_network_security_overview().
export interface NetworkSecurityOverview {
  acl: AclReport;
  firewall_policies: FirewallPoliciesReport;
  server_ports: ServerPortsReport;
  clients: NetworkSecurityClient[];
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
  // Null on a registry entity with no state object; such a row has problem true and reason "no state (integration not loaded)".
  state: string | null;
  device_class: string | null;
  problem: boolean;
  // Why problem is true: the problem state or the no-state explanation; null on a healthy row.
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

// Mirrors system_log's LogEntry.to_dict() exactly; a genuine core command, so called directly rather than proxied.
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

// Mirrors entity_remap.py's async_find_references()/async_apply_remap(); nothing implies a fix until apply returns.
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
  // Pre-rewrite snapshot paths under .storage/ha_soc_remap/ (kept 30 days); optional for older backends.
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

// revoke_sessions defaults true server-side; the client always sends it explicitly so the audit record reflects a choice.
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
    // 1 when the whole chain was re-checked; greater when verification restarted at the retention anchor.
    verified_from_seq: number;
    expired_through: string | null;
  }>(hass, {
    type: "ha_soc/audit/verify_chain",
  });

// Per-category record counts and byte shares for the newest audit day only.
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

// One action, one audit record carrying the id list.
export const bulkSetDetectionStatus = (hass: HomeAssistant, detectionIds: string[], status: string) =>
  ws<{ updated: number; missing: string[] }>(hass, {
    type: "ha_soc/detections/bulk_set_status",
    detection_ids: detectionIds,
    status,
  });

// Tunable-threshold table: effective value, secure default, inclusive min/max (null for booleans), input type.
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

// Mirrors logs.py's async_fault_log_overview(): the faulthandler dump, non-empty only after a fatal crash.
export interface FaultLogOverview {
  exists: boolean;
  content: string | null;
  size_bytes: number;
  modified_at: string | null;
  truncated: boolean;
}

export const fetchFaultLog = (hass: HomeAssistant) =>
  ws<FaultLogOverview>(hass, { type: "ha_soc/logs/fault" });

// Container logs via the Supervisor's journald gateway; available=false on a non-Supervisor install.
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

// Real core command, called directly for the same reason fetchSystemLog is.
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

// Mirrors scanner.py's coverage record; a domain with no record renders "not scanned", never zero findings.
export interface ScannerDomainCoverage {
  scanned_files: number;
  skipped_oversize: number;
  skipped_over_cap: number;
  parse_failures: number;
  scanned_at: string;
}

// Mirrors IntegrationScanner.listing_payload; coverage is optional so a pre-coverage backend still parses.
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

// Owner-only discard of a pending test after the add-on went silent; the server refuses it while the countdown runs.
export const discardFirewallPending = (hass: HomeAssistant) =>
  ws<{ ok: boolean }>(hass, { type: "ha_soc/firewall/discard_pending" });

export const fetchIntegrationSecurity = (hass: HomeAssistant) =>
  ws<IntegrationSecurityOverview>(hass, { type: "ha_soc/integration_security/list" });

// Mirrors github_provenance.py's refresh summary; see docs/protocol.md for the reason and count fields.
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

// backup_acknowledged is vol.Required server-side.
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

// The calling user's own "Customize" layout for one view, never another user's.
export const fetchLayout = (hass: HomeAssistant, viewId: string) =>
  ws<LayoutState>(hass, { type: "ha_soc/layout/get", view_id: viewId });

export const saveLayout = (hass: HomeAssistant, viewId: string, layout: LayoutState) =>
  ws<LayoutState>(hass, {
    type: "ha_soc/layout/set",
    view_id: viewId,
    order: layout.order,
    hidden: layout.hidden,
  });

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
