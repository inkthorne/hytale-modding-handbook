---
title: "NPC Roles"
description: "Define Hytale NPC roles in JSON — abstract Template and concrete Variant roles, a Parameters/Compute system, attitude definitions between groups, and groups and flocks for spawning."
seo:
  type: TechArticle
---

# NPC Roles

**Doc type:** JSON asset format · **Assets:** `Server/NPC` · **Verified against 0.5.1**

This document covers NPC role asset definitions, including templates, variants, behaviors, and spawning configurations. These assets are found in `Assets.zip` under `Server/NPC/`.

> **See also:** [NPC API](npc.md) for plugin events and sensor systems, [Drop System](drops.md) for NPC loot tables

---

## Overview

Defined as JSON assets under `Server/NPC/` in `Assets.zip` and provides:
- Role definitions: abstract `Template` roles and concrete `Variant` roles
- A `Parameters` / `Compute` system for parameterizing templates
- Attitude definitions describing relationships between NPC groups
- Groups and flocks for spawn grouping and pack sizing
- Spawn beacons controlling where and how NPCs spawn
- A behavior system (Instructions: sensors, actions, body motion) and reusable components
- Combat Action Evaluator (CAE) files for intelligent combat decisions

## Architecture
```
Server/NPC/
├── Roles/        Templates (Abstract) + Variants (concrete, inherit via Reference)
│   ├── Parameters / Compute   (parameterized values)
│   ├── MotionControllerList   (Walk / Fly)
│   └── Instructions           (Sensors → Actions / BodyMotion; reusable Components)
├── Attitude/     Friendly / Hostile / Neutral / Ignore / Revered between groups
├── Groups/       Named role collections (IncludeRoles, wildcards)
├── Flocks/       Weighted flock sizes
├── Spawn/Beacons/  Where/when NPCs spawn (by zone/tier/biome)
├── Balancing/    Combat Action Evaluator (CAE) files
└── DecisionMaking/ AI decision conditions
```

## Key Classes
The table below lists JSON asset constructs (file types / field schemas), not Java classes. Note, however, that the **behavior building blocks** these assets reference by `Type` — `Sensor`, `Action`, `BodyMotion`, `HeadMotion`, `EntityFilter` — *are* concrete Java classes (in `com.hypixel.hytale.server.npc.corecomponents.*`), and a plugin can register its own. The behavior system is data-*driven* but not code-closed; see [Registering custom core components (Java)](#registering-custom-core-components-java).

| Construct | Location | Description |
|-----------|----------|-------------|
| Role (`Template`) | `Server/NPC/Roles/` | Abstract base with `Parameters`; concrete roles inherit from it |
| Role (`Variant`) | `Server/NPC/Roles/` | Concrete NPC referencing a template, overriding via `Modify` |
| Attitude file | `Server/NPC/Attitude/Roles/` | Maps attitude values to other group names |
| Group file | `Server/NPC/Groups/` | Named collection of roles (`IncludeRoles`) |
| Flock file | `Server/NPC/Flocks/` | Weighted flock-size configuration |
| Spawn beacon | `Server/NPC/Spawn/Beacons/` | Spawn location/timing/filter configuration |
| CAE file | `Server/NPC/Balancing/` | Combat Action Evaluator for intelligent combat |

## Directory Structure

The NPC system is organized into several directories:

| Directory | Description |
|-----------|-------------|
| `Server/NPC/Roles/` | 952 NPC role definitions (templates and variants) |
| `Server/NPC/Attitude/` | Relationship definitions between NPC groups |
| `Server/NPC/Groups/` | NPC group collections for spawning |
| `Server/NPC/Flocks/` | Flock size configurations |
| `Server/NPC/Spawn/` | Spawn beacon configurations |
| `Server/NPC/Balancing/` | Combat Action Evaluator (CAE) files |
| `Server/NPC/DecisionMaking/` | AI decision conditions |

---

## Role Types

A role's top-level `Type` is one of four values registered by the role `BuilderFactory`:

| `Type` | Spawnable | Description |
|--------|-----------|-------------|
| `Abstract` | No | Template/base; concrete roles inherit from it via `Reference` |
| `Variant` | Yes | Concrete role referencing a template, overriding via `Modify` |
| `Generic` | Yes | Concrete, **self-contained** role that defines its behavior inline (the type the engine's own `Test_*` roles use) |
| `Role` | Yes | Concrete role (base concrete type) |

Most shipped content is the `Abstract` template + `Variant` pair documented below. Reach for **`Generic`** when you want a standalone role that defines its own inline `Instructions` rather than inheriting them — see [the Variant `Modify` gotcha](#variants) for why inline behavior must use `Generic`, not `Variant`.

### Abstract Templates

Templates define common behaviors and properties that concrete NPCs inherit from. They use `"Type": "Abstract"` and expose configurable values in their `Parameters` block. The shared core templates are found in `Server/NPC/Roles/_Core/Templates/`.

**Core Templates** (`Roles/_Core/Templates/`):

| Template | Description |
|----------|-------------|
| `Template_Animal_Neutral` | Neutral wild animal base (used by Cow, etc.) |
| `Template_Livestock` | Farm livestock base |
| `Template_Predator` | Base predator behavior with hunting AI |
| `Template_Intelligent` | Intelligent humanoid base |
| `Template_Spirit` | Spirit/ethereal base |
| `Template_Birds_Passive` | Flying passive bird behavior |
| `Template_Swimming_Passive` | Passive swimming creature base |
| `Template_Swimming_Aggressive` | Aggressive swimming creature base |
| `Template_Edible_Critter` | Small edible critter base |
| `Template_Beasts_Passive_Critter` | Passive beast critter base |
| `Template_Summoned_Ally` | Summoned allied NPC base |

Faction-specific templates live alongside their faction roles rather than in the shared `_Core/Templates/` folder. For example, Goblin templates are in `Roles/Intelligent/Aggressive/Goblin/Templates/` (`Template_Goblin`, `Template_Goblin_Scrapper`, `Template_Goblin_Ogre`, `Template_Goblin_Lobber`, and others). Trork, Kweebec, Feran, and Scarak templates follow the same convention under their own faction directories.

### Variants

Variants are concrete NPC definitions that inherit from a template. They use `"Type": "Variant"`, a `Reference` naming the parent template (by short name, resolved across the role tree), and `Modify` to override properties. Overridden numeric properties are usually plain values, not `{Value, Description}` objects (that form is only used inside a template's `Parameters` block). A variant may add its own `Parameters` block to supply values consumed by the template's `Compute` expressions.

**Example: Cow (`Roles/Creature/Livestock/Cow.json`, abridged)**

```json
{
    "Type": "Variant",
    "Reference": "Template_Animal_Neutral",
    "Modify": {
        "Appearance": "Cow",
        "AttitudeGroup": "PreyBig",
        "FlockArray": [ "Cow", "Cow_Calf" ],
        "DropList": "Drop_Cow",
        "MaxHealth": 103,
        "ViewRange": 15,
        "ViewSector": 340,
        "HearingRange": 9,
        "AbsoluteDetectionRange": 2,
        "Attack": "Root_NPC_Attack_Melee",
        "IsTameable": true,
        "TameRoleChange": "Tamed_Cow",
        "IsMemory": true,
        "NameTranslationKey": { "Compute": "NameTranslationKey" }
    },
    "Parameters": {
        "NameTranslationKey": {
            "Value": "server.npcRoles.Cow.name",
            "Description": "Translation key for NPC name display"
        }
    }
}
```

**Example: Goblin Scrapper (`Roles/Intelligent/Aggressive/Goblin/Goblin_Scrapper.json`)**

A combat NPC. Note that the CAE is referenced through the `_CombatConfig` field; combat abilities, attack distances, and instructions all come from the referenced template and CAE rather than being inlined here.

```json
{
    "Type": "Variant",
    "Reference": "Template_Goblin_Scrapper",
    "Modify": {
        "_CombatConfig": "CAE_Goblin_Scrapper",
        "MaxHealth": 38,
        "IsMemory": true,
        "MemoriesCategory": "Goblin",
        "MemoriesNameOverride": "Goblin_Scrapper",
        "NameTranslationKey": { "Compute": "NameTranslationKey" }
    },
    "Parameters": {
        "NameTranslationKey": {
            "Value": "server.npcRoles.Goblin_Scrapper.name",
            "Description": "Translation key for NPC name display"
        }
    }
}
```

> **Gotcha: a `Variant`'s `Modify` cannot hold `Instructions`.** Every value in a `Modify` block runs through the NPC **expression** system, which rejects a structural `Instructions` array. Shipping a `Variant` that overrides `Instructions` fails to load with `Illegal JSON value for expression: [{"Sensor":...}]`, and the role then silently never registers (it's absent from the spawn list). To give an NPC custom inline behavior, author a **`Type: "Generic"`** role with top-level `Instructions` instead — see [Inline behavior with a Generic role](#inline-behavior-with-a-generic-role).

---

## Parameters System

Templates declare configurable values in a `Parameters` block, each with a `Value` and a `Description`. Elsewhere in the role those parameters are read back with `{ "Compute": "..." }` expressions. Variants override the underlying values either by plain assignment in `Modify` or by supplying their own `Parameters` block.

### Value and Description

These come from a template's `Parameters` block (from `Template_Animal_Neutral`):

```json
{
    "MaxHealth": {
        "Value": 100,
        "Description": "The maximum health of the NPC."
    },
    "ViewRange": {
        "Value": 16,
        "Description": "The view distance of the NPC, in blocks."
    }
}
```

### Computed Values

Use `Compute` to read a parameter (or evaluate an expression over parameters) at the point of use:

```json
{
    "MaxHealth": { "Compute": "MaxHealth" },
    "Appearance": { "Compute": "Appearance" },
    "Enabled": { "Compute": "!isEmptyStringArray(FlockArray)" }
}
```

Helper functions such as `isEmpty`, `isEmptyStringArray`, `makeRange`, and `randomInRange` are available inside `Compute` expressions.

---

## Key Properties

### Basic Properties

| Property | Type | Description |
|----------|------|-------------|
| `Appearance` | String | Visual model path |
| `MaxHealth` | Number | Maximum health points |
| `DropList` | String | Loot table reference (see [Drop System](drops.md)) |
| `NameTranslationKey` | String | Localization key for NPC name |
| `Scale` | Number | Size multiplier |

### Movement Properties

| Property | Type | Description |
|----------|------|-------------|
| `MotionControllerList` | Array | Movement controllers (`Walk` or `Fly`) |
| `MaxSpeed` | Number | Maximum movement speed (parameter; fed into `MaxWalkSpeed`) |
| `WanderRadius` | Number | Random movement range from home |
| `ClimbHeight` | Number | Maximum block height for climbing (fed into `MaxClimbHeight`) |
| `JumpHeight` | Number | Vertical jump capability |

### Detection Properties

| Property | Type | Description |
|----------|------|-------------|
| `ViewRange` | Number | Visual detection distance |
| `ViewSector` | Number | Field of view angle (degrees) |
| `HearingRange` | Number | Audio detection distance |
| `AbsoluteDetectionRange` | Number | Always-detect distance |

### Combat Properties

| Property | Type | Description |
|----------|------|-------------|
| `AttitudeGroup` | String | NPC's attitude group membership (e.g. `Prey`, `PreyBig`, `Predators`) |
| `DefaultPlayerAttitude` | String | Default stance toward players (`Hostile`, `Ignore`, `Neutral`) |
| `Attack` | String | Attack interaction reference |
| `AttackDistance` | Number | Melee attack range |
| `_CombatConfig` | String | CAE file name for intelligent combat (e.g. `CAE_Goblin_Scrapper`) |

### Behavior Properties

| Property | Type | Description |
|----------|------|-------------|
| `StartState` | String | Initial AI state |
| `DayTimePeriod` | Array | `[startHour, endHour]` range considered daytime |
| `Instructions` | Array | Behavior tree definition |

### Memory Properties

| Property | Type | Description |
|----------|------|-------------|
| `IsMemory` | Boolean | Whether NPC has memory system |
| `MemoriesCategory` | String | Memory type category |

---

## Attitude System

Attitudes define relationships between NPC groups. Found in `Server/NPC/Attitude/`. The file name (e.g. `Predators.json`) is the attitude group that the file describes, and its contents map each attitude value to the list of other groups treated that way.

### Attitude Values

| Attitude | Description |
|----------|-------------|
| `Friendly` | Allied groups |
| `Hostile` | Will attack |
| `Neutral` | Will react/defend but not attack on sight |
| `Ignore` | No reaction, neither ally nor enemy |
| `Revered` | Special respect (leaders, chieftains) |

### Attitude Definition Structure

Each file is a single object with a `Groups` key. Under `Groups`, each attitude value maps to an array of group names. Groups not listed use a default (typically `Ignore`).

**Example: `Attitude/Roles/Predators.json`**

```json
{
    "Groups": {
        "Hostile": [ "Predators", "PredatorsBig", "Void" ],
        "Ignore": [ "Prey", "PreyBig", "Critters", "Vermin" ]
    }
}
```

**Example: `Attitude/Roles/Prey.json`**

```json
{
    "Groups": {
        "Neutral": [ "Prey" ],
        "Ignore": [ "Predators", "PreyBig" ]
    }
}
```

---

## NPC Categories

NPCs are organized into a hierarchical category structure:

### Creature

| Subcategory | Examples |
|-------------|----------|
| `Critter/` | Squirrel, Rabbit, Butterfly |
| `Livestock/` | Cow, Sheep, Pig, Chicken |
| `Mammal/` | Wolf, Bear, Deer |
| `Mythic/` | Unique fantasy creatures |
| `Reptile/` | Lizards, Snakes |
| `Vermin/` | Rats, Spiders |

### Aquatic

| Subcategory | Examples |
|-------------|----------|
| `Abyssal/` | Deep sea creatures |
| `Freshwater/` | River and lake fish |
| `Marine/` | Ocean creatures |

### Avian

| Subcategory | Examples |
|-------------|----------|
| `Aerial/` | Flying birds |
| `Fowl/` | Ground birds |
| `Raptor/` | Birds of prey |

### Intelligent

**Aggressive Factions:**

| Faction | Description |
|---------|-------------|
| `Goblin/` | Goblins and variants (Scrapper, Archer, Shaman) |
| `Outlander/` | Human outlaws |
| `Scarak/` | Insectoid faction |
| `Trork/` | Pig-like warriors |

**Neutral Factions:**

| Faction | Description |
|---------|-------------|
| `Feran/` | Beast-folk traders |
| `Kweebec/` | Small forest dwellers |
| `Tuluk/` | Nomadic traders |

### Other Categories

| Category | Description |
|----------|-------------|
| `Elemental/Golem/` | Stone and element golems |
| `Elemental/Spirit/` | Elemental spirits |
| `Undead/` | Zombies, skeletons, ghosts |
| `Void/` | Void creatures |
| `Boss/` | Boss encounters |

---

## Motion Controllers

Motion controllers define how NPCs move through the world. They are listed in `MotionControllerList`. Two controller types appear in real role files:

| Controller | Usage | Description |
|------------|-------|-------------|
| `Walk` | common | Ground-based movement |
| `Fly` | rare | Aerial movement |

Many controller fields accept `{ "Compute": "..." }` so they can read template parameters.

### Walk Configuration Example

From `Template_Animal_Neutral`:

```json
{
    "MotionControllerList": [
        {
            "Type": "Walk",
            "MaxWalkSpeed": { "Compute": "MaxSpeed" },
            "Gravity": 15,
            "MaxFallSpeed": 15,
            "JumpHeight": 0.1,
            "MaxRotationSpeed": { "Compute": "MaxRotationSpeed" },
            "Acceleration": 100,
            "RunThreshold": { "Compute": "RunThreshold" },
            "MaxClimbHeight": { "Compute": "ClimbHeight" }
        }
    ]
}
```

### Fly Configuration Example

```json
{
    "MotionControllerList": [
        {
            "Type": "Fly",
            "MaxHorizontalSpeed": 50,
            "MaxSinkSpeed": 10,
            "MaxClimbSpeed": 10,
            "MinAirSpeed": 10,
            "Acceleration": 10,
            "MinHeightOverGround": 40,
            "MaxHeightOverGround": 45,
            "MaxRollAngle": 80,
            "MaxTurnSpeed": 45
        }
    ]
}
```

---

## Behavior System (Instructions)

The behavior system uses a state machine driven by nested instruction nodes. `Instructions` is an array of nodes; nodes may have a `Sensor` (the condition to evaluate), `Actions` (what to run on match), `BodyMotion`/`HeadMotion` (movement behavior), nested `Instructions`, and flags such as `Continue`, `Enabled` (often a `{ "Compute": ... }`), `ActionsBlocking`, and `Weight`/`Type: "Random"` for [weighted random selection](#randomized-instructions-type-random). A node's `Sensor` is optional: **if omitted, it always matches** (the explicit catch-all is `{ "Type": "Any" }`).

### States

States are freeform strings, set with the `State` action and tested with the `State` sensor. Sub-states are addressed with a leading dot (e.g. `Flee.Switch`, `Sleep.Nap`, `.Default`). Commonly used states include:

| State | Description |
|-------|-------------|
| `Idle` | Default passive state |
| `Sleep` | Sleeping/inactive |
| `Alerted` | Noticed potential threat |
| `Search` | Looking for lost target |
| `ReturnHome` | Returning to spawn area |
| `Flee` | Running from threat |
| `Panic` | Panicked escape behavior |

Individual roles define whatever additional states they need; there is no fixed enum.

### Sensors

A node's `Sensor` is an object with a `Type`. Sensors can be composed with `And`, `Or`, and `Not`. Common sensor types:

| Sensor Type | Description |
|-------------|-------------|
| `State` | Matches a given AI state (`"State": "Idle"`) |
| `Any` | Always matches (optionally `"Once": true`) |
| `Target` | A valid target exists in range |
| `Damage` | Received damage (optionally `"Combat": true`) |
| `Mob` | Other NPCs nearby (with `Filters`) |
| `Leash` | Distance from home exceeds `Range` |
| `Time` | Time of day within `Period` |
| `Block` / `DroppedItem` | Nearby block set or dropped items |
| `Beacon` / `Alarm` / `Timer` | Flock beacons, alarms, named timers |

### Actions

Each entry in `Actions` is an object whose `Type` is the action. Common action types:

| Action Type | Description |
|-------------|-------------|
| `State` | Change AI state (`{ "Type": "State", "State": "Alerted" }`) |
| `PlayAnimation` | Trigger an animation in a slot |
| `Attack` | Execute the configured attack |
| `JoinFlock` | Join a nearby flock |
| `Timeout` | Wait for a `Delay` (optionally run a nested `Action`) |
| `SetAlarm` / `TimerStart` | Schedule alarms and timers |
| `OverrideAttitude` | Temporarily change attitude toward a target |
| `Nothing` | No-op |

### BodyMotion

A node's `BodyMotion` is an object with a `Type`. NPC locomotion is a **steering-force** system: each motion is a concrete Java class (under `com.hypixel.hytale.server.npc.corecomponents.movement`, plus `combat`) whose `Type` is the class name with the `BodyMotion` prefix stripped. The full built-in set:

| Motion Type | Description |
|-------------|-------------|
| `Wander` / `WanderInCircle` / `WanderInRect` | Random movement (in place / circle / rectangle) |
| `Find` / `FindWithTarget` | Path to a found point / toward the sensor's target |
| `MaintainDistance` | Keep a desired distance from target (strafes intermittently) |
| `MoveAway` | Flee away from target |
| `Land` / `TakeOff` / `Leave` | Flight transitions and despawn-departure |
| `Teleport` | Teleport to target position |
| `MatchLook` | Orient to match a look direction |
| `Charge` / `AimCharge` | Combat charge attacks (`corecomponents.combat`) |

There is **no built-in "orbit a target" motion** — `MaintainDistance` only strafes in duration/frequency bursts. A continuously circling motion has to be written as a custom `BodyMotion` (see [Registering custom core components (Java)](#registering-custom-core-components-java)).

### Instruction Tree Example

Real instruction nodes carry the action via `Type` (there is no separate `Action` field on the node). This pattern matches the structure in `Template_Animal_Neutral`:

```json
{
    "Instructions": [
        {
            "Sensor": { "Type": "State", "State": "Idle" },
            "Instructions": [
                {
                    "Sensor": { "Type": "Damage", "Combat": true },
                    "Actions": [
                        { "Type": "State", "State": "Alerted" }
                    ]
                },
                {
                    "Sensor": {
                        "Type": "Leash",
                        "Range": { "Compute": "LeashDistance" }
                    },
                    "ActionsBlocking": true,
                    "Actions": [
                        { "Type": "Timeout", "Delay": [ 15, 20 ] },
                        { "Type": "State", "State": "ReturnHome" }
                    ]
                },
                {
                    "BodyMotion": {
                        "Type": "WanderInCircle",
                        "Radius": { "Compute": "WanderRadius" },
                        "RelativeSpeed": 0.18
                    }
                }
            ]
        }
    ]
}
```

### Sensor → BodyMotion target hand-off

Within a single instruction node, the `Sensor` and the `BodyMotion` share an `InfoProvider`. `SensorEntityBase` owns an `EntityPositionProvider` and exposes `getSensorInfo()`; when the sensor matches a target, the node's motion reads the matched entity/position back through `info.getPositionProvider()`. So a **target-relative motion must be paired with a target-producing sensor** — e.g. `"Sensor": { "Type": "Player", "Range": N, "LockOnTarget": true }`. `"Type": "Any"` is the catch-all (no target), making it a good fallback node. Sensor classes live in `com.hypixel.hytale.server.npc.corecomponents.entity` (`SensorPlayer`, `SensorTarget`, `SensorEntity`, `SensorSelf`, `SensorBeacon`, …).

### Randomized instructions (Type: Random)

A node with `"Type": "Random"` (class `InstructionRandomized`) picks **one** of its child `Instructions` by weight and runs it. The surprising default: the pick is **permanent** — it only re-rolls on a state change or an explicit reset. Add `ExecuteFor` to make it a timer-driven switch (the headline use case is alternating a `BodyMotion` on a timer).

Fields read by `BuilderInstructionRandomized` (defaults from the bytecode):

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `Type` | string | — | Must be `"Random"` to select this builder. |
| `Instructions` | array | — | The candidate branches. Each child's own `Weight` sets its odds. |
| `ExecuteFor` | `[min, max]` | `[MAX, MAX]` | How long to run the chosen branch before re-rolling. Omitted ⇒ effectively never (the pick is permanent). Each entry must be `> 0` and `min ≤ max`. Units appear to be **seconds** (inferred — subtracted as the tick `dt`). |
| `ResetOnStateChange` | bool | `true` | Re-roll when the NPC's AI state changes. |
| `Sensor` | object | always matches | Gates the **whole** Random node; omit ⇒ always matches (general node behavior). |
| `Name` | string | — | Lets a `ResetInstructions` action target this node to force a re-roll. |
| `Enabled` / `Continue` / `Tag` | — | — | Standard node flags (see the intro above). |

`Weight` is **not** a field of the Random node itself — it is read from each **direct child** (`Instruction.getWeight()`) to build the weighted map. Equal or absent weights ⇒ uniform.

**Per-tick selection** (`InstructionRandomized.execute`, `dt` = the tick delta):

```
timeout -= dt
if (timeout <= 0 || current == null) {
    current  = weightedMap.get(random())                  // re-roll a branch by Weight
    timeout  = randomRange(ExecuteFor[0], ExecuteFor[1])  // new random window
}
if (current.matches(self, role, dt, store))               // ← re-checked EVERY tick
    current.execute()
```

A state change calls `clearOnce()`, which nulls `current` (forcing a re-roll next tick) only when `ResetOnStateChange` is `true`. Two non-obvious consequences:

1. **No `ExecuteFor` ⇒ the pick is permanent.** The default window is `[Double.MAX_VALUE, Double.MAX_VALUE]`, so `timeout` never reaches 0. The builder's own long description: *"One will be selected at random and executed until the NPC state changes."* The only re-roll triggers are then (a) a state change while `ResetOnStateChange` is `true`, or (b) an explicit `ResetInstructions`. **Add `ExecuteFor` for a timed re-roll.**
2. **The chosen branch's `Sensor` is re-evaluated every tick.** If it matched at pick time but stops matching mid-window (e.g. a `Player`-range sensor once the player walks off), the branch does **nothing** for the rest of the window — and the pick is **not** re-rolled; the NPC just idles. Workaround: give the branch a permissive top-level sensor (omit `Sensor`, or `"Type": "Any"`) and push the conditional logic into a nested `Instructions` fallthrough.

#### Timed switch example

`Inkwell_Chicken_Annoying` alternates every 5–12 s between orbiting the nearest player and wandering. The orbit branch is wrapped in `"Sensor": { "Type": "Any" }` with a nested fallthrough so it **wanders instead of freezing** when no player is in range (consequence #2 above):

```json
"Instructions": [
  {
    "Type": "Random",
    "Continue": true,
    "ExecuteFor": [ 5, 12 ],
    "Instructions": [
      {
        "Weight": 1,
        "Sensor": { "Type": "Any" },
        "Instructions": [
          {
            "Sensor": { "Type": "Player", "Range": 30, "LockOnTarget": true },
            "BodyMotion": { "Type": "Inkwell_Orbit", "Radius": 2.5, "RelativeSpeed": 0.95 }
          },
          {
            "Sensor": { "Type": "Any" },
            "BodyMotion": { "Type": "WanderInCircle", "Radius": 6, "RelativeSpeed": 0.25 }
          }
        ]
      },
      {
        "Weight": 1,
        "Sensor": { "Type": "Any" },
        "BodyMotion": { "Type": "WanderInCircle", "Radius": 6, "RelativeSpeed": 0.25 }
      }
    ]
  }
]
```

`Inkwell_Orbit` is a custom `BodyMotion` (see [Registering custom core components](#registering-custom-core-components-java)); for stock-only content swap in a vanilla motion — vanilla `Test_Random_Instruction.json` cycles `WanderInCircle` vs `Nothing` the same way.

#### Forcing a re-roll: `Name` + `ResetInstructions`

For the unbounded (no `ExecuteFor`) form, give the Random node a `Name` and have a separate instruction fire a `ResetInstructions` action to re-roll on demand. Vanilla `Test_Random_Instruction.json` shows both forms; this is its re-roll half:

```json
{ "Type": "Random", "Name": "Test", "Instructions": [ /* … branches … */ ] },
{ "Instructions": [
  { "Sensor": { "Type": "And", "Sensors": [
      { "Type": "Player", "Range": 10, "LockOnTarget": true },
      { "Type": "Damage" } ] },
    "Actions": [ { "Type": "ResetInstructions", "Instructions": [ "Test" ] } ] }
]}
```

Vanilla reference: `Server/NPC/Roles/_Core/Tests/Test_Random_Instruction.json` (both forms); production usage in `_Core/Templates/Template_{Livestock,Predator,Animal_Neutral,Intelligent}.json` and the reusable `_Core/Components/Steps/Component_Instruction_Combat_*.json` steps.

---

## Registering custom core components (Java)

The behavior building blocks referenced by `Type` in role JSON — `BodyMotion`, `HeadMotion`, `Sensor`, `Action`, `EntityFilter` — are concrete Java classes, each with a `Builder*` companion that acts as its JSON codec. A plugin can **register its own** and reference it from role JSON by `Type`, exactly like a built-in.

The core NPC plugin is itself a `JavaPlugin` with a static accessor and a registration method:

```java
// com.hypixel.hytale.server.npc.NPCPlugin
public static NPCPlugin get();
public <T> NPCPlugin registerCoreComponentType(String typeName, Supplier<Builder<T>> builder);
// Category constants route a builder to the right factory:
//   FACTORY_CLASS_ROLE / _BODY_MOTION / _HEAD_MOTION / _ACTION / _SENSOR /
//   _INSTRUCTION / _TRANSIENT_PATH / _ACTION_LIST
```

A builder's `category()` decides which slot its `Type` is usable in — `BuilderBodyMotionBase.category()` returns `BodyMotion.class`, so registering a `BuilderBodyMotionX` makes `"Type": "X"` valid in any `BodyMotion` slot. Register in your plugin's `setup()`:

```java
NPCPlugin.get().registerCoreComponentType("Inkwell_Orbit", BuilderBodyMotionOrbit::new);
```

No manifest `Dependencies` entry is needed — the NPC plugin is core and always loads first (and a wrong `group:name` would only *break* your load).

### The custom-`BodyMotion` contract

Locomotion is a **steering-force** system: a motion writes a *desired-movement vector* into a `Steering`, and the engine integrates that with pathing, collision avoidance, and the motion controller. **Do not drive an AI NPC by writing the `Velocity` component each tick** — that fights the locomotion layer. (`Velocity` is for knockback/impulses; see the [Velocity API](entities.md#velocity-api). Continuous AI movement belongs in a `BodyMotion`.)

```java
// Motion side: extends com.hypixel.hytale.server.npc.corecomponents.BodyMotionBase
public BodyMotionX(BuilderBodyMotionX builder, BuilderSupport support) { super(builder); /* read getters */ }

// return false = motion inactive this tick (no target / nothing to do)
public boolean computeSteering(Ref<EntityStore> self, Role role, InfoProvider info, double dt,
                               Steering out, ComponentAccessor<EntityStore> acc) {
    // Self position:
    TransformComponent tf = acc.getComponent(self, TransformComponent.getComponentType());
    Vector3d selfPos = tf.getPosition();                 // org.joml.Vector3d

    // Target comes from the PAIRED SENSOR, not a world query:
    IPositionProvider pp = info.getPositionProvider();   // com.hypixel.hytale.server.npc.sensorinfo.*
    if (pp == null || !pp.hasPosition()) return false;
    pp.providePosition(targetVec); pp.getTarget();       // position / Ref to the matched entity

    // Write movement:
    out.clear();
    out.setTranslation(x, y, z);                         // direction
    out.setTranslationRelativeSpeed(0.95);               // 0..1 fraction of the controller's MaxWalkSpeed
    // out.setYaw(float);                                // OPTIONAL — see "Facing" below
    return true;
}
```

Reusable steering primitives live in `com.hypixel.hytale.server.npc.movement.steeringforces` (`SteeringForcePursue`, `SteeringForceEvade`, `SteeringForceWander`, `SteeringForceRotate`, `SteeringForceAvoidCollision`, `SteeringForceWithTarget`).

The matching builder extends `BuilderBodyMotionBase` (whose `category()` returns `BodyMotion.class`). The framework calls `readCommonConfig(json)` then your `readConfig(json)`:

```java
@Override public BuilderBodyMotionX readConfig(JsonElement el) {
    getDouble(el, "Radius", radiusHolder, 3.0, DoubleSingleValidator.greater0(),
              getBuilderDescriptorState(), "short desc", null /* long desc */);
    getBoolean(el, "Clockwise", clockwiseHolder, true, getBuilderDescriptorState(), "short", null);
    return this;
}
@Override public BodyMotionX build(BuilderSupport s) { return new BodyMotionX(this, s); }
@Override public BuilderDescriptorState getBuilderDescriptorState() { return BuilderDescriptorState.Stable; }
@Override public String getShortDescription() { return "..."; }   // abstract — required
@Override public String getLongDescription()  { return "..."; }   // abstract — required
// getters resolve holders: radiusHolder.get(support.getExecutionContext())
```

Param holders (`DoubleHolder`, `BooleanHolder`, `NumberArrayHolder`, …) live in `com.hypixel.hytale.server.npc.asset.builder.holder`. The `getDouble` / `getBoolean` / `requireDoubleRange` config DSL lives on `BuilderBase`. Validators (optional, may be `null`) come from `com.hypixel.hytale.server.npc.asset.builder.validators`: `DoubleSingleValidator.greater0()` / `.greaterEqual0()`, `DoubleRangeValidator.between(a, b)` / `.fromExclToIncl(a, b)`.

### Facing: forward-moving motions set no yaw

Built-in forward-movers (`BodyMotionMoveAway`, `BodyMotionFindWithTarget`) set **no** rotation in `computeSteering` — the locomotion controller orients the NPC to its movement direction automatically. Only motions that want *decoupled* facing call `out.setYaw(...)` (e.g. `BodyMotionWanderBase` sets a wander heading; `MaintainDistance` faces its target while strafing). **Takeaway:** to face the movement direction, set no yaw; to face elsewhere (strafe-and-stare), set `out.setYaw(...)`.

### Inline behavior with a Generic role

A `Variant` cannot carry `Instructions` (see the [Variants gotcha](#variants)). To give an NPC custom inline behavior, author a self-contained `Type: "Generic"` role with top-level `Instructions`:

```json
{
  "Type": "Generic",
  "Appearance": "Chicken",
  "MotionControllerList": [ { "Type": "Walk", "MaxWalkSpeed": 7, "Gravity": 10, "MaxFallSpeed": 20, "Acceleration": 10 } ],
  "MaxHealth": { "Compute": "MaxHealth" },
  "Parameters": { "MaxHealth": { "Value": 12, "Description": "..." } },
  "Instructions": [
    { "Sensor": { "Type": "Player", "Range": 30, "LockOnTarget": true },
      "BodyMotion": { "Type": "Inkwell_Orbit", "Radius": 2.5, "RelativeSpeed": 0.95 } },
    { "Sensor": { "Type": "Any" }, "BodyMotion": { "Type": "WanderInCircle", "Radius": 6, "RelativeSpeed": 0.25 } }
  ],
  "NameTranslationKey": "server.npcRoles.Foo.name"
}
```

The role id is the **filename without `.json`**. `"Appearance": "Chicken"` reuses a vanilla model by its *referenced* (unprefixed) id. A `BodyMotion`'s `RelativeSpeed` (0..1) scales against the controller's `MaxWalkSpeed`. The first node here uses a custom `Inkwell_Orbit` motion registered via `registerCoreComponentType`; the second is a vanilla fallback.

---

## Components

Reusable behavior components allow shared logic across NPCs. They are referenced by short name with `Reference`, optionally adjusted with `Modify` (whose fields commonly use `{ "Compute": ... }`). Component files use the prefixes `Component_Sensor_*`, `Component_Instruction_*`, and `Component_ActionList_*`.

### Sensor Components

A sensor component can be referenced directly in a node's `Sensor` field:

```json
{
    "Sensor": {
        "Reference": "Component_Sensor_Standard_Detection",
        "Modify": {
            "ViewRange": { "Compute": "ViewRange" },
            "ViewSector": { "Compute": "ViewSector" },
            "HearingRange": { "Compute": "HearingRange" },
            "AbsoluteDetectionRange": { "Compute": "AbsoluteDetectionRange" },
            "Attitudes": [ "Hostile", "Neutral" ]
        }
    }
}
```

### Instruction Components

An instruction node can pull in a shared subtree:

```json
{
    "Reference": "Component_Instruction_Damage_Check",
    "Modify": {
        "_ExportStates": [ "Flee.Switch", "Panic" ],
        "AlertedRange": { "Compute": "AlertedRange" }
    }
}
```

### Action List Components

State transitions can reference shared action lists:

```json
{
    "States": [
        { "From": [ "Idle" ], "To": [ "Sleep" ] }
    ],
    "Actions": {
        "Reference": "Component_ActionList_Sleep"
    }
}
```

---

## Groups

Groups define named collections of NPC roles, referenced elsewhere (attitudes, flock filters, spawn filters). Found in `Server/NPC/Groups/`. The file name is the group name. Group files have no `Type` field; they directly contain an `IncludeRoles` array. Role names may use trailing-wildcard patterns (`Fox*`). An `ExcludeRoles` array is supported but rarely used.

### Group Definition

**Example: `Groups/Predators.json`**

```json
{
    "IncludeRoles": [
        "Fox*",
        "Hyena*",
        "Fen_Stalker",
        "Spark*",
        "Toad*"
    ]
}
```

Plain role names (without a wildcard) match a single role, while a name ending in `*` matches every role sharing that prefix.

---

## Flocks

Flocks configure how many NPCs spawn together. Found in `Server/NPC/Flocks/`. Real flock files use `"Type": "Weighted"`, a `MinSize`, and a flat `SizeWeights` array. Each weight corresponds to a size starting at `MinSize`: the first weight is for `MinSize`, the second for `MinSize + 1`, and so on. Weights are relative.

### Weighted Sizes

**Example: `Flocks/Group_Small.json`** (sizes 3, 4, 5 with weights 60/25/15)

```json
{
    "Type": "Weighted",
    "MinSize": 3,
    "SizeWeights": [ 60, 25, 15 ]
}
```

An optional `MaxGrowSize` caps how large a flock may grow over time:

**Example: `Flocks/Parent_And_Young_75_25.json`**

```json
{
    "Type": "Weighted",
    "MinSize": 1,
    "SizeWeights": [ 75, 25 ],
    "MaxGrowSize": 8
}
```

---

## Spawn Beacons

Spawn beacons configure where and how NPCs spawn in the world. Found in `Server/NPC/Spawn/Beacons/`. A beacon is a plain object (no `Type` wrapper). NPC entries in the `NPCs` array reference roles by an `Id` field, not `Role`.

### Beacon Properties

| Property | Type | Description |
|----------|------|-------------|
| `Environments` | Array | Biome/environment filters (e.g. `Env_Zone1_Caves_Volcanic_T1`) |
| `MinDistanceFromPlayer` | Number | Minimum player distance for spawning |
| `MaxSpawnedNPCs` | Number | Maximum concurrent spawns |
| `ConcurrentSpawnsRange` | Array | `[min, max]` NPCs spawned per cycle |
| `SpawnAfterGameTimeRange` | Array | `[min, max]` game-time durations before spawning (e.g. `PT20M`) |
| `NPCSpawnState` | String | State the NPC starts in when spawned |
| `SpawnRadius` | Number | Spawn area radius |
| `BeaconRadius` | Number | Beacon activation radius |
| `NPCs` | Array | NPC spawn entries (`Id`, `Weight`, optional `SpawnBlockSet`) |
| `LightRanges` | Object | Light level requirements (`Light: [min, max]`) |
| `Weight` | Number | Per-entry spawn weight |

### Beacon Example

**Example: `Spawn/Beacons/Zone1/Zone1_Cave_Tier1/Zone1_Cave_Volcanic_T1_Goblin.json`**

```json
{
    "Environments": [ "Env_Zone1_Caves_Volcanic_T1" ],
    "MinDistanceFromPlayer": 15,
    "MaxSpawnedNPCs": 2,
    "ConcurrentSpawnsRange": [ 1, 2 ],
    "SpawnAfterGameTimeRange": [ "PT20M", "PT60M" ],
    "BeaconRadius": 70,
    "SpawnRadius": 50,
    "NPCs": [
        { "Weight": 75, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Scrapper" },
        { "Weight": 15, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Lobber" },
        { "Weight": 5, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Hermit" },
        { "Weight": 5, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Miner" }
    ],
    "LightRanges": {
        "Light": [ 0, 7 ]
    }
}
```

A minimal beacon can also start an NPC in a chosen state:

```json
{
    "Environments": [],
    "NPCs": [
        { "Weight": 1, "Id": "Edible_Goblin_Scrapper" }
    ],
    "SpawnAfterGameTimeRange": [ "PT5M", "PT10M" ],
    "NPCSpawnState": "Seek"
}
```

### Zone-Based Organization

Spawn beacons are organized by zone (`Zone1` through `Zone4`), with subfolders by tier and biome, plus `Portals` and `Tests` directories:

```
Server/NPC/Spawn/Beacons/
├── Zone1/
│   ├── Zone1_Cave_Tier1/
│   ├── Zone1_Cave_Tier2/
│   └── ...
├── Zone2/
├── Zone3/
├── Zone4/
├── Portals/
└── Tests/
```

---

## Combat Action Evaluator (CAE)

The CAE system provides intelligent combat decision-making. Found in `Server/NPC/Balancing/`. A role references its CAE through the `_CombatConfig` field (see the Goblin Scrapper variant above).

### CAE Structure

A CAE file has `"Type": "CombatActionEvaluator"` at the top and wraps its evaluation logic in a nested `CombatActionEvaluator` object. That object holds:

- `RunConditions`: conditions that gate whether the evaluator runs at all.
- `MinRunUtility` / `MinActionUtility`: utility thresholds.
- `AvailableActions`: an object keyed by action name. Each action has a `Type` (commonly `Ability`), a `Target`, an `Ability` reference, an `AttackDistanceRange`, optional `InteractionVars`/`ChargeFor`/`WeaponSlot`/`SubState`, and a `Conditions` array.
- `ActionSets`: an object keyed by set name (not an array). Each set defines `BasicAttacks` and an `Actions` list of available action names.

```json
{
    "Type": "CombatActionEvaluator",
    "TargetMemoryDuration": 5,
    "CombatActionEvaluator": {
        "RunConditions": [
            {
                "Type": "TimeSinceLastUsed",
                "Curve": { "ResponseCurve": "Linear", "XRange": [ 0, 5 ] }
            },
            { "Type": "Randomiser", "MinValue": 0.9, "MaxValue": 1 }
        ],
        "MinRunUtility": 0.5,
        "MinActionUtility": 0.01,
        "AvailableActions": {
            "Melee": {
                "Type": "Ability",
                "WeaponSlot": 0,
                "SubState": "Default",
                "Ability": "Goblin_Scrapper_Attack",
                "Target": "Hostile",
                "AttackDistanceRange": [ 2.5, 2.5 ],
                "Conditions": [
                    {
                        "Type": "TimeSinceLastUsed",
                        "Curve": { "ResponseCurve": "Linear", "XRange": [ 0, 1 ] }
                    }
                ]
            },
            "Ranged": {
                "Type": "Ability",
                "WeaponSlot": 0,
                "SubState": "Ranged",
                "Ability": "Goblin_Scrapper_Rubble_Throw",
                "Target": "Hostile",
                "AttackDistanceRange": [ 15, 15 ],
                "Conditions": [
                    {
                        "Type": "TargetDistance",
                        "Curve": { "ResponseCurve": "SimpleLogistic", "XRange": [ 0, 15 ] }
                    }
                ]
            }
        },
        "ActionSets": {
            "Default": {
                "BasicAttacks": {
                    "Attacks": [ "Goblin_Scrapper_Attack" ],
                    "MaxRange": 2.5,
                    "Timeout": 0.5,
                    "CooldownRange": [ 0.001, 0.001 ]
                },
                "Actions": [ "SwingDown", "Ranged" ]
            }
        }
    }
}
```

### Response Curves

Conditions evaluate an input through a `Curve` object whose `ResponseCurve` selects the shape:

| Response Curve | Description |
|----------------|-------------|
| `Linear` | Direct proportion across `XRange` |
| `InverseExponential` | Exponential falloff |
| `SimpleLogistic` | Ascending S-curve |
| `SimpleDescendingLogistic` | Descending S-curve |

A few test files instead use a bare `"Curve": "ReverseLinear"` string, or a `"Type": "Switch"` curve with a `SwitchPoint` for step-function behavior.

### Condition Types

Conditions (in both `RunConditions` and per-action `Conditions`) use a `Type`. Common types:

| Condition Type | Description |
|----------------|-------------|
| `TimeSinceLastUsed` | Time elapsed since the action last ran |
| `TargetDistance` | Distance to the current target |
| `Randomiser` | Random value between `MinValue` and `MaxValue` |
| `OwnStatPercent` / `OwnStatAbsolute` | NPC's own stat as a percentage / absolute value |
| `TargetStatPercent` | Target's stat as a percentage |
| `RecentSustainedDamage` | Damage taken recently |
| `NearbyCount` / `KnownTargetCount` | Counts of nearby/known entities |

---

## Reference Summary

### Key File Locations

| File Type | Path |
|-----------|------|
| Core Templates | `Server/NPC/Roles/_Core/Templates/` |
| Creatures | `Server/NPC/Roles/Creature/` |
| Intelligent | `Server/NPC/Roles/Intelligent/` |
| Attitudes | `Server/NPC/Attitude/Roles/` |
| Spawn Beacons | `Server/NPC/Spawn/Beacons/` |
| Combat Balance | `Server/NPC/Balancing/` |
| Groups | `Server/NPC/Groups/` |
| Flocks | `Server/NPC/Flocks/` |

### Asset Statistics

| Category | Count | Description |
|----------|-------|-------------|
| Total Roles | 952 | NPC role definitions (templates + variants) |
| Templates (`Template_*`) | 51 | Abstract base templates (13 in `_Core/Templates/`) |
| Attitude Files | 26 | Relationship definitions (`Attitude/Roles/`) |
| Group Files | 70 | NPC role collections |
| Flock Files | 8 | Flock size configurations |
| Spawn Beacons | 75 | Spawn configurations |
| CAE Files | 28 | Combat balancing |

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 NPC role/spawn loader (verified against `HytaleServer.jar`).

- **`Unable to spawn entity with invalid role index`** → a spawn beacon `NPCs` entry references a role `Id` that does not resolve to a loaded role. Fix: the `Id` must match an existing variant's name exactly (case-sensitive), e.g. `Goblin_Scrapper`.
- **`attempted to spawn invalid NPC role`** → a spawn marker named a role that failed to load or doesn't exist. Fix: confirm the referenced role file is present under `Server/NPC/Roles/` and validated.
- **`Cannot have more than one combat state in an NPC`** → a role's `Instructions`/state machine declares more than one combat state. Fix: keep a single combat state per role.
- **`No such state for combat evaluator`** → a CAE `ActionSets`/`SubState` references a state that the role does not define. Fix: every CAE state/sub-state must correspond to a state used by the role's `Instructions`.
- **Symptom:** a `Variant` ignores its `Reference` template's values → the `Reference` short name didn't resolve, or you put `{Value, Description}` objects in `Modify`. Fix: reference the template by its exact short name, and in `Modify` use plain values (the `{Value, Description}` form belongs only in a template's `Parameters` block).
- **Symptom:** a `Compute` expression evaluates to nothing/default → the named parameter isn't declared in any `Parameters` block up the template chain. Fix: declare the parameter (in the template or an overriding variant `Parameters` block) before reading it with `{ "Compute": "..." }`.

---
