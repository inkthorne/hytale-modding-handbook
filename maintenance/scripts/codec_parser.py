#!/usr/bin/env python3
"""
codec_parser — read a BuilderCodec chain out of decompiled Hytale source and
report the JSON keys it declares, with requiredness.

Phase (a) of queued gate 1 (CLAUDE.md). This is a LIBRARY with a golden fixture
(maintenance/fixtures/registry-oracle/), deliberately built and validated before
any gate consumes it: a parser that cannot reproduce a known-good answer set has
no business failing a doc.

It encodes the §5 discipline from maintenance/registry-oracle-notes.md:

  * A chain is ONE statement, often thousands of characters, full of lambdas.
    Parse to the `.add()`, never to the first balanced paren.
  * Requiredness has TWO forms and they are not interchangeable:
      - a `true` THIRD argument to `KeyedCodec(...)`
      - a `Validators.nonNull()` attached AFTER `append(...)` closes
    A key may carry both (SpawnNPC's `Weight`).
  * `KeyedCodec` occurs raw as well as parameterised. A pattern expecting
    `KeyedCodec<T>` silently skips the raw ones and under-counts.
  * `.appendInherited(...)` declares a key on THIS codec — "Inherited" names the
    builder's self-type generic, not a parent's key.
  * An argument splitter must track `<>` as well as `()`, because type
    parameters hide commas that look top-level.
"""
from __future__ import annotations
import re, pathlib
from dataclasses import dataclass, field

OPEN, CLOSE = {'(': ')', '[': ']', '{': '}'}, {')': '(', ']': '[', '}': '{'}


def _scan(s: str, i: int) -> int:
    """Index just past the balanced bracket opening at s[i]. String/char aware."""
    assert s[i] in OPEN, s[i:i+20]
    depth, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '"' or c == "'":
            q, i = c, i + 1
            while i < n and s[i] != q:
                i += 2 if s[i] == '\\' else 1
            i += 1
            continue
        if c == '/' and i + 1 < n and s[i+1] in '/*':      # comment
            if s[i+1] == '/':
                i = s.find('\n', i) + 1 or n
            else:
                i = s.find('*/', i) + 2
            continue
        if c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('unbalanced')


def _split_args(s: str) -> list[str]:
    """Split a bracket body on top-level commas, tracking <> as well as ()[]{}."""
    out, buf, depth, ang, i, n = [], [], 0, 0, 0, len(s)
    while i < n:
        c = s[i]
        if c == '"' or c == "'":
            j, q = i + 1, c
            while j < n and s[j] != q:
                j += 2 if s[j] == '\\' else 1
            buf.append(s[i:j+1]); i = j + 1; continue
        if c in OPEN:
            depth += 1
        elif c in CLOSE:
            depth -= 1
        elif c == '<' and depth == 0 and _looks_generic(s, i):
            ang += 1
        elif c == '>' and ang and depth == 0:
            ang -= 1
        elif c == ',' and depth == 0 and ang == 0:
            out.append(''.join(buf).strip()); buf = []; i += 1; continue
        buf.append(c); i += 1
    if ''.join(buf).strip():
        out.append(''.join(buf).strip())
    return out


def _looks_generic(s: str, i: int) -> bool:
    """`<` after an identifier is a type parameter; after a value it is less-than."""
    j = i - 1
    while j >= 0 and s[j].isspace():
        j -= 1
    return j >= 0 and (s[j].isalnum() or s[j] in '_$')


@dataclass
class Key:
    name: str
    required_by_arg: bool = False        # `true` third argument to KeyedCodec
    required_by_validator: bool = False  # Validators.nonNull() after append(...)
    raw_keyedcodec: bool = False         # `new KeyedCodec(` with no <T>
    inherited: bool = False              # declared via appendInherited
    @property
    def required(self) -> bool:
        return self.required_by_arg or self.required_by_validator


@dataclass
class Chain:
    cls: str
    keys: list[Key] = field(default_factory=list)
    appends: int = 0
    adds: int = 0
    parent: str | None = None
    @property
    def consistent(self) -> bool:
        """Self-check from §11: appends == adds == keys, per chain."""
        return self.appends == self.adds == len(self.keys)


# NOTE: the field is not always called CODEC (registry-oracle-notes.md §1 records
# TYPE_CODEC, PLUGIN_CODEC, PAGE_CODEC, OPERATION_CODEC), so match any
# SHOUTY name and filter on the suffix. Writing `[A-Z][A-Z0-9_]*CODEC` here
# instead requires a prefix and therefore never matches a plain `CODEC` — it
# silently found nothing on all 44 fixture types before the fixture caught it.
_CODEC_DECL = re.compile(r'\b(?:public|protected|private)?\s*static\s+final\s+'
                         r'(?:\w+\.)*\w*Codec\s*(?:<.*?>)?\s+([A-Z][A-Z0-9_]*)\s*=', re.S)
_KEYED = re.compile(r'new\s+KeyedCodec\s*(<)?')


def parse_chain(src: str, codec_field: str = 'CODEC') -> Chain | None:
    m = None
    for cand in _CODEC_DECL.finditer(src):
        if cand.group(1) == codec_field and cand.group(1).endswith('CODEC'):
            m = cand; break
    if not m:
        return None
    # the whole initialiser, to its terminating ';' at depth 0
    i, depth, n = m.end(), 0, len(src)
    while i < n:
        c = src[i]
        if c in OPEN:
            i = _scan(src, i); continue
        if c == ';' and depth == 0:
            break
        i += 1
    stmt = src[m.end():i]

    ch = Chain(cls=codec_field)
    pm = re.search(r'BuilderCodec\.builder\s*\(', stmt)
    if pm:
        args = _split_args(stmt[pm.end()-1+1:_scan(stmt, pm.end()-1)-1])
        if len(args) >= 3:
            ch.parent = args[2].strip()

    for am in re.finditer(r'\.(appendInherited|append)\s*\(', stmt):
        ch.appends += 1
        opener = am.end() - 1
        close = _scan(stmt, opener)                     # end of append( ... )
        body = stmt[opener+1:close-1]
        first = _split_args(body)[0] if body.strip() else ''
        key = _read_keyedcodec(first)
        if key is None:
            continue
        key.inherited = am.group(1) == 'appendInherited'
        # attachments region: from the append's close to ITS `.add()` at depth 0
        j, d = close, 0
        while j < len(stmt):
            c = stmt[j]
            if c in OPEN:
                if stmt.startswith('.add(', j - 4) and d == 0:
                    break
                j = _scan(stmt, j); continue
            j += 1
        tail = stmt[close:j]
        if 'Validators.nonNull()' in tail:
            key.required_by_validator = True
        ch.keys.append(key)
    ch.adds = len(re.findall(r'\.add\(\s*\)', stmt))
    return ch


def _read_keyedcodec(arg: str) -> Key | None:
    km = _KEYED.search(arg)
    if not km:
        return None
    raw = km.group(1) is None
    i = km.end() - (0 if raw else 1)
    if not raw:                                   # skip the <...> type parameter
        ang, n = 0, len(arg)
        while i < n:
            if arg[i] == '<': ang += 1
            elif arg[i] == '>':
                ang -= 1
                if ang == 0:
                    i += 1; break
            i += 1
    while i < len(arg) and arg[i].isspace():
        i += 1
    if i >= len(arg) or arg[i] != '(':
        return None
    args = _split_args(arg[i+1:_scan(arg, i)-1])
    if not args:
        return None
    nm = re.match(r'^"([^"]*)"$', args[0].strip())
    if not nm:
        return None
    k = Key(name=nm.group(1), raw_keyedcodec=raw)
    if len(args) >= 3 and args[2].strip() == 'true':
        k.required_by_arg = True
    return k


def find_source(fqcn: str, root: pathlib.Path) -> pathlib.Path | None:
    p = root / (fqcn.replace('.', '/') + '.java')
    return p if p.exists() else None
