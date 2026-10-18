---
title: "Managers with no remote client: the double run"
description: "What an interaction's work does on an InteractionManager with no remote client (an NPC's, a host entity's, an ability entity's): the simulation and server passes both run, which interaction types land once, twice or throw, and how the pass order and the item-change check decide it. Measured headless."
seo:
  type: TechArticle
---

# Managers with no remote client: the double run

**Doc type:** Java API + JSON asset format · **Verified against 0.7.2**

> **See also:** [Interactions API](interactions.md) for the `Interaction` base class and `SimpleInstantInteraction`, [Operation System](interactions-operations.md) for `simulateTick()` and `tick()`.

Each statement below carries a label. **(read)** means read in the decompiled 0.7.2 source. **(measured)** means measured in a headless run of the probes in `maintenance/probes/double-run/`: a host entity, a flagged host and a real `Chicken`, no player. **(counted)** means counted over the extracted `Assets.zip` by `usage.py` in the same directory. Line numbers are those of the decompiled source.

An `InteractionManager` built without a `PlayerRef` has no remote client. On such a manager the server plays the client's part itself, so it runs **every operation of a chain twice**: a simulation pass, then a server pass. An interaction whose work can safely run twice loses nothing. One whose work cannot gets it done twice, or throws.

## The rule

- **Which managers. (read)** `new InteractionManager(null, ...)` is written in five places: NPCs (`NPCInteractionSystems`, with an `NPCInteractionSimulationHandler`), host entities from `InteractionHost.spawnHost` (the `SpawnInteraction` NPC action and the block-break host in `BlockHarvestUtils`), `EncounterManager`, `AbilityEntitySpawner` and `AbilityProjectileLauncher`. A player's manager is built with the `PlayerRef` (`InteractionSystems`) and runs the server pass only.
- **Projectile chains. (read)** A projectile's `ProjectileSpawn` chain runs on the shooter's manager (`ProjectileModule.onProjectileSpawnInteraction`, `:206`). Its `ProjectileHit` and `ProjectileMiss` chains run on the projectile's own manager if it has one, otherwise on the shooter's (`StandardPhysicsProvider`). When the shooter is an NPC, the `ProjectileSpawn` chain therefore runs on the NPC's manager, in two passes.
- **Two passes. (read)** `InteractionManager.doTickChain` (`:454`) calls `simulationTick` (`Operation.simulateTick`) and `serverTick` (`Operation.tick`, then `Operation.handle`) for each operation when the manager has no remote client (`:486-497`). `handle` runs in the server pass only. **(measured)** An `Interaction` whose `firstRun` writes one line wrote two: `pass=simulation`, then `pass=server`. On the manager flagged as a player's, it wrote one: `pass=server`.
- **Order. (read)** An operation that waits for `None` or `Client` runs the simulation pass first. One that waits for `Server` runs the server pass first. The server pass is `tick` and then `handle` (`serverTick`, `:591,602`), so for a `Server` wait the simulation pass runs after both (`:489-497`). **(measured)** A plugin type with `getWaitForDataFrom() = Server` wrote `pass=server`, then `pass=simulation`.
- **Shared state. (read)** Both passes use the same `InteractionEntry`, so they share one instance store (`context.getInstanceStore()`). Each pass keeps its own state and timestamp, so `firstRun` is `true` in both. `Interaction.tick` and `Interaction.simulateTick` are `final`: each runs the held-item check and the `RunTime` check, then calls `tick0` or `simulateTick0`.
- **No switch for the manager; the pass is visible. (read)** The manager keeps its flag private, and `setHasRemoteClient` is deprecated for removal and nothing calls it, so an interaction cannot ask which kind of manager it runs on. It can ask which pass it is in: `context.getEntry().isUseSimulationState()` (`InteractionContext.getEntry`, `:199`; `InteractionEntry.isUseSimulationState`, `:86`, both public) is `true` while `Operation.simulateTick` runs and `false` in the server pass (`InteractionManager.simulationTick` sets it around the call, `:653,669`). **(measured)** A plugin type that logged it wrote `sim=true` in the simulation line and `sim=false` in the server line on the NPC-shaped manager and on a real `Chicken`, `sim=false` first and `sim=true` second for a `Server` wait, and one `sim=false` line on the flagged manager.
- **Count the effect, not the calls.** What matters is how often the effect lands at its target: health lost, items added, entities spawned. A hook that runs twice can still land once.

## What the simulation pass calls (read)

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

That a type runs its hook twice does not say its effect doubles. A condition reads and jumps. A flag setter sets a value. [The table below](#what-each-of-the-48-types-does) classifies the 48 types that shipped NPC, encounter and ability assets can start on such a manager; the other 87 are **not classified**, and a plugin that uses one follows the rule above. The census also does not read what a "body of their own" does; for the 48, the table does.

## What lands (measured)

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
| `Explode` | **twice** | `firstRun` damages every entity in the radius straight away (`ExplodeInteraction.java:52`, `ExplosionUtils.java:255`; the `Damage` event is processed inline), stores nothing in the instance store, and `simulateFirstRun` is not overridden. (read) | a `Sheep` 3 blocks away: health -2.0 where the flagged host reads -1.0, and 2 `Damage` events (environment source) raised at it where flagged raises 1; two copies on flagged: -2.0 and 2 events |
| `TriggerCooldown`, a cooldown of 3 charges | **twice** | `resetCooldown` ends in `deductCharge()` (`TriggerCooldownInteraction.java:109`), which takes a charge each call. (read) | 1 charge left where the flagged host leaves 2 (2 used, not 1); two copies on flagged: 1 left |
| `TriggerCooldown`, the default 1 charge | **the same result twice** | `deductCharge` stops at 0 (`CooldownHandler.java:101-103`). (read) | 0 left, as flagged |
| `ModifyInventory` with `AdjustHeldItemQuantity` -1, owner is the running entity, stack of 5 | **twice, no desync** | the first pass writes the slot and calls `context.setHeldItem` (`ModifyInventoryInteraction.java:108-113`), so the item-change check finds no change and `firstRun` runs again. (read) | 3 items left where flagged leaves 4; two copies on flagged: 3 |
| the same, stack of 1 | **the same result twice** | the second pass finds no held item (`:106`). (read) | the one item removed, as flagged |
| `ApplyForce` | **once** | the force is applied in `simulateTick0` (`ApplyForceInteraction.java:189-195`); `tick0` returns on the first run (`:156-158`). A flagged manager has no simulation pass and applies none: the client does. (read) | vertical velocity +5.0 for a force of 5, +10.0 for two copies; flagged +0.0, its chain ends `Failed` waiting for the client |
| `Projectile` | **once** | `simulateFirstRun` only records the aim (`ProjectileInteraction.java:149`); `firstRun` spawns (`:101`). On a flagged manager the client spawns it. (read) | 1 projectile entity, 2 for two copies; flagged 0 and `Failed` |
| `Repeat` | **guarded** | `tick0` forks and stores `FORKED_CHAIN` in the instance store (`RepeatInteraction.java:52,80`); `simulateTick0` only reads it (`:89`). (read) | the forked `LaunchProjectile`: 1 projectile, as flagged; two `Repeat`: 2 |
| `ClearEntityEffect` | **the same result twice** | `firstRun` removes the effect (`ClearEntityEffectInteraction.java:50`); a second removal finds none. The harness cannot count the second removal: this is an end-state claim. (read) | the effect `Drop_Rare` applied to a `Sheep` first: gone, as flagged; a chain that clears nothing leaves it |
| `DestroyBlock` | **the same result twice** | `performBlockBreak` returns when the block is already air (`BlockHarvestUtils.java:172`). (read) | 1 `BreakBlockEvent` and the block (`Rock_Stone_Cobble`) gone, as flagged; two copies at one block: 1 event |

`ChangeStatWithModifier` passes the same `Behaviour` field to `processStatChanges` (`ChangeStatWithModifierInteraction.java:66`), so the rows apply to it too (read); no shipped chain NPCs or abilities run uses it. The shipped assets use both kinds of `ChangeStat`: of the 114 run-reached objects, 102 run on a manager with no remote client; 51 of those have no `Behaviour` and 4 say `Add`, so 55 add and double, and 33 say `Set` and 14 say `Min`, so 47 give the same result twice (none says `Max`). **(counted over the run-reached objects, below)** Over all of `Server/` the figures are 206 objects: 98 without `Behaviour`, 5 `Add`, 89 `Set`, 14 `Min`.

The same results came out on a real `Chicken` run headless (no player) in a ticking section, on its own manager, for `ProbeLog` (two lines, simulation then server), `ChangeStat` (+10), `DamageEntity` (one hit on a `Sheep`, one `Damage` event), `AttachBeam` (refused), `Explode` (2 `Damage` events at the `Sheep`), `TriggerCooldown` (2 of 3 charges used), `Projectile` (1), `Repeat` (1), `ClearEntityEffect` (gone) and `DestroyBlock` (1 event, block gone). The host agreed with the real NPC in all ten. Two were not run on a real NPC: `ApplyForce` (the NPC's physics system consumes the velocity) and `ModifyInventory`'s `AdjustHeldItemQuantity` (the `Chicken` has no hotbar); their rows rest on the host.

## What each of the 48 types does

### The population (counted)

The table covers the **48 of the 135 registered types** that a shipped asset can start on a manager with no remote client. The predicate, as `usage.py` runs it:

- **Seeds.** Every file under `Server/NPC` (1,858), `Server/EncounterManager` (67), and the ability roots `Server/Abilities`, `Server/Item/Interactions/Abilities` and `Server/Item/RootInteractions/Abilities` (68).
- **Edges.** Any JSON string equal to the id of an interaction, root interaction, projectile config, projectile or ability asset, and `Parent`. An object counts when its `Type` is a registered interaction type or its `Parent` chain reaches one.
- **Items.** An `Item/Items` id is an edge only when the item is *held* (the role's `HotbarItems` and `OffHandItems`, and the parameters they `Compute` from: `Weapons`, `OffHand`, `Weapon`) and its root for `Primary`, `Secondary` or `Ability1` to `Ability4` is tagged `Attack` (`ActionAttack.java:148-160`: with no `Attack` set, an NPC runs the held item's root, and only a tagged one). 140 held-item strings in NPC files meet that, 59 do not. A field that merely names an item (`AttractiveItemSet`, `Items`, `ProduceItem`, `HarvestInteractionRequiredItems`) starts no chain.
- **Result.** Counting every string that names an item as an edge gives 58 types; this predicate gives 48. The 10 dropped are reachable only through such a field: `ChangeActiveSlot`, `ContextualUseNPC`, `CycleBlockGroup`, `DragPlaceBlock`, `EquipItem`, `ExtrudePlaceBlock`, `PlaceModeSelect`, `RefillContainer`, `SpawnNPC` and `SurfaceDrawPlaceBlock`.
- **Runs on.** Each object carries the manager its chain runs on: `NPC` (the NPC's own; a projectile it fires runs its `ProjectileSpawn` chain there), `host` (under a `SpawnInteraction` action), `encounter`, `ability entity or projectile` (`AbilityEntitySpawner.java:59`, `AbilityProjectileLauncher.java:102`: `new InteractionManager(null, ...)`; the projectile's `ProjectileHit` and `ProjectileMiss` chains, not its `ProjectileSpawn`, which runs on the shooter's) and `ability caster`. A player's manager has a remote client and runs **one** pass, so an object reached only as an ability caster is outside the double run unless an NPC casts it. Six types are reached only that way: `ApplyAbilityEffects`, `AttachBeam`, `GrantAbilityCharges`, `GroundedCondition`, `LaunchAbilityProjectile` and `SpawnAbilityEntity`. The other 42 run on a manager with no remote client. A shared file counts under every manager that reaches it.

Verdicts: **12 measured, 36 read, 0 unknown** (the limit was 5). `Simple`'s `Effects` (animation, sound, particles) go to clients and are not classified. The 87 other types are not classified. The table is `maintenance/probes/double-run/verdict-table.tsv`; `usage.py` re-checks it against the population and the decompiled source on every run, so a new build that changes a type's reach or moves a deciding line is reported.

### Lands twice, throws or desyncs (4)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `ChangeStat` | 114 (NPC 102, ability caster 12) | measured | direct (EntityStatMap) | `ChangeStatInteraction.java:30` firstRun runs in both passes (:30); Add doubles, Set/Min/Max give the same result twice (13a, per Behaviour) |
| `ModifyInventory` | 17 (NPC 17) | measured | direct (the container) | `ModifyInventoryInteraction.java:86` firstRun runs in both passes (:86). AdjustHeldItemQuantity doubles (stack > 1); ItemToRemove/ItemToAdd are gated by RequiredGameMode in 14 of 17 shipped objects |
| `Explode` | 10 (NPC 9, ability entity or projectile 2) | measured | direct (the Damage event and block damage run inline) | `ExplodeInteraction.java:52` firstRun runs in both passes (:52); the target takes the damage twice, the blocks too if DamageBlocks |
| `AttachBeam` | 1 (ability caster 1) | measured | deferred (addComponent) | `AttachBeamInteraction.java:62` firstRun queues addComponent in each pass (:62); the second throws "Entity already contains component type" on the world thread (13a). The one shipped object (ChainHook) sits in a ProjectileSpawn chain, which runs on the shooter's manager: no shipped chain reaches it on a manager with no remote client |

### The same result twice (4)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `ClearEntityEffect` | 26 (NPC 25, host 7, ability entity or projectile 8, ability caster 8) | measured | direct (EffectControllerComponent) | `ClearEntityEffectInteraction.java:37` firstRun removes the effect (:37-50); a second removal finds none. The end state matches the flagged manager's |
| `TriggerCooldown` | 16 (NPC 3, ability caster 13) | measured | direct (CooldownHandler) | `TriggerCooldownInteraction.java:39` deductCharge runs in both passes (:109); with the default 1 charge the second finds none, with 3 charges it uses 2. None of the 19 shipped objects lists Charges (16 are run-reached) |
| `DestroyBlock` | 5 (NPC 5) | measured | direct (the chunk section) | `DestroyBlockInteraction.java:34` firstRun runs in both passes (:34); performBlockBreak returns when the block is already air (BlockHarvestUtils.java:172). 1 BreakBlockEvent, the block gone |
| `Interrupt` | 2 (NPC 2, ability entity or projectile 1, ability caster 1) | read | direct (cancelChains) | `InterruptInteraction.java:64` firstRun cancels the Target's matching chains (:75-80); a second pass finds none |

### Guarded: the type runs its effect once (4)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `DamageEntity` | 761 (NPC 744, host 5, encounter 2, ability entity or projectile 15, ability caster 14) | measured | direct (the Damage event is processed inline) | `DamageEntityInteraction.java:195` simulateTick0 runs tick0, which queues the damage in the instance store (:510); the server pass finds it and only processes it (:180) |
| `Parallel` | 267 (NPC 258, ability caster 9) | read | none | `ParallelInteraction.java:52` tick0 forks the branches after the first (:41-47); simulateTick0 only runs the first (:52), so the forks are made once. Each branch is its own chain and runs twice per operation |
| `Repeat` | 24 (NPC 24) | measured | direct (the forked chain) | `RepeatInteraction.java:89` tick0 forks once and stores FORKED_CHAIN in the instance store (:52,:80); simulateTick0 only reads it (:89). 1 forked projectile, 2 for two |
| `TriggerSpawnMarkers` | 2 (NPC 2) | read | deferred (commandBuffer.run) | `TriggerSpawnMarkersInteraction.java:51` firstRun queues trigger() in each pass (:64); SpawnMarkerEntity.trigger returns false while spawnCount > 0 (:816), which the first trigger sets (:402) |

### Once: the simulation pass does nothing (20)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `Selector` | 389 (NPC 378, host 5, encounter 3, ability entity or projectile 6, ability caster 6) | read | deferred (the forked hit chains) | `SelectInteraction.java:222` simulateTick0 is empty (:222); tick0 selects and forks the hit chains in the server pass (:101) |
| `ApplyEffect` | 155 (NPC 114, host 7, encounter 3, ability entity or projectile 13, ability caster 43) | read | direct (EffectControllerComponent) | `ApplyEffectInteraction.java:91` simulateFirstRun is empty (:91) |
| `Projectile` | 145 (NPC 119, host 22, encounter 5) | measured | deferred (addEntity) | `ProjectileInteraction.java:149` simulateFirstRun only records the aim (:149); firstRun spawns the projectile (:101). 1 projectile entity, 2 for two |
| `RemoveEntity` | 54 (NPC 38, host 10, encounter 8, ability entity or projectile 3) | read | deferred (removeEntity) | `RemoveEntityInteraction.java:58` simulateFirstRun is empty (:58) |
| `LaunchProjectile` | 42 (NPC 42) | measured | deferred (addEntity) | `LaunchProjectileInteraction.java:141` simulateFirstRun is empty (:141) (13a) |
| `ApplyForce` | 22 (NPC 22) | measured | direct (Velocity) | `ApplyForceInteraction.java:189` the force is applied in simulateTick0 only (:189-195); tick0 returns on the first run (:156). A flagged manager has no simulation pass and applies none |
| `SendBeacon` | 11 (NPC 10, encounter 1) | read | deferred | `SendBeaconInteraction.java:69` simulateFirstRun is empty (:69) |
| `LaunchAbilityProjectile` | 9 (ability caster 9) | read | deferred | `LaunchAbilityProjectileInteraction.java:53` simulateFirstRun is empty (:53); reached only in ability casts, on the caster's manager |
| `TriggerAbilityFX` | 8 (host 2, ability entity or projectile 6, ability caster 5) | read | none | `TriggerAbilityFXInteraction.java:110` simulateFirstRun is empty (:110) |
| `ChangeState` | 6 (NPC 3, host 4) | read | direct (the block) | `ChangeStateInteraction.java:104` simulateInteractWithBlock is empty (:104); interactWithBlock (:55) runs in the server pass |
| `SpawnTriggerVolume` | 5 (NPC 3, host 1, encounter 1) | read | deferred | `SpawnTriggerVolumeInteraction.java:150` simulateFirstRun is empty (:150) |
| `BreakBlock` | 4 (NPC 4) | read | direct (the block) | `BreakBlockInteraction.java:154` simulateInteractWithBlock is empty (:154) |
| `PlaceFluid` | 4 (NPC 4) | read | direct (the block) | `PlaceFluidInteraction.java:115` simulateInteractWithBlock is empty (:115) |
| `GrantAbilityCharges` | 2 (ability caster 2) | read | direct | `GrantAbilityChargesInteraction.java:102` simulateFirstRun is empty (:102); reached only in ability casts |
| `SignalNearbyVolumes` | 2 (NPC 1, host 1) | read | deferred | `SignalNearbyVolumesInteraction.java:123` simulateFirstRun is empty (:123) |
| `SplitAbilityProjectile` | 2 (ability entity or projectile 2, ability caster 2) | read | deferred | `SplitAbilityProjectileInteraction.java:192` simulateFirstRun is empty (:192) |
| `ApplyAbilityEffects` | 1 (ability caster 1) | read | direct | `ApplyAbilityEffectsInteraction.java:126` simulateFirstRun is empty (:126) |
| `PullEntityAbility` | 1 (ability entity or projectile 1, ability caster 1) | read | direct | `PullEntityAbilityInteraction.java:130` simulateFirstRun is empty (:130) |
| `SendMessage` | 1 (NPC 1) | read | none | `SendMessageInteraction.java:93` simulateFirstRun is empty (:93) |
| `SpawnAbilityEntity` | 1 (ability caster 1) | read | deferred (addEntity) | `SpawnAbilityEntityInteraction.java:101` simulateFirstRun is empty (:101) |

### Flow: the effect is the children's (8)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `Simple` | 1247 (NPC 1214, host 15, encounter 5, ability entity or projectile 8, ability caster 20) | read | none | `SimpleInteraction.java:55` tick0 only jumps to the failed label (SimpleInteraction.java:55-58); simulateTick0 calls it. Its Effects (animation, sound, particles) are presentation and not classified here |
| `Replace` | 508 (NPC 506, ability entity or projectile 3) | read | none | `ReplaceInteraction.java:68` both passes run doReplace into their own context (:57,:68); the effect is the replacement chain |
| `Serial` | 132 (NPC 120, host 8, ability entity or projectile 9, ability caster 9) | read | none | `SerialInteraction.java:32` compile flattens the children into the chain; Serial adds no operation of its own |
| `Wielding` | 60 (NPC 60) | read | direct (DamageDataComponent) | `WieldingInteraction.java:142` the server pass sets the current wielding (tick0 :142) and handle clears it (:198, server pass only); simulateTick0 (:177) only tests for the stamina-broken effect |
| `Chaining` | 53 (NPC 53) | read | direct (ChainingInteraction.Data) | `ChainingInteraction.java:153` the simulation pass picks the branch and advances the entity's chain counter (:153); the server pass follows the stored branch (:91). A host has no Data component, so there the simulation pass picks nothing |
| `Charging` | 33 (NPC 32, ability caster 2) | read | none | `ChargingInteraction.java:223` the simulation pass asks the simulation handler (an NPC's returns the requested charge time, NPCInteractionSimulationHandler.java) and the server pass follows (:223,:165) |
| `MovementCondition` | 2 (NPC 2) | read | none | `MovementConditionInteraction.java:112` the simulation pass always chooses the first branch, "no movement" (:112-115), and the server pass follows the stored direction (:84) |
| `UseBlock` | 2 (NPC 2) | read | none | `UseBlockInteraction.java:41` the simulation hook pushes the block's root into its own operation stream without the event (:41); the server hook fires UseBlockEvent and pushes it (:36) |

### Reads only (7)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `StatsCondition` | 62 (NPC 49, ability caster 14) | read | none | `StatsConditionInteraction.java:36` firstRun reads the stat map and sets Failed (:36-47) |
| `EffectCondition` | 42 (NPC 38, ability entity or projectile 4, ability caster 8) | read | none | `EffectConditionInteraction.java:54` firstRun reads the active effects (:54) |
| `DurabilityCondition` | 8 (NPC 8) | read | none | `DurabilityConditionInteraction.java:45` firstRun reads the held item's durability (:45) |
| `Condition` | 6 (NPC 6) | read | none | `ConditionInteraction.java:74` tick0 reads the movement states and sets Finished or Failed (:74) |
| `BlockCondition` | 3 (NPC 3) | read | none | `BlockConditionInteraction.java:60` the simulation hook reads the block and sets the face (:60) |
| `CooldownCondition` | 3 (NPC 3) | read | none | `CooldownConditionInteraction.java:34` firstRun reads the cooldown with hasCooldown(false), which does not deduct (:34-50) |
| `GroundedCondition` | 1 (ability caster 1) | read | none | `GroundedConditionInteraction.java:36` firstRun and simulateFirstRun run the same read (:36,:41) |

### No effect on these managers (1)

| Type | Objects (runs on) | Basis | Write | Deciding line and why |
|------|-------------------|-------|-------|-----------------------|
| `PlaceBlock` | 1 (NPC 1) | read | none | `PlaceBlockInteraction.java:172` the server pass places a block only from the block position the client reported (tick0 :88-92); the simulation pass sets no position (:172-183), so nothing is placed |

### Outcomes that depend on a field (counted over the run-reached objects, then those on a manager with no remote client)

| Type and field | Value (objects) | Outcome |
|----------------|-----------------|---------|
| `ChangeStat` `Behaviour` | absent (63; 51 on such a manager), `Add` (4) | **doubled**: `Add` is the default (`ChangeStatBaseInteraction.java:44`) |
| | `Set` (33), `Min` (14), `Max` (0) | the same result twice (`Set` measured, `Min` and `Max` read) |
| `TriggerCooldown` `Cooldown.Charges` | absent (16; 3 on such a manager) | **the same result twice**: the default is one charge (`InteractionManager.DEFAULT_CHARGE_TIMES`); the 13 others are ability-cast chains on a player's manager |
| | more than one charge (0 shipped) | **doubled**: it uses two |
| `Explode` `Config.DamageEntities` | `true` (10, the default) | the target takes the damage twice |
| `Explode` `Config.DamageBlocks` | `false` (7), `true` (3, the default) | `true`: the blocks take the damage twice (read) |
| `ModifyInventory` `RequiredGameMode` | `Adventure` (14) | **inert on these managers**: no `Player` component, so `firstRun` returns before any write (`ModifyInventoryInteraction.java:97`) |
| `ModifyInventory` (ungated) | `AdjustHeldItemQuantity` -1 (3) | **doubled** with a stack of 2 or more, the same result with a stack of 1 (measured); never trips the item-change check |
| | `ItemToRemove` or `ItemToAdd` (0) | **desync** under a `Server` wait with the owner the running entity (measured in 13a); no shipped object does this |
| `Repeat` `Repeat` | 1 (4), 2 (4), 3 (5), 4 (2), 5 (1), 7 (1), 14 (2), 15 (2), 35 (2), -1 (1) | **guarded**: the fork is made once per round in the server pass, whatever the count (measured for 1) |
| `ApplyForce` `Duration` | absent (22) | **once**: a duration of 0 applies the force on the first simulation tick only |
| `ApplyForce` `ChangeVelocityType` | `Set` (17), `Add` (2), absent (3, `Set` is the default, `ApplyForceInteraction.java:127`) | **once** either way |

### Gotchas

- **Symptom:** an NPC attack changes a stat by twice the authored amount, or an explosion hurts twice → `ChangeStat` with `Behaviour` `Add` (the default, 55 of the 102 shipped objects on such managers) and `Explode` (9 NPC objects, 2 on ability projectiles) run their `firstRun` in both passes. There is no JSON switch. Fix: author the amount for two, prefer `Set`, `Min` or `Max` for a stat, or write the effect as a type of your own that overrides `simulateFirstRun` ([below](#writing-your-own-interaction)).
- **Symptom:** a held stack of throwables is used up two at a time → `ModifyInventory` with `AdjustHeldItemQuantity` -1 removes one in each pass. A stack of 1 loses its one item either way. The shipped `Item_Throw` is one of the 3 ungated objects.
- **Symptom:** an NPC's `ModifyInventory` does nothing, or removes the NPC → with `RequiredGameMode` it returns early (14 of 17 shipped objects, the arrow chains of the bows and crossbows); without it, `ItemToRemove` or `ItemToAdd` under a `Server` wait with the owner the running entity desyncs and removes the entity ([above](#the-item-change-check-and-the-pass-order)). No shipped object does the second.
- **Symptom:** a cooldown loses two charges per use → `TriggerCooldown` with `Charges` of more than one entry deducts in both passes. The default (one charge) is safe, and none of the 19 shipped objects lists `Charges`.
- **Symptom:** `Entity already contains component type` on the world thread, and the world reloads → `AttachBeam` on a manager with no remote client ([beams.md](beams.md#gotchas--errors)). The one shipped object is in the `ProjectileSpawn` chain of the chain-hook ability projectile, which runs on the caster's (a player's) manager, so no shipped chain reaches it that way.
- **Symptom:** a `MovementCondition` on an NPC always takes its first branch → the simulation pass chooses "no movement" (`MovementConditionInteraction.java:112-115`) and the server pass follows it (read).

## The item-change check and the pass order

`Interaction.tickInternal` (`Interaction.java:288-302`) runs in both passes. If the held slot now holds a different item than when the context was built, the pass sets `ItemChanged` and does not call `tick0` or `simulateTick0`. A chain that runs through another entity is exempt (the owner is not the entity). An interaction that puts an item into the held slot of the entity that runs it without telling the context (`ModifyInventory` with `ItemToAdd` does, with the owner the running entity; `AdjustHeldItemQuantity` calls `context.setHeldItem`, keeps the context in step and does not) therefore changes what the **second** pass does, and the outcome depends on which pass that is, because only the server pass throws on `ItemChanged`:

- **The wait is `Server`: the server pass runs first, the simulation pass second. (measured)** The simulation pass sees the changed item and skips its hook, and `Interaction.simulateTick` has no `ItemChanged` case (`:263-286`; `tick` has one, `:256`), so it ends with its operation counter behind. `doTickChain` throws the desync (`:499-505`), and `TickInteractionManagerSystem` catches it and **removes the entity that runs the chain** (`InteractionSystems.java:255`). Measured with `ModifyInventory` (shipped, waits for `Server`): `Counter: 1 vs 0`, entity removed.
- **The wait is `None`: the simulation pass runs first, the server pass second. (measured)** When the simulation pass does the work (the default `simulateFirstRun`, which calls `firstRun`), the server pass sees the changed item, and `Interaction.tick` throws `ChainCancelledException(ItemChanged)` (`:256-258`), which the manager catches and only ends the chain with (`InteractionManager.java:376`). Measured with a plugin subclass of `ModifyInventory` that changes nothing but `getWaitForDataFrom()` to `None`: 1 item, `chain_server_state=ItemChanged`, no desync line, the entity kept. The effect lands once, and the chain ends there: no operation after it runs (read; the measured chain had none after it).
- **The wait is `Client`. (read, not measured)** `doTickChain` runs the simulation pass first for `Client` as for `None` (`:486-492`; only `Server` runs it second), and the client state the simulation pass stores satisfies the server pass's wait, so the reading is the `None` one, with the same precondition: the simulation pass must do the work. Of the 30 block interactions, 22 wait for `Client`, and 19 of those have an empty `simulateInteractWithBlock` (the census, `maintenance/probes/double-run/census-0.7.2.txt`; the other 8 wait for `Server`, the case above, which needs no such precondition). For those 19 the simulation pass changes nothing, the server pass changes the held slot after that operation's check has run, so the effect lands once and that operation is not cancelled (read). The next operation in the chain still meets the check. The same holds under `None` for a type whose `simulateFirstRun` is empty.
- **`"OnItemChangeBehavior": "Ignore"` on a `Server`-wait interaction. (measured)** No exception, and the effect doubled (2 items).
- **What the shipped assets do. (counted, read)** The check trips only when a write changes the item in the slot without telling the context. `ModifyInventory` is the one of the 48 types that writes an inventory slot directly (`usage.py` scans their class chains), and of its 17 run-reached objects 14 are gated by `RequiredGameMode` (inert here) and 3 use `AdjustHeldItemQuantity`, which calls `context.setHeldItem` (`ModifyInventoryInteraction.java:113`) and so never trips it: **no shipped chain an NPC, encounter or ability runs meets the desync**, and no attempt to reproduce one on a real NPC was made. `PlaceBlock` and `PlaceFluid` call `setHeldItem` but write through `BlockPlaceUtils`, and a block interaction's server hook runs once. `EquipItem` and `ChangeActiveSlot` write the slot too, but only an NPC field that names an item reaches them.

Measured on a host; the same code runs for an NPC (read).

## Writing your own interaction

- **Extend `SimpleInstantInteraction`. (read)** Your `firstRun` runs in both passes on a manager with no remote client. (measured with a plugin type that overrides only `firstRun`: two lines.)
- **If the effect must land once, silence the simulation pass. (measured)** Override `simulateFirstRun` with an empty body. A plugin type that did this wrote one line on the same manager. This is what `LaunchProjectile` and `ApplyEffect` do.

  ```java
  @Override
  protected void simulateFirstRun(InteractionType type, InteractionContext context,
                                  CooldownHandler cooldownHandler) {
      // empty: the effect lands once, in the server pass
  }
  ```

- **If the effect sets a value, it is usually safe. (read)** Setting a stat to a value, clearing an effect or raising a flag gives the same result twice (a `ChangeStat` with `Behaviour: Set` and a `ClearEntityEffect` read the same on a manager with no remote client as on a flagged one; measured). Adding to a stat is not that: the default `Behaviour` of `ChangeStat` is `Add`. [The table](#what-each-of-the-48-types-does) classifies the 48 types NPCs and abilities run; for any other type read the body.
- **Or branch on the pass. (measured on the NPC-shaped and the flagged host manager; read for a player's)** `context.getEntry().isUseSimulationState()` is `false` in the server pass, and a player's manager has only that pass, so `if (context.getEntry().isUseSimulationState()) return;` at the top of a hook that both passes reach makes it a server-pass effect. For a `SimpleInstantInteraction` the empty `simulateFirstRun` above says the same thing without a flag. The flag is for code that is shared between the passes, such as a `tick0` you write yourself.
- **Or guard it with the instance store. (read)** `DamageEntity` runs its real work in the simulation pass, stores the result with `context.getInstanceStore().putMetaObject(...)`, and the server pass reads it back. Both passes see the same store.
- **A hand-written `Interaction` must write `simulateTick0`. (read)** It is abstract in `Interaction`. `SimpleInteraction` implements it by calling `tick0`. If you extend `Interaction` directly and call `tick0` from `simulateTick0`, you get the same double run.
- **Changing the held slot from an interaction that runs for its own entity, without calling `context.setHeldItem`, depends on the wait. (measured)** With a `Server` wait, on an NPC-shaped manager, that desyncs and removes the entity. With a `None` wait the effect lands once and the rest of the chain is cancelled as `ItemChanged`, which is not a crash but ends the chain early ([above](#the-item-change-check-and-the-pass-order)). A chain a host or projectile runs for another owner is exempt.
- **Keep both passes on the same path. (read)** The two passes must end on the same operation, or `doTickChain` throws the desync. The item-change case with a `Server` wait is the measured instance.
- **`Server` waits reverse the order. (measured)** If your interaction waits for `Server`, your `firstRun` runs in the server pass first, then in the simulation pass. (read) The default `simulateTick0` copies a `Failed` server result into the simulation state (`context.getServerState()`).
