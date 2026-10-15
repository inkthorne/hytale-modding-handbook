---
title: "World Structures (Zones)"
description: "Define Hytale biome zones in JSON — biome assignment by mapping density to NoiseRange ranges, a DefaultBiome fallback, transition-width controls, and the biome-map density graph."
seo:
  type: TechArticle
---

# World Structures (Zones)

**Doc type:** JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.7.2**

The "zone" in Hytale's data is a **world structure** file under
`Server/HytaleGenerator/WorldStructures/`. A world structure assigns biomes across the
world by mapping a density value to **ranges**, names a default/fallback biome, controls
transition widths, and declares world-wide constants and spawn data through a `Framework`.

The shipped per-region structures are `Regions/Zone1_Plains1.json`, `Regions/Zone2_Desert1.json`,
`Regions/Zone3_Taiga1.json` and `Regions/Zone4_Volcanic1.json`; the portal worlds are
`Portals/Portals_Hedera.json`, `Portals_Henges`, `Portals_Jungles`, `Portals_Oasis` and
`Portals_Taiga`; `Debug/` holds `Test_Features.json` and five single-biome `Debug_*.json`
structures; and the folder root has `Default.json`, `Default_Flat.json`, `Default_Void.json`,
`Basic.json`, `Portals_Goblins.json`, `Portals_Goblins_Encounters.json` and
`Portals_Goblins_Encounters_Cave.json` — 22 files in all. The subfolders are only
organisation: a structure's id is still its file name, so an instance config names
`"WorldStructure": "Zone1_Plains1"`, not a path (0.7.2 moved the region and portal files into
`Regions/` and `Portals/` without renaming them).

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
| `Framework` | optional | Array of world-constant / positions blocks (see [Framework](#framework)); the codec flags it non-required, but all 22 shipped files carry it. A `BaseHeight` node whose `BaseHeightName` matches no declared constant silently reads `0` (`BaseHeightDensityAsset.build`), so in a structure without a `Base` constant every biome graph that measures from `Base` measures from Y 0 instead |
| `SpawnPositions` | optional | Where players spawn (flagged non-required, like `Framework`; present on 17 of the 22 shipped files) |
| `Tags` | optional | Generic asset tags (the 8 files that carry them — `Basic.json`, the five `Debug/Debug_*.json` and the two `Portals_Goblins_Encounters*.json` — all have `{"Template": []}`); a `Map<String, String[]>` from the shared `AssetBuilderCodec`, not read by the generator |

"Required" above records the codec's `required` flag (a `true` third argument to the key's
`KeyedCodec`). In 0.7.2 that flag governs how an explicit `null` is decoded; it does not make
the loader reject a file that omits the key — the field keeps its default, as `Default.json`
shows by omitting `Biomes`.

\* `Biomes` is present on most files; `Default_Flat`, `Default_Void`, `Basic`, the five
`Debug_*` structures and the two `Portals_Goblins_Encounters*` structures ship it empty, and
`Default.json` omits it entirely — all of them rely solely on `DefaultBiome`.

The seven non-`Tags` keys are exactly the keys of the `NoiseRange` codec
(`com.hypixel.hytale.builtin.hytalegenerator.assets.worldstructures.basic.BasicWorldStructureAsset`;
each `Biomes` entry is a `BiomeRangeAsset` with `Biome`/`Min`/`Max`); `Tags` is inherited
from the shared `AssetBuilderCodec`. `NoiseRange` is also the *only* registered
`WorldStructureAsset` type, and all 22 shipped files use it. A `BiomeTransitions` key
documented for 0.5.9 appears in neither the 0.7.2 codec nor any shipped file.

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
  { "Biome": "Plains1_Trork",  "Min": -1,     "Max": -0.875 },
  { "Biome": "Plains1_Oak",    "Min": -0.875, "Max": -0.75  },
  { "Biome": "Plains1_Gorges", "Min": -0.75,  "Max": -0.625 },
  { "Biome": "Plains1_Hills",  "Min": -0.625, "Max": -0.5   },
  { "Biome": "Plains1_River",  "Min": -0.5,   "Max": 0      }
]
```

| Field | Description |
|-------|-------------|
| `Biome` | The biome. Its codec is a `ContainedAssetCodec`, so this is either the **id** of a biome asset (the file name without extension, e.g. `"Plains1_Oak"`) *or* an inline biome object. Every shipped file uses the id form. |
| `Min` | Lower density bound (**inclusive**) |
| `Max` | Upper density bound (**inclusive**) |

Ranges are usually ordered low→high and typically over-extend their outer bounds (e.g.
`-2`/`2` in `Zone2_Desert1`) so the field never falls outside coverage; the portal structures
list theirs high→low, which is equally valid. `DefaultBiome` covers anything unmatched — in
`Zone1_Plains1` that is everything above `0`, since its last band stops there.

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

The biome maps live in `Density/Maps/` (moved there from `Density/` in 0.7.2; the export
names did not change). `Biome-Map` is defined in `Density/Maps/Map_Default.json` as an
`Exported` density node (`"ExportAs": "Biome-Map"`, `"SingleInstance": true`). It builds a
continent field from `SimplexNoise2D` sources through `Normalizer`/`Min`/`Clamp`/`Selector`
nodes, exports it as `World-Continent-Map`, and combines it with the imported
`Biome-Map-Tiles-Rivers`. The river sub-field `World-River-Map` is exported by
`Map_Default_Tiles_Rivers.json`, which itself imports `Biome-Map-Tiles`.

Which map each shipped structure reads (as of 0.7.2):

| Structure(s) | `Density` | Defined in |
|--------------|-----------|------------|
| `Zone2_Desert1`, `Zone3_Taiga1`, `Zone4_Volcanic1`, `Basic`, `Default`, `Debug_River`, `Portals_Goblins_Encounters`, `Portals_Goblins_Encounters_Cave` | `Imported "Biome-Map"` | `Density/Maps/Map_Default.json` |
| `Zone1_Plains1`, `Portals_Taiga` | `Imported "Biome-Map-Tiles-Rivers"` | `Density/Maps/Map_Default_Tiles_Rivers.json` |
| `Portals_Jungles`, `Debug_Gorges`, `Debug_Hills`, `Debug_Oak`, `Debug_Trork` | `Imported "Biome-Map-Tiles"` | `Density/Maps/Map_Default_Tiles.json` (a cell-based layout) |
| `Portals_Hedera`, `Portals_Henges`, `Portals_Oasis` | `Imported "Biome-Map-Portals"` | `Density/Maps/Map_Portals.json` |
| `Portals_Goblins` | `Imported "Portal_Goblin_Biome_Distance"` | `Density/Portal_Goblin_Biome_Distance.json` |
| `Default_Flat`, `Default_Void` | inline `Constant 0` | — |
| `Test_Features` | inline `YOverride` → `Cache` → `PositionsCellNoise` | — |

Two maps no structure reads: `Density/Maps/Map_Portals_Oasis.json`
(`Biome-Map-Portals-Oasis`) — `Portals_Oasis.json` uses the plain `Biome-Map-Portals`
despite the name — and `Density/Maps/Map_Default_Spawn.json` (`Biome-Map-Spawn`, which
imports `Biome-Map` and `Global-Spawns`).

Density can also be inline rather than imported. `Default_Flat.json` and
`Default_Void.json` use a flat field:

```json
"Density": { "Type": "Constant", "Value": 0 }
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
(e.g. `"Base"`, `"Bedrock"`). The entries are not limited to heights: `Zone1_Plains1` and
the five `Debug_*` structures also declare the ore budgets `Copper_Count` and `Iron_Count`,
which the Plains1 biomes read through the same `BaseHeightName` mechanism, and all of them
but `Debug_Trork` declare `Lava` (`20`).

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
| `Imported` | `Name` | Pull a positions graph published with `ExportAs` |
| `Framework` | `Name` | Pull a `Framework` `Positions` entry by its entry `Name` (no `ExportAs` needed); a missing name logs `Couldn't find WorldStructure Framework Positions with name ` and yields no positions |
| `BaseHeight` | `BedName`, `Positions` (plus `MinYRead`/`MaxYRead`) | Lift child positions by the named `DecimalConstants` value |
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

### Regional zone — `WorldStructures/Regions/Zone1_Plains1.json`

```json
{
  "Type": "NoiseRange",
  "Biomes": [
    { "Biome": "Plains1_Trork",  "Min": -1,     "Max": -0.875 },
    { "Biome": "Plains1_Oak",    "Min": -0.875, "Max": -0.75  },
    { "Biome": "Plains1_Gorges", "Min": -0.75,  "Max": -0.625 },
    { "Biome": "Plains1_Hills",  "Min": -0.625, "Max": -0.5   },
    { "Biome": "Plains1_River",  "Min": -0.5,   "Max": 0      }
  ],
  "DefaultBiome": "Basic",
  "DefaultTransitionDistance": 32,
  "MaxBiomeEdgeDistance": 32,
  "Density": { "Type": "Imported", "Name": "Biome-Map-Tiles-Rivers" },
  "SpawnPositions": {
    "Type": "BaseHeight", "BedName": "Base",
    "Positions": {
      "Type": "Offset", "Offset": { "X": 0, "Y": 50, "Z": 0 },
      "Positions": { "Type": "Framework", "Name": "Zone1-Forests-Spawns" }
    }
  },
  "Framework": [
    {
      "Type": "Positions",
      "Entries": [
        { "Name": "World-Biome-Cells", "Positions": { "...": "a jittered, scaled TriangularGrid2d" } },
        { "Name": "Zone1-Forests-Spawns",
          "Positions": { "Type": "List", "Positions": [ { "X": 0.5, "Y": 0, "Z": 290.5 } ] } }
      ]
    },
    {
      "Type": "DecimalConstants",
      "Entries": [
        { "Name": "Base",         "Value": 100 },
        { "Name": "Water",        "Value": 100 },
        { "Name": "Lava",         "Value": 20  },
        { "Name": "Bedrock",      "Value": 0   },
        { "Name": "Copper_Count", "Value": 30  },
        { "Name": "Iron_Count",   "Value": 5   }
      ]
    }
  ]
}
```

(The shipped `Offset` also carries `OffsetX`/`OffsetY`/`OffsetZ` of `0` beside the vector, and
most nodes carry `"Skip": false`; both are omitted above.)

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
`HytaleGenerator` plugin log (verified against `HytaleServer.jar` 0.7.2). All of them are
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
