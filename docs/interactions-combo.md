---
title: "Combo System Interactions"
description: "Build Hytale weapon combos with JSON interactions — Chaining for sequential combo chains with timing windows, FirstClick tap/hold branching, and charged-attack inputs."
seo:
  type: TechArticle
---

# Combo System Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against build-12**

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

This page covers the combo-system interactions: chaining attacks together with timing windows, branching on tap vs hold, charge-and-release mechanics, and the flag/cancel machinery that coordinates chains.

## Overview

Defined as JSON interaction assets (server classes under `com.hypixel.hytale.server.core.modules.interaction.interaction.config`) and provides:
- `Chaining` for sequential combo chains with a `ChainingAllowance` timing window
- `FirstClick` to branch between tap (click) and hold (held) input paths
- `Charging` for charge-and-release abilities keyed by hold-time thresholds
- `ChainId`-based coordination so separate chains can share state
- `ChainFlag` to set named flags that jump a chain into a `Flags` branch
- `CancelChain` to reset an active chain's state to the beginning

## Architecture
```
Combo System (coordinated by shared ChainId)
├── ChainingInteraction (Next[] steps + ChainingAllowance window)
│   └── Flags map ── jumped into by ──┐
├── FirstClickInteraction             │
│   ├── Click path                    │
│   └── Held path ─► often a Charging │ or sets a flag
├── ChargingInteraction (Next: time-threshold → interaction)
├── ChainFlagInteraction ─────────────┘ (sets Flag on a ChainId)
└── CancelChainInteraction (clears chain state + flags for a ChainId)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `ChainingInteraction` | `config/client/ChainingInteraction` | Sequential combo chains with timing windows and `Flags` branches |
| `FirstClickInteraction` | `config/client/FirstClickInteraction` | Branches on tap (`Click`) vs hold (`Held`) input |
| `ChargingInteraction` | `config/client/ChargingInteraction` | Charge-and-release, keyed by hold-time thresholds |
| `ChainFlagInteraction` | `config/none/ChainFlagInteraction` | Sets a named flag on a chain to trigger a `Flags` branch |
| `CancelChainInteraction` | `config/none/CancelChainInteraction` | Resets an active chain's state (and clears its flags) |

## Quick Navigation

| Interaction | Description |
|-------------|-------------|
| [ChainingInteraction](#chaininginteraction) | Sequential combo chains with timing windows |
| [FirstClickInteraction](#firstclickinteraction) | Branch based on tap vs hold input |
| [ChargingInteraction](#charginginteraction) | Charge-and-release mechanics |
| [ChainFlagInteraction](#chainflaginteraction) | Set flags for cross-chain communication |
| [CancelChainInteraction](#cancelchaininteraction) | Reset chain state to beginning |

---

## ChainingInteraction

**Package:** `config/client/ChainingInteraction`

Enables combo attack chains where players can input subsequent attacks within a timing window. This is the foundation for melee weapon combos, multi-hit abilities, and any sequence where attacks flow from one to the next. The system buffers player input during animations, allowing smooth combo execution.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Chaining"` |
| `ChainingAllowance` | float | Required | Time window (seconds) to input the next attack |
| `Next` | array | Required | Sequence of interactions in the chain |
| `ChainId` | string | - | Identifier for cross-interaction chain synchronization |
| `Flags` | object | - | Named branches that can be triggered via ChainFlagInteraction |

### Attack Chain Timing

Attack chains allow sequential attacks to flow together as combos. The timing between attacks is controlled by properties in the interaction configuration files.

#### Key Properties

| Property | Location | Purpose |
|----------|----------|---------|
| `ChainingAllowance` | Chain JSON files | Time window (seconds) before chain resets |
| `Cooldown` | Root interaction files | Minimum time between attacks |
| `ClickQueuingTimeout` | Root interaction files | Input buffer for queuing next attack |

#### ChainingAllowance

Defines how long (in seconds) the player has to execute the next attack before the chain breaks and resets.

**File location:** `Server/Item/Interactions/Weapons/{WeaponType}/Primary/*_Chain.json`

**Example:**
```json
{
  "Type": "Chaining",
  "ChainingAllowance": 2,
  "ChainId": "Sword_Swings",
  "Next": [...]
}
```

**Values by weapon:**

| Weapon | ChainingAllowance |
|--------|-------------------|
| Sword | 2.0s |
| Battleaxe | 2.9s |
| Daggers | 1.2s |

#### Cooldown & Click Queuing

Configured in Root Interaction files: `Server/Item/RootInteractions/Weapons/{WeaponType}/`

```json
{
  "RequireNewClick": true,
  "ClickQueuingTimeout": 0.2,
  "Cooldown": { "Cooldown": 0.25 },
  "Interactions": ["Weapon_Sword_Primary"]
}
```

- **Cooldown**: Minimum delay between attacks (prevents spam)
- **ClickQueuingTimeout**: Buffer window to queue next attack input
- **RequireNewClick**: If true, must click again to chain (holding won't auto-chain)

### ChainingAllowance Timing

The `ChainingAllowance` value determines how long the player has to input the next attack in the chain. This window opens during the current attack animation.

**Recommended values by weapon type:**

| Weapon Type | ChainingAllowance | Feel |
|-------------|-------------------|------|
| Fast tools (shears) | 0.5 | Very responsive |
| Light weapons (daggers, sticks) | 0.725-0.93 | Quick combos |
| Medium weapons (spears, staves) | 1.2-1.5 | Balanced timing |
| Heavy weapons (swords, battleaxes) | 2.0-3.0 | Deliberate, weighty |
| NPCs/AI | 10-15 | Effectively unlimited for AI timing |

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 1.5,
  "Next": ["Spear_Thrust_1", "Spear_Thrust_2", "Spear_Thrust_3"]
}
```

### The Next Array System

The `Next` property is an array defining the sequence of interactions. Each entry can be:

1. **String reference** - Path to another interaction file
2. **Inline interaction object** - Full interaction definition with optional `RunTime` and `Effects`
3. **Nested chain** - Another Chaining, Charging, or Conditional interaction

**Simple string references:**

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 2,
  "Next": [
    "Sword_Swing_Left",
    "Sword_Swing_Right",
    "Sword_Swing_Overhead"
  ]
}
```

**Inline interactions with RunTime:**

Each chain step can specify a `RunTime` to control animation duration:

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 1.2,
  "Next": [
    {
      "RunTime": 0.8,
      "Effects": {
        "ItemAnimationId": "dagger_slash_1"
      },
      "Next": "Dagger_Damage_1"
    },
    {
      "RunTime": 0.6,
      "Effects": {
        "ItemAnimationId": "dagger_slash_2"
      },
      "Next": "Dagger_Damage_2"
    }
  ]
}
```

**Using Replace for variable substitution:**

Chains often use Replace interactions to inject a step's behavior via a context variable, falling back to a default:

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 2,
  "Next": [
    {
      "Type": "Replace",
      "Var": "Swing_Left",
      "DefaultValue": {
        "Interactions": ["Sword_Swing_Left"]
      }
    },
    {
      "Type": "Replace",
      "Var": "Swing_Right",
      "DefaultValue": {
        "Interactions": ["Sword_Swing_Right"]
      }
    }
  ]
}
```

### ChainId and Cross-Interaction Sync

The `ChainId` property enables coordination between separate interaction chains (e.g., primary and secondary attacks). When multiple chains share the same `ChainId`, they share state and can trigger each other's `Flags` branches.

**Primary attack chain:**

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 2,
  "ChainId": "Sword_Combat",
  "Next": ["Sword_Swing_1", "Sword_Swing_2", "Sword_Swing_3"],
  "Flags": {
    "Block_Counter": "Sword_Counter_Attack"
  }
}
```

**Secondary defense chain (same ChainId):**

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 3,
  "ChainId": "Sword_Combat",
  "Next": ["Sword_Block_Start"]
}
```

With shared `ChainId`, a ChainFlagInteraction from the block can trigger the primary chain's `Block_Counter` flag.

### Flags System (Advanced)

The `Flags` object defines named branches that can be triggered by ChainFlagInteraction. This enables complex combo systems where certain actions unlock special moves.

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 2,
  "ChainId": "Advanced_Combo",
  "Next": ["Attack_1", "Attack_2", "Attack_3"],
  "Flags": {
    "Perfect_Parry": "Riposte_Attack",
    "Dodge_Cancel": "Dodge_Slash"
  }
}
```

A separate interaction can set these flags:

```json
{
  "Type": "ChainFlag",
  "ChainId": "Advanced_Combo",
  "Flag": "Perfect_Parry"
}
```

### Complete Examples

**Basic 3-Hit Combo:**

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 2,
  "Next": [
    "interactions/weapons/sword/swing_left",
    "interactions/weapons/sword/swing_right",
    "interactions/weapons/sword/swing_overhead"
  ]
}
```

**Dagger Combo with Effects:**

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 1.2,
  "ChainId": "Dagger_Primary",
  "Next": [
    {
      "RunTime": 0.5,
      "Effects": {
        "ItemAnimationId": "dagger_stab_1",
        "WorldSoundEventId": "sounds/weapons/dagger_swoosh"
      },
      "Next": "Dagger_Damage_Light"
    },
    {
      "RunTime": 0.5,
      "Effects": {
        "ItemAnimationId": "dagger_stab_2"
      },
      "Next": "Dagger_Damage_Light"
    },
    {
      "RunTime": 0.7,
      "Effects": {
        "ItemAnimationId": "dagger_slash_heavy"
      },
      "Next": "Dagger_Damage_Heavy"
    },
    {
      "RunTime": 0.6,
      "Effects": {
        "ItemAnimationId": "dagger_finisher"
      },
      "Next": "Dagger_Damage_Finisher"
    }
  ]
}
```

**Click/Held Branching with Chains:**

```json
{
  "Type": "FirstClick",
  "Click": {
    "Type": "Chaining",
    "ChainingAllowance": 1.0,
    "Next": ["Quick_Jab_1", "Quick_Jab_2"]
  },
  "Held": {
    "Type": "Charging",
    "Next": {
      "0": "Charge_Cancel",
      "1.0": {
        "Type": "Chaining",
        "ChainingAllowance": 2.0,
        "Next": ["Heavy_Swing_1", "Heavy_Swing_2", "Heavy_Finisher"]
      }
    }
  }
}
```

**NPC Attack Pattern:**

NPCs use high `ChainingAllowance` values since AI timing is less precise:

```json
{
  "Type": "Chaining",
  "ChainingAllowance": 15,
  "Next": [
    {
      "Type": "Serial",
      "Interactions": [
        { "Type": "Simple", "RunTime": 0.3 },
        "NPC_Skeleton_Swing_1"
      ]
    },
    {
      "Type": "Serial",
      "Interactions": [
        { "Type": "Simple", "RunTime": 0.5 },
        "NPC_Skeleton_Swing_2"
      ]
    }
  ]
}
```

### Common Patterns

| Pattern | Use Case | Key Properties |
|---------|----------|----------------|
| Simple combo | Basic melee weapons | `Next` array of string refs |
| Replace chain | Single animation with directional variants | `Replace` + shared interaction |
| Timed chain | Precise attack timing | `RunTime` on each step |
| Branching chain | Different combos from tap vs hold | `FirstClick` wrapper |
| Synced chains | Primary + secondary coordination | Shared `ChainId` |
| Flag combos | Conditional special moves | `Flags` + `ChainFlag` |

### Related Interactions

- [ChargingInteraction](#charginginteraction) - For charge-release mechanics
- [FirstClickInteraction](#firstclickinteraction) - Differentiates between tap and hold inputs
- [ChainFlagInteraction](#chainflaginteraction) - Sets a flag to trigger a Flags branch
- [CancelChainInteraction](#cancelchaininteraction) - Cancels/resets an active chain

---

## FirstClickInteraction

**Package:** `config/client/FirstClickInteraction`

Branches execution based on whether the player clicked (tapped) or held the input button. This enables interactions that differentiate between quick taps and sustained holds, such as quick attacks vs charged attacks, or single-use vs continuous tool actions.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"FirstClick"` |
| `Click` | Interaction | - | Interaction to run if input was a click (tap) |
| `Held` | Interaction | - | Interaction to run if input is being held down |

Both `Click` and `Held` are optional but at least one should be specified. If neither is set, the interaction completes immediately with no effect.

### How Click vs Held Detection Works

The interaction system tracks input state client-side. When FirstClickInteraction executes:

1. **Click path** - Triggers when the player quickly pressed and released the input, or when still in the initial press frame
2. **Held path** - Triggers when the player continues holding the input after the initial frame

This detection integrates with the chain system - if FirstClickInteraction is part of a Chaining sequence, the "held" state refers to whether the player is still holding when that chain step begins.

### Basic Examples

**Simple click vs hold:**

```json
{
  "Type": "FirstClick",
  "Click": {
    "Type": "Simple",
    "RunTime": 0.5,
    "Next": "Quick_Attack"
  },
  "Held": {
    "Type": "Charging",
    "Next": {
      "0": "Cancel",
      "1.0": "Heavy_Attack"
    }
  }
}
```

**Tool with animation on click:**

From `Watering_Can_Use.json` - clicking plays the water animation then performs the action, while holding goes directly to continuous watering:

```json
{
  "Type": "FirstClick",
  "Click": {
    "Type": "Simple",
    "RunTime": 0.3,
    "Effects": {
      "ItemAnimationId": "Water"
    },
    "Next": "Watering_Can_Use"
  },
  "Held": "Watering_Can_Use"
}
```

### Nested in Chaining

FirstClickInteraction can be used as chain steps to create combos that vary based on input timing. From `Debug_Combo_Primary.json`:

```json
{
  "Type": "Chaining",
  "ChainId": "Debug_Combo",
  "ChainingAllowance": 0.8,
  "Next": [
    {
      "Type": "SendMessage",
      "Message": "First - Primary",
      "RunTime": 0.5,
      "Effects": {
        "ItemAnimationId": "Swing_Right"
      }
    },
    {
      "Type": "FirstClick",
      "Click": {
        "Type": "SendMessage",
        "Message": "Second click - Primary",
        "RunTime": 0.5,
        "Effects": {
          "ItemAnimationId": "Swing_Left"
        }
      },
      "Held": {
        "Type": "SendMessage",
        "Message": "Second held - Primary",
        "RunTime": 0.5,
        "Effects": {
          "ItemAnimationId": "Hook_Left"
        },
        "Next": {
          "Type": "ChainFlag",
          "ChainId": "Debug_Combo",
          "Flag": "Held_Second"
        }
      }
    }
  ],
  "Flags": {
    "Special_Second": {
      "Type": "SendMessage",
      "Message": "Flag hit!"
    }
  }
}
```

In this pattern:
- The first attack always plays `Swing_Right`
- The second attack varies: click does `Swing_Left`, hold does `Hook_Left` and sets a flag
- The held path sets a `ChainFlag` that can trigger special branches in other chains sharing the same `ChainId`

### Integration with ChainFlag

The `Held` path commonly uses `ChainFlagInteraction` to communicate with other chains sharing the same `ChainId`. This enables mechanics like:
- Hold during combo to unlock special finisher
- Cross-hand coordination (primary attack held → secondary gains special move)

```json
{
  "Type": "FirstClick",
  "Click": "Normal_Combo_Step",
  "Held": {
    "Type": "Serial",
    "Interactions": [
      "Heavy_Combo_Step",
      {
        "Type": "ChainFlag",
        "ChainId": "Weapon_Combat",
        "Flag": "Heavy_Unlocked"
      }
    ]
  }
}
```

### Common Patterns

| Pattern | Click | Held | Use Case |
|---------|-------|------|----------|
| **Light/Heavy attack** | Quick strike | Charging interaction | Melee weapons with charge attacks |
| **Single/Continuous** | Single action with animation | Direct action | Tools (watering can, spray) |
| **Combo variant** | Normal combo step | Alternative step + flag | Branching combos |
| **Instant/Aimed** | Hip-fire | Aim-down-sights mode | Ranged weapons |

### Related Interactions

- [ChainingInteraction](#chaininginteraction) - FirstClick is often nested within chains
- [ChargingInteraction](#charginginteraction) - `Held` path commonly leads to Charging
- [ChainFlagInteraction](#chainflaginteraction) - Set flags from `Held` path for cross-chain coordination

---

## ChargingInteraction

**Package:** `config/client/ChargingInteraction`

Enables charged attacks and abilities that scale with hold duration. Players hold the input to build charge, then release to trigger an interaction based on how long they charged. This is the foundation for bows, charged melee attacks, consumables, and casting mechanics.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Charging"` |
| `Next` | object | Required | Map of charge time thresholds to interactions |
| `AllowIndefiniteHold` | boolean | `false` | If `true`, player can hold at max charge indefinitely |
| `DisplayProgress` | boolean | `true` | Show charge progress indicator to player |
| `Effects` | object | - | Animation, sound, and particle effects during charging |
| `HorizontalSpeedMultiplier` | float | `1.0` | Movement speed while charging (0.0-1.0) |
| `FailOnDamage` | boolean | `false` | Cancel charging if player takes damage |
| `Failed` | object | - | Interaction to execute if charging fails/cancels |
| `MouseSensitivityAdjustmentTarget` | float | - | Target sensitivity multiplier during charge |
| `MouseSensitivityAdjustmentDuration` | float | - | Time to transition to target sensitivity |

### The Next Map System

The `Next` property is a map where **keys are charge time thresholds** (in seconds as strings) and **values are interactions** to execute when released at or above that threshold. The system selects the highest threshold the player reached.

```json
{
  "Type": "Charging",
  "Next": {
    "0": { "Type": "Serial", "Comment": "Uncharged release" },
    "0.5": { "Type": "Serial", "Comment": "Partial charge" },
    "1.2": { "Type": "Serial", "Comment": "Full charge" }
  }
}
```

**Key patterns:**
- `"0"` - Triggered on immediate release (no charge)
- Numeric strings like `"0.5"`, `"1.2"` - Minimum charge time to trigger
- Values can be inline interactions, string references, or `"Parent"` to chain back

**Example with references:**

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": true,
  "Next": {
    "0": "interactions/weapons/bow_cancel",
    "0.3": "interactions/weapons/bow_fire_weak",
    "1.0": "interactions/weapons/bow_fire_full"
  }
}
```

### Effects Configuration

The `Effects` object configures visual and audio feedback during the charging phase:

| Property | Type | Description |
|----------|------|-------------|
| `ItemAnimationId` | string | Animation to play on held item during charge |
| `ClearAnimationOnFinish` | boolean | Stop animation when charge completes/releases |
| `WorldSoundEventId` | string | Sound event audible to all nearby players |
| `LocalSoundEventId` | string | Sound event only the charging player hears |
| `ClearSoundEventOnFinish` | boolean | Stop sound when charge completes/releases |
| `Particles` | array | Particle effects during charging |

**Particles array entry:**

```json
{
  "Particles": [
    {
      "ParticleSystemId": "particles/charge_buildup",
      "NodeId": "weapon_tip",
      "Position": [0, 0, 0],
      "Rotation": [0, 0, 0],
      "Scale": [1, 1, 1]
    }
  ]
}
```

### Complete Examples

**Bow with Progressive Charge:**

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": true,
  "DisplayProgress": true,
  "HorizontalSpeedMultiplier": 0.6,
  "MouseSensitivityAdjustmentTarget": 0.5,
  "MouseSensitivityAdjustmentDuration": 0.3,
  "Effects": {
    "ItemAnimationId": "bow_draw",
    "WorldSoundEventId": "sounds/weapons/bow_draw",
    "ClearSoundEventOnFinish": true,
    "Particles": [
      {
        "ParticleSystemId": "particles/bow_tension",
        "NodeId": "string_center"
      }
    ]
  },
  "Next": {
    "0": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "Simple", "Effects": { "ClearAnimationOnFinish": true } }
      ]
    },
    "0.5": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
        { "Type": "LaunchProjectile", "ProjectileId": "arrow", "Speed": 30 }
      ]
    },
    "1.2": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
        { "Type": "LaunchProjectile", "ProjectileId": "arrow", "Speed": 60 }
      ]
    }
  }
}
```

**Charged Melee Attack with Stamina:**

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": false,
  "DisplayProgress": true,
  "HorizontalSpeedMultiplier": 0.4,
  "Effects": {
    "ItemAnimationId": "sword_charge",
    "LocalSoundEventId": "sounds/weapons/charge_hum",
    "ClearAnimationOnFinish": true,
    "Particles": [
      {
        "ParticleSystemId": "particles/weapon_glow",
        "NodeId": "blade_edge",
        "Scale": [1.5, 1.5, 1.5]
      }
    ]
  },
  "Next": {
    "0": { "Type": "Serial", "Comment": "Charge canceled" },
    "0.8": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
        { "Type": "Simple", "Effects": { "ItemAnimationId": "sword_heavy_swing" } },
        {
          "Type": "DamageEntity",
          "DamageCalculator": { "BaseDamage": { "Physical": 25 } }
        }
      ]
    },
    "1.5": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ChangeStat", "StatModifiers": { "Stamina": -40 } },
        { "Type": "Simple", "Effects": { "ItemAnimationId": "sword_power_swing" } },
        {
          "Type": "DamageEntity",
          "DamageCalculator": { "BaseDamage": { "Physical": 50 } }
        }
      ]
    }
  }
}
```

**Consumable with Fail on Damage:**

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": false,
  "DisplayProgress": true,
  "FailOnDamage": true,
  "HorizontalSpeedMultiplier": 0.3,
  "Effects": {
    "ItemAnimationId": "eat_food",
    "LocalSoundEventId": "sounds/player/eating"
  },
  "Failed": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "Simple", "Effects": { "LocalSoundEventId": "sounds/ui/action_canceled" } }
    ]
  },
  "Next": {
    "0": { "Type": "Serial", "Comment": "Eating canceled" },
    "2.0": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
        { "Type": "ApplyEffect", "EffectId": "satiated" }
      ]
    }
  }
}
```

**Charging into Chaining (Hybrid):**

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": true,
  "DisplayProgress": false,
  "Effects": {
    "ItemAnimationId": "staff_channel",
    "Particles": [
      { "ParticleSystemId": "particles/magic_gather", "NodeId": "staff_orb" }
    ]
  },
  "Next": {
    "0": { "Type": "Serial" },
    "0.6": {
      "Type": "Chaining",
      "ChainingAllowance": 1.5,
      "ChainId": "staff_combo",
      "Next": [
        { "Type": "LaunchProjectile", "ProjectileId": "magic_bolt" },
        { "Type": "LaunchProjectile", "ProjectileId": "magic_bolt_double" }
      ]
    }
  }
}
```

### Common Patterns

| Pattern | AllowIndefiniteHold | DisplayProgress | HorizontalSpeedMultiplier | Use Case |
|---------|---------------------|-----------------|---------------------------|----------|
| **Ranged Hold** | `true` | `true` | 0.5-0.7 | Bows, crossbows, aimed spells |
| **Melee Power** | `false` | `true` | 0.3-0.5 | Heavy attacks, ground slams |
| **Consumable** | `false` | `true` | 0.2-0.4 | Food, potions, bandages |
| **Quick Charge** | `false` | `false` | 0.8-1.0 | Fast abilities, parries |

### Integration Notes

- Combine with [Serial](interactions-flow.md#serial) to execute multiple effects on release
- Use [Condition](interactions-flow.md#condition) within `Next` values for ammo/stamina checks
- Chain into [ChainingInteraction](#chaininginteraction) for charge-then-combo patterns

---

## ChainFlagInteraction

**Package:** `config/none/ChainFlagInteraction`

Sets a flag on a chain that a [ChainingInteraction](#chaininginteraction) can use to jump to an alternative execution path. This enables cross-chain communication where one interaction (like a successful block or special input) can trigger a special move in another chain sharing the same `ChainId`.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"ChainFlag"` |
| `ChainId` | string | Required | Target chain identifier to set the flag on |
| `Flag` | string | Required | Flag name matching a key in the target chain's `Flags` map |

### How Flag Triggering Works

When `ChainFlagInteraction` executes:

1. The system looks up the entity's active chain state for the given `ChainId`
2. It sets a flag index that points to the named flag
3. On the next tick of the target `ChainingInteraction`, it checks `flagIndex`
4. If a flag is set (`flagIndex != -1`), the chain jumps to the interaction defined in `Flags[flagName]` instead of continuing its normal `Next` sequence
5. The flag is consumed (reset) after triggering

This allows interactions to "inject" behavior into an ongoing chain without interrupting it directly.

### Cross-Chain Communication

Multiple chains can share the same `ChainId`, enabling coordination between primary and secondary attack chains:

**Primary attack chain (defines the flag targets):**

```json
{
  "Type": "Chaining",
  "ChainId": "Sword_Combat",
  "ChainingAllowance": 2,
  "Next": ["Sword_Swing_1", "Sword_Swing_2", "Sword_Swing_3"],
  "Flags": {
    "Counter_Ready": "Sword_Counter_Attack",
    "Special_Second": "Sword_Special_Strike"
  }
}
```

**Secondary attack chain (can trigger the primary's flags):**

```json
{
  "Type": "Chaining",
  "ChainId": "Sword_Combat",
  "ChainingAllowance": 3,
  "Next": [
    {
      "Type": "Wielding",
      "BlockedInteractions": {
        "Interactions": [
          {
            "Type": "ChainFlag",
            "ChainId": "Sword_Combat",
            "Flag": "Counter_Ready"
          }
        ]
      }
    }
  ]
}
```

When the player successfully blocks (secondary), it sets `Counter_Ready` on the shared chain. The next time the player uses primary attack, instead of continuing the normal combo, the chain jumps to `Sword_Counter_Attack`.

### Complete Examples

**Debug combo with flag from held input:**

From `Debug_Combo_Primary.json` - when player holds during second attack, it sets a flag:

```json
{
  "Type": "Chaining",
  "ChainId": "Debug_Combo",
  "ChainingAllowance": 0.8,
  "Next": [
    {
      "Type": "SendMessage",
      "Message": "First - Primary",
      "RunTime": 0.5
    },
    {
      "Type": "FirstClick",
      "Click": {
        "Type": "SendMessage",
        "Message": "Second click - Primary",
        "RunTime": 0.5
      },
      "Held": {
        "Type": "SendMessage",
        "Message": "Second held - Primary",
        "RunTime": 0.5,
        "Next": {
          "Type": "ChainFlag",
          "ChainId": "Debug_Combo",
          "Flag": "Held_Second"
        }
      }
    }
  ],
  "Flags": {
    "Special_Second": {
      "Type": "SendMessage",
      "Message": "Flag triggered!"
    }
  }
}
```

**Secondary attack triggering primary's special:**

From `Debug_Combo_Secondary.json` - secondary attack sets a flag on the primary chain:

```json
{
  "Type": "Chaining",
  "ChainId": "Debug_Combo",
  "ChainingAllowance": 0.8,
  "Next": [
    {
      "Type": "Serial",
      "Interactions": [
        {
          "Type": "SendMessage",
          "Message": "First - Secondary"
        },
        {
          "Type": "ChainFlag",
          "ChainId": "Debug_Combo",
          "Flag": "Special_Second"
        }
      ],
      "RunTime": 0.5
    }
  ]
}
```

When the player uses secondary attack, it immediately sets `Special_Second`. The next primary attack will jump to the flag target instead of the normal combo.

### Common Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Block counter** | Successful block unlocks riposte | Block sets `Counter_Ready`, next primary triggers counter attack |
| **Combo extender** | Specific input unlocks special finisher | Hold during combo sets `Special_Finisher` flag |
| **Primary/Secondary sync** | Secondary attack modifies primary behavior | Secondary sets flag, primary checks it next tick |
| **Parry window** | Perfect timing unlocks powerful response | Parry interaction sets `Perfect_Parry` flag |

### Related Interactions

- [ChainingInteraction](#chaininginteraction) - Defines the `Flags` map that ChainFlag targets
- [CancelChainInteraction](#cancelchaininteraction) - Resets chain state (clears flags)
- [FirstClickInteraction](#firstclickinteraction) - Often used to trigger flags on held input

---

## CancelChainInteraction

**Package:** `config/none/CancelChainInteraction`

**Class hierarchy:** `CancelChainInteraction` → `SimpleInstantInteraction` → `SimpleInteraction` → `Interaction`

**Protocol class:** `CancelChainInteractionProtocol` (handles client-server synchronization)

Cancels and resets an active chain's state, returning it to the beginning. This is used to break combos early, reset chain state after special moves, or clear chain flags without waiting for the `ChainingAllowance` timeout.

### Core Properties

| Property | Type | Default | Validator | Description |
|----------|------|---------|-----------|-------------|
| `Type` | string | Required | - | Always `"CancelChain"` |
| `ChainId` | string | Required | `nonNull` | Target chain identifier to cancel/reset |

The `ChainId` validator ensures the property cannot be null or empty - every CancelChainInteraction must specify which chain to cancel.

### How Chain Cancellation Works

When `CancelChainInteraction` executes, the following steps occur internally:

1. **Entity lookup** - Gets the entity from the `InteractionContext`
2. **Component access** - Retrieves the entity's `ChainingInteraction.Data` component which stores all active chain states
3. **Chain state removal** - Removes the entry for the specified `ChainId` from the component's `namedMap`
4. **Flag clearing** - Any flags set on that chain via `ChainFlagInteraction` are also cleared

**Effect:** The next time the player triggers an interaction using that `ChainId`, the chain starts from the beginning (index 0 of the `Next` array) instead of continuing from where it left off.

```
Before CancelChain:
┌─────────────────────────────────────────────┐
│ Chain State for "Sword_Primary"             │
│   currentIndex: 2                           │
│   flagIndex: 1 (Counter flag set)           │
│   timeRemaining: 1.5s                       │
└─────────────────────────────────────────────┘

After CancelChain:
┌─────────────────────────────────────────────┐
│ Chain State for "Sword_Primary"             │
│   (entry removed - chain resets on next use)│
└─────────────────────────────────────────────┘
```

### When to Use CancelChain

- **After charged attacks** - Reset combo after a charged heavy attack so the next attack starts fresh
- **On special move execution** - Clear chain state when a flagged special move triggers
- **Manual combo reset** - Allow players to reset their combo with a specific action (dodge, block)
- **Timeout override** - Force-reset a chain before its `ChainingAllowance` would naturally expire

### Complete Examples

**Reset combo after charged attack:**

From `Sword_Combo_Stage_1.json` - after a charged attack, the chain resets:

```json
{
  "Type": "Chaining",
  "ChainId": "Sword_Primary",
  "ChainingAllowance": 2,
  "Next": [
    {
      "Type": "FirstClick",
      "Click": "Sword_Swing_1",
      "Held": {
        "Type": "Charging",
        "Next": {
          "0": "Sword_Swing_Cancel",
          "1.0": {
            "Type": "Serial",
            "Interactions": [
              "Sword_Heavy_Attack",
              {
                "Type": "CancelChain",
                "ChainId": "Sword_Primary"
              }
            ]
          }
        }
      }
    },
    "Sword_Swing_2",
    "Sword_Swing_3"
  ]
}
```

The charged attack (`Sword_Heavy_Attack`) is followed by `CancelChain`, so the next attack will restart from `Sword_Swing_1` instead of continuing to `Sword_Swing_2`.

**Reset after special flag execution:**

```json
{
  "Type": "Chaining",
  "ChainId": "Advanced_Combo",
  "ChainingAllowance": 2,
  "Next": ["Attack_1", "Attack_2", "Attack_3"],
  "Flags": {
    "Counter": {
      "Type": "Serial",
      "Interactions": [
        "Powerful_Counter_Attack",
        {
          "Type": "CancelChain",
          "ChainId": "Advanced_Combo"
        }
      ]
    }
  }
}
```

When the `Counter` flag triggers, it executes the counter attack and then resets the chain.

**Dodge-cancel combo:**

```json
{
  "Type": "Serial",
  "Interactions": [
    "Dodge",
    {
      "Type": "CancelChain",
      "ChainId": "Sword_Primary"
    }
  ]
}
```

Dodging (a referenced dodge interaction) cancels any active combo chain, letting the player reset their attack pattern.

**Mode switch reset:**

When a weapon has multiple modes (e.g., one-handed vs two-handed grip), switching modes should reset any active combo:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "CancelChain",
      "ChainId": "Sword_Primary"
    },
    {
      "Type": "CancelChain",
      "ChainId": "Sword_Secondary"
    },
    {
      "Type": "Replace",
      "Var": "GripMode",
      "DefaultValue": {
        "Interactions": ["Switch_Grip_Animation"]
      }
    }
  ]
}
```

This pattern cancels both primary and secondary attack chains before switching to the new grip mode.

### Common Patterns

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **Heavy attack reset** | Charged attacks end the combo | CancelChain after charged hit |
| **Special move reset** | Flag-triggered moves reset chain | CancelChain in Flags target |
| **Defensive reset** | Blocking/dodging resets combo | CancelChain in block/dodge interaction |
| **Mode switch** | Switching weapon modes resets combos | CancelChain when switching |
| **Timeout prevention** | Force immediate reset without waiting | CancelChain instead of relying on `ChainingAllowance` expiry |

### Technical Notes

- **Empty `firstRun()`** - The `CancelChainInteraction` class has an empty `firstRun()` method. All cancellation logic executes in `simulateFirstRun()`, which runs on both client and server.

- **Client/server sync** - The `CancelChainInteractionProtocol` class handles network synchronization. When a cancel occurs on the client, it's replicated to the server to ensure both sides have consistent chain state.

- **Clears flags too** - Canceling a chain also clears any flags set via `ChainFlagInteraction`. If you need to preserve flags while resetting position, you would need a custom solution.

- **No partial reset** - There's no built-in way to reset a chain to a specific index. CancelChain always fully removes the chain state, causing it to restart from index 0.

### Related Interactions

- [ChainingInteraction](#chaininginteraction) - The chain type that CancelChain resets
- [ChainFlagInteraction](#chainflaginteraction) - Often used together (flag triggers special, then cancel resets)
- [FirstClickInteraction](#firstclickinteraction) - Common parent for charged attacks that trigger CancelChain

---

## Gotchas & Errors

- **Symptom:** a combo never advances past the first hit → the next input arrived after the `ChainingAllowance` window closed, so the chain reset to the start. Fix: widen `ChainingAllowance`, and remember the window opens *during* the current attack animation (see [ChainingAllowance Timing](#chainingallowance-timing)).
- **Symptom:** a `ChainFlag` set in one chain never triggers a branch in another → the two chains don't share the same `ChainId`. Fix: give both interactions the identical `ChainId` so they share flag state (see [ChainId and Cross-Interaction Sync](#chainid-and-cross-interaction-sync)).
- **Symptom:** a flag-triggered branch only fires once → flags are consumed (reset) immediately after triggering. Fix: re-set the flag with `ChainFlag` each time you need the branch to fire again.
- **Symptom:** a `Charging` interaction releases the wrong tier (or nothing) → the `Next` map keys are **strings** representing charge-time thresholds, and the system picks the highest threshold reached. Fix: include a `"0"` entry for immediate release, and use string keys like `"0.5"`, not numbers (see [The Next Map System](#the-next-map-system)).
- **Symptom:** `CancelChain` wiped flags you wanted to keep → cancelling a chain also clears any flags set via `ChainFlag`, and always resets to index 0 (no partial reset). Fix: don't rely on flag persistence across a cancel; re-establish state afterward.
