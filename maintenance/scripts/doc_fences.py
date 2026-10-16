#!/usr/bin/env python3
"""
doc_fences — the ONE fence reader for every gate that reads a docs page's code fences.

WHY THIS EXISTS. Nine readers each carried a private regex for "where a fence starts"
and they disagreed. check-symbols, check-snippets and three verify-docs.sh readers
anchored at column 0; check-type-values and section_binder allowed indentation; gate 3
(check-asset-ids) alone allowed a `> ` blockquote prefix, because its review found a live
invented id (`Boss_Slam`) in one. Measured at bc10b45: 3 java fences and 1 json fence sit
inside a blockquote (inventory.md:245, :282, world.md:506, interactions-combat.md:1148)
and 2 java and 4 json sit indented in list items (interactions.md:589, worldgen.md:383,
interactions.md:594, items.md:343/352/360), and the column-0 readers saw none of the six
java ones: a dead `Receiver.member` or a package-led block that does not compile could
sit there with every gate green. Nothing was wrong with those fences; the point is that
nothing would have noticed. The fix that scales is not a seventh regex, it is one reader
and a CENSUS (below) that fails when a marker belongs to no fence the reader returned.

WHAT A FENCE IS HERE. Only THREE-backtick fences are supported. A line is an opener when,
after a container prefix, it carries exactly three backticks and an info string without a
backtick. The container prefix is a run of blockquote markers and indentation:

    prefix shape = (n, w): n = number of `>` markers, each optionally followed by ONE
                   space; then w = width of the remaining leading whitespace, a tab
                   counting as 4 columns. Whitespace before the first `>` is ignored.

A fence's `kind` is `col0` (0, 0), `indent` (0, w>0) or `quote` (n>0). A fence that is
both blockquoted and indented is `quote` (the blockquote is the container that changes
what a gate must do with its lines; the indent is stripped either way).

A CLOSER is a line of exactly three backticks and nothing else, with THE SAME PREFIX
SHAPE as the opener: a blockquote fence closes inside the blockquote, and a closer at a
different indentation is not this fence's closer. A BLANK line inside a quoted fence may
be a bare `>` (world.md writes them) or empty; a body line that is non-blank and carries
fewer `>` markers than the opener ends the blockquote, and with it the fence: reported as
`quote-break` and the fence returned unclosed.

The body has the container prefix removed from every line (up to n `>` markers, then up
to w columns of indentation) and, like the regexes it replaces, keeps the newline of
every line, so `body` is byte-identical to the old group(1) for a column-0 fence.

WHAT IT REFUSES, loudly, as PROBLEMS (never a silent extension to EOF, never a guess):
  * `unclosed`      an opener with no closer before EOF (the fence is still returned,
                    closed=False, body to EOF, so a gate reading it reads MORE not less);
  * `marker`        a marker that is not a supported opener or closer: four or more
                    backticks, `~~~`, a ```lang line inside an open fence, a closer
                    whose prefix shape differs from its opener's, and a fence opener
                    behind a LIST MARKER (`- ```java`) -- DECISION: list-marker openers
                    are not supported, they are a FAIL, because the supported prefix is
                    blockquote-and-indentation and the corpus has none (a list item's
                    fence is written indented on the next line, as interactions.md does);
  * `quote-break`   see above.

THE CENSUS. `census()` does not trust the reader: it counts every line whose ``` or ~~~ is
preceded only by whitespace, `>` and list markers (`-*+`, `\\d+[.)]`) with its own regex
and requires each to be an opener or closer line of a fence the reader returned. An
orphan marker is a FAIL with file:line. It is the guard against the next container form
nobody thought of: a reader that handled only the forms measured above would be the bug
this module exists to close. It FAILS on 0 pages and on 0 fences, because a census that
visited nothing certifies nothing.

THE TAG ALLOWLIST. Every content gate selects fences with a case-sensitive test on the tag
(`lang == 'java'`, `'json'`), so a fence written ```Java, ```JAVA, ```JSON or ```jsonc is
returned by the reader, counted by the census, counted identically by each gate's own
fence tally (fence_agree compares counts, and the count is of ALL fences), and read by no
gate: a dead `World.noSuchMemberXyzzy()` in a ```Java fence reported nothing (review of
bc10b45..23ea833, MAJOR-1). So the census also FAILS, with file:line, on any fence in docs/
whose whole info string is not one of ALLOWED_TAGS, the set the corpus uses (measured at
23ea833: java 1099, json 731, untagged 229, bash 4, batch 2). It fails closed: a new
language is an explicit edit of ALLOWED_TAGS, made by someone who has asked which gates
should read it. The comparison is on the whole info string, not on the leading \\w+: an
info string of `java title=x` or `java-x` is read as `java` by the gates and is refused.
The info string is stripped first, so ``` json (a space before the tag) is accepted as json;
check-asset-ids.py's own `(\\w*)` reads it as untagged, and verify-docs' fence_agree on gate 3's
json count, not this census, is what catches that disagreement.
The allowlist is a docs/ rule. Outside docs/ (check-links reads README, CLAUDE.md,
maintenance/, examples/) only the structural orphans apply, via `orphans_of()`.

HEADINGS. A heading-shaped line inside a fence is not a heading. The heading readers
(check-links, section_binder, verify-docs.sh's doc-type _sections and gotcha scan) take their
headings only from lines outside `Page.fence_lines`.

CLI (for the bash-inline readers and the census line):
    doc_fences.py --census [--docs DIR]     print the census line; exit 1 on any orphan
    doc_fences.py --counts [--docs DIR]     print `JAVA n JSON n TOTAL n PAGES n ORPHANS n`, the figures
                                            verify-docs.sh compares every gate's fence count with
"""
from __future__ import annotations
import argparse, collections, pathlib, re, sys
from typing import NamedTuple


# The info strings a fence in docs/ may carry. '' is an untagged fence. See THE TAG ALLOWLIST.
ALLOWED_TAGS = frozenset({'', 'java', 'json', 'bash', 'batch'})

# The census's own definition of "a marker line", independent of the reader's grammar.
CENSUS_MARKER = re.compile(r'^(?:[ \t]|>|[-*+]|\d+[.)])*(?:```|~~~)')
_TICKS = re.compile(r'`+|~+')


class Fence(NamedTuple):
    lang: str            # leading \w+ of the info string, '' if none ('java', 'json', ...)
    line: int            # 1-based line of the opener
    end_line: int | None # 1-based line of the closer, None when unclosed
    body: str            # prefix-stripped body, every line newline-terminated
    body_line: int       # 1-based line of the first body line (opener + 1)
    kind: str            # 'col0' | 'indent' | 'quote'
    closed: bool
    quotes: int          # prefix shape: number of `>` markers
    indent: int          # prefix shape: indentation columns after them
    start: int           # char offset of the opener line's first character
    end: int             # char offset just past the closer line (EOF if unclosed)
    info: str            # the whole info string after the three backticks, stripped


class Problem(NamedTuple):
    line: int            # 1-based
    kind: str            # 'unclosed' | 'marker' | 'quote-break'
    detail: str


class Page(NamedTuple):
    fences: list         # [Fence]
    problems: list       # [Problem]
    fence_lines: frozenset  # 1-based line numbers occupied by a fence, opener..closer

    def of(self, lang):
        return [f for f in self.fences if f.lang == lang]


def split_prefix(line: str):
    """-> (quotes, indent_columns, offset of the first character after the prefix)."""
    i, n, quotes = 0, len(line), 0
    while True:
        j = i
        while j < n and line[j] in ' \t':
            j += 1
        if j < n and line[j] == '>':
            quotes += 1
            i = j + 1
            if i < n and line[i] == ' ':        # each marker owns ONE optional space
                i += 1
        else:
            break
    j, width = i, 0
    while j < n and line[j] in ' \t':
        width += 4 if line[j] == '\t' else 1
        j += 1
    return quotes, width, j


def _strip(line: str, quotes: int, indent: int) -> str:
    """Remove up to `quotes` `>` markers, then up to `indent` columns of whitespace."""
    i, n = 0, len(line)
    for _ in range(quotes):
        j = i
        while j < n and line[j] in ' \t':
            j += 1
        if j < n and line[j] == '>':
            i = j + 1
            if i < n and line[i] == ' ':
                i += 1
        else:
            break
    cols = 0
    while i < n and cols < indent and line[i] in ' \t':
        cols += 4 if line[i] == '\t' else 1
        i += 1
    return line[i:]


def _kind(quotes: int, indent: int) -> str:
    if quotes:
        return 'quote'
    return 'indent' if indent else 'col0'


def parse(text: str) -> Page:
    lines = text.split('\n')
    if text.endswith('\n'):
        lines.pop()                 # the empty string after the last newline is not a line
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    found: list = []
    problems: list = []
    occupied: set = set()
    cur = None                      # the open fence's state

    def finish(closer_no, end_off):
        body = ''.join(b + '\n' for b in cur['body'])
        found.append(Fence(cur['lang'], cur['line'], closer_no, body, cur['line'] + 1,
                           _kind(cur['q'], cur['w']), closer_no is not None, cur['q'], cur['w'],
                           cur['start'], end_off, cur['info']))
        occupied.update(range(cur['line'], (closer_no or last_line) + 1))

    last_line = len(lines)
    for idx, line in enumerate(lines):
        no = idx + 1
        marker = CENSUS_MARKER.match(line)
        q, w, j = split_prefix(line)
        rest = line[j:]
        if cur is None:
            if not marker:
                continue
            if not rest.startswith(('```', '~~~')):
                problems.append(Problem(no, 'marker', 'a fence marker behind a list marker is '
                                        'not a supported opener: ' + line.strip()[:60]))
                continue
            run = _TICKS.match(rest).group(0)
            if rest[0] == '~':
                problems.append(Problem(no, 'marker', 'only three-backtick fences are supported, '
                                        'found a ~~~ marker: ' + line.strip()[:60]))
                continue
            if len(run) > 3:
                problems.append(Problem(no, 'marker', 'only three-backtick fences are supported, '
                                        'found ' + str(len(run)) + ' backticks: ' + line.strip()[:60]))
                continue
            info = rest[len(run):].strip()
            if '`' in info:
                problems.append(Problem(no, 'marker', 'a backtick in the info string makes this '
                                        'inline code, not an opener: ' + line.strip()[:60]))
                continue
            m = re.match(r'\w+', info)
            cur = dict(lang=m.group(0) if m else '', line=no, q=q, w=w, body=[],
                       start=starts[idx], info=info)
            continue
        # ---- inside an open fence ----
        if rest.strip() == '':                  # blank: empty, whitespace, or a bare `>` run
            cur['body'].append(_strip(line, cur['q'], cur['w']))
            continue
        if marker:
            if rest.startswith('```') and rest[3:].strip() == '':
                if (q, w) == (cur['q'], cur['w']):
                    finish(no, starts[idx] + len(line))
                    cur = None
                    continue
                problems.append(Problem(no, 'marker',
                                        f"closer with prefix shape (quotes={q}, indent={w}) does not "
                                        f"match its opener's (quotes={cur['q']}, indent={cur['w']}) "
                                        f"opened at line {cur['line']}"))
            else:
                problems.append(Problem(no, 'marker', 'a fence marker inside the fence opened at '
                                        f"line {cur['line']}: " + line.strip()[:60]))
            cur['body'].append(_strip(line, cur['q'], cur['w']))
            continue
        if q < cur['q']:
            problems.append(Problem(no, 'quote-break',
                                    f"a body line carries {q} `>` marker(s) but the fence opened at "
                                    f"line {cur['line']} sits in {cur['q']}: the blockquote ended "
                                    f"before the fence did"))
            last_line = no - 1
            finish(None, starts[idx])
            cur = None
            continue
        cur['body'].append(_strip(line, cur['q'], cur['w']))
    if cur is not None:
        problems.append(Problem(cur['line'], 'unclosed',
                                f"the fence opened here (```{cur['info']}) has no closer before EOF"))
        last_line = len(lines)
        finish(None, len(text))
    return Page(found, problems, frozenset(occupied))


def fences(text: str):
    """Every fence on a page, in order. Use parse() when the problems matter too."""
    return parse(text).fences


def fenced_text(text: str):
    """The raw text of each fence, opener line through closer line, prefix intact (the
    coverage advisory harvests identifiers from it, so the prefix does not matter)."""
    return [text[f.start:f.end] for f in parse(text).fences]


# ---- census ----------------------------------------------------------------

class Census(NamedTuple):
    pages: int
    fences: int
    by_lang: collections.Counter
    by_kind: collections.Counter
    orphans: list        # [(page, line, detail)]
    per_page: dict       # page -> Counter(lang)


def orphans_of(name: str, text: str, allowed_tags=None, page: Page | None = None) -> list:
    """The census's findings for one file's text: [(name, line, detail)].

    Structural orphans always (a marker line no returned fence opens or closes, an unclosed
    fence, a quote-break). With `allowed_tags` (a set of info strings), also every fence whose
    whole info string is outside it. check-links calls this without a tag set for the files
    outside docs/; census() calls it with ALLOWED_TAGS for docs/."""
    page = page or parse(text)
    accounted, found = set(), []
    for f in page.fences:
        accounted.add(f.line)
        if f.end_line is not None:
            accounted.add(f.end_line)
        if allowed_tags is not None and f.info not in allowed_tags:
            found.append((name, f.line, f'fence tag {f.info!r} is not in the allowed set '
                          f'({", ".join(repr(t) for t in sorted(allowed_tags))}): the gates select '
                          f'fences by an exact lowercase tag, so no gate reads this fence'))
    for no, line in enumerate(text.split('\n'), 1):
        if CENSUS_MARKER.match(line) and no not in accounted:
            why = next((pr.detail for pr in page.problems if pr.line == no),
                       'a marker line that no returned fence opens or closes')
            found.append((name, no, why))
    for pr in page.problems:
        if pr.kind != 'marker':        # unclosed / quote-break have no marker line of their own
            found.append((name, pr.line, f'{pr.kind}: {pr.detail}'))
    return found


def census(docs: pathlib.Path, allowed_tags=ALLOWED_TAGS) -> Census:
    by_lang, by_kind = collections.Counter(), collections.Counter()
    orphans: list = []
    per_page: dict = {}
    pages = list(sorted(pathlib.Path(docs).glob('*.md')))
    total = 0
    for p in pages:
        text = p.read_text(errors='replace')
        page = parse(text)
        for f in page.fences:
            by_lang[f.lang or 'untagged'] += 1
            by_kind[f.kind] += 1
            total += 1
        per_page[p.name] = collections.Counter(f.lang or 'untagged' for f in page.fences)
        orphans += orphans_of(p.name, text, allowed_tags, page)
    return Census(len(pages), total, by_lang, by_kind, sorted(set(orphans)), per_page)


def census_line(c: Census) -> str:
    order = sorted(c.by_lang, key=lambda k: (-c.by_lang[k], k))
    langs = ', '.join(f'{k} {c.by_lang[k]}' for k in order)
    return (f'{c.fences} fence(s) in {c.pages} page(s): {langs}; '
            f'{c.by_kind["quote"]} blockquoted, {c.by_kind["indent"]} indented, '
            f'{len(c.orphans)} orphan')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    # cwd-relative like every other reader verify-docs.sh runs (it cds to the repo root first);
    # a run from elsewhere finds no pages and FAILS on the zero floor rather than reading a
    # different tree than the caller meant.
    ap.add_argument('--docs', default='docs')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--census', action='store_true')
    g.add_argument('--counts', action='store_true',
                   help='machine line: JAVA n JSON n TOTAL n (the figures gates are compared to)')
    a = ap.parse_args(argv)
    c = census(pathlib.Path(a.docs))
    if a.counts:
        print(f'JAVA {c.by_lang["java"]} JSON {c.by_lang["json"]} TOTAL {c.fences} '
              f'PAGES {c.pages} ORPHANS {len(c.orphans)}')
        return 0
    floor = c.pages == 0 or c.fences == 0
    if floor:
        print(f'  FAIL  fence census visited {c.pages} page(s) and {c.fences} fence(s): a census '
              f'that examined nothing certifies nothing')
    else:
        print(f'  INFO  fence census: {census_line(c)}')
    # orphans are listed even under the floor: a tree whose only fences are refused markers
    # (four backticks, ~~~) has zero fences AND the orphans that explain why
    for page, line, why in c.orphans:
        print(f'  FAIL  {page}:{line}: {why}')
    return 1 if (floor or c.orphans) else 0


if __name__ == '__main__':
    sys.exit(main())
