---
title: "Blocks Java API"
description: "The Java side of Hytale blocks — BlockType, BlockMaterial, Rotation and RotationTuple, block ticking and block events, block health and fragility, and authoring custom block-entity components."
seo:
  type: TechArticle
---

# Blocks Java API

**Doc type:** Java API · **Verified against 0.7.2**

Split out of [blocks.md](blocks.md) at the seam recorded in `maintenance/page-size-arrears.txt`.
Everything a plugin touches from Java: the `BlockType` configuration class and the enums and
structures around it, the ticking and event systems, the block-health subsystem, and a full
walkthrough for authoring custom block-entity components. Reading and writing blocks in the world is
on [block-access.md](block-access.md). The **JSON** that configures blocks is in [blocks.md](blocks.md), and the connected-block rule sets are in
[blocks-connected.md](blocks-connected.md).

---

## Java API Reference

### BlockType
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Core class representing a block type configuration. Provides access to all block properties including material, textures, sounds, and behavior settings.

#### Constants
```java
static final BlockType EMPTY;      // Empty/air block
static final BlockType UNKNOWN;    // Unknown block placeholder
static final BlockType DEBUG_CUBE; // Debug cube block
static final BlockType DEBUG_MODEL;// Debug model block

static final String EMPTY_KEY;     // Key for empty block
static final String UNKNOWN_KEY;   // Key for unknown block
static final int EMPTY_ID;         // ID for empty block
static final int UNKNOWN_ID;       // ID for unknown block
```

#### Static Methods
```java
// Get block from string identifier
static BlockType fromString(String id)

// Access the block asset store
static AssetStore<String, BlockType, ...> getAssetStore()
static BlockTypeAssetMap<String, BlockType> getAssetMap()

// Get unknown block for a specific key
static BlockType getUnknownFor(String key)

// Get block ID with fallback to unknown
static int getBlockIdOrUnknown(String key, String context, Object... args)
```

#### Core Properties
```java
String getId()                    // Block identifier
String getGroup()                 // Block group/category
boolean isUnknown()               // Check if this is an unknown block
boolean isState()                 // Check if this is a block state
Item getItem()                    // Get associated item (if any)
```

#### Material & Rendering
```java
BlockMaterial getMaterial()       // Get block material (Empty/Solid)
DrawType getDrawType()            // How the block is drawn
Opacity getOpacity()              // Block opacity
BlockFlags getFlags()             // Block flags (various properties)
ColorLight getLight()             // Light emission
```

#### Textures & Model
```java
BlockTypeTextures[] getTextures() // Block textures
String getCustomModel()           // Custom model path (if any)
float getCustomModelScale()       // Custom model scale
String getCustomModelAnimation()  // Custom model animation
float getCustomModelAnimationSpeed() // 0.6.3+: playback multiplier for that animation
CustomModelTexture[] getCustomModelTexture()
```

#### Sounds & Particles
```java
String getBlockSoundSetId()       // Sound set identifier
int getBlockSoundSetIndex()       // Sound set index
ModelParticle[] getParticles()    // Particle effects
String getBlockParticleSetId()    // Particle set identifier
Color getParticleColor()          // Particle color
String getBlockBreakingDecalId()  // Breaking decal texture
```

#### Rotation & Placement
```java
Rotation getRotationYawPlacementOffset()    // Rotation offset when placed
RandomRotation getRandomRotation()          // Random rotation settings
VariantRotation getVariantRotation()        // Variant rotation settings
BlockFlipType getFlipType()                 // Flip behavior
BlockPlacementSettings getPlacementSettings()// Placement rules
```

#### Collision & Interaction
```java
String getHitboxType()                      // Collision hitbox type
int getHitboxTypeIndex()                    // Collision hitbox index
String getInteractionHitboxType()           // Interaction hitbox type
int getInteractionHitboxTypeIndex()         // Interaction hitbox index
String getInteractionHint()                 // UI interaction hint
boolean isTrigger()                         // Is this a trigger block
int getDamageToEntities()                   // Damage dealt to entities
Map<InteractionType, String> getInteractions()// Interaction mappings
```

#### Block States
```java
BlockType getBlockForState(String state)    // Get block for named state
String getBlockKeyForState(String state)    // Get block key for state
String getDefaultStateKey()                 // Default state key
String getStateForBlock(BlockType block)    // Get state name for block
String getStateForBlock(String blockKey)    // Get state name for key
StateData getState()                        // Get state data config
```

#### Movement & Support
```java
BlockMovementSettings getMovementSettings() // Movement properties
SupportDropType getSupportDropType()        // Support drop behavior
int getMaxSupportDistance()                 // Max support distance
boolean isFullySupportive()                 // Fully supports neighbors
boolean hasSupport()                        // Has support requirements
Map<BlockFace, RequiredBlockFaceSupport[]> getSupport(int rotation)
Map<BlockFace, BlockFaceSupport[]> getSupporting(int rotation)
```

#### Other Properties
```java
ConnectedBlockRuleSet getConnectedBlockRuleSet()
RotatedMountPointsArray getSeats()          // Seat mount points
RotatedMountPointsArray getBeds()           // Bed mount points
TickProcedure getTickProcedure()            // Tick behavior
ShaderType[] getEffect()                    // Shader effects
Bench getBench()                            // Crafting bench data
BlockGathering getGathering()               // Gathering/farming data
FarmingData getFarming()                    // Farming configuration
Holder<ChunkStore> getBlockEntity()         // Block entity template
RailConfig getRailConfig(int rotation)      // Rail configuration
boolean isDoor()                            // @Deprecated; JSON "IsDoor" (still read by DoorInteraction)
boolean canBePlacedAsDeco()                 // Can be deco placement
void getBlockCenter(int rotation, Vector3d out)// Get block center
```

---

### BlockMaterial
**Package:** `com.hypixel.hytale.protocol`

Simple enum representing the physical material type of a block.

```java
public enum BlockMaterial {
    Empty,  // No collision/air
    Solid   // Solid block with collision
}
```

#### Methods
```java
int getValue()                              // Get numeric value
static BlockMaterial fromValue(int value)   // Get from numeric value
static BlockMaterial[] values()             // All values
static BlockMaterial valueOf(String name)   // Get by name
```

---

### Rotation
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Enum representing 90-degree rotation increments around an axis.

```java
public enum Rotation {
    None,       // 0 degrees
    Ninety,     // 90 degrees
    OneEighty,  // 180 degrees
    TwoSeventy  // 270 degrees
}
```

#### Constants
```java
static final Rotation[] VALUES; // All rotation values
static final Rotation[] NORMAL; // Normal rotations subset
```

#### Methods
```java
int getDegrees()                 // Get rotation in degrees (0, 90, 180, 270)
double getRadians()              // Get rotation in radians
Axis getAxisOfAlignment()        // Get alignment axis
Vector3ic getAxisDirection()     // Get axis direction vector (read-only view)

// Rotation operations
Rotation flip()                  // Flip rotation
Rotation flip(Axis axis)         // Flip around axis
Rotation add(Rotation other)     // Add rotations
Rotation subtract(Rotation other)// Subtract rotations

// Vector rotation methods
Vector3i rotateX(Vector3i v, Vector3i out)
Vector3f rotateX(Vector3f v, Vector3f out)
Vector3d rotateX(Vector3d v, Vector3d out)
Vector3i rotateY(Vector3i v, Vector3i out)
Vector3f rotateY(Vector3f v, Vector3f out)
Vector3d rotateY(Vector3d v, Vector3d out)
Vector3i rotateZ(Vector3i v, Vector3i out)
Vector3f rotateZ(Vector3f v, Vector3f out)
Vector3d rotateZ(Vector3d v, Vector3d out)
Vector3i rotateYaw(Vector3i v, Vector3i out)
Vector3f rotateYaw(Vector3f v, Vector3f out)
Vector3i rotatePitch(Vector3i v, Vector3i out)
Vector3f rotatePitch(Vector3f v, Vector3f out)

// Static rotation methods (there is no static two-argument `add` — use the instance `add`)
static Rotation ofDegrees(int degrees)           // Get from degrees
static Rotation closestOfDegrees(float degrees)  // Closest to degrees
static Vector3i rotate(Vector3ic v, Rotation yaw, Rotation pitch)
static Vector3i rotate(Vector3ic v, Rotation yaw, Rotation pitch, Rotation roll)
static Vector3f rotate(Vector3fc v, Rotation yaw, Rotation pitch, Rotation roll)
static Vector3d rotate(Vector3dc v, Rotation yaw, Rotation pitch, Rotation roll)

// In-place variants (mutate the argument)
static void applyRotationTo(Vector3i v, Rotation yaw, Rotation pitch, Rotation roll)
static void applyRotationTo(Vector3f v, Rotation yaw, Rotation pitch, Rotation roll)
static void applyRotationTo(Vector3d v, Rotation yaw, Rotation pitch, Rotation roll)
static void applyRotationTo(Rotation3f r, Rotation yaw, Rotation pitch, Rotation roll)
static void undoRotationTo(Vector3i v, Rotation yaw, Rotation pitch, Rotation roll)  // and Vector3f / Vector3d

Rotation toInverse()             // The rotation that undoes this one
```

---

### RotationTuple
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Java record combining yaw, pitch, and roll rotations. Used for block placement rotation (see `PlaceBlockEvent.getRotation()`).

```java
public record RotationTuple(int index, Rotation yaw, Rotation pitch, Rotation roll) {
}
```

#### Constants
```java
static final RotationTuple NONE;       // No rotation (all None)
static final int NONE_INDEX;           // Index of NONE
static final RotationTuple[] VALUES;   // All possible rotation tuples
```

#### Factory Methods
```java
// Create from components
static RotationTuple of(Rotation yaw, Rotation pitch, Rotation roll)
static RotationTuple of(Rotation yaw, Rotation pitch)  // roll = None

// Get by index
static RotationTuple get(int index)

// Compute index from components
static int index(Rotation yaw, Rotation pitch, Rotation roll)
```

#### Record Components (Accessors)
```java
int index()        // Pre-computed index
Rotation yaw()     // Yaw rotation
Rotation pitch()   // Pitch rotation
Rotation roll()    // Roll rotation
```

#### Methods
```java
// Apply rotation to vector
Vector3d rotatedVector(Vector3d v)

// Get rotation from array
static RotationTuple getRotation(RotationTuple[] rotations,
                                  RotationTuple tuple, Rotation yaw)
```

#### Usage Example
```java
// In a PlaceBlockEvent handler
PlaceBlockEvent event = ...;
RotationTuple rotation = event.getRotation();

// Access individual components
Rotation yaw = rotation.yaw();
Rotation pitch = rotation.pitch();
Rotation roll = rotation.roll();

// Modify rotation
RotationTuple newRotation = RotationTuple.of(
    Rotation.Ninety,
    Rotation.None,
    Rotation.None
);
event.setRotation(newRotation);
```

---

### Gathering Drop Types
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

These classes back the `Gathering` JSON object (see [Gathering Configuration](blocks.md#gathering-configuration)). `BlockType.getGathering()` returns a `BlockGathering` whose codec maps each gathering mode to its own config class:

| JSON key (under `Gathering`) | Class | Accessor on `BlockGathering` |
|------------------------------|-------|------------------------------|
| `Breaking` | `BlockBreakingDropType` | `getBreaking()` |
| `Harvest` | `HarvestingDropType` | `getHarvest()` |
| `Soft` | `SoftBlockDropType` | `getSoft()` |
| `Physics` | `PhysicsDropType` | `getPhysics()` |

`BlockGathering` also exposes `isHarvestable()`, `isSoft()`, `getToolData()` (the `Tools` JSON key, decoded to a `Map<String, BlockGathering.BlockToolData>` keyed by gather type), and `shouldUseDefaultDropWhenPlaced()` (JSON `UseDefaultDropWhenPlaced`).

#### BlockBreakingDropType

Decodes `Gathering.Breaking` — JSON keys `GatherType`, `Quality`, `ItemId`, `Quantity`, `DropList`:

```java
String getGatherType()   // Tool category that gathers this block ("Rocks", "Woods", ...)
int getQuality()         // Quality override on the produced item
int getQuantity()        // Direct-drop quantity
String getItemId()       // Item produced directly (alternative to a drop list)
String getDropListId()   // Drop table reference (JSON "DropList")
BlockBreakingDropType withoutDrops() // Copy that keeps the gather type but drops nothing
```

#### HarvestingDropType

Decodes `Gathering.Harvest` — JSON keys `ItemId`, `DropList`:

```java
String getItemId()
String getDropListId()
HarvestingDropType withoutDrops()
```

#### SoftBlockDropType

Decodes `Gathering.Soft` — JSON keys `ItemId`, `DropList`, `IsWeaponBreakable`:

```java
String getItemId()
String getDropListId()
boolean isWeaponBreakable()  // Block can also be broken by weapon hits
SoftBlockDropType withoutDrops()
```

---

### BlockSupportsRequiredForType
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Enum behind the `BlockType` JSON key `SupportsRequiredFor`. When a block declares support requirements (see [Support System](items-blocks.md#support-system)), this decides whether **any one** satisfied direction keeps the block alive or **all** declared directions must hold.

```java
public enum BlockSupportsRequiredForType {
    Any,  // One satisfied support direction is enough
    All   // Every declared support direction must be satisfied
}
```

The default is `All`; no shipped block overrides it in JSON.

---

### BlockMountPoint
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.mountpoints`

One sit/sleep mount point on a block — the entries of the `Seats` and `Beds` arrays in `BlockType` JSON (`BlockType.getSeats()` / `BlockType.getBeds()` return the rotation-aware `RotatedMountPointsArray` wrapper). Per-entry JSON keys: `Offset` (relative to the block center at `.5,.5,.5`; forward on a chair is positive Z) and `Yaw` (degrees).

```json
{
  "BlockType": {
    "Seats": [
      { "Offset": { "X": 0, "Y": 0, "Z": 0.12 }, "Yaw": 0 }
    ]
  }
}
```
*(from `Furniture_Kweebec_Stool.json`)*

```java
static final BlockMountPoint[] EMPTY_ARRAY;

Vector3dc getOffset()             // Offset from the block center
float getYawOffSetDegrees()       // Yaw offset for the seated model, in degrees
BlockMountPoint rotate(Rotation yaw, Rotation pitch, Rotation roll) // Rotated copy
Vector3d computeWorldSpacePosition(Vector3i blockPos) // Absolute world position of the mount
Rotation3f computeRotationEuler(int rotationIndex)    // Final rotation for a placed variant
```

---

### FallingBlockSettings
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.fallingblocks`

Backs the `BlockType` JSON key `FallingBlockSettings` — blocks that detach and fall as entities when unsupported (sand-style). `BlockType.getFallingBlockSettings()` returns it.

```json
{
  "BlockType": {
    "FallingBlockSettings": {
      "HitboxCollisionConfig": "HardCollision",
      "Impact": { "Type": "Explode" }
    }
  }
}
```
*(from `Server/Item/Items/_Debug/Debug_Falling_Explosive.json`)*

```java
static final FallingBlockSettings DEFAULT;

FallingBlockImpact getImpact()          // What happens when the falling entity lands
String getHitboxCollisionConfigId()     // JSON "HitboxCollisionConfig"
```

`FallingBlockImpact` is the abstract landing behavior; its codec dispatches on the `Impact.Type` key. The shipped falling-blocks plugin registers `"Place"` (default — the block is placed back), `"Break"`, and `"Explode"`:

```java
public abstract class FallingBlockImpact {
    public static final CodecMapCodec<FallingBlockImpact> CODEC;   // dispatches on "Type"
    public static final BuilderCodec<FallingBlockImpact> BASE_CODEC;

    // Signature changed in 0.6.3: the first argument became a Ref<ChunkStore>, and the
    // falling entity's own Ref plus an EntityStore CommandBuffer were added. The ref is the
    // SECTION at the landing position (FallingBlockTickingSystem resolves it with
    // getChunkSectionReferenceAtBlock), ready for BlockOperations.setBlock.
    public abstract void apply(Ref<ChunkStore> sectionRef, World world, BlockType blockType,
                               Vector3d position, RotationTuple rotation,
                               Store<EntityStore> store, Ref<EntityStore> fallingEntity,
                               CommandBuffer<EntityStore> buffer);
}
```

A plugin can add its own impact by subclassing and calling `FallingBlockImpact.CODEC.register("MyImpact", MyImpact.class, MyImpact.CODEC)` in `setup()`.

---

### Bench Configuration
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.bench`

Backs the `BlockType` JSON key `Bench` — the inline bench definition carried by bench items (e.g. `Server/Item/Items/Bench/Bench_Weapon.json`). `BlockType.getBench()` returns it. `Bench.CODEC` dispatches on the `Type` key using the `BenchType` enum; `BlockTypeModule` registers the variants:

| `Type` value | Class | Shipped example |
|--------------|-------|-----------------|
| `Crafting` | `CraftingBench` | `Bench_Weapon.json` |
| `Processing` | `ProcessingBench` | `Bench_Furnace.json` |
| `DiagramCrafting` | `DiagramCraftingBench` | `Bench_Armory.json` |
| `StructuralCrafting` | `StructuralCraftingBench` | `Bench_Builders.json` |

Base JSON keys (all bench types): `Id`, `DescriptiveLabel`, `TierLevels` (array), and the sound-event ids `LocalOpenSoundEventId`, `LocalCloseSoundEventId`, `CompletedSoundEventId`, `FailedSoundEventId`, `BenchUpgradeSoundEventId`, `BenchUpgradeCompletedSoundEventId`. Each `TierLevels` entry may set `UpgradeRequirement`, `CraftingTimeReductionModifier`, `ExtraInputSlot`, `ExtraOutputSlot`.

```json
{
  "BlockType": {
    "Bench": {
      "Type": "Crafting",
      "Id": "Weapon_Bench",
      "TierLevels": [
        {
          "CraftingTimeReductionModifier": 0.0,
          "UpgradeRequirement": {
            "Material": [
              { "ItemId": "Ingredient_Bar_Iron", "Quantity": 20 },
              { "ItemId": "Ingredient_Leather_Light", "Quantity": 30 }
            ],
            "TimeSeconds": 3
          }
        }
      ]
    }
  }
}
```
*(abridged from `Bench_Weapon.json`)*

#### Bench (base class)

```java
BenchType getType()
String getId()
String getDescriptiveLabel()
BenchTierLevel getTierLevel(int tier)
BenchUpgradeRequirement getUpgradeRequirement(int tier)
RootInteraction getRootInteraction()   // The interaction that opens this bench type
Bench toPacket()                       // protocol.Bench

// Bind the opening interaction for a bench type (engine wiring).
// @Deprecated(forRemoval=true), as it was in 0.6.8
static void registerRootInteraction(BenchType type, RootInteraction interaction)
```

#### BenchUpgradeRequirement

One tier-upgrade cost — JSON keys `Material` (item + quantity list) and `TimeSeconds`:

```java
MaterialQuantity[] getInput()   // JSON "Material"
float getTimeSeconds()
```

#### DiagramCraftingBench

`Type: "DiagramCrafting"`. Extends `CraftingBench` and adds no keys of its own — categories come from `CraftingBench`'s `Categories` array (`getCategories()` returning `BenchCategory[]`, each with `Id`, `Name`, `Icon`, `ItemCategories`).

#### StructuralCraftingBench

`Type: "StructuralCrafting"` — the Builders bench (block-set crafting). Own JSON keys: `Categories` (string array), `HeaderCategories`, `AlwaysShowInventoryHints`, `AllowBlockGroupCycling`.

```java
boolean isHeaderCategory(String category)
int getCategoryIndex(String category)
boolean shouldAllowBlockGroupCycling()
boolean shouldAlwaysShowInventoryHints()
```

---

### Farming Config Classes
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.farming`

Two classes back the `Farming` JSON documented in [Farming & Soil](items-blocks.md#farming--soil).

#### FarmingStageData

Abstract base for the entries of `Farming.Stages.<set>[]`. `FarmingStageData.CODEC` dispatches on each stage's `Type` key; the shipped farming plugin registers `"BlockType"`, `"BlockState"`, `"Prefab"`, and `"Spread"`. Base JSON keys: `Duration` (`{ "Min", "Max" }` range) and `SoundEventId`.

```java
Rangef getDuration()
String getSoundEventId()
boolean implementsShouldStop()   // Whether this stage type uses shouldStop()
boolean consumesRemainingTime()

boolean shouldStop(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
                   Ref<ChunkStore> ref2, int x, int y, int z)
boolean canApply(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
                 Ref<ChunkStore> ref2, int x, int y, int z)
void apply(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
           Ref<ChunkStore> ref2, int x, int y, int z, FarmingStageData previous)
void remove(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
            Ref<ChunkStore> ref2, int x, int y, int z)
```

A plugin adds a custom stage type by subclassing and registering against `FarmingStageData.CODEC`.

#### GrowthModifierAsset

Asset type for growth-rate modifiers — the ids listed in `Farming.ActiveGrowthModifiers`. Assets load from `Server/Farming/Modifiers/*.json` (shipped: `Fertilizer`, `Water`, `LightLevel`, `Darkness`); each declares a `Type` (`"Fertilizer"`, `"LightLevel"`, or `"Water"` — registered by the farming plugin), a `Modifier` multiplier, and type-specific keys (e.g. `LightLevel` adds `ArtificialLight` / `Sunlight` ranges).

```json
{ "Type": "Fertilizer", "Modifier": 2 }
```
*(from `Server/Farming/Modifiers/Fertilizer.json`)*

```java
static AssetStore<String, GrowthModifierAsset, ...> getAssetStore()
static DefaultAssetMap<String, GrowthModifierAsset> getAssetMap()

String getId()
double getModifier()
double getCurrentGrowthMultiplier(CommandBuffer<ChunkStore> buffer, Ref<ChunkStore> ref1,
                                  Ref<ChunkStore> ref2, int x, int y, int z, boolean flag)
```

---

### BlockBoundingBoxes
**Package:** `com.hypixel.hytale.server.core.asset.type.blockhitbox`

The asset class behind [Hitbox Definitions](blocks.md#hitbox-definitions) — one asset per file under `Server/Item/Block/Hitboxes/`, decoding the `Boxes` array. A block references one by name via `HitboxType`; `BlockType.getHitboxTypeIndex()` is the index into this asset map.

```java
static final String DEFAULT = "Full";  // Default full-cube hitbox id
static final int DEFAULT_ID = 0;
static final BlockBoundingBoxes UNIT_BOX;

static AssetStore<String, BlockBoundingBoxes, ...> getAssetStore()
static IndexedLookupTableAssetMap<String, BlockBoundingBoxes> getAssetMap()
static BlockBoundingBoxes getUnitBoxFor(String id) // Full-cube stand-in for a removed asset

String getId()
boolean protrudesUnitBox()  // Any box extends outside the 1x1x1 cell
RotatedVariantBoxes get(Rotation yaw, Rotation pitch, Rotation roll)
RotatedVariantBoxes get(int rotationIndex)
Hitbox[] toPacket()
```

`BlockBoundingBoxes.RotatedVariantBoxes` is the box set for one placement rotation:

```java
Box getBoundingBox()     // Enclosing AABB
Box[] getDetailBoxes()   // Individual boxes (multi-box hitboxes)
boolean hasDetailBoxes()
boolean containsPosition(double x, double y, double z)
```

---

### FillerBlockUtil
**Package:** `com.hypixel.hytale.server.core.util`

When a block's hitbox protrudes its own cell (`BlockBoundingBoxes.protrudesUnitBox()`), the engine occupies the overlapped neighbor cells with invisible *filler blocks* so collision and placement stay consistent (large doors, oversized furniture). `FillerBlockUtil` is the static helper for that bookkeeping — mostly engine-driven, but useful when a plugin validates or clears multi-cell blocks.

```java
static final int NO_FILLER = 0;

// Iterate / test the neighbor cells a rotated hitbox spills into
// (both have overloads taking a coverage threshold before the boxes; forEachFillerBlock also has
//  forEachFillerBlock(float threshold, int expand, boxes, consumer), which widens the cell range by
//  `expand` cells on every side, and a form taking expandX, expandY, expandZ separately)
static void forEachFillerBlock(RotatedVariantBoxes boxes, TriIntConsumer consumer)
static boolean testFillerBlocks(RotatedVariantBoxes boxes, TriIntPredicate predicate)

// Multi-cell footprints (0.6.3+; 0.7.2 added Int3OpenHashSet overloads of the last two,
// and packedMinCell / packedMaxCell, the box set's extreme cells packed like a filler offset)
// multiCellFootprint: the block type's hitbox at that rotation index, or null when the id or its
// hitbox asset is unknown, or the hitbox stays inside its own cell (protrudesUnitBox() is false)
static RotatedVariantBoxes multiCellFootprint(int blockId, int rotation)
static boolean isFootprintFree(LongOpenHashSet occupied, int x, int y, int z, RotatedVariantBoxes boxes)
static void markFootprint(LongOpenHashSet occupied, int x, int y, int z, RotatedVariantBoxes boxes)
static int packedMinCell(RotatedVariantBoxes boxes)
static int packedMaxCell(RotatedVariantBoxes boxes)

// Filler offsets are packed into one int
static int pack(int x, int y, int z)
static int unpackX(int packed)
static int unpackY(int packed)
static int unpackZ(int packed)

// Engine-side add/remove of the filler blocks around the block at world (x, y, z).
// Both gained a BlockComponentSection parameter after the BlockSection in 0.6.3.
// `ref` is the section reference; blockId / filler / rotation describe the block whose fillers these are.
static void setFillerBlocksAt(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref,
                              BlockSection section, BlockComponentSection componentSection,
                              int x, int y, int z,
                              int blockId, int filler, int rotation, ChangeReason reason)
static void removeFillerBlocksAt(ComponentAccessor<ChunkStore> accessor,
                                 BlockSection section, BlockComponentSection componentSection,
                                 int x, int y, int z,
                                 int blockId, int filler, int rotation, ChangeReason reason)
```

`FillerBlockUtil.ChangeReason` enum: `NONE`, `NORMAL`, `BY_PHYSICS`. In 0.7.2 the normal entry point is
`BlockOperations.setBlock` ([block-access.md](block-access.md#writing-with-blockoperations)), which removes
the old block's fillers and places the new block's unless `SetBlockSettings.NO_BREAK_FILLER` /
`NO_SET_FILLER` say otherwise. (`BlockTypeModule.breakOrSetFillerBlocks` was removed in 0.7.2.)

---

### World Block Access

Reading and writing blocks from Java is on its own page, [block-access.md](block-access.md). In 0.7.2
the chunk getters this section used to list (`world.getChunkIfLoaded`, `getChunkAsync`, …) and every
block method on `World` and `WorldChunk` were removed: blocks are reached through a section reference
from `world.getChunkStore()`, read from its `BlockSection` component and written with
`BlockOperations.setBlock`. The [migration table](block-access.md#migrating-from-06x) maps each removed
call to its replacement.

---

## Block Ticking

**Packages:** `com.hypixel.hytale.server.core.asset.type.blocktick` and `...blocktick.config`

The engine ticks blocks through two separate paths, both configured per block type in JSON and both extensible from a plugin:

| Path | JSON key on `BlockType` | Java accessor | Runs |
|------|--------------------------|---------------|------|
| **Scheduled ticking** | `TickProcedure` | `BlockType.getTickProcedure()` | Every tick of a ticking chunk section, for its blocks flagged as *ticking* |
| **Random ticking** | `RandomTickProcedure` | `BlockType.getRandomTickProcedure()` | For a few randomly sampled blocks per chunk section per tick |

Scheduled ticking is driven by the shipped block-tick plugin (`com.hypixel.hytale.builtin.blocktick.BlockTickPlugin`), random ticking by the random-tick plugin (`com.hypixel.hytale.builtin.randomtick.RandomTickPlugin`). Grass spreading is a random tick; both procedure kinds decode polymorphically on a `Type` key.

### IBlockTickProvider & BlockTickManager

`IBlockTickProvider` answers "what runs when this block id gets a scheduled tick":

```java
public interface IBlockTickProvider {
    static final IBlockTickProvider NONE;       // No-op provider
    TickProcedure getTickProcedure(int blockId); // null = this block does not tick
}
```

`BlockTickManager` is the static holder the chunk-tick system reads the provider from. The whole class
is `@Deprecated(forRemoval=true)` (as it already was in 0.6.8); the 0.7.2 engine still reads it, so treat
it as plumbing to understand rather than an API to build on:

```java
static void setBlockTickProvider(IBlockTickProvider provider)
static IBlockTickProvider getBlockTickProvider()
static boolean hasBlockTickProvider()
```

The shipped provider is `BlockTickPlugin` itself: its `getTickProcedure(int)` simply returns `BlockType.getAssetMap().getAsset(blockId).getTickProcedure()`, i.e. the block's own `TickProcedure` JSON. There is exactly one global provider, but replacing it with `BlockTickManager.setBlockTickProvider(...)` does **not** change which procedure runs: the section tick system (`ChunkBlockTickSystem`) calls `BlockTickPlugin.get().getTickProcedure(blockId)` directly, and only checks `BlockTickManager.hasBlockTickProvider()` to decide whether to tick at all. The provider is consulted by `BlockOperations.setBlock`, which sets a written block's ticking bit when the provider returns a procedure for its id. To run your own logic, register a `TickProcedure` type (below) rather than a provider.

### BlockTickStrategy

Every scheduled tick — and every fluid tick (see [Fluids](fluids.md)) — returns a `BlockTickStrategy` telling the chunk what to do with the block's ticking flag:

```java
public enum BlockTickStrategy {
    CONTINUE,                     // Keep ticking this block next tick
    IGNORED,                      // Nothing to do; drop it from the ticking set
    SLEEP,                        // Stop ticking until something re-wakes the block
    WAIT_FOR_ADJACENT_CHUNK_LOAD  // Park it; retried when neighboring chunks load
}
```

A slept/ignored block is re-woken by flagging it again on its section — `BlockSection.setTicking(x, y, z, true)`, then `ChunkSection.markNeedsSaving()` if it returned `true` (`isTicking(x, y, z)` reads the flag); see [block-access.md → Ticking](block-access.md#ticking). (`BlockChunk.setTicking` was removed in 0.7.2.)
`BlockOperations.updateBlockArea(chunkStore, chunkSection, blockSection, x, y, z)` wakes the 3×3×3 neighbourhood of one cell.
A write with `SetBlockSettings.PERFORM_BLOCK_UPDATE` uses the other overload, `updateBlockArea(chunkStore, chunkSection, blockSection, blockType, rotation, x, y, z)`: it wakes every cell of the new block's rotated hitbox footprint plus a one-cell margin on each side (`FillerBlockUtil.forEachFillerBlock(0.0f, 1, ...)`), which is the 3×3×3 for a one-cell block and larger for a multi-cell one, and does nothing when the block type's hitbox asset is missing.
Cells in other sections are woken only if those sections are loaded or already loading (both overloads look them up with `NO_LOAD | NO_GENERATE`). `WAIT_FOR_ADJACENT_CHUNK_LOAD` blocks are merged back into the ticking set by the block-tick plugin's `MergeWaitingBlocksSystem`.

### TickProcedure (scheduled ticks)

```java
public abstract class TickProcedure {
    public static final CodecMapCodec<TickProcedure> CODEC;  // dispatches on "Type"

    // 0.7.2: was onTick(World, WorldChunk, x, y, z, blockId)
    public abstract BlockTickStrategy onTick(CommandBuffer<ChunkStore> commandBuffer,
                                             Ref<ChunkStore> sectionRef,
                                             int x, int y, int z, int blockId);
}
```

`sectionRef` is the ticking section and `x, y, z` are world coordinates, so a procedure writes with
`BlockOperations.setBlock(commandBuffer.getExternalData(), sectionRef, x, y, z, ...)` — exactly what the
shipped `BasicChanceBlockGrowthProcedure` does.

The block-tick plugin registers two growth-style types, `"BasicChance"` (keys `NextId`, `Chance`, `ChanceMin`, `NextTicking`) and `"SplitChance"`. No shipped block asset sets `TickProcedure` in JSON in this build — plant growth ships through the farming system instead — but the codec key is live, and custom types registered here work the same way as random-tick types (below).

### RandomTickProcedure (random ticks)

```java
public interface RandomTickProcedure {
    static final CodecMapCodec<RandomTickProcedure> CODEC;   // dispatches on "Type"

    void onRandomTick(Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer,
                      BlockSection section, int x, int y, int z,
                      int blockId, BlockType blockType);
}
```

Each tick the random-tick system samples a few block positions per chunk section (defaults: 1 per stable section, 3 per recently-changed section) and invokes the sampled block's procedure if it has one. Coordinates passed to `onRandomTick` are world block coordinates.

The random-tick plugin registers three types: `"ChangeIntoBlock"` (key `TargetBlock`), `"SpreadTo"`
(keys `SpreadDirections`, `MinY`, `MaxY`, `AllowedTag`, `AllowedAboveFluids`, `RequireEmptyAboveTarget`,
`RequiredLightLevel`, `RevertBlock`), and — new in 0.6.3 — `"PlaceBlock"` (keys `Placements`, `Offset`,
`RequireEmptyTarget`; each `Placements` entry is a weighted `Blocks` list, as
`Test_PlaceBlockProcedure.json` shows). Grass is the shipped `SpreadTo` example — `Soil_Grass.json`:

```json
{
  "BlockType": {
    "RandomTickProcedure": {
      "Type": "SpreadTo",
      "AllowedTag": "Spreadable=Grass",
      "SpreadDirections": [
        { "X": -1, "Z": 0 }, { "X": 1, "Z": 0 },
        { "X": 0, "Z": -1 }, { "X": 0, "Z": 1 }
      ],
      "MaxY": 1,
      "MinY": -1,
      "RevertBlock": "Soil_Dirt"
    }
  }
}
```
*(abridged — the real file lists all eight horizontal directions)*

### Hooking custom block ticking

Registering a custom procedure type is the supported way for a plugin to tick its own blocks:

```java
public class MeltProcedure implements RandomTickProcedure {
    public static final BuilderCodec<MeltProcedure> CODEC =
        BuilderCodec.builder(MeltProcedure.class, MeltProcedure::new)
            .addField(new KeyedCodec<>("MeltInto", Codec.STRING),
                      (p, v) -> p.meltInto = v, p -> p.meltInto)
            .build();

    private String meltInto = "Empty";

    @Override
    public void onRandomTick(Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer,
                             BlockSection section, int x, int y, int z,
                             int blockId, BlockType blockType) {
        // e.g. replace this block with `meltInto` when its biome is warm
    }
}

// In your plugin's setup():
RandomTickProcedure.CODEC.register("Melt", MeltProcedure.class, MeltProcedure.CODEC);
```

Then reference it from the block's JSON:

```json
{ "BlockType": { "RandomTickProcedure": { "Type": "Melt", "MeltInto": "Water_Source" } } }
```

The same pattern applies to scheduled ticks: extend `TickProcedure`, register via `TickProcedure.CODEC.register(...)`, set the block's `TickProcedure` key, and return a [`BlockTickStrategy`](#blocktickstrategy) from `onTick` (`CONTINUE` to keep ticking, `SLEEP`/`IGNORED` when done). Registration names are global to the codec, so pick a distinctive `Type` string. The shipped `BlockTickPlugin` / `RandomTickPlugin` must be enabled (they are by default) — they own the systems that actually walk ticking blocks and call your procedure.

---

## Block Events

Handle block interactions through the event system. All block events are ECS events and should be handled using `EntityEventSystem`.

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

### Event Summary

| Class | Description | Cancellable |
|-------|-------------|-------------|
| `PlaceBlockEvent` | Block is placed | Yes |
| `BreakBlockEvent` | Block is broken | Yes |
| `DamageBlockEvent` | Block takes damage (mining progress) | Yes |
| `UseBlockEvent.Pre` | Before block is used/interacted with | Yes |
| `UseBlockEvent.Post` | After block is used/interacted with | No |

---

### PlaceBlockEvent

Fired when a block is placed.

```java
public class PlaceBlockEvent extends CancellableEcsEvent {
    ItemStack getItemInHand()
    Vector3i getTargetBlock()
    void setTargetBlock(Vector3i position)
    RotationTuple getRotation()
    void setRotation(RotationTuple rotation)
    boolean isConsumeItem()               // 0.6.3+: whether placing consumes the held stack
    void setConsumeItem(boolean)          // 0.6.3+: e.g. leave the item in hand
    boolean isCancelled()
    void setCancelled(boolean)
}
```

---

### BreakBlockEvent

Fired when a block is broken.

```java
public class BreakBlockEvent extends CancellableEcsEvent {
    ItemStack getItemInHand()
    Vector3i getTargetBlock()
    BlockType getBlockType()
    void setTargetBlock(Vector3i position)
    boolean isCancelled()
    void setCancelled(boolean)
}
```

---

### DamageBlockEvent

Fired when a block takes damage (mining progress). This fires during the mining process before the block is actually broken.

```java
public class DamageBlockEvent extends CancellableEcsEvent {
    ItemStack getItemInHand()
    Vector3i getTargetBlock()
    void setTargetBlock(Vector3i position)
    BlockType getBlockType()
    float getCurrentDamage()   // despite the name: the block's current HEALTH, 1.0 = undamaged
    float getDamage()          // damage this strike would subtract from that health
    void setDamage(float)      // scale or zero this strike without cancelling the event
    boolean isCancelled()
    void setCancelled(boolean)
}
```

#### DamageBlockEvent Usage

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.DamageBlockEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class DamageBlockEventSystem extends EntityEventSystem<EntityStore, DamageBlockEvent> {

    public DamageBlockEventSystem() {
        super(DamageBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       DamageBlockEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            // Could log mining progress or modify damage
            var blockType = event.getBlockType();
            var pos = event.getTargetBlock();
            System.out.println("Mining " + blockType + " at " + pos);
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

### UseBlockEvent

Fired when a block is used/interacted with. `UseBlockEvent` itself is abstract and carries the four
accessors; the concrete events are its `Pre` and `Post` subclasses.

```java
public abstract class UseBlockEvent extends EcsEvent {
    InteractionType getInteractionType()
    InteractionContext getContext()   // com.hypixel.hytale.server.core.entity.InteractionContext
    Vector3i getTargetBlock()
    BlockType getBlockType()
}
```

#### UseBlockEvent.Pre

Fired before the block interaction is processed. Can be cancelled — note it implements
`ICancellableEcsEvent` rather than extending `CancellableEcsEvent`.

```java
public final class UseBlockEvent.Pre extends UseBlockEvent implements ICancellableEcsEvent {
    boolean isCancelled()
    void setCancelled(boolean)
}
```

#### UseBlockEvent.Post

Fired after the block interaction is processed. Cannot be cancelled.

```java
public final class UseBlockEvent.Post extends UseBlockEvent { }
```

#### UseBlockEvent Usage

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.UseBlockEvent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class UseBlockPreSystem extends EntityEventSystem<EntityStore, UseBlockEvent.Pre> {

    public UseBlockPreSystem() {
        super(UseBlockEvent.Pre.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       UseBlockEvent.Pre event) {
        // Chat goes through the entity's PlayerRef component
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef != null) {
            // Prevent using certain block types
            // event.setCancelled(true);
            playerRef.sendMessage(Message.raw("You used a block!"));
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

## Usage Examples

### Handle Block Break Event
```java
// Using EntityEventSystem for ECS events
public class BlockBreakSystem extends EntityEventSystem<EntityStore, BreakBlockEvent> {
    public BlockBreakSystem() {
        super(BreakBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       BreakBlockEvent event) {
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef != null) {
            Vector3i pos = event.getTargetBlock();
            playerRef.sendMessage(Message.raw("You broke a block at " + pos.x + ", " + pos.y + ", " + pos.z));
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}

// Register in setup()
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new BlockBreakSystem());
}
```

### Cancel Block Placement
```java
public class BlockPlaceSystem extends EntityEventSystem<EntityStore, PlaceBlockEvent> {
    public BlockPlaceSystem() {
        super(PlaceBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PlaceBlockEvent event) {
        // Cancel placement in certain conditions
        Vector3i target = event.getTargetBlock();
        if (target.y > 100) {
            event.setCancelled(true);
            PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
            if (playerRef != null) {
                playerRef.sendMessage(Message.raw("Cannot place blocks above y=100"));
            }
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

## Block Health & Fragility

**Package:** `com.hypixel.hytale.server.core.modules.blockhealth`

A separate runtime subsystem tracks per-block *durability* — how damaged a block is between hits. It is
the state behind [`DamageBlockEvent`](#damageblockevent): each strike reads it, fires the event, and
subtracts the event's damage. It ships as the core `JavaPlugin` module `BlockHealthModule`.

> **0.7.2 moved block health from the chunk column to the section.** `BlockHealthChunk` is
> `@Deprecated(forRemoval=true)` (its `FragileBlock` class was removed), and `BlockHealthModule` now registers
> `BlockHealthSection`, a component on every chunk section, keyed by block index instead of
> `Vector3i`. `getBlockHealthChunkComponentType()` was removed; `BlockHealthSystems.MigrateBlockHealthChunk`
> moves old saves over. The section API — `getHealth`, `damage`, `makeFragile`, … — is on
> [block-access.md → BlockHealthSection](block-access.md#blockhealthsection).

How it behaves, read from `BlockHealthSystems` and `BlockHarvestUtils.performBlockDamage`:

- **Health is a fraction.** `BlockHealth.FULL_HEALTH` is `1.0`; only damaged or fragile blocks have an
  entry. `DamageBlockEvent.getCurrentDamage()` carries this current health (not accumulated damage).
- **A strike** resolves the block's section, fires `DamageBlockEvent`, calls
  `BlockHealthSection.damage(x, y, z, event.getDamage(), now)`, marks the section for saving, and
  breaks the block when the result is destroyed (`BlockHealth.isDestroyed`) or the block is fragile.
- **Regeneration** runs in `BlockHealthSystems.Tick`: 5 seconds after the last hit, health returns at
  0.1 per second. Fragility counts down in the same system.
- **Replacing a block** clears its entry (`BlockHealthModule.onBlockReplaced`, called by
  `BlockOperations.setBlock`).

### BlockHealth methods

| Member | Description |
|--------|-------------|
| `FULL_HEALTH` (static) | `1.0`, an undamaged block |
| `isDamaged(float)` / `isDestroyed(float)` (static) | Classify a health value: damaged is strictly between 0 and 1; destroyed is at or below 0 |
| `getHealth()` / `setHealth(float)` | Current durability value |
| `getLastDamageGameTime()` / `setLastDamageGameTime(Instant)` | When the block was last hit (drives regen timing) |
| `isDestroyed()` | Health has reached zero |

0.7.2 removed `NO_DAMAGE_INSTANCE` and `isFullHealth()`; compare against `FULL_HEALTH` instead.

> [!WARNING]
> This is engine infrastructure exposed publicly. Re-surveyed against 0.7.2, no first-party *content
> plugin* references it. Outside its own package it is used by two engine classes, `BlockHarvestUtils`
> (the damage path) and `BlockOperations` (`setBlock` calls `BlockHealthModule.onBlockReplaced`), and
> `Constants` lists `BlockHealthModule` among the core plugins. How a
> custom block would author its own durability is not exercised by any shipped plugin.

---

## Custom Block-Entity Components

The worked example below is an example project compiled by the example-build gate (the full `verify-docs.sh` run), and it uses none of the block API that 0.7.2 removed. The end-to-end run against a live server was last exercised on an older build and has not been repeated for 0.7.2 — treat the runtime behaviour as unconfirmed rather than guaranteed. Worked example: [`examples/item-respawner`](https://github.com/inkthorne/hytale-modding-handbook/tree/main/examples/item-respawner), a placeable pedestal that drops an item, respawns it on an interval (Quake-style), and is edited in-world through a press-F settings GUI.

A *block-entity component* is your own data attached to individual placed blocks. Unlike a [`DamageBlockEvent`](#damageblockevent) handler (which reacts to player actions), a block-entity component is **persistent per-block state** that you can tick on the server's heartbeat. The shipped `BlockSpawner`, `ItemContainerBlock`, and bed `RespawnBlock` all work this way; this section shows how to author your own.

Block-entity components live on the **`ChunkStore`** — the ECS store that backs chunks and blocks (see [Components](components.md)), distinct from the `EntityStore` that holds players, mobs, and dropped items. Living on the `ChunkStore` is what makes the state save and load with the chunk.

### 1. The component

Implement `Component<ChunkStore>`. Give it a `BuilderCodec` (see [Codecs](codecs.md)) that lists the persisted fields, a no-arg constructor, and a `clone()` (the engine clones the JSON-defined template to instantiate each placed block).

```java
public class ItemRespawner implements Component<ChunkStore> {

    public static final BuilderCodec<ItemRespawner> CODEC =
        BuilderCodec.builder(ItemRespawner.class, ItemRespawner::new)
            .addField(new KeyedCodec<>("Item", Codec.STRING),
                      (s, v) -> s.item = v, s -> s.item)
            .addField(new KeyedCodec<>("IntervalSeconds", Codec.INTEGER),
                      (s, v) -> s.intervalSeconds = v, s -> s.intervalSeconds)
            .build();

    private String item = "Weapon_Crossbow_Iron";
    private int intervalSeconds = 20;

    public ItemRespawner() {}

    // getters/setters ...

    @Override
    public ItemRespawner clone() {
        ItemRespawner copy = new ItemRespawner();
        copy.item = this.item;
        copy.intervalSeconds = this.intervalSeconds;
        return copy;
    }
}
```

Each `addField` key (`"Item"`, `"IntervalSeconds"`) is the JSON key authors set in the block definition. Fields absent from the data keep their defaults.

### 2. Wire it to a block

Define a normal block-item, and nest your component under `BlockType.BlockEntity.Components` keyed by the **name you register it under** (step 3). The object's keys map to the codec fields:

```json
{
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Model",
    "Opacity": "Transparent",
    "CustomModel": "Blocks/Structures/Pillars/Pillar_Base.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Blocks/Structures/Pillars/Pillar_Base_Textures/Marble_Brick.png", "Weight": 1 }
    ],
    "Interactions": {
      "Use": {
        "Interactions": [
          {
            "Type": "Condition",
            "RequiredGameMode": "Creative",
            "Next": { "Type": "OpenCustomUI", "Page": { "Id": "ItemRespawner" } }
          }
        ]
      }
    },
    "BlockEntity": {
      "Components": {
        "ItemRespawner": { "Item": "Weapon_Crossbow_Iron", "IntervalSeconds": 20 }
      }
    }
  }
}
```

The carrier block is just a normal block — here a visible, solid pedestal reusing a shipped marble pillar-base model so the spawned item rests on top and the block is targetable (needed for the press-F GUI in step 7). It could equally be a plain cube, or even invisible and walk-through (`Material: "Empty"` + `DrawType: "Empty"`, as shipped crops and the `Barrier` block are) if you don't need to interact with it. The `Use` → `OpenCustomUI` interaction is only needed for the editing GUI; drop it for a fixed-config spawner.

Two deliberate choices here:
- **No `Gathering`.** Omitting the gathering config makes the block unbreakable by mining in adventure/survival (the same way `Rock_Bedrock` and `Barrier` are), while creative's instant-break can still remove it. Add a `Gathering.Breaking` block if you want it mineable.
- **`Condition` → `Creative`.** Wrapping `OpenCustomUI` in a `Condition` with `RequiredGameMode: "Creative"` means the GUI only opens for creative-mode players, so adventure players can't reconfigure the block (see the prompt caveat in step 7).

### 3. Register the component and a system

In your plugin's `setup()`, register against **`getChunkStoreRegistry()`** (not the entity-store registry). `registerComponent` returns the `ComponentType` handle; pass it to your system:

```java
ComponentType<ChunkStore, ItemRespawner> type = getChunkStoreRegistry()
    .registerComponent(ItemRespawner.class, "ItemRespawner", ItemRespawner.CODEC);
getChunkStoreRegistry().registerSystem(new ItemRespawnerSystem(type));
```

The string `"ItemRespawner"` is exactly the JSON key from step 2.

### 4. Tick over placed blocks

`EntityTickingSystem` is generic over the store type, so `EntityTickingSystem<ChunkStore>` ticks block-entities the same way `EntityTickingSystem<EntityStore>` ticks entities — this is the base the engine's own fluid ticker uses. `getQuery()` restricts the tick to block-entities carrying both your component and the engine's `BlockModule.BlockStateInfo` (which every placed block-entity has, and which carries the block's location):

```java
public class ItemRespawnerSystem extends EntityTickingSystem<ChunkStore> {
    private final ComponentType<ChunkStore, ItemRespawner> type;
    private final Query<ChunkStore> query;

    public ItemRespawnerSystem(ComponentType<ChunkStore, ItemRespawner> type) {
        this.type = type;
        this.query = Query.and(type, BlockModule.BlockStateInfo.getComponentType());
    }

    @Override public Query<ChunkStore> getQuery() { return query; }

    // We mutate the EntityStore from here (step 5), so keep the tick single-threaded.
    @Override public boolean isParallel(int chunkCount, int entityCount) { return false; }

    @Override
    public void tick(float deltaTime, int index, ArchetypeChunk<ChunkStore> chunk,
                     Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer) {
        ItemRespawner spawner = chunk.getComponent(index, type);
        var info = chunk.getComponent(index, BlockModule.BlockStateInfo.getComponentType());
        if (spawner == null || info == null) return;
        // ... resolve position (step 4b), then spawn/respawn (step 5) ...
    }
}
```

#### 4b. Resolving the block's world position

`BlockStateInfo` carries a reference to the owning **chunk section** (`getSectionRef()`, a 32×32×32 `ChunkSection`) plus the block's packed section-local index (`getIndex()`). As of 0.6.3 it resolves the world position for you:

```java
Vector3i blockPos = new Vector3i();                  // org.joml
if (!info.fillWorldPos(store, blockPos)) return;     // false: section ref invalid / section unloaded
int x = blockPos.x, y = blockPos.y, z = blockPos.z;

World world = store.getExternalData().getWorld();   // ChunkStore -> World
```

`fillWorldPos(accessor, out)` looks up the `ChunkSection` component through the section ref and does `worldCoordFromLocalCoord(section.getX/Y/Z(), ChunkUtil.xFromIndex/yFromIndex/zFromIndex(index))`; the no-accessor overload `fillWorldPos(out)` uses the ref's own store. (Before 0.6.3 the component exposed `getChunkRef()` to the column `WorldChunk` and you unpacked a column index with `ChunkUtil.{x,y,z}FromBlockInColumn` — both are gone.)

### 5. Spawning an item-entity from the block

The item you drop is a normal entity in the **`EntityStore`**, reached via the `World`. Build a dropped-item `Holder` with `ItemComponent.generateItemDrop(...)` and insert it with `Store.addEntity(...)`:

```java
EntityStore entityStore = world.getEntityStore();
Store<EntityStore> entities = entityStore.getStore();   // also a ComponentAccessor

ItemStack stack = new ItemStack(spawner.getItem(), 1);
Vector3d pos = new Vector3d(x + 0.5, y + 1.1, z + 0.5);   // rest on top of the pedestal
Holder<EntityStore> drop = ItemComponent.generateItemDrop(
        entities, stack, pos, new Rotation3f(), 0f, 0f, 0f);   // Rotation3f + three velocity floats
if (drop == null) return;   // null on an invalid/empty stack
Ref<EntityStore> ref = entities.addEntity(drop, AddReason.SPAWN);
```

`generateItemDrop` attaches everything a pickup needs (transform, velocity, physics, a UUID, and a despawn timer) and returns `null` for an invalid item id, so a bad `Item` value fails safe. The drop carries the engine's standard despawn timer — an untouched pickup eventually despawns, after which your "is it still here?" check (below) treats it as gone.

> Because this mutates the `EntityStore` while iterating the `ChunkStore`, override `isParallel(...)` to return `false` (shown in step 4) so the tick runs single-threaded. The `CommandBuffer<ChunkStore>` the tick receives cannot insert `EntityStore` entities — it's typed to the chunk store — which is why the spawn goes through `world.getEntityStore().getStore()` directly.

### 6. "Only if not already present" + surviving reloads

To avoid spawning a second item while one is still lying there, remember what you spawned and check it each tick. Within one session, hold the `Ref` that `addEntity` returned: `Ref.isValid()` is `true` while the item exists and flips to `false` the instant it's picked up or despawns.

A `Ref` is a transient, in-memory handle — it does **not** survive a reload, but the dropped item (saved with the world) does. To keep the two in sync, also persist the spawned item's `UUID` (add it to the codec with `Codec.UUID_BINARY`) and re-acquire the `Ref` on load via `EntityStore.getRefFromUUID(uuid)`:

```java
// re-acquire after a reload, when the transient Ref is gone but the UUID persisted
Ref<EntityStore> ref = spawner.getSpawnedRef();
if ((ref == null || !ref.isValid()) && spawner.getSpawnedUuid() != null) {
    ref = entityStore.getRefFromUUID(spawner.getSpawnedUuid());
    spawner.setSpawnedRef(ref);
}
if (ref != null && ref.isValid()) {
    // still present — capture the UUID once the engine assigns it (see gotcha), then wait
    return;
}
// gone — count up deltaTime; spawn again once IntervalSeconds elapses
```

The engine provides a ready-made wrapper for exactly this — `com.hypixel.hytale.server.core.entity.reference.PersistentRef` (a UUID + cached `Ref`, with its own `CODEC`, that re-resolves through `getRefFromUUID`). Its `getEntity(accessor)` returns the live `Ref` or `null`. The engine's own mob and chicken-coop spawner blocks (`SpawnMarkerBlock`, `CoopBlock`) persist a `PersistentRef` this way. The example tracks the `Ref` and `UUID` by hand only to make the moving parts explicit.

### 7. Editing block-entity state in-world (press-F GUI)

To let players reconfigure a placed block (its `Item`, `IntervalSeconds`, …) without commands, open a custom UI page bound to that specific block-entity. This is how the shipped `Prefab_Spawner_Block` is edited, and it's three pieces:

**A. A `Use` interaction in the block JSON** (step 2) opens a page by id. Wrap it in a `Condition` so only creative-mode players can edit:

```json
"Interactions": {
  "Use": {
    "Interactions": [
      {
        "Type": "Condition",
        "RequiredGameMode": "Creative",
        "Next": { "Type": "OpenCustomUI", "Page": { "Id": "ItemRespawner" } }
      }
    ]
  }
}
```

> [!NOTE]
> **The interact prompt ("press F") shows for _any_ block with an interaction, in every game mode** — it's emitted by the engine's interaction tracker based solely on the block having interactions, and ignores both game mode and the `Condition` above. So the `Condition` stops adventure players from *opening* the GUI, but they still *see* the prompt. To suppress the prompt entirely (no interaction on the block at all), trigger the GUI from a command instead — open the same page with `player.getPageManager().openCustomPage(...)` from an `AbstractWorldCommand` that targets the looked-at block.

**B. A page extending `InteractiveCustomUIPage<T>`**, where `T` is a small codec-backed data class for the submitted form. `build()` loads the `.ui` layout, seeds each field from the component, and binds the Save button to send the field values back; the base decodes them into `T` and calls `handleDataEvent()`, where you write to the component and persist with `BlockStateInfo.markNeedsSaving()`:

```java
public class ItemRespawnerSettingsPage extends InteractiveCustomUIPage<ItemRespawnerSettingsData> {
    private final BlockModule.BlockStateInfo info;
    private final ItemRespawner state;

    public ItemRespawnerSettingsPage(PlayerRef player, BlockModule.BlockStateInfo info,
                                     ItemRespawner state, CustomPageLifetime lifetime) {
        super(player, lifetime, ItemRespawnerSettingsData.CODEC);   // base decodes the form via this codec
        this.info = info;
        this.state = state;
    }

    @Override
    public void build(Ref<EntityStore> player, UICommandBuilder cmd, UIEventBuilder evt, Store<EntityStore> store) {
        cmd.append("Pages/ItemRespawnerSettingsPage.ui");      // path relative to Common/UI/Custom/
        cmd.set("#Item.Value", state.getItem());              // seed fields from current state
        cmd.set("#IntervalSeconds.Value", (double) state.getIntervalSeconds());
        // on Save, send each named element's value back under the codec's @-keys
        EventData data = new EventData()
                .append("@Item", "#Item.Value")
                .append("@IntervalSeconds", "#IntervalSeconds.Value");
        evt.addEventBinding(CustomUIEventBindingType.Activating, "#SaveButton", data);
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> player, Store<EntityStore> store, ItemRespawnerSettingsData data) {
        state.setItem(data.getItem());
        state.setIntervalSeconds((int) Math.round(data.getIntervalSeconds()));
        info.markNeedsSaving();   // persist the edited block-entity with its chunk
        close();
    }
}
```

The data class is a plain object whose `BuilderCodec` keys are the `@`-names bound in `build()` (`@Item`, `@IntervalSeconds`); the `.ui` file provides the named input elements (`#Item`, `#IntervalSeconds`, `#SaveButton`).

**C. Bind the page id to the block** in `setup()`. `registerBlockEntityCustomPage` hands your supplier the targeted block-entity's `Ref`; read its components (via `ref.getStore()`) and construct the page:

```java
OpenCustomUIInteraction.registerBlockEntityCustomPage(
    this, ItemRespawnerSettingsPage.class, "ItemRespawner",   // id matches OpenCustomUI Page.Id
    (player, blockRef) -> {
        Store<ChunkStore> s = blockRef.getStore();
        var info = s.getComponent(blockRef, BlockModule.BlockStateInfo.getComponentType());
        ItemRespawner state = s.getComponent(blockRef, type);   // the ComponentType from step 3
        return (info == null || state == null) ? null
            : new ItemRespawnerSettingsPage(player, info, state, CustomPageLifetime.CanDismissOrCloseThroughInteraction);
    });
```

Because the supplier reads the components off the targeted block's `Ref`, the page is always bound to the exact block the player pressed F on — edits land on that block's state and persist with it.

### Key classes for this recipe

| Class | Package | Role |
|-------|---------|------|
| `Component<ChunkStore>` | `component` | Interface your block-entity state implements |
| `ComponentRegistryProxy` | `component` | `getChunkStoreRegistry()`; `registerComponent` / `registerSystem` |
| `BlockModule.BlockStateInfo` | `server.core.modules.block` | Per-block-entity component: `getSectionRef()` + `getIndex()`, `fillWorldPos(...)` resolves the world position |
| `ChunkUtil` | `math.util` | `xFromIndex` / `yFromIndex` / `zFromIndex` (section-local index → 0–31) / `worldCoordFromLocalCoord` |
| `EntityTickingSystem<ChunkStore>` | `component.system.tick` | Per-tick system over block-entities |
| `ItemComponent` | `server.core.modules.entity.item` | `generateItemDrop(...)` builds a dropped-item `Holder` |
| `PersistentRef` | `server.core.entity.reference` | Save-surviving reference to a spawned entity |
| `InteractiveCustomUIPage<T>` | `server.core.entity.entities.player.pages` | Form page; decodes the submission into `T` and calls `handleDataEvent` (step 7) |
| `OpenCustomUIInteraction` | `server.core.modules.interaction.interaction.config.server` | `registerBlockEntityCustomPage(...)` binds a page id to a block-entity (step 7) |

### Gotchas

- **Register on the chunk store, not the entity store.** Block-entity components and their systems go through `getChunkStoreRegistry()`. Registering on `getEntityStoreRegistry()` means your `tick()` never sees placed blocks.
- **The JSON key is the registration name.** `BlockEntity.Components.<Key>` must match the string passed to `registerComponent(class, "<Key>", codec)` exactly, or the component silently never attaches.
- **A fresh drop's UUID is null for a tick.** `generateItemDrop` ensures a `UUIDComponent`, but the actual UUID is assigned slightly later — reading it immediately after `addEntity` yields `null`. Capture it lazily on a later tick (the live `Ref` covers the gap), or use `PersistentRef`.
- **`world.getEntity(uuid)` won't find a dropped item.** That method returns high-level `Entity` wrappers (players/NPCs); a bare item holder isn't one. Use `EntityStore.getRefFromUUID(uuid)` (or a `PersistentRef`) for the existence check instead.
- **Keep the tick single-threaded if it spawns entities.** `EntityTickingSystem` may run in parallel by default; override `isParallel(...)` to `false` when the body mutates another store.
- **`Opacity` has no `"Opaque"` value.** The valid `Opacity` values are `Solid`, `Transparent`, `Semitransparent`, and `Cutout`. A `Model`-draw block uses `"Transparent"`; an invalid value fails JSON decode and the whole mod refuses to load. (Likewise, asset *ids* like `BlockParticleSetId` / `ItemSoundSetId` must name a real shipped asset — copy them from a real block of the same material rather than guessing.)
- **A press-F GUI needs a targetable block.** An invisible, non-collidable carrier (`Material/DrawType: "Empty"`) can't be aimed at, so `OpenCustomUI` never fires. Use a visible, solid block (as in step 2) when you want the editing GUI.
- **The interact prompt can't be game-mode-gated from block config.** Any block with an interaction shows the "press F" prompt in every mode; neither game mode nor `Condition` affects it (they gate the *action*, not the prompt). For a prompt-free block, drop the interaction and open the GUI from a command (step 7 note).
- **Omit `Gathering` for an unbreakable block.** A block with no `Gathering.Breaking` can't be mined in adventure/survival (like `Rock_Bedrock`), but creative instant-break still removes it.

---

## Notes

Moved here with their subject when `blocks.md` was split — every one is about the
Java side rather than the JSON.

- Block reads and writes go through a chunk-section reference from `world.getChunkStore()` — see [block-access.md](block-access.md)
- A synchronous section lookup returns `null` when the section is not loaded; check before reading
- Use the async section lookup (continued on the world executor) when the area may not be loaded
- Block events are ECS events; use `EntityEventSystem` to handle them
- To place blocks in geometric shapes (spheres, cubes, cones, …), use the coordinate iterators in [Block Shape Iteration](math.md#block-shape-iteration)

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the block system (verified against `HytaleServer.jar`).

- **`itemId cannot be BlockTypeKey.EMPTY!`** → an operation received the empty/air block key where a real block was required. Fix: pass a concrete block type key, not `EMPTY_KEY` (see [Java API Reference](#java-api-reference)).

The JSON-side errors — `One and only one of BlockTag or ItemId must be set!`,
`Block entry cannot be empty`, `Cannot select from empty blocks list` and the
block-type-list load skip — stay in [blocks.md](blocks.md#gotchas--errors).

---

## Related Documentation

- [Block Definitions](blocks.md) - The JSON that configures every block
- [Connected Blocks](blocks-connected.md) - Connected and patterned rule sets
- [Components](components.md) - ECS components including BlockEntity
- [Events](events.md) - Event system overview
- [Block Access](block-access.md) - Reading and writing blocks through chunk sections
- [World](world.md) - The `World` object and its `ChunkStore`
- [Math](math.md) - `Vector3i`, `Vector3ic` and the block-position types

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
