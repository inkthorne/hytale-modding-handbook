---
title: "Combat & Effects Interactions"
description: "Hytale combat interactions in JSON — the Simple interaction for delays/animations/sounds/particles, Selector for melee/AOE/raycast targeting, and damage and effect application."
seo:
  type: TechArticle
---

# Combat & Effects Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.6.3**

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
│   └── Selector (Horizontal / Stab / AOECircle / AOECylinder / Raycast / Donut) → HitEntity / HitBlock
├── Damage
│   ├── DamageEntity (DamageCalculator + DamageEffects + EntityStatsOnHit)
│   └── ApplyForce (Direction + Force knockback/launch)
├── Status effects
│   ├── ApplyEffect (EffectId → effect asset)
│   └── ClearEntityEffect (EntityEffectId — one per interaction)
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
| `ApplyEffect` (`ApplyEffectInteraction`) | `config/none/simple/ApplyEffectInteraction` | Applies a status effect by `EffectId` |
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
| `HorizontalSpeedMultiplier` | float | `1.0` | Multiplier applied to the entity's horizontal speed while the interaction runs. The codec imposes no bound; every shipped value is between `0` and `1` |
| `ViewDistance` | double | `96.0` | Distance within which other players can see this interaction's effects |
| `OnItemChangeBehavior` | string | `Cancel` | What happens when the held item changes: `Cancel`, `Fail`, `Finish`, or `Ignore` (`InteractionItemChangeBehavior`, 0.6.3+). The old boolean `CancelOnItemChange` is still accepted as an alias — `true` → `Cancel`, `false` → `Ignore` — but no shipped asset uses it any more |
| `Settings` | Map<GameMode, InteractionSettings> | - | Per-gamemode settings |
| `Rules` | InteractionRules | - | Interaction rules |
| `Camera` | InteractionCameraSettings | - | Camera keyframes (`FirstPerson`/`ThirdPerson`) played during the interaction — see [Camera Control](camera.md#the-camera-property-keyframe-arrays). Distinct from the [`Camera` interaction type](camera.md#the-camera-interaction-json). |

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
| `CameraEffect` | string | Camera effect id (shake, zoom, etc.) — references a `Server/Camera/CameraEffect/**` asset; see [Camera Control → Adjacent systems](camera.md#adjacent-camera-systems) |
| `MovementEffects` | object | Movement modification effects |
| `HideFirstPersonHeldItem` | boolean | Hide the held item from the local player's own first-person view while the interaction is active; other players still see it. Default `false` (0.6.3+) |
| `Zoom` | object | `ZoomConfig` driving the client zoom while this step is active — `MagnificationMultiplier`, `MouseSensitivityMultiplier`, `DepthOfField`, `OverlayTexture`, `OverlayFade*`, `InLerp`/`OutLerp`/`TransitionLerp`, `ForcePerspective`, `AllowCameraOrbit`, `LodMultiplier` (0.6.3+) |
| `PersistZoom` | boolean | Keep the `Zoom` applied for the rest of the chain instead of clearing it when this step ends (0.6.3+) |
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

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `RunTime` | float | `0` | Duration of the selection window in seconds. The selector runs **every tick** and may sweep its search area across that window (e.g. tracing a sword arc) |
| `Selector` | object | - | Hitbox configuration; `Id` picks the shape (see Selector Types below) |
| `HitEntity` | string/object | - | **Root interaction** forked once per hit entity (hence the `{ "Interactions": [...] }` shape, not a bare interaction) |
| `HitBlock` | string/object | - | **Root interaction** forked once per hit block |
| `HitEntityRules` | array | - | Conditional hit handling with matchers; **overrides `HitEntity`** for any entity that matches |
| `IgnoreOwner` | boolean | `true` | Ignore the owner of the affiliated entity (e.g. the thrower of a projectile) |
| `MaxTargets` | int | `0` | Cap on how many of the selected entities actually get a fork; `0` = unlimited. When more are hit, the survivors are picked by reservoir sampling (i.e. randomly) |
| `FailOn` | string | `Neither` | What makes the selector take its `Failed` branch: `Neither`, `Entity` (nothing hit an entity), `Block`, or `Either` |

> **`HitEntity`/`HitBlock` are root-interaction references, not interactions.** They accept a
> `RootInteractions/` asset id *or* an inline root interaction, which is why real assets write
> `"HitEntity": { "Interactions": ["Weapon_Damage"] }` rather than `"HitEntity": { "Type": "DamageEntity" }`.

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
| `TestLineOfSight` | boolean | Check for obstacles between attacker and target (default `true` on `Horizontal`, `false` on `Stab`) |
| `ExtendTop` | float | Hitbox extension upward (default `1.0`) |
| `ExtendBottom` | float | Hitbox extension downward (default `1.0`) |
| `StartDistance` | float | Starting distance from attacker (default `0.01`) |
| `EndDistance` | float | Maximum reach distance |
| `Length` | float | Arc length in degrees |
| `RollOffset` | float | Rotation offset around forward axis |
| `YawStartOffset` | float | Starting yaw offset in degrees |
| `PitchOffset` | float | Pitch rotation offset in degrees |
| `Anchor` | string | Where the selector anchors vertically: `Eyes` (default) follows the model's eye height, `Feet` anchors at ground level (0.6.3+) |
| `IgnorePitch` | boolean | Ignore the entity's look pitch so the selector stays level with the ground (0.6.3+) |
| `IgnoreYaw` | boolean | Ignore the entity's look yaw, keeping the selector in a fixed world direction — use `YawStartOffset` to orient it (0.6.3+) |

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
| `Range` | float | Radius of the sphere. Validated with an inclusive max of `30`; a larger value fails validation with `Must be less than or equal to 30.0` |
| `Offset` | object | `{ "X", "Y", "Z" }` offset of the sphere center from the entity position. **Rotated by the attacker's head yaw** before being added, so it is relative to facing, not to world axes. A zero offset centres the sphere on the entity's *feet* (its `TransformComponent` position), not its eyes |

> ⚠️ **`AOECircle` is a sphere, not a disc.** Despite the name, `AOECircleSelector` runs
> `Selector.selectNearbyEntities(...)`, a 3-D radius query over the entity spatial index
> (`KDTree.collect` compares squared 3-D distance), and its debug draw is `DebugUtils.addSphere`.
> There is no height field and none is needed: a `Range` of 4 reaches 4 blocks in every direction,
> including straight up and straight down from the (feet-level) origin.
>
> **`AOECylinder`** (`AOECylinderSelector extends AOECircleSelector`) is the one that constrains
> vertical reach: it adds `Height` and selects only entities whose vertical offset from the origin is
> in `[0, Height]` — so it reaches *upward only*, and misses anything below the origin plane. Use it
> when a ground slam should not hit a target hovering below a ledge. No shipped asset uses it
> (`Server/` uses `Horizontal` ×369, `Stab` ×76, `AOECircle` ×17, `Raycast` ×3 and one debug `Donut`),
> so it is untested in content despite having a registered codec.
>
> **`Donut` (0.6.3+)** is a ring selector whose radius grows from `MinRadius` to `MaxRadius` over the
> interaction's `RunTime`, with a constant radial `Width` and vertical `Height` (extending up from the
> selector position), an `AngleDeg` (360 = full ring; less = an arc centred on the attacker's look
> direction when the selector starts), `YawOffsetDeg`, and an `Offset`. The only shipped use is
> `Server/Item/Items/_Debug/Debug_Donut_Selector.json` (`MinRadius 0.5`, `MaxRadius 6`, `Width 1`,
> `Height 2`, `AngleDeg 120`, `RunTime 0.6`) — an expanding shockwave.
>
> ⚠️ **A selector in a *projectile's* `ProjectileHit`/`ProjectileMiss` does NOT sweep a radius** — it
> resolves only the entity the projectile directly collides with (unlike a melee swing, which sweeps).
> To do real AOE from a projectile impact, use `Type: "Explode"`, a [trigger volume](trigger-volumes.md),
> or a Java radius query (`Selector.selectNearbyEntities(accessor, pos, radius, consumer, predicate)` —
> the static query `ExplosionUtils.performExplosion` uses internally).
>
> ⚠️ **`Explode` (`ExplosionConfig`) cannot apply a status effect.** It does radius **damage +
> knockback + model particles + sound** (`DamageEntities`, `EntityDamageRadius`, `EntityDamage`,
> `EntityDamageFalloff`, `Knockback`, `Particles`, `SoundEventId`, plus `DamageBlocks`,
> `BlockDamageRadius`, `BlockDamageFalloff`, `BlockDropChance`, `ItemTool`) — but has **no field for an
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
| `Distance` | int | Maximum search distance for the ray (default `30`; the codec is `Codec.INTEGER`, so a fractional value is rejected) |
| `BlockTag` | string | Tag a block must carry for the ray to count it as a hit |
| `IgnoreFluids` / `IgnoreEmptyCollisionMaterial` | boolean | Skip fluids / blocks with no collision material (both default `false`) |

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

`Stab` shares `TestLineOfSight`, `ExtendTop`/`ExtendBottom`, `StartDistance`/`EndDistance`, `RollOffset`, `PitchOffset` and a `YawOffset` with `Horizontal`, and gained the same `Anchor` / `IgnorePitch` / `IgnoreYaw` keys in 0.6.3.

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

Each rule entry has:

| Property | Type | Description |
|----------|------|-------------|
| `Matchers` | array | Entity matchers that must **all** pass for the rule to apply. Each carries an `Invert` flag that flips its result |
| `Next` | string/object | The **root interaction** to fork for a matching entity (same shape as `HitEntity`) |

> **Rules override `HitEntity`, and the *last* matching rule wins.** The engine walks
> `HitEntityRules` in order and assigns `hitEntity = rule.next` on every match without breaking, so a
> later rule silently replaces an earlier one. Order the array most-general first, most-specific last.

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
| `DamageCalculator` | object | Damage source (see below). Holds `BaseDamage` per damage type |
| `DamageEffects` | object | Hit feedback: knockback, sounds, particles (see below) |
| `EntityStatsOnHit` | array | Stats granted to the attacker on a successful hit |
| `AngledDamage` | array | Per-angle overrides: each entry takes `Angle`, `AngleDistance` and its own `DamageCalculator` / `DamageEffects` / `TargetEntityEffects` / `Next`, so a hit from behind can differ from a hit to the face |
| `TargetedDamage` | object | Map of hit-detail key (the body part / sub-hitbox the selector reported) to the same per-hit override shape as `AngledDamage` |
| `Next` | string/object | Interaction to run when the damage lands |
| `Failed` | string/object | Interaction to run when the interaction fails |
| `Blocked` | string/object | Interaction to run when the target blocked the hit |
| `Parent` | string | Optional. Inherits another interaction (e.g. `DamageEntityParent`) |

### DamageCalculator Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `BaseDamage` | object | - | Map of **damage-cause asset id** to amount, e.g. `{ "Physical": 10 }`. Keys are validated against `Server/Entity/Damage/*.json` (`Physical`, `Fire`, `Ice`, `Poison`, `Fall`, `Projectile`, …), so a typo fails asset load |
| `Type` | string | `Absolute` | `Absolute` — the numbers *are* the damage; `Dps` — they are damage *per second* and get multiplied by how long the damage has been applying |
| `Class` | string | `Unknown` | `Unknown`, `Light`, `Charged` or `Signature` — the damage system uses it to pick which of the source's equipment modifiers apply |
| `RandomPercentageModifier` | float | `0` | Randomises the result within ±this fraction. Vanilla melee overwhelmingly uses `0.1`, with `0.15` / `0.2` on heavier weapons |
| `SequentialModifierStep` | float | `0` | Falloff for repeated hits in one damage sequence: the amount is multiplied by `max(1 − Step × priorHits, SequentialModifierMinimum)` |
| `SequentialModifierMinimum` | float | `0` | Floor for that multiplier (`0` means a long enough sequence can reach zero damage) |

### DamageEffects Properties

These nine keys are the whole of `DamageEffects` — there is nothing else the codec accepts:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Knockback` | object | - | Knockback configuration (see below) |
| `WorldParticles` | array | - | World-space particles spawned at the hit location. Each entry is a `WorldParticle`: `SystemId`, `Color`, `Scale`, `PositionOffset`, `RotationOffset` (see note) |
| `LocalSoundEventId` | string | - | Sound played for the attacker only |
| `WorldSoundEventId` | string | - | Sound played at hit location for all nearby |
| `PlayerSoundEventId` | string | - | Sound played to a *player* receiving the damage |
| `StaminaDrainMultiplier` | float | `1.0` | Multiplier for stamina drain on hit |
| `ModelParticles` | array | - | Bone-attached `ModelParticle`s on the victim (`SystemId`, `TargetEntityPart`, `TargetNodeName`, `Color`, `Scale`, `PositionOffset`, `RotationOffset`, `DetachedFromModel`, `ClearParticlesOnRemove`) |
| `CameraEffect` | string | - | Camera effect asset played for the victim on hit (e.g. `"Impact_Light"` in `Common_Melee_Damage`) |
| `ViewDistance` | double | `75.0` | View distance within which these hit effects are sent |

> **`Scale` defaults to `1.0`.** As of 0.6.3 both `WorldParticle.scale` and `ModelParticle.scale`
> initialise to `1.0f`, so omitting `"Scale"` is safe (vanilla omits it widely — e.g. the
> `Impact_Blade_01` particle in `Weapon_Damage.json`). Explicit values other than `1` still matter
> (`"Scale": 1` appears where an asset wants to be explicit). `ModelParticle`s (the `Particles` array on
> the generic `Effects` block, and `ModelParticles` here) also accept `ClearParticlesOnRemove`
> (0.6.3+): when the owning entity is removed, clear this effect's already-emitted particles instantly
> instead of letting them finish their lifespan.

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

Shared by every knockback type:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | `Directional` | `Directional`, `Force` or `Point` — see [Knockback Types](combat.md#knockback-types). It is the first registered type, so omitting `Type` gives you `Directional` |
| `Force` | float | `0` | Strength of the knockback impulse |
| `Duration` | float | `0` | Seconds to keep applying the force. `0` = applied once. Validated `>= 0` |
| `VelocityType` | string | `Add` | `Add` or `Set` (`ChangeVelocityType`) |
| `VelocityConfig` | object | - | Air/ground resistance and `Style` tuning |

Per-type keys — each type accepts **only** its own, on top of the shared four:

| Type | Keys |
|------|------|
| `Directional` | `RelativeX`, `RelativeZ`, `VelocityY` — a push relative to the attacker's facing |
| `Force` | `Direction` — a `{ "X", "Y", "Z" }` vector (defaults to straight up) |
| `Point` | `OffsetX`, `OffsetZ`, `RotateY`, `VelocityY` — pushes away from an offset point. **It has no `Direction`** |

### EntityStatsOnHit

A top-level array (sibling of `DamageEffects`) that grants stats to the attacker on a successful hit. Each entry has `EntityStatId` and `Amount`, plus optional `MultipliersPerEntitiesHit` (default `[1.0, 0.6, 0.4, 0.2, 0.1]`, scaling `Amount` by how many entities the swing has already hit) and `MultiplierPerExtraEntityHit` (default `0.05`) — see [Stat Modification on Hit](combat.md#stat-modification-on-hit-json):

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

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Direction` | object | `{0, 1, 0}` | Force direction as `{ "X", "Y", "Z" }`, rotated by the entity's yaw |
| `Force` | float | `1.0` | Magnitude applied along `Direction` |
| `AdjustVertical` | boolean | `false` | Also rotate the direction by the entity's look pitch |
| `Forces` | array | - | A list of `{ "Direction", "AdjustVertical", "Force" }` entries applied together. **Replaces** `Direction`/`AdjustVertical`/`Force` when present (used by `Debug_Stick_Parry`) |
| `Duration` | float | `0` | Seconds to keep re-applying the force each tick. `0` = applied on first run only |
| `VerticalClamp` | array | - | **Two-element array** `[minDeg, maxDeg]` clamping the look pitch used by `AdjustVertical` — e.g. `"VerticalClamp": [-85, 20]` in `Weapon_Sword_Primary_Thrust_Force`. An object form is rejected |
| `ChangeVelocityType` | string | `Set` | `Set` or `Add`. Only the first force in `Forces` uses it; the rest are always `Add` |
| `VelocityConfig` | object | - | Air/ground resistance tuning, as on knockback |
| `WaitForGround` | boolean | `true` | **After** applying the force, keep the interaction running until the entity is on the ground, in fluid, or climbing. Not a precondition |
| `GroundCheckDelay` | float | `0.1` | Seconds before the ground check starts (stops an immediate self-trigger) |
| `GroundNext` | string/object | - | Interaction to run when the ground check fires; falls back to `Next` |
| `WaitForCollision` | boolean | `false` | Same idea for colliding with another entity |
| `CollisionCheckDelay` | float | `0` | Seconds before the collision check starts |
| `CollisionNext` | string/object | - | Interaction to run when the collision check fires; falls back to `Next` |
| `RaycastDistance` | float | `1.5` | Raycast length for the collision check |
| `RaycastHeightOffset` | float | `0` | Raycast height offset for the collision check |
| `RaycastMode` | string | `FollowMotion` | `FollowMotion` or `FollowLook` — what the collision raycast points along |
| `UseTargetBlockForDirection` | boolean | `false` | Align the direction to the interaction chain's target block; `Direction` and `Forces` are then ignored and only the root settings are used (0.6.3+) |

> **`WaitForGround` defaults to `true`, and it gates *completion*, not the force.** The force is applied
> on the first tick either way; with `WaitForGround` the interaction then holds until the entity lands.
> A launch that must finish immediately needs `"WaitForGround": false` **and** `RunTime: 0` — the
> instant-complete path requires no `RunTime`, no `WaitForGround` and no `WaitForCollision`.

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

**Package:** `config/none/simple/ApplyEffectInteraction`

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

These two keys are all `ApplyEffectInteraction` adds to the base interaction:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `EffectId` | string/object | - | The effect to apply. A `ContainedAssetCodec`, so it takes either an `Server/Entity/Effects/**` asset id (e.g. `Stun`, `Root`, `Red_Flash`) **or an inline effect definition** |
| `Entity` | string | `User` | Who receives the effect — `Target`, `User`, or `Owner` (`InteractionTarget`; there is no `Self` — `User` is the entity running the chain) |

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

Removes a status effect from an entity, identified by its entity-effect id.

### Structure

```json
{
  "Type": "ClearEntityEffect",
  "Entity": "Target",
  "EntityEffectId": "Potion_Health_Regen"
}
```

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Entity` | string | `User` | Whose effect to remove — typically `Target` |
| `EntityEffectId` | string | - | The single effect id to remove |

> ⚠️ **`ClearEntityEffect` clears exactly one effect — there is no `EntityEffectIds` array.**
> `ClearEntityEffectInteraction`'s codec has only `EntityEffectId` and `Entity`; a plural key is
> silently dropped as an unused key and nothing is cleared. To strip several effects, chain one
> `ClearEntityEffect` per id inside a `Serial` (which is exactly what `DamageEntityParent` does — see
> below). The plural `EntityEffectIds` belongs to a *different* interaction,
> [`EffectCondition`](interactions-flow.md#effectcondition), which tests for effects rather than removing them.

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

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `StatModifiers` | object | **required** | Map of stat id to value. Validated `nonNull` **and** `nonEmptyMap`, so an empty `{}` fails asset load |
| `Behaviour` | string | `Add` | How the value is applied (see below) |
| `ValueType` | string | `Absolute` | `Absolute` or `Percent` |
| `Entity` | string | `User` | Whose stats change — `User`, `Target` or `Owner` |

(`ChangeStatWithModifier` is the same interaction plus an `InteractionModifierId`, which pulls the
amount from an armour piece's interaction modifier instead of a literal.)

### StatModifiers

A map of stat names to modification values:

```json
"StatModifiers": {
  "SignatureEnergy": 5,
  "Stamina": 10,
  "Health": -5
}
```

**Available stats** — keys are `Server/Entity/Stats/*.json` asset ids, and the full shipped set is:

| Stat | Purpose |
|------|---------|
| `Health` | Entity health |
| `Stamina` | Used for blocking, sprinting, dashes |
| `StaminaRegenDelay` | Delay before stamina starts regenerating (used with `"Behaviour": "Set"`) |
| `SignatureEnergy` | Ultimate/signature ability resource |
| `SignatureCharges` | Banked signature uses |
| `Mana` | Magic resource |
| `MagicCharges` | Banked magic uses |
| `Immunity` | Damage/CC immunity window (see the stun-bomb pattern below) |
| `Oxygen` | Breath underwater |
| `Ammo` | Ranged ammunition |
| `GlidingActive` / `DeployablePreview` | Internal state flags |

An unrecognised key fails asset load, so these are the only names that work unless you ship your own
stat asset.

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
| `Min` | Lower the stat to the value if it is currently higher (0.6.3+) |
| `Max` | Raise the stat to the value if it is currently lower (0.6.3+) |

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
| `Absolute` (default) | Absolute value |
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

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | **required** | Always `"Interrupt"` |
| `Entity` | string | `User` | Target entity selector (`User`, `Target` or `Owner`; combat almost always writes `"Target"`) |
| `RequiredTag` | string | - | Tag the **root interaction** of an active chain must carry to be interrupted; unset = any chain |
| `ExcludedTag` | string | - | Tag that, if the **root interaction** of an active chain carries it, protects that chain from this interrupt |
| `InterruptTypes` | array | - | Restrict the interrupt to chains of these `InteractionType`s (`Primary`, `Secondary`, `Ability1`…`Ability3`, `Use`, `Dodge`, `Wielding`, `ProjectileHit`, …). Unset = every type |

### How Interruption Works

When an InterruptInteraction executes:

1. The interaction resolves the target entity using the `Entity` selector
2. It reads the target's `InteractionManager` component and walks **every active chain** on it
3. Each chain is skipped if its type is not in `InterruptTypes`, if its root interaction lacks
   `RequiredTag`, or if its root interaction carries `ExcludedTag`
4. Every surviving chain is cancelled via `interactionManager.cancelChains(chain)`

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
| `"User"` | The entity running the interaction chain |
| `"Owner"` | The entity that owns the current item/projectile |

(`InteractionTarget` has exactly these three values — there is no `"Self"`.)

### ExcludedTag System

`ExcludedTag` marks an *interaction* as uninterruptible, not an entity:

```json
{
  "Type": "Interrupt",
  "Entity": "Target",
  "ExcludedTag": "Uninterruptable"
}
```

> ⚠️ **The tag is read from the chain's root interaction, not from the entity.** The engine looks up
> `interactionChain.getInitialRootInteraction().getData().getExpandedTagIndexes()` — the `Tags` block
> on the **root interaction asset** that started the chain, e.g.
>
> ```json
> { "Interactions": ["Boss_Slam"], "Tags": { "Attack": ["Uninterruptable"] } }
> ```
>
> Putting `Uninterruptable` on a *mob* does nothing; you must tag the root interaction whose chain
> should survive (a boss's wind-up attack, an armoured stance). `RequiredTag` is the inverse filter on
> the same tag set. A boss whose every attack should survive interrupts therefore needs the tag on
> each of its attack root interactions.
>
> As of 0.6.3 **no shipped root interaction actually declares an `Uninterruptable` tag** — the two
> vanilla assets that write `"ExcludedTag": "Uninterruptable"` (`Bomb_Explode_Stun`,
> `Debug_Stick_Stun`) therefore currently exclude nothing. Treat the name as a convention to follow,
> not as an engine-recognised value; any string works as long as your root interactions declare it.

Because the check is per chain, one entity can have some chains interrupted and others spared in the
same interrupt — e.g. its movement ability cancelled while its tagged super-attack keeps running.

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
- **Symptom:** a `HitEntity` interaction never fires even when the swing looks like a hit → the selector's `TestLineOfSight` blocked the target (default `true` on `Horizontal`), or `IgnoreOwner` (default `true`) excluded the attacker. Fix: verify line-of-sight is clear and the intended target is not the owner; loosen `TestLineOfSight` for through-wall attacks.
- **Symptom:** a `HitEntity` written as `{ "Type": "DamageEntity", ... }` is rejected or ignored → `HitEntity`/`HitBlock` take a **root interaction**, not an interaction. Fix: wrap it, `"HitEntity": { "Interactions": [ { "Type": "DamageEntity", ... } ] }`, or reference a `RootInteractions/` asset id.
- **Symptom:** a `ClearEntityEffect` with `"EntityEffectIds": [...]` removes nothing → that key does not exist on `ClearEntityEffect` and is silently dropped. Fix: one `ClearEntityEffect` per `EntityEffectId` inside a `Serial` (see [ClearEntityEffect](#clearentityeffect)).
- **Symptom:** an `Interrupt` with `ExcludedTag` still cancels the "immune" mob's attacks → the tag is matched against the **root interaction's** `Tags`, not the entity's. Fix: add the tag to each root interaction that should survive (see [ExcludedTag System](#excludedtag-system)).
- **Symptom:** an `ApplyForce` launch never completes and the chain stalls in mid-air → `WaitForGround` defaults to **`true`**, so the interaction holds until the entity lands. Fix: set `"WaitForGround": false` (and leave `RunTime` at `0`) for a fire-and-forget impulse.
