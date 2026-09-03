---
title: "World Structures (Zones)"
description: "Define Hytale biome zones in JSON — biome assignment by mapping density to NoiseRange ranges, a DefaultBiome fallback, transition-width controls, and the biome-map density graph."
seo:
  type: TechArticle
---

# World Structures (Zones)

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.6.3**

The "zone" in Hytale's data is a **world structure** file under
`Server/HytaleGenerator/WorldStructures/`. A world structure assigns biomes across the
world by mapping a density value to **ranges**, names a default/fallback biome, controls
transition widths, and declares world-wide constants and spawn data through a `Framework`.

The shipped per-region structures are `Zone1_Plains1.json`, `Zone2_Desert1.json`,
`Zone3_Taiga1.json`, `Zone4_Volcanic1.json`; there are also `Default.json`,
`Default_Flat.json`, `Default_Void.json`, `Basic.json`, and several `Portals_*.json`.

See [worldgen.md](worldgen.md) for the node-graph vocabulary and
[worldgen-biomes.md](worldgen-biomes.md) for what each referenced biome contains.

## Overview

Defined as JSON files under `Server/HytaleGenerator/WorldStructures/` and provides:
- Biome assignment across the world by mapping a density value to ranges (`NoiseRange`)
- A `DefaultBiome` fallback and transition-width controls
- A `Density` graph (the "biome map") that drives biome selection
- A `Framework` declaring world constants and named position graphs
- `SpawnPositions` selecting where players spawn

## Architecture
```
World structure file (WorldStructures/*.json, Type: NoiseRange)
├── Density          biome-map field (usually Imported "Biome-Map")
├── Biomes[]         density Min/Max range -> biome name
├── DefaultBiome     fallback outside any range
├── DefaultTransitionDistance / MaxBiomeEdgeDistance   blend widths
├── Framework[]
│   ├── DecimalConstants   Base / Water / Bedrock (sampled by biome BaseHeight)
│   └── Positions          named position graphs (e.g. Spawns)
└── SpawnPositions   positions graph (List / Imported / Offset / Bound / ...)
```

## Key Classes
These are JSON worldgen node types (not Java classes); the table lists the key node types documented on this page.

| Node type | Where | Description |
|-----------|-------|-------------|
| `NoiseRange` | top-level `Type` | The world-structure kind; assigns biomes by density range |
| (biome entry) | `Biomes[]` | `{ Biome, Min, Max }` mapping a density band to a biome name |
| `Imported` | `Density` | Pulls in the shared biome map (`Biome-Map`) |
| `Constant` / `SimplexNoise2D` | `Density` | Inline density field alternatives |
| `DecimalConstants` | `Framework` | Named world constants (`Base`, `Water`, `Bedrock`) |
| `Positions` | `Framework` | Named position graphs (published via `ExportAs`) |
| `List` / `Offset` / `Bound` | `SpawnPositions` | Fixed points, shift, and box-restrict positions |
| `FieldFunction` / `Mesh2D` / `Distance` | `SpawnPositions` | Gate and generate candidate spawn points |

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Top-Level Structure](#top-level-structure) | The keys a world structure uses |
| [Biome Assignment](#biome-assignment-noiserange) | Mapping density to biomes |
| [Density](#density) | The field that drives biome selection |
| [Framework](#framework) | World constants, positions, spawns |
| [SpawnPositions](#spawnpositions) | Player spawn point selection |
| [Complete Examples](#complete-examples) | Real files |

---

## Top-Level Structure

Every world structure file uses the same small set of top-level keys:

| Key | Required | Description |
|-----|----------|-------------|
| `Type` | yes | Always `"NoiseRange"` in the shipped files |
| `Biomes` | yes* | Array of biome assignments by density range (may be empty) |
| `DefaultBiome` | yes | Fallback biome, used outside any range. Also a `ContainedAssetCodec` — a biome id or an inline biome definition. |
| `DefaultTransitionDistance` | yes | Default blend width in blocks between biomes (clamped to `>= 1` at build time) |
| `MaxBiomeEdgeDistance` | yes | Maximum distance over which biome edges are resolved |
| `Density` | yes | Density graph whose value selects the biome (the "biome map") |
| `Framework` | yes | Array of world-constant / positions blocks (see [Framework](#framework)) |
| `SpawnPositions` | optional | Where players spawn (the only key the codec marks non-required; present on 8 of the 15 shipped files) |
| `Tags` | optional | Generic asset tags (`Basic.json`, the only file that carries them, has `{"Template": []}`); a `Map<String, String[]>` from the shared `AssetBuilderCodec`, not read by the generator |

\* `Biomes` is present on most files; `Default_Flat`, `Default_Void`, and `Basic` ship it
empty, and `Default.json` omits it entirely — all four rely solely on `DefaultBiome`.

The seven non-`Tags` keys are exactly the keys of the `NoiseRange` codec
(`com.hypixel.hytale.builtin.hytalegenerator.assets.worldstructures.basic.BasicWorldStructureAsset`;
each `Biomes` entry is a `BiomeRangeAsset` with `Biome`/`Min`/`Max`); `Tags` is inherited
from the shared `AssetBuilderCodec`. `NoiseRange` is also the *only* registered
`WorldStructureAsset` type, and all 15 shipped files use it. A `BiomeTransitions` key
documented for 0.5.9 appears in neither the 0.6.3 codec nor any shipped file.

> There is **no** `ZonePatternGenerator`, `BiomePatternGenerator`, Voronoi `CellSize`,
> `ZoneDiscoveryConfig`, `UniquePrefabContainer`, or `CaveGenerator` block. Biome
> distribution is driven entirely by the `Density` field and the `Biomes` ranges.

---

## Biome Assignment (NoiseRange)

With `Type: "NoiseRange"`, each entry in `Biomes` maps a band of the `Density` value to a
biome. The band is **fully inclusive** on both ends — `BiomeRangeAsset.getRange()` returns
`DoubleRange.inclusive(Min, Max)`, so shipped files deliberately butt one entry's `Max`
against the next entry's `Min`. Where the density falls between two entries, the named
biomes blend over `DefaultTransitionDistance` blocks (clamped to a minimum of `1`).

```json
"Type": "NoiseRange",
"Biomes": [
  { "Biome": "Plains1_Oak",      "Min": -1,    "Max": -0.82 },
  { "Biome": "Plains1_Gorges",   "Min": -0.82, "Max": -0.66 },
  { "Biome": "Plains1_Deeproot", "Min": -0.66, "Max": -0.5  },
  { "Biome": "Plains1_River",    "Min": -0.5,  "Max": 0     },
  { "Biome": "Plains1_Shore",    "Min": 0,     "Max": 0.15  },
  { "Biome": "Oceans",           "Min": 0.15,  "Max": 2     }
]
```

| Field | Description |
|-------|-------------|
| `Biome` | The biome. Its codec is a `ContainedAssetCodec`, so this is either the **id** of a biome asset (the file name without extension, e.g. `"Plains1_Oak"`) *or* an inline biome object. Every shipped file uses the id form. |
| `Min` | Lower density bound (**inclusive**) |
| `Max` | Upper density bound (**inclusive**) |

Ranges are ordered low→high and typically over-extend their outer bounds (e.g. `-1`/`2`)
so the field never falls outside coverage. `DefaultBiome` covers anything unmatched.

---

## Density

`Density` is an ordinary density graph (see [worldgen.md](worldgen.md#node-families)). Its
output value is what the `Biomes` ranges are read against. The standard regional zones pull
in the shared world biome map by name:

```json
"Density": {
  "Type": "Imported",
  "Name": "Biome-Map"
}
```

`Biome-Map` is defined once in `Density/Map_Default.json` as an `Exported` density node
(`"ExportAs": "Biome-Map"`, `"SingleInstance": true`). It mixes continent, river, and ocean
fields built from several `SimplexNoise2D` sources through `Mix`/`Min`/`Normalizer`/`Clamp`/
`Distance` nodes, and also exports the sub-fields `World-Continent-Map` and `World-River-Map`.

Which map each shipped structure reads (as of 0.6.3):

| Structure(s) | `Density` | Defined in |
|--------------|-----------|------------|
| `Zone1_Plains1`, `Zone2_Desert1`, `Zone3_Taiga1`, `Zone4_Volcanic1`, `Basic`, `Default` | `Imported "Biome-Map"` | `Density/Map_Default.json` |
| `Portals_Hedera`, `Portals_Henges`, `Portals_Oasis` | `Imported "Biome-Map-Portals"` | `Density/Map_Portals.json` |
| `Portals_Jungles` | `Imported "Biome-Map-Tiles"` | `Density/Map_Default_Tiles.json` (a cell-based layout that also exports `World-Biome-Cells`) |
| `Portals_Taiga` | `Imported "Biome-Map-Tiles-Rivers"` | `Density/Map_Default_Tiles_Rivers.json` |
| `Default_Flat`, `Default_Void` | inline `Constant 0` | — |
| `Test_Features` | inline `YOverride` → `Cache` → `PositionsCellNoise` | — |
| `Dev/Interpolation` | inline `SimplexNoise2D` | — |

`Map_Default.json` itself imports `Biome-Map-Tiles`, so the tile map feeds the main map as
well as `Portals_Jungles`. The one map no structure reads is
`Density/Map_Portals_Oasis.json` (`Biome-Map-Portals-Oasis`) — `Portals_Oasis.json` uses the
plain `Biome-Map-Portals` despite the name.

Density can also be inline rather than imported. `Default_Flat.json` and
`Default_Void.json` use a flat field, and `Dev/Interpolation.json` inlines a noise field:

```json
"Density": { "Type": "Constant", "Value": 0 }
```

```json
"Density": {
  "Type": "SimplexNoise2D",
  "Skip": false,
  "Lacunarity": 2, "Persistence": 0.5, "Octaves": 1, "Scale": 400, "Seed": "A"
}
```

---

## Framework

`Framework` is an array of typed blocks that declare world-wide values. Two block types
appear in the assets.

### DecimalConstants

Named decimal constants. The three that every regional structure defines are `Base`
(reference/surface height that biome terrain graphs sample via `BaseHeight`), `Water`
(sea level), and `Bedrock`:

```json
"Framework": [
  {
    "Type": "DecimalConstants",
    "Entries": [
      { "Name": "Base",    "Value": 100 },
      { "Name": "Water",   "Value": 100 },
      { "Name": "Bedrock", "Value": 0   }
    ]
  }
]
```

`Base` varies per structure — e.g. `Default_Flat` uses `80`, `Zone4_Volcanic1` uses `120`.
Biome terrain and material graphs reference these names through `BaseHeightName`
(e.g. `"Base"`, `"Bedrock"`).

### Positions

Named position graphs, used for things like spawn points. Each entry has a `Name` and a
`Positions` graph; the graph may publish itself with `ExportAs` so `SpawnPositions` can
import it. From `Default.json`:

```json
{
  "Type": "Positions",
  "Entries": [
    {
      "Name": "Spawns",
      "Positions": {
        "Type": "List",
        "ExportAs": "Spawns",
        "Positions": [
          { "X": 0, "Y": 140, "Z": 0 }
        ]
      }
    }
  ]
}
```

---

## SpawnPositions

`SpawnPositions` selects where players spawn. It is itself a positions graph. The simplest
form imports a named positions entry from the `Framework`:

```json
"SpawnPositions": { "Type": "Imported", "Name": "Spawns" }
```

Position graph node types observed in world structures:

| Type | Key fields | Purpose |
|------|-----------|---------|
| `List` | `Positions[]` of `{X,Y,Z}` | Explicit fixed points |
| `Imported` | `Name` | Pull a named positions graph |
| `Offset` | `OffsetX` / `OffsetY` / `OffsetZ` (plus a vector `Offset`), `Positions` | Shift child positions (e.g. lift spawns up) |
| `Bound` | `Bounds.PointA`/`PointB`, `Positions` | Restrict positions to a box |
| `FieldFunction` | `FieldFunction`, `Delimiters[]` (`Min`/`Max`), `Positions` | Keep points where a sampled field is in range |
| `Mesh2D` / `Mesh` | `PointsY`, `PointGenerator` | Generate a candidate point grid |
| `Distance` | `Curve` (`Manual` with `In`/`Out` points) | Distance-based field used to gate points |

`Test_Features.json` instead drives its `Density` from a `PositionsCellNoise` node over a
`List` of positions (a Voronoi-style field around fixed points). The complete position-node
vocabulary (grids, jitter, `Scaler`, `Union`, `Clusters`, …) is listed in
[worldgen-prefabs.md](worldgen-prefabs.md#positions--propdistributions).

`Portals_Oasis.json` shows these composed: a `Bound` box constrains an outer
`FieldFunction` (gated on an imported `Desert1_Oasis_Pillar_Distance` field), which in turn
constrains a `Distance`-curve `FieldFunction`, whose candidate points come from a `Mesh2D`
grid — and the whole thing is lifted by an `Offset` of `OffsetY: 60`.

```json
"SpawnPositions": {
  "Type": "Offset",
  "OffsetY": 60,
  "Positions": { "Type": "Imported", "Name": "Portals-Oasis-Spawns" }
}
```

---

## Complete Examples

### Regional zone — `WorldStructures/Zone1_Plains1.json`

```json
{
  "Type": "NoiseRange",
  "Biomes": [
    { "Biome": "Plains1_Oak",      "Min": -1,    "Max": -0.82 },
    { "Biome": "Plains1_Gorges",   "Min": -0.82, "Max": -0.66 },
    { "Biome": "Plains1_Deeproot", "Min": -0.66, "Max": -0.5  },
    { "Biome": "Plains1_River",    "Min": -0.5,  "Max": 0     },
    { "Biome": "Plains1_Shore",    "Min": 0,     "Max": 0.15  },
    { "Biome": "Oceans",           "Min": 0.15,  "Max": 2     }
  ],
  "DefaultBiome": "Basic",
  "DefaultTransitionDistance": 32,
  "MaxBiomeEdgeDistance": 32,
  "Density": { "Type": "Imported", "Name": "Biome-Map" },
  "Framework": [
    {
      "Type": "DecimalConstants",
      "Entries": [
        { "Name": "Base",    "Value": 100 },
        { "Name": "Water",   "Value": 100 },
        { "Name": "Bedrock", "Value": 0   }
      ]
    }
  ]
}
```

### Fallback-only structure — `WorldStructures/Default_Flat.json`

No ranges; a flat density and a single default biome.

```json
{
  "Type": "NoiseRange",
  "Biomes": [],
  "DefaultBiome": "Default_Flat",
  "DefaultTransitionDistance": 32,
  "MaxBiomeEdgeDistance": 32,
  "Density": { "Type": "Constant", "Value": 0 },
  "Framework": [
    {
      "Type": "DecimalConstants",
      "Entries": [
        { "Name": "Base",    "Value": 80 },
        { "Name": "Water",   "Value": 80 },
        { "Name": "Bedrock", "Value": 0  }
      ]
    }
  ]
}
```

---

## Gotchas & Errors

Backtick-quoted strings below are the literal messages `BasicWorldStructureAsset` and the
`HytaleGenerator` plugin log (verified against `HytaleServer.jar` 0.6.3). All of them are
**warnings** — the world still generates, just wrong — so watch the server log rather than
waiting for a load failure.

- **`Reverting to empty WorldStructure because couldn't find default Biome asset with id: `** — assembled line appends the id → `DefaultBiome` names a biome that is not in the asset store. The *entire* structure is thrown away and replaced by `WorldStructure.DEFAULT_INSTANCE`, so every `Biomes` range is lost too. Fix: match the biome file name exactly (see the next gotcha).
- **`Couldn't find Biome asset with name `** — assembled line appends the id → one `Biomes` entry's `Biome` id does not resolve. Only that band is dropped; the rest of the structure loads, so the symptom is a missing biome, not a broken world.
- **`World Structure asset not found: `** (assembled line appends the structure name) / **`World Structure asset not loaded.`** (complete literal) → the world's generator profile names a structure that is not in `WorldStructures/`, or the store has not finished loading. Fix: check the structure name in the world's config against the file name.
- **`Couldn't find Density asset exported with name: '`** — assembled line `Couldn't find Density asset exported with name: '<name>'. Using empty Node instead.` → the structure's `Density` is an `Imported` node naming a field nothing exports. It degrades to a constant `0` field, so the whole world collapses onto whichever single `Biomes` band contains `0` (or `DefaultBiome` if none does). Fix: confirm the `Density/*.json` that publishes that `ExportAs` is present. The `SpawnPositions` equivalent is **`Couldn't find Positions asset exported with name: '`**.
- **Symptom:** a `"Biome": "Plains1_Oak"` entry resolves to the default biome even though `Plains1_Oak.json` exists → references use the **file name** (without extension), not the file's `Name` display field, and the match is case-sensitive.
- **Symptom:** you added a `ZonePatternGenerator`, `BiomePatternGenerator`, Voronoi `CellSize`, `ZoneDiscoveryConfig`, or `CaveGenerator` block and it is ignored → none of those exist in the format. Fix: biome distribution is driven entirely by the `Density` field and the `Biomes` ranges (see [Top-Level Structure](#top-level-structure)).

> The `Invalid json-type for Biomes property`, `Unexpected type for 'UniqueZones' field` and
> `Could not resolve all unique climate zones` messages that older versions of this page
> listed live in `com.hypixel.hytale.server.worldgen.loader.*` — the **legacy** folder-of-JSON
> generator behind `WorldGen.Type: "Hytale"`. There is no `UniqueZones` key on a
> `HytaleGenerator` world structure.

---

## Related Documentation

- [World Generation Overview](worldgen.md) — node-graph model and asset layout
- [Biomes](worldgen-biomes.md) — what each referenced biome defines
- [Block System](blocks.md) — block ids used as materials
