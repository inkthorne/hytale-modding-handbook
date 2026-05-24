# Entities API

**Doc type:** Java API · **Verified against build-12**

This page covers the entity class tree (Entity, LivingEntity, Player), the lightweight `PlayerRef`, and the ECS components that hold entity state — stats, velocity, and interactions.

## Overview

Implemented in `com.hypixel.hytale.server.core.entity` (and related `modules` packages) and provides:
- An entity class hierarchy: `Entity` → `LivingEntity` → `Player`
- `PlayerRef`, a lightweight player handle for messaging, identity, and position
- `EntityStatMap` for reading and modifying entity stats (health, stamina, mana, etc.)
- `StatModifiersManager` for recalculating stats when modifiers change
- `Velocity` for applying forces and impulses to entities
- `InteractionManager` for entity interaction chains with trigger blocks
- Entity lifecycle events (`EntityEvent`, `EntityRemoveEvent`, `LivingEntityUseBlockEvent`)

## Architecture
```
Entity (ECS-backed entity + lifecycle)
├── PlayerRef            (lightweight handle: messaging / identity / position)
├── Player               (full component: permissions, inventory, UI managers)
│   ├── HudManager / PageManager / WindowManager / HotbarManager
│   └── Inventory
├── Stats
│   ├── EntityStatMap        (health, stamina, mana via DefaultEntityStatTypes)
│   └── StatModifiersManager (recalculation of stat modifiers)
├── Physics
│   └── Velocity             (forces / impulses via addInstruction)
├── InteractionManager   (interaction chains with trigger blocks)
└── Entity Events        (EntityEvent / EntityRemoveEvent / LivingEntityUseBlockEvent)
```

## Key Classes
| Class | Location | Description |
|-------|----------|-------------|
| `Entity` | `server.core.entity` | Base class for all entities; lifecycle and identity |
| `LivingEntity` | `server.core.entity` | Entities with health and inventory |
| `Player` | `server.core.entity.entities` | Full player entity with all game state |
| `PlayerRef` | `server.core.universe` | Lightweight player reference for messaging and identity |
| `EntityStatMap` | `server.core.modules.entitystats` | Component holding entity stats (health, mana, etc.) |
| `DefaultEntityStatTypes` | `server.core.modules.entitystats.asset` | Provides stat indices for common stats |
| `StatModifiersManager` | `server.core.entity` | Recalculates stat modifiers for living entities |
| `Velocity` | `server.core.modules.physics.component` | Component for applying forces/impulses |
| `VelocityConfig` | `server.core.modules.splitvelocity` | Configuration for velocity behavior |
| `ChangeVelocityType` | `protocol` | Enum for how velocity is applied (Add/Set) |
| `InteractionManager` | `server.core.entity` | Component managing entity interaction chains |
| `EntityEvent` | `server.core.event.events.entity` | Base entity lifecycle event |
| `EntityRemoveEvent` | `server.core.event.events.entity` | Fired when an entity is removed |
| `LivingEntityUseBlockEvent` | `server.core.event.events.entity` | Fired when a living entity uses a block (keyed by block type) |

## Class Hierarchy
```
Entity (abstract, implements Component<EntityStore>)
  └── LivingEntity (abstract)
        └── Player (implements CommandSender, PermissionHolder)

InteractionManager (component for interaction chains)
```

## PlayerRef
**Package:** `com.hypixel.hytale.server.core.universe`

Lightweight reference to a player, passed to commands. Use this for sending messages.

**Implements:** `Component<EntityStore>`, `MetricProvider`, `IMessageReceiver`

### Key Methods
```java
// Constructor
PlayerRef(Holder<EntityStore> holder, UUID uuid, String username, String language,
          PacketHandler handler, ChunkTracker tracker)

// Messaging
void sendMessage(Message msg)

// Identity
UUID getUuid()
String getUsername()
String getLanguage()
void setLanguage(String lang)

// Position
Transform getTransform()
UUID getWorldUuid()
Vector3f getHeadRotation()
void updatePosition(World world, Transform transform, Vector3f headRotation)

// References
boolean isValid()
Ref<EntityStore> getReference()
Holder<EntityStore> getHolder()
<T extends Component<EntityStore>> T getComponent(ComponentType<EntityStore, T> type)

// Network
PacketHandler getPacketHandler()
ChunkTracker getChunkTracker()
void referToServer(String host, int port)
void referToServer(String host, int port, byte[] data)

// Player Management
HiddenPlayersManager getHiddenPlayersManager()

// Lifecycle
Ref<EntityStore> addToStore(Store<EntityStore> store)
Holder<EntityStore> removeFromStore()

// Component type for ECS access
static ComponentType<EntityStore, PlayerRef> getComponentType()
```

## Player
**Package:** `com.hypixel.hytale.server.core.entity.entities`

Full player entity with all game state.

**Extends:** `LivingEntity`
**Implements:** `CommandSender`, `PermissionHolder`, `MetricProvider`

### Key Methods
```java
// Messaging & Permissions
void sendMessage(Message msg)
boolean hasPermission(String permission)
boolean hasPermission(String permission, boolean defaultValue)

// Identity
String getDisplayName()
PlayerRef getPlayerRef()
PacketHandler getPlayerConnection()

// Game State
GameMode getGameMode()
static void setGameMode(Ref<EntityStore> ref, GameMode mode, ComponentAccessor<EntityStore> accessor)
static void initGameMode(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)
boolean isFirstSpawn()
void setFirstSpawn(boolean firstSpawn)

// Inventory
Inventory getInventory()

// Position & Movement
void moveTo(Ref<EntityStore> ref, double x, double y, double z, ComponentAccessor<EntityStore> accessor)
void addLocationChange(Ref<EntityStore> ref, double x, double y, double z, ComponentAccessor<EntityStore> accessor)
static CompletableFuture<Transform> getRespawnPosition(Ref<EntityStore> ref, String spawnPoint, ComponentAccessor<EntityStore> accessor)
void applyMovementStates(Ref<EntityStore> ref, SavedMovementStates saved, MovementStates current, ComponentAccessor<EntityStore> accessor)
void resetVelocity(Velocity velocity)
void processVelocitySample(double deltaTime, Vector3d sample, Velocity velocity)

// Managers
WindowManager getWindowManager()
PageManager getPageManager()
HudManager getHudManager()
HotbarManager getHotbarManager()
WorldMapTracker getWorldMapTracker()

// View Distance
int getViewRadius()
int getClientViewRadius()
void setClientViewRadius(int radius)

// Spawn Protection
boolean hasSpawnProtection()
void setLastSpawnTimeNanos(long nanos)
long getSinceLastSpawnNanos()

// Mounting
int getMountEntityId()
void setMountEntityId(int id)

// Item Durability
ItemStackSlotTransaction updateItemStackDurability(Ref<EntityStore> ref, ItemStack stack, ItemContainer container, int slot, double amount, ComponentAccessor<EntityStore> accessor)

// Block Processing
void configTriggerBlockProcessing(boolean trigger, boolean process, CollisionResultComponent result)

// Persistence
CompletableFuture<Void> saveConfig(World world, Holder<EntityStore> holder)

// Connection State
boolean isWaitingForClientReady()

// Component type for ECS access
static ComponentType<EntityStore, Player> getComponentType()
```

## LivingEntity
**Package:** `com.hypixel.hytale.server.core.entity`

Base class for entities with health, inventory, etc.

### Key Methods
```java
// Inventory
Inventory getInventory()

// Movement
void moveTo(Ref<EntityStore> ref, double x, double y, double z, ComponentAccessor<EntityStore> accessor)
double getCurrentFallDistance()
void setCurrentFallDistance(double distance)

// Environment
boolean canBreathe(Ref<EntityStore> ref, BlockMaterial material, int fluidLevel, ComponentAccessor<EntityStore> accessor)
```

## Entity
**Package:** `com.hypixel.hytale.server.core.entity`

Base class for all entities.

### Key Methods
```java
// Lifecycle
boolean remove()
boolean wasRemoved()
void loadIntoWorld(World world)
void unloadFromWorld()
void markNeedsSave()

// Identity
int getNetworkId()
UUID getUuid()
void setLegacyUUID(UUID uuid)
String getLegacyDisplayName()

// Position
TransformComponent getTransformComponent()
void setTransformComponent(TransformComponent transform)
void moveTo(Ref<EntityStore> ref, double x, double y, double z, ComponentAccessor<EntityStore> accessor)
World getWorld()

// Collision
boolean isCollidable()

// ECS
void setReference(Ref<EntityStore> ref)
Ref<EntityStore> getReference()
void clearReference()
Holder<EntityStore> toHolder()
```

## PlayerRef vs Player: When to Use Each

Commands receive both `PlayerRef` and `Ref<EntityStore>`. Understanding when to use each is important:

### PlayerRef — Lightweight Reference

`PlayerRef` is a lightweight wrapper providing:
- **Messaging:** `sendMessage()`, `getLanguage()`
- **Identity:** `getUuid()`, `getUsername()`
- **Position:** `getTransform()`, `getWorldUuid()`
- **Network:** `getPacketHandler()`, `referToServer()`

Use `PlayerRef` when you only need these operations.

### Player — Full Component Access

`Player` is the full entity component with access to:
- **Permissions:** `hasPermission()`
- **Inventory:** `getInventory()`
- **Game State:** `getGameMode()`, `isFirstSpawn()`
- **UI Managers:** `getWindowManager()`, `getPageManager()`, `getHudManager()`, `getHotbarManager()`
- **Movement:** `moveTo()`, `resetVelocity()`

### Getting Player from PlayerRef

In commands, you receive `Ref<EntityStore>` which can access any component:

```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // PlayerRef is sufficient for messaging
    playerRef.sendMessage(Message.raw("Hello!"));

    // Get Player component for extended functionality
    Player player = store.getComponent(ref, Player.getComponentType());

    // Now you can access Player-specific features
    if (player.hasPermission("myplugin.admin")) {
        HudManager hud = player.getHudManager();
        Inventory inventory = player.getInventory();
        // ...
    }
}
```

### Quick Reference

| Need | Use | How |
|------|-----|-----|
| Send message | `PlayerRef` | `playerRef.sendMessage(msg)` |
| Get UUID/username | `PlayerRef` | `playerRef.getUuid()` |
| Get position | `PlayerRef` | `playerRef.getTransform()` |
| Check permissions | `Player` | `player.hasPermission(perm)` |
| Access inventory | `Player` | `player.getInventory()` |
| Manage HUD | `Player` | `player.getHudManager()` |
| Open pages/windows | `Player` | `player.getPageManager()`, `player.getWindowManager()` |

### Alternative: PlayerRef.getComponent()

`PlayerRef` also has a `getComponent()` method for convenience:

```java
// These are equivalent:
Player player = store.getComponent(ref, Player.getComponentType());
Player player = playerRef.getComponent(Player.getComponentType());
```

---

## Usage in Commands
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // Use playerRef for simple messaging
    playerRef.sendMessage(Message.raw("Hello!"));

    // Get full Player for more operations
    Player player = store.getComponent(ref, Player.getComponentType());
    player.hasPermission("myplugin.admin");

    // Get player position
    Transform transform = playerRef.getTransform();
}
```

---

## Built-in Entity Components

**Package:** `com.hypixel.hytale.server.core.modules.entity.component`

Beyond stats and velocity, the engine ships a set of ready-made `Component<EntityStore>` types that control an entity's **appearance and behaviour** — its model, display name, scale, lighting, interactability, and more. Attaching one of these to an entity's `Ref` is the standard way a plugin changes how an entity looks or acts.

Every class here follows the same ECS contract: a static `getComponentType()` returning its `ComponentType<EntityStore, …>`, used with the [Store component API](components.md#component-operations) (`addComponent` / `getComponent` / `putComponent`).

### Data components

These carry state and have getters/setters (and a constructor that seeds the value):

| Component | Holds | Key members |
|-----------|-------|-------------|
| `ModelComponent` | The entity's render model | `new ModelComponent(Model)`, `getModel()` |
| `PersistentModel` | A model that persists across reloads | `new PersistentModel(Model.ModelReference)`, `getModelReference()` / `setModelReference(...)` |
| `DisplayNameComponent` | Floating name | `new DisplayNameComponent(Message)`, `getDisplayName()` |
| `EntityScaleComponent` | Uniform render scale | `new EntityScaleComponent(float)`, `getScale()` / `setScale(float)` |
| `HeadRotation` | Head look direction | `new HeadRotation(Vector3f)`, `getRotation()` / `setRotation(...)`, `getDirection()` (→ `Vector3d`) |
| `DynamicLight` | Light emitted by the entity | `new DynamicLight(ColorLight)`, `getColorLight()` / `setColorLight(...)` |
| `PersistentDynamicLight` | Persisted dynamic light | `new PersistentDynamicLight(ColorLight)`, `getColorLight()` / `setColorLight(...)` |
| `BoundingBox` | Collision/selection box | `new BoundingBox(Box)`, `getBoundingBox()` / `setBoundingBox(...)`, `getDetailBoxes()` |
| `AudioComponent` | Looping sound-event ids on the entity | `getSoundEventIds()` (`int[]`), `addSound(int)` |
| `FromWorldGen` / `WorldGenId` | Tags an entity with its world-gen id | `new FromWorldGen(int)` / `new WorldGenId(int)`, `getWorldGenId()` |

### Marker / singleton components

These hold no per-entity state — presence alone is the signal. They expose a shared instance rather than a public constructor (`INSTANCE` or static `get()`):

| Component | Effect | Accessor |
|-----------|--------|----------|
| `Interactable` | Entity can be interacted with | `Interactable.INSTANCE` |
| `Intangible` | Entity ignores collision | `Intangible.INSTANCE` |
| `HiddenFromAdventurePlayers` | Hidden from players in Adventure mode | `HiddenFromAdventurePlayers.INSTANCE` |
| `NPCMarkerComponent` | Tags the entity as an NPC | `NPCMarkerComponent.get()` |
| `PropComponent` | Tags the entity as a static prop | `PropComponent.get()` |

### Usage

```java
// Give an entity a custom render model and a floating name.
store.addComponent(ref, ModelComponent.getComponentType(), new ModelComponent(model));
store.addComponent(ref, DisplayNameComponent.getComponentType(),
        new DisplayNameComponent(Message.raw("Shopkeeper")));

// Scale it up and make it non-colliding (marker component via its shared instance).
store.addComponent(ref, EntityScaleComponent.getComponentType(), new EntityScaleComponent(1.5f));
store.addComponent(ref, Intangible.getComponentType(), Intangible.INSTANCE);

// Read a component back.
ModelComponent mc = store.getComponent(ref, ModelComponent.getComponentType());
```

> [!NOTE]
> Components ending in `consumeNetworkOutdated()` (e.g. `ModelComponent`, `EntityScaleComponent`, `DynamicLight`, `AudioComponent`) are network-synced: mutating them marks the entity dirty so the change is pushed to clients on the next tick. The `Persistent*` variants additionally survive save/reload.

---

## Entity Stats (EntityStatMap)

Component that holds entity stats like health, stamina, mana, etc.

**Package:** `com.hypixel.hytale.server.core.modules.entitystats`

### Getting the Component

```java
EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
```

### DefaultEntityStatTypes

**Package:** `com.hypixel.hytale.server.core.modules.entitystats.asset`

Provides stat indices for common stats:

```java
int healthIndex = DefaultEntityStatTypes.getHealth();
int oxygenIndex = DefaultEntityStatTypes.getOxygen();
int staminaIndex = DefaultEntityStatTypes.getStamina();
int manaIndex = DefaultEntityStatTypes.getMana();
int signatureIndex = DefaultEntityStatTypes.getSignatureEnergy();
int ammoIndex = DefaultEntityStatTypes.getAmmo();
```

### Modifying Stats

```java
EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
int healthIndex = DefaultEntityStatTypes.getHealth();

// Modify stat values
stats.subtractStatValue(healthIndex, 5.0f);   // Subtract 5 health
stats.addStatValue(healthIndex, 10.0f);       // Add 10 health
stats.setStatValue(healthIndex, 100.0f);      // Set to 100
stats.maximizeStatValue(healthIndex);         // Set to max
stats.minimizeStatValue(healthIndex);         // Set to min (usually 0)
```

### Reading Stat Values

```java
EntityStatValue healthStat = stats.get(healthIndex);
float currentHealth = healthStat.get();
float maxHealth = healthStat.getMax();
float minHealth = healthStat.getMin();
```

### Example: Damage Player on Hit

```java
// In a damage event handler, subtract health from attacker
if (source instanceof Damage.EntitySource entitySource) {
    Ref<EntityStore> attackerRef = entitySource.getRef();
    EntityStatMap stats = store.getComponent(attackerRef, EntityStatMap.getComponentType());
    if (stats != null) {
        int healthIndex = DefaultEntityStatTypes.getHealth();
        stats.subtractStatValue(healthIndex, 5.0f);
    }
}
```

---

## StatModifiersManager
**Package:** `com.hypixel.hytale.server.core.entity`

Manages stat modifiers for living entities. Used to recalculate entity stats when equipment, buffs, or other modifiers change.

### Getting the Manager
```java
EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
StatModifiersManager manager = stats.getStatModifiersManager();
```

### Methods
```java
// Schedule stat recalculation
void scheduleRecalculate()

// Queue specific stats to be cleared before recalculation
void queueEntityStatsToClear(int[] statIndices)

// Recalculate all stat modifiers for an entity
void recalculateEntityStatModifiers(
    Ref<EntityStore> ref,
    EntityStatMap stats,
    ComponentAccessor<EntityStore> accessor
)
```

### Usage Example
```java
// Force recalculation of entity stats after changing equipment
EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
if (stats != null) {
    StatModifiersManager manager = stats.getStatModifiersManager();
    manager.scheduleRecalculate();

    manager.recalculateEntityStatModifiers(ref, stats, store);
}
```

---

## Velocity API

Component for applying forces and impulses to entities.

**Package:** `com.hypixel.hytale.server.core.modules.physics.component`

### Getting the Component

```java
Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
```

Or when you have a chunk index:
```java
Velocity velocity = chunk.getComponent(index, Velocity.getComponentType());
```

### Important: Player vs NPC Velocity

Players are **client-authoritative** for movement. The server cannot directly modify player velocity - changes must be synchronized to the client via the instruction system.

| Method | Use Case | Client Sync |
|--------|----------|-------------|
| `addForce(x,y,z)` | Server-side physics (untested) | No |
| `set(x,y,z)` | Server-side physics (untested) | No |
| `addInstruction(...)` | **All entities** (players + NPCs) | Yes |

### Applying Velocity to Players

Use `addInstruction()` for players - this queues velocity changes that get synchronized to the client:

```java
Velocity velocity = chunk.getComponent(index, Velocity.getComponentType());
if (velocity != null) {
    Vector3d impulse = new Vector3d(0.0, 15.0, 0.0);  // Upward impulse
    VelocityConfig config = new VelocityConfig();
    velocity.addInstruction(impulse, config, ChangeVelocityType.Add);
}
```

### VelocityConfig

**Package:** `com.hypixel.hytale.server.core.modules.splitvelocity`

Configuration for velocity behavior. Default constructor provides standard physics behavior.

### ChangeVelocityType

**Package:** `com.hypixel.hytale.protocol`

Enum controlling how velocity is applied:
- `Add` - Add to current velocity
- `Set` - Replace current velocity

### Applying Velocity to NPCs/Entities

For NPCs and creatures, `addInstruction()` works the same as for players:

```java
Velocity velocity = chunk.getComponent(index, Velocity.getComponentType());
if (velocity != null) {
    Vector3d impulse = new Vector3d(0.0, 15.0, 0.0);
    VelocityConfig config = new VelocityConfig();
    velocity.addInstruction(impulse, config, ChangeVelocityType.Add);
}
```

Note: `addForce()` and `set()` exist but haven't been verified to work.

### Example: Launch Player Upward

```java
public void launchPlayer(Store<EntityStore> store, Ref<EntityStore> ref) {
    Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
    if (velocity != null) {
        Vector3d impulse = new Vector3d(0.0, 20.0, 0.0);
        VelocityConfig config = new VelocityConfig();
        velocity.addInstruction(impulse, config, ChangeVelocityType.Add);
    }
}
```

### Example: Knockback from Damage

```java
// In a damage system, apply knockback to the damaged entity
public void applyKnockback(Velocity velocity, Vector3d direction, double force) {
    Vector3d knockback = new Vector3d(
        direction.getX() * force,
        5.0,  // Small upward component
        direction.getZ() * force
    );
    VelocityConfig config = new VelocityConfig();
    velocity.addInstruction(knockback, config, ChangeVelocityType.Add);
}
```

> **See also:** For the component-based knockback system with automatic duration management and resistance modifiers, see [KnockbackComponent in combat.md](combat.md#knockback-system).

---

## InteractionManager

**Package:** `com.hypixel.hytale.server.core.entity`

Component for managing entity interaction chains. Used with trigger blocks to execute interaction sequences when entities enter or contact special blocks.

### Tick & Lifecycle
```java
void tick(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer, float deltaTime)   // Process pending interactions
void clear()  // Clear all interaction chains
```

### Chain Management
```java
// Start a new interaction chain
boolean tryStartChain(...)

// Execute pending chains
void executeChain(...)

// Cancel active chains
void cancelChains(InteractionChain chain)
```

### Query
```java
// Check if a chain can run
boolean canRun(...)

// Get active chains
Int2ObjectMap<InteractionChain> getChains()
```

### Rules
```java
// Apply interaction rules
void applyRules(...)
```

### Usage with CollisionResult

The `InteractionManager` is used when processing trigger blocks:

```java
CollisionResult result = new CollisionResult(false, true);  // Enable triggers
module.findIntersections(world, hitbox, position, result, true, false);

// Process triggers with interaction manager
InteractionManager manager = store.getComponent(ref, InteractionManager.getComponentType());
result.defaultTriggerBlocksProcessing(manager, entity, ref, flag, accessor);
```

---

## Entity Events

**Package:** `com.hypixel.hytale.server.core.event.events.entity`

Events related to entity lifecycle. For inventory-related events (`InventoryChangeEvent`, `DropItemEvent`, `SwitchActiveSlotEvent`, `InteractivelyPickupItemEvent`), see [inventory.md](inventory.md#inventory-events).

### Event Summary

| Class | Description |
|-------|-------------|
| `EntityEvent` | Base entity event |
| `EntityRemoveEvent` | Entity is removed |
| `LivingEntityUseBlockEvent` | Living entity uses a block (keyed by block type) |

---

### EntityEvent

**Package:** `com.hypixel.hytale.server.core.event.events.entity`

Base class for entity-related events.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getEntity()` | `Entity` | The entity this event relates to |

---

### EntityRemoveEvent

**Package:** `com.hypixel.hytale.server.core.event.events.entity`

Fired when an entity is removed from the world.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getEntity()` | `Entity` | The entity being removed |

---

### LivingEntityUseBlockEvent

**Package:** `com.hypixel.hytale.server.core.event.events.entity`

Fired when a living entity uses/interacts with a block. Implements `IEvent<String>` (keyed by block type).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getBlockType()` | `String` | The block type being used |
| `getRef()` | `Ref<EntityStore>` | Entity reference |

### Usage Example

Since this is a keyed event (keyed by block type String), use `registerGlobal()` to catch all block uses:

```java
import com.hypixel.hytale.server.core.event.events.entity.LivingEntityUseBlockEvent;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;

@Override
protected void setup() {
    // Listen for all block uses
    getEventRegistry().registerGlobal(LivingEntityUseBlockEvent.class, event -> {
        var ref = event.getRef();
        String blockType = event.getBlockType();
        System.out.println("Entity used block: " + blockType);
    });

    // Or listen for a specific block type
    getEventRegistry().register(LivingEntityUseBlockEvent.class, "Bench_Builders", event -> {
        System.out.println("Entity used crafting bench!");
    });
}
```

---

### Entity Events Usage Example

```java
import com.hypixel.hytale.server.core.event.events.entity.EntityRemoveEvent;

@Override
protected void setup() {
    // Listen for entity removals
    getEventRegistry().registerGlobal(EntityRemoveEvent.class, event -> {
        var entity = event.getEntity();
        System.out.println("Entity removed: " + entity);
    });
}
```

### ECS Inventory Events

For ECS inventory events like `SwitchActiveSlotEvent` and `DropItemEvent`, see the [Inventory Events section in inventory.md](inventory.md#inventory-events).

See [events.md](events.md) for general `EntityEventSystem` usage patterns.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 entity subsystem (verified against `HytaleServer.jar`).

- **`No EntityStatType found for index`** → an `EntityStatMap` call was given a stat index that no registered stat type maps to (e.g. a hardcoded/stale integer). Fix: obtain indices from `DefaultEntityStatTypes` (`getHealth()`, `getStamina()`, ...) rather than literals.
- **Symptom:** server-side `velocity.addForce(...)`/`velocity.set(...)` appear to do nothing on players → players are client-authoritative for movement, so direct velocity writes are not synchronized. Fix: use `velocity.addInstruction(impulse, config, ChangeVelocityType.Add)`, which queues a client-synced change (see [Player vs NPC Velocity](#important-player-vs-npc-velocity)).
- **Symptom:** `store.getComponent(ref, Player.getComponentType())` returns `null` for a command sender → the entity isn't a full `Player` (or you used the wrong ref). Fix: for messaging/identity use the `PlayerRef` you were handed; only fetch the `Player` component when you need permissions/inventory/UI, and null-check it.
- **Symptom:** a `LivingEntityUseBlockEvent` handler never fires for a specific block → the event is keyed by block-type string, so `register(LivingEntityUseBlockEvent.class, "Bench_Builders", ...)` only matches that exact key. Fix: use `registerGlobal(...)` to catch all block uses, or pass the precise block-type key.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
