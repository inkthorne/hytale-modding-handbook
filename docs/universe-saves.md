---
title: "Universes & Save Format"
description: "How a Hytale save is structured for a dedicated server — the universe/worlds layout, the per-world config.json that binds a world to a worldgen WorldStructure, the server config.json (Defaults.World spawn selection, IsPvpEnabled), how the creative crossroads is the CreativeHub plugin, and the workflow for moving a creative-authored world onto a dedicated server."
seo:
  type: TechArticle
---

# Universes & Save Format

**Doc type:** Save / config file format · **Files:** `UserData/Saves/<save>/` · **Verified against 0.5.2**

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
    ├── memories.json
    └── worlds/
        └── <world-name>/    keyed by folder name in Universe.worlds
            ├── config.json   the world definition (WorldGen, SpawnProvider, IsPvpEnabled, ...)
            ├── chunks/        block data
            ├── resources/     world-scoped resources
            └── instance.bson  world metadata
```

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

How it resolves, from `Universe.getDefaultWorld()` (decompiled):

```java
String worldName = HytaleServer.get().getConfig().getDefaults().getWorld();
return worldName != null ? getWorld(worldName) : null;   // getWorld lowercases + looks up the worlds map
```

When the `Defaults` block is **absent**, the server falls back to the world literally named
**`default`** (a hardcoded `"default"` string constant). This is why creative saves — which
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

Optional flags include `--backup` and `--backup-dir <dir>` for periodic world backups. Players join
and spawn directly into your authored world.

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
