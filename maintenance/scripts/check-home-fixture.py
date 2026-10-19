#!/usr/bin/env python3
"""
Fixture for check-home.py: the gate that holds the Home page's Verified-against paragraph to README.md's and its
task lists to the properties that make a row useful (a fragment on every page link, a Receiver.member call that
check-symbols will actually check, a class that exists, a row count that keeps Home a door).

THE PROTOCOL is check-links-fixture.py's, as check-example-lists-fixture.py restates it: every case is a labelled
check, `--mutations` reverts one guard of check-home.py at a time, every case runs against the copy, and the set of
red labels must equal the one written beside the mutation. A stale mutation (its text not found once) fails the
run, and the IDENTITY mutation must leave nothing red. A label carries no tab, which the runner splits on.

The corpus is a README.md and a docs/index.md in a temporary directory and a jar that is a zip of empty files named
like classes, which is all the gate reads of one.

Usage: python3 maintenance/scripts/check-home-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, concurrent.futures, os, pathlib, shutil, subprocess, sys, tempfile, time, zipfile

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--from-dir', default=str(HERE))
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()
FROM = pathlib.Path(A.from_dir)

MIN_CASES = 33
MIN_MUTATIONS = 28
fails: list[str] = []
seen: list[str] = []

PARA = ('**Verified against Hytale 0.7.2 (build-34).** Each topic page carries its own "Verified against" stamp, and a\n'
        'game update can invalidate any of them until the next re-verification pass.')
RECEIVERS = ['CommandRegistry', 'EventRegistry', 'EntityEventSystem', 'EntityTickingSystem', 'InventoryComponent',
             'BlockOperations', 'PageManager']
ASSETS = ['Parent', 'Container', 'Recipe', 'Instructions', 'CustomModelAnimation']
README = f'# R\n\n{PARA}\n\n## Documentation\n\nText.\n'


def api_row(i, recv=None, extra=''):
    r = recv or RECEIVERS[i % len(RECEIVERS)]
    return f'- **Do thing {i}{extra}** — [Page {i}](page{i}.md#section-{i}). API: `{r}.doIt`.'


def asset_row(i):
    return f'- **Make asset {i}** — [Page {i}](page{i}.md#section-{i}). Key: `{ASSETS[i % len(ASSETS)]}`.'


def home(api=7, asset=5, para=PARA, before='', after='', api_rows=None, asset_rows=None, tail='', intro=''):
    a = api_rows if api_rows is not None else [api_row(i) for i in range(api)]
    b = asset_rows if asset_rows is not None else [asset_row(100 + i) for i in range(asset)]
    return (f'---\ntitle: Home\n---\n\n# H\n\n{para}\n\n{before}## Find it by task\n\n{intro}### In Java (plugins)\n\n'
            + '\n'.join(a) + '\n\n### In JSON (no Java)\n\n' + '\n'.join(b) + f'\n{after}\n## How to read a page\n\nText.\n{tail}')


def make_jar(path, names=RECEIVERS, nested=()):
    with zipfile.ZipFile(path, 'w') as z:
        for n in names:
            z.writestr(f'com/hypixel/hytale/x/{n}.class', b'')
        for n in nested:
            z.writestr(f'com/hypixel/hytale/x/Outer${n}.class', b'')


def run(root, jar=None, from_dir=None):
    cmd = [sys.executable, str((from_dir or FROM) / 'check-home.py'), '--root', str(root)]
    if jar:
        cmd += ['--jar', str(jar)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def broken(index=None, readme=README, jar=True, jar_names=RECEIVERS, nested=(), no_files=(), from_dir=None):
    """Write README.md and docs/index.md (`index` defaults to a healthy Home) and run the gate, with a fake jar
    unless jar=False. -> (rc, sorted FAIL bodies, whole output)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        (tmp / 'docs').mkdir()
        if 'README.md' not in no_files:
            (tmp / 'README.md').write_text(readme)
        if 'docs/index.md' not in no_files:
            (tmp / 'docs/index.md').write_text(home() if index is None else index)
        j = None
        if jar:
            j = tmp / 'fake.jar'
            make_jar(j, jar_names, nested)
        rc, out = run(tmp, j, from_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = sorted(l.strip()[6:].strip() for l in out.split('\n') if l.strip().startswith('FAIL'))
    return rc, bad, out


def check(label, thunk, want):
    seen.append(label)
    try:
        got = thunk()
    except Exception as e:                      # noqa: BLE001
        fails.append(f'{label}\traised {type(e).__name__}: {e}')
        return
    if got != want:
        fails.append(f'{label}\t{got!r} != {want!r}')
    elif A.verbose:
        print(f'  ok   {label}')


# ---- labels ------------------------------------------------------------------------------------------------
L_HEALTHY = 'a Home whose paragraph matches README.md and whose lists hold the properties passes, exit 0'
L_LINE = 'and the PASS line counts the words, the rows by kind, the page links, the names and the names resolved'
L_LINE_NOJAR = 'and without --jar it says the receivers were not resolved'
L_PDIFF = 'a paragraph that differs by one word FAILs, naming the character where it differs'
L_PWRAP = 'a paragraph wrapped differently is the same paragraph'
L_PTAIL = 'a paragraph that differs in its last line FAILs too (the part of a bump that is forgotten)'
L_PEND = 'the paragraph ends at the first blank line, so text after it is not compared'
L_PNONE = 'a file without the paragraph FAILs, saying 0 (README.md and docs/index.md)'
L_PTWICE = 'a file with the paragraph twice FAILs, saying 2'
L_PFENCE = 'a copy of the paragraph inside a code fence is not a paragraph'
L_FILE = 'a missing README.md or docs/index.md FAILs, naming the file'
L_NOSECTION = 'a Home without `## Find it by task` SKIPs, exit 2, saying it is a broken check'
L_NOLIST = 'a section with no list item SKIPs the same way'
L_SECTION_END = 'the section ends at the next `## ` heading, so a list after it is not read'
L_ROWS_LOW = 'fewer than 12 rows FAILs, and 12 passes'
L_ROWS_HIGH = 'more than 18 rows FAILs, and 18 passes'
L_ROWS_SUM = 'the rows of the two lists are added: 7 + 5 passes, and 7 alone does not'
L_FRAG = 'a page link without a #fragment FAILs, naming the line and the link'
L_FRAG_OK = 'a link to a non-.md file or a URL needs no fragment'
L_GROUP = 'a ### group that is neither In Java nor In JSON FAILs, naming it'
L_ITEMOUT = 'a list item above any group FAILs, naming the line'
L_NOSYM = 'an API row whose API: names no Receiver.member FAILs'
L_FIELD = 'a row without its API: or Key: field and a code span FAILs, naming the line'
L_NEG = 'an API row holding a word check-symbols reads as a denial FAILs, naming the word'
L_NEG_ASSET = 'and the same word in an Asset key row is no finding (check-symbols checks no symbol there)'
L_NEG_READ = 'the word list is check-symbols.py\'s NEG, not a copy: a word only that list holds is found'
L_NEG_MISSING = 'a check-symbols.py with no NEG assignment FAILs, saying the gate cannot tell which rows it skips'
L_JAR = 'a receiver that is no class of the jar FAILs, naming it'
L_JAR_NESTED = 'a nested class is a receiver by its own name'
L_JAR_EMPTY = 'a jar with no com/hypixel class FAILs'
L_FENCED = 'a list inside a code fence is not read'
L_MULTI = 'every code span after API: is a call: a second one that is no jar class is found'
L_RC = 'a finding exits 1'
L_ALLCASES = 'ALL_CASES lists exactly the labels the fixture checks'

ALL_CASES = {L_HEALTHY, L_LINE, L_LINE_NOJAR, L_PDIFF, L_PWRAP, L_PTAIL, L_PEND, L_PNONE, L_PTWICE, L_PFENCE, L_FILE, L_NOSECTION,
             L_NOLIST, L_SECTION_END, L_ROWS_LOW, L_ROWS_HIGH, L_ROWS_SUM, L_FRAG, L_FRAG_OK, L_GROUP, L_ITEMOUT, L_NOSYM,
             L_FIELD, L_NEG, L_NEG_ASSET, L_NEG_READ, L_NEG_MISSING, L_JAR, L_JAR_NESTED, L_JAR_EMPTY, L_FENCED, L_MULTI,
             L_RC}

# ---- the mutations -----------------------------------------------------------------------------------------
if A.mutations:
    MUTATIONS = {
        'IDENTITY (no change, the harness control)': (
            '#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity)', set()),
        'the paragraph is compared with its line breaks': (
            "out.append(' '.join(' '.join(lines[i:j]).split()))", "out.append('\\n'.join(lines[i:j]))",
            {L_PWRAP}),
        'a paragraph in a code fence counts': (
            "if i + 1 in fenced or not l.startswith(PARA):", "if not l.startswith(PARA):",
            {L_PFENCE}),
        'the paragraph is its first line only': (
            "while j < len(lines) and lines[j].strip():", "while j < i + 1:",
            {L_PWRAP, L_PTAIL, L_LINE}),
        'the paragraph runs to the next heading, past its blank line': (
            "while j < len(lines) and lines[j].strip():", "while j < len(lines) and not lines[j].startswith('#'):",
            {L_PEND, L_PFENCE}),
        'a second copy of the paragraph is fine': (
            "if len(got) != 1:", "if len(got) < 1:",
            {L_PTWICE}),
        'a differing paragraph is not a finding': (
            "if len(paras) == 2 and paras['README.md'] != paras['docs/index.md']:", "if False:",
            {L_PDIFF, L_PTAIL}),
        'a missing README.md or docs/index.md is not a finding': (
            "            findings.append(f'{rel}: the file is missing')\n            continue",
            "            continue",
            {L_FILE}),
        'a Home without the section does not SKIP': (
            "        if start is None:\n            print(f'  SKIP  docs/index.md has no",
            "        if False:\n            print(f'  SKIP  docs/index.md has no",
            {L_NOSECTION}),
        'a section without a list item does not SKIP': (
            "        if not rows:\n            print(", "        if False:\n            print(",
            {L_NOLIST}),
        'the section runs to the end of the page': (
            "if n not in fenced and lines[n - 1].startswith('## ')), len(lines))", "if False), len(lines))",
            {L_SECTION_END}),
        'the row bounds are not checked': (
            "        if not ROWS_MIN <= total <= ROWS_MAX:", "        if False:",
            {L_ROWS_LOW, L_ROWS_HIGH, L_ROWS_SUM}),
        'the row count is the API list alone': (
            "        total = nrows['api'] + nrows['asset']", "        total = nrows['api'] + 5",
            {L_ROWS_SUM, L_ROWS_HIGH}),
        'a page link needs no fragment': (
            "                    if not frag:", "                    if False:",
            {L_FRAG}),
        'every link needs a fragment, not only .md pages': (
            "                if path.endswith('.md'):", "                if True:",
            {L_FRAG_OK}),
        'an unknown group is not a finding': (
            "            if kind is None:\n                bad.append((n, h))", "            if False:\n                bad.append((n, h))",
            {L_GROUP}),
        'an item above any group is not a finding': (
            "            if kind == 'none':\n                findings.append(", "            if False:\n                findings.append(",
            {L_ITEMOUT}),
        'an API row needs no symbol': (
            "                if not syms:", "                if False:",
            {L_NOSYM}),
        'a row needs no field': (
            "            if not field:\n", "            if False:\n",
            {L_FIELD}),
        'a row check-symbols would skip is not a finding': (
            "                if neg is not None and neg.search(l):", "                if False:",
            {L_NEG, L_NEG_READ}),
        'the denial words are a copy, not check-symbols.py\'s list': (
            "        neg = neg_pattern()", "        neg = re.compile(r'\\b(not|no)\\b', re.I)",
            {L_NEG, L_NEG_READ, L_NEG_MISSING}),
        'an unreadable NEG is not a finding': (
            "        if neg is None:\n            findings.append(", "        if False:\n            findings.append(",
            {L_NEG_MISSING}),
        'a receiver need not be a class': (
            "                        if m.group(1) in jar:", "                        if True:",
            {L_JAR, L_MULTI}),
        'a nested class is a receiver by its whole name': (
            "names.add(n[:-6].rsplit('/', 1)[-1].rsplit('$', 1)[-1])", "names.add(n[:-6].rsplit('/', 1)[-1])",
            {L_JAR_NESTED}),
        'a jar with no class is fine': (
            "                if not jar:", "                if False:",
            {L_JAR_EMPTY}),
        'lists inside code fences are read': (
            "        if n in fenced:\n            continue\n        if l.startswith('### '):", "        if l.startswith('### '):",
            {L_FENCED}),
        'only the first code span after API: is read': (
            "(?:, )?)+)'", "(?:, )?))'",
            {L_MULTI}),
        'a finding exits 0': (
            "    if findings:\n        return 1", "    if findings:\n        return 0",
            {L_RC}),
    }
    print(f'MUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
    if len(MUTATIONS) < MIN_MUTATIONS:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s), floor {MIN_MUTATIONS}')
        sys.exit(1)
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control')
        sys.exit(1)

    def one(item):
        label, (old, new, expect) = item
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            for f in HERE.glob('*.py'):
                shutil.copy2(f, tmp / f.name)
            body = (tmp / 'check-home.py').read_text()
            if body.count(old) != 1:
                return label, None, f'text occurs {body.count(old)}x, wanted 1: the mutation is stale and measured nothing'
            (tmp / 'check-home.py').write_text(body.replace(old, new, 1))
            r = subprocess.run([sys.executable, str(HERE / pathlib.Path(__file__).name), '--from-dir', str(tmp)],
                               capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            out = r.stdout + r.stderr
            red = {l[len('  FAIL '):].split('\t')[0] for l in out.split('\n') if l.startswith('  FAIL ') and '\t' in l}
            return label, red, out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    t0 = time.time()
    rc = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, MUTATIONS.items()))
    for label, red, out in results:
        expect = MUTATIONS[label][2]
        if red is None:
            rc = 1
            print(f'  FAIL  {label}: {out}')
        elif red == expect:
            print(f'  ok    {label}  ({len(red)} case(s) red)')
        else:
            rc = 1
            print(f'  FAIL  {label}')
            for m in sorted(expect - red):
                print(f'          expected red, stayed green: {m}')
            for m in sorted(red - expect):
                print(f'          reddened unexpectedly:      {m}')
    print('MUTATIONS ' + ('all expected red sets matched' if rc == 0 else 'a red set did not match, see above')
          + f' ({time.time() - t0:.0f} s)')
    sys.exit(rc)

# ---- the healthy Home --------------------------------------------------------------------------------------
_rc, _bad, _out = broken()
check(L_HEALTHY, lambda: (_rc, _bad), (0, []))
check(L_LINE, lambda: next((l.strip() for l in _out.split('\n') if 'PASS' in l), ''),
      'PASS  the Verified against paragraph is the same in README.md and docs/index.md (28 words); the task lists '
      'hold 7 API and 5 Asset key rows, 12 page link(s) all with a #fragment, 7 Receiver.member name(s) on rows '
      'check-symbols reads, 7 resolved in the jar')
check(L_LINE_NOJAR, lambda: next((l.strip() for l in broken(jar=False)[2].split('\n') if 'PASS' in l), '')[-40:],
      'n(s) on rows check-symbols reads, receivers not resolved (no --jar)'[-40:])

# ---- the paragraph -----------------------------------------------------------------------------------------
def _collapse(t):
    return ' '.join(t.split())


_P2 = PARA.replace(' own ', ' own-ish ')
_x, _y = _collapse(PARA), _collapse(_P2)
_k = next(i for i, (p, q) in enumerate(zip(_x, _y)) if p != q)
check(L_PDIFF, lambda: broken(home(para=_P2))[1],
      [f"the Verified against paragraph of docs/index.md differs from README.md's at character {_k}: "
       f'README.md "...{_x[max(0, _k - 20):_k + 30]}" docs/index.md "...{_y[max(0, _k - 20):_k + 30]}"'])
check(L_PTAIL, lambda: len(broken(home(para=PARA.replace('any of them', 'any of it')))[1]), 1)
check(L_PWRAP, lambda: broken(home(para=PARA.replace('\n', ' ').replace(', and a', ',\n   and a')))[1], [])
check(L_PEND, lambda: broken(home(para=PARA + '\n\nA different second paragraph.'))[1], [])
check(L_PNONE, lambda: (broken(home(para='Some other text.'))[1], broken(readme='# R\n')[1]),
      (['docs/index.md has 0 paragraphs that start with **Verified against Hytale, wanted exactly 1'],
       ['README.md has 0 paragraphs that start with **Verified against Hytale, wanted exactly 1']))
check(L_PTWICE, lambda: broken(home(para=PARA + '\n\n' + PARA))[1],
      ['docs/index.md has 2 paragraphs that start with **Verified against Hytale, wanted exactly 1'])
check(L_PFENCE, lambda: broken(home(para=PARA + '\n\n```md\n' + PARA + '\n```'))[1], [])
check(L_FILE, lambda: (broken(no_files=('README.md',))[1], broken(no_files=('docs/index.md',))[1]),
      (['README.md: the file is missing'], ['docs/index.md: the file is missing']))

# ---- the section -------------------------------------------------------------------------------------------
_NOSEC = home().replace('## Find it by task', '## Elsewhere')
check(L_NOSECTION, lambda: (broken(_NOSEC)[0], 'a broken check, not a clean run' in broken(_NOSEC)[2]), (2, True))
_NOLISTS = '# H\n\n' + PARA + '\n\n## Find it by task\n\nJust prose.\n\n## Next\n'
check(L_NOLIST, lambda: (broken(_NOLISTS)[0], 'holds no list item' in broken(_NOLISTS)[2]), (2, True))
_late = '\n## Later\n\n- **x** — [a](a.md). API: `Mystery`.\n'
check(L_SECTION_END, lambda: broken(home(after=_late))[1], [])

# ---- row count ---------------------------------------------------------------------------------------------
HIGH = 'wanted 12 to 18'
check(L_ROWS_LOW, lambda: (broken(home(api=6, asset=5))[1], broken(home(api=7, asset=5))[1]),
      (['`## Find it by task` has 11 rows, wanted 12 to 18'], []))
check(L_ROWS_HIGH, lambda: (broken(home(api=7, asset=12))[1], broken(home(api=7, asset=11))[1]),
      (['`## Find it by task` has 19 rows, wanted 12 to 18'], []))
check(L_ROWS_SUM, lambda: broken(home(api=7, asset=0, asset_rows=[]))[1],
      ['`## Find it by task` has 7 rows, wanted 12 to 18'])

# ---- links -------------------------------------------------------------------------------------------------
def _with_api(row):
    rows = [api_row(i) for i in range(6)] + [row]
    return home(api_rows=rows)


check(L_FRAG, lambda: broken(_with_api(api_row(6).replace('page6.md#section-6', 'page6.md')))[1],
      ['docs/index.md:20 links page6.md without a #fragment'])
check(L_FRAG_OK, lambda: broken(_with_api(api_row(6)[:-1] + ' Example: [Ex](../examples/e/Ex6.java) [gh](https://example.com/x) '
                                          '[d](../examples/e/).'))[1], [])

# ---- structure ---------------------------------------------------------------------------------------------
_EXTRA = '\n### Extra\n\n- **x** — [a](a.md#b). API: `A.b`.\n'
check(L_GROUP, lambda: broken(home(after=_EXTRA))[1],
      ['docs/index.md:30 the group `### Extra` is neither `In Java` nor `In JSON`'])
check(L_ITEMOUT, lambda: broken(home(intro='- **x** — [a](a.md#b). API: `A.b`.\n\n'))[1],
      ['docs/index.md:12 is a list item above any `In Java` or `In JSON` group'])
_NOCALL = 'doIt`.'
check(L_NOSYM, lambda: broken(_with_api(api_row(6).replace('`' + RECEIVERS[6 % len(RECEIVERS)] + '.doIt`', '`doIt`')))[1],
      ['docs/index.md:20 names no Receiver.member call after `API:`'])
check(L_FIELD, lambda: (broken(_with_api(api_row(6).replace('API:', 'See:')))[1],
                        broken(_with_api(api_row(6).replace('`' + RECEIVERS[6 % len(RECEIVERS)] + '.doIt`', 'doIt')))[1],
                        broken(home(asset_rows=[asset_row(100 + i) for i in range(4)] + ['- **Make asset** — [P](p.md#s). Key: Parent.']))[1]),
      (['docs/index.md:20 has no `API: ` field with a code span'],
       ['docs/index.md:20 has no `API: ` field with a code span'],
       ['docs/index.md:28 has no `Key: ` field with a code span']))
check(L_MULTI, lambda: broken(_with_api(api_row(6).replace('.doIt`.', '.doIt`, `Ghost.doIt`.')))[1],
      ['docs/index.md:20 names Ghost.doIt, and Ghost is no class of the jar'])

# ---- the denial words --------------------------------------------------------------------------------------
check(L_NEG, lambda: broken(_with_api(api_row(6, extra=' without the old route')))[1] +
                     broken(_with_api(api_row(6, extra=' that is deprecated')))[1],
      ['docs/index.md:20 holds a word check-symbols reads as a denial ("deprecated"), so it would not check the call on this row'])
_ASSET_NEG = home(asset_rows=[asset_row(100 + i) for i in range(4)] + ['- **Make an item with no Java** — [P](p.md#s). Key: `Parent`.'])
check(L_NEG_ASSET, lambda: broken(_ASSET_NEG)[1], [])
check(L_NEG_READ, lambda: broken(_with_api(api_row(6, extra=' renamed')))[1],
      ['docs/index.md:20 holds a word check-symbols reads as a denial ("renamed"), so it would not check the call on this row'])


def _no_neg():
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        for f in FROM.glob('*.py'):
            shutil.copy2(f, tmp / f.name)
        cs = (tmp / 'check-symbols.py').read_text()
        (tmp / 'check-symbols.py').write_text(cs.replace('NEG = re.compile(', 'NEGX = re.compile(', 1))
        return broken(from_dir=tmp)[1]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


check(L_NEG_MISSING, _no_neg, ['check-symbols.py has no NEG assignment to read: the gate cannot tell which rows it skips'])

# ---- the jar -----------------------------------------------------------------------------------------------
check(L_JAR, lambda: broken(_with_api(api_row(6, recv='Ghost')))[1],
      ['docs/index.md:20 names Ghost.doIt, and Ghost is no class of the jar'])
check(L_JAR_NESTED, lambda: broken(_with_api(api_row(6, recv='HudManager')), nested=('HudManager',))[1], [])
check(L_JAR_EMPTY, lambda: [b.split(' ', 1)[0] + ' ' + b.split(' ', 2)[2] for b in broken(jar_names=(), nested=())[1]],
      ['--jar holds no com/hypixel class'])
check(L_FENCED, lambda: broken(home(after='\n```md\n- **x** — [a](a.md). API: `z`.\n### Bogus\n```\n'))[1], [])
check(L_RC, lambda: broken(home(para='Other.'))[0], 1)

# ---- the report --------------------------------------------------------------------------------------------
check(L_ALLCASES, lambda: sorted(set(seen) - {L_ALLCASES}), sorted(ALL_CASES))
print(f'\nFIXTURE {len(seen)} check(s): {len(seen) - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if len(seen) < MIN_CASES:
    print(f'  FAIL floor: {len(seen)} check(s) ran, at least {MIN_CASES} expected')
    sys.exit(1)
sys.exit(1 if fails else 0)
