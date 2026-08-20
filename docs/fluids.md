---
title: "Fluids API"
description: "Define Hytale fluids in Java — the Fluid asset's identity and properties, fluid level, light emission, entity damage, spread Ticker behavior, and interaction rules like water plus lava."
seo:
  type: TechArticle
---

# Fluids API

**Doc type:** Java API · **Verified against 0.5.9**

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
| `FluidTicker` | `server.core.asset.type.fluid` | Abstract tick behavior controlling fluid spread; returned by `Fluid.getTicker()` — see [FluidTicker](#fluidticker) |
| `DefaultFluidTicker` | `server.core.asset.type.fluid` | Standard infinite-source spread (water, lava); fluid-vs-fluid `Collisions` |
| `FiniteFluidTicker` | `server.core.asset.type.fluid` | Volume-conserving spread (`Water_Finite`) |
| `FireFluidTicker` | `server.core.asset.type.fluid` | Fire as a fluid: spreads via `Flammability` tag rules, burns into solid blocks |
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

## FluidTicker
**Package:** `com.hypixel.hytale.server.core.asset.type.fluid`

Abstract base class for fluid tick behavior — what `Fluid.getTicker()` returns. It decodes from the `Ticker` object of a fluid block asset (`Server/Item/Block/Fluids/*.json`); `FluidTicker.CODEC` dispatches on the `Type` key. The shipped fluid plugin registers three tickers:

| `Type` value | Class | Shipped example |
|--------------|-------|-----------------|
| `Default` (used when `Type` is omitted) | `DefaultFluidTicker` | `Water_Source.json`, `Lava_Source.json` |
| `Finite` | `FiniteFluidTicker` | `Water_Finite.json` |
| `Fire` | `FireFluidTicker` | `Fire.json` |

### Ticker JSON keys

Base keys (all ticker types):

| Key | Type | Description |
|-----|------|-------------|
| `FlowRate` | float | Spread speed (e.g. lava sets `2.0`) |
| `CanDemote` | boolean | Whether the fluid level may decrease over time |
| `SupportedBy` | string | Fluid id that keeps this fluid alive (e.g. flowing `Water` is `"SupportedBy": "Water_Source"`) |

`DefaultFluidTicker` adds:

| Key | Type | Description |
|-----|------|-------------|
| `SpreadFluid` | string | Fluid id placed when this fluid spreads (source blocks spread as their flowing variant) |
| `Collisions` | object | Map of *other fluid id* → collision result: `BlockToPlace`, `SoundEvent`, `PlaceFluid` (whether the fluid is still placed) |

```json
"Ticker": {
  "CanDemote": false,
  "SpreadFluid": "Water",
  "Collisions": {
    "Lava":        { "BlockToPlace": "Rock_Stone_Cobble", "SoundEvent": "SFX_Flame_Break" },
    "Lava_Source": { "BlockToPlace": "Rock_Magma_Cooled", "SoundEvent": "SFX_Flame_Break" }
  }
}
```
*(from `Water_Source.json` — the water + lava transform rules)*

`FireFluidTicker` adds `SpreadFluid` plus a `Flammability` array — tag-pattern rules deciding what fire can ignite. Each entry: `TagPattern` (an `Op` tree of `Equals` / `And` / `Not` over block tags), `Priority`, `BurnLevel`, `BurnChance`, and optional `ResultingBlock` / `ResultingState` / `SoundEvent`:

```json
"Ticker": {
  "Type": "Fire",
  "CanDemote": false,
  "SpreadFluid": "Fire",
  "FlowRate": 2.0,
  "SupportedBy": "Fire",
  "Flammability": [
    { "TagPattern": { "Op": "Equals", "Tag": "Plant" }, "Priority": 0, "BurnLevel": 3, "BurnChance": 0.9 }
  ]
}
```
*(abridged from `Fire.json`)*

`FiniteFluidTicker` adds no keys of its own (`"Ticker": { "Type": "Finite" }`) — it conserves volume when spreading instead of emitting from an infinite source.

### Java surface

```java
public abstract class FluidTicker {
    public static final int FLUID_BLOCK_DISTANCE = 5; // Max horizontal flow distance

    int getSupportedById()          // Resolved fluid id of "SupportedBy"
    boolean canDemote()             // JSON "CanDemote"
    boolean canOccupySolidBlocks()  // false except FireFluidTicker
    boolean isSelfFluid(int fluidId, int otherFluidId)
    boolean blocksFluidFrom(BlockType type, int rotationIndex, int offsetX, int offsetZ)

    // Engine entry points — both return a BlockTickStrategy
    BlockTickStrategy tick(CommandBuffer<ChunkStore> buffer, FluidTicker.CachedAccessor accessor,
                           FluidSection fluids, BlockSection blocks, Fluid fluid,
                           int fluidId, int x, int y, int z)
    BlockTickStrategy process(World world, long tick, FluidTicker.Accessor accessor,
                              FluidSection fluids, BlockSection blocks, Fluid fluid,
                              int fluidId, int x, int y, int z)

    static boolean isFullySolid(BlockType type)
    static boolean isSolid(BlockType type)
    // Re-wake fluid ticking around a changed block
    static void setTickingSurrounding(FluidTicker.Accessor accessor, BlockSection section,
                                      int x, int y, int z)
}
```

Subclasses implement the protected `spread(...)` hook (and may override `isAlive(...)`) — both also return a `BlockTickStrategy`, the same enum scheduled block ticks use (see [Block Ticking](blocks.md#blocktickstrategy)): `CONTINUE` keeps the fluid ticking, `SLEEP` parks it until a neighboring block change re-wakes it via `setTickingSurrounding`, `WAIT_FOR_ADJACENT_CHUNK_LOAD` retries once the neighbor chunk is in.

Subclass extras:

```java
// DefaultFluidTicker
static final DefaultFluidTicker INSTANCE;
Int2ObjectMap<DefaultFluidTicker.FluidCollisionConfig> getCollisionMap() // "Collisions", keyed by fluid id

// FireFluidTicker
static final FireFluidTicker INSTANCE;
boolean canOccupySolidBlocks()  // true — fire spreads into flammable solid blocks
List<FireFluidTicker.FlammabilityConfig> getSortedFlammabilityConfigs() // by Priority
```

A custom ticker is possible in principle by subclassing and registering a new `Type` on `FluidTicker.CODEC` in `setup()` — the same codec-registration pattern as [custom block ticking](blocks.md#hooking-custom-block-ticking).

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
