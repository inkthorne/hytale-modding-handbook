---
title: "World API"
description: "Work with the Hytale World in Java — the World tick thread exposing players, entities, chunks, and ECS stores, per-chunk block/state/terrain access, and per-player chunk loading."
seo:
  type: TechArticle
---

# World API

**Doc type:** Java API · **Verified against build-12**

Covers the runtime `World` object, its chunks, per-player chunk tracking, gameplay configuration, and the world/chunk lifecycle events plugins can observe.

## Overview

Implemented in `com.hypixel.hytale.server.core.universe.world` (and related asset/event subpackages) and provides:
- A `World` tick thread exposing players, entities, chunks, and ECS stores
- Direct block/state/terrain access per `WorldChunk`
- Per-player chunk loading and visibility control via `ChunkTracker`
- Layered gameplay configuration (`GameplayConfig`, `WorldConfig`, `DeathConfig`)
- Per-world client feature toggles (`ClientFeature`)
- World-lifecycle and chunk events (add/remove/start/load, save/unload, moon phase)

## Architecture
```
World (tick thread)
├── Players (getPlayers / addPlayer / PlayerRef)
│   └── ChunkTracker (per-player chunk loading + visibility)
├── Chunks (getChunk* / WorldChunk)
│   ├── Block + state + terrain access
│   └── ChunkFlag (per-chunk state flags)
├── ECS Stores (ChunkStore, EntityStore)
├── Configuration
│   └── GameplayConfig
│       ├── WorldConfig (block rules, day/night, sleep)
│       └── DeathConfig (item loss, respawn)
├── ClientFeature toggles (per-world, broadcast to clients)
└── Events
    ├── World lifecycle (Add / Remove / Start / AllWorldsLoaded)
    └── Chunk (ChunkPreLoadProcess / ChunkSave / ChunkUnload / MoonPhaseChange)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `World` | `server.core.universe.world` | The game world; tick thread exposing players, entities, chunks, and config |
| `WorldChunk` | `server.core.universe.world.chunk` | A loaded chunk; block, state, and terrain data access |
| `ChunkFlag` | `server.core.universe.world.chunk` | Enum of per-chunk state flags |
| `ChunkTracker` | `server.core.modules.entity.player` | Per-player chunk loading rate and visibility |
| `GameplayConfig` | `server.core.asset.type.gameplay` | Master gameplay configuration; holds sub-configs |
| `WorldConfig` (gameplay) | `server.core.asset.type.gameplay` | Block rules, day/night cycle, sleep settings |
| `DeathConfig` | `server.core.asset.type.gameplay` | Death/respawn and item-loss behavior |
| `ClientFeature` | `protocol.packets.setup` | Enum of per-world client feature toggles |
| `WorldEvent` | `server.core.universe.world.events` | Base for world-lifecycle events (keyed by String) |
| `ChunkEvent` | `server.core.universe.world.events` | Base for chunk events |
| `ChunkSaveEvent` / `ChunkUnloadEvent` | `server.core.universe.world.events.ecs` | ECS events for chunk save/unload |
| `MoonPhaseChangeEvent` | `server.core.universe.world.events.ecs` | ECS event fired on moon phase change |

## World
**Package:** `com.hypixel.hytale.server.core.universe.world`

Represents a game world. Extends TickingThread, implements Executor.

### Core Properties
```java
String getName()
boolean isAlive()
boolean isTicking()
void setTicking(boolean ticking)
boolean isPaused()
void setPaused(boolean paused)
long getTick()
HytaleLogger getLogger()
```

### Configuration
```java
WorldConfig getWorldConfig()
DeathConfig getDeathConfig()
GameplayConfig getGameplayConfig()
int getDaytimeDurationSeconds()
int getNighttimeDurationSeconds()
void setTps(int tps)
static void setTimeDilation(float dilation, ComponentAccessor<EntityStore> accessor)
```

See [Configuration Classes](#configuration-classes) below for details on WorldConfig, DeathConfig, and GameplayConfig.

### Players
```java
List<Player> getPlayers()
int getPlayerCount()
Collection<PlayerRef> getPlayerRefs()
void trackPlayerRef(PlayerRef ref)
void untrackPlayerRef(PlayerRef ref)

// Adding players
CompletableFuture<PlayerRef> addPlayer(PlayerRef ref)
CompletableFuture<PlayerRef> addPlayer(PlayerRef ref, Transform position)
CompletableFuture<PlayerRef> addPlayer(PlayerRef ref, Transform position, Boolean teleport, Boolean respawn)
CompletableFuture<Void> drainPlayersTo(World targetWorld, Collection<PlayerRef> players)
```

### Entities
```java
Entity getEntity(UUID uuid)
Ref<EntityStore> getEntityRef(UUID uuid)
<T extends Entity> T spawnEntity(T entity, Vector3d position, Vector3f rotation)
<T extends Entity> T addEntity(T entity, Vector3d position, Vector3f rotation, AddReason reason)
```

### Chunks
```java
WorldChunk loadChunkIfInMemory(long chunkKey)
WorldChunk getChunkIfInMemory(long chunkKey)
WorldChunk getChunkIfLoaded(long chunkKey)
WorldChunk getChunkIfNonTicking(long chunkKey)
CompletableFuture<WorldChunk> getChunkAsync(long chunkKey)
CompletableFuture<WorldChunk> getNonTickingChunkAsync(long chunkKey)
```

### ECS Stores
```java
ChunkStore getChunkStore()
EntityStore getEntityStore()
```

### Messaging
```java
void sendMessage(Message msg)  // Broadcast to all players in world
```

### Features
```java
Map<ClientFeature, Boolean> getFeatures()
boolean isFeatureEnabled(ClientFeature feature)
void registerFeature(ClientFeature feature, boolean enabled)
void broadcastFeatures()
```

See [ClientFeature](#clientfeature) enum below.

### Other
```java
ChunkLightingManager getChunkLighting()
WorldMapManager getWorldMapManager()
WorldPathConfig getWorldPathConfig()
WorldNotificationHandler getNotificationHandler()
EventRegistry getEventRegistry()
Path getSavePath()

// Lifecycle
CompletableFuture<World> init()
void stopIndividualWorld()
void execute(Runnable task)  // Execute on world thread
```

> **See also:** [ECS Components](components.md#common-store-types)

---

## WorldChunk
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk`

Represents a chunk in the world. Implements `BlockAccessor` and `Component<ChunkStore>`. Provides direct access to block data, states, and chunk properties.

### Getting the ComponentType
```java
static ComponentType<ChunkStore, WorldChunk> getComponentType()
```

### Block Access
```java
// Get block ID at local coordinates (0-31 for x/z, 0-255 for y)
int getBlock(int x, int y, int z)

// Set block at local coordinates
boolean setBlock(int x, int y, int z, int blockId,
                 BlockType blockType, int rotation, int filler, int flags)

// Get filler block ID
int getFiller(int x, int y, int z)

// Get rotation index at position
int getRotationIndex(int x, int y, int z)
```

### Block States
```java
// Set the block type, rotation, and component holder at position
void setState(int x, int y, int z, BlockType type, int rotationIndex, Holder<ChunkStore> holder)

// Get block component entity reference
Ref<ChunkStore> getBlockComponentEntity(int x, int y, int z)

// Get block component holder
Holder<ChunkStore> getBlockComponentHolder(int x, int y, int z)
```

### Ticking Blocks
```java
// Check if block is ticking
boolean isTicking(int x, int y, int z)

// Set block ticking state
boolean setTicking(int x, int y, int z, boolean ticking)
```

### Terrain Data
```java
// Get height at x,z position
short getHeight(int x, int z)
short getHeight(int index)

// Get tint at position
int getTint(int x, int z)

// Get fluid data
int getFluidId(int x, int y, int z)
byte getFluidLevel(int x, int y, int z)

// Get support value
int getSupportValue(int x, int y, int z)
```

### Chunk Properties
```java
// Get chunk position
long getIndex()    // Chunk key
int getX()         // Chunk X coordinate
int getZ()         // Chunk Z coordinate

// Get parent world
World getWorld()

// Get chunk accessor
ChunkAccessor getChunkAccessor()
```

### Chunk Flags
```java
// Check/set chunk flags
boolean is(ChunkFlag flag)
boolean not(ChunkFlag flag)
void setFlag(ChunkFlag flag, boolean value)
boolean toggleFlag(ChunkFlag flag)
void initFlags()
```

### Keep-Alive & Loading
```java
// Keep chunk loaded
boolean shouldKeepLoaded()
void addKeepLoaded()
void removeKeepLoaded()

// Keep-alive timer (returns remaining time)
int pollKeepAlive(int decrement)
void resetKeepAlive()

// Active timer
int pollActiveTimer(int decrement)
void resetActiveTimer()
```

### Persistence
```java
// Saving state
void markNeedsSaving()
boolean getNeedsSaving()
boolean consumeNeedsSaving()
boolean isSaving()
void setSaving(boolean saving)
```

### Lighting
```java
// Lighting updates
void setLightingUpdatesEnabled(boolean enabled)
boolean isLightingUpdatesEnabled()
```

### Chunk Components
```java
// Get internal chunk components
BlockChunk getBlockChunk()
BlockComponentChunk getBlockComponentChunk()
EntityChunk getEntityChunk()
```

### ECS Integration
```java
// Convert to holder (blueprint)
Holder<ChunkStore> toHolder()

// Reference management
void setReference(Ref<ChunkStore> ref)
Ref<ChunkStore> getReference()

// Clone as component
Component<ChunkStore> clone()
```

### Loading from Holder
```java
void loadFromHolder(World world, int x, int z, Holder<ChunkStore> holder)
```

> **See also:** [Collision API](collision.md#blockcollisiondata)

---

## ChunkFlag
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk`

Enum defining chunk state flags. Implements `Flag` interface.

### Values

| Value | Description |
|-------|-------------|
| `START_INIT` | Chunk initialization has started |
| `INIT` | Chunk is fully initialized |
| `NEWLY_GENERATED` | Chunk was newly generated (not loaded from disk) |
| `ON_DISK` | Chunk exists on disk |
| `TICKING` | Chunk is actively ticking |

### Methods
```java
static ChunkFlag[] values()
static ChunkFlag valueOf(String name)
int mask()  // Get bitmask for this flag
```

### Usage Example
```java
WorldChunk chunk = world.getChunkIfLoaded(chunkKey);
if (chunk != null) {
    // Check if chunk is newly generated
    if (chunk.is(ChunkFlag.NEWLY_GENERATED)) {
        // Apply first-time generation logic
    }

    // Check if chunk is ticking
    if (chunk.is(ChunkFlag.TICKING)) {
        // Chunk is actively processing
    }

    // Set a flag
    chunk.setFlag(ChunkFlag.ON_DISK, true);
}
```

---

### Usage Example
```java
// Get a chunk from the world
World world = ...;
long chunkKey = ...; // Calculate from world coordinates

WorldChunk chunk = world.getChunkIfLoaded(chunkKey);
if (chunk != null) {
    // Read block at local position (0-31, 0-255, 0-31)
    int blockId = chunk.getBlock(16, 64, 16);

    // Set a block (requires BlockType lookup).
    // Note: setBlock's 4th param is the int blockId, NOT BlockType.getId()
    // (which returns a String). Resolve the numeric id separately.
    BlockType stoneType = BlockType.fromString("stone");
    chunk.setBlock(16, 65, 16, blockId, stoneType, 0, 0, 0);

    // Mark chunk for saving
    chunk.markNeedsSaving();
}
```

---

## ChunkTracker
**Package:** `com.hypixel.hytale.server.core.modules.entity.player`

Component that manages chunk loading and visibility per player. Controls how quickly chunks are sent to a player and which chunks should be visible.

### Getting the Component
```java
ChunkTracker tracker = store.getComponent(ref, ChunkTracker.getComponentType());
// Or from PlayerRef
ChunkTracker tracker = playerRef.getChunkTracker();
```

### Chunk Visibility
```java
boolean isLoaded(long chunkIndex)           // Is chunk loaded for this player?
boolean shouldBeVisible(long chunkIndex)    // Should chunk be visible?
ChunkVisibility getChunkVisibility(long chunkIndex)  // Get visibility state
```

#### ChunkVisibility Enum

Nested enum defining chunk visibility states for a player.

| Value | Description |
|-------|-------------|
| `NONE` | Chunk is not visible to player |
| `HOT` | Chunk is actively visible (nearby) |
| `COLD` | Chunk is visible but not actively updated |

### Chunk Loading Rates
```java
int getMaxChunksPerSecond()                 // Max chunks sent per second
void setMaxChunksPerSecond(int rate)
void setDefaultMaxChunksPerSecond(PlayerRef ref)  // Reset to default based on connection

int getMaxChunksPerTick()                   // Max chunks sent per tick
void setMaxChunksPerTick(int rate)
```

### Load Radius
```java
int getMinLoadedChunksRadius()              // Minimum radius of loaded chunks
void setMinLoadedChunksRadius(int radius)

int getMaxHotLoadedChunksRadius()           // Max radius of hot-loaded chunks
void setMaxHotLoadedChunksRadius(int radius)
```

### Statistics
```java
int getLoadedChunksCount()                  // Number of chunks loaded for player
int getLoadingChunksCount()                 // Number of chunks currently loading
```

### Lifecycle
```java
void unloadAll(PlayerRef ref)               // Unload all chunks for player
void clear()                                // Clear tracker state
void removeForReload(long chunkIndex)       // Mark chunk for reload
```

### Constants
```java
static final int MAX_CHUNKS_PER_SECOND       // Default max (remote)
static final int MAX_CHUNKS_PER_SECOND_LAN   // Max for LAN connections
static final int MAX_CHUNKS_PER_SECOND_LOCAL // Max for local/singleplayer
static final int MAX_CHUNKS_PER_TICK
static final int MIN_LOADED_CHUNKS_RADIUS
static final int MAX_HOT_LOADED_CHUNKS_RADIUS
```

### Usage Example
```java
// Increase chunk loading speed for a player
ChunkTracker tracker = playerRef.getChunkTracker();
tracker.setMaxChunksPerSecond(100);  // Send up to 100 chunks/second

// Check how many chunks are loaded
int loaded = tracker.getLoadedChunksCount();
playerRef.sendMessage(Message.raw("You have " + loaded + " chunks loaded"));
```

---

## Usage Example
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // Get world info
    String worldName = world.getName();
    int playerCount = world.getPlayerCount();

    // Broadcast to all players in world
    world.sendMessage(Message.raw("Hello everyone!"));

    // Get all players
    for (Player player : world.getPlayers()) {
        player.sendMessage(Message.raw("Individual message"));
    }
}
```

---

## Configuration Classes

### GameplayConfig
**Package:** `com.hypixel.hytale.server.core.asset.type.gameplay`

Master configuration class containing all gameplay settings for a world. Implements `JsonAssetWithMap`.

#### Getting the Config
```java
// From World
GameplayConfig config = world.getGameplayConfig();

// From asset store
GameplayConfig config = GameplayConfig.getAssetMap().get("default");
```

#### Key Methods
```java
// Identity
String getId()

// Sub-configs
WorldConfig getWorldConfig()
DeathConfig getDeathConfig()
CombatConfig getCombatConfig()
GatheringConfig getGatheringConfig()
WorldMapConfig getWorldMapConfig()
ItemDurabilityConfig getItemDurabilityConfig()
ItemEntityConfig getItemEntityConfig()
RespawnConfig getRespawnConfig()
PlayerConfig getPlayerConfig()
CameraEffectsConfig getCameraEffectsConfig()
CraftingConfig getCraftingConfig()
SpawnConfig getSpawnConfig()

// Settings
boolean getShowItemPickupNotifications()
int getMaxEnvironmentalNPCSpawns()
String getCreativePlaySoundSet()
int getCreativePlaySoundSetIndex()

// Plugin extensions
MapKeyMapCodec.TypeMap<Object> getPluginConfig()
```

#### Constants
```java
static final String DEFAULT_ID;           // Default config ID
static final GameplayConfig DEFAULT;      // Default config instance
```

---

### WorldConfig
**Package:** `com.hypixel.hytale.server.core.asset.type.gameplay`

Configuration for world-specific gameplay settings like block rules and day/night cycle.

> **Note: two distinct `WorldConfig` classes exist.** The gameplay settings below
> (`isBlockBreakingAllowed`, `getSleepConfig`, day/night durations, `DEFAULT_*_DURATION_SECONDS`)
> live on `com.hypixel.hytale.server.core.asset.type.gameplay.WorldConfig`, reached via
> `world.getGameplayConfig().getWorldConfig()`. The separate `World.getWorldConfig()` method
> returns a *different* class, `com.hypixel.hytale.server.core.universe.world.WorldConfig`,
> which does **not** expose these gameplay accessors. (The universe `WorldConfig` is where
> `get/setSpawnProvider` live — see [Controlling Respawn Location](#controlling-respawn-location).)

#### Key Methods
```java
// Block rules
boolean isBlockBreakingAllowed()
boolean isBlockGatheringAllowed()
boolean isBlockPlacementAllowed()
float getBlockPlacementFragilityTimer()

// Day/night cycle
int getDaytimeDurationSeconds()
int getNighttimeDurationSeconds()
int getTotalMoonPhases()

// Sleep
SleepConfig getSleepConfig()
```

#### Constants
```java
static final int DEFAULT_TOTAL_DAY_DURATION_SECONDS;
static final int DEFAULT_DAYTIME_DURATION_SECONDS;
static final int DEFAULT_NIGHTTIME_DURATION_SECONDS;
```

#### Usage Example
```java
// Gameplay WorldConfig is reached through the gameplay config, not world.getWorldConfig()
WorldConfig config = world.getGameplayConfig().getWorldConfig();

if (config.isBlockBreakingAllowed()) {
    // Players can break blocks
}

int dayLength = config.getDaytimeDurationSeconds();
int nightLength = config.getNighttimeDurationSeconds();
```

---

### DeathConfig
**Package:** `com.hypixel.hytale.server.core.asset.type.gameplay`

Configuration for death and respawn behavior.

#### Key Methods
```java
// Respawn
RespawnController getRespawnController()

// Item loss on death
ItemsLossMode getItemsLossMode()
double getItemsAmountLossPercentage()
double getItemsDurabilityLossPercentage()
```

#### ItemsLossMode Enum

| Value | Description |
|-------|-------------|
| (values defined in DeathConfig$ItemsLossMode) | Controls how items are lost on death |

#### Usage Example
```java
DeathConfig config = world.getDeathConfig();

ItemsLossMode lossMode = config.getItemsLossMode();
double lossPercent = config.getItemsAmountLossPercentage();
```

#### Respawn flow

`getRespawnController()` returns the policy that decides where a dead player reappears. Two built-ins
exist (`com.hypixel.hytale.server.core.asset.type.gameplay.respawn`):

| Controller | Behavior |
|------------|----------|
| `HomeOrSpawnPoint` (default) | Uses the player's personal respawn point if set, else the world spawn provider |
| `WorldSpawnPoint` | Always uses the world spawn provider |

Both ultimately delegate placement to the world's **spawn provider**, which is the seam to override —
see below.

---

### Controlling Respawn Location

To control where players spawn (and respawn), install an `ISpawnProvider` rather than teleporting
players manually. The respawn controller calls the provider and adds the `Teleport` component itself,
so there is no manual-teleport race.

**Package:** `com.hypixel.hytale.server.core.universe.world.spawn` (note: *not* under
`asset.type.gameplay.respawn`). The provider lives on the **universe** `WorldConfig`
(`World.getWorldConfig()`), distinct from the gameplay `WorldConfig`/`DeathConfig` above:

```java
world.getWorldConfig().setSpawnProvider(provider);   // universe.world.WorldConfig
```

The interface has several overloads, but the only one you must implement is
`Transform getSpawnPoint(World, UUID)` — the default `getSpawnPoint(Ref, ComponentAccessor)` and
`getSpawnPoint(Entity)` overloads resolve the UUID/World for you and delegate to it.

```java
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.ISpawnProvider;
import java.util.UUID;

public class ArenaSpawnProvider implements ISpawnProvider {
    @Override
    public Transform getSpawnPoint(World world, UUID player) {
        return pickSpawn(player);   // your placement logic
    }

    @Override public Transform[] getSpawnPoints() { return new Transform[0]; } // deprecated, still abstract
    @Override public boolean isWithinSpawnDistance(com.hypixel.hytale.math.vector.Vector3d p, double d) { return true; }
}
```

Built-ins worth referencing instead of rolling your own:

| Provider | Use |
|----------|-----|
| `GlobalSpawnProvider(Transform)` | One fixed spawn for everyone |
| `IndividualSpawnProvider(Transform[])` | Round-robins / assigns from a set of points |
| `FitToHeightMapSpawnProvider(ISpawnProvider)` | Wraps another provider and ground-snaps a sentinel `y < 0` to the terrain height |

> **⚠️ `getSpawnPoint` is polled, not called once.** It can be invoked repeatedly while the death
> screen is open, not only at the instant of respawn. A provider that returns a *fresh random* point
> each call makes the spawn visibly jitter every tick. Compute once and **cache per player** (keyed on
> the `UUID`), invalidating the cache on respawn (e.g. from a `RespawnSystems.OnRespawnSystem` — see
> [combat.md → Reacting to Death & Respawn](combat.md#reacting-to-death--respawn)).

Because no world exists at plugin `setup()` time, install the provider per-world from a
`StartWorldEvent` handler — see [World Events](#world-events) below.

---

## ClientFeature
**Package:** `com.hypixel.hytale.protocol.packets.setup`

Enum defining client-side features that can be enabled or disabled per world.

### Values

| Value | Description |
|-------|-------------|
| `SplitVelocity` | Split velocity calculations |
| `Mantling` | Allow mantling/climbing over obstacles |
| `SprintForce` | Sprint force mechanics |
| `CrouchSlide` | Crouch sliding movement |
| `SafetyRoll` | Safety roll on landing |
| `DisplayHealthBars` | Show health bars over entities |
| `DisplayCombatText` | Show combat damage numbers |

### Methods
```java
static ClientFeature[] values()
static ClientFeature valueOf(String name)
int getValue()
static ClientFeature fromValue(int value)
```

### Usage Example
```java
World world = ...;

// Check if a feature is enabled
if (world.isFeatureEnabled(ClientFeature.DisplayHealthBars)) {
    // Health bars are visible
}

// Enable/disable features
world.registerFeature(ClientFeature.DisplayCombatText, true);
world.registerFeature(ClientFeature.CrouchSlide, false);

// Broadcast changes to all players
world.broadcastFeatures();
```

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

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 world system (verified against `HytaleServer.jar`).

- **`Player is already in a world`** → you called `addPlayer()` for a `PlayerRef` that is already in a world. Fix: remove it from its current world first, or skip the add.
- **`Entity is already in a world!`** → `addEntity()` was called on an entity already added to a world. Fix: add each entity once; check before re-adding.
- **`Entity is already not in a world!`** → a remove was called on an entity that is not in any world. Fix: guard the removal so it only runs for entities currently in a world.
- **`This world has already been shutdown!`** → an operation ran against a world that was already shut down. Fix: stop touching the world reference after shutdown.
- **`Cannot demote empty chunk section!`** → a chunk-palette/section operation ran against an empty section. Fix: operate on a loaded chunk section with content; verify the chunk is loaded first (e.g. `getChunkIfLoaded()` returns non-null).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
