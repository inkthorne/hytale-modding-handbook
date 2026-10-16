#!/usr/bin/env python3
"""
Fixture for doc_fences.py, the ONE fence reader every gate shares, and for each gate's use of it.

WHAT THIS GUARDS. Nine readers carried nine regexes for "where a fence starts" and they
disagreed: the column-0 ones (check-symbols, check-snippets, three verify-docs.sh readers)
could not see the 3 java and 1 json fences inside a blockquote or the 2 java and 4 json
indented in list items (measured at bc10b45), so a dead `Receiver.member` or a package-led
block that does not compile could have sat in one with every gate green. doc_fences.py is
the single reader, the census in verify-docs.sh fails on any ``` or ~~~ marker that belongs
to no fence it returned, and THIS file is what shows each gate reads through it.

THREE LAYERS, each with its own cases:
  reader    exact fences and problems for every container rule (col0, indented, blockquoted,
            `> >`, blockquote holding an indented fence, bare-`>` blank line, tab-indented
            closer) and every refusal (unclosed, 4-backtick, ~~~, ```lang inside a fence, a
            closer whose prefix shape differs, a body line missing the opener's `>`, a fence
            opener behind a list marker, inline code at a line start);
  census    the CLI on synthetic page sets: each orphan is a FAIL naming file:line, and a
            census that visited zero pages or zero fences is a FAIL;
  gates     a synthetic docs tree with a planted defect in a BLOCKQUOTED and in an INDENTED
            fence, run through the real gate: a dead Receiver.member (check-symbols), a
            package-led block that fails javac (check-snippets), an unregistered "Type" and a
            "Type" registered only in a quoted java fence (check-type-values), a fence root key
            that changes a binding and so exposes a wrong Default (section_binder, check-defaults),
            and the four verify-docs.sh inline readers (JSON parse, doc-type, code names, fields),
            extracted from verify-docs.sh itself so the fixture runs the code that ships.
            Each case also has a HEALTHY twin (the same tree with the defects repaired) that must
            pass: a red for the wrong reason is as worthless as a green for the wrong reason.

--mutations: for every container rule and every refusal, a mutant of doc_fences.py with that one
guard removed, which must turn the case(s) NAMED for that guard red; and for every gate, a
mutant whose `doc_fences` is a verbatim copy of that gate's OLD reader (the regex at bc10b45),
shadowing the real module in the temp dir that holds the gate copy, which must turn the gate's
content case red. check-defaults has no reader of its own: it reads fences only through
section_binder, so its mutation is the binder's. code names and fields get a reader that
returns nothing instead of an old regex: their old regexes were unanchored and already read
blockquoted and indented fences, so no content case could have been red for them; what the
mutation guards is the fence count each prints, which verify-docs.sh compares with the census.
A mutation whose anchor is not present exactly once is a FAIL (it tests nothing), and so is a
mutant that crashes (a traceback is not a detection).

HEADINGS. A third reader of a page's text is the heading readers (check-links, section_binder,
verify-docs.sh's doc-type `_sections` and its gotcha `## ` scan). A `# comment` line in a bash
fence matches a heading pattern, so before 2026-10-16 each of them read it as a heading. They
now take their headings only from lines outside doc_fences.py's `fence_lines`. The `headings`
group plants such a line in a column-0 fence (and a blockquoted one, which is a PIN: `> # x` never
matched `^#`) and requires each reader to ignore it; its mutations restore the fence-blind
heading scan in each reader, and two reader mutations break `fence_lines` itself.

Usage:
  python3 maintenance/scripts/check-doc-fences-fixture.py [-v]
  python3 maintenance/scripts/check-doc-fences-fixture.py --mutations [-v]
"""
from __future__ import annotations
import argparse, contextlib, importlib.util, io, os, pathlib, shutil, subprocess, sys, tempfile, textwrap, time, zipfile

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
VERIFY = HERE / 'verify-docs.sh'
READER = HERE / 'doc_fences.py'
FIXTURES = REPO / 'maintenance' / 'fixtures'
TV_CORPUS = FIXTURES / 'type-values' / 'corpus'
DEF_CORPUS = FIXTURES / 'defaults' / 'corpus'

# FLOORS: raise freely, lowering one needs a reason in the commit message. The fixture guards
# the reader and nothing guards the fixture; a table that quietly shrank would report "every
# mutation red" over fewer mutations, which is the sentence this repo keeps having to prevent.
MIN_CASES = 99
MIN_MUTATIONS = 48


# ---------------------------------------------------------------------------------------------
# synthetic jar: com.hypixel.fx.Widget, so check-symbols and check-snippets run against a jar
# whose members are known. Built with javac, zipped with zipfile; no game jar is needed.
# ---------------------------------------------------------------------------------------------
def make_jar(td: pathlib.Path) -> pathlib.Path:
    src = td / 'jarsrc' / 'com' / 'hypixel' / 'fx'
    src.mkdir(parents=True)
    (src / 'Widget.java').write_text(
        'package com.hypixel.fx;\npublic class Widget {\n    public static int realMember() { return 1; }\n}\n')
    out = td / 'jarclasses'
    out.mkdir()
    subprocess.run(['javac', '-proc:none', '-nowarn', '-d', str(out), str(src / 'Widget.java')],
                   check=True, capture_output=True)
    jar = td / 'fx.jar'
    with zipfile.ZipFile(jar, 'w') as z:
        for f in out.rglob('*.class'):
            z.write(f, f.relative_to(out).as_posix())
    return jar


# ---------------------------------------------------------------------------------------------
# the OLD readers, verbatim from bc10b45, as shadow modules. Each exposes the doc_fences API the
# gates call (parse().of/.fence_lines, fences(), fenced_text()) and nothing newer.
# ---------------------------------------------------------------------------------------------
SHIM_HEAD = '''
import re
from typing import NamedTuple
class Fence(NamedTuple):
    lang: str; line: int; end_line: object; body: str; body_line: int; kind: str; closed: bool
    quotes: int; indent: int; start: int; end: int; info: str
class Page(NamedTuple):
    fences: list; problems: list; fence_lines: frozenset
    def of(self, lang): return [f for f in self.fences if f.lang == lang]
def _mk(lang, line, end_line, body, start, end):
    return Fence(lang, line, end_line, body, line + 1, 'col0', end_line is not None, 0, 0, start, end, lang)
def fences(text): return parse(text).fences
def fenced_text(text): return [text[f.start:f.end] for f in parse(text).fences]
import pathlib, collections
def census(docs):
    n = sum(len(parse(p.read_text()).fences) for p in pathlib.Path(docs).glob('*.md'))
    return collections.namedtuple('Census', 'fences')(n)
'''

# check-symbols, check-snippets, and the doc-type reader: a line toggle anchored at column 0
# (check-symbols' `fence_open`; the others' `^```java`/`^```(\\w*)` are the same reach).
SHIM_COL0 = SHIM_HEAD + '''
_OPEN = re.compile(r"^```([a-zA-Z]*)\\s*$")
def parse(text):
    lines = text.split("\\n"); off = 0; cur = None; fs = []; occ = set()
    for i, ln in enumerate(lines, 1):
        m = _OPEN.match(ln)
        if m:
            if cur is None:
                cur = [m.group(1) or "", i, [], off]
            else:
                fs.append(_mk(cur[0], cur[1], i, "".join(b + "\\n" for b in cur[2]), cur[3], off + len(ln)))
                occ.update(range(cur[1], i + 1)); cur = None
        elif cur is not None:
            cur[2].append(ln)
        off += len(ln) + 1
    return Page(fs, [], frozenset(occ))
'''

# check-type-values: FENCE, indentation allowed, no blockquote, body unstripped.
SHIM_INDENT = SHIM_HEAD + '''
FENCE = re.compile(r'^([ \\t]*)```(\\w*)[^\\n]*\\n(.*?)^[ \\t]*```', re.M | re.S)
def parse(text):
    fs = [_mk(m.group(2), text.count("\\n", 0, m.start()) + 1, None, m.group(3), m.start(), m.end())
          for m in FENCE.finditer(text)]
    return Page(fs, [], frozenset())
'''

# section_binder: JSON_FENCE, indentation allowed, body read with the indentation still on it.
SHIM_BINDER = SHIM_HEAD + '''
JSON_FENCE = re.compile(r'^[ \\t]*```json[^\\n]*\\n(.*?)^[ \\t]*```', re.M | re.S)
def parse(text):
    fs = [_mk("json", text.count("\\n", 0, m.start()) + 1, None, m.group(1), m.start(), m.end())
          for m in JSON_FENCE.finditer(text)]
    return Page(fs, [], frozenset())
'''

# verify-docs.sh JSON-parse check: unanchored, so a blockquoted fence IS found, with its `> ` on every line.
SHIM_UNANCHORED = SHIM_HEAD + '''
def parse(text):
    fs = [_mk("json", 0, None, b, 0, 0) for b in re.findall(r'```json\\n(.*?)```', text, re.S)]
    return Page(fs, [], frozenset())
'''

# code names and fields: a reader that returns nothing (see the module docstring for why).
SHIM_NONE = SHIM_HEAD + '''
def parse(text): return Page([], [], frozenset())
'''


# ---------------------------------------------------------------------------------------------
# variants: a copy of the scripts directory whose doc_fences.py is the real one, a mutated one, or a shim
# ---------------------------------------------------------------------------------------------
def make_variant(td: pathlib.Path, name: str, reader_src: str | None = None) -> pathlib.Path:
    d = td / name
    d.mkdir()
    for f in HERE.glob('*.py'):
        if f.name.endswith('-fixture.py'):
            continue
        shutil.copy(f, d / f.name)
    shutil.copy(VERIFY, d / 'verify-docs.sh')       # the inline readers and the census are extracted from it
    if reader_src is not None:
        (d / 'doc_fences.py').write_text(reader_src)
    return d


def load_reader(scripts: pathlib.Path):
    name = 'df_' + str(abs(hash(str(scripts))))
    spec = importlib.util.spec_from_file_location(name, scripts / 'doc_fences.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run(cmd, cwd=None, timeout=300):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH', None)
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd, env=env, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def write_pages(root: pathlib.Path, pages: dict) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (root / name).write_text(text)
    return root


# ---------------------------------------------------------------------------------------------
# case recording
# ---------------------------------------------------------------------------------------------
class Cases:
    def __init__(self):
        self.out: dict[str, list[str]] = {}
        self.crashed: list[str] = []

    def check(self, label, ok_or_problems):
        probs = ok_or_problems if isinstance(ok_or_problems, list) else ([] if ok_or_problems else ['false'])
        self.out[label] = probs

    def text(self, label, rc, text, *, want_rc=None, must=(), must_not=()):
        probs = []
        if want_rc is not None and rc != want_rc:
            probs.append(f'exit {rc}, wanted {want_rc}')
        probs += [f'missing {m!r}' for m in must if m not in text]
        probs += [f'unexpected {m!r}' for m in must_not if m in text]
        if 'Traceback (most recent call last)' in text:
            self.crashed.append(label)
        self.out[label] = probs


# ---------------------------------------------------------------------------------------------
# layer 1: the reader
# ---------------------------------------------------------------------------------------------
# label -> (page text, expected fences, expected problems).
# a fence is (lang, line, end_line, kind, closed, quotes, indent, body)
READER_CASES = {
    'col0 fence': (
        "```java\nA\n```\n",
        [('java', 1, 3, 'col0', True, 0, 0, 'A\n')], set()),
    'col0 untagged fence': (
        "```\nA\n```\n",
        [('', 1, 3, 'col0', True, 0, 0, 'A\n')], set()),
    'indented fence in a list item, indent stripped from the body': (
        "1. Step\n   ```java\n   x\n     y\n   ```\n",
        [('java', 2, 5, 'indent', True, 0, 3, 'x\n  y\n')], set()),
    'blockquoted fence, one marker and its one space stripped': (
        "> ```java\n> x\n>   y\n> ```\n",
        [('java', 1, 4, 'quote', True, 1, 0, 'x\n  y\n')], set()),
    'nested `> >` fence': (
        "> > ```json\n> > {}\n> > ```\n",
        [('json', 1, 3, 'quote', True, 2, 0, '{}\n')], set()),
    'a blockquote holding an INDENTED fence is kind quote, indent still stripped': (
        ">    ```java\n>    x\n>    ```\n",
        [('java', 1, 3, 'quote', True, 1, 3, 'x\n')], set()),
    'bare `>` blank line inside a quoted fence (world.md form)': (
        "> ```java\n> a\n>\n> b\n> ```\n",
        [('java', 1, 5, 'quote', True, 1, 0, 'a\n\nb\n')], set()),
    'bare `>` blank line inside a NESTED quoted fence': (
        "> > ```json\n> > {}\n>\n> > ```\n",
        [('json', 1, 4, 'quote', True, 2, 0, '{}\n\n')], set()),
    'a fully empty line inside a quoted fence is a blank line': (
        "> ```java\n> a\n\n> b\n> ```\n",
        [('java', 1, 5, 'quote', True, 1, 0, 'a\n\nb\n')], set()),
    'tab-indented closer closes a 4-space opener (a tab is 4 columns)': (
        "    ```java\n    x\n\t```\n",
        [('java', 1, 3, 'indent', True, 0, 4, 'x\n')], set()),
    'closer with trailing spaces and an info string with extra words': (
        "```java title=x\nA\n```  \n",
        [('java', 1, 3, 'col0', True, 0, 0, 'A\n')], set()),
    'two fences with prose between keep their own line numbers': (
        "p\n```json\n1\n```\nq\n> ```java\n> 2\n> ```\n",
        [('json', 2, 4, 'col0', True, 0, 0, '1\n'), ('java', 6, 8, 'quote', True, 1, 0, '2\n')], set()),
    'inline triple-backtick mid-line is not a marker': (
        "see ```x``` here\n",
        [], set()),
    'UNCLOSED fence is returned, closed=False, and reported': (
        "```java\nx\n",
        [('java', 1, None, 'col0', False, 0, 0, 'x\n')], {(1, 'unclosed')}),
    '4-backtick fence is refused at both markers': (
        "````java\nx\n````\n",
        [], {(1, 'marker'), (3, 'marker')}),
    '~~~ fence is refused at both markers': (
        "~~~\nx\n~~~\n",
        [], {(1, 'marker'), (3, 'marker')}),
    'a fence inside a 4-backtick fence: the outer markers are refused, the inner is a fence': (
        "````md\n```java\nx\n```\n````\n",
        [('java', 2, 4, 'col0', True, 0, 0, 'x\n')], {(1, 'marker'), (5, 'marker')}),
    'closer with a different PREFIX SHAPE does not close (blockquote opener, col0 closer)': (
        "> ```java\n> x\n```\n",
        [('java', 1, None, 'quote', False, 1, 0, 'x\n```\n')], {(3, 'marker'), (1, 'unclosed')}),
    'closer with a different PREFIX SHAPE does not close (indented opener, col0 closer)': (
        "   ```java\n   x\n```\n",
        [('java', 1, None, 'indent', False, 0, 3, 'x\n```\n')], {(3, 'marker'), (1, 'unclosed')}),
    '```lang line inside an open fence is a marker problem and the fence goes on': (
        "```java\nx\n```json\ny\n```\n",
        [('java', 1, 5, 'col0', True, 0, 0, 'x\n```json\ny\n')], {(3, 'marker')}),
    'a non-blank body line missing the opener `>` ends the blockquote: quote-break': (
        "> ```java\n> a\nb\n> ```\n",
        [('java', 1, None, 'quote', False, 1, 0, 'a\n'), ('', 4, None, 'quote', False, 1, 0, '')],
        {(3, 'quote-break'), (4, 'unclosed')}),
    'a fence opener behind a LIST MARKER is refused (decision: not supported)': (
        "- ```java\n  x\n  ```\n",
        [('', 3, None, 'indent', False, 0, 2, '')], {(1, 'marker'), (3, 'unclosed')}),
    'inline code at a line start whose info string holds a backtick is refused': (
        "```foo``` bar\n",
        [], {(1, 'marker')}),
}

# fence_lines: the lines a fence occupies, opener through closer (EOF when unclosed). The heading
# readers trust it: a line in this set is never a heading.
FENCE_LINES_CASES = {
    'col0 fence occupies opener through closer and nothing else': ("p\n```java\nA\n```\nq\n", {2, 3, 4}),
    'blockquoted fence occupies its quoted lines': ("> ```java\n> x\n> ```\n", {1, 2, 3}),
    'indented fence occupies its lines': ("1. s\n   ```java\n   x\n   ```\n", {2, 3, 4}),
    'two fences leave the prose between them unoccupied': ("```a\n1\n```\np\n```b\n2\n```\n", {1, 2, 3, 5, 6, 7}),
    'an UNCLOSED fence occupies everything to EOF': ("p\n```java\nx\ny\n", {2, 3, 4}),
    'a quote-break ends the first fence at the line before it': ("> ```java\n> a\nb\n> ```\n", {1, 2, 4}),
}

# fenced_text() and the offsets: the raw text of each fence, opener line through closer line
SLICE_PAGE = "p\n```json\n1\n```\nq\n> ```java\n> 2\n> ```\nr\n"
SLICE_WANT = ["```json\n1\n```", "> ```java\n> 2\n> ```"]


def render(f):
    return (f.lang, f.line, f.end_line, f.kind, f.closed, f.quotes, f.indent, f.body)


def reader_group(c: Cases, scripts: pathlib.Path):
    mod = load_reader(scripts)
    for label, (text, want_f, want_p) in READER_CASES.items():
        try:
            page = mod.parse(text)
            got_f = [render(f) for f in page.fences]
            got_p = {(p.line, p.kind) for p in page.problems}
            probs = []
            if got_f != want_f:
                probs.append(f'fences {got_f!r} != {want_f!r}')
            if got_p != want_p:
                probs.append(f'problems {sorted(got_p)!r} != {sorted(want_p)!r}')
            c.check('reader: ' + label, probs)
        except Exception as e:                          # noqa: BLE001 - a crash is a failure
            c.check('reader: ' + label, [f'raised {type(e).__name__}: {e}'])
    for label, (text, want) in FENCE_LINES_CASES.items():
        try:
            got = set(mod.parse(text).fence_lines)
            c.check('reader: fence_lines, ' + label, [] if got == want else [f'{sorted(got)} != {sorted(want)}'])
        except Exception as e:                          # noqa: BLE001
            c.check('reader: fence_lines, ' + label, [f'raised {type(e).__name__}: {e}'])
    try:
        got = mod.fenced_text(SLICE_PAGE)
        c.check('reader: fenced_text() slices opener line through closer line, prefix intact',
                [] if got == SLICE_WANT else [f'{got!r} != {SLICE_WANT!r}'])
    except Exception as e:                              # noqa: BLE001
        c.check('reader: fenced_text() slices opener line through closer line, prefix intact',
                [f'raised {type(e).__name__}: {e}'])


# ---------------------------------------------------------------------------------------------
# layer 2: the census
# ---------------------------------------------------------------------------------------------
HEALTHY_PAGE = ("# H\n\n```java\nA\n```\n\n1. step\n\n   ```json\n   {}\n   ```\n\n"
                "> ```java\n> B\n> ```\n\n```\nplain\n```\n")
CENSUS_LINE = ("  INFO  fence census: 4 fence(s) in 1 page(s): java 2, json 1, untagged 1; "
               "1 blockquoted, 1 indented, 0 orphan")
# label -> (pages, expected rc, substrings the output must hold)
CENSUS_CASES = {
    'healthy pages: exact census line, rc 0': ({'h.md': HEALTHY_PAGE}, 0, [CENSUS_LINE]),
    'orphan: a 4-backtick fence FAILs naming both markers': (
        {'bad.md': "p\n````java\nx\n````\n"}, 1,
        ['bad.md:2:', 'bad.md:4:', 'only three-backtick fences are supported, found 4 backticks']),
    'orphan: a ~~~ fence FAILs naming both markers': (
        {'bad.md': "p\n~~~\nx\n~~~\n"}, 1,
        ['bad.md:2:', 'bad.md:4:', 'only three-backtick fences are supported, found a ~~~ marker']),
    'orphan: a closer whose prefix shape differs FAILs naming it': (
        {'bad.md': "> ```java\n> x\n```\n"}, 1, ['bad.md:3:', 'does not match its opener']),
    'orphan: a ```lang line inside an open fence FAILs naming it': (
        {'bad.md': "```java\nx\n```json\ny\n```\n"}, 1, ['bad.md:3:', 'a fence marker inside the fence']),
    'orphan: a non-blank body line missing the opener `>` FAILs naming it': (
        {'bad.md': "> ```java\n> a\nb\n> ```\n"}, 1, ['bad.md:3:', 'quote-break']),
    'orphan: an UNCLOSED fence FAILs naming its opener': (
        {'bad.md': "p\n```java\nx\n"}, 1, ['bad.md:2:', 'has no closer before EOF']),
    'orphan: a fence opener behind a list marker FAILs naming it': (
        {'bad.md': "- ```java\n  x\n  ```\n"}, 1, ['bad.md:1:', 'list marker']),
    'orphan: a 4-backtick fence around a ``` fence FAILs on the outer markers only': (
        {'bad.md': "````md\n```java\nx\n```\n````\n"}, 1, ['bad.md:1:', 'bad.md:5:']),
    'tag allowlist: ```Java FAILs naming file:line and the tag': (
        {'bad.md': HEALTHY_PAGE + "\n```Java\nWorld.noSuchMemberXyzzy();\n```\n"}, 1,
        ["bad.md:21:", "fence tag 'Java' is not in the allowed set"]),
    'tag allowlist: ```JSON FAILs naming file:line and the tag': (
        {'bad.md': HEALTHY_PAGE + "\n```JSON\n{}\n```\n"}, 1,
        ["bad.md:21:", "fence tag 'JSON' is not in the allowed set"]),
    'tag allowlist: ```jsonc FAILs naming file:line and the tag': (
        {'bad.md': HEALTHY_PAGE + "\n```jsonc\n{}\n```\n"}, 1,
        ["bad.md:21:", "fence tag 'jsonc' is not in the allowed set"]),
    'tag allowlist: an unknown LOWERCASE tag (```text) FAILs, a new language is an explicit edit': (
        {'bad.md': HEALTHY_PAGE + "\n```text\nx\n```\n"}, 1,
        ["bad.md:21:", "fence tag 'text' is not in the allowed set"]),
    'tag allowlist: the whole info string is compared (```java title=x FAILs)': (
        {'bad.md': HEALTHY_PAGE + "\n```java title=x\nx\n```\n"}, 1,
        ["bad.md:21:", "fence tag 'java title=x' is not in the allowed set"]),
    'tag allowlist: java, json, bash, batch and untagged all pass': (
        {'ok.md': HEALTHY_PAGE + "\n```bash\nls\n```\n\n```batch\ndir\n```\n"}, 0,
        ['6 fence(s) in 1 page(s): java 2, bash 1, batch 1, json 1, untagged 1; 1 blockquoted, 1 indented, 0 orphan']),
    'a census that visited ZERO pages FAILs': ({}, 1, ['visited 0 page(s)']),
    'a census that visited pages but ZERO fences FAILs': (
        {'p.md': "# no fences here\n"}, 1, ['visited 1 page(s) and 0 fence(s)']),
}


def census_group(c: Cases, scripts: pathlib.Path, td: pathlib.Path, tag: str):
    mod = load_reader(scripts)
    for i, (label, (pages, want_rc, must)) in enumerate(CENSUS_CASES.items()):
        d = write_pages(td / f'census-{tag}-{i}', pages)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = mod.main(['--census', '--docs', str(d)])
            c.text('census: ' + label, rc, buf.getvalue(), want_rc=want_rc, must=must)
        except Exception as e:                          # noqa: BLE001
            c.crashed.append('census: ' + label)
            c.check('census: ' + label, [f'raised {type(e).__name__}: {e}'])


def census_cli_group(c: Cases, scripts: pathlib.Path, td: pathlib.Path):
    """The process boundary: exit status and the line verify-docs.sh greps are what ships."""
    d = write_pages(td / 'census-cli', {'h.md': HEALTHY_PAGE})
    rc, t = run([sys.executable, scripts / 'doc_fences.py', '--census', '--docs', d])
    c.text('census CLI: exits 0 and prints the census line', rc, t, want_rc=0, must=[CENSUS_LINE])
    rc, t = run([sys.executable, scripts / 'doc_fences.py', '--counts', '--docs', d])
    c.text('census CLI: --counts prints the figures the gates are compared with', rc, t, want_rc=0,
           must=['JAVA 2 JSON 1 TOTAL 4 PAGES 1 ORPHANS 0'])
    bad = write_pages(td / 'census-cli-bad', {'bad.md': "````x\n"})
    rc, t = run([sys.executable, scripts / 'doc_fences.py', '--census', '--docs', bad])
    c.text('census CLI: an orphan exits 1', rc, t, want_rc=1, must=['FAIL  bad.md:1:'])


# ---------------------------------------------------------------------------------------------
# layer 3: the gates, on a planted tree and its healthy twin
# ---------------------------------------------------------------------------------------------
def symbols_page(planted: bool) -> str:
    q = 'noSuchQuoted' if planted else 'realMember'
    i = 'noSuchIndented' if planted else 'realMember'
    qv = '"text"' if planted else '1'
    iv = '"text"' if planted else '2'
    return textwrap.dedent(f'''\
        # Planted

        A dead member in a BLOCKQUOTED fence and in an INDENTED one, and two package-led
        units (one in each) that must compile.

        > ```java
        > Widget.{q}();
        > ```

        > ```java
        > package fx.q;
        > public class QuotedUnit {{ int v = {qv}; }}
        > ```

        1. A step:

           ```java
           Widget.{i}();
           ```

        2. Another step:

           ```java
           package fx.i;
           public class IndentedUnit {{ int v = {iv}; }}
           ```
        ''')


def typevalues_page(planted: bool) -> str:
    qt = 'Zzz_Quoted_NotReal' if planted else 'Alpha'
    it = 'Zzz_Indented_NotReal' if planted else 'Beta'
    return textwrap.dedent(f'''\
        # Planted types

        > ```json
        > {{ "Type": "{qt}" }}
        > ```

        1. A step:

           ```json
           {{ "Type": "{it}" }}
           ```

        The next value is registered only in a BLOCKQUOTED java fence on this page:

        > ```java
        > Foo.CODEC.register("Quoted_Registered", QFoo.class, QFoo.CODEC);
        > ```

        ```json
        {{ "Type": "Quoted_Registered" }}
        ```
        ''')


def defaults_page(planted: bool) -> str:
    r = '9.5' if planted else '1.5'
    n = '9' if planted else '0'
    return textwrap.dedent(f'''\
        # Planted defaults

        ### Widget

        **Package:** `defpkg`

        #### Quoted Fence Section

        Its only fingerprint is a blockquoted fence, so it binds only if that fence is read. The
        table header is `JSON key`, which check-defaults accepts as a key column (trailing-word
        rule) and the binder does NOT take as a fingerprint (it wants a bare Key/Property/Field/
        Name), so the table cannot bind the section in the fence's place.

        > ```json
        > {{
        >   "Radius": 1
        > }}
        > ```

        | JSON key | Type | Default |
        |----------|------|---------|
        | `Radius` | double | `{r}` |

        #### Indented Fence Section

        1. Example:

           ```json
             {{
             "Count": 1
           }}
           ```

        | JSON key | Type | Default |
        |----------|------|---------|
        | `Count` | int | `{n}` |
        ''')


def gate_groups(c: Cases, scripts: pathlib.Path, td: pathlib.Path, tag: str, jar: pathlib.Path, groups):
    py = sys.executable
    if 'symbols' in groups:
        for planted in (True, False):
            d = write_pages(td / f'sym-{tag}-{planted}', {'planted.md': symbols_page(planted)})
            rc, t = run([py, scripts / 'check-symbols.py', jar, '--docs', d])
            if planted:
                c.text('check-symbols: dead members in a BLOCKQUOTED and an INDENTED java fence are found',
                       rc, t, want_rc=0,
                       must=['FINDINGS 2', 'Widget.noSuchQuoted', 'Widget.noSuchIndented', 'JAVA_FENCES 4'])
            else:
                c.text('check-symbols healthy twin: the same fences hold, 1 member checked, 4 java fences read',
                       rc, t, want_rc=0, must=['CHECKED_MEMBERS 1', 'FINDINGS 0', 'JAVA_FENCES 4'])
    if 'snippets' in groups:
        for planted in (True, False):
            d = write_pages(td / f'snip-{tag}-{planted}', {'planted.md': symbols_page(planted)})
            rc, t = run([py, scripts / 'check-snippets.py', jar, '--docs', d])
            if planted:
                c.text('check-snippets: package-led units in a BLOCKQUOTED and an INDENTED fence that fail javac FAIL',
                       rc, t, want_rc=1, must=['FAIL', 'QuotedUnit', 'IndentedUnit', 'BLOCKS 4'])
            else:
                c.text('check-snippets healthy twin: both units compile, BLOCKS counts the quoted and indented fences',
                       rc, t, want_rc=0, must=['CHECKED 2', 'BLOCKS 4', 'DOCS 1 1'], must_not=['FAIL'])
    if 'typevalues' in groups:
        empty = td / 'empty-skiplist.txt'
        empty.write_text('# empty\n')
        for planted in (True, False):
            d = write_pages(td / f'tv-{tag}-{planted}', {'planted.md': typevalues_page(planted)})
            rc, t = run([py, scripts / 'check-type-values.py', '--docs', d, '--src', TV_CORPUS / 'src',
                         '--assets', TV_CORPUS / 'assets', '--skiplist', empty])
            if planted:
                c.text('check-type-values: unregistered Types in a BLOCKQUOTED and an INDENTED json fence FAIL',
                       rc, t, want_rc=1, must=['Zzz_Quoted_NotReal', 'Zzz_Indented_NotReal', 'unresolved 2'])
            else:
                c.text('check-type-values healthy twin: exact fence denominator and tally',
                       rc, t, want_rc=0,
                       must=['3 json fence(s) of 4 in 1 page(s); 3 "Type" occurrence(s), 3 distinct value(s)',
                             "registry 2, shipped assets 0, page's own java fence 1"],
                       must_not=['FAIL'])
        # the quoted java fence supplies the page-local name; with it unread the healthy page FAILs
        c.out['check-type-values: a Type registered only in a BLOCKQUOTED java fence resolves page-locally'] = (
            [] if c.out['check-type-values healthy twin: exact fence denominator and tally'] == [] else
            ['the healthy twin is red'])
    if 'binder' in groups or 'defaults' in groups:
        for planted in (True, False):
            d = write_pages(td / f'def-{tag}-{planted}', {'planted.md': defaults_page(planted)})
            if 'binder' in groups and planted:
                probe = ("import sys, pathlib; sys.path.insert(0, sys.argv[1]); import section_binder as sb; "
                         "r = sb.bind_all(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])); "
                         "print('ACCEPTED', sorted(i.section for i in r.inherited_accepted)); "
                         "print('REJECTED', len(r.inherited_rejected))")
                rc, t = run([py, '-c', probe, scripts, d, DEF_CORPUS / 'src'])
                c.text('section_binder: root keys of a BLOCKQUOTED and of an INDENTED json fence bind their sections',
                       rc, t, want_rc=0,
                       must=["ACCEPTED ['Indented Fence Section', 'Quoted Fence Section']", 'REJECTED 0'])
            if 'defaults' in groups:
                rc, t = run([py, scripts / 'check-defaults.py', '--docs', d, '--src', DEF_CORPUS / 'src'])
                if planted:
                    c.text('check-defaults: a wrong Default in a section bound ONLY by a quoted / indented fence is found',
                           rc, t, want_rc=1,
                           must=['Quoted Fence Section: `Radius` is documented as `9.5`',
                                 'Indented Fence Section: `Count` is documented as `9`'])
                else:
                    c.text('check-defaults healthy twin: both sections are bound and both Defaults agree',
                           rc, t, want_rc=0,
                           must=['2 Default-column key table(s) on 1 page(s); 2 in a bound section (0 direct, 2 inherited-accepted)',
                                 'PASS'], must_not=['FAIL'])


# ---------------------------------------------------------------------------------------------
# the verify-docs.sh inline readers, extracted from the script that ships
# ---------------------------------------------------------------------------------------------
def extract_block(scripts: pathlib.Path, title: str, delim: str = 'PY') -> str:
    t = (scripts / 'verify-docs.sh').read_text()
    i = t.index(title)
    b = t[i:]
    s = b.index(f"<<'{delim}'\n") + len(delim) + 4
    e = b.index(f"\n{delim}\n", s)
    return b[s:e] + '\n'


def extract_harvest(scripts: pathlib.Path) -> str:
    t = (scripts / 'verify-docs.sh').read_text()
    a = t.index('dfq = set(); code_names = set(); alltext = []; codetext = []')
    end = 'alltext = "\\n".join(alltext); codetext = "\\n".join(codetext)'
    b = t.index(end, a) + len(end)
    return t[a:b] + '\n'


def inline_root(td: pathlib.Path, name: str, scripts: pathlib.Path, pages: dict, extra=None) -> pathlib.Path:
    root = td / name
    (root / 'maintenance').mkdir(parents=True)
    os.symlink(scripts, root / 'maintenance' / 'scripts')
    write_pages(root / 'docs', pages)
    for rel, text in (extra or {}).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def run_script(root: pathlib.Path, source: str, args=()):
    script = root / 'inline.py'
    script.write_text(source)
    return run([sys.executable, '-I' if False else str(script), *args], cwd=root)


JSON_PAGE = textwrap.dedent('''\
    # J

    > ```json
    > { "A": 1 }
    > ```

    ```json
    { "B": 2 }
    ```
    ''')

# a JSON-tagged page citing two classes on Package lines; the Java surface it carries is in a
# BLOCKQUOTED (planted) fence and, on the second page, an INDENTED one. Healthy: no Java at all.
def doctype_page(kind: str) -> str:
    java = {'quote': "> ```java\n> void setFoo(boolean b)\n> ```\n",
            'indent': "1. A step:\n\n   ```java\n   void setFoo(boolean b)\n   ```\n",
            'upper': "```Java\nvoid setFoo(boolean b)\n```\n",
            'none': ""}[kind]
    return ("**Doc type:** JSON asset format\n\n"
            "### Alpha Interaction\n\n"
            "**Package:** `com.hypixel.hytale.server.core.foo.AlphaInteraction`\n\n"
            "| Property | Type |\n|---|---|\n| `X` | int |\n\n"
            "### Beta Interaction\n\n"
            "**Package:** `com.hypixel.hytale.server.core.foo.BetaInteraction`\n\n"
            "```json\n{ \"Type\": \"Beta\" }\n```\n\n" + java)


def fields_pages(planted: bool):
    q = 'PlantedQuotedKey' if planted else 'KnownKey'
    i = 'PlantedIndentedKey' if planted else 'KnownKey'
    page = ("**Assets:** `Server/Thing`\n\n> ```json\n> { \"%s\": 1 }\n> ```\n\n"
            "1. A step:\n\n   ```json\n   { \"%s\": 2 }\n   ```\n" % (q, i))
    return {'planted.md': page}, {'assets/Server/Thing/x.json': '{ "KnownKey": 1 }\n',
                                  'jarsrc/Empty.java': '// nothing\n'}


def inline_groups(c: Cases, scripts: pathlib.Path, td: pathlib.Path, tag: str, groups):
    if 'jsonparse' in groups:
        root = inline_root(td, f'jp-{tag}', scripts, {'j.md': JSON_PAGE})
        rc, t = run_script(root, extract_block(scripts, 'section "[ADVISORY] JSON code blocks parse"'))
        c.text('JSON-parse check: a valid json fence inside a BLOCKQUOTE parses (its `> ` is removed), both fences counted',
               rc, t, want_rc=0, must=['FRAG 0', 'JSONFENCES 2'])
    if 'doctype' in groups:
        for kind in ('quote', 'indent', 'upper', 'none'):
            root = inline_root(td, f'dt-{tag}-{kind}', scripts, {'p.md': doctype_page(kind)})
            rc, t = run_script(root, extract_block(scripts, 'section "[ADVISORY] Doc-type tags are present'))
            if kind == 'none':
                c.text('doc-type healthy twin: Package-line citations on a page with no Java surface are provenance',
                       rc, t, want_rc=0, must=['FELL p.md', 'FENCESREAD 1'], must_not=['MISMATCH'])
            else:
                label = {'quote': 'a java fence inside a BLOCKQUOTE', 'indent': 'a java fence INDENTED in a list item',
                         'upper': 'a ```Java fence (the case fold is kept on purpose, maintenance/fixtures/doctype/fixture-i.md)'}[kind]
                c.text(f'doc-type: {label} disqualifies the provenance exclusion (D), so the page is a MISMATCH',
                       rc, t, want_rc=0, must=['MISMATCH p.md', 'FENCESREAD 2'], must_not=['FELL p.md'])
    if 'codenames' in groups:
        page = "# C\n\n> ```java\n> PlantedQuotedName.doIt();\n> ```\n\n```java\nPlainName.go();\n```\n"
        root = inline_root(td, f'cn-{tag}', scripts, {'c.md': page})
        drv = ("import re, glob, sys\nsys.path.insert(0, 'maintenance/scripts')\nimport doc_fences\n"
               + extract_harvest(scripts)
               + "print('HARVESTED', fences_harvested)\nprint('NAMES', ' '.join(sorted(code_names)))\n")
        rc, t = run_script(root, drv)
        c.text('code names: the harvest reads the BLOCKQUOTED fence too, and counts both fences',
               rc, t, want_rc=0, must=['HARVESTED 2', 'PlantedQuotedName', 'PlainName'])
    if 'codenames' in groups:
        # the coverage advisory's own comparison with the census (it is a heredoc that needs the jar's
        # classes, so only the comparison is run, on a stand-in for the harvested count)
        t = (scripts / 'verify-docs.sh').read_text()
        a = t.index('_census_total = doc_fences.census(')
        cmp_src = t[a:t.index('print(f"  {len(cand)} public top-level candidate classes', a)]
        root = inline_root(td, f'cn-cmp-{tag}', scripts, {'h.md': HEALTHY_PAGE})
        for n, want_rc, must in ((4, 0, ['(the census counted 4)']),
                                 (3, 3, ['FAIL  the coverage advisory harvested a different number'])):
            drv = ("import sys, pathlib\nsys.path.insert(0, 'maintenance/scripts')\nimport doc_fences\n"
                   f"fences_harvested = {n}\n" + cmp_src)
            rc, out = run_script(root, drv)
            c.text(f'coverage advisory: a harvest of {n} fence(s) against a census of 4 '
                   + ('passes' if want_rc == 0 else 'exits 3'), rc, out, want_rc=want_rc, must=must)
    if 'fields' in groups:
        for planted in (True, False):
            pages, extra = fields_pages(planted)
            root = inline_root(td, f'fl-{tag}-{planted}', scripts, pages, extra)
            rc, t = run_script(root, extract_block(scripts, 'section "[ADVISORY] Documented JSON fields', 'FIELDSPY'),
                               [str(root / 'assets'), str(root / 'jarsrc')])
            if planted:
                c.text('fields check: a fabricated key in a BLOCKQUOTED and in an INDENTED json fence is suspect',
                       rc, t, want_rc=0, must=['SUSPECT planted.md', 'PlantedQuotedKey', 'PlantedIndentedKey',
                                               'FLAGGED 2', 'JSONFENCES 2'])
            else:
                c.text('fields check healthy twin: known keys pass, both fences counted',
                       rc, t, want_rc=0, must=['CHECKED 1', 'FLAGGED 0', 'JSONFENCES 2'])


# ---------------------------------------------------------------------------------------------
# the heading readers: a heading-shaped line inside a code fence is not a heading
# ---------------------------------------------------------------------------------------------
# Two sections each cite TWO classes and carry a bash fence BEFORE their Package line; a third
# is clean JSON. Read correctly, the bash fence is in Alpha's section, so rule E refuses to treat
# Alpha's citation as provenance and the page is a MISMATCH. Fence-blind, the fence's `# comment`
# ends Alpha's section at the comment, the Package line lands in a section whose only fence is the
# json one after it, and the citation is wrongly excluded: the page FELLs below the threshold and
# the MISMATCH is lost.
def doctype_heading_page(comment: bool, quoted: bool = False) -> str:
    inside = '# comment\nrun\n' if comment else 'run\n'
    fence = ('> ```bash\n' + ''.join('> ' + ln + '\n' for ln in inside.split('\n')[:-1]) + '> ```\n') if quoted \
        else '```bash\n' + inside + '```\n'
    return ("**Doc type:** JSON asset format\n\n"
            "### Alpha Interaction\n\n" + fence + "\n"
            "**Package:** `com.hypixel.hytale.server.core.foo.AlphaInteraction` "
            "and `com.hypixel.hytale.server.core.foo.AlphaTwoInteraction`\n\n"
            "| Property | Type |\n|---|---|\n| `X` | int |\n\n"
            "### Beta Interaction\n\n"
            "**Package:** `com.hypixel.hytale.server.core.foo.BetaInteraction`\n\n"
            "```json\n{ \"Type\": \"Beta\" }\n```\n")


GOTCHA_PAGES = {
    # a `## ` line inside a fence must not END the Gotchas section: the bullet after the fence is a gotcha
    'gotchas.md': "## Gotchas\n\n```text\n## Notes\n```\n\n- **`FirstGotcha`** -> cause\n",
    # ... and must not OPEN one: the bullet after the fence belongs to Usage
    'usage.md': "## Usage\n\n```text\n## Gotchas\n```\n\n- **`NotAGotcha`** -> not under a Gotchas heading\n",
}
# A section's `## Gotchas` heading written inside a BLOCKQUOTED fence never matched `^##` (PIN).
GOTCHA_QUOTED = {'quoted.md': "## Usage\n\n> ```text\n> ## Gotchas\n> ```\n\n- **`StillNotAGotcha`** -> no\n"}

BINDER_HEADING_PAGE = ("### Widget\n\n**Package:** `defpkg`\n\n#### Props\n\n"
                       "```text\n## Phantom Level Two\n```\n\n| Key | Type |\n|-----|------|\n| `Radius` | double |\n")


def heading_groups(c: Cases, scripts: pathlib.Path, td: pathlib.Path, tag: str):
    py = sys.executable
    # --- doc-type _sections ------------------------------------------------------------------
    for kind, page in (('col0', doctype_heading_page(True)), ('quote', doctype_heading_page(True, True)),
                       ('twin', doctype_heading_page(False))):
        root = inline_root(td, f'hd-dt-{tag}-{kind}', scripts, {'p.md': page})
        rc, t = run_script(root, extract_block(scripts, 'section "[ADVISORY] Doc-type tags are present'))
        if kind == 'twin':
            c.text('doc-type headings, healthy twin: a bash fence with no comment line still blocks the exclusion (MISMATCH)',
                   rc, t, want_rc=0, must=['MISMATCH p.md'], must_not=['FELL p.md'])
        elif kind == 'col0':
            c.text('doc-type headings, a `# comment` in a bash fence does not end the section it sits in (MISMATCH kept)',
                   rc, t, want_rc=0, must=['MISMATCH p.md'], must_not=['FELL p.md'])
        else:
            c.text('doc-type headings, PIN a `# comment` in a BLOCKQUOTED bash fence is no heading either',
                   rc, t, want_rc=0, must=['MISMATCH p.md'], must_not=['FELL p.md'])
    # --- the gotcha scan ----------------------------------------------------------------------
    pool = td / f'empty-pool-{tag}'
    pool.write_text('')
    for kind, pages, must, must_not in (
            ('col0', GOTCHA_PAGES, ['CHECKED 1', 'MISS gotchas.md:7: FirstGotcha'], ['usage.md', 'NotAGotcha']),
            ('quote', GOTCHA_QUOTED, ['CHECKED 0'], ['quoted.md', 'StillNotAGotcha'])):
        root = inline_root(td, f'hd-gt-{tag}-{kind}', scripts, pages)
        rc, t = run_script(root, extract_block(scripts, 'section "[ADVISORY] Gotcha error strings trace to the jar"'),
                           [str(pool)])
        if kind == 'col0':
            c.text('gotcha scan headings, a `## ` line in a fence neither ends nor opens a Gotchas section',
                   rc, t, want_rc=0, must=must, must_not=must_not)
        else:
            c.text('gotcha scan headings, PIN a `## Gotchas` line in a BLOCKQUOTED fence opens nothing',
                   rc, t, want_rc=0, must=must, must_not=must_not)
    # --- section_binder ------------------------------------------------------------------------
    d = write_pages(td / f'hd-bd-{tag}', {'planted.md': BINDER_HEADING_PAGE})
    probe = ("import sys, pathlib; sys.path.insert(0, sys.argv[1]); import section_binder as sb; "
             "r = sb.bind_all(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])); "
             "print('SEEN', r.seen); print('ACCEPTED', sorted(i.section for i in r.inherited_accepted)); "
             "print('UNBOUND', sorted(u.section for u in r.unbound))")
    rc, t = run([py, '-c', probe, scripts, d, DEF_CORPUS / 'src'])
    c.text('section_binder headings, a `## ` line in a fence adds no section and the table still binds its own',
           rc, t, want_rc=0, must=['SEEN 2', "ACCEPTED ['Props']", 'UNBOUND []'])


# ---------------------------------------------------------------------------------------------
# the shell half: the census section and fence_agree(), extracted from verify-docs.sh
# ---------------------------------------------------------------------------------------------
PRELUDE = textwrap.dedent('''\
    HARD_FAILS=0
    section() { echo "== $1 =="; }
    pass() { echo "  PASS  $1"; }
    fail() { echo "  FAIL  $1"; HARD_FAILS=$((HARD_FAILS+1)); }
    warn() { echo "  WARN  $1"; }
    info() { echo "  INFO  $1"; }
    ''')
# every gate the census is compared with, by the label verify-docs.sh gives fence_agree
AGREE_LABELS = ('check-symbols.py (java fences)', 'check-snippets.py (java fences)',
                'check-type-values.py (json fences)', 'check-type-values.py (all fences)',
                'check-asset-ids.py (json fences)', 'JSON-parse check (json fences)',
                'Doc-type check (all fences)')
TV_LINE = '  INFO  3 json fence(s) of 4 in 1 page(s); 3 "Type" occurrence(s), 3 distinct value(s)'
AI_LINE = ('  INFO  docs scan: 76 page(s); 727 ```json fence(s) (640 strict-parse, 87 unparseable and read '
           'tolerantly); 229 untagged fence(s)')


def agree_def(vtext: str) -> str:
    a = vtext.index('fence_agree() {')
    b = vtext.index('\n}\n', a) + 3
    return vtext[a:b] + '\n'


def census_section(vtext: str) -> str:
    a = vtext.index('section "[HARD] Fence census')
    b = vtext.index('\n# =====', a)
    return vtext[a:b] + '\n'


def bash(root: pathlib.Path, source: str):
    return run(['bash', '-c', source], cwd=root)


def verify_group(c: Cases, scripts: pathlib.Path, td: pathlib.Path, tag: str):
    vtext = (scripts / 'verify-docs.sh').read_text()
    sect = census_section(vtext)
    # --- the census section, run for real on synthetic pages -----------------------------
    for name, pages, must, must_not in (
            ('healthy pages PASS and print the census line and the counts', {'h.md': HEALTHY_PAGE},
             ['PASS  every fence marker is accounted for', CENSUS_LINE.strip(), 'FC=2/1/4', 'HARD_FAILS=0'], ['FAIL  ']),
            ('an orphan marker is a HARD FAIL naming file:line', {'h.md': HEALTHY_PAGE, 'bad.md': "p\n````x\n"},
             ['FAIL  fence census:', 'bad.md:2:', 'HARD_FAILS=1'], ['PASS  every fence marker']),
            ('a fence tagged ```Java is a HARD FAIL naming file:line', {'h.md': HEALTHY_PAGE + "\n```Java\nx\n```\n"},
             ['FAIL  fence census:', "h.md:21:", "fence tag 'Java'", 'HARD_FAILS=1'], ['PASS  every fence marker'])):
        root = inline_root(td, f'vs-{tag}-{abs(hash(name))}', scripts, pages)
        rc, t = bash(root, PRELUDE + sect + 'echo "FC=$FC_JAVA/$FC_JSON/$FC_TOTAL"; echo "HARD_FAILS=$HARD_FAILS"\n')
        c.text('verify-docs census section: ' + name, rc, t, want_rc=0, must=must, must_not=must_not)
    # --- the counts guard: a census that exits 0 but prints no counts must not leave the comparisons empty ---
    stub = td / f'stub-scripts-{tag}'
    stub.mkdir()
    (stub / 'doc_fences.py').write_text(
        "import sys\nif '--census' in sys.argv: print('  INFO  fence census: stub')\n")
    root = inline_root(td, f'vs-stub-{tag}', stub, {'h.md': HEALTHY_PAGE})
    rc, t = bash(root, PRELUDE + sect + 'echo "HARD_FAILS=$HARD_FAILS"\n')
    c.text('verify-docs census section: a census that prints no counts is a HARD FAIL', rc, t, want_rc=0,
           must=['FAIL  the fence census printed no counts', 'HARD_FAILS=1'])
    # --- fence_agree(): equal is silent; unequal, over and under, and an empty figure FAIL ------
    agree = agree_def(vtext)
    root = inline_root(td, f'vs-agree-{tag}', scripts, {'h.md': HEALTHY_PAGE})
    for name, call, must, must_not in (
            ('equal counts are silent', 'fence_agree g 4 4', ['HARD_FAILS=0'], ['FAIL  ']),
            ('a gate that read FEWER fences than the census FAILs, naming both numbers', 'fence_agree g 3 4',
             ['FAIL  g: read 3 fence(s), the census counted 4', 'HARD_FAILS=1'], []),
            ('a gate that read MORE fences than the census FAILs, naming both numbers', 'fence_agree g 5 4',
             ['FAIL  g: read 5 fence(s), the census counted 4', 'HARD_FAILS=1'], []),
            ('a gate that printed no fence count FAILs, it is never skipped', 'fence_agree g "" 4',
             ['FAIL  g: printed no fence count', 'HARD_FAILS=1'], []),
            ('control: 5 against 6 FAILs naming both numbers', 'fence_agree g 5 6',
             ['FAIL  g: read 5 fence(s), the census counted 6', 'HARD_FAILS=1'], []),
            ('a newline-joined figure (two numbers on two lines) is a malformed-figure FAIL, not a silent pass',
             "fence_agree g $'5\\n5' 5", ['FAIL  g: malformed fence figure(s)', 'HARD_FAILS=1'], []),
            ('a figure with a suffix (5x) is a malformed-figure FAIL', 'fence_agree g 5x 5',
             ['FAIL  g: malformed fence figure(s)', 'HARD_FAILS=1'], []),
            ('a whitespace-only figure is a malformed-figure FAIL', 'fence_agree g " " 5',
             ['FAIL  g: malformed fence figure(s)', 'HARD_FAILS=1'], []),
            ('a malformed CENSUS figure is a malformed-figure FAIL too', 'fence_agree g 5 ""',
             ['FAIL  g: malformed fence figure(s)', 'HARD_FAILS=1'], []),
            ('a malformed figure produces no shell error text', "fence_agree g 5x 5",
             ['FAIL  g: malformed fence figure(s)'], ['integer expression expected'])):
        rc, t = bash(root, PRELUDE + agree + call + '\necho "HARD_FAILS=$HARD_FAILS"\n')
        c.text('verify-docs fence_agree: ' + name, rc, t, want_rc=0, must=must, must_not=must_not)
    # --- gate 3's and the type-values gate's printed lines, parsed by the lines that ship ----------
    lines = {k: [ln for ln in vtext.split('\n') if ln.lstrip().startswith(f'fence_agree "{k}')]
             for k in ('check-type-values.py (json fences)', 'check-type-values.py (all fences)',
                       'check-asset-ids.py (json fences)')}
    missing = [k for k, v in lines.items() if len(v) != 1]
    c.check('verify-docs: the type-values (x2) and asset-ids comparisons each exist exactly once',
            [] if not missing else [f'not exactly one call for {missing}'])
    if not missing:
        def parse_case(name, key, out, fc_json, fc_total, must):
            src = (PRELUDE + agree + f'FC_JSON={fc_json}; FC_TOTAL={fc_total}\nOUT={_shq(out)}\n'
                   + lines[key][0] + '\necho "HARD_FAILS=$HARD_FAILS"\n')
            rc, t = bash(root, src)
            c.text('verify-docs: ' + name, rc, t, want_rc=0, must=must)
        parse_case('type-values: json fences agree with the census', 'check-type-values.py (json fences)', TV_LINE, 3, 4, ['HARD_FAILS=0'])
        parse_case('type-values: a json-fence mismatch FAILs naming both numbers', 'check-type-values.py (json fences)', TV_LINE, 4, 4,
                   ['FAIL  check-type-values.py (json fences): read 3 fence(s), the census counted 4'])
        parse_case('type-values: the all-fences figure is compared too', 'check-type-values.py (all fences)', TV_LINE, 3, 5,
                   ['FAIL  check-type-values.py (all fences): read 4 fence(s), the census counted 5'])
        parse_case('type-values: a missing INFO line is a FAIL, not a skip', 'check-type-values.py (json fences)', '  INFO  nothing', 3, 4,
                   ['FAIL  check-type-values.py (json fences): printed no fence count'])
        parse_case('asset-ids: the printed json-fence count agrees with the census', 'check-asset-ids.py (json fences)', AI_LINE, 727, 2057, ['HARD_FAILS=0'])
        parse_case('asset-ids: a mismatch FAILs naming both numbers', 'check-asset-ids.py (json fences)', AI_LINE, 731, 2057,
                   ['FAIL  check-asset-ids.py (json fences): read 727 fence(s), the census counted 731'])
        parse_case('asset-ids: a missing docs-scan line is a FAIL, not a skip', 'check-asset-ids.py (json fences)', '  INFO  asset sweep: 1', 727, 2057,
                   ['FAIL  check-asset-ids.py (json fences): printed no fence count'])
    # --- every gate is compared: a call that was deleted is a gate nobody compares ------------------
    absent = [lab for lab in AGREE_LABELS if f'fence_agree "{lab}"' not in vtext]
    c.check('verify-docs: every gate is compared with the census (7 comparisons)',
            [] if not absent else [f'no fence_agree call for: {absent}'])


def _shq(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


# ---------------------------------------------------------------------------------------------
# running everything
# ---------------------------------------------------------------------------------------------
ALL_GROUPS = ('reader', 'census', 'cli', 'symbols', 'snippets', 'typevalues', 'binder', 'defaults',
              'jsonparse', 'doctype', 'codenames', 'fields', 'verify', 'headings')


def all_cases(scripts: pathlib.Path, jar: pathlib.Path, groups=ALL_GROUPS):
    c = Cases()
    with tempfile.TemporaryDirectory() as t:
        td = pathlib.Path(t)
        tag = 'v'
        if 'reader' in groups:
            reader_group(c, scripts)
        if 'census' in groups:
            census_group(c, scripts, td, tag)
        if 'cli' in groups:
            census_cli_group(c, scripts, td)
        gate_groups(c, scripts, td, tag, jar, groups)
        inline_groups(c, scripts, td, tag, groups)
        if 'verify' in groups:
            verify_group(c, scripts, td, tag)
        if 'headings' in groups:
            heading_groups(c, scripts, td, tag)
    return c


# ---------------------------------------------------------------------------------------------
# mutations. label -> (file in the variant, old, new, groups to run, the cases that must go red)
# ---------------------------------------------------------------------------------------------
RD = 'reader: '
TA = 'census: tag allowlist: '
TAG_RED = ('```Java FAILs naming file:line and the tag', '```JSON FAILs naming file:line and the tag',
           '```jsonc FAILs naming file:line and the tag',
           'an unknown LOWERCASE tag (```text) FAILs, a new language is an explicit edit',
           'the whole info string is compared (```java title=x FAILs)')
READER_MUTATIONS = {
    'READER: blockquote markers are not counted': (
        "            quotes += 1\n", "            pass\n",
        ('reader', 'census'), {RD + 'blockquoted fence, one marker and its one space stripped',
                               RD + 'nested `> >` fence'}),
    'READER: a marker does not own its ONE optional space': (
        "            if i < n and line[i] == ' ':        # each marker owns ONE optional space\n                i += 1\n", "",
        ('reader',), {RD + 'blockquoted fence, one marker and its one space stripped'}),
    'READER: a tab counts as one column': (
        "        width += 4 if line[j] == '\\t' else 1", "        width += 1",
        ('reader',), {RD + 'tab-indented closer closes a 4-space opener (a tab is 4 columns)'}),
    'READER: a closer need not share the opener prefix shape': (
        "if (q, w) == (cur['q'], cur['w']):", "if True:",
        ('reader', 'census'), {RD + 'closer with a different PREFIX SHAPE does not close (blockquote opener, col0 closer)',
                               RD + 'closer with a different PREFIX SHAPE does not close (indented opener, col0 closer)',
                               'census: orphan: a closer whose prefix shape differs FAILs naming it'}),
    'READER: a body line outside the blockquote no longer ends the fence': (
        "        if q < cur['q']:\n", "        if False:\n",
        ('reader', 'census'), {RD + 'a non-blank body line missing the opener `>` ends the blockquote: quote-break',
                               'census: orphan: a non-blank body line missing the opener `>` FAILs naming it'}),
    'READER: a blank line inside a quoted fence is no longer tolerated': (
        "        if rest.strip() == '':                  # blank: empty, whitespace, or a bare `>` run\n",
        "        if False:\n",
        ('reader',), {RD + 'bare `>` blank line inside a NESTED quoted fence',
                      RD + 'a fully empty line inside a quoted fence is a blank line'}),
    'READER: four-backtick fences are accepted': (
        "            if len(run) > 3:\n", "            if False:\n",
        ('reader', 'census'), {RD + '4-backtick fence is refused at both markers',
                               'census: orphan: a 4-backtick fence FAILs naming both markers'}),
    'READER: ~~~ fences are accepted': (
        "            if rest[0] == '~':\n", "            if False:\n",
        ('reader', 'census'), {RD + '~~~ fence is refused at both markers',
                               'census: orphan: a ~~~ fence FAILs naming both markers'}),
    'READER: a ```lang line inside an open fence is no longer reported': (
        "                problems.append(Problem(no, 'marker', 'a fence marker inside the fence opened at '\n"
        "                                        f\"line {cur['line']}: \" + line.strip()[:60]))\n", "                pass\n",
        ('reader', 'census'), {RD + '```lang line inside an open fence is a marker problem and the fence goes on',
                               'census: orphan: a ```lang line inside an open fence FAILs naming it'}),
    'READER: a fence opener behind a list marker is silently ignored': (
        "                problems.append(Problem(no, 'marker', 'a fence marker behind a list marker is '\n"
        "                                        'not a supported opener: ' + line.strip()[:60]))\n", "                pass\n",
        ('reader', 'census'), {RD + 'a fence opener behind a LIST MARKER is refused (decision: not supported)',
                               'census: orphan: a fence opener behind a list marker FAILs naming it'}),
    'READER: an unclosed fence is no longer reported': (
        "        problems.append(Problem(cur['line'], 'unclosed',\n"
        "                                f\"the fence opened here (```{cur['info']}) has no closer before EOF\"))\n", "",
        ('reader', 'census'), {RD + 'UNCLOSED fence is returned, closed=False, and reported'}),
    'READER: an unclosed fence is dropped instead of returned': (
        "        finish(None, len(text))\n", "        pass\n",
        ('reader',), {RD + 'UNCLOSED fence is returned, closed=False, and reported'}),
    'READER: a fence both quoted and indented is kind indent': (
        "    if quotes:\n        return 'quote'\n    return 'indent' if indent else 'col0'",
        "    if indent:\n        return 'indent'\n    return 'quote' if quotes else 'col0'",
        ('reader',), {RD + 'a blockquote holding an INDENTED fence is kind quote, indent still stripped'}),
    'READER: the blockquote prefix is left on the body': (
        "    for _ in range(quotes):\n", "    for _ in range(0):\n",
        ('reader',), {RD + 'blockquoted fence, one marker and its one space stripped'}),
    'READER: the indentation is left on the body': (
        "    while i < n and cols < indent and line[i] in ' \\t':", "    while i < n and cols < 0 and line[i] in ' \\t':",
        ('reader',), {RD + 'indented fence in a list item, indent stripped from the body'}),
    'READER: inline code at a line start is taken for an opener': (
        "            if '`' in info:\n", "            if False:\n",
        ('reader',), {RD + 'inline code at a line start whose info string holds a backtick is refused'}),
    'READER: offsets stop covering the closer line (fenced_text)': (
        "                    finish(no, starts[idx] + len(line))", "                    finish(no, starts[idx])",
        ('reader',), {RD + 'fenced_text() slices opener line through closer line, prefix intact'}),
    'CENSUS: orphan markers are no longer collected': (
        "        if CENSUS_MARKER.match(line) and no not in accounted:", "        if False and no not in accounted:",
        ('census', 'cli'), {'census: orphan: a 4-backtick fence FAILs naming both markers',
                            'census: orphan: a ~~~ fence FAILs naming both markers',
                            'census CLI: an orphan exits 1'}),
    'CENSUS: unclosed fences and quote-breaks are no longer collected': (
        "        if pr.kind != 'marker':", "        if False:",
        ('census',), {'census: orphan: an UNCLOSED fence FAILs naming its opener',
                      'census: orphan: a non-blank body line missing the opener `>` FAILs naming it'}),
    'CENSUS: zero pages or zero fences is no longer a FAIL': (
        "    floor = c.pages == 0 or c.fences == 0\n", "    floor = False\n",
        ('census',), {'census: a census that visited ZERO pages FAILs',
                      'census: a census that visited pages but ZERO fences FAILs'}),
    'CENSUS: the tag allowlist is no longer enforced': (
        "        if allowed_tags is not None and f.info not in allowed_tags:\n", "        if False:\n",
        ('census', 'cli', 'verify'), {TA + t for t in TAG_RED}),
    'CENSUS: the allowlist folds case (the tag is lower-cased before the test)': (
        "f.info not in allowed_tags:", "f.info.lower() not in allowed_tags:",
        ('census', 'verify'), {TA + t for t in TAG_RED[:2]} | {'verify-docs census section: a fence tagged ```Java is a HARD FAIL naming file:line'}),
    'CENSUS: the allowlist compares the leading word, not the whole info string': (
        "f.info not in allowed_tags:", "f.lang not in allowed_tags:",
        ('census',), {TA + 'the whole info string is compared (```java title=x FAILs)'}),
    'CENSUS: the marker definition forgets list markers': (
        "CENSUS_MARKER = re.compile(r'^(?:[ \\t]|>|[-*+]|\\d+[.)])*(?:```|~~~)')",
        "CENSUS_MARKER = re.compile(r'^(?:[ \\t]|>)*(?:```|~~~)')",
        ('reader', 'census'), {RD + 'a fence opener behind a LIST MARKER is refused (decision: not supported)',
                               'census: orphan: a fence opener behind a list marker FAILs naming it'}),
}

VF = 'verify-docs.sh'
FA = 'verify-docs fence_agree: '
FA_MALFORMED = ('a newline-joined figure (two numbers on two lines) is a malformed-figure FAIL, not a silent pass',
                'a figure with a suffix (5x) is a malformed-figure FAIL',
                'a whitespace-only figure is a malformed-figure FAIL',
                'a malformed CENSUS figure is a malformed-figure FAIL too',
                'a malformed figure produces no shell error text')
_AI_CALL = ('  fence_agree "check-asset-ids.py (json fences)" "$(echo "$OUT" | sed -n '
            '\'s/^  INFO  docs scan: [0-9][0-9]* page(s); \\([0-9][0-9]*\\) ```json fence(s).*/\\1/p\')" "$FC_JSON"\n')
VERIFY_MUTATIONS = {
    'VERIFY: fence_agree no longer refuses an empty figure': (
        '  if [ -z "$2" ]; then\n'
        '    fail "$1: printed no fence count, so it cannot be compared with the census ($3)"\n'
        '  elif case "$2" in',
        '  if case "$2" in',
        ('verify',), {'verify-docs fence_agree: a gate that printed no fence count FAILs, it is never skipped',
                      'verify-docs: type-values: a missing INFO line is a FAIL, not a skip',
                      'verify-docs: asset-ids: a missing docs-scan line is a FAIL, not a skip'}),
    'VERIFY: the doc-type reader stops folding the fence tag to lower case': (
        'def _tag(s): return s.lower()', 'def _tag(s): return s',
        ('doctype',), {'doc-type: a ```Java fence (the case fold is kept on purpose, maintenance/fixtures/doctype/fixture-i.md) '
                       'disqualifies the provenance exclusion (D), so the page is a MISMATCH'}),
    'VERIFY: fence_agree no longer validates the figures before comparing them': (
        '''  elif case "$2" in *[!0-9]*) true ;; *) false ;; esac || case "$3" in ''|*[!0-9]*) true ;; *) false ;; esac; then\n''',
        '  elif false; then\n',
        ('verify',), {FA + n for n in FA_MALFORMED}),
    'VERIFY: fence_agree validates the gate figure but not the census figure': (
        '''|| case "$3" in ''|*[!0-9]*) true ;; *) false ;; esac; then''', '; then',
        ('verify',), {FA + 'a malformed CENSUS figure is a malformed-figure FAIL too'}),
    'VERIFY: fence_agree only notices a gate that read MORE': (
        'elif [ "$2" -ne "$3" ]; then', 'elif [ "$2" -gt "$3" ]; then',
        ('verify',), {'verify-docs fence_agree: a gate that read FEWER fences than the census FAILs, naming both numbers'}),
    'VERIFY: the asset-ids comparison is deleted': (
        _AI_CALL, '',
        ('verify',), {'verify-docs: the type-values (x2) and asset-ids comparisons each exist exactly once',
                      'verify-docs: every gate is compared with the census (7 comparisons)'}),
    'VERIFY: the check-symbols comparison is deleted': (
        '  fence_agree "check-symbols.py (java fences)" "$JF" "$FC_JAVA"\n', '',
        ('verify',), {'verify-docs: every gate is compared with the census (7 comparisons)'}),
    'VERIFY: the census section stops failing on an orphan': (
        '  fail "fence census:"\n', '  :\n',
        ('verify',), {'verify-docs census section: an orphan marker is a HARD FAIL naming file:line',
                      'verify-docs census section: a fence tagged ```Java is a HARD FAIL naming file:line'}),
    'VERIFY: the coverage advisory ignores a fence-count mismatch': (
        '    sys.exit(3)\n', '    pass\n',
        ('codenames',), {'coverage advisory: a harvest of 3 fence(s) against a census of 4 exits 3'}),
    'VERIFY: a census that prints no counts is accepted': (
        'if [ -z "$FC_JAVA" ] || [ -z "$FC_JSON" ] || [ -z "$FC_TOTAL" ]; then', 'if false; then',
        ('verify',), {'verify-docs census section: a census that prints no counts is a HARD FAIL'}),
}

# The heading readers, each reverted to its fence-blind scan (the code that shipped before
# 2026-10-16). label -> (file in the variant, old, new, groups, cases that must go red).
HD = 'reader: fence_lines, '
HEADING_MUTATIONS = {
    'HEADINGS doc-type: _sections() reads headings inside fences': (
        VF,
        '    fenced=doc_fences.parse(txt).fence_lines\n'
        '    hs=[(m.start(), len(m.group(1))) for m in head_re.finditer(txt)\n'
        '        if txt.count("\\n",0,m.start())+1 not in fenced]\n',
        '    hs=[(m.start(), len(m.group(1))) for m in head_re.finditer(txt)]\n',
        ('headings',), {'doc-type headings, a `# comment` in a bash fence does not end the section it sits in (MISMATCH kept)'}),
    'HEADINGS gotcha scan: a `## ` line in a fence opens and closes sections': (
        VF,
        "h = re.match(r'^##\\s+(.*)', line) if ln not in fenced else None\n",
        "h = re.match(r'^##\\s+(.*)', line)\n",
        ('headings',), {'gotcha scan headings, a `## ` line in a fence neither ends nor opens a Gotchas section'}),
    'HEADINGS section_binder: _sections() cuts a section at a fenced `## ` line': (
        'section_binder.py',
        "    ms = [m for m in HEADING.finditer(text)\n"
        "          if text.count('\\n', 0, m.start()) + 1 not in fenced]\n",
        "    ms = list(HEADING.finditer(text))\n",
        ('headings',), {'section_binder headings, a `## ` line in a fence adds no section and the table still binds its own'}),
    'READER: fence_lines leaves out the closer line': (
        'doc_fences.py',
        "occupied.update(range(cur['line'], (closer_no or last_line) + 1))",
        "occupied.update(range(cur['line'], (closer_no or last_line + 1)))",
        ('reader',), {HD + 'col0 fence occupies opener through closer and nothing else',
                      HD + 'blockquoted fence occupies its quoted lines',
                      HD + 'indented fence occupies its lines',
                      HD + 'two fences leave the prose between them unoccupied'}),
    'READER: an unclosed fence occupies only its opener line in fence_lines': (
        'doc_fences.py',
        "occupied.update(range(cur['line'], (closer_no or last_line) + 1))",
        "occupied.update(range(cur['line'], (closer_no or cur['line']) + 1))",
        ('reader',), {HD + 'an UNCLOSED fence occupies everything to EOF',
                      HD + 'a quote-break ends the first fence at the line before it'}),
}

# gate reversions: the gate's `doc_fences` becomes a verbatim copy of its OLD reader.
GATE_SHIMS = {
    'GATE check-symbols: reverted to the column-0 reader': (
        SHIM_COL0, ('symbols',),
        {'check-symbols: dead members in a BLOCKQUOTED and an INDENTED java fence are found',
         'check-symbols healthy twin: the same fences hold, 1 member checked, 4 java fences read'}),
    'GATE check-snippets: reverted to the column-0 reader': (
        SHIM_COL0, ('snippets',),
        {'check-snippets: package-led units in a BLOCKQUOTED and an INDENTED fence that fail javac FAIL',
         'check-snippets healthy twin: both units compile, BLOCKS counts the quoted and indented fences'}),
    'GATE check-type-values: reverted to the indent-only FENCE regex': (
        SHIM_INDENT, ('typevalues',),
        {'check-type-values: unregistered Types in a BLOCKQUOTED and an INDENTED json fence FAIL',
         'check-type-values healthy twin: exact fence denominator and tally',
         'check-type-values: a Type registered only in a BLOCKQUOTED java fence resolves page-locally'}),
    'GATE section_binder: reverted to the indent-only JSON_FENCE regex (body unstripped)': (
        SHIM_BINDER, ('binder', 'defaults'),
        {'section_binder: root keys of a BLOCKQUOTED and of an INDENTED json fence bind their sections',
         'check-defaults: a wrong Default in a section bound ONLY by a quoted / indented fence is found',
         'check-defaults healthy twin: both sections are bound and both Defaults agree'}),
    'GATE JSON-parse check: reverted to the unanchored regex (prefix left on the body)': (
        SHIM_UNANCHORED, ('jsonparse',),
        {'JSON-parse check: a valid json fence inside a BLOCKQUOTE parses (its `> ` is removed), both fences counted'}),
    'GATE doc-type check: reverted to the column-0 reader': (
        SHIM_COL0, ('doctype',),
        {'doc-type: a java fence inside a BLOCKQUOTE disqualifies the provenance exclusion (D), so the page is a MISMATCH',
         'doc-type: a java fence INDENTED in a list item disqualifies the provenance exclusion (D), so the page is a MISMATCH'}),
    'GATE code names: the reader returns nothing': (
        SHIM_NONE, ('codenames',),
        {'code names: the harvest reads the BLOCKQUOTED fence too, and counts both fences'}),
    'GATE fields check: the reader returns nothing': (
        SHIM_NONE, ('fields',),
        {'fields check: a fabricated key in a BLOCKQUOTED and in an INDENTED json fence is suspect',
         'fields check healthy twin: known keys pass, both fences counted'}),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    if not READER.exists() or not VERIFY.exists():
        print('  FAIL  doc_fences.py or verify-docs.sh is missing')
        return 1
    with tempfile.TemporaryDirectory() as t:
        td = pathlib.Path(t)
        jar = make_jar(td)
        real = make_variant(td, 'real')
        c = all_cases(real, jar)
        if c.crashed:
            print(f'  FAIL  the real gates crashed on {len(c.crashed)} case(s): ' + ', '.join(c.crashed))
            return 1
        if len(c.out) < MIN_CASES:
            print(f'  FAIL  {len(c.out)} case(s) ran, floor is {MIN_CASES}. A fixture that examines nothing '
                  f'reports the same thing as one that passes.')
            return 1
        fails = {k: v for k, v in c.out.items() if v}
        if a.verbose:
            for k, v in c.out.items():
                if not v:
                    print(f'  ok   {k}')
        t_base = time.time() - t0
        print(f'\nFIXTURE {len(c.out)} case(s): {len(c.out) - len(fails)} passed, {len(fails)} failed '
              f'({t_base:.1f}s)')
        for k, v in fails.items():
            print(f'  FAIL {k}: ' + '; '.join(v))
        rc = 1 if fails else 0
        if not a.mutations:
            return rc
        if fails:
            print('  FAIL  the base run is red; no mutation below would mean anything')
            return 1

        total = len(READER_MUTATIONS) + len(VERIFY_MUTATIONS) + len(HEADING_MUTATIONS) + len(GATE_SHIMS) + 1
        if total < MIN_MUTATIONS:
            print(f'  FAIL  {total} mutation(s) defined, floor is {MIN_MUTATIONS}. "every mutation red" over '
                  f'an empty table is a claim about nothing.')
            return 1
        print(f'\nMUTATIONS {total} defect(s) reintroduced, each must turn its named case(s) red')
        reader_src = READER.read_text()
        n_red = 0

        def judge(label, variant_dir, groups, names, identity=False):
            nonlocal rc, n_red
            mc = all_cases(variant_dir, jar, groups)
            if mc.crashed:
                rc = 1
                print(f'  FAIL {label}: the MUTANT CRASHED on {len(mc.crashed)} case(s) - broken, not caught: '
                      + ', '.join(mc.crashed))
                return
            red = {k for k, v in mc.out.items() if v}
            unknown = {n for n in names if n not in mc.out}
            if unknown:
                rc = 1
                print(f'  FAIL {label}: names a case that never ran (typo or wrong groups): ' + ', '.join(sorted(unknown)))
                return
            if identity:
                if red:
                    print(f'  FAIL {label}: the control reddened {len(red)} case(s); the harness is broken, '
                          f'so no mutation below would mean anything. Aborting.')
                    for x in sorted(red):
                        print(f'         {x}: ' + '; '.join(mc.out[x]))
                    raise SystemExit(1)
                print(f'  ok   {label} -> {len(mc.out)} case(s) ran, none red')
                return
            stayed = names - red
            if stayed:
                rc = 1
                print(f'  FAIL {label}: the case(s) this defect belongs to stayed GREEN')
                for x in sorted(stayed):
                    print(f'         {x}')
                return
            n_red += 1
            print(f'  ok   {label} -> {len(red)} case(s) red, including all {len(names)} named')
            if a.verbose:
                for r in sorted(red):
                    print(f'         {r}')

        # THE CONTROL, first: an unchanged copy must pass every case it runs.
        ident = make_variant(td, 'identity')
        judge('IDENTITY (no change - the harness control)', ident, ALL_GROUPS, set(), identity=True)

        verify_src = VERIFY.read_text()
        table = [(l, 'doc_fences.py', *m) for l, m in READER_MUTATIONS.items()] + \
                [(l, VF, *m) for l, m in VERIFY_MUTATIONS.items()] + \
                [(l, *m) for l, m in HEADING_MUTATIONS.items()]
        for i, (label, fname, old, new, groups, names) in enumerate(table):
            src = reader_src if fname == 'doc_fences.py' else (HERE / fname).read_text()
            n = src.count(old)
            if n != 1:
                rc = 1
                print(f'  FAIL {label}: the anchor occurs {n} time(s) in {fname}, not once - the mutation '
                      f'is stale and tests nothing')
                continue
            v = make_variant(td, f'mut-reader-{i}')
            (v / fname).write_text(src.replace(old, new, 1))
            judge(label, v, groups, set(names))
        for i, (label, (shim, groups, names)) in enumerate(GATE_SHIMS.items()):
            v = make_variant(td, f'mut-gate-{i}', shim)
            judge(label, v, groups, set(names))

        print(f'\nMUTATIONS {n_red} of {total - 1} mutation(s) turned their named cases red '
              f'(+1 identity control), {time.time() - t0:.1f}s in all')
        if n_red != total - 1:
            rc = 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
