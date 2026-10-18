#!/usr/bin/env python3
"""
usage-test.py -- does usage.py count what the item says it counts? (the negative control for the population)

    python3 -I maintenance/probes/double-run/usage-test.py WORKDIR [--assets DIR] [--src DIR]

WORKDIR must be absent, empty, or carry the marker .double-run-usage-test (nothing else is ever removed). A small
asset tree is planted there, one defect at a time, and usage.analyse() must report exactly what the rules say:

  planted                                                                  must be
  an AttractiveItemSet naming an item whose Attack-tagged root has a ChangeStat   in the 13a population, NOT run-reached
  a held weapon (HotbarItems) with an Attack-tagged root (Explode)                run-reached
  a held weapon whose root is NOT tagged Attack (ModifyInventory)                 not run-reached; seen by the 13a graph
  a weapon held through {"Compute": "Weapons"} and Modify.Weapons (Repeat)       run-reached
  a weapon whose Interactions come from its Parent (Interrupt)                    run-reached
  an item in OffHandItems with an Attack-tagged root (Condition)                  run-reached
  a held "Droplist:..." string and a held id that is no item                      counted as such, no edge
  an ability seed with a SpawnAbilityEntity carrying an inline chain (ClearEntityEffect), a plain cast (StatsCondition),
  an NPC action SpawnInteraction naming a root (TriggerCooldown)                  labels A-entity / A-caster / host
and then the sabotages that must move exactly one type:
  Root_Held's Attack tag removed     -> Explode leaves the run-reached population (the rule is the tag)
  Root_NotAttack gains the tag        -> ModifyInventory joins it
  the bait item moved into HotbarItems -> ChangeStat joins it (the held rule is the field, not the item)
Each sabotage must also leave every other planted type where it was. Last, on the real extracted assets: the 13a
population is 58 types with ModifyInventory 38 and ChangeStat 135; with no item edge it is 46 (2 and 25), and the 12
types the brief names fall out. A run that cannot show the planted defect, or whose real figures differ, is VOID (exit 2).

Review of b0b119a..c4e97d1 added, each with the negative control that shows the defect first:
  MINOR-2  a template item whose InteractionVars two held children inherit: its object is counted once (the keying by the child's file counted it twice)
  MAJOR-1  the routes no asset string names: a block's Collision* (also in a state variant), OnBreak*, a stat's Min/MaxValueEffects, RunRootInteraction
           effects of a volume that targets Npc (asset, instance data, prefab) or that a signal runs, and an item an NPC wears with an Equipped root; each
           with its own label and a decoy that must not count (a Primary root of a block, a Player-only volume, an item no NPC wears). The walk without
           the routes does not reach any of them.
  MINOR-3  check_table: a deciding file outside the type's class chain, and an outcome its census sim label cannot carry (Explode=once), are problems;
           the old per-row rule (the hook is declared at the recorded line) passed both
"""
from __future__ import annotations
import argparse, json, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import usage                                         # noqa: E402

TYPES = {'ChangeStat', 'ModifyInventory', 'Explode', 'Repeat', 'Interrupt', 'Condition', 'ClearEntityEffect',
         'StatsCondition', 'TriggerCooldown', 'Simple', 'Selector', 'Charging', 'Wielding', 'Projectile', 'SendMessage', 'PullEntityAbility', 'GroundedCondition',
         'Serial', 'ChangeState', 'RemoveEntity', 'BreakBlock', 'DestroyBlock', 'SpawnNPC', 'ApplyEffect', 'DamageEntity', 'SendBeacon', 'ApplyForce', 'Replace',
         'Parallel', 'AttachBeam', 'Mount', 'LaunchProjectile', 'Camera', 'CancelChain', 'Door'}
MARK = '.double-run-usage-test'


def put(root: pathlib.Path, rel: str, doc) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc))


def plant(server: pathlib.Path, *, attack_held=True, attack_notattack=False, bait_held=False, vol_npc='Npc', vol_player='Player') -> None:
    if server.exists():
        shutil.rmtree(server)
    tag = {'Tags': {'Attack': ['Melee']}}
    # --- interactions, one type each
    for name, t in [('Int_Held', 'Explode'), ('Int_NotAttack', 'SendMessage'), ('Int_Bait', 'ChangeStat'),
                    ('Int_Compute', 'Repeat'), ('Int_Parent', 'Interrupt'), ('Int_Off', 'Condition'),
                    ('Int_Entity', 'ClearEntityEffect'), ('Int_Cast', 'StatsCondition'), ('Int_Host', 'TriggerCooldown'),
                    ('Int_Plain', 'Simple'), ('Int_Swap', 'Charging'),
                    ('Int_Vars', 'Wielding'), ('Int_VarsNo', 'Projectile')]:
        put(server, f'Item/Interactions/{name}.json', {'Type': t})
    # --- roots; the Attack tag is what the NPC needs (ActionAttack.java:148-160)
    put(server, 'Item/RootInteractions/Root_Held.json', {'Interactions': ['Int_Held'], **(tag if attack_held else {})})
    put(server, 'Item/RootInteractions/Root_NotAttack.json', {'Interactions': ['Int_NotAttack'], **(tag if attack_notattack else {})})
    put(server, 'Item/RootInteractions/Root_Bait.json', {'Interactions': ['Int_Bait'], **tag})
    put(server, 'Item/RootInteractions/Root_Compute.json', {'Interactions': ['Int_Compute'], **tag})
    put(server, 'Item/RootInteractions/Root_Parent.json', {'Interactions': ['Int_Parent'], **tag})
    put(server, 'Item/RootInteractions/Root_Off.json', {'Interactions': ['Int_Off'], **tag})
    put(server, 'Item/RootInteractions/Root_Swap.json', {'Interactions': ['Int_Swap'], **tag})
    put(server, 'Item/RootInteractions/Root_Plain.json', {'Interactions': ['Int_Plain', 'Int_MI_Remove', 'Int_MI_Gate', 'Int_MI_Adjust', 'Int_MI_Ignore', 'Int_MI_Child', 'Int_MI_Dur']})
    put(server, 'Item/Interactions/Int_MI_Remove.json', {'Type': 'ModifyInventory', 'ItemToRemove': {'Id': 'X', 'Quantity': 1}})
    put(server, 'Item/Interactions/Int_MI_Gate.json', {'Type': 'ModifyInventory', 'RequiredGameMode': 'Adventure', 'ItemToRemove': {'Id': 'X', 'Quantity': 1}})
    put(server, 'Item/Interactions/Int_MI_Adjust.json', {'Type': 'ModifyInventory', 'AdjustHeldItemQuantity': -1})
    put(server, 'Item/Interactions/Int_MI_Ignore.json', {'Type': 'ModifyInventory', 'OnItemChangeBehavior': 'Ignore', 'ItemToAdd': {'Id': 'X', 'Quantity': 1}})
    put(server, 'Item/Interactions/Int_MI_Child.json', {'Parent': 'Int_MI_Gate'})
    put(server, 'Item/Interactions/Int_MI_Dur.json', {'Type': 'ModifyInventory', 'AdjustHeldItemDurability': -2.0})
    put(server, 'Item/RootInteractions/Root_Host.json', {'Interactions': ['Int_Host']})
    put(server, 'Item/RootInteractions/Root_Entity.json', {'Interactions': ['Int_Entity']})
    # --- items
    put(server, 'Item/Items/Weapon_Held.json', {'Interactions': {'Primary': 'Root_Held', 'SwapFrom': 'Root_Swap'},
                                                          'InteractionVars': {'V': {'Interactions': [{'Parent': 'Int_Vars'}]}}})
    put(server, 'Item/Items/Weapon_NotAttack.json', {'Interactions': {'Primary': 'Root_NotAttack'},
                                                              'InteractionVars': {'V': {'Interactions': [{'Parent': 'Int_VarsNo'}]}}})
    put(server, 'Item/Items/Item_Bait.json', {'Interactions': {'Primary': 'Root_Bait'}})
    put(server, 'Item/Items/Weapon_Compute.json', {'Interactions': {'Primary': 'Root_Compute'}})
    put(server, 'Item/Items/Template_Parent.json', {'Interactions': {'Secondary': 'Root_Parent'}})
    put(server, 'Item/Items/Weapon_Parent.json', {'Parent': 'Template_Parent'})
    put(server, 'Item/Items/Shield_Off.json', {'Interactions': {'Primary': 'Root_Off'}})
    # --- NPC files
    put(server, 'NPC/Roles/Npc_A.json', {
        'HotbarItems': ['Weapon_Held', 'Weapon_NotAttack', 'Droplist:Some_List', 'Not_An_Item'] + (['Item_Bait'] if bait_held else []),
        'OffHandItems': ['Shield_Off'],
        'AttractiveItemSet': ['Item_Bait'],
        'Attack': 'Root_Plain'})
    put(server, 'NPC/Roles/Npc_B.json', {
        'Parameters': {'Weapons': {'Value': []}},
        'HotbarItems': {'Compute': 'Weapons'},
        'Modify': {'Weapons': ['Weapon_Compute', 'Weapon_Parent']}})
    put(server, 'NPC/Roles/Npc_C.json', {'Instructions': [{'Type': 'SpawnInteraction', 'Interaction': 'Root_Host'}]})
    # --- ability seeds
    put(server, 'Item/Interactions/Abilities/Cast.json', {
        'Type': 'Selector', 'Next': 'Int_Cast',
        'Interactions': [{'Type': 'SpawnAbilityEntity', 'Repeats': [{'Chain': {'Interactions': [{'Type': 'ClearEntityEffect'}]}}]}]})
    put(server, 'Item/RootInteractions/Abilities/Root_Cast.json', {'Interactions': ['Cast']})
    # an ability projectile: its ProjectileSpawn chain runs on the shooter, its ProjectileHit chain on the projectile's own manager
    put(server, 'Item/Interactions/Abilities/Launch.json', {'Type': 'LaunchAbilityProjectile', 'Projectile': 'Proj_Cfg'})
    put(server, 'Item/RootInteractions/Abilities/Root_Launch.json', {'Interactions': ['Launch']})
    put(server, 'ProjectileConfigs/Proj_Cfg.json', {'Interactions': {'ProjectileSpawn': {'Interactions': [{'Type': 'PullEntityAbility'}]},
                                                                      'ProjectileHit': {'Interactions': [{'Type': 'GroundedCondition'}]}}})
    (server / 'EncounterManager').mkdir(parents=True, exist_ok=True)
    (server / 'Abilities').mkdir(parents=True, exist_ok=True)
    plant_review(server, vol_npc, vol_player)


def plant_review(server: pathlib.Path, vol_npc='Npc', vol_player='Player') -> None:
    """What the review of b0b119a..c4e97d1 added to the tree (MINOR-2, MAJOR-1)."""
    tag = {'Tags': {'Attack': ['Melee']}}
    for name, t in [('Int_Shared', 'Serial'), ('Int_Own', 'Selector'), ('Int_Pair', 'Mount'), ('Int_Decoy', 'Camera'), ('Int_Death', 'CancelChain'),
                    ('Int_Collide', 'ChangeState'), ('Int_Leave', 'RemoveEntity'), ('Int_Break', 'SpawnNPC'), ('Int_VolPlayer', 'DamageEntity'), ('Int_VolSignal', 'SendBeacon'),
                    ('Int_VolInst', 'ApplyForce'), ('Int_VolPrefab', 'Replace'), ('Int_VolNpc', 'LaunchProjectile'), ('Int_Worn', 'Parallel'), ('Int_Unworn', 'AttachBeam')]:
        put(server, f'Item/Interactions/{name}.json', {'Type': t})
    for name, i in [('Root_Pair', 'Int_Pair'), ('Root_Decoy', 'Int_Decoy'), ('Root_Death', 'Int_Death'), ('Root_Collide', 'Int_Collide'), ('Root_Leave', 'Int_Leave'),
                    ('Root_Break', 'Int_Break'), ('Root_VolPlayer', 'Int_VolPlayer'), ('Root_VolSignal', 'Int_VolSignal'),
                    ('Root_VolInst', 'Int_VolInst'), ('Root_VolPrefab', 'Int_VolPrefab'), ('Root_VolNpc', 'Int_VolNpc'), ('Root_Worn', 'Int_Worn'), ('Root_Unworn', 'Int_Unworn')]:
        put(server, f'Item/RootInteractions/{name}.json', {'Interactions': [i], **(tag if name == 'Root_Pair' else {})})
    # MINOR-2: a template whose InteractionVars two held children inherit; one child overrides the var, so the template's is the other child's
    put(server, 'Item/Items/Template_Pair.json', {'Interactions': {'Primary': 'Root_Pair'},
                                                       'InteractionVars': {'Shared': {'Interactions': [{'Type': 'Serial'}]}, 'Own': {'Interactions': [{'Type': 'Serial'}]},
                                                                           'Dead': {'Interactions': [{'Type': 'Door'}]}}})
    put(server, 'Item/Items/Weapon_Kid_A.json', {'Parent': 'Template_Pair', 'InteractionVars': {'Dead': {'Interactions': [{'Type': 'Mount'}]}}})
    put(server, 'Item/Items/Weapon_Kid_B.json', {'Parent': 'Template_Pair', 'InteractionVars': {'Own': {'Interactions': [{'Type': 'Selector'}]}, 'Dead': {'Interactions': [{'Type': 'Mount'}]}}})
    put(server, 'NPC/Roles/Npc_D.json', {'HotbarItems': ['Weapon_Kid_A', 'Weapon_Kid_B']})
    # MAJOR-1: the routes. A block's Collision chain (and one in a state variant), an OnBreak chain, a block with both, a decoy Primary root
    put(server, 'Item/Items/Block_Collide.json', {'BlockType': {'Interactions': {'CollisionEnter': 'Root_Collide', 'Primary': 'Root_Decoy'},
                                                                 'State': {'Definitions': {'Open': {'Interactions': {'CollisionLeave': 'Root_Leave'}}}}}})
    put(server, 'Item/Items/Block_Break.json', {'BlockType': {'Interactions': {'OnBreak': 'Root_Break'}}})
    put(server, 'Item/Block/Blocks/Block_Both.json', {'Interactions': {'Collision': {'Interactions': [{'Type': 'BreakBlock'}]}, 'OnBreakImpact': {'Interactions': [{'Type': 'DestroyBlock'}]}}})
    put(server, 'Entity/Stats/Stat_Test.json', {'InitialValue': 1, 'MinValueEffects': {'Interactions': {'Interactions': [{'Type': 'ApplyEffect', 'EffectId': 'E'}]}}, 'MaxValueEffects': {'TriggerAtZero': True}})
    put(server, 'Entity/Stats/Stat_Decoy.json', {'InitialValue': 1})
    # trigger volumes: an NPC volume (asset), a Player volume (decoy), a Player volume with a signal event, instance data, a prefab, a missing root
    put(server, 'TriggerVolumes/Effects/Vol_Npc.json', {'Effects': [{'Type': 'RunRootInteraction', 'Event': 'ENTER', 'RootInteraction': 'Root_VolNpc'},
                                                                      {'Type': 'RunRootInteraction', 'Event': 'TICK', 'RootInteraction': 'Root_Missing'}], 'TargetTypes': [vol_npc]})
    put(server, 'TriggerVolumes/Effects/Vol_Player.json', {'Effects': [{'Type': 'RunRootInteraction', 'Event': 'ENTER', 'RootInteraction': 'Root_VolPlayer'}], 'TargetTypes': [vol_player]})
    put(server, 'TriggerVolumes/Effects/Vol_Signal.json', {'Effects': [{'Type': 'RunRootInteraction', 'Event': 'SIGNAL_RECEIVED', 'RootInteraction': 'Root_VolSignal'}], 'TargetTypes': ['Player']})
    put(server, 'Instances/Inst/resources/TriggerVolumeData.json', {'Volumes': {'v1': {'TargetTypes': ['Npc'], 'Effects': [{'Type': 'RunRootInteraction', 'Event': 'TICK', 'RootInteraction': 'Root_VolInst'}]}}})
    put(server, 'Prefabs/P.prefab.json', {'entities': [{'Components': {'TriggerVolume': {'TargetTypes': ['Npc'], 'Effects': [{'Type': 'RunRootInteraction', 'Event': 'ENTER', 'RootInteraction': 'Root_VolPrefab'}]}}}]})
    # held and worn items: an NPC wears an item with an Equipped root (through Armor); another item has a Held root and nobody holds it
    put(server, 'Item/Items/Armor_Eq.json', {'Interactions': {'Equipped': {'Interactions': ['Int_Worn']}, 'Primary': 'Root_Decoy'}})
    put(server, 'Item/Items/Item_HeldUnworn.json', {'Interactions': {'Held': {'Interactions': ['Int_Unworn']}}})
    put(server, 'NPC/Roles/Npc_E.json', {'Armor': ['Armor_Eq']})
    # DeathInteraction: one that names a root, one that names nothing
    put(server, 'NPC/Roles/Npc_F.json', {'DeathInteraction': 'Root_Death'})
    put(server, 'NPC/Roles/Npc_G.json', {'DeathInteraction': 'Root_NotThere'})


def types_of(r, key='run'):
    return set(r[key])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--assets', default=str(pathlib.Path.home() / '.cache/hytale-assets'))
    ap.add_argument('--src', default=str(pathlib.Path.home() / '.cache/hytale-jar/src'))
    a = ap.parse_args()
    work = pathlib.Path(a.work).resolve()
    if not a.work.startswith('/'):
        print('FAIL  WORKDIR must be absolute', file=sys.stderr)
        return 3
    if work.exists() and not (work / MARK).exists() and (not work.is_dir() or any(work.iterdir())):
        print(f'FAIL  {work} exists, is not empty and has no marker; give a new path', file=sys.stderr)
        return 3
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    (work / MARK).write_text('')
    server = work / 'Server'

    fails, void = [], []

    def check(label, cond, detail=''):
        print(('PASS  ' if cond else 'FAIL  ') + label + ('' if cond else f'   {detail}'))
        if not cond:
            fails.append(label)

    # ---- the planted tree, unharmed
    plant(server)
    r = usage.analyse(server, TYPES)
    run, allc = types_of(r), set(r['all_edges'])
    if r['n_npc'] != 7 or not r['held']['attack']:
        print(f'VOID  the planted tree is not what the test thinks: {r["n_npc"]} NPC seeds, {len(r["held"]["attack"])} held items with an Attack root')
        return 2
    # the instrument must SEE the defects first: the 13a graph reaches the bait's ChangeStat and the non-Attack ModifyInventory
    if not {'ChangeStat', 'SendMessage'} <= allc:
        print('VOID  the 13a graph does not reach the bait (ChangeStat) or the non-Attack weapon (SendMessage): the planted item edges are invisible')
        return 2
    check('13a graph: an AttractiveItemSet item edge reaches ChangeStat (the defect is visible)', 'ChangeStat' in allc)
    check('run-reached: the AttractiveItemSet bait does NOT count (ChangeStat)', 'ChangeStat' not in run, sorted(run))
    check('run-reached: a held weapon with an Attack-tagged root counts (Explode)', 'Explode' in run, sorted(run))
    check('run-reached: a held weapon whose root is not tagged Attack does not count (SendMessage)', 'SendMessage' not in run, sorted(run))
    check('run-reached: a weapon held through Compute + Modify.Weapons counts (Repeat)', 'Repeat' in run, sorted(run))
    check('run-reached: a weapon whose Interactions come from its Parent counts (Interrupt)', 'Interrupt' in run, sorted(run))
    check('run-reached: an OffHandItems item with an Attack-tagged root counts (Condition)', 'Condition' in run, sorted(run))
    check('run-reached: a root under a key that is not an AttackType (SwapFrom), even tagged Attack, does not count (Charging)', 'Charging' not in run, sorted(run))
    check('run-reached: the InteractionVars of a held Attack weapon count (Wielding via Parent)', 'Wielding' in run, sorted(run))
    check('run-reached: the InteractionVars of a held weapon with no Attack root do not (Projectile)', 'Projectile' not in run, sorted(run))
    check('run-reached: a plain Attack field counts (Simple)', 'Simple' in run, sorted(run))
    h = r['held']
    check('held strings: 1 droplist reference and 1 id that is no item are counted and given no edge',
          len(h['droplist']) == 1 and len(h['missing']) == 1, (len(h['droplist']), len(h['missing'])))
    check('held items with an Attack root: 6 strings (Held, Compute, Parent, Off, the two kids of Template_Pair); 1 without (NotAttack)',
          len(h['attack']) == 6 and len(h['no_attack']) == 1, (len(h['attack']), len(h['no_attack'])))
    check('compute names are read from the roles: Weapons', h['fields'] == ['Weapons'], h['fields'])
    lab = r['labels']
    check('label: a plain NPC chain runs on NPC', lab.get('Simple') == {'NPC'}, lab.get('Simple'))
    check('label: SpawnInteraction hands its root to a host', lab.get('TriggerCooldown') == {'host'}, lab.get('TriggerCooldown'))
    check('label: a SpawnAbilityEntity Repeats chain runs on the ability entity', lab.get('ClearEntityEffect') == {'A-entity'}, lab.get('ClearEntityEffect'))
    check("label: an ability projectile's ProjectileSpawn chain runs on the caster", lab.get('PullEntityAbility') == {'A-caster'}, lab.get('PullEntityAbility'))
    check("label: an ability projectile's ProjectileHit chain runs on the projectile's own manager", lab.get('GroundedCondition') == {'A-entity'}, lab.get('GroundedCondition'))
    check('label: a plain ability cast runs on the caster', lab.get('StatsCondition') == {'A-caster'}, lab.get('StatsCondition'))
    # ---- MINOR-2: an object is keyed by the file that defines it. Negative control first: keyed by the held item's own file, as before the review, the template's
    # InteractionVars are counted once per held child (Serial: Shared via both kids, Own via Weapon_Kid_A, = 3), and the instrument must see that
    orig_by = usage.Assets.by_definer
    usage.Assets.by_definer = lambda self, stem, field, keys=None: ([(self.items[stem][0], self.item_vars(stem))] if field == 'InteractionVars' else orig_by(self, stem, field, keys))
    try:
        old_objs = usage.analyse(server, TYPES)['run_objs']
    finally:
        usage.Assets.by_definer = orig_by
    if len(old_objs.get('Serial', {})) != 3:
        print(f'VOID  keyed by the child, the planted template is counted {len(old_objs.get("Serial", {}))} time(s), wanted 3: the duplicate is invisible')
        return 2
    check('keyed by the held item\'s own file (the old rule) a template shared by two held children is counted once per child (the defect is visible: Serial 3)', True)
    ser = r['run_objs'].get('Serial', {})
    check('MINOR-2: a template shared by two held children is counted once: Serial 2 (Shared, and Own for the child that did not override it), both defined in Template_Pair',
          len(ser) == 2 and all(pathlib.Path(f).name == 'Template_Pair.json' for f, _ in ser), sorted(ser))
    sel = [k for k in r['run_objs'].get('Selector', {}) if pathlib.Path(k[0]).name == 'Weapon_Kid_B.json']
    check("MINOR-2: a var a child overrides is counted at the child's file, once (Selector at Weapon_Kid_B)", len(sel) == 1, sel)
    check("MINOR-2: a template var that every held child overrides never runs and is not counted (Door)", 'Door' not in run, sorted(run))

    # ---- MAJOR-1: the routes. The walk without them does not reach any of these types (the defect), with them each has its own label; a decoy per route does not count
    route_types = {'ChangeState': 'NPC collision', 'RemoveEntity': 'NPC collision', 'BreakBlock': 'NPC collision', 'DestroyBlock': 'NPC block break',
                   'SpawnNPC': 'NPC block break', 'ApplyEffect': 'NPC stat effect', 'LaunchProjectile': 'NPC trigger volume', 'SendBeacon': 'NPC trigger volume',
                   'ApplyForce': 'NPC trigger volume', 'Replace': 'NPC trigger volume', 'Parallel': 'NPC held item'}
    seen_by_base = sorted(set(route_types) & set(r['run_base']))
    if seen_by_base:
        print(f'VOID  the walk without the routes already reaches {seen_by_base}: the planted routes are invisible to the control')
        return 2
    check('MAJOR-1 negative control: the walk without the routes reaches none of the 11 planted route types', not seen_by_base)
    for t, want in route_types.items():
        check(f'MAJOR-1: {t} is reached with the label {want!r} and no other', lab.get(t) == {want}, lab.get(t))
    check('MAJOR-1: a block\'s Primary root, a Player-only volume\'s root and an item no NPC wears do not count (Camera, DamageEntity, AttachBeam)',
          not ({'Camera', 'DamageEntity', 'AttachBeam'} & set(run)), sorted(run))
    rv = r['routes']['volume']
    check('MAJOR-1: 6 RunRootInteraction effects found in the planted volumes; 4 run on an NPC, 1 names no root, 1 is a Player volume',
          (len(rv['effects']), len(rv['taken']), len(rv['missing'])) == (6, 4, 1), (len(rv['effects']), len(rv['taken']), len(rv['missing'])))
    check('MAJOR-1: a block with a Collision and an OnBreakImpact chain is two seeds with two labels (BreakBlock only on collision, DestroyBlock only on block break)',
          lab.get('BreakBlock') == {'NPC collision'} and lab.get('DestroyBlock') == {'NPC block break'})
    check('MAJOR-1: the route counts of the planted tree: collision 2 seed files, block break 2, stat 1, volume 4, held 1',
          tuple(len(r['routes'][k]['seeds']) for k in ('collision', 'blockbreak', 'stat', 'volume', 'held')) == (2, 2, 1, 4, 1),
          tuple(len(r['routes'][k]['seeds']) for k in ('collision', 'blockbreak', 'stat', 'volume', 'held')))
    inline = {}
    for t_ in ('BreakBlock', 'DestroyBlock', 'ApplyEffect'):
        for (f_, path_), labs_ in r['run_objs'].get(t_, {}).items():
            o_ = usage.object_at(r['assets'], f_, path_, r['overrides'], labs_)
            inline[t_] = (o_ or {}).get('Type')
    check('MAJOR-1: an object inside a route\'s document is found again by (file, path, labels), also for a block that has two routes', inline == {'BreakBlock': 'BreakBlock', 'DestroyBlock': 'DestroyBlock', 'ApplyEffect': 'ApplyEffect'}, inline)
    check('MAJOR-1: a DeathInteraction that names a root is reached by the string walk; one that names none is reported as not reached',
          sorted((pathlib.Path(p_).name, rid, ok) for p_, rid, ok in r['death']) == [('Npc_F.json', 'Root_Death', True), ('Npc_G.json', 'Root_NotThere', False)], r['death'])
    check('MAJOR-1: a DeathInteraction root is a plain NPC chain (CancelChain on NPC)', lab.get('CancelChain') == {'NPC'}, lab.get('CancelChain'))
    base = run
    rows, tot = usage.modify_inventory_walk(r['assets'], r['run_objs'], r['overrides'])
    kinds = {Path_.name: k for (f, p_, act, gate, beh, k, v) in rows for Path_ in [pathlib.Path(f)]}
    check('held-slot walk: ItemToRemove with no gate and no Ignore is the one CANDIDATE', kinds.get('Int_MI_Remove.json') == 'CANDIDATE' and tot['CANDIDATE'] == 1, dict(tot))
    check('held-slot walk: RequiredGameMode makes it inert, also through a Parent', kinds.get('Int_MI_Gate.json') == 'inert (RequiredGameMode)' and kinds.get('Int_MI_Child.json') == 'inert (RequiredGameMode)', kinds)
    check('held-slot walk: AdjustHeldItemQuantity and AdjustHeldItemDurability write through setHeldItem and cannot trip',
          kinds.get('Int_MI_Adjust.json') == 'setHeldItem only' and kinds.get('Int_MI_Dur.json') == 'setHeldItem only', kinds)
    check('held-slot walk: a slot write under Ignore is not a candidate', kinds.get('Int_MI_Ignore.json') == 'slot write, Ignore', kinds)
    check('held-slot walk: the 6 planted ModifyInventory objects are all seen', sum(tot.values()) == 6, dict(tot))

    # ---- sabotages: each must move exactly one type
    def moved(label, kw, gained=(), lost=()):
        plant(server, **kw)
        r2 = usage.analyse(server, TYPES)
        now = types_of(r2)
        ok = now - base == set(gained) and base - now == set(lost)
        check(label, ok, f'gained {sorted(now - base)}, lost {sorted(base - now)}; wanted +{sorted(gained)} -{sorted(lost)}')

    moved("sabotage: Root_Held loses its Attack tag -> Explode and the item's InteractionVars (Wielding) leave", dict(attack_held=False), lost=['Explode', 'Wielding'])
    moved("sabotage: Root_NotAttack gains the tag -> SendMessage and the item's InteractionVars (Projectile) join", dict(attack_notattack=True), gained=['SendMessage', 'Projectile'])
    moved("sabotage: the bait item is held -> only ChangeStat joins", dict(bait_held=True), gained=['ChangeStat'])
    moved("sabotage: the Player-only volume targets Npc -> only DamageEntity joins (the route is the volume's TargetTypes)", dict(vol_player='Npc'), gained=['DamageEntity'])
    moved("sabotage: the Npc volume targets Player -> only LaunchProjectile leaves", dict(vol_npc='Player'), lost=['LaunchProjectile'])
    plant(server)

    # ---- negative control: the 13a rule (every item id is an edge) must count the bait and the non-Attack weapon
    orig = usage.reach
    usage.reach = lambda a_, t_, seeds, item_edges, overrides=None: orig(a_, t_, seeds, 'all', overrides)
    try:
        old = types_of(usage.analyse(server, TYPES))
    finally:
        usage.reach = orig
    if not {'ChangeStat', 'SendMessage'} <= old:
        print('VOID  with every item id an edge, the run-reached walk still misses the bait: the negative control cannot see the defect')
        return 2
    check('negative control: under the 13a rule (item ids are edges) the bait and the non-Attack weapon are counted', {'ChangeStat', 'SendMessage'} <= old)

    # ---- the real data
    assets = pathlib.Path(a.assets) / 'Server'
    if not (assets / 'NPC').is_dir():
        print(f'VOID  no extracted assets under {usage.home(assets)}; the real-data checks did not run')
        return 2
    info = usage.registry(pathlib.Path(a.src))
    real = usage.analyse(assets, set(info))
    ni = real['no_item_edges']
    allr = real['all_edges']
    fell = sorted(set(allr) - set(ni))
    want = ['ChangeActiveSlot', 'ContextualUseNPC', 'CycleBlockGroup', 'DragPlaceBlock', 'DurabilityCondition', 'EquipItem', 'ExtrudePlaceBlock',
            'MovementCondition', 'PlaceModeSelect', 'RefillContainer', 'SpawnNPC', 'SurfaceDrawPlaceBlock']
    if not real['n_npc'] or not real['n_abil'] or not allr:
        print('VOID  the real walk visited nothing')
        return 2
    check('real: the 13a population is 58 types, ModifyInventory 38 objects, ChangeStat 135',
          (len(allr), allr.get('ModifyInventory'), allr.get('ChangeStat')) == (58, 38, 135), (len(allr), allr.get('ModifyInventory'), allr.get('ChangeStat')))
    check('real: with no item edge it is 46 types, ModifyInventory 2, ChangeStat 25',
          (len(ni), ni.get('ModifyInventory'), ni.get('ChangeStat')) == (46, 2, 25), (len(ni), ni.get('ModifyInventory'), ni.get('ChangeStat')))
    check('real: the 12 types that fall out without item edges are the brief\'s', fell == want, fell)
    check('real: the run-reached population of the seeds without the routes sits between the two (no type outside the 13a population)',
          set(ni) <= set(real['run_base']) <= set(allr), (sorted(set(real['run_base']) - set(allr)), sorted(set(ni) - set(real['run_base']))))
    want10 = ['ChangeBlock', 'ExitInstance', 'HubPortal', 'LaunchPad', 'Portal', 'PortalReturn', 'SpawnNPC', 'TeleportConfigInstance', 'TeleportInstance', 'Teleporter']
    check('real: the 48 types of 13b are reproduced by the seeds without the routes', len(real['run_base']) == 48, len(real['run_base']))
    check('real: the routes add the 10 types the review found (58 in all), all of them from the collision route but SpawnNPC, which the block-break route reaches too',
          sorted(set(real['run']) - set(real['run_base'])) == want10 and len(real['run']) == 58
          and sorted(real['routes']['collision']['new']) == want10 and real['routes']['blockbreak']['new'] == ['SpawnNPC'] and not real['routes']['stat']['new'] and not real['routes']['volume']['new'],
          (sorted(set(real['run']) - set(real['run_base'])), len(real['run'])))
    check('real: seed files per route (collision, block break, stat, volume, held) are 58, 2, 3, 12, 0',
          tuple(len(real['routes'][k]['seeds']) for k in ('collision', 'blockbreak', 'stat', 'volume', 'held')) == (58, 2, 3, 12, 0),
          tuple(len(real['routes'][k]['seeds']) for k in ('collision', 'blockbreak', 'stat', 'volume', 'held')))
    # MINOR-2 by a route that shares nothing with usage.py: the reviewer's dupcount re-keyed 4,272 rows to 4,127 distinct objects
    check('real: the objects of the seeds without the routes are 4127, each keyed by the file that defines it (the reviewer counted 4,272 rows, 4,127 distinct)',
          sum(len(v) for v in real['run_base_objs'].values()) == 4127, sum(len(v) for v in real['run_base_objs'].values()))
    # why the run-reached Projectile count (145) was larger than the all-edges one (99): it was not a subset. The 13a graph had no encounter seeds (26 Projectile objects),
    # and the child-keyed duplicates added 20. Keyed by definer and with the encounter seeds in the all-edges walk, the seeds without the routes are a subset of it.
    enc_ = [(p_, 'encounter') for p_ in real['assets'].files_under('EncounterManager')]
    objs_all_enc, _ = usage.reach(real['assets'], set(info), real['seeds_all'] + enc_, 'all')
    outside = {t_: len(set(v_) - set(objs_all_enc.get(t_, {}))) for t_, v_ in real['run_base_objs'].items()}
    check('real: every object of the seeds without the routes is also an object of the all-edges walk with the encounter seeds added (a subset; Projectile 125 of 125)',
          not any(outside.values()) and len(real['run_base_objs']['Projectile']) == len(objs_all_enc['Projectile']) == 125, {t_: n_ for t_, n_ in outside.items() if n_})
    check('real: the all-edges walk without the encounter seeds has 99 Projectile objects, 26 fewer (the surplus the 13b count showed over 13a\'s was the encounters and the duplicates)',
          len(real['all_objs']['Projectile']) == 99 and len(set(real['run_base_objs']['Projectile']) - set(real['all_objs']['Projectile'])) == 26)
    check('real: every DeathInteraction a role names is reached by the string walk (3 files)', len(real['death']) == 3 and all(ok for _, _, ok in real['death']), real['death'])
    check('real: no item an NPC holds or wears carries a Held, HeldOffhand or Equipped root (the held route is empty at 0.7.2)', not real['routes']['held']['hits'] and real['routes']['held']['worn_strings'] > 0,
          (real['routes']['held']['hits'], real['routes']['held']['worn_strings']))
    # ---- the verdict table is re-checked against the population and the source
    tsv = HERE / 'verdict-table.tsv'
    src = pathlib.Path(a.src)
    runset = set(real['run'])
    probs, trows = usage.check_table(tsv, src, runset)
    if not trows:
        print('VOID  verdict-table.tsv has no rows')
        return 2
    check('verdict table: the shipped table has a row for each of the run-reached types and every deciding line holds', not probs and len(trows) == len(runset), probs[:3])
    base_lines = tsv.read_text().split('\n')
    tdir = work / 'tsv'
    tdir.mkdir()

    def variant(name, edit):
        lines = edit(list(base_lines))
        p = tdir / name
        p.write_text('\n'.join(lines))
        return usage.check_table(p, src, runset, info)[0]
    first = next(i for i, l in enumerate(base_lines) if l and not l.startswith('#'))
    cols = base_lines[first].split('\t')
    pr = variant('missing.tsv', lambda L: L[:first] + L[first + 1:])
    check('verdict table: a deleted row is reported ("has no row")', any('has no row' in x and cols[0] in x for x in pr), pr)
    pr = variant('extra.tsv', lambda L: L + ['\t'.join(['ApplyBlockEntity', 'once', 'read', 'none', 'firstRun', cols[5], cols[6], 'x'])])
    check('verdict table: a row for a type that is not run-reached is reported', any('not run-reached' in x for x in pr), pr)
    pr = variant('dup.tsv', lambda L: L + [L[first]])
    check('verdict table: a duplicate row is reported', any('duplicate row' in x for x in pr), pr)
    pr = variant('shift.tsv', lambda L: L[:first] + [L[first].replace('\t' + cols[6] + '\t', '\t' + str(int(cols[6]) + 1) + '\t')] + L[first + 1:])
    check('verdict table: a deciding line that moved is reported', any('does not declare' in x and cols[0] in x for x in pr), pr)
    pr = variant('badword.tsv', lambda L: L[:first] + [L[first].replace('\t' + cols[1] + '\t', '\tmaybe\t')] + L[first + 1:])
    check('verdict table: an outcome outside the vocabulary is reported', any("outcome 'maybe'" in x for x in pr), pr)
    pr = variant('badbasis.tsv', lambda L: L[:first] + [L[first].replace('\t' + cols[2] + '\t', '\tguessed\t')] + L[first + 1:])
    check('verdict table: a basis outside the vocabulary is reported', any("basis 'guessed'" in x for x in pr), pr)

    def six_unknown(L):
        out, n = [], 0
        for l in L:
            c = l.split('\t')
            if l and not l.startswith('#') and len(c) == 8 and n < usage.MAX_UNKNOWN + 1:
                c[1] = 'unknown'
                n += 1
                l = '\t'.join(c)
            out.append(l)
        return out
    pr = variant('unknown.tsv', six_unknown)
    check('verdict table: more than K = 5 unknown verdicts fail', any('more than' in x for x in pr), pr)

    # ---- MINOR-3: the deciding file must be in the type's class chain, and the outcome must be one its census sim label can carry.
    # The reviewer's planted rows: ChangeStat=once citing ApplyEffectInteraction.java:91 simulateFirstRun, and Explode=once. The old per-row rule (the hook is declared at the
    # recorded line of the recorded file) passed both; that is the defect, and the instrument must see it before the new rules are credited.
    def old_rule(cols):
        try:
            text = (src / 'com/hypixel/hytale' / cols[5]).read_text().split('\n')
            return re.search(r'\bvoid ' + re.escape(cols[4]) + r'\(', text[int(cols[6]) - 1]) is not None
        except (OSError, ValueError, IndexError):
            return False

    def edit_row(L, t, **kw):
        names = ['type', 'outcome', 'basis', 'write', 'hook', 'file', 'line', 'reason']
        out = list(L)
        for i, l in enumerate(out):
            c = l.split('\t')
            if l and not l.startswith('#') and c[0] == t:
                d = dict(zip(names, c))
                d.update(kw)
                out[i] = '\t'.join(d[k] for k in names)
                return out, [d[k] for k in names]
        raise KeyError(t)
    ae = next(l.split('\t') for l in base_lines if l.startswith('ApplyEffect\t'))
    wrong = dict(outcome='once', basis='read', hook=ae[4], file=ae[5], line=ae[6])
    L1, cols1 = edit_row(base_lines, 'ChangeStat', **wrong)
    L2, cols2 = edit_row(base_lines, 'Explode', outcome='once')
    L3, cols3 = edit_row(base_lines, 'ChangeStat', hook=ae[4], file=ae[5], line=ae[6])
    if not (old_rule(cols1) and old_rule(cols2) and old_rule(cols3)):
        print('VOID  the old per-row rule does not accept the planted wrong rows: the defect is not reproduced')
        return 2
    check('MINOR-3 negative control: the old per-row rule (hook declared at the recorded line) accepts ChangeStat=once citing ApplyEffectInteraction, Explode=once, and ChangeStat citing ApplyEffectInteraction', True)
    pr = variant('minor3a.tsv', lambda L: edit_row(L, 'ChangeStat', **wrong)[0])
    check('MINOR-3: ChangeStat=once citing ApplyEffectInteraction.java:91 is reported twice: the file is not in ChangeStat\'s class chain, and once cannot sit on sim firstRun',
          any('ApplyEffectInteraction.java is not in the class chain of ChangeStat' in x for x in pr) and any('ChangeStat: outcome once cannot sit on sim firstRun' in x for x in pr), pr)
    pr = variant('minor3b.tsv', lambda L: edit_row(L, 'Explode', outcome='once')[0])
    check('MINOR-3: Explode=once is reported (its simulation pass runs firstRun again), and the file is accepted (it is in the chain)',
          any('Explode: outcome once cannot sit on sim firstRun' in x for x in pr) and not any('class chain' in x for x in pr), pr)
    pr = variant('minor3c.tsv', lambda L: edit_row(L, 'ChangeStat', hook=ae[4], file=ae[5], line=ae[6])[0])
    check('MINOR-3: a doubled ChangeStat citing a hook of another class is reported for the file alone (doubled can sit on sim firstRun)',
          any('ApplyEffectInteraction.java is not in the class chain of ChangeStat' in x for x in pr) and not any('cannot sit' in x for x in pr), pr)
    pr = variant('minor3d.tsv', lambda L: edit_row(L, 'ApplyEffect', outcome='doubled')[0])
    check('MINOR-3: ApplyEffect=doubled is reported (its simulation pass does nothing, so nothing runs twice)', any('ApplyEffect: outcome doubled cannot sit on sim no-op' in x for x in pr), pr)
    pr = variant('minor3e.tsv', lambda L: L + ['\t'.join(['NotAType', 'once', 'read', 'none', cols[4], cols[5], cols[6], 'x'])])
    check('MINOR-3: a row for a name that is not a registered interaction type is reported', any('NotAType is not a registered interaction type' in x for x in pr), pr)
    check('MINOR-3: every shipped row is accepted by the outcome/sim mapping (the mapping was decided from the rows and holds for all of them)',
          not [x for x in usage.check_table(tsv, src, runset, info)[0] if 'cannot sit' in x or 'class chain' in x])
    # the page tables: one row per run-reached type
    tb = usage.page_tables(real, trows)
    check('--tables: one table row per run-reached type', len([l for l in tb.split('\n') if l.startswith('| `')]) == len(runset), len(tb))
    print(f'---- {len(fails)} failed')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
