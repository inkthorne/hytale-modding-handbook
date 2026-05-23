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
  "IncludesAssetPack": true
}
```

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
