---
title: "Projectiles API"
description: "Spawn and manage Hytale projectiles in Java — the ProjectileModule, asset-based ProjectileConfig for ballistics and visuals, physics via PhysicsConfig, and projectile interactions."
seo:
  type: TechArticle
---

# Projectiles API

**Doc type:** Java API · **Verified against 0.7.2**

This page covers spawning and simulating projectiles: the module, asset-based configuration, physics, ECS components, and impact/bounce callbacks.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.projectile` (and its `config`, `component`, and `interaction` subpackages) and provides:
- `ProjectileModule` for spawning and managing projectiles
- `ProjectileConfig`, asset-based ballistic and visual configuration
- Physics via `PhysicsConfig` / `StandardPhysicsConfig` (and its 0.7.2 subclass `GroundFollowPhysicsConfig`) and `StandardPhysicsProvider`
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
│   │                    └── GroundFollowPhysicsConfig  (0.7.2+: terrain following)
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
| `GroundFollowPhysicsConfig` | `modules.projectile.config` | 0.7.2+: `Standard` physics that follows the terrain |
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
  └── StandardPhysicsConfig (default implementation, "Type": "Standard")
        └── GroundFollowPhysicsConfig ("Type": "GroundFollow", 0.7.2+)

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
| Physics | flat fields (`MuzzleVelocity`, `Gravity`, `Bounciness`, `TimeToLive`, …) | typed `Physics` object (`"Type": "Standard"` or, 0.7.2+, `"GroundFollow"`) + `LaunchForce`, `SpawnOffset` |
| Particles/despawn | native (`HitParticles`, `MissParticles`, `TimeToLive`, `DeadTime`) — "just work", world-oriented | **none native** — you spawn particles and despawn from interactions |
| Interactions | **none** | **`Interactions`** (`ProjectileSpawn` / `ProjectileHit` / `ProjectileMiss`) |
| Launched via | the `LaunchProjectile` interaction (`ProjectileId`, plus `RotationOffset` and, as of 0.6.3, `IgnorePitch`/`IgnoreYaw`/`IgnoreRoll` — no on-hit hook) | `{ "Type": "Projectile", "Config": "<id>" }` (also accepts `IgnorePitch`/`IgnoreYaw`/`IgnoreRoll` as of 0.6.3, and `Lifetime` as of 0.7.2) |

Only the **config** schema can run interactions, so it's the one you need to apply effects, AOE, or
custom on-hit logic. Hit routing: a **terrain/wall** hit fires **`ProjectileMiss`**; a **direct entity**
hit fires **`ProjectileHit`** (confirmed in vanilla `Projectile_Config_Ice_Ball`, which restates both).

**Which manager runs a chain.** `ProjectileSpawn` runs on the shooter's `InteractionManager`; `ProjectileHit` and `ProjectileMiss` run on the projectile's own manager if it has one (ability projectiles do), otherwise on the shooter's. A shot an NPC fires therefore runs all three on the NPC's manager, which has no remote client, and the server runs each operation twice: an `Explode` in the `ProjectileHit` chain damages the target twice, a `DamageEntity` once. [The double run](interactions-double-run.md#what-each-run-reached-type-does) has the verdict per type.

### Gotchas authoring config-projectile `Interactions`

- **`Interactions` is a `Map<InteractionType, String>`, not a nested object** — so on a `Parent`-inheriting
  config, providing `Interactions` **replaces the whole handler map** rather than merging per-handler.
  (The [`Parent` deep-merge](codecs.md#parent-inheritance-inheritcodec) recurses only for nested
  `BuilderCodec` objects; a `Map` container, like an array, is replaced wholesale.) Restate **every**
  handler you want — omit `ProjectileMiss` and terrain hits never despawn, so the projectile sticks in
  the wall forever.
- **No `TimeToLive` key** on config projectiles. On impact they despawn via a `RemoveEntity`
  interaction (`"Entity": "User"`); otherwise `ProjectileModule` gives every projectile it spawns a
  `DespawnComponent` that removes it **5 minutes** after spawn. As of 0.7.2 the `Projectile`
  interaction's `Lifetime` key (seconds, `>= 0`) replaces that timer for the projectiles it launches;
  `0`, the default, keeps the 5 minutes.
- Run the effect-bearing interaction **before** `RemoveEntity` so impact effects dispatch before the
  entity is destroyed: vanilla `Projectile_Config_Ice_Ball` puts a
  `{ "Type": "Simple", "RunTime": 0, "Effects": { … } }` ahead of `RemoveEntity` in `ProjectileMiss`, and
  the `DamageEntityParent` interaction (whose `DamageEffects` carry the particles/sound) ahead of it in
  `ProjectileHit`. Copy the miss branch's sound, though, and leave its particles: the shipped file also
  writes `WorldParticles` into that `Effects` block, and the `InteractionEffects` codec declares
  only `Particles` (model-attached), so the `WorldParticles` entry is an unused key. `WorldParticles`
  is a `DamageEffects` key, which is why the hit branch's particles do render.

## ProjectileModule
**Package:** `com.hypixel.hytale.server.core.modules.projectile`

Main module for spawning and managing projectiles.

### Getting the Module
```java
ProjectileModule module = ProjectileModule.get();
```

### Key Methods
```java
// Spawn a projectile. `direction` is re-derived from its yaw/pitch (magnitude ignored) and
// scaled by config.getLaunchForce(); `position` is mutated in place by the spawn offset.
Ref<EntityStore> spawnProjectile(
    Ref<EntityStore> creatorRef,
    CommandBuffer<EntityStore> commandBuffer,
    ProjectileConfig config,
    Vector3d position,
    Vector3d direction
)

// 0.7.2+: the same, with a model-scale multiplier (also scales a DirectionalHitBox) and a
// launch-speed multiplier applied on top of LaunchForce.
Ref<EntityStore> spawnProjectile(
    Ref<EntityStore> creatorRef,
    CommandBuffer<EntityStore> commandBuffer,
    ProjectileConfig config,
    Vector3d position,
    Vector3d direction,
    float scaleMultiplier,
    float speedMultiplier
)

// The full form. `predictionId` (client prediction) and `scaleSeed` are nullable; `scaleSeed`
// feeds ProjectileConfig.createSpawnModel(Long, float) when the config sets
// "UseModelScale": true, and null picks a random scale. `despawnDelay` is in milliseconds;
// 0 or less keeps the default 5-minute despawn.
Ref<EntityStore> spawnProjectile(
    UUID predictionId,
    Long scaleSeed,
    Ref<EntityStore> creatorRef,
    CommandBuffer<EntityStore> commandBuffer,
    ProjectileConfig config,
    Vector3d position,
    Vector3d direction,
    float scaleMultiplier,
    float speedMultiplier,
    long despawnDelay
)
// Shorter prediction overloads also exist: (…, direction, long despawnDelay) and
// (…, direction, float scaleMultiplier, float speedMultiplier).

// Get component types
ComponentType<EntityStore, Projectile> getProjectileComponentType()
ComponentType<EntityStore, StandardPhysicsProvider> getStandardPhysicsProviderComponentType()
ComponentType<EntityStore, PredictedProjectile> getPredictedProjectileComponentType()
// 0.7.2+, all in modules.projectile.component:
ComponentType<EntityStore, ImpactModifiers> getImpactModifiersComponentType()
ComponentType<EntityStore, PierceProjectile> getPierceProjectileComponentType()
ComponentType<EntityStore, SpectralProjectile> getSpectralProjectileComponentType()
ComponentType<EntityStore, ProjectileHitExclusions> getProjectileHitExclusionsComponentType()
ComponentType<EntityStore, ProjectileLaunchContext> getProjectileLaunchContextComponentType()
ComponentType<EntityStore, GroundFollowProjectile> getGroundFollowProjectileComponentType()
ComponentType<EntityStore, DirectionalHitBox> getDirectionalHitBoxComponentType()
```

> **0.7.2 removed the 7-argument prediction overload**
> `spawnProjectile(UUID, Long, Ref, CommandBuffer, ProjectileConfig, Vector3d, Vector3d)`. A plugin
> compiled against it fails to link; call the `(…, direction, long despawnDelay)` overload with `0`
> for the old behaviour.

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
double getHorizontalCenterShot()
double getDepthShot()
boolean isPitchAdjustShot()

// Spawn positioning
Vector3f getSpawnOffset()
boolean isRotateSpawnOffsetByPitch()   // 0.6.3+: JSON "RotateSpawnOffsetByPitch"
boolean isRotateSpawnOffsetByYaw()     // 0.6.3+: JSON "RotateSpawnOffsetByYaw"
Direction getSpawnRotationOffset()
Vector3d getCalculatedOffset(float pitch, float yaw)

// Physics behavior
PhysicsConfig getPhysicsConfig()

// Visuals
Model getModel()
ModelAsset getModelAsset()              // 0.6.3+
Model createSpawnModel(Long scaleSeed)  // 0.6.3+: scaled per "UseModelScale" (random when seed is null)
Model createSpawnModel(Long scaleSeed, float scaleMultiplier)  // 0.7.2+: that scale times the multiplier

// Piercing hit shape (0.7.2+, JSON "DirectionalHitBox": { "Width", "Depth" }, both required);
// null when unset
DirectionalHitBoxConfig getDirectionalHitBox()

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
double getHorizontalCenterShot() // Horizontal offset for aiming
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

## GroundFollowPhysicsConfig
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Added in 0.7.2 and registered on `PhysicsConfig.CODEC` as `"Type": "GroundFollow"`. It extends
`StandardPhysicsConfig`, so it takes every `Standard` key, and adds two integers, each default `1`
and validated `>= 0`:

| Key | Meaning |
|-----|---------|
| `MaxClimb` | Blocks the projectile may step up in one move; a taller wall ends its course |
| `MaxDrop` | Blocks it may drop in one move; a deeper drop ends its course |

`apply(...)` adds a `GroundFollowProjectile` component, and the tick system then snaps the
projectile to the ground ahead instead of casting it against blocks. The one shipped user is
`Projectile_Config_GroundSlam` (`"MaxClimb": 1, "MaxDrop": 1, "Gravity": 0`).

---

## ImpactConsumer
**Package:** `com.hypixel.hytale.server.core.modules.projectile.config`

Callback interface for handling projectile impacts.

### Method
```java
void onImpact(
    Ref<EntityStore> projectileRef,    // The projectile entity
    Vector3d impactPosition,           // Where it hit
    Vector3i impactBlock,              // Block it bounced off / came to rest on (null if none) — added as of 0.6.3
    Ref<EntityStore> targetRef,        // Entity that was hit (null on a terrain hit)
    String collisionDetailName,        // Hitbox detail name on the hit entity (null on a terrain hit)
    CommandBuffer<EntityStore> buffer  // Command buffer for responses
)
```
The tick system fires this on an entity contact (`targetRef` set, state → `INACTIVE`) and when a bounce settles into rest (`targetRef`/`collisionDetailName` null, state → `RESTING`). Two 0.7.2 additions change that for some projectiles. A piercing projectile (one carrying the `PierceProjectile` component, which the abilities launcher adds) fires it once per newly hit entity and keeps flying. A projectile whose course ends fires it once more with `impactBlock`, `targetRef` and `collisionDetailName` all null, state → `INACTIVE`, and despawns 300 ms later. A course ends when a piercing projectile expires, passes its maximum distance, stalls or runs out of bounces, or when a `GroundFollow` projectile meets a wall or drop it cannot take.

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
static final int WATER_DETECTION_EXTREMA_COUNT = 2;    // Samples for water detection
static final double MIN_BOUNCE_EPSILON = 0.4;          // Minimum bounce velocity
static final double MIN_BOUNCE_EPSILON_SQUARED = 0.16; // Squared minimum
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
Vector3i bounceBlockPosition()        // 0.6.3+: block hit by the last bounce (null once cleared)
void clearBounced()                   // 0.6.3+: resets bounced flag and bounceBlockPosition
BlockPosition getContactBlock()       // 0.6.3+: block the projectile is resting against (null if none)
void setFallingAfterBreak(boolean b)  // 0.6.3+: set when the support block breaks (see RestingSupport)
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
void setImpactConsumer(ImpactConsumer consumer)
BounceConsumer getBounceConsumer()
void setBounceConsumer(BounceConsumer consumer)
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
void rotateBody(double deltaTime, Rotation3f rotation)   // applies the config RotationMode to the body rotation
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

JSON keys (`"Type": "Projectile"`): `Config` (the `ProjectileConfig` id), `IgnorePitch`,
`IgnoreYaw`, `IgnoreRoll`, and, as of 0.7.2, `Lifetime` (seconds, `>= 0`; `0` keeps the
5-minute default despawn).

As of 0.7.2 a launch also puts a `ProjectileLaunchContext` component (the `InteractionType` and
whether the held item is a weapon) and, when the shooter has any, an `ImpactModifiers` component
on the new projectile. It then invokes a `ProjectileLaunchEvent` (an `EcsEvent` in
`modules.projectile.event`, with `getProjectileRef()`, `getInteractionType()` and
`isLaunchedByWeapon()`) on the **shooter**, so an `EntityEventSystem` over players can react to
each shot.

---

## Usage Examples

### Spawning a Projectile
```java
ProjectileModule module = ProjectileModule.get();

// Get projectile config from assets (the id is the file name under Server/ProjectileConfigs/)
ProjectileConfig config = ProjectileConfig.getAssetMap().getAsset("Projectile_Config_Arrow_Crossbow");

// Spawn position (mutated in place by the config's spawn offset) and aim direction.
// Only the direction's yaw/pitch matter: the module rebuilds a unit vector from them,
// adds SpawnRotationOffset, and scales by config.getLaunchForce() — do not pre-multiply.
Vector3d spawnPos = new Vector3d(x, y, z);
Vector3d direction = new Vector3d(dirX, dirY, dirZ);

// Spawn the projectile
Ref<EntityStore> projectileRef = module.spawnProjectile(
    shooterRef,
    commandBuffer,
    config,
    spawnPos,
    direction
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
    String systemId, Vector3dc pos,       // any Vector3d works (position parameters are Vector3dc as of 0.6.3)
    float yaw, float pitch, float roll,   // ROTATION IN RADIANS — (0,0,0) = world-aligned
    float scale, float maxDuration,
    ComponentAccessor<EntityStore> accessor);   // a CommandBuffer works here
```

The three rotation floats are yaw/pitch/roll, in that order, in **radians** (the `PlayVfxEffect`
trigger calls this after `Math.toRadians(...)` on its degree fields). The overload sends the effect
to players within 75 blocks of `pos`. Simpler overloads exist —
`spawnParticleEffect(String, Vector3dc, ComponentAccessor)`,
`spawnParticleEffect(WorldParticle, Vector3dc, ...)`, and `Rotation3f`/`List<Ref>`/`Color` variants.

Spawning from code with rotation `(0,0,0)` is how you get an **untilted, world-oriented** impact
effect. A `ModelParticle` placed in JSON attaches to an `EntityPart` (`Self`, `Entity`, `PrimaryItem`,
or `SecondaryItem` — there is **no world-space anchor**) and inherits that entity's transform, so a
particle on a pitched projectile tilts with the shot — a flat ground decal looks wrong. `DetachedFromModel: true`
only makes the system *persist* after the entity despawns; it does **not** change spawn orientation
(0.6.3 adds a sibling `ClearParticlesOnRemove` boolean on `ModelParticle`, the opposite switch: its codec
documentation says that when the owning entity is removed, the effect's already-emitted particles are
cleared at once instead of finishing their lifespan. The server only forwards the flag to the client).
For a world-oriented effect, use a `WorldParticle` (only available via `DamageEffects`, i.e. entity
hits) or spawn from code with rotation `(0,0,0)`. As with JSON particles, pass a non-zero `scale` —
the field is a primitive `float` and `0` renders invisibly.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the projectile subsystem (verified against `HytaleServer.jar`).

- **`has no valid ProjectileConfig`** → an entity/interaction tried to launch a projectile whose `ProjectileConfig` could not be resolved. Fix: pass a config obtained from `ProjectileConfig.getAssetMap().getAsset(id)` and verify the id exists.
- **`No projectile config typeName provided`** → a simple-schema projectile was launched with an empty asset name: `ProjectileComponent.assembleDefaultProjectile(...)`, which the `LaunchProjectile` interaction calls, throws it when `ProjectileId` is empty. Fix: set `ProjectileId` to a `Server/Projectiles/` asset id.
- **Symptom:** `ProjectileConfig.getAssetMap().getAsset("arrow")` returns `null` → the asset id didn't match (ids are case-sensitive file names, e.g. `Projectile_Config_Arrow_Crossbow`). Fix: use the exact asset-file id and null-check before spawning.
- **Symptom:** a projectile bounces forever or never stops → bounce limits come from `StandardPhysicsConfig`. Fix: compare `physics.getBounces()` against `config.getBounceCount()` and check `getBounceLimit()`/`getBounciness()` (see [StandardPhysicsProvider](#standardphysicsprovider)).
- **Symptom:** an `AOECircle`/`AOECylinder` selector in a projectile's `ProjectileHit`/`ProjectileMiss` affects only the directly-hit entity, never a radius → projectile-hosted selectors don't sweep (unlike melee). Fix: use `Type: "Explode"`, a trigger volume, or the Java radius query `Selector.selectNearbyEntities(...)` (see [interactions-combat.md → AOECircle](interactions-combat.md#aoecircle-area-of-effect)).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
