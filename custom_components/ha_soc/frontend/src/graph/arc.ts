// Vendored from trooperthorn/relationship-maps, packages/graph-core (commit 0c4d268).
// Framework-neutral engine only: no React. Refresh with frontend/src/graph/VENDOR.md.
import { forceCollide, forceSimulation, forceX, forceY, type SimulationNodeDatum } from 'd3-force'
import { indexCategories } from './theme'
import type {
  AxisLabel,
  Category,
  DotPos,
  GraphEntity,
  GraphEvent,
  GraphScope,
  Layout,
  LinkPos,
  NodePos,
} from './types'

export interface ArcInput {
  entities: GraphEntity[]
  events: GraphEvent[]
  /** Selected scopes, in order. Their [0,1] ranges are concatenated onto one arc. */
  scopes: GraphScope[]
  groups: Category[]
  width: number
  height: number
  sizeScale: number
  axis?: { start: string; middle: string; end: string }
}

interface SimNode extends SimulationNodeDatum {
  entityId: string
  r: number
  tx: number
  ty: number
}

/**
 * The arc.
 *
 * The ordered axis becomes an angle: u in [0,1] across the concatenated selected scopes maps
 * to theta = pi - u*pi, so the axis runs start (180 deg, left) -> middle (90 deg, top) ->
 * end (0 deg, right). Every event becomes a dot on the band at its own theta, in a lane
 * chosen by entity group. Every entity is placed at the circular mean of its events, pushed
 * outward in proportion to how scattered they are: an entity confined to one stretch of the
 * axis sits tight against the band, one that recurs throughout floats out.
 *
 * Nothing here knows what the axis measures. Campaign time, schema distance and wall-clock
 * hours all land in the same place.
 */
export function layoutArc(input: ArcInput): Layout {
  const { entities, events, scopes, groups, width, height, sizeScale } = input
  const cx = width / 2
  const cy = height * 0.84
  const R = Math.min(width * 0.4, height * 0.68)
  const rOuter = R
  const rInner = R * 0.84
  const lanes = Math.max(1, groups.length)
  const laneStep = (rOuter - rInner) / lanes

  const nodes: NodePos[] = []
  const dots: DotPos[] = []
  const links: LinkPos[] = []
  const axis: AxisLabel[] = []
  const band = { cx, cy, rInner, rOuter }

  if (!scopes.length || !entities.length) return { nodes, dots, links, axis, band }

  const cat = indexCategories(groups)
  const laneOf = (e: GraphEntity) => (cat.get(e.group)?.lane ?? 0) % lanes
  const colorOf = (e: GraphEntity) => cat.get(e.group)?.color ?? '#8892a4'

  const byId = new Map(entities.map((e) => [e.id, e]))
  const n = scopes.length

  // Segment the arc by scope weight, not by scope count. `span` holds each scope's start
  // offset and share of the whole arc in [0,1].
  const total = scopes.reduce((sum, s) => sum + Math.max(0, s.weight ?? 1), 0) || 1
  const span = new Map<string, { from: number; width: number }>()
  let cursor = 0
  for (const s of scopes) {
    const width = Math.max(0, s.weight ?? 1) / total
    span.set(s.id, { from: cursor, width })
    cursor += width
  }

  // Accumulate a resultant vector per entity so we can take a circular mean. Averaging raw
  // angles would wrap wrongly at the ends of the arc.
  const acc = new Map<string, { sx: number; sy: number; count: number }>()

  for (const ev of events) {
    const e = byId.get(ev.entityId)
    if (!e) continue
    const seg = span.get(ev.scopeId)
    if (!seg) continue
    const u = seg.from + Math.min(1, Math.max(0, ev.t)) * seg.width
    const theta = Math.PI - u * Math.PI
    const r = rInner + laneOf(e) * laneStep + laneStep / 2
    dots.push({
      x: cx + r * Math.cos(theta),
      y: cy - r * Math.sin(theta),
      entityId: e.id,
      scopeId: ev.scopeId,
      color: colorOf(e),
    })
    const a = acc.get(e.id) ?? { sx: 0, sy: 0, count: 0 }
    a.sx += Math.cos(theta)
    a.sy += Math.sin(theta)
    a.count++
    acc.set(e.id, a)
  }

  const sim: SimNode[] = []
  const meta = new Map<string, GraphEntity>()
  const gap = 26
  const spread = R * 0.62
  for (const e of entities) {
    const a = acc.get(e.id)
    if (!a || !a.count) continue
    const meanTheta = Math.atan2(a.sy, a.sx)
    // Resultant length: 1 = every event at one instant, 0 = spread across the whole axis.
    const concentration = Math.hypot(a.sx, a.sy) / a.count
    const r = rOuter + gap + laneOf(e) * 15 + (1 - concentration) * spread
    sim.push({
      entityId: e.id,
      r: (4 + Math.sqrt(a.count) * 1.5) * sizeScale,
      tx: cx + r * Math.cos(meanTheta),
      ty: cy - r * Math.sin(meanTheta),
      x: cx + r * Math.cos(meanTheta),
      y: cy - r * Math.sin(meanTheta),
    })
    meta.set(e.id, e)
  }

  forceSimulation(sim)
    .force('x', forceX<SimNode>((d) => d.tx).strength(0.35))
    .force('y', forceY<SimNode>((d) => d.ty).strength(0.35))
    .force('collide', forceCollide<SimNode>((d) => d.r + 9).iterations(2))
    .stop()
    .tick(120)

  const posOf = new Map<string, NodePos>()
  for (const s of sim) {
    const e = meta.get(s.entityId)!
    const p: NodePos = {
      entityId: s.entityId,
      x: s.x ?? s.tx,
      y: s.y ?? s.ty,
      r: s.r,
      color: colorOf(e),
      emphasis: e.emphasis,
    }
    nodes.push(p)
    posOf.set(s.entityId, p)
  }

  // Entity -> its own event dots: one faint curve each, bowed toward the arc centre so the
  // result reads as spokes rather than a mesh.
  for (const d of dots) {
    const p = posOf.get(d.entityId)
    if (!p) continue
    const mx = (p.x + d.x) / 2
    const my = (p.y + d.y) / 2
    links.push({
      x1: p.x,
      y1: p.y,
      x2: d.x,
      y2: d.y,
      cx: mx + (cx - mx) * 0.22,
      cy: my + (cy - my) * 0.22,
      source: d.entityId,
      target: d.entityId,
      color: '#c8d2e0',
      typed: false,
    })
  }

  const at = (u: number, pad: number, text: string): AxisLabel => {
    const theta = Math.PI - u * Math.PI
    const r = rOuter + pad
    return { x: cx + r * Math.cos(theta), y: cy - r * Math.sin(theta), text }
  }
  const caption = input.axis ?? { start: 'Start', middle: 'Midpoint', end: 'Finish' }
  axis.push({ x: cx - rOuter, y: cy + 20, text: caption.start })
  axis.push({ x: cx + rOuter, y: cy + 20, text: caption.end })
  axis.push(at(0.5, 16, caption.middle))
  if (n > 1 && n <= 14) {
    for (const s of scopes) {
      const seg = span.get(s.id)!
      if (seg.width < 0.02) continue // too narrow to label without colliding
      axis.push(at(seg.from + seg.width / 2, -(rOuter - rInner) - 14, s.title))
    }
  }

  return { nodes, dots, links, axis, band }
}
