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

**Read the gate's own PASS/WARN/FAIL line. If you need an exit code, capture it
in the same statement as the script — never from a wrapper, a pipe, or a job
runner.** This is not a footnote about one bad harness. It has now caught two
independent instruments within an hour: the first harness took `$?` through the
`sed` that stripped ANSI colour, and a reviewer's background job reported
"completed (exit code 0)" for the case-4 run whose script exited 1, because the
notification reports the last command in the chain. Both returned a plausible
number while structurally unable to observe the thing they named. Case 4 is
where this bites hardest, since it is the only case whose required outcome is a
non-zero exit.

| # | Mutation | Required outcome |
|---|----------|------------------|
| 1 | none (as committed) | **PASS**, listing every entry with its live line count, and both denominators |
| 2 | delete the `world.md` line | **WARN** — `over the line and UNLISTED: world.md` |
| 3 | append `01-index.md` (a page under the threshold) | **WARN** — `listed but now UNDER: 01-index.md` |
| 4 | remove every entry, leaving only comments | **FAIL** — `parsed 0 entries`, **and** `1 hard check(s) failed.` in the summary, **and** exit status 1 |
| 5 | set `THRESHOLD = 1700` in the gate | **WARN** — `listed but now UNDER: prefabs.md (1534 lines)`, and **both** printed figures read `threshold 1700` |

Case 4 is the one that matters most, and the reason it is a FAIL rather than a
WARN: a parser that finds nothing reports zero unlisted pages *forever*, and it
reports it in exactly the words a healthy run uses. Under invariant 1 a WARN is
same-day actionable, but nobody actions a check that says everything is fine.
An empty list is a broken check, not a clean corpus.

Case 3 exists because the reverse direction is real: `npc-roles.md` dropped
under the threshold when it was split on 2026-09-04 and had to be removed from
the list by hand. Nothing would have noticed if it hadn't been.

Case 5 guards a defect that shipped in the gate's first commit: `PS_THRESHOLD`
was never assigned, so the PASS line printed a `:-1500` fallback while the WARN
line hardcoded `1500` — neither bound to the Python's `THRESHOLD`. Both figures
would have kept saying 1500 while the gate behaved differently. That is the same
rot the commit had just removed from invariant 6's illustration, reintroduced in
the gate the commit added: a printed number that does not track what it names.
So the case asserts the figure and the behaviour move *together*, which is the
only assertion that catches it.

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

## Independent reproduction

All four outcomes were reproduced by hytale-reviewer on a scratchpad copy of
`docs/` and `maintenance/`, extracting the gate's Python verbatim from
`verify-docs.sh` rather than reimplementing it, and running the real script
end-to-end for the two cases where shell wiring matters. Case 1 gave a real exit
of 0, case 4 a real exit of 1.

Three partial-corruption mutations were tested too, and none goes silent:

| Mutation | Outcome |
|---|---|
| entry commented out (`#inventory.md`) | WARN — `UNLISTED inventory.md` |
| entry mistyped (`inventoy.md`) | WARN ×2 — `UNLISTED inventory.md` *and* `MISSING inventoy.md` |
| entry indented (`  inventory.md  `) | PASS, parsed 6 — tolerated, not dropped |

That is why the gate asserts **no expected minimum** on `entries parsed`. The
list is checked against measurement in both directions, so a dropped entry
reappears as UNLISTED and a corrupted one names both halves of the error; the
parsed figure is a backstop, not the primary detection. An expected minimum
would instead fail every time a split lands and the list correctly shrinks — and
a number people routinely edit to quiet a gate is worse than no number at all.
