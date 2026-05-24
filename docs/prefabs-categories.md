# Prefab Categories

**Doc type:** JSON asset format · **Assets:** `Server/Prefabs`

Hytale includes ~7,824 prefab files organized into major categories for world generation. This reference documents the taxonomy of prefab types, naming conventions, and directory structures.

> **See also:** [Prefabs API](prefabs.md) for Java API and file format documentation

This page is a taxonomy of the shipped prefab assets — the major category directories, their naming conventions, and the directory structures used for world generation.

## Overview

Defined as JSON assets under `Server/Prefabs` (in `Assets.zip`) and covers:
- The major prefab categories (trees, rocks, NPC structures, monuments, mineshafts, dungeons, caves, plants, spawn)
- Naming conventions encoding category, type, variant, and size
- Growth-stage directory layout for trees and biome/material variant suffixes
- Where each category lives under `Server/Prefabs/`

## Architecture
```
Server/Prefabs/
├── Trees/            (per-species → Stage_N subdirs, Stumps)
├── Rocks/            (formations, arches, fossils, pillars, mushrooms)
├── NPC structures    (faction buildings, villages, outposts)
├── Monuments         (towers, temples, encounters, camps)
├── Mineshafts/       (modular mine components; + Mineshaft_Drift)
├── Dungeons/         (modular dungeon rooms)
├── Caves/            (formations, nests, nodes)
├── Plants/           (bushes, cacti, coral, driftwood)
├── Spawn/            (player spawn layouts)
└── Unique, Blocksets, Testing, TestTree
```

## Key Classes
| Class | Location | Description |
|-------|----------|-------------|
| Trees | `Server/Prefabs/Trees/` | Growth stages, species, biome variants (~1126) |
| Rock Formations | `Server/Prefabs/` (Rocks) | Rocks, arches, fossils, pillars, mushrooms (~1676) |
| NPC Structures | `Server/Prefabs/` | Faction buildings, villages, outposts (~856) |
| Monuments | `Server/Prefabs/` | Towers, temples, encounters, camps (~806) |
| Mineshafts | `Server/Prefabs/` | Modular mine components (~1160) |
| Dungeons | `Server/Prefabs/` | Modular dungeon rooms (~858) |
| Caves | `Server/Prefabs/` | Formations, nests, nodes (~492) |
| Plants | `Server/Prefabs/` | Bushes, cacti, coral, driftwood (~555) |
| Spawn | `Server/Prefabs/` | Player spawn layouts (~20) |

---

## Quick Navigation

| Category | Count | Description |
|----------|-------|-------------|
| [Trees](#trees) | ~1126 | Growth stages, species, biome variants |
| [Rock Formations](#rock-formations) | ~1676 | Rocks, arches, fossils, pillars, mushrooms |
| [NPC Structures](#npc-structures) | ~856 | Faction buildings, villages, outposts |
| [Monuments](#monuments) | ~806 | Towers, temples, encounters, camps |
| [Mineshafts](#mineshafts) | ~1160 | Modular mine components |
| [Dungeons](#dungeons) | ~858 | Modular dungeon rooms |
| [Caves](#caves) | ~492 | Formations, nests, nodes |
| [Plants](#plants) | ~555 | Bushes, cacti, coral, driftwood |
| [Spawn](#spawn) | ~20 | Player spawn layouts |

Additional top-level directories include `Mineshaft_Drift`, `Unique`, `Blocksets`, `Testing`, and `TestTree`.

**Location:** `Assets.zip > Server/Prefabs/`

---

## Naming Conventions

Prefab files follow consistent naming patterns that encode category, type, variant, and size information.

### General Pattern

```
{Category}_{Type}_{Variant}_{Size}_{Number}.prefab.json
```

### Common Patterns

| Pattern | Example | Description |
|---------|---------|-------------|
| `{Tree}_Stage{N}_{NNN}` | `Oak_Stage2_001` | Tree growth stage (0-7+) |
| `{Type}_{Biome}` | `Rock_Desert` | Biome-specific variant |
| `{Type}_{Material}` | `Rock_Basalt` | Material variant |
| `{Type}_{Size}` | `Rock_Large` | Size variant (Small, Medium, Large) |
| `{Faction}_{Building}` | `Kweebec_House` | Faction structure |
| `{Type}_{Number}` | `Rock_01` | Numbered variants |

### Growth Stage Naming (Trees)

Each species directory contains one **subdirectory per growth stage** (`Stage_0`, `Stage_1`, ... up to `Stage_7` for some species, plus optional `Stage_00` and `Stumps`). Each subdirectory holds numbered prefab files, e.g. `Trees/Oak/Stage_2/Oak_Stage2_001.prefab.json`.

| Stage | Age | Description |
|-------|-----|-------------|
| `Stage_0` | Sapling | Newly planted, small |
| `Stage_1` | Young | Growing, moderate size |
| `Stage_2`-`Stage_3` | Mature | Full-grown, standard |
| `Stage_4`-`Stage_7` | Ancient | Large, may have special features |
| `Stumps` | Remnant | Cut/decayed stumps |

### Biome Variant Suffixes

| Suffix | Biome |
|--------|-------|
| `_Desert` | Arid/desert regions |
| `_Volcanic` | Volcanic/lava regions |
| `_Swamp` | Wetland/swamp regions |
| `_Winter` | Cold/snow regions |
| `_Eternal` | Magical/eternal regions |
| `_Cave` | Underground variants |
| `_Underwater` | Aquatic variants |

---

## Trees

**Location:** `Prefabs/Trees/`
**Count:** ~1126 files

Trees are organized by species. Each species directory contains growth-stage subdirectories (`Stage_0`, `Stage_1`, ...), each holding numbered prefab files.

### Directory Structure

```
Prefabs/Trees/
├── Oak/
│   ├── Stage_0/
│   │   ├── Oak_Stage0_001.prefab.json
│   │   └── ...
│   ├── Stage_1/
│   ├── Stage_2/
│   │   ├── Oak_Stage2_001.prefab.json
│   │   ├── Oak_Stage2_002.prefab.json
│   │   └── ...
│   ├── ...
│   └── Stumps/
├── Birch/
├── Fir/
├── Palm/
├── Banyan/
├── Willow/
├── Maple/
├── Redwood/
├── Jungle/
├── Boab/
└── ...
```

### Tree Species

Real species directories (partial list of ~80) under `Prefabs/Trees/`:

| Species | Notes |
|---------|-------|
| `Oak` | Common forest tree; also `Oak_Moss`, `Oak_Stumps` |
| `Birch` | White bark |
| `Fir` | Coniferous; many variants (`Fir_Snow`, `Fir_Autumn`, `Fir_Dead`, `Fir_Logs`) |
| `Palm` | Coastal; also `Palm_Green` |
| `Banyan` | Large canopy |
| `Willow` | Drooping branches |
| `Maple` | Autumn colors; also `Maple_Stumps` |
| `Redwood` | Giant trees; also `Redwood_Logs`, `Redwood_Stumps` |
| `Jungle` | Dense canopy; many variants (`Jungle1`-`Jungle3`, `Jungle_Crystal`, `Jungle_Mushroom`) |
| `Boab` | Thick trunk (savanna) |
| `Ash` | Many variants (`Ash_Dead`, `Ash_swamp`, `Ash_twisted`, ...) |
| `Aspen`, `Beech`, `Cedar`, `Crystal`, `Petrified`, `Wisteria` | Additional species |

### Tree Variants

| Variant | Description |
|---------|-------------|
| `_Dead` | Leafless, decayed appearance |
| `_Moss` | Covered in moss |
| `_Autumn` | Fall foliage colors |
| `_Snow` | Snow-covered branches |
| `_Fruit` | Bearing fruit |

### Example: Oak Tree at Stage 2

**File:** `Prefabs/Trees/Oak/Stage_2/Oak_Stage2_001.prefab.json`

This prefab contains:
- Trunk blocks with appropriate rotations
- Branch blocks extending outward
- Leaf blocks forming the canopy
- Anchor at base of trunk for proper ground placement

---

## Rock Formations

**Location:** `Prefabs/Rock_Formations/`
**Count:** ~1676 files

Rock formations provide natural terrain features including standalone rocks, arches, fossils, pillars, and geological features. Material variants live in subdirectories under `Rocks/`.

### Directory Structure

```
Prefabs/Rock_Formations/
├── Rocks/
│   ├── Stone/
│   ├── Sandstone/
│   ├── Quartzite/
│   ├── Volcanic/
│   ├── Basalt/
│   ├── Calcite/
│   ├── Chalk/
│   ├── Gems/
│   ├── Geodes/
│   ├── Frozenstone/
│   └── ...
├── Arches/
├── Pillars/
├── Dolmen/
├── Fossils/
├── Ice_Formations/
├── Crystal_Pattern/
├── Crystal_Pits/
├── Hotsprings/
├── Crystals/
├── Mushrooms/
└── Stalactites/
```

### Subcategories

| Subcategory | Count | Description |
|-------------|-------|-------------|
| `Rocks/` | ~944 | Standard rock formations (by material) |
| `Arches/` | ~275 | Natural stone arches |
| `Pillars/` | ~215 | Tall stone columns |
| `Fossils/` | ~72 | Exposed fossil formations |
| `Mushrooms/` | ~33 | Giant mushroom formations |
| `Hotsprings/` | ~30 | Geothermal features |
| `Stalactites/` | ~23 | Hanging rock formations |
| `Ice_Formations/` | ~17 | Frozen formations |

### Material Variants (`Rocks/` subdirectories)

| Material | Biomes | Appearance |
|----------|--------|------------|
| `Stone` | Universal | Gray, standard rock |
| `Sandstone` | Desert | Tan, layered (also `Sandstone_Red`, `Sandstone_White`) |
| `Quartzite` | Mountains | White, crystalline |
| `Volcanic` | Volcanic | Dark, igneous |
| `Basalt` | Volcanic | Dark, columnar |
| `Calcite` | Caves | Light, crystalline |
| `Chalk` | Coastal | White, soft |
| `Gems` / `Geodes` | Caves | Gem-bearing rock |
| `Frozenstone` | Winter | Icy stone |

### Size Variants

| Size | Approximate Dimensions |
|------|------------------------|
| `Small` | 1-3 blocks |
| `Medium` | 4-8 blocks |
| `Large` | 9-20 blocks |
| `Massive` | 20+ blocks |

### Example: Sandstone Arch

**File:** `Prefabs/Rock_Formations/Arches/Arch_Sandstone_01.prefab.json`

Contains sandstone blocks arranged in an arch formation, with anchor at the base center for proper terrain integration.

---

## NPC Structures

**Location:** `Prefabs/Npc/`
**Count:** ~856 files

NPC structures represent buildings and camps for various factions. Each faction directory is further organized by biome/material theme (e.g. `Oak`, `Redwood`, `Swamp`).

### Directory Structure

```
Prefabs/Npc/
├── Kweebec/
│   ├── Oak/
│   │   ├── Kweebec_Oak_Well_001.prefab.json
│   │   └── ...
│   ├── Redwood/
│   ├── Swamp/
│   └── ...
├── Trork/
├── Feran/
├── Outlander/
├── Scarak/
├── Yeti/
├── Dragons/
├── Slothian/
└── Hedera/
```

### Factions

| Faction | Style | Biomes | Notes |
|---------|-------|--------|-------|
| `Kweebec` | Organic, wood | Forest | Friendly forest dwellers |
| `Trork` | Crude, bone | Swamp, Forest | Tribal camps |
| `Feran` | Refined, stone | Varied | Wolf-like humanoids |
| `Outlander` | Human, varied | Varied | Human settlements |
| `Scarak` | Hive, organic | Underground | Insectoid structures |
| `Yeti` | Ice, stone | Winter | Mountain dwellings |
| `Dragons` | Lair structures | Varied | Dragon-related sites |
| `Slothian` | Organic | Varied | Slothian structures |
| `Hedera` | Plant, vine | Varied | Hedera structures |

### Building Types

| Type | Description |
|------|-------------|
| `House` | Residential dwellings |
| `Shop` | Merchant buildings |
| `Guard_Tower` | Defensive structures |
| `Well` | Water source |
| `Storage` | Warehouses, barns |
| `Workshop` | Crafting buildings |
| `Temple` | Religious structures |
| `Inn` | Rest buildings |

### Size Variants

| Size | Interior Space | NPCs |
|------|----------------|------|
| `Small` | 1-2 rooms | 1-2 |
| `Medium` | 3-4 rooms | 2-4 |
| `Large` | 5+ rooms | 4+ |

### Example: Kweebec Well

**File:** `Prefabs/Npc/Kweebec/Oak/Kweebec_Oak_Well_001.prefab.json`

Contains:
- Wood and leaf block walls
- Interior furniture blocks
- Container blocks with faction-appropriate loot
- Door blocks with proper rotations
- Entity spawners for NPC inhabitants

---

## Monuments

**Location:** `Prefabs/Monuments/`
**Count:** ~806 files

Monuments are unique or semi-unique structures including towers, temples, encounter areas, and points of interest. Top-level categories are `Challenge`, `Encounter`, `Incidental`, `Story`, and `Unique`. Special structures such as Mage Towers and Temples live under `Unique/`.

### Directory Structure

```
Prefabs/Monuments/
├── Challenge/
├── Encounter/
├── Incidental/
│   ├── Shipwrecks/
│   ├── Treasure_Rooms/
│   ├── Grasslands/
│   └── ... (biome/material themes)
├── Story/
└── Unique/
    ├── Mage_Towers/
    │   ├── Quartzite/
    │   │   ├── Tier_2/
    │   │   │   └── Monuments_MageTower_Quartzite_Tier2_001.prefab.json
    │   │   └── Tier_3/
    │   ├── Shale/
    │   ├── Volcanic/
    │   └── Sandstone/
    ├── Temple/
    ├── Start_Camp/
    ├── World_Portal/
    └── ...
```

### Categories

| Category | Count | Description |
|----------|-------|-------------|
| `Encounter/` | ~305 | Multi-zone encounter progressions |
| `Incidental/` | ~252 | Camps, shipwrecks, treasure rooms (by biome) |
| `Unique/` | ~240 | One-of-a-kind structures (Mage Towers, Temples, Start Camp, World Portal) |
| `Challenge/` | ~6 | Combat encounter arenas |
| `Story/` | ~3 | Story-related structures |

### Encounter Types

| Type | Description |
|------|-------------|
| `Challenge` | Single-area combat encounters |
| `Encounter_Tier1` | Easy multi-zone progression |
| `Encounter_Tier2` | Medium difficulty |
| `Encounter_Tier3` | Hard difficulty |
| `Boss` | Boss encounter areas |

### Incidental Structures

`Incidental/` is organized by biome/material theme, plus a few special subdirectories:

| Subdirectory | Description |
|------|-------------|
| `Shipwrecks` | Wrecked ships |
| `Treasure_Rooms` | Hidden loot rooms |
| `Grasslands`, `Sandstone`, `Volcanic`, ... | Biome/material-themed incidental structures |

### Example: Mage Tower

Mage Towers live under `Unique/`, organized by material and tier:

**File:** `Prefabs/Monuments/Unique/Mage_Towers/Quartzite/Tier_2/Monuments_MageTower_Quartzite_Tier2_001.prefab.json`

Contains:
- Multi-story tower structure
- Material-themed block work (e.g. Quartzite, Shale, Volcanic, Sandstone)
- Interior rooms with furniture
- Loot containers with rare drops
- Potential boss spawn areas

---

## Mineshafts

**Location:** `Prefabs/Mineshaft/`
**Count:** ~1160 files

Mineshafts use a modular system where different components connect to form complete mine networks. (A separate `Prefabs/Mineshaft_Drift/` directory holds ~117 additional drift-mine prefabs.)

### Directory Structure

```
Prefabs/Mineshaft/
├── Shaft/
│   ├── Mineshaft_Shaft_Surface_001.prefab.json
│   └── ...
├── Slope/
│   ├── Mineshaft_Slope_Surface_001.prefab.json
│   └── ...
├── Surface/
│   ├── Mineshaft_Surface_001.prefab.json
│   └── ...
├── Fir/
└── Dry/
```

### Component Types

| Component | Description |
|-----------|-------------|
| `Shaft` | Tunnel sections |
| `Slope` | Ascending/descending sections |
| `Surface` | Above-ground entrances and buildings |
| `Fir` / `Dry` | Biome/material-themed mineshaft variants |

### Connection System

Mineshaft components use standardized connection points:
- Opening at each end of tunnels
- Matching dimensions for seamless connection
- Anchor points at center of floor

### Example: Surface Shaft

**File:** `Prefabs/Mineshaft/Shaft/Mineshaft_Shaft_Surface_001.prefab.json`

Contains:
- Tunnel walls and ceiling
- Support beam blocks
- Rail track blocks
- Torch/light source blocks
- Openings on three sides for connections

---

## Dungeons

**Location:** `Prefabs/Dungeon/`
**Count:** ~858 files

Dungeons use modular room systems similar to mineshafts, creating varied dungeon layouts. Top-level directories mix themed dungeons and material variants.

### Directory Structure

```
Prefabs/Dungeon/
├── Goblin_Lair/
│   ├── Goblin_Lair_Empty.prefab.json
│   ├── Goblin_Lair_Stairs_U_Turn_001.prefab.json
│   └── ...
├── Cursed_Crypt/
├── Labyrinth/
├── Sewer/
├── Rift/
├── Magic_Ruins/
├── Outlander_Temple/
├── Challenge_Gate/
├── Stone/
├── Slate/
├── Shale/
└── Sandstone/
```

### Dungeon Types

| Type | Theme | Enemies |
|------|-------|---------|
| `Goblin_Lair` | Cave, crude construction | Goblins |
| `Cursed_Crypt` | Stone, dark | Undead |
| `Labyrinth` | Maze-like | Varied |
| `Sewer` | Underground waterways | Varied |
| `Rift` | Magical | Magical creatures |
| `Magic_Ruins` | Ancient, magical | Varied |
| `Outlander_Temple` | Human ruins | Outlanders |
| `Stone` / `Slate` / `Shale` / `Sandstone` | Material-themed | Varied |

### Room Types

Dungeon room prefabs use descriptive names rather than a fixed component set, e.g. `Goblin_Lair_Stairs_U_Turn_001`, `Goblin_Lair_Entrance_Library_Layout_001`, `Goblin_Lair_Empty`.

### Example: Goblin Lair Room

**File:** `Prefabs/Dungeon/Goblin_Lair/Goblin_Lair_Stairs_U_Turn_001.prefab.json`

Contains:
- Goblin-themed decorations
- Loot containers
- Entity spawn points for minions
- Entrance and exit openings for connection

---

## Caves

**Location:** `Prefabs/Cave/`
**Count:** ~492 files

Cave prefabs include geological formations, creature nests, and resource nodes found underground.

### Directory Structure

```
Prefabs/Cave/
├── Formations/
│   ├── Rock_Volcanic_Ceiling_Formation_001.prefab.json
│   ├── Rock_Volcanic_Floor_Formation_001.prefab.json
│   └── ...
├── Klops/
│   ├── Klops_Oak_Entrance_001.prefab.json
│   └── ...
├── Nodes/
│   ├── Node_Shale_Deep_Fossil_001.prefab.json
│   └── ...
├── Organics/
├── Stalagmites/
├── Geysers/
└── Hive/
```

### Categories

| Category | Description |
|----------|-------------|
| `Formations/` | Stalactites, stalagmites, columns |
| `Klops/` | Klops nest structures and entrances |
| `Nodes/` | Ore, fossil, and crystal deposits |
| `Organics/` | Organic cave growths |
| `Stalagmites/` | Floor formations |
| `Geysers/` | Geothermal vents |
| `Hive/` | Insectoid hive structures |

### Resource Nodes

Node prefabs encode material, depth, and feature in their names, e.g. `Node_Shale_Deep_Fossil_001`, `Node_Shale_Shallow_Crypt_002`.

---

## Plants

**Location:** `Prefabs/Plants/`
**Count:** ~555 files

Plant prefabs include bushes, cacti, coral, and other vegetation beyond trees.

### Directory Structure

```
Prefabs/Plants/
├── Bush/
│   ├── Bush_Brambles_005.prefab.json
│   └── ...
├── Cacti/
│   ├── Cacti_Flat_Stage_0_002.prefab.json
│   └── ...
├── Mushroom_Rings/
├── Mushroom_Large/
├── Jungle/
├── Vines/
├── Seaweed/
├── Driftwood/
├── Coral/
└── Twisted_Wood/
```

### Categories

| Category | Biomes | Description |
|----------|--------|-------------|
| `Bush/` | Varied | Berry, bramble, decorative bushes |
| `Cacti/` | Desert | Desert plants (staged growth) |
| `Mushroom_Rings/` | Varied | Mushroom ring clusters |
| `Mushroom_Large/` | Varied | Large mushroom formations |
| `Jungle/` | Tropical | Jungle vegetation |
| `Vines/` | Varied | Hanging vines |
| `Seaweed/` | Underwater | Aquatic vegetation |
| `Driftwood/` | Coastal | Washed-up wood |
| `Coral/` | Underwater | Coral formations |
| `Twisted_Wood/` | Corrupted | Dark, twisted plants |

---

## Spawn

**Location:** `Prefabs/Spawn/`
**Count:** ~20 files

Spawn prefabs define player spawn layouts, pathways, rooms, and prefab spawners used at the start area.

### Directory Structure

```
Prefabs/Spawn/
├── Layouts/
├── Pathways/
├── Room/
├── Room_Goblin/
├── Spawners_Trees_Oak/
│   ├── Prefabspawner_OakT2.prefab.json
│   └── ...
├── Spawners_Trees_Birch/
└── Spawners_Rocks_Stone/
```

### Types

| Subdirectory | Description |
|------|-------------|
| `Layouts/` | Spawn-area layouts |
| `Pathways/` | Initial player pathways |
| `Room/` / `Room_Goblin/` | Spawn rooms |
| `Spawners_*` | Prefab spawners for trees and rocks |

### Example: Spawn Tree Spawner

**File:** `Prefabs/Spawn/Spawners_Trees_Oak/Prefabspawner_OakT2.prefab.json`

Contains:
- A prefab spawner definition placing Oak trees at tier 2 around the spawn area

---

## PrefabList Integration

World generation references prefabs through PrefabList files that group related prefabs by category and biome.

### Example: Birch Trees PrefabList

**File:** `Server/PrefabList/Trees_Birch.json`

```json
{
  "Prefabs": [
    {
      "RootDirectory": "Asset",
      "Path": "Trees/Birch/Stage_0/",
      "Recursive": true
    },
    {
      "RootDirectory": "Asset",
      "Path": "Trees/Birch/Stage_1/",
      "Recursive": true
    },
    {
      "RootDirectory": "Asset",
      "Path": "Trees/Birch/Stumps/",
      "Recursive": true
    }
  ]
}
```

(Other tree lists include `Trees_Fir.json`, `Trees_Oak.json`, `Trees_Redwood.json`, etc.)

### Example: Boulders PrefabList

**File:** `Server/PrefabList/ForestBrush_Boulders.json`

```json
{
  "Prefabs": [
    {
      "RootDirectory": "Asset",
      "Path": "Rock_Formations/Rocks/Stone/Small/",
      "Recursive": true
    }
  ]
}
```

---

## Related Documentation

- [Prefabs API](prefabs.md) - Java API and file format
- [Drop System](drops.md) - Loot tables for containers
- [Block System](blocks.md) - Block types and properties
- [NPC Roles](npc-roles.md) - NPC configuration
