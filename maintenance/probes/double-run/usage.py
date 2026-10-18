#!/usr/bin/env python3
"""
usage.py -- which interaction types do chains that an NPC, an encounter or an ability runs actually reach?

Run:  python3 -I maintenance/probes/double-run/usage.py [--assets DIR] [--src DIR] [--table FILE] [--tables FILE]

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
  usage(T) = distinct (file, json-path) objects of type T reachable from the seeds. The file is the one that DEFINES the
  object: a held item's InteractionVars come from the item and its Parent chain, and each var is credited to the nearest
  file that defines it, so a template shared by two held items is counted once (review of b0b119a..c4e97d1, MINOR-2).
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
CHAIN-START ROUTES THAT NO ASSET STRING NAMES (review of b0b119a..c4e97d1, MAJOR-1)
  Some chains are started by the engine on an entity's own manager from a field of a block, a stat or a volume, not from
  an NPC file. Each is a seed with its own label, and each was read in the source before it was added (ROUTES below):
      NPC collision       Collision, CollisionEnter and CollisionLeave of a block or fluid (CollisionResult.java:285-338)
      NPC block break     OnBreak and OnBreakImpact of a block, run on the breaker's manager (BlockHarvestUtils.java:849-880)
      NPC stat effect     Min/MaxValueEffects.Interactions of an entity stat (EntityStatsSystems.java:244-336)
      NPC trigger volume  RunRootInteraction effects of a volume that targets NPCs, or that a signal runs on its actor
      NPC held item       Held, HeldOffhand, Equipped of an item an NPC holds or wears (NPCInteractionSystems.java:49-55)
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
WORN_ROOT_KEYS = HELD_ROOT_KEYS + ('Armor',)           # BuilderRole.java:284: the armor an NPC wears (Equipped chains run per armor slot)
ITEM_CHAIN_KEYS = ('Held', 'HeldOffhand', 'Equipped')  # InteractionType keys NPCInteractionSystems.TickHeldInteractionsSystem starts every tick
CARRIERS = {'SpawnInteraction': 'host', 'SpawnAbilityEntity': 'A-entity', 'LaunchAbilityProjectile': 'A-entity',
            'SplitAbilityProjectile': 'A-entity'}
LABEL_OF_SEED = {'npc': 'NPC', 'encounter': 'encounter', 'ability': 'A-caster'}
# Chain-start routes that no asset string names (MAJOR-1 of the review of b0b119a..c4e97d1). name -> (label, what starts the chain, the lines that decide it).
# Every route runs the chain on an NPC's own manager (new InteractionManager(null, NPCInteractionSimulationHandler), NPCInteractionSystems.java:83)
# or, for a block break by nothing with a manager, on a host. A player's manager has a remote client; the same fields run there in one pass.
ROUTES = {
    'collision': ('NPC collision', 'Collision, CollisionEnter and CollisionLeave of the block or fluid an NPC moves into: MotionControllerBase.processTriggers '
                  '(:1138, EnableTriggers defaults to true, :142) -> CollisionResult.defaultTriggerBlocksProcessing (:262-334, living entities only) -> '
                  'doCollisionInteraction (:336) on the colliding entity\'s own manager'),
    'blockbreak': ('NPC block break', 'OnBreak and OnBreakImpact of a block an NPC breaks (DestroyBlock, BreakBlock, Explode): BlockHarvestUtils.fireOnBreakInteraction '
                   '(:849) -> queueBlockInteraction (:863) runs it on the breaker\'s manager, or on a host when the breaker has none (:872)'),
    'stat': ('NPC stat effect', 'MinValueEffects and MaxValueEffects Interactions of an entity stat: EntityStatsSystems.Changes (:244, every living entity with a '
             'manager, :251) -> runInteractions (:327-336) on the entity\'s own manager. Every living entity carries every stat type (EntityStatMap.update)'),
    'volume': ('NPC trigger volume', 'RunRootInteraction effects (RunRootInteractionEffect.java:41-64) run on TriggerContext.getEntityRef(), the entity that triggered the '
               'volume. A volume\'s TargetTypes decide which (TriggerVolumeTickingSystem.java:344,785-801: anything that is not a player, an item drop or '
               'a projectile is NPC), and a queued SIGNAL_RECEIVED has no target filter, its actor being whoever sent the signal (TriggerVolumeManager.enqueueVolumeEvent), '
               'an NPC through the SignalNearbyVolumes interaction or the SignalTaggedVolumes action'),
    'held': ('NPC held item', 'Held, HeldOffhand and Equipped of the item an NPC holds or wears: NPCInteractionSystems.TickHeldInteractionsSystem (:49-55) -> '
             'InteractionManager.tryRunHeldInteraction (:1177) every tick'),
}
ROUTE_LABELS = tuple(v[0] for v in ROUTES.values())
EXPOSED_NOT = ('A-caster',)          # the only label that is outside the double run (a player casts: a remote client, one pass)
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
    'TriggerSpawnMarkers': ['Count'],                                       # absent = 0: every eligible marker (TriggerSpawnMarkersInteraction.java:58); above 0 a reservoir sample runs in each pass (:69)
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

    def by_definer(self, stem, field, keys=None):
        """[(file, {key: value})] for the item and its Parent chain: each key of `field` (InteractionVars, or Interactions restricted to `keys`) is credited
        to the nearest file in the chain that defines it, the one whose value wins in the merge. An object is then keyed by the file that DEFINES it, so a
        template shared by two held items is one object, not one per child (review of b0b119a..c4e97d1, MINOR-2)."""
        claimed, out = set(), []
        for s, d in self.item_chain(stem):
            v = d.get(field)
            if not isinstance(v, dict):
                continue
            mine = {k: x for k, x in v.items() if k not in claimed and (keys is None or k in keys)}
            claimed |= set(v)
            if mine:
                out.append((self.items[s][0], mine))
        return out

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


def held_items(a: Assets, npc_files, keys=HELD_ROOT_KEYS):
    """Every item id a role holds (or, with keys=WORN_ROOT_KEYS, holds or wears), with the file and the path it sits at.
    A role names them in HotbarItems / OffHandItems, directly or by {"Compute": NAME}; NAME is then a
    parameter whose default is Parameters.NAME.Value and whose per-variant value is Modify.NAME. The
    field names are taken from the roles themselves, not listed here: every Compute under those keys."""
    compute = set()
    docs = {}
    for p in npc_files:
        d = a.load(p)
        if not isinstance(d, dict):
            continue
        docs[p] = d
        for k in keys:
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
        for k in keys:
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

def doc_of(a: 'Assets', overrides, p, labels=()):
    """The document the walk reads for file p. An override is keyed by (file, label) when it belongs to one route (a block that carries both a Collision and
    an OnBreak chain is two seeds with two labels and two documents), or by the file alone (a held item's InteractionVars)."""
    p = pathlib.Path(p)
    for l in sorted(labels):
        if (p, l) in (overrides or {}):
            return overrides[(p, l)]
    if p in (overrides or {}):
        return overrides[p]
    return a.load(p)


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
    overrides: {path: doc} or {(path, label): doc} replaces a file's document (a held item contributes only its InteractionVars; a route only the field that starts the chain).
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
        d = doc_of(a, overrides, p, (lab,))
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


# the label as the page writes it
LABEL_NAMES = [('NPC', 'NPC'), ('host', 'host'), ('encounter', 'encounter'), ('A-entity', 'ability entity or projectile'), ('A-caster', 'ability caster')] \
              + [(v[0], v[0]) for v in ROUTES.values()]


def label_counts(r, t):
    """Distinct objects of type t by the label of the manager they run on; an object reached under two labels counts under each."""
    cnt = collections.Counter()
    for ls in r['run_objs'][t].values():
        for l in ls:
            cnt[l] += 1
    return cnt


def runs_on(r, t):
    c = label_counts(r, t)
    return ', '.join(f'{name} {c[k]}' for k, name in LABEL_NAMES if c[k])


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


# ------------------------------------------------------------------ chain-start routes that no asset string names

def occurrences(doc, keys):
    """Every dict in doc whose `Interactions` map holds one of `keys`: [{'Interactions': {key: value}}]. A block's state variants carry their own."""
    out = []

    def find(o):
        if isinstance(o, dict):
            ia = o.get('Interactions')
            if isinstance(ia, dict):
                got = {k: ia[k] for k in keys if k in ia}
                if got:
                    out.append({'Interactions': got})
            for v in o.values():
                find(v)
        elif isinstance(o, list):
            for v in o:
                find(v)
    find(doc)
    return out


def block_route(a: Assets, name, keys):
    """The files of Item/Items and Item/Block/{Blocks,Fluids} with a block whose Interactions hold one of `keys` (Collision*, OnBreak*)."""
    label = ROUTES[name][0]
    seeds, ov = [], {}
    for st in ('Item/Items', 'Item/Block/Blocks', 'Item/Block/Fluids'):
        for p in a.files_under(st):
            occ = occurrences(a.load(p), keys)
            if occ:
                ov[(p, label)] = {'Occurrences': occ}
                seeds.append((p, label))
    return seeds, ov


def stat_route(a: Assets):
    """Entity/Stats files with MinValueEffects or MaxValueEffects holding an Interactions root."""
    label = ROUTES['stat'][0]
    seeds, ov = [], {}
    for p in a.files_under('Entity/Stats'):
        d = a.load(p)
        if not isinstance(d, dict):
            continue
        found = {k: d[k] for k in ('MinValueEffects', 'MaxValueEffects') if isinstance(d.get(k), dict) and d[k].get('Interactions') is not None}
        if found:
            ov[(p, label)] = found
            seeds.append((p, label))
    return seeds, ov


def volume_effects(a: Assets):
    """[(file, path, TargetTypes, Event, root id)] for every RunRootInteraction effect in Server/ (TriggerVolumes/Effects, Instances/*/resources/TriggerVolumeData.json,
    Prefabs): the nearest enclosing object with a TargetTypes list gives the volume's targets."""
    out = []

    def walk_(o, f, path, tt):
        if isinstance(o, dict):
            if isinstance(o.get('TargetTypes'), list):
                tt = [str(x) for x in o['TargetTypes']]
            if o.get('Type') == 'RunRootInteraction':
                out.append((f, path, tt, o.get('Event'), o.get('RootInteraction')))
            for k, v in o.items():
                walk_(v, f, f'{path}/{k}', tt)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk_(v, f, f'{path}[{i}]', tt)
    for f in sorted(a.server.rglob('*.json')):
        try:
            raw = f.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if '"RunRootInteraction"' not in raw:
            continue
        walk_(a.load(f), f, '', None)
    return out


def volume_hits_npc(target_types, event):
    """A RunRootInteraction effect runs on an NPC when its volume targets Npc, or when a queued signal runs it on the actor that sent the signal."""
    return any(str(t).lower() == 'npc' for t in (target_types or [])) or event == 'SIGNAL_RECEIVED'


def volume_route(a: Assets):
    label = ROUTES['volume'][0]
    seeds, effects, missing = [], volume_effects(a), []
    taken = []
    for f, path, tt, event, rid in effects:
        if not volume_hits_npc(tt, event):
            continue
        files = [q for q in a.base.get(rid, []) if 'Item/RootInteractions' in str(q)] if isinstance(rid, str) else []
        if not files:
            missing.append((a.rel(f), path, rid))
            continue
        taken.append((f, path, tt, event, rid))
        seeds += [(q, label) for q in files]
    return sorted(set(seeds)), {}, effects, taken, missing


def held_route(a: Assets, npc_files):
    """Held, HeldOffhand and Equipped of an item an NPC holds (HotbarItems, OffHandItems) or wears (Armor), through Compute parameters as the roles name them."""
    label = ROUTES['held'][0]
    held, _ = held_items(a, npc_files, WORN_ROOT_KEYS)
    seeds, ov, hits = [], {}, []
    for stem, f, path in held:
        if stem not in a.items:
            continue
        for dpath, mine in a.by_definer(stem, 'Interactions', ITEM_CHAIN_KEYS):
            doc = ov.setdefault((dpath, label), {'Interactions': {}})
            doc['Interactions'].update(mine)
            seeds.append((dpath, label))
            hits.append((stem, a.rel(f), path, sorted(mine)))
    return sorted(set(seeds)), ov, len(held), hits


def death_roles(a: Assets, npc_files):
    """[(role file, root id)] for every role that names a DeathInteraction (RoleBuilderSystem.java:160-161 hands it to DeathSystems.java:549 on the NPC's own manager)."""
    out = []

    def find(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'DeathInteraction':
                    val = v.get('Value') if isinstance(v, dict) else v      # a role names it, or a template declares it as a parameter with a default
                    if isinstance(val, str):
                        out.append((p, val))
                find(v, p)
        elif isinstance(o, list):
            for v in o:
                find(v, p)
    for p in npc_files:
        find(a.load(p), p)
    return out


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
        for dpath, dvars in a.by_definer(stem, 'InteractionVars'):
            overrides.setdefault(dpath, {'InteractionVars': {}})['InteractionVars'].update(dvars)
            extra_seeds.append((dpath, 'NPC'))
    base_seeds = npc_seeds + enc_seeds + abil_seeds + extra_seeds
    objs_base, seen_base = reach(a, types, base_seeds, 'none', overrides)
    r['run_base_objs'], r['run_base'] = objs_base, counts(objs_base)

    # 2b. the chain-start routes no asset string names (MAJOR-1 of the review of b0b119a..c4e97d1)
    npc_files = [p for p, _ in npc_seeds]
    routes = {}
    sd, ov = block_route(a, 'collision', ('Collision', 'CollisionEnter', 'CollisionLeave'))
    routes['collision'] = {'seeds': sd, 'overrides': ov}
    sd, ov = block_route(a, 'blockbreak', ('OnBreak', 'OnBreakImpact'))
    routes['blockbreak'] = {'seeds': sd, 'overrides': ov}
    sd, ov = stat_route(a)
    routes['stat'] = {'seeds': sd, 'overrides': ov}
    sd, ov, effects, taken, missing = volume_route(a)
    routes['volume'] = {'seeds': sd, 'overrides': ov, 'effects': effects, 'taken': taken, 'missing': missing}
    sd, ov, n_worn, hits = held_route(a, npc_files)
    routes['held'] = {'seeds': sd, 'overrides': ov, 'worn_strings': n_worn, 'hits': hits}
    route_seeds, route_ov = [], {}
    for name, rt in routes.items():
        objs_r, _ = reach(a, types, rt['seeds'], 'none', rt['overrides'])
        rt['objs'], rt['types'] = objs_r, counts(objs_r)
        rt['new'] = sorted(set(rt['types']) - set(r['run_base']))
        rt['more'] = {t: len({k for k in objs_r[t] if k not in objs_base.get(t, {})}) for t in objs_r if t in r['run_base']}
        route_seeds += rt['seeds']
        route_ov.update(rt['overrides'])
    r['routes'] = routes
    run_seeds = base_seeds + route_seeds
    overrides = {**overrides, **route_ov}
    objs_run, seen_run = reach(a, types, run_seeds, 'none', overrides)
    r['run_objs'], r['run_seen'], r['run_seeds'] = objs_run, seen_run, run_seeds
    r['run'] = counts(objs_run)
    r['overrides'] = overrides
    r['death'] = [(p, rid, any(s_[0] == q for s_ in seen_run for q in a.base.get(rid, []))) for p, rid in death_roles(a, npc_files)]
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


def object_at(a: Assets, f, path, overrides=None, labels=()):
    o = doc_of(a, overrides, f, labels)
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
        o = object_at(a, f, path, overrides, labs)
        if o is None:
            out['(object not found)'] += 1
            continue
        val = resolve_field(a, o, field)
        out['(absent)' if val is None else json.dumps(val)] += 1
    return out


OUTCOMES = ('doubled', 'desync', 'refuses', 'same-twice', 'guarded', 'once', 'flow', 'reads', 'none', 'unknown')
# Which census `sim` labels (what the simulation pass reaches) an outcome can sit on (review of b0b119a..c4e97d1, MINOR-3). Decided from what each outcome claims,
# then checked against every shipped row (a row that falls outside is a PROBLEM, and the shipped rows all fall inside):
#   doubled desync refuses same-twice   the effect is run by both passes, so the simulation pass must reach the server pass's method again
#   guarded      the method is reached again and a guard (the instance store, a fork recorded once) stops the second effect; or an own body of the type
#   once         the simulation pass does nothing, or only reads or records (a block hook that is empty, an own body, a wrapped tick0 that applies in this pass only)
#   flow         the type's body is its own, or a block hook that does something else
#   reads none unknown   a condition reads whatever either pass; no label is excluded
# A `once` on a type whose simulation pass runs firstRun or tick0 again (Explode=once, ChangeStat=once) is the wrong row this rules out.
AGAIN = {'firstRun', 'firstRun+', 'tick0', 'tick0+'}
COMPATIBLE_SIM = {
    'doubled': AGAIN, 'desync': AGAIN, 'refuses': AGAIN, 'same-twice': AGAIN,
    'guarded': AGAIN | {'own', 'own+'},
    'once': {'no-op', 'own', 'own+', 'tick0+', 'via-*:no-op', 'via-*:other'},
    'flow': {'own', 'own+', 'tick0+', 'via-*:no-op', 'via-*:other'},
    'reads': None, 'none': None, 'unknown': None,          # None = any label
}


def sim_class(label):
    """`via-<hook>:<kind>` labels are matched as via-*:<kind>."""
    return re.sub(r'^via-[^:]+:', 'via-*:', label)

BASES = ('measured', 'read')
MAX_UNKNOWN = 5      # item 13b R5: more than this fails the item


def check_table(tsv: pathlib.Path, src_root: pathlib.Path, run_types: set, info=None):
    """Re-check verdict-table.tsv against the run-reached population and the decompiled source. Returns (problems, rows).
    Problems: a run-reached type without a row, a row for a type that is not run-reached, a duplicate row, a word outside the vocabularies,
    a deciding hook that is not declared at the recorded line of the recorded file, a deciding file that is not in the type's class chain (census
    Chain(type).classes), an outcome that its census `sim` label cannot carry (COMPATIBLE_SIM), more unknowns than MAX_UNKNOWN.
    info is registry()'s result; it is computed from src_root when not given."""
    if info is None:
        info = registry(src_root)
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
        if t not in info:
            problems.append(f'{tsv.name}:{n}: {t} is not a registered interaction type')
        else:
            sim, _, _, _, files = info[t]
            if file not in files:
                problems.append(f'{tsv.name}:{n}: {t}: the deciding file {file.rsplit("/", 1)[-1]} is not in the class chain of {t} ({", ".join(f.rsplit("/", 1)[-1] for f in files)})')
            ok_sims = COMPATIBLE_SIM.get(outcome)
            if ok_sims is not None and sim_class(sim) not in ok_sims:
                problems.append(f'{tsv.name}:{n}: {t}: outcome {outcome} cannot sit on sim {sim} (its simulation pass; {outcome} needs one of {", ".join(sorted(ok_sims))})')
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
    for (f, path), labs in sorted(run_objs.get('ModifyInventory', {}).items()):
        o = doc_of(a, overrides, f, labs)
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
        root = pathlib.Path(src) / 'com/hypixel/hytale'
        files = tuple(str(c.path.relative_to(root)) for c in ch.classes)
        info[s.name] = (lab, w, writes, holds, files)
    return info


PAGE_GROUPS = (
    ('Lands twice, throws or desyncs', ('doubled', 'refuses', 'desync')),
    ('The same result twice', ('same-twice',)),
    ('Guarded: the type runs its effect once', ('guarded',)),
    ('Once: the simulation pass does nothing', ('once',)),
    ("Flow: the effect is the children's", ('flow',)),
    ('Reads only', ('reads',)),
    ('No effect on these managers', ('none',)),
    ('Not classified', ('unknown',)),
)


def page_tables(r, trows):
    """The per-outcome tables of docs/interactions-double-run.md, from the population (objects by the manager label they run on) and the verdict table."""
    by = {x['type']: x for x in trows}
    out = []
    for title, outs in PAGE_GROUPS:
        ts = sorted((t for t in by if by[t]['outcome'] in outs and t in r['run']), key=lambda t: (-r['run'][t], t))
        if not ts:
            continue
        out += [f'### {title} ({len(ts)})', '', '| Type | Objects (runs on) | Basis | Write | Deciding line and why |',
                '|------|-------------------|-------|-------|-----------------------|']
        for t in ts:
            x = by[t]
            out.append(f"| `{t}` | {r['run'][t]} ({runs_on(r, t)}) | {x['basis']} | {x['write']} | `{x['file'].rsplit('/', 1)[-1]}:{x['line']}` {x['reason']} |")
        out.append('')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', default=str(pathlib.Path.home() / '.cache/hytale-assets'))
    ap.add_argument('--src', default=str(pathlib.Path.home() / '.cache/hytale-jar/src'))
    ap.add_argument('--table', default=str(HERE / 'verdict-table.tsv'), help='the verdict table to check against the population (default: verdict-table.tsv)')
    ap.add_argument('--tables', metavar='FILE', help='write the per-outcome tables of docs/interactions-double-run.md (population counts joined with the verdict table) to FILE, which must resolve outside the repository and is not --table (refused with exit 2 otherwise)')
    args = ap.parse_args()
    if args.tables:
        # --tables WRITES its file. Read as an input it overwrote verdict-table.tsv, exited 0 and printed nothing unusual (item 14, 2026-10-18); the damage showed
        # only on the next run. So FILE must resolve (symlinks followed) outside the repository, and must not be --table. Checked before anything is read.
        out, repo = pathlib.Path(args.tables).resolve(), HERE.parents[2]
        if out == repo or repo in out.parents:
            print(f'FAIL  --tables {args.tables} resolves to {out}, inside the repository; this option writes its file, so give it a scratch path outside {repo}', file=sys.stderr)
            return 2
        if out == pathlib.Path(args.table).resolve():
            print(f'FAIL  --tables {args.tables} is the verdict table (--table {args.table}); this option writes its file and would overwrite it', file=sys.stderr)
            return 2
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
    rb = r['run_base']
    print(f'   held weapons and off-hand items with an Attack-tagged root bring back {len(set(rb) & (set(allc) - set(ni)))}: '
          f'{", ".join(sorted(set(rb) & (set(allc) - set(ni)))) or "none"}')
    print(f'   run-reached by the seeds above (NPC, encounter, ability, held weapons): {len(rb)} of {len(types)} types; ModifyInventory {rb.get("ModifyInventory", 0)} objects, ChangeStat {rb.get("ChangeStat", 0)}')
    print(f'   run-reached with the routes of 2b added: {len(run)} of {len(types)} types; ModifyInventory {run.get("ModifyInventory", 0)} objects, ChangeStat {run.get("ChangeStat", 0)}')
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
    seeds_run = [(p, l) for p, l in r['run_seeds']]
    lost_run = sorted(set(run) - set(counts(reach(a2, types, seeds_run, 'none', r['overrides'])[0])))
    print(f'   dropping Item/Interactions/Tests from the run-reached walk (routes included) loses types: {lost_run or "none"}')

    print()
    print('2b. CHAIN-START ROUTES THAT NO ASSET STRING NAMES (each read in the source; a seed with its own label; the types and objects it adds to the walk above)')
    for name, rt in r['routes'].items():
        lbl, why = ROUTES[name]
        print(f'   {lbl}: {len(rt["seeds"])} seed file(s); reaches {len(rt["types"])} types, {sum(len(v) for v in rt["objs"].values())} objects; '
              f'types not in the {len(rb)} above: {", ".join(rt["new"]) or "none"}; objects added to types already in it: '
              + (", ".join(f'{t} {n}' for t, n in sorted(rt['more'].items(), key=lambda kv: (-kv[1], kv[0])) if n) or 'none'))
        print(f'       {why}')
    vt = r['routes']['volume']
    print(f'   trigger volumes: {len(vt["effects"])} RunRootInteraction effects in Server/; {len(vt["taken"])} run on an NPC (the volume targets Npc, or the event is SIGNAL_RECEIVED); '
          f'{len(vt["effects"]) - len(vt["taken"]) - len(vt["missing"])} do not (Player-only volumes: ENTER, TICK, BLOCK_USED run on the player); {len(vt["missing"])} name no RootInteraction asset: '
          + (", ".join(sorted({str(m[2]) for m in vt["missing"]})) or 'none'))
    ht = r['routes']['held']
    print(f'   held and worn items: {ht["worn_strings"]} strings in HotbarItems, OffHandItems and Armor (and the parameters they Compute from); {len(ht["hits"])} name an item with a Held, HeldOffhand or Equipped root'
          + (': ' + ', '.join(f'{x[0]} ({x[1]}{x[2]}: {"/".join(x[3])})' for x in ht['hits']) if ht['hits'] else ''))
    shipped_keys = collections.Counter()
    for stem, ps in a.items.items():
        for _, d in a.item_chain(stem)[:1]:
            ia = d.get('Interactions')
            if isinstance(ia, dict):
                for k in ITEM_CHAIN_KEYS:
                    if k in ia:
                        shipped_keys[k] += 1
    print(f'       (items that carry them at all: ' + ', '.join(f'{k} {shipped_keys[k]}' for k in ITEM_CHAIN_KEYS) + '; none is held or worn by an NPC file)')
    dr = r['death']
    unarmed = pathlib.Path(a.server) / 'Item/Unarmed/Interactions/Empty.json'
    ud = a.load(unarmed)
    has_death = isinstance(ud, dict) and isinstance(ud.get('Interactions'), dict) and 'Death' in ud['Interactions']
    print(f'   death: {len(dr)} NPC file(s) name a DeathInteraction (RoleBuilderSystem.java:160-161 -> DeathSystems.java:549, on the dying NPC\'s own manager); '
          f'{sum(1 for x in dr if x[2])} of their roots are reached by the string walk already; the unarmed fallback (Item/Unarmed/Interactions/Empty.json) has a Death root: {"yes" if has_death else "no"}')

    print()
    print('   type                         sim                                   wait     sum all-edges  runs on (objects by manager label; sum = distinct objects, an object reached under two labels counts under each)')
    rows = sorted(run, key=lambda t: (-sum(len(v) for v in [r["run_objs"][t]]), t))
    for t in rows:
        print(f'   {t:28s} {info[t][0]:37s} {info[t][1]:7s} {run[t]:4d} {allc.get(t, 0):9d}  {runs_on(r, t)}')

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
    problems, trows = check_table(pathlib.Path(args.table), pathlib.Path(args.src), set(run), info)
    byo = collections.Counter(x['outcome'] for x in trows)
    byb = collections.Counter(x['basis'] for x in trows)
    print(f'6. VERDICT TABLE ({pathlib.Path(args.table).name}): {len(trows)} rows for {len(run)} run-reached types; outcomes ' + ', '.join(f'{k} {v}' for k, v in sorted(byo.items())) + '; basis ' + ', '.join(f'{k} {v}' for k, v in sorted(byb.items())))
    print('   outcome -> the census `sim` labels it can sit on (a row outside is a PROBLEM; the deciding file must also be in the type\'s class chain):')
    for o in OUTCOMES:
        ss = COMPATIBLE_SIM[o]
        print(f'      {o:11s} {"any" if ss is None else ", ".join(sorted(ss))}')
    pairs = collections.Counter((x['outcome'], sim_class(info[x['type']][0])) for x in trows if x['type'] in info)
    print('   rows by (outcome, sim): ' + '; '.join(f'{o}/{sm} {n}' for (o, sm), n in sorted(pairs.items())))
    for p in problems:
        print(f'   PROBLEM  {p}')
    print(f'   unknown: {byo.get("unknown", 0)} (limit {MAX_UNKNOWN}); {len(problems)} problem(s)')
    if args.tables:
        pathlib.Path(args.tables).write_text(page_tables(r, trows))
        print(f'   wrote the page tables to {pathlib.Path(args.tables).name}')
    print()
    print(f'registered types never reached by either population: {len(types - set(allc) - set(run))} of {len(types)}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
