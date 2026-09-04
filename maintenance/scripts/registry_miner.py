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
"""
from __future__ import annotations
import re, pathlib, sys
from dataclasses import dataclass, field
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from codec_parser import _scan, _split_args

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


def mine_file(path: pathlib.Path) -> list[tuple[str, str, Site]]:
    src = path.read_text(errors='replace')
    if '.register(' not in src:
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


def mine(root: pathlib.Path) -> dict[str, Registry]:
    regs: dict[str, Registry] = {}
    for p in root.rglob('*.java'):
        for declaring, fld, site in mine_file(p):
            key = f'{declaring}.{fld}'
            r = regs.setdefault(key, Registry(declaring, fld))
            r.sites.append(site)
    return regs
