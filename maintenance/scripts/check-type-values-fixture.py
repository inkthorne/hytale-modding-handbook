#!/usr/bin/env python3
"""
Run check-type-values.py against a miniature corpus with known answers.

Phase (c) shipped without a fixture while phases (a) and (b) shipped with one, and
all three defects the review then found map onto a case nobody had constructed: a
missing-cache run, a value resolved by different sources on different pages, and a
stale-entry-only run. See maintenance/fixtures/type-values/README.md.

Every case invokes the checker as a SUBPROCESS rather than importing it, because
two of the three defects were in what it printed and what it exited with — neither
of which an import exercises. Exit status is read from the call itself, never
through a pipe or wrapper: this repo has twice reported a wrapper's status as the
script's.

Usage: python3 maintenance/scripts/check-type-values-fixture.py [-v]
"""
from __future__ import annotations
import argparse, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parents[0] / 'fixtures' / 'type-values'
CORPUS, SKIPLIST = FIX / 'corpus', FIX / 'skiplist.txt'
CHECKER = HERE / 'check-type-values.py'

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
A = ap.parse_args()

fails: list[str] = []
checks = 0


def run(docs, src, assets, skiplist):
    """Invoke the checker; return (rc, stdout). rc comes from the call itself."""
    p = subprocess.run(
        [sys.executable, str(CHECKER), '--docs', str(docs), '--src', str(src),
         '--assets', str(assets), '--skiplist', str(skiplist)],
        capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def case(label, rc, out, *, want_rc, must=(), must_not=()):
    global checks
    checks += 1
    problems = []
    if rc != want_rc:
        problems.append(f'exit {rc}, wanted {want_rc}')
    for m in must:
        if m not in out:
            problems.append(f'missing {m!r}')
    for m in must_not:
        if m in out:
            problems.append(f'unexpected {m!r}')
    if problems:
        fails.append(f'{label}: ' + '; '.join(problems))
        if A.verbose:
            print(f'  FAIL {label}\n' + '\n'.join('      ' + l for l in out.splitlines()))
    elif A.verbose:
        print(f'  ok   {label}')


with tempfile.TemporaryDirectory() as td:
    tmp = pathlib.Path(td)
    docs, src, assets = tmp / 'docs', tmp / 'src', tmp / 'assets'
    for name, dst in (('docs', docs), ('src', src), ('assets', assets)):
        shutil.copytree(CORPUS / name, dst)

    # 1. The healthy corpus. Five distinct values, one per resolution source plus
    #    the tab case, nothing unresolved.
    rc, out = run(docs, src, assets, SKIPLIST)
    case('healthy corpus passes', rc, out, want_rc=0,
         must=('PASS', 'unresolved 0'), must_not=('FAIL', 'WARN'))

    # 2/3. A missing oracle must NOT be an exit 0. This is the defect that printed
    #      a bare PASS in verify-docs.sh: the shell filtered the SKIP line away and
    #      trusted the status, so the status had to carry the meaning too.
    rc, out = run(docs, tmp / 'no-such-src', assets, SKIPLIST)
    case('missing source cache exits 2', rc, out, want_rc=2,
         must=('SKIP',), must_not=('PASS',))
    rc, out = run(docs, src, tmp / 'no-such-assets', SKIPLIST)
    case('missing asset cache exits 2', rc, out, want_rc=2,
         must=('SKIP',), must_not=('PASS',))

    # 4. The mixed-source tally. Epsilon is page-local on aaa.md and skiplisted on
    #    bbb.md. The old tally re-derived with all(... for page in pages) and
    #    printed `unresolved 1` beside PASS on exactly this shape.
    rc, out = run(docs, src, assets, SKIPLIST)
    case('a value resolved by different sources per page is not unresolved',
         rc, out, want_rc=0, must=("page's own java fence 1", 'unresolved 0'))
    case('the live exemption count is reported, not just the bucket',
         rc, out, want_rc=0, must=('live',))

    # 5. The tab-separated asset value. A space-only asset scan drops 112 distinct
    #    values in the real tree, all under Server/HytaleGenerator/ (notes §12).
    case('a tab-separated asset "Type" resolves', rc, out, want_rc=0,
         must_not=('"Delta"',))

    # 6. The indented fence in bbb.md. An `^```' anchor skipped this shape.
    case('a fence indented inside a list item is scanned', rc, out, want_rc=0,
         must=('json fence(s)',), must_not=('"Beta"',))

    # 7. A fabricated value must fail and must be named.
    (docs / 'ccc.md').write_text('# C\n\n```json\n{ "Type": "Zzz_NotReal" }\n```\n')
    rc, out = run(docs, src, assets, SKIPLIST)
    case('a fabricated value fails and is named', rc, out, want_rc=1,
         must=('FAIL', 'Zzz_NotReal', 'ccc.md', 'unresolved 1'), must_not=('PASS',))
    (docs / 'ccc.md').unlink()

    # 8. A stale entry with NO fabrication. This rendered as a FAIL whose header
    #    named fabricated values and whose body was empty, because the detail grep
    #    matched only FAIL lines while the cause was a WARN.
    stale = tmp / 'stale.txt'
    stale.write_text(SKIPLIST.read_text() +
                     '\nAlpha  aaa.md  bogus: Alpha resolves via the registry\n')
    rc, out = run(docs, src, assets, stale)
    case('a stale entry alone fails, as a WARN naming the entry', rc, out, want_rc=1,
         must=('WARN', 'stale skiplist entry', "'Alpha'"), must_not=('PASS',))

    # 9. A canary that has become resolvable must fail LOUDLY, because the probe is
    #    the only thing standing between "clean corpus" and "oracle accepts
    #    everything". Furniture is one keystroke from real: it is already live in
    #    the asset tree as an "Id" and a "Tag".
    (assets / 'Server' / 'Thing' / 'canary.json').write_text('{ "Type": "Furniture" }\n')
    rc, out = run(docs, src, assets, SKIPLIST)
    case('a canary that became real fails the run', rc, out, want_rc=1,
         must=('known-positive probe', 'Furniture'), must_not=('PASS',))

print(f'\nFIXTURE {checks} case(s): {checks - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
sys.exit(1 if fails else 0)
