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
        LN  (parent, '#')   - a STRING held directly at a child of `parent` whose KEY PARSES
                              AS A NUMBER (`"Next": {"1.0": "Heavy_Swing_1"}`, the shape of a
                              Float2ObjectMapCodec map, which ChargingInteraction.Next is and
                              nothing else in the jar is). Selected by that property, never by a
                              list of keys; a string that is a field of an inline object held at
                              the child (`"1.0": {"Interactions": ...}`) has a non-numeric last
                              key and is not in the class, nor does an object count toward N or P.
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
keys, and every key with fewer than N shipped values (so a fixed field shipped once, such as
MovementCondition's `ForwardLeft`, and an id-valued child of a free-form map the assets only
ever fill with inline objects, such as Chaining's `Flags`, stay untyped). `--report-typing`
prints what is typed, what is not and why.

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
# The same, but a fence may sit inside a blockquote (`> ```json`): 8 of the handbook's fences do, and an
# anchor that allows only spaces before the backticks neither scanned nor COUNTED them.
QFENCE = re.compile(r'^([ \t]*(?:>[ \t]?)*)```(\w*)[^\n]*\n(.*?)^[ \t]*(?:>[ \t]?)*```', re.M | re.S)
BQ = re.compile(r'^[ \t]*(?:>[ \t]?)*')


def fences(text: str):
    """(lang, body, body_start, open_start, quoted) per fence; a blockquoted fence's body has its
    `> ` markers stripped line by line, newlines kept so line numbers still add up."""
    for m in QFENCE.finditer(text):
        quoted = '>' in m.group(1)
        body = m.group(3)
        if quoted:
            body = '\n'.join(BQ.sub('', ln) for ln in body.split('\n'))
        yield m.group(2), body, m.start(3), m.start(), quoted
# A path-shaped token naming an asset file: Server/Item/Items/Foo.json, Item/Items/Foo.json
PATH_TOKEN = re.compile(r'[\w./\-]*?/([\w.\-]+?)\.(?:json|particlesystem|particlespawner)\b')
PATH_FULL = re.compile(r'[\w./\-]+\.(?:json|particlesystem|particlespawner)\b')
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# Settings added AFTER the first docs run, each a response to a measured false positive, each
# switchable so every result is reportable under the setting before it (measure-asset-id-recall.py
# prints them all):
#   WIDEN          a value the shipped assets themselves put under the key passes ("verbatim"):
#                  the built-in `Empty`, `Full`, tag names under `Attack`. 60 flags became 44.
#   VERBATIM_STRICT  ...but a value taken from a BARE-KEY (or parent.*) class counts only if it
#                  resolves in NO store at all (a sentinel). An id of another store shipped under
#                  the key somewhere (a stage id under Forks.Next) is the wrong kind everywhere
#                  else, and passed `"Next": "Hunt_Breach_Stage2"` until the review found it.
#                  Values shipped at exactly (parent, key) stay verbatim at any kind.
#   EXACT_WINS     where the shipped assets show THIS exact (parent, key) and its values do not
#                  resolve in the bare-key class's family, the bare key does not speak there. A
#                  bare key can be a mixture of two codec fields (`Attack` is root-interaction ids
#                  under Actions/Modify and the tag names Block/Melee/Ranged under Tags; `Build` is
#                  9 sounds and 1 particle). The review found `Tags.Attack: Uninterruptable` flagged.
#   PARENT_K       a bare-key class types a position under a parent the shipped assets never show
#                  the key under only if the key was seen under at least this many distinct parents.
#                  One parent is one codec context (`Weapons`: 55 NPC-inventory item ids, all under
#                  `Modify`, and Family tag names on an item ability). The value 3 is a JUDGMENT,
#                  not a measurement: K = 1..4 give identical flag sets on every docs revision
#                  measured (37425a6, a83ffd0, HEAD), so the data cannot choose. The fixture pins
#                  2 vs 3 (key `Twin`, two parents) so a change to it is a decision, not drift.
WIDEN = True
VERBATIM_STRICT = True
EXACT_WINS = True
# ...and "holding something else" means FEWER THAN HALF of the values shipped at that exact pair resolve in
# the class's family. Not "no store reaches P there": Breaking.DropList is 58/71 drop lists (82%) and
# Soft.DropList 222/248 (89.5%), mixed but plainly drop lists, and treating them as contradicted made 3 live
# pairs unchecked (found by the verify pass of b4365d8). Tags.Attack (Block/Melee/Ranged) has 0 of 3.
EXACT_SHARE = 0.5
PARENT_K = 3
# NUMERIC_CHILD (the LN class above) was added by acceptance 6. It exists because the LW class cannot speak
# for these keys: `k not in sweep.children[p]` stops a parent.* class from typing a key the shipped assets
# show as a child of that parent (a FIELD, not a free-form map key), and every distinct numeric key of a
# Charging `Next` is such a child (41 distinct numeric keys; only `0` reaches the 5 values L2 needs). The numeric property
# selects the map child directly, so the LN class does not consult that guard; it consults EXACT_WINS /
# EXACT_SHARE (a (parent, key) the assets show holding something else is not spoken for) and VERBATIM_STRICT
# (a sentinel the assets ship there passes) exactly as the other classes do. PARENT_K does not apply: LN is
# keyed by its parent, so there is no bare key to be asked how many contexts it was seen in.
NUMERIC_CHILD = True
NUMKEY = re.compile(r'^[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$')   # what Float.parseFloat accepts, less NaN/Infinity/hex
EXEMPT_CLASSES = ('shape', 'shipped-use', 'shipped-excerpt', 'placeholder', 'pack', 'page-defined')


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
        self.LN = collections.defaultdict(set)
        self.files = 0
        self.excluded = 0
        self.parse_fail = 0
        self.fail_by_top = collections.Counter()
        self.children = collections.defaultdict(set)   # parent -> child keys seen
        self.parents = collections.defaultdict(set)    # key -> nearest named parents it carries a string under
        self.relpaths = []                             # swept files, relative to Server/

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
            self.parents[path[-1]].add(path[-2] if len(path) > 1 else None)
            self.L1[path[-1:]].add(o)
            if len(path) > 1:
                self.L2[path[-2:]].add(o)
                if IDENT.match(path[-2]):
                    self.LW[(path[-2], '*')].add(o)
                # a string at a numeric-keyed child of a NAMED map: the parent must be a name, not itself a
                # number (a numeric key inside an inline object held at a numeric child is not a map M)
                if NUMKEY.match(path[-1]) and IDENT.match(path[-2]):
                    self.LN[(path[-2], '#')].add(o)

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
            self.relpaths.append(f.relative_to(server).as_posix())
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
LIST_OR_TABLE = re.compile(r'^\s*(?:\||[-*+]\s|\d+[.)]\s)')


def prose_paragraphs(text: str):
    """(first line number, text) of every PROSE paragraph outside fences, blockquote markers
    removed. A table row or a list item is not a paragraph: it ends the one before it and is
    dropped, with its continuation lines. A symptoms list that mentions a UI "placeholder" is
    not a note about ids."""
    stripped = QFENCE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    para, out, start, in_list = [], [], 0, False
    for n, ln in enumerate(stripped.split('\n'), 1):
        ln = re.sub(r'^\s*>\s?', '', ln)
        if not ln.strip():
            if para:
                out.append((start, ' '.join(para))); para = []
            in_list = False
        elif LIST_OR_TABLE.match(ln):
            if para:
                out.append((start, ' '.join(para))); para = []
            in_list = True
        elif in_list:
            continue
        else:
            if not para:
                start = n
            para.append(ln)
    if para:
        out.append((start, ' '.join(para)))
    return out


def placeholder_note(text: str):
    """(prefixes, exact ids) -> each with the line of the paragraph that declares it, from the
    page's own placeholder PARAGRAPHS (see prose_paragraphs)."""
    prefixes, ids = {}, {}
    for n, p in prose_paragraphs(text):
        if not re.search(r'\bplaceholders?\b', p, re.I):
            continue
        for x in re.findall(r'`([A-Za-z0-9]+_)`', p):
            prefixes.setdefault(x, n)
        for x in re.findall(r'`"([A-Za-z0-9_.\-]+)"`', p):
            ids.setdefault(x, n)
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


def fence_claims(text):
    """Per fence (same order as fences()): (nearest non-blank line before it, the two nearest, first
    line of the body if it is a `//` comment), as raw text lines - where a fence says which file it is."""
    out = []
    lines = text.split('\n')
    for lang, body, bstart, ostart, quoted in fences(text):
        start_line = text.count('\n', 0, ostart)      # 0-based line of the opening fence
        prev = []
        j = start_line - 1
        while j >= 0 and len(prev) < 2:
            if BQ.sub('', lines[j]).strip():
                prev.append(lines[j])
            j -= 1
        first = body.split('\n')[0]
        out.append((lang, prev, first if first.strip().startswith('//') else None))
    return out


def page_defined(text, stores):
    """id -> set of stores, from a path token on the line before a JSON (or untagged) fence or in its
    first `//` comment. Not a path anywhere else on the page, and not one before a java fence."""
    defs = collections.defaultdict(set)
    for lang, prev, comment in fence_claims(text):
        if lang not in ('json', ''):
            continue
        for c in (prev[:1] + ([comment] if comment else [])):
            for pm in PATH_FULL.finditer(c):
                tok = pm.group()
                st = stem_of(tok.rsplit('/', 1)[-1])
                sp = store_of_path(tok, stores)
                if st and sp:
                    defs[st].add(sp)
    return defs


def excerpt_pairs(claims, sweep, assets):
    """Per fence index: the (path, value) string pairs of every REAL shipped file its introduction
    names (the two lines before it, or its first comment). A path that matches no swept file, or a
    file that does not parse, names nothing."""
    by_base = sweep.__dict__.get('_by_base')
    if by_base is None:
        by_base = collections.defaultdict(list)
        for rp in sweep.relpaths:
            by_base[rp.rsplit('/', 1)[-1]].append(rp)
        sweep._by_base = by_base
    parsed = sweep.__dict__.setdefault('_parsed', {})
    out = {}
    for i, (lang, prev, comment) in enumerate(claims):
        if lang not in ('json', ''):
            continue
        pairs = []
        for c in (prev + ([comment] if comment else [])):
            for pm in PATH_FULL.finditer(c):
                tok = pm.group()
                tok = tok[len('Server/'):] if tok.startswith('Server/') else tok
                for rp in by_base.get(tok.rsplit('/', 1)[-1], ()):
                    if rp == tok or rp.endswith('/' + tok):
                        if rp not in parsed:
                            try:
                                parsed[rp] = list(strict_pairs(json.loads(
                                    (assets / 'Server' / rp).read_text(encoding='utf-8-sig'))))
                            except Exception:
                                parsed[rp] = []
                        pairs += parsed[rp]
        if pairs:
            out[i] = pairs
    return out


def excerpt_holds(path, val, pairs):
    """True when the named file ships `val` at this position: the same string under the same key path,
    one path being a suffix of the other (a fence quotes a fragment, so it may lose its parents).
    The claim a fence makes by naming a file is about the PAIR, so the sentence that names it does not
    matter: a path in an unrelated sentence excuses nothing the file does not itself ship there."""
    for fp, v in pairs:
        if v == val and (fp[-len(path):] == path or path[-len(fp):] == fp):
            return True
    return False


def scan_docs(docs: pathlib.Path):
    """-> list of page records with fence-level pairs and per-page denominators."""
    pages = []
    for d in sorted(docs.glob('*.md')):
        text = d.read_text()
        rec = dict(name=d.name, text=text, pairs=[], n_json=0, n_json_strict=0,
                   n_json_tolerant=0, n_untagged=0, n_untagged_strict=0,
                   n_untagged_jsonish=0, n_untagged_fragment=0, n_other=0, tolerant_pairs=0,
                   n_quoted=0, n_quoted_json=0, recovered_pairs=0, strict_disagree=[])
        for fi, (lang, body, bstart, ostart, quoted) in enumerate(fences(text)):
            first_line = text.count('\n', 0, bstart) + 1
            rec['n_quoted'] += quoted
            rec['n_quoted_json'] += quoted and lang == 'json'
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
                elif has_pairs:
                    rec['n_untagged_fragment'] += 1      # a quoted "Key": inside a tree or a .lang sample
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
                rec['pairs'].append((first_line + body.count('\n', 0, off), path, val, strict is None, fi))
            rec['tolerant_pairs'] += len(tp)
            if strict is None:
                rec['recovered_pairs'] += len(tp)
        pages.append(rec)
    return pages


def exact_share(sweep, idx, p, k, fams):
    """The fraction of the shipped values at exactly (parent, key) that resolve in `fams`; None when
    the assets never show that pair."""
    if p is None or (p, k) not in sweep.L2:
        return None
    cache = sweep.__dict__.setdefault('_share', {})
    key = (p, k, frozenset(fams))
    if key not in cache:
        vs = sweep.L2[(p, k)]
        cache[key] = sum(1 for v in vs if set(resolves(v, idx)) & set(fams)) / len(vs)
    return cache[key]


def lookup_families(path, typed, sweep, idx):
    """Union of the families of every typed class this position matches, minus a bare-key or
    parent.* class that the exact (parent, key) contradicts (EXACT_WINS)."""
    fams, via = set(), []
    k = path[-1]
    p = path[-2] if len(path) > 1 else None
    if p is not None and (p, k) in typed['L2']:
        fams |= typed['L2'][(p, k)][0]; via.append('L2')
    if (k,) in typed['L1'] and (p in sweep.parents.get(k, ()) or len(sweep.parents.get(k, ())) >= PARENT_K):
        l1 = typed['L1'][(k,)][0]
        sh = exact_share(sweep, idx, p, k, l1)
        if EXACT_WINS and sh is not None and sh < EXACT_SHARE:
            pass        # the shipped assets show this (parent, key) holding something else
        else:
            fams |= l1; via.append('L1')
    if NUMERIC_CHILD and p is not None and NUMKEY.match(k) and (p, '#') in typed['LN']:
        # a numeric-keyed child of a map: selected by the key's PROPERTY, so the children guard below
        # (which separates fields from free-form keys by looking the key up) is not consulted
        ln = typed['LN'][(p, '#')][0]
        sh = exact_share(sweep, idx, p, k, ln)
        if not (EXACT_WINS and sh is not None and sh < EXACT_SHARE):
            fams |= ln; via.append('LN')
    if p is not None and (p, '*') in typed['LW']:
        # LW is for maps with free-form keys. If this exact (parent, key) is a FIELD
        # the shipped assets use and no class types it, it is not an id slot.
        lw = typed['LW'][(p, '*')][0]
        sh = exact_share(sweep, idx, p, k, lw)
        if EXACT_WINS and sh is not None and sh < EXACT_SHARE:
            pass        # this (parent, key) is a field of its own that the parent.* class does not describe
        elif k not in sweep.children.get(p, ()) or (p, k) in typed['L2'] or (k,) in typed['L1']:
            fams |= lw; via.append('LW')
    return fams, via


def shipped_values(path, sweep, idx, via):
    """Values the shipped assets themselves put at this position (verbatim). At exactly
    (parent, key): any value. From a bare-key or parent.* class: only a value that resolves in
    NO store (a sentinel such as `Empty`) - a real id of another store is the wrong kind
    everywhere but where it ships (VERBATIM_STRICT)."""
    k = path[-1]
    p = path[-2] if len(path) > 1 else None
    verb = set(sweep.L2.get((p, k), ())) if p is not None else set()
    for lvl, tbl, key in (('L1', sweep.L1, (k,)), ('LW', sweep.LW, (p, '*')), ('LN', sweep.LN, (p, '#'))):
        if lvl in via:
            vs = tbl.get(key, set())
            verb |= {v for v in vs if not resolves(v, idx)} if VERBATIM_STRICT else vs
    return verb


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
    for lvl, table in (('L1', c.sweep.L1), ('L2', c.sweep.L2), ('LW', c.sweep.LW), ('LN', c.sweep.LN)):
        c.typed[lvl], c.excl[lvl], c.ratios[lvl] = type_classes(table, c.idx)
    c.covered = set()
    for lvl in c.typed:
        for fams, _, _ in c.typed[lvl].values():
            c.covered |= fams
    return c


def evaluate(pages, ctx: Ctx, packs, assets=None):
    """One verdict per extracted pair. verdict is one of 'untyped', 'resolved',
    'failed' or an exemption class in EXEMPT_CLASSES. An exemption is only reached for a value that
    did NOT resolve, so an exemption count is a count of things it actually excused. A placeholder
    note that declares a prefix some shipped id starts with, or an id that resolves, is itself a
    record (verdict 'bad-placeholder') and excuses nothing."""
    stores_set = set(ctx.stores)
    out = []
    for r in pages:
        text = r['text']
        decl_prefixes, decl_ids = placeholder_note(text)
        pre_prefixes, pre_ids = {}, {}
        for x, n in decl_prefixes.items():
            hit = next((i for i in ctx.idx if i.startswith(x)), None)
            if hit:
                out.append(dict(page=r['name'], line=n, path=('<placeholder note>',), val=x, fams=(),
                                hit=(hit,), verdict='bad-placeholder'))
            else:
                pre_prefixes[x] = n
        for x, n in decl_ids.items():
            if resolves(x, ctx.idx):
                out.append(dict(page=r['name'], line=n, path=('<placeholder note>',), val=x, fams=(),
                                hit=(x,), verdict='bad-placeholder'))
            else:
                pre_ids[x] = n
        pdef = page_defined(text, stores_set)
        excerpts = excerpt_pairs(fence_claims(text), ctx.sweep, assets) if assets is not None else {}
        pack_ids = {}
        for pk, ids in packs.items():
            if pk in text:
                for i in ids:
                    pack_ids[i] = pk
        for line, path, val, tol, fi in r['pairs']:
            rec = dict(page=r['name'], line=line, path=path, val=val, fams=(), hit=(), verdict=None,
                       tolerant=tol)
            out.append(rec)
            fams, via = lookup_families(path, ctx.typed, ctx.sweep, ctx.idx)
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
            verb = shipped_values(path, ctx.sweep, ctx.idx, via) if WIDEN else set()
            if val in verb or core in verb:
                rec['verdict'] = 'shipped-use'
            elif excerpt_holds(path, val, excerpts.get(fi, ())):
                rec['verdict'] = 'shipped-excerpt'
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
    for lvl in ('L1', 'L2', 'LW', 'LN'):
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
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='also print one PAIR line per extracted pair with its verdict')
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
          f"LW {len(typed['LW'])} of {len(sweep.LW)}, LN {len(typed['LN'])} of {len(sweep.LN)}; {len(covered)} of {n_stores_present} store(s) "
          f"are the target of at least one typed class; {ties} tied class(es)")

    if a.dump_typing:
        header = (f"# Asset-id typing table: position class -> store(s) reaching P>={P_MIN} over N>={N_MIN} "
                  f"distinct shipped values.\n"
                  f"# Derived by check-asset-ids.py from the shipped assets; a PRE-REGISTRATION SNAPSHOT of the\n"
                  f"# typing taken before the docs were first resolved against it. The gate diffs its live table\n"
                  f"# against this file and reports drift as INFO; regenerate with --dump-typing after a game\n"
                  f"# update, once the docs have been re-verified. Not otherwise an input.\n"
                  f"# {len(typed['L1'])} L1 / {len(typed['L2'])} L2 / {len(typed['LW'])} LW / {len(typed['LN'])} LN class(es).\n")
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
                  'n_untagged_jsonish', 'n_untagged_fragment', 'n_other', 'tolerant_pairs',
                  'n_quoted', 'n_quoted_json', 'recovered_pairs'):
            tot[k] += r[k]
    bad_extract = [(r['name'], ln, d) for r in pages for ln, d in r['strict_disagree']]

    all_records = evaluate(pages, ctx, packs, assets)
    decl_flags = [r for r in all_records if r['verdict'] == 'bad-placeholder']
    records = [r for r in all_records if r['verdict'] != 'bad-placeholder']
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
    rec_typed = sum(1 for r in records if r['tolerant'] and r['verdict'] != 'untyped')
    rec_failed = sum(1 for r in records if r['tolerant'] and r['verdict'] == 'failed')

    if a.verbose:
        # one line per extracted pair, tab-separated: the fixture asserts on these rather than
        # inferring a verdict from the absence of a flag, which a silently dropped pair also satisfies
        for r in records:
            print(f"  PAIR  {r['page']}:{r['line']}\t{'.'.join(r['path'])}\t{r['val']}\t{r['verdict']}")
    t_docs = time.time() - t1
    n_pairs = tot['tolerant_pairs']
    if n_pages == 0 or tot['n_json'] == 0 or n_pairs == 0 or typed_pairs == 0:
        print(f"  FAIL  scanned nothing: {n_pages} page(s), {tot['n_json']} json fence(s), "
              f"{n_pairs} pair(s), {typed_pairs} typed pair(s)")
        return 3

    print(f"  INFO  docs scan: {n_pages} page(s); {tot['n_json']} ```json fence(s) "
          f"({tot['n_json_strict']} strict-parse, {tot['n_json_tolerant']} unparseable and read tolerantly); "
          f"{tot['n_untagged']} untagged fence(s), of which {tot['n_untagged_strict']} parse as JSON and "
          f"{tot['n_untagged_jsonish']} hold JSON pairs (scanned); {tot['n_untagged_fragment']} more hold only a "
          f"quoted-key fragment inside a tree or sample (not scanned); {tot['n_other']} other-language fence(s) not scanned; "
          f"{tot['n_quoted']} fence(s) sit inside a blockquote, {tot['n_quoted_json']} of them ```json (all counted and scanned)")
    n_exempt = sum(exempt.values())
    print(f"  INFO  pairs: {n_pairs} string value(s) extracted, {typed_pairs} at a typed position "
          f"({untyped_pairs} untyped, not checkable); of the typed: {checked['resolved']} resolved, "
          f"{n_exempt} exempt (" + ', '.join(f"{k} {exempt[k]}" for k in EXEMPT_CLASSES)
          + f"), {checked['failed']} failed; resolved in {len(fam_checked)} distinct store(s)")
    print(f"  INFO  recovered from the unparseable fences: {tot['recovered_pairs']} pair(s), "
          f"{rec_typed} at a typed position, {rec_failed} failed")
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
    for r in decl_flags:
        what = (f"prefix `{r['val']}` that shipped ids start with (e.g. {r['hit'][0]})" if r['val'].endswith('_')
                else f"id `\"{r['val']}\"` that names a shipped asset")
        print(f"  FLAG  {r['page']}:{r['line']}: the placeholder note declares {what}; "
              f"a placeholder must be a name no asset has, so it excuses nothing")
    if flags or decl_flags:
        rc = rc or 1
    if rc == 0:
        print(f"  PASS  all {checked['resolved']} checked asset id(s) resolve in the family their key refers to")
    return rc


def report_typing(sweep, typed, excl, ratios, stores, covered):
    """The C1 report: histogram of per-key resolution ratios, what is typed, what is not."""
    for lvl, label in (('L1', 'bare key (L1)'), ('L2', 'parent.key (L2)'), ('LW', 'parent.* (LW)'), ('LN', 'parent.# numeric child (LN)')):
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
