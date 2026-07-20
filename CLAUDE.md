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

### Inspecting the server jar (cached)

`HytaleServer.jar` is large, so exploring its API by launching `javap` per class is slow. `maintenance/scripts/build-jar-cache.sh` builds a greppable cache **once** (outside the repo, never committed — same convention as the assets cache):

```bash
./maintenance/scripts/build-jar-cache.sh           # signature index + decompiled source
./maintenance/scripts/build-jar-cache.sh --no-src  # signature index only (fast)
```

It produces:
- `~/.cache/hytale-jar/javap-index.txt` — `javap -p -constants` signatures of **every** `com.hypixel.*` class, concatenated (compile-time constant fields include their `= value`, so a changed documented constant shows up in the update diff). Grep this instead of running `javap` per symbol: `grep -n 'registerCoreComponentType' ~/.cache/hytale-jar/javap-index.txt`.
- `~/.cache/hytale-jar/src/` — decompiled `.java` for `com.hypixel.hytale.*`, for reading actual method bodies (e.g. *does* `BuilderSensorFlockLeader.readConfig` call `readCommonConfig`?). Grep/Read it like any source tree.

The decompiler is resolved automatically: a `DECOMPILER_JAR` you point at, a `vineflower`/`cfr` on `PATH`, a previously-cached `~/.cache/hytale-jar-tools/cfr.jar`, or a one-time CFR download from Maven Central. If none is available the script still writes the signature index and skips `src/` with a note.

Like the assets cache, the script **wipes the cache first** so classes removed/renamed in a new build don't linger and mask dead references — re-run it after a game update. (Direct `javap` against the jar still works for one-off lookups; the cache just makes broad sweeps cheap.)

## Verifying documentation

The `docs/` were fact-checked against game **0.5.7** (Update 5 patch; build-20) — `HytaleServer.jar`'s `Implementation-Version` is `0.5.7` (API docs via `javap` on the jar; JSON-asset/DSL docs against the extracted `Assets.zip`). They are only known-accurate as of that build — a game update can silently invalidate them. (0.5.7 was the first Update-5 patch with real Common-asset drift: 36 assets changed content vs build-17 — door blockyanims, a few decorative-set models/textures, localization files, and `TriggerVolumeInspectorPage.ui` — none added or removed; both changed formats still match the format docs. The API delta was likewise small — a `HitboxCollision`/`Repulsion` config index→id migration, `computeSpawnTransform` going async, the trigger-volume inspector's asset-pack browser, and `ItemStack.cleanCopy()` — and only `cleanCopy()` touched the documented surface (now in `docs/inventory.md`); the full API surface re-passes `verify-docs.sh` against the 0.5.7 jar with all hard gates green.) (Update 5 migrated the math library to JOML — vectors are now `org.joml.*` with Hytale `Vector*Util` companions and `Rotation3f`; see `docs/math.md`.)

**After a game update, start with the one-command wrapper** — it does the whole mechanical half of an update pass (snapshots the previous javap index for a jar→docs new-API diff, rebuilds both caches wipe-first, reports asset drift vs the baseline and per-class API drift, greps docs/examples for mentions of everything that changed, then runs the checker) and ends by printing the judgment checklist it deliberately does *not* automate (re-verifying flagged docs, documenting new API, stamp bumps, baseline refresh, commit):

```bash
./maintenance/scripts/update-build.sh              # full run; reports land in ~/.cache/hytale-update-report
./maintenance/scripts/update-build.sh --skip-caches   # reuse existing caches (re-triage after the first pass)
```

(Updates are detected automatically: `maintenance/scripts/check-for-update.sh` compares the installed jar version to the docs stamp — a weekly systemd user timer on the maintainer's machine runs it and raises a desktop notification plus `~/.cache/hytale-update-pending` when they diverge.)

Run the regression checker alone after doc edits (or before trusting/extending a doc):

```bash
./maintenance/scripts/verify-docs.sh          # full run (hard gates + advisories)
./maintenance/scripts/verify-docs.sh --no-build   # skip example compilation (faster)
```

It auto-resolves the jar/assets per-platform. **Hard gates** (fail the run): every `com.hypixel.*` class referenced in docs resolves via `javap`; every documented **member symbol** in `Receiver.member` form (where `Receiver` is a real jar class) exists on that class — walking superclasses for inherited members (`maintenance/scripts/check-symbols.py`, calibrated to skip JSON/DSL key paths, prose negative examples, locally-declared example types, and private-but-present members); all intra-doc anchor links resolve; and all example projects compile. **Advisory/INFO**: referenced asset paths exist, and **asset drift vs the two baselines** — `maintenance/baseline/CommonAssetsIndex.hashes` (Hytale's own Common index) and `maintenance/baseline/ServerAssetsIndex.hashes` (our generated index of `Server/`+`Cosmetics/`, where the JSON data configs live — regenerate via `maintenance/scripts/hash-server-assets.sh`); changed assets mean re-verifying the docs that reference them. See `maintenance/baseline/README.md` for the drift workflow; refresh both baselines after re-verifying against a new build.

## Maintenance invariants

Hard-won rules from the 2026-07-19 quality pass. Treat these as repo law, not suggestions:

1. **Zero-warning invariant.** `verify-docs.sh` passes with **zero warnings** as of 2026-07-19. Any new WARN is a signal, not a backlog item: fix it, or add an audited skip-list entry with a justification, the same day it appears. A warning list that stays non-empty becomes wallpaper — before calibration, 21 genuinely fabricated JSON shapes hid for weeks among ~100 unread warnings in the (then opt-in) fields check.
2. **No shared-tree git operations during parallel agent work.** When running multiple doc agents concurrently: give each agent an explicit, disjoint set of files it may edit, and forbid `git stash` / `git checkout` / `git reset` — agents verify with the maintenance scripts, never by baselining the tree. (Or isolate agents in separate worktrees.) A mid-flight `git stash` by one parallel agent clobbered concurrent edits during the 2026-07-19 pass and cost a full reconciliation sweep.
3. **Never automate the stamp bump.** A page's "Verified against X" line is a *claim that re-verification actually happened*, and the claim is the handbook's core differentiator. `update-build.sh` deliberately stops at a printed judgment checklist — keep the mechanical/judgment boundary exactly where it is, even though auto-bumping would be easy.
4. **Known-accepted verification gap** (don't rediscover it): behavior changes behind *unchanged* method signatures are undetectable by the current pipeline — mitigated only by the gotcha-string checks and lambda-signature leakage in the javap diff. Accepted 2026-07-19; revisit only if it demonstrably bites.
5. **Page-size seam rule.** These docs are designed for AI-agent consumption, and oversized pages burn agent context. When a page crosses roughly 1,500–2,000 lines, split it along its existing section seams, following the `items.md` → `items-*.md` and `interactions.md` → `interactions-*.md` precedent.

Two of the three follow-up levers are now built (2026-07-19): the **snippet-compilation hard gate** (`maintenance/scripts/check-snippets.py`, run by `verify-docs.sh`) — any ` ```java ` block starting with `package ` is a complete compilation unit and must compile against the jar; same-doc same-package blocks co-compile, fragments are exempt; write new walkthrough code as complete units so it opts in. (The class of bug it catches is real: 18 snippets called `sendMessage` on the entity `Player`, which has no such method — the symbol checker cannot type local variables, and its first run also exposed a fabricated `AssetStore` walkthrough.) And **`docs/llms.txt`** for AI-retrieval findability — generated from page frontmatter by `maintenance/scripts/generate-llms-txt.sh`; regenerate + commit when pages or descriptions change (verify-docs WARNs when stale). The remaining lever: expanding the coverage advisory's denominator beyond `server.core`/`component`/`math` to the `builtin.*` packages. Distribution, not quality, stays the open strategic work.

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
- **examples/events/**: both event mechanisms side by side — global bus (`PlayerConnectEvent`/`PlayerDisconnectEvent`) and an ECS `EntityEventSystem` for `BreakBlockEvent` (query-filtered to players, chat via `getPlayerRef()`)
