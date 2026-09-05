#!/usr/bin/env python3
"""
Fixture for check-links.py — the sixth runner, and the newest guard in the repo.

WHY IT EXISTS. The link gate was widened after it missed two links a docs/ split
broke. The widening was verified by hand — three must-flag cases and three
must-pass ones, run once. That is real evidence about the code as written and no
evidence about the code next week, and this gate has already been wrong once in a
way that took an outside reader to find. `[HARD] The gates' own fixtures pass`
already runs five of these; nothing covered links.

WHAT IT PROTECTS ABOVE ALL. The corpus narrowing back to `docs/*.md`. That is the
exact regression the widening exists to prevent, and a total-link floor cannot
see it: 1883 of the repo's 1984 links are under docs/, so re-narrowing the glob
sails over any plausible total floor and reports green having re-acquired the
bug. The `outside docs/` population is floored on its own, and the mutation below
asserts that the floor fires.

Usage: python3 maintenance/scripts/check-links-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, os, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = HERE.parents[0] / 'fixtures' / 'links' / 'corpus'

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--from-dir', default=str(HERE))
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()
FROM = pathlib.Path(A.from_dir)

fails: list[str] = []
checks = 0
MIN_CASES = 12
MIN_MUTATIONS = 5


def run(root, *extra):
    p = subprocess.run([sys.executable, str(FROM / 'check-links.py'),
                        '--root', str(root), '--min-links', '3', *extra],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def check(label, thunk, want):
    """`thunk` is ALWAYS a callable: an eagerly-evaluated argument that raises
    never reaches this function, and a harness reading only FAIL lines scores the
    crash as "no reds" — measured twice in this repo's gate family."""
    global checks
    checks += 1
    if not callable(thunk):
        fails.append(f'{label}: check() takes a callable')
        return
    try:
        got = thunk()
    except Exception as e:                      # noqa: BLE001
        fails.append(f'{label}: raised {type(e).__name__}: {e}')
        return
    if got != want:
        fails.append(f'{label}: {got!r} != {want!r}')
    elif A.verbose:
        print(f'  ok   {label}')


def broken(root_extra_files, *extra):
    """Copy the corpus, add files, run, return (rc, sorted FAIL bodies)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(CORPUS, tmp / 'c')
    for rel, body in root_extra_files.items():
        f = tmp / 'c' / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
    rc, out = run(tmp / 'c', *extra)
    bad = sorted(l.strip()[6:].strip() for l in out.split('\n') if l.strip().startswith('FAIL'))
    shutil.rmtree(tmp, ignore_errors=True)
    return rc, bad, out


if A.mutations:
    # Each entry: the edit, and the EXACT set of case labels it must redden.
    MUTATIONS = {
        'IDENTITY (no change — the harness control)': (
            '#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity)', set()),
        'the corpus narrows back to docs/ (THE regression)': (
            "    return [p for p in sorted(root.rglob('*.md'))",
            "    return [p for p in sorted(root.glob('docs/*.md'))",
            # The whole corpus outside docs/ vanishes, so the OUTSIDE floor fires
            # and every run SKIPs. Note what stays green: the case that builds its
            # own examples-free corpus already expects a SKIP, so it cannot see
            # this — which is why the detection has to come from the healthy-corpus
            # cases rather than from the narrowing case alone.
            {'a healthy corpus passes',
             'it prints the two populations separately, never their sum',
             'a dead intra-doc anchor is caught',
             'a link to a file that does not exist is caught',
             'a broken link in a file outside docs/ is caught',
             'and it exits 1, not 0'}),
        'the outside-docs floor is removed': (
            """    if pop['outside'] < a.min_outside:""", '    if False:',
            {'a corpus with no links outside docs/ SKIPs, never passes',
             'and it says the corpus has narrowed, not merely that it is small',
             "every SKIP line is indented where the caller's filter can see it"}),
        'the link pattern loses its path segment': (
            r"""LINK = re.compile(r'\[([^\]]*)\]\(([^)\s#]*\.md)?(?:#([A-Za-z0-9_\-]+))?\)')""",
            r"""LINK = re.compile(r'\[([^\]]*)\]\(([A-Za-z0-9_\-]+\.md)?(?:#([A-Za-z0-9_\-]+))?\)')""",
            # Identical red set to the corpus narrowing, and that is the finding
            # rather than a flaw: either narrowing alone makes every link outside
            # docs/ invisible, so they are indistinguishable from the outside.
            {'a healthy corpus passes',
             'it prints the two populations separately, never their sum',
             'a dead intra-doc anchor is caught',
             'a link to a file that does not exist is caught',
             'a broken link in a file outside docs/ is caught',
             'and it exits 1, not 0'}),
        'a missing target FILE stops being a finding': (
            """                if tp not in anchors:
                    findings.append(f'{rel}:{ln} -> {tgt} (no such file)')""",
            """                if tp not in anchors:
                    pass""",
            {'a link to a file that does not exist is caught'}),
        'SKIP shares an exit code with PASS': (
            '        return 2\n    if pop', '        return 0\n    if pop',
            {'a too-small corpus SKIPs with exit 2'}),
    }
    rc = 0
    if len(MUTATIONS) < MIN_MUTATIONS:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s), floor {MIN_MUTATIONS}')
        sys.exit(1)
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control')
        sys.exit(1)
    print(f'MUTATIONS {len(MUTATIONS)} defect(s) reintroduced, '
          f'expected red set asserted exactly')
    for label, (old, new, expect) in MUTATIONS.items():
        tmp = pathlib.Path(tempfile.mkdtemp())
        for f in HERE.glob('*.py'):
            shutil.copy2(f, tmp / f.name)
        body = (tmp / 'check-links.py').read_text()
        if body.count(old) != 1:
            print(f'  FAIL  {label}: text occurs {body.count(old)}x, wanted 1 — '
                  f'the mutation is stale and this run measured nothing')
            rc = 1
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        (tmp / 'check-links.py').write_text(body.replace(old, new, 1))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        r = subprocess.run([sys.executable, str(HERE / pathlib.Path(__file__).name),
                            '--from-dir', str(tmp)],
                           capture_output=True, text=True, env=env)
        out = r.stdout + r.stderr
        red = {l.split(':')[0].removeprefix('  FAIL ').strip()
               for l in out.split('\n') if l.startswith('  FAIL ')}
        red = {x for x in red if not x.startswith('floor')}
        if red == expect:
            print(f'  ok    {label}  ({len(red)} case(s) red)')
        else:
            rc = 1
            print(f'  FAIL  {label}')
            for m in sorted(expect - red):
                print(f'          expected red, stayed green: {m}')
            for m in sorted(red - expect):
                print(f'          reddened unexpectedly:      {m}')
        shutil.rmtree(tmp, ignore_errors=True)
    print('MUTATIONS ' + ('all expected red sets matched' if rc == 0
                          else 'a red set did not match — see above'))
    sys.exit(rc)


# ---- the healthy corpus, and its denominator -------------------------------
_rc, _out = run(CORPUS)
check('a healthy corpus passes', lambda: _rc, 0)
check('it prints the two populations separately, never their sum',
      lambda: next((l.strip() for l in _out.split('\n') if 'INFO' in l), ''),
      'INFO  5 markdown link(s) in 3 file(s): 4 under docs/, 1 outside it')

# ---- the three break kinds --------------------------------------------------
check('a dead intra-doc anchor is caught',
      lambda: broken({'docs/gamma.md': '# G\n\n## Here\n\n[x](#nope)\n'})[1],
      ['docs/gamma.md:5 -> gamma.md#nope (no such anchor)'])
check('a link to a file that does not exist is caught',
      lambda: broken({'docs/gamma.md': '# G\n\n## Here\n\n[x](ghost.md)\n'})[1],
      ['docs/gamma.md:5 -> ghost.md (no such file)'])
# THE case the widening bought. It needs BOTH properties — outside docs/, and
# reached by a relative path — because either narrowing alone hides it.
check('a broken link in a file outside docs/ is caught',
      lambda: broken({'examples/sub/readme.md':
                      '# E\n\n[x](../../docs/alpha.md#gone)\n'})[1],
      ['examples/sub/readme.md:3 -> ../../docs/alpha.md#gone (no such anchor)'])
check('and it exits 1, not 0',
      lambda: broken({'examples/sub/readme.md':
                      '# E\n\n[x](../../docs/alpha.md#gone)\n'})[0], 1)

# ---- the floors, which are what end up unverified ---------------------------
def _docs_only():
    """A repo-shaped corpus with nothing outside docs/ — NOT `--root docs/`.

    Rooting at docs/ does not simulate the regression: `inside` is computed
    relative to the root, so with root=docs/ every file's first path part is its
    own filename and the whole corpus counts as OUTSIDE. The run passes and the
    case asserts nothing. The regression is a top-rooted corpus that reaches no
    further than docs/, so that is what this builds.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(CORPUS, tmp / 'c')
    shutil.rmtree(tmp / 'c' / 'examples')
    r = subprocess.run([sys.executable, str(FROM / 'check-links.py'),
                        '--root', str(tmp / 'c'), '--min-links', '4'],
                       capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return r


check('a corpus with no links outside docs/ SKIPs, never passes',
      lambda: _docs_only().returncode, 2)
check('and it says the corpus has narrowed, not merely that it is small',
      lambda: 'narrowed back to docs/' in _docs_only().stdout, True)
check('a too-small corpus SKIPs with exit 2',
      lambda: subprocess.run([sys.executable, str(FROM / 'check-links.py'),
                              '--root', str(CORPUS), '--min-links', '9999'],
                             capture_output=True, text=True).returncode, 2)
check('a missing root SKIPs with exit 2',
      lambda: run(CORPUS / 'no-such-dir')[0], 2)
check('every SKIP line is indented where the caller\'s filter can see it',
      lambda: sorted({l[:6] for l in _docs_only().stdout.split('\n')
                      if 'SKIP' in l}), ['  SKIP'])

# ---- what must NOT be a finding ---------------------------------------------
check('a bare page link to a real file is fine',
      lambda: broken({'docs/gamma.md': '# G\n\n## Here\n\n[x](beta.md)\n'})[1], [])

print(f'\nFIXTURE {checks} check(s): {checks - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if checks < MIN_CASES:
    print(f'  FAIL floor: {checks} check(s) ran, at least {MIN_CASES} expected')
    sys.exit(1)
sys.exit(1 if fails else 0)
