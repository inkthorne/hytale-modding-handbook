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
# Windows
./build.bat     # Build the plugin
./deploy.bat    # Build and deploy to Hytale mods folder

# Linux / bash
./gradlew build # Build the plugin
./deploy.sh     # Build (if needed) and deploy to Hytale mods folder
```

Note: Use `./` prefix when running from bash. There is no `build.sh` — `./gradlew build` is the portable build entry point that `build.bat` itself wraps.

Mods directory: `%APPDATA%\Hytale\UserData\Mods\` (Windows); on Linux the Flatpak install resolves to `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/UserData/Mods/`.

### Path Configuration

Hytale paths are centralized in shared configuration files. All three resolve the same way — explicit `APPDATA` first, then the Linux Flatpak install, then a fallback:
- `examples/hytale-paths.gradle` - Used by build.gradle files for `hytaleServerJar` and `hytaleModsDir`
- `examples/hytale-paths.bat` - Used by deploy.bat scripts for `HYTALE_MODS_DIR`
- `examples/hytale-paths.sh` - Used by deploy.sh scripts for `HYTALE_MODS_DIR`

## Requirements

- Java 25+
- Hytale installed (provides `HytaleServer.jar` from `%APPDATA%\Hytale\install\release\package\game\latest\Server\`)

## Hytale Reference Files

The Hytale installation contains reference files useful for plugin development:

- **HytaleServer.jar**: `%APPDATA%\Hytale\install\release\package\game\latest\Server\HytaleServer.jar` - Decompile to explore API classes and code syntax
- **Assets.zip**: `%APPDATA%\Hytale\install\release\package\game\latest\Assets.zip` - Contains Hytale assets; use as reference for asset structure and formatting

### Inspecting assets on Linux

On Linux the launcher installs as a `--user` Flatpak, so the install mirrors the Windows layout under `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/` (consistent across Flatpak installs; a non-Flatpak install would differ). To inspect assets, extract the archive **once** to a cache dir rather than `unzip -p`-ing files individually — this enables grep/glob/read across all ~60k files. **Wipe the cache first** so the extraction is clean:

```bash
rm -rf ~/.cache/hytale-assets && unzip -q ~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Assets.zip -d ~/.cache/hytale-assets
```

Then read assets directly from `~/.cache/hytale-assets/` (`Common/` holds blockymodel/blockyanim/UI formats). The cache lives outside the repo, so it is never committed. Re-run the command (~10s) if the install updates. **Do not** re-extract with `unzip -o` over an existing cache: `-o` only overwrites, so assets *removed or renamed* in the new build linger as stale files and silently mask dead/renamed asset references in the docs (this is why the command wipes first). Verify the cache mirrors the zip exactly: `find ~/.cache/hytale-assets -type f | wc -l` should equal `unzip -Z1 …/Assets.zip | grep -vc '/$'`.

## Verifying documentation

The `docs/` were fact-checked against game **0.5.2** (Update 5; build-15) — `HytaleServer.jar`'s `Implementation-Version` is `0.5.2` (API docs via `javap` on the jar; JSON-asset/DSL docs against the extracted `Assets.zip`). They are only known-accurate as of that build — a game update can silently invalidate them. (0.5.2 is a patch of Update 5: the `CommonAssetsIndex.hashes` index is byte-identical in *content* to the 0.5.1/build-14 capture — only its internal line ordering changed — so format docs carry over unchanged; the full API surface re-passes `verify-docs.sh` against the 0.5.2 jar.) (Update 5 migrated the math library to JOML — vectors are now `org.joml.*` with Hytale `Vector*Util` companions and `Rotation3f`; see `docs/math.md`.)

Run the regression checker after any game update (or before trusting/extending a doc):

```bash
./maintenance/scripts/verify-docs.sh          # full run (hard gates + advisories)
./maintenance/scripts/verify-docs.sh --no-build   # skip example compilation (faster)
```

It auto-resolves the jar/assets per-platform. **Hard gates** (fail the run): every `com.hypixel.*` class referenced in docs resolves via `javap`; every documented **member symbol** in `Receiver.member` form (where `Receiver` is a real jar class) exists on that class — walking superclasses for inherited members (`maintenance/scripts/check-symbols.py`, calibrated to skip JSON/DSL key paths, prose negative examples, locally-declared example types, and private-but-present members); all intra-doc anchor links resolve; and all example projects compile. **Advisory/INFO**: referenced asset paths exist, and **asset drift vs `maintenance/baseline/CommonAssetsIndex.hashes`** (which Common assets changed since the baseline build — re-verify docs referencing those). See `maintenance/baseline/README.md` for the drift workflow; refresh the baseline after re-verifying against a new build.

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
- **examples/inventory/**: Inventory and item-stack management
- **examples/entity-count/**: ECS ticking system (`EntityTickingSystem`) that counts world entities each tick and pushes the totals to a live `CustomUIHud`
