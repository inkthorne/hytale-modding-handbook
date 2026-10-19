#!/usr/bin/env python3
"""
Fixture for generate-llms-txt.py and for verify-docs.sh's "llms.txt generates, and docs/llms.txt is current" section.

WHAT IT PROTECTS. docs/llms.txt is the file an AI tool reads first. Its groups must be the sidebar's, its examples
must be the tracked directories with the table's Type and description, its build must be Home's, and a generator that
cannot say any of that must fail loudly instead of writing a plausible file. Before the section existed
`generate | cmp` took cmp's status, so a generator that crashed after printing the old text read as current, and one
that printed nothing read as "stale".

TWO PARTS, one protocol (check-example-lists-fixture.py's). Every case is a labelled check; a case is red when its
check returns something other than the value written for it.
  GENERATOR  a throwaway git repository built from CORPUS plus a case's edits (an index is all `git ls-files` needs),
             the generator run on it with --root. A failure case wants exit 2, an EMPTY stdout, and the problem
             lines it names.
  SECTION    the section is cut out of verify-docs.sh (from its `section "[HARD] llms.txt generates ...` line to the
             next `# =====` line) and run under the real section()/pass()/fail()/warn() definitions, in a temp root
             whose maintenance/scripts/generate-llms-txt.py is a STUB that prints what the case says (stdout,
             stderr, status). The first section case is a NEGATIVE CONTROL: a TRANSCRIPTION of the section as it stood at
             430bec9 (`generate | cmp`; its two messages are simplified, the logic is the same) must read a stub that crashes after printing the file's own text as PASS, and
             one that prints nothing as a WARN - or the run is refused, because a fixture that cannot see the
             defect certifies nothing.

`--mutations` copies the scripts and verify-docs.sh, reverts one guard at a time (in generate-llms-txt.py, or in the
section), runs every case against the copy, and requires the set of red labels to equal the one written beside the
mutation. A mutation whose text no longer occurs once in its target is stale and fails the run; the IDENTITY mutation
must leave nothing red.

PINS: one case is reddened by no mutation of a guard: the section's negative control, which is a control, not a guard. The
reordered-README case (G_REORDER) is reddened only by mutations that break every corpus (Home must be listed), and
'docs/index.md must be listed' reddens nearly every generator case, because Home becomes a problem in every corpus; its
red set is written as everything but the three cases that read no corpus.

Usage: python3 maintenance/scripts/generate-llms-txt-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, concurrent.futures, os, pathlib, re, shutil, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--from-dir', default=str(HERE))
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()
FROM = pathlib.Path(A.from_dir)
REPO = HERE.parents[1]
VERIFY = FROM / 'verify-docs.sh'
ANSI = re.compile(r'\x1b\[[0-9;]*m')

MIN_CASES = 76
MIN_MUTATIONS = 74
fails: list[str] = []
seen: list[str] = []

SITE = 'https://inkthorne.github.io/hytale-modding-handbook'
RAWPAT = 'https://raw.githubusercontent.com/inkthorne/hytale-modding-handbook/main/docs/<file>.md'


# ---- the corpus: two categories (README order is not alphabetical), four pages and Home, two examples -------------
def page(title='T', desc='D', body='Text.\n'):
    fm = '---\n' + (f'title: "{title}"\n' if title else '') + (f'description: "{desc}"\n' if desc else '') + '---\n\n'
    return fm + body


README = ('# R\n\n## Documentation\n\n### Zed\n\n- [B](./docs/b-page.md) - b\n- [A](./docs/a-page.md) - a\n\n'
          '### Aye\n\n- [C](./docs/c-page.md) - c\n\n## Examples\n\nSee below.\n')
TABLE = ('| Example | Type | What it demonstrates | Commands |\n|---|---|---|---|\n'
         '| [plugy/](./plugy/) | Plugin | The plugin way | `/x` |\n'
         '| [packx/](./packx/) | Pack | The pack way | — |\n')
CORPUS = {
    'README.md': README,
    'docs/index.md': ('---\ntitle: Home\ndescription: "Start page"\n---\n\n# Home\n\n'
                      '**Verified against Hytale 1.2.3 (build-9).** Each page carries a stamp.\n'),
    'docs/b-page.md': page('Bee', 'The b page'),
    'docs/a-page.md': page('Ay', 'The a page', 'It says Verified against 0.1 about something else.\n'),
    'docs/c-page.md': page('Cee', 'The c page'),
    'examples/README.md': '# Examples\n\n' + TABLE + '\nNotes.\n',
    'examples/plugy/README.md': '# P\n',
    'examples/plugy/Foo.java': 'class Foo {}\n',
    'examples/packx/README.md': '# P\n',
    'examples/packx/x.json': '{}\n',
    'examples/hytale-paths.sh': '#!/bin/sh\n',
}
def fm_page(*lines):
    return '---\n' + '\n'.join(lines) + '\n---\n\nText.\n'


NEWDIR = {'examples/newz/README.md': '# N\n', 'examples/newz/y.json': '{}\n'}
ROW_NEWZ = '| [newz/](./newz/) | Pack | A third example | — |\n'


def gen(edits=None, untracked=(), git=True):
    """Build the corpus with `edits` (path -> text, or None to delete), `git add` it, run the generator.
    -> (rc, stdout, [stderr lines])."""
    files = dict(CORPUS)
    for k, v in (edits or {}).items():
        if v is None:
            files.pop(k, None)
        else:
            files[k] = v
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        for rel, body in files.items():
            f = tmp / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body)
        if git:
            subprocess.run(['git', 'init', '-q', str(tmp)], check=True)
            subprocess.run(['git', '-C', str(tmp), 'add', '-A'], check=True)
            for u in untracked:
                subprocess.run(['git', '-C', str(tmp), 'rm', '-q', '--cached', u], check=True)
        p = subprocess.run([sys.executable, str(FROM / 'generate-llms-txt.py'), '--root', str(tmp)],
                           capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return p.returncode, p.stdout, p.stderr.split('\n')


def problems(edits=None, **kw):
    """-> (rc, stdout is empty, the problem lines, the closing summary line dropped). A healthy run gives (0, False, [])."""
    rc, out, err = gen(edits, **kw)
    bad = [l.strip()[6:] for l in err if l.strip().startswith('FAIL') and 'was not generated' not in l]
    return rc, out == '', bad


def only(edits=None, **kw):
    """-> the problem lines of a run that must have failed with exit 2 and an empty stdout, else the (rc, empty) pair."""
    rc, empty, bad = problems(edits, **kw)
    return sorted(bad) if (rc, empty) == (2, True) else (rc, empty, bad)


def headings(out):
    return [l[3:] for l in out.split('\n') if l.startswith('## ')]


def links(out, under):
    """The `- [text](url)` lines of one `## ` section."""
    sect, got = None, []
    for l in out.split('\n'):
        if l.startswith('## '):
            sect = l[3:]
        elif sect == under and l.startswith('- ['):
            got.append(l)
    return got


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


# ---- the section, run as text --------------------------------------------------------------------------------
ANCHOR = 'section "[HARD] llms.txt generates, and docs/llms.txt is current"'
OLD_SECTION = '''section "[ADVISORY] llms.txt is current"
if [ -f docs/llms.txt ]; then
  if ./maintenance/scripts/generate-llms-txt.sh | cmp -s - docs/llms.txt; then
    pass "docs/llms.txt matches a fresh regeneration"
  else
    warn "docs/llms.txt is stale - regenerate"
  fi
else
  warn "docs/llms.txt missing - generate"
fi
'''


def section_text() -> str:
    src = VERIFY.read_text()
    n = src.count(ANCHOR)
    if n != 1:
        raise SystemExit(f'FAIL  {ANCHOR!r} occurs {n} time(s) in verify-docs.sh, not once - the section was renamed or '
                         f'duplicated; move this anchor with it')
    s = src.index(ANCHOR)
    return src[s:src.index('\n# =====', s)] + '\n'


def prelude() -> str:
    """`set -u` and the real HARD_FAILS/section/pass/fail/warn/info definitions of verify-docs.sh, verbatim."""
    v = VERIFY.read_text()
    a = v.index('\nHARD_FAILS=0\n') + 1
    i = v.index('\ninfo()', a) + 1
    return 'set -u\n' + v[a:v.index('\n', i) + 1]


STUB = ('import sys\nsys.stdout.write({out!r})\nsys.stderr.write({err!r})\nopen("ran", "a").write("x")\nsys.exit({rc})\n')
LINK = lambda n: f'- [P{n}]({SITE}/p{n}.html): d\n'
EXL = lambda d: f'- [{d}/](https://github.com/inkthorne/hytale-modding-handbook/tree/main/examples/{d}/): Pack. x\n'
GOOD_OUT = ('# H\n\n## Start here\n\n' + LINK(1) + '\n## Cat\n\n' + LINK(2) + LINK(3) + '\n## Examples\n\n' + EXL('e1') + EXL('e2')
            + '\n## Source\n\n- [GitHub repository](https://github.com/inkthorne/hytale-modding-handbook): z\n')
GOOD_ERR = 'LLMS 1 categories, 3 pages, 2 examples\n'


def run_section(text, *, out=GOOD_OUT, err=GOOD_ERR, rc=0, llms='same', docs=3, tmpdir='ok', stub_name='generate-llms-txt.py',
                tracked=2, git=True, dirmd=False):
    """-> (exit status, [output lines, ANSI dropped], temp entries left, whether the stub ran, HARD_FAILS)."""
    root = pathlib.Path(tempfile.mkdtemp())
    tmp = root / 'tmp'
    try:
        tmp.mkdir()
        (root / 'maintenance/scripts').mkdir(parents=True)
        (root / 'maintenance/scripts' / stub_name).write_text(STUB.format(out=out, err=err, rc=rc))
        (root / 'docs').mkdir()
        for i in range(docs):
            (root / 'docs' / f'p{i + 1}.md').write_text('x\n')
        (root / 'docs/sub').mkdir()
        (root / 'docs/sub/ignored.md').write_text('x\n')
        if dirmd:
            (root / 'docs/dir.md').mkdir()
        for i in range(tracked):
            (root / 'examples' / f'e{i + 1}').mkdir(parents=True)
            (root / 'examples' / f'e{i + 1}' / 'README.md').write_text('x\n')
        (root / 'examples').mkdir(exist_ok=True)
        (root / 'examples/hytale-paths.sh').write_text('x\n')
        if git:
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
        if llms == 'same':
            (root / 'docs/llms.txt').write_text(out)
        elif llms == 'other':
            (root / 'docs/llms.txt').write_text(out + 'an old line\n')
        script = prelude() + text + 'echo "HARD_FAILS=$HARD_FAILS"\n'
        tdir = {'ok': str(tmp), 'gone': str(root / 'nonexistent')}[tmpdir]
        p = subprocess.run(['bash', '-c', script], capture_output=True, text=True, cwd=root,
                           env=dict(os.environ, TMPDIR=tdir, PYTHONDONTWRITEBYTECODE='1'))
        o = ANSI.sub('', p.stdout + p.stderr)
        lines = [l.strip() for l in o.splitlines() if l.strip() and not l.startswith('== ')]
        hf = int(re.findall(r'^HARD_FAILS=(\d+)$', o, re.M)[-1])
        lines = [l for l in lines if not l.startswith('HARD_FAILS=')]
        return p.returncode, lines, len(list(tmp.iterdir())), (root / 'ran').exists(), hf
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- labels ------------------------------------------------------------------------------------------------
G_HEALTHY = 'GENERATOR a healthy corpus generates, exit 0, and says "LLMS 2 categories, 4 pages, 2 examples" on stderr'
G_GROUPS = 'the sections are Start here, the README categories in README order, Examples, Source'
G_ORDER = 'pages come in README order inside a category (not alphabetical), and Home is the only entry under Start here'
G_REORDER = 'a README with its categories and pages reordered moves them in the output'
G_LINKS = 'every page link is the rendered .html page on the site, the examples link tree/main/examples/<d>/'
G_RAWLINE = 'the markdown source pattern is given once, in one line, and no page links to raw markdown'
G_TITLE = 'a link is titled with the page title and followed by its description'
G_STAMP = "the build is Home's Verified-against paragraph, not a `Verified against N` in another page's prose"
G_STAMP0 = 'Home without the Verified-against paragraph exits 2, naming it'
G_STAMP2 = 'Home with the paragraph twice exits 2, naming the count'
G_NOCAT = 'a README with no categories exits 2'
G_UNLISTED = 'a docs page that no category lists exits 2, naming the page'
G_INDEX_OK = 'docs/index.md is in no README category and that is no problem'
G_TWICE = 'a page listed in two categories exits 2, naming it'
G_MISSINGFILE = 'a README link whose page does not exist exits 2, naming it'
G_NOFM = 'a listed page without frontmatter exits 2, naming it'
G_NOTITLE = 'a listed page without a title exits 2, naming it'
G_NODESC = 'a listed page without a description exits 2, naming it'
G_HOMEDESC = "Home without a description exits 2 (it is an entry like any other)"
G_ALLPROBLEMS = 'every problem is listed, not only the first'
G_EMPTY = 'an empty `title:` or `description:` is empty, not the next frontmatter line: exit 2 naming the missing field'
G_Y_CONT = 'a title or description that goes on on the next, indented line exits 2, naming the form'
G_Y_IND = 'a block scalar (> |), anchor (&), alias (*) or tag (!) as a title or description exits 2, naming the form'
G_Y_FLOW = 'a flow collection ([ {) as a description exits 2, naming the form'
G_Y_DQ = 'a double-quoted value with an escape or an inner quote exits 2, naming the form'
G_Y_SQ = 'a single-quoted value with a doubled quote exits 2, naming the form'
G_Y_UNCLOSED = 'a quote that does not close exits 2, naming the form'
G_Y_COMMENT = 'a plain value with a trailing " #" comment exits 2, naming the form'
G_Y_COLON = "a plain value holding ': ' exits 2, naming the form"
G_Y_OK = "plain and quoted one-line values with # and : inside them (C#, a:b, \"x # y: z\") are read as written"
G_SUB = 'a row whose link goes below an example directory (./plugy/sub/) exits 2, naming the line'
G_FRAGENC = 'a fragment and a %-encoded destination in a row still name the directory'
G_NONASCII = 'an example directory with a non-ASCII name is read and listed (git ls-files -z)'
G_HEADER = 'an examples table whose header row is not exactly the expected one exits 2'
G_HEADER2 = 'a header row that occurs twice exits 2'
G_SEP = 'a header row not followed by its separator row exits 2'
G_NOROW = 'an example directory with no row exits 2, naming it'
G_GHOSTROW = 'a row whose link is not a tracked example directory exits 2, naming the line'
G_NOLINK = 'a row with no link in its first cell exits 2'
G_CELLS = 'a row that is not four cells exits 2'
G_DUPROW = 'a second row for one directory exits 2, naming both lines'
G_BADTYPE = 'a Type other than Pack or Plugin exits 2, naming it'
G_EMPTYWHAT = 'an empty "What it demonstrates" cell exits 2'
G_PIPE = 'an escaped \\| inside a cell does not split it: the Commands cell is whole, and a \\| in the description shows as |'
G_KEYED = 'rows are keyed by the link destination, not by position: reordered rows keep their own Type'
G_TABLEORDER = "the examples come in the table's order, not sorted"
G_NEWDIR = 'a third tracked example directory with a row appears in the output and the count'
G_UNTRACKED = 'an untracked directory with no row is no example and no problem'
G_ZERO = '0 tracked example directories exits 2, saying so'
G_NOGIT = 'a tree that is not a git work tree exits 2, naming git'
G_NOEXREADME = 'no examples/README.md exits 2'
G_STDOUT = 'a failing run writes nothing to stdout'
G_REAL = "the real tree: docs/llms.txt equals this generator's output"
S_NEG = 'SECTION NEGATIVE CONTROL: the section as it stood (generate | cmp) reads a crashed generator as current, and an empty one as stale'
S_HEALTHY = "a healthy run PASSes, with the generator's three figures and the counts made from the output in the line, HARD_FAILS 0"
S_RC = 'a generator that exits non-zero FAILs, naming the status and its stderr, even if its stdout equals the file'
S_EMPTY = 'a generator that exits 0 and writes nothing FAILs, saying so'
S_NOMARK = "a generator that prints no 'LLMS ...' denominator line FAILs"
S_TWO = "a generator that prints two 'LLMS ...' lines FAILs (the section used to error and PASS)"
S_MALFORMED = "an 'LLMS' line whose figures are not digits FAILs, quoting it"
S_MARKBAD = 'a pages figure that disagrees with the distinct page links in the output FAILs, naming both'
S_DUPPAGE = 'a page linked twice counts once: 3 links to 2 pages FAIL against the figure and against docs/'
S_FEWER = 'fewer distinct page links than docs/*.md files FAILs (and a .md in a subdirectory of docs/ is not counted)'
S_MORE = 'more distinct page links than docs/*.md files FAILs too: equal, not at least'
S_DIRMD = 'a directory named like a markdown file in docs/ is not a docs page'
S_EXBAD = 'an examples figure that disagrees with the distinct example tree links in the output FAILs, naming both'
S_EXDUP = 'an example linked twice counts once'
S_EXTRACKED = 'example links that are not the tracked top-level directories of examples/ FAIL, naming both counts'
S_GITFAIL = 'a git ls-files that fails FAILs, naming its status, and the example counts are not compared'
S_CATBAD = "a categories figure that disagrees with the output's headings (less Start here, Examples, Source) FAILs, naming both"
S_STALE = 'an output that differs from docs/llms.txt is a WARN with the regenerate command, not a FAIL, and no PASS'
S_MISSING = 'a missing docs/llms.txt is a WARN naming the command'
S_CLEAN = 'the temp dir is removed on the pass path and on the failure path'
S_MKTEMP = 'a mktemp that fails FAILs, naming it, and the generator is not run'
S_STATIC = 'the section holds no trap and no exit outside a comment (the asset-drift section owns the only EXIT hook)'
S_ALLCASES = 'ALL_CASES lists exactly the labels the fixture checks'

GEN_CASES = {G_HEALTHY, G_GROUPS, G_ORDER, G_REORDER, G_LINKS, G_RAWLINE, G_TITLE, G_STAMP, G_STAMP0, G_STAMP2, G_NOCAT,
             G_UNLISTED, G_INDEX_OK, G_TWICE, G_MISSINGFILE, G_NOFM, G_NOTITLE, G_NODESC, G_HOMEDESC, G_ALLPROBLEMS,
             G_EMPTY, G_Y_CONT, G_Y_IND, G_Y_FLOW, G_Y_DQ, G_Y_SQ, G_Y_UNCLOSED, G_Y_COMMENT, G_Y_COLON, G_Y_OK, G_SUB, G_FRAGENC,
             G_NONASCII, G_HEADER, G_HEADER2, G_SEP, G_NOROW, G_GHOSTROW, G_NOLINK, G_CELLS, G_DUPROW, G_BADTYPE, G_EMPTYWHAT, G_PIPE,
             G_KEYED, G_TABLEORDER, G_NEWDIR, G_UNTRACKED, G_ZERO, G_NOGIT, G_NOEXREADME, G_STDOUT, G_REAL}
SEC_CASES = {S_NEG, S_HEALTHY, S_RC, S_EMPTY, S_NOMARK, S_TWO, S_MALFORMED, S_MARKBAD, S_DUPPAGE, S_FEWER, S_MORE, S_DIRMD, S_EXBAD, S_EXDUP, S_EXTRACKED, S_GITFAIL, S_CATBAD, S_STALE, S_MISSING, S_CLEAN, S_MKTEMP, S_STATIC, S_ALLCASES}
ALL_CASES = GEN_CASES | SEC_CASES
# the cases that expect a failing generator: a mutation that lets a problem through reddens the ones it hides
FAIL_CASES = {G_EMPTY, G_Y_CONT, G_Y_IND, G_Y_FLOW, G_Y_DQ, G_Y_SQ, G_Y_UNCLOSED, G_Y_COMMENT, G_Y_COLON, G_SUB, G_NOCAT, G_UNLISTED, G_TWICE, G_MISSINGFILE, G_NOFM, G_NOTITLE, G_NODESC, G_HOMEDESC, G_STAMP0, G_STAMP2,
              G_ALLPROBLEMS, G_HEADER, G_HEADER2, G_SEP, G_NOROW, G_GHOSTROW, G_NOLINK, G_CELLS, G_DUPROW, G_BADTYPE,
              G_EMPTYWHAT, G_ZERO, G_NOGIT, G_NOEXREADME, G_STDOUT}

# ---- the mutations -----------------------------------------------------------------------------------------
if A.mutations:
    GEN = 'generate-llms-txt.py'
    SEC = 'verify-docs.sh'
    # Each entry: the text of the target that occurs exactly once, its replacement, the EXACT set of case labels the edit must
    # redden, and the target (default generate-llms-txt.py).
    MUTATIONS = {
        'IDENTITY (no change, the harness control)': (
            '#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity)', set()),
        # ---- generate-llms-txt.py: the exit guards
        'no categories is not a problem': (
            "    if not cats:\n        problems.append('README.md lists no categories", "    if False:\n        problems.append('README.md lists no categories",
            {G_NOCAT}),
        "generate-site-nav's problems (a missing page, a page listed twice) are dropped": (
            "    problems += NAV.generate(root)[3]", "    pass",
            {G_TWICE, G_MISSINGFILE}),
        'a docs page in no category is not a problem': (
            "        if p != 'index.md' and p not in listed:\n            problems.append(", "        if False:\n            problems.append(",
            {G_UNLISTED}),
        'docs/index.md must be listed in a category like any page': (
            "        if p != 'index.md' and p not in listed:", "        if p not in listed:",
            # Home is a problem in every corpus, so each case that reads a corpus changes its problem list; three read
            # nothing the problem could join: no categories (it asks only for the first), no git, and stdout alone
            GEN_CASES - {G_NOCAT, G_NOGIT, G_STDOUT}),
        'a missing stamp is not a problem': (
            '    if len(found) == 0:\n        problems.append(', '    if False:\n        problems.append(',
            {G_STAMP0}),
        'a repeated stamp is not a problem': (
            '    if len(found) > 1:\n        problems.append(', '    if False:\n        problems.append(',
            {G_STAMP2}),
        'a page without frontmatter is not a problem': (
            "        problems.append(f'docs/{page} has no frontmatter, so no title and no description')\n        return None",
            "        return None",
            {G_NOFM}),
        'a page without a title is listed': (
            "    if not title and not t_refused:\n        problems.append(", "    if False:\n        problems.append(",
            {G_NOTITLE, G_ALLPROBLEMS, G_EMPTY}),
        'a page without a description is listed': (
            "    if not desc and not d_refused:\n        problems.append(", "    if False:\n        problems.append(",
            {G_NODESC, G_HOMEDESC, G_EMPTY}),
        'only the first problem is reported': (
            "        for p in problems:\n            print(f'  FAIL  {p}', file=sys.stderr)",
            "        for p in problems[:1]:\n            print(f'  FAIL  {p}', file=sys.stderr)",
            # a row that fails leaves its directory without a row too: those two cases list two problems
            {G_ALLPROBLEMS, G_CELLS, G_NOLINK, G_EMPTY}),
        'problems do not stop the run': (
            "    text, ncat, npages, nex, problems = generate(root)\n    if problems:",
            "    text, ncat, npages, nex, problems = generate(root)\n    if False:",
            FAIL_CASES),
        'a failing run writes its text to stdout before it stops': (
            "    if problems:\n        for p in problems:",
            "    if problems:\n        sys.stdout.write('#')\n        for p in problems:",
            FAIL_CASES),
        # ---- frontmatter forms
        'an empty value reads the next frontmatter line': (
            "    elif not v:\n        return None, False", "    elif not v:\n        return (lines[at + 1].strip() or None), False",
            {G_EMPTY}),
        'a value that goes on on the next line is read': (
            "    elif cont:\n", "    elif False:\n",
            {G_Y_CONT}),
        'a block scalar, anchor, alias or tag is read': (
            "    if v and v[0] in '>|&*!':", "    if False:",
            {G_Y_IND}),
        'a flow collection is read': (
            "    elif v[0] in '[{':", "    elif False:",
            {G_Y_FLOW}),
        'a quote that does not close is read': (
            "        if len(v) < 2 or v[-1] != v[0]:", "        if False:",
            {G_Y_UNCLOSED}),
        'a double-quoted escape is read': (
            "        elif v[0] == '\"' and ('\\\\' in inner or '\"' in inner):", "        elif False:",
            {G_Y_DQ}),
        'a single-quoted doubled quote is read': (
            "        elif v[0] == \"'\" and \"'\" in inner:", "        elif False:",
            {G_Y_SQ}),
        'a trailing comment is read': (
            "    elif re.search(r'\\s#', v):", "    elif False:",
            {G_Y_COMMENT}),
        "a ': ' in a plain value is read": (
            "    elif ': ' in v:", "    elif False:",
            {G_Y_COLON}),
        'a # with no space before it is a comment': (
            "    elif re.search(r'\\s#', v):", "    elif '#' in v:",
            {G_Y_OK}),
        "a ':' with no space after it is a mapping": (
            "    elif ': ' in v:", "    elif ':' in v:",
            {G_Y_OK}),
        'a refused value is also reported as missing': (
            "    return None, True\n", "    return None, False\n",
            {G_Y_CONT, G_Y_IND, G_Y_FLOW, G_Y_DQ, G_Y_SQ, G_Y_UNCLOSED, G_Y_COMMENT, G_Y_COLON}),
        # ---- the examples table
        'the header row is matched loosely': (
            "if l.rstrip() == HEADER]", "if l.startswith('| Example')]",
            {G_HEADER}),
        'a repeated header row is the first one': (
            "    if len(at) != 1:", "    if len(at) < 1:",
            {G_HEADER2}),
        'a missing separator row is not a problem': (
            "    if i >= len(lines) or not SEPARATOR.match(lines[i].strip()):", "    if False:",
            {G_SEP}),
        'a row that is not four cells is read': (
            "        if len(parts) != 6 or parts[0] != '' or parts[-1] != '':", "        if False:",
            {G_CELLS}),
        'a row with no link is read': (
            "        if not m:\n            problems.append(f'examples/README.md:{n + 1} has no link", "        if False:\n            problems.append(f'examples/README.md:{n + 1} has no link",
            {G_NOLINK}),
        'a row for something that is not an example directory is read': (
            "        if len(segs) != 2 or segs[0] != 'examples' or segs[1] not in pop:", "        if False:",
            {G_GHOSTROW, G_SUB}),
        'a second row for a directory is read': (
            "        if d in seen:\n            problems.append(", "        if False:\n            problems.append(",
            {G_DUPROW}),
        'any Type is accepted': (
            "        if cells[1] not in TYPES:", "        if False:",
            {G_BADTYPE}),
        'an empty description is accepted': (
            "        if not what:\n            problems.append(", "        if False:\n            problems.append(",
            {G_EMPTYWHAT}),
        'a directory with no row is not a problem': (
            "    for d in sorted(pop - set(seen)):\n        problems.append(", "    for d in sorted(pop - set(seen)):\n        pass  # (",
            {G_NOROW, G_CELLS, G_NOLINK}),
        'a missing examples/README.md is not a problem': (
            "    if not f.is_file():\n        problems.append('examples/README.md does not exist", "    if False:\n        problems.append('examples/README.md does not exist",
            {G_NOEXREADME}),
        '0 example directories is a clean run': (
            "    if not pop:\n        problems.append('0 example", "    if False:\n        problems.append('0 example",
            {G_ZERO}),
        'a git failure is not a problem': (
            "    if r.returncode != 0:\n        problems.append(", "    if False:\n        problems.append(",
            {G_NOGIT}),
        'untracked directories are examples': (
            "'ls-files', '-z', '--', 'examples/'", "'ls-files', '-z', '--cached', '--others', '--', 'examples/'",
            {G_UNTRACKED}),
        'cells are split on every |': (
            "re.split(r'(?<!\\\\)\\|', row)", "row.split('|')",
            {G_PIPE, G_REAL}),
        'an escaped | in a description stays escaped': (
            "cells[2].replace('\\\\|', '|')", "cells[2]",
            {G_PIPE}),
        'rows are keyed by position': (
            "        d = segs[1]\n", "        d = sorted(pop)[len(seen)] if len(seen) < len(pop) else segs[1]\n",
            {G_KEYED, G_DUPROW, G_NEWDIR, G_NOROW, G_LINKS, G_TABLEORDER, G_REAL, G_FRAGENC, G_NONASCII}),
        'a row below an example directory names the directory': (
            "        if len(segs) != 2 or segs[0] != 'examples' or segs[1] not in pop:", "        if segs[0] != 'examples' or segs[1] not in pop:",
            {G_SUB}),
        'a fragment stays on the destination': (
            "path = urllib.parse.unquote(m.group(1).partition('#')[0].partition('?')[0])", "path = urllib.parse.unquote(m.group(1))",
            {G_FRAGENC}),
        'a %-encoded destination is not decoded': (
            "path = urllib.parse.unquote(m.group(1).partition('#')[0].partition('?')[0])", "path = m.group(1).partition('#')[0].partition('?')[0]",
            {G_FRAGENC}),
        'git ls-files quotes a non-ASCII name': (
            "'ls-files', '-z', '--'", "'ls-files', '--'",
            {G_NONASCII}),
        # ---- the output
        "the examples are sorted, not in the table's order": (
            "for d, t, w in examples]))", "for d, t, w in sorted(examples)]))",
            {G_TABLEORDER, G_NEWDIR, G_PIPE, G_LINKS, G_KEYED, G_REAL, G_FRAGENC, G_NONASCII}),
        "the pages of a category are sorted, not in README order": (
            "        for _, page in pages:\n            e = page_entry(", "        for _, page in sorted(pages, key=lambda x: x[1]):\n            e = page_entry(",
            {G_ORDER, G_TITLE, G_LINKS, G_REAL}),
        'the categories are sorted, not in README order': (
            "    for cat, pages in cats:\n        items = []", "    for cat, pages in sorted(cats):\n        items = []",
            {G_GROUPS, G_REAL}),
        'the page links are the raw markdown files': (
            "{SITE}/{page[:-3]}.html", "{RAW}/{page[:-3]}.md",
            {G_LINKS, G_RAWLINE, G_TITLE, G_REAL, G_Y_OK}),
        'the denominator line is not printed': (
            "    print(f'LLMS {ncat} categories, {npages} pages, {nex} examples', file=sys.stderr)", "    pass",
            {G_HEALTHY, G_NEWDIR, G_UNTRACKED}),
        "the build is read from every page's prose before Home's paragraph": (
            "    found = STAMP.findall(index.read_text()) if index.is_file() else []",
            "    found = [m for f in (root / 'docs').glob('*.md') for m in re.findall(r'Verified against ([0-9]+(?:\\.[0-9]+)*)()', f.read_text())] or (STAMP.findall(index.read_text()) if index.is_file() else [])",
            {G_STAMP, G_STAMP0, G_STAMP2, G_REAL}),
        # ---- verify-docs.sh: the section
        'the section reads cmp\'s status, not the generator\'s': (
            '  if [ "$LLMS_RC" -ne 0 ]; then', '  if false; then',
            {S_RC}, SEC),
        'empty output is not a failure of its own': (
            '  elif [ ! -s "$LLMS_TMP/out" ]; then', '  elif false; then',
            {S_EMPTY}, SEC),
        'a missing or repeated LLMS line is not a failure': (
            '  elif [ "$LLMS_NLINES" -ne 1 ]; then', '  elif false; then',
            {S_NOMARK, S_TWO}, SEC),
        'an LLMS line that is not digits is not a failure': (
            '  elif [ -z "$LLMS_FIELDS" ]; then', '  elif false; then',
            {S_MALFORMED}, SEC),
        'a pages figure that disagrees with the output is not a failure': (
            '    if [ "$LLMS_MP" -ne "$LLMS_N" ]; then', '    if false; then',
            {S_MARKBAD, S_DUPPAGE}, SEC),
        'page links are not compared with the docs files': (
            '    if [ "$LLMS_N" -ne "$LLMS_DOCS" ]; then', '    if false; then',
            {S_FEWER, S_MORE, S_DUPPAGE}, SEC),
        'at least as many page links as docs files is enough': (
            '    if [ "$LLMS_N" -ne "$LLMS_DOCS" ]; then', '    if [ "$LLMS_N" -lt "$LLMS_DOCS" ]; then',
            {S_MORE}, SEC),
        'page links are counted with repeats': (
            "\\1/p' \"$LLMS_TMP/out\" | sort -u | wc -l", "\\1/p' \"$LLMS_TMP/out\" | wc -l",
            {S_DUPPAGE}, SEC),
        'docs files are counted below docs/ too': (
            "find docs -maxdepth 1 -type f -name '*.md'", "find docs -type f -name '*.md'",
            # only the paths that get as far as the count: the failures before it never read it
            {S_CATBAD, S_DIRMD, S_GITFAIL, S_HEALTHY, S_MISSING, S_DUPPAGE, S_MARKBAD, S_EXDUP, S_EXBAD, S_STALE, S_EXTRACKED, S_FEWER,
             S_MORE}, SEC),
        'a directory named like a markdown file is a docs page': (
            "find docs -maxdepth 1 -type f -name '*.md'", "find docs -maxdepth 1 -name '*.md'",
            {S_DIRMD}, SEC),
        'an examples figure that disagrees with the output is not a failure': (
            '    if [ "$LLMS_ME" -ne "$LLMS_X" ]; then', '    if false; then',
            {S_EXBAD, S_EXDUP}, SEC),
        'example links are counted with repeats': (
            "[^/)]+/\\)' \"$LLMS_TMP/out\" | sort -u | wc -l", "[^/)]+/\\)' \"$LLMS_TMP/out\" | wc -l",
            {S_EXDUP}, SEC),
        'example links are not compared with the tracked directories': (
            '    elif [ "$LLMS_X" -ne "$LLMS_T" ]; then', '    elif false; then',
            {S_EXTRACKED, S_EXDUP}, SEC),
        'a failing git ls-files is not a failure of its own': (
            '    if [ "$LLMS_GITRC" -ne 0 ]; then', '    if false; then',
            {S_GITFAIL}, SEC),
        'a categories figure that disagrees with the headings is not a failure': (
            '    if [ "$LLMS_MC" -ne "$LLMS_C" ]; then', '    if false; then',
            {S_CATBAD}, SEC),
        'a differing file is a PASS': (
            '      elif cmp -s "$LLMS_TMP/out" docs/llms.txt; then', '      elif true; then',
            {S_STALE}, SEC),
        'a differing file is a FAIL': (
            '        warn "docs/llms.txt is stale', '        fail "docs/llms.txt is stale',
            {S_STALE}, SEC),
        'a missing docs/llms.txt is passed': (
            '      if [ ! -f docs/llms.txt ]; then\n        warn "docs/llms.txt missing', '      if false; then\n        warn "docs/llms.txt missing',
            {S_MISSING}, SEC),
        'the temp dir is left behind': (
            '  rm -rf "$LLMS_TMP"\n', '  true\n',
            {S_CLEAN}, SEC),
        'a failed mktemp is not a failure': (
            'if [ -z "$LLMS_TMP" ] || [ ! -d "$LLMS_TMP" ]; then', 'if false; then',
            {S_MKTEMP}, SEC),
        'the section sets its own EXIT hook': (
            '  rm -rf "$LLMS_TMP"\n', "  rm -rf \"$LLMS_TMP\"\n  trap 'true' EXIT\n",
            {S_STATIC}, SEC),
        'the counts are not in the PASS line': (
            '"llms.txt generates ($LLMS_LINE; $LLMS_N of $LLMS_DOCS docs pages and $LLMS_X of $LLMS_T example directories linked, each figure counted from the output) and docs/llms.txt matches it"',
            '"llms.txt generates and docs/llms.txt matches it"',
            {S_HEALTHY, S_DIRMD}, SEC),
    }
    print(f'MUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
    if len(MUTATIONS) < MIN_MUTATIONS:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s), floor {MIN_MUTATIONS}')
        sys.exit(1)
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control')
        sys.exit(1)

    def one(item):
        label, (old, new, expect, *rest) = item
        target = rest[0] if rest else GEN
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            for f in list(HERE.glob('*.py')) + [HERE / 'verify-docs.sh']:
                shutil.copy2(f, tmp / f.name)
            body = (tmp / target).read_text()
            if body.count(old) != 1:
                return label, None, f'text occurs {body.count(old)}x in {target}, wanted 1: the mutation is stale and measured nothing'
            (tmp / target).write_text(body.replace(old, new, 1))
            r = subprocess.run([sys.executable, str(HERE / pathlib.Path(__file__).name), '--from-dir', str(tmp)],
                               capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            out = r.stdout + r.stderr
            ran = re.search(r'^FIXTURE (\d+) check\(s\)', out, re.M)
            tail = ' | '.join(out.strip().split('\n')[-3:])
            if ran is None or int(ran.group(1)) < MIN_CASES:
                return label, None, (f'the run printed no "FIXTURE N check(s)" line with N >= {MIN_CASES} (exit {r.returncode}), so it did not '
                                     f'run its cases and its red set says nothing: {tail}')
            if label.startswith('IDENTITY') and r.returncode != 0:
                return label, None, f'the IDENTITY run exited {r.returncode}, not 0: {tail}'
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

# ---- generator cases ---------------------------------------------------------------------------------------
_rc, _out, _err = gen()
check(G_HEALTHY, lambda: (_rc, [l for l in _err if l]), (0, ['LLMS 2 categories, 4 pages, 2 examples']))
check(G_GROUPS, lambda: headings(_out), ['Start here', 'Zed', 'Aye', 'Examples', 'Source'])
check(G_ORDER, lambda: ([re.search(r'\[(.*?)\]', l).group(1) for l in links(_out, 'Zed') + links(_out, 'Aye')],
                        [re.search(r'\[(.*?)\]', l).group(1) for l in links(_out, 'Start here')]),
      (['Bee', 'Ay', 'Cee'], ['Home']))
_RE = README.replace('### Zed\n\n- [B](./docs/b-page.md) - b\n- [A](./docs/a-page.md) - a\n\n### Aye\n\n- [C](./docs/c-page.md) - c\n',
                     '### Aye\n\n- [C](./docs/c-page.md) - c\n\n### Zed\n\n- [A](./docs/a-page.md) - a\n- [B](./docs/b-page.md) - b\n')
check(G_REORDER, lambda: (lambda o: (headings(o)[1:3], [re.search(r'\[(.*?)\]', l).group(1) for l in links(o, 'Zed')]))(
    gen({'README.md': _RE})[1]), (['Aye', 'Zed'], ['Ay', 'Bee']))
check(G_LINKS, lambda: ([re.search(r'\]\((.*?)\)', l).group(1) for l in links(_out, 'Zed') + links(_out, 'Start here')],
                        [re.search(r'\]\((.*?)\)', l).group(1) for l in links(_out, 'Examples')]),
      ([f'{SITE}/b-page.html', f'{SITE}/a-page.html', f'{SITE}/index.html'],
       ['https://github.com/inkthorne/hytale-modding-handbook/tree/main/examples/plugy/',
        'https://github.com/inkthorne/hytale-modding-handbook/tree/main/examples/packx/']))
check(G_RAWLINE, lambda: ([l for l in _out.split('\n') if 'raw.githubusercontent.com' in l and l.startswith('- [')],
                          len([l for l in _out.split('\n') if 'raw.githubusercontent.com' in l]),
                          [l for l in _out.split('\n') if RAWPAT in l][0].startswith('The links below are the rendered pages.')),
      ([], 1, True))
check(G_TITLE, lambda: links(_out, 'Zed')[0], f'- [Bee]({SITE}/b-page.html): The b page')
check(G_STAMP, lambda: ('Hytale 1.2.3 (build-9)' in _out, '0.1' in _out), (True, False))
_NOSTAMP = CORPUS['docs/index.md'].replace('**Verified against Hytale 1.2.3 (build-9).**', 'Verified against Hytale 1.2.3.')
check(G_STAMP0, lambda: only({'docs/index.md': _NOSTAMP}),
      ['docs/index.md has no `**Verified against Hytale X (build-N).**` paragraph'])
check(G_STAMP2, lambda: only({'docs/index.md': CORPUS['docs/index.md'] + '\n**Verified against Hytale 1.2.3 (build-9).**\n'}),
      ['docs/index.md has 2 `**Verified against Hytale X (build-N).**` paragraphs, wanted 1'])
check(G_NOCAT, lambda: only({'README.md': '# R\n\n## Documentation\n\nNothing grouped.\n'})[0],
      'README.md lists no categories under `## Documentation`')
check(G_UNLISTED, lambda: only({'docs/zzz.md': page()}), ['docs/zzz.md is listed in no README category, so in no group'])
check(G_INDEX_OK, lambda: (_rc, 'docs/index.md' in ''.join(_err)), (0, False))
check(G_TWICE, lambda: only({'README.md': README.replace('- [C](./docs/c-page.md) - c\n', '- [C](./docs/c-page.md) - c\n- [A](./docs/a-page.md)\n')}),
      ["a-page.md is listed twice in README (under 'Zed' and 'Aye')"])
check(G_MISSINGFILE, lambda: only({'docs/c-page.md': None}),
      ["README lists c-page.md under 'Aye', and docs/c-page.md does not exist"])
check(G_NOFM, lambda: only({'docs/a-page.md': 'No frontmatter.\n'}), ['docs/a-page.md has no frontmatter, so no title and no description'])
check(G_NOTITLE, lambda: only({'docs/a-page.md': page(title='')}), ['docs/a-page.md has no frontmatter title'])
check(G_NODESC, lambda: only({'docs/a-page.md': page(desc='')}), ['docs/a-page.md has no frontmatter description'])
check(G_HOMEDESC, lambda: only({'docs/index.md': CORPUS['docs/index.md'].replace('description: "Start page"\n', '')}),
      ['docs/index.md has no frontmatter description'])
check(G_ALLPROBLEMS, lambda: only({'docs/a-page.md': page(title=''), 'docs/c-page.md': page(title='')}),
      ['docs/a-page.md has no frontmatter title', 'docs/c-page.md has no frontmatter title'])

# ---- frontmatter forms --------------------------------------------------------------------------------------
def fm_problems(**fields):
    """a-page's frontmatter with `fields` (key -> raw text after `key:`); -> the problems, cut at the shared explanation."""
    r = only({'docs/a-page.md': fm_page(*[f'{k}:{v}' for k, v in fields.items()])})
    return [b.split(': this reader')[0] for b in r] if isinstance(r, list) else r


_A = 'docs/a-page.md frontmatter'
check(G_EMPTY, lambda: only({'docs/a-page.md': fm_page('title:', 'description: "D"', 'seo:', '  type: X'),
                             'docs/c-page.md': fm_page('title: "C"', 'description:', 'seo:', '  type: X')}),
      ['docs/a-page.md has no frontmatter title', 'docs/c-page.md has no frontmatter description'])
check(G_Y_CONT, lambda: [fm_problems(title=' "T"', description=' folded text\n  second line'),
                         fm_problems(title=' "T"', description='\n  indented on the next line')],
      [[f'{_A} description goes on on the next line']] * 2)
check(G_Y_IND, lambda: [fm_problems(title=' "T"', description=' ' + v) for v in ('>-\n  text', '| \n  text', '&anchor text', '*alias', '!!str text')]
                       + [fm_problems(title=' >', description=' "D"')],
      [[f"{_A} description starts with {c!r} (a block scalar, anchor, alias or tag)"] for c in '>|&*!'] +
      [[f"{_A} title starts with '>' (a block scalar, anchor, alias or tag)"]])
check(G_Y_FLOW, lambda: [fm_problems(title=' "T"', description=' [a, b]'), fm_problems(title=' "T"', description=' {a: b}')],
      [[f'{_A} description is a flow collection']] * 2)
check(G_Y_DQ, lambda: [fm_problems(title=' "T"', description=' "Say \\"hi\\" now"'), fm_problems(title=' "T"', description=' "a\\nb"'),
                       fm_problems(title=' "T"', description=' "say "hi" now"')],
      [[f'{_A} description is double-quoted with an escape']] * 3)
check(G_Y_SQ, lambda: fm_problems(title=' "T"', description=" 'It''s a page'"), [f'{_A} description is single-quoted with a doubled quote'])
check(G_Y_UNCLOSED, lambda: [fm_problems(title=' "T"', description=' "never closed'), fm_problems(title=' "T"', description=' "')],
      [[f'{_A} description has a quote that does not close']] * 2)
check(G_Y_COMMENT, lambda: fm_problems(title=' "T"', description=' Plain text # a comment'), [f'{_A} description has a trailing comment'])
check(G_Y_COLON, lambda: fm_problems(title=' "T"', description=' Plain: text'), [f"{_A} description has ': ' in a plain value"])
_ok = gen({'docs/a-page.md': fm_page('title: C# and a:b', 'description: "Use # and: here"'),
           'docs/c-page.md': fm_page("title: 'Single # q'", "description: 'single # and: here'")})
check(G_Y_OK, lambda: (_ok[0], [l for l in links(_ok[1], 'Zed') + links(_ok[1], 'Aye') if 'a-page' in l or 'c-page' in l]),
      (0, [f'- [C# and a:b]({SITE}/a-page.html): Use # and: here', f"- [Single # q]({SITE}/c-page.html): single # and: here"]))

# ---- the examples table ------------------------------------------------------------------------------------
def with_table(t, tail='\nNotes.\n'):
    return {'examples/README.md': '# Examples\n\n' + t + tail}


check(G_SUB, lambda: only(with_table(TABLE + '| [sub/](./plugy/sub/) | Plugin | x | \u2014 |\n')),
      ['examples/README.md:7 links ./plugy/sub/, which is not an example directory'])
_fe = gen(with_table(TABLE.replace('(./plugy/)', '(./plugy/#top)').replace('(./packx/)', '(./pa%63kx/)')))
check(G_FRAGENC, lambda: (_fe[0], [re.search(r'\[(.*?)/\]', l).group(1) for l in links(_fe[1], 'Examples')]), (0, ['plugy', 'packx']))
_na = gen({'examples/caf\u00e9/README.md': '# C\n', 'examples/README.md': '# Examples\n\n' + TABLE + '| [caf\u00e9/](./caf\u00e9/) | Pack | Accented | \u2014 |\n'})
check(G_NONASCII, lambda: (_na[0], [re.search(r'\[(.*?)/\]', l).group(1) for l in links(_na[1], 'Examples')]), (0, ['plugy', 'packx', 'caf\u00e9']))
check(G_HEADER, lambda: only(with_table(TABLE.replace('| Type |', '| Kind |'))),
      ['examples/README.md holds the table header `| Example | Type | What it demonstrates | Commands |` 0 times, wanted exactly once'])
check(G_HEADER2, lambda: only(with_table(TABLE + '\n' + TABLE)),
      ['examples/README.md holds the table header `| Example | Type | What it demonstrates | Commands |` 2 times, wanted exactly once'])
check(G_SEP, lambda: only(with_table(TABLE.replace('|---|---|---|---|\n', ''))),
      ['examples/README.md: the table header is not followed by its separator row'])
check(G_NOROW, lambda: only({**NEWDIR, 'examples/README.md': CORPUS['examples/README.md']}),
      ['examples/newz/ is tracked and has no row in examples/README.md'])
check(G_GHOSTROW, lambda: only(with_table(TABLE + '| [ghost/](./ghost/) | Pack | x | — |\n')),
      ['examples/README.md:7 links ./ghost/, which is not an example directory'])
check(G_NOLINK, lambda: only(with_table(TABLE.replace('[plugy/](./plugy/)', 'plugy'))),
      ['examples/README.md:5 has no link in its first cell', 'examples/plugy/ is tracked and has no row in examples/README.md'])
check(G_CELLS, lambda: only(with_table(TABLE.replace('| The plugin way |', '|'))),
      ['examples/README.md:5 is not a row of four cells', 'examples/plugy/ is tracked and has no row in examples/README.md'])
check(G_DUPROW, lambda: only(with_table(TABLE + '| [plugy/](./plugy/) | Plugin | Again | — |\n')),
      ['examples/README.md:7 is a second row for examples/plugy/ (first at line 5)'])
check(G_BADTYPE, lambda: only(with_table(TABLE.replace('| Pack |', '| Mod |'))),
      ["examples/README.md:6 has Type 'Mod', wanted one of Pack or Plugin"])
check(G_EMPTYWHAT, lambda: only(with_table(TABLE.replace('| The pack way |', '| |'))),
      ['examples/README.md:6 has an empty "What it demonstrates" cell'])
_pipe = gen(with_table(TABLE.replace('| The pack way |', '| Choose a\\|b |').replace('`/x`', '`/x <a\\|b>`')))
check(G_PIPE, lambda: (_pipe[0], [l.split('): ', 1)[1] for l in links(_pipe[1], 'Examples')]),
      (0, ['Plugin. The plugin way', 'Pack. Choose a|b']))
check(G_KEYED, lambda: [(re.search(r'\[(.*?)/\]', l).group(1), l.split('): ', 1)[1]) for l in links(_out, 'Examples')],
      [('plugy', 'Plugin. The plugin way'), ('packx', 'Pack. The pack way')])
check(G_TABLEORDER, lambda: [re.search(r'\[(.*?)/\]', l).group(1) for l in links(_out, 'Examples')], ['plugy', 'packx'])
_nd = gen({**NEWDIR, 'examples/README.md': '# Examples\n\n' + TABLE + ROW_NEWZ})
check(G_NEWDIR, lambda: (_nd[0], [re.search(r'\[(.*?)/\]', l).group(1) for l in links(_nd[1], 'Examples')],
                         [l for l in _nd[2] if l]), (0, ['plugy', 'packx', 'newz'], ['LLMS 2 categories, 4 pages, 3 examples']))
check(G_UNTRACKED, lambda: (gen({**NEWDIR}, untracked=tuple(NEWDIR))[0], [l for l in gen({**NEWDIR}, untracked=tuple(NEWDIR))[2] if l]),
      (0, ['LLMS 2 categories, 4 pages, 2 examples']))
_zero = {k: None for k in CORPUS if k.startswith('examples/') and k.count('/') >= 2}
check(G_ZERO, lambda: problems(_zero), (2, True, ['0 example directories are tracked under examples/: a list of nothing is a broken run']))
check(G_NOGIT, lambda: (lambda r: (r[0], r[1], any('git work tree' in b for b in r[2])))(problems(git=False)), (2, True, True))
check(G_NOEXREADME, lambda: only({'examples/README.md': None}), ['examples/README.md does not exist, and the examples are described by its table'])
check(G_STDOUT, lambda: (lambda r: (r[0], r[1]))(gen({'docs/zzz.md': page(), 'docs/a-page.md': page(title=''), 'docs/index.md': 'x\n'})),
      (2, ''))
check(G_REAL, lambda: subprocess.run([sys.executable, str(FROM / 'generate-llms-txt.py'), '--root', str(REPO)],
                                     capture_output=True, text=True).stdout == (REPO / 'docs/llms.txt').read_text(), True)

# ---- the section cases -------------------------------------------------------------------------------------
_sec = section_text()
OK_PASS = ('PASS  llms.txt generates (1 categories, 3 pages, 2 examples; 3 of 3 docs pages and 2 of 2 example directories linked, '
           'each figure counted from the output) and docs/llms.txt matches it')
CMD = 'python3 maintenance/scripts/generate-llms-txt.py > docs/llms.txt'


def sec(**kw):
    r = run_section(_sec, **kw)
    return r[4], r[1]


def old(**kw):
    r = run_section(OLD_SECTION, stub_name='generate-llms-txt.sh', **kw)
    return r[4], r[1]


# the stub is a python script; the old section ran it as an executable, so the control's stub needs a shebang and mode
def old_section_control():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        res = []
        for kw in (dict(out=GOOD_OUT, rc=3, err='  FAIL  boom\n', llms='same'), dict(out='', rc=0, err='', llms='same')):
            (root / 'maintenance/scripts').mkdir(parents=True, exist_ok=True)
            (root / 'docs').mkdir(exist_ok=True)
            s = root / 'maintenance/scripts/generate-llms-txt.sh'
            s.write_text('#!/usr/bin/env python3\n' + STUB.format(out=kw['out'], err=kw['err'], rc=kw['rc']))
            s.chmod(0o755)
            (root / 'docs/llms.txt').write_text(GOOD_OUT)
            p = subprocess.run(['bash', '-c', prelude() + OLD_SECTION + 'echo "HARD_FAILS=$HARD_FAILS"\n'], capture_output=True,
                               text=True, cwd=root)
            res.append([l.strip() for l in ANSI.sub('', p.stdout).splitlines() if l.strip() and not l.startswith(('== ', 'HARD_FAILS='))])
        return res
    finally:
        shutil.rmtree(root, ignore_errors=True)


check(S_NEG, old_section_control, [['PASS  docs/llms.txt matches a fresh regeneration'],
                                   ['WARN  docs/llms.txt is stale - regenerate']])
check(S_HEALTHY, lambda: sec(), (0, [OK_PASS]))
check(S_RC, lambda: sec(rc=3, err='  FAIL  boom\n  FAIL  llms.txt was not generated: 1 problem(s)\n'),
      (1, ['FAIL  generate-llms-txt.py exited 3 (docs/llms.txt is not checked against a generator that failed):',
           'boom', 'llms.txt was not generated: 1 problem(s)']))
check(S_EMPTY, lambda: sec(out='', err='LLMS 1 categories, 0 pages, 0 examples\n', llms='none'),
      (1, ['FAIL  generate-llms-txt.py exited 0 and wrote nothing']))
check(S_NOMARK, lambda: sec(err=''), (1, ["FAIL  generate-llms-txt.py printed 0 'LLMS' lines on stderr, wanted exactly 1"]))
check(S_TWO, lambda: sec(err='LLMS 1 categories, 3 pages, 2 examples\nLLMS 1 categories, 9 pages, 2 examples\n'),
      (1, ["FAIL  generate-llms-txt.py printed 2 'LLMS' lines on stderr, wanted exactly 1"]))
check(S_MALFORMED, lambda: sec(err='LLMS 1 categories, x pages, 2 examples\n'),
      (1, ["FAIL  the generator's 'LLMS' line is not 'LLMS <c> categories, <p> pages, <e> examples' with digits only (got: 1 categories, x pages, 2 examples)"]))
check(S_MARKBAD, lambda: sec(err='LLMS 1 categories, 5 pages, 2 examples\n'),
      (1, ['FAIL  generate-llms-txt.py says 5 pages, its output links 3 distinct page(s)']))
_DUP = GOOD_OUT.replace(LINK(3), LINK(1))
check(S_DUPPAGE, lambda: sec(out=_DUP),
      (2, ['FAIL  generate-llms-txt.py says 3 pages, its output links 2 distinct page(s)',
           'FAIL  the llms.txt output links 2 distinct page(s), docs/ holds 3 .md files: a page is missing from it, or listed twice']))
check(S_FEWER, lambda: sec(docs=5),
      (1, ['FAIL  the llms.txt output links 3 distinct page(s), docs/ holds 5 .md files: a page is missing from it, or listed twice']))
check(S_MORE, lambda: sec(docs=2),
      (1, ['FAIL  the llms.txt output links 3 distinct page(s), docs/ holds 2 .md files: a page is missing from it, or listed twice']))
check(S_DIRMD, lambda: sec(dirmd=True), (0, [OK_PASS]))
check(S_EXBAD, lambda: sec(err='LLMS 1 categories, 3 pages, 5 examples\n'),
      (1, ['FAIL  generate-llms-txt.py says 5 examples, its output links 2 distinct example directories']))
check(S_EXDUP, lambda: sec(out=GOOD_OUT.replace(EXL('e2'), EXL('e1')), err='LLMS 1 categories, 3 pages, 2 examples\n'),
      (2, ['FAIL  generate-llms-txt.py says 2 examples, its output links 1 distinct example directories',
           'FAIL  the llms.txt output links 1 distinct example directories, git tracks 2 under examples/']))
check(S_EXTRACKED, lambda: sec(tracked=3),
      (1, ['FAIL  the llms.txt output links 2 distinct example directories, git tracks 3 under examples/']))
check(S_GITFAIL, lambda: sec(git=False),
      (1, ['FAIL  git ls-files -z -- examples/ failed (status 128), so the examples were not counted']))
check(S_CATBAD, lambda: sec(err='LLMS 4 categories, 3 pages, 2 examples\n'),
      (1, ['FAIL  generate-llms-txt.py says 4 categories, its output has 1 category headings']))
check(S_STALE, lambda: sec(llms='other'), (0, [f'WARN  docs/llms.txt is stale \u2014 regenerate: {CMD}']))
check(S_MISSING, lambda: sec(llms='none'), (0, [f'WARN  docs/llms.txt missing \u2014 generate: {CMD}']))
check(S_CLEAN, lambda: (run_section(_sec)[2], run_section(_sec, rc=3, err='x\n')[2], run_section(_sec, out='')[2]), (0, 0, 0))
check(S_MKTEMP, lambda: (lambda r: (r[4], [l for l in r[1] if l.startswith(('FAIL', 'PASS', 'WARN'))], r[3]))(run_section(_sec, tmpdir='gone')),
      (1, ['FAIL  mktemp -d failed, so the llms.txt generator was not run'], False))
check(S_STATIC, lambda: [l for l in _sec.splitlines() if re.search(r'(?<![.\w])(trap|exit)\b', l) and not l.lstrip().startswith('#')], [])

# ---- the report --------------------------------------------------------------------------------------------
check(S_ALLCASES, lambda: sorted(set(seen) - {S_ALLCASES}), sorted(ALL_CASES - {S_ALLCASES}))
print(f'\nFIXTURE {len(seen)} check(s): {len(seen) - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if len(seen) < MIN_CASES:
    print(f'  FAIL floor: {len(seen)} check(s) ran, at least {MIN_CASES} expected')
    sys.exit(1)
sys.exit(1 if fails else 0)
