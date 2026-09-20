# Vendored graph engine

`src/graph/` is a copy of the framework-neutral half of
[trooperthorn/relationship-maps](https://github.com/trooperthorn/relationship-maps)
`packages/graph-core`: the data model, the two layouts and the canvas renderer. The React
shell of that package is deliberately not vendored; the panel drives the engine from Lit in
`views/entity-map-view.ts`.

Vendored rather than depended on because the panel ships one self-contained bundle and HACS
installs the integration directory as-is; a workspace dependency on a second repository would
not survive that.

| Vendored file | Upstream path |
| --- | --- |
| `types.ts` | `packages/graph-core/src/types.ts` |
| `theme.ts` | `packages/graph-core/src/theme.ts` |
| `arc.ts` | `packages/graph-core/src/layout/arc.ts` |
| `force.ts` | `packages/graph-core/src/layout/force.ts` |
| `renderer.ts` | `packages/graph-core/src/render/renderer.ts` |

## Refreshing

```bash
node scripts/vendor-graph-core.mjs --from /path/to/relationship-maps
npm run build
```

The script rewrites the two relative imports (`../theme`, `../types`) to siblings, strips em
dashes to match this repository's style rule, and stamps the upstream commit into each
header. Do not edit the vendored files by hand: a local fix belongs upstream, or the next
refresh silently reverts it.
