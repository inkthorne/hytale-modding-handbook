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

Eleven cases, each an end-to-end invocation rather than an import: the healthy run
(both INFO lines **verbatim**), the three missing-input runs (source cache, asset
cache, skiplist — all exit 2), a fabricated value, a stale entry with no
fabrication, the mixed-source tally, the live exemption count, the tab-separated
asset value, and a canary that has become resolvable. Exit codes are captured in
the same statement as the command — a status taken through a pipe or a wrapper
reports the wrapper, which this repo has been bitten by twice.

**Assert counts, not the absence of a name.** The first version of this fixture
asserted things like `'"Beta"' not in output`, and that is satisfied *by the
regression it guards*: a fence that stops being scanned takes its value out of the
corpus rather than making it fail. Absence assertions detect a value that fails to
**resolve** and never one that silently stops being **scanned** — which is the
entire class the fence anchor belongs to. The two INFO lines are pinned exactly
instead; they move the moment anything leaves the corpus.

## `--mutations`

    python3 maintenance/scripts/check-type-values-fixture.py --mutations

Reintroduces each known defect into a copy of the checker and asserts **the exact
set of cases that goes red**, plus that the case the defect *belongs to* is among
them. It exists because of a specific failure, and the failure is the fixture
making the mistake the fixture is for.

**A case propped up by an unrelated corpus feature.** With the pre-fix fence anchor
restored, five cases went red — which looked like coverage. All five failed on
`exit 1`, and that exit came from the Epsilon waiver going stale because *its*
fence happened to be indented, not from anything the fence case asserted. De-indent
that one fence and the broken checker passed 10 of 10, the named case included.
That is the original `My_Type` bug — an anchor that skipped a value *and* the java
fence justifying it, so the two errors cancelled and the run looked clean —
reappearing one level up, inside the fixture written to prevent it. The corpus now
puts `Beta` and `Theta` in indented fences so the scan denominator and two buckets
move on their own, and the case has been re-verified with the prop removed.

**The IDENTITY control comes first and must stay.** A copy of the checker with
nothing changed must pass every case. Without it the first `--mutations` run
reported all five defects "caught" by nearly every case — it was measuring a
`ModuleNotFoundError`, because a mutant in a temp directory cannot import
`registry_miner`. A red for the wrong reason is worth no more than a green for the
wrong reason, and it is more dangerous, because "the fixture catches everything" is
the result you were hoping for.

**Red sets are wider than the named case, deliberately.** The corpus is built so a
regression produces a *finding*, and a finding turns every `want_rc=0` case red at
once. Pinning the exact set rather than requiring it to be non-empty is what stops
that cascade hiding a case that has gone quiet.
