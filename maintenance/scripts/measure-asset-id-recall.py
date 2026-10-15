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
FENCE = re.compile(r'^([ \t]*)```(\w*)[^\n]*\n(.*?)^[ \t]*```', re.M | re.S)
QUOTED = re.compile(r'"((?:[^"\\\n]|\\.)*)"')   # consumed left to right, so a closing quote never opens the next
ID_LIKE = re.compile(r'^[A-Za-z][A-Za-z0-9_.\-]*$')


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
                body = m.group(3)
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
    for widen in (True, False):
        gate.WIDEN = widen
        print(f"\n{'=' * 8} widening {'ON (as shipped)' if widen else 'OFF (the setting of the first docs run)'} {'=' * 8}")
        r, res = measure(gate, ctx, packs, zip_stems, a)
        rc = rc or r
        results[widen] = res
    for widen, (ra, rb) in results.items():
        print(f"RECALL widening {'ON ' if widen else 'OFF'}  (a) {ra:.0%}  (b) {rb:.0%}")
    return rc


def measure(gate, ctx, packs, zip_stems, a):
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
        recs_base = gate.evaluate(gate.scan_docs(base), ctx, packs)
        recs_fix = gate.evaluate(gate.scan_docs(fix), ctx, packs)
        flagged_base = {(r['page'], r['val']) for r in recs_base if r['verdict'] == 'failed'}
        flagged_vals = {v for _, v in flagged_base}
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
        recs_d = gate.evaluate(gate.scan_docs(drops_old), ctx, packs)
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
