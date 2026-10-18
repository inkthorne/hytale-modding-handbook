---
title: "Block Access"
description: "Reading and writing blocks in Hytale 0.7.2+ — resolving chunk-section references from the ChunkStore, the BlockSection / FluidSection / BlockComponentSection / BlockHealthSection components, BlockOperations writes, SectionReader, SetBlockSettings, threading, and a migration table from the removed World and WorldChunk block methods."
seo:
  type: TechArticle
---

# Block Access

**Doc type:** Java API · **Verified against 0.7.2**

How a plugin reads and writes blocks. In 0.7.2 every block lives in a 32×32×32 chunk **section**, and
sections are entities in the world's `ChunkStore`: you resolve a section reference, read its
components, and write through `BlockOperations`. The column-level side (chunk loading, `WorldChunk`,
`ChunkFlag`, cubic sections, lighting, `ChunkTracker`) is in [world-chunks.md](world-chunks.md), and
the `World` object is in [world.md](world.md).

> **0.7.2 redesigned block access. Code written against 0.6.x does not compile.**
> - `World` dropped `ChunkAccessor` and `IWorldChunks`. Both interfaces were removed, along with
>   `IChunkAccessorSync`, `OverridableChunkAccessor`, `LocalCachedChunkAccessor` and
>   `ChunkSectionReference`. So `world.getBlock(...)`, `world.setBlock(...)`, `world.breakBlock(...)`,
>   `world.getChunkIfLoaded(...)` and `world.getChunkAsync(...)` are gone.
> - `WorldChunk` lost its whole block API (`getBlock`, `setBlock`, `breakBlock`, `getBlockType`,
>   `getFluidId`, `getHeight`, `setTicking`, `setState`, `getBlockComponentHolder`, `getWorld`,
>   `getBlockChunk`, …). It now holds only the column's flags, keep-alive and save state.
> - Blocks are reached through the **section**: resolve a section reference from the world's
>   `ChunkStore` (which now extends the new `ChunkGrid`), read its `BlockSection` component, and write
>   with the static `BlockOperations.setBlock`. The shipped `/block` commands in
>   `server.core.universe.world.commands.block` are the reference idiom, and this page follows them.
>
> The [migration table](#migrating-from-06x) maps each removed method to its replacement.

---

## The section model

Every chunk **column** (32×32 blocks, keyed by `ChunkUtil.indexChunk(chunkX, chunkZ)`) and every
32×32×32 **section** is its own entity in the world's `ChunkStore`. The column entity carries
`WorldChunk`, `BlockChunk`, `ChunkColumn` and `HeightmapColumn`. Each section entity carries
`ChunkSection` (its coordinates and save state), `BlockSection` (block ids, rotations, fillers,
ticking bits, light) and `BlockHealthSection` (durability), and, when present, `FluidSection`,
`BlockComponentSection` (block-entity holders), `EnvironmentSection` and `BlockPhysics` (support
values). Their APIs are under [Section components](#section-components).

Section coordinates are block coordinates shifted right by 5: `ChunkUtil.chunkCoordinate(blockY)` gives
the section's y, exactly as it gives the column's x and z. Every block-level method on `BlockSection`,
`FluidSection` and `BlockOperations` takes **world** block coordinates and masks them to the section
itself (`ChunkUtil.indexBlock` keeps the low 5 bits), so you never convert to local coordinates.

> **How tall is a world?** On a default world a column has sections 0–9 (blocks 0–319), loaded with the
> column. Worlds with *cubic* storage can load sections at any y, which is why 0.7.2 deprecated
> `ChunkUtil.HEIGHT` and its siblings. Ask the world which y it can hold, in place of a hard-coded
> `0..319`. `SectionReader.canHoldY(y)` returning `false` rules a y out: it is outside `0..319` and
> neither the world's loader nor its generator is cubic. A `true` outside `0..319` is only permission. Loading
> such a section takes a cubic loader, and generating it takes a cubic loader *and* a cubic generator,
> so a lookup there can still complete with `null`; see
> [world-chunks.md → Cubic sections](world-chunks.md#cubic-sections).

---

## Resolving a section

`ChunkStore` inherits these lookups from `ChunkGrid`:

```java
// Synchronous: the section's ref if it is loaded right now, else null. Never loads anything.
Ref<ChunkStore> getChunkSectionReferenceAtBlock(int blockX, int blockY, int blockZ)
Ref<ChunkStore> getChunkSectionReference(int sectionX, int sectionY, int sectionZ)

// Asynchronous: loads or generates as the flags allow (GetChunkFlags; default 0 = load or generate)
CompletableFuture<Ref<ChunkStore>> getChunkSectionReferenceAtBlockAsync(int blockX, int blockY, int blockZ)
CompletableFuture<Ref<ChunkStore>> getChunkSectionReferenceAtBlockAsync(int blockX, int blockY, int blockZ, int flags)
CompletableFuture<Ref<ChunkStore>> getChunkSectionReferenceAsync(int sectionX, int sectionY, int sectionZ, int flags)
```

The `AtBlock` forms only convert with `ChunkUtil.chunkCoordinate` and delegate. The future completes
with `null` when there is nothing to return, for example a section outside `0..9` that the world's
loader and generator cannot supply (see [Cubic sections](world-chunks.md#cubic-sections)), or a `NO_LOAD | NO_GENERATE` request for a section that is not in memory. Always check
`ref != null && ref.isValid()`.

**Which one to use depends on the thread.**

- **On the world thread** (inside a system, an interaction, or a `world.execute` task), the block is
  usually in a loaded section already. Use the synchronous form and treat `null` as "not loaded". This
  is what the shipped interactions do — `BreakBlockInteraction`, `ChangeBlockInteraction`,
  `ChangeStateInteraction`, `PlaceFluidInteraction` all start with
  `world.getChunkStore().getChunkSectionReferenceAtBlock(x, y, z)`.
- **Anywhere else, or when the section may not be loaded** (commands, async callbacks), use the async
  form and continue **on the world executor**. `World` implements `Executor`, so pass it as the second
  argument of `thenAcceptAsync`. Component reads and writes on the `ChunkStore` assert they are on the
  world thread, and a plain `thenAccept` gives no thread guarantee: when the section is already loaded
  the future usually comes back completed, and the continuation runs at once on the calling thread.

```java
// SimpleBlockCommand (server.core.universe.world.commands.block), condensed
ChunkStore chunkStore = world.getChunkStore();
chunkStore.getChunkSectionReferenceAtBlockAsync(x, y, z, GetChunkFlags.SET_TICKING)
        .thenAcceptAsync(sectionRef -> {
            if (sectionRef == null || !sectionRef.isValid()) {
                return;                                   // no section there
            }
            // on the world thread: read or write through the section
        }, world)
        .exceptionally(t -> {
            // a load or generation failure surfaces here
            return null;
        });
```

The shipped commands pass `GetChunkFlags.SET_TICKING` (4): load or generate the section if needed, and
make sure it is ticking. See [GetChunkFlags](world-chunks.md#getchunkflags) for the rest.

---

## Reading

Read components straight off the section ref with the `ChunkStore`'s `Store`:

```java
Store<ChunkStore> store = chunkStore.getStore();
BlockSection blocks = store.getComponent(sectionRef, BlockSection.getComponentType());

int blockId   = blocks.get(x, y, z);                 // world coordinates
BlockType type = BlockType.getAssetMap().getAsset(blockId);
int rotation  = blocks.getRotationIndex(x, y, z);
int filler    = blocks.getFiller(x, y, z);

FluidSection fluids = store.getComponent(sectionRef, FluidSection.getComponentType());   // may be null
BlockPhysics physics = store.getComponent(sectionRef, BlockPhysics.getComponentType());  // may be null
int support = physics != null ? physics.get(x, y, z) : 0;
```

That is `BlockGetCommand`'s body. For reads that cross many sections, use a
[`SectionReader`](#sectionreader), which caches the section refs it resolves.

---

## Writing with BlockOperations

**Package:** `com.hypixel.hytale.server.core.universe.world.chunk`

`BlockOperations` holds the static write path. It replaces the `setBlock` overloads that `World` and `WorldChunk` carried before 0.7.2:

```java
// The normal write. Coordinates are world coordinates inside the section `sectionRef`.
// Returns true if the block id or rotation changed.
static boolean setBlock(ChunkStore chunkStore, Ref<ChunkStore> sectionRef,
                        int x, int y, int z, int blockId, BlockType blockType,
                        int rotation, int filler, int settings)      // settings = SetBlockSettings bits

// Switch a block to another state of its type (e.g. an open/closed door), keeping its rotation
static void setBlockInteractionState(ChunkStore chunkStore, Ref<ChunkStore> sectionRef,
                                     int x, int y, int z, BlockType blockType, String state, boolean force)

// Would blockType at rotationIndex fit here, counting every block its hitbox covers?
static boolean testPlaceBlock(ComponentAccessor<ChunkStore> accessor, BlockSection section,
                              int x, int y, int z, BlockType blockType, int rotationIndex)
static boolean testPlaceBlock(ComponentAccessor<ChunkStore> accessor, BlockSection section,
                              int x, int y, int z, BlockType blockType, int rotationIndex,
                              BlockOperations.TestBlockFunction occupiedIsOk)

// Mark the 3x3x3 cells around (x, y, z) ticking
static void updateBlockArea(ChunkStore chunkStore, ChunkSection chunkSection, BlockSection section,
                            int x, int y, int z)
// The PERFORM_BLOCK_UPDATE effect: mark ticking every cell of blockType's hitbox footprint at that
// rotation, plus a one-cell margin (a 3x3x3 for a one-cell block); returns early without a hitbox asset
static void updateBlockArea(ChunkStore chunkStore, ChunkSection chunkSection, BlockSection section,
                            BlockType blockType, int rotation, int x, int y, int z)

// For a filler block, the position of the block it belongs to
static BlockPosition resolveBaseBlockPosition(ChunkStore chunkStore, BlockPosition position)
```

`setBlock` is what `BlockSetCommand` calls:

```java
BlockOperations.setBlock(chunkStore, sectionRef, x, y, z,
        BlockType.getAssetMap().getIndex(blockType.getId()), blockType, 0, 0, 0);
```

The block id is the **int** index from `BlockType.getAssetMap().getIndex(id)`; `BlockType.getId()` is
the string key. To clear a block, write id `0` with `BlockType.EMPTY`, as `PrefabUtil` does.

When the id or rotation changes (or `FORCE_CHANGED` is set), `setBlock` runs the side-effect pipeline:
it marks the section for saving, updates the column's heightmap, sends particles, reports the
replacement (`BlockAnimationModule.onBlockReplaced`, `BlockHealthModule.onBlockReplaced`), swaps the
block entity, invalidates light through the world's lighting manager, sets the ticking bit from the new
type's tick procedure, removes and places filler blocks, and resets block physics. A
[`SetBlockSettings`](#setblocksettings) bit can suppress the heightmap, particle, block-entity and
filler steps. The saving flag, the two `onBlockReplaced` calls, the light invalidation, the ticking
bit and the physics reset (made whenever the column ref is valid) always run. It does **not** fire
`BreakBlockEvent`, drop items or play sounds.

> **⚠️ `BlockSection.set(x, y, z, id, rotation, filler)` is the raw palette write.**
> When it changes something it calls the section's own `BlockSection.invalidateLocalLight()` and,
> once the section is loaded, records the cell so `ChunkSystems` resends it to players. Every other
> step above is skipped: the saving flag, heightmap, ticking bit, filler, block entity, health,
> physics, and the world-level light update that `setBlock` makes through
> `ChunkLightingManager.invalidateLightAtBlock` (which also weighs the heightmap change).
> Use it only for bulk analysis or worldgen-style code; for gameplay edits use
> `BlockOperations.setBlock`.
> `BlockOperations.setBlockPreLoad` is the in-between form for sections that are not in the store yet
> (on top of the raw write it sets the saving flag and the ticking bit, nothing else).

---

## Breaking like a player

To break a block the way a player or an explosion does — `BreakBlockEvent` (cancellable), drops,
break sound, the block's `OnBreak` interaction — use `BlockHarvestUtils`
(`server.core.modules.interaction`), which needs both stores:

```java
// ref: the breaking entity (null for an environmental break, which fires EnvironmentBreakBlockEvent)
BlockHarvestUtils.performBlockBreak(ref, heldItemStack, new Vector3i(x, y, z),
        SetBlockSettings.NONE, sectionRef, entityStoreAccessor, chunkStore.getStore());
```

It redirects a filler block to its base block, then removes it through `BlockOperations.setBlock`.

---

## Ticking

A block ticks when its ticking bit is set in its section **and** the section is ticking. Sections and
columns that are not ticking carry the `NonTicking` marker component
(`ChunkStore.REGISTRY.getNonTickingComponentType()`); `GetChunkFlags.SET_TICKING` removes it. The
per-block bit lives on `BlockSection` (`BlockSetTickingCommand`):

```java
if (blockSection.setTicking(x, y, z, true)) {
    chunkSection.markNeedsSaving();          // ChunkSection from the same sectionRef
}
```

---

## Complete example

A world command that replaces the block at a position with stone, written in the
`SimpleBlockCommand` idiom. It compiles against the 0.7.2 jar.

```java
package com.example.blocks;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.arguments.types.RelativeIntPosition;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractWorldCommand;
import com.hypixel.hytale.server.core.universe.world.SetBlockSettings;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.BlockOperations;
import com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.universe.world.storage.GetChunkFlags;
import org.joml.Vector3i;

public class StoneCommand extends AbstractWorldCommand {
    private final RequiredArg<RelativeIntPosition> posArg =
            this.withRequiredArg("x y z", "Block position", ArgTypes.RELATIVE_BLOCK_POSITION);

    public StoneCommand() {
        super("stone", "Replace a block with stone");
    }

    @Override
    protected void execute(CommandContext context, World world, Store<EntityStore> store) {
        Vector3i pos = context.get(this.posArg).getBlockPosition(context, store);
        int x = pos.x;
        int y = pos.y;
        int z = pos.z;
        ChunkStore chunkStore = world.getChunkStore();

        chunkStore.getChunkSectionReferenceAtBlockAsync(x, y, z, GetChunkFlags.SET_TICKING)
                .thenAcceptAsync(sectionRef -> {
                    if (sectionRef == null || !sectionRef.isValid()) {
                        context.sender().sendMessage(Message.raw("No section at that position"));
                        return;
                    }
                    BlockSection blocks = chunkStore.getStore()
                            .getComponent(sectionRef, BlockSection.getComponentType());
                    BlockType previous = BlockType.getAssetMap().getAsset(blocks.get(x, y, z));

                    BlockType stone = BlockType.getAssetMap().getAsset("Rock_Stone");
                    int stoneId = BlockType.getAssetMap().getIndex(stone.getId());
                    BlockOperations.setBlock(chunkStore, sectionRef, x, y, z, stoneId, stone,
                            0, 0, SetBlockSettings.NO_SEND_PARTICLES);

                    context.sender().sendMessage(Message.raw(
                            "Replaced " + previous.getId() + " with " + stone.getId()));
                }, world)
                .exceptionally(t -> {
                    context.sender().sendMessage(Message.raw("Failed to load that section"));
                    return null;
                });
    }
}
```

---

## SectionReader
**Package:** `com.hypixel.hytale.server.core.universe.world.accessor` (0.7.2+)

A synchronous, world-coordinate reader over the sections **already loaded** in a `ChunkStore`. It
resolves each section with `getChunkSectionReferenceAtBlock` and caches the ref by section coordinates,
so a scan over an area resolves each section once. It never loads anything: a block in a section that
is not in memory reads as `0`. Use it on the world thread. It implements the two-method `BlockReader`
interface (`getBlock`, `getFluidId`). The shipped user is `BlockSelection`, which copies a region
through it.

```java
SectionReader(ChunkStore chunkStore)

int getBlock(int x, int y, int z)                    // 0 when the section is not loaded
int getRotationIndex(int x, int y, int z)
int getFiller(int x, int y, int z)
int getSupportValue(int x, int y, int z)             // from the section's BlockPhysics
int getFluidId(int x, int y, int z)                  // same as getWorldFluidId
int getWorldFluidId(int x, int y, int z)
byte getFluidLevel(int x, int y, int z)
int getEnvironment(int x, int y, int z)              // from the section's EnvironmentSection
Holder<ChunkStore> getBlockComponentHolder(int x, int y, int z)   // a copy, or null

Ref<ChunkStore> sectionAt(int x, int y, int z)        // cached section ref, or null
boolean hasStorageInMemory(int x, int y, int z)       // is the block's section loaded?
boolean supportsCubicSections()
boolean canHoldY(int y)                               // cubic, or 0 <= y < 320
SectionReader.SectionCursor sectionCursor()
```

`SectionCursor` is the fast path for walking positions in order: `moveTo(x, y, z)` re-resolves only when
the section changes and returns whether the block's section is loaded, then `block()`, `rotation()`,
`filler()`, `support()`, `fluidId()`, `fluidLevel()` and `holder()` read the current position.

```java
SectionReader reader = new SectionReader(world.getChunkStore());
SectionReader.SectionCursor cursor = reader.sectionCursor();
int air = 0;
for (int y = minY; y <= maxY; y++) {
    if (cursor.moveTo(x, y, z) && cursor.block() == BlockType.EMPTY_ID) {
        air++;
    }
}
```

---

## SetBlockSettings
**Package:** `com.hypixel.hytale.server.core.universe.world`

Bit-flag constants for the `int settings` parameter of `BlockOperations.setBlock` and the
`BlockHarvestUtils` break and damage helpers. Combine with bitwise OR. `NONE` (0) runs the full default
pipeline: most flags *suppress* a side effect, while `PHYSICS`, `FORCE_CHANGED` and
`PERFORM_BLOCK_UPDATE` *opt in* to extra behaviour. The class is unchanged in 0.7.2; what changed is the
method that consumes it.

| Constant | Value | Effect |
|----------|-------|--------|
| `NONE` | 0 | Default behaviour (all side effects; no neighbour update) |
| `NO_NOTIFY` | 1 | Declared, but no reader of the value was found in the 0.7.2 jar |
| `NO_UPDATE_STATE` | 2 | Skip the block-entity swap: the new type's block entity components are not attached or replaced |
| `NO_SEND_PARTICLES` | 4 | Skip break/place particles (the filler change is then recorded as reason `NONE`) |
| `NO_SET_FILLER` | 8 | Do not place filler blocks for a multi-block type |
| `NO_BREAK_FILLER` | 16 | Do not remove the old block's filler blocks |
| `PHYSICS` | 32 | Mark the change as physics-caused (physics break particles; filler change reason `BY_PHYSICS`) |
| `FORCE_CHANGED` | 64 | Run the pipeline even if id and rotation are unchanged (and invalidate the block) |
| `NO_UPDATE_NEIGHBOR_CONNECTIONS` | 128 | Declared, but no reader of the value was found in the 0.7.2 jar |
| `PERFORM_BLOCK_UPDATE` | 256 | Mark the new block's hitbox footprint plus a one-cell margin ticking (the `BlockType`/rotation overload of `BlockOperations.updateBlockArea`) |
| `NO_UPDATE_HEIGHTMAP` | 512 | Skip the heightmap update |
| `NO_SEND_AUDIO` | 1024 | Skip break audio in the `BlockHarvestUtils` paths |
| `NO_DROP_ITEMS` | 2048 | Skip item drops in the `BlockHarvestUtils` paths (they also set it themselves for a non-natural break) |
| `NO_FIRE_ON_BREAK` | 4096 | Skip the broken block's `OnBreak` interaction, despite the fire-sounding name: `BlockHarvestUtils.fireOnBreakInteraction` returns early when the bit is set, and `performBlockBreak` passes the caller's settings straight through to it |

`BlockOperations.setBlock` reads `NO_UPDATE_STATE`, `NO_SEND_PARTICLES`, `NO_SET_FILLER`,
`NO_BREAK_FILLER`, `PHYSICS`, `FORCE_CHANGED`, `PERFORM_BLOCK_UPDATE` and `NO_UPDATE_HEIGHTMAP`;
`BlockHarvestUtils` reads `NO_SEND_AUDIO`, `NO_DROP_ITEMS` and `NO_FIRE_ON_BREAK`. These are
compile-time constants, so the jar reads them as literals (`0x1000` for `NO_FIRE_ON_BREAK`) and a search
for a constant's name finds only its declaration. The two "no reader found" rows come from searching for
the values `1` and `0x80` in settings expressions.

```java
// Replace a block without particles, then wake its neighbours
BlockOperations.setBlock(chunkStore, sectionRef, x, y, z, newId, newType, 0, 0,
        SetBlockSettings.NO_SEND_PARTICLES | SetBlockSettings.PERFORM_BLOCK_UPDATE);
```

---

## Section components

Every component below lives on a section entity, except `HeightmapColumn`, which is on the column.

### ChunkSection

The identity component on each section entity. Extends `Savable`, so `markNeedsSaving()` /
`needsSaving()` / `consumeNeedsSaving()` mark the section for the next save.

```java
static ComponentType<ChunkStore, ChunkSection> getComponentType()

Ref<ChunkStore> getChunkColumnReference()   // the owning column entity
int getX(); int getY(); int getZ()          // section coordinates
boolean shouldKeepLoaded()                  // 0.7.2+: per-section keep-loaded counter
void addKeepLoaded()
void removeKeepLoaded()
int pollKeepAlive(int pollCount)
void resetKeepAlive()
int pollActiveTimer(int pollCount)
void resetActiveTimer()
```

### BlockSection

Palette-compressed block storage for one section: block ids, fillers, rotations, ticking bits and light.
Every `(x, y, z)` method takes world coordinates (masked to the section); the single-`int` forms take a
packed index from `ChunkUtil.indexBlock`.

```java
static ComponentType<ChunkStore, BlockSection> getComponentType()
static final int VERSION   // on-disk section format version (7 in 0.7.2; 6 before)

// Reads
int get(int x, int y, int z)
int get(int index)
int getFiller(int x, int y, int z)
int getRotationIndex(int x, int y, int z)
RotationTuple getRotation(int x, int y, int z)

// Raw writes (no side effects — see BlockOperations)
boolean set(int x, int y, int z, int blockId, int rotation, int filler)
void invalidateBlock(int x, int y, int z)   // force a resend of this block to clients

// Content queries
boolean contains(int blockId)
boolean containsAny(IntList blockIds)
int count()                      // non-air blocks in the section
int count(int blockId)
IntSet values()                  // distinct block ids present
Int2ShortMap valueCounts()
void forEachValue(IntConsumer consumer)
boolean isSolidAir()

// Ticking blocks
boolean setTicking(int x, int y, int z, boolean ticking)
boolean isTicking(int x, int y, int z)
boolean hasTicking()
int getTickingBlocksCount()
void scheduleTick(int index, Instant gameTime)

// Lighting (see ChunkLightData below)
ChunkLightData getLocalLight()
ChunkLightData getGlobalLight()
boolean hasLocalLight()
boolean hasGlobalLight()
void invalidateLocalLight()
void invalidateGlobalLight()

IntOpenHashSet getAndClearChangedPositions()
```

0.7.2 removed `getMaximumHitboxExtent()` and `setChunkSection(...)`.

### FluidSection

Per-section fluid storage: a fluid-type palette plus a per-block level. Read it off the section ref; on
a section without fluids the component can be absent, so check for `null` (`PlaceFluidInteraction`
gives up in that case).

```java
static ComponentType<ChunkStore, FluidSection> getComponentType()

boolean setFluid(int x, int y, int z, Fluid fluid, byte level)
boolean setFluid(int x, int y, int z, int fluidId, byte level)   // fluidId 0 + level 0 clears
Fluid getFluid(int x, int y, int z)
int getFluidId(int x, int y, int z)
byte getFluidLevel(int x, int y, int z)
boolean isEmpty()
int getX(); int getY(); int getZ()   // section coordinates
```

`setFluid` changes only the storage. `PlaceFluidInteraction` follows it with
`blockSection.setTicking(x, y, z, true)` so the fluid starts to flow.

### BlockComponentSection

The section's block-entity storage, keyed by block index (`ChunkUtil.indexBlock`). It holds
the `Holder`s of unloaded block entities and the `Ref`s of loaded ones. `BlockOperations.setBlock`
manages it; for reads, `getBlockReference(index)` returns the live block-entity ref,
`copyBlockHolder(index)` a copy of its holder, and `hasBlockComponents(index)` whether the block has
one. `SectionReader.getBlockComponentHolder(x, y, z)` wraps the copy.

To give a block a specific block-entity holder (what the removed `WorldChunk.setState` did), use
`BlockEntity.setBlockEntity(accessor, sectionRef, blockComponentSection, x, y, z, blockType, rotation,
holder)` (`server.core.modules.block`); `holder == null` removes the block's entity. Every block entity
carries a `BlockModule.BlockStateInfo` whose `getSectionRef()` and `getIndex()` locate it, and
`fillWorldPos(Vector3i)` turns that into world coordinates.

### EnvironmentSection

**0.7.2+.** Per-section environment ids (the `Environment` asset index of each block), replacing the
column-wide `EnvironmentChunk`, which is now `@Deprecated` and kept only so older saves load and migrate.
`BlockChunk.getEnvironmentChunk()` was removed.

```java
static ComponentType<ChunkStore, EnvironmentSection> getComponentType()

int get(int x, int y, int z)
boolean set(int x, int y, int z, int environmentId)
boolean setColumn(int x, int z, int environmentId)
boolean setUniform(int environmentId)
boolean isUniform()
boolean contains(int environmentId)
```

`SectionReader.getEnvironment(x, y, z)` reads it across sections.

### BlockHealthSection

**Package:** `com.hypixel.hytale.server.core.modules.blockhealth` (0.7.2+)

Per-section block durability, replacing `BlockHealthChunk`, which is now `@Deprecated(forRemoval=true)`.
`BlockHealthModule` adds the component to every section (`BlockHealthSystems.EnsureSection`), so
`store.getComponent(sectionRef, BlockHealthSection.getComponentType())` is non-null on a loaded section.
Health is a **fraction**: `1.0` is undamaged, and only damaged or fragile blocks occupy an entry. The
section's `Health` and `Fragility` maps are keyed by block index and saved with the section.

```java
static ComponentType<ChunkStore, BlockHealthSection> getComponentType()

float getHealth(int x, int y, int z)              // 1.0 when undamaged
float damage(int x, int y, int z, float amount, Instant now)   // returns the new health
boolean clearHealth(int index)                    // index = ChunkUtil.indexBlock(x, y, z)
boolean isDamaged(int index)
boolean isFragile(int x, int y, int z)
void makeFragile(int x, int y, int z, float seconds)
void clearFragility(int index)
float getFragilitySeconds(int index)
boolean isEmpty()
```

`damage` records the hit time and queues the change for clients; `BlockHealthSystems.ReplicateChanges`
sends it. A block that reaches zero is not removed by `damage` itself. The engine's damage path,
`BlockHarvestUtils.performBlockDamage`, reads the health, fires `DamageBlockEvent`, calls `damage`,
marks the `ChunkSection` for saving, and breaks the block when it is destroyed or fragile. Regeneration
runs in `BlockHealthSystems.Tick`: 5 seconds after the last hit, health returns at 0.1 per second.
When a block is replaced, `BlockOperations.setBlock` clears its entry
(`BlockHealthModule.onBlockReplaced`). Block-health concepts and the damage event are in
[blocks-java-api.md](blocks-java-api.md#block-health--fragility).

### HeightmapColumn

**0.7.2+.** The column's heightmap, moved off `BlockChunk`. Read the surface height with
`getHeight(x, z)` (world coordinates); it returns `HeightmapColumn.NO_HEIGHT` (`Integer.MIN_VALUE`) where
no height is known.

Which read to use depends on the thread, as for sections. On the world thread,
`ChunkStore.getChunkComponent` is the short form; it goes through `Store.getComponent`, which asserts
the world thread:

```java
// on the world thread (a system, an interaction, a world.execute task, or after thenApplyAsync(..., world))
HeightmapColumn heights = chunkStore.getChunkComponent(
        ChunkUtil.indexChunkFromBlock(x, z), HeightmapColumn.getComponentType());
int top = heights != null ? heights.getHeight(x, z) : HeightmapColumn.NO_HEIGHT;
```

Off the world thread, read through `Store.getComponentConcurrent`, which is safe from any thread. That is
what `FitToHeightMapSpawnProvider` does: a spawn lookup runs on whatever thread asks, often a thread
other than the world thread (see [world.md → Controlling Respawn Location](world.md#controlling-respawn-location)),
so it resolves the column with `getChunkReferenceAsync(index, 32)`
(`HIGH_PRIORITY`), continues with a plain `thenApply` with no hop to the world executor (so the continuation can run on
any thread, including the caller's when the column is already loaded), and reads
the heightmap with `chunkStore.getStore().getComponentConcurrent(chunkRef, HeightmapColumn.getComponentType())`:

```java
// condensed from FitToHeightMapSpawnProvider.getSpawnPointAsync / fit
chunkStore.getChunkReferenceAsync(ChunkUtil.indexChunkFromBlock(x, z), GetChunkFlags.HIGH_PRIORITY)
        .thenApply(chunkRef -> {
            HeightmapColumn heights = chunkRef != null && chunkRef.isValid()
                    ? chunkStore.getStore().getComponentConcurrent(chunkRef, HeightmapColumn.getComponentType())
                    : null;
            return heights != null ? heights.getHeight(x, z) : HeightmapColumn.NO_HEIGHT;
        });
```

`getCollisionHeight(x, z)` is the collision-based variant.

---

## Migrating from 0.6.x

`chunkStore` is `world.getChunkStore()`, `store` is `chunkStore.getStore()`, and `sectionRef` is a
section resolved as in [Resolving a section](#resolving-a-section). Coordinates are world block
coordinates throughout.

| Removed (0.6.8) | 0.7.2 replacement |
|---|---|
| `world.getBlock(x, y, z)`, `chunk.getBlock(...)` | `store.getComponent(sectionRef, BlockSection.getComponentType()).get(x, y, z)`, or `new SectionReader(chunkStore).getBlock(x, y, z)` |
| `world.getBlockType(...)`, `chunk.getBlockType(...)` | `BlockType.getAssetMap().getAsset(blockId)` on the id read above |
| `world.setBlock(x, y, z, "Key"[, settings])`, the `chunk.setBlock` overloads | `BlockOperations.setBlock(chunkStore, sectionRef, x, y, z, id, blockType, rotation, filler, settings)`, with `id = BlockType.getAssetMap().getIndex(key)` |
| `world.breakBlock(x, y, z, settings)`, `chunk.breakBlock(...)` | These only wrote air, so: `BlockOperations.setBlock(chunkStore, sectionRef, x, y, z, 0, BlockType.EMPTY, 0, 0, settings)`. For a break with events, drops and sound, `BlockHarvestUtils.performBlockBreak` |
| `chunk.getFiller`, `chunk.getRotationIndex` | `BlockSection.getFiller(x, y, z)`, `BlockSection.getRotationIndex(x, y, z)` |
| `chunk.setTicking`, `chunk.isTicking` | `BlockSection.setTicking(x, y, z, b)` (then `ChunkSection.markNeedsSaving()`), `BlockSection.isTicking(x, y, z)` |
| `chunk.getHeight(x, z)` | `HeightmapColumn.getHeight(x, z)` on the column (`chunkStore.getChunkComponent(index, HeightmapColumn.getComponentType())`) |
| `chunk.getBlockChunk().getTint(x, z)` | `chunkStore.getChunkComponent(index, BlockChunk.getComponentType()).getTint(x, z)` |
| `world.getFluidId`, `chunk.getFluidId`, `chunk.getFluidLevel` | `FluidSection.getFluidId` / `getFluidLevel`, or `SectionReader.getWorldFluidId` / `getFluidLevel` |
| `chunk.getSupportValue` | `BlockPhysics.get(x, y, z)` on the section, or `SectionReader.getSupportValue` |
| `world.getBlockComponentHolder`, `chunk.getBlockComponentHolder` | `SectionReader.getBlockComponentHolder(x, y, z)` (a copy), or `BlockComponentSection.copyBlockHolder(ChunkUtil.indexBlock(x, y, z))` |
| `chunk.getBlockComponentEntity` | `BlockComponentSection.getBlockReference(ChunkUtil.indexBlock(x, y, z))` |
| `chunk.setState(x, y, z, type, rotation, holder)` | `BlockEntity.setBlockEntity(store, sectionRef, blockComponentSection, x, y, z, type, rotation, holder)` |
| `world.setBlockInteractionState`, `chunk.setBlockInteractionState` | `BlockOperations.setBlockInteractionState(chunkStore, sectionRef, x, y, z, blockType, state, force)` |
| `world.getBaseBlock(position)` | `BlockOperations.resolveBaseBlockPosition(chunkStore, position)` |
| `world.performBlockUpdate(x, y, z)` | `BlockOperations.updateBlockArea(chunkStore, chunkSection, blockSection, x, y, z)` |
| `LocalCachedChunkAccessor`, `world.getBlockBulkRelative` | `SectionReader` and its `SectionCursor` for reads; one `BlockOperations.setBlock` per block for writes |
| `world.getChunkIfLoaded(index)`, `getChunkIfInMemory`, `getChunkIfNonTicking`, `loadChunkIfInMemory` | `chunkStore.getChunkReference(index)` or `chunkStore.getChunkComponent(index, WorldChunk.getComponentType())` |
| `world.getChunkAsync(index)` | `chunkStore.getChunkReferenceAsync(index, GetChunkFlags.SET_TICKING)` (what it called internally) |
| `world.getNonTickingChunkAsync(index)` | `chunkStore.getChunkReferenceAsync(index)` |
| `chunk.getWorld()` | `chunkStore.getWorld()` |
| `chunk.getBlockChunk()` | `store.getComponent(chunkRef, BlockChunk.getComponentType())` |
| `ChunkFlag.TICKING` (removed) | the absence of the `NonTicking` marker (`ChunkStore.REGISTRY.getNonTickingComponentType()`) on the column or section |
| `BlockHealthChunk` | `BlockHealthSection` |
| `EnvironmentChunk`, `BlockChunk.getEnvironmentChunk()` (removed) | `EnvironmentSection`, or `SectionReader.getEnvironment(x, y, z)` |

---

## Gotchas & Errors

- **`Assert not in thread!`** → a `ChunkStore` component was read or written off the world thread,
  typically inside a `thenAccept` on a section future. Fix: continue with
  `thenAcceptAsync(..., world)`.
- **A block read returns `0` (air) where there is clearly a block** → the section was not loaded.
  `getChunkSectionReferenceAtBlock` and `SectionReader` never load; use
  `getChunkSectionReferenceAtBlockAsync` when the area may be unloaded.
- **A write "works" but the block reverts, has no light, or keeps a stale block entity** → it went
  through `BlockSection.set`, which is the raw palette write. Use `BlockOperations.setBlock`.
- **A ticking bit set by hand is lost on reload** → mark the section dirty:
  `ChunkSection.markNeedsSaving()` after `BlockSection.setTicking` returns `true`.
- **A section lookup above y 319 (or below 0) completes with `null`** → the world cannot supply that
  section. Which half is missing decides the fix:
    - loading a stored off-range section needs a cubic **loader** (`IChunkLoader.Cubic`; in 0.7.2 the
      `RocksDb` storage provider), and
    - generating a new one needs a cubic loader **and** a cubic generator (`IWorldGen.Cubic`).

    `SectionReader.canHoldY(y)` answers neither question, since it is `true` when either half is cubic.
    A cubic loader with the default generator, or the default storage with `CubicTestWorldGenProvider`,
    both report `canHoldY(400) == true`, and both return `null` at y 400 for a section that was never
    stored there.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
