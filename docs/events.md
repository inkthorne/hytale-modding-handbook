---
title: "Events API"
description: "Handle Hytale server events in Java — the EventRegistry for sync, async, global, and keyed listeners, EventPriority ordering, and ECS component-system events."
seo:
  type: TechArticle
---

# Events API

**Doc type:** Java API · **Verified against build-12**

This document covers the core event system. For specific event classes, see the relevant domain documentation:

- **Player events** → [player.md](player.md) (includes ChangeGameModeEvent, CraftRecipeEvent)
- **Block events** → [blocks.md](blocks.md)
- **World/Chunk events** → [world.md](world.md)
- **Entity events** → [entities.md](entities.md) (includes LivingEntityUseBlockEvent)
- **Combat/Damage events** → [combat.md](combat.md)
- **NPC/Sensor events** → [npc.md](npc.md)
- **Adventure events** → [adventure.md](adventure.md) (includes DiscoverZoneEvent)
- **Inventory events** → [inventory.md](inventory.md) (includes ItemContainerChangeEvent)
- **UI events** → [ui-api.md](ui-api.md) (includes WindowCloseEvent)
- **Permission events** → [permissions.md](permissions.md)
- **Prefab events** → [prefabs.md](prefabs.md)
- **Lifecycle events** → [plugin-lifecycle.md](plugin-lifecycle.md)
- **Asset events** → [assets.md](assets.md) (includes LoadAssetEvent, AssetPackRegisterEvent)
- **Asset editor events** → [asset-editor.md](asset-editor.md)
- **Localization events** → [i18n.md](i18n.md) (includes GenerateDefaultLanguageEvent)
- **Singleplayer events** → [singleplayer.md](singleplayer.md)

---

This page covers the core event system: registering listeners, priorities, the event interface hierarchy, keyed vs non-keyed events, and ECS event handling.

## Overview

Implemented in `com.hypixel.hytale.event` (with ECS events in `com.hypixel.hytale.component.system`) and provides:
- An `EventRegistry` for registering synchronous, async, global, keyed, and unhandled listeners
- Handler ordering via `EventPriority`
- A marker-interface hierarchy distinguishing keyed, async, and cancellable events
- `EventRegistration` handles for unregistering (and combining) listeners
- Cancellable events via `ICancellable` / `CancellableEcsEvent`
- ECS events handled by `EntityEventSystem` with entity-level context

## Architecture
```
EventRegistry (getEventRegistry())
├── Registration modes
│   ├── register / registerGlobal (keyed vs all keys)
│   ├── registerAsync / registerAsyncGlobal
│   └── registerUnhandled / registerAsyncUnhandled
├── EventPriority (FIRST → EARLY → NORMAL → LATE → LAST)
├── EventRegistration (unregister / combine)
├── Event types
│   ├── IBaseEvent → IEvent (keyed) / IAsyncEvent (async)
│   └── ICancellable (cancellable)
└── ECS events (registered via getEntityStoreRegistry())
    ├── EcsEvent → CancellableEcsEvent
    └── EntityEventSystem (handle() with chunk/index entity context)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `EventRegistry` | `event` | Registers event listeners |
| `EventPriority` | `event` | Enum controlling handler execution order |
| `EventRegistration<KeyType, EventType>` | `event` | Handle for unregistering / combining listeners |
| `IBaseEvent<KeyType>` | `event` | Marker interface for all events |
| `IEvent<KeyType>` | `event` | Marker interface for keyed events |
| `IAsyncEvent<KeyType>` | `event` | Marker interface for async events |
| `ICancellable` | `event` | Interface for cancellable events |
| `EcsEvent` | `component.system` | Abstract base for ECS events |
| `CancellableEcsEvent` | `component.system` | Abstract base for cancellable ECS events |
| `ICancellableEcsEvent` | `component.system` | Interface for cancellable ECS events |
| `EntityEventSystem` | `component.system` | System that handles ECS events with entity context |

## EventRegistry
**Package:** `com.hypixel.hytale.event`

Register event listeners. Access via `getEventRegistry()` in your plugin.

### Basic Registration
```java
// Simple event listener (no key)
<EventType extends IBaseEvent<Void>> EventRegistration<Void, EventType>
    register(Class<? super EventType> eventClass, Consumer<EventType> handler)

// With priority
<EventType extends IBaseEvent<Void>> EventRegistration<Void, EventType>
    register(EventPriority priority, Class<? super EventType> eventClass, Consumer<EventType> handler)

// With numeric priority (lower = earlier)
<EventType extends IBaseEvent<Void>> EventRegistration<Void, EventType>
    register(short priority, Class<? super EventType> eventClass, Consumer<EventType> handler)
```

### Keyed Registration
For events filtered by a key (e.g., specific block type):
```java
<KeyType, EventType extends IBaseEvent<KeyType>> EventRegistration<KeyType, EventType>
    register(Class<? super EventType> eventClass, KeyType key, Consumer<EventType> handler)

<KeyType, EventType extends IBaseEvent<KeyType>> EventRegistration<KeyType, EventType>
    register(EventPriority priority, Class<? super EventType> eventClass, KeyType key, Consumer<EventType> handler)
```

### Async Registration
For async event handlers (return CompletableFuture):
```java
<EventType extends IAsyncEvent<Void>> EventRegistration<Void, EventType>
    registerAsync(Class<? super EventType> eventClass,
                  Function<CompletableFuture<EventType>, CompletableFuture<EventType>> handler)

<EventType extends IAsyncEvent<Void>> EventRegistration<Void, EventType>
    registerAsync(EventPriority priority, Class<? super EventType> eventClass,
                  Function<CompletableFuture<EventType>, CompletableFuture<EventType>> handler)
```

### Global Registration
Listens to events regardless of key:
```java
<KeyType, EventType extends IBaseEvent<KeyType>> EventRegistration<KeyType, EventType>
    registerGlobal(Class<? super EventType> eventClass, Consumer<EventType> handler)

<KeyType, EventType extends IBaseEvent<KeyType>> EventRegistration<KeyType, EventType>
    registerGlobal(EventPriority priority, Class<? super EventType> eventClass, Consumer<EventType> handler)

// Async global
<KeyType, EventType extends IAsyncEvent<KeyType>> EventRegistration<KeyType, EventType>
    registerAsyncGlobal(Class<? super EventType> eventClass,
                        Function<CompletableFuture<EventType>, CompletableFuture<EventType>> handler)
```

### Unhandled Registration
Listens only if no other handler processed the event:
```java
<KeyType, EventType extends IBaseEvent<KeyType>> EventRegistration<KeyType, EventType>
    registerUnhandled(Class<? super EventType> eventClass, Consumer<EventType> handler)

<KeyType, EventType extends IAsyncEvent<KeyType>> EventRegistration<KeyType, EventType>
    registerAsyncUnhandled(Class<? super EventType> eventClass,
                           Function<CompletableFuture<EventType>, CompletableFuture<EventType>> handler)
```

---

## EventPriority
**Package:** `com.hypixel.hytale.event`

Use to control handler execution order. Lower priority number executes first.

### Enum Values
```java
public enum EventPriority {
    FIRST,   // Executes first (lowest priority number)
    EARLY,   // Early execution
    NORMAL,  // Default priority
    LATE,    // Late execution
    LAST     // Executes last (highest priority number)

    short getValue()  // Get numeric priority value
}
```

### Usage
```java
// Using enum
getEventRegistry().register(EventPriority.EARLY, PlayerConnectEvent.class, event -> {
    // Handle early
});

// Using raw short (lower = earlier)
getEventRegistry().register((short) 100, PlayerConnectEvent.class, event -> {
    // Custom priority
});
```

---

## Event Base Types

Core interfaces and classes that events extend or implement.

### IBaseEvent<KeyType>

**Package:** `com.hypixel.hytale.event`

Marker interface for all events. The generic `KeyType` parameter specifies whether the event is keyed (e.g., `String`) or non-keyed (`Void`).

```java
public interface IBaseEvent<KeyType> {
    // Marker interface
}
```

### IEvent<KeyType>

**Package:** `com.hypixel.hytale.event`

Marker interface for keyed events. Extends `IBaseEvent`.

```java
public interface IEvent<KeyType> extends IBaseEvent<KeyType> {
    // Marker interface for keyed events
}
```

### IAsyncEvent<KeyType>

**Package:** `com.hypixel.hytale.event`

Marker interface for async events. Extends `IBaseEvent`. Used with `registerAsync()` and `registerAsyncGlobal()` methods.

```java
public interface IAsyncEvent<KeyType> extends IBaseEvent<KeyType> {
    // Marker interface for async events
}
```

### ICancellable

**Package:** `com.hypixel.hytale.event`

Interface for events that can be cancelled.

```java
public interface ICancellable {
    boolean isCancelled();
    void setCancelled(boolean cancelled);
}
```

### EcsEvent

**Package:** `com.hypixel.hytale.component.system`

Abstract base class for ECS events handled by `EntityEventSystem`.

```java
public abstract class EcsEvent {
    public EcsEvent();
}
```

### ICancellableEcsEvent

**Package:** `com.hypixel.hytale.component.system`

Interface for cancellable ECS events.

```java
public interface ICancellableEcsEvent {
    boolean isCancelled();
    void setCancelled(boolean cancelled);
}
```

### CancellableEcsEvent

**Package:** `com.hypixel.hytale.component.system`

Abstract base class for cancellable ECS events. Extends `EcsEvent` and implements `ICancellableEcsEvent`.

```java
public abstract class CancellableEcsEvent extends EcsEvent implements ICancellableEcsEvent {
    public CancellableEcsEvent();
    public final boolean isCancelled();
    public final void setCancelled(boolean cancelled);
}
```

### Event Type Hierarchy

```
IBaseEvent<KeyType>
├── IEvent<KeyType>           (keyed events registered via EventRegistry)
│   └── ICancellable          (optional - for cancellable keyed events)
├── IAsyncEvent<KeyType>      (async events registered via registerAsync*)
│
EcsEvent                      (ECS events handled by EntityEventSystem)
└── CancellableEcsEvent       (cancellable ECS events)
    └── ICancellableEcsEvent  (interface)
```

---

## EventRegistration<KeyType, EventType>

**Package:** `com.hypixel.hytale.event`

Handle returned by `EventRegistry.register*()` methods. Used to unregister event handlers or check registration status. Extends `Registration`.

### Methods
```java
// Get the event class this registration handles
Class<EventType> getEventClass()

// Unregister this event handler (inherited from Registration)
void unregister()

// Check if still registered (inherited from Registration)
boolean isRegistered()
```

### Static Methods
```java
// Combine multiple registrations into one (unregistering the combined
// registration will unregister all)
static <K, E> EventRegistration<K, E> combine(EventRegistration<K, E>... registrations)
```

### Usage Example
```java
// Store registration for later unregistration
private EventRegistration<Void, PlayerConnectEvent> connectRegistration;

@Override
protected void setup() {
    connectRegistration = getEventRegistry().register(PlayerConnectEvent.class, event -> {
        event.getPlayerRef().sendMessage(Message.raw("Welcome!"));
    });
}

// Later, to unregister:
public void disableWelcomeMessage() {
    if (connectRegistration != null && connectRegistration.isRegistered()) {
        connectRegistration.unregister();
    }
}

// Combine multiple registrations
EventRegistration<Void, PlayerConnectEvent> reg1 = getEventRegistry().register(...);
EventRegistration<Void, PlayerConnectEvent> reg2 = getEventRegistry().register(...);
EventRegistration<Void, PlayerConnectEvent> combined = EventRegistration.combine(reg1, reg2);

// Unregistering combined will unregister both
combined.unregister();
```

---

## Keyed vs Non-Keyed Events

Some events are "keyed" (filtered by a key type like String or item type). Use:
- `register()` for non-keyed events (e.g., `PlayerConnectEvent`)
- `registerGlobal()` for keyed events when you want ALL events regardless of key (e.g., `PlayerInteractEvent`)
- `register(EventClass, key, handler)` for keyed events filtered to a specific key

### Keyed Events
Use `registerGlobal()` or provide a specific key:
- `PlayerInteractEvent` (keyed by String)
- `PlayerChatEvent` (keyed by String)
- World events (keyed by String)

### Non-Keyed Events
Use `register()`:
- `PlayerConnectEvent`
- `PlayerDisconnectEvent`
- `AllWorldsLoadedEvent`
- `BootEvent`, `ShutdownEvent`

### Example
```java
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.player.PlayerConnectEvent;
import com.hypixel.hytale.server.core.event.events.player.PlayerInteractEvent;

@Override
protected void setup() {
    // Non-keyed event: use register()
    getEventRegistry().register(PlayerConnectEvent.class, event -> {
        event.getPlayerRef().sendMessage(Message.raw("Welcome!"));
    });

    // Keyed event: use registerGlobal() to catch ALL interactions
    getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
        event.getPlayer().sendMessage(Message.raw("You interacted!"));
    });

    // Keyed event: filter to specific key
    getEventRegistry().register(PlayerInteractEvent.class, "specific_interaction_id", event -> {
        event.getPlayer().sendMessage(Message.raw("Specific interaction!"));
    });
}
```

---

## ECS Events (EntityEventSystem)

ECS events like `PlaceBlockEvent`, `BreakBlockEvent`, and `Damage` don't have direct player access.
To handle them with entity context, create an `EntityEventSystem` and register it with `getEntityStoreRegistry()`.

### Creating an EntityEventSystem

```java
package inkthorne.experiment.systems;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.PlaceBlockEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class PlaceBlockEventSystem extends EntityEventSystem<EntityStore, PlaceBlockEvent> {

    public PlaceBlockEventSystem() {
        super(PlaceBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PlaceBlockEvent event) {
        // Get player component using chunk and index
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            player.sendMessage(Message.raw("You placed a block!"));
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        // ComponentType implements Query, so return it directly
        return Player.getComponentType();
    }
}
```

### Registering the System

```java
@Override
protected void setup() {
    // Register ECS event system
    getEntityStoreRegistry().registerSystem(new PlaceBlockEventSystem());
}
```

### EntityEventSystem Methods

| Method | Description |
|--------|-------------|
| `handle(index, chunk, store, buffer, event)` | Called when the event fires. Use `chunk.getComponent(index, type)` to access entity components. |
| `getQuery()` | Return a Query to filter which entities this system handles. Return `null` to handle all, or a ComponentType to filter. |

### Common ECS Events

| Event | Package | Description |
|-------|---------|-------------|
| `PlaceBlockEvent` | `...event.events.ecs` | Block placed |
| `BreakBlockEvent` | `...event.events.ecs` | Block broken |
| `DamageBlockEvent` | `...event.events.ecs` | Block damaged |
| `UseBlockEvent.Pre/Post` | `...event.events.ecs` | Block used |
| `ChangeGameModeEvent` | `...event.events.ecs` | Game mode changes (cancellable) |
| `CraftRecipeEvent.Pre/Post` | `...event.events.ecs` | Crafting events (Pre is cancellable) |
| `DiscoverZoneEvent.Display` | `...event.events.ecs` | Zone discovery UI (cancellable) |
| `Damage` | `...modules.entity.damage` | Entity takes damage |
| `ChunkSaveEvent` | `...world.events.ecs` | Chunk saved |
| `ChunkUnloadEvent` | `...world.events.ecs` | Chunk unloaded |
| `PrefabPasteEvent` | `...prefab.event` | Prefab pasted |
| `KillFeedEvent.*` | `...damage.event` | Kill feed messages |

---

## Cancellable Events

Many events implement `ICancellable` or extend `CancellableEcsEvent` and can be cancelled:

```java
getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
    if (shouldPreventInteraction()) {
        event.setCancelled(true);
    }
});
```

### Checking Cancellation

```java
if (event.isCancelled()) {
    return; // Another handler already cancelled this
}
```

---

## Event Registration Best Practices

1. **Use appropriate priority** - Use `EARLY` if you need to cancel events before other handlers process them
2. **Check cancellation** - If another handler might cancel the event, check `isCancelled()` first
3. **Use keyed registration** - When you only care about specific event keys, use keyed registration for better performance
4. **Prefer ECS systems** - For ECS events, always use `EntityEventSystem` rather than trying to work around it
5. **Register in setup()** - Always register event handlers in your plugin's `setup()` method

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 event/ECS-event system (verified against `HytaleServer.jar`).

- **`eventTypeClass must extend EcsEvent!`** → an ECS event class registered via `registerEntityEventType`/`registerWorldEventType` (or used by an `EntityEventSystem`) does not extend `EcsEvent`. Fix: extend `EcsEvent`, or `CancellableEcsEvent` for cancellable ones.
- **Symptom:** a handler registered with `register()` on a keyed event (e.g. `PlayerInteractEvent`) never fires → keyed events are filtered by key, so a plain `register()` only matches the default/`Void` key. Fix: use `registerGlobal()` for all keys, or `register(EventClass, key, handler)` for a specific key (see [Keyed vs Non-Keyed Events](#keyed-vs-non-keyed-events)).
- **Symptom:** an ECS event (e.g. `PlaceBlockEvent`, `Damage`) handler can't reach the acting player → ECS events carry no direct player accessor. Fix: handle them in an `EntityEventSystem` and read components via `chunk.getComponent(index, type)` (see [ECS Events](#ecs-events-entityeventsystem)).
- **Symptom:** a later handler re-processes an event another handler already cancelled → cancellation does not stop dispatch. Fix: check `event.isCancelled()` first, and use an earlier `EventPriority` (e.g. `EARLY`) when you intend to cancel before others run.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
