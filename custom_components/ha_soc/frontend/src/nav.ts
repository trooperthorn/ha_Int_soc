/** Cross-view navigation: any view can ask the panel to switch tabs by
 * dispatching this bubbling, composed event — it crosses shadow DOM
 * boundaries up to <ha-soc-panel>, which owns the actual tab state. */
export type SocTab =
  | "dashboard"
  | "network"
  | "users"
  | "audit"
  | "permissions"
  | "scanner"
  | "logs"
  | "peripherals"
  | "entity_remap"
  | "integration_security"
  | "settings";

export const HA_SOC_NAVIGATE = "ha-soc-navigate";

export interface HaSocNavigateDetail {
  tab: SocTab;
}

export function navigate(el: HTMLElement, tab: SocTab): void {
  el.dispatchEvent(
    new CustomEvent<HaSocNavigateDetail>(HA_SOC_NAVIGATE, {
      detail: { tab },
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
