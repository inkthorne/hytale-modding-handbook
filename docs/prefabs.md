---
title: "Prefabs API"
description: "Work with Hytale prefabs in Java — the PrefabStore for loading/saving server, asset, and world-gen prefabs, BlockSelection payloads of blocks/fluids/entities, and placement with rotation."
seo:
  type: TechArticle
---

# Prefabs API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Prefabs` · **Verified against build-12**

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

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Categories Reference](prefabs-categories.md) | `prefabs-categories.md` | Trees, Rocks, NPCs, Dungeons (2,455+ files) |
| [File Format](#prefab-file-format) | Below | JSON schema, blocks, fluids, entities |
| [Java API](#prefabstore) | Below | PrefabStore, BlockSelection, Events |

---

## Class Hierarchy
```
PrefabStore                    (central storage and loading)
BlockSelection                 (prefab data: blocks, fluids, entities)
PrefabEntry                    (prefab file metadata)
PrefabRotation                 (rotation enum)
PrefabWeights                  (weighted random selection)
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
    (int) transform.getPosition().getX(),
    (int) transform.getPosition().getY(),
    (int) transform.getPosition().getZ()
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
import com.hypixel.hytale.math.vector.Vector3i;
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
        (int) transform.getPosition().getX() + 5,
        (int) transform.getPosition().getY(),
        (int) transform.getPosition().getZ()
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

The `SpawnPrefab` interaction can spawn entity prefabs during combat or ability execution:

```json
{
  "Type": "SpawnPrefab",
  "PrefabId": "Skeleton_Fighter_Random_Weapon",
  "Position": "Self",
  "Count": 3,
  "Offset": [0, 0, 2]
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
- **`prefab pool contains empty list`** / **`prefab pool contains list with null element`** → a weighted prefab pool was built with an empty entry list or a null member. Fix: ensure every pool entry is populated and non-null.
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
