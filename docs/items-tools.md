---
title: "Tool Items"
description: "Define Hytale tools in JSON — the Tool property (Specs power per gather type, Speed, durability loss), GatherType categories and quality gating, and material tiers with power scaling."
seo:
  type: TechArticle
---

# Tool Items

**Doc type:** JSON asset format · **Assets:** `Server/Item` · **Verified against 0.5.9**

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

| Tool Type | Files | Primary Use | Description |
|-----------|-------|-------------|-------------|
| [Pickaxe](#pickaxe) | 10 | Rocks/Ores | Mining stone and ore blocks |
| [Hatchet](#hatchet) | 10 | Woods | Chopping wood and trees |
| [Shovel](#shovel) | 5 | Soils | Digging soil and dirt |
| [Hoe](#hoe) | 4 | Tilling | Converting soil for farming |
| [Hammer](#hammer) | 2 | Block Cycling | Rotating block variants |
| [Shears](#shears) | 1 | Shearing | Collecting wool from animals |
| [Watering Can](#watering-can) | 2 | Watering | Irrigating crops (template + item) |
| [Sickle](#sickle) | 4 | Harvesting | Cutting plants and crops |
| [Repair Kit](#repair-kit) | 3 | Repair | Restoring item durability |
| [Capture Crate](#capture-crate) | 1 | Capture | Capturing animals |
| [Feedbag](#feedbag) | 1 | Feeding | Attracting livestock |
| [Fertilizer](#fertilizer) | 2 | Growing | Accelerating plant growth |

("Files" = JSON files in the family's folder as of 0.6.3, excluding the `Pickaxe/_Debug/` break-shape
test items. `Server/Item/Items/Tool/` also holds a few loose tools outside these families —
`Tool_Fishing_Trap`, `Tool_Trap_Bait`, `Tool_Growth_Potion`, `Tool_Sap_Shunt`, `Tool_Map` — and a
`Prototype/` folder.)

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
| `IsIncorrect` | bool | Optional; marks the spec as the "wrong tool" entry for this gather type |
| `HitSoundLayer` | string | Optional impact sound override (a `SFX_*` event id), played in addition to the block's own break sound |

(Codec: `com.hypixel.hytale.server.core.asset.type.item.config.ItemToolSpec`; the `Tool` block itself is `ItemTool`.)

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

Optional speed multiplier (a double). Rarely set by stock assets — `Tool_Shears_Basic` is one that does:

```json
{
  "Tool": {
    "Speed": 1.0
  }
}
```

### Other Tool Keys

The full `Tool` (`ItemTool`) codec, as of 0.6.3:

| Key | Type | Description |
|-----|------|-------------|
| `Specs` | array | Per-gather-type power entries (above) |
| `Speed` | double | Speed multiplier |
| `DurabilityLossBlockTypes` | array | Per-block-set durability loss (above) |
| `HitSoundLayer` | string | Sound played in addition to the block-break sound when hitting a block this tool is designed to break (tool-wide default; a spec's own `HitSoundLayer` is per gather type) |
| `IncorrectMaterialSoundLayer` | string | Sound played in addition to the block-break sound when hitting a block this tool *cannot* break |
| `BreakShape` | object | Optional multi-block break shape (0.6.3+): when set, a swing affects every block the shape covers, oriented to the user's view, instead of only the targeted block. Keys: `Id` (e.g. `Box`), `Width`, `Height`, `Depth`, `Centered`, `Offset`, `Orientation` (e.g. `View`) — codec `com.hypixel.hytale.server.core.modules.interaction.breakshape.BreakShape` |
| `BreakShapeDurabilityMode` | enum | How durability is consumed when a break shape hits several blocks: `PerSwing` (once per swing) or `PerBlock` (once per block broken) — `com.hypixel.hytale.server.core.asset.type.item.config.BreakShapeDurabilityMode` |

`BreakShape` is only used by the two debug items under `Tool/Pickaxe/_Debug/` in stock 0.6.3 assets (excerpt from `Debug_Pickaxe_Shaped.json`, which inherits `Tool_Pickaxe_Adamantite`):

```json
{
  "Tool": {
    "BreakShape": {
      "Id": "Box",
      "Orientation": "View",
      "Width": 3,
      "Height": 3,
      "Depth": 1
    },
    "BreakShapeDurabilityMode": "PerSwing"
  }
}
```

---

## Material Tiers

Pickaxes and hatchets share one material progression (values read from the 0.6.3 `Tool_Pickaxe_*` /
`Tool_Hatchet_*` files; "inherits" means the variant doesn't set the key and takes the Crude base's
value). Breaking power is per gather type, never a single number — see each family's scaling table.

| Tier | Quality | ItemLevel (Pickaxe / Hatchet) | MaxDurability |
|------|---------|-------------------------------|---------------|
| Wood | Common | inherits (5 / 4) | inherits (150) |
| Crude | Common | 5 / 4 | 150 |
| Scrap (pickaxe only) | Uncommon | inherits (5) | 60 |
| Copper | Common | 12 / 11 | 200 |
| Iron | Uncommon | 20 / 20 | 250 |
| Thorium | Rare | 30 / 30 | 325 |
| Cobalt | Rare | 35 / 35 | 325 |
| Adamantite | Rare | 40 / 40 | 400 |
| Mithril | Epic | 50 / 50 | 400 |
| Onyxium | Epic | inherits (5 / 4) | 450 |

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

`Rocks` spec values from every 0.6.3 `Tool_Pickaxe_*` file ("inherits" = not set by the variant, so the Crude value applies):

| Pickaxe | Quality | ItemLevel | Rocks (Power / Quality) | Durability |
|---------|---------|-----------|-------------------------|------------|
| Wood | Common | inherits (5) | 0.1 / 1 | inherits (150) |
| Crude | Common | 5 | 0.25 / 1 | 150 |
| Scrap | Uncommon | inherits (5) | 0.1 / 1 | 60 |
| Copper | Common | 12 | 0.35 / 2 | 200 |
| Iron | Uncommon | 20 | 0.5 / 3 | 250 |
| Thorium | Rare | 30 | 0.5 / 4 | 325 |
| Cobalt | Rare | 35 | 0.5 / 4 | 325 |
| Adamantite | Rare | 40 | 1 / 5 | 400 |
| Mithril | Epic | 50 | 1.0 / 6 | 400 |
| Onyxium | Epic | inherits (5) | 1 / 6 | 450 |

Higher-tier pickaxes raise the `Rocks` spec `Quality` (gating which ore tiers are mineable) and increase individual `Ore*` powers rather than scaling a single number (Iron's `VolcanicRocks` is 0.17 vs Crude's 0.084, for example).

### All Pickaxe Variants

Tool_Pickaxe_Crude, Tool_Pickaxe_Wood, Tool_Pickaxe_Scrap, Tool_Pickaxe_Copper, Tool_Pickaxe_Iron, Tool_Pickaxe_Thorium, Tool_Pickaxe_Cobalt, Tool_Pickaxe_Adamantite, Tool_Pickaxe_Mithril, Tool_Pickaxe_Onyxium (plus `_Debug/Debug_Pickaxe_Shaped` and `_Debug/Debug_Pickaxe_Shaped_Cylinder`, the `BreakShape` test items)

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

`Woods` spec power from every 0.6.3 `Tool_Hatchet_*` file; higher tiers raise the `Woods` power (it plateaus at 0.5 from Thorium up) and add `HitSoundLayer` overrides.

| Hatchet | Quality | ItemLevel | Woods | Durability |
|---------|---------|-----------|-------|------------|
| Wood | Common | inherits (4) | 0.2 | inherits (150) |
| Crude | Common | 4 | 0.15 | 150 |
| Copper | Common | 11 | 0.2 | 200 |
| Iron | Uncommon | 20 | 0.3 | 250 |
| Thorium | Rare | 30 | 0.5 | 325 |
| Cobalt | Rare | 35 | 0.5 | 325 |
| Adamantite | Rare | 40 | 0.5 | 400 |
| Mithril | Epic | 50 | 0.5 | 400 |
| Onyxium | Epic | inherits (4) | 0.5 | 450 |

### All Hatchet Variants

Tool_Hatchet_Crude, Tool_Hatchet_Wood, Tool_Hatchet_Copper, Tool_Hatchet_Iron, Tool_Hatchet_Thorium, Tool_Hatchet_Cobalt, Tool_Hatchet_Adamantite, Tool_Hatchet_Mithril, Tool_Hatchet_Onyxium. The folder also holds `Tool_Bark_Scraper`, a non-hatchet utility tool.

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

(Crude also defines `SoftBlocks` (1), `Woods` (0.05), `Rocks` (0.05), `Benches` (0.5), `VolcanicRocks` (0.017) and low-power specs for the various `Ore*` types. Its `DurabilityLossOnHit` for the standard block sets is 0.05, not the pickaxe/hatchet 0.25.)

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Primary` | Shovel_Attack | Block breaking dig |

(`Tool_Shovel_Crude` writes the slot in the long form `"Primary": { "Interactions": ["Shovel_Attack"] }` rather than the bare-string form the pickaxe and hatchet use — both are accepted.)

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
| Copper | Common | inherits (3) | 0.2 | 200 |
| Iron | Uncommon | 20 | 0.5 | 250 |
| Cobalt | Rare | inherits (3) | 0.5 | 300 |
| Thorium | Rare | inherits (3) | 0.5 | 350 |

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

The `Hoe_Till` root interaction (`RootInteractions/Weapons/Hoe/Attacks/Till/Hoe_Till.json`, a 0.233s
`BlockInteraction` cooldown per game mode) wraps the `Hoe_Till` interaction, which uses `ChangeBlock`.
Its `Changes` is a map of source block to result block — 16 entries as of 0.6.3, covering the dirt,
grass, mud, leaves, needles and pathway soil variants (abridged excerpt):

```json
{
  "Type": "ChangeBlock",
  "RunTime": 0.233,
  "RequireNotBroken": true,
  "Changes": {
    "Soil_Dirt": "Soil_Dirt_Tilled",
    "Soil_Dirt_Dry": "Soil_Dirt_Tilled",
    "Soil_Grass": "Soil_Dirt_Tilled",
    "Soil_Grass_Full": "Soil_Dirt_Tilled",
    "Soil_Mud": "Soil_Dirt_Tilled",
    "Soil_Pathway": "Soil_Dirt_Tilled"
  },
  "WorldSoundEventId": "SFX_Hoe_T1_Till",
  "Effects": {
    "ItemAnimationId": "Till",
    "WorldSoundEventId": "SFX_Tool_T1_Swing",
    "LocalSoundEventId": "SFX_Hoe_T1_Swing_Down_Local"
  },
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1,
    "NotifyOnBreak": true,
    "NotifyOnBreakMessage": "server.general.repair.itemBroken_Hoe"
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
| `ItemLevel` | 2 |
| `PlayerAnimationsId` | Pickaxe (the hammer reuses the pickaxe rig) |
| `MaxDurability` | 100 |
| `MaxStack` | 1 |
| `Categories` | Items.Tools |

### Interactions

The hammer has no root interaction; both `Primary` and `Secondary` are the same inline
`CycleBlockGroup` interaction (from `Tool_Hammer_Crude`):

```json
{
  "Interactions": {
    "Primary": {
      "Interactions": [
        {
          "Type": "CycleBlockGroup",
          "RunTime": 0.1,
          "Effects": { "ItemAnimationId": "Mine" }
        }
      ]
    },
    "Secondary": {
      "Interactions": [
        {
          "Type": "CycleBlockGroup",
          "RunTime": 0.1,
          "Effects": { "ItemAnimationId": "Mine" }
        }
      ]
    }
  }
}
```

`CycleBlockGroup` (`CycleBlockGroupInteraction`, a `SimpleBlockInteraction`) attempts to cycle the target
block through its block set; it adds no keys of its own. The block-selector behaviour is a separate
**top-level item property**, not an interaction key:

```json
{
  "BlockSelectorTool": {
    "DurabilityLossOnUse": 1.0
  }
}
```

(`BlockSelectorToolData`; `DurabilityLossOnUse` is its only key.)

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### All Hammer Variants

Tool_Hammer_Crude, Tool_Hammer_Iron (Uncommon, `ItemLevel` 20, `MaxDurability` 500)

---

## Shears

**Location:** `Server/Item/Items/Tool/Shears/`

Tool for shearing wool from animals.

The single shears item is `Tool_Shears_Basic` (`Shears/Tool_Shears_Basic.json`).

### Base Properties (Tool_Shears_Basic)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `ItemLevel` | 16 |
| `PlayerAnimationsId` | Shears |
| `Set` | Tool_Iron |
| `Tool` | `Specs: [{ Power 1.0, SoftBlocks }]`, `Speed: 1.0` |
| `Categories` | Items.Tools |

(No `MaxDurability` is set.)

### Interactions

Both `Primary` and `Secondary` are the same inline `ContextualUseNPC` interaction with the `Shear` context,
behind a shared 0.2s `Shearing` cooldown; if there is no shearable NPC in front of the player it falls
back to `Shears_Attack` (a `Chaining` → `Shears_Snip` → `Shears_Block_Break` chain that cuts blocks
instead). From `Tool_Shears_Basic`:

```json
{
  "Primary": {
    "Cooldown": { "Id": "Shearing", "Cooldown": 0.2 },
    "Interactions": [
      {
        "Type": "ContextualUseNPC",
        "Context": "Shear",
        "Effects": {
          "ItemAnimationId": "Shear",
          "WaitForAnimationToFinish": true,
          "WorldSoundEventId": "SFX_Shears_Activate"
        },
        "Failed": "Shears_Attack"
      }
    ]
  }
}
```

`ContextualUseNPC` (`com.hypixel.hytale.server.npc.interactions.ContextualUseNPCInteraction`) has a single
key of its own, `Context`; there is no `Range` or `DurabilityLossOnUse` on it. Which NPCs respond is
decided on the NPC side — the tamed livestock roles (`Tamed_Sheep`, `Tamed_Chicken`, `Tamed_Skrill`, …)
declare the `Shear` context.

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### All Shears Variants

Tool_Shears_Basic

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
      "DurabilityLossOnDeath": false,
      "Repairable": false
    }
  }
}
```

### Fill and Water Interactions

The empty can's `Secondary` is `Watering_Can_Empty_Use`, the filled state's is `Watering_Can_Filled_Use`.
Both root interactions go through a crouch `Condition` — crouching places the can as a block
(`Block_Secondary`), otherwise the chain tries to fill (`Watering_Can_Fill`), and for the filled state
falls through to watering when there is no fluid to refill from:

```
Watering_Can_Empty_Use  → Watering_Can_Condition_Place        (Crouching → Block_Secondary, else → Watering_Can_Fill)
Watering_Can_Filled_Use → Watering_Can_Filled_Condition_Place (Crouching → Block_Secondary, else → Watering_Can_Fill, Failed → Watering_Can_Use_Charge)
Watering_Can_Use_Charge → Charging: "0" → Watering_Can_Use, "0.5" → Watering_Can_Use_3x3
```

Filling uses the `RefillContainer` interaction type, gated by the source fluid (from the real `Watering_Can_Fill` interaction; `RefillContainerInteraction` also accepts `TransformFluid` and `Durability`):

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
      "ClearAnimationOnFinish": true,
      "ItemAnimationId": "Water",
      "WorldSoundEventId": "SFX_Water_MoveIn"
    },
    "RunTime": 0.5
  }
}
```

Watering crops uses the `UseWateringCan` interaction type
(`com.hypixel.hytale.builtin.adventure.farming.interactions.UseWateringCanInteraction`; keys `Duration`,
`RefreshModifiers`, `RadiusX`, `RadiusZ`). From the real `Watering_Can_Use` interaction — a quick tap;
holding the charge for 0.5s runs `Watering_Can_Use_3x3` instead:

```json
{
  "Type": "UseWateringCan",
  "UseLatestTarget": true,
  "Duration": 86400,
  "RadiusX": 1,
  "RadiusZ": 1,
  "RefreshModifiers": ["Water"],
  "Effects": {
    "ItemAnimationId": "Water",
    "Particles": [
      { "SystemId": "Watering_Can", "TargetEntityPart": "PrimaryItem", "TargetNodeName": "Can" }
    ],
    "WorldSoundEventId": "SFX_Tool_Watering_Can_Water"
  },
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1,
    "BrokenItem": "Tool_Watering_Can"
  },
  "Failed": "Watering_Can_No_Effect",
  "RunTime": 0.2,
  "OnItemChangeBehavior": "Cancel"
}
```

`OnItemChangeBehavior` (`Cancel` / `Fail` / `Finish` / `Ignore`) is the common interaction key that
replaced the boolean `CancelOnItemChange` by 0.6.3 — it says what happens to an in-flight interaction when
the held item changes.

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
| `MaxStack` | 1 |
| `Weapon` | `{}` (empty — lets it swing like a weapon) |
| `Categories` | Items.Tools |

Crafted at the `Farmingbench` (`RequiredTierLevel` 2). The sickle has **no** `Tool` block — it cuts
plants through its swing interactions, not through gather-type specs.

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Primary` | Sickle_Attack | Two-swing `Chaining` combo (`Sickle_Swing_Left`, `Sickle_Swing_Right`) |

`Sickle_Attack` is a `Chaining` interaction whose `Next` steps are `Replace` slots (`Swing_Left`,
`Swing_Right`) defaulting to `Sickle_Swing_Left` / `Sickle_Swing_Right`; the item's `InteractionVars`
override the per-swing `*_Effect`, `*_Damage` and `*_Selector` variables (area selection lives in the
selector interactions).

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### All Sickle Variants

Tool_Sickle_Crude, Tool_Sickle_Copper, Tool_Sickle_Iron, Tool_Sickle_Steel_Rusty

---

## Repair Kit

**Location:** `Server/Item/Items/Tool/Repair_Kit/`

Utility item that opens a repair UI to restore item durability.

### Base Properties (Tool_Repair_Kit_Crude)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `MaxStack` | 25 |
| `DropOnDeath` | true |
| `PlayerAnimationsId` | Item |
| `Set` | Repair_Kit |
| `InteractionConfig` | `{ "AllEntities": true }` |
| `Categories` | Items.Tools |

### Interactions

Both `Primary` and `Secondary` are the same inline `OpenCustomUI` interaction. The page is a nested
`Page` object — its `Id` picks the page supplier, and the supplier's own keys sit beside it (from
`Tool_Repair_Kit_Crude`):

```json
{
  "Type": "OpenCustomUI",
  "Page": {
    "Id": "ItemRepair",
    "RepairPenalty": 0.2
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Page.Id` | string | Page supplier to open (`ItemRepair` → `ItemRepairPageSupplier`) |
| `Page.RepairPenalty` | double | Max-durability reduction per repair, as a ratio (0.2 = 20%) — a key of `ItemRepairPageSupplier`, not of the interaction |

### Repair Kit Tiers

| Repair Kit | Parent | Quality | RepairPenalty |
|------------|--------|---------|---------------|
| `Tool_Repair_Kit_Crude` | — | Common | 0.2 |
| `Tool_Repair_Kit_Iron` | `Tool_Repair_Kit_Crude` | Common (`ItemLevel` 1) | 0.1 |
| `Tool_Repair_Kit_Rare` | — (standalone; borrows the Thorium pickaxe model) | not set | 0.15 |

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### All Repair Kit Variants

Tool_Repair_Kit_Crude, Tool_Repair_Kit_Iron, Tool_Repair_Kit_Rare

---

## Capture Crate

**Location:** `Server/Item/Items/Tool/Capture_Crate/`

Utility item for capturing and transporting animals.

### Base Properties (Tool_Capture_Crate)

| Property | Value |
|----------|-------|
| `ItemLevel` | 18 |
| `MaxStack` | 1 |
| `PlayerAnimationsId` | Block |

The crate sets no `Quality`, `Categories` or `Tags`, and is not `Consumable`. Crafted at the
`Farmingbench` from 4 `Wood_All` and 50 `Ingredient_Life_Essence`.

### Interactions

`Primary` is inline: a 0.05s `Simple` step (plays the `Interact` item animation) whose `Next` is the
`UseCaptureCrate` interaction (from `Tool_Capture_Crate.json`):

```json
{
  "Type": "UseCaptureCrate",
  "AcceptedNpcGroups": ["Capture_Crate"],
  "FullIcon": "Icons/ItemsGenerated/Tool_Capture_Crate_Full.png",
  "Failed": {
    "Type": "Simple",
    "Effects": { "LocalSoundEventId": "SFX_Capture_Crate_Capture_Fail_Local" }
  },
  "Next": {
    "Type": "Simple",
    "Effects": {
      "LocalSoundEventId": "SFX_Capture_Crate_Capture_Succeed_Local",
      "WorldSoundEventId": "SFX_Capture_Crate_Capture_Succeed"
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AcceptedNpcGroups` | array | NPC groups that can be captured |
| `FullIcon` | string | Icon shown on the crate item once it holds a captured NPC |

(`UseCaptureCrateInteraction`, `com.hypixel.hytale.builtin.adventure.farming.interactions`; those two are
its only keys.) There is no separate "filled crate" item id: on capture, the NPC is stored on the crate
item itself as `CapturedEntity` metadata (`CapturedNPCMetadata`, keyed `CapturedEntity`, with
`IconPath`, `NpcNameKey`, `FullItemIcon`, `AlarmStore` and `CapturedEntity` fields), and capture range
comes from the interaction chain's targeting, not a `Range` property on this interaction.

### Tags

None — `Tool_Capture_Crate` sets no `Tags` block.

### All Capture Crate Variants

Tool_Capture_Crate (the "full" state is the same item carrying `CapturedEntity` metadata)

---

## Feedbag

**Location:** `Server/Item/Items/Tool/Feedbag/`

Farming tool for leading livestock around.

### Base Properties (Tool_Feedbag)

| Property | Value |
|----------|-------|
| `Quality` | Common |
| `PlayerAnimationsId` | Block |
| `Tool` | `{}` |
| `Categories` | Items.Tools |

Sets no `ItemLevel` or `MaxStack`. It carries a `BlockType` block (custom model, `Gathering.Soft`), so it
can be placed in the world. Crafted at the `Farmingbench` from wheat, vegetables, fruit and life essence.

### Interactions

**None.** `Tool_Feedbag` defines no `Interactions` block at all — there is no "feed" interaction. It works
from the NPC side: `Template_Livestock` lists it as the attractive item, so livestock follow a player
holding it (`Template_Livestock.json`):

```json
{
  "AttractiveItemSet": {
    "Value": [ "Tool_Feedbag" ],
    "Description": "The list of items that are deemed attractive (there's a chance targets holding them will be followed)."
  },
  "WeightFollowItem": {
    "Value": 100,
    "Description": "The probability the NPC will follow an attractive item when held by a non-hostile target, in percent."
  }
}
```

(Individual roles override the set — `Bison` prefers `Plant_Crop_Cauliflower_Item`.)

### Tags

```json
{
  "Tags": {
    "Type": ["Tool"]
  }
}
```

### All Feedbag Variants

Tool_Feedbag

---

## Fertilizer

**Location:** `Server/Item/Items/Tool/Feedbag/` (the fertilizer files live in the Feedbag folder and share
its `Feedbag.blockymodel` with a different texture)

Farming tool that applies a growth modifier to tilled soil. It is a durability item, not a stack of
consumables.

### Base Properties (Tool_Fertilizer)

| Property | Value |
|----------|-------|
| `ItemLevel` | 21 |
| `MaxStack` | 1 |
| `MaxDurability` | 5 |
| `DurabilityLossOnDeath` | false |
| `Repairable` | false |
| `PlayerAnimationsId` | Block |
| `Tool` | `{}` |
| `Categories` | Items.Tools |

(No `Quality` set. Crafted at the `Farmingbench`, `RequiredTierLevel` 3, from `Ingredient_Poop`,
`Ingredient_Life_Essence` and vegetables.)

### Interactions

| Slot | Interaction | Description |
|------|-------------|-------------|
| `Secondary` | Fertilizer_Use | Apply to soil (5 uses, one durability each) |

`Fertilizer_Use` is a `FertilizeSoil` interaction
(`com.hypixel.hytale.builtin.adventure.farming.interactions.FertilizeSoilInteraction`, a
`SimpleBlockInteraction`; its one key is `RefreshModifiers`). The full file:

```json
{
  "Type": "FertilizeSoil",
  "RefreshModifiers": ["Fertilizer"],
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1,
    "BrokenItem": "Empty",
    "Next": {
      "Type": "Simple",
      "RunTime": 0.15,
      "Effects": { "ItemAnimationId": "Till" }
    }
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

### All Fertilizer Variants

Tool_Fertilizer, Tool_Fertilizer_Crystal (`Secondary` = `Fertilizer_Crystal_Use`; crafted at the
`Alchemybench` from 25 `Crystal_Shards` and `Ingredient_Void_Essence`)

---

## Common Tool Patterns

### BreakBlock Interaction

Block-breaking tools point their `Primary` slot at a `*_Attack` interaction (e.g. `Pickaxe_Attack`) whose chain falls through to a `BreakBlock` step. Which blocks a tool can break, and how fast, is driven by the item's `Tool.Specs` gather types — there is no `Tool` field on the `BreakBlock` interaction itself. This excerpt is from the real `Block_Break` interaction:

```json
{
  "Type": "UseBlock",
  "Failed": {
    "Type": "BreakBlock",
    "UseLatestTarget": true,
    "Next": {
      "Type": "Replace",
      "Var": "Block_Hit_Camera_Effects",
      "DefaultOk": true,
      "DefaultValue": {
        "Interactions": [
          { "Type": "Simple", "Effects": { "CameraEffect": "Unarmed_Block_Impact" } }
        ]
      }
    }
  }
}
```

(`Block_Hit_Camera_Effects` is the `InteractionVars` hook the pickaxe uses to swap in its own
`Pickaxe_Mine_Impact` camera effect.)

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

There are no tool-specific item sound sets: every stock tool family (pickaxe, hatchet, shovel, hoe,
hammer, shears, sickle, watering can, repair kit, feedbag, fertilizer) sets
`"ItemSoundSetId": "ISS_Weapons_Wood"`. Per-tool audio comes from the interaction effects
(`SFX_Tool_T1_Swing`, `SFX_Pickaxe_T1_Swing_Down_Local`, …) and the spec-level `HitSoundLayer`.

---

## Builder Tool Args

Separate from gathering tools, **builder tool** items (the editor tools under
`Server/Item/Items/EditorTool/*.json`) are configured through a `BuilderTool` property whose `Args` array
declares the tool's adjustable parameters — the fields shown in the builder-tools UI. Which items appear in
the creative Tools menu is a separate asset (see
[Builder Tool Item References](items.md#builder-tool-item-references)).

```json
{
  "BuilderTool": {
    "Id": "Paint",
    "IsBrush": true,
    "Args": [
      {
        "Type": "Block",
        "Id": "builtin_Material",
        "Default": "Rock_Stone",
        "AllowPattern": true
      },
      {
        "Type": "Int",
        "Id": "builtin_Width",
        "Default": 5,
        "Min": 1,
        "Max": 100
      },
      {
        "Type": "Option",
        "Id": "builtin_Shape",
        "Default": "Sphere",
        "Options": ["Cube", "Sphere", "Cylinder", "Cone", "InvertedCone", "Pyramid", "InvertedPyramid", "Dome", "InvertedDome", "Diamond", "Torus"]
      },
      {
        "Type": "Option",
        "Id": "builtin_Origin",
        "Default": "Center",
        "Options": ["Center", "Bottom", "Top", "Lowest", "Highest"]
      }
    ]
  }
}
```

(Abridged from `EditorTool_Paint.json`, which also declares `builtin_Height`, `builtin_RotationFace`,
`builtin_Thickness`, `builtin_Density` and `builtin_Spacing`. The `builtin_*` ids are the `*_KEY`
constants on `BuilderTool`.)

`BuilderTool` keys: `Id`, `IsBrush`, `Args`, plus `SurvivalAllowed` (bool, `isSurvivalAllowed()` — whether
the tool may be used outside Creative; no stock editor tool sets it) and `BrushConfigurationCommand`
(string). As of 0.6.3 `BuilderTool` is a plain `BuilderCodec` value embedded in the item, not a
standalone asset — there is no `BuilderTool.getAssetMap()`.

### Arg Types

Every arg entry carries `Type` (the discriminator), `Id`, an optional `Default`, and optional
`Required` (defaults to `true`). Each `Type` value maps to a class in
`com.hypixel.hytale.server.core.asset.type.buildertool.config.args`:

| JSON `Type` | Class | Value type | Extra JSON fields |
|-------------|-------|------------|-------------------|
| `Bool` | `BoolArg` | `Boolean` | — |
| `String` | `StringArg` | `String` | — |
| `Int` | `IntArg` | `Integer` | `Min`, `Max` |
| `Float` | `FloatArg` | `Float` | `Min`, `Max` |
| `Block` | `BlockArg` | `BlockPattern` | `AllowPattern` (accept weighted block patterns, not just one block) |
| `Mask` | `MaskArg` | `BlockMask` | — |
| `Option` | `OptionArg` | `String` | `Options` (allowed values) |
| `BrushShape` | `BrushShapeArg` | `BrushShape` | — |
| `BrushOrigin` | `BrushOriginArg` | `BrushOrigin` | — |

(Those nine are the names registered on `ToolArg.CODEC` by `BuilderToolsPlugin`. The package also contains
`BrushAxisArg` and `BrushRotationArg`, but as of 0.6.3 neither is registered under a JSON `Type`, so they
cannot be declared from an item file.)

### ToolArg (Base Class)

**Package:** `com.hypixel.hytale.server.core.asset.type.buildertool.config.args`

`ToolArg<T>` is the abstract base all arg types extend.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getId()` | `String` | The arg's `Id` |
| `getValue()` | `T` | Current/default value |
| `isRequired()` | `boolean` | Whether the arg must be set (`Required`, default true) |
| `fromString(String)` | `T` | Parse a value from its string form (throws `ToolArgException` on bad input) |
| `getCodec()` | `Codec<T>` | Codec for the value type |
| `toPacket()` | `BuilderToolArg` | Network form sent to the client UI |

Typed subclasses add small extras: `IntArg.getMin()` / `IntArg.getMax()` and
`FloatArg.getMin()` / `FloatArg.getMax()` expose the range bounds.

### ToolArgException

**Package:** `com.hypixel.hytale.server.core.asset.type.buildertool.config.args`

Checked exception thrown by `fromString(String)` when a value can't be parsed (bad number, out-of-range,
unknown block, …). Carries a player-facing localized message:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getTranslationMessage()` | `Message` | Localized error message for display |

---

## Related Documentation

- [Items Reference](items.md) - Common properties and systems
- [Interactions API](interactions.md) - Tool interactions
- [Block Interactions](interactions-block.md) - BreakBlock, ChangeBlock, PlaceBlock
- [Weapons Reference](items-weapons.md) - Combat items
