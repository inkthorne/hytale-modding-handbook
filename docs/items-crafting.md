---
title: "Crafting System"
description: "Hytale crafting in JSON plus Java — bench types (Crafting, Processing, DiagramCrafting, StructuralCrafting), recipe structure, input types (ItemId vs ResourceTypeId), and bench requirements."
seo:
  type: TechArticle
---

# Crafting System

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item` · **Verified against 0.5.0**

> Part of the [Items API](items.md). For inventory management, see [Inventory Reference](inventory.md).

This page documents crafting: the bench items that host crafting UIs, the JSON recipe structure embedded in item definitions, the tier-upgrade system, and the Java `CraftingRecipe` API and crafting events.

## Overview

Defined as JSON assets under `Server/Item` with a supporting Java API, and covers:
- Bench types: `Crafting`, `Processing`, `DiagramCrafting`, `StructuralCrafting`
- Recipe structure embedded in item definitions (inputs, outputs, requirements)
- Input types (`ItemId` vs `ResourceTypeId`) and `BenchRequirement`
- Processing and salvage recipes
- The bench tier system (`TierLevels`, time-reduction modifiers)
- Java API: `CraftingRecipe`, `BenchRequirement`, `BenchType`, and `CraftRecipeEvent`

## Architecture
```
Crafting
├── Bench items (BlockType.Bench)
│   ├── Crafting (Workbench, Weapon Bench, Alchemy)
│   ├── Processing (Furnace, Campfire, Tannery, Salvage)
│   ├── DiagramCrafting (Armory)
│   └── StructuralCrafting (Builder's Bench)
├── Recipe (embedded in item definition)
│   ├── Input (ItemId / ResourceTypeId + Quantity)
│   ├── Output
│   └── BenchRequirement (Type, Categories, Id, RequiredTierLevel)
├── Tier system (TierLevels, time-reduction modifiers)
└── Java API
    ├── CraftingRecipe
    ├── BenchRequirement / BenchType
    └── CraftRecipeEvent (Pre / Post)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Bench` | `BlockType.Bench` (item property) | Bench config; `Type`, categories, tier levels |
| `Recipe` | item property | Embedded crafting recipe (inputs, output, requirements) |
| `BenchRequirement` (asset) | `Recipe.BenchRequirement` | JSON bench requirement for a recipe |
| `CraftingRecipe` | `server.core.asset.type.item.config` | Java recipe config (inputs, outputs, requirements) |
| `BenchRequirement` | `protocol` | Java type for a recipe's required bench |
| `BenchType` | `protocol` | Crafting bench type enum |
| `CraftRecipeEvent` | `server.core.event.events.ecs` | ECS crafting event (`Pre`/`Post`) |

## Quick Navigation

| Bench Type | Examples | Description |
|------------|----------|-------------|
| [Crafting](#crafting-type-benches) | Workbench, Weapon Bench, Alchemy | Standard recipe crafting |
| [Processing](#processing-type-benches) | Furnace, Campfire, Tannery, Salvage | Fuel-based or timed processing |
| [DiagramCrafting](#diagramcrafting-type) | Armory | Blueprint-based crafting |
| [StructuralCrafting](#structuralcrafting-type) | Builder's Bench | Building block variants |

---

## Crafting Benches

Crafting benches are placeable items that provide crafting interfaces. Each bench has a `Bench` configuration within its `BlockType` that defines its behavior.

### Crafting Type Benches

Standard crafting benches allow players to craft items from recipes displayed in categorized menus.

#### Bench_WorkBench

**Location:** `Server/Item/Items/Bench/Bench_WorkBench.json`

The workbench is the primary crafting station with multiple categories and tier upgrades.

```json
{
  "Recipe": {
    "Input": [
      { "Quantity": 4, "ResourceTypeId": "Wood_Trunk" },
      { "Quantity": 3, "ResourceTypeId": "Rock" }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Tools"],
      "Id": "Fieldcraft"
    }]
  },
  "BlockType": {
    "Bench": {
      "Type": "Crafting",
      "Categories": [
        { "Id": "Workbench_Survival", "Icon": "Icons/CraftingCategories/Workbench/WeaponsCrude.png", "Name": "server.benchCategories.workbench.survival" },
        { "Id": "Workbench_Tools", "Icon": "Icons/CraftingCategories/Workbench/Tools.png", "Name": "server.benchCategories.workbench.tools" },
        { "Id": "Workbench_Crafting", "Icon": "Icons/CraftingCategories/Workbench/Processing.png", "Name": "server.benchCategories.workbench.crafting" },
        { "Id": "Workbench_Tinkering", "Icon": "Icons/CraftingCategories/Workbench/Deco_Target.png", "Name": "server.benchCategories.workbench.tinkering" }
      ],
      "Id": "Workbench",
      "TierLevels": [
        {
          "CraftingTimeReductionModifier": 0.0,
          "UpgradeRequirement": {
            "Material": [
              { "ItemId": "Ingredient_Bar_Copper", "Quantity": 30 },
              { "ItemId": "Ingredient_Bar_Iron", "Quantity": 20 },
              { "ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": 20 }
            ],
            "TimeSeconds": 5.0
          }
        },
        {
          "CraftingTimeReductionModifier": 0.15,
          "UpgradeRequirement": {
            "Material": [
              { "ItemId": "Ingredient_Bar_Thorium", "Quantity": 30 },
              { "ItemId": "Ingredient_Bar_Cobalt", "Quantity": 20 },
              { "ItemId": "Ingredient_Leather_Heavy", "Quantity": 30 },
              { "ItemId": "Ingredient_Fabric_Scrap_Shadoweave", "Quantity": 50 },
              { "ItemId": "Ingredient_Fire_Essence", "Quantity": 25 }
            ],
            "TimeSeconds": 10.0
          }
        },
        { "CraftingTimeReductionModifier": 0.3 }
      ]
    }
  }
}
```

##### Bench Configuration Properties

| Property | Type | Description |
|----------|------|-------------|
| `Type` | string | Bench type: `Crafting`, `Processing`, `DiagramCrafting`, `StructuralCrafting` |
| `Id` | string | Unique bench identifier referenced by recipes |
| `Categories` | array | Crafting categories with icons and localization |
| `TierLevels` | array | Upgrade tiers with time reduction and requirements |
| `LocalOpenSoundEventId` | string | Sound when opening bench UI |
| `LocalCloseSoundEventId` | string | Sound when closing bench UI |
| `CompletedSoundEventId` | string | Sound when crafting completes |
| `FailedSoundEventId` | string | Sound when crafting fails |
| `BenchUpgradeSoundEventId` | string | Sound when upgrade starts |
| `BenchUpgradeCompletedSoundEventId` | string | Sound when upgrade completes |

#### Bench_Weapon

**Location:** `Server/Item/Items/Bench/Bench_Weapon.json`

Weapon bench for crafting swords, maces, battleaxes, daggers, and bows.

```json
{
  "Recipe": {
    "TimeSeconds": 3,
    "Input": [
      { "ItemId": "Ingredient_Bar_Copper", "Quantity": 2 },
      { "ResourceTypeId": "Wood_Trunk", "Quantity": 10 },
      { "ResourceTypeId": "Rock", "Quantity": 5 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Workbench_Crafting"],
      "Id": "Workbench"
    }]
  },
  "BlockType": {
    "Bench": {
      "Type": "Crafting",
      "Categories": [
        { "Id": "Weapon_Sword", "Icon": "Icons/CraftingCategories/Armory/Sword.png", "Name": "server.benchCategories.sword" },
        { "Id": "Weapon_Mace", "Icon": "Icons/CraftingCategories/Armory/Mace.png", "Name": "server.benchCategories.mace" },
        { "Id": "Weapon_Battleaxe", "Icon": "Icons/CraftingCategories/Armory/Battleaxe.png", "Name": "server.benchCategories.battleaxe" },
        { "Id": "Weapon_Daggers", "Icon": "Icons/CraftingCategories/Armory/Daggers.png", "Name": "server.benchCategories.daggers" },
        { "Id": "Weapon_Bow", "Icon": "Icons/CraftingCategories/Armory/Bow.png", "Name": "server.benchCategories.bow" }
      ],
      "Id": "Weapon_Bench",
      "TierLevels": [
        { "CraftingTimeReductionModifier": 0.0 },
        { "CraftingTimeReductionModifier": 0.15 },
        { "CraftingTimeReductionModifier": 0.3 }
      ]
    }
  }
}
```

#### Bench_Armour

**Location:** `Server/Item/Items/Bench/Bench_Armour.json`

Armor bench for crafting armor pieces and shields.

| Property | Value |
|----------|-------|
| Bench Id | `Armor_Bench` |
| Categories | `Armor_Head`, `Armor_Chest`, `Armor_Hands`, `Armor_Legs`, `Weapon_Shield` |
| Tier Levels | 3 (0%, 15%, 30% time reduction) |
| ItemLevel | 2 |

#### Bench_Alchemy

**Location:** `Server/Item/Items/Bench/Bench_Alchemy.json`

Alchemy bench for crafting potions and bombs. Requires Workbench Tier 2 to craft.

```json
{
  "Recipe": {
    "TimeSeconds": 3,
    "Input": [
      { "ResourceTypeId": "Rock", "Quantity": 20 },
      { "ItemId": "Ingredient_Bar_Gold", "Quantity": 5 },
      { "ItemId": "Ingredient_Sac_Venom", "Quantity": 10 },
      { "ItemId": "Ingredient_Bone_Fragment", "Quantity": 10 }
    ],
    "BenchRequirement": [{
      "Id": "Workbench",
      "Type": "Crafting",
      "Categories": ["Workbench_Crafting"],
      "RequiredTierLevel": 2
    }]
  },
  "BlockType": {
    "Bench": {
      "Type": "Crafting",
      "Categories": [
        { "Id": "Alchemy_Potions", "Icon": "Icons/CraftingCategories/Alchemy/Combat_Potions.png", "Name": "server.benchCategories.combatPotions" },
        { "Id": "Alchemy_Potions_Misc", "Icon": "Icons/CraftingCategories/Alchemy/Misc_Potions.png", "Name": "server.benchCategories.miscPotions" },
        { "Id": "Alchemy_Bombs", "Icon": "Icons/CraftingCategories/Alchemy/Bombs.png", "Name": "server.benchCategories.bombs" }
      ],
      "Id": "Alchemybench",
      "TierLevels": [
        { "CraftingTimeReductionModifier": 0.0 },
        { "CraftingTimeReductionModifier": 0.3 }
      ]
    }
  }
}
```

#### Bench_Cooking

**Location:** `Server/Item/Items/Bench/Bench_Cooking.json`

Cooking bench for preparing food items.

| Property | Value |
|----------|-------|
| Bench Id | `Cookingbench` |
| Categories | `Prepared`, `Baked`, `Ingredients` |
| ItemLevel | 6 |

---

### Processing Type Benches

Processing benches convert raw materials into refined products using fuel or time-based processing.

#### Bench_Furnace

**Location:** `Server/Item/Items/Bench/Bench_Furnace.json`

The furnace smelts ores into bars using fuel. It produces charcoal as a bonus output.

```json
{
  "Recipe": {
    "Input": [
      { "ResourceTypeId": "Wood_Trunk", "Quantity": 6 },
      { "ResourceTypeId": "Rock", "Quantity": 6 }
    ],
    "Output": [{
      "ItemId": "Bench_Furnace",
      "Metadata": {
        "BlockState": {
          "Type": "processingBench",
          "FuelContainer": { "Capacity": 2 }
        }
      }
    }],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Workbench_Crafting"],
      "Id": "Workbench"
    }],
    "TimeSeconds": 3
  },
  "BlockType": {
    "Bench": {
      "Type": "Processing",
      "AllowNoInputProcessing": true,
      "Input": [
        { "FilterValidIngredients": true },
        { "FilterValidIngredients": true }
      ],
      "Fuel": [{
        "ResourceTypeId": "Fuel",
        "Icon": "Icons/Processing/FuelSlotIcon.png"
      }],
      "ExtraOutput": {
        "Outputs": [{ "ItemId": "Ingredient_Charcoal" }],
        "PerFuelItemsConsumed": 2,
        "IgnoredFuelSources": [
          { "ItemId": "Ingredient_Charcoal" },
          { "ItemId": "Ingredient_Fibre" },
          { "ItemId": "Ingredient_Tree_Sap" }
        ]
      },
      "OutputSlotsCount": 4,
      "Id": "Furnace",
      "TierLevels": [
        {
          "CraftingTimeReductionModifier": 0.0,
          "UpgradeRequirement": {
            "Material": [
              { "ItemId": "Ingredient_Bar_Copper", "Quantity": 5 },
              { "ItemId": "Ingredient_Bar_Iron", "Quantity": 5 },
              { "ItemId": "Ingredient_Bar_Thorium", "Quantity": 5 },
              { "ItemId": "Ingredient_Bar_Cobalt", "Quantity": 5 }
            ],
            "TimeSeconds": 3
          }
        },
        {
          "CraftingTimeReductionModifier": 0.3,
          "ExtraInputSlot": 1
        }
      ]
    }
  }
}
```

##### Processing Bench Properties

| Property | Type | Description |
|----------|------|-------------|
| `AllowNoInputProcessing` | boolean | Allow processing with only fuel (for charcoal production) |
| `Input` | array | Input slot configuration |
| `FilterValidIngredients` | boolean | Only allow items with valid processing recipes |
| `Fuel` | array | Fuel slot configuration with resource type and icon |
| `ExtraOutput` | object | Bonus outputs from fuel consumption |
| `OutputSlotsCount` | int | Number of output slots |

##### ExtraOutput Properties

| Property | Type | Description |
|----------|------|-------------|
| `Outputs` | array | Items produced as bonus output |
| `PerFuelItemsConsumed` | int | Fuel items needed per bonus output |
| `IgnoredFuelSources` | array | Fuel items that don't produce bonus output |

#### Bench_Campfire

**Location:** `Server/Item/Items/Bench/Bench_Campfire.json`

Simple processing bench for early-game cooking and smelting.

```json
{
  "Recipe": {
    "TimeSeconds": 1,
    "Input": [
      { "ItemId": "Ingredient_Stick", "Quantity": 4 },
      { "ResourceTypeId": "Rubble", "Quantity": 2 }
    ],
    "BenchRequirement": [
      { "Type": "Crafting", "Categories": ["Tools"], "Id": "Fieldcraft" },
      { "Id": "Workbench", "Type": "Crafting", "Categories": ["Workbench_Survival"] }
    ]
  },
  "BlockType": {
    "Bench": {
      "Type": "Processing",
      "AllowNoInputProcessing": true,
      "Input": [
        { "FilterValidIngredients": true },
        { "FilterValidIngredients": true }
      ],
      "Fuel": [{
        "ResourceTypeId": "Fuel",
        "Icon": "Icons/Processing/FuelSlotIcon.png"
      }],
      "ExtraOutput": {
        "Outputs": [{ "ItemId": "Ingredient_Charcoal" }],
        "PerFuelItemsConsumed": 2,
        "IgnoredFuelSources": [
          { "ItemId": "Ingredient_Charcoal" },
          { "ItemId": "Ingredient_Fibre" },
          { "ItemId": "Ingredient_Tree_Sap" }
        ]
      },
      "OutputSlotsCount": 4,
      "Id": "Campfire"
    }
  }
}
```

Note: The campfire can be crafted at either Fieldcraft or Workbench (multiple `BenchRequirement` entries).

#### Bench_Salvage

**Location:** `Server/Item/Items/Bench/Bench_Salvage.json`

Breaks down items into component materials. Requires Workbench Tier 2 to craft.

```json
{
  "Recipe": {
    "Input": [
      { "ItemId": "Ingredient_Bar_Iron", "Quantity": 6 },
      { "ResourceTypeId": "Wood_Trunk", "Quantity": 5 },
      { "ResourceTypeId": "Rock", "Quantity": 5 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Workbench_Crafting"],
      "Id": "Workbench",
      "RequiredTierLevel": 2
    }],
    "TimeSeconds": 3
  },
  "BlockType": {
    "Bench": {
      "Type": "Processing",
      "Input": [{ "FilterValidIngredients": true }],
      "ExtraOutput": {
        "Outputs": [{ "ItemId": "Ingredient_Charcoal" }],
        "PerFuelItemsConsumed": 2
      },
      "OutputSlotsCount": 4,
      "Id": "Salvagebench"
    }
  }
}
```

#### Bench_Tannery

**Location:** `Server/Item/Items/Bench/Bench_Tannery.json`

Processes hides into leather. No fuel required.

```json
{
  "BlockType": {
    "Bench": {
      "Type": "Processing",
      "Input": [
        { "FilterValidIngredients": true },
        { "FilterValidIngredients": true }
      ],
      "OutputSlotsCount": 2,
      "Id": "Tannery",
      "TierLevels": [
        { "CraftingTimeReductionModifier": 0.0 },
        {
          "CraftingTimeReductionModifier": 0.4,
          "ExtraInputSlot": 1,
          "ExtraOutputSlot": 2
        }
      ]
    }
  }
}
```

##### Tier Upgrade Slot Properties

| Property | Type | Description |
|----------|------|-------------|
| `ExtraInputSlot` | int | Additional input slots at this tier |
| `ExtraOutputSlot` | int | Additional output slots at this tier |

---

### DiagramCrafting Type

Blueprint-based crafting with hierarchical category selection.

#### Bench_Armory

**Location:** `Server/Item/Items/Bench/Bench_Armory.json`

Advanced crafting station with diagram-based item selection. Note: This is a developer item.

```json
{
  "Quality": "Developer",
  "BlockType": {
    "Bench": {
      "Type": "DiagramCrafting",
      "Categories": [
        {
          "Id": "Weapons",
          "Icon": "Icons/CraftingCategories/Armory/Weapons.png",
          "Name": "Weapons",
          "ItemCategories": [
            { "Id": "Sword", "Icon": "Icons/CraftingCategories/Armory/Sword.png", "Slots": 2, "Name": "Sword" },
            { "Id": "Club", "Icon": "Icons/CraftingCategories/Armory/Club.png", "Slots": 2, "Name": "Club" },
            { "Id": "Axe", "Icon": "Icons/CraftingCategories/Armory/Axe.png", "Slots": 2, "Name": "Axe" },
            { "Id": "Longsword", "Icon": "Icons/CraftingCategories/Armory/Longsword.png", "Slots": 2, "Name": "Longsword" },
            { "Id": "Mace", "Icon": "Icons/CraftingCategories/Armory/Mace.png", "Slots": 2, "Name": "Mace" },
            { "Id": "Battleaxe", "Icon": "Icons/CraftingCategories/Armory/Battleaxe.png", "Slots": 2, "Name": "Battleaxe" },
            { "Id": "Bow", "Icon": "Icons/CraftingCategories/Armory/Bow.png", "Slots": 2, "Name": "Bow" },
            { "Id": "Shield", "Icon": "Icons/CraftingCategories/Armory/Shield.png", "Slots": 2, "Name": "Shield" }
          ]
        },
        {
          "Id": "Armor",
          "Icon": "Icons/CraftingCategories/Armory/MetalArmor.png",
          "Name": "Armor",
          "ItemCategories": [
            { "Id": "Head", "Icon": "Icons/CraftingCategories/Armory/MetalHead.png", "Slots": 2, "Name": "Head" },
            { "Id": "Chest", "Icon": "Icons/CraftingCategories/Armory/MetalChest.png", "Slots": 2, "Name": "Chest" },
            { "Id": "Hands", "Icon": "Icons/CraftingCategories/Armory/MetalHands.png", "Slots": 2, "Name": "Hands" },
            { "Id": "Legs", "Icon": "Icons/CraftingCategories/Armory/MetalLegs.png", "Slots": 2, "Name": "Legs" }
          ]
        }
      ],
      "Id": "Armory"
    }
  }
}
```

##### DiagramCrafting Category Properties

| Property | Type | Description |
|----------|------|-------------|
| `ItemCategories` | array | Nested categories within main category |
| `Slots` | int | Number of crafting slots per item category |

---

### StructuralCrafting Type

Used for creating building block variants (stairs, slabs, walls). Referenced by the Builder's Bench.

---

## Recipe Structure

Recipes can be embedded in item definitions or defined as standalone files.

### Embedded Recipe (Item Definition)

Recipes are typically embedded within item JSON files under the `Recipe` property.

**Example: Iron Sword Recipe**

```json
{
  "Parent": "Template_Weapon_Sword",
  "Recipe": {
    "TimeSeconds": 3.5,
    "KnowledgeRequired": false,
    "Input": [
      { "ItemId": "Ingredient_Bar_Iron", "Quantity": 6 },
      { "ItemId": "Ingredient_Leather_Light", "Quantity": 3 },
      { "ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": 3 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Weapon_Sword"],
      "Id": "Weapon_Bench"
    }]
  }
}
```

### Basic Recipe Properties

| Property | Type | Description |
|----------|------|-------------|
| `TimeSeconds` | float | Crafting duration in seconds |
| `Input` | array | Required materials (ItemId or ResourceTypeId) |
| `BenchRequirement` | array | Required crafting benches |
| `Output` | array | Output items (optional, defaults to the item containing the recipe) |
| `PrimaryOutput` | object | Main output item |
| `OutputQuantity` | int | Number of items produced (default: 1) |
| `KnowledgeRequired` | boolean | Whether recipe must be learned first |

### Input Types

Recipes can require specific items or abstract resource categories:

#### ItemId Input

Requires a specific item:

```json
{
  "Input": [
    { "ItemId": "Ingredient_Bar_Iron", "Quantity": 6 }
  ]
}
```

#### ResourceTypeId Input

Accepts any item matching the resource type:

```json
{
  "Input": [
    { "ResourceTypeId": "Wood_Trunk", "Quantity": 4 },
    { "ResourceTypeId": "Rock", "Quantity": 3 }
  ]
}
```

##### Common Resource Types

| ResourceTypeId | Matching Items |
|----------------|----------------|
| `Wood_Trunk` | Any wood log (Oak, Birch, etc.) |
| `Rock` | Stone, Cobblestone, etc. |
| `Rubble` | Gravel, small stones |
| `Fuel` | Wood, charcoal, coal |
| `Metal_Bars` | Any metal bar (Copper, Iron, etc.) |
| `Foods` | Any food item |
| `Fruits` | Any fruit item |
| `Vegetables` | Any vegetable item |

Items register their resource types via `ResourceTypes`:

```json
{
  "ResourceTypes": [
    { "Id": "Metal_Bars" }
  ]
}
```

### BenchRequirement

Specifies which bench(es) can craft the recipe:

```json
{
  "BenchRequirement": [{
    "Type": "Crafting",
    "Id": "Weapon_Bench",
    "Categories": ["Weapon_Sword"],
    "RequiredTierLevel": 1
  }]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Type` | string | Bench type: `Crafting`, `Processing`, `DiagramCrafting`, `StructuralCrafting` |
| `Id` | string | Specific bench ID |
| `Categories` | array | Bench categories where recipe appears |
| `RequiredTierLevel` | int | Minimum bench tier required (1-indexed) |

Multiple bench requirements allow crafting at different stations:

```json
{
  "BenchRequirement": [
    { "Type": "Crafting", "Categories": ["Tools"], "Id": "Fieldcraft" },
    { "Type": "Crafting", "Categories": ["Workbench_Survival"], "Id": "Workbench" }
  ]
}
```

---

## Processing Recipes

Processing recipes convert raw materials using time-based processing, optionally with fuel.

**Example: Iron Bar Processing**

```json
{
  "Recipe": {
    "Input": [
      { "ItemId": "Ore_Iron", "Quantity": 1 }
    ],
    "BenchRequirement": [{
      "Type": "Processing",
      "Id": "Furnace"
    }],
    "OutputQuantity": 1,
    "TimeSeconds": 14
  }
}
```

Processing benches automatically filter inputs to only show items with valid recipes when `FilterValidIngredients: true` is set.

---

## Salvage Recipes

Salvage recipes are standalone files that break down items into components.

**Location:** `Server/Item/Recipes/Salvage/`

**Example: Iron Chest Armor Salvage**

```json
{
  "Input": [
    { "ItemId": "Armor_Iron_Chest", "Quantity": 1 }
  ],
  "PrimaryOutput": {
    "ItemId": "Ore_Iron",
    "Quantity": 6
  },
  "Output": [
    { "ItemId": "Ore_Iron", "Quantity": 6 },
    { "ItemId": "Ingredient_Hide_Light", "Quantity": 2 },
    { "ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": 2 }
  ],
  "BenchRequirement": [{
    "Type": "Processing",
    "Id": "Salvagebench"
  }],
  "TimeSeconds": 4
}
```

### Salvage Recipe Properties

| Property | Type | Description |
|----------|------|-------------|
| `Input` | array | Item to salvage |
| `PrimaryOutput` | object | Main returned material |
| `Output` | array | All returned materials |
| `TimeSeconds` | float | Salvaging duration |

---

## Tier System

Benches can have multiple tiers that reduce crafting time and unlock additional slots.

### TierLevels Configuration

```json
{
  "TierLevels": [
    {
      "CraftingTimeReductionModifier": 0.0,
      "UpgradeRequirement": {
        "Material": [
          { "ItemId": "Ingredient_Bar_Copper", "Quantity": 30 },
          { "ItemId": "Ingredient_Bar_Iron", "Quantity": 20 }
        ],
        "TimeSeconds": 5.0
      }
    },
    {
      "CraftingTimeReductionModifier": 0.15
    },
    {
      "CraftingTimeReductionModifier": 0.3
    }
  ]
}
```

### TierLevel Properties

| Property | Type | Description |
|----------|------|-------------|
| `CraftingTimeReductionModifier` | float | Percentage reduction (0.15 = 15% faster) |
| `UpgradeRequirement` | object | Materials and time to upgrade to next tier |
| `ExtraInputSlot` | int | Additional input slots at this tier |
| `ExtraOutputSlot` | int | Additional output slots at this tier |

### Tier Time Reduction by Bench

| Bench | Tier 1 | Tier 2 | Tier 3 |
|-------|--------|--------|--------|
| Workbench | 0% | 15% | 30% |
| Weapon Bench | 0% | 15% | 30% |
| Armor Bench | 0% | 15% | 30% |
| Alchemy Bench | 0% | 30% | - |
| Furnace | 0% | 30% | - |
| Tannery | 0% | 40% | - |

---

## Recipe with Tier Requirement

Some recipes require a minimum bench tier:

```json
{
  "BenchRequirement": [{
    "Id": "Workbench",
    "Type": "Crafting",
    "Categories": ["Workbench_Crafting"],
    "RequiredTierLevel": 2
  }]
}
```

---

## API Reference

### CraftingRecipe

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config`

```java
// Get recipe information
String getId()
MaterialQuantity[] getInput()
MaterialQuantity[] getOutputs()
MaterialQuantity getPrimaryOutput()
BenchRequirement[] getBenchRequirement()
float getTimeSeconds()
boolean isKnowledgeRequired()

// Check tier restrictions
boolean isRestrictedByBenchTierLevel(String benchId, int tierLevel)
```

### BenchRequirement

**Package:** `com.hypixel.hytale.protocol`

```java
BenchType type           // Type of bench required
String id                // Specific bench ID
String[] categories      // Bench categories
int requiredTierLevel    // Minimum bench tier
```

### BenchType

**Package:** `com.hypixel.hytale.protocol`

```java
public enum BenchType {
    Crafting,           // Standard crafting table
    Processing,         // Processing station (smelting, etc.)
    DiagramCrafting,    // Blueprint-based crafting
    StructuralCrafting  // Building/structural crafting
}
```

### CraftRecipeEvent

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

`CraftRecipeEvent` is an abstract event that extends `CancellableEcsEvent`. Its data
accessors and cancellation are defined on the base class; the `Pre` and `Post`
subclasses add no methods of their own.

```java
// Abstract base
abstract class CraftRecipeEvent extends CancellableEcsEvent {
    CraftingRecipe getCraftedRecipe();
    int getQuantity();

    // Inherited from CancellableEcsEvent:
    //   boolean isCancelled();
    //   void setCancelled(boolean);
}

// Subclasses (no additional methods):
//   CraftRecipeEvent.Pre  - fired before crafting (cancel here to prevent it)
//   CraftRecipeEvent.Post - fired after crafting
```

### Event Example

```java
public class CraftingSystem extends EntityEventSystem<EntityStore, CraftRecipeEvent.Pre> {

    public CraftingSystem() {
        super(CraftRecipeEvent.Pre.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       CraftRecipeEvent.Pre event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            CraftingRecipe recipe = event.getCraftedRecipe();
            MaterialQuantity output = recipe.getPrimaryOutput();

            // Check bench requirements
            for (BenchRequirement bench : recipe.getBenchRequirement()) {
                if (bench.type == BenchType.Processing) {
                    // Processing recipe
                }
            }

            // Optionally cancel
            // event.setCancelled(true);
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

## Common Patterns

### Recipe in Item Definition

Most items embed their recipe directly:

```json
{
  "Parent": "Template_Food",
  "Recipe": {
    "TimeSeconds": 5.0,
    "Input": [
      { "ItemId": "Ingredient_Flour", "Quantity": 3 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Food"],
      "Id": "Cooking_Campfire"
    }]
  }
}
```

### Recipe with Metadata Output

Benches can output items with pre-configured metadata:

```json
{
  "Output": [{
    "ItemId": "Bench_Furnace",
    "Metadata": {
      "BlockState": {
        "Type": "processingBench",
        "FuelContainer": { "Capacity": 2 }
      }
    }
  }]
}
```

### Multiple Bench Options

Allow crafting at different benches:

```json
{
  "BenchRequirement": [
    { "Type": "Crafting", "Id": "Fieldcraft", "Categories": ["Tools"] },
    { "Type": "Crafting", "Id": "Workbench", "Categories": ["Workbench_Survival"] }
  ]
}
```

---

## All Crafting Benches

| Bench | Type | Id | Categories |
|-------|------|----|-----------
| Bench_WorkBench | Crafting | `Workbench` | Survival, Tools, Crafting, Tinkering |
| Bench_Weapon | Crafting | `Weapon_Bench` | Sword, Mace, Battleaxe, Daggers, Bow |
| Bench_Armour | Crafting | `Armor_Bench` | Head, Chest, Hands, Legs, Shield |
| Bench_Alchemy | Crafting | `Alchemybench` | Potions, Misc Potions, Bombs |
| Bench_Cooking | Crafting | `Cookingbench` | Prepared, Baked, Ingredients |
| Bench_Furniture | Crafting | `Furniture_Bench` | Various furniture categories |
| Bench_Farming | Crafting | `Farming_Bench` | Farming items |
| Bench_Furnace | Processing | `Furnace` | Smelting with fuel |
| Bench_Campfire | Processing | `Campfire` | Basic cooking/smelting |
| Bench_Tannery | Processing | `Tannery` | Hide processing |
| Bench_Salvage | Processing | `Salvagebench` | Item deconstruction |
| Bench_Loom | Processing | `Loom` | Fabric processing |
| Bench_Armory | DiagramCrafting | `Armory` | Blueprint-based weapons/armor |
| Bench_Builders | StructuralCrafting | `Buildersbench` | Block variants |

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 crafting/recipe loaders (verified against `HytaleServer.jar`).

- **`KnowledgeRequired in recipe can't be set for non crafting recipes`** → `KnowledgeRequired: true` was set on a recipe whose bench `Type` is not `Crafting` (e.g. `Processing` or a salvage recipe). Fix: only set `KnowledgeRequired` on standard `Crafting` recipes; remove it from processing/salvage recipes.
- **`CraftingRecipe can't be null!`** → a recipe reference resolved to nothing — typically a recipe id or `Parent` that does not match a loaded recipe asset. Fix: confirm the recipe asset loaded and the referenced id matches exactly (case-sensitive).
- **Symptom:** a recipe loads but never appears at the bench → the `BenchRequirement` `Id`/`Categories` do not match the target bench's configured categories, or `RequiredTierLevel` exceeds the bench's tier. Fix: match `Id`/`Categories` to the bench (see [BenchRequirement](#benchrequirement)) and lower `RequiredTierLevel`.
- **Symptom:** a recipe declares no usable input or output and fails to register → `Input`/`Output` resolved empty (every `MaterialQuantity` must carry an `ItemId`, `ResourceTypeId`, or tag). Fix: give the recipe at least one valid input and a `PrimaryOutput`/`Output`.

---

## Related Documentation

- [Items Reference](items.md) - Common item properties
- [Inventory Reference](inventory.md) - Inventory management and crafting events
- [Consumables](items-consumables.md) - Food and potion items with recipes
- [Weapons](items-weapons.md) - Weapon items with recipes
- [Tools](items-tools.md) - Tool items

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
