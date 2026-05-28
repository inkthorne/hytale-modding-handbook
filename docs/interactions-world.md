---
title: "Entity & World Interactions"
description: "Hytale entity and world interactions in JSON — entity lifecycle (SpawnPrefab, RemoveEntity, LaunchProjectile), player messaging and custom UI, and inventory/equipment changes."
seo:
  type: TechArticle
---

# Entity & World Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.5.2**

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

This page covers the entity- and world-affecting interactions: spawning and removing entities, launching projectiles, messaging, opening UI, manipulating inventory and blocks, state transitions, and movement mechanics.

## Overview

Defined as JSON interaction assets (server classes under `com.hypixel.hytale.server.core.modules.interaction.interaction.config`) and provides:
- Entity lifecycle: `SpawnPrefab`, `RemoveEntity`, `LaunchProjectile`
- Player communication: `SendMessage` and UI page opening (`OpenCustomUI`)
- Inventory/equipment changes: `EquipItem`, `ModifyInventory`
- World blocks: `BreakBlock`, `PlaceBlock`
- Entity state and physics: `ChangeState`, `LaunchPad`, `Wielding`

## Architecture
```
Entity & World
├── Entity lifecycle
│   ├── SpawnPrefab (PrefabId at Self / Target / HitLocation)
│   ├── RemoveEntity
│   └── LaunchProjectile (ProjectileId + Speed)
├── Player I/O
│   ├── SendMessage (chat)
│   └── UI (OpenCustomUI)
├── Inventory
│   ├── EquipItem
│   └── ModifyInventory
├── Blocks
│   ├── BreakBlock
│   └── PlaceBlock
└── Entity state & physics
    ├── ChangeState (state-machine transition)
    ├── LaunchPad
    └── Wielding (blocking / guarding)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `SpawnPrefabInteraction` | `config/server/SpawnPrefabInteraction` | Spawns entity prefabs at a location |
| `RemoveEntityInteraction` | `config/none/RemoveEntityInteraction` | Despawns entities from the world |
| `LaunchProjectileInteraction` | `config/server/LaunchProjectileInteraction` | Fires projectiles from an entity |
| `SendMessageInteraction` | `config/none/SendMessageInteraction` | Sends chat messages to players |
| `OpenCustomUIInteraction` | `config/server/OpenCustomUIInteraction` | Opens a custom UI page |
| `EquipItemInteraction` | `config/server/EquipItemInteraction` | Equips an item |
| `ModifyInventoryInteraction` | `config/server/ModifyInventoryInteraction` | Adjusts inventory contents |
| `BreakBlockInteraction` | `config/client/BreakBlockInteraction` | Breaks a targeted block |
| `PlaceBlockInteraction` | `config/client/PlaceBlockInteraction` | Places a block |
| `ChangeStateInteraction` | `config/client/ChangeStateInteraction` | Changes an entity's state-machine state |
| `LaunchPadInteraction` | `config/server/LaunchPadInteraction` | Launch-pad physics |
| `WieldingInteraction` | `config/client/WieldingInteraction` | Blocking and guarding mechanics |

## Quick Navigation

| Interaction | Description |
|-------------|-------------|
| [SpawnPrefab](#spawnprefab) | Spawn entities at locations |
| [RemoveEntity](#removeentity) | Despawn entities from the world |
| [LaunchProjectile](#launchprojectile) | Fire projectiles |
| [SendMessage](#sendmessage) | Send chat messages to players |
| [UI Interactions](#ui-interactions) | Open custom UI pages (OpenCustomUI) |
| [Inventory Interactions](#inventory-interactions) | Manage inventory and equipment |
| [Block Interactions](#block-interactions) | Break or place blocks |
| [ChangeState](#changestate) | Change entity state machine state |
| [LaunchPadInteraction](#launchpadinteraction) | Launch pad physics |
| [WieldingInteraction](#wieldinginteraction) | Blocking and guarding mechanics |

---

## SpawnPrefab

**Package:** `config/server/SpawnPrefabInteraction`

Spawns entities at specified locations.

### Structure

```json
{
  "Type": "SpawnPrefab",
  "PrefabId": "Skeleton_Fighter_Random_Weapon",
  "Position": "Target",
  "Count": 1,
  "Offset": [0, 0, 0]
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `PrefabId` | string | Entity prefab ID to spawn |
| `Position` | string | `Self`, `Target`, or `HitLocation` |
| `Count` | int | Number of entities to spawn |
| `Offset` | [x, y, z] | Position offset from spawn point |
| `SpawnVelocity` | [x, y, z] | Initial velocity for spawned entity |
| `InheritVelocity` | boolean | Inherit spawner's velocity |

### Example: Summon Minions on Ability

```json
{
  "Type": "SpawnPrefab",
  "PrefabId": "Skeleton_Fighter_Random_Weapon",
  "Position": "Self",
  "Count": 3,
  "Offset": [0, 0, 2]
}
```

---

## RemoveEntity

**Package:** `config/none/RemoveEntityInteraction`

Despawns/removes entities from the world.

### Structure

```json
{
  "Type": "RemoveEntity",
  "Entity": "User"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Entity` | string | Which entity to remove (e.g. `User`, `Target`) |
| `Effects` | object | Optional sound/particle effects played on removal |

### Example: Projectile self-removal (from Bomb_Popberry.json)

```json
{
  "Type": "RemoveEntity",
  "Entity": "User",
  "Effects": {
    "WorldSoundEventId": "SFX_Goblin_Lobber_Bomb_Death",
    "LocalSoundEventId": "SFX_Goblin_Lobber_Bomb_Death"
  }
}
```

---

## LaunchProjectile

**Package:** `config/server/LaunchProjectileInteraction`

Fires projectiles from an entity.

### Structure

```json
{
  "Type": "LaunchProjectile",
  "ProjectileId": "Arrow_FullCharge",
  "Speed": 50,
  "SpawnOffset": [0, 1.5, 0.5],
  "AimType": "Forward"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `ProjectileId` | string | Projectile prefab ID |
| `Speed` | float | Initial projectile speed |
| `SpawnOffset` | [x, y, z] | Offset from entity position |
| `AimType` | string | `Forward`, `AtTarget`, `AtCursor` |
| `Spread` | float | Random spread angle (degrees) |
| `Count` | int | Number of projectiles |
| `Gravity` | float | Gravity multiplier |

See [projectiles.md](projectiles.md) for more projectile details.

---

## SendMessage

**Package:** `config/none/SendMessageInteraction`

Sends chat messages to players.

### Structure

```json
{
  "Type": "SendMessage",
  "Message": "Critical Hit!"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Message` | string | Literal text to display |
| `Key` | string | Localization key to display (alternative to `Message`) |

`SendMessage` is used heavily in the debug interactions (e.g. `Debug_Combo_Primary.json`) with a literal `Message`, and in system interactions (e.g. `Teleporter_Try_Place.json`) with a localization `Key`.

---

## UI Interactions

### OpenCustomUI

**Package:** `config/server/OpenCustomUIInteraction`

Opens a custom UI page registered via Java. Unlike `OpenPage`, this interaction uses a nested `Page` object that can include additional properties passed to the page supplier.

```json
{
  "Type": "OpenCustomUI",
  "Page": {
    "Id": "ItemRepair",
    "RepairPenalty": 0.1
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Page.Id` | string | Registered page supplier ID |
| `Page.*` | varies | Additional properties passed to the supplier |

#### Built-in Pages

| Page ID | Supplier Properties | Description |
|---------|---------------------|-------------|
| `ItemRepair` | `RepairPenalty` (float) | Item repair UI |
| `Shop` | `shopId` (string) | Shop interface |
| `Memories` | - | Memories/journal page |
| `PrefabSpawner` | - | Prefab spawner settings |

#### Example: Item Repair Interaction

From `Tool_Repair_Kit_Crude.json`:

```json
{
  "Type": "OpenCustomUI",
  "Page": {
    "Id": "ItemRepair",
    "RepairPenalty": 0.1
  }
}
```

This opens the item repair UI with a 10% durability penalty applied to repairs.

See [UI API - Registering Pages for OpenCustomUI](ui-api.md#registering-pages-for-opencustomui) for creating custom pages that work with this interaction.

---

## Inventory Interactions

### EquipItem

**Package:** `config/server/EquipItemInteraction`

Equips an item to an equipment slot.

```json
{
  "Type": "EquipItem",
  "Slot": "MainHand",
  "ItemId": "Weapon_Sword_Iron"
}
```

### ModifyInventory

**Package:** `config/server/ModifyInventoryInteraction`

Adjusts the quantity of the currently held item. Used to consume items on use (e.g. placing a block, eating food).

```json
{
  "Type": "ModifyInventory",
  "AdjustHeldItemQuantity": -1
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AdjustHeldItemQuantity` | int | Amount to add to (positive) or remove from (negative) the held stack |
| `RequiredGameMode` | string | Optional game mode gate (e.g. `Adventure`) for the adjustment to apply |

### Example: Consume one item only in Adventure mode (from Half_Block.json)

```json
{
  "Type": "ModifyInventory",
  "AdjustHeldItemQuantity": -1,
  "RequiredGameMode": "Adventure"
}
```

> **Gotcha — a non-matching `RequiredGameMode` skips the node and proceeds to `Next` (it does *not*
> route to `Failed`).** So a weapon/block whose cost lives in a `ModifyInventory` with
> `"RequiredGameMode": "Adventure"` fires/places **for free** in Creative and Survival, and only
> charges in Adventure. This differs from the **`Condition`** pattern used by consumables, whose
> `Failed` branch routes to `Block_Secondary` — which is why food/potions are *blocked* (not free)
> outside Adventure (see [items-consumables.md](items-consumables.md)). To make an Adventure-mode
> item cost nothing, copy the interaction and drop the `ModifyInventory` node while keeping its
> `Next`. Note the cost can recur deeper in the tree (e.g. the Flame Crystal Staff consumes essence
> in each `Weapon_Stick_Fire_Projectile_Charged_*` node, not at the entry), so grep the whole chain
> before assuming a weapon is free.

---

## Block Interactions

### BreakBlock

**Package:** `config/client/BreakBlockInteraction`

Breaks a block at the target location.

```json
{
  "Type": "BreakBlock",
  "Target": "TargetBlock",
  "DropItems": true
}
```

### PlaceBlock

**Package:** `config/client/PlaceBlockInteraction`

Places a block at the target location.

```json
{
  "Type": "PlaceBlock",
  "Target": "TargetBlock",
  "BlockId": "Rock_Dawnstone"
}
```

---

## ChangeState

**Package:** `config/client/ChangeStateInteraction`

Changes block or entity state machine state. Used for toggleable blocks (torches, lanterns), traps, and temporary state effects.

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `Changes` | object | State transition map defining from→to state mappings |
| `Effects` | object | Sound/particle effects triggered on state change |
| `RunTime` | float | Duration in seconds before `Next` interaction executes |
| `Next` | interaction | Chained interaction to execute after `RunTime` |
| `UpdateBlockState` | boolean | Force visual state update after change |

### State Transition Map (Changes)

The `Changes` property defines a mapping where keys are current states and values are target states:

```json
{
  "Changes": {
    "default": "Off",
    "Off": "default"
  }
}
```

This creates a toggle: when in `default` state, transition to `Off`; when in `Off`, transition back to `default`.

**State naming conventions:**
- `default` - The initial/primary state (lit torch, open door)
- `Off` - Disabled/inactive state (extinguished torch)
- `Closed` - For traps and containers
- Custom states defined in block's `State.Definitions`

### Integration with Block State Definitions

ChangeState works with the block's state machine defined in its BlockType configuration:

```json
{
  "State": {
    "Definitions": {
      "On": { "CanProvideSupport": { "Up": true } },
      "Off": { "CanProvideSupport": { "Up": false } }
    }
  }
}
```

Each state in `Definitions` can override block properties like collision, light emission, and support behavior. The `Changes` map references these state names.

### Examples

#### Simple Toggle (Torch)

Basic on/off toggle for a wall torch:

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "Off",
    "Off": "default"
  }
}
```

#### Multi-State Transition (Colored Lantern)

Transition any non-default state back to default:

```json
{
  "Type": "ChangeState",
  "Changes": {
    "Off": "default",
    "Blue": "default",
    "Green": "default",
    "Red": "default"
  }
}
```

#### One-Way Transition (Trap)

Irreversible state change for triggered traps:

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "Closed"
  }
}
```

#### Timed State Change (Geyser)

Temporary state with automatic reversion using `RunTime` and `Next`:

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "Erupting"
  },
  "RunTime": 3,
  "Next": {
    "Type": "ChangeState",
    "Changes": {
      "Erupting": "default"
    }
  }
}
```

The geyser enters `Erupting` state, waits 3 seconds, then returns to `default`.

#### With Sound Effects (Trophy)

State change with audio feedback:

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "Off",
    "Off": "default"
  },
  "Effects": {
    "LocalSoundEventId": "SFX_Door_Crude_Open"
  }
}
```

### File Locations

Example assets using ChangeState:
- `data/BlockTypes/Light_Sources/Wood_Torch_Wall.json` - Simple toggle
- `data/BlockTypes/Light_Sources/Lantern_Blue.json` - Multi-state
- `data/BlockTypes/Traps/Survival_Trap_Snapjaw.json` - One-way trap
- `data/BlockTypes/Nature/Prototype_Geyser.json` - Timed with RunTime/Next
- `data/BlockTypes/Decorative/Deco_Trophy_Harvest.json` - Effects property

### Related

- [BlockCondition](interactions-flow.md#blockcondition) - Check current block state
- [State.Definitions](items-blocks.md#block-states) - Define block states and their property overrides

---

## LaunchPadInteraction

**Package:** `config/server/LaunchPadInteraction`

Specialized launch pad physics for bouncing entities.

```json
{
  "Type": "LaunchPad",
  "LaunchVelocity": [0, 20, 0],
  "PreserveHorizontal": true
}
```

---

## WieldingInteraction

**Package:** `config/client/WieldingInteraction`

**Class hierarchy:** `WieldingInteraction` → `ChargingInteraction` → `SimpleInteraction` → `Interaction`

Enables blocking and guarding mechanics for shields and weapons. When active, the player holds a defensive stance that reduces or negates incoming damage based on attack angle. The interaction inherits from ChargingInteraction, providing hold-duration behavior, movement speed reduction, and animation support. Wielding integrates with stamina systems—blocking consumes stamina proportional to damage blocked, and stamina depletion triggers guard break effects.

### Core Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Type` | string | Required | Always `"Wielding"` |
| `AngledWielding` | object | - | Directional blocking configuration with damage/knockback modifiers |
| `DamageModifiers` | object | - | Direct damage reduction (alternative to AngledWielding for simpler configs) |
| `StaminaCost` | object | - | Stamina consumption per damage blocked |
| `BlockedEffects` | object | - | Visual/audio effects when block succeeds |
| `BlockedInteractions` | object | - | Interactions triggered on successful block |
| `Forks` | object | - | Branching interactions while blocking (e.g., shield bash) |
| `Failed` | object | - | Interactions triggered on guard break (stamina depleted) |
| `Next` | Interaction | - | Interaction to run when guard ends normally |
| `Effects` | object | - | Animation/sound for guard start (inherited from ChargingInteraction) |

**Inherited from ChargingInteraction:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `RunTime` | float | - | Maximum duration in seconds (omit for indefinite hold) |
| `AllowIndefiniteHold` | boolean | `true` | If `true`, block can be held indefinitely |
| `CancelOnOtherClick` | boolean | `false` | If `true`, interaction cancels when another input is pressed |
| `FailOnDamage` | boolean | `false` | If `true`, interaction ends when hit (even if blocked) |
| `HorizontalSpeedMultiplier` | float | `1.0` | Movement speed while blocking (0.0-1.0) |
| `DisplayProgress` | boolean | - | Show guard duration indicator |

### File Locations

**Player weapon guards:**
```
Server/Item/Interactions/Weapons/{WeaponType}/Secondary/Guard/*_Guard_Wield.json
```

Weapon types with guard: Sword, Shield, Battleaxe, Daggers, Mace, Crossbow, Shortbow

**NPC blocks:**
```
Server/Item/Interactions/NPCs/{Type}/{NPC}/*_Block.json
```

NPCs like Skeleton Knight, Outlander Brute use simpler block configurations.

**Root interactions:**
```
Server/Item/RootInteractions/Weapons/{WeaponType}/Root_Weapon_{Type}_Secondary_Guard.json
```

### AngledWielding

Controls directional blocking based on attack angle, with separate modifiers for damage and knockback:

```json
"AngledWielding": {
  "Angle": 0,
  "AngleDistance": 90,
  "DamageModifiers": {
    "Physical": 0,
    "Projectile": 0,
    "Poison": 0
  },
  "KnockbackModifiers": {
    "Physical": 0.25,
    "Projectile": 0.25
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Angle` | float | Center angle of the blocking arc (0 = forward) |
| `AngleDistance` | float | Half-width of the blocking arc in degrees |
| `DamageModifiers` | object | Multipliers per damage type (0 = full block, 1 = no reduction) |
| `KnockbackModifiers` | object | Multipliers per damage type for knockback reduction |

**Real values from weapon assets:**

| Weapon | DamageModifiers | KnockbackModifiers | Notes |
|--------|-----------------|--------------------|----|
| Sword | Physical: 0, Projectile: 0, Poison: 0 | Physical: 0.25, Projectile: 0.25 | Full damage block, 75% knockback reduction |
| Shield | Physical: 0, Projectile: 0, Poison: 0 | Physical: 0.25, Projectile: 0.25 | Same as sword |
| Battleaxe | Physical: 0, Projectile: 0, Poison: 0 | Physical: 0.25, Projectile: 0.25 | Heavy weapon guard |
| Unarmed | Physical: 0.8, Projectile: 0.8 | - | 20% damage reduction only |
| NPC Skeleton Knight | Physical: 0.2, Projectile: 0.2 | - | 80% damage reduction |
| NPC Outlander Brute | Physical: 0, Projectile: 0 | - | Full block |

### DamageModifiers (Top-Level)

For simpler configurations (commonly used by NPCs), damage modifiers can be specified at the top level instead of inside AngledWielding:

```json
{
  "Type": "Wielding",
  "DamageModifiers": {
    "Physical": 0.2,
    "Projectile": 0.2
  }
}
```

This format blocks from all angles with uniform damage reduction.

### Forks (Guard Branching)

The `Forks` system allows branching to different interactions while blocking is active. This enables mechanics like shield bash (primary click during guard).

```json
"Forks": {
  "Primary": {
    "Type": "Replace",
    "Var": "Weapon",
    "DefaultValue": {
      "Interactions": ["Guard_Bash"]
    }
  }
}
```

| Fork Key | Trigger | Common Use |
|----------|---------|------------|
| `Primary` | Primary click while blocking | Shield bash, guard counter |
| `Secondary` | Secondary click while blocking | Alternate guard action |

**Shield Bash Pattern:**

The Primary fork typically uses Replace to select the correct bash animation based on weapon type:

```json
"Forks": {
  "Primary": {
    "Type": "Replace",
    "Var": "Weapon",
    "DefaultValue": {
      "Interactions": ["Sword_Guard_Bash"]
    }
  }
}
```

### Effects (Guard Start)

Inherited from ChargingInteraction, the `Effects` object configures the animation and sound when entering guard stance:

```json
"Effects": {
  "ItemAnimationId": "Guard",
  "ClearAnimationOnFinish": true,
  "WorldSoundEventId": "SFX_Shield_T2_Raise",
  "LocalSoundEventId": "SFX_Shield_T2_Raise_Local"
}
```

| Property | Type | Description |
|----------|------|-------------|
| `ItemAnimationId` | string | Animation to play on held item when guard starts |
| `ClearAnimationOnFinish` | boolean | Stop animation when guard ends |
| `WorldSoundEventId` | string | Sound event audible to nearby players |
| `LocalSoundEventId` | string | Sound event only the blocking player hears |

### StaminaCost

Stamina consumption when blocking damage:

```json
"StaminaCost": {
  "CostType": "Damage",
  "Value": 7
}
```

| Property | Type | Description |
|----------|------|-------------|
| `CostType` | string | `"Damage"` = cost per point of damage blocked |
| `Value` | float | Stamina consumed per damage point blocked |

**Real values:** Most weapons use `Value: 7` for their guard stamina cost.

### BlockedEffects

Effects triggered on each successful block (sounds, particles):

```json
"BlockedEffects": {
  "WorldSoundEventId": "SFX_Shield_T2_Impact",
  "LocalSoundEventId": "SFX_Shield_T2_Impact_Local",
  "WorldParticles": [
    { "SystemId": "Shield_Block" }
  ]
}
```

### BlockedInteractions

Interactions triggered when a block succeeds. This enables mechanics like:
- Granting signature energy on successful blocks
- Applying knockback to attackers
- Setting chain flags for counter-attack windows

```json
"BlockedInteractions": {
  "Interactions": [
    {
      "Type": "ChangeStat",
      "StatModifiers": {
        "SignatureEnergy": 5
      }
    },
    {
      "Type": "ChainFlag",
      "ChainId": "Sword_Combat",
      "Flag": "Counter_Ready"
    }
  ]
}
```

**Parry Example (from Debug_Stick_Parry):**

A parry is a short-duration wielding that triggers special interactions on block:

```json
{
  "Type": "Wielding",
  "RunTime": 0.3,
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 180,
    "DamageModifiers": { "Physical": 0 }
  },
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "SendMessage",
        "Message": "Perfect Parry!"
      },
      {
        "Type": "ApplyForce",
        "Entity": "Target",
        "Direction": { "X": 0, "Y": 5, "Z": -15 },
        "AdjustVertical": false,
        "Force": 15
      },
      {
        "Type": "ChainFlag",
        "ChainId": "Debug_Combat",
        "Flag": "Parry_Counter"
      }
    ]
  }
}
```

### Failed (Guard Break)

Interactions triggered when stamina is depleted while blocking:

```json
"Failed": {
  "Interactions": [
    {
      "Type": "ApplyEffect",
      "EffectId": "Stamina_Broken"
    },
    {
      "Type": "Simple",
      "Effects": { "WorldSoundEventId": "SFX_Guard_Break" }
    }
  ]
}
```

Guard break typically applies a stagger state, leaving the player vulnerable.

### Next (Post-Guard)

The `Next` property specifies an interaction to run when guard ends normally (not from guard break). Common use: reset stamina regeneration delay.

```json
"Next": {
  "Type": "ChangeStat",
  "Behaviour": "Set",
  "StatModifiers": {
    "StaminaRegenDelay": -1
  }
}
```

This pattern resets the stamina regen delay timer when guard ends, allowing stamina to begin regenerating.

### Complete Examples

**Full Sword Guard Configuration:**

```json
{
  "Type": "Wielding",
  "Effects": {
    "ItemAnimationId": "Guard",
    "ClearAnimationOnFinish": true,
    "WorldSoundEventId": "SFX_Sword_T2_Guard_Raise",
    "LocalSoundEventId": "SFX_Sword_T2_Guard_Raise_Local"
  },
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 90,
    "DamageModifiers": {
      "Physical": 0,
      "Projectile": 0,
      "Poison": 0
    },
    "KnockbackModifiers": {
      "Physical": 0.25,
      "Projectile": 0.25
    }
  },
  "StaminaCost": {
    "CostType": "Damage",
    "Value": 7
  },
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Sword_T2_Impact",
    "LocalSoundEventId": "SFX_Sword_T2_Impact_Local",
    "WorldParticles": [
      { "SystemId": "Sword_Block_Sparks" }
    ]
  },
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "ChangeStat",
        "StatModifiers": {
          "SignatureEnergy": 3
        }
      }
    ]
  },
  "Forks": {
    "Primary": {
      "Type": "Replace",
      "Var": "Weapon",
      "DefaultValue": {
        "Interactions": ["Sword_Guard_Bash"]
      }
    }
  },
  "Failed": {
    "Interactions": [
      {
        "Type": "ApplyEffect",
        "EffectId": "Stamina_Broken"
      }
    ]
  },
  "Next": {
    "Type": "ChangeStat",
    "Behaviour": "Set",
    "StatModifiers": {
      "StaminaRegenDelay": -1
    }
  }
}
```

**Simple NPC Block:**

```json
{
  "Type": "Wielding",
  "DamageModifiers": {
    "Physical": 0.2,
    "Projectile": 0.2
  },
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Metal_Block"
  }
}
```

**Timed Parry Window:**

```json
{
  "Type": "Wielding",
  "RunTime": 0.25,
  "AllowIndefiniteHold": false,
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 120,
    "DamageModifiers": { "Physical": 0 }
  },
  "Effects": {
    "ItemAnimationId": "Parry_Start",
    "ClearAnimationOnFinish": true
  },
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "Serial",
        "Interactions": [
          {
            "Type": "ApplyForce",
            "Entity": "Target",
            "Direction": { "X": 0, "Y": 3, "Z": -12 },
            "AdjustVertical": false,
            "Force": 12
          },
          {
            "Type": "ApplyEffect",
            "Entity": "Target",
            "EffectId": "Stamina_Broken"
          },
          {
            "Type": "ChainFlag",
            "ChainId": "Combat",
            "Flag": "Perfect_Parry"
          }
        ]
      }
    ]
  },
  "Failed": {
    "Interactions": [
      {
        "Type": "SendMessage",
        "Message": "Parry missed!"
      }
    ]
  }
}
```

### Common Patterns

| Pattern | Key Properties | Use Case |
|---------|----------------|----------|
| **Standard Guard** | `AngledWielding` + `StaminaCost` + `Forks.Primary` | Sword/shield blocking with bash option |
| **Simple NPC Block** | `DamageModifiers` only | Basic AI blocking |
| **Parry Window** | `RunTime: 0.25`, `BlockedInteractions` with counter | Timing-based defensive option |
| **Energy-Building Block** | `BlockedInteractions` with `ChangeStat` | Blocking charges signature meter |
| **Counter Setup** | `BlockedInteractions` with `ChainFlag` | Successful block unlocks counter-attack |

### Technical Notes

- **Inheritance** - WieldingInteraction inherits all properties from ChargingInteraction, including movement speed modifiers, progress display, and the `Next` map system. However, Wielding typically uses `AllowIndefiniteHold: true` by default.

- **Stamina Integration** - When `StaminaCost` is configured with `CostType: "Damage"`, each point of damage blocked consumes `Value` stamina. When stamina reaches zero, the `Failed` branch triggers.

- **Directional Blocking** - The `Angle` and `AngleDistance` create a blocking arc. Attacks from within this arc apply `DamageModifiers`; attacks from outside bypass the block entirely.

- **Forks Execution** - When a Fork triggers (e.g., Primary click during guard), the Wielding interaction ends and the forked interaction executes. The guard does not resume automatically.

- **Guard Break Recovery** - The `Failed` interactions should include a state change (stagger/stun) that prevents immediate re-blocking, creating a vulnerability window.

### Related Interactions

- [ChargingInteraction](interactions-combo.md#charginginteraction) - Parent class providing hold-duration behavior
- [ChainFlagInteraction](interactions-combo.md#chainflaginteraction) - Set flags from BlockedInteractions for counter-attack systems
- [ChangeState](interactions-world.md#changestate) - Used in Failed for guard break stagger
- [ChangeStat](interactions-combat.md#changestat) - Modify stamina, signature energy on block
- [Replace](interactions-flow.md#replace) - Used in Forks for weapon-specific bash attacks

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 server (verified against `HytaleServer.jar`).

- **`State transition edge cannot be defined from a state to itself:`** → a `ChangeState` `Changes` entry maps a state to itself (e.g. `"Off": "Off"`). Fix: every `Changes` key must map to a *different* target state; use distinct from→to names (see [State Transition Map](#state-transition-map-changes)).
- **`No projectile config typeName provided`** → a `LaunchProjectile` (or the projectile prefab it references) is missing its projectile config type. Fix: point `ProjectileId` at a prefab that defines a valid projectile config.
- **`has no valid ProjectileConfig:`** → the referenced projectile prefab exists but carries no usable `ProjectileConfig`. Fix: verify the projectile asset is fully defined, not just present.
- **Symptom:** a `ChangeState` does nothing → the current state isn't a key in the `Changes` map, so no transition matches. Fix: include the entity/block's actual current state as a key, and confirm the target state exists in the block's `State.Definitions`.
- **Symptom:** a `SpawnPrefab` spawns nothing → `PrefabId` doesn't resolve to a loaded prefab. Fix: use a prefab ID that exists in the loaded asset set (filename without extension).
