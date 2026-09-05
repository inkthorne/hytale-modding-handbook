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
_REGISTER = re.compile(r'\.register\s*\(')
_CONST = re.compile(r'static\s+final\s+String\s+(\w+)\s*=\s*"([^"]*)"\s*;')
_IMPORT = re.compile(r'^import\s+(?:static\s+)?([\w.]+);', re.M)
_PKG = re.compile(r'^package\s+([\w.]+);', re.M)
_LITERAL = re.compile(r'^"([^"]*)"$')
_FORM3 = re.compile(r'registerCoreComponentType\s*\(')
_CTOR_REF = re.compile(r'^([\w.]+)::new$')
_DECLARATION = re.compile(r'\s*(?:throws\s+[\w.,\s]+?)?\{')
_CATEGORY = re.compile(r'Class\s*<\s*([\w.]+)\s*>\s+category\s*\(')
_EXTENDS = re.compile(r'\bclass\s+\w+(?:\s*<[^{]*?>)?\s+extends\s+([\w.]+)')
CORE_COMPONENT_FIELD = 'CORE_COMPONENT_TYPES'
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


@dataclass
class Registry:
    declaring_type: str       # fully qualified where resolvable
    field: str
    sites: list[Site] = field(default_factory=list)

    @property
    def key(self): return f'{self.declaring_type}.{self.field}'
    @property
    def names(self): return sorted({s.name for s in self.sites if s.name})
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
    def statements(self, form=None):
        return len({s.stmt for s in self.sites if form is None or s.form == form})


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

def mine_file(path: pathlib.Path,
              root: pathlib.Path | None = None) -> list[tuple[str, str, Site]]:
    src = path.read_text(errors='replace')
    if '.register(' not in src and 'registerCoreComponentType' not in src:
        return []
    pkg_m = _PKG.search(src)
    pkg = pkg_m.group(1) if pkg_m else ''
    imports = {fq.rsplit('.', 1)[-1]: fq for fq in _IMPORT.findall(src)}
    consts = dict(_CONST.findall(src))
    out = []

    for stmt, off in _statement_spans(src):
        if '.register(' not in stmt:
            continue
        m2, m1 = _FORM2.search(stmt), _FORM1.search(stmt)
        if m2:
            recv, fld, form = m2.group(1), m2.group(2), 2
        elif m1:
            recv, fld, form = m1.group(1), m1.group(2), 1
        else:
            continue
        declaring = _resolve_type(recv, imports, pkg)

        for rm in _REGISTER.finditer(stmt):
            opener = rm.end() - 1
            try:
                body = stmt[opener + 1:_scan(stmt, opener) - 1]
            except (ValueError, AssertionError):
                continue
            args = _split_args(body)
            name, kind, expr, idx = _pick_name(args, consts)
            line = src.count('\n', 0, off + rm.start()) + 1
            out.append((declaring, fld, Site(str(path), line, form, name, expr, kind, idx, off)))

    if 'registerCoreComponentType' in src:
        for cat, fld, site in _mine_core_components(src, path, imports, pkg, consts, root):
            out.append((cat or UNRESOLVED_CATEGORY, fld, site))
    return out


def _pick_name(args: list[str], consts: dict[str, str]):
    """The id is the FIRST argument that is a string literal or a resolvable constant —
    NOT necessarily argument one (§1: `register(Class, "Name", codec)` at 18 sites), and
    the search must span every position (§2's false-positive guard:
    `register(Priority.DEFAULT, "Name", …)` is closed, not open)."""
    lits = [i for i, a in enumerate(args) if _LITERAL.match(a.strip())]
    if len(lits) > 1:
        # Build-26 has none: of 754 register calls, 738 carry exactly one top-level
        # string literal and 16 carry zero. That is luck, not design — with two, the
        # first-literal rule would silently pick the wrong argument. Report instead.
        return None, 'ambiguous', args[lits[0]].strip(), -1
    for i, a in enumerate(args):
        a = a.strip()
        lit = _LITERAL.match(a)
        if lit:
            return lit.group(1), 'literal', a, i
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


def mine(root: pathlib.Path) -> dict[str, Registry]:
    regs: dict[str, Registry] = {}
    for p in root.rglob('*.java'):
        for declaring, fld, site in mine_file(p, root):
            key = f'{declaring}.{fld}'
            r = regs.setdefault(key, Registry(declaring, fld))
            r.sites.append(site)
    return regs
