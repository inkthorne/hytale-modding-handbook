---
title: "Control Flow Interactions"
description: "Control Hytale interaction flow in JSON — Serial and Parallel composition of child interactions and conditional branching on state, stats, effects, blocks, cooldowns, and placement."
seo:
  type: TechArticle
---

# Control Flow Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.5.2**

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

This page covers the control-flow interactions: composing interactions in sequence or parallel, branching on game state, looping, variable substitution, and target selection.

## Overview

Defined as JSON interaction assets (server classes under `com.hypixel.hytale.server.core.modules.interaction.interaction.config`) and provides:
- `Serial` and `Parallel` composition of child interactions
- Conditional branching on game/movement state, stats, effects, blocks, cooldowns, and placement counts
- Cooldown control via `TriggerCooldown` and `ResetCooldown`
- `Repeat` for looping execution
- `Replace` for variable substitution in templated interactions
- Target selectors for AOE, raycast, and stab targeting

## Architecture
```
Control Flow
├── Composition
│   ├── Serial (run children in order)
│   └── Parallel (run children concurrently)
├── Conditions (branch via Next / fallthrough)
│   ├── Condition (game mode + movement state)
│   ├── StatsCondition (entity stat values)
│   ├── EffectCondition (active status effects)
│   ├── BlockCondition (block type/state/tag)
│   ├── CooldownCondition (cooldown completion)
│   ├── MovementCondition (input direction)
│   └── PlacementCountCondition (block placement count)
├── Cooldown control (TriggerCooldown / ResetCooldown)
├── Looping (Repeat)
├── Templating (Replace — Var + DefaultValue)
└── Target Selectors (AOE / raycast / stab)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Serial` (`SerialInteraction`) | `config/none/SerialInteraction` | Runs child interactions sequentially |
| `Parallel` | `interaction config` | Runs child interactions concurrently |
| `Condition` | `interaction config` | Branches on game mode and movement state |
| `StatsCondition` | `interaction config` | Branches on entity stat values |
| `EffectCondition` | `interaction config` | Branches on active status effects |
| `BlockCondition` | `interaction config` | Branches on block type/state/tag |
| `CooldownCondition` | `interaction config` | Branches on cooldown completion |
| `MovementCondition` | `interaction config` | Branches on input direction |
| `PlacementCountCondition` | `interaction config` | Branches on block placement count |
| `Repeat` | `interaction config` | Loops execution of child interactions |
| `Replace` | `interaction config` | Variable substitution (`Var` + `DefaultValue`) |

## Quick Navigation

| Interaction | Description |
|-------------|-------------|
| [Serial](#serial) | Execute interactions sequentially |
| [Parallel](#parallel) | Execute interactions concurrently |
| [Condition](#condition) | Game mode and movement state branching |
| [StatsCondition](#statscondition) | Branch based on entity stat values |
| [EffectCondition](#effectcondition) | Branch based on active status effects |
| [BlockCondition](#blockcondition) | Branch based on block type/state |
| [CooldownCondition](#cooldowncondition) | Branch based on cooldown completion |
| [TriggerCooldown](#triggercooldown) | Start a cooldown timer |
| [ResetCooldown](#resetcooldown) | Reset a cooldown timer |
| [MovementCondition](#movementcondition) | Direction-based input branching |
| [PlacementCountCondition](#placementcountcondition) | Branch based on block placement count |
| [Repeat](#repeat) | Loop execution of interactions |
| [Replace](#replace) | Variable substitution for templates |
| [Target Selectors](#target-selectors) | AOE, raycast, and stab targeting |

---

## Serial

**Package:** `config/none/SerialInteraction`

Executes multiple interactions sequentially, one after another. Each interaction in the sequence must complete before the next one begins. This is the fundamental building block for multi-step abilities, consumables, combo finishers, and any interaction that requires ordered execution of multiple effects.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Serial"` |
| `Interactions` | array | Required | List of interactions to execute in order |

### Interactions Array Format

The `Interactions` property accepts an array where each entry can be:

1. **Inline interaction object** - Full interaction definition
2. **String reference** - Path to another interaction file
3. **Mixed format** - Combination of both

**Inline interaction objects:**

```json
{
  "Type": "Serial",
  "Interactions": [
    { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 5 } } },
    { "Type": "ApplyEffect", "EffectId": "Stamina_Broken" }
  ]
}
```

**String references:**

```json
{
  "Type": "Serial",
  "Interactions": [
    "Sword_Damage_Light",
    "Sword_Sound_Hit",
    "Sword_Particles_Slash"
  ]
}
```

> **References resolve by basename, scoped per namespace — not by path.** `Sword_Damage_Light` matches
> the file of that basename regardless of which subfolder it sits in. `Interactions/` and
> `RootInteractions/` are independent namespaces (the same basename may exist once in each), but within
> a namespace basenames must be unique. A custom interaction therefore just needs a unique basename in
> its namespace; the subfolder is organizational. (`Parent` is also supported on root interactions, not
> just items and plain interactions — e.g. `RootInteractions/.../Lantern_Yellow` → `Lantern_Base`.)

**Mixed format:**

```json
{
  "Type": "Serial",
  "Interactions": [
    "Prepare_Animation",
    { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 10 } } },
    "Cleanup_Effects"
  ]
}
```

### Execution Behavior

Serial interactions execute **synchronously in order**. Each interaction must fully complete before the next one begins. This differs from [Parallel](#parallel) which starts all interactions simultaneously.

**Execution flow:**

```
Serial Start
    │
    ▼
┌─────────────────┐
│ Interaction 1   │──► Wait for completion
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Interaction 2   │──► Wait for completion
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Interaction 3   │──► Wait for completion
└─────────────────┘
    │
    ▼
Serial Complete
```

**Important timing considerations:**

- Interactions with `RunTime` will block until that duration completes
- Instant interactions (like stat changes) complete immediately
- Nested Serial blocks execute their full sequence before continuing
- If any interaction fails, subsequent interactions may still execute (no short-circuit)

### Deep Nesting Patterns

Serial interactions can be nested within other control flow structures for complex multi-step behaviors.

**Serial inside `Next` blocks (Charging):**

```json
{
  "Type": "Charging",
  "FailOnDamage": true,
  "Next": {
    "2.0": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
        { "Type": "ApplyEffect", "EffectId": "Regeneration" }
      ]
    }
  }
}
```

**Serial inside `Next`/`Failed` blocks (StatsCondition):**

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 25 },
  "Next": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 999 } } },
      { "Type": "SendMessage", "Message": "Executed!" }
    ]
  }
}
```

**Serial inside `Failed` blocks (Charging):**

```json
{
  "Type": "Charging",
  "FailOnDamage": true,
  "Failed": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "Simple", "Effects": { "LocalSoundEventId": "action_canceled" } }
    ]
  },
  "Next": { "1.0": "Consume_Complete" }
}
```

**Serial inside Serial (deeply nested):**

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Serial",
      "Interactions": [
        "Prepare_Phase_1",
        "Execute_Phase_1"
      ]
    },
    {
      "Type": "Serial",
      "Interactions": [
        "Prepare_Phase_2",
        "Execute_Phase_2"
      ]
    }
  ]
}
```

### Complete Examples

**Dodge Mechanic:**

A dodge combines movement, animation, effects, and stat changes in sequence:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Simple",
      "RunTime": 0.4,
      "Effects": {
        "ItemAnimationId": "Dodge",
        "LocalSoundEventId": "SFX_Dodge_Whoosh"
      },
      "Next": {
        "Type": "ApplyForce",
        "Direction": { "X": -1, "Y": 0, "Z": 0 },
        "AdjustVertical": false,
        "Force": 8.0
      }
    },
    {
      "Type": "ApplyEffect",
      "EffectId": "Invulnerable"
    },
    {
      "Type": "ChangeStat",
      "StatModifiers": { "Stamina": -15 }
    }
  ]
}
```

**Double Jump (from Double_Jump.json):**

A stamina-gated aerial boost. The real asset uses a `StatsCondition` with a `Costs`
map (which both checks and deducts the cost) and branches with `Next`:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 2.01 },
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": 2, "Z": 0 },
        "AdjustVertical": false,
        "WaitForGround": false,
        "Force": 15
      },
      {
        "Type": "ChangeStat",
        "StatModifiers": { "Stamina": -2 }
      },
      {
        "Type": "Simple",
        "RunTime": 1,
        "Effects": {
          "LocalSoundEventId": "SFX_Chicken_Alerted",
          "WorldSoundEventId": "SFX_Chicken_Alerted"
        }
      }
    ]
  }
}
```

**Consumable with Charge (from Consume_Charge.json):**

A consumable that requires holding, then executes multiple effects:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Charging",
      "FailOnDamage": true,
      "HorizontalSpeedMultiplier": 0.3,
      "DisplayProgress": true,
      "Effects": {
        "ItemAnimationId": "Consume"
      },
      "Next": {
        "0": {
          "Type": "Simple",
          "Effects": { "ClearAnimationOnFinish": true }
        },
        "2.0": {
          "Type": "Serial",
          "Interactions": [
            { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
            { "Type": "ApplyEffect", "EffectId": "Satiated" },
            { "Type": "ChangeStat", "StatModifiers": { "Health": 20 } },
            { "Type": "Simple", "Effects": { "LocalSoundEventId": "SFX_Eat_Finish" } }
          ]
        }
      }
    }
  ]
}
```

**Signature Ability:**

A powerful ability with a signature-energy cost, animation, AOE damage, and cleanup.
The `StatsCondition.Costs` map both checks for and deducts the energy, and an AOE
`Selector` finds entities to damage:

```json
{
  "Type": "StatsCondition",
  "Costs": { "SignatureEnergy": 100 },
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "Simple",
        "RunTime": 1.2,
        "Effects": {
          "ItemAnimationId": "Vortexstrike",
          "WorldSoundEventId": "SFX_Sword_Signature"
        }
      },
      {
        "Type": "Selector",
        "Selector": { "Id": "AOECircle", "Range": 4.0 },
        "HitEntity": {
          "Interactions": [
            {
              "Type": "DamageEntity",
              "DamageCalculator": { "BaseDamage": { "Physical": 35 } }
            }
          ]
        }
      },
      { "Type": "ApplyEffect", "EffectId": "Slow", "Entity": "User" }
    ]
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Not enough energy!"
  }
}
```

**Arrow Volley (deep nesting example):**

A charged ability that fires multiple projectiles in sequence:

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": true,
  "Next": {
    "0": "Bow_Cancel",
    "1.5": {
      "Type": "Serial",
      "Interactions": [
        { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -5 },
        {
          "Type": "Repeat",
          "Repeat": 5,
          "RunTime": 0.1,
          "ForkInteractions": {
            "Interactions": [
              {
                "Type": "Serial",
                "Interactions": [
                  {
                    "Type": "LaunchProjectile",
                    "ProjectileId": "Arrow_FullCharge"
                  },
                  {
                    "Type": "Simple",
                    "Effects": {
                      "WorldSoundEventId": "SFX_Bow_T2_Shoot"
                    }
                  }
                ]
              }
            ]
          }
        },
        {
          "Type": "Simple",
          "RunTime": 0.8,
          "Effects": {
            "ItemAnimationId": "Bow_Recover"
          }
        }
      ]
    }
  }
}
```

### Serial vs Parallel Comparison

| Aspect | Serial | Parallel |
|--------|--------|----------|
| **Execution order** | Sequential (1 → 2 → 3) | Simultaneous (1, 2, 3 all at once) |
| **Timing** | Total time = sum of all interactions | Total time = longest interaction |
| **Dependencies** | Each step can depend on previous | No ordering guarantees |
| **Use case** | Multi-step abilities, state changes | Multiple simultaneous effects |
| **Failure handling** | Subsequent steps still execute | All started regardless of failures |

**When to use Serial:**
- Stat changes that must happen before damage
- Consuming items before applying effects
- Animations that must play in sequence
- Any ordered multi-step process

**When to use Parallel:**
- Applying multiple status effects at once
- Playing multiple sounds/particles simultaneously
- Independent effects that don't need ordering

**Parallel example for reference:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Type": "ApplyEffect", "EffectId": "burning" },
    { "Type": "ApplyEffect", "EffectId": "slow" },
    { "Type": "Simple", "Effects": { "LocalSoundEventId": "fire_ignite" } }
  ]
}
```

All three effects start at the same instant rather than one after another.

### Common Patterns

| Pattern | Description | Example Use |
|---------|-------------|-------------|
| **Sequential actions** | Multiple effects in order | Consume item → apply buff → play sound |
| **Combo finishers** | Multi-hit or multi-effect attacks | Damage → knockback → particle burst |
| **Stat changes before ability** | Resource consumption | Spend stamina → execute attack |
| **Variable injection with Replace** | Template customization | Set variable → execute template |
| **Conditional then actions** | Multiple effects on condition pass | Check health → heal → message → sound |
| **Cleanup sequences** | Restore state after ability | Clear animation → reset cooldown → remove buff |

### Integration with Replace

Serial is commonly used with [Replace](#replace) to create reusable templates:

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Replace",
      "Var": "DamageAmount",
      "DefaultValue": { "Interactions": [] }
    },
    {
      "Type": "Replace",
      "Var": "EffectToApply",
      "DefaultOk": true,
      "DefaultValue": {
        "Interactions": ["No_Effect"]
      }
    }
  ]
}
```

Items or abilities calling this template provide their own `DamageAmount` and `EffectToApply` values.

### Related Interactions

- [Parallel](#parallel) - Execute interactions simultaneously instead of sequentially
- [Condition](#condition) - Conditional branching (often contains Serial in Then/Else)
- [StatsCondition](#statscondition) - Stat-based branching (often contains Serial in Then/Else)
- [Replace](#replace) - Variable substitution for templates
- [Repeat](#repeat) - Execute a Serial block multiple times

---

## Parallel

**Package:** `config/none/ParallelInteraction`

Executes multiple interactions concurrently. Unlike [Serial](#serial) which waits for each interaction to complete before starting the next, Parallel starts all interactions at the same time. This is essential for separating independent concerns like damage logic and visual effects, allowing them to run simultaneously without blocking each other.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Parallel"` |
| `Interactions` | array | Required | List of interactions to execute concurrently |

### Interactions Array Format

The `Interactions` property accepts an array where each entry can be:

1. **Inline interaction object** - Full interaction definition
2. **String reference** - Path to another interaction file
3. **Mixed format** - Combination of both

**Inline interaction objects:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Type": "ApplyEffect", "EffectId": "Burn" },
    { "Type": "ApplyEffect", "EffectId": "Slow" }
  ]
}
```

**String references:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    "Attack_Damage_Branch",
    "Attack_Visual_Branch",
    "Attack_Sound_Branch"
  ]
}
```

**Mixed format:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    "NPC_Attack_Damage",
    { "Type": "Simple", "Effects": { "WorldSoundEventId": "attack_swoosh" } },
    "NPC_Attack_Particles"
  ]
}
```

### Execution Behavior

Parallel interactions use a **fork-based execution model** that provides true concurrency:

1. **First interaction** executes synchronously on the main context
2. **Remaining interactions** fork with duplicated contexts and run asynchronously
3. **Parent completes immediately** after forking - it does not wait for child interactions

**Key timing characteristic:** The total duration equals the duration of the **longest** interaction, not the sum. This is fundamentally different from Serial where total time = sum of all interactions.

**Execution flow:**

```
ParallelInteraction.tick0()
    │
    ├─► Execute interactions[0] on main context (SYNC)
    │
    ├─► Fork interactions[1] with duplicate context (ASYNC)
    │
    ├─► Fork interactions[2] with duplicate context (ASYNC)
    │
    └─► Mark parent as Finished (returns immediately)
        All forked interactions continue independently
```

**Important execution details:**

- The parent Parallel interaction marks itself as `Finished` immediately after forking
- Forked interactions continue running independently of the parent
- There is no built-in mechanism to wait for all forks to complete
- Changes made in one fork do **not** affect other forks (isolated contexts)

### Context Behavior

Understanding context duplication is critical for advanced Parallel usage:

| Interaction | Context | Notes |
|-------------|---------|-------|
| First (`interactions[0]`) | Shared with parent | Changes affect the original context |
| Subsequent (forked) | Duplicated copy | Changes are isolated to that fork |

**Example implications:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Type": "ChangeStat", "StatModifiers": { "Health": -10 } },
    { "Type": "ChangeStat", "StatModifiers": { "Health": -10 } }
  ]
}
```

In this example:
- First interaction modifies health on the main context (applies to entity)
- Second interaction modifies health on a **duplicated** context
- The entity only receives **one** 10-damage hit, not two

For damage that must stack, use Serial instead or design your interactions to work independently.

### Deep Nesting Patterns

Parallel interactions can be nested within other control flow structures.

**Parallel inside Serial (common pattern):**

```json
{
  "Type": "Serial",
  "Interactions": [
    { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
    {
      "Type": "Parallel",
      "Interactions": [
        "Attack_Damage_Logic",
        "Attack_Visual_Effects"
      ]
    },
    { "Type": "Simple", "Effects": { "ClearAnimationOnFinish": true } }
  ]
}
```

This pattern ensures stamina is consumed first, then damage and visuals happen concurrently, then cleanup occurs after.

**Parallel inside `Next`/`Failed` blocks (StatsCondition):**

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 50 },
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 50 } } },
      { "Type": "ApplyEffect", "EffectId": "Bleeding" },
      { "Type": "Simple", "Effects": { "LocalSoundEventId": "critical_hit" } }
    ]
  }
}
```

**Parallel inside `Next` blocks (Charging):**

```json
{
  "Type": "Charging",
  "FailOnDamage": true,
  "Next": {
    "1.5": {
      "Type": "Parallel",
      "Interactions": [
        { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 25 } } },
        {
          "Type": "Simple",
          "Effects": {
            "WorldSoundEventId": "heavy_attack",
            "ItemAnimationId": "Slam"
          }
        }
      ]
    }
  }
}
```

### Complete Examples

**Basic Multiple Effects:**

Apply multiple status effects simultaneously:

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Type": "ApplyEffect", "EffectId": "burning" },
    { "Type": "ApplyEffect", "EffectId": "slow" },
    { "Type": "Simple", "Effects": { "LocalSoundEventId": "fire_ignite" } }
  ]
}
```

All three effects start at the same instant rather than one after another.

**NPC Melee Attack Pattern (Damage + Visuals Separation):**

This pattern separates damage logic from visual effects, a common design in Hytale's NPC attacks:

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Type": "Serial",
      "Interactions": [
        {
          "Type": "Simple",
          "RunTime": 0.3
        },
        {
          "Type": "Selector",
          "Selector": {
            "Id": "Horizontal",
            "EndDistance": 2.5,
            "Length": 90
          },
          "HitEntity": {
            "Interactions": [
              {
                "Type": "DamageEntity",
                "DamageCalculator": { "BaseDamage": { "Physical": 15 } }
              }
            ]
          }
        }
      ]
    },
    {
      "Type": "Serial",
      "Interactions": [
        {
          "Type": "Simple",
          "RunTime": 0.8,
          "Effects": {
            "ItemAnimationId": "Attack_Swing"
          }
        },
        {
          "Type": "Simple",
          "Effects": {
            "WorldSoundEventId": "sword_whoosh"
          }
        }
      ]
    }
  ]
}
```

**Branch 1 (Damage):** Waits 0.3 seconds (wind-up), then applies damage to entities in a horizontal arc.

**Branch 2 (Visuals):** Plays the full 0.8-second animation with a weapon trail, then plays the sound.

This separation allows:
- Independent timing control for damage window vs. animation duration
- Easy modification of one aspect without affecting the other
- Cleaner organization of concerns

**AOE Ground Slam with Effects:**

A powerful ground slam that combines damage with visual feedback:

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Type": "Selector",
      "Selector": {
        "Id": "AOECircle",
        "Range": 4.0
      },
      "HitEntity": {
        "Interactions": [
          {
            "Type": "DamageEntity",
            "DamageCalculator": { "BaseDamage": { "Physical": 30 } }
          },
          { "Type": "ApplyEffect", "EffectId": "Stagger", "Entity": "Target" }
        ]
      }
    },
    {
      "Type": "Simple",
      "Effects": {
        "WorldSoundEventId": "ground_slam",
        "Particles": [ { "SystemId": "Explosion_Medium" } ]
      }
    }
  ]
}
```

All three branches (damage, animation/particles, debuff) execute simultaneously.

**Variable Replacement in Parallel:**

Using [Replace](#replace) within Parallel for customizable attack templates:

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Type": "Replace",
      "Var": "DamageBranch",
      "DefaultOk": true,
      "DefaultValue": {
        "Interactions": ["Default_Damage"]
      }
    },
    {
      "Type": "Replace",
      "Var": "EffectsBranch",
      "DefaultOk": true,
      "DefaultValue": {
        "Interactions": ["Default_Effects"]
      }
    }
  ]
}
```

Items or abilities can provide custom `DamageBranch` and `EffectsBranch` values to inject specific behavior while sharing the parallel execution structure.

**Projectile Impact with Multiple Effects:**

When a projectile hits, apply damage, effects, and visuals simultaneously:

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Type": "DamageEntity",
      "DamageCalculator": { "BaseDamage": { "Physical": 20 } }
    },
    { "Type": "ApplyEffect", "EffectId": "slow" },
    { "Type": "ApplyEffect", "EffectId": "poison" },
    {
      "Type": "Simple",
      "Effects": {
        "Particles": [ { "SystemId": "poison_splash" } ],
        "WorldSoundEventId": "poison_impact"
      }
    }
  ]
}
```

### Error Handling

Parallel execution has specific error handling behavior:

| Scenario | Behavior |
|----------|----------|
| One branch fails | Other branches continue independently |
| Parent interaction | Completes immediately regardless of fork outcomes |
| Fork throws exception | Exception is isolated to that fork |
| Missing referenced interaction | Only that branch fails to execute |

**Important:** There is no built-in synchronization point for waiting on all forks to complete. If you need to ensure all parallel branches finish before continuing, you must design your interaction flow accordingly (e.g., using `RunTime` on a wrapping Simple interaction).

### Common Patterns

| Pattern | Description | Example Use |
|---------|-------------|-------------|
| **Damage + Visuals separation** | One branch for damage logic, another for effects | NPC attacks, weapon abilities |
| **Multiple status effects** | Apply several effects at once | Elemental weapons, potions |
| **AOE with feedback** | Damage selector + particles + sound | Ground slams, explosions |
| **Template branches** | Replace variables for customizable forks | Reusable attack templates |
| **Conditional parallel effects** | Parallel inside Then/Else blocks | Critical hit bonuses |

### When to Use Parallel vs Serial

| Aspect | Serial | Parallel |
|--------|--------|----------|
| **Execution order** | Sequential (1 → 2 → 3) | Simultaneous (1, 2, 3 all at once) |
| **Timing** | Total time = sum of all interactions | Total time = longest interaction |
| **Dependencies** | Each step can depend on previous | No ordering guarantees |
| **Context** | Shared context throughout | First shares, rest get duplicates |
| **Use case** | Multi-step abilities, state changes | Multiple simultaneous effects |
| **Failure handling** | Subsequent steps still execute | All started regardless of failures |

**When to use Parallel:**
- Applying multiple status effects at once
- Separating damage logic from visual effects
- Playing multiple sounds/particles simultaneously
- Independent effects that don't need ordering
- Reducing total execution time (parallel = max duration, not sum)

**When to use Serial:**
- Stat changes that must happen before damage
- Consuming items before applying effects
- Animations that must play in sequence
- Any ordered multi-step process
- When effects must modify the same context

### Related Interactions

- [Serial](#serial) - Execute interactions sequentially instead of concurrently
- [Condition](#condition) - Conditional branching (can contain Parallel in Then/Else)
- [StatsCondition](#statscondition) - Stat-based branching (can contain Parallel in Then/Else)
- [Replace](#replace) - Variable substitution for template branches
- [Repeat](#repeat) - Execute interactions multiple times (can wrap Parallel)

---

## Condition

**Package:** `config/none/ConditionInteraction`

The base Condition interaction provides branching based on game mode and entity movement states (jumping, swimming, crouching, running, flying). It evaluates the current state of an entity and branches to either `Next` (condition passed) or `Failed` (condition did not pass).

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Condition"` |
| `RequiredGameMode` | string | `null` | Game mode that must be active (`Creative`, `Survival`, `Adventure`) |
| `Jumping` | boolean | `null` | If set, entity must be/not be jumping |
| `Swimming` | boolean | `null` | If set, entity must be/not be swimming |
| `Crouching` | boolean | `null` | If set, entity must be/not be crouching |
| `Running` | boolean | `null` | If set, entity must be/not be running (sprinting) |
| `Flying` | boolean | `null` | If set, entity must be/not be flying |
| `Next` | interaction | `null` | Interaction to execute when condition passes |
| `Failed` | interaction | `null` | Interaction to execute when condition fails |

### Branching Behavior

Unlike most condition interactions that use `Then`/`Else`, the base Condition uses `Next`/`Failed`:

- **Next**: Executed when ALL specified conditions are met
- **Failed**: Executed when ANY specified condition is not met
- Unset properties (`null`) are not checked - only explicitly set conditions are evaluated

### Execution Flow

```
Condition Evaluation
    │
    ├─► Check RequiredGameMode (if set)
    │       └─► Mismatch? → Execute Failed
    │
    ├─► Check Jumping (if set)
    │       └─► Mismatch? → Execute Failed
    │
    ├─► Check Swimming (if set)
    │       └─► Mismatch? → Execute Failed
    │
    ├─► Check Crouching (if set)
    │       └─► Mismatch? → Execute Failed
    │
    ├─► Check Running (if set)
    │       └─► Mismatch? → Execute Failed
    │
    ├─► Check Flying (if set)
    │       └─► Mismatch? → Execute Failed
    │
    └─► All checks passed → Execute Next
```

### Examples

**Game Mode Restriction:**

Only allow ability in Creative mode:

```json
{
  "Type": "Condition",
  "RequiredGameMode": "Creative",
  "Next": {
    "Type": "SpawnPrefab",
    "PrefabId": "debug_entity"
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Creative mode only!"
  }
}
```

**Aerial Combat Ability:**

Special attack that only works while jumping:

```json
{
  "Type": "Condition",
  "Jumping": true,
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": -1, "Z": 0 },
        "AdjustVertical": false,
        "Force": 15.0
      },
      {
        "Type": "Selector",
        "Selector": { "Id": "AOECircle", "Range": 3.0 },
        "HitEntity": {
          "Interactions": [
            {
              "Type": "DamageEntity",
              "DamageCalculator": { "BaseDamage": { "Physical": 40 } }
            }
          ]
        }
      }
    ]
  },
  "Failed": "Ground_Attack_Normal"
}
```

**Aquatic Boost:**

Faster swimming when already in water:

```json
{
  "Type": "Condition",
  "Swimming": true,
  "Next": {
    "Type": "ApplyEffect",
    "EffectId": "dolphins_grace"
  }
}
```

**Stealth Attack:**

Bonus damage when attacking from crouch:

```json
{
  "Type": "Condition",
  "Crouching": true,
  "Next": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 50 } }
  },
  "Failed": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 20 } }
  }
}
```

**Sprint Attack:**

Momentum-based damage scaling:

```json
{
  "Type": "Condition",
  "Running": true,
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 35 } }
      },
      {
        "Type": "Simple",
        "Effects": { "WorldSoundEventId": "charge_impact" }
      }
    ]
  },
  "Failed": "Attack_Normal"
}
```

**Multiple Conditions:**

All specified conditions must be true:

```json
{
  "Type": "Condition",
  "RequiredGameMode": "Survival",
  "Running": true,
  "Jumping": false,
  "Next": "Sprint_Slide_Start",
  "Failed": "Movement_Normal"
}
```

This checks: Survival mode AND sprinting AND NOT jumping.

### Related Interactions

- [StatsCondition](#statscondition) - Branch based on stat values
- [EffectCondition](#effectcondition) - Branch based on active effects
- [MovementCondition](#movementcondition) - Branch based on movement direction input

---

## StatsCondition

**Package:** `config/none/StatsConditionInteraction`

Branch based on whether an entity can afford a set of stat costs. Each entry in the `Costs` map names a stat and the amount required; when all costs are satisfiable the interaction deducts them and branches to `Next`, otherwise it branches to `Failed`. Essential for resource gating (stamina, signature energy) and stat-based ability variations.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"StatsCondition"` |
| `Costs` | object | Required | Map of stat name to required amount (deducted when the check passes) |
| `ValueType` | string | `"Absolute"` | How to interpret the cost amounts (`Absolute` or `Percent`) |
| `Lenient` | boolean | `false` | If true, passes when a referenced stat doesn't exist on the entity |
| `Next` | interaction | `null` | Interaction when the costs can be paid (and are deducted) |
| `Failed` | interaction | `null` | Interaction when the costs cannot be paid |

### ValueType Reference

| ValueType | Description |
|-----------|-------------|
| `Absolute` | Cost amounts are raw stat values |
| `Percent` | Cost amounts are a percentage of the stat's maximum (0-100) |

### Lenient Mode

When `Lenient` is `true`, the condition passes if a referenced stat doesn't exist on the entity. This is useful for optional stats that not all entities have.

```json
{
  "Type": "StatsCondition",
  "Costs": { "CustomAbilityCharge": 100 },
  "Lenient": true,
  "Next": "Execute_Ability",
  "Failed": "Charge_More"
}
```

If an entity doesn't have `CustomAbilityCharge`, it will execute `Next` instead of failing.

### Common Stats

| Stat | Description |
|------|-------------|
| `Health` | Current health points |
| `Stamina` | Current stamina points |
| `SignatureEnergy` | Signature ability charge |
| `StaminaRegenDelay` | Delay before stamina begins regenerating |

### Examples

**Stamina Cost Check (from Double_Jump.json):**

The `Costs` map both checks for and deducts the stamina, so no separate `ChangeStat` is needed for the cost itself:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 2.01 },
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": 2, "Z": 0 },
        "AdjustVertical": false,
        "Force": 15
      }
    ]
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Not enough stamina!"
  }
}
```

**Signature Energy Threshold:**

```json
{
  "Type": "StatsCondition",
  "Costs": { "SignatureEnergy": 100 },
  "Next": "Signature_Ability_Execute",
  "Failed": {
    "Type": "Simple",
    "Effects": { "WorldSoundEventId": "ability_not_ready" }
  }
}
```

**Percent Cost:**

Interpret the cost as a percentage of the stat's maximum:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Health": 20 },
  "ValueType": "Percent",
  "Next": "Apply_Blood_Magic",
  "Failed": "Apply_Normal_Effect"
}
```

**Nested Cost Checks:**

Multiple resource requirements, each checked (and deducted) in turn:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 50 },
  "Next": {
    "Type": "StatsCondition",
    "Costs": { "SignatureEnergy": 30 },
    "Next": "Hybrid_Ability_Execute",
    "Failed": { "Type": "SendMessage", "Message": "Not enough energy!" }
  },
  "Failed": { "Type": "SendMessage", "Message": "Not enough stamina!" }
}
```

### Related Interactions

- [Condition](#condition) - Game mode and movement state branching
- [EffectCondition](#effectcondition) - Branch based on active effects
- [ChangeStat](interactions-combat.md#changestat) - Modify stat values

---

## EffectCondition

**Package:** `config/none/EffectConditionInteraction`

Branch based on whether an entity has active status effects. Supports checking for multiple effects with configurable match modes (`All` or `None`). Use this for effect-based combat bonuses, immunity checks, and tiered buff systems.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"EffectCondition"` |
| `EntityEffectIds` | array | Required | List of effect IDs to check |
| `Match` | string | `"All"` | Match mode: `"All"` or `"None"` |
| `Entity` | string | `"User"` | Which entity to check (e.g. `"User"`, `"Target"`) |
| `Next` | interaction | `null` | Interaction when the match condition holds |
| `Failed` | interaction | `null` | Interaction when the match condition does not hold |

### Match Modes

| Mode | Description |
|------|-------------|
| `All` | Entity must have ALL specified effects |
| `None` | Entity must have NONE of the specified effects |

### Entity Reference

| Entity | Description |
|--------|-------------|
| `User` | Check the entity executing the interaction |
| `Target` | Check the target entity (from context) |

### Execution Behavior

```
EffectCondition Evaluation
    │
    ├─► Resolve Entity (User or Target)
    │
    ├─► For each effect in EntityEffectIds:
    │       └─► Check if entity has effect
    │
    ├─► Match Mode: All
    │       └─► ALL effects present? → Next
    │       └─► ANY effect missing? → Failed
    │
    └─► Match Mode: None
            └─► NO effects present? → Next
            └─► ANY effect present? → Failed
```

### Examples

**Single Effect Check:**

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["burning"],
  "Entity": "Target",
  "Next": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 30 } }
  },
  "Failed": {
    "Type": "ApplyEffect",
    "EffectId": "burning"
  }
}
```

If target is burning, deal bonus fire damage. Otherwise, ignite them.

**Multiple Effects Check (All):**

Combo system requiring multiple debuffs:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["burning", "poisoned", "frozen"],
  "Match": "All",
  "Entity": "Target",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 100 } }
      },
      { "Type": "ClearEntityEffect", "EffectId": "burning" },
      { "Type": "ClearEntityEffect", "EffectId": "poisoned" },
      { "Type": "ClearEntityEffect", "EffectId": "frozen" },
      { "Type": "Simple", "Effects": { "Particles": [ { "SystemId": "elemental_explosion" } ] } }
    ]
  },
  "Failed": "Normal_Attack"
}
```

**Immunity Check (None):**

Prevent effect stacking:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["immunity"],
  "Match": "None",
  "Entity": "Target",
  "Next": {
    "Type": "ApplyEffect",
    "EffectId": "stun"
  },
  "Failed": {
    "Type": "Simple",
    "Effects": { "WorldSoundEventId": "ability_blocked" }
  }
}
```

Only apply stun if target doesn't have immunity.

**Tiered Buff System (Meat_TierCheck pattern):**

Check for food buff tiers:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["well_fed_tier3"],
  "Match": "None",
  "Entity": "User",
  "Next": {
    "Type": "EffectCondition",
    "EntityEffectIds": ["well_fed_tier2"],
    "Match": "None",
    "Entity": "User",
    "Next": {
      "Type": "EffectCondition",
      "EntityEffectIds": ["well_fed_tier1"],
      "Match": "None",
      "Entity": "User",
      "Next": "Apply_Tier1_Buff",
      "Failed": "Upgrade_To_Tier2"
    },
    "Failed": "Upgrade_To_Tier3"
  },
  "Failed": "Refresh_Tier3"
}
```

**Self-Buff Check:**

Only allow ability if not already buffed:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["enraged"],
  "Match": "None",
  "Entity": "User",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyEffect", "EffectId": "enraged" },
      { "Type": "Simple", "Effects": { "ItemAnimationId": "Enrage" } }
    ]
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Already enraged!"
  }
}
```

**Elemental Weakness:**

Bonus damage against debuffed targets:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["wet"],
  "Match": "All",
  "Entity": "Target",
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 40 } } },
      { "Type": "ApplyEffect", "EffectId": "shocked" }
    ]
  },
  "Failed": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 20 } }
  }
}
```

### Related Interactions

- [Condition](#condition) - Game mode and movement state branching
- [StatsCondition](#statscondition) - Branch based on stat values
- [ApplyEffect](interactions-combat.md#applyeffect) - Apply status effects
- [ClearEntityEffect](interactions-combat.md#clearentityeffect) - Remove status effects

---

## BlockCondition

**Package:** `config/client/BlockConditionInteraction`

Branch based on block type and state at a target position. Uses a `Matchers` array where each matcher nests block identity in a `Block` object and may add face-specific options for directional placement logic. Branches with `Next` (any matcher succeeds) and `Failed` (all matchers fail).

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"BlockCondition"` |
| `Matchers` | array | Required | List of `BlockMatcher` objects |
| `Next` | interaction | `null` | Interaction when any matcher succeeds |
| `Failed` | interaction | `null` | Interaction when all matchers fail |

### BlockMatcher Structure

Each `BlockMatcher` in the array nests block identity in a `Block` object, with optional face siblings:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Block` | object | Required | Block matcher: `{ "Id": ..., "State": ... }` |
| `Block.Id` | string | `null` | Exact block ID to match |
| `Block.State` | string | `null` | Block state name to match (e.g. `"default"`) |
| `Face` | string | `"None"` | Which face to check relative to target |
| `StaticFace` | boolean | `false` | If true, face is absolute; if false, face is relative to player |

### Face Reference

| Face | Description |
|------|-------------|
| `None` | Check block at target position |
| `Up` | Check block above target |
| `Down` | Check block below target |
| `Left` | Check block to the left |
| `Right` | Check block to the right |
| `Front` | Check block in front |
| `Back` | Check block behind |

### StaticFace Behavior

| StaticFace | Behavior |
|------------|----------|
| `false` | Face directions are relative to player's facing direction |
| `true` | Face directions are absolute world directions |

### Examples

**Specific Block ID Check (from Lantern_Yellow.json):**

Only act when the target block is a specific lantern, then change its state:

```json
{
  "Type": "BlockCondition",
  "Matchers": [
    {
      "Block": {
        "Id": "Furniture_Human_Ruins_Lantern"
      }
    }
  ],
  "Next": {
    "Type": "ChangeState",
    "Changes": { "default": "Yellow" }
  },
  "Failed": "Block_Secondary"
}
```

**Block + State + Face Check (from Half_Block.json):**

Check that the block on the `Up` face is stone in its `default` state before placing:

```json
{
  "Type": "BlockCondition",
  "Matchers": [
    {
      "Block": {
        "Id": "Rock_Stone",
        "State": "default"
      },
      "Face": "Up",
      "StaticFace": false
    }
  ],
  "Next": {
    "Type": "ChangeState",
    "Changes": { "default": "Block" },
    "Next": {
      "Type": "ModifyInventory",
      "AdjustHeldItemQuantity": -1,
      "RequiredGameMode": "Adventure"
    }
  },
  "Failed": "Block_Secondary"
}
```

**Multiple Matchers (OR logic):**

Succeed if the target matches any of several block types:

```json
{
  "Type": "BlockCondition",
  "Matchers": [
    { "Block": { "Id": "Soil_Farmland" } },
    { "Block": { "Id": "Soil_Grass" } },
    { "Block": { "Id": "Soil_Dirt" } }
  ],
  "Next": "Plant_Seed",
  "Failed": {
    "Type": "SendMessage",
    "Message": "Cannot plant here!"
  }
}
```

### Related Interactions

- [PlacementCountCondition](#placementcountcondition) - Check block placement limits
- [Block Interactions](interactions-world.md#block-interactions) - Break or place blocks

---

## CooldownCondition

**Package:** `config/client/CooldownConditionInteraction`

Branch based on whether a cooldown has completed. Checks if the specified cooldown timer has elapsed, allowing time-gated abilities and rate limiting.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"CooldownCondition"` |
| `Id` | string | Required | Cooldown identifier to check |
| `Next` | interaction | `null` | Interaction when cooldown is ready |
| `Failed` | interaction | `null` | Interaction when cooldown is active |

### Execution Flow

```
CooldownCondition
    │
    ▼
┌─────────────────────────┐
│ Check cooldown by Id    │
└─────────────────────────┘
    │
    ├─► Cooldown elapsed (ready) ──► Execute Next
    │
    └─► Cooldown active ──► Execute Failed
```

### Execution Behavior

CooldownCondition checks if the specified cooldown timer has expired:

- **Next**: Executed when cooldown has elapsed (ability is ready)
- **Failed**: Executed when cooldown is still active (ability on cooldown)

Cooldowns are typically started using [TriggerCooldown](#triggercooldown) and can be reset using [ResetCooldown](#resetcooldown).

### Examples

**NPC Poison Attack (from Spider.json):**

Check if poison cooldown has elapsed before applying poison effect:

```json
{
  "Type": "CooldownCondition",
  "Id": "Spider_Poison",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "TriggerCooldown",
        "Cooldown": {
          "Id": "Spider_Poison",
          "Cooldown": 8
        }
      },
      {
        "Type": "ApplyEffect",
        "EffectId": "poison"
      },
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 5 } }
      }
    ]
  },
  "Failed": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 5 } }
  }
}
```

**Boss Special Attack (from Snapdragon.json):**

Cooldown-gated fire breath attack:

```json
{
  "Type": "CooldownCondition",
  "Id": "Snapdragon_FireBreath",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "TriggerCooldown",
        "Cooldown": {
          "Id": "Snapdragon_FireBreath",
          "Cooldown": 12
        }
      },
      "Snapdragon_FireBreath_Execute"
    ]
  },
  "Failed": "Snapdragon_BasicAttack"
}
```

**Conditional Damage Bonus:**

Apply bonus damage only when cooldown is ready:

```json
{
  "Type": "CooldownCondition",
  "Id": "critical_strike",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 25 } }
      },
      {
        "Type": "TriggerCooldown",
        "Cooldown": {
          "Id": "critical_strike",
          "Cooldown": 5
        }
      }
    ]
  },
  "Failed": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 10 } }
  }
}
```

### Related Interactions

- [TriggerCooldown](#triggercooldown) - Start a cooldown timer
- [ResetCooldown](#resetcooldown) - Reset a cooldown timer
- [Condition](#condition) - Base conditional branching
- [StatsCondition](#statscondition) - Resource-based gating

---

## TriggerCooldown

**Package:** `config/client/TriggerCooldownInteraction`

Start a cooldown timer. Used to initiate time-gated abilities that can later be checked with [CooldownCondition](#cooldowncondition).

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"TriggerCooldown"` |
| `Cooldown` | object | Required | [InteractionCooldown](#interactioncooldown-configuration) configuration |

### InteractionCooldown Configuration

The `Cooldown` property uses the InteractionCooldown configuration object:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Id` | string | `null` | Cooldown identifier (used to check with CooldownCondition) |
| `Cooldown` | float | Required | Duration in seconds |
| `ClickBypass` | boolean | `false` | If true, clicking bypasses the cooldown |
| `Charges` | float[] | `null` | Array of charge times for charged abilities |
| `SkipCooldownReset` | boolean | `false` | If true, prevents cooldown from being reset when triggered again |
| `InterruptRecharge` | boolean | `false` | If true, interrupting the ability also interrupts cooldown recharge |

### Examples

**Basic Cooldown Start:**

```json
{
  "Type": "TriggerCooldown",
  "Cooldown": {
    "Id": "ability_dash",
    "Cooldown": 5
  }
}
```

**NPC Attack Cooldown (from Spider.json):**

```json
{
  "Type": "TriggerCooldown",
  "Cooldown": {
    "Id": "Spider_Poison",
    "Cooldown": 8
  }
}
```

**Cooldown with Click Bypass (from RootInteractions):**

Used in block interactions where clicking can bypass the wait:

```json
{
  "Type": "TriggerCooldown",
  "Cooldown": {
    "Id": "BlockInteraction_Creative",
    "Cooldown": 0.0,
    "ClickBypass": true
  }
}
```

**Cooldown without Id:**

Anonymous cooldown (cannot be checked with CooldownCondition):

```json
{
  "Type": "TriggerCooldown",
  "Cooldown": {
    "Cooldown": 1.5
  }
}
```

### Usage Pattern

TriggerCooldown is typically used inside the `Next` branch of a CooldownCondition:

```json
{
  "Type": "CooldownCondition",
  "Id": "my_ability",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "TriggerCooldown",
        "Cooldown": {
          "Id": "my_ability",
          "Cooldown": 10
        }
      },
      "Execute_Ability"
    ]
  },
  "Failed": "Ability_NotReady_Feedback"
}
```

### Related Interactions

- [CooldownCondition](#cooldowncondition) - Check if cooldown has elapsed
- [ResetCooldown](#resetcooldown) - Reset a cooldown timer

---

## ResetCooldown

**Package:** `config/client/ResetCooldownInteraction`

Reset a cooldown timer, making it immediately ready. Used to cancel active cooldowns or refresh ability availability.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"ResetCooldown"` |
| `Cooldown` | object | Required | [InteractionCooldown](#interactioncooldown-configuration) configuration |

### Examples

**Reset Named Cooldown:**

```json
{
  "Type": "ResetCooldown",
  "Cooldown": {
    "Id": "ability_dash",
    "Cooldown": 0
  }
}
```

**Reset on Parry (from Debug_Stick_Parry.json):**

Successful parry resets attack cooldown:

```json
{
  "Type": "Serial",
  "Interactions": [
    "Parry_Success_Effects",
    {
      "Type": "ResetCooldown",
      "Cooldown": {
        "Id": "attack_cooldown",
        "Cooldown": 0
      }
    }
  ]
}
```

**Reset Anonymous Cooldown (from Bomb_Throw.json):**

```json
{
  "Type": "ResetCooldown",
  "Cooldown": {
    "Cooldown": 1
  }
}
```

### Usage Patterns

**Reset on Kill:**

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "DamageEntity",
      "DamageCalculator": { "BaseDamage": { "Physical": 100 } }
    },
    {
      "Type": "ResetCooldown",
      "Cooldown": {
        "Id": "execute_ability",
        "Cooldown": 0
      }
    }
  ]
}
```

**Emergency Reset Consumable:**

```json
{
  "Type": "Serial",
  "Interactions": [
    { "Type": "ModifyInventory", "AdjustHeldItemQuantity": -1 },
    {
      "Type": "ResetCooldown",
      "Cooldown": {
        "Id": "ultimate_ability",
        "Cooldown": 0
      }
    }
  ]
}
```

### Related Interactions

- [CooldownCondition](#cooldowncondition) - Check if cooldown has elapsed
- [TriggerCooldown](#triggercooldown) - Start a cooldown timer

---

## MovementCondition

**Package:** `config/client/MovementConditionInteraction`

Branch based on player movement input direction. Provides eight directional branches plus a failed branch, enabling direction-based combat abilities like directional dodges, strafing attacks, and movement-responsive mechanics.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"MovementCondition"` |
| `Forward` | interaction | `null` | Interaction when moving forward |
| `Back` | interaction | `null` | Interaction when moving backward |
| `Left` | interaction | `null` | Interaction when moving left |
| `Right` | interaction | `null` | Interaction when moving right |
| `ForwardLeft` | interaction | `null` | Interaction when moving forward-left diagonal |
| `ForwardRight` | interaction | `null` | Interaction when moving forward-right diagonal |
| `BackLeft` | interaction | `null` | Interaction when moving backward-left diagonal |
| `BackRight` | interaction | `null` | Interaction when moving backward-right diagonal |
| `Failed` | interaction | `null` | Interaction when no movement or no matching direction |

### Direction Detection

Directions are based on player input relative to camera facing:

```
        Forward
           ↑
   ForwardLeft  ForwardRight
        ↖   ↗
Left  ←       →  Right
        ↙   ↘
   BackLeft    BackRight
           ↓
         Back
```

### Execution Behavior

1. Reads current movement input direction
2. Matches to closest of 8 cardinal/diagonal directions
3. Executes corresponding branch interaction
4. If no movement input or no branch defined for direction, executes `Failed`

### Examples

**Directional Dodge System:**

```json
{
  "Type": "MovementCondition",
  "Forward": "Dodge_Forward",
  "Back": "Dodge_Back",
  "Left": "Dodge_Left",
  "Right": "Dodge_Right",
  "ForwardLeft": "Dodge_Forward_Left",
  "ForwardRight": "Dodge_Forward_Right",
  "BackLeft": "Dodge_Back_Left",
  "BackRight": "Dodge_Back_Right",
  "Failed": "Dodge_Back"
}
```

**Directional Attack Variations:**

```json
{
  "Type": "MovementCondition",
  "Forward": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": 0, "Z": 1 },
        "AdjustVertical": false,
        "Force": 5.0 },
      { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 25 } } }
    ]
  },
  "Back": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": 0, "Z": -1 },
        "AdjustVertical": false,
        "Force": 3.0 },
      { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 15 } } }
    ]
  },
  "Left": "Slash_Left",
  "Right": "Slash_Right",
  "Failed": "Slash_Neutral"
}
```

**Simple Four-Direction Dodge:**

Only handle cardinal directions, default others to Failed:

```json
{
  "Type": "MovementCondition",
  "Forward": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": 0, "Z": 1 },
        "AdjustVertical": false,
        "Force": 8.0 },
      { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
      { "Type": "ApplyEffect", "EffectId": "invulnerable" }
    ]
  },
  "Back": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyForce",
        "Direction": { "X": 0, "Y": 0, "Z": -1 },
        "AdjustVertical": false,
        "Force": 8.0 },
      { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
      { "Type": "ApplyEffect", "EffectId": "invulnerable" }
    ]
  },
  "Left": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyForce",
        "Direction": { "X": -1, "Y": 0, "Z": 0 },
        "AdjustVertical": false,
        "Force": 8.0 },
      { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
      { "Type": "ApplyEffect", "EffectId": "invulnerable" }
    ]
  },
  "Right": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyForce",
        "Direction": { "X": 1, "Y": 0, "Z": 0 },
        "AdjustVertical": false,
        "Force": 8.0 },
      { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
      { "Type": "ApplyEffect", "EffectId": "invulnerable" }
    ]
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Hold a direction to dodge!"
  }
}
```

**Movement-Based Attack Selection:**

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 15 },
  "Next": {
    "Type": "MovementCondition",
    "Forward": "Lunge_Attack",
    "Back": "Retreating_Slash",
    "Left": "Sidestep_Left_Attack",
    "Right": "Sidestep_Right_Attack",
    "Failed": "Standing_Attack"
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Not enough stamina!"
  }
}
```

### Related Interactions

- [Condition](#condition) - Movement state branching (jumping, running, etc.)
- [ApplyForce](interactions-combat.md#applyforce) - Apply movement forces

---

## PlacementCountCondition

**Package:** `config/server/PlacementCountConditionInteraction`

Server-side condition that checks the count of a specific block type placed by the player in the current instance. Used to enforce placement limits for special blocks like teleporters. The condition passes when the player's placement count is less than the threshold value.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"PlacementCountCondition"` |
| `Block` | string | Required | Block ID to count (without namespace prefix) |
| `Value` | int | Required | Threshold value - condition passes when count < this value |
| `Next` | interaction | `null` | Interaction when count < Value (condition passes) |
| `Failed` | interaction | `null` | Interaction when count >= Value (condition fails) |

### Execution Flow

```
PlacementCountCondition
    │
    ▼
┌─────────────────────────┐
│ Get player's block      │
│ placement count from    │
│ instance BlockCounter   │
└─────────────────────────┘
    │
    ├─► count < Value ──► Execute Next
    │
    └─► count >= Value ──► Execute Failed
```

PlacementCountCondition performs server-side validation:

1. Reads the block type from `Block` property
2. Queries the instance's `BlockCounter` for the player's placement count of that block type
3. Compares count against `Value` threshold
4. Branches to `Next` if count is below threshold, `Failed` if at or above

### Block Tracking Requirements

For PlacementCountCondition to work, two components must be configured:

**1. Block must have TrackedPlacement component:**

Blocks that should be counted need the `TrackedPlacement` component in their BlockEntity definition:

```json
{
  "BlockEntity": {
    "TrackedPlacement": {}
  }
}
```

**2. Instance must have BlockCounter resource:**

The instance resource (e.g., `BlockCounter.json`) tracks placement counts:

```json
{
  "BlockPlacementCounts": {}
}
```

### Examples

**Teleporter Placement Limit (Real - from Teleporter_Try_Place.json):**

Only allow placing a teleporter if the player has fewer than 2:

```json
{
  "Type": "PlacementCountCondition",
  "Block": "Teleporter",
  "Value": 2,
  "Next": {
    "Type": "PlaceBlock",
    "RunTime": 0.125
  },
  "Failed": {
    "Type": "SendMessage",
    "Key": "server.interactions.teleporter.failedCollectMore"
  }
}
```

**Combined with MemoriesCondition for Tier-Based Limits:**

Different memory states can unlock higher placement limits:

```json
{
  "Type": "MemoriesCondition",
  "Conditions": [
    {
      "Condition": "UnlockedTeleporterTier2",
      "Interaction": {
        "Type": "PlacementCountCondition",
        "Block": "Teleporter",
        "Value": 4,
        "Next": "Place_Teleporter",
        "Failed": {
          "Type": "SendMessage",
          "Key": "server.interactions.teleporter.limitReached"
        }
      }
    }
  ],
  "Failed": {
    "Type": "PlacementCountCondition",
    "Block": "Teleporter",
    "Value": 2,
    "Next": "Place_Teleporter",
    "Failed": {
      "Type": "SendMessage",
      "Key": "server.interactions.teleporter.failedCollectMore"
    }
  }
}
```

**Spawner Limit Check:**

```json
{
  "Type": "PlacementCountCondition",
  "Block": "CreatureSpawner",
  "Value": 5,
  "Next": "Place_Spawner",
  "Failed": {
    "Type": "SendMessage",
    "Key": "server.interactions.spawner.maxReached"
  }
}
```

### Related Interactions

- [CooldownCondition](#cooldowncondition) - Check cooldown state (also uses `Next`/`Failed`)
- MemoriesCondition - Branch based on player memory states
- [Block Interactions](interactions-world.md#block-interactions) - PlaceBlock interaction for actual placement

---

## Repeat

**Package:** `config/none/RepeatInteraction`

Loop execution of interactions with timing control and optional interruption.

### Structure

```json
{
  "Type": "Repeat",
  "Repeat": 3,
  "RunTime": 0.5,
  "ForkInteractions": {
    "Interactions": [
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 5 } }
      }
    ]
  },
  "Next": {
    "Type": "SendMessage",
    "Message": "Repeat complete"
  }
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Repeat` | int | Number of repetitions. Use `-1` for indefinite looping until interrupted |
| `RunTime` | float | Duration of each iteration in seconds |
| `ForkInteractions` | object | Contains `Interactions` array to execute each iteration |
| `Next` | interaction | Interaction to execute after all repetitions complete |
| `HorizontalSpeedMultiplier` | float | Movement speed modifier during repeat (e.g., `0.6` for 60% speed) |
| `Rules` | object | Contains `InterruptedBy` array for early termination |
| `Failed` | interaction | Handler when repeat cannot continue or is interrupted |

### Examples

**Whirlwind Attack (speed-modified combat loop):**

```json
{
  "Type": "Repeat",
  "Repeat": 10,
  "HorizontalSpeedMultiplier": 0.6,
  "ForkInteractions": {
    "Interactions": [
      "Whirlwind_Spin_Effect",
      "Whirlwind_Damage_Selector"
    ]
  }
}
```

**Interruptible Reload (indefinite loop):**

```json
{
  "Type": "Repeat",
  "Repeat": -1,
  "Rules": {
    "InterruptedBy": ["Primary", "Secondary"]
  },
  "ForkInteractions": {
    "Interactions": [
      { "Type": "ChangeStat", "StatModifiers": { "Ammo": 1 } }
    ]
  },
  "Failed": {
    "Type": "SendMessage",
    "Message": "Reload interrupted"
  }
}
```

**Rapid Strikes (timed iterations):**

```json
{
  "Type": "Repeat",
  "Repeat": 4,
  "RunTime": 0.138,
  "ForkInteractions": {
    "Interactions": [
      "Stab_Left",
      "Stab_Right"
    ]
  }
}
```

### Notes

- Without the `Repeat` property specified, acts as a single fork that waits for completion
- Can be nested within other flow interactions for complex multi-level repetition patterns
- `Rules.InterruptedBy` accepts input names like `"Primary"`, `"Secondary"` to allow player input to break the loop

---

## Replace

**Package:** `config/none/ReplaceInteraction`

Variable substitution for creating reusable interaction templates. Looks up a variable from the interaction context and executes its value, or falls back to a default.

### Structure

```json
{
  "Type": "Replace",
  "Var": "EffectName",
  "DefaultValue": {
    "Interactions": ["Fallback_Effect"]
  },
  "DefaultOk": true
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Var` | string | Variable name to look up from context |
| `DefaultValue` | object | Fallback interaction(s) if variable isn't set |
| `DefaultOk` | boolean | If `true`, silently uses default when variable missing. If `false`, logs SEVERE error then uses default. |

### DefaultOk Behavior

| `DefaultOk` | Variable Missing | Result |
|-------------|------------------|--------|
| `true` | Yes | Silently uses `DefaultValue` |
| `false`/omitted | Yes | Logs SEVERE error, then uses `DefaultValue` |
| either | No | Uses the variable's value |

### Example: Reusable Consumable Template

Create a generic consume template that items can customize:

**Consume_Template.json:**
```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Charging",
      "FailOnDamage": true,
      "Next": {
        "2.0": {
          "Type": "Serial",
          "Interactions": [
            {
              "Type": "ModifyInventory",
              "AdjustHeldItemQuantity": -1
            },
            {
              "Type": "Replace",
              "Var": "Effect",
              "DefaultValue": {
                "Interactions": ["No_Effect"]
              }
            }
          ]
        }
      }
    }
  ]
}
```

Items referencing this template provide their own `Effect` variable to inject custom behavior (healing, buffs, etc.) without duplicating the consume logic.

---

## Target Selectors

For target selection in combat interactions, see the **[Selector](interactions-combat.md#selector)** interaction in the Combat Interactions documentation.

The `Selector` interaction type defines hitbox shapes (`Horizontal`, `AOECircle`, `Stab`, `Raycast`) and executes interactions when entities or blocks are hit.

---

## Gotchas & Errors

- **Symptom:** a `Replace` logs a SEVERE error in the server log → `DefaultOk` is `false`/omitted and the `Var` was not provided by the item. It still falls back to `DefaultValue`, but noisily. Fix: set `"DefaultOk": true` when the variable is genuinely optional, or have the referencing item define the variable (see [DefaultOk Behavior](#defaultok-behavior)).
- **Symptom:** the same effect (e.g. damage) only applies once when run under `Parallel`, not per-branch → `Parallel` branches execute against duplicated contexts, so changes to the shared context are not additive. Fix: use `Serial` for effects that must stack (see the Parallel notes around [duplicated context](#parallel)).
- **Symptom:** branches after a `Parallel` run before all forks finish → there is no built-in join/sync point for parallel forks. Fix: wrap in a `Simple` interaction with a `RunTime` long enough to cover the branches, or restructure with `Serial`.
- **Symptom:** a `Condition` / `StatsCondition` interaction does nothing → no branch matched the current game-mode/stat/state and there was no fallthrough target. Fix: provide a default/`Next` branch so the interaction has somewhere to go when no condition matches.
