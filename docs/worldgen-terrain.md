---
title: "Terrain Density Graphs"
description: "Shape Hytale terrain with JSON density node graphs — per-biome DAOTerrain heightfields, density combiners (Sum/Min/Max/Mix), noise sources, and shaping nodes."
seo:
  type: TechArticle
---

# Terrain Density Graphs

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.7.2**

Hytale terrain is **not** built from a stack of fixed/variable "layers". It is produced by a
**node graph of density functions**. Each biome owns a `DAOTerrain` node whose `Density` input is
a tree of math/noise nodes that, evaluated per world position, yields a scalar **density** value.
Where density is `> 0` the world is solid; where it is `<= 0` the world is empty (air/fluid)
(`TerrainStage`: `solidity = density > 0.0` — the boundary value `0` is *empty*).
A separate `MaterialProvider` then decides *which* block fills each solid (or empty) cell.

This document describes the real format used by the asset files under
`Server/HytaleGenerator/`.

## Overview

Defined as JSON density node graphs under `Server/HytaleGenerator/` and provides:
- A per-biome `DAOTerrain` node whose `Density` graph yields a scalar heightfield
- Density combiners (`Sum`/`Min`/`Max`/`Mix`) and unary math over noise sources
- Noise nodes (`SimplexNoise2D`/`3D`, `CellNoise2D`) as the field sources
- Shaping via `CurveMapper`, `Normalizer`, `Pow`, `Abs`, `Clamp`
- `BaseHeight` references to surface/bedrock for altitude-driven shaping
- Field reuse via `Cache` / `Exported` / `Imported`
- A `MaterialProvider` that turns density into block ids

## Architecture
```
Biome Terrain (DAOTerrain)
└── Density graph (scalar field; > 0 solid, <= 0 empty)
    ├── Combiners   Sum / Min / Max / Mix
    ├── Sources     SimplexNoise2D / SimplexNoise3D / CellNoise2D
    ├── Shaping     CurveMapper / Normalizer / Pow / Abs / Clamp
    ├── BaseHeight  Base / Water / Bedrock reference (+ Distance)
    └── Reuse       Cache / Exported / Imported (e.g. cave field via Min)

MaterialProvider (Solidity)
├── Solid  Queue / SpaceAndDepth / SimpleHorizontal / FieldFunction / Constant
└── Empty  (air + fluids)
```

## Key Classes
These are JSON worldgen node types (not Java classes); the table lists the key node types documented on this page.

| Node type | Family | Description |
|-----------|--------|-------------|
| `DAOTerrain` | Entry point | Biome terrain node; wraps the root `Density` graph |
| `Sum` / `Min` / `Max` / `Mix` | Combiner | Add / clip / union / blend input fields |
| `Abs` / `Inverter` / `Pow` / `Constant` | Unary math | Reshape or supply a fixed value |
| `Normalizer` / `Clamp` | Range remap | Linearly remap or clamp a field |
| `SimplexNoise2D` / `SimplexNoise3D` / `CellNoise2D` | Noise source | The scalar field sources |
| `CurveMapper` / `Distance` | Shaping | Map a value through a `Manual` curve |
| `BaseHeight` | Reference | Inject a named reference height (`Base` / `Water` / `Bedrock`) |
| `Cache` / `Exported` / `Imported` | Reuse | Memoize, publish, and pull fields by name |
| `Solidity` | Material provider | Routes solid cells and empty cells to providers |
| `SpaceAndDepth` / `ConstantThickness` | Material provider | Stack material layers by depth into the floor |
| `FieldFunction` | Material provider | Select material by a sampled density range |

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Where terrain lives](#where-terrain-lives) | Canonical asset paths |
| [Node anatomy](#node-anatomy) | `$NodeId`, `Type`, `Inputs`, `Skip` |
| [The DAOTerrain node](#the-daoterrain-node) | Biome terrain entry point |
| [Density node families](#density-node-families) | Sum / Min / Max / Mix / noise / curves |
| [Noise nodes](#noise-nodes) | SimplexNoise2D / 3D and parameters |
| [Shaping nodes](#shaping-nodes) | CurveMapper, Normalizer, Pow, Abs, Clamp |
| [BaseHeight](#baseheight) | Referencing surface / bedrock height |
| [Reuse: Cache, Exported, Imported](#reuse-cache-exported-imported) | Sharing fields across graphs |
| [MaterialProvider](#materialprovider) | Turning density into blocks |
| [Worked example](#worked-example-plains1_oak) | Plains1_Oak terrain |

---

## Where terrain lives

| Content | Path |
|---------|------|
| Biome definitions (contain `Terrain`) | `Server/HytaleGenerator/Biomes/**/<Biome>.json` |
| Shared / map-level density fields | `Server/HytaleGenerator/Density/*.json` |
| Generator settings | `Server/HytaleGenerator/Settings/Settings.json` |

A biome file (for example `Server/HytaleGenerator/Biomes/Plains1/Plains1_Oak.json`) has this
top-level shape:

```json
{
  "$NodeId": "Biome-fb9c6a20-0178-4045-86db-b9c078e694bc",
  "Name": "Hills",
  "Terrain":             { "...": "DAOTerrain node, see below" },
  "MaterialProvider":    { "...": "material provider graph, see below" },
  "Props":               [ "...prop placement entries..." ],
  "EnvironmentProvider": { "...": "see worldgen-biomes.md" },
  "TintProvider":        { "...": "see worldgen-biomes.md" }
}
```

The standalone files in `Density/` (such as `Maps/Map_Default.json`,
`Volcanic1_Caves_Terrain.json` and the `Base_Simplex/` noise bank) are density graphs that are
*exported by name* and then *imported* into biome terrain graphs.

---

## Node anatomy

Every node in every graph is an object with at minimum:

| Field | Type | Description |
|-------|------|-------------|
| `$NodeId` | string | Unique id, e.g. `"SumDensityNode-15164002-..."`. Editor-assigned. |
| `Type` | string | Node kind, e.g. `"Sum"`, `"SimplexNoise2D"`, `"CurveMapper"`. |
| `Inputs` | array | Child density nodes feeding this node (order matters for some types). |
| `Skip` | bool | When `true` the node is bypassed. Present on most density nodes. |

Optional fields seen on nodes:

| Field | Meaning |
|-------|---------|
| `ExportAs` | Publishes this node's value under a name other graphs can `Imported`. |
| `SingleInstance` | Evaluate once and share the result. |
| `$NodeEditorMetadata` | Editor-only: node positions, groups, comments. **Ignored at runtime.** |

> The deeply nested `Inputs` arrays in the asset files are how the graph edges are stored — there
> is no separate adjacency list. A node's children are literally nested inside its `Inputs`.

---

## The DAOTerrain node

A biome's `Terrain` is a single node of `Type: "DAOTerrain"`. Its one meaningful field is
`Density`, the root of the density graph:

```json
"Terrain": {
  "$NodeId": "Terrain.Biome-d4edd770-d325-42c5-99b7-335d50d612de",
  "Type": "DAOTerrain",
  "Density": {
    "Type": "Min",
    "Skip": false,
    "Inputs": [
      { "Type": "Mix", "Inputs": [ "...the surface field..." ] },
      { "Type": "YSampled", "SampleDistance": 3, "SampleOffset": 0, "Interpolate": true,
        "Inputs": [ { "Type": "Mix", "Inputs": [
          { "Type": "Constant", "Value": 1 },
          { "Type": "Graph", "GraphGenerator": { "ImportName": "Plains1_Caves" }, "...": "..." },
          { "Type": "CurveMapper", "...": "depth band over BaseHeight" }
        ] } ] }
    ]
  }
}
```

The example above (abridged from `Plains1_Oak.json`) is the canonical terrain pattern: the
biome's own surface field (a `Mix`) is combined via `Min` with a cave field. `Min` keeps
whichever value is smaller, so wherever the cave field goes negative it carves the solid
terrain away. In the Plains1 biomes the cave field is a `Graph` density node fed by the
`Plains1_Caves` graph generator, faded to `Constant 1` (solid) outside a depth band; other
biomes import a plain density field instead. See [worldgen-caves.md](worldgen-caves.md) for
the cave side.

---

## Density node families

These are the node `Type` values observed across `Density/` and biome `Terrain` graphs. All take
their children in `Inputs` unless noted. (The generator registers many more density types — comparators,
logic gates, smooth min/max, shapes, 3D/cell/white noise, warps, position-driven fields — see the
full list in [worldgen.md](worldgen.md#density-nodes-the-core); each one is a
`*DensityAsset` class in `com.hypixel.hytale.builtin.hytalegenerator.assets.density`, whose
codec keys are the JSON keys.)

### Combiners

| Type | Behavior |
|------|----------|
| `Sum` | Adds all input values. |
| `Min` | Smallest of inputs. Used to carve (caves) and to clip terrain. |
| `Max` | Largest of inputs. Used to union shapes (raise terrain). |
| `Mix` | Linear blend of **exactly three** inputs — `Inputs[0]` = A, `Inputs[1]` = B, `Inputs[2]` = the influence field. Influence `≤ 0` returns A, `≥ 1` returns B, otherwise `A·(1−t) + B·t`. |

### Unary math

| Type | Fields | Behavior |
|------|--------|----------|
| `Abs` | — | Absolute value of input (used to make ridges from noise). |
| `Inverter` | — | Negates the input. |
| `Pow` | `Exponent` | Raises input to a power (sharpens/softens a field). |
| `Constant` | `Value` | A fixed value, no inputs. |

### Range remapping

| Type | Fields | Behavior |
|------|--------|----------|
| `Normalizer` | `FromMin`, `FromMax`, `ToMin`, `ToMax` | Linearly remaps `[FromMin,FromMax]` to `[ToMin,ToMax]`. |
| `Clamp` | `WallA`, `WallB` | Clamps the input between the two walls. |

Real `Normalizer` from `Density/Maps/Map_Default.json`:

```json
{
  "Type": "Normalizer",
  "FromMin": -1, "FromMax": 1,
  "ToMin": -0.5, "ToMax": 1,
  "Inputs": [ { "Type": "SimplexNoise2D", "Lacunarity": 5, "Persistence": 0.3, "Octaves": 2,
                "Scale": 1000, "Seed": "World-Continent-Map-B" } ]
}
```

---

## Noise nodes

### SimplexNoise2D

The workhorse. Produces a height-independent 2D noise field.

| Field | Type | Notes |
|-------|------|-------|
| `Lacunarity` | number | Frequency multiplier per octave. |
| `Persistence` | number | Amplitude falloff per octave. |
| `Octaves` | int | Number of fractal octaves. |
| `Scale` | number | Feature size in blocks (larger = broader features). |
| `Seed` | **string** | Seed label, e.g. `"A"`, `"Plains1_Oak"`, `"Cave-Floor"`. Note it is a string, not a number. |

```json
{
  "Type": "SimplexNoise2D",
  "ExportAs": "Plains1_Oak",
  "Lacunarity": 4.2,
  "Persistence": 0.12,
  "Octaves": 3,
  "Scale": 200,
  "Seed": "Plains1_Oak"
}
```

(From `Plains1_Oak.json`, which exports it so later nodes in the same biome can `Imported` it.)

### SimplexNoise3D

Volumetric noise (used for ore veins, e.g. `Assignments/Desert1/Desert1_Iron.json`). Same
parameters but with separate horizontal/vertical scale:

```json
{
  "Type": "SimplexNoise3D",
  "Lacunarity": 2, "Persistence": 0.5, "Octaves": 1,
  "ScaleXZ": 4, "ScaleY": 4,
  "Seed": "A"
}
```

### CellNoise2D

Voronoi/cellular noise, seen in prop placement (e.g. a positions gate in `Plains1_Oak.json`'s
`Props`) and in `Plains1_Hills.json`. Fields: `ScaleX`, `ScaleZ`, `Jitter`, `CellType`
(e.g. `"Distance2Div"`), `Octaves`, `Seed`.

---

## Shaping nodes

### CurveMapper

Maps an input value through a curve. The curve is a child object of `Type: "Manual"` whose
`Points` are `{ "In": x, "Out": y }` pairs. The mapper interpolates between the points.

```json
{
  "Type": "CurveMapper",
  "Curve": {
    "Type": "Manual",
    "Points": [
      { "In": 0,   "Out": 1 },
      { "In": 0.1, "Out": -1 }
    ]
  },
  "Inputs": [ { "Type": "BaseHeight", "BaseHeightName": "Base", "Distance": true } ]
}
```

This is how terrain is shaped by altitude: feed `BaseHeight` into a `CurveMapper` so density
falls off above some height, producing a surface. The curve above (from `Plains1_Oak.json`)
is a flat surface exactly at `Base`: solid below, empty above.

### Distance

Seen in `Density/Maps/Map_Portals.json` as the island-shaping node of the portal worlds; it
carries its own `Curve` (a `Manual` curve mapping distance-in to density-out).

---

## BaseHeight

`BaseHeight` injects a reference height into the graph instead of noise.

| Field | Notes |
|-------|-------|
| `BaseHeightName` | Named constant declared by the world structure's `DecimalConstants` block. The three height names are used across the assets: `"Base"` (the terrain surface, 461 uses), `"Water"` (sea level, 61) and `"Bedrock"` (44), counted on live nodes under `Server/HytaleGenerator` (orphan nodes kept in `$NodeEditorMetadata` excluded). Any constant can be read this way: the five Plains1 biomes read the non-height constants `"Copper_Count"` and `"Iron_Count"` (10 uses each). |
| `Distance` | When `true`, yields signed distance from that reference rather than the raw height. |

```json
{ "Type": "BaseHeight", "BaseHeightName": "Base", "Distance": true }
```

Feeding `BaseHeight` (`Distance: true`) into a `CurveMapper` is the standard way to make a field
that is positive below the surface and negative above it.

---

## Reuse: Cache, Exported, Imported

Large graphs avoid recomputation and share fields with three node types:

| Type | Fields | Purpose |
|------|--------|---------|
| `Cache` | `Capacity` | Memoizes its input's result (cache size = `Capacity`). `Cache2D` is a deprecated alias. |
| `Exported` | `ExportAs`, `SingleInstance` | Publishes its input under a name. Also appears as an `ExportAs` field directly on other nodes. |
| `Imported` | `Name` | Pulls in a previously exported field by name. |
| `YOverride` | `Value` | Forces the Y coordinate to a constant (used to make a 3D field behave as a flat 2D field). |
| `Scale` | `ScaleX`, `ScaleY`, `ScaleZ` | Scales the sampling coordinates. |
| `YSampled` | `SampleDistance`, `SampleOffset`, `Interpolate` | Evaluates its input only on a Y grid (every `SampleDistance` blocks, shifted by `SampleOffset`) and, with `Interpolate: true`, interpolates linearly between the two nearest samples. A `SampleDistance` of `0` or less makes it a constant `0`. The Plains1 biomes wrap their surface and cave fields in it. |

Example: `Volcanic1_Caldera.json` imports the shared volcanic cave density, and
`Density/Maps/Map_Default.json` exports the biome map:

```json
{ "Type": "Imported", "Name": "Volcanic1_Caves_Terrain" }
```

```json
{ "Type": "Exported", "ExportAs": "Biome-Map", "SingleInstance": true, "Inputs": [ ... ] }
```

---

## MaterialProvider

The density graph decides *where* terrain is solid. The biome's `MaterialProvider` decides *what
block* goes there. In 66 of the 75 shipped biome files the top-level provider is
`Type: "Solidity"`, splitting into a `Solid` provider and an `Empty` provider. Seven put a
`Queue` on top that ends in a `Solidity` provider — in `Plains1_Oak`, `Plains1_Hills`,
`Plains1_River` and `Plains1_Trork` the entry before it is a `Graph` provider supplying the
cave materials — and two (`Void`, `Default_Void`) are a bare `Constant`:

```json
"MaterialProvider": {
  "Type": "Solidity",
  "Solid": { "Type": "Queue", "Queue": [ ... ] },
  "Empty": { "Type": "Queue", "Queue": [ ... ] }
}
```

### Provider types observed

| Type | Fields | Purpose |
|------|--------|---------|
| `Solidity` | `Solid`, `Empty` | Routes to one provider for solid cells, another for empty cells. |
| `Queue` | `Queue[]` | Tries each provider in order; first match wins. |
| `SimpleHorizontal` | `TopY`, `TopBaseHeight`, `BottomY`, `BottomBaseHeight`, `Material` | Applies its material only in a vertical band defined relative to a named base height. |
| `SpaceAndDepth` | `LayerContext` (`DEPTH_INTO_FLOOR` or `DEPTH_INTO_CEILING`), `MaxExpectedDepth`, `Layers[]`, optional `Condition` | Stacks layers measured by depth into the floor (or up into the ceiling) — this is the closest real analogue to "soil layers". |
| `ConstantThickness` (layer) | `Thickness`, `Material` | One band of material `Thickness` blocks deep. The layer type nearly every shipped biome uses (39 files). |
| `FieldFunction` | `FieldFunction` (a density node), `Delimiters[]` | Selects material based on a noise/density value falling inside a `From`/`To` range. Used for scattered surface variation (pebbles, leaves, grass patches). |
| `Constant` | `Material` | A single fixed material. |

The other registered `Layers[]` entry types (as of 0.7.2) are `NoiseThickness`
(`ThicknessFunctionXZ` + `Material` — thickness driven by a density field; used by
`Plains1_Oak`, `Plains1_Hills` and `Plains1_River`), `RangeThickness` (`RangeMin`,
`RangeMax`, `Seed`, `Material` — a random thickness per column; used only by
`Experimental/BasicForest.json`) and `WeightedThickness` (`PossibleThicknesses` of
`Weight`/`Thickness`, plus `Seed`, `Material`; unused). A `Condition` on the `SpaceAndDepth` gates the whole stack; its
predicate types are `AlwaysTrueCondition`, `EqualsCondition`, `GreaterThanCondition`,
`SmallerThanCondition`, `AndCondition`, `OrCondition` and `NotCondition`, reading the
parameters `SPACE_ABOVE_FLOOR` / `SPACE_BELOW_CEILING`.

Also registered (as of 0.7.2, mostly unused by the shipped biomes): `Weighted`
(`WeightedMaterials` with `Weight`/`Material`, `SkipChance`, `Seed`), `Striped` (`Stripes`
between `TopY`/`BottomY`), `UpwardDepth`/`DownwardDepth` (`Depth` + `Material`),
`UpwardSpace`/`DownwardSpace` (`Space` + `Material`), `TerrainDensity` (`Delimiters` over the
terrain density itself), `Transparent`, `Imported` (`Name`), and `Graph` (`GraphGenerator`,
`ContentLayer`, `QueryBufferCapacity` — materials supplied by a graph generator's content,
which is how the Plains1 cave walls get their blocks).

### Materials

A `Material` node names a block via one of:

| Key | Meaning | Examples |
|-----|---------|----------|
| `Solid` | A solid block id | `Rock_Stone`, `Rock_Bedrock`, `Rock_Marble`, `Soil_Dirt`, `Soil_Grass`, `Soil_Grass_Sunny`, `Soil_Pebbles`, `Soil_Leaves`, `Soil_Pathway`, `Ore_Iron_Stone`, `Empty` |
| `Fluid` | A fluid id | `Water_Source` |
| `SolidBottomUp` | Optional boolean: place the solid block flipped upside down (default `false`; ignored when `SolidRotation` is set) | — |
| `SolidRotation` | Optional orthogonal rotation for the solid block | — |

`Empty` is itself a valid `Solid` value meaning "no block" — note the `"$Comment": "REQUIRED"`
on the trailing `Empty` constant in the `Empty` queue of `Biomes/Basic.json` (and most other
biomes that end their `Empty` queue that way).

Real soil stack from `Plains1_Oak.json` (a `SpaceAndDepth` with a one-block surface layer over a
noise-driven dirt layer 1–6 blocks thick):

```json
{
  "Type": "SpaceAndDepth",
  "LayerContext": "DEPTH_INTO_FLOOR",
  "MaxExpectedDepth": 6,
  "Layers": [
    { "Type": "ConstantThickness", "Thickness": 1, "Material": { "...": "a grass/pebble Queue of FieldFunction providers" } },
    { "Type": "NoiseThickness",
      "ThicknessFunctionXZ": { "Type": "Normalizer", "FromMin": -1, "FromMax": 1, "ToMin": 1, "ToMax": 6,
        "Inputs": [ { "Type": "SimplexNoise2D", "Lacunarity": 2, "Persistence": 0.5, "Octaves": 1, "Scale": 20, "Seed": "Plains1_Dirt" } ] },
      "Material": { "Type": "Constant", "Material": { "Solid": "Soil_Dirt" } } }
  ]
}
```

---

## Worked example: Plains1_Oak

`Server/HytaleGenerator/Biomes/Plains1/Plains1_Oak.json` builds its surface like this (simplified
from the real file — the actual graph is hundreds of nested nodes):

```
DAOTerrain.Density
└─ Min
   ├─ Mix                                         (the surface)
   │  ├─ A: Max / Min of YSampled Sums of normalized SimplexNoise2D fields
   │  │      (Seeds "Plains1_Oak", "Plains1_Oak_Random", "Plains1_Oak_Random2",
   │  │       "Plains1_Oak_Plains", "Plains1_Oak_Cliifs", "Plains1_Oak_Dips", …)
   │  ├─ B: CurveMapper( BaseHeight Base, Distance )   flat surface at Base
   │  └─ influence: CurveMapper( BaseHeight Base, Distance )
   │        points -10→1, 0→0, 35→0, 45→1: the band 0–35 blocks above Base uses A
   └─ YSampled → Mix                              (the caves)
      ├─ Constant 1
      ├─ Graph  (GraphGenerator ImportName "Plains1_Caves")
      └─ CurveMapper( BaseHeight Base, Distance )  depth band -80…20 around Base
```

Slope-dependent surface materials come from the `MaterialProvider`, not from the terrain
graph: a `FieldFunction` provider samples an `Angle` density (between the up vector and a
`DensityGradient` vector provider over a `Terrain` density node, which reads the biome's own
terrain field) and applies the grass/dirt `SpaceAndDepth` stack only where that angle is
0–55°. This is the real mechanism that the old docs incorrectly described as "slope
conditions" on layers.

---

## What does NOT exist

The previous version of this document described a fictional schema. None of the following appear
in any asset file and they are not part of the format:

`LayerContainer`, `Filling`, `StaticLayers`, `DynamicLayers`, `SubsurfaceLayers`,
`HeightSupplier` (and the `Constant`/`Perlin`/`Simplex`/`Voronoi`/`Ridged`/`Compound` supplier
"Type"s), per-layer `Conditions` with `SlopeMin`/`SlopeMax`/`HeightMin`, and the
`BlockPopulator`/`BlockPriorityChunk` priority table. Terrain is the density graph plus a
`MaterialProvider`, nothing more.

---

## Gotchas & Errors

Backtick-quoted strings below are the literal messages the density-asset codecs emit
(verified against `HytaleServer.jar` 0.7.2). Codec **validator failures** reject the asset
at load; **warnings** let generation continue with a degraded node, so they are easy to
miss — watch the server log.

Validator failures (`Validators`/`results.fail`, asset is rejected):

- **`FromMin must be less than FromMax. Given: `** / **`ToMin must be less than ToMax. Given: `** — assembled lines `FromMin must be less than FromMax. Given: <fromMin> and <fromMax>` (and the `ToMin`/`ToMax` twin) → a `Normalizer` node's range is **inverted** (`FromMin > FromMax`). Fix: order each pair strictly ascending. A *degenerate* pair (`FromMin == FromMax`) is only a warning today, with a different literal: **`FromMin must be less than FromMax. This will fail to load in future versions. Given: `** — so equal bounds still load in 0.7.2 but are on notice.
- **`Inputs can't be empty. Anchor offsets its first input.`** → an `Anchor` density node with no `Inputs`. Fix: give it at least one input.
- **`Keys must have unique Value entries. Keys[`** — assembled line `Keys must have unique Value entries. Keys[<j>] and Keys[<i>] both use <value>` → two `MultiMix` `Keys` entries share a `Value`. Fix: make every key's `Value` distinct.
- **`Vector must have all components greater than 0, got `** — assembled line appends the offending vector → a vector-valued parameter (e.g. a scale) has a zero or negative component (`VectorAssetValidatorUtil`).
- **`String not a valid enum value: `** — assembled line appends the provided string → an enum-typed key (`CellType`, `LayerContext`, a `Rotation`, …) got a name the enum does not define (`assets.ValidatorUtil`).

Silent degradations (no message at all — the worst kind):

- **A `Mix` node without exactly three non-skipped `Inputs` becomes constant `0`.** `MixDensityAsset.build` returns a `ConstantValueDensity(0)` rather than failing, and `Skip: true` on a child *removes* it from the count — so skipping one input of a `Mix` silently zeroes the whole subtree instead of passing the others through.

Warnings (generation continues, node degrades):

- **`Couldn't find Density asset exported with name: '`** — assembled line `Couldn't find Density asset exported with name: '<name>'. Using empty Node instead.` → an `Imported` node names a field nothing `ExportAs`-ed, and the import degrades to a constant `0`. Fix: check the exporting graph is loaded and the names match exactly. The other graph kinds have their own literals with the same shape: **`Couldn't find Assignments asset exported with name: '`**, **`Couldn't find Positions asset exported with name: '`**, **`Couldn't find VectorProvider asset exported with name: '`** and **`Couldn't find ReturnType asset exported with name: '`** (that last one ends `. Using a return type that only outputs 0 instead.`).
- **`Duplicate export name for asset: `** — assembled line appends the export name → two nodes used the same `ExportAs`; the later registration wins. Fix: keep export names unique across *all* loaded graphs — the export table is global.
- **`Density Index out of bounds in MultiMix node `** — assembled line `Density Index out of bounds in MultiMix node <index>, valid range is [0, <n>]` (the second literal fragment is `, valid range is [0, `) → a `MultiMix` `Keys` entry's `DensityIndex` does not address an input; that key is dropped. Note the jar rejects `DensityIndex == n` even though the message advertises `[0, n]` — usable indices stop one short of the last input.
- **Symptom:** you added a `LayerContainer`, `StaticLayers`/`DynamicLayers`, a `HeightSupplier` `Type`, or per-layer `Conditions`/`SlopeMin` and they are ignored → none of those exist in the format. Fix: terrain is the `Density` node graph plus a `MaterialProvider` (see [What does NOT exist](#what-does-not-exist)).

> The `Number of noises must match number of thresholds` /
> `Thresholds must be in ascending order and cannot be equal` /
> `Threshold array must contain at least one entry!` messages that older versions of this
> page listed come from `com.hypixel.hytale.procedurallib.json` — the **legacy** folder-of-JSON
> generator behind `WorldGen.Type: "Hytale"`, not from these density assets.

---

## Related Documentation

- [World Generation Overview](worldgen.md) - Node-graph system and shared vocabulary
- [Caves](worldgen-caves.md) - Cave density fields subtracted from terrain
- [Prefabs / Props](worldgen-prefabs.md) - Placing structures and decorations
