// Vendored from trooperthorn/relationship-maps, packages/graph-core (commit 0c4d268).
// Framework-neutral engine only: no React. Refresh with frontend/src/graph/VENDOR.md.
/**
 * The domain-neutral graph model.
 *
 * Every tool built on this core maps its own world onto these shapes and nothing else.
 * A TTRPG campaign, a SolarWinds schema, a Home Assistant instance and a Music Assistant
 * library are all "entities in groups, related by typed edges, appearing at points along an
 * ordered axis". Keep domain vocabulary out of this file.
 */

/** A colour-carrying category. Entity groups and relation kinds are both categories. */
export interface Category {
  id: string
  label: string
  color: string
  /** Radial lane for the arc layout; defaults to declaration order. */
  lane?: number
}

export interface GraphEntity {
  id: string
  name: string
  /** Category id from `Dataset.groups` - decides colour and lane. */
  group: string
  /** Free-form sub-type shown in the details panel (e.g. "PC", "Orion.Nodes", "sensor"). */
  kind?: string
  /** Pre-computed weight: mention count, degree, popularity. Drives node radius. */
  weight: number
  /** Draws a hollow centre - use for the handful of entities that anchor the graph. */
  emphasis?: boolean
  /** Arbitrary key/values rendered in the details panel, in insertion order. */
  meta?: Record<string, string | number>
}

export interface GraphRelation {
  id: string
  source: string
  target: string
  /** Category id from `Dataset.relationKinds` - decides edge colour and legend row. */
  kind: string
  /** Specific name for this edge, e.g. a SWIS navigation property. Shown in details. */
  label?: string
  weight?: number
}

/**
 * One slice of the ordered axis: a play session, a polling window, a schema depth, an album.
 * Scopes are what the scope picker selects and what the arc concatenates.
 */
export interface GraphScope {
  id: string
  title: string
  ordinal: number
  subtitle?: string
  /**
   * Relative share of the arc this scope occupies. Defaults to 1, giving every scope an
   * equal segment - right for play sessions, wrong for anything whose slices differ wildly
   * in population (a hop ring holding one entity should not get the same arc as one holding
   * four hundred).
   */
  weight?: number
}

/**
 * An entity appearing at a point inside a scope. `t` is 0 at the start of the scope and 1 at
 * its end. This is the only thing the arc layout needs in order to mean something.
 */
export interface GraphEvent {
  id: string
  scopeId: string
  entityId: string
  t: number
}

export interface Dataset {
  title: string
  subtitle?: string
  groups: Category[]
  relationKinds: Category[]
  scopes: GraphScope[]
  entities: GraphEntity[]
  relations: GraphRelation[]
  events: GraphEvent[]
  /** Axis captions for the arc, e.g. Start / Midpoint / Finish or Root / … / Leaf. */
  axis?: { start: string; middle: string; end: string }
  /** Words the UI uses for a scope, singular and plural. */
  scopeNoun?: [string, string]
  /** What the arc axis means; shown in the hint bar. */
  arcHint?: string
  /** What the relation graph shows; shown in the hint bar. */
  webHint?: string
  /** Labels for the two view buttons. */
  viewLabels?: { arc: string; web: string }
}

/** A pluggable origin for a dataset: a bundled file, a REST call, a websocket snapshot. */
export interface DataSource {
  id: string
  label: string
  load(signal?: AbortSignal): Promise<Dataset>
}

export type ViewId = 'arc' | 'web'

export interface NodePos {
  entityId: string
  x: number
  y: number
  r: number
  color: string
  emphasis?: boolean
}

export interface DotPos {
  x: number
  y: number
  entityId: string
  scopeId: string
  color: string
}

export interface LinkPos {
  x1: number
  y1: number
  x2: number
  y2: number
  cx?: number
  cy?: number
  source: string
  target: string
  color: string
  /** Typed edges draw brighter and thicker than derived event spokes. */
  typed: boolean
}

export interface AxisLabel {
  x: number
  y: number
  text: string
}

export interface Layout {
  nodes: NodePos[]
  dots: DotPos[]
  links: LinkPos[]
  axis: AxisLabel[]
  band?: { cx: number; cy: number; rInner: number; rOuter: number }
}
