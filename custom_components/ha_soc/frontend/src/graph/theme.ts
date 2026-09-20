// Vendored from trooperthorn/relationship-maps, packages/graph-core (commit 0c4d268).
// Framework-neutral engine only: no React. Refresh with frontend/src/graph/VENDOR.md.
import type { Category } from './types'

export const BG = '#05070a'
export const ACCENT = '#2fe08a'

/**
 * A qualitative palette that survives a dark background and colour-vision deficiency
 * reasonably well. Adapters pick from it by index when they have no palette of their own,
 * which keeps every tool in the family looking like the same tool.
 */
export const PALETTE = [
  '#4c9ffe', // blue
  '#3ddc84', // green
  '#f3d04e', // yellow
  '#b45cf0', // purple
  '#ff7a5c', // coral
  '#4fd6c8', // teal
  '#ff6b9d', // pink
  '#9ad14b', // lime
  '#e4a33c', // amber
  '#7b8cff', // indigo
  '#d86bd0', // magenta
  '#5ec8e5', // sky
]

export function paletteColor(i: number): string {
  return PALETTE[i % PALETTE.length]!
}

/** Build categories from plain ids, assigning palette colours and lanes in order. */
export function categories(items: Array<{ id: string; label?: string }>): Category[] {
  return items.map((it, i) => ({
    id: it.id,
    label: it.label ?? it.id,
    color: paletteColor(i),
    lane: i,
  }))
}

export function indexCategories(list: Category[]): Map<string, Category> {
  return new Map(list.map((c) => [c.id, c]))
}
