---
title: "Universes & Save Format"
description: "How a Hytale save is structured for a dedicated server — the universe/worlds layout, the per-world config.json that binds a world to a worldgen WorldStructure, the server config.json (Defaults.World spawn selection, IsPvpEnabled), and how the creative crossroads is the CreativeHub plugin."
seo:
  type: TechArticle
---

# Universes & Save Format

**Doc type:** Save / config file format · **Files:** `UserData/Saves/<save>/` · **Verified against release server build `2026.03.26-89796e57b`**

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
  "Mods": { "inkthorne:Example Entity Count": { "Enabled": true } }
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
  "UUID": { "$binary": "fPvCX3Y/RoarqbEG5zJogw==", "$type": "04" },
  "DisplayName": "Default Flat",
  "Seed": 1779519412083,
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
  "ReturnPoint": { "World": { ... }, "ReturnPoint": { "X": 374.5, "Y": 121.0, "Z": 86.5 }, "ReturnOnReconnect": true }
} }
```

From the crossroads, portals move the player to the separate destination worlds (e.g.
`flat_world` bound to `Default_Flat`, `zone3_taiga1_world` bound to `Zone3_Taiga1`). **The
crossroads is not terrain — it exists only because the `CreativeHub` plugin is attached to the
spawn world. Remove that plugin block and players spawn directly into the world.**

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

## Gotchas & Errors

- **Players still spawn at the crossroads** → the spawn world still has
  `"Plugin": { "CreativeHub": { ... } }`. Clear it to `"Plugin": {}`.
- **`Defaults.World` has no effect** → the value must match a `universe/worlds/<name>/`
  folder name (lookup is case-insensitive). A name with no matching folder yields no default
  world.
- **No `Defaults` block** → the server falls back to the world named `default`; if you want a
  different spawn world you must add `Defaults`.
- **PvP not working** → `IsPvpEnabled` is **per world**, not global. Set it on the specific
  world players fight in.

## Related Documentation

- [World API](world.md) — the runtime `World` object, chunks, and gameplay config
- [World Structures (Zones)](worldgen-zones.md) — the `WorldStructure` files `WorldGen` references
- [World Generation Overview](worldgen.md) — the generator and asset layout
- [Combat API](combat.md) — damage events; PvP is gated by `IsPvpEnabled` here
