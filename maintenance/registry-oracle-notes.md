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
