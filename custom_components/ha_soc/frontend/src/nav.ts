/** Cross-view navigation: any view can ask the panel to switch tabs by
 * dispatching this bubbling, composed event — it crosses shadow DOM
 * boundaries up to <ha-soc-panel>, which owns the actual tab state. */
export type SocTab =
  | "dashboard"
  | "network"
  | "network_security"
  | "users"
  | "audit"
  | "permissions"
  | "scanner"
  | "logs"
  | "peripherals"
  | "entity_remap"
  | "integration_security"
  | "settings";

export type SocWorkspace = "overview" | "assets" | "findings" | "identity" | "siem" | "settings";

export interface SocWorkspaceDefinition {
  id: SocWorkspace;
  label: string;
  defaultTab: SocTab;
  ownerOnly?: boolean;
  tabs: { id: SocTab; label: string }[];
}

/**
 * The console's stable information architecture. The leaf tab ids remain
 * unchanged so stored per-view layouts, cross-view navigation events, and
 * backend authorization contracts do not migrate or lose state. Only the
 * shell presentation changes: related tools are grouped into six workspaces
 * instead of competing in one long horizontal list.
 */
export const SOC_WORKSPACES: SocWorkspaceDefinition[] = [
  {
    id: "overview",
    label: "Overview",
    defaultTab: "dashboard",
    tabs: [{ id: "dashboard", label: "Security Overview" }],
  },
  {
    id: "assets",
    label: "Assets",
    defaultTab: "network",
    tabs: [
      { id: "network", label: "Network" },
      { id: "peripherals", label: "Local Peripherals" },
      { id: "entity_remap", label: "Entity ReMap" },
      { id: "integration_security", label: "Integration Security" },
    ],
  },
  {
    id: "findings",
    label: "Findings",
    defaultTab: "scanner",
    tabs: [
      { id: "scanner", label: "Vulnerability Scanner" },
      { id: "network_security", label: "Network Security" },
    ],
  },
  {
    id: "identity",
    label: "Identity",
    defaultTab: "users",
    tabs: [
      { id: "users", label: "Users & Access" },
      { id: "permissions", label: "Permissions" },
    ],
  },
  {
    id: "siem",
    label: "SIEM & Audit",
    defaultTab: "audit",
    tabs: [
      { id: "audit", label: "Audit Log" },
      { id: "logs", label: "Logs" },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    defaultTab: "settings",
    ownerOnly: true,
    tabs: [{ id: "settings", label: "Security Settings" }],
  },
];

export function workspaceForTab(tab: SocTab): SocWorkspaceDefinition {
  return SOC_WORKSPACES.find((workspace) => workspace.tabs.some((item) => item.id === tab)) ?? SOC_WORKSPACES[0];
}

export function labelForTab(tab: SocTab): string {
  for (const workspace of SOC_WORKSPACES) {
    const item = workspace.tabs.find((candidate) => candidate.id === tab);
    if (item) return item.label;
  }
  return "Security Overview";
}

export const HA_SOC_NAVIGATE = "ha-soc-navigate";

export interface HaSocNavigateDetail {
  tab: SocTab;
  // Pre-fills the target tab's own search/filter box (currently only the
  // Network tab's Clients table search consumes this) so "jump from a
  // rule's resolved device to that device on the Network tab" lands
  // already filtered to it, not just on the tab.
  clientFilter?: string;
}

export function navigate(el: HTMLElement, tab: SocTab, clientFilter?: string): void {
  el.dispatchEvent(
    new CustomEvent<HaSocNavigateDetail>(HA_SOC_NAVIGATE, {
      detail: clientFilter ? { tab, clientFilter } : { tab },
      bubbles: true,
      composed: true,
    })
  );
}

/**
 * Navigate elsewhere in Home Assistant's own frontend (e.g. its native
 * Devices dashboard) without a full page reload. A custom panel's JS
 * module runs in the same document as core frontend (confirmed against
 * home-assistant/frontend source: `mainWindow` resolves to `window` itself
 * for a non-iframe panel_custom), so pushing history state and firing the
 * `location-changed` event core's own router listens for is the standard,
 * documented pattern third-party panels/cards use to navigate the app's
 * router — the same thing `history.back()`-aware core links do internally.
 *
 * Only call this with URLs verified to actually support what you're
 * relying on. Confirmed against source: `/config/devices/dashboard`
 * accepts `?config_entry=<id>` and `?domain=<domain>` as real pre-applied
 * filters. It does NOT support any availability/state filter — devices
 * have no "state" concept in that table at all, only disabled/enabled —
 * and the entities dashboard's status filter cannot be preset via URL
 * either (UI-click + sessionStorage only). Don't construct a URL implying
 * either of those unless that changes upstream.
 */
export function navigateToHaPath(path: string): void {
  window.history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
}

export function deviceDetailPath(deviceId: string): string {
  return `/config/devices/device/${deviceId}`;
}

export function devicesForIntegrationPath(configEntryId: string): string {
  return `/config/devices/dashboard?historyBack=1&config_entry=${configEntryId}`;
}

export function devicesForDomainPath(domain: string): string {
  return `/config/devices/dashboard?historyBack=1&domain=${domain}`;
}
