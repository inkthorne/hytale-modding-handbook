#!/usr/bin/env python3
"""
Run check-asset-ids.py against a miniature asset tree and miniature docs with known
answers, and (with --mutations) verify that each case detects the defect it is named for.
See maintenance/fixtures/asset-ids/README.md for what the corpus holds.

Same method as check-type-values-fixture.py, whose lessons apply here unchanged and are
not repeated: assert counts and exact verdicts rather than the absence of a name (a pair
that silently stops being SCANNED satisfies every absence assertion), pin the exact set
of cases each mutation reddens, run the checker as a subprocess and read its own exit
status, and keep an IDENTITY mutation as the harness control.

What is specific to this gate:

* The cases assert on PAIR lines (`-v`), one per extracted string value with the verdict
  the gate gave it. A flag list alone cannot say a real id PASSED: a pair the extractor
  dropped is missing from it exactly as a passing pair is.
* Every exemption is a pair of cases, the one it excuses and the one it must not: the
  placeholder prefix on a page that names it and on a page that only mentions it; a pack's
  ids on a page that names the pack and on pages that name another or none; a page-defined
  id for the family its path is in and for another. A mutation widens each one.
* `expect` is a measurement and `names` the specification (see the type-values fixture's
  note on why the difference decides what to do when a red set moves).

Usage:
  python3 maintenance/scripts/check-asset-ids-fixture.py [-v]
  python3 maintenance/scripts/check-asset-ids-fixture.py --mutations [-v]
"""
from __future__ import annotations
import argparse, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parents[0] / 'fixtures' / 'asset-ids'
CORPUS, SNAPSHOT = FIX / 'corpus', FIX / 'typing-snapshot.txt'
CHECKER = HERE / 'check-asset-ids.py'

# The healthy corpus, stated exactly. Each line is asserted verbatim: a value leaving the
# corpus, a fence no longer scanned, a class no longer typed all move one of them.
SWEEP = ('asset sweep: 66 JSON-bodied file(s) swept under Server/ (+2 excluded as bulk data: '
         'Prefabs, World); 1 failed to parse; 8 store(s) declared in the jar, 7 present with ids '
         '(1 absent from this build), 56 distinct id(s)')
TYPING = ('typing (N>=5 distinct values, P>=0.90 in one store): L2 7 of 70 classes, L1 13 of 43, '
          'LW 8 of 20; 7 of 7 store(s) are the target of at least one typed class; 2 tied class(es)')
DRIFT = 'typing drift vs typing-snapshot.txt: 1 class(es) added, 1 removed, 1 retargeted (28 in the snapshot)'
SCAN = ('docs scan: 9 page(s); 37 ```json fence(s) (34 strict-parse, 3 unparseable and read tolerantly); '
        '2 untagged fence(s), of which 1 parse as JSON and 1 hold JSON pairs (scanned); 1 more hold only a '
        'quoted-key fragment inside a tree or sample (not scanned); 3 other-language fence(s) not scanned; '
        '2 fence(s) sit inside a blockquote, 1 of them ```json (all counted and scanned)')
PAIRS = ('pairs: 99 string value(s) extracted, 90 at a typed position (9 untyped, not checkable); of the typed: '
         '18 resolved, 15 exempt (shape 6, shipped-use 1, shipped-excerpt 1, placeholder 3, pack 2, '
         'page-defined 2), 57 failed; resolved in 7 distinct store(s)')
RECOVERED = 'recovered from the unparseable fences: 4 pair(s), 3 at a typed position, 3 failed'
N_FLAG_LINES = 59       # 57 failed pairs and the 2 declarations in declared.md

# Floors, same shape as every other fixture in this directory: raise freely, lower only
# with a reason in the commit message.
MIN_CASES = 38
MIN_MUTATIONS = 36

PAIR_RE = re.compile(r'^  PAIR  (\S+?):\d+\t([^\t]*)\t([^\t]*)\t(\S+)$')
FLAG_RE = re.compile(r'^  FLAG  (\S+?):\d+: "([^"]*)": "([^"]*)" is not an id in (\S+) \((.*)\)$')


def run(checker, docs, src, assets, packs=None, snapshot=SNAPSHOT, verbose=True):
    # PYTHONPATH is not needed (the checker imports nothing local) but mutants live in a temp
    # dir, so the IDENTITY mutation below is what proves the harness itself still works.
    cmd = [sys.executable, str(checker), '--docs', str(docs), '--src', str(src),
           '--assets', str(assets), '--snapshot', str(snapshot)]
    if packs is not None:
        cmd += ['--packs', str(packs)]
    if verbose:
        cmd += ['-v']
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def pairs_of(text):
    out = {}
    for ln in text.split('\n'):
        m = PAIR_RE.match(ln)
        if m:
            out.setdefault((m.group(1), m.group(2), m.group(3)), []).append(m.group(4))
    return out


def flags_of(text):
    return {(m.group(1), m.group(2), m.group(3)): (m.group(4), m.group(5))
            for ln in text.split('\n') if (m := FLAG_RE.match(ln))}


def all_cases(checker) -> tuple[dict[str, list[str]], list[str]]:
    """Run every case. Returns ({label: [problems]}, [cases that produced a traceback])."""
    out: dict[str, list[str]] = {}
    crashed: list[str] = []

    def case(label, rc, text, *, want_rc, must=(), must_not=(), verdicts=None, flagged=None):
        problems = []
        if rc != want_rc:
            problems.append(f'exit {rc}, wanted {want_rc}')
        problems += [f'missing {m!r}' for m in must if m not in text]
        problems += [f'unexpected {m!r}' for m in must_not if m in text]
        if verdicts:
            got = pairs_of(text)
            for key, want in verdicts.items():
                have = got.get(key)
                if have is None:
                    problems.append(f'no PAIR for {key} (the pair was not extracted)')
                elif want not in have:
                    problems.append(f'{key}: verdict {have}, wanted {want}')
        if flagged:
            got = flags_of(text)
            for key, kind in flagged.items():
                if key not in got:
                    problems.append(f'{key} not flagged')
                elif kind not in got[key][1]:
                    problems.append(f'{key} flagged as {got[key][1]!r}, wanted {kind!r}')
        if 'Traceback (most recent call last)' in text:
            crashed.append(label)
        out[label] = problems

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        docs, src, assets, packs = tmp / 'docs', tmp / 'src', tmp / 'assets', tmp / 'packs'
        for name, dst in (('docs', docs), ('src', src), ('assets', assets), ('packs', packs)):
            shutil.copytree(CORPUS / name, dst)

        rc, t = run(checker, docs, src, assets, packs)
        # The load-bearing case. Every INFO line verbatim: the denominators catch anything that
        # stops being SCANNED or TYPED, which no absence assertion can.
        case('healthy corpus: every denominator is exact', rc, t, want_rc=1,
             must=(SWEEP, TYPING, DRIFT, SCAN, PAIRS, RECOVERED), must_not=('PASS', 'FAIL'))
        case('the flag set is exactly the invented, wrong-kind and unexcused ids', rc, t, want_rc=1,
             must=('57 failed',))
        n_flags = sum(1 for ln in t.split('\n') if ln.startswith('  FLAG  '))
        if n_flags != N_FLAG_LINES:
            out['the flag set is exactly the invented, wrong-kind and unexcused ids'].append(
                f'{n_flags} FLAG line(s), wanted {N_FLAG_LINES}')

        F = 'families.md'
        case('an invented id in each covered family fails', rc, t, want_rc=1, verdicts={
            (F, 'ItemId', 'Sword_Fake'): 'failed', (F, 'Next', 'Int_Fake'): 'failed',
            (F, 'LocalSoundEventId', 'SFX_Fake'): 'failed', (F, 'EffectId', 'Fx_Fake'): 'failed',
            (F, 'SystemId', 'P_Fake'): 'failed', (F, 'DropListId', 'D_Fake'): 'failed'})
        case('a real id in each covered family passes', rc, t, want_rc=1, verdicts={
            (F, 'ItemId', 'Sword_A'): 'resolved', (F, 'Next', 'Int_A'): 'resolved',
            (F, 'LocalSoundEventId', 'SFX_A'): 'resolved', (F, 'EffectId', 'Fx_A'): 'resolved',
            (F, 'SystemId', 'P_A'): 'resolved', (F, 'DropListId', 'D_A'): 'resolved'})
        # The point of typing. Each id below EXISTS (in some other store); resolving against
        # all of Server/ would pass every one of them for the wrong reason.
        case('a real id of the WRONG family under a typed key fails, naming where it lives', rc, t,
             want_rc=1, flagged={
                 (F, 'ItemId', 'SFX_A'): 'exists only as Audio/SoundEvents',
                 (F, 'Next', 'Sword_A'): 'exists only as Item/Items',
                 (F, 'LocalSoundEventId', 'Fx_A'): 'exists only as Entity/Effects',
                 (F, 'EffectId', 'P_A'): 'exists only as Particles',
                 (F, 'SystemId', 'D_A'): 'exists only as Drops, Item/Block/Spawners',
                 (F, 'DropListId', 'Int_A'): 'exists only as Item/Interactions'})
        case('a tie passes in either store; the stem, not the path or extension, is the id', rc, t,
             want_rc=1, verdicts={
                 (F, 'DropListId', 'S_ONLY'): 'resolved',      # only in the second of two tied stores
                 (F, 'SystemId', 'Spawn_A'): 'resolved',       # a .particlespawner file
                 (F, 'ItemId', 'Axe_C'): 'resolved'})          # Item/Items/Weapons/Axe_C.json
        case('an id inside an array is checked', rc, t, want_rc=1, verdicts={
            (F, 'Interactions', 'Int_B'): 'resolved', (F, 'Interactions', 'Int_Fake_Arr'): 'failed'})
        case('a map value is typed by its parent, whatever its key', rc, t, want_rc=1, verdicts={
            (F, 'SoundMap.Fly', 'SFX_F'): 'resolved', (F, 'SoundMap.Dive', 'SFX_Fake_Map'): 'failed',
            (F, 'Tones.Zeta', 'SFX_Fake_Zeta'): 'failed'})
        case('a known FIELD among map values is not mistaken for an id slot', rc, t, want_rc=1,
             verdicts={(F, 'Tones.Style', 'quiet'): 'untyped', (F, 'Tones.Inner', 'text'): 'untyped'})
        case('a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped',
             rc, t, want_rc=1, verdicts={
                 (F, 'Rewards.Id', 'Sword_B'): 'resolved', (F, 'Rewards.Id', 'Id_Fake_Reward'): 'failed',
                 (F, 'Rewards.Id', 'SFX_B'): 'failed',
                 (F, 'Cues.Id', 'SFX_C'): 'resolved', (F, 'Cues.Id', 'Id_Fake_Cue'): 'failed',
                 (F, 'Cues.Id', 'Sword_B'): 'failed', (F, 'Other.Id', 'Anything_Goes'): 'untyped'})
        case('a bare key seen under one parent types that parent and no unseen one', rc, t, want_rc=1,
             verdicts={(F, 'Holder.Lonely', 'Sword_Fake_L'): 'failed',
                       (F, 'Elsewhere.Lonely', 'Anything_L'): 'untyped'})
        case('a mixture key does not speak where the exact position shows the other field, and still speaks '
             'for an unseen parent', rc, t, want_rc=1, verdicts={
                 (F, 'Dust.Build', 'P_B'): 'untyped', (F, 'Tags.Pick', 'Uninterruptable'): 'untyped',
                 (F, 'Smoke.Build', 'Nothing_Real'): 'failed', (F, 'SoundEvents.Build', 'SFX_B'): 'resolved'})
        case('a parent.* class does not speak for a pair the assets show holding another kind, and still does '
             'for an unseen key', rc, t, want_rc=1, verdicts={
                 (F, 'Bag.Loot', 'D_B'): 'resolved', (F, 'Bag.Loot', 'Sword_A'): 'failed',
                 (F, 'Bag.Extra', 'Sword_Fake_Bag'): 'failed'})
        case('two parents are not enough to speak for a third (PARENT_K = 3)', rc, t, want_rc=1, verdicts={
            (F, 'HolderA.Twin', 'Sword_Fake_T'): 'failed', (F, 'Elsewhere.Twin', 'Anything_T'): 'untyped'})
        case('a value the shipped assets put under the key passes if it names no asset; an untyped bare key '
             'lends nothing', rc, t, want_rc=1, verdicts={
                 (F, 'Solid', 'Empty'): 'shipped-use', (F, 'Solid', 'Nothing'): 'failed',
                 (F, 'Rewards.Id', 'SFX_B'): 'failed'})
        case('an id of ANOTHER store that ships under the key somewhere is still the wrong kind', rc, t,
             want_rc=1, flagged={(F, 'Next', 'Fx_A'): 'exists only as Entity/Effects'})
        X = 'excerpt.md'
        case('an excerpt of a real shipped file passes only for the pair that file ships', rc, t, want_rc=1,
             flagged={(X, 'Next', 'Fx_A'): 'exists only as Entity/Effects'})
        got_x = pairs_of(t)
        for key, want in (((X, 'Next', 'Fx_A'), ['shipped-excerpt', 'failed', 'failed']),
                          ((X, 'Next', 'Fx_D'), ['failed', 'failed']),    # ships under EffectId; and an unrelated sentence
                          ((X, 'Next', 'B0'), ['failed'])):               # occurs in the file only as a map KEY
            if got_x.get(key) != want:
                out['an excerpt of a real shipped file passes only for the pair that file ships'].append(
                    f'verdicts for {key} are {got_x.get(key)}, wanted {want}')
        case('a pair mixed below P but mostly of the class\'s kind is still checked as that kind', rc, t,
             want_rc=1, verdicts={(F, 'Mixed.Loot', 'Sword_A'): 'failed'})
        case('a generated-state id resolves by its base', rc, t, want_rc=1, verdicts={
            (F, 'Solid', '*Sword_A_State_Broken'): 'resolved', (F, 'Solid', '*Ghost_State_X'): 'failed'})
        case('a value not shaped like an id is exempt as shape and counted', rc, t, want_rc=1, verdicts={
            ('shapes.md', 'ItemId', v): 'shape'
            for v in ('<Item Id>', '...', 'Sword A or B', '', '3', 'Weapons/Sword')})

        E, B = 'exempt.md', 'bare.md'
        case('placeholder: a prefix or quoted id the page names is exempt there, nothing near it is', rc, t,
             want_rc=1, verdicts={
                 (E, 'Next', 'MyMod_Step'): 'placeholder', (E, 'Next', 'Chain_Named'): 'placeholder',
                 (E, 'ItemId', 'MyMod_Item'): 'placeholder',
                 (E, 'Next', 'MyMod'): 'failed', (E, 'Next', 'Other_Step'): 'failed'})
        case('placeholder: the same ids on a page that only mentions them in prose fail', rc, t, want_rc=1,
             verdicts={(B, 'Next', 'MyMod_Step'): 'failed', (B, 'Next', 'Chain_Named'): 'failed',
                       (B, 'ItemId', 'MyMod_Item'): 'failed'})
        case('placeholder: a table row or a list item that says "placeholder" is not a note', rc, t, want_rc=1,
             verdicts={(B, 'Next', 'Zed_One'): 'failed', (B, 'Next', 'List_Named'): 'failed',
                       (B, 'Next', 'Tab_One'): 'failed', (B, 'Next', 'Table_Named'): 'failed'})
        case('placeholder: a note that declares a real prefix or a real id is reported and excuses nothing', rc,
             t, want_rc=1, must=('declared.md:3: the placeholder note declares prefix `Sword_`',
                                 'declared.md:3: the placeholder note declares id `"Axe_C"`'),
             verdicts={('declared.md', 'ItemId', 'Sword_Mine'): 'failed'})
        case('pack: a pack\'s id is exempt on a page that names that pack and only there', rc, t, want_rc=1,
             verdicts={(E, 'ItemId', 'Food_Snack'): 'pack', (E, 'ItemId', 'Drop_Chick'): 'failed',
                       ('pack2.md', 'ItemId', 'Drop_Chick'): 'pack', ('pack2.md', 'ItemId', 'Food_Snack'): 'failed',
                       (B, 'ItemId', 'Food_Snack'): 'failed'})
        case('page-defined: a path on the line before a fence or in its first comment defines the stem, '
             'for that path\'s family only', rc, t, want_rc=1, verdicts={
                 (E, 'ItemId', 'Sword_Page'): 'page-defined', (E, 'Next', 'Sword_Page'): 'failed',
                 (E, 'Next', 'Int_Page'): 'page-defined',
                 (B, 'ItemId', 'Sword_Page'): 'failed', (B, 'Next', 'Int_Page'): 'failed'})
        case('page-defined: a path in prose, or before a java fence, defines nothing', rc, t, want_rc=1,
             verdicts={('pathprose.md', 'ItemId', 'Sword_Prose'): 'failed',
                       ('pathprose.md', 'ItemId', 'Sword_Java'): 'failed'})
        case('a blockquoted fence is counted and scanned; a quoted java fence is counted and not read', rc, t,
             want_rc=1, must=('2 fence(s) sit inside a blockquote, 1 of them ```json',),
             verdicts={('fences.md', 'Next', 'Int_Bad7'): 'failed'})
        case('pairs recovered from unparseable fences are reported on their own line', rc, t, want_rc=1,
             must=(RECOVERED,))
        got = pairs_of(t)
        case('fences: comments, an ellipsis, a fragment, an untagged JSON fence and an indented fence are read; '
             'a tree and a java fence are not', rc, t, want_rc=1, verdicts={
                 ('fences.md', 'Next', 'Int_Bad1'): 'failed', ('fences.md', 'Interactions', 'Int_Bad1b'): 'failed',
                 ('fences.md', 'Next', 'Int_Bad2'): 'failed', ('fences.md', 'Next', 'Int_Bad3'): 'failed',
                 ('fences.md', 'Next', 'Int_Bad6'): 'failed'})
        out['fences: comments, an ellipsis, a fragment, an untagged JSON fence and an indented fence are read; '
            'a tree and a java fence are not'] += [
            f'{k} was extracted from a fence that is not JSON' for k in
            (('fences.md', 'Next', 'Int_Bad4'), ('fences.md', 'Next', 'Int_Bad5')) if k in got]
        case('the tolerant extractor agrees with json.loads on every strict fence', rc, t, want_rc=1,
             must_not=('the tolerant extractor lost',))

        # ---- inputs that must fail loudly, not pass quietly
        rc, t = run(checker, docs, src, tmp / 'no-assets', packs, verbose=False)
        case('missing asset cache exits 2', rc, t, want_rc=2, must=('SKIP',), must_not=('PASS', 'INFO'))
        rc, t = run(checker, docs, tmp / 'no-src', assets, packs, verbose=False)
        case('missing source cache exits 2', rc, t, want_rc=2, must=('SKIP',), must_not=('PASS', 'INFO'))
        rc, t = run(checker, tmp / 'no-docs', src, assets, packs, verbose=False)
        case('missing docs corpus exits 2', rc, t, want_rc=2, must=('SKIP',), must_not=('PASS', 'INFO'))

        (tmp / 'empty-assets' / 'Server').mkdir(parents=True)
        rc, t = run(checker, docs, src, tmp / 'empty-assets', packs, verbose=False)
        # must_not INFO is the load-bearing half: the early return is the guard, and its
        # signature is that nothing is reported after it.
        case('an EMPTY asset tree fails (exit 3) rather than typing nothing and passing', rc, t, want_rc=3,
             must=('asset-side denominator is zero', '0 file(s) swept'), must_not=('PASS', 'INFO'))
        (tmp / 'empty-docs').mkdir()
        rc, t = run(checker, tmp / 'empty-docs', src, assets, packs, verbose=False)
        case('an EMPTY docs corpus fails (exit 3)', rc, t, want_rc=3,
             must=('scanned nothing', '0 page(s)'), must_not=('PASS', 'INFO  docs scan'))
        (tmp / 'untyped-docs').mkdir()
        (tmp / 'untyped-docs' / 'u.md').write_text('# U\n\n```json\n{ "Colour": "Red", "Note": "text" }\n```\n')
        rc, t = run(checker, tmp / 'untyped-docs', src, assets, packs, verbose=False)
        case('docs with JSON but no typed pair fail (exit 3): nothing was checked', rc, t, want_rc=3,
             must=('scanned nothing', '0 typed pair(s)'), must_not=('PASS', 'INFO  docs scan'))
        rc, t = run(checker, docs, src, assets, packs, snapshot=tmp / 'no-snapshot.txt', verbose=False)
        case('a missing typing snapshot is reported, not fatal', rc, t, want_rc=1,
             must=('no typing snapshot at',))
    return out, crashed


# label -> (edits, expected red set, the cases this defect BELONGS to). `edits` is a list of
# (old, new); every `old` must occur exactly once in the checker. `expect` is a MEASUREMENT and
# `names` is the SPECIFICATION: re-measure `expect` freely, never `names`.
def E(old, new):
    return [(old, new)]


MUTATIONS = {
    'IDENTITY (no change - the harness control)': (
        E('#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity mutation)'), set(), set()),

    # --- typing
    'typing disabled: resolve against every store, not the key\'s family': (
        E("            if set(hit) & fams:\n                rec['verdict'] = 'resolved'",
          "            if hit:\n                rec['verdict'] = 'resolved'"),
        None, {'a real id of the WRONG family under a typed key fails, naming where it lives'}),
    'path typing collapsed to bare keys': (
        E("    if p is not None and (p, k) in typed['L2']:", "    if False:"),
        None, {'a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped'}),
    'map-value typing by the parent dropped': (
        E("    if p is not None and (p, '*') in typed['LW']:", "    if False:"),
        None, {'a map value is typed by its parent, whatever its key'}),
    'the field guard on map-value typing removed': (
        E("        elif k not in sweep.children.get(p, ()) or (p, k) in typed['L2'] or (k,) in typed['L1']:",
          "        elif True:"),
        None, {'a known FIELD among map values is not mistaken for an id slot'}),
    'a bare key speaks for parents it was never seen under (PARENT_K = 1)': (
        E("PARENT_K = 3\n", "PARENT_K = 1\n"),
        None, {'a bare key seen under one parent types that parent and no unseen one'}),
    'N floor lowered to 1': (
        E("N_MIN = 5          # distinct", "N_MIN = 1          # distinct"),
        None, {'healthy corpus: every denominator is exact'}),
    'P floor lowered to 0.5': (
        E("P_MIN = 0.90       # fraction", "P_MIN = 0.50       # fraction"),
        None, {'healthy corpus: every denominator is exact'}),

    # --- extraction
    'array elements not extracted': (
        E("                elif top[0] == 'a':\n                    out.append((top[1], unq(text), off))",
          "                elif top[0] == 'a':\n                    pass"),
        None, {'an id inside an array is checked'}),
    'array elements not extracted AND the json.loads cross-check removed': (
        E("                elif top[0] == 'a':\n                    out.append((top[1], unq(text), off))",
          "                elif top[0] == 'a':\n                    pass") +
        E("                if sp - tc:     # strict saw a pair the tolerant extractor lost", "                if False:"),
        None, {'an id inside an array is checked'}),
    'bulk data (Prefabs, World) swept like a store': (
        E("SWEEP_EXCLUDED_TOPS = ('Prefabs', 'World')", "SWEEP_EXCLUDED_TOPS = ()"),
        None, {'healthy corpus: every denominator is exact'}),

    # --- widening and normalisation
    'verbatim widening off (WIDEN = False)': (
        E("\nWIDEN = True\n", "\nWIDEN = False\n"),
        None, {'a value the shipped assets put under the key passes if it names no asset; an untyped bare key '
               'lends nothing'}),
    'verbatim of another store\'s id accepted (VERBATIM_STRICT = False)': (
        E("VERBATIM_STRICT = True\n", "VERBATIM_STRICT = False\n"),
        None, {'an id of ANOTHER store that ships under the key somewhere is still the wrong kind'}),
    'verbatim taken from an untyped class AND the strict filter off (the via guard\'s own effect)': (
        E("        if lvl in via:\n", "        if True:\n") + E("VERBATIM_STRICT = True\n", "VERBATIM_STRICT = False\n"),
        None, {'a value the shipped assets put under the key passes if it names no asset; an untyped bare key '
               'lends nothing'}),
    'the exact position no longer wins over a bare key (EXACT_WINS = False)': (
        E("EXACT_WINS = True\n", "EXACT_WINS = False\n"),
        None, {'a mixture key does not speak where the exact position shows the other field, and still speaks '
               'for an unseen parent'}),
    'the exact pair no longer wins over parent.*': (
        E("        if EXACT_WINS and sh is not None and sh < EXACT_SHARE:\n            pass        # this", "        if False:\n            pass        # this"),
        None, {'a parent.* class does not speak for a pair the assets show holding another kind, and still does '
               'for an unseen key'}),
    'the placeholder note is the whole page, not a paragraph': (
        E("    for n, p in prose_paragraphs(text):", "    for n, p in [(1, text)]:"),
        None, {'placeholder: the same ids on a page that only mentions them in prose fail'}),
    'two parents suffice to speak for a third (PARENT_K = 2)': (
        E("PARENT_K = 3\n", "PARENT_K = 2\n"),
        None, {'two parents are not enough to speak for a third (PARENT_K = 3)'}),
    'an excerpt exempts any id, whether or not the named file holds it': (
        E("elif excerpt_holds(path, val, excerpts.get(fi, ())):", "elif bool(excerpts.get(fi)):"),
        None, {'an excerpt of a real shipped file passes only for the pair that file ships'}),
    'an excerpt ignores the key position (any key of the file will do)': (
        E("if v == val and (fp[-len(path):] == path or path[-len(fp):] == fp):", "if v == val:"),
        None, {'an excerpt of a real shipped file passes only for the pair that file ships'}),
    'an excerpt matches any quoted string in the file, map keys included (the b4365d8 test)': (
        E("                                parsed[rp] = list(strict_pairs(json.loads(\n                                    (assets / 'Server' / rp).read_text(encoding='utf-8-sig'))))",
          "                                parsed[rp] = [((), q) for q in re.findall(r'\"((?:[^\"\\\\]|\\\\.)*)\"', (assets / 'Server' / rp).read_text(encoding='utf-8-sig'))]") +
        E("if v == val and (fp[-len(path):] == path or path[-len(fp):] == fp):", "if v == val:"),
        None, {'an excerpt of a real shipped file passes only for the pair that file ships'}),
    'a mixed-below-P pair counts as contradicted: no store reaches P (the b4365d8 test)': (
        E("        if EXACT_WINS and sh is not None and sh < EXACT_SHARE:\n            pass        # the shipped assets show this (parent, key) holding something else",
          "        if EXACT_WINS and sh is not None and sh < 0.9:\n            pass        # the shipped assets show this (parent, key) holding something else"),
        None, {'a pair mixed below P but mostly of the class\'s kind is still checked as that kind'}),
    'a table row or list item counts as a placeholder note': (
        E("        elif LIST_OR_TABLE.match(ln):", "        elif False:"),
        None, {'placeholder: a table row or a list item that says "placeholder" is not a note'}),
    'a declared prefix that shipped ids start with still excuses': (
        E("hit = next((i for i in ctx.idx if i.startswith(x)), None)", "hit = None"),
        None, {'placeholder: a note that declares a real prefix or a real id is reported and excuses nothing'}),
    'a declared id that names a shipped asset still excuses': (
        E("            if resolves(x, ctx.idx):\n                out.append(dict(page=r['name'], line=n, path=('<placeholder note>',), val=x",
          "            if False:\n                out.append(dict(page=r['name'], line=n, path=('<placeholder note>',), val=x"),
        None, {'placeholder: a note that declares a real prefix or a real id is reported and excuses nothing'}),
    'blockquoted fences not recognised': (
        E(r"QFENCE = re.compile(r'^([ \t]*(?:>[ \t]?)*)```(\w*)[^\n]*\n(.*?)^[ \t]*(?:>[ \t]?)*```', re.M | re.S)",
          "QFENCE = FENCE"),
        None, {'a blockquoted fence is counted and scanned; a quoted java fence is counted and not read'}),
    'a page-defined path counts before any fence, java included': (
        E("    for lang, prev, comment in fence_claims(text):\n        if lang not in ('json', ''):\n            continue\n        for c in (prev[:1]",
          "    for lang, prev, comment in fence_claims(text):\n        for c in (prev[:1]"),
        None, {'page-defined: a path in prose, or before a java fence, defines nothing'}),
    'a page-defined path counts from anywhere on the page': (
        E("        for c in (prev[:1] + ([comment] if comment else [])):", "        for c in text.split('\\n'):"),
        None, {'page-defined: a path in prose, or before a java fence, defines nothing'}),
    'generated-state base rule dropped': (
        E("    if not hit and gen and '_State_' in core:", "    if False:"),
        None, {'a generated-state id resolves by its base'}),
    'numeric strings no longer exempt by shape': (
        E("if not core or not ID_SHAPE.match(core) or NUMERIC.match(core):", "if not core or not ID_SHAPE.match(core):"),
        None, {'a value not shaped like an id is exempt as shape and counted'}),

    # --- exemptions, each widened
    'placeholder prefix exempt without a page note': (
        E("any(core.startswith(p) for p in pre_prefixes)", "core.startswith('MyMod_')"),
        None, {'placeholder: the same ids on a page that only mentions them in prose fail'}),
    'placeholder note recognised without the word "placeholder"': (
        E("        if not re.search(r'\\bplaceholders?\\b', p, re.I):\n            continue\n", ""),
        None, {'placeholder: the same ids on a page that only mentions them in prose fail'}),
    'a pack\'s ids exempt on every page': (
        E("            if pk in text:", "            if True:"),
        None, {'pack: a pack\'s id is exempt on a page that names that pack and only there'}),
    'page-defined id exempt for any family, not its path\'s': (
        E("core in pdef and (pdef[core] & fams)", "core in pdef"),
        None, {'page-defined: a path on the line before a fence or in its first comment defines the stem, '
               'for that path\'s family only'}),

    # --- guards against a run that examined nothing
    'asset-side zero floor removed': (
        E("              f\"{sum(len(v) for v in typed.values())} typed class(es)\")\n        return 3\n",
          "              f\"{sum(len(v) for v in typed.values())} typed class(es)\")\n"),
        None, {'an EMPTY asset tree fails (exit 3) rather than typing nothing and passing'}),
    'docs zero floor removed': (
        E("              f\"{n_pairs} pair(s), {typed_pairs} typed pair(s)\")\n        return 3\n",
          "              f\"{n_pairs} pair(s), {typed_pairs} typed pair(s)\")\n"),
        None, {'an EMPTY docs corpus fails (exit 3)',
               'docs with JSON but no typed pair fail (exit 3): nothing was checked'}),
    'missing-input SKIP returns 0 instead of 2': (
        E("            print(f\"  SKIP  {label} not found at {p} — {how}\")\n            return 2",
          "            print(f\"  SKIP  {label} not found at {p} — {how}\")\n            return 0") +
        E("        print(f\"  SKIP  docs corpus not found at {docs} — check the --docs path\")\n        return 2",
          "        print(f\"  SKIP  docs corpus not found at {docs} — check the --docs path\")\n        return 0"),
        None, {'missing asset cache exits 2', 'missing source cache exits 2', 'missing docs corpus exits 2'}),
}

# label -> the exact set of cases that goes red. MEASURED (see `--measure`); the `names` in MUTATIONS are the specification.
EXPECT = {
    'IDENTITY (no change - the harness control)': set(),
    "typing disabled: resolve against every store, not the key's family": {
        'a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped',
        "a pair mixed below P but mostly of the class's kind is still checked as that kind",
        'a parent.* class does not speak for a pair the assets show holding another kind, and still does for an unseen key',
        'a real id of the WRONG family under a typed key fails, naming where it lives',
        'a value the shipped assets put under the key passes if it names no asset; an untyped bare key lends nothing',
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'an id of ANOTHER store that ships under the key somewhere is still the wrong kind',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'path typing collapsed to bare keys': {
        'a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped',
        'a value the shipped assets put under the key passes if it names no asset; an untyped bare key lends nothing',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'map-value typing by the parent dropped': {
        'a map value is typed by its parent, whatever its key',
        'a parent.* class does not speak for a pair the assets show holding another kind, and still does for an unseen key',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'the field guard on map-value typing removed': {
        'a known FIELD among map values is not mistaken for an id slot',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a bare key speaks for parents it was never seen under (PARENT_K = 1)': {
        'a bare key seen under one parent types that parent and no unseen one',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
        'two parents are not enough to speak for a third (PARENT_K = 3)',
    },
    'N floor lowered to 1': {
        'a mixture key does not speak where the exact position shows the other field, and still speaks for an unseen parent',
        'healthy corpus: every denominator is exact',
    },
    'P floor lowered to 0.5': {
        'a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped',
        'a value the shipped assets put under the key passes if it names no asset; an untyped bare key lends nothing',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'array elements not extracted': {
        'a bare key seen under one parent types that parent and no unseen one',
        'a blockquoted fence is counted and scanned; a quoted java fence is counted and not read',
        'a generated-state id resolves by its base',
        'a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped',
        'a known FIELD among map values is not mistaken for an id slot',
        'a map value is typed by its parent, whatever its key',
        'a missing typing snapshot is reported, not fatal',
        'a mixture key does not speak where the exact position shows the other field, and still speaks for an unseen parent',
        "a pair mixed below P but mostly of the class's kind is still checked as that kind",
        'a parent.* class does not speak for a pair the assets show holding another kind, and still does for an unseen key',
        'a real id in each covered family passes',
        'a real id of the WRONG family under a typed key fails, naming where it lives',
        'a tie passes in either store; the stem, not the path or extension, is the id',
        'a value not shaped like an id is exempt as shape and counted',
        'a value the shipped assets put under the key passes if it names no asset; an untyped bare key lends nothing',
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'an id inside an array is checked',
        'an id of ANOTHER store that ships under the key somewhere is still the wrong kind',
        'an invented id in each covered family fails',
        'fences: comments, an ellipsis, a fragment, an untagged JSON fence and an indented fence are read; a tree and a java fence are not',
        'healthy corpus: every denominator is exact',
        "pack: a pack's id is exempt on a page that names that pack and only there",
        'page-defined: a path in prose, or before a java fence, defines nothing',
        "page-defined: a path on the line before a fence or in its first comment defines the stem, for that path's family only",
        'pairs recovered from unparseable fences are reported on their own line',
        'placeholder: a note that declares a real prefix or a real id is reported and excuses nothing',
        'placeholder: a prefix or quoted id the page names is exempt there, nothing near it is',
        'placeholder: a table row or a list item that says "placeholder" is not a note',
        'placeholder: the same ids on a page that only mentions them in prose fail',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
        'the tolerant extractor agrees with json.loads on every strict fence',
        'two parents are not enough to speak for a third (PARENT_K = 3)',
    },
    'array elements not extracted AND the json.loads cross-check removed': {
        'an id inside an array is checked',
        'fences: comments, an ellipsis, a fragment, an untagged JSON fence and an indented fence are read; a tree and a java fence are not',
        'healthy corpus: every denominator is exact',
        'pairs recovered from unparseable fences are reported on their own line',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'bulk data (Prefabs, World) swept like a store': {
        'healthy corpus: every denominator is exact',
    },
    'verbatim widening off (WIDEN = False)': {
        'a value the shipped assets put under the key passes if it names no asset; an untyped bare key lends nothing',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    "verbatim of another store's id accepted (VERBATIM_STRICT = False)": {
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'an id of ANOTHER store that ships under the key somewhere is still the wrong kind',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    "verbatim taken from an untyped class AND the strict filter off (the via guard's own effect)": {
        'a key typed by (parent, key) fails wrong-kind and invented ids; an unseen parent is untyped',
        'a parent.* class does not speak for a pair the assets show holding another kind, and still does for an unseen key',
        'a value the shipped assets put under the key passes if it names no asset; an untyped bare key lends nothing',
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'an id of ANOTHER store that ships under the key somewhere is still the wrong kind',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'the exact position no longer wins over a bare key (EXACT_WINS = False)': {
        'a mixture key does not speak where the exact position shows the other field, and still speaks for an unseen parent',
        'a parent.* class does not speak for a pair the assets show holding another kind, and still does for an unseen key',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'the exact pair no longer wins over parent.*': {
        'a parent.* class does not speak for a pair the assets show holding another kind, and still does for an unseen key',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'the placeholder note is the whole page, not a paragraph': {
        'healthy corpus: every denominator is exact',
        'placeholder: a note that declares a real prefix or a real id is reported and excuses nothing',
        'placeholder: a table row or a list item that says "placeholder" is not a note',
        'placeholder: the same ids on a page that only mentions them in prose fail',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'two parents suffice to speak for a third (PARENT_K = 2)': {
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
        'two parents are not enough to speak for a third (PARENT_K = 3)',
    },
    'an excerpt exempts any id, whether or not the named file holds it': {
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'an excerpt ignores the key position (any key of the file will do)': {
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'an excerpt matches any quoted string in the file, map keys included (the b4365d8 test)': {
        'an excerpt of a real shipped file passes only for the pair that file ships',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a mixed-below-P pair counts as contradicted: no store reaches P (the b4365d8 test)': {
        "a pair mixed below P but mostly of the class's kind is still checked as that kind",
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a table row or list item counts as a placeholder note': {
        'healthy corpus: every denominator is exact',
        'placeholder: a table row or a list item that says "placeholder" is not a note',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a declared prefix that shipped ids start with still excuses': {
        'healthy corpus: every denominator is exact',
        'placeholder: a note that declares a real prefix or a real id is reported and excuses nothing',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a declared id that names a shipped asset still excuses': {
        'placeholder: a note that declares a real prefix or a real id is reported and excuses nothing',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'blockquoted fences not recognised': {
        'a blockquoted fence is counted and scanned; a quoted java fence is counted and not read',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a page-defined path counts before any fence, java included': {
        'healthy corpus: every denominator is exact',
        'page-defined: a path in prose, or before a java fence, defines nothing',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'a page-defined path counts from anywhere on the page': {
        'healthy corpus: every denominator is exact',
        'page-defined: a path in prose, or before a java fence, defines nothing',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'generated-state base rule dropped': {
        'a generated-state id resolves by its base',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'numeric strings no longer exempt by shape': {
        'a value not shaped like an id is exempt as shape and counted',
        'healthy corpus: every denominator is exact',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'placeholder prefix exempt without a page note': {
        'healthy corpus: every denominator is exact',
        'placeholder: the same ids on a page that only mentions them in prose fail',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'placeholder note recognised without the word "placeholder"': {
        'healthy corpus: every denominator is exact',
        'placeholder: the same ids on a page that only mentions them in prose fail',
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    "a pack's ids exempt on every page": {
        'healthy corpus: every denominator is exact',
        "pack: a pack's id is exempt on a page that names that pack and only there",
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    "page-defined id exempt for any family, not its path's": {
        'healthy corpus: every denominator is exact',
        "page-defined: a path on the line before a fence or in its first comment defines the stem, for that path's family only",
        'the flag set is exactly the invented, wrong-kind and unexcused ids',
    },
    'asset-side zero floor removed': {
        'an EMPTY asset tree fails (exit 3) rather than typing nothing and passing',
    },
    'docs zero floor removed': {
        'an EMPTY docs corpus fails (exit 3)',
        'docs with JSON but no typed pair fail (exit 3): nothing was checked',
    },
    'missing-input SKIP returns 0 instead of 2': {
        'missing asset cache exits 2',
        'missing docs corpus exits 2',
        'missing source cache exits 2',
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mutations', action='store_true',
                    help='reintroduce each known defect and assert the EXACT set of cases that goes red')
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--measure', action='store_true', help='print each mutation\'s red set as a literal')
    a = ap.parse_args()

    res, crashed = all_cases(CHECKER)
    if crashed:
        print(f'  FAIL  the checker crashed on {len(crashed)} case(s): ' + ', '.join(crashed))
        return 1
    if len(res) < MIN_CASES:
        print(f'  FAIL  {len(res)} case(s) ran, floor is {MIN_CASES}. A fixture that examines '
              f'nothing reports the same thing as one that passes.')
        return 1
    fails = {k: v for k, v in res.items() if v}
    for label in res:
        if a.verbose and not res[label]:
            print(f'  ok   {label}')
    print(f'\nFIXTURE {len(res)} case(s): {len(res) - len(fails)} passed, {len(fails)} failed')
    for k, v in fails.items():
        print(f'  FAIL {k}: ' + '; '.join(v))
    rc = 1 if fails else 0
    if not a.mutations and not a.measure:
        return rc

    if len(MUTATIONS) < MIN_MUTATIONS and not a.measure:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s) defined, floor is {MIN_MUTATIONS}. "expected red '
              f'set asserted exactly" over an empty table is a claim about nothing.')
        return 1
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control in MUTATIONS. Without it a broken harness reports every '
              'defect as caught.')
        return 1
    print(f'\nMUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
    with tempfile.TemporaryDirectory() as td:
        for label, (edits, _unused, names) in MUTATIONS.items():
            expect = EXPECT[label]
            src = CHECKER.read_text()
            bad = [old for old, _ in edits if src.count(old) != 1]
            if bad:
                print(f'  FAIL {label}: an anchor occurs {src.count(bad[0])} time(s) in the checker, '
                      f'not once ({bad[0][:60]!r}...). `replace` would edit the first, which is whichever '
                      f'comes earlier in the file - say where you mean.')
                rc = 1
                continue
            for old, new in edits:
                src = src.replace(old, new, 1)
            mutant = pathlib.Path(td) / 'mutant.py'
            mutant.write_text(src)
            mres, mcrashed = all_cases(mutant)
            if mcrashed:
                rc = 1
                print(f'  FAIL {label}: the MUTANT CRASHED on {len(mcrashed)} case(s) - it is broken, '
                      f'not caught. Fix the mutation, not the case.')
                continue
            red = {k for k, v in mres.items() if v}
            if a.measure:
                print(f'--- {label}\n    {sorted(red)!r}')
                continue
            if label.startswith('IDENTITY') and red:
                print(f'  FAIL {label}: the control reddened {len(red)} case(s); the harness itself is '
                      f'broken, so no mutation below would mean anything. Aborting.')
                for x in sorted(red):
                    print(f'         {x}')
                return 1
            missing_own = names - red
            if missing_own:
                rc = 1
                print(f'  FAIL {label}: the case this defect belongs to stayed GREEN')
                for x in sorted(missing_own):
                    print(f'         {x}')
                continue
            if red == expect:
                print(f'  ok   {label} -> {len(red)} case(s) red, exactly as expected')
                if a.verbose:
                    for r in sorted(red):
                        print(f'         {r}')
            else:
                rc = 1
                print(f'  FAIL {label}:')
                for x in sorted(expect - red):
                    print(f'         expected red, stayed green: {x}')
                for x in sorted(red - expect):
                    print(f'         unexpectedly red: {x}')
    return rc


if __name__ == '__main__':
    sys.exit(main())
