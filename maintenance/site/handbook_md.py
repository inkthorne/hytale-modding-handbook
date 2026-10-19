r"""Python-Markdown extension for the handbook's Zensical build (loaded as `handbook_md` from PYTHONPATH).

The docs are written for GitHub: relative links, GitHub's heading anchors. Three things differ on the site,
and this module makes the site agree with GitHub rather than the other way round. The source is never edited.

(a) LINKS THAT LEAVE docs/. `../examples/...` and `../CLAUDE.md` are repo paths, not site pages, and the site
    has nothing at them. They are rewritten to github.com at the ref being built (env HANDBOOK_REF, default
    `main`): `tree` for a directory, `blob` for anything else, the `#fragment` kept. The rewrite runs as a
    treeprocessor at priority 1, before Zensical's own link processor (priority 0), which would otherwise
    resolve the `.md` ones against the docs and warn "page does not exist" (it still does, once, for
    `../CLAUDE.md`: Zensical validates the source text, not the tree, and the build section of verify-docs
    explains that one warning by name). It resolves `../` against docs/ and assumes docs/ is FLAT, which
    verify-docs checks.
(b) DUPLICATE ANCHORS. A second heading `X` is `x-1` on GitHub and `x_1` in Python-Markdown's toc, so a link
    that works on GitHub broke on the site. `toc.unique` is replaced by GitHub's `-N` numbering.
(c) THE SLUG. `github()` is the `toc.slugify` factory; it applies check-links.py's `char_slug`, the character
    rule alone. The tag rule (`<KeyType>` is dropped) is not applied here: verify-docs lints every heading
    that would need it, so by the time a heading reaches the site its text is plain characters, and the
    site and GitHub compute from the same ones. That agreement is measured per page (verify-docs, "The site
    builds ...": every anchor check-links computes must be an id in the built page), not assumed.

(d) LISTS AFTER A PARAGRAPH LINE. GitHub starts a list where a bullet (or `1.`) follows a paragraph line;
    Python-Markdown needs a blank line, and reads the list as run-on text without one (the preprocessor adds 162 blank
    lines on 63 pages: lists after a paragraph line, in blockquotes, and after a closed fence).
    `mdx_breakless_lists` does the same job and was measured to add a blank line INSIDE code fences wherever a
    fenced line looks like a list item (` * comment` in Javadoc, `1. step` in a diagram): 7 of 2,066 code
    blocks changed. `ListBreaks` below is its replacement, fence-aware by doc_fences.py's reader and
    blockquote-aware (the extension's pattern never matched a `> - item` line). `mdx_truly_sane_lists` was
    measured too and is not used: it splits one loose list into one `<ul>` per item and reads a 4-space
    nested item as text.
(e) ADJACENT BLOCKQUOTES. Python-Markdown merges two `>` blocks into one box however many blank lines
    separate them; CommonMark ends a quote at a blank line, so GitHub shows two boxes. `SeparateQuotes` keeps
    them apart. A quote that continues across a `>` line with nothing after it is still one block and still
    one box.

(f) INLINE HTML. Python-Markdown calls `<GameMode, InteractionSettings>` an HTML tag (a name, a space, anything) and
    emits it raw, where the browser drops it: `Map<GameMode, InteractionSettings>` lost its type argument on the
    site (interactions-combat.md:106, in a table cell). CommonMark, which GitHub follows, needs a name and then
    attributes, so a comma makes it text. The inline-HTML pattern is replaced by CommonMark's, the one
    check-links.py slugs headings with.
(g) BACKSLASH ESCAPES. CommonMark lets a backslash escape any ASCII punctuation; Python-Markdown knows 16
    characters, so `\"Supporting\"` printed its backslashes (items-blocks.md:462). The rest are added, except
    `&`, `<` and `|`, which it writes raw or handles elsewhere (a table cell).

(h) PIPES IN TABLE CODE. In a table cell GitHub writes `\|` as `|`, in a code span too (a row cannot hold a bare pipe,
    so the escape is the only way to show one). Python-Markdown's tables extension drops the backslash from cell text
    and keeps it inside `<code>`: 17 spans on 5 pages (camera.md 12, 02-structure.md 2, entities.md, player.md and
    trigger-volumes.md 1 each) showed `\|` where GitHub shows `|` (review of d361e13..9f19ac9, MINOR-1).
    `TableCodePipes` removes the backslash from code inside td and th. The converse, a bare pipe inside a code span
    on a table row, splits the cell on GitHub and is refused by check-site-markdown.py.

Paths are resolved from this file, never from the working directory or an environment variable: the build
runs in a copy of the tree (zensical writes `.cache/` beside the config), and the copy keeps the layout.

Both (a) and (b) ride on the Python-Markdown path that Zensical says it is moving to Rust
(zensical/markdown/render.py). A zensical version bump is its own item and re-runs the parity comparison,
the anchor cross-check and the negative control.
"""
from __future__ import annotations

import importlib.util
import os
import posixpath
import urllib.parse
from pathlib import Path

import markdown.extensions.toc as _toc
import re

from markdown import Extension
from markdown.blockprocessors import BlockQuoteProcessor
from markdown.inlinepatterns import HtmlInlineProcessor
from markdown.preprocessors import Preprocessor
from markdown.treeprocessors import Treeprocessor
from markdown.util import HTML_PLACEHOLDER_RE
from xml.etree import ElementTree as etree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                                   # maintenance/site/ -> the repository root
_CHECK_LINKS = REPO / "maintenance" / "scripts" / "check-links.py"


def _load_check_links():
    spec = importlib.util.spec_from_file_location("handbook_check_links", _CHECK_LINKS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_check_links = _load_check_links()
char_slug = _check_links.char_slug


def _load_doc_fences():
    spec = importlib.util.spec_from_file_location("handbook_doc_fences", REPO / "maintenance" / "scripts" / "doc_fences.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


doc_fences = _load_doc_fences()


def slugify(text, sep):
    return char_slug(text)


def github(**_kw):
    """The `toc.slugify` factory: Zensical calls it with the configured kwds and gets `slugify(text, sep)`.
    A module-level function, not a closure: Zensical pickles the markdown configuration to hash it."""
    return slugify


def github_unique(id, ids):
    """GitHub's duplicate numbering: `x`, `x-1`, `x-2` (Python-Markdown's is `x`, `x_1`, `x_2`)."""
    base, n = id, 0
    while id in ids or not id:
        n += 1
        id = f"{base}-{n}"
    ids.add(id)
    return id


_toc.unique = github_unique


class Rewrite(Treeprocessor):
    def __init__(self, md, base, ref):
        super().__init__(md)
        self.base = base.rstrip("/")
        self.ref = ref

    def target(self, href):
        """The GitHub URL for a relative href that resolves outside docs/, else None."""
        if not href or href.startswith(("#", "/")) or urllib.parse.urlsplit(href).scheme or href.startswith("//"):
            return None
        path, _, frag = href.partition("#")
        path = urllib.parse.unquote(path.partition("?")[0])
        if not path:
            return None
        rel = posixpath.normpath(posixpath.join("docs", path))
        if rel == "docs" or rel.startswith("docs/") or rel == ".." or rel.startswith("../"):
            return None                       # inside docs/ (the site's), or out of the repository
        is_dir = path.endswith("/") or (REPO / rel).is_dir()
        url = f"{self.base}/{'tree' if is_dir else 'blob'}/{self.ref}/{urllib.parse.quote(rel)}"
        return url + (f"#{frag}" if frag else "")

    def run(self, root):
        for a in root.iter("a"):
            new = self.target(a.get("href", ""))
            if new:
                a.set("href", new)


QUOTE_PREFIX = re.compile(r"^((?:[ ]{0,3}>[ ]?)*)(.*)$")
# A bullet, or `1.`, followed by a space and some content: what CommonMark lets interrupt a paragraph
# (an empty item and an ordered list that starts at another number cannot).
ITEM = re.compile(r"^[ ]*(?:[*+-]|1\.)[ ]+\S")
ITEM_ANY = re.compile(r"^[ ]*(?:[*+-]|\d+\.)[ ]+\S")


class ListBreaks(Preprocessor):
    """A blank line before a list that follows a paragraph line, as GitHub reads it. Never inside a fence."""

    def run(self, lines):
        fenced = doc_fences.parse("\n".join(lines)).fence_lines
        out = []
        in_item = False          # inside a run of list lines (a continuation line keeps the run going)
        prev_prefix, prev_text = "", False     # the previous line's quote prefix, and whether it was paragraph text
        prev_fence = False       # the previous line closed a fence: its placeholder would swallow an item that follows
        for no, line in enumerate(lines, 1):
            if no in fenced:
                out.append(line)
                in_item, prev_text, prev_prefix = False, False, ""
                prev_fence = (no + 1) not in fenced
                continue
            prefix, rest = QUOTE_PREFIX.match(line).groups()
            was_fence, prev_fence = prev_fence, False
            if prefix != prev_prefix:
                in_item, prev_text = False, False
            if not rest.strip():
                in_item, prev_text = False, False
            elif ITEM.match(rest):
                if (prev_text and not in_item) or was_fence:
                    out.append(prefix.rstrip())
                in_item, prev_text = True, False
            elif ITEM_ANY.match(rest):
                in_item, prev_text = True, False
            else:
                # a line of text (a thematic break and a line of html are handled by Python-Markdown itself: a blank
                # line inserted before a list after either changes nothing, measured, so neither is special-cased)
                prev_text = not in_item
            prev_prefix = prefix
            out.append(line)
        return out


class TableCodePipes(Treeprocessor):
    """`\\|` in a code span in a table cell is `|`, as GitHub shows it.

    pymdownx.inlinehilite (enabled in zensical.toml) takes every backtick span: the <code> element holds only a
    placeholder and the text sits in the html stash, so both places are rewritten; the first version looked at
    code.text alone and changed nothing in the real build (measured: 18 spans still showed the backslash)."""

    def run(self, root):
        stash = self.md.htmlStash.rawHtmlBlocks
        for cell in root.iter():
            if cell.tag in ("td", "th"):
                for code in cell.iter("code"):
                    if not code.text:
                        continue
                    m = HTML_PLACEHOLDER_RE.fullmatch(code.text)
                    if m:
                        i = int(m.group(1))
                        stash[i] = stash[i].replace("\\|", "|")
                    elif "\\|" in code.text:
                        code.text = type(code.text)(code.text.replace("\\|", "|"))


class SeparateQuotes(BlockQuoteProcessor):
    """BlockQuoteProcessor.run with the sibling merge removed: every block that starts a quote starts a box."""

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()]
            self.parser.parseBlocks(parent, [before])
            block = "\n".join([self.clean(line) for line in block[m.start():].split("\n")])
        quote = etree.SubElement(parent, "blockquote")
        self.parser.state.set("blockquote")
        self.parser.parseChunk(quote, block)
        self.parser.state.reset()


class HandbookExtension(Extension):
    def __init__(self, **kw):
        self.config = {
            "base": ["", "The repository URL, e.g. https://github.com/OWNER/REPO (required)"],
            "ref": [os.environ.get("HANDBOOK_REF") or "main", "The git ref the rewritten links point at"],
        }
        super().__init__(**kw)

    def extendMarkdown(self, md):
        base = self.getConfig("base")
        if not base:
            raise ValueError("handbook_md: `base` (the repository URL) is not configured")
        md.treeprocessors.register(Rewrite(md, base, self.getConfig("ref")), "handbook_rewrite", 1)
        md.treeprocessors.register(TableCodePipes(md), "handbook_table_code_pipes", 1)
        md.preprocessors.register(ListBreaks(md), "handbook_list_breaks", 27)
        md.parser.blockprocessors.register(SeparateQuotes(md.parser), "quote", 20)
        md.inlinePatterns.register(HtmlInlineProcessor("(" + _check_links.RAW_HTML.pattern + ")", md), "html", 90)
        md.ESCAPED_CHARS.extend(c for c in "\"$%',/:;=?@^~" if c not in md.ESCAPED_CHARS)


def makeExtension(**kw):
    return HandbookExtension(**kw)
