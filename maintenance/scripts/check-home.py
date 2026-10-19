#!/usr/bin/env python3
"""
What the Home page (docs/index.md) says about the handbook is held to what the rest of the repo says.

TWO THINGS, both of which a hand edit breaks without a sound.

1. THE VERIFIED-AGAINST PARAGRAPH. README.md and docs/index.md each carry the paragraph that starts
`**Verified against Hytale`: the build the whole handbook was last verified against, and what a page stamp is.
CLAUDE.md's release step bumps both by hand, and a bump that reaches one file leaves the two pages telling a
reader different builds. The gate takes the paragraph of each file (from that line to the next blank line, outside a
fence), collapses whitespace, and compares. It FAILs when a file has the paragraph 0 or 2 times, and when the two differ.
It proves the two agree. It does not prove either is true: the bump stays a hand bump, and the stamps on the pages are
the INFO section "Version stamps on topic pages".

2. THE TASK TABLES under `## Find it by task`. Home sends a reader from a goal to the page, the section and the call
that does it, so the properties that make a row useful are held:
  * every link to a .md page carries a #fragment (a row that sends a reader to the top of a 1,500-line page has not
    answered the task; check-links holds the fragment to a real heading);
  * the row count is within 12..18 (Home is a door, not a second index);
  * a table's third column is headed `API` or `Asset key`, and nothing else;
  * in an `API` table every row names its main call as `Receiver.member` in a code span, which check-symbols then
    checks against the jar; and the row is not a line check-symbols would skip. check-symbols treats any prose line
    holding one of its negation words (no, not, never, instead, removed, deprecated, ...) as a denial and ignores the
    symbols on it, and a table row is a prose line. The word list is read from check-symbols.py itself (its NEG
    assignment, by ast), so the two cannot drift;
  * with --jar, the receiver of each of those names resolves to a class of the jar. check-symbols skips a receiver
    that is no jar class, so a mistyped class name there is a pass in both, and this closes it;
  * in an `Asset key` table every row names the key or asset in a code span.
Not held: that the section a row links answers the task, and that the call is the current route. Those are read by a
person, per row (the item 16 audit); a deprecated route is found by `@Deprecated` in the decompiled source.

Usage: python3 maintenance/scripts/check-home.py [--root DIR] [--jar HytaleServer.jar]
Exit 0 pass, 1 findings, 2 SKIP (the page has no table to read: a broken check, not a clean run).
"""
from __future__ import annotations
import argparse, ast, importlib.util, pathlib, re, sys, zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import doc_fences

_spec = importlib.util.spec_from_file_location('check_links_for_home', HERE / 'check-links.py')
CL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CL)

PARA = '**Verified against Hytale'
SECTION = '## Find it by task'
ROWS_MIN, ROWS_MAX = 12, 18
KINDS = {'API': 'api', 'Asset key': 'asset'}
CELLS = re.compile(r'(?<!\\)\|')
CODE = re.compile(r'`([^`\n]+)`')
SYMBOL = re.compile(r'\b([A-Z][A-Za-z0-9_]*)\.([a-z_][A-Za-z0-9_]*)\b')


def verified_paragraphs(text: str):
    """-> the whitespace-collapsed paragraphs that start with PARA, outside fences."""
    fenced = doc_fences.parse(text).fence_lines
    lines = text.split('\n')
    out = []
    for i, l in enumerate(lines):
        if i + 1 in fenced or not l.startswith(PARA):
            continue
        j = i
        while j < len(lines) and lines[j].strip():
            j += 1
        out.append(' '.join(' '.join(lines[i:j]).split()))
    return out


def neg_pattern():
    """check-symbols.py's NEG, read from its source so the two cannot drift."""
    tree = ast.parse((HERE / 'check-symbols.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'NEG' for t in node.targets):
            return eval(compile(ast.Expression(node.value), 'check-symbols.py', 'eval'), {'re': re})
    return None


def jar_names(jar: pathlib.Path):
    """-> the simple names of the jar's com/hypixel classes, a nested class by its own name, as check-symbols keys them."""
    names = set()
    with zipfile.ZipFile(jar) as z:
        for n in z.namelist():
            if n.endswith('.class') and n.startswith('com/hypixel/'):
                names.add(n[:-6].rsplit('/', 1)[-1].rsplit('$', 1)[-1])
    return names


def tables(lines, start: int, end: int, fenced):
    """-> [(header cells, [(line number, line, cells)])] for the markdown tables on lines start..end."""
    out, cur = [], None
    for n in range(start, end + 1):
        l = lines[n - 1]
        if n in fenced or not l.lstrip().startswith('|'):
            cur = None
            continue
        cells = [c.strip() for c in CELLS.split(l.strip().strip('|'))]
        if cur is None:
            cur = (cells, [])
            out.append(cur)
        elif all(re.fullmatch(r':?-{3,}:?', c) for c in cells):
            continue
        else:
            cur[1].append((n, l, cells))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(HERE.parents[1]))
    ap.add_argument('--jar', default=None)
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    findings: list[str] = []

    # ---- 1. the verified-against paragraph ----
    paras = {}
    for rel in ('README.md', 'docs/index.md'):
        f = root / rel
        if not f.is_file():
            findings.append(f'{rel}: the file is missing')
            continue
        got = verified_paragraphs(f.read_text(errors='replace'))
        if len(got) != 1:
            findings.append(f'{rel} has {len(got)} paragraphs that start with {PARA}, wanted exactly 1')
        else:
            paras[rel] = got[0]
    if len(paras) == 2 and paras['README.md'] != paras['docs/index.md']:
        x, y = paras['README.md'], paras['docs/index.md']
        k = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
        findings.append(f'the Verified against paragraph of docs/index.md differs from README.md\'s at character {k}: '
                        f'README.md "...{x[max(0, k - 20):k + 30]}" docs/index.md "...{y[max(0, k - 20):k + 30]}"')

    # ---- 2. the task tables ----
    home = root / 'docs/index.md'
    nrows = {'api': 0, 'asset': 0}
    nlinks = nsyms = nresolved = 0
    if home.is_file():
        text = home.read_text(errors='replace')
        fenced = doc_fences.parse(text).fence_lines
        lines = text.split('\n')
        start = next((n for n, l in enumerate(lines, 1) if n not in fenced and l.rstrip() == SECTION), None)
        if start is None:
            print(f'  SKIP  docs/index.md has no `{SECTION}` section - a broken check, not a clean run')
            return 2
        end = next((n - 1 for n in range(start + 1, len(lines) + 1)
                    if n not in fenced and lines[n - 1].startswith('## ')), len(lines))
        tabs = tables(lines, start + 1, end, fenced)
        if not tabs:
            print(f'  SKIP  `{SECTION}` holds no table - a broken check, not a clean run')
            return 2
        neg = neg_pattern()
        if neg is None:
            findings.append('check-symbols.py has no NEG assignment to read: the gate cannot tell which rows it skips')
        jar = None
        if a.jar:
            try:
                jar = jar_names(pathlib.Path(a.jar))
            except (OSError, zipfile.BadZipFile) as e:
                findings.append(f'--jar {a.jar} could not be read: {e}')
            else:
                if not jar:
                    findings.append(f'--jar {a.jar} holds no com/hypixel class')
                    jar = None
        rows_by_line = {}
        for header, rows in tabs:
            if len(header) != 4 or header[2] not in KINDS:
                findings.append(f'docs/index.md: a table under `{SECTION}` has the header {header}, wanted four '
                                f'columns with `API` or `Asset key` third')
                continue
            kind = KINDS[header[2]]
            for n, l, cells in rows:
                rows_by_line[n] = (kind, l, cells)
        for n, (kind, l, cells) in sorted(rows_by_line.items()):
            nrows[kind] += 1
            if len(cells) != 4:
                findings.append(f'docs/index.md:{n} has {len(cells)} cells, wanted 4')
                continue
            if kind == 'api':
                syms = [m for s in CODE.findall(cells[2]) for m in SYMBOL.finditer(s)]
                if not syms:
                    findings.append(f'docs/index.md:{n} names no Receiver.member call in its API cell')
                nsyms += len(syms)
                if neg is not None and neg.search(l):
                    findings.append(f'docs/index.md:{n} holds a word check-symbols reads as a denial '
                                    f'("{neg.search(l).group(0)}"), so it would not check the call on this row')
                if jar is not None:
                    for m in syms:
                        if m.group(1) in jar:
                            nresolved += 1
                        else:
                            findings.append(f'docs/index.md:{n} names {m.group(1)}.{m.group(2)}, '
                                            f'and {m.group(1)} is no class of the jar')
            elif not CODE.search(cells[2]):
                findings.append(f'docs/index.md:{n} names no key or asset in a code span in its Asset key cell')
        total = nrows['api'] + nrows['asset']
        if not ROWS_MIN <= total <= ROWS_MAX:
            findings.append(f'`{SECTION}` has {total} rows, wanted {ROWS_MIN} to {ROWS_MAX}')
        for ln, raw in CL.link_dests(text, fenced):
            if ln in rows_by_line:
                path, _, frag = raw.partition('#')
                if path.endswith('.md'):
                    nlinks += 1
                    if not frag:
                        findings.append(f'docs/index.md:{ln} links {raw} without a #fragment')

    for f in findings:
        print(f'  FAIL  {f}')
    if findings:
        return 1
    k = len(paras['README.md'].split())
    print(f'  PASS  the Verified against paragraph is the same in README.md and docs/index.md ({k} words); '
          f'the task tables hold {nrows["api"]} API and {nrows["asset"]} Asset key rows, {nlinks} page link(s) all with a '
          f'#fragment, {nsyms} Receiver.member name(s) on rows check-symbols reads'
          + (f', {nresolved} resolved in the jar' if a.jar else ', receivers not resolved (no --jar)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
