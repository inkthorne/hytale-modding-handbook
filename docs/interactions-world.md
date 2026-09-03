---
title: "Entity & World Interactions"
description: "Hytale entity and world interactions in JSON — entity lifecycle (SpawnPrefab, RemoveEntity, LaunchProjectile), player messaging and custom UI, and inventory/equipment changes."
seo:
  type: TechArticle
---

# Entity & World Interactions

**Doc type:** JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.5.9**

> Part of the [Interactions API](interactions.md). For base interaction properties, see [Reference](interactions.md#reference).

This page covers the entity- and world-affecting interactions: spawning and removing entities, launching projectiles, messaging, opening UI, manipulating inventory and blocks, state transitions, and movement mechanics.

## Overview

Defined as JSON interaction assets (server classes under `com.hypixel.hytale.server.core.modules.interaction.interaction.config`) and provides:
- Entity lifecycle: `SpawnPrefab`, `RemoveEntity`, `LaunchProjectile`
- Player communication: `SendMessage` and UI page opening (`OpenCustomUI`)
- Inventory/equipment changes: `EquipItem`, `ModifyInventory`
- World blocks: `BreakBlock`, `PlaceBlock`, `PlaceFluid`
- Interactive blocks and explosions: `Door`, `OpenContainer`, `Explode`
- Entity state and physics: `ChangeState`, `LaunchPad`, `Wielding`
- Java utilities behind block interactions: `BlockHarvestUtils`, `PlacedByInteractionComponent`

## Architecture
```
Entity & World
├── Entity lifecycle
│   ├── SpawnPrefab (PrefabPath at Entity / Block origin)
│   ├── RemoveEntity
│   └── LaunchProjectile (ProjectileId)
├── Player I/O
│   ├── SendMessage (chat)
│   └── UI (OpenCustomUI)
├── Inventory
│   ├── EquipItem
│   └── ModifyInventory
├── Blocks
│   ├── BreakBlock
│   ├── PlaceBlock
│   ├── PlaceFluid
│   ├── Door / OpenContainer (server-side block interactions)
│   └── Explode (ExplosionConfig)
└── Entity state & physics
    ├── ChangeState (state-machine transition)
    ├── LaunchPad
    └── Wielding (blocking / guarding)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `SpawnPrefabInteraction` | `config/server/SpawnPrefabInteraction` | Spawns entity prefabs at a location |
| `RemoveEntityInteraction` | `config/none/simple/RemoveEntityInteraction` | Despawns entities from the world |
| `LaunchProjectileInteraction` | `config/server/LaunchProjectileInteraction` | Fires projectiles from an entity |
| `SendMessageInteraction` | `config/none/simple/SendMessageInteraction` | Sends chat messages to players |
| `OpenCustomUIInteraction` | `config/server/OpenCustomUIInteraction` | Opens a custom UI page |
| `EquipItemInteraction` | `config/server/EquipItemInteraction` | Equips an item |
| `ModifyInventoryInteraction` | `config/server/ModifyInventoryInteraction` | Adjusts inventory contents |
| `BreakBlockInteraction` | `config/client/BreakBlockInteraction` | Breaks a targeted block |
| `PlaceBlockInteraction` | `config/client/PlaceBlockInteraction` | Places a block |
| `PlaceFluidInteraction` | `config/client/PlaceFluidInteraction` | Places a fluid at the targeted block |
| `DoorInteraction` | `config/server/DoorInteraction` | Opens/closes doors and gates (incl. double doors) |
| `OpenContainerInteraction` | `config/server/OpenContainerInteraction` | Opens a container block's inventory window |
| `ExplodeInteraction` | `config/client/ExplodeInteraction` | Explosion with block and entity damage |
| `BlockHarvestUtils` | `server.core.modules.interaction` | Java helpers: block damage, breaking, drops |
| `PlacedByInteractionComponent` | `server.core.modules.interaction.components` | Chunk-store component recording who placed a block |
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
| [PlaceFluid](#placefluid) | Place a fluid into the world |
| [Door](#door) | Open/close doors and gates |
| [OpenContainer](#opencontainer) | Open a container block's window |
| [Explode](#explode) | Explosion with block and entity damage |
| [ChangeState](#changestate) | Change entity state machine state |
| [LaunchPadInteraction](#launchpadinteraction) | Launch pad physics |
| [WieldingInteraction](#wieldinginteraction) | Blocking and guarding mechanics |
| [Java Block Utilities](#java-block-utilities) | BlockHarvestUtils, PlacedByInteractionComponent |

---

## SpawnPrefab

**Package:** `config/server/SpawnPrefabInteraction`

Spawns a prefab at the current location.

### Structure

```json
{
  "Type": "SpawnPrefab",
  "PrefabPath": "Goblin_Thief_Chest.prefab.json",
  "Offset": { "X": 0, "Y": 0, "Z": 0 },
  "RotationYaw": "OneEighty",
  "OriginSource": "Entity",
  "Force": true
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `PrefabPath` | string | Prefab file to paste (e.g. `Goblin_Thief_Chest.prefab.json`) |
| `Offset` | object | `{X, Y, Z}` integer offset from the origin |
| `RotationYaw` | string | `None`, `Ninety`, `OneEighty`, or `TwoSeventy` |
| `OriginSource` | string | `Entity` (position of the interacting entity) or `Block` (position of the targeted block) |
| `Force` | boolean | Paste even where placement would otherwise be rejected |

### Example: Goblin Thief dropping its loot chest

From `Server/Item/Interactions/NPCs/Intelligent/Goblin_Thief/Goblin_Thief_Chest.json`:

```json
{
  "Type": "SpawnPrefab",
  "PrefabPath": "Goblin_Thief_Chest.prefab.json",
  "Offset": { "X": 0, "Y": 0, "Z": 0 },
  "RotationYaw": "OneEighty",
  "OriginSource": "Entity",
  "Force": true
}
```

---

## RemoveEntity

**Package:** `config/none/simple/RemoveEntityInteraction`

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
| `Entity` | string | Which entity to remove — `User` (the executor; every shipped use), `Owner` or `Target` (`InteractionTarget`; codec doc: "The entity to target for this interaction.") |
| `Effects` | object | Optional sound/particle effects played on removal (inherited `Effects`) |

### Example: Projectile self-removal on hit

From `Weapons/Bow/Prototype/CombatBow/Bow_Combat_Projectile_Damage_End.json` (run as the projectile's `ProjectileHit` chain, so `User` is the projectile):

```json
{
  "Type": "RemoveEntity",
  "Entity": "User",
  "Effects": {
    "LocalSoundEventId": "SFX_Daggers_T2_Stab_Impact",
    "WorldSoundEventId": "SFX_Daggers_T2_Stab_Impact"
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
  "ProjectileId": "Arrow_FullCharge"
}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `ProjectileId` | string | Projectile config ID |
| `IgnorePitch` | boolean | 0.6.3+. Codec doc: "If true, the shooter's pitch is set to 0 before the launch direction is computed, so the projectile's pitch is fixed by RotationOffset." |
| `IgnoreYaw` | boolean | 0.6.3+. Same for yaw |
| `IgnoreRoll` | boolean | 0.6.3+. Same for roll |
| `RotationOffset` | object | 0.6.3+. `{Yaw, Pitch, Roll}` `Direction`; codec doc: "A fixed rotation offset (in degrees) added to the launch rotation after any ignored axes are zeroed." |

Apart from the 0.6.3 launch-rotation controls, `ProjectileId` is the interaction's only own property — speed, gravity, spawn offset,
and spread all live on the referenced projectile config, not on the interaction.
Charged bows fire stronger shots by launching a different projectile per charge level
(`Arrow_NoCharge` / `Arrow_HalfCharge` / `Arrow_FullCharge`), and the interaction can
still carry inherited properties such as `RunTime` and `Effects`.

See [projectiles.md](projectiles.md) for more projectile details.

---

## SendMessage

**Package:** `config/none/simple/SendMessageInteraction`

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
| `Target` | string | 0.6.3+. Codec doc: "The set of players that receive the message." `Owner` (default — the chain's owning entity), `World` (every player in the executor's world) or `Universe` (every player on the server) |

With `Owner`, if the owning entity has no `PlayerRef` (e.g. an NPC chain) the message is written to the server log at INFO instead.

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
    "RepairPenalty": 0.2
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
| `Shop` | `ShopId` (string) | Shop interface (`ShopPageSupplier`) |
| `Memories` / `MemoriesUnlocked` | - | Memories/journal pages |
| `PrefabSpawner`, `BlockSpawner`, `LaunchPad`, `ConfigInstanceBlock` | - | Block-entity settings pages (registered via `registerBlockEntityCustomPage`) |

Other page ids used by shipped assets: `Teleporter`, `PortalDevice`, `Arcanebench`, `Workbench`.

#### Example: Item Repair Interaction

From `Server/Item/Items/Tool/Repair_Kit/Tool_Repair_Kit_Crude.json`:

```json
{
  "Type": "OpenCustomUI",
  "Page": {
    "Id": "ItemRepair",
    "RepairPenalty": 0.2
  }
}
```

This opens the item repair UI with a 20% durability penalty applied to repairs.

See [UI API - Registering Pages for OpenCustomUI](ui-api.md#registering-pages-for-opencustomui) for creating custom pages that work with this interaction.

---

## Inventory Interactions

### EquipItem

**Package:** `config/server/EquipItemInteraction`

Equips the item currently being held (codec doc: "Equips the item being held."). It has **no properties of its own** — there is no slot or item id to configure; the held stack's own equipment slot decides where it goes:

```json
{
  "Type": "EquipItem"
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
| `AdjustHeldItemDurability` | double | Durability delta for the held item |
| `ItemToRemove` / `ItemToAdd` | item | Remove / add an item stack |
| `BrokenItem` | string | Item the held item turns into when its durability hits 0 |
| `NotifyOnBreak` | boolean | Codec doc: "If true, shows the 'item broken' message and plays the break sound when durability reaches 0. Defaults to true for tools (no BrokenItem or same item), false for transformations (different BrokenItem)." |
| `NotifyOnBreakMessage` | string | "Custom translation key for the break notification message. Supports {itemName} parameter. Defaults to 'server.general.repair.itemBroken' if not specified." |

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

Attempts to break the target block.

```json
{
  "Type": "BreakBlock",
  "Tool": "Scraper",
  "MatchTool": true
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Harvest` | boolean | Trigger as a harvest gather instead of a break gather |
| `SoftOnly` | boolean | 0.6.3+. Codec doc: "Whether this can only break soft blocks, whatever the breaking entity holds." |
| `Tool` | string | Tool to break as |
| `MatchTool` | boolean | Require a match to `Tool` to work |

### PlaceBlock

**Package:** `config/client/PlaceBlockInteraction`

Places the current or given block.

```json
{
  "Type": "PlaceBlock",
  "BlockTypeToPlace": "Tree_Sap_Glob",
  "RemoveItemInHand": true
}
```

| Property | Type | Description |
|----------|------|-------------|
| `BlockTypeToPlace` | string | Overrides the placed block type of the held item with the provided block type |
| `RemoveItemInHand` | boolean | Remove the item in the instigating entity's hand |
| `QuickReplace` | boolean | 0.6.3+. "Replaces the targeted block without requiring it to be broken first. Only honored for players in Creative." |
| `QuickRetype` | boolean | 0.6.3+. "Swaps the targeted block to the held block type while keeping its shape and rotation. Only honored for players in Creative." |
| `NoPhysics` | boolean | 0.6.3+. "Suppresses block physics updates for the placement. Only honored for players in Creative." |

`AllowDragPlacement` was removed by 0.6.3 — drag/extrude/surface placement are now their own interaction types (`DragPlaceBlock`, `ExtrudePlaceBlock`, `SurfaceDrawPlaceBlock`, `DragEraseBlock`, with `PlaceModeSelect` to switch between them), not a flag on `PlaceBlock`.

### PlaceFluid

**Package:** `config/client/PlaceFluidInteraction`

Places a fluid at the targeted block. Extends [SimpleBlockInteraction](interactions.md#simpleblockinteraction) (but its codec builds on `SimpleInteraction.CODEC`, so it does not expose `UseLatestTarget`).

```json
{
  "Type": "PlaceFluid",
  "FluidToPlace": "Water",
  "RemoveItemInHand": true
}
```

| Property | Type | Description |
|----------|------|-------------|
| `FluidToPlace` | string | Fluid asset key to place (validated against loaded fluids; see [fluids.md](fluids.md)) |
| `RemoveItemInHand` | boolean | Default `true`. Consume the held item when placing (only applies for Adventure-mode players, and only when the held stack's quantity is exactly 1) |

Behavior (from the decompiled source):

- If the fluid's ticker cannot occupy solid blocks and the target block is solid, the fluid is placed one block out, on the face the client hit.
- The fluid is set at its **maximum fluid level** and the block is marked ticking so the fluid starts flowing.
- An unknown `FluidToPlace` key logs `Unknown fluid: %s` and resolves to the unknown fluid.

Java accessors: `getFluidKey()`; `getWaitForDataFrom()` returns `WaitForDataFrom.Client`; `needsRemoteSync()` returns `true`.

---

## Door

**Package:** `config/server/DoorInteraction`

Opens/closes a door block (codec doc: "Opens/Closes a door"). Extends [SimpleBlockInteraction](interactions.md#simpleblockinteraction). Wired to door blocks via `"Interactions": { "Use": "Door" }` in the block's item definition; the door's states themselves are block-state JSON (see [blocks.md](blocks.md)).

```json
{
  "Type": "Door",
  "Horizontal": false
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Horizontal` | boolean | Codec doc: "Whether the door is horizontal (e.g. gates) or vertical (e.g. regular doors)." |

Behavior (from the decompiled source):

- **Open direction depends on where you stand:** a vertical door opens *away* from the interacting entity — `OPENED_OUT` if the entity is in front of the door, otherwise `OPENED_IN`. Opening/closing drives the block interaction states `OpenDoorIn` / `OpenDoorOut` / `CloseDoorIn` / `CloseDoorOut`, and a blocked door checks the `DoorBlocked` state.
- **Double doors:** the paired door (if present) is activated in the mirrored state at the same time.
- Soft blocks inside the door's swept hitbox are broken when the door moves.
- If the door cannot move, the interaction ends in `InteractionState.Failed` (so a `Failed` branch in the chain can react).

Java API:

```java
boolean getIsHorizontal()

// Find the door (and its double-door pairing info) at a position
static DoorInteraction.DoorInfo getDoorAtPosition(ChunkStore chunkStore,
        int x, int y, int z, Rotation rotation)

// DoorInteraction.DoorInfo
BlockType getBlockType()
Vector3i getBlockPosition()
DoorBlockUtils.DoorState getDoorState()   // CLOSED / OPENED_IN / OPENED_OUT (moved to DoorBlockUtils by 0.6.3)
```

---

## OpenContainer

**Package:** `config/server/OpenContainerInteraction`

Opens the item container of the targeted block (codec doc: "Opens the container of the block currently being interacted with."). Extends [SimpleBlockInteraction](interactions.md#simpleblockinteraction) and adds no properties of its own:

```json
{
  "Type": "OpenContainer"
}
```

Behavior (from the decompiled source):

- Looks up the block's `ItemContainerBlock` component and opens a `ContainerBlockWindow` for the player (Bench page). Multiple players can have the same container open — windows are tracked per player UUID.
- The **first** opened window sets the block's `OpenWindow` interaction state (public constant `OPEN_WINDOW`); when the **last** window closes, the `CloseWindow` state (`CLOSE_WINDOW`) is applied. The state's interaction sound plays at the block center.
- If the targeted block has no container component, the player receives the `server.interactions.invalidBlockState` translation message and nothing opens.

See [Inventory API](inventory.md) for the container/window classes themselves.

---

## Explode

**Package:** `config/client/ExplodeInteraction`

Performs an explosion (codec doc: "Performs an explosion using the provided config."). Extends `SimpleInstantInteraction`, so it fires immediately. This is the recommended way to get real AOE from a projectile impact (see the gotchas in [projectiles.md](projectiles.md) and [interactions-combat.md](interactions-combat.md)).

```json
{
  "Type": "Explode",
  "Config": {
    "DamageEntities": true,
    "DamageBlocks": true,
    "BlockDamageRadius": 3,
    "BlockDropChance": 0.5,
    "EntityDamageRadius": 5,
    "EntityDamage": 40
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Config` | object | Required `ExplosionConfig` (codec doc: "The explosion config associated with this projectile.") |

`Config` sub-properties (descriptions are the codec documentation strings):

| Property | Type | Description |
|----------|------|-------------|
| `DamageEntities` | boolean | "Determines whether the explosion should damage entities." |
| `DamageBlocks` | boolean | "Determines whether the explosion should damage blocks." |
| `BlockDamageRadius` | int | "The radius in which blocks should be damaged by the explosion." |
| `BlockDamageFalloff` | float | "The falloff applied to the block damage." |
| `BlockDropChance` | float | "The chance in which a block drops its loot after breaking." |
| `EntityDamageRadius` | float | "The radius in which entities should be damaged by the explosion." |
| `EntityDamage` | float | "The amount of damage to be applied to entities within range." |
| `EntityDamageFalloff` | float | "The falloff applied to the entity damage." |
| `Knockback` | object | "Determines the knockback effect applied to damaged entities." |
| `ItemTool` | object | "The item tool to reference when applying damage to blocks." |
| `Particles` | array | "The particles to spawn when the explosion is triggered." |
| `SoundEventId` | string | "The sound event played to surrounding players when the explosion is triggered." (must be a mono sound event) |

Behavior (from the decompiled source):

- **Explosion origin**, in priority order: the `HIT_LOCATION` meta value if present; else the targeted block's center (for collision-triggered interaction types); else the executing entity's position.
- If the executing entity is a projectile, damage is attributed as a projectile source (shooter = owning entity); otherwise the environment source `"explosion"` is used (public constant `DAMAGE_SOURCE_EXPLOSION`).

---

## ChangeState

**Package:** `config/client/ChangeStateInteraction`

Changes block or entity state machine state. Used for toggleable blocks (torches, lanterns), traps, and temporary state effects.

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `Changes` | object | State transition map defining from→to state mappings (codec doc: "`\"default\"` can be used for the initial state of a block.") |
| `Effects` | object | Sound/particle effects triggered on state change |
| `RunTime` | float | Duration in seconds before `Next` interaction executes |
| `Next` | interaction | Chained interaction to execute after `RunTime` |
| `UpdateBlockState` | boolean | Force visual state update after change |
| `RequireBlockPlacement` | boolean | 0.6.3+. Codec doc: "When set, the state change is treated as a block placement and only runs in worlds where block placement is allowed." (used by `Block/Half_Block.json`, whose `default → Block` change stands in for placing a half block) |

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

ChangeState works with the block's state machine defined in its BlockType configuration.
For example, fence blocks override their `Supporting` faces per state (from
`Server/Item/Items/Build/Build_Grey/Build_Grey_Fence.json`):

```json
{
  "State": {
    "Definitions": {
      "Corner": {
        "CustomModel": "...",
        "HitboxType": "...",
        "Supporting": {
          "Down": [{ "FaceType": "Fence_Corner" }],
          "Up": [{ "FaceType": "Fence_Corner" }]
        }
      }
    }
  }
}
```

Each state in `Definitions` can override block properties like collision, light emission,
and support behavior — the real support keys are `Support` (required-support conditions,
per face), `Supporting` (faces this block offers to others), `SupportsRequiredFor`,
`MaxSupportDistance`, and `SupportDropType`. The `Changes` map references these state names.

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

Send every colour (and `default`) to one target colour — `Block/Lantern/Lantern_Blue.json`, the `Next` of a `BlockCondition` that first checks the block is `Furniture_Human_Ruins_Lantern`:

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "Blue",
    "Yellow": "Blue",
    "Red": "Blue",
    "White": "Blue",
    "Cyan": "Blue",
    "Green": "Blue",
    "Pink": "Blue",
    "Purple": "Blue"
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

Temporary state with automatic reversion using `RunTime` and `Next` (from `MISC/Prototype_Geyser.json`; the root also carries a 5 s `Cooldown`):

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "On",
    "On": "default"
  },
  "RunTime": 3,
  "Next": {
    "Type": "ChangeState",
    "Changes": {
      "default": "On",
      "On": "default"
    }
  },
  "UpdateBlockState": true
}
```

The geyser toggles to `On`, waits 3 seconds, then the same toggle map flips it back to `default`.

#### With Sound Effects (Trophy)

State change with audio feedback (from `Deco/Deco_Trophy_Harvest.json`):

```json
{
  "Type": "ChangeState",
  "Changes": {
    "default": "Off",
    "On": "Off",
    "Off": "On"
  },
  "Effects": {
    "LocalSoundEventId": "SFX_Plushie_Interact"
  }
}
```

### File Locations

Example assets using ChangeState (all under `Server/Item/`; block definitions live in the item files):
- `Items/Wood/Wood_Torch_Wall.json` - Simple toggle
- `Interactions/Block/Lantern/Lantern_Blue.json` - Multi-state (one file per colour)
- `Items/Trap/Survival_Trap_Snapjaw.json` - One-way trap (`default → Closed` on `CollisionEnter`; a separate `Closed → default` resets it)
- `Items/MISC/Prototype_Geyser.json` - Timed with RunTime/Next
- `Items/Deco/Deco_Trophy_Harvest.json` - Effects property

### Related

- [BlockCondition](interactions-flow.md#blockcondition) - Check current block state
- [State.Definitions](items-blocks.md#block-states) - Define block states and their property overrides

---

## LaunchPadInteraction

**Package:** `config/server/LaunchPadInteraction`

Applies the launchpad forces. The interaction itself has **no own codec fields** — it is
just `{ "Type": "LaunchPad" }`, wired to the block's `CollisionEnter` interaction slot.
The launch velocity comes from the block entity's `LaunchPad` component
(`world/meta/state/LaunchPad`), whose per-placement values are edited in-game via the
pad's settings UI:

```json
{
  "Type": "LaunchPad"
}
```

`LaunchPad` component keys:

| Property | Type | Description |
|----------|------|-------------|
| `VelocityX` | double | The X velocity of the launch pad |
| `VelocityY` | double | The Y velocity of the launch pad |
| `VelocityZ` | double | The Z velocity of the launch pad |
| `PlayersOnly` | boolean | Determines whether only players can use this launch pad |

On collision the velocity is applied with `ChangeVelocityType.Set` (replacing the
entity's velocity, not adding to it). From
`Server/Item/Items/Electrum/Portal/Launchpad.json`:

```json
{
  "BlockType": {
    "BlockEntity": {
      "Components": {
        "LaunchPad": {}
      }
    },
    "Interactions": {
      "CollisionEnter": {
        "Interactions": [
          { "Type": "LaunchPad" }
        ]
      }
    }
  }
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
| `AllowIndefiniteHold` | boolean | `true` for Wielding (`false` on a plain `Charging`) | If `true`, block can be held indefinitely |
| `CancelOnOtherClick` | boolean | `true` | If `true`, interaction cancels when another input is pressed — the shipped weapon guards set it to `false` so `Forks` can fire |
| `FailOnDamage` | boolean | `false` | Codec doc: "Whether the interaction will be cancelled and the item removed when the entity takes damage" |
| `HorizontalSpeedMultiplier` | float | `1.0` | Movement speed while blocking (0.0-1.0) — from the `Interaction` base |
| `DisplayProgress` | boolean | `true` | Show guard duration indicator |
| `OnItemChangeBehavior` | string | `Cancel` | From the `Interaction` base; the shipped guards use `Finish` so swapping items ends the guard cleanly (see [interactions.md](interactions.md#held-item-change-behavior)) |

### File Locations

**Player weapon guards:**
```
Server/Item/Interactions/Weapons/{WeaponType}/Secondary/Guard/Weapon_{WeaponType}_Secondary_Guard_Wield.json
```

Weapon types with guard: Sword (under `Weapons/Sword/Attacks/Secondary/Guard/`), Shield, Battleaxe, Daggers, Mace, Crossbow, Shortbow; plus the shared `Weapons/Common/Guarding/Common_Guard_Wield.json`

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
    "Interactions": [
      {
        "Type": "Replace",
        "Var": "Guard_Bash",
        "DefaultOk": true,
        "DefaultValue": {
          "Interactions": ["Weapon_Sword_Secondary_Guard_Bash"]
        }
      }
    ]
  }
}
```

`Forks` is a map of [`InteractionType`](interactions.md#interactiontype-enum) → interaction (codec doc: "A collection of interactions to fork into when the input associated with the interaction type is used."). Because `CancelOnOtherClick` defaults to `true`, a fork only gets a chance to fire if the guard sets it to `false`.

| Fork Key | Trigger | Common Use |
|----------|---------|------------|
| `Primary` | Primary click while blocking | Shield bash, guard counter |
| `Secondary` | Secondary click while blocking | Alternate guard action |

**Guard Bash Pattern:**

The shipped guards (above, from `Weapon_Sword_Secondary_Guard_Wield.json`) wrap a `Replace` in the fork so an item can override the bash via its `InteractionVars` (`Guard_Bash`), falling back to the weapon's own `*_Secondary_Guard_Bash` interaction when the var is unset (`DefaultOk`).

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
| `CostType` | string | `Damage` — `Value` is how much blocked damage one stamina point is worth; `MaxHealthPercentage` (the default) — `Value` is the fraction of max health one stamina point is worth (codec doc: "for 4% of max health, the value expected here is 0.04"; default `0.04`) |
| `Value` | float | Per `CostType` above; must be ≥ 0 |

**Real values:** Every shipped weapon guard uses `"CostType": "Damage", "Value": 7`.

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

**Parry Example (from `_Debug/Debug_Stick_Parry.json`):**

A parry is a wielding that ends on the first hit (`FailOnDamage`) and triggers a riposte from `BlockedInteractions` — here a short step back (`ApplyForce` always acts on the **user**), the `Stick_Attack` counter and a cooldown reset, run in `Parallel`:

```json
{
  "Type": "Wielding",
  "Effects": { "ItemAnimationId": "Guard", "ClearAnimationOnFinish": true },
  "RunTime": 5,
  "FailOnDamage": true,
  "DamageModifiers": { "Physical": 0 },
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "Parallel",
        "Interactions": [
          {
            "Interactions": [
              { "Type": "Simple", "RunTime": 0.1 },
              {
                "Type": "ApplyForce",
                "WaitForGround": false,
                "Forces": [ { "Direction": { "X": 0, "Y": 0, "Z": -1 }, "Force": 10 } ],
                "VelocityConfig": { "AirResistance": 0.93, "GroundResistance": 0.93 }
              }
            ]
          },
          { "Interactions": [ "Stick_Attack" ] }
        ]
      },
      {
        "Type": "ResetCooldown",
        "Cooldown": { "Id": "Debug_Stick_Parry", "Cooldown": 0.5 }
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

**Full Sword Guard Configuration** (`Weapons/Sword/Attacks/Secondary/Guard/Weapon_Sword_Secondary_Guard_Wield.json`, verbatim):

```json
{
  "Type": "Wielding",
  "OnItemChangeBehavior": "Finish",
  "Effects": {
    "ItemAnimationId": "Guard",
    "ClearAnimationOnFinish": true,
    "WorldSoundEventId": "SFX_Light_Melee_T2_Block",
    "LocalSoundEventId": "SFX_Sword_T2_Block_Local"
  },
  "Forks": {
    "Primary": {
      "Interactions": [
        {
          "Type": "Replace",
          "Var": "Guard_Bash",
          "DefaultOk": true,
          "DefaultValue": { "Interactions": ["Weapon_Sword_Secondary_Guard_Bash"] }
        }
      ]
    }
  },
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 90,
    "DamageModifiers": { "Physical": 0, "Projectile": 0, "Poison": 0 },
    "KnockbackModifiers": { "Physical": 0.25, "Projectile": 0.25 }
  },
  "StaminaCost": { "Value": 7, "CostType": "Damage" },
  "CancelOnOtherClick": false,
  "Failed": {
    "Type": "Replace",
    "Var": "Guard_Break",
    "DefaultOk": true,
    "DefaultValue": {
      "Interactions": [
        {
          "Type": "Simple",
          "Effects": {
            "Particles": [ { "SystemId": "Shield_Shatter" } ],
            "WorldSoundEventId": "SFX_Light_Melee_T2_Guard_Break",
            "LocalSoundEventId": "SFX_Light_Melee_T2_Guard_Break"
          }
        }
      ]
    }
  },
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Light_Melee_T2_Guard_Hit",
    "WorldParticles": [ { "SystemId": "Shield_Block" } ]
  },
  "Next": {
    "Type": "ChangeStat",
    "Behaviour": "Min",
    "OnItemChangeBehavior": "Ignore",
    "StatModifiers": { "StaminaRegenDelay": -0.5 }
  }
}
```

Note what the real file does *not* do: no `BlockedInteractions` (signature-energy-on-block is a pattern, not the sword's default), and the guard-break `Failed` branch is just particles + sound — the stagger comes from the stamina system, not from an `ApplyEffect` here.

**Simple NPC Block** (`NPCs/Undead/Skeleton_Knight/Skeleton_Knight_Shield_Block.json` — a 0.1 s `Simple` "prepare" step, then the guard):

```json
{
  "Type": "Simple",
  "Effects": {
    "ItemPlayerAnimationsId": "Skeleton_Shield",
    "ItemAnimationId": "Guard",
    "ClearAnimationOnFinish": true
  },
  "RunTime": 0.1,
  "Next": {
    "Type": "Wielding",
    "Effects": { "ItemAnimationId": "Guard", "ClearAnimationOnFinish": true },
    "DamageModifiers": { "Physical": 0.2, "Projectile": 0.2 }
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
            "Direction": { "X": 0, "Y": 0, "Z": -1 },
            "AdjustVertical": false,
            "Force": 10
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

- **Inheritance** - WieldingInteraction inherits all properties from ChargingInteraction, including progress display, `Forks`/`Failed` and the `Next` map system. Its constructor flips `AllowIndefiniteHold` to `true`, so a guard with no `RunTime` holds until released.

- **`ApplyForce` acts on the user** - it has no `Entity` property (codec doc: "A collection of forces to apply to the user"), so a "knock the attacker back" riposte cannot be expressed with it; `ApplyEffect` does take `Entity: "Target"`.

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

## Java Block Utilities

Server-side helpers behind the block interactions on this page. Java API, not JSON.

### BlockHarvestUtils

**Package:** `com.hypixel.hytale.server.core.modules.interaction`

Static utilities implementing block damage, breaking, pickup, and drops. Used by `BreakBlock`/`DestroyBlock` interactions, doors (soft-block clearing), explosions, and the block-physics plugins — and useful from your own plugin when you want block breaking that respects tools, durability, and drop lists.

```java
// Damage a block (returns true when handled). 0.6.3 added a `boolean softOnly` (see BreakBlock's
// SoftOnly) to both overloads, a separate `instigator` ref (the entity credited with the break —
// e.g. the shooter of a projectile — next to the executing `ref`), and a multi-block overload that
// damages a whole `targets` list at once and returns the number of blocks handled.
static boolean performBlockDamage(Vector3i targetBlock, ItemStack itemStack, ItemTool tool,
        float damageScale, int setBlockSettings, boolean softOnly, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)
static boolean performBlockDamage(Ref<EntityStore> ref, Ref<EntityStore> instigator, Vector3i targetBlock,
        ItemStack itemStack, ItemTool tool, String toolId, boolean matchTool, float damageScale,
        int setBlockSettings, boolean softOnly, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)
static int performBlockDamage(Ref<EntityStore> ref, Ref<EntityStore> instigator, List<Vector3i> targets,
        Vector3i primaryTarget, ItemStack itemStack, ItemTool tool, String toolId, boolean matchTool,
        float damageScale, int setBlockSettings, boolean softOnly, boolean applyDurabilityPerBlock,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)

// Break a block outright (with drops). The BlockType overloads let you override drop
// item/list/quantity (the former `World`-first overload was removed by 0.6.3 — the world is
// resolved from the accessors); a List<Vector3i> overload breaks several blocks and returns the count.
static void performBlockBreak(Ref<EntityStore> ref, ItemStack heldItemStack, Vector3i targetBlock,
        Ref<ChunkStore> chunkReference, ComponentAccessor<EntityStore> entityStore,
        ComponentAccessor<ChunkStore> chunkStore)
static void performBlockBreak(Ref<EntityStore> ref, ItemStack heldItemStack, Vector3i targetBlock,
        int setBlockSettings, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)
static void performBlockBreak(Ref<EntityStore> ref, Ref<EntityStore> instigator, ItemStack heldItemStack,
        Vector3i targetBlock, int setBlockSettings, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)
static int performBlockBreak(Ref<EntityStore> ref, ItemStack heldItemStack, List<Vector3i> targets,
        int setBlockSettings, ComponentAccessor<EntityStore> entityStore,
        ComponentAccessor<ChunkStore> chunkStore)
static void performBlockBreak(Vector3i blockPosition, BlockType targetBlockType, ItemStack heldItemStack,
        int dropQuantity, String dropItemId, String dropListId, int setBlockSettings,
        Ref<EntityStore> ref, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)
static void performBlockBreak(Vector3i blockPosition, BlockType targetBlockType, ItemStack heldItemStack,
        int dropQuantity, String dropItemId, String dropListId, int setBlockSettings,
        Ref<EntityStore> ref, Ref<EntityStore> instigator, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)

// "Natural" removal (physics-driven, e.g. support lost), replacing with a filler block id
static void naturallyRemoveBlockByPhysics(Vector3i blockPosition, BlockType blockType, int filler,
        int setBlockSettings, Ref<ChunkStore> chunkReference,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)
static void naturallyRemoveBlock(Vector3i blockPosition, BlockType blockType, int filler,
        int quantity, String itemId, String dropListId, int setBlockSettings,
        Ref<ChunkStore> chunkReference, ComponentAccessor<EntityStore> entityStore,
        ComponentAccessor<ChunkStore> chunkStore)

// Blocks picked up directly into the inventory instead of breaking
static boolean shouldPickupByInteraction(BlockType blockType)
static void performPickupByInteraction(Ref<EntityStore> ref, Vector3i targetBlock,
        BlockType blockType, int filler, Ref<ChunkStore> chunkReference, BlockSection blockSection,
        ComponentAccessor<EntityStore> entityStore, ComponentAccessor<ChunkStore> chunkStore)

// Compute the drop stacks for a block (drop-list aware)
static List<ItemStack> getDrops(BlockType blockType, int quantity, String itemId, String dropListId)

// 0.6.3+: run a block type's OnBreak / OnBreakImpact interactions (the two InteractionTypes added in 0.6.3)
static void fireOnBreakInteraction(Ref<EntityStore> ref, Ref<EntityStore> instigator, BlockType blockType,
        Vector3i blockPosition, int rotationIndex, int blockId, ComponentAccessor<EntityStore> entityStore)
static void queueOnBreakImpactInteraction(Ref<EntityStore> ref, BlockType blockType, Vector3i blockPosition,
        int blockId, CommandBuffer<EntityStore> commandBuffer)
```

Removed by 0.6.3 with no direct replacement: `getSpecPowerDamageBlock(Item, BlockType, ItemTool)` and
`calculateDurabilityUse(Item, BlockType)` — tool/spec resolution and durability now happen inside
`performBlockDamage` (see `ItemTool.getBreakShape()` / `getBreakShapeDurabilityMode()` for the new
multi-block "break shape" durability rules).

See [drops.md](drops.md) for how drop lists are defined.

### PlacedByInteractionComponent

**Package:** `com.hypixel.hytale.server.core.modules.interaction.components`

Chunk-store component (serialized id `PlacedByInteraction`, registered by `InteractionModule`) that records **which player placed a block**. It is attached to the block's chunk-store entry by the block-placement path when a player places a block, and can be read by systems that care about ownership — e.g. the builtin teleporter creates a warp for the placing player when a teleporter block gains this component.

```java
public static final BuilderCodec<PlacedByInteractionComponent> CODEC;

static ComponentType<ChunkStore, PlacedByInteractionComponent> getComponentType()

PlacedByInteractionComponent()
PlacedByInteractionComponent(UUID whoPlacedUuid)

UUID getWhoPlacedUuid()
Component<ChunkStore> clone()
```

The component type is also reachable via `InteractionModule.get().getPlacedByComponentType()` (see [interactions.md](interactions.md#interactionmodule)).

---

## Gotchas & Errors

Backtick-quoted error strings below are literal messages from the server (verified against `HytaleServer.jar`).

- **`Unknown fluid: <key>`** (`PlaceFluidInteraction`) → `FluidToPlace` names a fluid that isn't loaded; the interaction falls back to the unknown fluid. Fix: use a key from the fluid asset store (see [fluids.md](fluids.md)).
- **`server.interactions.invalidBlockState`** (translation message sent to the player by `OpenContainerInteraction`) → the targeted block has no `ItemContainerBlock` component. Fix: only wire `OpenContainer` to container blocks.
- **`No projectile config typeName provided`** (`ProjectileComponent`) → a `LaunchProjectile` (or the projectile prefab it references) is missing its projectile config type. Fix: point `ProjectileId` at a prefab that defines a valid projectile config.
- **`has no valid ProjectileConfig:`** (`ProjectileInteraction`) → the referenced projectile prefab exists but carries no usable `ProjectileConfig`. Fix: verify the projectile asset is fully defined, not just present.
- **Symptom:** a `ChangeState` does nothing → the current state isn't a key in the `Changes` map, so no transition matches (the codec does not validate the map — a self-mapping like `"Off": "Off"` loads fine and is simply a no-op). Fix: include the entity/block's actual current state as a key, and confirm the target state exists in the block's `State.Definitions`.
- **Symptom:** a `ChangeState` with `RequireBlockPlacement` never fires → it is treated as block placement and is skipped in worlds where placement is disallowed. Fix: drop the flag unless the state change really stands in for placing a block.
- **Symptom:** a `SpawnPrefab` spawns nothing → `PrefabPath` doesn't resolve to a stored prefab. Fix: use the prefab's file name as registered in the prefab store (e.g. `Goblin_Thief_Chest.prefab.json`).
