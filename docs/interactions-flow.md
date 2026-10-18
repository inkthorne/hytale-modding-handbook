---
title: "Control Flow Interactions"
description: "Control Hytale interaction flow in JSON — Serial and Parallel composition of child interactions and conditional branching on state, stats, effects, blocks, cooldowns, and placement."
seo:
  type: TechArticle
---

# Control Flow Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.7.2**

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

This page covers the control-flow interactions: composing interactions in sequence or parallel, branching on game state, looping, variable substitution, and target selection.

> **Chains NPCs run.** NPC attack chains are built from these types on a manager with no remote client, so the server runs each operation twice. `Serial`, `Parallel` and `Replace` add nothing of their own (the effect is their children's), `Repeat` forks once, the conditions only read, and `TriggerCooldown` spends a cooldown's charge in each pass (the default one charge is safe). [The double run](interactions-double-run.md#what-each-of-the-48-types-does) has the verdict for each type.

> **Reading the examples.** An example that names a shipped source file is taken from the shipped
> assets. In the others, every id that starts with `MyMod_` is a placeholder for an interaction (or,
> in a slot that takes one, a root interaction) that you write yourself; all other interaction,
> effect, sound, particle, block and animation ids are real shipped ids. References resolve by
> basename, so a `MyMod_` string fails validation until an asset of that name exists.

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
| [AugmentCondition](#augmentcondition) | Branch on augment tags granted around the target block |
| [CooldownCondition](#cooldowncondition) | Branch based on cooldown completion |
| [TriggerCooldown](#triggercooldown) | Start a cooldown timer |
| [ResetCooldown](#resetcooldown) | Reset a cooldown timer |
| [IncrementCooldown](#incrementcooldown) | Adjust a cooldown that is already running |
| [MovementCondition](#movementcondition) | Direction-based input branching |
| [PlacementCountCondition](#placementcountcondition) | Branch based on block placement count |
| [Repeat](#repeat) | Loop execution of interactions |
| [Replace](#replace) | Variable substitution for templates |
| [RunOnBlockTypes](#runonblocktypes) | Fork a chain onto each matching block in range |
| [Target Selectors](#target-selectors) | AOE, raycast, and stab targeting |

---

## Serial

**Package:** `config/none/SerialInteraction`

Executes multiple interactions sequentially, one after another. Each interaction in the sequence must complete before the next one begins. This is the fundamental building block for multi-step abilities, consumables, combo finishers, and any interaction that requires ordered execution of multiple effects.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Serial"` |
| `Interactions` | array | Required | Codec doc: "A list of interactions to run. They will be executed in the order specified sequentially." Validated non-null with non-null elements; unlike [Parallel](#parallel) there is no minimum length |

`SerialInteraction` extends `Interaction` directly, so it has **no `Next`/`Failed` of its own** (those keys live on `SimpleInteraction`). It is also never ticked: `compile()` inlines each child into the chain's operation stream, so a `Serial` is a purely structural wrapper.

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
    "MyMod_Attack_Windup",
    "MyMod_Attack_Damage_Logic",
    "MyMod_Attack_Visual_Effects"
  ]
}
```

> **References resolve by basename, scoped per namespace — not by path.** `Dodge_Left` matches
> the file of that basename regardless of which subfolder it sits in (shipped, it is `Interactions/Dodge/Dodge_Left.json`). `Interactions/` and
> `RootInteractions/` are independent namespaces (the same basename may exist once in each), but within
> a namespace basenames must be unique. A custom interaction therefore just needs a unique basename in
> its namespace; the subfolder is organizational. (`Parent` is also supported on root interactions, not
> just items and plain interactions — e.g. `RootInteractions/.../Lantern_Yellow` → `Lantern_Base`.)

**Mixed format:**

```json
{
  "Type": "Serial",
  "Interactions": [
    "MyMod_Prepare_Animation",
    { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 10 } } },
    "MyMod_Cleanup_Effects"
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
- **A failed step short-circuits the rest.** `InteractionChain.updateServerState()` maps any entry state other than `NotFinished`/`Finished` onto a chain state of `Failed`, and the manager tears the chain down as soon as its state leaves `NotFinished`. So a step that ends in `InteractionState.Failed` stops the Serial — unless that step declares its own `Failed` branch, which jumps the chain to that branch's label instead of failing.

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
        { "Type": "ApplyEffect", "EffectId": "Potion_Health_Regen" }
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
      { "Type": "Simple", "Effects": { "LocalSoundEventId": "SFX_Creative_Play_Error" } }
    ]
  },
  "Next": { "1.0": "MyMod_Consume_Complete" }
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
        "MyMod_Prepare_Phase_1",
        "MyMod_Execute_Phase_1"
      ]
    },
    {
      "Type": "Serial",
      "Interactions": [
        "MyMod_Prepare_Phase_2",
        "MyMod_Execute_Phase_2"
      ]
    }
  ]
}
```

### Complete Examples

**Dodge (from `Interactions/Dodge/Dodge_Left.json`, abbreviated):**

A dodge gates on stamina, then runs its steps in order: two effects, the push, and — in Adventure only —
the stamina spend. The real asset uses the armour-discounted `StatsConditionWithModifier` /
`ChangeStatWithModifier` pair; the shape is the same with plain `StatsCondition` / `ChangeStat`
(abbreviated — the asset also sets a `VelocityConfig` on the force and resets `StaminaRegenDelay`):

```json
{
  "Type": "StatsConditionWithModifier",
  "Costs": { "Stamina": 2 },
  "InteractionModifierId": "Dodge",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyEffect", "EffectId": "Dodge_Invulnerability" },
      { "Type": "ApplyEffect", "EffectId": "Dodge_Left" },
      {
        "Type": "ApplyForce",
        "Direction": { "X": -1, "Y": 0, "Z": 0 },
        "AdjustVertical": false,
        "WaitForGround": false,
        "Force": 13,
        "ChangeVelocityType": "Set"
      },
      {
        "Type": "Condition",
        "RequiredGameMode": "Adventure",
        "Next": {
          "Type": "ChangeStatWithModifier",
          "StatModifiers": { "Stamina": -2 },
          "ValueType": "Absolute",
          "InteractionModifierId": "Dodge"
        }
      }
    ]
  },
  "Failed": "Stamina_Bar_Flash"
}
```

The condition only checks that the stamina is there (`Costs` deducts nothing); the `ChangeStat…` step
inside `Next` is what spends it.

**Consumable with Charge (from Consume_Charge.json):**

A consumable that requires holding for 4 s, then consumes the item and runs a Serial of `Replace` hooks the item fills in (`ConsumedSFX`, `Effect`):

```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Replace",
      "Var": "ConsumeSFX",
      "DefaultValue": { "Interactions": ["Consume_SFX"] }
    },
    {
      "Type": "Charging",
      "FailOnDamage": false,
      "Effects": {
        "ItemAnimationId": "Consume",
        "ClearAnimationOnFinish": true,
        "ClearSoundEventOnFinish": true
      },
      "HorizontalSpeedMultiplier": 0.75,
      "Next": {
        "4.0": {
          "Type": "ModifyInventory",
          "AdjustHeldItemQuantity": -1,
          "Next": {
            "Type": "Serial",
            "Interactions": [
              { "Type": "Replace", "Var": "ConsumedSFX", "DefaultOk": true,
                "DefaultValue": { "Interactions": ["Consumed_SFX"] } },
              { "Type": "Replace", "Var": "Effect",
                "DefaultValue": { "Interactions": ["Effect"] } },
              { "Type": "Simple", "RunTime": 0.2 }
            ]
          }
        }
      },
      "Failed": { "Type": "Simple" }
    }
  ]
}
```

**Signature Ability (from `Interactions/Weapons/Sword/Attacks/Signature/VortexStrike/Weapon_Sword_Signature_Vortexstrike.json`, verbatim):**

A `StatsCondition` checks for a full signature bar (it does not spend it — the trailing `ChangeStat`
does), then a Serial runs the spin and the stab through `Replace` hooks the item can override:

```json
{
  "Type": "StatsCondition",
  "Costs": { "SignatureEnergy": 100 },
  "ValueType": "Percent",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "Replace",
        "Var": "Vortexstrike_Spin",
        "DefaultOk": true,
        "DefaultValue": { "Interactions": ["Weapon_Sword_Signature_Vortexstrike_Spin"] }
      },
      { "Type": "Simple", "RunTime": 0.13 },
      {
        "Type": "Replace",
        "Var": "Vortexstrike_Stab",
        "DefaultOk": true,
        "DefaultValue": { "Interactions": ["Weapon_Sword_Signature_Vortexstrike_Stab"] }
      },
      {
        "Type": "ChangeStat",
        "StatModifiers": { "SignatureEnergy": -100 },
        "ValueType": "Percent"
      }
    ]
  }
}
```

**Arrow Volley (deep nesting example):**

A charged ability that fires multiple projectiles in sequence. The pause between shots lives *inside*
the forked chain, because a `Repeat`'s own `RunTime` does not pace its iterations (see the
[Repeat gotcha](#repeat)):

```json
{
  "Type": "Charging",
  "AllowIndefiniteHold": true,
  "Next": {
    "0": "MyMod_Bow_Cancel",
    "1.5": {
      "Type": "Serial",
      "Interactions": [
        {
          "Type": "Repeat",
          "Repeat": 5,
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
                    "RunTime": 0.1,
                    "Effects": {
                      "WorldSoundEventId": "SFX_Bow_T2_Shoot"
                    }
                  }
                ]
              }
            ]
          }
        },
        { "Type": "Simple", "RunTime": 0.8 }
      ]
    }
  }
}
```

### Serial vs Parallel Comparison

| Aspect | Serial | Parallel |
|--------|--------|----------|
| **Execution order** | Sequential (1 → 2 → 3) | Branch 1 runs in the chain; branches 2+ are forked and run alongside it |
| **Timing** | The chain waits for every step | The chain waits for **branch 1 only**; forks finish on their own schedule |
| **Dependencies** | Each step can depend on previous | No ordering guarantees between branches |
| **Use case** | Multi-step abilities, state changes | Multiple simultaneous effects |
| **Failure handling** | A failed step fails the chain and stops the rest (unless it has its own `Failed` branch) | Forks are independent; a failed fork does not stop the others |

**When to use Serial:**
- Stat changes that must happen before damage
- Consuming items before applying effects
- Animations that must play in sequence
- Any ordered multi-step process

**When to use Parallel:**
- Applying multiple status effects at once
- Playing multiple sounds/particles simultaneously
- Independent effects that don't need ordering

**Parallel example for reference** — note each entry is a *root* body, `{ "Interactions": [...] }`:

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Interactions": [ { "Type": "ApplyEffect", "EffectId": "Burn" } ] },
    { "Interactions": [ { "Type": "ApplyEffect", "EffectId": "Slow" } ] },
    { "Interactions": [ { "Type": "Simple", "Effects": { "LocalSoundEventId": "SFX_Flame_Ignite" } } ] }
  ]
}
```

All three start on the same tick rather than one after another.

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
        "Interactions": ["MyMod_No_Effect"]
      }
    }
  ]
}
```

Items or abilities calling this template provide their own `DamageAmount` and `EffectToApply` values.

### Related Interactions

- [Parallel](#parallel) - Execute interactions simultaneously instead of sequentially
- [Condition](#condition) - Conditional branching (often contains Serial in Next/Failed)
- [StatsCondition](#statscondition) - Stat-based branching (often contains Serial in Next/Failed)
- [Replace](#replace) - Variable substitution for templates
- [Repeat](#repeat) - Execute a Serial block multiple times

---

## Parallel

**Package:** `config/none/ParallelInteraction`

Runs several interaction roots at once. The first entry runs inside the current chain; every other entry
is **forked** into its own chain with a copy of the context. This is how damage logic and visual effects
are kept apart without one blocking the other.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Parallel"` |
| `Interactions` | array | Required | Codec doc: "The collection of interaction roots to run in parallel via forks." Validated non-null and to contain at least **two** entries |

Each entry is a **root** interaction (`RootInteraction.CHILD_ASSET_CODEC`), not a plain child interaction. Like [Serial](#serial), `ParallelInteraction` extends `Interaction` directly and so has **no `Next`/`Failed` of its own**.

### Interactions Array Format

Because each entry is a root, an entry takes one of two forms:

1. **Inline root body** — an object whose own `Interactions` array lists the steps of that branch. This is
   the form every one of the 1,001 inline entries in the shipped assets uses.
2. **String reference** — the id of a **root interaction** (a file under `RootInteractions/`), not of a
   plain interaction. The namespaces are separate, so an id that names a file under `Interactions/`
   does not resolve here.

An inline object written as a plain interaction (`{ "Type": "ApplyEffect", … }`) is **not** a root body,
and it does not fail validation either. `RootInteraction`'s `Interactions` key carries `nonNull()` and
`nonEmptyArray()`, but the field starts as an empty array, so an omitted key passes both checks (they
reject only an explicit `null` or `[]`). The entry loads as a root with nothing to run, and the plain
interaction's keys are unknown to it; the asset loader logs an unknown key as unused and carries on.

**Inline root bodies:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Interactions": [ { "Type": "ApplyEffect", "EffectId": "Burn" } ] },
    { "Interactions": [ { "Type": "ApplyEffect", "EffectId": "Slow" } ] }
  ]
}
```

**String references (from `RootInteractions/NPCs/Creature/Mammal/Bear_Voidtaken/Root_Bear_Voidtaken_Tentacle.json`):**

The two shipped string entries both name root interactions:

```json
{
  "Type": "Parallel",
  "Interactions": [
    "Root_Bear_Voidtaken_Tentacle_Impact",
    "Root_Bear_Voidtaken_Tentacle_Spawn"
  ]
}
```

### Execution Behavior

```
ParallelInteraction.tick0()
    │
    ├─► context.execute(interactions[0])   push branch 1 onto THIS chain's call stack
    │
    ├─► context.fork(context.duplicate(), interactions[1])   new chain
    │
    ├─► context.fork(context.duplicate(), interactions[2])   new chain
    │
    └─► mark the Parallel step Finished
```

- **Branch 1 is a call, not a fork.** `context.execute` pushes the root onto the current chain's call
  stack, so the chain runs branch 1 next and returns to whatever follows the `Parallel` only when branch 1
  ends. Steps after a `Parallel` therefore wait for branch 1 — and for nothing else.
- **Branches 2+ are forks.** Each runs as its own chain and is not waited on; there is no built-in join.
- **Duration.** The chain's own time is branch 1's duration. The forks may end earlier or later.
- During client simulation (`simulateTick0`) only branch 1 is run; the forks are server-side.

### Context Behavior

`InteractionContext.duplicate()` copies the context — its held-item fields and the **meta store**
(target entity, hit location, target block, …) — not the entity. Every branch still acts on the same
entities.

| Branch | Context | Notes |
|--------|---------|-------|
| First (`interactions[0]`) | The chain's own | Meta values it sets are visible to steps after the `Parallel` |
| Subsequent (forked) | A copy | Meta values set in a fork stay in that fork |

**Example implications:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    { "Interactions": [ { "Type": "ChangeStat", "StatModifiers": { "Health": -10 } } ] },
    { "Interactions": [ { "Type": "ChangeStat", "StatModifiers": { "Health": -10 } } ] }
  ]
}
```

Both branches run `ChangeStat` against the same entity (`context.getEntity()` is copied into the fork),
so it loses **20** health, not 10. What the copy isolates is meta state: a target a `Selector` picks in
one branch is not seen by the other.

### Deep Nesting Patterns

**Parallel inside Serial (common pattern):**

```json
{
  "Type": "Serial",
  "Interactions": [
    { "Type": "ChangeStat", "StatModifiers": { "Stamina": -20 } },
    {
      "Type": "Parallel",
      "Interactions": [
        "MyMod_Root_Attack_Damage_Logic",
        "MyMod_Root_Attack_Visual_Effects"
      ]
    },
    { "Type": "Simple", "Effects": { "ClearAnimationOnFinish": true } }
  ]
}
```

Stamina is spent first, then damage and visuals start together. The closing `Simple` runs when
`MyMod_Root_Attack_Damage_Logic` (branch 1) ends; the visuals fork may still be running then.

**Parallel inside `Next` (StatsCondition):**

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 50 },
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Interactions": [ { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 50 } } } ] },
      { "Interactions": [ { "Type": "ApplyEffect", "EffectId": "Poison_T1", "Entity": "Target" } ] },
      { "Interactions": [ { "Type": "Simple", "Effects": { "Particles": [ { "SystemId": "Impact_Critical" } ] } } ] }
    ]
  }
}
```

**Ability cast (from `Interactions/Abilities/Fireball/Ability_Fireball_Cast.json`, abbreviated):**

A shipped cast gates on the ability's cost, then forks the cooldown and the cost spend alongside the cast
itself. Each branch is an inline root body:

```json
{
  "Type": "StatsCondition",
  "UseAbilityCost": true,
  "Failed": "Ability_Cast_Fail",
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Interactions": [ { "Type": "Simple", "RunTime": 0.87 }, { "Type": "LaunchAbilityProjectile", "Projectile": "Projectile_Config_Ability_Fireball" } ] },
      { "Interactions": [ { "Type": "TriggerCooldown", "UseAbilityCooldown": true } ] },
      { "Interactions": [ { "Type": "ChangeStat", "UseAbilityCost": true } ] }
    ]
  }
}
```

### Complete Examples

**NPC Melee Attack Pattern (Damage + Visuals Separation):**

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Interactions": [
        { "Type": "Simple", "RunTime": 0.3 },
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
      "Interactions": [
        {
          "Type": "Simple",
          "RunTime": 0.8,
          "Effects": { "ItemAnimationId": "SwingLeft" }
        },
        {
          "Type": "Simple",
          "Effects": { "WorldSoundEventId": "SFX_Sword_T1_Swing" }
        }
      ]
    }
  ]
}
```

**Branch 1 (Damage):** waits 0.3 s (wind-up), then damages entities in a horizontal arc. It runs in the
chain, so anything after this `Parallel` waits for it.

**Branch 2 (Visuals):** a fork that plays the 0.8 s swing animation, then the sound.

**AOE Ground Slam with Effects:**

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Interactions": [
        {
          "Type": "Selector",
          "Selector": { "Id": "AOECircle", "Range": 4.0 },
          "HitEntity": {
            "Interactions": [
              {
                "Type": "DamageEntity",
                "DamageCalculator": { "BaseDamage": { "Physical": 30 } }
              },
              { "Type": "ApplyEffect", "EffectId": "Stun", "Entity": "Target" }
            ]
          }
        }
      ]
    },
    {
      "Interactions": [
        {
          "Type": "Simple",
          "Effects": {
            "WorldSoundEventId": "SFX_Ability_Ground_Slam_Impact",
            "Particles": [ { "SystemId": "Explosion_Medium" } ]
          }
        }
      ]
    }
  ]
}
```

Two branches: the damage selector (whose `HitEntity` also stuns each target) and the sound/particle
feedback.

**Variable Replacement in Parallel:**

Using [Replace](#replace) inside the branches for customizable attack templates:

```json
{
  "Type": "Parallel",
  "Interactions": [
    {
      "Interactions": [
        {
          "Type": "Replace",
          "Var": "DamageBranch",
          "DefaultOk": true,
          "DefaultValue": { "Interactions": ["MyMod_Default_Damage"] }
        }
      ]
    },
    {
      "Interactions": [
        {
          "Type": "Replace",
          "Var": "EffectsBranch",
          "DefaultOk": true,
          "DefaultValue": { "Interactions": ["MyMod_Default_Effects"] }
        }
      ]
    }
  ]
}
```

Items or abilities can provide custom `DamageBranch` and `EffectsBranch` values to inject specific behavior while sharing the parallel execution structure.

### Error Handling

| Scenario | Behavior |
|----------|----------|
| One branch fails | Other branches continue independently |
| The `Parallel` step itself | Finishes on the tick it runs, whatever the branches do |
| Steps after the `Parallel` | Wait for branch 1, not for the forks |
| Unknown root id | Caught at load by the late `RootInteraction` validator; at runtime `getRootInteractionOrUnknown` substitutes the placeholder root |

**Important:** There is no built-in synchronization point for the forks. If something must happen only
after every branch finishes, put the work in branch 1 or restructure the chain with `Serial`.

### Common Patterns

| Pattern | Description | Example Use |
|---------|-------------|-------------|
| **Damage + Visuals separation** | One branch for damage logic, another for effects | NPC attacks, weapon abilities |
| **Multiple status effects** | Apply several effects at once | Elemental weapons, potions |
| **AOE with feedback** | Damage selector + particles + sound | Ground slams, explosions |
| **Template branches** | Replace variables for customizable forks | Reusable attack templates |
| **Ability bookkeeping** | Cooldown and cost run as forks beside the cast | The shipped `Ability_*_Cast` chains |

### When to Use Parallel vs Serial

| Aspect | Serial | Parallel |
|--------|--------|----------|
| **Execution order** | Sequential (1 → 2 → 3) | Branch 1 in the chain, branches 2+ forked |
| **Timing** | The chain waits for every step | The chain waits for branch 1 only |
| **Dependencies** | Each step can depend on previous | No ordering guarantees |
| **Context** | One context throughout | Branch 1 shares the chain's; forks get copies |
| **Use case** | Multi-step abilities, state changes | Multiple simultaneous effects |
| **Failure handling** | A failed step fails the chain and stops the rest (unless it has its own `Failed` branch) | Forks are independent; a failed fork does not stop the others |

**When to use Parallel:**
- Applying multiple status effects at once
- Separating damage logic from visual effects
- Playing multiple sounds/particles simultaneously
- Independent effects that don't need ordering

**When to use Serial:**
- Stat changes that must happen before damage
- Consuming items before applying effects
- Animations that must play in sequence
- Any ordered multi-step process
- When later steps must see meta values (such as a selected target) set by earlier ones

### Related Interactions

- [Serial](#serial) - Execute interactions sequentially instead of concurrently
- [Condition](#condition) - Conditional branching (can contain Parallel in Next/Failed)
- [StatsCondition](#statscondition) - Stat-based branching (can contain Parallel in Next/Failed)
- [Replace](#replace) - Variable substitution for template branches
- [Repeat](#repeat) - Execute interactions multiple times (can wrap Parallel)

---

## Condition

**Package:** `config/none/ConditionInteraction`

The base Condition interaction provides branching based on game mode and entity movement states (jumping, swimming, crouching, running, flying, gliding). It evaluates the current state of an entity and branches to either `Next` (condition passed) or `Failed` (condition did not pass).

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Condition"` |
| `RequiredGameMode` | string | `null` | Game mode that must be active (`Adventure` or `Creative` — the `GameMode` enum has no other members). Only checked when the entity actually has a `Player` component: an NPC or block chain passes this check unconditionally |
| `Jumping` | boolean | `null` | If set, entity must be/not be jumping |
| `Swimming` | boolean | `null` | If set, entity must be/not be swimming |
| `Crouching` | boolean | `null` | If set, entity must be/not be crouching |
| `Running` | boolean | `null` | If set, entity must be/not be running (sprinting) |
| `Flying` | boolean | `null` | If set, entity must be/not be flying |
| `Gliding` | boolean | `null` | If set, entity must be/not be gliding (0.7.2+; read from `MovementStates.gliding`) |
| `Next` | interaction | `null` | Interaction to execute when condition passes |
| `Failed` | interaction | `null` | Interaction to execute when condition fails |

### Branching Behavior

Like every condition on this page, Condition branches through `Next`/`Failed` (no interaction codec has a `Then`/`Else` key):

- **Next**: Executed when ALL specified conditions are met
- **Failed**: Executed when ANY specified condition is not met
- Unset properties (`null`) are not checked - only explicitly set conditions are evaluated
- The checks read the **owning** entity of the chain (`InteractionContext.getOwningEntity()`), not the executor, and every check is evaluated before the verdict is applied (there is no early exit — the outcome is the same either way)

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
    ├─► Check Gliding (if set)
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
    "PrefabPath": "Example_Portal1.prefab.json"
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
  "Failed": "MyMod_Ground_Attack_Normal"
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
    "EffectId": "Potion_Stamina_Regen"
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
        "Effects": { "WorldSoundEventId": "SFX_Mace_T1_Impact" }
      }
    ]
  },
  "Failed": "MyMod_Attack_Normal"
}
```

**Glider durability (from `Item/Items/Glider/Template_Glider.json`, abbreviated):**

The shipped glider uses the 0.7.2 `Gliding` key to charge durability only for a glide that is just
starting, not for one being cancelled:

```json
{
  "Type": "Condition",
  "RequiredGameMode": "Adventure",
  "Swimming": false,
  "Gliding": false,
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1
  }
}
```

**Multiple Conditions:**

All specified conditions must be true:

```json
{
  "Type": "Condition",
  "RequiredGameMode": "Adventure",
  "Running": true,
  "Jumping": false,
  "Next": "MyMod_Sprint_Slide_Start",
  "Failed": "MyMod_Movement_Normal"
}
```

This checks: Adventure mode AND sprinting AND NOT jumping.

### Related Interactions

- [StatsCondition](#statscondition) - Branch based on stat values
- [EffectCondition](#effectcondition) - Branch based on active effects
- [MovementCondition](#movementcondition) - Branch based on movement direction input

---

## StatsCondition

**Package:** `config/none/StatsConditionInteraction`

Branch based on whether an entity's stats meet a set of thresholds. Each entry in the `Costs` map names a stat and the amount required; when every listed stat is at or above its amount the interaction branches to `Next`, otherwise to `Failed`. It is a **pure check** — nothing is deducted (pair it with [ChangeStat](interactions-combat.md#changestat) to spend the resource, as the shipped `Weapon_Sword_Signature_Vortexstrike.json` does). Essential for resource gating (stamina, signature energy) and stat-based ability variations.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"StatsCondition"` |
| `Costs` | object | — | Map of stat name to threshold amount; passes when every listed stat is ≥ its amount (nothing is deducted). Keys are validated against the loaded `EntityStatType` assets, so a typo fails asset validation at load. **Not required since 0.7.2** (it carried `Validators.nonNull()` through 0.6.8), but with neither `Costs` nor `UseAbilityCost` the condition always fails |
| `LessThan` | boolean | `false` | Invert the comparison: pass when every listed stat is **below** its amount |
| `ValueType` | string | `"Absolute"` | How to interpret the amounts (`Absolute` or `Percent`) |
| `Lenient` | boolean | `false` | Allow overdraw: a stat below its amount still passes as long as it is above zero and the stat's minimum is negative |
| `UseAbilityCost` | boolean | `false` | 0.7.2+. Test the casting ability's own `Cost` / `CostType` instead of `Costs` — see [Ability Costs](#ability-costs). `StatsCondition` only; `StatsConditionWithModifier` does not declare it |
| `Next` | interaction | `null` | Interaction when all thresholds are met |
| `Failed` | interaction | `null` | Interaction when any threshold is not met (or a listed stat is missing on the entity) |

### ValueType Reference

| ValueType | Description |
|-----------|-------------|
| `Absolute` | Cost amounts are raw stat values |
| `Percent` | Cost amounts are a percentage of the stat's maximum on a 0-100 scale (the code compares against `stat.asPercentage() * 100`) |

The stats are read from the **executing** entity (`InteractionContext.getEntity()`), unlike [Condition](#condition), which reads the chain's owning entity.

### Lenient Mode

When `Lenient` is `true`, a stat that is *below* its amount still passes provided its current value is above zero and the stat's configured minimum is negative (i.e. the stat may be overdrawn into negative territory by the follow-up `ChangeStat`). A stat that does not exist on the entity always fails, lenient or not.

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 10 },
  "Lenient": true,
  "Next": "MyMod_Execute_Ability",
  "Failed": "MyMod_Out_Of_Stamina"
}
```

With 4 stamina left this still runs `Next` (4 > 0) if the Stamina stat's minimum is below zero.

### Ability Costs

The 0.7.2 ability system declares a cost on the ability item itself, and `"UseAbilityCost": true` makes
a `StatsCondition` read it: `AbilityCastUtil.resolveCostMap` builds a one-entry cost map from the ability's
`CostType` (the stat) and `Cost`, scaled by the cast's `Cost` attribute when the cast carries modifiers. Eight of the nine
shipped `*_Cast.json` ability chains open this way (`Ability_GroundSlam_Cast` puts a `GroundedCondition` first) (see the ability-cast example under [Parallel](#parallel)).

The condition **passes without checking anything** whenever no cost resolves: outside an ability cast
(the chain must run from the ability slot), for an ability whose `Cost` is ≤ 0 or whose `CostType` is
`None`, for a stat id that does not exist, and for a player in Creative. The codec says the same for the
first case — "An ability without a cost passes." The spend is a separate `ChangeStat` with the same flag.

### Common Stats

| Stat | Description |
|------|-------------|
| `Health` | Current health points |
| `Stamina` | Current stamina points |
| `SignatureEnergy` | Signature ability charge |
| `StaminaRegenDelay` | Delay before stamina begins regenerating |

### Examples

**Stamina Gate (from `Interactions/Weapons/Sword/Attacks/Primary/Thrust/Weapon_Sword_Primary_Thrust_StaminaCondition.json`, verbatim):**

At least 0.1 stamina lets the thrust through; with less, the chain falls back to the ordinary combo.
`Costs` only checks — the `ChangeStat` in `Next` sets `StaminaRegenDelay` rather than spending stamina:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 0.1 },
  "Failed": "Weapon_Sword_Primary_Chain",
  "Next": {
    "Type": "ChangeStat",
    "Behaviour": "Set",
    "StatModifiers": { "StaminaRegenDelay": -2 },
    "Next": {
      "Type": "Replace",
      "Var": "Thrust",
      "DefaultOk": true,
      "DefaultValue": { "Interactions": ["Weapon_Sword_Primary_Thrust"] }
    }
  }
}
```

**Below-maximum check (from `Interactions/Consumables/Stat_Check.json`, verbatim):**

`LessThan` with a `Percent` cost of `100` means "not at full health". Items such as
`Food_Candy_Cane` inherit it through a `Stat_Check` interaction var (`"Parent": "Stat_Check"`) and
override `Costs`:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Health": 100 },
  "ValueType": "Percent",
  "LessThan": true,
  "Next": "Consume_Charge"
}
```

**Signature Energy Threshold:**

```json
{
  "Type": "StatsCondition",
  "Costs": { "SignatureEnergy": 100 },
  "Next": "MyMod_Signature_Ability_Execute",
  "Failed": {
    "Type": "Simple",
    "Effects": { "LocalSoundEventId": "SFX_Creative_Play_Error" }
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
  "Next": "MyMod_Apply_Blood_Magic",
  "Failed": "MyMod_Apply_Normal_Effect"
}
```

**Nested Cost Checks:**

Multiple resource requirements, each checked in turn:

```json
{
  "Type": "StatsCondition",
  "Costs": { "Stamina": 50 },
  "Next": {
    "Type": "StatsCondition",
    "Costs": { "SignatureEnergy": 30 },
    "Next": "MyMod_Hybrid_Ability_Execute",
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
| `Entity` | string | `"User"` | Which entity to check: `"User"`, `"Owner"`, or `"Target"` |
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
| `Owner` | Check the entity that owns the interaction chain (differs from `User` when a chain runs on behalf of another entity) |
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

> **Gotcha — a missing target passes.** If the resolved `Entity` reference is invalid, or the entity
> has no `EffectControllerComponent`, `firstRun` returns without touching the state, so the
> interaction **succeeds** and `Next` runs. An `EffectCondition` is therefore not a reliable
> "this entity exists and is affected" guard; only its `None` sense is safe by default.

### Examples

**Single Effect Check:**

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["Burn"],
  "Entity": "Target",
  "Next": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 30 } }
  },
  "Failed": {
    "Type": "ApplyEffect",
    "EffectId": "Burn"
  }
}
```

If the target is burning, deal bonus damage. Otherwise, ignite it.

**Multiple Effects Check (All):**

Combo system requiring multiple debuffs:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["Burn", "Poison", "Freeze"],
  "Match": "All",
  "Entity": "Target",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 100 } }
      },
      { "Type": "ClearEntityEffect", "Entity": "Target", "EntityEffectId": "Burn" },
      { "Type": "ClearEntityEffect", "Entity": "Target", "EntityEffectId": "Poison" },
      { "Type": "ClearEntityEffect", "Entity": "Target", "EntityEffectId": "Freeze" },
      { "Type": "Simple", "Effects": { "Particles": [ { "SystemId": "Impact_Critical" } ] } }
    ]
  },
  "Failed": "MyMod_Normal_Attack"
}
```

**Immunity Check (None, from `Interactions/Stamina_Broken_Check.json`, verbatim):**

Prevent applying an effect while its immunity effect is active:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["Stamina_Broken_Immune"],
  "Match": "None",
  "Next": {
    "Type": "ApplyEffect",
    "EffectId": "Stamina_Broken"
  }
}
```

`Entity` is omitted, so the check runs against the `User`; `Stamina_Broken` is only applied when the user does not carry `Stamina_Broken_Immune`.

**Tiered Buff System (illustrative nested `None` checks):**

Check for food buff tiers:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["FruitVeggie_Buff_T3"],
  "Match": "None",
  "Entity": "User",
  "Next": {
    "Type": "EffectCondition",
    "EntityEffectIds": ["FruitVeggie_Buff_T2"],
    "Match": "None",
    "Entity": "User",
    "Next": {
      "Type": "EffectCondition",
      "EntityEffectIds": ["FruitVeggie_Buff_T1"],
      "Match": "None",
      "Entity": "User",
      "Next": "MyMod_Apply_Tier1_Buff",
      "Failed": "MyMod_Upgrade_To_Tier2"
    },
    "Failed": "MyMod_Upgrade_To_Tier3"
  },
  "Failed": "MyMod_Refresh_Tier3"
}
```

**Self-Buff Check:**

Only allow ability if not already buffed:

```json
{
  "Type": "EffectCondition",
  "EntityEffectIds": ["Ability_Enrage_Buff"],
  "Match": "None",
  "Entity": "User",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      { "Type": "ApplyEffect", "EffectId": "Ability_Enrage_Buff" },
      { "Type": "Simple", "Effects": { "ItemAnimationId": "Stomp" } }
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
  "EntityEffectIds": ["Freeze"],
  "Match": "All",
  "Entity": "Target",
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Interactions": [ { "Type": "DamageEntity", "DamageCalculator": { "BaseDamage": { "Physical": 40 } } } ] },
      { "Interactions": [ { "Type": "ApplyEffect", "EffectId": "Stun", "Entity": "Target" } ] }
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
| `Matchers` | array | — | List of `BlockMatcher` objects. The codec does not require it, but `doInteraction` loops over it with no null check, so leaving it out throws at runtime — always write it |
| `Next` | interaction | `null` | Interaction when any matcher succeeds |
| `Failed` | interaction | `null` | Interaction when all matchers fail |

### BlockMatcher Structure

Each `BlockMatcher` in the array nests block identity in a `Block` object, with optional face siblings:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Block` | object | — | Codec doc: "Match against block values" — `{ "Id": ..., "State": ..., "Tag": ... }`. Optional: a matcher without `Block` matches any block that passes its `Face` test |
| `Block.Id` | string | `null` | Block ID to match. **Compared against the block's *item* id** (`blockType.getItem().getId()`), so a state variant such as the blue lantern still matches its base id `Furniture_Human_Ruins_Lantern`. Validated against the loaded `BlockType` assets |
| `Block.State` | string | `null` | Block state name to match; a block with no state reads as `"default"` |
| `Block.Tag` | string | `null` | Block tag to match (any block type carrying the tag in its `Data.Tags`) |
| `Face` | string | `"None"` | Which face of the target block the player must have hit for the matcher to apply. `None` skips the face test |
| `StaticFace` | boolean | `false` | Codec doc: "Whether the face matching is unaffected by the block rotation or not." |

### Face Reference

`Face` is a `BlockFace` (the same enum block-type configs use); the matcher only applies when the face the player clicked equals it (after the `StaticFace` transform). A matcher whose `Block` matches but whose `Face` does not is skipped.

| Face | Description |
|------|-------------|
| `None` | Ignore the clicked face; match on the block alone |
| `Up` / `Down` | Top / bottom face |
| `North` / `South` / `East` / `West` | Side faces |

### StaticFace Behavior

| StaticFace | Behavior |
|------------|----------|
| `false` (default) | `Face` is rotated by the **target block's own** yaw and pitch (`BlockSection.getRotation(...)`) before being compared with the clicked face — so `Up` means "the face that is 'up' in the block's local frame". It is **not** the player's rotation |
| `true` | `Face` is compared as an absolute world face, ignoring the block's rotation |

> **Gotcha (0.6.3) — a non-default Creative place mode makes every matcher fail.** After a matcher
> succeeds, `BlockConditionInteraction` re-checks the executor: if it is a player in Creative whose
> `PlayerSettings.creativeSettings().placeMode()` is anything other than `Default`, the match is
> discarded and the interaction ends `Failed`. `PlaceMode` (`Default`, `Replace`, `Retype`,
> `Extrude`, `SurfaceDraw`, `FastPlace`) is new in 0.6.3 and is what the `PlaceModeSelect` /
> `DragPlaceBlock` / `ExtrudePlaceBlock` / `SurfaceDrawPlaceBlock` interactions switch between, so a
> block whose `Use` chain starts with a `BlockCondition` silently stops responding while a builder
> has one of those modes selected.

### Examples

**Specific Block ID Check (from `Interactions/Block/Lantern/Lantern_Yellow.json`):**

Only act when the target block is a specific lantern, then change its state (`Changes` abbreviated — the asset maps every colour state to `Yellow`):

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

Check that the clicked block is stone in its `default` state and was hit on its `Up` face before changing it to the full-block state:

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
    "RequireBlockPlacement": true,
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
    { "Block": { "Id": "Soil_Dirt_Tilled" } },
    { "Block": { "Id": "Soil_Grass" } },
    { "Block": { "Id": "Soil_Dirt" } }
  ],
  "Next": "MyMod_Plant_Seed",
  "Failed": {
    "Type": "SendMessage",
    "Message": "Cannot plant here!"
  }
}
```

The shipped seeds use the same shape: `Interactions/Crops/Seed_Condition.json` matches `Soil_Dirt_Tilled`
or a block tagged `SubType=Planter` on its `Up` face, and its `Next` is a `Replace` on the `SeedId`
variable whose `DefaultValue` is the shipped `Seed_Place` interaction. A seed item supplies its own
`SeedId`: `Plant_Seeds_Carrot` sets it to an interaction with `"Parent": "Seed_Place"` and
`"BlockTypeToPlace": "Plant_Crop_Carrot_Block"`, so one condition serves every crop.

### Related Interactions

- [PlacementCountCondition](#placementcountcondition) - Check block placement limits
- [Block Interactions](interactions-world.md#block-interactions) - Break or place blocks

---

## AugmentCondition

**Package:** `com.hypixel.hytale.builtin.augmentblocks.AugmentConditionInteraction`

Passes while every named augment tag is granted by augment blocks around the **target block**. Codec
doc: "An interaction that is successful while every required tag is granted by augment blocks around
the target block." Extends [SimpleInstantInteraction](interactions.md#simpleinstantinteraction), and
registered by `AugmentBlocksPlugin` rather than `InteractionModule`, so it exists only when that
plugin is loaded.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `RequiredAugmentTags` | string[] | — | Every tag listed must be granted by an augment block in range. Carries `Validators.nonNull()`, but the field starts as an empty array, so an omitted key passes and behaves as `[]` (see the gotcha below) |
| `Radius` | double | `100.0` | Sphere radius, centred on the target block, within which augment blocks are collected |

This is the interaction-side twin of the bench mechanism: the tags come from `AugmentBlock`
block-entity components (`GrantsAugmentTags`, see
[items-blocks.md](items-blocks.md#block-entity-components)), the same source a crafting recipe's
`RequiredAugmentTags` reads through
[BenchRequirement](items-crafting.md#benchrequirement).

0.7.2 ships its first uses: **14** `AugmentCondition`s across **7** Goblin Lab puzzle blocks under
`Server/Item/Items/Puzzles/Goblins/Lab/`, every one requiring the single tag `goblin_lab_power` and every one
writing both `Next` and `Failed`. Only `GoblinLab_Teleporter.json` sets `Radius` (to `200`); the rest take the
default. Its `Use` chain, abbreviated (the shipped `Next` continues past the page, and its `Failed`
opens a message page):

```json
{
  "Type": "AugmentCondition",
  "RequiredAugmentTags": [ "goblin_lab_power" ],
  "Radius": 200,
  "Next": {
    "Type": "OpenCustomUI",
    "Page": { "Id": "AugmentUpgrade" }
  }
}
```

- **It needs a target block.** With no `targetBlock` in the context the check returns false and the
  interaction ends `Failed`, so this is a block-targeting condition even though it is an *instant*
  interaction rather than a block one.
- **`Radius` defaults to 100 blocks**, which is not a neighbourhood — it is effectively "anywhere in
  the loaded area". Set it deliberately.

> **Gotcha — an empty or omitted array passes wherever there is a target block.** The key carries
> `Validators.nonNull()`, yet its field starts as an empty array, so omitting it passes load exactly
> as `[]` does, and `AugmentBlocksUtils.requirementsMet` returns true immediately when the array is
> empty, before collecting anything. So a condition with an empty or absent `RequiredAugmentTags`
> passes on every targeted block, and it looks exactly like a configured condition. It is not unconditional, though: with no target block at all
> the check fails first, and nothing structurally supplies one — see the bullet above. The bench side behaves
> the same way — [items-crafting.md](items-crafting.md#benchrequirement) records that an empty or
> absent array always passes — so this is the subsystem's convention rather than a slip here.

---

## CooldownCondition

**Package:** `config/client/CooldownConditionInteraction`

Branch based on whether a cooldown has completed. Checks if the specified cooldown timer has elapsed, allowing time-gated abilities and rate limiting.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"CooldownCondition"` |
| `Id` | string | Required | Codec doc: "The ID of the cooldown to check for in this condition." Validated non-null |
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

One case skips the check: when the executing entity has **no** `Player` component **and** the interaction has a client state, the condition copies the client's state instead of evaluating the cooldown. Everything else consults the server-side `CooldownHandler` — players, and NPCs running server-side chains with no client state, which is how the two NPC examples below work.

### Examples

**NPC Poison Attack (from `Server/NPC/Roles/Creature/Vermin/Spider.json`, `_InteractionVars.Bite_Damage`; simplified):**

Check if the poison cooldown has elapsed before applying the poison effect (the real asset applies `Poison_T1` to the `Target` via an `EffectCondition` that skips targets with `Antidote`):

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
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 23 } },
        "Next": {
          "Type": "ApplyEffect",
          "Entity": "Target",
          "EffectId": "Poison_T1"
        }
      }
    ]
  },
  "Failed": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 23 } }
  }
}
```

**Boss Poison Bite (from `Server/NPC/Roles/Creature/Mythic/Snapdragon.json`, `_InteractionVars.Melee_Damage`; simplified):**

Same shape with a shorter cooldown and a stronger poison tier:

```json
{
  "Type": "CooldownCondition",
  "Id": "Snapdragon_Poison",
  "Next": {
    "Type": "Serial",
    "Interactions": [
      {
        "Type": "TriggerCooldown",
        "Cooldown": {
          "Id": "Snapdragon_Poison",
          "Cooldown": 5
        }
      },
      {
        "Type": "DamageEntity",
        "DamageCalculator": { "BaseDamage": { "Physical": 27 } },
        "Next": { "Type": "ApplyEffect", "Entity": "Target", "EffectId": "Poison_T3" }
      }
    ]
  },
  "Failed": {
    "Type": "DamageEntity",
    "DamageCalculator": { "BaseDamage": { "Physical": 27 } }
  }
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

Start a cooldown: the named cooldown's remaining time is set to its full duration and one charge is
spent. Used to initiate time-gated abilities that can later be checked with
[CooldownCondition](#cooldowncondition). Codec doc: "Triggers the cooldown as if it was triggered
normally."

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"TriggerCooldown"` |
| `Cooldown` | object | *the root's cooldown* | [InteractionCooldown](#interactioncooldown-configuration) configuration. Optional — codec doc: "The cooldown concerning this interaction, defaulting to the root cooldown if none presented" |
| `UseAbilityCooldown` | boolean | `false` | 0.7.2+. Take the id and duration from the casting ability instead — see below |

**How the id and duration resolve.** When `Cooldown` carries no `Id` (or is absent), the id comes from
the chain's **initial root interaction**: its own `Cooldown.Id` if it has one, otherwise the root
interaction's asset id. The duration is the first of: a positive `Cooldown.Cooldown` here; the
duration of the cooldown currently stored under that id (`CooldownHandler.tick` drops an entry once its
time has run out and its charges are full); a positive root `Cooldown.Cooldown`, when the id itself came from the
root; and finally `0.35` s. The charge list resolves the same way, ending at a single instant charge
(`InteractionManager.DEFAULT_CHARGE_TIMES`, `{0.0}`).

**`UseAbilityCooldown` (0.7.2+).** Codec doc: "Arm the casting ability's declared Cooldown, keyed by its
Cast root, so the ability item stays the single source (and Parallel pseudo-roots cannot mis-key the
id). Only meaningful in ability cast chains." When the chain is an ability cast, the id becomes the
ability's cast-root id and a positive ability cooldown replaces the duration, scaled by the cast's
`Cooldown` attribute when the cast carries modifiers. Outside a cast the flag does nothing and the
resolution above applies. Of the 19 shipped `TriggerCooldown` objects, 12 (in the `Abilities/` cast and charged-shot chains) write
`{ "Type": "TriggerCooldown", "UseAbilityCooldown": true }` with no `Cooldown` object at all (see the ability-cast example under
[Parallel](#parallel)); the other 7 name a `Cooldown` with an `Id` and a duration (two potions, the fire trap, the charged-shot release and three NPC poison cooldowns), and none lists `Charges`.

> **On an NPC's manager.** The manager has no remote client, so `firstRun` runs in both passes and each one spends a charge. With the default single charge the second spend finds none and the result is the same as once, which is what every shipped object gets; a cooldown whose `Charges` lists three entries used two of them (measured, one use). See [the double run](interactions-double-run.md#what-each-of-the-48-types-does).

### InteractionCooldown Configuration

The `Cooldown` property uses the InteractionCooldown configuration object:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Id` | string | `null` | Codec doc: "The Id for the cooldown. Cooldowns can be used on different interactions but share a cooldown." |
| `Cooldown` | float | `0` | "The time in seconds this cooldown should last for." Validated ≥ 0 |
| `Charges` | float[] | `null` | "The charge times available for this interaction." Each entry validated ≥ 0 |
| `SkipCooldownReset` | boolean | `false` | "Determines whether resetting cooldown should be skipped." |
| `InterruptRecharge` | boolean | `false` | "Determines whether recharge is interrupted by use." |
| `ClickBypass` | boolean | `false` | "Whether this cooldown can be bypassed by clicking." |

The same object is built by `RootInteraction.COOLDOWN_CODEC`, which is why it appears verbatim under a root interaction's `Cooldown` and under `Settings.<GameMode>.Cooldown` as well as inside `TriggerCooldown` / `ResetCooldown`.

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

**NPC Attack Cooldown (from `Server/NPC/Roles/Creature/Vermin/Spider.json`):**

```json
{
  "Type": "TriggerCooldown",
  "Cooldown": {
    "Id": "Spider_Poison",
    "Cooldown": 8
  }
}
```

**Cooldown with Click Bypass (from `RootInteractions/Tools/Watering_Can_Use.json`):**

The same `InteractionCooldown` object is used by root interactions' `Cooldown` (top-level or per game mode under `Settings`); `ClickBypass` lets a fresh click skip the remaining wait:

```json
{
  "Settings": {
    "Creative": {
      "Cooldown": {
        "Id": "BlockInteraction_Creative",
        "Cooldown": 0.01,
        "ClickBypass": true
      }
    }
  },
  "Interactions": [ "..." ]
}
```

**Cooldown without Id:**

Not anonymous: with no `Id`, the cooldown is keyed by the chain's initial root interaction — its
`Cooldown.Id` if it declares one, otherwise the root's own asset id — so a `CooldownCondition` can test
it under that id:

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
      "MyMod_Execute_Ability"
    ]
  },
  "Failed": "MyMod_Ability_NotReady_Feedback"
}
```

### Related Interactions

- [CooldownCondition](#cooldowncondition) - Check if cooldown has elapsed
- [ResetCooldown](#resetcooldown) - Reset a cooldown timer

---

## ResetCooldown

**Package:** `config/client/ResetCooldownInteraction`

**Restarts** a cooldown: its remaining time is set back to its full duration and all of its charges are
refilled. Codec doc: "Resets the cooldown." It does **not** clear the cooldown — "reset" means the timer
starts over, so straight after a `ResetCooldown` the cooldown is *active*, and a
[CooldownCondition](#cooldowncondition) on it takes `Failed`. To make an ability usable again sooner, give
it a shorter `Cooldown` here: the value replaces the stored duration before the restart.

`CooldownHandler.Cooldown.resetCooldown()` sets `remainingCooldown = cooldownMax` and `resetCharges()`
sets the charge count to the length of the charge list. The id and duration resolve exactly as for
[TriggerCooldown](#triggercooldown), including the fallback to the chain's root. The difference from
`TriggerCooldown` is the charges: `TriggerCooldown` spends one, `ResetCooldown` refills them all.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"ResetCooldown"` |
| `Cooldown` | object | *the root's cooldown* | [InteractionCooldown](#interactioncooldown-configuration) configuration. Optional — codec doc: "The cooldown concerning this interaction, defaulting to the root cooldown if none presented" |

### Examples

**Restart with a shorter duration (from Debug_Stick_Parry.json, abbreviated):**

A successful block (the `Wielding` interaction's `BlockedInteractions`) counter-attacks and then restarts
the `Debug_Stick_Parry` cooldown with its duration set to 0.5 s and its charges refilled:

```json
{
  "Type": "Wielding",
  "RunTime": 5,
  "FailOnDamage": true,
  "DamageModifiers": { "Physical": 0 },
  "BlockedInteractions": {
    "Interactions": [
      "Stick_Attack",
      {
        "Type": "ResetCooldown",
        "Cooldown": {
          "Id": "Debug_Stick_Parry",
          "Cooldown": 0.5
        }
      }
    ]
  }
}
```

(The shipped file runs the counter-attack inside a `Parallel` with a push-back force; the order of the
two steps is the same.)

**Restart the root's cooldown (from `Interactions/Weapons/Bomb/Bomb_Throw.json`):**

No `Id`, so the cooldown is the throw's root cooldown, restarted at 1 s:

```json
{
  "Type": "ResetCooldown",
  "Cooldown": {
    "Cooldown": 1
  }
}
```

The same shape appears in `Bomb_Throw_Popberry.json`, `Bomb_Throw_Stun.json` and `Bangstick_Throw.json`; with
the parry above, those five files are every shipped use of the type.

### Related Interactions

- [CooldownCondition](#cooldowncondition) - Check if cooldown has elapsed
- [TriggerCooldown](#triggercooldown) - Start a cooldown timer
- [IncrementCooldown](#incrementcooldown) - Adjust a running cooldown's time or charges

---

## IncrementCooldown

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.IncrementCooldownInteraction`

Adjusts a cooldown that is already running, rather than starting or clearing one — the fourth member
of the cooldown group alongside [CooldownCondition](#cooldowncondition),
[TriggerCooldown](#triggercooldown) and [ResetCooldown](#resetcooldown). Codec doc: "Increase the
given cooldown." Extends [SimpleInstantInteraction](interactions.md#simpleinstantinteraction).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Id` | string | *the chain's root cooldown* | Which cooldown to adjust. Omit it and the id comes from the root interaction's own `Cooldown` block |
| `Time` | float | `0` | Seconds added to the cooldown's remaining time |
| `Charge` | int | `0` | Number of spent charges to replenish |
| `ChargeTime` | float | `0` | Seconds added to the wait for the next charge. Negated at decode — see below for why, and for the two cases where it does nothing |
| `InterruptRecharge` | boolean | `false` | Passed to the charge replenish, deciding whether an in-progress recharge is interrupted |

**None of the five is required**, and each of the three numeric ones is skipped when it is zero, so
an `IncrementCooldown` with no properties resolves a cooldown id and then does nothing to it. No
shipped asset uses this type.

- **The cooldown must already exist.** `processCooldown` looks the id up on the `CooldownHandler`
  and returns silently when there is none, so this cannot be used to create one — pair it with
  [TriggerCooldown](#triggercooldown), which does.
- **The interaction always finishes.** `firstRun` sets `InteractionState.Finished` unconditionally,
  before and regardless of whether the cooldown was found, so a `Failed` branch never fires here
  even when nothing happened.
- It also generates a client packet carrying all five values — including the already-negated
  `chargeTime`, so client and server agree and the negation is not a desync.

**Why `ChargeTime` is negated at decode.** The codec's `afterDecode` runs
`chargeTime = -chargeTime` before the value is ever used, which looks like a sign bug and is not.
The two timers in `CooldownHandler.Cooldown` run in opposite directions: `remainingCooldown` counts
*down* (`remainingCooldown -= dt`), while `chargeTimer` counts *up* as elapsed progress
(`chargeTimer += dt`, and a charge is granted when it reaches the current `charges[chargeCount]`).
`ChargeTime` is expressed the way the key reads — seconds added to the **wait** — so it has to be
subtracted from progress to lengthen that wait. `"ChargeTime": 2` therefore pushes the next charge
*two seconds further away*, which is what the codec's description ("The amount of time to increase
the current charge time by") means. `Time` and `Charge` are not negated; the inversion exists only
because `chargeTime` and the field it feeds measure opposite things.

> **Gotcha — `ChargeTime` does nothing at all on most cooldowns.** `increaseChargeTime` returns
> immediately when the cooldown is already at maximum charges, and again when the cooldown defines
> one charge or fewer. A cooldown without a real multi-charge configuration therefore ignores the
> key completely — no error, no log, and the interaction still reports `Finished`. Since
> `IncrementCooldown` has no shipped uses and no shipped asset writes `ChargeTime` at all, there is
> no working example to compare against: check the target cooldown's charge list before assuming
> the key does anything.

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
| `Failed` | interaction | `null` | From `SimpleInteraction`, but here it is the **`MovementDirection.None` branch** — it runs when the player is not moving, not when something failed |

> **Gotcha — an undefined direction runs nothing, not `Failed`.** `compile()` emits one label per
> `MovementDirection` (plus label 0 for `None` ← `Failed`) and `tick0` jumps straight to the label for
> the reported direction, always with state `Finished`. A direction key you left out compiles to an
> empty body followed by a jump to the end, so moving that way silently does nothing. `Failed` only
> covers standing still. During client-side simulation the direction is forced to `None`, so the
> `Failed` branch is what the client predicts.

### Direction Detection

Directions come from the client-reported `MovementDirection` on the interaction's client state
(`WaitForDataFrom.Client`), one of nine values — `None` plus the eight below:

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

1. Reads the client-reported `MovementDirection`
2. Jumps to that direction's compiled label (state is always set to `Finished`)
3. Executes that branch's interaction, then jumps to the end of the `MovementCondition`
4. `MovementDirection.None` (standing still) takes the `Failed` label; a direction with no key defined executes an empty branch

### Examples

**Shipped dodge (from `Interactions/Dodge.json`, verbatim):**

The real dodge refuses while flying, then routes only the two pure sideways directions to a dodge. The
four diagonals are given an empty `Simple`, so they finish without doing anything; `Forward`, `Back` and
standing still (`Failed`) are left out, which does nothing either:

```json
{
  "Type": "Condition",
  "Flying": false,
  "Next": {
    "Type": "MovementCondition",
    "ForwardLeft": { "Type": "Simple" },
    "ForwardRight": { "Type": "Simple" },
    "Left": "Dodge_Left",
    "Right": "Dodge_Right",
    "BackLeft": { "Type": "Simple" },
    "BackRight": { "Type": "Simple" }
  }
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
  "Left": "MyMod_Slash_Left",
  "Right": "MyMod_Slash_Right",
  "Failed": "MyMod_Slash_Neutral"
}
```

**Simple Four-Direction Dodge:**

Only handle cardinal directions. Note the diagonals are **not** routed to `Failed` — leaving them out means a diagonal dodge does nothing at all; `Failed` fires only when the player is standing still:

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
      { "Type": "ApplyEffect", "EffectId": "Dodge_Invulnerability" }
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
      { "Type": "ApplyEffect", "EffectId": "Dodge_Invulnerability" }
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
      { "Type": "ApplyEffect", "EffectId": "Dodge_Invulnerability" }
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
      { "Type": "ApplyEffect", "EffectId": "Dodge_Invulnerability" }
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
    "Forward": "MyMod_Lunge_Attack",
    "Back": "MyMod_Retreating_Slash",
    "Left": "MyMod_Sidestep_Left_Attack",
    "Right": "MyMod_Sidestep_Right_Attack",
    "Failed": "MyMod_Standing_Attack"
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

Server-side condition that checks how many blocks of a specific type are currently placed in the world (per world, not per player — the count lives in the world's `BlockCounter` resource). Used to enforce placement limits for special blocks like teleporters. By default the condition passes when the count is less than the threshold value.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"PlacementCountCondition"` |
| `Block` | string | Required | Block ID to count (without namespace prefix) |
| `Value` | int | `0` | Threshold value - condition passes when count < this value |
| `LessThan` | boolean | `true` | Comparison direction: `true` passes when count < `Value`; `false` passes when count > `Value` |
| `Next` | interaction | `null` | Interaction when the comparison holds (condition passes) |
| `Failed` | interaction | `null` | Interaction when it does not (condition fails) |

### Execution Flow

```
PlacementCountCondition
    │
    ▼
┌─────────────────────────┐
│ Get the world's count   │
│ of placed `Block` from  │
│ the BlockCounter        │
│ resource (ChunkStore)   │
└─────────────────────────┘
    │
    ├─► count < Value ──► Execute Next      (LessThan: true, default)
    │
    └─► count >= Value ──► Execute Failed
```

PlacementCountCondition performs server-side validation (`WaitForDataFrom.Server`):

1. Reads the block type from `Block` property
2. Queries the world's `BlockCounter` resource (`BlockCounter.getBlockPlacementCount(block)`) for the number of that block currently placed
3. Compares count against `Value` threshold (`<` by default, `>` with `"LessThan": false`)
4. Branches to `Next` if the comparison holds, `Failed` otherwise

### Block Tracking Requirements

For PlacementCountCondition to work, two components must be configured:

**1. Block must have TrackedPlacement component:**

Blocks that should be counted need the `TrackedPlacement` component among their block-entity `Components` (from `Items/Electrum/Portal/Teleporter.json`, abbreviated):

```json
{
  "BlockType": {
    "BlockEntity": {
      "Components": {
        "Teleporter": { "WarpNameWordList": "Runes" },
        "TrackedPlacement": {}
      }
    }
  }
}
```

**2. Instance must have the BlockCounter resource:**

`BlockCounter` is a chunk-store resource registered by `InteractionModule` under the id `BlockCounter`; each instance seeds it from `Server/Instances/<Instance>/resources/BlockCounter.json`, which ships empty and fills up at runtime:

```json
{
  "BlockPlacementCounts": {}
}
```

`TrackedPlacement.OnAddRemove` does the bookkeeping: on block-entity spawn it calls `BlockCounter.trackBlock(blockType.getId())` and stashes that name on the component; on removal it calls `untrackBlock`. The key counted is therefore the **`BlockType` id** — which is what `PlacementCountCondition.Block` must name.

### Examples

**Teleporter Placement Limit (verbatim, from `Interactions/Block/Teleporter/Teleporter_Try_Place.json`):**

Only allow placing a teleporter while the world holds fewer than 2 (the count is per world, not per player):

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

**Combined with MemoriesCondition for Tier-Based Limits (verbatim, from `Interactions/Block/Teleporter/Teleporter_Place.json`):**

`MemoriesCondition` (`com.hypixel.hytale.builtin.adventure.memories.interactions.MemoriesConditionInteraction`) branches on the world's *memories level*: `Next` is a map from level (integer, as a string key) to interaction, and `Failed` runs when the current level has no entry. (The codec documents `Next` as "The interaction to run if the player's memories level matches the key", but the implementation reads `MemoriesPlugin.getMemoriesLevel(world.getGameplayConfig())` — it is a **world** level, shared by everyone in the world, not per player.) Each branch inherits `Teleporter_Try_Place` via `Parent` and overrides only `Value`, so higher levels allow more teleporters:

```json
{
  "Type": "MemoriesCondition",
  "Next": {
    "0": { "Parent": "Teleporter_Try_Place", "Value": 2 },
    "1": { "Parent": "Teleporter_Try_Place", "Value": 2 },
    "2": { "Parent": "Teleporter_Try_Place", "Value": 3 },
    "3": { "Parent": "Teleporter_Try_Place", "Value": 4 },
    "4": { "Parent": "Teleporter_Try_Place", "Value": 6 },
    "5": { "Parent": "Teleporter_Try_Place", "Value": 8 }
  },
  "Failed": {
    "Parent": "Teleporter_Try_Place",
    "Value": 8,
    "Failed": {
      "Type": "SendMessage",
      "Key": "server.interactions.teleporter.failed"
    }
  }
}
```

`Teleporter` is the only shipped block type that carries `TrackedPlacement`, so it is the only block a
`PlacementCountCondition` can count out of the box; to limit another block, add the component to that
block's `BlockEntity.Components` first, or its count stays at zero.

### Related Interactions

- [CooldownCondition](#cooldowncondition) - Check cooldown state (also uses `Next`/`Failed`)
- MemoriesCondition - Branch on the world's memories level (`Next` map keyed by level, plus `Failed`)
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
| `Repeat` | int | Codec doc: "The number of times to repeat. -1 is considered as infinite, be careful when using this value." Default `1`; validated as ≥ 1 **or** exactly `-1`, so `0` fails validation |
| `ForkInteractions` | object | Codec doc: "The interactions to run in the forks created by this interaction." A **root** interaction reference or inline root. **Required** (`Validators.nonNull()`) |
| `Next` | interaction | From `SimpleInteraction`. Runs after the last iteration finishes successfully |
| `Failed` | interaction | From `SimpleInteraction`. Runs when a forked chain **fails** — remaining repetitions are abandoned |
| `HorizontalSpeedMultiplier` | float | From the `Interaction` base. Movement speed modifier while the repeat runs (e.g. `0.6` for 60% speed) |
| `Rules` | object | From the `Interaction` base. Contains `InterruptedBy` for early termination |
| `RunTime` | float | From the `Interaction` base — but see the gotcha below; it does **not** pace the iterations |

Codec doc for the interaction itself: "Forks from the current interaction into one or more chains that
run the specified interactions. When run this will create a new chain that will run the interactions
specified in `ForkInteractions`. This will then wait until that chain completes. If the chain completes
successfully it will then check the `Repeat` field to see if it needs to run again, if not then the
interactions `Next` are run otherwise this repeats with the next fork. If the chain fails then any
repeating is ignored and the interactions `Failed` are run instead."

> **Gotcha — `RunTime` on a `Repeat` is inert.** `Interaction.tick` applies the base `RunTime` gate
> first and then calls `tick0`, and `RepeatInteraction.tick0` unconditionally reassigns the
> interaction state from the forked chain's state on every tick. Iteration pacing therefore comes
> entirely from how long each forked chain takes, not from `RunTime`. Some shipped assets still carry
> it (e.g. `Weapons/Daggers/Deprecated/Attacks/Stab_Flurry/Daggers_Stab_Flurry_8.json` sets
> `"RunTime": 0.138` with `"Repeat": 4`) — put the delay in the forked chain instead.

### Examples

**Whirlwind Attack (speed-modified combat loop):**

```json
{
  "Type": "Repeat",
  "Repeat": 10,
  "HorizontalSpeedMultiplier": 0.6,
  "ForkInteractions": {
    "Interactions": [
      "MyMod_Whirlwind_Spin_Effect",
      "MyMod_Whirlwind_Damage_Selector"
    ]
  }
}
```

**Interruptible Reload (from `Interactions/Weapons/Common/StatAmmoReload/Common_StatAmmoReload_Entry.json`, abbreviated):**

An endless loop that reloads one step per iteration. Two different things end it: input listed in
`Rules.InterruptedBy` cuts it off, and the fork **failing** — here, the `StatsCondition` finding the ammo
already at 100% — abandons the remaining repetitions and runs `Failed`:

```json
{
  "Type": "Repeat",
  "Repeat": -1,
  "Rules": {
    "InterruptedBy": ["Primary", "Secondary"]
  },
  "ForkInteractions": {
    "Interactions": [
      {
        "Type": "StatsCondition",
        "LessThan": true,
        "Costs": { "Ammo": 100 },
        "ValueType": "Percent",
        "Next": {
          "Type": "Replace",
          "Var": "Reload_ItemConsume",
          "DefaultValue": { "Interactions": ["Common_StatAmmoReload_ItemConsume"] }
        }
      }
    ]
  },
  "Failed": {
    "Type": "Replace",
    "Var": "No_Ammo_Effects",
    "DefaultValue": { "Interactions": ["Common_Bow_No_Ammo"] }
  }
}
```

**Rapid Strikes (from `Weapons/Daggers/Deprecated/Attacks/Stab_Flurry/Daggers_Stab_Flurry_8.json`, verbatim):**

Its `RunTime` is the inert one described in the gotcha above; the pacing comes from the forked chain, which runs the left and then the right stab each iteration:

```json
{
  "Type": "Repeat",
  "$Comment": "Prepare Delay",
  "RunTime": 0.138,
  "Repeat": 4,
  "ForkInteractions": {
    "Interactions": [
      "Daggers_Stab_Flurry_Left",
      "Daggers_Stab_Flurry_Right"
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
    "Interactions": ["MyMod_Fallback_Effect"]
  },
  "DefaultOk": true
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Var` | string | Variable name to look up in the chain's `InteractionVars`. **Required** (validated non-null) |
| `DefaultValue` | object | Fallback root interaction if the variable isn't set — an id string *or* an inline `{ "Interactions": [...] }` root |
| `DefaultOk` | boolean | If `true`, silently uses default when variable missing. If `false`, logs SEVERE error then uses default. |

### DefaultOk Behavior

| `DefaultOk` | Variable Missing | Result |
|-------------|------------------|--------|
| `true` | Yes | Silently uses `DefaultValue` |
| `false`/omitted | Yes | Logs SEVERE error (rate-limited to once a minute), then uses `DefaultValue` |
| either | No | Uses the variable's value |

If the variable is missing **and** there is no `DefaultValue`, the interaction ends in the `Failed` state.

The SEVERE line is `Missing replacement interactions for interaction: %s for var %s on item %s` (interaction id, variable name, held item) and is emitted only on the authoritative run, never during client simulation.

### Example: Reusable Consumable Template

Create a generic consume template that items can customize:

**MyMod_Consume_Template.json** (an interaction of your own):
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
                "Interactions": ["MyMod_No_Effect"]
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

## RunOnBlockTypes

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.RunOnBlockTypesInteraction`

Finds matching blocks around the interacting entity and forks a chain onto each one. Codec doc:
"Searches for matching block types within a radius and runs interactions on each found block up to a
configured maximum number of blocks." Extends `SimpleInteraction`, and unlike most block-facing types
it searches from the **entity's** position rather than a targeted block.

| Property | Type | Description |
|----------|------|-------------|
| `Range` | int | Spherical search radius. Validated `greaterThan(0)` |
| `BlockSets` | string[] | `BlockSet` ids to match. Validated non-empty, and late-validated against the loaded `BlockSet` assets |
| `MaxCount` | int | Maximum block positions to act on. Validated `greaterThan(0)` |
| `Interactions` | interaction | The chain to run per matched block — inline or a root-interaction reference. Late-validated against the `RootInteraction` assets |

**None of the four is required at load**: an empty `RunOnBlockTypes` decodes. All four carry a `true`
third argument to `KeyedCodec`, which in 0.7.2 changes only how an explicit `null` is decoded; an
omitted key still passes. The validators check a written value: `Range` and `MaxCount` fall back to
`0` when omitted, and `BlockSets`' `nonEmptyArray()` is satisfied by its field's initial empty array.
A key is required only when it carries `Validators.nonNull()` (or `nonEmptyArray()`) **and** its
field is still null after construction, as [SendBeacon's `Message`](npc-roles.md#sendbeacon) is.
Write all four anyway. With `BlockSets` omitted the search matches nothing, and with `Interactions`
omitted there is nothing to fork; either way the interaction ends `Failed`.

Two of the four are also the **raw** `KeyedCodec` form rather than the parameterised one —
`new KeyedCodec("Interactions", RootInteraction.CHILD_ASSET_CODEC, true)` and the array-codec
`BlockSets` — the same shape `CustomConnectedBlockTemplateAsset`'s `Shapes` has, which a pattern
expecting `KeyedCodec<T>` skips silently.

Its one shipped use is the Rekindle Embers spellbook, which raises undead from bone blocks around
the caster (`Server/Item/Items/Weapon/Spellbook/Weapon_Spellbook_Rekindle_Embers.json`, abridged —
the forked chain continues into a full `SpawnNPC`):

```json
{
  "Type": "RunOnBlockTypes",
  "BlockSets": [ "Necromancy_Bones" ],
  "MaxCount": 5,
  "Range": 5,
  "Interactions": {
    "Interactions": [
      { "Type": "Serial", "Interactions": [ { "Type": "SpawnNPC" } ] }
    ]
  }
}
```

Note the inline form of `Interactions`: an object with its own `Interactions` array, i.e. a
root-interaction body written in place rather than referenced by id.

- **`MaxCount` selects at random, not by distance.** The matched positions are reservoir-sampled down
  to `MaxCount`, so a value below the number of matches picks an arbitrary subset each run.
- **Each fork carries its own block position and is validated independently at the tick it runs** —
  the codec says so — so a block that becomes invalid between the search and its fork simply fails
  that fork rather than the whole interaction.

---

## Target Selectors

For target selection in combat interactions, see the **[Selector](interactions-combat.md#selector)** interaction in the Combat Interactions documentation.

The `Selector` interaction type picks targets with one of the six shapes registered on `SelectorType.CODEC` — `Horizontal`, `Stab`, `AOECircle`, `AOECylinder`, `Raycast` and `Donut` — and runs interactions on the entities or blocks it hits. In 0.7.2 `AOECircle` (and so `AOECylinder`, which extends it) and `Stab` gained a `SizeAttribute` key and `Raycast` a `DistanceAttribute` key, which name an ability attribute that scales the shape during an ability cast.

---

## Gotchas & Errors

- **Symptom:** a `Replace` logs a SEVERE error in the server log → `DefaultOk` is `false`/omitted and the `Var` was not provided by the item. It still falls back to `DefaultValue`, but noisily. Fix: set `"DefaultOk": true` when the variable is genuinely optional, or have the referencing item define the variable (see [DefaultOk Behavior](#defaultok-behavior)).
- **Symptom:** a `Parallel` entry written as a plain interaction (`{ "Type": "ApplyEffect", … }`) fails asset validation → each entry is a **root**, so an inline entry must be a root body, `{ "Interactions": [ … ] }`, and a string entry must name a file under `RootInteractions/`. Fix: wrap the step (see [Interactions Array Format](#interactions-array-format-1)).
- **Symptom:** a target picked in one `Parallel` branch is unknown in another → forks run on a *copy* of the context's meta store. Entities are not copied, so stat changes and damage from every branch do land. Fix: keep steps that share meta values in one branch, or use `Serial` (see [Context Behavior](#context-behavior)).
- **Symptom:** steps after a `Parallel` run before all its branches finish → the chain waits for branch 1 only; branches 2+ are forks with no join. Fix: put whatever must finish first in branch 1, or restructure with `Serial`.
- **Symptom:** a `Condition` / `StatsCondition` interaction does nothing → the check failed and there is no `Failed` branch, so the chain simply fails there. Fix: give it a `Failed` branch.
- **Symptom (0.7.2):** a `StatsCondition` with `UseAbilityCost` always passes, even when the player is out of the resource → no cost resolved, which passes by design: the chain is not running from the ability slot, the ability has no `Cost`/`CostType`, or the player is in Creative (see [Ability Costs](#ability-costs)).
- **Symptom:** `ResetCooldown` leaves an ability *on* cooldown → "reset" restarts the timer at its full duration; it does not clear it. Fix: pass a shorter `Cooldown` to shorten the restart (see [ResetCooldown](#resetcooldown)).
- **Symptom:** a `MovementCondition` diagonal does nothing, and `Failed` never fires for it → `Failed` is the `MovementDirection.None` (standing-still) branch, not a catch-all; an omitted direction key compiles to an empty branch. Fix: define every direction you care about explicitly (see [MovementCondition](#movementcondition)).
- **Symptom:** an `EffectCondition` takes `Next` even though the target entity is gone → an invalid target ref, or a target with no `EffectControllerComponent`, leaves the state untouched, which reads as success. Fix: gate on something that actually fails (e.g. a `Selector` that produced the target) before the `EffectCondition`.
- **Symptom (0.6.3):** a block's `Use` chain that starts with a `BlockCondition` stops working in Creative → the interaction force-fails whenever the player's creative `PlaceMode` is not `Default`. Fix: switch the place mode back to `Default` (see [StaticFace Behavior](#staticface-behavior)).
- **Symptom:** a `Repeat` ignores its `RunTime` → `RepeatInteraction.tick0` overwrites the state every tick, so the base `RunTime` gate never applies. Fix: put the per-iteration delay inside `ForkInteractions` (see [Repeat](#repeat)).
