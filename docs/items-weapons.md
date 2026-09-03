---
title: "Weapon Items"
description: "Define Hytale weapons in JSON — Template_Weapon families with signature abilities, Primary/Secondary/Ability interaction slots, weapon stats, dual-wield rendering, and damage overrides."
seo:
  type: TechArticle
---

# Weapon Items

**Doc type:** JSON asset format · **Assets:** `Server/Item` · **Verified against 0.5.9**

> Part of the [Items API](items.md). For common item properties, see [Items Reference](items.md#common-properties).

This page documents weapon items — swords, daggers, shields, battleaxes, bows, maces, and crossbows — each built from a formal `Template_Weapon_*` with combo interactions, signature abilities, and per-tier damage overrides.

## Overview

Defined as JSON assets under `Server/Item` and covers:
- One `Template_Weapon_*` per weapon family, each with its signature ability
- Interaction slots: `Primary` (combo), `Secondary` (guard/aim), `Ability1` (signature)
- `Weapon` stats (stat modifiers, dual-wield rendering) and `Tags`
- Per-item damage overrides via `InteractionVars` and damage scaling by tier
- Charge- and ammo-based mechanics (bows, crossbows) including the reload system
- Signature-ready appearance/effects and common patterns (damage calculator, stamina cost, blocked effects)

## Architecture
```
Weapon item (inherits a Template_Weapon_* template)
├── Templates
│   ├── Template_Weapon_Sword (Vortexstrike)
│   ├── Template_Weapon_Daggers (Razorstrike)
│   ├── Template_Weapon_Shield (bash)
│   ├── Template_Weapon_Battleaxe (Whirlwind)
│   ├── Template_Weapon_Shortbow (Volley)
│   ├── Template_Weapon_Mace (Groundslam)
│   └── Template_Weapon_Crossbow (BigArrow)
├── Interactions (Primary combo / Secondary guard / Ability1 signature)
├── Weapon stats + Tags (Type / Family)
├── InteractionVars (per-item damage, guard, charge overrides)
└── Ranged mechanics (charge, ammo consumption, reload)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Template_Weapon_Sword` | `Server/Item/Items/Weapon/Sword/Template_Weapon_Sword.json` | Sword template; 4-hit combo + Vortexstrike |
| `Template_Weapon_Daggers` | `Server/Item/Items/Weapon/...` | Dual-wield daggers + Razorstrike |
| `Template_Weapon_Shield` | `Server/Item/Items/Weapon/...` | Defensive shield with bash |
| `Template_Weapon_Battleaxe` | `Server/Item/Items/Weapon/...` | Two-handed battleaxe + Whirlwind |
| `Template_Weapon_Shortbow` | `Server/Item/Items/Weapon/...` | Charged bow + Volley |
| `Template_Weapon_Mace` | `Server/Item/Items/Weapon/...` | Blunt mace + Groundslam |
| `Template_Weapon_Crossbow` | `Server/Item/Items/Weapon/...` | Ammo-based crossbow + BigArrow |
| `Weapon` | item property | Wield stats and dual-wield rendering |

## Quick Navigation

| Template | Children | Signature Ability | Description |
|----------|----------|-------------------|-------------|
| [Template_Weapon_Sword](#template_weapon_sword) | 24 | Vortexstrike | One-handed blade with combo swings |
| [Template_Weapon_Daggers](#template_weapon_daggers) | 17 | Razorstrike | Dual-wielded fast attacks |
| [Template_Weapon_Shield](#template_weapon_shield) | 16 | - | Defensive blocking with bash |
| [Template_Weapon_Battleaxe](#template_weapon_battleaxe) | 16 | Whirlwind | Heavy two-handed sweeping attacks |
| [Template_Weapon_Shortbow](#template_weapon_shortbow) | 20 | Volley | Charged arrow shots |
| [Template_Weapon_Mace](#template_weapon_mace) | 13 | Groundslam | Heavy blunt weapon |
| [Template_Weapon_Crossbow](#template_weapon_crossbow) | 3 | BigArrow | Ammo-based ranged weapon |

(Counts are the `.json` files in each family directory, template included.)

These seven are the **only** `Template_Weapon_*` assets in the game. The other weapon
directories under `Server/Item/Items/Weapon/` — `Axe`, `Blowgun`, `Bomb`, `Claws`, `Club`,
`Dart`, `Deployable`, `Flamethrower`, `Gun`, `Kunai`, `Longsword`, `Spear`, `Spellbook`,
`Staff`, `Wand`, plus `Arrow` and `_Debug` — have no `Template_Weapon_*` parent: each item
declares its own `Interactions` and stats directly (a few chain off a sibling item via a
top-level `Parent`, e.g. `Weapon_Longsword_Praetorian`).

---

## Handedness (one- vs two-handed)

There is **no one/two-handed flag in item JSON**, and **no "TwoHanded" concept anywhere in
`HytaleServer.jar`**. "Two-handed" is purely descriptive — it is determined by the weapon's animation
rig (`PlayerAnimationsId`): `Staff`, `Bow`, `Crossbow`, `Spear`, `Battleaxe`, and `Rifle` read as
two-handed; `Sword`, `Club`, `Mace`, `Daggers`, `Wand`, and `Spellbook` read as one-handed.

A player **can equip** an offhand shield alongside any main-hand weapon, but can only **block with**
it when the main-hand weapon is one-handed; held two-handed, the offhand shield is equipped-but-unusable.
This offhand-block gate is **not** reachable from the server: overriding a two-handed weapon's
`PlayerAnimationsId` to a one-handed rig (e.g. `Staff` → `Wand`) does **not** re-enable offhand blocking,
and the server jar has no handedness logic — the gate is almost certainly **hardcoded client-side**.
Don't chase it from a plugin or server asset.

(Shields are themselves main-hand items — `Template_Weapon_Shield`, Primary = punch, Secondary =
guard/bash — so a player holds *either* a shield as the active weapon, *or* a weapon plus an offhand shield.)

---

## Template_Weapon_Sword

**Location:** `Server/Item/Items/Weapon/Sword/Template_Weapon_Sword.json`

One-handed sword with a 4-hit combo chain (left swing, right swing, down swing, thrust) and the Vortexstrike signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 15 |
| `PlayerAnimationsId` | Sword |
| `Reticle` | DefaultMelee |
| `MaxDurability` | 80 |
| `DurabilityLossOnHit` | 0.21 |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapons_Blade_Large |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Weapon_Sword_Primary | 4-hit combo chain |
| `Secondary` | Root_Weapon_Sword_Secondary_Guard | Blocking stance |
| `Ability1` | Root_Weapon_Sword_Signature_Vortexstrike | Spinning slash + thrust |

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Sword"]
  }
}
```

### Weapon Stats

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 20,
        "CalculationType": "Additive"
      }]
    }
  }
}
```

Grants 20 maximum SignatureEnergy when equipped. Clears SignatureEnergy when unequipped.

### InteractionVars

Child items must provide these variables to customize damage:

| Variable | Purpose |
|----------|---------|
| `Swing_Left_Damage` | Damage for first combo hit |
| `Swing_Right_Damage` | Damage for second combo hit |
| `Swing_Down_Damage` | Damage for third combo hit |
| `Thrust_Damage` | Damage for fourth combo hit (grants SignatureEnergy) |
| `Vortexstrike_Spin_Damage` | Damage per hit during signature spin |
| `Vortexstrike_Stab_Damage` | Damage for signature thrust finisher |
| `Guard_Wield` | Stamina cost for blocking |

### Example Child: Iron Sword

```json
{
  "Parent": "Template_Weapon_Sword",
  "TranslationProperties": {
    "Name": "server.items.Weapon_Sword_Iron.name"
  },
  "Model": "Items/Weapons/Sword/Iron.blockymodel",
  "Texture": "Items/Weapons/Sword/Iron_Texture.png",
  "Icon": "Icons/ItemsGenerated/Weapon_Sword_Iron.png",
  "Quality": "Uncommon",
  "ItemLevel": 20,
  "MaxDurability": 120,
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
  },
  "InteractionVars": {
    "Swing_Left_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Left_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 10 } },
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Sword_T2_Impact",
          "LocalSoundEventId": "SFX_Sword_T2_Impact"
        }
      }]
    },
    "Swing_Right_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Right_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 10 } },
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Sword_T2_Impact",
          "LocalSoundEventId": "SFX_Sword_T2_Impact"
        }
      }]
    },
    "Swing_Down_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Down_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 18 } },
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Sword_T2_Impact",
          "LocalSoundEventId": "SFX_Sword_T2_Impact"
        }
      }]
    },
    "Thrust_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Thrust_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 26 } },
        "EntityStatsOnHit": [{ "EntityStatId": "SignatureEnergy", "Amount": 3 }],
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Sword_T2_Impact",
          "LocalSoundEventId": "SFX_Sword_T2_Impact"
        }
      }]
    },
    "Vortexstrike_Spin_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Signature_Vortexstrike_Spin_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 19 } },
        "EntityStatsOnHit": [],
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Sword_T2_Impact",
          "LocalSoundEventId": "SFX_Sword_T2_Impact"
        }
      }]
    },
    "Vortexstrike_Stab_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Signature_Vortexstrike_Stab_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 56 } },
        "EntityStatsOnHit": [],
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Sword_T2_Impact",
          "LocalSoundEventId": "SFX_Sword_T2_Impact"
        }
      }]
    },
    "Guard_Wield": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Secondary_Guard_Wield",
        "StaminaCost": { "Value": 10, "CostType": "Damage" }
      }]
    }
  },
  "MaxDurability": 120,
  "DurabilityLossOnHit": 0.21
}
```

> `BenchRequirement` entries also accept `RequiredTierLevel` (int) and, as of 0.6.3,
> `RequiredAugmentTags` (string array) alongside `Type`, `Id`, and `Categories`.
> See [Crafting Items](items-crafting.md) for the full recipe schema.

### Damage Scaling by Tier

| Sword | Quality | ItemLevel | Swing L/R | Swing Down | Thrust | Vortex Spin | Vortex Stab |
|-------|---------|-----------|-----------|------------|--------|-------------|-------------|
| Crude | Common | 3 | 6/6 | 11 | 16 | 12 | 35 |
| Copper | Common | 10 | 8/8 | 14 | 21 | 15 | 44 |
| Scrap / Steel_Rusty / Bronze | Uncommon | 15-25 | 9/9 | 16 | 24 | 17 | 50 |
| Iron | Uncommon | 20 | 10/10 | 18 | 26 | 19 | 56 |
| Stone_Trork | Uncommon | 25 | 11/11 | 20 | 30 | 21 | 63 |
| Bone / Cobalt / Doomed / Thorium | Rare | 25-30 | 12/12 | 22 | 32 | 23 | 70 |
| Adamantite | Rare | 40 | 14/14 | 28 | 41 | 29 | 87 |
| Mithril / Onyxium | Epic | 50 | 18/18 | 34 | 51 | 37 | 110 |

Left and right swings carry the *same* base damage on every stock sword; the combo's
escalation comes from the down swing and thrust.

### All Sword Variants

Weapon_Sword_Adamantite, Weapon_Sword_Bone, Weapon_Sword_Bronze, Weapon_Sword_Bronze_Ancient, Weapon_Sword_Cobalt, Weapon_Sword_Copper, Weapon_Sword_Crude, Weapon_Sword_Cutlass, Weapon_Sword_Doomed, Weapon_Sword_Frost, Weapon_Sword_Iron, Weapon_Sword_Mithril, Weapon_Sword_Nexus, Weapon_Sword_Onyxium, Weapon_Sword_Runic, Weapon_Sword_Scrap, Weapon_Sword_Silversteel, Weapon_Sword_Steel, Weapon_Sword_Steel_Incandescent, Weapon_Sword_Steel_Rusty, Weapon_Sword_Stone_Trork, Weapon_Sword_Thorium, Weapon_Sword_Wood

---

## Template_Weapon_Daggers

**Location:** `Server/Item/Items/Weapon/Daggers/Template_Weapon_Daggers.json`

Dual-wielded daggers with fast attacks and the Razorstrike signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 30 |
| `PlayerAnimationsId` | Daggers |
| `Reticle` | DefaultMelee |
| `MaxDurability` | 80 |
| `DurabilityLossOnHit` | 0.1 |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapon_Blade_Small |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Weapon_Daggers_Primary | Fast dual-wield attacks |
| `Secondary` | Root_Weapon_Daggers_Secondary_Guard | Blocking stance |
| `Ability1` | Root_Weapon_Daggers_Signature_Razorstrike | Rapid slash combo |

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Dagger"]
  }
}
```

### Weapon Stats

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 27,
        "CalculationType": "Additive"
      }]
    },
    "RenderDualWielded": true
  }
}
```

`RenderDualWielded: true` causes the item to render in both hands.

### Signature Ready Effects

Daggers display particles on both the primary and secondary item when signature energy is full
(abridged — the real template repeats three systems per hand):

```json
{
  "ItemAppearanceConditions": {
    "SignatureEnergy": [{
      "Condition": [100, 100],
      "ConditionValueType": "Percent",
      "Particles": [
        {
          "SystemId": "Daggers_Signature_Ready",
          "TargetNodeName": "Handle",
          "PositionOffset": { "X": 0.5 },
          "TargetEntityPart": "PrimaryItem"
        },
        {
          "SystemId": "Daggers_Signature_Ready",
          "TargetNodeName": "Handle",
          "PositionOffset": { "X": 0.5 },
          "TargetEntityPart": "SecondaryItem"
        }
      ],
      "ModelVFXId": "Sword_Signature_Status",
      "FirstPersonParticles": [
        {
          "SystemId": "Daggers_Signature_Ready",
          "TargetNodeName": "Handle",
          "PositionOffset": { "X": 0.5 },
          "TargetEntityPart": "PrimaryItem"
        }
      ]
    }]
  }
}
```

`TargetEntityPart` selects which held item the particle attaches to (`PrimaryItem` /
`SecondaryItem`), `ModelVFXId` applies a shader effect to the model itself, and
`FirstPersonParticles` is a separate list rendered only in the wielder's own view.

---

## Template_Weapon_Shield

**Location:** `Server/Item/Items/Weapon/Shield/Template_Weapon_Shield.json`

Defensive shield with blocking and shield bash. No signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 40 |
| `PlayerAnimationsId` | Shield |
| `Reticle` | DefaultMelee |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapons_Shield_Metal |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Unarmed_Attack_Swing_Left | Unarmed punch (shield doesn't attack) |
| `Secondary` | Root_Weapon_Shield_Secondary_Guard | Blocking + bash on release |

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Shield"]
  }
}
```

### InteractionVars

Shield templates define guard behavior directly in the template:

| Variable | Purpose |
|----------|---------|
| `Guard_Start_StaminaCost` | Stamina cost to begin guarding |
| `Guard_Wield` | Active blocking configuration |
| `Guard_Bash` | Shield bash attack on guard release |
| `Guard_Bash_Damage` | Damage dealt by shield bash |

### Template InteractionVars

```json
{
  "InteractionVars": {
    "Guard_Start_StaminaCost": {
      "Interactions": [{
        "Type": "ChangeStat",
        "StatModifiers": { "Stamina": -0.5 }
      }]
    },
    "Guard_Wield": {
      "Interactions": [{
        "Parent": "Weapon_Shield_Secondary_Guard_Wield",
        "Effects": {
          "WorldSoundEventId": "SFX_Shield_T2_Raise",
          "LocalSoundEventId": "SFX_Shield_T2_Raise_Local"
        },
        "StaminaCost": { "Value": 12, "CostType": "Damage" },
        "BlockedEffects": {
          "WorldSoundEventId": "SFX_Shield_T2_Impact"
        }
      }]
    },
    "Guard_Bash": {
      "Interactions": [
        { "Type": "ApplyEffect", "EffectId": "Stamina_Broken_Immune" },
        {
          "Parent": "Weapon_Shield_Secondary_Guard_Bash",
          "Effects": {
            "WorldSoundEventId": "SFX_Shield_T2_Swing",
            "LocalSoundEventId": "SFX_Shield_T2_Swing_Local"
          },
          "StatModifiers": { "Stamina": -2 }
        }
      ]
    },
    "Guard_Bash_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Shield_Secondary_Guard_Bash_Damage",
        "DamageEffects": {
          "WorldSoundEventId": "SFX_Shield_T2_Impact",
          "LocalSoundEventId": "SFX_Shield_T2_Impact"
        }
      }]
    }
  }
}
```

---

## Template_Weapon_Battleaxe

**Location:** `Server/Item/Items/Weapon/Battleaxe/Template_Weapon_Battleaxe.json`

Heavy two-handed axe with sweeping attacks and the Whirlwind signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 15 |
| `PlayerAnimationsId` | Battleaxe |
| `Reticle` | DefaultMelee |
| `MaxDurability` | 80 |
| `DurabilityLossOnHit` | 0.45 |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapon_Blunt_Large |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Weapon_Battleaxe_Primary | Heavy sweeping attacks |
| `Secondary` | Root_Weapon_Battleaxe_Secondary_Guard | Blocking stance |
| `Ability1` | Root_Weapon_Battleaxe_Signature_Whirlwind | Spinning AOE attack |

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"]
  }
}
```

Note: Battleaxe only has `Type` tag, no `Family` tag in the template.

### Weapon Stats

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 9,
        "CalculationType": "Additive"
      }]
    }
  }
}
```

---

## Template_Weapon_Shortbow

**Location:** `Server/Item/Items/Weapon/Shortbow/Template_Weapon_Shortbow.json`

Ranged bow with charge-based damage scaling and the Volley signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 5 |
| `PlayerAnimationsId` | Bow |
| `Reticle` | DefaultMelee |
| `MaxDurability` | 80 |
| `DurabilityLossOnHit` | 0.58 |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapons_Wood |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Weapon_Shortbow_Primary_Shoot | Charged arrow shot |
| `Secondary` | Root_Weapon_Shortbow_Secondary_Guard | Blocking with bow |
| `Ability1` | Root_Weapon_Shortbow_Signature_Volley | Triple arrow volley |
| `SwapFrom` | *(inline interaction list)* | Refunds a nocked arrow and clears `StaminaRegenDelay` on weapon swap |

Unlike the other slots, the shortbow's `SwapFrom` is not a root-interaction id — it is an
inline `{ "Interactions": [ … ] }` list written directly in the template.

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Bow"]
  }
}
```

### Weapon Stats

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy", "SignatureCharges", "Ammo"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 6,
        "CalculationType": "Additive"
      }],
      "SignatureCharges": [{
        "Amount": 1,
        "CalculationType": "Additive"
      }],
      "Ammo": [{
        "Amount": 1,
        "CalculationType": "Additive"
      }]
    }
  }
}
```

Shortbow uses SignatureEnergy and SignatureCharges for its volley ability, plus a
single-slot `Ammo` stat (below) for the nocked arrow.

### Arrow Consumption (as of 0.6.3)

The shortbow now tracks the nocked arrow through an `Ammo` stat with a maximum of 1, and the
whole arrow economy is gated on `"RequiredGameMode": "Adventure"` — in Creative the bow costs
nothing. Drawing the bow (`Weapon_Shortbow_Primary_Shoot`) runs a `ModifyInventory` that
removes one `Weapon_Arrow_Crude` and banks it as `Ammo: 1`; the chain ends in a
`StatsCondition` that refunds any `Ammo` still held (the shot never fired) as an arrow item.
With no arrow in the inventory the `ModifyInventory` fails and the `No_Ammo_Effects` var
runs instead (default `Common_Bow_No_Ammo`). The template's `SwapFrom` performs the same
refund when the player switches weapons mid-draw:

```json
{
  "SwapFrom": {
    "Interactions": [
      {
        "Type": "StatsCondition",
        "Costs": { "Ammo": 1 },
        "Next": {
          "Type": "ModifyInventory",
          "RequiredGameMode": "Adventure",
          "ItemToAdd": { "Id": "Weapon_Arrow_Crude", "Quantity": 1 },
          "Next": {
            "Type": "ChangeStat",
            "Behaviour": "Set",
            "StatModifiers": { "StaminaRegenDelay": -1 }
          }
        }
      },
      { "Type": "ChangeActiveSlot" }
    ]
  }
}
```

The same "spend an item, bank it as a stat, refund the stat on swap" pattern the crossbow
uses — see the [ammo/arrow gotcha](#template_weapon_crossbow) below, which applies here too.

### Charge-Based Damage

Shortbow damage scales with charge time. The thresholds live in
`Weapon_Shortbow_Primary_Shoot_Charge` (`"Type": "Charging"`), whose `Next` map is keyed by
hold time in seconds; each entry replaces the `Primary_Shoot_Strength_N` var:

| Charge Level | Charge Time | Damage (Template) |
|--------------|-------------|-------------------|
| *(none)* | 0.0s | released too early — no shot |
| Strength_0 | 0.1s | 6 Projectile |
| Strength_1 | 0.3s | 10 Projectile |
| Strength_2 | 0.6s | 12 Projectile |
| Strength_3 | 0.9s | 14 Projectile |
| Strength_4 | 1.2s+ (full) | 15 Projectile |
| Signature Volley | - | 25 Projectile |

The charge interaction also sets `AllowIndefiniteHold: true` and
`HorizontalSpeedMultiplier: 0.67` (the template overrides the latter to `0.667`).

### InteractionVars

| Variable | Purpose |
|----------|---------|
| `Primary_Shoot_Charge` | Charge-up effects and movement speed |
| `Primary_Shoot_Strength_0` through `_4` | Launch effects per charge level |
| `Primary_Shoot_Damage_Strength_0` through `_4` | Damage per charge level |
| `Primary_Shoot_Impact_Strength_0` through `_4` | Hit effects per charge level |
| `Primary_Shoot_Miss_Strength_0` through `_4` | Miss effects per charge level |
| `Signature_Activate_Effects` | Sound when signature activates |
| `Signature_Volley_Charge` | Volley charge-up |
| `Signature_Volley_Effects` | Volley launch effects |
| `Signature_Volley_Damage` | Volley arrow damage |
| `Signature_Volley_Impact` | Volley hit effects |
| `Signature_Volley_Miss` | Volley miss effects |
| `Guard_*` | Blocking configuration |

### Signature Ready Appearance

When SignatureCharges >= 1, the bow model changes to show three arrows:

```json
{
  "ItemAppearanceConditions": {
    "SignatureCharges": [{
      "Condition": [1, 100],
      "ConditionValueType": "Percent",
      "Model": "Items/Weapons/Bow/Iron_Triple.blockymodel",
      "Texture": "Items/Weapons/Bow/Iron_Texture.png",
      "LocalSoundEventId": "SFX_Bow_T2_Signature_Loop_Local",
      "WorldSoundEventId": "SFX_Bow_T2_Signature_Loop",
      "Particles": [
        { "SystemId": "Bow_Signature_Charge", "TargetNodeName": "ARROW-PLACEHOLDER", "PositionOffset": { "X": 0.5, "Y": 0.25, "Z": 0 }, "Scale": 0.5, "TargetEntityPart": "PrimaryItem" },
        { "SystemId": "Bow_Signature_Charge", "TargetNodeName": "ARROW-PLACEHOLDER", "PositionOffset": { "X": 0.5, "Y": 0, "Z": 0 }, "Scale": 0.5, "TargetEntityPart": "PrimaryItem" },
        { "SystemId": "Bow_Signature_Charge", "TargetNodeName": "ARROW-PLACEHOLDER", "PositionOffset": { "X": 0.5, "Y": -0.25, "Z": 0 }, "Scale": 0.5, "TargetEntityPart": "PrimaryItem" }
      ],
      "ModelVFXId": "Bow_Signature_Status"
    }]
  }
}
```

The template also carries a second `ItemAppearanceConditions` entry keyed on
`SignatureEnergy` at `[100, 100]`, which adds the shared `Sword_Signature_Ready` particles.

---

## Template_Weapon_Mace

**Location:** `Server/Item/Items/Weapon/Mace/Template_Weapon_Mace.json`

Heavy blunt weapon with the Groundslam signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `ItemLevel` | 40 |
| `PlayerAnimationsId` | Mace |
| `Reticle` | MaceMelee |
| `MaxDurability` | 80 |
| `DurabilityLossOnHit` | 0.5 |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapon_Blunt_Large |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Primary` | Root_Weapon_Mace_Primary | Heavy blunt attacks |
| `Secondary` | Root_Weapon_Mace_Secondary_Guard | Blocking stance |
| `Ability1` | Root_Weapon_Mace_Signature_Groundslam | AOE ground pound |

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Mace"]
  }
}
```

### Weapon Stats

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 8,
        "CalculationType": "Additive"
      }]
    }
  }
}
```

---

## Template_Weapon_Crossbow

**Location:** `Server/Item/Items/Weapon/Crossbow/Template_Weapon_Crossbow.json`

Ammo-based ranged weapon with reload mechanics and the BigArrow signature ability.

### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `PlayerAnimationsId` | Crossbow |
| `Reticle` | DefaultMelee |
| `MaxDurability` | 80 |
| `DurabilityLossOnHit` | 0.28 |
| `Categories` | Items.Weapons |
| `ItemSoundSetId` | ISS_Weapons_Wood |
| `Consumable` | false |
| `ClipsGeometry` | false |

### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `SwapFrom` | Root_Weapon_Crossbow_Swap_From | Triggered when switching away |
| `Primary` | Root_Weapon_Crossbow_Primary_Signature | Fire loaded bolt |
| `Secondary` | Root_Weapon_Crossbow_Secondary_Guard | Blocking stance |
| `Ability1` | Root_Weapon_Crossbow_Signature_BigArrow | Powerful charged shot |
| `Ability3` | Root_Common_StatAmmoReload_Entry | Reload ammo |

### Tags

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Crossbow"]
  }
}
```

### Weapon Stats

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy", "SignatureCharges", "Ammo"],
    "StatModifiers": {
      "Ammo": [{
        "Amount": 6,
        "CalculationType": "Additive"
      }],
      "SignatureEnergy": [{
        "Amount": 5,
        "CalculationType": "Additive"
      }],
      "SignatureCharges": [{
        "Amount": 1,
        "CalculationType": "Additive"
      }]
    }
  }
}
```

Crossbow manages three stats:
- **Ammo** (max 6): Bolts currently loaded
- **SignatureEnergy** (max 5): Energy for signature ability
- **SignatureCharges** (max 1): Signature ready state

> **Ammo and arrow items are interchangeable currency — inflating `Ammo` dupes arrows.** Each shot
> spends one `Ammo` stat (granted 6 on equip via `Weapon.StatModifiers`); reloading **converts arrow
> items → Ammo** (`Reload_ItemConsume` → `Common_StatAmmoReload_ItemConsume`, a `ModifyInventory`
> removing `Weapon_Arrow_Crude`); and `SwapFrom` (`Weapon_Crossbow_Swap_From`) **refunds leftover Ammo
> back into arrow items** on weapon swap — a `StatsCondition` ladder testing `Ammo` 6 down to 1 and
> adding that many arrows. So raising the `Ammo` grant to fake "infinite ammo" lets a
> player swap weapons to harvest the surplus as real arrows. The safe approach is to make *reload*
> free — drop the arrow `ModifyInventory` from the reload chain — rather than inflating `Ammo`.
>
> The entire chain is wrapped in `"RequiredGameMode": "Adventure"`, so none of it costs or
> refunds anything in Creative.

### DisplayEntityStatsHUD

```json
{
  "DisplayEntityStatsHUD": ["Ammo"]
}
```

Displays the Ammo stat on the HUD when wielding.

### InteractionVars

| Variable | Purpose |
|----------|---------|
| `Arrow_Inventory_Condition` | Checks/consumes arrows from inventory |
| `Standard_Projectile_Launch` | Normal shot launch |
| `Standard_Projectile_Damage` | Normal shot damage (3 Projectile) |
| `Standard_Projectile_Impact` | Normal shot hit effects |
| `Standard_Projectile_Miss` | Normal shot miss effects |
| `No_Ammo_Effects` | Effects when firing with no ammo |
| `Combo_Projectile_Damage` | Combo shot damage (9 Projectile) |
| `Overcharge_Start` | Overcharge ability startup |
| `Overcharge_Projectile_Launch` | Overcharge shot launch |
| `Reload_Start` | Begin reload sequence |
| `Reload_ItemConsume` | Consume arrow per reload iteration |
| `Reload_Effects` | Reload animation/sound effects |
| `Reload_StatModifier` | Grant Ammo stat per reload |
| `Signature_Activate_Effects` | Sound/VFX when the signature activates |
| `Signature_BigArrow_Launch` | BigArrow projectile launch |
| `Signature_BigArrow_Damage` | BigArrow damage |
| `Signature_BigArrow_Miss` | BigArrow miss effects |
| `Guard_Start_StaminaCost` | Stamina cost to begin guarding |
| `Guard_Wield` | Active blocking configuration |
| `Guard_Bash` | Bash on guard release |
| `Guard_Bash_Damage` | Bash damage |

### Ammo Consumption

The crossbow consumes `Weapon_Arrow_Crude` items from inventory (Adventure mode only):

```json
{
  "Arrow_Inventory_Condition": {
    "Interactions": [{
      "Type": "ModifyInventory",
      "RequiredGameMode": "Adventure",
      "ItemToRemove": {
        "Id": "Weapon_Arrow_Crude",
        "Quantity": 1
      }
    }]
  }
}
```

### Reload System

```json
{
  "Reload_ItemConsume": {
    "Interactions": [{
      "Parent": "Common_StatAmmoReload_ItemConsume",
      "ItemToRemove": {
        "Id": "Weapon_Arrow_Crude",
        "Quantity": 1
      }
    }]
  },
  "Reload_StatModifier": {
    "Interactions": [{
      "Parent": "Common_StatAmmoReload_StatModifier",
      "HorizontalSpeedMultiplier": 0.75,
      "EffectId": {
        "StatModifiers": { "Ammo": 1 }
      }
    }]
  }
}
```

---

## Common Weapon Patterns

### Damage Calculator

All weapon damage uses `DamageCalculator` with `BaseDamage`:

```json
{
  "DamageCalculator": {
    "BaseDamage": {
      "Physical": 10
    }
  }
}
```

`DamageCalculator` accepts five keys:

| Key | Type | Description |
|-----|------|-------------|
| `BaseDamage` | object | Map of damage-cause id → amount |
| `Type` | enum | `Absolute` (default) or `Dps` — whether `BaseDamage` is a flat amount or a per-second rate scaled by the interaction's duration |
| `Class` | enum | `Unknown` (default), `Light`, `Charged`, or `Signature` — the damage class used for resistance/animation bucketing |
| `SequentialModifierStep` | float | Per-hit falloff applied when one interaction damages several targets in sequence |
| `SequentialModifierMinimum` | float | Floor for that falloff |
| `RandomPercentageModifier` | float | Random ± spread applied to the rolled damage |

The `BaseDamage` keys are `DamageCause` asset ids from `Server/Entity/Damage/`
— `Bludgeoning`, `Command`, `Drowning`, `Elemental`, `Environment`, `Environmental`, `Fall`,
`Fire`, `Ice`, `OutOfWorld`, `Physical`, `Poison`, `Projectile`, `Slashing`, `Suffocation`.
Weapons overwhelmingly use two:
- `Physical` - Melee weapon damage
- `Projectile` - Ranged weapon damage

The shared base interactions (e.g. `Weapon_Sword_Primary_Swing_Left_Damage`) set only
`"DamageCalculator": { "Class": "Light" }` — no `BaseDamage` — which is why a sword that
supplies no `InteractionVars` override does no configured weapon damage.

### Stamina Cost for Blocking

```json
{
  "StaminaCost": {
    "Value": 10,
    "CostType": "Damage"
  }
}
```

`StaminaCost` has exactly two keys, and `CostType` has exactly two values (there is no
"flat" mode — the cost is always proportional to the damage blocked):

| CostType | Meaning | `Value` |
|----------|---------|---------|
| `MaxHealthPercentage` (default) | `Value` is the fraction of the blocker's **max health** that one stamina point absorbs | ratio, e.g. `0.04` for 4%. Default `0.04` |
| `Damage` | `Value` is the raw **damage** that one stamina point absorbs | flat damage, e.g. `10` |

Stamina consumed is `damage / Value` for `Damage`, and
`damage / (Value × maxHealth)` for `MaxHealthPercentage`. The stock weapon templates all use
`"CostType": "Damage"`. Enum values in item JSON are written in CamelCase and matched
**exactly** — `"DAMAGE"` fails to decode.

### Blocked Effects

Sound played when successfully blocking:

```json
{
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Shield_T2_Impact"
  }
}
```

### Entity Stats On Hit

Grant stats to attacker on successful hit:

```json
{
  "EntityStatsOnHit": [{
    "EntityStatId": "SignatureEnergy",
    "Amount": 3
  }]
}
```

### Impact Sounds (and silent weapons)

`InteractionVars` is where per-item **impact sounds** are injected, not just damage. Each damage
interaction's `DamageEffects` carries `WorldSoundEventId` (spatial, heard by all nearby) and
`LocalSoundEventId` (only the attacker), exactly as in the [Iron Sword example](#example-child-iron-sword).

The shared `Weapon_Sword_Primary_*_Damage` interactions (and the common `DamageEntityParent`) carry
**no** sound of their own, so a weapon that doesn't override `DamageEffects` in its `InteractionVars`
is **silent on hit**. As of 0.6.3 eight stock swords ship with an empty `InteractionVars`
block — so they also get no `BaseDamage` — Cutlass, Frost, Nexus, Runic, Silversteel, Steel,
Steel_Incandescent, and Wood. If you base a weapon on one of those and want an impact sound
(or any tier damage at all), add a `DamageEffects` and `DamageCalculator` block per combo
hit. (The exact list is version-specific.)

To play a sound from Java instead of JSON, see [Audio → Playing Sounds from Java](audio.md#playing-sounds-from-java).

---

## Sound Sets

| ItemSoundSetId | Weapon Types |
|----------------|--------------|
| `ISS_Weapons_Blade_Large` | Swords |
| `ISS_Weapon_Blade_Small` | Daggers |
| `ISS_Weapons_Shield_Metal` | Shields |
| `ISS_Weapon_Blunt_Large` | Battleaxes, Maces |
| `ISS_Weapons_Wood` | Bows, Crossbows |

---

## Related Documentation

- [Items Reference](items.md) - Common properties and systems
- [Interactions API](interactions.md) - Combat interactions
- [Combat Interactions](interactions-combat.md) - DamageEntity, Selector, ApplyForce
- [Combo Interactions](interactions-combo.md) - ChainingInteraction, ChargingInteraction
- [Effects & Stats](effects-stats.md) - Status effects and stat modifiers
