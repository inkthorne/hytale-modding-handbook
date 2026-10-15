---
title: "World Events"
description: "Hytale's World Event system (0.6.3+) — author stage/fork timelines as JSON assets under Server/WorldEvent, drive them with conditions, actions and context keys, start them from gameplay config, interactions or commands, and extend or observe them from a Java plugin."
seo:
  type: TechArticle
---

# World Events

**Doc type:** Java API + JSON asset format · **Assets:** `Server/WorldEvent` · **Verified against 0.7.2**

New as of 0.6.3. A **world event** is a scripted timeline that runs inside a world: a graph of **stages**, each
offering one or more **forks**; a fork waits on a list of **conditions** (a timer, players entering a radius, a
location being found and a prefab spawned there, a signal from an NPC encounter, another event ending…), then runs
its **actions** (paste/remove a prefab, play effects, show a map marker, message players, start/stop other events)
and hands over to its **next** stage. The whole thing is data: a `WorldEventAsset` JSON plus optional shared
`StageAsset` JSONs. The engine's `WorldEventsPlugin` (`com.hypixel.hytale.builtin.adventure.worldevents`) owns the
runtime; plugins can start events, observe them ending, feed them signals, and register new condition types.

The shipped `Server/WorldEvent/Event/Test_Signal_Complete.json` is the smallest example: a one-stage event that
waits for an encounter signal and prints a message. As of 0.7.2 the game also ships real events built on the system:
`Coffer_Goblin` (find a wilderness location, paste a prefab, wait on an encounter signal or a 30-minute timeout),
`Hunt_Breach` (started by the `PortalsGoblins` gameplay config) and the `Goblin/Goblin_Breach_*` family, whose stages
live in separate files under `Server/WorldEvent/Stage/`. They are the best reference for multi-stage graphs.

## Packages and key classes

| Class | Package (`com.hypixel.hytale.builtin.adventure.worldevents…`) | Role |
|-------|-----------------------------------------------------------------|------|
| `WorldEventsPlugin` | (root) | Registers components/resources/systems/codecs; static registration API for custom conditions |
| `WorldEventsConfig` | (root) | `GameplayConfig` plugin section `"WorldEvents"` — events to auto-start per world |
| `WorldEventsWorldConfig` | (root) | Per-world `WorldConfig` plugin section `"WorldEvents"` — the `EnableWorldEvents` switch |
| `RecurringWorldEventTracker` | (root) | Per-world resource that sends repeating events' countdowns to clients for the map list |
| `WorldEventRecord` | (root) | `(UUID id, String event, boolean isTransient)` record naming an event instance to start |
| `WorldEventManager` | (root) | Per-world `Resource<EntityStore>` — lookup of running events by UUID / asset id |
| `WorldEventStorage` | (root) | Per-world persisted resource — running persistent events + completed UUIDs |
| `GlobalWorldEventManager` | (root) | Universe-level singleton (`INSTANCE`) for **global** events persisted in `events.json` |
| `WorldEventAsset`, `StageAsset` | `.event` | The JSON assets (`Server/WorldEvent/Event`, `Server/WorldEvent/Stage`) |
| `WorldEvent` | `.event` | The **component** (on an entity in the `EntityStore`) that is one running instance |
| `Stage`, `Fork`, `StageId`, `Validator` | `.event` | Built runtime graph and the load-time validator |
| `EventCondition` (+ `Type`, `Config`, `Ticking`, `Event`, `TrackedEvent`) | `.condition` | Condition contract and built-ins |
| `EventAction` | `.action` | Action contract and built-ins |
| `Context`, `ContextKey`, `ContextMap`, `ContextEntry` | `.context` | Typed variables shared between conditions and actions |
| `TrackedEntityComponent`, `TrackedBlockComponent`, `WorldEventSignal`, `EventEndEcsEvent` | `.component` | ECS glue: what an event spawned, signals in, end notification out |
| `ConditionManager`, `ConditionEventHandler` | `.condition.manager`, `.system` | Ticks conditions and routes ECS events to them |
| `EventStartInteraction` … `ModifyIntervalConditionInteraction` | `.interaction` | Item/block interaction types that start/stop events |
| `WorldEventCommand` | `.command` | `/worldevent` and its sub-commands |

---

## Asset format

### `Server/WorldEvent/Event/<Id>.json` — `WorldEventAsset`

```json
{
  "Root": {
    "Forks": [
      {
        "Conditions": [
          { "Type": "SignalCondition", "SignalId": "test_signal_complete" }
        ],
        "Actions": [
          { "Type": "MessageAction", "Message": { "RawText": "[Test] World event completed by encounter signal!" } }
        ]
      }
    ]
  },
  "Persistent": false,
  "IterationCount": 1,
  "PlayerCountMin": 1,
  "InstanceCountMax": 1
}
```

| Key | Type | Default | Meaning (from the codec documentation strings) |
|-----|------|---------|------------------------------------------------|
| `Root` | stage id **or** inline stage | `"Unknown"` | The starting stage. The codec is `StageAsset.REF_CODEC` (a `ContainedAssetCodec`), so this is `anyOf(id, inline definition)` — either the id of a `Server/WorldEvent/Stage` asset, or a stage object written inline as in the example above, which is registered as a contained asset under a generated id. Omitting the key entirely fails validation with `Missing root stage: Unknown` |
| `Persistent` | bool | **`true`** | Persist the running event with the world and resume it after a server restart. Note the default: omit the key and the event *is* persisted (the shipped example sets `false` explicitly, which makes `false` look like the default) |
| `IterationCount` | int | `-1` | How many times the event repeats; `-1` (`WorldEvent.INFINITE_ITERATIONS`) = forever. Codec accepts `>= -1`, but `0` makes the asset permanently unstartable (see gotchas) |
| `PlayerCountMin` | int | `1` | Minimum non-spectator players in the world for the event to tick. Codec accepts `>= 0`, and the value is used unclamped — `0` means it runs in an empty world |
| `InstanceCountMax` | int | `-1` | Maximum simultaneous instances of this asset; `-1` (`WorldEvent.INFINITE_INSTANCES`) = unlimited. Enforced at start |
| `RetryLimit` | int | `5` | "The number of times this event may retry after failing. Set to -1 to retry indefinitely." Codec accepts `>= -1`; `WorldEvent.DEFAULT_RETRY_LIMIT` / `WorldEvent.INFINITE_RETRIES`. See *Runtime model* |
| `Name` | string | — | "Translation key of the player-facing event name. Shown on the map while the event waits at an interval marked ShowOnMap." |
| `Icon` | string | — | "Common asset path of the event icon. Shown next to the name on the map." (the shipped breach events use `UI/WorldMap/MapMarkers/GoblinBreach.png`) |

`RetryLimit`, `Name` and `Icon` are new in 0.7.2. `RetryLimit` replaces the fixed five-failure threshold that earlier
builds hard-coded as `FAIL_COUNT_THRESHOLD` (removed in 0.7.2, along with the `failCount` field that is now `retryCount`).

The asset store is registered at path `WorldEvent/Event`, keyed by file name; `WorldEventAsset.ASSET_MAP` /
`WorldEventAsset.getAssetOrUnknown(id)` look assets up, and `WorldEventAsset.build(UUID, boolean transient)` produces
the `WorldEvent` component for a new instance.

`WorldEventAsset.valid()` runs `Validator` over the asset and memoizes the verdict. The validator walks the whole
reachable stage graph and fails on: a `Root` or `Next` id with no matching `StageAsset` (`Missing root stage: %s` /
`Missing stage: %s`), a condition or action whose own `validate(...)` objected (`Invalid condition: %s` /
`Invalid action: %s`), a context key that is *referenced* anywhere but *defined* nowhere
(`Referenced name '%s' has not been defined`), and a **cyclic** stage graph
(`Cyclic stage graph reachable from root stage: %s`). An asset that fails is refused by every start path.

### `Server/WorldEvent/Stage/<Id>.json` — `StageAsset`

A stage is "a step in a world-event's timeline. May consist of multiple different forks that are taken depending on
their conditions." A stage can be written inline at `Root` / `Next` (as the reference asset above does), or split
into its own file under `Server/WorldEvent/Stage/` and referenced by id — useful when several events share a stage:

```json
{
  "Forks": [
    {
      "Conditions": [ { "Type": "IntervalCondition", "IntervalKey": "warmup", "MinSeconds": 30, "MaxSeconds": 60 } ],
      "Actions":    [ { "Type": "None" } ],
      "Next": "MyEvent_Stage2"
    }
  ]
}
```

| Fork key | Meaning |
|----------|---------|
| `Conditions` | Array of condition objects that must **all** complete for the fork to complete |
| `Actions` | Array of action objects run once the fork completes |
| `Next` | The next stage — like `Root`, `StageAsset.REF_CODEC`, so either a `StageAsset` id or an inline stage object. Omit on a terminal fork; the iteration then ends (see *Runtime model* — that is not necessarily the end of the event) |
| `Mode` | 0.7.2+. "How the event proceeds once this fork has completed": `Continue` (default — go to `Next`, or end the iteration when there is none), `Complete` ("Ends and removes the event as having completed successfully"), or `Restart` ("Restarts the event from its root stage. This mode does not consume the event's retry or repeat budget"). A fork with `Next` must leave `Mode` at `Continue`; anything else fails validation with `Fork cannot have a 'Next' stage when set to 'Mode': %s. (Requires: %s)` |

"Whichever fork's conditions complete first will be selected to run its actions and 'next' stage" — forks are
alternatives, evaluated concurrently; the losing forks' conditions are cancelled.

Enum values are written in camel case in JSON (`"Mode": "Complete"`, as in the shipped
`Goblin_Breach_First_Stage5.json`): the `EnumCodec` matches the camel-cased key exactly, so `"COMPLETE"` fails to
decode. The same applies to every enum on this page.

> **Shipped stage files.** 0.7.2 ships its first standalone stages under `Server/WorldEvent/Stage/` — `Hunt_Breach_Stage1`–`3`,
> `Goblin/Coffer/Coffer_Goblin_Cleanup` and the `Goblin/Breach/…` chains. The example above is constructed from the
> codec; the shipped files are referenced by id from their events' `Root` exactly as shown.

---

## Conditions

Every condition object carries `"Type"` (the registered id) plus its own keys. Built-ins registered by
`WorldEventsPlugin.setup()`:

| `Type` | Keys | Completes when |
|--------|------|----------------|
| `None` | — | Immediately |
| `IntervalCondition` | `IntervalKey` (context key), `MinSeconds`, `MaxSeconds`, `ShowOnMap`, `MapIntervalKey`, `RemainingSeconds` (runtime/persisted) | A random duration in `[Min, Max]` has elapsed. Publishes an `IntervalContext` under `IntervalKey` so a `ModifyIntervalConditionInteraction` can shorten/extend it. `ShowOnMap` (0.7.2+) lists the event on the client's map with this interval as the countdown — "Set it on the interval that waits for the next occurrence"; `MapIntervalKey` is the translation key of that countdown text (it takes a `time` parameter; generic text when unset). The listing is only sent for a repeating event (`IterationCount: -1`, or more than one iteration left), using the asset's `Name` and `Icon` |
| `TimeCondition` | `Day`, `Hour` (0–23), `Minute` (0–59), each `-1` (the default) to ignore; `Complete` (runtime/persisted) | 0.7.2+. The world's game time is at or past the target, compared day, then hour, then minute. `Day` counts days since the world started (the first day is day 0); without a `Day` the target is a time of day, so the condition can complete again each day when its stage repeats. It latches once complete. All three unset fails validation (`TimeCondition unconditionally completes immediately`) |
| `LocationCondition` | `LocationKey`, `LocationType` (an `EventLocation`; see *Registered by other plugins* below), `Content` (array of spawners), `Clearance` (open blocks required above a candidate surface), `SearchRadius` | A valid location was found and the `Content` spawners placed there; publishes a `LocationContext` (`Location`, `Rotation`) under `LocationKey` |
| `ProximityCondition` | `LocationKey`, `Radius`, `Invert` | One or more players are within `Radius` of the location stored under `LocationKey` (`Invert`: completes once **no** player is within it) |
| `WorldClosedCondition` | `WorldKey` | The world stored under `WorldKey` (a `WorldContext`) is closed or unloaded — the condition tests `world != null && world.isAlive()` on start and every `0.1s`. 0.7.2 removed the `LoadTimeoutSeconds` key and its grace period, so a world that has not finished loading when the condition starts counts as closed |
| `EventEndCondition` | `EventKey`, `EndMode` (`Iteration` \| `Termination`), `Result` (`Pending` \| `Complete` \| `Failed`; runtime/persisted) | The child event stored under `EventKey` (an `EventContext`) ends. `Iteration`: "whenever the referenced event reaches the end of an iteration, including its final one". `Termination`: "when the referenced event terminates, either after its final iteration or through a fork with 'Mode': Complete". A child that ends with `Reason.FAIL` fails the condition in either mode |
| `SignalCondition` | `SignalId` | A `WorldEventSignal` ECS event with a matching `signalId` is received — "for example from an encounter's `SignalWorldEvent` action" (see [Encounters](encounters.md)) |

### Registered by other plugins

Other built-in plugins add types to the same codecs, and the shipped events use them:

| Kind | `Type` | Registered by | Keys |
|------|--------|---------------|------|
| Condition | `GameFlagLevelCondition` (0.7.2+) | `GameFlagsPlugin` | `Flag`, `Level`, `Comparator` (e.g. `"LessOrEqual"`, `"GreaterThan"`); `Result` (runtime/persisted) |
| Condition | `EnterPortalCondition` | `PortalsPlugin` | `WorldKey` |
| Condition | `EnterInstanceTeleporterCondition` (0.7.2+) | `InstancesPlugin` | `WorldKey`; `State`, `WorldUUID` (runtime/persisted) |
| Location | `None` | `WorldEventsPlugin` | — (the default; finds nothing on its own) |
| Location | `WildernessLocation` | `WildernessPlugin` | `MinHorizontalDistance`, `MaxHorizontalDistance`, `MinVerticalDistance`, `MaxVerticalDistance` — "random wilderness positions nearby a player"; the location the shipped events use |
| Location | `BiomeLocationV1` | `WorldGenPlugin` | `Location` (another `EventLocation`), `Rules` (`Zone`, `Biomes`) — filters another location to world-gen-v1 biomes |
| Action | `TriggerVolumeCreateAction`, `TriggerVolumeRemoveAction` | `TriggerVolumesPlugin` | see [Trigger Volumes](trigger-volumes.md) |

### Spawners (`LocationCondition.Content[]`)

| `Type` | Keys |
|--------|------|
| `NoSpawner` | — |
| `PrefabSpawner` | `PrefabKey` (context key the pasted prefab is published under, for a later `PrefabRemoveAction`), `Prefab` (one or more prefab asset ids — one is chosen at random), `Rotations` (candidate rotations, one chosen at random), `MaxHeightDelta` (maximum terrain height difference across the footprint), `Mask` (a `PlacementMask` — `Type` (`BlocksAndFluids` \| `BlocksOnly` \| `FluidsOnly`), `Blocks` and `Fluids` (arrays of `BlockTypeList` asset ids) — that the prefab may be placed onto; omit for any — `PlacementMask.DEFAULT_ANY`) |

`WorldEventsConfig.ExclusionRadius` (default `512`, `DEFAULT_EXCLUSION_RADIUS`) is "the minimum distance that a
world-event location must be from other world-event locations" — location search rejects candidates closer than
that to another event's location; `0` disables the filter.

---

## Actions

| `Type` | Keys | Effect |
|--------|------|--------|
| `None` | — | No-op |
| `EffectsAction` | `LocationKey`, `Radius`, `Shape` (`{"Type": "Point", "Count", "OffsetMin", "OffsetMax"}` or `{"Type": "Ring", "Radius", "Count", "OffsetMin", "OffsetMax"}`), `CameraFX` (`Effect`, `IntensityMin/Max`), `SoundFX` (`Effect`, `MinVolumeDb`/`MaxVolumeDb` in decibels, `-100`–`0`, and `MinPitchSemitones`/`MaxPitchSemitones`, `-60`–`12`), `VisualFX` (`Effect`, `Color`, `ScaleMin/Max`, `Offset`, `DurationMin/Max`) | Collects players within `Radius` of the location and sends camera shake / sound / particle effects at points generated by `Shape`. 0.7.2 moved `SoundFX` to decibels and semitones; the old linear `VolumeMin/Max` and `PitchMin/Max` keys still load but are marked deprecated, and a min/max pair only randomises when both bounds are set |
| `EventStartAction` | `Event` (a `WorldEventRecord`: `Id`, `Event`, `Transient`), `EventKey`, `Detach` | Starts a child event and publishes an `EventContext` under `EventKey`; unless `Detach` is true the child is terminated when the parent ends |
| `EventStopAction` | `EventKey` | Stops the child event stored under `EventKey` |
| `GlobalEventStartAction` / `GlobalEventStopAction` | `Id` (UUID), `Fail` (treat "already running / not running" as a failure) | Start/stop a **global** event via `GlobalWorldEventManager` |
| `MapMarkerOverrideAddAction` | `MarkerKey`, `Name`, `Icon`, `DisplayName`, `Global` | Overrides the world-map marker named `Name`: `Icon` replaces its icon, `DisplayName` (0.7.2+) its name with a localization key, `Global` = show to all players rather than only those within view distance. Publishes a `MapMarkerOverrideContext` under `MarkerKey` |
| `MapMarkerOverrideRemoveAction` | `MarkerKey` | Removes that marker |
| `MessageAction` | `Message` (a `Message` JSON, e.g. `{"RawText": "…"}`) | Broadcasts to the world |
| `PrefabPasteAction` | `PrefabKey`, `Permanent` | Pastes the prefab chosen by the spawner under `PrefabKey`; if `Permanent` is false "the prefab and its entities will be removed and the world rolled back to its previous state when the event ends" (the snapshot is a `PrefabRemoveContext`) |
| `PrefabRemoveAction` | `PrefabKey` | Removes a pasted prefab now |
| `ShowEventTitleAction` | `LocationKey` (required), `PrimaryTitle` (required), `Radius`, `SecondaryTitle`, `Style`, `Icon`, `Duration` (`4.0`), `FadeInDuration` / `FadeOutDuration` (`1.5`), `SoundFX`, `CameraFX` | 0.7.2+. Shows an event title to players within `Radius` of the location; both titles are translation keys. The class is `@Deprecated(forRemoval=true)` in the same build that adds it, so expect it to go |

An action returning `false` from `apply(...)` fails the fork (see *Runtime* below).

---

## Context keys

Conditions **define** typed variables and actions **reference** them; both sides name them with a plain string
(`"IntervalKey": "warmup"`, `"LocationKey": "site"`). `Validator` checks that every referenced key is defined
*somewhere* in the reachable graph, so a typo fails the asset — but it is a plain set-membership test with **no
ordering or reachability-position check**, so referencing a key that is only defined by a *later* stage passes
validation and fails at runtime instead (see gotchas). At runtime the values live in `WorldEvent.context`, a
`ContextMap` keyed by `ContextKey` **and** context class:

| Context `Type` | Produced by | Payload keys (persisted) |
|----------------|-------------|---------------------------|
| `IntervalContext` | `IntervalCondition` | (timer state) |
| `LocationContext` | `LocationCondition` | `Location` (`Vector3i`), `Rotation` (`Rotation3f`) |
| `EventContext` | `EventStartAction` | `EventId`, `Detach` |
| `MapMarkerOverrideContext` | `MapMarkerOverrideAddAction` | `Name`, `Override` |
| `PrefabPasteContext` | `PrefabSpawner` / paste | `Path`, `Origin`, `Rotation` |
| `PrefabRemoveContext` | `PrefabPasteAction` (non-permanent) | `Key`, `Prefab`, `Origin`, `Rotation`, `Snapshot` |
| `WorldContext` | (world-scoped events) | `World` |

```java
ContextKey key = ContextKey.of("site");
LocationContext loc = event.context.get(key, LocationContext.class);   // null if not (yet) defined
boolean has = event.context.has(key, LocationContext.class);
```

Each `Context` gets `cleanup(CommandBuffer, WorldEvent)` when the event ends or resets — that is how a
non-permanent prefab is rolled back and a map marker removed.

---

## Runtime model

- A running instance is an **entity** in the world's `EntityStore` carrying the `WorldEvent` component
  (`WorldEvent.getComponentType()`, codec id `"WorldEvent"`). It is registered in the per-world `WorldEventManager`
  resource and, if the asset is `Persistent`, saved through the `WorldEventStorage` resource (`"WorldEventStorage"`;
  instances ship a `resources/WorldEventStorage.json` with `Active` / `Complete` arrays).
- `WorldEventTickSystem` visits every `WorldEvent` and advances it every `WorldEvent.TICK_INTERVAL_SECONDS`
  (`0.25f`), skipping the event while the world's non-spectator player count is below `requiredPlayerCount`.
  When a stage is entered it submits the forks' conditions to the `ConditionManager` (`onStart`); afterwards
  it picks the first fork whose conditions all `test()` true, cancels the other forks' conditions, runs
  `onComplete` + `reset` on the winning conditions, applies the actions in order, then proceeds by the fork's
  `Mode` (`WorldEventTickSystem.handleNextStage`). A `Next` stage is initialised in the same tick; a restart at the
  root waits for the next tick.
- **Failure:** if any condition's `onStart` (during stage init), any winning condition's `onComplete`, or any action
  returns `false`, the event resets to its root stage and clears its context, counting a retry in
  `WorldEvent.retryCount`. Once the count exceeds the asset's `RetryLimit` (default `5`, so the sixth failure) it
  fires `EventEndEcsEvent(event, Reason.FAIL)` and removes the entity; `RetryLimit: -1` retries forever. The count
  resets to `0` at the end of each successful iteration.
- **Iteration end — and note it does not mean "over".** A `Continue` fork with no `Next` ends the *iteration*.
  While the event still has iterations left (`repeatCount == -1`, or `--repeatCount > 0`) it resets to the root
  stage, clears its context, fires `EventEndEcsEvent(event, Reason.ITERATION)` and keeps running — so a listener on
  an `IterationCount: -1` event sees `ITERATION` on every lap, and the event is never stored or removed.
- **Success.** When the iterations are exhausted, or a fork with `"Mode": "Complete"` wins, the event fires
  `EventEndEcsEvent(event, Reason.SUCCESS)`, adds a non-transient event's UUID to `WorldEventStorage`
  (`isComplete(uuid)`), and removes the entity. A `"Mode": "Restart"` fork goes back to the root without touching
  the iteration or retry counts. (`Reason.ITERATION` is new in 0.7.2; earlier builds fired `SUCCESS` on every lap.)
- Conditions are ticked by `ConditionManager.tick(dt, store)` for `EventCondition.Ticking` types, and ECS events are
  routed by `ConditionManager.handle(world, event)` (for conditions registered with a `ConditionEventHandler`) —
  that is how `SignalCondition` hears `WorldEventSignal` and `EventEndCondition` hears `EventEndEcsEvent`.
- Entities and blocks an event creates are stamped with `TrackedEntityComponent` (`EntityStore`, codec id
  `"EventTrackedEntity"`) / `TrackedBlockComponent` (`ChunkStore`, `"EventTrackedBlock"`), each holding the
  event `UUID` and the `ContextKey` it belongs to — `ConditionManager.handle(world, event, trackedComponent)`
  delivers ECS events on those to `EventCondition.TrackedEvent` conditions.

---

## Starting and stopping events

### From gameplay config (`Server/GameplayConfigs/*.json`)

```json
"WorldEvents": {
  "ExclusionRadius": 512,
  "Events": [
    { "Id": "8d1e0d3e-6f0a-4c1e-9a5f-0b8c7d6e5f4a", "Event": "MyEvent", "Transient": false }
  ],
  "GlobalEvents": []
}
```

`Events` are started when the world loads (`WorldEventsPlugin.loadGameplayWorldEvents(world)` → one
`EventStartAction.startEvent` per record); `GlobalEvents` are registered with `GlobalWorldEventManager` and run
"when triggered by an action in-game such as an interaction". A record's `Transient: true` means "the event is not
recorded after completion, allowing it to run again in future". As of 0.7.2, `Default.json` starts the
`Goblin_Breach_Prelude_Bootstrap` event and registers three global breach events, and `PortalsGoblins.json` starts
`Hunt_Breach` with an `ExclusionRadius` of `48`; the other shipped gameplay configs carry an empty `WorldEvents`
block.

### Turning events off for one world

0.7.2 adds a per-world switch in the world's own config (`WorldEventsWorldConfig`, registered on
`WorldConfig.PLUGIN_CODEC` under the same `"WorldEvents"` id):

```json
"Plugin": { "WorldEvents": { "EnableWorldEvents": false } }
```

"When false, no gameplay or global world events start and running events are cancelled." It defaults to `true`.
`loadGameplayWorldEvents(world)` returns early for a disabled world, and `WorldEventsPlugin.stopAllWorldEvents(world)`
removes every running event entity. `/worldevent enable [enable]` toggles the switch for the current world and saves
the world config.

### Global events (`GlobalWorldEventManager`)

`GlobalWorldEventManager` persists active global event UUIDs in `events.json` (`FILENAME`). Mind the split:

```java
// static — the control API
GlobalWorldEventManager.startEvent(id);
GlobalWorldEventManager.stopEvent(id);
GlobalWorldEventManager.scheduleStartEventInAllWorlds(id);
GlobalWorldEventManager.scheduleRestartEventInAllWorlds(id);

// instance — state, via the singleton
GlobalWorldEventManager.INSTANCE.contains(id);
GlobalWorldEventManager.INSTANCE.activeCount();
GlobalWorldEventManager.INSTANCE.activeIds();
```

(`add`, `remove`, `clear`, `start`, `loadAsync`, `saveAsync`, `startup` and `shutdown` are likewise instance
methods.) It is loaded asynchronously in `WorldEventsPlugin.start()`; a failure logs `Failed to load events.json`.

### From interactions

Registered on the `Interaction` codec, so they can be used anywhere an interaction chain runs (item use, block use,
trigger volumes):

| Interaction `Type` | Keys |
|--------------------|------|
| `EventStartInteraction` | `Event` (a `WorldEventRecord`) |
| `EventStopInteraction` | `Event` (UUID) |
| `GlobalEventStartInteraction` / `GlobalEventStopInteraction` | `Id` (UUID) |
| `ModifyIntervalConditionInteraction` | `Event`, `IntervalKey`, `Modifier` — adjust a running `IntervalCondition`'s remaining time |

### From commands

`/worldevent` (`WorldEventCommand`) with sub-commands `start asset <asset>` (a `WorldEventAsset` id) /
`start global <event-id> [--restart]`, `cancel asset <asset>` / `cancel uuid <uuid>` / `cancel global …`, `list`,
`enable [enable]` (0.7.2+, the per-world switch above), `reset` (stops every event in the world, clears the manager
and storage, then reloads the gameplay-config events) and `panel` (the in-game inspector UI backed by
`WorldEventPanelPage` and friends in `.ui`).

### From Java

```java
Store<EntityStore> store = world.getEntityStore().getStore();
WorldEventManager manager = store.getResource(WorldEventManager.getResourceType());
WorldEvent running = manager.get(uuid);                       // null if not running
ReferenceSet<WorldEvent> all = manager.allOf("MyEvent");      // every instance of an asset

WorldEventStorage storage = store.getResource(WorldEventStorage.getResourceType());
boolean done = storage.isComplete(uuid);                      // completed non-transient events
```

`WorldEventsPlugin.get()` exposes the component/resource types (`getWorldEventComponentType()`,
`getWorldEventManagerResourceType()`, `getWorldEventStorageResourceType()`, `getConditionManagerResourceType()`,
`getRecurringWorldEventTrackerResourceType()`, `getTrackedEntityComponentType()`, `getTrackedBlockComponentType()`). Start an event from a plugin the same way the
config path does — build a `WorldEventRecord` and call `EventStartAction.startEvent(store, record)` on the world
thread.

---

## Observing and driving events from a plugin

**Ending:** `EventEndEcsEvent` is an `EcsEvent` invoked on the event entity; `getWorldEvent()` gives the instance
and `getReason()` is `ITERATION` (one lap of a repeating event ended), `SUCCESS` (the event is over) or `FAIL`. Handle it with an `EntityEventSystem<EntityStore, EventEndEcsEvent>`
registered on the entity store (see [Events → ECS events](events.md)).

**Signalling:** any system can complete a `SignalCondition` by invoking `WorldEventSignal` on an entity:

```java
store.invoke(ref, new WorldEventSignal(null, "test_signal_complete"));   // eventId null = any event listening
```

This is exactly what the encounter-manager's `SignalWorldEvent` NPC action does (`ActionSignalWorldEvent`).

**Custom conditions:** implement `EventCondition` (`test()`, `reset()`, optional `onStart` / `onComplete` /
`onCancel` / `merge`), add `EventCondition.Ticking` for a per-tick `tick(float, Store<EntityStore>)`, give it a
`Config` with a `BuilderCodec`, and register in your plugin's `setup()`:

```java
// Type id is the JSON "Type"; tickIntervalSeconds throttles Ticking conditions (nonTicking(...) for event-driven ones)
EventCondition.Type MY_TYPE = new EventCondition.Type("MyCondition", 0.5f);
WorldEventsPlugin.registerCondition(this, MY_TYPE, MyCondition.CODEC, MyCondition.Config.CODEC);
// Event-driven: also supply a ConditionEventHandler so ConditionManager routes the ECS event to it
WorldEventsPlugin.registerEntityStoreEventCondition(this, MY_TYPE, MyCondition.CODEC, MyCondition.Config.CODEC, new MyHandler());
```

`registerChunkStoreEventCondition` is the `ChunkStore` twin (block-side events). Custom **actions** and
**contexts** are registered on the plain codec-map codecs — `EventAction.TYPE_CODEC` and `Context.TYPE_CODEC`
via `getCodecRegistry(...)`, exactly as the built-ins are in `WorldEventsPlugin.setup()`.

---

## Gotchas

- **Validation is lazy, not load-time.** `valid()` only runs `Validator` the first time it is called, and the first
  call happens when something tries to *start* the event. A broken asset therefore loads silently and only warns
  (`WorldEventAsset is invalid: %s`) at first use — then the start path refuses it
  (`Refusing to start invalid world-event asset: %s`, `Cannot build world-event asset that failed validation: %s`,
  or `Removed world-event for invalid asset: %s` from the init system). A missing asset id is a separate,
  earlier message: `Failed to create world-event. Could not find asset: %s`.
- **Key definition is order-insensitive.** `Validator` only checks that a referenced context key is defined
  *somewhere* reachable. An action in stage 1 referencing a `LocationKey` that a `LocationCondition` in stage 2
  defines **passes** validation, then fails at runtime with a null from `ContextMap.get`. Order your stages so a
  key is genuinely produced before it is consumed — nothing checks it for you.
- **Stages cannot loop.** A cycle in the stage graph is rejected (`Cyclic stage graph reachable from root stage`);
  repetition is expressed with `IterationCount` or a `"Mode": "Restart"` fork, not by pointing `Next` back at an
  earlier stage.
- **`"IterationCount": 0` is a silent brick.** The codec accepts it (`>= -1`), but `valid()` is
  `state == VALID && iterationCount != 0`, so the asset can never start and reports only the generic refusal.
- **Retries run out.** Actions and `onComplete` returning `false` reset the event; with the default `RetryLimit` of
  `5` the sixth failure in one iteration removes the entity with `Reason.FAIL`. Each failure is logged as
  `World-Event failed at stage: %d. Error: %s. Resetting event. Fail count: %d`, and the last as
  `… Removing event entity`.
- **Ticks are quarter-second.** Conditions are not evaluated faster than every `0.25s`, and not at all while the
  world has fewer non-spectator players than `PlayerCountMin`.
- **Non-permanent prefabs are rolled back.** With `"Permanent": false` the pasted blocks and any entities are
  restored from the snapshot when the event ends, so don't leave player-facing state inside them.
- **Global vs world events persist differently.** World events live in the world's `WorldEventStorage`; global
  ones in the universe `events.json`. Transient records are never marked complete.

> **See also:** [Encounters](encounters.md) (NPC-side `SignalWorldEvent`), [Trigger Volumes](trigger-volumes.md),
> [Interactions](interactions.md), [Prefabs](prefabs.md), [Events](events.md).
