#!/usr/bin/env python3
"""
Run codec_parser against the golden fixture (§11's 44 interaction types).

Per CLAUDE.md's queued gate 1, phase (a): the parser must reproduce a known-good
answer set before any gate consumes it. §11's figures were derived independently
twice and reconciled, which makes them the best fixture available in this repo.

Two sets are asserted for every key, never their union: `null_validated` (the
field's validator chain holds a NonNullValidator instance; the only thing that makes
an OMITTED key fail decode) and `strict_null` (the KeyedCodec's `true` third argument,
which does not). Both were measured live: maintenance/probes/requiredness/run.sh.

Usage:  python3 maintenance/scripts/check-codec-fixture.py [--src DIR] [-v] [--mutations]
Exit 0 when every type matches on key count, key names and both sets.

--mutations reverts each guard the requiredness pass added, one at a time, on a copy of
the scripts, and requires the named checks (the MISMATCH labels below) to go red. It
reruns this script once per mutation (~MUT_SECONDS s each); run it by hand whenever
codec_parser.py or this file changes. MIN_MUTATIONS is the floor on how many ran.
"""
import json, os, pathlib, sys, argparse
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import codec_parser
from codec_parser import parse_chain, find_source, file_coverage, all_chains, derive_null_validators, _PINNED

ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--mutations', action='store_true')
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
    got_nv = sorted(k.name for k in ch.keys if k.null_validated)
    got_sn = sorted(k.name for k in ch.keys if k.strict_null)
    exp_keys = exp.get('keys')

    problems = []
    if len(got_keys) != exp['own_keys']:
        problems.append(f"own_keys {len(got_keys)} != {exp['own_keys']} (got {got_keys})")
    if exp_keys is not None and got_keys != exp_keys:
        problems.append(f"key names {got_keys} != {exp_keys}")
    if got_nv != sorted(exp['null_validated']):
        problems.append(f"null_validated {got_nv} != {sorted(exp['null_validated'])}")
    if got_sn != sorted(exp['strict_null']):
        problems.append(f"strict_null {got_sn} != {sorted(exp['strict_null'])}")
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


def judge(case, ch):
    """Compare one parsed chain with a trap case; returns the problems."""
    names = lambda pred: sorted(k.name for k in ch.keys if pred(k))
    got_nv, got_sn = names(lambda k: k.null_validated), names(lambda k: k.strict_null)
    got_raw = names(lambda k: k.raw_keyedcodec)
    problems = []
    if 'expect_parent' in case and (ch.parent or None) != case['expect_parent']:
        problems.append(f"parent {ch.parent!r} != {case['expect_parent']!r}")
    if 'expect_keys' in case and len(ch.keys) != case['expect_keys']:
        problems.append(f"keys {len(ch.keys)} != {case['expect_keys']}")
    if 'expect_null_validated' in case and got_nv != sorted(case['expect_null_validated']):
        problems.append(f"null_validated {got_nv} != {sorted(case['expect_null_validated'])}")
    if 'expect_strict_null' in case and got_sn != sorted(case['expect_strict_null']):
        problems.append(f"strict_null {got_sn} != {sorted(case['expect_strict_null'])}")
    for n in case.get('expect_null_validated_contains', []):
        if n not in got_nv:
            problems.append(f"{n!r} should be null_validated, got {got_nv}")
    for n in case.get('expect_null_validated_excludes', []):
        if n in got_nv:
            problems.append(f"{n!r} must NOT be null_validated (got {got_nv})")
    if 'expect_raw' in case and got_raw != sorted(case['expect_raw']):
        problems.append(f"raw {got_raw} != {sorted(case['expect_raw'])}")
    if 'expect_builder' in case and ch.builder_field != case['expect_builder']:
        problems.append(f"builder field {ch.builder_field} != {case['expect_builder']}")
    if 'expect_kind' in case and ch.kind != case['expect_kind']:
        problems.append(f"kind {ch.kind} != {case['expect_kind']}")
    if 'expect_has_key' in case and case['expect_has_key'] not in [k.name for k in ch.keys]:
        problems.append(f"key {case['expect_has_key']!r} missing")
    if case.get('expect_covered') and not ch.covered:
        problems.append(f"coverage gap {ch.coverage_gap} (file declares {ch.declared_in_file})")
    if not ch.consistent:
        problems.append(f"self-check appends={ch.appends} adds={ch.adds} keys={len(ch.keys)}")
    if ch.unparsed_tails:
        problems.append(f"{ch.unparsed_tails} validator tail(s) did not parse to .add()")
    return problems


for case in traps['cases']:
    path = root / case['path']
    if not path.exists():
        t_bad += 1; fails.append((case['label'], f"source not found: {case['path']}")); continue
    ch = parse_chain(path.read_text(), 'CODEC', case.get('occurrence') or 0)
    if ch is None:
        t_bad += 1; fails.append((case['label'], 'no CODEC chain found')); continue
    problems = judge(case, ch)
    if problems:
        t_bad += 1; fails.append((case['label'], '; '.join(problems)))
    else:
        t_ok += 1
        if a.verbose:
            print(f"  ok  trap: {case['label']}")

# --- inline cases: synthetic sources, because some shapes have no real instance --------
# (a key carrying ONLY nonEmptyMap() does not exist at 0.7.2, so subclass detection for it
# can only be tested on a source written for the purpose.)
i_ok = i_bad = 0
for case in traps['inline']:
    ch = parse_chain(case['src'], 'CODEC')
    if ch is None:
        i_bad += 1; fails.append((case['label'], 'no CODEC chain found')); continue
    problems = judge(case, ch)
    if problems:
        i_bad += 1; fails.append((case['label'], '; '.join(problems)))
    else:
        i_ok += 1
        if a.verbose:
            print(f"  ok  inline: {case['label']}")

# --- the NonNullValidator table: derived from source, pinned in the parser -------------
# A game update that adds a subclass or a factory must fail here, not narrow the attribute
# silently.
table_ok = True
derived = derive_null_validators(root)
if derived != _PINNED:
    table_ok = False
    fails.append(("validator table", f"derived from source {derived} != pinned {_PINNED}"))
if codec_parser.null_validators() != _PINNED:
    table_ok = False
    fails.append(("validator table", "the table in force differs from the pinned one"))

# --- corpus coverage: the denominator the fixture alone cannot provide --------
# 44 interaction types are 44 samples of ONE shape. A green fixture says nothing
# about the other shapes in the corpus, which is how a parser that read ZERO keys
# from Item (59 of them, the most-documented asset type here) reported clean.
# So sweep every class that has a builder chain AND at least one `new KeyedCodec`,
# and count the ones we read nothing from.
import re
# validator mentions that look like null-validation and are not NonNullValidator instances
NOT_INSTANCES = {'Validators.nonNullArrayElements()', 'Validators.nonEmptyString()',
                 'Validators.nonEmptyFloatArray()', 'Validators.nonEmptyDoubleArray()'}
vk = vstrict = vnull = vboth = vsub = vtails = vchains = 0
vstray = []
BASELINE_BLIND = 23      # classes yielding 0 keys while declaring some (build-26)
BASELINE_NOFIELD = 22    # classes whose codec field is not named plainly CODEC (21 at build-26; +EditorPropertyGallery in 0.7.2)
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
# Validators are swept over EVERY file declaring a KeyedCodec, not only the BuilderCodec
# files above: RecordCodec classes keep their validators inside the append group and are
# exactly the files that sweep never visits.
vfiles = 0
for jp in root.rglob('*.java'):
    src = jp.read_text(errors='replace')
    if not re.search(r'new\s+KeyedCodec', src):
        continue
    vfiles += 1
    for ac in all_chains(src):
        vchains += 1
        vtails += ac.unparsed_tails
        for k in ac.keys:
            vk += 1
            vstrict += k.strict_null
            vnull += k.null_validated
            vboth += k.strict_null and k.null_validated
            vsub += k.null_validated and not any(v == 'nonNull' for v in k.null_validators)
            for ov in k.other_validators:
                if re.search(r'(?i)nonnull|nonempty', ov) and ov not in NOT_INSTANCES:
                    vstray.append(f"{jp.name}:{k.name}: {ov[:60]}")
if swept == 0:
    # Same discipline as the README gate: a sweep that examined nothing is a broken
    # check, not a clean corpus. Without this, an empty ~/.cache/hytale-jar/src
    # gives swept=0, blind=0, 0 <= baseline, and a green run.
    bad += 1
    fails.append(("corpus sweep", "examined 0 classes — treating as a broken check, not a clean run"))
print(f"\nCORPUS  {swept} class(es) swept: {blind} read as zero keys while declaring some "
      f"(baseline {BASELINE_BLIND}), {nofield} with no field named CODEC (baseline {BASELINE_NOFIELD}), "
      f"{uncovered} chain(s) short of their own fragment, {filegap} file(s) with an unread codec")
print(f"VALIDATORS {vk} key(s) in {vchains} chain(s) of {vfiles} file(s): {vstrict} strict_null (true flag), {vnull} null_validated "
      f"({vsub} of them only via a NonNullValidator subclass), {vboth} both; "
      f"{vtails} validator tail(s) unparsed, {len(vstray)} unclassified null-looking validator(s); "
      f"validator table {codec_parser._table_cache.get('source')}")
if vk == 0 or vnull == 0:
    bad += 1
    fails.append(("corpus: validators", f"examined {vk} key(s), {vnull} null_validated - a broken check, not a clean run"))
if vtails:
    bad += 1
    fails.append(("corpus: validator tails", f"{vtails} append group(s) whose validators did not parse to .add()"))
if vstray:
    bad += 1
    fails.append(("corpus: unclassified validators", f"{len(vstray)} validator(s) mention nonNull/nonEmpty and were not resolved: {vstray[:3]}"))
if uncovered:
    bad += 1
    fails.append(("corpus coverage", f"{uncovered} chain(s) read fewer keys than their own parsed fragment declares"))
if blind > BASELINE_BLIND:
    bad += 1
    fails.append(("corpus blind spots", f"{blind} > baseline {BASELINE_BLIND} — the parser lost coverage"))

MIN_MUTATIONS = 8
MUT_SECONDS = 3
PARSER = 'codec_parser.py'
# Each mutation reintroduces ONE defect in a copy of the parser and names the checks (the
# MISMATCH labels this script prints) that must go red. A named check that stays green is a
# check that is not about that guard; a patch that no longer applies means the parser moved
# (update the mutation, do not delete it).
T_NN = "null_validated by Validators.nonNull() attached AFTER append(...) closes"
T_STRICT = "raw KeyedCodec + true THIRD ARGUMENT = strict_null, NOT required"
T_INNER = "raw KeyedCodec + true INSIDE the inner constructor = not strict_null"
T_SUB = "nonEmptyArray() is a NonNullValidator subclass: the literal `nonNull()` text misses it"
T_ANIM = "nonEmptyArray() alone, then an .addField() key after it"
T_ADDF = ".addField() keys do not inherit the next append's validators"
T_REC = "RecordCodec: the validator is INSIDE the append group, not after it"
I_SUB = "inline: subclass-only, explicit INSTANCE, composite and element validators"
I_ADDF = "inline: addField followed by an append that has nonNull"
I_REC = "inline: RecordCodec with lambda, direct and absent validators"
MUTATIONS = [
    ("(i) attribute reverted to arg-OR-validator: the true flag also sets null_validated", PARSER,
     "        k.strict_null = True\n", "        k.strict_null = True; k.null_validated = True\n",
     {"RunOnBlockTypes", T_STRICT}),
    ("(ii) validator detection disabled", PARSER,
     "        kind = classify_validator(ex)\n", "        kind = None\n",
     {"AddItem", "RunOnBlockTypes", T_NN, I_SUB}),
    ("(iii) the inner constructor's trailing true is attributed to the outer KeyedCodec", PARSER,
     "    if len(args) >= 3 and args[2].strip() == 'true':\n",
     "    if re.search(r',\\s*true\\s*\\)*\\s*$', arg[i+1:_scan(arg, i)-1]):\n",
     {T_INNER}),
    ("(iv) subclass detection removed: only the literal nonNull counts", PARSER,
     "SUBCLASS_DETECTION = True ", "SUBCLASS_DETECTION = False",
     {"RunOnBlockTypes", T_SUB, T_ANIM, I_SUB}),
    ("(v) an .addField() key scans on into the next append's validators", PARSER,
     "            pass\n        elif kind == 'record':\n",
     "            j = close\n            while j < len(stmt):\n                if stmt[j] in OPEN:\n"
     "                    if stmt.startswith('.add(', j - 4):\n                        break\n"
     "                    j = _scan(stmt, j); continue\n                j += 1\n"
     "            if 'Validators.nonNull()' in stmt[close:j]:\n                key.null_validated = True\n"
     "        elif kind == 'record':\n",
     {T_ADDF, I_ADDF}),
    ("(vi) a substring match instead of the whole expression", PARSER,
     "    e = expr.strip()\n    t = null_validators()\n",
     "    e = expr.strip()\n    if 'nonNull()' in e:\n        return 'nonNull'\n    t = null_validators()\n",
     {I_SUB}),
    ("(vii) RecordCodec validators (inside the append group) ignored", PARSER,
     "    if len(args) < 3:\n        return [], True\n", "    return [], True\n",
     {T_REC, I_REC}),
    ("(viii) the derived factory table stops at the literal NonNullValidator", PARSER,
     "        if m.group(2) in classes:\n            factories[m.group(1)] = m.group(2)\n",
     "        if m.group(2) == 'NonNullValidator':\n            factories[m.group(1)] = m.group(2)\n",
     {"validator table"}),
]


def run_mutations():
    import re as _re, shutil, subprocess, tempfile
    ran, bad = 0, []
    scripts_dir = pathlib.Path(__file__).parent
    for label, fname, old, new, must_red in MUTATIONS:
        with tempfile.TemporaryDirectory() as t:
            root_t = pathlib.Path(t)
            shutil.copytree(scripts_dir, root_t / 'maintenance/scripts', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(scripts_dir.parent / 'fixtures', root_t / 'maintenance/fixtures')
            f = root_t / 'maintenance/scripts' / fname
            src_t = f.read_text()
            if src_t.count(old) != 1:
                bad.append(f"{label}: patch no longer applies to {fname} ({src_t.count(old)} match(es))"); continue
            f.write_text(src_t.replace(old, new))
            r = subprocess.run([sys.executable, '-I', str(root_t / 'maintenance/scripts/check-codec-fixture.py'),
                                '--src', a.src], capture_output=True, text=True)
            ran += 1
            # labels contain ": " themselves (the inline cases), so match known labels by prefix
            red_lines = [l for l in r.stdout.splitlines() if l.startswith('  MISMATCH ')]
            red = {m for m in must_red if any(l.startswith(f"  MISMATCH {m}: ") for l in red_lines)}
            if r.returncode == 0:
                bad.append(f"{label}: the whole fixture stayed green")
            stayed = sorted(must_red - red)
            if stayed:
                bad.append(f"{label}: still green: {'; '.join(stayed)}")
            elif a.verbose:
                print(f"  red {label}: {len(red_lines)} check(s) failed, including all {len(must_red)} expected")
    return ran, bad


print(f"\nFIXTURE {len(types)} type(s): {ok} reproduced, {bad} mismatched, "
      f"{unresolved} source(s) not found")
print(f"TRAPS   {len(traps['cases'])} case(s): {t_ok} handled, {t_bad} mishandled; "
      f"{len(traps['inline'])} inline: {i_ok} handled, {i_bad} mishandled")
bad += t_bad + i_bad + (0 if table_ok else 1)
for t, why in fails:
    print(f"  MISMATCH {t}: {why}")
if a.mutations:
    if bad or unresolved:
        print("MUTATIONS 0 run: the unmutated fixture is not green, so no mutation can mean anything")
        sys.exit(1)
    ran, mbad = run_mutations()
    if ran < MIN_MUTATIONS:
        mbad.append(f"only {ran} mutation(s) ran, floor is {MIN_MUTATIONS}")
    print(f"MUTATIONS {ran} defect(s) reintroduced, {ran - len([b for b in mbad if 'still green' in b or 'stayed green' in b])} turned their checks red")
    for m in mbad:
        print(f"  FAIL {m}")
    sys.exit(1 if mbad else 0)
sys.exit(0 if bad == 0 and unresolved == 0 else 1)

