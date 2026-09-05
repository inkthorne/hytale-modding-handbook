# `defaults/` — fixture for `defaults_probe.py` and `check-defaults.py`

    python3 maintenance/scripts/check-defaults-fixture.py [-v]
    python3 maintenance/scripts/check-defaults-fixture.py --mutations

Both run by `verify-docs.sh` on every invocation.

## Written before the probe, on purpose

Every case in the runner was red when the runner was committed, and each went green
only as `defaults_probe.py` was built to satisfy it. That ordering is the rule this
gate family earned across seven instances of one sentence — *a clean result reported
over nothing* — each of which lived in the guard added most recently.

It paid immediately. The first real run of the gate reported **eight disagreements
and every one was the checker's**, in two clusters that the fixture now pins:

- **A box is not its primitive.** `private Boolean jumping;` defaults to `null`;
  read as `boolean` it defaults to `false`, and `interactions-flow.md` gets accused
  of five wrong defaults it does not have. One entry in a set literal.
- **A JSON-quoted cell carries quotes.** The docs write `` `"Absolute"` `` because
  the value appears in JSON. Comparing the quotes against `ValueType.Absolute`
  manufactures three more.

Both are exactly the shape the prototype had already produced once: it reported
**14** disagreements, and all 14 were its own normaliser — an enum-tail rule that
took `1.3` apart into `3`, and a literal-detector that read the marker word
`Required` as a value. Nothing in the docs was wrong on any of the three runs.

## The corpus

`corpus/src/defpkg` is three classes and `corpus/docs/defaults.md` is one page. Every
row of the page's first table names the case it is:

| shape | why it is here |
|---|---|
| literal initialiser, float suffix, enum constant | the ordinary agreements |
| primitive with **no** initialiser | Java's zero — `0`, `false` |
| **boxed** `Boolean`/`Integer` with no initialiser | `null`, not the primitive's zero |
| a key on the **parent** chain (`Base.ABSTRACT_CODEC`) | the parent's *field name* is part of the address |
| a key on this chain whose **field** is on the parent | the walk searches every hop for the field, not only the hop that named the key |
| setter assigning **two** fields | refused, with a reason — not guessed |
| setter that is a **method reference** | refused, with a reason |
| setter that **calls** rather than assigns | refused, with a reason |
| a key on **no** chain | absent from the probe, not a silent `None` |
| `—` and `*italic prose*` | state no literal; counted separately, never compared |

`#### Wrong Defaults` is the **positive control**: every row disagrees on purpose, so
the gate's red path is exercised rather than believed in. `### Plain` names a class
with no codec chain and `### Loose` has no `**Package:**` line, so both are *counted
and not checked* — which is what makes the printed coverage a ratio that can differ
from its own denominator.

`corpus/docs-nodefaults/` is a second, separate corpus, and the separation is the
point: an **empty** directory trips the *binder's* floor and never reaches the gate,
so testing the gate's zero-floor with an empty directory tests the binder's instead.
This one binds, has sections, and states no defaults anywhere.

## Mutation-tested

Eleven defects reintroduced one at a time, each asserted against the **exact** set of
cases it must redden — not "at least one", because a mutation reddening more cases
than expected means a case asserts something other than what its label says. Fixing
those expectations after the first sweep changed four of the sets, every time
because a probe defect also moved the *gate's* findings, which is a coupling worth
knowing about.

The harness refuses a **stale** mutation rather than reporting it caught: the text
to patch must occur exactly once in the target file, and it earned that within the
hour — indenting the checker's `SKIP` lines moved one anchor and the sweep said so
instead of silently measuring nothing.

`IDENTITY` comes first and changes nothing: an unchanged copy must pass all 50
cases. Without it, a harness that reddens everything for an unrelated reason — a
`ModuleNotFoundError` in its own temp directory, which is what happened the first
time a sibling gate ran one — reads as total coverage.

The harness copies the whole scripts directory per mutation and runs with
`PYTHONDONTWRITEBYTECODE=1`. A sweep on a sibling fixture once reported the source
restored while the module still behaved as the last mutant: the restored file's
mtime was older than the `.pyc` compiled from the mutant, so the file on disk read
`PACKAGE_GAP_LINES = 4` while the import reported `1`.
