#!/usr/bin/env python3
"""
Cases for handbook_md.py, run with the SITE venv's python (it needs `markdown` and `pymdownx`), against the
extension that sits beside this file:

  ~/.cache/handbook-site/venv/bin/python maintenance/site/check-extension.py

check-site-fixture.py runs it with $HANDBOOK_SITE_PY, once on the real extension and once per mutation of it
(on a copy of maintenance/site and maintenance/scripts), and pins which cases each mutation turns red. Nothing
here builds a site: the cases push small markdown through Python-Markdown with the same extensions zensical.toml
names, and compare the HTML. Prints one `CASE <name> ok|FAIL ...` line per case and a `EXTENSION n case(s)`
summary; exit 1 on any FAIL.

Each case states the GitHub behaviour it matches. The ones about lists, quotes, inline HTML and escapes were
measured against GitHub's own rendering (POST /markdown, mode gfm) on 2026-10-18.
"""
from __future__ import annotations
import os, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import markdown                                                       # noqa: E402

REPO = HERE.parents[1]
BASE = 'https://github.com/o/r'


def render(src: str, ref: str = 'REF') -> str:
    md = markdown.Markdown(
        extensions=['tables', 'toc', 'pymdownx.inlinehilite', 'pymdownx.superfences', 'handbook_md'],
        extension_configs={'toc': {'slugify': __import__('handbook_md').github(), 'permalink': False},
                           'handbook_md': {'base': BASE, 'ref': ref}})
    return md.convert(src)


def flat(html: str) -> str:
    """The HTML with its highlighting and whitespace flattened, so a case reads structure, not layout."""
    html = re.sub(r'<pre.*?</pre>', lambda m: '<PRE>' + re.sub(r'<[^>]+>', '', m.group(0)) + '</PRE>', html, flags=re.S)
    return re.sub(r'\s+', ' ', html).strip()


CASES = []


def case(ident, description):
    """A case has a short id (what check-site-fixture.py pins mutations by) and a sentence."""
    def deco(fn):
        CASES.append((ident, description, fn))
        return fn
    return deco


def has(html, *wanted, absent=()):
    f = flat(html)
    bad = [f'missing {w!r}' for w in wanted if w not in f] + [f'unexpected {a!r}' for a in absent if a in f]
    return bad


# ---- (a) links that leave docs/ ------------------------------------------------------------------------------
@case('link_blob', 'link: ../CLAUDE.md goes to github.com blob at the ref')
def _():
    return has(render('[c](../CLAUDE.md)'), f'href="{BASE}/blob/REF/CLAUDE.md"')


@case('link_tree', 'link: a trailing slash is a tree, and the fragment is kept')
def _():
    return has(render('[d](../examples/ui/#top)'), f'href="{BASE}/tree/REF/examples/ui#top"')


@case('link_dir', 'link: an existing directory without a trailing slash is a tree too (examples/ exists in the tree)')
def _():
    return has(render('[d](../examples)'), f'href="{BASE}/tree/REF/examples"')


@case('link_frag', 'link: a file keeps its fragment and is a blob')
def _():
    return has(render('[f](../examples/ui/src/Foo.java#L3)'), f'href="{BASE}/blob/REF/examples/ui/src/Foo.java#L3"')


@case('link_ref', 'link: the ref is the configured one')
def _():
    return has(render('[c](../CLAUDE.md)', ref='abc123'), f'href="{BASE}/blob/abc123/CLAUDE.md"')


@case('link_alone', 'link: inside docs/, a URL, a fragment and a path out of the repository are left alone')
def _():
    return has(render('[a](other.md) [b](../docs/other.md) [c](https://x.invalid/y) [d](#frag) [e](../../out.txt) [f](/abs) '
                      '[g](https://x.invalid/a/../../../../x) [h](mailto:a@b.invalid)'),
               'href="other.md"', 'href="../docs/other.md"', 'href="https://x.invalid/y"', 'href="#frag"',
               'href="../../out.txt"', 'href="/abs"', 'href="https://x.invalid/a/../../../../x"', 'href="mailto:a@b.invalid"',
               absent=('github.com',))


# ---- (b)/(c) anchors -------------------------------------------------------------------------------------------
@case('anchor_dup', 'anchor: a duplicate heading is x-1, x-2 (GitHub), not x_1')
def _():
    return has(render('## X\n\n## X\n\n## X\n'), 'id="x"', 'id="x-1"', 'id="x-2"', absent=('x_1',))


@case('anchor_slug', 'anchor: the slug is the character rule (a code-span generic, a dash, parentheses)')
def _():
    return has(render('## `Codec<T>`\n\n## Foo — Bar\n\n## A (B)\n'), 'id="codect"', 'id="foo--bar"', 'id="a-b"')


# ---- (d) lists -------------------------------------------------------------------------------------------------
@case('list_bullet', 'lists: a bullet straight after a paragraph line starts a list')
def _():
    return has(render('text\n- a\n- b\n'), '<p>text</p> <ul> <li>a</li> <li>b</li> </ul>')


@case('list_ordered', 'lists: 1. starts a list after a paragraph line, 2. does not (CommonMark)')
def _():
    return has(render('text\n1. a\n2. b\n\nmore\n2. c\n'), '<p>text</p> <ol>', '<p>more 2. c</p>')


@case('list_quote', 'lists: inside a blockquote too')
def _():
    return has(render('> **Gotchas**\n> - a\n> - b\n'), '<blockquote> <p><strong>Gotchas</strong></p> <ul> <li>a</li> <li>b</li> </ul> </blockquote>')


@case('list_fence', 'lists: a code fence is left exactly as written (no blank line inside it)')
def _():
    import html
    out = render('```\nintro line\n * javadoc\n- dash\n1. one\n```\n')
    text = html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<pre.*?</pre>', out, re.S).group(0))).strip('\n')
    want = 'intro line\n * javadoc\n- dash\n1. one'
    return [] if text == want else [f'the fence content became {text!r}, wanted {want!r}']


@case('list_after_fence', 'lists: an item after a closed fence stays in the list')
def _():
    out = flat(render('- a\n  ```\n  x\n  ```\n- b\n'))
    return [] if out.count('<li>') == 2 and out.count('<ul>') == 1 and '<p>b</p>' in out and '- b' not in out else [f'got {out!r}']


@case('list_not_start', 'lists: a thematic break and a line of html are not list starts')
def _():
    return has(render('text\n\n* * *\n\n<div>\n- not a list\n</div>\n'), '<hr', '- not a list', absent=('<ul>',))


@case('list_loose', 'lists: a loose list stays one list (not one <ul> per item)')
def _():
    out = flat(render('- a\n\n- b\n\n- c\n'))
    return [] if out.count('<ul>') == 1 and out.count('<li>') == 3 else [f'got {out!r}']


@case('list_nested', 'lists: a nested item at four spaces nests')
def _():
    return has(render('- a\n    - b\n- c\n'), '<li>a<ul> <li>b</li> </ul> </li>')


# ---- (e) blockquotes -------------------------------------------------------------------------------------------
@case('quote_two', 'quotes: two > blocks with a blank line between are two boxes (CommonMark)')
def _():
    out = flat(render('> a\n\n> b\n'))
    return [] if out.count('<blockquote>') == 2 else [f'got {out!r}']


@case('quote_one', 'quotes: a > line with nothing after it keeps one box')
def _():
    out = flat(render('> a\n>\n> b\n'))
    return [] if out.count('<blockquote>') == 1 and '<p>a</p> <p>b</p>' in out else [f'got {out!r}']


# ---- (f) inline html, (g) escapes ----------------------------------------------------------------------------
@case('html_text', 'html: <GameMode, Settings> is text (a comma makes it no tag), <b> is a tag')
def _():
    return has(render('Map<GameMode, InteractionSettings> and <b>bold</b>'), 'Map&lt;GameMode, InteractionSettings&gt;', '<b>bold</b>')


@case('escape_quote', 'escapes: \\" prints the quote without its backslash')
def _():
    return has(render('FaceType in \\"Supporting\\" of'), 'in "Supporting" of', absent=('\\',))


@case('table_pipe', 'an escaped pipe in a code span in a table cell is a pipe, and outside a table the backslash stays')
def _():
    return has(render('| a | b |\n|---|---|\n| `c\\|d` | x\\|y |\n\n`e\\|f`\n'), '<code>c|d</code>', '<td>x|y</td>', '<code>e\\|f</code>')


@case('list_quote_end', 'a list straight after a quote line is a list outside the quote (GitHub), not a lazy line of the quote')
def _():
    out = flat(render('> quote text\n- item\n- item2\n'))
    ok = out.startswith('<blockquote> <p>quote text</p> </blockquote> <ul> <li>item</li> <li>item2</li> </ul>')
    out2 = flat(render('> - a\n- b\n'))
    ok2 = '</blockquote> <ul> <li>b</li> </ul>' in out2
    return [] if ok and ok2 else [f'got {out!r} and {out2!r}']


@case('list_indented_code', 'a list-looking line in an indented code block gets no blank line')
def _():
    import html
    out = render('Para\n\n    code line\n    - not a list\n')
    text = html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<pre.*?</pre>', out, re.S).group(0))).strip('\n')
    return [] if text == 'code line\n- not a list' else [f'the code became {text!r}']


@case('list_two_dot', 'text, `2. foo`, then a bullet: `2. foo` is paragraph text and the bullet starts the list (GitHub)')
def _():
    return has(render('Text\n2. foo\n- bar\n'), '<p>Text 2. foo</p> <ul> <li>bar</li> </ul>')


@case('list_orphan_fence', 'a ~~~ or four-backtick fence is left untouched (no blank line inside it)')
def _():
    import html
    out = ''
    for src in ('Para\n~~~\ntext\n- inside\n~~~\n', 'Para\n````\ntext\n- inside\n```\n- still\n````\n'):
        o = render(src)
        t = html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<pre.*?</pre>', o, re.S).group(0))).strip('\n')
        if '\n\n' in t:
            return [f'a blank line was inserted into the fence: {t!r}']
    return []


@case('escape_amp_lt', '`\\&` and `\\<` print the character without the backslash')
def _():
    return has(render('AT\\&T and \\<b\\> and 1\\. x'), 'AT&amp;T and &lt;b&gt; and 1. x', absent=('\\',))


@case('base_required', 'an extension configured without the repository URL refuses to load')
def _():
    try:
        markdown.Markdown(extensions=['handbook_md']).convert('x')
    except ValueError as e:
        return [] if 'base' in str(e) else [f'ValueError without the word base: {e}']
    return ['it loaded']


def main() -> int:
    bad = 0
    for ident, description, fn in CASES:
        try:
            problems = fn()
        except Exception as e:          # noqa: BLE001
            problems = [f'raised {type(e).__name__}: {e}']
        if problems:
            bad += 1
            print(f'CASE {ident} FAIL {description} - {"; ".join(problems)}')
        else:
            print(f'CASE {ident} ok')
    print(f'EXTENSION {len(CASES)} case(s): {len(CASES) - bad} passed, {bad} failed')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
