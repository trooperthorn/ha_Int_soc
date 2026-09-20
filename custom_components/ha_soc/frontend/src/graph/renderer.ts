// Vendored from trooperthorn/relationship-maps, packages/graph-core (commit 0c4d268).
// Framework-neutral engine only: no React. Refresh with frontend/src/graph/VENDOR.md.
import { quadtree } from 'd3-quadtree'
import { BG } from './theme'
import type { GraphEntity, Layout, NodePos } from './types'

export interface Camera {
  x: number
  y: number
  k: number
}

export interface Scene {
  layout: Layout
  entities: Map<string, GraphEntity>
  camera: Camera
  showLabels: boolean
  hovered: string | null
  selected: string | null
  /** Entities related to the selection; everything else is dimmed. */
  focus: Set<string> | null
  /** Device pixel ratio; `w`/`h` are CSS pixels. */
  dpr: number
}

const LABEL_FONT = '600 11px ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif'
const MAX_LABELS = 55

export function worldToScreen(c: Camera, x: number, y: number): [number, number] {
  return [x * c.k + c.x, y * c.k + c.y]
}

export function screenToWorld(c: Camera, x: number, y: number): [number, number] {
  return [(x - c.x) / c.k, (y - c.y) / c.k]
}

/** Camera that fits the whole layout into `w` x `h` with a margin, never magnifying past 1:1. */
export function fitCamera(layout: Layout, w: number, h: number): Camera {
  if (!layout.nodes.length) return { x: 0, y: 0, k: 1 }
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  const consider = (x: number, y: number, pad: number) => {
    minX = Math.min(minX, x - pad)
    minY = Math.min(minY, y - pad)
    maxX = Math.max(maxX, x + pad)
    maxY = Math.max(maxY, y + pad)
  }
  // Pad generously above each node: labels are drawn in screen space above the dot and
  // would otherwise be clipped by a fit that only accounted for the geometry.
  for (const p of layout.nodes) consider(p.x, p.y, p.r + 34)
  for (const d of layout.dots) consider(d.x, d.y, 2)
  if (layout.band) {
    const { cx, cy, rOuter } = layout.band
    consider(cx - rOuter, cy - rOuter, 0)
    consider(cx + rOuter, cy + 30, 0)
  }
  const k = Math.min(1, Math.min(w / (maxX - minX), h / (maxY - minY)) * 0.94)
  return { k, x: w / 2 - ((minX + maxX) / 2) * k, y: h / 2 - ((minY + maxY) / 2) * k }
}

export function pickNode(layout: Layout, wx: number, wy: number): string | null {
  const tree = quadtree<NodePos>()
    .x((d) => d.x)
    .y((d) => d.y)
    .addAll(layout.nodes)
  const hit = tree.find(wx, wy, 40)
  if (!hit) return null
  return Math.hypot(hit.x - wx, hit.y - wy) <= hit.r + 8 ? hit.entityId : null
}

export function render(ctx: CanvasRenderingContext2D, w: number, h: number, scene: Scene): void {
  const { layout, entities, camera, focus, hovered, selected } = scene
  const dpr = scene.dpr
  const toWorld = () =>
    ctx.setTransform(camera.k * dpr, 0, 0, camera.k * dpr, camera.x * dpr, camera.y * dpr)
  const toScreen = () => ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  toScreen()
  ctx.fillStyle = BG
  ctx.fillRect(0, 0, w, h)
  toWorld()
  ctx.lineCap = 'round'

  const lit = (id: string) => !focus || focus.has(id)

  if (layout.band) {
    const { cx, cy, rInner, rOuter } = layout.band
    ctx.beginPath()
    ctx.arc(cx, cy, rOuter, Math.PI, 0)
    ctx.arc(cx, cy, rInner, 0, Math.PI, true)
    ctx.closePath()
    ctx.fillStyle = 'rgba(190,198,210,0.10)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(190,198,210,0.16)'
    ctx.lineWidth = 1 / camera.k
    ctx.stroke()
  }

  // Two passes so highlighted edges land on top of dimmed ones.
  const drawLinks = (highlighted: boolean) => {
    for (const l of layout.links) {
      const on = lit(l.source) || lit(l.target)
      if (on !== highlighted) continue
      ctx.beginPath()
      ctx.moveTo(l.x1, l.y1)
      if (l.cx !== undefined && l.cy !== undefined) ctx.quadraticCurveTo(l.cx, l.cy, l.x2, l.y2)
      else ctx.lineTo(l.x2, l.y2)
      ctx.strokeStyle = l.color
      if (l.typed) {
        ctx.globalAlpha = highlighted ? 0.85 : 0.1
        ctx.lineWidth = (highlighted ? 1.6 : 1) / camera.k
      } else {
        ctx.globalAlpha = highlighted ? 0.28 : 0.05
        ctx.lineWidth = (highlighted ? 0.9 : 0.6) / camera.k
      }
      ctx.stroke()
    }
  }
  drawLinks(false)
  drawLinks(true)
  ctx.globalAlpha = 1

  for (const d of layout.dots) {
    const on = lit(d.entityId)
    ctx.globalAlpha = on ? 0.95 : 0.16
    ctx.fillStyle = on ? d.color : '#8892a4'
    ctx.beginPath()
    ctx.arc(d.x, d.y, (on ? 1.5 : 1.1) / camera.k + 0.6, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1

  for (const p of [...layout.nodes].sort((a, b) => a.r - b.r)) {
    const on = lit(p.entityId)
    ctx.globalAlpha = on ? 1 : 0.2
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fillStyle = p.color
    ctx.fill()
    if (p.entityId === hovered || p.entityId === selected) {
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 2 / camera.k
    } else {
      ctx.strokeStyle = 'rgba(5,7,10,0.85)'
      ctx.lineWidth = 1.2 / camera.k
    }
    ctx.stroke()
    if (p.emphasis) {
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r * 0.42, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(5,7,10,0.65)'
      ctx.fill()
    }
  }
  ctx.globalAlpha = 1

  // Axis furniture in screen space so it keeps a constant size as you zoom.
  toScreen()
  ctx.font = '600 10px ui-sans-serif, system-ui, sans-serif'
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'center'
  ctx.fillStyle = 'rgba(190,198,210,0.55)'
  for (const a of layout.axis) {
    const [sx, sy] = worldToScreen(camera, a.x, a.y)
    if (sx < -60 || sx > w + 60 || sy < -20 || sy > h + 20) continue
    ctx.fillText(a.text, sx, sy)
  }
  ctx.textAlign = 'left'

  if (!scene.showLabels) return

  const labelled = [...layout.nodes]
    .filter((p) => lit(p.entityId))
    .sort((a, b) => b.r - a.r)
    .slice(0, MAX_LABELS)
  for (const id of [hovered, selected]) {
    if (!id) continue
    const p = layout.nodes.find((q) => q.entityId === id)
    if (p && !labelled.includes(p)) labelled.push(p)
  }

  toScreen()
  ctx.font = LABEL_FONT
  ctx.textBaseline = 'middle'
  // Biggest first, dropping any label whose box collides with one already placed. Without
  // this the dense end of the arc turns into a wall of overlapping pills.
  const placed: Array<[number, number, number, number]> = []
  const collides = (x: number, y: number, bw: number, bh: number) =>
    placed.some(([px, py, pw, ph]) => x < px + pw && x + bw > px && y < py + ph && y + bh > py)
  for (const p of labelled) {
    const e = entities.get(p.entityId)
    if (!e) continue
    const [sx, sy] = worldToScreen(camera, p.x, p.y)
    const tw = ctx.measureText(e.name).width
    const bw = tw + 14
    const bh = 18
    const bx = sx - bw / 2
    const by = sy - p.r * camera.k - bh - 6
    if (bx + bw < 0 || bx > w || by + bh < 0 || by > h) continue
    const forced = p.entityId === hovered || p.entityId === selected
    if (!forced && collides(bx - 2, by - 2, bw + 4, bh + 16)) continue
    placed.push([bx - 2, by - 2, bw + 4, bh + 16])
    ctx.fillStyle = 'rgba(5,7,10,0.82)'
    ctx.strokeStyle = p.color
    ctx.lineWidth = 1
    roundRect(ctx, bx, by, bw, bh, 5)
    ctx.fill()
    ctx.stroke()
    ctx.fillStyle = '#e8eef6'
    ctx.fillText(e.name, bx + 7, by + bh / 2 + 0.5)

    const badge = String(e.weight)
    ctx.font = '600 9px ui-sans-serif, system-ui, sans-serif'
    const cw = ctx.measureText(badge).width + 8
    ctx.fillStyle = 'rgba(5,7,10,0.9)'
    ctx.strokeStyle = 'rgba(190,198,210,0.45)'
    roundRect(ctx, sx - p.r * camera.k - cw + 2, by + bh - 2, cw, 13, 6)
    ctx.fill()
    ctx.stroke()
    ctx.fillStyle = '#b9c4d4'
    ctx.fillText(badge, sx - p.r * camera.k - cw + 6, by + bh + 4.5)
    ctx.font = LABEL_FONT
  }
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
