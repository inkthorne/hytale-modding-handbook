---
title: "Consumable Items"
description: "Define Hytale consumables in JSON — food items with tiers and buffs, potions for instant effects and transformations, timed consumption, and consumable interactions."
seo:
  type: TechArticle
---

# Consumable Items

**Doc type:** JSON asset format · **Assets:** `Server/Item` · **Verified against 0.7.2**

> Part of the [Items API](items.md). For common item properties, see [Items Reference](items.md#common-properties).

This page documents consumable items — food and potions — that apply effects or stat changes when used, including their templates, tiers, and the interactions that drive consumption.

## Overview

Defined as JSON assets under `Server/Item` and covers:
- Food items (`Template_Food`, `Template_Fruit`, `Template_Crop_Item`) with tiers and buffs
- Potions (`Potion_Template`) for instant effects and transformations
- Timed consumption via `Consume_Charge` and the `Secondary` (right-click) slot
- Consumable interactions: `ApplyEffect`, `ChangeStat`, `ModifyInventory`, `RemoveEffect`/`ClearEntityEffect`
- `EffectCondition` / `StatsCondition` gating of potion effects
- Recipes for building custom food and potion items

> **Gotcha — consuming requires Adventure mode, standing up.** Every consume interaction is gated by a condition with `"RequiredGameMode": "Adventure"` **and `"Crouching": false`** (see `Server/Item/Interactions/Consumables/Condition_Consume_Food*.json` and `Condition_Consume_Potion*.json`), and its `Failed` branch routes to `Block_Secondary`. So food and potions **cannot be eaten/drunk in Creative mode, or while crouching** — the right-click consume is blocked, and the input falls through to the default behavior (in Creative, throwing the held item). To test a consumable, switch to Adventure first (`/gamemode Adventure`) and stand up. A custom food that "does nothing on right-click" is almost always this, not a broken item.

## Architecture
```
Consumable item (Consumable: true)
├── Food
│   ├── Template_Food / Template_Fruit / Template_Crop_Item
│   ├── Food tiers + buff system
│   └── InteractionVars: Consume_Charge, Effect
└── Potion
    ├── Potion_Template
    ├── families: Health / Stamina / Morph / Signature (drinkable)
    ├── Decorative_Potion_Template → Regen / Mana / Poison / Purify (placeable props)
    └── EffectCondition tier gating
Consumption interactions
├── ApplyEffect / RemoveEffect / ClearEntityEffect
├── ChangeStat
└── ModifyInventory
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Template_Food` | `Server/Item/Items/Food/Template_Food.json` | Base template for prepared food items |
| `Template_Fruit` | `Server/Item/Items/Plant/Fruit/Template_Fruit.json` | Template for fruit food items |
| `Template_Crop_Item` | `Server/Item/Items/Plant/Crop/_Template/Template_Crop_Item.json` | Template for raw crop items |
| `Potion_Template` | `Server/Item/Items/Potion/Potion_Template.json` | Base template for drinkable potions |
| `Decorative_Potion_Template` | `Server/Item/Items/Potion/Decorative_Potion_Template.json` | Base template for placeable, **non-drinkable** potion props |
| `ApplyEffect` | consumable interaction | Applies a status effect on use |
| `ChangeStat` | consumable interaction | Modifies an entity stat on use |
| `ModifyInventory` | consumable interaction | Alters inventory contents on use |
| `Consume_Charge` | food `InteractionVars` slot | Charging/timing config for consumption |

## Quick Navigation

| Category | Template | Count | Description |
|----------|----------|-------|-------------|
| [Food](#food-system) | Template_Food | 30 files in `Items/Food/` | Healing and stat buffs |
| [Fruit / Crops](#template_fruit) | Template_Fruit, Template_Crop_Item | 9 fruit + 14 crop items | Foraged and farmed edibles |
| [Potions](#potion-system) | Potion_Template | 19 children (+ `Potion_Antidote`) | Instant effects and transformations |
| [Potion props](#regeneration-potions-decorative-not-drinkable) | Decorative_Potion_Template | 16 children | Placeable, non-drinkable potion scenery |

`Server/Item/Items/Potion/` holds 41 files: the two templates, 19 drinkable
`Potion_Template` children, 16 decorative props, the standalone `Potion_Antidote`, and three
empty-bottle items (`Potion_Empty`, `Potion_Empty_Small`, `Potion_Empty_Large`).

---

## Food System

Food items restore health and provide temporary buffs when consumed. The system uses timed consumption with charging mechanics.

### Template_Food

**Location:** `Server/Item/Items/Food/Template_Food.json`

Base template for all prepared food items (bread, pies, kebabs, salads).

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `MaxStack` | 25 |
| `ItemLevel` | 10 |
| `Consumable` | true |
| `Categories` | Items.Foods |
| `ResourceTypes` | `[{ "Id": "Foods" }]` |
| `PlayerAnimationsId` | Item |

#### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Secondary` | Root_Secondary_Consume_Food_T1 | Timed consumption |

Food uses the `Secondary` (right-click) slot for consumption, leaving `Primary` available for other actions. Children override the slot to pick their tier — `Root_Secondary_Consume_Food_T2` / `_T3` for the slower, stronger tiers.

#### Tags

```json
{
  "Tags": {
    "Type": ["Food"]
  }
}
```

#### InteractionVars

Child food items customize these variables:

| Variable | Purpose |
|----------|---------|
| `Consume_Charge` | Charging configuration (duration, movement speed) |
| `Effect` | ApplyEffect interaction for healing/buffs |
| `ConsumeSFX` | Sound during consumption |
| `ConsumedSFX` | Sound when consumption completes |

#### Template InteractionVars

```json
{
  "InteractionVars": {
    "Consume_Charge": {
      "Interactions": [{
        "Parent": "Consume_Charge_Food_T1_Inner",
        "Effects": {
          "ItemAnimationId": "Consume"
        }
      }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "ApplyEffect",
        "EffectId": "Food_Health_Regen_Small"
      }]
    },
    "ConsumeSFX": {
      "Interactions": [{
        "Parent": "Consume_SFX",
        "Effects": {
          "LocalSoundEventId": "SFX_Consume_Bread_Local"
        }
      }]
    },
    "ConsumedSFX": {
      "Interactions": [{
        "Parent": "Consumed_SFX",
        "Effects": {
          "LocalSoundEventId": "SFX_Consume_Bread_Local"
        }
      }]
    }
  }
}
```

Each `InteractionVar` extends a shared parent interaction (e.g. `Consume_Charge_Food_T1_Inner`, `Consume_SFX`, `Consumed_SFX`) via the `Parent` field rather than declaring a `Type`.

---

### Template_Fruit

**Location:** `Server/Item/Items/Plant/Fruit/Template_Fruit.json`

Base template for fruit items. Uses the same `Root_Secondary_Consume_Food_T1` consumption
chain as `Template_Food`, but is a *plant* by tag — fruit hangs on a bush or tree, so it is
also a placeable block.

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 0 |
| `Consumable` | true |
| `Categories` | `["Blocks.Plants", "Items.Foods"]` |
| `ItemSoundSetId` | ISS_Items_Foliage |
| `PlayerAnimationsId` | Item |

It sets no `MaxStack` of its own (children inherit the engine default or set their own). Its
`Effect` var applies `Food_Instant_Heal_T1` and then chains `HealthRegen_TierCheck_Raw` (see
[Food Buff System](#food-buff-system)).

#### Interactions

| Slot | Root Interaction |
|------|------------------|
| `Secondary` | Root_Secondary_Consume_Food_T1 |

#### Tags

```json
{
  "Tags": {
    "Type": ["Plant"],
    "Family": ["Fruit"]
  }
}
```

Note the tag is `Plant`, **not** `Food` — only `Template_Food` carries `"Type": ["Food"]`.

#### ResourceTypes

Fruits register a single resource type for recipe flexibility:

```json
{
  "ResourceTypes": [
    { "Id": "Fruits" }
  ]
}
```

---

### Template_Crop_Item

**Location:** `Server/Item/Items/Plant/Crop/_Template/Template_Crop_Item.json`

Base template for harvested vegetables and crops.

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `Consumable` | true |
| `Categories` | Items.Foods |
| `ItemSoundSetId` | ISS_Items_Foliage |
| `PlayerAnimationsId` | Item |

Like `Template_Fruit`, it sets no `MaxStack`. Its only `InteractionVars` entry is `Effect`
(`Food_Instant_Heal_T1`, then `HealthRegen_TierCheck_Raw`); the SFX vars fall through to the
shared defaults.

#### Interactions

| Slot | Root Interaction |
|------|------------------|
| `Secondary` | Root_Secondary_Consume_Food_T1 |

#### Tags

```json
{
  "Tags": {
    "Type": ["Plant"],
    "Family": ["Crop"]
  }
}
```

#### ResourceTypes

```json
{
  "ResourceTypes": [
    { "Id": "Vegetables" }
  ]
}
```

---

### Food Tiers

Food items follow a tiered progression. The tier is named by which
`Root_Secondary_Consume_Food_T*` the item puts in its `Secondary` slot, and in 0.7.2 the tier
decides **only which buffs the food grants**. Eat time and instant heal are the same at every
tier:

| Tier | Typical Quality | Consume Time | Instant Heal | Buff tier |
|------|-----------------|--------------|--------------|-----------|
| T1 | Common | 2.5s | 5% (`Food_Instant_Heal_T1`) | `*_TierCheck_T1` |
| T2 | Uncommon | 2.5s | 5% (`Food_Instant_Heal_T1`) | `*_TierCheck_T2` |
| T3 | Rare | 2.5s | 5% (`Food_Instant_Heal_T1`) | `*_TierCheck_T3` |

The three charge interactions `Consume_Charge_Food_T{1,2,3}_Inner` are identical: a `"2.5"`
hold threshold, `"FailOnDamage": false` and `"HorizontalSpeedMultiplier": 0.75`, so taking a
hit does not cancel the meal and eating slows you to 75% speed. (Every stock food also
overrides `Consume_Charge` with `"Parent": "Consume_Charge_Food_T1_Inner"`, so the T2 and T3
inner charges only run for a food that leaves that var alone.) 0.7.2 also removed the
`Food_Instant_Heal_T2`, `Food_Instant_Heal_T3` and `Food_Instant_Heal_Bread` effects, so every
stock food's instant heal is `Food_Instant_Heal_T1`; a custom food that still names one of the
removed ids points at an effect that no longer ships. `Food_Instant_Heal_T1` applies its
`StatModifiers` as a `Percent` of max health over a `Duration` of `0.1`s, which is what makes
it read as instant.

---

### Food Buff System

Prepared foods layer a longer buff on top of the instant heal. Rather than applying the buff
effect directly, they chain a **tier-check interaction** from
`Server/Item/Interactions/Consumables/Food/` — `HealthRegen_TierCheck_T{1,2,3}`,
`Meat_TierCheck_T{1,2,3}`, `FruitVeggie_TierCheck_T{1,2,3}`, plus `HealthRegen_TierCheck_Raw`
(0.7.2), which fruits and crops chain. Each is an `EffectCondition` that refuses to downgrade
an already-active higher tier, clears the lower tiers, and then applies its own:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["Meat_Buff_T3"],
  "Match": "None",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ClearEntityEffect", "EntityEffectId": "Meat_Buff_T1" },
      { "Type": "ApplyEffect", "EffectId": "Meat_Buff_T2" }
    ]
  },
  "Failed": { "Type": "Simple", "RunTime": 0 }
}
```

#### Health Regeneration Buffs

Defined in `Server/Entity/Effects/Food/Buff/`. `StatModifiers` here are a **percent of max
health per regen tick** (`DamageCalculatorCooldown` = 2s between ticks), not HP/s:

| Buff | Duration | Effect |
|------|----------|--------|
| `HealthRegen_Buff_Raw` | 60s | +1% max health / 2s |
| `HealthRegen_Buff_T1` | 360s | +1% max health / 2s |
| `HealthRegen_Buff_T2` | 360s | +1.5% max health / 2s |
| `HealthRegen_Buff_T3` | 360s | +2% max health / 2s |

`HealthRegen_Buff_Raw` is new in 0.7.2. `HealthRegen_TierCheck_Raw` applies it only while none
of T1–T3 is active, and each of T1–T3 clears it.

#### Meat Buffs

Cooked meats raise maximum health via a `Multiplicative` `RawStatModifiers` entry targeting
`Max`:

| Buff | Duration | Effect |
|------|----------|--------|
| `Meat_Buff_T1` | 360s | ×1.05 Max Health |
| `Meat_Buff_T2` | 360s | ×1.10 Max Health |
| `Meat_Buff_T3` | 360s | ×1.15 Max Health, plus 5% Physical and Projectile `DamageResistance` |

#### Fruit/Vegetable Buffs

Plant-based foods boost maximum stamina, and the higher tiers also add flat stamina regen:

| Buff | Duration | Effect |
|------|----------|--------|
| `FruitVeggie_Buff_T1` | 360s | ×1.10 Max Stamina |
| `FruitVeggie_Buff_T2` | 360s | ×1.20 Max Stamina, +0.025 Stamina regen |
| `FruitVeggie_Buff_T3` | 360s | ×1.30 Max Stamina, +0.05 Stamina regen |

---

### Example Child: Food_Bread

Abridged from `Server/Item/Items/Food/Food_Bread.json` (the real file also carries a full
`BlockType` so bread can be placed):

```json
{
  "Parent": "Template_Food",
  "TranslationProperties": {
    "Name": "server.items.Food_Bread.name",
    "Description": "server.items.Food_Bread.description"
  },
  "Interactions": {
    "Secondary": "Root_Secondary_Consume_Food_T2"
  },
  "Quality": "Uncommon",
  "Icon": "Icons/ItemsGenerated/Food_Bread.png",
  "ItemLevel": 7,
  "MaxStack": 25,
  "DropOnDeath": true,
  "Scale": 1.5,
  "Recipe": {
    "TimeSeconds": 5,
    "Input": [
      { "ItemId": "Ingredient_Dough", "Quantity": 1 },
      { "ResourceTypeId": "Fuel", "Quantity": 3 }
    ],
    "Output": [ { "ItemId": "Food_Bread" } ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Id": "Cookingbench",
      "Categories": ["Baked"]
    }]
  },
  "InteractionVars": {
    "Consume_Charge": {
      "Interactions": [{
        "Parent": "Consume_Charge_Food_T1_Inner",
        "Effects": {
          "Particles": [{
            "SystemId": "Food_Eat",
            "Color": "#DCC15D",
            "TargetNodeName": "Mouth",
            "TargetEntityPart": "Entity"
          }]
        }
      }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "ApplyEffect",
        "EffectId": "Food_Instant_Heal_T1"
      }]
    }
  }
}
```

Two things worth copying: a recipe input can name a `ResourceTypeId` (any fuel) instead of a
specific `ItemId`, and the `Consume_Charge` override is where per-food eat particles go —
`Food_Eat` attached to the eater's `Mouth` node, tinted to match the food.

---

### Food Categories

#### Raw Foods

Unprocessed foods: instant heal only, no buff, and **no `Secondary` slot of their own** —
they inherit `Root_Secondary_Consume_Food_T1` from `Template_Food`.

| Item | Quality | Instant heal |
|------|---------|--------------|
| `Food_Beef_Raw` | Common | `Food_Instant_Heal_T1` |
| `Food_Chicken_Raw` | Common | `Food_Instant_Heal_T1` |
| `Food_Pork_Raw` | Common | `Food_Instant_Heal_T1` |
| `Food_Wildmeat_Raw` | Common | `Food_Instant_Heal_T1` |
| `Food_Fish_Raw` | Common | `Food_Instant_Heal_T1` |
| `Food_Egg` | Common | `Food_Instant_Heal_T1` |

`Food_Fish_Raw_Uncommon` / `_Rare` / `_Epic` / `_Legendary` are `Parent: "Food_Fish_Raw"`
rarity re-skins that override only `Variant`, `ItemLevel` and `Recipe`, so they eat exactly like
plain raw fish.

#### Cooked Foods

Cooked at a campfire; T1 timing plus a tier-1 buff pair.

| Item | Quality | Tier | Buff checks |
|------|---------|------|-------------|
| `Food_Wildmeat_Cooked` | Common | T1 | `HealthRegen_TierCheck_T1`, `Meat_TierCheck_T1` |
| `Food_Fish_Grilled` | Common | T1 | `HealthRegen_TierCheck_T1`, `Meat_TierCheck_T1` |
| `Food_Vegetable_Cooked` | Common | T1 | `HealthRegen_TierCheck_T1`, `FruitVeggie_TierCheck_T1` |

#### Prepared Foods

Crafted at a cooking bench; the T2/T3 root and the matching buff tier.

| Item | Quality | Tier | Buff checks |
|------|---------|------|-------------|
| `Food_Bread` | Uncommon | T2 | none |
| `Food_Kebab_Meat` | Uncommon | T2 | `HealthRegen_TierCheck_T2`, `Meat_TierCheck_T2` |
| `Food_Kebab_Fruit` | Uncommon | T2 | `HealthRegen_TierCheck_T2`, `FruitVeggie_TierCheck_T2` |
| `Food_Kebab_Vegetable` | Uncommon | T2 | `HealthRegen_TierCheck_T2`, `FruitVeggie_TierCheck_T2` |
| `Food_Kebab_Mushroom` | Uncommon | T2 | `HealthRegen_TierCheck_T2`, `FruitVeggie_TierCheck_T2` |
| `Food_Salad_Berry` | Uncommon | T2 | `HealthRegen_TierCheck_T2`, `FruitVeggie_TierCheck_T2` |
| `Food_Salad_Mushroom` | Uncommon | T2 | `HealthRegen_TierCheck_T2`, `FruitVeggie_TierCheck_T2` |
| `Food_Cheese` | Uncommon | T3 | none |
| `Food_Popcorn` | Uncommon | T3 | none |
| `Food_Pie_Meat` | Rare | T3 | `HealthRegen_TierCheck_T3`, `Meat_TierCheck_T3` |
| `Food_Pie_Apple` | Rare | T3 | `HealthRegen_TierCheck_T3`, `FruitVeggie_TierCheck_T3` |
| `Food_Pie_Pumpkin` | Rare | T3 | `HealthRegen_TierCheck_T3`, `FruitVeggie_TierCheck_T3` |
| `Food_Salad_Caesar` | Rare | T3 | `HealthRegen_TierCheck_T3`, `FruitVeggie_TierCheck_T3` |

---

### All Food Variants

`Server/Item/Items/Food/` holds 30 files: Food_Beef_Raw, Food_Bread, Food_Candy_Cane,
Food_Cheese, Food_Chicken_Raw, Food_Egg, Food_Fish_Grilled, Food_Fish_Raw,
Food_Fish_Raw_Epic, Food_Fish_Raw_Legendary, Food_Fish_Raw_Rare, Food_Fish_Raw_Uncommon,
Food_Kebab_Fruit, Food_Kebab_Meat, Food_Kebab_Mushroom, Food_Kebab_Vegetable, Food_Pie_Apple,
Food_Pie_Meat, Food_Pie_Pumpkin, Food_Popcorn, Food_Pork_Raw, Food_Salad_Berry,
Food_Salad_Caesar, Food_Salad_Mushroom, Food_Vegetable_Cooked, Food_Wildmeat_Cooked,
Food_Wildmeat_Raw, Template_Food, plus two seasonal props (Halloween_Basket_Pumpkin,
Halloween_Basket_Straw) that are `Parent: "Deco_Trash"` and not edible at all.

Fruits and crops are *not* in that directory: they live under
`Server/Item/Items/Plant/Fruit/` and `Server/Item/Items/Plant/Crop/<Crop>/` as
`Plant_Fruit_*` and `Plant_Crop_*_Item` items built on `Template_Fruit` and
`Template_Crop_Item`.

---

## Potion System

Potions provide instant effects and transformations. Unlike food, the drinkable ones gate
themselves with an `EffectCondition` so a stronger effect is never overwritten by a weaker
one. Note that only 20 of the 41 files in `Server/Item/Items/Potion/` are drinkable — see
[Regeneration Potions](#regeneration-potions-decorative-not-drinkable).

### Potion_Template

**Location:** `Server/Item/Items/Potion/Potion_Template.json`

Base template for all **drinkable** potion items. (Placeable potion scenery uses
`Decorative_Potion_Template` instead.)

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `MaxStack` | 10 |
| `Consumable` | true |
| `Categories` | Items.Potions |

#### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Secondary` | Root_Secondary_Consume_Potion | Consumption via `Condition_Consume_Potion` → `Consume_Charge_Potion_Fast` (1.5s hold) |

Most drinkable children replace that root with a family-specific one:

| Family | `Secondary` root | Chain |
|--------|------------------|-------|
| Health | `Root_Secondary_Consume_Potion_Health` (0.7.2) | `Condition_Consume_Potion_Health`: a `CooldownCondition` on `Potion_Consume_Health`, then `Consume_Charge_Potion_Fast` (1.5s) |
| Stamina | `Root_Secondary_Consume_Potion_Stamina` | `Condition_Consume_Potion_Stamina`: a `CooldownCondition` on `Potion_Consume_Stamina`, then `Consume_Charge_Potion_Fastest` (0.5s) |
| Signature | `Root_Secondary_Consume_Potion_Slow` | `Condition_Consume_Potion_Slow` → `Consume_Charge_Potion_Slow` (3.0s) |
| Morph | `Root_Secondary_Consume_Potion_Morph` | `Condition_Consume_Potion_Morph`, which refuses the drink while a potion morph is active, then `Consume_Charge_Potion_Fast` |

The cooldowns are new in 0.7.2. `Consume_Charge_Potion_Fast` and `_Fastest` `Replace` a
`ConsumeCooldown` var after the drink completes (default: a no-op), and the health and stamina
potions fill it with `Consume_Potion_Health_Cooldown` (a `TriggerCooldown` of 15s on
`Potion_Consume_Health`) or `Consume_Potion_Stamina_Cooldown` (30s on `Potion_Consume_Stamina`).
While that cooldown runs, the `CooldownCondition` fails and the potion cannot be drunk. All five
health tiers share one cooldown id, and so do all five stamina tiers.

#### Tags

```json
{
  "Tags": {
    "Type": ["Potion"]
  }
}
```

#### BlockType (Placeable)

Potions define a `BlockType` so they can be placed and emit colored light:

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Items/Consumables/Potions/Potion.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Items/Consumables/Potions/Potion_Textures/Red.png", "Weight": 1 }
    ],
    "ParticleColor": "#ff3730",
    "Light": {
      "Color": "#522"
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `CustomModel` | string | `.blockymodel` used for the placed block |
| `CustomModelTexture` | array | Weighted texture variants for the model |
| `ParticleColor` | string | Hex color for block-break particles |
| `Light.Color` | string | Hex color of the light the placed potion emits |

#### InteractionVars

`Potion_Template` defines exactly four vars (the health and stamina children add a fifth,
`ConsumeCooldown`, described above):

| Variable | Purpose |
|----------|---------|
| `Effect` | ApplyEffect / EffectCondition interaction (the template's own default applies `Potion_Health_Instant_Lesser` + `Potion_Health_Regen_Lesser`) |
| `RemoveEffect` | Effect to clear on consumption; defaults to a no-op `{ "Type": "Simple" }` |
| `ConsumeSFX` | Sound while drinking (`SFX_Health_Potion_Low_Drink`) |
| `ConsumedSFX` | Sound when consumption completes (`SFX_Potion_Drink_Success`) |

The template also sets `PlayerAnimationsId` to an inline animation override that maps the
`Consume` animation to the drink `.blockyanim` pair, and `Utility: { "Compatible": false }`.

---

### Stat Check Condition

A `StatsCondition` interaction can gate a consume on a stat threshold — the shipped
`Server/Item/Interactions/Consumables/Stat_Check.json` is exactly that:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Health": 100 },
  "ValueType": "Percent",
  "LessThan": true,
  "Next": "Consume_Charge"
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Costs` | object | Stat to check and threshold |
| `ValueType` | string | `"Percent"` or `"Absolute"` |
| `LessThan` | boolean | If true, the stat must be below the threshold |
| `Lenient` | boolean | Codec doc: "the interaction can run even if the stat cost is not met, providing that the value is greater than zero" |

`Costs` stopped being required in 0.7.2 (ability cast chains can supply their costs another
way); in an ordinary item chain, omitting it makes the condition always fail.

Example: `Health: 100` with `LessThan: true` means "only drink if health < 100%".

> **Gotcha — the `Stat_Check` var is not wired into the stock consume chains.** Several
> potions (`Potion_Morph_*`) and `Food_Candy_Cane` declare a `Stat_Check` entry in their
> `InteractionVars`, but nothing in `Root_Secondary_Consume_Potion` →
> `Condition_Consume_Potion` → `Consume_Charge_Potion_Fast` does a `Replace` on that var, so
> those blocks never run. The only asset that actually consumes it is the test item
> `Server/Item/Items/MISC/Bandage_Potion_Test.json`, which supplies its own chain with
> `{ "Type": "Replace", "Var": "Stat_Check" }`. If you want a stat gate on a custom
> consumable, put a `StatsCondition` in the `Effect` var (or write your own root
> interaction) rather than relying on `Stat_Check`. What the stock potions actually use to
> avoid waste is an `EffectCondition` inside `Effect` (see below).

---

### Health Potions

Restore health instantly. Waste is avoided with an `EffectCondition` (`"Match": "None"`) that
refuses to drink while a stronger regen effect is already running, then clears the weaker
tiers before applying its own. `Potion_Health_Large`, the top tier, skips the condition and
always drinks. Drinking any health potion starts the shared 15s `Potion_Consume_Health`
cooldown.

Listed weakest first — that is also the order in which each tier clears the ones below it:

| Potion | Quality | EffectId(s) Applied | Clears |
|--------|---------|---------------------|--------|
| `Potion_Health_Lesser` | Common | Potion_Health_Instant_Lesser, Potion_Health_Regen_Lesser | - |
| `Potion_Health_Small` | Uncommon | Potion_Health_Instant_Small, Potion_Health_Regen_Small | Regen_Lesser |
| `Potion_Health` | Common | Potion_Health_Instant, Potion_Health_Regen | Regen_Lesser, Regen_Small |
| `Potion_Health_Greater` | Uncommon | Potion_Health_Instant_Greater, Potion_Health_Regen_Greater | Regen, Regen_Lesser, Regen_Small |
| `Potion_Health_Large` | Rare | Potion_Health_Instant_Large, Potion_Health_Regen_Large | Regen, Regen_Greater, Regen_Lesser, Regen_Small |

#### Example: Potion_Health

```json
{
  "Parent": "Potion_Template",
  "TranslationProperties": {
    "Name": "server.items.Potion_Health.name",
    "Description": "server.items.Potion_Health.description"
  },
  "Quality": "Common",
  "ItemLevel": 7,
  "Icon": "Icons/ItemsGenerated/Potion_Health.png",
  "Interactions": {
    "Secondary": "Root_Secondary_Consume_Potion_Health"
  },
  "Recipe": {
    "KnowledgeRequired": false,
    "Input": [
      { "ItemId": "Potion_Empty", "Quantity": 1 },
      { "ItemId": "Plant_Fruit_Berries_Red", "Quantity": 12 },
      { "ItemId": "Plant_Petals_Blood", "Quantity": 6 },
      { "ItemId": "Plant_Crop_Health2", "Quantity": 1 }
    ],
    "BenchRequirement": [{
      "Id": "Alchemybench",
      "Type": "Crafting",
      "Categories": ["Alchemy_Potions"],
      "RequiredTierLevel": 3
    }],
    "OutputQuantity": 1,
    "TimeSeconds": 1
  },
  "InteractionVars": {
    "RemoveEffect": {
      "Interactions": [{ "Type": "Simple" }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "EffectCondition",
        "EntityEffectIds": [
          "Potion_Health_Regen_Greater",
          "Potion_Health_Regen_Large"
        ],
        "Match": "None",
        "Next": {
          "Type": "Serial",
          "Interactions": [
            { "Type": "ClearEntityEffect", "EntityEffectId": "Potion_Health_Regen_Lesser" },
            { "Type": "ClearEntityEffect", "EntityEffectId": "Potion_Health_Regen_Small" },
            { "Type": "ApplyEffect", "EffectId": "Potion_Health_Instant" },
            { "Type": "ApplyEffect", "EffectId": "Potion_Health_Regen" }
          ]
        },
        "Failed": { "Type": "Simple" }
      }]
    },
    "ConsumeCooldown": {
      "Interactions": ["Consume_Potion_Health_Cooldown"]
    }
  }
}
```

(Abridged: the real file also carries `IconProperties`, the `ConsumeSFX` / `ConsumedSFX` vars,
a `BlockType`, and `DropOnDeath`.)

---

### Stamina Potions

Restore stamina instantly. What stops a player chain-drinking them is the shared 30s
`Potion_Consume_Stamina` cooldown (see [Potion_Template](#potion_template)). 0.7.2 removed the
`Potion_Stamina_Cooldown` effect that earlier builds applied for the same purpose, so an item
that still applies it names an effect that no longer ships:

| Potion | Quality | EffectId Applied |
|--------|---------|------------------|
| `Potion_Stamina_Lesser` | Common | Potion_Stamina_Instant_Lesser |
| `Potion_Stamina_Small` | Uncommon | Potion_Stamina_Instant_Small |
| `Potion_Stamina` | Common | Potion_Stamina_Instant_Small |
| `Potion_Stamina_Greater` | Uncommon | Potion_Stamina_Instant_Greater |
| `Potion_Stamina_Large` | Rare | Potion_Stamina_Instant_Large |

(`Potion_Stamina` reusing `Potion_Stamina_Instant_Small` looks like a content oversight —
`Potion_Stamina_Instant` exists as an effect asset but no item applies it.)

---

### Regeneration Potions (decorative, not drinkable)

| Potion | Variants |
|--------|----------|
| `Potion_Regen_Health` | `Potion_Regen_Health_Small`, `Potion_Regen_Health`, `Potion_Regen_Health_Large` |
| `Potion_Regen_Stamina` | `Potion_Regen_Stamina_Small`, `Potion_Regen_Stamina`, `Potion_Regen_Stamina_Large` |
| `Potion_Regen_Mana` | `Potion_Regen_Mana_Small`, `Potion_Regen_Mana`, `Potion_Regen_Mana_Large` |

> **Gotcha — these are props, not potions.** The nine `Potion_Regen_*` items are
> `Parent: "Decorative_Potion_Template"`, which is **not** consumable: it sets no
> `Consumable`, declares no `InteractionVars`, and its `Interactions` are
> `{"Primary": "Block_Primary", "Secondary": "Block_Secondary"}` — i.e. place-the-block, not
> drink-it. Right-clicking one places it. If you want an actual over-time recovery potion,
> parent from `Potion_Template` and put the regen `ApplyEffect` in the `Effect` var; the
> effect assets themselves (`Potion_Health_Regen*`, `Potion_Stamina_Regen*`, …) are real and
> live under `Server/Entity/Effects/Potion/`.

A regen-potion item overrides only `Icon`, `TranslationProperties`, and the `BlockType`
model/texture/light — everything else comes from the decorative template:

```json
{
  "Parent": "Decorative_Potion_Template",
  "TranslationProperties": {
    "Name": "server.items.Potion_Regen_Health.name"
  },
  "Icon": "Icons/ItemsGenerated/Potion_Regen_Health.png",
  "BlockType": {
    "CustomModel": "Items/Consumables/Potions/Potion.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Items/Consumables/Potions/Potion_Textures/Pink.png", "Weight": 1 }
    ],
    "ParticleColor": "#f977be",
    "Light": { "Color": "#414" },
    "TextureComputedColor": "#A7B6C5"
  }
}
```

---

### Morph Potions

Transform the player into creatures for exploration or stealth.

| Potion | Quality | Form |
|--------|---------|------|
| `Potion_Morph_Dog` | Rare | Dog |
| `Potion_Morph_Frog` | Rare | Frog |
| `Potion_Morph_Mouse` | Rare | Mouse |
| `Potion_Morph_Pigeon` | Rare | Pigeon |

#### Morph Effect Structure

The potion's `Effect` var simply applies an effect whose `EffectId` matches a morph effect asset. The transformation details (model, duration) live on the effect, not the item interaction:

```json
{
  "Type": "ApplyEffect",
  "EffectId": "Potion_Morph_Dog"
}
```

The corresponding effect (`Server/Entity/Effects/Potion/Potion_Morph_Dog.json`) sets
`ModelChange` (`"Corgi"`), `Duration` (60s), `OverlapBehavior`, a `StatusEffectIcon`, and an
`ApplicationEffects` block with the transformation burst particle and sound. See
[Effects & Stats](effects-stats.md#model-transformation).

Morph potions also route through their own condition, `Root_Secondary_Consume_Potion_Morph` →
`Condition_Consume_Potion_Morph`, which adds an `EffectCondition` refusing the drink while any
of the four potion morphs (`Potion_Morph_Dog` / `_Frog` / `_Mouse` / `_Pigeon`) is already
active. A fifth morph effect, `Potion_Morph_Mosshorn`, exists with no potion item — it is
applied by drinking `Container_Bucket` or `Deco_Bucket` in its `Filled_Mosshorn_Milk` state,
and the morph condition does not check for it.

---

### Utility Potions

Special-purpose potions — but note that most of this family ships as scenery:

| Potion | Quality | Effect |
|--------|---------|--------|
| `Potion_Antidote` | Common | Clears `Poison_T1`/`T2`/`T3` and `Ability_Poison_Stack_A`/`B`/`C`, applies `Antidote` |
| `Potion_Purify` | - | **Decorative only** — `Parent: "Decorative_Potion_Template"`, no effect |
| `Potion_Poison` / `Potion_Poison_Minor` / `Potion_Poison_Large` | - | **Decorative only** |
| `Potion_Mana` / `Potion_Mana_Small` / `Potion_Mana_Large` | - | **Decorative only** |

`Potion_Antidote` is the only utility potion that is actually drinkable — and it is not even a
`Potion_Template` child; it is a standalone item under `Categories: ["Items.Consumables"]`
that wires up `Root_Secondary_Consume_Potion` itself and re-uses a bomb model/texture.

#### Example: Potion_Antidote

The antidote clears each poison tier in sequence (via chained `ClearEntityEffect.Next`), then applies the `Antidote` effect. 0.7.2 added the three `Ability_Poison_Stack_*` effects to the chain (abridged — the real file also carries `PlayerAnimationsId`, `Model`, `Texture`, `Light`, `Tags`, the SFX vars, and a `Recipe`):

```json
{
  "TranslationProperties": {
    "Name": "server.items.Potion_Antidote.name",
    "Description": "server.items.Potion_Antidote.description"
  },
  "Quality": "Common",
  "ItemLevel": 15,
  "Categories": ["Items.Consumables"],
  "Consumable": true,
  "Interactions": {
    "Secondary": "Root_Secondary_Consume_Potion"
  },
  "InteractionVars": {
    "Effect": {
      "Interactions": [{
        "Type": "ClearEntityEffect",
        "EntityEffectId": "Poison_T1",
        "Next": {
          "Type": "ClearEntityEffect",
          "EntityEffectId": "Poison_T2",
          "Next": {
            "Type": "ClearEntityEffect",
            "EntityEffectId": "Poison_T3",
            "Next": {
              "Type": "ClearEntityEffect",
              "EntityEffectId": "Ability_Poison_Stack_A",
              "Next": {
                "Type": "ClearEntityEffect",
                "EntityEffectId": "Ability_Poison_Stack_B",
                "Next": {
                  "Type": "ClearEntityEffect",
                  "EntityEffectId": "Ability_Poison_Stack_C",
                  "Next": { "Type": "ApplyEffect", "EffectId": "Antidote" }
                }
              }
            }
          }
        }
      }]
    }
  }
}
```

---

### Signature Potions

Potions that affect signature energy/charges.

| Potion | Quality | EffectId Applied |
|--------|---------|------------------|
| `Potion_Signature_Lesser` | Common | Potion_Signature_Regen_Lesser |
| `Potion_Signature_Small` | Uncommon | Potion_Signature_Regen_Small |
| `Potion_Signature` | Common | Potion_Signature_Regen |
| `Potion_Signature_Greater` | Uncommon | Potion_Signature_Regen_Greater |
| `Potion_Signature_Large` | Rare | Potion_Signature_Regen_Large |

Like the health line, each tier clears the weaker regen effects before applying its own, and
`Potion_Signature_Large` skips the stronger-effect check. Signature potions drink through
`Root_Secondary_Consume_Potion_Slow` (a 3.0s hold) and have no consume cooldown.

---

### All Potion Variants

**Drinkable** (`Parent: "Potion_Template"`, plus the standalone antidote): Potion_Antidote,
Potion_Health_Lesser, Potion_Health_Small, Potion_Health, Potion_Health_Greater,
Potion_Health_Large, Potion_Morph_Dog, Potion_Morph_Frog, Potion_Morph_Mouse,
Potion_Morph_Pigeon, Potion_Signature_Lesser, Potion_Signature_Small, Potion_Signature,
Potion_Signature_Greater, Potion_Signature_Large, Potion_Stamina_Lesser,
Potion_Stamina_Small, Potion_Stamina, Potion_Stamina_Greater, Potion_Stamina_Large

**Decorative only** (`Parent: "Decorative_Potion_Template"`, not consumable):
Potion_Mana_Small, Potion_Mana, Potion_Mana_Large, Potion_Poison_Minor, Potion_Poison,
Potion_Poison_Large, Potion_Purify, Potion_Regen_Health_Small, Potion_Regen_Health,
Potion_Regen_Health_Large, Potion_Regen_Mana_Small, Potion_Regen_Mana,
Potion_Regen_Mana_Large, Potion_Regen_Stamina_Small, Potion_Regen_Stamina,
Potion_Regen_Stamina_Large

**Crafting inputs:** Potion_Empty, Potion_Empty_Small, Potion_Empty_Large

---

## Common Consumable Patterns

### Consumable Property

All consumable items share these core properties:

```json
{
  "Consumable": true,
  "MaxStack": 25
}
```

> **`Consumable: true` does not itself remove anything.** In the server jar it is a plain
> boolean on `Item` that is forwarded to the client in the item packet (nothing on the server
> branches on `isConsumable()`), so it drives client-side presentation only. The stack is
> decremented by the `ModifyInventory` / `AdjustHeldItemQuantity: -1` step inside the
> consume-charge chain. A custom item that sets `Consumable: true` but wires up no consume
> interaction will never be eaten.

### ApplyEffect Interaction

The standard way to grant buffs from consumables:

```json
{
  "Type": "ApplyEffect",
  "EffectId": "Food_Instant_Heal_T1"
}
```

`ApplyEffect` takes these keys on top of the common interaction fields:

| Key | Type | Description |
|-----|------|-------------|
| `EffectId` | string or object | Effect asset id (required). An inline effect object also decodes, as `Food_Candy_Cane` does |
| `Entity` | enum | Which entity in the interaction context receives it; defaults to the user |
| `Duration` | float | 0.7.2: overrides the effect asset's duration, in seconds. `0` or absent keeps the asset's own |

Before 0.7.2 there was no `Duration` key, and a "same buff, shorter timer" variant needed a
second effect asset. From 0.7.2 an item can override the timer in place:
`{ "Type": "ApplyEffect", "EffectId": "Meat_Buff_T1", "Duration": 60 }`.

### ChangeStat Interaction

For instant stat modifications without buff effects:

```json
{
  "Type": "ChangeStat",
  "Behaviour": "Add",
  "StatModifiers": { "Health": 0.30 },
  "ValueType": "Percent"
}
```

| Property | Type | Description |
|----------|------|-------------|
| `StatModifiers` | object | Stat ID to value mapping. Required and non-empty before 0.7.2; the codec stops enforcing that in 0.7.2, but in an ordinary item chain the interaction does nothing without it |
| `ValueType` | enum | `Absolute` (default) or `Percent`. With `Absolute`, `100` means the stat's max |
| `Behaviour` | enum | `Add` (default), `Set`, `Min`, or `Max` — how the modifier combines with the current value |
| `Entity` | enum | Which entity in the interaction context to modify; defaults to the user |

### Consume_Charge (Food)

Food items handle timed consumption by extending a shared charge interaction through the `Consume_Charge` var rather than declaring charge fields inline. The parent (`Consume_Charge_Food_T1_Inner`) defines the charge behavior; the child only supplies effects such as the consume animation:

```json
{
  "Consume_Charge": {
    "Interactions": [{
      "Parent": "Consume_Charge_Food_T1_Inner",
      "Effects": {
        "ItemAnimationId": "Consume"
      }
    }]
  }
}
```

The food tier templates (`Consume_Charge_Food_T1` / `_T2` / `_T3`) compose this via `Type: "Serial"` interactions that `Replace` the `ConsumeSFX` and `Consume_Charge` vars with their defaults. The `_Inner` charge interaction then hangs the payload off its hold-time threshold (`"2.5"` for all three tiers as of 0.7.2), which fires a `ModifyInventory` to eat the item and then `Replace`s `ConsumedSFX` and `Effect`.

Potions use the same shape with the charge inline rather than in a `*_Inner` file:
`Consume_Charge_Potion_Fastest` (0.5s), `Consume_Charge_Potion_Fast` (1.5s, the default), and
`Consume_Charge_Potion_Slow` (3.0s).

### ModifyInventory Interaction

Removes the consumed item from the stack in hand:

```json
{
  "Type": "ModifyInventory",
  "AdjustHeldItemQuantity": -1
}
```

This is what the shipped consume chains actually use. `ModifyInventory` accepts
`ItemToRemove` / `ItemToAdd` (each an `ItemStack` object with `Id`, `Quantity`, `Durability`,
`MaxDurability`, `QualityOverride`, `Metadata`, `OverrideDroppedItemAnimation`; 0.7.2 renamed
the `ItemStack` key `Quality` to `QualityOverride`), `AdjustHeldItemQuantity`,
`AdjustHeldItemDurability`, `BrokenItem`, `NotifyOnBreak`, `NotifyOnBreakMessage`, and
`RequiredGameMode`. There is **no** `"Self": true` shorthand — use
`AdjustHeldItemQuantity: -1` to consume the held stack.

### RemoveEffect / ClearEntityEffect Interaction

Clears active effects. Antidotes use `ClearEntityEffect` keyed on `EntityEffectId`, chaining additional removals through `Next`:

```json
{
  "Type": "ClearEntityEffect",
  "EntityEffectId": "Poison_T1",
  "Next": {
    "Type": "ClearEntityEffect",
    "EntityEffectId": "Poison_T2"
  }
}
```

Potion templates also expose a `RemoveEffect` var that defaults to a no-op (`{ "Type": "Simple" }`) so children can override it when they need to strip an effect on consumption.

---

## Creating Custom Consumables

### Custom Food Item

```json
{
  "Parent": "Template_Food",
  "TranslationProperties": {
    "Name": "server.items.My_Custom_Food.name"
  },
  "Icon": "Icons/ItemsGenerated/My_Food.png",
  "Quality": "Uncommon",
  "MaxStack": 25,
  "InteractionVars": {
    "Consume_Charge": {
      "Interactions": [{
        "Parent": "Consume_Charge_Food_T1_Inner",
        "Effects": {
          "ItemAnimationId": "Consume"
        }
      }]
    },
    "Effect": {
      "Interactions": [
        {
          "Type": "ApplyEffect",
          "EffectId": "Food_Instant_Heal_T1"
        },
        {
          "Type": "ApplyEffect",
          "EffectId": "Meat_Buff_T1"
        }
      ]
    }
  }
}
```

> **Try it:** [`examples/custom-food`](../examples/custom-food/) is a complete, no-code, no-art **pack** built from exactly this pattern — a runnable copy of a custom food item with a beginner walkthrough of every field.

### Custom Potion Item

```json
{
  "Parent": "Potion_Template",
  "TranslationProperties": {
    "Name": "server.items.My_Custom_Potion.name"
  },
  "Icon": "Icons/ItemsGenerated/My_Potion.png",
  "Quality": "Rare",
  "MaxStack": 10,
  "InteractionVars": {
    "Effect": {
      "Interactions": [{
        "Type": "StatsCondition",
        "Costs": { "Health": 100 },
        "ValueType": "Percent",
        "LessThan": true,
        "Next": {
          "Type": "ApplyEffect",
          "EffectId": "My_Custom_Buff"
        }
      }]
    }
  }
}
```

Two things to note against older examples of this pattern: the stat gate goes **inside the
`Effect` var** (the stock consume chain never `Replace`s a `Stat_Check` var — see the gotcha
[above](#stat-check-condition)), and the buff's duration normally lives on `My_Custom_Buff`'s
own effect asset under `Server/Entity/Effects/`. From 0.7.2 an `ApplyEffect` `Duration` can
override it per item.

---

## Related Documentation

- [Items Reference](items.md) - Common properties and systems
- [Effects & Stats](effects-stats.md) - Status effects and stat modifiers
- [Interactions API](interactions.md) - ApplyEffect, ChangeStat, ModifyInventory
- [Weapons Reference](items-weapons.md) - Combat items
- [Tools Reference](items-tools.md) - Gathering tools
