---
title: "World Generation"
description: "Hytale world generation in JSON node graphs — the typed node-graph model, density graphs driving terrain height, cave carving and biome selection, and material providers."
seo:
  type: TechArticle
---

# World Generation

**Doc type:** Java API + JSON asset format · **Assets:** `Server/HytaleGenerator` · **Verified against 0.6.3**

Hytale's world generator is a **node-graph system**. Terrain height, cave carving,
material placement, biome selection, tinting, and prop scattering are all expressed as
trees of typed nodes that are evaluated per world position. There is no imperative
"populator pipeline" in the assets — instead, each generation concern is a graph whose
leaves are noise/constant sources and whose root produces a value (a density, a material,
a tint, a set of positions, etc.).

All world-generation assets live under:

```
Server/HytaleGenerator/
```

> The canonical asset root is `Server/HytaleGenerator/` — **not** `Server/WorldGen/`.

## Overview

Defined as JSON node-graph assets under `Server/HytaleGenerator/` and provides:
- A typed node-graph model (every node has a `Type` plus child `Inputs`)
- Density graphs that drive terrain height, cave carving, and biome selection
- Material providers that turn density into block ids (solid vs. empty)
- Prop/placement graphs for scattering props and prefabs
- Environment and tint selection per biome
- Reuse across graphs via `ExportAs` / `Imported`

## Architecture
```
Server/HytaleGenerator/
├── WorldStructures/   maps a density value -> biomes; world constants (Framework)
│   └── Density "Biome-Map"  (which biome appears where)
├── Biomes/            per-biome graphs
│   ├── Terrain (DAOTerrain) -> Density graph (heightfield)
│   ├── MaterialProvider (Solidity: Solid / Empty branches)
│   ├── Props[]  -> Positions + Assignments
│   ├── EnvironmentProvider / TintProvider
│   └── pull shared fields via Imported
├── Density/           shared density graphs (Biome-Map, cave fields)
├── Assignments/       prop/prefab placement graphs (imported by biome Props)
├── Positions/ · PropDistributions/ · Props/   standalone placement graphs
├── BlockMasks/        block-set placement filters
├── GraphGenerators/ · GraphPasses/ · GraphContentSuppliers/ · GraphContentPredicates/
│                      graph-generator assets (roads, rivers, roots — see below)
└── Settings/          generator runtime settings (Settings.json)
```

## Key Classes
These are JSON worldgen node types (not Java classes); the table lists the key node types documented on this page.

| Node type | Family | Description |
|-----------|--------|-------------|
| `SimplexNoise2D` / `CellNoise2D` | Density source | Noise fields (the core scalar sources) |
| `BaseHeight` | Density source | Injects a named world reference height (`Base`, `Water`, `Bedrock`) |
| `Imported` / `Exported` | Reuse | Pull / publish a field by name across graphs |
| `Sum` / `Min` / `Max` / `Mix` | Density combiner | Combine input fields |
| `CurveMapper` / `Normalizer` / `Clamp` / `Pow` / `Abs` | Density shaping | Remap or reshape a field |
| `Solidity` | Material provider | Splits placement into `Solid` and `Empty` branches |
| `Queue` / `SimpleHorizontal` / `SpaceAndDepth` / `FieldFunction` | Material provider | Select which block fills a cell |
| `Mesh2D` / `Occurrence` | Prop positions | Candidate point grids and probability gating |
| `Weighted` / `Cluster` / `Constant` | Prop assignment | Choose / group what to place |
| `Prefab` / `Column` | Prop | Place a prefab structure or a block stack |
| `DensityDelimited` | Provider/selection | Pick environment/tint by density range |

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Biomes](worldgen-biomes.md) | `worldgen-biomes.md` | Biome files: `Terrain`, `MaterialProvider`, `Props`, environment, tint |
| [Zones / World Structures](worldgen-zones.md) | `worldgen-zones.md` | `WorldStructures/*.json`: biome assignment by noise range, framework |
| [Terrain & Density](worldgen-terrain.md) | `worldgen-terrain.md` | Building heightfields out of density graphs |
| [Caves](worldgen-caves.md) | `worldgen-caves.md` | Carving cave systems with 3D density fields |
| [Worldgen Prefabs](worldgen-prefabs.md) | `worldgen-prefabs.md` | Placing prefabs and props from generation graphs |

---

## Asset Layout

```
Server/HytaleGenerator/
├── Biomes/             # Biome definitions (Terrain + MaterialProvider + Props + ...)
│   ├── Plains1/        #   grouped by zone family (Plains1, Desert1, Taiga1, Volcanic1, ...)
│   ├── Examples/       #   small documented graphs demonstrating single node types
│   └── Experimental/
├── WorldStructures/    # "Zone" equivalents: which biomes appear, keyed by a density value
│   ├── Zone1_Plains1.json
│   ├── Zone2_Desert1.json
│   └── Portals_*.json
├── Assignments/        # Prop / prefab placement graphs imported by biome `Props`
│   └── Plains1/Plains1_Oak_Trees.json ...
├── Density/            # Shared density graphs (e.g. the world `Biome-Map`, cave fields)
├── BlockMasks/         # Block-set masks
├── Positions/          # Standalone position graphs
├── PropDistributions/  # Standalone prop-distribution graphs
├── Props/              # Standalone prop graphs
├── GraphGenerators/    # Graph-generator assets (node/edge graphs for roads, rivers, roots …)
├── GraphPasses/        #   … their passes, content suppliers and content predicates
├── GraphContentSuppliers/
├── GraphContentPredicates/
└── Settings/           # Generator runtime settings (Settings.json)
```

(The former `Graphs/` folder — a single `ExampleGraph.json` — is gone as of 0.6.3,
replaced by the four `Graph*/` folders above, each shipping one `Example*.json`.
`Positions/`, `PropDistributions/` and `Props/` are unchanged single-example folders.)

How the pieces fit together:

- A **WorldStructure** (`WorldStructures/*.json`) maps a density value to a list of
  **biomes** and defines world-wide constants (sea level, bedrock, base height).
- Each **biome** (`Biomes/.../*.json`) owns a `Terrain` density graph (the heightfield),
  a `MaterialProvider` (which blocks fill solid vs. empty space), optional `Props`
  (which reference **assignment** graphs), and optional environment/tint providers.
- **Density** graphs and **Assignments** can be shared and pulled in by name through
  `Imported` nodes, so a biome can reuse the world `Biome-Map`, cave fields, or a prop
  placement defined once elsewhere.

---

## The Node-Graph Model

Every node is a JSON object that carries a `Type` and an identity. Two identity styles
appear in the assets, and both are valid input to the generator:

- **`$NodeId`** — a stable id string, e.g. `"$NodeId": "SimplexNoise2DDensityNode-f2c2..."`.
  Files saved by the tooling also carry a `$NodeEditorMetadata` block (node positions,
  groups, comments). Editor-only keys are prefixed with `$`.
- **`$Position` / `$Title`** — used by editor-exported files instead of `$NodeId`.

Editor-only metadata (`$NodeId`, `$Position` — an `{"$x","$y"}` pair — `$Title`,
`$NodeEditorMetadata` and its `$Nodes`/`$Links`/`$FloatingNodes`/`$Comments`,
`$WorkspaceID`, `$Groups`, `$Comment`) does not affect
generation; the load-bearing fields are `Type`, the node's parameters, and its child
node references (commonly under `Inputs`).

A minimal density node:

```json
{
  "Type": "SimplexNoise2D",
  "Skip": false,
  "Lacunarity": 5,
  "Persistence": 0.08,
  "Octaves": 3,
  "Scale": 400,
  "Seed": "Plains1_Oak"
}
```

### Common conventions

| Key | Meaning |
|-----|---------|
| `Type` | The node kind. Required on every node. |
| `Inputs` | Array of child density nodes feeding this node. |
| `Skip` | `true` bypasses the node (passes its input through). Common on density nodes. |
| `ExportAs` | Publishes this node's output under a name so other graphs can pull it. |
| `Name` | On an `Imported` node, the name of the value to pull in. |
| `Seed` | A **string** label (e.g. `"A"`, `"Plains1_Oak"`, `"1235"`), not a numeric seed. |

### Noise parameters

Noise nodes (`SimplexNoise2D`, `CellNoise2D`, …) share these parameters:

| Parameter | Description |
|-----------|-------------|
| `Lacunarity` | Frequency multiplier between octaves |
| `Persistence` | Amplitude falloff between octaves |
| `Octaves` | Number of noise layers summed |
| `Scale` | Feature size (larger = broader features) |
| `Seed` | String label that differentiates noise instances |

`CellNoise2D` additionally uses `ScaleX`/`ScaleZ`, `Jitter`, and `CellType`
(e.g. `"Distance2Div"`).

---

## Node Families

Nodes are organized by the value they produce.

### Density nodes (the core)

Density graphs produce a scalar field. They drive terrain height, cave carving, biome
maps, prop probability, and tint/environment selection.

**Sources**

| Type | Description |
|------|-------------|
| `SimplexNoise2D` | 2D Simplex/fractal noise (`Lacunarity`, `Persistence`, `Octaves`, `Scale`, `Seed`) |
| `CellNoise2D` | Cellular/Worley noise (`ScaleX`, `ScaleZ`, `Jitter`, `CellType`, `Octaves`, `Seed`) |
| `Constant` | Fixed `Value` |
| `BaseHeight` | A named world reference height (`BaseHeightName`: `"Base"`, `"Water"` or `"Bedrock"`, declared by the world structure's `DecimalConstants`; plus a `Distance` flag) |
| `Imported` | Pulls a value exported elsewhere by `Name` (e.g. `"Biome-Map"`) |
| `Exported` | Wraps a subgraph and publishes it (`ExportAs`, optional `SingleInstance`) |

**Combiners**

| Type | Description |
|------|-------------|
| `Sum` | Adds its `Inputs` |
| `Min` / `Max` | Lower / upper envelope of `Inputs` |
| `Mix` | Linear blend of exactly **three** `Inputs`: `A`, `B`, and an influence field — `≤ 0` gives `A`, `≥ 1` gives `B`, in between `A·(1−t) + B·t`. Any other input count silently yields constant `0`. |
| `Abs` | Absolute value |
| `Pow` | Raises input to `Exponent` |
| `Inverter` | Negates |
| `Normalizer` | Remaps `FromMin`..`FromMax` to `ToMin`..`ToMax` |
| `Clamp` | Clamps between `WallA` and `WallB` |
| `Scale` | Scales coordinates (`ScaleX`/`ScaleY`/`ScaleZ`) |
| `Cache` | Memoizes its input (`Capacity`) for reuse |
| `YOverride` | Forces a constant Y when sampling (`Value`) — makes a field 2D |
| `CurveMapper` | Remaps a value through a `Curve` (a `Manual` curve of `In`/`Out` `Points`) |
| `Distance` | Distance-based falloff via a `Curve` |

The tables above cover the types the shipped biomes lean on. The full density vocabulary
registered by the generator (as of 0.6.3, `DensityAsset.CODEC` registrations in
`com.hypixel.hytale.builtin.hytalegenerator.assets.AssetManager`) is larger — comparators
and logic (`Comparator`, `Equal`, `GreaterThan`, `GreaterOrEqual`, `LessThan`,
`LessOrEqual`, `And`, `Or`, `Not`, `Nor`, `Xor`, `Selector`, `Switch`, `SwitchState`),
smooth variants (`SmoothMin`, `SmoothMax`, `SmoothClamp`, `SmoothFloor`, `SmoothCeiling`,
`Floor`, `Ceiling`), more math (`Sqrt`, `Multiplier`, `Amplitude`, `AmplitudeConstant`,
`Offset`, `OffsetConstant`, `Trig`, `Pipeline`, `MultiMix`), coordinate access
(`XValue`/`YValue`/`ZValue`, `XOverride`/`ZOverride`, `YSampled`, `Axis`, `Plane`,
`Rotator`, `Angle`), shapes (`Cube`, `Cuboid`, `Cylinder`, `Ellipsoid`, `Shell`, `Anchor`),
more noise (`SimplexNoise3D`, `CellNoise3D`, `WhiteNoise`, `GradientWarp`,
`FastGradientWarp`, `VectorWarp`, `Gradient`, `Slider`), position-driven fields
(`PositionsCellNoise`, `Positions3D`, `PositionsPinch`, `PositionsTwist`,
`CellWallDistance`), and graph/biome-aware fields (`Terrain`, `Graph`,
`DistanceToBiomeEdge`, `DistanceToGraphEdge`). `Cache2D` is a deprecated alias for
`Cache`. Every node accepts the shared `Inputs`, `Skip`, and `ExportAs` keys.

### Material providers

A biome's `MaterialProvider` decides which block fills each cell. The top-level type used
by terrain biomes is `Solidity` (it has separate `Solid` and `Empty` branches).

| Type | Description |
|------|-------------|
| `Solidity` | Splits placement into `Solid` and `Empty` (required) branches |
| `Constant` | Always places one `Material` |
| `Queue` | Tries providers in order; first match wins |
| `SimpleHorizontal` | Applies a nested `Material` provider within a Y band (`TopY`/`BottomY`, all three required; optional `TopBaseHeight`/`BottomBaseHeight` name the reference heights the band is measured from) |
| `SpaceAndDepth` | Layers materials by depth into the floor (`Layers`, `LayerContext`, `MaxExpectedDepth`, `Condition`) |
| `FieldFunction` | Selects materials by sampling a density `FieldFunction` against `Delimiters` (each `From`/`To`/`Material`) |

A `Material` is a leaf (`MaterialAsset`) with a block id, e.g. `{"Solid": "Rock_Stone"}`,
`{"Solid": "Soil_Dirt"}`, `{"Solid": "Empty"}`, or a fluid `{"Fluid": "Water_Source"}`.
`Solid` and `Fluid` are independent — a cell can carry both — and two optional keys rotate
the solid:

| Key | Meaning |
|-----|---------|
| `SolidBottomUp` | Boolean. Applies a 180° **pitch** (`RotationTuple.of(None, OneEighty, None)`), i.e. places the block upside-down. Widely used in the shipped biomes (stalactites, hanging vines). |
| `SolidRotation` | An explicit orthogonal rotation: `{"Yaw": …, "Pitch": …, "Roll": …}`, each a `Rotation` enum name. Takes precedence — if it is anything but all-`None`, `SolidBottomUp` is ignored. |

Because `MaterialAsset` is an *asset* codec, a `Material` value may equally be the id
string of a standalone material asset instead of an inline object.

### Provider / selection nodes

| Type | Description |
|------|-------------|
| `Constant` (Environment) | `{"Type":"Constant","Environment":"Env_Zone1_Plains"}` |
| `Constant` (Tint) | `{"Type":"Constant","Color":"#5b9e28"}` |
| `DensityDelimited` | Picks an environment/tint by which `Range` a `Density` value falls into |

### Prop / placement nodes

Used inside biome `Props` and in `Assignments/*.json`:

| Type | Description |
|------|-------------|
| `Mesh2D` | Position provider: a point grid (`PointGenerator`, `PointsY`) |
| `Mesh` | The point generator `Mesh2D` nests (`Jitter`, `ScaleX`/`ScaleY`/`ScaleZ`, `Seed`) |
| `Occurrence` | Gates `Positions` by a probability `FieldFunction` (plus `Seed`) |
| `FieldFunction` | Maps a density field to assignments via `Delimiters` (`Min`/`Max`/`Assignments`) |
| `Weighted` | Random weighted choice among `WeightedAssignments` (plus `SkipChance`, `Seed`) |
| `Cluster` | Spawns grouped props (`Range`, `DistanceCurve`, `WeightedProps`, `Pattern`, `Scanner`) |
| `Constant` (Assignments) | Always assigns one `Prop` |
| `Prefab` | Places prefab(s) by path (`WeightedPrefabPaths` of `Weight`/`Path`; also `Directionality`, `Scanner`, `BlockMask`, `LoadEntities`) |
| `Column` | Places a stack of blocks (`ColumnBlocks`, `Material`, `Y`, `Scanner`, `BlockMask`, `Directionality`) |
| `Imported` | Pulls an assignment/positions graph by `Name` |

---

## Settings

`Server/HytaleGenerator/Settings/Settings.json` holds generator runtime settings, e.g.:

```json
{
  "StatsCheckpoints": [1, 100, 500, 1000],
  "LowPriorityConcurrency": 0,
  "NormalPriorityConcurrency": 0,
  "HighPriorityConcurrency": 0,
  "BufferCapacityFactor": 0.15,
  "TargetViewDistance": 512,
  "TargetPlayerCount": 3
}
```

These are the shipped values (codec:
`com.hypixel.hytale.builtin.hytalegenerator.assets.SettingsAsset`). The three
`*PriorityConcurrency` keys size the generator's low/normal/high-priority worker pools; a
value `> 0` is used as-is, while `0` (`HytaleGenerator.AUTO_CONCURRENCY_LEVEL`, the shipped
value) means *auto* — the plugin picks a default per CPU count
(`HytaleGenerator.getDefaultConcurrency()`). The in-game
`/worldgen2 concurrency <low> <normal> <high>` command overrides them at runtime; unlike
the settings values, an override *is* capped to `Runtime.availableProcessors()`.
`BufferCapacityFactor`, `TargetViewDistance`, and `TargetPlayerCount` size the
chunk-request buffers. (0.5.9's single concurrency setting — `SettingsAsset`'s
`customConcurrency` field — is gone as of 0.6.3, split into the three priority keys.)

---

## Reading the Assets

The smallest, most readable graphs are under `Biomes/Examples/` (each demonstrates one
idea, e.g. `Example_CellNoise2D.json`, `Example_Curve_Mapper.json`, `Example_Mixer.json`).
Production biomes such as `Biomes/Plains1/Plains1_Oak.json` are large because every node
in the chain is inlined. To find a specific concept, search for a `Type` value across the
folder rather than reading a whole file top to bottom.

---

## Java World Generator API

**Package:** `com.hypixel.hytale.server.core.universe.world.worldgen` (+ `.provider`)

Everything above is JSON consumed by the shipped `HytaleGenerator` plugin. Underneath it
the server defines a small Java abstraction that a plugin can implement to ship its own
generator: an `IWorldGenProvider` (the config/codec side, selected by the `WorldGen`
block in a world's `config.json` — see [Universe & Saves](universe-saves.md)) produces an
`IWorldGen` (the runtime side, called per chunk).

### IWorldGen

The runtime generator interface. One instance serves a world; `generate` is called once
per chunk column (32×32 blocks).

```java
CompletableFuture<GeneratedChunk> generate(int seed, long index, int x, int z,
                                           LongPredicate stillNeeded,
                                           Long2FloatFunction priority)
WorldGenTimingsCollector getTimings()          // @Nullable — may return null
Transform[] getSpawnPoints(int seed)           // @Deprecated
ISpawnProvider getDefaultSpawnProvider(int seed)  // default method
void shutdown()                                // default method, no-op
```

- `index` is the packed chunk index; `x`/`z` are chunk coordinates. `stillNeeded` (may be
  `null`) lets a slow generator skip chunks nobody is waiting on anymore.
- `priority` (added as of 0.6.3; may be `null`) maps a packed chunk index to a scheduling
  priority — the `ChunkStore` passes the distance-based column priority of the nearest
  player tracking that chunk (`-1` for chunks flagged urgent), so a queued generator can
  serve nearby chunks first. `Float.MAX_VALUE` (`SectionPriority.LOWEST_PRIORITY`) is the
  "nobody is waiting" value.
- The default `getDefaultSpawnProvider(int)` wraps `getSpawnPoints(int)` in a
  `FitToHeightMapSpawnProvider`.
- A sub-interface `IWorldGen.Cubic` (new as of 0.6.3) adds a per-*section* entry point,
  `generate(int seed, int x, int y, int z, IWorldGen.StillNeededSection,
  IWorldGen.SectionPriority)`, returning a `CompletableFuture<Holder<ChunkStore>>` for one
  32³ section; the chunk store uses it when the world runs in cubic-section mode
  (`ChunkStore.supportsCubicSections()`). Both callback interfaces are nested in
  `IWorldGen`: `StillNeededSection.test(int x, int y, int z)` and
  `SectionPriority.fetchPriority(int x, int y, int z)`.
- The world's active generator hangs off the chunk store:
  `world.getChunkStore()` → `ChunkStore.getGenerator()` / `setGenerator(IWorldGen)` /
  `shutdownGenerator()`.

### IWorldGenProvider

The config-side factory, decoded from the `WorldGen` block of a world's `config.json`.

```java
// com.hypixel.hytale.server.core.universe.world.worldgen.provider.IWorldGenProvider
static final BuilderCodecMapCodec<IWorldGenProvider> CODEC;   // keyed by "Type"
IWorldGen getGenerator() throws WorldGenLoadException
```

Registered `Type` values (as of 0.6.3):

| `Type` | Provider class | Registered by |
|--------|----------------|---------------|
| `Flat` | `FlatWorldGenProvider` | core (`Universe`) |
| `Void` | `VoidWorldGenProvider` | core (`Universe`) |
| `Dummy` | `DummyWorldGenProvider` (internal no-op) | core (`Universe`) |
| `CubicTest` | `CubicTestWorldGenProvider` (new as of 0.6.3; a fixed test platform with scattered prefabs, used by the shipped `Instances/CubicTest`) | core (`Universe`) |
| `HytaleGenerator` | the node-graph generator documented on this page | `HytaleGenerator` plugin |
| `Hytale` | `HytaleWorldGenProvider` — the legacy folder-of-JSON generator; keys `Name` (default `"Default"`), `Version` (a semver, default `0.0.0`) and `Path` (defaults to the server's world-gen folder) | `WorldGenPlugin` |

A plugin registers its own provider type on the shared codec, the same way the built-ins
do:

```java
IWorldGenProvider.CODEC.register("MyGen", MyProvider.class, MyProvider.CODEC);
```

After that, `"WorldGen": { "Type": "MyGen", ... }` in a world's `config.json` decodes to
your provider; at runtime it is reachable via
`world.getWorldConfig().getWorldGenProvider()` (and swappable with
`setWorldGenProvider(...)` on the same `WorldConfig`).

### FlatWorldGenProvider (`Type: "Flat"`)

Generates a flat world from a list of layers. Codec fields: `Tint` (a color, default
`DEFAULT_TINT`) and `Layers` (required array). Each `Layer` carries:

| JSON key | Field | Meaning |
|----------|-------|---------|
| `From` | `int from` | Bottom Y of the layer (inclusive; clamped to ≥ 0) |
| `To` | `int to` | Top Y of the layer (**exclusive**; clamped to ≤ 320, and validated `> From`) |
| `BlockType` | `String blockType` | Block asset id to fill with |
| `Environment` | `String environment` | Environment asset id for the layer |

```json
"WorldGen": {
  "Type": "Flat",
  "Layers": [ { "From": 0, "To": 3, "BlockType": "Rock_Stone" } ]
}
```

`getGenerator()` throws `WorldGenLoadException` if a layer has `To` ≤ `From`
(`Failed to load 'Flat' WorldGen config, 'To' must be greater than 'From':`) or an
unknown `BlockType`/`Environment` id (`Unknown key!`).

### VoidWorldGenProvider (`Type: "Void"`)

Generates empty chunks, optionally applying a `Tint` (color) and an `Environment`
(environment asset id, validated — unknown ids throw `WorldGenLoadException` with
`Unknown key!`) to every generated column.

### GeneratedChunk and its buffers

`generate(...)` resolves to a `GeneratedChunk`: a block buffer, an entity buffer, and the
array of per-section `ChunkStore` holders (block-state entities such as chests and signs
are written straight into those section holders), which the server converts into a live
chunk:

```java
GeneratedChunk(GeneratedBlockChunk, GeneratedEntityChunk, Holder<ChunkStore>[] sections)
GeneratedBlockChunk getBlockChunk()
GeneratedEntityChunk getEntityChunk()
Holder<ChunkStore>[] getSections()
Holder<ChunkStore> getState(int x, int y, int z)            // @Nullable
void setState(int x, int y, int z, Holder<ChunkStore> state) // state may be null (= remove)
Holder<ChunkStore> toWorldChunk(World world)                // builds the live chunk holder
Holder<ChunkStore> toHolder(World world)                    // alias of toWorldChunk
static Holder<ChunkStore>[] makeSections()                  // 10 fresh section holders
```

(`GeneratedBlockStateChunk` — the separate block-state buffer of 0.5.9, with its
`toBlockComponentChunk()` — was removed by 0.6.3; `getState`/`setState` moved onto
`GeneratedChunk` itself and address the `BlockComponentSection` of the matching section
holder.)

**`GeneratedBlockChunk`** — the block/tint/environment buffer for one column:

```java
GeneratedBlockChunk(long index, int x, int z)
void setBlock(int x, int y, int z, int blockId, int rotation, int filler)
int getBlock(int x, int y, int z)
int getRotationIndex(int x, int y, int z)
void setTint(int x, int z, int tint)               // per-column tint index
int getTint(int x, int z)
void setEnvironment(int x, int y, int z, int environment)
void setEnvironmentColumn(int x, int z, int environment)
int getEnvironment(int x, int y, int z)
int getHeight(int x, int z)
GeneratedChunkSection getSection(int sectionIndex)   // per-section block buffer
void removeSection(int sectionIndex)
EnvironmentChunk getEnvironmentChunk()
BlockChunk toBlockChunk(Holder<ChunkStore>[] sectionHolders)
```

**`GeneratedEntityChunk`** — entities to spawn with the chunk (e.g. from prefabs):

```java
void addEntities(Vector3i offset, PrefabRotation rotation,
                 Holder<EntityStore>[] entityHolders, int objectId, int prefabInstanceId)
void forEachEntity(Consumer<GeneratedEntityChunk.EntityWrapperEntry> consumer)
List<GeneratedEntityChunk.EntityWrapperEntry> getEntities()
void toEntitySections(Holder<ChunkStore>[] sections)   // applies rotation, writes into sections
```

(`toEntityChunk()` was removed by 0.6.3 — entities are now written into the per-section
holders by `toEntitySections`, which `GeneratedChunk.toWorldChunk` calls for you.)

### WorldGenTimingsCollector

Optional per-generator timing metrics, returned by `IWorldGen.getTimings()` (nullable).
A generator reports phase durations in nanoseconds; the collector exposes rolling
averages in seconds:

```java
WorldGenTimingsCollector(ThreadPoolExecutor threadPoolExecutor)
double reportChunk(long nanos)             // also: reportZoneBiomeResult, reportPrepare,
                                           // reportBlocksGeneration, reportCaveGeneration,
                                           // reportPrefabGeneration
double getChunkTime()                      // avg seconds/chunk
long getChunkCounter()
int getQueueLength()                       // from the executor
int getGeneratingCount()
```

### WorldGenLoadException

Checked exception thrown by `IWorldGenProvider.getGenerator()` when a generator cannot
be built (bad config, unknown asset ids):

```java
WorldGenLoadException(String message)
WorldGenLoadException(String message, Throwable cause)
String getTraceMessage()
String getTraceMessage(String joiner)   // 0.6.3+ (the no-arg form joins with ", ")
```

### WorldGenChunksClearedEvent

**Package:** `com.hypixel.hytale.server.core.universe.world.events`

Fired (keyed by world name) by the `/worldgen reload` command's *clear* path after all
saved chunks of a world have been deleted and before the loaded ones are regenerated —
the signal that any plugin state tied to old worldgen output (markers, cached positions)
is now stale. Extends `WorldEvent`; the only accessor is the inherited `getWorld()`. Not
cancellable. The shipped trigger-volumes plugin listens to it to drop volumes created by
worldgen.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the world-generator loaders (verified against `HytaleServer.jar`).

All three come from the **legacy `Type: "Hytale"` provider** (`HytaleWorldGenProvider` +
`ChunkGeneratorJsonLoader`), which loads a folder of JSON under a `Path`/`Name`/`Version`
config — *not* from the `HytaleGenerator` node-graph assets this page documents. The
node-graph generator loads through the asset codecs instead, so a malformed node there
surfaces as a codec/asset-store error naming the offending key.

- **`Invalid world gen name:`** → the `Name` in a `Type: "Hytale"` `WorldGen` block did not resolve to a directory inside the world-gen path. Fix: use a generator folder name that exists under the configured `Path` (or `Universe.getWorldGenPath()`).
- **`World gen path must be within a trusted directory:`** → the `Path` key of a `Type: "Hytale"` `WorldGen` block points outside the server's trusted roots (`PathUtil.isInTrustedRoot`). Fix: keep the folder inside the server directory, or drop `Path` to use the default world-gen folder.
- **Symptom:** a node fails to load with a `Property … must be of type …` message (`procedurallib.json.JsonLoader`) → a node parameter in a legacy generator's JSON has the wrong type (e.g. a string where a number is expected). Fix: match the parameter to its declared type; the load-bearing fields on every node are `Type`, its parameters, and child references under `Inputs` (see [The Node-Graph Model](#the-node-graph-model)).

---

## Related Documentation

- [Biomes](worldgen-biomes.md) — biome file structure
- [Zones / World Structures](worldgen-zones.md) — biome assignment and world framework
- [Terrain Density Graphs](worldgen-terrain.md) — the density vocabulary in depth
- [Caves](worldgen-caves.md) — carving with density fields
- [Props & Structure Placement](worldgen-prefabs.md) — prop, prefab and assignment graphs
- [Block System](blocks.md) — block ids used as materials
