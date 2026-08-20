---
title: "World API"
description: "Work with the Hytale World in Java — the World tick thread exposing players, entities, chunks, and ECS stores, per-chunk block/state/terrain access, and per-player chunk loading."
seo:
  type: TechArticle
---

# World API

**Doc type:** Java API · **Verified against 0.5.9**

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
| `SetBlockSettings` | `server.core.universe.world` | Bit flags controlling `setBlock`/`breakBlock` side effects |
| `ChunkAccessor` / `LocalCachedChunkAccessor` | `server.core.universe.world.accessor` | World-coordinate block access; cached accessor for area edits |
| `ChunkColumn` / `BlockSection` / `FluidSection` | `server.core.universe.world.chunk(.section)` | ECS chunk-column component and per-section block/fluid storage |
| `GetChunkFlags` | `server.core.universe.world.storage` | Bit flags for async chunk loading via `ChunkStore` |
| `WorldTimeResource` | `server.core.modules.time` | Per-world game clock resource (time of day, moon phase, sun) |
| `MapMarkerBuilder` / `MarkersCollector` | `server.core.universe.world.worldmap.markers` | Building and collecting world-map markers |
| `PlayerUtil` | `server.core.universe.world` | Static broadcast helpers (messages/packets to players) |

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
List<Player> getPlayers()          // @Deprecated(forRemoval=true) — prefer getPlayerRefs()
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
<T extends Entity> T spawnEntity(T entity, Vector3d position, Rotation3f rotation)
<T extends Entity> T addEntity(T entity, Vector3d position, Rotation3f rotation, AddReason reason)
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

## SetBlockSettings
**Package:** `com.hypixel.hytale.server.core.universe.world`

Bit-flag constants for the `int settings` (a.k.a. `flags`) parameter accepted by every block-writing method: `WorldChunk.setBlock(...)`, the `BlockAccessor` `setBlock`/`breakBlock`/`placeBlock` overloads, and the [chunk accessor](#chunk-accessors) `setBlock(x, y, z, blockTypeKey, settings)` defaults. Combine with bitwise OR. `NONE` (0) runs the full default side-effect pipeline — most flags *suppress* a side effect, while `PHYSICS`, `FORCE_CHANGED`, and `PERFORM_BLOCK_UPDATE` *opt in* to extra behavior.

| Constant | Value | Effect |
|----------|-------|--------|
| `NONE` | 0 | Default behavior (all side effects; no neighbor block update) |
| `NO_NOTIFY` | 1 | Suppress the block-changed notification |
| `NO_UPDATE_STATE` | 2 | Skip block-state update — the block type's block entity components are not attached/replaced |
| `NO_SEND_PARTICLES` | 4 | Skip break/place particles |
| `NO_SET_FILLER` | 8 | Don't place filler blocks for multi-block types |
| `NO_BREAK_FILLER` | 16 | Don't remove existing filler blocks (`breakBlock` also skips redirecting to the base block) |
| `PHYSICS` | 32 | Mark the change as physics-caused (changes the particle and filler-removal behavior) |
| `FORCE_CHANGED` | 64 | Run the side-effect pipeline even if block id + rotation are unchanged (invalidates the block) |
| `NO_UPDATE_NEIGHBOR_CONNECTIONS` | 128 | Skip updating neighbor block connections |
| `PERFORM_BLOCK_UPDATE` | 256 | Trigger a neighbor block update around the changed block |
| `NO_UPDATE_HEIGHTMAP` | 512 | Skip the heightmap update |
| `NO_SEND_AUDIO` | 1024 | Skip break/place audio |
| `NO_DROP_ITEMS` | 2048 | Skip item drops when breaking |

The decompiled `WorldChunk.setBlock` pipeline consumes `NO_UPDATE_STATE`, `NO_SEND_PARTICLES`, `NO_SET_FILLER`, `NO_BREAK_FILLER`, `PHYSICS`, `FORCE_CHANGED`, `PERFORM_BLOCK_UPDATE`, and `NO_UPDATE_HEIGHTMAP` directly; the notify/connections/audio/drops flags are honored by the higher-level breaking and interaction paths.

### Usage Example
```java
import com.hypixel.hytale.server.core.universe.world.SetBlockSettings;

// Replace a block without particles, then update its neighbors
chunk.setBlock(x, y, z, newBlockId, newBlockType, 0, 0,
        SetBlockSettings.NO_SEND_PARTICLES | SetBlockSettings.PERFORM_BLOCK_UPDATE);

// Break a block without dropping items (World implements ChunkAccessor — see below)
world.breakBlock(x, y, z, SetBlockSettings.NO_DROP_ITEMS);
```

---

## Chunk Accessors
**Package:** `com.hypixel.hytale.server.core.universe.world.accessor`

The accessor interfaces provide **world-coordinate** block access that spans chunk boundaries — each default method resolves the owning chunk from the block coordinates and delegates to it. **`World` implements `ChunkAccessor<WorldChunk>`**, so all of these methods can be called directly on a `World`.

```
IChunkAccessorSync<WorldChunk>       @Deprecated base: chunk getters + block defaults
└── ChunkAccessor<WorldChunk>        adds fluid lookup + neighbor block updates   ← implemented by World
    └── OverridableChunkAccessor<X>  adds overwrite()
        └── LocalCachedChunkAccessor caching implementation for area edits
```

### IChunkAccessorSync

The (deprecated, but still load-bearing) base interface. Chunk getters are keyed by chunk index (`ChunkUtil.indexChunkFromBlock(x, z)`); block methods take world coordinates:

```java
// Chunk getters
WorldChunk getChunk(long chunkIndex)
WorldChunk getNonTickingChunk(long chunkIndex)
WorldChunk getChunkIfInMemory(long chunkIndex)
WorldChunk loadChunkIfInMemory(long chunkIndex)
WorldChunk getChunkIfLoaded(long chunkIndex)
WorldChunk getChunkIfNonTicking(long chunkIndex)

// Block access (default methods, world coordinates)
int getBlock(int x, int y, int z)
int getBlock(Vector3i pos)
BlockType getBlockType(int x, int y, int z)
BlockType getBlockType(Vector3i pos)
void setBlock(int x, int y, int z, String blockTypeKey)
void setBlock(int x, int y, int z, String blockTypeKey, int settings)   // SetBlockSettings flags
boolean breakBlock(int x, int y, int z, int settings)
boolean testBlockTypes(int x, int y, int z, BlockType type, int rotation, TestBlockFunction predicate)
boolean testPlaceBlock(int x, int y, int z, BlockType type, int rotation)
boolean testPlaceBlock(int x, int y, int z, BlockType type, int rotation, TestBlockFunction predicate)
Holder<ChunkStore> getBlockComponentHolder(int x, int y, int z)
void setBlockInteractionState(Vector3i pos, BlockType type, String state)
int getBlockRotationIndex(int x, int y, int z)
BlockPosition getBaseBlock(BlockPosition position)   // @Deprecated(forRemoval=true)
```

The nested functional interface `IChunkAccessorSync.TestBlockFunction` is the predicate used by the `test*` methods: `boolean test(int, int, int, BlockType, int, int)`.

### ChunkAccessor

Extends `IChunkAccessorSync` with:

```java
int getFluidId(int x, int y, int z)
boolean performBlockUpdate(int x, int y, int z)                          // = performBlockUpdate(x, y, z, true)
boolean performBlockUpdate(int x, int y, int z, boolean allowPartialLoad) // update the 3x3 chunk-local area
```

### OverridableChunkAccessor

Extends `ChunkAccessor` with a single method:

```java
void overwrite(X chunk)   // inject/replace a chunk in the accessor's view
```

### LocalCachedChunkAccessor

A concrete `OverridableChunkAccessor<WorldChunk>` that caches the chunks of a square area in a flat array, so repeated block reads/writes during an area edit skip the world's chunk lookup. This is what the built-in builder tools and farming systems use for multi-block operations.

```java
// Factories (delegate is usually the World itself)
static LocalCachedChunkAccessor atWorldCoords(ChunkAccessor<WorldChunk> delegate, int centerX, int centerZ, int blockRadius)
static LocalCachedChunkAccessor atChunkCoords(ChunkAccessor<WorldChunk> delegate, int chunkX, int chunkZ, int chunkRadius)
static LocalCachedChunkAccessor atChunk(ChunkAccessor<WorldChunk> delegate, WorldChunk center, int chunkRadius)

void cacheChunksInRadius()          // pre-populate the cache from the delegate
void overwrite(WorldChunk chunk)    // place a chunk into its cache slot
ChunkAccessor getDelegate()
int getMinX()                       // min chunk X of the cached square
int getMinZ()
int getLength()                     // side length in chunks (2 * radius + 1)
int getCenterX()
int getCenterZ()

// Extra chunk-coordinate getters on top of the accessor family
WorldChunk getChunkIfInMemory(int x, int z)
WorldChunk getChunkIfLoaded(int x, int z)
```

#### Usage Example
```java
// Cache all chunks within `range` blocks of (x, z), then edit through the accessor
LocalCachedChunkAccessor accessor = LocalCachedChunkAccessor.atWorldCoords(world, x, z, range);
for (/* each block in the edit */) {
    accessor.setBlock(bx, by, bz, "stone", SetBlockSettings.NONE);
}
```

---

## GetChunkFlags
**Package:** `com.hypixel.hytale.server.core.universe.world.storage`

Bit-flag constants for the `int flags` parameter of the `ChunkStore` async loaders — `ChunkStore.getChunkReferenceAsync(long, int)` and `ChunkStore.getChunkSectionReferenceAsync(int, int, int, int)`:

| Constant | Value | Effect |
|----------|-------|--------|
| `NONE` | 0 | Default: load from disk or generate as needed |
| `NO_LOAD` | 1 | Don't load the chunk from disk |
| `NO_GENERATE` | 2 | Don't generate the chunk if missing |
| `SET_TICKING` | 4 | Mark the chunk as ticking once available |
| `BYPASS_LOADED` | 8 | Internal load-scheduling flag |
| `POLL_STILL_NEEDED` | 16 | Internal load-scheduling flag |
| `NO_SET_TICKING_SYNC` | `Integer.MIN_VALUE` | Internal: don't set ticking synchronously |

`NO_LOAD | NO_GENERATE` restricts the request to chunks already in memory.

---

## Chunk Columns & Sections
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk` (and `.section`, `.environment`, `.palette`)

Underneath `WorldChunk`, chunk data lives in the ECS: each chunk column is an entity in the `ChunkStore`, and its `ChunkColumn` component holds references to per-**section** entities (one per 32-block vertical slice) that carry the actual `BlockSection` / `FluidSection` storage. Plugins reach them via the component API:

```java
Store<ChunkStore> chunkStore = world.getChunkStore().getStore();
ChunkColumn column = chunkStore.getComponent(chunk.getReference(), ChunkColumn.getComponentType());
Ref<ChunkStore> section = column.getSection(ChunkUtil.chunkCoordinate(blockY));
FluidSection fluids = chunkStore.ensureAndGetComponent(section, FluidSection.getComponentType());
```

### ChunkColumn

Component mapping a chunk column to its section entities.

```java
static ComponentType<ChunkStore, ChunkColumn> getComponentType()

Ref<ChunkStore> getSection(int sectionY)    // sectionY = ChunkUtil.chunkCoordinate(blockY)
Ref<ChunkStore>[] getSections()
Holder<ChunkStore>[] getSectionHolders()
Holder<ChunkStore>[] takeSectionHolders()
void putSectionHolders(Holder<ChunkStore>[] holders)
```

### BlockSection

Palette-compressed block storage for one 32×32×32 section: block ids, filler ids, rotations, ticking-block bookkeeping, and light data. Local coordinates or a packed block index address the same data.

> **⚠️ Prefer `WorldChunk.setBlock` / the accessors for writes.** `BlockSection.set` writes the raw palette only — no heightmap, lighting, filler, block-entity, or notification side effects run. It is the right tool for bulk analysis and for migration/worldgen-style code, not for gameplay edits.

```java
static ComponentType<ChunkStore, BlockSection> getComponentType()

// Reads
int get(int x, int y, int z)
int get(int index)
int getFiller(int x, int y, int z)
int getRotationIndex(int x, int y, int z)
RotationTuple getRotation(int x, int y, int z)

// Raw writes (no side effects — see warning above)
boolean set(int blockIdx, int blockId, int rotation, int filler)
boolean set(int x, int y, int z, int blockId, int rotation, int filler)

// Content queries
boolean contains(int blockId)
boolean containsAny(IntList blockIds)
int count()                      // non-air blocks in the section
int count(int blockId)
IntSet values()                  // distinct block ids present
Int2ShortMap valueCounts()
void forEachValue(IntConsumer consumer)
boolean isSolidAir()

// Ticking blocks
boolean setTicking(int blockIdx, boolean ticking)
boolean setTicking(int x, int y, int z, boolean ticking)
boolean isTicking(int blockIdx)
boolean isTicking(int x, int y, int z)
boolean hasTicking()
int getTickingBlocksCount()
void scheduleTick(int index, Instant gameTime)

// Lighting (see ChunkLightData below)
ChunkLightData getLocalLight()
ChunkLightData getGlobalLight()
boolean hasLocalLight()
boolean hasGlobalLight()
void invalidateLocalLight()
void invalidateGlobalLight()

// Misc
double getMaximumHitboxExtent()
IntOpenHashSet getAndClearChangedPositions()
```

### FluidSection

Per-section fluid storage: a fluid-type palette plus a per-block fluid level. See the same `ChunkColumn` retrieval pattern above (`ensureAndGetComponent` creates the component on sections that have no fluids yet).

```java
static ComponentType<ChunkStore, FluidSection> getComponentType()

boolean setFluid(int x, int y, int z, Fluid fluid, byte level)
boolean setFluid(int x, int y, int z, int fluidId, byte level)   // fluidId 0 + level 0 clears
Fluid getFluid(int x, int y, int z)
int getFluidId(int x, int y, int z)
byte getFluidLevel(int x, int y, int z)
boolean isEmpty()
int getX(); int getY(); int getZ()   // section coordinates
```

### ChunkLightData

Immutable snapshot of a section's light: four 4-bit channels (red, green, blue block light + sky light) stored in an octree. Obtained from `BlockSection.getLocalLight()` / `getGlobalLight()`.

```java
byte getRedBlockLight(int x, int y, int z)
byte getGreenBlockLight(int x, int y, int z)
byte getBlueBlockLight(int x, int y, int z)
byte getBlockLightIntensity(int x, int y, int z)   // max of R/G/B
short getBlockLight(int x, int y, int z)           // packed RGB
byte getSkyLight(int x, int y, int z)
byte getLight(int index, int channel)              // RED_CHANNEL..SKY_CHANNEL
short getLightRaw(int x, int y, int z)             // all four channels packed

static short combineLightValues(byte red, byte green, byte blue, byte sky)
static byte getLightValue(short packed, int channel)
```

Constants: `EMPTY` (the all-zero instance), `MAX_VALUE` (15 per channel), `CHANNEL_COUNT` (4), and the channel indices `RED_CHANNEL`/`GREEN_CHANNEL`/`BLUE_CHANNEL`/`SKY_CHANNEL`.

### Supporting classes

| Class | Package | Description |
|-------|---------|-------------|
| `EnvironmentChunk` | `...world.chunk.environment` | Chunk-column component storing per-column environment values (`get(x, y, z)`, `set(x, y, z, value)`, `getComponentType()`); columns are run-length `EnvironmentColumn`s |
| `ShortBytePalette` | `...world.chunk.palette` | Palette-compressed 1024-entry (`LENGTH`, 32×32) short grid — `set`/`get`/`contains`/`optimize`/`copyFrom`; used for per-column data such as the heightmap |
| `AbstractCachedAccessor` | `...world.chunk` | Base class for systems that cache chunk/section `Ref`s over an area — `getChunk(x, z)`, `getSection(x, y, z)` (used by the block-physics systems) |
| `BlockRotationUtil` | `...world.chunk` | Static rotation math: `getRotated(RotationTuple, Axis, Rotation, VariantRotation)`, `getFlipped(RotationTuple, BlockFlipType, Axis)`, `getRotatedFiller(int, RotationTuple)`, `getFlippedFiller(int, Axis)` |

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

## PlayerUtil
**Package:** `com.hypixel.hytale.server.core.universe.world`

Static helpers for broadcasting to the players of a world's `EntityStore`. Useful from systems that need to notify every player — or only the players who can currently see a given entity.

```java
// Run a callback for each player whose entity tracker can see `entityRef`
static void forEachPlayerThatCanSeeEntity(Ref<EntityStore> entityRef,
        TriConsumer<Ref<EntityStore>, PlayerRef, ComponentAccessor<EntityStore>> callback,
        ComponentAccessor<EntityStore> accessor)

// Broadcast a chat message to all players; players who have hidden
// sourcePlayerUuid (nullable) are skipped
static void broadcastMessageToPlayers(UUID sourcePlayerUuid, Message message, Store<EntityStore> store)

// Broadcast raw packets to all players in the store
static void broadcastPacketToPlayers(ComponentAccessor<EntityStore> accessor, ToClientPacket packet)
static void broadcastPacketToPlayers(ComponentAccessor<EntityStore> accessor, ToClientPacket... packets)
static void broadcastPacketToPlayersNoCache(ComponentAccessor<EntityStore> accessor, ToClientPacket packet)

// Force a player's model to be rebuilt/resent
static void resetPlayerModel(Ref<EntityStore> playerRef, ComponentAccessor<EntityStore> accessor)
```

### Usage Example
```java
// Send an animation packet only to players who can see the entity
PlayerUtil.forEachPlayerThatCanSeeEntity(ref,
        (playerEntityRef, playerRef, accessor) ->
                playerRef.getPacketHandler().write(animationPacket),
        store);
```

For a plain world-wide chat broadcast, `world.sendMessage(Message msg)` (above) is simpler.

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

    // Get all players (getPlayerRefs() — getPlayers() is deprecated for removal)
    for (PlayerRef ref : world.getPlayerRefs()) {
        ref.sendMessage(Message.raw("Individual message"));
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
    @Override public boolean isWithinSpawnDistance(org.joml.Vector3d p, double d) { return true; }
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

> **⚠️ `getSpawnPoint` runs OFF the world thread — reading the `Store` there crashes the join.**
> The engine invokes it from `World.addPlayer` (→ `SpawnUtil.applyFirstSpawnTransform`) on a
> **`ServerWorkerGroup`** thread, not the world thread. Any `Store` read inside the provider —
> `Store.forEachChunk(...)`, `World.getNonTickingChunk(...)`, component reads — hits
> `Store.assertThread` and throws `IllegalStateException: Assert not in thread!`. The server then
> logs `SEVERE … Exception when player adding to universe` and disconnects the client with
> `client.general.disconnect.universeException`, which the client shows as a **blank loading screen**
> (`Server closed connection (code=0)` after everything reports "Prepared"). If the provider caches
> per-`UUID`, the *first* joiner populates the cache off-thread without reading the store and joins
> fine, so the crash only fires on the **second** joiner — "works solo, kicks the 2nd player" is the
> signature. To read the store from a provider, marshal onto the world thread (`World` implements
> `Executor`; `Store.isInThread()` detects whether you are already on it — guard to avoid self-deadlock):
>
> ```java
> private Transform computeSpawn(World world, UUID uuid) {
>     if (world.getChunkStore().getStore().isInThread()) {
>         return computeOnThread(world, uuid);   // already on the world thread
>     }
>     CompletableFuture<Transform> r = new CompletableFuture<>();
>     world.execute(() -> {                       // queue onto the world thread, block for the result
>         try { r.complete(computeOnThread(world, uuid)); }
>         catch (Throwable t) { r.completeExceptionally(t); }
>     });
>     return r.join();
> }
> ```
>
> This applies more broadly: engine **callbacks** (spawn providers, and likely other connection/setup
> hooks) may run on a `ServerWorkerGroup` thread, where touching a `Store` throws. Ticking **Systems**
> always run on the world thread and are safe; engine callbacks are not.

Because no world exists at plugin `setup()` time, install the provider per-world from a
`StartWorldEvent` handler — see [World Events](#world-events) below.

---

## World Time
**Package:** `com.hypixel.hytale.server.core.modules.time`

Two ECS **resources** on the world's `EntityStore` hold time state. Retrieve them with `store.getResource(...)` from any system running on the world thread.

### WorldTimeResource

The per-world game clock: time of day, calendar date, moon phase, and sun position. This is what ticking systems read to gate day/night behavior, and what you set to change the world's time.

```java
static ResourceType<EntityStore, WorldTimeResource> getResourceType()

// Reading time
Instant getGameTime()
LocalDateTime getGameDateTime()
int getCurrentHour()
float getDayProgress()               // 0.0–1.0 through the current day
double getSunlightFactor()
Vector3d getSunDirection()
boolean isDayTimeWithinRange(double minTime, double maxTime)   // 0–1 fractions; wraps midnight
boolean isScaledDayTimeWithinRange(double minTime, double maxTime)
boolean isYearWithinRange(double min, double max)

// Setting time (broadcasts the update to clients)
void setGameTime(Instant gameTime, World world, ComponentAccessor<EntityStore> accessor)
void setDayTime(double dayTime, World world, ComponentAccessor<EntityStore> accessor)  // 0.0–1.0; rolls forward, never backward

// Moon phase (see MoonPhaseChangeEvent above)
int getMoonPhase()
void setMoonPhase(int phase, ComponentAccessor<EntityStore> accessor)
void updateMoonPhase(World world, ComponentAccessor<EntityStore> accessor)
boolean isMoonPhaseWithinRange(World world, int min, int max)

// Client sync
void broadcastTimePacket(ComponentAccessor<EntityStore> accessor)
void sendTimePackets(PlayerRef playerRef)

// Statics
static double getSecondsPerTick(World world)
```

Useful constants: `SECONDS_PER_DAY`, `HOURS_PER_DAY`, `DAYS_PER_YEAR`, `DAYTIME_PORTION_PERCENTAGE` (0.6 — daylight fraction of a day), `DAYTIME_SECONDS`, `NIGHTTIME_SECONDS`, `SUNRISE_SECONDS`.

#### Usage Example
```java
WorldTimeResource time = store.getResource(WorldTimeResource.getResourceType());

// Gate behavior on night time (0.75 = midnight-ish, wrapping ranges supported)
if (time.isDayTimeWithinRange(0.7, 0.3)) { /* it's night */ }

// Skip to the next morning
time.setDayTime(0.25, world, store);
```

The day/night *durations* come from the gameplay config — see `getDaytimeDurationSeconds()` / `getNighttimeDurationSeconds()` under [WorldConfig](#worldconfig).

### TimeResource

The tick-advanced wall clock (an `Instant` moved forward each tick, scaled by the time-dilation modifier). `World.setTimeDilation(float, ComponentAccessor)` (see [Configuration](#configuration)) validates the range (0.01–4.0], writes `setTimeDilationModifier`, and syncs clients.

```java
static ResourceType<EntityStore, TimeResource> getResourceType()

Instant getNow()
void setNow(Instant now)
void add(Duration duration)
void add(long amount, TemporalUnit unit)
float getTimeDilationModifier()
void setTimeDilationModifier(float modifier)
```

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

## World Map Markers
**Package:** `com.hypixel.hytale.server.core.universe.world.worldmap.markers`

Plugins add markers to the in-game world map by registering a **marker provider** on the world's `WorldMapManager` (`world.getWorldMapManager()`). The engine calls every registered provider when it refreshes a player's map, passing a `MarkersCollector` to fill. Built-in providers supply the spawn, death, respawn, other-player, and POI markers.

### WorldMapManager.MarkerProvider

```java
// Nested interface WorldMapManager$MarkerProvider — the extension point
void update(World world, Player player, MarkersCollector collector)

// Registration (WorldMapManager)
void addMarkerProvider(String key, WorldMapManager.MarkerProvider provider)
Map<String, WorldMapManager.MarkerProvider> getMarkerProviders()
```

### MapMarkerBuilder

Builder for the `MapMarker` packet objects a provider adds to the collector:

```java
MapMarkerBuilder(String id, String image, Transform transform)   // image e.g. "Spawn.png"

MapMarkerBuilder withName(Message name)
MapMarkerBuilder withCustomName(String name)
MapMarkerBuilder withContextMenuItem(ContextMenuItem item)
MapMarkerBuilder withComponent(MapMarkerComponent component)
MapMarker build()
```

### MarkersCollector

Passed to `update()`; collects the markers for the player currently being refreshed:

```java
void add(MapMarker marker)                        // respects map view distance
void addIgnoreViewDistance(MapMarker marker)
boolean isInViewDistance(Transform transform)
boolean isInViewDistance(Vector3d position)
boolean isInViewDistance(double x, double z)
Predicate<PlayerRef> getPlayerMapFilter()
```

### Usage Example

Modeled on the built-in `SpawnMarkerProvider`:

```java
import com.hypixel.hytale.server.core.universe.world.worldmap.WorldMapManager;
import com.hypixel.hytale.server.core.universe.world.worldmap.markers.MapMarkerBuilder;
import com.hypixel.hytale.server.core.universe.world.worldmap.markers.MarkersCollector;

public class ArenaMarkerProvider implements WorldMapManager.MarkerProvider {
    @Override
    public void update(World world, Player player, MarkersCollector collector) {
        collector.add(new MapMarkerBuilder("Arena", "Spawn.png", new Transform(arenaCenter))
                .withCustomName("The Arena")
                .build());
    }
}

// Register per world, e.g. from a StartWorldEvent handler (see World Events below):
world.getWorldMapManager().addMarkerProvider("arena", new ArenaMarkerProvider());
```

---

## World Paths
**Package:** `com.hypixel.hytale.server.core.universe.world.path`

Named waypoint paths stored per world (loaded into the `WorldPathConfig` reachable via `world.getWorldPathConfig()`); NPC behaviors use them for patrol routes.

```java
// IPath<Waypoint extends IPathWaypoint>
UUID getId()
String getName()
List<Waypoint> getPathWaypoints()
int length()
Waypoint get(int index)

// IPathWaypoint
int getOrder()
Vector3d getWaypointPosition(ComponentAccessor<EntityStore> accessor)
Rotation3f getWaypointRotation(ComponentAccessor<EntityStore> accessor)
double getPauseTime()
float getObservationAngle()
```

`SimplePathWaypoint(int order, Transform transform)` is the ready-made fixed-position `IPathWaypoint` implementation (position/rotation from the transform; pause time and observation angle 0).

---

## Other World Classes

| Class | Package | Description |
|-------|---------|-------------|
| `ValidationOption` | `server.core.universe.world` | Enum of prefab-validation checks — `PHYSICS`, `BLOCKS`, `BLOCK_STATES`, `ENTITIES`, `BLOCK_FILLER`; consumed by `PrefabBufferValidator.validate` / `validateAllPrefabs` / `validatePrefabsInPath` |
| `INonPlayerCharacter` | `server.core.universe.world.npc` | Minimal NPC handle — `getNPCTypeId()`, `getNPCTypeIndex()`; returned (paired with the entity `Ref`) by `NPCPlugin.spawnNPC` |
| `WorldLocationCondition` | `server.core.universe.world.worldlocationcondition` | Abstract JSON-polymorphic position predicate — `test(World, x, y, z)`; subtypes register on its `CodecMapCodec` `CODEC` (the adventure plugin registers `"NeighbourBlockTags"` → `NeighbourBlockTagsLocationCondition`); consumed by treasure-map objectives, spawn-beacon objectives, and farming spread |

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
