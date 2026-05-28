---
title: "Projectiles API"
description: "Spawn and manage Hytale projectiles in Java — the ProjectileModule, asset-based ProjectileConfig for ballistics and visuals, physics via PhysicsConfig, and projectile interactions."
seo:
  type: TechArticle
---

# Projectiles API

**Doc type:** Java API · **Verified against 0.5.2**

This page covers spawning and simulating projectiles: the module, asset-based configuration, physics, ECS components, and impact/bounce callbacks.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.projectile` (and its `config`, `component`, and `interaction` subpackages) and provides:
- `ProjectileModule` for spawning and managing projectiles
- `ProjectileConfig`, asset-based ballistic and visual configuration
- Physics via `PhysicsConfig` / `StandardPhysicsConfig` and `StandardPhysicsProvider`
- ECS components: `Projectile` and `PredictedProjectile` (client prediction)
- `ImpactConsumer` / `BounceConsumer` callbacks for impacts and bounces
- `ProjectileInteraction` for launching projectiles from interactions

## Architecture
```
ProjectileModule  (spawnProjectile, component-type accessors)
├── ProjectileConfig        (asset: ballistic data, spawn offset, model, sounds)
│   └── BallisticData        (muzzle velocity, gravity, shot adjustments)
├── Physics
│   ├── PhysicsConfig → StandardPhysicsConfig  (bounce, rolling, fluid)
│   └── StandardPhysicsProvider (per-tick simulation, collision, fluid state)
├── Components
│   ├── Projectile           (marks entity as a projectile)
│   └── PredictedProjectile  (client-side prediction by UUID)
├── Callbacks
│   ├── ImpactConsumer
│   └── BounceConsumer
└── ProjectileInteraction   (launches projectiles, provides BallisticData)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `ProjectileModule` | `modules.projectile` | Spawns and manages projectiles |
| `ProjectileConfig` | `modules.projectile.config` | Asset-based projectile configuration |
| `BallisticData` | `modules.projectile.config` | Interface for ballistic properties |
| `PhysicsConfig` | `modules.projectile.config` | Interface for projectile physics behavior |
| `StandardPhysicsConfig` | `modules.projectile.config` | Default physics implementation (bounce, fluid, rolling) |
| `StandardPhysicsProvider` | `modules.projectile.config` | ECS component running physics simulation |
| `ImpactConsumer` | `modules.projectile.config` | Callback for projectile impacts |
| `BounceConsumer` | `modules.projectile.config` | Callback for projectile bounces |
| `BallisticDataProvider` | `modules.projectile.config` | Interface for types providing ballistic data |
| `Projectile` | `modules.projectile.component` | ECS component marking an entity as a projectile |
| `PredictedProjectile` | `modules.projectile.component` | ECS component for client-side prediction |
| `ProjectileInteraction` | `modules.projectile.interaction` | Interaction that launches projectiles |

## Class Hierarchy
```
ProjectileConfig (asset-based configuration)
  implements JsonAssetWithMap, NetworkSerializable, BallisticData

PhysicsConfig (interface)
  └── StandardPhysicsConfig (default implementation)

Projectile (ECS component)
  implements Component<EntityStore>

ProjectileInteraction
  extends SimpleInstantInteraction
  implements BallisticDataProvider
```

## Two Projectile Schemas (Simple vs Config)

Two different JSON asset trees both produce projectiles, but only one can run interactions on impact.
Pick based on whether you need on-hit logic (effects, AOE, despawn handling).

| | **Simple** (`Server/Projectiles/*.json`) | **Config** (`Server/ProjectileConfigs/*.json`) |
|---|---|---|
| Maps to | (native projectile asset) | `ProjectileConfig` |
| Damage | top-level `Damage` (int) | via an on-hit `DamageEntity` interaction |
| Physics | flat fields (`MuzzleVelocity`, `Gravity`, `Bounciness`, `TimeToLive`, …) | typed `Physics` object (`"Type": "Standard"`, …) + `LaunchForce`, `SpawnOffset` |
| Particles/despawn | native (`HitParticles`, `MissParticles`, `TimeToLive`, `DeadTime`) — "just work", world-oriented | **none native** — you spawn particles and despawn from interactions |
| Interactions | **none** | **`Interactions`** (`ProjectileSpawn` / `ProjectileHit` / `ProjectileMiss`) |
| Launched via | the `LaunchProjectile` interaction (only field `projectileId` — no on-hit hook) | `{ "Type": "Projectile", "Config": "<id>" }` |

Only the **config** schema can run interactions, so it's the one you need to apply effects, AOE, or
custom on-hit logic. Hit routing: a **terrain/wall** hit fires **`ProjectileMiss`**; a **direct entity**
hit fires **`ProjectileHit`** (confirmed in vanilla `Projectile_Config_Ice_Ball`, which restates both).

### Gotchas authoring config-projectile `Interactions`

- **`Interactions` is a `Map<InteractionType, String>`, not a nested object** — so on a `Parent`-inheriting
  config, providing `Interactions` **replaces the whole handler map** rather than merging per-handler.
  (The [`Parent` deep-merge](codecs.md#parent-inheritance-inheritcodec) recurses only for nested
  `BuilderCodec` objects; a `Map` container, like an array, is replaced wholesale.) Restate **every**
  handler you want — omit `ProjectileMiss` and terrain hits never despawn, so the projectile sticks in
  the wall forever.
- **No native `TimeToLive`** on config projectiles — they despawn via a `RemoveEntity` interaction.
  Put a `{ "Type": "Simple", "RunTime": 0.2 }` (or `RunTime: 0`) **before** `RemoveEntity` so impact
  effects dispatch before the entity is destroyed — the pattern vanilla `Projectile_Config_Ice_Ball`
  uses in both its `ProjectileHit` and `ProjectileMiss`.

## ProjectileModule
**Package:** `com.hypixel.hytale.server.core.modules.projectile`

Main module for spawning and managing projectiles.

### Getting the Module
```java
ProjectileModule module = ProjectileModule.get();
```

### Key Methods
```java
// Spawn a projectile
Ref<EntityStore> spawnProjectile(
    Ref<EntityStore> shooter,
    CommandBuffer<EntityStore> commandBuffer,
    ProjectileConfig config,
    Vector3d position,
    Vector3d velocity
)

// Spawn with custom UUID
Ref<EntityStore> spawnProjectile(
    UUID uuid,
    Ref<EntityStore> shooter,
    CommandBuffer<EntityStore> commandBuffer,
    ProjectileConfig config,
    Vector3d position,
    Vector3d velocity
)

// Get component types
ComponentType<EntityStore, Projectile> getProjectileComponentType()
ComponentType<EntityStore, StandardPhysicsProvider> getStandardPhysicsProviderComponentType()
ComponentType<EntityStore, PredictedProjectile> getPredictedProjectileComponentType()
```

> **See also:** [ECS Components](components.md#core-types)

---

## ProjectileConfig
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Asset-based configuration for projectile behavior.

**Implements:** `JsonAssetWithMap`, `NetworkSerializable<ProjectileConfig>`, `BallisticData`

### Getting Configs from Assets
```java
// Get the asset store
AssetStore<String, ProjectileConfig, DefaultAssetMap<String, ProjectileConfig>> store =
    ProjectileConfig.getAssetStore();

// Get the asset map
DefaultAssetMap<String, ProjectileConfig> map = ProjectileConfig.getAssetMap();
```

### Key Methods
```java
// Identity
String getId()

// Ballistic properties
double getLaunchForce()
double getMuzzleVelocity()
double getGravity()
double getVerticalCenterShot()
double getDepthShot()
boolean isPitchAdjustShot()

// Spawn positioning
Vector3f getSpawnOffset()
Direction getSpawnRotationOffset()
Vector3d getCalculatedOffset(float yaw, float pitch)

// Physics behavior
PhysicsConfig getPhysicsConfig()

// Visuals
Model getModel()

// Sound events
int getLaunchWorldSoundEventIndex()
int getProjectileSoundEventIndex()

// Interactions
Map<InteractionType, String> getInteractions()
```

---

## BallisticData
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Interface for ballistic properties.

### Methods
```java
double getMuzzleVelocity()    // Initial projectile speed
double getGravity()           // Gravity multiplier
double getVerticalCenterShot() // Vertical offset for aiming
double getDepthShot()         // Forward offset for spawn
boolean isPitchAdjustShot()   // Whether to adjust pitch for trajectory
```

---

## PhysicsConfig
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Interface for projectile physics behavior.

### Methods
```java
// Apply physics to a projectile entity
void apply(
    Holder<EntityStore> holder,
    Ref<EntityStore> ref,
    Vector3d position,
    ComponentAccessor<EntityStore> accessor,
    boolean flag
)

// Get gravity (default implementation available)
double getGravity()
```

---

## StandardPhysicsConfig
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Default physics implementation for projectiles.

**Implements:** `PhysicsConfig`

### Constants
```java
static final StandardPhysicsConfig DEFAULT  // Default physics config
```

### Key Methods
```java
// Gravity
double getGravity()

// Bouncing
double getBounciness()        // How much velocity is retained on bounce (0-1)
int getBounceCount()          // Maximum number of bounces
double getBounceLimit()       // Minimum velocity to continue bouncing

// Surface behavior
boolean isSticksVertically()  // Whether projectile sticks to vertical surfaces
boolean isAllowRolling()      // Whether projectile can roll on surfaces
double getRollingFrictionFactor()  // Friction when rolling

// Water interaction
double getSwimmingDampingFactor()  // Velocity damping in water
double getHitWaterImpulseLoss()    // Velocity loss when entering water

// Physics application
void apply(
    Holder<EntityStore> holder,
    Ref<EntityStore> ref,
    Vector3d position,
    ComponentAccessor<EntityStore> accessor,
    boolean flag
)
```

---

## ImpactConsumer
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Callback interface for handling projectile impacts.

### Method
```java
void onImpact(
    Ref<EntityStore> projectileRef,    // The projectile entity
    Vector3d impactPosition,           // Where it hit
    Ref<EntityStore> targetRef,        // Entity that was hit (if any)
    String interactionId,              // Interaction identifier
    CommandBuffer<EntityStore> buffer  // Command buffer for responses
)
```

---

## BounceConsumer
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Callback interface for handling projectile bounces.

### Method
```java
void onBounce(
    Ref<EntityStore> projectileRef,    // The projectile entity
    Vector3d bouncePosition,           // Where it bounced
    CommandBuffer<EntityStore> buffer  // Command buffer for responses
)
```

---

## BallisticDataProvider
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Interface for types that provide ballistic data.

### Method
```java
BallisticData getBallisticData()  // Get the ballistic properties
```

### Implementations
- `ProjectileInteraction` - Provides ballistic data from its config

---

## Projectile Component
**Package:** `com.hypixel.hytale.server.core.modules.projectile.component`

ECS component marking an entity as a projectile.

**Implements:** `Component<EntityStore>`

### Getting the Component
```java
ComponentType<EntityStore, Projectile> type = Projectile.getComponentType();
Projectile projectile = store.getComponent(ref, type);
```

---

## PredictedProjectile
**Package:** `com.hypixel.hytale.server.core.modules.projectile.component`

ECS component for client-side projectile prediction. Links a predicted projectile to its UUID.

**Implements:** `Component<EntityStore>`

### Getting the Component
```java
ComponentType<EntityStore, PredictedProjectile> type = PredictedProjectile.getComponentType();
// Or via ProjectileModule
ComponentType<EntityStore, PredictedProjectile> type =
    ProjectileModule.get().getPredictedProjectileComponentType();
```

### Methods
```java
// Constructor
PredictedProjectile(UUID uuid)

// Get the prediction UUID
UUID getUuid()

// Clone for ECS
Component<EntityStore> clone()
```

### Usage Example
```java
// Check if a projectile has prediction
PredictedProjectile predicted = store.getComponent(ref, PredictedProjectile.getComponentType());
if (predicted != null) {
    UUID predictionId = predicted.getUuid();
    // This projectile is being predicted on the client
}
```

---

## StandardPhysicsProvider
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

ECS component that provides physics simulation for projectiles. Handles collision, bouncing, rolling, and fluid interaction.

**Implements:** `Component<EntityStore>`, `IBlockCollisionConsumer`

### Getting the Component
```java
ComponentType<EntityStore, StandardPhysicsProvider> type = StandardPhysicsProvider.getComponentType();
// Or via ProjectileModule
ComponentType<EntityStore, StandardPhysicsProvider> type =
    ProjectileModule.get().getStandardPhysicsProviderComponentType();
```

### Constants
```java
static final int WATER_DETECTION_EXTREMA_COUNT;  // Samples for water detection
static final double MIN_BOUNCE_EPSILON;          // Minimum bounce velocity
static final double MIN_BOUNCE_EPSILON_SQUARED;  // Squared minimum
```

### State Enum
```java
StandardPhysicsProvider.STATE getState()
void setState(StandardPhysicsProvider.STATE state)
```

### Physics Configuration
```java
StandardPhysicsConfig getPhysicsConfig()
```

### Position and Movement
```java
Vector3d getPosition()
Vector3d getVelocity()
Vector3d getMovement()           // Current tick movement
Vector3d getNextMovement()       // Next tick planned movement
```

### Ground and Fluid State
```java
boolean isOnGround()
void setOnGround(boolean onGround)
boolean isSwimming()
boolean isInFluid()
void setInFluid(boolean inFluid)
double getDragCoefficient(double value)
```

### Bounce Tracking
```java
boolean isBounced()
void setBounced(boolean bounced)
int getBounces()
void incrementBounces()
```

### Collision Data
```java
double getCollisionStart()
void setCollisionStart(double start)
Vector3d getContactPosition()
Vector3d getContactNormal()
boolean isSliding()
void setSliding(boolean sliding)
```

### Fluid Interaction
```java
double getDisplacedMass()
void setDisplacedMass(double mass)
double getSubSurfaceVolume()
void setSubSurfaceVolume(double volume)
double getEnterFluid()
void setEnterFluid(double value)
double getLeaveFluid()
void setLeaveFluid(double value)
```

### Collision Providers
```java
BlockCollisionProvider getBlockCollisionProvider()
EntityRefCollisionProvider getEntityCollisionProvider()
BlockTracker getTriggerTracker()
BlockTracker getFluidTracker()
```

### Physics State
```java
ForceProviderEntity getForceProviderEntity()
ForceProvider[] getForceProviders()
ForceProviderStandardState getForceProviderStandardState()
PhysicsBodyStateUpdater getStateUpdater()
PhysicsBodyState getStateBefore()
PhysicsBodyState getStateAfter()
RestingSupport getRestingSupport()
```

### Callbacks
```java
ImpactConsumer getImpactConsumer()
BounceConsumer getBounceConsumer()
```

### World and Entity
```java
void setWorld(World world)
UUID getCreatorUuid()
boolean isProvidesCharacterCollisions()
```

### Collision Handling (IBlockCollisionConsumer)
```java
Result onCollision(int x, int y, int z, Vector3d velocity, BlockContactData contact,
                   BlockData block, Box box)
Result probeCollisionDamage(int x, int y, int z, Vector3d velocity,
                            BlockContactData contact, BlockData block)
void onCollisionDamage(int x, int y, int z, Vector3d velocity,
                       BlockContactData contact, BlockData block)
Result onCollisionSliceFinished()
void onCollisionFinished()
```

> **See also:** [Collision API](collision.md#collisionresult)

### Tick Methods
```java
void finishTick(TransformComponent transform, Velocity velocity)
void rotateBody(double angle, Vector3f axis)
```

### Usage Example
```java
// Get physics provider from a projectile
StandardPhysicsProvider physics = store.getComponent(ref,
    StandardPhysicsProvider.getComponentType());

if (physics != null) {
    // Check state
    if (physics.isOnGround()) {
        // Projectile has landed
    }

    // Check bounces
    int bounceCount = physics.getBounces();
    StandardPhysicsConfig config = physics.getPhysicsConfig();
    if (bounceCount >= config.getBounceCount()) {
        // Max bounces reached
    }

    // Get velocity
    Vector3d vel = physics.getVelocity();
}
```

> **See also:** [Math API](math.md#vector3d)

---

## ProjectileInteraction
**Package:** `com.hypixel.hytale.server.core.modules.projectile.interaction`

Interaction that launches projectiles when triggered.

**Extends:** `SimpleInstantInteraction`
**Implements:** `BallisticDataProvider`

### Key Methods
```java
ProjectileConfig getConfig()           // Get the projectile config
BallisticData getBallisticData()       // Get ballistic properties
WaitForDataFrom getWaitForDataFrom()   // Client/server data sync mode
boolean needsRemoteSync()              // Whether to sync across network
```

---

## Usage Examples

### Spawning a Projectile
```java
ProjectileModule module = ProjectileModule.get();

// Get projectile config from assets
ProjectileConfig config = ProjectileConfig.getAssetMap().get("arrow");

// Calculate spawn position and velocity
Vector3d spawnPos = new Vector3d(x, y, z);
Vector3d velocity = new Vector3d(dirX * config.getMuzzleVelocity(),
                                  dirY * config.getMuzzleVelocity(),
                                  dirZ * config.getMuzzleVelocity());

// Spawn the projectile
Ref<EntityStore> projectileRef = module.spawnProjectile(
    shooterRef,
    commandBuffer,
    config,
    spawnPos,
    velocity
);
```

### Checking if Entity is a Projectile
```java
Projectile projectileComp = store.getComponent(ref, Projectile.getComponentType());
if (projectileComp != null) {
    // Entity is a projectile
}
```

---

## Spawning Particles from Java

To spawn a particle effect at an arbitrary world position from code (e.g. a world-oriented impact
burst that fires consistently on **both** direct hits and terrain misses), use
`com.hypixel.hytale.server.core.universe.world.ParticleUtil`. It has many `spawnParticleEffect`
overloads; the general one:

```java
ParticleUtil.spawnParticleEffect(
    String systemId, Vector3d pos,
    float pitch, float yaw, float roll,   // ROTATION IN RADIANS — (0,0,0) = world-aligned
    float scale, float duration,
    ComponentAccessor<EntityStore> accessor);   // a CommandBuffer works here
```

The three rotation floats are pitch/yaw/roll in **radians** (the `PlayVfxEffect` trigger calls this
after `Math.toRadians(...)` on its degree fields). Simpler overloads exist —
`spawnParticleEffect(String, Vector3d, ComponentAccessor)`,
`spawnParticleEffect(WorldParticle, Vector3d, ...)`, and `Rotation3f`/`List<Ref>`/`Color` variants.

Spawning from code with rotation `(0,0,0)` is how you get an **untilted, world-oriented** impact
effect. A `ModelParticle` placed in JSON attaches to an `EntityPart` (`Self`, `Entity`, `PrimaryItem`,
or `SecondaryItem` — there is **no world-space anchor**) and inherits that entity's transform, so a
particle on a pitched projectile tilts with the shot — a flat ground decal looks wrong. `DetachedFromModel: true`
only makes the system *persist* after the entity despawns; it does **not** change spawn orientation.
For a world-oriented effect, use a `WorldParticle` (only available via `DamageEffects`, i.e. entity
hits) or spawn from code with rotation `(0,0,0)`. As with JSON particles, pass a non-zero `scale` —
the field is a primitive `float` and `0` renders invisibly.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 projectile subsystem (verified against `HytaleServer.jar`).

- **`has no valid ProjectileConfig`** → an entity/interaction tried to launch a projectile whose `ProjectileConfig` could not be resolved. Fix: pass a config obtained from `ProjectileConfig.getAssetMap().get(id)` and verify the id exists.
- **`No projectile config typeName provided`** → a `ProjectileInteraction` (or launch config) omitted the projectile config type name. Fix: set the projectile config reference in the interaction JSON.
- **Symptom:** `ProjectileConfig.getAssetMap().get("arrow")` returns `null` → the asset id didn't match (ids are case-sensitive). Fix: use the exact asset-file id and null-check before spawning.
- **Symptom:** a projectile bounces forever or never stops → bounce limits come from `StandardPhysicsConfig`. Fix: compare `physics.getBounces()` against `config.getBounceCount()` and check `getBounceLimit()`/`getBounciness()` (see [StandardPhysicsProvider](#standardphysicsprovider)).
- **Symptom:** an `AOECircle`/`AOECylinder` selector in a projectile's `ProjectileHit`/`ProjectileMiss` affects only the directly-hit entity, never a radius → projectile-hosted selectors don't sweep (unlike melee). Fix: use `Type: "Explode"`, a trigger volume, or the Java radius query `Selector.selectNearbyEntities(...)` (see [interactions-combat.md → AOECircle](interactions-combat.md#aoecircle-area-of-effect)).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
