---
title: "Prefabs API"
description: "Work with Hytale prefabs in Java — the PrefabStore for loading/saving server, asset, and world-gen prefabs, BlockSelection payloads of blocks/fluids/entities, and placement with rotation."
seo:
  type: TechArticle
---

# Prefabs API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Prefabs` · **Verified against 0.5.9**

Prefabs are pre-defined block/entity selections that can be loaded and placed into the world. They allow consistent structure creation with blocks, fluids, and entities.

## Overview

Implemented in `com.hypixel.hytale.server.core.prefab` and provides:
- A central `PrefabStore` for loading and saving server, asset, and world-gen prefabs
- `BlockSelection`, the prefab payload holding blocks, fluids, and entities
- Placement into the world with rotation (`PrefabRotation`) and transformation
- Capturing selections from the world back into prefabs
- Weighted random selection (`PrefabWeights`) and prefab metadata (`PrefabEntry`)
- Prefab lifecycle events (paste, place-entity)

## Architecture
```
PrefabStore  (load / save / locate)
├── Sources
│   ├── server prefabs
│   ├── asset prefabs (per AssetPack)
│   └── world-gen prefabs
├── BlockSelection  (blocks + fluids + entities)
│   ├── place into world (+ PrefabRotation, transform)
│   └── copy from world
├── PrefabEntry  (file metadata)
├── PrefabWeights  (weighted random pick)
└── Events
    ├── PrefabPasteEvent
    └── PrefabPlaceEntityEvent
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `PrefabStore` | `server.core.prefab` | Central store for loading/saving prefabs; `PrefabStore.get()` |
| `BlockSelection` | `server.core.prefab.selection.standard` | Prefab data: blocks, fluids, entities; placement and copy |
| `PrefabRotation` | `server.core.prefab` | Rotation enum applied during placement |
| `PrefabEntry` | `server.core.prefab` | Prefab file metadata record |
| `PrefabWeights` | `server.core.prefab` | Weighted random selection over prefabs |
| `PrefabPasteEvent` | `server.core.prefab.event` | Fired when a prefab is pasted into the world |
| `PrefabPlaceEntityEvent` | `server.core.prefab.event` | Fired when a prefab places an entity |
| `PrefabLoadException` / `PrefabSaveException` | `server.core.prefab` | Unchecked exceptions from prefab load/save, each with a `Type` enum |
| `PrefabCopyableComponent` | `server.core.prefab` | Marker component: entity gets captured when a prefab is saved |
| `SelectionManager` / `SelectionProvider` | `server.core.prefab.selection` | Global hook to the builder-tools selection (clipboard) provider |
| `RotateBlockMode` | `server.core.prefab.selection.standard` | Which blocks get their per-block rotation updated during a rotate |
| `FeedbackConsumer` | `server.core.prefab.selection.standard` | Progress-feedback callback for selection operations |
| `BlockFilter` | `server.core.prefab.selection.mask` | One positional filter inside a `BlockMask` |
| `PrefabLoader` | `server.core.prefab.selection.buffer` | Resolves dotted prefab names to `.prefab.json` paths |
| `PrefabBufferUtil` | `server.core.prefab.selection.buffer` | Loads, caches, and binary-converts prefab files |
| `PrefabBufferCall` | `server.core.prefab.selection.buffer` | Iteration context: `Random` + `PrefabRotation` |
| `IPrefabBuffer` / `PrefabBuffer` | `server.core.prefab.selection.buffer.impl` | Packed prefab block data and its read view |
| `PrefabUtil` | `server.core.util` | Static paste / remove / can-place for `IPrefabBuffer` prefabs |
| `PrefabSpawnerBlock` | `server.core.modules.prefabspawner` | Chunk-store component behind Prefab Spawner blocks |
| `PrefabListAsset` | `server.core.asset.type.buildertool.config` | Java asset type behind `Server/PrefabList/*.json` |

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Categories Reference](prefabs-categories.md) | `prefabs-categories.md` | Trees, Rocks, NPCs, Dungeons (2,455+ files) |
| [File Format](#prefab-file-format) | Below | JSON schema, blocks, fluids, entities |
| [Java API](#prefabstore) | Below | PrefabStore, BlockSelection, Events |
| [Buffer Pipeline](#the-prefab-buffer-pipeline) | Below | PrefabLoader, PrefabBufferUtil, IPrefabBuffer, PrefabUtil |

---

## Class Hierarchy
```
PrefabStore                    (central storage and loading)
BlockSelection                 (prefab data: blocks, fluids, entities)
PrefabEntry                    (prefab file metadata)
PrefabRotation                 (rotation enum)
PrefabWeights                  (weighted random selection)
SelectionManager               (global SelectionProvider hook)
PrefabLoader                   (prefab name → file path)
PrefabBufferUtil               (file → cached PrefabBuffer)
PrefabBuffer / IPrefabBuffer   (packed block data + read view)
PrefabUtil                     (paste / remove / can-place)
```

---

## PrefabStore
**Package:** `com.hypixel.hytale.server.core.prefab`

Central storage for loading and saving prefabs. Access via `PrefabStore.get()`.

### Constants
```java
static final Path PREFABS_PATH                    // Default prefabs directory
static final Predicate<Path> PREFAB_FILTER        // File filter for prefab files
```

### Getting the Store
```java
PrefabStore store = PrefabStore.get();
```

### Loading Prefabs
```java
// Load server prefab by name
BlockSelection getServerPrefab(String name)

// Load asset prefab by name
BlockSelection getAssetPrefab(String name)

// Load from any asset pack
BlockSelection getAssetPrefabFromAnyPack(String name)

// Load world generation prefab
BlockSelection getWorldGenPrefab(String name)

// Load from specific path
BlockSelection getPrefab(Path path)

// Load directory of prefabs
Map<Path, BlockSelection> getServerPrefabDir(String dirName)
Map<Path, BlockSelection> getAssetPrefabDir(String dirName)
Map<Path, BlockSelection> getWorldGenPrefabDir(String dirName)
Map<Path, BlockSelection> getPrefabDir(Path path)
```

### Saving Prefabs
```java
void saveServerPrefab(String name, BlockSelection selection)
void saveServerPrefab(String name, BlockSelection selection, boolean overwrite)
void saveAssetPrefab(String name, BlockSelection selection)
void saveAssetPrefab(String name, BlockSelection selection, boolean overwrite)
void saveWorldGenPrefab(String name, BlockSelection selection)
void saveWorldGenPrefab(String name, BlockSelection selection, boolean overwrite)
void savePrefab(Path path, BlockSelection selection, boolean overwrite)
```

### Path Queries
```java
Path getServerPrefabsPath()
Path getAssetPrefabsPath()
Path getWorldGenPrefabsPath()
Path getWorldGenPrefabsPath(String subPath)
Path getAssetRootPath()
Path getAssetPrefabsPathForPack(AssetPack pack)
Path findAssetPrefabPath(String name)
List<AssetPackPrefabPath> getAllAssetPrefabPaths()
AssetPack findAssetPackForPrefabPath(Path path)
```

### Usage Example
```java
PrefabStore store = PrefabStore.get();

// Load a prefab
BlockSelection house = store.getServerPrefab("buildings/house");

// Place it in the world
house.place(commandSender, world);
```

> **See also:** [World API](world.md#worldchunk)

---

## BlockSelection
**Package:** `com.hypixel.hytale.server.core.prefab.selection.standard`

The core prefab data structure containing blocks, fluids, and entities. This is what gets loaded from prefab files and placed in the world.

### Constructors
```java
BlockSelection()
BlockSelection(int initialBlockCapacity, int initialFluidCapacity)
BlockSelection(BlockSelection source)  // Copy constructor
```

### Position & Bounds
```java
// Current position
int getX()
int getY()
int getZ()
void setPosition(int x, int y, int z)

// Anchor point (placement origin)
int getAnchorX()
int getAnchorY()
int getAnchorZ()
void setAnchor(int x, int y, int z)
void setAnchorAtWorldPos(int x, int y, int z)

// Selection bounds
Vector3i getSelectionMin()
Vector3i getSelectionMax()
boolean hasSelectionBounds()
void setSelectionArea(Vector3i min, Vector3i max)
```

### Content Info
```java
int getBlockCount()
int getFluidCount()
int getEntityCount()
int getSelectionVolume()
```

### Block Access
```java
boolean hasBlockAtWorldPos(int x, int y, int z)
boolean hasBlockAtLocalPos(int x, int y, int z)
int getBlockAtWorldPos(int x, int y, int z)
BlockHolder getBlockHolderAtWorldPos(int x, int y, int z)
int getFluidAtWorldPos(int x, int y, int z)
byte getFluidLevelAtWorldPos(int x, int y, int z)
int getSupportValueAtWorldPos(int x, int y, int z)
Holder<ChunkStore> getStateAtWorldPos(int x, int y, int z)
```

### Adding Content
```java
// Blocks
void addEmptyAtWorldPos(int x, int y, int z)
void addBlockAtWorldPos(int x, int y, int z, int blockType, int rotation, int filler, int supportValue)
void addBlockAtWorldPos(int x, int y, int z, int blockType, int rotation, int filler, int supportValue, Holder<ChunkStore> state)
void addBlockAtLocalPos(int x, int y, int z, int blockType, int rotation, int filler, int supportValue)

// Fluids
void addFluidAtWorldPos(int x, int y, int z, int fluidType, byte level)
void addFluidAtLocalPos(int x, int y, int z, int fluidType, byte level)

// Entities
void addEntityFromWorld(Holder<EntityStore> holder)
void addEntityHolderRaw(Holder<EntityStore> holder)
```

### Iteration
```java
void forEachBlock(BlockIterator iterator)
void forEachFluid(FluidIterator iterator)
void forEachEntity(Consumer<Holder<EntityStore>> consumer)
```

### Placement
```java
// Place and return undo selection
BlockSelection place(CommandSender sender, World world)
BlockSelection place(CommandSender sender, World world, BlockMask mask)
BlockSelection place(CommandSender sender, World world, Vector3i position, BlockMask mask)
BlockSelection place(CommandSender sender, World world, Vector3i position, BlockMask mask, Consumer<Ref<EntityStore>> entityConsumer)

// Place without undo
void placeNoReturn(World world, Vector3i position, ComponentAccessor<EntityStore> accessor)
void placeNoReturn(String id, CommandSender sender, World world, ComponentAccessor<EntityStore> accessor)

// Check if placement is valid
boolean canPlace(World world, Vector3i position, IntList invalidBlocks)
boolean matches(World world, Vector3i position)
```

### Transformation
```java
// Rotation (returns new BlockSelection)
BlockSelection rotate(Axis axis, int degrees)
BlockSelection rotate(Axis axis, int degrees, Vector3f pivot)
BlockSelection rotateArbitrary(float yaw, float pitch, float roll)

// Flip
BlockSelection flip(Axis axis)

// Make positions relative to anchor
BlockSelection relativize()
BlockSelection relativize(int x, int y, int z)

// Clone
BlockSelection cloneSelection()

// Combine selections
void add(BlockSelection other)
void copyPropertiesFrom(BlockSelection other)
```

### Copying from World
```java
void copyFromAtWorld(int x, int y, int z, WorldChunk chunk, BlockPhysics physics)
```

### Usage Example
```java
// Load and place a prefab
PrefabStore store = PrefabStore.get();
BlockSelection prefab = store.getServerPrefab("structures/tower");

// Place at player position
Transform transform = playerRef.getTransform();
Vector3i pos = new Vector3i(
    (int) transform.getPosition().x(),
    (int) transform.getPosition().y(),
    (int) transform.getPosition().z()
);

// Place returns undo selection
BlockSelection undo = prefab.place(commandSender, world, pos, null);

// To undo, place the undo selection
// undo.place(commandSender, world);
```

### Rotation Example
```java
BlockSelection prefab = store.getServerPrefab("buildings/house");

// Rotate 90 degrees around Y axis
BlockSelection rotated = prefab.rotate(Axis.Y, 90);
rotated.place(commandSender, world);
```

---

## PrefabRotation
**Package:** `com.hypixel.hytale.server.core.prefab`

Enum for standard prefab rotations (90-degree increments around Y axis).

### Enum Values
```java
public enum PrefabRotation {
    ROTATION_0,    // No rotation
    ROTATION_90,   // 90 degrees clockwise
    ROTATION_180,  // 180 degrees
    ROTATION_270   // 270 degrees (90 counter-clockwise)
}

static final PrefabRotation[] VALUES  // All values array
static final String PREFIX            // Rotation name prefix
```

### Methods
```java
// Conversion
static PrefabRotation fromRotation(Rotation blockRotation)
static PrefabRotation valueOfExtended(String name)

// Combine rotations
PrefabRotation add(PrefabRotation other)

// Apply rotation to vectors
void rotate(Vector3d vec)
void rotate(Vector3i vec)
void rotate(Vector3l vec)

// Get rotated coordinates
int getX(int x, int z)
int getZ(int x, int z)

// Get yaw angle
float getYaw()

// Get rotated block rotation/filler values
int getRotation(int originalRotation)
int getFiller(int originalFiller)
```

### Usage Example
```java
// Rotate a position
Vector3i pos = new Vector3i(5, 0, 3);
PrefabRotation.ROTATION_90.rotate(pos);
// pos is now rotated 90 degrees around origin

// Combine rotations
PrefabRotation combined = PrefabRotation.ROTATION_90.add(PrefabRotation.ROTATION_180);
// combined == ROTATION_270
```

---

## PrefabEntry
**Package:** `com.hypixel.hytale.server.core.prefab`

Java Record containing prefab file metadata. Used when listing available prefabs.

### Record Components
```java
Path path()           // Full file path
Path relativePath()   // Path relative to prefabs directory
AssetPack pack()      // Asset pack containing this prefab (may be null)
String displayName()  // Human-readable display name
```

### Methods
```java
boolean isFromBasePack()       // Is from the base game
boolean isFromAssetPack()      // Is from an asset pack
String getPackName()           // Get asset pack name
String getFileName()           // Get file name only
String getDisplayNameWithPack() // Display name including pack
```

---

## PrefabWeights
**Package:** `com.hypixel.hytale.server.core.prefab`

Weighted random selection for prefabs. Allows assigning different spawn weights to different prefab variants.

### Constants
```java
static final PrefabWeights NONE           // Empty weights
static final double DEFAULT_WEIGHT        // Default weight value
static final char DELIMITER_CHAR          // Delimiter for parsing
static final char ASSIGNMENT_CHAR         // Assignment char for parsing
static final Codec<PrefabWeights> CODEC   // Serialization codec
```

### Constructors
```java
PrefabWeights()                           // Empty weights
static PrefabWeights parse(String spec)   // Parse from string format
```

### Weight Management
```java
int size()                                // Number of entries
double getWeight(String prefabName)       // Get weight for prefab
void setWeight(String prefabName, double weight)  // Set weight
void removeWeight(String prefabName)      // Remove weight entry
double getDefaultWeight()                 // Get default weight
void setDefaultWeight(double weight)      // Set default weight
```

### Random Selection
```java
// Select from array using weights
<T> T get(T[] options, Function<T, String> nameExtractor, Random random)

// Select using pre-generated random value (0.0-1.0)
<T> T get(T[] options, Function<T, String> nameExtractor, double randomValue)
```

### Serialization
```java
String getMappingString()                 // Get as parseable string
Set<Entry<String>> entrySet()             // Get all entries
```

### Usage Example
```java
// Create weighted selection
PrefabWeights weights = new PrefabWeights();
weights.setWeight("common_tree", 0.6);
weights.setWeight("rare_tree", 0.3);
weights.setWeight("unique_tree", 0.1);

// Select random prefab
String[] prefabNames = {"common_tree", "rare_tree", "unique_tree"};
Random random = new Random();
String selected = weights.get(prefabNames, name -> name, random);

// Load and place selected prefab
BlockSelection prefab = PrefabStore.get().getServerPrefab("trees/" + selected);
prefab.place(commandSender, world);
```

---

## Prefab Exceptions
**Package:** `com.hypixel.hytale.server.core.prefab`

`PrefabStore` load/save failures surface as two unchecked exceptions, each carrying a `Type` enum that describes the failure category.

### PrefabLoadException
```java
PrefabLoadException(PrefabLoadException.Type type)
PrefabLoadException(PrefabLoadException.Type type, String message)
PrefabLoadException(PrefabLoadException.Type type, String message, Throwable cause)
PrefabLoadException(PrefabLoadException.Type type, Throwable cause)

PrefabLoadException.Type getType()   // ERROR or NOT_FOUND
```

`Type.NOT_FOUND` means the name/path did not resolve to a stored prefab — this is the exception behind the `Could not locate prefab: ` message in [Gotchas & Errors](#gotchas--errors). `Type.ERROR` wraps I/O and parse failures.

### PrefabSaveException
```java
PrefabSaveException(PrefabSaveException.Type type)
PrefabSaveException(PrefabSaveException.Type type, String message)
PrefabSaveException(PrefabSaveException.Type type, String message, Throwable cause)
PrefabSaveException(PrefabSaveException.Type type, Throwable cause)

PrefabSaveException.Type getType()   // ERROR or ALREADY_EXISTS
```

`Type.ALREADY_EXISTS` is thrown by the `PrefabStore` save methods when the target file already exists and overwrite was not requested; `Type.ERROR` wraps everything else.

---

## PrefabCopyableComponent
**Package:** `com.hypixel.hytale.server.core.prefab`

Stateless marker component on `EntityStore` entities. Entities carrying it are the ones collected into a prefab when a world region is saved (the prefab editor's saver iterates only copyable entities in the selection). Because it holds no data, it is a singleton.

```java
static final PrefabCopyableComponent INSTANCE
static final BuilderCodec<PrefabCopyableComponent> CODEC
static ComponentType<EntityStore, PrefabCopyableComponent> getComponentType()
static PrefabCopyableComponent get()      // returns INSTANCE
Component<EntityStore> clone()            // returns INSTANCE (stateless)
```

Attach it to make an entity part of prefab captures:

```java
holder.putComponent(PrefabCopyableComponent.getComponentType(), PrefabCopyableComponent.get());
```

---

## SelectionManager & SelectionProvider
**Package:** `com.hypixel.hytale.server.core.prefab.selection`

Static bridge between core prefab code and whichever plugin owns "the player's current selection". In practice the built-in builder-tools plugin registers itself as the provider, so this is how other code reads a player's clipboard selection without a hard dependency on that plugin.

```java
// SelectionManager — static holder
static void setSelectionProvider(SelectionProvider provider)
static SelectionProvider getSelectionProvider()      // null until a provider registers

// SelectionProvider — the single abstract method
<T extends Throwable> void computeSelectionCopy(
    Ref<EntityStore> ref, Player player,
    ThrowableConsumer<BlockSelection, T> consumer,
    ComponentAccessor<EntityStore> accessor)
```

```java
SelectionProvider provider = SelectionManager.getSelectionProvider();
if (provider != null) {
    provider.computeSelectionCopy(ref, player, selection -> {
        // selection is a BlockSelection copy of the player's current selection
    }, accessor);
}
```

---

## RotateBlockMode
**Package:** `com.hypixel.hytale.server.core.prefab.selection.standard`

Enum controlling which blocks get their per-block rotation value updated when a selection or clipboard is rotated (used by the builder-tools rotate and randomize-clipboard actions).

```java
public enum RotateBlockMode {
    ALL,              // rotate every block's rotation value
    NON_UNIFORM,      // "NonUniform"
    NON_FULL_BLOCKS,  // "NonFullBlocks"
    NOTHING           // "Nothing" — move blocks, keep rotation values untouched
}

static RotateBlockMode fromString(String value)
```

`fromString()` accepts the client-facing spellings `"NonUniform"`, `"NonFullBlocks"`, `"Nothing"`; anything else — including `null` — falls back to `ALL`.

---

## FeedbackConsumer
**Package:** `com.hypixel.hytale.server.core.prefab.selection.standard`

Functional callback for reporting the outcome of selection operations back to a `CommandSender`. `FeedbackConsumer.DEFAULT` is a no-op — pass it when you don't want feedback.

```java
static final FeedbackConsumer DEFAULT   // no-op
void accept(String, int, int, CommandSender, ComponentAccessor<EntityStore>)
```

---

## BlockFilter
**Package:** `com.hypixel.hytale.server.core.prefab.selection.mask`

One positional filter inside a `BlockMask` (the mask type accepted by `BlockSelection.place(...)` and the builder-tools edit operations). A filter tests a position against a `|`-separated block list, optionally at a relative position (above / below / adjacent / cardinal / diagonal), and can be inverted.

### Filter string syntax

Parsed by `BlockFilter.parse(String)`. The leading prefix picks the `BlockFilter.FilterType`; `!` inverts any filter:

| Prefix | FilterType | Tests |
|--------|------------|-------|
| *(none)* | `TargetBlock` | the block at the position itself |
| `!` | *(any)* | invert prefix, combines with the others |
| `>` | `AboveBlock` | the block above |
| `<` | `BelowBlock` | the block below |
| `~` | `AdjacentBlock` | adjacent position |
| `^` | `NeighborBlock` | neighboring position |
| `+n` / `+e` / `+s` / `+w` | `NorthBlock` / `EastBlock` / `SouthBlock` / `WestBlock` | the cardinal neighbor |
| `%xy` / `%xz` / `%zy` | `DiagonalXy` / `DiagonalXz` / `DiagonalZy` | diagonal in that plane |
| `#` | `Selection` | position is inside the current selection (no block list) |

### Key members
```java
BlockFilter(BlockFilter.FilterType type, String[] blocks, boolean inverted)
static BlockFilter parse(String filter)
static BlockFilter.ParsedFilterParts parseComponents(String filter)  // split without resolving
static IntSet parseBlocks(String[] blocks)
static BlockFilter.BlocksAndFluids parseBlocksAndFluids(String[] blocks)

void resolve()                 // map block names → runtime block/fluid ids
boolean hasInvalidBlocks()     // true if any name failed to resolve

BlockFilter.FilterType getBlockFilterType()
String[] getBlocks()
boolean isInverted()

// the actual test (min/max are the selection bounds, used by the Selection type)
boolean isExcluded(ChunkAccessor accessor, int x, int y, int z, Vector3i min, Vector3i max, int blockId)
boolean isExcluded(ChunkAccessor accessor, int x, int y, int z, Vector3i min, Vector3i max, int blockId, int fluidId)

static final String BLOCK_SEPARATOR = "|"
static final Codec<BlockFilter> CODEC
```

`FilterType` itself exposes `getPrefix()`, `hasBlocks()` (the `Selection` type takes no block list), and `parse(String, int)`.

---

## The Prefab Buffer Pipeline

Alongside `BlockSelection` (the editable, builder-tools-facing payload) the server has a second, packed prefab representation used by world generation, the prefab spawner, and anything that stamps prefabs at scale. It flows through four classes:

```
name ("Trees.Oak.Oak_Large_01" or "Trees.Oak.*")
│
│  PrefabLoader.resolvePrefabs      (dotted name → .prefab.json path(s))
▼
path
│
│  PrefabBufferUtil.getCached       (load + weak-ref cache; .lpf binary fast path)
▼
PrefabBuffer ── newAccess() ──▶ IPrefabBuffer   (read view)
│
│  PrefabUtil.paste / remove / canPlacePrefab
▼
World
```

### PrefabLoader
**Package:** `com.hypixel.hytale.server.core.prefab.selection.buffer`

Resolves dot-separated prefab names to files under a root folder. A name ending in `.*` resolves a whole folder recursively.

```java
PrefabLoader(Path rootFolder)
Path getRootFolder()

void resolvePrefabs(String prefabName, Consumer<Path> pathConsumer) throws IOException
static void resolvePrefabs(Path rootFolder, String prefabName, Consumer<Path> pathConsumer) throws IOException
static void resolvePrefabFolder(Path rootFolder, String prefabName, Consumer<Path> pathConsumer) throws IOException
static String resolveRelativeJsonPath(String, Path, Path)
```

`.` is the path separator: `"Trees.Oak.Oak_Large_01"` resolves to `Trees/Oak/Oak_Large_01.prefab.json` under the root. The `.*` folder form walks the directory tree and emits every prefab file it finds (with the `.prefab.json` / `.lpf` suffix stripped — `PrefabBufferUtil` re-resolves the extension). A name that escapes the root folder throws `IllegalArgumentException` with the literal `Invalid prefab name: ` message from [Gotchas & Errors](#gotchas--errors).

### PrefabBufferUtil
**Package:** `com.hypixel.hytale.server.core.prefab.selection.buffer`

Loads prefab files into `PrefabBuffer`s, with a weak-reference cache and a binary fast path: a JSON prefab is converted once to a binary `.lpf` file (written under the prefab cache directory for immutable asset packs, next to the JSON otherwise) and re-read from that on subsequent loads.

```java
static IPrefabBuffer getCached(Path path)      // main entry point: cache hit or loadBuffer()
static PrefabBuffer loadBuffer(Path path)      // .lpf if present, else JSON (+ conversion)

static PrefabBuffer readFromFile(Path path)    // raw binary read
static CompletableFuture<PrefabBuffer> readFromFileAsync(Path path)
static CompletableFuture<Void> writeToFileAsync(PrefabBuffer prefab, Path path)
static PrefabBuffer loadFromLPF(Path path, Path realPath)
static PrefabBuffer loadFromJson(AssetPack pack, Path path, Path cachedLpfPath, Path jsonPath) throws IOException

static final Path CACHE_PATH                   // prefab cache dir (default .cache/prefabs)
static final String LPF_FILE_SUFFIX      = ".lpf"
static final String JSON_FILE_SUFFIX     = ".prefab.json"
static final String JSON_LPF_FILE_SUFFIX = ".prefab.json.lpf"
static final Pattern FILE_SUFFIX_PATTERN
```

`getCached()` is what the rest of the server calls. The cache holds buffers behind `WeakReference`s, so prefabs that nothing is using can be garbage-collected and transparently reloaded later. `loadBuffer()` accepts a path with or without the prefab suffix and probes `.lpf`, `.prefab.json.lpf`, then `.prefab.json` siblings.

### PrefabBuffer & IPrefabBuffer
**Package:** `com.hypixel.hytale.server.core.prefab.selection.buffer.impl`

`PrefabBuffer` is the immutable packed payload — block columns stored in off-heap memory plus an array of child-prefab references. `IPrefabBuffer` is the read interface everything consumes; get one with `newAccess()`.

```java
// PrefabBuffer
static PrefabBuffer.Builder newBuilder()
int getAnchorX() / getAnchorY() / getAnchorZ()
PrefabBuffer.PrefabBufferAccessor newAccess()   // implements IPrefabBuffer
static final float DEFAULT_CHANCE = 1.0f
```

```java
// IPrefabBuffer — bounds & metadata
int getAnchorX() / getAnchorY() / getAnchorZ()
int getMinX() / getMinY() / getMinZ()
int getMaxX() / getMaxY() / getMaxZ()
int getMinX(PrefabRotation) / getMinZ(PrefabRotation)   // rotation-aware bounds
int getMaxX(PrefabRotation) / getMaxZ(PrefabRotation)
int getMinYAt(PrefabRotation, int x, int z)
int getMaxYAt(PrefabRotation, int x, int z)
int getColumnCount()
int getMaximumExtend()
PrefabBuffer.ChildPrefab[] getChildPrefabs()

// direct block access (prefab-local coordinates)
int getBlockId(int x, int y, int z)
int getFiller(int x, int y, int z)
int getRotationIndex(int x, int y, int z)

// iteration — T is a context object threaded through the callbacks
<T extends PrefabBufferCall> void forEach(IPrefabBuffer.ColumnPredicate<T>,
    IPrefabBuffer.BlockConsumer<T>, IPrefabBuffer.EntityConsumer<T>,
    IPrefabBuffer.ChildConsumer<T>, T call)
<T> void forEachEntity(IPrefabBuffer.EntityConsumer<T>, T context)
<T> void forEachRaw(IPrefabBuffer.ColumnPredicate<T>, IPrefabBuffer.RawBlockConsumer<T>,
    IPrefabBuffer.FluidConsumer<T>, IPrefabBuffer.EntityConsumer<T>, T context)
<T> boolean forEachRaw(IPrefabBuffer.ColumnPredicate<T>, IPrefabBuffer.RawBlockPredicate<T>,
    IPrefabBuffer.FluidPredicate<T>, IPrefabBuffer.EntityPredicate<T>, T context)
<T extends PrefabBufferCall> boolean compare(IPrefabBuffer.BlockComparingPredicate<T>, T call)

static final IPrefabBuffer.ColumnPredicate<?> ALL_COLUMNS
static <T> IPrefabBuffer.ColumnPredicate<T> iterateAllColumns()
```

The consumer/predicate types are nested functional interfaces of `IPrefabBuffer`. `forEach` applies the call's `PrefabRotation` to coordinates as it iterates; the `forEachRaw` variants walk the stored data unrotated, and the predicate overload short-circuits on the first `false`. `compare` walks blocks against a predicate and is how `PrefabUtil.prefabMatchesAtPosition` and `PrefabUtil.canPlacePrefab` are implemented.

Buffers can also be built in code:

```java
// PrefabBuffer.Builder
void setAnchor(Vector3i anchor)
PrefabBufferBlockEntry newBlockEntry(int y)
void addColumn(int x, int z, PrefabBufferBlockEntry[] entries, Holder<EntityStore>[] entities)
void addChildPrefab(int x, int y, int z, String path, boolean fitHeightmap,
    boolean inheritSeed, boolean inheritHeightCondition,
    PrefabWeights weights, PrefabRotation rotation)
PrefabBuffer build()
```

**Child prefabs** (`PrefabBuffer.ChildPrefab`) are nested prefab references baked into a parent buffer — the packed form of [Prefab Spawner blocks](#prefabspawnerblock). Accessors: `getX()` / `getY()` / `getZ()`, `getPath()`, `isFitHeightmap()`, `isInheritSeed()`, `isInheritHeightCondition()`, `getWeights()`, `getRotation()`.

### PrefabBufferCall
**Package:** `com.hypixel.hytale.server.core.prefab.selection.buffer`

The context object threaded through `forEach` / `compare` passes, carrying the RNG and the rotation the callbacks should apply. Both fields are public.

```java
public Random random;
public PrefabRotation rotation;

PrefabBufferCall()
PrefabBufferCall(Random random, PrefabRotation rotation)
```

### PrefabUtil
**Package:** `com.hypixel.hytale.server.core.util`

Static stamping operations that apply an `IPrefabBuffer` to a `World` — the programmatic paste path. Pasting fires the same `PrefabPasteEvent` / `PrefabPlaceEntityEvent` documented in [Prefab Events](#prefab-events).

```java
// test before placing
static boolean prefabMatchesAtPosition(IPrefabBuffer buffer, World world,
    Vector3i position, Rotation yaw, Random random)
static boolean canPlacePrefab(IPrefabBuffer buffer, World world, Vector3i position,
    Rotation yaw, IntSet mask, Random random, boolean ignoreOrigin)

// paste
static void paste(IPrefabBuffer buffer, World world, Vector3i position, Rotation yaw,
    boolean force, Random random, ComponentAccessor<EntityStore> accessor)
static void paste(IPrefabBuffer buffer, World world, Vector3i position, Rotation yaw,
    boolean force, Random random, int setBlockSettings,
    ComponentAccessor<EntityStore> accessor)
static void paste(IPrefabBuffer buffer, World world, Vector3i position, Rotation yaw,
    boolean force, Random random, int setBlockSettings, boolean technicalPaste,
    boolean pasteAnchorAsBlock, boolean loadEntities,
    ComponentAccessor<EntityStore> accessor)

// remove a pasted prefab's blocks again
static void remove(IPrefabBuffer buffer, World world, Vector3i position,
    boolean force, Random random, int setBlockSettings)
static void remove(IPrefabBuffer buffer, World world, Vector3i position,
    boolean force, Random random, int setBlockSettings, double brokenParticlesRate)
static void remove(IPrefabBuffer buffer, World world, Vector3i position, Rotation rotation,
    boolean force, Random random, int setBlockSettings, double brokenParticlesRate)

static int getNextPrefabId()   // source of the internal id seen in PrefabPasteEvent.getPrefabId()
```

Rotation here is the block-config `Rotation` enum (`None`, `Ninety`, `OneEighty`, `TwoSeventy`); it is converted internally via `PrefabRotation.fromRotation()`.

### Buffer pipeline example

```java
import com.hypixel.hytale.server.core.asset.type.blocktype.config.Rotation;
import com.hypixel.hytale.server.core.prefab.PrefabStore;
import com.hypixel.hytale.server.core.prefab.selection.buffer.PrefabBufferUtil;
import com.hypixel.hytale.server.core.prefab.selection.buffer.PrefabLoader;
import com.hypixel.hytale.server.core.prefab.selection.buffer.impl.IPrefabBuffer;
import com.hypixel.hytale.server.core.util.PrefabUtil;

// Resolve every oak-tree prefab under the world-gen prefab root and stamp one
PrefabLoader loader = new PrefabLoader(PrefabStore.get().getWorldGenPrefabsPath());
try {
    loader.resolvePrefabs("Trees.Oak.*", path -> {
        IPrefabBuffer buffer = PrefabBufferUtil.getCached(path);
        if (PrefabUtil.canPlacePrefab(buffer, world, pos, Rotation.None, null, random, false)) {
            PrefabUtil.paste(buffer, world, pos, Rotation.None, false, random, accessor);
        }
    });
} catch (IOException e) {
    // root folder missing / unreadable
}
```

---

## PrefabSpawnerBlock
**Package:** `com.hypixel.hytale.server.core.modules.prefabspawner`

Chunk-store component holding the configuration of a Prefab Spawner block — the world-building block that stamps another prefab when its host prefab is placed. The core `PrefabSpawnerModule` registers it under the id `"PrefabSpawner"`, and the in-game settings page edits the same fields. When a region containing a spawner block is saved into a prefab buffer, the spawner's settings are baked into a `PrefabBuffer.ChildPrefab` entry instead of a block (see [the buffer pipeline](#the-prefab-buffer-pipeline)).

```java
static ComponentType<ChunkStore, PrefabSpawnerBlock> getComponentType()

PrefabSpawnerBlock()
PrefabSpawnerBlock(String prefabPath, boolean fitHeightmap, boolean inheritSeed,
                   boolean inheritHeightCondition, PrefabWeights prefabWeights)

String getPrefabPath()               / void setPrefabPath(String)
boolean isFitHeightmap()             / void setFitHeightmap(boolean)
boolean isInheritSeed()              / void setInheritSeed(boolean)
boolean isInheritHeightCondition()   / void setInheritHeightCondition(boolean)
PrefabWeights getPrefabWeights()     / void setPrefabWeights(PrefabWeights)

static final BuilderCodec<PrefabSpawnerBlock> CODEC
```

A spawner with no prefab path logs a warning and is skipped when the containing prefab is packed.

---

## PrefabListAsset
**Package:** `com.hypixel.hytale.server.core.asset.type.buildertool.config`

The Java asset type behind `Server/PrefabList/*.json` files (format documented in [PrefabList Files](#prefablist-files)). Each asset expands its references into a flat list of prefab file paths.

```java
static AssetStore<String, PrefabListAsset, DefaultAssetMap<String, PrefabListAsset>> getAssetStore()
static DefaultAssetMap<String, PrefabListAsset> getAssetMap()

String getId()
Path[] getPrefabPaths()                              // expanded list of prefab files
PrefabListAsset.PrefabReference[] getPrefabReferences()
Path getRandomPrefab()                               // random pick from the expanded paths

static final AssetBuilderCodec<String, PrefabListAsset> CODEC
```

`PrefabListAsset.PrefabReference` mirrors one entry of the JSON `Prefabs` array — public fields `rootDirectory`, `unprocessedPrefabPath`, `recursive`, `prefabPaths`, plus `processPrefabPath()` which expands the reference into concrete paths. The `PrefabListAsset.PrefabRootDirectory` enum has **three** values — `Server`, `Asset`, and `Worldgen` (each exposing `getPrefabPath()` for its root) — one more than the two shown in the JSON table below.

```java
PrefabListAsset list = PrefabListAsset.getAssetMap().getAsset("MyMod_Trees");
Path prefab = list.getRandomPrefab();
```

---

## Prefab Events

Events related to prefab pasting and entity placement from prefabs.

> **See also:** [ECS Event Systems](components.md#event-type-registration)

**Package:** `com.hypixel.hytale.server.core.prefab.event`

### Event Summary

| Class | Description | Cancellable |
|-------|-------------|-------------|
| `PrefabPasteEvent` | Prefab is being pasted into world (ECS) | Yes |
| `PrefabPlaceEntityEvent` | Entity placed from prefab (ECS) | No |

---

### PrefabPasteEvent

ECS event fired when a prefab is being pasted into the world. Extends `CancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPrefabId()` | `int` | Internal ID of the prefab being pasted |
| `isPasteStart()` | `boolean` | True if this is the start of pasting, false if end |
| `isCancelled()` | `boolean` | Whether the paste is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the paste |

> **Note:** `getPrefabId()` returns an internal integer ID, not the string path used with `PrefabStore`.

---

### PrefabPlaceEntityEvent

ECS event fired when an entity is placed as part of a prefab. Extends `EcsEvent` (not cancellable).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPrefabId()` | `int` | ID of the prefab containing this entity |
| `getHolder()` | `Holder<EntityStore>` | Entity holder for the placed entity |

---

### Prefab Events Usage

Prefab events are ECS events, so handle them using an `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.prefab.event.PrefabPasteEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class PrefabPasteSystem extends EntityEventSystem<EntityStore, PrefabPasteEvent> {

    public PrefabPasteSystem() {
        super(PrefabPasteEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PrefabPasteEvent event) {
        if (event.isPasteStart()) {
            System.out.println("Starting to paste prefab: " + event.getPrefabId());
        } else {
            System.out.println("Finished pasting prefab: " + event.getPrefabId());
        }

        // Optionally cancel the paste
        // event.setCancelled(true);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return null; // Or a specific component type
    }
}
```

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.prefab.event.PrefabPlaceEntityEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class PrefabPlaceEntitySystem extends EntityEventSystem<EntityStore, PrefabPlaceEntityEvent> {

    public PrefabPlaceEntitySystem() {
        super(PrefabPlaceEntityEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PrefabPlaceEntityEvent event) {
        var holder = event.getHolder();
        System.out.println("Entity placed from prefab " + event.getPrefabId() + ": " + holder);
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
    getEntityStoreRegistry().registerSystem(new PrefabPasteSystem());
    getEntityStoreRegistry().registerSystem(new PrefabPlaceEntitySystem());
}
```

---

## Complete Usage Example

```java
import com.hypixel.hytale.math.Axis;
import org.joml.Vector3i;
import com.hypixel.hytale.server.core.prefab.PrefabStore;
import com.hypixel.hytale.server.core.prefab.PrefabRotation;
import com.hypixel.hytale.server.core.prefab.PrefabWeights;
import com.hypixel.hytale.server.core.prefab.selection.standard.BlockSelection;

@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    PrefabStore prefabStore = PrefabStore.get();

    // Load a prefab
    BlockSelection building = prefabStore.getServerPrefab("buildings/small_house");
    if (building == null) {
        playerRef.sendMessage(Message.raw("Prefab not found!"));
        return;
    }

    // Get player position
    Transform transform = playerRef.getTransform();
    Vector3i placePos = new Vector3i(
        (int) transform.getPosition().x() + 5,
        (int) transform.getPosition().y(),
        (int) transform.getPosition().z()
    );

    // Rotate 90 degrees
    BlockSelection rotated = building.rotate(Axis.Y, 90);

    // Place in world
    BlockSelection undo = rotated.place(playerRef, world, placePos, null);

    playerRef.sendMessage(Message.raw("Placed building with " +
        building.getBlockCount() + " blocks at " + placePos));

    // Store undo for later if needed
    // undoStack.push(undo);
}
```

---

## Prefab File Format

Prefabs are stored as `.prefab.json` files (or compressed `.prefab.json.lpf` files) in the assets.

### File Locations

| Location | Path | Description |
|----------|------|-------------|
| **Asset Prefabs** | `Assets.zip > Prefabs/` | World generation prefabs (trees, rocks, structures) |
| **Server Prefabs** | `Server/Prefabs/` | Server-side prefabs for plugins |
| **World Gen Prefabs** | `Assets.zip > Prefabs/` | Referenced by world generation |
| **Asset Pack Prefabs** | `{AssetPack}/Prefabs/` | Custom prefabs from mods |

**Compression:** Most asset prefabs use `.prefab.json.lpf` compression (LZ4 frame format). The game automatically handles decompression when loading.

### Root Schema (Version 8)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | int | Yes | - | Format version (current: 8) |
| `blockIdVersion` | int | No | 0 | Block ID version for compatibility |
| `anchorX` | int | No | 0 | Anchor X position (placement origin) |
| `anchorY` | int | No | 0 | Anchor Y position (placement origin) |
| `anchorZ` | int | No | 0 | Anchor Z position (placement origin) |
| `blocks` | array | No | [] | Array of block entries |
| `fluids` | array | No | [] | Array of fluid entries |
| `entities` | array | No | [] | Array of entity entries |

### Block Entry Properties

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `x` | int | Yes | - | X position relative to anchor |
| `y` | int | Yes | - | Y position relative to anchor |
| `z` | int | Yes | - | Z position relative to anchor |
| `name` | string | Yes | - | Block type name (e.g., `"Stone"`, `"Furniture_Chair_Wood"`) |
| `rotation` | int | No | 0 | Block rotation (0=North, 1=East, 2=South, 3=West) |
| `filler` | int | No | 0 | Filler value for multi-block structures |
| `supportValue` | int | No | 0 | Structural support value |
| `components` | object | No | null | ECS component overrides |

**Rotation Values:**

| Value | Direction | Degrees |
|-------|-----------|---------|
| 0 | North | 0° |
| 1 | East | 90° clockwise |
| 2 | South | 180° |
| 3 | West | 270° clockwise |

### Components Structure

Block components allow attaching ECS data to placed blocks. The most common use is configuring containers with loot tables.

```json
{
  "components": {
    "Components": {
      "container": {
        "Droplist": "Prefabs/Zone1/Chest_Common",
        "ItemContainer": { "Capacity": 18 }
      }
    }
  }
}
```

**Container Component Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `Droplist` | string | Drop file reference (see [Drop System](drops.md)) |
| `ItemContainer` | object | Container configuration |
| `ItemContainer.Capacity` | int | Number of inventory slots |

**Example: Chest with Zone-Based Loot:**

```json
{
  "components": {
    "Components": {
      "container": {
        "Droplist": "Prefabs/Zone2/Chest_Rare",
        "ItemContainer": { "Capacity": 27 }
      }
    }
  }
}
```

### Fluid Entry Properties

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | int | Yes | X position relative to anchor |
| `y` | int | Yes | Y position relative to anchor |
| `z` | int | Yes | Z position relative to anchor |
| `name` | string | Yes | Fluid type name (e.g., `"Water"`, `"Lava"`) |
| `level` | int | No | Fluid level (0-15, 15 = full block) |

**Example: Water Pool Prefab:**

```json
{
  "version": 8,
  "anchorX": 0,
  "anchorY": 0,
  "anchorZ": 0,
  "fluids": [
    { "x": 0, "y": 0, "z": 0, "name": "Water", "level": 15 },
    { "x": 1, "y": 0, "z": 0, "name": "Water", "level": 15 },
    { "x": 0, "y": 0, "z": 1, "name": "Water", "level": 15 },
    { "x": 1, "y": 0, "z": 1, "name": "Water", "level": 15 }
  ]
}
```

### Entity Entry Properties

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `x` | float | Yes | X position relative to anchor |
| `y` | float | Yes | Y position relative to anchor |
| `z` | float | Yes | Z position relative to anchor |
| `type` | string | Yes | Entity prefab ID |
| `components` | object | No | Component overrides for the entity |

**Example: Prefab with Spawned NPC:**

```json
{
  "version": 8,
  "anchorX": 0,
  "anchorY": 0,
  "anchorZ": 0,
  "blocks": [
    { "x": 0, "y": 0, "z": 0, "name": "Stone_Brick" }
  ],
  "entities": [
    { "x": 0.5, "y": 1.0, "z": 0.5, "type": "Npc_Kweebec_Villager" }
  ]
}
```

### Complete Examples

**Simple Single-Block Prefab:**

```json
{
  "version": 8,
  "blockIdVersion": 0,
  "anchorX": 0,
  "anchorY": 0,
  "anchorZ": 0,
  "blocks": [
    { "x": 0, "y": 0, "z": 0, "name": "Stone" }
  ]
}
```

**Container with Loot Table:**

```json
{
  "version": 8,
  "blockIdVersion": 0,
  "anchorX": 0,
  "anchorY": 0,
  "anchorZ": 0,
  "blocks": [
    {
      "x": 0,
      "y": 0,
      "z": 0,
      "name": "Furniture_Goblin_Chest_Small",
      "rotation": 1,
      "components": {
        "Components": {
          "container": {
            "Droplist": "Prefabs/Zone1/Chest_Uncommon",
            "ItemContainer": { "Capacity": 18 }
          }
        }
      }
    }
  ]
}
```

**Multi-Block Building with Rotations:**

```json
{
  "version": 8,
  "blockIdVersion": 0,
  "anchorX": 1,
  "anchorY": 0,
  "anchorZ": 1,
  "blocks": [
    { "x": 0, "y": 0, "z": 0, "name": "Stone_Brick" },
    { "x": 1, "y": 0, "z": 0, "name": "Stone_Brick" },
    { "x": 2, "y": 0, "z": 0, "name": "Stone_Brick" },
    { "x": 0, "y": 0, "z": 1, "name": "Stone_Brick" },
    { "x": 2, "y": 0, "z": 1, "name": "Stone_Brick" },
    { "x": 0, "y": 0, "z": 2, "name": "Stone_Brick" },
    { "x": 1, "y": 0, "z": 2, "name": "Stone_Brick" },
    { "x": 2, "y": 0, "z": 2, "name": "Stone_Brick" },
    { "x": 1, "y": 0, "z": 0, "name": "Furniture_Door_Wood", "rotation": 0 },
    { "x": 1, "y": 1, "z": 0, "name": "Furniture_Door_Wood_Top", "rotation": 0 }
  ]
}
```

### PrefabList Files

`Server/PrefabList/*.json` files reference directories of prefabs for world generation. They allow grouping related prefabs for procedural placement.

```json
{
  "Prefabs": [
    {
      "RootDirectory": "Asset",
      "Path": "Trees/Oak/",
      "Recursive": true
    }
  ]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `RootDirectory` | string | `"Asset"` for asset prefabs, `"Server"` for server prefabs |
| `Path` | string | Relative path to prefab directory |
| `Recursive` | boolean | Include subdirectories |

**Example: Multi-Source PrefabList:**

```json
{
  "Prefabs": [
    {
      "RootDirectory": "Asset",
      "Path": "Rock_Formations/Rocks/Stone/",
      "Recursive": true
    },
    {
      "RootDirectory": "Asset",
      "Path": "Rock_Formations/Pillars/",
      "Recursive": false
    }
  ]
}
```

---

## Integration Points

Prefabs integrate with several other systems in Hytale.

### Drop System Integration

Container blocks in prefabs can reference drop files to populate loot:

```json
{
  "components": {
    "Components": {
      "container": {
        "Droplist": "Prefabs/Zone1/Chest_Rare"
      }
    }
  }
}
```

The `Droplist` property references files in `Server/Drops/`. When the container is opened, items are generated according to the drop file's weighted random selection.

> **See also:** [Drop System](drops.md) for loot table configuration

### Interaction System Integration

The `SpawnPrefab` interaction can paste a prefab into the world during an interaction
chain — e.g. the Goblin Thief dropping its loot chest
(`Server/Item/Interactions/NPCs/Intelligent/Goblin_Thief/Goblin_Thief_Chest.json`):

```json
{
  "Type": "SpawnPrefab",
  "PrefabPath": "Goblin_Thief_Chest.prefab.json",
  "Offset": { "X": 0, "Y": 0, "Z": 0 },
  "RotationYaw": "OneEighty",
  "OriginSource": "Entity",
  "Force": true
}
```

> **See also:** [SpawnPrefab Interaction](interactions-world.md#spawnprefab)

### Event Handling

Prefab operations fire events that can be handled by plugin systems:

| Event | Description | Cancellable |
|-------|-------------|-------------|
| `PrefabPasteEvent` | Prefab being pasted into world | Yes |
| `PrefabPlaceEntityEvent` | Entity placed from prefab | No |

```java
public class PrefabPasteSystem extends EntityEventSystem<EntityStore, PrefabPasteEvent> {
    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PrefabPasteEvent event) {
        if (event.isPasteStart()) {
            // Prefab paste starting
        }
    }
}
```

> **See also:** [Prefab Events](#prefab-events) for full event documentation

### World Generation Integration

World generation uses prefabs for placing structures, trees, and rock formations. PrefabList files group related prefabs:

```json
{
  "Prefabs": [
    {
      "RootDirectory": "Asset",
      "Path": "Trees/Oak/",
      "Recursive": true
    }
  ]
}
```

The world generator selects prefabs from these lists based on biome rules and placement constraints.

> **See also:** [Prefab Categories](prefabs-categories.md) for the full taxonomy of world generation prefabs

---

## Notes

- BlockSelection is the actual prefab data structure - it contains blocks, fluids, and entities
- Use `PrefabStore.get()` to access the singleton store
- Placement returns an undo BlockSelection that can be placed to revert changes
- Rotations create new BlockSelection instances (immutable pattern)
- Prefab files are typically stored in the server's prefabs directory
- PrefabWeights allows weighted random selection for variety in procedural generation

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 prefab system (verified against `HytaleServer.jar`).

- **`Could not locate prefab: `** → a prefab path/name handed to `PrefabStore` does not resolve to a stored prefab. Fix: use the exact string path the prefab is registered under (case-sensitive), not the internal integer id from `getPrefabId()`.
- **`Invalid prefab name: `** / **`Invalid prefab path: `** → an empty or malformed prefab name/path was supplied. Fix: pass a non-empty, well-formed name/path.
- **`PrefabList asset not found: `** → a referenced `PrefabList` asset id does not exist. Fix: confirm the `Server/PrefabList/*.json` file exists and the id matches exactly.
- **`prefab pool contains list with null element`** → a weighted prefab pool was built with a null member. Fix: ensure every pool entry is populated and non-null. (An `empty list` sibling message existed through build-17 but was removed by 0.5.7 — an empty pool no longer throws that exact string.)
- **`Cannot have a negative y level for pasting prefabs`** → a paste/placement was requested at a negative Y. Fix: place prefabs at a non-negative Y level.

---

## Related Documentation

- [Prefab Categories](prefabs-categories.md) - Full taxonomy of all 2,455+ prefab files
- [Drop System](drops.md) - Loot table configuration for containers
- [SpawnPrefab Interaction](interactions-world.md#spawnprefab) - Spawning prefabs via interactions
- [World API](world.md) - World and chunk operations
- [Block System](blocks.md) - Block types and properties

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
