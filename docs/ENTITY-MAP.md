# Entity Map

The Assets workspace tab that draws the instance as a graph: what exists, what hosts what,
and when it was last doing something. Read this with `design.md` (frontend section) and
`FRONTEND-VISUAL-ARCHITECTURE.md`.

## Why it exists

The other Assets tabs answer questions about one kind of thing at a time: peripherals,
integrations, remapped entity ids. None of them show the shape of the instance. A relationship
map does, and for security work the shape is the point: an integration with an unexpected
reach, a device whose entities are scattered across areas, a bridge every other device depends
on, a corner of the instance that produced no events all day.

## Data sources

Every call is a documented Home Assistant websocket command, made with the signed-in
administrator's own session. The tab adds no backend, no new websocket command of its own,
and no new permission.

| Command | Used for |
| --- | --- |
| `config/entity_registry/list` | entity nodes, their device, area, platform and category |
| `config/device_registry/list` | device nodes, area, `via_device_id`, config entries |
| `config/area_registry/list` | area nodes |
| `config_entries/get` | integration nodes, one per domain rather than per entry |
| `logbook/get_events` | the activity arc, one dot per logbook entry |

Verified against home-assistant/core 2026.9.2:
`homeassistant/components/config/{entity_registry,device_registry,area_registry}.py`,
`components/config/config_entries.py`, and `components/logbook/websocket_api.py` (the schema
takes `start_time`, optional `end_time`, `entity_ids`, `device_ids`, `context_id`).
`via_device_id` is the registry field name that the deprecated `DeviceInfo` key `via_device`
migrates to, per `helpers/device_registry.py`; reading it here is current, not deprecated.

The entity model follows developers.home-assistant.io/docs/core/entity: an entity belongs to
at most one device, carries its own `area_id` or inherits the device's, and is produced by the
platform of a config entry.

## What is drawn

Nodes are devices, entities, areas and integrations. Devices are the anchors, in the same
sense that `Orion.Nodes` anchors the SolarWinds map: everything else is arranged around the
things a home is actually made of.

| Edge kind | Meaning |
| --- | --- |
| Device hosts entity | the entity's `device_id` |
| Device in area | the device's `area_id` |
| Entity in area | the entity's own `area_id`, when it has one |
| Integration provides device | a config entry of the device, collapsed to its domain |
| Integration provides entity | for entities with no device |
| Connected through device | `via_device_id`, for example a bulb through its bridge |

Node size is degree within the currently shown edge kinds, so hiding a kind in the legend
shrinks the nodes that depended on it.

Hidden and disabled registry entries are excluded by default; the checkbox in the toolbar
includes them.

## The two views

**Relationships** is a force layout with devices pinned near the centre. Clicking a node dims
everything that is not a neighbour and opens a details panel with the registry metadata and
the typed links, each of which is a button that walks to the other end.

**Activity** is the arc: the band runs from `-Nh` on the left through the midpoint to `now` on
the right, and every logbook entry is a dot at the moment it happened. An entity active in one
burst hugs the band; an entity active all day floats out above it. The window is 6, 12, 24 or
48 hours.

If the recorder or logbook is not available the call fails softly: the arc is empty and the
relationship view still works.

## The engine

`frontend/src/graph/` is vendored from
[trooperthorn/relationship-maps](https://github.com/trooperthorn/relationship-maps)
`packages/graph-core`, the framework-neutral half only: the data model, the arc and force
layouts and the canvas renderer. `frontend/src/graph/VENDOR.md` says how to refresh it, and
`frontend/scripts/vendor-graph-core.mjs` does the copy. The panel drives it from Lit in
`views/entity-map-view.ts`; the upstream React shell is not vendored.

Vendored rather than depended on because the panel ships one self-contained bundle and HACS
installs the integration directory as it stands. The engine brings `d3-force` and
`d3-quadtree`, which are used for the relaxation pass and for hit testing.

The arc maps the ordered axis to an angle, `theta = pi - u * pi`, and places each node at the
circular mean of its own events, pushed outward in proportion to how scattered they are. The
full explanation lives in the upstream README.

## Limits

- The graph is built in the browser from three registry lists. On a very large instance the
  first layout of several thousand nodes takes a visible moment; the layout is synchronous and
  would need a worker before it grew much further.
- Areas with no devices and integrations with no entities still appear, as isolated nodes.
  That is deliberate: an integration that provides nothing is worth seeing.
- Automations, scripts and scenes appear only as entities. Their references to other entities
  are not drawn; `search/related` would provide them and is the obvious next step.
- The canvas export writes a PNG of the map only, without the toolbar and legend.

## Verification status

The adapter (`frontend/src/data/ha-graph.ts`) was exercised against mock registry payloads:
node and edge construction for all six edge kinds, hidden and disabled filtering both ways,
logbook rows outside the window and for unknown entities dropped, degree weights, and bucket
assignment. The panel bundle builds and type checks.

Not yet run against a live instance: nobody has opened the tab on El Rancho Assist. The first
open is the real test, and the things most likely to be wrong there are layout density on a
real instance and the logbook window size.
