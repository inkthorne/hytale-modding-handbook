#!/usr/bin/env python3
"""
census.py -- which pass of a double run does each registered Interaction type's work in?

Run it with the decompiled-source cache (read-only; nothing is written):

    python3 -I maintenance/probes/double-run/census.py                 # table + denominator
    python3 -I maintenance/probes/double-run/census.py --src DIR       # another cache
    python3 -I maintenance/probes/double-run/census.py --check         # only the denominator/self-checks

Re-run it at the next build and diff against census-0.7.2.txt.

WHAT IT DECIDES (mechanically, from source text; it never runs the game)
  Population: every name registered in the `Interaction` codec registry, taken from
  maintenance/scripts/registry_miner.py (not from "extends SimpleInstantInteraction"). The miner
  records NAMES; the class is parsed here from the `.register(name, X.class, ...)` call itself.
  Per name: its class, the chain of superclasses up to `Interaction`, and for each hook the
  nearest class in that chain that declares it:
      simulateTick0   what the simulation pass calls (Interaction.simulateTick, final)
      simulateFirstRun  what SimpleInstantInteraction.simulateTick0 calls
      tick0           what the server pass calls (Interaction.tick, final)
      getWaitForDataFrom  None | Server | Client: sets the pass order and whether the server pass waits
  and the one-word kind of each declared body:
      no-op            empty, or only `return`
      runs-tick0       one statement: this.tick0(...)
      runs-firstRun    one statement: this.firstRun(...)
      delegates        one statement: super.<hook>(...)
      other            anything else (the calls it makes are listed)
  Then `sim` is what the simulation pass reaches, following delegation:
      tick0 / firstRun  the same method the server pass runs, called again (`+` = with code around it)
      via-<hook>:<kind> an own body that calls one more overridable hook (abstract, or declared twice in the
                        chain), e.g. via-simulateInteractWithBlock:no-op for the block interactions
      no-op             nothing runs in the simulation pass
      own               a different body from the server pass's; read it
  The word does NOT say whether running it twice changes the world. That is the next step (the
  effect table, item 13b) and needs a reading of the body, or a run.

DENOMINATOR (printed first, and --check fails if any line is zero or does not add up)
  names registered, distinct classes, classes carrying more than one name, names whose class could
  not be parsed (must be 0), classes whose superclass chain did not reach Interaction (must be 0).
"""
from __future__ import annotations
import argparse, collections, pathlib, re, sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import registry_miner as rm                      # noqa: E402
from codec_parser import _split_args, find_source  # noqa: E402

INTERACTION_FQ = 'com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction'
REGISTRY_KEY = INTERACTION_FQ + '.CODEC'
HOOKS = ('simulateTick0', 'simulateFirstRun', 'tick0', 'getWaitForDataFrom')
KEYWORDS = {'if', 'for', 'while', 'switch', 'catch', 'assert', 'return', 'new', 'synchronized', 'throw', 'else'}


# ---------------------------------------------------------------- source access

class Tree:
    def __init__(self, root: pathlib.Path):
        self.root = root
        self._cache: dict[pathlib.Path, tuple[str, str]] = {}

    def text(self, path):
        if path not in self._cache:
            src = path.read_text(errors='replace')
            self._cache[path] = (src, rm._mask(src))
        return self._cache[path]


def match_brace(masked: str, i: int) -> int:
    """Index just past the `}` closing the `{` at masked[i]."""
    depth = 0
    for j in range(i, len(masked)):
        c = masked[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError('unbalanced braces')


def strip_generics(h: str) -> str:
    out, d = [], 0
    for c in h:
        if c == '<':
            d += 1
        elif c == '>':
            d = max(0, d - 1)
        elif d == 0:
            out.append(c)
    return ''.join(out)


class Cls:
    """One class: the file, its header text (masked), and the span of its body."""
    def __init__(self, fq, path, src, masked, hdr_start, body_start, body_end):
        self.fq, self.path, self.src, self.masked = fq, path, src, masked
        self.hdr_start, self.body_start, self.body_end = hdr_start, body_start, body_end
        self.header = strip_generics(masked[hdr_start:body_start])

    @property
    def simple(self):
        return self.fq.rsplit('.', 1)[-1]

    @property
    def is_abstract(self):
        return bool(re.search(r'\babstract\b', self.header))

    @property
    def extends(self):
        m = re.search(r'\bclass\s+\w+\s+extends\s+([\w.]+)', self.header)
        return m.group(1) if m else None


def find_class(tree: Tree, fq: str) -> Cls | None:
    path = find_source(fq, tree.root)
    if path is None:
        return None
    src, masked = tree.text(path)
    rel = path.relative_to(tree.root).with_suffix('')
    top = '.'.join(rel.parts)
    nest = fq[len(top):].lstrip('.').split('.') if fq != top else []
    lo, hi = 0, len(masked)
    chain = [top.rsplit('.', 1)[-1]] + nest
    start = None
    for name in chain:
        m = re.compile(r'(?<![\w.$])class\s+' + re.escape(name) + r'\b').search(masked, lo, hi)
        if not m:
            return None
        b = masked.find('{', m.end())
        e = match_brace(masked, b)
        start = (m.start(), b, e)
        lo, hi = b + 1, e - 1
    return Cls(fq, path, src, masked, *start)


def resolve_base(tree: Tree, c: Cls, name: str) -> str | None:
    """FQCN of the superclass `name` as written in class c's file."""
    masked = c.masked
    imports = {fq.rsplit('.', 1)[-1]: fq for fq in rm._IMPORT.findall(c.src)}
    pkg_m = rm._PKG.search(c.src)
    pkg = pkg_m.group(1) if pkg_m else ''
    first = name.split('.')[0]
    rest = name[len(first):]
    cands = [name] if '.' in name else []                # written fully qualified
    if first in imports:
        cands.append(imports[first] + rest)
    # a nested class of the same file (or of an enclosing class of it)
    if re.search(r'(?<![\w.$])class\s+' + re.escape(first) + r'\b', masked):
        top = c.fq.split('.')
        for k in range(len(top), 0, -1):
            cands.append('.'.join(top[:k]) + '.' + name)
        cands.append((pkg + '.' if pkg else '') + name)
    cands.append((pkg + '.' if pkg else '') + name)                     # same package
    for w in re.findall(r'^import\s+([\w.]+)\.\*;', c.src, re.M):       # wildcard imports
        cands.append(w + '.' + name)
    for fq in cands:
        if fq == INTERACTION_FQ or find_class(tree, fq) is not None:
            return fq
    return None


# ---------------------------------------------------------------- hooks

def declarations(c: Cls):
    """(name, body_or_None) for every method declared directly in class c (depth 1 of its body).
    None marks a declaration with no body (abstract)."""
    out = []
    body = c.masked[c.body_start + 1:c.body_end - 1]
    depth_at = []
    d = 0
    for ch in body:
        if ch == '}':
            d -= 1
        depth_at.append(d)
        if ch == '{':
            d += 1
    for m in re.finditer(r'(?<![\w.$])(\w+)\s*\(', body):
        name = m.group(1)
        if depth_at[m.start()] != 0 or name in KEYWORDS:
            continue
        before = body[max(0, m.start() - 60):m.start()]
        if not re.search(r'[\w>\]]\s+$', before) or re.search(r'\bnew\s+$', before):
            continue                                         # a call or `new X(`, not a declaration
        i = m.end() - 1
        depth = 0
        for j in range(i, len(body)):
            if body[j] == '(':
                depth += 1
            elif body[j] == ')':
                depth -= 1
                if depth == 0:
                    break
        mm = re.match(r'\s*(?:throws\s+[\w.,\s]+?)?\s*(\{|;)', body[j + 1:])
        if not mm:
            continue
        if mm.group(1) == ';':
            out.append((name, None))
            continue
        bstart = j + 1 + mm.end() - 1
        bend = match_brace(body, bstart)
        out.append((name, body[bstart + 1:bend - 1]))
    return out


def methods_at_depth1(c: Cls, name: str):
    """The bodies of the methods called `name` declared directly in c (abstract ones are skipped)."""
    return [b for n, b in declarations(c) if n == name and b is not None]


def classify(body: str):
    """(kind, calls). kind in no-op | runs-tick0 | runs-firstRun | delegates:<m> | other."""
    b = body.strip()
    if not b or re.fullmatch(r'return\s*;?', b):
        return 'no-op', []
    calls = []
    for m in re.finditer(r'(?<![\w$])((?:this\.|super\.)?)(\w+)\s*\(', b):
        n = m.group(2)
        if n in KEYWORDS:
            continue
        calls.append((m.group(1) + n))
    one = re.fullmatch(r'(?:return\s+)?((?:this\.|super\.)?)(\w+)\s*\((?:[^;{}]*)\)\s*;?', b, re.S)
    if one and '{' not in b and b.count(';') <= 1:
        who, n = one.group(1), one.group(2)
        if who == 'super.':
            return 'delegates:' + n, calls
        if n == 'tick0':
            return 'runs-tick0', calls
        if n == 'firstRun':
            return 'runs-firstRun', calls
    return 'other', calls


def return_value(body: str):
    m = re.fullmatch(r'\s*return\s+([\w.]+)\s*;\s*', body)
    return m.group(1).split('.')[-1] if m else None


class Chain:
    """A class and its superclasses up to Interaction."""
    def __init__(self, tree: Tree, fq: str):
        self.classes: list[Cls] = []
        self.complete = False
        seen = set()
        cur = fq
        while cur and cur != INTERACTION_FQ and cur not in seen:
            seen.add(cur)
            c = find_class(tree, cur)
            if c is None:
                return
            self.classes.append(c)
            ex = c.extends
            if ex is None:
                return
            cur = resolve_base(tree, c, ex)
        self.complete = cur == INTERACTION_FQ

    def nearest(self, hook: str, start: int = 0):
        """(index in chain, body) of the first class from `start` that declares hook, or None."""
        for i in range(start, len(self.classes)):
            ms = methods_at_depth1(self.classes[i], hook)
            if ms:
                return i, ms[0]
        return None

    def short(self):
        return ' < '.join(c.simple for c in self.classes) + ' < Interaction'


def first_run_reach(ch: Chain, start: int = 0):
    """What a call of simulateFirstRun reaches, from the nearest class at or above `start` that declares it:
    (label, note). Follows `super.simulateFirstRun(...)` down the chain, as sim_pass follows super.simulateTick0."""
    sr = ch.nearest('simulateFirstRun', start)
    if sr is None:
        return 'unknown', 'no class declares simulateFirstRun'
    j, sbody = sr
    sk, scalls = classify(sbody)
    sat = ch.classes[j].simple
    if sk == 'no-op':
        return 'no-op', f'{sat}.simulateFirstRun is empty'
    if sk == 'runs-firstRun':
        return 'firstRun', f'{sat}.simulateFirstRun calls firstRun'
    if sk == 'delegates:simulateFirstRun':
        lab, note = first_run_reach(ch, j + 1)
        return lab, f'{sat}.simulateFirstRun delegates to super; {note}'
    if any(c in ('firstRun', 'this.firstRun') for c in scalls):
        return 'firstRun+', f'{sat}.simulateFirstRun has its own code and calls firstRun'
    if 'super.simulateFirstRun' in scalls:
        lab, note = first_run_reach(ch, j + 1)
        return lab.rstrip('+') + '+', f'{sat}.simulateFirstRun has its own code and calls super ({note})'
    via = via_hook(ch, scalls)
    if via:
        return via[0], f'{sat}.simulateFirstRun is its own body and calls {via[1]}'
    return 'own', f'{sat}.simulateFirstRun is its own body (calls {", ".join(sorted(set(scalls))) or "-"})'


def sim_pass(ch: Chain, start: int = 0, depth: int = 0):
    """What the simulation pass reaches: (label, note). Follows delegation to the server-pass code."""
    nr = ch.nearest('simulateTick0', start)
    if nr is None:
        return 'unknown', 'no simulateTick0 declared'
    i, body = nr
    kind, calls = classify(body)
    at = ch.classes[i].simple
    if kind == 'no-op':
        return 'no-op', f'{at}.simulateTick0 is empty'
    if kind == 'runs-tick0':
        return 'tick0', f'{at}.simulateTick0 calls tick0'
    if kind == 'runs-firstRun':
        return 'firstRun', f'{at}.simulateTick0 calls firstRun'
    if kind.startswith('delegates:'):
        lab, note = sim_pass(ch, i + 1, depth + 1)
        return lab, f'{at} delegates to super; {note}'
    # other: look at which hook it reaches
    if 'simulateFirstRun' in [c.split('.')[-1] for c in calls if not c.startswith('super.')] or 'this.simulateFirstRun' in calls:
        lab, note = first_run_reach(ch, 0)
        return lab, note
    if any(c in ('firstRun', 'this.firstRun') for c in calls):
        return 'firstRun+', f'{at}.simulateTick0 has its own code and calls firstRun'
    plain = [c for c in calls if c in ('tick0', 'this.tick0')]
    sup = [c for c in calls if c == 'super.simulateTick0']
    if plain:
        return 'tick0+', f'{at}.simulateTick0 calls tick0 with code around it'
    if sup:
        lab, note = sim_pass(ch, i + 1, depth + 1)
        base = lab.rstrip('+')
        return base + '+', f'{at}.simulateTick0 has its own code and calls super ({note})'
    via = via_hook(ch, calls)
    if via:
        return via[0], f'{at}.simulateTick0 is its own body and calls {via[1]}'
    return 'own', f'{at}.simulateTick0 is its own body (calls {", ".join(sorted(set(calls))) or "-"})'


def via_hook(ch: 'Chain', calls):
    """An own body that calls exactly one more overridable hook of the chain (abstract, or declared
    by two of its classes; not tick0/firstRun): the work is in that hook. Returns ('via-<name>:<kind>', description) or None."""
    decls = [(n, b) for c in ch.classes for n, b in declarations(c)]
    counts = collections.Counter(n for n, _ in decls)
    # an overridable hook: declared abstract somewhere in the chain, or declared by two of its classes
    own = {n for n, b in decls if b is None or counts[n] >= 2} - set(HOOKS) - {'handle', 'firstRun'}
    named = sorted({c.split('.')[-1] for c in calls if not c.startswith('super.')} & own)
    if len(named) != 1:
        return None
    n = named[0]
    nr = ch.nearest(n, 0)
    if nr is None:
        return None
    kind, _ = classify(nr[1])
    return f'via-{n}:{kind}', f'{ch.classes[nr[0]].simple}.{n} ({kind})'


def wait_of(ch: Chain):
    nr = ch.nearest('getWaitForDataFrom', 0)
    if nr is None:
        return 'unknown', '-'
    i, body = nr
    rv = return_value(body)
    return (rv if rv else 'other'), ch.classes[i].simple


# ---------------------------------------------------------------- the registry

def interaction_registry(tree: Tree):
    regs = rm.mine(tree.root)
    reg = regs.get(REGISTRY_KEY)
    if reg is None:
        raise SystemExit(f'FAIL  registry {REGISTRY_KEY} not found by the miner')
    return reg


def class_arg(site, tree: Tree):
    """The `X.class` argument of the .register(...) call the miner recorded as `site`."""
    path = pathlib.Path(site.file)
    src, masked = tree.text(path)
    for stmt, off in rm._statement_spans(src):
        if off != site.stmt:
            continue
        mstmt = masked[off:off + len(stmt)]
        for r in rm._REGISTER.finditer(mstmt):
            if src.count('\n', 0, off + r.start()) + 1 != site.line:
                continue
            opener = r.end() - 1
            from codec_parser import _scan
            args = _split_args(stmt[opener + 1:_scan(stmt, opener) - 1])
            # several registers can share one line (WorldEventsPlugin chains them): pick by the id argument the miner recorded
            if not any(a.strip() == site.id_expr.strip() for a in args):
                continue
            cls = [a for a in args if re.fullmatch(r'[\w.]+\.class', a.strip())]
            if len(cls) == 1:
                return cls[0].strip()[:-len('.class')], args
            return None, args
    return None, []


def fq_from_arg(tree: Tree, site, simple: str):
    path = pathlib.Path(site.file)
    src, masked = tree.text(path)
    imports = {fq.rsplit('.', 1)[-1]: fq for fq in rm._IMPORT.findall(src)}
    pkg_m = rm._PKG.search(src)
    pkg = pkg_m.group(1) if pkg_m else ''
    first = simple.split('.')[0]
    rest = simple[len(first):]
    cands = []
    if first in imports:
        cands.append(imports[first] + rest)
    cands.append((pkg + '.' if pkg else '') + simple)
    for w in re.findall(r'^import\s+([\w.]+)\.\*;', src, re.M):
        cands.append(w + '.' + simple)
    for fq in cands:
        if find_class(tree, fq) is not None:
            return fq
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=str(pathlib.Path.home() / '.cache/hytale-jar/src'))
    ap.add_argument('--check', action='store_true', help='print only the denominator; exit 1 on a bad line')
    a = ap.parse_args()
    root = pathlib.Path(a.src)
    if not (root / 'com/hypixel/hytale').is_dir():
        print(f'FAIL  {root} is not a decompiled-source tree', file=sys.stderr)
        return 1
    tree = Tree(root)
    meta = root.parent / 'cache-meta.txt'
    ident = meta.read_text().replace('\n', ' ') if meta.exists() else '(no cache-meta.txt)'
    reg = interaction_registry(tree)

    rows = []            # (name, fq, chain, sim, simnote, wait, waitat)
    unparsed = []
    for s in reg.sites:
        simple, args = class_arg(s, tree)
        fq = fq_from_arg(tree, s, simple) if simple else None
        if fq is None:
            unparsed.append((s.name, s.file, s.line, args))
            continue
        ch = Chain(tree, fq)
        rows.append((s.name, fq, ch))
    byclass = collections.defaultdict(list)
    for n, fq, ch in rows:
        byclass[fq].append(n)
    open_chain = [(n, fq) for n, fq, ch in rows if not ch.complete]
    multi = {fq: ns for fq, ns in byclass.items() if len(ns) > 1}

    print(f'build: {ident}')
    print(f'source: {str(root).replace(str(pathlib.Path.home()), "~")}')
    print('DENOMINATOR')
    print(f'  registry: {REGISTRY_KEY} ({reg.verdict}, key "{reg.discriminator}")')
    print(f'  names registered (miner sites): {len(reg.sites)}; distinct names: {len(reg.names)}')
    print(f'  names whose class was parsed: {len(rows)}; names whose class could not be parsed: {len(unparsed)}')
    print(f'  distinct classes: {len(byclass)}; classes carrying more than one name: {len(multi)}')
    print(f'  classes whose superclass chain did not reach Interaction: {len(set(fq for _, fq in open_chain))}')
    for fq, ns in sorted(multi.items()):
        print(f'    {fq.rsplit(".", 1)[-1]} carries {len(ns)} names: {", ".join(sorted(ns))}')
    for n, f, l, args in unparsed:
        print(f'    UNPARSED {n} ({f}:{l}) args={args}')
    for n, fq in open_chain:
        print(f'    BROKEN CHAIN {n} {fq}')
    bad = []
    if len(reg.sites) == 0 or len(rows) == 0:
        bad.append('the census visited nothing')
    if len(rows) + len(unparsed) != len(reg.sites):
        bad.append('parsed + unparsed != sites')
    if unparsed:
        bad.append(f'{len(unparsed)} names whose class could not be parsed')
    if open_chain:
        bad.append('a superclass chain did not reach Interaction')
    if sum(len(v) for v in byclass.values()) != len(rows):
        bad.append('class table does not add up')
    for b in bad:
        print('FAIL  ' + b)
    if a.check:
        return 1 if bad else 0

    # ---- per-class facts (a class carrying several names is one row)
    print()
    print('PER CLASS (sim = what the simulation pass reaches; wait = getWaitForDataFrom)')
    sims = collections.Counter()
    waits = collections.Counter()
    table = []
    for fq in sorted(byclass, key=lambda f: sorted(byclass[f])[0].lower()):
        ch = next(c for n, f, c in rows if f == fq)
        lab, note = sim_pass(ch)
        w, wat = wait_of(ch)
        hooks = []
        for h in ('simulateTick0', 'simulateFirstRun', 'tick0'):
            nr = ch.nearest(h, 0)
            if nr is None:
                hooks.append(f'{h}=-')
                continue
            i, body = nr
            kind, _ = classify(body)
            hooks.append(f'{h}={ch.classes[i].simple}:{kind}')
        table.append((sorted(byclass[fq]), fq, ch, lab, note, w, wat, hooks))
        sims[lab] += len(byclass[fq])
        waits[w] += len(byclass[fq])
    for names, fq, ch, lab, note, w, wat, hooks in table:
        print(f'{"/".join(names)}')
        print(f'    class   {fq.rsplit(".", 1)[-1]}  [{ch.short()}]')
        print(f'    sim     {lab}  -- {note}')
        print(f'    wait    {w} (declared in {wat})')
        print(f'    hooks   {"; ".join(hooks)}')
    print()
    print('SUMMARY (counted in NAMES, denominator ' + str(len(rows)) + ')')
    for k, v in sorted(sims.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f'  sim {k:8s} {v:4d}')
    for k, v in sorted(waits.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f'  wait {k:8s} {v:4d}')
    # the two shapes a plugin author can write
    simple_inst = sum(len(byclass[fq]) for fq in byclass
                      if any(c.simple == 'SimpleInstantInteraction' for c in next(c for n, f, c in rows if f == fq).classes))
    print(f'  names whose class extends SimpleInstantInteraction (shape 1): {simple_inst}')
    print(f'  all other names (shape 2, tick0/simulateTick0 written by hand): {len(rows) - simple_inst}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
