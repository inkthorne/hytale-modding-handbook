#!/usr/bin/env python3
"""
Every example directory is linked once from each of the three lists of examples.

WHY. The handbook lists its examples in three places a reader can start from: docs/examples.md (the site),
examples/README.md (what GitHub shows when someone browses examples/) and README.md's `## Examples` section. A
fourth list (CLAUDE.md's) is for the maintainer and is not gated. Before this gate nothing tied the lists to the
directories or to each other: the README-listing gate measures docs pages, check-links measures that a link
resolves, and neither notices an example that is on one list and not on another, or that is on a list twice.
Pages went unlisted 16 times out of 71 before the README-listing gate existed; the same shape applies here.

THE POPULATION is the tracked top-level directories of examples/: `git ls-files examples/`, the first path
segment of every path that has one below it. A file at the top (README.md, hytale-paths.gradle) is not a
directory, and an untracked directory (a build output) is not an example. A directory without a tracked
README.md is a FAIL, because each list sends the reader to it. 0 directories is a FAIL: a gate that visited
nothing certifies nothing. The gate needs a git work tree, as the site build does.

THE THREE LISTS, and the part of each that is the list:
  docs/examples.md      the whole page
  examples/README.md    the rows of its table (lines that start with `|`); its `###` headings link the same
                        directories again, which is a second use of one link and not a second list entry
  README.md             the `## Examples` section, up to the next `## ` heading
Each must link every directory of the population exactly once, with its trailing slash, and must link nothing
under examples/ that is not one.

HOW A LINK IS READ. With check-links' link_dests(), so a link in a code span or a fence is no link. The
destination is resolved against the file's own directory, so `./custom-food/`, `custom-food/` and
`../examples/custom-food/` all name the same directory and each list may write it the way it likes. Then:
  * under examples/ and naming a directory of the population, with a trailing slash: a list entry;
  * the same without the slash: a FAIL naming the link (the site's link rewrite picks tree or blob by asking
    whether the path exists, and GitHub's own rendering of a slash-less directory link differs from a file);
  * naming anything else under examples/ (a directory that is not tracked, a stray file): a FAIL;
  * a link to a file inside an example (`../examples/commands/README.md`, a source file) is not a list entry
    and is not a FAIL: the Examples page links each README beside its directory;
  * examples/README.md, linked from examples.md and from README.md, is allowed and counted, never a member.
A link that leaves examples/ is not this gate's business.

Usage: python3 maintenance/scripts/check-example-lists.py [--root DIR]
Exit 0 pass, 1 findings, 2 SKIP (nothing to check: a broken check, not a clean run).
"""
from __future__ import annotations
import argparse, collections, importlib.util, pathlib, posixpath, re, subprocess, sys, urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import doc_fences

_spec = importlib.util.spec_from_file_location('check_links_for_example_lists', HERE / 'check-links.py')
CL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CL)

LISTS = (
    ('docs/examples.md', 'whole'),
    ('examples/README.md', 'rows'),
    ('README.md', 'section'),
)
SECTION = '## Examples'


def scope_lines(text: str, how: str, fenced):
    """-> the line numbers that are the list, or None when the file has no such part (a missing section)."""
    lines = text.split('\n')
    if how == 'whole':
        return set(range(1, len(lines) + 1))
    if how == 'rows':
        return {n for n, l in enumerate(lines, 1) if l.lstrip().startswith('|')}
    start = next((n for n, l in enumerate(lines, 1) if n not in fenced and l.rstrip() == SECTION), None)
    if start is None:
        return None
    end = next((n for n in range(start + 1, len(lines) + 1)
                if n not in fenced and lines[n - 1].startswith('## ')), len(lines) + 1)
    return set(range(start + 1, end))


def population(root: pathlib.Path):
    """-> (set of directory names, set of tracked paths under examples/), or None when git cannot say."""
    r = subprocess.run(['git', '-C', str(root), 'ls-files', '--', 'examples/'], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    tracked = {p for p in r.stdout.split('\n') if p}
    return {p.split('/')[1] for p in tracked if p.count('/') >= 2}, tracked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(HERE.parents[1]))
    a = ap.parse_args()
    root = pathlib.Path(a.root)

    pop_tracked = population(root)
    if pop_tracked is None:
        print(f'  FAIL  the gate needs a git work tree: `git ls-files examples/` failed in {root}')
        return 1
    pop, tracked = pop_tracked
    if not pop:
        print(f'  SKIP  0 example directories tracked under examples/ in {root} - a broken check, not a clean run')
        return 2

    findings: list[str] = []
    for d in sorted(pop):
        if f'examples/{d}/README.md' not in tracked:
            findings.append(f'examples/{d}/ has no tracked README.md, and each list sends the reader to it')

    counts = {}
    allowed = {}
    for rel, how in LISTS:
        f = root / rel
        if not f.is_file():
            findings.append(f'{rel}: the list is missing')
            continue
        text = f.read_text(errors='replace')
        fenced = doc_fences.parse(text).fence_lines
        scope = scope_lines(text, how, fenced)
        if scope is None:
            findings.append(f'{rel}: no `{SECTION}` section, so no list')
            continue
        hits = collections.defaultdict(list)
        allowed[rel] = 0
        for ln, raw in CL.link_dests(text, fenced):
            if ln not in scope:
                continue
            path = urllib.parse.unquote(raw.partition('#')[0].partition('?')[0])
            if CL.SCHEME.match(path):
                continue                    # a URL: `examples/` inside it is not a path of this repository
            slash = path.endswith('/')
            joined = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
            if not joined.startswith('examples/'):
                continue
            segs = joined[len('examples/'):].split('/')
            name = segs[0]
            if segs == ['README.md']:
                allowed[rel] += 1
            elif name not in pop:
                findings.append(f'{rel}:{ln} links {raw}, which is not an example directory')
            elif len(segs) == 1:
                if not slash:
                    findings.append(f'{rel}:{ln} links {raw} without the trailing slash (write {raw}/)')
                hits[name].append(ln)
        counts[rel] = 0
        for d in sorted(pop):
            n = len(hits[d])
            if n == 0:
                findings.append(f'{rel} does not link examples/{d}/')
            elif n > 1:
                findings.append(f'{rel} links examples/{d}/ {n} times (lines {", ".join(map(str, hits[d]))})')
            counts[rel] += n == 1

    print(f'  INFO  {sum(allowed.values())} link(s) to examples/README.md allowed, not members: '
          + ', '.join(f'{k} {v}' for k, v in allowed.items()))
    for f in findings:
        print(f'  FAIL  {f}')
    if findings:
        return 1
    print(f'  PASS  {len(pop)} example dir(s); examples.md {counts["docs/examples.md"]}, '
          f'examples/README.md {counts["examples/README.md"]}, README.md {counts["README.md"]} '
          f'(each directory linked once, with its slash, from each list)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
