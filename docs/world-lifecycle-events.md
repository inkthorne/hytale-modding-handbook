---
title: "World & Chunk Lifecycle Events"
description: "The Java event classes Hytale fires for world and chunk lifecycle — creation, loading, removal, saving and unloading — from universe.world.events and its .ecs subpackage, with keying and cancellability per event."
seo:
  type: TechArticle
---

# World & Chunk Lifecycle Events

**Doc type:** Java API · **Verified against 0.6.3**

Split out of [world.md](world.md) at the 2026-09-04 seam. The event classes a plugin subscribes to for world and chunk lifecycle, from `com.hypixel.hytale.server.core.universe.world.events` and its `.ecs` subpackage. The registry, priorities and base types these plug into are in [events.md](events.md), which defers domain event classes to pages like this one.\n\n> **Not to be confused with [world-events.md](world-events.md).** That documents the **World Event** feature added in 0.6.3 — scripted stage/fork timelines authored as JSON under `Server/WorldEvent`. This page is the engine's world and chunk lifecycle events, which are Java classes on the event bus. The two share the phrase and nothing else.

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
| `ChunkPreLoadProcessEvent` | `...universe.world.events` | Chunk pre-load processing | No |
| `ChunkSaveEvent` | `...universe.world.events.ecs` | Chunk is being saved (ECS) | Yes |
| `ChunkUnloadEvent` | `...universe.world.events.ecs` | Chunk is being unloaded (ECS) | Yes |
| `MoonPhaseChangeEvent` | `...universe.world.events.ecs` | Moon phase changed (ECS) | No |

---

### ChunkEvent (Base Class)

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Abstract base class for chunk-related events. Keyed by String.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getChunk()` | `WorldChunk` | The chunk this event relates to |

---

### ChunkSaveEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events.ecs`

ECS event fired when a chunk is being saved. Extends `CancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getChunk()` | `WorldChunk` | The chunk being saved |
| `isCancelled()` | `boolean` | Whether save is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the save |

---

### ChunkUnloadEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events.ecs`

ECS event fired when a chunk is being unloaded. Extends `CancellableEcsEvent`.

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

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getNewMoonPhase()` | `int` | The new moon phase index |

---

### ChunkPreLoadProcessEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Extends `ChunkEvent`, implements `IProcessedEvent`. Fired before a chunk is fully loaded, allowing pre-processing.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isNewlyGenerated()` | `boolean` | Whether chunk is newly generated |
| `getHolder()` | `Holder<ChunkStore>` | Chunk store holder |
| `processEvent(String)` | `void` | Process the event |
| `didLog()` | `boolean` | Whether event was logged |

**Usage Example:**
```java
getEventRegistry().registerGlobal(ChunkPreLoadProcessEvent.class, event -> {
    if (event.isNewlyGenerated()) {
        System.out.println("New chunk generated: " + event.getChunk());
    }
});
```

---

### Chunk Events Usage Notes

Chunk events (`ChunkSaveEvent`, `ChunkUnloadEvent`, `MoonPhaseChangeEvent`) extend `EcsEvent` rather than implementing `IEvent`. Handle them using an `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.universe.world.events.ecs.ChunkUnloadEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class ChunkUnloadSystem extends EntityEventSystem<EntityStore, ChunkUnloadEvent> {

    public ChunkUnloadSystem() {
        super(ChunkUnloadEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       ChunkUnloadEvent event) {
        var worldChunk = event.getChunk();
        System.out.println("Chunk unloading: " + worldChunk);

        // Optionally prevent unload
        // event.setCancelled(true);
    }

    @Override
    public Query<EntityStore> getQuery() {
        // Return appropriate query for entities you want to match
        return null; // Or a specific component type
    }
}
```

Register it in your plugin:

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new ChunkUnloadSystem());
}
```

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
