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
"""
from __future__ import annotations
import argparse, json, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import usage                                         # noqa: E402

TYPES = {'ChangeStat', 'ModifyInventory', 'Explode', 'Repeat', 'Interrupt', 'Condition', 'ClearEntityEffect',
         'StatsCondition', 'TriggerCooldown', 'Simple', 'Selector', 'Charging', 'Wielding', 'Projectile', 'SendMessage', 'PullEntityAbility', 'GroundedCondition'}
MARK = '.double-run-usage-test'


def put(root: pathlib.Path, rel: str, doc) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc))


def plant(server: pathlib.Path, *, attack_held=True, attack_notattack=False, bait_held=False) -> None:
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
    if r['n_npc'] != 3 or not r['held']['attack']:
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
    check('held items with an Attack root: 4 strings (Held, Compute, Parent, Off); 1 without (NotAttack)',
          len(h['attack']) == 4 and len(h['no_attack']) == 1, (len(h['attack']), len(h['no_attack'])))
    check('compute names are read from the roles: Weapons', h['fields'] == ['Weapons'], h['fields'])
    lab = r['labels']
    check('label: a plain NPC chain runs on NPC', lab.get('Simple') == {'NPC'}, lab.get('Simple'))
    check('label: SpawnInteraction hands its root to a host', lab.get('TriggerCooldown') == {'host'}, lab.get('TriggerCooldown'))
    check('label: a SpawnAbilityEntity Repeats chain runs on the ability entity', lab.get('ClearEntityEffect') == {'A-entity'}, lab.get('ClearEntityEffect'))
    check("label: an ability projectile's ProjectileSpawn chain runs on the caster", lab.get('PullEntityAbility') == {'A-caster'}, lab.get('PullEntityAbility'))
    check("label: an ability projectile's ProjectileHit chain runs on the projectile's own manager", lab.get('GroundedCondition') == {'A-entity'}, lab.get('GroundedCondition'))
    check('label: a plain ability cast runs on the caster', lab.get('StatsCondition') == {'A-caster'}, lab.get('StatsCondition'))
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
    check('real: the run-reached population sits between the two (no type outside the 13a population)',
          set(ni) <= set(real['run']) <= set(allr), (sorted(set(real['run']) - set(allr)), sorted(set(ni) - set(real['run']))))
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
        return usage.check_table(p, src, runset)[0]
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
    print(f'---- {len(fails)} failed')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
