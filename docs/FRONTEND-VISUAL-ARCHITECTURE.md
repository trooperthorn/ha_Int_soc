# HA SOC frontend visual architecture

## Decision

HA SOC uses a hybrid presentation model:

1. The integration-owned panel is the protected security console. Detailed
   assets, findings, identities, audit records, evidence, and mutations remain
   behind HA SOC's server-side WebSocket authorization gates.
2. Home Assistant dashboards may consume a deliberately small set of aggregate
   entities for optional summary views. Lovelace visibility is presentation,
   not authorization, so detailed security data must not be copied into entity
   state attributes to make a third-party card convenient.
3. HA SOC does not auto-install or require HACS frontend cards. Optional example
   dashboards may use them, but security administration must work without them.

This preserves the existing architecture: the browser cannot obtain protected
detail unless the corresponding `ha_soc/*` command authorizes the logged-in
user.

## Console information architecture

The console groups the existing leaf views into six stable workspaces. Existing
leaf ids are intentionally unchanged so saved per-user layouts and internal
navigation events continue to work.

| Workspace | Existing protected views |
| --- | --- |
| Overview | Security Overview |
| Assets | Network, Local Peripherals, Entity ReMap, Integration Security |
| Findings | Vulnerability Scanner, Network Security |
| Identity | Users & Access, Permissions |
| SIEM & Audit | Audit Log, Logs |
| Settings | Security Settings (owner only) |

Settings remains owner-only in both the frontend and backend. Grouping a view
under a new workspace does not change its WebSocket permissions.

## Overview rules

The overview is an action-oriented summary, not a second copy of every console
table. It presents:

- posture score and grade;
- open detections;
- critical/high findings;
- monitored asset count;
- posture trend from the existing protected thirty-day history;
- device operational availability;
- vulnerability severity distribution;
- entity reliability;
- identity and detection summaries; and
- the existing protected investigation queues.

Operational availability and security severity are separate axes. An
unavailable device is not automatically a critical vulnerability, and a
critical finding does not mean a device is offline.

## Customize contract

The existing **Customize** function is a retained requirement, not a temporary
implementation detail:

- it appears on every card-based view except Settings;
- order and hidden sections remain scoped per Home Assistant account and leaf
  view id;
- drag-and-drop and keyboard-accessible up/down controls remain available;
- hiding a section never deletes its data;
- a failed layout fetch falls back to declared order with nothing hidden; and
- a failed save may lose persistence but does not roll back the current screen.

Workspace grouping must never migrate, merge, or broaden these per-view layout
records.

## Accessibility and responsive behavior

- Workspace and subview navigation use semantic `nav` elements and native
  buttons.
- Active destinations expose `aria-current`.
- Charts include text values, legends, and accessible names; color is not the
  only carrier of meaning.
- Tables remain horizontally contained on narrow screens.
- KPI and chart grids collapse from four/two columns to one column on mobile.
- Home Assistant theme variables remain the source of surface, text, and status
  colors.

## Delivery phases

### Phase 1 — console shell and Overview

- Introduce the six-workspace navigation shell.
- Preserve every existing leaf component and authorization check.
- Restyle Overview KPIs, posture, trend, availability, and severity visuals.
- Keep the existing Customize store and component unchanged.

### Phase 2 — workspace composition

- Align Assets, Findings, Identity, and SIEM views with the approved hierarchy.
- Remove duplicated summary content only after its destination workspace has a
  tested equivalent.
- Standardize table toolbars, empty states, severity labels, and drill-down
  behavior.

### Phase 3 — optional Lovelace summary

- Define and review an explicit low-sensitivity aggregate entity contract.
- Make expanded summary entities opt-in.
- Provide a native-card-only example and a separate enhanced HACS example.
- Keep all privileged actions and detailed records in the protected console.

## Review gates

Each phase requires:

- a successful TypeScript/Rollup production build with the committed bundle;
- backend authorization and layout regression tests;
- desktop and mobile visual review in light and dark themes;
- keyboard navigation review; and
- confirmation that no protected record was moved into entity attributes or
  another globally readable Home Assistant state surface.
