#!/usr/bin/env python3
"""
Generate the site's sidebar (`nav` in zensical.toml) from README.md, so there is one list of pages.

README.md's `## Documentation` section is the only human-curated list of every docs page, grouped in `###`
categories with a label per page. The sidebar is that list: Home first, then each category in README order,
holding its pages under the README link text as the label. Nothing in zensical.toml's nav is edited by hand;
the array between the two marker comments is this script's output and verify-docs fails when it differs from a
fresh generation.

  python3 maintenance/scripts/generate-site-nav.py            # print the generated block
  python3 maintenance/scripts/generate-site-nav.py --write    # rewrite the block in zensical.toml
  python3 maintenance/scripts/generate-site-nav.py --check    # exit 1 unless the committed block equals it

Every run prints `NAV <categories> categories, <pages> pages` on stderr, so a caller can tell a generator that
found nothing from one that found the list. Exit 2 when it found 0 categories or 0 pages, or a README link
whose page does not exist, or a page listed twice.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BEGIN = '# BEGIN GENERATED NAV (maintenance/scripts/generate-site-nav.py from README.md; do not edit by hand)'
END = '# END GENERATED NAV'
ITEM = re.compile(r'^- \[([^\]]+)\]\(\./docs/([A-Za-z0-9._-]+\.md)\)')


def read_categories(readme: str):
    """-> [(category, [(label, page.md), ...])] for the `###` headings under `## Documentation`."""
    s = readme.find('\n## Documentation')
    if s < 0:
        return []
    e = readme.find('\n## ', s + 1)
    section = readme[s:e if e > 0 else len(readme)]
    cats = []
    for line in section.split('\n'):
        if line.startswith('### '):
            cats.append((line[4:].strip(), []))
        elif cats:
            m = ITEM.match(line)
            if m:
                cats[-1][1].append((m.group(1), m.group(2)))
    return cats


def generate(root: pathlib.Path):
    """-> (block text, categories, pages, problems)"""
    cats = [c for c in read_categories((root / 'README.md').read_text()) if c[1]]
    problems, seen = [], {}
    for cat, pages in cats:
        for label, page in pages:
            if not (root / 'docs' / page).is_file():
                problems.append(f'README lists {page} under {cat!r}, and docs/{page} does not exist')
            if page in seen:
                problems.append(f'{page} is listed twice in README (under {seen[page]!r} and {cat!r})')
            seen[page] = cat
    lines = [BEGIN, 'nav = [', '  { "Home" = "index.md" },']
    for cat, pages in cats:
        items = ', '.join('{ %s = %s }' % (json.dumps(l), json.dumps(p)) for l, p in pages)
        lines.append('  { %s = [ %s ] },' % (json.dumps(cat), items))
    lines += [']', END]
    return '\n'.join(lines), len(cats), sum(len(p) for _, p in cats), problems


def splice(toml: str, block: str):
    """-> the toml with its marker block replaced, or None when it does not hold exactly one block."""
    if toml.count(BEGIN) != 1 or toml.count(END) != 1 or toml.index(BEGIN) > toml.index(END):
        return None
    a = toml.index(BEGIN)
    b = toml.index(END) + len(END)
    return toml[:a] + block + toml[b:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(ROOT))
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--write', action='store_true')
    g.add_argument('--check', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    block, ncat, npage, problems = generate(root)
    print(f'NAV {ncat} categories, {npage} pages', file=sys.stderr)
    for p in problems:
        print(f'  FAIL  {p}', file=sys.stderr)
    if ncat == 0 or npage == 0 or problems:
        print('  FAIL  the generator found no usable page list in README.md', file=sys.stderr)
        return 2
    if not (a.write or a.check):
        print(block)
        return 0
    f = root / 'zensical.toml'
    toml = f.read_text() if f.exists() else ''
    new = splice(toml, block)
    if new is None:
        print(f'  FAIL  zensical.toml does not hold exactly one {BEGIN!r} ... {END!r} block', file=sys.stderr)
        return 2
    if a.write:
        f.write_text(new)
        return 0
    if new != toml:
        print('  FAIL  the nav in zensical.toml differs from a fresh generation from README.md; run '
              'maintenance/scripts/generate-site-nav.py --write', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
