# Page-size gate fixtures

Required outcomes for `verify-docs.sh`'s **[HARD] Page-size arrears list is
current** gate. There are no fixture *files* here: the gate's only input besides
`docs/` is `maintenance/page-size-arrears.txt`, so each case is a mutation of
that one file, run against the real corpus.

**Why this file exists.** A gate that has never been observed red is not a gate;
it is an instrument assumed to work. This repo was bitten by that nine times in
one session — detectors that returned a plausible number while structurally
unable to fire. So the gate was run once per outcome *before* it was trusted, and
the required results are recorded here so the next person can redo it in four
commands rather than re-deriving what "working" looks like.

## The four cases

Mutate `maintenance/page-size-arrears.txt`, run
`./maintenance/scripts/verify-docs.sh --no-build`, read the
`[HARD] Page-size arrears list is current` section, then restore the file.

| # | Mutation | Required outcome |
|---|----------|------------------|
| 1 | none (as committed) | **PASS**, listing every entry with its live line count, and both denominators |
| 2 | delete the `world.md` line | **WARN** — `over the line and UNLISTED: world.md` |
| 3 | append `01-index.md` (a page under the threshold) | **WARN** — `listed but now UNDER: 01-index.md` |
| 4 | remove every entry, leaving only comments | **FAIL** — parsed 0 entries |

Case 4 is the one that matters most, and the reason it is a FAIL rather than a
WARN: a parser that finds nothing reports zero unlisted pages *forever*, and it
reports it in exactly the words a healthy run uses. Under invariant 1 a WARN is
same-day actionable, but nobody actions a check that says everything is fine.
An empty list is a broken check, not a clean corpus.

Case 3 exists because the reverse direction is real: `npc-roles.md` dropped
under the threshold when it was split on 2026-09-04 and had to be removed from
the list by hand. Nothing would have noticed if it hadn't been.

## Reading the pass line

    PASS  arrears list current (69 page(s) measured, 6 entr(y/ies) parsed, threshold 1500)

Two denominators, per invariant 6. **Pages measured** proves the corpus was
walked; **entries parsed** proves the list was read. Either at an unexpected
value means the gate is measuring something other than what you think, and the
`listed:` lines above it print each entry's live size, so the pass line is a
status report rather than a bare verdict.

Sizes live nowhere but in this output. `maintenance/page-size-arrears.txt`
deliberately records no line counts — a recorded size is what went stale twice
on 2026-09-04, in the prose this gate replaced.

## A caveat on measuring the gate itself

The harness used for the first run reported `exit=0` for all four cases, which
is wrong: it captured the exit status of the `sed` that stripped ANSI colour,
not of `verify-docs.sh`. The outcomes above were read from the log *contents*
instead, which is what the table asserts. If you re-run these, assert on the
gate's own PASS/WARN/FAIL line — do not trust an exit code taken through a pipe.
