#!/usr/bin/env python3
"""
The fixture of the docs site's gates: it runs verify-docs.sh's OWN sections for the site, cut out of the
script by their headers (as check-asset-drift-fixture.py does for the drift section), under planted defects,
and with --mutations proves that each guard is the thing that catches its defect.

WHAT IT COVERS, one part per gate. Each part has its cases, and each guard a mutation whose exact red set is
pinned (a mutation that reddens a case it was not written for, or fails to redden the one it was, is a FAIL;
a red set not yet pinned is printed as MEASURED and fails the run, so a number is never pasted blind):

  markdown   the section "Docs markdown renders the same on GitHub and on the site" and
             maintenance/scripts/check-site-markdown.py (the lint it runs).
  nav        the section "The sidebar is generated from README.md and holds every docs page once" and
             maintenance/scripts/generate-site-nav.py.

WHY THE SECTION'S TEXT AND NOT A COPY OF ITS LOGIC. The same reason as the drift fixture's: a helper with a
fixture of its own tests the helper and leaves the wrapper that reads the helper's status and denominators
untested, which is the same defect one level up. Each section is cut from verify-docs.sh (from its `section "..."`
line to the next `# =====` line, asserting it finds exactly one), prefixed with the script's own `set -u` and
section()/pass()/fail()/warn()/info() definitions, and run in a temp root that holds copies of the scripts it
calls and a planted corpus. A mutation edits that text, or one of the copied scripts, and re-runs every case.

Usage:
  python3 maintenance/scripts/check-site-fixture.py [-v]
  python3 maintenance/scripts/check-site-fixture.py --mutations [-v]
"""
from __future__ import annotations
import argparse, concurrent.futures, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
VERIFY = HERE / 'verify-docs.sh'
FIX = REPO / 'maintenance' / 'fixtures' / 'site'
ANSI = re.compile(r'\x1b\[[0-9;]*m')

# FLOORS, as in the other fixtures: lowering one needs a reason in the commit message.
MIN_CASES = 41
MIN_MUTATIONS = 35

SECTION_MD = 'section "[HARD] Docs markdown renders the same on GitHub and on the site"'
SECTION_NAV = 'section "[HARD] The sidebar is generated from README.md and holds every docs page once"'
SCRIPTS = ('check-site-markdown.py', 'check-links.py', 'doc_fences.py', 'generate-site-nav.py')


def cut(src: str, anchor: str) -> str:
    n = src.count(anchor)
    if n != 1:
        raise SystemExit(f'FAIL  {anchor!r} occurs {n} time(s) in verify-docs.sh, not once - the section was '
                         f'renamed or duplicated; move this anchor with it')
    s = src.index(anchor)
    return src[s:src.index('\n# =====', s)] + '\n'


def prelude() -> str:
    """`set -u` and the real HARD_FAILS/section/pass/fail/warn/info definitions of verify-docs.sh, verbatim:
    fail() incrementing HARD_FAILS is part of what a section's severity means."""
    v = VERIFY.read_text()
    assert v.count('\nset -u\n') == 1, 'verify-docs.sh no longer has exactly one `set -u` line'
    a = v.index('\nHARD_FAILS=0\n') + 1
    i = v.index('\ninfo()', a) + 1
    return 'set -u\n' + v[a:v.index('\n', i) + 1]


class World:
    """One variant of the system under test: the section texts and the scripts, possibly with ONE mutation
    applied. `run` makes a root of its own for each call, so cases never see each other's files."""

    def __init__(self, base: pathlib.Path, *, section_edits=None, script_edits=None):
        self.base = base
        base.mkdir(parents=True, exist_ok=True)
        src = VERIFY.read_text()
        self.sections = {'md': cut(src, SECTION_MD), 'nav': cut(src, SECTION_NAV)}
        for key, (old, new) in (section_edits or {}).items():
            if self.sections[key].count(old) != 1:
                raise SystemExit(f'FAIL  mutation anchor {old!r} occurs {self.sections[key].count(old)} time(s) in the {key} section')
            self.sections[key] = self.sections[key].replace(old, new, 1)
        self.scripts = base / 'scripts'
        self.scripts.mkdir()
        for name in SCRIPTS:
            shutil.copy2(HERE / name, self.scripts / name)
        for name, (old, new) in (script_edits or {}).items():
            body = (self.scripts / name).read_text()
            if body.count(old) != 1:
                raise SystemExit(f'FAIL  mutation anchor {old!r} occurs {body.count(old)} time(s) in {name}')
            (self.scripts / name).write_text(body.replace(old, new, 1))
        self.n = 0

    def root(self, name: str, corpus: str, files: dict | None = None, drop: tuple = ()) -> pathlib.Path:
        self.n += 1
        root = self.base / f'{name}-{self.n}'
        shutil.copytree(FIX / corpus, root)
        (root / 'maintenance').mkdir(exist_ok=True)
        shutil.copytree(self.scripts, root / 'maintenance' / 'scripts')
        for rel in drop:
            (root / rel).unlink()
        for rel, body in (files or {}).items():
            f = root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body)
        return root

    def run(self, key: str, root: pathlib.Path, *, env=None):
        """Run section `key` in `root`. -> (exit status, output without colours, HARD_FAILS)"""
        script = prelude() + self.sections[key] + 'echo "HARD_FAILS=$HARD_FAILS"\n'
        e = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(env or {}))
        p = subprocess.run(['bash', '-c', script], capture_output=True, text=True, cwd=root, env=e)
        out = ANSI.sub('', p.stdout + p.stderr)
        m = re.findall(r'^HARD_FAILS=(\d+)$', out, re.M)
        return p.returncode, out, (int(m[-1]) if m else -1)


def lines(out: str) -> list[str]:
    """The section's own lines: no header, no HARD_FAILS marker."""
    return [l.strip() for l in out.splitlines() if l.strip() and not l.startswith(('HARD_FAILS=', '== '))]


# ============================== part 1: the markdown lint ==============================

CASE_MD = {
    'healthy': 'markdown: a clean docs tree prints its denominators and passes',
    'gen_raw': 'markdown: a heading with <ECS_TYPE> outside a code span FAILs with file:line',
    'gen_tag': 'markdown: a heading with <KeyType> (a tag to GitHub) FAILs the same way',
    'gen_comma': 'markdown: a heading with <K, T> (text to GitHub) FAILs too, the lint refuses every raw `<`',
    'gen_span': 'markdown: a generic in a code span is clean, and a code span after a raw one does not hide it',
    'gen_fence': 'markdown: a `# Foo<T>` line in a code fence is not a heading',
    'nest2': 'markdown: a nested list item indented 2 past its parent FAILs',
    'nest4': 'markdown: a nested list item indented 4 past its parent is clean',
    'nest_ord': 'markdown: a child of a numbered item at 3 FAILs and at 4 is clean',
    'nest_quote': 'markdown: the same inside a blockquote',
    'block2': 'markdown: a paragraph after a blank line inside an item at 2 FAILs, at 4 it is clean',
    'fence2': 'markdown: a fence after a blank line inside an item at 2 FAILs',
    'fence_adj': 'markdown: a fence straight after the item line needs no more than the content column',
    'zero_pages': 'markdown: a docs tree with no page is a FAIL naming the exit status, not a clean run',
    'silent': 'markdown: a lint that exits 0 having read nothing is a FAIL, not a clean run',
    'zero_pages_figs': 'markdown: a lint that reports 0 pages beside non-zero figures is a FAIL, not a clean run',
    'zero_items': 'markdown: a tree with no list item is a FAIL naming the denominator',
    'zero_heads': 'markdown: a tree with no heading is a FAIL naming the denominator',
    'fix': 'markdown: --fix re-indents the flagged blocks, changes whitespace only, and leaves a tree that lints clean',
}


def md_cases(w: World) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}

    def check(key, label_problems):
        res[CASE_MD[key]] = label_problems

    def sec(files, **kw):
        return w.run('md', w.root('md', 'md-base', files, **kw))

    def verdict(key, got, *, hf, must=(), must_not=(), exact=None):
        rc, out, h = got
        pr = []
        if h != hf:
            pr.append(f'HARD_FAILS {h}, wanted {hf}')
        if exact is not None and lines(out) != exact:
            pr.append(f'lines {lines(out)!r}, wanted {exact!r}')
        pr += [f'missing {m!r}' for m in must if m not in out]
        pr += [f'unexpected {m!r}' for m in must_not if m in out]
        check(key, pr)

    base_info = 'INFO  1 page(s), 2 heading(s) and 2 list item(s) read'
    base_pass = ('PASS  1 page(s) linted (2 heading(s), 2 list item(s) read): no generic outside a code span in a '
                 'heading, no list child indented under 4')
    verdict('healthy', sec({}), hf=0, exact=[base_info, base_pass])

    for key, heading, text in (('gen_raw', '## Store<ECS_TYPE>', 'Store<ECS_TYPE>'),
                               ('gen_tag', '### IAsyncEvent<KeyType>', 'IAsyncEvent<KeyType>'),
                               ('gen_comma', '## AssetCodecMapCodec<K, T>', 'AssetCodecMapCodec<K, T>')):
        verdict(key, sec({'docs/gen.md': f'# Gen\n\n{heading}\n\ntext\n'}), hf=1,
                must=(f"docs/gen.md:3: heading-generic: a `<` outside a code span in a heading: {text!r}",
                      'docs markdown that GitHub and the site would render differently:'),
                must_not=('PASS',))
    verdict('gen_span', sec({'docs/gen.md': '# Gen\n\n## `Store<ECS_TYPE>` and Foo<T> after a span\n\n### `A<B>` only\n'}), hf=1,
            must=("docs/gen.md:3: heading-generic",), must_not=('docs/gen.md:5',))
    # (the clean tree reads 2 headings, this page adds `# Gen`: 3 are read and the two `#` lines in the fence are not)
    verdict('gen_fence', sec({'docs/gen.md': '# Gen\n\n```bash\n# Foo<T> comment\n## Bar<K>\n```\n'}), hf=0,
            must=('3 heading(s)', 'PASS'), must_not=('  FAIL  ',))

    parent = '- parent item\n'
    verdict('nest2', sec({'docs/l.md': f'# L\n\n{parent}  - child at two\n'}), hf=1,
            must=("docs/l.md:4: list-child-indent: a nested list item indented 2 past its parent (needs 4): '- child at two'",))
    verdict('nest4', sec({'docs/l.md': f'# L\n\n{parent}    - child at four\n    - and a sibling\n'}), hf=0, must=('PASS',), must_not=('  FAIL  ',))
    verdict('nest_ord', sec({'docs/l.md': '# L\n\n1. first\n   - child at three\n'}), hf=1,
            must=("docs/l.md:4: list-child-indent: a nested list item indented 3 past its parent (needs 4)",))
    # the second half of that case: at four it is clean
    ok = sec({'docs/l.md': '# L\n\n1. first\n    - child at four\n'})
    if ok[2] != 0 or '  FAIL  ' in ok[1]:
        res[CASE_MD['nest_ord']].append(f'a child of a numbered item at 4 was refused: {lines(ok[1])}')
    verdict('nest_quote', sec({'docs/l.md': '# L\n\n> - parent in a quote\n>   - child at two\n'}), hf=1,
            must=("docs/l.md:4: list-child-indent: a nested list item indented 2 past its parent (needs 4)",))
    verdict('block2', sec({'docs/l.md': f'# L\n\n{parent}\n  a second paragraph at two\n'}), hf=1,
            must=("docs/l.md:5: list-child-indent: a block inside a list item indented 2 past the item (needs 4): 'a second paragraph at two'",))
    ok = sec({'docs/l.md': f'# L\n\n{parent}\n    a second paragraph at four\n'})
    if ok[2] != 0 or '  FAIL  ' in ok[1]:
        res[CASE_MD['block2']].append(f'a paragraph at 4 after a blank line was refused: {lines(ok[1])}')
    verdict('fence2', sec({'docs/l.md': f'# L\n\n{parent}\n  ```java\n  int x;\n  ```\n'}), hf=1,
            must=("docs/l.md:5: list-child-indent: a fence inside a list item indented 2 past the item (needs 4): '```java'",))
    verdict('fence_adj', sec({'docs/l.md': f'# L\n\n{parent}  ```java\n  int x;\n  ```\n- next item\n'}), hf=0, must=('PASS',), must_not=('  FAIL  ',))

    # the lint reads nothing
    verdict('zero_pages', sec({}, drop=('docs/ok.md',)), hf=1,
            must=('FAIL  check-site-markdown.py exited 2, so nothing was linted:',), must_not=('PASS',))
    stub = '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n'
    verdict('silent', sec({'maintenance/scripts/check-site-markdown.py': stub}), hf=1,
            must=('FAIL  the markdown lint read no page(s), no heading(s) and no list item(s)',), must_not=('PASS',))
    fake = ('#!/usr/bin/env python3\nprint("  INFO  0 page(s), 5 heading(s) and 5 list item(s) read")\n')
    verdict('zero_pages_figs', sec({'maintenance/scripts/check-site-markdown.py': fake}), hf=1,
            must=('FAIL  the markdown lint read 0 page(s), 5 heading(s) and 5 list item(s)',), must_not=('PASS',))
    verdict('zero_items', sec({'docs/ok.md': '# Ok\n\ntext only\n'}), hf=1,
            must=('FAIL  the markdown lint read 1 page(s), 1 heading(s) and 0 list item(s)',), must_not=('PASS',))
    verdict('zero_heads', sec({'docs/ok.md': 'text only\n\n- an item\n'}), hf=1,
            must=('FAIL  the markdown lint read 1 page(s), 0 heading(s) and 1 list item(s)',), must_not=('PASS',))

    # --fix: whitespace only, exactly the spaces the flagged blocks lack, and a golden result
    broken = ('# B\n\n- parent\n  - child at two\n  - another\n\n- second\n\n  second para at two\n\n'
              '- third\n\n  ```java\n  int x;\n  ```\n\n  after the fence\n')
    golden = ('# B\n\n- parent\n    - child at two\n    - another\n\n- second\n\n    second para at two\n\n'
              '- third\n\n    ```java\n    int x;\n    ```\n\n    after the fence\n')
    root = w.root('md-fix', 'md-base', {'docs/b.md': broken})
    subprocess.run([sys.executable, str(root / 'maintenance' / 'scripts' / 'check-site-markdown.py'), '--root', str(root), '--fix'],
                   capture_output=True, text=True)
    after = (root / 'docs' / 'b.md').read_text()
    pr = []
    if after != golden:
        pr.append(f'--fix wrote {after!r}, wanted {golden!r}')
    rc, out, h = w.run('md', root)
    if h != 0 or '  FAIL  ' in out:
        pr.append(f'the fixed tree does not lint clean: {lines(out)}')
    check('fix', pr)
    return res



# ============================== part 2: the sidebar ==============================

CASE_NAV = {
    'healthy': 'nav: a tree whose committed sidebar is the generation passes, with the figures of both sides',
    'stale': 'nav: a committed sidebar that differs from a fresh generation FAILs and says how to regenerate',
    'label': 'nav: a README link text changed since the generation FAILs (the sidebar label is the README text)',
    'order': 'nav: two categories swapped in the README FAIL (order is the README\'s)',
    'missing': 'nav: a docs page the README does not list is missing from the sidebar and FAILs by name',
    'twice': 'nav: a page listed under two categories is refused by the generator, by name',
    'ghost': 'nav: a README link to a page that does not exist is refused by the generator, by name',
    'zero': 'nav: a README with no category is a FAIL naming the empty read, not a clean run',
    'silent': 'nav: a generator that exits 0 having printed nothing is a FAIL, not a clean run',
    'zero_cats': 'nav: a generator that reports 0 categories beside 3 pages is a FAIL, not a clean run',
    'zero_pages': 'nav: a generator that reports 0 pages beside 2 categories is a FAIL, not a clean run',
    'emptynav': 'nav: a committed sidebar with no entry is a FAIL naming the unreadable nav',
    'nodocs': 'nav: a tree with no docs page is a FAIL naming the unreadable docs, not a clean run',
    'listed': 'nav: a page count different from the README-listing gate\'s LISTED FAILs',
    'emptycat': 'nav: a category with no page is not a sidebar group',
    'section': 'nav: pages listed after the Documentation section (Examples) are not read',
    'read_twice': 'nav: a committed sidebar naming a page twice FAILs by name (read from the toml, not the generator)',
    'read_nofile': 'nav: a committed sidebar entry naming a file that does not exist FAILs by name',
    'read_home': 'nav: a committed sidebar whose first entry is not Home FAILs',
    'read_missing': 'nav: a docs page absent from the committed sidebar FAILs by name (read from the toml)',
    'badtoml': 'nav: an unreadable zensical.toml is a FAIL, not a pass',
    'exit': 'nav: a generator that crashes (exit 3) is a FAIL naming the status',
}

NAV_PASS = ('PASS  sidebar = README: 2 categories and 3 pages generated, equal to the README-listing gate\'s 3; '
            'the committed nav holds 4 of 4 docs pages (Home first, each once, each file present)')
STUB_NAV = '#!/usr/bin/env python3\nimport sys\nprint("NAV 2 categories, 3 pages", file=sys.stderr)\n'


def nav_toml(nav_lines: str) -> str:
    return ('[project]\nsite_name = "Fixture"\n# BEGIN GENERATED NAV (maintenance/scripts/generate-site-nav.py from README.md; '
            'do not edit by hand)\nnav = [\n' + nav_lines + ']\n# END GENERATED NAV\n')


def nav_cases(w: World) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}

    def sec(files=None, drop=(), listed='3'):
        return w.run('nav', w.root('nav', 'nav-base', files, drop), env={'RM_LISTED': listed})

    def verdict(key, got, *, hf, must=(), must_not=(), exact=None):
        rc, out, h = got
        pr = []
        if h != hf:
            pr.append(f'HARD_FAILS {h}, wanted {hf}')
        if exact is not None and lines(out) != exact:
            pr.append(f'lines {lines(out)!r}, wanted {exact!r}')
        pr += [f'missing {m!r}' for m in must if m not in out]
        pr += [f'unexpected {m!r}' for m in must_not if m in out]
        res[CASE_NAV[key]] = pr

    readme = (FIX / 'nav-base' / 'README.md').read_text()
    toml = (FIX / 'nav-base' / 'zensical.toml').read_text()
    home = '  { "Home" = "index.md" },\n'
    first = '  { "First" = [ { "Alpha" = "a.md" }, { "Beta" = "b.md" } ] },\n'
    second = '  { "Second" = [ { "Gamma" = "c.md" } ] },\n'

    verdict('healthy', sec(), hf=0, exact=[NAV_PASS])
    verdict('stale', sec({'zensical.toml': toml.replace('"Alpha"', '"Alfa"')}), hf=1,
            must=('the nav in zensical.toml differs from a fresh generation from README.md (run maintenance/scripts/generate-site-nav.py --write)',),
            must_not=('PASS',))
    verdict('label', sec({'README.md': readme.replace('[Alpha]', '[Alpha page]')}), hf=1,
            must=('differs from a fresh generation',), must_not=('PASS',))
    swapped = readme.replace('### First\n- [Alpha](./docs/a.md) - the first page\n- [Beta](./docs/b.md) - the second page\n\n### Second\n- [Gamma](./docs/c.md) - the third page\n',
                             '### Second\n- [Gamma](./docs/c.md) - the third page\n\n### First\n- [Alpha](./docs/a.md) - the first page\n- [Beta](./docs/b.md) - the second page\n')
    assert swapped != readme
    verdict('order', sec({'README.md': swapped}), hf=1, must=('differs from a fresh generation',), must_not=('PASS',))
    # a page the README does not list: the generator's count (2) is also not LISTED's, but the committed nav is read itself
    verdict('missing', sec({'README.md': readme.replace('### Second\n- [Gamma](./docs/c.md) - the third page\n', ''),
                            'zensical.toml': nav_toml(home + first)}, listed='2'), hf=1,
            must=('docs page missing from the sidebar: c.md',), must_not=('PASS',))
    verdict('twice', sec({'README.md': readme.replace('- [Gamma](./docs/c.md) - the third page', '- [Gamma](./docs/c.md) - the third page\n- [Alpha again](./docs/a.md) - twice')}), hf=1,
            must=('generate-site-nav.py exited 2', 'a.md is listed twice in README (under \'First\' and \'Second\')'), must_not=('PASS',))
    verdict('ghost', sec({'README.md': readme.replace('./docs/c.md', './docs/ghost.md')}), hf=1,
            must=('generate-site-nav.py exited 2', 'README lists ghost.md under \'Second\', and docs/ghost.md does not exist'), must_not=('PASS',))
    verdict('zero', sec({'README.md': '# T\n\n## Documentation\n\nnothing listed\n'}), hf=1,
            must=('generate-site-nav.py exited 2',), must_not=('PASS',))
    verdict('silent', sec({'maintenance/scripts/generate-site-nav.py': '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n'}), hf=1,
            must=('the sidebar generator read no categor(ies) and no page(s) from README.md',), must_not=('PASS',))
    verdict('zero_cats', sec({'maintenance/scripts/generate-site-nav.py': STUB_NAV.replace('2 categories, 3 pages', '0 categories, 3 pages')}), hf=1,
            must=('the sidebar generator read 0 categor(ies) and 3 page(s) from README.md',), must_not=('PASS',))
    verdict('zero_pages', sec({'maintenance/scripts/generate-site-nav.py': STUB_NAV.replace('2 categories, 3 pages', '2 categories, 0 pages')}), hf=1,
            must=('the sidebar generator read 2 categor(ies) and 0 page(s) from README.md',), must_not=('PASS',))
    verdict('listed', sec(listed='4'), hf=1,
            must=('the generator read 3 page(s) from README.md, the README-listing gate counts 4 listed',), must_not=('PASS',))
    verdict('emptycat', sec({'README.md': readme.replace('### Second', '### Empty\n\n### Second')}), hf=0,
            exact=[NAV_PASS])
    # (the Examples section of the base README lists docs/a.md again; read, it would be a second listing and the generator would refuse)
    verdict('section', sec(), hf=0, must=('PASS',), must_not=('twice',))

    # the committed toml read by the section itself, the generator stubbed to agree (3 pages, exit 0)
    stub = {'maintenance/scripts/generate-site-nav.py': STUB_NAV}
    verdict('read_twice', sec({**stub, 'zensical.toml': nav_toml(home + first + '  { "Again" = [ { "Alpha" = "a.md" } ] },\n' + second)}), hf=1,
            must=('docs page in the sidebar twice: a.md',), must_not=('PASS',))
    verdict('read_nofile', sec({**stub, 'zensical.toml': nav_toml(home + first + second.replace('c.md', 'c.md" }, { "Ghost" = "ghost.md'))}), hf=1,
            must=('sidebar entry names a file that does not exist: docs/ghost.md',), must_not=('PASS',))
    verdict('read_home', sec({**stub, 'zensical.toml': nav_toml(first + home + second)}), hf=1,
            must=('the first sidebar entry is not Home (index.md): First',), must_not=('PASS',))
    verdict('read_missing', sec({**stub, 'zensical.toml': nav_toml(home + first)}), hf=1,
            must=('docs page missing from the sidebar: c.md',), must_not=('PASS',))
    verdict('emptynav', sec({**stub, 'zensical.toml': nav_toml('')}), hf=1,
            must=('could not read the nav of zensical.toml or the docs pages',), must_not=('PASS',))
    verdict('nodocs', sec({**stub}, drop=('docs/index.md', 'docs/a.md', 'docs/b.md', 'docs/c.md')), hf=1,
            must=('could not read the nav of zensical.toml or the docs pages',), must_not=('PASS',))
    verdict('badtoml', sec({**stub, 'zensical.toml': 'this is = not [valid toml\n'}), hf=1,
            must=('could not read the nav of zensical.toml',), must_not=('PASS',))
    verdict('exit', sec({'maintenance/scripts/generate-site-nav.py': '#!/usr/bin/env python3\nimport sys\nsys.exit(3)\n'}), hf=1,
            must=('generate-site-nav.py exited 3, so the sidebar cannot be compared with README.md',), must_not=('PASS',))
    return res


# ============================== the mutation table ==============================

MUTATIONS: dict = {}
MEAS = None      # an expected red set not yet pinned: main() prints the measured one and fails


def mut(label, where, old, new, names, expect, part='md'):
    """where: ('script', file) or ('section', key). names: the cases this guard exists for, which must go red.
    expect: the exact set that goes red (the guard's neighbours included), pinned so a case that stops
    detecting is a failure. Both are CASE_* keys of `part`."""
    MUTATIONS[label] = (where, old, new, part, set(names), None if expect is None else set(expect))


CMD = 'check-site-markdown.py'
mut('IDENTITY (no change - the harness control)', ('script', CMD), '#!/usr/bin/env python3', '#!/usr/bin/env python3', [], [])
mut('the heading rule is removed', ('script', CMD), "if '<' in outside_code(m.group(1)):", 'if False:',
    ['gen_raw'], ['gen_raw', 'gen_tag', 'gen_comma', 'gen_span'])
mut('code spans are not set aside in a heading', ('script', CMD), "return CL.CODE_SPAN.sub('', t)", 'return t',
    ['gen_span'], ['healthy', 'gen_span', 'gen_fence', 'nest4', 'nest_ord', 'block2', 'fence_adj', 'fix'])
mut('fenced `#` lines are read as headings', ('script', CMD), '        if m and no not in fenced:', '        if m:',
    ['gen_fence'], ['gen_fence'])
mut('the nested-item rule is removed', ('script', CMD),
    'if stack and col >= stack[-1][1] and col - stack[-1][0] < 4:', 'if False:',
    ['nest2'], ['nest2', 'nest_ord', 'nest_quote', 'fix'])
mut('the nested-item threshold is 2, not 4', ('script', CMD),
    'if stack and col >= stack[-1][1] and col - stack[-1][0] < 4:', 'if stack and col >= stack[-1][1] and col - stack[-1][0] < 2:',
    ['nest2'], ['nest2', 'nest_ord', 'nest_quote', 'fix'])
mut('the block rule is removed', ('script', CMD), '            if stack and indent - stack[-1][0] < 4:', '            if False:',
    ['block2'], ['block2', 'fence2', 'fix'])
mut('a fence is not a block (its opener is skipped)', ('script', CMD),
    'opener = no in fenced and (no - 1) not in fenced', 'opener = False',
    ['fence2'], ['fence2', 'fix'])
mut('a fence straight after the item line is judged too', ('script', CMD),
    '        if prev_blank:\n            while stack and indent < stack[-1][1]:', '        if prev_blank or opener:\n            while stack and indent < stack[-1][1]:',
    ['fence_adj'], ['fence_adj'])
mut('quote prefixes are not read', ('script', CMD), 'prefix, line = QUOTE.match(raw).groups()', "prefix, line = '', raw",
    ['nest_quote'], ['nest_quote'])
mut('--fix does nothing', ('script', CMD), '            p.write_text(fix_page(text))', '            pass',
    ['fix'], ['fix'])
mut('the section does not read the lint\'s exit status', ('section', 'md'),
    'if [ "$RC" -ne 0 ] && [ "$RC" -ne 1 ]; then', 'if false; then',
    ['zero_pages'], ['zero_pages'])
mut('the section does not require a page', ('section', 'md'),
    '[ -z "$MD_PAGES" ] || [ "$MD_PAGES" -eq 0 ] || ', '',
    ['zero_pages_figs'], ['zero_pages_figs'])
mut('the section does not require a heading', ('section', 'md'),
    '|| [ "${MD_HEADS:-0}" -eq 0 ]', '',
    ['zero_heads'], ['zero_heads'])
mut('the section does not require a list item', ('section', 'md'),
    '|| [ "${MD_ITEMS:-0}" -eq 0 ]', '',
    ['zero_items'], ['zero_items'])
mut('findings are not a FAIL', ('section', 'md'),
    'elif [ "$RC" -eq 1 ]; then', 'elif false; then',
    ['gen_raw'], ['gen_raw', 'gen_tag', 'gen_comma', 'gen_span', 'nest2', 'nest_ord', 'nest_quote', 'block2', 'fence2'])
mut('the pass line drops the denominators', ('section', 'md'),
    'pass "$MD_PAGES page(s) linted ($MD_HEADS heading(s), $MD_ITEMS list item(s) read): ', 'pass "linted: ',
    ['healthy'], ['healthy'])


# ---- the sidebar ----
GEN = 'generate-site-nav.py'
mut('the generator reads past the Documentation section', ('script', GEN), "e = readme.find('\\n## ', s + 1)", 'e = -1',
    ['section'], ['healthy', 'section', 'stale', 'label', 'order', 'missing', 'emptycat', 'listed'], part='nav')
mut('a page listed twice is not refused', ('script', GEN), "if page in seen:", 'if False:',
    ['twice'], ['twice'], part='nav')
mut('a README link to a missing page is not refused', ('script', GEN), "if not (root / 'docs' / page).is_file():", 'if False:',
    ['ghost'], ['ghost'], part='nav')
mut('an empty category is a sidebar group', ('script', GEN), "if c[1]]", "]",
    ['emptycat'], ['emptycat'], part='nav')
mut('Home is not first', ('script', GEN), "lines = [BEGIN, 'nav = [', '  { \"Home\" = \"index.md\" },']", "lines = [BEGIN, 'nav = [']",
    ['healthy'], ['healthy', 'missing', 'emptycat', 'section', 'listed'], part='nav')
mut('the generator exits 0 on an empty read', ('script', GEN), "if ncat == 0 or npage == 0 or problems:", 'if problems:',
    ['zero'], ['zero'], part='nav')
mut('--check never fails', ('script', GEN), '    if new != toml:', '    if False:',
    ['stale'], ['stale', 'label', 'order'], part='nav')
mut('the section does not read the generator\'s exit status', ('section', 'nav'),
    'if [ "$NAV_RC" -ne 0 ] && [ "$NAV_RC" -ne 1 ]; then', 'if false; then',
    ['exit'], ['exit', 'twice', 'ghost', 'zero'], part='nav')
mut('the section does not require a category', ('section', 'nav'),
    '[ -z "$NAV_CATS" ] || [ "$NAV_CATS" -eq 0 ] || ', '',
    ['zero_cats'], ['zero_cats'], part='nav')
mut('the section does not require a page from the generator', ('section', 'nav'),
    ' || [ "${NAV_PAGES:-0}" -eq 0 ]; then\n  fail "the sidebar generator read', '; then\n  fail "the sidebar generator read',
    ['zero_pages'], ['zero_pages'], part='nav')
mut('the committed-vs-generated difference is not a FAIL', ('section', 'nav'),
    'if [ "$NAV_RC" -eq 1 ]; then', 'if false; then',
    ['stale'], ['stale', 'label', 'order'], part='nav')
mut('the page count is not compared with LISTED', ('section', 'nav'),
    'if [ "$NAV_PAGES" != "${RM_LISTED:-}" ]; then', 'if false; then',
    ['listed'], ['listed'], part='nav')
mut('an empty committed sidebar is readable', ('section', 'nav'),
    '[ "${NAV_N:-0}" -eq 0 ] || ', '',
    ['emptynav'], ['emptynav'], part='nav')
mut('a tree with no docs page is readable', ('section', 'nav'),
    ' || [ "${NAV_D:-0}" -eq 0 ]; then', '; then',
    ['nodocs'], ['nodocs'], part='nav')
mut('a page missing from the sidebar is not reported', ('section', 'nav'), "s/^MISSING /      docs page missing from the sidebar: /p; ", '',
    ['read_missing'], ['read_missing', 'missing'], part='nav')
mut('a page in the sidebar twice is not reported', ('section', 'nav'), "s/^TWICE /      docs page in the sidebar twice: /p; ", '',
    ['read_twice'], ['read_twice'], part='nav')
mut('a sidebar entry naming a missing file is not reported', ('section', 'nav'), "s/^NOFILE /      sidebar entry names a file that does not exist: docs\\//p; ", '',
    ['read_nofile'], ['read_nofile'], part='nav')
mut('Home first is not required', ('section', 'nav'), 'if first != "index.md":\n    print(f"HOME {first_label}")', 'pass',
    ['read_home'], ['read_home'], part='nav')

PARTS = {'md': (CASE_MD, md_cases), 'nav': (CASE_NAV, nav_cases)}


def apply_edit(where, old, new):
    kind, name = where
    return ({}, {name: (old, new)}) if kind == 'script' else ({name: (old, new)}, {})


def run_part(part: str, w: World) -> dict[str, list[str]]:
    return PARTS[part][1](w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        res: dict[str, list[str]] = {}
        for part in PARTS:
            res.update(run_part(part, World(work / f'base-{part}')))
        if len(res) < MIN_CASES:
            print(f'  FAIL  {len(res)} case(s) ran, floor is {MIN_CASES}. A fixture that examines nothing '
                  f'reports the same thing as one that passes.')
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
            print(f'  FAIL  {len(MUTATIONS)} mutation(s) defined, floor is {MIN_MUTATIONS}.')
            return 1
        if not any(k.startswith('IDENTITY') for k in MUTATIONS):
            print('  FAIL  no IDENTITY control in MUTATIONS')
            return 1
        print(f'\nMUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')

        def one(item):
            k, (label, (where, old, new, part, names, expect)) = item
            sec, scr = apply_edit(where, old, new)
            mres = run_part(part, World(work / f'm{k}', section_edits=sec, script_edits=scr))
            return label, part, names, expect, {c for c, v in mres.items() if v}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as pool:
            results = list(pool.map(one, enumerate(MUTATIONS.items())))
        for label, part, names, expect, red in results:
            case = PARTS[part][0]
            full = lambda keys: {case[x] for x in keys}
            if label.startswith('IDENTITY') and red:
                print(f'  FAIL {label}: the control reddened {len(red)} case(s); the harness is broken. Aborting.')
                for x in sorted(red):
                    print(f'         {x}')
                return 1
            if full(names) - red:
                rc = 1
                print(f'  FAIL {label}: the case this defect belongs to stayed GREEN')
                for x in sorted(full(names) - red):
                    print(f'         {x}')
                continue
            if expect is None:
                rc = 1
                print(f'  MEASURED {label}: ' + repr(sorted(k for k, c in case.items() if c in red)))
            elif red == full(expect):
                print(f'  ok   {label} -> {len(red)} case(s) red, exactly as expected')
                if a.verbose:
                    for r in sorted(red):
                        print(f'         {r}')
            else:
                rc = 1
                print(f'  FAIL {label}:')
                for x in sorted(full(expect) - red):
                    print(f'         expected red, stayed green: {x}')
                for x in sorted(red - full(expect)):
                    print(f'         unexpectedly red: {x}')
        print('MUTATIONS ' + ('all expected red sets matched' if rc == 0 else 'a red set did not match - see above'))
    return rc


if __name__ == '__main__':
    sys.exit(main())
