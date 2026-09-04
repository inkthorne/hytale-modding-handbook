---
title: "Interactions API"
description: "Hytale interactions in JSON — the Interaction base class and SimpleInteraction hierarchy, root vs nested interactions, input-triggered entry points, and asset-store registration."
seo:
  type: TechArticle
---

# Interactions API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.6.3**

> **Note:** For `InteractionManager` (the entity component that manages interaction chains), see [entities.md](entities.md#interactionmanager).
>
> **See also:**
> - [Operation System](interactions-operations.md) - Low-level execution model and flow control
> - [InteractionContext](interactions-context.md) - Execution state and data access
> - [Item Definitions](items.md) - How items define and customize interactions via `InteractionVars`

This page covers the interaction system: the data-driven actions entities perform (attacks, abilities, item uses), how they are defined as JSON assets, and how they are triggered, gated, and configured.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.interaction.interaction.config` and provides:
- A base `Interaction` abstract class with a `SimpleInteraction` / `SimpleInstantInteraction` hierarchy
- Root vs nested interactions: input-triggered entry points and reusable building blocks
- Asset-store lookup of interactions by string ID
- A meta-key store for passing targeting/hit/damage data between steps
- Per-`GameMode` settings and cooldown configuration
- Conflict rules (`InteractionRules`) for blocking and interrupting between interaction types

## Architecture
```
Interaction System
├── RootInteraction (Server/Item/RootInteractions/)
│   ├── triggered by input (PRIMARY, SECONDARY, ...)
│   ├── RootInteractionSettings (per-GameMode + cooldown)
│   └── references nested Interactions
├── Nested Interaction (Server/Item/Interactions/)
│   ├── SimpleInteraction → SimpleInstantInteraction
│   └── composed via Serial / Parallel / Condition (see interactions-flow.md)
├── Asset lookup (Interaction.getInteractionOrUnknown / getAssetStore / getAssetMap)
├── Meta keys (TARGET_ENTITY, HIT_LOCATION, DAMAGE, ...) — see interactions-context.md
├── InteractionRules (blockedBy / blocking / interruptedBy / interrupting)
├── CooldownHandler (per-entity cooldown timers)
└── InteractionSettings / RootInteractionSettings (per-GameMode behavior)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Interaction` | `server.core.modules.interaction.interaction.config` | Abstract base for all interactions; identity, effects, rules, asset lookup |
| `SimpleInteraction` | `server.core.modules.interaction.interaction.config` | Base building-block interaction (delays, animations, sounds, flow) |
| `SimpleInstantInteraction` | `server.core.modules.interaction.interaction.config` | Abstract base for instant (no-duration) interactions |
| `RootInteraction` | `server.core.modules.interaction.interaction.config` | Input-triggered entry-point interaction; holds settings and cooldowns |
| `CooldownHandler` | `server.core.modules.interaction.interaction` | Manages per-entity cooldown timers |
| `InteractionRules` | `server.core.modules.interaction.interaction.config` | Block/interrupt conflict rules between interaction types |
| `InteractionSettings` | `protocol` | Per-`GameMode` settings for a nested interaction |
| `RootInteractionSettings` | `protocol` | Per-`GameMode` settings + cooldown for a root interaction |
| `InteractionType` | `protocol` | Enum of interaction trigger types (PRIMARY, SECONDARY, ...) |
| `SimpleBlockInteraction` | `server.core.modules.interaction.interaction.config.client` | Abstract base for block-targeting interactions (client-supplied target block) |
| `InteractionItemChangeBehavior` | `protocol` | Enum: what an interaction does when the held item changes (`Cancel`/`Fail`/`Finish`/`Ignore`) |
| `InteractionModule` | `server.core.modules.interaction` | Core plugin that registers interaction assets, components, and all built-in `Type` strings |
| `InteractionValidation` | `server.core.modules.interaction.interaction.util` | Static server-side range checks for player block/entity interactions |
| `OriginSource` | `server.core.modules.interaction.interaction.config` | Enum: position interactions relative to the entity or the targeted block |
| `RelativeRotationMode` | `server.core.modules.interaction.interaction.config` | Enum: how much of a reference rotation (none/yaw/full) to apply |

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Operation System](interactions-operations.md) | `interactions-operations.md` | Low-level execution model, OperationsBuilder, labels |
| [InteractionContext](interactions-context.md) | `interactions-context.md` | Execution state, entity refs, meta store, InteractionVars |
| [Combo Systems](interactions-combo.md) | `interactions-combo.md` | Chaining, charging, input branching |
| [Combat & Effects](interactions-combat.md) | `interactions-combat.md` | Damage, forces, status effects, animations |
| [Control Flow](interactions-flow.md) | `interactions-flow.md` | Serial, parallel, conditions, targeting |
| [Entity & World](interactions-world.md) | `interactions-world.md` | Spawning, inventory, blocks, wielding |

### Interaction Documentation Index

A curated reading path through the types that have a written section, grouped by the page that
covers them. It is **not** the full vocabulary: as of build-26, `Interaction.CODEC` carries **124**
registered `Type` values, of which 82 have a written section on another page, 12 are documented in
their registry rows themselves, and 30 are not yet documented. For the complete list — and to
tell "undocumented" apart from "does not exist" — see
[Complete Type Registry](#complete-type-registry) below.

**Combo Systems** ([interactions-combo.md](interactions-combo.md))
- [ChainingInteraction](interactions-combo.md#chaininginteraction) - Sequential combo chains with timing windows
- [FirstClickInteraction](interactions-combo.md#firstclickinteraction) - Branch based on tap vs hold input
- [ChargingInteraction](interactions-combo.md#charginginteraction) - Charge-and-release mechanics
- [ChainFlagInteraction](interactions-combo.md#chainflaginteraction) - Set flags for cross-chain communication
- [CancelChainInteraction](interactions-combo.md#cancelchaininteraction) - Reset chain state to beginning

**Combat & Effects** ([interactions-combat.md](interactions-combat.md))
- [SimpleInteraction](interactions-combat.md#simpleinteraction) - Delays, animations, sounds, and flow control
- [Selector](interactions-combat.md#selector) - Target selection for melee attacks (hitboxes)
- [DamageEntity](interactions-combat.md#damageentity) - Deal damage with effects, knockback, and stat grants
- [ApplyForce](interactions-combat.md#applyforce) - Apply physics forces for knockback and launches
- [ApplyEffect](interactions-combat.md#applyeffect) - Apply status effects (buffs, debuffs, DoT)
- [ClearEntityEffect](interactions-combat.md#clearentityeffect) - Remove status effects from entities
- [ChangeStat](interactions-combat.md#changestat) - Modify health, stamina, signature energy
- [InterruptInteraction](interactions-combat.md#interruptinteraction) - Cancel an entity's current interaction chain

**Control Flow** ([interactions-flow.md](interactions-flow.md))
- [Serial](interactions-flow.md#serial) - Execute interactions sequentially
- [Parallel](interactions-flow.md#parallel) - Execute interactions concurrently
- [Condition](interactions-flow.md#condition) - Game mode and movement state branching
- [StatsCondition](interactions-flow.md#statscondition) - Branch based on entity stat values
- [EffectCondition](interactions-flow.md#effectcondition) - Branch based on active status effects
- [BlockCondition](interactions-flow.md#blockcondition) - Branch based on block type/state/tag
- [CooldownCondition](interactions-flow.md#cooldowncondition) - Branch based on cooldown completion
- [MovementCondition](interactions-flow.md#movementcondition) - Direction-based input branching
- [PlacementCountCondition](interactions-flow.md#placementcountcondition) - Branch based on block placement count
- [Repeat](interactions-flow.md#repeat) - Loop execution of interactions
- [Replace](interactions-flow.md#replace) - Variable substitution for templates
- [Target Selectors](interactions-flow.md#target-selectors) - AOE, raycast, and sweep targeting

**Entity & World** ([interactions-world.md](interactions-world.md))
- [SpawnPrefab](interactions-world.md#spawnprefab) - Spawn entities at locations
- [RemoveEntity](interactions-world.md#removeentity) - Despawn entities from the world
- [LaunchProjectile](interactions-world.md#launchprojectile) - Fire projectiles
- [SendMessage](interactions-world.md#sendmessage) - Send chat messages to players
- [UI Interactions](interactions-world.md#ui-interactions) - Open UI pages (OpenPage, OpenCustomUI)
- [Inventory Interactions](interactions-world.md#inventory-interactions) - Manage inventory and equipment
- [Block Interactions](interactions-world.md#block-interactions) - Break or place blocks
- [PlaceFluid](interactions-world.md#placefluid) - Place a fluid into the world
- [Door](interactions-world.md#door) - Open/close doors and gates (incl. double doors)
- [OpenContainer](interactions-world.md#opencontainer) - Open a container block's inventory window
- [Explode](interactions-world.md#explode) - Explosion with block and entity damage
- [ChangeState](interactions-world.md#changestate) - Change entity state machine state
- [LaunchPadInteraction](interactions-world.md#launchpadinteraction) - Launch pad physics
- [WieldingInteraction](interactions-world.md#wieldinginteraction) - Blocking and guarding mechanics

**Documented with their subsystem** (0.6.3+)
- [SetGameFlag](world.md#game-flags) - Write a universe-wide named integer flag
- [GameFlagCondition](world.md#game-flags) - Succeed while a game flag is at (or at least) a level
- [SpectateControl](player.md#spectatecontrol-interaction) - Cycle a spectator's follow camera, or detach it to free cam

### Complete Type Registry

Every `Type` value `Interaction.CODEC` accepts, as of **build-26 (0.6.3)** — **124** rows: 82 have a
written section on another page, 12 are documented in their registry rows themselves, and 30 are
not yet documented. A row count is itself a closure claim, and so is each of those three figures, so
re-derive them after a game update rather than trusting this line; the greps that produce them are
given below.

The **Documented** cell has three states, and its first character tells you which:

- **A link** — some page carries a section describing what the type does as an interaction, its JSON
  keys, or both.
- **Prose** — the type has fewer than two keys of its own and no gotcha needing a paragraph, so
  *this row is its documentation*: one line, its own keys with their requiredness, and the
  fully-qualified class last. There is no section to link to and none is owed.
- **`— *not yet documented*`** — neither, yet.

A bare mention in a list, or a name that appears only inside an example, is *not* documentation and
earns neither a link nor a prose cell. Two names are documented in this corpus as something
*other* than an interaction and are still marked `—`: `ShowEventTitle` is also a
[trigger-volume effect type](trigger-volumes.md#built-in-effect-types) with that same name, and
`BuilderTool` is also an item property ([items-tools.md](items-tools.md#builder-tool-args)). Same
string, different registry — the documented one is not the interaction. As each such row fills, the
warning moves into that row's own cell and the name leaves this list.

**Registered by** names the module or plugin whose `setup()` registers the type. `Interaction.CODEC`
is shared, so a type exists only when its owner is loaded. The 76 rows whose owner is listed in
`Constants.CORE_PLUGINS` (`server/core/Constants.java:65`) are always present — that is
`InteractionModule` (75 rows) plus `ProjectileModule` (`Projectile`). The remaining 48 rows come from
19 bundled plugins and are absent whenever their plugin is not loaded. Test membership against
`CORE_PLUGINS` rather than against the owner's name: `ProjectileModule` and `NPCPlugin` are both
engine code, but only the first is core, so `Projectile` is always available while `SpawnNPC`,
`UseNPC`, `ContextualUseNPC` and `SendBeacon` are not.

| `Type` | Registered by | Documented |
|---|---|---|
| `AddItem` | `InteractionModule` | — *not yet documented* |
| `ApplyEffect` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#applyeffect) |
| `ApplyForce` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#applyforce) |
| `AugmentCondition` | `AugmentBlocksPlugin` | — *not yet documented* |
| `Bed` | `BedsPlugin` | [player.md](player.md#bed-interaction) |
| `BlockCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#blockcondition) |
| `BreakBlock` | `InteractionModule` | [interactions-world.md](interactions-world.md#breakblock) |
| `BuilderTool` | `InteractionModule` | — *not yet documented* |
| `Camera` | `InteractionModule` | [camera.md](camera.md#the-camera-interaction-json) |
| `CameraShake` | `CameraPlugin` | Sends one `CameraEffect` asset's shake to the interacting player. One key, `CameraEffect` (a `CameraEffect` asset id, required by `Validators.nonNull()` and validated against the asset map, so a bad id fails at load). It does nothing at all for a non-player entity — `firstRun` returns without setting a failed state when there is no `PlayerRef`. **The string is registered on two codecs**: `CameraEffect.CODEC` as well as `Interaction.CODEC`, and all **49** shipped `"Type": "CameraShake"` assets are `CameraEffect` assets under `Server/Camera/CameraEffect/` — the interaction has **zero** shipped uses, so a usage count mined by grepping the string measures the other registry entirely. `com.hypixel.hytale.builtin.adventure.camera.interaction.CameraShakeInteraction` |
| `CanBreakRespawnPoint` | `ObjectivePlugin` | Succeeds unless the target block carries a `RespawnBlock` component owned by a **different** player; an unowned point, or one the interacting player owns, passes. It also passes when the block has no block entity or no `RespawnBlock` at all, so it only ever blocks someone else's claimed respawn point. Ownership is read from the **owning** entity's `UUIDComponent`, not the interacting one. No keys of its own. Its one shipped use is the head of `Server/Item/RootInteractions/Block/Check_Can_Break_Respawn.json`, whose `Next` chain swings and then runs `BreakBlock` — the root the bed in [player.md](player.md#bed-interaction) wires onto `Primary`. `com.hypixel.hytale.builtin.adventure.objectives.interactions.CanBreakRespawnPointInteraction` |
| `CancelChain` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#cancelchaininteraction) |
| `CarryBlock` | `InteractionModule` | — *not yet documented* |
| `CarryDroppedBlock` | `InteractionModule` | — *not yet documented* |
| `CarryPlaceBlock` | `InteractionModule` | — *not yet documented* |
| `ChainFlag` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#chainflaginteraction) |
| `Chaining` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#chaininginteraction) |
| `ChangeActiveSlot` | `InteractionModule` | — *not yet documented* |
| `ChangeBlock` | `InteractionModule` | [items-tools.md](items-tools.md#changeblock-interaction) |
| `ChangeFarmingStage` | `FarmingPlugin` | — *not yet documented* |
| `ChangeStat` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#changestat) |
| `ChangeState` | `InteractionModule` | [interactions-world.md](interactions-world.md#changestate) |
| `ChangeStatWithModifier` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#changestat) |
| `Charging` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#charginginteraction) |
| `CheckUniqueItemUsage` | `InteractionModule` | A condition **with a side effect**: it fails if the interacting player has already used an item with this item id, and otherwise records the usage on their `UniqueItemUsagesComponent` and succeeds — so running it is what consumes the one allowed use, and the record is permanent and per-item-id, not per-item-stack. A repeat use also sends the player the `server.commands.checkUniqueItemUsage.uniqueItemAlreadyUsed` notification. No keys of its own, and no shipped asset uses it. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.CheckUniqueItemUsageInteraction` |
| `ClearEntityEffect` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#clearentityeffect) |
| `Condition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#condition) |
| `ContextualUseNPC` | `NPCPlugin` | [items-tools.md](items-tools.md#shears) |
| `CooldownCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#cooldowncondition) |
| `CycleBlockGroup` | `InteractionModule` | [items-tools.md](items-tools.md#hammer) |
| `DamageEntity` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#damageentity) |
| `DestroyBlock` | `InteractionModule` | — *not yet documented* |
| `DestroyTaggedVolumes` | `TriggerVolumesPlugin` | [trigger-volumes.md](trigger-volumes.md#commands-tooling) |
| `DestroyTreasureCondition` | `ObjectivePlugin` | Succeeds only once the target treasure chest has been **opened** — `TreasureChestBlock.canDestroy` returns nothing but that chest's `opened` flag — so it is the gate that keeps an unlooted objective chest unbreakable. Passes trivially when the target block has no block entity or no `TreasureChestBlock` on it. No keys of its own. `com.hypixel.hytale.builtin.adventure.objectives.interactions.DestroyTreasureConditionInteraction` |
| `Door` | `InteractionModule` | [interactions-world.md](interactions-world.md#door) |
| `DragEraseBlock` | `InteractionModule` | — *not yet documented* |
| `DragPlaceBlock` | `InteractionModule` | [items-blocks.md](items-blocks.md#block_secondary-interaction) |
| `DurabilityCondition` | `InteractionModule` | [items-weapons.md](items-weapons.md#durabilitycondition-interaction) |
| `EffectCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#effectcondition) |
| `EquipItem` | `InteractionModule` | [interactions-world.md](interactions-world.md#equipitem) |
| `EventStartInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `EventStopInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `ExitInstance` | `InstancesPlugin` | — *not yet documented* |
| `Explode` | `InteractionModule` | [interactions-world.md](interactions-world.md#explode) |
| `ExtrudePlaceBlock` | `InteractionModule` | — *not yet documented* |
| `FertilizeSoil` | `FarmingPlugin` | [items-tools.md](items-tools.md#fertilizer) |
| `FirstClick` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#firstclickinteraction) |
| `GameFlagCondition` | `GameFlagsPlugin` | [world.md](world.md#game-flags) |
| `GlobalEventStartInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `GlobalEventStopInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `HarvestCrop` | `FarmingPlugin` | [items-blocks.md](items-blocks.md#harvestcrop-interaction) |
| `HubPortal` | `CreativeHubPlugin` | — *not yet documented* |
| `IncreaseBackpackCapacity` | `InteractionModule` | — *not yet documented* |
| `IncrementCooldown` | `InteractionModule` | — *not yet documented* |
| `Interrupt` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#interruptinteraction) |
| `LaunchPad` | `InteractionModule` | [interactions-world.md](interactions-world.md#launchpadinteraction) |
| `LaunchProjectile` | `InteractionModule` | [interactions-world.md](interactions-world.md#launchprojectile) |
| `LearnRecipe` | `CraftingPlugin` | [items-crafting.md](items-crafting.md#learning-recipes-learnrecipe) |
| `MemoriesCondition` | `MemoriesPlugin` | [interactions-flow.md](interactions-flow.md#placementcountcondition) |
| `ModifyIntervalConditionInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `ModifyInventory` | `InteractionModule` | [interactions-world.md](interactions-world.md#modifyinventory) |
| `Mount` | `MountPlugin` | [mounts.md](mounts.md#mount-interaction) |
| `MovementCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#movementcondition) |
| `OpenBenchPage` | `CraftingPlugin` | Opens a crafting bench window on the interacting player. One key, `Page` (required by `Validators.nonNull()`), selecting one of `OpenBenchPageInteraction.PageType`'s three constants — `SIMPLE_CRAFTING`, `DIAGRAM_CRAFTING`, `STRUCTURAL_CRAFTING` — which pick a `SimpleCraftingWindow`, `DiagramCraftingWindow` or `StructuralCraftingWindow`. **No shipped asset writes this type**: `CraftingPlugin` builds three instances with the ids `*Simple_Crafting_Default`, `*Diagram_Crafting_Default` and `*Structural_Crafting_Default` and binds them through `Bench.registerRootInteraction` to the `Crafting`, `DiagramCrafting` and `StructuralCrafting` bench types, so a bench of those types opens without naming any interaction. `com.hypixel.hytale.builtin.crafting.interaction.OpenBenchPageInteraction` |
| `OpenContainer` | `InteractionModule` | [interactions-world.md](interactions-world.md#opencontainer) |
| `OpenCustomUI` | `InteractionModule` | [interactions-world.md](interactions-world.md#opencustomui) |
| `OpenItemStackContainer` | `InteractionModule` | — *not yet documented* |
| `OpenPage` | `InteractionModule` | [interactions-world.md](interactions-world.md#ui-interactions) |
| `OpenProcessingBench` | `CraftingPlugin` | Opens the processing-bench window on the interacting player. No keys of its own. It is the **fourth** `BenchType`'s route and the asymmetric one: `Processing` is the one bench type `Bench.registerRootInteraction` is never called for, so `Bench.getRootInteraction()` returns null for it and a processing bench must name the interaction itself — all four shipped ones (`Bench_Furnace`, `Bench_Campfire`, `Bench_Tannery`, `Bench_Salvage`) set `"Interactions": { "Use": "Open_Processing_Bench" }`. `com.hypixel.hytale.builtin.crafting.interaction.OpenProcessingBenchInteraction` |
| `OpenTreasureContainer` | `ObjectivePlugin` | Opens the targeted treasure chest's container window and marks the chest opened, which is what later lets `DestroyTreasureCondition` (this table) pass. It fires [TreasureChestOpeningEvent](adventure.md#treasurechestopeningevent) only when the chest carries an objective UUID, so a chest placed outside an objective opens silently. No keys of its own. `com.hypixel.hytale.builtin.adventure.objectives.interactions.OpenTreasureContainerInteraction` |
| `Parallel` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#parallel) |
| `PickBlock` | `InteractionModule` | — *not yet documented* |
| `PickupItem` | `BuilderToolsPlugin` | — *not yet documented* |
| `PlaceBlock` | `InteractionModule` | [interactions-world.md](interactions-world.md#placeblock) |
| `PlaceFluid` | `InteractionModule` | [interactions-world.md](interactions-world.md#placefluid) |
| `PlacementCountCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#placementcountcondition) |
| `PlaceModeSelect` | `InteractionModule` | [items-blocks.md](items-blocks.md#block_secondary-interaction) |
| `Portal` | `PortalsPlugin` | — *not yet documented* |
| `PortalReturn` | `PortalsPlugin` | — *not yet documented* |
| `PrefabSelectionInteraction` | `BuilderToolsPlugin` | — *not yet documented* |
| `Projectile` | `ProjectileModule` | [projectiles.md](projectiles.md#projectileinteraction) |
| `RefillContainer` | `InteractionModule` | [items-tools.md](items-tools.md#watering-can) |
| `RemoveEntity` | `InteractionModule` | [interactions-world.md](interactions-world.md#removeentity) |
| `Repeat` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#repeat) |
| `Replace` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#replace) |
| `ResetCooldown` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#resetcooldown) |
| `RevealMapMarkersInView` | `InteractionModule` | — *not yet documented* |
| `RunOnBlockTypes` | `InteractionModule` | — *not yet documented* |
| `RunRootInteraction` | `InteractionModule` | Runs a named root interaction, and **does not wait for it**: `firstRun` sets its own state to `Finished` first and then executes the root, so a surrounding chain continues immediately rather than on the root's completion. One key, `RootInteraction` (a root-interaction id, required by `Validators.nonNull()` and late-validated against the `RootInteraction` assets); at runtime an id that still does not resolve yields `RootInteraction.getRootInteractionOrUnknown`'s placeholder rather than an error. No shipped asset uses the type — the only occurrences of the string under `Assets.zip` are `.lang` entries. **Not the trigger-volume effect of the same name** ([trigger-volumes.md](trigger-volumes.md#built-in-effect-types)), which shares the `RootInteraction` key but adds `InteractionType` and `EquipSlot`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.RunRootInteraction` |
| `Seating` | `MountPlugin` | [mounts.md](mounts.md#seating-interaction) |
| `Selector` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#selector) |
| `SendBeacon` | `NPCPlugin` | [npc-roles.md](npc-roles.md#sendbeacon) |
| `SendMessage` | `InteractionModule` | [interactions-world.md](interactions-world.md#sendmessage) |
| `Serial` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#serial) |
| `SetGameFlag` | `GameFlagsPlugin` | [world.md](world.md#game-flags) |
| `SetMemoriesCapacity` | `MemoriesPlugin` | Raises a player's memory capacity to `Capacity`, and **fails when that value is not higher than the current one** — it can only ever increase, so the same item cannot be used twice. Crossing from zero also unlocks the memories feature for that player (an `UpdateMemoriesFeatureStatus` packet plus a notification). One key: `Capacity` (int, not required). One shipped use, `Server/Item/Items/Bench/Bench_Memories.json`. `com.hypixel.hytale.builtin.adventure.memories.interactions.SetMemoriesCapacityInteraction` |
| `ShowEventTitle` | `InteractionModule` | — *not yet documented* |
| `SignalNearbyVolumes` | `TriggerVolumesPlugin` | [trigger-volumes.md](trigger-volumes.md#commands-tooling) |
| `Simple` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#simpleinteraction) |
| `SpawnDeployableAtHitLocation` | `DeployablesPlugin` | [deployables.md](deployables.md#the-three-interactions) |
| `SpawnDeployableAtLocation` | `DeployablesPlugin` | [deployables.md](deployables.md#the-three-interactions) |
| `SpawnDeployableFromRaycast` | `DeployablesPlugin` | [deployables.md](deployables.md#the-three-interactions) |
| `SpawnMinecart` | `MountPlugin` | [mounts.md](mounts.md#spawnminecart-interaction) |
| `SpawnNPC` | `NPCPlugin` | [npc-roles.md](npc-spawning.md#spawnnpc-interaction) |
| `SpawnPrefab` | `InteractionModule` | [interactions-world.md](interactions-world.md#spawnprefab) |
| `SpawnTriggerVolume` | `TriggerVolumesPlugin` | [trigger-volumes.md](trigger-volumes.md#commands-tooling) |
| `SpectateControl` | `InteractionModule` | [player.md](player.md#spectatecontrol-interaction) |
| `StartObjective` | `ObjectivePlugin` | Starts the objective described by its one key, `Setup` (an `ObjectiveTypeSetup` — shipped assets write `{ "Type": "Objective", "ObjectiveId": … }` — required by `Validators.nonNull()`). Starting stamps the new objective's UUID into the **held item stack's** metadata, and a later use of that same stack adds the player to the existing objective instead of starting another. `com.hypixel.hytale.builtin.adventure.objectives.interactions.StartObjectiveInteraction` — note that `com.hypixel.hytale.builtin.adventure.objectiveshop.StartObjectiveInteraction` shares the simple name, is registered on `ChoiceInteraction.CODEC` with a different single key, and is **not** this type |
| `StatsCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#statscondition) |
| `StatsConditionWithModifier` | `InteractionModule` | — *not yet documented* |
| `SurfaceDrawPlaceBlock` | `InteractionModule` | — *not yet documented* |
| `TeleportConfigInstance` | `InstancesPlugin` | — *not yet documented* |
| `Teleporter` | `TeleporterPlugin` | — *not yet documented* |
| `TeleportInstance` | `InstancesPlugin` | — *not yet documented* |
| `ToggleGlider` | `InteractionModule` | Toggles glider movement for the player. No keys of its own, and **no server-side behaviour at all**: `firstRun` is empty and the class exists to emit a protocol `ToggleGliderInteraction` from `generatePacket()`, which is why it lives in the `config.client` package — the client performs the toggle. One shipped use, `Server/Item/Items/Glider/Template_Glider.json`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.ToggleGliderInteraction` |
| `TriggerCooldown` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#triggercooldown) |
| `TriggerSpawnMarkers` | `SpawningPlugin` | [npc-spawning.md](npc-spawning.md#triggerspawnmarkers) |
| `UseBlock` | `InteractionModule` | [items-blocks.md](items-blocks.md#block_secondary-interaction) |
| `UseCaptureCrate` | `FarmingPlugin` | [items-tools.md](items-tools.md#capture-crate) |
| `UseCoop` | `FarmingPlugin` | — *not yet documented* |
| `UseEntity` | `InteractionModule` | [items-weapons.md](items-weapons.md#useentity-interaction) |
| `UseNPC` | `NPCPlugin` | The right-click-an-NPC interaction — it reserves the target NPC for the user, and fails unless the user is a player and the target is an in-range, unreserved `NPCEntity` willing to interact. No keys of its own. **Never written as a `"Type"` in an asset**: `NPCPlugin` loads a code-built instance under the id `*UseNPC`, and `RoleBuilderSystem` binds that id to every NPC's `Use` slot, so no shipped asset names it. `com.hypixel.hytale.server.npc.interactions.UseNPCInteraction` |
| `UseWateringCan` | `FarmingPlugin` | [items-tools.md](items-tools.md#watering-can) |
| `Wielding` | `InteractionModule` | [interactions-world.md](interactions-world.md#wieldinginteraction) |

Both registration forms are load-bearing when re-deriving this table. Most types are registered
directly:

```
grep -rn 'Interaction\.CODEC\.register("' ~/.cache/hytale-jar/src     # 89 names
```

but 35 more reach the same codec through the plugin's registry handle, where the receiver is not
`Interaction.CODEC`, the calls chain (one line in `WorldEventsPlugin` registers seven), and one id is
a constant rather than a literal (`CameraPlugin`'s `CODEC_CAMERA_SHAKE` is `"CameraShake"`):

```
grep -rn 'getCodecRegistry(Interaction\.CODEC)' ~/.cache/hytale-jar/src   # 21 sites, 35 names
```

A sweep that matches only the first form silently under-reports the vocabulary by 28%.

The three **Documented**-state figures come from the rendered table, classified by the cell's first
character — which is why a prose cell that needs to point at another page puts the link *after* the
description, never first. **Scope the greps to this section**: other three-column tables on this page
match the same row shape, so an unscoped sweep silently counts their rows as row-documented ones.

```
sec() { awk '/^### Complete Type Registry/,/^## /' docs/interactions.md; }
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \|'                          # 124 rows
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \| \['                        # section-documented
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \| [^[|—]'                    # row-documented
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \| — \*not yet documented\*'  # remaining
```

The three must sum to the row count; if they do not, a cell has drifted out of all three states.

---

## Quick Start

Interactions are actions entities can perform. Start with `SimpleInteraction` for animations and effects.

### Play an Animation

```json
{
  "Type": "Simple",
  "RunTime": 0.5,
  "Effects": {
    "ItemAnimationId": "SwingDown"
  }
}
```

### Play a Sound Effect

```json
{
  "Type": "Simple",
  "RunTime": 0,
  "Effects": {
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"
  }
}
```

### Animation + Sound + Trail

```json
{
  "Type": "Simple",
  "RunTime": 0.177,
  "Effects": {
    "ItemAnimationId": "SwingDown",
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing",
    "Trails": [{ "TrailId": "Small_Default", "TargetNodeName": "Handle" }]
  }
}
```

### Delay Between Actions

```json
{
  "Type": "Simple",
  "RunTime": 0.2
}
```

### Chain to Another Interaction

```json
{
  "Type": "Simple",
  "RunTime": 0.2,
  "Next": "Sword_Swing_Down_Damage"
}
```

---

## Reference

This section contains technical details, class hierarchies, and complete property tables.

### Class Hierarchy

```
Interaction (abstract)
  implements Operation, JsonAssetWithMap, NetworkSerializable
  └── SimpleInteraction
        └── SimpleInstantInteraction (abstract)
              ├── ProjectileInteraction (see projectiles.md)
              ├── RunRootInteraction
              └── CancelChainInteraction
```

### Interaction Base Class

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Base class for all interactions. An interaction is an action that an entity can perform (attacks, abilities, item uses, etc.).

**Implements:** `Operation`, `JsonAssetWithMap<String, ...>`, `NetworkSerializable<Interaction>`

### Getting Interactions from Assets

```java
// Get the asset store
AssetStore<String, Interaction, ...> store = Interaction.getAssetStore();

// Get the asset map
IndexedLookupTableAssetMap<String, Interaction> map = Interaction.getAssetMap();

// Get interaction by ID (returns unknown if not found). Note: this is the *nested*
// interaction store — root interactions (e.g. "Melee_Root") live in RootInteraction's store.
Interaction interaction = Interaction.getInteractionOrUnknown("Weapon_Sword_Primary");
int interactionId = Interaction.getInteractionIdOrUnknown("Weapon_Sword_Primary");
```

### Meta Keys

Static meta keys for storing context data during interaction execution:

| Key | Type | Description |
|-----|------|-------------|
| `TARGET_ENTITY` | `Ref<EntityStore>` | Entity being targeted |
| `HIT_LOCATION` | `Vector4d` | Location where hit occurred |
| `HIT_DETAIL` | `String` | Detail about what was hit |
| `TARGET_BLOCK` | `BlockPosition` | Block being targeted |
| `TARGET_BLOCK_RAW` | `BlockPosition` | Raw block position |
| `TARGET_BLOCK_TYPE` | `BlockType` | Resolved type of the targeted block (0.6.3+) |
| `TARGET_BLOCK_ROTATION_INDEX` | `Integer` | Rotation index of the targeted block (0.6.3+) |
| `TARGET_SLOT` | `Integer` | Inventory slot |
| `DAMAGE` | `Damage` | Damage information |

Those are all registered on `Interaction.CONTEXT_META_REGISTRY` and read/written through
`context.getMetaStore()` (a `DynamicMetaStore<InteractionContext>`). One key belongs to the
*other* registry:

| Key | Type | Registry | Accessed via |
|-----|------|----------|--------------|
| `TIME_SHIFT` | `Float` | `Interaction.META_REGISTRY` | `context.getInstanceStore()` (a `DynamicMetaStore<Interaction>`) |

`TIME_SHIFT` carries the per-interaction overshoot (`time - maxTime`) forward to the next
interaction in the chain; `InteractionContext.setTimeShift(float)` is the convenience setter.

### Key Methods

```java
// Identity
String getId()
boolean isUnknown()

// Configuration
InteractionEffects getEffects()        // Visual/audio effects
float getHorizontalSpeedMultiplier()   // Movement speed during interaction
double getViewDistance()               // View distance modifier
float getRunTime()                     // Duration of interaction
InteractionItemChangeBehavior getOnItemChangeBehavior()   // What happens when the held item changes (see below)

// Rules and settings
InteractionRules getRules()
Map<GameMode, InteractionSettings> getSettings()

// Execution (called by framework; both are final)
void tick(Ref<EntityStore> ref, boolean firstRun, float time,
          InteractionType type, InteractionContext context, CooldownHandler cooldown)
void simulateTick(Ref<EntityStore> ref, boolean firstRun, float time,
          InteractionType type, InteractionContext context, CooldownHandler cooldown)

// Override in subclasses
void compile(OperationsBuilder builder)
protected abstract void tick0(boolean firstRun, float time, InteractionType type,
          InteractionContext context, CooldownHandler cooldown)
protected abstract void simulateTick0(boolean firstRun, float time, InteractionType type,
          InteractionContext context, CooldownHandler cooldown)
abstract boolean walk(Collector collector, InteractionContext context)  // Visitor pattern for tree traversal and metadata collection
abstract boolean needsRemoteSync()

// Network
Interaction toPacket()
```

### Utility Methods

```java
// Check if interaction state indicates failure
static boolean failed(InteractionState state)
```

### Held-Item Change Behavior

Every interaction carries an `OnItemChangeBehavior` (`com.hypixel.hytale.protocol.InteractionItemChangeBehavior`) that decides what happens when the executing entity's held item changes mid-interaction (`isCancelOnItemChange()` / the boolean `cancelOnItemChange` field were removed by 0.6.3 — use `getOnItemChangeBehavior()`):

| Value | Meaning |
|-------|---------|
| `Cancel` | Default. The chain is cancelled |
| `Fail` | The interaction ends in `InteractionState.Failed` (so a `Failed` branch can react) |
| `Finish` | The interaction ends in `InteractionState.Finished` as if it completed |
| `Ignore` | The item change is ignored and the interaction keeps running |

```json
{ "Type": "Simple", "RunTime": 0.5, "OnItemChangeBehavior": "Ignore" }
```

The old boolean `CancelOnItemChange` key is still parsed (codec doc: "Deprecated field for whether the interaction will be cancelled when the entity's held item changes.") — `true` maps to `Cancel`, `false` to `Ignore` — but it is flagged deprecated by the validator; write `OnItemChangeBehavior` in new assets.

### SimpleInstantInteraction

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Abstract base class for instant interactions (no duration, immediate effect).

**Extends:** `SimpleInteraction`

#### Key Methods
```java
// Inherited from SimpleInteraction
WaitForDataFrom getWaitForDataFrom()
boolean needsRemoteSync()
```

#### Codec
```java
public static final BuilderCodec<SimpleInstantInteraction> CODEC;
```

#### Usage
This is the base class for interactions that execute immediately, such as:
- Projectile launches (see `ProjectileInteraction` in projectiles.md)
- Instant abilities
- Quick actions

#### Registering a Custom Interaction Type (Java)

A plugin can register its own interaction `Type` and reference it from JSON. `Interaction.CODEC` is
the `AssetCodecMapCodec<String, Interaction>` type-dispatch map; register into it via
[`PluginBase.getCodecRegistry(...)`](codecs.md#registering-custom-types-via-the-plugin-registry):

1. Extend `SimpleInstantInteraction` and override
   `firstRun(InteractionType, InteractionContext, CooldownHandler)` with your logic.
2. Define a `BuilderCodec<MyInteraction>` (the
   [`BuilderCodec.builder(...).append(...).build()`](codecs.md#defining-a-codec-for-an-object) idiom).
3. Register in `setup()`:
   ```java
   getCodecRegistry(Interaction.CODEC)
       .register("My_Type", MyInteraction.class, MyInteraction.CODEC);
   ```
4. Reference from JSON inline, or as a named interaction asset others reference by id:
   ```json
   { "Type": "My_Type", "MyField": 8 }
   ```

Namespace your `Type` ids (interaction/asset ids resolve globally and case-sensitively) — e.g. a
`MyPlugin_` prefix. Key [`InteractionContext`](interactions-context.md) API inside such an interaction:

- `getEntity()` → `Ref<EntityStore>` of the **executor**. For an interaction running in a projectile's
  `ProjectileHit`/`ProjectileMiss`, this is the **projectile** — its `TransformComponent` position is
  the impact point.
- `getOwningEntity()` → the **caster/shooter** (exclude it from AOE so the shooter isn't self-hit).
- `getCommandBuffer()` → a `CommandBuffer<EntityStore>` that also serves as the `ComponentAccessor`
  for queries like `Selector.selectNearbyEntities(...)` and `EffectControllerComponent.addEffect(...)`.

### SimpleBlockInteraction

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client`

Abstract base class for interactions that act on a targeted block (`BreakBlock`, `PlaceBlock`, `PlaceFluid`, `UseBlock`, `Door`, `OpenContainer`, and many builtin interactions extend it). It resolves the target block position from the client and hands it to the subclass.

**Extends:** `SimpleInteraction`

#### Key Methods

```java
// Block targets come from the client
WaitForDataFrom getWaitForDataFrom()   // returns WaitForDataFrom.Client
boolean needsRemoteSync()

// Subclasses implement these two — server-side effect and client-side prediction
protected abstract void interactWithBlock(World world, CommandBuffer<EntityStore> commandBuffer,
        InteractionType type, InteractionContext context, ItemStack itemInHand,
        Vector3i targetBlock, CooldownHandler cooldownHandler)
protected abstract void simulateInteractWithBlock(InteractionType type, InteractionContext context,
        ItemStack itemInHand, World world, Vector3i targetBlock)

// Helpers (0.6.3+)
static BlockPosition resolveBaseBlockPosition(World world, BlockPosition pos)  // multi-block: the block's base/anchor position
protected static boolean hasRemovedBlockContext(InteractionContext context)   // true when the targeted block was already removed
```

#### Codec

```java
public static final BuilderCodec<SimpleBlockInteraction> CODEC;
```

JSON property added on top of `SimpleInteraction`:

| Property | Type | Description |
|----------|------|-------------|
| `UseLatestTarget` | boolean | Use the client's latest target block position for this interaction (codec doc: "Determines whether to use the clients latest target block position for this interaction.") |

`UseLatestTarget` is inherited by subclasses whose codec builds on `SimpleBlockInteraction.CODEC` (e.g. `Door`, `OpenContainer`); a few subclasses (e.g. `PlaceFluid`) build directly on `SimpleInteraction.CODEC` and don't expose it.

To write your own block-targeting interaction type, extend `SimpleBlockInteraction`, implement the two abstract methods, and register a `Type` string as described in [Registering a Custom Interaction Type (Java)](#registering-a-custom-interaction-type-java).

### InteractionType Enum

**Package:** `com.hypixel.hytale.protocol`

Enum representing the type of interaction trigger. Members are PascalCase (`Primary`, `Secondary`, `Ability1`–`Ability3`, `Use`, `Pick`, `Pickup`, `CollisionEnter`, `CollisionLeave`, `Collision`, `EntityStatEffect`, `SwapTo`, `SwapFrom`, `Death`, `Wielding`, `ProjectileSpawn`, `ProjectileHit`, `ProjectileMiss`, `ProjectileBounce`, `Held`, `HeldOffhand`, `Equipped`, `Dodge`, `GameModeSwap`, and, as of 0.6.3, `OnBreak` and `OnBreakImpact` — block-break hooks fired via `BlockHarvestUtils.fireOnBreakInteraction` / `queueOnBreakImpactInteraction`). The JSON `EnumCodec` matches names case-insensitively, so `"PRIMARY"` and `"Primary"` both parse; shipped assets use PascalCase.

See [Player Documentation](player.md) for full details.

### OriginSource Enum

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Selects the origin an interaction's position math is based on. Used as the `OriginSource` JSON property of [SpawnPrefab](interactions-world.md#spawnprefab) (and builtin interactions like `SpawnDeployableAtLocation` and the instance-teleport interactions).

| Value | Meaning (codec doc) |
|-------|---------------------|
| `ENTITY` | "The origin will be based on the position of the entity performing the interaction." |
| `BLOCK` | "The origin will be based on the position of the targeted block." |

```java
public static final EnumCodec<OriginSource> CODEC;
```

With `BLOCK`, offsets and yaw are additionally rotated by the targeted block's rotation; if there is no target block the interaction is skipped.

### RelativeRotationMode Enum

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Controls how much of a reference rotation is applied to an interaction-supplied offset or spawned object. Used by the builtin `SpawnDeployableAtLocation` interaction (`OffsetRotationMode` / `DeployableRotationMode` JSON properties, both defaulting to `NONE`).

| Value | Meaning (codec doc) |
|-------|---------------------|
| `NONE` | "The reference rotation will not be applied. Values are treated as absolute." |
| `YAW` | "Only the yaw (Y-axis) component of the reference rotation will be applied." |
| `FULL` | "The full reference rotation (pitch, yaw, and roll) will be applied." |

```java
public static final EnumCodec<RelativeRotationMode> CODEC;
```

### InteractionModule

**Package:** `com.hypixel.hytale.server.core.modules.interaction`

The core plugin (`extends JavaPlugin`) that owns the interaction system. Its `setup()` registers the `Interaction` and `RootInteraction` asset stores (`Server/Item/Interactions`, `Server/Item/RootInteractions`), every built-in `Type` string listed across these pages (`"Simple"`, `"PlaceBlock"`, `"Door"`, `"Explode"`, ...), and the interaction-related components. Your own `Type` strings go through the same registry — see [Registering a Custom Interaction Type (Java)](#registering-a-custom-interaction-type-java).

#### Key Methods

```java
// Singleton accessor
static InteractionModule get()

// Entry point for mouse-driven interactions (called by the packet handler)
void doMouseInteraction(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        MouseInteraction packet, Player player, PlayerRef playerRef)

// Registered component/resource types
ComponentType<EntityStore, InteractionManager> getInteractionManagerComponent()
ComponentType<EntityStore, Interactions> getInteractionsComponentType()
ComponentType<EntityStore, ChainingInteraction.Data> getChainingDataComponent()
ComponentType<ChunkStore, PlacedByInteractionComponent> getPlacedByComponentType()
ResourceType<ChunkStore, BlockCounter> getBlockCounterResourceType()
ComponentType<ChunkStore, TrackedPlacement> getTrackedPlacementComponentType()

// 0.6.3+
ComponentType<EntityStore, InteractionHost> getInteractionHostComponentType()          // standalone entity that runs an interaction chain at a position (InteractionHost.spawnHost(...))
ComponentType<EntityStore, CarriedBlock> getCarriedBlockComponentType()                // block currently carried (CarryBlock / CarryPlaceBlock / CarryDroppedBlock types)
ResourceType<EntityStore, CarriedBlockSystems.QueueResource> getCarriedBlockQueueResourceType()
```

`InteractionModule` registers 75 of the 124 `Type` strings. `SpectateControl` is documented with the rest of spectator mode in [player.md](player.md#spectatecontrol-interaction); for which of the other 74 have a written section, see the [Complete Type Registry](#complete-type-registry).

**Types registered by other plugins.** `Interaction.CODEC` is shared, so bundled plugins add their own `Type` strings in *their* `setup()`, and those types only exist when that plugin is loaded. Twenty other modules and plugins contribute the remaining 49 types — `Hytale:GameFlags` adds `SetGameFlag` and `GameFlagCondition` (see [world.md → Game Flags](world.md#game-flags)), and the registry table names the rest against their registering plugin.

#### Static Fields

```java
static final PluginManifest MANIFEST;
static final EnumCodec<InteractionType> INTERACTION_TYPE_CODEC;
static final SetCodec<InteractionType, EnumSet<InteractionType>> INTERACTION_TYPE_SET_CODEC;
```

For `PlacedByInteractionComponent` (the chunk-store component behind `getPlacedByComponentType()`), see [interactions-world.md](interactions-world.md#placedbyinteractioncomponent).

### InteractionValidation

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.util`

Static server-side range checks run before a player's block/entity interactions are accepted.

```java
static boolean canPlayerInteractWithEntity(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, Ref<EntityStore> targetRef)

static boolean canPlayerInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, int blockX, int blockY, int blockZ)
static boolean canPlayerInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, Vector3i pos)
static boolean canPlayerInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, BlockPosition pos)

// 0.6.3+: any entity (players delegate to canPlayerInteractWithBlock)
static boolean canEntityInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, BlockPosition blockPosition, BlockPosition contactPosition)
// 0.6.3+: may `ref` run a projectile-type interaction through `proxy` (a predicted projectile it created)?
static boolean isAccessibleProxyTarget(Ref<EntityStore> ref, Ref<EntityStore> proxy, InteractionType type)
```

How the allowed distance is computed (from the decompiled source):

- Base distance comes from the held item's `InteractionConfiguration.getUseDistance(gameMode)` (default config if no item is held).
- In **Creative**, the client's `creativeInteractionDistance` setting is honored, clamped to `0–128` blocks (default `10` if no settings component), and the larger of the two distances wins.
- A `+2.0` buffer is added before squaring, and distance is measured from the player's **eye height** to the target (block center for blocks).
- A `ref` without a `Player` component always passes (`true`); a player missing a `TransformComponent` always fails.
- `canEntityInteractWithBlock` (0.6.3+): a player delegates to the player check; a non-player without a `StandardPhysicsProvider` always passes; a physics entity must be within **8 blocks** (64 squared, from its position, no eye offset) of `contactPosition`.
- `isAccessibleProxyTarget` (0.6.3+) is `true` only for `ProjectileSpawn`/`ProjectileHit`/`ProjectileMiss`/`ProjectileBounce`, when `proxy` is a valid `PredictedProjectile` whose `StandardPhysicsProvider` creator UUID equals `ref`'s `UUIDComponent`.

### Usage Examples

#### Getting an Interaction

```java
// Get interaction from assets (a nested interaction id, i.e. a file under Server/Item/Interactions/)
Interaction swordSwing = Interaction.getInteractionOrUnknown("Weapon_Sword_Primary");

if (!swordSwing.isUnknown()) {
    float duration = swordSwing.getRunTime();
    InteractionRules rules = swordSwing.getRules();
}
```

#### Checking Interaction Settings per GameMode

```java
Interaction interaction = Interaction.getInteractionOrUnknown("my_interaction");
Map<GameMode, InteractionSettings> settings = interaction.getSettings();

// GameMode has exactly two values: Adventure and Creative
InteractionSettings adventureSettings = settings.get(GameMode.Adventure);
if (adventureSettings != null) {
    // Use adventure-specific settings
}
```

#### Using Meta Keys in Custom Interactions

```java
// During interaction execution, access meta data via the meta store
DynamicMetaStore<InteractionContext> meta = context.getMetaStore();
Ref<EntityStore> target = meta.getMetaObject(Interaction.TARGET_ENTITY);
Vector4d hitLocation = meta.getMetaObject(Interaction.HIT_LOCATION);
Damage damage = meta.getMetaObject(Interaction.DAMAGE);
```

### Root Interaction Configuration

Root interactions are defined in `Server/Item/RootInteractions/` and configure how interactions are triggered. `Weapons/Sword/Root_Weapon_Sword_Primary.json`:

```json
{
  "RequireNewClick": true,
  "ClickQueuingTimeout": 0.2,
  "Cooldown": { "Cooldown": 0.25 },
  "Interactions": ["Weapon_Sword_Primary"]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `RequireNewClick` | boolean | If true, must click again to chain (holding won't auto-chain) |
| `ClickQueuingTimeout` | float | Buffer window to queue next attack input |
| `Cooldown` | object | Minimum delay between attacks (see [Cooldown Configuration](#cooldown-configuration)) |
| `Interactions` | array | List of interactions to execute (required, non-empty) |
| `Rules` | object | [InteractionRules](#interactionrules) for the whole chain |
| `Settings` | object | Per-`GameMode` [RootInteractionSettings](#rootinteractionsettings) |
| `HudInputBindingEntry` | string | 0.6.3+. Codec doc: "The localization key the client shows as an input binding hint on the HUD for whichever input this root interaction is bound to. When unset, no hint is shown." |

### Cooldown System

Cooldowns prevent interactions from being spammed by enforcing minimum delays between uses.

#### CooldownHandler

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction`

The `CooldownHandler` manages cooldown timers for an entity:

```java
public final class CooldownHandler implements Tickable {
    // Check if a cooldown is active
    boolean isOnCooldown(RootInteraction root, String cooldownId, float time,
                         float[] progress, boolean checkOnly);

    // Reset a cooldown timer
    void resetCooldown(String cooldownId, float duration, float[] progress, boolean notify);

    // Get cooldown info
    Cooldown getCooldown(String cooldownId);

    // Update all cooldowns (called each frame)
    void tick(float deltaTime);
}
```

#### Cooldown Configuration

Cooldowns are configured in RootInteraction JSON files, either at the top level (applies to every
game mode) or per-`GameMode` under `Settings`:

```json
{
  "Interactions": ["Block_Primary"],
  "Settings": {
    "Adventure": {
      "Cooldown": {
        "Id": "BlockInteraction",
        "Cooldown": 0.278
      }
    },
    "Creative": {
      "Cooldown": {
        "Id": "BlockInteraction_Creative",
        "Cooldown": 0.278,
        "ClickBypass": true
      }
    }
  }
}
```

`Id` is an author-chosen string, not a lookup into any asset store: two roots that use the same `Id`
share one timer. (The shipped `Server/Item/RootInteractions/` tree uses only three: `BlockInteraction`,
`BlockInteraction_Creative` and `SlowEffect` — everything else relies on the top-level `Cooldown`
block, as `Root_Weapon_Sword_Primary.json` above does.)

| Property | Type | Description |
|----------|------|-------------|
| `Id` | string | Unique cooldown identifier (codec doc: "Cooldowns can be used on different interactions but share a cooldown.") |
| `Cooldown` | float | Cooldown duration in seconds (must be ≥ 0) |
| `ClickBypass` | boolean | If true, clicking can bypass cooldown |
| `Charges` | float[] | "The charge times available for this interaction." — a charge-based cooldown (see `CooldownHandler.Cooldown.deductCharge()` / `replenishCharge(...)`) |
| `SkipCooldownReset` | boolean | "Determines whether resetting cooldown should be skipped." |
| `InterruptRecharge` | boolean | "Determines whether recharge is interrupted by use." |

#### Cooldown Interactions

Several interactions work with cooldowns:

| Interaction | Description |
|-------------|-------------|
| `TriggerCooldown` | Start a cooldown timer |
| `ResetCooldown` | Reset a cooldown to zero |
| `CooldownCondition` | Branch based on cooldown state |

See [interactions-flow.md#cooldowncondition](interactions-flow.md#cooldowncondition) for conditional usage.

---

### InteractionRules

`InteractionRules` control how interactions conflict with each other. They determine which interactions can be blocked or interrupted by others.

#### Rule Types

```java
public class InteractionRules {
    // Which interaction types block this interaction from starting
    protected Set<InteractionType> blockedBy;
    protected String blockedByBypass;  // Condition to bypass blocking

    // Which interaction types this interaction blocks
    protected Set<InteractionType> blocking;
    protected String blockingBypass;

    // Which interaction types can interrupt this interaction mid-execution
    protected Set<InteractionType> interruptedBy;
    protected String interruptedByBypass;

    // Which interaction types this interaction interrupts
    protected Set<InteractionType> interrupting;
    protected String interruptingBypass;

    // Validation methods (Int2ObjectMap/IntSet are fastutil collections)
    boolean validateInterrupts(InteractionType type, Int2ObjectMap<IntSet> tags,
                               InteractionType otherType, Int2ObjectMap<IntSet> otherTags,
                               InteractionRules otherRules);
    boolean validateBlocked(InteractionType type, Int2ObjectMap<IntSet> tags,
                            InteractionType otherType, Int2ObjectMap<IntSet> otherTags,
                            InteractionRules otherRules);
}
```

#### JSON Configuration

```json
{
  "Type": "Simple",
  "RunTime": 0.5,
  "Rules": {
    "BlockedBy": ["Secondary"],
    "InterruptedBy": ["Dodge"],
    "Interrupting": ["Primary"]
  }
}
```

Values are [`InteractionType`](#interactiontype-enum) names (PascalCase in shipped assets; parsing is case-insensitive).

| Property | Type | Description |
|----------|------|-------------|
| `BlockedBy` | array | Interaction types that prevent starting. Codec doc: "If not set then a set of default rules will be applied based on the interaction type that the interaction is fired with. This is only effective when used on the root interaction of a chain." |
| `Blocking` | array | Interaction types this blocks from starting while running (defaults to blocking nothing) |
| `InterruptedBy` | array | Types that can cancel mid-execution ("only effective when used on the root interaction of a chain") |
| `Interrupting` | array | Types this cancels when it starts |
| `*Bypass` | string | A **tag** that, if matched, bypasses the corresponding rule (`BlockedByBypass`, `BlockingBypass`, `InterruptedByBypass`, `InterruptingBypass`) |

#### Common Patterns

**Heavy Attack (can be interrupted by dodge):**
```json
{
  "Rules": {
    "InterruptedBy": ["Dodge", "Wielding"]
  }
}
```

**Blocking Stance (blocks attacks from starting):**
```json
{
  "Rules": {
    "Blocking": ["Primary", "Secondary"]
  }
}
```

---

### InteractionSettings

**Package:** `com.hypixel.hytale.protocol`

`InteractionSettings` configures per-GameMode behavior for nested interactions (accessed via `Interaction.getSettings()`).

```java
public class InteractionSettings {
    public boolean allowSkipOnClick;
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AllowSkipOnClick` | boolean | If true, clicking can skip this interaction early |

#### JSON Configuration

InteractionSettings can be configured per game mode within nested interaction definitions:

```json
{
  "Type": "Simple",
  "RunTime": 0.5,
  "Settings": {
    "Creative": {
      "AllowSkipOnClick": true
    }
  }
}
```

#### Usage in Code

```java
Interaction interaction = Interaction.getInteractionOrUnknown("my_interaction");
Map<GameMode, InteractionSettings> settings = interaction.getSettings();

InteractionSettings creativeSettings = settings.get(GameMode.Creative);
if (creativeSettings != null && creativeSettings.allowSkipOnClick) {
    // Handle skip behavior
}
```

---

### RootInteractionSettings

**Package:** `com.hypixel.hytale.protocol`

`RootInteractionSettings` configures per-GameMode behavior for root interactions (accessed via `RootInteraction.getSettings()`). Unlike `InteractionSettings`, this class includes cooldown configuration.

```java
public class RootInteractionSettings {
    public boolean allowSkipChainOnClick;
    public InteractionCooldown cooldown;
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AllowSkipChainOnClick` | boolean | If true, clicking can skip the entire interaction chain early |
| `Cooldown` | [InteractionCooldown](#cooldown-configuration) | Cooldown configuration for this game mode |

#### JSON Configuration

RootInteractionSettings are configured in root interaction files (`Server/Item/RootInteractions/`):

```json
{
  "Interactions": ["Block_Primary"],
  "Settings": {
    "Adventure": {
      "Cooldown": {
        "Id": "BlockInteraction",
        "Cooldown": 0.278
      }
    },
    "Creative": {
      "AllowSkipChainOnClick": true,
      "Cooldown": {
        "Id": "BlockInteraction_Creative",
        "Cooldown": 0.278,
        "ClickBypass": true
      }
    }
  }
}
```

#### Difference from InteractionSettings

| Class | Used By | Key Difference |
|-------|---------|----------------|
| `InteractionSettings` | Nested `Interaction` | Has `AllowSkipOnClick` (skips single interaction) |
| `RootInteractionSettings` | `RootInteraction` | Has `AllowSkipChainOnClick` (skips entire chain) + cooldown config |

---

### Root vs Nested Interactions

Interactions are organized into two categories based on their role and file location.

#### Root Interactions

**Location:** `Server/Item/RootInteractions/`

Root interactions are entry points triggered by player input (PRIMARY, SECONDARY, etc.). They:

- Define per-GameMode settings
- Configure cooldowns
- Specify which nested interactions to execute
- Are referenced by items via `PrimaryInteraction`, `SecondaryInteraction`, etc.

**Example:** `Block_Primary.json`
```json
{
  "Interactions": ["Block_Primary"],
  "Settings": {
    "Adventure": {
      "Cooldown": {
        "Id": "BlockInteraction",
        "Cooldown": 0.278
      }
    },
    "Creative": {
      "AllowSkipChainOnClick": true,
      "Cooldown": {
        "Id": "BlockInteraction_Creative",
        "Cooldown": 0.278,
        "ClickBypass": true
      }
    }
  }
}
```

#### Nested Interactions

**Location:** `Server/Item/Interactions/`

Nested interactions are reusable building blocks. They:

- Define the actual behavior (animations, damage, effects)
- Can be referenced by ID from other interactions
- Can be inlined directly in JSON
- Support composition via `Serial`, `Parallel`, `Condition`, etc.

**Example:** `Dodge.json`
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

(`Dodge_Left` / `Dodge_Right` live in the `Dodge/` subfolder — IDs are filenames, subfolders don't matter.)

#### Reference Patterns

Nested interactions can be referenced in two ways:

**By ID (string reference):**
```json
{
  "Type": "Serial",
  "Interactions": [
    "Sword_Swing_Down",
    "Sword_Swing_Down_Damage"
  ]
}
```

**Inline (direct definition):**
```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Simple",
      "RunTime": 0.2,
      "Effects": { "ItemAnimationId": "SwingDown" }
    },
    "Sword_Swing_Down_Damage"
  ]
}
```

#### Asset Discovery

The interaction system loads assets in this order:

1. **Root interactions** from `Server/Item/RootInteractions/`
2. **Nested interactions** from `Server/Item/Interactions/`
3. String references resolve to loaded interaction IDs

IDs are derived from filenames without the `.json` extension.

---

### Complete Interaction Type Reference

**Class Hierarchy Overview**

```
Interaction (abstract)
├── SimpleInteraction
│   └── SimpleInstantInteraction
└── RootInteraction
```

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

---

## Gotchas & Errors

Backtick-quoted error strings below are literal messages from the server (verified against `HytaleServer.jar`).

- **`No interaction ID found for`** / **`Failed to find interaction:`** (`InteractionManager`) → a string reference (in `Next`, `Interactions`, `Serial`, etc.) points to an interaction ID that was never loaded. Fix: the ID must match a `.json` filename (minus the extension) under `Server/Item/Interactions/` or `Server/Item/RootInteractions/`; see [Asset Discovery](#asset-discovery). (`No such interaction:` is the NPC combat-action evaluator's version of the same problem, for an `AbilityCombatAction` naming an unknown interaction.)
- **`Missing interaction:`** → an interaction expected at lookup time is absent from the asset store. Fix: ensure the referenced asset ships in your asset pack and loaded without error.
- **`No interactions are defined for`** → a root interaction has an empty (or missing) `Interactions` list, so there is nothing to run. Fix: list at least one nested interaction in the root's `Interactions` array (the codec also rejects a missing/empty list at load time).
- **Symptom:** a `BlockedBy` / `InterruptedBy` rule on a nested interaction has no effect → per the codec docs those two rules are "only effective when used on the root interaction of a chain". Fix: put them in the root interaction's `Rules`.
- **Symptom:** an ID resolves at runtime but the interaction silently does nothing → `getInteractionOrUnknown(...)` returns the *unknown* placeholder rather than throwing for a bad ID. Fix: guard with `!interaction.isUnknown()` before using a looked-up `Interaction` (see [Getting an Interaction](#getting-an-interaction)).
- **Symptom:** an interaction never starts even though the input fires → another interaction's `Rules` block it. `BlockedBy`/`Blocking` (and the default rules applied per `InteractionType` when `Rules` is unset) gate starting. Fix: review the [InteractionRules](#interactionrules) of both interactions, or set a `*Bypass` condition.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
