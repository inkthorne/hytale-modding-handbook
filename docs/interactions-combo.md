---
title: "Combo System Interactions"
description: "Build Hytale weapon combos with JSON interactions — Chaining for sequential combo chains with timing windows, FirstClick tap/hold branching, and charged-attack inputs."
seo:
  type: TechArticle
---

# Combo System Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.5.9**

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
└── CancelChainInteraction (removes the stored chain index for a ChainId)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `ChainingInteraction` | `config/client/ChainingInteraction` | Sequential combo chains with timing windows and `Flags` branches |
| `FirstClickInteraction` | `config/client/FirstClickInteraction` | Branches on tap (`Click`) vs hold (`Held`) input |
| `ChargingInteraction` | `config/client/ChargingInteraction` | Charge-and-release, keyed by hold-time thresholds |
| `ChainFlagInteraction` | `config/none/ChainFlagInteraction` | Sets a named flag on a chain to trigger a `Flags` branch |
| `CancelChainInteraction` | `config/none/CancelChainInteraction` | Resets an active chain's position to the start |

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
| `ChainingAllowance` | float | `0` | Time window (seconds) to input the next attack; `0` (the default) never expires the chain |
| `Next` | array | Required | Sequence of interactions in the chain. Validated `nonNull` with `nonNull` elements; each entry is an interaction id **or** an inline interaction object |
| `ChainId` | string | - | Identifier for cross-interaction chain synchronization. When omitted, chain state is keyed by this interaction's own asset id and stored in a *different* map — see the warning below |
| `Flags` | object | - | Named branches that can be triggered via ChainFlagInteraction. Values are interaction ids or inline interaction objects |

> ⚠️ **A chain without a `ChainId` cannot be reset by `CancelChain`.** The server keeps two maps on the
> `ChainingInteraction.Data` component: `namedMap`, keyed by `ChainId`, and an unnamed `map`, keyed by
> the chaining interaction's own asset id. `CancelChainInteraction` only ever calls
> `getNamedMap().removeInt(chainId)`, and `map` has no public accessor at all — so a chain that omits
> `ChainId` is unreachable from `CancelChain`. `ChainFlag` is likewise addressed by `ChainId`, so give
> any chain you intend to reset or flag an explicit `ChainId`.

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

**File location:** `Server/Item/Interactions/Weapons/{WeaponType}/Primary/*_Chain.json` (e.g. `Battleaxe/Primary/Weapon_Battleaxe_Primary_Chain.json`, `Daggers/Primary/Weapon_Daggers_Primary_Chain.json`; the sword's sits one level deeper at `Sword/Attacks/Primary/Weapon_Sword_Primary_Chain.json`)

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

The `ChainingAllowance` value determines how long the player has to input the next attack in the chain. This window opens during the current attack animation. The server accepts a small grace band around the boundary — `min(0.5, ChainingAllowance × 0.25)` seconds — during which either the next step or a restart from step 0 is accepted; an input past the allowance restarts the chain at index 0, and once the last `Next` entry has run the chain wraps back to index 0.

**Recommended values by weapon type:**

| Weapon Type | ChainingAllowance | Feel |
|-------------|-------------------|------|
| Fast tools (shears) | 0.5 | Very responsive |
| Light weapons (sticks, knives, daggers) | 0.725-1.2 | Quick combos |
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

From `Server/Item/RootInteractions/Tools/Watering_Can_Use.json` - clicking plays the water animation then performs a single watering (`Watering_Can_Use`, `RadiusX`/`RadiusZ` of 1), while holding hands off to `Watering_Can_Use_Charge` — a `Charging` interaction whose `"0"` threshold falls back to the same single watering and whose `"0.5"` threshold runs `Watering_Can_Use_3x3`, a wider radius (`RadiusX`/`RadiusZ` of 3):

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
  "Held": "Watering_Can_Use_Charge"
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
| `Next` | object | - | Map of charge-time thresholds to interactions. The codec does **not** mark it required, but a `Charging` with no `Next` has no release behaviour and (with `AllowIndefiniteHold` false) a max charge of `0` |
| `AllowIndefiniteHold` | boolean | `false` | If `true`, player can hold at max charge indefinitely |
| `DisplayProgress` | boolean | `true` | Show charge progress indicator to player |
| `Effects` | object | - | Animation, sound, and particle effects during charging |
| `HorizontalSpeedMultiplier` | float | `1.0` | Movement speed while charging. No codec bound; every shipped value is between `0` and `1` |
| `FailOnDamage` | boolean | `false` | Cancel the charge when the entity takes damage. The codec's own description is "the interaction will be cancelled and the item removed", so treat it as more than a pure cancel and test before shipping it on a non-consumable |
| `Failed` | string/object | - | Interaction to execute if charging fails/cancels |
| `MouseSensitivityAdjustmentTarget` | float | `1.0` | Target sensitivity multiplier during charge |
| `MouseSensitivityAdjustmentDuration` | float | `1.0` | Overrides the global adjustment: the time taken to go from `1.0` to `0.0` |
| `CancelOnOtherClick` | boolean | `true` | Cancel the charge when another click arrives while holding |
| `Forks` | object | - | Map of `InteractionType` → **root interaction** to run when that input is pressed *while still holding* this one (see below) |
| `Delay` | object | - | `ChargingDelay`: delays the charge when the user is damaged — `MinDelay`/`MaxDelay` (seconds, scaled between the `MinHealth` and `MaxHealth` health fractions), with `MaxTotalDelay` capping the accumulated delay |

### Forks (input-while-holding)

`Forks` is the mechanism behind "hold Secondary to guard, tap Primary to bash". Keys are
`InteractionType` values (`Primary`, `Secondary`, `Ability1`–`Ability3`, `Use`, …); values are
**root interaction** references — an id, or an inline `{ "Interactions": [...] }` object.

Every shipped use is on a `Wielding` interaction, e.g. `Weapon_Shield_Secondary_Guard_Wield`:

```json
{
  "Type": "Wielding",
  "CancelOnOtherClick": false,
  "Forks": {
    "Primary": {
      "Interactions": ["Weapon_Shield_Secondary_Guard_Bash"]
    }
  }
}
```

Forking does **not** cancel the held interaction — but the `CancelOnOtherClick` check still runs and
may cancel it, which is why the vanilla guards pair `Forks` with `"CancelOnOtherClick": false`. A
forked chain keeps running even after the charging interaction itself ends.

> **`Wielding` is a `Charging`.** `WieldingInteraction extends ChargingInteraction`, so `Forks`,
> `CancelOnOtherClick`, `Failed`, `AllowIndefiniteHold`, `DisplayProgress`, `FailOnDamage`, `Delay`
> and the mouse-sensitivity pair are all equally valid on a `"Type": "Wielding"` block, on top of
> `Wielding`'s own `AngledWielding`, `DamageModifiers`, `KnockbackModifiers`, `StaminaCost`,
> `BlockedEffects` and `BlockedInteractions`. The one property that does **not** carry over is `Next`:
> `Wielding` redeclares it as a single interaction, not a charge-threshold map, so
> `"Next": { "Type": "ChangeStat", ... }` on a `Wielding` and `"Next": { "0.5": ... }` on a `Charging`
> are different keys that happen to share a name.

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
- Values can be inline interactions or string references (an inline object may itself use `"Parent"` to inherit from a named interaction and override a few fields)

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

**Particles array entry** (a `ModelParticle`: `SystemId` names the particle system,
`TargetEntityPart`/`TargetNodeName` pick the model node to attach to,
`PositionOffset`/`RotationOffset`/`Scale` adjust placement, `Color` tints it,
`DetachedFromModel` spawns it in world space instead of following the model, and
`ClearParticlesOnRemove` (0.6.3+) removes the emitted particles when the entry is removed):

```json
{
  "Particles": [
    {
      "SystemId": "Watering_Can",
      "TargetEntityPart": "PrimaryItem",
      "TargetNodeName": "Can",
      "PositionOffset": { "X": 0, "Y": 0, "Z": 0 }
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
        "SystemId": "particles/bow_tension",
        "TargetNodeName": "string_center"
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
        { "Type": "LaunchProjectile", "ProjectileId": "Arrow_HalfCharge" }
      ]
    },
    "1.2": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
        { "Type": "LaunchProjectile", "ProjectileId": "Arrow_FullCharge" }
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
        "SystemId": "particles/weapon_glow",
        "TargetNodeName": "blade_edge",
        "Scale": 1.5
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
      { "SystemId": "particles/magic_gather", "TargetNodeName": "staff_orb" }
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

1. The flag is recorded in the **client's** interaction state for the given `ChainId` — the server-side `ChainFlagInteraction.firstRun` is empty; the server only forwards `ChainId`/`Flag` to the client in the interaction packet
2. The next time the target `ChainingInteraction` runs, the client sends a `flagIndex` (the position of the flag name among the chain's sorted `Flags` keys) instead of a `chainingIndex`
3. The server validates the index (an out-of-range value fails the interaction with a `WARNING` log) and, when `flagIndex != -1`, jumps to the interaction defined in `Flags[flagName]` instead of continuing its normal `Next` sequence
4. The flag is consumed (reset) after triggering, so the following run resumes the normal sequence

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
      "Message": "Flag hit!"
    }
  }
}
```

**Secondary attack triggering primary's special:**

From `Debug_Combo_Secondary.json` - the second step of the secondary chain sets a flag on the shared `Debug_Combo` chain (abbreviated):

```json
{
  "Type": "Chaining",
  "ChainId": "Debug_Combo",
  "ChainingAllowance": 0.8,
  "Next": [
    {
      "Type": "SendMessage",
      "Message": "First - Secondary",
      "RunTime": 0.5
    },
    {
      "Type": "SendMessage",
      "Message": "Second - Secondary",
      "RunTime": 0.5,
      "Next": {
        "Type": "ChainFlag",
        "ChainId": "Debug_Combo",
        "Flag": "Special_Second"
      }
    }
  ],
  "Flags": {
    "Held_Second": { "Type": "SendMessage", "Message": "Held Flag hit!" }
  }
}
```

The second secondary attack sets `Special_Second`; the next primary attack then jumps to the primary chain's `Special_Second` flag target instead of continuing its normal combo. Symmetrically, the primary chain's held second step sets `Held_Second`, which this chain's `Flags` map handles.

### Common Patterns

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Block counter** | Successful block unlocks riposte | Block sets `Counter_Ready`, next primary triggers counter attack |
| **Combo extender** | Specific input unlocks special finisher | Hold during combo sets `Special_Finisher` flag |
| **Primary/Secondary sync** | Secondary attack modifies primary behavior | Secondary sets flag, primary checks it next tick |
| **Parry window** | Perfect timing unlocks powerful response | Parry interaction sets `Perfect_Parry` flag |

### Related Interactions

- [ChainingInteraction](#chaininginteraction) - Defines the `Flags` map that ChainFlag targets
- [CancelChainInteraction](#cancelchaininteraction) - Resets chain position to the start
- [FirstClickInteraction](#firstclickinteraction) - Often used to trigger flags on held input

---

## CancelChainInteraction

**Package:** `config/none/CancelChainInteraction`

**Class hierarchy:** `CancelChainInteraction` → `SimpleInstantInteraction` → `SimpleInteraction` → `Interaction`

**Protocol class:** `com.hypixel.hytale.protocol.CancelChainInteraction` (the wire form of the config class, carrying `chainId` to the client)

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
2. **Component access** - Retrieves (creating it if absent) the entity's `ChainingInteraction.Data` component, which stores the last-reached index per chain
3. **Chain state removal** - Removes the entry for the specified `ChainId` from the component's `namedMap` (`getNamedMap().removeInt(chainId)`)

**Effect:** The next time the player triggers an interaction using that `ChainId`, the chain starts from the beginning (index 0 of the `Next` array) instead of continuing from where it left off. Flags are not part of the server's `Data` component (it holds only the per-chain index maps and a shared `lastAttack` timestamp) — a pending flag set via `ChainFlagInteraction` is client-side state.

> ⚠️ **Only `namedMap` is touched.** `CancelChain` calls `getNamedMap().removeInt(chainId)`, so it can
> reset only chains that declared a matching `ChainId`. A `ChainingInteraction` without a `ChainId`
> stores its index in the component's other, unexposed `map` and is unreachable from `CancelChain`.

```
Before CancelChain:
┌─────────────────────────────────────────────┐
│ ChainingInteraction.Data                    │
│   namedMap["Sword_Primary"] = 2             │
│   lastAttack: <timestamp, shared by chains> │
└─────────────────────────────────────────────┘

After CancelChain:
┌─────────────────────────────────────────────┐
│ ChainingInteraction.Data                    │
│   (entry removed - chain resets on next use)│
│   lastAttack: <unchanged>                   │
└─────────────────────────────────────────────┘
```

### When to Use CancelChain

- **After charged attacks** - Reset combo after a charged heavy attack so the next attack starts fresh
- **On special move execution** - Clear chain state when a flagged special move triggers
- **Manual combo reset** - Allow players to reset their combo with a specific action (dodge, block)
- **Timeout override** - Force-reset a chain before its `ChainingAllowance` would naturally expire

### Complete Examples

**Reset combo after charged attack:**

From `Sword_Combo_Stage_1.json` (now under `Weapons/Sword/Attacks/Deprecated/Combo/` — the live sword uses `Weapon_Sword_Primary_Chain.json`, but the pattern is unchanged) - a stamina-gated `Charging` step whose charged release runs the dash attack and then cancels the `Sword_Combo` chain (abbreviated):

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 2.01 },
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "Charging",
        "DisplayProgress": false,
        "Effects": { "ItemAnimationId": "StabDashCharging" },
        "Next": {
          "0": "Sword_Swing_Left_Fast",
          "0.45": {
            "Type": "Serial",
            "Interactions": [
              { "Type": "ChangeStat", "StatModifiers": { "Stamina": -2 } },
              "Sword_Stab_Dash_Charged",
              { "Type": "CancelChain", "ChainId": "Sword_Combo" }
            ]
          }
        }
      }
    ]
  },
  "Failed": "Sword_Swing_Left_Fast"
}
```

The charged release (`Sword_Stab_Dash_Charged`) is followed by `CancelChain`, so the next primary attack restarts the `Sword_Combo` chain from its first step instead of continuing.

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

- **Empty `firstRun()`** - `firstRun()` (reached from `tick0`) is empty; the cancellation lives in `simulateFirstRun()` (reached from `simulateTick0`), the path the server takes when simulating a client-initiated chain.

- **Client/server sync** - The config class serialises to `com.hypixel.hytale.protocol.CancelChainInteraction` (just `chainId` on top of the base interaction fields), so the client runs the same cancel locally and both sides keep a consistent chain index.

- **Flags are client-side** - The server's `ChainingInteraction.Data` stores only per-chain indices and a `lastAttack` timestamp; a pending `ChainFlag` is not stored there, so whether it survives a cancel is client behaviour. Don't design around a flag persisting across a cancel.

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
- **Symptom:** `CancelChain` silently does nothing → the target `ChainingInteraction` has no `ChainId`, so its index lives in the `Data` component's unnamed map, which `CancelChain` cannot reach (it only removes from `namedMap`). Fix: give the chain an explicit `ChainId` and use the same string in `CancelChain`.
- **Symptom:** `CancelChain` didn't behave like a partial reset → cancelling always removes the chain's index entry, so the chain restarts at index 0 (there is no reset-to-index). Flag state is client-side and not part of the server's `Data` component, so don't rely on a pending `ChainFlag` surviving a cancel; re-establish state afterward.
