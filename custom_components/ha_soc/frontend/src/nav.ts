/** Cross-view navigation: a bubbling, composed event that crosses shadow DOM up to <ha-soc-panel>, which owns tab state. */
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
 * The console's information architecture. Leaf tab ids are stable: stored
 * layouts, navigation events, and backend authorization key on them.
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
  // Pre-fills the target tab's search box (only the Network tab's Clients table consumes it).
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
 * Navigate elsewhere in Home Assistant's own frontend without a full page
 * reload, by pushing `history` state and firing the `location-changed` event
 * core's router listens for (`mainWindow` is `window` for a non-iframe
 * panel_custom). Only `/config/devices/dashboard` with `?config_entry=<id>`
 * or `?domain=<domain>` is verified; no availability/state filter exists via
 * URL, see docs/design.md.
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
