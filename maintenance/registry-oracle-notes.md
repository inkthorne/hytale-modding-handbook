# Registry-oracle notes (input for queued gate 1)

Findings from the 2026-09-03 interaction-coverage pass, recorded here so they reach
whoever builds the registration/type-value oracle described in
[CLAUDE.md](../CLAUDE.md#verifying-documentation). Nothing here is a gate yet — these are
the constraints the gate has to satisfy, each with the evidence that produced it.

## 1. There are two registration forms, and mining only the first under-reports by 28%

> **Three, as of 2026-09-04.** This heading is left as written because the 28% is a
> real measurement of the first-vs-second gap, but a third form —
> `registerCoreComponentType`, ~176 names with no codec field anywhere in the
> statement — is the fourth correction at the end of this section. Read that before
> treating the two forms below as the whole surface.

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

### Four corrections to §1, from the phase-(b) miner (2026-09-04)

The miner reproduces §1's headline figures exactly — `Interaction.CODEC` at 124
names from 89 first-form and 35 second-form registrations across 21 second-form
statements, and all ten cells of the field table. Three things in §1 need
amending, and the first two are the kind §1 predicted about itself. A fourth
arrived a few hours later, from phase (c), and it is the largest of the four.

**The field table counts STATEMENTS, not registrations.** Its "via
`getCodecRegistry`" column reads 44 for `CODEC`; the miner counts 60 *registrations*
in 44 *statements*. Both are right and the distinction is the whole point of the
second form — §1 says so itself for `Interaction.CODEC` ("21 sites, 35 names") but
the table does not carry the word. Read that column as sites.

**The nineteen second-form-only registries are twenty-two.** Missing are
`Memory.CODEC`, `EventCondition.TYPE_CODEC` and `EventCondition.Config.TYPE_CODEC` —
all three have zero first-form registrations and belong in the list. They are
precisely the three §2 goes on to discuss as open or indirected, so the omission
looks like a scope slip between the two sections rather than a measurement error.
§1 warned that "an enumeration here would itself be a closure claim and would rot
the same way", and it did, in the same document, within a day.

**The "18 sites" of `register(Class, "Name", codec)` mixes two kinds of registry.**
Twelve are codec registrations, and they are exactly what §1 says — every
`GameplayConfig.PLUGIN_CODEC` and `WorldConfig.PLUGIN_CODEC` site. The rest are the
"asset-editor event registry", which is
`getEventRegistry().register(AssetEditorActivateButtonEvent.class, "EquipItem", handler)`
and six siblings in `AssetSpecificFunctionality.java`: the same *argument shape*,
but an event-handler registry with no codec and no `"Type"` vocabulary. For a
`"Type"`-oracle denominator the figure is **12**. Argument shape alone does not
identify a codec registry; the anchor does.

**Constant resolution is load-bearing for the headline figure, not defensive.**
§1 lists "ids can be constants" as one of three properties that break a naive
matcher, alongside chaining and runtime values — a list of hazards. It is more than
that: an independent literal-only sweep of both forms returns **123** names for
`Interaction.CODEC`, not 124. The missing one is `CameraPlugin.java:44`,
`getCodecRegistry(Interaction.CODEC).register(CODEC_CAMERA_SHAKE, …)`, with
`CODEC_CAMERA_SHAKE = "CameraShake"` at line 34 — a constant id sitting in argument
position one of the three-argument form, so it needs §1's constant rule *and* §1's
"the name is not always the first argument" rule at the same site. Drop constant
resolution and `docs/interactions.md`'s 124-row table becomes a 123-row table with
no error anywhere; the same name is also §4's worst case, since `CameraShake` has
zero literals of its own anywhere in the jar.

**There is a THIRD registration form, and it is not a codec registration at all.**
`NPCPlugin.registerCoreComponentType(name, Builder::new)` — 194 call sites in 10
files, chained many-per-statement like the second form — puts a name into a builder
*factory*, and `NPCPlugin:1507-1509` chooses the factory by calling
`builder.get().category()`. So the vocabulary is partitioned by `Sensor` /
`BodyMotion` / `HeadMotion` / `Action` / `IEntityFilter` /
`ISensorEntityCollector` / `ISensorEntityPrioritiser`, and **not one of those ~176
names is visible to forms 1 and 2**, because there is no `X.CODEC` anywhere in the
statement to anchor on. Every `"Type"` on `docs/npc-roles.md` and `docs/npc-combat.md`
draws on this form.

The category is readable statically without executing anything: every implementation
is `public [final] Class<X> category()`, so the *return type* is the answer, and **188**
of the 194 sites reach it by inheritance from a `Builder*Base`. Resolution is
two hops — `BuilderSensorKill::new` → `BuilderSensorKill.java` → `extends
BuilderSensorBase` → `Class<Sensor> category()`.

The other **six** declare `category()` in their own file, and they are worth naming
because each is a point where one resolution route disagrees with another:
`BuilderBodyMotionSequence`, `BuilderHeadMotionSequence`, `BuilderBodyMotionTimer`,
`BuilderHeadMotionTimer`, `BuilderCombatTargetCollector`,
`BuilderEncounterMemberCollector`. The four Sequence/Timer builders override
locally *because* their names are multi-category; the two collectors are the two
the naming convention cannot bucket. (`5639eb1`'s message said 191 here. That is
the *convention route's* total, 194 − 3 constant-named, borrowed across from the
paragraph below it — two unrelated denominators, the same shape of error as the
`MinValueEffects` finding in numeric form. The fixture recorded 191 correctly, as
`by_name_convention.total`, and never claimed it for inheritance.)

> **A single `extends` is enough, and following `implements` too would be the
> regression.** The obvious alternative oracle — the type argument of
> `implements Builder<X>` — resolves all 194 and returns the type variable `T`
> for 189 of them, because the decompiled hierarchy puts `implements Builder<T>`
> on the generic bases. `category()`'s return type is the only static evidence.
> The sharp edge is that `Builder.java` itself declares `public Class<T>
> category();`, and a naive `_resolve_type` turns `T` into a plausible-looking
> `…npc.asset.builder.T`, which is **not** the `<category-unresolved>` bucket and
> so slips past the guard built for exactly this. Nothing reaches it today only
> because the walk follows `extends` and `Builder` is reached only through
> `implements` — an unstated traversal-order property protecting a 194-site
> resolver. The resolver therefore now requires a captured category name to
> resolve to a real source file, so the protection is deliberate rather than
> emergent and survives whoever later decides the walk "should also follow
> interfaces".

It cost a wrong answer within the hour of being missed, which is why it is written
here rather than only in the code. `docs/effects-stats.md` documented
`"Type": "Kill"` as an interaction; a forms-1-and-2 sweep reported `Kill` as
**registered nowhere**, which reads as *invented*. `Kill` is a perfectly real
registered name — a **sensor** — so the page's actual defect is §4 name collision,
not invention, and the two want different fixes. A vocabulary oracle that is
missing a whole registration form does not fail quietly in the safe direction; it
manufactures fabrication findings.

> **The partition is load-bearing, not decoration.** Fifteen of the 176 names are
> registered in more than one category: `Timer` is a legal `Type` in `BodyMotion`,
> `HeadMotion` *and* `Sensor`; `State`, `Random`, `Beacon`, `AdjustPosition` and
> `ProjectToGround` each span `Action` and `Sensor`; `Nothing` and `Sequence` span
> three. So a flat "is this name registered?" membership test passes every one of
> them in every slot, and phase (c) has to check the name against the slot's
> vocabulary rather than the union — the same lesson as §3 and §4, arriving a third
> time from a third direction.

The two id-shape rules from §1 and §2 both still apply here and both were needed:
three of the 194 sites name their type with a `static final String` constant
(`FACTORY_CLASS_TRANSIENT_PATH` = `"Path"`, twice, and `FACTORY_CLASS_ROLE` =
`"Role"`), so a `registerCoreComponentType("` grep silently sees 191. And
`NPCPlugin:1507` *declares* the method with a parameter list of the same arity as
every call site, so arity cannot exclude it and it surfaces as one bogus
unresolvable registry; exclude it structurally — a declaration is the occurrence
followed by a body.

Regression baselines from that run, which cannot validate the miner and exist only
to make drift visible: 105 registries, 948 registrations, 10 with an open verdict.
(98 / 754 before form 3 was added; all seven new registries are closed.)

Three further properties of the resolution hold on build-26 and are pinned at zero
in the fixture, because each fails by substituting a **plausible** category rather
than by admitting it cannot resolve — the one direction `<category-unresolved>`
cannot catch, since there is nothing to put in the bucket: no file in a resolution
chain declares two `Class<X> category()` methods (the match is whole-file
first-wins), no `extends` first-match names a class other than its own file's, and
none of the 194 builder simple names is ambiguous tree-wide (244 names are, so the
simple-name fallback is one collision away from mattering).

> **Where this landed in the history, which the commit subjects get wrong.** The
> form-3 miner, its fixture, its runner and this section were all committed in
> **`969b4da`**, whose subject is `docs: follow-up to 872f007 — a false closure
> claim…`; **`5639eb1`**, whose subject announces the third registration form,
> contains only the constant-resolution paragraph above. A `git add -A` run to
> inspect status left everything staged, and the next `git add <two docs files>
> && git commit` swept it all in. `git log --stat` and a bisect for "when did
> form 3 land?" both answer `969b4da`. Recorded here rather than in `refs/notes`
> because invariant 8's own argument is that a note is invisible to every gate,
> page and grep — and because `5639eb1`'s message *asserts* content it does not
> contain, which is a claim, and claims get a follow-up commit. This is the
> `commit-subject-scopes-the-audit-trail` failure repeating with a new trigger:
> not parallel agents this time, just a status check that staged the tree.

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

> **Arrears: an indirect-registrar follower is not built, deliberately.** Category
> (b) is statically resolvable, and phase (c) meets exactly one value that needs it
> — `IntervalCondition` on `docs/world-events.md`. The chain is
> `.register(conditionType.id(), …)` at `WorldEventsPlugin.java:220` and `:221`
> (two calls, because each condition registers on both `EventCondition.TYPE_CODEC`
> and `EventCondition.Config.TYPE_CODEC`) inside `registerCondition` at `:218`,
> called at `:129` with `IntervalCondition.TYPE`, which is
> `new EventCondition.Type("IntervalCondition", 0.033333335f)` at
> `IntervalCondition.java:25`. That is two call-graph hops plus a constructor
> unwrap to resolve one documented value, so phase (c) carries an audited skiplist
> entry with those file:lines instead. Build the follower when a second value needs
> it, or when §2(b)'s other registrars (`registerTask`, `registerCompletion`,
> `registerEffectType`, `registerConditionType`, `registerRuleType`) start reaching
> the docs — not before. The entry itself is the tripwire: `check-type-values.py`
> reports a skiplist line that starts resolving on its own as a finding.
>
> **The two triggers, so the decision is not re-argued from scratch:** a *second*
> §2(b) value appearing in a docs JSON fence, or the miner being opened anyway for
> a game update. `ObjectiveTask` / `ObjectiveTaskAsset` are the ones to watch —
> ten names arrive through `ObjectivePlugin.registerTask(id, …)` by the same
> indirection, so the follower earns its keep the moment objectives get a JSON
> page. Until then one audited entry costs less than the machinery.
>
> **Those ten are split across two files, which is §1's lesson arriving again.**
> Six are in `ObjectivePlugin.java:173-178` on `this` (`Craft`, `Gather`,
> `UseBlock`, `UseEntity`, `TreasureMap`, `ReachLocation`); four are in
> `NPCObjectivesPlugin.java:69-72` on an `objectivePlugin` reference
> (`KillSpawnBeacon`, `KillSpawnMarker`, `Bounty`, `KillNPC`). A follower anchored
> on the declaring file finds **6 of 10** and exits clean — the same 60%-with-a-green-run
> shape as mining only form 1 for `Interaction.CODEC`.
>
> And a collision to guard when that follower is written:
> `TaskRegistry.registerTask` (`TaskRegistry.java:21,25`) has two unrelated
> overloads taking `CompletableFuture` / `ScheduledFuture`. A corpus-wide
> `registerTask\s*\(` matches both, and neither registers anything named.

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

**The wrapper is part of the check, and it is the half nobody reads.** All of the
above is about a detector that cannot fire. The 2026-09-05 instance was a detector that
fired correctly and a *caller* that turned the result into a pass:
`check-type-values.py` exited **0** when its jar cache was missing and printed `SKIP` at
column 0, and `verify-docs.sh`'s block filtered output with `grep -E '^  (INFO|WARN)'`,
discarded the column-0 line, saw `RC=0`, and ran `pass "$(… sed -n 's/^  PASS  //p')"`
over output containing no PASS line — emitting a bare `PASS` with no message and no
denominator. Two independent mistakes had to line up, one in each layer, and **neither is
visible from the checker alone or the caller alone**. So: a skip must never share an exit
code with a pass (use a third value); the caller must guard the input independently rather
than trusting the callee's status; and any `pass "$(…)"` interpolating a captured
substring must be run once against output where that substring is absent. Note which half
had been reviewed — the checker's reasoning carried several hundred words of comment and
its twenty-two lines of shell carried none, which is the general hazard: the interesting
half attracts the documentation, the documentation attracts the review, and the plumbing
has nothing to read.

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

### Three failure shapes from the second review round

**A negative in a row must be shown, not inferred from the positive.** The
`PickupItem` row said "this is not ordinary walk-over pickup" on the strength of
having found the one thing that *does* bind it. That is the same asymmetry as the
`Self` error one round earlier, and reviewer closed it by finding the other side:
walk-over pickup is `PlayerItemEntityPickupSystem`, whose query is
`Query.and(ItemComponent, TransformComponent, not(Interactable), not(PickupItemComponent),
not(PreventPickup), not(PropComponent))` — and `applyPickupState(true)`, the only
binder of `*PickupItem`, is exactly what **adds** `Interactable`. So the two paths
are not merely distinct, they are mutually exclusive by ECS query, and
`applyPickupState(false)` adds `PreventPickup` rather than restoring walk-over
pickup. **Finding the mechanism turns a hedge into a stronger claim than the hedge
was**, which is the argument for always spending the extra grep.

Two nearby name traps on that one: `PickupItemComponent` / `PickupItemSystem` are
the cosmetic fly-to-player lerp, not pickup logic; and the hook a modder actually
wants for "run a chain when a player walks over this item" is the item asset's own
`InteractionType.Pickup` entry, which `PlayerItemEntityPickupSystem` runs in place
of giving the item.

**A field default is invisible to the codec, and a table's Default column has to
say which one it is reporting.** Two `ChangeFarmingStage` claims rested on
`targetStage`'s *field* initialiser of `-1` with no codec default — true, but it
is not the kind of finding a codec-doc-vs-reality read produces, and it must not
be filed as one (the codec's description does say "Use -1 for the final stage").
The related trap is requiredness's cousin: `Increase`/`Decrease` are nullable
boxed `Integer` while `Stage` is a primitive `int`, so the branch is selected on
null-vs-set, and `"Increase": 0` is not the same as omitting the key.

**A key can be resolved twice against different fallbacks, and a Default column
can be right about one and wrong about the other.** `ChangeFarmingStage` resolves
`StageSet` first as `StageSet ?: config.getStartingStageSet()` — used only for an
early validity check — and then as `StageSet ?: farmingBlock.getCurrentStageSet()`,
which is the one applied. The row's Default cell named the first and its
description named the second, so the row contradicted itself while both halves
were separately traceable to real code. Read every resolution of a key, not the
first one; and where two disagree, the seam between them is usually a real defect
worth its own bullet (here: a block in a later stage set fails the precheck naming
a set the interaction was never going to use).

### The `ChargeTime` near-miss: stopping at a find rather than at an answer

`IncrementCooldown`'s codec runs `chargeTime = -chargeTime` in `afterDecode`. Read
against the codec's own description — "the amount of time to increase the current
charge time by" — that looks exactly like the `SpawnYawOffset` shape: doc says one
thing, code silently does the other. It was written up that way, claiming a
positive `ChargeTime` makes the next charge arrive *sooner*. It makes it arrive
**later**, and hytale-reviewer caught it before the commit landed.

The missing step was one call further on, in `CooldownHandler.Cooldown`, and it is
a **sign convention rather than a fact**: `chargeTimer += dt` with a charge granted
at `chargeTimer >= chargeTimeMax`, so `chargeTimer` is elapsed progress counting
*up*, while `remainingCooldown -= dt` two lines below counts *down*. Two timers,
one class, opposite senses. Subtracting from progress lengthens the wait, so the
negation is the implementation reconciling a key expressed as "seconds added to the
wait" with a field that stores progress already made. The codec description is
correct, and the negation is why.

Three things worth carrying forward:

- **A find is a worse place to stop than a puzzle.** An `afterDecode` that negates
  a value announces itself as a discovery, and that is precisely what ended the
  read early. The §5 rule says parse the chain to its `.add()`; this is its
  runtime twin — parse through to what the field *means*, not to where the value
  stops moving.
- **Check the sign convention of any field a documented key feeds.** A wrong fact
  usually contradicts something; a wrong sign convention produces a fluent,
  confident, exactly-backwards paragraph.
- **Zero shipped uses removes the only other check.** `IncrementCooldown` has none,
  and `"ChargeTime"` appears in no shipped asset at all, so nothing but a second
  reader was ever going to catch this. Treat "no positive control exists" as a
  reason to slow down rather than as licence, and say so on the page: the section
  now tells the reader to check the target cooldown's charge list, because
  `increaseChargeTime` returns early both at max charges and at one charge or
  fewer — so on most cooldowns the key does nothing, silently, while the
  interaction still reports `Finished`.

Related, from the same pass: a preamble sentence claiming "four names are
registered on a second codec" was caught before the checker ran. §11 records eight
collisions. A count in prose is a closure claim; where the real set is recorded
elsewhere, point at it instead of restating its size.

### Two attribution lessons from closing the tail

**Directory is not always the discriminator.** §4's worked case, `CameraShake`, splits cleanly:
all 49 hits sit under `Server/Camera/CameraEffect/`, so a directory-scoped grep is correct there and
"scope the grep to the directory" reads like the general fix. It is not. `ExitInstance` gets four
hits, of which two are the interaction (under `Server/Item/Items/`) and two are a
`Death.RespawnController` type in `Server/GameplayConfigs/Portal.json` and `Default_Instance.json`.
The thing that separates them is the **parent key path**, not the directory; a directory-scoped grep
happens to be right today only because no `RespawnController` currently sits under `Server/Item/`.
Attribute a hit by the key path it hangs from, and treat a directory that appears to separate two
registries as a coincidence until checked.

**`server.lang` is a shipped key-set oracle, and it is free.** CLAUDE.md records that the
gotcha-string advisory greps the jar only, so `Server/Languages/*/server.lang` is checked by nothing.
It nonetheless carries, for any type with an in-game editor UI, a block of the form
`customUI.<editor>.field.<Type>.<Key>` — one entry per codec key. For `ShowEventTitleEffect` those
entries enumerate exactly the seven keys its codec declares, in all five shipped language files, and
the one shipped prefab writes all seven: two independent confirmations of a key set, from outside the
jar. Worth running against any type being documented from a codec alone, and worth remembering that a
control which agrees is still a result — this one caught nothing, which is what a passing check looks
like.

The same check corrected a claim in the other direction. The `ShowEventTitle` section originally said
the material had "no positive control"; that is true of the *interaction*, which has zero shipped
uses, and false of the *effect*, which is among the better-corroborated types on its page. A blanket
"nothing corroborates this" over a section documenting two twins understates one and overstates the
other.

### Defaults are a claim, and a wrong one can invent a symptom

Two defects reached `main` in the tail's last four commits, both caught by
hytale-reviewer, and both were **defaults** rather than behaviour.

**`ShowEventTitleInteraction`'s three `…DurationS` keys were documented as
defaulting to `0`.** They default to `4.0`, `1.5` and `1.5`. The page then built a
gotcha on the wrong figure — "a title that shows for no time and never fades" —
which is a symptom that does not exist, and would have sent a reader debugging a
fade that was working. The true defaults make the warning *stronger*: the shipped
trigger-volume effect block writes `Duration` `4.0`, `FadeInDuration` `1.5`,
`FadeOutDuration` `1.5`, which are exactly the interaction's three defaults. So
copying that block into an interaction silently drops three keys and substitutes
identical values — it works, and keeps working until someone edits a timing value
and finds it has no effect. **A wrong default is not a small error when a gotcha
is derived from it: it manufactures a false failure mode with a confident
description attached.**

**And a default is the one thing in a key table with no gate behind it.**
`check-symbols.py` binds names, the snippet gate compiles units, the fields check
confirms a documented key exists — none of them reads a *value*. That is the
structural reason both of this round's defects were defaults while every mechanism
claim in the same batch was caught: the mechanism claims had a reviewer *and* a
decompiler to argue with, and the defaults had neither. "Re-read the field
initialisers" is therefore a cheap standing check on any key table, not a lesson
about these two keys.

**`TeleportInstance`'s `InstanceKey` was documented as deciding whether the
instance is fresh.** It decides *where the identity is stored*. With a key, the
instance is a global world name shared by every block using it. Without one, an
`InstanceBlock` component is created on the triggering block, the world UUID is
written into it and the block is marked for saving — so that block returns to its
own instance every later use. Neither branch is "a fresh instance each time". The
two shipped assets are one per branch, and were sitting there the whole time: a
dungeon portal you must be able to re-enter (no key) and a test that sets
`"InstanceKey": "Persistent"`.

The generalisable part: **a codec description that explains a key's *value*
("Random if not provided") does not explain its *effect*.** The value really is
random; the inference that randomness means non-persistence was mine, and the
branch immediately below the key's read contradicted it. Read the branch the key
selects, not only the description of what goes in it.

Two smaller ones from the same review, both the good direction:

- An unfalsifiable-by-asset negative ("nothing enforces the mutual exclusion, so
  an asset setting both loads") is worth one more step: the branch says which one
  *wins*. `HubPortal` resolves `InstanceTemplate` first, so `WorldGenType` is
  silently ignored. That converts a negative nothing can contradict into a
  positive anyone can check — the same move that fixed the `PickupItem` row.
- An inference stated as mechanism should be traced to the guard that implements
  it. "Zeroing both clear-out distances re-enables teleporter bouncing" was right
  about the distances and wrong about the conclusion: `ClearUsedTeleporterSystem`
  checks a separate 100 ms global cooldown *before* the distances, so zeroing them
  reduces the guard rather than removing it.

**A postscript on the same `PositionOffset` bullet, because the correction was
corrected.** The first fix added a qualifier — "only reached when the instance is
being created" — which was itself wrong, and wrong in the direction that
*understates* exposure. `makeReturnPoint` has three call sites, not the two on the
creation paths: the third is inside `getPersonalReturnPoint`, which both teleport
branches call, including the one where the instance already exists. So with
`PersonalReturnPoint` set the unguarded dereference runs on **every** use, and
both shipped assets set it. The lesson is narrow and worth stating plainly:
**counting a method's call sites is not the same as reading the two you already
found.** A `grep -n` for the method name would have shown three in one line, and
the qualifier was written from the two that were already on screen.

**Then the evidence for the fix needed the same treatment.** The corrected bullet
first cited "both shipped assets set `PersonalReturnPoint`" — a true sentence that
does not support the claim, because one of the two sets `"OriginSource": "Block"`
and therefore takes the branch that *guards* the null. An asset only corroborates
a path it actually takes. The right citation is the single asset carrying all
three conditions at once (`Forgotten_Temple_Portal_Enter.json`: no `OriginSource`
so the `ENTITY` default, `PersonalReturnPoint` set, `PositionOffset` written as
`{0,0,0}`) — one asset that exercises the path beats two that merely mention the
key. Check which branch a cited asset takes before counting it as evidence, which
is §4's registry-attribution discipline applied one level down, to branches within
a single type.

### The two unautomated elements of a key table

The defaults defect and the citation defect have one explanation, and stating it
turns two scars into a known gap.

**Every gate in this corpus checks a *claim*, and neither of these is one.**
`check-symbols.py` binds a name to a class. The snippet gate compiles a unit. The
fields check confirms a documented key exists. The asset-path advisory resolves a
path. None of them reads a **value**, so a default written as `0` when the field
initialises to `4.0` passes forever. And none of them reads a **warrant** — that
the asset a sentence cites actually exercises the path the sentence is about — so
"both shipped assets set `PersonalReturnPoint`" passes forever too, being a true
statement wrongly attached.

Defaults and citations are therefore the two elements of a documented key table
with no automation behind them at all, which is why both of this batch's surviving
defects were one or the other while every mechanism claim in the same batch was
caught. Two cheap manual checks cover the corpus's actual blind spot, and unlike
the three queued gates neither waits on a parser:

1. **Re-read the field initialisers** before writing a Default column. The value
   is in the class body, a few lines below the codec chain that was just parsed.
2. **Check that a cited asset takes the path** the sentence describes, not merely
   that it mentions the key. An asset only corroborates a branch it actually
   enters.

**And the first of those is nearly free once queued gate 1 exists.** That gate has
to parse codec chains to count keys; field initialisers sit in the same class body
it will already be reading, adjacent to the keys they belong to. A defaults check
is close to a by-product of the parse rather than new work — probably the cheapest
thing to bolt onto that gate, and it closes half of this pair. The citation half
has no obvious automation and stays a reading discipline.

### A correction that was filed where nothing reads it

`79075d7`'s commit message claimed the `TriggerSpawnMarkers` findings were "all
read from the implementation rather than from the codec's own key descriptions".
That is false for `Count`: the codec documents it as "Max number of spawn markers
to activate. Set to 0 to activate all spawn markers", so implementation and codec
doc agree, and it is **not** a codec-doc-vs-reality find of the `SpawnYawOffset`
kind. The gotcha still earns its place — a JSON author never sees that string —
but it must not be cited as evidence that a codec description was wrong.

The reason this paragraph exists rather than the correction simply being made: it
was originally attached to that commit with `git notes`. That put it in
`refs/notes/commits` — a ref no clone fetches by default, no gate reads, no page
renders, and no grep of the working tree finds. The fact was correct and it was
invisible. It reached the repo only when the choice was questioned.

CLAUDE.md invariant 8 now carries the rule: a review finding is fixed by a
follow-up commit, never by touching the reviewed commit. The generalisation worth
keeping is narrower than "don't rewrite history" — **a fact worth correcting is
worth committing**, because the working tree is the only surface anything in this
project actually reads.

## 12. Phase (c) is unscoped, and the obvious scoping was measured before it was rejected

`check-type-values.py` (queued gate 1, phase c, landed 2026-09-04) checks that a
documented `"Type"` value is a registered name **somewhere**. It does not check
that the name is legal in the **slot** it appears in. That is a real gap — §4 lists
eight names registered on two different codecs, and §1's fourth correction adds 15
core-component names registered in more than one category — so the gate catches
*invention* and is blind to *misattribution*.

**Do not read the numbers below as an argument that scoping is nearly done.** They
are here because the next person to look at this will reach for the same binding,
find an encouraging figure, and ship it.

Scoping needs a map from the enclosing JSON key to the codec that decodes its
value. The obvious construction is to mine `new KeyedCodec("<Key>", <X>.CODEC)`
corpus-wide and keep the keys that bind to exactly one type-discriminated codec.
Measured on build-26: **165** JSON keys bind to at least one, and **156** bind to
exactly one. That 156 looks like a gate.

It is not. "Exactly one" is an artefact of the match window, not a fact about the
corpus, and one counterexample is enough to see why:

| Key | Binds "uniquely" to | Whose whole vocabulary is | But the docs use it for |
|---|---|---|---|
| `Interactions` | `ChoiceInteraction.CODEC` | `GiveItem`, `StartObjective` | `RootInteraction` — `ChangeStat`, `ApplyEffect`, `ClearEntityEffect`, … |

A gate built on that binding would hard-fail `docs/effects-stats.md`, which is
correct. And the slots that most need scoping — `Sensor`, `BodyMotion`,
`Instructions`, `MotionControllerList` — bind to **nothing at all**, because §1's
third registration form has no `KeyedCodec` anywhere near it.

**The safe subset cannot be carved out either, and this is the load-bearing
point.** The instrument that would identify "the keys that bind unambiguously" is
the same corpus-wide name match that called `Interactions` unambiguous. So the
subset's safety is unverified *by construction*, not merely unverified yet — the
selection and the error share a cause. Note also which way each version fails: the
unscoped gate produces false negatives, which are stated openly in the checker, in
`CLAUDE.md` and here; a scoped gate on a bad binding produces false *positives* on
correct pages, which under invariant 1 either blocks runs or breeds skiplist
entries justified by the checker's own binding — invariant 7's trap, arriving
through the door the gate was built to avoid.

What a sound binding would need: parse the **enclosing codec's chain** and read the
codec argument the key actually declares, rather than matching key names across the
corpus. That is §3's lesson — match within the documenting scope, never globally —
arriving from a third direction, after §3 itself and after §4's name collisions.
The whole-chain parser that phase (a) built is the prerequisite, so this is
buildable; it is arrears, not a dead end.

One thing to state whenever this gate's green line is quoted: `CLAUDE.md` cites a
fabricated `"Type": "Wall"` as the defect that motivated the whole oracle, and
**this gate would have passed it**. `Wall` is registered on `PatternAsset.CODEC`
*and* appears as a `"Type"` **seven times across two shipped assets**
(`HytaleGenerator/Assignments/Plains1/Plains1_Oak_Vines.json` ×4,
`HytaleGenerator/Biomes/Experimental/Zone4.json` ×3), so it passes for two
independent reasons and would survive the loss of either oracle. The fabrication
there was misattribution.

> Two files, seven occurrences — worth writing both, because the review that
> produced this paragraph rendered it as "7 shipped assets" and so did the first
> draft here. Whichever figure you quote, say which of the two it counts.

### The tab hazard, measured corpus-wide

The separator in those two files is a **tab**, and that is not a local oddity. Any
hand-written scan of the asset tree for `"Type"` values must use a whitespace
class, not a literal space. Measured on build-26, `"Type"\s*:\s*"…"` against
`"Type" *: *"…"`:

| | `\s*` | space-only | lost |
|---|---|---|---|
| distinct values | 566 | 454 | **112** |
| occurrences | 53,919 | 41,400 | 12,519 |

> **Start with the near-miss, because it is the whole lesson in one line.** While
> checking how far this hazard reached, I wrote a pattern anchored on
> `"Type"\t`. It matched **zero files**, and zero reads as *the hazard is
> narrower than we thought*. It matches zero because the tab is after the
> **colon** — `"Type":\t"…"` — and `before` is empty in all 12,519 occurrences,
> so there is no `"Type" :\t` variant for it to find either. A check written to
> verify a claim about *patterns that silently match nothing* silently matched
> nothing, and came one keystroke from being filed as evidence of absence.

**There are four separator dialects, and each has a known extent.** Measured by
capturing the whitespace either side of the colon in every `"Type"` in the asset
tree — a complete partition, since the four sum to the 53,919 that `\s*` matches:

| Between key and `:` | Between `:` and value | occurrences | files | where |
|---|---|---|---|---|
| — | one space | 41,215 | 16,484 | everywhere (the mainstream) |
| — | **tab** | 12,519 | 222 | `HytaleGenerator/` — Assignments 118, Biomes 75, Density 18, WorldStructures 14 |
| — | — | 143 | 69 | mostly `World/Default/` |
| **space** | one space | 42 | 14 | `HytaleGenerator/WorldStructures/` only |

A fourth dialect neither measuring pass mentioned is `"Type":"…"` with no
whitespace at all, in 69 files. Both comparison patterns below admit it — mine
because `*` allows zero, the review's because `?` does — which is luck rather
than design, and the specific luck is worth naming: **both were written to be
lenient about *a* space, and leniency about a space silently implies leniency
about *zero* spaces.** Neither of us decided that; `?` and `*` decided it. An
entry that depends on undecided leniency breaks the day someone tightens a regex
for an unrelated reason.

So a pattern's figure is a function of **which dialects it admits**, and the
dialects are per-file rather than per-line: **16,634 files use exactly one and
only 75 mix** (99.55% pure). That is what makes a space-only scan fail in one
clean block instead of degrading gently — it drops dialect 2 entire, and dialect
2 is the world generator.

> **"Directory-scoped" invites an assumption that one directory breaks.** The
> mixing is directory-scoped too: of the 75 mixed files, 58 are `World/Default/`
> (dialects 1+3), 14 `WorldStructures/`, 2 `EncounterManager/Examples/`, 1
> `NPC/Roles/`. So a reader who concludes "this directory is uniform, I can scan
> it with a literal" is right almost everywhere and wrong in `World/Default`.

The comparison figure therefore moves with how you write the pattern, and that
is the point rather than an untidiness. Two passes measuring "the same thing"
produced:

| Comparison pattern | distinct | matched | lost | files disagreeing with `\s*` |
|---|---|---|---|---|
| `"Type": ?"` | 452 | 41,358 | 12,561 | 231 |
| `"Type" *: *"` | 454 | 41,400 | 12,519 | 222 |

Both derive cleanly and neither is wrong; they are different questions wearing
the same label. The nine-file gap is **derivable, not merely explicable**, and it
is this rule stated in the smallest possible case. Dialect 4 never occurs pure —
all 14 of its files are mixed, all under `WorldStructures/`:

| files | dialects present | first pattern | second pattern | gap? |
|---|---|---|---|---|
| 9 | 1 + 4 | misses 4 | catches 4 | **yes** |
| 5 | 1 + 2 + 4 | misses 2 | misses 2 | no |

The 9/5 split is therefore not a property of the files' contents so much as of
which dialect each pattern happens to admit.

**So: quote the regex beside any figure a regex produced, and say what the count
counts.** The `\s*` reference figure — 566 — is the only one of the three that is
a property of the corpus rather than of the question asked about it.

**The 222 files where the two disagree are entirely under
`Server/HytaleGenerator/`** — Assignments, Biomes, Density, WorldStructures.
Nothing outside that subtree is tab-separated. So the failure mode is much
sharper than "some values get missed": a space-only scan loses **the whole
world-generator vocabulary and nothing else** — `Abs`, `Clamp`, `Constant`,
`CellNoise2D`, `Amplitude`, `ColumnRandom`, `AlwaysTrueCondition` and ~105 more.
A re-derivation written that way comes back clean everywhere except the generator
pages, where it manufactures a hundred fabrication findings at once, every one of
them a real value. That is an *easier* trap than a subtle one, because the check
looks like it is working.

**This is prospective, not load-bearing.** Of the 20 documented values that
resolve only via the asset oracle, **zero** are in the tab-only set, and zero
documented values would be wrongly flagged by a space-only asset scan. Today's
green run does not depend on the whitespace class. The hazard is aimed entirely
at whoever next writes an asset scan by hand — including at a reviewer
re-deriving this gate's own figures, which is how it was found.

## 13. The inherited-scope guard, audited from both sides (2026-09-05)

`section_binder.bind_all` binds a docs section to the codec class it documents, and
reports four classes: **direct** (a `**Package:**` line, an FQCN, or a path-style
heading), **inherited-accepted**, **inherited-rejected**, **unbound**. A subsection
inherits its ancestor's binding only if every top-level key it names — key-table
first column, JSON-fence root keys — exists on that class's chain with parents
walked. One unknown key rejects it and the rejection records the key.

Build-26: **139 direct, 52 inherited-accepted, 86 inherited-rejected, 2859
unbound, 3136 seen** (the four sum exactly).

### The input sets step 5 and scoped (c) are built against

Measured after the guard, and these are the denominators, not the section counts.
A table or fence is *usable* by a check if its section is direct-bound or
inherited-accepted:

| | total | direct | inherited-accepted | usable |
|---|---|---|---|---|
| key tables **with** a Default column | 60 | 5 | 8 | 21% |
| key tables without one | 253 | 20 | 7 | 10% |
| json fences containing a `"Type"` | 412 | 32 | 38 | 16% |

(Measured at 52 accepted; the fractions move a little with the parent-walk fixes
below and should be re-printed before either check ships.) Position-only
inheritance would have offered 68% and 50% — the guard refuses most of that, which
is the guard working. **The honest figure for the defaults check is ~13 of 60, not
41 of 60**, and it is the figure to quote when that check reports coverage.

### The rejections are correct refusals — but only after three fixes

The first audit pass read the rejections by failing key, on the hypothesis that
base-interaction keys were failing because the parent walk could not reach them.
That was right, and it took three fixes:

1. **The parent's field name is part of the address.** `chain.parent` is
   `Interaction.ABSTRACT_CODEC`, not `Interaction.CODEC`, and `Interaction.CODEC`
   is an `AssetCodecMapCodec` with no keys at all.
2. **Simple names collide.** Two files are named `SimpleInteraction.java`
   (`protocol` and `interaction.config`), so a unique-filename lookup refused and
   the walk stopped at hop 0 — 15 rejections blamed `Next`, a key
   `SimpleInteraction` declares. Resolve sibling-directory first, then up the
   package tree, and only then accept a unique tree-wide match.
3. **`BuilderCodec.abstractBuilder` puts the parent in argument ONE**, where
   `BuilderCodec.builder` puts it in argument two. A phase-(a) parser defect, not a
   binder one: 96 chains use `abstractBuilder` against 1516 plain builders, which
   looks negligible and is the opposite, because every one of the 96 is a **base
   class** — precisely the links other chains inherit through.

`Next` 15 → 13 → gone; accepted 40 → 44 → **52**.

What remains is genuine. The residual rejections are led by `Interactions` (15),
`default` (6), `ItemAnimationId` (5), and every one checked was absent from the
ancestor's full ancestry. The shape is consistent and worth knowing: they sit in
`§Examples` / `§Structure` / `§Usage Patterns` subsections whose fences show a
**composed** shape whose root is a different type. `interactions-flow.md`'s
`§Examples` under `StatsConditionInteraction` opens `{"Type": "Serial",
"Interactions": [...]}` — a `Serial`, not a `StatsCondition`. The guard refused a
real misattribution.

### The accepted sample: 20 of 20 correct, and the exemption costs nothing today

Sampled 20 of the 52 accepted (seeded, `random.seed(11)`) and read each against its
ancestor's declared keys. **20 of 20 correctly attributed**; no misattribution in
the sample. Fingerprint sizes: min 1 key, median 4, max 18.

**The discriminator exemption is used, and only in its safe form.** 38 of the 52
acceptances depended on an exempted key, and **all 49 exempted occurrences were
`Type`**. The mined set is `Type` (38 declarations), `component`, `Id` and `type` —
and `Id` is the one that worried us, because it is a common key name and a global
exemption for it would silently accept a sibling's table. It is used **zero** times.
So the per-codec refinement is not needed yet; the figure to re-check if it ever is:
`exempted` on each `Inherited` record names which keys carried the acceptance, so
the cost of the fallback is measurable rather than assumed.

> **The audit instrument was wrong first.** The initial pass reconstructed each
> section's fingerprint by keying bodies on `(page, title)` — and
> `interactions-flow.md` has five different `#### Core Properties` subsections, so
> they collapsed and five distinct ancestors all showed the *last* one's keys. The
> binder itself was correct; only the audit was not. Fixed by recording the
> fingerprint on the `Inherited` record at bind time rather than reconstructing it,
> which is the same rule as reading a gate's own denominator instead of recounting
> its inputs.

