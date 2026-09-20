import type { HomeAssistant } from "../types";
import type { Category, Dataset, GraphEntity, GraphRelation } from "../graph/types";

/**
 * Builds the entity relationship map from Home Assistant's own registries.
 *
 * Every call is a documented websocket command already available to an admin session, so the
 * map needs no backend of its own and no extra permission:
 *   config/entity_registry/list, config/device_registry/list, config/area_registry/list,
 *   config_entries/get, logbook/get_events
 *
 * The model follows developers.home-assistant.io/docs/core/entity: an entity belongs to at
 * most one device, carries its own area or inherits the device's, and is produced by the
 * platform of a config entry. Those are the edges.
 */

export interface EntityRegistryEntry {
  entity_id: string;
  device_id: string | null;
  area_id: string | null;
  platform: string;
  config_entry_id?: string | null;
  name: string | null;
  original_name: string | null;
  entity_category: string | null;
  disabled_by: string | null;
  hidden_by: string | null;
  labels?: string[];
}

export interface DeviceRegistryEntry {
  id: string;
  name: string | null;
  name_by_user: string | null;
  manufacturer: string | null;
  model: string | null;
  area_id: string | null;
  via_device_id: string | null;
  config_entries: string[];
  disabled_by: string | null;
  entry_type: string | null;
}

export interface AreaRegistryEntry {
  area_id: string;
  name: string;
  floor_id: string | null;
}

export interface ConfigEntryItem {
  entry_id: string;
  domain: string;
  title: string;
  state: string;
}

interface LogbookEntry {
  entity_id?: string;
  when: number;
  name?: string;
  state?: string;
  domain?: string;
}

export interface MapOptions {
  /** Size of the activity window on the arc. */
  hours: number;
  /** Number of arc segments the window is cut into. */
  buckets: number;
  /** Include entities the registry has disabled or hidden. */
  includeHidden: boolean;
}

export const DEFAULT_OPTIONS: MapOptions = { hours: 24, buckets: 6, includeHidden: false };

/** Groups are the things a map can contain, not entity domains: domains are too many. */
const GROUPS: Category[] = [
  { id: "device", label: "Devices", color: "#4c9ffe", lane: 0 },
  { id: "entity", label: "Entities", color: "#3ddc84", lane: 1 },
  { id: "area", label: "Areas", color: "#f3d04e", lane: 2 },
  { id: "integration", label: "Integrations", color: "#b45cf0", lane: 3 },
];

const KINDS: Category[] = [
  { id: "device_entity", label: "Device hosts entity", color: "#3ddc84" },
  { id: "device_area", label: "Device in area", color: "#f3d04e" },
  { id: "entity_area", label: "Entity in area", color: "#e4a33c" },
  { id: "integration_device", label: "Integration provides device", color: "#b45cf0" },
  { id: "integration_entity", label: "Integration provides entity", color: "#c58cff" },
  { id: "via_device", label: "Connected through device", color: "#ff7a5c" },
];

const iso = (ms: number) => new Date(ms).toISOString();

export async function fetchEntityMap(
  hass: HomeAssistant,
  options: MapOptions = DEFAULT_OPTIONS,
): Promise<Dataset> {
  const [entityReg, deviceReg, areaReg, entries] = await Promise.all([
    hass.callWS<EntityRegistryEntry[]>({ type: "config/entity_registry/list" }),
    hass.callWS<DeviceRegistryEntry[]>({ type: "config/device_registry/list" }),
    hass.callWS<AreaRegistryEntry[]>({ type: "config/area_registry/list" }),
    hass.callWS<ConfigEntryItem[]>({ type: "config_entries/get" }).catch(() => []),
  ]);

  const visible = (e: EntityRegistryEntry) =>
    options.includeHidden || (!e.disabled_by && !e.hidden_by);
  const usableEntities = entityReg.filter(visible);

  const entryById = new Map(entries.map((e) => [e.entry_id, e]));
  const areaById = new Map(areaReg.map((a) => [a.area_id, a]));
  const deviceById = new Map(deviceReg.map((d) => [d.id, d]));

  const entities: GraphEntity[] = [];
  const relations: GraphRelation[] = [];
  const add = (e: GraphEntity) => entities.push(e);
  const link = (id: string, source: string, target: string, kind: string, label: string) =>
    relations.push({ id, source, target, kind, label });

  for (const a of areaReg) {
    add({
      id: `area:${a.area_id}`,
      name: a.name,
      group: "area",
      kind: "Area",
      weight: 0,
      meta: { "Area id": a.area_id, Floor: a.floor_id ?? "none" },
    });
  }

  // One integration node per domain, not per config entry: two Hue bridges are one
  // integration on the map, which is how people talk about them.
  const domains = new Map<string, ConfigEntryItem[]>();
  for (const e of entries) {
    const list = domains.get(e.domain) ?? [];
    list.push(e);
    domains.set(e.domain, list);
  }
  for (const [domain, list] of domains) {
    add({
      id: `integration:${domain}`,
      name: domain,
      group: "integration",
      kind: "Integration",
      weight: 0,
      meta: {
        "Config entries": list.length,
        Titles: list
          .map((e) => e.title)
          .slice(0, 6)
          .join(", "),
      },
    });
  }
  const domainOfEntry = (entryId: string | null | undefined) =>
    entryId ? (entryById.get(entryId)?.domain ?? null) : null;

  for (const d of deviceReg) {
    if (!options.includeHidden && d.disabled_by) continue;
    add({
      id: `device:${d.id}`,
      name: d.name_by_user ?? d.name ?? d.id,
      group: "device",
      kind: d.entry_type ? `Device (${d.entry_type})` : "Device",
      weight: 0,
      // Devices are what a home is actually made of; pin them like Orion.Nodes.
      emphasis: true,
      meta: {
        Manufacturer: d.manufacturer ?? "unknown",
        Model: d.model ?? "unknown",
        Area: d.area_id ? (areaById.get(d.area_id)?.name ?? d.area_id) : "none",
        "Device id": d.id,
      },
    });
    if (d.area_id && areaById.has(d.area_id)) {
      link(`da:${d.id}`, `device:${d.id}`, `area:${d.area_id}`, "device_area", "Area");
    }
    if (d.via_device_id && deviceById.has(d.via_device_id)) {
      link(
        `vd:${d.id}`,
        `device:${d.via_device_id}`,
        `device:${d.id}`,
        "via_device",
        "Connected through",
      );
    }
    for (const entryId of d.config_entries) {
      const domain = domainOfEntry(entryId);
      if (domain) {
        link(
          `id:${d.id}:${domain}`,
          `integration:${domain}`,
          `device:${d.id}`,
          "integration_device",
          "Provides",
        );
      }
    }
  }

  const knownDevice = new Set(entities.filter((e) => e.group === "device").map((e) => e.id));

  for (const e of usableEntities) {
    const id = `entity:${e.entity_id}`;
    const domain = e.entity_id.split(".")[0] ?? "unknown";
    add({
      id,
      name: e.name ?? e.original_name ?? e.entity_id,
      group: "entity",
      kind: domain,
      weight: 0,
      meta: {
        "Entity id": e.entity_id,
        Domain: domain,
        Platform: e.platform,
        Category: e.entity_category ?? "primary",
        Device: e.device_id ? (deviceById.get(e.device_id)?.name ?? e.device_id) : "none",
      },
    });
    if (e.device_id && knownDevice.has(`device:${e.device_id}`)) {
      link(`de:${e.entity_id}`, `device:${e.device_id}`, id, "device_entity", "Hosts");
    } else {
      // Entities with no device still belong to their integration, and to their own area.
      const domainForEntity = domainOfEntry(e.config_entry_id) ?? e.platform;
      if (domains.has(domainForEntity)) {
        link(
          `ie:${e.entity_id}`,
          `integration:${domainForEntity}`,
          id,
          "integration_entity",
          "Provides",
        );
      }
    }
    if (e.area_id && areaById.has(e.area_id)) {
      link(`ea:${e.entity_id}`, id, `area:${e.area_id}`, "entity_area", "Area");
    }
  }

  const degree = new Map<string, number>();
  for (const r of relations) {
    degree.set(r.source, (degree.get(r.source) ?? 0) + 1);
    degree.set(r.target, (degree.get(r.target) ?? 0) + 1);
  }
  for (const e of entities) e.weight = degree.get(e.id) ?? 0;

  // The arc is activity: when did each thing actually do something. The logbook is the
  // cheapest honest answer, and it is already indexed by time.
  const now = Date.now();
  const span = options.hours * 3600_000;
  const scopes = Array.from({ length: options.buckets }, (_, i) => {
    const from = new Date(now - span + (i * span) / options.buckets);
    return {
      id: `w${i}`,
      title: from.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      ordinal: i + 1,
      subtitle: `${(options.hours / options.buckets).toFixed(1)}h`,
    };
  });

  let logbook: LogbookEntry[] = [];
  try {
    logbook = await hass.callWS<LogbookEntry[]>({
      type: "logbook/get_events",
      start_time: iso(now - span),
      end_time: iso(now),
    });
  } catch {
    // No recorder, or logbook not loaded. The relation view still works; the arc is empty.
    logbook = [];
  }

  const known = new Set(entities.map((e) => e.id));
  const events = [];
  let n = 0;
  for (const entry of logbook) {
    if (!entry.entity_id) continue;
    const id = `entity:${entry.entity_id}`;
    if (!known.has(id)) continue;
    // logbook `when` is epoch seconds, float.
    const ms = entry.when * 1000;
    const u = (ms - (now - span)) / span;
    if (u < 0 || u > 1) continue;
    const bucket = Math.min(options.buckets - 1, Math.floor(u * options.buckets));
    events.push({
      id: `lb${n++}`,
      scopeId: `w${bucket}`,
      entityId: id,
      t: u * options.buckets - bucket,
    });
  }

  const deviceCount = entities.filter((e) => e.group === "device").length;
  const entityCount = entities.filter((e) => e.group === "entity").length;

  return {
    title: "Entity relationship map",
    subtitle: `${deviceCount} devices, ${entityCount} entities, ${relations.length} links, ${events.length} logbook events`,
    groups: GROUPS,
    relationKinds: KINDS,
    scopes,
    entities,
    relations,
    events,
    axis: { start: `-${options.hours}h`, middle: `-${options.hours / 2}h`, end: "now" },
    scopeNoun: ["window", "windows"],
    viewLabels: { arc: "Activity", web: "Relationships" },
    arcHint: `Activity over the last ${options.hours} hours from the logbook. Each dot is one event.`,
    webHint:
      "Registry relationships: devices host entities, live in areas and come from integrations.",
  };
}
