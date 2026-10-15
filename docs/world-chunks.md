---
title: "World Chunks"
description: "Hytale's chunk storage and lifecycle Java API — ChunkStore/ChunkGrid column and section references, chunk-load flags, the WorldChunk column component, chunk flags, cubic sections, section lighting, and per-player chunk tracking with ChunkTracker."
seo:
  type: TechArticle
---

# World Chunks

**Doc type:** Java API · **Verified against 0.7.2**

Split out of [world.md](world.md) at the 2026-09-04 seam. The chunk half of the World API: how columns
and sections are loaded and referenced, the flags that control loading, the `WorldChunk` column
component and its flags, how tall a world can be, section lighting, and `ChunkTracker`, which decides
what each player has loaded. **Reading and writing blocks is on its own page,
[block-access.md](block-access.md).** The `World` object stays in [world.md](world.md), and the chunk
**events** are in [world-lifecycle-events.md](world-lifecycle-events.md).

> **0.7.2 moved block access off `World` and `WorldChunk`.** `World` no longer implements
> `ChunkAccessor` / `IWorldChunks` (both removed, with `IChunkAccessorSync`,
> `OverridableChunkAccessor`, `LocalCachedChunkAccessor` and `ChunkSectionReference`), and `WorldChunk`
> lost its block, fluid, height and ticking methods. Blocks are read and written per section — see
> [block-access.md](block-access.md), which also has a migration table.

---

## ChunkGrid and ChunkStore

**Package:** `com.hypixel.hytale.server.core.universe.world.storage`

`ChunkStore extends ChunkGrid` (`ChunkGrid` is new in 0.7.2), so every method below is called on
`world.getChunkStore()`. The grid tracks a load state for every column and every section, and hands
out `Ref<ChunkStore>` references to their entities.

```java
Store<ChunkStore> getStore()
World getWorld()

// Columns
Ref<ChunkStore> getChunkReference(long chunkIndex)                       // loaded column, or null
CompletableFuture<Ref<ChunkStore>> getChunkReferenceAsync(long chunkIndex)
CompletableFuture<Ref<ChunkStore>> getChunkReferenceAsync(long chunkIndex, int flags)
<T extends Component<ChunkStore>> T getChunkComponent(long chunkIndex, ComponentType<ChunkStore, T> type)
LongSet getChunkIndexes()
int getLoadedChunksCount()

// Sections (the block-coordinate lookups are on block-access.md)
Ref<ChunkStore> getChunkSectionReference(int sectionX, int sectionY, int sectionZ)
Ref<ChunkStore> getChunkSectionReferenceAtBlock(int blockX, int blockY, int blockZ)
CompletableFuture<Ref<ChunkStore>> getChunkSectionReferenceAsync(int sectionX, int sectionY, int sectionZ, int flags)
CompletableFuture<Ref<ChunkStore>> getChunkSectionReferenceAtBlockAsync(int blockX, int blockY, int blockZ, int flags)
List<Ref<ChunkStore>> getLoadedSectionReferences(int chunkX, int chunkZ)
boolean hasLoadedSections(long chunkIndex)
int lowestLoadedSectionBelow(int chunkX, int chunkZ, int anchorSectionY)
int highestLoadedSectionAbove(int chunkX, int chunkZ, int anchorSectionY)
void removeSection(Ref<ChunkStore> sectionRef, RemoveReason reason)
boolean supportsCubicSections()
```

`ChunkStore` keeps the storage side: `start`, `getSaver`, `pauseBackgroundSaving`,
`resumeBackgroundSaving`, and the `SECTION_UNLOAD_RESOURCE` / `UNLOAD_RESOURCE` / `SAVE_RESOURCE`
resource types.

`getChunkReference` and `getChunkSectionReference*` without `Async` never load: they return the ref if
it is loaded now, else `null`. The async forms load or generate as their [flags](#getchunkflags)
allow, and complete with `null` when there is nothing to return. A failed load puts the column or
section on a short back-off (`FAILURE_BACKOFF_NANOS`, growing to `MAX_FAILURE_BACKOFF_NANOS`, 10 s),
during which a new request fails immediately with `Chunk failure backoff` / `Chunk section failure
backoff`. A fresh load or generation finishes its last stage on the world executor
(`thenApplyAsync(postLoadChunk, world)` for a column, `whenCompleteAsync(..., world)` for a section),
but a ref that is already loaded usually comes back as an already-completed future, and a plain `thenAccept`
on a completed future runs at once on the **calling** thread. Called from a command, a scheduler or
another async callback, that is a thread other than the world thread, so continue with
`thenAcceptAsync(..., world)` before touching components either way — see
[block-access.md → Resolving a section](block-access.md#resolving-a-section).

---

## GetChunkFlags
**Package:** `com.hypixel.hytale.server.core.universe.world.storage`

Bit-flag constants for the `int flags` parameter of the async loaders on `ChunkStore` (inherited from
`ChunkGrid`): `getChunkReferenceAsync(long chunkIndex, int flags)`,
`getChunkSectionReferenceAsync(int, int, int, int flags)` and
`getChunkSectionReferenceAtBlockAsync(int, int, int, int flags)`. The overloads without `flags` pass `0`.

| Constant | Value | Effect (read from `ChunkGrid`) |
|----------|-------|--------|
| `NONE` | 0 | Load from storage, and generate if storage has nothing |
| `NO_LOAD` | 1 | Skip the storage load |
| `NO_GENERATE` | 2 | Skip generation |
| `SET_TICKING` | 4 | Once available, remove the `NonTicking` marker so the column or section ticks |
| `BYPASS_LOADED` | 8 | Column requests only: start a load even if the column is already loaded |
| `POLL_STILL_NEEDED` | 16 | Let the generator abandon the request once no player's `ChunkTracker` still wants it |
| `HIGH_PRIORITY` | 32 | Put the request at the front of the generation queue |
| `NO_SET_TICKING_SYNC` | `Integer.MIN_VALUE` | With `SET_TICKING` on the world thread, defer the ticking change to a world task instead of applying it immediately |

`NO_LOAD | NO_GENERATE` (3) never starts work: it returns the loaded ref, the in-flight future if a load
is already running, or `null`. `BlockOperations.updateBlockArea` uses exactly that form to touch
neighbouring sections without loading them.

---

## WorldChunk
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk`

The column entity's bookkeeping component. Implements `Component<ChunkStore>`. **In 0.7.2 it has no
block, fluid, height or ticking API** — see [block-access.md](block-access.md).
Its constructor and `loadFromHolder` also lost their `World` parameter.

```java
static ComponentType<ChunkStore, WorldChunk> getComponentType()
static final int KEEP_ALIVE_DEFAULT   // 15

// Position
long getIndex()    // column key (ChunkUtil.indexChunk)
int getX()         // column x, in chunk coordinates
int getZ()

// Flags (see ChunkFlag below)
boolean is(ChunkFlag flag)
void setFlag(ChunkFlag flag, boolean value)

// Keep-alive and loading
boolean shouldKeepLoaded()
void addKeepLoaded()
void removeKeepLoaded()
int pollKeepAlive(int pollCount)
void resetKeepAlive()
int pollActiveTimer(int pollCount)
void resetActiveTimer()

// Persistence
void markNeedsSaving()
boolean getNeedsSaving()          // also true when the column's BlockChunk needs saving
boolean consumeNeedsSaving()
boolean isSaving()
void setSaving(boolean saving)

// ECS
Ref<ChunkStore> getReference()
void setReference(Ref<ChunkStore> reference)                 // @Deprecated
void loadFromHolder(int x, int z, Holder<ChunkStore> holder) // @Deprecated
Component<ChunkStore> clone()
```

To get a loaded column's `WorldChunk`:

```java
long index = ChunkUtil.indexChunkFromBlock(blockX, blockZ);
WorldChunk chunk = world.getChunkStore().getChunkComponent(index, WorldChunk.getComponentType()); // null if not loaded
```

Whether a column ticks is no longer a flag: check for the `NonTicking` marker on its ref, as
`ChunkInfoCommand` does —
`!store.getArchetype(chunkRef).contains(ChunkStore.REGISTRY.getNonTickingComponentType())`.

> **See also:** [Collision API](collision.md#blockcollisiondata)

---

## ChunkFlag
**Package:** `com.hypixel.hytale.server.core.universe.world.chunk`

Enum of per-column state flags, read with `WorldChunk.is(flag)`. Implements `Flag`. 0.7.2 removed
`START_INIT`, `INIT` and `TICKING`.

| Value | Description |
|-------|-------------|
| `NEWLY_GENERATED` | The column was generated this session, not loaded from storage |
| `ON_DISK` | The column exists in storage (set on load from storage and after a save) |
| `NEEDS_FORMAT_REWRITE` | Set by the `RocksDb` storage provider when a column is loaded from an older on-disk format. On load the column and its sections are marked for saving and the flag is cleared, so the next save rewrites them |

```java
static ChunkFlag[] values()
static ChunkFlag valueOf(String name)
int mask()  // bitmask for this flag
```

```java
WorldChunk chunk = chunkStore.getChunkComponent(index, WorldChunk.getComponentType());
if (chunk != null && chunk.is(ChunkFlag.NEWLY_GENERATED)) {
    // first-time generation logic (TriggerVolumeChunkRegenSystem gates on this flag)
}
```

---

## Cubic sections

A section is 32×32×32 blocks, and section coordinates are block coordinates shifted right by 5
(`ChunkUtil.chunkCoordinate`). On a default world a column has the ten sections `y = 0..9` (blocks
0–319); they are loaded and saved with their column, and `ChunkColumn` lists them.

0.7.2 lets a world grow past that range, but loading and generating an off-range section have
different requirements, and the query plugins see is looser than both:

- `ChunkGrid.supportsCubicSections()` is `true` when the world's chunk loader implements
  `IChunkLoader.Cubic` **or** its generator implements `IWorldGen.Cubic`.
- `ChunkGrid.getChunkSectionReferenceAsync` **loads** a section outside `0..9` on its own only through a
  cubic loader (`IChunkLoader.Cubic.loadSectionHolder`).
- It **generates** one only when the loader is cubic **and** the generator is cubic
  (`IWorldGen.Cubic.generate(seed, x, y, z, …)`). The column path makes the same test: with both
  cubic, a column's ten sections are generated section by section through the cubic generator, and otherwise
  the whole column comes from the classic `IWorldGen.generate`.

In the 0.7.2 jar the `RocksDb` storage provider's loader is cubic, and so is the test generator
`CubicTestWorldGenProvider`; the default storage (`Hytale`, which delegates to `IndexedStorage`) and the
shipped generators other than `CubicTestWorldGenProvider` are classic. So only `RocksDb` storage with a cubic generator grows sections on
demand. `RocksDb` with a classic generator loads off-range sections that were stored, and the default
storage with `CubicTestWorldGenProvider` reaches none at all, yet `supportsCubicSections()` is `true` for
both. Wherever the required half is missing, a lookup for a section outside `0..9` completes with
`null`.

Consequences for plugins:

- `ChunkUtil.HEIGHT` (320), `HEIGHT_SECTIONS` (10), `HEIGHT_MINUS_1`, `HEIGHT_MASK` and
  `SIZE_BLOCKS_COLUMN` are `@Deprecated` in 0.7.2. Check a height with
  `new SectionReader(chunkStore).canHoldY(y)`, which is `supportsCubicSections() || (0 <= y && y < 320)`.
  A `false` rules the y out. A `true` outside `0..319` only says one half is cubic, so treat it as
  "a section may exist here" and handle a `null` lookup.
- `ChunkColumn` still holds only sections `0..9`. Reach any other section through `ChunkGrid`
  (`getChunkSectionReference`, `getLoadedSectionReferences(chunkX, chunkZ)`,
  `lowestLoadedSectionBelow` / `highestLoadedSectionAbove`).
- Sections carry their own keep-alive (`ChunkSection.pollKeepAlive` / `addKeepLoaded`), so a section
  outside `0..9` can unload while its column stays loaded (`ChunkStore.SECTION_UNLOAD_RESOURCE`);
  `SectionUnloadingSystem` keeps sections `0..9` for as long as their column is loaded.

---

## ChunkColumn

The column component listing its section entities. It holds the fixed sections 0–9 only; see
[Cubic sections](#cubic-sections). The section components themselves (`ChunkSection`, `BlockSection`,
`FluidSection`, …) are on [block-access.md](block-access.md#section-components).

```java
static ComponentType<ChunkStore, ChunkColumn> getComponentType()

Ref<ChunkStore> getSection(int sectionY)    // null outside 0..9
Ref<ChunkStore>[] getSections()
Holder<ChunkStore>[] getSectionHolders()
Holder<ChunkStore>[] takeSectionHolders()
void putSectionHolders(Holder<ChunkStore>[] holders)
```

---

## ChunkLightData

Immutable snapshot of a section's light: four 4-bit channels (red, green, blue block light, plus sky
light) stored in an octree. Obtained from the section's `BlockSection.getLocalLight()` / `getGlobalLight()`.
Recomputation is driven by `world.getChunkLighting()` (`ChunkLightingManager`), whose `invalidate*`
methods take a `ChunkGrid` in 0.7.2.

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

Constants: `EMPTY` (the all-zero instance), `MAX_VALUE` (15 per channel), `CHANNEL_COUNT` (4), and the
channel indices `RED_CHANNEL` / `GREEN_CHANNEL` / `BLUE_CHANNEL` / `SKY_CHANNEL`.

---

## Supporting classes

| Class | Package | Description |
|-------|---------|-------------|
| `BlockChunk` | `...world.chunk` | Column component for the tint map (`getTint(x, z)`, `setTint(x, z, tint)`) and column-level save state. 0.7.2 moved its heightmap to `HeightmapColumn` and its environment data to per-section `EnvironmentSection`, and removed its block accessors |
| `EnvironmentSection` | `...world.chunk.section` | 0.7.2+: per-section environment ids — see [block-access.md](block-access.md#environmentsection) |
| `HeightmapColumn` | `...world.chunk.heightmap` | 0.7.2+: the column's heightmap component, replacing the removed `WorldChunk.getHeight` — see [block-access.md](block-access.md#heightmapcolumn) |
| `EnvironmentChunk` | `...world.chunk.environment` | `@Deprecated` in 0.7.2: the old column-wide environment store, kept so older saves load: `sliceToSection(sectionY)` converts it, and the `ChunkSystems.MigrateEnvironmentChunk` system migrates it |
| `ShortBytePalette` | `...world.chunk.palette` | Palette-compressed 1024-entry (`LENGTH`, 32×32) short grid — `set` / `get` / `contains` / `optimize` / `copyFrom`; in 0.7.2 it backs only the legacy heightmap (`LegacyHeightmap`) |
| `AbstractCachedAccessor` | `...world.chunk` | Base class for systems that cache column/section refs over an area — `getColumn(x, z)`, `getColumnAtBlock(x, z)`, `getSection(x, y, z)`, `getSectionAtBlock(x, y, z)`; its constructor takes an `AbstractCachedAccessor.Registry`. Subclassed by the block-physics systems and `FluidTicker` |
| `BlockRotationUtil` | `...world.chunk` | Static rotation math: `getRotated(RotationTuple, Axis, Rotation, VariantRotation)`, `getFlipped(RotationTuple, BlockFlipType, Axis)`, `getRotatedFiller(int, RotationTuple)`, `getRotatedFiller(int, Axis, Rotation)`, and (0.7.2 signature) `getFlippedFiller(int, Axis, RotatedVariantBoxes, RotatedVariantBoxes)` |

---

## ChunkTracker
**Package:** `com.hypixel.hytale.server.core.modules.entity.player`

Component that manages chunk loading and visibility per player: how quickly chunk data is sent and
which columns and sections should be visible. Since 0.6.3 it streams 32×32×32 **sections**, so its rate,
radius and count methods are named for sections.

### Getting the Component
```java
ChunkTracker tracker = store.getComponent(ref, ChunkTracker.getComponentType());
// Or from PlayerRef
ChunkTracker tracker = playerRef.getChunkTracker();
```

### Chunk Visibility
```java
boolean isLoaded(long chunkIndex)           // Is the column loaded for this player?
boolean isLoaded(int x, int y, int z)       // ... or a specific section
boolean shouldBeVisible(long chunkIndex)    // Should the column be visible?
boolean shouldBeVisible(int x, int y, int z)
ChunkVisibility getChunkVisibility(long chunkIndex)          // Column visibility state
ChunkVisibility getSectionVisibility(int x, int y, int z)    // Section visibility state
```

#### ChunkVisibility Enum

| Value | Description |
|-------|-------------|
| `NONE` | Not visible to the player |
| `HOT` | Actively visible (nearby) |
| `COLD` | Visible but not actively updated |

### Section Loading Rates
```java
int getMaxSectionsPerSecond()
void setMaxSectionsPerSecond(int rate)
void setDefaultMaxSectionsPerSecond(PlayerRef ref)  // reset to the default for the connection type

int getMaxSectionsPerTick()
void setMaxSectionsPerTick(int rate)
```

### Load Radius
```java
int getMinLoadedRadius()
void setMinLoadedRadius(int radius)

int getMaxHotLoadedRadius()
void setMaxHotLoadedRadius(int radius)
```

### Statistics
```java
int getLoadedSectionsCount()
int getLoadingSectionsCount()
void forEachLoadedSection(TriIntConsumer consumer)   // iterate loaded section coordinates
```

### Lifecycle
```java
void clear()                                // Clear tracker state
void removeForReload(long chunkIndex)       // Mark a column for reload
void removeForReload(int x, int y, int z)   // ... or one section
boolean isReadyForChunks()                  // May the tracker stream sections now? (cleared when the player is added to a world, set by the player tracker systems once the client is in)
void setReadyForChunks(boolean ready)
```

### Constants
```java
static final int MAX_SECTIONS_PER_SECOND        = 360    // default (remote)
static final int MAX_SECTIONS_PER_SECOND_LAN    = 1280   // LAN connections
static final int MAX_SECTIONS_PER_SECOND_LOCAL  = 2560   // local / singleplayer
static final int MAX_SECTIONS_PER_TICK          = 40
static final int MIN_LOADED_RADIUS              = 2
static final int MAX_HOT_LOADED_RADIUS          = 8
```

### Usage Example
```java
// Increase chunk streaming speed for a player
ChunkTracker tracker = playerRef.getChunkTracker();
tracker.setMaxSectionsPerSecond(1000);  // up to 1000 sections/second (~100 columns)

// Check how many sections are loaded
int loaded = tracker.getLoadedSectionsCount();
playerRef.sendMessage(Message.raw("You have " + loaded + " chunk sections loaded"));
```

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the chunk system (verified
against `HytaleServer.jar`).

- **`Chunk failure backoff`** / **`Chunk section failure backoff`** → an async load is failing fast
  because the previous attempt for that column or section failed less than the back-off ago. Fix: look
  for the earlier `Failed to load chunk!` / `Failed to generate chunk!` log line; retry later.
- **`Assert not in thread!`** → a `ChunkStore` component was touched off the world thread, typically in
  a `thenAccept` on a chunk future. Fix: continue with `thenAcceptAsync(..., world)`. Block-level
  gotchas are on [block-access.md](block-access.md#gotchas--errors).
- **`Cannot demote empty chunk section!`** → a palette operation ran against an empty section. Fix:
  operate on a loaded section with content.

The world-level errors (`Player is already in a world`, `This world has already been shutdown!` and the
entity add/remove pair) stayed with [world.md](world.md#gotchas--errors), which still owns the `World`
object those operate on.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
