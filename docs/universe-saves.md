---
title: "Universes & Save Format"
description: "How a Hytale save is structured for a dedicated server — the universe/worlds layout, the per-world config.json that binds a world to a worldgen WorldStructure, the server config.json (Defaults.World spawn selection, IsPvpEnabled), how the creative crossroads is the CreativeHub plugin, and the workflow for moving a creative-authored world onto a dedicated server."
seo:
  type: TechArticle
---

# Universes & Save Format

**Doc type:** Save / config file format · **Files:** `UserData/Saves/<save>/` · **Verified against 0.5.9**

A Hytale **save is a universe of worlds**. When you host a dedicated server you point it at a
save directory; that directory *is* the universe. This page documents the on-disk layout, the
two `config.json` files (server-level and per-world), how a world is bound to a worldgen
[WorldStructure](worldgen-zones.md), how the server chooses the spawn world, and why the
creative "crossroads" hub appears.

Most of this is **not** covered by the [World API](world.md) page, which documents the
*runtime* `World` object rather than the save format that produces it.

## Overview

A save under `UserData/Saves/<save>/` provides:
- A **server/save `config.json`** at the save root (the `HytaleServerConfig`)
- A **`universe/`** holding per-player data and a `worlds/` directory
- One **`worlds/<name>/`** directory per world, each with its own `config.json`
- A per-world binding to either a procedural [WorldStructure](worldgen-zones.md) or a fixed
  named generator

## Architecture
```
UserData/Saves/<save>/
├── config.json              HytaleServerConfig: server name, mods, backups, Defaults (spawn world)
├── permissions.json · bans.json · whitelist.json
└── universe/
    ├── players/<uuid>.json  per-player; PlayerData.World = current world, PerWorldData[...]
    ├── resources/          0.6.3+: universe-scoped resources (Memories.json, GameFlags.json, Hardcore.json)
    └── worlds/
        └── <world-name>/    keyed by folder name in Universe.worlds
            ├── config.json   the world definition (WorldGen, SpawnProvider, IsPvpEnabled, ...)
            ├── chunks/        block data
            ├── resources/     world-scoped resources
            └── instance.bson  world metadata
```

> As of 0.6.3 the adventure "memories" file moved from `universe/memories.json` into the new
> `universe/resources/` directory as `Memories.json`. The move is automatic on first boot
> (`MemoriesPlugin` migrates the legacy file *and* its `.bak`), but only when the universe resource
> storage is still disk-backed — a custom `UniverseResourceStorage` logs
> `Legacy memories file memories.json cannot migrate to a custom universe resource storage` and
> leaves the old file alone. See [Universe resources](#universe-resources).

## The save / server `config.json`

The file at the **save root**, `config.json`, is the `HytaleServerConfig`
(`com.hypixel.hytale.server.core.HytaleServerConfig`, its `PATH` is literally `"config.json"`).
The same file serves a singleplayer save and a dedicated server — the server is run pointed at
the save directory.

A creative singleplayer save writes only a subset:

```json
{
  "Backup": { "Enabled": true, "FrequencyMinutes": 30, "Directory": "backup", "MaxCount": 5, "ArchiveMaxCount": 5 },
  "Version": 4,
  "Mods": { "author-id:Example Mod": { "Enabled": true } }
}
```

Top-level keys the config codec recognizes (capitalization exact):

| Key | Description |
|-----|-------------|
| `ServerName` | Dedicated-server display name |
| `MOTD` | Message of the day |
| `Password` | Join password (empty = none) |
| `MaxPlayers` | Player cap |
| `MaxViewRadius` | Max chunk view radius |
| `Mods` | Map of `mod-id → { "Enabled": bool }` |
| `Modules` | Built-in module toggles |
| `DefaultModsEnabled` | Whether bundled mods default on |
| `Backup` | Auto-backup settings |
| **`Defaults`** | **Default world + game mode for joining players (see below)** |
| `WorldMap` · `PlayerStorage` · `LogLevels` | World-map, player-storage, and logging config |
| `RequireJoinPermission` | 0.6.3+: when `true`, only players holding the join permission can connect (bool) |
| `UniverseResourceStorage` · `BanStorage` | 0.6.3+: storage-provider blocks for universe-level resources (see [Universe resources](#universe-resources)) and the ban list (`{ "Type": ... }`, like the per-world `ChunkStorage`) |
| `ConnectionTimeouts` · `RateLimit` · `ModLoadOrder` · `AuthCredentialStore` · `Update` · `FallbackServer` · `DisplayTmpTagsInStrings` | Connection timeouts, packet rate limits, explicit mod load order, auth credential storage, auto-update, fallback server (`Host`/`Port`), and a debug flag for untranslated strings |

> Singleplayer saves omit most server fields (`ServerName`, `MOTD`, `Password`, `MaxPlayers`)
> and fall back to defaults. Add them when hosting a dedicated server.

### Defaults — the spawn world

`Defaults` is the block that decides which world joining players spawn into:

```json
"Defaults": { "World": "flat_world", "GameMode": "Adventure" }
```

| Key | Description |
|-----|-------------|
| `World` | Name of the `universe/worlds/<name>/` folder to spawn players into |
| `GameMode` | Default game mode (`Adventure` / `Creative`) |
| `GameModeTypeOnDeath` | 0.6.3+: game-mode type players are switched to when they die — the server-wide *fallback*, used only when the world's gameplay config `Death.GameModeTypeOnDeath` is unset (`World.getGameModeTypeOnDeath()` checks the gameplay value first) |
| `HardcoreMode` | 0.6.3+: `None`, `PerPlayer`, or `Global` (`server.core.universe.hardcore.HardcoreMode`) — enables the hardcore ruleset, scoped per player or for the whole universe |
| `HardcoreLives` | 0.6.3+: lives per player/world in hardcore mode (int). Under `Global` the shared pool lives in the `Hardcore` universe resource — see [Universe resources](#universe-resources) |
| `CrashRecovery` | 0.6.3+: what happens when a world crashes — `{ "Mode": None/Reload/Shutdown, "MaxAttempts", "RetryDelaySeconds", "Fallback": None/Shutdown }` (`MaxAttempts`/`RetryDelaySeconds`/`Fallback` apply to `Reload` only; the same block is accepted per world) |

How it resolves, from `Universe.getDefaultWorld()` (decompiled):

```java
String worldName = HytaleServer.get().getConfig().getDefaults().getWorld();
return worldName != null ? getWorld(worldName) : null;   // getWorld lowercases + looks up the worlds map
```

When the `Defaults` block is **absent**, the server falls back to the world literally named
**`default`** (`Defaults.World` is initialised to `"default"` in `HytaleServerConfig.Defaults`; the same
string is `World.DEFAULT`). This is why creative saves — which
write no `Defaults` block — spawn you into the `default/` world. **To host a specific world
(e.g. a flat arena), set `Defaults.World` to that world's folder name.**

## The per-world `config.json`

Each `universe/worlds/<name>/config.json` defines one world. A flat creative world
(`worlds/flat_world/config.json`) looks like:

```json
{
  "Version": 4,
  "UUID": { "$binary": "AAAAAAAAAAAAAAAAAAAAAA==", "$type": "04" },
  "DisplayName": "Default Flat",
  "Seed": 123456789,
  "SpawnProvider": { "Id": "Global", "SpawnPoint": { "X": 0.5, "Y": 80.0, "Z": 0.5, "Yaw": 180.0 } },
  "WorldGen": { "Type": "HytaleGenerator", "WorldStructure": "Default_Flat" },
  "GameMode": "Creative",
  "IsPvpEnabled": false,
  "IsFallDamageEnabled": true,
  "GameplayConfig": "Default",
  "IsTicking": true,
  "IsBlockTicking": true,
  "Plugin": {}
}
```

Key fields:

| Field | Description |
|-------|-------------|
| `DisplayName` | Human-readable world name |
| `Seed` | World generation seed |
| `SpawnProvider` | `{ "Id": "Global", "SpawnPoint": { X, Y, Z, Yaw, Pitch, Roll } }` — where players spawn |
| `WorldGen` | The generator binding (see below) |
| `GameMode` | `Creative` / `Adventure` |
| **`IsPvpEnabled`** | **Per-world player-vs-player toggle** (bool) |
| `IsFallDamageEnabled` | Per-world fall damage toggle (bool) |
| `GameplayConfig` | Named [GameplayConfig](world.md#gameplayconfig) asset (`Default`, `CreativeHub`, ...) |
| `IsTicking` / `IsBlockTicking` | Whether the world / its blocks tick |
| `Plugin` | Per-world plugin config (see [CreativeHub](#the-crossroads-is-the-creativehub-plugin)) |
| `ChunkStorage` / `ResourceStorage` | `{ "Type": "Hytale" }` — storage-provider selection (see [Programmatic persistence](#programmatic-persistence-plugin-api)) |
| `DeleteOnRemove` / `DeleteOnUniverseStart` | Delete the world's files when it is removed / on universe boot (bool) |
| `CrashRecovery` | 0.6.3+: per-world crash-recovery policy, same shape as the server-level `Defaults.CrashRecovery` |

### WorldGen — binding to a structure

`WorldGen` selects how terrain is generated. Two `Type` values are observed:

```json
"WorldGen": { "Type": "HytaleGenerator", "WorldStructure": "Default_Flat" }
```
Uses the procedural generator and a [WorldStructure](worldgen-zones.md) by name (here the
shipped flat structure). This is the link from a runtime world to a
`Server/HytaleGenerator/WorldStructures/*.json` file.

```json
"WorldGen": { "Type": "Hytale", "Name": "Default", "Version": "0.0.0" }
```
Uses a fixed named generator rather than a structure file.

## The "crossroads" is the CreativeHub plugin

A creative save's `default` world carries a per-world plugin block:

```json
"Plugin": { "CreativeHub": { "StartupInstance": "CreativeHub" } }
```

That `CreativeHub` plugin spawns a temporary **instance world** — `DisplayName: "the Crossroads"`,
`WorldGen.Name: "Instance_Creative_Hub"`, `GameplayConfig: "CreativeHub"` — and warps the
player into it. The instance carries a `ReturnPoint` back to the spawn world and auto-removes
when empty:

```json
"Plugin": { "Instance": {
  "RemovalConditions": [ { "Type": "WorldEmpty", "TimeoutSeconds": 300.0 } ],
  "ReturnPoint": { "World": { ... }, "ReturnPoint": { "X": 0.5, "Y": 64.0, "Z": 0.5 }, "ReturnOnReconnect": true }
} }
```

From the crossroads, portals move the player to the separate destination worlds (e.g.
`flat_world` bound to `Default_Flat`, `zone3_taiga1_world` bound to `Zone3_Taiga1`). **The
crossroads is not terrain — it exists only because the `CreativeHub` plugin is attached to the
spawn world. Remove that plugin block and players spawn directly into the world.**

## A universe runs many worlds at once

A universe is not one world with sub-areas — it is a set of independent worlds that all load and
**tick concurrently**. `Universe` holds a name→world map, and each `World` is its own tick thread
with its own terrain, chunks, and per-world settings. The boot log lists each one as it loads:

```
[World|arena]   Added world 'arena'
[World|default] Added world 'default'
```

Consequences worth designing around:

- **Worlds are isolated.** Separate terrain, and separate *per-player* position — each
  `players/<uuid>.json` stores a `PerWorldData` entry per world, and `PlayerData.World` is the
  player's current world. A returning player is restored to the world they last logged out in,
  which is why `Defaults.World` only governs players with no record (see the gotcha below).
- **Gameplay rules are per world, not global.** One world can be `Creative` with PvP off while
  another is `Adventure` with PvP on — `GameMode`, `IsPvpEnabled`, day length, etc. live in each
  world's own `config.json`.
- **Players don't pick a world freely** — they need *transport* between worlds: a portal (the
  built-in `Portals` plugin / a `Portal` block), a teleport, or a hub like the
  [CreativeHub](#the-crossroads-is-the-creativehub-plugin). A loaded world with no route into it is
  simply unreachable in normal play.
- **Each loaded world costs memory and CPU** because it ticks. Temporary instance worlds avoid this
  by auto-unloading when empty (`RemovalConditions: WorldEmpty`); persistent worlds stay resident.

## Worked example: a flat PvP arena server

To host a flat world with PvP, joined directly (no crossroads):

**1. The arena world** — `universe/worlds/arena/config.json`:
```json
"WorldGen":     { "Type": "HytaleGenerator", "WorldStructure": "Default_Flat" },
"Plugin":       {},
"GameMode":     "Adventure",
"IsPvpEnabled": true,
"IsFallDamageEnabled": true,
"SpawnProvider": { "Id": "Global", "SpawnPoint": { "X": 0.5, "Y": 80.0, "Z": 0.5 } }
```

**2. The server config** — `<save>/config.json`:
```json
"Defaults": { "World": "arena", "GameMode": "Adventure" }
```

**3. Run the dedicated server pointed at the save directory.** Players join and land directly
on the flat arena with PvP enabled.

To build the arena by hand first, generate it in a flat creative world (a world bound to
`Default_Flat`), then host that save with the two edits above (drop `CreativeHub`, flip
`IsPvpEnabled`, set `Defaults.World`).

## Workflow: a creative-authored world → dedicated server

The common path: you build a world in **creative singleplayer**, then host that same world on a
dedicated server. A singleplayer save and a dedicated server consume the **identical on-disk
format** (see top of this page), so "moving" the world is mostly copying the save directory and
editing two config files — no export step.

### Where your authored blocks live

Your creative edits are written into the **world's `chunks/`** directory, e.g.
`universe/worlds/flat_world/chunks/`. The world is keyed by its **folder name** (`flat_world`),
*not* its `DisplayName` (`"Default Flat"`) and *not* the save name. Note that in creative you
spawn into the `default` world — the [CreativeHub crossroads](#the-crossroads-is-the-creativehub-plugin)
— and portal *out* to the flat world; the blocks you placed are in the destination world's
folder, not in `default/`.

### Steps

**1. Flush the save.** Fully exit the game (or stop the server) before copying. Chunk and config
writes are flushed on shutdown; copying a running save can capture a half-written `config.json`
(the `.bak` siblings are the previous good copy, not a live mirror).

**2. Copy the whole save directory** `UserData/Saves/<save>/` to the server host. It carries
everything the universe needs: the root `config.json`, `universe/worlds/<name>/` (with `chunks/`,
`resources/`, `instance.bson`), `universe/players/`, and `permissions.json` / `bans.json` /
`whitelist.json`. Copying the entire save is the safe default; dropping a single
`worlds/<name>/` folder into an existing universe also works but only if you also point a spawn
at it (next step).

**3. Pick the spawn world.** A creative save has no `Defaults` block, so the server falls back to
the world literally named `default` — which is the **crossroads**, not your build. Set
`Defaults.World` to your world's folder name so players land directly in it:

```json
"Defaults": { "World": "flat_world", "GameMode": "Adventure" }
```

Because `Defaults.World` bypasses `default` entirely, the crossroads never loads — you do **not**
also need to remove `default`'s `CreativeHub` plugin (though clearing it to `"Plugin": {}` is
harmless cleanup).

**4. Add dedicated-server fields.** A singleplayer root `config.json` omits server fields. Add the
ones you need alongside `Backup`/`Version`/`Mods`:

```json
"ServerName": "My Arena", "MOTD": "...", "MaxPlayers": 20, "Password": ""
```

**5. Set per-world gameplay.** Game mode and PvP are **per world** — edit
`universe/worlds/<name>/config.json`, not the root config. A creative-built world ships as
`"GameMode": "Creative"`; flip it for play and enable PvP if wanted:

```json
"GameMode": "Adventure",
"IsPvpEnabled": true
```

**6. Install any mods the world needs.** A dedicated server loads mods from the `mods/` directory in
its **working directory** (the save root), and the root `config.json` `Mods` map enables/disables
them by id. Copying the save carries each mod's saved *state* (under `mods/<ModName>/`) but not the
mod code itself — install the mod jars/packs the world expects (anything in its `RequiredPlugins`,
or listed in your `Mods` config) on the server. A world bound to a **shipped** `WorldStructure`
(like `Default_Flat`) needs no custom mod.

**7. Run the server pointed at the save.** The dedicated server *is* the same
`HytaleServer.jar`. It has **no save-path/universe argument** — it resolves `config.json`,
`universe/`, and `mods/` relative to its **working directory**, so you run it *from inside the
save directory*. It does need to be pointed at the game assets with `--assets`:

```bash
cd /path/to/save-directory
java -jar /path/to/Server/HytaleServer.jar --assets /path/to/Assets.zip
```

Optional flags include `--backup` with `--backup-dir <dir>` (plus `--backup-frequency <min>`,
`--backup-max-count` and `--backup-archive-max-count`) for periodic world backups, and `--mods <dir,...>`
for extra mod directories (all from `com.hypixel.hytale.server.core.Options`). Players join and spawn
directly into your authored world.

## Updating a world on a running server

A persistent world is **resident while the server runs** — it stays loaded and ticking even with no
players in it (only temporary instance worlds auto-unload when empty). So you **cannot** simply copy
updated files over a world's directory on a live server: the server serves that world from memory
(your copy has no effect), it will **overwrite your files** on its next save (auto-backup, chunk
unload, or shutdown), and writing under the live process risks corruption.

Take just that one world offline first — no full restart needed. The server exposes per-world
console commands:

| Command | Effect |
|---------|--------|
| `/world save <name>` (or `/world save all`) | Flush the world to disk |
| `/world remove <name>` (alias `rm`) | Unload the world from the running universe (does not delete its files unless the world's `DeleteOnRemove` is set). You can't remove the only loaded world, and removing the world named by `Defaults.World` requires reassigning the default first. |
| `/world load <name>` | Load an on-disk world that isn't currently loaded |
| `/world add <name> [gen …]` | Create a new world |
| `/world list` (alias `ls`) | List loaded worlds (`/world` itself has the alias `/worlds`) |
| `/world setdefault <name>` | Reassign `Defaults.World` on the running server (the step `remove` needs for the default world) |
| `/world prune` · `/world rocksdb compact` · `/world tps` · `/world perf` | 0.6.3 additions: bulk-remove prunable worlds (each goes through `Universe.removeWorld`), compact a `RocksDb` chunk store, and per-world tick-rate / performance diagnostics |

So the live update loop is:

1. Close the route in (disable/remove the portal to the world) so no one enters mid-swap.
2. `/world save <name>` then `/world remove <name>`.
3. Replace the files on disk (see below).
4. `/world load <name>`.
5. Reopen the route.

### Update the build, not the identity

Re-edit a world **in the same save** and its **UUID stays the same** — the UUID is assigned at
creation and persisted in the world's `config.json`, not regenerated on edit. That matters because
**portals target their destination by UUID**: the `PortalDevice` component stores a
`destinationWorldUuid`. A world swapped in with a *different* UUID (e.g. rebuilt in a fresh save)
leaves every portal pointing at a missing world. When a world is removed, the Portals plugin turns
off portals into it automatically; loading the same world back (same UUID) reconnects them.

To update a world safely:

- **Copy the build, not the config.** Copy `chunks/` (and `resources/` / `instance.bson` for
  map/metadata), but **leave the destination `config.json` in place**. The server's copy holds the
  world's identity (UUID) and your server-side settings (`GameMode`, `IsPvpEnabled`, `DisplayName`,
  spawn point); overwriting it with a singleplayer copy reverts those.
- **Match the destination folder name.** A world is keyed by its folder name — copy into the
  existing `worlds/<name>/`, don't create a second folder under a different name.

## Programmatic persistence (plugin API)

The directories above are read and written through a small pluggable Java layer. Per-world chunk
and resource storage are **providers** selected in the world's runtime config (and by extension
its `config.json` — `ChunkStorage` and `ResourceStorage` are recognized per-world keys), and
plugins can persist their own keyed records under `universe/` with a **data store**.

### Chunk storage providers

**Package:** `com.hypixel.hytale.server.core.universe.world.storage` (+ `.provider`)

A world's `chunks/` data goes through the `IChunkStorageProvider` on its runtime `WorldConfig`
(`world.getWorldConfig().getChunkStorageProvider()` / `setChunkStorageProvider(...)`). Providers
are codec-registered by id; the ids `Universe` registers are `Hytale` (`DefaultChunkStorageProvider`,
still the `Priority.DEFAULT` choice in 0.6.3), `IndexedStorage`, `RocksDb`, `Migration`, and `Empty`.

```java
// IChunkStorageProvider<Data>
Data initialize(Store<ChunkStore> store)
IChunkLoader getLoader(Data data, Store<ChunkStore> store)
IChunkSaver getSaver(Data data, Store<ChunkStore> store)
void close(Data data, Store<ChunkStore> store)
void delete(Data data, Store<ChunkStore> store)
<OtherData> Data migrateFrom(Store<ChunkStore> store, IChunkStorageProvider<OtherData> from)  // default: copy all chunks over
boolean isSame(IChunkStorageProvider<?> other)                                                // default

// Crash-recovery hooks (0.6.3+, all default no-ops; paired with the CrashRecovery config)
IChunkLoader getRecoveryLoader(Store<ChunkStore> store, Path backupPath)
void beginRecovery(Path file, Path recoveryPath)
void revertRecovery(Path file, Path recoveryPath)
```

| Provider | Id | Use |
|----------|----|-----|
| `EmptyChunkStorageProvider` (`INSTANCE`) | `Empty` | Loads nothing, saves nowhere — for worlds that must never touch disk (e.g. throwaway instances) |
| `MigrationChunkStorageProvider` | `Migration` | Wraps old (`from[]`) and new (`to`) providers: reads fall back through the old formats, writes go to the new one |
| `RocksDbChunkStorageProvider` | `RocksDb` | 0.6.3+: RocksDB-backed chunk store (this is the provider that sets `ChunkFlag.NEEDS_FORMAT_REWRITE` on old-format chunks). Tunable through `hytale.rocksdb.*` system properties (`stats`, `io_threads`, `min_blob_size`, `blob_cache_size`, `blob_gc_age_cutoff`, `blob_gc_force_threshold`, `blob_compaction_readahead_size`); `/world rocksdb compact` triggers a compaction |

The loader/saver pair a provider hands out is the actual chunk I/O surface:

```java
// IChunkLoader (extends Closeable)
CompletableFuture<Holder<ChunkStore>> loadHolder(int x, int z)
LongList getIndexes()

// IChunkSaver (extends Closeable)
CompletableFuture<Void> saveHolder(int x, int z, Holder<ChunkStore> holder)
CompletableFuture<Void> saveChunkColumn(int x, int z, Store<ChunkStore> store, Ref<ChunkStore> column,
                                        Executor executor, Runnable onComplete)   // default (0.6.3+): save a live column entity
CompletableFuture<Void> removeHolder(int x, int z)
LongList getIndexes()
void flush()
CompletableFuture<Void> compact(long[] indexes)                  // default; returned a void before 0.6.3
void pauseBackgroundSaving(ChunkSavingSystems.Data data)         // default
CompletableFuture<Void> resumeBackgroundSaving()                 // default; returned a void before 0.6.3
```

(`ChunkStore.resumeBackgroundSaving()` changed the same way — it now returns the `CompletableFuture<Void>`.)

### ChunkSavingSystems

**Package:** `com.hypixel.hytale.server.core.universe.world.storage.component`

The ECS systems that drain dirty chunks (`markNeedsSaving()`, see [World API](world.md#worldchunk))
to the saver. The plugin-facing pieces:

```java
// 0.6.3 added the Executor parameter to both statics (pass the world — World implements Executor)
static CompletableFuture<Void> saveChunksInWorld(Store<ChunkStore> store, Executor executor)   // flush every chunk that needs saving
static void saveChunk(Ref<ChunkStore> chunk, ChunkSavingSystems.Data data, boolean report,
                      Store<ChunkStore> store, Executor completionExecutor)

// ChunkSavingSystems.Data — the per-world save-queue *resource* (nested class; these are NOT statics on
// ChunkSavingSystems). Fetch it with store.getResource(ChunkStore.SAVE_RESOURCE).
ChunkSavingSystems.Data data = world.getChunkStore().getStore().getResource(ChunkStore.SAVE_RESOURCE);
CompletableFuture<Void> waitForSavingChunks()
void clearSaveQueue()
int getQueueDepth()            // 0.6.3+ metrics (what `/chunk savequeue` prints)
int getInFlightSaveCount()
int getMaxInFlightSaves()
```

### Resource storage providers

**Package:** `com.hypixel.hytale.server.core.universe.world.storage.resources`

The analog for a world's `resources/` directory. `IResourceStorageProvider.getResourceStorage(World)`
returns the `IResourceStorage` backing the world's store resources; select the provider via the
per-world `ResourceStorage` config key or `WorldConfig.setResourceStorageProvider(...)`. Registered
ids: `Hytale` (default), `Disk`, `Empty` — `EmptyResourceStorageProvider` (`INSTANCE`, id `Empty`)
is the no-persistence choice.

### Universe resources

**Package:** `com.hypixel.hytale.server.core.universe.resources` (0.6.3+)

The **universe-level** counterpart to the per-world store resources above. A universe resource is a
single codec-typed object, registered by id, loaded once when the universe starts and written back to
`universe/resources/<Id>.json`. Use it for state that belongs to the *save* rather than to one world
or one player — campaign progression, hardcore bookkeeping, server-wide counters.

Registration happens in a plugin's `setup()`:

```java
// Universe (com.hypixel.hytale.server.core.universe)
static <T> UniverseResourceType<T> registerResource(Class<T> typeClass, String id, BuilderCodec<T> codec)
<T> T getResource(UniverseResourceType<T> type)                    // instance method: Universe.get().getResource(...)
CompletableFuture<Void> flushResource(UniverseResourceType<?> type)
```

```java
public class MyPlugin extends JavaPlugin {
    private UniverseResourceType<MyState> stateType;

    @Override
    protected void setup() {
        // id becomes the filename: universe/resources/MyState.json
        this.stateType = Universe.registerResource(MyState.class, "MyState", MyState.CODEC);
    }

    public MyState getState() {
        return Universe.get().getResource(this.stateType);   // same instance for the whole universe
    }

    public void save() {
        Universe.get().flushResource(this.stateType);        // write now, don't wait for the 10s flush
    }
}
```

| Class | Role |
|-------|------|
| `UniverseResources` | The per-universe holder. `static <T> UniverseResourceType<T> register(Class<T>, String, BuilderCodec<T>)` (what `Universe.registerResource` delegates to), `static Collection<UniverseResourceType<?>> registeredTypes()`, `void load(Collection<? extends UniverseResourceType<?>>)`, `<T> T get(UniverseResourceType<T>)`, `CompletableFuture<Void> flush(UniverseResourceType<?>)`, `CompletableFuture<Void> flushAll()` |
| `UniverseResourceType<T>` | The registration handle (constructor is package-private — you only ever get one from `register`). `getTypeClass()`, `getId()`, `getCodec()` |
| `IUniverseResourceStorage` | Backing store: `Map<UniverseResourceType<?>, Object> loadAll(Collection<? extends UniverseResourceType<?>>)`, `<T> CompletableFuture<Void> save(UniverseResourceType<T>, T)` |
| `IUniverseResourceStorageProvider` | Codec-registered factory: `IUniverseResourceStorage getResourceStorage()` |
| `DefaultUniverseResourceStorageProvider` | Id `Hytale`, the `Priority.DEFAULT` choice (`INSTANCE`); delegates to a `DiskUniverseResourceStorageProvider` exposed as `DEFAULT` |
| `DiskUniverseResourceStorageProvider` | Id `Disk`; one `Path` key, default `<universe>/resources`. `getPath()` |

Selected with the `UniverseResourceStorage` block in the save `config.json`, exactly like the
per-world `ChunkStorage`:

```json
"UniverseResourceStorage": { "Type": "Disk", "Path": "universe/resources" }
```

**Lifecycle and persistence** (from `Universe.start()` / `DiskUniverseResourceStorageProvider`):

- Every registered type is loaded **once**, at universe start, from `<dir>/<Id>.json` (JSON text, read
  through the same `.bak` fallback as the other save files). A missing or unreadable file yields the
  codec's default value, so `getResource` never returns `null`.
- Writes are asynchronous and go through the `StorageManager`, so they respect
  `Universe.lockSaving()`; each write rotates the previous file to `<Id>.json.bak`.
- A background task flushes **all** universe resources every **10 seconds**, `runBackup()` flushes
  them before archiving the save, and a `ShutdownEvent` handler flushes them with a **30-second**
  timeout (`Timed out waiting for universe resource writes during shutdown ... unfinished writes are
  lost when the process exits`). `flushResource(...)` forces one type immediately.
- With `--bare`, the periodic flush is not scheduled and the disk store creates neither the directory
  nor new files — it only overwrites files that already exist.

The three universe resources the game registers itself:

| Id | File | Class | Registered by |
|----|------|-------|---------------|
| `Memories` | `Memories.json` | `RecordedMemories` | `MemoriesPlugin` (`RECORDED_MEMORIES_ID`) |
| `GameFlags` | `GameFlags.json` | `GameFlagsResource` | `GameFlagsPlugin` — see [Game Flags](world.md#game-flags) |
| `Hardcore` | `Hardcore.json` | `HardcoreState` | `EntityModule` |

`HardcoreState` is the pooled-lives record behind `HardcoreMode: "Global"` (see
[Defaults](#defaults--the-spawn-world)); reach it with
`Universe.get().getResource(HardcoreState.getResourceType())`, then
`burnPoolLife(poolSize)` / `getPoolRemaining(poolSize)` / `isGameOver()` / `markGameOver()`. Its two
persisted keys are `PoolRemaining` and `GameOver`. Per-player hardcore lives are **not** here — they
live in the `PlayerLives` entity component (see [Combat API](combat.md)).

> **Gotchas**
> - **`Universe resources are not loaded yet`** → `getResource` / `flushResource` ran before
>   `Universe.start()`. Register in `setup()`, read in `start()` or later.
> - **`Universe resource 'X' was registered after resources loaded`** → the type was registered after
>   the universe finished loading, so nothing was read for it. Register during plugin `setup()`.
> - **`Duplicate universe resource id: X`** → ids are global across all plugins. Prefix yours.
> - **`Invalid universe resource id: X`** → the id becomes a filename, so it must pass
>   `PathUtil.isValidName` (no separators, no `..`).
> - **`Ignoring unknown universe resource file <path>`** (WARNING at load) → a stray `*.json` in the
>   resources directory that matches no registered id — usually a plugin that is no longer installed.
> - **`Universe resource storage path must be within a trusted directory`** → a `Disk` provider
>   `Path` pointing outside the trusted root.

### Data stores — plugin key/value persistence

**Package:** `com.hypixel.hytale.server.core.universe.datastore`

A `DataStore<T>` persists codec-typed records by string id. The disk implementation stores each
record as a `.bson` file in a directory **under `universe/`** — this is how e.g. the objectives
plugin keeps its state (`universe/objectives/`).

```java
// DataStoreProvider (codec-registered; id "Disk" → DiskDataStoreProvider)
<T> DataStore<T> create(BuilderCodec<T> codec)

// DiskDataStoreProvider
DiskDataStoreProvider(String path)     // directory name, resolved under universe/

// DataStore<T>
T load(String id)
void save(String id, T value)
void remove(String id)
List<String> list()
Map<String, T> loadAll()
void saveAll(Map<String, T> values)
void removeAll()
BuilderCodec<T> getCodec()
```

```java
// Persist plugin records under universe/myplugin/
DataStore<MyRecord> store = new DiskDataStoreProvider("myplugin").create(MyRecord.CODEC);
store.save("some-id", record);
MyRecord loaded = store.load("some-id");
```

### StorageManager

**Package:** `com.hypixel.hytale.server.core.universe`

The universe-level coordinator that serializes save/load operations per path and holds them while
saving is locked (`Universe.lockSaving()` / `unlockSaving()`). Reached via `Universe.getStorageManager()`; mostly internal,
but useful when a plugin's own I/O must cooperate with the universe save cycle:

```java
CompletableFuture<Void> doSave(Path path, Supplier<CompletableFuture<Void>> saveOp)
<T> CompletableFuture<T> doLoad(Path path, Supplier<CompletableFuture<T>> loadOp)
CompletableFuture<Void> pendingOperations()   // completes when all queued ops finish
boolean hasQueuedSave(Path path)
```

### Chunk-format migrations

**Package:** `com.hypixel.hytale.server.core.modules.migrations`

`MigrationModule` is the built-in module that rewrites stored chunks between format versions at
boot (it walks every stored chunk through the loader, applies registered migrations, and saves).

```java
static MigrationModule get()
void register(String name, Function<Path, Migration> migrationCtor)
void runMigrations()
SystemType<ChunkStore, ChunkColumnMigrationSystem> getChunkColumnMigrationSystem()
SystemType<ChunkStore, ChunkSectionMigrationSystem> getChunkSectionMigrationSystem()
```

`ChunkColumnMigrationSystem` and `ChunkSectionMigrationSystem` are abstract `HolderSystem<ChunkStore>`
bases registered as system *types* on the chunk store — extend one to transform chunk-column or
chunk-section holders as they load (this is the hook the version bumps in `BlockSection.VERSION`-style
format changes run through).

## Gotchas & Errors

- **Players still spawn at the crossroads** → the spawn world still has
  `"Plugin": { "CreativeHub": { ... } }`. Clear it to `"Plugin": {}`.
- **`Defaults.World` has no effect** → the value must match a `universe/worlds/<name>/`
  folder name. The name is **lowercased** before lookup, so use a lowercase folder name; a value
  with no matching folder yields no default world.
- **No `Defaults` block** → the server falls back to the world named `default`; if you want a
  different spawn world you must add `Defaults`.
- **PvP not working** → `IsPvpEnabled` is **per world**, not global. Set it on the specific
  world players fight in.
- **Returning players don't land at `Defaults.World`** → `Defaults.World` only places players
  with **no saved location**. Each `universe/players/<uuid>.json` records `PlayerData.World`, so a
  player who was last in another world (or the now-gone creative crossroads instance) is restored
  there. For a clean dedicated start, delete `universe/players/` before first boot so everyone
  spawns via `Defaults`.
- **Players spawn holding editor tools / in Creative** → that state lives in per-player data
  (`ToolInventory` holds `EditorTool_*`, and game mode can be saved per player). It came over with
  `universe/players/`; clearing that directory (above) resets it.
- **Copied save won't load / is corrupt** → the save was copied while the game/server was still
  running. Stop it first so chunks and `config.json` are flushed, then copy.

## Related Documentation

- [World API](world.md) — the runtime `World` object, chunks, and gameplay config
- [World Structures (Zones)](worldgen-zones.md) — the `WorldStructure` files `WorldGen` references
- [World Generation Overview](worldgen.md) — the generator and asset layout
- [Combat API](combat.md) — damage events; PvP is gated by `IsPvpEnabled` here
