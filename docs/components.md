---
title: "Components (ECS) API"
description: "Use Hytale's Entity Component System in Java — typed component Stores accessed via Ref handles, Component/Resource type descriptors, and entity composition via Holder blueprints."
seo:
  type: TechArticle
---

# Components (ECS) API

**Doc type:** Java API · **Verified against 0.5.0**

Hytale uses an Entity Component System (ECS) architecture. Entities are composed of components stored in typed stores.

## Overview

Implemented in `com.hypixel.hytale.component` and provides:
- Typed component stores (`Store<EntityStore>`, `Store<ChunkStore>`) accessed via `Ref` handles
- Components, resources, and their type descriptors (`Component`, `ComponentType`, `Resource`, `ResourceType`)
- Entity composition via `Holder` blueprints and `Archetype` descriptions
- Querying and filtering entities (`Query` and its `and`/`or`/`not`/`any` combinators)
- Deferred, iteration-safe mutation via `CommandBuffer`
- A `ComponentRegistry` for registering components, resources, systems, and event types
- Ticking systems (`EntityTickingSystem`) for per-tick entity processing

## Architecture
```
ComponentRegistry (per ECS type: EntityStore / ChunkStore)
├── Store<ECS_TYPE> (the live entity/component container)
│   ├── Ref<ECS_TYPE> (handle to one entity)
│   ├── ArchetypeChunk (component access by index during iteration)
│   └── CommandBuffer (deferred add/remove/spawn during iteration)
├── Composition
│   ├── Component / ComponentType
│   ├── Holder (entity blueprint) → Archetype (component layout)
│   └── Resource / ResourceType (world-level singletons)
├── Query (filter entities; and / or / not / any)
└── Systems
    └── EntityTickingSystem (per-tick processing, filtered by getQuery())
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Store<ECS_TYPE>` | `component` | Container for entities and components; implements `ComponentAccessor` |
| `Ref<ECS_TYPE>` | `component` | Lightweight handle to a single entity |
| `Component<ECS_TYPE>` | `component` | Interface for all components (must be cloneable) |
| `ComponentType<ECS_TYPE, T>` | `component` | Type descriptor for a component; also usable as a `Query` |
| `ComponentAccessor<ECS_TYPE>` | `component` | Interface for component access; `Store` implements it |
| `ArchetypeChunk<ECS_TYPE>` | `component` | Indexed component access during iteration / event handling |
| `CommandBuffer<ECS_TYPE>` | `component` | Deferred entity/component operations during iteration |
| `Holder<ECS_TYPE>` | `component` | Blueprint/template for creating entities |
| `Archetype<ECS_TYPE>` | `component` | Describes a component composition; implements `Query` |
| `Resource<ECS_TYPE>` | `component` | Marker interface for world-level singleton resources |
| `ResourceType<ECS_TYPE, T>` | `component` | Type descriptor for resources |
| `ComponentRegistry<ECS_TYPE>` | `component` | Registers components, resources, systems, and event types |
| `Query<ECS_TYPE>` | `component.query` | Filters entities by component composition |
| `EntityTickingSystem<ECS_TYPE>` | `component.system.tick` | Base class for per-tick entity processing |
| `EntityStore` | `server.core.universe.world.storage` | ECS type parameter for entity components |
| `ChunkStore` | `server.core.universe.world.storage` | ECS type parameter for chunk components |
| `TransformComponent` | `server.core.modules.entity.component` | Stores entity position and rotation |
| `Teleport` | `server.core.modules.entity.teleport` | Action component triggering player teleportation |

## Core Types

### Store<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Container for entities and their components. Implements `ComponentAccessor`.

#### Component Operations
```java
// Get component from entity
<T extends Component<ECS_TYPE>> T getComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)

// Add component (creates if not exists)
<T extends Component<ECS_TYPE>> T addComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void addComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)

// Ensure component exists and get it
<T extends Component<ECS_TYPE>> T ensureAndGetComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)

// Replace/put component
<T extends Component<ECS_TYPE>> void putComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)
<T extends Component<ECS_TYPE>> void replaceComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)

// Remove component
<T extends Component<ECS_TYPE>> void removeComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void tryRemoveComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> boolean removeComponentIfExists(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
```

#### Entity Management
```java
// Add entity from holder (blueprint)
Ref<ECS_TYPE> addEntity(Holder<ECS_TYPE> holder, AddReason reason)

// Remove entity
Holder<ECS_TYPE> removeEntity(Ref<ECS_TYPE> ref, RemoveReason reason)

// Copy entity
Holder<ECS_TYPE> copyEntity(Ref<ECS_TYPE> ref)
```

#### Query Entities
```java
int getEntityCount()
int getEntityCountFor(Query<ECS_TYPE> query)
Archetype<ECS_TYPE> getArchetype(Ref<ECS_TYPE> ref)
```

#### Iterate Entities
```java
void forEachChunk(BiConsumer<ArchetypeChunk<ECS_TYPE>, CommandBuffer<ECS_TYPE>> consumer)
void forEachChunk(Query<ECS_TYPE> query, BiConsumer<ArchetypeChunk<ECS_TYPE>, CommandBuffer<ECS_TYPE>> consumer)
void forEachEntityParallel(IntBiObjectConsumer<ArchetypeChunk<ECS_TYPE>, CommandBuffer<ECS_TYPE>> consumer)
```

#### Resources (World-Level Singletons)
```java
<T extends Resource<ECS_TYPE>> T getResource(ResourceType<ECS_TYPE, T> type)
<T extends Resource<ECS_TYPE>> void replaceResource(ResourceType<ECS_TYPE, T> type, T resource)
```

#### Events
```java
<Event extends EcsEvent> void invoke(Ref<ECS_TYPE> ref, Event event)
<Event extends EcsEvent> void invoke(Event event)
```

#### Utility
```java
ECS_TYPE getExternalData()
ComponentRegistry<ECS_TYPE> getRegistry()
boolean isProcessing()
boolean isInThread()
void assertThread()
```

> **See also:** [Inventory API](inventory.md#itemcontainer)

---

### Ref<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Lightweight reference to an entity in a store. Used as a pointer to access entity data.

#### Constructors
```java
Ref(Store<ECS_TYPE> store)
Ref(Store<ECS_TYPE> store, int index)
```

#### Methods
```java
Store<ECS_TYPE> getStore()
int getIndex()
boolean isValid()
void validate()
void invalidate()
```

---

### Component<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Interface for all components. Must be cloneable.

```java
Component<ECS_TYPE> clone()
default Component<ECS_TYPE> cloneSerializable()
```

---

### ComponentType<ECS_TYPE, T>
**Package:** `com.hypixel.hytale.component`

Type descriptor for a component. Used to get/set components.

**Note:** `ComponentType` implements `Query<ECS_TYPE>`, so it can be used directly where a Query is required.

```java
ComponentRegistry<ECS_TYPE> getRegistry()
Class<? super T> getTypeClass()
int getIndex()
boolean test(Archetype<ECS_TYPE> archetype)
boolean requiresComponentType(ComponentType<ECS_TYPE, ?> type)
```

---

### ComponentAccessor<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Interface for accessing components. Store implements this.

```java
<T extends Component<ECS_TYPE>> T getComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> T ensureAndGetComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void putComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)
<T extends Component<ECS_TYPE>> void addComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)
<T extends Component<ECS_TYPE>> T addComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void removeComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
Archetype<ECS_TYPE> getArchetype(Ref<ECS_TYPE> ref)
<T extends Resource<ECS_TYPE>> T getResource(ResourceType<ECS_TYPE, T> type)
ECS_TYPE getExternalData()
```

---

### ArchetypeChunk<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Used in `EntityEventSystem` handlers and iteration to access components by entity index.

```java
// Get component for entity at index
<T extends Component<ECS_TYPE>> T getComponent(int index, ComponentType<ECS_TYPE, T> type)

// Number of entities in this chunk
int size()
```

See [Events API - ECS Events](events.md#ecs-events-entityeventsystem) for usage example.

---

### Query<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.query`

Interface for filtering entities by their component composition. Used with `Store.forEachChunk()`, `Store.getEntityCountFor()`, and as the return type for `EntityEventSystem.getQuery()`.

**Note:** `ComponentType` implements `Query`, so you can use a component type directly as a query.

#### Static Factory Methods
```java
// Match any entity (no filtering)
static <ECS_TYPE> AnyQuery<ECS_TYPE> any()

// Match entities that do NOT match the given query
static <ECS_TYPE> NotQuery<ECS_TYPE> not(Query<ECS_TYPE> query)

// Match entities that match ALL given queries
static <ECS_TYPE> AndQuery<ECS_TYPE> and(Query<ECS_TYPE>... queries)

// Match entities that match ANY of the given queries
static <ECS_TYPE> OrQuery<ECS_TYPE> or(Query<ECS_TYPE>... queries)
```

#### Methods
```java
// Test if an archetype matches this query
boolean test(Archetype<ECS_TYPE> archetype)

// Check if query requires a specific component type
boolean requiresComponentType(ComponentType<ECS_TYPE, ?> type)

// Validation
void validateRegistry(ComponentRegistry<ECS_TYPE> registry)
void validate()
```

#### Usage Examples
```java
// Simple query - match entities with Player component
Query<EntityStore> playerQuery = Player.getComponentType();

// Match any entity
Query<EntityStore> allEntities = Query.any();

// Match entities WITHOUT a component
Query<EntityStore> nonPlayers = Query.not(Player.getComponentType());

// Match entities with BOTH Player AND Health
Query<EntityStore> playersWithHealth = Query.and(
    Player.getComponentType(),
    Health.getComponentType()
);

// Match entities with Player OR NPC
Query<EntityStore> actors = Query.or(
    Player.getComponentType(),
    NPC.getComponentType()
);

// Combined query - entities with Player but not Dead
Query<EntityStore> alivePlayers = Query.and(
    Player.getComponentType(),
    Query.not(Dead.getComponentType())
);

// Use in EntityEventSystem
public class MySystem extends EntityEventSystem<EntityStore, MyEvent> {
    @Override
    public Query<EntityStore> getQuery() {
        return Query.and(
            Player.getComponentType(),
            SomeOtherComponent.getComponentType()
        );
    }
}

// Use with Store iteration
store.forEachChunk(playerQuery, (chunk, buffer) -> {
    // Process matching entities
});

// Count matching entities
int count = store.getEntityCountFor(playerQuery);
```

---

### CommandBuffer<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Buffer for deferred entity/component operations during ECS system iteration. Implements `ComponentAccessor`. Used in `EntityEventSystem.handle()` and `EntityTickingSystem.tick()` to safely modify entities while iterating.

Operations are queued and applied after the current iteration completes, avoiding concurrent modification issues.

#### Read Operations (Immediate)
```java
// Get store reference
Store<ECS_TYPE> getStore()

// Get component (reads current state)
<T extends Component<ECS_TYPE>> T getComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)

// Get entity archetype
Archetype<ECS_TYPE> getArchetype(Ref<ECS_TYPE> ref)

// Get resource
<T extends Resource<ECS_TYPE>> T getResource(ResourceType<ECS_TYPE, T> type)

// Get external data
ECS_TYPE getExternalData()
```

#### Deferred Entity Operations
```java
// Add entity from holder
Ref<ECS_TYPE> addEntity(Holder<ECS_TYPE> holder, AddReason reason)

// Add entity with pre-allocated ref
Ref<ECS_TYPE> addEntity(Holder<ECS_TYPE> holder, Ref<ECS_TYPE> ref, AddReason reason)

// Add multiple entities
Ref<ECS_TYPE>[] addEntities(Holder<ECS_TYPE>[] holders, AddReason reason)
void addEntities(Holder<ECS_TYPE>[] holders, int holderOffset,
                 Ref<ECS_TYPE>[] refs, int refOffset, int count, AddReason reason)

// Remove entity
void removeEntity(Ref<ECS_TYPE> ref, RemoveReason reason)
void tryRemoveEntity(Ref<ECS_TYPE> ref, RemoveReason reason)
Holder<ECS_TYPE> removeEntity(Ref<ECS_TYPE> ref, Holder<ECS_TYPE> outHolder, RemoveReason reason)

// Copy entity to holder
Holder<ECS_TYPE> copyEntity(Ref<ECS_TYPE> ref, Holder<ECS_TYPE> outHolder)
```

#### Deferred Component Operations
```java
// Add component
<T extends Component<ECS_TYPE>> T addComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void addComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)

// Ensure component exists
<T extends Component<ECS_TYPE>> void ensureComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> T ensureAndGetComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)

// Replace/put component
<T extends Component<ECS_TYPE>> void replaceComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)
<T extends Component<ECS_TYPE>> void putComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type, T component)

// Remove component
<T extends Component<ECS_TYPE>> void removeComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void tryRemoveComponent(Ref<ECS_TYPE> ref, ComponentType<ECS_TYPE, T> type)
```

#### Event Invocation
```java
// Invoke event on specific entity
<Event extends EcsEvent> void invoke(Ref<ECS_TYPE> ref, Event event)
<Event extends EcsEvent> void invoke(EntityEventType<ECS_TYPE, Event> type, Ref<ECS_TYPE> ref, Event event)

// Invoke world-level event
<Event extends EcsEvent> void invoke(Event event)
<Event extends EcsEvent> void invoke(WorldEventType<ECS_TYPE, Event> type, Event event)
```

#### Custom Operations
```java
// Queue arbitrary operation
void run(Consumer<Store<ECS_TYPE>> consumer)
```

#### Parallel Processing
```java
// Create a fork for parallel work
CommandBuffer<ECS_TYPE> fork()

// Merge parallel buffer back
void mergeParallel(CommandBuffer<ECS_TYPE> forkedBuffer)
```

#### Utility
```java
boolean setThread()
void validateEmpty()
```

#### Usage Example
```java
public class MyEventSystem extends EntityEventSystem<EntityStore, MyEvent> {

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       MyEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());

        // Read component (immediate)
        Health health = buffer.getComponent(ref, Health.getComponentType());

        // Deferred: add component
        buffer.addComponent(ref, MarkerComponent.getComponentType());

        // Deferred: remove component
        buffer.removeComponent(ref, OldComponent.getComponentType());

        // Deferred: spawn new entity
        Holder<EntityStore> holder = store.getRegistry().newHolder();
        holder.addComponent(SomeComponent.getComponentType(), new SomeComponent());
        buffer.addEntity(holder, AddReason.SPAWN);

        // Deferred: arbitrary operation
        buffer.run(s -> {
            // Operations on store after iteration
            s.getResource(MyResource.getResourceType()).incrementCounter();
        });
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

## Blueprint and Composition Types

### Holder<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Blueprint/template for creating entities. Use to define entity composition before adding to store. `Holder` has no public constructor — obtain one via `registry.newHolder()`.

```java
// Get archetype (component composition)
Archetype<ECS_TYPE> getArchetype()

// Component management
<T extends Component<ECS_TYPE>> T ensureComponent(ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void addComponent(ComponentType<ECS_TYPE, T> type, T component)
<T extends Component<ECS_TYPE>> void putComponent(ComponentType<ECS_TYPE, T> type, T component)
<T extends Component<ECS_TYPE>> T getComponent(ComponentType<ECS_TYPE, T> type)
<T extends Component<ECS_TYPE>> void removeComponent(ComponentType<ECS_TYPE, T> type)

// Cloning
Holder<ECS_TYPE> clone()
```

#### Usage
```java
// Create entity from holder (obtain holder from the registry)
Holder<EntityStore> holder = store.getRegistry().newHolder();
holder.addComponent(MyComponent.getComponentType(), new MyComponent());
Ref<EntityStore> entityRef = store.addEntity(holder, AddReason.SPAWN);
```

---

### Archetype<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Describes the composition of components for entities. Implements `Query<ECS_TYPE>`.

```java
// Check for component
boolean contains(ComponentType<ECS_TYPE, ?> type)

// Count components
int count()
int length()

// Query matching
boolean test(Archetype<ECS_TYPE> archetype)

// Factory methods
static <ECS_TYPE> Archetype<ECS_TYPE> of(ComponentType<ECS_TYPE, ?>... types)

// Query matching
boolean requiresComponentType(ComponentType<ECS_TYPE, ?> type)

// Modify archetype (STATIC; returns new instance)
static <ECS_TYPE, T extends Component<ECS_TYPE>> Archetype<ECS_TYPE> add(Archetype<ECS_TYPE> archetype, ComponentType<ECS_TYPE, T> type)
static <ECS_TYPE, T extends Component<ECS_TYPE>> Archetype<ECS_TYPE> remove(Archetype<ECS_TYPE> archetype, ComponentType<ECS_TYPE, T> type)

// Serialization
Archetype<ECS_TYPE> getSerializableArchetype(ComponentRegistry.Data<ECS_TYPE> data)
```

---

## Resource Types

### Resource<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Interface for world-level singleton resources (not per-entity).

```java
// Marker interface - implement for your resource classes
```

### ResourceType<ECS_TYPE, T>
**Package:** `com.hypixel.hytale.component`

Type descriptor for resources.

```java
ComponentRegistry<ECS_TYPE> getRegistry()
Class<? super T> getTypeClass()
int getIndex()
```

---

## Enums

### AddReason
Reason for adding an entity to the store.

```java
public enum AddReason {
    SPAWN,
    LOAD
}
```

### RemoveReason
Reason for removing an entity from the store.

```java
public enum RemoveReason {
    REMOVE,
    UNLOAD
}
```

---

## Annotations

### @NonSerialized
Mark components or fields that should not be serialized.

### @NonTicking
Mark components that should not participate in ticking systems.

---

## Common Store Types

The ECS system uses two primary store types:
- `Store<EntityStore>` - Entity components (Player, PlayerRef, TransformComponent, etc.)
- `Store<ChunkStore>` - Chunk components (WorldChunk, block data, etc.)

---

## EntityStore
**Package:** `com.hypixel.hytale.server.core.universe.world.storage`

The ECS type parameter for entity components. Provides access to entity references and the component registry.

### Static Fields
```java
static final ComponentRegistry<EntityStore> REGISTRY  // Component registry for entities
```

### Methods
```java
Store<EntityStore> getStore()                    // Get the entity store
Ref<EntityStore> getRefFromUUID(UUID uuid)       // Get entity ref by UUID
Ref<EntityStore> getRefFromNetworkId(int id)     // Get entity ref by network ID
int takeNextNetworkId()                          // Allocate next network ID
World getWorld()                                 // Get the world
```

### Usage
```java
// In a command or system, you receive Store<EntityStore>
Store<EntityStore> store = ...;

// Get component from entity
Player player = store.getComponent(ref, Player.getComponentType());

// Find entity by UUID
Ref<EntityStore> entityRef = entityStore.getRefFromUUID(uuid);
```

---

## ChunkStore
**Package:** `com.hypixel.hytale.server.core.universe.world.storage`

The ECS type parameter for chunk components. Provides access to chunk references and loading.

### Static Fields
```java
static final ComponentRegistry<ChunkStore> REGISTRY  // Component registry for chunks
```

### Methods
```java
Store<ChunkStore> getStore()                     // Get the chunk store
World getWorld()                                 // Get the world

// Chunk access
Ref<ChunkStore> getChunkReference(long index)    // Get chunk ref by packed index
Ref<ChunkStore> getChunkSectionReference(int x, int y, int z)  // Get chunk by coordinates

// Async chunk access
CompletableFuture<Ref<ChunkStore>> getChunkSectionReferenceAsync(int x, int y, int z)
CompletableFuture<Ref<ChunkStore>> getChunkReferenceAsync(long index)

// Get component directly
<T> T getChunkComponent(long index, ComponentType<ChunkStore, T> type)

// Statistics
int getLoadedChunksCount()
int getTotalGeneratedChunksCount()
int getTotalLoadedChunksCount()
```

---

## ComponentRegistry<ECS_TYPE>
**Package:** `com.hypixel.hytale.component`

Registry for components, resources, systems, and event types. Access via `EntityStore.REGISTRY` or `ChunkStore.REGISTRY`.

### Component Registration
```java
<T> ComponentType<ECS_TYPE, T> registerComponent(Class<? super T> clazz, Supplier<T> supplier)
<T> ComponentType<ECS_TYPE, T> registerComponent(Class<? super T> clazz, String name, BuilderCodec<T> codec)
<T> void unregisterComponent(ComponentType<ECS_TYPE, T> type)
<T> T createComponent(ComponentType<ECS_TYPE, T> type)
```

### Resource Registration
```java
<T> ResourceType<ECS_TYPE, T> registerResource(Class<? super T> clazz, Supplier<T> supplier)
<T> ResourceType<ECS_TYPE, T> registerResource(Class<? super T> clazz, String name, BuilderCodec<T> codec)
<T> void unregisterResource(ResourceType<ECS_TYPE, T> type)
```

### System Registration
```java
void registerSystem(ISystem<ECS_TYPE> system)
void registerSystem(ISystem<ECS_TYPE> system, boolean enabled)
void unregisterSystem(Class<? extends ISystem<ECS_TYPE>> systemClass)
SystemGroup<ECS_TYPE> registerSystemGroup()
void unregisterSystemGroup(SystemGroup<ECS_TYPE> group)
```

### Event Type Registration
```java
<T> EntityEventType<ECS_TYPE, T> registerEntityEventType(Class<? super T> eventClass)
<T> WorldEventType<ECS_TYPE, T> registerWorldEventType(Class<? super T> eventClass)
<T> void unregisterEntityEventType(EntityEventType<ECS_TYPE, T> type)
<T> void unregisterWorldEventType(WorldEventType<ECS_TYPE, T> type)
```

### Holder Creation
```java
Holder<ECS_TYPE> newHolder()
Holder<ECS_TYPE> newHolder(Archetype<ECS_TYPE> archetype, Component<ECS_TYPE>[] components)
```

### Query Methods
```java
boolean hasSystem(ISystem<ECS_TYPE> system)
<T> boolean hasSystemClass(Class<T> systemClass)
<T> EntityEventType<ECS_TYPE, T> getEntityEventTypeForClass(Class<T> eventClass)
<T> WorldEventType<ECS_TYPE, T> getWorldEventTypeForClass(Class<T> eventClass)
```

---

## TransformComponent
**Package:** `com.hypixel.hytale.server.core.modules.entity.component`

Component storing entity position and rotation. Present on all positioned entities.

### Getting the Component
```java
TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
```

### Position Methods
```java
Vector3d getPosition()
void setPosition(Vector3d position)
void teleportPosition(Vector3d position)  // Teleport (bypasses interpolation)
```

### Rotation Methods
```java
Vector3f getRotation()
void setRotation(Vector3f rotation)
void teleportRotation(Vector3f rotation)  // Teleport rotation
```

### Transform Access
```java
Transform getTransform()  // Get combined position/rotation
```

### Chunk Access
```java
WorldChunk getChunk()                // Get current chunk
Ref<ChunkStore> getChunkRef()        // Get chunk reference
void setChunkLocation(Ref<ChunkStore> ref, WorldChunk chunk)
void markChunkDirty(ComponentAccessor<EntityStore> accessor)
```

### Usage Example
```java
// Get entity position
TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
if (transform != null) {
    Vector3d pos = transform.getPosition();
    Vector3f rot = transform.getRotation();

    // Teleport entity
    transform.teleportPosition(new Vector3d(100, 64, 100));
}
```

> **See also:** [Math API](math.md#transform)

---

## Action Components

Some operations in Hytale use "action components" — components you add to an entity that trigger systems to perform an action, rather than storing persistent state. This is an ECS pattern where adding a component causes a system to process it, perform the action, and often remove the component afterward.

### The Pattern

1. **Create** an action component using a factory method
2. **Add** the component to the entity store
3. **System processes** the component and performs the action
4. **Component removed** (automatically by the system)

### Teleport Module

The `Teleport` component is the primary example of this pattern. Instead of calling `transform.teleportPosition()` directly, you add a `Teleport` component and the `TeleportSystems` process it.

**Package:** `com.hypixel.hytale.server.core.modules.entity.teleport`

#### Factory Methods
```java
// Create teleport for a player (handles player-specific synchronization)
static Teleport createForPlayer(World world, Vector3d position, Vector3f rotation)

// Get component type for ECS operations
static ComponentType<EntityStore, Teleport> getComponentType()
```

#### Usage Example
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    Transform current = playerRef.getTransform();
    Vector3d targetPos = new Vector3d(100, 64, 200);

    // Create teleport component for player
    Teleport teleport = Teleport.createForPlayer(world, targetPos, current.getRotation());

    // Add to store - TeleportSystems will process this and move the player
    store.addComponent(ref, Teleport.getComponentType(), teleport);

    playerRef.sendMessage(Message.raw("Teleporting..."));
}
```

### Direct Teleport vs Action Component

Both approaches exist for teleportation:

| Approach | Method | Use Case |
|----------|--------|----------|
| Direct | `transform.teleportPosition(pos)` | Simple position changes, NPCs |
| Action Component | `store.addComponent(ref, Teleport.getComponentType(), teleport)` | Player teleportation with proper client sync |

**When to use each:**
- **Action Component (Teleport):** Recommended for players — handles network synchronization, chunk loading, and client state properly
- **Direct (TransformComponent):** Suitable for server-side entities or when you need immediate position changes without system processing

### Other Action Components

The action component pattern may be used by other modules. Look for:
- Static factory methods like `createFor*()`
- Components that trigger behavior rather than store state
- Systems that process and remove components

> **Note:** Action components differ from persistent components. Persistent components (like `Player`, `Inventory`, `Health`) store ongoing state. Action components represent a one-time request for the ECS to perform an operation.

---

## Usage in Commands
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // Get Player component
    Player player = store.getComponent(ref, Player.getComponentType());

    // Get PlayerRef component (alternative)
    PlayerRef pref = store.getComponent(ref, PlayerRef.getComponentType());

    // Check if component exists
    TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
    if (transform != null) {
        // Use transform
    }

    // Get entity archetype
    Archetype<EntityStore> archetype = store.getArchetype(ref);
    if (archetype.contains(Player.getComponentType())) {
        // Entity is a player
    }
}
```

---

## Creating Custom Components

```java
public class MyCustomComponent implements Component<EntityStore> {
    private int value;

    public MyCustomComponent() {
        this.value = 0;
    }

    public MyCustomComponent(int value) {
        this.value = value;
    }

    public int getValue() {
        return value;
    }

    public void setValue(int value) {
        this.value = value;
    }

    @Override
    public Component<EntityStore> clone() {
        return new MyCustomComponent(this.value);
    }

    // Register with ComponentRegistryProxy
    private static ComponentType<EntityStore, MyCustomComponent> TYPE;

    public static ComponentType<EntityStore, MyCustomComponent> getComponentType() {
        return TYPE;
    }
}
```

---

## Entity Iteration Example

```java
// Iterate all entities with Player component
store.forEachChunk(Player.getComponentType(), (chunk, buffer) -> {
    for (int i = 0; i < chunk.size(); i++) {
        Player player = chunk.getComponent(i, Player.getComponentType());
        // Process player
    }
});

// Count entities matching query
int playerCount = store.getEntityCountFor(Player.getComponentType());
```

---

## Working with Holders

```java
// Get holder from entity (for copying or inspection)
Holder<EntityStore> holder = store.copyEntity(ref);

// Modify holder and create new entity
holder.putComponent(SomeComponent.getComponentType(), new SomeComponent());
Ref<EntityStore> newEntity = store.addEntity(holder, AddReason.SPAWN);
```

---

## Resource Example

```java
// Get world-level resource
MyWorldResource resource = store.getResource(MyWorldResource.getResourceType());

// Replace resource
store.replaceResource(MyWorldResource.getResourceType(), newResource);
```

---

## Ticking Systems

For per-frame entity processing, extend `EntityTickingSystem`.

### EntityTickingSystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system.tick`

Abstract base class for systems that process entities every tick. Part of the system hierarchy:

```
ISystem (interface)
  └── System (abstract)
        └── TickingSystem (abstract)
              └── ArchetypeTickingSystem (abstract)
                    └── EntityTickingSystem (abstract)
```

#### Methods to Override
```java
// Called once per entity per tick
public abstract void tick(float deltaTime, int index,
                          ArchetypeChunk<ECS_TYPE> chunk,
                          Store<ECS_TYPE> store,
                          CommandBuffer<ECS_TYPE> buffer);

// Define which entities to process (from QuerySystem interface)
public Query<ECS_TYPE> getQuery();
```

#### Example: Per-Player Ticking System

Full working example: [`examples/entity-count/.../EntityCountTickingSystem.java`](../examples/entity-count/src/main/java/hytale/examples/entitycount/EntityCountTickingSystem.java) (counts world entities each tick, filtered to `Player.getComponentType()`, and pushes totals to a live HUD).

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class MyTickingSystem extends EntityTickingSystem<EntityStore> {

    @Override
    public void tick(float deltaTime, int index, ArchetypeChunk<EntityStore> chunk,
                     Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player == null) return;

        // Process player each tick
        // deltaTime = time since last tick in seconds
    }

    @Override
    public Query<EntityStore> getQuery() {
        // Only tick entities with Player component
        return Player.getComponentType();
    }
}
```

#### Registering the System
```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new MyTickingSystem());
}
```

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 component system (verified against `HytaleServer.jar`).

- **`Entity already contains component type:`** → you added a component to an entity that already has one of that type. Fix: use `putComponent`/`replaceComponent` to overwrite, or `ensureAndGetComponent` to add-or-get.
- **`ComponentType is already in Archetype!`** → an archetype build added the same `ComponentType` twice. Fix: add each component type to a `Holder`/`Archetype` only once.
- **`ComponentType is not in archetype:`** → you removed (or read by required slot) a component the entity doesn't have. Fix: guard with `archetype.contains(type)` / `getComponent(...) != null`, or use `tryRemoveComponent` / `removeComponentIfExists`.
- **`eventTypeClass must extend EcsEvent!`** → `registerEntityEventType`/`registerWorldEventType` got a class that isn't an `EcsEvent`. Fix: make your ECS event class extend `EcsEvent` (or `CancellableEcsEvent`).
- **`System is already registered!`** → the same system instance was passed to `registerSystem()` twice. Fix: register each system instance once (registering in `setup()` already runs once per plugin load).
- **`System dependency isn't registered:`** → a system declares a dependency on another system that wasn't registered first. Fix: register the dependency system before the dependent one.
- **Symptom:** modifying an entity's components directly inside a `tick()`/`handle()` iteration corrupts iteration → structural changes during iteration are unsafe. Fix: route add/remove/spawn through the `CommandBuffer` passed in (operations are applied after iteration completes).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
