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
│   │   └── MyWeapon.json
│   └── Drops/
│       └── MyLootTable.json
└── Common/
    └── UI/
        └── Custom/
            └── MyPage.ui
```

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
│           │       └── MyItem.json
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

> Verified against build-12 (`com.hypixel.hytale.server.core.asset.AssetModule`). The literal value below is build-specific — see the caveat.

Any mod with `"IncludesAssetPack": true` should declare the server build it targets, or the server logs a warning when the pack registers:

```
Plugin '<name>' does not specify a target server version. You may encounter issues,
please check for plugin updates. This will be a hard error in the future
```

Add the `ServerVersion` field (a plain string, not a semver):

```json
{
  "Group": "MyGroup",
  "Name": "My Plugin",
  "Version": "1.0.0",
  "Main": "com.example.MyPlugin",
  "ServerVersion": "2026.03.26-89796e57b",
  "IncludesAssetPack": true
}
```

The value must **exactly equal** the server's own version string (`AssetModule` compares with `String.equals`). That string is the running `HytaleServer.jar`'s `Implementation-Version` manifest attribute — on build-12 it is `2026.03.26-89796e57b`. Read the current value with:

```bash
unzip -p "$HYTALE_JAR" META-INF/MANIFEST.MF | grep Implementation-Version
```

Caveats:
- The string embeds the build's git short-SHA, so it changes every game update. A mismatch downgrades the message to `Plugin '<name>' targets a different server version <v>...` — still a warning. There is **no permanent value**: `"*"` and any non-matching string both still warn (the wildcard falls into the "does not specify" branch). Re-pin this field after each game update.
- `-Dhytale.allow_outdated_mods` only suppresses the separate SEVERE "one or more asset packs are targeting an older server version" failure — not this per-plugin warning.
- Packs **without** `IncludesAssetPack` (code-only plugins) are not checked, but the example plugins set it anyway for forward-compatibility ("will be a hard error in the future").

## Server/ vs Common/ Directories

Assets are organized into two directories based on where they're used:

### Server/

Assets in `Server/` are only loaded by the server and are **not sent to clients**. Use this for:

| Directory | Contents |
|-----------|----------|
| `Server/Item/` | Item definitions (.json) |
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
  "ServerVersion": "2026.03.26-89796e57b",
  "IncludesAssetPack": true
}
```

(See [ServerVersion](#serverversion-target-server-version) — the example mods pin the build-12 value.)

## Examples

### Minimal Pack (Custom Weapon)

A simple pack that adds a custom sword using the weapon template:

```
CustomSword/
├── manifest.json
└── Server/
    └── Item/
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

**Server/Item/CustomSword.json:**
```json
{
  "Parent": "Hytale/Item/Weapon/Template_Weapon_Sword",
  "Name": "Custom Sword",
  "InteractionVars": {
    "BaseDamage": 15
  }
}
```

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
