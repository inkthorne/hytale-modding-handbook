---
title: "Pack vs Plugin Directory Structure"
description: "Hytale mod project structure — Pack (JSON/asset content) vs Plugin (Java code), the Server/ and Common/ directories, and manifest configuration."
seo:
  type: TechArticle
---

# Pack vs Plugin Directory Structure

**Doc type:** Guide

This guide explains the difference between asset packs and plugins, and how to organize your files for each.

## Overview

Hytale supports two types of mods:

| Type | Description | Use Case |
|------|-------------|----------|
| **Pack** | Pure JSON/asset content with no Java code | Custom items, NPCs, world generation, audio |
| **Plugin** | Java code with optional embedded assets | Commands, custom logic, event handling, UI |

**When to use a Pack:**
- Adding new items, weapons, or tools using existing templates
- Defining NPCs with behaviors from existing AI systems
- Customizing world generation parameters
- Adding audio or visual assets

**When to use a Plugin:**
- Adding server commands
- Implementing custom game logic or event handlers
- Creating interactive UI that responds to player actions
- Anything requiring runtime code execution

## Pack Structure

A pack is a folder or `.zip` file containing assets and a manifest. No Java code is involved.

```
MyPack/          (or MyPack.zip)
├── manifest.json
├── Server/
│   ├── Item/
│   │   └── Items/
│   │       └── MyWeapon.json
│   └── Drops/
│       └── MyLootTable.json
└── Common/
    └── UI/
        └── Custom/
            └── MyPage.ui
```

> **Folder determines asset type.** The game decides what an asset *is* from the
> folder it sits in. `Server/Item/` is itself subdivided by type — item definitions
> go in `Server/Item/Items/`, interactions in `Server/Item/Interactions/`, resource
> types in `Server/Item/ResourceTypes/`, and so on. A `.json` placed directly in
> `Server/Item/` matches no type and is **silently ignored** (it loads with no error
> but never registers, so commands like `/give` can't find it). By contrast,
> `Server/Drops/` *is* a leaf type folder, so loot tables sit directly inside it.

### Pack Manifest

The manifest identifies the pack but has no `Main` field since there's no code entry point:

```json
{
  "Group": "MyGroup",
  "Name": "My Custom Pack",
  "Version": "1.0.0",
  "Authors": [
    { "Name": "YourName" }
  ]
}
```

## Plugin Structure

A plugin is a Gradle/Java project. Assets are placed in `src/main/resources/` and get bundled into the JAR.

```
my-plugin/
├── build.gradle
├── settings.gradle
├── src/
│   └── main/
│       ├── java/
│       │   └── com/example/
│       │       └── MyPlugin.java
│       └── resources/
│           ├── manifest.json
│           ├── Server/
│           │   └── Item/
│           │       └── Items/
│           │           └── MyItem.json
│           └── Common/
│               └── UI/
│                   └── Custom/
│                       └── MyPage.ui
└── build.bat
```

### Plugin Manifest

The manifest must include a `Main` field pointing to the plugin class:

```json
{
  "Group": "MyGroup",
  "Name": "My Plugin",
  "Version": "1.0.0",
  "Authors": [
    { "Name": "YourName" }
  ],
  "Main": "com.example.MyPlugin"
}
```

If the plugin includes assets (files in `Server/` or `Common/`), add:

```json
{
  "Group": "MyGroup",
  "Name": "My Plugin",
  "Version": "1.0.0",
  "Authors": [
    { "Name": "YourName" }
  ],
  "Main": "com.example.MyPlugin",
  "IncludesAssetPack": true
}
```

### ServerVersion (target server version)

> Verified against 0.5.3 (`com.hypixel.hytale.common.plugin.PluginManifest`, `com.hypixel.hytale.common.semver.SemverRange`).

> **Changed in Update 5.** `ServerVersion` is now a **semver range**, not a literal build string. It is parsed
> into a `SemverRange` and checked by *range satisfaction* against the server's own version — the old
> `String.equals` against a dated `2026.03.26-…` build stamp is gone. Old dated strings are deprecated; use range
> syntax going forward.

Any mod with `"IncludesAssetPack": true` should declare the server versions it targets, or the server logs a warning when the pack registers:

```
Plugin '<name>' does not specify a target server version. You may encounter issues
```

Add the `ServerVersion` field as a **semver range**:

```json
{
  "Group": "MyGroup",
  "Name": "My Plugin",
  "Version": "1.0.0",
  "Main": "com.example.MyPlugin",
  "ServerVersion": "^0.5.0",
  "IncludesAssetPack": true
}
```

`PluginManifest.getServerVersion()` returns a `SemverRange`; `PluginManifest.checkServerVersionCompatibility(range, runningVersion)` resolves to `COMPATIBLE`, `INCOMPATIBLE`, `MISSING`, or `PARSE_FAILED`. The running version it checks against is the `HytaleServer.jar`'s `Implementation-Version` manifest attribute — a semver, `0.5.0` on Update 5. Read it with:

```bash
unzip -p "$HYTALE_JAR" META-INF/MANIFEST.MF | grep Implementation-Version
```

### Range syntax

| Value | Matches |
|-------|---------|
| `^0.5.0` | Compatible with `0.5.x` (`>=0.5.0 <0.6.0`) — the recommended default |
| `>=0.5.0 <0.6.0` | Explicit bounded range (equivalent to the caret above) |
| `0.5.0` | Exactly `0.5.0` — valid, but brittle: won't match a `0.5.1` patch |
| `*` | Any version (`SemverRange.WILDCARD`) — opts out of the check |

A caret/range means you **no longer have to re-pin on every patch release** — the chief reason the old exact-string
form was painful. Pin a range that reflects what your plugin actually tolerates.

Warnings (all non-fatal):
- **Doesn't satisfy the range:** `Plugin '<name>' targets server version range '<range>' which does not match the running server version '<v>'. You may encounter issues` (`INCOMPATIBLE`).
- **Running version unparsable:** `Plugin '<name>' targets server version range '<range>' but the running server version '<v>' could not be parsed.` (`PARSE_FAILED`).
- **Field missing:** `Plugin '<name>' does not specify a target server version. You may encounter issues` (`MISSING`).
- The server also logs an aggregate `One or more plugins are targeting a different server version...`.

Caveats:
- **Pre-release tags are excluded.** A range like `>=0.5.0` does **not** match a pre-release such as `0.5.0-pre.3` (standard semver behavior) — target the stable release, or include the pre-release explicitly.
- Packs **without** `IncludesAssetPack` (code-only plugins) are not checked, but the example plugins set it anyway for forward-compatibility ("will be a hard error in the future").

## Server/ vs Common/ Directories

Assets are organized into two directories based on where they're used:

### Server/

Assets in `Server/` are only loaded by the server and are **not sent to clients**. Use this for:

| Directory | Contents |
|-----------|----------|
| `Server/Item/Items/` | Item definitions (.json) — see the folder-determines-type note under [Pack Structure](#pack-structure) |
| `Server/Audio/` | Audio configurations (.json) |
| `Server/Drops/` | Loot tables (.json) |
| `Server/HytaleGenerator/` | World generation configs (.json) |
| `Server/NPC/` | NPC definitions (.json) |

### Common/

Assets in `Common/` are shared with clients. Use this for:

| Directory | Contents |
|-----------|----------|
| `Common/UI/Custom/` | UI layouts (.ui files) |
| `Common/Sounds/` | Sound files (.ogg) |
| `Common/Blocks/` | Block models and definitions |
| `Common/BlockTextures/` | Block texture files (.png) |
| `Common/Items/` | Item models (.blockymodel) and textures (.png) |

## Notable Hytale Assets

Key built-in assets that may be useful for plugin and pack development:

| Asset | Path | Description |
|-------|------|-------------|
| Player Model | `Common/Characters/Player.blockymodel` | Main player character model |
| Player Model (with face) | `Common/Characters/Player_With_Face.blockymodel` | Player model with integrated face attachment |

## Manifest Comparison

### Pack Manifest (No Code)

```json
{
  "Group": "MyGroup",
  "Name": "Custom Weapons Pack",
  "Version": "1.0.0",
  "Authors": [
    { "Name": "YourName" }
  ]
}
```

### Plugin Manifest (Code Only)

```json
{
  "Group": "inkthorne",
  "Name": "Example Commands",
  "Version": "0.1.0",
  "Authors": [
    { "Name": "inkthorne" }
  ],
  "Main": "hytale.examples.commands.CommandsPlugin"
}
```

### Plugin Manifest (Code + Assets)

```json
{
  "Group": "inkthorne",
  "Name": "Example UI",
  "Version": "0.1.0",
  "Authors": [
    { "Name": "inkthorne" }
  ],
  "Main": "hytale.examples.ui.UIPlugin",
  "ServerVersion": "^0.5.0",
  "IncludesAssetPack": true
}
```

(See [ServerVersion](#serverversion-target-server-version) — the example mods target the `^0.5.0` range.)

## Examples

### Minimal Pack (Custom Weapon)

A simple pack that adds a custom sword using the weapon template:

```
CustomSword/
├── manifest.json
└── Server/
    └── Item/
        └── Items/
            └── CustomSword.json
```

**manifest.json:**
```json
{
  "Group": "MyGroup",
  "Name": "Custom Sword",
  "Version": "1.0.0"
}
```

**Server/Item/Items/CustomSword.json:**
```json
{
  "Parent": "Template_Weapon_Sword",
  "Name": "Custom Sword",
  "InteractionVars": {
    "BaseDamage": 15
  }
}
```

`Parent` references the template by its **id** (the filename without `.json`), not by
a path — the game resolves item ids globally regardless of which folder they live in.
Shipping a file at the **same id** as a vanilla asset *replaces* it (whole-asset, last-load-wins);
see [Assets API → Overriding base-game assets](assets.md#overriding-base-game-assets).

### Plugin Without Assets (Commands Only)

A plugin that only adds commands, with no custom assets:

```
example-commands/
├── build.gradle
├── src/main/java/hytale/examples/commands/
│   ├── CommandsPlugin.java
│   └── HelloCommand.java
└── src/main/resources/
    └── manifest.json
```

The manifest has no `IncludesAssetPack` since there are no assets.

### Plugin With Assets (UI)

A plugin that adds commands and custom UI:

```
example-ui/
├── build.gradle
├── src/main/java/hytale/examples/ui/
│   ├── UIPlugin.java
│   ├── MenuCommand.java
│   └── pages/
│       └── SimpleMenuPage.java
└── src/main/resources/
    ├── manifest.json
    └── Common/
        └── UI/
            └── Custom/
                └── SimpleMenuPage.ui
```

The manifest must include `"IncludesAssetPack": true` for the UI files to be loaded.

## Deployment

Both packs and plugins are deployed to the mods folder:

```
%APPDATA%\Hytale\UserData\Mods\
```

- **Packs**: Copy the folder or `.zip` file to the mods directory
- **Plugins**: Copy the built JAR file to the mods directory

For plugins, use the build scripts in each example:

```bash
./build.bat    # Build the plugin JAR
./deploy.bat   # Build and copy to mods folder
```
