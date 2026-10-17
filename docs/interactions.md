---
title: "Interactions API"
description: "Hytale interactions in JSON — the Interaction base class and SimpleInteraction hierarchy, root vs nested interactions, input-triggered entry points, and asset-store registration."
seo:
  type: TechArticle
---

# Interactions API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.7.2**

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
covers them. It is **not** the full vocabulary: as of build-34 (0.7.2), `Interaction.CODEC` carries **135**
registered `Type` values, of which 102 have a written section (on this page or another) and 33 are
documented in their registry rows themselves. None is undocumented. For the complete list — and to
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
- [ChangeState](interactions-world.md#changestate) - Change the targeted block's state
- [LaunchPadInteraction](interactions-world.md#launchpadinteraction) - Launch pad physics
- [WieldingInteraction](interactions-world.md#wieldinginteraction) - Blocking and guarding mechanics

**Beams and Chapter Rewards** (this page, 0.7.2+)
- [AttachBeam](#attachbeam) - Draw a `Beam` asset between two entities
- [OpenChapterRewards](#openchapterrewards) - Show the chapter-complete page and branch on the player's answer

**Documented with their subsystem** (0.6.3+)
- [SetGameFlag](world.md#game-flags) - Write a universe-wide named integer flag
- [GameFlagCondition](world.md#game-flags) - Succeed while a game flag is at (or at least) a level
- [SpectateControl](player.md#spectatecontrol-interaction) - Cycle a spectator's follow camera, or detach it to free cam

### Complete Type Registry

Every `Type` value `Interaction.CODEC` accepts, as of **build-34 (0.7.2)** — **135** rows: 102 have a
written section (on this page or another) and 33 are documented in their registry rows themselves. **None is
undocumented** — as of 2026-09-04 every registered `Type` is covered. A `—` appearing here again
means some type is undocumented: usually a game update adding one, but an edit that drops a link or
a prose cell produces the same state. A row count is itself a closure claim, and so is each of those three figures, so
re-derive them after a game update rather than trusting this line; the greps that produce them are
given below.

The **Documented** cell has three states, and its first character tells you which:

- **A link** — some page (possibly this one) carries a section describing what the type does as an interaction, its JSON
  keys, or both.
- **Prose** — the type has fewer than two keys of its own and no gotcha needing a paragraph, so
  *this row is its documentation*: one line, its own keys with their requiredness, and the
  fully-qualified class last. There is no section to link to and none is owed.
- **`— *not yet documented*`** — neither, yet. No row is in this state today.

A bare mention in a list, or a name that appears only inside an example, is *not* documentation and
earns neither a link nor a prose cell. Several of these names are *also* registered elsewhere — on
another codec, as a block-entity component, or as an item property — and where that is so the row
says it in its own cell rather than in a list here, because the row is where someone counting usages
of that string will be standing. Treat any `"Type": "<name>"` grep as needing attribution to a
registry before it means anything; `maintenance/registry-oracle-notes.md` §4 has the worked cases.

**Registered by** names the module or plugin whose `setup()` registers the type. `Interaction.CODEC`
is shared, so a type exists only when its owner is loaded. The 78 rows whose owner is listed in
`Constants.CORE_PLUGINS` (`server/core/Constants.java:66`) are always present — that is
`InteractionModule` (77 rows) plus `ProjectileModule` (`Projectile`). The remaining 57 rows come from
21 bundled plugins and are absent whenever their plugin is not loaded. Test membership against
`CORE_PLUGINS` rather than against the owner's name **or the class's package**: `ProjectileModule` and
`NPCPlugin` are both engine code, but only the first is core, so `Projectile` is always available while
`SpawnNPC`, `UseNPC`, `ContextualUseNPC` and `SendBeacon` are not. `GroundedCondition` is the sharpest
case: its class sits in the core `config.none` package beside `Condition`, yet only `AbilitiesPlugin`
registers it.

| `Type` | Registered by | Documented |
|---|---|---|
| `AddItem` | `InteractionModule` | [interactions-world.md](interactions-world.md#additem) |
| `ApplyAbilityEffects` | `AbilitiesPlugin` | [abilities.md](abilities.md#applyabilityeffects) |
| `ApplyEffect` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#applyeffect) |
| `ApplyForce` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#applyforce) |
| `AttachBeam` | `BeamPlugin` | [interactions.md](#attachbeam), [beams.md](beams.md#the-attachbeam-interaction) |
| `AugmentCondition` | `AugmentBlocksPlugin` | [interactions-flow.md](interactions-flow.md#augmentcondition) |
| `Bed` | `BedsPlugin` | [player.md](player.md#bed-interaction) |
| `BlockCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#blockcondition) |
| `BreakBlock` | `InteractionModule` | [interactions-world.md](interactions-world.md#breakblock) |
| `BuilderTool` | `InteractionModule` | Runs the builder tool held by the player, and is a **pass-through to the client**: it declares `WaitForDataFrom.Client` and `needsRemoteSync()`, and its `tick0` copies the client's interaction state onto the server's, so the server mirrors an outcome the client decides. No keys of its own — which tool it runs, and that tool's parameters, come from the item's separate `BuilderTool` **property** ([items-tools.md](items-tools.md#builder-tool-args)), a different registry with the same name. One shipped use, the root interaction `Server/Item/RootInteractions/Tools/Builder_Tool.json`, which wraps it in a 0.05s click-bypassing cooldown. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.BuilderToolInteraction` |
| `Camera` | `InteractionModule` | [camera.md](camera.md#the-camera-interaction-json) |
| `CameraShake` | `CameraPlugin` | Sends one `CameraEffect` asset's shake to the interacting player. One key, `CameraEffect` (a `CameraEffect` asset id, required by `Validators.nonNull()` and validated against the asset map, so a bad id fails at load). It does nothing at all for a non-player entity — `firstRun` returns without setting a failed state when there is no `PlayerRef`. **The string is registered on two codecs**: `CameraEffect.CODEC` as well as `Interaction.CODEC`, and of the **55** shipped files containing `"Type": "CameraShake"`, **54** are `CameraEffect` assets under `Server/Camera/CameraEffect/`. The interaction has **one** shipped use, `Server/Item/RootInteractions/NPCs/Boss/Goblin_Gobliterator/Root_Arena_Horn_Shake.json`, so a usage count mined by grepping the string measures the other registry almost entirely. `com.hypixel.hytale.builtin.adventure.camera.interaction.CameraShakeInteraction` |
| `CanBreakRespawnPoint` | `ObjectivePlugin` | Succeeds unless the target block carries a `RespawnBlock` component owned by a **different** player; an unowned point, or one the interacting player owns, passes. It also passes when the block has no block entity or no `RespawnBlock` at all, so it only ever blocks someone else's claimed respawn point. Ownership is read from the **owning** entity's `UUIDComponent`, not the interacting one. No keys of its own. Its one shipped use is the head of `Server/Item/RootInteractions/Block/Check_Can_Break_Respawn.json`, whose `Next` chain swings and then runs `BreakBlock` — the root the bed in [player.md](player.md#bed-interaction) wires onto `Primary`. `com.hypixel.hytale.builtin.adventure.objectives.interactions.CanBreakRespawnPointInteraction` |
| `CancelChain` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#cancelchaininteraction) |
| `CarryBlock` | `InteractionModule` | Picks the targeted block up onto the interacting entity as a `CarriedBlock` component and then breaks the block. **The block entity travels with it** — `BlockEntity.takeBlockEntity` moves the component data into the carried state — so a container carried this way keeps its contents. One key, `EntityEffectId` (an `EntityEffect`, inline or by reference, late-validated, not required), played on the carrier while it holds the block. When block-entity data is taken, a `BlockCarriedEvent` is invoked on it first, naming the carrier. Three shipped uses, all goblin furniture: `Server/Item/Items/Furniture/Goblin/Throwable_Explosive_Barrel.json`, `Throwable_Explosive_Barrel_Gobliterator.json` and `Furniture_Goblin_Pot_Loot.json`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.CarryBlockInteraction` |
| `CarryDroppedBlock` | `InteractionModule` | Takes the carried block off the targeted **entity** and onto the interacting one, cloning the `CarriedBlock` component and removing the source entity. It drops whatever the user was already carrying first, so it is a swap rather than a stack, and it fails when the target is absent or is not carrying anything. No keys of its own. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.CarryDroppedBlockInteraction` |
| `CarryPlaceBlock` | `InteractionModule` | Puts the carried block back into the world, restoring the block-entity data `CarryBlock` took with it. Client-driven: `WaitForDataFrom.Client` plus `needsRemoteSync()`, and it reuses the protocol `PlaceBlockInteraction` packet with `blockId` `-1` and `removeItemInHand` `false`, so nothing is consumed from the hand. It also clears the client's block rotation on the first tick, so a carried block is always placed unrotated. No keys of its own. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.CarryPlaceBlockInteraction` |
| `ChainFlag` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#chainflaginteraction) |
| `Chaining` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#chaininginteraction) |
| `ChangeActiveSlot` | `InteractionModule` | Switches the player's active hotbar slot. One key, `TargetSlot` (int, validated `range(0, 8)` so the nine hotbar slots, **not required**) — omit it and the slot comes from the interaction context instead, which is what four of the five shipped uses do; only an NPC equipping a second sword pins `"TargetSlot": 1`. Note it extends `Interaction` through `Interaction.ABSTRACT_CODEC` rather than one of the `Simple*` bases, so it does **not** carry the base-interaction keys the other rows here inherit, and it declares `WaitForDataFrom.None`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.ChangeActiveSlotInteraction` |
| `ChangeBlock` | `InteractionModule` | [items-tools.md](items-tools.md#changeblock-interaction) |
| `ChangeFarmingStage` | `FarmingPlugin` | [items-blocks.md](items-blocks.md#changefarmingstage-interaction) |
| `ChangeStat` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#changestat) |
| `ChangeState` | `InteractionModule` | [interactions-world.md](interactions-world.md#changestate) |
| `ChangeStatWithModifier` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#changestat) |
| `Charging` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#charginginteraction) |
| `CheckUniqueItemUsage` | `InteractionModule` | A condition **with a side effect**: it fails if the interacting player has already used an item with this item id, and otherwise records the usage on their `UniqueItemUsagesComponent` and succeeds — so running it is what consumes the one allowed use, and the record is permanent and per-item-id, not per-item-stack. A repeat use also sends the player the `server.commands.checkUniqueItemUsage.uniqueItemAlreadyUsed` notification. No keys of its own, and no shipped asset uses it. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.CheckUniqueItemUsageInteraction` |
| `ClearCarriedBlock` | `InteractionModule` | Throws away the block the interacting entity is carrying. Codec doc: "Clears the block currently being carried, discarding it without placing or dropping it." It nulls the `CarriedBlock`'s item container first, so the contents of a carried container go with it, and then removes the component; with nothing carried it changes nothing and still finishes. Server-only: `simulateFirstRun` is empty. No keys of its own. One shipped use, the last step of `Server/Item/Interactions/Weapons/Carryable_Block/Throw_Carryable_Block.json`, after the throw has launched its projectile. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.ClearCarriedBlockInteraction` |
| `ClearEntityEffect` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#clearentityeffect) |
| `Condition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#condition) |
| `ContextualUseNPC` | `NPCPlugin` | [items-tools.md](items-tools.md#shears) |
| `CooldownCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#cooldowncondition) |
| `CycleBlockGroup` | `InteractionModule` | [items-tools.md](items-tools.md#hammer) |
| `DamageEntity` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#damageentity) |
| `DestroyBlock` | `InteractionModule` | Breaks the target block outright, with no tool, drop or hardness handling to configure. It is distance-validated like a normal break, and **credits the break to the owning entity when there is one**, falling back to the interacting entity — so a projectile or trap breaking a block is attributed to whoever fired it. No keys of its own. Eleven shipped uses across ten files, mostly NPC attacks and block `CollisionEnter` chains (`Weapon_Spellbook_Rekindle_Embers.json` uses it twice). `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.DestroyBlockInteraction` |
| `DestroyTaggedVolumes` | `TriggerVolumesPlugin` | [trigger-volumes.md](trigger-volumes.md#commands-tooling) |
| `Door` | `InteractionModule` | [interactions-world.md](interactions-world.md#door) |
| `DragEraseBlock` | `InteractionModule` | Erases blocks along a held drag, speeding up the longer the input is held. Zero keys **of its own**, which does not mean it takes none: it extends `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.DragPlaceBlockInteraction`, whose five keys it inherits — `ForkInteractions` (required), `MaxBlocksPerTick` (`4`), `MaxBlocksPerGesture` (`512`), `ValidateForkPositions` (`true`) and `MaxForkPositionViolations` (`8`). See [items-blocks.md](items-blocks.md#block_secondary-interaction) for the `PlaceModeSelect` chain that dispatches to these. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.DragEraseBlockInteraction` |
| `DragPlaceBlock` | `InteractionModule` | [items-blocks.md](items-blocks.md#block_secondary-interaction) |
| `DurabilityCondition` | `InteractionModule` | [items-weapons.md](items-weapons.md#durabilitycondition-interaction) |
| `EffectCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#effectcondition) |
| `EquipItem` | `InteractionModule` | [interactions-world.md](interactions-world.md#equipitem) |
| `EventStartInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `EventStopInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `ExitInstance` | `InstancesPlugin` | Sends the entity out of the instance it is in, to its set return point. Codec doc: "Teleports the **Entity** out of the current **Instance** and places them at their return point" — note *entity*, not player, where its `TeleportInstance` sibling says player. No keys of its own; the return point was recorded on the way in. Two shipped uses (`Forgotten_Temple_Portal_Exit.json`, `Leave_Instance.json`). **Two further files name the string and are a different registry**: `Server/GameplayConfigs/Portal.json` and `Default_Instance.json` use it as a `Death.RespawnController` type, so a name-scoped grep reports four against a true two. Note the discriminator here is a **parent key path**, not a directory — unlike `CameraShake`, which splits cleanly on `Server/Camera/CameraEffect/`, scoping this grep to a directory only happens to work while no `RespawnController` sits under `Server/Item/`. `com.hypixel.hytale.builtin.instances.interactions.ExitInstanceInteraction` |
| `Explode` | `InteractionModule` | [interactions-world.md](interactions-world.md#explode) |
| `ExtrudePlaceBlock` | `InteractionModule` | Extrudes the targeted block face while the click is held, placing one layer per depth step and erasing the streamed layers again when the gesture pulls back. Zero keys **of its own**, which does not mean it takes none: it extends `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.DragPlaceBlockInteraction`, whose five keys it inherits — `ForkInteractions` (required), `MaxBlocksPerTick` (`4`), `MaxBlocksPerGesture` (`512`), `ValidateForkPositions` (`true`) and `MaxForkPositionViolations` (`8`). See [items-blocks.md](items-blocks.md#block_secondary-interaction) for the `PlaceModeSelect` chain that dispatches to these. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.ExtrudePlaceBlockInteraction` |
| `FertilizeSoil` | `FarmingPlugin` | [items-tools.md](items-tools.md#fertilizer) |
| `FirstClick` | `InteractionModule` | [interactions-combo.md](interactions-combo.md#firstclickinteraction) |
| `GameFlagCondition` | `GameFlagsPlugin` | [world.md](world.md#game-flags) |
| `GlobalEventStartInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `GlobalEventStopInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `GrantAbilityCharges` | `AbilitiesPlugin` | [abilities.md](abilities.md#grantabilitycharges) |
| `GroundedCondition` | `AbilitiesPlugin` | Fails the chain unless the interacting entity stands on the ground. Codec doc: "Fails the chain unless the caster stands on ground (or within Tolerance blocks above it). Author the fail feedback on Failed. Swimming, climbing and falling all fail." It passes when `MovementStatesComponent` reports `onGround`, or, with a positive `Tolerance`, when a downward ray from just above the feet meets a block of `Solid` material within `Tolerance` blocks. One key, `Tolerance` (float, default `0` meaning strictly on the ground, validated `>= 0`, not required). The client runs the same check (`simulateFirstRun` calls it too). Two shipped uses: `Server/Item/Interactions/Abilities/GroundSlam/Ability_GroundSlam_Cast.json` (`"Tolerance": 1`) and the core `Server/Item/Items/Glider/Template_Glider.json`, so that core item depends on a bundled plugin. The class lives in the core package all the same. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.GroundedConditionInteraction`. See [abilities.md](abilities.md#groundedcondition). |
| `HarvestCrop` | `FarmingPlugin` | [items-blocks.md](items-blocks.md#harvestcrop-interaction) |
| `HubPortal` | `CreativeHubPlugin` | [adventure.md](adventure.md#hubportal) |
| `IncreaseBackpackCapacity` | `InteractionModule` | [interactions-world.md](interactions-world.md#increasebackpackcapacity) |
| `IncrementCooldown` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#incrementcooldown) |
| `Interrupt` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#interruptinteraction) |
| `LaunchAbilityProjectile` | `AbilitiesPlugin` | [abilities.md](abilities.md#launchabilityprojectile) |
| `LaunchPad` | `InteractionModule` | [interactions-world.md](interactions-world.md#launchpadinteraction) |
| `LaunchProjectile` | `InteractionModule` | [interactions-world.md](interactions-world.md#launchprojectile) |
| `LearnRecipe` | `CraftingPlugin` | [items-crafting.md](items-crafting.md#learning-recipes-learnrecipe) |
| `MarkAbilityBenchIntroSeen` | `AbilitiesPlugin` | A once-per-player gate. Codec doc: "Marks the ability bench intro as seen. Runs Next the first time the player uses it, and Failed on every later use." The record is the player's `AbilityBenchIntro` component, which is persisted (one key, `Seen`); the `/abilities resetintro` command removes it. Server-decided: `WaitForDataFrom.Server`. No keys of its own. One shipped use, `Server/Item/Items/Bench/Bench_Abilities.json`, whose `Use` chain opens the `AbilityBenchIntro` custom page on `Next` and runs `OpenAbilityBench` on `Failed`, so a player sees the intro once and the bench every time after. `com.hypixel.hytale.builtin.abilities.interaction.MarkAbilityBenchIntroSeenInteraction`. See [abilities.md](abilities.md#the-ability-bench). |
| `MemoriesCondition` | `MemoriesPlugin` | [interactions-flow.md](interactions-flow.md#placementcountcondition) |
| `ModifyIntervalConditionInteraction` | `WorldEventsPlugin` | [world-events.md](world-events.md#starting-and-stopping-events) |
| `ModifyInventory` | `InteractionModule` | [interactions-world.md](interactions-world.md#modifyinventory) |
| `Mount` | `MountPlugin` | [mounts.md](mounts.md#mount-interaction) |
| `MovementCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#movementcondition) |
| `OpenAbilityBench` | `AbilitiesPlugin` | Opens the ability bench window (`Page.Bench` holding an `AbilityBenchWindow`) over the interacting player's own ability slots, the `InventoryComponent.AbilitySlots` component. Codec doc: "Opens the ability bench for the using player, over their own ability slots. Author as any block's Use interaction to make that block the bench." It does nothing for an entity with no `Player` or no ability slots, and the window opens from a deferred command-buffer task, after the tick. No keys of its own. One shipped use, the `Failed` branch of `Server/Item/Items/Bench/Bench_Abilities.json`'s `Use` chain (see `MarkAbilityBenchIntroSeen`). `com.hypixel.hytale.builtin.abilities.interaction.OpenAbilityBenchInteraction`. See [abilities.md](abilities.md#the-ability-bench). |
| `OpenBenchPage` | `CraftingPlugin` | Opens a crafting bench window on the interacting player. One key, `Page` (it carries `Validators.nonNull()`, yet omitting it passes, as this entry explains further on), selecting one of `OpenBenchPageInteraction.PageType`'s three constants, written in JSON as the default `EnumCodec`'s PascalCase keys `"SimpleCrafting"`, `"DiagramCrafting"`, `"StructuralCrafting"` (constants `SIMPLE_CRAFTING` …), which pick a `SimpleCraftingWindow`, `DiagramCraftingWindow` or `StructuralCraftingWindow`. The validator checks the field **after** decoding, and the field is initialised to `SIMPLE_CRAFTING`, so an omitted `Page` passes and means simple crafting. The one shipped use, `Server/Item/Items/Puzzles/Goblins/Lab/GoblinLab_Tinkering_Bench.json`, omits it this way: a `Crafting` bench that gates its window behind an `AugmentCondition`. Benches normally need no interaction at all: `CraftingPlugin` builds three instances with the ids `*Simple_Crafting_Default`, `*Diagram_Crafting_Default` and `*Structural_Crafting_Default` and binds them through `Bench.registerRootInteraction` (marked `@Deprecated(forRemoval = true)` in 0.7.2, so plugins should leave it alone) to the `Crafting`, `DiagramCrafting` and `StructuralCrafting` bench types, so a bench of those types opens without naming any interaction. `com.hypixel.hytale.builtin.crafting.interaction.OpenBenchPageInteraction` |
| `OpenChapterRewards` | `InteractionModule` | [interactions.md](#openchapterrewards) |
| `OpenContainer` | `InteractionModule` | [interactions-world.md](interactions-world.md#opencontainer) |
| `OpenCustomUI` | `InteractionModule` | [interactions-world.md](interactions-world.md#opencustomui) |
| `OpenItemStackContainer` | `InteractionModule` | Opens the container carried *inside the held item* — a bag or pouch — as a bench page. No keys of its own: which slots exist comes from the item's own `ItemStackContainerConfig`, and the container is created on the stack on first use. It gives up silently rather than failing when the user is not a player, already has a custom page open, or is holding nothing. One shipped use, `Server/Item/Items/Utility/Utility_Bag_Seed.json`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.OpenItemStackContainerInteraction` |
| `OpenPage` | `InteractionModule` | [interactions-world.md](interactions-world.md#ui-interactions) |
| `OpenProcessingBench` | `CraftingPlugin` | Opens the processing-bench window on the interacting player. No keys of its own. It is the **fourth** `BenchType`'s route and the asymmetric one: `Processing` is the one bench type `Bench.registerRootInteraction` is never called for, so `Bench.getRootInteraction()` returns null for it and a processing bench must name the interaction itself — all four shipped ones (`Bench_Furnace`, `Bench_Campfire`, `Bench_Tannery`, `Bench_Salvage`) set `"Interactions": { "Use": "Open_Processing_Bench" }`. `com.hypixel.hytale.builtin.crafting.interaction.OpenProcessingBenchInteraction` |
| `Parallel` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#parallel) |
| `PickBlock` | `InteractionModule` | Performs a block pick — moves the targeted block into the user's hand if they have it in their inventory or are in creative. **Entirely client-side on the server's part**: both server callbacks are empty, and the class exists to declare `WaitForDataFrom.Client` and `needsRemoteSync()` and to emit the protocol `PickBlockInteraction`. No keys of its own. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.PickBlockInteraction` |
| `PickupItem` | `BuilderToolsPlugin` | Picks the targeted item entity up into the player's inventory, leaving any partial remainder on the entity — and, when *nothing* fits, returning with no state change and no `Failed`. **It is not ordinary walk-over pickup; it is mutually exclusive with it.** Walk-over pickup is the ECS system `com.hypixel.hytale.server.core.modules.entity.player.PlayerItemEntityPickupSystem`, whose query excludes any item entity carrying `Interactable` — and `EntitySettingsSnapshot.applyPickupState`, the only thing that binds this interaction (under the code-built id `*PickupItem`; no shipped asset names it), is exactly what *adds* `Interactable`. Turning the interaction path on therefore removes the entity from walk-over pickup by query, and turning it off adds `PreventPickup` rather than handing pickup back. If what you want is to run a chain when a player walks over an item, the hook is the item asset's own `InteractionType.Pickup` entry, which `PlayerItemEntityPickupSystem` runs in place of giving the item — not this type. No keys of its own. `com.hypixel.hytale.builtin.buildertools.interactions.PickupItemInteraction` |
| `PlaceBlock` | `InteractionModule` | [interactions-world.md](interactions-world.md#placeblock) |
| `PlaceFluid` | `InteractionModule` | [interactions-world.md](interactions-world.md#placefluid) |
| `PlacementCountCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#placementcountcondition) |
| `PlaceModeSelect` | `InteractionModule` | [items-blocks.md](items-blocks.md#block_secondary-interaction) |
| `Portal` | `PortalsPlugin` | Enters the portal block being interacted with — the class is `EnterPortalInteraction`, so the registered name and the class name do not match, and a search for `PortalInteraction` finds nothing. No keys of its own: the destination comes from the portal block's own configuration, not from the interaction. Two shipped uses, both the `CollisionEnter` chain of a block's `Active` state: `Server/Item/Items/Portal/Portal_Device.json` and `Server/Item/Items/Puzzles/Goblins/Lab/GoblinLab_Fragment_Portal.json`. `com.hypixel.hytale.builtin.portals.interactions.EnterPortalInteraction` |
| `PortalReturn` | `PortalsPlugin` | The return leg of [`Portal`](#complete-type-registry) — class `ReturnPortalInteraction`, again not matching the registered name. No keys of its own. One shipped use, the interaction asset `Server/Item/Interactions/Block/Portal/Portal_Return.json`, referenced by its id `Portal_Return` from three items: the `Portal_Return` block's `CollisionEnter`, and the `Success` branch of the two dungeon exits, `Dungeon_Portal_End.json` (through [`OpenChapterRewards`](#openchapterrewards)) and `Dungeon_Portal_Early_Exit.json`. `com.hypixel.hytale.builtin.portals.interactions.ReturnPortalInteraction` |
| `PrefabSelectionInteraction` | `BuilderToolsPlugin` | Selects a prefab in the prefab editor, and is the one registered name that carries the `Interaction` suffix — the `Type` string really is `PrefabSelectionInteraction`. It requires an active prefab edit session (otherwise it messages `server.commands.editprefab.notInEditSession`) and branches on the slot it was run from: `Secondary` picks the loaded prefab whose horizontal centre is nearest the player, while any other slot picks the one whose bounding box contains the block the player is looking at. No keys of its own. One shipped use, `Server/Item/Items/EditorTool/EditorTool_PrefabEditing_SelectPrefab.json`, which runs it from both `Primary` and `Secondary`. `com.hypixel.hytale.builtin.buildertools.prefabeditor.PrefabSelectionInteraction` |
| `Projectile` | `ProjectileModule` | [projectiles.md](projectiles.md#projectileinteraction) |
| `PullEntityAbility` | `AbilitiesPlugin` | [abilities.md](abilities.md#pullentityability) |
| `RefillContainer` | `InteractionModule` | [items-tools.md](items-tools.md#watering-can) |
| `RemoveEntity` | `InteractionModule` | [interactions-world.md](interactions-world.md#removeentity) |
| `Repeat` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#repeat) |
| `Replace` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#replace) |
| `ResetCooldown` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#resetcooldown) |
| `RevealMapMarkersInView` | `InteractionModule` | [world.md](world.md#revealmapmarkersinview) |
| `RunOnBlockTypes` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#runonblocktypes) |
| `RunRootInteraction` | `InteractionModule` | Runs a named root interaction, and **does not wait for it**: `firstRun` sets its own state to `Finished` first and then executes the root, so a surrounding chain continues immediately rather than on the root's completion. One key, `RootInteraction` (a root-interaction id, required by `Validators.nonNull()` and late-validated against the `RootInteraction` assets); at runtime an id that still does not resolve yields `RootInteraction.getRootInteractionOrUnknown`'s placeholder rather than an error. No shipped asset uses it as an interaction. All **13** shipped files containing `"Type": "RunRootInteraction"` use it as a **trigger-volume effect**: the two `Server/TriggerVolumes/Effects/` assets, the `TriggerVolume` components of nine prefabs, and two instances' `TriggerVolumeData.json`. That effect is **not this type** ([trigger-volumes.md](trigger-volumes.md#built-in-effect-types)), which shares the `RootInteraction` key but adds `InteractionType` and `EquipSlot`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.RunRootInteraction` |
| `Seating` | `MountPlugin` | [mounts.md](mounts.md#seating-interaction) |
| `Selector` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#selector) |
| `SendBeacon` | `NPCPlugin` | [npc-roles.md](npc-roles.md#sendbeacon) |
| `SendMessage` | `InteractionModule` | [interactions-world.md](interactions-world.md#sendmessage) |
| `Serial` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#serial) |
| `SetGameFlag` | `GameFlagsPlugin` | [world.md](world.md#game-flags) |
| `SetMemoriesCapacity` | `MemoriesPlugin` | Raises a player's memory capacity to `Capacity`, and **fails when that value is not higher than the current one** — it can only ever increase, so the same item cannot be used twice. Crossing from zero also unlocks the memories feature for that player (an `UpdateMemoriesFeatureStatus` packet plus a notification). One key: `Capacity` (int, not required). One shipped use, `Server/Item/Items/Bench/Bench_Memories.json`. `com.hypixel.hytale.builtin.adventure.memories.interactions.SetMemoriesCapacityInteraction` |
| `ShowEventTitle` | `InteractionModule` | [trigger-volumes.md](trigger-volumes.md#the-showeventtitle-interaction-is-a-different-type-with-the-same-name) |
| `SignalNearbyVolumes` | `TriggerVolumesPlugin` | [trigger-volumes.md](trigger-volumes.md#commands-tooling) |
| `Simple` | `InteractionModule` | [interactions-combat.md](interactions-combat.md#simpleinteraction) |
| `SpawnAbilityEntity` | `AbilitiesPlugin` | [abilities.md](abilities.md#spawnabilityentity) |
| `SpawnDeployableAtHitLocation` | `DeployablesPlugin` | [deployables.md](deployables.md#the-three-interactions) |
| `SpawnDeployableAtLocation` | `DeployablesPlugin` | [deployables.md](deployables.md#the-three-interactions) |
| `SpawnDeployableFromRaycast` | `DeployablesPlugin` | [deployables.md](deployables.md#the-three-interactions) |
| `SpawnMinecart` | `MountPlugin` | [mounts.md](mounts.md#spawnminecart-interaction) |
| `SpawnNPC` | `NPCPlugin` | [npc-spawning.md](npc-spawning.md#spawnnpc-interaction) |
| `SpawnPrefab` | `InteractionModule` | [interactions-world.md](interactions-world.md#spawnprefab) |
| `SpawnTriggerVolume` | `TriggerVolumesPlugin` | [trigger-volumes.md](trigger-volumes.md#commands-tooling) |
| `SpectateControl` | `InteractionModule` | [player.md](player.md#spectatecontrol-interaction) |
| `SplitAbilityProjectile` | `AbilitiesPlugin` | [abilities.md](abilities.md#splitabilityprojectile) |
| `StartObjective` | `ObjectivePlugin` | Starts the objective described by its one key, `Setup` (an `ObjectiveTypeSetup` — shipped assets write `{ "Type": "Objective", "ObjectiveId": … }` — required by `Validators.nonNull()`). Starting stamps the new objective's UUID into the **held item stack's** metadata, and a later use of that same stack adds the player to the existing objective instead of starting another. `com.hypixel.hytale.builtin.adventure.objectives.interactions.StartObjectiveInteraction` — note that `com.hypixel.hytale.builtin.adventure.objectiveshop.StartObjectiveInteraction` shares the simple name, is registered on `ChoiceInteraction.CODEC` with a different single key, and is **not** this type |
| `StatsCondition` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#statscondition) |
| `StatsConditionWithModifier` | `InteractionModule` | The armour-discounted variant of [`StatsCondition`](interactions-flow.md#statscondition), whose keys (`Costs`, `LessThan`, `ValueType`, `Lenient`) it inherits from their shared `StatsConditionBaseInteraction` base. Its one own key, `InteractionModifierId`, is **required** (`Validators.nonNull()`) and is `ItemArmor.InteractionModifierId`, an enum with exactly **one** constant, `Dodge` — which both shipped uses (`Server/Item/Interactions/Dodge/Dodge_Left.json` and `Dodge_Right.json`) write. That closure claim belongs to the enum rather than to this type: `ChangeStatWithModifier`'s identically-named key reads the same enum, so a second constant in a future build falsifies both rows at once. The difference from `StatsCondition` is that each cost is first reduced by the flat and multiplier modifiers carried by the armour the player has **equipped** — the lookup runs over the armour container only — so the same `Costs` passes for a better-equipped player. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.StatsConditionWithModifierInteraction` |
| `SurfaceDrawPlaceBlock` | `InteractionModule` | Draws blocks along a plane while the click is held. Zero keys **of its own**, which does not mean it takes none: it extends `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.DragPlaceBlockInteraction`, whose five keys it inherits — `ForkInteractions` (required), `MaxBlocksPerTick` (`4`), `MaxBlocksPerGesture` (`512`), `ValidateForkPositions` (`true`) and `MaxForkPositionViolations` (`8`). See [items-blocks.md](items-blocks.md#block_secondary-interaction) for the `PlaceModeSelect` chain that dispatches to these. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.SurfaceDrawPlaceBlockInteraction` |
| `TeleportConfigInstance` | `InstancesPlugin` | The UI-configured form of [TeleportInstance](adventure.md#teleportinstance): same destination behaviour, but **no keys of its own** because the instance, offset and rotation are set through an in-game UI and stored on the block rather than written in the asset. The codec says so directly — "This is configured via a UI instead of inside the interaction. This interaction just executes that set configuration." One shipped use, `Server/Item/Items/Portal/Instance_Gateway.json`. `com.hypixel.hytale.builtin.instances.interactions.TeleportConfigInstanceInteraction` |
| `Teleporter` | `TeleporterPlugin` | [adventure.md](adventure.md#teleporter) |
| `TeleportInstance` | `InstancesPlugin` | [adventure.md](adventure.md#teleportinstance) |
| `ToggleGlider` | `InteractionModule` | Toggles glider movement for the player. No keys of its own, and **no server-side behaviour at all**: `firstRun` is empty and the class exists to emit a protocol `ToggleGliderInteraction` from `generatePacket()`, which is why it lives in the `config.client` package — the client performs the toggle. One shipped use, `Server/Item/Items/Glider/Template_Glider.json`. `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.ToggleGliderInteraction` |
| `TriggerAbilityFX` | `AbilitiesPlugin` | [abilities.md](abilities.md#triggerabilityfx) |
| `TriggerCooldown` | `InteractionModule` | [interactions-flow.md](interactions-flow.md#triggercooldown) |
| `TriggerSpawnMarkers` | `SpawningPlugin` | [npc-spawning.md](npc-spawning.md#triggerspawnmarkers) |
| `UseBlock` | `InteractionModule` | [items-blocks.md](items-blocks.md#block_secondary-interaction) |
| `UseCaptureCrate` | `FarmingPlugin` | [items-tools.md](items-tools.md#capture-crate) |
| `UseCoop` | `FarmingPlugin` | Harvests a chicken coop's accumulated produce into the interacting player's inventory (hotbar first) and then flips the block's interaction state to `Produce_Ready` or `default` depending on whether any produce is left. No keys of its own. It needs a `CoopBlock` block-entity component and **creates one on demand** when the block type declares it, so a coop that has never been used still works; every other failure — unloaded section, unknown block type, a block type that does not declare `CoopBlock` — ends the interaction `Failed`. One shipped use, `Server/Item/Items/Coops/Coop_Chicken.json`. `com.hypixel.hytale.builtin.adventure.farming.interactions.UseCoopInteraction` |
| `UseEntity` | `InteractionModule` | [items-weapons.md](items-weapons.md#useentity-interaction) |
| `UseNPC` | `NPCPlugin` | The right-click-an-NPC interaction — it reserves the target NPC for the user, and fails unless the user is a player and the target is an in-range, unreserved `NPCEntity` willing to interact. No keys of its own. **No shipped asset names it**, and it is registered on `Interaction.CODEC` like any other type so a mod still may: `NPCPlugin` loads a code-built instance under the id `*UseNPC`, and `RoleBuilderSystem` binds that id to every NPC's `Use` slot, so nothing shipped needs to write it. `com.hypixel.hytale.server.npc.interactions.UseNPCInteraction` |
| `UseWateringCan` | `FarmingPlugin` | [items-tools.md](items-tools.md#watering-can) |
| `Wielding` | `InteractionModule` | [interactions-world.md](interactions-world.md#wieldinginteraction) |

Both registration forms are load-bearing when re-deriving this table. Most types are registered
directly:

```
grep -rn '[^A-Za-z]Interaction\.CODEC\.register("' ~/.cache/hytale-jar/src     # 92 names
```

The leading `[^A-Za-z]` matters: without it the pattern also matches
`ChoiceInteraction.CODEC.register("StartObjective"`, a different codec, and counts one too many.
A further 43 reach the same codec through the plugin's registry handle, where the receiver is not
`Interaction.CODEC`, the calls chain (one line in `FarmingPlugin` registers six), and one id is
a constant rather than a literal (`CameraPlugin`'s `CODEC_CAMERA_SHAKE` is `"CameraShake"`):

```
grep -rn 'getCodecRegistry(Interaction\.CODEC)' ~/.cache/hytale-jar/src   # 29 sites, 43 names
```

A sweep that matches only the first form silently under-reports the vocabulary by 32%.

The three **Documented**-state figures come from the rendered table, classified by the cell's first
character — which is why a prose cell that needs to point at another page puts the link *after* the
description, never first. **Scope the greps to this section**: other three-column tables on this page
match the same row shape, so an unscoped sweep silently counts their rows as row-documented ones.

```
sec() { awk '/^### Complete Type Registry/{f=1;next} f&&/^#{1,3} /{exit} f' docs/interactions.md; }
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \|'                          # 135 rows
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \| \['                        # section-documented
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \| [^[|—]'                    # row-documented
sec | grep -cE '^\| `[^`]+` \| `[^`]+` \| — \*not yet documented\*'  # remaining
```

Re-derive all three, never two and a subtraction. They necessarily sum to the row count even when a
cell is in the wrong state, because the states are exhaustive — the sum stays 135 across exactly the
move (undocumented → prose) that every edit here makes, so it confirms nothing about whether the
stated figures are current.

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
| `Fail` | The check sets `InteractionState.Failed` (so a `Failed` branch can react), but the operation's own hook (`tick0`, `simulateTick0`) still runs that tick |
| `Finish` | The check sets `InteractionState.Finished` as if it completed, and the hook still runs that tick |
| `Ignore` | The item change is ignored and the interaction keeps running |

```json
{ "Type": "Simple", "RunTime": 0.5, "OnItemChangeBehavior": "Ignore" }
```

`Fail` and `Finish` do not stop the operation (read, not measured). `Interaction.tickInternal` sets the state but returns true only for `ItemChanged` (`Interaction.java:302`), so for these two `tick` still calls `tick0` (`:238-239`). A `SimpleInstantInteraction` reached on its first tick after the change therefore still runs `firstRun`, and the state it ends in is the one the check set. A type whose `tick0` writes the state itself overrides it: `ChargingInteraction.tick0` sets `NotFinished` or `Finished`, so `Fail` does not end a Charging operation as `Failed`.

The check is skipped for a chain that runs through another entity, one whose owning entity differs
from the executing entity (a projectile's hit chain, for example). On a manager with no remote client the check runs in both passes, and what a changed
held slot then does depends on which pass runs second: after a `Server` wait the passes desync and the
entity is removed, after a `None` wait the chain ends as `ItemChanged`
(see [the item-change check](#the-item-change-check-and-the-pass-order)). A chain cast from the ability
slots compares against the slot it was cast from rather than the hotbar's active slot.

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
       .register("MyMod_Type", MyInteraction.class, MyInteraction.CODEC);
   ```
4. Reference from JSON inline, or as a named interaction asset others reference by id:
   ```json
   { "Type": "MyMod_Type", "MyField": 8 }
   ```

You don't advance the chain yourself. `Interaction.tick` is `final`. After your `firstRun` returns,
once the state is `Finished`, `Failed` or `Skip`, it increments the context's operation counter, unless
your code already moved the counter or the call depth. That increment is what lets the chain move to
the next step. A raw `Operation` gets no such help
([interactions-operations.md](interactions-operations.md)).

Namespace your `Type` ids (interaction/asset ids resolve globally and case-sensitively) — e.g. a
`MyPlugin_` prefix. Key [`InteractionContext`](interactions-context.md) API inside such an interaction:

- `getEntity()` → `Ref<EntityStore>` of the **executor**. For an interaction running in a projectile's
  `ProjectileHit`/`ProjectileMiss`, this is the **projectile** — its `TransformComponent` position is
  the impact point.
- `getOwningEntity()` → the **caster/shooter** (exclude it from AOE so the shooter isn't self-hit).
- `getCommandBuffer()` → a `CommandBuffer<EntityStore>` that also serves as the `ComponentAccessor`
  for queries like `Selector.selectNearbyEntities(...)` and `EffectControllerComponent.addEffect(...)`.

### Managers with no remote client: the double run

Each statement below carries a label. **(read)** means read in the decompiled 0.7.2 source. **(measured)** means measured in a headless run of the probes in `maintenance/probes/double-run/`: a host entity, a flagged host and a real `Chicken`, no player. Line numbers are those of the decompiled source.

An `InteractionManager` built without a `PlayerRef` has no remote client. On such a manager the server plays the client's part itself, so it runs **every operation of a chain twice**: a simulation pass, then a server pass. An interaction whose work can safely run twice loses nothing. One whose work cannot gets it done twice, or throws.

#### The rule

- **Which managers. (read)** `new InteractionManager(null, ...)` is written in five places: NPCs (`NPCInteractionSystems`, with an `NPCInteractionSimulationHandler`), host entities from `InteractionHost.spawnHost` (the `SpawnInteraction` NPC action and the block-break host in `BlockHarvestUtils`), `EncounterManager`, `AbilityEntitySpawner` and `AbilityProjectileLauncher`. A player's manager is built with the `PlayerRef` (`InteractionSystems`) and runs the server pass only.
- **Projectile chains. (read)** A projectile's `ProjectileSpawn` chain runs on the shooter's manager (`ProjectileModule.onProjectileSpawnInteraction`, `:206`). Its `ProjectileHit` and `ProjectileMiss` chains run on the projectile's own manager if it has one, otherwise on the shooter's (`StandardPhysicsProvider`). When the shooter is an NPC, the `ProjectileSpawn` chain therefore runs on the NPC's manager, in two passes.
- **Two passes. (read)** `InteractionManager.doTickChain` (`:454`) calls `simulationTick` (`Operation.simulateTick`) and `serverTick` (`Operation.tick`, then `Operation.handle`) for each operation when the manager has no remote client (`:486-497`). `handle` runs in the server pass only. **(measured)** An `Interaction` whose `firstRun` writes one line wrote two: `pass=simulation`, then `pass=server`. On the manager flagged as a player's, it wrote one: `pass=server`.
- **Order. (read)** An operation that waits for `None` or `Client` runs the simulation pass first. One that waits for `Server` runs the server pass first. The server pass is `tick` and then `handle` (`serverTick`, `:591,602`), so for a `Server` wait the simulation pass runs after both (`:489-497`). **(measured)** A plugin type with `getWaitForDataFrom() = Server` wrote `pass=server`, then `pass=simulation`.
- **Shared state. (read)** Both passes use the same `InteractionEntry`, so they share one instance store (`context.getInstanceStore()`). Each pass keeps its own state and timestamp, so `firstRun` is `true` in both. `Interaction.tick` and `Interaction.simulateTick` are `final`: each runs the held-item check and the `RunTime` check, then calls `tick0` or `simulateTick0`.
- **No switch for the manager; the pass is visible. (read)** The manager keeps its flag private, and `setHasRemoteClient` is deprecated for removal and nothing calls it, so an interaction cannot ask which kind of manager it runs on. It can ask which pass it is in: `context.getEntry().isUseSimulationState()` (`InteractionContext.getEntry`, `:199`; `InteractionEntry.isUseSimulationState`, `:86`, both public) is `true` while `Operation.simulateTick` runs and `false` in the server pass (`InteractionManager.simulationTick` sets it around the call, `:653,669`). **(measured)** A plugin type that logged it wrote `sim=true` in the simulation line and `sim=false` in the server line on the NPC-shaped manager and on a real `Chicken`, `sim=false` first and `sim=true` second for a `Server` wait, and one `sim=false` line on the flagged manager.
- **Count the effect, not the calls.** What matters is how often the effect lands at its target: health lost, items added, entities spawned. A hook that runs twice can still land once.

#### What the simulation pass calls (read)

`SimpleInstantInteraction.simulateTick0` calls `simulateFirstRun`, and the default `simulateFirstRun` calls `firstRun` (`SimpleInstantInteraction.java:40,49-51`). `SimpleInteraction.simulateTick0` calls `tick0`. A type that overrides neither hook runs its work in both passes. The census (`census.py`) reads this for the 135 names registered in the `Interaction` codec registry. 135 classes were parsed, none were missed, and none carries two names.

| Simulation pass | Names | Types |
|-----------------|------:|-------|
| runs `firstRun` again (default `simulateFirstRun`) | 56 | listed below |
| does nothing (`simulateFirstRun` or `simulateTick0` is empty) | 21 | `ApplyAbilityEffects`, `ApplyEffect`, `CarryDroppedBlock`, `ClearCarriedBlock`, `DestroyTaggedVolumes`, `GrantAbilityCharges`, `LaunchAbilityProjectile`, `LaunchProjectile`, `OpenAbilityBench`, `PullEntityAbility`, `RemoveEntity`, `RunOnBlockTypes`, `Selector`, `SendBeacon`, `SendMessage`, `ShowEventTitle`, `SignalNearbyVolumes`, `SpawnAbilityEntity`, `SpawnTriggerVolume`, `SplitAbilityProjectile`, `TriggerAbilityFX` |
| runs `tick0` again | 2 | `DamageEntity`, `PlaceModeSelect` |
| wraps `tick0` in other code | 12 | `ApplyForce`, `BuilderTool`, `Camera`, `CarryPlaceBlock`, `Condition`, `DragEraseBlock`, `DragPlaceBlock`, `ExtrudePlaceBlock`, `PlaceBlock`, `Repeat`, `Simple`, `SurfaceDrawPlaceBlock` |
| block interactions: the simulate hook is empty | 25 | `AddItem`, `Bed`, `BreakBlock`, `CanBreakRespawnPoint`, `CarryBlock`, `ChangeFarmingStage`, `ChangeState`, `CycleBlockGroup`, `Door`, `FertilizeSoil`, `HarvestCrop`, `LaunchPad`, `OpenBenchPage`, `OpenContainer`, `OpenProcessingBench`, `PickBlock`, `PlaceFluid`, `Portal`, `Seating`, `SpawnMinecart`, `SpawnNPC`, `TeleportConfigInstance`, `UseCaptureCrate`, `UseCoop`, `UseWateringCan` |
| block interactions: a real simulate hook | 5 | `BlockCondition`, `ChangeBlock`, `PortalReturn`, `Teleporter`, `UseBlock` |
| a body of their own | 14 | `CancelChain`, `Chaining`, `ChangeActiveSlot`, `Charging`, `FirstClick`, `GroundedCondition`, `MemoriesCondition`, `MovementCondition`, `Parallel`, `Projectile`, `Replace`, `RevealMapMarkersInView`, `Serial`, `Wielding` |

The 56 names that run `firstRun` again: `AttachBeam`, `AugmentCondition`, `CameraShake`, `ChainFlag`, `ChangeStat`, `ChangeStatWithModifier`, `CheckUniqueItemUsage`, `ClearEntityEffect`, `ContextualUseNPC`, `CooldownCondition`, `DestroyBlock`, `DurabilityCondition`, `EffectCondition`, `EquipItem`, `EventStartInteraction`, `EventStopInteraction`, `ExitInstance`, `Explode`, `GameFlagCondition`, `GlobalEventStartInteraction`, `GlobalEventStopInteraction`, `HubPortal`, `IncreaseBackpackCapacity`, `IncrementCooldown`, `Interrupt`, `LearnRecipe`, `MarkAbilityBenchIntroSeen`, `ModifyIntervalConditionInteraction`, `ModifyInventory`, `Mount`, `OpenChapterRewards`, `OpenCustomUI`, `OpenItemStackContainer`, `OpenPage`, `PickupItem`, `PlacementCountCondition`, `PrefabSelectionInteraction`, `RefillContainer`, `ResetCooldown`, `RunRootInteraction`, `SetGameFlag`, `SetMemoriesCapacity`, `SpawnDeployableAtHitLocation`, `SpawnDeployableAtLocation`, `SpawnDeployableFromRaycast`, `SpawnPrefab`, `SpectateControl`, `StartObjective`, `StatsCondition`, `StatsConditionWithModifier`, `TeleportInstance`, `ToggleGlider`, `TriggerCooldown`, `TriggerSpawnMarkers`, `UseEntity`, `UseNPC`.

That a type runs its hook twice does not say its effect doubles. A condition reads and jumps. A flag setter sets a value. The effect of most of these 70 names (the 56, the 2 that run `tick0` again and the 12 that wrap it) has **not been classified**. Three have been measured (below). The census also does not read what a "body of their own" does.

#### What lands (measured)

Each row is a count at the target. The control is the same chain on a host whose manager was flagged as a player's (`setHasRemoteClient(true)`): one copy reads one unit, two copies in one chain read two units. All controls held.

| Type | On a manager with no remote client | Why | Measured |
|------|------------------------------------|-----|----------|
| `DamageEntity` | **once** | `simulateTick0` runs `tick0`, which queues the damage and stores it in the instance store. The server pass finds it and only processes it (`DamageEntityInteraction.java:180,195,510`). (read) | health -3 for one hit; one `Damage` event raised; two copies on the flagged manager: -6 |
| `LaunchProjectile` | **once** | `simulateFirstRun` is empty (`LaunchProjectileInteraction.java:141`). (read) | 1 projectile entity; two copies: 2 |
| `ChangeStat` with `Behaviour` `Add` (the default) | **twice** | `firstRun` passes the modifiers to `processStatChanges`, which calls `addStatValue` for `Add`; `Behaviour` defaults to `Add` (`ChangeStatBaseInteraction.java:44`), and `simulateFirstRun` is not overridden. (read) | `SignatureCharges` +10 for a `+5` chain; flagged: +5 |
| `ChangeStat` with `Behaviour` `Set` | **the same result twice** | `processStatChanges` calls `setStatValue`, which writes the value, so the second write changes nothing. (read) | `SignatureCharges` +5 for a chain that sets it to 5, the same as flagged (+5); the `Add` chain on the same harness: +10 |
| `ChangeStat` with `Behaviour` `Min` or `Max` | **the same result twice** (read, not measured) | `minStatValue` and `maxStatValue` write `min(current, value)` and `max(current, value)`, which a second call leaves as it is | none |
| `ModifyInventory` (waits for `Server`) | **twice** when the owner is another entity (a host) | server pass first, then `firstRun` again | 2 items for `ItemToAdd` of 1; flagged: 1; two copies on flagged: 2 |
| `ModifyInventory` (waits for `Server`) when the owner is the running entity | **desync, and the entity is removed** | the server pass runs first and the simulation pass second; see [the item-change check](#the-item-change-check-and-the-pass-order) | `Simulation and server tick are not in sync (operation position)`, `Counter: 1 vs 0`; the entity is removed |
| `ModifyInventory` with only the wait changed to `None` (a plugin subclass), owner is the running entity | **once, then the rest of the chain is cancelled as `ItemChanged`** | the simulation pass runs first and does the work; the server pass sees the changed held item and ends the chain; see [the item-change check](#the-item-change-check-and-the-pass-order) | 1 item, `chain_server_state=ItemChanged`, no desync line, the entity kept; flagged: 1 item, `Finished` |
| `AttachBeam` | **refuses** | `addComponent` is queued twice and the second throws `Entity already contains component type` on the world thread (see [beams.md](beams.md#gotchas--errors)) | 1 `BeamComponent` added, then the exception; the world reloads 5 s later. Flagged: 1 added, no exception |

`ChangeStatWithModifier` passes the same `Behaviour` field to `processStatChanges` (`ChangeStatWithModifierInteraction.java:66`), so the rows apply to it too (read). The shipped assets use both kinds: of the 206 objects with `"Type": "ChangeStat"` in `Server/` of the extracted `Assets.zip` (every `.json` file that parses, found at any depth; the 6,030 files that do not are under `World/` and `Prefabs/`, and none names `ChangeStat`), 98 have no `Behaviour` and 5 say `Add`, so 103 add and double; 89 say `Set` and 14 say `Min`, so 103 do not (none says `Max`). **(counted)**

The same results came out on a real `Chicken` run headless (no player) in a ticking section, on its own manager, for `ProbeLog` (two lines, simulation then server), `ChangeStat` (+10), `DamageEntity` (one hit on a `Sheep`, one `Damage` event) and `AttachBeam` (refused). The host agreed with the real NPC in all four.

#### The item-change check and the pass order

`Interaction.tickInternal` (`Interaction.java:288-302`) runs in both passes. If the held slot now holds a different item than when the context was built, the pass sets `ItemChanged` and does not call `tick0` or `simulateTick0`. A chain that runs through another entity is exempt (the owner is not the entity). An interaction that puts an item into the held slot of the entity that runs it (`ModifyInventory` does, with the owner the running entity) therefore changes what the **second** pass does, and the outcome depends on which pass that is, because only the server pass throws on `ItemChanged`:

- **The wait is `Server`: the server pass runs first, the simulation pass second. (measured)** The simulation pass sees the changed item and skips its hook, and `Interaction.simulateTick` has no `ItemChanged` case (`:263-286`; `tick` has one, `:256`), so it ends with its operation counter behind. `doTickChain` throws the desync (`:499-505`), and `TickInteractionManagerSystem` catches it and **removes the entity that runs the chain** (`InteractionSystems.java:255`). Measured with `ModifyInventory` (shipped, waits for `Server`): `Counter: 1 vs 0`, entity removed.
- **The wait is `None`: the simulation pass runs first, the server pass second. (measured)** When the simulation pass does the work (the default `simulateFirstRun`, which calls `firstRun`), the server pass sees the changed item, and `Interaction.tick` throws `ChainCancelledException(ItemChanged)` (`:256-258`), which the manager catches and only ends the chain with (`InteractionManager.java:376`). Measured with a plugin subclass of `ModifyInventory` that changes nothing but `getWaitForDataFrom()` to `None`: 1 item, `chain_server_state=ItemChanged`, no desync line, the entity kept. The effect lands once, and the chain ends there: no operation after it runs (read; the measured chain had none after it).
- **The wait is `Client`. (read, not measured)** `doTickChain` runs the simulation pass first for `Client` as for `None` (`:486-492`; only `Server` runs it second), and the client state the simulation pass stores satisfies the server pass's wait, so the reading is the `None` one, with the same precondition: the simulation pass must do the work. Of the 30 block interactions, 22 wait for `Client`, and 19 of those have an empty `simulateInteractWithBlock` (the census, `maintenance/probes/double-run/census-0.7.2.txt`; the other 8 wait for `Server`, the case above, which needs no such precondition). For those 19 the simulation pass changes nothing, the server pass changes the held slot after that operation's check has run, so the effect lands once and that operation is not cancelled (read). The next operation in the chain still meets the check. The same holds under `None` for a type whose `simulateFirstRun` is empty.
- **`"OnItemChangeBehavior": "Ignore"` on a `Server`-wait interaction. (measured)** No exception, and the effect doubled (2 items).

Measured on a host; the same code runs for an NPC (read).

#### Writing your own interaction

- **Extend `SimpleInstantInteraction`. (read)** Your `firstRun` runs in both passes on a manager with no remote client. (measured with a plugin type that overrides only `firstRun`: two lines.)
- **If the effect must land once, silence the simulation pass. (measured)** Override `simulateFirstRun` with an empty body. A plugin type that did this wrote one line on the same manager. This is what `LaunchProjectile` and `ApplyEffect` do.

  ```java
  @Override
  protected void simulateFirstRun(InteractionType type, InteractionContext context,
                                  CooldownHandler cooldownHandler) {
      // empty: the effect lands once, in the server pass
  }
  ```

- **If the effect sets a value, it is usually safe. (read)** Setting a stat to a value, clearing an effect or raising a flag gives the same result twice (a `ChangeStat` with `Behaviour: Set` read the same on a manager with no remote client as on a flagged one; measured). Adding to a stat is not that: the default `Behaviour` of `ChangeStat` is `Add`. Read the body before you rely on it: this page has classified only the types measured above.
- **Or branch on the pass. (measured on the NPC-shaped and the flagged host manager; read for a player's)** `context.getEntry().isUseSimulationState()` is `false` in the server pass, and a player's manager has only that pass, so `if (context.getEntry().isUseSimulationState()) return;` at the top of a hook that both passes reach makes it a server-pass effect. For a `SimpleInstantInteraction` the empty `simulateFirstRun` above says the same thing without a flag. The flag is for code that is shared between the passes, such as a `tick0` you write yourself.
- **Or guard it with the instance store. (read)** `DamageEntity` runs its real work in the simulation pass, stores the result with `context.getInstanceStore().putMetaObject(...)`, and the server pass reads it back. Both passes see the same store.
- **A hand-written `Interaction` must write `simulateTick0`. (read)** It is abstract in `Interaction`. `SimpleInteraction` implements it by calling `tick0`. If you extend `Interaction` directly and call `tick0` from `simulateTick0`, you get the same double run.
- **Changing the held slot from an interaction that runs for its own entity depends on the wait. (measured)** With a `Server` wait, on an NPC-shaped manager, that desyncs and removes the entity. With a `None` wait the effect lands once and the rest of the chain is cancelled as `ItemChanged`, which is not a crash but ends the chain early ([above](#the-item-change-check-and-the-pass-order)). A chain a host or projectile runs for another owner is exempt.
- **Keep both passes on the same path. (read)** The two passes must end on the same operation, or `doTickChain` throws the desync. The item-change case with a `Server` wait is the measured instance.
- **`Server` waits reverse the order. (measured)** If your interaction waits for `Server`, your `firstRun` runs in the server pass first, then in the simulation pass. (read) The default `simulateTick0` copies a `Failed` server result into the simulation state (`context.getServerState()`).

### SimpleBlockInteraction

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client`

Abstract base class for interactions that act on a targeted block (`BreakBlock`, `PlaceFluid`, `UseBlock`, `Door`, `OpenContainer`, and many builtin interactions extend it; `PlaceBlock` does not, and extends `SimpleInteraction` directly). It resolves the target block position from the client and hands it to the subclass.

**Extends:** `SimpleInteraction`

#### Key Methods

```java
// Block targets come from the client
WaitForDataFrom getWaitForDataFrom()   // returns WaitForDataFrom.Client
boolean needsRemoteSync()

// Subclasses implement these two. interactWithBlock is the effect of the server pass (tick0);
// simulateInteractWithBlock is the hook of the simulation pass (simulateTick0). The server calls it
// itself on a manager with no remote client; for a player the client runs its own half and the
// server never calls it
protected abstract void interactWithBlock(World world, CommandBuffer<EntityStore> commandBuffer,
        InteractionType type, InteractionContext context, ItemStack itemInHand,
        Vector3i targetBlock, CooldownHandler cooldownHandler)
protected abstract void simulateInteractWithBlock(InteractionType type, InteractionContext context,
        ItemStack itemInHand, World world, Vector3i targetBlock)

// Helpers
protected static boolean hasRemovedBlockContext(InteractionContext context)   // 0.6.3+: true when the targeted block was already removed
protected static void computeCurrentBlockSyncData(InteractionContext context)  // 0.7.2+
```

`SimpleBlockInteraction.resolveBaseBlockPosition(World, BlockPosition)` was removed in 0.7.2. The
multi-block anchor lookup is now `BlockOperations.resolveBaseBlockPosition(ChunkStore, BlockPosition)`
(`com.hypixel.hytale.server.core.universe.world.chunk.BlockOperations`); pass `world.getChunkStore()`,
as `SimpleBlockInteraction`'s own `tick0` does.

#### Codec

```java
public static final BuilderCodec<SimpleBlockInteraction> CODEC;
```

JSON property added on top of `SimpleInteraction`:

| Property | Type | Description |
|----------|------|-------------|
| `UseLatestTarget` | boolean | Use the client's latest target block position for this interaction (codec doc: "Determines whether to use the clients latest target block position for this interaction.") |

`UseLatestTarget` is inherited by subclasses whose codec builds on `SimpleBlockInteraction.CODEC` (e.g. `Door`, `OpenContainer`, `PlaceFluid`), which is 35 of the 36 subclasses in the jar. The exception is `UseCaptureCrateInteraction` (farming), which extends `SimpleBlockInteraction` but builds its codec on `SimpleInteraction.CODEC`, so `UseCaptureCrate` does not accept the key.

To write your own block-targeting interaction type, extend `SimpleBlockInteraction`, implement the two abstract methods, and register a `Type` string as described in [Registering a Custom Interaction Type (Java)](#registering-a-custom-interaction-type-java).

### InteractionType Enum

**Package:** `com.hypixel.hytale.protocol`

Enum representing the type of interaction trigger. Members are PascalCase (`Primary`, `Secondary`, `Ability1`–`Ability4` (`Ability4` added in 0.7.2), `Use`, `Pick`, `Pickup`, `CollisionEnter`, `CollisionLeave`, `Collision`, `EntityStatEffect`, `SwapTo`, `SwapFrom`, `Death`, `Wielding`, `ProjectileSpawn`, `ProjectileHit`, `ProjectileMiss`, `ProjectileBounce`, `Held`, `HeldOffhand`, `Equipped`, `Dodge`, `GameModeSwap`, and, as of 0.6.3, `OnBreak` and `OnBreakImpact` — block-break hooks fired via `BlockHarvestUtils.fireOnBreakInteraction` / `queueOnBreakImpactInteraction`). The JSON `EnumCodec` matches names case-insensitively, so `"PRIMARY"` and `"Primary"` both parse; shipped assets use PascalCase.

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
ComponentType<EntityStore, CarriedBlock> getCarriedBlockComponentType()                // block currently carried (CarryBlock / CarryPlaceBlock / CarryDroppedBlock / ClearCarriedBlock types)
ResourceType<EntityStore, CarriedBlockSystems.QueueResource> getCarriedBlockQueueResourceType()

// 0.7.2+: state behind the OpenChapterRewards type
ComponentType<EntityStore, OpenChapterRewardsInteraction.ChapterRewardsPrompt> getChapterRewardsPromptComponent()
ComponentType<EntityStore, OpenChapterRewardsInteraction.ChapterRewardsSoundPlayed> getChapterRewardsSoundPlayedComponent()
```

`InteractionModule` registers 77 of the 135 `Type` strings. `SpectateControl` is documented with the rest of spectator mode in [player.md](player.md#spectatecontrol-interaction); for which of the other 76 have a written section, see the [Complete Type Registry](#complete-type-registry).

**Types registered by other plugins.** `Interaction.CODEC` is shared, so bundled plugins add their own `Type` strings in *their* `setup()`, and those types only exist when that plugin is loaded. Twenty-two other modules and plugins contribute the remaining 58 types — `Hytale:GameFlags` adds `SetGameFlag` and `GameFlagCondition` (see [world.md → Game Flags](world.md#game-flags)), and the registry table names the rest against their registering plugin.

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
  "Cooldown": { "Cooldown": 0.217 },
  "Interactions": ["Weapon_Sword_Primary"]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `RequireNewClick` | boolean | If true, must click again to chain (holding won't auto-chain) |
| `ClickQueuingTimeout` | float | Buffer window to queue next attack input |
| `Cooldown` | object | Minimum delay between attacks (see [Cooldown Configuration](#cooldown-configuration)) |
| `Interactions` | array | List of interactions to execute. Carries `nonNull()` and `nonEmptyArray()`, but the field starts as an empty array, so an omitted key loads as a root that runs nothing; a written `[]` fails validation |
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

    // Restart a cooldown at its full duration (remaining = max) and refill its charges
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
| `ResetCooldown` | Restart a cooldown at its full duration and refill its charges. It leaves the cooldown running; it does not make it ready |
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

### AttachBeam

**Package:** `com.hypixel.hytale.builtin.beam.interaction.AttachBeamInteraction`

Draws a beam from the executing entity to another entity. It adds a `BeamComponent` to the executing
entity, and `BeamSystems.Tracker` sends the beam to clients that can see it. Registered by the bundled
`BeamPlugin` (`com.hypixel.hytale.builtin.beam.BeamPlugin`, 0.7.2+, absent from
`Constants.CORE_PLUGINS`), which also owns the `Beam` asset store at `Server/Entity/Beams/`. A `Beam`
asset has one key, the required `TexturePath`. Four ship: `Basic`, `Chain`, `Fire` and `Rope`.
For the full subsystem (the `Beam` asset and its validator messages, the `BeamComponent` and
`AttachedBeam` Java API, `/beam`, client sync, and gotchas), see [Beams](beams.md).

> **Danger.** `AttachBeam` on an entity that already has a `BeamComponent`, or in a chain that runs on
> an NPC's `InteractionManager` (`ProjectileModule` runs a projectile's `ProjectileSpawn` chain on its creator's manager),
> throws and ends the world thread. See the first two items under
> [Gotchas](beams.md#gotchas--errors).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `TargetEntity` | enum | `User` | Where the beam ends: `User`, `Owner` or `Target` (the default `EnumCodec`'s keys for `InteractionTarget`'s constants), resolved against the context. Carries `Validators.nonNull()`, which the default satisfies, so it may be omitted |
| `BeamConfig` | string | — | **Required** (`Validators.nonNull()`). A `Beam` asset id, validated at load. The codec, `Beam.CHILD_ASSET_CODEC` (a `ContainedAssetCodec`), also decodes an inline `Beam` object, but run on a booted server such a beam gets index `Integer.MIN_VALUE` (a reload of the same file resolves a real one); use an id. See [Beams](beams.md#an-inline-beamconfig) |
| `Scale` | float | `1.0` | Beam scale |
| `SourceNodeName` | string | — | Model node on the executing entity to attach to |
| `TargetNodeName` | string | — | Model node on the target entity to attach to |

Both shipped uses run on a projectile's `ProjectileSpawn`, so the rope or chain trails from the
projectile back to the shooter's hand. From
`Server/ProjectileConfigs/Tools/Projectile_Config_Hookshot.json`:

```json
{
  "Type": "AttachBeam",
  "BeamConfig": "Rope",
  "TargetEntity": "Owner",
  "Scale": 0.25,
  "TargetNodeName": "R-Attachment"
}
```

The other is `Server/ProjectileConfigs/Abilities/Projectile_Config_ChainHook.json`, which uses
`"BeamConfig": "Chain"` and `"Scale": 0.5`.

---

### OpenChapterRewards

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.OpenChapterRewardsInteraction`

Opens the chapter-complete page on the player's client, then runs one of two root interactions with
the player's answer. The server sends the page as an `OpenChapterRewardsPage` packet and records the
pending answer on the player in a `ChapterRewardsPrompt` component. When the client answers,
`GamePacketHandler` runs `Success` or `Fail` on the block the player originally interacted with, so
block interactions such as `PortalReturn` work there. Codec doc: "Set RequireNewClick on the root
that holds it, or holding the interact key opens the page again." It does nothing for an entity
without a `PlayerRef`. An answer is dropped if it arrives from a different world from the one the page
was opened in.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ChapterId` | string | — | **Required**, `nonNull` and `nonEmptyString`. The client holds the chapter data and the server only relays this id |
| `Success` | root interaction | — | **Required** (`Validators.nonNull()`). Run when the player takes the main action (the button labelled by `LeaveKey`). It carries no target entity |
| `Fail` | root interaction | — | Run when the player keeps playing or dismisses the page; omit it to run nothing |
| `TitleKey` | string | — | **Required**, `nonNull` and `nonEmptyString`. Localization key for the title |
| `SubtitleKey` | string | — | **Required**, as `TitleKey`. The line under the title |
| `LeaveKey` | string | — | **Required**, as `TitleKey`. Label of the `Success` button |
| `StayKey` | string | — | **Required**, as `TitleKey`. Label of the `Fail` button |
| `ShowRewards` | boolean | `true` | List the chapter's reward tiles; `false` shows only the text and the two buttons |
| `SoundEventId` | string | — | One-shot sound played in 2D, in the `Music` category, the first time this chapter's page opens for that player in a world (tracked by the `ChapterRewardsSoundPlayed` component) |

`Success` and `Fail` take an inline `{ "Interactions": [...] }` or a root-interaction id, both
late-validated. The one shipped use is the `Use` interaction of the `Chapter1_TheDeepworks` block state
in `Server/Item/Items/Portal/Dungeon/Dungeon_Portal_End.json`:

```json
{
  "Type": "OpenChapterRewards",
  "ChapterId": "fe093c59-8900-4b87-b30c-e536f5cc7491",
  "TitleKey": "server.portals.dungeon.complete.title",
  "SubtitleKey": "server.portals.dungeon.complete.subtitle",
  "LeaveKey": "server.portals.dungeon.leave",
  "StayKey": "server.portals.dungeon.stay",
  "SoundEventId": "SFX_Event_Chapter_1_Complete_Sting",
  "Success": { "Interactions": ["Portal_Return"] }
}
```

---

### Complete Interaction Type Reference

**Class Hierarchy Overview**

```
Interaction (abstract)
└── SimpleInteraction
    └── SimpleInstantInteraction (abstract)

RootInteraction            (a separate asset class, not an Interaction subclass)
```

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

`RootInteraction` implements `JsonAssetWithMap` and `NetworkSerializable` itself and extends nothing,
so a `RootInteraction` cannot stand where an `Interaction` is expected: the two live in separate asset
stores and resolve through separate lookups (`Interaction.getInteractionOrUnknown` /
`RootInteraction.getRootInteractionOrUnknown`).

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
