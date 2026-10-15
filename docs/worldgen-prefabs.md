---
title: "Props & Structure Placement"
description: "Place props and structures in Hytale worldgen — a biome Props[] array pairing positions with assignments, shared Assignments graphs, field/range/weight gating, and prop builders."
seo:
  type: TechArticle
---

# Props & Structure Placement

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.7.2**

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
| [Block masks](#block-masks) | What a prop may place and overwrite |
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
| `Runtime` | Integer placement pass. The generator collects every distinct value across a biome's `Props[]` and runs one `PropStage` per index, in ascending order, so a later pass sees what earlier passes placed. The shipped biomes use `0` (88 entries), `1` (29), `2` (17) and `3` (1). |
| `ContextPrecision` | How the prop stage sizes the terrain it must read before placing this entry (0.7.2+): `"Biome"` (the default) reserves room for the largest prop the entry could place, everywhere in the chunk; `"Chunk"` does the same but skips the entry entirely when its distribution yields no position in the chunk; `"Prop"` runs the distribution and sizes the read area from each actual prop at its actual position. 23 of the 135 shipped entries set it (`Biome` 19, `Prop` 2, `Chunk` 2). |
| `Positions` | A positions node (where to attempt placement). |
| `Assignments` | What to place — usually `{ "Type": "Imported", "Name": "<assignment>" }`. |
| `PropDistribution` | Alternative to the `Positions`+`Assignments` pair: a single prop-distribution node (see [Positions & PropDistributions](#positions--propdistributions)). |

(Codec: `com.hypixel.hytale.builtin.hytalegenerator.assets.propruntime.PropRuntimeAsset`.)

Real entry (`Desert1_Rocky.json` placing iron veins via an imported assignment on a jittered
point mesh):

```json
{
  "Skip": false,
  "Runtime": 0,
  "Positions": {
    "Type": "Mesh2D",
    "PointsY": 0,
    "PointGenerator": { "Type": "Mesh", "Jitter": 0.5, "ScaleX": 22, "ScaleY": 22, "ScaleZ": 22, "Seed": "Iron" }
  },
  "Assignments": { "Type": "Imported", "Name": "Desert1_Iron" }
}
```

The Plains1 biomes use the other form throughout: every `Props[]` entry in `Plains1_Oak.json`
is a `PropDistribution` — a `Union` of `Assigned` distributions, each pairing a positions graph
(often `BaseHeight` → `Occurrence` → a grid) with an imported assignment; two of its three
unions also carry a `Graph` distribution, which places the cave props attached to the
`Plains1_Caves` graph generator (see [worldgen-caves.md](worldgen-caves.md)).

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
| `Sandwich` | `Delimiters[]` (`MinY`/`MaxY` → `Assignments`) | Route by the candidate's Y band (registered as of 0.7.2; unused by the shipped files). |

These five are the complete assignment vocabulary (`AssignmentsAsset.CODEC` registrations).
`Union` is **not** an assignment — it is a prop type (see below); an assignment that places
several things is a `Constant` whose `Prop` is a `Union`.

`SimplexNoise2D` is the usual `FieldFunction` driver (a `Density`-family node — same parameters as
in [worldgen-terrain.md](worldgen-terrain.md): `Lacunarity`, `Persistence`, `Octaves`, `Scale`,
string `Seed`).

Real `Weighted` (the root of `Assignments/Plains1/Gorges/Plains1_Gorges_Forest_Bushes.json`):

```json
{
  "Type": "Weighted",
  "ExportAs": "Plains1_Gorges_Bushes_Assignment",
  "SkipChance": 0.2,
  "Seed": "A",
  "WeightedAssignments": [
    { "Weight": 1, "Assignments": { "Type": "Constant", "Prop": { "...": "a Column placing Plant_Bush_Lush" } } }
  ]
}
```

With a single entry the weights do nothing; the `SkipChance` of `0.2` alone thins the bushes
by a fifth.

---

## Delimiters

A `FieldFunction` assignment carries `Delimiters[]`. Each delimiter gates a `Min`/`Max` range of
the field value and routes matches to an `Assignments` child:

```json
{
  "Type": "FieldFunction",
  "ExportAs": "Plains1_Oak_Trees",
  "FieldFunction": { "Type": "SimplexNoise2D", "Lacunarity": 2, "Persistence": 0.5, "Scale": 80, "Seed": "1235", "Octaves": 1 },
  "Delimiters": [
    { "Min": -1,   "Max": -0.3, "Assignments": { "Type": "Constant", "...": "beech trees" } },
    { "Min": -0.3, "Max": 1,    "Assignments": { "Type": "Constant", "...": "oak trees" } }
  ]
}
```

(From `Assignments/Plains1/Oak/Plains1_Oak_Trees.json`.) So where the noise reads −1 to −0.3
you get beech, from −0.3 to 1 oak; a value outside every delimiter places nothing. This range-gating is also how `FieldFunction` material providers work in terrain — same
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
| `LoadEntities` | Whether to spawn the prefab's entities (both `true` and `false` ship). |
| `Directionality` | Rotation rule (see below). |
| `Scanner` | Vertical scan to find the placement Y (see below). |
| `BlockMask` | Optional `DontPlace` / `DontReplace` material sets — see [Block masks](#block-masks) below. |
| `MoldingDirection` / `MoldingChildren` / `MoldingPattern` / `MoldingScanner` | Terrain-conforming options (observed `"None"` / `false`; the pattern/scanner pair is unused by the shipped files). |

```json
{
  "Type": "Prefab",
  "WeightedPrefabPaths": [
    { "Path": "Orbis/Rocks/Chalk/Medium", "Weight": 20 },
    { "Path": "Orbis/Rocks/Chalk/Small",  "Weight": 80 }
  ],
  "LegacyPath": false,
  "LoadEntities": false,
  "MoldingDirection": "None",
  "MoldingChildren": false
}
```

(From `Assignments/Plains1/Oak/Plains1_Oak_Boulders.json`, where the `Prefab` carries no
`Directionality`/`Scanner` of its own — it sits inside a `RandomRotator` inside a `Locator`
that supplies the floor pattern and scanner.) Prefab paths are relative resource paths under
`Server/Prefabs/`, e.g. `Orbis/Trees/Oak/Stage_4`, `Trees/Beech/Stage_3`,
`Rock_Formations/Rocks/Chalk/Small` — the shipped assignments use both the `Orbis/…` tree
and the older top-level folders.

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

Real cluster (a ring of sticks around dry trees in `Biomes/Desert1/Desert1_Rocky.json`):

```json
{
  "Type": "Cluster",
  "Range": 10,
  "Seed": "A",
  "DistanceCurve": { "Type": "Manual", "Points": [ { "In": 9, "Out": 0.005 }, { "In": 10, "Out": 0 } ] },
  "WeightedProps": [ { "Weight": 1, "ColumnProp": { "Type": "Column", "ColumnBlocks": [ { "Y": 0, "Material": { "Solid": "Wood_Sticks" } } ],
      "Directionality": { "Type": "Static", "Rotation": 0, "Pattern": { "Type": "Imported", "Name": "Desert1_Sticks_Dry_Floor" } },
      "Scanner": { "Type": "Imported", "Name": "Desert1_Rocky_Trees_Dry_Scanner" } } } ],
  "Pattern": { "Type": "Imported", "Name": "Desert1_Trees_Dry_Floor" },
  "Scanner": { "Type": "Imported", "Name": "Desert1_Rocky_Trees_Dry_Scanner" }
}
```

### Column

Stacks one or more blocks at offsets along Y.

```json
{
  "Type": "Column",
  "ColumnBlocks": [ { "Y": 0, "Material": { "Solid": "Wood_Sticks" } } ],
  "Directionality": { "Type": "Static", "Rotation": 0, "Pattern": {
    "Type": "Floor",
    "Origin": { "Type": "BlockType", "Material": { "Solid": "Empty" } },
    "Floor":  { "Type": "BlockSet", "BlockSet": { "Inclusive": true, "Materials": [ { "Solid": "Soil_Sand_White" } ] } } } },
  "Scanner": { "Type": "ColumnLinear", "MaxY": 5, "MinY": -5, "RelativeToPosition": true, "BaseHeightName": "Base", "TopDownOrder": true, "ResultCap": 1 }
}
```

(Sticks on white sand, from `Assignments/Desert1/Desert1_Stacks_Trees.json`.)

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
position — `Plains1_Oak_Trees.json` unions an `Imported` mushroom prop with a `Prefab` tree.

### Other prop types

Also registered (as of 0.7.2): `Locator` (`Prop` + `Pattern`/`Scanner`/`PlacementCap` —
relocate a child prop to a matching surface), `Mask` (`Prop` + `Mask` block mask — e.g.
`Taiga1_Iron.json` wraps its `Density` ore prop), `Offset` (`Offset` + `Prop`), `Weighted` (`Entries` of `Weight`/`Prop`,
`Seed`), `Queue` (`Props[]`, first that fits), `StaticRotator` / `RandomRotator`
(`Rotation` / `Rotations`, `HorizontalRotations`, `Seed`), `Orienter` (`Rotations`,
`SelectionMode`), `Box` (`Range`, `Material`, `Pattern`, `Scanner`), `Manual` (`Blocks[]` of
`Position`/`Material`), `DensitySelector` (`Delimiters` over a `Density` choosing a `Prop`),
`PondFiller` (`FillMaterial`, `BarrierBlockSet`, `Bounds`), `Empty`, and `Imported` (`Name`).

### Density

Places blocks wherever a 3D `Density` field exceeds a threshold — used for ore veins. From
`Assignments/Desert1/Desert1_Iron.json`:

| Field | Description |
|-------|-------------|
| `Pattern` | A `Ceiling`/`Floor`/`BlockSet` rule for valid host blocks and origin. |
| `Scanner` | Vertical band to scan (e.g. `MinY: 60`, `MaxY: 120`, `BaseHeightName: "Bedrock"`). |
| `Material` | The block to place (a material provider: a `Solidity` provider here, a `FieldFunction` provider in the Plains1 ores). |
| `Density` | A density node (e.g. `Sum` of `SimplexNoise3D` + `Anchor`/`Cube`). |
| `PlacementMask` | A `BlockMask` (see [Block masks](#block-masks)). |
| `Range` | The placement extent — a `Vector3i`, i.e. `{"X":…,"Y":…,"Z":…}`. |
| `Bounds` | Optional explicit bounds for the field sample. |

```json
{
  "Type": "Density",
  "Material": { "Type": "Solidity", "Solid": { "Type": "Constant", "Material": { "Solid": "Ore_Iron_Sandstone" } } },
  "Density": { "Type": "Sum", "Inputs": [ { "Type": "Normalizer", "Inputs": [ { "Type": "SimplexNoise3D", "ScaleXZ": 4, "ScaleY": 4, "Seed": "A" } ] }, "..." ] },
  "Scanner": { "Type": "ColumnLinear", "MaxY": 120, "MinY": 60, "BaseHeightName": "Bedrock", "ResultCap": 1 },
  "PlacementMask": { "DontPlace":   { "Inclusive": true, "Materials": [ { "Solid": "Empty" } ] },
                     "DontReplace": { "Inclusive": true, "Materials": [ { "Solid": "Empty" } ] } },
  "Range": { "X": 2, "Y": 2, "Z": 2 }
}
```

The Plains1 ores (`Assignments/Plains1/Plains1_Iron.json`, `Plains1_Copper.json`) are built
differently: a `Constant` assignment whose `Prop` is a `Mask` wrapping a `Density` prop with
explicit `Bounds` and no `Scanner`, whose `Material` is a `FieldFunction` provider over the same
kind of noise-plus-`Anchor` field, picking `Ore_Iron_Basalt_Cracked` / `Ore_Iron_Basalt` (iron)
or `Ore_Copper_Stone` (copper) by value band; the `Mask`'s `DontReplace` (`Inclusive: false`)
limits them to replacing basalt/volcanic rock (iron) or `Rock_Stone` (copper).

---

## Directionality & Scanner

Most placeable props share two helpers:

**Directionality** controls rotation. Observed `Type` values: `Static` (with a fixed
`Rotation`, e.g. `0`; 115 uses), `Random` (with a `Seed`; 59) and `Pattern` (`InitialDirection`,
`Seed`, and a `NorthPattern`/`SouthPattern`/`EastPattern`/`WestPattern` per facing; 4); also
registered is `Imported` (`Name`). Many 0.7.2 assignments leave rotation to a wrapping
`RandomRotator`/`StaticRotator` prop instead. It also carries a `Pattern` describing the surface a prop may sit on:

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

Pattern `Type`s seen: `Floor`, `Ceiling`, `Wall`, `BlockSet`, `BlockType`, `Offset`,
`FieldFunction`, the combinators `And`/`Or`/`Not`, and `Imported` (reusing a named pattern such
as `Floor_Grass_Pattern`); also registered: `Surface`, `Cuboid`, `Rotator` and `Constant`. A
`BlockSet` lists `Materials` and an `Inclusive` flag.

**Scanner** finds the Y to place at by scanning a vertical band:

| Field | Meaning |
|-------|---------|
| `Type` | Observed: `Origin` (264 uses), `Linear` (256 — `Axis`, `AscendingOrder`, `Range`, and a child `Scanner`, usually `Origin`), `ColumnLinear` (184), `Imported` (41), `Random` (5), `ColumnRandom` (4) and `Radial` (1). Also registered: `Area` and `Queue`. (`Origin`'s class is `DirectScannerAsset`, but `"Origin"` is the `Type` string.) The `MinY`…`ResultCap` rows below are the `ColumnLinear` keys. |
| `MinY` / `MaxY` | Scan range. |
| `RelativeToPosition` | Whether the range is relative to the candidate point. |
| `BaseHeightName` | Reference height named by the world structure's `DecimalConstants`: `"Base"`, `"Water"` or `"Bedrock"`. |
| `TopDownOrder` | Scan direction. |
| `ResultCap` | Max placements found per column (usually `1`). |

---

## Block masks

A `BlockMask` (inline on a prop, or a file under `BlockMasks/`) decides which blocks a prop
may write and which existing blocks it may overwrite.

| Key | Meaning |
|-----|---------|
| `DontPlace` | A material set of blocks the prop may **not** write (`BlockMask.canPlace` = *not* in this set). |
| `DontReplace` | A material set of existing world blocks the prop may **not** overwrite (`canReplace` = *not* in this set), used when no `Advanced` entry matches. |
| `Advanced` | Per-source overrides: entries of `Source` (a material set of the prop's own blocks) and `CanReplace` (the material set those blocks may overwrite). The first matching `Source` wins and bypasses `DontReplace` entirely. |
| `ExportAs` / `Import` | Publish this mask under a name / pull one in by name. |

A material set is `{"Inclusive": <bool>, "Materials": [ … ]}`, and **`Inclusive` inverts the
whole set**: `MaterialSet.test` returns `contains && Inclusive || !contains && !Inclusive`.

> **Gotcha:** because both fields are phrased as *don't*, an `Inclusive: false` set reads as
> a double negative. `Biomes/Examples/Example_Prop.json` carries
> `"DontReplace": {"Inclusive": false, "Materials": [{"Solid": "Soil_Dirt"}]}` — the set
> matches everything *except* `Soil_Dirt`, and `canReplace` is its negation, so that prop
> may overwrite **only** `Soil_Dirt`. It does not "protect" dirt.

---

## Positions & PropDistributions

The `Positions/`, `PropDistributions/`, and `Props/` directories hold standalone, reusable graphs.
As of 0.7.2 each ships only a stub example (`ExamplePositions.json` is a bare `List`,
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
`Union` (`PropDistributions[]`) of `Assigned` entries, each carrying a `PropDistribution`
(here a `Positions` distribution wrapping a positions graph) and an `Assignments` node.
`Assigned` also accepts an `OverrideAllProps` boolean — omitted in the shipped file, so it
defaults to `false`, meaning the assignment only fills positions that do not already hold a
prop; `true` makes it overwrite whatever a previous distribution put there.

Registered distribution types and their keys: `Constant` (`Positions` + `Prop`), `Assigned`
(`PropDistribution`, `Assignments`, `OverrideAllProps`), `Positions` (`Positions`), `Union`
(`PropDistributions[]`), `Anchor` (`PropDistribution`, `Reversed`), `Graph` (`GraphGenerator`,
`ContentLayer`), `None`, and `Imported` (`Name`). All of them also take the shared `Skip` and
`ExportAs`.

---

## Worked examples

- **Boulders** (`Assignments/Plains1/Oak/Plains1_Oak_Boulders.json`): a `Constant` assignment
  whose `Prop` is a `Locator` (`PlacementCap: 1`, a `Floor` pattern over
  `Soil_Gravel_Lime`/`Soil_Pebbles`/`Soil_Gravel` below `Empty`, and a `Linear` Y scanner over
  `Origin` with `Range` 0–40, descending) wrapping a `RandomRotator` (`HorizontalRotations`)
  wrapping a `Prefab` with two `WeightedPrefabPaths` (`Orbis/Rocks/Chalk/Medium` 20,
  `…/Small` 80).
- **Trees** (`Assignments/Plains1/Oak/Plains1_Oak_Trees.json`): a `FieldFunction`
  (`SimplexNoise2D`, scale 80) gated by two `Delimiters` (−1…−0.3 beech, −0.3…1 oak), each a
  `Constant` → `Locator` → `RandomRotator` → `Union` of an `Imported` mushroom prop and a
  `Prefab` tree (`Orbis/Trees/Beech/Stage_1`–`2`, `Orbis/Trees/Oak/Stage_3`–`5`).
- **Ore veins** (`Assignments/Desert1/Desert1_Iron.json`): a `Constant` placing a `Density` prop
  (`Ore_Iron_Sandstone`) driven by `SimplexNoise3D`, scanned between Y 60 and 120 above
  bedrock under a sandstone `Ceiling` pattern.

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

Backtick-quoted strings below are literal messages from `HytaleServer.jar` 0.7.2.

The `HytaleGenerator` prop pipeline logs rather than throws, so a broken prop usually shows
up as *nothing being placed* plus a line in the server log:

- **`Couldn't load prefab with path: `** (SEVERE, `PrefabPropAsset`; the assembled line appends the path and a stack trace) → one of the prop's `WeightedPrefabPaths` did not resolve to a prefab file or folder. The whole prop yields no prefabs. Fix: check the path is a real resource path under the prefab root, e.g. `Trees/Oak/Stage_4`.
- **`Exception thrown by HytaleGenerator while loading a Prefab:`** (SEVERE, `PrefabLoader`) → an I/O error while walking a prefab directory.
- **`Couldn't place prefab prop.`** (WARNING, `PrefabProp`) → the prefab loaded but placement failed at a position (usually out-of-bounds writes).
- **Symptom:** a prop whose `Pattern` (or `Directionality` pattern) is `{ "Type": "Imported", "Name": … }` never places, and nothing is logged → the name matches no pattern published with `ExportAs`. `ImportedPatternAsset` silently falls back to a constant-false pattern, so no position ever qualifies (only an *empty* `Name` logs `An exported Pattern with the name does not exist: `). The shipped 0.7.2 assets contain a live instance: `Floor_Grass_Pattern` is imported by `Plains1_Gorges_Forest_Bushes.json`, `Plains1_Gorges_Forest_Clusters.json` and `Experimental/BasicForest.json`, and exported by no file. Fix: grep for the `ExportAs` before relying on an imported pattern.
- **`Imported BlockMask asset with name '`** (WARNING; assembled line `Imported BlockMask asset with name '<name>' not found`, whose tail literal is **`' not found`**) → a prop's `BlockMask` uses `Import` naming a mask nothing publishes with `ExportAs`. It degrades to an **empty** mask, which permits everything, so the symptom is a prop that overwrites blocks it should not.

Legacy-generator messages (`com.hypixel.hytale.server.worldgen.*` and `builtin.buildertools`),
kept here because they still surface in server logs:

- **`Prefabs are empty! Key: Prefab`** → thrown by `PrefabCaveNodeShapeGeneratorJsonLoader`, part of the legacy `WorldGen.Type: "Hytale"` cave loader. It is **not** raised by a `HytaleGenerator` `Prefab` prop.
- **`Prefab nesting limit exceeded!`** → thrown by `buildertools`' `RecursivePrefabLoader` (the `/prefab` command), not by worldgen. Fix: flatten the prefab references / break the cycle.
- **`prefab pool contains list with null element`** → a prefab pool list has a null/missing path entry. Fix: remove the null and provide a valid resource path. (Through build-17 an empty pool threw a sibling `prefab pool contains empty list` message; 0.5.7 removed that exact string — an empty pool still fails, but not with that text.)

> As of 0.7.2 the `prefab pool contains list with null element` string lives in the
> `PrefabProp` under `hytalegenerator/props/deprecated/prefab/`, not the live `PrefabProp`
> in `hytalegenerator/props/` — the live one logs the messages in the first list above
> instead.

- **Symptom:** you added a `PrefabContainer`, `PrefabPopulator`, `UniquePrefabContainer`, `RotationMode`, `FitHeightmap`, or a weighted top-level `PrefabList` and it is ignored → none of those exist in the format. Fix: use biome `Props[]` entries plus `Assignments/` graphs (see [What does NOT exist](#what-does-not-exist)).

---

## Related Documentation

- [Terrain Density Graphs](worldgen-terrain.md) - Density nodes reused by FieldFunctions
- [Caves](worldgen-caves.md) - Cave decorations are placed by these same props
- [World Generation Overview](worldgen.md) - Node-graph system
