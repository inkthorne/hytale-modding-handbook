#!/usr/bin/env python3
"""
Run registry_miner against the phase-(b) fixture.

The fixture separates two kinds of figure and only one of them can validate the
miner. `independent` figures were derived BY HAND in registry-oracle-notes.md
§1-§2 before this miner existed; reproducing them is evidence. `measured`
figures came from this miner and are regression baselines only — checking a
miner against its own output proves nothing, which is the same circularity
CLAUDE.md invariant 7 warns about for detectors and their matches.

Usage: python3 maintenance/scripts/check-registry-fixture.py [--src DIR] [-v]
"""
import json, os, pathlib, sys, argparse, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import registry_miner as rm

ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
ap.add_argument('-v', '--verbose', action='store_true')
a = ap.parse_args()

root = pathlib.Path(a.src)
if not root.exists():
    sys.exit(f"FAIL  decompiled source not found at {root}\n"
             "      build it with maintenance/scripts/build-jar-cache.sh")

fx = json.loads((pathlib.Path(__file__).parents[1] /
                 'fixtures/registry-oracle/registries.json').read_text())
ind, meas = fx['independent'], fx['measured']
regs = rm.mine(root)
fails, checks = [], 0


def check(label, got, want):
    global checks
    checks += 1
    if got != want:
        fails.append(f"{label}: {got!r} != {want!r}")
    elif a.verbose:
        print(f"  ok  {label} = {got!r}")


# --- Interaction.CODEC: the headline §1 measurement -------------------------
i = next((r for r in regs.values() if r.key.endswith('.Interaction.CODEC')), None)
if i is None:
    fails.append("Interaction.CODEC not found at all")
else:
    e = ind['interaction_codec']
    check("Interaction.CODEC names", len(i.names), e['names'])
    check("Interaction.CODEC form-1 registrations", i.forms()[1], e['form1_registrations'])
    check("Interaction.CODEC form-2 registrations", i.forms()[2], e['form2_registrations'])
    check("Interaction.CODEC form-2 statements", i.statements(2), e['form2_statements'])
    check("Interaction.CODEC verdict", i.verdict, e['verdict'])

# --- field table, counted in STATEMENTS (that is what §1's table counted) ---
stmt = collections.defaultdict(lambda: [0, 0])
for r in regs.values():
    stmt[r.field][0] += r.statements(2)
    stmt[r.field][1] += r.statements(1)
for fld, want in ind['field_statements'].items():
    check(f"{fld} form-2 statements", stmt[fld][0], want['form2'])
    check(f"{fld} form-1 statements", stmt[fld][1], want['form1'])

# --- the three verdicts -----------------------------------------------------
for key in ind['open_registries'] + ind['indirect_registries']:
    r = regs.get(key)
    check(f"open verdict: {key.rsplit('.',2)[-2]}.{key.rsplit('.',1)[-1]}",
          r.verdict if r else 'MISSING', 'open')
for key in ind['closed_despite_nonliteral_arg0']['examples']:
    r = regs.get(key)
    check(f"closed despite non-literal arg0: {key.rsplit('.',2)[-2]}.{key.rsplit('.',1)[-1]}",
          r.verdict if r else 'MISSING', 'closed')

check("open registry count", sum(1 for r in regs.values() if r.verdict == 'open'),
      ind['open_registry_count']['value'])
amb = [(r.key, s) for r in regs.values() for s in r.sites if s.kind == 'ambiguous']
check("register calls with two top-level literals", len(amb), 0)

# --- form 3: core-component types, categorised by category() ----------------
# The independent route here is a NAMING CONVENTION (`Builder<Category>*`) plus the
# three constant-named sites it structurally cannot see. It agrees with category()
# resolution only after both corrections are applied, which is exactly why it is
# worth checking: a resolver bug would have to reproduce the convention's own blind
# spots to stay hidden.
cc = {k.rsplit('.', 1)[0]: r for k, r in regs.items()
      if r.field == rm.CORE_COMPONENT_FIELD}
c3 = ind['core_component_types']
check("core-component call sites",
      sum(len(r.sites) for r in cc.values()), c3['call_sites'])
check("core-component sites named by a constant",
      sum(1 for r in cc.values() for s in r.sites if s.kind == 'constant'),
      c3['constant_named'])
check("core-component categories", len(cc), len(c3['categories_resolved']))
for cat, want in c3['categories_resolved'].items():
    r = cc.get(cat)
    check(f"category {cat.rsplit('.', 1)[-1]}", len(r.sites) if r else 'MISSING', want)
check("core-component categories unresolved",
      len(cc.get(rm.UNRESOLVED_CATEGORY, rm.Registry('', '')).sites),
      c3['unresolved_categories'])
conv = c3['by_name_convention']
check("convention total + constants == call sites",
      conv['total'] + c3['constant_named'], c3['call_sites'])
diag = rm.core_component_diagnostics(root)
z = c3['zero_pins']
for k in ('files_with_two_category_declarations',
          'extends_first_match_not_own_class',
          'builder_simple_names_ambiguous_in_tree'):
    check(f"zero-pin {k}", diag[k], z[k])
# The type-variable pin is checked by asking the resolver directly: Builder
# declares `Class<T> category()`, so if the guard is removed this returns a
# plausible FQCN instead of None and the whole resolver can silently mis-key.
check("zero-pin category_returning_a_type_variable",
      0 if rm._category_of(
          'Builder',
          {'Builder': 'com.hypixel.hytale.server.npc.asset.builder.Builder'},
          '', root) is None else 1,
      z['category_returning_a_type_variable'])

own_decl, inherited = [], 0
for p_ in root.rglob('*.java'):
    text = p_.read_text(errors='replace')
    if 'registerCoreComponentType' not in text:
        continue
    pkg_m = rm._PKG.search(text)
    imps = {x.rsplit('.', 1)[-1]: x for x in rm._IMPORT.findall(text)}
    for m_ in rm._FORM3.finditer(text):
        o = m_.end() - 1
        try:
            cl = rm._scan(text, o)
            ar = rm._split_args(text[o + 1:cl - 1])
        except (ValueError, AssertionError):
            continue
        if len(ar) < 2 or rm._DECLARATION.match(text, cl):
            continue
        ref = rm._CTOR_REF.match(ar[1].strip())
        if not ref:
            continue
        b = ref.group(1).split('.')[-1]
        f = (rm.find_source(rm._resolve_type(b, imps, pkg_m.group(1) if pkg_m else ''), root)
             or rm.find_source(b, root))
        if f and rm._CATEGORY.search(f.read_text(errors='replace')):
            own_decl.append(b)
        else:
            inherited += 1
check("categories resolved by inheritance", inherited, c3['resolved_by_inheritance'])
check("categories declared on the builder itself", len(own_decl),
      c3['resolved_by_own_declaration'])
check("which builders declare their own category",
      sorted(set(own_decl)), sorted(c3['own_declaration_builders']))

slots = collections.defaultdict(list)
for cat, r in cc.items():
    for n in r.names:
        slots[n].append(cat.rsplit('.', 1)[-1])
for name, want in c3['probes'].items():
    check(f"probe {name}", sorted(slots.get(name, [])), sorted(want))

# --- regression baselines (cannot validate, only detect drift) --------------
drift = []
if len(regs) != meas['registries']:
    drift.append(f"registry count {len(regs)} != {meas['registries']}")
got2 = sorted(r.key for r in regs.values() if r.forms()[1] == 0 and r.forms()[2] > 0)
if got2 != meas['second_form_only']:
    drift.append(f"second-form-only set changed ({len(got2)} vs {len(meas['second_form_only'])})")

print(f"\nINDEPENDENT {checks} check(s) against hand-derived §1/§2 figures: "
      f"{checks - len(fails)} reproduced, {len(fails)} failed")
for f in fails:
    print(f"  FAIL {f}")
print(f"BASELINE    {len(regs)} registries, {sum(len(r.sites) for r in regs.values())} registrations, "
      f"{sum(1 for r in regs.values() if r.verdict == 'open')} open"
      + ("" if not drift else "  — DRIFT:"))
for d in drift:
    print(f"  drift {d}")
sys.exit(1 if fails else 0)
