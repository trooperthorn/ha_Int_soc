import type { FirewallPolicy, FirewallZone } from "./data/ha-soc-ws";

/**
 * Pure zone x zone summary of the Firewall Policies list — the "at a
 * glance" companion to the full policy table, mirroring the drill-down
 * flow of a zone matrix -> the policies for one zone pair -> one policy's
 * full detail (which the existing table row already provides once
 * filtered to that pair).
 *
 * Matched by zone NAME, not id: unifi.py's _normalize_firewall_policy
 * already resolves each policy's source/destination zoneId to its display
 * name (the id itself isn't carried on the policy row), so name is what's
 * actually available to match against the zones list here. A policy whose
 * zone name doesn't match any zone in the current `zones` list (a zone
 * deleted after the policy was last fetched, in the narrow window between
 * two API calls) is simply absent from the matrix rather than crashing.
 *
 * "dominant" is a description of what's THERE, never a claim about which
 * policy wins: UniFi evaluates policies in order with implicit-deny
 * fallback, and confirming which one actually governs a given zone pair
 * would require modeling that evaluation exactly — this project hasn't
 * verified enough of it to claim a winner. "mixed" means both ALLOW and
 * BLOCK/REJECT policies exist for this pair; read the filtered table to
 * see which is actually first.
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
