---
title: "Effects & Stats Reference"
description: "Hytale status effects and stats in JSON — buffs, debuffs, DoT and transformations, damage immunity and resistance modifiers, and stat modifiers with calculation control."
seo:
  type: TechArticle
---

# Effects & Stats Reference

**Doc type:** JSON asset format · **Assets:** `Server/Entity` · **Verified against 0.5.0**

This document covers the JSON asset structure for status effects and entity stats.

> **See also:** [ApplyEffect Interaction](interactions-combat.md#applyeffect) for applying effects via interactions, [ChangeStat Interaction](interactions-combat.md#changestat) for modifying stats.

---

## Overview

Defined as JSON assets under `Server/Entity/` in `Assets.zip` and provides:
- Status effect definitions (`Server/Entity/Effects/`): buffs, debuffs, DoT, transformations
- Damage immunity and per-type `DamageResistance` modifiers
- Stat modifiers (`StatModifiers`, `RawStatModifiers`) with calculation control
- Application/tick effect hooks (particles, sounds, tints, movement/ability restrictions)
- Stat definitions (`Server/Entity/Stats/`): bounds, regeneration, and min/max value effects
- A condition system gating regeneration rules

## Architecture
```
Server/Entity/
├── Effects/   Status effect definitions
│   ├── Core: Duration / Infinite / OverlapBehavior / Debuff
│   ├── Invulnerable / DamageResistance / ModelChange
│   ├── StatModifiers / RawStatModifiers (+ DamageCalculatorCooldown)
│   ├── ApplicationEffects  (one-time: particles, sounds, tints, movement/ability)
│   └── StatModifierEffects (per-tick: WorldParticles / WorldSoundEventId)
└── Stats/     Stat definitions
    ├── Core: InitialValue / Min / Max / Shared / ResetType
    ├── Regenerating[]   (Interval / Amount / RegenType + Conditions)
    ├── Condition Ids    (Alive, IsPlayer, Stat, NoDamageTaken, Sprinting, ...)
    └── MinValueEffects / MaxValueEffects  (Interactions on min/max)
```

## Key Classes
These are JSON asset constructs (field schemas), not Java classes.

| Construct | Location | Description |
|-----------|----------|-------------|
| Effect definition | `Server/Entity/Effects/` | A status effect (buff/debuff/transform) |
| `DamageResistance` | effect JSON | Per-damage-type resistance modifiers |
| `StatModifiers` / `RawStatModifiers` | effect JSON | Stat changes (simple vs. calculation-controlled) |
| `ApplicationEffects` | effect JSON | One-time effects applied when the effect starts |
| `StatModifierEffects` | effect JSON | Effects triggered on each stat-modifier tick |
| Stat definition | `Server/Entity/Stats/` | Bounds, regen, and value-trigger rules for a stat |
| `Regenerating` | stat JSON | Automatic stat recovery/drain rules with conditions |
| `MinValueEffects` / `MaxValueEffects` | stat JSON | Interactions run when a stat hits min/max |

## Effects (Status Effects)

**Asset location:** `Server/Entity/Effects/` in Assets.zip

Status effects are temporary modifications applied to entities - buffs, debuffs, damage over time, transformations, and more.

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `Duration` | float | Effect duration in seconds |
| `Infinite` | boolean | Effect persists until manually removed |
| `OverlapBehavior` | string | `Overwrite` (replace existing), `Extend` (add duration) |
| `Debuff` | boolean | Marks as negative effect (for cleanse mechanics) |
| `StatusEffectIcon` | string | UI icon path for effect display |
| `RemovalBehavior` | string | How effect is removed (e.g., `Duration`) |

### Damage Immunity & Resistance

| Property | Type | Description |
|----------|------|-------------|
| `Invulnerable` | boolean | Grants complete damage immunity |
| `DamageResistance` | object | Per-damage-type resistance modifiers |

**DamageResistance example:**

`DamageResistance` maps each damage type to an array of modifier objects (`{ CalculationType, Amount }`):

```json
{
  "DamageResistance": {
    "Fire": [
      { "Amount": 1.0, "CalculationType": "Multiplicative" }
    ],
    "Physical": [
      { "CalculationType": "Multiplicative", "Amount": 0.05 }
    ]
  }
}
```

For `Multiplicative`, `Amount` is the fraction of damage removed (1.0 = immune, 0.05 = 5% reduction, 0 = no resistance).

### Model Transformation

| Property | Type | Description |
|----------|------|-------------|
| `ModelChange` | string | Transform entity into a different model (morph effects) |

**Example (Morph Potion):**

```json
{
  "Duration": 60,
  "ModelChange": "Corgi",
  "OverlapBehavior": "Overwrite"
}
```

`ModelChange` is the model/creature identifier to morph into (e.g. `"Corgi"`), not a file path.

---

### Stat Modifiers

Effects can modify entity stats over time using two systems:

#### Simple StatModifiers

For basic stat changes with optional percentage-based values:

| Property | Type | Description |
|----------|------|-------------|
| `StatModifiers` | object | Map of stat names to modification values |
| `ValueType` | string | `"Percent"` for percentage-based, omit for absolute |

```json
{
  "StatModifiers": {
    "HorizontalSpeed": 0.3
  },
  "ValueType": "Percent"
}
```

#### RawStatModifiers

For complex stat changes with calculation control. `RawStatModifiers` maps each stat name to an array of modifier objects:

| Property | Type | Description |
|----------|------|-------------|
| `Amount` | number | Value to apply (for `Multiplicative`, a factor such as `1.15` = +15%) |
| `CalculationType` | string | How to calculate (`Additive`, `Multiplicative`) |
| `Target` | string | Which value to target (`Max`, `Current`) |

```json
{
  "RawStatModifiers": {
    "Health": [
      {
        "Amount": 1.15,
        "CalculationType": "Multiplicative",
        "Target": "Max"
      }
    ]
  }
}
```

#### DamageCalculatorCooldown

| Property | Type | Description |
|----------|------|-------------|
| `DamageCalculatorCooldown` | float | Cooldown between stat modifier ticks (seconds) |

---

### ApplicationEffects

Effects applied when the status effect starts (one-time application):

| Property | Type | Description |
|----------|------|-------------|
| `EntityTopTint` | string | Hex color tint applied to top of entity model |
| `EntityBottomTint` | string | Hex color tint applied to bottom of entity model |
| `HorizontalSpeedMultiplier` | float | Movement speed modifier (0.0-1.0) |
| `LocalSoundEventId` | string | Sound played for the affected entity only |
| `WorldSoundEventId` | string | Sound played for all nearby entities |
| `Particles` | array | Particle systems to spawn on the entity |
| `ScreenEffect` | string | Screen overlay effect for the affected player |

**Movement restriction:**

| Property | Type | Description |
|----------|------|-------------|
| `MovementEffects.DisableAll` | boolean | Completely disable all movement |

**Ability restriction:**

| Property | Type | Description |
|----------|------|-------------|
| `AbilityEffects.Disabled` | array | List of abilities to disable (`Primary`, `Secondary`) |

**Example (Stun Effect):**

```json
{
  "Duration": 2,
  "Debuff": true,
  "ApplicationEffects": {
    "MovementEffects": {
      "DisableAll": true
    },
    "AbilityEffects": {
      "Disabled": ["Primary", "Secondary"]
    },
    "WorldSoundEventId": "SFX_Stun_Apply",
    "Particles": [
      { "SystemId": "Stun_Stars", "Bone": "Head" }
    ]
  }
}
```

---

### StatModifierEffects

Effects triggered each time stat modifiers tick:

| Property | Type | Description |
|----------|------|-------------|
| `WorldParticles` | array | Particles spawned on stat tick |
| `WorldSoundEventId` | string | Sound played on stat tick |

**Example (Regeneration with visual feedback):**

```json
{
  "Duration": 10,
  "StatModifiers": {
    "Health": 2
  },
  "DamageCalculatorCooldown": 1.0,
  "StatModifierEffects": {
    "WorldParticles": [
      { "SystemId": "Heal_Sparkle" }
    ],
    "WorldSoundEventId": "SFX_Heal_Tick"
  }
}
```

---

### Complete Effect Examples

#### Simple Buff (Food Effect)

From `Server/Entity/Effects/Food/Buff/Meat_Buff_T1.json`:

```json
{
  "RawStatModifiers": {
    "Health": [
      {
        "Amount": 1.05,
        "CalculationType": "Multiplicative",
        "Target": "Max"
      }
    ]
  },
  "OverlapBehavior": "Overwrite",
  "Duration": 45,
  "StatusEffectIcon": "UI/StatusEffects/AddHealth/Tiny.png"
}
```

#### Regeneration Potion

From `Server/Entity/Effects/Potion/Potion_Health_Regen_Lesser.json`:

```json
{
  "StatModifiers": {
    "Health": 15
  },
  "ValueType": "Percent",
  "DamageCalculatorCooldown": 5,
  "Duration": 5.05,
  "OverlapBehavior": "Overwrite",
  "StatusEffectIcon": "Icons/ItemsGenerated/Potion_Health_Lesser.png",
  "ApplicationEffects": {
    "Particles": [
      {
        "SystemId": "Potion_Health_Heal",
        "TargetEntityPart": "Entity",
        "TargetNodeName": "Pelvis"
      }
    ]
  },
  "StatModifierEffects": {
    "WorldParticles": [
      {
        "SystemId": "Potion_Health_Implosion",
        "PositionOffset": { "Y": 1.0 }
      }
    ],
    "WorldSoundEventId": "SFX_Deployable_Totem_Heal_Despawn"
  }
}
```

#### Stun Effect (Bomb)

From `Server/Entity/Effects/Projectiles/Bomb/Bomb_Explode_Stun.json`:

```json
{
  "ApplicationEffects": {
    "EntityTopTint": "#008000",
    "EntityBottomTint": "#000000",
    "ScreenEffect": "ScreenEffects/Poison.png",
    "Particles": [
      { "SystemId": "Effect_Poison" }
    ],
    "MovementEffects": {
      "DisableAll": true
    },
    "AbilityEffects": {
      "Disabled": ["Primary", "Secondary"]
    }
  },
  "Duration": 5,
  "OverlapBehavior": "Extend"
}
```

#### Morph Effect (Transformation Potion)

From `Server/Entity/Effects/Potion/Potion_Morph_Dog.json`:

```json
{
  "StatusEffectIcon": "Icons/ItemsGenerated/Potion_Purify.png",
  "OverlapBehavior": "Overwrite",
  "Duration": 60,
  "ModelChange": "Corgi",
  "ApplicationEffects": {
    "Particles": [
      { "SystemId": "Potion_Morph_Burst" }
    ],
    "WorldSoundEventId": "SFX_Wolf_Alerted"
  }
}
```

#### Damage Immunity (Dodge Invulnerability)

From `Server/Entity/Effects/Movement/Dodge_Invulnerability.json`:

```json
{
  "Duration": 0.25,
  "Invulnerable": true
}
```

#### Damage Resistance (Fire Immunity)

From `Server/Entity/Effects/Immunity/Immunity_Fire.json`:

```json
{
  "Infinite": true,
  "DamageResistance": {
    "Fire": [
      { "Amount": 1.0, "CalculationType": "Multiplicative" }
    ]
  }
}
```

---

## Applying Effects from Java

The JSON above defines effect *assets*; to apply one to an entity at runtime — for crowd control
(freeze/stun/root), buffs on a custom item, etc. — go through the entity's **`EffectControllerComponent`**
(`com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent`).

The built-in CC assets live under `Server/Entity/Effects/Status/` — e.g. **`Stun`** and **`Root`**
(`MovementEffects.DisableAll: true`; `Stun` also disables abilities), and **`Freeze`**.

```java
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;

// Resolve the named asset → index → effect. getAsset takes an int, so resolve the name first:
var effectMap = EntityEffect.getAssetMap();
EntityEffect stun = effectMap.getAsset(effectMap.getIndex("Stun"));

EffectControllerComponent ctrl =
    store.getComponent(ref, EffectControllerComponent.getComponentType());

// Duration is in SECONDS (float).
ctrl.addEffect(ref, stun, 5.0f, OverlapBehavior.OVERWRITE, accessor);

ctrl.clearEffects(ref, accessor);   // remove everything
```

- **Duration is in seconds** (a `float`), not ticks.
- Effects **auto-clear on respawn** (the engine's `ClearEntityEffectsRespawnSystem`), so you don't
  need to strip CC from a player you're about to respawn.
- **Freezing players vs NPCs uses two different mechanisms — each a no-op on the other kind.**
  Player movement is client-driven and is only halted by a **status effect** with
  `MovementEffects.DisableAll` (`Stun` / `Root`); applying it to an NPC shows the VFX/tint but does
  **not** stop its AI — a stunned bear keeps pathing and attacking. NPC AI is halted by the
  **`Frozen` component** (`com.hypixel.hytale.server.core.entity.Frozen`, singleton `Frozen.get()` /
  `Frozen.getComponentType()`, used by `NPCFreezeCommand`), which in turn does **nothing** to a
  player. To freeze *everything* in an arena, apply both to every living entity — each is harmless on
  the type it doesn't affect. Add/remove the `Frozen` component through the
  [`CommandBuffer`](components.md#commandbufferecs_type) (it's a structural change), while `addEffect`
  mutates `EffectControllerComponent` in place and is safe inline.
- Note the asymmetry on respawn: status effects auto-clear (above), but the `Frozen` component does
  **not** — remove it explicitly with `buffer.tryRemoveComponent(ref, Frozen.getComponentType())`.

---

## Stat Definitions

**Asset location:** `Server/Entity/Stats/` in Assets.zip

Stat definitions configure how entity stats behave - their bounds, regeneration rules, and effects when reaching minimum or maximum values.

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `InitialValue` | number | Starting value for the stat |
| `Min` | number | Minimum allowed value (can be negative) |
| `Max` | number | Maximum allowed value |
| `Shared` | boolean | Whether stat value is visible to other players |
| `ResetType` | string | How stat resets (e.g., `MaxValue` to reset to max) |

**Basic stat definition:**

```json
{
  "InitialValue": 100,
  "Min": 0,
  "Max": 100,
  "Shared": true
}
```

---

### Regeneration System

The `Regenerating` array defines automatic stat recovery/drain rules. Each entry creates a regeneration rule that ticks independently.

#### Regenerating Entry Properties

| Property | Type | Description |
|----------|------|-------------|
| `Interval` | float | Seconds between regeneration ticks |
| `Amount` | number | Amount to change per tick (negative for drain) |
| `RegenType` | string | `Additive` (flat amount) or `Percentage` (percent of max) |
| `ClampAtZero` | boolean | Stop regeneration when stat reaches zero |
| `Conditions` | array | Conditions that must be met for this regen to apply |

**Simple regeneration:**

```json
{
  "Regenerating": [
    {
      "Interval": 1.0,
      "Amount": 5,
      "RegenType": "Additive"
    }
  ]
}
```

---

### Condition Types

Conditions control when regeneration rules apply. Each condition object is keyed by `Id`. Multiple conditions in an array must ALL be true.

| Condition Id | Properties | Description |
|--------------|------------|-------------|
| `Alive` | - | Entity must be alive |
| `IsPlayer` | `Inverse` | Entity is (or, inverted, is not) a player |
| `CheckPlayerGameMode` | `GameMode` | Player must be in specified game mode |
| `Stat` | `Stat`, `Amount`, `Comparison` | Another stat must meet a threshold |
| `NoDamageTaken` | `Delay` | No damage received for X seconds |
| `Suffocating` | - | Entity is suffocating in a block |
| `Sprinting` | - | Entity is sprinting |
| `Gliding` | - | Entity is gliding |
| `Wielding` | - | Entity is wielding/blocking |
| `Charging` | - | Entity is charging an interaction |
| `RegenHealth` | - | Health regeneration is enabled |

All conditions support an `Inverse` property to negate the check:

```json
{
  "Id": "Sprinting",
  "Inverse": true
}
```

#### Comparison Values

For `Stat` conditions:

| Value | Meaning |
|-------|---------|
| `Gte` | Greater than or equal to (>=) |
| `Lt` | Less than (<) |

**Stat condition example:**

```json
{
  "Id": "Stat",
  "Stat": "Stamina",
  "Amount": 0,
  "Comparison": "Gte"
}
```

---

### MinValueEffects / MaxValueEffects

Trigger interactions when stat reaches its minimum or maximum value.

| Property | Type | Description |
|----------|------|-------------|
| `TriggerAtZero` | boolean | Whether to trigger when stat hits zero |
| `Interactions` | object | Interactions to run when triggered |

**Example (death on zero health):**

```json
{
  "MinValueEffects": {
    "TriggerAtZero": true,
    "Interactions": {
      "Interactions": [
        { "Type": "Kill" }
      ]
    }
  }
}
```

**Example (visual effect at max energy):**

```json
{
  "MaxValueEffects": {
    "Interactions": {
      "Interactions": [
        {
          "Type": "ApplyEffect",
          "EffectId": "FullEnergy_Glow"
        }
      ]
    }
  }
}
```

---

### Complete Stat Examples

#### Health Stat

From `Server/Entity/Stats/Health.json`:

```json
{
  "InitialValue": 100,
  "Min": 0,
  "Max": 100,
  "Shared": true,
  "ResetType": "MaxValue",
  "Regenerating": [
    {
      "$Comment": "NPC",
      "Interval": 0.5,
      "Amount": 0.05,
      "RegenType": "Percentage",
      "Conditions": [
        { "Id": "Alive" },
        { "Id": "IsPlayer", "Inverse": true },
        { "Id": "NoDamageTaken", "Delay": 15 },
        { "Id": "RegenHealth" }
      ]
    },
    {
      "$Comment": "Player in creative mode",
      "Interval": 0.5,
      "Amount": 1.0,
      "RegenType": "Percentage",
      "Conditions": [
        { "Id": "Alive" },
        { "Id": "CheckPlayerGameMode", "GameMode": "Creative" }
      ]
    }
  ]
}
```

This health stat:
- Starts and caps at 100
- Regenerates 5%/0.5s for non-player entities when alive, regen enabled, and no damage taken for 15 seconds
- Regenerates 100%/0.5s for players in Creative mode (instant regen)

#### Stamina Stat

From `Server/Entity/Stats/Stamina.json`:

```json
{
  "InitialValue": 10,
  "Min": -4,
  "Max": 10,
  "Shared": false,
  "Regenerating": [
    {
      "$Comment": "Positive stamina regeneration values",
      "Interval": 0.1,
      "Amount": 0.3,
      "RegenType": "Additive",
      "Conditions": [
        { "Id": "Stat", "Stat": "StaminaRegenDelay", "Amount": 0 },
        { "Id": "Stat", "Stat": "Stamina", "Amount": 0, "Comparison": "Gte" },
        { "Id": "Wielding", "Inverse": true },
        { "Id": "Sprinting", "Inverse": true },
        { "Id": "Gliding", "Inverse": true }
      ]
    },
    {
      "Interval": 0.1,
      "Amount": -0.1,
      "ClampAtZero": true,
      "RegenType": "Additive",
      "Conditions": [
        { "Id": "Sprinting" }
      ]
    }
  ],
  "MinValueEffects": {
    "TriggerAtZero": true,
    "Interactions": {
      "Interactions": [
        "Stamina_Bar_Flash",
        "Stamina_Broken_Check",
        {
          "Type": "ChangeStat",
          "Behaviour": "Set",
          "StatModifiers": { "StaminaRegenDelay": -0.5 }
        }
      ]
    }
  },
  "MaxValueEffects": {
    "Interactions": {
      "Interactions": [
        {
          "Type": "ClearEntityEffect",
          "EntityEffectId": "Stamina_Broken"
        }
      ]
    }
  }
}
```

This stamina stat (the real file includes additional creative-mode, overdrawn, and gliding-drain rules, omitted here for brevity):
- Caps at 10 with a `-4` overdrawn floor
- Regenerates 0.3/tick when stamina is non-negative, the `StaminaRegenDelay` gate has elapsed, and the entity is not wielding, sprinting, or gliding
- Drains 0.1/tick while sprinting
- On hitting zero, flashes the bar, runs the broken check, and sets a regen delay
- Clears the `Stamina_Broken` effect when reaching full

#### Mana Stat

From `Server/Entity/Stats/Mana.json`:

```json
{
  "InitialValue": 0,
  "Min": 0,
  "Max": 0,
  "Shared": false,
  "ResetType": "MaxValue",
  "Regenerating": [
    {
      "Interval": 0.2,
      "Amount": 1,
      "RegenType": "Additive",
      "Conditions": [
        { "Id": "Alive" },
        { "Id": "NoDamageTaken", "Delay": 6 },
        { "Id": "Charging", "Inverse": true }
      ]
    }
  ]
}
```

This mana stat:
- Defaults to a 0 cap (raised by gear/effects that grant max mana)
- Regenerates 1/0.2s when alive, not damaged for 6 seconds, and not charging

#### Oxygen Stat

From `Server/Entity/Stats/Oxygen.json`:

```json
{
  "InitialValue": 100,
  "Min": 0,
  "Max": 100,
  "Shared": false,
  "Regenerating": [
    {
      "Interval": 0.5,
      "Amount": 25,
      "RegenType": "Additive",
      "Conditions": [
        { "Id": "Alive" },
        { "Id": "Suffocating", "Inverse": true }
      ]
    },
    {
      "$Comment": "Player in creative mode",
      "Interval": 0.5,
      "Amount": 1.0,
      "RegenType": "Percentage",
      "Conditions": [
        { "Id": "Alive" },
        { "Id": "CheckPlayerGameMode", "GameMode": "Creative" }
      ]
    },
    {
      "Interval": 0.5,
      "Amount": -3,
      "RegenType": "Additive",
      "Conditions": [
        { "Id": "Alive" },
        { "Id": "Suffocating" }
      ]
    }
  ]
}
```

This oxygen stat:
- Regenerates quickly (25/0.5s) when alive and not suffocating
- Refills instantly for players in Creative mode
- Drains 3/0.5s while suffocating

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 effect/stat subsystem (verified against `HytaleServer.jar`).

- **`Unknown EntityEffect with index`** → an effect was applied/cleared by an id that doesn't resolve to a loaded effect asset (e.g. an `ApplyEffect`/`ClearEntityEffect` `EffectId`/`EntityEffectId` typo). Fix: the id must match an effect file under `Server/Entity/Effects/` exactly (case-sensitive).
- **Symptom:** a `DamageResistance` of `0` lets full damage through and `1.0` blocks everything (feels inverted) → for `Multiplicative`, `Amount` is the *fraction removed* (`1.0` = immune, `0` = no resistance). Fix: use `Amount` as the removed fraction, not the surviving fraction.
- **Symptom:** a `Multiplicative` `RawStatModifiers` `Amount` of `1.15` doesn't add 15% → for `Multiplicative` the value is a factor (`1.15` ≈ +15%, `1.0` = no change), not an additive bonus. Fix: use `Additive` with the flat delta if you want a plain add.
- **Symptom:** a stat with `Max: 0` (e.g. Mana) never holds any value → its cap starts at 0 and is meant to be raised by gear/effects granting max. Fix: grant a max-stat modifier rather than only adding current value.
- **Symptom:** a `Regenerating` rule never ticks → one of its `Conditions` is unmet, and all conditions in the array must be true. Fix: check each `Id` (and any `Inverse`), since e.g. `NoDamageTaken`/`CheckPlayerGameMode` silently gate the whole rule.
- **Symptom:** an effect doesn't refresh/stack as expected → behavior is set by `OverlapBehavior` (`Overwrite` replaces, `Extend` adds duration). Fix: set `OverlapBehavior` explicitly for re-application.
