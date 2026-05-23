# Combat & Effects Interactions

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

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
| `OnFinishLocalSoundEventId` | string | Sound played when interaction finishes |
| `ClearAnimationOnFinish` | boolean | Stop animation when interaction ends |
| `ClearSoundEventOnFinish` | boolean | Stop sound when interaction ends |
| `WaitForAnimationToFinish` | boolean | Wait for animation before completing |
| `Particles` | array | Particles attached to model bones |
| `FirstPersonParticles` | array | Particles for first-person view |
| `Trails` | array | Weapon trail effects |
| `CameraEffectId` | string | Camera effect (shake, zoom, etc.) |
| `MovementEffects` | object | Movement modification effects |
| `StartDelay` | float | Delay before effects begin |

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

The core interaction for dealing damage to entities. Supports damage calculation, effects, knockback, and stat modifications.

### Basic Structure

```json
{
  "Type": "DamageEntity",
  "DamageParameters": {
    "DamageAmount": 10,
    "DamageCauseId": "Physical"
  }
}
```

### Full Structure with All Options

```json
{
  "Type": "DamageEntity",
  "DamageParameters": {
    "DamageAmount": 10,
    "DamageCauseId": "Physical",
    "DamageCalculator": {
      "Type": "Standard",
      "BaseDamage": 10,
      "CriticalMultiplier": 1.5,
      "CriticalChance": 0.1
    }
  },
  "EntityStatsOnHit": [
    { "EntityStatId": "SignatureEnergy", "Amount": 1 }
  ],
  "DamageEffects": {
    "ModelParticles": [
      { "SystemId": "Blood_Splatter", "Bone": "Chest" }
    ],
    "WorldParticles": [
      { "SystemId": "Impact_Sparks" }
    ],
    "LocalSoundEventId": "SFX_Hit_Flesh",
    "WorldSoundEventId": "SFX_Impact_Metal",
    "PlayerSoundEventId": "SFX_Player_Hit",
    "CameraEffectId": "Camera_Shake_Light",
    "StaminaDrainMultiplier": 1.0,
    "Knockback": {
      "Force": 0.5,
      "RelativeX": -5,
      "RelativeZ": -5,
      "VelocityY": 5
    }
  },
  "TargetSelector": {
    "Type": "AOECircle",
    "Radius": 3.0
  }
}
```

### DamageParameters Properties

| Property | Type | Description |
|----------|------|-------------|
| `DamageAmount` | float | Base damage value |
| `DamageCauseId` | string | Damage type (Physical, Magical, Fire, etc.) |
| `DamageCalculator` | object | Optional custom damage calculation |

### DamageEffects Properties

| Property | Type | Description |
|----------|------|-------------|
| `ModelParticles` | array | Particles attached to hit entity's model bones |
| `WorldParticles` | array | Particles spawned at hit location in world space |
| `LocalSoundEventId` | string | Sound played for the attacker only |
| `WorldSoundEventId` | string | Sound played at hit location for all nearby |
| `PlayerSoundEventId` | string | Sound played for hit player specifically |
| `CameraEffectId` | string | Camera shake or effect on hit |
| `StaminaDrainMultiplier` | float | Multiplier for stamina drain on hit |
| `Knockback` | object | Knockback configuration (see [Knockback System](combat.md#knockback-system)) |

### EntityStatsOnHit

Grants stats to the attacker on successful hit:

```json
"EntityStatsOnHit": [
  { "EntityStatId": "SignatureEnergy", "Amount": 1 },
  { "EntityStatId": "Stamina", "Amount": 5 }
]
```

---

## ApplyForce

**Package:** `config/client/ApplyForceInteraction`

Applies physics force to entities, used for knockback, launches, and movement effects.

### Structure

```json
{
  "Type": "ApplyForce",
  "Force": [0, 10, -5],
  "ForceType": "Impulse",
  "RelativeToFacing": true
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Force` | [x, y, z] | Force vector to apply |
| `ForceType` | string | `Impulse` (instant) or `Continuous` (over time) |
| `RelativeToFacing` | boolean | If true, force is relative to entity facing direction |
| `Duration` | float | Duration for continuous forces |

### Example: Launch Pad Effect

```json
{
  "Type": "ApplyForce",
  "Force": [0, 25, 0],
  "ForceType": "Impulse",
  "RelativeToFacing": false
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
  "EffectId": "hytale:poison",
  "Duration": 10,
  "Amplifier": 1,
  "Target": "Self"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `EffectId` | string | ID of the effect to apply |
| `Duration` | float | Duration in seconds |
| `Amplifier` | int | Effect strength/level (0 = level 1) |
| `Target` | string | `Self`, `Target`, or `AOE` |
| `ShowParticles` | boolean | Whether to show effect particles |

### Example: Apply Burning Effect on Hit

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "DamageEntity",
      "DamageParameters": {
        "DamageAmount": 5,
        "DamageCauseId": "Fire"
      }
    },
    {
      "Type": "ApplyEffect",
      "EffectId": "hytale:burning",
      "Duration": 5,
      "Amplifier": 0,
      "Target": "Target"
    }
  ]
}
```

---

## ClearEntityEffect

**Package:** `config/server/ClearEntityEffectInteraction`

Removes status effects from entities.

### Structure

```json
{
  "Type": "ClearEntityEffect",
  "EffectId": "hytale:poison",
  "Target": "Self"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `EffectId` | string | Specific effect to remove, or omit for all |
| `Target` | string | `Self` or `Target` |
| `EffectCategory` | string | Remove all effects of a category (optional) |

### Example: Cleanse Potion

```json
{
  "Type": "ClearEntityEffect",
  "EffectCategory": "Debuff",
  "Target": "Self"
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
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Selector",
      "SelectorType": "AOECircle",
      "Radius": 4,
      "IncludeSelf": false,
      "EntityCategory": "Creature",
      "Interaction": {
        "Type": "Condition",
        "ConditionType": "Effect",
        "Effect": "Immune",
        "Invert": true,
        "Next": {
          "Type": "Serial",
          "Interactions": [
            {
              "Type": "ChangeStat",
              "Entity": "Target",
              "StatType": "Effects",
              "StatModifiers": { "Immune": 4.0 }
            },
            {
              "Type": "Interrupt",
              "Entity": "Target",
              "ExcludedTag": "Uninterruptable"
            },
            {
              "Type": "ApplyEffect",
              "Entity": "Target",
              "Effect": "Stun",
              "Duration": 3.0
            },
            {
              "Type": "DamageEntity",
              "Entity": "Target",
              "DamageType": "Physical",
              "Amount": 10,
              "Knockback": 5
            }
          ]
        }
      }
    }
  ]
}
```

This pattern:
1. Selects all creatures in a 4-block radius
2. Checks they don't already have Immunity (prevents chain-stunning)
3. Grants 4 seconds of Immunity
4. Interrupts their current action (unless Uninterruptable)
5. Applies a 3-second Stun effect
6. Deals damage with knockback

#### Melee Stun Attack

A weapon hit that interrupts and stuns on contact:

```json
{
  "Type": "HitEntity",
  "Interactions": [
    {
      "Type": "DamageEntity",
      "Entity": "Target",
      "DamageType": "Physical",
      "Amount": 15
    },
    {
      "Type": "Interrupt",
      "Entity": "Target"
    },
    {
      "Type": "ApplyEffect",
      "Entity": "Target",
      "Effect": "Stun",
      "Duration": 1.5
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
