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

AND THE GATE'S OWN TEST DATA DOES NOT VOTE IN THAT FLOOR. The first version of
this split counted `maintenance/fixtures/links/**` in the outside population —
5 of its 106 — against a floor of 1. Rebuilt as the real regression (a top-rooted
corpus reaching no further than docs/, with the fixture directory surviving as it
would in any real regression) the outside population fell 106 -> 5, a 95%
collapse of exactly what the floor measures, and the gate passed: the scaffolding
alone cleared the floor. Fixture links are still CHECKED for correctness; they
are excluded from the number that makes a claim about repo content. Exclusion
rather than a bigger floor, because a calibrated value rots every time an
examples README is added — the argument this repo already settled twice for page
sizes.

EVERY FILE THIS GATE READS IS FENCE-CENSUSED. The headings rule below trusts doc_fences.py's
`fence_lines`, and that module's refusals (four backticks, ~~~, a closer of another prefix shape, an
unclosed fence, ...) are only enforced by the census in verify-docs.sh, which covers docs/*.md. In
README.md, CLAUDE.md, maintenance/ and examples/ the refusals were dropped on the floor: a
`# phantom` line inside a ~~~ fence is a heading to a reader that does not support ~~~, so a link
to `#phantom` passed (review of bc10b45..23ea833, MINOR-9). So here every file scanned goes
through `doc_fences.orphans_of()`, and an orphan is a FAIL naming file:line. The tag allowlist is
a docs/ rule and is not applied (maintenance/fixtures/doctype/fixture-i.md carries a ```Java fence
on purpose). Measured at the commit that added it: 0 orphans in the 131 tracked markdown files.

HEADINGS COME FROM OUTSIDE FENCES ONLY. A `# comment` line in a bash fence matches the heading
pattern, so before 2026-10-16 it was an anchor: a link to a section that does not exist
but whose slug equalled one of those comments passed. Six such lines in the repo's own
tree (00-overview.md:105, 02-structure.md:412, i18n.md:61, ui-templates.md:451 and
CLAUDE.md:18/22); no link targeted any, so no verdict moved, but nothing would have
noticed one that did. A line is read as a heading only when it is not on a line
doc_fences.py's `fence_lines` occupies, so this gate shares the one fence reader the
others read through. The count of heading-shaped lines it passed over is printed, so a
run that excluded nothing can be told from one that was never offered any.

THE SLUG IS GITHUB'S, TAGS INCLUDED. A heading is slugged from the text GitHub renders, and GitHub drops
raw HTML from it: `## IAsyncEvent<KeyType>` is `iasyncevent`, not `iasynceventkeytype`, because `<KeyType>`
is an inline HTML tag and not text. This gate slugged the raw characters, so it passed two links GitHub
breaks (asset-editor.md:58 and player.md:265). What counts as a tag is CommonMark's inline raw HTML and
nothing wider, fitted to GitHub's own ids (maintenance/fixtures/links/gh-heading-ids.tsv, read at d361e13
with `gh api -H 'Accept: application/vnd.github.html' .../contents/docs/X.md`): `<KeyType>`, `<T>`, `<D>`
and `<T extends Transaction>` are tags; `<K, T>`, `<Arg, D>` and `<ECS_TYPE>` are text, because a comma, or
an underscore in the name, makes the thing no tag. A `[^>]*` regex drops `<K, T>` and so is wrong in the
other direction. Code spans are text. `char_slug()` is the character rule alone, which the site's slugify
shares: once no heading carries raw HTML (verify-docs lints that), the characters are all there is to
compute from.

EVERY RELATIVE TARGET IS CHECKED, NOT ONLY `.md`. The link pattern matched only `.md` targets, so the nine
links that leave docs/ (eight into `../examples/`, one to `../CLAUDE.md`) and the README's directory links
were never read: a renamed example would have left eight dead links and a green run. Any link whose target
is neither a URL (`scheme:`), a `//` URL nor a bare `#fragment` must resolve to a file or a directory inside
the root. Fragments are checked on `.md` targets only. Links on lines inside a code fence are not links
(`list[i](x)` is code), so they are not read; none exists in the tree today.

Usage: python3 maintenance/scripts/check-links.py [--root DIR] [--min-outside N] [--min-other N]
Exit 0 pass, 1 findings, 2 SKIP (the corpus is absent or implausible).
"""
from __future__ import annotations
import argparse, collections, os, pathlib, re, sys, urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import doc_fences

# `.claude` holds tooling state, never repo docs: the session lock (scheduled_tasks.lock), the
# agents' addenda, and `worktrees/`, where each parallel agent has a full checkout of this repo.
# Those checkouts' markdown is a second copy of the tracked tree (and of whatever an agent has
# half-edited), so a main-checkout run counted it: 4484 links in 262 files with one worktree
# present against the tracked tree's 2242 in 131, a figure that moved with how many agents
# happened to be running and that nobody could reproduce from a clone. Nothing under .claude/ is
# a link target of any tracked page (no tracked file lives there: `git ls-files .claude` is empty).
SKIP_DIRS = {'.git', '.claude', 'build', 'out', '.gradle', 'node_modules'}

# The heading -> anchor rule, GitHub's. `char_slug` is the character rule: lower-case, drop everything that
# is not a word character, hyphen or space, spaces to hyphens. `slug` first drops the inline HTML GitHub
# drops from the heading text (see THE SLUG IS GITHUB'S above), outside code spans.
def char_slug(t: str) -> str:
    s = t.strip().lower()
    s = re.sub(r'[^\w\- ]', '', s)
    return s.replace(' ', '-')


# CommonMark's inline raw HTML (spec 6.6), the five forms. An open tag is a name, then attributes that each
# need whitespace before them and a name of their own, then an optional `/`. That is why `<K, T>` is no tag
# (a comma cannot start an attribute) and `<T extends Transaction>` is one (two boolean attributes).
_ATTR = r'''\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?'''
RAW_HTML = re.compile(
    r'<[A-Za-z][A-Za-z0-9-]*(?:' + _ATTR + r')*\s*/?>'      # open tag
    r'|</[A-Za-z][A-Za-z0-9-]*\s*>'                        # closing tag
    r'|<!--.*?-->'                                         # comment
    r'|<\?.*?\?>'                                          # processing instruction
    r'|<![A-Za-z][^>]*>'                                   # declaration
    r'|<!\[CDATA\[.*?\]\]>', re.S)
CODE_SPAN = re.compile(r'(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)')


def strip_tags(t: str) -> str:
    """`t` with the inline HTML GitHub drops removed, code spans left alone (their `<`..`>` is text)."""
    out, pos = [], 0
    for m in CODE_SPAN.finditer(t):
        out.append(RAW_HTML.sub('', t[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(RAW_HTML.sub('', t[pos:]))
    return ''.join(out)


def slug(t: str) -> str:
    return char_slug(strip_tags(t))

HEADING = re.compile(r'^#{1,6}\s+(.*?)\s*#*$')
# Every link, `[text](target)` with an optional title; main() classifies the target. A fragment is read as
# an anchor only inside `[A-Za-z0-9_-]`, because `slug()` strips everything else from a heading, so no
# anchor outside that class can ever be VALID. The failure mode is therefore "an unfixable link is
# skipped rather than reported", not "a broken link passes" - audited, not live on build-26, and stated
# here so the next reader does not have to re-derive it.
ANY_LINK = re.compile(r'\[([^\]]*)\]\(([^)\s]*)(?:\s+(?:"[^"]*"|\'[^\']*\'))?\)')
SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:|^//')


def anchors_of(text: str):
    """-> (anchors, passed_over): the anchors a page's headings define, and the number of
    heading-shaped lines that sit inside a code fence and so define none."""
    fenced = doc_fences.parse(text).fence_lines
    seen: collections.Counter = collections.Counter()
    got = set()
    passed_over = 0
    for no, line in enumerate(text.split('\n'), 1):
        m = HEADING.match(line)
        if not m:
            continue
        if no in fenced:
            passed_over += 1
            continue
        b = slug(m.group(1))
        got.add(b if seen[b] == 0 else f'{b}-{seen[b]}')
        seen[b] += 1
    return got, passed_over


def corpus(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in sorted(root.rglob('*.md'))
            if not (SKIP_DIRS & set(p.relative_to(root).parts))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(pathlib.Path(__file__).resolve().parents[2]))
    ap.add_argument('--min-links', type=int, default=100)
    ap.add_argument('--min-outside', type=int, default=1)
    ap.add_argument('--min-other', type=int, default=1)
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    if not root.exists():
        print(f'  SKIP  corpus root not found at {root}')
        return 2

    def where(page: pathlib.Path, target: str) -> str:
        """Where a link's path points: beside the page, or from the repository root when it starts with `/`
        (GitHub's reading of a root-relative link)."""
        base = root if target.startswith('/') else page.parent
        return os.path.normpath(str(base / target.lstrip('/')))

    files = corpus(root)
    texts = {p: p.read_text(errors='replace') for p in files}
    anchors: dict[str, set[str]] = {}
    in_fences = 0
    for p in files:
        anchors[str(p)], n = anchors_of(texts[p])
        in_fences += n

    pop = collections.Counter()
    findings: list[str] = []
    orphans = 0
    other = other_dirs = 0          # relative targets that are not .md pages: files, and directories
    for p in files:
        rel = p.relative_to(root)
        # THREE buckets, not two, and the classification is ROOT-RELATIVE.
        # Pointing --root at docs/ therefore makes every file read as "outside",
        # which is why the fixture simulates the narrowing with a top-rooted
        # corpus containing no examples/ rather than by rooting at docs/ — the
        # latter passes while asserting nothing. `fixture` exists because a floor
        # its own test data can satisfy is not a floor: those links are checked
        # for correctness and excluded from the number that claims something
        # about repo content.
        if 'docs' in rel.parts[:1]:
            bucket = 'docs'
        elif rel.parts[:2] == ('maintenance', 'fixtures'):
            bucket = 'fixture'
        else:
            bucket = 'outside'
        # A fence marker the shared reader did not accept (see EVERY FILE ... above), in any bucket.
        for _name, no, why in doc_fences.orphans_of(str(rel), texts[p]):
            findings.append(f'{rel}:{no}: fence census orphan ({why})')
            orphans += 1
        fenced = doc_fences.parse(texts[p]).fence_lines
        for ln, line in enumerate(texts[p].split('\n'), 1):
            if ln in fenced:
                continue            # `list[i](x)` in a fence is code, not a link
            for m in ANY_LINK.finditer(line):
                raw = m.group(2)
                if not raw or SCHEME.match(raw):
                    continue        # empty, or a URL: counted nowhere, fetched never
                path, _, frag = raw.partition('#')
                path = urllib.parse.unquote(path.partition('?')[0])
                if not path:
                    tgt, an = None, frag            # `#fragment`: this file
                elif path.endswith('.md'):
                    tgt, an = path, frag or None
                else:
                    tgt, an = path, None            # any other target must exist; its fragment is not read
                if tgt is None or tgt.endswith('.md'):
                    # An anchor outside `[A-Za-z0-9_-]` can never be VALID (slug() strips everything else), so
                    # the link is skipped, as before, rather than reported: unfixable, not broken.
                    if an is not None and not re.fullmatch(r'[A-Za-z0-9_\-]+', an):
                        if tgt is None:
                            continue
                        an = None
                    if tgt is None and not an:
                        continue
                    pop[bucket] += 1
                    tp = str(p) if tgt is None else where(p, tgt)
                    if tp not in anchors:
                        findings.append(f'{rel}:{ln} -> {tgt} (no such file)')
                    elif an is not None and an not in anchors[tp]:
                        findings.append(f'{rel}:{ln} -> {tgt or p.name}#{an} (no such anchor)')
                    elif a.verbose:
                        print(f'  ok    {rel}:{ln} -> {tgt or ""}#{an or ""}')
                else:
                    other += 1
                    dest = pathlib.Path(where(p, path))
                    if not dest.is_relative_to(os.path.normpath(str(root))):
                        findings.append(f'{rel}:{ln} -> {raw} (outside the repository)')
                    elif not dest.exists():
                        findings.append(f'{rel}:{ln} -> {raw} (no such file or directory)')
                    else:
                        other_dirs += dest.is_dir()
                        if a.verbose:
                            print(f'  ok    {rel}:{ln} -> {raw}')

    total = sum(pop.values())
    print(f'  INFO  {total} markdown link(s) in {len(files)} file(s): '
          f'{pop["docs"]} under docs/, {pop["outside"]} outside it, '
          f'{pop["fixture"]} in gate fixtures (checked, not floored)')
    print(f'  INFO  {in_fences} heading-shaped line(s) inside code fences passed over, not read as anchors')
    print(f'  INFO  {len(files)} file(s) fence-censused, {orphans} orphan marker(s)')
    print(f'  INFO  {other} relative non-.md target(s) checked for existence ({other_dirs} directories)')

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

    if other < a.min_other:
        print(f'  SKIP  {other} relative non-.md target(s) read, floor is {a.min_other} - the reader of '
              f'links that leave the .md pages (examples/, CLAUDE.md, directories) has gone blind')
        return 2

    for f in findings:
        print(f'  FAIL  {f}')
    if findings:
        return 1
    print(f'  PASS  all {total} markdown link(s) and {other} other relative target(s) resolve')
    return 0


if __name__ == '__main__':
    sys.exit(main())
