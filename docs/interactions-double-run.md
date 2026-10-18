---
title: "Managers with no remote client: the double run"
description: "What an interaction's work does on an InteractionManager with no remote client (an NPC's, a host entity's, an ability entity's): the simulation and server passes both run, which interaction types land once, twice or throw, and how the pass order and the item-change check decide it. Measured headless."
seo:
  type: TechArticle
---

# Managers with no remote client: the double run

**Doc type:** Java API + JSON asset format · **Verified against 0.7.2**

> **See also:** [Interactions API](interactions.md) for the `Interaction` base class and `SimpleInstantInteraction`, [Operation System](interactions-operations.md) for `simulateTick()` and `tick()`.

Each statement below carries a label. **(read)** means read in the decompiled 0.7.2 source. **(measured)** means measured in a headless run of the probes in `maintenance/probes/double-run/`: a host entity, a flagged host and a real `Chicken`, no player. Line numbers are those of the decompiled source.

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

That a type runs its hook twice does not say its effect doubles. A condition reads and jumps. A flag setter sets a value. The effect of most of these 70 names (the 56, the 2 that run `tick0` again and the 12 that wrap it) has **not been classified**. Three have been measured (below). The census also does not read what a "body of their own" does.

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

`ChangeStatWithModifier` passes the same `Behaviour` field to `processStatChanges` (`ChangeStatWithModifierInteraction.java:66`), so the rows apply to it too (read). The shipped assets use both kinds: of the 206 objects with `"Type": "ChangeStat"` in `Server/` of the extracted `Assets.zip` (every `.json` file that parses, found at any depth; the 6,030 files that do not are under `World/` and `Prefabs/`, and none names `ChangeStat`), 98 have no `Behaviour` and 5 say `Add`, so 103 add and double; 89 say `Set` and 14 say `Min`, so 103 do not (none says `Max`). **(counted)**

The same results came out on a real `Chicken` run headless (no player) in a ticking section, on its own manager, for `ProbeLog` (two lines, simulation then server), `ChangeStat` (+10), `DamageEntity` (one hit on a `Sheep`, one `Damage` event) and `AttachBeam` (refused). The host agreed with the real NPC in all four.

## The item-change check and the pass order

`Interaction.tickInternal` (`Interaction.java:288-302`) runs in both passes. If the held slot now holds a different item than when the context was built, the pass sets `ItemChanged` and does not call `tick0` or `simulateTick0`. A chain that runs through another entity is exempt (the owner is not the entity). An interaction that puts an item into the held slot of the entity that runs it (`ModifyInventory` does, with the owner the running entity) therefore changes what the **second** pass does, and the outcome depends on which pass that is, because only the server pass throws on `ItemChanged`:

- **The wait is `Server`: the server pass runs first, the simulation pass second. (measured)** The simulation pass sees the changed item and skips its hook, and `Interaction.simulateTick` has no `ItemChanged` case (`:263-286`; `tick` has one, `:256`), so it ends with its operation counter behind. `doTickChain` throws the desync (`:499-505`), and `TickInteractionManagerSystem` catches it and **removes the entity that runs the chain** (`InteractionSystems.java:255`). Measured with `ModifyInventory` (shipped, waits for `Server`): `Counter: 1 vs 0`, entity removed.
- **The wait is `None`: the simulation pass runs first, the server pass second. (measured)** When the simulation pass does the work (the default `simulateFirstRun`, which calls `firstRun`), the server pass sees the changed item, and `Interaction.tick` throws `ChainCancelledException(ItemChanged)` (`:256-258`), which the manager catches and only ends the chain with (`InteractionManager.java:376`). Measured with a plugin subclass of `ModifyInventory` that changes nothing but `getWaitForDataFrom()` to `None`: 1 item, `chain_server_state=ItemChanged`, no desync line, the entity kept. The effect lands once, and the chain ends there: no operation after it runs (read; the measured chain had none after it).
- **The wait is `Client`. (read, not measured)** `doTickChain` runs the simulation pass first for `Client` as for `None` (`:486-492`; only `Server` runs it second), and the client state the simulation pass stores satisfies the server pass's wait, so the reading is the `None` one, with the same precondition: the simulation pass must do the work. Of the 30 block interactions, 22 wait for `Client`, and 19 of those have an empty `simulateInteractWithBlock` (the census, `maintenance/probes/double-run/census-0.7.2.txt`; the other 8 wait for `Server`, the case above, which needs no such precondition). For those 19 the simulation pass changes nothing, the server pass changes the held slot after that operation's check has run, so the effect lands once and that operation is not cancelled (read). The next operation in the chain still meets the check. The same holds under `None` for a type whose `simulateFirstRun` is empty.
- **`"OnItemChangeBehavior": "Ignore"` on a `Server`-wait interaction. (measured)** No exception, and the effect doubled (2 items).

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

- **If the effect sets a value, it is usually safe. (read)** Setting a stat to a value, clearing an effect or raising a flag gives the same result twice (a `ChangeStat` with `Behaviour: Set` read the same on a manager with no remote client as on a flagged one; measured). Adding to a stat is not that: the default `Behaviour` of `ChangeStat` is `Add`. Read the body before you rely on it: this page has classified only the types measured above.
- **Or branch on the pass. (measured on the NPC-shaped and the flagged host manager; read for a player's)** `context.getEntry().isUseSimulationState()` is `false` in the server pass, and a player's manager has only that pass, so `if (context.getEntry().isUseSimulationState()) return;` at the top of a hook that both passes reach makes it a server-pass effect. For a `SimpleInstantInteraction` the empty `simulateFirstRun` above says the same thing without a flag. The flag is for code that is shared between the passes, such as a `tick0` you write yourself.
- **Or guard it with the instance store. (read)** `DamageEntity` runs its real work in the simulation pass, stores the result with `context.getInstanceStore().putMetaObject(...)`, and the server pass reads it back. Both passes see the same store.
- **A hand-written `Interaction` must write `simulateTick0`. (read)** It is abstract in `Interaction`. `SimpleInteraction` implements it by calling `tick0`. If you extend `Interaction` directly and call `tick0` from `simulateTick0`, you get the same double run.
- **Changing the held slot from an interaction that runs for its own entity depends on the wait. (measured)** With a `Server` wait, on an NPC-shaped manager, that desyncs and removes the entity. With a `None` wait the effect lands once and the rest of the chain is cancelled as `ItemChanged`, which is not a crash but ends the chain early ([above](#the-item-change-check-and-the-pass-order)). A chain a host or projectile runs for another owner is exempt.
- **Keep both passes on the same path. (read)** The two passes must end on the same operation, or `doTickChain` throws the desync. The item-change case with a `Server` wait is the measured instance.
- **`Server` waits reverse the order. (measured)** If your interaction waits for `Server`, your `firstRun` runs in the server pass first, then in the simulation pass. (read) The default `simulateTick0` copies a `Failed` server result into the simulation state (`context.getServerState()`).
