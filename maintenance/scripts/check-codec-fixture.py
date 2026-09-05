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
from codec_parser import parse_chain, find_source, file_coverage

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
    if not ch.covered:
        problems.append(f"coverage gap {ch.coverage_gap} within its own fragment")
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
    if 'expect_parent' in case and (ch.parent or None) != case['expect_parent']:
        problems.append(f"parent {ch.parent!r} != {case['expect_parent']!r}")
    if len(ch.keys) != case['expect_keys']:
        problems.append(f"keys {len(ch.keys)} != {case['expect_keys']}")
    if 'expect_required' in case and got_req != sorted(case['expect_required']):
        problems.append(f"required {got_req} != {sorted(case['expect_required'])}")
    if 'expect_raw' in case and got_raw != sorted(case['expect_raw']):
        problems.append(f"raw {got_raw} != {sorted(case['expect_raw'])}")
    if 'expect_builder' in case and ch.builder_field != case['expect_builder']:
        problems.append(f"builder field {ch.builder_field} != {case['expect_builder']}")
    if 'expect_has_key' in case and case['expect_has_key'] not in [k.name for k in ch.keys]:
        problems.append(f"key {case['expect_has_key']!r} missing")
    if case.get('expect_covered') and not ch.covered:
        problems.append(f"coverage gap {ch.coverage_gap} (file declares {ch.declared_in_file})")
    if not ch.consistent:
        problems.append(f"self-check appends={ch.appends} adds={ch.adds} keys={len(ch.keys)}")
    if problems:
        t_bad += 1; fails.append((case['label'], '; '.join(problems)))
    else:
        t_ok += 1
        if a.verbose:
            print(f"  ok  trap: {case['label']}")

# --- corpus coverage: the denominator the fixture alone cannot provide --------
# 44 interaction types are 44 samples of ONE shape. A green fixture says nothing
# about the other shapes in the corpus, which is how a parser that read ZERO keys
# from Item (59 of them, the most-documented asset type here) reported clean.
# So sweep every class that has a builder chain AND at least one `new KeyedCodec`,
# and count the ones we read nothing from.
import re
BASELINE_BLIND = 23      # classes yielding 0 keys while declaring some (build-26)
BASELINE_NOFIELD = 21    # classes whose codec field is not named plainly CODEC
blind = nofield = swept = uncovered = filegap = 0
for jp in root.rglob('*.java'):
    src = jp.read_text(errors='replace')
    if 'BuilderCodec.builder' not in src and 'AssetBuilderCodec' not in src:
        continue
    if not re.search(r'new\s+KeyedCodec', src):
        continue
    swept += 1
    c = parse_chain(src)
    if c is None:
        nofield += 1
    elif not c.keys:
        blind += 1
    elif not c.covered:
        uncovered += 1
    got, dec = file_coverage(src)
    if got < dec:
        filegap += 1
if swept == 0:
    # Same discipline as the README gate: a sweep that examined nothing is a broken
    # check, not a clean corpus. Without this, an empty ~/.cache/hytale-jar/src
    # gives swept=0, blind=0, 0 <= baseline, and a green run.
    bad += 1
    fails.append(("corpus sweep", "examined 0 classes — treating as a broken check, not a clean run"))
print(f"\nCORPUS  {swept} class(es) swept: {blind} read as zero keys while declaring some "
      f"(baseline {BASELINE_BLIND}), {nofield} with no field named CODEC (baseline {BASELINE_NOFIELD}), "
      f"{uncovered} chain(s) short of their own fragment, {filegap} file(s) with an unread codec")
if uncovered:
    bad += 1
    fails.append(("corpus coverage", f"{uncovered} chain(s) read fewer keys than their own parsed fragment declares"))
if blind > BASELINE_BLIND:
    bad += 1
    fails.append(("corpus blind spots", f"{blind} > baseline {BASELINE_BLIND} — the parser lost coverage"))

print(f"\nFIXTURE {len(types)} type(s): {ok} reproduced, {bad} mismatched, "
      f"{unresolved} source(s) not found")
print(f"TRAPS   {len(traps['cases'])} case(s): {t_ok} handled, {t_bad} mishandled")
bad += t_bad
for t, why in fails:
    print(f"  MISMATCH {t}: {why}")
sys.exit(0 if bad == 0 and unresolved == 0 else 1)

