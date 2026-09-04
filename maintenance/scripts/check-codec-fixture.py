#!/usr/bin/env python3
"""
Run codec_parser against the golden fixture (§11's 44 interaction types).

Per CLAUDE.md's queued gate 1, phase (a): the parser must reproduce a known-good
answer set before any gate consumes it. §11's figures were derived independently
twice and reconciled, which makes them the best fixture available in this repo.

Usage:  python3 maintenance/scripts/check-codec-fixture.py [--src DIR] [-v]
Exit 0 when every type matches on key count, key names and required-set.
"""
import json, os, pathlib, sys, argparse
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from codec_parser import parse_chain, find_source

ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
ap.add_argument('-v', '--verbose', action='store_true')
a = ap.parse_args()

root = pathlib.Path(a.src)
if not root.exists():
    sys.exit(f"FAIL  decompiled source not found at {root}\n"
             "      build it with maintenance/scripts/build-jar-cache.sh")

fx = json.loads((pathlib.Path(__file__).parents[1] /
                 'fixtures/registry-oracle/tail-44.json').read_text())
types = fx['types']

INTERACTION_PKG = 'com.hypixel.hytale.server.core.modules.interaction.interaction'
def resolve(cls):
    """§11 abbreviates two prefixes; everything else is already unambiguous."""
    if cls.startswith(('config.client.', 'config.none.', 'config.server.')):
        return f'{INTERACTION_PKG}.{cls}'
    if cls.startswith('objectives.interactions.'):
        return 'com.hypixel.hytale.builtin.adventure.' + cls
    return cls

ok = bad = unresolved = 0
fails = []
for typ, exp in sorted(types.items()):
    cls = resolve(exp['class'])
    if '.' not in cls:                       # bare simple name: search the tree
        hits = [p for p in root.rglob(cls + '.java') if '/protocol/' not in str(p)]
        path = hits[0] if len(hits) == 1 else None
        if len(hits) > 1:
            fails.append((typ, f'AMBIGUOUS simple name, {len(hits)} candidates')); bad += 1; continue
    else:
        path = find_source(cls, root)
    if path is None:
        unresolved += 1
        fails.append((typ, f'source not found: {cls}')); continue

    ch = parse_chain(path.read_text())
    if ch is None:
        fails.append((typ, 'no CODEC chain found')); bad += 1; continue

    got_keys = [k.name for k in ch.keys]
    got_req = sorted(k.name for k in ch.keys if k.required)
    exp_keys = exp.get('keys')
    exp_req = sorted(exp['required'])

    problems = []
    if len(got_keys) != exp['own_keys']:
        problems.append(f"own_keys {len(got_keys)} != {exp['own_keys']} (got {got_keys})")
    if exp_keys is not None and got_keys != exp_keys:
        problems.append(f"key names {got_keys} != {exp_keys}")
    if got_req != exp_req:
        problems.append(f"required {got_req} != {exp_req}")
    if not ch.consistent:
        problems.append(f"self-check appends={ch.appends} adds={ch.adds} keys={len(ch.keys)}")
    if problems:
        bad += 1; fails.append((typ, '; '.join(problems)))
    else:
        ok += 1
        if a.verbose:
            flags = ''.join('R' if k.raw_keyedcodec else '' for k in ch.keys)
            print(f"  ok  {typ:28} {len(got_keys)} key(s)"
                  f"{'  raw KeyedCodec present' if flags else ''}")

# --- known traps: the documented ways to be confidently wrong ---------------
traps = json.loads((pathlib.Path(__file__).parents[1] /
                    'fixtures/registry-oracle/known-traps.json').read_text())
t_ok = t_bad = 0
for case in traps['cases']:
    path = root / case['path']
    if not path.exists():
        t_bad += 1; fails.append((case['label'], f"source not found: {case['path']}")); continue
    ch = parse_chain(path.read_text())
    if ch is None:
        t_bad += 1; fails.append((case['label'], 'no CODEC chain found')); continue
    got_req = sorted(k.name for k in ch.keys if k.required)
    got_raw = sorted(k.name for k in ch.keys if k.raw_keyedcodec)
    problems = []
    if len(ch.keys) != case['expect_keys']:
        problems.append(f"keys {len(ch.keys)} != {case['expect_keys']}")
    if got_req != sorted(case['expect_required']):
        problems.append(f"required {got_req} != {sorted(case['expect_required'])}")
    if got_raw != sorted(case['expect_raw']):
        problems.append(f"raw {got_raw} != {sorted(case['expect_raw'])}")
    if not ch.consistent:
        problems.append(f"self-check appends={ch.appends} adds={ch.adds} keys={len(ch.keys)}")
    if problems:
        t_bad += 1; fails.append((case['label'], '; '.join(problems)))
    else:
        t_ok += 1
        if a.verbose:
            print(f"  ok  trap: {case['label']}")

print(f"\nFIXTURE {len(types)} type(s): {ok} reproduced, {bad} mismatched, "
      f"{unresolved} source(s) not found")
print(f"TRAPS   {len(traps['cases'])} case(s): {t_ok} handled, {t_bad} mishandled")
bad += t_bad
for t, why in fails:
    print(f"  MISMATCH {t}: {why}")
sys.exit(0 if bad == 0 and unresolved == 0 else 1)

