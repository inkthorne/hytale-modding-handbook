# Tool Items

**Doc type:** JSON asset format · **Assets:** `Server/Item` · **Verified against build-12**

> Part of the [Items API](items.md). For common item properties, see [Items Reference](items.md#common-properties).

This page documents tool items — pickaxes, hatchets, shovels, and other gathering/utility tools — configured through the `Tool` property and a shared "Crude" base item per family.

## Overview

Defined as JSON assets under `Server/Item` and covers:
- The `Tool` property: `Specs` (power per gather type), `Speed`, and `DurabilityLossBlockTypes`
- `GatherType` categories and gather-quality levels that gate which blocks a tool breaks
- Material tiers and power scaling across tool variants
- Each tool family (pickaxe, hatchet, shovel, hoe, hammer, shears, watering can, sickle, repair kit, capture crate, feedbag, fertilizer) with its `Crude` base and child variants
- Tool interactions: `BreakBlock`, `ChangeBlock`, and durability handling
- The watering can's `State` system for fill/water

## Architecture
```
Tool item (inherits Tool_<Family>_Crude base)
├── Tool property
│   ├── Specs[] (Power + GatherType + optional Quality)
│   ├── Speed
│   └── DurabilityLossBlockTypes
├── Material tiers (power scaling)
├── Tool families
│   ├── Pickaxe / Hatchet / Shovel / Hoe / Hammer
│   ├── Shears / Watering Can / Sickle
│   └── Repair Kit / Capture Crate / Feedbag / Fertilizer
└── Interactions (BreakBlock, ChangeBlock, durability)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Tool` | item property | Tool config: specs, speed, durability rules |
| `Tool.Specs` | item property | Per-`GatherType` power (and optional quality) entries |
| `Tool_Pickaxe_Crude` | `Server/Item/Items/.../Tool_Pickaxe_Crude.json` | Crude base inherited by pickaxe variants |
| `Tool_Hatchet_Crude` | `Server/Item/Items/.../Tool_Hatchet_Crude.json` | Crude base for hatchets |
| `Tool_Shovel_Crude` | `Server/Item/Items/.../Tool_Shovel_Crude.json` | Crude base for shovels |
| `Tool_Watering_Can` | `Server/Item/Items/.../Tool_Watering_Can.json` | Watering can with fill/water `State` system |
| `BreakBlock` | tool interaction | Breaks/harvests the targeted block |
| `ChangeBlock` | tool interaction | Cycles/converts a block (e.g. hammer, hoe) |

## Quick Navigation

| Tool Type | Children | Primary Use | Description |
|-----------|----------|-------------|-------------|
| [Pickaxe](#pickaxe) | 10 | Rocks/Ores | Mining stone and ore blocks |
| [Hatchet](#hatchet) | 10 | Woods | Chopping wood and trees |
| [Shovel](#shovel) | 5 | Soils | Digging soil and dirt |
| [Hoe](#hoe) | 3 | Tilling | Converting soil for farming |
| [Hammer](#hammer) | 2 | Block Cycling | Rotating block variants |
| [Shears](#shears) | 1 | Shearing | Collecting wool from animals |
| [Watering Can](#watering-can) | 1 | Watering | Irrigating crops |
| [Sickle](#sickle) | 2 | Harvesting | Cutting plants and crops |
| [Repair Kit](#repair-kit) | 3 | Repair | Restoring item durability |
| [Capture Crate](#capture-crate) | 1 | Capture | Capturing animals |
| [Feedbag](#feedbag) | 1 | Feeding | Feeding animals |
| [Fertilizer](#fertilizer) | 1 | Growing | Accelerating plant growth |

---

## Tool Property

Unlike weapons which use formal Templates with signature abilities, tools inherit from a "Crude" base item (e.g., `Tool_Pickaxe_Crude`) and use the `Tool` property to configure block-breaking behavior.

### Tool.Specs

Defines power and efficiency for different block types. Each tool lists a spec for every gather type it can affect; this example is taken from `Tool_Pickaxe_Iron`:

```json
{
  "Tool": {
    "Specs": [
      { "Power": 1, "GatherType": "SoftBlocks" },
      { "Power": 0.5, "GatherType": "Soils" },
      { "Power": 0.05, "GatherType": "Woods" },
      { "Power": 0.5, "GatherType": "Rocks", "Quality": 3 },
      { "Power": 0.5, "GatherType": "Benches" },
      { "Power": 0.17, "GatherType": "VolcanicRocks" },
      { "Power": 0.5, "GatherType": "OreCopper" },
      { "Power": 0.25, "GatherType": "OreIron" }
    ]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Power` | float | Breaking speed multiplier (higher = faster) |
| `GatherType` | string | Block category this spec applies to |
| `Quality` | int | Optional gather-quality level for this spec (controls which blocks the tool can break, e.g. higher-tier ore) |
| `HitSoundLayer` | string | Optional impact sound override (a `SFX_*` event id) |

### GatherTypes

| GatherType | Primary Tool | Description |
|------------|--------------|-------------|
| `SoftBlocks` | All tools (1.0) | Soft blocks like grass, leaves |
| `Soils` | Shovel | Dirt, sand, gravel |
| `Woods` | Hatchet | Wood blocks, tree trunks |
| `Rocks` | Pickaxe | Stone, rock formations |
| `VolcanicRocks` | Pickaxe (low power) | Volcanic stone, obsidian |
| `Benches` | Most tools | Crafting stations, furniture |

Ore deposits use granular per-metal gather types (there is no single `Ores` gather type in tool specs):

| GatherType | Metal |
|------------|-------|
| `OreCopper` | Copper |
| `OreIron` | Iron |
| `OreSilver` | Silver |
| `OreGold` | Gold |
| `OreThorium` | Thorium |
| `OreCobalt` | Cobalt |
| `OreAdamantite` | Adamantite |
| `OreMithril` | Mithril |

### Tool.DurabilityLossBlockTypes

Configures durability loss per block set. This example is taken from `Tool_Pickaxe_Iron`:

```json
{
  "Tool": {
    "DurabilityLossBlockTypes": [
      {
        "BlockSets": ["Stone", "Rock", "Ores", "Soil", "Wood"],
        "DurabilityLossOnHit": 0.25
      }
    ]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `BlockSets` | array | Block sets this rule applies to |
| `DurabilityLossOnHit` | float | Durability points lost per hit on these blocks |

### Tool.Speed

Optional speed multiplier for tool animations:

```json
{
  "Tool": {
    "Speed": 1.2
  }
}
```

---

## Material Tiers

Tools follow a consistent material progression:

| Tier | Quality | ItemLevel | Durability | Power Range |
|------|---------|-----------|------------|-------------|
| Crude/Wood | Common | 3-10 | 100-150 | 1.0-1.5 |
| Copper | Common | 10 | ~150 | 2.0-2.5 |
| Iron | Uncommon | 20 | 250 | 3.0-3.5 |
| Cobalt | Rare | 30 | 300 | 4.0-4.5 |
| Mithril | Rare | 35 | 325 | 4.5-5.0 |
| Adamantite | Rare | 40 | 400 | 5.0-6.0 |

---

## Pickaxe

**Location:** `Server/Item/Items/Tool/Pickaxe/`

Mining tool optimized for rocks, stone, and ore extraction.

### Base Properties (Tool_Pickaxe_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 5 |
| `PlayerAnimationsId` | Pickaxe |
| `MaxDurability` | 150 |
| `Categories` | Items.Tools |

### Tool.Specs (Tool_Pickaxe_Crude)

| GatherType | Power | Description |
|------------|-------|-------------|
| `SoftBlocks` | 1 | General soft blocks |
| `Soils` | 0.35 | Dirt, sand |
| `Woods` | 0.05 | Wood (very inefficient) |
| `Rocks` | 0.25 | Primary use - stone blocks (`Quality: 1`) |
| `Benches` | 0.5 | Crafting stations |
| `VolcanicRocks` | 0.084 | Volcanic/obsidian (reduced) |
| `OreCopper` | 0.125 | Copper ore |
| `OreIron` | 0.084 | Iron ore |

(Crude also defines low-power specs for `OreSilver`, `OreGold`, `OreThorium`, `OreCobalt`, `OreAdamantite`, and `OreMithril`.)

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Primary` | Pickaxe_Attack | Block breaking swing |

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### Example Child: Iron Pickaxe

```json
{
  "Parent": "Tool_Pickaxe_Crude",
  "TranslationProperties": {
    "Name": "server.items.Tool_Pickaxe_Iron.name",
    "Description": "server.items.Tool_Pickaxe_Crude.description"
  },
  "Icon": "Icons/ItemsGenerated/Tool_Pickaxe_Iron.png",
  "Quality": "Uncommon",
  "ItemLevel": 20,
  "Model": "Items/Tools/Pickaxe/Iron.blockymodel",
  "Texture": "Items/Tools/Pickaxe/Iron_Texture.png",
  "Recipe": {
    "TimeSeconds": 3.5,
    "Input": [
      { "ItemId": "Ingredient_Bar_Iron", "Quantity": 5 },
      { "ItemId": "Ingredient_Leather_Light", "Quantity": 2 },
      { "ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": 2 }
    ],
    "BenchRequirement": [{
      "Id": "Workbench",
      "Type": "Crafting",
      "Categories": ["Workbench_Tools"]
    }]
  },
  "Tool": {
    "Specs": [
      { "Power": 1, "GatherType": "SoftBlocks" },
      { "Power": 0.5, "GatherType": "Soils" },
      { "Power": 0.05, "GatherType": "Woods" },
      { "Power": 0.5, "GatherType": "Rocks", "Quality": 3 },
      { "Power": 0.5, "GatherType": "Benches" },
      { "Power": 0.17, "GatherType": "VolcanicRocks" },
      { "Power": 0.5, "GatherType": "OreCopper" },
      { "Power": 0.25, "GatherType": "OreIron" },
      { "Power": 0.25, "GatherType": "OreSilver" },
      { "Power": 0.25, "GatherType": "OreGold" },
      { "Power": 0.125, "GatherType": "OreThorium" },
      { "Power": 0.125, "GatherType": "OreCobalt" },
      { "Power": 0.084, "GatherType": "OreAdamantite" },
      { "Power": 0.063, "GatherType": "OreMithril" }
    ],
    "DurabilityLossBlockTypes": [
      {
        "BlockSets": ["Stone", "Rock", "Ores", "Soil", "Wood"],
        "DurabilityLossOnHit": 0.25
      }
    ]
  },
  "MaxDurability": 250
}
```

### Power Scaling by Tier

Verified `Crude` and `Iron` values from the real asset files; intermediate tiers are illustrative.

| Pickaxe | Quality | ItemLevel | Rocks (Power / Quality) | VolcanicRocks | Durability |
|---------|---------|-----------|-------------------------|---------------|------------|
| Crude | Common | 5 | 0.25 / 1 | 0.084 | 150 |
| Iron | Uncommon | 20 | 0.5 / 3 | 0.17 | 250 |

Higher-tier pickaxes raise the `Rocks` spec `Quality` (gating which ore tiers are mineable) and increase individual `Ore*` powers rather than scaling a single number.

### All Pickaxe Variants

Tool_Pickaxe_Crude, Tool_Pickaxe_Copper, Tool_Pickaxe_Iron, Tool_Pickaxe_Cobalt, Tool_Pickaxe_Mithril, Tool_Pickaxe_Adamantite, Tool_Pickaxe_Bone, Tool_Pickaxe_Stone, Tool_Pickaxe_Bronze, Tool_Pickaxe_Steel

---

## Hatchet

**Location:** `Server/Item/Items/Tool/Hatchet/`

Woodcutting tool optimized for trees and wood blocks.

### Base Properties (Tool_Hatchet_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 4 |
| `PlayerAnimationsId` | Hatchet |
| `MaxDurability` | 150 |
| `Categories` | Items.Tools |

### Tool.Specs (Tool_Hatchet_Crude)

| GatherType | Power | Description |
|------------|-------|-------------|
| `SoftBlocks` | 1 | General soft blocks |
| `Soils` | 0.05 | Dirt, sand (very inefficient) |
| `Woods` | 0.15 | Primary use - wood blocks |
| `Rocks` | 0.05 | Stone (very inefficient) |
| `Benches` | 0.5 | Crafting stations |
| `VolcanicRocks` | 0.017 | Volcanic/obsidian |
| `OreCopper` | 0.036 | Copper ore |

(Crude also defines low-power specs for `OreIron`, `OreSilver`, `OreGold`, `OreThorium`, `OreCobalt`, `OreAdamantite`, and `OreMithril`.)

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Primary` | Hatchet_Attack | Block breaking swing |

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### Example Child: Iron Hatchet

The `Woods` and `Benches` specs carry an optional `HitSoundLayer` impact-sound override (taken from the real `Tool_Hatchet_Iron`):

```json
{
  "Parent": "Tool_Hatchet_Crude",
  "TranslationProperties": {
    "Name": "server.items.Tool_Hatchet_Iron.name"
  },
  "Model": "Items/Tools/Hatchet/Iron.blockymodel",
  "Texture": "Items/Tools/Hatchet/Iron_Texture.png",
  "Icon": "Icons/ItemsGenerated/Tool_Hatchet_Iron.png",
  "Quality": "Uncommon",
  "ItemLevel": 20,
  "MaxDurability": 250,
  "Tool": {
    "Specs": [
      { "Power": 1, "GatherType": "SoftBlocks" },
      { "Power": 0.05, "GatherType": "Soils" },
      { "Power": 0.3, "GatherType": "Woods", "HitSoundLayer": "SFX_Hatchet_T2_Impact_Nice" },
      { "Power": 0.05, "GatherType": "Rocks" },
      { "Power": 0.5, "GatherType": "Benches", "HitSoundLayer": "SFX_Hatchet_T2_Impact_Nice" },
      { "Power": 0.017, "GatherType": "VolcanicRocks" }
    ]
  },
  "Recipe": {
    "TimeSeconds": 3.5,
    "Input": [
      { "ItemId": "Ingredient_Bar_Iron", "Quantity": 5 },
      { "ItemId": "Ingredient_Leather_Light", "Quantity": 2 },
      { "ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": 2 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Workbench_Tools"],
      "Id": "Workbench"
    }]
  }
}
```

### Power Scaling by Tier

Verified `Crude` and `Iron` `Woods` values from the real asset files; higher tiers raise the `Woods` power and add `HitSoundLayer` overrides.

| Hatchet | Quality | ItemLevel | Woods | Durability |
|---------|---------|-----------|-------|------------|
| Crude | Common | 4 | 0.15 | 150 |
| Iron | Uncommon | 20 | 0.3 | 250 |

### All Hatchet Variants

Tool_Hatchet_Crude, Tool_Hatchet_Copper, Tool_Hatchet_Iron, Tool_Hatchet_Cobalt, Tool_Hatchet_Mithril, Tool_Hatchet_Adamantite, Tool_Hatchet_Bone, Tool_Hatchet_Stone, Tool_Hatchet_Bronze, Tool_Hatchet_Steel

---

## Shovel

**Location:** `Server/Item/Items/Tool/Shovel/`

Digging tool optimized for soil, sand, and dirt blocks.

### Base Properties (Tool_Shovel_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 3 |
| `PlayerAnimationsId` | Shovel |
| `MaxDurability` | 150 |
| `Categories` | Items.Tools |

### Tool.Specs (Tool_Shovel_Crude)

| GatherType | Power | Description |
|------------|-------|-------------|
| `Soils` | 0.4 | Primary use - dirt, sand |

(Crude also defines a `SoftBlocks` spec plus low-power specs for the various `Ore*` types.)

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Primary` | Shovel_Attack | Block breaking dig |

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### Power Scaling by Tier

Verified `Crude` and `Iron` `Soils` values from the real asset files. The Iron `Soils` spec also adds `"HitSoundLayer": "SFX_Shovel_T2_Impact_Nice"`.

| Shovel | Quality | ItemLevel | Soils | Durability |
|--------|---------|-----------|-------|------------|
| Crude | Common | 3 | 0.4 | 150 |
| Iron | Uncommon | 20 | 0.5 | 250 |

### All Shovel Variants

Tool_Shovel_Crude, Tool_Shovel_Copper, Tool_Shovel_Iron, Tool_Shovel_Cobalt, Tool_Shovel_Thorium

---

## Hoe

**Location:** `Server/Item/Items/Tool/Hoe/`

Farming tool that converts soil blocks for planting.

### Base Properties (Tool_Hoe_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 1 |
| `PlayerAnimationsId` | Hoe |
| `MaxDurability` | 100 |
| `Categories` | Items.Tools |

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Primary` | Hoe_Attack | Melee swing |
| `Secondary` | Hoe_Till | Till soil block |

The `Hoe_Till` interaction uses `ChangeBlock`, whose `Changes` is a map of source block to result block (excerpt from the real `Hoe_Till` interaction):

```json
{
  "Type": "ChangeBlock",
  "RunTime": 0.233,
  "RequireNotBroken": true,
  "Changes": {
    "Soil_Dirt": "Soil_Dirt_Tilled",
    "Soil_Grass": "Soil_Dirt_Tilled",
    "Soil_Mud": "Soil_Dirt_Tilled"
  },
  "WorldSoundEventId": "SFX_Hoe_T1_Till",
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1
  }
}
```

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### All Hoe Variants

Tool_Hoe_Crude, Tool_Hoe_Copper, Tool_Hoe_Iron, Tool_Hoe_Thorium

---

## Hammer

**Location:** `Server/Item/Items/Tool/Hammer/`

Utility tool for cycling through block variants and rotations.

### Base Properties (Tool_Hammer_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 10 |
| `PlayerAnimationsId` | Hammer |
| `MaxDurability` | 200 |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_Hammer_Primary | Cycle block variant |

Uses `CycleBlockGroup` interaction:

```json
{
  "Type": "CycleBlockGroup",
  "BlockSelectorTool": true,
  "DurabilityLossOnUse": 0.5
}
```

The `BlockSelectorTool` property enables special block selection UI.

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["Hammer"]
  }
}
```

### All Hammer Variants

Tool_Hammer_Crude, Tool_Hammer_Iron

---

## Shears

**Location:** `Server/Item/Items/Tool/Shears/`

Tool for shearing wool from animals.

### Base Properties (Tool_Shears)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 10 |
| `PlayerAnimationsId` | Shears |
| `MaxDurability` | 100 |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_Shears_Primary | Shear animal |

Uses `ContextualUseNPC` interaction with "Shear" context:

```json
{
  "Type": "ContextualUseNPC",
  "Context": "Shear",
  "Range": 3.0,
  "DurabilityLossOnUse": 1.0
}
```

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["Shears"]
  }
}
```

### All Shears Variants

Tool_Shears

---

## Watering Can

**Location:** `Server/Item/Items/Tool/Watering_Can/`

Farming tool for irrigating crops. A single item (`Tool_Watering_Can`) uses the `State` system to switch between its empty and filled appearances rather than being two separate items.

### Base Properties (Tool_Watering_Can)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 10 |
| `PlayerAnimationsId` | Watering_Can |
| `Scale` | 2 |
| `Parent` | Template_Tool_Watering_Can |

### State System

A `State` block defines the filled variant. The empty model is the item's base `Model`; the `Filled_Water` state swaps in the filled model, durability, and a watering interaction (excerpt from the real `Tool_Watering_Can`):

```json
{
  "State": {
    "Filled_Water": {
      "Variant": true,
      "Model": "Items/Tools/Watering_Can/Watering_Can.blockymodel",
      "PlayerAnimationsId": "Watering_Can",
      "Interactions": {
        "Secondary": "Watering_Can_Filled_Use"
      },
      "MaxDurability": 50,
      "DurabilityLossOnDeath": false
    }
  }
}
```

### Fill and Water Interactions

Filling uses the `RefillContainer` interaction type, gated by the source fluid (from the real `Watering_Can_Fill` interaction):

```json
{
  "Type": "RefillContainer",
  "States": {
    "Filled_Water": {
      "AllowedFluids": ["Water_Source", "Water"]
    }
  },
  "Next": {
    "Type": "Simple",
    "Effects": {
      "ItemAnimationId": "Water",
      "WorldSoundEventId": "SFX_Water_MoveIn"
    },
    "RunTime": 0.5
  }
}
```

Watering crops uses the `UseWateringCan` interaction type (from the real `Watering_Can_Use` interaction):

```json
{
  "Type": "UseWateringCan",
  "UseLatestTarget": true,
  "RadiusX": 1,
  "RadiusZ": 1,
  "RefreshModifiers": ["Water"],
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1,
    "BrokenItem": "Tool_Watering_Can"
  },
  "Failed": "Watering_Can_No_Effect"
}
```

### Recipe

Crafted at the `Farmingbench` (category `Farming`):

```json
{
  "Recipe": {
    "TimeSeconds": 1,
    "Input": [
      { "ItemId": "Ingredient_Bar_Iron", "Quantity": 3 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Farming"],
      "Id": "Farmingbench"
    }]
  }
}
```

### All Watering Can Variants

Tool_Watering_Can (with `Template_Tool_Watering_Can` as its parent template)

---

## Sickle

**Location:** `Server/Item/Items/Tool/Sickle/`

Harvesting tool for cutting plants and crops efficiently.

### Base Properties (Tool_Sickle_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 5 |
| `PlayerAnimationsId` | Sickle |
| `MaxDurability` | 100 |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_Sickle_Primary | Harvest plants |

Optimized for harvesting plant blocks with area effect.

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["Sickle"]
  }
}
```

### All Sickle Variants

Tool_Sickle_Crude, Tool_Sickle_Iron

---

## Repair Kit

**Location:** `Server/Item/Items/Tool/RepairKit/`

Utility item that opens a repair UI to restore item durability.

### Base Properties (Tool_RepairKit_Basic)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 10 |
| `MaxStack` | 1 |
| `Consumable` | false |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_RepairKit_Open | Open repair UI |

Uses `OpenCustomUI` interaction:

```json
{
  "Type": "OpenCustomUI",
  "PageId": "ItemRepair",
  "RepairPenalty": 0.1
}
```

| Property | Type | Description |
|----------|------|-------------|
| `PageId` | string | UI page to open |
| `RepairPenalty` | float | Max durability reduction per repair (10%) |

### Repair Kit Tiers

| Repair Kit | Quality | RepairPenalty | Description |
|------------|---------|---------------|-------------|
| Basic | Common | 0.10 | 10% max durability loss |
| Advanced | Uncommon | 0.05 | 5% max durability loss |
| Master | Rare | 0.02 | 2% max durability loss |

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["RepairKit"]
  }
}
```

### All Repair Kit Variants

Tool_RepairKit_Basic, Tool_RepairKit_Advanced, Tool_RepairKit_Master

---

## Capture Crate

**Location:** `Server/Item/Items/Tool/CaptureCrate/`

Utility item for capturing and transporting animals.

### Base Properties (Tool_CaptureCrate)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 15 |
| `MaxStack` | 1 |
| `Consumable` | true |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_CaptureCrate_Use | Capture animal |

Uses `UseCaptureCrate` interaction:

```json
{
  "Type": "UseCaptureCrate",
  "Range": 3.0,
  "AcceptedNpcGroups": ["Livestock", "Pets", "SmallAnimals"],
  "CapturedItem": "Tool_CaptureCrate_Filled"
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AcceptedNpcGroups` | array | NPC groups that can be captured |
| `CapturedItem` | string | Item created with captured entity |
| `Range` | float | Maximum capture distance |

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["CaptureCrate"]
  }
}
```

### All Capture Crate Variants

Tool_CaptureCrate, Tool_CaptureCrate_Filled

---

## Feedbag

**Location:** `Server/Item/Items/Tool/Feedbag/`

Farming tool for feeding animals.

### Base Properties (Tool_Feedbag)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 5 |
| `MaxStack` | 1 |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_Feedbag_Use | Feed animal |

Uses `ContextualUseNPC` interaction with "Feed" context.

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["Feedbag"]
  }
}
```

### All Feedbag Variants

Tool_Feedbag

---

## Fertilizer

**Location:** `Server/Item/Items/Tool/Fertilizer/`

Farming consumable that accelerates plant growth.

### Base Properties (Tool_Fertilizer)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 5 |
| `MaxStack` | 25 |
| `Consumable` | true |
| `Categories` | Items.Tools |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Tool_Fertilizer_Use | Apply to crop |

Uses block interaction to advance plant growth stage.

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"],
    "Family": ["Fertilizer"]
  }
}
```

### All Fertilizer Variants

Tool_Fertilizer

---

## Common Tool Patterns

### BreakBlock Interaction

Block-breaking tools point their `Primary` slot at a `*_Attack` interaction (e.g. `Pickaxe_Attack`) whose chain falls through to a `BreakBlock` step. Which blocks a tool can break, and how fast, is driven by the item's `Tool.Specs` gather types — there is no `Tool` field on the `BreakBlock` interaction itself. This excerpt is from the real `Block_Break` interaction:

```json
{
  "Type": "UseBlock",
  "Failed": {
    "Type": "BreakBlock",
    "UseLatestTarget": true
  }
}
```

### ChangeBlock Interaction

Used by hoes to transform blocks. `Changes` is a map of source block to result block:

```json
{
  "Type": "ChangeBlock",
  "Changes": {
    "Soil_Grass": "Soil_Dirt_Tilled",
    "Soil_Dirt": "Soil_Dirt_Tilled"
  },
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1
  }
}
```

### Tool Durability

Tools lose durability based on the block set hit, via `DurabilityLossBlockTypes` (excerpt from the real `Tool_Pickaxe_Iron`):

```json
{
  "Tool": {
    "DurabilityLossBlockTypes": [
      {
        "BlockSets": ["Stone", "Rock", "Ores", "Soil", "Wood"],
        "DurabilityLossOnHit": 0.25
      }
    ]
  }
}
```

A separate top-level `DurabilityLossOnHit` (a common item property) provides the default per-hit loss when a block is not covered by `DurabilityLossBlockTypes`.

---

## Sound Sets

| Tool Family | ItemSoundSetId |
|-------------|----------------|
| Pickaxe | ISS_Tool_Pickaxe |
| Hatchet | ISS_Tool_Hatchet |
| Shovel | ISS_Tool_Shovel |
| Hoe | ISS_Tool_Hoe |
| Hammer | ISS_Tool_Hammer |
| Shears | ISS_Tool_Shears |

---

## Related Documentation

- [Items Reference](items.md) - Common properties and systems
- [Interactions API](interactions.md) - Tool interactions
- [Block Interactions](interactions-block.md) - BreakBlock, ChangeBlock, PlaceBlock
- [Weapons Reference](items-weapons.md) - Combat items
