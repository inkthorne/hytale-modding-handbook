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

**The codec field is not always called `CODEC`.** `CaveTypeGenerator`, `Context`, `EventAction`
and `Shape` register on `TYPE_CODEC`; `BrushOperation` uses `OPERATION_CODEC` and
`OpenCustomUIInteraction` uses `PAGE_CODEC`. A pattern anchored on the literal `.CODEC`
misses these silently — it is how the `CaveTypeGenerator` row below was nearly discarded as
spurious while checking this list.

Eleven registries are reachable *only* through the second form and are therefore invisible to
a first-form-only sweep entirely, not merely undercounted — each verified to have zero
first-form registrations: `CameraEffect`, `CaveTypeGenerator`, `ChoiceElement`,
`CombatTextUIComponentAnimationEvent`, `EntityUIComponent`, `FarmingStageData`,
`GrowthModifierAsset`, `PhysicsConfig`, `RemovalCondition`, `SpreadGrowthBehaviour`, and
`SelectInteraction.EntityMatcher` (`InteractionModule.java:328-329`). Two more registries gain members only
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

## 6. Validate anchors with the gate's own slugger

`verify-docs.sh`'s slug function strips `[^\w\- ]`, so **underscores survive**, and it
numbers repeated headings `-1`, `-2`. A separately written slugger that strips underscores
reports `items-blocks.md#block_secondary-interaction` as broken when it resolves fine.
Re-use the function in `verify-docs.sh` rather than reimplementing it.
