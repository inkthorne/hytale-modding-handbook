#!/usr/bin/env python3
"""
Queued gate 3: every asset id in a docs JSON fence must name an asset of the
family its key refers to.

A fabricated id reads exactly like a real one, and nothing checked them: `check-symbols.py`
skips JSON key paths, `check-type-values.py` reads only `"Type"`, and the fields
check confirms documented-key -> real, never value -> real. The 0.7.2 pass removed
~80 invented interaction ids by hand (d58a7a1) and `drops.md` once carried 31.

THE ONE IDEA: TYPE BY KEY POSITION. An id is only checkable when the gate knows which
key it sits under, and therefore which directory to resolve it against. Resolving
against all of Server/ passes a real-but-wrong-kind id (a sound id under an
`Interactions` key) for the wrong reason, so the gate never does that.

HOW A KEY GETS A FAMILY (derived from the SHIPPED assets, never from the docs):

  * A FAMILY is an asset store: a `setPath("...")` directory the decompiled jar
    registers (`--src`), restricted to the ones that exist under Server/. An id is
    what the store keys on, the FILE STEM (the final extension dropped:
    `.json`, `.particlesystem`, `.particlespawner`). Stores keyed any other way are
    NOT covered (see COVERAGE below).
  * Every string value in every JSON-bodied shipped file is recorded under three
    POSITION CLASSES, arrays being transparent (an array element inherits its key):
        L2  (parent, key)   - the nearest enclosing named key, then the key
        L1  (key,)          - the bare key
        LW  (parent, '*')   - any value under that parent, for maps whose keys
                              are themselves free-form
  * A class is TYPED when it has >= N distinct string values and >= P of them
    resolve in one store. A class reaching P in two stores (block ids defined
    inside Item JSON, `CameraShake` vs `CameraEffect`...) is a TIE and a value
    passes if it resolves in ANY tied store: the ambiguity is the shipped data's,
    and only resolving in none of them is a finding.
  * A doc pair is checked against the UNION of the families of every typed class
    its position matches. Union, not "most specific wins": two classes of one key can
    disagree (`Forks.Next` is a WorldEvent stage, bare `Next` an interaction), and
    letting the specific class overrule would fail a correct page.

    N = 5 distinct values, P = 0.90 of them. PRE-REGISTERED before the first docs
    run (C0): the shipped-only histogram showed no gap to move them to, so neither
    moved. They are constants here and printed on every run.

WHAT IS EXEMPT, each counted by class and none derived from a flag list:

  * shape      the value is not shaped like an id at all (whitespace, `<Id>`, `...`,
               `A|B`, a path, a number, empty). Shipped ids all match [\\w.-]+.
  * generated  a leading `*` (a generated item-state id: `*Base_State_Variant`) and a
               `|Yaw=180` suffix are stripped, and the `_State_` form resolves by its
               base. All three appear as VALUES in shipped assets under typed keys.
  * placeholder  a prefix or quoted id that the PAGE'S OWN prose placeholder note
               names: a paragraph containing the word "placeholder" and a backticked
               `Prefix_` (a prefix) or `"Id"` (an exact id). Only on that page.
  * pack       an id defined by examples/<pack>/Server/**, only on a page that names
               the pack's directory.
  * page-defined  an id whose file stem is named by a path-shaped token on the line
               before a fence, or in the fence's first `//` comment, and only when
               the path's own store is one of the families the position expects.

COVERAGE, said plainly because item ids happening to be Capital_Snake_Case makes recall
look good there and it is not the same everywhere: only string VALUES are checked
(not map KEYS that are ids), only stem-keyed JSON stores, and only positions a shipped
class types. Not covered: Instances (directory-keyed, instance.bson), Prefabs and World
(path-keyed bulk data, not asset stores), Common/ (cited by path, not id), `.lang`
keys, and every key with fewer than N shipped values. `--report-typing` prints what is
typed, what is not and why.

Usage: python3 maintenance/scripts/check-asset-ids.py [--docs DIR] [--assets DIR]
         [--src DIR] [--packs DIR] [--snapshot FILE] [--report-typing] [--dump-typing FILE]
         [--docs-only-prefix] [-v]
Exit: 0 clean, 1 flags, 2 an input is missing, 3 a zero denominator (the gate examined nothing).
"""
from __future__ import annotations
import argparse, collections, json, os, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

N_MIN = 5          # distinct shipped string values a class needs to be typed
P_MIN = 0.90       # fraction of them that must resolve in one store
STORE_EXTS = ('.json', '.particlesystem', '.particlespawner')
# Bulk data that is not an asset store: path-keyed block data and worldgen node files
# (the latter do not even parse as JSON). Named, counted, and excluded from the sweep.
SWEEP_EXCLUDED_TOPS = ('Prefabs', 'World')
ID_SHAPE = re.compile(r'^[A-Za-z0-9_.\-]+$')
NUMERIC = re.compile(r'^[0-9.\-]+$')
SETPATH = re.compile(r'setPath\("([^"]*)"\)')
FENCE = re.compile(r'^([ \t]*)```(\w*)[^\n]*\n(.*?)^[ \t]*```', re.M | re.S)
# A path-shaped token naming an asset file: Server/Item/Items/Foo.json, Item/Items/Foo.json
PATH_TOKEN = re.compile(r'[\w./\-]*?/([\w.\-]+?)\.(?:json|particlesystem|particlespawner)\b')
PATH_FULL = re.compile(r'[\w./\-]+\.(?:json|particlesystem|particlespawner)\b')
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# The two position-evidence widenings (see position_evidence). They were added AFTER the first
# docs run, which flagged 60 pairs without them; WIDEN = False reproduces that first setting so the
# change is always reportable under both.
WIDEN = True
EXEMPT_CLASSES = ('shape', 'position-evidence', 'shipped-use', 'placeholder', 'pack', 'page-defined')


def stem_of(name: str):
    for e in STORE_EXTS:
        if name.endswith(e):
            return name[:-len(e)]
    return None


def norm_value(v: str):
    """(core id, generated?) — strip the generated-state marker and a `|...` modifier."""
    core = v.split('|', 1)[0]
    gen = core.startswith('*')
    if gen:
        core = core[1:]
    return core, gen


# --------------------------------------------------------------------- stores
def mine_store_paths(src: pathlib.Path):
    paths = set()
    for p in src.rglob('*.java'):
        paths.update(SETPATH.findall(p.read_text(errors='replace')))
    return paths


def build_stores(assets: pathlib.Path, declared):
    """-> (stores: path -> set of ids, idx: id -> tuple(store paths), absent: [paths])"""
    server = assets / 'Server'
    present = {sp for sp in declared if (server / sp).is_dir()}
    absent = sorted(set(declared) - present)
    # longest-prefix wins, so a store nested under another is not double-counted
    order = sorted(present, key=lambda s: -len(s))
    stores = {sp: set() for sp in present}
    for sp in present:
        for f in (server / sp).rglob('*'):
            if not f.is_file():
                continue
            st = stem_of(f.name)
            if st is None:
                continue
            owner = next(o for o in order if f.relative_to(server).as_posix().startswith(o + '/'))
            stores[owner].add(st)
    idx = collections.defaultdict(list)
    for sp, ids in stores.items():
        for i in ids:
            idx[i].append(sp)
    return stores, idx, absent


# ------------------------------------------------------------------- sweep
class Sweep:
    def __init__(self):
        self.L1 = collections.defaultdict(set)
        self.L2 = collections.defaultdict(set)
        self.LW = collections.defaultdict(set)
        self.files = 0
        self.excluded = 0
        self.parse_fail = 0
        self.fail_by_top = collections.Counter()
        self.children = collections.defaultdict(set)   # parent -> child keys seen

    def walk(self, o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if len(path) >= 1:
                    self.children[path[-1]].add(k)
                self.walk(v, path + (k,))
        elif isinstance(o, list):
            for v in o:
                self.walk(v, path)
        elif isinstance(o, str) and path:
            self.L1[path[-1:]].add(o)
            if len(path) > 1:
                self.L2[path[-2:]].add(o)
                if IDENT.match(path[-2]):
                    self.LW[(path[-2], '*')].add(o)

    def run(self, assets: pathlib.Path):
        server = assets / 'Server'
        for f in server.rglob('*'):
            if not f.is_file() or stem_of(f.name) is None:
                continue
            top = f.relative_to(server).parts[0]
            if top in SWEEP_EXCLUDED_TOPS:
                self.excluded += 1
                continue
            self.files += 1
            try:
                o = json.loads(f.read_text(encoding='utf-8-sig'))
            except Exception:
                self.parse_fail += 1
                self.fail_by_top[top] += 1
                continue
            self.walk(o, ())


def resolves(value, idx, stores_set=None):
    """Stores in which `value` is an id (after normalisation); () when none."""
    core, gen = norm_value(value)
    hit = idx.get(core, ())
    if not hit and gen and '_State_' in core:
        hit = idx.get(core.split('_State_', 1)[0], ())
    return tuple(hit)


def type_classes(table, idx):
    """class -> (frozenset of stores reaching P, best ratio, N)."""
    out, excluded = {}, collections.Counter()
    ratios = []
    for k, vs in table.items():
        if len(vs) < N_MIN:
            excluded['N<%d' % N_MIN] += 1
            continue
        c = collections.Counter()
        for v in vs:
            for s in set(resolves(v, idx)):
                c[s] += 1
        best = max(c.values()) / len(vs) if c else 0.0
        ratios.append(best)
        tied = frozenset(s for s, n in c.items() if n / len(vs) >= P_MIN)
        if tied:
            out[k] = (tied, best, len(vs))
        else:
            excluded['P<%.2f' % P_MIN] += 1
    return out, excluded, ratios


# ------------------------------------------------- tolerant JSON extraction
TOKEN = re.compile(r'''
    (?P<ws>\s+)
  | (?P<lc>//[^\n]*)
  | (?P<bc>/\*.*?\*/)
  | (?P<str>"(?:\\.|[^"\\])*")
  | (?P<punct>[{}\[\]:,])
  | (?P<atom>[^\s{}\[\]:,"]+)
''', re.X | re.S)


def tolerant_pairs(body: str):
    """Yield (path tuple, string value, offset) for every string VALUE in a JSON-ish
    body, tolerating comments, `...`, and a fragment that starts at `"Key": {`.
    Arrays are transparent: an element inherits the array's key."""
    toks = []
    for m in TOKEN.finditer(body):
        kind = m.lastgroup
        if kind in ('ws', 'lc', 'bc'):
            continue
        toks.append((kind, m.group(), m.start()))
    stack = []        # frames: [kind 'o'|'a', keys tuple, pending key or None]
    out = []

    def unq(s):
        try:
            return json.loads(s)
        except Exception:
            return s[1:-1]

    i = 0
    while i < len(toks):
        kind, text, off = toks[i]
        nxt = toks[i + 1][1] if i + 1 < len(toks) else None
        top = stack[-1] if stack else None
        if kind == 'str':
            if nxt == ':':
                if top is None or top[0] == 'a':
                    # a fragment such as `"Key": {...}` — an implicit object
                    keys = top[1] if top else ()
                    stack.append(['o', keys, None]); top = stack[-1]
                top[2] = unq(text)
                i += 2
                continue
            if top is not None:
                if top[0] == 'o' and top[2] is not None:
                    out.append((top[1] + (top[2],), unq(text), off))
                elif top[0] == 'a':
                    out.append((top[1], unq(text), off))
        elif kind == 'punct':
            if text in '{[':
                if top is None:
                    keys = ()
                elif top[0] == 'o':
                    keys = top[1] + ((top[2],) if top[2] is not None else ())
                else:
                    keys = top[1]
                stack.append(['o' if text == '{' else 'a', keys, None])
            elif text in '}]':
                want = 'o' if text == '}' else 'a'
                for j in range(len(stack) - 1, -1, -1):
                    if stack[j][0] == want:
                        del stack[j:]
                        break
            elif text == ',':
                if top is not None and top[0] == 'o':
                    top[2] = None
        i += 1
    return out


def strict_pairs(o, path=()):
    """The same path semantics as tolerant_pairs, over a json.loads result."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strict_pairs(v, path + (k,))
    elif isinstance(o, list):
        for v in o:
            yield from strict_pairs(v, path)
    elif isinstance(o, str) and path:
        yield path, o


# ------------------------------------------------------------------- docs
def prose_paragraphs(text: str):
    """Paragraphs of text OUTSIDE fences, with blockquote markers removed."""
    stripped = FENCE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    para, out = [], []
    for ln in stripped.split('\n'):
        ln = re.sub(r'^\s*>\s?', '', ln)
        if ln.strip():
            para.append(ln)
        elif para:
            out.append(' '.join(para)); para = []
    if para:
        out.append(' '.join(para))
    return out


def placeholder_note(text: str):
    """(prefixes, exact ids) named by the page's own placeholder paragraphs."""
    prefixes, ids = set(), set()
    for p in prose_paragraphs(text):
        if not re.search(r'\bplaceholders?\b', p, re.I):
            continue
        prefixes.update(re.findall(r'`([A-Za-z0-9]+_)`', p))
        ids.update(re.findall(r'`"([A-Za-z0-9_.\-]+)"`', p))
    return prefixes, ids


def load_packs(packs: pathlib.Path):
    """pack dir name -> set of ids (file stems under <pack>/Server)."""
    out = {}
    if not packs.is_dir():
        return out
    for d in sorted(packs.iterdir()):
        s = d / 'Server'
        if s.is_dir():
            out[d.name] = {stem_of(f.name) for f in s.rglob('*')
                           if f.is_file() and stem_of(f.name)}
    return out


def store_of_path(token: str, stores):
    """The store directory a path-shaped token lives in, longest prefix, or None."""
    t = token
    if t.startswith('Server/'):
        t = t[len('Server/'):]
    best = None
    for sp in stores:
        if (t.startswith(sp + '/')) and (best is None or len(sp) > len(best)):
            best = sp
    return best


def page_defined(text, stores):
    """id -> set of stores, from a path token on the line before a fence or in its
    first `//` comment."""
    defs = collections.defaultdict(set)
    lines = text.split('\n')
    for m in FENCE.finditer(text):
        start_line = text.count('\n', 0, m.start()) # 0-based line of the opening fence
        cands = []
        j = start_line - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        if j >= 0:
            cands.append(lines[j])
        body_lines = m.group(3).split('\n')
        for bl in body_lines[:1]:
            if bl.strip().startswith('//'):
                cands.append(bl)
        for c in cands:
            for pm in PATH_FULL.finditer(c):
                tok = pm.group()
                st = stem_of(tok.rsplit('/', 1)[-1])
                sp = store_of_path(tok, stores)
                if st and sp:
                    defs[st].add(sp)
    return defs


def scan_docs(docs: pathlib.Path):
    """-> list of page records with fence-level pairs and per-page denominators."""
    pages = []
    for d in sorted(docs.glob('*.md')):
        text = d.read_text()
        rec = dict(name=d.name, text=text, pairs=[], n_json=0, n_json_strict=0,
                   n_json_tolerant=0, n_untagged=0, n_untagged_strict=0,
                   n_untagged_jsonish=0, n_other=0, tolerant_pairs=0,
                   strict_disagree=[])
        for m in FENCE.finditer(text):
            lang, body = m.group(2), m.group(3)
            first_line = text.count('\n', 0, m.start(3)) + 1
            strict = None
            try:
                strict = json.loads(body)
            except Exception:
                pass
            if lang == 'json':
                rec['n_json'] += 1
                scan = True
            elif lang == '':
                rec['n_untagged'] += 1
                sig = re.sub(r'(?m)^\s*//[^\n]*\n?', '', body).lstrip()
                has_pairs = bool(re.search(r'"[^"\n]+"\s*:', body))
                if strict is not None:
                    rec['n_untagged_strict'] += 1
                jsonish = bool(sig[:1] in ('{', '[', '"') and has_pairs)
                if jsonish:
                    rec['n_untagged_jsonish'] += 1
                scan = jsonish
            else:
                rec['n_other'] += 1
                scan = False
            if not scan:
                continue
            tp = tolerant_pairs(body)
            if strict is not None:
                if lang == 'json':
                    rec['n_json_strict'] += 1
                sp = collections.Counter(strict_pairs(strict))
                tc = collections.Counter((p, v) for p, v, _ in tp)
                if sp - tc:     # strict saw a pair the tolerant extractor lost
                    rec['strict_disagree'].append((first_line, dict(sp - tc)))
            elif lang == 'json':
                rec['n_json_tolerant'] += 1
            for path, val, off in tp:
                rec['pairs'].append((first_line + body.count('\n', 0, off), path, val))
            rec['tolerant_pairs'] += len(tp)
        pages.append(rec)
    return pages


def lookup_families(path, typed, sweep):
    """Union of the families of every typed class this position matches."""
    fams, via = set(), []
    k = path[-1]
    p = path[-2] if len(path) > 1 else None
    if p is not None and (p, k) in typed['L2']:
        fams |= typed['L2'][(p, k)][0]; via.append('L2')
    if (k,) in typed['L1']:
        fams |= typed['L1'][(k,)][0]; via.append('L1')
    if p is not None and (p, '*') in typed['LW']:
        # LW is for maps with free-form keys. If this exact (parent, key) is a FIELD
        # the shipped assets use and no class types it, it is not an id slot.
        if k not in sweep.children.get(p, ()) or (p, k) in typed['L2'] or (k,) in typed['L1']:
            fams |= typed['LW'][(p, '*')][0]; via.append('LW')
    return fams, via


def position_evidence(path, sweep, idx):
    """What the shipped assets show at THIS position, beyond the typed classes.

    A bare-key class can be a mixture of two codec fields that happen to share a
    name (`Build` is 9 sound ids and 1 particle id: typed to sounds at 0.90 by that
    margin). Two monotone widenings, each read from the shipped assets at the exact
    position and neither able to type a position that was not already typed:
      stores    the stores in which >= P of the values at exactly (parent, key)
                resolve, at ANY N — a path with little data still says where its
                few values live;
      verbatim  the shipped values themselves, from every class the position matches:
                a value the game ships under this key is real by demonstration even
                when it resolves nowhere (`Empty`, a built-in; `Full`; the
                `Melee`/`Ranged` tag values under `Attack`)."""
    k = path[-1]
    p = path[-2] if len(path) > 1 else None
    stores, verb = set(), set()
    if p is not None and (p, k) in sweep.L2:
        vs = sweep.L2[(p, k)]
        c = collections.Counter(s for v in vs for s in set(resolves(v, idx)))
        stores |= {s for s, n in c.items() if n / len(vs) >= P_MIN}
        verb |= vs
    verb |= sweep.L1.get((k,), set())
    if p is not None:
        verb |= sweep.LW.get((p, '*'), set())
    return stores, verb


# ---------------------------------------------------------------- evaluation
class Ctx:
    """Everything derived from the shipped assets (reusable across doc trees)."""


def build_context(assets: pathlib.Path, src: pathlib.Path) -> Ctx:
    c = Ctx()
    c.declared = mine_store_paths(src)
    c.stores, c.idx, c.absent = build_stores(assets, c.declared)
    c.sweep = Sweep()
    c.sweep.run(assets)
    c.typed, c.excl, c.ratios = {}, {}, {}
    for lvl, table in (('L1', c.sweep.L1), ('L2', c.sweep.L2), ('LW', c.sweep.LW)):
        c.typed[lvl], c.excl[lvl], c.ratios[lvl] = type_classes(table, c.idx)
    c.covered = set()
    for lvl in c.typed:
        for fams, _, _ in c.typed[lvl].values():
            c.covered |= fams
    return c


def evaluate(pages, ctx: Ctx, packs):
    """One verdict per extracted pair. verdict is one of 'untyped', 'resolved',
    'failed' or an exemption class in EXEMPT_CLASSES. Order of the checks is the
    order of the cheapest-and-most-structural first; an exemption is only reached
    for a value that did NOT resolve, so an exemption count is a count of things it
    actually excused."""
    stores_set = set(ctx.stores)
    out = []
    for r in pages:
        text = r['text']
        pre_prefixes, pre_ids = placeholder_note(text)
        pdef = page_defined(text, stores_set)
        pack_ids = {}
        for pk, ids in packs.items():
            if pk in text:
                for i in ids:
                    pack_ids[i] = pk
        for line, path, val in r['pairs']:
            rec = dict(page=r['name'], line=line, path=path, val=val, fams=(), hit=(), verdict=None)
            out.append(rec)
            fams, via = lookup_families(path, ctx.typed, ctx.sweep)
            rec['fams'] = tuple(sorted(fams))
            if not fams:
                rec['verdict'] = 'untyped'
                continue
            core, gen = norm_value(val)
            if not core or not ID_SHAPE.match(core) or NUMERIC.match(core):
                rec['verdict'] = 'shape'
                continue
            hit = resolves(val, ctx.idx)
            rec['hit'] = tuple(sorted(set(hit)))
            if set(hit) & fams:
                rec['verdict'] = 'resolved'
                continue
            ev_stores, verb = position_evidence(path, ctx.sweep, ctx.idx) if WIDEN else (set(), set())
            if set(hit) & ev_stores:
                rec['verdict'] = 'position-evidence'
            elif val in verb or core in verb:
                rec['verdict'] = 'shipped-use'
            elif val in pre_ids or core in pre_ids or any(core.startswith(p) for p in pre_prefixes):
                rec['verdict'] = 'placeholder'
            elif core in pack_ids:
                rec['verdict'] = 'pack'
            elif core in pdef and (pdef[core] & fams):
                rec['verdict'] = 'page-defined'
            else:
                rec['verdict'] = 'failed'
    return out


# -------------------------------------------------------------------- main
def load_snapshot(path: pathlib.Path):
    out = {}
    for ln in path.read_text().splitlines():
        if not ln or ln.startswith('#'):
            continue
        cls, _, fams = ln.partition('\t')
        out[cls] = fams
    return out


def fmt_class(level, key):
    return level + ' ' + '.'.join(key)


def table_lines(typed):
    rows = []
    for lvl in ('L1', 'L2', 'LW'):
        for k, (fams, ratio, n) in typed[lvl].items():
            rows.append((fmt_class(lvl, k), ','.join(sorted(fams))))
    return sorted(rows)


def main():
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', default=str(REPO / 'docs'))
    ap.add_argument('--assets', default=os.path.expanduser('~/.cache/hytale-assets'))
    ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
    ap.add_argument('--packs', default=str(REPO / 'examples'))
    ap.add_argument('--snapshot', default=str(REPO / 'maintenance' / 'baseline' / 'AssetIdTyping.txt'))
    ap.add_argument('--report-typing', action='store_true',
                    help='print the C1 report (histogram, typed classes, exclusions) and stop; '
                         'reads no docs')
    ap.add_argument('--dump-typing', metavar='FILE',
                    help='write the derived key->family table to FILE (the snapshot format)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    docs, assets, src = pathlib.Path(a.docs), pathlib.Path(a.assets), pathlib.Path(a.src)

    for label, p, how in (('asset cache', assets / 'Server', 'build it with the unzip command in CLAUDE.md'),
                          ('decompiled source', src, 'build it with maintenance/scripts/build-jar-cache.sh')):
        if not p.exists():
            print(f"  SKIP  {label} not found at {p} — {how}")
            return 2
    if not a.report_typing and a.dump_typing is None and not docs.exists():
        print(f"  SKIP  docs corpus not found at {docs} — check the --docs path")
        return 2

    # ---- the asset sweep ------------------------------------------------
    ctx = build_context(assets, src)
    declared, stores, idx, absent = ctx.declared, ctx.stores, ctx.idx, ctx.absent
    sweep, typed, excl, ratios = ctx.sweep, ctx.typed, ctx.excl, ctx.ratios
    t_sweep = time.time() - t0

    n_stores_present = len(stores)
    n_ids = len(idx)
    if not declared or not stores or not n_ids or not sweep.files or not any(typed.values()):
        print(f"  FAIL  an asset-side denominator is zero: {len(declared)} declared store(s), "
              f"{n_stores_present} present, {n_ids} id(s), {sweep.files} file(s) swept, "
              f"{sum(len(v) for v in typed.values())} typed class(es)")
        return 3

    covered = ctx.covered
    ties = sum(1 for lvl in typed for fams, _, _ in typed[lvl].values() if len(fams) > 1)

    print(f"  INFO  asset sweep: {sweep.files} JSON-bodied file(s) swept under Server/ "
          f"(+{sweep.excluded} excluded as bulk data: {', '.join(SWEEP_EXCLUDED_TOPS)}); "
          f"{sweep.parse_fail} failed to parse; {len(declared)} store(s) declared in the jar, "
          f"{n_stores_present} present with ids ({len(absent)} absent from this build), {n_ids} distinct id(s)")
    print(f"  INFO  typing (N>={N_MIN} distinct values, P>={P_MIN:.2f} in one store): "
          f"L2 {len(typed['L2'])} of {len(sweep.L2)} classes, L1 {len(typed['L1'])} of {len(sweep.L1)}, "
          f"LW {len(typed['LW'])} of {len(sweep.LW)}; {len(covered)} of {n_stores_present} store(s) "
          f"are the target of at least one typed class; {ties} tied class(es)")

    if a.dump_typing:
        header = (f"# Asset-id typing table: position class -> store(s) reaching P>={P_MIN} over N>={N_MIN} "
                  f"distinct shipped values.\n"
                  f"# Derived by check-asset-ids.py from the shipped assets; a PRE-REGISTRATION SNAPSHOT of the\n"
                  f"# typing taken before the docs were first resolved against it. The gate diffs its live table\n"
                  f"# against this file and reports drift as INFO; regenerate with --dump-typing after a game\n"
                  f"# update, once the docs have been re-verified. Not otherwise an input.\n"
                  f"# {len(typed['L1'])} L1 / {len(typed['L2'])} L2 / {len(typed['LW'])} LW class(es).\n")
        pathlib.Path(a.dump_typing).write_text(header + ''.join(f"{c}\t{f}\n" for c, f in table_lines(typed)))
        print(f"  INFO  typing table written to {a.dump_typing}")

    if a.report_typing:
        report_typing(sweep, typed, excl, ratios, stores, covered)
        return 0

    # ---- typing drift vs the pre-registered snapshot --------------------
    snap = pathlib.Path(a.snapshot)
    if snap.exists():
        old = load_snapshot(snap)
        new = dict(table_lines(typed))
        add = sorted(set(new) - set(old))
        rem = sorted(set(old) - set(new))
        chg = sorted(c for c in set(new) & set(old) if new[c] != old[c])
        print(f"  INFO  typing drift vs {snap.name}: {len(add)} class(es) added, {len(rem)} removed, "
              f"{len(chg)} retargeted ({len(old)} in the snapshot)")
    else:
        print(f"  INFO  no typing snapshot at {snap} — drift not measured")

    # ---- the docs scan --------------------------------------------------
    t1 = time.time()
    pages = scan_docs(docs)
    packs = load_packs(pathlib.Path(a.packs))
    n_pages = len(pages)
    tot = collections.Counter()
    for r in pages:
        for k in ('n_json', 'n_json_strict', 'n_json_tolerant', 'n_untagged', 'n_untagged_strict',
                  'n_untagged_jsonish', 'n_other', 'tolerant_pairs'):
            tot[k] += r[k]
    bad_extract = [(r['name'], ln, d) for r in pages for ln, d in r['strict_disagree']]

    records = evaluate(pages, ctx, packs)
    verdicts = collections.Counter(r['verdict'] for r in records)
    exempt = collections.Counter({k: verdicts[k] for k in EXEMPT_CLASSES})
    checked = collections.Counter(resolved=verdicts['resolved'], failed=verdicts['failed'])
    untyped_pairs = verdicts['untyped']
    typed_pairs = len(records) - untyped_pairs
    fam_checked = collections.Counter(f for r in records if r['verdict'] == 'resolved'
                                      for f in set(r['fams']) & set(r['hit']))
    flags = [(r['page'], r['line'], r['path'], r['val'], list(r['fams']),
              ('exists only as ' + ', '.join(r['hit'])) if r['hit'] else 'absent from every store')
             for r in records if r['verdict'] == 'failed']

    t_docs = time.time() - t1
    n_pairs = tot['tolerant_pairs']
    if n_pages == 0 or tot['n_json'] == 0 or n_pairs == 0 or typed_pairs == 0:
        print(f"  FAIL  scanned nothing: {n_pages} page(s), {tot['n_json']} json fence(s), "
              f"{n_pairs} pair(s), {typed_pairs} typed pair(s)")
        return 3

    print(f"  INFO  docs scan: {n_pages} page(s); {tot['n_json']} ```json fence(s) "
          f"({tot['n_json_strict']} strict-parse, {tot['n_json_tolerant']} unparseable and read tolerantly); "
          f"{tot['n_untagged']} untagged fence(s), of which {tot['n_untagged_strict']} parse as JSON and "
          f"{tot['n_untagged_jsonish']} hold JSON pairs (scanned); {tot['n_other']} other-language fence(s) not scanned")
    n_exempt = sum(exempt.values())
    print(f"  INFO  pairs: {n_pairs} string value(s) extracted, {typed_pairs} at a typed position "
          f"({untyped_pairs} untyped, not checkable); of the typed: {checked['resolved']} resolved, "
          f"{n_exempt} exempt (" + ', '.join(f"{k} {exempt[k]}" for k in EXEMPT_CLASSES)
          + f"), {checked['failed']} failed; resolved in {len(fam_checked)} distinct store(s)")
    print(f"  INFO  timing: asset sweep {t_sweep:.1f}s, docs scan {t_docs:.1f}s")
    if typed_pairs != checked['resolved'] + n_exempt + checked['failed']:
        print("  FAIL  the typed-pair tally does not add up")
        return 3

    rc = 0
    if bad_extract:
        for name, ln, d in bad_extract:
            print(f"  FAIL  {name}:{ln}: the tolerant extractor lost pair(s) json.loads sees: {d}")
        rc = 3
    for name, line, path, val, fams, kind in flags:
        print(f"  FLAG  {name}:{line}: \"{'.'.join(path)}\": \"{val}\" is not an id in "
              f"{'/'.join(fams)} ({kind})")
    if flags:
        rc = rc or 1
    if rc == 0:
        print(f"  PASS  all {checked['resolved']} checked asset id(s) resolve in the family their key refers to")
    return rc


def report_typing(sweep, typed, excl, ratios, stores, covered):
    """The C1 report: histogram of per-key resolution ratios, what is typed, what is not."""
    for lvl, label in (('L1', 'bare key (L1)'), ('L2', 'parent.key (L2)'), ('LW', 'parent.* (LW)')):
        rs = ratios[lvl]
        h = collections.Counter(min(int(r * 10), 10) for r in rs)
        print(f"\n  {label}: best-family resolution ratio over {len(rs)} class(es) with N>={N_MIN}")
        for b in range(10, -1, -1):
            lo = b / 10
            name = '1.0' if b == 10 else f'{lo:.1f}-{lo + .099:.2f}'
            print(f"    {name:>9} {h[b]:5d} {'#' * min(h[b], 60)}")
        print(f"    typed {len(typed[lvl])}; excluded: " + ', '.join(f"{k}: {v}" for k, v in sorted(excl[lvl].items())))
    # collisions: a key typed to different families at different levels
    col = []
    for (p, k), (f2, _, _) in typed['L2'].items():
        f1 = typed['L1'].get((k,))
        if f1 and not (f1[0] & f2):
            col.append(((p, k), sorted(f2), sorted(f1[0])))
    print(f"\n  collisions (an L2 class typed to a family the bare key is not): {len(col)}")
    for c in col:
        print(f"    {'.'.join(c[0])} -> {c[1]}   bare {c[0][1]} -> {c[2]}")
    only_l2 = [k for k in typed['L2'] if (k[1],) not in typed['L1']]
    print(f"  keys typed ONLY by path (the bare key is untyped): {len({k[1] for k in only_l2})} key(s) in {len(only_l2)} L2 class(es)")
    ties = [(lvl, k, sorted(v[0])) for lvl in typed for k, v in typed[lvl].items() if len(v[0]) > 1]
    print(f"  ties (a class reaching P in two or more stores): {len(ties)}")
    for t in ties:
        print(f"    {t[0]} {'.'.join(t[1])} -> {t[2]}")
    print(f"\n  families covered: {len(covered)} of {len(stores)} present store(s)")
    print("    covered:     " + ', '.join(sorted(covered)))
    print("    not covered: " + ', '.join(sorted(set(stores) - covered)))
    if sweep.fail_by_top:
        print("  parse failures by top-level directory: " + ', '.join(f"{k} {v}" for k, v in sweep.fail_by_top.items()))


if __name__ == '__main__':
    sys.exit(main())
