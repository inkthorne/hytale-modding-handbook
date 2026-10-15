# Registry-oracle fixtures

Golden inputs for `maintenance/scripts/codec_parser.py`, the codec-chain parser
that queued gate 1 (CLAUDE.md) is built on. Run them with:

    python3 maintenance/scripts/check-codec-fixture.py [-v]

**Why a fixture exists before the gate does.** A checker that has never
reproduced a known-good answer set cannot be trusted to fail a doc, and this
repo has already paid for that lesson twice — the 0.6.3 pass produced three
wrong answers from reading a detector's output instead of auditing its input
(CLAUDE.md invariant 7). The parser here was wrong on its very first run, in the
quietest possible way: its field-name regex was `[A-Z][A-Z0-9_]*CODEC`, which
requires a prefix and therefore can never match a field named plainly `CODEC`.
It matched nothing on all 44 types. A gate shipped in that state would have
reported a clean run forever.

## `tail-44.json`

The 44 interaction types of `registry-oracle-notes.md` §11 — key counts, key
names and, per type, two sets: `null_validated` (the field carries a
`NonNullValidator` instance; the only thing that makes an omitted key fail) and
`strict_null` (a `true` third `KeyedCodec` argument; it does not). The old single
`required` list was their union. Both sets were re-derived by hand from the 0.7.2
source and every key cites the line it was read on; `required_from_key_table` is
what the docs claimed, not a measurement. The measurement that separates the two
is `maintenance/probes/requiredness/run.sh`. §11 is the best fixture material in the repo because
its figures were derived independently **twice**, by two sessions with separately
written parsers, and reconciled. Extracting them here also machine-checks that
§11's own two tables agree with each other, which had never been verified.

## `known-traps.json`

Cases CLAUDE.md invariant 7 and §11 name as the documented ways to be
confidently wrong, plus the requiredness pass's (subclass validators, `.addField()`
bleed, RecordCodec). Each defeated some plausible parser. `--mutations` reintroduces
each guard's defect and requires the named cases to go red:

| Case | What it defeats |
|---|---|
| `CustomConnectedBlockTemplateAsset.Shapes` | raw `KeyedCodec` (a `KeyedCodec<T>` pattern skips it) **and** `strict_null` by a `true` third argument (stopping at the first balanced paren keeps the key, loses the flag). It is **not** required: the live probe decodes a shipped asset with `Shapes` deleted |
| `ConnectedBlockPatternRule.Shapes` | the symmetric inverse — same key name, also raw, but the `true` is inside the inner constructor, so attributing it outward **manufactures** a `strict_null` that is not there. The key that really is `strict_null` in that class is `IncludeOrExclude` |
| `PluginManifest` | `null_validated` via `Validators.nonNull()` attached after `append(...)` closes. Parse to the first balanced paren and this reports *no null-validated keys at all* |
| `RunOnBlockTypesInteraction`, `ModelAsset.AnimationSet` | `Validators.nonEmptyArray()` is a `NonNullValidator` subclass; the literal-text match missed 21 keys |
| `ModelAsset.Animation` | `.addField()` keys have no `.add()`, so a bracket-aware tail scan ran into the next append's validators |
| `MessageAction` and three inline cases | `RecordCodec` puts the validator inside the append group, and a synthetic source covers shapes with no real instance (a key with only `nonEmptyMap()` does not exist at 0.7.2) |
| `objectiveshop.StartObjectiveInteraction` | same simple name as a registered type, same key **count**, different key name and requiredness — so a count cross-check agrees while both facts are wrong |

Add a case here whenever a parse turns out to have been confidently wrong. Per
CLAUDE.md invariant 8, correct a fixture in a commit that says which parse was
wrong and why — never silently edit it to match the parser.

## `registries.json`

Fixture for `maintenance/scripts/registry_miner.py` (phase b). Run it with:

    python3 maintenance/scripts/check-registry-fixture.py [-v]

**The file separates two kinds of figure, and only one can validate the miner.**
`independent` figures were derived by hand in `registry-oracle-notes.md` §1–§2
*before* this miner existed, so reproducing them is evidence — 44 checks, covering
`Interaction.CODEC`'s 124 names across both registration forms, all ten cells of
the field table, and the three verdicts including §2's false-positive guard.
`measured` figures came from the miner itself and are regression baselines only:
checking a miner against its own output proves nothing, which is invariant 7's
circularity in another costume.

The miner reproduced every independent figure on the run that created this
fixture, and in doing so found three amendments to §1 — recorded there, not here.

**The `core_component_types` block is independent by a different route**, and that
is the point. §1's third registration form (`registerCoreComponentType`) had no
hand-derived figures in the notes to reproduce, so instead of writing down what the
miner said and calling it a fixture, the counts come from a *second method*:
bucketing each site by its builder's `Builder<Category>*` name rather than by
resolving `category()`. The two disagree by exactly 3 — the sites whose id is a
`static final String` constant, which a naive `registerCoreComponentType("` grep
cannot see — and the fixture records the reconciliation arithmetic rather than the
agreed total, so a resolver bug would have to reproduce the naming convention's own
blind spots to stay hidden. `unresolved_categories` is pinned at **0**: a name the
resolver cannot place is not a harmless gap, because phase (c) checks a documented
`"Type"` against its *slot*, and 15 of the 176 names are legal in more than one.

### Unqualified registrations (2026-10-15)

A review of the 0.7.2 pass found that the miner and the recount both required a
`Receiver.` before the codec field, so `CODEC.register("Box", ...)` inside the class that
declares `CODEC` was invisible to both: 69 sites in 20 classes at 0.7.2 (68 at 0.6.8),
18 registries absent from the miner and `Condition.CODEC` short by 15 names. The miner now
binds such a site the way Java does, walking outward from the call: a local, parameter or lambda
parameter of that name excludes it; a class declaring a static field of that name binds it; a class
declaring an instance field of it excludes it; a class that declares neither but extends or
implements something, or an anonymous body, leaves the site UNRESOLVED (it may inherit the name; no
superclass rule finds out); a `this.`/`super.` receiver is excluded. The recount implements the scope
walk separately. Fixture changes:

- `independent.unqualified` (0.7.2) and `independent.unqualified_previous_build` (0.6.8) are the
  **recount's** figures, never the miner's. The pre-existing `independent` figures are
  unchanged and are checked against **qualified** sites only.
- `synthetic` + `synthetic/src/`: a hand-written tree with one instance of every binding rule
  (see the comments in `alpha/Outer.java` and, for the cases where Java binds a bare name differently from "innermost declaring class" — inherited, anonymous, instance field, lambda parameter, enclosing-block local — `beta/Host.java`). Both scripts run on it; the expected figures were read
  off the source, not produced by either script.
- The runner also compares miner and recount **live** on each tree (`AGREEMENT` line), pins
  `UNRESOLVED` at 0, and counts what neither spelling covers (`residue`).
- `check-registry-fixture.py --mutations` removes each guard in a patched copy of the scripts and
  requires named checks to go red (26 mutations, ~45 s).

The two scripts share the decision table and six patterns (field character class, class
keyword, not-a-type keywords, typed-local regex, cast-literal regex, lambda-parameter regex),
so their agreement does not vouch for those; the hand-read synthetic expectations do. They
implement the scope walk separately, which is what the agreement does vouch for.
