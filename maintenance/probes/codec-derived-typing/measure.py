"""Codec-derived typing for gate 3, MEASURED ONLY, never built (CLAUDE.md gate 3, "Measured, not
built"). A key name K is typable as store S when EVERY KeyedCodec named K in the decompiled source
uses the asset codec of S (a CHILD_ASSET_CODEC, or a VALIDATOR_CACHE validator, of a class that
HytaleAssetStore registers with a setPath). Reports how many key names that types and how many
conflict, how many of the interactions replay's 41 misses and of HEAD's untyped docs pairs it would
reach, and how many keys it types to the empty Item/Block/Blocks store (the reason a build would
need (declaring class, key), not the key name alone).

Run from anywhere: python3 maintenance/probes/codec-derived-typing/measure.py
Needs ~/.cache/hytale-jar/src, ~/.cache/hytale-assets and the installed Assets.zip. ~1 min.
Committed 2026-10-16 after the review of bc10b45..23ea833 found the CLAUDE.md figures had no
committed probe (it lived in a session scratchpad)."""
import sys, re, os, pathlib, collections, importlib.util, tempfile, json
REPO = pathlib.Path(__file__).resolve().parents[3]
S = REPO / 'maintenance/scripts'
sys.path.insert(0, str(S))
import codec_parser as cp
def load(n, f):
    spec = importlib.util.spec_from_file_location(n, S / f); m = importlib.util.module_from_spec(spec); sys.modules[n] = m; spec.loader.exec_module(m); return m
gate = load('gate', 'check-asset-ids.py'); rec = load('rec', 'measure-asset-id-recall.py')
SRC = pathlib.Path(os.path.expanduser('~/.cache/hytale-jar/src'))
ASSETS = pathlib.Path(os.path.expanduser('~/.cache/hytale-assets'))
ctx = gate.build_context(ASSETS, SRC)
# class -> store, from HytaleAssetStore.builder(...).setPath("...")
cls2store = {}
for jp in (SRC / 'com/hypixel').rglob('*.java'):
    t = jp.read_text(errors='replace')
    for m in re.finditer(r'HytaleAssetStore\.builder\(', t):
        op = m.end() - 1
        try: cl = cp._scan(t, op)
        except Exception: continue
        args = cp._split_args(t[op+1:cl-1])
        cands = [a.strip()[:-6].split('.')[-1] for a in args if a.strip().endswith('.class')]
        cands = [c for c in cands if c not in ('String', 'Integer', 'Long')]
        end = t.find(';', cl)
        sp = re.search(r'\.setPath\("([^"]*)"\)', t[cl:end if end > 0 else len(t)])
        if cands and sp:
            cls2store[cands[0]] = sp.group(1)
print('asset classes with a setPath store:', len(cls2store), file=sys.stderr)
# unqualified CHILD_ASSET_CODEC: the nearest class, walking `extends`, that declares the field
sup, declares = {}, set()
for jp in (SRC / 'com/hypixel').rglob('*.java'):
    t = jp.read_text(errors='replace')
    m = re.search(r'\bclass\s+(\w+)\s*(?:<[^{]*?>)?\s*\n?\s*extends\s+(\w+)', t)
    if m and m.group(1) == jp.stem: sup[jp.stem] = m.group(2)
    if re.search(r'\bCHILD_ASSET_CODEC\w*\s*=', t): declares.add(jp.stem)
def owner_of(c):
    seen = 0
    while c and c not in declares and seen < 12:
        c = sup.get(c); seen += 1
    return c
decls = collections.defaultdict(list)    # K -> list of (file, stores frozenset, kind, plain?)
KEYED = re.compile(r'new\s+KeyedCodec\s*(?:<[^()]*?>)?\s*\(')
n_decl = 0
for jp in sorted((SRC / 'com/hypixel').rglob('*.java')):
    t = jp.read_text(errors='replace')
    own = jp.stem
    for m in KEYED.finditer(t):
        op = m.end() - 1
        try: cl = cp._scan(t, op)
        except Exception: continue
        args = cp._split_args(t[op+1:cl-1])
        if len(args) < 2 or not re.fullmatch(r'"[^"]*"', args[0].strip()): continue
        name = args[0].strip()[1:-1]; codec = args[1]
        n_decl += 1
        valtxt = ''
        pre = t[max(0, m.start()-90):m.start()]
        am = re.search(r'\.(appendInherited|append|addField)\s*\(\s*(?:\([^)]*\)\s*)?$', pre)
        if am:
            aop = m.start() - len(pre) + am.end() - 0
            # find the paren of the append group
            apos = t.rfind('(', max(0, m.start()-90), m.start())
            apos = max(0, m.start()-90) + am.end() - 1
            # locate '(' of append: it is the last '(' that belongs to the .append match
            mm = re.search(r'\.(appendInherited|append|addField)\s*\(', pre[am.start():])
            apos = max(0, m.start()-90) + am.start() + mm.end() - 1
            try:
                acl = cp._scan(t, apos)
                calls, _, closed = cp._dot_calls(t, acl)
                valtxt = ' '.join(a for n, a in calls if n in ('addValidator', 'addValidatorLate'))
                aargs = cp._split_args(t[apos+1:acl-1])
                valtxt += ' ' + ' '.join(aargs[2:])
            except Exception: pass
        stores = set(); mapkey = False
        for cm in re.finditer(r'\b(\w+)\.CHILD_ASSET_CODEC\w*|(?<![\w.])CHILD_ASSET_CODEC\w*', codec):
            c = cm.group(1) or owner_of(own) or own
            if c in cls2store: stores.add(cls2store[c])
            else: stores.add('?' + c)
        for vm in re.finditer(r'\b(\w+)\.VALIDATOR_CACHE\.(get\w+)', valtxt):
            c, how = vm.group(1), vm.group(2)
            if how == 'getMapKeyValidator': mapkey = True; continue
            stores.add(cls2store.get(c, '?' + c))
        kind = 'map' if re.search(r'Map\w*Codec', codec) else 'value'
        decls[name].append((jp.relative_to(SRC).as_posix(), frozenset(stores), kind, mapkey))
print('KeyedCodec declarations parsed:', n_decl, 'distinct key names:', len(decls))
typable, conflict, plain_only, unknownc = {}, {}, 0, 0
for K, ds in decls.items():
    sets = {d[1] for d in ds}
    any_store = any(d[1] for d in ds)
    if not any_store: plain_only += 1; continue
    if len(sets) == 1 and len(next(iter(sets))) == 1 and not any(s.startswith('?') for s in next(iter(sets))):
        typable[K] = (next(iter(next(iter(sets)))), {d[2] for d in ds}, len(ds))
    else:
        conflict[K] = ds
print('names with no asset codec in any declaration:', plain_only)
print('TYPABLE (every declaration uses the asset codec of one store S):', len(typable))
print('CONFLICTING (some declaration carries asset evidence, but not all agree on one known store):', len(conflict))
kinds = collections.Counter(tuple(sorted(v[1])) for v in typable.values()); print('  typable kinds:', dict(kinds))
by_store = collections.Counter(v[0] for v in typable.values()); print('  typable by store (top):', by_store.most_common(12))
# why conflicting
why = collections.Counter()
for K, ds in conflict.items():
    sets = [d[1] for d in ds]
    if any(not s for s in sets): why['some declaration has NO asset evidence (plain)'] += 1
    elif any(any(x.startswith('?') for x in s) for s in sets): why['asset class not a registered store (?)'] += 1
    else: why['declarations name different stores'] += 1
print('  conflict causes:', dict(why))
# agreement with the shipped-values typing
l1 = ctx.typed['L1']
agree = dis = untyped_by_ship = 0; dl = []
for K, (st, kinds_, n) in typable.items():
    if (K,) in l1:
        if st in l1[(K,)][0]: agree += 1
        else: dis += 1; dl.append((K, st, sorted(l1[(K,)][0])))
    else: untyped_by_ship += 1
print(f'  of the {len(typable)} typable: {agree} bare-key-typed by shipped values to the SAME store, {dis} to a different one, {untyped_by_ship} not typed (L1) by shipped values')
for d in dl[:30]: print('    DISAGREE', d)
# docs reach
def reach(path, tbl):
    k = path[-1]; p = path[-2] if len(path) > 1 else None
    if k in tbl: return k, tbl[k][0]
    if p in tbl and 'map' in tbl[p][1]: return p + '.*', tbl[p][0]
    return None
def run(label, docs_dir, only=None):
    pages = gate.scan_docs(docs_dir)
    recs = gate.evaluate(pages, ctx, load_packs := {}, ASSETS) if False else gate.evaluate(pages, ctx, gate.load_packs(REPO / 'examples'), ASSETS)
    return recs
def summarize(label, recs, den=None):
    unt = [r for r in recs if r['verdict'] == 'untyped']
    reached = []
    for r in unt:
        v = r['val']; core, g = gate.norm_value(v)
        if not core or not gate.ID_SHAPE.match(core) or gate.NUMERIC.match(core): continue
        rr = reach(r['path'], typable)
        if rr: reached.append((r, rr))
    ok = [(r, rr) for r, rr in reached if set(gate.resolves(r['val'], ctx.idx)) & {rr[1]}]
    bad = [(r, rr) for r, rr in reached if (r, rr) not in ok]
    print(f'[{label}] untyped pairs {len(unt)}; reached by codec typing (id-shaped): {len(reached)} pairs / {len({r["val"] for r, _ in reached})} distinct values; resolve in S: {len(ok)}; do NOT resolve: {len(bad)}')
    kc = collections.Counter(rr[0] for r, rr in reached); print('   keys reached (pairs):', dict(kc.most_common(25)))
    return reached, ok, bad
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    base = rec.export_docs(rec.REV_BASE, td / 'a')
    recs_base = run('37425a6', base)
    HEAD = REPO / 'docs'
    recs_head = run('HEAD', HEAD)
    # the 41 misses
    fix = rec.export_docs(rec.REV_FIX, td / 'b')
    vb, vf = rec.json_fence_values(base), rec.json_fence_values(fix)
    import subprocess
    zs = rec.stems_from_names(subprocess.run(['unzip', '-Z1', os.path.expanduser('~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Assets.zip')], capture_output=True, text=True, check=True).stdout.split('\n'))
    den = sorted(v for v in vb if v not in vf and rec.ID_LIKE.match(v) and v not in zs)
    gate.NUMERIC_CHILD = False
    recs_b0 = run('37425a6 (NUMERIC_CHILD off)', base)
    flagged = {r['val'] for r in recs_b0 if r['verdict'] == 'failed' and r['page'].startswith('interactions')}
    misses = [v for v in den if v not in flagged]
    print('misses before this item:', len(misses))
    reached_m = {}
    for r in recs_b0:
        if r['val'] in misses and r['page'].startswith('interactions'):
            rr = reach(r['path'], typable)
            if rr: reached_m.setdefault(r['val'], set()).add((rr[0], rr[1], '.'.join(r['path'][-2:])))
    print(f'41-miss reach: {len(reached_m)} of {len(misses)} missed values sit at a codec-typable position')
    for v, s in sorted(reached_m.items()): print('   ', v, sorted(s))
    unreached = [v for v in misses if v not in reached_m]
    print('   not reached:', unreached)
    gate.NUMERIC_CHILD = True
    summarize('37425a6', recs_base); r_h = summarize('HEAD', recs_head)
    # HEAD bad list
    for r, rr in r_h[2][:40]:
        print('   HEAD no-resolve', r['page'], r['line'], '.'.join(r['path']), r['val'], '->', rr)
    # HEAD, pairs the gate already types: how many of the codec-typable keys' positions are already covered
    typed_already = [r for r in recs_head if r['verdict'] != 'untyped' and reach(r['path'], typable)]
    print('HEAD pairs at codec-typable positions already typed by the gate:', len(typed_already))
print('---- conflict detail')
for K in ('Forward','Back','Flags','Next','Failed','Interactions','Parent','Block','EffectId','ChainId','Id','Key'):
    if K in conflict:
        print(K, 'CONFLICT', [(d[0].split('/')[-1], sorted(d[1]), d[2]) for d in conflict[K]])
    elif K in typable: print(K, 'TYPABLE', typable[K])
    else: print(K, 'no asset evidence', [(d[0].split('/')[-1]) for d in decls.get(K, [])][:6])
bl = [K for K,v in typable.items() if v[0]=='Item/Block/Blocks']; print('typable keys whose store is the block store Item/Block/Blocks:', len(bl), bl)
