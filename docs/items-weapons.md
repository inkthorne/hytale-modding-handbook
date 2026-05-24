# Weapon Items

**Doc type:** JSON asset format · **Assets:** `Server/Item` · **Verified against build-12**

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
| [Template_Weapon_Shortbow](#template_weapon_shortbow) | 19 | Volley | Charged arrow shots |
| [Template_Weapon_Mace](#template_weapon_mace) | 13 | Groundslam | Heavy blunt weapon |
| [Template_Weapon_Crossbow](#template_weapon_crossbow) | 3 | BigArrow | Ammo-based ranged weapon |

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
        "DamageCalculator": { "BaseDamage": { "Physical": 9 } },
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
  }
}
```

### Damage Scaling by Tier

| Sword | Quality | ItemLevel | Swing L/R | Swing Down | Thrust | Vortex Spin | Vortex Stab |
|-------|---------|-----------|-----------|------------|--------|-------------|-------------|
| Copper | Common | 10 | 8/9 | 14 | 21 | 15 | 44 |
| Iron | Uncommon | 20 | 9/10 | 18 | 26 | 19 | 56 |
| Adamantite | Rare | 40 | 14/16 | 28 | 41 | 29 | 87 |

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

Daggers display particles on both the primary and secondary item when signature energy is full:

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
          "TargetEntityPart": "PrimaryItem"
        },
        {
          "SystemId": "Daggers_Signature_Ready",
          "TargetNodeName": "Handle",
          "TargetEntityPart": "SecondaryItem"
        }
      ]
    }]
  }
}
```

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
    "EntityStatsToClear": ["SignatureEnergy", "SignatureCharges"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 6,
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

Shortbow uses both SignatureEnergy and SignatureCharges for its volley ability.

### Charge-Based Damage

Shortbow damage scales with charge time:

| Charge Level | Charge Time | Damage (Template) |
|--------------|-------------|-------------------|
| Strength_0 | 0.0s | 6 Projectile |
| Strength_1 | 0.3s | 10 Projectile |
| Strength_2 | 0.6s | 12 Projectile |
| Strength_3 | 0.9s | 14 Projectile |
| Strength_4 | 1.2s+ (full) | 15 Projectile |
| Signature Volley | - | 25 Projectile |

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
        { "SystemId": "Bow_Signature_Charge", "TargetNodeName": "ARROW-PLACEHOLDER", "PositionOffset": { "Y": 0.25 } },
        { "SystemId": "Bow_Signature_Charge", "TargetNodeName": "ARROW-PLACEHOLDER", "PositionOffset": { "Y": 0 } },
        { "SystemId": "Bow_Signature_Charge", "TargetNodeName": "ARROW-PLACEHOLDER", "PositionOffset": { "Y": -0.25 } }
      ]
    }]
  }
}
```

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
| `Signature_*` | Signature ability configuration |
| `Guard_*` | Blocking configuration |

### Ammo Consumption

The crossbow consumes `Weapon_Arrow_Crude` items from inventory:

```json
{
  "Arrow_Inventory_Condition": {
    "Interactions": [{
      "Type": "ModifyInventory",
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

Damage types:
- `Physical` - Melee weapon damage
- `Projectile` - Ranged weapon damage

### Stamina Cost for Blocking

```json
{
  "StaminaCost": {
    "Value": 10,
    "CostType": "Damage"
  }
}
```

| CostType | Description |
|----------|-------------|
| `Damage` | Stamina cost per damage blocked |
| `Flat` | Fixed stamina cost per block |

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
