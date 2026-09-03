---
title: "Pack vs Plugin Directory Structure"
description: "Hytale mod project structure — Pack (JSON/asset content) vs Plugin (Java code), the Server/ and Common/ directories, and manifest configuration."
seo:
  type: TechArticle
---

# Pack vs Plugin Directory Structure

**Doc type:** Guide + Java API

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

These are the fields the examples use. The full key set `PluginManifest.CODEC` reads is `Group`, `Name`, `Version`,
`Description`, `Authors`, `Website`, `Main`, `ServerVersion`, `Dependencies`, `OptionalDependencies`, `LoadBefore`
(the last three are maps of plugin identifier → semver range), `DisabledByDefault`, `IncludesAssetPack` and
`SubPlugins` (an array of nested manifests).

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

> Verified against 0.6.3 (`com.hypixel.hytale.common.plugin.PluginManifest`, `com.hypixel.hytale.common.semver.SemverRange`).

> **Changed in Update 5.** `ServerVersion` is now a **semver range**, not a literal build string. It is parsed
> into a `SemverRange` and checked by *range satisfaction* against the server's own version — the old
> `String.equals` against a dated `2026.03.26-…` build stamp is gone. An old dated string still parses, but only
> as `SemverRange.WILDCARD` (matches anything) with a warning — `Manifest ServerVersion '<v>' is in the pre-semver
> YYYY.MM.DD-<sha> format. Treated as wildcard for backward compatibility. Update to a SemverRange.` — so it no
> longer expresses any constraint. Use range syntax going forward.

Every mod should declare the server versions it targets, or the server logs a warning when it loads:

```
Plugin '<name>' does not specify a target server version. You may encounter issues, please check for plugin updates. This will be a hard error in the future
```

Add the `ServerVersion` field as a **semver range**:

```json
{
  "Group": "MyGroup",
  "Name": "My Plugin",
  "Version": "1.0.0",
  "Main": "com.example.MyPlugin",
  "ServerVersion": "^0.6.0",
  "IncludesAssetPack": true
}
```

`PluginManifest.getServerVersion()` returns a `SemverRange`; `PluginManifest.checkServerVersionCompatibility(range, runningVersion)` resolves to `COMPATIBLE`, `INCOMPATIBLE`, `MISSING`, or `PARSE_FAILED`. The running version it checks against is the `HytaleServer.jar`'s `Implementation-Version` manifest attribute — a semver, `0.5.9` on the last Update 5 build and `0.6.3` on the current one. Read it with:

```bash
unzip -p "$HYTALE_JAR" META-INF/MANIFEST.MF | grep Implementation-Version
```

### Range syntax

| Value | Matches |
|-------|---------|
| `^0.6.0` | Compatible with `0.6.x` (`>=0.6.0 <0.7.0`) — the recommended default on the current build |
| `~0.6.0` | `>=0.6.0 <0.7.0` — identical to the caret here; the tilde bumps the *minor* when the minor is non-zero, and the *major* when it is zero |
| `>=0.6.0 <0.7.0` | Explicit bounded range (space = AND) |
| `0.6.x` / `0.6.0` | Bare form; `x`/`*` become `0`, and a zero patch widens to `>=0.6.0 <0.7.0` — **not** an exact match |
| `=0.6.3` | Exactly `0.6.3` — valid, but brittle: won't match a `0.6.4` patch |
| `^0.5.0 \|\| ^0.6.0` | `\|\|` joins alternatives (OR) |
| `*` | Any version (`SemverRange.WILDCARD`) — opts out of the check |

> **Gotcha — a bare version with a non-zero patch is a parse error, not an exact match.**
> `SemverRange.fromString` only accepts a bare version when the patch is zero. `"ServerVersion": "0.6.3"`
> throws `Bare version '0.6.3' is not a valid range. Use '=0.6.3' for an exact match, or '^0.6.3' / '~0.6.3'
> for a range. Bare ranges only work when the patch is zero (e.g. '1.2.0' or '1.x').` Write `=0.6.3` (or a
> caret range) instead.

A caret/range means you **no longer have to re-pin on every patch release** — the chief reason the old exact-string
form was painful. Pin a range that reflects what your plugin actually tolerates. A caret does **not** survive a
*minor* bump, though: `^0.5.0` (`>=0.5.0 <0.6.0`) stopped matching when the server moved to `0.6.x`, so every plugin
still pinned to it now logs the `INCOMPATIBLE` warning below against `0.6.3`. Re-pin on each minor update.

Warnings (all non-fatal):
- **Doesn't satisfy the range:** `Plugin '<name>' targets server version range '<range>' which does not match the running server version '<v>'. You may encounter issues, please check for plugin updates.` (`INCOMPATIBLE`).
- **Running version unparsable:** `Plugin '<name>' targets server version range '<range>' but the running server version '<v>' could not be parsed.` (`PARSE_FAILED`).
- **Field missing:** `Plugin '<name>' does not specify a target server version. You may encounter issues, please check for plugin updates. This will be a hard error in the future` (`MISSING`).
- The server also logs an aggregate per surface: `One or more plugins are targeting a different server version...` (plugin loader) and `One or more asset packs are targeting an older server version...` (asset loader). Both are `SEVERE`, and both are suppressed by the `-Dhytale.allow_outdated_mods` system property. Players holding the `hytale.mods.outdated.notify` permission are also messaged on join.

Caveats:
- **Pre-release tags are excluded.** A range like `>=0.5.0` does **not** match a pre-release such as `0.5.0-pre.3` (standard semver behavior) — target the stable release, or include the pre-release explicitly.
- **Every mod is checked as of 0.6.3, code-only ones included.** The check runs twice on two independent surfaces: the plugin loader validates *every* manifest whose `Group` is not `Hytale`, and the asset loader separately validates every registered asset pack. So omitting `ServerVersion` warns even without `IncludesAssetPack` — set it on every mod ("will be a hard error in the future").

## Server/ vs Common/ Directories

Assets are organized into two directories based on where they're used:

### Server/

Assets in `Server/` are only loaded by the server and are **not sent to clients**. Use this for:

| Directory | Contents |
|-----------|----------|
| `Server/Item/Items/` | Item definitions (.json) — see the folder-determines-type note under [Pack Structure](#pack-structure) |
| `Server/Item/Interactions/` | Interaction definitions (.json); root interactions live in `Server/Item/RootInteractions/` |
| `Server/Drops/` | Loot tables (.json) — a leaf type folder |
| `Server/Audio/<type>/` | Audio configs, subdivided by type: `SoundEvents/`, `SoundSets/`, `MusicContainers/`, `AudioCategories/`, … |
| `Server/HytaleGenerator/<type>/` | World generation configs, subdivided by type: `Biomes/`, `Props/`, `Settings/`, `Density/`, … |
| `Server/NPC/<type>/` | NPC configs, subdivided by type: `Roles/`, `Flocks/`, `Groups/`, `Spawn/World/`, … |

### Common/

Assets in `Common/` are shared with clients. Use this for:

| Directory | Contents |
|-----------|----------|
| `Common/UI/Custom/` | UI layouts (.ui files) |
| `Common/Sounds/` | Sound files (.ogg) |
| `Common/Blocks/` | Block models (.blockymodel), animations (.blockyanim) and textures (.png) — block *definitions* are server-side, under `Server/Item/Block/Blocks/` |
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
  "Main": "hytale.examples.commands.CommandsPlugin",
  "ServerVersion": "^0.6.0"
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
  "ServerVersion": "^0.6.0",
  "IncludesAssetPack": true
}
```

(See [ServerVersion](#serverversion-target-server-version) — the example mods pin a caret range on the server's
current minor version; re-pin it whenever that minor changes.)

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
  "TranslationProperties": {
    "Name": "server.items.CustomSword.name"
  },
  "ItemLevel": 20,
  "MaxDurability": 120,
  "InteractionVars": {
    "Swing_Left_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Left_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 15 } }
      }]
    }
  }
}
```

> **`InteractionVars` values are interactions, never bare numbers.** The key is
> `MapCodec(RootInteraction.CHILD_ASSET_CODEC, …)`: each entry names a **chain slot** the
> template exposes (`Swing_Left_Damage`, `Guard_Wield`, `Consume_Charge`, …), and the value is
> either the **id** of an existing interaction or an **inline `RootInteraction`** that overrides
> one — a `ContainedAssetCodec`, so both forms are legal. Across every `Server/` asset in the
> game, all 1,840 `InteractionVars` values are objects or id strings; none is a number. Damage
> lives one level down, inside the interaction's `DamageCalculator`. There is no top-level
> `Name` key on an item either — the display name comes from `TranslationProperties.Name`.
> See [Weapon Items](items-weapons.md#example-child-iron-sword) for the full pattern.

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

```batch
:: Windows
build.bat      :: Build the plugin JAR
deploy.bat     :: Build and copy to the mods folder
```

```bash
# Linux / macOS
./gradlew build  # Build the plugin JAR (build/libs/*.jar)
./deploy.sh      # Build (if needed) and copy to the mods folder
```

On the Linux Flatpak launcher the mods folder resolves to
`~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/UserData/Mods/`; the deploy scripts
resolve it for you.
