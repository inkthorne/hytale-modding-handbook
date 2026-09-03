---
title: "Props & Structure Placement"
description: "Place props and structures in Hytale worldgen — a biome Props[] array pairing positions with assignments, shared Assignments graphs, field/range/weight gating, and prop builders."
seo:
  type: TechArticle
---

# Props & Structure Placement

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.5.9**

Hytale places trees, rocks, plants, ores, encounters and structures through **props**. A biome
carries a `Props[]` array; each entry pairs a set of **positions** (where to try placing) with an
**assignment** (what to place). The "what" lives in shared files under
`Server/HytaleGenerator/Assignments/` referenced by name, or inline in the biome.

Assignments are themselves node graphs. The recurring pipeline is:

```
FieldFunction (noise) -> Delimiter (Min/Max range gate) -> Weighted (pick by weight)
   -> Constant -> Prop (Prefab | Cluster | Column | Cuboid | Union | Density)
```

This document describes the real format under `Server/HytaleGenerator/`.

## Overview

Defined as JSON node graphs under `Server/HytaleGenerator/` and provides:
- A biome `Props[]` array pairing positions (where) with assignments (what)
- Shared `Assignments/` graphs referenced by name
- Field/range/weight gating of placement (`FieldFunction` -> `Delimiter` -> `Weighted`)
- Prop builders: `Prefab`, `Cluster`, `Column`, `Cuboid`, `Union`, `Density`
- Rotation (`Directionality`) and vertical placement (`Scanner`) helpers
- Standalone reusable position and prop-distribution graphs

## Architecture
```
Biome Props[] entry
├── Positions  (Mesh2D / Occurrence — where to try)
└── Assignments (usually Imported -> Assignments/*.json)
        │
        ▼
Assignment graph (ExportAs "<name>")
└── FieldFunction (noise) -> Delimiter (Min/Max gate) -> Weighted (pick by weight)
        -> Constant -> Prop:
           ├── Prefab   (WeightedPrefabPaths)
           ├── Cluster  (DistanceCurve + WeightedProps)
           ├── Column   (ColumnBlocks)
           ├── Cuboid   (Bounds + Material)
           ├── Union    (Props[] — several props at one position)
           └── Density  (3D field -> ore veins)
        each prop: Directionality (rotation) + Scanner (vertical placement)

Standalone: Positions/ · PropDistributions/ · Props/ · BlockMasks/
```

## Key Classes
These are JSON worldgen node types (not Java classes); the table lists the key node types documented on this page.

| Node type | Family | Description |
|-----------|--------|-------------|
| `FieldFunction` | Assignment | Gate placement on a density value via `Min`/`Max` `Delimiters` |
| `Weighted` | Assignment | Randomly choose one child by `Weight` (`SkipChance` to place nothing) |
| `Constant` | Assignment | Always yields one `Prop` |
| `Union` | Prop | Place several props (`Props[]`) together at one position |
| `Prefab` | Prop | Place a pre-authored structure (`WeightedPrefabPaths`) |
| `Cluster` | Prop | Scatter props around an anchor by `DistanceCurve` |
| `Column` | Prop | Stack blocks at Y offsets (`ColumnBlocks`) |
| `Cuboid` | Prop | Fill an axis-aligned box |
| `Density` | Prop | Place where a 3D density field exceeds a threshold (ore veins) |
| `Mesh2D` / `Occurrence` | Positions | Candidate point grid / probability gate |
| `Directionality` | Helper | Rotation rule (`Random` / `Static`) + surface `Pattern` |
| `Scanner` | Helper | Vertical band scan (`ColumnLinear`) to find placement Y |

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Where props live](#where-props-live) | Canonical asset paths |
| [Biome Props array](#biome-props-array) | Position generator + assignment |
| [Assignment node types](#assignment-node-types) | FieldFunction, Weighted, Constant |
| [Delimiters](#delimiters) | Min/Max gating on a field |
| [Prop types](#prop-types) | Prefab, Cluster, Column, Cuboid, Union, Density |
| [Directionality & Scanner](#directionality--scanner) | Rotation and vertical placement |
| [Positions & PropDistributions](#positions--propdistributions) | Standalone position graphs |
| [Worked examples](#worked-examples) | Boulders, trees, ore veins |
| [What does NOT exist](#what-does-not-exist) | Removed fictional schema |

---

## Where props live

| Content | Path |
|---------|------|
| Shared assignments (referenced by name) | `Server/HytaleGenerator/Assignments/**/*.json` |
| Biome `Props[]` arrays | `Server/HytaleGenerator/Biomes/**/<Biome>.json` |
| Standalone position graphs | `Server/HytaleGenerator/Positions/*.json` |
| Standalone prop distributions | `Server/HytaleGenerator/PropDistributions/*.json` |
| Block masks (placement filters) | `Server/HytaleGenerator/BlockMasks/*.json` |

---

## Biome Props array

In a biome file (e.g. `Biomes/Plains1/Plains1_Oak.json`), `Props` is an array of entries. Each
entry has:

| Field | Description |
|-------|-------------|
| `Skip` | When `true`, the entry is disabled. |
| `Runtime` | Integer placement phase/pass. |
| `Positions` | A positions node (where to attempt placement). |
| `Assignments` | What to place — usually `{ "Type": "Imported", "Name": "<assignment>" }`. |
| `PropDistribution` | Alternative to the `Positions`+`Assignments` pair: a single prop-distribution node (see [Positions & PropDistributions](#positions--propdistributions)). |

(Codec: `com.hypixel.hytale.builtin.hytalegenerator.assets.propruntime.PropRuntimeAsset`.)

Real entry (Plains1_Oak placing boulder patches via an imported assignment; the candidate
grid is wrapped in an `Occurrence` gate whose density field is elided here):

```json
{
  "Skip": false,
  "Runtime": 0,
  "Positions": {
    "Type": "Occurrence",
    "Seed": "A",
    "FieldFunction": { "Type": "Normalizer", "FromMin": -1, "FromMax": 1, "ToMin": -0.7, "ToMax": 1,
                       "Inputs": [ { "...": "cached ring field, ExportAs Plains1_Oak_Boulder_Patches" } ] },
    "Positions": {
      "Type": "Mesh2D",
      "PointsY": 0,
      "PointGenerator": { "Type": "Mesh", "Jitter": 0.4, "ScaleX": 7, "ScaleY": 7, "ScaleZ": 7, "Seed": "A" }
    }
  },
  "Assignments": { "Type": "Imported", "Name": "Plains1_Oak_Boulder_Patches" }
}
```

Position node types seen in biomes: `Mesh2D` (with a `Mesh` `PointGenerator`: `Jitter`,
`ScaleX/Y/Z`, `Seed`), `Occurrence` (a `FieldFunction` density gate wrapping inner `Positions`,
with its own `Seed`), and `FieldFunction` (`Delimiters` with `Min`/`Max` over a field).
`Occurrence` lets a density field decide *whether* a candidate point survives.

---

## Assignment node types

An assignment file's root node has an `ExportAs` (the name biomes import) and a `Type`. Observed
root/branch types:

| Type | Key fields | Purpose |
|------|-----------|---------|
| `FieldFunction` | `FieldFunction` (a density node), `Delimiters[]` | Gate placement on a noise/density value via `Min`/`Max` ranges. |
| `Weighted` | `WeightedAssignments[]`, `SkipChance`, `Seed` | Randomly choose one child assignment by `Weight`. `SkipChance` is the chance to place nothing. |
| `Constant` | `Prop` | Always yields one prop. |
| `Imported` | `Name` | Pull in an assignment graph exported elsewhere. |
| `Sandwich` | `Delimiters[]` (`MinY`/`MaxY` → `Assignments`) | Route by the candidate's Y band (registered as of 0.6.3; unused by the shipped files). |

These five are the complete assignment vocabulary (`AssignmentsAsset.CODEC` registrations).
`Union` is **not** an assignment — it is a prop type (see below); an assignment that places
several things is a `Constant` whose `Prop` is a `Union`.

`SimplexNoise2D` is the usual `FieldFunction` driver (a `Density`-family node — same parameters as
in [worldgen-terrain.md](worldgen-terrain.md): `Lacunarity`, `Persistence`, `Octaves`, `Scale`,
string `Seed`).

Real `Weighted` (from `Plains1_Oak_Trees.json`, a child of a `Delimiter`):

```json
{
  "Type": "Weighted",
  "SkipChance": 0,
  "Seed": "A",
  "WeightedAssignments": [
    { "Weight": 70, "Assignments": { "Type": "Constant", "Prop": { "...": "small trees" } } },
    { "Weight": 30, "Assignments": { "Type": "Constant", "Prop": { "...": "bushes" } } }
  ]
}
```

---

## Delimiters

A `FieldFunction` assignment carries `Delimiters[]`. Each delimiter gates a `Min`/`Max` range of
the field value and routes matches to an `Assignments` child:

```json
{
  "Type": "FieldFunction",
  "ExportAs": "Plains1_Oak_Trees",
  "FieldFunction": { "Type": "SimplexNoise2D", "Scale": 80, "Seed": "1235", "Octaves": 1 },
  "Delimiters": [
    { "Min": 0.7,  "Max": 0.85, "Assignments": { "Type": "Weighted", "...": "small trees" } },
    { "Min": 0.85, "Max": 1,    "Assignments": { "Type": "Constant", "...": "large trees" } }
  ]
}
```

So where the noise reads 0.70–0.85 you get small trees, 0.85–1.0 large trees, and elsewhere
nothing. This range-gating is also how `FieldFunction` material providers work in terrain — same
`Delimiter` concept, sometimes spelled with `From`/`To` keys instead of `Min`/`Max` (both forms
appear; `Min`/`Max` in assignments, `From`/`To` in material `Delimiters`).

---

## Prop types

A `Prop` node names *what to build* at an accepted position.

### Prefab

References a pre-authored structure by path, with weighted variants.

| Field | Description |
|-------|-------------|
| `WeightedPrefabPaths[]` | `{ "Path": "...", "Weight": n }` — weighted set of prefab paths. |
| `LegacyPath` | Path-format flag (observed `false`). |
| `LoadEntities` | Whether to spawn the prefab's entities (observed `true`). |
| `Directionality` | Rotation rule (see below). |
| `Scanner` | Vertical scan to find the placement Y (see below). |
| `BlockMask` | Optional `DontPlace` / `DontReplace` block sets (e.g. `Biomes/Examples/Example_Prop.json` refuses to overwrite `Soil_Dirt`). |
| `MoldingDirection` / `MoldingChildren` / `MoldingPattern` / `MoldingScanner` | Terrain-conforming options (observed `"None"` / `false`; the pattern/scanner pair is unused by the shipped files). |

```json
{
  "Type": "Prefab",
  "WeightedPrefabPaths": [
    { "Path": "Rock_Formations/Rocks/Chalk/Medium", "Weight": 20 },
    { "Path": "Rock_Formations/Rocks/Chalk/Small",  "Weight": 80 }
  ],
  "LegacyPath": false,
  "LoadEntities": true,
  "Directionality": { "...": "see Directionality" },
  "Scanner": { "...": "see Scanner" }
}
```

Prefab paths are relative resource paths, e.g. `Trees/Oak/Stage_4`, `Trees/Beech/Stage_3`,
`Rock_Formations/Rocks/Chalk/Small`.

### Cluster

Scatters small props (often single blocks) around an anchor within a `Range`, weighted by a
`DistanceCurve`.

| Field | Description |
|-------|-------------|
| `Range` | Cluster radius. |
| `Seed` | Cluster RNG seed. |
| `DistanceCurve` | A `Manual` curve (`In`/`Out` points) controlling density vs. distance. |
| `WeightedProps[]` | `{ "Weight": n, "ColumnProp": { ... } }` candidates. |
| `Pattern` | Where the cluster may sit (often an `Imported` floor pattern). |
| `Scanner` | Vertical scan. |

Real cluster (grass/stick ring around trees in `Plains1_Oak_Trees.json`):

```json
{
  "Type": "Cluster",
  "Range": 10,
  "Seed": "A",
  "DistanceCurve": { "Type": "Manual", "Points": [ { "In": 9, "Out": 0.005 }, { "In": 10, "Out": 0 } ] },
  "WeightedProps": [ { "Weight": 1, "ColumnProp": { "Type": "Column", "ColumnBlocks": [ { "Y": 0, "Material": { "Solid": "Wood_Sticks" } } ] } } ],
  "Pattern": { "Type": "Imported", "Name": "Plains1_OakPattern_Floor" }
}
```

### Column

Stacks one or more blocks at offsets along Y.

```json
{
  "Type": "Column",
  "ColumnBlocks": [ { "Y": 0, "Material": { "Solid": "Plant_Bush_Green" } } ],
  "Directionality": { "Type": "Static", "Rotation": 0, "Pattern": { "..." : "..." } },
  "Scanner": { "Type": "ColumnLinear", "MaxY": 5, "MinY": -5, "RelativeToPosition": true, "BaseHeightName": "Base", "TopDownOrder": true, "ResultCap": 1 }
}
```

### Cuboid

Fills an axis-aligned box. From `Biomes/Basic.json`, where it is wrapped in a `Locator`
prop (`PlacementCap`, `Pattern`, `Scanner`) that finds a stone floor for it:

```json
{
  "Type": "Cuboid",
  "Bounds": { "PointA": { "X": -2, "Y": 0, "Z": -2 }, "PointB": { "X": 3, "Y": 3, "Z": 3 } },
  "Material": { "Type": "Constant", "Material": { "Solid": "Soil_Dirt", "SolidBottomUp": false } }
}
```

### Union

`{ "Type": "Union", "Props": [ ... ] }` places every listed prop at the same accepted
position — `Plains1_Oak_Trees.json` unions a `Prefab` tree with a `Cluster` of sticks.

### Other prop types

Also registered (as of 0.6.3): `Locator` (`Prop` + `Pattern`/`Scanner`/`PlacementCap` —
relocate a child prop to a matching surface), `Mask` (`Prop` + `Mask` block mask — e.g.
`Taiga1_Iron.json` wraps its `Density` ore prop), `Offset` (`Offset` + `Prop`), `Weighted` (`Entries` of `Weight`/`Prop`,
`Seed`), `Queue` (`Props[]`, first that fits), `StaticRotator` / `RandomRotator`
(`Rotation` / `Rotations`, `HorizontalRotations`, `Seed`), `Orienter` (`Rotations`,
`SelectionMode`), `Box` (`Range`, `Material`, `Pattern`, `Scanner`), `Manual` (`Blocks[]` of
`Position`/`Material`), `DensitySelector` (`Delimiters` over a `Density` choosing a `Prop`),
`PondFiller` (`FillMaterial`, `BarrierBlockSet`, `Bounds`), `Empty`, and `Imported` (`Name`).

### Density

Places blocks wherever a 3D `Density` field exceeds a threshold — used for ore veins. From
`Assignments/Plains1/Plains1_Iron.json`:

| Field | Description |
|-------|-------------|
| `Pattern` | A `Ceiling`/`Floor`/`BlockSet` rule for valid host blocks and origin. |
| `Scanner` | Vertical band to scan (e.g. `MinY: 60`, `MaxY: 120`, `BaseHeightName: "Bedrock"`). |
| `Material` | The block to place (a `Solidity` provider, e.g. `Ore_Iron_Stone`). |
| `Density` | A density node (e.g. `Sum` of `SimplexNoise3D` + `Anchor`/`Cube`). |
| `PlacementMask` | A `BlockMask` with `DontPlace` / `DontReplace` block sets. |
| `Range` | A `Point3D` cluster extent. |

```json
{
  "Type": "Density",
  "Material": { "Type": "Solidity", "Solid": { "Type": "Constant", "Material": { "Solid": "Ore_Iron_Stone" } } },
  "Density": { "Type": "Sum", "Inputs": [ { "Type": "Normalizer", "Inputs": [ { "Type": "SimplexNoise3D", "ScaleXZ": 4, "ScaleY": 4, "Seed": "A" } ] }, "..." ] },
  "Scanner": { "Type": "ColumnLinear", "MaxY": 120, "MinY": 60, "BaseHeightName": "Bedrock", "ResultCap": 1 },
  "PlacementMask": { "DontPlace": { "Materials": [ { "Solid": "Empty" } ] }, "DontReplace": { "Materials": [ { "Solid": "Empty" } ] } }
}
```

Note `Plains1_Iron.json` is itself a top-level `Weighted` assignment whose two `WeightedAssignments`
(weights 20 and 80) place `Ore_Iron_Stone` and `Ore_Copper_Stone`.

---

## Directionality & Scanner

Most placeable props share two helpers:

**Directionality** controls rotation. Observed `Type` values: `Random` (with a `Seed`) and
`Static` (with a fixed `Rotation`, e.g. `0`); also registered are `Pattern` (`InitialDirection`,
`Seed`, and a `NorthPattern`/`SouthPattern`/`EastPattern`/`WestPattern` per facing) and
`Imported` (`Name`). It also carries a `Pattern` describing the surface a prop may sit on:

```json
"Directionality": {
  "Type": "Random",
  "Seed": "A",
  "Pattern": {
    "Type": "Floor",
    "Origin": { "Type": "BlockType", "Material": { "Solid": "Empty" } },
    "Floor":  { "Type": "BlockSet", "BlockSet": { "Inclusive": true, "Materials": [ { "Solid": "Soil_Grass" }, { "Solid": "Soil_Grass_Sunny" } ] } }
  }
}
```

Pattern `Type`s seen: `Floor`, `Ceiling`, `BlockSet`, `BlockType`, and `Imported` (reusing a named
pattern such as `Plains1_OakPattern_Floor`); also registered: `Wall`, `Surface`, `Cuboid`,
`Offset`, `Rotator`, `FieldFunction`, `Constant`, and the combinators `And`/`Or`/`Not`. A
`BlockSet` lists `Materials` and an `Inclusive` flag.

**Scanner** finds the Y to place at by scanning a vertical band:

| Field | Meaning |
|-------|---------|
| `Type` | Observed: `ColumnLinear` (also registered: `ColumnRandom`, `Linear` — `Axis`, `AscendingOrder`, `Range` — `Random`, `Radial`, `Area`, `Direct`, `Origin`, `Queue`, `Imported`). |
| `MinY` / `MaxY` | Scan range. |
| `RelativeToPosition` | Whether the range is relative to the candidate point. |
| `BaseHeightName` | Reference height: `"Base"` or `"Bedrock"`. |
| `TopDownOrder` | Scan direction. |
| `ResultCap` | Max placements found per column (usually `1`). |

---

## Positions & PropDistributions

The `Positions/`, `PropDistributions/`, and `Props/` directories hold standalone, reusable graphs.
As of 0.6.3 each ships only a stub example (`ExamplePositions.json` is a bare `List`,
`ExamplePropDistribution.json` a bare `Constant`, `ExampleProp.json` a bare `Cuboid`); the
real composed graphs live inline in biomes.

**Positions** build candidate-point sets by composing a grid with jitter and scale. From
`Biomes/Basic.json`:

```json
{
  "Type": "Scaler",
  "Scale": { "X": 25, "Y": 10, "Z": 25 },
  "Positions": {
    "Type": "Jitter2d", "Magnitude": 0.7,
    "Positions": { "Type": "TriangularGrid2d" }
  }
}
```

Position node `Type`s: `TriangularGrid2d`, `SquareGrid2d`, `SquareGrid3d`, `Jitter2d` /
`Jitter3d` (`Magnitude`, `Seed`), `Scaler` (`Scale` vector), `Offset` (`OffsetX/Y/Z` or an
`Offset` vector), `Union` (`Positions[]` — merge several point sets), `Bound` (`Bounds`),
`List`, `Mesh2D` / `Mesh3D`, `Occurrence`, `FieldFunction`, `Clusters` (a `Cluster` point set
scattered by a `Distributor`), `VectorOffset`, `DirectionalJitter`, `BaseHeight` (lift points to a
named base height, e.g. `BedName: "Water"`), `Anchor`, `SimpleHorizontal`, `Cache`,
`Framework`, `Graph`, and `Imported`.

**PropDistributions** pair positions with assignments. A biome `Props[]` entry may carry a
`PropDistribution` instead of `Positions`+`Assignments`; `Biomes/Taiga1/Taiga1_River.json` uses a
`Union` (`PropDistributions[]`) of `Assigned` entries, each with a `PropDistribution` (here a
`Positions` distribution wrapping a positions graph), an `Assignments` node, and an
`OverrideAllProps` flag. Registered distribution types: `Constant` (`Positions` + `Prop`),
`Assigned`, `Positions`, `Union`, `Anchor`, `Graph`, `None`, and `Imported`.

---

## Worked examples

- **Boulders** (`Assignments/Plains1/Plains1_Oak_Boulders.json`): a `Constant` assignment whose
  `Prop` is a `Prefab` with two `WeightedPrefabPaths` (Chalk Medium/Small), a `Random`
  directionality with a `Floor` pattern over `Soil_Gravel`/`Soil_Pebbles`, and a `ColumnLinear`
  scanner (`MinY` 0, `MaxY` 20, base `"Base"`).
- **Trees** (`Assignments/Plains1/Plains1_Oak_Trees.json`): a `FieldFunction` (SimplexNoise2D,
  scale 80) gated by two `Delimiters` (0.7–0.85 small, 0.85–1.0 large), each routing to `Weighted`
  / `Union` props that combine `Prefab` trees with `Cluster` undergrowth.
- **Ore veins** (`Assignments/Plains1/Plains1_Iron.json`): a top-level `Weighted` placing
  `Density` props (`Ore_Iron_Stone`, `Ore_Copper_Stone`) driven by `SimplexNoise3D` between Y 60
  and 120 above bedrock.

---

## What does NOT exist

The previous version of this document described a fictional placement system. None of these appear
in any asset file and they are not part of the format:

`PrefabContainer`, `PrefabPopulator`, `UniquePrefabContainer`/`UniquePrefabGenerator`/
`UniquePrefabConfiguration`, `RotationMode`, `FitHeightmap`, a weighted `PrefabList`, generic
`Density`/`Frequency`/`Spacing`/`MinDistance` placement-condition blocks, and the
`Server/WorldGen/Zone/` or `Server/WorldGen/UniquePrefab/` directories. Real placement is biome
`Props[]` entries plus `Assignments/` graphs (`FieldFunction` -> `Delimiter` -> `Weighted` ->
`Constant`/`Union` -> `Prefab`/`Cluster`/`Column`/`Cuboid`/`Density`), all under
`Server/HytaleGenerator/`.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the prefab/prop loader (verified against `HytaleServer.jar`).

- **`Prefabs are empty! Key: Prefab`** → a `Prefab` prop resolved to no prefab paths. Fix: give the prop a non-empty `WeightedPrefabPaths[]` (see [Prefab](#prefab)).
- **`prefab pool contains list with null element`** → a prefab pool list has a null/missing path entry. Fix: remove the null and provide a valid resource path. (Through build-17 an empty pool threw a sibling `prefab pool contains empty list` message; 0.5.7 removed that exact string — an empty pool still fails, but not with that text.)
- **`Prefab nesting limit exceeded!`** → a prefab references other prefabs that nest too deeply (a cycle, or excessive depth). Fix: flatten the prefab references / break the cycle.
- **Symptom:** you added a `PrefabContainer`, `PrefabPopulator`, `UniquePrefabContainer`, `RotationMode`, `FitHeightmap`, or a weighted top-level `PrefabList` and it is ignored → none of those exist in the format. Fix: use biome `Props[]` entries plus `Assignments/` graphs (see [What does NOT exist](#what-does-not-exist)).

---

## Related Documentation

- [Terrain Density Graphs](worldgen-terrain.md) - Density nodes reused by FieldFunctions
- [Caves](worldgen-caves.md) - Cave decorations are placed by these same props
- [World Generation Overview](worldgen.md) - Node-graph system
