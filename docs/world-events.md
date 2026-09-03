---
title: "World Events"
description: "Hytale's World Event system (0.6.3+) — author stage/fork timelines as JSON assets under Server/WorldEvent, drive them with conditions, actions and context keys, start them from gameplay config, interactions or commands, and extend or observe them from a Java plugin."
seo:
  type: TechArticle
---

# World Events

**Doc type:** Java API + JSON asset format · **Assets:** `Server/WorldEvent` · **Verified against 0.6.3**

New as of 0.6.3. A **world event** is a scripted timeline that runs inside a world: a graph of **stages**, each
offering one or more **forks**; a fork waits on a list of **conditions** (a timer, players entering a radius, a
location being found and a prefab spawned there, a signal from an NPC encounter, another event ending…), then runs
its **actions** (paste/remove a prefab, play effects, show a map marker, message players, start/stop other events)
and hands over to its **next** stage. The whole thing is data: a `WorldEventAsset` JSON plus optional shared
`StageAsset` JSONs. The engine's `WorldEventsPlugin` (`com.hypixel.hytale.builtin.adventure.worldevents`) owns the
runtime; plugins can start events, observe them ending, feed them signals, and register new condition types.

The shipped `Server/WorldEvent/Event/Test_Signal_Complete.json` is the reference example: a one-stage event that
waits for an encounter signal and prints a message.

## Packages and key classes

| Class | Package (`com.hypixel.hytale.builtin.adventure.worldevents…`) | Role |
|-------|-----------------------------------------------------------------|------|
| `WorldEventsPlugin` | (root) | Registers components/resources/systems/codecs; static registration API for custom conditions |
| `WorldEventsConfig` | (root) | `GameplayConfig` plugin section `"WorldEvents"` — events to auto-start per world |
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

| Key | Type | Meaning (from the codec documentation strings) |
|-----|------|------------------------------------------------|
| `Root` | stage | The starting stage — either an inline stage object (`Forks`) or the id of a `Server/WorldEvent/Stage` asset. Resolved with `StageAsset.getAssetOrUnknown(root)` at build time, so an unknown id degrades to the `"Unknown"` stage rather than failing |
| `Persistent` | bool | Persist the running event with the world and resume it after a server restart |
| `IterationCount` | int | How many times the event repeats; `-1` (`WorldEvent.INFINITE_ITERATIONS`) = forever |
| `PlayerCountMin` | int | Minimum non-spectator players in the world for the event to tick (floor `WorldEvent.MIN_PLAYER_COUNT` = 1) |
| `InstanceCountMax` | int | Maximum simultaneous instances of this asset; `-1` (`WorldEvent.INFINITE_INSTANCES`) = unlimited |

The asset store is registered at path `WorldEvent/Event`, keyed by file name; `WorldEventAsset.ASSET_MAP` /
`WorldEventAsset.getAssetOrUnknown(id)` look assets up, and `WorldEventAsset.build(UUID, boolean transient)` produces
the `WorldEvent` component for a new instance. Every asset is run through `Validator` on load (stage graph must be
acyclic; every context key an action *references* must be *defined* by an earlier condition); `WorldEventAsset.valid()`
reports the result and an invalid asset is refused by the start paths.

### `Server/WorldEvent/Stage/<Id>.json` — `StageAsset`

A stage is "a step in a world-event's timeline. May consist of multiple different forks that are taken depending on
their conditions." Shared stages live in their own files and are referenced by id from `Root` / `Next`:

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
| `Next` | Id of the next `StageAsset`; omit on a terminal fork — the event then ends with `EventEndEcsEvent.Reason.SUCCESS` |

"Whichever fork's conditions complete first will be selected to run its actions and 'next' stage" — forks are
alternatives, evaluated concurrently; the losing forks' conditions are cancelled.

---

## Conditions

Every condition object carries `"Type"` (the registered id) plus its own keys. Built-ins registered by
`WorldEventsPlugin.setup()`:

| `Type` | Keys | Completes when |
|--------|------|----------------|
| `None` | — | Immediately |
| `IntervalCondition` | `IntervalKey` (context key), `MinSeconds`, `MaxSeconds`, `RemainingSeconds` (runtime/persisted) | A random duration in `[Min, Max]` has elapsed. Publishes an `IntervalContext` under `IntervalKey` so a `ModifyIntervalConditionInteraction` can shorten/extend it |
| `LocationCondition` | `LocationKey`, `LocationType` (`{"Type": "None"}` is the only built-in `EventLocation`), `Content` (array of spawners), `Clearance` (open blocks required above a candidate surface), `SearchRadius` | A valid location was found and the `Content` spawners placed there; publishes a `LocationContext` (`Location`, `Rotation`) under `LocationKey` |
| `ProximityCondition` | `LocationKey`, `Radius`, `Invert` | One or more players are within `Radius` of the location stored under `LocationKey` (`Invert`: completes once **no** player is within it) |
| `WorldClosedCondition` | `WorldKey`, `LoadTimeoutSeconds` | The world stored under `WorldKey` (a `WorldContext`) has been closed and unloaded; the timeout keeps it from completing while the world is still loading |
| `EventEndCondition` | `EventKey`, `EndMode` (`ITERATION` \| `TERMINATION`), `Result` (`PENDING` \| `COMPLETE` \| `FAILED`) | The child event stored under `EventKey` (an `EventContext`) ends — per iteration or on final termination |
| `SignalCondition` | `SignalId` | A `WorldEventSignal` ECS event with a matching `signalId` is received — "for example from an encounter's `SignalWorldEvent` action" (see [Encounters](encounters.md)) |

### Spawners (`LocationCondition.Content[]`)

| `Type` | Keys |
|--------|------|
| `NoSpawner` | — |
| `PrefabSpawner` | `PrefabKey` (context key the pasted prefab is published under, for a later `PrefabRemoveAction`), `Prefab` (one or more prefab asset ids — one is chosen at random), `Rotations` (candidate rotations, one chosen at random), `MaxHeightDelta` (maximum terrain height difference across the footprint), `Mask` (a `PlacementMask` of block/fluid types the prefab may be placed onto; omit for any — `PlacementMask.DEFAULT_ANY`) |

`WorldEventsConfig.ExclusionRadius` (default `512`, `DEFAULT_EXCLUSION_RADIUS`) is "the minimum distance that a
world-event location must be from other world-event locations" — location search rejects candidates closer than
that to another event's location; `0` disables the filter.

---

## Actions

| `Type` | Keys | Effect |
|--------|------|--------|
| `None` | — | No-op |
| `EffectsAction` | `LocationKey`, `Radius`, `Shape` (`{"Type": "Point", "Count", "OffsetMin", "OffsetMax"}` or `{"Type": "Ring", "Radius", "Count", "OffsetMin", "OffsetMax"}`), `CameraFX` (`Effect`, `IntensityMin/Max`), `SoundFX` (`Effect`, `VolumeMin/Max`, `PitchMin/Max`), `VisualFX` (`Effect`, `Color`, `ScaleMin/Max`, `DurationMin/Max`) | Collects players within `Radius` of the location and sends camera shake / sound / particle effects at points generated by `Shape` |
| `EventStartAction` | `Event` (a `WorldEventRecord`: `Id`, `Event`, `Transient`), `EventKey`, `Detach` | Starts a child event and publishes an `EventContext` under `EventKey`; unless `Detach` is true the child is terminated when the parent ends |
| `EventStopAction` | `EventKey` | Stops the child event stored under `EventKey` |
| `GlobalEventStartAction` / `GlobalEventStopAction` | `Id` (UUID), `Fail` (treat "already running / not running" as a failure) | Start/stop a **global** event via `GlobalWorldEventManager` |
| `MapMarkerOverrideAddAction` | `MarkerKey`, `Name`, `Icon`, `Global` | Adds a world-map marker override at the event location; `Global` = show to all players rather than only those within view distance. Publishes a `MapMarkerOverrideContext` under `MarkerKey` |
| `MapMarkerOverrideRemoveAction` | `MarkerKey` | Removes that marker |
| `MessageAction` | `Message` (a `Message` JSON, e.g. `{"RawText": "…"}`) | Broadcasts to the world |
| `PrefabPasteAction` | `PrefabKey`, `Permanent` | Pastes the prefab chosen by the spawner under `PrefabKey`; if `Permanent` is false "the prefab and its entities will be removed and the world rolled back to its previous state when the event ends" (the snapshot is a `PrefabRemoveContext`) |
| `PrefabRemoveAction` | `PrefabKey` | Removes a pasted prefab now |

An action returning `false` from `apply(...)` fails the fork (see *Runtime* below).

---

## Context keys

Conditions **define** typed variables and actions **reference** them; both sides name them with a plain string
(`"IntervalKey": "warmup"`, `"LocationKey": "site"`). At load time `Validator` checks that every referenced key
was defined by an earlier stage, so a typo fails the asset rather than a running event. At runtime the values
live in `WorldEvent.context`, a `ContextMap` keyed by `ContextKey` **and** context class:

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
  On the first tick of a stage it submits the forks' conditions to the `ConditionManager` (`onStart`); afterwards
  it picks the first fork whose conditions all `test()` true, cancels the other forks' conditions, runs
  `onComplete` + `reset` on the winning conditions, applies the actions in order, then moves to `next()`.
- **Failure:** if any winning condition's `onComplete` or any action returns `false`, the event resets to its root
  stage and clears its context; after `WorldEvent.FAIL_COUNT_THRESHOLD` (`5`) consecutive failures it fires
  `EventEndEcsEvent(event, Reason.FAIL)` and removes the entity.
- **Success:** a fork with no `Next` ends the iteration: `EventEndEcsEvent(event, Reason.SUCCESS)` is invoked on the
  event entity; a non-transient event's UUID is added to `WorldEventStorage` (`isComplete(uuid)`), and
  `repeatCount` / `IterationCount` decide whether it restarts.
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
recorded after completion, allowing it to run again in future". Every shipped gameplay config carries an empty
`WorldEvents` block.

### Global events (`GlobalWorldEventManager`)

The universe-level singleton `GlobalWorldEventManager.INSTANCE` persists active global event UUIDs in
`events.json` (`FILENAME`) and exposes `startEvent(UUID)` / `stopEvent(UUID)`,
`scheduleStartEventInAllWorlds(UUID)` / `scheduleRestartEventInAllWorlds(UUID)`, `contains(UUID)`,
`activeCount()` and `activeIds()`. It is loaded asynchronously in `WorldEventsPlugin.start()` (a failure logs
`Failed to load events.json`).

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
`reset` and `panel` (the in-game inspector UI backed by `WorldEventPanelPage` and friends in `.ui`).

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
`getTrackedEntityComponentType()`, `getTrackedBlockComponentType()`). Start an event from a plugin the same way the
config path does — build a `WorldEventRecord` and call `EventStartAction.startEvent(store, record)` on the world
thread.

---

## Observing and driving events from a plugin

**Ending:** `EventEndEcsEvent` is an `EcsEvent` invoked on the event entity; `getWorldEvent()` gives the instance
and `getReason()` is `SUCCESS` or `FAIL`. Handle it with an `EntityEventSystem<EntityStore, EventEndEcsEvent>`
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

- **Unknown asset ids don't fail loudly.** `Root` / `Next` resolve through `StageAsset.getAssetOrUnknown`, so a typo
  yields the `"Unknown"` stage (no forks) and an event that silently never advances. Run `/worldevent list` /
  `panel` to see what it is doing.
- **Referenced-before-defined keys are rejected at load.** `Validator` flags a `LocationKey` used by an action in
  stage 1 when the `LocationCondition` that defines it only runs in stage 2.
- **Five failures and it's gone.** Actions and `onComplete` returning `false` reset the event; the fifth consecutive
  failure removes the entity with `Reason.FAIL`. The warning is logged as `Failed to initialize world-event at
  stage: %d. Resetting event. Fail count: %d`.
- **Ticks are quarter-second.** Conditions are not evaluated faster than every `0.25s`, and not at all while the
  world has fewer non-spectator players than `PlayerCountMin`.
- **Non-permanent prefabs are rolled back.** With `"Permanent": false` the pasted blocks and any entities are
  restored from the snapshot when the event ends, so don't leave player-facing state inside them.
- **Global vs world events persist differently.** World events live in the world's `WorldEventStorage`; global
  ones in the universe `events.json`. Transient records are never marked complete.

> **See also:** [Encounters](encounters.md) (NPC-side `SignalWorldEvent`), [Trigger Volumes](trigger-volumes.md),
> [Interactions](interactions.md), [Prefabs](prefabs.md), [Events](events.md).
