#!/usr/bin/env python3
"""
Fixture for defaults_probe.py and check-defaults.py — WRITTEN BEFORE BOTH.

The rule this repo earned the hard way: a case that has never been red has never
been shown to fire, and the guard added last is the one that ships unverified
(seven instances over 2026-09-04/05, three of them in the guard written to prevent
exactly that). So every case below is red when this file is committed, and each
goes green only when the probe is built to satisfy it.

What it protects specifically. A defaults check compares a documented cell against
a field initialiser, and BOTH sides normalise. A normaliser that is too eager
manufactures disagreements — the first prototype of this check reported 14, and
every one of the 14 was its own bug: an enum-tail rule that took `1.3` apart into
`3`, and a literal-detector that read the bare word `Required` as a value. So the
disagreement cases here are the positive control and the agreement cases are the
false-positive control, and neither is optional.

Usage: python3 maintenance/scripts/check-defaults-fixture.py [-v]
"""
from __future__ import annotations
import argparse, contextlib, importlib.util, io, os, pathlib, re, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parents[0] / 'fixtures' / 'defaults'
CORPUS = FIX / 'corpus'
sys.path.insert(0, str(HERE))

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--from-dir', default=str(HERE),
                help='directory to load defaults_probe/check-defaults from — the '
                     'mutation harness points this at a patched copy')
ap.add_argument('--mutations', action='store_true',
                help='reintroduce each known defect and assert the EXACT set of '
                     'cases that must redden')
A = ap.parse_args()
FROM = pathlib.Path(A.from_dir)

fails: list[str] = []
checks = 0

# Floors. A fixture that can silently run no cases is the defect it exists to
# catch; MIN_* is asserted at the bottom against the count actually executed.
MIN_CASES = 61


def check(label, thunk, want):
    """`thunk` is ALWAYS a callable, enforced. An eagerly-evaluated argument that
    raises never reaches this function, so a harness reading only FAIL lines
    scores the crash as "no reds" — measured twice in this gate family."""
    global checks
    checks += 1
    if not callable(thunk):
        fails.append(f'{label}: check() takes a callable, got {type(thunk).__name__}')
        return
    try:
        got = thunk()
    except Exception as e:                      # noqa: BLE001
        fails.append(f'{label}: raised {type(e).__name__}: {e}')
        return
    if got != want:
        fails.append(f'{label}: {got!r} != {want!r}')
    elif A.verbose:
        print(f'  ok   {label}')


def expect_raises(label, fn, wanted_substr):
    global checks
    checks += 1
    try:
        fn()
    except Exception as e:                      # noqa: BLE001
        if wanted_substr in str(e):
            if A.verbose:
                print(f'  ok   {label}')
            return
        fails.append(f'{label}: raised {e!r}, wanted a message containing '
                     f'{wanted_substr!r}')
        return
    fails.append(f'{label}: did NOT fail — a floor that does not fire is not a floor')



# ---- the mutation harness ---------------------------------------------------
# The fixture guards the checker; this guards the fixture. Without it a case that
# has quietly stopped asserting anything still prints "passed", and on this gate's
# record that is where the defect goes: `MUTATIONS = {}` once printed "0 defect(s)
# reintroduced, expected red set asserted exactly" and exited 0.
#
# Each entry names a real defect this build actually shipped or nearly shipped,
# the file it lives in, the edit that reintroduces it, and the EXACT set of case
# labels that must go red. An exact set, not "at least one": a mutation that
# reddens more cases than expected means a case is asserting something other than
# what its label says.
MIN_MUTATIONS = 14

PROBE, GATE = 'defaults_probe.py', 'check-defaults.py'

MUTATIONS = {
    # THE CONTROL, and it comes first. An unchanged copy must pass every case. A
    # harness that reports every defect "caught" is usually measuring an import
    # failure in its own temp directory, which is what happened the first time a
    # sibling gate ran one of these.
    'IDENTITY (no change — the harness control)': (
        PROBE, '#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity)',
        set()),

    'a box is read as its primitive (the five interactions-flow accusations)': (
        PROBE, "        return PRIMITIVE_ZERO.get(base, 'null'), 'java-zero'",
        "        return {**PRIMITIVE_ZERO, 'Boolean': 'false', 'Integer': '0'}"
        ".get(base, 'null'), 'java-zero'",
        {'a boxed Boolean with no initialiser is null, not false',
         'a boxed Integer with no initialiser is null, not zero',
         'the primitive and its box are not the same default',
         'it reports exactly the three planted disagreements',
         'it prints the row-level breakdown too'}),

    'a JSON-quoted cell keeps its quotes (three more of the eight)': (
        PROBE, """    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]""", '    pass',
        {'a JSON-quoted literal drops the quotes, which are syntax not value',
         'an empty JSON string is still a literal, and it is empty',
         'it reports exactly the three planted disagreements',
         'it prints the row-level breakdown too'}),

    'a bare word is read as a literal (the `Required` accusation)': (
        PROBE, """    m = re.fullmatch(r'`([^`]*)`', c)
    if m is None:
        return None
    v = m.group(1)""", """    m = re.fullmatch(r'`([^`]*)`', c)
    v = m.group(1) if m else c""",
        {'an em dash is not a literal', 'an empty cell is not a literal',
         'italic prose is not a literal',
         'a bare word is not a literal — `Required` is a marker, not a value',
         'bold prose is not a literal',
         'it reports exactly the three planted disagreements',
         'it prints the row-level breakdown too',
         'it says how much of the evidence is an implicit zero'}),

    # THE DEFECT THAT MADE THE PROTOTYPE REPORT 14 DISAGREEMENTS. The dotted-name
    # rule ran first and its character class admitted digits, so `1.3` was read as
    # a qualified constant and its default reported as `3`.
    'the enum-tail rule runs before the numeric one and admits digits': (
        PROBE, """    if re.fullmatch(r'-?\\d[\\d_]*(\\.\\d*)?(e-?\\d+)?[fFdDlL]?', s):
        return re.sub(r'[fFdDlL]$', '', s.replace('_', '')), 'initialiser'""",
        """    if re.fullmatch(r'[\\w.]+', s) and '.' in s:
        return s.split('.')[-1], 'initialiser'
    if re.fullmatch(r'-?\\d[\\d_]*(\\.\\d*)?(e-?\\d+)?[fFdDlL]?', s):
        return re.sub(r'[fFdDlL]$', '', s.replace('_', '')), 'initialiser'""",
        {'a literal initialiser is the default',
         'a float suffix is not part of the value',
         'it reports exactly the three planted disagreements',
         'it prints the row-level breakdown too'}),

    'a two-field setter guesses the first instead of refusing': (
        PROBE, """    if len(hits) > 1:
        return None, f'setter assigns {len(hits)} fields'""",
        """    if len(hits) > 1:
        return sorted(hits)[0], ''""",
        {'a setter assigning two fields is refused, with a reason',
         'a refusal still names the key it refused',
         'it reports exactly the three planted disagreements',
         'it prints the row-level breakdown too',
         'it says how much of the evidence is an implicit zero'}),

    "the parent's codec FIELD NAME is dropped from the address": (
        PROBE, "hops(parent, src, fld or 'CODEC', _depth + 1, truncations)",
        "hops(parent, src, 'CODEC', _depth + 1, truncations)",
        {'the probe reports every key it saw, resolved or not',
         'a key declared on the parent chain resolves',
         'the record says which class declared the field',
         'it prints the row-level breakdown too',
         'it says how much of the evidence is an implicit zero',
         "an ambiguous parent resolves through the child's import",
         'and it resolves to the RIGHT one of the two'}),

    'SKIP returns 0 instead of 2 (the empty PASS, in this gate)': (
        GATE, '            return 2', '            return 0',
        {'a missing source tree SKIPs with exit 2, never 0'}),

    'the zero-floor is removed (a clean run over an empty corpus)': (
        GATE, """        print(f'  SKIP  nothing to check: {tables} Default-column table(s), '
              f'{rows} row(s), {len(usable)} bound section(s) — an oracle is '
              f'missing, not clean')
        return 2""",
        """        print(f'  INFO  {tables} table(s), {rows} row(s)')""",
        {'a corpus that binds but states no defaults SKIPs with exit 2, never PASS',
         "every SKIP line is indented where the caller's filter can see it"}),

    'the non-plain header spellings stop being printed': (
        GATE, """        if spelling.strip().lower() != 'default':""",
        """        if False:""",
        {'it prints every Default header spelling that is not plain'}),

    'the walk stops silently again (the eighth instance)': (
        PROBE, """        stop('ambiguous simple name and no import names it'
             if n > 1 else 'no source file for the parent class')
        return""",
        """        return""",
        {'an unresolvable parent truncates the walk WITH a reason',
         'the gate reports a truncated ancestry in its INFO block'}),

    "the child's import is no longer consulted for an ambiguous parent": (
        PROBE, """    if text is not None:
        for static_imp, imp in IMPORT.findall(text):""",
        """    if False:
        for static_imp, imp in IMPORT.findall(text or ''):""",
        {"an ambiguous parent resolves through the child's import",
         'and it resolves to the RIGHT one of the two',
         'a walk that completes records no truncation',
         'an unresolvable parent truncates the walk WITH a reason'}),

    'a receiver-less parent is read as a class name again': (
        PROBE, """    if not fld:""", """    if False:""",
        {'a receiver-less parent is another field on the same class',
         "and both fields' keys carry their own defaults",
         'a walk that completes records no truncation',
         'an unresolvable parent truncates the walk WITH a reason'}),

    'a filtered row is dropped instead of counted': (
        GATE, """                    if max(ki, di) >= len(cells):
                        bucket['row states no key'] += 1
                        noncell['row has fewer cells than the header'] += 1
                        continue""",
        """                    if max(ki, di) >= len(cells):
                        rows -= 1
                        continue""",
        {'it prints the row-level breakdown too',
         'it prints the row coverage, INCLUDING the rows outside the check',
         'every filtered row is counted, with the reason it was filtered'}),

    'the ROW denominator counts only what it could check': (
        GATE, """                all_rows += len(table_rows)
                if here is None:
                    continue""",
        """                if here is None:
                    continue
                all_rows += len(table_rows)""",
        {'it prints the row coverage, INCLUDING the rows outside the check'}),
}


def mutations() -> int:
    """Copy the scripts, patch one line, re-run THIS file against the copy."""
    import shutil
    rc = 0
    if len(MUTATIONS) < MIN_MUTATIONS:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s) defined, floor is '
              f'{MIN_MUTATIONS} — "exact red set asserted" over an empty dict is '
              f'a claim about zero things')
        return 1
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control — without it a harness that reddens '
              'everything for an unrelated reason reads as total coverage')
        return 1
    print(f'MUTATIONS {len(MUTATIONS)} defect(s) reintroduced, '
          f'expected red set asserted exactly')
    for label, (target, old, new, expect) in MUTATIONS.items():
        tmp = pathlib.Path(tempfile.mkdtemp())
        for f in HERE.glob('*.py'):
            shutil.copy2(f, tmp / f.name)
        srcfile = tmp / target
        body = srcfile.read_text()
        if body.count(old) != 1:
            print(f'  FAIL  {label}: the text to mutate occurs {body.count(old)} '
                  f'time(s) in {target}, wanted exactly 1 — the mutation is stale '
                  f'and this run measured nothing')
            rc = 1
            continue
        srcfile.write_text(body.replace(old, new, 1))
        # PYTHONDONTWRITEBYTECODE, because a restored file with an older mtime than
        # its cached bytecode reads as the mutant for a whole run. Measured.
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        run = subprocess.run([sys.executable, str(HERE / pathlib.Path(__file__).name),
                              '--from-dir', str(tmp)],
                             capture_output=True, text=True, env=env)
        out = run.stdout + run.stderr
        if 'Traceback (most recent call last)' in out and not expect:
            print(f'  FAIL  {label}: the CONTROL crashed — {out.strip().splitlines()[-1]}')
            rc = 1
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        red = {l.split(':')[0].removeprefix('  FAIL ').strip()
               for l in out.split('\n') if l.startswith('  FAIL ')}
        red = {r for r in red if not r.startswith('floor')}
        if red == expect:
            print(f'  ok    {label}  ({len(red)} case(s) red)')
        else:
            rc = 1
            print(f'  FAIL  {label}')
            for m in sorted(expect - red):
                print(f'          expected red, stayed green: {m}')
            for m in sorted(red - expect):
                print(f'          reddened unexpectedly:      {m}')
        shutil.rmtree(tmp, ignore_errors=True)
    print('MUTATIONS ' + ('all expected red sets matched' if rc == 0
                          else 'a red set did not match — see above'))
    return rc


if A.mutations:
    sys.exit(mutations())

sys.path.insert(0, str(FROM))
try:
    import defaults_probe as dp
except ImportError as e:
    print(f'  FAIL  defaults_probe not importable yet: {e}')
    print( '        Expected while the cases are being written before the probe.')
    sys.exit(1)

docs, src = CORPUS / 'docs', CORPUS / 'src'

# ---- floors first, because they are what ends up unverified -----------------
expect_raises('floor: a missing source tree is not a clean probe',
              lambda: dp.probe('defpkg.Widget', src / 'no-such-dir'),
              'not found')
expect_raises('floor: an empty source tree is not a clean probe',
              lambda: dp.probe('defpkg.Widget', pathlib.Path(tempfile.mkdtemp())),
              'not found')

W = dp.probe('defpkg.Widget', src)

# ---- the WALK must report where it stopped ----------------------------------
# `defaults_probe`'s own contract: every key it cannot resolve comes back with a
# reason and is counted. The refusals honour that; `hops()` did not — it hit
# `if parent is None: return` and dropped the rest of the ancestry with no reason
# and no counter. Eleven of the gate's bound classes were doing that, two of them
# inside the 13 direct-bound Default tables. It is the eighth appearance of the
# sentence, in the file whose docstring lists the first seven, and it was found by
# walking every bound class rather than by reading: the line looks like ordinary
# defensive code and the docstring three lines above it says the collision is
# handled.
# Crash-safe, like every other setup call in this file: a mutation that breaks the
# walk must produce FAIL lines, not an exception that a harness reading only
# `^  FAIL` scores as "no reds".
_trunc: list = []
try:
    _FAR = dp.probe('defpkg.other.Far', src, truncations=_trunc)
    _CHARGED = dp.probe('defpkg.Charged', src, truncations=_trunc)
    dp.probe('defpkg.Orphaned', src, truncations=_trunc)
    _walk_setup = None
except Exception as e:                          # noqa: BLE001
    _FAR = _CHARGED = {}
    _walk_setup = f'{type(e).__name__}: {e}'
check('the walk cases could be set up at all', lambda: _walk_setup, None)

# A: the ambiguous simple name, disambiguated by the child's own import. `Base.java`
# exists twice and `Far` lives under neither directory, so no upward walk reaches
# it — but `import defpkg.Base;` is written down in the child, which is the same
# imports-first resolution registry_miner._resolve_type already does.
check('an ambiguous parent resolves through the child\'s import',
      lambda: sorted(_FAR), ['Depth', 'Distance'])
check('and it resolves to the RIGHT one of the two',
      lambda: (_FAR['Depth'].declared_on, _FAR['Depth'].value),
      ('defpkg.core.Anchor', '9'))

# B: `chain.parent` with no receiver is a codec field on the SAME class, not a
# class named `ABSTRACT_CODEC`.
check('a receiver-less parent is another field on the same class',
      lambda: sorted(_CHARGED), ['Amps', 'Volts'])
check('and both fields\' keys carry their own defaults',
      lambda: (_CHARGED['Amps'].value, _CHARGED['Volts'].value), ('13', '240'))

# C: genuinely unresolvable. The walk stops — and SAYS SO.
check('an unresolvable parent truncates the walk WITH a reason',
      lambda: [(t.fqcn.split('.')[-1], t.parent, t.reason) for t in _trunc],
      [('Orphaned', 'Ghost.CODEC', 'no source file for the parent class')])
check('a walk that completes records no truncation',
      lambda: [t for t in _trunc if 'Far' in t.fqcn or 'Charged' in t.fqcn], [])
check('the truncation channel is optional, and probe still works without it',
      lambda: sorted(dp.probe('defpkg.Orphaned', src)), ['Own'])


def val(key):
    d = W.get(key)
    return None if d is None else d.value


def reason(key):
    d = W.get(key)
    return 'ABSENT' if d is None else (d.reason or '')


# ---- the denominator, before the values -------------------------------------
check('the probe reports every key it saw, resolved or not',
      lambda: sorted(W), sorted(['Boxed', 'BoxedNum', 'Cased', 'Count', 'Enabled',
                                 'Extras', 'Grace', 'Label', 'Mode', 'Name',
                                 'Quoted', 'Radius', 'Ratio', 'Retries', 'Shared',
                                 'Tag']))
check('a key on no chain and no ancestor is absent, not a silent None',
      lambda: 'Missing' in W, False)

# ---- resolution --------------------------------------------------------------
check('a literal initialiser is the default', lambda: val('Radius'), '1.5')
check('a float suffix is not part of the value', lambda: val('Ratio'), '30.0')
check('no initialiser on a numeric field is Java zero', lambda: val('Count'), '0')
check('no initialiser on a boolean is false', lambda: val('Enabled'), 'false')
check('no initialiser on a reference type is null', lambda: val('Name'), 'null')
check('an enum initialiser reports the constant, not the qualified name',
      lambda: val('Mode'), 'Fast')
# A BOX IS NOT ITS PRIMITIVE, and this is not a nicety. `private Boolean jumping;`
# defaults to null; read as `boolean` it defaults to `false`, and the checker then
# accuses `interactions-flow.md` of documenting `null` for five keys that are
# documented correctly. Five of the eight disagreements on this gate's first real
# run were this one line.
check('a boxed Boolean with no initialiser is null, not false',
      lambda: val('Boxed'), 'null')
check('a boxed Integer with no initialiser is null, not zero',
      lambda: val('BoxedNum'), 'null')
check('the primitive and its box are not the same default',
      lambda: (val('Enabled'), val('Boxed')), ('false', 'null'))
check('the origin distinguishes a written default from an implied one',
      lambda: (W['Radius'].origin, W['Count'].origin),
      ('initialiser', 'java-zero'))

# ---- the walk ----------------------------------------------------------------
# `Base.ABSTRACT_CODEC`, not `Base.CODEC`: the parent's FIELD NAME is part of the
# address, and a walk that keeps the receiver and drops the field finds nothing.
check('a key declared on the parent chain resolves', lambda: val('Retries'), '3')
check('a key on this chain whose FIELD is declared on the parent resolves',
      lambda: val('Shared'), '0')
check('the record says which class declared the field',
      lambda: (W['Radius'].declared_on, W['Retries'].declared_on),
      ('defpkg.Widget', 'defpkg.Base'))

# ---- what the probe must REFUSE ---------------------------------------------
# Each of these is a value the probe could guess at. Guessing is how the naive
# version of this check reached a 44% false-positive rate on a neighbouring gate.
check('a setter assigning two fields is refused, with a reason',
      lambda: (val('Grace'), reason('Grace')),
      (None, 'setter assigns 2 fields'))
check('a method-reference setter is refused, with a reason',
      lambda: (val('Tag'), reason('Tag')), (None, 'setter is not a lambda'))
check('a setter that assigns nothing is refused, with a reason',
      lambda: (val('Extras'), reason('Extras')),
      (None, 'setter assigns no field'))
check('a refusal still names the key it refused',
      lambda: sorted(k for k, d in W.items() if d.value is None),
      ['Extras', 'Grace', 'Tag'])

# ---- the documented side -----------------------------------------------------
# A cell is only comparable when it is a BACKTICKED literal. The prototype read
# the bare word `Required` as a value and reported three disagreements against
# `null`; requiring the backticks removes the whole class.
check('an em dash is not a literal', lambda: dp.doc_value('—'), None)
check('an empty cell is not a literal', lambda: dp.doc_value(''), None)
check('italic prose is not a literal',
      lambda: dp.doc_value('*inherited from Base*'), None)
check('a bare word is not a literal — `Required` is a marker, not a value',
      lambda: dp.doc_value('Required'), None)
check('bold prose is not a literal', lambda: dp.doc_value('**Required**'), None)
check('a backticked value is a literal', lambda: dp.doc_value('`1.5`'), '1.5')
check('a backticked value keeps its own spelling',
      lambda: dp.doc_value('`Fast`'), 'Fast')
# The docs write JSON, so a value cell is routinely `"Absolute"` — quotes included.
# Three of the eight first-run disagreements were the quotes.
check('a JSON-quoted literal drops the quotes, which are syntax not value',
      lambda: dp.doc_value('`"Absolute"`'), 'Absolute')
check('an empty JSON string is still a literal, and it is empty',
      lambda: dp.doc_value('`""`'), '')

# ---- the comparison ----------------------------------------------------------
check('equal strings agree', lambda: dp.agrees('Fast', 'Fast'), True)
check('0 and 0.0 are the same number', lambda: dp.agrees('0', '0.0'), True)
check('1.3 is not 3 — the enum-tail rule must not run on a number',
      lambda: dp.agrees('1.3', '3'), False)
check('different enum constants disagree', lambda: dp.agrees('Fast', 'Slow'), False)
check('case is not a difference in a boolean',
      lambda: dp.agrees('False', 'false'), True)
check('a null default and a written value disagree',
      lambda: dp.agrees('none', 'null'), False)
check('null and false are different defaults',
      lambda: dp.agrees('null', 'false'), False)
# InteractionTarget is {User, Owner, Target} in `protocol` and {USER, OWNER,
# TARGET} in `server`, and EnumStyle.detect renders both to the same JSON, so the
# case of an enum constant is not a difference a doc can get wrong.
check('an enum constant compares case-insensitively',
      lambda: dp.agrees('User', 'USER'), True)

# ---- the CHECKER, not only the library --------------------------------------
# "When a component gets a fixture, ask what consumes it." Phases (a) and (b) each
# shipped with a fixture and phase (c) shipped without one, and all three of that
# gate's defects lined up against corpora nobody had built. The probe above is a
# library; these cases run the GATE, against a corpus whose every disagreement is
# planted, so the red path is exercised and not merely believed in.
_run = subprocess.run(
    [sys.executable, str(FROM / 'check-defaults.py'),
     '--docs', str(docs), '--src', str(src)],
    capture_output=True, text=True)
_out = _run.stdout


def _finding(key):
    return [l.strip() for l in _out.split('\n')
            if l.lstrip().startswith('FAIL') and f'`{key}`' in l]


check('the gate exits 1 on a corpus of planted disagreements', lambda: _run.returncode, 1)
check('it reports exactly the three planted disagreements',
      lambda: sorted(l.split('`')[1] for l in _out.split('\n')
                     if l.lstrip().startswith('FAIL')),
      ['Count', 'Mode', 'Radius'])
check('a finding names the field it read, not just the key',
      lambda: bool(_finding('Radius')) and 'defpkg.Widget.radius' in _finding('Radius')[0],
      True)
# The denominator, asserted as an EXACT LINE. An absence assertion here would pass
# for the wrong reason — `"Beta" not in output` went green in a neighbouring
# fixture precisely BECAUSE the fence had stopped being scanned.
check('it prints what it scanned, not only what it found',
      lambda: next((l.strip() for l in _out.split('\n') if 'Default-column' in l), ''),
      'INFO  5 Default-column key table(s) on 1 page(s); 3 in a bound section '
      '(2 direct, 1 inherited-accepted)')
# Rows in UNBOUND tables are counted too, and stated. Reporting only the rows the
# gate can reach makes a green line read as corpus coverage; on the real corpus
# 197 of 358 Default rows sit outside the check, which 161/84 alone never says.
check('it prints the row coverage, INCLUDING the rows outside the check',
      lambda: next((l.strip() for l in _out.split('\n') if 'row(s) in those' in l), ''),
      'INFO  26 row(s) in those tables; 24 in a bound section (21 direct, '
      '3 inherited-accepted), 2 outside the check')
check('it prints the row-level breakdown too',
      lambda: next((l.strip() for l in _out.split('\n') if 'of those' in l), ''),
      'INFO  of those 24: 15 comparable (12 agree, 3 disagree), '
      '2 state no literal, 4 unresolved, 3 state no key')
# A ROW A FILTER DROPS IS STILL A ROW. Two filters here reject a row before it can
# be compared — a ragged row and a key cell that is not an identifier — and an
# uncounted filter is an unaudited skip list: check-symbols.py reduced 2811 hits to
# the 750 it reports through eight of them, one eating 283 on its own.
check('every filtered row is counted, with the reason it was filtered',
      lambda: sorted(l.strip() for l in _out.split('\n') if 'INFO    no key:' in l),
      ['INFO    no key: key cell is not a plain identifier x2',
       'INFO    no key: row has fewer cells than the header x1'])
check('the reason breakdowns sum to their buckets',
      lambda: 'does not sum to its bucket' in _out, False)
def _scanned_vs_bound():
    line = next(l for l in _out.split('\n') if 'Default-column' in l)
    return (int(line.split()[1]), int(line.split('table(s) on')[1].split(';')[1].split()[0]))


# The COMPOSITION of the population, printed rather than described. This exact
# sentence went stale as a docstring figure within one commit of the predicate
# being widened — "59 plain `Default` headers" against a live 61.
check('it prints every Default header spelling that is not plain',
      lambda: sorted(l.strip() for l in _out.split('\n') if 'header spelling' in l),
      ['INFO    header spelling other than a plain "Default": '
       "'Default (as shipped)' x1"])

# The gate must SURFACE a truncated walk, not merely record one in the library. No
# finding depends on it — that is exactly why it needs its own case.
check('the gate reports a truncated ancestry in its INFO block',
      lambda: sorted(l.strip() for l in _out.split('\n') if 'ancestry truncated' in l),
      ['INFO    ancestry truncated: Ghost.CODEC '
       '(no source file for the parent class) x1'])

check('it says how much of the evidence is an implicit zero',
      lambda: next((l.strip() for l in _out.split('\n') if 'comparable:' in l), ''),
      "INFO  of those 15 comparable: 9 match a written initialiser, "
      "6 match the type's implicit zero")

check('an unbound section\'s Default table is COUNTED and not checked',
      lambda: (_scanned_vs_bound(), '999.0' in _out), ((5, 3), False))
# A skip must not share an exit code with a pass: check-type-values.py returned 0
# on a missing cache and the caller rendered a bare `PASS` with no message.
check('a missing source tree SKIPs with exit 2, never 0',
      lambda: subprocess.run(
          [sys.executable, str(FROM / 'check-defaults.py'),
           '--docs', str(docs), '--src', str(src / 'nope')],
          capture_output=True, text=True).returncode, 2)
# NOT an empty directory: an empty corpus trips the BINDER's floor and never
# reaches the gate's, so testing one with the other leaves the gate's own floor
# unverified — which is this gate family's signature failure, not a hypothetical.
check('a corpus that binds but states no defaults SKIPs with exit 2, never PASS',
      lambda: subprocess.run(
          [sys.executable, str(FROM / 'check-defaults.py'),
           '--docs', str(CORPUS / 'docs-nodefaults'), '--src', str(src)],
          capture_output=True, text=True).returncode, 2)
# The exit code and the RENDERING are two different things. verify-docs.sh picks
# findings out with `grep -E '^  (FAIL|SKIP)'`, so a SKIP printed at column 0
# renders as a FAIL with an empty body — which is how a stale-skiplist-only run of
# the sibling gate once printed a header naming the wrong problem over no lines.
# ---- the whole-gate property no per-case assertion covers --------------------
# Every case above says a PARTICULAR comparison lands the right way. None of them
# says the comparisons are doing work at all — 84 rows could agree because the
# documented side is empty there, and the gate would look identical. So: corrupt
# every documented literal and require that EVERY comparable row flips to
# disagree. A row that still agrees with a corrupted value was never being
# compared. Suggested by review after it ran this against the real corpus (84 of
# 84 flipped), which is the measurement the hard-fail decision actually rests on.
def _corruption_flips_every_row():
    spec = importlib.util.spec_from_file_location('_cd', FROM / 'check-defaults.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    real = mod.dp.doc_value

    def corrupt(cell):
        # A SUFFIX, not an offset. `+7` on the numeric ones can land on the real
        # value by accident — it did, on a fixture field initialised to `9.0`
        # against a documented `2.0` — and an accidental agreement reads as the
        # property failing. Suffixing cannot collide: the result parses as no
        # number and equals no constant.
        v = real(cell)
        return None if v is None else v + '_corrupted'

    argv = sys.argv
    out = io.StringIO()
    mod.dp.doc_value = corrupt
    try:
        sys.argv = ['check-defaults.py', '--docs', str(docs), '--src', str(src)]
        with contextlib.redirect_stdout(out):
            mod.main()
    finally:
        mod.dp.doc_value = real
        sys.argv = argv
    m = re.search(r'(\d+) comparable \((\d+) agree, (\d+) disagree\)', out.getvalue())
    if m is None:
        return 'no comparable line'
    comparable, agree, disagree = (int(g) for g in m.groups())
    # The PROPERTY, not the arithmetic. Pinning the count here makes the case
    # redden whenever any unrelated change moves the corpus's comparable total,
    # and a case that reddens for reasons other than its label is how an expected
    # red set stops meaning anything.
    return (agree, disagree == comparable, comparable > 0)


check('corrupting every documented literal flips EVERY comparable row',
      _corruption_flips_every_row, (0, True, True))

check('every SKIP line is indented where the caller\'s filter can see it',
      lambda: [l[:6] for l in subprocess.run(
          [sys.executable, str(FROM / 'check-defaults.py'),
           '--docs', str(CORPUS / 'docs-nodefaults'), '--src', str(src)],
          capture_output=True, text=True).stdout.split('\n')
          if 'SKIP' in l], ['  SKIP'])
check('an empty docs corpus SKIPs on the binder floor, and says so',
      lambda: (lambda p: (p.returncode, 'section binder floor' in p.stdout))(
          subprocess.run(
              [sys.executable, str(FROM / 'check-defaults.py'),
               '--docs', tempfile.mkdtemp(), '--src', str(src)],
              capture_output=True, text=True)), (2, True))

print(f'\nFIXTURE {checks} check(s): {checks - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if checks < MIN_CASES:
    print(f'  FAIL floor: {checks} check(s) ran, at least {MIN_CASES} expected — '
          f'a fixture that runs nothing passes')
    sys.exit(1)
sys.exit(1 if fails else 0)
