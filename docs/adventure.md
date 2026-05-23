# Adventure API

This document covers adventure gameplay features like instance discovery and treasure chests.

## Adventure Events

Events related to adventure gameplay features.

### Event Summary

| Class | Package | Description |
|-------|---------|-------------|
| `DiscoverInstanceEvent` | `com.hypixel.hytale.builtin.instances.event` | Base class for instance discovery (ECS) |
| `DiscoverInstanceEvent.Display` | `com.hypixel.hytale.builtin.instances.event` | Instance discovery UI display (ECS, cancellable) |
| `DiscoverZoneEvent` | `com.hypixel.hytale.server.core.event.events.ecs` | Base class for zone discovery (ECS) |
| `DiscoverZoneEvent.Display` | `com.hypixel.hytale.server.core.event.events.ecs` | Zone discovery UI display (ECS, cancellable) |
| `TreasureChestOpeningEvent` | `com.hypixel.hytale.builtin.adventure.objectives.events` | Player opens treasure chest (keyed by String) |

---

## DiscoverInstanceEvent (Base Class)

**Package:** `com.hypixel.hytale.builtin.instances.event`

Abstract base class for instance discovery events. Extends `EcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getInstanceWorldUuid()` | `UUID` | UUID of the discovered instance world |
| `getDiscoveryConfig()` | `InstanceDiscoveryConfig` | Configuration for this discovery |

> **See also:** [ECS Event Systems](components.md#event-type-registration)

---

## DiscoverInstanceEvent.Display

**Package:** `com.hypixel.hytale.builtin.instances.event`

ECS event fired to display instance discovery in the UI. Extends `DiscoverInstanceEvent`, implements `ICancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getInstanceWorldUuid()` | `UUID` | UUID of the discovered instance world |
| `getDiscoveryConfig()` | `InstanceDiscoveryConfig` | Configuration for this discovery |
| `shouldDisplay()` | `boolean` | Whether the discovery should be displayed |
| `setDisplay(boolean)` | `void` | Control whether to display the discovery |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the event |

### Usage Example

Handle instance discovery using an `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.builtin.instances.event.DiscoverInstanceEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class InstanceDiscoverySystem extends EntityEventSystem<EntityStore, DiscoverInstanceEvent.Display> {

    public InstanceDiscoverySystem() {
        super(DiscoverInstanceEvent.Display.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       DiscoverInstanceEvent.Display event) {
        System.out.println("Instance discovered: " + event.getInstanceWorldUuid());

        // Optionally suppress the discovery display
        // event.setDisplay(false);

        // Or cancel entirely
        // event.setCancelled(true);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return null; // Or a specific component type
    }
}
```

### Registration

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new InstanceDiscoverySystem());
}
```

---

## DiscoverZoneEvent (Base Class)

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

Abstract base class for zone discovery events. Extends `EcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDiscoveryInfo()` | `WorldMapTracker.ZoneDiscoveryInfo` | Zone discovery details |

---

## DiscoverZoneEvent.Display

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

ECS event fired to display zone discovery in the UI. Extends `DiscoverZoneEvent`, implements `ICancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDiscoveryInfo()` | `WorldMapTracker.ZoneDiscoveryInfo` | Zone discovery details |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the event |

### Usage Example

Handle zone discovery using an `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.DiscoverZoneEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class ZoneDiscoverySystem extends EntityEventSystem<EntityStore, DiscoverZoneEvent.Display> {

    public ZoneDiscoverySystem() {
        super(DiscoverZoneEvent.Display.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       DiscoverZoneEvent.Display event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            var discoveryInfo = event.getDiscoveryInfo();
            player.sendMessage(Message.raw("Zone discovered!"));

            // Optionally suppress the discovery display
            // event.setCancelled(true);
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

### Registration

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new ZoneDiscoverySystem());
}
```

---

## TreasureChestOpeningEvent

**Package:** `com.hypixel.hytale.builtin.adventure.objectives.events`

Fired when a player opens a treasure chest. Implements `IEvent<String>` (keyed by String).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getObjectiveUUID()` | `UUID` | UUID of the adventure objective |
| `getChestUUID()` | `UUID` | UUID of the treasure chest being opened |
| `getPlayerRef()` | `Ref<EntityStore>` | Reference to the player opening the chest |
| `getStore()` | `Store<EntityStore>` | Entity store for accessing components |

> **See also:** [Inventory API](inventory.md#inventory)

### Usage Example

Since this is a keyed event (keyed by String), use `registerGlobal()` to catch all chest openings:

```java
import com.hypixel.hytale.builtin.adventure.objectives.events.TreasureChestOpeningEvent;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;

@Override
protected void setup() {
    // Listen for all treasure chest openings
    getEventRegistry().registerGlobal(TreasureChestOpeningEvent.class, event -> {
        var store = event.getStore();
        var playerRef = event.getPlayerRef();

        Player player = store.getComponent(playerRef, Player.getComponentType());
        if (player != null) {
            player.sendMessage(Message.raw("You opened a treasure chest!"));
        }

        System.out.println("Chest " + event.getChestUUID() +
                           " opened for objective " + event.getObjectiveUUID());
    });
}
```

---

## InstanceDiscoveryConfig

**Package:** `com.hypixel.hytale.builtin.instances.config`

Configuration class for instance discovery display settings. Used by `DiscoverInstanceEvent` to control how discoveries appear to players.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getTitleKey()` | `String` | Localization key for discovery title |
| `setTitleKey(String)` | `void` | Set title localization key |
| `getSubtitleKey()` | `String` | Localization key for subtitle |
| `setSubtitleKey(String)` | `void` | Set subtitle localization key |
| `isDisplay()` | `boolean` | Whether to display the discovery |
| `setDisplay(boolean)` | `void` | Control display visibility |
| `alwaysDisplay()` | `boolean` | Whether to always show discovery |
| `setAlwaysDisplay(boolean)` | `void` | Set always display |
| `getDiscoverySoundEventId()` | `String` | Sound event ID for discovery |
| `setDiscoverySoundEventId(String)` | `void` | Set discovery sound |
| `getIcon()` | `String` | Icon asset path |
| `setIcon(String)` | `void` | Set icon |
| `isMajor()` | `boolean` | Whether this is a major discovery |
| `setMajor(boolean)` | `void` | Set major flag |
| `getDuration()` | `float` | Display duration in seconds |
| `setDuration(float)` | `void` | Set display duration |
| `getFadeInDuration()` | `float` | Fade-in time in seconds |
| `setFadeInDuration(float)` | `void` | Set fade-in time |
| `getFadeOutDuration()` | `float` | Fade-out time in seconds |
| `setFadeOutDuration(float)` | `void` | Set fade-out time |
| `clone()` | `InstanceDiscoveryConfig` | Clone this config |

### Usage Example

```java
// In an EntityEventSystem handler for DiscoverInstanceEvent.Display
@Override
public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                   Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                   DiscoverInstanceEvent.Display event) {
    InstanceDiscoveryConfig config = event.getDiscoveryConfig();

    // Check discovery properties
    String title = config.getTitleKey();
    boolean isMajor = config.isMajor();
    float duration = config.getDuration();

    System.out.println("Discovery: " + title + " (major=" + isMajor + ", duration=" + duration + "s)");
}
```

---

## WorldMapTracker.ZoneDiscoveryInfo

**Package:** `com.hypixel.hytale.server.core.universe.world`

Java Record containing zone discovery information. Returned by `DiscoverZoneEvent.getDiscoveryInfo()`.

| Component | Type | Description |
|-----------|------|-------------|
| `zoneName()` | `String` | Name of the discovered zone |
| `regionName()` | `String` | Name of the region containing the zone |
| `display()` | `boolean` | Whether to display the discovery UI |
| `discoverySoundEventId()` | `String` | Sound event ID for discovery |
| `icon()` | `String` | Icon asset path |
| `major()` | `boolean` | Whether this is a major discovery |
| `duration()` | `float` | Display duration in seconds |
| `fadeInDuration()` | `float` | Fade-in time in seconds |
| `fadeOutDuration()` | `float` | Fade-out time in seconds |

### Usage Example

```java
// In an EntityEventSystem handler for DiscoverZoneEvent.Display
@Override
public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                   Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                   DiscoverZoneEvent.Display event) {
    WorldMapTracker.ZoneDiscoveryInfo info = event.getDiscoveryInfo();

    String zoneName = info.zoneName();
    String regionName = info.regionName();
    boolean isMajor = info.major();

    System.out.println("Discovered zone '" + zoneName + "' in region '" + regionName + "'");

    if (isMajor) {
        System.out.println("This is a major discovery!");
    }
}
```

---

## WorldMapTracker

**Package:** `com.hypixel.hytale.server.core.universe.world`

Tracks world map discovery state for a player. Provides methods to discover/undiscover zones and control map features.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPlayer()` | `Player` | Get the player this tracker belongs to |
| `getCurrentZone()` | `ZoneDiscoveryInfo` | Get current zone info (nullable) |
| `getCurrentBiomeName()` | `String` | Get current biome name |
| `discoverZone(World, String)` | `boolean` | Discover a zone by name |
| `undiscoverZone(World, String)` | `boolean` | Undiscover a zone |
| `discoverZones(World, Set<String>)` | `boolean` | Discover multiple zones |
| `undiscoverZones(World, Set<String>)` | `boolean` | Undiscover multiple zones |
| `isAllowTeleportToCoordinates()` | `boolean` | Check if coordinate teleport allowed |
| `isAllowTeleportToMarkers()` | `boolean` | Check if marker teleport allowed |
| `getViewRadiusOverride()` | `Integer` | Get view radius override (nullable) |
| `setViewRadiusOverride(Integer)` | `void` | Set view radius override |

### Accessing WorldMapTracker

The `WorldMapTracker` is accessed via `Player.getWorldMapTracker()`:

```java
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.world.WorldMapTracker;

// In a command or event handler where you have access to a Player
Player player = /* ... */;
WorldMapTracker tracker = player.getWorldMapTracker();

// Get current zone
WorldMapTracker.ZoneDiscoveryInfo currentZone = tracker.getCurrentZone();
if (currentZone != null) {
    System.out.println("Player is in zone: " + currentZone.zoneName());
}

// Discover a specific zone
World world = player.getWorld();
boolean discovered = tracker.discoverZone(world, "ancient_ruins");

// Check teleport permissions
boolean canTeleportToCoords = tracker.isAllowTeleportToCoordinates();
boolean canTeleportToMarkers = tracker.isAllowTeleportToMarkers();

// Override view radius
tracker.setViewRadiusOverride(500);  // Set custom view radius
```

---

## Complete Adventure System Example

```java
import com.hypixel.hytale.builtin.adventure.objectives.events.TreasureChestOpeningEvent;
import com.hypixel.hytale.builtin.instances.event.DiscoverInstanceEvent;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class AdventurePlugin extends JavaPlugin {

    public AdventurePlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        // Register ECS system for instance discovery
        getEntityStoreRegistry().registerSystem(new InstanceDiscoverySystem());

        // Register event listener for treasure chests
        getEventRegistry().registerGlobal(TreasureChestOpeningEvent.class, this::onChestOpen);
    }

    private void onChestOpen(TreasureChestOpeningEvent event) {
        var store = event.getStore();
        var playerRef = event.getPlayerRef();

        Player player = store.getComponent(playerRef, Player.getComponentType());
        if (player != null) {
            player.sendMessage(
                Message.raw("Treasure found!")
                    .bold(true)
                    .color("#FFD700")
            );
        }
    }

    // Inner class for instance discovery handling
    public static class InstanceDiscoverySystem
            extends EntityEventSystem<EntityStore, DiscoverInstanceEvent.Display> {

        public InstanceDiscoverySystem() {
            super(DiscoverInstanceEvent.Display.class);
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                           Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                           DiscoverInstanceEvent.Display event) {
            // Log the discovery
            System.out.println("Player discovered instance: " + event.getInstanceWorldUuid());

            // Could customize display behavior here
            // event.setDisplay(false); // Suppress default UI
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Player.getComponentType();
        }
    }
}
```
