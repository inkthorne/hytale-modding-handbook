# Biome System

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against build-12**

A biome is a node-graph file under `Server/HytaleGenerator/Biomes/`. It defines the
terrain heightfield, the materials that fill solid and empty space, optional scattered
props, and optional environment and tint providers. Biomes are referenced by **name**
from world structures (see [worldgen-zones.md](worldgen-zones.md)).

See [worldgen.md](worldgen.md) for the node-graph vocabulary (`Type`, `Inputs`, `Skip`,
`ExportAs`, `Imported`, noise parameters) that this document builds on.

## Overview

Defined as JSON node-graph files under `Server/HytaleGenerator/Biomes/` and provides:
- A `Terrain` heightfield (a `DAOTerrain` node wrapping a density graph)
- A `MaterialProvider` (usually `Solidity`) choosing solid vs. empty blocks
- Optional `Props` entries scattering props/prefabs
- Optional `EnvironmentProvider` for sky/ambient selection
- Optional `TintProvider` for block color tint
- Referencing by file name from world structures (see [worldgen-zones.md](worldgen-zones.md))

## Architecture
```
Biome file (Biomes/<Family>/<Biome>.json)
├── Name                 display name
├── Terrain (DAOTerrain)
│   └── Density          heightfield graph (Min/Max/Sum/Mix over noise + BaseHeight)
├── MaterialProvider (Solidity)
│   ├── Solid            blocks where terrain is solid
│   └── Empty (REQUIRED) air + fluids (e.g. Water_Source)
├── Props[]              Positions (Mesh2D/Occurrence) + Assignments (usually Imported)
├── EnvironmentProvider  Constant | DensityDelimited
└── TintProvider         Constant | DensityDelimited
```

## Key Classes
These are JSON worldgen node types (not Java classes); the table lists the key node types documented on this page.

| Node type | Where | Description |
|-----------|-------|-------------|
| `DAOTerrain` | `Terrain` | Biome terrain entry point; wraps the `Density` heightfield graph |
| `Solidity` | `MaterialProvider` | Top-level provider; splits into `Solid` and `Empty` branches |
| `Constant` | provider / env / tint | Always places one block, environment, or tint color |
| `Queue` | material provider | Tries child providers in order; first match wins |
| `SimpleHorizontal` | material provider | Applies a provider within a Y band relative to a base height |
| `SpaceAndDepth` | material provider | Stacks `ConstantThickness` layers by depth into the floor |
| `FieldFunction` | material provider | Picks material by where a sampled density falls (`From`/`To`) |
| `Mesh2D` / `Occurrence` | `Props` Positions | Candidate point grid / probability gate |
| `DensityDelimited` | env / tint provider | Selects environment or tint by density `Range` |

## Quick Navigation

| Section | Description |
|---------|-------------|
| [File Location & Naming](#file-location--naming) | Where biome files live |
| [Top-Level Structure](#top-level-structure) | The keys every biome file uses |
| [Terrain](#terrain) | The heightfield density graph (`DAOTerrain`) |
| [MaterialProvider](#materialprovider) | Solid vs. empty block placement (`Solidity`) |
| [Props](#props) | Scattered props / prefabs |
| [EnvironmentProvider](#environmentprovider) | Sky / ambient environment |
| [TintProvider](#tintprovider) | Block color tint |
| [Minimal Biome](#minimal-biome-example) | Smallest complete example |

---

## File Location & Naming

```
Server/HytaleGenerator/Biomes/
├── Plains1/        Plains1_Oak.json, Plains1_River.json, Plains1_Shore.json, ...
├── Desert1/        Desert1_Oasis.json, Desert1_River.json, ...
├── Taiga1/         Taiga1_Redwood.json, Taiga1_Mountains.json, ...
├── Volcanic1/      Volcanic1_Jungle.json, Volcanic1_Caldera.json, ...
├── Ocean1/         Oceans.json
├── Examples/       single-concept demo graphs
├── Experimental/   work-in-progress biomes
├── Generative/     generative structure biomes
├── Default_Flat/   Default_Flat.json
└── Void.json, Void_Buffer.json, Basic.json, ...
```

The file's `Name` field is the display name; biomes are wired together by the **file
name** (without extension), which is what a world structure's `Biome` entries reference
(e.g. a structure entry `"Biome": "Plains1_Oak"` resolves to `Plains1/Plains1_Oak.json`).

---

## Top-Level Structure

Biome files use these top-level keys (counts reflect how common each is across the
shipped biomes):

| Key | Required | Description |
|-----|----------|-------------|
| `Name` | yes | Display name |
| `Terrain` | yes | A `DAOTerrain` node wrapping a `Density` graph — the heightfield |
| `MaterialProvider` | yes | A material graph (usually `Solidity`) choosing blocks |
| `Density` | sometimes | A shared density graph (some biomes export terrain fields here) |
| `Props` | optional | Array of prop-placement entries |
| `EnvironmentProvider` | optional | Sky/ambient environment selection |
| `TintProvider` | optional | Block color tint selection |

> There is **no** `TileBiome` / `CustomBiome` distinction, no `LayerContainer`,
> `CoverContainer`, `PrefabContainer`, `WaterContainer`, `FadeContainer`,
> `EnvironmentContainer`, or `TintContainer`. Terrain and materials are node graphs;
> water is just a fluid `Material` placed by the `Empty` branch of the material provider.

A biome file may be serialized in one of two equivalent styles (see
[worldgen.md](worldgen.md#the-node-graph-model)): with `$NodeId` plus a
`$NodeEditorMetadata` block, or with `$Title` / `$Position` editor keys. The
generation-relevant content is identical.

---

## Terrain

`Terrain` is a node of `Type` `DAOTerrain` whose `Density` child is a density graph that
produces the heightfield. The root of that graph is typically a combiner
(`Min`/`Max`/`Sum`/`Mix`) over noise and curve-mapped base-height nodes.

A simple terrain (from `Biomes/Examples/Example_CellNoise2D.json`) — cellular noise summed
with a base-height curve:

```json
"Terrain": {
  "Type": "DAOTerrain",
  "Density": {
    "Type": "Sum",
    "Skip": false,
    "Inputs": [
      {
        "Type": "CellNoise2D",
        "ScaleX": 150,
        "ScaleZ": 150,
        "Jitter": 0.3,
        "CellType": "Distance2Div",
        "Octaves": 1,
        "Seed": "A"
      },
      {
        "Type": "CurveMapper",
        "Curve": {
          "Type": "Manual",
          "Points": [
            { "In": 0,  "Out": 1 },
            { "In": 50, "Out": -1 }
          ]
        },
        "Inputs": [
          {
            "Type": "BaseHeight",
            "BaseHeightName": "Base",
            "Distance": true
          }
        ]
      }
    ]
  }
}
```

Production biomes (e.g. `Plains1/Plains1_Oak.json`) nest many `Min`/`Max`/`Sum`/`Mix`,
`Normalizer`, `Pow`, `Cache`, and `YOverride` nodes over several `SimplexNoise2D`
sources, and pull in shared fields with `Imported` (e.g. a cave terrain field). A node can
publish an intermediate result with `ExportAs` (e.g. `"ExportAs": "Plains1_Oak_Terrain_Field"`)
so the material provider and prop graphs can sample the same field by `Imported` name.

`BaseHeight` references a named world constant defined by the world structure's
`Framework` (commonly `"Base"`); see [worldgen-zones.md](worldgen-zones.md#framework).

---

## MaterialProvider

`MaterialProvider` decides which block id occupies each cell. Terrain biomes use
`Type` `Solidity`, which has two required branches:

- `Solid` — materials placed where terrain is solid.
- `Empty` — materials placed in open space (air, and any fluids such as water).

A `Material` leaf carries a block id: `{"Solid": "Soil_Dirt"}`, `{"Solid": "Rock_Stone"}`,
`{"Solid": "Empty"}`, or a fluid `{"Fluid": "Water_Source"}`.

Minimal solidity provider (from `Biomes/Examples/Example_CellNoise2D.json`):

```json
"MaterialProvider": {
  "Type": "Solidity",
  "Solid": {
    "Type": "Queue",
    "Queue": [
      {
        "Type": "Constant",
        "Material": { "Solid": "Soil_Dirt" }
      }
    ]
  },
  "Empty": {
    "$Comment": "REQUIRED",
    "Type": "Constant",
    "Material": { "Solid": "Empty" }
  }
}
```

### Provider node types

| Type | Key fields | Purpose |
|------|-----------|---------|
| `Constant` | `Material` | Always place one block id |
| `Queue` | `Queue[]` | Try child providers in order; first that matches wins |
| `SimpleHorizontal` | `TopY`, `TopBaseHeight`, `BottomY`, `BottomBaseHeight`, `Material` | Apply a provider only within a Y band relative to a named base height |
| `SpaceAndDepth` | `LayerContext`, `MaxExpectedDepth`, `Layers[]` | Stack materials by depth into the floor |
| `FieldFunction` | `FieldFunction`, `Delimiters[]` | Choose material by where a sampled density falls (`From`/`To`) |

`SpaceAndDepth` layers are `ConstantThickness` entries (`Thickness` + `Material`), and may
carry a `Condition` (e.g. `GreaterThanCondition` on `SPACE_ABOVE_FLOOR`). `LayerContext`
observed value: `"DEPTH_INTO_FLOOR"`.

Surface layering example — grass on top, dirt below (from `Default_Flat/Default_Flat.json`):

```json
"Type": "SpaceAndDepth",
"LayerContext": "DEPTH_INTO_FLOOR",
"MaxExpectedDepth": 4,
"Layers": [
  {
    "Type": "ConstantThickness",
    "Thickness": 1,
    "Material": { "Type": "Constant", "Material": { "Solid": "Soil_Grass" } }
  },
  {
    "Type": "ConstantThickness",
    "Thickness": 3,
    "Material": { "Type": "Constant", "Material": { "Solid": "Soil_Dirt" } }
  }
]
```

Water is placed by the `Empty` branch as a fluid material within a Y band — e.g.
`Plains1_Oak`'s empty queue places `{"Fluid": "Water_Source"}` between two `Base`-relative
Y values, then falls through to `{"Solid": "Empty"}`.

---

## Props

`Props` is an array of placement entries. Each entry pairs a set of `Positions` with the
`Assignments` to place there, and may carry `Skip` and a `Runtime` ordering value.

```json
"Props": [
  {
    "Skip": false,
    "Runtime": 0,
    "Positions": {
      "Type": "Mesh2D",
      "PointsY": 0,
      "PointGenerator": {
        "Type": "Mesh",
        "Jitter": 0.4,
        "ScaleX": 20, "ScaleY": 20, "ScaleZ": 20,
        "Seed": "A"
      }
    },
    "Assignments": {
      "Type": "Imported",
      "Name": "Plains1_Oak_Pillars"
    }
  }
]
```

- `Positions` defines candidate points. `Mesh2D` lays out a jittered grid via its
  `PointGenerator` (`Mesh`, with `Jitter`, `ScaleX/Y/Z`, `Seed`). An `Occurrence` node may
  wrap positions to gate them by a probability `FieldFunction`.
- `Assignments` decides what to place. Most biomes use `{"Type":"Imported","Name":"..."}`
  to reference a graph in `Assignments/` (see
  [worldgen-zones.md](worldgen-zones.md) and the assignment files such as
  `Assignments/Plains1/Plains1_Oak_Trees.json`).

Assignment graphs themselves use `FieldFunction` (mapping a density to placement via
`Delimiters` with `Min`/`Max`), `Weighted` (weighted random among `WeightedAssignments`),
`Cluster` (grouped placement with a `DistanceCurve`), and `Prefab` nodes that name prefab
paths via `WeightedPrefabPaths` (`Path`, `Weight`).

---

## EnvironmentProvider

Selects the ambient environment for the biome. Two forms occur:

**Constant** — a single named environment (the common case):

```json
"EnvironmentProvider": {
  "Type": "Constant",
  "Environment": "Env_Zone1_Plains"
}
```

Observed environment names include `Env_Zone1_Plains`, `Env_Zone1_Shores`, `Env_Zone0`,
`Env_Void`, `Env_Default_Flat`, `Env_Zone3_Glacial_Henges`.

**DensityDelimited** — chooses among environments by where a `Density` value falls,
using `Delimiters` each carrying an `Environment` and a `Range`. Used where the
environment should vary within the biome (e.g. `Volcanic1/Volcanic1_Jungle.json`).

---

## TintProvider

Selects a block tint color. Two forms occur:

**Constant** — one color for the whole biome (from `Void.json`):

```json
"TintProvider": {
  "Type": "Constant",
  "Color": "#5b9e28"
}
```

**DensityDelimited** — picks a tint per `Range` of a sampled `Density`. Each `Delimiter`
holds a `Tint` (`{"Type":"Constant","Color":"#..."}`) and a `Range`
(`MinInclusive` / `MaxExclusive`). Example from `Volcanic1/Volcanic1_Jungle.json`:

```json
"TintProvider": {
  "Type": "DensityDelimited",
  "Density": {
    "Type": "SimplexNoise2D",
    "Lacunarity": 5, "Persistence": 0.2, "Octaves": 2, "Scale": 100, "Seed": "tints"
  },
  "Delimiters": [
    {
      "Tint": { "Type": "Constant", "Color": "#508A29" },
      "Range": { "MinInclusive": -1, "MaxExclusive": -0.33 }
    },
    {
      "Tint": { "Type": "Constant", "Color": "#598D26" },
      "Range": { "MinInclusive": -0.33, "MaxExclusive": 0.33 }
    },
    {
      "Tint": { "Type": "Constant", "Color": "#5F8F26" },
      "Range": { "MinInclusive": 0.33, "MaxExclusive": 1 }
    }
  ]
}
```

---

## Minimal Biome Example

The smallest complete shape — flat-ish terrain, dirt fill, required empty branch:

```json
{
  "Name": "Hills",
  "Terrain": {
    "Type": "DAOTerrain",
    "Density": {
      "Type": "Constant",
      "Value": 0
    }
  },
  "MaterialProvider": {
    "Type": "Solidity",
    "Solid": {
      "Type": "Constant",
      "Material": { "Solid": "Soil_Dirt" }
    },
    "Empty": {
      "$Comment": "REQUIRED",
      "Type": "Constant",
      "Material": { "Solid": "Empty" }
    }
  }
}
```

(`Void.json` is essentially this with a `Constant` density of `0`, an `Empty` material,
and a `Constant` environment/tint.)

---

## Gotchas & Errors

- **Symptom:** a world structure's `"Biome": "Plains1_Oak"` entry resolves to a missing/default biome even though `Plains1_Oak.json` exists → references use the **file name** (without extension), not the file's `Name` display field, and the match is case-sensitive. Fix: reference the exact file name, e.g. `Plains1/Plains1_Oak.json` → `"Plains1_Oak"`.
- **Symptom:** you added `LayerContainer`, `CoverContainer`, `WaterContainer`, `PrefabContainer`, or a `TileBiome`/`CustomBiome` type and it is silently ignored → none of those exist in the format. Fix: terrain is a `DAOTerrain`→`Density` node graph, materials are a `MaterialProvider` graph, and water is a fluid `Material` placed by the `Empty` branch of the material provider (see [Top-Level Structure](#top-level-structure)).
- **Symptom:** a top-level key like `Terrain` or `MaterialProvider` is missing and the biome fails to load → `Name`, `Terrain`, and `MaterialProvider` are required. Fix: provide all three; `Density`, `Props`, `EnvironmentProvider`, and `TintProvider` are optional.

---

## Related Documentation

- [World Generation Overview](worldgen.md) — node-graph model and asset layout
- [Zones / World Structures](worldgen-zones.md) — how biomes are assigned across the world
- [Block System](blocks.md) — block ids used as materials
