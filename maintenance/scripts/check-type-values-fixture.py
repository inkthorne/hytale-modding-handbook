#!/usr/bin/env python3
"""
Run check-type-values.py against a miniature corpus with known answers, and
(with --mutations) verify that each case detects the defect it is named for.

Phase (c) shipped without a fixture while phases (a) and (b) shipped with one, and
all three defects the review then found map onto a case nobody had constructed: a
missing-cache run, a value resolved by different sources on different pages, and a
stale-entry-only run. See maintenance/fixtures/type-values/README.md.

TWO THINGS THIS FILE LEARNED THE HARD WAY, both about how a green run gets faked.

1. ASSERT THE COUNTS, NOT THE ABSENCE OF A NAME. The first version of case
   "indented fence" asserted `'json fence(s)' in out` (a format-string substring,
   present even when zero fences are scanned) and `'"Beta"' not in out` — which the
   regression SATISFIES, because a fence that stops being scanned takes its value
   out of the corpus rather than making it fail. Every absence assertion detects a
   value that fails to RESOLVE and none detects a value that silently stops being
   SCANNED, which is the entire class the fence anchor belongs to. The exact INFO
   lines are asserted instead: they pin the fence denominator and all five buckets
   at once, and they move the moment anything leaves the corpus.

2. A CASE CAN BE PROPPED UP BY AN UNRELATED CORPUS FEATURE. With the pre-fix anchor
   restored, five cases went red — but all five on `exit 1`, coming from the Epsilon
   waiver going stale because ITS fence was indented, not from anything the
   fence case asserted. De-indent that one fence and the broken checker passes 10 of
   10, the named case included. That is the original `My_Type` bug (an anchor that
   skipped a value AND the fence justifying it, so the errors cancelled) reappearing
   one level up, inside the fixture written to prevent it. `--mutations` exists
   because of this: it asserts the EXACT SET of cases each mutation reddens, so a
   case that stops detecting its own defect is a failure rather than a silence.

Every case invokes the checker as a SUBPROCESS rather than importing it, because
two of the three original defects were in what it printed and what it exited with —
neither of which an import exercises. Exit status is read from the call itself,
never through a pipe or wrapper: this repo has twice reported a wrapper's status as
the script's.

Usage:
  python3 maintenance/scripts/check-type-values-fixture.py [-v]
  python3 maintenance/scripts/check-type-values-fixture.py --mutations [-v]
"""
from __future__ import annotations
import argparse, os, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parents[0] / 'fixtures' / 'type-values'
CORPUS, SKIPLIST = FIX / 'corpus', FIX / 'skiplist.txt'
CHECKER = HERE / 'check-type-values.py'

# The healthy corpus, stated exactly. Six values, one per resolution path plus the
# two trap cases. Asserting these two lines verbatim is what makes a value leaving
# the corpus a failure rather than a quieter pass.
SCAN = '6 json fence(s) of 7 in 2 page(s); 7 "Type" occurrence(s), 6 distinct value(s)'
TALLY = ("registry 2, shipped assets 2, page's own java fence 1, "
         "audited skiplist 1, unresolved 0 (distinct values by first source; "
         "2 live (value, page) exemption(s) in total)")

# label -> (old, new) applied to a COPY of the checker, and the exact set of case
# labels that must go red. "and no others" is the point: a mutation whose red set
# is a superset is being caught by something other than the case that names it.
# label -> (old, new, expected red set, the case this defect BELONGS to).
#
# `expect` IS A MEASUREMENT, `names` IS THE SPECIFICATION, and the difference
# decides what to do when one of these goes red. Three of the five `expect` sets
# were wrong when first written from prediction; the recorded sets came from
# running the mutations. So an exact-set failure is a CHANGE DETECTOR — it says a
# red set moved, never that the new one is wrong — while `names` says what OUGHT to
# redden. The failure mode is specific: add a twelfth case, watch six exact-set
# assertions go red, re-measure and paste, and the whole check silently becomes a
# tautology. `names` survives that repair; `expect` does not. Re-measure `expect`
# freely; never re-measure `names`.
#
# Two assertions per mutation. `names` is the case the defect is the reason for,
# and it must go red — that is the reviewer's finding that started this: a case can
# be named for a regression it does not actually detect, propped up by an unrelated
# corpus feature. The exact-set check is the second: red sets here are WIDER than
# the named case because the corpus is built so a regression produces a FINDING,
# and a finding turns every `want_rc=0` case red at once. That cascade is exactly
# what could hide a case going quiet, which is why the set is pinned rather than
# merely required to be non-empty.
# FLOORS. Same shape as the checker's own, and this file is where the chain ends:
# the fixture guards the checker and nothing guards the fixture. `MUTATIONS = {}`
# printed "0 defect(s) reintroduced, expected red set asserted exactly" and exited
# 0 — a claim about zero things, phrased as verification, which is the fourth
# appearance of one sentence in this gate. `all_cases` returning nothing printed
# "0 case(s): 0 passed, 0 failed" and exited 0, one layer above that.
#
# The realistic path to either is not deletion in one go. It is `expect`-staleness:
# someone adds cases, several exact-set assertions redden at once, and the cheapest
# repair under pressure is to drop the offending mutations rather than re-measure
# each. Every individual deletion looks locally reasonable and nothing stops the
# slide at zero.
#
# These are FLOORS, not targets. Raise them freely when cases or mutations are
# added; lowering one needs a reason in the commit message, exactly like the
# page-size arrears list.
MIN_CASES = 13
MIN_MUTATIONS = 7

MUTATIONS = {
    # THE CONTROL, and it must come first. A copy of the checker with NOTHING
    # changed must still pass every case. Without it the harness reported all five
    # defects as caught by nearly every case, when what it had actually measured
    # was a ModuleNotFoundError in the temp directory — a red for the wrong reason
    # is as worthless as a green for the wrong reason, and here it was worse,
    # because "the fixture catches everything" is what I wanted to see.
    'IDENTITY (no change — the harness control)': (
        '#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity mutation)',
        set(), set()),

    # All THREE missing-input guards share this `return 2`, docs included since the
    # subject is now guarded beside the oracles — so all three belong in `names`,
    # not just the two that were there when only the oracles were checked.
    'SKIP returns 0 instead of 2': (
        '            return 2', '            return 0',
        {'missing source cache exits 2', 'missing asset cache exits 2',
         'missing docs corpus exits 2'},
        {'missing source cache exits 2', 'missing asset cache exits 2',
         'missing docs corpus exits 2'}),

    'fence anchor loses indent tolerance': (
        "FENCE = re.compile(r'^([ \\t]*)```(\\w*)[^\\n]*\\n(.*?)^[ \\t]*```', re.M | re.S)",
        "FENCE = re.compile(r'^()```(\\w*)[^\\n]*\\n(.*?)^```', re.M | re.S)",
        {'a fence indented inside a list item is scanned', 'a tab-separated asset "Type" resolves', 'a value resolved by different sources per page is not unresolved', 'healthy corpus: scan denominator and tally are exact', 'the live exemption count is the number, not the label'}, {'a fence indented inside a list item is scanned'}),

    'TYPE regex narrowed to space-only': (
        '''TYPE = re.compile(r'"Type"\\s*:\\s*"([^"]*)"')''',
        '''TYPE = re.compile(r'"Type" *: *"([^"]*)"')''',
        {'a fabricated value fails and is named', 'a fence indented inside a list item is scanned', 'a tab-separated asset "Type" resolves', 'a value resolved by different sources per page is not unresolved', 'healthy corpus: scan denominator and tally are exact', 'the live exemption count is the number, not the label'}, {'a tab-separated asset "Type" resolves'}),

    # The zero-floor is a guard, so it gets a mutation like every other guard —
    # otherwise the newest defence is the one nothing verifies, which is how the
    # gate acquired three instances of this shape in the first place.
    'zero-floor removed (a clean run over an empty corpus)': (
        """        print( "        A clean run over an empty corpus is the sentence invariant 6 "
               "exists to make impossible.")
        return 1""",
        """        print( "        A clean run over an empty corpus is the sentence invariant 6 "
               "exists to make impossible.")""",
        {'an EMPTY docs corpus fails rather than passing'},
        {'an EMPTY docs corpus fails rather than passing'}),

    'stale entries no longer set rc': (
        '''              f"or the page no longer uses it. Remove the line.")\n        rc = 1''',
        '''              f"or the page no longer uses it. Remove the line.")''',
        {'a stale entry alone fails, as a WARN naming the entry'}, {'a stale entry alone fails, as a WARN naming the entry'}),

    'tally re-derived by a second pass (the original defect 2)': (
        """    by_source = collections.Counter()
    for value, used in sources.items():
        if 'unresolved' in used:
            by_source['unresolved'] += 1
        else:
            by_source[next(k for k in PRECEDENCE if k in used)] += 1""",
        """    by_source = collections.Counter()
    for value, pages in values.items():
        if value in registered: by_source['registry'] += 1
        elif value in asset_types: by_source['assets'] += 1
        elif all(value in page_local.get(pg, ()) for pg in pages): by_source['page-local'] += 1
        elif all(pg in skip.get(value, {}) for pg in pages): by_source['skiplist'] += 1
        else: by_source['unresolved'] += 1""",
        {'a canary that became real fails the run', 'a fabricated value fails and is named', 'a fence indented inside a list item is scanned', 'a stale entry alone fails, as a WARN naming the entry', 'a tab-separated asset "Type" resolves', 'a value resolved by different sources per page is not unresolved',
         'healthy corpus: scan denominator and tally are exact', 'the live exemption count is the number, not the label'}, {'a value resolved by different sources per page is not unresolved'}),
}


def run(checker, docs, src, assets, skiplist):
    # PYTHONPATH matters only for mutants, which live in a temp dir: the checker
    # does sys.path.insert(0, __file__'s parent), so a copy elsewhere cannot find
    # registry_miner and dies with ModuleNotFoundError before parsing anything.
    # The first --mutations run reported all five defects "caught" by nearly every
    # case; it was measuring an import failure. See IDENTITY below for the control
    # that turns that into a failure instead of a result.
    env = dict(os.environ, PYTHONPATH=str(HERE) + os.pathsep + os.environ.get('PYTHONPATH', ''))
    p = subprocess.run(
        [sys.executable, str(checker), '--docs', str(docs), '--src', str(src),
         '--assets', str(assets), '--skiplist', str(skiplist)],
        capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def all_cases(checker) -> tuple[dict[str, list[str]], list[str]]:
    """Run every case. Returns ({label: [problems]}, [cases that produced a traceback]).

    The traceback list exists because `NameError -> exit 1` is indistinguishable
    from `defect caught -> exit 1` if you read only the status. That is the empty
    PASS in a third costume: a status that means two things cannot separate them.
    A mutant that CRASHED is not a mutant that was CAUGHT.
    """
    out: dict[str, list[str]] = {}
    crashed: list[str] = []

    def case(label, rc, text, *, want_rc, must=(), must_not=()):
        problems = []
        if rc != want_rc:
            problems.append(f'exit {rc}, wanted {want_rc}')
        problems += [f'missing {m!r}' for m in must if m not in text]
        problems += [f'unexpected {m!r}' for m in must_not if m in text]
        if 'Traceback (most recent call last)' in text:
            crashed.append(label)
        out[label] = problems

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        docs, src, assets = tmp / 'docs', tmp / 'src', tmp / 'assets'
        for name, dst in (('docs', docs), ('src', src), ('assets', assets)):
            shutil.copytree(CORPUS / name, dst)

        rc, t = run(checker, docs, src, assets, SKIPLIST)
        # The load-bearing case. Both INFO lines exact: the scan denominator catches
        # anything that stops being SCANNED, the tally catches anything that changes
        # WHICH ORACLE resolves it. Together they subsume every absence assertion the
        # first version of this file used, and unlike those they cannot be satisfied
        # by the regression they guard.
        case('healthy corpus: scan denominator and tally are exact', rc, t,
             want_rc=0, must=(SCAN, TALLY, 'PASS'), must_not=('FAIL', 'WARN'))
        case('a value resolved by different sources per page is not unresolved',
             rc, t, want_rc=0, must=("page's own java fence 1", 'unresolved 0'))
        # The live count, not the label: this line exists BECAUSE the bucket
        # under-reports, so asserting the word 'live' would pass on '0 live'.
        case('the live exemption count is the number, not the label', rc, t,
             want_rc=0, must=('2 live (value, page) exemption(s)',))
        # Delta is tab-separated in the assets. Asserted positively via the tally
        # (shipped assets 2); the old `'"Delta"' not in out` was satisfied by the
        # regression, since a dropped value stops being reported at all.
        case('a tab-separated asset "Type" resolves', rc, t, want_rc=0,
             must=('shipped assets 2',))
        # Beta and Theta live in fences indented inside list items.
        case('a fence indented inside a list item is scanned', rc, t, want_rc=0,
             must=(SCAN, 'registry 2', 'audited skiplist 1'))

        rc, t = run(checker, docs, tmp / 'no-src', assets, SKIPLIST)
        case('missing source cache exits 2', rc, t, want_rc=2,
             must=('SKIP',), must_not=('PASS',))
        rc, t = run(checker, docs, src, tmp / 'no-assets', SKIPLIST)
        case('missing asset cache exits 2', rc, t, want_rc=2,
             must=('SKIP',), must_not=('PASS',))
        rc, t = run(checker, docs, src, assets, tmp / 'no-skiplist.txt')
        case('missing skiplist exits 2, not a traceback', rc, t, want_rc=2,
             must=('SKIP',), must_not=('PASS', 'Traceback'))

        # THE SUBJECT, not an oracle. The three cases above are "a missing-cache
        # run"; these two are its mirror image, "a missing-corpus run", and the
        # asymmetry is why they were absent: a missing oracle makes everything
        # FAIL, which is loud, and a missing corpus makes everything PASS, which
        # is silent. Both produced `0 json fence(s) of 0 in 0 page(s)` + PASS + 0.
        rc, t = run(checker, tmp / 'no-docs', src, assets, SKIPLIST)
        case('missing docs corpus exits 2', rc, t, want_rc=2,
             must=('SKIP',), must_not=('PASS',))
        (tmp / 'empty-docs').mkdir()
        rc, t = run(checker, tmp / 'empty-docs', src, assets, SKIPLIST)
        # `must_not=('INFO',)` is the load-bearing half and it took a mutation to
        # find. An empty corpus ALSO makes every skiplist entry stale, which sets
        # rc=1 on its own — so with the zero-floor's `return 1` removed this case
        # still saw exit 1 and still matched 'scanned nothing' (the print survives
        # the mutation), and passed. That is the same prop failure as the fence
        # case, in the case written to fix the fence case. The early return is what
        # the guard actually does, and its observable signature is that NOTHING
        # follows: no INFO lines, no tally, no stale warnings.
        case('an EMPTY docs corpus fails rather than passing', rc, t, want_rc=1,
             must=('scanned nothing', '0 page(s)'), must_not=('PASS', 'INFO'))

        (docs / 'zzz.md').write_text('# Z\n\n```json\n{ "Type": "Zzz_NotReal" }\n```\n')
        rc, t = run(checker, docs, src, assets, SKIPLIST)
        case('a fabricated value fails and is named', rc, t, want_rc=1,
             must=('FAIL', 'Zzz_NotReal', 'zzz.md', 'unresolved 1'), must_not=('PASS',))
        (docs / 'zzz.md').unlink()

        stale = tmp / 'stale.txt'
        stale.write_text(SKIPLIST.read_text() +
                         '\nAlpha  aaa.md  bogus: Alpha resolves via the registry\n')
        rc, t = run(checker, docs, src, assets, stale)
        case('a stale entry alone fails, as a WARN naming the entry', rc, t,
             want_rc=1, must=('WARN', 'stale skiplist entry', "'Alpha'"),
             must_not=('PASS',))

        # Make a canary real and check the probe fires. Use the SYNTHETIC canary,
        # not `Furniture`: Furniture is one keystroke from real — already live in
        # the asset tree as an "Id" and a "Tag" — and the day it becomes a "Type"
        # the checker's CANARIES must change, this case breaks, and the cheapest
        # repair is to paste in whatever the checker now lists. That is
        # `expect`-vs-`names` wearing the canary's clothes. `__NotARegisteredType__`
        # is drift-proof by construction, so the fixture's correctness stops
        # depending on a name chosen to be fragile on purpose.
        (assets / 'Server' / 'Thing' / 'canary.json').write_text(
            '{ "Type": "__NotARegisteredType__" }\n')
        rc, t = run(checker, docs, src, assets, SKIPLIST)
        case('a canary that became real fails the run', rc, t, want_rc=1,
             must=('known-positive probe', '__NotARegisteredType__'), must_not=('PASS',))
    return out, crashed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mutations', action='store_true',
                    help='reintroduce each known defect and assert the EXACT set of '
                         'cases that goes red')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    res, crashed = all_cases(CHECKER)
    if crashed:
        print(f'  FAIL  the checker crashed on {len(crashed)} case(s): '
              + ', '.join(crashed))
        return 1
    if len(res) < MIN_CASES:
        print(f'  FAIL  {len(res)} case(s) ran, floor is {MIN_CASES}. A fixture that '
              f'examines nothing reports the same thing as one that passes.')
        return 1
    fails = {k: v for k, v in res.items() if v}
    for label in res:
        if a.verbose and not res[label]:
            print(f'  ok   {label}')
    print(f'\nFIXTURE {len(res)} case(s): {len(res) - len(fails)} passed, {len(fails)} failed')
    for k, v in fails.items():
        print(f'  FAIL {k}: ' + '; '.join(v))
    rc = 1 if fails else 0
    if not a.mutations:
        return rc

    if len(MUTATIONS) < MIN_MUTATIONS:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s) defined, floor is '
              f'{MIN_MUTATIONS}. "expected red set asserted exactly" over an empty '
              f'table is a claim about nothing.')
        return 1
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control in MUTATIONS. Without it a broken harness '
              'reports every defect as caught.')
        return 1
    print(f'\nMUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
    with tempfile.TemporaryDirectory() as td:
        for label, (old, new, expect, names) in MUTATIONS.items():
            src = CHECKER.read_text()
            if old not in src:
                print(f'  FAIL {label}: anchor no longer present in the checker — the '
                      f'mutation is stale and tests nothing')
                rc = 1
                continue
            mutant = pathlib.Path(td) / 'mutant.py'
            # A mutation is a CLAIM about what changed, and it needs verifying like
            # any other. Three times this session one did something else: `or True`
            # was cruder than the defect and tripped the wrong case; an empty-corpus
            # case passed off an unrelated tripwire; and a slice anchored on
            # `MUTATIONS = {` matched the comment EXPLAINING the floor, edited that
            # instead, and the run died on NameError at exit 1 — indistinguishable
            # from the floor firing.
            #
            # The check is that the anchor is UNIQUE. A size check cannot do this:
            # `replace(old, new, 1)` edits the first match only, so the delta is
            # exactly len(new)-len(old) however many places matched, and the
            # assertion that shipped first here was incapable of firing. Ambiguity
            # is the failure — `replace` silently picks the first, and the first is
            # whichever the file happens to mention earlier.
            n = src.count(old)
            if n != 1:
                print(f'  FAIL {label}: the anchor occurs {n} time(s) in the '
                      f'checker, not once. `replace` would edit the first, which is '
                      f'whichever comes earlier in the file — say where you mean.')
                rc = 1
                continue
            mutant.write_text(src.replace(old, new, 1))
            mres, mcrashed = all_cases(mutant)
            if mcrashed:
                # A broken mutant, not a detected defect. Without this the run
                # reports reds that mean nothing — which is how an anchor that ate
                # its own guard read as the guard firing.
                rc = 1
                print(f'  FAIL {label}: the MUTANT CRASHED on {len(mcrashed)} case(s) '
                      f'— it is broken, not caught. Fix the mutation, not the case.')
                continue
            red = {k for k, v in mres.items() if v}
            if label.startswith('IDENTITY') and red:
                # Abort, do not continue. Every later `ok` would be measured in a
                # known-broken environment, and a page of `ok` lines under one FAIL
                # invites exactly the reading one wants ("the fixture catches
                # everything") — which is how the ModuleNotFoundError run read.
                print(f'  FAIL {label}: the control reddened {len(red)} case(s); '
                      f'the harness itself is broken, so no mutation below would '
                      f'mean anything. Aborting.')
                for x in sorted(red):
                    print(f'         {x}')
                return 1
            missing_own = names - red
            if missing_own:
                rc = 1
                print(f'  FAIL {label}: the case this defect belongs to stayed GREEN')
                for x in sorted(missing_own):
                    print(f'         {x}')
                continue
            if red == expect:
                print(f'  ok   {label} -> {len(red)} case(s) red, exactly as expected')
                if a.verbose:
                    for r in sorted(red):
                        print(f'         {r}')
            else:
                rc = 1
                print(f'  FAIL {label}:')
                for x in sorted(expect - red):
                    print(f'         expected red, stayed green: {x}')
                for x in sorted(red - expect):
                    print(f'         unexpectedly red: {x}')
    return rc


if __name__ == '__main__':
    sys.exit(main())
