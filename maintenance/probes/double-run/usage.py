#!/usr/bin/env python3
"""
usage.py -- which interaction types do the shipped NPC roles and ability chains reach?

Run:  python3 -I maintenance/probes/double-run/usage.py [--assets DIR] [--src DIR]

Reads the extracted Assets.zip (default ~/.cache/hytale-assets; read-only) and joins the counts
with census.py's `sim` label. The sample rule (item 13, R6) is fixed BEFORE any verdict is read:
  "the doubled types a shipped NPC role or ability chain uses; if more than 6, the 6 most used".
This script is the "most used" half: it prints, for every type whose simulation pass runs the same
work as the server pass (sim in firstRun, tick0, tick0+), how many objects of that type the NPC and
ability seeds reach. Whether a type is DOUBLED is read from its source afterwards (census.py does
not decide it).

THE GRAPH
  Nodes: a JSON file is a node named by its stem (the asset id) in these stores:
      Item/Interactions, Item/RootInteractions, ProjectileConfigs, Projectiles, Item/Items, Abilities.
  Edge: any JSON string value that equals a node's stem (this includes "Parent"). A stem used in
  two stores points to both (an over-count, never an under-count).
  Seeds: NPC = every file under Server/NPC. Ability = every file under Server/Abilities,
  Item/Interactions/Abilities and Item/RootInteractions/Abilities.
THE COUNT
  An OBJECT is a JSON object whose "Type" is a registered interaction type, or that has a "Parent"
  and no "Type" (then its type is its parent's, followed to the root). Objects are counted in every
  node in the interaction stores, and in any other file (NPC files, items, abilities) only inside an
  "Interactions" subtree (NPC files also use "Type" for sensors and actions, which share names with
  interaction types).
  usage(T) = distinct (file, json-path) objects of type T reachable from the seeds. Reported per
  seed set and for the union; the union orders the sample.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import census                       # noqa: E402

STORES = ['Item/Interactions', 'Item/RootInteractions', 'ProjectileConfigs', 'Projectiles', 'Item/Items', 'Abilities']
ABILITY_SEEDS = ['Abilities', 'Item/Interactions/Abilities', 'Item/RootInteractions/Abilities']


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def objects(o, path='', in_interactions=False):
    """Yield (path, obj, inside_an_Interactions_subtree) for every dict in o."""
    if isinstance(o, dict):
        yield path, o, in_interactions
        for k, v in o.items():
            yield from objects(v, f'{path}/{k}', in_interactions or k == 'Interactions')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from objects(v, f'{path}[{i}]', in_interactions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', default=str(pathlib.Path.home() / '.cache/hytale-assets'))
    ap.add_argument('--src', default=str(pathlib.Path.home() / '.cache/hytale-jar/src'))
    a = ap.parse_args()
    server = pathlib.Path(a.assets) / 'Server'
    if not (server / 'NPC').is_dir():
        print(f'FAIL  no {server}/NPC', file=sys.stderr)
        return 1

    # registered type names and their census sim labels
    tree = census.Tree(pathlib.Path(a.src))
    reg = census.interaction_registry(tree)
    sim_of = {}
    for s in reg.sites:
        simple, _ = census.class_arg(s, tree)
        fq = census.fq_from_arg(tree, s, simple)
        lab, _ = census.sim_pass(census.Chain(tree, fq))
        sim_of[s.name] = lab
    types = set(sim_of)

    nodes: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
    for st in STORES:
        for p in sorted((server / st).rglob('*.json')):
            nodes[p.stem].append(p)
    docs: dict[pathlib.Path, object] = {}

    def load(p):
        if p not in docs:
            try:
                docs[p] = json.loads(p.read_text())
            except Exception:
                docs[p] = None
        return docs[p]

    def files_under(rel):
        return sorted((server / rel).rglob('*.json'))

    interaction_files = {p for st in ('Item/Interactions', 'Item/RootInteractions', 'ProjectileConfigs', 'Projectiles')
                         for p in files_under(st)}
    npc_seeds = files_under('NPC')
    abil_seeds = [p for r in ABILITY_SEEDS for p in files_under(r)]
    print(f'assets: {str(server).replace(str(pathlib.Path.home()), "~")}')
    print(f'nodes: {sum(len(v) for v in nodes.values())} files in {len(nodes)} ids ({", ".join(STORES)})')
    print(f'seeds: NPC {len(npc_seeds)} files; ability {len(abil_seeds)} files')

    def type_of(obj, seen=()):
        t = obj.get('Type')
        if isinstance(t, str):
            return t if t in types else None
        par = obj.get('Parent')
        if isinstance(par, str) and par not in seen:
            for pf in nodes.get(par, []):
                d = load(pf)
                if isinstance(d, dict):
                    r = type_of(d, seen + (par,))
                    if r:
                        return r
        return None

    def reach(seeds):
        seen_files = set()
        stack = list(seeds)
        seed_set = set(seeds)
        counts = collections.Counter()
        objs = collections.defaultdict(set)
        while stack:
            p = stack.pop()
            if p in seen_files:
                continue
            seen_files.add(p)
            d = load(p)
            if d is None:
                continue
            for s in set(strings(d)):
                for q in nodes.get(s, []):
                    if q not in seen_files:
                        stack.append(q)
            for path, o, inside in objects(d):
                if p not in interaction_files and not inside:
                    continue
                t = type_of(o)
                if t:
                    objs[t].add((str(p), path))
        return {t: len(v) for t, v in objs.items()}, len(seen_files)

    npc, npc_files = reach(npc_seeds)
    abil, abil_files = reach(abil_seeds)
    print(f'reached files: NPC {npc_files}, ability {abil_files}')
    if not npc or not abil:
        print('FAIL  a seed set reached nothing')
        return 1
    union_t = set(npc) | set(abil)
    cand = [t for t in union_t if sim_of[t] in ('firstRun', 'tick0', 'tick0+')]
    print()
    print('Types reached, by objects (NPC / ability), with the census sim label.')
    print(f'{"type":28s} {"sim":10s} {"npc":>6s} {"abil":>6s} {"sum":>6s}')
    for t in sorted(union_t, key=lambda t: (-(npc.get(t, 0) + abil.get(t, 0)), t)):
        print(f'{t:28s} {sim_of[t]:10s} {npc.get(t, 0):6d} {abil.get(t, 0):6d} {npc.get(t, 0) + abil.get(t, 0):6d}')
    print()
    print(f'CANDIDATES: {len(cand)} reached types whose simulation pass runs the server pass\'s method '
          f'(sim firstRun/tick0/tick0+), most used first:')
    for t in sorted(cand, key=lambda t: (-(npc.get(t, 0) + abil.get(t, 0)), t)):
        print(f'  {t:28s} {sim_of[t]:8s} npc={npc.get(t, 0):4d} ability={abil.get(t, 0):4d}')
    unreached = sorted(t for t in types if t not in union_t)
    print()
    print(f'registered types never reached by either seed set: {len(unreached)} of {len(types)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
