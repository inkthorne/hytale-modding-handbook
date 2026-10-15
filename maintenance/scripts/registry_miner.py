#!/usr/bin/env python3
"""
registry_miner — enumerate the `"Type"` vocabulary of every codec registry in the
decompiled Hytale source, and say for each whether that vocabulary is knowable.

Phase (b) of queued gate 1 (CLAUDE.md). Library only; no gate is wired to it.

Everything here is shaped by measurements in maintenance/registry-oracle-notes.md
§1-§2, each of which killed an obvious approach:

  * TWO registration forms, disjoint for Interaction.CODEC (89 + 35 = 124).
    Mining only `X.CODEC.register("Name", …)` sees 72% and reports a clean run.
  * Calls CHAIN: one statement can register seven names. Anchor the registry per
    STATEMENT, then take every `.register(` in it.
  * The field is not always `CODEC` — TYPE_CODEC, PLUGIN_CODEC, PAGE_CODEC,
    OPERATION_CODEC all occur, in both forms. Match `[A-Z_]*CODEC` structurally.
  * The name is not always argument ONE. `register(Class, "Name", codec)` is
    every GameplayConfig/WorldConfig PLUGIN_CODEC site; `register(\\s*"` sees none.
  * Ids can be `static final String` CONSTANTS — resolve them per file.
  * Ids can be RUNTIME values, so a registry has three verdicts, not two. The
    false-positive guard matters: `register(Priority.DEFAULT, "Name", …)` has a
    non-literal in position one while the id is a literal in position two, and a
    shape test reading only argument one calls a dozen closed registries open.
  * The receiver is not always spelled. `CODEC.register("Box", …)` inside the class
    that declares CODEC has NO `Receiver.` before the field (69 sites in 20 classes at
    0.7.2: 18 registries invisible to the first version of this miner, and
    `Condition.CODEC` short by 15 names), and `getCodecRegistry(PAGE_CODEC)` is its
    form-2 analogue. Such a site is bound by LEXICAL SCOPE (class `_Lexical`), walking
    outward from the call and stopping at the first scope that decides the name: a local,
    parameter or lambda parameter (excluded), a class declaring a static field of that
    name (bound), a class declaring an instance field of it (excluded), a class that
    declares neither but extends/implements something, or an anonymous `new X() {…}` body
    (UNRESOLVED — it may inherit the name and Java would bind it there first). There is
    no superclass rule that finds out, so such a site is reported, never guessed, and the
    fixture pins UNRESOLVED at 0 on the real trees. A call is excluded only by a PROPERTY
    of its receiver (a `this.`/`super.` receiver too), never by package or file. Every
    `Site` records its `spelling`, so a figure can be checked against the qualified
    population alone (the hand-derived fixture figures) or the unqualified one (derived
    by hand-registry-recount.py).
  * Anchors and `.register(` calls are read from comment- and string-masked text: a
    registration spelled in a comment or a string is not one.
  * Key a registry by its FULLY-QUALIFIED declaring type. Keying on the simple
    name collapses distinct `Config` / `Content` / `Context` / `Op` / `Shape`
    registries into single bogus rows.

A THIRD form was added on 2026-09-04 and is NOT a codec registry at all — see
§1's third correction. `NPCPlugin.registerCoreComponentType(name, Builder::new)`
(194 call sites, 10 files) puts a name into a builder FACTORY, and which factory
is decided by the builder's `category()` return type, not by any field on a
codec. So the vocabulary is partitioned by `Sensor` / `BodyMotion` / `Action` /
`MotionController` / … rather than by `X.CODEC`, and forms 1 and 2 cannot see a
single one of those ~200 names. That gap produced a wrong answer the same day:
`"Type": "Kill"` in effects-stats.md was first read as registered NOWHERE, when
it is a registered SENSOR — a §4 collision, not an invention. The registry keys
these synthesise carry the field `CORE_COMPONENT_TYPES`, which is deliberately
not a real Java field name: nothing in the jar is called that, so a reader who
greps for it finds this note rather than a phantom codec.
"""
from __future__ import annotations
import re, pathlib, sys, collections
from dataclasses import dataclass, field
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from codec_parser import _scan, _split_args, find_source

# NOTE the leading class is OPTIONAL. `[A-Z][A-Z0-9_]*CODEC` requires at least one
# character before the literal CODEC and therefore cannot match a field named plainly
# `CODEC` — which is 578 of the direct registrations. That exact regex had already been
# found and fixed in codec_parser.py hours earlier and was reintroduced here by copying
# the constraint's intent without its correction. §1's own advice is `\.[A-Z_]*CODEC\b`,
# with a star, for precisely this reason.
CODEC_FIELD = r'[A-Z0-9_]*CODEC'
_FORM2 = re.compile(r'getCodecRegistry\s*\(\s*([\w.]+)\.(' + CODEC_FIELD + r')\s*\)')
_FORM1 = re.compile(r'\b([\w.]+)\.(' + CODEC_FIELD + r')\s*\.register\s*\(')
# The UNQUALIFIED spellings: the field is a bare identifier, so it can only mean a
# field visible from the call site's own lexical scope. `(?<![\w.])` is what makes
# the pattern unqualified. `this.CODEC` / `super.CODEC` match the QUALIFIED patterns
# with a receiver of `this`/`super`; mine_file reports those as excluded.
_FORM2U = re.compile(r'getCodecRegistry\s*\(\s*(' + CODEC_FIELD + r')\s*\)')
_FORM1U = re.compile(r'(?<![\w.$])(' + CODEC_FIELD + r')\s*\.register\s*\(')
_REGISTER = re.compile(r'\.register\s*\(')
_CONST = re.compile(r'static\s+final\s+String\s+(\w+)\s*=\s*"([^"]*)"\s*;')
_IMPORT = re.compile(r'^import\s+(?:static\s+)?([\w.]+);', re.M)
_PKG = re.compile(r'^package\s+([\w.]+);', re.M)
_LITERAL = re.compile(r'^"([^"]*)"$')
# `Schema` registers `CODEC.register((Object)"null", …)`: the literal sits behind a cast
# because the id parameter is `Object`. It is still a literal id, not a runtime value.
_CAST_LITERAL = re.compile(r'^\(\s*[\w.$<>?,\s]+\s*\)\s*"([^"]*)"$')
_FORM3 = re.compile(r'registerCoreComponentType\s*\(')
_CTOR_REF = re.compile(r'^([\w.]+)::new$')
_DECLARATION = re.compile(r'\s*(?:throws\s+[\w.,\s]+?)?\{')
_CATEGORY = re.compile(r'Class\s*<\s*([\w.]+)\s*>\s+category\s*\(')
_EXTENDS = re.compile(r'\bclass\s+\w+(?:\s*<[^{]*?>)?\s+extends\s+([\w.]+)')
CORE_COMPONENT_FIELD = 'CORE_COMPONENT_TYPES'
UNRESOLVED_OWNER = '<owner-unresolved>'
UNRESOLVED_CATEGORY = '<category-unresolved>'


@dataclass
class Site:
    file: str
    line: int
    form: int                 # 1 = X.FIELD.register(...), 2 = getCodecRegistry(X.FIELD)
    name: str | None          # resolved id, when statically knowable
    id_expr: str = ''         # the raw argument, when not
    kind: str = 'literal'     # literal | constant | indirect | runtime | ambiguous
    arg_index: int = 0        # WHICH argument carried the id (§1: not always 0)
    stmt: int = 0             # offset of the enclosing statement, so sites != names
    spelling: str = 'qualified'   # 'qualified' (`X.FIELD`) | 'unqualified' (bare `FIELD`,
                                  # bound by lexical scope) — figures are checked per spelling


@dataclass
class Registry:
    declaring_type: str       # fully qualified where resolvable
    field: str
    sites: list[Site] = field(default_factory=list)

    @property
    def key(self): return f'{self.declaring_type}.{self.field}'
    @property
    def names(self):
        # `if s.name` drops the EMPTY id too: Schema registers `(Object)""` under
        # Priority.DEFAULT, the default entry rather than a discriminator anyone writes
        # as a "Type". Such a site is RESOLVED (it does not make the registry open) and
        # is not a vocabulary name. Decided 2026-10-15; fixture: unqualified.empty_id_decision.
        return sorted({s.name for s in self.sites if s.name})
    @property
    def open_sites(self): return [s for s in self.sites if s.name is None]
    @property
    def verdict(self):
        """§2: three outcomes — but only TWO are decidable from the source alone.

        'closed' vs 'open' is what a miner can know; whether a closed registry is
        *fully documented* needs the doc side and arrives in phase (c). Do not read
        this as implementing the third verdict.
        """
        return 'open' if self.open_sites else 'closed'
    def forms(self):
        """Registration COUNTS, not statements — §1 distinguishes them
        ('21 sites, 35 names'), because form 2 chains many registers per statement."""
        return {1: sum(1 for s in self.sites if s.form == 1),
                2: sum(1 for s in self.sites if s.form == 2)}
    def statements(self, form=None, spelling=None):
        return len({s.stmt for s in self.sites if (form is None or s.form == form)
                    and (spelling is None or s.spelling == spelling)})
    def of_spelling(self, spelling):
        return [s for s in self.sites if s.spelling == spelling]


def _resolve_type(simple: str, imports: dict[str, str], pkg: str) -> str:
    """`EventLocation.Config` -> fqcn of EventLocation + '.Config'. §1's closing note:
    keying on the simple name collapses distinct registries into one row."""
    head, *rest = simple.split('.')
    base = imports.get(head) or (f'{pkg}.{head}' if pkg else head)
    return '.'.join([base, *rest])


def _delimiters(src: str) -> list[int]:
    """Offsets of every `;`, `{`, `}` outside strings and comments, at ANY depth.

    An earlier version split on `;` at bracket depth zero and skipped whole class
    bodies, so it found ZERO registrations across the corpus while exiting clean —
    the same silent-zero failure phase (a)'s regex had. A statement boundary in
    Java is not a depth-zero construct; it is a token.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'':
            q, i = c, i + 1
            while i < n and src[i] != q:
                i += 2 if src[i] == '\\' else 1
            i += 1; continue
        if c == '/' and i + 1 < n and src[i+1] in '/*':
            if src[i+1] == '/':
                j = src.find('\n', i); i = n if j < 0 else j + 1
            else:
                j = src.find('*/', i); i = n if j < 0 else j + 2
            continue
        if c in ';{}':
            out.append(i)
        i += 1
    return out


def _statement_spans(src: str):
    """Yield (start, end) for every statement containing at least one `.register(`."""
    import bisect
    delims = _delimiters(src)
    spans = {}
    for rm in _REGISTER.finditer(src):
        k = bisect.bisect_left(delims, rm.start())
        start = delims[k-1] + 1 if k else 0
        end = delims[k] if k < len(delims) else len(src)
        # a chained statement ends at the delimiter AFTER its last register
        while end < len(src) and src[start:end].count('(') > src[start:end].count(')'):
            k += 1
            end = delims[k] if k < len(delims) else len(src)
        spans[start] = max(spans.get(start, 0), end)
    for start in sorted(spans):
        yield src[start:spans[start]], start


def _mask(src: str) -> str:
    """`src` with every comment and the INSIDE of every string/char literal replaced by
    spaces (newlines kept), so offsets still index the original. Structure — braces,
    declarations — is read from this; ids are read from the original."""
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in '"\'':
            q, j = c, i + 1
            while j < n and src[j] != q:
                j += 2 if src[j] == '\\' else 1
            for k in range(i + 1, min(j, n)):
                if out[k] != '\n': out[k] = ' '
            i = j + 1; continue
        if c == '/' and i + 1 < n and src[i+1] in '/*':
            if src[i+1] == '/':
                j = src.find('\n', i); j = n if j < 0 else j
            else:
                j = src.find('*/', i); j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n': out[k] = ' '
            i = j; continue
        i += 1
    return ''.join(out)


_CLASS_HEADER = re.compile(r'(?<![\w.$])(?:(class|interface|enum)\s+(\w+)|(record)\s+(\w+)\s*[(<])')
_NEW_TYPE = re.compile(r'\bnew\s+[\w.$<>?, ]+?\s*$')
_INHERITS = re.compile(r'\b(?:extends|implements)\b')
_FIELD_NAME = re.compile(r'(?<![\w.$])(' + CODEC_FIELD + r')\s*$')
_FIELD_DECLARATOR = re.compile(r',\s*(' + CODEC_FIELD + r')\s*(?:=|$)')
_NOT_A_TYPE = frozenset('return throw new else case assert yield instanceof in do'.split())


def _is_anonymous(head: str) -> bool:
    """`… new Base(args) ` — the text before a `{` ends in the argument list of a `new`.
    The `(` is found by walking back from the final `)`, so `if (new Foo().ok()) {` (whose
    last paren group is not the constructor's) is not mistaken for one."""
    h = head.rstrip()
    if not h.endswith(')'):
        return False
    depth = 0
    for j in range(len(h) - 1, -1, -1):
        if h[j] == ')':
            depth += 1
        elif h[j] == '(':
            depth -= 1
            if depth == 0:
                return bool(_NEW_TYPE.search(h[:j]))
    return False


def _drop_generics(text: str) -> str:
    """`class Foo<T extends Bar<U>> extends Base` -> `class Foo extends Base`: the bound
    inside <> is not an inheritance clause."""
    prev = None
    while prev != text:
        prev, text = text, re.sub(r'<[^<>]*>', '', text)
    return text


@dataclass
class _Scope:
    open: int
    header: int               # offset where the text before `{` begins (method parameters live here)
    close: int = -1
    cls: str | None = None    # class/interface/enum/record NAME, or None for a plain block
    iface: bool = False
    anon: bool = False        # `new Base() { … }`: a class body with no name
    inherits: bool = False    # may inherit members: extends/implements clause, or anonymous
    fields: set = field(default_factory=set)   # static CODEC-shaped fields declared directly in this class body
    inst: set = field(default_factory=set)     # INSTANCE CODEC-shaped fields declared directly in it


class _Lexical:
    """The brace structure of ONE file, for binding an unqualified identifier.

    An unqualified `CODEC.register(` means "the CODEC visible from here", and Java's
    rule for that is lexical: a local or parameter first, then each enclosing class
    outward — each class contributing its OWN members and the ones it INHERITS. So the
    lookup walks the scopes enclosing the call site from the inside out and stops at
    the first that decides the name:

      * a block that declares a LOCAL/PARAMETER (or a lambda parameter) of that name
        -> the call is EXCLUDED (it is not the registry field);
      * a class declaring a STATIC field of that name       -> the call is bound to it;
      * a class declaring an INSTANCE field of that name    -> EXCLUDED (not the static registry);
      * a class that declares none but has an extends/implements clause, or an anonymous
        class body       -> UNRESOLVED: the name may be inherited, and Java would bind it
        there before looking outward. There is NO superclass rule that finds out, so the
        site is listed rather than guessed; the fixture pins UNRESOLVED at 0 on the real
        trees. Skipping such a class and binding to the outer field was the first
        version's guess (review, 2026-10-15).
      * nothing                                              -> UNRESOLVED.

    Lambdas and array initialisers are plain blocks — only a header naming
    class/interface/enum/record makes a scope a class, and `new X(…) {` an anonymous one.
    """
    def __init__(self, src: str, masked: str | None = None):
        m = self.masked = masked if masked is not None else _mask(src)
        self.scopes: list[_Scope] = []
        stack, last = [], -1
        for i, c in enumerate(m):
            if c == '{':
                head = m[last + 1:i]
                ch = _CLASS_HEADER.search(head)
                sc = _Scope(i, last + 1)
                if ch:
                    sc.cls = ch.group(2) or ch.group(4)
                    sc.iface = ch.group(1) == 'interface'
                    sc.inherits = bool(_INHERITS.search(_drop_generics(head[ch.end():])))
                elif _is_anonymous(head):
                    sc.anon = sc.inherits = True
                self.scopes.append(sc); stack.append(sc); last = i
            elif c == '}':
                if stack: stack.pop().close = i
                last = i
            elif c == ';':
                last = i
        for sc in self.scopes:
            if sc.close < 0: sc.close = len(m)
        for sc in self.scopes:
            if sc.cls:
                self._members(sc)

    def _members(self, sc: _Scope):
        """The CODEC-shaped fields declared directly in class `sc`, split static/instance.
        A member is the text between boundaries at the class's own depth; a field member
        ends in `;`, its HEAD (up to the first `=`) carries the modifiers and the first
        declarator, and further declarators follow commas (`static X A_CODEC = …, CODEC = …;`)."""
        m, depth, start = self.masked, 0, sc.open + 1
        for i in range(sc.open + 1, sc.close):
            c = m[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and not re.match(r'\s*[;,).\]]', m[i + 1:i + 40]):
                    # a method, nested class or initialiser block ends the member — but a
                    # `}` followed by `;` or `)` closes a lambda or anonymous body INSIDE a
                    # field initialiser (`CODEC = new AssetCodecMapCodec<…>(…, (t, k) -> {…});`),
                    # and the member goes on to its `;`
                    start = i + 1
            elif c == ';' and depth == 0:
                seg = m[start:i]
                start = i + 1
                eq = seg.find('=')
                head = seg if eq < 0 else seg[:eq]
                if '(' in head:           # a method declaration, not a field
                    continue
                names = []
                hm = _FIELD_NAME.search(head)
                if hm:
                    names.append(hm.group(1))
                names += _FIELD_DECLARATOR.findall(seg)
                static = sc.iface or bool(re.search(r'\bstatic\b', head))
                for n in names:
                    (sc.fields if static else sc.inst).add(n)

    def _owner(self, off):
        """The scope a declaration at `off` belongs to: the innermost scope whose body
        contains it, or the block whose HEADER contains it (a method's parameters)."""
        best = None
        for sc in self.scopes:
            if sc.header <= off < sc.close and (best is None or sc.open > best.open):
                best = sc
        return best

    def resolve(self, off: int, fld: str):
        """('class', [outer..declaring class names]) | ('local' | 'instance', None) |
        ('unresolved', None)."""
        chain = [sc for sc in self.scopes if sc.open < off < sc.close]
        chain.sort(key=lambda sc: sc.open)
        local = re.compile(r'(?<![\w.$])([\w$.]+(?:\s*<[^;(){}=]*?>)?(?:\s*\[\s*\])*)\s+'
                           + re.escape(fld) + r'\s*[=;,:)]')
        lam = re.compile(r'(?<![\w.$])' + re.escape(fld) + r'\s*->|\((?:[^()]*,)?\s*'
                         + re.escape(fld) + r'\s*(?:,[^()]*)?\)\s*->')
        for k in range(len(chain) - 1, -1, -1):
            sc = chain[k]
            if sc.cls:
                if fld in sc.fields:
                    return 'class', [c.cls for c in chain[:k + 1] if c.cls]
                if fld in sc.inst:
                    return 'instance', None
                if sc.inherits:
                    return 'unresolved', None
                continue
            if sc.anon:
                return 'unresolved', None
            for lm in local.finditer(self.masked, sc.header, off):
                if lm.group(1).split('.')[-1] in _NOT_A_TYPE:
                    continue
                if self._owner(lm.start(1)) is sc:
                    return 'local', None
            for lm in lam.finditer(self.masked, sc.header, off):
                # a lambda parameter is in scope for the lambda's own body: the block it
                # heads (match inside this block's header), or the rest of its statement
                in_header = lm.start() < sc.open
                if in_header or (self._owner(lm.start()) is sc
                                 and not re.search(r'[;{}]', self.masked[lm.end():off])):
                    return 'local', None
        return 'unresolved', None


def _category_of(builder: str, imports: dict, pkg: str, root: pathlib.Path,
                 _seen: frozenset = frozenset()) -> str | None:
    """FQCN of the category a core-component builder registers into, or None.

    `registerCoreComponentType("Kill", BuilderSensorKill::new)` says nothing about
    which slot `Kill` is legal in; `NPCPlugin:1507-1509` routes it by
    `builder.get().category()`. The return TYPE carries the answer — every
    implementation is `public [final] Class<X> category()` — so this reads the
    signature rather than the body, and walks `extends` when a concrete builder
    inherits the method (the common case: 191 of 194 sites resolve through a
    `Builder*Base`). Returns None rather than guessing, and the caller counts
    those: a resolver that silently substitutes a plausible category would put
    real names under the wrong slot, which is worse than an admitted gap.
    """
    if builder in _seen:               # a cycle in the decompiled output
        return None
    fq = _resolve_type(builder, imports, pkg)
    src_file = find_source(fq, root) or find_source(builder, root)
    if src_file is None:
        return None
    body = src_file.read_text(errors='replace')
    own_pkg_m = _PKG.search(body)
    own_pkg = own_pkg_m.group(1) if own_pkg_m else ''
    own_imports = {f.rsplit('.', 1)[-1]: f for f in _IMPORT.findall(body)}
    cm = _CATEGORY.search(body)
    if cm:
        cat = _resolve_type(cm.group(1), own_imports, own_pkg)
        # The category must name a REAL type. `Builder.java` declares the method
        # as `public Class<T> category();` — a type VARIABLE — and _resolve_type
        # happily turns `T` into `…npc.asset.builder.T`, a plausible-looking FQCN
        # that is not `<category-unresolved>` and so slips past the guard built
        # for exactly this. Today nothing reaches it, because this walk follows
        # `extends` and `Builder` is only ever reached through `implements`. That
        # is an unstated traversal-order property protecting a 194-site resolver,
        # and the obvious future hardening — "also follow interfaces" — is the
        # regression. Requiring the captured name to resolve to a source file
        # makes the protection deliberate instead of emergent, and fails LOUDLY
        # (into the bucket the fixture pins at zero) rather than quietly.
        if find_source(cat, root) is None:
            return None
        return cat
    em = _EXTENDS.search(body)
    if em:
        return _category_of(em.group(1), own_imports, own_pkg, root,
                            _seen | {builder})
    return None


def _mine_core_components(src: str, path: pathlib.Path, imports: dict, pkg: str,
                          consts: dict, root: pathlib.Path | None):
    """Form 3. Yields (category_fqcn_or_None, CORE_COMPONENT_FIELD, Site)."""
    for m in _FORM3.finditer(src):
        opener = m.end() - 1
        try:
            close = _scan(src, opener)
            args = _split_args(src[opener + 1:close - 1])
        except (ValueError, AssertionError):
            continue
        if len(args) < 2 or _DECLARATION.match(src, close):
            # NPCPlugin:1507 DECLARES the method, and its parameter list
            # (`String name`, `Supplier<Builder<T>> builder`) is two arguments
            # like every call site's, so an arity test does not exclude it. A
            # declaration is the occurrence followed by a body; skipping it by
            # name or file would break the moment the method moves or a second
            # overload appears. Left in as `<category-unresolved>` it read as
            # one genuinely unresolvable site, which is the false positive the
            # unresolved bucket exists to make impossible to ignore.
            continue
        name, kind, expr, idx = _pick_name(args[:1], consts)
        cat = None
        if root is not None:
            ref = _CTOR_REF.match(args[1].strip())
            if ref:
                cat = _category_of(ref.group(1).split('.')[-1], imports, pkg, root)
        line = src.count('\n', 0, m.start()) + 1
        yield cat, CORE_COMPONENT_FIELD, Site(str(path), line, 3, name, expr,
                                              kind, idx, m.start())

@dataclass
class Skip:
    """A registration-shaped call that was NOT mined, and why. Reported, never dropped."""
    file: str
    line: int
    field: str
    form: int
    reason: str               # 'unresolved' | 'local' | 'this-super'
    expr: str


def _anchor(stmt: str):
    """(form, receiver or None, field, offset of the field token) for the first
    registry anchor in a statement, or None. Qualified spellings first, as before;
    an UNQUALIFIED anchor has receiver None."""
    m = _FORM2.search(stmt)
    if m: return 2, m.group(1), m.group(2), m.start(2)
    m = _FORM2U.search(stmt)
    if m: return 2, None, m.group(1), m.start(1)
    m = _FORM1.search(stmt)
    if m: return 1, m.group(1), m.group(2), m.start(2)
    m = _FORM1U.search(stmt)
    if m: return 1, None, m.group(1), m.start(1)
    return None


def mine_file(path: pathlib.Path, root: pathlib.Path | None = None,
              skipped: list | None = None) -> list[tuple[str, str, Site]]:
    """Registrations in one file as (declaring type, field, Site).

    An unqualified site whose owner cannot be bound is yielded with the declaring type
    UNRESOLVED_OWNER (and recorded in `skipped`); mine() keeps those out of the registry
    table. check-type-values' page-local oracle wants the NAME regardless of owner.
    `skipped` collects Skip rows for the calls that were deliberately not mined."""
    src = path.read_text(errors='replace')
    if '.register(' not in src and 'registerCoreComponentType' not in src:
        return []
    pkg_m = _PKG.search(src)
    pkg = pkg_m.group(1) if pkg_m else ''
    imports = {fq.rsplit('.', 1)[-1]: fq for fq in _IMPORT.findall(src)}
    consts = dict(_CONST.findall(src))
    out = []
    lexical = None
    # Anchors and `.register(` calls are looked for in the MASKED text (comments and string
    # contents blanked, offsets kept), the ids are read from the original. A registration
    # spelled in a `//` comment or a string is not a registration: check-type-values mines
    # docs java fences with this, and a commented-out example there supplied a page-local
    # name (review, 2026-10-15).
    masked = _mask(src)

    for stmt, off in _statement_spans(src):
        mstmt = masked[off:off + len(stmt)]
        if '.register(' not in mstmt:
            continue
        anc = _anchor(mstmt)
        if anc is None:
            continue
        form, recv, fld, at = anc
        spelling = 'qualified' if recv is not None else 'unqualified'
        first_line = src.count('\n', 0, off + at) + 1
        if recv is not None:
            if recv.split('.')[-1] in ('this', 'super'):      # property: an instance receiver
                if skipped is not None:
                    skipped.append(Skip(str(path), first_line, fld, form, 'this-super', recv + '.' + fld))
                continue
            declaring = _resolve_type(recv, imports, pkg)
        else:
            if lexical is None:
                lexical = _Lexical(src, masked)
            how, names = lexical.resolve(off + at, fld)
            if how in ('local', 'instance'):       # property: not the static registry field
                if skipped is not None:
                    skipped.append(Skip(str(path), first_line, fld, form,
                                        'local' if how == 'local' else 'instance-field', fld))
                continue
            if how == 'class':
                declaring = '.'.join(([pkg] if pkg else []) + names)
            else:
                declaring = UNRESOLVED_OWNER
                if skipped is not None:
                    skipped.append(Skip(str(path), first_line, fld, form, 'unresolved', fld))

        for rm in _REGISTER.finditer(mstmt):
            opener = rm.end() - 1
            try:
                body = stmt[opener + 1:_scan(stmt, opener) - 1]
            except (ValueError, AssertionError):
                continue
            args = _split_args(body)
            name, kind, expr, idx = _pick_name(args, consts)
            line = src.count('\n', 0, off + rm.start()) + 1
            out.append((declaring, fld, Site(str(path), line, form, name, expr, kind, idx, off, spelling)))

    if 'registerCoreComponentType' in src:
        for cat, fld, site in _mine_core_components(src, path, imports, pkg, consts, root):
            out.append((cat or UNRESOLVED_CATEGORY, fld, site))
    return out


def _lit(arg: str):
    """The string a literal argument spells, or None. `(Object)"null"` is a literal id
    behind a cast (Schema's id parameter is an Object), and spells `null`."""
    a = arg.strip()
    m = _LITERAL.match(a) or _CAST_LITERAL.match(a)
    return m.group(1) if m else None


def _pick_name(args: list[str], consts: dict[str, str]):
    """The id is the FIRST argument that is a string literal or a resolvable constant —
    NOT necessarily argument one (§1: `register(Class, "Name", codec)` at 18 sites), and
    the search must span every position (§2's false-positive guard:
    `register(Priority.DEFAULT, "Name", …)` is closed, not open)."""
    lits = [i for i, a in enumerate(args) if _lit(a) is not None]
    if len(lits) > 1:
        # Build-26 has none: of 754 register calls, 738 carry exactly one top-level
        # string literal and 16 carry zero. That is luck, not design — with two, the
        # first-literal rule would silently pick the wrong argument. Report instead.
        return None, 'ambiguous', args[lits[0]].strip(), -1
    for i, a in enumerate(args):
        a = a.strip()
        lit = _lit(a)
        if lit is not None:
            return lit, 'literal', a, i
        if a in consts:
            return consts[a], 'constant', a, i
        if a.startswith(('this.', 'super.')) and a.split('.')[-1] in consts:
            return consts[a.split('.')[-1]], 'constant', a, i
    if not args:
        return None, 'runtime', '', -1
    first = args[0].strip()
    # §2 taxonomy: a bare identifier is an id parameter (indirected, knowable by
    # call-graph following); anything else is a runtime value.
    kind = 'indirect' if re.fullmatch(r'\w+', first) else 'runtime'
    return None, kind, first, -1


def core_component_diagnostics(root: pathlib.Path) -> dict:
    """Properties of the category() resolution that hold on build-26 and must.

    Each one fails by substituting a PLAUSIBLE category rather than by admitting
    it cannot resolve, which is the direction `<category-unresolved>` cannot
    protect against — so each is pinned at zero in the fixture rather than left
    as a property nobody measured. Reported, not enforced, here; the fixture
    runner is what turns them into a check.
    """
    visited, multi, extends_foreign, ambiguous = set(), [], [], []
    by_simple = collections.Counter(p.stem for p in root.rglob('*.java'))

    def walk(builder, imports, pkg, seen=frozenset()):
        if builder in seen:
            return
        fq = _resolve_type(builder, imports, pkg)
        f = find_source(fq, root)
        if f is None:
            f = find_source(builder, root)
            if f is not None and by_simple[builder] > 1:
                ambiguous.append(builder)
        if f is None:
            return
        visited.add(str(f))
        body = f.read_text(errors='replace')
        if len(_CATEGORY.findall(body)) > 1:
            multi.append(str(f))
        em = _EXTENDS.search(body)
        if _CATEGORY.search(body):
            return
        if em:
            m_own = re.search(r'\bclass\s+(\w+)', body)
            if m_own and m_own.group(1) != f.stem:
                extends_foreign.append(str(f))
            own_pkg_m = _PKG.search(body)
            walk(em.group(1),
                 {x.rsplit('.', 1)[-1]: x for x in _IMPORT.findall(body)},
                 own_pkg_m.group(1) if own_pkg_m else '',
                 seen | {builder})

    for p in root.rglob('*.java'):
        src = p.read_text(errors='replace')
        if 'registerCoreComponentType' not in src:
            continue
        pkg_m = _PKG.search(src)
        imports = {x.rsplit('.', 1)[-1]: x for x in _IMPORT.findall(src)}
        for m in _FORM3.finditer(src):
            opener = m.end() - 1
            try:
                close = _scan(src, opener)
                args = _split_args(src[opener + 1:close - 1])
            except (ValueError, AssertionError):
                continue
            if len(args) < 2 or _DECLARATION.match(src, close):
                continue
            ref = _CTOR_REF.match(args[1].strip())
            if ref:
                walk(ref.group(1).split('.')[-1], imports,
                     pkg_m.group(1) if pkg_m else '')
    return {'classes_visited': len(visited),
            'files_with_two_category_declarations': len(multi),
            'extends_first_match_not_own_class': len(extends_foreign),
            'builder_simple_names_ambiguous_in_tree': len(ambiguous)}


def mine(root: pathlib.Path, skipped: list | None = None) -> dict[str, Registry]:
    """Every registry in the tree. `skipped`, if given, receives a Skip row for each
    call that was seen and deliberately not mined (see Skip.reason); UNRESOLVED sites
    are among them and are never entered into a registry."""
    regs: dict[str, Registry] = {}
    for p in root.rglob('*.java'):
        for declaring, fld, site in mine_file(p, root, skipped):
            if declaring == UNRESOLVED_OWNER:
                continue
            key = f'{declaring}.{fld}'
            r = regs.setdefault(key, Registry(declaring, fld))
            r.sites.append(site)
    return regs
