---
title: "World & Chunk Lifecycle Events"
description: "The Java event classes Hytale fires for world and chunk lifecycle — creation, loading, removal, saving and unloading — from universe.world.events and its .ecs subpackage, with keying and cancellability per event."
seo:
  type: TechArticle
---

# World & Chunk Lifecycle Events

**Doc type:** Java API · **Verified against 0.7.2**

Split out of [world.md](world.md) at the 2026-09-04 seam. The event classes a plugin subscribes to for world and chunk lifecycle, from `com.hypixel.hytale.server.core.universe.world.events` and its `.ecs` subpackage. The registry, priorities and base types these plug into are in [events.md](events.md), which defers domain event classes to pages like this one.

> **Not to be confused with [world-events.md](world-events.md).** That documents the **World Event** feature added in 0.6.3 — scripted stage/fork timelines authored as JSON under `Server/WorldEvent`. This page is the engine's world and chunk lifecycle events, which are Java classes on the event bus. The two share the phrase and nothing else.

---

## World Events

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Events related to world lifecycle (creation, removal, loading). These are **keyed by String** (world identifier).

### Event Summary

| Class | Description | Keyed | Cancellable |
|-------|-------------|-------|-------------|
| `WorldEvent` | Base class for world events | Yes (String) | - |
| `AddWorldEvent` | World is added to universe | Yes (String) | Yes |
| `RemoveWorldEvent` | World is being removed | Yes (String) | Yes |
| `StartWorldEvent` | World has started | Yes (String) | No |
| `AllWorldsLoadedEvent` | All worlds finished loading | No | No |

---

### WorldEvent (Base Class)

Abstract base class for world-related events.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getWorld()` | `World` | The world this event relates to |

---

### AddWorldEvent

Fired when a world is added to the universe. Implements `ICancellable`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getWorld()` | `World` | The world being added |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the event |

---

### RemoveWorldEvent

Fired when a world is being removed. Implements `ICancellable`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getWorld()` | `World` | The world being removed |
| `getRemovalReason()` | `RemovalReason` | Why the world is being removed |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the event |

**RemovalReason Enum:**

| Value | Description |
|-------|-------------|
| `GENERAL` | Normal removal |
| `EXCEPTIONAL` | Removal due to an error or exception |

---

### StartWorldEvent

Fired when a world starts (after loading completes).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getWorld()` | `World` | The world that started |

---

### AllWorldsLoadedEvent

Fired once when all worlds have finished loading. This is a **non-keyed event** (use `register()` not `registerGlobal()`).

```java
// No additional methods - just signals all worlds are loaded
getEventRegistry().register(AllWorldsLoadedEvent.class, event -> {
    // All worlds are now loaded and ready
});
```

---

### World Events Registration Example

```java
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.events.*;

@Override
protected void setup() {
    // Listen to all world additions (keyed event)
    getEventRegistry().registerGlobal(AddWorldEvent.class, event -> {
        System.out.println("World added: " + event.getWorld());
    });

    // Listen to world removals
    getEventRegistry().registerGlobal(RemoveWorldEvent.class, event -> {
        if (event.getRemovalReason() == RemoveWorldEvent.RemovalReason.EXCEPTIONAL) {
            System.out.println("World removed due to error: " + event.getWorld());
        }
    });

    // Listen for world start
    getEventRegistry().registerGlobal(StartWorldEvent.class, event -> {
        System.out.println("World started: " + event.getWorld());
    });

    // Listen for all worlds loaded (non-keyed)
    getEventRegistry().register(AllWorldsLoadedEvent.class, event -> {
        System.out.println("All worlds have finished loading!");
    });
}
```

---

## Chunk Events

Events related to chunk loading, saving, and unloading.

> **See also:** [Event Systems](components.md#event-type-registration)

### Event Summary

| Class | Package | Description | Cancellable |
|-------|---------|-------------|-------------|
| `ChunkEvent` | `...universe.world.events` | Base class for chunk events | - |
| `ChunkPreLoadProcessEvent` | `...universe.world.events` | Column pre-load processing | No |
| `ChunkSectionPreLoadProcessEvent` | `...universe.world.events` | Section pre-load processing | No |
| `ChunkSaveEvent` | `...universe.world.events.ecs` | Chunk is being saved (ECS) | Yes |
| `ChunkUnloadEvent` | `...universe.world.events.ecs` | Chunk is being unloaded (ECS) | Yes |
| `MoonPhaseChangeEvent` | `...universe.world.events.ecs` | Moon phase changed (ECS) | No |

---

### ChunkEvent (Base Class)

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Abstract base class for chunk-related events. Keyed by String.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getChunk()` | `WorldChunk` | The chunk column this event relates to |

`WorldChunk` has no block API in 0.7.2 — it is the column's flags, keep-alive and save state (see
[world-chunks.md → WorldChunk](world-chunks.md#worldchunk)). To read blocks, resolve a section as on
[block-access.md](block-access.md#resolving-a-section).

---

### ChunkSaveEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events.ecs`

ECS event fired when a chunk column is queued for saving. Extends `CancellableEcsEvent`. It is invoked
on the **`ChunkStore`**, against the column's entity ref, by `ChunkSavingSystems`; cancelling it keeps
the column out of this save pass.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getChunk()` | `WorldChunk` | The chunk being saved |
| `isCancelled()` | `boolean` | Whether save is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the save |

---

### ChunkUnloadEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events.ecs`

ECS event fired when a chunk column's keep-alive runs out and it is about to unload. Extends
`CancellableEcsEvent`. It is invoked on the **`ChunkStore`**, against the column's entity ref, by
`ChunkUnloadingSystem`. Cancelling keeps the column loaded; with `willResetKeepAlive()` still `true`
(the default) its keep-alive timer is reset, so the unload is retried once the timer runs out again.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getChunk()` | `WorldChunk` | The chunk being unloaded |
| `isCancelled()` | `boolean` | Whether unload is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the unload |
| `willResetKeepAlive()` | `boolean` | Whether keep-alive will be reset |
| `setResetKeepAlive(boolean)` | `void` | Control keep-alive reset behavior |

---

### MoonPhaseChangeEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events.ecs`

ECS event fired when the moon phase changes. Extends `EcsEvent` (not cancellable).
`WorldTimeResource.setMoonPhase` invokes it on the world's **`EntityStore`** with no entity ref, so it is
handled by a `WorldEventSystem<EntityStore, MoonPhaseChangeEvent>` (as the spawning plugin's
`MoonPhaseChangeEventSystem` does), not an `EntityEventSystem`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getNewMoonPhase()` | `int` | The new moon phase index |

---

### ChunkPreLoadProcessEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Extends `ChunkEvent`, implements `IProcessedEvent`. Fired once per chunk **column** after it is loaded
or generated and before its entity is added to the `ChunkStore`, keyed by the world's name. Listeners
can edit the column's `Holder` before it goes live.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isNewlyGenerated()` | `boolean` | Whether the column was generated rather than loaded from storage |
| `getHolder()` | `Holder<ChunkStore>` | The column's holder (not yet in the store) |
| `getWorld()` | `World` | 0.7.2+: the world the column belongs to |
| `processEvent(String)` | `void` | Process the event |
| `didLog()` | `boolean` | Whether event was logged |

0.7.2 added `World` as the constructor's first argument and the `getWorld()` accessor. The built-in
per-block preprocessing (block-entity setup in `BlockModule`, ticking-block discovery in
`BlockTickPlugin`, warp-marker spawning in the teleport plugin) moved off this event onto
`ChunkSectionPreLoadProcessEvent` below; in 0.7.2 the fluid plugin is the only shipped listener left on
this one, and it subscribes to both.

**Usage Example:**
```java
getEventRegistry().registerGlobal(ChunkPreLoadProcessEvent.class, event -> {
    if (event.isNewlyGenerated()) {
        System.out.println("New chunk generated: " + event.getChunk());
    }
});
```

---

### ChunkSectionPreLoadProcessEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Implements `IEvent<String>` and `IProcessedEvent` (it does **not** extend `ChunkEvent`, so there is no
`getChunk()`). Fired once per chunk **section** before the section's entity is added to the
`ChunkStore`, keyed by the world's name. For a classic column that is ten times per column load (sections
0–9, right after `ChunkPreLoadProcessEvent`); on a cubic world it also fires for sections loaded on their
own (see [world-chunks.md → Cubic sections](world-chunks.md#cubic-sections)).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isNewlyGenerated()` | `boolean` | Whether the section was generated rather than loaded from storage |
| `getHolder()` | `Holder<ChunkStore>` | The section's holder; its `ChunkSection` component gives the section coordinates, and its `BlockSection` the blocks |
| `getWorld()` | `World` | The world the section belongs to |
| `processEvent(String)` | `void` | Process the event |
| `didLog()` | `boolean` | Whether event was logged |

The shipped section listeners are `BlockModule` (ensures block entities), `BlockTickPlugin` (discovers
ticking blocks in newly generated sections), the farming, fluid and teleport plugins.

> **Both pre-load events run off the world thread.** The `ChunkGrid` load pipeline calls them from a
> `thenApplyAsync` stage with no executor, before the column or section is in the store. Work on the
> `Holder` you are given; do not read or write `ChunkStore` components from the listener. A listener that
> takes longer than one world tick is logged as `Took too long to pre-load process chunk section`.

---

### Chunk Events Usage Notes

The three ECS chunk events extend `EcsEvent` rather than implementing `IEvent`, so they are handled by
systems, not by the event registry, and **on the store they are invoked on**:

| Event | Store | Invoked against | System base |
|-------|-------|-----------------|-------------|
| `ChunkSaveEvent` | `ChunkStore` | the column's entity ref | `EntityEventSystem<ChunkStore, ChunkSaveEvent>` |
| `ChunkUnloadEvent` | `ChunkStore` | the column's entity ref | `EntityEventSystem<ChunkStore, ChunkUnloadEvent>` |
| `MoonPhaseChangeEvent` | `EntityStore` | no ref (store-wide) | `WorldEventSystem<EntityStore, MoonPhaseChangeEvent>` |

A system registered on the wrong store never sees the event. For the chunk events, query on
`WorldChunk` and register on `getChunkStoreRegistry()`. The unit below compiles against the 0.7.2 jar.

```java
package com.example.chunkevents;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.universe.world.chunk.WorldChunk;
import com.hypixel.hytale.server.core.universe.world.events.ecs.ChunkUnloadEvent;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;

public class ChunkUnloadSystem extends EntityEventSystem<ChunkStore, ChunkUnloadEvent> {

    public ChunkUnloadSystem() {
        super(ChunkUnloadEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<ChunkStore> chunk,
                       Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer,
                       ChunkUnloadEvent event) {
        WorldChunk column = event.getChunk();
        if (column.getX() == 0 && column.getZ() == 0) {
            event.setCancelled(true);   // keep the origin column loaded; keep-alive is reset
        }
    }

    @Override
    public Query<ChunkStore> getQuery() {
        return WorldChunk.getComponentType();
    }
}
```

Register it in your plugin:

```java
@Override
protected void setup() {
    getChunkStoreRegistry().registerSystem(new ChunkUnloadSystem());
}
```

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
