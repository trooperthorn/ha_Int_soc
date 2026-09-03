import type { FirewallPolicy, FirewallZone } from "./data/ha-soc-ws";

/**
 * Pure zone x zone summary of the Firewall Policies list, the at-a-glance
 * companion to the full policy table. Matched by zone name (against `zones`),
 * not id; "dominant" describes what is present, never which policy wins. See
 * docs/design.md.
 */

export type ZoneMatrixDominant = "allow" | "block" | "mixed" | "none";

export interface ZoneMatrixCell {
  srcZone: string;
  dstZone: string;
  policies: FirewallPolicy[];
  allowCount: number;
  blockCount: number;
  dominant: ZoneMatrixDominant;
}

export function buildZoneMatrix(zones: FirewallZone[], rules: FirewallPolicy[]): ZoneMatrixCell[][] {
  const zoneNames = zones.map((z) => z.name);
  return zoneNames.map((srcZone) =>
    zoneNames.map((dstZone) => {
      const policies = rules.filter((r) => r.source.zone === srcZone && r.destination.zone === dstZone);
      const enabled = policies.filter((r) => r.enabled !== false);
      const allowCount = enabled.filter((r) => r.action === "ALLOW").length;
      const blockCount = enabled.filter((r) => r.action === "BLOCK" || r.action === "REJECT").length;
      let dominant: ZoneMatrixDominant = "none";
      if (allowCount && blockCount) dominant = "mixed";
      else if (allowCount) dominant = "allow";
      else if (blockCount) dominant = "block";
      return { srcZone, dstZone, policies, allowCount, blockCount, dominant };
    })
  );
}
