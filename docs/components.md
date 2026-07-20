---
title: "Components (ECS) API"
description: "Use Hytale's Entity Component System in Java — typed component Stores accessed via Ref handles, Component/Resource type descriptors, and entity composition via Holder blueprints."
seo:
  type: TechArticle
---

# Components (ECS) API

**Doc type:** Java API · **Verified against 0.5.7**

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
| `DelayedEntitySystem<ECS_TYPE>` | `component.system.tick` | Per-entity processing on a fixed interval instead of every tick |
| `RunWhenPausedSystem<ECS_TYPE>` | `component.system.tick` | Marker interface — the system also ticks while the world is paused |
| `RefSystem<ECS_TYPE>` | `component.system` | Lifecycle callbacks with a live `Ref` when matching entities are added/removed |
| `HolderSystem<ECS_TYPE>` | `component.system` | Lifecycle callbacks with the entity's `Holder` data on add/remove |
| `StoreSystem<ECS_TYPE>` | `component.system` | Callbacks when the system itself is added to / removed from a store |
| `DelayedSystem<ECS_TYPE>` | `component.system` | Store-wide ticking on a fixed interval instead of every tick |
| `WorldEventSystem<ECS_TYPE, EventType>` | `component.system` | Handles world-level ECS events (no target entity) |
| `Dependency<ECS_TYPE>` | `component.dependency` | Base class for system ordering constraints |
| `SystemDependency<ECS_TYPE, T>` | `component.dependency` | Order a system before/after another system class |
| `SystemGroupDependency<ECS_TYPE>` | `component.dependency` | Order a system before/after a `SystemGroup` |
| `RootDependency<ECS_TYPE>` | `component.dependency` | Pin a system toward the very start/end of the system order |
| `Order` / `OrderPriority` | `component.dependency` | `BEFORE`/`AFTER` direction plus tie-break priority for dependencies |
| `SystemType<ECS_TYPE, T>` | `component` | Type descriptor for a registered system class (like `ComponentType` for systems) |
| `DisableProcessingAssert` | `component` | Marker interface — opts a system out of the store's processing assertion |
| `SpatialSystem<ECS_TYPE>` | `component.spatial` | Ticking system that maintains a spatial index of matching entities |
| `SpatialResource<T, ECS_TYPE>` | `component.spatial` | World resource holding a spatial index (`SpatialData` + `SpatialStructure`) |
| `SpatialStructure<T>` / `KDTree<T>` | `component.spatial` | Position queries — closest / radius / cylinder / box / distance-ordered |
| `SpatialData<T>` | `component.spatial` | Flat position + payload buffer a spatial structure is rebuilt from |
| `UnknownComponents<ECS_TYPE>` | `component.data.unknown` | Preserves serialized data of unregistered component types across save/load |
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
```

> ⚠️ **`addComponent` throws if the component already exists** —
> `IllegalArgumentException: Entity already contains component type: ...`. There is **no
> `tryAddComponent`** (the remove side has `tryRemoveComponent`, but add does not). Guard with
> `getComponent(ref, type) == null` first, or use `ensureAndGetComponent` for add-or-get semantics.
> An **uncaught throw inside an interaction crashes the world thread**, which halts tick systems
> game-wide (e.g. player stamina stops regenerating) and aborts the rest of the interaction chain
> until restart — so this is not a localized failure.

```java

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

## Choosing a System Base Class

`EntityTickingSystem` is one of several abstract system bases in `com.hypixel.hytale.component.system`. All of them are registered the same way (`registry.registerSystem(new MySystem())`); pick by what should trigger your code:

| You want to... | Extend | Override |
|----------------|--------|----------|
| Process matching entities every tick | `EntityTickingSystem<ECS_TYPE>` | `tick(...)`, `getQuery()` |
| Process matching entities on a fixed interval | `DelayedEntitySystem<ECS_TYPE>` | `tick(...)`, `getQuery()` (interval via constructor) |
| Run store-wide logic on a fixed interval | `DelayedSystem<ECS_TYPE>` | `delayedTick(...)` (interval via constructor) |
| React when matching entities spawn/despawn (live entity) | `RefSystem<ECS_TYPE>` | `onEntityAdded(...)`, `onEntityRemove(...)`, `getQuery()` |
| Inspect/adjust entity data as it enters/leaves the store | `HolderSystem<ECS_TYPE>` | `onEntityAdd(...)`, `onEntityRemoved(...)`, `getQuery()` |
| Set up / tear down per-world state with the system | `StoreSystem<ECS_TYPE>` | `onSystemAddedToStore(...)`, `onSystemRemovedFromStore(...)` |
| Handle an ECS event targeted at an entity | `EntityEventSystem<ECS_TYPE, Event>` | see [Events API](events.md#ecs-events-entityeventsystem) |
| Handle a world-level ECS event | `WorldEventSystem<ECS_TYPE, Event>` | `handle(store, buffer, event)` |

### RefSystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system`

Lifecycle callbacks fired when an entity matching `getQuery()` is added to or removed from the store. You get a live `Ref` plus a `CommandBuffer`, so you can read components and queue follow-up mutations safely.

```java
public abstract void onEntityAdded(Ref<ECS_TYPE> ref, AddReason reason,
                                   Store<ECS_TYPE> store, CommandBuffer<ECS_TYPE> buffer)
public abstract void onEntityRemove(Ref<ECS_TYPE> ref, RemoveReason reason,
                                    Store<ECS_TYPE> store, CommandBuffer<ECS_TYPE> buffer)
public abstract Query<ECS_TYPE> getQuery()   // from QuerySystem
```

This is the standard "player joined the world" hook: a `RefSystem<EntityStore>` with `getQuery()` returning `Player.getComponentType()` gets `onEntityAdded` for every player entity. Check `AddReason` (`SPAWN` vs `LOAD`) / `RemoveReason` (`REMOVE` vs `UNLOAD`) to distinguish fresh spawns from persistence loads.

> **Note the asymmetric names:** `onEntityAdded` (past tense) but `onEntityRemove` (present) — `RefSystem` fires *after* the entity is in the store and *before* it leaves. The `HolderSystem` pair is mirrored: `onEntityAdd` / `onEntityRemoved`.

### HolderSystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system`

Like `RefSystem`, but the callbacks receive the entity's `Holder` (blueprint) instead of a live `Ref` — `onEntityAdd` runs *before* the entity is inserted (you can still add/adjust components on the holder), and `onEntityRemoved` runs *after* removal with the removed entity's data.

```java
public abstract void onEntityAdd(Holder<ECS_TYPE> holder, AddReason reason, Store<ECS_TYPE> store)
public abstract void onEntityRemoved(Holder<ECS_TYPE> holder, RemoveReason reason, Store<ECS_TYPE> store)
public abstract Query<ECS_TYPE> getQuery()   // from QuerySystem
```

Reach for `HolderSystem` to guarantee an entity enters the store fully equipped (the engine uses it to ensure components exist on matching entities before any other system sees them). For a given entity, `HolderSystem.onEntityAdd` fires before `RefSystem.onEntityAdded`; on removal, `RefSystem.onEntityRemove` fires before `HolderSystem.onEntityRemoved`.

### StoreSystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system`

Callbacks tied to the *system's* lifecycle, not any entity's — fired when the system is attached to / detached from a `Store` (e.g. on registration, per world).

```java
public abstract void onSystemAddedToStore(Store<ECS_TYPE> store)
public abstract void onSystemRemovedFromStore(Store<ECS_TYPE> store)
```

Use it to initialize or clean up per-world state (seed a `Resource`, hook external services). It has no query and never iterates entities.

### DelayedSystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system`

A `TickingSystem` that only does work every `intervalSec` seconds instead of every tick. It accumulates delta time in an internal per-store resource and calls `delayedTick` once the interval elapses.

```java
public DelayedSystem(float intervalSec)
public float getIntervalSec()
public abstract void delayedTick(float dt, int systemIndex, Store<ECS_TYPE> store)
```

Use for periodic store-wide jobs (cleanup sweeps, notifications) that would be wasteful every tick. The `dt` passed to `delayedTick` is the **full accumulated time** since the last delayed tick (≥ `intervalSec`), not the per-tick delta — scale any rate-based math by it.

### DelayedEntitySystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system.tick`

`EntityTickingSystem` with the same interval gating as `DelayedSystem`: you implement the usual per-entity `tick(dt, index, chunk, store, buffer)` and `getQuery()`, but entities are only processed once per interval.

```java
public DelayedEntitySystem(float intervalSec)
public float getIntervalSec()
// then override EntityTickingSystem.tick(...) and getQuery() as usual
```

The interval is tracked store-wide (one hidden resource), so all matching entities are processed together in the same burst tick, each receiving the accumulated `dt`. The engine uses this for things like periodic sleep-state packets.

### WorldEventSystem<ECS_TYPE, EventType>
**Package:** `com.hypixel.hytale.component.system`

Handles world-level ECS events — events invoked on the store itself (`store.invoke(event)` / `buffer.invoke(event)`) rather than on a target entity. The counterpart of `EntityEventSystem` for events with no entity.

```java
protected WorldEventSystem(Class<EventType> eventType)
public abstract void handle(Store<ECS_TYPE> store, CommandBuffer<ECS_TYPE> buffer, EventType event)
```

The event class must be registered via `registerWorldEventType` (see [ComponentRegistry](#componentregistryecs_type)) and extend `EcsEvent`. Note the `handle` signature has no `index`/`ArchetypeChunk`/`Ref` — there is no target entity; use the `CommandBuffer` for any entity mutations.

### RunWhenPausedSystem<ECS_TYPE>
**Package:** `com.hypixel.hytale.component.system.tick`

Marker interface (no methods) extending `TickableSystem`. When a world is paused, the store's normal tick is replaced by a paused tick that runs **only** systems implementing this interface — everything else is skipped.

```java
public interface RunWhenPausedSystem<ECS_TYPE> extends TickableSystem<ECS_TYPE> { }
```

Implement it alongside a ticking base class if your system must keep running while the world is paused (the engine's chunk-saving and chunk-unloading systems do this). Ordinary gameplay systems should *not* implement it.

### DisableProcessingAssert
**Package:** `com.hypixel.hytale.component`

Marker interface (no methods). While a system implementing it is executing, the store suppresses its "is processing" assertion, permitting direct store operations that are normally asserted against during system execution.

```java
public interface DisableProcessingAssert { }
```

This is an escape hatch used by a handful of engine systems (e.g. block physics). For plugin code, prefer routing mutations through the `CommandBuffer` — it stays iteration-safe without disabling the guardrail.

---

## System Ordering (Dependencies)

**Package:** `com.hypixel.hytale.component.dependency`

Registered systems run in an order computed from declared dependencies. Override `getDependencies()` (a default method on `ISystem`) to constrain where your system runs relative to others:

```java
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;

public class MyFollowUpSystem extends EntityTickingSystem<EntityStore> {
    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
        Set.of(new SystemDependency<>(Order.AFTER, SomeOtherSystem.class));

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    // ... tick(...) and getQuery() as usual
}
```

### Dependency Types

`Dependency<ECS_TYPE>` is the abstract base — every dependency carries an `Order` (direction) and a priority (`getOrder()` / `getPriority()`). Three concrete forms cover plugin needs:

```java
// Run before/after another system class
SystemDependency(Order order, Class<T> systemClass)
SystemDependency(Order order, Class<T> systemClass, OrderPriority priority)

// Run before/after a SystemGroup (created via registry.registerSystemGroup())
SystemGroupDependency(Order order, SystemGroup<ECS_TYPE> group)
SystemGroupDependency(Order order, SystemGroup<ECS_TYPE> group, OrderPriority priority)

// Pin toward the absolute start/end of the system order
static <ECS_TYPE> RootDependency<ECS_TYPE> RootDependency.first()
static <ECS_TYPE> RootDependency<ECS_TYPE> RootDependency.last()
// Ready-made singleton sets for getDependencies():
static <ECS_TYPE> Set<Dependency<ECS_TYPE>> RootDependency.firstSet()
static <ECS_TYPE> Set<Dependency<ECS_TYPE>> RootDependency.lastSet()
```

### Order and OrderPriority

```java
public enum Order { BEFORE, AFTER }

public enum OrderPriority { CLOSEST, CLOSE, NORMAL, FURTHER, FURTHEST }
```

`Order` is the direction of the constraint; `OrderPriority` breaks ties when multiple systems declare the same relative order — `CLOSEST` sorts nearest to the anchor system, `FURTHEST` farthest. Constructors also accept a raw `int` priority; `OrderPriority.getValue()` exposes the underlying value.

> ⚠️ A `SystemDependency` on a system class that was never registered fails at sort time with
> `System dependency isn't registered:` (see [Gotchas](#gotchas--errors)) — register the anchor
> system before the dependent one.

### SystemType<ECS_TYPE, T>
**Package:** `com.hypixel.hytale.component`

Type descriptor for a registered system class — the system-side analogue of `ComponentType`. Obtained from `ComponentRegistry.registerSystemType(Class)`; key members are `getTypeClass()`, `isType(ISystem)`, `getIndex()`, and `getRegistry()`. The engine uses it to schedule whole categories of systems (ticking, run-when-paused), and `SystemTypeDependency` orders a system relative to *every* system of a type. Most plugins never need it directly — `SystemDependency` on a concrete class covers the common case.

---

## Spatial Queries (component.spatial)

**Package:** `com.hypixel.hytale.component.spatial`

The spatial package maintains per-world positional indexes so systems can answer "what's near this point?" without scanning every entity. The engine registers spatial systems for players, NPCs, items, and more; each one keeps a `SpatialResource` up to date every tick.

### SpatialSystem<ECS_TYPE>

Abstract `TickingSystem` that rebuilds a spatial index each tick from every entity matching `getQuery()`, using `getPosition` to extract each entity's position.

```java
public SpatialSystem(ResourceType<ECS_TYPE, SpatialResource<Ref<ECS_TYPE>, ECS_TYPE>> resourceType)
public abstract Vector3d getPosition(ArchetypeChunk<ECS_TYPE> chunk, int index)
public abstract Query<ECS_TYPE> getQuery()   // from QuerySystem
```

To publish your own index: register a `SpatialResource` as a resource, then register a `SpatialSystem` subclass pointing at its `ResourceType`. Consumers query through the resource, never the system.

### SpatialResource<T, ECS_TYPE>

The world-level `Resource` holding the index: a `SpatialData` buffer of positions plus the queryable `SpatialStructure`.

```java
public SpatialResource(SpatialStructure<T> spatialStructure)
public SpatialData<Ref<ECS_TYPE>> getSpatialData()
public SpatialStructure<T> getSpatialStructure()
public static <ECS_TYPE> List<Ref<ECS_TYPE>> getThreadLocalReferenceList()
```

`getThreadLocalReferenceList()` returns a reusable scratch list for query results (cleared on every call) — handy as the `results` argument to the `collect*` methods, but don't hold onto it across calls.

### SpatialStructure<T> / KDTree<T>

`SpatialStructure` is the query interface; `KDTree` is the standard implementation (its constructor takes a `Predicate<T>` filter applied to every collected result).

```java
int size()
void rebuild(SpatialData<T> data)

T closest(Vector3d position)                                     // nearest single entry
void collect(Vector3d center, double radius, List<T> results)    // sphere
void collectCylinder(Vector3d center, double radius, double height, List<T> results)
void collectBox(Vector3d min, Vector3d max, List<T> results)     // axis-aligned corners
void ordered(Vector3d center, double radius, List<T> results)    // sorted nearest-first
void ordered3DAxis(Vector3d center, double x, double y, double z, List<T> results)
```

Verified parameter semantics: `collectCylinder`'s `height` is the **total** height (halved internally around `center`), and `collectBox` takes **min/max corner** vectors, not center + extents. The `collect*` methods append to the list you pass without clearing it first.

```java
// Typical consumer: query an engine-maintained index
SpatialResource<Ref<EntityStore>, EntityStore> spatial = store.getResource(spatialResourceType);
List<Ref<EntityStore>> nearby = SpatialResource.getThreadLocalReferenceList();
spatial.getSpatialStructure().collect(position, 16.0, nearby);
```

> **Staleness:** the index is rebuilt by its owning `SpatialSystem` once per tick, so query results
> reflect positions as of the last rebuild — up to one tick old. Re-check live positions via
> `TransformComponent` if exactness matters.

### SpatialData<T>

The flat position + payload buffer a structure is rebuilt from — parallel arrays of `Vector3d` and data entries. Mostly internal plumbing; you only touch it when feeding a structure manually.

```java
int size()
void add(Vector3d position, T data)        // add, marks for sorting
void append(Vector3d position, T data)
void sort()
void sortMorton()                          // Morton-code (Z-order) sort
void clear()
Vector3d getVector(int index)
T getData(int index)
```

---

## UnknownComponents<ECS_TYPE>

**Package:** `com.hypixel.hytale.component.data.unknown`

Component that preserves the serialized data (raw BSON, keyed by component name) of component types the server couldn't resolve at load time — e.g. components written by a plugin that is no longer installed. Instead of dropping the data, deserialization parks it here so it round-trips through future saves.

```java
public static final String ID = "Unknown";
public boolean contains(String componentName)
public <T extends Component<ECS_TYPE>> T removeComponent(String componentName, Codec<T> codec)
public Map<String, BsonDocument> getUnknownComponents()
```

Plugin-facing use is niche but real: after re-installing a plugin (or renaming a component), you can recover previously "orphaned" data by pulling it out with `removeComponent(name, codec)` and re-attaching the deserialized component. Mostly, its existence explains why data from uninstalled plugins survives — deleting it requires explicitly clearing this component.

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
