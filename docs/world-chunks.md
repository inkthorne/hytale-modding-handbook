---
title: "World Chunks"
description: "Hytale's per-chunk Java API — the WorldChunk component, chunk accessors and columns/sections, block-write settings flags, chunk flags, and per-player chunk tracking with ChunkTracker."
seo:
  type: TechArticle
---

# World Chunks

**Doc type:** Java API · **Verified against 0.6.3**

Split out of [world.md](world.md) at the 2026-09-04 seam. The chunk half of the World API: the `WorldChunk` component and its block, state and terrain access; the accessor and column/section layers beneath it; the settings flags every block-writing method takes; and `ChunkTracker`, which decides what each player has loaded. The `World` object that owns all of this stays in [world.md](world.md), and the chunk **events** are in [world-lifecycle-events.md](world-lifecycle-events.md).

---

## WorldChunk
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk`

Represents a chunk column in the world. Implements `Component<ChunkStore>`. Provides direct access to block data, states, and chunk properties. (The `BlockAccessor` interface it used to implement was removed by 0.6.3; the `setBlock`/`breakBlock` convenience overloads it contributed now live directly on `WorldChunk` — see below.)

### Getting the ComponentType
```java
static ComponentType<ChunkStore, WorldChunk> getComponentType()
```

### Block Access
```java
// Get block ID / type at local coordinates (0-31 for x/z, 0-319 for y — ChunkUtil.HEIGHT is 320)
int getBlock(int x, int y, int z)
BlockType getBlockType(int x, int y, int z)
BlockType getBlockType(Vector3ic localPos)

// Full-control write at local coordinates (settings = SetBlockSettings flags)
boolean setBlock(int x, int y, int z, int blockId,
                 BlockType blockType, int rotation, int filler, int settings)

// Convenience overloads (0.6.3+, moved here from the removed BlockAccessor interface);
// the forms without `settings` pass SetBlockSettings.NONE
boolean setBlock(int x, int y, int z, String blockTypeKey)
boolean setBlock(int x, int y, int z, String blockTypeKey, int settings)
boolean setBlock(int x, int y, int z, int blockId)
boolean setBlock(int x, int y, int z, int blockId, int settings)
boolean setBlock(int x, int y, int z, BlockType blockType)
boolean setBlock(int x, int y, int z, BlockType blockType, int settings)
boolean breakBlock(int x, int y, int z, int settings)
boolean breakBlock(int x, int y, int z, int filler, int settings)

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

// Switch a block's interaction state (0.6.3+ on WorldChunk; also on the accessors)
void setBlockInteractionState(Vector3i localPos, BlockType type, String state)
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

// Tint lookup moved off WorldChunk by 0.6.3 — read it from the block-data component:
//   chunk.getBlockChunk().getTint(x, z)

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
// (getChunkAccessor() was removed by 0.6.3 — the owning World implements ChunkAccessor; use getWorld())
```

### Chunk Flags
```java
// Check/set chunk flags
boolean is(ChunkFlag flag)
void setFlag(ChunkFlag flag, boolean value)
void initFlags()
// not(ChunkFlag) and toggleFlag(ChunkFlag) were removed by 0.6.3 — use !is(flag) / setFlag(flag, !is(flag))
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
// Lighting updates (the isLightingUpdatesEnabled() getter was removed by 0.6.3)
void setLightingUpdatesEnabled(boolean enabled)
```

### Chunk Components
```java
// Get the block-data component (heightmap, tints, environment, section refs)
BlockChunk getBlockChunk()
// getBlockComponentChunk() / getEntityChunk() were removed by 0.6.3: BlockComponentChunk and EntityChunk
// are now bare serialization carriers (takeEntityHolders()) with no runtime lookup API. Resolve block
// entities through getBlockComponentEntity / getBlockComponentHolder above instead.
```

### ECS Integration
```java
// (toHolder() was removed by 0.6.3 — chunk columns are serialized by the ChunkSavingSystems, not by hand)

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
| `NEEDS_FORMAT_REWRITE` | Set by the `RocksDb` storage provider when a chunk is loaded from an older on-disk format; `ChunkStore` rewrites it on the next save and clears the flag (0.6.3+) |

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

Bit-flag constants for the `int settings` (a.k.a. `flags`) parameter accepted by every block-writing method: the `WorldChunk` `setBlock`/`breakBlock` overloads and the [chunk accessor](#chunk-accessors) `setBlock(x, y, z, blockTypeKey, settings)` / `breakBlock(x, y, z, settings)` defaults. Combine with bitwise OR. `NONE` (0) runs the full default side-effect pipeline — most flags *suppress* a side effect, while `PHYSICS`, `FORCE_CHANGED`, and `PERFORM_BLOCK_UPDATE` *opt in* to extra behavior.

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
| `NO_FIRE_ON_BREAK` | 4096 | Declared in 0.6.3 (intent: skip fire spread/ignition on break); nothing in the 0.6.3 jar reads it yet |

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

The accessor interfaces provide **world-coordinate** block access that spans chunk boundaries — each default method resolves the owning chunk from the block coordinates and delegates to it. **`World` implements `ChunkAccessor`** (and `IWorldChunks`), so all of these methods can be called directly on a `World`. As of 0.6.3 the accessor interfaces are **no longer generic** — they are typed to `WorldChunk` directly, and the `BlockAccessor` abstraction that used to sit under them was removed.

```
IChunkAccessorSync                   @Deprecated base: chunk getters + block defaults
└── ChunkAccessor                    adds fluid lookup + neighbor block updates   ← implemented by World
    └── OverridableChunkAccessor     adds overwrite(WorldChunk)
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
BlockType getBlockType(Vector3ic pos)
void setBlock(int x, int y, int z, String blockTypeKey)
void setBlock(int x, int y, int z, String blockTypeKey, int settings)   // SetBlockSettings flags
boolean breakBlock(int x, int y, int z, int settings)
Holder<ChunkStore> getBlockComponentHolder(int x, int y, int z)
void setBlockInteractionState(Vector3i pos, BlockType type, String state)
BlockPosition getBaseBlock(BlockPosition position)   // @Deprecated(forRemoval=true)
```

The `testBlockTypes` / `testPlaceBlock` defaults and `getBlockRotationIndex` were removed from the accessor by 0.6.3. Placement testing is now a static on `BlockOperations` (`server.core.universe.world.chunk`): `BlockOperations.testPlaceBlock(ComponentAccessor<ChunkStore> accessor, BlockSection section, int x, int y, int z, BlockType type, int rotation[, BlockOperations.TestBlockFunction predicate])`, and the predicate interface moved with it — `BlockOperations.TestBlockFunction` is `boolean test(int, int, int, BlockType, int, int)` (the old `IChunkAccessorSync.TestBlockFunction` nested type is gone). For a rotation index use `WorldChunk.getRotationIndex(x, y, z)` on the owning chunk.

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
void overwrite(WorldChunk chunk)   // inject/replace a chunk in the accessor's view
```

### LocalCachedChunkAccessor

A concrete `OverridableChunkAccessor` that caches the chunks of a square area in a flat array, so repeated block reads/writes during an area edit skip the world's chunk lookup. This is what the built-in builder tools and farming systems use for multi-block operations.

```java
// Factories (delegate is usually the World itself)
static LocalCachedChunkAccessor atWorldCoords(ChunkAccessor delegate, int centerX, int centerZ, int blockRadius)
static LocalCachedChunkAccessor atChunkCoords(ChunkAccessor delegate, int chunkX, int chunkZ, int chunkRadius)
static LocalCachedChunkAccessor atChunk(ChunkAccessor delegate, WorldChunk center, int chunkRadius)

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
| `HIGH_PRIORITY` | 32 | Schedule the load ahead of normal requests (0.6.3+) |
| `NO_SET_TICKING_SYNC` | `Integer.MIN_VALUE` | Internal: don't set ticking synchronously |

`NO_LOAD | NO_GENERATE` restricts the request to chunks already in memory.

---

## Chunk Columns & Sections
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk` (and `.section`, `.environment`, `.palette`)

Underneath `WorldChunk`, chunk data lives in the ECS: each chunk column is an entity in the `ChunkStore`, and its `ChunkColumn` component holds references to per-**section** entities (one per 32-block vertical slice; each carries a `ChunkSection` component) that hold the actual `BlockSection` / `FluidSection` storage. Plugins reach them via the component API:

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

### ChunkSection

The identity component on each section entity (0.6.3 reworked it: sections now carry their own keep-alive
and active timers, and `ChunkStore.supportsCubicSections()` reports whether the world's storage can load
and unload sections independently of their column).

```java
static ComponentType<ChunkStore, ChunkSection> getComponentType()

Ref<ChunkStore> getChunkColumnReference()   // back-reference to the owning column entity
int getX(); int getY(); int getZ()          // section coordinates (y = ChunkUtil.chunkCoordinate(blockY))
int pollKeepAlive(int decrement)            // same semantics as the WorldChunk timers
void resetKeepAlive()
int pollActiveTimer(int decrement)
void resetActiveTimer()
```

Related `ChunkStore` entry points (0.6.3+): `supportsCubicSections()`, `hasLoadedSections(long chunkIndex)`,
`removeSection(Ref<ChunkStore> section, RemoveReason reason)`, and the `SECTION_UNLOAD_RESOURCE` resource type
that backs section unloading.

### BlockSection

Palette-compressed block storage for one 32×32×32 section: block ids, filler ids, rotations, ticking-block bookkeeping, and light data. Local coordinates or a packed block index address the same data.

> **⚠️ Prefer `WorldChunk.setBlock` / the accessors for writes.** `BlockSection.set` writes the raw palette only — no heightmap, lighting, filler, block-entity, or notification side effects run. It is the right tool for bulk analysis and for migration/worldgen-style code, not for gameplay edits.

```java
static ComponentType<ChunkStore, BlockSection> getComponentType()
static final int VERSION   // on-disk section format version (6 in 0.6.3)

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
| `AbstractCachedAccessor` | `...world.chunk` | Base class for systems that cache column/section `Ref`s over an area — `getColumn(x, z)`, `getColumnAtBlock(x, z)`, `getSection(x, y, z)`, `getSectionAtBlock(x, y, z)` (0.6.3 renamed `getChunk` → `getColumn`, added the `AtBlock` forms, and the constructor now takes an `AbstractCachedAccessor.Registry`); used by the block-physics systems |
| `BlockRotationUtil` | `...world.chunk` | Static rotation math: `getRotated(RotationTuple, Axis, Rotation, VariantRotation)`, `getFlipped(RotationTuple, BlockFlipType, Axis)`, `getRotatedFiller(int, RotationTuple)`, `getFlippedFiller(int, Axis)` |

---

## ChunkTracker
**Package:** `com.hypixel.hytale.server.core.modules.entity.player`

Component that manages chunk loading and visibility per player. Controls how quickly chunk data is sent to a player and which chunks should be visible.

> **0.6.3 renamed the whole rate/radius/count API from chunks to sections** — the tracker now streams
> 32×32×32 *sections*, not whole columns. Every `*Chunks*` accessor below became `*Sections*` (or lost the
> word entirely for the radii), the constants were renamed and re-scaled ×10, `unloadAll(PlayerRef)` was
> removed, and section-coordinate `(x, y, z)` overloads were added next to the `long chunkIndex` ones.

### Getting the Component
```java
ChunkTracker tracker = store.getComponent(ref, ChunkTracker.getComponentType());
// Or from PlayerRef
ChunkTracker tracker = playerRef.getChunkTracker();
```

### Chunk Visibility
```java
boolean isLoaded(long chunkIndex)           // Is the column loaded for this player?
boolean isLoaded(int x, int y, int z)       // ... or a specific section (0.6.3+)
boolean shouldBeVisible(long chunkIndex)    // Should the column be visible?
boolean shouldBeVisible(int x, int y, int z)
ChunkVisibility getChunkVisibility(long chunkIndex)          // Column visibility state
ChunkVisibility getSectionVisibility(int x, int y, int z)    // Section visibility state (0.6.3+)
```

#### ChunkVisibility Enum

Nested enum defining chunk visibility states for a player.

| Value | Description |
|-------|-------------|
| `NONE` | Chunk is not visible to player |
| `HOT` | Chunk is actively visible (nearby) |
| `COLD` | Chunk is visible but not actively updated |

### Section Loading Rates
```java
int getMaxSectionsPerSecond()               // Max sections sent per second (was getMaxChunksPerSecond)
void setMaxSectionsPerSecond(int rate)
void setDefaultMaxSectionsPerSecond(PlayerRef ref)  // Reset to default based on connection

int getMaxSectionsPerTick()                 // Max sections sent per tick (was getMaxChunksPerTick)
void setMaxSectionsPerTick(int rate)
```

### Load Radius
```java
int getMinLoadedRadius()                    // Minimum radius kept loaded (was getMinLoadedChunksRadius)
void setMinLoadedRadius(int radius)

int getMaxHotLoadedRadius()                 // Max radius of hot-loaded sections (was getMaxHotLoadedChunksRadius)
void setMaxHotLoadedRadius(int radius)
```

### Statistics
```java
int getLoadedSectionsCount()                // Sections loaded for the player (was getLoadedChunksCount)
int getLoadingSectionsCount()               // Sections currently loading (was getLoadingChunksCount)
void forEachLoadedSection(TriIntConsumer consumer)   // iterate loaded section coordinates (0.6.3+)
```

### Lifecycle
```java
void clear()                                // Clear tracker state
void removeForReload(long chunkIndex)       // Mark a column for reload
void removeForReload(int x, int y, int z)   // ... or one section (0.6.3+)
boolean isReadyForChunks()                  // May the tracker stream sections right now? (cleared by World.addPlayer, set by the player tracker systems once the client is in)
void setReadyForChunks(boolean ready)
// unloadAll(PlayerRef) was removed by 0.6.3 — unloading is driven by the tracker's own tick
```

### Constants
```java
static final int MAX_SECTIONS_PER_SECOND        = 360    // Default max (remote); was MAX_CHUNKS_PER_SECOND = 36
static final int MAX_SECTIONS_PER_SECOND_LAN    = 1280   // LAN connections;   was MAX_CHUNKS_PER_SECOND_LAN = 128
static final int MAX_SECTIONS_PER_SECOND_LOCAL  = 2560   // Local/singleplayer; was MAX_CHUNKS_PER_SECOND_LOCAL = 256
static final int MAX_SECTIONS_PER_TICK          = 40     // was MAX_CHUNKS_PER_TICK = 4
static final int MIN_LOADED_RADIUS              = 2      // was MIN_LOADED_CHUNKS_RADIUS
static final int MAX_HOT_LOADED_RADIUS          = 8      // was MAX_HOT_LOADED_CHUNKS_RADIUS
```

### Usage Example
```java
// Increase chunk streaming speed for a player
ChunkTracker tracker = playerRef.getChunkTracker();
tracker.setMaxSectionsPerSecond(1000);  // Send up to 1000 sections/second (~100 columns)

// Check how many sections are loaded
int loaded = tracker.getLoadedSectionsCount();
playerRef.sendMessage(Message.raw("You have " + loaded + " chunk sections loaded"));
```

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the chunk system (verified
against `HytaleServer.jar`).

- **`Cannot demote empty chunk section!`** → a chunk-palette/section operation ran against an empty section. Fix: operate on a loaded chunk section with content; verify the chunk is loaded first (e.g. `getChunkIfLoaded()` returns non-null).

The world-level errors (`Player is already in a world`, `This world has already been shutdown!` and
the entity add/remove pair) stayed with [world.md](world.md#gotchas--errors), which still owns the
`World` object those operate on.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
