---
title: "Collision API"
description: "Query Hytale collisions in Java — CollisionModule detection and position validation, CollisionResult data, block and character collision types, filters, and configs."
seo:
  type: TechArticle
---

# Collision API

**Doc type:** Java API · **Verified against 0.6.3**

This page covers block and character collision detection: the module, query results, the various collision-data types, configuration, and evaluators.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.collision` and provides:
- `CollisionModule` for collision detection, queries, and position validation
- `CollisionResult`, the container managing block/character collisions, slides, and triggers
- Collision-data types: `BlockCollisionData`, `BoxCollisionData`, `CharacterCollisionData`, `BasicCollisionData`
- `CollisionConfig` / `CollisionModuleConfig` for query and module configuration
- Material constants (`CollisionMaterial`) and filtering (`CollisionFilter`)
- Evaluators (`IBlockCollisionEvaluator`, `BoxBlockIntersectionEvaluator`) for intersection tests
- `CollisionResultComponent` for per-entity collision tracking

## Architecture
```
CollisionModule  (findCollisions, findIntersections, validatePosition)
├── CollisionResult  (query results container)
│   ├── Block collisions  → BlockCollisionData
│   ├── Character collisions → CharacterCollisionData
│   ├── Slides / Triggers / Damage blocks
│   └── CollisionDataArray<T>  (internal element storage)
├── Collision data types
│   └── BasicCollisionData → BoxCollisionData → BlockCollisionData
│       (CharacterCollisionData also extends BasicCollisionData)
├── Configuration
│   ├── CollisionConfig        (per-query)
│   ├── CollisionModuleConfig  (module-wide)
│   └── CollisionMaterial       (material constants)
├── Filtering / Evaluation
│   ├── CollisionFilter<D, T>
│   ├── IBlockCollisionEvaluator
│   └── BoxBlockIntersectionEvaluator
└── CollisionResultComponent  (per-entity collision tracking)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `CollisionModule` | `modules.collision` | Main module for collision detection and queries |
| `CollisionResult` | `modules.collision` | Container for collision query results |
| `BlockCollisionData` | `modules.collision` | Information about a block collision |
| `BoxCollisionData` | `modules.collision` | Base class for box collision info |
| `CharacterCollisionData` | `modules.collision` | Information about a character/entity collision |
| `BasicCollisionData` | `modules.collision` | Base collision data (point + start) |
| `CollisionConfig` | `modules.collision` | Per-query collision configuration |
| `CollisionFilter` | `modules.collision` | Generic filter interface for collision queries |
| `CollisionMaterial` | `modules.collision` | Constants for collision material types |
| `IBlockCollisionEvaluator` | `modules.collision` | Interface for evaluating block collisions |
| `BoxBlockIntersectionEvaluator` | `modules.collision` | Evaluates box-vs-block intersection |
| `CollisionModuleConfig` | `modules.collision` | Module-wide collision configuration |
| `CollisionDataArray<T>` | `modules.collision` | Generic container for collision data elements |
| `CollisionResultComponent` | `modules.entity.component` | Entity component wrapping a CollisionResult |
| `WorldUtil` | `modules.collision` | Static block-material and fluid queries at world positions |
| `SimplePhysicsProvider` | `modules.physics` | Simple physics integrator for block entities and legacy projectiles; consumes block collisions |

## Class Hierarchy
```
CollisionModule (main collision system)
  extends JavaPlugin

CollisionResult (query results container)
  implements BoxBlockIterator.BoxIterationConsumer

BasicCollisionData (base collision data)
  └── BoxCollisionData
        └── BlockCollisionData
  └── CharacterCollisionData

BlockContactData
  └── BoxBlockIntersectionEvaluator
        implements IBlockCollisionEvaluator

IBlockCollisionEvaluator (interface)
CollisionConfig (collision configuration)
CollisionFilter<D, T> (filtering interface)
CollisionMaterial (material constants)
CollisionModuleConfig (module configuration)
CollisionDataArray<T> (generic data container)
WorldUtil (static material/fluid position queries)

SimplePhysicsProvider (modules.physics)
  implements IBlockCollisionConsumer
```

## CollisionModule
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Main module for collision detection and queries.

### Getting the Module
```java
CollisionModule module = CollisionModule.get();
```

### Validation Constants
```java
static final int VALIDATE_INVALID    // Position is invalid
static final int VALIDATE_OK         // Position is valid
static final int VALIDATE_ON_GROUND  // Entity is on ground
static final int VALIDATE_TOUCH_CEIL // Entity is touching ceiling
```

### Static Collision Methods
```java
// Find all collisions along a movement path
static boolean findCollisions(
    Box hitbox,
    Vector3d startPos,
    Vector3d endPos,
    CollisionResult result,
    ComponentAccessor<EntityStore> accessor
)

// Find collisions with extra flag
static boolean findCollisions(
    Box hitbox,
    Vector3d startPos,
    Vector3d endPos,
    boolean includeSlides,
    CollisionResult result,
    ComponentAccessor<EntityStore> accessor
)

// Find block collisions iteratively
static void findBlockCollisionsIterative(
    World world,
    Box hitbox,
    Vector3d startPos,
    Vector3d endPos,
    boolean flag,
    CollisionResult result
)

// Find character (entity) collisions
static void findCharacterCollisions(
    Box hitbox,
    Vector3d startPos,
    Vector3d endPos,
    CollisionResult result,
    ComponentAccessor<EntityStore> accessor
)

// Find block collisions for short distances
static void findBlockCollisionsShortDistance(
    World world,
    Box hitbox,
    Vector3d startPos,
    Vector3d endPos,
    CollisionResult result
)

// Check if movement is below threshold
static boolean isBelowMovementThreshold(Vector3d movement)
```

### Instance Methods
```java
// Get module configuration
CollisionModuleConfig getConfig()
```

> **See also:** [World API](world-chunks.md#worldchunk)

```java
// Find intersections with blocks
void findIntersections(
    World world,
    Box hitbox,
    Vector3d position,
    CollisionResult result,
    boolean checkTriggers,
    boolean checkDamage
)

// Validate a position (position is read-only: any Vector3dc, e.g. a Vector3d)
int validatePosition(
    World world,
    Box hitbox,
    Vector3dc position,
    CollisionResult result
)

// Validate with custom filter
<T> int validatePosition(
    World world,
    Box hitbox,
    Vector3dc position,
    int flags,
    T filterData,
    CollisionFilter<BoxBlockIntersectionEvaluator, T> filter,
    CollisionResult result
)
```

---

## CollisionResult
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Container for collision query results. Manages block collisions, character collisions, slides, and triggers.

### Public Fields
```java
List<Ref<EntityStore>> collisionEntities  // Entity refs involved in the collision (never Entity objects)
double slideStart                         // Start of slide collision
double slideEnd                           // End of slide collision
boolean isSliding                         // Whether entity is sliding
int validate                              // Validation result
Predicate<CollisionConfig> isNonWalkable  // Current non-walkable predicate (see setNonWalkablePredicate)

static final Comparator<BlockCollisionData> BLOCK_COLLISION_DATA_COMPARATOR  // Sort order used by process()
```

### Constructor
```java
CollisionResult()
CollisionResult(boolean enableCharacterCollisions, boolean enableTriggerBlocks)
```

### Block Collision Methods
```java
int getBlockCollisionCount()
BlockCollisionData getBlockCollision(int index)
BlockCollisionData getFirstBlockCollision()
BlockCollisionData forgetFirstBlockCollision()  // Get and remove first collision
BlockCollisionData newCollision()               // Allocate new collision data
void addCollision(IBlockCollisionEvaluator evaluator, int flags)
```

### Character Collision Methods
```java
int getCharacterCollisionCount()
CharacterCollisionData getCharacterCollision(int index)
CharacterCollisionData getFirstCharacterCollision()
CharacterCollisionData forgetFirstCharacterCollision()
CharacterCollisionData allocCharacterCollision()
```

### Slide Methods
```java
BlockCollisionData newSlide()
void addSlide(IBlockCollisionEvaluator evaluator, int flags)
void disableSlides()
void enableSlides()
```

### Trigger Block Methods
```java
CollisionDataArray<BlockCollisionData> getTriggerBlocks()
BlockCollisionData newTrigger()
void addTrigger(IBlockCollisionEvaluator evaluator, int flags)
void pruneTriggerBlocks(double threshold)
int defaultTriggerBlocksProcessing(
    InteractionManager manager,
    Entity entity,
    Ref<EntityStore> ref,
    boolean flag,
    ComponentAccessor<EntityStore> accessor
)
void enableTriggerBlocks()
void disableTriggerBlocks()
boolean isCheckingTriggerBlocks()
```

### Pass-Through Blocks
Blocks the sweep passed *through* (non-colliding by material or filter) can be recorded separately:
```java
boolean isRecordingPassThrough()
void setRecordPassThrough(boolean record)
int getPassThroughCount()
BlockCollisionData getPassThrough(int index)
BlockCollisionData newPassThrough()
void addPassThrough(IBlockCollisionEvaluator evaluator, int flags)
```

### Damage Block Methods
```java
void enableDamageBlocks()
void disableDamageBlocks()
boolean isCheckingDamageBlocks()
boolean setDamageBlocking(boolean blocking)
boolean isDamageBlocking()
```

### Material-Based Collision
```java
void setCollisionByMaterial(int material)
void setCollisionByMaterial(int includeMask, int excludeMask)
int getCollisionByMaterial()
void setDefaultCollisionBehaviour()
void setDefaultBlockCollisionPredicate()
void setNonWalkablePredicate(Predicate<CollisionConfig> predicate)
void setDefaultNonWalkablePredicate()
void setWalkableByMaterial(int material)
void setDefaultWalkableBehaviour()
void setDefaultPlayerSettings()

// Extra per-block filter applied on top of the material mask (returns the previous filter)
Predicate<CollisionConfig> getBlockCollisionFilter()
Predicate<CollisionConfig> setBlockCollisionFilter(Predicate<CollisionConfig> filter)

// The per-query CollisionConfig this result drives
CollisionConfig getConfig()
```

### Character Collision Control
```java
void disableCharacterCollisions()
void enableCharacterCollsions()
boolean isCheckingForCharacterCollisions()
```

### Overlap Detection
```java
boolean isComputeOverlaps()
void setComputeOverlaps(boolean compute)
```

> **See also:** [Projectiles API](projectiles.md#standardphysicsprovider)

### Lifecycle
```java
void reset()                    // Reset for reuse
void process()                  // Process accumulated results
void acquireCollisionModule()   // Acquire module reference
```

### Debug Logging
Attach a logger to have the sweep log per-block decisions for one entity; `shouldLog()` is simply "a logger is set". The `debugEntityId` overloads are new as of 0.6.3.
```java
HytaleLogger getLogger()
boolean shouldLog()
void setLogger(HytaleLogger logger)
void setLogger(HytaleLogger logger, int debugEntityId)   // 0.6.3+
void setDebugEntityId(int debugEntityId)                 // 0.6.3+
int getDebugEntityId()                                   // 0.6.3+
```

---

## BlockCollisionData
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Information about a block collision.

**Extends:** `BoxCollisionData`

### Public Fields
```java
int x, y, z                     // Block coordinates
int blockId                     // Block type ID
int rotation                    // Block rotation
BlockType blockType             // Block type asset
BlockMaterial blockMaterial     // Block material
int detailBoxIndex              // Index of detail collision box
boolean willDamage              // Whether block causes damage
int fluidId                     // Fluid ID if present
Fluid fluid                     // Fluid asset if present
boolean touching                // Whether touching the block
boolean overlapping             // Whether overlapping the block
boolean filteredByCollisionFilter  // Rejected by the CollisionResult block-collision filter
```

### Methods
```java
void setBlockData(CollisionConfig config)
void setDetailBoxIndex(int index)
void setTouchingOverlapping(boolean touching, boolean overlapping)
void clear()
```

---

## BoxCollisionData
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Base class for box collision information.

**Extends:** `BasicCollisionData`

### Public Fields
```java
double collisionEnd             // End point of collision
Vector3d collisionNormal        // Normal vector at collision point
```

### Methods
```java
void setEnd(double end, Vector3d normal)
```

---

## CharacterCollisionData
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Information about a character (entity) collision.

**Extends:** `BasicCollisionData`

### Public Fields
```java
final Vector3d sourcePosition     // Moving entity's position at the collision
final Vector3d targetPosition     // Collided entity's position
Ref<EntityStore> entityReference  // Reference to collided entity
boolean isPlayer                  // Whether the entity is a player
```

### Methods
```java
void assign(
    Vector3dc sourcePosition,
    Vector3dc targetPosition,
    double collisionStart,
    Ref<EntityStore> entityRef,
    boolean isPlayer
)
```

---

## CollisionConfig
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Configuration for collision queries.

### Material Constants
```java
static final int MATERIAL_EMPTY     // Empty/air blocks
static final int MATERIAL_FLUID     // Fluid blocks
static final int MATERIAL_SOLID     // Solid blocks
static final int MATERIAL_SUBMERGED // Inside fluid
static final int MATERIAL_DAMAGE    // Damage-causing blocks
static final int MATERIAL_SET_NONE  // No materials
static final int MATERIAL_SET_ANY   // All materials
static final int MATERIAL_INVALID   // -1, sentinel for "no material resolved"
```

### Public Fields
```java
int blockId
BlockType blockType
BlockMaterial blockMaterial
int rotation
int blockX, blockY, blockZ
Fluid fluid
int fluidId
byte fluidLevel
int blockMaterialMask
boolean blockCanCollide
boolean blockCanTrigger
boolean blockCanTriggerPartial
boolean checkTriggerBlocks
boolean checkDamageBlocks
boolean blockFilteredOut                              // Set when extraBlockCollisionFilter rejected the block
Predicate<CollisionConfig> canCollide
Predicate<CollisionConfig> extraBlockCollisionFilter  // Extra filter (CollisionResult.setBlockCollisionFilter)
boolean dumpInvalidBlocks
boolean dumpNonOverlappingBlocks                      // 0.6.3+: debug-log blocks that were tested but not overlapping (from CollisionModuleConfig)
Object extraData1, extraData2
```

### Methods
```java
// Bounding box
int getDetailCount()
Box getBoundingBox()
Box getBoundingBox(int detailIndex)
int getBoundingBoxOffsetX()
int getBoundingBoxOffsetY()
int getBoundingBoxOffsetZ()

// Material configuration
void setCollisionByMaterial(int material)
int getCollisionByMaterial()
boolean isCollidingWithDamageBlocks()
boolean setCollideWithDamageBlocks(boolean collide)

// Collision predicates
Predicate<CollisionConfig> getBlockCollisionPredicate()
void setDefaultCollisionBehaviour()
void setDefaultBlockCollisionPredicate()

// Trigger and damage blocks
boolean isCheckTriggerBlocks()
void setCheckTriggerBlocks(boolean check)
boolean isCheckDamageBlocks()
void setCheckDamageBlocks(boolean check)

// World context
void setWorld(World world)
boolean canCollide(int x, int y, int z)
void clear()
```

---

## CollisionFilter
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Generic filter interface for collision queries.

### Method
```java
boolean test(T filterData, int flags, D evaluator, CollisionConfig config)
```

---

## CollisionMaterial
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Constants for collision material types.

### Constants
Bit flags (same values as the `MATERIAL_*` constants on `CollisionConfig`):
```java
static final int MATERIAL_EMPTY      = 1   // Air/empty
static final int MATERIAL_FLUID      = 2   // Fluid blocks
static final int MATERIAL_SOLID      = 4   // Solid blocks
static final int MATERIAL_SUBMERGED  = 8   // Inside fluid
static final int MATERIAL_DAMAGE     = 16  // Damage blocks
static final int MATERIAL_SET_NONE   = 0   // Match no materials
static final int MATERIAL_SET_ANY    = 15  // Match any material (EMPTY|FLUID|SOLID|SUBMERGED — not DAMAGE)
static final int MATERIAL_INVALID    = -1  // Sentinel
```

---

## BasicCollisionData
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Base class for collision data, storing the collision point and start time/position.

### Public Fields
```java
public final Vector3d collisionPoint  // Point where collision occurred
public double collisionStart          // Start time/position of collision
```

### Methods
```java
// Set collision start data
void setStart(Vector3d point, double start)
```

### Static Fields
```java
// Comparator for sorting by collision start
static Comparator<BasicCollisionData> COLLISION_START_COMPARATOR
```

---

## IBlockCollisionEvaluator
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Interface for evaluating block collisions.

### Methods
```java
// Get the collision start time/position
double getCollisionStart()

// Set collision data from evaluation
void setCollisionData(BlockCollisionData data, CollisionConfig config, int flags)
```

---

## BoxBlockIntersectionEvaluator
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Evaluates intersection between a box and blocks. Used for position validation and overlap detection.

**Extends:** `BlockContactData`
**Implements:** `IBlockCollisionEvaluator`

### Box Configuration
```java
// These return the evaluator (builder pattern), not void
BoxBlockIntersectionEvaluator setBox(Box box)
BoxBlockIntersectionEvaluator setBox(Box box, Vector3dc position)
BoxBlockIntersectionEvaluator setPosition(Vector3dc position)
BoxBlockIntersectionEvaluator offsetPosition(Vector3d offset)
BoxBlockIntersectionEvaluator expandBox(double amount)
BoxBlockIntersectionEvaluator setStartEnd(double start, double end)

// "Up" axis used for on-ground / ceiling tests (default +Y)
Vector3dc getWorldUp()
void setWorldUp(Vector3dc up)
```

### Intersection Tests
```java
// Basic intersection (returns a result code, not a boolean)
int intersectBox(Box box, double x, double y, double z)

// Intersection with touch detection
int intersectBoxComputeTouch(Box box, double x, double y, double z)

// Intersection with ground detection
int intersectBoxComputeOnGround(Box box, double x, double y, double z)
```

### Query Results
```java
boolean isBoxIntersecting(Box box, double x, double y, double z)
boolean isTouching()
boolean touchesCeil()
```

> **See also:** [Math API - Box](math.md#box-aabb)

---

## CollisionModuleConfig
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Configuration for the collision module.

### Constants
```java
static final double MOVEMENT_THRESHOLD          // 1.0E-5 — minimum movement to trigger a collision check
static final double MOVEMENT_THRESHOLD_SQUARED  // MOVEMENT_THRESHOLD²
static final double EXTENT                      // 1.0E-5 — default extent value
```

### Methods
```java
// Maximum extent for collision queries
double getExtentMax()
void setExtentMax(double value)

// Debug: dump invalid block positions
boolean isDumpInvalidBlocks()
void setDumpInvalidBlocks(boolean dump)

// Debug (0.6.3+): also dump blocks that were tested but not overlapping
boolean isDumpNonOverlappingBlocks()
void setDumpNonOverlappingBlocks(boolean dump)

// Minimum thickness for collision surfaces
double getMinimumThickness()
void setMinimumThickness(double thickness)
boolean hasMinimumThickness()
```

---

## CollisionDataArray<T>
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Generic container for collision data elements. Used internally by `CollisionResult` for managing block collisions, character collisions, and triggers.

### Allocation
```java
T alloc()     // Allocate and return a new element
void reset()  // Clear all elements
```

### Access
```java
int getCount()
int size()
boolean isEmpty()
T get(int index)
T getFirst()
T forgetFirst()  // Get first element and remove it
void remove(int index)
```

### Sorting
```java
void sort(Comparator<? super T> comparator)
```

---

## WorldUtil
**Package:** `com.hypixel.hytale.server.core.modules.collision`

Final class of static helpers for querying block material and fluid state at world positions. Used by the physics/fluid paths; handy whenever you need "is this position solid / fluid / empty" without running a full collision query.

### Material Classification
```java
// Classify a block + fluid-id pair (fluidId 0 = no fluid)
static boolean isFluidOnlyBlock(BlockType blockType, int fluidId)  // Empty material AND fluid present
static boolean isSolidOnlyBlock(BlockType blockType, int fluidId)  // Solid material AND no fluid
static boolean isEmptyOnlyBlock(BlockType blockType, int fluidId)  // Empty material AND no fluid
```

### Fluid Queries
```java
// Fluid id at a block position (0 if none / out of range / chunk not loaded)
static int getFluidIdAtPosition(ComponentAccessor<ChunkStore> chunkStore,
        ChunkColumn column, int x, int y, int z)

// BlockMaterial ordinal + fluid id packed into one long (MathUtil.packLong);
// a fluid whose surface is below the queried y counts as no fluid
static long getPackedMaterialAndFluidAtPosition(Ref<ChunkStore> chunkRef,
        ComponentAccessor<ChunkStore> chunkStore, double x, double y, double z)

// Scan a column for fluid / the water surface level
static int findFluidBlock(ComponentAccessor<ChunkStore> chunkStore, ChunkColumn column,
        BlockChunk blocks, int x, int y, int z, boolean flag)
static int getWaterLevel(ComponentAccessor<ChunkStore> chunkStore, ChunkColumn column,
        BlockChunk blocks, int x, int y, int z)
```

### Empty-Space Scans
```java
// Scan down/up from (x, y, z) for the farthest empty block within a limit
static int findFarthestEmptySpaceBelow(ComponentAccessor<ChunkStore> chunkStore,
        ChunkColumn column, BlockChunk blocks, int x, int y, int z, int limit)
static int findFarthestEmptySpaceAbove(ComponentAccessor<ChunkStore> chunkStore,
        ChunkColumn column, BlockChunk blocks, int x, int y, int z, int limit)
```

> **Note:** Positions with `y < 0` or `y >= 320` read as empty with no fluid.

---

## CollisionResultComponent
**Package:** `com.hypixel.hytale.server.core.modules.entity.component`

Entity component that wraps a `CollisionResult` for per-entity collision tracking. Used internally by the physics system to track collision state between ticks.

### Getting the Component
```java
CollisionResultComponent collisionComp = store.getComponent(ref, CollisionResultComponent.getComponentType());
```

### Collision Result Access
```java
CollisionResult getCollisionResult()  // Get the wrapped CollisionResult
```

### Position Tracking
```java
Vector3d getCollisionStartPosition()      // Start position of collision check
Vector3d getCollisionPositionOffset()     // Position offset/movement
Vector3d getCollisionStartPositionCopy()  // Copy of start position
Vector3d getCollisionPositionOffsetCopy() // Copy of offset
void resetLocationChange()                // Reset position tracking
```

### Pending Collision State
```java
boolean isPendingCollisionCheck()    // Is a collision check pending?
void markPendingCollisionCheck()     // Mark for collision check
void consumePendingCollisionCheck()  // Clear pending flag
```

### Usage with Player
```java
// Configure trigger block processing for a player
Player player = store.getComponent(ref, Player.getComponentType());
CollisionResultComponent collisionComp = store.getComponent(ref, CollisionResultComponent.getComponentType());

if (collisionComp != null) {
    // Enable/disable trigger block processing
    player.configTriggerBlockProcessing(true, true, collisionComp);

    // Access collision result for custom processing
    CollisionResult result = collisionComp.getCollisionResult();
}
```

---

## SimplePhysicsProvider
**Package:** `com.hypixel.hytale.server.core.modules.physics`

**Implements:** `IBlockCollisionConsumer`

Self-contained physics integrator for simple ballistic bodies: gravity, drag/terminal velocity, bounces, fluid buoyancy and swimming damping, move-out-of-solid resolution, and a rest state. It consumes block collisions from the collision system (hence `IBlockCollisionConsumer`). Used by block entities (e.g. falling blocks) and legacy projectiles; the modern projectile path uses `StandardPhysicsProvider` (see [projectiles.md](projectiles.md#standardphysicsprovider)). As of 0.6.3 it records the block it came to rest on (`contactBlockPosition`, protected) and hands that to `RestingSupport`, so a resting body wakes and falls again when its support block is broken (`fallingAfterBreak`, protected — no public accessors on this class).

### Getting an Instance
```java
// Block entities create/own one
BlockEntity blockEntity = ...;
SimplePhysicsProvider physics = blockEntity.initPhysics(boundingBox);
physics = blockEntity.getSimplePhysicsProvider();

// Legacy projectiles expose theirs
SimplePhysicsProvider projectilePhysics = projectileComponent.getSimplePhysicsProvider();
```

### Constructors
```java
SimplePhysicsProvider()
SimplePhysicsProvider(
    BiConsumer<Vector3d, ComponentAccessor<EntityStore>> bounceConsumer,
    QuadConsumer<Ref<EntityStore>, Vector3d, Ref<EntityStore>,
                 ComponentAccessor<EntityStore>> impactConsumer)
```
The optional consumers are callbacks fired on bounces and on impacts.

### Ticking
```java
// Advance the body one step: integrates velocity, resolves block/character
// collisions, applies fluid forces, and updates the transform
Ref<EntityStore> tick(double deltaTime, Velocity velocity, World world,
        TransformComponent transform, Ref<EntityStore> ref,
        ComponentAccessor<EntityStore> accessor)
```

### Configuration
```java
void setGravity(double gravity, BoundingBox boundingBox)
void setBounciness(double bounciness)
void setTerminalVelocities(double terminalVelocity, double density, BoundingBox boundingBox)
void setTerminalVelocities(double terminalVelocity1, double density1,
        double terminalVelocity2, double density2, BoundingBox boundingBox)
SimplePhysicsProvider setImpactSlowdown(double slowdown)   // builder-style, returns this
void setSticksVertically(boolean sticks)
void setComputeYaw(boolean compute)
void setComputePitch(boolean compute)
void setProvideCharacterCollisions(boolean provide)
void setMoveOutOfSolid(boolean move)
void setMoveOutOfSolid(double speed)
void setCreatorId(UUID creatorUuid)

// Configure everything from a projectile asset config
void initialize(Projectile projectileConfig, BoundingBox boundingBox)
```

### State and Velocity
```java
boolean isOnGround()
boolean isSwimming()
boolean isImpacted()
void setImpacted(boolean impacted)
boolean isResting()
void setResting(boolean resting)
boolean isComputeYaw()
boolean isComputePitch()
boolean isProvidingCharacterCollisions()

Vector3d getVelocity()
void setVelocity(Vector3d velocity)
void addVelocity(float x, float y, float z)

// Reflect a vector off a surface normal (used for bounces)
static void computeReflectedVector(Vector3d velocity, Vector3d normal, Vector3d result)
```

### IBlockCollisionConsumer Callbacks
Called by the collision sweep; you normally don't invoke these yourself:
```java
IBlockCollisionConsumer.Result onCollision(int x, int y, int z, Vector3d movement,
        BlockContactData contact, BlockData block, Box box)
IBlockCollisionConsumer.Result probeCollisionDamage(int x, int y, int z, Vector3d movement,
        BlockContactData contact, BlockData block)
void onCollisionDamage(int x, int y, int z, Vector3d movement,
        BlockContactData contact, BlockData block)
IBlockCollisionConsumer.Result onCollisionSliceFinished()
void onCollisionFinished()
```

### Nested Enums
```java
// How the body's rotation follows its motion — set from a projectile's
// "RotationMode" JSON key (Projectile.getRotationMode(), default Velocity)
enum SimplePhysicsProvider.ROTATION_MODE { None, Velocity, VelocityDamped }

// Integrator lifecycle state
enum SimplePhysicsProvider.STATE { Active, Resting, Inactive }
```

---

## Usage Examples

### Basic Collision Query
```java
CollisionModule module = CollisionModule.get();
CollisionResult result = new CollisionResult();

Box hitbox = new Box(-0.3, 0, -0.3, 0.3, 1.8, 0.3);
Vector3d start = new Vector3d(x, y, z);
Vector3d end = new Vector3d(x + dx, y + dy, z + dz);

boolean hasCollision = CollisionModule.findCollisions(
    hitbox, start, end, result, accessor
);

if (hasCollision) {
    BlockCollisionData collision = result.getFirstBlockCollision();
    // Handle collision at collision.x, collision.y, collision.z
}
```

### Validate Entity Position
```java
CollisionModule module = CollisionModule.get();
CollisionResult result = new CollisionResult();

Box hitbox = new Box(-0.3, 0, -0.3, 0.3, 1.8, 0.3);
Vector3d position = new Vector3d(x, y, z);

int validateResult = module.validatePosition(world, hitbox, position, result);

if (validateResult == CollisionModule.VALIDATE_OK) {
    // Position is valid
}
if ((validateResult & CollisionModule.VALIDATE_ON_GROUND) != 0) {
    // Entity is on ground
}
```

### Check for Trigger Blocks
```java
CollisionResult result = new CollisionResult(false, true);  // Enable triggers
result.enableTriggerBlocks();

module.findIntersections(world, hitbox, position, result, true, false);

CollisionDataArray<BlockCollisionData> triggers = result.getTriggerBlocks();
// Process trigger blocks
```

### Filter Collisions by Material
```java
CollisionResult result = new CollisionResult();

// Only collide with solid blocks
result.setCollisionByMaterial(CollisionMaterial.MATERIAL_SOLID);

// Or exclude fluids
result.setCollisionByMaterial(
    CollisionMaterial.MATERIAL_SET_ANY,
    CollisionMaterial.MATERIAL_FLUID
);
```

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the collision subsystem (verified against `HytaleServer.jar`).

- **`Must provide supplier for CollisionDataArray`** → a `CollisionDataArray` was used without an element supplier configured. Fix: this is internal — use a `CollisionResult` (which sets up its arrays), rather than constructing `CollisionDataArray` directly.
- **Symptom:** trigger-block queries return nothing → trigger checking wasn't enabled on the `CollisionResult`. Fix: construct it with `new CollisionResult(false, true)` (or call `enableTriggerBlocks()`) before `findIntersections(..., true, false)` (see [Check for Trigger Blocks](#check-for-trigger-blocks)).
- **Symptom:** `intersectBox(...)` always looks "true" when used in an `if` → it returns an int result code, not a boolean. Fix: use `isBoxIntersecting(...)` for a boolean, or compare the returned code.
- **Symptom:** `setBox(...)`/`setPosition(...)`/`expandBox(...)` on `BoxBlockIntersectionEvaluator` seem to discard configuration → these return the evaluator (builder pattern), they are not void mutators. Fix: chain the calls or capture the returned instance.
- **Symptom:** `validatePosition` "succeeds" but the entity is mid-air/on-ground checks fail → the result is a flag set, not a single value. Fix: test `== VALIDATE_OK` for validity and mask with `& VALIDATE_ON_GROUND` (etc.) for the individual flags (see [Validate Entity Position](#validate-entity-position)).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
