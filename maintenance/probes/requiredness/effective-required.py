#!/usr/bin/env python3
"""
effective-required — which codec keys does the ENGINE say are required? Measured, then
compared with what codec_parser.py predicts statically.

For every top-level class that declares a BuilderCodec `CODEC`, EffectiveRequired.java
decodes an EMPTY document through the real codec with a collecting ExtraInfo and lists the
keys that failed. That set is the ground truth for "a key is required" (decode fails when it
is omitted), reached by running the jar rather than reading it, so it cannot share a failure
mode with the parser. This script compares the two:

  predicted(class) = keys the parser marks null_validated, on the chain and its parents
  measured(class)  = keys the engine reported

Expected relationship, and what each deviation means:
  measured  SUBSET OF  predicted        always: only a NonNullValidator instance rejects omission
  predicted - measured                  the validator is toothless: the field already holds a
                                        non-null value after construction (BuilderField.nullValidate
                                        reads the field through the getter). Split by whether the
                                        static default reads null (constructor-assigned) or not.
  measured - predicted                  must be EMPTY, except the parser blind spots listed in
                                        KNOWN_UNEXPLAINED (codecs finished in a `static {}` block)

Usage:  python3 maintenance/probes/requiredness/effective-required.py [-v] [--src DIR] [--jar JAR]
Exit 0 when the relationship holds AND the pinned figures are unchanged; 1 on a deviation or a
moved figure; 2 when the run is void (negative controls); 3 when the jar or source is missing.
Flags: --jar PATH (HytaleServer.jar), --src DIR (decompiled source cache), --out FILE, -v.
"""
import argparse, collections, os, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
from codec_parser import find_source, parse_chain
import defaults_probe as dp

ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
ap.add_argument('--jar', default=os.environ.get('HYTALE_SERVER_JAR', os.path.expanduser(
    '~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Server/HytaleServer.jar')))
ap.add_argument('--out', help='also write the raw measurement (TSV) here')
ap.add_argument('-v', '--verbose', action='store_true')
a = ap.parse_args()
src = pathlib.Path(a.src)
for label, p in (('decompiled source', src), ('HytaleServer.jar', pathlib.Path(a.jar))):
    if not p.exists():
        print(f"FAIL  {label} not found at {p}", file=sys.stderr)
        sys.exit(3)

# Parser blind spots, recorded so a NEW unexplained key is a failure and these are not:
# the codec's parent or keys are attached in a `static {}` block the parser cannot read.
KNOWN_UNEXPLAINED = {('SelectInteraction', 'Selector'),   # first `CODEC` in the file is a nested class's
                     ('WorldNPCSpawn', 'NPCs'),           # parent NPCSpawn.BASE_CODEC is built in a static block
                     ('LaunchAbilityProjectileInteraction', 'Projectile')}  # CODEC = createCodec(): a factory method
# Negative controls: one class that MUST report a failing key, one with a nonNull key that
# MUST decode clean. If either flips, the harness is not measuring what this file says.
MUST_FAIL = ('com.hypixel.hytale.common.plugin.PluginManifest', {'Name'})
MUST_PASS = 'com.hypixel.hytale.builtin.augmentblocks.AugmentConditionInteraction'

names = []
for jp in sorted(src.rglob('*.java')):
    t = jp.read_text(errors='replace')
    # `CODEC;` too: 22 classes finish their codec in a `static {}` block, which the parser cannot
    # read but the engine can decode. They are measured, and counted apart (see `unparsed` below).
    # `BuilderCodec`, not `KeyedCodec`: a class with no keys of its own still inherits its parent's.
    if 'BuilderCodec' in t and re.search(r'\bstatic\s+final\s+[\w.<>?, ]+\s+CODEC\s*(?:=|;)', t):
        names.append(str(jp.relative_to(src))[:-5].replace('/', '.'))

with tempfile.TemporaryDirectory() as t:
    tmp = pathlib.Path(t)
    r = subprocess.run(['javac', '-nowarn', '-proc:none', '-cp', a.jar, '-d', str(tmp),
                        str(HERE / 'EffectiveRequired.java')], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAIL  EffectiveRequired.java did not compile:\n{r.stderr}")
    (tmp / 'in.txt').write_text('\n'.join(names) + '\n')
    r = subprocess.run(['java', '-cp', f'{tmp}:{a.jar}', 'EffectiveRequired', str(tmp / 'in.txt')],
                       capture_output=True, text=True, timeout=300)
    if r.returncode:
        sys.exit(f"FAIL  EffectiveRequired exited {r.returncode}:\n{r.stderr[:2000]}")
raw = r.stdout
if a.out:
    pathlib.Path(a.out).write_text(raw)
rows = [l.split('\t', 2) for l in raw.splitlines() if l.strip()]
measured = {}
hook_also = set()        # keys failed AND a key-less codec-level holder failed too
for n, st, d in rows:
    if st == 'KEYS' and d.endswith('|CODEC_LEVEL'):
        d = d[:-len('|CODEC_LEVEL')]
        hook_also.add(n)
    if st == 'THROW':
        # `Frames | Type: message`. A first frame that is a lambda of the class under test is its
        # own validator/afterDecode hook crashing on the empty document (BlockSpawnerTable:
        # a validator dereferencing Entries). Anything else is an unbooted singleton or the
        # harness not supplying an id, which says nothing about the document.
        simple = n.split('.')[-1].split('$')[-1]
        if d.split(' < ')[0].split('.')[0] == simple and '.lambda$' in d.split(' < ')[0]:
            st = 'HOOK_CRASH'
    measured[n] = (st, set(d.split(',')) if d and st == 'KEYS' else set())
status = collections.Counter(s for s, _ in measured.values())
print(f"MEASURED {len(names)} class(es) with a CODEC: " + ', '.join(f"{v} {k}" for k, v in sorted(status.items())))

if len(measured) != len(names):
    sys.exit(f"VOID  {len(measured)} result line(s) for {len(names)} class(es)")
if status['KEYS'] < 500:
    print(f"VOID  only {status['KEYS']} class(es) decoded; the floor is 500 - the harness is not running the codecs")
    sys.exit(2)
s, got = measured.get(MUST_FAIL[0], ('missing', set()))
if s != 'KEYS' or got != MUST_FAIL[1]:
    print(f"VOID  negative control: {MUST_FAIL[0].split('.')[-1]} should fail on {sorted(MUST_FAIL[1])}, got {s} {sorted(got)}")
    sys.exit(2)
s, got = measured.get(MUST_PASS, ('missing', set()))
if s != 'KEYS' or got:
    print(f"VOID  control: {MUST_PASS.split('.')[-1]} carries nonNull on a key with a non-null default and must decode clean, got {s} {sorted(got)}")
    sys.exit(2)

pred_fail = pass_nonnull = 0
pass_null, unresolved, unexplained, unparsed = [], [], [], []
classes_failing = 0
for name, (st, M) in sorted(measured.items()):
    if st != 'KEYS':
        continue
    classes_failing += bool(M)
    keys = {}
    chain0 = parse_chain(find_source(name, src).read_text(errors='replace'))
    if chain0 is None:
        # The parser reads no chain here (codec finished in a static block): nothing to
        # compare against, so these are counted, not judged.
        unparsed.append((name.split('.')[-1], sorted(M)))
        continue
    for p, txt, ch in dp.hops(find_source(name, src), src):
        if ch is not None:
            for k in ch.keys:
                keys.setdefault(k.name, k)
    try:
        defaults = dp.probe(name, src)
    except Exception:
        defaults = {}
    N = {k for k, x in keys.items() if x.null_validated}
    short = name.split('.')[-1]
    for k in sorted(M - N):
        unexplained.append((short, k))
    for k in sorted(N):
        if k in M:
            pred_fail += 1
            continue
        d = defaults.get(k)
        if d is None or d.value is None:
            unresolved.append((short, k, d.reason if d else 'not resolved'))
        elif d.value == 'null':
            pass_null.append((short, k, d.field, d.expr, d.origin))
        else:
            pass_nonnull += 1
npred = pred_fail + pass_nonnull + len(pass_null) + len(unresolved)
print(f"PREDICTED {npred} null_validated key(s) in {status['KEYS']} decodable class(es); the engine rejects the omission of {pred_fail}")
print(f"  {pass_nonnull} accept omission because the field already holds a non-null default")
print(f"  {len(pass_null)} accept omission although the initialiser reads null (assigned elsewhere, e.g. the constructor)")
print(f"  {len(unresolved)} accept omission, default not resolvable by defaults_probe")
keyless = sorted(n.split('.')[-1] for n, (st, _) in measured.items() if st == 'CODEC_LEVEL')
alongside = sorted(n.split('.')[-1] for n in hook_also)
crash = sorted(n.split('.')[-1] for n, (st, _) in measured.items() if st == 'HOOK_CRASH')
print(f"CODEC-LEVEL {len(keyless) + len(alongside)} class(es) reject an empty document through a codec-level validator or "
      f"afterDecode hook that names no key ({len(keyless)} only that, {len(alongside)} alongside failing keys), and {len(crash)} more "
      f"crash inside their own hook - outside every per-key attribute"
      + (f": {', '.join(keyless + alongside)}; crash: {', '.join(crash)}" if a.verbose else ''))
print(f"UNPARSED {len(unparsed)} decodable class(es) have no chain the parser can read (static-block codecs); the engine "
      f"rejects omitted keys in {sum(1 for _, m in unparsed if m)} of them")
print(f"UNEXPLAINED {len(unexplained)} key(s) failed that the parser does not mark null_validated "
      f"(known blind spots: {len(KNOWN_UNEXPLAINED)})")
if a.verbose:
    for x in pass_null: print('  pass-with-null-initialiser', x)
    for x in unresolved: print('  unresolved', x)
# The figures this probe and the handbook quote (CLAUDE.md invariant 7, README.md) are PINNED. A
# parser that stops reading validators moves "predicted" without touching "rejected" and would
# otherwise pass (a copy of the parser with the old union put back moved 545 -> 1236 with exit 0).
BASELINE = {'classes': 1491, 'decodable': 1257, 'predicted': 545, 'rejected': 258, 'non-null default': 252,
            'null initialiser, assigned elsewhere': 5, 'default unresolved': 30,
            'codec-level, names no key': 5, 'codec-level, alongside keys': 1, 'hook crash': 1, 'unparsed': 10}
GOT = {'classes': len(names), 'decodable': status['KEYS'], 'predicted': npred, 'rejected': pred_fail,
       'non-null default': pass_nonnull, 'null initialiser, assigned elsewhere': len(pass_null),
       'default unresolved': len(unresolved), 'codec-level, names no key': len(keyless),
       'codec-level, alongside keys': len(alongside), 'hook crash': len(crash), 'unparsed': len(unparsed)}
moved = {k: (BASELINE[k], GOT[k]) for k in BASELINE if BASELINE[k] != GOT[k]}
for k, (was, now) in moved.items():
    print(f"  FAIL pinned figure moved: {k}: {was} -> {now}")
if moved:
    print("  The figures in CLAUDE.md invariant 7 and probes/requiredness/README.md quote these. Game update:"
          " re-derive (run with -v), update BASELINE here and the quoted figures. No update: codec_parser or"
          " the harness regressed - the engine's side ('rejected') should not move on its own.")
bad = [x for x in unexplained if x not in KNOWN_UNEXPLAINED]
stale = sorted(KNOWN_UNEXPLAINED - set(unexplained))
for x in bad: print(f"  FAIL unexplained failing key {x}")
for x in stale: print(f"  FAIL known blind spot {x} no longer reproduces - remove it from KNOWN_UNEXPLAINED")
sys.exit(1 if bad or stale or moved else 0)
