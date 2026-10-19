#!/usr/bin/env python3
"""
Docs markdown that renders the same on GitHub and on the site (Zensical, i.e. Python-Markdown).

The docs are written for GitHub and the site must show what GitHub shows. Most of the differences between
the two renderers are absorbed by maintenance/site/handbook_md.py (a list after a paragraph line, adjacent
blockquotes, inline HTML, backslash escapes). Two kinds cannot be, because the source says something one
renderer cannot read, and this lint refuses them. Both are found outside code fences, with file:line.

RULE heading-generic. A heading with a `<` outside a code span. GitHub drops `<KeyType>` from the heading's
text and anchor but keeps `<K, T>`; Python-Markdown has its own opinion of both. Every renderer agrees on a
heading written ``### `Codec<T>` ``, whose anchor is `codect`. 48 headings had the raw form at d361e13
(9 pages); the lint's population is that count, and it is 0 now.

RULE table-code-pipe. A `|` inside a code span on a table row that is not written `\\|`. GitHub splits a table row on
every unescaped pipe, code span or not, so `/whitelist add|remove|clear` in a cell made three cells (docs/
permissions.md:496 at d361e13, the one case; review of d361e13..9f19ac9, MINOR-1). The site rewrites `\\|` inside
table code to `|` (handbook_md.py, h), so writing the escape is right on both.

RULE list-child-indent. A child of a list item (a nested list item, or a paragraph, table or fence that follows
a blank line inside the item) indented fewer than 4 spaces past its parent's marker. CommonMark nests a child
indented to the parent's content (2 spaces under `- `, 3 under `1. `), which is what the docs were written to;
Python-Markdown needs 4, and reads a 2-space nested item as a sibling and a 2-space fence as the end of the
list (the items after it start a new `<ul>`). A child indented 4 past its parent is a child on both. Measured
at d361e13: 9 nested items on 2 pages (block-access.md, combat.md) and 2 continuation blocks (worldgen.md,
interactions-double-run.md).

  python3 maintenance/scripts/check-site-markdown.py [--root DIR] [--fix]

--fix re-indents every flagged child block (itself and what hangs from it) by the missing spaces, which
changes whitespace and nothing else. Exit 0 clean, 1 findings, 2 the corpus is absent or empty.
Prints `SCANNED <pages> page(s), <headings> heading(s) read, <list items> list item(s) read`.
"""
from __future__ import annotations
import argparse, importlib.util, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import doc_fences

_spec = importlib.util.spec_from_file_location('check_links_for_markdown', HERE / 'check-links.py')
CL = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CL)

QUOTE = re.compile(r'^((?:[ ]{0,3}>[ ]?)*)(.*)$')
HEADING = re.compile(r'^#{1,6}\s+(.*?)\s*#*$')
ITEM = re.compile(r'^( *)([*+-]|\d+[.)])( +)(?=\S)')
THEMATIC = re.compile(r'^ {0,3}(?:(?:-[ ]*){3,}|(?:\*[ ]*){3,}|(?:_[ ]*){3,})$')


def outside_code(t: str) -> str:
    """`t` with its code spans removed."""
    return CL.CODE_SPAN.sub('', t)


def heading_findings(text: str, fenced):
    out, read = [], 0
    for no, line in enumerate(text.split('\n'), 1):
        m = HEADING.match(line)
        if m and no not in fenced:
            read += 1
            if '<' in outside_code(m.group(1)):
                out.append((no, 'heading-generic', f'a `<` outside a code span in a heading: {m.group(1)!r} (write the generic in backticks)'))
    return out, read


def table_findings(text: str, fenced):
    """-> [(line, rule, message)]: a bare `|` in a code span on a table row (a line that starts with `|`)."""
    out = []
    for no, line in enumerate(text.split('\n'), 1):
        if no in fenced:
            continue
        rest = QUOTE.match(line).group(2).lstrip()
        if not rest.startswith('|'):
            continue
        for m in CL.CODE_SPAN.finditer(rest):
            if re.search(r'(?<!\\)\|', m.group(2)):
                out.append((no, 'table-code-pipe',
                            f'a `|` inside a code span on a table row splits the cell on GitHub (write `\\|`): {m.group(0)[:60]!r}'))
    return out


def list_findings(text: str, fenced):
    """-> ([(line, rule, message, delta)], list items read). `delta` is the indentation the child lacks."""
    lines = [l.expandtabs(4) for l in text.split('\n')]
    out, items_read = [], 0
    stack = []                      # open items: (marker column, content column), outermost first
    prev_blank = True
    prefix_seen = ''
    for no, raw in enumerate(lines, 1):
        opener = no in fenced and (no - 1) not in fenced
        if no in fenced and not opener:
            continue                # inside a fence: its lines are the fence's, not blocks
        prefix, line = QUOTE.match(raw).groups()
        if prefix != prefix_seen:
            stack, prev_blank, prefix_seen = [], True, prefix
        if not line.strip():
            prev_blank = True
            continue
        indent = len(line) - len(line.lstrip(' '))
        m = None if opener else ITEM.match(line)
        if m and not THEMATIC.match(line):
            items_read += 1
            col, content = len(m.group(1)), len(m.group(1)) + len(m.group(2)) + len(m.group(3))
            while stack and stack[-1][0] >= col:
                stack.pop()
            if stack and col >= stack[-1][1] and col - stack[-1][0] < 4:
                out.append((no, 'list-child-indent',
                            f'a nested list item indented {col - stack[-1][0]} past its parent (needs 4): {line.strip()[:60]!r}',
                            4 - (col - stack[-1][0])))
            stack.append((col, content))
            prev_blank = False
            continue
        # not an item: a block or a continuation line. A block that starts after a blank line belongs to the
        # innermost open item whose content column it reaches. A fence straight after an item line needs no
        # more than the item's content column on either renderer (measured: superfences keeps it in the item at
        # any indent), so only a fence after a blank line is judged.
        if prev_blank:
            while stack and indent < stack[-1][1]:
                stack.pop()
            if stack and indent - stack[-1][0] < 4:
                kind = 'a fence' if opener else 'a block'
                out.append((no, 'list-child-indent',
                            f'{kind} inside a list item indented {indent - stack[-1][0]} past the item (needs 4): {line.strip()[:60]!r}',
                            4 - (indent - stack[-1][0])))
        prev_blank = False
    return out, items_read


def scan_page(text: str):
    fenced = doc_fences.parse(text).fence_lines
    hs, nh = heading_findings(text, fenced)
    ls, ni = list_findings(text, fenced)
    return hs + [(no, rule, msg) for no, rule, msg in table_findings(text, fenced)], ls, nh, ni


def fix_page(text: str) -> str:
    """Re-indent each flagged child block by the spaces it lacks. A block runs from its first line to the last line
    before one that is less indented (blank lines and fence lines go with it). Whitespace only."""
    fenced = doc_fences.parse(text).fence_lines
    ls, _ = list_findings(text, fenced)
    lines = text.split('\n')
    shift = [0] * (len(lines) + 1)
    for no, _rule, _msg, delta in ls:
        indent = len(QUOTE.match(lines[no - 1]).group(2)) - len(QUOTE.match(lines[no - 1]).group(2).lstrip(' '))
        j = no
        while j < len(lines):
            nxt = j + 1
            if nxt > len(lines):
                break
            line = QUOTE.match(lines[nxt - 1]).group(2)
            if nxt in fenced or not line.strip():
                j = nxt
                continue
            if len(line) - len(line.lstrip(' ')) < indent:
                break
            j = nxt
        end = j
        while end > no and not lines[end - 1].strip():
            end -= 1
        for k in range(no, end + 1):
            if lines[k - 1].strip():
                shift[k] = max(shift[k], delta)
    out = []
    for k, l in enumerate(lines, 1):
        if shift[k]:
            pre = QUOTE.match(l).group(1)
            out.append(pre + ' ' * shift[k] + l[len(pre):])
        else:
            out.append(l)
    return '\n'.join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(HERE.parents[1]))
    ap.add_argument('--fix', action='store_true')
    a = ap.parse_args()
    docs = sorted((pathlib.Path(a.root) / 'docs').glob('*.md'))
    if not docs:
        print(f'  SKIP  no docs/*.md under {a.root}')
        return 2
    findings, nh, ni = [], 0, 0
    for p in docs:
        text = p.read_text()
        hs, ls, h, i = scan_page(text)
        nh += h; ni += i
        findings += [(p.name, *f[:3]) for f in hs + ls]
        if a.fix and ls:
            p.write_text(fix_page(text))
    print(f'  INFO  {len(docs)} page(s), {nh} heading(s) and {ni} list item(s) read')
    for name, no, rule, msg in findings:
        print(f'  FAIL  docs/{name}:{no}: {rule}: {msg}')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
