#!/usr/bin/env python3
"""
usage-mutations.py -- is every guard added to usage.py by the review of b0b119a..c4e97d1 tested by usage-test.py?

    python3 -I maintenance/probes/double-run/usage-mutations.py WORKDIR [FROM TO] [--assets DIR] [--src DIR]

For each guard it writes a copy of usage.py with that one guard deleted (the text patch is the guard, named below) and runs usage-test.py against the copy: the
test must go red (exit 1 or 2, or a crash). A mutation that leaves the test green means the test is not about that guard. The unmutated copy is the identity
control: it must exit 0, else every verdict below proves nothing, and the run is VOID. Each patch must also apply: a patch whose text is no longer in
usage.py is an error, not a skipped mutation (a guard that was reworded is a guard nobody tests).

WORKDIR must be absent, empty, or carry the marker .double-run-usage-mutations. FROM TO (1-based, inclusive) run a slice; one run of usage-test.py takes about 14 s.
--assets and --src are passed to every usage-test.py run (item 14: verify-docs.sh hands over its own caches; the defaults are the usual ones).
The last line is `---- B survived or failed to apply, C caught (of the slice FROM..TO of N)`. A caller that wants every guard tested reads C == N and N at
least its floor: a MUTATIONS emptied to nothing prints `slice 1..0 of 0` and exits 0, which says nothing about any guard.
"""
from __future__ import annotations
import argparse, pathlib, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
MARK = '.double-run-usage-mutations'

# (name, old text, new text): each old text occurs exactly once in usage.py
MUTATIONS = [
    ('MINOR-2 by_definer: a key already claimed by a nearer file is credited again to its parents', "            claimed |= set(v)\n", "            pass\n"),
    ('MINOR-2 analyse: an item\'s vars are credited to the held item\'s own file (the old keying)',
     "        for dpath, dvars in a.by_definer(stem, 'InteractionVars'):\n",
     "        for dpath, dvars in [(a.items[stem][0], a.item_vars(stem))]:\n"),
    ('MAJOR-1 collision route not seeded', "    routes['collision'] = {'seeds': sd, 'overrides': ov}\n", "    routes['collision'] = {'seeds': [], 'overrides': {}}\n"),
    ('MAJOR-1 block-break route not seeded', "    routes['blockbreak'] = {'seeds': sd, 'overrides': ov}\n", "    routes['blockbreak'] = {'seeds': [], 'overrides': {}}\n"),
    ('MAJOR-1 stat route not seeded', "    routes['stat'] = {'seeds': sd, 'overrides': ov}\n", "    routes['stat'] = {'seeds': [], 'overrides': {}}\n"),
    ('MAJOR-1 volume route not seeded', "        seeds += [(q, label) for q in files]\n", "        pass\n"),
    ('MAJOR-1 held route not seeded', "            seeds.append((dpath, label))\n            hits.append(", "            hits.append("),
    ('MAJOR-1 volume predicate: every volume counts (a Player-only volume is an NPC chain)', "    return any(str(t).lower() == 'npc' for t in (target_types or [])) or event == 'SIGNAL_RECEIVED'",
     "    return True"),
    ('MAJOR-1 volume predicate: a signal does not reach an NPC', "    return any(str(t).lower() == 'npc' for t in (target_types or [])) or event == 'SIGNAL_RECEIVED'",
     "    return any(str(t).lower() == 'npc' for t in (target_types or []))"),
    ('MAJOR-1 volume predicate: TargetTypes is not read', "    return any(str(t).lower() == 'npc' for t in (target_types or [])) or event == 'SIGNAL_RECEIVED'",
     "    return event == 'SIGNAL_RECEIVED'"),
    ('MAJOR-1 volume TargetTypes taken from the file, not the nearest enclosing object', "            if isinstance(o.get('TargetTypes'), list):\n                tt = [str(x) for x in o['TargetTypes']]\n",
     "            if isinstance(o.get('TargetTypes'), list) and path == '':\n                tt = [str(x) for x in o['TargetTypes']]\n"),
    ('MAJOR-1 occurrences: a state variant\'s own Interactions are not looked for', "            for v in o.values():\n                find(v)\n        elif isinstance(o, list):\n            for v in o:\n                find(v)\n    find(doc)\n    return out",
     "            pass\n        elif isinstance(o, list):\n            pass\n    find(doc)\n    return out"),
    ('MAJOR-1 block route: one document per file, whatever the route', "                ov[(p, label)] = {'Occurrences': occ}\n", "                ov[p] = {'Occurrences': occ}\n"),
    ('MAJOR-1 doc_of: the label is not used to pick the document', "        if (p, l) in (overrides or {}):\n            return overrides[(p, l)]\n", "        if False:\n            return overrides[(p, l)]\n"),
    ('MAJOR-1 death check: every DeathInteraction counts as reached', "any(s_[0] == q for s_ in seen_run for q in a.base.get(rid, []))", "True"),
    ('MINOR-3 check_table: the deciding file need not be in the class chain', "            if file not in files:\n", "            if False:\n"),
    ('MINOR-3 check_table: an outcome may sit on any sim label', "            if ok_sims is not None and sim_class(sim) not in ok_sims:\n", "            if False:\n"),
    ('MINOR-3 check_table: a name that is not a registered type is not reported', "            problems.append(f'{tsv.name}:{n}: {t} is not a registered interaction type')\n", "            pass\n"),
    ('MINOR-3 sim_class: via-<hook>:<kind> labels are compared whole', "    return re.sub(r'^via-[^:]+:', 'via-*:', label)", "    return label"),
    ('item 14 --tables: a FILE inside the repository is written', "        if out == repo or repo in out.parents:\n", "        if False:\n"),
    ('item 14 --tables: the verdict table can be named as FILE', "        if out == pathlib.Path(args.table).resolve():\n", "        if False:\n"),
    ('item 14 --tables: FILE is not resolved (a symlink to the repository or to the table passes)', "        out, repo = pathlib.Path(args.tables).resolve(), HERE.parents[2]\n",
     "        out, repo = pathlib.Path(args.tables).absolute(), HERE.parents[2]\n"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('slice', nargs='*', type=int, help='FROM TO')
    ap.add_argument('--assets', default=str(pathlib.Path.home() / '.cache/hytale-assets'))
    ap.add_argument('--src', default=str(pathlib.Path.home() / '.cache/hytale-jar/src'))
    args = ap.parse_args()
    if not args.work.startswith('/') or len(args.slice) not in (0, 2):
        print('usage: usage-mutations.py ABSOLUTE_WORKDIR [FROM TO] [--assets DIR] [--src DIR]', file=sys.stderr)
        return 3
    work = pathlib.Path(args.work).resolve()
    lo, hi = args.slice if args.slice else (1, len(MUTATIONS))
    if work.exists() and not (work / MARK).exists() and (not work.is_dir() or any(work.iterdir())):
        print(f'FAIL  {work} exists, is not empty and has no marker; give a new path', file=sys.stderr)
        return 3
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    (work / MARK).write_text('')
    src = (HERE / 'usage.py').read_text()
    # the copy keeps the repo's depth (census.py finds maintenance/scripts two levels up from its own directory)
    tree = work / 'maintenance/probes/double-run'
    tree.mkdir(parents=True)
    (work / 'maintenance/scripts').symlink_to(HERE.parents[1] / 'scripts')

    def run(text, name):
        for f in ('census.py', 'usage-test.py', 'verdict-table.tsv'):
            shutil.copy(HERE / f, tree / f)
        (tree / 'usage.py').write_text(text)
        r = subprocess.run([sys.executable, '-I', str(tree / 'usage-test.py'), str(work / 'ut'), '--assets', args.assets, '--src', args.src], capture_output=True, text=True, timeout=300)
        shutil.rmtree(work / 'ut', ignore_errors=True)
        first = next((l for l in r.stdout.split('\n') if l.startswith(('FAIL', 'VOID'))), r.stderr.strip().split('\n')[-1] if r.stderr.strip() else '')
        return r.returncode, first

    rc, first = run(src, 'identity')
    if rc != 0:
        print(f'VOID  the unmutated copy of usage.py is not green on usage-test.py (rc {rc}: {first})')
        return 2
    print('identity: green')
    bad = caught = 0
    for n, (name, old, new) in enumerate(MUTATIONS, 1):
        if not lo <= n <= hi:
            continue
        if src.count(old) != 1:
            print(f'ERROR     #{n} {name}: the patch text occurs {src.count(old)} time(s) in usage.py, wanted 1')
            bad += 1
            continue
        rc, first = run(src.replace(old, new), name)
        if rc == 0:
            print(f'SURVIVED  #{n} {name}')
            bad += 1
        else:
            caught += 1
            print(f'CAUGHT    #{n} {name}  (rc {rc}: {first[:150]})')
    print(f'---- {bad} survived or failed to apply, {caught} caught (of the slice {lo}..{hi} of {len(MUTATIONS)})')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
