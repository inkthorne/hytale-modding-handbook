---
title: "Caves"
description: "Generate Hytale caves with JSON density fields — cave volumes as density graphs or graph-generator tunnels, carving into terrain via Min, depth-band confinement with CurveMapper, and tunnel shaping from noise."
seo:
  type: TechArticle
---

# Caves

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.7.2**

Hytale caves are **not** a separate "cave type / cave node / corridor" system. A cave is simply a
**density field** that goes negative inside the volume you want hollow, combined into a biome's
terrain density with `Min`. Wherever the cave field is lower than the surface field, the surface
field is overridden and that cell becomes empty — i.e. carved out.

The shipped assets build that cave field in two ways, both out of the ordinary node vocabulary:

- **A plain density field** — noise shaped with the same nodes as
  [terrain](worldgen-terrain.md) (`SimplexNoise2D`, `CurveMapper`, `Sum`, `Min`, `Max`, `Mix`,
  `Normalizer`, `Pow`, `Abs`, `Inverter`, `BaseHeight`, `Cache`, `Imported`, `Constant`),
  exported by name and imported into biomes. `Volcanic1_Caves_Terrain` is built this way.
- **A graph generator read through a `Graph` density node** — tunnels laid out as a graph of
  nodes and edges, each node carrying the density that hollows the space around it. All five
  Plains1 biomes carve their caves this way from the shared `Plains1_Caves` generator, and the
  goblin portal world does the same with `Portal_Goblin_Graph_Cave`.

## Overview

Defined as JSON density fields and graph generators under `Server/HytaleGenerator/` and provides:
- Cave volumes expressed as density graphs (no dedicated cave schema)
- Carving by combining a cave field into terrain with `Min`
- Depth-band confinement via `CurveMapper` over `BaseHeight`
- Noise-shaped caves (`Density/`) or graph-laid tunnels (`GraphGenerators/`)
- Export by name so several biomes share the same cave field

## Architecture
```
Plain cave field (Density/Volcanic1_Caves_Terrain.json)
├── root Cache (ExportAs "Volcanic1_Caves_Terrain")
│   └── Mix of Constant -1, a noise Sum, and a depth-band CurveMapper(BaseHeight)
└── carving: biome Terrain root = Min(Inverter(Imported cave field), surface field)

Graph cave (GraphGenerators/Plains1_Caves.json)
├── Passes: lay nodes on a grid → move them → connect neighbours → attach content
│           (content = density + materials + cave props around each node)
└── carving: biome Terrain root = Min(surface field,
               YSampled(Mix(Constant 1, Graph "Plains1_Caves", depth-band CurveMapper)))
```

## Key Classes
These are JSON worldgen node types (not Java classes); the table lists the key node types documented on this page.

| Node type | Role in caves | Description |
|-----------|---------------|-------------|
| `Min` | Carving | Combines cave field with terrain; lower (cave) value wins -> empty |
| `Graph` | Graph cave | Density read from a graph generator's node content |
| `Cache` | Field root | Memoizes and `ExportAs` the cave field for biome import |
| `SimplexNoise2D` | Tunnel shape | Drives the meander of a noise-built cave |
| `CurveMapper` | Depth band | Maps `BaseHeight` (`Distance`) altitude to a carve multiplier |
| `BaseHeight` | Reference | Ties cave heights to the named world `Base` height |
| `Imported` / `Exported` | Reuse | Pull the cave field into a biome terrain graph |

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Where caves live](#where-caves-live) | Canonical asset paths |
| [How carving works](#how-carving-works) | `Min` against terrain |
| [Anatomy of a cave field](#anatomy-of-a-cave-field) | Plains1_Caves: tunnels from a graph generator |
| [Volcanic example](#volcanic-example) | A plain noise-built density field |
| [Building blocks](#building-blocks) | Depth bands, wall pinching |
| [What does NOT exist](#what-does-not-exist) | Removed fictional schema |
| [Gotchas](#gotchas) | Dangling imports and silent fallbacks |

---

## Where caves live

| Content | Path |
|---------|------|
| Noise-built cave density fields | `Server/HytaleGenerator/Density/*_Caves_*.json` |
| Graph-generator caves | `Server/HytaleGenerator/GraphGenerators/*.json` |

Shipped cave assets (0.7.2):

| File | Kind | Published as |
|------|------|--------------|
| `Density/Volcanic1_Caves_Terrain.json` | density field | `ExportAs` `Volcanic1_Caves_Terrain` (plus an inner `Volcanic1_Swamps_Giant_Roots_Wave` noise) |
| `GraphGenerators/Plains1_Caves.json` | graph generator | `ExportName` `Plains1_Caves` |
| `GraphGenerators/Portal_Goblin_Graph_Cave.json` + `Density/Portal_Goblin_Graph_Cave.json` | graph generator, wrapped in an exported density | the density file exports `Portal_Goblin_Graph_Cave`: an `Exported` → `Cache` → `YSampled` → `Mix` whose first input is the `Graph` node |

The three Plains1 cave fields that 0.6.8 shipped as density files
(`Plains1_Caves_Terrain`, `Plains1_Caves_Deeproot_Terrain`, `Plains1_Caves_Mountains`) were
removed in 0.7.2, along with the `Plains1_Deeproot` and `Plains1_Mountains` biomes; the Plains1
caves are now the `Plains1_Caves` graph generator.

---

## How carving works

The terrain root in `Plains1_Oak.json` is a `Min` node:

```json
"Density": {
  "Type": "Min",
  "Inputs": [
    { "Type": "Mix", "Inputs": [ "...surface..." ] },
    { "Type": "YSampled", "SampleDistance": 3, "SampleOffset": 0, "Interpolate": true,
      "Inputs": [ { "Type": "Mix", "Inputs": [ "...Constant 1, Graph, CurveMapper..." ] } ] }
  ]
}
```

`Min` returns the smaller of the two inputs. The surface field is positive (solid) below ground.
The cave field is engineered to dip **below** the surface value along the tunnels and chambers;
where it does, `Min` selects it and the cell reads as empty. Everywhere else the cave field stays
high enough (here `Constant 1`, or the `Graph` node's `BackgroundValue` of `1`) that the surface
field wins and the ground is untouched.

There is no separate carve pass and no priority table — carving is one `Min` at the terrain
root. What varies between biomes is the *wrapper* around the cave field, not the combinator:

| Biome | Terrain root | How the cave field enters |
|-------|--------------|---------------------------|
| `Plains1_Oak`, `Plains1_Gorges`, `Plains1_Hills`, `Plains1_River`, `Plains1_Trork` | `Min` | `YSampled` (`SampleDistance: 3`) → `Mix` of `Constant 1`, a `Graph` node importing `Plains1_Caves`, and a depth-band `CurveMapper` — identical in all five |
| `Portal_Goblin_Biome_Edge` | `Min` | `Imported` `Portal_Goblin_Graph_Cave` directly |
| `Portal_Goblin_Biome` | `Selector` | `Imported` `Portal_Goblin_Graph_Cave` as the `Selector`'s first input and again under a `LessOrEqual` node in its third |
| `Volcanic1_Caldera` | `Min` | `Imported` inside an `Inverter` — `Volcanic1_Caves_Terrain` is authored sign-flipped, so it is negated before the `Min` |
| `Volcanic1_Jungle` | `Mix` | `Imported` deep inside the `Mix`'s first input, under an `Exported` `Volcanic1_Jungles_Roots_Wood` chain and a `CurveMapper` |
| `Volcanic1_River` | `Multiplier` | `Imported` deep inside a `Cache`/`Exported` chain, not at the root |
| `Desert1_Rocky`, `Experimental/Mountains`, `Desert1_Stacks` | `Min` (`Max` → `Min` in `Stacks`) | `Imported` `Plains1_Caves_Terrain` — a name nothing exports in 0.7.2; see [Gotchas](#gotchas) |

> **Gotcha:** a cave field's sign convention is not universal. A field meant to drop into a
> `Min` reads "negative = hollow"; `Volcanic1_Caves_Terrain` is the other way round (its `Mix`
> returns `Constant -1` outside the depth band) and is only correct after an `Inverter`. Check
> which way an existing field is authored before importing it.

Import counts across the shipped assets (as of 0.7.2): `Volcanic1_Caves_Terrain` 4× (two in
`Volcanic1_Caldera`, one each in `Volcanic1_Jungle` and `Volcanic1_River`), and
`Plains1_Caves` is named by 21 `ImportName`s across the Plains1 biomes' terrain and material
providers.

---

## Anatomy of a cave field

The Plains1 caves (`GraphGenerators/Plains1_Caves.json`) are the reference example: a graph
generator read through a `Graph` density node.

### The `Graph` density node

A `Graph` density node evaluates a graph generator and turns the content attached to its nodes
into a density value:

| Key | Meaning |
|-----|---------|
| `GraphGenerator` | The generator: inline, or `{ "ImportName": "<name>" }` to use one published elsewhere with `ExportName` |
| `ContentLayer` | Which content layer to read from each node (`"Priority0"` in the shipped caves) |
| `BackgroundValue` | Value returned where no node's content reaches |
| `TransitionSlope` / `TransitionOffset` / `TransitionSmooth` | Shape of each node's falloff from its centre to the edge of its content `Range` |
| `QueryBufferCapacity` | Size of the node-query cache |

At a sample position the node gathers every graph node whose density content (on that
`ContentLayer`) has the position within its `Range`, evaluates each node's own density with that
node as the anchor, and returns their average weighted by the falloff; with no node in range it
returns `BackgroundValue` (`GraphDensity.evaluate`). The five Plains1 biomes all use
`ContentLayer: "Priority0"`, `BackgroundValue: 1`, `TransitionSlope: 2.5`,
`TransitionOffset: 0`, `TransitionSmooth: 0.2` and `QueryBufferCapacity: 3`, then fade the result
to `Constant 1` outside a depth band with a `CurveMapper` over `BaseHeight` (points
`-90→0, -80→1, 20→1, 30→0`) as the `Mix` influence.

Because every biome imports the generator by name, they share **one** graph layout: the
generator's grid is cached per `ExportName`/`ImportName` key, so a tunnel crossing a biome border
continues on the other side.

### The generator file

`Server/HytaleGenerator/GraphGenerators/Plains1_Caves.json` carries the generator itself:

```json
{
  "ExportName": "Plains1_Caves",
  "CacheCellSize": { "X": 320, "Y": 320, "Z": 320 },
  "CacheCapacity": 50,
  "PrintStats": false,
  "StatsPrintInterval": 50,
  "StatsLabel": "UNNAMED",
  "Passes": [ "...13 passes..." ]
}
```

The world is cut into `CacheCellSize` cells and the passes run once per cell, in order. The
shipped file also carries an `"IsSingleInstance": true` key, which 0.7.2 no longer reads (it was
removed from the generator's codec). Its 13 passes are:

| Passes | Type | What they do |
|--------|------|--------------|
| 0, 3 | `Positions` | Lay graph nodes: a `SquareGrid2d` scaled by 20 (pass 3: by 30, thinned by a `FieldFunction` over the imported `Base-Simplex-192` noise), jittered (`Jitter2d`), lifted to the `Base` height by a `BaseHeight` position provider |
| 1, 4 | `NodeAction` → `Content` | Tag the new nodes with content |
| 2, 5 | `NodeAction` → `Selector` → `Move` | Move the tagged nodes of each layer vertically by an amount read from noise (`MaxDistance` 70 / 90) |
| 6–9 | `NodeAction` → `Selector` → `ProximityConnector` | Connect nodes into tunnels: each selected node links to up to `Cap` (1) randomly chosen nodes within `Range` (25–40) that match the connector's own `NodeSelector` |
| 10–12 | `NodeAction` → `Selector` → `Content` | Attach the cave content to selected nodes |

The content attached in passes 10–12 is what actually carves. Each content object carries
`DensityContent` (a density graph plus the `Range` it reaches and its `ContentLayer` — here a
`MultiMix` or `Min` built on `DistanceToGraphEdge`, so the space along each edge goes hollow),
`MaterialContent` (the blocks lining the cave, read by a `Graph` **material provider** at the top
of the `MaterialProvider` in `Plains1_Oak`, `Plains1_Hills`, `Plains1_River` and `Plains1_Trork`;
`Plains1_Gorges` carves with the graph but has no `Graph` material provider) and `PropDistributionContent` (cave props, importing
assignments such as `Plains1_Caves_Boulders`, `Plains1_Caves_Stalactites` and
`Plains1_Caves_Crystals_Red` from `Assignments/Plains1/Caves/`).

---

## Volcanic example

`Server/HytaleGenerator/Density/Volcanic1_Caves_Terrain.json` shows the plain-density recipe.
Its root is a `Cache` (capacity 3, `ExportAs` `"Volcanic1_Caves_Terrain"`) wrapping a `Mix` of
three inputs: a `Constant -1`, a `Sum` (of a `CurveMapper`, a `Normalizer` over
`SimplexNoise2D`, and a `Clamp` over `Inverter`-ed noise), and a `CurveMapper` over
`BaseHeight` that bounds the depth band.

`Mix` takes exactly three inputs — `A`, `B`, and an influence field: influence `≤ 0` returns A,
`≥ 1` returns B. That is the whole cave: sculpt a field, then fade it to a constant outside the
depth band. The sheet-like hollows come from a four-point `CurveMapper` inside the `Sum`:

```json
{
  "Type": "CurveMapper",
  "Curve": { "Type": "Manual", "Points": [
    { "In": -0.25, "Out": -1 },
    { "In": -0.02, "Out": 1 },
    { "In":  0.02, "Out": 1 },
    { "In":  0.25, "Out": -1 }
  ]}
}
```

This maps a noise value near zero to `1` and pushes the extremes to `-1`, producing thin sheet-like
hollows along the noise's zero band — and because `Volcanic1_Caldera` inverts the whole field
before its `Min`, those `1`s become the hollows.

---

## Building blocks

The recurring idioms in cave fields:

### Confine carving to a depth band

A `CurveMapper` fed by `BaseHeight` (`Distance: true`) maps altitude to a weight so caves only
appear in a vertical range. From the Plains1 biomes (the `Mix` influence that picks the `Graph`
cave field over `Constant 1`):

```json
{
  "Type": "CurveMapper",
  "Curve": { "Type": "Manual", "Points": [
    { "In": -90, "Out": 0 },
    { "In": -80, "Out": 1 },
    { "In": 20,  "Out": 1 },
    { "In": 30,  "Out": 0 }
  ]},
  "Inputs": [ { "Type": "BaseHeight", "BaseHeightName": "Base", "Distance": true } ]
}
```

This produces `1` (use the cave field) from 80 blocks below `Base` to 20 above it, fading to `0`
(use `Constant 1`, solid) beyond those bounds — walling caves off from bedrock and from the sky.

### Wall pinch with Pow/Abs

`Abs` of noise gives a value near zero along the noise's zero-crossings and larger away from
them; `Pow` sharpens that into a narrow band along the zero line. From
`Volcanic1_Caves_Terrain.json`:

```json
{
  "Type": "Pow", "Exponent": 3,
  "Inputs": [ { "Type": "Abs", "Inputs": [
    { "Type": "SimplexNoise2D", "Lacunarity": 3, "Persistence": 0.15, "Octaves": 2,
      "Scale": 150, "Seed": "O" } ] } ]
}
```

---

## What does NOT exist

The previous version of this document described a fictional cave system. None of these appear in
any asset file and they are not part of the format:

`CaveType`, `CaveNodeType`, `CaveNodeShape` (cylinder/ellipsoid/pipe/etc.),
`CaveNodeChildEntry`/corridors, `CaveNodeCoverEntry`, `CavePrefabContainer`, `CavePopulator`,
`EntryNode`, `PitchRange`/`YawRange`, `FluidLevel`/`FluidType` cave flooding, and the
`Server/WorldGen/Cave/` or `Server/WorldGen/CaveNode/` directories. Caves are density fields —
noise-built under `Server/HytaleGenerator/Density/`, or graph-built under
`Server/HytaleGenerator/GraphGenerators/` — combined into terrain with `Min`. (The graph
generator's nodes and edges are general-purpose: the same machinery lays out
`Plains1_Trork_Camp`.)

Decorations and encounters *inside* caves — boulders, moss, mobs — are placed by props: in the
Plains1 caves through the graph content's `PropDistributionContent`, elsewhere by ordinary prop
`Props[]`/`Assignments` entries. See [worldgen-prefabs.md](worldgen-prefabs.md).

---

## Gotchas

- **`Couldn't find Density asset exported with name: '`** — assembled line `Couldn't find Density asset exported with name: '<name>'. Using empty Node instead.` → an `Imported` cave field names an export nothing publishes, and it becomes a constant `0`. Under a carving `Min` that is not harmless: `Min(surface, 0)` can never exceed `0`, and terrain is solid only where density is `> 0`, so the biome's terrain root cannot produce a solid cell. Three shipped 0.7.2 biomes still import `Plains1_Caves_Terrain`, which no 0.7.2 asset exports: `Desert1_Rocky`, `Desert1_Stacks` and `Experimental/Mountains`. Fix for your own biomes: confirm the name against an `ExportAs` in a loaded file, and re-check imports after a game update removes a field.
- **Symptom:** a `Graph` node whose `GraphGenerator` uses `ImportName` produces no caves and logs nothing → the `ImportName` matches no generator's `ExportName`. `GraphGeneratorAsset` falls back to an empty generator silently, so the field is `BackgroundValue` everywhere. Fix: match `ImportName` to the `ExportName` in `GraphGenerators/*.json` exactly.

---

## Related Documentation

- [Terrain Density Graphs](worldgen-terrain.md) - The density node vocabulary caves reuse
- [World Generation Overview](worldgen.md) - Node-graph system
- [Prefabs / Props](worldgen-prefabs.md) - Placing cave decorations and encounters
