#!/usr/bin/env python3
"""
usage.py -- which interaction types do chains that an NPC, an encounter or an ability runs actually reach?

Run:  python3 -I maintenance/probes/double-run/usage.py [--assets DIR] [--src DIR] [--check]

Reads the extracted Assets.zip (default ~/.cache/hytale-assets; read-only) and joins the counts with
census.py's `sim` and `wait` labels. It fixes the POPULATION of item 13b: the types whose double-run
behaviour the handbook classifies. It prints three things:

  1. the 13a population ("all-edges": every string equal to an asset id is an edge), 58 types at 0.7.2;
  2. the run-reached population: the same types, but an Item/Items id is an edge only when the item is HELD
     (the role's HotbarItems / OffHandItems, and the parameters they Compute from) and the item's root for one of
     the NPC AttackType keys is tagged `Attack` (ActionAttack.java:148-160). A string in AttractiveItemSet, Items,
     ProduceItem, HarvestInteractionRequiredItems, ... names an item and starts no chain;
  3. the item-only types: in 1 and not in 2, each with the shortest path that reaches it and the field its item edge sits in.

THE GRAPH
  Nodes: a JSON file is a node named by its stem (the asset id) in these stores:
      Item/Interactions, Item/RootInteractions, ProjectileConfigs, Projectiles, Abilities
  and, for the all-edges graph only, Item/Items. Edge: any JSON string value that equals a node's stem (this
  includes "Parent"). A stem used in two stores points to both (an over-count, never an under-count).
  Seeds: NPC = every file under Server/NPC. Encounter = every file under Server/EncounterManager. Ability =
  every file under Server/Abilities, Item/Interactions/Abilities and Item/RootInteractions/Abilities.
THE COUNT
  An OBJECT is a JSON object whose "Type" is a registered interaction type, or that has a "Parent" and no "Type"
  (then its type is its parent's, followed to the root). Objects are counted in every node in the interaction
  stores, and in any other file (NPC files, items, abilities) only inside an "Interactions" subtree (NPC files
  also use "Type" for sensors and actions, which share names with interaction types).
  usage(T) = distinct (file, json-path) objects of type T reachable from the seeds.
RUNS ON (item 13b, R6)
  Every state of the walk carries the manager the chain runs on, starting from its seed set:
      NPC         an NPC seed: the NPC's own manager (a projectile it fires runs ProjectileSpawn on it)
      encounter   an EncounterManager seed
      A-caster    an ability seed: the caster's manager. A player's has a remote client, so ONE pass
      host        under an object whose Type is SpawnInteraction: the host InteractionHost.spawnHost builds
      A-entity    under an object whose Type is SpawnAbilityEntity, LaunchAbilityProjectile or
                  SplitAbilityProjectile: the ability entity's or ability projectile's own manager, built
                  with `new InteractionManager(null, ...)` (AbilityEntitySpawner.java:59, AbilityProjectileLauncher.java:102).
                  Not the ProjectileSpawn chain of that projectile: it runs on the shooter's manager
                  (ProjectileModule.onProjectileSpawnInteraction, :206), so it keeps the caster's label
  A type reached only as A-caster runs on a player's manager and is outside the double run.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import census                       # noqa: E402

BASE_STORES = ['Item/Interactions', 'Item/RootInteractions', 'ProjectileConfigs', 'Projectiles', 'Abilities']
ITEM_STORE = 'Item/Items'
ABILITY_SEEDS = ['Abilities', 'Item/Interactions/Abilities', 'Item/RootInteractions/Abilities']
ATTACK_TYPES = ('Primary', 'Secondary', 'Ability1', 'Ability2', 'Ability3', 'Ability4')   # ActionAttack.AttackType
HELD_ROOT_KEYS = ('HotbarItems', 'OffHandItems')       # BuilderRole.java:280-281; the held-item fields of a role
CARRIERS = {'SpawnInteraction': 'host', 'SpawnAbilityEntity': 'A-entity', 'LaunchAbilityProjectile': 'A-entity',
            'SplitAbilityProjectile': 'A-entity'}
LABEL_OF_SEED = {'npc': 'NPC', 'encounter': 'encounter', 'ability': 'A-caster'}
# calls that write an inventory slot, found in a type's class chain (the held-slot walk, item 13b R2)
SLOT_WRITE_APIS = ('setActiveSlot', 'setItemStackForSlot', 'removeItemStackFromSlot', 'removeItemStack', 'addItemStack',
                   'addOrDropItemStack', 'moveItemStack', 'putItemStack', 'replaceItemStackInSlot')
# ModifyInventory's paths, read from ModifyInventoryInteraction.firstRun (file:line of the decompiled cache): field -> (the write, calls setHeldItem?)
MODIFY_INVENTORY_PATHS = {
    'ItemToRemove': ('combinedHotbarFirst.removeItemStack (:101)', False),
    'AdjustHeldItemQuantity': ('removeItemStackFromSlot then context.setHeldItem (:113); a positive value adds a stack (:115)', True),
    'ItemToAdd': ('addOrDropItemStack (:119)', False),
    'AdjustHeldItemDurability': ('setItemStackForSlot then context.setHeldItem (:145-149)', True),
}
# per-type fields whose value decides the outcome; counted over the run-reached objects (item 13b, R6)
FIELD_TABLE: dict[str, list[str]] = {
    'ChangeStat': ['Behaviour'],                                            # absent = Add (ChangeStatBaseInteraction.java:44)
    'Explode': ['Config.DamageEntities', 'Config.DamageBlocks'],            # absent = true, true (ExplosionConfig.java:79-80)
    'TriggerCooldown': ['Cooldown.Charges', 'UseAbilityCooldown'],          # absent Charges = DEFAULT_CHARGE_TIMES {0.0}: 1 charge (InteractionManager.java:81)
    'Repeat': ['Repeat'],                                                   # absent = 1
    'ApplyForce': ['Duration', 'ChangeVelocityType'],                       # absent Duration = 0, absent ChangeVelocityType = Set (ApplyForceInteraction.java:127)
    'ModifyInventory': ['RequiredGameMode'],
}


def home(s: object) -> str:
    return str(s).replace(str(pathlib.Path.home()), '~')


# ------------------------------------------------------------------ JSON walking

def walk(o, label, path='', inside=False, key=''):
    """Yield ('obj', path, dict, label, inside) for every dict, and ('str', value, label, key) for every string.
    A dict whose Type is a carrier hands its CHILDREN a different label (the manager its chains run on)."""
    if isinstance(o, str):
        yield ('str', o, label, key)
    elif isinstance(o, dict):
        yield ('obj', path, o, label, inside)
        t = o.get('Type')
        child = CARRIERS.get(t, label) if isinstance(t, str) else label
        for k, v in o.items():
            # an ability projectile's ProjectileSpawn chain runs on the shooter's manager (ProjectileModule.onProjectileSpawnInteraction, :206);
            # only its hit, miss and bounce chains run on the projectile's own manager (AbilityProjectileLauncher.java:102)
            lab = 'A-caster' if child == 'A-entity' and k == 'ProjectileSpawn' else child
            yield from walk(v, lab, f'{path}/{k}', inside or k == 'Interactions', k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, label, f'{path}[{i}]', inside, key)


class Assets:
    def __init__(self, server: pathlib.Path):
        self.server = server
        self.docs: dict[pathlib.Path, object] = {}
        self.base: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
        for st in BASE_STORES:
            for p in sorted((server / st).rglob('*.json')):
                self.base[p.stem].append(p)
        self.items: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
        for p in sorted((server / ITEM_STORE).rglob('*.json')):
            self.items[p.stem].append(p)
        self.interaction_files = {p for st in ('Item/Interactions', 'Item/RootInteractions', 'ProjectileConfigs', 'Projectiles')
                                  for p in self.files_under(st)}

    def files_under(self, rel):
        return sorted((self.server / rel).rglob('*.json'))

    def load(self, p):
        if p not in self.docs:
            try:
                self.docs[p] = json.loads(p.read_text())
            except Exception:
                self.docs[p] = None
        return self.docs[p]

    def rel(self, p):
        return str(pathlib.Path(p).relative_to(self.server))

    # --- items
    def item_chain(self, stem):
        """The item's file, then its Parent's, ... (a loop or a missing parent ends the chain)."""
        out, seen = [], set()
        while stem and stem not in seen and stem in self.items:
            seen.add(stem)
            d = self.load(self.items[stem][0])
            if not isinstance(d, dict):
                break
            out.append((stem, d))
            stem = d.get('Parent') if isinstance(d.get('Parent'), str) else None
        return out

    def item_roots(self, stem):
        """{AttackType key: root id} of the item, the child overriding its parents."""
        roots = {}
        for _, d in reversed(self.item_chain(stem)):
            ia = d.get('Interactions')
            if isinstance(ia, dict):
                roots.update({k: v for k, v in ia.items() if isinstance(v, str)})
        return roots

    def item_vars(self, stem):
        """The InteractionVars of the item and its parents, merged (the child's entry wins), as one dict."""
        merged = {}
        for _, d in reversed(self.item_chain(stem)):
            v = d.get('InteractionVars')
            if isinstance(v, dict):
                merged.update(v)
        return merged

    def root_tagged_attack(self, root_id):
        """True when the RootInteraction carries Tags.Attack (itself or through its Parent chain)."""
        seen = set()
        while isinstance(root_id, str) and root_id not in seen:
            seen.add(root_id)
            fs = [p for p in self.base.get(root_id, []) if 'Item/RootInteractions' in str(p)]
            if not fs:
                return False
            d = self.load(fs[0])
            if not isinstance(d, dict):
                return False
            tags = d.get('Tags')
            if isinstance(tags, dict) and 'Attack' in tags:
                return True
            root_id = d.get('Parent')
        return False


def held_items(a: Assets, npc_files):
    """Every item id a role holds, with the file and the path it sits at.
    A role names them in HotbarItems / OffHandItems, directly or by {"Compute": NAME}; NAME is then a
    parameter whose default is Parameters.NAME.Value and whose per-variant value is Modify.NAME. The
    field names are taken from the roles themselves, not listed here: every Compute under those two keys."""
    compute = set()
    docs = {}
    for p in npc_files:
        d = a.load(p)
        if not isinstance(d, dict):
            continue
        docs[p] = d
        for k in HELD_ROOT_KEYS:
            v = d.get(k)
            if isinstance(v, dict) and isinstance(v.get('Compute'), str):
                compute.add(v['Compute'])
    held = []     # (item stem, file, path)
    for p, d in docs.items():
        def take(lst, path):
            if isinstance(lst, list):
                for i, s in enumerate(lst):
                    if isinstance(s, str):
                        held.append((s, p, f'{path}[{i}]'))
        for k in HELD_ROOT_KEYS:
            take(d.get(k), '/' + k)
        for n in sorted(compute):
            mod = d.get('Modify')
            if isinstance(mod, dict):
                take(mod.get(n), f'/Modify/{n}')
            par = d.get('Parameters')
            if isinstance(par, dict) and isinstance(par.get(n), dict):
                take(par[n].get('Value'), f'/Parameters/{n}/Value')
    return held, sorted(compute)


# ------------------------------------------------------------------ the walk

def type_resolver(a: Assets, types):
    def type_of(obj, seen=()):
        t = obj.get('Type')
        if isinstance(t, str):
            return t if t in types else None
        par = obj.get('Parent')
        if isinstance(par, str) and par not in seen:
            for pf in a.base.get(par, []):
                d = a.load(pf)
                if isinstance(d, dict):
                    r = type_of(d, seen + (par,))
                    if r:
                        return r
        return None
    return type_of


def reach(a: Assets, types, seeds, item_edges, overrides=None):
    """seeds: [(path, label)]. item_edges: 'all' (an Item/Items id is a node), 'none'.
    overrides: {path: doc} replaces a file's document (a held item contributes only its InteractionVars).
    Returns (objs, parent, seen): objs[type] = {(file, objpath): {labels}}; parent[(file,label)] = (prev state, via string, key)."""
    type_of = type_resolver(a, types)
    overrides = overrides or {}
    seen: dict[tuple, tuple | None] = {}
    queue = collections.deque()
    for p, lab in seeds:
        if (p, lab) not in seen:
            seen[(p, lab)] = None
            queue.append((p, lab))
    objs: dict[str, dict] = collections.defaultdict(dict)
    while queue:
        p, lab = queue.popleft()
        d = overrides[p] if p in overrides else a.load(p)
        if d is None:
            continue
        done = set()
        for ev in walk(d, lab):
            if ev[0] == 'str':
                _, s, l2, key = ev
                if (s, l2) in done:
                    continue
                done.add((s, l2))
                targets = list(a.base.get(s, []))
                if item_edges == 'all':
                    targets += a.items.get(s, [])
                for q in targets:
                    if (q, l2) not in seen:
                        seen[(q, l2)] = ((p, lab), s, key)
                        queue.append((q, l2))
            else:
                _, path, o, l2, inside = ev
                if p not in a.interaction_files and not inside:
                    continue
                t = type_of(o)
                if t:
                    objs[t].setdefault((str(p), path), set()).add(l2)
    return objs, seen


def counts(objs):
    return {t: len(v) for t, v in objs.items()}


def explain(objs, seen, t):
    """The shortest chain of files from a seed to a file that holds an object of type t, with the key of every edge."""
    if t not in objs:
        return None
    (f, path), labs = sorted(objs[t].items())[0]
    state = (pathlib.Path(f), sorted(labs)[0])
    if state not in seen:
        state = next(s for s in seen if s[0] == pathlib.Path(f))
    steps = []
    while seen.get(state) is not None:
        prev, s, key = seen[state]
        steps.append((state[0], s, key))
        state = prev
    steps.append((state[0], None, None))
    steps.reverse()
    return steps, path


def analyse(server: pathlib.Path, types: set):
    """Everything the page's population needs, as plain data (also called by usage-test.py on a planted tree)."""
    a = Assets(server)
    npc_seeds = [(p, 'NPC') for p in a.files_under('NPC')]
    enc_seeds = [(p, 'encounter') for p in a.files_under('EncounterManager')]
    abil_seeds = [(p, 'A-caster') for r in ABILITY_SEEDS for p in a.files_under(r)]
    r = {'assets': a, 'n_npc': len(npc_seeds), 'n_enc': len(enc_seeds), 'n_abil': len(abil_seeds)}

    # 1. the 13a population: every string equal to an asset id is an edge, items included (NPC + ability seeds)
    objs_all, seen_all = reach(a, types, npc_seeds + abil_seeds, 'all')
    r['all_edges'] = counts(objs_all)
    r['all_objs'], r['all_seen'] = objs_all, seen_all

    # 2. the run-reached population
    held, compute = held_items(a, [p for p, _ in npc_seeds])
    held_ok, held_missing, held_no_attack, held_droplist = [], [], [], []
    extra_seeds, overrides = [], {}
    for stem, f, path in held:
        if stem.startswith('Droplist:'):
            held_droplist.append((stem, f, path))
            continue
        if stem not in a.items:
            held_missing.append((stem, f, path))
            continue
        roots = a.item_roots(stem)
        tagged = sorted({rid for k, rid in roots.items() if k in ATTACK_TYPES and a.root_tagged_attack(rid)})
        if not tagged:
            held_no_attack.append((stem, f, path))
            continue
        held_ok.append((stem, f, path, tagged))
        for rid in tagged:
            for q in a.base.get(rid, []):
                if 'Item/RootInteractions' in str(q):
                    extra_seeds.append((q, 'NPC'))
        ipath = a.items[stem][0]
        overrides[ipath] = {'InteractionVars': a.item_vars(stem)}
        extra_seeds.append((ipath, 'NPC'))
    run_seeds = npc_seeds + enc_seeds + abil_seeds + extra_seeds
    objs_run, seen_run = reach(a, types, run_seeds, 'none', overrides)
    r['run_objs'] = objs_run
    r['run'] = counts(objs_run)
    r['overrides'] = overrides
    r['held'] = {'fields': compute, 'strings': len(held), 'distinct': len({h[0] for h in held}), 'attack': held_ok,
                 'no_attack': held_no_attack, 'missing': held_missing, 'droplist': held_droplist}
    r['no_item_edges'] = counts(reach(a, types, npc_seeds + abil_seeds, 'none')[0])     # the 13a seeds, no Item/Items node at all
    # labels per type
    lab = collections.defaultdict(set)
    for t, v in objs_run.items():
        for ls in v.values():
            lab[t] |= ls
    r['labels'] = dict(lab)
    r['item_only'] = sorted(set(r['all_edges']) - set(r['run']))
    r['run_only'] = sorted(set(r['run']) - set(r['all_edges']))
    r['seeds_all'] = npc_seeds + abil_seeds
    r['types'] = types
    return r


def resolve_field(a: Assets, o, dotted: str):
    """The value of a (dotted) field on object o, looked up leaf-wise through its Parent chain (the child wins); None when no object in the chain sets it."""
    parts = dotted.split('.')
    cur, seen = o, set()
    while isinstance(cur, dict):
        v = cur
        for p in parts:
            v = v.get(p) if isinstance(v, dict) else None
            if v is None:
                break
        if v is not None:
            return v
        par = cur.get('Parent')
        if not isinstance(par, str) or par in seen:
            return None
        seen.add(par)
        cur = next((x for x in (a.load(pf) for pf in a.base.get(par, [])) if isinstance(x, dict)), None)
    return None


def object_at(a: Assets, f, path, overrides=None):
    d = (overrides or {}).get(pathlib.Path(f)) or a.load(pathlib.Path(f))
    o = d
    try:
        for tok in [x for x in path.replace('[', '/[').split('/') if x]:
            o = o[int(tok[1:-1])] if tok.startswith('[') else o[tok]
    except (KeyError, IndexError, TypeError):
        return None
    return o


def field_counts(a: Assets, types, objs_run, t, field, overrides=None, exposed_only=False):
    """Value of `field` on each distinct run-reached object of type t (dotted paths allowed; resolved leaf-wise through Parent); '(absent)' if none.
    exposed_only drops the objects reached only as an ability caster (a player's manager, one pass)."""
    out = collections.Counter()
    for (f, path), labs in objs_run.get(t, {}).items():
        if exposed_only and labs == {'A-caster'}:
            continue
        o = object_at(a, f, path, overrides)
        if o is None:
            out['(object not found)'] += 1
            continue
        val = resolve_field(a, o, field)
        out['(absent)' if val is None else json.dumps(val)] += 1
    return out


OUTCOMES = ('doubled', 'desync', 'refuses', 'same-twice', 'guarded', 'once', 'flow', 'reads', 'none', 'unknown')
BASES = ('measured', 'read')
MAX_UNKNOWN = 5      # item 13b R5: more than this fails the item


def check_table(tsv: pathlib.Path, src_root: pathlib.Path, run_types: set):
    """Re-check verdict-table.tsv against the run-reached population and the decompiled source. Returns (problems, rows).
    Problems: a run-reached type without a row, a row for a type that is not run-reached, a duplicate row, a word outside the vocabularies,
    a deciding hook that is not declared at the recorded line of the recorded file, more unknowns than MAX_UNKNOWN."""
    problems, rows, seen = [], [], set()
    if not tsv.exists():
        return [f'{tsv.name} does not exist'], rows
    for n, line in enumerate(tsv.read_text().split('\n'), 1):
        if not line.strip() or line.startswith('#'):
            continue
        c = line.split('\t')
        if len(c) != 8:
            problems.append(f'{tsv.name}:{n}: {len(c)} columns, wanted 8')
            continue
        t, outcome, basis, write, hook, file, ln, reason = c
        rows.append(dict(type=t, outcome=outcome, basis=basis, write=write, hook=hook, file=file, line=ln, reason=reason))
        if t in seen:
            problems.append(f'{tsv.name}:{n}: duplicate row for {t}')
        seen.add(t)
        if outcome not in OUTCOMES:
            problems.append(f'{tsv.name}:{n}: {t}: outcome {outcome!r} is not one of {", ".join(OUTCOMES)}')
        if basis not in BASES:
            problems.append(f'{tsv.name}:{n}: {t}: basis {basis!r} is not one of {", ".join(BASES)}')
        src = src_root / 'com/hypixel/hytale' / file
        try:
            text = src.read_text().split('\n')
            ok = re.search(r'\bvoid ' + re.escape(hook) + r'\(', text[int(ln) - 1]) is not None
        except (OSError, ValueError, IndexError):
            ok = False
        if not ok:
            problems.append(f'{tsv.name}:{n}: {t}: {file}:{ln} does not declare {hook}( (the source moved or the row is wrong)')
    for t in sorted(run_types - seen):
        problems.append(f'run-reached type {t} has no row in {tsv.name}')
    for t in sorted(seen - run_types):
        problems.append(f'{tsv.name} has a row for {t}, which is not run-reached')
    unknown = [r['type'] for r in rows if r['outcome'] == 'unknown']
    if len(unknown) > MAX_UNKNOWN:
        problems.append(f'{len(unknown)} unknown verdicts ({", ".join(unknown)}), more than {MAX_UNKNOWN}')
    return problems, rows


def modify_inventory_walk(a: Assets, run_objs, overrides):
    """Every run-reached ModifyInventory object, with the fields that write a slot (resolved through Parent), its RequiredGameMode gate and
    OnItemChangeBehavior, and what follows by the rule of the held-slot walk. Returns (rows, Counter of kinds)."""
    rows, tot = [], collections.Counter()
    for (f, path) in sorted(run_objs.get('ModifyInventory', {})):
        d = (overrides or {}).get(pathlib.Path(f)) or a.load(pathlib.Path(f))
        o = d
        try:
            for tok in [x for x in path.replace('[', '/[').split('/') if x]:
                o = o[int(tok[1:-1])] if tok.startswith('[') else o[tok]
        except (KeyError, IndexError, TypeError):
            tot['object not found'] += 1
            continue

        def get(name, o=o):
            cur, seen = o, set()
            while isinstance(cur, dict):
                if name in cur:
                    return cur[name]
                par = cur.get('Parent')
                if not isinstance(par, str) or par in seen:
                    return None
                seen.add(par)
                cur = next((x for x in (a.load(pf) for pf in a.base.get(par, [])) if isinstance(x, dict)), None)
            return None
        gate = get('RequiredGameMode')
        beh = get('OnItemChangeBehavior') or 'ItemChanged (the default)'
        active = [k for k in MODIFY_INVENTORY_PATHS if get(k) not in (None, 0, 0.0)]
        writes_no_held = [k for k in active if not MODIFY_INVENTORY_PATHS[k][1]]
        if gate is not None:
            kind, verdict = 'inert (RequiredGameMode)', f'inert: RequiredGameMode {gate} and no Player component, returns before any write (ModifyInventoryInteraction.java:97)'
        elif not active:
            kind, verdict = 'no write', 'no write'
        elif not writes_no_held:
            kind, verdict = 'setHeldItem only', 'writes through context.setHeldItem: never trips the check; the effect is doubled (measured InvAdjSelf1) unless the stack is exhausted'
        elif beh == 'Ignore':
            kind, verdict = 'slot write, Ignore', 'writes the slot without setHeldItem, Ignore: no check, doubled'
        else:
            kind, verdict = 'CANDIDATE', f'CANDIDATE: writes {writes_no_held} without setHeldItem, behaviour {beh}, wait Server: desync when owner == entity'
        tot[kind] += 1
        rows.append((f, path, active, gate, beh, kind, verdict))
    return rows, tot


def registry(src: pathlib.Path):
    tree = census.Tree(src)
    reg = census.interaction_registry(tree)
    info = {}
    for s in reg.sites:
        simple, _ = census.class_arg(s, tree)
        fq = census.fq_from_arg(tree, s, simple)
        ch = census.Chain(tree, fq)
        lab, _ = census.sim_pass(ch)
        w, _ = census.wait_of(ch)
        writes = {api for c in ch.classes for api in SLOT_WRITE_APIS if re.search(r'\.' + api + r'\(|\b' + api + r'\(', c.masked[c.body_start:c.body_end])}
        holds = any(re.search(r'\bsetHeldItem\(', c.masked[c.body_start:c.body_end]) for c in ch.classes)
        info[s.name] = (lab, w, writes, holds)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', default=str(pathlib.Path.home() / '.cache/hytale-assets'))
    ap.add_argument('--src', default=str(pathlib.Path.home() / '.cache/hytale-jar/src'))
    ap.add_argument('--table', default=str(HERE / 'verdict-table.tsv'), help='the verdict table to check against the population (default: verdict-table.tsv)')
    args = ap.parse_args()
    server = pathlib.Path(args.assets) / 'Server'
    if not (server / 'NPC').is_dir():
        print(f'FAIL  no {home(server)}/NPC', file=sys.stderr)
        return 1
    info = registry(pathlib.Path(args.src))
    types = set(info)
    r = analyse(server, types)
    a = r['assets']
    allc, run, lab = r['all_edges'], r['run'], r['labels']
    print(f'assets: {home(server)}')
    print(f'registered interaction types: {len(types)}')
    print(f'nodes: {sum(len(v) for v in a.base.values())} files in {len(a.base)} ids ({", ".join(BASE_STORES)}); '
          f'{sum(len(v) for v in a.items.values())} item files in {len(a.items)} ids ({ITEM_STORE}, an edge target in the all-edges graph only)')
    print(f'seeds: NPC {r["n_npc"]} files; encounter {r["n_enc"]}; ability {r["n_abil"]}')
    if not allc or not run or not r['n_npc'] or not r['n_abil']:
        print('FAIL  a seed set or a population is empty')
        return 1

    print()
    print('1. THE 13a POPULATION (every string equal to an asset id is an edge, items included; NPC + ability seeds)')
    print(f'   {len(allc)} of {len(types)} registered types reached; ModifyInventory {allc.get("ModifyInventory", 0)} objects, ChangeStat {allc.get("ChangeStat", 0)}')

    h = r['held']
    print()
    print('2. THE RUN-REACHED POPULATION')
    print('   An Item/Items id is an edge only when the item is held and its root for an AttackType key is tagged Attack (ActionAttack.java:148-160).')
    print(f'   held-item fields: {", ".join(HELD_ROOT_KEYS)}, and the parameters they Compute from: {", ".join(h["fields"])}')
    print(f'   held-item strings in NPC files: {h["strings"]} ({h["distinct"]} distinct): {len(h["attack"])} with an Attack-tagged root '
          f'({len({x[0] for x in h["attack"]})} distinct items), {len(h["no_attack"])} with no Attack-tagged root, '
          f'{len(h["droplist"])} droplist references, {len(h["missing"])} not an item id')
    ni = r['no_item_edges']
    print(f'   with no item edge at all (the 13a seeds): {len(ni)} types; ModifyInventory {ni.get("ModifyInventory", 0)} objects, ChangeStat {ni.get("ChangeStat", 0)}; '
          f'{len(set(allc) - set(ni))} of the {len(allc)} fall out: {", ".join(sorted(set(allc) - set(ni)))}')
    print(f'   held weapons and off-hand items with an Attack-tagged root bring back {len(set(run) & (set(allc) - set(ni)))}: '
          f'{", ".join(sorted(set(run) & (set(allc) - set(ni)))) or "none"}')
    print(f'   run-reached: {len(run)} of {len(types)} types; ModifyInventory {run.get("ModifyInventory", 0)} objects, ChangeStat {run.get("ChangeStat", 0)}')
    print(f'   item-only (in 1, not in 2): {len(r["item_only"])}; in 2 and not in 1: {len(r["run_only"])}')
    print(f'   not reached by either: {len(types - set(allc) - set(run))}')

    # sensitivity lines the item brief asked for
    server_dirs = {}
    for extra in ('EncounterManager', 'WorldEvent'):
        objs, _ = reach(a, types, r['seeds_all'] + [(p, 'NPC') for p in a.files_under(extra)], 'all')
        server_dirs[extra] = sorted(set(counts(objs)) - set(allc))
    print(f'   seeds added to 1: EncounterManager adds types {server_dirs["EncounterManager"] or "none"}; WorldEvent adds {server_dirs["WorldEvent"] or "none"}')
    nt = [(p, l) for p, l in r['seeds_all']]
    a2 = Assets(server)
    for st in list(a2.base):
        a2.base[st] = [p for p in a2.base[st] if 'Item/Interactions/Tests' not in str(p)]
    lost = sorted(set(allc) - set(counts(reach(a2, types, nt, 'all')[0])))
    print(f'   dropping Item/Interactions/Tests from the nodes loses types: {lost or "none"}')

    print()
    print('   type                         sim        wait    runs on                               npc  enc abil  sum  all-edges')
    rows = sorted(run, key=lambda t: (-sum(len(v) for v in [r["run_objs"][t]]), t))
    for t in rows:
        cnt = collections.Counter()
        for ls in r['run_objs'][t].values():
            for l in ls:
                cnt[l] += 1
        # objects per seed set: an object reached under two labels counts under each
        npc = cnt['NPC'] + cnt['host']
        enc = cnt['encounter']
        ab = cnt['A-caster'] + cnt['A-entity']
        print(f'   {t:28s} {info[t][0]:10s} {info[t][1]:7s} {",".join(sorted(lab[t])):36s} {npc:4d} {enc:4d} {ab:4d} {run[t]:4d}  {allc.get(t, 0):4d}')

    print()
    only_caster = sorted(t for t in run if lab[t] == {'A-caster'})
    print(f'   runs on a player\'s manager only (A-caster, one pass; outside the double run unless an NPC casts it): {len(only_caster)}: {", ".join(only_caster) or "none"}')
    exposed = sorted(set(run) - set(only_caster))
    print(f'   on a manager with no remote client (NPC, encounter, host, A-entity): {len(exposed)}')

    print()
    print(f'3. ITEM-ONLY TYPES ({len(r["item_only"])}): reached from a seed only through a string that names an item')
    for t in r['item_only']:
        ex = explain(r['all_objs'], r['all_seen'], t)
        if ex is None:
            print(f'   {t:26s} (no path)')
            continue
        steps, path = ex
        chain = ' > '.join(f'{a.rel(f)}' + (f' [{k}={s}]' if s else '') for f, s, k in steps)
        item_key = next((k for f, s, k in steps if s and s in a.items), '?')
        print(f'   {t:26s} item edge in field {item_key}')
        print(f'       {chain}   object at {path}')
    if r['run_only']:
        print(f'   in the run-reached population and not in 1: {r["run_only"]}')

    print()
    print('4. PER-FIELD COUNTS over the run-reached objects (distinct file+path; the value resolved through Parent), then over those not reached only as an ability caster')
    for t, fields in FIELD_TABLE.items():
        for f in fields:
            c = field_counts(a, types, r['run_objs'], t, f, r['overrides'])
            e = field_counts(a, types, r['run_objs'], t, f, r['overrides'], exposed_only=True)
            print(f'   {t}.{f}: ' + ', '.join(f'{k}={v}' for k, v in sorted(c.items())) + f'  (total {sum(c.values())}); on a manager with no remote client: '
                  + ', '.join(f'{k}={v}' for k, v in sorted(e.items())) + f'  (total {sum(e.values())})')

    print()
    print('5. THE HELD-SLOT WALK (item 13b, R2): run-reached operations that write an inventory slot')
    writers = sorted(t for t in run if info[t][2])
    print(f'   scanned the class chain of each of the {len(run)} run-reached types for {", ".join(SLOT_WRITE_APIS)}: {len(writers)} write: '
          + (", ".join(f"{t} ({', '.join(sorted(info[t][2]))})" for t in writers) or 'none'))
    indirect = sorted(t for t in run if info[t][3] and t not in writers)
    print(f'   types that call context.setHeldItem but make no direct slot write above: {", ".join(indirect) or "none"} (their writes go through BlockPlaceUtils; read: PlaceBlock needs the client\'s block position and a block interaction\'s server hook runs once, so neither doubles a slot write)')
    print('   the item-change check (Interaction.tickInternal, :288-291) trips when the item in the slot no longer matches context.getHeldItem(), the')
    print('   OnItemChangeBehavior is not Ignore, and the context is not a proxy (owner != entity). A write that calls context.setHeldItem keeps')
    print('   the context in step and never trips it. Fail and Finish run the hook anyway (tickInternal returns false); only ItemChanged skips it.')
    rows, tot = modify_inventory_walk(a, r['run_objs'], r['overrides'])
    for t in writers:
        if t != 'ModifyInventory':
            print(f'   {t}: not analysed here (no field table); read its class')
    for f, path, active, gate, beh, kind, verdict in rows:
        print(f'   {a.rel(f)} {path}: fields {active or "-"}, gate {gate}, behaviour {beh}: {verdict}')
    print('   walk total: ' + ', '.join(f'{k} {v}' for k, v in sorted(tot.items())) + f'  (of {sum(tot.values())} ModifyInventory objects; EquipItem and ChangeActiveSlot write the slot too but are item-only, not run-reached)')

    cand = [t for t in run if info[t][0] in ('firstRun', 'tick0', 'tick0+')]
    print()
    print(f'CANDIDATES: {len(cand)} run-reached types whose simulation pass runs the server pass\'s method (sim firstRun/tick0/tick0+)')
    print(f'   ' + ', '.join(sorted(cand)))
    print()
    problems, trows = check_table(pathlib.Path(args.table), pathlib.Path(args.src), set(run))
    byo = collections.Counter(x['outcome'] for x in trows)
    byb = collections.Counter(x['basis'] for x in trows)
    print(f'6. VERDICT TABLE ({pathlib.Path(args.table).name}): {len(trows)} rows for {len(run)} run-reached types; outcomes ' + ', '.join(f'{k} {v}' for k, v in sorted(byo.items())) + '; basis ' + ', '.join(f'{k} {v}' for k, v in sorted(byb.items())))
    for p in problems:
        print(f'   PROBLEM  {p}')
    print(f'   unknown: {byo.get("unknown", 0)} (limit {MAX_UNKNOWN}); {len(problems)} problem(s)')
    print()
    print(f'registered types never reached by either population: {len(types - set(allc) - set(run))} of {len(types)}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
