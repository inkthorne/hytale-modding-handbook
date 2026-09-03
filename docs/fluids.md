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
├── Ticker (fluid spread behavior; fluid-meets-fluid rules live on DefaultFluidTicker)
└── Interactions (interaction slots — Use / Collision / …, like BlockType)

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
String getId()      // The asset key ("Water_Source", "Lava", …) — not the numeric id
boolean isUnknown()
```

The **numeric** fluid id used by `FluidSection`, `CollisionConfig.fluidId` and the `Collisions` map is the asset-map index, not `getId()`. Resolve one with `Fluid.getFluidIdOrUnknown(String key, String errorFormat, Object... args)` or `Fluid.getAssetMap().getIndex(key)`; `EMPTY_ID` is `0` and `UNKNOWN_ID` is `1`.

### Properties
```java
int getMaxFluidLevel()      // JSON "MaxFluidLevel" — 1 for source blocks, 8 for flowing Water
FluidTicker getTicker()     // Tick behavior for fluid spread (see FluidTicker below)
int getDamageToEntities()   // Damage dealt to entities (e.g., lava)
ColorLight getLight()       // Light emitted (protocol.ColorLight)
boolean isTrigger()         // Whether fluid triggers collision events
String getFluidFXId()       // JSON "FluidFXId" (Server/Item/Block/FluidFX/<id>.json)
```

### Interactions
```java
Map<InteractionType, String> getInteractions()  // Interaction slots (Use / Collision / …), same shape as BlockType.getInteractions()
```

Fluid-meets-fluid transforms (water + lava → cobblestone) are **not** here — they are the ticker's `Collisions` map, `DefaultFluidTicker.getCollisionMap()` (below).

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
| `FlowRate` | float | "The tick frequency for this fluid type, **in seconds**" — a tick *period*, so a larger value is a **slower** fluid. Default `0.5`; must be greater than `0`. Lava and fire set `2.0` |
| `CanDemote` | boolean | "If false then the fluid will stay at its level". Default `true` |
| `SupportedBy` | string | Fluid key that keeps this fluid alive (e.g. flowing `Water` is `"SupportedBy": "Water_Source"`) |

`DefaultFluidTicker` adds:

| Key | Type | Description |
|-----|------|-------------|
| `SpreadFluid` | string | Fluid key placed when this fluid spreads (source blocks spread as their flowing variant); validated against the `Fluid` asset store |
| `Collisions` | object | "Defines what happens when this fluid tries to spread into another fluid" — map of *other fluid key* → `FluidCollisionConfig`: `BlockToPlace` (block placed on collision), `SoundEvent`, `PlaceFluid` (whether to still place the fluid; default `false`) |

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

`FireFluidTicker` adds `SpreadFluid` plus a `Flammability` array — tag-pattern rules deciding what fire can ignite. Each entry:

| Key | Type | Description |
|-----|------|-------------|
| `TagPattern` | id **or** inline object | "TagPattern to match blocks that this config applies to". A `ContainedAssetCodec`, so either a `TagPattern` asset key or an inline `Op` tree of `Equals` / `And` / `Not` over block tags (the shipped `Fire.json` inlines them) |
| `Priority` | integer | "Priority for pattern matching - higher values are checked first" |
| `BurnLevel` | byte | "The fluid level the fluid has to be greater than or equal to to burn this block". Default `1` |
| `BurnChance` | float | "Probability (0.0 to 1.0) that the block will burn each tick when above the burn level". Default `0.1` |
| `ResultingBlock` | string | "The block to place after burning, if any". Default `"Empty"` |
| `ResultingState` | string | "The block state to attempt to change to after burning, if any" |
| `SoundEvent` | string | Sound played when the block burns; validated against the `SoundEvent` asset store |

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

Subclasses implement the protected `spread(...)` hook, which returns a `BlockTickStrategy` — the same enum scheduled block ticks use (see [Block Ticking](blocks.md#blocktickstrategy)): `CONTINUE` keeps the fluid ticking, `SLEEP` parks it until a neighboring block change re-wakes it via `setTickingSurrounding`, `WAIT_FOR_ADJACENT_CHUNK_LOAD` retries once the neighbor chunk is in.

They may also override the protected `isAlive(...)`, which returns a **`FluidTicker.AliveStatus`** (`ALIVE`, `DEMOTE`, `WAIT_FOR_ADJACENT_CHUNK`) rather than a `BlockTickStrategy`. Both `FiniteFluidTicker` and `FireFluidTicker` override it to always return `ALIVE`; the base implementation is what enforces `SupportedBy` and `CanDemote`. Both hooks take the same argument list, with the fluid's current level as a `byte` between `Fluid` and the block coordinates:

```java
protected abstract BlockTickStrategy spread(World world, long tick, FluidTicker.Accessor accessor,
                                            FluidSection fluids, BlockSection blocks, Fluid fluid,
                                            int fluidId, byte fluidLevel, int x, int y, int z)
protected FluidTicker.AliveStatus isAlive(FluidTicker.Accessor accessor,
                                          FluidSection fluids, BlockSection blocks, Fluid fluid,
                                          int fluidId, byte fluidLevel, int x, int y, int z)
```

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
byte fluidLevel = config.fluidLevel;  // 1..MaxFluidLevel; MaxFluidLevel = full, one less per spread step; 0 = no fluid
```

Level semantics (from `DefaultFluidTicker.spread`): fluid flowing straight down is placed at the spread fluid's full `getMaxFluidLevel()` (8 for flowing `Water`); each *horizontal* spread step places the `SpreadFluid` at `level - 1`, and a non-source block at level 1 sleeps instead of spreading sideways. A source (max level 1) spreads its flowing variant at *that* fluid's `MaxFluidLevel - 1` (7 for `Water`).

---

## Gotchas & Errors

Backtick-quoted strings below are literal messages in the jar.

- **`Attempted to register a Fluid with an invalid name`** (the full line appends `<name>: using Unknown instead.`) → world generation asked `MaterialCache.getFluidMaterial(String)` for a fluid key that is not in the `Fluid` asset store. It is a **warning**, not a failure: generation continues with the unknown-fluid material. Fix: check the key's spelling against `Server/Item/Block/Fluids/`. (Earlier revisions of this page quoted this as "Attempted to register an invalid Fluid"; that exact wording is not in the jar.)
- **`Unknown fluid: %s`** → a `PlaceFluid` interaction names a fluid key that does not resolve; the interaction falls back to `Fluid.UNKNOWN` (see [Interactions — World](interactions-world.md)). Sibling messages exist for other call sites: `Unknown fluid %s` (`RefillContainerInteraction`), `Unknown fluid '%s'` (prefab deserialization), `Unknown fluid! <name>` (worldgen block-array loading, which throws).
- **Symptom:** a collision reports a fluid even where there is none → `collision.fluid` is non-null but set to the `Fluid.EMPTY` sentinel. Fix: guard with `collision.fluid != null && collision.fluid != Fluid.EMPTY` (and treat `Fluid.UNKNOWN` as unresolved), as in the usage example above.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
