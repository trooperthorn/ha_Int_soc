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
// collection). An integration with none of these doesn't appear at all.
export type IntegrationIssueCategory = "credential" | "failing" | "communication" | "collection";

export interface IntegrationIssueRow {
  entry_id: string;
  domain: string;
  title: string;
  state: string;
  reason: string | null;
  error_count_24h: number;
  unavailable_ratio: number;
  retry_transitions_24h: number;
  issue_category: IntegrationIssueCategory;
}

export interface IntegrationOverview {
  integrations: IntegrationIssueRow[];
  category_counts: Record<IntegrationIssueCategory, number>;
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
  nvd_api_key: string | null;
  risk_learning_period_days: number;
  access_level: AccessLevel;
  mfa_policy: MfaPolicy;
  mfa_grace_period_days: number;
}

export interface AccessInfo {
  is_owner: boolean;
  access_level: AccessLevel;
  allowed: boolean;
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
  ws<{ ok: boolean; records_checked: number; first_break_seq: number | null }>(hass, {
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
