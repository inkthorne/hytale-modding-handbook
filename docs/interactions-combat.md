---
title: "Combat & Effects Interactions"
description: "Hytale combat interactions in JSON — the Simple interaction for delays/animations/sounds/particles, Selector for melee/AOE/raycast targeting, and damage and effect application."
seo:
  type: TechArticle
---

# Combat & Effects Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.5.2**

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

This page covers the combat and effects interactions: target selection, dealing damage, applying forces and status effects, modifying stats, and interrupting other entities.

## Overview

Defined as JSON interaction assets (server classes under `com.hypixel.hytale.server.core.modules.interaction.interaction.config`) and provides:
- A versatile `Simple` interaction for delays, animations, sounds, particles, and flow control
- A `Selector` for melee/AOE/raycast hitbox target selection
- `DamageEntity` for damage (via `DamageCalculator`) with knockback, sounds, and stat grants
- `ApplyForce` for physics-based knockback and launches
- `ApplyEffect` / `ClearEntityEffect` for adding and removing status effects
- `ChangeStat` for modifying health, stamina, and signature energy
- `Interrupt` for cancelling a target's active interaction chain

## Architecture
```
Combat & Effects
├── Targeting
│   └── Selector (Horizontal / AOECircle / Raycast / Stab) → HitEntity / HitBlock
├── Damage
│   ├── DamageEntity (DamageCalculator + DamageEffects + EntityStatsOnHit)
│   └── ApplyForce (Direction + Force knockback/launch)
├── Status effects
│   ├── ApplyEffect (EffectId → effect asset)
│   └── ClearEntityEffect (EntityEffectId / EntityEffectIds)
├── Stats
│   └── ChangeStat (StatModifiers, Behaviour, ValueType)
├── Control
│   └── InterruptInteraction (cancel target chain; ExcludedTag immunity)
└── SimpleInteraction (delays, animations, sounds, flow via Next / Failed)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `SimpleInteraction` | `config` (server + `protocol`) | Base building-block interaction; delays, animations, sounds, flow control |
| `Selector` (`SelectInteraction`) | `config/none/SelectInteraction` | Hitbox/target selection for melee, AOE, raycast, and stab |
| `DamageEntity` (`DamageEntityInteraction`) | `config/server/DamageEntityInteraction` | Deals damage via `DamageCalculator` with `DamageEffects` |
| `ApplyForce` (`ApplyForceInteraction`) | `config/client/ApplyForceInteraction` | Applies a physics force for knockback/launches |
| `ApplyEffect` (`ApplyEffectInteraction`) | `config/none/ApplyEffectInteraction` | Applies a status effect by `EffectId` |
| `ClearEntityEffect` (`ClearEntityEffectInteraction`) | `config/server/ClearEntityEffectInteraction` | Removes status effects by id |
| `InterruptInteraction` | `config/server/InterruptInteraction` | Cancels the target's current interaction chain |

## Quick Navigation

| Interaction | Description |
|-------------|-------------|
| [SimpleInteraction](#simpleinteraction) | Delays, animations, sounds, and flow control |
| [Selector](#selector) | Target selection for melee attacks (hitboxes) |
| [DamageEntity](#damageentity) | Deal damage with effects, knockback, and stat grants |
| [ApplyForce](#applyforce) | Apply physics forces for knockback and launches |
| [ApplyEffect](#applyeffect) | Apply status effects (buffs, debuffs, DoT) |
| [ClearEntityEffect](#clearentityeffect) | Remove status effects from entities |
| [ChangeStat](#changestat) | Modify health, stamina, signature energy |
| [InterruptInteraction](#interruptinteraction) | Cancel an entity's current interaction chain |

---

## SimpleInteraction

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

**Class hierarchy:** `SimpleInteraction` → `Interaction`

**Protocol class:** `com.hypixel.hytale.protocol.SimpleInteraction` (handles client-server synchronization)

A fundamental building block interaction that does nothing other than provide base interaction features. Despite its simplicity, it's one of the most versatile interaction types, used for delays, triggering animations, playing sounds, and controlling flow between other interactions.

### Purpose

SimpleInteraction serves as:
- **Delay mechanism** - Creates timed pauses between interactions via `RunTime`
- **Animation trigger** - Plays item/player animations via `Effects.ItemAnimationId`
- **Audio controller** - Plays sounds via `Effects.WorldSoundEventId` and `Effects.LocalSoundEventId`
- **Visual effects** - Spawns particles and trails via `Effects.Particles` and `Effects.Trails`
- **Flow control** - Chains interactions via `Next` and handles failures via `Failed`
- **No-op placeholder** - Acts as an empty interaction when no action is needed

### Inherited Properties (from Interaction)

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `RunTime` | float | `0` | Duration in seconds before completing |
| `Effects` | InteractionEffects | - | Visual and audio effects configuration |
| `HorizontalSpeedMultiplier` | float | `1.0` | Movement speed modifier during interaction (0.0-1.0) |
| `ViewDistance` | double | - | View distance modifier |
| `CancelOnItemChange` | boolean | `false` | Cancel if held item changes |
| `Settings` | Map<GameMode, InteractionSettings> | - | Per-gamemode settings |
| `Rules` | InteractionRules | - | Interaction rules |
| `Camera` | InteractionCameraSettings | - | Camera settings during interaction |

### SimpleInteraction-Specific Properties

| Property | Type | Default | Validator | Description |
|----------|------|---------|-----------|-------------|
| `Next` | string/object | - | Late validator (VALIDATOR_CACHE) | Interaction(s) to run when this interaction succeeds |
| `Failed` | string/object | - | Late validator (VALIDATOR_CACHE) | Interaction(s) to run when this interaction fails |

### Effects Configuration

The `Effects` object supports these properties:

| Property | Type | Description |
|----------|------|-------------|
| `ItemAnimationId` | string | Animation to play on the held item |
| `ItemPlayerAnimationsId` | string | Player animation set ID |
| `WorldSoundEventId` | string | Sound audible to all nearby players |
| `LocalSoundEventId` | string | Sound only the executing player hears |
| `ClearAnimationOnFinish` | boolean | Stop animation when interaction ends |
| `ClearSoundEventOnFinish` | boolean | Stop sound when interaction ends |
| `WaitForAnimationToFinish` | boolean | Wait for animation before completing |
| `Particles` | array | Particles attached to model bones |
| `FirstPersonParticles` | array | Particles for first-person view |
| `Trails` | array | Weapon trail effects |
| `CameraEffect` | string | Camera effect id (shake, zoom, etc.) |
| `MovementEffects` | object | Movement modification effects |
| `StartDelay` | float | Delay before effects begin |

> ⚠️ **The generic `Effects` block has no `WorldParticles` field.** `Particles` above are
> `ModelParticle`s attached to model bones (`InteractionEffects.particles`); there is **no**
> world-space particle option here. Only [`DamageEffects`](#damageeffects-properties) (combat hits)
> carries `WorldParticles`. A stray `"WorldParticles"` key in a generic `Effects` block is **silently
> dropped** — the engine logs an `AssetStore` warning (`Unused key(s) in '<asset>': Effects.WorldParticles`)
> and the particles never spawn (this is even latent in vanilla `Projectile_Config_Ice_Ball`'s
> `ProjectileMiss`). Because the sibling `WorldSoundEventId` *is* a valid key, the **sound plays while
> the particles vanish** — a misleading symptom. To spawn world-space particles outside a damage event,
> spawn from code with [`ParticleUtil`](projectiles.md#spawning-particles-from-java).

### Sounds (World vs Local)

**World sounds** are audible to all nearby players - use for attack impacts, explosions, and actions others should hear:

```json
{
  "Type": "Simple",
  "Effects": {
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"
  }
}
```

**Local sounds** are only heard by the executing player - use for UI feedback, personal notifications:

```json
{
  "Type": "Simple",
  "RunTime": 0,
  "Effects": {
    "LocalSoundEventId": "SFX_Consume_Bread_Local",
    "ClearSoundEventOnFinish": true
  }
}
```

### Particles & Trails

**Trail effects** for weapons:

```json
{
  "Type": "Simple",
  "RunTime": 0.177,
  "Effects": {
    "Trails": [
      {
        "PositionOffset": { "X": 0.4, "Y": -0.2, "Z": 0 },
        "RotationOffset": { "Pitch": 0, "Roll": 90, "Yaw": 0 },
        "TargetNodeName": "Handle",
        "TrailId": "Small_Default"
      }
    ],
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"
  }
}
```

### WaitForDataFrom Enum

Controls client-server synchronization behavior (accessible via `getWaitForDataFrom()`):

| Value | Description |
|-------|-------------|
| `Client` | Wait for data from the client |
| `Server` | Wait for data from the server |
| `None` | No synchronization needed (default for SimpleInteraction) |

### Key Methods

```java
// Synchronization
WaitForDataFrom getWaitForDataFrom()   // Returns None by default
boolean needsRemoteSync()              // True if Next or Failed need sync

// Execution flow
void compile(OperationsBuilder builder)
boolean walk(Collector collector, InteractionContext context)  // Visitor pattern for tree traversal
```

### Complete Examples

**Basic delay:**

```json
{
  "Type": "Simple",
  "RunTime": 0.2,
  "$Comment": "Delay before next consume cycle can start to prevent sound overlap"
}
```

**Animation trigger with sound:**

```json
{
  "Type": "Simple",
  "RunTime": 0.177,
  "Effects": {
    "ItemAnimationId": "SwingDown",
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"
  }
}
```

**Flow control with Next:**

```json
{
  "Type": "Simple",
  "Next": {
    "Type": "UseBlock",
    "Failed": "Block_Attack"
  }
}
```

**Empty no-op (failure handler):**

```json
{
  "Type": "Charging",
  "FailOnDamage": true,
  "Next": { "4.0": "..." },
  "Failed": {
    "Type": "Simple"
  }
}
```

**Prepare delay before combat:**

```json
{
  "Type": "Simple",
  "Effects": {
    "ItemAnimationId": "SwingDown"
  },
  "$Comment": "Prepare Delay",
  "RunTime": 0.244,
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Interactions": ["Axe_Swing_Down_Damage"] },
      { "Interactions": ["Axe_Swing_Down_Effect"] }
    ]
  }
}
```

### Common Patterns

| Pattern | Use Case | Key Properties |
|---------|----------|----------------|
| **Delay** | Pause between chain steps | `RunTime` only |
| **Animation trigger** | Play weapon/item animation | `Effects.ItemAnimationId` |
| **Sound effect** | Audio feedback | `Effects.WorldSoundEventId`, `Effects.LocalSoundEventId` |
| **Visual effect** | Trails, particles | `Effects.Trails`, `Effects.Particles` |
| **Flow control** | Chain to next interaction | `Next` |
| **No-op** | Empty failure handler | Empty `{"Type": "Simple"}` |
| **Prepare phase** | Wind-up before attack | `RunTime` + `Effects.ItemAnimationId` |

### Technical Notes

- **Default behavior** - Without `Next` or `Failed`, the interaction completes immediately after `RunTime` elapses
- **Sync behavior** - `getWaitForDataFrom()` returns `None`, meaning SimpleInteraction doesn't inherently require client-server sync. However, if `Next` or `Failed` reference interactions that need sync, `needsRemoteSync()` returns true.
- **Tick behavior** - On each tick, if state is `Failed` and labels exist, jumps to the failure label (index 0)
- **Protocol** - Serializes `next` and `failed` as integer indices referencing the interaction asset map
- **Inheritance** - `SimpleInstantInteraction` extends this class for instant (no duration) interactions

### Related Interactions

- [Interaction](interactions.md#interaction-base-class) - Base class providing inherited properties
- [Serial](interactions-flow.md#serial) - Often used to chain multiple SimpleInteractions
- [Parallel](interactions-flow.md#parallel) - Execute SimpleInteractions concurrently
- [ChargingInteraction](interactions-combo.md#charginginteraction) - Uses SimpleInteraction for `Failed` handlers

---

## Selector

**Package:** `config/none/SelectInteraction`

Target selection for combat interactions. Defines hitbox shapes and detection areas for melee attacks, and executes interactions when entities or blocks are hit.

### Structure

```json
{
  "Type": "Selector",
  "RunTime": 0.1,
  "Selector": {
    "Id": "Horizontal",
    "Direction": "ToRight",
    "TestLineOfSight": true,
    "ExtendTop": 0.5,
    "ExtendBottom": 0.5,
    "StartDistance": 0.1,
    "EndDistance": 2.5,
    "Length": 60,
    "RollOffset": 45,
    "YawStartOffset": -15
  },
  "HitEntity": {
    "Interactions": [
      "Sword_Swing_Damage"
    ]
  }
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `RunTime` | float | Duration of the selection window in seconds |
| `Selector` | object | Hitbox configuration (see Selector Types below) |
| `HitEntity` | object | Interactions to execute when an entity is hit |
| `HitBlock` | object | Interactions to execute when a block is hit |
| `HitEntityRules` | array | Conditional hit handling with matchers |
| `IgnoreOwner` | boolean | Whether to ignore the attacking entity |
| `FailOn` | string | Condition that causes the selector to fail |

### Selector Types

#### Horizontal (Sweeping attacks)

Used for sword swings and wide melee attacks.

```json
{
  "Id": "Horizontal",
  "Direction": "ToRight",
  "TestLineOfSight": true,
  "ExtendTop": 0.5,
  "ExtendBottom": 0.5,
  "StartDistance": 0.1,
  "EndDistance": 2.5,
  "Length": 60,
  "RollOffset": 45,
  "YawStartOffset": -15
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Direction` | string | `"ToLeft"` or `"ToRight"` - sweep direction |
| `TestLineOfSight` | boolean | Check for obstacles between attacker and target |
| `ExtendTop` | float | Hitbox extension upward |
| `ExtendBottom` | float | Hitbox extension downward |
| `StartDistance` | float | Starting distance from attacker |
| `EndDistance` | float | Maximum reach distance |
| `Length` | float | Arc length in degrees |
| `RollOffset` | float | Rotation offset around forward axis |
| `YawStartOffset` | float | Starting yaw offset in degrees |

#### AOECircle (Area of effect)

Used for ground slams and radial attacks.

```json
{
  "Id": "AOECircle",
  "Range": 4
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Range` | float | Radius of the circular area |
| `Offset` | object | `{ "X", "Y", "Z" }` offset of the disc center from the entity position |

> ⚠️ **`AOECircle` is a flat, zero-height disc.** `AOECircleSelector` has only `Range` (radius) +
> `Offset`, so a ground-level circle misses entities whose model center sits above the impact plane.
> For vertical reach use **`AOECylinder`** (`AOECylinderSelector extends AOECircleSelector`), which
> adds a `Height` field — though no shipped asset uses it (only `AOECircle`, `Horizontal`, `Stab`,
> `Raycast` appear in `Server/`), so it is untested in content despite having a registered codec.
>
> ⚠️ **A selector in a *projectile's* `ProjectileHit`/`ProjectileMiss` does NOT sweep a radius** — it
> resolves only the entity the projectile directly collides with (unlike a melee swing, which sweeps).
> To do real AOE from a projectile impact, use `Type: "Explode"`, a [trigger volume](trigger-volumes.md),
> or a Java radius query (`Selector.selectNearbyEntities(accessor, pos, radius, consumer, predicate)` —
> the static query `ExplosionUtils.performExplosion` uses internally).
>
> ⚠️ **`Explode` (`ExplosionConfig`) cannot apply a status effect.** It does radius **damage +
> knockback + `ModelParticles` + sound** (`damageEntities`, `entityDamageRadius`, `entityDamage`,
> `knockback`, `particles`, `soundEventId`, plus block damage) — but has **no field for an
> entity/status effect**. So `Explode` covers AOE *damage*, not AOE *slow/stun/etc.* For AOE **effects**
> you need a Java radius query + `EffectControllerComponent.addEffect` (see
> [interactions.md → Registering a Custom Interaction Type](interactions.md#registering-a-custom-interaction-type-java)),
> a deployable/trap with `ApplyEffects` and `DamageAmount: 0`, or a trigger volume's `EntityEffect`.

#### Raycast (Straight line)

Used for wand spells and targeted abilities.

```json
{
  "Id": "Raycast",
  "Offset": {
    "Y": 1.6
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Offset` | object | Starting point offset from entity position |

#### Stab (Thrust attacks)

Used for spear thrusts and lunging attacks.

```json
{
  "Id": "Stab",
  "TestLineOfSight": true,
  "ExtendTop": 0.5,
  "ExtendBottom": 0.5,
  "ExtendLeft": 0.5,
  "ExtendRight": 0.5,
  "StartDistance": 0,
  "EndDistance": 2.5
}
```

| Property | Type | Description |
|----------|------|-------------|
| `ExtendLeft` | float | Hitbox extension to the left |
| `ExtendRight` | float | Hitbox extension to the right |

### HitEntityRules

For conditional hit handling based on entity matchers:

```json
{
  "HitEntityRules": [{
    "Matchers": [{
      "Type": "Vulnerable"
    }],
    "Next": {
      "Interactions": [
        { "Type": "ApplyEffect", "EffectId": "Stoneskin" }
      ]
    }
  }]
}
```

### Examples

**Sword Swing (Horizontal sweep):**

```json
{
  "Type": "Selector",
  "RunTime": 0.055,
  "Selector": {
    "Id": "Horizontal",
    "Direction": "ToRight",
    "TestLineOfSight": true,
    "ExtendTop": 0.5,
    "ExtendBottom": 0.5,
    "StartDistance": 0.1,
    "EndDistance": 2.5,
    "Length": 30,
    "RollOffset": 45,
    "YawStartOffset": -15
  },
  "HitEntity": {
    "Interactions": ["Sword_Swing_Damage"]
  }
}
```

**Ground Stomp (AOE Circle):**

```json
{
  "Type": "Selector",
  "RunTime": 0.333,
  "Selector": {
    "Id": "AOECircle",
    "Range": 4
  },
  "HitEntity": {
    "Interactions": ["Stomp_Damage"]
  }
}
```

**Wand Spell (Raycast):**

```json
{
  "Type": "Selector",
  "Selector": {
    "Id": "Raycast",
    "Offset": { "Y": 1.6 }
  },
  "HitEntityRules": [{
    "Matchers": [{ "Type": "Vulnerable" }],
    "Next": {
      "Interactions": [
        { "Type": "ApplyEffect", "EffectId": "Root" }
      ]
    }
  }]
}
```

---

## DamageEntity

**Package:** `config/server/DamageEntityInteraction`

The core interaction for dealing damage to entities. Damage amount comes from a `DamageCalculator` (not a flat amount field), and hit feedback / knockback live under `DamageEffects`.

Most weapon attacks reference a shared `DamageEntityParent` via `"Parent"` instead of writing `"Type": "DamageEntity"` directly. The parent supplies common behaviour (clearing regen effects on hit, etc.) and the child adds its `DamageCalculator` and `DamageEffects`.

### Basic Structure

```json
{
  "Type": "DamageEntity",
  "DamageCalculator": {
    "BaseDamage": {
      "Physical": 5
    }
  },
  "DamageEffects": {}
}
```

### Full Structure with All Options

```json
{
  "Parent": "DamageEntityParent",
  "DamageCalculator": {
    "BaseDamage": {
      "Physical": 10
    }
  },
  "DamageEffects": {
    "Knockback": {
      "Type": "Force",
      "VelocityConfig": {
        "AirResistance": 0.97,
        "AirResistanceMax": 0.96,
        "GroundResistance": 0.94,
        "GroundResistanceMax": 0.3,
        "Threshold": 3.0,
        "Style": "Exp"
      },
      "Direction": { "X": 0.0, "Y": -2.0, "Z": -2.5 },
      "Force": 8.0,
      "VelocityType": "Set"
    },
    "StaminaDrainMultiplier": 2.5,
    "WorldSoundEventId": "SFX_Club_Steel_Impact",
    "LocalSoundEventId": "SFX_Club_Steel_Impact",
    "WorldParticles": [
      { "SystemId": "Impact_Sword_Basic_Stronk" }
    ]
  },
  "EntityStatsOnHit": [
    { "EntityStatId": "SignatureEnergy", "Amount": 0 }
  ]
}
```

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `DamageCalculator` | object | Damage source (see below). Holds `BaseDamage` per damage class |
| `DamageEffects` | object | Hit feedback: knockback, sounds, particles (see below) |
| `EntityStatsOnHit` | array | Stats granted to the attacker on a successful hit |
| `Parent` | string | Optional. Inherits another interaction (e.g. `DamageEntityParent`) |

### DamageCalculator Properties

| Property | Type | Description |
|----------|------|-------------|
| `BaseDamage` | object | Map of damage class to amount, e.g. `{ "Physical": 10 }` (other classes such as `Fire` also appear) |

### DamageEffects Properties

| Property | Type | Description |
|----------|------|-------------|
| `Knockback` | object | Knockback configuration (see below) |
| `WorldParticles` | array | Particles spawned at the hit location, each an object with `SystemId` and `Scale` (see note) |
| `LocalSoundEventId` | string | Sound played for the attacker only |
| `WorldSoundEventId` | string | Sound played at hit location for all nearby |
| `StaminaDrainMultiplier` | float | Multiplier for stamina drain on hit |

> ⚠️ **Always set `Scale` on particles.** Both `WorldParticle.scale` and `ModelParticle.scale` are
> primitive `float`s — omit `"Scale"` and the value is `0.0`, which renders the particle
> **invisibly**. Every explicit vanilla usage sets it (`"Scale": 1` or more); a config that omits it
> is relying on a zero scale. This applies to the `Particles` array on the generic `Effects` block too.

### Knockback Properties

Two `Type` forms appear in real assets — a simple relative form and a `Force`/`Point` directional form:

```json
"Knockback": {
  "Force": 1,
  "RelativeX": 5,
  "RelativeZ": -5,
  "VelocityY": 5
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Type` | string | `"Force"` or `"Point"` for directional knockback (omitted for the relative form) |
| `Force` | float | Strength of the knockback impulse |
| `Direction` | object | `{ "X", "Y", "Z" }` push direction (with `Type: Force`/`Point`) |
| `RelativeX` / `RelativeZ` / `VelocityY` | float | Relative push offsets and upward velocity (simple form) |
| `VelocityType` | string | e.g. `"Set"` |
| `VelocityConfig` | object | Air/ground resistance and `Style` tuning |

### EntityStatsOnHit

A top-level array (sibling of `DamageEffects`) that grants stats to the attacker on a successful hit. Each entry has `EntityStatId` and `Amount`:

```json
"EntityStatsOnHit": [
  { "EntityStatId": "SignatureEnergy", "Amount": 0 }
]
```

---

## ApplyForce

**Package:** `config/client/ApplyForceInteraction`

Applies physics force to entities, used for launches, dashes, and movement effects. The force is a `Direction` vector scaled by a `Force` magnitude.

### Structure

```json
{
  "Type": "ApplyForce",
  "Direction": { "X": 0, "Y": 2, "Z": 0 },
  "AdjustVertical": false,
  "WaitForGround": false,
  "Force": 15
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Direction` | object | Force direction as `{ "X", "Y", "Z" }` |
| `Force` | float | Magnitude applied along `Direction` |
| `AdjustVertical` | boolean | Adjust the vertical component of the force |
| `WaitForGround` | boolean | Wait until the entity is grounded before applying |
| `Duration` | float | Duration for sustained forces (optional) |

### Example: Double Jump

A vertical launch used by the double-jump interaction:

```json
{
  "Type": "ApplyForce",
  "Direction": { "X": 0, "Y": 2, "Z": 0 },
  "AdjustVertical": false,
  "WaitForGround": false,
  "Force": 15
}
```

---

## ApplyEffect

**Package:** `config/none/ApplyEffectInteraction`

Applies status effects to entities (buffs, debuffs, damage over time, etc.).

> **See also:** [Effects Reference](effects-stats.md#effects-status-effects) for the complete effect asset JSON structure including stat modifiers, application effects, and damage resistance.

### Structure

```json
{
  "Type": "ApplyEffect",
  "EffectId": "Stun",
  "Entity": "Target"
}
```

The effect's duration, magnitude, and particles are defined in the effect asset itself (referenced by `EffectId`), not on the interaction.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `EffectId` | string | ID of the effect to apply (e.g. `Stun`, `Root`, `Red_Flash`) |
| `Entity` | string | Who receives the effect — `Target`, `Self`, `User`, or `Owner` (defaults to the executing entity when omitted) |

### Example: Apply Root on a Wand Hit

After a raycast selector hits a vulnerable entity, grant brief immunity then apply the Root effect:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "ChangeStat",
      "Entity": "Target",
      "StatModifiers": { "Immunity": 25 }
    },
    {
      "Type": "ApplyEffect",
      "EffectId": "Root",
      "Entity": "Target"
    }
  ]
}
```

---

## ClearEntityEffect

**Package:** `config/server/ClearEntityEffectInteraction`

Removes status effects from entities. Effects are identified by their entity-effect id (`EntityEffectId` for one, or `EntityEffectIds` for several).

### Structure

```json
{
  "Type": "ClearEntityEffect",
  "Entity": "Target",
  "EntityEffectId": "Potion_Health_Regen"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Entity` | string | Whose effect to remove — typically `Target` |
| `EntityEffectId` | string | Single effect id to remove |
| `EntityEffectIds` | array | List of effect ids to remove |

### Example: Strip Regen Effects on Hit

`DamageEntityParent` chains a series of `ClearEntityEffect` interactions so a damaging hit cancels the target's active regen buffs:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "ClearEntityEffect",
      "Entity": "Target",
      "EntityEffectId": "Potion_Health_Regen"
    },
    {
      "Type": "ClearEntityEffect",
      "Entity": "Target",
      "EntityEffectId": "Potion_Stamina_Regen"
    }
  ]
}
```

---

## ChangeStat

Modifies entity stats like health, stamina, or signature energy.

> **See also:** [Stat Definitions](effects-stats.md#stat-definitions) for the complete stat asset JSON structure including regeneration rules, conditions, and min/max value effects.

**Example locations:**
- `Server/Entity/Effects/Potion/*_Regen.json`
- Used in `BlockedInteractions` for granting stats on block

### Basic Structure

```json
{
  "Type": "ChangeStat",
  "StatModifiers": {
    "SignatureEnergy": 5,
    "Stamina": 10
  }
}
```

### StatModifiers

A map of stat names to modification values:

```json
"StatModifiers": {
  "SignatureEnergy": 5,
  "Stamina": 10,
  "Health": -5
}
```

**Available stats:**
- `SignatureEnergy` - Ultimate/signature ability resource
- `Stamina` - Used for blocking, sprinting, etc.
- `Health` - Entity health
- `Mana` - Magic resource (if applicable)

### Behaviour Options

Control how the stat is modified:

```json
{
  "Type": "ChangeStat",
  "StatModifiers": {
    "Health": 50
  },
  "Behaviour": "Set"
}
```

| Behaviour | Description |
|-----------|-------------|
| `Add` | Add value to current stat (default) |
| `Set` | Set stat to exact value |

### ValueType Options

Control whether the value is absolute or percentage-based:

```json
{
  "Type": "ChangeStat",
  "StatModifiers": {
    "Health": 25
  },
  "ValueType": "Percent"
}
```

| ValueType | Description |
|-----------|-------------|
| (default) | Absolute value |
| `Percent` | Percentage of max stat |

### Example: Grant Signature Energy on Block

Combine `Wielding` with `BlockedInteractions` and `ChangeStat`:

```json
{
  "Type": "Wielding",
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "ChangeStat",
        "StatModifiers": {
          "SignatureEnergy": 5
        }
      }
    ]
  },
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 90,
    "DamageModifiers": { "Physical": 0 }
  },
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Shield_T2_Impact"
  }
}
```

This grants 5 signature energy each time the player successfully blocks an attack.

---

## InterruptInteraction

**Package:** `config/server/InterruptInteraction`

Cancels the current interaction chain on the target entity. Used for stagger effects, crowd control, or cancelling enemy attacks mid-animation. Typically paired with [ApplyEffect](#applyeffect) (Stun) for full crowd control mechanics.

### Core Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `Type` | string | Yes | Always `"Interrupt"` |
| `Entity` | string | Yes | Target entity selector (typically `"Target"`) |
| `ExcludedTag` | string | No | Tag that makes entities immune to interruption |

### How Interruption Works

When an InterruptInteraction executes:

1. The interaction resolves the target entity using the `Entity` selector
2. If `ExcludedTag` is specified, entities with that tag are skipped
3. The target's `InteractionManager` component receives the interrupt signal
4. All active interaction chains on the target are immediately cancelled

This stops any ongoing:
- Attack animations mid-swing
- Charging abilities (bow draws, spell charges)
- Combo sequences
- Channel effects

**Important:** Interrupt only cancels ongoing interactions—it does not prevent the target from starting new ones. For persistent crowd control, combine with status effects like Stun.

### Entity Values

| Value | Description |
|-------|-------------|
| `"Target"` | The entity being hit (most common for combat) |
| `"Self"` | The entity performing the interaction |
| `"Owner"` | The entity that owns the current item/projectile |

### ExcludedTag System

The `ExcludedTag` property allows certain entities to be immune to interruption:

```json
{
  "Type": "Interrupt",
  "Entity": "Target",
  "ExcludedTag": "Uninterruptable"
}
```

Common immunity tags:
- `"Uninterruptable"` - Boss enemies or armored states
- Custom tags for specific enemy types or phases

Entities with the specified tag will not have their interactions cancelled, even when hit by the interrupt.

### Complete Examples

#### Basic Interrupt

Minimal interrupt that cancels the target's current action:

```json
{
  "Type": "Interrupt",
  "Entity": "Target"
}
```

#### Stun Bomb with Immunity Check

From an area-effect stun bomb that grants immunity to prevent chain-stunning:

```json
{
  "Type": "Selector",
  "Selector": {
    "Id": "AOECircle",
    "Range": 3
  },
  "HitEntity": {
    "Interactions": [
      {
        "Type": "EffectCondition",
        "Entity": "Target",
        "EntityEffectIds": ["Immune"],
        "Match": "None",
        "Next": {
          "Type": "Serial",
          "Interactions": [
            {
              "Type": "ChangeStat",
              "Entity": "Target",
              "StatModifiers": { "Immunity": 25 }
            },
            {
              "Type": "Interrupt",
              "Entity": "Target",
              "ExcludedTag": "Uninterruptable"
            },
            {
              "Type": "ApplyEffect",
              "EffectId": "Stun",
              "Entity": "Target"
            },
            {
              "Parent": "DamageEntityParent",
              "DamageCalculator": {
                "BaseDamage": { "Physical": 15 }
              },
              "DamageEffects": {
                "Knockback": {
                  "Type": "Point",
                  "Force": 15,
                  "VelocityType": "Set"
                }
              }
            }
          ]
        }
      }
    ]
  }
}
```

This pattern (from `Bomb_Explode_Stun`):
1. Selects entities in a 3-block-radius `AOECircle`
2. Uses `EffectCondition` with `Match: "None"` to skip targets that already have `Immune`
3. Grants Immunity via `ChangeStat`
4. Interrupts their current action (unless tagged `Uninterruptable`)
5. Applies the `Stun` effect
6. Deals damage with knockback through `DamageEntityParent`

#### Melee Stun Attack

A weapon hit that interrupts and stuns on contact:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "DamageEntity",
      "DamageCalculator": {
        "BaseDamage": { "Physical": 15 }
      },
      "DamageEffects": {}
    },
    {
      "Type": "Interrupt",
      "Entity": "Target"
    },
    {
      "Type": "ApplyEffect",
      "EffectId": "Stun",
      "Entity": "Target"
    }
  ]
}
```

### Common Patterns

| Pattern | Use Case | Structure |
|---------|----------|-----------|
| Interrupt only | Cancel attacks without disabling movement | `Interrupt` alone |
| Interrupt + Stun | Full crowd control (cancel + disable) | `Interrupt` → `ApplyEffect(Stun)` |
| Conditional Interrupt | Respect boss immunity phases | `EffectCondition` → `Interrupt` |
| AOE Interrupt | Crowd control multiple enemies | `Selector(AOE)` → `Interrupt` |

### Interrupt vs Stun

| Mechanic | Effect | Target Can Move | Target Can Start New Actions |
|----------|--------|-----------------|------------------------------|
| **Interrupt** | Cancels current action | Yes | Yes (immediately) |
| **Stun** | Disables controls | No | No (until expires) |
| **Both** | Full crowd control | No | No |

Use Interrupt alone for light staggers (enemy can recover quickly). Use both for meaningful crowd control windows.

### Technical Notes

- Interrupt is processed server-side and takes effect immediately
- The `InteractionManager` component on entities tracks active interaction chains
- Interrupted chains call their cleanup/cancellation logic (animations stop cleanly)
- Interrupt has no visual feedback by itself—pair with effects or animations for player feedback

### Related Interactions

- [ApplyEffect](#applyeffect) - Apply status effects like Stun
- [ChainingInteraction](interactions-combo.md#chaininginteraction) - Create interruptible combo chains
- [DamageEntity](#damageentity) - Deal damage alongside interrupt
- [Selector](#selector) - Target multiple entities for AOE interrupts

---

## Gotchas & Errors

- **Symptom:** a `DamageEntity` with a flat `Damage` (or `Amount`) number deals no damage → there is no flat-amount field; the amount comes from `DamageCalculator`. Fix: put the value under `DamageCalculator.BaseDamage` (e.g. `{ "Physical": 5 }`), and place knockback/sounds under `DamageEffects` (see [DamageEntity](#damageentity)).
- **Symptom:** a single `Selector` sweep only damages each entity (or block) once even though the hitbox overlaps it on several frames → by design, a single selector cannot hit the same entity or block more than once. Fix: use a separate `Selector` (or re-trigger the interaction) for a second hit; don't rely on the same sweep hitting twice.
- **Symptom:** a `HitEntity` interaction never fires even when the swing looks like a hit → the selector's `TestLineOfSight` blocked the target, or `IgnoreOwner` excluded the attacker. Fix: verify line-of-sight is clear and the intended target is not the owner; loosen `TestLineOfSight` for through-wall attacks.
