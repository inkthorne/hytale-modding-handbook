#!/usr/bin/env python3
"""
codec_parser — read a BuilderCodec chain out of decompiled Hytale source and
report the JSON keys it declares, with what each does about being omitted
(`null_validated`) and about an explicit null (`strict_null`).

Phase (a) of queued gate 1 (CLAUDE.md). This is a LIBRARY with a golden fixture
(maintenance/fixtures/registry-oracle/), deliberately built and validated before
any gate consumes it: a parser that cannot reproduce a known-good answer set has
no business failing a doc.

It encodes the §5 discipline from maintenance/registry-oracle-notes.md:

  * A chain is ONE statement, often thousands of characters, full of lambdas.
    Parse to the `.add()`, never to the first balanced paren.
  * "Required" is TWO facts, measured separately (maintenance/probes/requiredness/,
    run live against the jar), and they are not interchangeable:
      - `null_validated`: the field carries a validator that is an INSTANCE OF
        NonNullValidator (`Validators.nonNull()`, and its subclasses
        `nonEmptyArray()` / `nonEmptyMap()`). Only this makes an OMITTED key fail
        decode (BuilderField.nullValidate, run from afterDecodeAndValidate).
      - `strict_null`: a `true` THIRD argument to `KeyedCodec(...)`. It NEVER makes
        an omitted key fail, on any decode path. Its whole effect is that an
        explicit JSON `null` is not treated as absent on the BSON inherit path
        (KeyedCodec.getAndInherit), where it then fails to decode.
    A key may carry both (SpawnNPC's `Weight`). There is deliberately no
    `required` property: the old `required_by_arg or required_by_validator` union
    called 623 keys required that the engine accepts omitted.
    The validator attaches AFTER `append(...)` closes, before `.add()`; for a
    RecordCodec it sits INSIDE the append group (third argument).
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


# --- which validators are NonNullValidator INSTANCES --------------------------------
#
# BuilderField (and RecordField) set `nonNullValidator` to the first validator that is
# `instanceof NonNullValidator`; that, and nothing else, is what nullValidate() acts on.
# Matching the literal text `Validators.nonNull()` misses the subclasses
# NonEmptyArrayValidator / NonEmptyMapValidator, reached through
# `Validators.nonEmptyArray()` / `nonEmptyMap()` (36 keys at 0.7.2). So the set is
# derived from the SOURCE: every class that (transitively) extends NonNullValidator,
# and every `Validators.<factory>()` whose body returns one of them.
#
# The derivation needs the decompiled tree; _PINNED is the same answer written down,
# used when the tree is absent, and check-codec-fixture.py asserts the two agree so a
# game update that adds a subclass or a factory fails the fixture instead of silently
# narrowing the attribute.
_PINNED = {
    'classes': ['NonEmptyArrayValidator', 'NonEmptyMapValidator', 'NonNullValidator'],
    'factories': {'nonEmptyArray': 'NonEmptyArrayValidator',
                  'nonEmptyMap': 'NonEmptyMapValidator',
                  'nonNull': 'NonNullValidator'},
}
SUBCLASS_DETECTION = True     # mutation hook: False = literal `nonNull` only (the old behaviour)
_table_cache: dict = {}


def _jar_src_root() -> pathlib.Path:
    import os
    return pathlib.Path(os.environ.get('HYTALE_JAR_SRC', os.path.expanduser('~/.cache/hytale-jar/src')))


def derive_null_validators(root: pathlib.Path) -> dict:
    """Walk the decompiled tree: classes extending NonNullValidator, and the factories returning them."""
    ext = {}                                   # simple class name -> simple superclass name
    for jp in (root / 'com/hypixel').rglob('*.java'):
        txt = jp.read_text(errors='replace')
        if 'extends' not in txt:
            continue
        for m in re.finditer(r'\bclass\s+(\w+)\s*(?:<[^{]*?>)?\s+extends\s+(\w+)', txt):
            ext[m.group(1)] = m.group(2)
    classes, grew = {'NonNullValidator'}, True
    while grew:
        grew = False
        for c, sup in ext.items():
            if sup in classes and c not in classes:
                classes.add(c); grew = True
    vsrc = (root / 'com/hypixel/hytale/codec/validation/Validators.java').read_text()
    factories = {}
    for m in re.finditer(r'public\s+static\s+(?:<[^>]*>\s*)?[^=;{(]+?\s+(\w+)\s*\(\s*\)\s*\{\s*return\s+(\w+)\.INSTANCE\s*;', vsrc):
        if m.group(2) in classes:
            factories[m.group(1)] = m.group(2)
    return {'classes': sorted(classes), 'factories': factories}


def null_validators() -> dict:
    """The table in force: derived from source when the tree exists, else pinned."""
    if 'v' not in _table_cache:
        try:
            _table_cache['v'] = derive_null_validators(_jar_src_root())
            _table_cache['source'] = 'derived'
        except (OSError, ValueError):
            _table_cache['v'] = _PINNED
            _table_cache['source'] = 'pinned'
    return _table_cache['v']


def classify_validator(expr: str) -> str | None:
    """Name the NonNullValidator kind an expression builds, or None.

    Structural, on the WHOLE expression: `Validators.or(Validators.nonNull(), x)` is an
    OrValidator, not a NonNullValidator, and a substring search for `nonNull()` calls it
    one. Accepted spellings: `Validators.[<T>]factory()`, `Cls.INSTANCE`, `new Cls(...)`,
    where the factory or class is in the derived table."""
    e = expr.strip()
    t = null_validators()
    if not SUBCLASS_DETECTION:
        t = {'classes': ['NonNullValidator'], 'factories': {'nonNull': 'NonNullValidator'}}
    m = re.fullmatch(r'Validators\s*\.\s*(?:<.*?>\s*)?(\w+)\s*\(\s*\)', e, re.S)
    if m and m.group(1) in t['factories']:
        return m.group(1)
    m = re.fullmatch(r'(?:[\w.]+\.)?(\w+)\s*\.\s*INSTANCE', e)
    if m and m.group(1) in t['classes']:
        return m.group(1)
    m = re.match(r'new\s+(?:[\w.]+\.)?(\w+)\s*(?:<[^()]*>)?\s*\(', e)
    if m and m.group(1) in t['classes']:
        return m.group(1)
    return None


_CALL = re.compile(r'\s*\.\s*(?:<[^()]*?>\s*)?([A-Za-z_]\w*)\s*\(')


def _dot_calls(s: str, j: int) -> tuple[list, int, bool]:
    """Parse `.name(args).name(args)...` from s[j], stopping after `.add(...)`.
    Returns (calls, end, closed_by_add)."""
    calls = []
    while True:
        m = _CALL.match(s, j)
        if not m:
            return calls, j, False
        op = m.end() - 1
        cl = _scan(s, op)
        calls.append((m.group(1), s[op+1:cl-1]))
        j = cl
        if m.group(1) == 'add':
            return calls, j, True


def _apply_validators(key: 'Key', exprs: list[str]) -> None:
    for ex in exprs:
        kind = classify_validator(ex)
        if kind:
            key.null_validated = True
            key.null_validators.append(kind)
        else:
            key.other_validators.append(ex.strip())


@dataclass
class Key:
    name: str
    strict_null: bool = False            # `true` third argument to KeyedCodec (NOT "required")
    null_validated: bool = False         # carries an instance of NonNullValidator
    null_validators: list = field(default_factory=list)  # which factories, in order: 'nonNull', 'nonEmptyArray', ...
    other_validators: list = field(default_factory=list)  # validator exprs resolved neither way
    raw_keyedcodec: bool = False         # `new KeyedCodec(` with no <T>
    inherited: bool = False              # declared via appendInherited
    setter: str = ''                     # the append group's 2nd argument, verbatim


@dataclass
class Chain:
    cls: str
    keys: list[Key] = field(default_factory=list)
    appends: int = 0      # .append / .appendInherited groups
    addfields: int = 0    # .addField groups — these do NOT terminate in .add()
    adds: int = 0
    parent: str | None = None
    declared_in_file: int = 0   # `new KeyedCodec` across the WHOLE file
    declared_in_scope: int = 0  # `new KeyedCodec` within the fragment actually parsed
    builder_field: str | None = None
    kind: str = 'builder'       # 'builder' (BuilderCodec / AssetBuilderCodec) or 'record' (RecordCodec)
    unparsed_tails: int = 0     # append groups whose validator tail did not parse to `.add()`

    @property
    def consistent(self) -> bool:
        """§11's self-check: appends == adds == keys.

        NOT a coverage check, and it must never be read as one. All three counts
        come from the same scan, so when the scan finds nothing they are all 0 and
        the check agrees with itself. Measured on build-26: of 88 classes this
        parser failed to read, this predicate endorsed 85. Use `covered`.

        It is also SHAPE-SPECIFIC, which §11 could not see from 44 samples of one
        shape: `.addField(...)` declares a key with NO terminating `.add()`, so
        `appends == adds` holds for the append family alone. Item mixes both in one
        chain — 57 appends + 1 addField in the declaration, 1 append 700 lines below
        it — and SpawnMarkerEntity is addField only (8 keys, zero adds).
        """
        # A RecordCodec chain has no terminating `.add()`: its validators are an argument.
        return (len(self.keys) == self.appends + self.addfields
                and (self.kind == 'record' or self.adds == self.appends))

    @property
    def covered(self) -> bool:
        """Did this chain read every key ITS OWN fragment declares?

        The denominator still comes from outside the scan — that is the point, and
        the only way to catch a scan that found nothing — but it is now scoped to
        the fragment parsed. Scoping it to the whole FILE reported 97 correct chains
        as uncovered, every one of them a file holding more than one codec: on
        `SpawnNPCInteraction` the nested `WeightedNPCSpawn` adds 3 keys the outer
        chain never claimed, so a perfect 14-key parse scored 14/17. Use
        `file_coverage()` for the file-level question.
        """
        return len(self.keys) >= self.declared_in_scope

    @property
    def coverage_gap(self) -> int:
        return max(0, self.declared_in_scope - len(self.keys))


# NOTE: the field is not always called CODEC (registry-oracle-notes.md §1 records
# TYPE_CODEC, PLUGIN_CODEC, PAGE_CODEC, OPERATION_CODEC), so match any
# SHOUTY name and filter on the suffix. Writing `[A-Z][A-Z0-9_]*CODEC` here
# instead requires a prefix and therefore never matches a plain `CODEC` — it
# silently found nothing on all 44 fixture types before the fixture caught it.
_CODEC_DECL = re.compile(r'\b(?:public|protected|private)?\s*static\s+final\s+'
                         r'(?:\w+\.)*\w*Codec\s*(?:<.*?>)?\s+([A-Z][A-Z0-9_]*)\s*=', re.S)
_KEYED = re.compile(r'new\s+KeyedCodec\s*(<)?')


def _through_add(src: str, pos: int) -> int:
    """Extend to just past the `.add()` that terminates an append group.

    Without this the fragment stops at the append's closing paren and its `.add()`
    is never counted, so `adds == appends` fails by exactly the number of appends
    made outside the declaration."""
    j = pos
    while j < len(src):
        if src[j] in OPEN:
            if src.startswith('.add(', j - 4):
                return _scan(src, j)
            j = _scan(src, j); continue
        if src[j] == ';':
            return j
        j += 1
    return pos


def _record_validators(args: list[str]) -> tuple[list[str], bool]:
    """Validator expressions of one RecordCodec `.append(codec, accessor[, validator | opts -> ...])`.

    A RecordCodec has no `.add()`: the validator is the append group's THIRD argument,
    either a bare Validator or an `opts -> opts.documentation(..).addValidator(..)` lambda.
    Returns (expressions, parsed_ok)."""
    if len(args) < 3:
        return [], True
    third = args[2].strip()
    lm = re.match(r'(\w+)\s*->\s*', third)
    if not lm:
        return [third], True
    body = third[lm.end():].strip()
    if not body.startswith(lm.group(1)):
        return [], False                      # block lambda or another shape: say so
    calls, end, _ = _dot_calls(body, len(lm.group(1)))
    if body[end:].strip():
        return [], False
    return [a for n, a in calls if n == 'addValidator'], True


def _collect(stmt: str, kind: str = 'builder') -> Chain:
    """Scan one text fragment for append/appendInherited/addField groups."""
    out = Chain(cls='', kind=kind)
    for am in re.finditer(r'\.(appendInherited|append|addField)\s*\(', stmt):
        if am.group(1) == 'addField':
            out.addfields += 1
        else:
            out.appends += 1
        opener = am.end() - 1
        close = _scan(stmt, opener)                     # end of append( ... )
        body = stmt[opener+1:close-1]
        args = _split_args(body) if body.strip() else []
        key = _read_keyedcodec(args[0]) if args else None
        if key is None:
            continue
        key.inherited = am.group(1) == 'appendInherited'
        # The setter is the group's SECOND argument, and it is the only written
        # record of which FIELD a key sets. The names differ often enough that a
        # casing rule is not an option: `ClearOutXZ` sets `clearoutXZ` and
        # `DisplayName` sets `displayNameKey`. Stored verbatim; defaults_probe
        # decides what it can read out of it and refuses the rest.
        if len(args) > 1:
            key.setter = args[1].strip()
        if am.group(1) == 'addField':
            # `.addField(codec, setter, getter)` takes no validators and no `.add()`
            # follows it. The old tail scan, bracket-aware but not call-aware, ran on from
            # here to the NEXT append's `.add()` and credited this key with that key's
            # validators.
            pass
        elif kind == 'record':
            exprs, ok = _record_validators(args)
            if not ok:
                out.unparsed_tails += 1
            _apply_validators(key, exprs)
        else:
            calls, _, closed = _dot_calls(stmt, close)
            if not closed:
                out.unparsed_tails += 1
            _apply_validators(key, [a for n, a in calls if n == 'addValidator'])
        out.keys.append(key)
    out.adds = len(re.findall(r'\.add\(\s*\)', stmt))
    return out


def parse_chain(src: str, codec_field: str = 'CODEC', occurrence: int = 0) -> Chain | None:
    m = None
    seen = 0
    for cand in _CODEC_DECL.finditer(src):
        if cand.group(1) == codec_field and cand.group(1).endswith('CODEC'):
            if seen == occurrence:
                m = cand; break
            seen += 1
    if not m:
        # Explicit non-CODEC field (a `*_BUILDER`): its declared type is
        # `AssetBuilderCodec.Builder<...>`, which the codec-typed pattern above
        # cannot match, so look the field up by name alone.
        fm = re.search(r'\bstatic\s+final\s+[\w.]+(?:<.*?>)?\s+' + re.escape(codec_field) + r'\s*=', src, re.S)
        if not fm:
            return None
        m = fm
    # the whole initialiser, to its terminating ';' at depth 0
    i, n = m.end(), len(src)
    while i < n:
        c = src[i]
        if c in OPEN:
            i = _scan(src, i); continue
        if c == ';':
            break
        i += 1
    stmt = src[m.end():i]

    # A chain is often built on a separate `*_BUILDER` field and only `.build()`-ed
    # into the public codec: `Item.CODEC = CODEC_BUILDER.build()` carries 58 keys
    # that a scan of the CODEC statement alone reports as zero — on the corpus's
    # most-documented asset type. Follow the field, then also collect appends made
    # on it ELSEWHERE in the file (Item.java:1007 adds `State` far below the
    # declaration), because statement-scoped parsing is an assumption, not a rule.
    builder = None
    bm = re.match(r'\s*([A-Za-z_]\w*)\s*\.\s*build\s*\(\s*\)\s*$', stmt)
    if bm:
        builder = bm.group(1)
        inner = parse_chain(src, builder)
        if inner is not None:
            # Skip appends inside the builder's OWN declaration (already parsed) and
            # take every other one in the file. Filtering on "after the CODEC
            # declaration" instead would silently drop appends made BETWEEN the two
            # declarations; build-26 has none, but an unexercised shape assumption is
            # what produced both of this parser's earlier bugs.
            bd = re.search(r'\bstatic\s+final\s+[\w.]+(?:<.*?>)?\s+' + re.escape(builder) + r'\s*=', src, re.S)
            b_start = bd.start() if bd else 0
            b_end = b_start
            while b_end < len(src):
                if src[b_end] in OPEN:
                    b_end = _scan(src, b_end); continue
                if src[b_end] == ';':
                    break
                b_end += 1
            extra = ''.join(
                src[mm.start():_through_add(src, _scan(src, src.index('(', mm.end() - 1)))]
                for mm in re.finditer(re.escape(builder) + r'\s*\.\s*(?:appendInherited|append|addField)\s*\(', src)
                if not (b_start <= mm.start() < b_end))
            if extra:
                inner2 = _collect(extra, inner.kind)
                inner.keys.extend(inner2.keys)
                inner.appends += inner2.appends
                inner.addfields += inner2.addfields
                inner.adds += inner2.adds
                inner.unparsed_tails += inner2.unparsed_tails
            inner.cls = codec_field
            inner.builder_field = builder
            inner.declared_in_file = len(re.findall(r'new\s+KeyedCodec', src))
            inner.declared_in_scope += len(re.findall(r'new\s+KeyedCodec', extra))
            return inner

    ch = Chain(cls=codec_field,
               declared_in_file=len(re.findall(r'new\s+KeyedCodec', src)),
               declared_in_scope=len(re.findall(r'new\s+KeyedCodec', stmt)))
    # The parent's POSITION depends on which builder opened the chain, and reading
    # only `builder(...)`'s third argument severs the link for every abstract base:
    #   BuilderCodec.builder(X.class, X::new, Parent.CODEC)   -> parent is arg 2
    #   BuilderCodec.abstractBuilder(X.class, Parent.CODEC)   -> parent is arg 1
    # 96 chains use abstractBuilder against 1516 plain builders, which looks
    # negligible and is not: every one is a BASE class, so those 96 links are
    # exactly the ones other chains inherit through. Found by auditing why 15
    # inherited-scope bindings were rejected on `Next`, a key SimpleInteraction
    # declares that the parent walk could not reach.
    for pat, idx in ((r'BuilderCodec\.abstractBuilder\s*\(', 1),
                     (r'BuilderCodec\.builder\s*\(', 2)):
        pm = re.search(pat, stmt)
        if not pm:
            continue
        args = _split_args(stmt[pm.end()-1+1:_scan(stmt, pm.end()-1)-1])
        if len(args) > idx:
            ch.parent = args[idx].strip()
        break

    ch.kind = 'record' if re.search(r'\bRecordCodec\s*\.\s*(?:builder|rawBuilder)\s*\(', stmt) else 'builder'
    got = _collect(stmt, ch.kind)
    ch.unparsed_tails = got.unparsed_tails
    ch.keys, ch.appends, ch.addfields, ch.adds = got.keys, got.appends, got.addfields, got.adds
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
        k.strict_null = True
    return k


def all_chains(src: str) -> list[Chain]:
    """Every codec declaration in a file, including repeated field names.

    102 files declare the same field name more than once — nested classes each
    carrying their own `CODEC` (`InventoryComponent` has 7). Returning only the
    first is a worse silence than returning nothing, because `codec_fields()`
    faithfully reports `['CODEC', 'CODEC']` and there was no way to address the
    second.
    """
    out, counts = [], {}
    for name in codec_fields(src):
        idx = counts.get(name, 0)
        counts[name] = idx + 1
        ch = parse_chain(src, name, idx)
        if ch is not None:
            out.append(ch)
    return out


def file_coverage(src: str) -> tuple[int, int]:
    """(keys read across every chain, `new KeyedCodec` declared in the file)."""
    return (sum(len(c.keys) for c in all_chains(src)),
            len(re.findall(r'new\s+KeyedCodec', src)))


def codec_fields(src: str) -> list[str]:
    """Every codec-typed SHOUTY field in a file.

    `parse_chain` defaults to a field named plainly `CODEC`; 21 classes in build-26
    declare their codec as `MESSAGE_CODEC`, `PLAYER_SKIN_CODEC`, `TAGS_CODEC` and
    the like, and for those the default returns None. That is correct behaviour and
    a bad silence, so callers can enumerate instead of guessing.
    """
    return [m.group(1) for m in _CODEC_DECL.finditer(src)]


def find_source(fqcn: str, root: pathlib.Path) -> pathlib.Path | None:
    """Resolve a FQCN to a file, tolerating NESTED types.

    `EventLocation.Config` is one file, not a `Config.java` inside an
    `EventLocation/` directory — mapping every dot to a separator returns None for
    every nested class in the corpus.
    """
    parts = fqcn.split('.')
    for cut in range(len(parts), 0, -1):
        p = root / ('/'.join(parts[:cut]) + '.java')
        if p.exists():
            return p
    return None
