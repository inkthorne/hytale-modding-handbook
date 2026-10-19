#!/usr/bin/env python3
"""
Generate docs/llms.txt (https://llmstxt.org) so an AI tool can find the handbook's pages, in the order a reader
meets them, and the examples that go with them.

  python3 maintenance/scripts/generate-llms-txt.py > docs/llms.txt        # regenerate and commit
  python3 maintenance/scripts/generate-llms-txt.py --root DIR             # a tree other than this repository

WHAT IT READS, and nothing is typed into the output by hand except the summary sentences.
  * The groups are the sidebar's: README.md's `### ` categories under `## Documentation`, in README order, pages in
    README order. They are read with generate-site-nav.py's read_categories and checked with its generate(), imported
    rather than re-implemented, so llms.txt and the sidebar cannot disagree about which page is where.
  * Each page's title and description are its frontmatter. Home (docs/index.md) comes first, under `## Start here`.
  * The handbook's build is Home's `**Verified against Hytale X (build-N).**` paragraph, which check-home holds equal
    to README.md's. It must occur exactly once. (The first version took the minimum of every `Verified against N` in
    docs/*.md, which also matches prose: 02-structure.md:141 and commands.md:334 say it about something else.)
  * The examples are the tracked top-level directories of examples/ (`git ls-files`, the population of
    check-example-lists.py). Their Type and "What it demonstrates" are the cells of examples/README.md's table, read
    only when its header row is exactly HEADER below; rows are split on an unescaped `|` and keyed by the first
    cell's link destination, never by position.

EVERY LINK to a page is the rendered `.html` page, the form a person cites. One line says where the markdown source
of a page is, for a tool that wants fences and tables verbatim. No size is claimed for either: measured on the
site's own build, the text of commands.html is within 5% of commands.md (the sidebar costs 2.6-4.3 KB a page), and
raw markdown could not link the examples' directories.

EXIT 2, with nothing on stdout, when the output would be wrong, which is each of: no categories; a README link whose
page does not exist, or a page listed twice (generate-site-nav's problems); a docs page other than index.md that no
category lists; a listed page, or Home, with no frontmatter title or no description; Home's Verified-against
paragraph not found exactly once; examples/README.md's table header not exactly HEADER, a row that is not four
cells, links no example directory, repeats one, or has a Type other than Pack or Plugin; an example directory with
no row; no tracked example directory, or no git work tree to say. The problems are listed on stderr, all of them,
then the summary is not printed.

stderr carries `LLMS <categories> categories, <pages> pages, <examples> examples` on success: the denominator
verify-docs prints. `pages` is the number of page links in the output, Home included.
"""
from __future__ import annotations
import argparse, importlib.util, pathlib, posixpath, re, subprocess, sys, urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('generate_site_nav_for_llms', HERE / 'generate-site-nav.py')
NAV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NAV)

SITE = 'https://inkthorne.github.io/hytale-modding-handbook'
RAW = 'https://raw.githubusercontent.com/inkthorne/hytale-modding-handbook/main/docs'
REPO = 'https://github.com/inkthorne/hytale-modding-handbook'
HEADER = '| Example | Type | What it demonstrates | Commands |'
TYPES = ('Pack', 'Plugin')
STAMP = re.compile(r'\*\*Verified against Hytale ([0-9]+(?:\.[0-9]+)*) \(build-([0-9]+)\)\.\*\*')
FM = re.compile(r'\A---\n(.*?)\n---\n', re.S)
SEPARATOR = re.compile(r'^\|[ \t:|-]*-[ \t:|-]*\|$')
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def field(fm: str, name: str):
    m = re.search(rf'^{name}:\s*(.*)$', fm, re.M)
    if not m:
        return None
    v = m.group(1).strip()
    if v.startswith(('"', "'")):
        v = v[1:-1]
    return v or None


def page_entry(root: pathlib.Path, page: str, problems: list):
    """-> (title, description), or None after recording why the page cannot be listed."""
    f = root / 'docs' / page
    if not f.is_file():
        return None                         # generate-site-nav's problems already name it
    m = FM.match(f.read_text())
    if not m:
        problems.append(f'docs/{page} has no frontmatter, so no title and no description')
        return None
    title, desc = field(m.group(1), 'title'), field(m.group(1), 'description')
    if not title:
        problems.append(f'docs/{page} has no frontmatter title')
    if not desc:
        problems.append(f'docs/{page} has no frontmatter description')
    return (title, desc) if title and desc else None


def read_stamp(root: pathlib.Path, problems: list):
    index = root / 'docs' / 'index.md'
    found = STAMP.findall(index.read_text()) if index.is_file() else []
    if len(found) == 0:
        problems.append("docs/index.md has no `**Verified against Hytale X (build-N).**` paragraph")
    if len(found) > 1:
        problems.append(f'docs/index.md has {len(found)} `**Verified against Hytale X (build-N).**` paragraphs, wanted 1')
    return f'Hytale {found[0][0]} (build-{found[0][1]})' if len(found) == 1 else None


def population(root: pathlib.Path, problems: list):
    r = subprocess.run(['git', '-C', str(root), 'ls-files', '--', 'examples/'], capture_output=True, text=True)
    if r.returncode != 0:
        problems.append(f'`git ls-files examples/` failed in {root}: the examples are the tracked directories, so '
                        'the generator needs a git work tree')
        return set()
    tracked = {p for p in r.stdout.split('\n') if p}
    pop = {p.split('/')[1] for p in tracked if p.count('/') >= 2}
    if not pop:
        problems.append('0 example directories are tracked under examples/: a list of nothing is a broken run')
    return pop


def read_examples(root: pathlib.Path, pop: set, problems: list):
    """-> [(dir, Type, What it demonstrates)] in the table's order."""
    f = root / 'examples' / 'README.md'
    if not f.is_file():
        problems.append('examples/README.md does not exist, and the examples are described by its table')
        return []
    lines = f.read_text().split('\n')
    at = [i for i, l in enumerate(lines) if l.rstrip() == HEADER]
    if len(at) != 1:
        problems.append(f'examples/README.md holds the table header `{HEADER}` {len(at)} times, wanted exactly once')
        return []
    i = at[0] + 1
    if i >= len(lines) or not SEPARATOR.match(lines[i].strip()):
        problems.append('examples/README.md: the table header is not followed by its separator row')
        return []
    rows, seen = [], {}
    for n in range(i + 1, len(lines)):
        row = lines[n].strip()
        if not row.startswith('|'):
            break
        parts = re.split(r'(?<!\\)\|', row)
        if len(parts) != 6 or parts[0] != '' or parts[-1] != '':
            problems.append(f'examples/README.md:{n + 1} is not a row of four cells')
            continue
        cells = [c.strip() for c in parts[1:-1]]
        m = LINK.search(cells[0])
        if not m:
            problems.append(f'examples/README.md:{n + 1} has no link in its first cell')
            continue
        path = urllib.parse.unquote(m.group(1).partition('#')[0].partition('?')[0])
        segs = posixpath.normpath(posixpath.join('examples', path)).split('/')
        if len(segs) != 2 or segs[0] != 'examples' or segs[1] not in pop:
            problems.append(f'examples/README.md:{n + 1} links {m.group(1)}, which is not an example directory')
            continue
        d = segs[1]
        if d in seen:
            problems.append(f'examples/README.md:{n + 1} is a second row for examples/{d}/ (first at line {seen[d]})')
            continue
        seen[d] = n + 1
        if cells[1] not in TYPES:
            problems.append(f'examples/README.md:{n + 1} has Type {cells[1]!r}, wanted one of {" or ".join(TYPES)}')
            continue
        what = cells[2].replace('\\|', '|')
        if not what:
            problems.append(f'examples/README.md:{n + 1} has an empty "What it demonstrates" cell')
            continue
        rows.append((d, cells[1], what))
    for d in sorted(pop - set(seen)):
        problems.append(f'examples/{d}/ is tracked and has no row in examples/README.md')
    return rows


def generate(root: pathlib.Path):
    """-> (text or None, categories, page links, examples, problems)"""
    problems: list[str] = []
    cats = [c for c in NAV.read_categories((root / 'README.md').read_text()) if c[1]]
    if not cats:
        problems.append('README.md lists no categories under `## Documentation`')
    problems += NAV.generate(root)[3]
    listed = {page for _, pages in cats for _, page in pages}
    for p in sorted(f.name for f in (root / 'docs').glob('*.md')):
        if p != 'index.md' and p not in listed:
            problems.append(f'docs/{p} is listed in no README category, so in no group')
    stamp = read_stamp(root, problems)
    home = page_entry(root, 'index.md', problems)
    pop = population(root, problems)
    examples = read_examples(root, pop, problems) if pop else []

    sections, npages = [], 0
    if home:
        sections.append(('Start here', [f'- [{home[0]}]({SITE}/index.html): {home[1]}']))
        npages += 1
    for cat, pages in cats:
        items = []
        for _, page in pages:
            e = page_entry(root, page, problems)
            if e:
                items.append(f'- [{e[0]}]({SITE}/{page[:-3]}.html): {e[1]}')
                npages += 1
        sections.append((cat, items))
    sections.append(('Examples', [f'- [{d}/]({REPO}/tree/main/examples/{d}/): {t}. {w}' for d, t, w in examples]))
    sections.append(('Source', [f'- [GitHub repository]({REPO}): the markdown source of every page, the example mods, '
                                'and the scripts that run the checks']))
    if problems:
        return None, len(cats), npages, len(examples), problems

    out = ['# Hytale Modding Handbook', '',
           '> A Hytale server-plugin and asset-format API reference with descriptions, gotchas and runnable example '
           f'mods, verified against {stamp}. `verify-docs.sh`, which the maintainer runs before each push, checks '
           'that the `com.hypixel.*` class names and `Class.member` references in the pages exist in HytaleServer.jar; '
           'that the discriminator values in JSON examples (`Type` and the like) are names the jar registers under '
           'that key; that asset ids at typed key positions in JSON examples exist in the shipped assets; that '
           'complete Java examples (those that start with `package`) and the example plugins compile against the '
           'jar; and that links and section anchors resolve. It does not machine-check JSON enum values, required '
           'keys or lists of bare method signatures.', '',
           'Hytale mods are server-side Java plugins plus JSON/DSL asset packs. Start with Home, which sends each '
           'task to the section that does it.', '',
           f'The links below are the rendered pages. The markdown source of a page is `{RAW}/<file>.md`, where '
           '`<file>` is the name in its link (for `commands.html`, `commands.md`).', '']
    for title, items in sections:
        out += [f'## {title}', ''] + items + ['']
    return '\n'.join(out), len(cats), npages, len(examples), problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(HERE.parents[1]))
    root = pathlib.Path(ap.parse_args().root)
    text, ncat, npages, nex, problems = generate(root)
    if problems:
        for p in problems:
            print(f'  FAIL  {p}', file=sys.stderr)
        print(f'  FAIL  llms.txt was not generated: {len(problems)} problem(s)', file=sys.stderr)
        return 2
    sys.stdout.write(text)
    print(f'LLMS {ncat} categories, {npages} pages, {nex} examples', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
