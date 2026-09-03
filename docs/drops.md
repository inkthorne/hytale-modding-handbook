---
title: "Drop System"
description: "Define Hytale loot with the JSON Drop System — a hierarchical Container tree (Multiple, Choice, Single, Droplist), guaranteed and weighted drops, multi-roll loot, and modular composition."
seo:
  type: TechArticle
---

# Drop System

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Drops` · **Verified against 0.5.9**

Drop files define loot tables for blocks, NPCs, containers, and world prefabs. They use a hierarchical container system that supports guaranteed drops, weighted random selection, and modular composition through references.

> **Root structure:** Every drop file wraps its root container in a top-level `Container` object: `{ "Container": { "Type": ... } }`. The only exception is an empty drop file, which is literally `{}`.

> **See also:** [Item Definitions](items.md) for item IDs and properties, [NPC Roles](npc-roles.md) for NPC drop configuration, [Block Items](items-blocks.md) for container block drops

---

## Overview

Defined as JSON assets under `Server/Drops/` in `Assets.zip` and provides:
- A hierarchical container system rooted in a top-level `Container` object
- Container types: `Multiple`, `Choice`, `Single`, `Empty`, `Droplist`
- Guaranteed drops, weighted random selection, and multi-roll loot
- Modular composition via `Droplist` references to other drop files
- Item entries with `ItemId` and `QuantityMin`/`QuantityMax` ranges
- Drop tables for crops, NPCs, mining, plants, containers, prefabs, traps, and more

## Architecture
```
Drop File  { "Container": ... }
└── Container (Type)
    ├── Multiple  → all child containers evaluated (Weight = % chance)
    ├── Choice    → one child by weight (RollsMin/RollsMax for multi-roll)
    ├── Single    → leaf: one Item (ItemId, QuantityMin/Max)
    ├── Empty     → no drop (chance-for-nothing inside Choice)
    └── Droplist  → references another drop file by DroplistId
```

## Key Classes
These are JSON asset constructs (container/field schemas), not Java classes. For the server-side classes
they load into — and how to roll a droplist from a plugin — see [Java API](#java-api).

| Construct | Location | Description |
|-----------|----------|-------------|
| Drop file root | `Server/Drops/` | Wraps the root `Container` (or `{}` for no drop) |
| `Multiple` container | drop JSON | Evaluates all nested containers |
| `Choice` container | drop JSON | Selects one nested container by weight |
| `Single` container | drop JSON | Leaf node defining one item drop |
| `Empty` container | drop JSON | Produces no drop (used inside Choice/Multiple) |
| `Droplist` container | drop JSON | References another drop file by `DroplistId` |
| Item object | drop JSON | `ItemId` + `QuantityMin`/`QuantityMax` |

## Quick Navigation

| Category | Directory | Files | Description |
|----------|-----------|-------|-------------|
| [Crops](#crop-drops) | `Crop/` | 231 | Growth stage and harvest drops |
| [NPCs](#npc-drops) | `NPCs/` | 270 | Creature loot tables |
| [Mining](#mining-drops) | `Rock/` | 67 | Ore and crystal drops |
| [Plants](#plant-drops) | `Plant/` | 23 | Wild plant harvesting |
| [Ingredients](#ingredient-drops) | `Ingredients/` | 9 | Sap, grass, and gatherables |
| [Wood](#wood-drops) | `Wood/` | 8 | Tree, leaf, and branch drops |
| [Containers](#container-drops) | `Items/` | 13 | Destructible container drops |
| [Prefabs](#prefab-drops) | `Prefabs/` | 49 | Encounter loot by zone/tier |
| [Objectives](#objective-drops) | `Objectives/` | 4 | Quest rewards |
| [Traps](#trap-drops) | `Traps/` | 2 | Fishing trap catches |

**Location:** `Assets.zip > Server/Drops/` (678 total files, including two loose root-level
files `Soil_Gravel.json` and `Soil_Gravel_Pickaxe.json`)

---

## Quick Start

### Simple Guaranteed Drop

A single item that always drops:

```json
{
  "Container": {
    "Type": "Single",
    "Item": {
      "ItemId": "Plant_Crop_Carrot_Item",
      "QuantityMin": 1,
      "QuantityMax": 1
    }
  }
}
```

### Random Quantity Drop

A single item with variable quantity:

```json
{
  "Container": {
    "Type": "Single",
    "Item": {
      "ItemId": "Ingredient_Bolt_Wool",
      "QuantityMin": 1,
      "QuantityMax": 3
    }
  }
}
```

### Weighted Random Selection

One item chosen randomly from a pool:

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 70,
        "Item": { "ItemId": "Fish_Bluegill_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 25,
        "Item": { "ItemId": "Fish_Salmon_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 5,
        "Item": { "ItemId": "Fish_Pike_Item", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

### Multiple Guaranteed Drops

All items drop together:

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Item": { "ItemId": "Ingredient_Leather_Light", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Item": { "ItemId": "Food_Wildmeat_Raw", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

### Empty Drop File

Use for drops that should yield nothing. A standalone empty drop file is literally an empty object:

```json
{}
```

(The `Empty` container type itself only appears as a child inside a `Choice` or `Multiple`, never as a standalone file root.)

---

## Reference

### Container Types

| Type | Behavior | Use Case |
|------|----------|----------|
| `Multiple` | All nested containers evaluated | Guaranteed multi-item drops |
| `Choice` | One container selected by weight | Random loot tables |
| `Single` | One item stack | Leaf node for actual items |
| `Empty` | No drop | Chance for nothing in Choice |
| `Droplist` | Reference another drop file | Modular composition |

### Container Properties

| Property | Type | Description |
|----------|------|-------------|
| `Type` | string | Container type: `Multiple`, `Choice`, `Single`, `Empty`, `Droplist` |
| `Containers` | array | Nested containers (for Multiple/Choice) |
| `Item` | object | Item definition (for Single) |
| `Weight` | double | Selection weight (for Choice children); percent chance 0-100 for Multiple children. Defaults to `100` |
| `RollsMin` | int | Minimum number of selections (for Choice). Defaults to `1` |
| `RollsMax` | int | Maximum number of selections (for Choice). Defaults to `1` |
| `MinCount` | int | Minimum number of passes over the child list (for Multiple). Defaults to `1` |
| `MaxCount` | int | Maximum number of passes over the child list (for Multiple). Defaults to `1` |
| `DroplistId` | string | Flat ID of a referenced drop file (for Droplist), e.g. `Zone1_Encounters_Tier1` |
| `$Comment` | string | Documentation comment (ignored by game) |

### Item Properties

| Property | Type | Description |
|----------|------|-------------|
| `ItemId` | string | Item identifier from item definitions |
| `QuantityMin` | int | Minimum quantity to drop. Defaults to `1` |
| `QuantityMax` | int | Maximum quantity to drop. Defaults to `1` |
| `Metadata` | object | Optional BSON metadata copied onto the produced item stack |

---

## Container Type Details

### Multiple Container

Evaluates all nested containers. Every child container produces drops.

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Item": { "ItemId": "Ingredient_Bone_Fragment", "QuantityMin": 1, "QuantityMax": 3 }
      },
      {
        "Type": "Single",
        "Item": { "ItemId": "Food_Wildmeat_Raw", "QuantityMin": 1, "QuantityMax": 2 }
      }
    ]
  }
}
```

**Weight as Percentage Chance:**

Within a Multiple container, child `Weight` values function as percentage chances (0-100):

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 100,
        "$Comment": "Always drops",
        "Item": { "ItemId": "Ingredient_Leather_Light", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 25,
        "$Comment": "25% chance to drop",
        "Item": { "ItemId": "Ingredient_Bone_Fragment", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

**Repeating the whole list with MinCount/MaxCount:**

`Multiple` also accepts `MinCount`/`MaxCount` (both default to `1`). The container picks a
count in that range and runs the *entire* child list that many times, so each child's
`Weight` percentage is rolled once per pass:

```json
{
  "Container": {
    "Type": "Multiple",
    "MinCount": 1,
    "MaxCount": 3,
    "Containers": [
      {
        "Type": "Single",
        "Weight": 50,
        "Item": { "ItemId": "Ingredient_Stick", "QuantityMin": 1, "QuantityMax": 2 }
      }
    ]
  }
}
```

### Choice Container

Selects one nested container based on weight. Higher weight = higher chance.

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 60,
        "Item": { "ItemId": "Ingredient_Feathers_Light", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 30,
        "Item": { "ItemId": "Ingredient_Feathers_Dark", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 10,
        "Item": { "ItemId": "Ingredient_Feathers_Red", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

**Weight Calculation:**

Total weight = sum of all child weights. Probability = child weight / total weight.

In the example above:
- Common: 60/100 = 60%
- Uncommon: 30/100 = 30%
- Rare: 10/100 = 10%

**Multiple Rolls with RollsMin/RollsMax:**

```json
{
  "Container": {
    "Type": "Choice",
    "RollsMin": 2,
    "RollsMax": 4,
    "Containers": [
      {
        "Type": "Single",
        "Weight": 50,
        "Item": { "ItemId": "Rock_Gem_Topaz", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 30,
        "Item": { "ItemId": "Rock_Gem_Ruby", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 20,
        "Item": { "ItemId": "Rock_Gem_Sapphire", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

This selects 2-4 items from the pool (with replacement).

### Single Container

Leaf node that defines an actual item drop.

```json
{
  "Container": {
    "Type": "Single",
    "Item": {
      "ItemId": "Plant_Crop_Corn_Item",
      "QuantityMin": 1,
      "QuantityMax": 3
    }
  }
}
```

**Quantity Range:**

When `QuantityMin` differs from `QuantityMax`, a random value is chosen uniformly within the range.

### Empty Container

Produces no drops. Used within Choice containers to add a "nothing drops" outcome.

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 80,
        "Item": { "ItemId": "Plant_Seeds_Wheat", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Empty",
        "Weight": 20,
        "$Comment": "20% chance for no seed drop"
      }
    ]
  }
}
```

### Droplist Container

References another drop file for modular composition. `DroplistId` is a flat identifier (not a directory path).

```json
{
  "Container": {
    "Type": "Droplist",
    "DroplistId": "Zone1_Encounters_Tier1"
  }
}
```

**Use Cases:**
- Share common loot pools across multiple encounters
- Create tiered loot table hierarchies
- Separate base drops from bonus drops

**Example: Encounter loot referencing a shared zone droplist:**

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Choice",
        "RollsMin": 1,
        "RollsMax": 2,
        "Containers": [
          {
            "Type": "Single",
            "Weight": 8,
            "Item": { "ItemId": "Food_Beef_Raw", "QuantityMin": 1, "QuantityMax": 2 }
          }
        ]
      },
      {
        "Type": "Droplist",
        "DroplistId": "Zone1_Encounters_Tier1"
      }
    ]
  }
}
```

---

## Drop Categories

### Crop Drops

**Location:** `Server/Drops/Crop/`

Defines what crops yield when harvested at different growth stages.

**Organization:** Each crop has its own subdirectory (e.g. `Crop/Carrot/`), containing a file per growth stage and variant.

**Naming Convention:** `Drops_Plant_Crop_{CropName}_{Stage}.json`, with optional biome and harvest qualifiers, e.g. `Drops_Plant_Crop_Carrot_StageFinal.json`, `Drops_Plant_Crop_Carrot_Eternal_StageFinal_Harvest.json`.

**Example: Carrot Final Stage** (`Crop/Carrot/Drops_Plant_Crop_Carrot_StageFinal.json`)

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Item": { "ItemId": "Plant_Crop_Carrot_Item" }
      },
      {
        "Type": "Single",
        "Weight": 100.0,
        "Item": { "ItemId": "Ingredient_Life_Essence", "QuantityMin": 3, "QuantityMax": 6 }
      },
      {
        "Type": "Single",
        "Weight": 0.5,
        "Item": { "ItemId": "Plant_Seeds_Carrot_Eternal", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

**Stage / Variant Suffixes:**
- `_Stage1`, `_Stage2`, `_StageFinal` - Growth stages
- `_Block` - Whole-block break drop
- `_Harvest` - Drops from harvesting (vs. breaking)
- `_Eternal` - Eternal biome variant

### NPC Drops

**Location:** `Server/Drops/NPCs/`

Organized by creature category. NPC drop files use a `Drop_` prefix (e.g. `Drop_Bison.json`):

```
Server/Drops/NPCs/
├── Drop_Wildlife.json      (shared fallback, sits at the category root)
├── Beast/
├── Boss/
├── Critter/
├── Elemental/
├── Flying_Beast/
├── Flying_Critter/
├── Flying_Wildlife/
├── Intelligent/
│   ├── Feran/
│   ├── Goblin/
│   ├── Klops/
│   ├── Kweebec/
│   ├── Outlander/
│   ├── Trork/
│   └── Tuluk/
├── Inventory/              (droplists used to stock an NPC's inventory, e.g. Drop_Arrows)
├── Livestock/
├── Loadouts/               (randomised weapon/hotbar loadouts)
├── Swimming_Beast/
├── Swimming_Critter/
├── Swimming_Wildlife/
├── Undead/
├── Void/
└── Wildlife/
```

**Example: Bison Drop** (`NPCs/Livestock/Drop_Bison.json`)

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Choice",
        "Weight": 100,
        "Containers": [
          {
            "Type": "Single",
            "Item": { "ItemId": "Food_Beef_Raw", "QuantityMin": 2, "QuantityMax": 3 }
          }
        ]
      },
      {
        "Type": "Choice",
        "Weight": 100,
        "Containers": [
          {
            "Type": "Single",
            "Item": { "ItemId": "Ingredient_Hide_Medium", "QuantityMin": 2, "QuantityMax": 3 }
          }
        ]
      }
    ]
  }
}
```

### Mining Drops

**Location:** `Server/Drops/Rock/`

Defines drops for ore blocks and crystals when mined.

**Naming Convention:** `Rock_{Material}.json`, `Crystal_{Type}.json`

**Example: Ice Rock Drop** (`Rock/Rock_Ice.json`)

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Item": { "ItemId": "Rock_Ice" }
      }
    ]
  }
}
```

**Example: Gem Crystal with Rarity**

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 60,
        "Item": { "ItemId": "Rock_Gem_Topaz", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 30,
        "Item": { "ItemId": "Rock_Gem_Ruby", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 10,
        "Item": { "ItemId": "Rock_Gem_Diamond", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

### Plant Drops

**Location:** `Server/Drops/Plant/`

Wild plants and foraged items.

**Example: Berry Bush** (`Plant/Plant_Bush_Berry_Red.json`)

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Item": { "ItemId": "Plant_Fruit_Berries_Red", "QuantityMin": 1, "QuantityMax": 2 }
      },
      { "Type": "Single", "Weight": 50, "Item": { "ItemId": "Ingredient_Fibre" } },
      { "Type": "Single", "Weight": 20, "Item": { "ItemId": "Ingredient_Fibre" } },
      { "Type": "Single", "Weight": 50, "Item": { "ItemId": "Ingredient_Stick" } }
    ]
  }
}
```

Note the two separate `Ingredient_Fibre` children: repeating the same item as two
independently-weighted `Multiple` children is the idiomatic way to express "50% chance of
one fibre, plus a further 20% chance of a second".

Some plant drop files yield nothing (e.g. `Plant/Plant_Leaves.json` is `{}`).

### Ingredient Drops

**Location:** `Server/Drops/Ingredients/`

Gatherable ingredients such as tree sap globs and wild grass. Files include `Tree_Sap_Glob_0.json`, `Wild_Grass_2_Harvest.json`, etc.

### Wood Drops

**Location:** `Server/Drops/Wood/`

Tree, leaf, and branch drops when cut. The eight files are `Bark.json`, `Tree_Leaves.json`,
`Tree_Leaves_Palm.json`, `Tree_Leaves_Physics.json`, `Tree_Leaves_Physics_Palm.json`,
`Wood_Branch.json`, `Wood_Sticks.json`, and `Wood_Stripped_Deco.json`.

**Example: Wood Branch Drop** (`Wood/Wood_Branch.json`)

A `Choice` between two equally-weighted `Multiple` outcomes — one that can also yield sap,
one that yields a single stick:

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Multiple",
        "Weight": 50,
        "Containers": [
          { "Type": "Single", "Item": { "ItemId": "Ingredient_Stick", "QuantityMin": 0, "QuantityMax": 2 } },
          { "Type": "Single", "Item": { "ItemId": "Ingredient_Tree_Sap", "QuantityMin": 0, "QuantityMax": 1 } }
        ]
      },
      {
        "Type": "Multiple",
        "Weight": 50,
        "Containers": [
          { "Type": "Single", "Item": { "ItemId": "Ingredient_Stick" } }
        ]
      }
    ]
  }
}
```

(A `QuantityMin` of `0` is legal and yields "possibly nothing" for that entry.)

### Container Drops

**Location:** `Server/Drops/Items/`

Defines what destructible containers (barrels, pots, coffins) drop when broken. Files include `Barrels.json`, `Container_Pot_Clay.json`, `Container_Coffins.json`, `Container_Trash.json`, `Spider_Cocoon.json`, and `Iron_Stack.json`. An `Empty.json` (literally `{}`) is also present for containers that drop nothing.

**Example: Clay Pot Drop** (`Items/Container_Pot_Clay.json`, abridged — the real file has
three more loot children)

A `Choice` with a heavily-weighted `Empty` child so most pots drop nothing:

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Choice",
        "Weight": 100,
        "Containers": [
          { "Type": "Single", "Item": { "ItemId": "Plant_Fruit_Apple", "QuantityMin": 1, "QuantityMax": 1 } }
        ]
      },
      {
        "Type": "Choice",
        "Weight": 25,
        "Containers": [
          { "Type": "Single", "Item": { "ItemId": "Weapon_Arrow_Crude", "QuantityMin": 1, "QuantityMax": 5 } }
        ]
      },
      {
        "Type": "Empty",
        "Weight": 800
      }
    ]
  }
}
```

### Prefab Drops

**Location:** `Server/Drops/Prefabs/`

Loot tables for prefab encounters and structures, organized as a **flat directory** of files named by zone, faction/encounter, and tier.

**Naming Convention:** `Zone{N}_{Faction|Encounters}_Tier{N}.json` (no subdirectories, no `Chest_*` files).

```
Server/Drops/Prefabs/
├── Zone1_Encounters_Tier1.json
├── Zone1_Goblin_Tier1.json
├── Zone1_Trork_Tier1.json
├── Zone1_Undead_Tier1.json
├── Zone2_Feran_Tier1.json
├── Zone3_Kweebec_Tier3.json
├── Zone4_Undead_Tier1.json
└── ...
```

**Example: Zone 1 Trork Tier 1** (`Prefabs/Zone1_Trork_Tier1.json`)

A weighted `Choice` of loot rolls combined with a shared zone-encounter droplist:

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Choice",
        "RollsMin": 1,
        "RollsMax": 2,
        "Containers": [
          { "Type": "Single", "Weight": 8, "Item": { "ItemId": "Food_Beef_Raw", "QuantityMin": 1, "QuantityMax": 2 } },
          { "Type": "Single", "Weight": 8, "Item": { "ItemId": "Food_Wildmeat_Raw", "QuantityMin": 1, "QuantityMax": 2 } },
          { "Type": "Single", "Weight": 1, "Item": { "ItemId": "Armor_Trork_Chest", "QuantityMin": 1, "QuantityMax": 1 } },
          { "Type": "Single", "Weight": 1, "Item": { "ItemId": "Weapon_Sword_Stone_Trork", "QuantityMin": 1, "QuantityMax": 1 } }
        ]
      },
      {
        "Type": "Droplist",
        "DroplistId": "Zone1_Encounters_Tier1"
      }
    ]
  }
}
```

### Trap Drops

**Location:** `Server/Drops/Traps/`

Fishing traps and other trap-based loot. The two shipped files are
`Drops_Fishing_Trap_Crude.json` and `Drops_Fishing_Trap_Crude_Baited_Wild.json`. Both are a
top-level `Choice` over `$Comment`-labelled rarity buckets — *Common Fish* (weight 100),
*Common Resource* (99), *Common Junk* (98), *Uncommon Junk* (49), *Rare Junk* (9),
*Epic Junk* (4), *Legendary Junk* (0.9), *Monster Fish* (0.01) — where each bucket is itself
a `Choice` of equally-weighted items. Note that weights are `double`, so fractional weights
like `0.9` and `0.01` are the normal way to express very rare buckets.

**Example: Fishing Trap** (illustrative, same shape as the shipped files)

```json
{
  "Container": {
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 50,
        "Item": { "ItemId": "Fish_Bluegill_Item", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 25,
        "Item": { "ItemId": "Fish_Catfish_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 15,
        "Item": { "ItemId": "Fish_Salmon_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 8,
        "Item": { "ItemId": "Fish_Pike_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 2,
        "Item": { "ItemId": "Fish_Whale_Humpback_Item", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

### Objective Drops

**Location:** `Server/Drops/Objectives/`

Quest completion rewards. The four files are `Treasure.json`, `Treasure_Map.json`,
`Trork_Camp_Chest.json`, and `Trork_Camp_Inventory.json`.

---

## File Organization

### Directory Structure

```
Server/Drops/
├── Crop/
│   ├── Carrot/
│   │   ├── Drops_Plant_Crop_Carrot_Stage1.json
│   │   ├── Drops_Plant_Crop_Carrot_StageFinal.json
│   │   └── ...
│   ├── Corn/
│   └── ...
├── Ingredients/
│   ├── Tree_Sap_Glob_0.json
│   ├── Wild_Grass_2.json
│   └── ...
├── Items/
│   ├── Barrels.json
│   ├── Container_Pot_Clay.json
│   ├── Empty.json
│   └── ...
├── NPCs/
│   ├── Drop_Wildlife.json
│   ├── Beast/
│   ├── Boss/
│   ├── Critter/
│   ├── Elemental/
│   ├── Flying_Beast/
│   ├── Intelligent/
│   │   ├── Feran/
│   │   ├── Goblin/
│   │   ├── Klops/
│   │   ├── Kweebec/
│   │   ├── Outlander/
│   │   ├── Trork/
│   │   └── Tuluk/
│   ├── Inventory/
│   │   └── Drop_Arrows.json
│   ├── Livestock/
│   │   ├── Drop_Bison.json
│   │   ├── Drop_Boar.json
│   │   └── ...
│   ├── Loadouts/
│   ├── Swimming_Beast/
│   ├── Undead/
│   ├── Void/
│   └── Wildlife/
├── Objectives/
├── Plant/
│   ├── Plant_Bush_Berry_Red.json
│   ├── Moss/
│   └── ...
├── Prefabs/
│   ├── Zone1_Encounters_Tier1.json
│   ├── Zone1_Trork_Tier1.json
│   └── ...
├── Rock/
│   ├── Rock_Ice.json
│   ├── Crystal/
│   └── ...
├── Traps/
├── Wood/
├── Soil_Gravel.json
└── Soil_Gravel_Pickaxe.json
```

### Naming Conventions

| Pattern | Description | Example |
|---------|-------------|---------|
| `Drop_{Entity}.json` | NPC drop file | `Drop_Bison.json` |
| `Drop_{Entity}_{Variant}.json` | NPC variant | `Drop_Bison_Calf.json` |
| `Drops_Plant_Crop_{Crop}_{Stage}.json` | Crop growth stage | `Drops_Plant_Crop_Carrot_StageFinal.json` |
| `Zone{N}_{Faction}_Tier{N}.json` | Prefab encounter loot | `Zone1_Trork_Tier1.json` |

### Biome Variant Suffixes

| Suffix | Description |
|--------|-------------|
| `_Eternal` | Eternal/magical biome |
| `_Wet` | Swamp/wetland biome |
| `_Winter` | Cold/snow biome |
| `_Desert` | Arid/desert biome |
| `_Cave` | Underground variant |

---

## Integration Points

### Block Drops

Blocks reference drop files from their `BlockType.Gathering` block, once per gather mode
(`Soft`, `Breaking`, `Harvest`, …). The value is the **flat droplist id** — the same id used
by `DroplistId`, never a directory path. From `Server/Item/Items/Deco/Deco_Iron_Stack.json`:

```json
{
  "BlockType": {
    "Gathering": {
      "Breaking": {
        "GatherType": "Rocks",
        "DropList": "Iron_Stack"
      },
      "UseDefaultDropWhenPlaced": true
    }
  }
}
```

`DropList` also accepts an **inline** drop-file object instead of an id, so a one-off drop
need not get its own file under `Server/Drops/`. From
`Server/Item/Items/Container/Furniture_Kweebec_Chest_Large.json`:

```json
{
  "BlockType": {
    "Gathering": {
      "Breaking": {
        "GatherType": "Woods",
        "DropList": {
          "Container": {
            "Type": "Single",
            "Item": { "ItemId": "Furniture_Kweebec_Chest_Small", "QuantityMin": 2, "QuantityMax": 2 }
          }
        }
      }
    }
  }
}
```

Container *contents* (as opposed to break drops) come from the block's block-entity
component instead — `BlockType.BlockEntity.Components.ItemContainerBlock`, which carries a
`Capacity` and, when the container should be stocked with loot, a `Droplist`.

See [Block Items - Containers](items-blocks.md#containers) for details.

### NPC Drops

NPC roles reference drop files via the `DropList` property. Role files are `Variant`
documents whose `Reference` is the **flat id** of the template they extend, with the
overrides under `Modify`. From `Server/NPC/Roles/Creature/Livestock/Bison.json`:

```json
{
  "Type": "Variant",
  "Reference": "Template_Animal_Neutral",
  "Modify": {
    "Appearance": "Bison",
    "DropList": "Drop_Bison"
  }
}
```

See [NPC Roles](npc-roles.md#key-properties) for details.

### Farming Crops

Crop drops are regular drop files under `Server/Drops/Crop/<Crop>/` — one per growth
stage plus a `*_StageFinal_Harvest` file for the harvest yield (e.g.
`Drops_Plant_Crop_Wheat_StageFinal_Harvest.json`). The crop block's per-stage state
definitions reference them via `Gathering` `DropList`:

```json
{
  "BlockType": {
    "State": {
      "Definitions": {
        "StageFinal": {
          "Gathering": {
            "Harvest": { "DropList": "Drops_Plant_Crop_Wheat_StageFinal_Harvest" },
            "Soft": { "DropList": "Drops_Plant_Crop_Wheat_StageFinal" }
          }
        }
      }
    }
  }
}
```

The `BlockType.Farming` block (`FarmingData`) only drives growth — its keys are `Stages`,
`StartingStageSet`, `StageSetAfterHarvest`, `ActiveGrowthModifiers`, `SoilConfig`,
`Lifetime`, and `TargetBlock`. It holds no drop data; drops always come from the referenced
drop files.

See [Block Items - Farming & Soil](items-blocks.md#farming--soil) for details.

### Prefab Containers

Prefab-placed chests bind loot in the prefab's block list: a `blocks[]` entry names
the container block and attaches an `ItemContainerBlock` component whose `Droplist`
names the drop file. From `Server/Prefabs/Goblin_Thief_Chest.prefab.json`:

```json
{
  "blocks": [
    {
      "x": 0, "y": 0, "z": 0,
      "name": "Furniture_Goblin_Chest_Small",
      "components": {
        "Components": {
          "ItemContainerBlock": {
            "Droplist": "Drop_Goblin_Thief",
            "ItemContainer": { "Capacity": 18, "Items": {} },
            "Capacity": 20
          }
        }
      },
      "rotation": 1
    }
  ]
}
```

See [Prefabs](prefabs.md) for details.

---

## Complete Examples

### Tiered Rarity Loot Table

A fishing trap with common to legendary fish:

```json
{
  "Container": {
    "$Comment": "Fishing Trap - Freshwater",
    "Type": "Choice",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 45,
        "$Comment": "Common (45%)",
        "Item": { "ItemId": "Fish_Bluegill_Item", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 25,
        "$Comment": "Common (25%)",
        "Item": { "ItemId": "Fish_Catfish_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 15,
        "$Comment": "Uncommon (15%)",
        "Item": { "ItemId": "Fish_Salmon_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 10,
        "$Comment": "Rare (10%)",
        "Item": { "ItemId": "Fish_Pike_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 4,
        "$Comment": "Epic (4%)",
        "Item": { "ItemId": "Fish_Snapjaw_Item", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Single",
        "Weight": 1,
        "$Comment": "Legendary (1%)",
        "Item": { "ItemId": "Fish_Whale_Humpback_Item", "QuantityMin": 1, "QuantityMax": 1 }
      }
    ]
  }
}
```

### Multi-Roll Encounter Chest

A dungeon chest with multiple random items:

```json
{
  "Container": {
    "$Comment": "Zone 2 Dungeon Boss Chest",
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Choice",
        "RollsMin": 4,
        "RollsMax": 6,
        "$Comment": "Random loot rolls",
        "Containers": [
          {
            "Type": "Single",
            "Weight": 25,
            "Item": { "ItemId": "Ingredient_Bar_Iron", "QuantityMin": 2, "QuantityMax": 4 }
          },
          {
            "Type": "Single",
            "Weight": 20,
            "Item": { "ItemId": "Potion_Health", "QuantityMin": 1, "QuantityMax": 2 }
          },
          {
            "Type": "Single",
            "Weight": 20,
            "Item": { "ItemId": "Food_Wildmeat_Cooked", "QuantityMin": 2, "QuantityMax": 4 }
          },
          {
            "Type": "Single",
            "Weight": 15,
            "Item": { "ItemId": "Rock_Gem_Ruby", "QuantityMin": 1, "QuantityMax": 2 }
          },
          {
            "Type": "Single",
            "Weight": 10,
            "Item": { "ItemId": "Rock_Gem_Emerald", "QuantityMin": 1, "QuantityMax": 1 }
          },
          {
            "Type": "Single",
            "Weight": 10,
            "Item": { "ItemId": "Recipe_Page", "QuantityMin": 1, "QuantityMax": 1 }
          }
        ]
      },
      {
        "Type": "Choice",
        "$Comment": "Guaranteed equipment piece",
        "Containers": [
          {
            "Type": "Single",
            "Weight": 40,
            "Item": { "ItemId": "Weapon_Sword_Iron", "QuantityMin": 1, "QuantityMax": 1 }
          },
          {
            "Type": "Single",
            "Weight": 30,
            "Item": { "ItemId": "Armor_Iron_Chest", "QuantityMin": 1, "QuantityMax": 1 }
          },
          {
            "Type": "Single",
            "Weight": 20,
            "Item": { "ItemId": "Tool_Pickaxe_Iron", "QuantityMin": 1, "QuantityMax": 1 }
          },
          {
            "Type": "Single",
            "Weight": 10,
            "Item": { "ItemId": "Weapon_Shortbow_Iron", "QuantityMin": 1, "QuantityMax": 1 }
          }
        ]
      }
    ]
  }
}
```

### Creature with Guaranteed and Chance Drops

A predator with guaranteed meat and chance for rare drops:

```json
{
  "Container": {
    "$Comment": "Wolf Drop Table",
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Single",
        "Weight": 100,
        "$Comment": "Always drops meat",
        "Item": { "ItemId": "Food_Wildmeat_Raw", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 100,
        "$Comment": "Always drops fur",
        "Item": { "ItemId": "Ingredient_Hide_Soft", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 75,
        "$Comment": "75% chance for bone",
        "Item": { "ItemId": "Ingredient_Bone_Fragment", "QuantityMin": 1, "QuantityMax": 2 }
      },
      {
        "Type": "Single",
        "Weight": 25,
        "$Comment": "25% chance for fang",
        "Item": { "ItemId": "Ingredient_Leather_Soft", "QuantityMin": 1, "QuantityMax": 1 }
      },
      {
        "Type": "Choice",
        "Weight": 5,
        "$Comment": "5% chance for rare drop",
        "Containers": [
          {
            "Type": "Single",
            "Weight": 80,
            "Item": { "ItemId": "Rock_Gem_Ruby", "QuantityMin": 1, "QuantityMax": 1 }
          },
          {
            "Type": "Single",
            "Weight": 20,
            "Item": { "ItemId": "Rock_Gem_Diamond", "QuantityMin": 1, "QuantityMax": 1 }
          }
        ]
      }
    ]
  }
}
```

### Modular Drop with a Shared Droplist

Prefab encounter loot files combine encounter-specific rolls with a shared zone droplist via the `Droplist` type. This is the real pattern used across `Prefabs/Zone*_*_Tier*.json`.

**Zone3_Kweebec_Tier3.json (faction loot + shared zone droplist):**
```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Choice",
        "RollsMin": 1,
        "RollsMax": 2,
        "Containers": [
          { "Type": "Single", "Weight": 15, "Item": { "ItemId": "Armor_Kweebec_Chest", "QuantityMin": 1, "QuantityMax": 1 } },
          { "Type": "Single", "Weight": 10, "Item": { "ItemId": "Weapon_Spear_Leaf", "QuantityMin": 2, "QuantityMax": 5 } }
        ]
      },
      {
        "Type": "Droplist",
        "$Comment": "Shared loot for all Zone 3, Tier 3 encounters",
        "DroplistId": "Zone3_Encounters_Tier3"
      }
    ]
  }
}
```

The referenced `Zone3_Encounters_Tier3.json` is itself a normal drop file (with its own `Container` root), letting many faction tables reuse one shared loot pool.

---

## Java API

Every drop file loads into server-side classes at startup: the file becomes an `ItemDropList` asset whose
root is an `ItemDropContainer` tree mirroring the JSON `Container` structure. Plugins can look droplists up
and roll them programmatically.

### ItemDropList

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config`

The asset class for one drop file. Registered with asset path `Drops`, so the asset id is the **flat
filename** documented above (e.g. `Zone1_Encounters_Tier1`), regardless of subdirectory.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetMap()` (static) | `DefaultAssetMap<String, ItemDropList>` | All loaded droplists |
| `getAssetStore()` (static) | `AssetStore<String, ItemDropList, ...>` | The backing asset store |
| `getId()` | `String` | Droplist id (flat filename) |
| `getContainer()` | `ItemDropContainer` | Root of the container tree (null for an empty `{}` file) |

### ItemDropContainer

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.container`

Abstract base class of the container tree. Each JSON `Type` value maps to a subclass in the same package:

| JSON `Type` | Class |
|-------------|-------|
| `Multiple` | `MultipleItemDropContainer` |
| `Choice` | `ChoiceItemDropContainer` |
| `Single` | `SingleItemDropContainer` |
| `Empty` | `EmptyItemDropContainer` |
| `Droplist` | `DroplistItemDropContainer` |

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getWeight()` | `double` | The container's `Weight` value |
| `populateDrops(List<ItemDrop>, DoubleSupplier, String)` | `void` | Roll the tree once, appending the resulting drops; the `DoubleSupplier` provides randomness and the `String` names the root droplist (guards `Droplist` references against self-recursion) |
| `getAllDrops(List<ItemDrop>)` | `List<ItemDrop>` | Collect every drop the tree can possibly produce (no randomness) |

Each rolled entry is an `ItemDrop` (same package as `ItemDropList`): `getItemId()`, `getQuantityMin()`,
`getQuantityMax()`, `getRandomQuantity(Random)`, `getMetadata()`.

### Rolling a Droplist from a Plugin

The simplest entry point is `ItemModule.getRandomItemDrops(String)`, which resolves the droplist, rolls it,
and converts the result to item stacks:

```java
import com.hypixel.hytale.server.core.modules.item.ItemModule;
import com.hypixel.hytale.server.core.inventory.ItemStack;

List<ItemStack> drops = ItemModule.get().getRandomItemDrops("Zone1_Encounters_Tier1");
```

For lower-level control, walk the tree yourself:

```java
import com.hypixel.hytale.server.core.asset.type.item.config.ItemDrop;
import com.hypixel.hytale.server.core.asset.type.item.config.ItemDropList;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

ItemDropList dropList = ItemDropList.getAssetMap().getAsset("Zone1_Encounters_Tier1");
if (dropList != null && dropList.getContainer() != null) {
    ThreadLocalRandom random = ThreadLocalRandom.current();
    List<ItemDrop> rolled = new ArrayList<>();
    dropList.getContainer().populateDrops(rolled, random::nextDouble, dropList.getId());
    for (ItemDrop drop : rolled) {
        int quantity = drop.getRandomQuantity(random);
        // build ItemStacks, spawn item entities, etc.
    }
}
```

---

## Gotchas & Errors

These are authoring symptoms for drop JSON, sourced from the documented format above (no literal game error strings apply to drop files).

- **Symptom:** a drop file is ignored or errors on load → the root isn't wrapped in a top-level `Container` object. Fix: every drop file is `{ "Container": { "Type": ... } }`; the only exception is a no-drop file, which is literally `{}` (see [Root structure](#drop-system)).
- **Symptom:** a `Droplist` reference resolves to nothing → `DroplistId` is a **flat id**, not a directory path. Fix: use the flat id (e.g. `Zone1_Encounters_Tier1`), not `Prefabs/Zone1_Encounters_Tier1`.
- **Symptom:** items don't drop / drop with wrong rarity because every child fires → `Multiple` evaluates **all** children (child `Weight` is a 0-100 percent chance), while `Choice` picks **one** child by relative weight. Fix: use `Choice` for "pick one of", `Multiple` for "roll each independently".
- **Symptom:** a "chance for nothing" outcome never happens → `Empty` only works as a child inside a `Choice`/`Multiple`, never as a standalone file root. Fix: add an `Empty` child with a `Weight` inside a `Choice`.
- **Symptom:** an item never appears though it's listed → `ItemId` didn't match a real item definition (ids are case-sensitive). Fix: use the exact item id from [Item Definitions](items.md).

---

## Related Documentation

- [Item Definitions](items.md) - Item IDs, properties, and inheritance
- [NPC Roles](npc-roles.md) - NPC configuration and DropList property
- [Block Items](items-blocks.md) - Container blocks and Droplist property
- [Prefabs](prefabs.md) - Prefab container loot configuration
- [Inventory API](inventory.md) - Programmatic inventory and item management
