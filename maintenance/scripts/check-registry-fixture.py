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
