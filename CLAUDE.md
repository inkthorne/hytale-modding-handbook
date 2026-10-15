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

Like the assets cache, the script **wipes the cache first**, so classes removed or renamed in a new build don't linger and mask dead references. Re-run it after a game update. Before wiping a cache built from a different jar, it saves that cache to `~/.cache/hytale-update-snapshot`, which is the previous-build record `update-build.sh` diffs against. Running it by hand therefore never loses that record. A scratch cache set with `HYTALE_JAR_CACHE` gets its own store beside it and never touches the default one. (Direct `javap` against the jar still works for one-off lookups; the cache just makes broad sweeps cheap.)

## Verifying documentation

The `docs/` were fact-checked against game **0.7.2** (build-34). `HytaleServer.jar`'s `Implementation-Version` is `0.7.2`. API docs were checked with `javap` on the jar and against the decompiled source cache; JSON-asset and DSL docs against the extracted `Assets.zip`. They are only known-accurate as of that build — a game update can silently invalidate them.

The 0.6.8 → 0.7.2 pass (2026-10-14/15, diffed from build-31 as one step) was the largest since 0.6.3:
- **Drift:**
  - Common assets: 1,158 modified, 3,971 added, 576 removed.
  - `Server/`+`Cosmetics/`: 2,121 modified, 5,350 added, 681 removed.
  - API: 504 classes added, 72 removed, 850 changed. These count binary class names, so anonymous and local classes (`Foo$1`) are included.
  - Source: 259 body-only changes and 59 `@Deprecated` lines added or removed.
- **Scale of the edit:** 72 pages changed across the pass's commits, and every topic page was re-read and re-stamped.
- **Two structural breaks:**
  - The treasure-map objective was **removed outright**, with no replacement: its task, chest block, event, two interactions and nine assets are gone.
  - **Block access moved from `World`/`WorldChunk` to section ECS.** Both lost their block APIs. Reads now go through `SectionReader` or the `BlockSection` component, after resolving a section ref with `ChunkStore.getChunkSectionReferenceAtBlockAsync`; writes go through the static `BlockOperations.setBlock`. The new `docs/block-access.md` documents this, and `world-chunks.md` and `blocks-java-api.md` were rescoped around it.
- **Pipeline changes:**
  - `triage_drift.py` now folds anonymous and local classes (`Foo$1`) onto their enclosing class. Before that, the triage matched their binary names as text and flagged them against nearly every page: 59 noise rows, which between them also flagged the examples' Gradle and deploy files. The fixture is at 181 checks and 32 mutations.
  - The registry and codec fixtures were re-derived by hand. The recount came from `maintenance/scripts/hand-registry-recount.py`, which shares no code with the miner and reproduced the 0.6.8 figures first (`registry-oracle-notes.md` §15). That recount first matched, like the miner, only qualified registrations (`Receiver.FIELD.register(` and `getCodecRegistry(Receiver.FIELD)`). So neither saw 69 unqualified in-class sites in 20 classes: `TriggerVolumeShape`'s `CODEC.register("Box", …)`, `ItemDropContainer`, `MusicContainer`, `Condition` and others. 18 registries were absent from the miner, and `Condition.CODEC` was short by 15 names. The review of this pass found it; agreement certified nothing there, because the two shared the predicate. Closed 2026-10-15: the miner binds a bare field by lexical scope, and the recount binds the same sites by a different route. They agree live, per registry, at 0.7.2 and 0.6.8 (`check-registry-fixture.py`, 183 agreement checks). UNRESOLVED is 0, and a synthetic tree plus 14 mutations pin the binding rules.

**As in the 0.6.3 pass, much of what was corrected was not drift.** It was pre-existing error that no gate checks:
- About 80 invented asset ids and invalid array-entry shapes in the interactions pages.
- About 25 wrong claims across the items pages.
- About 20 `UPPER_SNAKE` enum lists in `trigger-volumes.md` that could never decode.
- Keyed-event examples built on `PlayerInteractEvent`, which nothing in the jar dispatches.
- A `setCustomHud` that never existed.
- A `getQuery()`-returns-`null` idiom that throws at registration.

None of these was in a form a gate reads: enum values, array-entry shapes, requiredness, and asset ids inside JSON fences are all unchecked. That is the measured case for gate 3 below.

The 0.6.3 → 0.6.8 pass (2026-09-23; builds 27–30 were never installed locally, so it was diffed as one step) was small:
- **Assets:** translation-only drift. 4 `Server/Languages` files changed (`pt-BR`/`uk-UA`/`zh-CN` `server.lang` plus `uk-UA/wordlists.lang`), none added or removed. Common was content-identical; Hytale only re-ordered its index.
- **API:** 22 classes changed or added, almost all internal (QUIC/ICE networking, a new `io.ConnectionRegistry`, worldgen prop internals).
- **Plugin-facing changes:** `AccessControlModule.getDisconnectReason(UUID)` became public. `ban(Ban)` and `/kick` disconnect through the new `ConnectionRegistry`; whether 0.6.3 kicked on ban cannot be checked, because its source was not kept. Custom `AccessProvider`s now also gate asset-editor connections. All three are in `docs/permissions.md`; the last two are body changes that the 22-class signature diff did not show, and the review found them. The server also refuses to boot inside the launcher install directory unless given `--allow-install-dir` (`startup.InstallDirGuard`; a gotcha in `docs/universe-saves.md`).
- **Stamps and claims:** every page stamp was bumped. So were the in-prose claims about the *current* build: shipped-asset counts, "still deprecated", "registered as of", "verified against the jar". That was 77 in the pass, plus 12 more the review found missed (among them `02-structure.md`'s running-version example, left saying 0.6.3). Each one's source asset is byte-identical or its class is signature-identical, and the deprecation and behaviour claims were re-read in the new decompiled source. Introduction markers (`0.6.3+`, "as of 0.6.3", "removed by 0.6.3") were deliberately left alone, because they date a change rather than assert the present.

One gap surfaced that invariant 4 did not name: `javap-index.txt` is built with `javap -p -constants`, which prints no annotations, so **a class gaining or losing `@Deprecated` is invisible to the API diff.** Closed the same day by the source-drift section described in invariant 4, which reports `@Deprecated` lines added or removed.

The review of that pass found two more, and both come down to one rule: **signature identity vouches only for signatures.**
- **Method bodies.** A claim about what a method *does* can rot with no signature change. `KickCommand`'s body moved onto `ConnectionRegistry` and never appeared in the diff (invariant 4's accepted gap, now seen in practice).
- **Compile-time constants.** javac inlines a `static final int` into every reader, so a search for its *name* finds only the declaration. `world-chunks.md` claimed "nothing in the jar reads" `SetBlockSettings.NO_FIRE_ON_BREAK` and gave it a fire-related intent. It is read as the literal `0x1000` in `BlockHarvestUtils.fireOnBreakInteraction`, and it suppresses the `OnBreak` interaction. The pass re-checked that claim by name and "confirmed" it. To show a documented constant unread, search for its **value**. The source drift catches a *changed* reader, since the literal sits in the reader's body, but a claim that nothing reads a constant is still a manual search.

The 0.5.9 → 0.6.3 pass was the largest since the handbook began: 1,334 `com.hypixel.*` classes added, 143 removed, 1,790 changed, plus ~1,700 `Server/` and ~780 `Common/` assets drifted. Every one of the 65 pages that existed at the time was re-verified page-by-page, and the per-page evidence is in the commit history rather than here. Structural breaks worth knowing: the NPC core-component API was decomposed so every sensor/action/motion/instruction callback now takes `ExecutionSupport` instead of `Role` (and the failure mode is *silent* for a concrete override without `@Override`); protocol serialization moved from Netty `ByteBuf` to `java.lang.foreign.MemorySegment` across 413 packets; `Inventory` is deprecated wholesale for `InventoryComponent`; `AbstractCommand.canGeneratePermission()` was replaced by `requireNoPermission()`; the 76 `hytalegenerator.density.nodes` classes were replaced by `hytalegenerator.assets.density`; and two new subsystems arrived with their own pages (`docs/world-events.md`, `docs/encounters.md`).

**What that pass revealed about the gates, which matters more than the delta.** Most of what it corrected was not 0.6.3 drift at all — it was pre-existing error that every green run had missed, in four places no checker looks:

- **Bare-signature fences and method tables.** `check-symbols.py` only binds `Receiver.member` forms, so a fence of plain signatures under a `### ClassName` heading is verified by nothing. Dead methods survived here for at least a build.
- **JSON keys and `"Type"` values in prose examples.** A fabricated key, an invented enum value, or a whole invented section reads exactly like a real one. Several pages carried shapes that could not decode; one documented an item field that no shipped asset uses.
- **Asset ids inside JSON examples.** `check-symbols.py` deliberately skips JSON/DSL key paths and the asset-path advisory only checks strings shaped like paths, so a bare item id in an example is checked by nothing. `drops.md` carried 31 ids that existed in neither 0.6.3 *nor* 0.5.9 — invention, not drift.
- **Player-facing strings in `Server/Languages/en-US/server.lang`.** The gotcha-string advisory searches the jar only, so a quoted `.lang` message can never trace however it is written.

Two habits follow from that, and both earned their place the hard way. **Audit the page, not a detector's output** — reading what a regex matched tells you why it fired, never whether it was right; to judge whether a page documents Java, count `**Package:**` headings, ```java fences and `| Method |` tables. And **never judge a codec key from a windowed view** — builder chains are single statements thousands of characters long, so a line- or column-truncated read silently drops a validator or a required flag and yields a *confident wrong answer*; parse whole `append(...)` groups through to their closing `.add()`, and remember requiredness has two forms (a `true` third argument to `KeyedCodec`, and `Validators.nonNull()`).

**After a game update, start with the one-command wrapper** — it does the whole mechanical half of an update pass (snapshots the previous javap index and decompiled source, rebuilds both caches wipe-first, reports asset drift vs the baseline, per-class API drift, and source drift — the body-only and `@Deprecated` changes a signature diff cannot see — then triages which docs/examples mention everything that changed, and runs the checker) and ends by printing the judgment checklist it deliberately does *not* automate (re-verifying flagged docs, documenting new API, stamp bumps, baseline refresh, commit):

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
4. **Behaviour behind unchanged signatures: detected, not judged.** This was accepted as undetectable on 2026-07-19. It bit in the 0.6.8 pass: `KickCommand`'s body changed with no signature change, and a constant's reader was missed. It has been narrowed since 2026-09-23, over two review rounds.
   - **Where the record lives.** The previous build's javap index, decompiled source and per-class bytecode hashes are kept in `~/.cache/hytale-update-snapshot`. `build-jar-cache.sh` saves them there itself, just before it wipes a cache that was built from a **different jar**. So running it by hand after an update is safe. A scratch cache (`HYTALE_JAR_CACHE`) gets its own store, `<cache>.snapshot`. Each snapshot records the cache it came from, and a different cache never replaces it. Two runs at once against one store are not supported.
   - **How a build is identified.** By the jar's sha256, recorded in `cache-meta.txt`, never by the version string. The first cut keyed on the version string, and a jar without `Implementation-Version` then compared a build with itself. An unstamped cache never replaces an existing snapshot. `update-build.sh` also warns whenever the snapshot is content-identical to the installed build, or when it cannot prove otherwise (a byte-identical index with no hashes to compare).
   - **What section 5b reports.** It diffs the two decompilations of `com.hypixel.hytale.*` and lists every top-level class whose source changed while its own signatures did not, plus every `@Deprecated` added or removed. The triage flags pages naming those classes.
   - **Failed decompiles.** CFR renders a method it cannot decompile as the same stub whatever the bytecode says (0.6.8 has 9 such methods in 8 files, one of them `PluginManager.loadManifest`). For those files 5b compares the bytecode hashes of the file's classes, nested ones included, and reports any change as `BYTECODE`. It reports `BLIND`, with a WARN, when a side has no hashes to compare.
   - **Incomplete decompiles.** 5b warns unless both sides' decompile completed. It also warns about any file present on one side only that the API drift does not explain as an added or removed class.
   - **The fixture.** `check-update-build-fixture.py` holds all of this to generated jars. `verify-docs.sh` runs its 181-check base pass. Its `--mutations` pass reverts each guard the three review rounds and the 0.7.2 triage fix added: 32 mutations, each of which must turn its named checks red. It takes ~13 min, too slow for every run, so **run it by hand whenever `build-jar-cache.sh`, `update-build.sh` or `triage_drift.py` changes**. A guard with no mutation is untested; the round-3 review found six.
   - **Noise.** An unchanged caller can re-render when a class it calls changes: review found a cast appearing when the callee's generics changed. So `BODY` rows can include callers of a changed API. A different decompiler between the two caches re-renders everything, and the script warns when the recorded decompilers differ.
   - **What remains is judgment.** The diff says a body changed, never whether a documented claim still holds. A `BYTECODE` row cannot even show *what* changed; read the class with `javap -c`.
   - **Not covered, and not tested** (noted in the round-2 review and left for later). Two gaps. First, the jar's non-class resources: `migration/blocks/{0_1,1_2,2_3,3_4}.json`, the block-id migrations, are in no drift section, since the javap index, class hashes and decompiled source cover classes only and the asset baselines cover `Assets.zip` only. A changed or added migration file surfaces nowhere; list them with `unzip -Z1 HytaleServer.jar | grep -v '\.class$'` and diff by hand. Second, the Vineflower decompiler path in `build-jar-cache.sh` has never been run: every run and the fixture use CFR, so a `vineflower` on `PATH`, which the script prefers over a cached CFR jar, is untested. That covers its output layout, its failure behaviour and the one-file-per-top-level-class assumption behind the partial-decompile guard.
5. **Page-size seam rule.** These docs are designed for AI-agent consumption, and oversized pages burn agent context. When a page crosses roughly 1,500–2,000 lines, split it along its existing section seams, following the `items.md` → `items-*.md` and `interactions.md` → `interactions-*.md` precedent. **The list of pages in deliberate arrears now lives in `maintenance/page-size-arrears.txt`, not in this paragraph** — it records which pages are deferred and where they cut, and `verify-docs.sh` measures every page against it on every run, WARNing in both directions (over the line and unlisted; listed but no longer over) and FAILing if the list parses to nothing. Sizes are deliberately **absent** from that file and the gate prints the live figure instead: a recorded size is precisely what went stale twice on 2026-09-04. The arrears themselves date from the 0.6.3 pass, where splitting was deferred so that it did not churn pages while 20+ agents were re-verifying them. Why the list moved out of here at all: for a year nothing measured page sizes, so this list was only ever checked when a human chose to measure — and re-reading a list cannot reveal an omission, because the omission is the thing missing from what you are reading. Three pages went over the line unlisted that way. **`npc-roles.md` was split on 2026-09-04** and is no longer in arrears: 1,925 → **1,411**, with `## Spawn Beacons` / `## Companion Block Spawners` / `## SpawnNPC Interaction` moved to `npc-spawning.md` (325) and `## Melee attacks without a CAE` / `## Combat Action Evaluator (CAE)` to `npc-combat.md` (227). It had been over the threshold and *unrecorded* since before that pass — a page above the line but missing from that list is how an arrear goes quiet, which is what the list exists to prevent — and, since 2026-09-04, what the gate enforces rather than trusting a reader to notice.
6. **Report a denominator, not just findings.** A check that narrates only what it caught cannot be audited: nobody can tell a clean run from a run that examined nothing. Every gate should print what it *scanned* alongside what it *found* — `check-symbols.py`'s `CHECKED_MEMBERS`, the snippet gate's "5 of 1091 java block(s)", the doc-type check's "N doc(s) scanned, M of K candidate(s) examined, S audited-skip, P Package-line citation(s) on Q page(s) treated as provenance, F page(s) fell below threshold because of it" (quoted as its *shape*: an invariant that exists to make figures trustworthy should not itself carry a figure that rots every time a page is added — this one read "65 doc(s)" while the gate had been scanning 69 and printing a counter the example did not mention). This is not cosmetic: the snippet gate's green line read as corpus coverage for a year while compiling 3 of 61 stamped pages.
7. **Audit the page, not the detector's output.** Reading a heuristic's matches tells you why it fired, never whether it was right — so any skip-list entry needs evidence the check itself cannot see. The 0.6.3 pass produced three separate wrong answers from this one mistake, including a four-page skip list justified by reading the very regex it was meant to calibrate. Related: never judge a codec key from a line- or column-truncated view; those builder chains are single statements thousands of characters long and a windowed read fails by producing a *confident* wrong answer, not a blank. The specific trap is that the chain is full of constructs that look like termini and are not: `append(...)`'s closing paren closes a syntactically complete call, but the validator attaches *after* it, on the builder, before `.add()` (for a `RecordCodec`, which has no `.add()`, it sits *inside* the append group as the third argument). So parse to the `.add()`, not to the first balanced paren: `PluginManifest.CODEC` read that way reports no null-validated keys at all, when `Name` carries `Validators.nonNull()` two calls further along.

   **"Required" is two facts, and the parser reports them separately** (`maintenance/probes/requiredness/`, measured against the 0.7.2 jar on 2026-10-15; until then this invariant treated them as one).
   - `null_validated`: the field's validator chain holds an instance of `NonNullValidator`, that is `Validators.nonNull()` and its subclasses `nonEmptyArray()` and `nonEmptyMap()`. Matching the text `nonNull()` misses 21 keys.
   - `strict_null`: a `true` third argument to `KeyedCodec`. It **never makes an omitted key fail, on any decode path**. Its only effect is that an explicit JSON `null` is decoded rather than treated as absent on the BSON inherit path.
   - Even `null_validated` is necessary, not sufficient. `BuilderField.nullValidate` reads the field through the getter, so a key whose field already holds a non-null default accepts its own omission. Of 545 null-validated keys in the 1,257 classes that decode, the engine rejects the omission of 258 and accepts it for 252.
   - Only the engine settles it: `effective-required.py` decodes `{}` through each real codec and reads which keys it names.
   - A Parent satisfies a nonNull key only if the key was declared `appendInherited`.
   - Codec-level validators and `afterDecode` hooks can reject an empty document with no key attached (5 classes), and no per-key attribute sees them.

   **The trap pair, restated.** `CustomConnectedBlockTemplateAsset`'s `Shapes` is `new KeyedCodec("Shapes", new MapCodec<…>, true)`. It is **raw**, so a pattern expecting `KeyedCodec<T>` skips it and undercounts the codec; and it is `strict_null`, not required: deleting it from a shipped asset still decodes. `ConnectedBlockPatternRule` declares a key also named `Shapes` as `new KeyedCodec("Shapes", new SetCodec<…>(…, true))`: two arguments, the `true` inside the inner constructor, and not `strict_null`. Nothing but which paren the `true` sits inside tells them apart, so an argument splitter must track `<>` as well as `()`. The attribution still matters, but the dangerous direction moved. A parser mistake now only misplaces a flag; **calling a flag-only key required** is what tells a modder to write a key the engine does not want, and no shipped asset can contradict it. 608 keys are in that state in the parser's population, and the review of the 0.7.2 pass found 34 handbook claims of this and related kinds. Evidence in `maintenance/registry-oracle-notes.md` §5.
8. **A review finding is fixed by a follow-up commit, never by touching the reviewed commit.** Once a commit exists, do not amend it, rebase it, or hang a `git notes` correction on it — write the fix as a new commit whose message says what was wrong and cites the review. This is not a history-purity rule; it is about where the information ends up. A `git notes` correction lives in `refs/notes/commits`, which no clone fetches by default, no gate reads, no page renders and no grep of the working tree finds — so a correction filed there is invisible to exactly the people the correction is for. It happened on 2026-09-04: a wrong claim in `79075d7`'s message (that `TriggerSpawnMarkers`' `Count: 0` contradicted its codec doc, when the two agree) was corrected by a note, and the correction reached the repo only when the note was noticed and moved into `maintenance/registry-oracle-notes.md`. **A fact worth correcting is worth committing.** If the wrong claim is in a commit message only, the follow-up commit is where the correction goes; if it is also a claim about the subject matter, it belongs in the docs or the notes file as well, because that is what the next session actually reads. The related memory rule — repair with `git notes` rather than a rewrite — is about content accidentally filed under an unrelated *subject* during parallel work, and does not extend to correcting claims.

Two of the three follow-up levers are now built (2026-07-19): the **snippet-compilation hard gate** (`maintenance/scripts/check-snippets.py`, run by `verify-docs.sh`) — any ` ```java ` block starting with `package ` is a complete compilation unit and must compile against the jar; same-doc same-package blocks co-compile, fragments are exempt; write new walkthrough code as complete units so it opts in. (The class of bug it catches is real: 18 snippets called `sendMessage` on the entity `Player`, which has no such method — the symbol checker cannot type local variables, and its first run also exposed a fabricated `AssetStore` walkthrough.) And **`docs/llms.txt`** for AI-retrieval findability — generated from page frontmatter by `maintenance/scripts/generate-llms-txt.sh`; regenerate + commit when pages or descriptions change (verify-docs WARNs when stale). The remaining lever: expanding the coverage advisory's denominator beyond `server.core`/`component`/`math` to the `builtin.*` packages.

**Queued after the 0.6.3 pass** — three gates for the blind spots that pass exposed. **Read this before the order: every defect that motivated these three has been fixed, and gate 1 is closed.** Gate 1's two fabrications were repaired on the day it found them; gate 2's 19 dead signatures and gate 3's 31 invented ids were both repaired in the 0.6.3 pass itself, before either gate existed. What remains is fragility checking against *future* rot with no known live defect behind it, which earns its keep at the next game update through `update-build.sh` rather than now. Building more instruments here was stopped on 2026-09-05 for that reason, not because the designs are wrong. **One property shapes all of them and is permanent:** every check in this suite runs *documented → real* and none runs *real → documented*. The fields check confirms a documented key exists; nothing reports a real key nobody documented, a codec that gained one, or a claim that something does **not** exist. That is why a closure claim can be falsified by a new build with nothing on the page changing, and it is a design input for gate 3 as much as it was for gate 1.
1. **A registration/type-value oracle — CLOSED 2026-09-05, and deliberately incomplete.** Do not resume the unbuilt half; the maintainer ruled the remaining steps out of the queue rather than deferring them. What shipped, all live hard gates in `verify-docs.sh` with fixtures under `maintenance/fixtures/`: **(a)** `codec_parser.py`, the whole-chain parser (44/44 golden types, 7 traps); **(b)** `registry_miner.py`, all three registration forms in both spellings — qualified (`Receiver.CODEC.register(…)`) and unqualified in-class (`CODEC.register(…)`, `getCodecRegistry(PAGE_CODEC)`), the latter bound to the class that declares the field by lexical scope with no superclass rule (69 sites in 20 classes at 0.7.2, UNRESOLVED pinned at 0; see `registry-oracle-notes.md` §15) — with three verdicts — closed-and-covered, closed-with-gaps, and **open (not statically enumerable)**, because `MemoriesPlugin` registers `provider.getId()` in a loop and collapsing that into "closed" is a false zero exactly where a closure claim is least safe; **(c)** `check-type-values.py`, every `"Type"` in a docs JSON fence resolved against four oracles (all three registration forms, both spellings; shipped-asset `"Type"` values; **names the page registers in its own ```java fences**, since the walkthrough pages are self-registering; an audited skiplist, empty since 0.7.2 shipped assets using its one entry, `IntervalCondition`) — 201 distinct values, 0 unresolved, and it found two fabrications on its first run (what neither spelling covers is counted, not assumed: no registry is held in a variable, and every `getCodecRegistry(` with a non-field argument is one of three `PluginBase` declarations, pinned in `check-registry-fixture.py`; the oracle is unscoped, so the unqualified registries' common-word names such as `Single`, `Random`, `Switch` and UIEditor's `Text`/`Number` are accepted in any slot, and `check-type-values.py -v` lists the 11 docs values only an unqualified registration supplies); and **(e)** `check-defaults.py`, every documented `Default` cell against the value the field holds, with `section_binder.py` binding a section to its codec class.

   **What was NOT built, and why — one line each, so nobody re-derives the reasoning.** *Scoping (c) to the slot:* the obvious key→codec binding was measured and is unsound, and the "safe subset" cannot be carved out because the instrument that would select it is the broken one (`registry-oracle-notes.md` §12). *Negative-closure claims and cardinality:* every such claim was hand-verified correct in September, so the instrument cost exceeded the defect yield — and the cheap shortcut is already excluded rather than untried, because a naive regex version was measured at a **44% false-positive rate** (4 of 9 claims flagged, all four the checker's bug and none the docs') of which **33% is irreducible** without the whole-chain parse. **One exception, and it needs no parser:** denials of a *method or class* rather than a JSON key are already visible to `check-symbols.py`, whose `NEG` guard suppresses exactly those lines and could instead assert them — ~7 `Receiver.member` denials plus ~4 bare-class ones, all verified holding against build-26. The finished brief lives at that suppression, including the two hard requirements and why the naive version accuses correct pages (43% of denied names are near-misses of real members **on the same class**, which is structural: a denial earns its place on a page precisely because the wrong name is plausible). *Asset-usage-count claims:* same, and never started. The common reason is measured rather than asserted: across gate 1 the instruments found **two** fabrications, both by (c) on day one, while step 5 compared 84 rows and found the docs correct every time — against gate 2's prototype, which found 19 verified-dead signatures.

   **The two things a successor must not re-derive.** (c) is unscoped **on purpose**: it checks a value is registered *somewhere*, not that it is legal in its *slot*, so it catches invention and is blind to misattribution — the `"Type": "Wall"` this entry once cited as its motivating defect would have **passed**, for two independent reasons. And a *fabricated required key can never be contradicted by a shipped asset* (an asset omitting an optional key looks exactly like one omitting a key nobody needs), whereas a fabricated optional fails loudly the first time someone omits it — which is why invariant 7's `Shapes` trap runs in the dangerous direction.

2. **A signature-block checker** for bare-signature fences — **not built, and its motivating figure is stale.** The design still stands: bind the fence to the type its heading or an in-fence comment names (`// InventoryComponent (instance)`), honouring `Outer.Nested`, and trust a heading only when at least one signature under it resolves there — that last rule is load-bearing, and dropping it takes the same corpus from 116 flags to 588. **What this entry said for two days was that "a prototype found 19 verified-dead signatures". That is true history and false as a claim about the corpus: all 19 were fixed on 2026-09-03 during the 0.6.3 pass** ("all 19 previously verified-dead signatures cleared, with zero true positives remaining"), and nobody had re-derived it before it was used to rank this gate above others. Re-derived 2026-09-05 by `maintenance/scripts/check-sigblocks.py` — a review-only reconstruction, not a gate: **2,653 signatures, 2,140 bound, 116 flagged (5.4%), and zero confirmed live defects**, with four known false-positive classes (constructors, example code with bodies, first-candidate-not-best receivers, nested types). Read that script's header before reviving this.
3. **An asset-id gate, typed by key position — BUILT and HARD since 2026-10-15.** Its first run's 43 flags were all real (42 invented ids and one id of the wrong kind), and were fixed in the commit that promoted it. Files: `maintenance/scripts/check-asset-ids.py`; its fixture `check-asset-ids-fixture.py --mutations` (28 cases, 22 mutations, run by `verify-docs.sh`); the recall replay `measure-asset-id-recall.py`; the corpus `maintenance/fixtures/asset-ids/`; and the pre-registered typing snapshot `maintenance/baseline/AssetIdTyping.txt`.
   - **What it does.** Every string value in a docs JSON fence is typed by its key position and resolved in the asset store that position refers to. A store is a `setPath` directory the jar registers, and an id is the file stem.
   - **Typing.** A position class (parent.key, bare key or parent.*) is typed when it has ≥5 distinct shipped values and ≥90% of them resolve in one store. N=5 and P=0.90 were pre-registered. Ties pass in either store. Two widenings are read from the shipped assets: stores resolving the exact (parent, key), and values shipped verbatim under the key. A bare key needs ≥3 distinct parents to speak for a parent it was never seen under. `Weapons` is why: it holds item ids in NPC roles, but item Family tag names on an item `Ability`.
   - **Counted exemptions.** Values that are not id-shaped; a generated-state `*Id_State_X`; a prefix or quoted id named by the page's *own* placeholder paragraph; an example pack's ids on a page that names the pack; and an id defined by a path on the line before a fence, for that path's family only.
   - **Measured on 0.7.2.** 18,473 files swept, 108 stores, 475 typed classes. 3,722 values, of which 968 sit at typed positions: 876 resolved, 49 exempt, 43 failed, 0 false positives, and no skiplist.
   - **Recall on ids removed by hand.** drops.md (`d003f50`): 31/31. interactions (`d58a7a1`): 79/120 (66%), under the pre-set ~70% line and reported, not tuned away. All 41 misses are at untyped positions: 30 values in namespaces that are not file stems (`ChainId`, `ItemAnimationId`, `TargetNodeName`, `Id`, `Key`), and 11 map children with free-form keys under `Next`/`Failed` maps.
   - **Not covered, by design.** Map *keys* that are ids; Instances (directory-keyed); Prefabs and World (path-keyed bulk data); EncounterManager (not a `setPath` store); Common/ (cited by path); `.lang` keys; and every key with fewer than 5 shipped values. A green run proves ids at typed positions only. The store label on Parallel `Interactions`, `DefaultValue` and `ForkInteractions` flags reads Item/Interactions, although their codec is `RootInteraction`; a flag there is still correct.
   - **Cost.** About 14 s per run, nearly all of it the shipped-asset sweep.
   - **History.** Before this gate existed, the 0.6.3 pass fixed `drops.md`'s 31 invented ids and the 0.7.2 pass removed about 80 from the interactions pages.

Also worth doing when that code is next touched: give the gotcha-string matcher a fragment mode (split the documented string on `%s`/placeholders and require each fragment in one jar literal) and a second corpus (`Server/Languages/en-US/server.lang`), and make `verify-docs.sh`'s metadata filtering structural rather than a hand-maintained `grep -vE` list. Distribution, not quality, stays the open strategic work.

## Architecture

### Plugin Structure
- Plugins extend `JavaPlugin` and override `setup()` to register commands
- Each plugin requires a `manifest.json` in `src/main/resources/` with `Group`, `Name`, and `Main` fields (PascalCase). Only `Name` is actually enforced — it is the sole key carrying `Validators.nonNull()` in `PluginManifest.CODEC`, and decoding a manifest without it is the only omission that fails (measured) — but `Main` is what names the entry-point class, so a plugin without it loads as content only. That is precisely what the two packs are: no `Main`, and the manifest at the pack root rather than under `src/main/resources/`, since there is no Gradle build to place it.
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
