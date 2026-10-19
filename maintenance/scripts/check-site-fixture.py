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
  links      maintenance/scripts/check-site-links.py on planted HTML (a built site made here, 79 small pages).
  build      maintenance/scripts/check-site-build.py on planted zensical logs.
  ext        maintenance/site/handbook_md.py, through maintenance/site/check-extension.py run with the SITE venv's
             python ($HANDBOOK_SITE_PY): skipped, and said so, when there is no venv; see part 6.
  site       the section "The site builds with no unexplained warning", with a stub in place of zensical (a shell
             script that copies a planted site into ./site and prints a planted log), so every branch of the
             section runs in a second, not in the 4 s a real build takes, and the real one is run by verify-docs.

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
MIN_CASES = 107            # without the extension part, which needs the site venv; +MIN_EXT_CASES with it
MIN_MUTATIONS = 93
MIN_EXT_CASES = 21
MIN_EXT_MUTATIONS = 23

SECTION_MD = 'section "[HARD] Docs markdown renders the same on GitHub and on the site"'
SECTION_NAV = 'section "[HARD] The sidebar is generated from README.md and holds every docs page once"'
SECTION_SITE = 'section "[HARD] The site builds with no unexplained warning"'
SCRIPTS = ('check-site-markdown.py', 'check-links.py', 'doc_fences.py', 'generate-site-nav.py',
           'check-site-links.py', 'check-site-build.py')


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

    def __init__(self, base: pathlib.Path, *, section_edits=None, script_edits=None, ext_edits=None):
        self.base = base
        base.mkdir(parents=True, exist_ok=True)
        src = VERIFY.read_text()
        self.sections = {'md': cut(src, SECTION_MD), 'nav': cut(src, SECTION_NAV), 'site': cut(src, SECTION_SITE)}
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
        self.site_copy = base / 'site-copy'
        shutil.copytree(REPO / 'maintenance' / 'site', self.site_copy, ignore=shutil.ignore_patterns('__pycache__', 'requirements*'))
        for name, (old, new) in (ext_edits or {}).items():
            body = (self.site_copy / name).read_text()
            if body.count(old) != 1:
                raise SystemExit(f'FAIL  mutation anchor {old!r} occurs {body.count(old)} time(s) in maintenance/site/{name}')
            (self.site_copy / name).write_text(body.replace(old, new, 1))
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

    def py(self, script: str, *args, cwd=None):
        """Run one of the (possibly mutated) scripts directly. -> (exit status, stdout + stderr)"""
        p = subprocess.run([sys.executable, str(self.scripts / script), *map(str, args)], capture_output=True, text=True,
                           cwd=cwd, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        return p.returncode, ANSI.sub('', p.stdout + p.stderr)

    def run(self, key: str, root: pathlib.Path, *, env=None, inject=None, pre='', post=''):
        """Run section `key` in `root`. -> (exit status, output without colours, HARD_FAILS)"""
        text = self.sections[key]
        if inject:
            assert text.count(inject[0]) == 1, f'the injection site occurs {text.count(inject[0])} time(s)'
            text = text.replace(inject[0], inject[1], 1)
        script = prelude() + pre + text + post + 'echo "HARD_FAILS=$HARD_FAILS"\n'
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



# ============================== part 3: check-site-links.py on planted HTML ==============================

GH = 'https://github.com/inkthorne/hytale-modding-handbook'
SITE_URL = 'https://inkthorne.github.io/hytale-modding-handbook/'
REF = 'REFTOKEN'
GH_PATHS = ['CLAUDE.md', 'examples/ui/A.java', 'examples/ui/B.java', 'examples/ui/C.java', 'examples/events/',
            'examples/events/D.java', 'examples/custom-food/', 'examples/commands/E.java', 'examples/inventory/F.java']

CASE_LINKS = {
    'healthy': 'links: a built site whose links all resolve passes, with every figure printed',
    'dead_file': 'links: a link to a page the build did not write FAILs naming page and target',
    'dead_frag': 'links: a #fragment that is no id in its target page FAILs',
    'self_frag': 'links: a #fragment on the page itself is checked too',
    'name_attr': 'links: an <a name=...> is an anchor as well as an id',
    'frag_css': 'links: a fragment on a target that is not HTML is not looked up',
    'dir_ok': 'links: dir/ resolves to dir/index.html, and a dead dir/ FAILs',
    'asset': 'links: a missing image, script or stylesheet FAILs',
    'root_rel': 'links: a root-relative link outside the site\'s path FAILs, the site\'s own path is the site',
    'abs_site': 'links: an absolute URL under site_url is checked as a page, a dead one FAILs',
    'offsite': 'links: off-site links, mailto: and javascript: are counted and never looked up',
    'escape': 'links: a link out of the built directory FAILs',
    'query': 'links: a query string does not stop a link resolving, a percent-encoded path is decoded',
    'blob_ok': 'links: a GitHub blob link to an existing file is clean and counted as rewritten',
    'blob_dir': 'links: a blob link to a directory FAILs',
    'tree_file': 'links: a tree link to a file FAILs',
    'gh_dead': 'links: a GitHub link to a path that is not in the repository FAILs',
    'gh_ref': 'links: a GitHub link at another ref is checked for its path and not counted as rewritten',
    'gh_malformed': 'links: a blob/tree link of this repository with no ref and path FAILs',
    'md_count': 'links: the rewritten links to .md files are counted',
    'floor_pages': 'links: fewer than 79 pages is a FAIL whatever else is true',
    'floor_internal': 'links: 0 internal links is a FAIL',
    'floor_rewritten': 'links: fewer than 9 rewritten links is a FAIL',
    'anchors_ok': 'links: every anchor check-links computes for a docs page is a heading id of its built page',
    'anchors_missing': 'links: an anchor with no heading id in the built page FAILs naming the nearest built id',
    'anchors_nonheading': 'links: an id on a non-heading element is not a heading id',
    'anchors_nopage': 'links: a docs page with no built page FAILs',
    'anchors_zero': 'links: a cross-check that read no docs page FAILs',
    'nodir': 'links: a site directory that does not exist exits 2',
}


def page_html(title: str, body: str = '', head: bool = True) -> str:
    head_links = '<link rel="stylesheet" href="assets/s.css"><script src="assets/j.js"></script>' if head else ''
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>{head_links}</head>'
            f'<body><a href="#__skip" id="__skip">skip</a><h1 id="{title}">{title}</h1>{body}</body></html>\n')


def gh_link(path: str, kind: str | None = None, ref: str = REF) -> str:
    kind = kind or ('tree' if path.endswith('/') else 'blob')
    return f'<a href="{GH}/{kind}/{ref}/{path.rstrip("/")}">g</a>'


def home_body(rewritten: int = 9, ref: str = REF) -> str:
    return ''.join(gh_link(p, ref=ref) for p in GH_PATHS[:rewritten]) + '<a href="a.html#one">a</a><a href="b.html">b</a>'


def make_site(root: pathlib.Path, *, n_pages=79, rewritten=9, edits: dict | None = None, home_extra='', ref: str = REF):
    """A small built site: index.html (with `rewritten` GitHub links at REF), a.html and b.html (the pages of the
    docs corpus), padding pages up to `n_pages` html files, assets. `edits` replaces or adds files, a value of
    None removes one; `home_extra` is appended to the home page's body."""
    site = root / 'site'
    (site / 'assets').mkdir(parents=True)
    (site / 'assets' / 's.css').write_text('body{}')
    (site / 'assets' / 'j.js').write_text('//')
    pages = {'index.html': page_html('home', home_body(rewritten, ref) + home_extra),
             'a.html': page_html('a', '<h2 id="one">One</h2><h2 id="one-1">One again</h2><a href="index.html">home</a>'),
             'b.html': page_html('b', '<a href="index.html">home</a>')}
    k = 0
    while len(pages) < n_pages:
        k += 1
        pages[f'pad{k:02d}.html'] = page_html(f'pad{k}', '<a href="index.html">home</a>')
    for name, html in (edits or {}).items():
        if html is None:
            pages.pop(name, None)
        else:
            pages[name] = html
    for name, html in pages.items():
        f = site / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html)
    return site


def make_repo(root: pathlib.Path, extra_docs=()):
    repo = root / 'repo'
    for rel in ('CLAUDE.md', 'examples/ui/A.java', 'examples/ui/B.java', 'examples/ui/C.java', 'examples/events/D.java',
                'examples/custom-food/pack.json', 'examples/commands/E.java', 'examples/inventory/F.java'):
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('x')
    (repo / 'docs').mkdir(exist_ok=True)
    (repo / 'docs' / 'a.md').write_text('# a\n\n## One\n\n## One\n')     # anchors: a, one, one-1
    (repo / 'docs' / 'b.md').write_text('# b\n')                          # anchors: b
    for name in extra_docs:
        (repo / 'docs' / name).write_text('# extra\n')
    return repo


def links_cases(w: World) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}
    n = [0]

    def run(*, docs=False, extra_docs=(), docs_dir=None, site_arg=None, ref=REF, flags=(), **site_kw):
        n[0] += 1
        root = w.base / f'links-{n[0]}'
        root.mkdir()
        repo = make_repo(root, extra_docs)
        site = site_arg or make_site(root, **site_kw)
        args = [site, '--repo', repo, '--ref', ref, '--site-url', SITE_URL, *flags]
        if docs or docs_dir:
            args += ['--docs', docs_dir or repo / 'docs']
        return w.py('check-site-links.py', *args)

    def verdict(key, got, *, rc, must=(), must_not=()):
        code, out = got
        pr = res.setdefault(CASE_LINKS[key], [])
        if code != rc:
            pr.append(f'exit {code}, wanted {rc}: {out[-300:]!r}')
        pr += [f'missing {m!r}' for m in must if m not in out]
        pr += [f'unexpected {m!r}' for m in must_not if m in out]

    # healthy: the exact SITE line (the figures of the planted site: 79 pages, one a.html#one link, 9 GitHub links)
    verdict('healthy', run(), rc=0, must=(f'SITE 79 page(s) parsed, 317 internal link(s) resolved (80 with a fragment), '
                                           f'9 off-site link(s) counted, not fetched, 9 rewritten GitHub link(s) at {REF} (1 to .md files)',))
    X = lambda body: dict(home_extra=body)
    verdict('dead_file', run(**X('<a href="ghost.html">g</a>')), rc=1,
            must=('FAIL  index.html: a ghost.html -> no such file in the built site (ghost.html)',))
    verdict('dead_frag', run(**X('<a href="a.html#nope">g</a>')), rc=1,
            must=("FAIL  index.html: a a.html#nope -> no element with id 'nope' in a.html",))
    verdict('self_frag', run(**X('<a href="#nope">g</a><a href="#home">h</a>')), rc=1,
            must=("index.html: a #nope -> no element with id 'nope' in index.html",), must_not=("'home'",))
    verdict('name_attr', run(edits={'a.html': page_html('a', '<h2 id="one">One</h2><a name="old-anchor"></a>')}, **X('<a href="a.html#old-anchor">g</a>')), rc=0)
    verdict('frag_css', run(**X('<a href="assets/s.css#nothing">g</a>')), rc=0)
    verdict('dir_ok', run(edits={'sub/index.html': page_html('sub', head=False)}, **X('<a href="sub/">s</a>')), rc=0)
    verdict('dir_ok', run(**X('<a href="nosub/">s</a>')), rc=1, must=('nosub/ -> no such file in the built site (nosub/index.html)',))
    verdict('asset', run(**X('<img src="assets/missing.png"><script src="assets/missing.js"></script>'
                             '<link rel="stylesheet" href="assets/missing.css">')), rc=1,
            must=('img assets/missing.png', 'script assets/missing.js', 'link assets/missing.css'))
    verdict('root_rel', run(**X('<a href="/elsewhere/x.html">e</a>')), rc=1,
            must=('index.html: a /elsewhere/x.html is root-relative; the site is served from a sub-path',))
    verdict('root_rel', run(**X('<a href="/hytale-modding-handbook/a.html#one">e</a>')), rc=0)
    verdict('abs_site', run(**X(f'<a href="{SITE_URL}a.html#one">ok</a><a href="{SITE_URL}ghost.html">dead</a>')), rc=1,
            must=('index.html: a ghost.html -> no such file in the built site (ghost.html)',), must_not=('a.html#one ->',))
    verdict('offsite', run(**X('<a href="https://example.invalid/x">e</a><a href="mailto:a@b.invalid">m</a>'
                               '<a href="javascript:void(0)">j</a>')), rc=0, must=('10 off-site link(s) counted, not fetched',))
    verdict('escape', run(**X('<a href="../../outside.html">o</a>')), rc=1,
            must=('index.html: a ../../outside.html -> no such file in the built site',))
    verdict('query', run(edits={'my page.html': page_html('mp')}, **X('<a href="a.html?x=1#one">q</a><a href="my%20page.html">p</a>')), rc=0)

    verdict('blob_ok', run(**X(gh_link('examples/ui/A.java'))), rc=0, must=(f'10 rewritten GitHub link(s) at {REF}',))
    verdict('blob_dir', run(**X(gh_link('examples/ui', 'blob'))), rc=1,
            must=("names 'examples/ui', which is not a file in the repository",))
    verdict('tree_file', run(**X(gh_link('examples/ui/A.java', 'tree'))), rc=1,
            must=("names 'examples/ui/A.java', which is not a directory in the repository",))
    verdict('gh_dead', run(**X(gh_link('examples/ghost/G.java'))), rc=1,
            must=("names 'examples/ghost/G.java', which is not a file in the repository",))
    verdict('gh_ref', run(**X(gh_link('examples/ui/A.java', ref='main'))), rc=0, must=('9 rewritten GitHub link(s)',))
    verdict('gh_ref', run(**X(gh_link('examples/ghost.java', ref='main'))), rc=1, must=("names 'examples/ghost.java'",))
    verdict('gh_malformed', run(**X(f'<a href="{GH}/blob/">g</a>')), rc=1,
            must=(f'is not of the form {GH}/(blob|tree)/<ref>/<path>',))
    verdict('md_count', run(**X(gh_link('CLAUDE.md'))), rc=0, must=(f'10 rewritten GitHub link(s) at {REF} (2 to .md files)',))

    verdict('floor_pages', run(n_pages=78), rc=1, must=('only 78 page(s) were parsed, floor is 79',))
    # no internal link anywhere: every page is bare (no head links) and the home page holds only GitHub links,
    # so the rewritten floor is met and only the internal-links floor can fire
    nolink = lambda t: f'<!doctype html><html><head><title>{t}</title></head><body><h1 id="{t}">{t}</h1></body></html>\n'
    bare = {name: nolink(name[:-5]) for name in ['a.html', 'b.html'] + [f'pad{k:02d}.html' for k in range(1, 77)]}
    bare['index.html'] = nolink('home').replace('</h1>', '</h1>' + home_body(9).split('<a href="a.html')[0])
    verdict('floor_internal', run(edits=bare, extra_docs=()), rc=1, must=('0 internal links were found',))
    verdict('floor_rewritten', run(rewritten=8), rc=1, must=(f'8 link(s) were rewritten to GitHub at {REF}, floor is 9',))

    # the --docs cross-check
    verdict('anchors_ok', run(docs=True), rc=0, must=('ANCHORS 4 heading anchor(s) of 2 docs page(s)',))
    verdict('anchors_missing', run(docs=True, edits={'a.html': page_html('a', '<h2 id="one">One</h2>')}), rc=1,
            must=("docs/a.md: anchor 'one-1' (check-links) is not a heading id of a.html (nearest built id: one)",))
    verdict('anchors_nonheading', run(docs=True, edits={'a.html': page_html('a', '<h2 id="x">x</h2><div id="one">d</div><div id="one-1">d</div>')}), rc=1,
            must=("anchor 'one' (check-links) is not a heading id of a.html", "anchor 'one-1' (check-links) is not a heading id of a.html"))
    verdict('anchors_nopage', run(docs=True, extra_docs=('zzz.md',)), rc=1, must=('docs/zzz.md: no built page zzz.html',))
    n[0] += 1
    empty = w.base / f'links-empty-docs-{n[0]}'
    empty.mkdir()
    verdict('anchors_zero', run(docs_dir=empty), rc=1, must=('the anchor cross-check read 0 pages or 0 anchors',))
    verdict('nodir', run(site_arg=w.base / 'no-such-site-dir'), rc=2, must=('is not a directory',))
    return res


# ============================== part 4: check-site-build.py on planted logs ==============================

CASE_BUILD = {
    'clean': 'build: a build with no issues passes and prints its figures',
    'explained': 'build: the ../CLAUDE.md warning (page does not exist, a link out of docs/ to a path in the repo) is explained',
    'rewritten_ok': 'build: --rewritten-md equal to the explained count passes',
    'rewritten_less': 'build: --rewritten-md below the explained count FAILs (a warning for a link the build did not rewrite)',
    'rewritten_more': 'build: --rewritten-md above the explained count FAILs (a rewritten link the build did not warn about)',
    'missing_page': 'build: a page that is really missing (the link resolves inside docs/) is unexplained',
    'outside_nopath': 'build: a link out of docs/ to a path the repository does not have is unexplained',
    'anchor': 'build: an anchor warning is unexplained, whatever the link',
    'unknown_kind': 'build: a warning of a kind never seen is unexplained',
    'not_a_target': 'build: a position that is not the target of a [text](target) link is unexplained',
    'shown_line': 'build: a source line the build shows that is not the line of docs/ is unexplained',
    'summary_less': 'build: an issue count below the warnings parsed FAILs',
    'summary_more': 'build: an issue count above the warnings parsed FAILs',
    'no_summary': 'build: a log with no issue count FAILs',
    'garbage': 'build: a line that is not a line of a zensical build FAILs, with the word Warning nowhere in it',
    'no_start': 'build: a log that does not start with "Build started" FAILs',
    'no_finish': 'build: a log with no "Build finished in" (the build died) FAILs',
    'unclosed': 'build: a warning block that never closes FAILs',
    'ansi': 'build: ANSI colour sequences are stripped (zensical ignores NO_COLOR for the marker line)',
    'nolog': 'build: a missing log exits 2',
    'nodocs': 'build: a --docs that is not a directory exits 2',
}

BUILD_CMD = 'CLAUDE.md'


def block(msg: str, file: str, line: int, col: int, src: str, marker_len: int = 12) -> str:
    return (f'Warning: {msg}\n    ╭─[ {file}:{line}:{col} ]\n    │\n {line} │ {src}\n    │ {" " * (col - 1)}{"─" * marker_len}\n'
            f'    │ {" " * (col - 1)}╰─ {msg}\n────╯\n')


def build_log(blocks: list[str], *, summary: str | None = '', start=True, finish='Build finished in 3.85s', tail=''):
    n = len(blocks)
    if summary == '':
        summary = 'No issues found' if n == 0 else (f'{n} issue found' if n == 1 else f'{n} issues found')
    return ('Build started\n' if start else '') + ''.join(blocks) + (summary + '\n' if summary else '') + (finish + '\n' if finish else '') + tail


def build_cases(w: World) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}
    n = [0]
    src_line = 'See [CLAUDE.md](../CLAUDE.md) for the details.'
    col = src_line.index('](') + 3        # 1-based column of the target's first character

    def run(log: str, *, docs_line=src_line, flags=(), nolog=False, nodocs=False):
        n[0] += 1
        root = w.base / f'build-{n[0]}'
        (root / 'docs').mkdir(parents=True)
        (root / 'docs' / 'page.md').write_text(f'# Page\n\n{docs_line}\n')
        (root / 'CLAUDE.md').write_text('x')
        (root / 'sub').mkdir()
        (root / 'sub' / 'inside.md').write_text('x')
        if not nolog:
            (root / 'build.log').write_text(log)
        return w.py('check-site-build.py', root / 'build.log', '--docs', root / ('docs' if not nodocs else 'nope'), '--repo', root, *flags)

    def verdict(key, got, *, rc, must=(), must_not=()):
        code, out = got
        pr = res.setdefault(CASE_BUILD[key], [])
        if code != rc:
            pr.append(f'exit {code}, wanted {rc}: {out[-300:]!r}')
        pr += [f'missing {m!r}' for m in must if m not in out]
        pr += [f'unexpected {m!r}' for m in must_not if m in out]

    good = block('page does not exist', 'page.md', 3, col, src_line)
    verdict('clean', run(build_log([])), rc=0, must=('BUILD 0 warning(s), 0 explained, 0 issue(s) reported, finished in 3.85s',), must_not=('FAIL',))
    verdict('explained', run(build_log([good])), rc=0, must=('BUILD 1 warning(s), 1 explained, 1 issue(s) reported',), must_not=('FAIL',))
    verdict('rewritten_ok', run(build_log([good]), flags=('--rewritten-md', '1')), rc=0, must=('1 explained',), must_not=('FAIL',))
    verdict('rewritten_less', run(build_log([good]), flags=('--rewritten-md', '0')), rc=1,
            must=('FAIL  1 warning(s) explained, but check-site-links.py counted 0 rewritten .md link(s)',))
    verdict('rewritten_more', run(build_log([]), flags=('--rewritten-md', '1')), rc=1,
            must=('FAIL  0 warning(s) explained, but check-site-links.py counted 1 rewritten .md link(s)',))
    inside = 'Read [other](inside.md) too.'
    verdict('missing_page', run(build_log([block('page does not exist', 'page.md', 3, inside.index('](') + 3, inside)]), docs_line=inside), rc=1,
            must=("unexplained warning at page.md:3:", "resolves inside docs/, so the page really is missing"))
    ghost = 'See [x](../ghost/Nope.java) here.'
    verdict('outside_nopath', run(build_log([block('page does not exist', 'page.md', 3, ghost.index('](') + 3, ghost)]), docs_line=ghost), rc=1,
            must=("resolves outside docs/ to", "which is not a path in the repository"))
    verdict('anchor', run(build_log([block('anchor does not exist', 'page.md', 3, col, src_line)])), rc=1,
            must=('FAIL  unexplained warning at page.md:3:' + str(col) + ': anchor does not exist',), must_not=('1 explained',))
    verdict('unknown_kind', run(build_log([block('something new', 'page.md', 3, col, src_line)])), rc=1,
            must=(f'FAIL  unexplained warning at page.md:3:{col}: something new',))
    verdict('not_a_target', run(build_log([block('page does not exist', 'page.md', 3, 1, src_line)])), rc=1,
            must=('the position is not the target of a [text](target) link',))
    verdict('shown_line', run(build_log([block('page does not exist', 'page.md', 3, col, 'a different line than the page has')])), rc=1,
            must=('the source line the build shows is not docs/page.md:3',))
    verdict('summary_less', run(build_log([good], summary='No issues found')), rc=1,
            must=('the build reports 0 issue(s) and 1 warning block(s) were parsed',))
    verdict('summary_more', run(build_log([good], summary='2 issues found')), rc=1,
            must=('the build reports 2 issue(s) and 1 warning block(s) were parsed',))
    verdict('no_summary', run(build_log([], summary=None)), rc=1, must=('the build printed no issue count',))
    verdict('garbage', run(build_log([], tail='Error: could not read the thing\n')), rc=1,
            must=("is not a line of a zensical build",), must_not=('Warning',))
    verdict('no_start', run(build_log([], start=False)), rc=1, must=('"Build started" appears 0 time(s), not once',))
    verdict('no_finish', run(build_log([], finish='')), rc=1, must=('"Build finished in ..." appears 0 time(s), not once: the build did not finish',))
    verdict('unclosed', run(build_log([good.replace('────╯\n', '')])), rc=1, must=('a warning block that never closed',))
    verdict('ansi', run(re.sub(r'(Warning:)', '\x1b[33m\\1\x1b[0m', build_log([good]))), rc=0, must=('1 explained',), must_not=('FAIL',))
    verdict('nolog', run('', nolog=True), rc=2, must=('cannot read the build log',))
    verdict('nodocs', run(build_log([]), nodocs=True), rc=2, must=('is not a directory',))
    return res


# ============================== part 5: the site-build section, with a stub in place of zensical ==============================

SITE_REF = 'verify-docs-ref'

STUB = '''#!/usr/bin/env bash
# stands in for `python -m zensical build --clean`: records how it was called, copies a planted site into ./site and
# prints a planted log. STUB_RECORD, STUB_SITE, STUB_LOG and STUB_RC come from the fixture.
echo "$PWD" > "$STUB_RECORD/cwd"; echo "${HANDBOOK_REF:-}" > "$STUB_RECORD/ref"; echo "${PYTHONPATH:-}" > "$STUB_RECORD/pythonpath"
echo "$*" > "$STUB_RECORD/args"; echo "${NO_COLOR:-}" > "$STUB_RECORD/no_color"
[ -n "${STUB_SITE:-}" ] && cp -R "$STUB_SITE" ./site
cat "$STUB_LOG"
exit "${STUB_RC:-0}"
'''

CASE_SITE = {
    'healthy': 'site: a clean stubbed build passes, naming pages, seconds, warnings and explained',
    'called': 'site: zensical is run as `-m zensical build --clean` in a copy of the tree, with HANDBOOK_REF, PYTHONPATH and NO_COLOR set',
    'nopollute': 'site: nothing is written into the repository, and the temp dir is gone when the section ends',
    'rc': 'site: a build that exits non-zero FAILs and says so',
    'few_html': 'site: fewer than 79 .html files written FAILs naming the count',
    'dead_link': 'site: a dead link in the built site FAILs with the checker\'s line',
    'unexplained': 'site: a warning that is not the explained one FAILs by name',
    'issues': 'site: an issue count that differs from the warnings parsed FAILs',
    'rewritten': 'site: an explained warning with no rewritten .md link in the built pages FAILs',
    'garbage': 'site: a build whose output has a line outside the grammar FAILs',
    'no_venv': 'site: a missing venv is one WARN and nothing else runs',
    'no_url': 'site: a zensical.toml with no site_url is a FAIL, nothing built',
    'not_flat': 'site: a .md below docs/ is a FAIL naming it, nothing built',
    'tmp_inside': 'site: a TMPDIR inside the repository is a FAIL naming it, nothing built',
    'mktemp': 'site: a TMPDIR that cannot be used is its own FAIL, nothing built',
    'exit_trap': 'site: an exit inside the section still removes the temp dir (the EXIT trap)',
}


def site_cases(w: World) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}
    n = [0]
    TRAP = re.search(r"^trap .*EXIT$", VERIFY.read_text(), re.M).group(0)
    PRE = f'SITE_TMP=""\n{TRAP}\n'

    def run(*, log=None, rc=0, site_edits=None, rewritten=9, n_pages=79, files=None, drop=(), tmpdir='ok', py='stub', env=None, inject=None,
            rewritten_md=True):
        n[0] += 1
        root = w.root('site', 'site-base', files, drop)
        work = w.base / f'site-work-{n[0]}'
        work.mkdir()
        record = work / 'record'
        record.mkdir()
        tmp = work / 'tmp'
        tmp.mkdir()
        edits = dict(site_edits or {})
        site = make_site(work, n_pages=n_pages, rewritten=rewritten, ref=SITE_REF, edits=edits)
        if not rewritten_md:
            # swap the CLAUDE.md link for a file link, so the built pages hold no rewritten .md link
            idx = site / 'index.html'
            idx.write_text(idx.read_text().replace('/blob/' + SITE_REF + '/CLAUDE.md', '/blob/' + SITE_REF + '/examples/ui/A.java'))
        stub = work / 'stub-zensical'
        stub.write_text(STUB)
        stub.chmod(0o755)
        line = 'See [CLAUDE.md](../CLAUDE.md) for the details.'
        explained = block('page does not exist', 'b.md', 3, line.index('](') + 3, line)
        logtext = log if log is not None else build_log([explained])
        (work / 'build.log').write_text(logtext)
        e = {'HANDBOOK_SITE_PY': str(stub) if py == 'stub' else py, 'STUB_RECORD': str(record), 'STUB_SITE': str(site),
             'STUB_LOG': str(work / 'build.log'), 'STUB_RC': str(rc), 'TMPDIR': {'ok': str(tmp), 'inside': str(root / 'tmpin'),
                                                                                  'missing': str(work / 'no-such-tmp')}[tmpdir]}
        if tmpdir == 'inside':
            (root / 'tmpin').mkdir()
        e.update(env or {})
        # the real trap and an empty SITE_TMP before it, as the drift section sets them in verify-docs.sh
        post = ('echo "SITE_TMP_AFTER_SECTION=$([ -d "${SITE_TMP:-}" ] && echo present || echo gone)"\n'
                'echo "SITE_TMP_CLEARED=$([ -z "${SITE_TMP:-}" ] && echo yes || echo no)"\n')
        code, out, h = w.run('site', root, env=e, inject=inject, pre=PRE, post=post)
        left = len(list(tmp.iterdir())) if tmp.exists() else -1
        return dict(code=code, out=out, hf=h, root=root, record=record, tmp=tmp, left=left, work=work)

    def v(key, r, *, hf, must=(), must_not=(), left=0, called=None):
        pr = res.setdefault(CASE_SITE[key], [])
        if r['hf'] != hf:
            pr.append(f'HARD_FAILS {r["hf"]}, wanted {hf}: {lines(r["out"])[-4:]!r}')
        pr += [f'missing {m!r}' for m in must if m not in r['out']]
        pr += [f'unexpected {m!r}' for m in must_not if m in r['out']]
        if left is not None and r['left'] != left:
            pr.append(f'{r["left"]} entr(ies) left in TMPDIR, wanted {left}')

    def rec(r, name):
        f = r['record'] / name
        return f.read_text().strip() if f.exists() else None

    r = run()
    v('healthy', r, hf=0, must=('INFO  SITE 79 page(s) parsed', 'INFO  ANCHORS 4 heading anchor(s) of 2 docs page(s)'), must_not=('  FAIL  ', 'WARN'))
    m = re.search(r'^  PASS  79 page\(s\) built in [0-9]+\.[0-9] s; 1 warning\(s\), 1 explained$', r['out'], re.M)
    if not m:
        res[CASE_SITE['healthy']].append(f'no PASS line of the form "79 page(s) built in T s; 1 warning(s), 1 explained": {lines(r["out"])!r}')
    pr = res.setdefault(CASE_SITE['called'], [])
    tmp_root = str(r['tmp'])
    cwd = rec(r, 'cwd') or ''
    if not cwd.startswith(tmp_root) or cwd.startswith(str(r['root'])):
        pr.append(f'zensical ran in {cwd!r}, wanted a copy under {tmp_root} and not in the tree {r["root"]}')
    for name, want in (('args', '-m zensical build --clean'), ('ref', SITE_REF), ('pythonpath', 'maintenance/site'), ('no_color', '1')):
        if rec(r, name) != want:
            pr.append(f'{name}: {rec(r, name)!r}, wanted {want!r}')
    pr = res.setdefault(CASE_SITE['nopollute'], [])
    if (r['root'] / 'site').exists() or (r['root'] / '.cache').exists():
        pr.append('the section wrote site/ or .cache/ into the tree')
    if r['left'] != 0:
        pr.append(f'{r["left"]} entr(ies) left in TMPDIR')
    if 'SITE_TMP_AFTER_SECTION=gone' not in r['out']:
        pr.append('the section left its temp dir in place when it ended')
    if 'SITE_TMP_CLEARED=yes' not in r['out']:
        pr.append('the section left SITE_TMP set to the removed path (the EXIT trap would act on it)')

    v('rc', run(rc=1), hf=1, must=('FAIL  zensical build exited 1:',), must_not=('PASS',))
    v('few_html', run(n_pages=78), hf=2, must=('FAIL  the build wrote 78 .html file(s), at least 79 are expected (78 docs pages and 404.html)',), must_not=('PASS',))
    v('dead_link', run(site_edits={'index.html': page_html('home', home_body(9, SITE_REF) + '<a href="ghost.html">g</a>')}), hf=1,
      must=('FAIL  check-site-links.py found problems in the built site (exit 1):', 'ghost.html -> no such file in the built site'), must_not=('PASS',))
    extra = block('page does not exist', 'a.md', 1, 3, '# a')
    v('unexplained', run(log=build_log([block('page does not exist', 'b.md', 3, 'See [CLAUDE.md](../CLAUDE.md) for the details.'.index('](') + 3,
                                              'See [CLAUDE.md](../CLAUDE.md) for the details.'), extra])), hf=1,
      must=('FAIL  the build output is not a clean zensical build (check-site-build.py exit 1):', 'unexplained warning at a.md:1:3'), must_not=('PASS',))
    line = 'See [CLAUDE.md](../CLAUDE.md) for the details.'
    v('issues', run(log=build_log([block('page does not exist', 'b.md', 3, line.index('](') + 3, line)], summary='3 issues found')), hf=1,
      must=('the build reports 3 issue(s) and 1 warning block(s) were parsed',), must_not=('PASS',))
    v('rewritten', run(rewritten_md=False), hf=1,
      must=('1 warning(s) explained, but check-site-links.py counted 0 rewritten .md link(s)',), must_not=('PASS',))
    v('garbage', run(log=build_log([], tail='Error: it broke\n')), hf=1, must=('is not a line of a zensical build',), must_not=('PASS',))

    r = run(py='/nonexistent/venv/bin/python')
    v('no_venv', r, hf=0, must=('WARN  skipped (no site venv: /nonexistent/venv/bin/python is not an executable;',), must_not=('PASS', '  FAIL  '))
    if rec(r, 'cwd') is not None:
        res[CASE_SITE['no_venv']].append('zensical ran although the venv was missing')
    nb = lambda r: [] if rec(r, 'cwd') is None else ['zensical ran']
    r = run(files={'zensical.toml': '[project]\nsite_name = "x"\n'})
    v('no_url', r, hf=1, must=('FAIL  the site build cannot run: zensical.toml has no site_url line',), must_not=('PASS',))
    res[CASE_SITE['no_url']] += nb(r)
    r = run(files={'docs/sub/x.md': '# x\n'})
    v('not_flat', r, hf=1, must=('FAIL  docs/ is not flat:', 'docs/sub/x.md'), must_not=('PASS',))
    res[CASE_SITE['not_flat']] += nb(r)
    r = run(tmpdir='inside')
    v('tmp_inside', r, hf=1, must=('FAIL  site build: TMPDIR (', 'inside the repository', 'nothing was built'), must_not=('PASS',), left=None)
    res[CASE_SITE['tmp_inside']] += nb(r)
    r = run(tmpdir='missing')
    v('mktemp', r, hf=1, must=('FAIL  site build: could not create a temporary directory (mktemp -d failed',), must_not=('PASS',), left=None)
    res[CASE_SITE['mktemp']] += nb(r)

    # an exit inside the section, after the temp dir exists: only the EXIT trap can remove it
    mk = 'SITE_T0="$(date +%s%N)"\n'
    r = run(inject=(mk, 'echo work > "$SITE_TMP/x"; exit 7\n'))
    pr = res.setdefault(CASE_SITE['exit_trap'], [])
    if r['code'] != 7:
        pr.append(f'harness exit {r["code"]}, wanted 7')
    if r['left'] != 0:
        pr.append(f'{r["left"]} entr(ies) left in TMPDIR: the trap did not remove SITE_TMP')
    return res



# ============================== part 6: the extension, under the site venv ==============================

def site_python():
    """The venv python the extension's cases need, or None (then the part is skipped, loudly)."""
    py = os.environ.get('HANDBOOK_SITE_PY') or str(pathlib.Path.home() / '.cache' / 'handbook-site' / 'venv' / 'bin' / 'python')
    if not os.access(py, os.X_OK):
        return None
    ok = subprocess.run([py, '-c', 'import markdown, pymdownx'], capture_output=True)
    return py if ok.returncode == 0 else None


EXT_PY = site_python()

CASE_EXT = {k: f'ext: {v}' for k, v in {
    'link_blob': '../CLAUDE.md goes to github.com blob at the ref',
    'link_tree': 'a trailing slash is a tree, and the fragment is kept',
    'link_dir': 'an existing directory without a trailing slash is a tree too',
    'link_frag': 'a file keeps its fragment and is a blob',
    'link_ref': 'the ref is the configured one',
    'link_alone': 'inside docs/, a URL, a fragment and a path out of the repository are left alone',
    'anchor_dup': 'a duplicate heading is x-1, x-2 (GitHub), not x_1',
    'anchor_slug': 'the slug is the character rule',
    'list_bullet': 'a bullet straight after a paragraph line starts a list',
    'list_ordered': '1. starts a list after a paragraph line, 2. does not',
    'list_quote': 'a list after a paragraph line inside a blockquote too',
    'list_fence': 'a code fence is left exactly as written',
    'list_after_fence': 'an item after a closed fence stays in the list',
    'list_not_start': 'a thematic break and a line of html are not list starts (a pin: Python-Markdown handles both)',
    'list_loose': 'a loose list stays one list',
    'list_nested': 'a nested item at four spaces nests',
    'quote_two': 'two > blocks with a blank line between are two boxes',
    'quote_one': 'a > line with nothing after it keeps one box',
    'html_text': '<GameMode, Settings> is text, <b> is a tag',
    'escape_quote': '\\" prints the quote without its backslash',
    'base_required': 'an extension configured without the repository URL refuses to load'}.items()}


def ext_cases(w: World) -> dict[str, list[str]]:
    tree = w.base / 'ext-tree'
    (tree / 'maintenance').mkdir(parents=True)
    (tree / 'examples').mkdir()
    shutil.copytree(w.site_copy, tree / 'maintenance' / 'site')
    (tree / 'maintenance' / 'scripts').mkdir()
    for name in ('check-links.py', 'doc_fences.py'):
        shutil.copy2(w.scripts / name, tree / 'maintenance' / 'scripts' / name)
    p = subprocess.run([EXT_PY, str(tree / 'maintenance' / 'site' / 'check-extension.py')], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    seen = {}
    for l in p.stdout.splitlines():
        m = re.match(r'^CASE (\S+) (ok|FAIL)\b(.*)$', l)
        if m:
            seen[m.group(1)] = [] if m.group(2) == 'ok' else [m.group(3).strip()[:300]]
    crash = [] if seen else [f'the extension failed to load or run: {(p.stderr or p.stdout)[-300:]!r}']
    return {label: seen.get(k, crash or ['the case did not run']) for k, label in CASE_EXT.items()}


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

# ---- check-site-links.py ----
LNK = 'check-site-links.py'
mut('a missing page is not a finding', ('script', LNK), "            if target not in files:", '            if False:',
    ['dead_file'], ['abs_site', 'asset', 'dead_file', 'dir_ok', 'escape'], part='links')
mut('a fragment is not looked up', ('script', LNK), "if frag and target.endswith('.html'):", 'if False:',
    ['dead_frag'], ['dead_frag', 'healthy', 'self_frag'], part='links')
mut('a fragment is looked up in any target, css included', ('script', LNK), "if frag and target.endswith('.html'):", 'if frag:',
    ['frag_css'], ['frag_css'], part='links')
mut('an <a name> is not an anchor', ('script', LNK), "        for k in ('id', 'name'):", "        for k in ('id',):",
    ['name_attr'], ['name_attr'], part='links')
mut('a directory link is not resolved to its index', ('script', LNK), "if path.endswith('/') or (target not in files and f'{target}/index.html' in files):", 'if False:',
    ['dir_ok'], ['dir_ok'], part='links')
mut('img and script sources are not links', ('script', LNK), "'img': 'src', 'script': 'src', ", '',
    ['asset'], ['asset', 'healthy'], part='links')
mut('a root-relative link is never refused', ('script', LNK), "            if url.startswith('/'):", '            if False:',
    ['root_rel'], ['root_rel'], part='links')
mut('the site path is not stripped from a root-relative link', ('script', LNK), "            if site_path and url.startswith(site_path):", '            if False:',
    ['root_rel'], ['root_rel'], part='links')
mut('an absolute URL under site_url is off-site', ('script', LNK), "if site_url and url.startswith(site_url):", 'if False:',
    ['abs_site'], ['abs_site'], part='links')
mut('off-site links are not counted', ('script', LNK), '                    offsite += 1', '                    offsite += 0',
    ['offsite'], ['healthy', 'offsite'], part='links')
mut('mailto: and javascript: are looked up as files', ('script', LNK), "            elif sp.scheme:\n                other += 1                  # mailto:, javascript:, data:, tel:\n                continue\n", '',
    ['offsite'], ['offsite'], part='links')
mut('a query string stays on the path', ('script', LNK), "path = urllib.parse.unquote(sp.path)", "path = urllib.parse.unquote(sp.path + ('?' + sp.query if sp.query else ''))",
    ['query'], ['query'], part='links')
mut('a percent-encoded path is not decoded', ('script', LNK), "path = urllib.parse.unquote(sp.path)", "path = sp.path",
    ['query'], ['query'], part='links')
mut('a GitHub link is not checked against the repository', ('script', LNK), "                        if not ok:", "                        if False:",
    ['blob_dir'], ['blob_dir', 'gh_dead', 'gh_ref', 'tree_file'], part='links')
mut('blob and tree are not told apart', ('script', LNK), "ok = target.is_file() if kind == 'blob' else target.is_dir()", 'ok = target.exists()',
    ['blob_dir'], ['blob_dir', 'tree_file'], part='links')
mut('every GitHub link counts as rewritten, whatever its ref', ('script', LNK), "                        if ref == a.ref:", '                        if True:',
    ['gh_ref'], ['gh_ref'], part='links')
mut('a GitHub link at another ref is not checked for its path', ('script', LNK), "                        if not ok:", "                        if not ok and ref == a.ref:",
    ['gh_ref'], ['gh_ref'], part='links')
mut('a malformed blob/tree link is let through', ('script', LNK), "                    elif url.startswith(repo_url + '/blob/') or url.startswith(repo_url + '/tree/'):", '                    elif False:',
    ['gh_malformed'], ['gh_malformed'], part='links')
mut('.md targets among the rewritten are not counted', ('script', LNK), "rewritten_md += path.endswith('.md')", 'rewritten_md += 0',
    ['md_count'], ['healthy', 'md_count'], part='links')
mut('the page floor is removed', ('script', LNK), '    if len(htmls) < a.min_pages:', '    if False:',
    ['floor_pages'], ['floor_pages'], part='links')
mut('the internal-link floor is removed', ('script', LNK), '    if internal == 0:', '    if False:',
    ['floor_internal'], ['floor_internal'], part='links')
mut('the rewritten floor is removed', ('script', LNK), '    if rewritten < a.min_rewritten:', '    if False:',
    ['floor_rewritten'], ['floor_rewritten'], part='links')
mut('the anchor cross-check looks anywhere, not in headings', ('script', LNK), 'have = page(built).heading_ids', 'have = page(built).ids',
    ['anchors_nonheading'], ['anchors_nonheading'], part='links')
mut('the anchor cross-check is skipped', ('script', LNK), '    if a.docs:\n', '    if False:\n',
    ['anchors_ok', 'anchors_missing'], ['anchors_missing', 'anchors_nonheading', 'anchors_nopage', 'anchors_ok', 'anchors_zero'], part='links')
mut('a docs page with no built page is let through', ('script', LNK), "            if built not in files:\n                fails.append(f'docs/{md.name}: no built page {built}')\n                continue\n", '',
    ['anchors_nopage'], ['anchors_nopage'], part='links')
mut('a cross-check that read nothing is let through', ('script', LNK), "        if n_pages == 0 or n_anchors == 0:", '        if False:',
    ['anchors_zero'], ['anchors_zero'], part='links')
mut('a missing site directory is not refused', ('script', LNK), '    if not site.is_dir():', '    if False:',
    ['nodir'], ['nodir'], part='links')

# ---- check-site-build.py ----
BLD = 'check-site-build.py'
mut('an unexplained message is explained', ('script', BLD), "        if b['msg'] != 'page does not exist':", '        if False:',
    ['anchor', 'unknown_kind'], ['anchor', 'unknown_kind'], part='build')
mut('a link that resolves inside docs/ is explained', ('script', BLD), "        if dest is None or dest == docs_abs or docs_abs in dest.parents:", '        if dest is None:',
    ['missing_page'], ['missing_page'], part='build')
mut('a path outside docs/ need not exist in the repository', ('script', BLD), "        if repo_abs not in dest.parents or not dest.exists():", '        if repo_abs not in dest.parents:',
    ['outside_nopath'], ['outside_nopath'], part='build')
mut('a position that is not a link target is explained', ('script', BLD), "        if col < 3 or text[col - 3:col - 1] != '](':", '        if False:',
    ['not_a_target'], ['not_a_target'], part='build')
mut('the source line the build shows is not compared', ('script', BLD), "        if shown and shown[0].rstrip() != text.rstrip():", '        if False:',
    ['shown_line'], ['shown_line'], part='build')
mut('the issue count is not compared with the warnings', ('script', BLD), '    elif summary != len(blocks):', '    elif False:',
    ['summary_less', 'summary_more'], ['summary_less', 'summary_more'], part='build')
mut('a missing issue count is let through', ('script', BLD), '    if summary is None:', '    if False:',
    ['no_summary'], ['no_summary'], part='build')
mut('an unknown line is let through', ('script', BLD), "            fails.append(f'build output line {no}: {l!r} is not a line of a zensical build')", '            pass',
    ['garbage'], ['garbage'], part='build')
mut('"Build started" is not required', ('script', BLD), '    if started != 1:', '    if False:',
    ['no_start'], ['no_start'], part='build')
mut('"Build finished" is not required', ('script', BLD), '    if finished != 1:', '    if False:',
    ['no_finish'], ['no_finish'], part='build')
mut('an unclosed block is let through', ('script', BLD), '    if cur is not None:\n        fails.append', '    if False:\n        fails.append',
    ['unclosed'], ['unclosed'], part='build')
mut('ANSI sequences are not stripped', ('script', BLD), "lines = [ANSI.sub('', l).rstrip() for l in log.splitlines()]", 'lines = [l.rstrip() for l in log.splitlines()]',
    ['ansi'], ['ansi'], part='build')
mut('the rewritten count is not compared', ('script', BLD), '    if a.rewritten_md is not None and e != a.rewritten_md:', '    if False:',
    ['rewritten_less', 'rewritten_more'], ['rewritten_less', 'rewritten_more'], part='build')
mut('an unreadable log is not refused', ('script', BLD), "        print(f'  FAIL  cannot read the build log {a.log}: {e}')\n        return 2", "        print('x')\n        return 0",
    ['nolog'], ['nolog'], part='build')
mut('a docs dir that is not a directory is not refused', ('script', BLD), '    if not docs.is_dir():', '    if False:',
    ['nodocs'], ['nodocs'], part='build')

# ---- the site-build section ----
mut('the section does not read the build status', ('section', 'site'), '    if [ "$SITE_RC" -ne 0 ]; then', '    if false; then',
    ['rc'], ['rc'], part='site')
mut('the .html floor is removed', ('section', 'site'), '    if [ "$SITE_HTML" -lt 79 ]; then', '    if false; then',
    ['few_html'], ['few_html'], part='site')
mut('the link checker\'s status is not read', ('section', 'site'), '    if [ "$SITE_LRC" -ne 0 ]; then', '    if false; then',
    ['dead_link', 'few_html'], ['dead_link', 'few_html'], part='site')
mut('the warning judge\'s status is not read', ('section', 'site'), '    if [ "$SITE_WRC" -ne 0 ] || [ -z "$SITE_W" ]; then', '    if false; then',
    ['unexplained', 'issues', 'rewritten', 'garbage'], ['garbage', 'issues', 'rewritten', 'unexplained'], part='site')
mut('the rewritten .md count is not handed to the judge', ('section', 'site'), ' --rewritten-md "${SITE_REWRITTEN_MD:--1}"', '',
    ['rewritten'], ['rewritten'], part='site')
mut('a missing venv is not skipped', ('section', 'site'), 'if [ ! -x "$SITE_PY" ]; then', 'if false; then',
    ['no_venv'], ['no_venv'], part='site')
mut('a missing site_url is not refused', ('section', 'site'), 'elif [ -z "$SITE_URL" ]; then', 'elif false; then',
    ['no_url'], ['no_url'], part='site')
mut('docs/ need not be flat', ('section', 'site'), """elif [ -n "$(find docs -mindepth 2 -name '*.md' 2>/dev/null)" ]; then""", 'elif false; then',
    ['not_flat'], ['not_flat'], part='site')
mut('a TMPDIR inside the repository is allowed', ('section', 'site'), 'elif case "$SITE_TD/" in "$SITE_REPO"/*) true ;; *) false ;; esac; then', 'elif false; then',
    ['tmp_inside'], ['tmp_inside'], part='site')
mut('a failed mktemp is not read', ('section', 'site'), '  if [ -z "$SITE_TMP" ]; then', '  if false; then',
    ['mktemp'], ['mktemp'], part='site')
mut('the build runs in the tree, not in a copy', ('section', 'site'), '    ( cd "$SITE_TMP" && PYTHONPATH', '    ( cd "$SITE_REPO" && PYTHONPATH',
    ['called', 'nopollute'], ['called', 'dead_link', 'few_html', 'garbage', 'healthy', 'issues', 'nopollute', 'rc', 'rewritten', 'unexplained'], part='site')
mut('the build is not run with --clean', ('section', 'site'), 'build --clean )', 'build )',
    ['called'], ['called'], part='site')
mut('HANDBOOK_REF is not set', ('section', 'site'), 'HANDBOOK_REF="$SITE_REF" ', '',
    ['called'], ['called'], part='site')
mut('PYTHONPATH is not set', ('section', 'site'), 'PYTHONPATH=maintenance/site ', '',
    ['called'], ['called'], part='site')
mut('NO_COLOR is not set', ('section', 'site'), ' NO_COLOR=1 ', ' ',
    ['called'], ['called'], part='site')
mut('the section does not remove its temp dir', ('section', 'site'), '    rm -rf "$SITE_TMP"\n    SITE_TMP=""', '    SITE_TMP=""',
    ['healthy', 'nopollute'], ['dead_link', 'few_html', 'garbage', 'healthy', 'issues', 'nopollute', 'rc', 'rewritten', 'unexplained'], part='site')

# ---- the extension (skipped, and said so, without the site venv) ----
EXTM = 'handbook_md.py'
mut('the link rewrite is not registered', ('ext', EXTM), 'md.treeprocessors.register(Rewrite(md, base, self.getConfig("ref")), "handbook_rewrite", 1)', 'pass',
    ['link_blob'], ['link_blob', 'link_dir', 'link_frag', 'link_ref', 'link_tree'], part='ext')
mut('every rewritten link is a blob', ('ext', EXTM), 'is_dir = path.endswith("/") or (REPO / rel).is_dir()', 'is_dir = False',
    ['link_tree'], ['link_dir', 'link_tree'], part='ext')
mut('a directory without a trailing slash is a blob', ('ext', EXTM), 'is_dir = path.endswith("/") or (REPO / rel).is_dir()', 'is_dir = path.endswith("/")',
    ['link_dir'], ['link_dir'], part='ext')
mut('the fragment is dropped from a rewritten link', ('ext', EXTM), 'return url + (f"#{frag}" if frag else "")', 'return url',
    ['link_tree'], ['link_frag', 'link_tree'], part='ext')
mut('the configured ref is ignored', ('ext', EXTM), 'url = f"{self.base}/{\'tree\' if is_dir else \'blob\'}/{self.ref}/', 'url = f"{self.base}/{\'tree\' if is_dir else \'blob\'}/main/',
    ['link_ref'], ['link_blob', 'link_dir', 'link_frag', 'link_ref', 'link_tree'], part='ext')
mut('a link inside docs/ is rewritten too', ('ext', EXTM), 'if rel == "docs" or rel.startswith("docs/") or rel == ".." or rel.startswith("../"):', 'if rel == ".." or rel.startswith("../"):',
    ['link_alone'], ['link_alone'], part='ext')
mut('a path out of the repository is rewritten', ('ext', EXTM), 'if rel == "docs" or rel.startswith("docs/") or rel == ".." or rel.startswith("../"):', 'if rel == "docs" or rel.startswith("docs/"):',
    ['link_alone'], ['link_alone'], part='ext')
mut('a URL is rewritten as a path', ('ext', EXTM), 'or urllib.parse.urlsplit(href).scheme or href.startswith("//"):', ':',
    ['link_alone'], ['link_alone'], part='ext')
mut('a root-relative link is rewritten', ('ext', EXTM), 'if not href or href.startswith(("#", "/")) or', 'if not href or href.startswith(("#",)) or',
    ['link_alone'], ['link_alone'], part='ext')
mut('duplicate headings keep Python-Markdown\'s numbering', ('ext', EXTM), '_toc.unique = github_unique', 'pass',
    ['anchor_dup'], ['anchor_dup'], part='ext')
mut('the slug is not the character rule', ('ext', EXTM), '    return char_slug(text)', "    return text.lower().replace(' ', '-')",
    ['anchor_slug'], ['anchor_slug'], part='ext')
mut('the list-break preprocessor is not registered', ('ext', EXTM), 'md.preprocessors.register(ListBreaks(md), "handbook_list_breaks", 27)', 'pass',
    ['list_bullet'], ['list_after_fence', 'list_bullet', 'list_ordered', 'list_quote'], part='ext')
mut('code fences are not skipped by the list-break preprocessor', ('ext', EXTM), '            if no in fenced:\n                out.append(line)', '            if False:\n                out.append(line)',
    ['list_fence'], ['list_after_fence', 'list_fence'], part='ext')
mut('the quote prefix is lost on the inserted blank line', ('ext', EXTM), '                    out.append(prefix.rstrip())', "                    out.append('')",
    ['list_quote'], ['list_quote'], part='ext')
mut('any number starts a list after a paragraph line', ('ext', EXTM), 'ITEM = re.compile(r"^[ ]*(?:[*+-]|1\\.)[ ]+\\S")', 'ITEM = re.compile(r"^[ ]*(?:[*+-]|\\d+\\.)[ ]+\\S")',
    ['list_ordered'], ['list_ordered'], part='ext')
mut('an item after a closed fence gets no blank line', ('ext', EXTM), 'if (prev_text and not in_item) or was_fence:', 'if (prev_text and not in_item):',
    ['list_after_fence'], ['list_after_fence'], part='ext')
mut('a paragraph line before a list is not noticed', ('ext', EXTM), '                prev_text = not in_item\n', '                prev_text = False\n',
    ['list_bullet'], ['list_bullet', 'list_ordered', 'list_quote'], part='ext')
mut('adjacent blockquotes merge again', ('ext', EXTM), 'md.parser.blockprocessors.register(SeparateQuotes(md.parser), "quote", 20)', 'pass',
    ['quote_two'], ['quote_two'], part='ext')
mut('a quote with a bare > line is split', ('ext', EXTM), '        block = blocks.pop(0)\n        m = self.RE.search(block)\n        if m:\n            before', '        block = blocks.pop(0).replace("\\n>\\n", "\\n\\n>")\n        m = self.RE.search(block)\n        if m:\n            before',
    ['quote_one'], ['list_quote', 'quote_one'], part='ext')
mut('inline html is Python-Markdown\'s again', ('ext', EXTM), '        md.inlinePatterns.register(HtmlInlineProcessor("(" + _check_links.RAW_HTML.pattern + ")", md), "html", 90)\n', '',
    ['html_text'], ['html_text'], part='ext')
mut('the extra backslash escapes are not added', ('ext', EXTM), '        md.ESCAPED_CHARS.extend(c for c in "\\"$%\',/:;=?@^~" if c not in md.ESCAPED_CHARS)\n', '',
    ['escape_quote'], ['escape_quote'], part='ext')
mut('the ref comes from the environment only', ('ext', EXTM), 'self.getConfig("ref")), "handbook_rewrite"', 'os.environ.get("HANDBOOK_REF", "main")), "handbook_rewrite"',
    ['link_ref'], ['link_blob', 'link_dir', 'link_frag', 'link_ref', 'link_tree'], part='ext')
mut('the extension accepts a missing base', ('ext', EXTM), '        if not base:\n            raise ValueError', '        if False:\n            raise ValueError',
    ['base_required'], ['base_required'], part='ext')

PARTS = {'md': (CASE_MD, md_cases), 'nav': (CASE_NAV, nav_cases), 'links': (CASE_LINKS, links_cases),
         'build': (CASE_BUILD, build_cases), 'site': (CASE_SITE, site_cases)}
if EXT_PY:
    PARTS['ext'] = (CASE_EXT, ext_cases)


def apply_edit(where, old, new):
    """-> (section_edits, script_edits, ext_edits)"""
    kind, name = where
    return {'script': ({}, {name: (old, new)}, {}), 'section': ({name: (old, new)}, {}, {}), 'ext': ({}, {}, {name: (old, new)})}[kind]


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
        floor = MIN_CASES + (MIN_EXT_CASES if EXT_PY else 0)
        if len(res) < floor:
            print(f'  FAIL  {len(res)} case(s) ran, floor is {floor}. A fixture that examines nothing '
                  f'reports the same thing as one that passes.')
            return 1
        fails = {k: v for k, v in res.items() if v}
        for label in res:
            if a.verbose and not res[label]:
                print(f'  ok   {label}')
        print(f'\nFIXTURE {len(res)} case(s): {len(res) - len(fails)} passed, {len(fails)} failed'
              + ('' if EXT_PY else '; the extension part (21 cases, 23 mutations) was SKIPPED: no site venv at '
                 '$HANDBOOK_SITE_PY or ~/.cache/handbook-site (maintenance/scripts/site-env.sh creates it)'))
        for k, v in fails.items():
            print(f'  FAIL {k}: ' + '; '.join(v))
        rc = 1 if fails else 0
        if not a.mutations:
            return rc
        todo = {k: v for k, v in MUTATIONS.items() if v[3] in PARTS}
        mfloor = MIN_MUTATIONS + (MIN_EXT_MUTATIONS if EXT_PY else 0)
        if len(todo) < mfloor:
            print(f'  FAIL  {len(todo)} mutation(s) defined, floor is {mfloor}.')
            return 1
        if not any(k.startswith('IDENTITY') for k in MUTATIONS):
            print('  FAIL  no IDENTITY control in MUTATIONS')
            return 1
        print(f'\nMUTATIONS {len(todo)} defect(s) reintroduced, expected red set asserted exactly')

        def one(item):
            k, (label, (where, old, new, part, names, expect)) = item
            sec, scr, ext = apply_edit(where, old, new)
            mres = run_part(part, World(work / f'm{k}', section_edits=sec, script_edits=scr, ext_edits=ext))
            return label, part, names, expect, {c for c, v in mres.items() if v}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as pool:
            results = list(pool.map(one, enumerate(todo.items())))
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
