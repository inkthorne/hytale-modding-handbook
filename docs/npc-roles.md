---
title: "NPC Roles"
description: "Define Hytale NPC roles in JSON — abstract Template and concrete Variant roles, a Parameters/Compute system, attitude definitions between groups, and groups and flocks for spawning, plus driving the engine flock and marked combat targets from Java at runtime."
seo:
  type: TechArticle
---

# NPC Roles

**Doc type:** Java API + JSON asset format · **Assets:** `Server/NPC` · **Verified against 0.6.3**

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
| `Server/NPC/Roles/` | 1,000 NPC role definitions (templates and variants) |
| `Server/NPC/Attitude/` | Relationship definitions between NPC groups |
| `Server/NPC/Groups/` | NPC group collections for spawning |
| `Server/NPC/Flocks/` | Flock size configurations |
| `Server/NPC/Spawn/` | Spawn configuration — `Beacons/` (ambient spawning), `Markers/` (worldgen / prefab spawn markers), `World/`, `Suppression/`, `CompanionBlockSpawners/` ([companion block spawners](#companion-block-spawners)) |
| `Server/NPC/Balancing/` | Combat Action Evaluator (CAE) files |
| `Server/NPC/DecisionMaking/` | AI decision conditions |

---

## Role Types

A role's top-level `Type` is one of three values registered by the role `BuilderFactory`:

| `Type` | Spawnable | Description |
|--------|-----------|-------------|
| `Abstract` | No | Template/base; concrete roles inherit from it via `Reference` |
| `Variant` | Yes | Concrete role referencing a template, overriding via `Modify` |
| `Generic` | Yes | Concrete, **self-contained** role that defines its behavior inline (the type the engine's own `Test_*` roles use) |

Those three are the **only** top-level role types — `NPCPlugin` registers exactly `Generic` → `BuilderRole`, `Abstract` → `BuilderRoleAbstract`, `Variant` → `BuilderRoleVariant`. `"Type": "Role"` is **not** a role type: it is the role-change *action* (`BuilderActionRole`, see [Actions](#actions)), which is why it turns up inside `Actions` arrays in files like `Template_Animal_Neutral.json`.

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
| `Template_Spirit` | Spirit/ethereal base — **moved to `_Core/Templates/Deprecated/` as of 0.6.3** (alongside `Template_Eye` and `Template_Scarak_Seeker`) |
| `Template_Birds_Passive` | Flying passive bird behavior |
| `Template_Swimming_Passive` | Passive swimming creature base |
| `Template_Swimming_Aggressive` | Aggressive swimming creature base |
| `Template_Edible_Critter` | Small edible critter base |
| `Template_Beasts_Passive_Critter` | Passive beast critter base |
| `Template_Summoned_Ally` | Summoned allied NPC base |
| `Template_Beasts_Passive_Cactee` | Passive cactus-creature base |
| `Template_Flying_Aggressive` | Aggressive flier base (the `Fly` motion-controller exemplar) |
| `Template_Temple` | Temple/structure guard base |

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

**Reserved keys inside `Modify`.** Every key under `Modify` is treated as *a role parameter to set* — **except** five reserved names that `BuilderModifier` handles structurally. They are the only `_`-prefixed keys the block accepts:

| Key | Purpose |
|-----|---------|
| `_CombatConfig` | The CAE asset for this role (the top-level, non-`Modify` spelling of the same field is `CombatConfig`). |
| `_InteractionVars` | Interaction-var overrides (top-level spelling: `InteractionVars`) — see [Melee attacks without a CAE](#melee-attacks-without-a-cae). |
| `_ExportStates` | Maps a referenced component's states onto this role's states. Must be a JSON array; illegal inside `_ForwardedModifiers`. |
| `_InterfaceParameters` | Parameters passed to the referenced construct's interface. |
| `_ForwardedModifiers` | Modifiers forwarded down to nested references. |

Anything else — including `$Comment` — is looked up as a parameter and throws `Parameter <name> does not exist or is private` if there is none (see [Gotchas](#gotchas--errors)).

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

> **Engine keys vs template parameters.** Only some of the names below are read directly by the role builder. `BuilderRole` reads 81 keys (`Appearance`, `MaxHealth`, `DropList`, `NameTranslationKey`, `MotionControllerList`, `Instructions`, `InteractionVars`, `CombatConfig`, `IsMemory`, `MemoriesCategory`, `Invulnerable`, `Armor`, `HotbarItems`, the whole `Separation*`/`Avoidance*`/`Collision*`/`Flock*` families, …) and `SupportConfigBuilder` reads a further ten (`StartState`, `DefaultSubState`, `AttitudeGroup`, `ItemAttitudeGroup`, `DefaultPlayerAttitude`, `DefaultNPCAttitude`, `BusyStates`, `DisableDamageFlock`, `DisableDamageGroups`, `Debug`). Everything else in the tables below — `Scale`, `MaxSpeed`, `WanderRadius`, `ClimbHeight`, `ViewRange`, `ViewSector`, `HearingRange`, `AbsoluteDetectionRange`, `Attack`, `AttackDistance`, `DayTimePeriod`, `FlockArray`, `IsTameable`, … — is a **template `Parameters` entry** that the template's own `Compute` expressions feed into a real key or component. That is why a `Variant` can set them from `Modify` even though no builder declares them, and why a `Generic` role that invents its own must declare them in `Parameters` first.

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
| `JumpHeight` | Number | Vertical jump capability (a `Walk` motion-controller key, not a role key) |
| `ApplySeparation` | Boolean | Soft spacing so NPCs don't overlap — see [Separation & avoidance steering](#separation--avoidance-steering) |
| `ApplyAvoidance` | Boolean | Predictive collision avoidance — see [Separation & avoidance steering](#separation--avoidance-steering) |

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
| `CombatConfig` / `_CombatConfig` | String | CAE file name for intelligent combat (e.g. `CAE_Goblin_Scrapper`). `CombatConfig` at a role's top level; `_CombatConfig` inside a `Variant`'s `Modify` |

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

**Example: `Attitude/Roles/Prey.json`** — prey treat predators as threats (which is what drives their detection/flee branches) and ignore each other:

```json
{
    "Groups": {
        "Hostile": [ "Predators", "PredatorsBig", "Void" ],
        "Ignore": [ "Prey", "PreyBig", "Critters", "Vermin" ]
    }
}
```

**Example: `Attitude/Roles/Predators.json`** — predators are merely `Neutral` toward prey (hunting is driven by the role's own instructions, not by a `Hostile` attitude):

```json
{
    "Groups": {
        "Neutral": [ "Prey" ],
        "Ignore": [ "Predators", "PreyBig" ]
    }
}
```

The lookup is source-indexed: `AttitudeMap.getAttitude` reads the **acting** NPC's `AttitudeGroup` to pick the file, then looks the **target's** role up inside it. So `Prey.json` says how a *prey* NPC feels about others.

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
| `Hedera.json` | Standalone aggressive plant-creature role |

**Neutral Factions:**

| Faction | Description |
|---------|-------------|
| `Feran/` | Beast-folk traders |
| `Kweebec/` | Small forest dwellers |
| `Tuluk/` | Nomadic traders |
| `Bramblekin*.json` | Standalone neutral bramble folk |

There is also an `Intelligent/Passive/` directory alongside `Aggressive/` and `Neutral/`.

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

Motion controllers define how NPCs move through the world. They are listed in `MotionControllerList`. Three controller types appear in real role files (counts are `MotionControllerList` entries across `Server/NPC/Roles/`):

| Controller | Usage | Description |
|------------|-------|-------------|
| `Walk` | 357 | Ground-based movement (`MotionControllerWalk`) |
| `Fly` | 19 | Aerial movement (`MotionControllerFly`) |
| `Dive` | 5 | Swimming/diving movement (`MotionControllerDive`) — *"Provide diving abilities for NPC"* |

Many controller fields accept `{ "Compute": "..." }` so they can read template parameters.

### Walk Configuration Example

From `Template_Animal_Neutral` (abridged — the shipped block also carries `DescentAnimationType`, `DescentSteepness`, `DescentBlending` and `JumpDescentSteepness`):

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

## Separation & avoidance steering

Two **independent** role-level steering forces keep NPCs from piling up. Both are off by default, both are toggled by their own boolean key, and both are applied per-tick by `com.hypixel.hytale.server.npc.systems.AvoidanceSystem`, which blends each into the NPC's body steering after the behaviour tick. **Neither is a flocking feature** — they act on solo, un-flocked NPCs and push against *any* nearby entity regardless of role or flock. This answers the common question *"why do my rats space out while my chickens walk through each other?"*: the rats' role sets `ApplySeparation: true`; the chickens' role omits it (it defaults `false`).

| Force | Key (default) | What it does |
| --- | --- | --- |
| **Separation** | `ApplySeparation` (`false`) | Soft positional spacing — sums the offsets to neighbours within `SeparationDistance` and nudges the NPC away so bodies don't overlap. |
| **Avoidance** | `ApplyAvoidance` (`false`) | Predictive collision avoidance — projects velocities and steers around an entity on a collision course (brake or sidestep). |

> The getter for `ApplyAvoidance` is `Role.isAvoidingEntities()` (**not** `isApplyAvoidance`); `ApplySeparation`'s getter is `Role.isApplySeparation()`. Every `Separation*` / `Avoidance*` key in this section is flagged **Experimental** in `BuilderRole` (the neighbouring `Collision*` keys are a mix of `Stable` and `Experimental`).

### Neighbour scope (who gets pushed)

The neighbour set for both forces comes from the NPC's own `com.hypixel.hytale.server.npc.role.support.PositionCache`, filtered by **distance only** — there is **no role filter and no flock filter**. Enabling `ApplySeparation` registers the separation radius against both the cache's NPC list (`requireEntityDistanceAvoidance`) *and* its player list (`requirePlayerDistanceAvoidance`), so an NPC separates from **nearby NPCs and players alike**. Whether a player counts is decided by `EntityDetectionUtil.isDetectableByNPCs`: anything carrying `Intangible` is skipped, a **spectating** player is skipped, and a **Creative** player counts only when their creative settings have `allowNPCDetection` enabled — every other player counts. The NPC's current combat target is excluded — it sits in the role's `ignoredEntitiesForAvoidance` set (via `MarkedEntitySupport`) — so an NPC still closes on the thing it is attacking.

### Separation keys

`ApplySeparation` enables a soft spacing force toward a desired `SeparationDistance`. That distance can **tighten as the NPC nears its current target**, so a pack swarms a target without bouncing off each other:

| Key | Default | Description |
| --- | --- | --- |
| `ApplySeparation` | `false` | Apply the separation steering force. |
| `SeparationDistance` | `3.0` | Desired spacing between this NPC and others. |
| `SeparationWeight` | `1.0` | Blend factor for the summed-distance force. |
| `SeparationMode` | `Legacy` | Calculation mode — `Legacy` or `Push` (`Role$SeparationMode`). |
| `SeparationDistanceTarget` | `1.0` | Desired (tighter) spacing when close to the current target. |
| `SeparationNearRadiusTarget` | `1.0` | At/under this distance to the target, use `SeparationDistanceTarget`. |
| `SeparationFarRadiusTarget` | `5.0` | Past this distance to the target, use the normal `SeparationDistance`; between the two radii the engine lerps. |

`SeparationMode` (`com.hypixel.hytale.server.npc.role.Role$SeparationMode` = `Legacy` | `Push`, default `Legacy`) selects the force model:

- **`Legacy`** — sums normalized offset vectors from neighbours into one steering nudge scaled by `SeparationLegacySteeringStrength` (default `0.5`). The target-distance falloff (the `…Target` trio above) is a Legacy feature. Pushes even a resting NPC once neighbours are in range.
- **`Push`** — a per-neighbour push with a distance-falloff exponent (`SeparationPushDistanceWeightDefault`, made sharper near a motion target via `SeparationPushDistanceWeightTarget` / `…Attacker`), steering strength `SeparationPushSteeringStrength` (default `0.8`), and small-speed scaling `SeparationPushSpeedScale`. It is target-aware through the active BodyMotion's desired target and `SeparationPushSafeDistanceMultiplier`. Common in vanilla combat/livestock roles. A **resting** NPC is *not* pushed in Push mode unless `SeparationOverrideAlwaysSeparate` is set.

Push-mode-only tuning knobs (all Experimental, with sensible defaults): `SeparationPushSafeDistanceMultiplier` (`0.8`), `SeparationPushSteeringStrength` (`0.8`), `SeparationPushDistanceWeightDefault` (`1.0`), `SeparationPushDistanceWeightTarget` (`8.0`), `SeparationPushDistanceWeightAttacker` (`8.0`), `SeparationPushSpeedScale` (`0.5`). Three tri-state overrides apply to either mode: `SeparationOverrideOrientation` (turn the NPC to face its separation direction), `SeparationOverrideAlwaysSeparate` (separate even when the NPC would otherwise rest), and `SeparationOverrideNormalizeDistances`.

### Avoidance keys

`ApplyAvoidance` is the *other*, distinct force — predictive collision avoidance rather than positional spacing:

| Key | Default | Description |
| --- | --- | --- |
| `ApplyAvoidance` | `false` | Apply the avoidance steering force (getter `Role.isAvoidingEntities()`). |
| `AvoidanceMode` | `Any` | Manoeuvre set — `Slowdown`, `Evade`, or `Any` (`Role$AvoidanceMode`). |
| `EntityAvoidanceStrength` | `1.0` | Blend factor for the avoidance force. |

`AvoidanceMode` (`com.hypixel.hytale.server.npc.role.Role$AvoidanceMode`): **`Slowdown`** brakes to let the obstacle pass, **`Evade`** steers around it, and **`Any`** (default) lets the engine pick. The probe distance and collision shape are tuned by the adjacent `CollisionDistance` / `CollisionRadius` / `CollisionForceFalloff` / `CollisionViewAngle` keys. (`AvoidanceFallCheck` is a deprecated no-op kept only for backwards compatibility — don't use it.)

### Minimal example

A role that spaces out from its neighbours needs only the toggle plus a distance; everything else defaults:

```json
{
    "ApplySeparation": true,
    "SeparationDistance": 3,
    "SeparationMode": "Push"
}
```

Two roles identical except for `ApplySeparation` behave exactly as the rats-vs-chickens question describes — the one with it set spaces out, the one without it overlaps. Vanilla isolates this in `Server/NPC/Roles/_Core/Tests_Development/Test_Separation_*.json`: `Test_Separation_Stationary.json` is the snippet above verbatim, and `Test_Separation_Maintain.json` / `…_Flee.json` / `…_Wander.json` exercise it under different motions. For a production example, `Template_Livestock.json` drives the distance through a parameter:

```json
"ApplySeparation": true,
"SeparationDistance": { "Compute": "SeparationDistance" },
"SeparationWeight": 1,
"SeparationDistanceTarget": { "Compute": "SeparationDistance" },
"SeparationNearRadiusTarget": 2,
"SeparationFarRadiusTarget": 7
```

> **Not the same as flock separation.** The boids-style flock steering (`FlockWeightSeparation`, `FlockWeightAlignment`, `FlockWeightCohesion`, ranged by `FlockInfluenceRange` and gated by actual flock membership) is a **separate** force that acts **only among flock-mates** — see [Flocks](#flocks). `ApplySeparation` is flock-independent. So *"do only same-flock NPCs avoid each other?"* → **no** for `ApplySeparation`, **yes** for `FlockWeightSeparation`. The `/npc debug` flag `VisSeparation` visualizes the `ApplySeparation` force, **not** the flock force (`VisFlock` shows flock-member connections).

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
| `Target` | A valid target exists in a [marked slot](#marked-targets-lockedtarget-and-the-target-sensor) within range (no line-of-sight required) |
| `Damage` | Received damage (optionally `"Combat": true`) |
| `Mob` | Other NPCs nearby (with `Filters`) |
| `Leash` | Distance from home exceeds `Range` |
| `Time` | Time of day within `Period` |
| `Block` / `DroppedItem` | Nearby block set or dropped items |
| `Beacon` / `Alarm` / `Timer` | Flock beacons, alarms, named timers (see [Alarms](#alarms-setalarm--alarm)) |
| `Flag` | Tests a per-NPC boolean (see [Flags](#flags-setflag--flag)) |

### Actions

Each entry in `Actions` is an object whose `Type` is the action. Common action types:

| Action Type | Description |
|-------------|-------------|
| `State` | Change AI state (`{ "Type": "State", "State": "Alerted" }`) |
| `PlayAnimation` | Trigger an animation in a slot |
| `Attack` | Execute the configured attack (params + behavior in [The `Attack` action](#the-attack-action)) |
| `JoinFlock` | Join a nearby flock |
| `Timeout` | Wait for a `Delay` (optionally run a nested `Action`) |
| `SetAlarm` / `TimerStart` | Schedule alarms and timers (see [Alarms](#alarms-setalarm--alarm)) |
| `SetFlag` | Write a per-NPC boolean (see [Flags](#flags-setflag--flag)) |
| `OverrideAttitude` | Temporarily change attitude toward a target |
| `Role` | **Change the NPC's role** (`BuilderActionRole`): `Role` (required, must resolve), `ChangeAppearance` (`true`), `State`, `DetachFromSpawning` (`false`). This is the only meaning of `"Type": "Role"` — see [Role Types](#role-types). |
| `Nothing` | No-op |

**Encounter actions live on their own page.** The encounter-manager plugin registers a further set of NPC actions — `SignalWorldEvent`, `SetEncounterBossBar`, `ClearEncounterBossBar`, `StartEncounterMusic`, `StopEncounterMusic`, `SetEncounterAudioState`, `ChangeTargetRole`, `SetTargetNPCInvulnerable` and the `EncounterMembers` sensor collector — plus the `TriggerSpawners` action (`server.npc.corecomponents.world.ActionTriggerSpawners`, new in 0.6.3). They are usable in any role's `Actions` array, but are documented in **[encounters.md](encounters.md)** rather than duplicated here.

### BodyMotion

A node's `BodyMotion` is an object with a `Type`. NPC locomotion is a **steering-force** system: each motion is a concrete Java class (mostly under `com.hypixel.hytale.server.npc.corecomponents.movement`, with a few in `combat`, `utility`, `timer` and `debug`). The full built-in set:

> **The JSON `Type` is the *registered* name, which for two motions differs from the class name.** `"Type": "Seek"` builds `BodyMotionFind` and `"Type": "Flee"` builds `BodyMotionMoveAway` — `"Find"`, `"FindWithTarget"` and `"MoveAway"` are **not** valid `Type` values and appear in no shipped role.

| Motion Type | Class | Description |
|-------------|-------|-------------|
| `Wander` / `WanderInCircle` / `WanderInRect` | `BodyMotionWander*` | Random movement (in place / circle / rectangle) |
| `Seek` | `BodyMotionFind` | Path toward the sensor's target |
| `Flee` | `BodyMotionMoveAway` | Path away from the sensor's target |
| `MaintainDistance` | `BodyMotionMaintainDistance` | Keep a desired distance from target (strafes intermittently) |
| `Land` / `TakeOff` / `Leave` | `BodyMotionLand` / `…TakeOff` / `…Leave` | Flight transitions and despawn-departure |
| `Teleport` | `BodyMotionTeleport` | Teleport to target position |
| `MatchLook` | `BodyMotionMatchLook` | Orient to match a look direction |
| `Charge` / `AimCharge` | `corecomponents.combat.BodyMotionCharge` / `…AimCharge` | Combat charge attacks |
| `Flock` | `BodyMotionFlock` | Boids steering among flock-mates |
| `Nothing` | `corecomponents.utility.BodyMotionNothing` | Explicit no-op (hold still) |
| `Sequence` / `Timer` | `corecomponents.utility.BodyMotionSequence` / `corecomponents.timer.BodyMotionTimer` | Compose or time-slice child motions |
| `TestProbe` | `corecomponents.debug.BodyMotionTestProbe` | Debug movement probe |

`HeadMotion` slots take their own set: `Aim`, `Watch`, `Observe`, `Rotate`, `Sequence`, `Timer`, `Nothing`.

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

### Entity-sensor slots: `Filters`, `Prioritiser`, `Collector`

The two **scanning** entity sensors — `"Type": "Player"` (`SensorPlayer`) and `"Type": "Mob"` (`SensorEntity`), the only two whose builders extend `BuilderSensorEntityBase` — share its full key set: `Range`, `MinRange`, `LockOnTarget`, `Rebind`, `MultiTarget`, `LockedTargetSlot`, `AutoUnlockTarget`, `OnlyLockedTarget`, `IgnoredTargetSlot`, `UseProjectedDistance`, plus three nested slots:

| Key | Holds | Effect |
|-----|-------|--------|
| `Filters` | array of `EntityFilter` objects | Every candidate must pass all filters (`Attitude`, `LineOfSight`, `ViewSector`, `NPCGroup`, `Stat`, `IsDead`, …). |
| `Prioritiser` | one `ISensorEntityPrioritiser` | Picks *which* match wins when several qualify. |
| `Collector` | one `ISensorEntityCollector` | Receives **every** entity the sensor examined, matching or not, and can act on the whole set. |

`Filters` alone is more widely available: `Target` and `Self` extend `SensorWithEntityFilters` and read `Filters` but **not** `Prioritiser` / `Collector`; `Beacon`, `Count` and `Kill` extend plain `SensorBase` and read none of the three.

`Prioritiser` has one built-in implementation, `"Type": "Attitude"` (`SensorEntityPrioritiserAttitude`, *"Prioritises return entities by attitude"*), whose required key is `AttitudesByPriority` — an ordered, duplicate-free array of [attitude values](#attitude-values):

```json
"Sensor": {
    "Type": "Mob",
    "Range": 20,
    "Prioritiser": { "Type": "Attitude", "AttitudesByPriority": [ "Hostile", "Neutral" ] }
}
```

**The `Collector` slot** (`com.hypixel.hytale.server.npc.corecomponents.ISensorEntityCollector`) is the multi-target escape hatch. Under `Server/NPC/` exactly 17 sensor nodes declare one — all `Mob` (15) or `Player` (2), all of them `CombatTargets`; the two `EncounterMembers` uses live in `Server/EncounterManager/`. Its interface is `init` → `collectMatching` / `collectNonMatching` per candidate → `cleanup`, plus `terminateOnFirstMatch()`. That last method is the important one: the built-in `ISensorEntityCollector.DEFAULT` returns `true`, so **a sensor with no collector stops scanning at its first match**; a collector that returns `false` makes the sensor walk every candidate in range, which is how a single sensor feeds a whole group.

```json
"Sensor": {
    "Type": "Player",
    "Range": 30,
    "Collector": { "Type": "EncounterMembers" }
}
```

Two collectors ship:

| `Type` | Class | Purpose |
|--------|-------|---------|
| `CombatTargets` | `builtin.npccombatactionevaluator.corecomponents.CombatTargetCollector` | *"processes matched friendly and hostile targets and adds them to the NPC's short-term combat memory"* — the feed behind the [CAE](#combat-action-evaluator-cae)'s `KnownTargetCount` / target memory. Attached to the shared detection components (`Component_Sensor_Standard_Detection`, `…_Sight*`, `…_Sound*`, `…_Scent_By_Attitude`), so every role referencing those inherits it. |
| `EncounterMembers` | `builtin.encountermanager.npc.EncounterMemberCollector` | Collects the matches into an encounter's member set — see [encounters.md](encounters.md). |

A collector is a first-class registered category (`NPCPlugin` registers a `BuilderFactory` for `ISensorEntityCollector` keyed on `Type`), so a plugin can add its own: the builder extends `BuilderBase<ISensorEntityCollector>` and its `category()` returns `ISensorEntityCollector.class` — register it with the same [`registerCoreComponentType`](#registering-custom-core-components-java) call used for sensors and motions.

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
| `Enabled` / `Continue` / `Tag` / `TreeMode` | — | — | Standard node flags (see the intro above). `TreeMode` (`false`) makes the node and its children behave like a traditional behaviour tree — *"will continue if all child instructions fail"* — and is mutually constrained with `Continue`. |

`Weight` is **not** a field of the Random node itself — it is read from each **direct child** (`Instruction.getWeight()`) to build the weighted map. Equal or absent weights ⇒ uniform.

**Per-tick selection** (`InstructionRandomized.execute`, `dt` = the tick delta):

```
timeout -= dt
if (timeout <= 0 || current == null) {
    current  = weightedMap.get(random())                  // re-roll a branch by Weight
    timeout  = randomRange(ExecuteFor[0], ExecuteFor[1])  // new random window
}
if (current.matches(self, exec, dt, store))               // ← re-checked EVERY tick (exec = ExecutionSupport)
    current.execute()
```

A state change calls `clearOnce()`, which nulls `current` (forcing a re-roll next tick) only when `ResetOnStateChange` is `true`. Two non-obvious consequences:

1. **No `ExecuteFor` ⇒ the pick is permanent.** The default window is `[Double.MAX_VALUE, Double.MAX_VALUE]`, so `timeout` never reaches 0. The builder's own long description: *"One will be selected at random and executed until the NPC state changes."* The only re-roll triggers are then (a) a state change while `ResetOnStateChange` is `true`, or (b) an explicit `ResetInstructions`. **Add `ExecuteFor` for a timed re-roll.**
2. **The chosen branch's `Sensor` is re-evaluated every tick.** If it matched at pick time but stops matching mid-window (e.g. a `Player`-range sensor once the player walks off), the branch does **nothing** for the rest of the window — and the pick is **not** re-rolled; the NPC just idles. Workaround: give the branch a permissive top-level sensor (omit `Sensor`, or `"Type": "Any"`) and push the conditional logic into a nested `Instructions` fallthrough.

#### Timed switch example

This role alternates every 5–12 s between orbiting the nearest player and wandering. The orbit branch is wrapped in `"Sensor": { "Type": "Any" }` with a nested fallthrough so it **wanders instead of freezing** when no player is in range (consequence #2 above). (`Orbit` here is a custom `BodyMotion` the plugin registers — see [Registering custom core components](#registering-custom-core-components-java); for stock-only content, swap in a vanilla motion.)

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
            "BodyMotion": { "Type": "Orbit", "Radius": 2.5, "RelativeSpeed": 0.95 }
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

For a stock-only equivalent, vanilla `Test_Random_Instruction.json` cycles `WanderInCircle` vs `Nothing` the same way.

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

### The `Attack` action

The `Attack` action (`com.hypixel.hytale.server.npc.corecomponents.combat.ActionAttack`, builder `…combat.builders.BuilderActionAttack`) fires a configured attack interaction. It is the action behind the `Attack` row in the [Actions table](#actions), and is the swing in the [melee-without-a-CAE](#melee-attacks-without-a-cae) path.

JSON params (from `BuilderActionAttack`):

| Key | Type | Meaning |
|-----|------|---------|
| `Attack` | string | Attack interaction id (e.g. `Root_NPC_Attack_Melee`). Roles normally pass the role's own field through with `{ "Compute": "Attack" }`. |
| `AttackType` | enum | `Primary` (default) / `Secondary` / `Ability1` / `Ability2` / `Ability3` (`ActionAttack$AttackType`). |
| `AttackPauseRange` | `[min, max]` | Pause **between** attacks — a throttle, in seconds; default `[0, 0]`. **Number array, not strings.** |
| `AimingTimeRange` | `[min, max]` | How long to aim before striking, in seconds; default `[0, 0]`. Number array. |
| `ChargeFor` / `ChargeDistance` | number | Charge-attack windup / distance (both default `0`; `ChargeFor` doubles as how long to block for). |
| `MeleeConeAngle` | number | Cone half-angle the target must be within. |
| `LineOfSight` / `AvoidFriendlyFire` / `DamageFriendlies` / `SkipAiming` | bool | Targeting/aiming toggles. The line-of-sight key is **`LineOfSight`** — there is no `CheckLineOfSight` key. |
| `BallisticMode` | enum | `Short` (default) / `Long` / `Alternate` / `Random` (`ActionAttack$BallisticMode`) — trajectory choice for ballistic attacks. It is an **enum, not a bool**. |
| `InteractionVars` | object | Per-action var overrides for the fired interaction. |

> **The interaction must be tagged as an NPC attack.** `ActionAttack.execute` rejects any resolved interaction whose root is not in `RootInteraction`'s `Attack` tag set, logging *"using interaction … that is not tagged as an 'Attack' usable by NPCs"* and doing nothing. `Root_NPC_Attack_Melee` earns it with `"Tags": { "Attack": [ "Melee" ] }`. If `Attack` is omitted **and** no `Attack` parameter is supplied by the paired sensor, the action falls back to the root interaction the NPC's held item provides for `AttackType` — not to the role's top-level field.

**Behavior (from `ActionAttack.execute`):** the action is effectively **one-shot per completion**. While aiming or not yet on target it returns "not done" — keeping a [blocking action list](#actionlist-blocking-semantics-multi-tick-sequences) parked on it — and once on target it triggers the attack interaction **once** and returns done. `AttackPauseRange` throttles the gap *between* attacks; it is **not** a blocking wait baked into a single call (so `[0, 0]` is fine when re-entry is gated externally).

```json
{ "Type": "Attack", "Attack": { "Compute": "Attack" }, "AttackPauseRange": [ 1, 2 ] }
```

Vanilla reference: the `Flee.Attack` retaliation in `Template_Animal_Neutral.json`.

### Marked targets (`LockedTarget`) and the `Target` sensor

A role can be handed a combat target **directly** — including one it never sensed — by writing the target into a *marked-target slot* and reading that slot back with the `Target` sensor. This is the mechanism behind "one NPC aggros and the whole pack attacks you, even members that can't see you," but it's broadly useful any time you want to make an NPC attack a specific entity from code.

**The slot.** Marked refs live on `MarkedEntitySupport` (`com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport`). **As of 0.6.3 this is an ECS component, not a field on `Role`** — `Role.getMarkedEntitySupport()` no longer exists. Reach it with the static accessor `MarkedEntitySupport.get(ref, accessor)` (or `accessor.getComponent(ref, MarkedEntitySupport.getComponentType())`); inside a sensor/action/motion you already hold an `ExecutionSupport`, which caches it as `ExecutionSupport.getMarkedEntitySupport()`. The default slot name is the constant `MarkedEntitySupport.DEFAULT_TARGET_SLOT`, whose value is `"LockedTarget"`.

**Set it from Java:**

```java
// component-based (0.6.3); `store` is any ComponentAccessor<EntityStore>
MarkedEntitySupport marked = MarkedEntitySupport.get(npcRef, store);
marked.setMarkedEntity(MarkedEntitySupport.DEFAULT_TARGET_SLOT, targetRef);

// or the one-liner on Role, which does exactly the above
npc.getRole().setMarkedTarget(npcRef, store, MarkedEntitySupport.DEFAULT_TARGET_SLOT, targetRef);
```

`setMarkedEntity` has `(String slot, Ref)` and `(int slot, Ref)` overloads, plus 0.6.3's `(slot, Ref, boolean rebind, ComponentAccessor)` forms — passing `rebind = true` records the target's UUID so the slot survives a short reload or a role change (`isRebindSlot` / `resolveRebinds`). Read a slot back with `getMarkedEntityRef(slot)`. There is also `flockSetTarget(selfRef, slot, targetRef, store)` — note the **leading self-ref added in 0.6.3** — which broadcasts the target across the marker's flock `EntityGroup`; convenient, but for *just-joined* members it is unreliable because the group is populated a tick late (see [Flocks at runtime](#flocks-at-runtime-driving-the-engine-flock-from-java)), so setting it per-member is robust.

**Set it from role JSON** — the `SetMarkedTarget` and `ReleaseTarget` actions (registered in `NPCPlugin`) are the JSON equivalents of set/clear:

```json
{ "Type": "SetMarkedTarget", "TargetSlot": "LockedTarget", "Rebind": false }
{ "Type": "ReleaseTarget",   "TargetSlot": "LockedTarget" }
```

Both default `TargetSlot` to `"LockedTarget"`. `SetMarkedTarget`'s `Rebind` (default `false`) is the JSON face of the UUID rebinding above.

**Read it back with the `Target` sensor** (`BuilderSensorTarget` → `SensorTarget`) rather than a fresh `Player`/`Mob` sense:

```json
{ "Type": "Target", "TargetSlot": "LockedTarget", "Range": 24 }
```

`SensorTarget` resolves the slot through the NPC's `MarkedEntitySupport` component (`getMarkedEntityRef(slot)`), so it supplies the marked target's **position with no line-of-sight requirement** — a recruited NPC chases and attacks a target it never detected. `TargetSlot` defaults to `"LockedTarget"`; `Range` (default `Double.MAX_VALUE`) acts as a leash, so omit it for "any distance." Two more keys: `AutoUnlockTarget` (default `false`) clears the slot when the match fails, and `Filters` takes the usual [entity-filter array](#entity-sensor-slots-filters-prioritiser-collector). Driving combat off the `Target` sensor (instead of re-sensing the player each tick) means "engaged" ≈ "has a `Target` within leash," and losing the target — the sensor stops matching — cleanly drives teardown.

### Alarms (`SetAlarm` / `Alarm`)

Alarms are named per-NPC timers. `SetAlarm` arms one; the `Alarm` sensor reads its state.

- **`SetAlarm` action** (`…corecomponents.timer.ActionSetAlarm`): `{ "Type": "SetAlarm", "Name": "<alarm>", "DurationRange": [ "<ISO8601>", "<ISO8601>" ] }`. Re-arms unconditionally to *now + minDuration + random within range*.
- **`Alarm` sensor** (`…corecomponents.timer.SensorAlarm`): `{ "Type": "Alarm", "Name": "<alarm>", "State": "Unset"|"Set"|"Passed", "Clear": false }`. States (enum `SensorAlarm$State`): **`Unset`** = never armed; **`Set`** = armed but not yet elapsed; **`Passed`** = armed and elapsed. Optional `"Clear": true` unsets the alarm when it matches a passed state.

> **⚠️ Gotcha: `DurationRange` is an array of ISO-8601 duration *strings*, not numbers.** e.g. `["PT8S","PT14S"]` (seconds), or the vanilla livestock produce alarm's `["PT6H","PT36H"]` (`ProduceTimeout` in `Template_Animal_Neutral` / `Template_Livestock`, raised to `["PT36H","PT48H"]` by `Chicken.json` and friends); `["P0D","P0D"]` unsets. The builder's holder type is `TemporalAmount[]` — passing numbers (`[8, 14]`) fails to load with `Expression type mismatch. Got NUMBER_ARRAY but expected STRING_ARRAY`, and the **entire role then silently drops from the spawn list** (see [Gotchas](#gotchas--errors)). This is specific to alarm durations: number arrays *are* correct for `Timeout.Delay`, `AttackPauseRange`, `AimingTimeRange`, `ExecuteFor`, and `TimerStart` ranges.

**Spawn-init idiom** — run an action exactly once when an NPC spawns, by matching only the initial `Unset` state (mirrors `Template_Animal_Neutral`'s `Produce_Ready` alarm):

```json
{ "Sensor": { "Type": "Alarm", "Name": "X", "State": "Unset" },
  "Actions": [ { "Type": "SetAlarm", "Name": "X", "DurationRange": [ "PT0S", "PT1S" ] } ] }
```

### Flags (`SetFlag` / `Flag`)

Flags are per-NPC booleans. The `Flag` sensor tests one; the `SetFlag` action writes one.

- **`Flag` sensor** (`…corecomponents.utility.SensorFlag`): `{ "Type": "Flag", "Name": "<flag>", "Set": true|false }` — tests the flag. Omitting `Set` tests for `true`.
- **`SetFlag` action** (`…corecomponents.utility.ActionSetFlag`): `{ "Type": "SetFlag", "Name": "<flag>", "SetTo": true|false }` — writes the flag.

> **⚠️ Asymmetric keys:** the sensor reads with **`Set`**, the action writes with **`SetTo`**. Easy to mix up.

**Transition detection** — flags give you a clean "do X once when switching from mode A to mode B" without a full state machine: branch A raises a flag while active; branch B, on the tick it takes over, sees the flag still set, fires one action, and clears it. Vanilla refs: `_Core/Tests/Test_Flags.json` (toggles a flag on each `Damage`), `Template_Predator.json`, `Component_Instruction_Combat_Flock_Take_Turns.json`.

> **Note:** `SetFlag` also appears in [the world/interaction docs](world.md) as a different surface (world/block flags); the NPC-role flag sensor/action documented here are the `corecomponents.utility` pair.

### `ActionList` blocking semantics (multi-tick sequences)

When an instruction node sets **`"ActionsBlocking": true`** (`com.hypixel.hytale.server.npc.instructions.ActionList`):

- The action list becomes a **stateful sequence that spans ticks**: it keeps an `actionIndex`, executes `actions[actionIndex]`, and **advances only when an action returns `true`** (done). An action returning `false` parks the list on it. The list reports itself done only when the last action completes.
- **Non-blocking** (`ActionsBlocking` absent/false): it fires **all** actions every tick — no index, no advancement.
- The sibling flag **`ActionsAtomic`** (default `false`) is the all-or-nothing variant: *"only execute actions if all actions can be executed."*

So a blocking `[PlayAnimation, Timeout 0.6, Attack, PlayAnimation, SetFlag]` runs **in order across ticks**: the `Timeout` parks the list while it counts, the [`Attack`](#the-attack-action) parks it while aiming then strikes once, and the trailing cleanup/flag-clear actions run exactly once at the end. This is the standard shape for composing windup → attack → cleanup.

---

## Registering custom core components (Java)

> **Looking for the built-in `Mount` core component?** It is documented with the rest of the
> mount system in [mounts.md](mounts.md#mount-npc-action). Note the name is overloaded three
> ways in `MountPlugin.setup()` alone — an NPC core component, an ECS component name, and an
> interaction `Type` — so `"Type": "Mount"` means different things in a role's `Instructions`
> than it does in an item's interaction chain. Both shapes are shown side by side there.

The behavior building blocks referenced by `Type` in role JSON — `BodyMotion`, `HeadMotion`, `Sensor`, `Action`, `EntityFilter` — are concrete Java classes, each with a `Builder*` companion that acts as its JSON codec. A plugin can **register its own** and reference it from role JSON by `Type`, exactly like a built-in.

The core NPC plugin is itself a `JavaPlugin` with a static accessor and a registration method:

```java
// com.hypixel.hytale.server.npc.NPCPlugin
public static NPCPlugin get();
public <T> NPCPlugin registerCoreComponentType(String typeName, Supplier<Builder<T>> builder);
// Category constants naming the factories (all `public static final String` as of 0.6.3):
//   FACTORY_CLASS_ROLE        = "Role"        FACTORY_CLASS_BODY_MOTION = "BodyMotion"
//   FACTORY_CLASS_HEAD_MOTION = "HeadMotion"  FACTORY_CLASS_ACTION      = "Action"
//   FACTORY_CLASS_SENSOR      = "Sensor"      FACTORY_CLASS_INSTRUCTION = "Instruction"
//   FACTORY_CLASS_TRANSIENT_PATH = "Path"     FACTORY_CLASS_ACTION_LIST = "ActionList"
//   ROLE_ASSETS_PATH          = "Server/NPC/Roles"
```

A builder's `category()` decides which slot its `Type` is usable in — `BuilderBodyMotionBase.category()` returns `BodyMotion.class`, so registering a `BuilderBodyMotionX` makes `"Type": "X"` valid in any `BodyMotion` slot. **Sensors and actions register exactly the same way** — only the builder base class (and thus its `category()`) differs. Register in your plugin's `setup()`:

```java
NPCPlugin.get().registerCoreComponentType("Orbit", BuilderBodyMotionOrbit::new);
```

No manifest `Dependencies` entry is needed — the NPC plugin is core and always loads first (and a wrong `group:name` would only *break* your load).

> **⚠️ 0.6.3 signature break: `Role` → `ExecutionSupport` throughout.** Every core-component callback that used to take a `Role` now takes a `com.hypixel.hytale.server.npc.instructions.ExecutionSupport` — `Sensor.matches`, `Action.execute` / `canExecute` / `activate` / `deactivate`, `Motion.computeSteering` / `activate` / `deactivate` / `preComputeSteering`, and `Instruction`'s whole lifecycle (`loaded`/`spawned`/`unloaded`/`removed`/`teleported`/`registerWithSupport`). `ExecutionSupport` is a pooled per-tick handle that caches the NPC's support components: `getRole()`, `getNpcEntity()`, `getStateSupport()`, `getMarkedEntitySupport()`, `getPositionCache()`, `getCombatSupport()`, `getFlagsComponent()`, `getWorldSupport()`, `getEntitySupport()`, `getMotionContextSupport()`, `getDisplayNameSupport()`, `getPlayerTaskSupport()`, `getDebugSupport()`. Outside a callback you can mint one with `Role.acquireExecutionSupport(ref, accessor)`. **A 0.5.9 plugin that overrode any of these will silently fail to override after recompiling — the base method is still there with a different parameter type.**
>
> **Fix: put `@Override` on every core-component callback before you recompile against 0.6.3.** The failure is silent only because the inherited method has a body: `SensorBase.matches` and `ActionBase.canExecute` / `execute` / `activate` / `deactivate` are **concrete** on the base class, and `Motion.preComputeSteering` / `activate` / `deactivate` are interface `default`s — so an old-signature method compiles cleanly as an unrelated overload and simply never runs. With `@Override` present, javac rejects it and points straight at the changed parameter type. (`Motion.computeSteering` is the one abstract callback, and `MotionBase` supplies no body for it, so a stale body-motion fails to compile either way.)

### The custom-`BodyMotion` contract

Locomotion is a **steering-force** system: a motion writes a *desired-movement vector* into a `Steering`, and the engine integrates that with pathing, collision avoidance, and the motion controller. **Do not drive an AI NPC by writing the `Velocity` component each tick** — that fights the locomotion layer. (`Velocity` is for knockback/impulses; see the [Velocity API](entities.md#velocity-api). Continuous AI movement belongs in a `BodyMotion`.)

```java
// Motion side: extends com.hypixel.hytale.server.npc.corecomponents.BodyMotionBase
public BodyMotionX(BuilderBodyMotionX builder, BuilderSupport support) { super(builder); /* read getters */ }

// return false = motion inactive this tick (no target / nothing to do)
public boolean computeSteering(Ref<EntityStore> self, ExecutionSupport exec, InfoProvider info, double dt,
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

### Facing: orientation is emergent from the active motion

There is no single "which way does my NPC face?" setting — **body facing is resolved each tick by the motion controller** from the active `BodyMotion`'s steering (`MotionControllerBase.calculateYaw`). The precedence:

1. If the motion set an **explicit yaw / direction hint** (`Steering.setYaw`, surfaced via `hasYawOrDirection()`), the NPC faces that.
2. Otherwise the controller faces the NPC in its **movement direction** (`PhysicsMath.headingFromDirection` of the translation vector).

So motions split two ways: **face the target** (set an explicit yaw — `MaintainDistance` ends `computeSteering` with `setYaw(targetYaw)`, `WanderInCircle`/`BodyMotionWanderBase` set the walk heading) vs **face travel** (set none — `Flee` (`BodyMotionMoveAway`) and the base pathing motions fall through to the movement-direction default). `Seek` (`BodyMotionFind`) is the hybrid: while it is actually pathing it sets no yaw, but when its path is throttled or deferred it calls `lookAtTarget`, which sets both yaw and pitch onto the target. **Takeaway:** to face the movement direction, set no yaw; to face elsewhere (strafe-and-stare), set `out.setYaw(...)`.

**`HeadMotion` is a separate channel, but not purely cosmetic.** A head motion (`Watch`, `Aim`) writes the head steering, and the controller will *blend the body toward the head* — but only when the body motion left yaw **unset** (`if (!bodySteering.hasYaw())`) **and** the head exceeds the model's camera yaw range (default ±45°). So a head motion can drag the body around on a travel-facing motion, but it **cannot** override a motion that set its own yaw, and small head turns (within ±45°) never move the body. (This is why a melee NPC running `HeadMotion: Aim` over a yaw-setting motion still [whiffs](#melee-hits-are-directional-swept-arcs--npcs-can-miss) — the head turns, the body doesn't.)

**Reusable technique — subclass a motion, override only the yaw.** Engine `BodyMotion`s and their builders are `public`/non-final with a `(builder, support)` constructor and a `public computeSteering`, so you can subclass one, defer to `super` for all its movement logic, and rewrite *just* the facing. This gives "this motion's movement, different facing" without reimplementing it:

```java
public class MyMaintainDistance extends BodyMotionMaintainDistance {   // distinct name — don't clash with the engine class
    private final boolean faceMovementDirection;
    public MyMaintainDistance(MyBuilderMaintainDistance b, BuilderSupport s) {
        super(b, s); this.faceMovementDirection = b.isFaceMovementDirection(s);
    }
    @Override public boolean computeSteering(Ref<EntityStore> ref, ExecutionSupport exec, InfoProvider info, double dt,
                                             Steering steering, ComponentAccessor<EntityStore> acc) {
        boolean active = super.computeSteering(ref, exec, info, dt, steering, acc);   // run vanilla logic first
        if (faceMovementDirection && steering.hasTranslation()) {                     // then overwrite the yaw it set
            Vector3d t = steering.getTranslation();
            steering.setYaw(PhysicsMath.normalizeTurnAngle(PhysicsMath.headingFromDirection(t.x(), t.z())));
        }
        return active;
    }
}
```

The builder mirror `extends BuilderBodyMotionMaintainDistance`; its `readConfig` calls `super.readConfig(data)` then reads the extra field — do **not** also call `readCommonConfig` (the framework already applies the common Enabled/Once config). Register it like any custom motion: `NPCPlugin.get().registerCoreComponentType("MyMaintainDistance", MyBuilderMaintainDistance::new)`. This is also a cleaner fix for the [melee-facing problem](#melee-hits-are-directional-swept-arcs--npcs-can-miss) than a `Seek` windup when you want a strafing motion to still face where it moves.

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
      "BodyMotion": { "Type": "Orbit", "Radius": 2.5, "RelativeSpeed": 0.95 } },
    { "Sensor": { "Type": "Any" }, "BodyMotion": { "Type": "WanderInCircle", "Radius": 6, "RelativeSpeed": 0.25 } }
  ],
  "NameTranslationKey": "server.npcRoles.Foo.name"
}
```

The role id is the **filename without `.json`**. `"Appearance": "Chicken"` reuses a vanilla model by its *referenced* (unprefixed) id. A `BodyMotion`'s `RelativeSpeed` (0..1) scales against the controller's `MaxWalkSpeed`. The first node here uses a custom `Orbit` motion registered via `registerCoreComponentType` (see above); the second is a vanilla fallback.

### Registering a custom sensor

Sensors register through the same `registerCoreComponentType` call as body motions — the builder's `category()` routes the `Type` to the `Sensor` slot instead. The runtime side extends `SensorBase` (`com.hypixel.hytale.server.npc.corecomponents.SensorBase`) and implements `matches` — return `true` when the gate condition holds:

```java
// com.hypixel.hytale.server.npc.corecomponents.SensorBase
public boolean matches(Ref<EntityStore> self, ExecutionSupport exec, double dt, Store<EntityStore> store) {
    // true only for the one flock member that currently holds the attack token
    return holdsAttackToken(self, store);
}
```

You must also implement **`getSensorInfo()`**, which supplies the target the paired `BodyMotion`/`Action` acts on (see [Sensor → BodyMotion target hand-off](#sensor--bodymotion-target-hand-off)). Note that it is declared abstract on the `Sensor` *interface* and is **not** implemented by `SensorBase`, so leaving it out will not compile. A **pure gate** sensor — one that only decides yes/no and provides no target of its own — returns `null` from it, exactly as the built-in `SensorAny` does; pair such a sensor with a target-producing sensor (`Player`, `Target`) via `And` so the node still acquires a target:

```json
{ "Type": "And", "Sensors": [
  { "Type": "Player", "Range": 4, "LockOnTarget": true },
  { "Type": "MyMod_FlockAttackToken" }
] }
```

> **Order matters in `And`.** Its own long description is *"Evaluate all sensors and execute action only when all sensor signal true. **Target is provided by first sensor.**"* — so the target-producing sensor must come **first**; a pure gate listed first would hand the node a `null` target.

The builder extends `BuilderSensorBase` (`com.hypixel.hytale.server.npc.corecomponents.builders.BuilderSensorBase`) and overrides `readConfig(JsonElement)`, `build(BuilderSupport)`, and the description methods. `category()` is inherited from `BuilderSensorBase` and already returns the `Sensor` slot, so you do not override it.

> **⚠️ FATAL TRAP — do NOT call `readCommonConfig(element)` from your `readConfig`.** The framework already applies the common `Enabled` / `Once` sensor config itself; calling `readCommonConfig` again **double-registers** those attributes and the role fails to load with terse errors like `FAIL: <role>.json: Once` and `FAIL: ... Enabled`, followed by `Reloading nonexistent role ...` spam. The engine's own flock-leader sensor builder, `BuilderSensorFlockLeader` (note: under `com.hypixel.hytale.server.flock.corecomponents.builders`, **not** `server.npc`), does **not** call it — its whole `readConfig` declares its requirements (`provideFeature` / `requireInstructionType`) and returns `this`. Yours should do the same: read only your own keys, then `return this`.

Register it in `setup()` exactly like a body motion — the builder's `category()` routes it to the Sensor slot:

```java
NPCPlugin.get().registerCoreComponentType("MyMod_FlockAttackToken", BuilderMyTokenSensor::new);
```

> **Note: track NPC identity with `UUIDComponent`, not a raw `Ref`.** A `Ref<EntityStore>` is a reused `(store, index)` handle with **no stable identity across ticks**. To remember which flock member held the token last tick, read `UUIDComponent.getUuid()` (`com.hypixel.hytale.server.core.entity.UUIDComponent`) and key your bookkeeping on the returned `UUID`.

---

## Components

Reusable behavior components allow shared logic across NPCs. They are referenced by short name with `Reference`, optionally adjusted with `Modify` (whose fields commonly use `{ "Compute": ... }`). Component files live under `Server/NPC/Roles/_Core/Components/` (`Sensors/`, `Steps/`, `ActionLists/`, `Flock/`, `Paths/`, `Selectors/`) and use the prefixes `Component_Sensor_*`, `Component_Instruction_*`, and `Component_ActionList_*`.

A component file declares which slot it fits with a top-level **`"Class"`** (`Sensor`, `Instruction`, or `ActionList`), an optional `"Type": "Component"`, a `Parameters` block, and a `Content` body. Callers override those parameters through `Modify`. Two parameter names are conventions rather than values: **`_ImportStates`** (declared by the component, listing the state names it expects) and **`_ExportStates`** (supplied by the caller in `Modify`, mapping the component's states onto the role's own).

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

Groups define named collections of NPC roles, referenced elsewhere (attitudes, flock filters, spawn filters). Found in `Server/NPC/Groups/`. The file name is the group name. Group files have no `Type` field; they directly contain an `IncludeRoles` array. Role names may use trailing-wildcard patterns (`Fox*`).

The `NPCGroup` codec accepts four keys — `IncludeRoles`, `ExcludeRoles`, and **`IncludeGroups` / `ExcludeGroups`**, which compose one group out of others. In practice 64 of the 72 shipped files use only `IncludeRoles`, and just one uses `ExcludeRoles`.

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

Flocks configure how many NPCs spawn together. Found in `Server/NPC/Flocks/`. There are **two** asset types, and the two shared keys `MaxGrowSize` (default `8` — the cap a flock may grow to *after* spawning) and `BlockedRoles` apply to both:

| `Type` | Class | Sizing keys |
|--------|-------|-------------|
| `Weighted` | `WeightedSizeFlockAsset` | `MinSize` + a flat `SizeWeights` array |
| *(omitted — the default)* | `RangeSizeFlockAsset` | `Size` `[min, max]` |

Seven of the eight shipped files use `"Type": "Weighted"`; `Pack_Small.json` is the lone default-type file and is just `{ "Size": [ 2, 3 ] }`.

For the weighted form, each weight corresponds to a size starting at `MinSize`: the first weight is for `MinSize`, the second for `MinSize + 1`, and so on. Weights are relative.

### Weighted Sizes

**Example: `Flocks/Group_Small.json`** (sizes 3, 4, 5 with weights 60/25/15)

```json
{
    "Type": "Weighted",
    "MinSize": 3,
    "SizeWeights": [ 60, 25, 15 ]
}
```

`MaxGrowSize` caps how large a flock may grow over time. It defaults to `8`, so the one shipped file that spells it out is merely restating the default:

**Example: `Flocks/Parent_And_Young_75_25.json`**

```json
{
    "Type": "Weighted",
    "MinSize": 1,
    "SizeWeights": [ 75, 25 ],
    "MaxGrowSize": 8
}
```

> **Flock *size* vs flock *steering* vs separation.** The files here only size a flock. Separately, a role can carry boids-style flock-steering weights (`FlockWeightSeparation` / `FlockWeightAlignment` / `FlockWeightCohesion`, ranged by `FlockInfluenceRange`) that act **only among flock-mates** — which is distinct from the flock-independent [`ApplySeparation`](#separation--avoidance-steering) spacing force. Don't conflate `FlockWeightSeparation` (flock-only) with `ApplySeparation` (any nearby entity).

---

## Flocks at runtime (driving the engine flock from Java)

The [Flocks](#flocks) configuration above is a **spawn-time** concept: membership is wired by `FlockMembershipSystems` at world-gen / spawn time, and NPCs placed by hand, via the entity menu, or via `/npc spawn` without `--flock` never auto-form a flock (see the [spawn-time note](#spawning-npcs-npc-spawn)). But a plugin can **build, grow, and tear down the same engine flock at runtime** — the basis for *emergent* packs, e.g. lone mobs that wander alone and rally into a pack when one of them aggros. Reusing the engine flock (rather than a hand-rolled grouping) gets you leader succession and cleanup for free, below.

The APIs below are all static, plugin-callable methods under `com.hypixel.hytale.server.flock` (source: `com/hypixel/hytale/server/flock/`).

### Creating a flock

```java
// FlockPlugin
static Ref<EntityStore> createFlock(Store<EntityStore> store, Role role)                          // uses role.getFlockAllowedRoles()
static Ref<EntityStore> createFlock(Store<EntityStore> store, @Nullable FlockAsset def, String[] allowedRoles)
```

`createFlock` is **synchronous**: it builds a holder with a `UUIDComponent`, an empty `EntityGroup`, and a `Flock(def, allowedRoles)`, then `store.addEntity(holder, AddReason.SPAWN)`. The returned flock entity has its `Flock` / `EntityGroup` / `UUIDComponent` immediately — it just has **no members yet**. (The `Flock` component owns the `PersistentFlockData`; the flock entity does **not** carry it as a separate component.)

> **⚠️ A `null` `FlockAsset` means *no* size cap, not the asset default of 8.** `PersistentFlockData` initialises `maxGrowSize` to `Integer.MAX_VALUE` and only overwrites it when a `FlockAsset` is supplied — the `8` default lives on `FlockAsset`, not on `PersistentFlockData`. So the `createFlock(store, role)` / `createFlock(store, null, roles)` paths grow without bound as far as `canJoinFlock` is concerned; cap them yourself, or pass a real `FlockAsset`.

### Recruiting members

```java
// FlockMembershipSystems
static void    join(Ref<EntityStore> memberRef, Ref<EntityStore> flockRef, Store<EntityStore> store)
static boolean canJoinFlock(Ref<EntityStore> memberRef, Ref<EntityStore> flockRef, Store<EntityStore> store)
```

`join` **synchronously** puts a `FlockMembership` (type `JOINING`) on the member, stamped with the flock entity's `UUIDComponent` UUID — so `FlockMembership.getFlockId()` **equals** that UUID and `getFlockRef()` is the flock entity ref, both available the instant `join` returns, before any deferred work. (Because this identity doesn't wait on the `EntityGroup` population below, a `UUID`-keyed map of `flockId → your per-pack state` is safe to build and read in the same tick — unlike anything that reads `EntityGroup`.) A **deferred** system — `FlockMembershipSystems.RefChange`, a `RefChangeSystem` — then adds the member to the flock's `EntityGroup`, promotes the first joiner to `LEADER` and the rest to `MEMBER`, and bumps `PersistentFlockData`. `canJoinFlock` returns `false` if the flock has no `PersistentFlockData`, if `EntityGroup.size() >= maxGrowSize`, or if the member's `NPCEntity.getRoleName()` isn't in the flock's allowed roles. Find candidates to recruit with a radius query — `Selector.selectNearbyEntities(accessor, pos, radius, consumer, predicate)` (see [interactions-combat.md](interactions-combat.md)).

### Queries

- `FlockPlugin.isFlockMember(ref, store)` — does this entity have a `FlockMembership`?
- `FlockPlugin.getFlockReference(memberRef, accessor)` — the flock entity ref for a member.
- `Flock.getFlockData()` → `PersistentFlockData.getMaxGrowSize()`; `EntityGroup.size()` / `isDissolved()` / `getLeaderRef()`; `FlockMembership.getMembershipType()` (`Type` ∈ `JOINING | MEMBER | LEADER | INTERIM_LEADER`).

### Leaving and dissolving

Remove a member's `FlockMembership` — `store.tryRemoveComponent(ref, FlockMembership.getComponentType())`, or the built-in `{ "Type": "LeaveFlock" }` action in role JSON. The same deferred `RefChange` system removes it from the group, **re-elects a leader if the leader left** (via `EntityGroup.testMembers`), and **deletes the flock entity once it drops below 2 members**.

### Leader death is auto-handled

On any flock member's death, `FlockDeathSystems.EntityDeath` removes its `FlockMembership` (unless `role.isCorpseStaysInFlock()`), which triggers leader re-election — `EntityGroup.testMembers(canBecomeLeader)`, gated on `Role.isCanLeadFlock()` — or dissolve. An `INTERIM_LEADER` state covers a leader being temporarily unavailable (e.g. its chunk is unloaded). **So reusing the engine flock gives you succession and cleanup for free** — a strong reason to prefer it over a custom grouping.

Once a pack is formed, propagate the aggro target to every member (including ones that never sensed it) via [Marked targets](#marked-targets-lockedtarget-and-the-target-sensor); to serialize who actually swings, see [Serializing a flock swarm](#serializing-a-flock-swarm--native-take-turns-cant-hard-gate-it).

### Gotcha — a brand-new flock reports 0 members for the rest of the tick

Because `RefChange` is deferred, `createFlock` + `join` do **not** synchronously populate the flock's `EntityGroup`. Within the same tick:

- `EntityGroup.size()` on a brand-new flock returns **0** even after you `join`ed members;
- `canJoinFlock` (which checks `size() >= maxGrowSize`) sees 0 too.

If you decide "is there already a flock for this target?" by member count, every freshly-created flock looks empty — so **every NPC that aggros on the same tick creates its own flock** and the pack overshoots. Fixes:

- **Validate a flock by its `Flock` component, not member count:** `store.getComponent(flockRef, Flock.getComponentType()) != null && !entityGroup.isDissolved()`.
- **Cap pack size with your own counter** (e.g. an `AtomicInteger` in your registry), since the engine's count lags a tick.
- **Get-or-create the per-target flock atomically** (`ConcurrentHashMap.compute`) so simultaneous aggros converge on one flock.

**The lag is symmetric — so plan for refill, not just capping.** A member's *removal* (death or leave) also takes a tick to drop out of `EntityGroup`, so a counter that only counts **up** caps correctly but a pack **never refills** after a death — it just dwindles. To keep a pack topped up, **decrement your counter when a member departs**. Hook death with a `DeathSystems.OnDeathSystem` ([combat.md → Reacting to Death & Respawn](combat.md#reacting-to-death--respawn)), narrowed to flock members with `getQuery() { return FlockMembership.getComponentType(); }`. The dying member **still has its `FlockMembership` when `onComponentAdded` fires** — the engine's own `FlockDeathSystems.EntityDeath` removes membership via a deferred `CommandBuffer`, so your handler runs before that removal applies. Read its `getFlockId()` there (the map key from [Recruiting members](#recruiting-members)) to find the pack and decrement it. The freed slot then refills through your normal recruit path — the next roaming same-role NPC that aggros and runs your `join` logic — and capacity stays exact because the counter, not the laggy group, is the source of truth in **both** directions.

### Gotcha — `FlockPlugin.getFlock` takes a *member* ref, not the flock entity

`FlockPlugin.getFlock(accessor, ref)` reads the **member's** `FlockMembership` to find its flock:

```java
// FlockPlugin.getFlock — abridged
FlockMembership m = accessor.getComponent(reference, FlockMembership.getComponentType());
if (m == null) return null;
return accessor.getComponent(m.getFlockRef(), Flock.getComponentType());
```

A flock **entity** has `Flock` / `EntityGroup` / `UUIDComponent` but **no** `FlockMembership`, so `getFlock(store, flockEntityRef)` always returns `null`. To inspect a flock entity, read its `Flock` component directly. (Combined with the deferred-population gotcha above, this produced "one flock per mob" until both were fixed.) `getFlock` is also `@Deprecated` in the jar — prefer reading `Flock` / `getFlockReference` directly.

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
| `NPCs` | Array | NPC spawn entries — per entry `Id`, `Weight`, and optional `SpawnBlockSet`, `Flock`, `MovementModes`, `SpawnFluidTag`, `EnableSafeSpawning` (`RoleSpawnParameters`) |
| `LightRanges` | Object | Light level requirements (`Light: [min, max]`) |
| `Weight` | Number | Per-entry spawn weight |
| `TargetDistanceFromPlayer` | Number | Preferred distance from the player to place the spawn |
| `NPCIdleDespawnTime` | Number | Seconds an idle spawned NPC survives before despawning |
| `BeaconVacantDespawnGameTime` | String | ISO-8601 game-time duration a vacant beacon keeps its NPCs (e.g. `PT15M`) |
| `TargetSlot` | String | Marked-target slot to pre-fill on the spawned NPC (see [Marked targets](#marked-targets-lockedtarget-and-the-target-sensor)) |

### Beacon Example

**Example: `Spawn/Beacons/Zone1/Zone1_Cave_Tier1/Zone1_Cave_Volcanic_T1_Goblin.json`** (abridged — the shipped file also sets `NPCIdleDespawnTime`, `BeaconVacantDespawnGameTime` and `TargetDistanceFromPlayer`)

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

Spawn beacons are organized by zone (`Zone1` through `Zone4`), with subfolders by tier and biome, plus `Portals` and `Tests` directories and a handful of loose beacons (`Edible_*`, `Goblin_Duke_Phase_*`) at the top level:

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

## Companion Block Spawners

A spawn beacon spawns NPCs from the *environment*. A **companion block spawner** spawns one
from a *player-built structure*: place a designated block, surround it with the blocks a
recipe asks for, and an NPC moves in and stays as long as the setup survives. New in 0.6.3
(`com.hypixel.hytale.builtin.companionblockspawner`).

The codec's own description is the clearest statement of the contract:

> *"A configuration that spawns a companion NPC when a spawner block and all of its required
> surrounding blocks are present within a radius. Requirement blocks are claimed exclusively
> (two spawners can't share one). While the setup holds, the referenced spawn marker keeps the
> companion alive (re-spawning it on death); breaking the setup despawns it."*

### The recipe asset

**Location:** `Server/NPC/Spawn/CompanionBlockSpawners/<Id>.json`
(`CompanionBlockSpawnerRecipe`, loaded after `SpawnMarker`, `BlockSet`, `BlockType` and `Item`)

**`Server/NPC/Spawn/CompanionBlockSpawners/Debug_Companion_Spawner.json`** — one of the two
shipped examples, verbatim:

```json
{
  "SpawnerBlockTypeKey": "Debug_Companion_Block_Spawner",
  "Radius": 6.0,
  "RequiredBlocks": [
    {
      "MatchBy": "Tag",
      "Value": "Bed",
      "Count": 1
    }
  ],
  "SpawnMarker": "Debug_Companion_Kweebec"
}
```

`Debug_Companion_Spawner_Explicit.json` is the same recipe with
`"MatchBy": "BlockId", "Value": "Debug_Companion_Block_Spawner_Requirement"` — the two files
exist to exercise both match modes.

| Key | Type | Description |
|-----|------|-------------|
| `SpawnerBlockTypeKey` | string | **Required, validated.** Block type key of the block that hosts the companion |
| `Radius` | number | **> 0.** Search radius in blocks for the required blocks (default `1.0`) |
| `RequiredBlocks` | array | **Required, non-empty.** The requirement blocks and their counts |
| `SpawnMarker` | string | **Required, validated.** Id of a `Server/NPC/Spawn/Markers/` asset defining the companion |

Each `RequiredBlocks` entry — *"A required block - how it is matched (MatchBy) and the value
to match (Value) - plus the minimum count of it within the recipe radius."*

| Key | Type | Description |
|-----|------|-------------|
| `MatchBy` | enum | **Required.** `BlockId` (exact block type key) or `Tag` (block tag) |
| `Value` | string | The block key, or a tag such as `"Bed"` / `"Family=Crude"` |
| `Count` | integer | **> 0.** Minimum matching blocks within `Radius` (default `1`) |

The four top-level keys are inheritable, so a family of recipes can share a `Parent` template
the way items do (see [items.md](items.md#inheritance-system)).

The referenced marker is an ordinary spawn-marker asset —
`Server/NPC/Spawn/Markers/Debug_Companion_Kweebec.json` is just:

```json
{
  "NPCs": [
    { "Name": "Temple_Kweebec_Static", "Weight": 1, "RealtimeRespawnTime": 30 }
  ],
  "RealtimeRespawn": true,
  "DeactivationDistance": 48
}
```

### How it resolves

1. **Index.** On start (and whenever recipes, or block types, load or unload)
   `CompanionBlockSpawnerRecipeCompendium` rebuilds: it validates every recipe, expands each
   `Tag` entry to the concrete block keys carrying that tag, and drops any recipe whose spawner
   block, required block or spawn marker does not resolve — logging the reason at `SEVERE`.
2. **Component injection.** The plugin then *injects* a `CompanionBlockSpawnerBlock`
   chunk-store component into the `BlockType` of every participating key — the spawner blocks
   **and** the ingredient blocks. **You do not add anything to the block JSON**; naming a block
   in a recipe is what makes it a block entity.
3. **Evaluation.** `CompanionBlockSpawnerSystems.AddOrRemove` reacts to those block entities
   appearing and disappearing, and `ReconcileTick` re-checks each active spawner roughly every
   30 s (jittered ±25 %). Candidates are found through a KD-tree
   (`CompanionBlockSpawnerSpatialSystem`) keyed on block position.
4. **Claiming.** When every `RequiredBlocks` entry is satisfied, the matching blocks are
   claimed by writing the spawner's position into their `ClaimedByBlock` field. Blocks already
   claimed by another spawner are invisible to this one — that is the "claimed exclusively"
   rule.
5. **Marker placement.** `CompanionBlockSpawnerSupport.createMarker` picks a weighted
   configuration from the marker, resolves its NPC role, and searches outward for a spawnable
   tile — rings 1–4 around the spawner, preferring 2 blocks below through the spawner's own
   level before trying 1 block above. It then creates a `SpawnMarkerEntity` carrying a
   `CompanionSpawnerMarkerReference` back to the spawner block, and the normal spawn-marker
   machinery takes over from there.
6. **Teardown.** Breaking the spawner (or enough of the requirement blocks) clears every claim,
   removes the marker, and removes the companions the marker spawned. A `MarkerHeartbeat`
   entity system sweeps up orphaned markers whose origin block is gone or now points at a
   different marker.

### Java surface

```java
// com.hypixel.hytale.builtin.companionblockspawner
static CompanionBlockSpawnerPlugin CompanionBlockSpawnerPlugin.get()

// config.CompanionBlockSpawnerRecipe
static DefaultAssetMap<String, CompanionBlockSpawnerRecipe> getAssetMap()
String getId()
String getSpawnerBlockTypeKey()
double getRadius()
CompanionBlockSpawnerRecipe.RequiredBlock[] getRequiredBlocks()
String getSpawnMarker()

// CompanionBlockSpawnerBlock  (Component<ChunkStore>, on the spawner and ingredient blocks)
static ComponentType<ChunkStore, CompanionBlockSpawnerBlock> getComponentType()
PersistentRef getMarkerRef()
boolean hasMarker()
Vector3i getClaimedByBlock()

// CompanionSpawnerMarkerReference  (Component<EntityStore>, on the marker entity)
static ComponentType<EntityStore, CompanionSpawnerMarkerReference> getComponentType()
Vector3i getSpawnerPosition()
```

`CompanionBlockSpawnerRecipeCompendium` exposes `getEntryKeySets(recipe)`, `getMaxRadius()`
and `isEmpty()` publicly; the compendium instance itself is package-private, so read recipes
through `CompanionBlockSpawnerRecipe.getAssetMap()`.

> **Gotchas**
> - **The spawner block needs no JSON changes.** `Server/Item/Items/_Debug/Debug_Companion_Block_Spawner.json`
>   is a plain crate — no `BlockEntity`, no flags. The recipe naming it is the whole opt-in.
> - **A recipe with an unresolvable reference is dropped silently from the player's view.**
>   It is logged at `SEVERE` and simply never spawns anything; check the server log rather than
>   assuming the mechanic is broken.
> - **Ingredient blocks are consumed exclusively.** Two spawners cannot share one bed. A second
>   spawner in range of the same requirement blocks will never activate until the first one is
>   broken.
> - **World config still gates the spawn.** If the world has `SpawningNPC` or
>   `SpawnMarkersEnabled` off, the marker is created but no companion appears; the module logs
>   this explicitly at `FINE`.
> - **The marker needs a free tile within 4 blocks.** If `SpawningContext` finds nowhere
>   spawnable in rings 1–4 (and within −2/+1 blocks of the spawner's height), no marker is
>   created and the spawner stays inactive.

---

## SpawnNPC Interaction

**Package:** `com.hypixel.hytale.server.npc.interactions.SpawnNPCInteraction` · registered by
`NPCPlugin`

Spawns NPCs from an interaction chain — the egg-spawner items, the Scarak eggsack burst, and the
spellbook all use it. Codec doc: "Spawns an NPC on the block that is being interacted with."
Extends [SimpleBlockInteraction](interactions.md#simpleblockinteraction), so the spawn is
positioned relative to the **targeted block**, not the interacting entity.

**None of its 14 keys is required** — neither by a `true` third argument nor by
`Validators.nonNull()`. That is deliberate rather than lax: `EntityId` can be omitted because
`WeightedEntityIds` supplies the role instead. Several keys are still validated at load, so
"optional" does not mean "unconstrained".

| Property | Type | Default | Description / load-time validation |
|----------|------|---------|-------------------------------------|
| `EntityId` | string | — | Role id of the NPC to spawn. Validated by `NPCRoleValidator`, so a bad id fails at load even though the key is optional |
| `WeightedEntityIds` | array | — | Weighted roles; one entry is picked per spawn roll. **Supersedes `EntityId`** when present. Entry shape below |
| `SpawnOffset` | vec3 | `0,0,0` | Offset from the block's centre, rotated by the block's rotation |
| `SpawnYawOffset` | float | `0` | Yaw offset added to the block's yaw. **In degrees** — see the gotcha below |
| `SpawnChance` | float | `1.0` | Probability the spawn happens at all |
| `AlternateSpawnMaxSearchDistance` | int | `0` | On `FAIL_INVALID_POSITION`, try adjacent columns along the horizontal cardinal axis toward the player, up to this many block steps. `0` disables. Distance is along that axis only, not a Euclidean radius. Validated `min(0)` |
| `SpawnCount` | int[2] | `[1,1]` | `[min, max]` spawns per trigger; with `WeightedEntityIds` it is the number of *rolls*. Validated: exactly 2 entries, each in `1..100`, weakly monotonic — so `[5,2]` fails at load |
| `DistanceRange` | double[2] | `[0,0]` | `[min, max]` random horizontal scatter per NPC. Validated: exactly 2 entries, each `>= 0`, weakly monotonic |
| `SpawnState` | string | — | Optional state to set on the spawned NPC |
| `SpawnSubState` | string | — | Optional sub-state; **only used when `SpawnState` is also set** |
| `SpawnVelocity` | double | `0` | Random horizontal velocity magnitude in a random XZ direction. `0` disables |
| `AllowMidAirSpawn` | boolean | `false` | Still validates physical space but skips the ground-seeking column search on failure — for NPCs emerging from hanging blocks |
| `CenterHitboxOnPosition` | boolean | `false` | Centre the collision box on the computed position rather than placing its feet there |
| `RequireFullCubeClearance` | boolean | **`true`** | When true every non-air block blocks the spawn. When false only full-cube blocks do, letting NPCs emerge past ropes, plants and cocoons. The only boolean here defaulting true |

### WeightedEntityIds entries

Each entry is a `WeightedNPCSpawn` with **three** keys, and it is the clearest example in the
codebase of requiredness arriving in two different forms within one chain:

| Property | Type | Required by | Description |
|----------|------|-------------|-------------|
| `Id` | string | `Validators.nonNull()` **only** | Role id of the NPC. Also validated by `NPCRoleValidator` |
| `Weight` | double | **both** a `true` third argument to `KeyedCodec` *and* `Validators.nonNull()` | Relative weight against the sum of all weights. Validated `greaterThan(0.0)` |
| `CountRange` | int[2] | not required | `[min, max]` of *this* entry to spawn when picked. Validated: 2 entries, each `1..100`, weakly monotonic |

Both forms have to be read: a key can be required by the codec's third argument, by a
`Validators.nonNull()` that attaches *after* `append(...)` closes, or — as `Weight` shows — by
both at once.

The simplest shipped use pins one role and lifts it half a block off the target
(`Server/Item/Items/EggSpawner/Egg_Spawner_Trork.json`):

```json
{
  "Type": "SpawnNPC",
  "EntityId": "Trork_Warrior",
  "SpawnOffset": { "X": 0, "Y": 0.5, "Z": 0 }
}
```

`Server/Item/Interactions/SpawnNPC/` ships a reusable chain built from
[`Replace`](interactions-flow.md#replace) slots, so an item customises the spawn through
`InteractionVars` rather than by redefining the interaction — `SpawnNPC_BlockCondition` (default:
no block restriction; a `Water_Source`/`Water` variant ships alongside), `SpawnNPC_Effects`
(default: a `Throw` animation) and `SpawnNPC_Entity`, which the chain's own comment marks as the
one an item **must** provide. The chain ends in a `ModifyInventory` that consumes one item.

Behavior notes:

- **Spawn position** is `blockCentre + rotate(SpawnOffset, blockRotation) + blockPosition`, and
  rotation is the block's yaw plus `SpawnYawOffset`. A block with no rotation still contributes
  its centre, so `SpawnOffset` of `0,0,0` spawns inside the block.
- **`SpawnCount` means rolls, not NPCs, once `WeightedEntityIds` is set.** The codec says so
  itself — "With `WeightedEntityIds` this is the number of weighted rolls (each roll spawns the
  picked entry's own `CountRange`)". So `SpawnCount` `[2,2]` against entries with `CountRange`
  `[3,3]` yields six NPCs, not two.

> **Gotcha — `SpawnYawOffset` is in degrees, and the engine's own codec documentation says
> radians.** The implementation applies `Math.toRadians(spawnYawOffset)` before adding it to the
> block's yaw, so the value is degrees; the codec's description string ("The yaw rotation offset
> in radians…") is wrong, and it is the string an asset editor would surface. Both shipped assets
> that use the key — `Block_Scarack_Eggsacks_Burst.json` and `Block_Coffin_Open.json` — pass
> `"SpawnYawOffset": 180` to face the spawned NPC away from the block, and 2 of 2 uses only make
> sense as degrees. Trusting the codec doc puts the NPC out by a factor of about 57.

---

## Testing roles in-game

The `com.hypixel.hytale.server.npc.commands` package provides console commands for spawning, removing, and debugging NPCs while iterating on a role. (For the broader command system see [commands.md](commands.md).)

### Spawning NPCs (`/npc spawn`)

```
/npc spawn <role> [options]
```

Main options (`NPCSpawnCommand`):

| Option | Meaning |
| --- | --- |
| `--count` | How many times to run the spawn loop (int > 0, **default `1`**). |
| `--flock` | Flock size (int) **or** a flock-asset id (default `1`). Spawns a whole flock per loop iteration. |
| `--radius` | Scatter radius for the spawned group (double > 0, default `8`). |
| `--speed` | Initial-velocity override along the player's look direction. |
| `--scale` | Body scale (clamped to the model's min/max unless `--bypassScaleLimits`). |
| `--position` | Explicit spawn position. |
| `--posOffset` | Offset from the resolved position. |
| `--headRotation` / `--bodyRotation` | Initial head / body yaw. |
| `--flags` | Comma-separated [`RoleDebugFlags`](#debug-overlay-npc-debug) to stamp on the spawned NPCs. |
| `--frozen` | Spawn frozen (no AI ticking). |
| `--spawnOnGround` | Snap to the ground. |
| `--randomModel` | Pick a random cosmetic skin/model. |
| `--randomRotation` | Randomize facing. |
| `--facingRotation` | Face the spawning player. |
| `--nonrandom` | Use a fixed RNG seed, for reproducible spawns. |
| `--bypassScaleLimits` | Allow scales outside the normal clamp. |
| `--test` | Test-spawn mode (only honoured when `--count` is 1). |

> **Note: `--count` and `--flock` multiply.** The command runs the spawn loop `count` times, and each iteration spawns a whole flock of `--flock` members. So `--count=1 --flock=5` is one pack of 5, while `--count=5 --flock=5` is **25** NPCs (five packs of 5). (Confirmed in-game.)

> **⚠️ Flock membership is wired only at spawn / world-gen time** by `com.hypixel.hytale.server.flock.FlockMembershipSystems`. NPCs placed by hand, via the entity menu, or via `/npc spawn` **without** `--flock` do **not** auto-form a flock — they have no `FlockMembership` component (`com.hypixel.hytale.server.flock.FlockMembership`, with `getFlockId()`). To exercise *any* flock behavior (beacons such as `Message_Attack`, take-turns, etc.) you **must** spawn with `--flock=N` — or build the flock yourself at runtime (see [Flocks at runtime](#flocks-at-runtime-driving-the-engine-flock-from-java)).

> **Note:** Group filters can resolve the dynamic token `$self` ("any NPC sharing my role") against the spawned flock. `Server/NPC/Groups/Self.json` is exactly `{"IncludeRoles":["$self"]}` — the take-turns and flock filters reference it.

### Removing NPCs

None of the built-in removal commands filter by role or type:

| Command | Effect |
| --- | --- |
| `/npc clean` (`NPCCleanCommand`) | Removes **all** NPCs. |
| `/entity clean` | Removes **all** entities. |
| `/entity remove [--others]` | Removes the looked-at entity, or with `--others` removes everything *except* it. |
| `/kill` | Affects **players only**. |

There is no built-in "kill all of role X." To remove NPCs by role you need a plugin command — see [bulk entity operations in commands.md](commands.md#example-bulk-entity-operations).

### Debug overlay (`/npc debug`)

`/npc debug` drives the role debug overlay (backed by `RoleDebugFlags`, via `NPCDebugCommand`) on the selected / looked-at NPC(s):

```
/npc debug <set|toggle|show|clear|presets|defaults> "<Flag,Flag,...>"
```

- `set` **replaces** the current flag set; `toggle` **adds** to it.
- `show` / `clear` / `defaults` display, clear, or reset the flags; `presets` lists every available flag.

The comma-separated flag list **must be quoted** — e.g. `/npc debug set "DisplayState,DisplayFlock"` — see [Argument syntax](commands.md#argument-syntax-input-format).

Genuinely useful flags (all from `RoleDebugFlags`):

| Flag | Shows |
| --- | --- |
| `DisplayState` | The NPC's current role state. |
| `DisplayFlock` | Flock id / membership. |
| `DisplayTarget` | The current target. |
| `VisMarkedTargets` | Marked targets, visualized. |
| `VisSensorRanges` | Sensor detection ranges. |
| `VisAvoidance` | `ApplyAvoidance` collision-avoidance vectors (see [Separation & avoidance steering](#separation--avoidance-steering)). |
| `VisSeparation` | `ApplySeparation` spacing vector — role separation, **not** flocking (see [Separation & avoidance steering](#separation--avoidance-steering)). |
| `VisFlock` | Flock-member connections (the actual flock visualization). |
| `TraceSensorFailures` | Why sensors are *not* matching. |
| `Flock` | General flock-coordination tracing. |

---

## Melee attacks without a CAE

Hytale has **two** NPC melee paths, and the choice matters:

- The **[CAE](#combat-action-evaluator-cae)** path (`_CombatConfig: CAE_…`, with `Ability` assets) — for intelligent, multi-ability combatants like Goblins.
- A far lighter **interaction-var chain** that vanilla animals use (livestock, undead chicken) — no CAE, no `Ability` assets, just a single scripted swing on an otherwise non-combat creature. This is what the rest of this section documents.

To give a creature the lightweight melee:

- Set a role field **`"Attack": "<RootInteraction>"`** (e.g. `Root_NPC_Attack_Melee`) — also settable inline on the `Attack` action.
- Run a **[`Type: "Attack"` action](#the-attack-action)** inside the role's `Instructions` (typically inside an [`ActionsBlocking`](#actionlist-blocking-semantics-multi-tick-sequences) windup sequence) to perform the swing.
- Customize damage / animation / hit-geometry purely by overriding **named interaction vars** under the role's **`InteractionVars`** — spelled **`_InteractionVars`** inside a `Variant`'s `Modify` (next subsection) — no CAE.

Neutral animals ship with this machinery **off by default**: `Template_Animal_Neutral` exposes `Attack` (default `""`) and `AttackWhenStartled` (default `false`) and has a dormant "startled" retaliation in its `Flee` state. Set `AttackWhenStartled: true` plus an `Attack` interaction to enable it. The cleanest "give a creature a bite" exemplar is `Server/NPC/Roles/Undead/Chicken_Undead.json` (a `Template_Predator` variant that sets `"Attack": "Root_NPC_Attack_Melee"` and overrides the start anim + damage). The instruction pattern itself lives in `Template_Predator.json`: a target-in-`AttackDistance` + line-of-sight gate, `HeadMotion: Aim`, `ActionsBlocking`, then `Timeout (pre-delay) → Attack → Timeout (post-delay)`.

### The interaction-var chain

`Attack: "Root_NPC_Attack_Melee"` walks a chain of interactions (under `Server/Item/…/NPCs/`), each of which `Replace`s a **named var** with a default you can override at the role level:

| Interaction | Sets var | Default | Overriding it customizes |
|---|---|---|---|
| `RootInteractions/NPCs/Root_NPC_Attack_Melee` | `Melee_Start` | `NPC_Attack_Melee_Simple` | the whole start (anim set + timing) |
| `Interactions/NPCs/NPC_Attack_Melee_Simple` | `Melee_Selector` | `NPC_Attack_Selector_Left` | the **hit geometry** (see below) |
| `Interactions/NPCs/NPC_Attack_Selector_Left` (`HitEntity`) | `Melee_Damage` | `NPC_Attack_Melee_Damage` | **damage + DamageEffects** |
| `Interactions/NPCs/NPC_Attack_Melee_Damage` | — (`Parent: DamageEntityParent`) | — | base: `DamageCalculator` (Physical 5) + `DamageEffects` (knockback, `WorldSoundEventId`, `WorldParticles`) |

A role overrides any link by declaring the var in its interaction-vars block. The selector's `HitEntity` does `{"Type":"Replace","Var":"Melee_Damage","DefaultValue":{…}}`, so a role-level `Melee_Damage` wins (vanilla `Chicken_Undead` notes in its override: *"When NPC overrides the InteractionVars, this info in Template not applicable anymore"*).

> **⚠️ The key name differs by role type.** `BuilderRole` reads **`InteractionVars`** at a role's top level — that is what the templates use (`Template_Animal_Neutral`, `Template_Predator`, `Template_Livestock`, `Template_Intelligent`, …), and it is what a `Generic` role uses. Inside a **`Variant`'s `Modify`** the same block is spelled **`_InteractionVars`** with the leading underscore, the same convention as `_CombatConfig`; every shipped variant that customises its bite (`Cow.json`, `Chicken_Undead.json`, ~94 files) uses `_InteractionVars`. Using the wrong one for the role type silently does nothing, or drops the role.

Example — lighten the bite to 2 physical, keep the default start/selector (shown as a `Variant` would write it):

```json
"_InteractionVars": {
  "Melee_Damage": {
    "Interactions": [
      { "Parent": "NPC_Attack_Melee_Damage",
        "DamageCalculator": { "Type": "Absolute", "BaseDamage": { "Physical": 2 }, "RandomPercentageModifier": 0.1 } }
    ]
  }
}
```

> This `Replace` / `Var` / `DefaultValue` override-by-name mechanism is general to interactions — see [Interactions](interactions.md). The damage interaction itself is documented in [Combat](combat.md).

### Melee hits are directional swept arcs — NPCs can miss

`NPC_Attack_Selector_Left.json` is a `Type: Selector` whose geometry is a **humanoid sword-swing arc**:

```json
"Selector": {
  "Id": "Horizontal", "Direction": "ToLeft", "TestLineOfSight": true,
  "ExtendTop": 0.5, "ExtendBottom": 0.5, "StartDistance": 0.1, "EndDistance": 3.5,
  "Length": 30, "RollOffset": 0, "YawStartOffset": -15
}
```

It's a narrow (~30°), side-offset wedge swept over the interaction's `RunTime` (0.25 s) **in front of the NPC's body**, reaching 0.1–3.5 blocks, ±0.5 vertical, requiring line of sight. Because the arc is **body-relative**, a custom NPC **whiffs if its body isn't facing the target at strike time** — and `HeadMotion: Aim`/`Watch` alone is *not* enough: a head motion only blends the *body* when the active motion set no yaw and the head exceeds the camera yaw limit (see [Facing](#facing-orientation-is-emergent-from-the-active-motion)), so over a yaw-setting attack motion it turns the head only. It also misses if the target leaves `EndDistance`, strafes out of the arc mid-sweep, or breaks line of sight.

So "why does my NPC sometimes not connect?" has a real mechanical answer: melee is a swept directional hitbox, not a homing hit. Two fixes:

- **Rotate the body onto the target before the swing.** Add a `Seek` body-motion + a longer windup (`Timeout`) so the NPC turns onto the target *before* `Attack` fires. (Coming out of a circling/orbit motion an NPC faces its *tangential* heading ~90° off the target; turning ~90° took ≈0.6 s of windup in testing — 0.35 s under-rotated and missed.)
- **Widen the arc.** Override `Melee_Selector` with a larger `Length`, a forward-centered `YawStartOffset`, and bigger `ExtendTop`/`ExtendBottom`.

### Serializing a flock swarm — native take-turns can't hard-gate it

The flock "take-turns" pattern (`Component_Instruction_Combat_Flock_Take_Turns`) passes an attack "baton" via flock beacons (`Message_Attack`) carrying a `Retreat` flag and a turn timer. But it only *influences positioning* — it does **not** hard-gate the attack:

- `Template_Predator`'s combat-attack instruction is gated only on "target within `AttackDistance` + line-of-sight." It does **not** check the take-turns `Retreat` flag.
- So `Component_Instruction_Combat_Flock_Take_Turns` only *moves* non-attackers out toward the combat-turn distance; any member still in range still swings. Against a stationary, surrounded player you therefore get **multiple simultaneous attackers** regardless.
- `CombatTurnAttackWeight` is a **percent chance to attack per turn** (per its own parameter description), **not** a count of attackers — despite some field descriptions miscalling it a count.

To truly serialize a swarm down to one attacker, gate the **attack decision itself** in a custom `Type: "Generic"` role (a `Variant`'s `Modify` cannot carry `Instructions` — see the [Variants gotcha](#variants)) on a shared signal. The cleanest signal is a [custom token sensor](#registering-a-custom-sensor) that is true for exactly one flock member at a time: gate the attack branch via `And[Player, <token>]`, and let non-holders fall through to a `MaintainDistance` hold branch.

Practical combat-role lessons (all confirmed in-game):

- **Gate the attack on actual bite/attack range, not just on "it's my turn."** Otherwise the turn-holder swings at air while still out of range and wastes its turn — add an inner short-range `Player` gate so it approaches first.
- **Hold position through the swing before transitioning** (e.g. to a retreat). A [`Type: "Attack"` action](#the-attack-action) only *starts* the interaction chain; damage lands partway through it. Use an [`ActionsBlocking`](#actionlist-blocking-semantics-multi-tick-sequences) sequence like `[Attack, Timeout ~0.45s, <transition>]` to stay in range and facing until the hit lands — otherwise the NPC moves away mid-swing and whiffs.
- **For one action per turn, prefer a per-NPC [`Flag`](#flags-setflag--flag)** (`SetFlag` / `Flag`) over relying on an attack-pause cooldown, especially when you also want to change behavior *after* the action.

---

## Combat Action Evaluator (CAE)

The CAE system provides intelligent combat decision-making. Found in `Server/NPC/Balancing/`. A role references its CAE through the `_CombatConfig` field (see the Goblin Scrapper variant above). For the lighter, non-CAE animal melee path, see [Melee attacks without a CAE](#melee-attacks-without-a-cae).

### CAE Structure

A CAE file has `"Type": "CombatActionEvaluator"` at the top and wraps its evaluation logic in a nested `CombatActionEvaluator` object. That object holds:

- `RunConditions`: conditions that gate whether the evaluator runs at all.
- `MinRunUtility` / `MinActionUtility`: utility thresholds.
- `AvailableActions`: an object keyed by action name. Each action has a `Type` (commonly `Ability`), a `Target`, an `Ability` reference, an `AttackDistanceRange`, a `PostExecuteDistanceRange` (the distance to hold *after* the action), optional `Description`/`InteractionVars`/`ChargeFor`/`WeaponSlot`/`SubState`, and a `Conditions` array.
- `ActionSets`: an object keyed by set name (not an array). Each set defines `BasicAttacks` (`Attacks`, `MaxRange`, `Timeout`, `CooldownRange`, optional `Randomise` and `InteractionVars`) and an `Actions` list of available action names.

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

A condition maps its raw input to a 0–1 utility through a `Curve`. **The `Curve` field has two different shapes depending on the condition's base class** — getting this wrong is the usual cause of a CAE failing to load:

| Base class | Conditions | `Curve` shape |
|---|---|---|
| `ScaledCurveCondition` | `TimeSinceLastUsed`, `TargetDistance`, `NearbyCount`, `TimeOfDay`, `OwnStatAbsolute`, `TargetStatAbsolute`, `RecentSustainedDamage`, `TotalSustainedDamage`, `KnownTargetCount` | an **object** — the input is un-normalised, so the curve carries the scaling. |
| `CurveCondition` | `OwnStatPercent`, `TargetStatPercent` | a **plain string** naming a response-curve asset — the input is already 0–1. |
| `SimpleCondition` / `Condition` | `HasTarget`, `IsInState`, `LineOfSight`, `TargetMovementState`, `SelfHasEffect`, `TargetHasEffect`, `Randomiser` | no `Curve` at all. |

```json
"Conditions": [
    { "Type": "TargetDistance",  "Curve": { "ResponseCurve": "SimpleLogistic", "XRange": [ 0, 15 ] } },
    { "Type": "OwnStatPercent",  "Stat": "Health", "Curve": "ReverseLinear" }
]
```

The object form is a `ScaledResponseCurve`, whose own `Type` selects between two implementations (the default may be omitted):

| `Type` | Class | Keys |
|--------|-------|------|
| *(omitted)* / `Default` | `ScaledXResponseCurve` | `ResponseCurve` (asset id) + `XRange` `[min, max]` — rescales x into the named curve. |
| `Switch` | `ScaledSwitchResponseCurve` | `SwitchPoint`, `InitialState` (y before it), `FinalState` (y at/after it) — a step function. Used by 22 shipped CAEs, not just tests. |

`ResponseCurve` values are **assets** under `Server/ResponseCurves/`, so the set is extensible. Each asset picks one of three families — `Exponential` (`Slope`, `Exponent`, `HorizontalShift`, `VerticalShift`), `Logistic` (`Ceiling`, `RateOfChange`, `HorizontalShift`, `VerticalShift`) or `SineWave` (`Amplitude`, `Frequency`, `HorizontalShift`, `VerticalShift`). Those that ship:

| Response Curve | Family | Shape |
|----------------|--------|-------|
| `Linear` | Exponential | `y = x` (slope 1, exponent 1) |
| `ReverseLinear` | Exponential | `y = 1 − x` (slope −1, x-shift 1) |
| `Quadratic` / `TestExponential` | Exponential | `y = x²` — slow start, fast finish |
| `InverseExponential` | Exponential | exponent `0.28` — a *root* curve: rises fast, then flattens (**not** a falloff) |
| `ConstantMidpoint` | Exponential | slope `0`, y-shift `0.5` — constant `0.5` |
| `SimpleLogistic` / `TestLogistic` | Logistic | ascending S-curve centred at `0.5` |
| `SimpleDescendingLogistic` | Logistic | descending S-curve centred at `0.5` |
| `LateRise` | Logistic | stays near 0, rises sharply at `0.8` |
| `LateFalloff` | Logistic | stays near 1, drops sharply at `0.8` |
| `SimpleParabola` | SineWave | half sine over the range — peaks mid-range, 0 at both ends |

### Condition Types

Conditions (in both `RunConditions` and per-action `Conditions`) use a `Type`. Common types:

| Condition Type | Description |
|----------------|-------------|
| `TimeSinceLastUsed` | Time elapsed since the action last ran |
| `TargetDistance` | Distance to the current target |
| `Randomiser` | Random value between `MinValue` and `MaxValue` |
| `OwnStatPercent` / `OwnStatAbsolute` | NPC's own stat as a percentage / absolute value |
| `TargetStatPercent` / `TargetStatAbsolute` | Target's stat as a percentage / absolute value |
| `RecentSustainedDamage` / `TotalSustainedDamage` | Damage taken recently / in total |
| `NearbyCount` / `KnownTargetCount` | Counts of nearby / remembered entities |
| `HasTarget` | Whether a target exists at all |
| `IsInState` | Whether the NPC is in a given state |
| `LineOfSight` | Whether the target is in line of sight |
| `TimeOfDay` | Current world time |
| `TargetMovementState` | Target's movement state |
| `SelfHasEffect` / `TargetHasEffect` | Entity-effect presence on self / target |

The first three groups come from `Condition.CODEC` in `server.npc.decisionmaker`; `RecentSustainedDamage`, `TotalSustainedDamage` and `KnownTargetCount` are registered by `NPCCombatActionEvaluatorPlugin` and therefore only exist where the CAE plugin is loaded.

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
| Companion Block Spawners | `Server/NPC/Spawn/CompanionBlockSpawners/` |
| Combat Balance | `Server/NPC/Balancing/` |
| Groups | `Server/NPC/Groups/` |
| Flocks | `Server/NPC/Flocks/` |

### Asset Statistics

| Category | Count | Description |
|----------|-------|-------------|
| Total Roles | 1,000 | NPC role definitions (`Server/NPC/Roles/**.json`) |
| — by `Type` | 467 `Variant` · 320 `Generic` · 55 `Abstract` | the rest are components, templates-by-reference and test fixtures |
| Templates (`Template_*`) | 51 | Abstract base templates (13 in `_Core/Templates/`, 3 more in its `Deprecated/`) |
| Attitude Files | 26 | Relationship definitions (`Attitude/Roles/`) |
| Group Files | 72 | NPC role collections |
| Flock Files | 8 | Flock size configurations |
| Spawn Beacons | 85 | Spawn configurations |
| Companion Block Spawner Recipes | 2 | Both are `Debug_*` examples |
| CAE Files | 28 | Combat balancing |

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the NPC role/spawn loader (each verified against `HytaleServer.jar`).

- **`Unable to spawn entity with invalid role index`** → a spawn beacon `NPCs` entry references a role `Id` that does not resolve to a loaded role. Fix: the `Id` must match an existing variant's name exactly (case-sensitive), e.g. `Goblin_Scrapper`.
- **`attempted to spawn invalid NPC role`** → a spawn marker named a role that failed to load or doesn't exist. Fix: confirm the referenced role file is present under `Server/NPC/Roles/` and validated.
- **`Cannot have more than one combat state in an NPC`** → a role's `Instructions`/state machine declares more than one combat state. Fix: keep a single combat state per role.
- **`No such state for combat evaluator`** → a CAE `ActionSets`/`SubState` references a state that the role does not define. Fix: every CAE state/sub-state must correspond to a state used by the role's `Instructions`.
- **Symptom:** a `Variant` ignores its `Reference` template's values → the `Reference` short name didn't resolve, or you put `{Value, Description}` objects in `Modify`. Fix: reference the template by its exact short name, and in `Modify` use plain values (the `{Value, Description}` form belongs only in a template's `Parameters` block).
- **Symptom:** a `Compute` expression evaluates to nothing/default → the named parameter isn't declared in any `Parameters` block up the template chain. Fix: declare the parameter (in the template or an overriding variant `Parameters` block) before reading it with `{ "Compute": "..." }`.
- **Symptom:** a role silently never registers (absent from the spawn list) after an edit → **any** load error drops the whole role, not just the offending field. The [`Variant`-with-`Instructions`](#variants) case is one instance; another common one is passing a number array to an alarm `DurationRange` (`Expression type mismatch. Got NUMBER_ARRAY but expected STRING_ARRAY`; see [Alarms](#alarms-setalarm--alarm)). Fix: check the server log for the load error and correct that field.
- **`Reloading nonexistent role %s!`** (logged at `SEVERE` with an `[NPC|P]` prefix, every tick — from `RoleBuilderSystem`) → a saved-world entity references a role that failed to load **or was renamed**, and persists in the save spamming the log. Fix: remove/replace the stale entities, or restore the old role name.
- **`Unknown JSON attribute '%s' found in %s: %s (JSON: %s)`** (WARN, non-fatal — from `BuilderBase`) → a custom/`$`-prefixed key other than the exact `$Comment` (e.g. `$Comment_Foo`); the second `%s` is the construct, e.g. `Role|Generic`. Only `$Comment` is whitelisted by the role parser, and you can't have two `$Comment`s at one object level (duplicate JSON key). Fix: consolidate prose into a single `$Comment`.
- **Symptom:** a role with a `$Comment` **directly under** a `Variant`'s `Modify` / `Parameters` block fails to load (FATAL) with `java.lang.IllegalStateException: Parameter $Comment does not exist or is private`, then vanishes from the spawn list (with the `Reloading nonexistent role` spam above). There, every key at that level of `Modify` is treated as a **role parameter to set**, and `$Comment` isn't one. A `Generic` role's *top level* and its `Instructions` **do** accept `$Comment`, and so do nested structural values inside a `Modify` (shipped variants such as `Chicken_Undead.json` carry `$Comment`s inside their `_InteractionVars` interactions). Fix: comment freely in `Generic` roles and inside a `Modify`'s nested structures; keep the `Modify`/`Parameters` level itself comment-free.
- **Symptom (runtime flocks):** a brand-new flock reports `EntityGroup.size() == 0` for the rest of the tick after `createFlock` + `join`, so per-target dedup-by-count spawns one flock per aggro'd NPC. The member group is populated by a *deferred* system. Fix: validate by the `Flock` component, not member count; cap with your own counter. See [Flocks at runtime](#flocks-at-runtime-driving-the-engine-flock-from-java).
- **Symptom (runtime flocks):** `FlockPlugin.getFlock(store, flockEntityRef)` always returns `null` on a flock entity. It expects a flock *member* ref (it reads the member's `FlockMembership`); a flock entity has no `FlockMembership`. Fix: read the entity's `Flock` component directly. See [Flocks at runtime](#flocks-at-runtime-driving-the-engine-flock-from-java).

---
