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
import argparse, os, pathlib, re, shutil, subprocess, sys, tempfile

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
MIN_CASES = 35
MIN_MUTATIONS = 12


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
    # Every case that expects a FINDING goes red when the run SKIPs instead (the two corpus
    # narrowings below), so the fenced-comment cases that expect one belong to those sets.
    FENCED_FINDINGS = {
        'a link to the would-be anchor of a `# comment` in a bash fence FAILs',
        'and the fenced-comment link makes the gate exit 1',
        'a cross-file link to a fenced comment FAILs too',
        'PIN, a `# comment` in a BLOCKQUOTED fence is not an anchor',
        'PIN, a `# comment` in an INDENTED fence is not an anchor',
        'and there is no #dup-1 because there is only one heading Dup'}
    # Cases that expect an orphan or a worktree finding: red whenever the run SKIPs instead.
    ORPHAN_CASES = {
        'CONTROL, a broken link in a checkout-shaped dir that is NOT .claude is a finding',
        'a ~~~ fence in docs/gamma.md FAILs naming both markers, and the phantom link still resolves',
        'a ~~~ fence in examples/sub/readme.md FAILs naming both markers, and the phantom link still resolves',
        'a ~~~ fence in maintenance/notes.md FAILs naming both markers, and the phantom link still resolves',
        'a ~~~ fence in CLAUDE.md FAILs naming both markers, and the phantom link still resolves',
        'and a file with an orphan makes the gate exit 1',
        'an UNCLOSED fence outside docs/ FAILs naming its opener',
        'the run reports how many files were fence-censused and how many orphans it found'}
    # The worktree denominator case pins the INFO line, so it goes red when the outside population goes.
    WT_DENOM = {'and the file is not in the denominator either'}
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
             'and it exits 1, not 0',
             'fixture links are still counted and reported, just not floored'} | FENCED_FINDINGS | ORPHAN_CASES | WT_DENOM),
        'the outside-docs floor is removed': (
            """    if pop['outside'] < a.min_outside:""", '    if False:',
            {'a corpus with no links outside docs/ SKIPs, never passes',
             'and it says the corpus has narrowed, not merely that it is small',
             "every SKIP line is indented where the caller's filter can see it",
             'the gate fixtures do not vote in the floor they are testing',
             'and the SKIP names the narrowing, not the corpus size'}),
        'the link pattern loses its path segment': (
            r"""LINK = re.compile(r'\[([^\]]*)\]\(([^)\s#]*\.md)?(?:#([A-Za-z0-9_\-]+))?\)')""",
            r"""LINK = re.compile(r'\[([^\]]*)\]\(([A-Za-z0-9_\-]+\.md)?(?:#([A-Za-z0-9_\-]+))?\)')""",
            # The same red set as the corpus narrowing for the link-dependent cases, and that is the
            # finding rather than a flaw: either narrowing alone makes every link outside docs/
            # invisible, so they are indistinguishable from the outside. The ORPHAN_CASES are not
            # in it: a fence orphan needs no link, so this pattern change cannot hide one. Two of them
            # still go red, only because the corpus's own outside link (which keeps the OUTSIDE floor
            # satisfied) is a path link: the docs/ ~~~ case and the UNCLOSED case (which brings its own
            # path link, `../../docs/alpha.md`, to clear that floor).
            {'a healthy corpus passes',
             'it prints the two populations separately, never their sum',
             'a dead intra-doc anchor is caught',
             'a link to a file that does not exist is caught',
             'a broken link in a file outside docs/ is caught',
             'and it exits 1, not 0',
             'fixture links are still counted and reported, just not floored'} | FENCED_FINDINGS | WT_DENOM
            | {'a ~~~ fence in docs/gamma.md FAILs naming both markers, and the phantom link still resolves',
               'an UNCLOSED fence outside docs/ FAILs naming its opener'}),
        'gate-fixture links vote in the floor again': (
            """        elif rel.parts[:2] == ('maintenance', 'fixtures'):
            bucket = 'fixture'""",
            """        elif False:
            bucket = 'fixture'""",
            # Only the three production cases move: the fixture's OWN corpus has
            # nothing under maintenance/fixtures when rooted at CORPUS, so its
            # bucket is 0 either way. A mutation that reddens only the cases built
            # for it is the shape you want.
            {'the gate fixtures do not vote in the floor they are testing',
             'and the SKIP names the narrowing, not the corpus size',
             'fixture links are still counted and reported, just not floored'}),

        'a missing target FILE stops being a finding': (
            """                if tp not in anchors:
                    findings.append(f'{rel}:{ln} -> {tgt} (no such file)')""",
            """                if tp not in anchors:
                    pass""",
            {'a link to a file that does not exist is caught',
             'CONTROL, a broken link in a checkout-shaped dir that is NOT .claude is a finding'}),
        'headings inside code fences are read as anchors again': (
            """        if no in fenced:
            passed_over += 1
            continue
""", '',
            # The fence-blind heading reader. Reddens exactly the cases that look for
            # a fenced comment's anchor, and the duplicate-slot one (the phantom takes
            # `dup`, the real heading becomes `dup-1`). The two PINs stay green under it.
            {'a link to the would-be anchor of a `# comment` in a bash fence FAILs',
             'and the fenced-comment link makes the gate exit 1',
             'a cross-file link to a fenced comment FAILs too',
             'and there is no #dup-1 because there is only one heading Dup',
             'the run reports the fenced heading-shaped lines it passed over'}),
        '.claude is scanned again (agent worktrees count as docs)': (
            "SKIP_DIRS = {'.git', '.claude', 'build'", "SKIP_DIRS = {'.git', 'build'",
            {'a broken link under .claude/worktrees/ is not scanned',
             'and the file is not in the denominator either'}),
        'the fence census is applied to docs/ only': (
            "for _name, no, why in doc_fences.orphans_of(str(rel), texts[p]):",
            "for _name, no, why in (doc_fences.orphans_of(str(rel), texts[p]) if bucket == 'docs' else []):",
            {'a ~~~ fence in examples/sub/readme.md FAILs naming both markers, and the phantom link still resolves',
             'a ~~~ fence in maintenance/notes.md FAILs naming both markers, and the phantom link still resolves',
             'a ~~~ fence in CLAUDE.md FAILs naming both markers, and the phantom link still resolves',
             'and a file with an orphan makes the gate exit 1',
             'an UNCLOSED fence outside docs/ FAILs naming its opener',
             'the run reports how many files were fence-censused and how many orphans it found'}),
        'the fence census is not applied at all': (
            "for _name, no, why in doc_fences.orphans_of(str(rel), texts[p]):",
            "for _name, no, why in []:",
            ORPHAN_CASES - {'CONTROL, a broken link in a checkout-shaped dir that is NOT .claude is a finding'}),
        'the fence census also applies the docs/ tag allowlist': (
            "doc_fences.orphans_of(str(rel), texts[p])",
            "doc_fences.orphans_of(str(rel), texts[p], doc_fences.ALLOWED_TAGS)",
            {'a ```Java tag outside docs/ is NOT an orphan (the tag allowlist is a docs/ rule)'}),
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
      'INFO  5 markdown link(s) in 3 file(s): 4 under docs/, 1 outside it, '
      '0 in gate fixtures (checked, not floored)')

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

# ---- the floor's VALUE, not just its mechanism ------------------------------
# The `if pop['outside'] < a.min_outside:` -> `if False:` mutation proves the floor
# FIRES. Nothing proved the number it fires on is adequate for the population
# production sees — and it was not: the gate's own fixture corpus contributed 5 of
# the 106 "outside" links against a floor of 1, so the scaffolding alone cleared
# it. Rebuild the real regression (top-rooted, reaching no further than docs/,
# with the fixture directory surviving as it would) and the gate passed green.
#
# This case runs the PRODUCTION invocation with production defaults — no
# --min-outside override — over a corpus whose only non-docs/ markdown is this
# repo's real fixture tree. `docs/bulk.md` exists so the corpus clears the
# production --min-links of 100; without it the TOTAL floor fires first and the
# case would pass while asserting nothing about the outside floor, which is the
# same trap as `--root docs/`.
def _production_on_narrowed():
    tmp = pathlib.Path(tempfile.mkdtemp())
    root = tmp / 'c'
    shutil.copytree(CORPUS / 'docs', root / 'docs')
    shutil.copytree(HERE.parents[0] / 'fixtures' / 'links',
                    root / 'maintenance' / 'fixtures' / 'links')
    bulk = ['# Bulk', '', '## Target', '']
    bulk += [f'- [l{i}](#target)' for i in range(120)]
    (root / 'docs' / 'bulk.md').write_text('\n'.join(bulk) + '\n')
    r = subprocess.run([sys.executable, str(FROM / 'check-links.py'), '--root', str(root)],
                       capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return r


check('the gate fixtures do not vote in the floor they are testing',
      lambda: _production_on_narrowed().returncode, 2)
check('and the SKIP names the narrowing, not the corpus size',
      lambda: 'narrowed back to docs/' in _production_on_narrowed().stdout, True)
check('fixture links are still counted and reported, just not floored',
      lambda: re.search(r'(\d+) outside it, (\d+) in gate fixtures',
                        _production_on_narrowed().stdout).groups(), ('0', '5'))

# ---- what must NOT be a finding ---------------------------------------------
check('a bare page link to a real file is fine',
      lambda: broken({'docs/gamma.md': '# G\n\n## Here\n\n[x](beta.md)\n'})[1], [])

# ---- headings inside code fences are not anchors ---------------------------
# A `# comment` line in a bash fence matches the heading pattern. Read as a heading
# it is an anchor, so a link to a section that does not exist but whose slug equals
# the comment used to PASS (measured at HEAD before the fix: 00-overview.md:105,
# 02-structure.md:412, i18n.md:61, ui-templates.md:451 and CLAUDE.md:18/22 were all
# anchors, and no link targeted one, so no verdict had moved). The fence membership
# is doc_fences.py's, shared with every other gate.
_BASH = '# G\n\n## Here\n\n```bash\n# Phantom Section\nrun\n```\n\n'
check('a link to the would-be anchor of a `# comment` in a bash fence FAILs',
      lambda: broken({'docs/gamma.md': _BASH + '[x](#phantom-section)\n'})[1],
      ['docs/gamma.md:10 -> gamma.md#phantom-section (no such anchor)'])
check('and the fenced-comment link makes the gate exit 1',
      lambda: broken({'docs/gamma.md': _BASH + '[x](#phantom-section)\n'})[0], 1)
check('a cross-file link to a fenced comment FAILs too',
      lambda: broken({'docs/gamma.md': _BASH,
                      'examples/sub/readme.md': '# E\n\n[x](../../docs/gamma.md#phantom-section)\n'})[1],
      ['examples/sub/readme.md:3 -> ../../docs/gamma.md#phantom-section (no such anchor)'])
# PIN, not a detector: a `> # comment` line never matched `^#{1,6}`, so this holds under
# the fence-blind pattern as well and no mutation can redden it. It is here because the
# ITEM names blockquoted fences and an indented one is the same shape; if the heading
# pattern ever learns to look inside a container, these are the first to notice.
check('PIN, a `# comment` in a BLOCKQUOTED fence is not an anchor',
      lambda: broken({'docs/gamma.md': '# G\n\n> ```bash\n> # Quoted Phantom\n> ```\n\n[x](#quoted-phantom)\n'})[1],
      ['docs/gamma.md:7 -> gamma.md#quoted-phantom (no such anchor)'])
check('PIN, a `# comment` in an INDENTED fence is not an anchor',
      lambda: broken({'docs/gamma.md': '# G\n\n1. step\n\n   ```bash\n   # Indented Phantom\n   ```\n\n[x](#indented-phantom)\n'})[1],
      ['docs/gamma.md:9 -> gamma.md#indented-phantom (no such anchor)'])
# Healthy twins: a real heading is still an anchor, and a fenced comment of the same
# slug does not consume the duplicate counter (`dup` is the heading, `dup-1` is nothing).
# Fence-blind, the phantom takes `dup` and the real heading becomes `dup-1`, so `#dup`
# keeps resolving and only `#dup-1` tells the two readings apart.
check('a REAL heading is still an anchor beside a fence holding the same words',
      lambda: broken({'docs/gamma.md': _BASH + '## Phantom Section\n\n[x](#phantom-section)\n'})[1], [])
_DUP = '# G\n\n```bash\n# Dup\n```\n\n## Dup\n\n'
check('a fenced comment beside a heading of the same slug leaves #dup resolving',
      lambda: broken({'docs/gamma.md': _DUP + '[x](#dup)\n'})[1], [])
check('and there is no #dup-1 because there is only one heading Dup',
      lambda: broken({'docs/gamma.md': _DUP + '[x](#dup-1)\n'})[1],
      ['docs/gamma.md:9 -> gamma.md#dup-1 (no such anchor)'])
# The denominator: the run says how many heading-shaped lines it passed over, so a run
# that was never offered one can be told from one that excluded it.
check('the run reports the fenced heading-shaped lines it passed over',
      lambda: re.search(r'(\d+) heading-shaped line\(s\) inside code fences',
                        broken({'docs/gamma.md': _BASH + '[x](#here)\n'})[2]).group(1), '1')

# ---- agent worktrees under .claude/ are not part of the corpus --------------
# Each parallel agent has a full checkout under .claude/worktrees/<id>/. A main-checkout run read
# them as a second copy of the repo: 4484 links in 262 files against the tracked tree's 2242 in 131
# (MINOR-3). The control is the SAME file at a path outside .claude/, which must be a finding, so a
# green here is "skipped by name" and not "the broken link was never broken".
_WT = '# W\n\n[x](ghost.md)\n'
check('CONTROL, a broken link in a checkout-shaped dir that is NOT .claude is a finding',
      lambda: broken({'extra/worktrees/a/docs/w.md': _WT})[1],
      ['extra/worktrees/a/docs/w.md:3 -> ghost.md (no such file)'])
check('a broken link under .claude/worktrees/ is not scanned',
      lambda: broken({'.claude/worktrees/a/docs/w.md': _WT})[1], [])
check('and the file is not in the denominator either',
      lambda: next((l.strip() for l in broken({'.claude/worktrees/a/docs/w.md': _WT})[2].split('\n') if 'INFO' in l), ''),
      'INFO  5 markdown link(s) in 3 file(s): 4 under docs/, 1 outside it, 0 in gate fixtures (checked, not floored)')

# ---- the fence census applies to every file this gate scans ------------------
# doc_fences.py refuses ~~~ (and four backticks, an unclosed fence, ...), so the lines inside such a
# fence are NOT in fence_lines and a `# comment` there reads as a heading. In docs/ the census in
# verify-docs.sh FAILs on the marker; outside docs/ nothing did, so a link to `#phantom` passed
# (MINOR-9). Each file below also carries that link, which resolves under the unsupported fence.
_TILDE = '# T\n\n~~~bash\n# Phantom\n~~~\n\n[x](#phantom)\n'
_TWHY = 'only three-backtick fences are supported, found a ~~~ marker: ~~~bash'
_TWHY2 = 'only three-backtick fences are supported, found a ~~~ marker: ~~~'
def _orph(rel):
    return [f'{rel}:3: fence census orphan ({_TWHY})', f'{rel}:5: fence census orphan ({_TWHY2})']
for _rel in ('docs/gamma.md', 'examples/sub/readme.md', 'maintenance/notes.md', 'CLAUDE.md'):
    check(f'a ~~~ fence in {_rel} FAILs naming both markers, and the phantom link still resolves',
          lambda _rel=_rel: broken({_rel: _TILDE})[1], _orph(_rel))
check('and a file with an orphan makes the gate exit 1',
      lambda: broken({'examples/sub/readme.md': _TILDE})[0], 1)
check('an UNCLOSED fence outside docs/ FAILs naming its opener',
      lambda: broken({'examples/sub/readme.md': '# E\n\n```bash\n# Phantom\n\n[x](../../docs/alpha.md)\n'})[1],
      ['examples/sub/readme.md:3: fence census orphan (unclosed: the fence opened here (```bash) has no closer before EOF)'])
check('a ```Java tag outside docs/ is NOT an orphan (the tag allowlist is a docs/ rule)',
      lambda: broken({'maintenance/fixtures/doctype/x.md': '# I\n\n```Java\nx\n```\n'})[1], [])
check('the run reports how many files were fence-censused and how many orphans it found',
      lambda: next((l.strip() for l in broken({'examples/sub/readme.md': _TILDE})[2].split('\n') if 'fence-censused' in l), ''),
      'INFO  3 file(s) fence-censused, 2 orphan marker(s)')

print(f'\nFIXTURE {checks} check(s): {checks - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if checks < MIN_CASES:
    print(f'  FAIL floor: {checks} check(s) ran, at least {MIN_CASES} expected')
    sys.exit(1)
sys.exit(1 if fails else 0)
