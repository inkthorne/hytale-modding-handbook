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

    SIG = ('(@Nonnull InteractionType type, @Nonnull InteractionContext context, '
           '@Nonnull CooldownHandler cooldownHandler)')
    cases = [
        ('AttachBeam gets an empty simulateFirstRun', 'AttachBeam', 'sim', 'no-op',
         'com/hypixel/hytale/builtin/beam/interaction/AttachBeamInteraction.java',
         lambda t: t.replace('    @Override\n    protected void firstRun', '    protected void simulateFirstRun' + SIG + ' {\n    }\n\n    @Override\n    protected void firstRun', 1)),
        ('ApplyEffect loses its simulateFirstRun', 'ApplyEffect', 'sim', 'firstRun',
         f'{CFG}/none/simple/ApplyEffectInteraction.java',
         lambda t: re.sub(r'    @Override\n    protected void simulateFirstRun[^{]*\{\s*\}\n', '', t, count=1)),
        ('DamageEntity simulateTick0 becomes return', 'DamageEntity', 'sim', 'no-op',
         f'{CFG}/server/DamageEntityInteraction.java',
         lambda t: re.sub(r'(protected void simulateTick0\([^)]*\) \{)\n\s*this\.tick0\([^;]*;\n', r'\1\n        return;\n', t, count=1)),
        ('ChangeStat simulateFirstRun has its own code and calls firstRun', 'ChangeStat', 'sim', 'firstRun+',
         f'{CFG}/server/ChangeStatInteraction.java',
         lambda t: t.replace('    @Override\n    protected void firstRun', '    @Override\n    protected void simulateFirstRun' + SIG + ' {\n        System.out.println("own");\n        this.firstRun(type, context, cooldownHandler);\n        this.firstRun(type, context, cooldownHandler);\n    }\n\n    @Override\n    protected void firstRun', 1)),
        ('ModifyInventory waits for Client', 'ModifyInventory', 'wait', 'Client',
         f'{CFG}/server/ModifyInventoryInteraction.java',
         lambda t: t.replace('return WaitForDataFrom.Server;', 'return WaitForDataFrom.Client;', 1)),
        ('Select simulateTick0 calls tick0', 'Selector', 'sim', 'tick0',
         f'{CFG}/none/SelectInteraction.java',
         None),
    ]
    fails = 0
    for label, name, key, wanted, path, fn in cases:
        p = copy / path
        orig = p.read_text()
        if fn is None:
            # Select: replace the body of simulateTick0 by a bare call to tick0
            m = re.search(r'(protected void simulateTick0\([^)]*\) \{)', orig)
            if not m:
                print(f'FAIL  {label}: no simulateTick0 in {path}')
                fails += 1
                continue
            # find the matching close brace
            depth, i = 0, m.end() - 1
            while True:
                if orig[i] == '{':
                    depth += 1
                elif orig[i] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            new = orig[:m.end()] + '\n        this.tick0(firstRun, time, type, context, cooldownHandler);\n    ' + orig[i:]
        else:
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
        moved = [n for n in base if base[n] != after.get(n)]
        got = after[name][key].split()[0]
        if moved == [name] and got == wanted:
            print(f'PASS  {label}: {name} {key} {base[name][key].split()[0]} -> {got}; no other row moved')
        else:
            print(f'FAIL  {label}: rows moved {moved}, {name} {key} is {got} (wanted {wanted})')
            fails += 1
    print(f'---- {fails} failed')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
