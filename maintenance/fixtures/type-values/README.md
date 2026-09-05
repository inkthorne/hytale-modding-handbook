# `type-values/` — fixture for `check-type-values.py`

Run it with:

    python3 maintenance/scripts/check-type-values-fixture.py [-v]

**Why this exists, and why it exists late.** Phase (a) shipped with a fixture and
phase (b) shipped with a fixture; phase (c) shipped with **none**, and all three
defects the review then found line up exactly with a corpus nobody had built:

| defect in the shipped gate | the case that was never run |
|---|---|
| exit 0 on a missing cache, rendered as a bare `PASS` | a **missing-cache** run |
| the by-source tally could print `unresolved 1` beside `PASS` | a value resolved by **different sources on different pages** |
| a stale entry rendered as a mislabelled `FAIL` with an empty body | a **stale-entry-only** run |

That explains all three without any claim about which layer they lived in — the
appealing story was "the Python was right and the bash was wrong", and it is false
on two of the three. The real stopping point is that the independent-derivation
discipline was applied to the *mined figures* (the parser and the miner both have
fixtures) and to nothing downstream of them.

**The canaries in the checker are not this.** They probe whether the oracle *union*
still rejects a value registered nowhere. They say nothing about resolution
precedence, exit codes, or rendering — which is where all three defects were.

## The corpus

`corpus/` is a miniature of the real inputs, small enough to read whole:

- `src/fixturepkg/Foo.java` registers `Alpha` and `Beta` on `Foo.CODEC`. The
  package is `fixturepkg`, not `com.example`, for a reason worth keeping: this
  repo's `.gitignore` carries `com/` to exclude decompiled classes, and it
  silently swallowed the file when the fixture first mirrored the real package
  layout. `git add` reported success and staged eight files instead of nine. A
  fixture corpus that imitates the thing it tests inherits the ignore rules
  written for the thing it tests.
- `assets/Server/Thing/gamma.json` uses a space separator; `delta.json` uses a
  **tab**. The tab is deliberate: `Server/HytaleGenerator/` is tab-separated in the
  real tree, a space-only pattern silently loses 112 distinct values there, and this
  file makes that regression fail here instead of in production (notes §12).
- `docs/aaa.md` carries registry, asset, tab-asset and page-local values, the last
  registered in the page's own ```java fence.
- `docs/bbb.md` repeats `Epsilon` on a page that does **not** register it, where
  `skiplist.txt` waives it — so one value is resolved by two different page-scoped
  sources, which is the tally case. It also puts a fence **indented inside a list
  item**, because an `^```' anchor silently skipped exactly that shape in the real
  corpus (and skipped the java fence that justified it, so the two errors cancelled
  and the run looked clean).

## What the runner asserts

Nine cases, each an end-to-end invocation, not an import: healthy run; missing
source cache; missing asset cache; a fabricated value; a stale skiplist entry with
no fabrications; the mixed-source tally; the tab-separated asset value; the indented
fence; and a canary that has become resolvable. Exit codes are captured in the same
statement as the command — a status taken through a pipe or a wrapper reports the
wrapper, which this repo has been bitten by twice.
