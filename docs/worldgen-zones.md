# World Structures (Zones)

The "zone" in Hytale's data is a **world structure** file under
`Server/HytaleGenerator/WorldStructures/`. A world structure assigns biomes across the
world by mapping a density value to **ranges**, names a default/fallback biome, controls
transition widths, and declares world-wide constants and spawn data through a `Framework`.

The shipped per-region structures are `Zone1_Plains1.json`, `Zone2_Desert1.json`,
`Zone3_Taiga1.json`, `Zone4_Volcanic1.json`; there are also `Default.json`,
`Default_Flat.json`, `Default_Void.json`, `Basic.json`, and several `Portals_*.json`.

See [worldgen.md](worldgen.md) for the node-graph vocabulary and
[worldgen-biomes.md](worldgen-biomes.md) for what each referenced biome contains.

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
| `DefaultBiome` | yes | Biome name used outside any range / as fallback |
| `DefaultTransitionDistance` | yes | Default blend width (blocks) between biomes |
| `MaxBiomeEdgeDistance` | yes | Maximum distance over which biome edges are resolved |
| `Density` | yes | Density graph whose value selects the biome (the "biome map") |
| `Framework` | yes | Array of world-constant / positions blocks (see [Framework](#framework)) |
| `SpawnPositions` | optional | Where players spawn |
| `BiomeTransitions` | optional | Explicit transition list (seen empty in `Dev/Interpolation.json`) |

\* `Biomes` is present on most files; `Default_Flat`, `Default_Void`, and `Basic` ship it
empty and rely solely on `DefaultBiome`.

> There is **no** `ZonePatternGenerator`, `BiomePatternGenerator`, Voronoi `CellSize`,
> `ZoneDiscoveryConfig`, `UniquePrefabContainer`, or `CaveGenerator` block. Biome
> distribution is driven entirely by the `Density` field and the `Biomes` ranges.

---

## Biome Assignment (NoiseRange)

With `Type: "NoiseRange"`, each entry in `Biomes` maps a half-open band of the `Density`
value to a biome by name. Where the density falls between two entries, the named biomes
blend over `DefaultTransitionDistance` blocks.

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
| `Biome` | Name of the biome file (without extension) under `Biomes/` |
| `Min` | Lower density bound (inclusive in practice) |
| `Max` | Upper density bound |

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
(`"ExportAs": "Biome-Map"`). It mixes continent, river, and ocean fields built from several
`SimplexNoise2D` sources through `Mix`/`Min`/`Normalizer`/`Clamp`/`Distance` nodes, and it
also exports sub-fields such as `World-Continent-Map` and `World-River-Map`. Portal
structures import a different map (`Biome-Map-Portals`).

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
| `Offset` | `OffsetY`, `Positions` | Shift child positions (e.g. lift spawns up) |
| `Bound` | `Bounds.PointA`/`PointB`, `Positions` | Restrict positions to a box |
| `FieldFunction` | `FieldFunction`, `Delimiters[]` (`Min`/`Max`), `Positions` | Keep points where a sampled field is in range |
| `Mesh2D` / `Mesh` | `PointsY`, `PointGenerator` | Generate a candidate point grid |
| `Distance` | `Curve` (`Manual` with `In`/`Out` points) | Distance-based field used to gate points |

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

## Related Documentation

- [World Generation Overview](worldgen.md) — node-graph model and asset layout
- [Biomes](worldgen-biomes.md) — what each referenced biome defines
- [Block System](blocks.md) — block ids used as materials
