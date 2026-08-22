/** Cross-view navigation: any view can ask the panel to switch tabs by
 * dispatching this bubbling, composed event — it crosses shadow DOM
 * boundaries up to <ha-soc-panel>, which owns the actual tab state. */
export type SocTab = "dashboard" | "users" | "audit" | "permissions" | "scanner";

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
