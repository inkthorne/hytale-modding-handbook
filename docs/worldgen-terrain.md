---
title: "Terrain Density Graphs"
description: "Shape Hytale terrain with JSON density node graphs — per-biome DAOTerrain heightfields, density combiners (Sum/Min/Max/Mix), noise sources, and shaping nodes."
seo:
  type: TechArticle
---

# Terrain Density Graphs

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.5.9**

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
  "Terrain":          { "...": "DAOTerrain node, see below" },
  "MaterialProvider": { "...": "Solidity provider, see below" },
  "Props":            [ "...prop placement entries..." ]
}
```

The standalone files in `Density/` (such as `Map_Default.json`,
`Plains1_Caves_Terrain.json`) are density graphs that are *exported by name* and then *imported*
into biome terrain graphs.

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
  "$NodeId": "Terrain-d4edd770-d325-42c5-99b7-335d50d612de",
  "Type": "DAOTerrain",
  "Density": {
    "$NodeId": "MinDensityNode-c9a8caa1-...",
    "Type": "Min",
    "Skip": false,
    "Inputs": [
      { "Type": "Imported", "Name": "Plains1_Caves_Terrain" },
      { "Type": "Mix", "ExportAs": "Plains1_Oak_Terrain_Field", "Inputs": [ ... ] }
    ]
  }
}
```

The example above (from `Plains1_Oak.json`) is the canonical terrain pattern: take the biome's
own surface field (a `Mix` exported as `Plains1_Oak_Terrain_Field`) and combine it via `Min`
with an imported cave density (`Plains1_Caves_Terrain`). `Min` keeps whichever value is smaller,
so wherever the cave field goes negative it carves the solid terrain away. See
[worldgen-caves.md](worldgen-caves.md) for the cave side.

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

Real `Normalizer` from `Map_Default.json`:

```json
{
  "Type": "Normalizer",
  "FromMin": -1, "FromMax": 1,
  "ToMin": -0.85, "ToMax": 0.85,
  "Inputs": [ { "Type": "SimplexNoise2D", "Scale": 1500, "Seed": "A" } ]
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
  "$NodeId": "SimplexNoise2DDensityNode-f2c2a89e-...",
  "Type": "SimplexNoise2D",
  "Lacunarity": 5,
  "Persistence": 0.08,
  "Octaves": 3,
  "Scale": 400,
  "Seed": "Plains1_Oak"
}
```

### SimplexNoise3D

Volumetric noise (used for ore veins and 3D carving). Same parameters but with separate
horizontal/vertical scale:

```json
{
  "Type": "SimplexNoise3D",
  "Lacunarity": 2, "Persistence": 0.5, "Octaves": 1,
  "ScaleXZ": 4, "ScaleY": 4,
  "Seed": "A"
}
```

### CellNoise2D

Voronoi/cellular noise, seen in material selection (e.g. `Plains1_Oak.json` boulder pebbles).
Fields observed: `ScaleX`, `ScaleZ`, `Jitter`, `CellType` (e.g. `"Distance2Div"`), `Octaves`,
`Seed`.

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
      { "In": -5, "Out": 1 },
      { "In": 40, "Out": -1 }
    ]
  },
  "Inputs": [ { "Type": "BaseHeight", "BaseHeightName": "Base", "Distance": true } ]
}
```

This is how terrain is shaped by altitude: feed `BaseHeight` into a `CurveMapper` so density
falls off above some height, producing a surface.

### Distance

Seen in `Map_Default.json` as a continent-shaping node; it carries its own `Curve` (a `Manual`
curve mapping distance-in to density-out).

---

## BaseHeight

`BaseHeight` injects a reference height into the graph instead of noise.

| Field | Notes |
|-------|-------|
| `BaseHeightName` | Named reference declared by the world structure's `DecimalConstants` block. All three shipped names are used across the assets: `"Base"` (the terrain surface, 621 uses), `"Water"` (sea level, 99) and `"Bedrock"` (35). |
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

Example: `Plains1_Oak.json` imports the shared cave density and the map exports the biome map:

```json
{ "Type": "Imported", "Name": "Plains1_Caves_Terrain" }
```

```json
{ "Type": "Exported", "ExportAs": "Biome-Map", "SingleInstance": true, "Inputs": [ ... ] }
```

---

## MaterialProvider

The density graph decides *where* terrain is solid. The biome's `MaterialProvider` decides *what
block* goes there. The top-level provider is `Type: "Solidity"`, splitting into a `Solid` provider
and an `Empty` provider:

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
| `ConstantThickness` (layer) | `Thickness`, `Material` | One band of material `Thickness` blocks deep. The only layer type the shipped biomes use. |

The other registered `Layers[]` entry types (as of 0.6.3) are `NoiseThickness`
(`ThicknessFunctionXZ` + `Material` — thickness driven by a density field),
`RangeThickness` (`RangeMin`, `RangeMax`, `Seed`, `Material` — a random thickness per
column) and `WeightedThickness` (`PossibleThicknesses` of `Weight`/`Thickness`, plus
`Seed`, `Material`). A `Condition` on the `SpaceAndDepth` gates the whole stack; its
predicate types are `AlwaysTrueCondition`, `EqualsCondition`, `GreaterThanCondition`,
`SmallerThanCondition`, `AndCondition`, `OrCondition` and `NotCondition`, reading the
parameters `SPACE_ABOVE_FLOOR` / `SPACE_BELOW_CEILING`.
| `FieldFunction` | `FieldFunction` (a density node), `Delimiters[]` | Selects material based on a noise/density value falling inside a `From`/`To` range. Used for scattered surface variation (pebbles, leaves, grass patches). |
| `Constant` | `Material` | A single fixed material. |

Also registered (as of 0.6.3, mostly unused by the shipped biomes): `Weighted`
(`WeightedMaterials` with `Weight`/`Material`, `SkipChance`, `Seed`), `Striped` (`Stripes`
between `TopY`/`BottomY`), `UpwardDepth`/`DownwardDepth` (`Depth` + `Material`),
`UpwardSpace`/`DownwardSpace` (`Space` + `Material`), `TerrainDensity` (`Delimiters` over the
terrain density itself), `Transparent`, `Imported` (`Name`), and `Graph` (`GraphGenerator` +
`ContentLayer`, for graph-generator content).

### Materials

A `Material` node names a block via one of:

| Key | Meaning | Examples |
|-----|---------|----------|
| `Solid` | A solid block id | `Rock_Stone`, `Rock_Bedrock`, `Rock_Marble`, `Soil_Dirt`, `Soil_Grass`, `Soil_Grass_Sunny`, `Soil_Pebbles`, `Soil_Leaves`, `Soil_Pathway`, `Ore_Iron_Stone`, `Empty` |
| `Fluid` | A fluid id | `Water_Source` |

`Empty` is itself a valid `Solid` value meaning "no block" — note the `"$Comment": "REQUIRED"`
on the trailing `Empty` constant in the `Empty` queue of `Plains1_Oak.json`.

Real soil stack from `Plains1_Oak.json` (a `SpaceAndDepth` with two `ConstantThickness` layers):

```json
{
  "Type": "SpaceAndDepth",
  "LayerContext": "DEPTH_INTO_FLOOR",
  "MaxExpectedDepth": 3,
  "Layers": [
    { "Type": "ConstantThickness", "Thickness": 1, "Material": { "...": "a grass/pebble Queue of FieldFunction providers" } },
    { "Type": "ConstantThickness", "Thickness": 2, "Material": { "Type": "Constant", "Material": { "Solid": "Soil_Dirt" } } }
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
   ├─ Imported "Plains1_Caves_Terrain"          (carves caves)
   └─ Mix  (ExportAs "Plains1_Oak_Terrain_Field")
      └─ Max / Max / Min of several fields:
         ├─ Sum of cached, normalized SimplexNoise2D fields
         │   (Seeds "Plains1_Oak", "Plains1_Oak_Random", "Plains1_Oak_Plains", "Plains1_Oak_Cliifs")
         ├─ CurveMapper( BaseHeight Base, Distance ) curves       (height falloff -> surface)
         └─ Pow / Normalizer / Abs reshaping of the noise
```

The exported name `Plains1_Oak_Terrain_Field` is later imported by the `MaterialProvider`
(via a `DensityGradient` vector provider) to compute slope and pick surface materials. This is the
real mechanism that the old docs incorrectly described as "slope conditions" on layers.

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
(verified against `HytaleServer.jar` 0.6.3). Codec **validator failures** reject the asset
at load; **warnings** let generation continue with a degraded node, so they are easy to
miss — watch the server log.

Validator failures (`Validators`/`results.fail`, asset is rejected):

- **`FromMin must be less than FromMax. Given: `** / **`ToMin must be less than ToMax. Given: `** — assembled lines `FromMin must be less than FromMax. Given: <fromMin> and <fromMax>` (and the `ToMin`/`ToMax` twin) → a `Normalizer` node's range is **inverted** (`FromMin > FromMax`). Fix: order each pair strictly ascending. A *degenerate* pair (`FromMin == FromMax`) is only a warning today, with a different literal: **`FromMin must be less than FromMax. This will fail to load in future versions. Given: `** — so equal bounds still load in 0.6.3 but are on notice.
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
