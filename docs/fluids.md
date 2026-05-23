# Fluids API

**Doc type:** Java API

## Fluid
**Package:** `com.hypixel.hytale.server.core.asset.type.fluid`

Asset type for fluid blocks (water, lava, etc.).

### Constants
```java
static final Fluid EMPTY    // Empty/no fluid
static final Fluid UNKNOWN  // Unknown fluid type
static final int EMPTY_ID   // ID for empty fluid
static final int UNKNOWN_ID // ID for unknown fluid
```

### Identity
```java
int getId()
boolean isUnknown()
```

### Properties
```java
int getMaxFluidLevel()      // Maximum level (typically 7)
Ticker getTicker()          // Tick behavior for fluid spread
float getDamageToEntities() // Damage dealt to entities (e.g., lava)
int getLight()              // Light level emitted
boolean isTrigger()         // Whether fluid triggers collision events
```

### Interactions
```java
Object getInteractions()  // Fluid interaction rules (e.g., water + lava = cobblestone)
```

> **See also:** [Collision API](collision.md#collisionconfig)

---

## Usage with BlockCollisionData

Fluids are exposed through `BlockCollisionData` when a collision intersects fluid:

```java
BlockCollisionData collision = result.getFirstBlockCollision();
if (collision.fluid != null && collision.fluid != Fluid.EMPTY) {
    int fluidId = collision.fluidId;
    Fluid fluid = collision.fluid;

    if (fluid.getDamageToEntities() > 0) {
        // Entity is in damaging fluid (e.g., lava)
    }
}
```

> **See also:** [World API](world.md#worldchunk)

## Usage with CollisionConfig

Access fluid information during collision queries:

```java
CollisionConfig config = ...;
Fluid fluid = config.fluid;
int fluidId = config.fluidId;
byte fluidLevel = config.fluidLevel;  // 0-7, where 0 is full
```
