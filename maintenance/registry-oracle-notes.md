# Registry-oracle notes (input for queued gate 1)

Findings from the 2026-09-03 interaction-coverage pass, recorded here so they reach
whoever builds the registration/type-value oracle described in
[CLAUDE.md](../CLAUDE.md#verifying-documentation). Nothing here is a gate yet — these are
the constraints the gate has to satisfy, each with the evidence that produced it.

## 1. There are two registration forms, and mining only the first under-reports by 28%

The obvious form is a direct call on the codec:

```
grep -rn 'Interaction\.CODEC\.register("' ~/.cache/hytale-jar/src     # 89 names
```

The second goes through the plugin's registry handle, and nothing about it resembles the
first — the receiver is `getCodecRegistry(...)`, not `<Type>.CODEC`:

```
grep -rn 'getCodecRegistry(Interaction\.CODEC)' ~/.cache/hytale-jar/src   # 21 sites, 35 names
```

For `Interaction.CODEC` the two forms are **disjoint**: 89 + 35 = 124 registered types. An
oracle matching only the first form sees 72% of the vocabulary while reporting a clean run.

Three properties of the second form each break a naive matcher on their own:

- **The calls chain.** One statement can carry many names —
  `WorldEventsPlugin.java:125` registers seven `Context` types in a single expression. A
  line-oriented or first-match-per-line matcher takes one and drops the rest.
- **Ids can be constants.** `CameraPlugin.java:44` registers `CODEC_CAMERA_SHAKE`, defined
  as `"CameraShake"` at `CameraPlugin.java:34`. Resolve `static final String` constants
  per file before giving up on a name.
- **Ids can be runtime values** — see §2.

### Two variations that cut across *both* forms

Do not enumerate either of these — match the structure. Both were measured across the whole
decompiled corpus.

**The codec field is not always called `CODEC`.** Match `\.[A-Z_]*CODEC\b`. Counts by field:

| Field | via `getCodecRegistry` | direct (`X.<field>.register`) |
|---|---|---|
| `CODEC` | 44 | 578 |
| `TYPE_CODEC` | 14 | 0 |
| `PLUGIN_CODEC` | 10 | 1 |
| `PAGE_CODEC` | 3 | 1 |
| `OPERATION_CODEC` | 0 | 56 |

The field name is orthogonal to the registration form — `PLUGIN_CODEC` and `PAGE_CODEC` each
appear in both — so a per-form list of field names is wrong however it is drawn. A pattern
anchored on the literal `.CODEC` misses all of it silently; that is how the `CaveTypeGenerator`
row below (`TYPE_CODEC`, `WorldGenPlugin.java:91`) was nearly discarded as spurious *while
checking this very list*.

**The name is not always the first argument.** `register(Class, "Name", codec)` occurs at 18
sites, and it is not a rarity confined to odd corners: it is *every*
`GameplayConfig.PLUGIN_CODEC` and `WorldConfig.PLUGIN_CODEC` registration (plus the
asset-editor event registry). A `register\(\s*"` pattern sees none of them, so those two
registries' vocabularies — `Reputation`, `Objective`, `Stash`, `Wilderness`, `WorldEvents`,
`ForgottenTemple`, `Portal`, `PortalOrigin`, `Stamina`, `Instance`, `CreativeHub` — read as
empty. Note `Portal` here is `PortalGameplayConfig` on `GameplayConfig.PLUGIN_CODEC`, a
different registry from the `Portal` interaction: another instance of §4.

None of the 18 target `Interaction.CODEC`, so the 124-row figure in `docs/interactions.md` is
unaffected — but that was checked, not assumed.

**Nineteen** registries are reachable *only* through the second form and are therefore invisible
to a first-form-only sweep entirely, not merely undercounted. Keyed by fully-qualified declaring
type and codec field, each with zero first-form registrations:

`CameraEffect.CODEC`, `CaveTypeGenerator.TYPE_CODEC`, `ChoiceElement.CODEC`,
`CombatTextUIComponentAnimationEvent.CODEC`, `Content.TYPE_CODEC` (10 names),
`Context.TYPE_CODEC` (8), `EntityUIComponent.CODEC`, `EventAction.TYPE_CODEC` (13),
`EventLocation.Config.TYPE_CODEC`, `FarmingStageData.CODEC`, `GrowthModifierAsset.CODEC`,
`Op.TYPE_CODEC`, `PhysicsConfig.CODEC`, `RemovalCondition.CODEC`,
`SelectInteraction.EntityMatcher.CODEC`, `Shape.TYPE_CODEC`, `Spawner.Config.TYPE_CODEC`,
`SpreadGrowthBehaviour.CODEC`, `WorldConfig.PLUGIN_CODEC`.

Note `GameplayConfig.PLUGIN_CODEC` is *not* in that list despite ten second-form sites — it has
one first-form registration (`ReputationPlugin.java:75`), which is the kind of single exception
that makes "reachable only via form 2" a per-registry measurement rather than a per-file guess.
Two more registries gain members only
through it: `ChoiceInteraction` gains `GiveItem` (`ShopPlugin.java:44`) on top of
`StartObjective` (`ObjectiveShopPlugin.java:33`), and `RespawnController` gains
`ExitInstance` (`InstancesPlugin.java:164`) on top of `HomeOrSpawnPoint` / `WorldSpawnPoint`
(`AssetModule.java:196-197`).

> **Key the registry by its declaring type, not the receiver's simple name.** A sweep keyed on
> the simple name returned 17 second-form-only registries. Eleven survive checking; the other
> six — `Config`, `Content`, `Context`, `EventAction`, `Op`, `Shape` — are generic nested names
> that may collapse several distinct declaring types into one row, so their memberships cannot
> be trusted until re-keyed by the fully-qualified declaring type. (The registries themselves
> are real: `TriggerVolumesPlugin` genuinely registers on `Context.TYPE_CODEC` and
> `EventAction.TYPE_CODEC`. It is the *grouping* that is unsound, not their existence.) This is
> the same failure as matching a documented name across the whole corpus instead of within its
> section.

## 2. Some registries are not statically enumerable — the gate needs a third outcome

`MemoriesPlugin.java:137`:

```java
this.getCodecRegistry(Memory.CODEC).register(provider.getId(), codec.getInnerClass(), codec);
```

The id is `provider.getId()` — a runtime value, inside a loop over providers. No static
oracle can enumerate `Memory`'s vocabulary, and no amount of constant resolution helps.

**`Memory` is not the only one, and the shape is a taxonomy rather than a list.** A sweep that
flags every `register(` whose name-position argument is not a string literal or resolvable
constant finds three *categories*, which must not be collapsed:

**(a) Literal at the site** — directly enumerable. The common case.

**(b) Indirected: the id is a parameter, and the real names are at call sites one or more hops
up.** Statically resolvable, but by call-graph following, not by a grep at the registration
site. `ObjectivePlugin.registerTask(id, …)` (`ObjectivePlugin.java:252-253`) registers on both
`ObjectiveTaskAsset.CODEC` and `ObjectiveTask.CODEC`; its call sites supply `Craft`, `Gather`,
`UseBlock`, `UseEntity`, `TreasureMap`, `ReachLocation` (`ObjectivePlugin.java:173-178`) plus
`KillSpawnBeacon`, `KillSpawnMarker`, `Bounty`, `KillNPC` (`NPCObjectivesPlugin.java:69-72`).
`EventCondition.TYPE_CODEC` / `EventCondition.Config.TYPE_CODEC` are the same shape at a
further remove — `WorldEventsPlugin.registerCondition(...)` passes `conditionType.id()`, where
`conditionType` is an `EventCondition.Type`. A miner that stops at the registration site reports
these as empty; one that treats them as "open" understates what is knowable.

**(c) Genuinely open** — and this splits again, which matters for what a doc page may claim:

| Registry | Why open |
|---|---|
| `Memory.CODEC` (`MemoriesPlugin.java:137`) | `provider.getId()`, iterating runtime providers |
| `TriggerEffect.CODEC`, `TriggerCondition.CODEC`, `TriggerRule.CODEC` | public `registerEffectType` / `registerConditionType` / `registerRuleType` (`TriggerVolumesPlugin.java:195-222`) — **extension points with zero internal callers**; the built-ins are registered separately with literals at `:482`, `:491` |

The trigger-volume case is the important one. Those registries are *closed for built-ins and
open by design for mods* simultaneously, so a page may enumerate the built-ins but must never
claim the set is complete — a mod adding a trigger effect is the intended use of that API, not
a drift event. Detecting all of this is cheap and must be in the miner, not a follow-up: the
test is a negative one on argument shape, so a miner that silently skips what it cannot parse
reports these as closed-and-complete without ever noticing.

> Watch for a false positive here. `register(Priority.DEFAULT, "Name", …)` puts a non-literal in
> the *first* argument position while the id is still a literal in the second. A shape test that
> looks only at argument one flags roughly a dozen provider registries (`IWorldGenProvider`,
> `PlayerStorageProvider`, `FluidTicker`, …) as open when every one of them is closed.

`docs/world-events.md:125` documents `EventCondition`'s types under the heading "Built-ins
registered by `WorldEventsPlugin.setup()`" — a *scoped* claim rather than a closure claim, which
is the correct way to write about an open registry and happens to already be right. Preserve
that phrasing; do not "improve" it into "the full set of condition types".

So a registry has **three** possible verdicts, not two:

| Verdict | Meaning |
|---|---|
| closed, fully documented | every registered name resolves to a documenting section |
| closed, with gaps | the name set is known; some names are undocumented |
| **open — not checkable** | at least one registration site takes a non-literal id |

Collapsing the third into either of the others is the dangerous case. Reported as "closed,
fully documented" it is a false zero on precisely the registry where a closure claim is
least safe; reported as "closed, with gaps" it invents undocumented names that may not
exist. The gate must detect a non-literal, non-constant id argument and mark the whole
registry open, naming the site — and a doc page must not carry a closure claim about an
open registry at all.

## 3. Match documented names within the documenting section, never corpus-wide

Already recorded in CLAUDE.md invariant 7 and the `registry-oracle-is-the-coverage-denominator`
memory; restated here with the cases that proved it, because all four were *scored as
documented* by a global match and none of them were:

| Name | Global match landed on | Actually |
|---|---|---|
| `Bed` | `npc-roles.md:1392` — `"Value": "Bed"` | a block **tag**, not the interaction |
| `Teleporter`, `Portal` | `blocks.md:1322`, `items-blocks.md:724` | block-entity **component** names |
| `CameraShake` | `camera.md:393` | a protocol/runtime type and an asset folder |

## 4. One name can be registered on two different codecs

`ShowEventTitle` and `RunRootInteraction` are each registered **twice** — on
`TriggerEffect.CODEC` (`TriggerVolumesPlugin.java:482`, `:491`) and on `Interaction.CODEC`
(`InteractionModule.java:262`, `:288`). `trigger-volumes.md:126` and `:138` document the
trigger-effect ones. `BuilderTool` is an interaction type at `InteractionModule.java:232`
while `items-tools.md:1319-1367` documents `BuilderTool` as an embedded *item property*.

In all three cases a name-based checker finds documentation and marks the type covered,
when what is documented is a different thing wearing the same string. The oracle must bind
a name to the registry it is being checked for, not merely find the name.

The same collision corrupts **shipped-asset usage counts**, which is how it did real damage
here: `"Type": "CameraShake"` matches 49 assets, every one of them a `CameraEffect` asset under
`Server/Camera/CameraEffect/`, because `CameraPlugin` registers that string on `CameraEffect.CODEC`
(line 43) and on `Interaction.CODEC` (line 44). As an *interaction* it has zero uses. A count
mined by grepping `"Type": "<name>"` across the asset tree is only meaningful once each hit is
attributed to the registry its file belongs to. Of the 53 undocumented interaction types, **8**
carry a name registered on another codec and need that treatment: `CameraShake`, `ExitInstance`,
`Portal`, `RunRootInteraction`, `ShowEventTitle`, `StartObjective`, `Teleporter`, `UseEntity`.

> **The ambiguity check must fold in the *indirected* registries of §2(b), or it under-reports.**
> A first pass built the set from resolved registrations only and returned 7 — missing
> `UseEntity`, which is an `Interaction.CODEC` type *and* an `ObjectiveTask` registered through
> `ObjectivePlugin.registerTask(id, …)`. Because that registrar takes its id as a parameter, the
> name never appears at a registration site and no resolved-registration sweep can see it. Two of
> `UseEntity`'s four `"Type": "UseEntity"` assets are objectives
> (`Server/Objective/Objectives/`), not interactions, so its true interaction usage is **2**.
> `UseBlock` collides the same way but is already documented. The indirected registrars to expand
> are `registerTask`, `registerCompletion`, `registerEffectType`, `registerConditionType` and
> `registerRuleType`.

> **Derive that set from resolved registrations, never from literal counts.** Counting
> occurrences of a name's string literal looks like a cheap proxy and silently drops the worst
> case: `CameraShake` has **zero** string literals of its own name anywhere in the jar, because
> both of its registrations go through the constant `CODEC_CAMERA_SHAKE`. A literal-count method
> therefore misses the very name that motivates the check.

## 5. Parse codec chains structurally, or get a confident wrong answer

Two extractors written during this pass were wrong in ways that produced plausible output
rather than errors — the failure mode CLAUDE.md invariant 7 describes:

- **Stopping at the first `.build()`** truncated `SpawnNPCInteraction` two keys early: its
  chain contains `mapBuilder.build();` inside an `afterDecode` lambda. Parse to the
  statement-terminating `;` at paren depth 0.
- **`[^)]*` to reach a `KeyedCodec`'s third argument** missed that `"BlockSets"` is
  required in `RunOnBlockTypesInteraction`, because its codec argument
  (`new ArrayCodec<String>(Codec.STRING, String[]::new)`) contains parens. Balance the
  constructor call instead. All four of that codec's keys are required; the regex found three.

Requiredness has two forms and both must be read: a `true` third argument to `KeyedCodec`,
and `Validators.nonNull()` attaching to the builder *after* `append(...)` has closed.

**The `true`-third-argument trap is symmetric, and the false-positive half is the dangerous
one.** CLAUDE.md invariant 7 warns that stopping before the third argument loses a key's
requiredness. The mirror image manufactures it: an inner constructor's trailing `true`
attributed to the outer `KeyedCodec`. These two are visually identical —

```java
new KeyedCodec("Shapes", new MapCodec<…>, true)                                  // 3 args: REQUIRED
new KeyedCodec("ProjectileSpawnOffsets",
        new MapCodec<Vector3d, Object2ObjectOpenHashMap>(codec, ctor::new, true)) // 2 args: NOT required
```

— and both are *raw* `KeyedCodec`, so the generic gives no signal either. Telling them apart
needs an argument splitter that tracks `<>` as well as `()`: `MapCodec<Vector3d,
Object2ObjectOpenHashMap>` contains a top-level-looking comma inside its type parameters, and a
splitter that ignores angle brackets reports three arguments for the second form and calls a
non-required key required. Both a reviewer and this author's first splitter made exactly that
error on `DeployableTurretConfig.ProjectileSpawnOffsets` before angle-bracket handling was added.

A false "required" is worse than a false "optional": it tells a modder to write a key the engine
does not want, and nothing in the corpus will contradict it.

## 6. Prefer a phrasing that names a real symbol over prose stating the same fact

`docs/interactions.md` had to say which types are always available. Two phrasings carry the
same fact:

- "the 76 rows registered by `InteractionModule` and `ProjectileModule`" — checked by nothing.
- "the 76 rows whose owner is listed in `Constants.CORE_PLUGINS` (`Constants.java:65`)" — a
  `Receiver.member` form, so `check-symbols.py` binds it. Writing it this way took the
  member-symbol count from 818 to 819 and the gate resolved it.

The second fails the run if the field is renamed or removed; the first goes stale in silence.
When a sentence can be anchored to a real symbol, anchor it — this is a cheap way to move a
claim onto a checked surface, and it is general, not specific to this page.

## 7. Scope decision: `BrushOperation.OPERATION_CODEC` (56 names, undocumented)

Recorded as a decision rather than left as an omission. `BuilderToolsPlugin.java:711-766`
registers **56** scripted-brush operations on `BrushOperation.OPERATION_CODEC` — a small DSL
with control flow (`jump`, `jumpifblocktype`, `jumpifcompare`, `loop`, `loopcircle`,
`looprandom`, `exit`, `breakpoint`), masks (`mask`, `appendmask`, `historymask`,
`useoperationmask`), and state (`persistentdata`, `savebrushconfig`, `loadint`). It appears in
31 shipped assets and in **zero** handbook pages.

Both this pass's registry sweep and the audit that preceded it missed it, for the §1 reason:
the receiver is `OPERATION_CODEC`, not `.CODEC`. It is genuine modding surface — builder tools
are creative-mode tooling — but documenting 56 operations is a project of its own, larger than
the 56 undocumented interaction types currently queued. **Status: known, sized, deferred** —
not out of scope, and not to be rediscovered as a surprise by the next coverage pass.

## 8. Validate anchors with the gate's own slugger

`verify-docs.sh`'s slug function strips `[^\w\- ]`, so **underscores survive**, and it
numbers repeated headings `-1`, `-2`. A separately written slugger that strips underscores
reports `items-blocks.md#block_secondary-interaction` as broken when it resolves fine.
Re-use the function in `verify-docs.sh` rather than reimplementing it.

## 9. `server.lang` keys drop the `server.` namespace

CLAUDE.md lists giving the gotcha-string matcher a second corpus
(`Server/Languages/en-US/server.lang`) as worth doing when that code is next touched. One
detail decides whether that works, and getting it wrong looks exactly like a clean run.

Documented strings are written with the namespace, as the jar uses them —
`Message.translation("server.modules.learnrecipe.alreadyKnown")`. The `.lang` file does **not**
carry it: the file *is* `server.lang`, so its keys start one segment in, and the format is
`key = value` rather than JSON.

```
modules.learnrecipe.alreadyKnown = You already know the recipe for "{name}"!
interactions.didNotMount = Unknown mount error: {state}
```

`grep -c '^server\.' Server/Languages/en-US/server.lang` returns **0** — not one key carries the
prefix. A matcher that looks up the documented key verbatim finds nothing, every time, and
reports zero unresolved strings. Strip the leading `server.` before lookup — and treat a
whole-corpus zero-match rate as a bug in the matcher rather than a pass, per CLAUDE.md
invariant 6: a check that reports only findings, with no denominator, cannot be told apart
from one that examined nothing.

This is not hypothetical — it is how the six keys quoted in the `HarvestCrop`, `Bed` and
`LearnRecipe` sections were nearly recorded as missing. All six resolve once the prefix is
stripped.

## 10. Absence of a signal is not a pass — and the invariant applies to us, not only to gates

CLAUDE.md invariant 6 says a check must report a denominator, because a run that narrates only
findings cannot be told apart from one that examined nothing. Everything in that invariant is
written about the *gates*. Four times in the 2026-09-03 pass the same failure came from the
people and tools reading the gates instead:

| What looked like a pass | What it actually was |
|---|---|
| Class references stayed at **227** across 208 added lines naming seven jar classes | the `**Package:**` headings were written without the `com.hypixel.hytale.` prefix `verify-docs.sh:69` requires, so the gate matched none of them (§6) |
| A `server.lang` lookup returning zero unresolved keys | the keys drop the `server.` namespace, so nothing could ever match (§9) |
| "The verify run is still in the javap pass" | it had never started. `until ! pgrep -f 'verify-docs.sh'` matches the waiting shell's **own** command line, so the waiter blocked forever and the log was never created. `pgrep -c javap` was 0 throughout |
| "0 FAIL, 0 WARN" reported off a real log that contained a WARN | the log is ANSI-coloured. `grep -E '^  WARN'` cannot match `  \x1b[33mWARN\x1b[0m …`, so the pattern returned 0 on every run regardless of content |

The last one is the sharpest, because the pattern had been used across seven runs and was right
six times by luck — every one of those logs genuinely had no warning. A check that cannot fail
looks exactly like a check that passes, and it will accumulate a record of correct answers until
the first time it matters.

**A tool's track record is not evidence about the call you are making now.** `keys.py` reads
only `argv[1]`; passed six files it parsed one and returned well-formed output for that one,
which nearly recorded the four `DeployableConfig` subtypes as having no keys of their own when
`Turret` has 19 and `Aoe` has 12. It had been correct on every previous use — because every
previous use happened to pass a single file. A history of right answers is evidence only about
the calls whose inputs were shaped the way the tool assumes, and says nothing about this one.

**The general rule.** A check you wrote is not trustworthy until it has been run against an
input you *know* it must flag. The ANSI case was not a check that missed something — it was one
**structurally incapable of firing**, and that is indistinguishable from a clean result until you
feed it a known positive. Until then the first thing it ever tells you truthfully is a lie you
have already acted on.

**Validating the check is not enough — validate the input too.** The escape-stripped matcher
above was demonstrated to fire on a known-positive log, and then reported "0 WARN/FAIL" on an
83-byte file containing only `./maintenance/scripts/verify-docs.sh: No such file or directory`.
The run had died on a wrong working directory; the answer was true and worthless. **Assert the
log is a log** before reading it for warnings — require the summary line the script always
prints (`All hard checks passed` / `hard check(s) FAILED`) and treat its absence as "no result",
never as "no problems". A detector that cannot distinguish a clean run from a crashed one has
just moved the blind spot rather than closed it.

**Practical rules.** Strip escapes before matching a verify log
(`sed 's/\x1b\[[0-9;]*m//g'`), and prefer the summary line the script itself prints over a grep
you wrote. Never gate one run on `pgrep` for a name your own command line contains — use the
completion notification. And when a count does not move after a change that should have moved
it, treat the unchanged number as the finding rather than as confirmation.

## 11. Brief: the 44 interaction types still undocumented (handoff, 2026-09-04)

Written so a fresh session does not re-derive these counts with a fresh parser
and fresh mistakes. **Every number below came from a splitter that tracks `<>` as
well as `()`** — see §5 for why that matters — and each chain self-checked
`appends == keys found`; all 44 passed. Registry state when this was written:
124 registered types, 80 documented, 44 remaining.

### Method (ruled by hytale-supervisor, D1/D3)

- **Page-first.** Work one target page at a time, writing its rows *and* its
  sections together, one commit per page. Not row-first: it avoids two passes
  over the same rows and keeps each commit self-contained.
- **Section-vs-row rule.** A type earns its own section only if it has **two or
  more keys of its own** beyond the base interaction, or a real gotcha worth a
  paragraph. Otherwise document it *in the registry row itself* — a one-line
  description plus the FQCN, which closes the "not yet documented" cell honestly
  and makes the class gate-checkable, since `interactions.md` is tagged
  `Java API + JSON asset format` and FQCNs there are checked.
- **New sections use fully-qualified `**Package:**` headings.** The short form is
  invisible to `verify-docs.sh:69` — that is how the class-reference count sat
  frozen at 227 across 208 added lines. The 40 existing `config/none/X` path-style
  headings on the `interactions-*` pages stay as they are; converting them is a
  separate decision that was ruled against.
- **A page carrying real Java surface gets `Java API + JSON asset format`**, which
  short-circuits the doctype check before provenance runs. Do not land Java
  surface on a JSON-tagged page — see the brittleness note in
  `maintenance/fixtures/doctype/README.md`.
- **After each page:** repoint its registry rows, update *both* stated counts in
  `interactions.md` (the index lede and the registry preamble), re-derive them
  from the rendered table rather than decrementing, regenerate `llms.txt` if a
  page was added, and run the checker.

### Cautions specific to this tail

- **Two target pages are within one large slice of the split threshold.**
  `interactions-world.md` (1,378, and tied with `world.md` for the most tail rows
  at 9) and `items-tools.md` (1,427, 3 rows) are both under 1,500 now and could
  cross while this tail is written. `verify-docs.sh` measures every page against
  `maintenance/page-size-arrears.txt` on each run, so **check the page-size gate's
  output after each page commit rather than at the end** — a WARN there is
  same-day actionable under invariant 1, and catching the crossing on the commit
  that caused it is far cheaper than splitting a page you have just finished
  writing. `world.md` is already over and already listed: decide its split before
  writing into it, not after.

- **Eight of the 44 carry a name registered on another codec**, so any usage
  count mined by grepping `"Type": "<name>"` across assets is meaningless until
  each hit is attributed to the registry its file belongs to (§4). The eight are
  `CameraShake`, `ExitInstance`, `Portal`, `RunRootInteraction`, `ShowEventTitle`,
  `StartObjective`, `Teleporter`, `UseEntity` (already documented).
- **That same collision corrupted this brief's first draft.** A class resolver
  that took the first `register(…, X.class)` match regardless of registry mapped
  `ShowEventTitle` → `ShowEventTitleEffect` (7 keys, the *TriggerEffect*),
  `RunRootInteraction` → `RunRootInteractionEffect` (3), and `CameraShake` →
  `CameraShakeEffect` (2). The table below was rebuilt with resolution scoped to
  `Interaction.CODEC` in both registration forms; the corrected figures are 8, 1
  and 1. Any tool used against this tail must be registry-scoped, not name-scoped.
- **Registry-scoping is necessary but not sufficient — resolve the FQN from the
  registering file's imports.** Scoping to `Interaction.CODEC` gives you the right
  registration and therefore the right class *simple name*; it does not say which
  **file** declares it. Two classes are named `StartObjectiveInteraction`:
  `builtin/adventure/objectives/interactions/` (on `Interaction.CODEC`, one key
  `Setup`, required) and `builtin/adventure/objectiveshop/` (on
  `ChoiceInteraction.CODEC`, one key `ObjectiveId`, not required). **Both declare
  exactly one key**, so a count cross-check agrees while the key name and its
  requiredness are both wrong — which is how the row below was wrong until
  hytale-reviewer's independent parse caught it. Take the FQN from
  `ObjectivePlugin.java`'s own import list, never a glob on the simple name; a bare
  glob also returns the `protocol.` twin (a MemorySegment DTO with no codec) ahead
  of the server class for every type that has one.
- **Why the table below prefixes ten class names.** Ten of the 44 have an
  ambiguous simple name; each carries a `com.hypixel.hytale.protocol.` twin.
  Checked all ten: **every twin has zero `KeyedCodec` and zero `BuilderCodec`**,
  so globbing the simple name does not error — it silently yields **0 keys**. That
  is the dangerous shape here, because 23 of the 44 rows legitimately say 0 own
  keys, and a wrong-file zero is indistinguishable by inspection from a right one.
  Both tools used on this tail made exactly this class of mistake (registry
  ambiguity on one side, the simple-name glob on the other), which is why the
  disambiguation lives in the column a row-by-row reader consumes rather than in
  this bullet. `StartObjective` carries `objectives.interactions.`; the other nine
  carry `config.client.` or `config.none.`, both relative to
  `com.hypixel.hytale.server.core.modules.interaction.interaction.`. An unprefixed
  class name in that column is unambiguous in the tree — verified, not assumed.
- **`.appendInherited(...)` declares a key on *this* codec** — "Inherited" names the
  builder's self-type generic, not a parent's key. A parser matching only
  `.append(` scores 0 keys for roughly a third of these types while looking clean.
  Self-check `appends == adds == keys` per chain; it catches that and the
  wrong-file resolution both.
- **Three types have 0 *own* keys but a non-trivial parent.** `DragEraseBlock`,
  `ExtrudePlaceBlock` and `SurfaceDrawPlaceBlock` inherit `DragPlaceBlockInteraction.CODEC`
  (5 keys, `ForkInteractions` required), and `DragPlaceBlock` is already documented
  in `items-blocks.md`. A bare row saying "0 keys" reads as "takes no keys", which is
  false — point those three rows at the `DragPlaceBlock` material. Same shape for
  `StatsConditionWithModifier` over `StatsConditionBaseInteraction`.
  `ChangeActiveSlot`'s parent is `Interaction.ABSTRACT_CODEC`, not one of the three
  `Simple*` bases, so do not let its row claim base-interaction keys.
- **`CameraShake` gets a row, not a section**, and the row should say explicitly
  that the string is registered on both `CameraEffect.CODEC` and
  `Interaction.CODEC`, and that the interaction has **zero** shipped uses — all
  49 `"Type": "CameraShake"` assets are `CameraEffect` assets. Recording that is
  the point; "collides" alone will read as a typo.

### The 44

| Target page | `Type` | Implementing class | Own keys | Required | Verdict |
|---|---|---|---|---|---|
| `adventure.md` | `SetMemoriesCapacity` | `SetMemoriesCapacityInteraction` | 1 | — | row |
| `adventure.md` | `StartObjective` | `objectives.interactions.StartObjectiveInteraction` | 1 | `Setup` | row |
| `adventure.md` | `DestroyTreasureCondition` | `DestroyTreasureConditionInteraction` | 0 | — | row |
| `adventure.md` | `OpenTreasureContainer` | `OpenTreasureContainerInteraction` | 0 | — | row |
| `blocks.md` | `AugmentCondition` | `AugmentConditionInteraction` | 2 | RequiredAugmentTags | **section** |
| `camera.md` | `CameraShake` | `CameraShakeInteraction` | 1 | CameraEffect | row |
| `interactions-flow.md` | `IncrementCooldown` | `config.client.IncrementCooldownInteraction` | 5 | — | **section** |
| `interactions-flow.md` | `RunOnBlockTypes` | `RunOnBlockTypesInteraction` | 4 | Range,BlockSets,MaxCount,Interactions | **section** |
| `interactions-flow.md` | `StatsConditionWithModifier` | `StatsConditionWithModifierInteraction` | 1 | InteractionModifierId | row |
| `interactions-world.md` | `AddItem` | `AddItemInteraction` | 2 | ItemId | **section** |
| `interactions-world.md` | `CarryBlock` | `CarryBlockInteraction` | 1 | — | row |
| `interactions-world.md` | `CarryDroppedBlock` | `CarryDroppedBlockInteraction` | 0 | — | row |
| `interactions-world.md` | `CarryPlaceBlock` | `CarryPlaceBlockInteraction` | 0 | — | row |
| `interactions-world.md` | `DestroyBlock` | `DestroyBlockInteraction` | 0 | — | row |
| `interactions-world.md` | `DragEraseBlock` | `config.client.DragEraseBlockInteraction` | 0 | — | row |
| `interactions-world.md` | `ExtrudePlaceBlock` | `config.client.ExtrudePlaceBlockInteraction` | 0 | — | row |
| `interactions-world.md` | `PickBlock` | `config.client.PickBlockInteraction` | 0 | — | row |
| `interactions-world.md` | `SurfaceDrawPlaceBlock` | `config.client.SurfaceDrawPlaceBlockInteraction` | 0 | — | row |
| `inventory.md` | `IncreaseBackpackCapacity` | `IncreaseBackpackCapacityInteraction` | 2 | — | **section** |
| `inventory.md` | `ChangeActiveSlot` | `config.none.ChangeActiveSlotInteraction` | 1 | — | row |
| `inventory.md` | `OpenItemStackContainer` | `OpenItemStackContainerInteraction` | 0 | — | row |
| `items-blocks.md` | `ChangeFarmingStage` | `ChangeFarmingStageInteraction` | 4 | — | **section** |
| `items-blocks.md` | `UseCoop` | `UseCoopInteraction` | 0 | — | row |
| `items-crafting.md` | `OpenBenchPage` | `OpenBenchPageInteraction` | 1 | Page | row |
| `items-crafting.md` | `OpenProcessingBench` | `OpenProcessingBenchInteraction` | 0 | — | row |
| `items-tools.md` | `BuilderTool` | `config.none.BuilderToolInteraction` | 0 | — | row |
| `items-tools.md` | `PickupItem` | `PickupItemInteraction` | 0 | — | row |
| `items-tools.md` | `PrefabSelectionInteraction` | `PrefabSelectionInteraction` | 0 | — | row |
| `items.md` | `CheckUniqueItemUsage` | `CheckUniqueItemUsageInteraction` | 0 | — | row |
| `npc-spawning.md` | `SendBeacon` | `SendBeaconInteraction` | 4 | Message | **section** |
| `npc-spawning.md` | `TriggerSpawnMarkers` | `TriggerSpawnMarkersInteraction` | 3 | — | **section** |
| `npc-spawning.md` | `UseNPC` | `UseNPCInteraction` | 0 | — | row |
| `player.md` | `CanBreakRespawnPoint` | `CanBreakRespawnPointInteraction` | 0 | — | row |
| `player.md` | `ToggleGlider` | `config.client.ToggleGliderInteraction` | 0 | — | row |
| `trigger-volumes.md` | `RunRootInteraction` | `config.none.RunRootInteraction` | 1 | RootInteraction | row |
| `world.md` | `ShowEventTitle` | `ShowEventTitleInteraction` | 8 | Target,PrimaryTitle | **section** |
| `world.md` | `TeleportInstance` | `TeleportInstanceInteraction` | 8 | InstanceName,OriginSource | **section** |
| `world.md` | `RevealMapMarkersInView` | `RevealMapMarkersInViewInteraction` | 6 | — | **section** |
| `world.md` | `HubPortal` | `HubPortalInteraction` | 3 | WorldName | **section** |
| `world.md` | `Teleporter` | `TeleporterInteraction` | 3 | — | **section** |
| `world.md` | `ExitInstance` | `ExitInstanceInteraction` | 0 | — | row |
| `world.md` | `Portal` | `EnterPortalInteraction` | 0 | — | row |
| `world.md` | `PortalReturn` | `ReturnPortalInteraction` | 0 | — | row |
| `world.md` | `TeleportConfigInstance` | `TeleportConfigInstanceInteraction` | 0 | — | row |

Counts: **13 sections, 31 rows.** Target-page assignments are a starting
judgment, not a ruling — move a type if the page it acts on is a better home than
the plugin that registers it, which is how `DurabilityCondition` ended up in
`items-weapons.md` rather than with the other conditions.

### Key names for the 21 types that declare any (* = required)

Independently derived twice — once here, once by hytale-reviewer with a separately
written parser — and reconciled. All 44 counts and required-sets agree.

| `Type` | Keys |
|---|---|
| `AddItem` | `ItemId`*, `Quantity` |
| `AugmentCondition` | `RequiredAugmentTags`*, `Radius` |
| `CameraShake` | `CameraEffect`* |
| `CarryBlock` | `EntityEffectId` |
| `ChangeActiveSlot` | `TargetSlot` |
| `ChangeFarmingStage` | `Stage`, `Increase`, `Decrease`, `StageSet` |
| `HubPortal` | `WorldName`*, `WorldGenType`, `InstanceTemplate` |
| `IncreaseBackpackCapacity` | `From`, `Capacity` |
| `IncrementCooldown` | `Id`, `Time`, `ChargeTime`, `Charge`, `InterruptRecharge` |
| `OpenBenchPage` | `Page`* |
| `RevealMapMarkersInView` | `FieldOfView`, `MaxDistance`, `ScanInterval`, `RunWhile`, `ConditionGrace`, `RevealParticles` |
| `RunOnBlockTypes` | `Range`*, `BlockSets`*, `MaxCount`*, `Interactions`* |
| `RunRootInteraction` | `RootInteraction`* |
| `SendBeacon` | `Message`*, `Range`, `ExpirationTime`, `TargetGroups` |
| `SetMemoriesCapacity` | `Capacity` |
| `ShowEventTitle` | `Target`*, `PrimaryTitle`*, `SecondaryTitle`, `IsMajor`, `Icon`, `DurationS`, `FadeInDurationS`, `FadeOutDurationS` |
| `StartObjective` | `Setup`* |
| `StatsConditionWithModifier` | `InteractionModifierId`* |
| `TeleportInstance` | `InstanceName`*, `InstanceKey`, `PositionOffset`, `Rotation`, `OriginSource`*, `PersonalReturnPoint`, `CloseOnBlockRemove`, `RemoveBlockAfter` |
| `Teleporter` | `Particle`, `ClearOutXZ`, `ClearOutY` |
| `TriggerSpawnMarkers` | `MarkerType`, `Range`, `Count` |

> **`ShowEventTitle`'s `…S` suffixes are the interaction's, and are not a defect in
> `trigger-volumes.md`.** That page documents the *`TriggerEffect`* of the same name,
> whose keys are `Duration` / `FadeInDuration` / `FadeOutDuration` with no suffix —
> `ShowEventTitleEffect` and `ShowEventTitleInteraction` genuinely differ. This was
> raised in review as a pre-existing wrong-key claim on a documented page; it is not
> one. Checking it meant reading both classes rather than assuming the shared name
> implied a shared shape, which is the §4 discipline applied to a review finding.

### Progress and rulings applied while writing the tail (2026-09-04)

**The section-vs-row rule renders as (A), ruled by hytale-supervisor.** A row-verdict type is
documented *inside* `interactions.md`'s registry cell — description first, own keys with
requiredness, fully-qualified class last — and its target page is **not** edited. The target-page
column stays live only for grouping commits and for recording where a section would go if the type
is ever promoted. The argument that settles it is gate-checkability: the FQCN is verified because
`interactions.md` is tagged `Java API + JSON asset format`, and 12 of the 31 row-verdict types
target JSON-tagged pages where a FQCN must not land. One exception: if a target page already
enumerates the interactions its subsystem registers, omitting the type from that list would be a
false closure claim on that page — add the bare name to the existing list, and do not create such a
list where none exists.

The registry preamble now states this as a three-state contract keyed on the cell's first character
(link / prose / `— *not yet documented*`), which is why a prose cell that must point elsewhere puts
its link **after** the description.

**The re-derivation greps must be scoped to the registry section.** The obvious unscoped forms are
wrong: other three-column tables on `interactions.md` match the same row shape, and an unscoped
row-documented sweep returned **27** against a true value of **1**. The section-documented and
`not yet documented` counts happened to agree unscoped, which is exactly the shape invariant 6
warns about — two of three figures right by luck reads as a working method. The page now carries an
`awk`-scoped form, plus the check that the three states sum to the row count.

**Page re-assignments made against the §11 table** (which invites them):

- `SendBeacon` moved `npc-spawning.md` → **`npc-roles.md`**. The §11 assignment followed the
  registering plugin, but the page it landed on documents *spawn* beacons — an unrelated subsystem
  that merely shares the word. Putting a message-broadcast interaction under a heading three
  sections below `## Spawn Beacons` would have manufactured exactly the collision §4 exists to
  prevent. `npc-roles.md` already documents the receiving half (the `Beacon` sensor, and
  `NPCGroup`, which `TargetGroups` addresses), so the section sits beside what it needs.
- `TriggerSpawnMarkers` stayed on `npc-spawning.md`, but the page needed a fourth spawn source
  first: nothing documented manual spawn markers, and the interaction is unusable without them.

**Two findings the tail turned up that are worth keeping even if the rows change:**

- `SendBeacon`'s `"TargetGroups": ["Self"]` delivers to nobody. `SendBeaconInteraction` passes a
  hardcoded sender role index of `-1` into `WorldSupport.isGroupMember`, and the `$self` shortcut
  there needs the candidate's role index to equal the sender's. `Self` is a shipped group
  (`Server/NPC/Groups/Self.json`), so this is a plausible thing to write and it fails silently.
- `TriggerSpawnMarkers`'s `"Count": 0` fires *all* markers. Zero is both the default and the
  unlimited sentinel, and `greaterThanOrEqual(0)` accepts it, so the value that reads like "disable
  this" does the opposite.

### What hytale-reviewer's pass corrected, and the habit behind each miss

Kept here because both misses are reproducible mistakes, not one-off slips.

**A "no shipped asset does X" line is only as good as the grep's subject.** The
`SendBeacon` `Self` gotcha originally read as "`Self` is a trap", justified by a
grep scoped to *`SendBeacon`'s* uses (one debug item) while the claim it supported
was about *`TargetGroups`* generally. 41 shipped assets use `TargetGroups`, and
`["Self"]` appears in two of them — `Test_Kweebec_Playing.json` (×4) and the
production role `Template_Goblin_Scavenger.json` — through the **`Beacon` action**,
where it works. `ActionBeacon` passes `executionSupport.getRoleIndex()` and
`allowGlobal = false`; `SendBeaconInteraction` passes `-1` and `true`. Same
`BeaconBroadcast.broadcast`, two arguments swapped, opposite behaviour for both an
empty `TargetGroups` and `["Self"]`. The corrected gotcha is strictly better — it
has a positive control instead of resting on absence — which is the argument for
the habit: **scope the grep to the subject of the sentence, not to the type you
happen to be writing about.**

**"Never written as a `Type`" overstates, and it is invariant 7's dangerous
direction.** `Interaction.CODEC.register("UseNPC", …)` is live, so a mod may write
the type; what is true is that no *shipped* asset names it. In a table whose whole
job is saying which `Type` values are legal, "never written" reads as "not
writable" — a fabricated prohibition that no asset can contradict. The form to use
is **"No shipped asset names it"**, and it applies to every code-built-root type in
this tail (`UseNPC`, `OpenBenchPage`, `PickupItem`), each of which still needs its
own asset grep rather than an inherited assumption.

Two smaller corrections worth not repeating: the `Beacon` **action** sends and the
**sensor** receives (an earlier lede had actions reacting), and a three-state count
whose states are exhaustive **cannot** be validated by checking that it sums to the
row count — the sum is invariant under exactly the state move every tail edit makes.
Re-derive all three; never derive two and subtract.

**Page-size note.** `npc-roles.md` sits at **1,496** after the beacon section — four
lines under the gate. The next section landing there will trip it. The natural seam
is `## Beacon messaging` itself: `BeaconSupport`, `MessageSupport`, `EventSupport`
and `NPCMessage` are a real `components/messaging/` subsystem and none of them is
documented, so the cut would be to a new page rather than a rearrangement. It is not
recorded in `page-size-arrears.txt`, because that file is for pages already over the
line and listing an under-threshold page trips the gate the other way.
