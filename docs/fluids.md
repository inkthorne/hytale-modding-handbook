---
title: "Fluids API"
description: "Define Hytale fluids in Java — the Fluid asset's identity and properties, fluid level, light emission, entity damage, spread Ticker behavior, and interaction rules like water plus lava."
seo:
  type: TechArticle
---

# Fluids API

**Doc type:** Java API · **Verified against 0.5.1**

Covers the `Fluid` asset type (water, lava, etc.) and how fluid data is surfaced through collision queries.

## Overview

Implemented in `com.hypixel.hytale.server.core.asset.type.fluid` and provides:
- A `Fluid` asset describing a fluid block's identity and properties
- Fluid level, light emission, and entity-damage values
- Tick behavior governing fluid spread (`Ticker`)
- Fluid interaction rules (e.g. water + lava transforms)
- Fluid exposure through collision results (`BlockCollisionData`, `CollisionConfig`)

## Architecture
```
Fluid (asset type)
├── Identity (getId / isUnknown; EMPTY / UNKNOWN constants)
├── Properties (max level, light, damage-to-entities, isTrigger)
├── Ticker (fluid spread behavior)
└── Interactions (fluid-meets-fluid rules)

Collision exposure
├── BlockCollisionData (fluid, fluidId on a block collision)
└── CollisionConfig (fluid, fluidId, fluidLevel during a query)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Fluid` | `server.core.asset.type.fluid` | Asset type for fluid blocks (water, lava, etc.) |
| `Ticker` | (referenced via `Fluid.getTicker()`) | Tick behavior controlling fluid spread |
| `BlockCollisionData` | see [collision.md](collision.md#blockcollisiondata) | Exposes the fluid at a block collision |
| `CollisionConfig` | see [collision.md](collision.md#collisionconfig) | Exposes fluid id/level during collision queries |

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

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 fluid system (verified against `HytaleServer.jar`).

- **`Attempted to register an invalid Fluid`** → fluid registration received a malformed/invalid fluid asset. Fix: register a valid `Fluid` asset.
- **Symptom:** a collision reports a fluid even where there is none → `collision.fluid` is non-null but set to the `Fluid.EMPTY` sentinel. Fix: guard with `collision.fluid != null && collision.fluid != Fluid.EMPTY` (and treat `Fluid.UNKNOWN` as unresolved), as in the usage example above.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
