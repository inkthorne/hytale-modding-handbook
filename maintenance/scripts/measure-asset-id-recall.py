#!/usr/bin/env python3
"""
Recall of check-asset-ids.py on the invented ids two historical commits removed by hand.

A gate that reports nothing on today's docs says nothing about whether it WOULD have
caught the defects that motivated it; this replays it on the docs as they stood BEFORE
those fixes and counts. Not a gate and not run by verify-docs.sh (it needs git history
and the Assets.zip listing); run by hand after the gate or its typing changes.

Nothing is checked out. Each tree is rebuilt with `git show <rev>:<path>` into a temp
directory, so concurrent work in the checkout is never touched.

(a) INTERACTIONS. Denominator = the distinct string values in the ```json fences of
    37425a6's docs/interactions*.md that are ABSENT from d58a7a1's (the commit that removed
    the invented ones) AND are id-shaped AND match no file stem anywhere in the 0.7.2
    `unzip -Z1 Assets.zip` listing. It is computed from raw quoted strings with a plain
    regex, WITHOUT the gate's family table or tolerant extractor, so the denominator
    does not share the gate's blind spots. Recall = denominator values the gate FLAGS on
    37425a6's docs. Every miss is grouped by cause: untyped key position, an exemption
    class, or extraction (no pair carried the value). Also listed: every flag the gate
    raises on 37425a6 that d58a7a1 kept.

(b) DROPS. d003f50 removed 46 `"ItemId"` lines from docs/drops.md, among them 31 invented
    ids (a3f68ea only bumped the stamp). Denominator = the distinct ids on those removed
    lines that match no file stem in build-26's asset list
    (`git show 8a83d79:maintenance/baseline/ServerAssetsIndex.hashes`). The gate's typing
    is derived from the 0.7.2 assets, so the skew is reported separately: how many of
    the denominator are also absent from 0.7.2, and the gate's flags on that page that
    are NOT in the denominator, with whether each exists in build-26.

Usage: python3 maintenance/scripts/measure-asset-id-recall.py [--assets DIR] [--src DIR] [--zip FILE]
"""
from __future__ import annotations
import argparse, collections, importlib.util, os, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
REV_BASE, REV_FIX = '37425a6', 'd58a7a1'
REV_DROPS_FIX = 'd003f50'
REV_BUILD26 = '8a83d79'
FENCE = re.compile(r'^([ \t]*(?:>[ \t]?)*)```(\w*)[^\n]*\n(.*?)^[ \t]*(?:>[ \t]?)*```', re.M | re.S)   # blockquoted fences too
QUOTED = re.compile(r'"((?:[^"\\\n]|\\.)*)"')   # consumed left to right, so a closing quote never opens the next
ID_LIKE = re.compile(r'^[A-Za-z][A-Za-z0-9_.\-]*$')


# ---------------------------------------------------------------------------------------------
# DECLARED SCOPE (acceptance 6). Which positions of the interactions replay name an ASSET.
#
# Written from the decompiled consumers BEFORE any verdict of the item was read, and applied to
# every value of the denominator, hits included, so that the subset figure cannot be selected
# by what the gate happened to catch. Each row is the codec field the position is, the consumer
# that reads it, and one of three classes:
#   asset  the value names a file in a `setPath` store (an id the engine resolves, or should)
#   free   ANY value is legal: the engine creates or keys state by the string, nothing resolves it
#   gap    a real reference that is NOT a file stem (a map key inside an asset, a model node, a
#          .lang key): the gate cannot check it by construction. A NAMED GAP, not built here.
# `classify(path)` is keyed by the last key, with the parent only where one key name is two codec
# fields (`Id`) or the key is a free-form / numeric map child. A position it does not know raises:
# the table must cover the denominator or the measurement does not run.
# ---------------------------------------------------------------------------------------------
_IA = ('asset', 'Item/Interactions')
SCOPE_BY_KEY = {
    # Interaction.CHILD_ASSET_CODEC / the Interaction validator
    **{k: (*_IA, 'Interaction child: Interaction.CHILD_ASSET_CODEC') for k in (
        'Next', 'Failed', 'Interactions', 'Parent', 'Click', 'Held',
        'Forward', 'Back', 'ForwardLeft', 'ForwardRight', 'BackLeft', 'BackRight')},
    'EffectId': ('asset', 'Entity/Effects', 'ApplyEffectInteraction.EffectId, HasEffectCondition.EffectId: EntityEffect.VALIDATOR_CACHE'),
    'EntityEffectIds': ('asset', 'Entity/Effects', 'EffectConditionInteraction.EntityEffectIds: EntityEffect.VALIDATOR_CACHE'),
    'WorldSoundEventId': ('asset', 'Audio/SoundEvents', 'InteractionEffects / DamageEffects / EntityEffect: SoundEvent.VALIDATOR_CACHE'),
    'LocalSoundEventId': ('asset', 'Audio/SoundEvents', 'InteractionEffects / DamageEffects / EntityEffect: SoundEvent.VALIDATOR_CACHE'),
    'ProjectileId': ('asset', 'Projectiles', 'LaunchProjectileInteraction.ProjectileId: Projectile.VALIDATOR_CACHE'),
    'SystemId': ('asset', 'Particles', 'ModelParticle.SystemId: ParticleSystem.VALIDATOR_CACHE'),
    'Block': ('asset', 'Item/Items', 'PlacementCountConditionInteraction.Block: plain string, looked up in BlockCounter by placed block-type key; '
                                    'a name no block has can never match'),
    # ---- free
    'ChainId': ('free', None, 'ChainingInteraction/ChainFlag/CancelChain.ChainId: a key into a runtime Object2IntMap (dataComponent.namedMap); '
                              'nothing resolves it, two interactions agree by writing the same string'),
    # ---- named gaps
    'ItemAnimationId': ('gap', None, 'InteractionEffects.ItemAnimationId: looked up with playerAnimations.getAnimations().get(id), a key of '
                                     'the Animations map INSIDE an ItemPlayerAnimations asset (Item/Animations/*.json), chosen by ItemPlayerAnimationsId'),
    'TargetNodeName': ('gap', None, 'ModelParticle/ModelTrail/BeamInstance.TargetNodeName: a node name inside a model file'),
    'Key': ('gap', None, 'SendMessageInteraction.Key: a translation key in a Languages/*/server.lang file'),
}


def classify(path):
    """(class, store or None, reason) for a pair's key path; raises KeyError on a position the table does not know."""
    k = path[-1]
    p = path[-2] if len(path) > 1 else None
    if p == 'Flags':
        return ('asset', 'Item/Interactions', 'ChainingInteraction.Flags: MapCodec(Interaction.CHILD_ASSET_CODEC), free-form keys')
    if p == 'Next' and re.match(r'^[0-9.]+$', k):
        return ('asset', 'Item/Interactions', 'ChargingInteraction.Next: Float2ObjectMapCodec(Interaction.CHILD_ASSET_CODEC)')
    if k == 'Id':
        if p == 'Block':
            return ('asset', 'Item/Items', 'BlockConditionInteraction.BlockIdMatcher.Id: BlockType.VALIDATOR_CACHE')
        if p == 'Cooldown':
            return ('free', None, 'InteractionCooldown.Id: a key into CooldownHandler.cooldowns, created by computeIfAbsent; any string is legal')
        raise KeyError(f"'Id' under {p!r}")
    if k in SCOPE_BY_KEY:
        return SCOPE_BY_KEY[k]
    raise KeyError(f'{p!r}.{k!r}')


def load_gate():
    spec = importlib.util.spec_from_file_location('check_asset_ids', HERE / 'check-asset-ids.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules['check_asset_ids'] = m
    spec.loader.exec_module(m)
    return m


def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True, check=True).stdout


def export_docs(rev, dest: pathlib.Path):
    """docs/ as of `rev`, via git show; returns the docs dir."""
    d = dest / 'docs'
    d.mkdir(parents=True)
    for name in git('ls-tree', '-r', '--name-only', rev, '--', 'docs').split('\n'):
        if name.endswith('.md'):
            (d / pathlib.Path(name).name).write_text(git('show', f'{rev}:{name}'))
    return d


def json_fence_values(docs: pathlib.Path, glob='interactions*.md'):
    vals = collections.defaultdict(set)      # value -> pages
    for f in sorted(docs.glob(glob)):
        for m in FENCE.finditer(f.read_text()):
            if m.group(2) == 'json':
                body = '\n'.join(re.sub(r'^[ \t]*(?:>[ \t]?)*', '', ln) for ln in m.group(3).split('\n')) \
                    if '>' in m.group(1) else m.group(3)
                for q in QUOTED.finditer(body):
                    if not body[q.end():].lstrip().startswith(':'):     # a value, not a key
                        vals[q.group(1)].add(f.name)
    return vals


def stems_from_names(names):
    out = set()
    for n in names:
        b = n.rsplit('/', 1)[-1]
        if not b:
            continue
        out.add(b.rsplit('.', 1)[0])
        out.add(b.split('.')[0])
    return out


def pct(a, b):
    return f'{a}/{b} = {100 * a / b:.0f}%' if b else f'{a}/0'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', default=os.path.expanduser('~/.cache/hytale-assets'))
    ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
    ap.add_argument('--zip', default=os.path.expanduser(
        '~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Assets.zip'))
    a = ap.parse_args()
    for label, p in (('asset cache', a.assets), ('decompiled source', a.src), ('Assets.zip', a.zip)):
        if not pathlib.Path(p).exists():
            print(f'  SKIP  {label} not found at {p}')
            return 2

    gate = load_gate()
    ctx = gate.build_context(pathlib.Path(a.assets), pathlib.Path(a.src))
    packs = gate.load_packs(REPO / 'examples')
    zip_stems = stems_from_names(subprocess.run(['unzip', '-Z1', a.zip], capture_output=True,
                                                text=True, check=True).stdout.split('\n'))
    print(f'  INFO  0.7.2 Assets.zip listing: {len(zip_stems)} distinct file stem(s)')
    rc = 0
    results = {}
    # The gate was changed after its first docs run (see its constants). Recall is
    # reported under every setting so neither change can quietly buy or cost a number.
    shipped = {k: getattr(gate, k) for k in ('WIDEN', 'VERBATIM_STRICT', 'EXACT_WINS', 'PARENT_K', 'NUMERIC_CHILD')}
    settings = (
        ('first docs run: no verbatim, bare key wins, speaks for any parent',
         dict(WIDEN=False, VERBATIM_STRICT=False, EXACT_WINS=False, PARENT_K=1, NUMERIC_CHILD=False)),
        ('+ verbatim from every class (the widening before the review)',
         dict(WIDEN=True, VERBATIM_STRICT=False, EXACT_WINS=False, PARENT_K=1, NUMERIC_CHILD=False)),
        ('+ PARENT_K',
         dict(WIDEN=True, VERBATIM_STRICT=False, EXACT_WINS=False, NUMERIC_CHILD=False)),
        # PRE-REGISTERED (acceptance 6): this row is run FIRST and is the baseline the item is judged
        # against, with the numeric map-child class (LN) switched off.
        ('before this item: + strict verbatim + exact position wins',
         dict(NUMERIC_CHILD=False)),
        ('as shipped: + numeric map-child class (LN)',
         dict()))
    for label, over in settings:
        for k, v in {**shipped, **over}.items():
            setattr(gate, k, v)
        print(f"\n{'=' * 8} {label} {'=' * 8}")
        r, res = measure(gate, ctx, packs, zip_stems, a, detail=label.startswith(('before this item', 'as shipped')))
        rc = rc or r
        results[label] = res
    for k, v in shipped.items():
        setattr(gate, k, v)
    for label, (ra, rb) in results.items():
        print(f"RECALL (a) {ra:.0%}  (b) {rb:.0%}   {label}")
    # PARENT_K sweep: does the data choose K? Flag sets per docs revision for K = 1..4.
    with tempfile.TemporaryDirectory() as td2:
        td2 = pathlib.Path(td2)
        trees = {'37425a6': export_docs(REV_BASE, td2 / 'a'), 'a83ffd0': export_docs('a83ffd0', td2 / 'b'),
                 'HEAD (working tree)': REPO / 'docs'}
        for name, tree in trees.items():
            pages = gate.scan_docs(tree)
            sets = {}
            for k in (1, 2, 3, 4):
                gate.PARENT_K = k
                recs = gate.evaluate(pages, ctx, packs, pathlib.Path(a.assets))
                sets[k] = {(r['page'], r['line'], r['val']) for r in recs if r['verdict'] == 'failed'}
            same = all(sets[k] == sets[3] for k in sets)
            print(f"PARENT_K sweep on {name}: flags " + ', '.join(f'K={k}: {len(v)}' for k, v in sets.items())
                  + ('  (identical sets - the data cannot choose K)' if same else '  (SETS DIFFER)'))
        gate.PARENT_K = shipped['PARENT_K']
        # WIDENING: every pair whose set of expected families differs between the code before this item
        # (NUMERIC_CHILD off) and as shipped, on both docs trees. Each must be explained or is a defect.
        for name in ('37425a6', 'HEAD (working tree)'):
            pages = gate.scan_docs(trees[name])
            gate.NUMERIC_CHILD = False
            old = gate.evaluate(pages, ctx, packs, pathlib.Path(a.assets))
            gate.NUMERIC_CHILD = True
            new = gate.evaluate(pages, ctx, packs, pathlib.Path(a.assets))
            assert len(old) == len(new)
            diff = [(o, n) for o, n in zip(old, new) if (o['fams'], o['verdict']) != (n['fams'], n['verdict'])]
            print(f'WIDENING on {name}: {len(diff)} of {len(new)} pair(s) change families or verdict (NUMERIC_CHILD off -> on)')
            for o, n in diff:
                print(f"    {n['page']}:{n['line']} {'.'.join(n['path'])}={n['val']}: "
                      f"{'/'.join(o['fams']) or '-'} [{o['verdict']}] -> {'/'.join(n['fams']) or '-'} [{n['verdict']}]")
        gate.NUMERIC_CHILD = shipped['NUMERIC_CHILD']
    return rc


def why_untyped(gate, ctx, path):
    """What the gate's tables hold for a position, as numbers: the evidence behind an 'untyped' verdict."""
    sw = ctx.sweep
    k = path[-1]
    p = path[-2] if len(path) > 1 else None
    parts = []
    l2 = sw.L2.get((p, k), ()) if p is not None else ()
    parts.append(f'L2 {p}.{k}: {len(l2)} distinct shipped value(s)')
    parts.append(f'L1 {k}: {len(sw.L1.get((k,), ()))}')
    if p is not None and gate.IDENT.match(p):
        parts.append(f'LW {p}.*: {len(sw.LW.get((p, "*"), ()))}'
                     + (', key is a shipped child of the parent (the children guard stops the wildcard)'
                        if k in sw.children.get(p, ()) else ''))
        if gate.NUMKEY.match(k):
            parts.append(f'LN {p}.#: {len(sw.LN.get((p, "#"), ()))}')
    return '; '.join(parts)


def scope_report(gate, ctx, recs, den, hits, detail):
    """Recall over the denominator split by the DECLARED scope (SCOPE_BY_KEY / classify, fixed from the
    codecs before any verdict was read). A value under two keys counts once, in its strongest class
    (asset > gap > free). Prints hits and misses on each side; the subset figure is labelled and is NOT
    the figure the ~70% line is judged on."""
    hitset = set(hits)
    cls = {}         # value -> (class, set of (class, store, reason, 'parent.key'))
    unknown = []
    for v in den:
        rs = [r for r in recs if r['val'] == v and r['page'].startswith('interactions') and r['verdict'] != 'bad-placeholder']
        found = []
        for r in rs:
            try:
                c, store, why = classify(r['path'])
            except KeyError as e:
                unknown.append((v, r['path']))
                continue
            found.append((c, store, why, '.'.join(r['path'][-2:])))
        order = {'asset': 0, 'gap': 1, 'free': 2}
        best = min((f[0] for f in found), key=order.get) if found else None
        cls[v] = (best, found)
    if unknown:
        print(f'  FAIL  {len(unknown)} denominator position(s) are not in the declared-scope table: {unknown[:5]}')
        return 1
    n_unextracted = [v for v in den if cls[v][0] is None]
    if n_unextracted:
        print(f'  FAIL  {len(n_unextracted)} denominator value(s) carry no extracted pair: {n_unextracted[:5]}')
        return 1
    multi = [v for v in den if len({f[0] for f in cls[v][1]}) > 1]
    print(f'    DECLARED SCOPE (classified per key from the codecs before any verdict; a value under two keys counts once, '
          f'strongest class wins: asset > gap > free; {len(multi)} value(s) sit under keys of different classes: {", ".join(multi) or "none"})')
    for c, label in (('asset', 'names an ASSET (resolves, or should, in a setPath store)'),
                     ('free', 'FREE: any value is legal, out of the denominator'),
                     ('gap', 'NAMED GAP: a real reference that is not a file stem')):
        vs = [v for v in den if cls[v][0] == c]
        h = [v for v in vs if v in hitset]
        m = [v for v in vs if v not in hitset]
        print(f'      {c:5s} {len(vs):3d} distinct value(s): {len(h)} caught, {len(m)} missed   [{label}]')
        if detail:
            by_key = collections.defaultdict(lambda: [[], []])
            for v in vs:
                f = next(f for f in cls[v][1] if f[0] == c)
                pth, last = f[3], f[3].split('.')[-1]
                label = ('Flags.*' if pth.startswith('Flags.') else 'Next.<numeric>' if f[2].startswith('ChargingInteraction.Next')
                         else pth if last == 'Id' else last)
                by_key[(label, f[1], f[2])][0 if v in hitset else 1].append(v)
            for (k, store, why), (hh, mm) in sorted(by_key.items(), key=lambda kv: -len(kv[1][0]) - len(kv[1][1])):
                print(f'        {k:24s} {len(hh):2d} caught {len(mm):2d} missed  -> {store or "-"}: {why}')
                if mm:
                    print(f'            missed: {", ".join(sorted(mm))}')
    ast = [v for v in den if cls[v][0] == 'asset']
    print(f'    recall over the 120 (the figure the ~70% line judges): {pct(len(hitset & set(den)), len(den))}')
    print(f'    recall WITHIN DECLARED SCOPE (asset-naming positions only; never compared to the line): '
          f'{pct(len([v for v in ast if v in hitset]), len(ast))}')
    if detail:
        mc = []
        for v in den:
            if v in hitset:
                continue
            for r in recs:
                if r['val'] == v and r['page'].startswith('interactions') and r['verdict'] == 'untyped':
                    k = r['path'][-1]
                    p = r['path'][-2] if len(r['path']) > 1 else None
                    if p == 'Flags' or (p == 'Next' and gate.NUMKEY.match(k)) or k in (
                            'Forward', 'Back', 'ForwardLeft', 'ForwardRight', 'BackLeft', 'BackRight', 'Failed', 'Click', 'Held'):
                        mc.append((r['page'], r['line'], '.'.join(r['path']), v, why_untyped(gate, ctx, r['path'])))
        print(f'    MAP-CHILD / FIXED-CHILD-FIELD MISSES ({len(mc)}), each with the gate tables behind its untyped verdict:')
        for pg, ln, pth, v, why in sorted(mc):
            print(f'      {pg}:{ln} {pth}={v}\n          {why}')
    return 0


def measure(gate, ctx, packs, zip_stems, a, detail=True):
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        # ------------------------------------------------------------ (a)
        base = export_docs(REV_BASE, td / 'base')
        fix = export_docs(REV_FIX, td / 'fix')
        v_base, v_fix = json_fence_values(base), json_fence_values(fix)
        removed = {v for v in v_base if v not in v_fix}
        den = sorted(v for v in removed if ID_LIKE.match(v) and v not in zip_stems)
        print(f'\n(a) interactions: {len(v_base)} distinct json-fence values at {REV_BASE}, '
              f'{len(v_fix)} at {REV_FIX}; {len(removed)} removed; denominator = {len(den)} id-shaped, '
              f'match no stem in the 0.7.2 listing')
        recs_base = gate.evaluate(gate.scan_docs(base), ctx, packs, pathlib.Path(a.assets))
        recs_fix = gate.evaluate(gate.scan_docs(fix), ctx, packs, pathlib.Path(a.assets))
        flagged_base = {(r['page'], r['val']) for r in recs_base if r['verdict'] == 'failed'}
        # a flag counts as a hit only on the pages the denominator was drawn from
        flagged_vals = {v for p_, v in flagged_base if p_.startswith('interactions')}
        hits = [v for v in den if v in flagged_vals]
        miss = [v for v in den if v not in flagged_vals]
        print(f'    recall: {pct(len(hits), len(den))}')
        by_cause = collections.defaultdict(list)
        for v in miss:
            rs = [r for r in recs_base if r['val'] == v and r['page'].startswith('interactions')]
            if not rs:
                where = [p for p in sorted(v_base[v])]
                by_cause['extraction (no pair carried the value; fence value on ' + ','.join(where) + ')'].append(v)
                continue
            for r in rs:
                cause = r['verdict']
                if cause == 'untyped':
                    cause += ' key=' + r['path'][-1]
                by_cause[cause].append(v)
        for cause, vs in sorted(by_cause.items()):
            print(f'    miss, {cause}: {len(set(vs))} id(s): {", ".join(sorted(set(vs))[:8])}'
                  f'{" ..." if len(set(vs)) > 8 else ""}')
        kept_fix = {(r['page'], r['val']) for r in recs_fix if r['verdict'] == 'failed'}
        kept = sorted(f for f in flagged_base if f in kept_fix)
        print(f'    flags the gate raises on {REV_BASE} (any page): {len(flagged_base)} (page, id); '
              f'{len(kept)} of them still flagged at {REV_FIX}: '
              + ', '.join(f'{p}:{v}' for p, v in kept))
        extra = sorted(f for f in flagged_base if f[1] not in set(den) and f[0].startswith('interactions'))
        print(f'    flagged on interactions*.md but outside the denominator: {len(extra)}')
        for p, v in extra:
            r = next(r for r in recs_base if r['page'] == p and r['val'] == v and r['verdict'] == 'failed')
            print(f'      {p}:{r["line"]} {".".join(r["path"])}={v}  expects {"/".join(r["fams"])}; '
                  f'{"in 0.7.2 listing" if v in zip_stems else "absent from 0.7.2 listing"}; '
                  f'{"still in " + REV_FIX if (p, v) in kept_fix else "gone by " + REV_FIX}')
        if not den:
            print('  FAIL  empty denominator'); rc = 1
        a_recall = len(hits) / len(den) if den else 0.0
        if den:
            rc = scope_report(gate, ctx, recs_base, den, hits, detail=detail) or rc

        # ------------------------------------------------------------ (b)
        drops_old = export_docs(REV_DROPS_FIX + '^', td / 'dropsold')
        diff = git('show', REV_DROPS_FIX, '--', 'docs/drops.md')
        removed_lines = [ln[1:] for ln in diff.split('\n') if ln.startswith('-') and '"ItemId"' in ln]
        ids_removed = sorted({m for ln in removed_lines for m in re.findall(r'"ItemId"\s*:\s*"([^"]*)"', ln)})
        b26_names = [ln.split(' ', 1)[1] for ln in
                     git('show', f'{REV_BUILD26}:maintenance/baseline/ServerAssetsIndex.hashes').split('\n') if ' ' in ln]
        b26_stems = stems_from_names(b26_names)
        den_b = [i for i in ids_removed if i not in b26_stems]
        print(f'\n(b) drops: {REV_DROPS_FIX} removed {len(removed_lines)} "ItemId" line(s) carrying '
              f'{len(ids_removed)} distinct id(s); build-26 listing has {len(b26_stems)} stem(s); '
              f'denominator = {len(den_b)} id(s) matching no build-26 stem')
        recs_d = gate.evaluate(gate.scan_docs(drops_old), ctx, packs, pathlib.Path(a.assets))
        flagged_d = {r['val']: r for r in recs_d if r['verdict'] == 'failed' and r['page'] == 'drops.md'}
        hits_b = [i for i in den_b if i in flagged_d]
        print(f'    recall: {pct(len(hits_b), len(den_b))}')
        for i in den_b:
            if i in flagged_d:
                continue
            rs = [r for r in recs_d if r['val'] == i and r['page'] == 'drops.md']
            print(f'    miss {i}: ' + (', '.join(sorted({r["verdict"] + (" key=" + r["path"][-1] if r["verdict"] == "untyped" else "") for r in rs})) or 'not extracted'))
        print(f'    build skew: {sum(1 for i in den_b if i not in zip_stems)} of {len(den_b)} denominator ids are also absent from 0.7.2; '
              f'{sum(1 for i in ids_removed if i in b26_stems and i not in zip_stems)} removed ids exist in build-26 but not in 0.7.2')
        other = sorted(v for v in flagged_d if v not in den_b)
        print(f'    other flags on drops.md at {REV_DROPS_FIX}^ (outside the denominator): {len(other)}')
        for v in other:
            r = flagged_d[v]
            print(f'      drops.md:{r["line"]} {".".join(r["path"])}={v}; '
                  f'{"in build-26" if v in b26_stems else "absent from build-26"}, '
                  f'{"in 0.7.2" if v in zip_stems else "absent from 0.7.2"}')
        if not den_b:
            print('  FAIL  empty denominator'); rc = 1
        b_recall = len(hits_b) / len(den_b) if den_b else 0.0
    return rc, (a_recall, b_recall)


if __name__ == '__main__':
    sys.exit(main())
