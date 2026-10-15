---
title: "Adventure API"
description: "Build Hytale adventure content — ECS events for instance and zone discovery, adventure objectives, portal-world assets, and the JSON portal and instance interactions (TeleportInstance, HubPortal, Teleporter)."
seo:
  type: TechArticle
---

# Adventure API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Items` · **Verified against 0.7.2**

This document covers adventure gameplay features: instance and zone discovery, portal worlds and wilderness tracking.

> **Removed in 0.7.2:** the treasure-map objective — `TreasureChestOpeningEvent`, the treasure-chest block and its
> interactions — is gone from the jar and the assets, with no replacement. A plugin listening for that event no
> longer compiles against 0.7.2.

## Overview

Implemented across `com.hypixel.hytale.builtin` (instances, portals, wilderness) and `com.hypixel.hytale.server.core.universe.world` and provides:
- ECS events for instance discovery (`DiscoverInstanceEvent` and its `.Display` variant)
- ECS events for zone discovery (`DiscoverZoneEvent` and its `.Display` variant)
- `InstanceDiscoveryConfig` for controlling how discoveries are displayed
- `WorldMapTracker` for querying and mutating per-player map/zone discovery state
- Portal-world configuration assets (`PortalType`, `PortalDescription`, `PillTag`, `PortalSpawnConfig`)
- The `PortalKey` item property and per-stack `AdventureMetadata` (ephemeral items)
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

Player map state
└── WorldMapTracker (discover/undiscover zones, teleport/view-radius rules)

Portal worlds (com.hypixel.hytale.server.core.asset.type.portalworld)
└── PortalType (Server/PortalTypes/*.json)
      ├── PortalDescription ("Description": name, flavor text, theme color)
      │     └── PillTag[] ("DescriptionTags": cosmetic UI tags)
      ├── PortalSpawnConfig ("Spawn": return-portal rules)
      └── ephemeral item ids ("EphemeralItems")

Portal items (com.hypixel.hytale.server.core.asset.type.item.config)
├── PortalKey (item "PortalKey" property → portal type + time limit)
└── metadata.AdventureMetadata (per-stack "Adventure" metadata: Ephemeral flag + world)

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
| `InstanceDiscoveryConfig` | `builtin.instances.config` | Configuration for instance-discovery display |
| `WorldMapTracker` | `server.core.universe.world` | Tracks and mutates per-player map discovery state |
| `WorldMapTracker.ZoneDiscoveryInfo` | `server.core.universe.world` | Record of zone-discovery details |
| `PortalType` | `server.core.asset.type.portalworld` | JSON asset for one portal destination (`Server/PortalTypes/*.json`) |
| `PortalDescription` | `server.core.asset.type.portalworld` | Display metadata for a portal (name, flavor text, theme color, tags) |
| `PillTag` | `server.core.asset.type.portalworld` | Cosmetic UI tag pill shown on a portal description |
| `PortalSpawnConfig` | `server.core.asset.type.portalworld` | Return-portal and spawn-override settings for a portal world |
| `PortalKey` | `server.core.asset.type.item.config` | Item config block that turns an item into a portal key |
| `AdventureMetadata` | `server.core.asset.type.item.config.metadata` | Per-`ItemStack` adventure metadata (the ephemeral flag) |
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
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class ZoneDiscoverySystem extends EntityEventSystem<EntityStore, DiscoverZoneEvent.Display> {

    public ZoneDiscoverySystem() {
        super(DiscoverZoneEvent.Display.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       DiscoverZoneEvent.Display event) {
        // Chat goes through the entity's PlayerRef component
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef != null) {
            var discoveryInfo = event.getDiscoveryInfo();
            playerRef.sendMessage(Message.raw("Zone discovered!"));

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

## InstanceDiscoveryConfig

**Package:** `com.hypixel.hytale.builtin.instances.config`

Configuration class for instance discovery display settings. Used by `DiscoverInstanceEvent` to control how discoveries appear to players.
As of 0.7.2 the major/default distinction is one value of a `Style` (`EventTitleStyle`); the older boolean
`Major` JSON key still loads and sets the style to `Major` or `Default`, but it is flagged deprecated
(`Validators.deprecated()`), and so are the `isMajor()` / `setMajor(...)` accessors.

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
| `getStyle()` | `EventTitleStyle` | How the client presents the title: `Default`, `Major`, `GoblinBreach` or `VoidEviction` (0.7.2+) |
| `setStyle(EventTitleStyle)` | `void` | Set the title style |
| `isMajor()` | `boolean` | Whether the style is `Major`. `@Deprecated(forRemoval=true)` as of 0.7.2 — use `getStyle()` |
| `setMajor(boolean)` | `void` | Sets the style to `Major` (`true`) or `Default` (`false`). `@Deprecated(forRemoval=true)` as of 0.7.2 — use `setStyle(...)` |
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
    EventTitleStyle style = config.getStyle();   // com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle
    float duration = config.getDuration();

    System.out.println("Discovery: " + title + " (style=" + style + ", duration=" + duration + "s)");
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
Ref<EntityStore> ref = /* the player's entity */;
Store<EntityStore> store = ref.getStore();
Player player = store.getComponent(ref, Player.getComponentType());
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
PlayerRef playerRef = store.getComponent(ref, PlayerRef.getComponentType());
boolean canTeleportToCoords = WorldMapTracker.isAllowTeleportToCoordinates(playerRef, player);
boolean canTeleportToMarkers = tracker.isAllowTeleportToMarkers(playerRef, player);

// Override view radius
tracker.setViewRadiusOverride(500);  // Set custom view radius
```

---

## Portal Worlds

Portal destinations are JSON assets under `Server/PortalTypes/`, backed by the classes in
`com.hypixel.hytale.server.core.asset.type.portalworld`. A portal key **item** references a portal type
through its `PortalKey` property; items listed in the portal type's `EphemeralItems` become ephemeral to that
portal world via per-stack [AdventureMetadata](#adventuremetadata) and cannot be taken out of it.

---

## PortalType

**Package:** `com.hypixel.hytale.server.core.asset.type.portalworld`

JSON asset describing one portal destination. Loaded from `Server/PortalTypes/*.json`; the asset id is the
filename without `.json` (0.7.2 ships `Goblin_Breach`, `Hederas_Lair`, `Henges`, `Jungles`, `Taiga`,
`The_Deepworks` and `Windsurf_Valley`).

**JSON fields**

| Field | Type | Description |
|-------|------|-------------|
| `InstanceId` | string | Instance world the portal opens (e.g. `"Portals/Portals_Jungles"`, under `Server/Instances/`) |
| `Description` | object | Display metadata — see [PortalDescription](#portaldescription) |
| `GameplayConfig` | string | Gameplay config id for the portal world (defaults to `"Portal"`, i.e. `Server/GameplayConfigs/Portal.json`) |
| `VoidInvasionEnabled` | boolean | Whether the void invasion is enabled for this portal |
| `EphemeralItems` | string[] | "Items that are considered ephemeral and can't be extracted from the portal instance" — see [AdventureMetadata](#adventuremetadata) |
| `Spawn` | object | Return-portal spawn settings — see [PortalSpawnConfig](#portalspawnconfig) |
| `CloseWhenEmpty` | boolean | Whether the portal and its world are closed once the last player leaves (default `true`, added in 0.6.3) |
| `TimeLimitSeconds` | int | "How long the portal world stays open, in seconds. 0 or less means no time limit." Default `-1`; a `PortalKey` can override it |
| `AllowedEntryCount` | int | "How many times a player can join the portal world before the world locks them out. 0 allows unlimited entries." Default `1`, validated `>= 0`; a `PortalKey` can override it |
| `AllowPlayersToLeaveViaMap` | boolean | Whether players can leave the portal world via the map (default `false`) |

`EphemeralItems`, `TimeLimitSeconds`, `AllowedEntryCount` and `AllowPlayersToLeaveViaMap` are new in 0.7.2.
`EphemeralItems` replaces the earlier `CursedItems` key, which 0.7.2 removed.

**Example** (`Server/PortalTypes/Jungles.json`):

```json
{
  "InstanceId": "Portals/Portals_Jungles",
  "TimeLimitSeconds": 720,
  "AllowedEntryCount": 1,
  "Description": {
    "DisplayName": "server.portals.jungles",
    "FlavorText": "server.portals.jungles.description",
    "ThemeColor": "#23970c",
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
| `getEphemeralItems()` | `Set<String>` | Item ids that become ephemeral in this portal world |
| `getSpawn()` | `PortalSpawnConfig` | Return-portal spawn settings |
| `isCloseWhenEmpty()` | `boolean` | Whether the portal world closes when empty (0.6.3+) |
| `getTimeLimitSeconds()` | `int` | Time limit in seconds; `0` or less = none |
| `getAllowedEntryCount()` | `int` | Entries allowed per player; `0` = unlimited |
| `isAllowPlayersToLeaveViaMap()` | `boolean` | Whether players can leave via the map |

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
    "PortalType": "Jungles"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `PortalType` | string | **Required** (`Validators.nonNull()`) id of the [PortalType](#portaltype) this key opens; an unknown id fails validation |
| `TimeLimitSeconds` | int | Optional override of the portal type's `TimeLimitSeconds`; `0` or less = no time limit |
| `AllowedEntryCount` | int | Optional override of the portal type's `AllowedEntryCount` (0.7.2+); `0` = unlimited, validated `>= 0` |

As of 0.7.2 every shipped key sets only `PortalType`; the time limit and entry count live on the portal type.

**Methods**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPortalTypeId()` | `String` | Portal type asset id |
| `getPortalType()` | `PortalType` | The resolved portal type (null if the id is unset or unknown) |
| `getTimeLimitSeconds()` | `int` | The key's override, else the portal type's value (`-1` if the type is missing) |
| `getAllowedEntryCount()` | `int` | The key's override, else the portal type's value (`1` if the type is missing) |

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

## Portal and instance interactions

The JSON `Type` values that move a player between worlds. The portal *assets* above describe a
destination; these describe the act of going there, and are written inside an item or block's
`Interactions` block. Three carry keys of their own and are documented below; four more —
`ExitInstance`, `Portal`, `PortalReturn` and `TeleportConfigInstance` — have none, and are
documented in their rows of the
[Complete Type Registry](interactions.md#complete-type-registry).

Two of the names collide with other registries and the collision is easy to trip over.
`Server/Item/Items/Electrum/Portal/Teleporter.json` carries both senses of `Teleporter` in one file:
a `BlockEntity.Components.Teleporter` block-entity component **and** a
`"Type": "Teleporter"` interaction on `CollisionEnter`. And the two
`Server/GameplayConfigs/` files that mention `ExitInstance` are not using this interaction at all —
there it is a `Death.RespawnController` type. Attribute a grep hit to a registry before counting it.

### TeleportInstance

**Package:** `com.hypixel.hytale.builtin.instances.interactions.TeleportInstanceInteraction`

Sends the player into a named **instance**, creating it if it does not exist. Codec doc: "Teleports
the **Player** to the named instance, creating it if required." Extends
[SimpleInstantInteraction](interactions.md#simpleinstantinteraction).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `InstanceName` | string | — | **Required** (`Validators.nonNull()`), and validated by `InstanceValidator`, so an unknown instance fails at load |
| `InstanceKey` | string | — | Chooses **where the instance's identity is stored**, not whether it persists — see below. Set it and identity is a global world name shared by every block using that key; omit it and identity lives on the triggering block |
| `OriginSource` | enum | `ENTITY` | **Required** (`Validators.nonNull()`) despite having a default. `ENTITY` takes the return position from the interacting entity, `BLOCK` from the targeted block. Those two are the whole enum |
| `PositionOffset` | vec3 | — | Offset applied to the return point, "used to prevent repeated interactions when returning from the instance". **Effectively required when `OriginSource` is `ENTITY`** — see below |
| `Rotation` | rotation | — | Rotation to set on the player when they return |
| `PersonalReturnPoint` | boolean | `false` | Give this player their own return point at the current location, overriding the world's |
| `CloseOnBlockRemove` | boolean | **`true`** | Delete the instance when the portal block is removed. The one boolean here defaulting true — and **it only has an effect when `InstanceKey` is omitted**, since it is written onto the block's `InstanceBlock` component and that component only exists on the keyless branch — the shipped test asset sets it alongside an `InstanceKey`, where it does nothing |
| `RemoveBlockAfter` | double | `-1` | Seconds to wait before removing the block that triggered the interaction; negative disables it |

Behavior notes:

- **`InstanceKey` decides where identity lives, and the shipped assets cover both branches.** With
  a key, the instance is looked up by that global world name, so every block naming the same key
  shares one instance — `Server/Item/Interactions/Tests/TeleportInstance.json` uses
  `"InstanceKey": "Persistent"`. Without one, an `InstanceBlock` component is created on the
  triggering block, the created world's UUID is written into it and the block is marked for saving,
  so **that block returns to its own instance on every later use** — which is what
  `Forgotten_Temple_Portal_Enter.json` and `Goblin/Goblin_Breach_Portal.json` rely on for portals you can
  re-enter. Neither branch is "a fresh instance each time".
- **Omitting `InstanceKey` requires a target block.** That branch opens with a bare `return` when
  there is none, or when the block's chunk section is not loaded — no `Failed` state, no message — so a
  keyless `TeleportInstance` fired with nothing targeted does nothing at all.
- **`OriginSource: BLOCK` throws rather than failing.** With no target block it raises
  `Can't use OriginSource.BLOCK without a target block`, and an unloaded chunk section raises
  `Chunk section not loaded` (0.7.2 reads the block through the section, not the chunk) — exceptions out
  of `firstRun`, not an `InteractionState.Failed` a chain can branch on. Both shipped `Block` uses are
  block interactions and therefore always have a target, so they exercise neither throw; both are read
  from the source alone.
- **`PositionOffset` is dereferenced without a null check on the `ENTITY` path.** The `BLOCK` branch
  guards it (`positionOffset != null ? … : new Vector3d()`); the `ENTITY` branch, which is the
  default, calls `getPosition().add(this.positionOffset)` on a field with no initialiser. How often
  that runs depends on `PersonalReturnPoint`: the return point is built once when the instance is
  created, but with `PersonalReturnPoint` set it is **also built on every later use**, including
  every re-entry into an instance that already exists. The one shipped asset on this path,
  `Forgotten_Temple_Portal_Enter.json`, carries all three conditions at once — it omits
  `OriginSource` (so the `ENTITY` default), sets `PersonalReturnPoint`, and writes `PositionOffset`
  as `{0,0,0}`, which is what you write when omitting it is not an option. (The other two shipped uses
  set `"OriginSource": "Block"`, so they take the guarded branch and say nothing about this one.)
  Treat the key as required whenever `OriginSource` is `ENTITY`.

> **Gotcha — `RemoveBlockAfter` cleans up outside the interaction chain, which is why it is a key at
> all.** The codec's stated reason is that "all interactions being stopped once teleporting to
> another world" makes a `Next` unsuitable. What is checkable without taking that on faith is the
> mechanism: for a positive value the removal is scheduled with `world.scheduleAfter(…)`, which then
> looks the chunk section up again and continues on the world executor, entirely outside the chain —
> and it re-checks that the block id is unchanged before removing it. `0` is **not** "disabled":
> it removes the block immediately, inline. Only a negative value disables it, and `-1` is the
> default — so unlike [`TriggerSpawnMarkers`'](npc-spawning.md#triggerspawnmarkers) `Count`, where
> the surprising value is also the default and you meet it by omission, this one has to be written
> deliberately. The only shipped value is `RemoveBlockAfter: 5`, on the test interaction, so the
> timed branch has a shipped example and the immediate one has none.

Three shipped uses: `Forgotten_Temple_Portal_Enter.json`, `Goblin/Goblin_Breach_Portal.json` and a test
interaction.

0.7.2 also invokes an `EnterInstanceTeleporterEvent` each time the interaction runs: on the entity store in the
keyed branch, and on the block entity in the keyless one. The world-event condition
`EnterInstanceTeleporterCondition` listens for it (see [World Events](world-events.md#registered-by-other-plugins)).

### HubPortal

**Package:** `com.hypixel.hytale.builtin.creativehub.interactions.HubPortalInteraction`

Sends the player to a **permanent** world rather than an instance, creating it if required. Extends
[SimpleInstantInteraction](interactions.md#simpleinstantinteraction).

| Property | Type | Description |
|----------|------|-------------|
| `WorldName` | string | **Required** (`Validators.nonNull()`). The permanent world to teleport to |
| `WorldGenType` | string | World generator to use when creating it (e.g. `Flat`, `Hytale`). **Mutually exclusive with `InstanceTemplate`** |
| `InstanceTemplate` | string | Instance asset to use as the template instead. **Mutually exclusive with `WorldGenType`** |

The mutual exclusion is stated in both codec descriptions and enforced by no validator, so an asset
setting both loads — and the resolution is not arbitrary: **`InstanceTemplate` wins and
`WorldGenType` is silently ignored**, because the branch tests the template first. Without a template it
loads the world from disk when `Universe.isWorldLoadable(WorldName)` is true, and only otherwise calls
`addWorld(worldName, worldGenType, null)` — so `WorldGenType` is read only for a world that exists nowhere yet.

**Both keys only ever matter at first creation.** The whole creation path runs only when
`Universe.getWorld(WorldName)` returns null; once that world exists the player is simply sent to it
and neither key is read again. So changing `WorldGenType` on a portal that has already been used has
no effect.

Three shipped uses, all under `Server/Item/Items/Portal/`: `Hub_Portal_Default.json`,
`Hub_Portal_Flat.json` and `Hub_Portal_Zone3_Taiga1.json`.

### Teleporter

**Package:** `com.hypixel.hytale.builtin.adventure.teleporter.interaction.server.TeleporterInteraction`

The rune-teleporter pad: warps an entity to the destination its block entity holds. Extends
[SimpleBlockInteraction](interactions.md#simpleblockinteraction).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Particle` | string | — | Particle played on the entity when it teleports |
| `ClearOutXZ` | double | `1.3` | How far the entity must move on the XZ plane after arriving before another teleporter will accept it. Validated `>= 0` |
| `ClearOutY` | double | `2.5` | The same along the Y axis. Validated `>= 0` |

None of the three is required. The two clear-out distances are what stop a player who arrives on top
of another teleporter from being bounced straight onward: arriving adds a `UsedTeleporter` component
and the interaction refuses while it is present, and `ClearUsedTeleporterSystem` removes it once the
entity has moved further than *either* threshold (a strict `>`, so exceeding one is enough). Setting
both to `0` does not fully re-enable the loop — it reduces the guard to the system's separate 100 ms
global teleporter cooldown, which is checked before the distances are.
Its one shipped use runs from `CollisionEnter`, not `Use`:

```json
{
  "Type": "Teleporter",
  "Particle": "Teleport"
}
```

---


## AdventureMetadata

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.metadata`

Per-`ItemStack` adventure metadata, stored in the stack's metadata document under the key `"Adventure"`
(`AdventureMetadata.KEY`). As of 0.7.2 it marks a stack **ephemeral** to one world: BSON fields `Ephemeral`
(boolean) and `EphemeralWorld` (that world's UUID). It replaces the 0.6.x "cursed" flag (`Cursed`,
`isCursed()` / `setCursed(...)`), which 0.7.2 removed along with the portal type's `CursedItems`.

How the portals plugin uses it:

- **Marking.** When an item entity appears in a portal world and its id is in the portal type's
  `EphemeralItems`, `EphemeralItemDropsSystem` sets `Ephemeral` and stamps the current world's UUID.
- **Deleting.** When a player entity is added to a world, `DeleteEphemeralItemsOnSpawnSystem` removes every
  ephemeral stack in the player's inventory whose `EphemeralWorld` is a different world.
- **Using.** If a player starts an interaction chain while holding an ephemeral stack outside its world,
  `CheckInteractionChainStartSystem` removes the stack and cancels the chain.

**Constants**

| Constant | Type | Description |
|----------|------|-------------|
| `KEY` | `String` | Metadata key: `"Adventure"` |
| `CODEC` | `BuilderCodec<AdventureMetadata>` | Codec for the metadata payload |
| `KEYED_CODEC` | `KeyedCodec<AdventureMetadata>` | `KEY` + `CODEC` in one handle |

**Methods**

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isEphemeral()` | `boolean` | Whether the stack is ephemeral |
| `setEphemeral(boolean)` | `void` | Set the ephemeral flag |
| `getEphemeralWorld()` | `UUID` | The world the stack belongs to |
| `setEphemeralWorld(UUID)` | `void` | Set that world |

### Usage Example

Read and write it through the `ItemStack` metadata accessors:

```java
import com.hypixel.hytale.server.core.asset.type.item.config.metadata.AdventureMetadata;
import com.hypixel.hytale.server.core.inventory.ItemStack;

// Check whether a stack is ephemeral
AdventureMetadata meta = stack.getFromMetadataOrNull(AdventureMetadata.KEYED_CODEC);
boolean ephemeral = meta != null && meta.isEphemeral();

// Bind a stack to the current world (ItemStack is immutable — withMetadata returns a new stack)
AdventureMetadata ephemeralMeta = new AdventureMetadata();
ephemeralMeta.setEphemeral(true);
ephemeralMeta.setEphemeralWorld(world.getWorldConfig().getUuid());
ItemStack ephemeralStack = stack.withMetadata(AdventureMetadata.KEYED_CODEC, ephemeralMeta);
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

It is **off by default in code** (`WildernessConfig.DEFAULT_ENABLED` is `false`), but as of 0.7.2 the shipped
`Server/GameplayConfigs/Default.json` and `PortalsGoblins.json` both set `Enabled: true`. `/wilderness debug [enabled]`
(0.7.2+) toggles debug visuals for a player: "Green marks wilderness chunks, red marks home chunks, on the world
map and in the world."

### WildernessConfig

`GameplayConfig` plugin section `"Wilderness"` (`WildernessConfig.ID`). Read it for a world with
`WildernessConfig.getOrDefault(world)`.

| Field | Type | Compiled default | Shipped `Default.json` | Description |
|-------|------|------------------|------------------------|-------------|
| `Enabled` | boolean | `false` | `true` | Enable wilderness tracking in this world |
| `OwnedHomeChunkRadius` | int | `8` | `3` | Horizontal chunk radius around an **owned** respawn marker (`-1` disables the radius) |
| `OwnedHomeChunkRadiusY` | int | `2` | `3` | Vertical chunk radius around an owned marker |
| `UnownedHomeChunkRadius` | int | `2` | `2` | Horizontal chunk radius around an **unowned** respawn marker |
| `UnownedHomeChunkRadiusY` | int | `1` | `2` | Vertical chunk radius around an unowned marker |
| `PlayerTrackerChunkRadius` | int | `2` | `8` | Horizontal chunk radius tracked around each player |
| `PlayerTrackerChunkRadiusY` | int | `1` | `2` | Vertical chunk radius tracked around each player |

```json
{
  "Plugin": {
    "Wilderness": {
      "Enabled": true,
      "OwnedHomeChunkRadius": 3,
      "OwnedHomeChunkRadiusY": 3,
      "UnownedHomeChunkRadius": 2,
      "UnownedHomeChunkRadiusY": 2,
      "PlayerTrackerChunkRadius": 8,
      "PlayerTrackerChunkRadiusY": 2
    }
  }
}
```

> The compiled-in defaults (`WildernessConfig.DEFAULT_*`) are *not* the shipped ones, and the two shipped configs
> differ from each other: `PortalsGoblins.json` uses `8`, `4`, `4`, `2`, `8`, `1`. Read the effective values with
> `WildernessConfig.getOrDefault(world)` rather than assuming any of them.

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
import com.hypixel.hytale.builtin.instances.event.DiscoverInstanceEvent;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.DiscoverZoneEvent;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class AdventurePlugin extends JavaPlugin {

    public AdventurePlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        // Register ECS systems for instance and zone discovery
        getEntityStoreRegistry().registerSystem(new InstanceDiscoverySystem());
        getEntityStoreRegistry().registerSystem(new ZoneAnnounceSystem());
    }

    // Inner class for zone discovery handling
    public static class ZoneAnnounceSystem
            extends EntityEventSystem<EntityStore, DiscoverZoneEvent.Display> {

        public ZoneAnnounceSystem() {
            super(DiscoverZoneEvent.Display.class);
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                           Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                           DiscoverZoneEvent.Display event) {
            PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
            if (playerRef != null) {
                playerRef.sendMessage(
                    Message.raw("New zone: " + event.getDiscoveryInfo().zoneName())
                        .bold(true)
                        .color("#FFD700")
                );
            }
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Player.getComponentType();
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
