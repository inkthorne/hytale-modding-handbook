---
title: "Prefab Categories"
description: "Hytale prefab categories in JSON — trees, rocks, NPC structures, monuments, mineshafts, dungeons, caves, plants, and spawn; naming conventions and growth-stage directory layout."
seo:
  type: TechArticle
---

# Prefab Categories

**Doc type:** JSON asset format · **Assets:** `Server/Prefabs` · **Verified against 0.6.3**

Hytale ships 7,828 `.prefab.json` files under `Server/Prefabs`, organized into major categories for world generation. This reference documents the taxonomy of prefab types, naming conventions, and directory structures.

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
Server/Prefabs/                      (7,828 .prefab.json files; 5 sit at the root)
├── Rock_Formations/  1676  (rocks by material, arches, pillars, fossils, mushrooms)
├── Mineshaft/        1159  (modular mine components)
├── Trees/            1126  (per-species → Stage_N subdirs, Stumps)
├── Npc/               856  (faction buildings, villages, outposts)
├── Monuments/         809  (towers, temples, encounters, camps)
├── Dungeon/           853  (modular dungeon rooms)
├── Plants/            555  (bushes, cacti, coral, driftwood)
├── Cave/              492  (formations, nests, nodes, stalagmites)
├── Testing/           156  (developer test assets)
├── Mineshaft_Drift/   117  (drift-mine variant of the mineshaft set)
├── Spawn/              20  (player spawn layouts)
└── Blocksets/, TestTree/, Unique/   (1-2 files each)
```

Note the singular directory names: `Mineshaft`, `Dungeon`, `Cave`, `Npc` — not the plural forms used in prose.

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| Trees | `Server/Prefabs/Trees/` | Growth stages, species, biome variants (1,126) |
| Rock Formations | `Server/Prefabs/Rock_Formations/` | Rocks, arches, fossils, pillars, mushrooms (1,676) |
| NPC Structures | `Server/Prefabs/Npc/` | Faction buildings, villages, outposts (856) |
| Monuments | `Server/Prefabs/Monuments/` | Towers, temples, encounters, camps (809) |
| Mineshafts | `Server/Prefabs/Mineshaft/` | Modular mine components (1,159) |
| Dungeons | `Server/Prefabs/Dungeon/` | Modular dungeon rooms (853) |
| Caves | `Server/Prefabs/Cave/` | Formations, nests, nodes (492) |
| Plants | `Server/Prefabs/Plants/` | Bushes, cacti, coral, driftwood (555) |
| Spawn | `Server/Prefabs/Spawn/` | Player spawn layouts (20) |

---

## Quick Navigation

Counts are exact file counts in the 0.6.3 `Assets.zip`.

| Category | Directory | Count | Description |
|----------|-----------|-------|-------------|
| [Rock Formations](#rock-formations) | `Rock_Formations/` | 1,676 | Rocks, arches, fossils, pillars, mushrooms |
| [Mineshafts](#mineshafts) | `Mineshaft/` | 1,159 | Modular mine components |
| [Trees](#trees) | `Trees/` | 1,126 | Growth stages, species, biome variants |
| [NPC Structures](#npc-structures) | `Npc/` | 856 | Faction buildings, villages, outposts |
| [Dungeons](#dungeons) | `Dungeon/` | 853 | Modular dungeon rooms |
| [Monuments](#monuments) | `Monuments/` | 809 | Towers, temples, encounters, camps |
| [Plants](#plants) | `Plants/` | 555 | Bushes, cacti, coral, driftwood |
| [Caves](#caves) | `Cave/` | 492 | Formations, nests, nodes |
| [Spawn](#spawn) | `Spawn/` | 20 | Player spawn layouts |

Additional top-level directories: `Testing/` (156), `Mineshaft_Drift/` (117), `Blocksets/`, `TestTree/` and `Unique/` (1–2 files each), plus 5 loose prefabs at the root of `Server/Prefabs/` — one of them `Goblin_Thief_Chest.prefab.json` (see [Prefabs API](prefabs.md#prefab-file-format)).

**Location:** `Assets.zip > Server/Prefabs/`

---

## Naming Conventions

Prefab files follow consistent naming patterns that encode category, type, variant, and size information.

### General Pattern

```
{Category}_{Type}_{Variant}_{Size}_{Number}.prefab.json
```

### Common Patterns

Every example below is a real 0.6.3 filename (the `.prefab.json` suffix is omitted).

| Pattern | Example | Description |
|---------|---------|-------------|
| `{Tree}_Stage{N}_{NNN}` | `Oak_Stage2_001` | Tree growth stage (0–7, plus `Stage_00`) |
| `{Category}_{Material}_{NNN}` | `Arches_Sandstone_001` | Material variant |
| `{Category}_{Material}_{Size}_{NNN}` | `Rocks_Stone_Small_001` | Material + size variant |
| `{Category}_{Variant}_{NNN}` | `Bush_Brambles_001` | Named variant |
| `{Faction}_{Theme}_{Building}_{NNN}` | `Kweebec_Oak_Well_001` | Faction structure |
| `Node_{Material}_{Depth}_{Feature}_{NNN}` | `Node_Shale_Deep_Fossil_001` | Cave resource node |
| `Encounter_{Zone}_{Tier}_{NNN}` | `Encounter_Zone4_Tier4_001` | Zoned encounter piece |

Numbering is a zero-padded three-digit counter (`_001`, `_002`, …) in almost every directory; a handful of older sets use two digits.

### Growth Stage Naming (Trees)

Each species directory contains one **subdirectory per growth stage** (`Stage_0`, `Stage_1`, ... up to `Stage_7` for some species, plus optional `Stage_00` and `Stumps`). Each subdirectory holds numbered prefab files, e.g. `Trees/Oak/Stage_2/Oak_Stage2_001.prefab.json` — note the directory uses `Stage_2` with an underscore while the filename uses `Stage2` without one. Not every species has every stage: `Oak` runs `Stage_00`, `Stage_0`–`Stage_7` plus `Stumps`; `Fir` stops at `Stage_3`; `Ash_Dead` ships only `Stage_2` and `Stage_3`. A few species add a themed stage directory (`Stage_1_Dead`, `Stage_2_Red`, `Stage_3_Vines`, `Stage_3_Crystal_Red`).

| Stage | Age | Description |
|-------|-----|-------------|
| `Stage_0` | Sapling | Newly planted, small |
| `Stage_1` | Young | Growing, moderate size |
| `Stage_2`-`Stage_3` | Mature | Full-grown, standard |
| `Stage_4`-`Stage_7` | Ancient | Large, may have special features |
| `Stumps` | Remnant | Cut/decayed stumps |

### Biome Variant Suffixes

Biome/theme tokens appear as an infix in the filename, not only at the end. These are the ones that actually occur across the shipped set (counts are matching files):

| Token | Biome | Example |
|-------|-------|---------|
| `_Volcanic_` (231) | Volcanic/lava regions | `Arches_Wastes_Lava_Large_Rocks_Volcanic_Arch_001` |
| `_Autumn_` (167) | Autumn foliage | `Fir_Autumn_Stage2_001` |
| `_Dead_` (127) | Dead/decayed variants | `Ash_Dead_Stage2_001` |
| `_Cave_` (87) | Underground variants | `Crypt_Cursed_C_Large_Cave_Corner_001` |
| `_Swamp_` (54) | Wetland/swamp regions | `Arches_Swamp_Large_001` |
| `_Winter_` (40) | Cold/snow regions | `Bush_Winter_001` |
| `_Jungle_` (30) | Tropical regions | `Bush_Jungle_Jungle_Bush_001` |
| `_Moss_` (27) | Moss-covered | `Ash_Moss_Stage3_001` |
| `_Desert_` (23) | Arid/desert regions | `Arches_Desert_Drylands_Pillars_006` |
| `_Frozen_` (14) | Frozen variants | `Encounter_Shale_Monuments_EncounterOBJ_Shale_Frozen_001` |

(`_Eternal` and `_Underwater` were documented for earlier builds but appear on no 0.6.3 prefab filename; aquatic content is instead grouped by directory — `Plants/Seaweed/`, `Plants/Coral/`, `Rock_Formations/Rocks/Ocean/`.)

---

## Trees

**Location:** `Server/Prefabs/Trees/`
**Count:** 1,126 files across 79 species directories

Trees are organized by species. Each species directory contains growth-stage subdirectories (`Stage_0`, `Stage_1`, ...), each holding numbered prefab files.

### Directory Structure

```
Server/Prefabs/Trees/                 (79 species directories, 1,126 files)
├── Oak/
│   ├── Stage_00/
│   ├── Stage_0/
│   │   ├── Oak_Stage0_001.prefab.json
│   │   └── ...
│   ├── Stage_1/ … Stage_7/
│   │   ├── Oak_Stage2_001.prefab.json
│   │   ├── Oak_Stage2_002.prefab.json
│   │   └── ...
│   └── Stumps/
│       └── Oak_Stumps_001.prefab.json
├── Birch/  Fir/  Palm/  Banyan/  Willow/  Maple/  Redwood/  Jungle/  Boab/
├── Ash_Dead/  Fir_Snow/  Oak_Moss/  Redwood_Logs/   (variant species dirs)
└── ...
```

### Tree Species

There are 79 species directories under `Server/Prefabs/Trees/`. A representative selection:

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

Variants are separate *species directories*, not filename suffixes on a base species — `Trees/Ash_Dead/` sits alongside `Trees/Ash/`, and its files are named `Ash_Dead_Stage2_001.prefab.json`.

| Variant directory | Description | Examples |
|-------------------|-------------|----------|
| `*_Dead` | Leafless, decayed | `Ash_Dead`, `Fir_Dead`, `Fir_Dead_Large`, `Dry_Dead`, `Petrified_Dead` |
| `*_Moss` | Covered in moss | `Ash_Moss`, `Oak_Moss` |
| `*_Autumn` | Fall foliage | `Fir_Autumn` (plus the standalone `Autumn` / `Autumn_Stumps` species) |
| `*_Snow` | Snow-covered branches | `Fir_Snow` |
| `*_Stumps` | Cut/decayed stumps | `Oak_Stumps`, `Maple_Stumps`, `Redwood_Stumps`, `Stormbark_Stumps` |
| `*_Logs` | Felled logs | `Cedar_Logs`, `Fir_Logs`, `Redwood_Logs`, `Petrified_Logs` |
| `*_Burnt` | Burned | `Cedar_Burnt`, `Burnt`, `Burnt_Roots`, `Burnt_dead` |

### Example: Oak Tree at Stage 2

**File:** `Server/Prefabs/Trees/Oak/Stage_2/Oak_Stage2_001.prefab.json`

This prefab contains:
- Trunk blocks with appropriate rotations
- Branch blocks extending outward
- Leaf blocks forming the canopy
- Anchor at base of trunk for proper ground placement

---

## Rock Formations

**Location:** `Server/Prefabs/Rock_Formations/`
**Count:** 1,676 files

Rock formations provide natural terrain features including standalone rocks, arches, fossils, pillars, and geological features. Material variants live in subdirectories under `Rocks/`; `Arches/` is instead keyed by biome/theme.

### Directory Structure

```
Server/Prefabs/Rock_Formations/
├── Rocks/              (by material, each often → Small/ Medium/ Large/ Cliff/ Oceans/)
│   ├── Stone/  Sandstone/  Sandstone_Red/  Sandstone_White/
│   ├── Basalt/  Basalt_Mushroom/  Volcanic/  Shale/  Slate/  Slate_Forest_Ghost/
│   ├── Calcite/  Chalk/  Marble/  Quartzite/  Frozenstone/
│   ├── Gems/  Geodes/  Stone_Mana/  Spikes/  Twisted/
│   └── Empty/  Floating/  Grass/  Jungle/  Ocean/
├── Arches/             (by biome: Sandstone, Desert, Swamp, Tundra, Wastes_Lava, …)
├── Pillars/
├── Fossils/
├── Geode_Floating/
├── Mushrooms/
├── Hotsprings/
├── Stalactites/
├── Ice_Formations/
├── Crystals/  Crystal_Floating/  Crystal_Pattern/  Crystal_Pits/
└── Dolmen/
```

### Subcategories

| Subcategory | Count | Description |
|-------------|-------|-------------|
| `Rocks/` | 944 | Standard rock formations (by material) |
| `Arches/` | 275 | Natural stone arches (24 biome/theme subdirectories) |
| `Pillars/` | 215 | Tall stone columns |
| `Fossils/` | 72 | Exposed fossil formations |
| `Geode_Floating/` | 61 | Floating geode clusters |
| `Mushrooms/` | 33 | Giant mushroom formations |
| `Hotsprings/` | 30 | Geothermal features |
| `Stalactites/` | 23 | Hanging rock formations |
| `Ice_Formations/` | 17 | Frozen formations |
| `Crystals/`, `Crystal_Floating/`, `Crystal_Pattern/`, `Crystal_Pits/`, `Dolmen/` | 1–2 each | One-off formations |

### Material Variants (`Rocks/` subdirectories)

All 25 material directories, with their own sub-splits:

| Material | Sub-splits | Appearance |
|----------|-----------|------------|
| `Stone` | `Small`, `Large`, `Cliff`, `Oceans` | Gray, standard rock |
| `Sandstone` | `Small`, `Large`, `Large_Tall`, `Cliff`, `Pillars`, `Oasis`, `Savannah`, `Savannah_Stamina` | Tan, layered |
| `Sandstone_Red` / `Sandstone_White` | `Small`, `Large` | Desert colour variants |
| `Quartzite` | `Small`, `Large`, `Moss_*` (incl. `_Health` buff variants) | White, crystalline |
| `Volcanic` | `Large`, `Ore`, `Spiked`, `Floating`, `Lava_Lakes_*`, `Firesteel_Golem_Rocks` | Dark, igneous |
| `Basalt` | `Small`, `Large`, `Hexagon`, `Hotspring`, `Shore`, `Snowy`, `Tundra` | Dark, columnar |
| `Basalt_Mushroom` | `Brown`, `Red`, `Yellow` | Mushroom-capped basalt |
| `Calcite` | `Small`, `Large`, `Cliff`, `Floating`, `Hexagon`, `Hexagon_Grass`, `Mossy_Tall`, `Pillars` | Light, crystalline |
| `Chalk` | `Small`, `Medium`, `Large` | White, soft |
| `Marble` | `Large` | Polished stone |
| `Shale` | `Small`, `Large`, `Ore`, `Ore_Health`, `Snowy`, `Spikey` | Layered dark stone |
| `Slate` / `Slate_Forest_Ghost` | `Small`…`Pillar_Large`, `Hexagon*`, `Azure`, `Spikes` / `Boulder_*`, `Pillars` | Flat-cleaving stone |
| `Gems` / `Geodes` | `Geodes` / nine colours (`Blue`, `Cyan`, `Green`, `Pink`, `Purple`, `Red`, `White`, `Yellow`, `Pink_S`/`Purple_S`) | Gem-bearing rock |
| `Frozenstone` | `Small`, `Snowy` | Icy stone |
| `Twisted` | `Green`, `Mushroom` | Corrupted stone |
| `Spikes` | `Volcanic_Poisoned` | Spiked hazard rock |
| `Empty`, `Floating`, `Grass`, `Jungle`, `Ocean`, `Stone_Mana` | — | Special-purpose sets |

### Size Variants

Size is a directory level under most materials, and repeats in the filename:

| Size | Files | Example |
|------|-------|---------|
| `Small` | 986 | `Rocks_Stone_Small_001` |
| `Large` | 730 | `Arches_Aspen_Large_001` |
| `Medium` | 184 | `Encounter_City_Oceans_Buildings_Medium_Blue_001` |
| `Tiny` | 8 | rare |

(No `Massive` tier ships in 0.6.3 — earlier builds of this page listed one.)

### Example: Sandstone Arch

**File:** `Server/Prefabs/Rock_Formations/Arches/Sandstone/Arches_Sandstone_001.prefab.json`

Sandstone blocks arranged in an arch formation, with the anchor at the base for terrain integration. `Arches/` splits by biome/theme first (24 directories: `Sandstone`, `Desert`, `Desert_Red`, `Swamp`, `Swamp_Poisoned`, `Tundra`, `Snowy`, `Wastes_Lava`, `Wastes_Ash`, …), and several of those split again by size (`Aspen/Large/Arches_Aspen_Large_001.prefab.json`).

---

## NPC Structures

**Location:** `Server/Prefabs/Npc/`
**Count:** 856 files across 9 faction directories

NPC structures represent buildings and camps for various factions. Each faction directory is organized differently — Kweebec by biome/material theme, Trork and Feran by tier, Outlander by structure type.

### Directory Structure

```
Server/Prefabs/Npc/
├── Kweebec/    337   Autumn/ Azure/ Oak/ Redwood/ Swamp/
│   └── Oak/          Bridge/ Bunny_Area/ Camps/ Garden/ Garden_Small/ Grandfather/
│                     Guard_Towers/ Houses_Guard/ Houses_Large/ Houses_Small/
│                     Lampposts/ Seats/ Shops/ Water_Pool/ Well/
│                     └── Well/Kweebec_Oak_Well_001.prefab.json
├── Scarak/     326   Scarak_Hives/
├── Outlander/   74   Boats/ Braziers/ Camps/ Forts/ Gates/ Houses/ Ice_Caves/
│                     Misc/ Spikes/ Totems/ Towers/
├── Trork/       51   Tier_1/ Tier_2/ Tier_3/ Bonfire/ Burrow/ Fireplace/ Misc/
│                     Resource/ Tent/ Trap/ Warehouse/ Warning/
├── Feran/       42   Tier1/ Tier2/ Tier3/ Portals_Oasis/
├── Slothian/    18   Camps/ Houses/ Disabled/
├── Yeti/         4   Camps/
├── Hedera/       3   Shrine/ Throne/
└── Dragons/      1   Frost/
```

### Factions

| Faction | Count | Style | Organized by |
|---------|-------|-------|--------------|
| `Kweebec` | 337 | Organic, wood | Biome theme (`Autumn`, `Azure`, `Oak`, `Redwood`, `Swamp`) |
| `Scarak` | 326 | Hive, organic | A single `Scarak_Hives/` tree |
| `Outlander` | 74 | Human, varied | Structure type (`Houses`, `Forts`, `Towers`, `Camps`, …) |
| `Trork` | 51 | Crude, bone | Tier (`Tier_1`–`Tier_3`) plus prop directories |
| `Feran` | 42 | Refined, stone | Tier (`Tier1`–`Tier3`) plus `Portals_Oasis` |
| `Slothian` | 18 | Organic | `Camps`, `Houses` |
| `Yeti` | 4 | Ice, stone | `Camps` |
| `Hedera` | 3 | Plant, vine | `Shrine`, `Throne` |
| `Dragons` | 1 | Lair structure | `Frost` |

### Building-Type Directories

Building types are directory names one level below the faction theme, and are plural. Recurring ones across factions:

| Directory | Description |
|-----------|-------------|
| `Houses_Small` / `Houses_Large` / `Houses_Guard` / `Houses` | Residential dwellings by size and role |
| `Shops` / `Store` | Merchant buildings |
| `Guard_Towers` / `Towers` / `Watchtower` | Defensive structures |
| `Camps` / `Encampment` | Outdoor camps |
| `Well` / `Water_Pool` | Water features |
| `Garden` / `Garden_Small` | Cultivated plots |
| `Chieftain` / `Grandfather` / `Throne` | Leader structures |
| `Bridge` / `Lampposts` / `Seats` / `Braziers` / `Totems` | Props and connectors |

(There are no `Workshop` or `Inn` directories in 0.6.3; `Temple` appears exactly once, under `Slothian/Disabled/`.)

### Example: Kweebec Well

**File:** `Server/Prefabs/Npc/Kweebec/Oak/Well/Kweebec_Oak_Well_001.prefab.json`

Contains:
- Wood and leaf block walls
- Interior furniture blocks
- Container blocks with faction-appropriate loot
- Door blocks with proper rotations
- `SpawnMarkerComponent` entity entries the spawn system turns into NPC inhabitants (see [Prefabs API → Entity Entries](prefabs.md#entity-entries))

---

## Monuments

**Location:** `Server/Prefabs/Monuments/`
**Count:** 809 files

Monuments are unique or semi-unique structures including towers, temples, encounter areas, and points of interest. Top-level categories are `Challenge`, `Encounter`, `Incidental`, `Story`, and `Unique`. Special structures such as Mage Towers and Temples live under `Unique/`.

### Directory Structure

```
Server/Prefabs/Monuments/
├── Encounter/    305   City_Oceans/ City_Ruins/ Shale/ Zone1/ Zone2/ Zone3/ Zone4/
├── Incidental/   252   Ash/ Basalt/ Grasslands/ Ocean/ Quartzite/ Sandstone/ Shale/
│                       Shipwrecks/ Slate/ Slothian/ Softwood/ Treasure_Rooms/ Volcanic/
├── Unique/       243   Elemental_Circles/ Mage_Towers/ Start_Camp/ Start_Den/ Start_Mine/
│   │                   Story_Dungeon/ Story_Gate/ Temple/ World_Gate/ World_Portal/
│   └── Mage_Towers/
│       ├── Quartzite/Tier_2/Monuments_MageTower_Quartzite_Tier2_001.prefab.json
│       ├── Quartzite/Tier_3/
│       ├── Shale/  Volcanic/  Sandstone/
├── Challenge/      6   Grass/ Grass_Cold/ Grass_Dry/ Sand/ Snow/ Volcanic/ (each → Combat/)
└── Story/          3   Start/ Story_gate/ Forgotten_temple/
```

### Categories

| Category | Count | Description |
|----------|-------|-------------|
| `Encounter/` | 305 | Zoned encounter progressions (`Zone1`–`Zone4`) plus two city sets |
| `Incidental/` | 252 | Camps, shipwrecks, treasure rooms (by biome/material) |
| `Unique/` | 243 | One-of-a-kind structures (Mage Towers, Temple, Start Camp, World Portal) |
| `Challenge/` | 6 | Combat encounter arenas — one per biome, each a single `Combat/` prefab |
| `Story/` | 3 | Story-related structures (`Story_Start_001`, `Story_Gate_001`, Forgotten Temple entrance) |

### Encounter Types

`Encounter/` splits by zone, and *tier* is a filename token rather than a directory in most sets:

| Subdirectory | Count | Naming |
|--------------|-------|--------|
| `Zone4/` | 77 | `Encounter_Zone4_Tier4_001`, `Encounter_Tier4_Grainsilo_001` |
| `City_Oceans/` | 62 | `Encounter_City_Oceans_Buildings_Capital_001` |
| `Zone3/` | 50 | `Encounter_Tier1_7x7_001` (under `Tier1/Orbis_Camp/7x7/`) |
| `Zone2/` | 44 | `Encounter_Zone2_Tier1_001` |
| `City_Ruins/` | 34 | `Encounter_City_Ruins_001`, `Encounter_Base_Basalt_Large_001` |
| `Zone1/` | 29 | `Encounter_Zone1_Tier1_001` |
| `Shale/` | 9 | `Encounter_Shale_Monuments_EncounterOBJ_Shale_Frozen_001` |

(There is no `Boss` encounter directory in 0.6.3.)

### Incidental Structures

`Incidental/` is organized by biome/material theme, plus a few special subdirectories:

| Subdirectory | Description |
|------|-------------|
| `Shipwrecks` | Wrecked ships |
| `Treasure_Rooms` | Hidden loot rooms |
| `Ash`, `Basalt`, `Grasslands`, `Ocean`, `Quartzite`, `Sandstone`, `Shale`, `Slate`, `Slothian`, `Softwood`, `Volcanic` | Biome/material-themed incidental structures |

### Example: Mage Tower

Mage Towers live under `Unique/`, organized by material and tier:

**File:** `Server/Prefabs/Monuments/Unique/Mage_Towers/Quartzite/Tier_2/Monuments_MageTower_Quartzite_Tier2_001.prefab.json`

Contains:
- Multi-story tower structure
- Material-themed block work (e.g. Quartzite, Shale, Volcanic, Sandstone)
- Interior rooms with furniture
- Loot containers with rare drops
- Potential boss spawn areas

---

## Mineshafts

**Location:** `Server/Prefabs/Mineshaft/`
**Count:** 1,159 files

Mineshafts use a modular system where different components connect to form complete mine networks. A separate `Server/Prefabs/Mineshaft_Drift/` directory holds 117 additional drift-mine prefabs, split into `Stage1_Generic` / `Stage2_Generic` / `Stage3_Generic`.

### Directory Structure

```
Server/Prefabs/Mineshaft/
├── Dry/      480   Elevator/ Mines/ Mines_Lvl1/ Mines_Lvl2/ Mines_Lvl3/ Surface/
├── Fir/      375   Elevator/ Mines/ Mines_Lvl1/ Mines_Lvl2/ Mines_Lvl3/
│                   Surface_1/ Surface_2/ Surface_3/
├── Shaft/    160   Elevator/ Mines/ Surface/
│   ├── Surface/Mineshaft_Shaft_Surface_001.prefab.json
│   └── Mines/Stage_01/Mineshaft_Shaft_Stage_01_Branch_Left_001.prefab.json
├── Slope/    143   Elevator/ Mines/ Surface/
│   └── Surface/Mineshaft_Slope_Surface_001.prefab.json
└── Surface/    1   Mineshaft_Surface_001.prefab.json
```

### Component Types

| Component | Count | Description |
|-----------|-------|-------------|
| `Dry` / `Fir` | 480 / 375 | Biome/material-themed complete mine sets, split by depth level |
| `Shaft` | 160 | Vertical tunnel sections (`Elevator`, `Mines/Stage_01`–`Stage_03`, `Surface`) |
| `Slope` | 143 | Ascending/descending sections (same three sub-splits) |
| `Surface` | 1 | Standalone above-ground entrance |

Within `Mines/`, pieces are named for their connection role — `Branch_Left`, `Branch_Right`, `Junction_End`, `Junction_Flip`, `Junction_Straight`, `Middle_Both`, `Middle_Left`, `Entrance`.

### Connection System

Mineshaft components use standardized connection points:
- Opening at each end of tunnels
- Matching dimensions for seamless connection
- Anchor points at center of floor

### Example: Surface Shaft

**File:** `Server/Prefabs/Mineshaft/Shaft/Surface/Mineshaft_Shaft_Surface_001.prefab.json`

Contains:
- Tunnel walls and ceiling
- Support beam blocks
- Rail track blocks
- Torch/light source blocks
- Openings on three sides for connections

---

## Dungeons

**Location:** `Server/Prefabs/Dungeon/`
**Count:** 853 files

Dungeons use modular room systems similar to mineshafts, creating varied dungeon layouts. Top-level directories mix themed dungeons and material variants.

### Directory Structure

```
Server/Prefabs/Dungeon/
├── Sewer/             148
├── Shale/             135
├── Magic_Ruins/       100
├── Goblin_Lair/        97   Entrance_Goblin/ Entrance_Mine/ Prefabs_Goblin/ Prefabs_Mine/
│                            + Goblin_Lair_Empty.prefab.json at the top level
├── Stone/              87   Entrance/ Entrance_Cave/ …
├── Labyrinth/          71
├── Outlander_Temple/   71
├── Sandstone/          61
├── Cursed_Crypt/       58
├── Rift/               10
├── Slate/              10
└── Challenge_Gate/      4
```

### Dungeon Types

| Type | Count | Theme |
|------|-------|-------|
| `Sewer` | 148 | Underground waterways |
| `Shale` | 135 | Material-themed |
| `Magic_Ruins` | 100 | Ancient, magical |
| `Goblin_Lair` | 97 | Cave, crude construction |
| `Stone` | 87 | Material-themed |
| `Labyrinth` | 71 | Maze-like |
| `Outlander_Temple` | 71 | Human ruins |
| `Sandstone` | 61 | Material-themed |
| `Cursed_Crypt` | 58 | Stone, dark |
| `Rift` | 10 | Magical |
| `Slate` | 10 | Material-themed |
| `Challenge_Gate` | 4 | Gated challenge entrances |

### Room Types

Dungeon room prefabs use descriptive names rather than a fixed component set. The path usually encodes the role: `Goblin_Lair/Entrance_Goblin/Library/Layout/Goblin_Lair_Entrance_Library_Layout_001.prefab.json`, `Goblin_Lair/Entrance_Goblin/Library/Stairs/Long/Goblin_Lair_Entrance_Library_Stairs_Long_001.prefab.json`, `Stone/Entrance_Cave/Stone_Entrance_Cave_001.prefab.json`. Only `Goblin_Lair_Empty.prefab.json` sits directly in a dungeon directory.

### Example: Goblin Lair Room

**File:** `Server/Prefabs/Dungeon/Goblin_Lair/Entrance_Goblin/Library/Layout/Goblin_Lair_Entrance_Library_Layout_001.prefab.json`

Contains:
- Goblin-themed decorations
- Loot containers
- Entity spawn points for minions
- Entrance and exit openings for connection

---

## Caves

**Location:** `Server/Prefabs/Cave/`
**Count:** 492 files

Cave prefabs include geological formations, creature nests, and resource nodes found underground. Every category except `Geysers/` nests one or two levels deeper before reaching files.

### Directory Structure

```
Server/Prefabs/Cave/
├── Stalagmites/  241   17 material dirs (Rock_Stone/, Rock_Basalt_Crystal/, Mushroom/, Spider/, …)
│   └── Rock_Stone/Ceiling/Stalagmites_Stone_Ceiling_001.prefab.json
├── Nodes/        119   Rock_Basalt/ Rock_Sandstone/ Rock_Shale/ Rock_Stone/ Rock_Volcanic/ Tree_Spiral/
│   └── Rock_Shale/Deep_Fossil/Node_Shale_Deep_Fossil_001.prefab.json
├── Klops/        115   Basalt/ Dry/ Oak/   (each → Bathroom/ Bedroom/ …)
├── Organics/       8   Lianas/ Roots/ Vines_Dry/ Vines_Empty/
├── Formations/     6   Rock_Sandstone/ Rock_Stone/ Rock_Volcanic/ (each → Ceiling/ Floor/)
│   └── Rock_Volcanic/Ceiling/Rock_Volcanic_Ceiling_Formation_001.prefab.json
├── Geysers/        2   Geyser_Firelands_001.prefab.json, _002
└── Hive/           1   Poisoned/
```

### Categories

| Category | Count | Description |
|----------|-------|-------------|
| `Stalagmites/` | 241 | Floor and ceiling spikes, by material (`Ceiling/` and `Floor/` splits) |
| `Nodes/` | 119 | Ore, fossil, and crystal deposits |
| `Klops/` | 115 | Klops nest structures and rooms |
| `Organics/` | 8 | Lianas, roots, vines |
| `Formations/` | 6 | Large ceiling/floor rock formations |
| `Geysers/` | 2 | Geothermal vents |
| `Hive/` | 1 | Insectoid hive structure |

### Resource Nodes

Node prefabs encode material, depth, and feature in the *path and* the filename: `Nodes/Rock_Shale/Deep_Fossil/Node_Shale_Deep_Fossil_001.prefab.json`. Depth-prefixed features are `Deep_*` (`Deep_Fossil`, `Deep_Ice`, `Deep_Narrow`, `Deep_Scarak`) and `Shallow_*` (`Shallow_Crypt`, `Shallow_Ice`, `Shallow_Mine`, `Shallow_Scarak`); the rest name a theme or inhabitant directly (`Burnt`, `Lakes`, `Lava`, `Crystal`, `Goblin`, `Spider`, `Skeleton`, `Wraith`, `Jungle_Green`, `Volcanic_Vents`, `Mines_Straight`, `Surface_Entry`, …). Note the directory keeps the `Rock_` prefix (`Rock_Shale`) while the filename drops it (`Node_Shale_…`).

`Klops/` rooms follow the same shape one level in — `Klops/Oak/{Bathroom, Bedroom, Cave, Cellar, Entrance, Main, Main_2, Main_3, Stairs, Start}/Klops_Oak_<Room>_001.prefab.json` (the numbered rooms drop the underscore in the filename: directory `Main_2` → `Klops_Oak_Main2_001.prefab.json`).

---

## Plants

**Location:** `Server/Prefabs/Plants/`
**Count:** 555 files

Plant prefabs include bushes, cacti, coral, and other vegetation beyond trees.

### Directory Structure

```
Server/Prefabs/Plants/
├── Coral/         133   Bracket/Large/{Blue,Cyan,Green,…}/Coral_Large_Blue_001.prefab.json
├── Seaweed/       119
├── Jungle/         85
├── Bush/           73   Arid/ Arid_Red/ Brambles/ Cliff/ Dead_Hanging/ Dead_Lavathorn/
│   │                    Green/ Hanging/ Hanging_Overhang/ Hanging_Short/ Jungle/ Lush/ Winter/
│   └── Brambles/Bush_Brambles_001.prefab.json
├── Cacti/          52   Flat/ Full/ → Stage_0/ Stage_1/ …
│   └── Flat/Stage_0/Cacti_Flat_Stage_0_001.prefab.json
├── Driftwood/      30
├── Mushroom_Large/ 24
├── Vines/          19
├── Twisted_Wood/   18
└── Mushroom_Rings/  2
```

### Categories

| Category | Count | Biomes | Description |
|----------|-------|--------|-------------|
| `Coral/` | 133 | Underwater | Coral formations (by shape → size → colour) |
| `Seaweed/` | 119 | Underwater | Aquatic vegetation |
| `Jungle/` | 85 | Tropical | Jungle vegetation |
| `Bush/` | 73 | Varied | Berry, bramble, hanging and decorative bushes |
| `Cacti/` | 52 | Desert | Desert plants (staged growth, like trees) |
| `Driftwood/` | 30 | Coastal | Washed-up wood |
| `Mushroom_Large/` | 24 | Varied | Large mushroom formations |
| `Vines/` | 19 | Varied | Hanging vines |
| `Twisted_Wood/` | 18 | Corrupted | Dark, twisted plants |
| `Mushroom_Rings/` | 2 | Varied | Mushroom ring clusters |

---

## Spawn

**Location:** `Server/Prefabs/Spawn/`
**Count:** 20 files

Spawn prefabs define player spawn layouts, pathways, rooms, and prefab spawners used at the start area. Small enough to list in full:

### Directory Structure

```
Server/Prefabs/Spawn/
├── Pathways/              5   Spawn_Zone1_Pathway_001 … _005
├── Layouts/               4   Layout_1_Balanced, Layout_2_Balanced,
│                              Layout_3_RocksOpen, Layout_4_Forest
├── Spawners_Trees_Oak/    3   Prefabspawner_OakT2, _OakT3, _OakT4
├── Spawners_Trees_Birch/  3
├── Room_Goblin/           2   Spawn_Room_Goblin_001, _002
├── Spawners_Rocks_Stone/  2
└── Room/                  1   Spawn_Room_001
```

### Types

| Subdirectory | Count | Description |
|------|-------|-------------|
| `Layouts/` | 4 | Spawn-area layouts (balanced / rocks-open / forest presets) |
| `Pathways/` | 5 | Initial player pathways |
| `Room/` / `Room_Goblin/` | 1 / 2 | Spawn rooms |
| `Spawners_*` | 3 / 3 / 2 | Prefab spawners for trees and rocks |

### Example: Spawn Tree Spawner

**File:** `Server/Prefabs/Spawn/Spawners_Trees_Oak/Prefabspawner_OakT2.prefab.json`

A single `Prefab_Spawner_Block` carrying the `PrefabSpawner` block component (documented on [Prefabs API → PrefabSpawnerBlock](prefabs.md#prefabspawnerblock)), which stamps a random Stage-2 Oak when the containing prefab is placed. The whole file:

```json
{
  "version": 8,
  "blockIdVersion": 11,
  "anchorX": 0, "anchorY": 0, "anchorZ": 0,
  "blocks": [
    {
      "x": 0, "y": 0, "z": 0,
      "name": "Prefab_Spawner_Block",
      "components": {
        "Components": {
          "PrefabSpawner": {
            "PrefabPath": "Trees.Oak.Stage_2.*",
            "FitHeightmap": false,
            "InheritSeed": false,
            "InheritHeightCondition": false
          },
          "PlacedByInteraction": {
            "WhoPlacedUuid": { "$binary": "loF51VQUMKu6CVE32X+4IQ==", "$type": "04" }
          }
        }
      }
    }
  ]
}
```

`PrefabPath` uses the dotted `PrefabLoader` syntax with a `.*` folder wildcard, so this spawner picks from every prefab under `Trees/Oak/Stage_2/`.

---

## PrefabList Integration

World generation references prefabs through PrefabList files that group related prefabs by category and biome.

### Example: Birch Trees PrefabList

**File:** `Server/PrefabList/Trees_Birch.json`

```json
{
  "Prefabs": [
    { "RootDirectory": "Asset", "Path": "Trees/Birch/Stage_0/", "Recursive": true },
    { "RootDirectory": "Asset", "Path": "Trees/Birch/Stage_1/", "Recursive": true },
    { "RootDirectory": "Asset", "Path": "Trees/Birch/Stage_2/", "Recursive": true },
    { "RootDirectory": "Asset", "Path": "Trees/Birch/Stage_3/", "Recursive": true },
    { "RootDirectory": "Asset", "Path": "Trees/Birch/Stage_4/", "Recursive": true },
    { "RootDirectory": "Asset", "Path": "Trees/Birch/Stumps/",  "Recursive": true }
  ]
}
```

(Other tree lists include `Trees_Fir.json`, `Trees_Oak.json`, `Trees_Redwood.json`, etc. `RootDirectory` accepts `Asset`, `Server` or `Worldgen` — see [Prefabs API → PrefabList Files](prefabs.md#prefablist-files).)

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

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the prefab-list system (verified against `HytaleServer.jar`).

- **`No prefab found in prefab list. Please double check your PrefabList asset.`** → a `PrefabList` resolved but yielded no prefab — usually a `Path` that matches no files, or `Recursive: false` over an empty directory. Fix: verify the `Path` points at real prefab files and matches the on-disk casing (see [PrefabList Integration](#prefablist-integration)).
- **`PrefabList asset not found: `** → a referenced `PrefabList` id does not exist. Fix: confirm the `Server/PrefabList/*.json` file exists and the referenced id matches exactly.
- **`Prefabs are defined but could not find a valid entry!`** → prefab entries are declared but none resolved to a usable prefab. Fix: check that each entry's `RootDirectory`/`Path` resolves and the directories actually contain `.prefab.json` files.

---

## Related Documentation

- [Prefabs API](prefabs.md) - Java API and file format
- [Drop System](drops.md) - Loot tables for containers
- [Block System](blocks.md) - Block types and properties
- [NPC Roles](npc-roles.md) - NPC configuration
