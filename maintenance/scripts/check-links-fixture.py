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
MIN_MUTATIONS = 31


def run(root, *extra):
    p = subprocess.run([sys.executable, str(FROM / 'check-links.py'),
                        '--root', str(root), '--min-links', '3', '--min-other', '0', *extra],
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


# ---- labels shared by the cases and the mutations that must redden them ----------------------------
# GitHub's own ids (gh-heading-ids.tsv, 51 headings with a `<`) and the text GitHub renders for 42 heading
# shapes (gh-heading-shapes.tsv) are measured data, committed beside the corpus; see the README there.
L_IDS = 'check-links slugs every heading of the GitHub id table to the id GitHub gave it'
L_IDS_N = 'the id table holds the 51 headings it was measured on, so a short read cannot pass it'
L_IDS_OLD = 'NEGATIVE CONTROL, the character rule alone (the slug before the tag rule) misses 18 of those ids'
L_SHAPES = 'strip_tags leaves exactly the text GitHub renders, for every measured heading shape'
L_SHAPES_N = 'the shape table holds the 42 shapes it was measured on'
L_CODE_KEEP = 'a code span keeps its angle brackets, as in a heading written ``## `Codec<T>` ``'
L_GEN_LINK = 'a link by the id GitHub gave a generic heading resolves'
L_GEN_RAW = 'a link by the raw-character id of a generic heading FAILs (GitHub has no such anchor)'
L_NONMD_DEAD = 'a dead non-.md file target FAILs'
L_NONMD_LIVE = 'a live non-.md file target passes'
L_DIR_LIVE = 'a directory target passes, with and without the trailing slash'
L_DIR_DEAD = 'a dead directory target FAILs'
L_FENCE_NONMD = 'a link in a code fence is not read, so a dead non-.md target there is no finding'
L_FENCE_MD = 'and nor is a dead .md link in a code fence'
L_URLS = 'a URL, a mailto link and a // URL are not read as paths'
L_FRAGQ = 'a fragment or a query after a non-.md target does not stop it being found'
L_OUTSIDE = 'a target that leaves the repository FAILs, even where the file exists'
L_PCT = 'a percent-encoded path is decoded before it is looked up'
L_TITLE = 'a link with a title is read and its dead target FAILs'
L_IMAGE = 'an image target is a link too'
L_COUNT = 'the run counts the non-.md targets it read and the directories among them'
L_FLOOR = 'a corpus with no non-.md target SKIPs, never passes'
L_FLOOR_MSG = 'and the SKIP says the reader of links that leave the .md pages has gone blind'
L_ABS = 'a root-relative target (/docs/alpha.md) resolves against the repository root'
L_BADFRAG = 'an anchor outside [A-Za-z0-9_-] is skipped, not reported (it can never be valid)'
L_BADFRAG_MD = 'and on an existing .md target too'
L_MDFRAG_BADCHAR = 'a .md target whose anchor is unfixable still has its FILE checked'

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
    # The new cases that expect a FINDING from a non-.md (or unfixable-anchor) link, and the slug case that
    # expects one: red whenever the run SKIPs instead, like every other case that expects a finding.
    NONMD_DEAD = {L_NONMD_DEAD, L_DIR_DEAD, L_TITLE, L_IMAGE, L_ABS,
                  'a dead target in a file outside docs/ is caught too (the examples/ links)',
                  'and it exits 1', 'and a dead one is still dead with a fragment on it'}
    NONMD_FINDINGS = {L_NONMD_DEAD, L_DIR_DEAD, L_OUTSIDE, L_TITLE, L_IMAGE, L_ABS, L_MDFRAG_BADCHAR, L_GEN_RAW,
                      'a dead target in a file outside docs/ is caught too (the examples/ links)',
                      'and it exits 1', 'and a dead one is still dead with a fragment on it'}
    # The link-dependent cases the two corpus narrowings share (see the first of them).
    LINK_DEPENDENT = {
        L_FLOOR_MSG,
        'a healthy corpus passes',
        'it prints the two populations separately, never their sum',
        'a dead intra-doc anchor is caught',
        'a link to a file that does not exist is caught',
        'a broken link in a file outside docs/ is caught',
        'and it exits 1, not 0',
        'fixture links are still counted and reported, just not floored'}
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
            LINK_DEPENDENT | FENCED_FINDINGS | ORPHAN_CASES | WT_DENOM | NONMD_FINDINGS),
        'the outside-docs floor is removed': (
            """    if pop['outside'] < a.min_outside:""", '    if False:',
            {'a corpus with no links outside docs/ SKIPs, never passes',
             'and it says the corpus has narrowed, not merely that it is small',
             "every SKIP line is indented where the caller's filter can see it",
             'the gate fixtures do not vote in the floor they are testing',
             'and the SKIP names the narrowing, not the corpus size'}),
        'the link pattern loses its path segment': (
            r"""ANY_LINK = re.compile(r'\[([^\]]*)\]\(([^)\s]*)(?:\s+""",
            r"""ANY_LINK = re.compile(r'\[([^\]]*)\]\(([A-Za-z0-9_.#\-]*)(?:\s+""",
            # The same red set as the corpus narrowing for the link-dependent cases, and that is the
            # finding rather than a flaw: either narrowing alone makes every link outside docs/
            # invisible, so they are indistinguishable from the outside. The ORPHAN_CASES are not
            # in it: a fence orphan needs no link, so this pattern change cannot hide one. Two of them
            # still go red, only because the corpus's own outside link (which keeps the OUTSIDE floor
            # satisfied) is a path link: the docs/ ~~~ case and the UNCLOSED case (which brings its own
            # path link, `../../docs/alpha.md`, to clear that floor).
            LINK_DEPENDENT | FENCED_FINDINGS | WT_DENOM | NONMD_FINDINGS | {L_COUNT}
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
            """                    if tp not in anchors:
                        findings.append(f'{rel}:{ln} -> {tgt} (no such file)')""",
            """                    if tp not in anchors:
                        pass""",
            {'a link to a file that does not exist is caught',
             'CONTROL, a broken link in a checkout-shaped dir that is NOT .claude is a finding',
             L_MDFRAG_BADCHAR}),
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
        # ---- the slug ----
        'the tag rule is dropped: the slug is the character rule alone': (
            "    return char_slug(strip_tags(t))", "    return char_slug(t)",
            {L_IDS, L_GEN_LINK, L_GEN_RAW}),
        'an open tag is anything up to a `>` (so <K, T> and <ECS_TYPE> are dropped)': (
            "    r'<[A-Za-z][A-Za-z0-9-]*(?:' + _ATTR + r')*\\s*/?>'      # open tag",
            "    r'<[A-Za-z][^>]*>'      # open tag",
            {L_IDS, L_SHAPES, 'a heading that keeps its text (<K, T> is no tag) is linked by the text'}),
        'an open tag has no attributes (so <T extends Transaction> is kept)': (
            "    r'<[A-Za-z][A-Za-z0-9-]*(?:' + _ATTR + r')*\\s*/?>'      # open tag",
            "    r'<[A-Za-z][A-Za-z0-9-]*\\s*/?>'      # open tag",
            {L_IDS, L_SHAPES}),
        'code spans are not protected from the tag rule': (
            "        out.append(m.group(0))", "        out.append(RAW_HTML.sub('', m.group(0)))",
            {L_IDS, L_SHAPES, L_CODE_KEEP}),
        'closing tags are kept': (
            "    r'|</[A-Za-z][A-Za-z0-9-]*\\s*>'                        # closing tag\n", "",
            {L_SHAPES}),
        'comments, processing instructions, declarations and CDATA are kept': (
            "    r'|<!--.*?-->'                                         # comment\n"
            "    r'|<\\?.*?\\?>'                                          # processing instruction\n"
            "    r'|<![A-Za-z][^>]*>'                                   # declaration\n"
            "    r'|<!\\[CDATA\\[.*?\\]\\]>', re.S)", "    , re.S)",
            {L_SHAPES}),
        # ---- every relative target ----
        'links in code fences are read again': (
            "            if ln in fenced:\n                continue            # `list[i](x)` in a fence is code, not a link\n", "",
            {L_FENCE_NONMD, L_FENCE_MD}),
        'a non-.md target is never looked up': (
            "                    elif not dest.exists():", "                    elif False:",
            NONMD_DEAD),
        'a directory is not an existing target (only files are)': (
            "                    elif not dest.exists():", "                    elif not dest.is_file():",
            {L_DIR_LIVE, L_COUNT}),
        'the outside-the-repository test is removed': (
            "                    if not dest.is_relative_to(os.path.normpath(str(root))):", "                    if False:",
            {L_OUTSIDE}),
        'a URL is read as a path': (
            "SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:|^//')", "SCHEME = re.compile(r'^\\0')",
            {L_URLS}),
        'a query string stays on the path': (
            "urllib.parse.unquote(path.partition('?')[0])", "urllib.parse.unquote(path)",
            {L_FRAGQ}),
        'a percent-encoded path is not decoded': (
            "urllib.parse.unquote(path.partition('?')[0])", "path.partition('?')[0]",
            {L_PCT}),
        'a root-relative target is read from the page, not the root': (
            "base = root if target.startswith('/') else page.parent", "base = page.parent",
            {L_ABS}),
        'the non-.md floor is removed': (
            "    if other < a.min_other:", "    if False:",
            {L_FLOOR, L_FLOOR_MSG}),
        'a link with a title is not read': (
            "(?:\\s+(?:\"[^\"]*\"|\\\'[^\\\']*\\\'))?\\)')", "\\)')",
            {L_TITLE}),
        'an unfixable anchor skips the whole link, file included': (
            "                        an = None\n", "                        continue\n",
            {L_MDFRAG_BADCHAR}),
        'an unfixable anchor is reported as a missing anchor': (
            "if an is not None and not re.fullmatch(r'[A-Za-z0-9_\\-]+', an):", "if False:",
            {L_BADFRAG, L_BADFRAG_MD}),
        'the directories among the non-.md targets are not counted': (
            "other_dirs += dest.is_dir()", "other_dirs += 0",
            {L_COUNT}),
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
    # one non-.md target (a directory), so the non-.md floor cannot be the one that fires
    (tmp / 'c' / 'docs' / 'dir.md').write_text('# D\n\n[here](./)\n')
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
    bulk += ['', '[here](./)']      # one non-.md target, so the non-.md floor cannot be the one that fires
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
      lambda: broken({'examples/sub/readme.md': '# E\n\n[up](../../docs/alpha.md)\n\n```bash\n# Phantom\n'})[1],
      ['examples/sub/readme.md:5: fence census orphan (unclosed: the fence opened here (```bash) has no closer before EOF)'])
check('a ```Java tag outside docs/ is NOT an orphan (the tag allowlist is a docs/ rule)',
      lambda: broken({'maintenance/fixtures/doctype/x.md': '# I\n\n```Java\nx\n```\n'})[1], [])
check('the run reports how many files were fence-censused and how many orphans it found',
      lambda: next((l.strip() for l in broken({'examples/sub/readme.md': _TILDE})[2].split('\n') if 'fence-censused' in l), ''),
      'INFO  3 file(s) fence-censused, 2 orphan marker(s)')

# ---- the slug is GitHub's ----------------------------------------------------
# Measured ground truth, not a restatement of the regex: for every docs heading at d361e13 with a `<`, the
# id GitHub gave it; and for 42 heading shapes the text GitHub renders. The module is loaded from FROM so a
# mutated copy is the one under test.
import importlib.util
_spec = importlib.util.spec_from_file_location('check_links_under_test', FROM / 'check-links.py')
CL = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(FROM))
_spec.loader.exec_module(CL)
FIX = HERE.parents[0] / 'fixtures' / 'links'


def _tsv(name):
    return [l.rstrip('\n').split('\t') for l in (FIX / name).read_text().splitlines()
            if l and not l.startswith('#')]


IDS = _tsv('gh-heading-ids.tsv')
SHAPES = _tsv('gh-heading-shapes.tsv')
check(L_IDS_N, lambda: len(IDS), 51)
check(L_IDS, lambda: [f'{f}:{n} {h!r} -> {CL.slug(h)} (GitHub {i})' for f, n, h, i in IDS if CL.slug(h) != i], [])
check(L_IDS_OLD, lambda: len([1 for f, n, h, i in IDS if CL.char_slug(h) != i]), 18)
check(L_SHAPES_N, lambda: len(SHAPES), 42)
check(L_SHAPES, lambda: [f'{h!r} -> {CL.strip_tags(h)!r} (GitHub {t!r})' for h, t in SHAPES
                          if CL.strip_tags(h).replace('`', '').strip() != t], [])
check(L_CODE_KEEP, lambda: CL.slug('`Codec<T>` x'), 'codect-x')
check('the character rule alone is what the site shares: it never strips a tag',
      lambda: (CL.char_slug('Codec<T> x'), CL.char_slug('Codec<K, T> x')), ('codect-x', 'codeck-t-x'))
_GEN = '# G\n\n## IAsyncEvent<KeyType>\n\n'
check(L_GEN_LINK, lambda: broken({'docs/gamma.md': _GEN + '[x](#iasyncevent)\n'})[1], [])
check(L_GEN_RAW, lambda: broken({'docs/gamma.md': _GEN + '[x](#iasynceventkeytype)\n'})[1],
      ['docs/gamma.md:5 -> gamma.md#iasynceventkeytype (no such anchor)'])
check('a heading that keeps its text (<K, T> is no tag) is linked by the text',
      lambda: broken({'docs/gamma.md': '# G\n\n## AssetCodecMapCodec<K, T>\n\n[x](#assetcodecmapcodeck-t)\n'})[1], [])

# ---- every relative target, not only .md ---------------------------------------
def _nonmd(body, extra=None):
    return broken({'docs/gamma.md': '# G\n\n' + body, **(extra or {})})
check(L_NONMD_DEAD, lambda: _nonmd('[x](nope.java)\n')[1],
      ['docs/gamma.md:3 -> nope.java (no such file or directory)'])
check(L_NONMD_LIVE, lambda: _nonmd('[x](data.json)\n', {'docs/data.json': '{}'})[1], [])
check(L_DIR_LIVE, lambda: _nonmd('[x](pack/)\n[y](pack)\n', {'docs/pack/a.json': '{}'})[1], [])
check(L_DIR_DEAD, lambda: _nonmd('[x](nopack/)\n')[1], ['docs/gamma.md:3 -> nopack/ (no such file or directory)'])
check('a dead target in a file outside docs/ is caught too (the examples/ links)',
      lambda: broken({'examples/sub/readme.md': '# E\n\n[up](../../docs/alpha.md)\n[x](src/Gone.java)\n'})[1],
      ['examples/sub/readme.md:4 -> src/Gone.java (no such file or directory)'])
check('and it exits 1', lambda: _nonmd('[x](nope.java)\n')[0], 1)
_FENCED = '```java\nlist[0](nope.java);\n```\n\n```\n[y](ghost.md)\n```\n'
check(L_FENCE_NONMD, lambda: _nonmd(_FENCED)[1], [])
check(L_FENCE_MD, lambda: _nonmd('```\n[y](ghost.md#x)\n```\n')[1], [])
check(L_URLS, lambda: _nonmd('[a](https://example.invalid/x.md)\n[b](mailto:a@b.invalid)\n[c](//example.invalid/y)\n')[1], [])
check(L_FRAGQ, lambda: _nonmd('[x](data.json#frag)\n[y](data.json?raw=1)\n', {'docs/data.json': '{}'})[1], [])
check('and a dead one is still dead with a fragment on it',
      lambda: _nonmd('[x](nope.json#frag)\n')[1], ['docs/gamma.md:3 -> nope.json#frag (no such file or directory)'])
check(L_OUTSIDE, lambda: _nonmd('[x](../../outside.txt)\n', {'../outside.txt': 'x'})[1],
      ['docs/gamma.md:3 -> ../../outside.txt (outside the repository)'])
check(L_PCT, lambda: _nonmd('[x](my%20file.txt)\n', {'docs/my file.txt': 'x'})[1], [])
check(L_TITLE, lambda: _nonmd('[x](nope.java "a title")\n')[1],
      ['docs/gamma.md:3 -> nope.java (no such file or directory)'])
check(L_IMAGE, lambda: _nonmd('![alt](pic.png)\n')[1], ['docs/gamma.md:3 -> pic.png (no such file or directory)'])
check(L_ABS, lambda: _nonmd('[x](/docs/alpha.md#real-section)\n[y](/docs/nope.json)\n')[1],
      ['docs/gamma.md:4 -> /docs/nope.json (no such file or directory)'])
check(L_BADFRAG, lambda: _nonmd('[x](#a.b)\n')[1], [])
check(L_BADFRAG_MD, lambda: _nonmd('[x](alpha.md#a.b)\n')[1], [])
check(L_MDFRAG_BADCHAR, lambda: _nonmd('[x](ghost.md#a.b)\n')[1], ['docs/gamma.md:3 -> ghost.md (no such file)'])
check(L_COUNT, lambda: next((l.strip() for l in _nonmd('[x](pack/)\n[y](data.json)\n',
                                                         {'docs/pack/a.json': '{}', 'docs/data.json': '{}'})[2].split('\n')
                             if 'non-.md' in l), ''),
      'INFO  2 relative non-.md target(s) checked for existence (1 directories)')
check(L_FLOOR, lambda: subprocess.run([sys.executable, str(FROM / 'check-links.py'), '--root', str(CORPUS),
                                       '--min-links', '3'], capture_output=True, text=True).returncode, 2)
check(L_FLOOR_MSG, lambda: 'has gone blind' in subprocess.run(
    [sys.executable, str(FROM / 'check-links.py'), '--root', str(CORPUS), '--min-links', '3'],
    capture_output=True, text=True).stdout, True)

print(f'\nFIXTURE {checks} check(s): {checks - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if checks < MIN_CASES:
    print(f'  FAIL floor: {checks} check(s) ran, at least {MIN_CASES} expected')
    sys.exit(1)
sys.exit(1 if fails else 0)
