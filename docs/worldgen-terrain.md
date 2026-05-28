---
title: "Terrain Density Graphs"
description: "Shape Hytale terrain with JSON density node graphs — per-biome DAOTerrain heightfields, density combiners (Sum/Min/Max/Mix), noise sources, and shaping nodes."
seo:
  type: TechArticle
---

# Terrain Density Graphs

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.5.2**

Hytale terrain is **not** built from a stack of fixed/variable "layers". It is produced by a
**node graph of density functions**. Each biome owns a `DAOTerrain` node whose `Density` input is
a tree of math/noise nodes that, evaluated per world position, yields a scalar **density** value.
Where density is `>= 0` the world is solid; where it is `< 0` the world is empty (air/fluid).
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
└── Density graph (scalar field; >= 0 solid, < 0 empty)
    ├── Combiners   Sum / Min / Max / Mix
    ├── Sources     SimplexNoise2D / SimplexNoise3D / CellNoise2D
    ├── Shaping     CurveMapper / Normalizer / Pow / Abs / Clamp
    ├── BaseHeight  Base / Bedrock reference (+ Distance)
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
| `BaseHeight` | Reference | Inject a named reference height (`Base` / `Bedrock`) |
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
their children in `Inputs` unless noted.

### Combiners

| Type | Behavior |
|------|----------|
| `Sum` | Adds all input values. |
| `Min` | Smallest of inputs. Used to carve (caves) and to clip terrain. |
| `Max` | Largest of inputs. Used to union shapes (raise terrain). |
| `Mix` | Blends inputs; commonly the first input is the value field and later inputs modulate it. Seen mixing noise fields together and mixing in `Constant` values. |

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
| `BaseHeightName` | Named reference, observed values: `"Base"` (the terrain surface) and `"Bedrock"`. |
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
| `Cache` | `Capacity` | Memoizes its input's result (cache size = `Capacity`). |
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
| `SpaceAndDepth` | `LayerContext`, `MaxExpectedDepth`, `Layers[]`, optional `Condition` | Stacks `ConstantThickness` layers measured by depth into the floor — this is the closest real analogue to "soil layers". |
| `ConstantThickness` (layer) | `Thickness`, `Material` | One band of material `Thickness` blocks deep. |
| `FieldFunction` | `FieldFunction` (a density node), `Delimiters[]` | Selects material based on a noise/density value falling inside a `From`/`To` range. Used for scattered surface variation (pebbles, leaves, grass patches). |
| `Constant` | `Material` | A single fixed material. |

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
    { "Type": "ConstantThickness", "Thickness": 1, "Material": { "...": "grass/pebble FieldFunction queue" } },
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

Backtick-quoted error strings below are the literal messages thrown by the build-12 density-graph loader (verified against `HytaleServer.jar`).

- **`Number of noises must match number of thresholds`** → a threshold-selecting density node has unequal counts of noise inputs and threshold values. Fix: supply one threshold boundary per noise band.
- **`Threshold array must contain at least one entry!`** → an empty threshold array. Fix: provide at least one entry.
- **`Thresholds must be in ascending order and cannot be equal`** → threshold values are out of order or contain duplicates. Fix: list thresholds strictly low→high with no repeats.
- **`Density Index out of bounds in MultiMix node`** → a `MultiMix`-style density node references an input index that does not exist. Fix: keep referenced indices within the node's input count.
- **Symptom:** you added a `LayerContainer`, `StaticLayers`/`DynamicLayers`, a `HeightSupplier` `Type`, or per-layer `Conditions`/`SlopeMin` and they are ignored → none of those exist in the format. Fix: terrain is the `Density` node graph plus a `MaterialProvider` (see [What does NOT exist](#what-does-not-exist)).

---

## Related Documentation

- [World Generation Overview](worldgen.md) - Node-graph system and shared vocabulary
- [Caves](worldgen-caves.md) - Cave density fields subtracted from terrain
- [Prefabs / Props](worldgen-prefabs.md) - Placing structures and decorations
