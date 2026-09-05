# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complete reference for Hytale server plugin development containing:
- **docs/**: Comprehensive API documentation. The page count is deliberately not written here — `verify-docs.sh` prints the live figure (`N page(s) measured`) on every run, and this line carried "65" for long enough to outlast three new pages.
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

The 0.5.9 → 0.6.3 pass was the largest since the handbook began: 1,334 `com.hypixel.*` classes added, 143 removed, 1,790 changed, plus ~1,700 `Server/` and ~780 `Common/` assets drifted. Every one of the 65 pages that existed at the time was re-verified page-by-page, and the per-page evidence is in the commit history rather than here. Structural breaks worth knowing: the NPC core-component API was decomposed so every sensor/action/motion/instruction callback now takes `ExecutionSupport` instead of `Role` (and the failure mode is *silent* for a concrete override without `@Override`); protocol serialization moved from Netty `ByteBuf` to `java.lang.foreign.MemorySegment` across 413 packets; `Inventory` is deprecated wholesale for `InventoryComponent`; `AbstractCommand.canGeneratePermission()` was replaced by `requireNoPermission()`; the 76 `hytalegenerator.density.nodes` classes were replaced by `hytalegenerator.assets.density`; and two new subsystems arrived with their own pages (`docs/world-events.md`, `docs/encounters.md`).

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

It auto-resolves the jar/assets per-platform. **Hard gates** (fail the run): every `com.hypixel.*` class referenced in docs resolves via `javap`; every documented **member symbol** in `Receiver.member` form (where `Receiver` is a real jar class) exists on that class — walking superclasses for inherited members (`maintenance/scripts/check-symbols.py`, calibrated to skip JSON/DSL key paths, prose negative examples, locally-declared example types, and private-but-present members); all anchor links resolve — the gate is **cross-doc**, not intra-doc as its own section label long said: a link naming a target file is checked against that file's anchors; and all example projects compile. Checks report a denominator where they can ("N doc(s) scanned, M of K candidates examined", "5 of 1091 java block(s)") — a check that narrates only its failures cannot be audited, and the snippet gate in particular is opt-in and covers a small fraction of the corpus by design. The doc-type consistency check is calibrated by `maintenance/scripts/doctype-skiplist.txt`, whose header records the audit method; stale entries are reported rather than left to re-suppress silently. **Advisory/INFO**: referenced asset paths exist, and **asset drift vs the two baselines** — `maintenance/baseline/CommonAssetsIndex.hashes` (Hytale's own Common index) and `maintenance/baseline/ServerAssetsIndex.hashes` (our generated index of `Server/`+`Cosmetics/`, where the JSON data configs live — regenerate via `maintenance/scripts/hash-server-assets.sh`); changed assets mean re-verifying the docs that reference them. See `maintenance/baseline/README.md` for the drift workflow; refresh both baselines after re-verifying against a new build.

## Maintenance invariants

Hard-won rules from the 2026-07-19 quality pass and the 2026-09-03 0.6.3 update pass. Treat these as repo law, not suggestions:

1. **Zero-warning invariant.** `verify-docs.sh` passes with **zero warnings** as of 2026-07-19. Any new WARN is a signal, not a backlog item: fix it, or add an audited skip-list entry with a justification, the same day it appears. A warning list that stays non-empty becomes wallpaper — before calibration, 21 genuinely fabricated JSON shapes hid for weeks among ~100 unread warnings in the (then opt-in) fields check.
2. **No shared-tree git operations during parallel agent work.** When running multiple doc agents concurrently: give each agent an explicit, disjoint set of files it may edit, and forbid `git stash` / `git checkout` / `git reset` — agents verify with the maintenance scripts, never by baselining the tree. (Or isolate agents in separate worktrees.) A mid-flight `git stash` by one parallel agent clobbered concurrent edits during the 2026-07-19 pass and cost a full reconciliation sweep.
3. **Never automate the stamp bump.** A page's "Verified against X" line is a *claim that re-verification actually happened*, and the claim is the handbook's core differentiator. `update-build.sh` deliberately stops at a printed judgment checklist — keep the mechanical/judgment boundary exactly where it is, even though auto-bumping would be easy.
4. **Known-accepted verification gap** (don't rediscover it): behavior changes behind *unchanged* method signatures are undetectable by the current pipeline — mitigated only by the gotcha-string checks and lambda-signature leakage in the javap diff. Accepted 2026-07-19; revisit only if it demonstrably bites.
5. **Page-size seam rule.** These docs are designed for AI-agent consumption, and oversized pages burn agent context. When a page crosses roughly 1,500–2,000 lines, split it along its existing section seams, following the `items.md` → `items-*.md` and `interactions.md` → `interactions-*.md` precedent. **The list of pages in deliberate arrears now lives in `maintenance/page-size-arrears.txt`, not in this paragraph** — it records which pages are deferred and where they cut, and `verify-docs.sh` measures every page against it on every run, WARNing in both directions (over the line and unlisted; listed but no longer over) and FAILing if the list parses to nothing. Sizes are deliberately **absent** from that file and the gate prints the live figure instead: a recorded size is precisely what went stale twice on 2026-09-04. The arrears themselves date from the 0.6.3 pass, where splitting was deferred so that it did not churn pages while 20+ agents were re-verifying them. Why the list moved out of here at all: for a year nothing measured page sizes, so this list was only ever checked when a human chose to measure — and re-reading a list cannot reveal an omission, because the omission is the thing missing from what you are reading. Three pages went over the line unlisted that way. **`npc-roles.md` was split on 2026-09-04** and is no longer in arrears: 1,925 → **1,411**, with `## Spawn Beacons` / `## Companion Block Spawners` / `## SpawnNPC Interaction` moved to `npc-spawning.md` (325) and `## Melee attacks without a CAE` / `## Combat Action Evaluator (CAE)` to `npc-combat.md` (227). It had been over the threshold and *unrecorded* since before that pass — a page above the line but missing from that list is how an arrear goes quiet, which is what the list exists to prevent — and, since 2026-09-04, what the gate enforces rather than trusting a reader to notice.
6. **Report a denominator, not just findings.** A check that narrates only what it caught cannot be audited: nobody can tell a clean run from a run that examined nothing. Every gate should print what it *scanned* alongside what it *found* — `check-symbols.py`'s `CHECKED_MEMBERS`, the snippet gate's "5 of 1091 java block(s)", the doc-type check's "N doc(s) scanned, M of K candidate(s) examined, S audited-skip, P Package-line citation(s) on Q page(s) treated as provenance, F page(s) fell below threshold because of it" (quoted as its *shape*: an invariant that exists to make figures trustworthy should not itself carry a figure that rots every time a page is added — this one read "65 doc(s)" while the gate had been scanning 69 and printing a counter the example did not mention). This is not cosmetic: the snippet gate's green line read as corpus coverage for a year while compiling 3 of 61 stamped pages.
7. **Audit the page, not the detector's output.** Reading a heuristic's matches tells you why it fired, never whether it was right — so any skip-list entry needs evidence the check itself cannot see. The 0.6.3 pass produced three separate wrong answers from this one mistake, including a four-page skip list justified by reading the very regex it was meant to calibrate. Related: never judge a codec key from a line- or column-truncated view; those builder chains are single statements thousands of characters long and a windowed read fails by producing a *confident* wrong answer, not a blank. The specific trap is that the chain is full of constructs that look like termini and are not — `append(...)`'s closing paren closes a syntactically complete call, but the validator that decides requiredness attaches *after* it, on the builder, before `.add()`. So parse to the `.add()`, not to the first balanced paren: `PluginManifest.CODEC` read that way reports no required keys at all, when `Name` carries `Validators.nonNull()` two calls further along. The same shape catches regexes, and one registration demonstrates both halves at once: `CustomConnectedBlockTemplateAsset`'s `Shapes` key is `new KeyedCodec("Shapes", new MapCodec<…>, true)` — **raw**, so any pattern expecting `KeyedCodec<T>` skips it silently and undercounts the codec; and carrying `true` as its third argument, so it is the one *required* key of that asset's four while the other three pass `false`. Miss the generic and you lose the key; stop before the third argument and you keep the key but lose its requiredness. **The trap is symmetric, and the inverse is worse.** `ConnectedBlockPatternRule` declares a key *also* named `Shapes` as `new KeyedCodec("Shapes", new SetCodec<…>(…, true))` — two arguments, the `true` inside the inner constructor, **not** required — against `CustomConnectedBlockTemplateAsset`'s `new KeyedCodec("Shapes", new MapCodec<…>(…), true)`, three arguments and required. Same key name, both raw, opposite requiredness, and nothing discriminates them but which paren the `true` sits inside; an argument splitter must therefore track `<>` as well as `()`, because the type parameters hide a top-level-looking comma. Attributing an inner constructor's `true` to the outer codec manufactures a requirement, and that direction is the dangerous one: a fabricated *required* can never be contradicted by a shipped asset — an asset omitting an optional key looks exactly like one omitting a key nobody needs — whereas a fabricated *optional* fails loudly the first time someone omits it. Evidence and the measured failures in `maintenance/registry-oracle-notes.md` §5.
8. **A review finding is fixed by a follow-up commit, never by touching the reviewed commit.** Once a commit exists, do not amend it, rebase it, or hang a `git notes` correction on it — write the fix as a new commit whose message says what was wrong and cites the review. This is not a history-purity rule; it is about where the information ends up. A `git notes` correction lives in `refs/notes/commits`, which no clone fetches by default, no gate reads, no page renders and no grep of the working tree finds — so a correction filed there is invisible to exactly the people the correction is for. It happened on 2026-09-04: a wrong claim in `79075d7`'s message (that `TriggerSpawnMarkers`' `Count: 0` contradicted its codec doc, when the two agree) was corrected by a note, and the correction reached the repo only when the note was noticed and moved into `maintenance/registry-oracle-notes.md`. **A fact worth correcting is worth committing.** If the wrong claim is in a commit message only, the follow-up commit is where the correction goes; if it is also a claim about the subject matter, it belongs in the docs or the notes file as well, because that is what the next session actually reads. The related memory rule — repair with `git notes` rather than a rewrite — is about content accidentally filed under an unrelated *subject* during parallel work, and does not extend to correcting claims.

Two of the three follow-up levers are now built (2026-07-19): the **snippet-compilation hard gate** (`maintenance/scripts/check-snippets.py`, run by `verify-docs.sh`) — any ` ```java ` block starting with `package ` is a complete compilation unit and must compile against the jar; same-doc same-package blocks co-compile, fragments are exempt; write new walkthrough code as complete units so it opts in. (The class of bug it catches is real: 18 snippets called `sendMessage` on the entity `Player`, which has no such method — the symbol checker cannot type local variables, and its first run also exposed a fabricated `AssetStore` walkthrough.) And **`docs/llms.txt`** for AI-retrieval findability — generated from page frontmatter by `maintenance/scripts/generate-llms-txt.sh`; regenerate + commit when pages or descriptions change (verify-docs WARNs when stale). The remaining lever: expanding the coverage advisory's denominator beyond `server.core`/`component`/`math` to the `builtin.*` packages.

**Queued after the 0.6.3 pass** — three gates for the blind spots that pass exposed. **Read this before the order: every defect that motivated these three has been fixed, and gate 1 is closed.** Gate 1's two fabrications were repaired on the day it found them; gate 2's 19 dead signatures and gate 3's 31 invented ids were both repaired in the 0.6.3 pass itself, before either gate existed. What remains is fragility checking against *future* rot with no known live defect behind it, which earns its keep at the next game update through `update-build.sh` rather than now. Building more instruments here was stopped on 2026-09-05 for that reason, not because the designs are wrong. **One property shapes all of them and is permanent:** every check in this suite runs *documented → real* and none runs *real → documented*. The fields check confirms a documented key exists; nothing reports a real key nobody documented, a codec that gained one, or a claim that something does **not** exist. That is why a closure claim can be falsified by a new build with nothing on the page changing, and it is a design input for gate 3 as much as it was for gate 1.
1. **A registration/type-value oracle — CLOSED 2026-09-05, and deliberately incomplete.** Do not resume the unbuilt half; the maintainer ruled the remaining steps out of the queue rather than deferring them. What shipped, all live hard gates in `verify-docs.sh` with fixtures under `maintenance/fixtures/`: **(a)** `codec_parser.py`, the whole-chain parser (44/44 golden types, 7 traps); **(b)** `registry_miner.py`, all three registration forms with three verdicts — closed-and-covered, closed-with-gaps, and **open (not statically enumerable)**, because `MemoriesPlugin` registers `provider.getId()` in a loop and collapsing that into "closed" is a false zero exactly where a closure claim is least safe; **(c)** `check-type-values.py`, every `"Type"` in a docs JSON fence resolved against four oracles (all three registration forms; shipped-asset `"Type"` values; **names the page registers in its own ```java fences**, since the walkthrough pages are self-registering; one audited skiplist entry) — 201 distinct values, 0 unresolved, and it found two fabrications on its first run; and **(e)** `check-defaults.py`, every documented `Default` cell against the value the field holds, with `section_binder.py` binding a section to its codec class.

   **What was NOT built, and why — one line each, so nobody re-derives the reasoning.** *Scoping (c) to the slot:* the obvious key→codec binding was measured and is unsound, and the "safe subset" cannot be carved out because the instrument that would select it is the broken one (`registry-oracle-notes.md` §12). *Negative-closure claims and cardinality:* every such claim was hand-verified correct in September, so the instrument cost exceeded the defect yield — and the cheap shortcut is already excluded rather than untried, because a naive regex version was measured at a **44% false-positive rate** (4 of 9 claims flagged, all four the checker's bug and none the docs') of which **33% is irreducible** without the whole-chain parse. **One exception, and it needs no parser:** denials of a *method or class* rather than a JSON key are already visible to `check-symbols.py`, whose `NEG` guard suppresses exactly those lines and could instead assert them — ~7 `Receiver.member` denials plus ~4 bare-class ones, all verified holding against build-26. The finished brief lives at that suppression, including the two hard requirements and why the naive version accuses correct pages (43% of denied names are near-misses of real members **on the same class**, which is structural: a denial earns its place on a page precisely because the wrong name is plausible). *Asset-usage-count claims:* same, and never started. The common reason is measured rather than asserted: across gate 1 the instruments found **two** fabrications, both by (c) on day one, while step 5 compared 84 rows and found the docs correct every time — against gate 2's prototype, which found 19 verified-dead signatures.

   **The two things a successor must not re-derive.** (c) is unscoped **on purpose**: it checks a value is registered *somewhere*, not that it is legal in its *slot*, so it catches invention and is blind to misattribution — the `"Type": "Wall"` this entry once cited as its motivating defect would have **passed**, for two independent reasons. And a *fabricated required key can never be contradicted by a shipped asset* (an asset omitting an optional key looks exactly like one omitting a key nobody needs), whereas a fabricated optional fails loudly the first time someone omits it — which is why invariant 7's `Shapes` trap runs in the dangerous direction.

2. **A signature-block checker** for bare-signature fences — **not built, and its motivating figure is stale.** The design still stands: bind the fence to the type its heading or an in-fence comment names (`// InventoryComponent (instance)`), honouring `Outer.Nested`, and trust a heading only when at least one signature under it resolves there — that last rule is load-bearing, and dropping it takes the same corpus from 116 flags to 588. **What this entry said for two days was that "a prototype found 19 verified-dead signatures". That is true history and false as a claim about the corpus: all 19 were fixed on 2026-09-03 during the 0.6.3 pass** ("all 19 previously verified-dead signatures cleared, with zero true positives remaining"), and nobody had re-derived it before it was used to rank this gate above others. Re-derived 2026-09-05 by `maintenance/scripts/check-sigblocks.py` — a review-only reconstruction, not a gate: **2,653 signatures, 2,140 bound, 116 flagged (5.4%), and zero confirmed live defects**, with four known false-positive classes (constructors, example code with bodies, first-candidate-not-best receivers, nested types). Read that script's header before reviving this.
3. **An asset-id gate**, typed by key position — an id is only checkable when the gate knows which key it sits under and therefore which directory to resolve it against. Resolving against all of `Server/` passes real-but-wrong-kind ids for the wrong reason. State which asset families it covers: item ids happen to be `Capital_Snake_Case`, so recall looks fine there and would be near-zero elsewhere. **Its motivating defect is gone too**: `drops.md`'s 31 invented ids were corrected in the same 0.6.3 pass (`a3f68ea`), and a re-check on 2026-09-05 found 47 distinct item ids in that page's JSON and **0** that name no shipped asset.

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
