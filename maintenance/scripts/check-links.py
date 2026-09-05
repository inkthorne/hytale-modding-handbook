#!/usr/bin/env python3
"""
Every markdown link in the repo resolves — target file and anchor, path-aware.

WHY THE CORPUS IS THE WHOLE TREE. This gate used to glob `docs/*.md` on both
sides, so `examples/README.md` and `examples/item-respawner/README.md` — the
handbook's own entry point — pointed `../docs/blocks.md#custom-block-entity-components`
at a section a split had moved, and nothing reported it. Widening the glob alone
would not have helped: the old link pattern was `([a-zA-Z0-9_\\-]+\\.md)?#`, which
cannot express a PATH, so `../docs/blocks.md#x` never matched in the first place.
Two independent narrowings, and the line the gate printed — `all anchor links
resolve` — was true of docs/ and false of the repo.

WHY THE DENOMINATOR IS SPLIT AND NOT SUMMED. `1984 links` is aggregated over two
populations, and the one this gate exists for is 5% of it: 1883 in docs/, 101
outside. Re-narrow the glob to `docs/*.md` and a total-only floor of 100 sails
through on 1883 — the gate would report green having re-acquired the exact bug it
was written to prevent. A figure summed over sources cannot show one source
reaching zero, which is this repo's third instance of that shape. So the two
populations are printed separately and the OUTSIDE one carries its own floor.

Usage: python3 maintenance/scripts/check-links.py [--root DIR] [--min-outside N]
Exit 0 pass, 1 findings, 2 SKIP (the corpus is absent or implausible).
"""
from __future__ import annotations
import argparse, collections, os, pathlib, re, sys

SKIP_DIRS = {'.git', 'build', 'out', '.gradle', 'node_modules'}

# The heading -> anchor rule, matching the site generator's.
def slug(t: str) -> str:
    s = t.strip().lower()
    s = re.sub(r'[^\w\- ]', '', s)
    return s.replace(' ', '-')

HEADING = re.compile(r'^#{1,6}\s+(.*?)\s*#*$')
# `[text](target.md#anchor)`, either part optional. The anchor class is
# `[A-Za-z0-9_-]` because `slug()` strips everything else from a heading, so no
# anchor outside that class can ever be VALID. The failure mode is therefore
# "an unfixable link is skipped rather than reported", not "a broken link
# passes" — audited, not live on build-26, and stated here so the next reader
# does not have to re-derive it.
LINK = re.compile(r'\[([^\]]*)\]\(([^)\s#]*\.md)?(?:#([A-Za-z0-9_\-]+))?\)')


def corpus(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in sorted(root.rglob('*.md'))
            if not (SKIP_DIRS & set(p.relative_to(root).parts))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(pathlib.Path(__file__).resolve().parents[2]))
    ap.add_argument('--min-links', type=int, default=100)
    ap.add_argument('--min-outside', type=int, default=1)
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    if not root.exists():
        print(f'  SKIP  corpus root not found at {root}')
        return 2

    files = corpus(root)
    anchors: dict[str, set[str]] = {}
    for p in files:
        seen: collections.Counter = collections.Counter()
        got = set()
        for line in p.read_text(errors='replace').split('\n'):
            m = HEADING.match(line)
            if m:
                b = slug(m.group(1))
                got.add(b if seen[b] == 0 else f'{b}-{seen[b]}')
                seen[b] += 1
        anchors[str(p)] = got

    pop = collections.Counter()
    findings: list[str] = []
    for p in files:
        # ROOT-RELATIVE, deliberately. Pointing --root at docs/ therefore makes
        # every file read as "outside", which is why the fixture simulates the
        # narrowing with a top-rooted corpus that contains no examples/ rather
        # than by rooting at docs/ — the latter passes and asserts nothing.
        inside = 'docs' in p.relative_to(root).parts[:1]
        for ln, line in enumerate(p.read_text(errors='replace').split('\n'), 1):
            for m in LINK.finditer(line):
                tgt, an = m.group(2), m.group(3)
                if tgt is None and an is None:
                    continue
                pop['docs' if inside else 'outside'] += 1
                tp = str(p) if tgt is None else os.path.normpath(str(p.parent / tgt))
                rel = p.relative_to(root)
                if tp not in anchors:
                    findings.append(f'{rel}:{ln} -> {tgt} (no such file)')
                elif an is not None and an not in anchors[tp]:
                    findings.append(f'{rel}:{ln} -> {tgt or p.name}#{an} (no such anchor)')
                elif a.verbose:
                    print(f'  ok    {rel}:{ln} -> {tgt or ""}#{an or ""}')

    total = sum(pop.values())
    print(f'  INFO  {total} markdown link(s) in {len(files)} file(s): '
          f'{pop["docs"]} under docs/, {pop["outside"]} outside it')

    # TWO floors, and the second one is the point. A total-only floor cannot tell
    # "the widening works" from "the widening was reverted".
    if total < a.min_links:
        print(f'  SKIP  only {total} link(s) scanned, floor is {a.min_links} — '
              f'a broken check, not a clean run')
        return 2
    if pop['outside'] < a.min_outside:
        print(f'  SKIP  {pop["outside"]} link(s) found outside docs/, floor is '
              f'{a.min_outside} — the corpus has narrowed back to docs/, which is '
              f'the regression this gate exists to prevent')
        return 2

    for f in findings:
        print(f'  FAIL  {f}')
    if findings:
        return 1
    print(f'  PASS  all {total} markdown link(s) resolve')
    return 0


if __name__ == '__main__':
    sys.exit(main())
