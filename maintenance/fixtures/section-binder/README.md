# `section-binder/` — fixture for `section_binder.py`

    python3 maintenance/scripts/check-section-binder-fixture.py [-v]

Also run by `verify-docs.sh` on every invocation, because a fixture nothing runs was
the sixth instance of this gate family's recurring failure.

## Written before the binder, on purpose

Seven times over 2026-09-04/05 one sentence appeared in this gate family — *a clean
result reported over nothing* — and every instance was in the guard added most
recently. Three of those times the new guard carried the exact defect it was written
to prevent. The structural cause is ordering: a guard added in response to review is
last relative to its own verification.

So every case in the runner was written and **watched fail** before `section_binder.py`
existed, floors first. That ordering paid twice within the hour:

- **The binder would have crashed on the real corpus.** `parse_chain` returns `None`
  for a class with no codec chain, which is 280 of the sections that otherwise
  resolve — components, systems, events. The first one would have taken the binder
  down. Found by a mutation, not by reading.
- **The harness scored that crash as "no reds".** It read only `^  FAIL` lines, so an
  `AttributeError` looked like a mutation nothing detected — the crashing-mutant
  lesson from `check-type-values-fixture.py`, recurring in the harness written after
  it. And the first repair was worse than the bug: making the two calls that had
  crashed lazy left the rest eager, so a `next(...)` still raised `StopIteration`
  before `check()` was entered and the mutation still scored zero. `check()` now
  takes a callable and nothing else.

## The corpus

Six sections over two pages, one per outcome, small enough to read whole:

| section | outcome |
|---|---|
| `Widget`, `Gadget` | **bound** — heading names a class, Package line resolves it, class declares a chain (2 keys and 1, so a wrong chain is visible) |
| `Sprocket` | no source file for the class |
| `Doohickey` | package does not resolve (`config` — ~74 real sections look like this) |
| `Thingummy` | no `**Package:**` line |
| `Sprinkler Component` | class declares no codec chain — **and** a multi-word heading, since with every other heading a single word, `cls = title` passed identically and the first-token extraction was untested |
| `Learning Widgets` | an **FQCN** Package line (`binderpkg.Gadget`) with a hostile heading whose first CamelCase token is `Learning` — 28 real sections are written this way |
| `Phantom` | an FQCN naming a class that does not exist |
| `Widget` (on `unbound.md`) | a package **directory holding no `.java`** — must read "package does not resolve", not "no source file", or the two reasons trade members |

Each unbound reason is counted **separately**. A single `unbound` total is an
aggregate over causes, and a figure summed over sources cannot show one source
reaching zero — three prior instances in this gate family.

## Mutation-tested

Ten defects reintroduced one at a time, each reddening at least one case: both
floors, the FQCN path disabled, the FQCN path binding without resolving, the
package-directory `.java` requirement dropped, the two resolve reasons collapsed,
the chain never parsed, the heading used whole, chainless classes bound anyway, and
`PACKAGE_GAP_LINES` narrowed.

**Run mutations with `PYTHONDONTWRITEBYTECODE=1`, and verify the restore.** A sweep
here reported the binder restored while `section_binder` still behaved as the last
mutant: `cp` put back a source file whose mtime was OLDER than the `.pyc` compiled
from the mutant, so Python reused the cached bytecode. The file on disk read
`PACKAGE_GAP_LINES = 4` and the imported module reported `1`. Every mutation result
in that sweep was sound — each mutant wrote a newer file — but the **restore** was
not, and a restore that silently does not restore turns the next measurement into a
measurement of the previous mutant. Check the restore after each mutation, not just
at the end.
