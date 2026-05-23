# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complete reference for Hytale server plugin development containing:
- **docs/**: Comprehensive API documentation (33 markdown files)
- **examples/**: Standalone Gradle projects demonstrating different aspects of the plugin API

Refer to `docs/00-overview.md` for guidance when implementing Java code for plugins.

## Build Commands

From an example's directory (e.g., `examples/commands/`), run:

```bash
./build.bat    # Build the plugin
./deploy.bat   # Build and deploy to Hytale mods folder
```

Note: Use `./` prefix when running from bash.

Mods directory: `%APPDATA%\Hytale\UserData\Mods\`

### Path Configuration

Hytale paths are centralized in shared configuration files:
- `examples/hytale-paths.gradle` - Used by build.gradle files for `hytaleServerJar` and `hytaleModsDir`
- `examples/hytale-paths.bat` - Used by deploy.bat scripts for `HYTALE_MODS_DIR`

## Requirements

- Java 25+
- Hytale installed (provides `HytaleServer.jar` from `%APPDATA%\Hytale\install\release\package\game\latest\Server\`)

## Hytale Reference Files

The Hytale installation contains reference files useful for plugin development:

- **HytaleServer.jar**: `%APPDATA%\Hytale\install\release\package\game\latest\Server\HytaleServer.jar` - Decompile to explore API classes and code syntax
- **Assets.zip**: `%APPDATA%\Hytale\install\release\package\game\latest\Assets.zip` - Contains Hytale assets; use as reference for asset structure and formatting

### Inspecting assets on Linux

On Linux the launcher installs as a `--user` Flatpak, so the install mirrors the Windows layout under `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/` (consistent across Flatpak installs; a non-Flatpak install would differ). To inspect assets, extract the archive **once** to a cache dir rather than `unzip -p`-ing files individually — this enables grep/glob/read across all ~59k files:

```bash
unzip -q -o ~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Assets.zip -d ~/.cache/hytale-assets
```

Then read assets directly from `~/.cache/hytale-assets/` (`Common/` holds blockymodel/blockyanim/UI formats). The cache lives outside the repo, so it is never committed. Re-run the command (~10s) if the install updates.

## Architecture

### Plugin Structure
- Plugins extend `JavaPlugin` and override `setup()` to register commands
- Each plugin requires a `manifest.json` in `src/main/resources/` with `Group`, `Name`, and `Main` fields (PascalCase)
- Plugins with UI assets need `"IncludesAssetPack": true` in manifest

### Command System
- Simple commands extend `AbstractPlayerCommand`
- Arguments registered via `withRequiredArg()` with types like `ArgTypes.RELATIVE_POSITION`
- Execute method receives `CommandContext`, entity store, player ref, and world

### UI System
- Custom pages extend `BasicCustomUIPage`
- UI layouts defined in `.ui` files using Hytale's curly-brace DSL (placed in `resources/Common/UI/Custom/`)
- Root `Group` in `.ui` files must NOT have an ID; named elements go inside it
- HUD controlled via `player.getHudManager().setVisibleHudComponents()`

## Examples

- **examples/commands/**: Command system (no-arg and position args)
- **examples/ui/**: Custom UI pages and HUD management
