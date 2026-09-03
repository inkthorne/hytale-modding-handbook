---
title: "Adventure API"
description: "Build Hytale adventure content in Java — ECS events for instance and zone discovery, adventure objectives, and world-instance integration."
seo:
  type: TechArticle
---

# Adventure API

**Doc type:** Java API · **Verified against 0.5.9**

This document covers adventure gameplay features like instance discovery and treasure chests.

## Overview

Implemented across `com.hypixel.hytale.builtin` (instances, adventure objectives) and `com.hypixel.hytale.server.core.universe.world` and provides:
- ECS events for instance discovery (`DiscoverInstanceEvent` and its `.Display` variant)
- ECS events for zone discovery (`DiscoverZoneEvent` and its `.Display` variant)
- A keyed `TreasureChestOpeningEvent` fired when a player opens a treasure chest
- `InstanceDiscoveryConfig` for controlling how discoveries are displayed
- `WorldMapTracker` for querying and mutating per-player map/zone discovery state
- Portal-world configuration assets (`PortalType`, `PortalDescription`, `PillTag`, `PortalSpawnConfig`)
- The `PortalKey` item property and per-stack `AdventureMetadata` (cursed items)
- Wilderness tracking (`WildernessConfig`, `WildernessTracker`) — which chunks are still "untouched"

> **Scripted adventure timelines** (stages, forks, conditions, actions) are a separate
> subsystem added in 0.6.3 and documented on their own page — see
> [World Events](world-events.md).

## Architecture
```
Instance discovery (com.hypixel.hytale.builtin.instances.event)
└── DiscoverInstanceEvent
      └── DiscoverInstanceEvent.Display (cancellable)
            └── InstanceDiscoveryConfig (display settings)

Zone discovery (com.hypixel.hytale.server.core.event.events.ecs)
└── DiscoverZoneEvent
      └── DiscoverZoneEvent.Display (cancellable)
            └── WorldMapTracker.ZoneDiscoveryInfo

Objectives
└── TreasureChestOpeningEvent (keyed by String)

Player map state
└── WorldMapTracker (discover/undiscover zones, teleport/view-radius rules)

Portal worlds (com.hypixel.hytale.server.core.asset.type.portalworld)
└── PortalType (Server/PortalTypes/*.json)
      ├── PortalDescription ("Description": name, flavor text, theme color)
      │     └── PillTag[] ("DescriptionTags": cosmetic UI tags)
      ├── PortalSpawnConfig ("Spawn": return-portal rules)
      └── cursed item ids ("CursedItems")

Portal items (com.hypixel.hytale.server.core.asset.type.item.config)
├── PortalKey (item "PortalKey" property → portal type + time limit)
└── metadata.AdventureMetadata (per-stack "Adventure" metadata: Cursed flag)

Wilderness (com.hypixel.hytale.builtin.adventure.wilderness)
├── WildernessConfig (GameplayConfig plugin section "Wilderness")
├── WildernessTracker (per-world ChunkStore Resource: which chunks are home vs wilderness)
└── component.Wilderness (per-entity wilderness-chunk bitset used by world events)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `DiscoverInstanceEvent` | `builtin.instances.event` | Base ECS event for instance discovery |
| `DiscoverInstanceEvent.Display` | `builtin.instances.event` | Cancellable ECS event for instance-discovery UI display |
| `DiscoverZoneEvent` | `server.core.event.events.ecs` | Base ECS event for zone discovery |
| `DiscoverZoneEvent.Display` | `server.core.event.events.ecs` | Cancellable ECS event for zone-discovery UI display |
| `TreasureChestOpeningEvent` | `builtin.adventure.objectives.events` | Keyed event fired when a player opens a treasure chest |
| `InstanceDiscoveryConfig` | `builtin.instances.config` | Configuration for instance-discovery display |
| `WorldMapTracker` | `server.core.universe.world` | Tracks and mutates per-player map discovery state |
| `WorldMapTracker.ZoneDiscoveryInfo` | `server.core.universe.world` | Record of zone-discovery details |
| `PortalType` | `server.core.asset.type.portalworld` | JSON asset for one portal destination (`Server/PortalTypes/*.json`) |
| `PortalDescription` | `server.core.asset.type.portalworld` | Display metadata for a portal (name, flavor text, theme color, tags) |
| `PillTag` | `server.core.asset.type.portalworld` | Cosmetic UI tag pill shown on a portal description |
| `PortalSpawnConfig` | `server.core.asset.type.portalworld` | Return-portal and spawn-override settings for a portal world |
| `PortalKey` | `server.core.asset.type.item.config` | Item config block that turns an item into a portal key |
| `AdventureMetadata` | `server.core.asset.type.item.config.metadata` | Per-`ItemStack` adventure metadata (the cursed flag) |
| `WildernessConfig` | `builtin.adventure.wilderness` | `GameplayConfig` plugin section `"Wilderness"` (0.6.3+) |
| `WildernessTracker` | `builtin.adventure.wilderness.resource` | Per-world `Resource<ChunkStore>`: home vs. wilderness chunks (0.6.3+) |
| `Wilderness` | `builtin.adventure.wilderness.component` | Per-entity component holding a bitset of nearby wilderness chunks (0.6.3+) |
| `WildernessLocation` | `builtin.adventure.wilderness.component` | World-event `EventLocation` type `"WildernessLocation"` (0.6.3+) |

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
            player.getPlayerRef().sendMessage(Message.raw("Zone discovered!"));

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
            player.getPlayerRef().sendMessage(Message.raw("You opened a treasure chest!"));
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
| `isAllowTeleportToCoordinates(PlayerRef, Player)` **(static)** | `boolean` | Whether that player may teleport to raw coordinates |
| `isAllowTeleportToMarkers(PlayerRef, Player)` | `boolean` | Whether that player may teleport to map markers |
| `getViewRadiusOverride()` | `Integer` | Get view radius override (nullable) |
| `setViewRadiusOverride(Integer)` | `void` | Set view radius override |
| `getEffectiveViewRadius(World)` | `int` | View radius actually in force (override, else the world's) |
| `getSentMarkers()` | `Map<String, MapMarker>` | Map markers already sent to this player |
| `unregisterEvents()` | `void` | Detach the tracker's listeners (called when the player leaves) |

> **Gotcha:** both teleport-permission checks take the player as arguments — they are *not*
> no-arg getters, and `isAllowTeleportToCoordinates` is **static** while
> `isAllowTeleportToMarkers` is an instance method.

### Accessing WorldMapTracker

The `WorldMapTracker` is accessed via `Player.getWorldMapTracker()`:

```java
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.PlayerRef;
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

// Check teleport permissions — both take the player, and the coordinate
// check is a static method on the class, not on the tracker instance
PlayerRef playerRef = player.getPlayerRef();
boolean canTeleportToCoords = WorldMapTracker.isAllowTeleportToCoordinates(playerRef, player);
boolean canTeleportToMarkers = tracker.isAllowTeleportToMarkers(playerRef, player);

// Override view radius
tracker.setViewRadiusOverride(500);  // Set custom view radius
```

---

## Portal Worlds

Portal destinations are JSON assets under `Server/PortalTypes/`, backed by the classes in
`com.hypixel.hytale.server.core.asset.type.portalworld`. A portal key **item** references a portal type
through its `PortalKey` property; while inside a portal world, item ids listed in the portal type's
`CursedItems` become cursed via per-stack [AdventureMetadata](#adventuremetadata).

---

## PortalType

**Package:** `com.hypixel.hytale.server.core.asset.type.portalworld`

JSON asset describing one portal destination. Loaded from `Server/PortalTypes/*.json`; the asset id is the
filename without `.json` (0.5.9 ships `Hederas_Lair`, `Henges`, `Jungles`, `Taiga`, `Windsurf_Valley`).

**JSON fields**

| Field | Type | Description |
|-------|------|-------------|
| `InstanceId` | string | Instance world the portal opens (e.g. `"Portals/Portals_Jungles"`, under `Server/Instances/`) |
| `Description` | object | Display metadata — see [PortalDescription](#portaldescription) |
| `GameplayConfig` | string | Gameplay config id for the portal world (defaults to `"Portal"`, i.e. `Server/GameplayConfigs/Portal.json`) |
| `VoidInvasionEnabled` | boolean | Whether the void invasion is enabled for this portal |
| `CursedItems` | string[] | Item ids that are cursed inside this portal world |
| `Spawn` | object | Return-portal spawn settings — see [PortalSpawnConfig](#portalspawnconfig) |
| `CloseWhenEmpty` | boolean | Whether the portal and its world are closed once the last player leaves (default `true`, added in 0.6.3) |

**Example** (`Server/PortalTypes/Jungles.json`):

```json
{
  "InstanceId": "Portals/Portals_Jungles",
  "Description": {
    "DisplayName": "server.portals.jungles",
    "FlavorText": "server.portals.jungles.description",
    "ThemeColor": "#23970cec",
    "SplashImage": "DefaultArtwork.png"
  }
}
```

**Methods**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetMap()` (static) | `DefaultAssetMap<String, PortalType>` | All loaded portal types |
| `getAssetStore()` (static) | `AssetStore<String, PortalType, ...>` | The backing asset store |
| `getId()` | `String` | Asset id (filename) |
| `getInstanceId()` | `String` | Instance world id the portal opens |
| `getDisplayName()` | `Message` | Localized display name (from the description) |
| `getDescription()` | `PortalDescription` | Display metadata |
| `getGameplayConfigId()` | `String` | Gameplay config id |
| `getGameplayConfig()` | `GameplayConfig` | Resolved gameplay config asset |
| `isVoidInvasionEnabled()` | `boolean` | Whether the void invasion runs in this portal world |
| `getCursedItems()` | `Set<String>` | Item ids cursed inside this portal world |
| `getSpawn()` | `PortalSpawnConfig` | Return-portal spawn settings |
| `isCloseWhenEmpty()` | `boolean` | Whether the portal world closes when empty (0.6.3+) |

```java
import com.hypixel.hytale.server.core.asset.type.portalworld.PortalType;

PortalType portalType = PortalType.getAssetMap().getAsset("Jungles");
if (portalType != null) {
    System.out.println("Opens instance: " + portalType.getInstanceId());
}
```

---

## PortalDescription

**Package:** `com.hypixel.hytale.server.core.asset.type.portalworld`

Display metadata for a portal — everything the portal-selection UI shows. Declared as the `Description`
object of a [PortalType](#portaltype).

**JSON fields**

| Field | Type | Description |
|-------|------|-------------|
| `DisplayName` | string | Translation key for the portal name |
| `FlavorText` | string | Translation key for the flavor text |
| `ThemeColor` | string | Color associated with the portal (hex) |
| `DescriptionTags` | array | Cosmetic UI tag pills — see [PillTag](#pilltag) |
| `Objectives` | string[] | Translation keys for the portal's objectives |
| `Tips` | string[] | Translation keys for wisdom/tips shown for this portal |
| `SplashImage` | string | Splash artwork filename |

**Methods**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDisplayNameKey()` | `String` | Translation key for the name |
| `getDisplayName()` | `Message` | Localized display name |
| `getFlavorTextKey()` | `String` | Translation key for the flavor text |
| `getFlavorText()` | `Message` | Localized flavor text |
| `getThemeColor()` | `Color` | Theme color |
| `getPillTags()` | `List<PillTag>` | Cosmetic UI tags (`DescriptionTags`) |
| `getObjectivesKeys()` | `String[]` | Objective translation keys |
| `getWisdomKeys()` | `String[]` | Tip translation keys (`Tips`) |
| `getSplashImageFilename()` | `String` | Splash artwork filename |

---

## PillTag

**Package:** `com.hypixel.hytale.server.core.asset.type.portalworld`

One cosmetic tag "pill" on a portal description (a label plus a color). Purely visual.

**JSON fields:** `TranslationKey` (string), `Color` (hex string).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getTranslationKey()` | `String` | Translation key of the label |
| `getMessage()` | `Message` | Localized label |
| `getColor()` | `Color` | Pill color |

---

## PortalSpawnConfig

**Package:** `com.hypixel.hytale.server.core.asset.type.portalworld`

Controls how players arrive in a portal world and how they get back. Declared as the `Spawn` object of a
[PortalType](#portaltype).

**JSON fields**

| Field | Type | Description |
|-------|------|-------------|
| `SpawnReturnPortal` | boolean | Whether a return portal is spawned in the portal world |
| `SpawnProviderOverride` | object | Overrides the world's spawn provider for arriving players |
| `ReturnBlock` | string | Block id used for the return portal block |

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isSpawningReturnPortal()` | `boolean` | Whether a return portal is spawned |
| `getSpawnProviderOverride()` | `ISpawnProvider` | Spawn-provider override (nullable) |
| `getReturnBlockOverrideId()` | `String` | Return-portal block id (nullable) |
| `getReturnBlockOverride()` | `BlockType` | Resolved return-portal block type |

---

## PortalKey

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config`

Item config block that turns an item into a **portal key**. Declared on an item definition via the
`PortalKey` property and read back with `Item.getPortalKey()` (null for items that aren't portal keys).
The portal device UI requires a key whose portal type matches before it summons a portal.

**JSON fields** (inside an item definition, e.g. `Server/Item/Items/Portal/PortalKey_Jungles.json`):

```json
{
  "PortalKey": {
    "PortalType": "Jungles",
    "TimeLimitSeconds": 720
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `PortalType` | string | Id of the [PortalType](#portaltype) this key opens |
| `TimeLimitSeconds` | int | Time limit for the portal visit, in seconds |

**Methods**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPortalTypeId()` | `String` | Portal type asset id |
| `getTimeLimitSeconds()` | `int` | Visit time limit in seconds |

```java
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.asset.type.item.config.PortalKey;

Item item = heldStack.getItem();
PortalKey key = item.getPortalKey();
if (key != null) {
    System.out.println("Opens portal " + key.getPortalTypeId()
        + " for " + key.getTimeLimitSeconds() + "s");
}
```

---

## AdventureMetadata

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.metadata`

Per-`ItemStack` adventure metadata, stored in the stack's metadata document under the key `"Adventure"`
(`AdventureMetadata.KEY`). In 0.5.9 it carries a single flag: whether the stack is **cursed** (BSON field
`Cursed`). Portal gameplay curses stacks whose item id appears in the active portal type's
`getCursedItems()` set; cursed stacks are uncursed or deleted when the portal visit ends.

**Constants**

| Constant | Type | Description |
|----------|------|-------------|
| `KEY` | `String` | Metadata key: `"Adventure"` |
| `CODEC` | `BuilderCodec<AdventureMetadata>` | Codec for the metadata payload |
| `KEYED_CODEC` | `KeyedCodec<AdventureMetadata>` | `KEY` + `CODEC` in one handle |

**Methods**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isCursed()` | `boolean` | Whether the stack is cursed |
| `setCursed(boolean)` | `void` | Set the cursed flag |

### Usage Example

Read and write it through the `ItemStack` metadata accessors:

```java
import com.hypixel.hytale.server.core.asset.type.item.config.metadata.AdventureMetadata;
import com.hypixel.hytale.server.core.inventory.ItemStack;

// Check whether a stack is cursed
AdventureMetadata meta = stack.getFromMetadataOrNull(AdventureMetadata.KEYED_CODEC);
boolean cursed = meta != null && meta.isCursed();

// Curse a stack (ItemStack is immutable — withMetadata returns a new stack)
AdventureMetadata cursedMeta = new AdventureMetadata();
cursedMeta.setCursed(true);
ItemStack cursedStack = stack.withMetadata(AdventureMetadata.KEYED_CODEC, cursedMeta);
```

> **See also:** [ItemStack → Metadata Access](inventory.md#metadata-access)

---

## Wilderness Tracking

**Package:** `com.hypixel.hytale.builtin.adventure.wilderness`

New as of 0.6.3. **Wilderness** is the engine's answer to "where can adventure content spawn without
bulldozing somebody's base". `WildernessPlugin` keeps a per-world `WildernessTracker` that marks every
chunk containing (or near) a `RespawnBlock` as **home**; every other chunk is **wilderness**. World-event
location conditions use it through the `"WildernessLocation"` [`EventLocation`](world-events.md) type, and
plugins can query it directly.

It is **off by default** — `Enabled` is `false` in the shipped `Server/GameplayConfigs/Default.json`.

### WildernessConfig

`GameplayConfig` plugin section `"Wilderness"` (`WildernessConfig.ID`). Read it for a world with
`WildernessConfig.getOrDefault(world)`.

| Field | Type | Default (shipped `Default.json`) | Description |
|-------|------|----------------------------------|-------------|
| `Enabled` | boolean | `false` | Enable wilderness tracking in this world |
| `OwnedHomeChunkRadius` | int | `8` | Horizontal chunk radius around an **owned** respawn marker (`-1` disables the radius) |
| `OwnedHomeChunkRadiusY` | int | `4` | Vertical chunk radius around an owned marker |
| `UnownedHomeChunkRadius` | int | `4` | Horizontal chunk radius around an **unowned** respawn marker |
| `UnownedHomeChunkRadiusY` | int | `2` | Vertical chunk radius around an unowned marker |
| `PlayerTrackerChunkRadius` | int | `2` | Horizontal chunk radius tracked around each player |
| `PlayerTrackerChunkRadiusY` | int | `1` | Vertical chunk radius tracked around each player |

```json
{
  "Plugin": {
    "Wilderness": {
      "Enabled": false,
      "OwnedHomeChunkRadius": 8,
      "OwnedHomeChunkRadiusY": 4,
      "UnownedHomeChunkRadius": 4,
      "UnownedHomeChunkRadiusY": 2,
      "PlayerTrackerChunkRadius": 2,
      "PlayerTrackerChunkRadiusY": 1
    }
  }
}
```

> The compiled-in defaults are *not* the shipped ones: `WildernessConfig.DEFAULT_HOME_RADIUS_Y_CHUNKS_OWNED`
> is `2`, `WildernessConfig.DEFAULT_HOME_RADIUS_CHUNKS_UNOWNED` is `2` and
> `WildernessConfig.DEFAULT_HOME_RADIUS_Y_CHUNKS_UNOWNED` is `1`, while `Default.json` sets `4`, `4` and `2`.
> Read the effective values with `WildernessConfig.getOrDefault(world)` rather than assuming either.

### WildernessTracker

**Package:** `com.hypixel.hytale.builtin.adventure.wilderness.resource` — a `Resource<ChunkStore>`, one per world.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getTracker(World)` **(static)** | `WildernessTracker` | The tracker resource for a world |
| `getResourceType()` **(static)** | `ResourceType<ChunkStore, WildernessTracker>` | Its resource type |
| `isEnabled()` / `isDisabled()` | `boolean` | Whether tracking is on for this world |
| `isWilderness(int x, int y, int z)` | `boolean` | Whether that **block** position is in a wilderness chunk (also `Vector3i` / `Vector3d` overloads) |
| `isHome(int x, int y, int z)` | `boolean` | Exactly `!isWilderness(...)` (also `Vector3i` / `Vector3d` overloads) |
| `isWildernessChunk(int x, int y, int z)` | `boolean` | Same test, in **chunk** coordinates (also a `Vector3i` overload) |
| `collectWildernessChunks(Vector3i, int, int, int, Collection<Vector3i>)` | `void` | Collect wilderness chunks in a radius (`Vector3d`, and raw-int-box, overloads too) |
| `collectHomeChunks(Vector3i, int, int, int, Collection<Vector3i>)` | `void` | Same for home chunks |
| `addHomeChunk(int, int, int, boolean)` | `void` | Mark a chunk as home (last arg = *owned*) |
| `removeHomeChunk(int, int, int, boolean)` | `void` | Drop a home-chunk mark |
| `generation()` | `long` | Bumped whenever the home-chunk set changes |

```java
import com.hypixel.hytale.builtin.adventure.wilderness.resource.WildernessTracker;

// Chunk-store thread only — WildernessTracker is a ChunkStore resource
WildernessTracker tracker = WildernessTracker.getTracker(world);
if (tracker.isEnabled() && tracker.isWilderness(x, y, z)) {
    // safe to spawn adventure content here
}
```

> **Gotchas**
> - `isHome(...)` is defined as the negation of `isWilderness(...)`, so with tracking **disabled**
>   every position reports as wilderness — check `isEnabled()` before trusting either.
> - Home chunks are derived from `RespawnBlock` block states, not from arbitrary player builds;
>   a base with no bed/respawn block is still "wilderness".
> - The tracker lives in the world's **chunk** store, so read it on that store's thread.

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
            player.getPlayerRef().sendMessage(
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

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
