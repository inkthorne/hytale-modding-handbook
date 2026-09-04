# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complete reference for Hytale server plugin development containing:
- **docs/**: Comprehensive API documentation (65 markdown files)
- **examples/**: Standalone, runnable mods — six Gradle plugin projects plus two no-code asset packs

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

The `docs/` were fact-checked against game **0.6.3** (build-26) — `HytaleServer.jar`'s `Implementation-Version` is `0.6.3` (API docs via `javap` on the jar and the decompiled source cache; JSON-asset/DSL docs against the extracted `Assets.zip`). They are only known-accurate as of that build — a game update can silently invalidate them.

The 0.5.9 → 0.6.3 pass was the largest since the handbook began: 1,334 `com.hypixel.*` classes added, 143 removed, 1,790 changed, plus ~1,700 `Server/` and ~780 `Common/` assets drifted. Every one of the 65 pages was re-verified page-by-page, and the per-page evidence is in the commit history rather than here. Structural breaks worth knowing: the NPC core-component API was decomposed so every sensor/action/motion/instruction callback now takes `ExecutionSupport` instead of `Role` (and the failure mode is *silent* for a concrete override without `@Override`); protocol serialization moved from Netty `ByteBuf` to `java.lang.foreign.MemorySegment` across 413 packets; `Inventory` is deprecated wholesale for `InventoryComponent`; `AbstractCommand.canGeneratePermission()` was replaced by `requireNoPermission()`; the 76 `hytalegenerator.density.nodes` classes were replaced by `hytalegenerator.assets.density`; and two new subsystems arrived with their own pages (`docs/world-events.md`, `docs/encounters.md`).

**What that pass revealed about the gates, which matters more than the delta.** Most of what it corrected was not 0.6.3 drift at all — it was pre-existing error that every green run had missed, in four places no checker looks:

- **Bare-signature fences and method tables.** `check-symbols.py` only binds `Receiver.member` forms, so a fence of plain signatures under a `### ClassName` heading is verified by nothing. Dead methods survived here for at least a build.
- **JSON keys and `"Type"` values in prose examples.** A fabricated key, an invented enum value, or a whole invented section reads exactly like a real one. Several pages carried shapes that could not decode; one documented an item field that no shipped asset uses.
- **Asset ids inside JSON examples.** `check-symbols.py` deliberately skips JSON/DSL key paths and the asset-path advisory only checks strings shaped like paths, so a bare item id in an example is checked by nothing. `drops.md` carried 31 ids that existed in neither 0.6.3 *nor* 0.5.9 — invention, not drift.
- **Player-facing strings in `Server/Languages/en-US/server.lang`.** The gotcha-string advisory searches the jar only, so a quoted `.lang` message can never trace however it is written.

Two habits follow from that, and both earned their place the hard way. **Audit the page, not a detector's output** — reading what a regex matched tells you why it fired, never whether it was right; to judge whether a page documents Java, count `**Package:**` headings, ```java fences and `| Method |` tables. And **never judge a codec key from a windowed view** — builder chains are single statements thousands of characters long, so a line- or column-truncated read silently drops a validator or a required flag and yields a *confident wrong answer*; parse whole `append(...)` groups through to their closing `.add()`, and remember requiredness has two forms (a `true` third argument to `KeyedCodec`, and `Validators.nonNull()`).

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

It auto-resolves the jar/assets per-platform. **Hard gates** (fail the run): every `com.hypixel.*` class referenced in docs resolves via `javap`; every documented **member symbol** in `Receiver.member` form (where `Receiver` is a real jar class) exists on that class — walking superclasses for inherited members (`maintenance/scripts/check-symbols.py`, calibrated to skip JSON/DSL key paths, prose negative examples, locally-declared example types, and private-but-present members); all intra-doc anchor links resolve; and all example projects compile. Checks report a denominator where they can ("N doc(s) scanned, M of K candidates examined", "5 of 1091 java block(s)") — a check that narrates only its failures cannot be audited, and the snippet gate in particular is opt-in and covers a small fraction of the corpus by design. The doc-type consistency check is calibrated by `maintenance/scripts/doctype-skiplist.txt`, whose header records the audit method; stale entries are reported rather than left to re-suppress silently. **Advisory/INFO**: referenced asset paths exist, and **asset drift vs the two baselines** — `maintenance/baseline/CommonAssetsIndex.hashes` (Hytale's own Common index) and `maintenance/baseline/ServerAssetsIndex.hashes` (our generated index of `Server/`+`Cosmetics/`, where the JSON data configs live — regenerate via `maintenance/scripts/hash-server-assets.sh`); changed assets mean re-verifying the docs that reference them. See `maintenance/baseline/README.md` for the drift workflow; refresh both baselines after re-verifying against a new build.

## Maintenance invariants

Hard-won rules from the 2026-07-19 quality pass and the 2026-09-03 0.6.3 update pass. Treat these as repo law, not suggestions:

1. **Zero-warning invariant.** `verify-docs.sh` passes with **zero warnings** as of 2026-07-19. Any new WARN is a signal, not a backlog item: fix it, or add an audited skip-list entry with a justification, the same day it appears. A warning list that stays non-empty becomes wallpaper — before calibration, 21 genuinely fabricated JSON shapes hid for weeks among ~100 unread warnings in the (then opt-in) fields check.
2. **No shared-tree git operations during parallel agent work.** When running multiple doc agents concurrently: give each agent an explicit, disjoint set of files it may edit, and forbid `git stash` / `git checkout` / `git reset` — agents verify with the maintenance scripts, never by baselining the tree. (Or isolate agents in separate worktrees.) A mid-flight `git stash` by one parallel agent clobbered concurrent edits during the 2026-07-19 pass and cost a full reconciliation sweep.
3. **Never automate the stamp bump.** A page's "Verified against X" line is a *claim that re-verification actually happened*, and the claim is the handbook's core differentiator. `update-build.sh` deliberately stops at a printed judgment checklist — keep the mechanical/judgment boundary exactly where it is, even though auto-bumping would be easy.
4. **Known-accepted verification gap** (don't rediscover it): behavior changes behind *unchanged* method signatures are undetectable by the current pipeline — mitigated only by the gotcha-string checks and lambda-signature leakage in the javap diff. Accepted 2026-07-19; revisit only if it demonstrably bites.
5. **Page-size seam rule.** These docs are designed for AI-agent consumption, and oversized pages burn agent context. When a page crosses roughly 1,500–2,000 lines, split it along its existing section seams, following the `items.md` → `items-*.md` and `interactions.md` → `interactions-*.md` precedent. **Currently in deliberate arrears** (deferred during the 0.6.3 pass so that splitting did not churn pages while 20+ agents were re-verifying them): `blocks.md` 3,150, `interactions-flow.md` ~2,525, `ui-api.md` ~1,854, `inventory.md` ~1,826. Recorded seams: `blocks.md` → the connected-block sections (~380 lines) and `## Java API Reference` onward (~1,100); `inventory.md` → `## Crafting System` onward (~600).
6. **Report a denominator, not just findings.** A check that narrates only what it caught cannot be audited: nobody can tell a clean run from a run that examined nothing. Every gate should print what it *scanned* alongside what it *found* — `check-symbols.py`'s `CHECKED_MEMBERS`, the snippet gate's "5 of 1091 java block(s)", the doc-type check's "65 doc(s) scanned, 0 of 1 candidate(s) examined". This is not cosmetic: the snippet gate's green line read as corpus coverage for a year while compiling 3 of 61 stamped pages.
7. **Audit the page, not the detector's output.** Reading a heuristic's matches tells you why it fired, never whether it was right — so any skip-list entry needs evidence the check itself cannot see. The 0.6.3 pass produced three separate wrong answers from this one mistake, including a four-page skip list justified by reading the very regex it was meant to calibrate. Related: never judge a codec key from a line- or column-truncated view; those builder chains are single statements thousands of characters long and a windowed read fails by producing a *confident* wrong answer, not a blank. The specific trap is that the chain is full of constructs that look like termini and are not — `append(...)`'s closing paren closes a syntactically complete call, but the validator that decides requiredness attaches *after* it, on the builder, before `.add()`. So parse to the `.add()`, not to the first balanced paren: `PluginManifest.CODEC` read that way reports no required keys at all, when `Name` carries `Validators.nonNull()` two calls further along. The same shape catches regexes, and one registration demonstrates both halves at once: `CustomConnectedBlockTemplateAsset`'s `Shapes` key is `new KeyedCodec("Shapes", new MapCodec<…>, true)` — **raw**, so any pattern expecting `KeyedCodec<T>` skips it silently and undercounts the codec; and carrying `true` as its third argument, so it is the one *required* key of that asset's four while the other three pass `false`. Miss the generic and you lose the key; stop before the third argument and you keep the key but lose its requiredness.

Two of the three follow-up levers are now built (2026-07-19): the **snippet-compilation hard gate** (`maintenance/scripts/check-snippets.py`, run by `verify-docs.sh`) — any ` ```java ` block starting with `package ` is a complete compilation unit and must compile against the jar; same-doc same-package blocks co-compile, fragments are exempt; write new walkthrough code as complete units so it opts in. (The class of bug it catches is real: 18 snippets called `sendMessage` on the entity `Player`, which has no such method — the symbol checker cannot type local variables, and its first run also exposed a fabricated `AssetStore` walkthrough.) And **`docs/llms.txt`** for AI-retrieval findability — generated from page frontmatter by `maintenance/scripts/generate-llms-txt.sh`; regenerate + commit when pages or descriptions change (verify-docs WARNs when stale). The remaining lever: expanding the coverage advisory's denominator beyond `server.core`/`component`/`math` to the `builtin.*` packages.

**Queued after the 0.6.3 pass** — three gates for the blind spots that pass exposed, in the order they earn their keep:
1. **A registration/type-value oracle.** Every `CODEC.register("X", …)` call site gives a *closed* set of legal `"Type"` values per codec, so a fabricated discriminator can be reported with no skip list and no false-positive tail. `"Type"` appears on nearly every JSON page; a fabricated `"Type": "Wall"` shipped for at least a build.

   **This gate must also check cardinality and closure claims, and they must not be split out into a gate of their own.** They are the most fragile sentences in the corpus: a codec gaining one key falsifies a closure claim silently, with nothing on the page changing. Nothing catches that today, because every existing check runs one direction only — the fields check confirms *documented → real* and never *real → documented*.

   **Build the negative-closure half first.** The claims split unevenly, and the smaller half is the one that looks easier. Roughly 6 are *cardinality* — "accepts six keys", "has exactly two values" — and roughly 20 are *negative closure*: "there is no `"Self"`", "these nine keys are the whole of `DamageEffects`", spread over a dozen pages. A count beside a table is bidirectional and needs the doc side parsed (find the table, count its rows). A negative-closure claim is one-directional — it is falsifiable only *real → documented*, precisely the direction nothing covers — and needs nothing parsed on the doc side but the quoted name. So the larger group is also the one carrying the value and the cheaper one to implement.

   It has to ride on this gate rather than stand alone because counting a codec's keys needs exactly the whole-chain parse this gate already needs. A naive regex version was measured at a **44% false-positive rate** (4 of 9 claims flagged, all four the checker's bug, none the docs'). One of the four — raw vs parameterized `KeyedCodec` — is cheaply fixed by matching both forms. The other three are not reachable by any shortcut: map-wrapped keys, inheritance from a base interaction, and enums existing twice with different casing in `protocol` and `server` (`InteractionTarget` is `{User, Owner, Target}` in one and `{USER, OWNER, TARGET}` in the other, and `EnumStyle.detect` renders both to the same JSON, so the duplicate is invisible in assets and lethal only to a checker resolving the simple name). So the honest figure is **33% irreducible**, which is the argument: what survives the cheap fix is exactly the whole-chain work this gate already does. Shipping that tail would violate invariant 1 directly. Every claim checked by hand in September 2026 was correct, so there is no live defect driving this — build it when the parser exists, not before. **The Java-symbol subset is the exception and does not wait on the parser**: denials of a *method or class* rather than a JSON key are already visible to `check-symbols.py`, whose `NEG` guard suppresses exactly those lines and could instead assert them — see the note at that suppression, which records the two requirements and why the naive version accuses correct pages.
2. **A signature-block checker** for bare-signature fences. Bind the fence to the type its heading or an in-fence comment names (`// InventoryComponent (instance)`), honouring `Outer.Nested`, and trust a heading only when at least one signature under it resolves there. A prototype found 19 verified-dead signatures the current gates cannot see.
3. **An asset-id gate**, typed by key position — an id is only checkable when the gate knows which key it sits under and therefore which directory to resolve it against. Resolving against all of `Server/` passes real-but-wrong-kind ids for the wrong reason. State which asset families it covers: item ids happen to be `Capital_Snake_Case`, so recall looks fine there and would be near-zero elsewhere.

Also worth doing when that code is next touched: give the gotcha-string matcher a fragment mode (split the documented string on `%s`/placeholders and require each fragment in one jar literal) and a second corpus (`Server/Languages/en-US/server.lang`), and make `verify-docs.sh`'s metadata filtering structural rather than a hand-maintained `grep -vE` list. Distribution, not quality, stays the open strategic work.

## Architecture

### Plugin Structure
- Plugins extend `JavaPlugin` and override `setup()` to register commands
- Each plugin requires a `manifest.json` in `src/main/resources/` with `Group`, `Name`, and `Main` fields (PascalCase). Only `Name` is actually enforced — it is the sole key carrying `Validators.nonNull()` in `PluginManifest.CODEC` — but `Main` is what names the entry-point class, so a plugin without it loads as content only. That is precisely what the two packs are: no `Main`, and the manifest at the pack root rather than under `src/main/resources/`, since there is no Gradle build to place it.
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
- **examples/item-respawner/**: the stateful-block example — a custom block with a block-entity component, a ticking system over the chunk store, a spawned item entity that persists across reloads, and a press-F GUI that edits the block's state in the world

Two of the eight are **packs, not plugins**: pure JSON content the game loads directly, with no Java, Gradle or art. They exist because the shortest path into modding shouldn't require a compiler.

- **examples/custom-food/**: one item (`Food_Hearty_Snack`) defined in a single JSON file, reusing shipped art and effects; its player-facing text lives in `Server/Languages/en-US/server.lang`
- **examples/custom-drop/**: overrides the chicken's shipped loot table so that snack drops in the world — and demonstrates that packs *compose*, referencing another pack's content by id

Note the denominator when reading the example-build gate: it reports **6 builds, not 8**, because the two packs have nothing to compile. That is full coverage of the compilable examples, not a gap — but the packs are consequently checked by no hard gate, so their asset ids and `.lang` keys rest on the same blind spots described above.
