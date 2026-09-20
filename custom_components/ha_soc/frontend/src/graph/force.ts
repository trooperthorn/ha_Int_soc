// Vendored from trooperthorn/relationship-maps, packages/graph-core (commit 0c4d268).
// Framework-neutral engine only: no React. Refresh with frontend/src/graph/VENDOR.md.
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceRadial,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force'
import { indexCategories } from './theme'
import type { Category, GraphEntity, GraphRelation, Layout, LinkPos, NodePos } from './types'

export interface ForceInput {
  entities: GraphEntity[]
  relations: GraphRelation[]
  groups: Category[]
  relationKinds: Category[]
  width: number
  height: number
  sizeScale: number
  /**
   * Entities to pin near the centre. Anchors are what the graph is *about* - the PCs in a
   * campaign, Orion.Nodes in a SolarWinds schema, the hub devices in a home. Everything else
   * arranges itself around them instead of the layout's arbitrary centre of mass.
   */
  anchors?: string[]
}

interface SimNode extends SimulationNodeDatum {
  entityId: string
  r: number
  degree: number
  anchor: boolean
}
type SimLink = SimulationLinkDatum<SimNode> & { kind: string }

/**
 * The relation web: the curated graph. Edges are typed and colour-coded, and node size is
 * degree within the *shown* edges, so filtering a kind out of the legend genuinely shrinks
 * the nodes that relied on it.
 */
export function layoutForce(input: ForceInput): Layout {
  const { entities, relations, groups, relationKinds, width, height, sizeScale } = input
  const gcat = indexCategories(groups)
  const kcat = indexCategories(relationKinds)
  const anchors = new Set(input.anchors ?? [])

  const degree = new Map<string, number>()
  for (const r of relations) {
    degree.set(r.source, (degree.get(r.source) ?? 0) + 1)
    degree.set(r.target, (degree.get(r.target) ?? 0) + 1)
  }

  const nodes: SimNode[] = entities.map((e, i) => {
    const d = degree.get(e.id) ?? 0
    const anchor = anchors.has(e.id)
    // Deterministic starting ring: random seeds make every reload a different picture.
    const a = (i / Math.max(1, entities.length)) * Math.PI * 2
    const ring = anchor ? 0 : Math.min(width, height) * 0.3
    return {
      entityId: e.id,
      degree: d,
      anchor,
      r: (anchor ? 8 : 5) + Math.sqrt(d) * (anchor ? 4.2 : 3.2) * sizeScale,
      x: width / 2 + Math.cos(a) * ring,
      y: height / 2 + Math.sin(a) * ring,
    }
  })
  const index = new Map(nodes.map((n) => [n.entityId, n]))
  const links: SimLink[] = relations
    .filter((r) => index.has(r.source) && index.has(r.target))
    .map((r) => ({ source: index.get(r.source)!, target: index.get(r.target)!, kind: r.kind }))

  const sim = forceSimulation(nodes)
    .force('link', forceLink<SimNode, SimLink>(links).distance(90).strength(0.35))
    .force('charge', forceManyBody<SimNode>().strength(-220))
    .force('center', forceCenter(width / 2, height / 2))
    .force('collide', forceCollide<SimNode>((d) => d.r + 12).iterations(2))

  if (anchors.size) {
    // Pull anchors to the middle and push everything else out, so the picture is read from
    // the anchor outwards rather than from wherever the simulation happened to settle.
    sim.force(
      'radial',
      forceRadial<SimNode>(
        (d) => (d.anchor ? 0 : Math.min(width, height) * 0.34),
        width / 2,
        height / 2,
      ).strength((d) => (d.anchor ? 0.35 : 0.06)),
    )
  }
  sim.stop().tick(360)

  const byId = new Map(entities.map((e) => [e.id, e]))
  const out: NodePos[] = nodes.map((n) => {
    const e = byId.get(n.entityId)!
    return {
      entityId: n.entityId,
      x: n.x ?? width / 2,
      y: n.y ?? height / 2,
      r: n.r,
      color: gcat.get(e.group)?.color ?? '#8892a4',
      emphasis: e.emphasis,
    }
  })

  const linkPos: LinkPos[] = links.map((l) => {
    const s = l.source as SimNode
    const t = l.target as SimNode
    return {
      x1: s.x ?? 0,
      y1: s.y ?? 0,
      x2: t.x ?? 0,
      y2: t.y ?? 0,
      source: s.entityId,
      target: t.entityId,
      color: kcat.get(l.kind)?.color ?? '#7b8cff',
      typed: true,
    }
  })

  return { nodes: out, dots: [], links: linkPos, axis: [] }
}
