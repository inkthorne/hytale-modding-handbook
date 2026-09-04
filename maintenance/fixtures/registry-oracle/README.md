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
names and required-sets. §11 is the best fixture material in the repo because
its figures were derived independently **twice**, by two sessions with separately
written parsers, and reconciled. Extracting them here also machine-checks that
§11's own two tables agree with each other, which had never been verified.

## `known-traps.json`

Four cases CLAUDE.md invariant 7 and §11 name as the documented ways to be
confidently wrong. Each defeated some plausible parser:

| Case | What it defeats |
|---|---|
| `CustomConnectedBlockTemplateAsset.Shapes` | raw `KeyedCodec` (a `KeyedCodec<T>` pattern skips it) **and** required by a `true` third argument (stopping at the first balanced paren keeps the key, loses the requirement) |
| `ConnectedBlockPatternRule.Shapes` | the symmetric inverse — same key name, also raw, but the `true` is inside the inner constructor, so attributing it outward **manufactures** a requirement. Invariant 7 calls this the dangerous direction: a fabricated *required* can never be contradicted by a shipped asset |
| `PluginManifest` | requiredness via `Validators.nonNull()` attached after `append(...)` closes. Parse to the first balanced paren and this reports *no required keys at all* |
| `objectiveshop.StartObjectiveInteraction` | same simple name as a registered type, same key **count**, different key name and requiredness — so a count cross-check agrees while both facts are wrong |

Add a case here whenever a parse turns out to have been confidently wrong. Per
CLAUDE.md invariant 8, correct a fixture in a commit that says which parse was
wrong and why — never silently edit it to match the parser.
