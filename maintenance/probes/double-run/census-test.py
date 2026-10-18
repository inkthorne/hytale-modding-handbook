#!/usr/bin/env python3
"""
census-test.py -- does census.py see a change? (the negative control for the census)

    python3 -I maintenance/probes/double-run/census-test.py WORKDIR [--src DIR]

Copies the decompiled-source cache (read-only; default ~/.cache/hytale-jar/src) to WORKDIR/src, which must
be absent, empty, or carry the marker .double-run-census-test (nothing else is ever removed), and plants
defects there one at a time. For each, census.py must move exactly the named row to the named label and
change no other row:

    AttachBeam           gets an empty simulateFirstRun        firstRun -> no-op
    ApplyEffect          loses its empty simulateFirstRun      no-op    -> firstRun
    DamageEntity         simulateTick0 becomes `return;`       tick0    -> no-op
    ChangeStat           simulateFirstRun calls firstRun twice, with other code  firstRun -> firstRun+
    ModifyInventory      getWaitForDataFrom returns Client     wait Server -> Client
    Select ("Selector")  simulateTick0 calls tick0             no-op    -> tick0

and the label paths a real build does not reach (review of 41db9fe..5be0ad0, LOW-2), each on a class of the
real tree:

    AttachBeam           simulateFirstRun { super.simulateFirstRun(...); }                firstRun stays firstRun
    AttachBeam           simulateTick0 { this.firstRun(...); }                            firstRun stays firstRun
    AttachBeam           simulateTick0 with other code around this.firstRun               firstRun -> firstRun+
    AttachBeam           simulateTick0 with other code around super.simulateTick0         firstRun -> firstRun+
    AttachBeam           simulateFirstRun with other code around super.simulateFirstRun   firstRun -> firstRun+
    DamageEntity         simulateTick0 with other code around tick0                       tick0 -> tick0+
    Selector             simulateTick0 gets a body that reaches no hook                   no-op -> own
    Wielding             simulateTick0 is a lone super.simulateTick0(...)                 own+ -> own
    AddItem              the block hook simulateInteractWithBlock gets a body             via-...:no-op -> via-...:other
    ChangeStat and ChangeStatWithModifier   their base ChangeStatBase gets an empty simulateFirstRun
                                                                                          both firstRun -> no-op

A case "stays" when the label is kept but the row's note changes: the row must still be the only one that moved.

The unmutated copy must reproduce the labels the README quotes, and the census must visit 135 names: a
census that visits nothing, or one whose baseline is not the quoted one, is VOID here (exit 2).
"""
from __future__ import annotations
import pathlib, re, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
CENSUS = HERE / 'census.py'
CFG = 'com/hypixel/hytale/server/core/modules/interaction/interaction/config'


def rows(src: pathlib.Path):
    out = subprocess.run([sys.executable, '-I', str(CENSUS), '--src', str(src)], capture_output=True, text=True)
    if out.returncode != 0:
        return None, out.stdout + out.stderr
    text = out.stdout
    per = text.split('PER CLASS')[1].split('SUMMARY')[0].strip().split('\n')[1:]
    table = {}
    cur = None
    for line in per:
        if not line.startswith('    '):
            cur = line.strip()
            table[cur] = {}
        else:
            k, _, v = line.strip().partition('  ')
            table[cur][k] = v.strip()
    return table, text


def brace_end(t: str, i: int) -> int:
    """Index of the `}` closing the `{` at t[i] (the decompiled sources have no braces inside strings that matter here)."""
    depth = 0
    for j in range(i, len(t)):
        if t[j] == '{':
            depth += 1
        elif t[j] == '}':
            depth -= 1
            if depth == 0:
                return j
    raise ValueError('unbalanced')


def set_body(t: str, method: str, body: str) -> str:
    """Replace the body of the first method `method` declared in t. Returns t unchanged if there is none."""
    m = re.search(r'\b' + method + r'\s*\([^)]*\)\s*\{', t)
    if not m:
        return t
    b = m.end() - 1
    return t[:b + 1] + '\n        ' + body + '\n    ' + t[brace_end(t, b):]


def add_method(t: str, text: str) -> str:
    """Add a method before the last `}` of the file (every file used here is one top-level class)."""
    k = t.rstrip().rfind('}')
    return t[:k] + '\n' + text + '\n' + t[k:]


S0 = ('(boolean firstRun, float time, @Nonnull InteractionType type, @Nonnull InteractionContext context, '
      '@Nonnull CooldownHandler cooldownHandler)')
SF = ('(@Nonnull InteractionType type, @Nonnull InteractionContext context, '
      '@Nonnull CooldownHandler cooldownHandler)')
ARGS0 = 'firstRun, time, type, context, cooldownHandler'
ARGSF = 'type, context, cooldownHandler'
BEAM = 'com/hypixel/hytale/builtin/beam/interaction/AttachBeamInteraction.java'


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 3
    work = pathlib.Path(args[0]).resolve()
    src = pathlib.Path(args[args.index('--src') + 1]) if '--src' in args else pathlib.Path.home() / '.cache/hytale-jar/src'
    marker = work / '.double-run-census-test'
    if work.exists() and not marker.exists():
        if not work.is_dir() or any(work.iterdir()):
            print(f'FAIL  {work} exists, is not empty and has no marker; give a new path')
            return 3
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    marker.write_text('')
    copy = work / 'src'
    shutil.copytree(src, copy)

    base, text = rows(copy)
    if base is None or len(base) < 100:
        print('VOID  the unmutated copy did not census', text[-300:])
        return 2
    want = {'AttachBeam': 'firstRun', 'ApplyEffect': 'no-op', 'DamageEntity': 'tick0', 'ChangeStat': 'firstRun',
            'ModifyInventory': 'firstRun', 'Selector': 'no-op'}
    for n, w in want.items():
        got = base[n]['sim'].split()[0]
        if got != w:
            print(f'VOID  baseline {n} is {got}, the README quotes {w}')
            return 2
    if base['ModifyInventory']['wait'].split()[0] != 'Server':
        print('VOID  baseline ModifyInventory wait is not Server')
        return 2
    print(f'baseline: {len(base)} rows, labels as quoted')

    CFGS = f'{CFG}/server'
    cases = [
        ('AttachBeam gets an empty simulateFirstRun', [('AttachBeam', 'sim', 'no-op')], BEAM,
         lambda t: add_method(t, '    protected void simulateFirstRun' + SF + ' {\n    }\n')),
        ('ApplyEffect loses its simulateFirstRun', [('ApplyEffect', 'sim', 'firstRun')],
         f'{CFG}/none/simple/ApplyEffectInteraction.java',
         lambda t: re.sub(r'    @Override\n    protected void simulateFirstRun[^{]*\{\s*\}\n', '', t, count=1)),
        ('DamageEntity simulateTick0 becomes return', [('DamageEntity', 'sim', 'no-op')],
         f'{CFGS}/DamageEntityInteraction.java',
         lambda t: re.sub(r'(protected void simulateTick0\([^)]*\) \{)\n\s*this\.tick0\([^;]*;\n', r'\1\n        return;\n', t, count=1)),
        ('ChangeStat simulateFirstRun has its own code and calls firstRun', [('ChangeStat', 'sim', 'firstRun+')],
         f'{CFGS}/ChangeStatInteraction.java',
         lambda t: add_method(t, '    @Override\n    protected void simulateFirstRun' + SF + ' {\n        System.out.println("own");\n'
                                 '        this.firstRun(' + ARGSF + ');\n        this.firstRun(' + ARGSF + ');\n    }\n')),
        ('ModifyInventory waits for Client', [('ModifyInventory', 'wait', 'Client')],
         f'{CFGS}/ModifyInventoryInteraction.java',
         lambda t: t.replace('return WaitForDataFrom.Server;', 'return WaitForDataFrom.Client;', 1)),
        ('Select simulateTick0 calls tick0', [('Selector', 'sim', 'tick0')],
         f'{CFG}/none/SelectInteraction.java',
         lambda t: set_body(t, 'simulateTick0', 'this.tick0(' + ARGS0 + ');')),
        # ---- label paths a real build does not reach (LOW-2)
        ('AttachBeam simulateFirstRun is a lone super.simulateFirstRun (stays firstRun; was "own")', [('AttachBeam', 'sim', 'firstRun')], BEAM,
         lambda t: add_method(t, '    @Override\n    protected void simulateFirstRun' + SF + ' {\n        super.simulateFirstRun(' + ARGSF + ');\n    }\n')),
        ('AttachBeam simulateTick0 is a lone this.firstRun (stays firstRun; was "via-firstRun:other")', [('AttachBeam', 'sim', 'firstRun')], BEAM,
         lambda t: add_method(t, '    @Override\n    protected void simulateTick0' + S0 + ' {\n        this.firstRun(' + ARGSF + ');\n    }\n')),
        ('AttachBeam simulateTick0 has code around this.firstRun', [('AttachBeam', 'sim', 'firstRun+')], BEAM,
         lambda t: add_method(t, '    @Override\n    protected void simulateTick0' + S0 + ' {\n        System.out.println("own");\n        this.firstRun(' + ARGSF + ');\n    }\n')),
        ('AttachBeam simulateTick0 has code around super.simulateTick0', [('AttachBeam', 'sim', 'firstRun+')], BEAM,
         lambda t: add_method(t, '    @Override\n    protected void simulateTick0' + S0 + ' {\n        System.out.println("own");\n        super.simulateTick0(' + ARGS0 + ');\n    }\n')),
        ('AttachBeam simulateFirstRun has code around super.simulateFirstRun', [('AttachBeam', 'sim', 'firstRun+')], BEAM,
         lambda t: add_method(t, '    @Override\n    protected void simulateFirstRun' + SF + ' {\n        System.out.println("own");\n        super.simulateFirstRun(' + ARGSF + ');\n    }\n')),
        ('DamageEntity simulateTick0 has code around tick0', [('DamageEntity', 'sim', 'tick0+')],
         f'{CFGS}/DamageEntityInteraction.java',
         lambda t: re.sub(r'(protected void simulateTick0\([^)]*\) \{)\n', r'\1\n        System.out.println("own");\n', t, count=1)),
        ('Select simulateTick0 gets a body that reaches no hook', [('Selector', 'sim', 'own')],
         f'{CFG}/none/SelectInteraction.java',
         lambda t: set_body(t, 'simulateTick0', 'System.out.println("own");')),
        ('Wielding simulateTick0 is a lone super.simulateTick0', [('Wielding', 'sim', 'own')],
         f'{CFG}/client/WieldingInteraction.java',
         lambda t: set_body(t, 'simulateTick0', 'super.simulateTick0(' + ARGS0 + ');')),
        ('AddItem block hook gets a body', [('AddItem', 'sim', 'via-simulateInteractWithBlock:other')],
         f'{CFG}/client/AddItemInteraction.java',
         lambda t: set_body(t, 'simulateInteractWithBlock', 'System.out.println("own");')),
        ('ChangeStatBase gets an empty simulateFirstRun: both subclasses move', [('ChangeStat', 'sim', 'no-op'), ('ChangeStatWithModifier', 'sim', 'no-op')],
         f'{CFGS}/ChangeStatBaseInteraction.java',
         lambda t: add_method(t, '    @Override\n    protected void simulateFirstRun' + SF + ' {\n    }\n')),
    ]
    fails = 0
    for label, expect, path, fn in cases:
        p = copy / path
        orig = p.read_text()
        new = fn(orig)
        if new == orig:
            print(f'FAIL  {label}: the mutation changed nothing; the test is broken')
            fails += 1
            continue
        p.write_text(new)
        try:
            after, t2 = rows(copy)
        finally:
            p.write_text(orig)
        if after is None:
            print(f'FAIL  {label}: census crashed on the mutated copy: {t2[-200:]}')
            fails += 1
            continue
        moved = sorted(n for n in base if base[n] != after.get(n))
        names = sorted(n for n, _, _ in expect)
        got = {n: after[n][k].split()[0] for n, k, _ in expect}
        was = {n: base[n][k].split()[0] for n, k, _ in expect}
        if moved == names and all(got[n] == w for n, _, w in expect):
            print(f'PASS  {label}: ' + ', '.join(f'{n} {k} {was[n]} -> {got[n]}' for n, k, _ in expect) + '; no other row moved')
        else:
            print(f'FAIL  {label}: rows moved {moved} (wanted {names}), ' + ', '.join(f'{n} {k} is {got[n]} (wanted {w})' for n, k, w in expect))
            fails += 1
    # a --src that is a symlink: cache-meta.txt sits beside the real cache, not beside the link (review of 94d2a32..3437c5d, MEDIUM-2).
    # The defect needs a link whose parent holds no cache-meta.txt, and the real cache's parent holds one; the control is that precondition.
    (work / 'cache-meta.txt').write_text('version=planted jar_sha=0123\n')
    (work / 'via').mkdir()
    (work / 'via' / 'src').symlink_to(copy)
    if (work / 'via' / 'cache-meta.txt').exists() or not (copy.parent / 'cache-meta.txt').exists():
        print('VOID  the symlink case is not set up: the link\'s parent must hold no cache-meta.txt and the real cache\'s parent one')
        return 2
    out = subprocess.run([sys.executable, '-I', str(CENSUS), '--src', str(work / 'via' / 'src')], capture_output=True, text=True)
    first = out.stdout.split('\n')[0]
    if first == 'build: version=planted jar_sha=0123 ':
        print('PASS  a --src that is a symlink finds cache-meta.txt beside the real cache: ' + first)
    else:
        print(f'FAIL  a --src that is a symlink does not find the cache-meta.txt beside the real cache: {first!r}')
        fails += 1
    print(f'---- {fails} failed')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
