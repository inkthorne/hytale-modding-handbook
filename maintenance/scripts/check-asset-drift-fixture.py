#!/usr/bin/env python3
"""
Run verify-docs.sh's OWN "Asset drift vs baseline" section under injected failures, and (with
--mutations) verify that each guard in it is the thing that catches its failure.

WHY THE SECTION'S TEXT AND NOT A HELPER. The section computed each half's drift count as
`... | diff ... | grep -c '^[<>]' || true`, so the only status it read was grep's. One unreadable
Common index read as every line changed; BOTH unreadable read as 0 and printed "0 changed Common
assets - docs verified against this build still apply", a false green; a hash-server-assets.sh that
exited 123 or 1 left a short index that was counted as drift. A helper with a fixture of its own
would have tested the helper and left the wrapper that reads the helper's status untested, which is
the same defect one level up. So this file cuts the section out of verify-docs.sh itself (from its
`section "[HARD] Asset drift vs baseline` line to the next `# =====` line) and runs that text, under
the real section()/pass()/fail()/warn()/info() definitions read from verify-docs.sh, in a temp root
that holds the baselines, a hash script, and shims of sort, diff and grep on PATH. If the section is
renamed, this anchor moves with it (the cut asserts it finds exactly one).

FAILURES ARE INJECTED WITHOUT DEPENDING ON THE USER ID. An unreadable file is a chmod that root
ignores. Instead: a `sort` shim that exits 2 when an operand contains a given substring (so the
baseline sort and the live sort fail separately, which is how the single-sided hole was found), a
`diff` and a `grep -c` shim that exit 2 on their Nth call (the Common half runs first), and stub
hash scripts that exit 123 after two rows and exit 1 with none. The shim for `sort` also reaches the
sort inside the real hash-server-assets.sh, which is one more way for it to fail.

THE NEGATIVE CONTROL. maintenance/fixtures/asset-drift/section-fbbb664.sh is the section as it was
at fbbb664, before the fix. The fixture runs it first, with both sorts failing, and refuses to
report unless it prints "0 changed Common assets ... still apply" with HARD_FAILS=0: the defect, as
measured. A run that cannot reproduce it has nothing to say about the fix.

Usage:
  python3 maintenance/scripts/check-asset-drift-fixture.py [-v]
  python3 maintenance/scripts/check-asset-drift-fixture.py --mutations [-v]
"""
from __future__ import annotations
import argparse, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / 'verify-docs.sh'
OLD_SECTION = HERE.parent / 'fixtures' / 'asset-drift' / 'section-fbbb664.sh'
HASH_SCRIPT = HERE / 'hash-server-assets.sh'
ANCHOR = 'section "[HARD] Asset drift vs baseline'
ANSI = re.compile(r'\x1b\[[0-9;]*m')

# FLOORS, as in the other fixtures: lowering one needs a reason in the commit message.
MIN_CASES = 29
MIN_MUTATIONS = 29

REAL = {n: shutil.which(n) for n in ('sort', 'diff', 'grep')}
for _n, _p in REAL.items():
    if not _p:
        sys.exit(f'{_n} not found on PATH')


def section_text(src: str) -> str:
    n = src.count(ANCHOR)
    if n != 1:
        raise SystemExit(f'FAIL  {ANCHOR!r} occurs {n} time(s) in verify-docs.sh, not once - '
                         f'the section was renamed or duplicated; move this anchor with it')
    s = src.index(ANCHOR)
    return src[s:src.index('\n# =====', s)] + '\n'


def prelude() -> str:
    """The shell options (`set -u`) and the real HARD_FAILS/section/pass/fail/warn/info definitions of
    verify-docs.sh, verbatim: fail() incrementing HARD_FAILS is part of what the section's severity
    means, and an unset variable in the section must stop it here as it would there."""
    v = VERIFY.read_text()
    assert v.count('\nset -u\n') == 1, 'verify-docs.sh no longer has exactly one `set -u` line'
    a = v.index('\nHARD_FAILS=0\n') + 1
    i = v.index('\ninfo()', a) + 1
    return 'set -u\n' + v[a:v.index('\n', i) + 1]


SORT_SHIM = f'''#!/usr/bin/env bash
if [ -n "${{SHIM_SORT_FAIL_ARG:-}}" ]; then
  for a in "$@"; do
    case "$a" in *"$SHIM_SORT_FAIL_ARG"*)
      # SHIM_SORT_PARTIAL=1: two sorted rows reach stdout BEFORE the failure, as a sort that dies midway
      # leaves a short file with a nonzero status. Writing nothing is caught by the 0-row guard, so only
      # this mode isolates the sort-status guard.
      [ "${{SHIM_SORT_PARTIAL:-}}" = 1 ] && {REAL['sort']} "$@" | sed 2q
      echo "sort: shim: cannot read: $a" >&2; exit 2 ;; esac
  done
fi
exec {REAL['sort']} "$@"
'''
# diff and grep fail on the Nth call (counted in a file); grep only counts `-c` calls, the one the
# section makes. The Common half runs before the Server half, so call 1 is Common and call 2 Server.
NTH_SHIM = '''#!/usr/bin/env bash
want="${{{var}:-}}"
if [ -n "$want" ] {gate}; then
  f="$SHIM_STATE/{name}.n"; n=$(( $(cat "$f" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$f"
  if [ "$n" = "$want" ]; then echo "{name}: shim: injected failure" >&2; exit 2; fi
fi
exec {real} "$@"
'''


def mk_shims(d: pathlib.Path):
    d.mkdir()
    (d / 'sort').write_text(SORT_SHIM)
    (d / 'diff').write_text(NTH_SHIM.format(var='SHIM_DIFF_FAIL_CALL', gate='', name='diff', real=REAL['diff']))
    (d / 'grep').write_text(NTH_SHIM.format(var='SHIM_GREP_FAIL_CALL', gate='&& [ "${1:-}" = "-c" ]',
                                            name='grep', real=REAL['grep']))
    for f in d.iterdir():
        f.chmod(0o755)


COMMON = [  # path order here is deliberately not C-sorted ('-' sorts before '_')
    'Common/Icons/Face_Scar.png', 'Common/Sounds/a.ogg', 'Common/Icons/Face-Scar.png',
    'Common/UI/Custom/Z.ui', 'Common/Models/m.blockymodel', 'Common/Zed/b.png']
SERVER = {'Server/Item/Items/A.json': '{"a":1}\n', 'Server/Item/Items/B.json': '{"b":2}\n',
          'Server/Drops/C.json': '{"c":3}\n', 'Server/Drops/D.json': '{"d":4}\n',
          'Cosmetics/Hair/E.json': '{"e":5}\n', 'Cosmetics/Hair/F.json': '{"f":6}\n'}


def build_template(tpl: pathlib.Path):
    """The healthy tree: assets (a Server/Cosmetics tree and a Common index) and the baselines
    that equal them. The Server baseline is produced by the REAL hash script on the real sort."""
    (tpl / 'assets').mkdir(parents=True)
    for rel, body in SERVER.items():
        p = tpl / 'assets' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    rows = [f'{i + 1:064x} {p}' for i, p in enumerate(COMMON)]
    (tpl / 'assets' / 'CommonAssetsIndex.hashes').write_text('\n'.join(reversed(rows)) + '\n')
    b = tpl / 'maintenance' / 'baseline'
    b.mkdir(parents=True)
    (b / 'CommonAssetsIndex.hashes').write_text('\n'.join(rows) + '\n')
    out = subprocess.run([str(HASH_SCRIPT), str(tpl / 'assets')], capture_output=True, text=True, check=True).stdout
    assert len(out.splitlines()) == len(SERVER), out
    (b / 'ServerAssetsIndex.hashes').write_text(out)
    (tpl / 'maintenance' / 'scripts').mkdir()
    shutil.copy(HASH_SCRIPT, tpl / 'maintenance' / 'scripts' / 'hash-server-assets.sh')


STUB_PARTIAL = '#!/usr/bin/env bash\ncat <<\'EOF\'\n{rows}\nEOF\necho "stub: could not hash every file" >&2\nexit 123\n'
STUB_NOROWS = '#!/usr/bin/env bash\nexit 0\n'
STUB_EMPTY = '#!/usr/bin/env bash\necho "stub: cannot enter a directory" >&2\nexit 1\n'


def run_section(text: str, tpl: pathlib.Path, work: pathlib.Path, name: str, *, shims=None, hash_stub=None,
                common_live=None, common_base=None, server_edit=None, drop=None, no_common_base=False,
                no_server=False, tmpdir=None, empty=(), no_server_base=False, no_common_live=False, inject=None):
    """Run `text` (a section) in a copy of the template, with a TMPDIR of its own. Returns (exit
    status, stripped output); the output ends with the number of entries left in that TMPDIR."""
    root = work / name
    shutil.copytree(tpl, root)
    assets = root / 'assets'
    if common_live is not None:
        (assets / 'CommonAssetsIndex.hashes').write_text('\n'.join(common_live) + '\n')
    base = root / 'maintenance' / 'baseline'
    if common_base is not None:
        (base / 'CommonAssetsIndex.hashes').write_text('\n'.join(common_base) + '\n')
    if drop:   # a baseline with `drop` rows deleted: the dose
        for f in ('CommonAssetsIndex.hashes', 'ServerAssetsIndex.hashes'):
            ls = (base / f).read_text().splitlines()
            (base / f).write_text('\n'.join(ls[drop:]) + '\n')
    if server_edit:
        server_edit(assets)
    if no_common_base:
        (base / 'CommonAssetsIndex.hashes').unlink()
    if no_common_live:
        (assets / 'CommonAssetsIndex.hashes').unlink()
    if no_server_base:
        (base / 'ServerAssetsIndex.hashes').unlink()
    for what, f in (('common-live', assets / 'CommonAssetsIndex.hashes'), ('common-base', base / 'CommonAssetsIndex.hashes'),
                    ('server-base', base / 'ServerAssetsIndex.hashes')):
        if what in empty:
            f.write_text('')
    if no_server:
        shutil.rmtree(assets / 'Server')
    sh = root / 'maintenance' / 'scripts' / 'hash-server-assets.sh'
    if hash_stub == 'partial':
        rows = '\n'.join((base / 'ServerAssetsIndex.hashes').read_text().splitlines()[:2])
        sh.write_text(STUB_PARTIAL.replace('{rows}', rows))
    elif hash_stub == 'empty1':
        sh.write_text(STUB_EMPTY)
    elif hash_stub == 'norows':
        sh.write_text(STUB_NOROWS)
    sh.chmod(0o755)
    shimdir = root / 'shims'
    mk_shims(shimdir)
    (root / 'shimstate').mkdir()
    env = dict(os.environ, PATH=f'{shimdir}{os.pathsep}{os.environ["PATH"]}', SHIM_STATE=str(root / 'shimstate'),
               PYTHONDONTWRITEBYTECODE='1')
    for k, v in (shims or {}).items():
        env[k] = v.replace('@ASSETS@', str(assets))
    tmp = root / 'tmp'
    tmp.mkdir()
    env['TMPDIR'] = tmpdir or str(tmp)
    if inject:
        n = text.count(inject[0])
        assert n == 1, f'the injection site occurs {n} time(s) in the section'
        text = text.replace(inject[0], inject[1], 1)
    # DRIFT_TMP_AFTER_SECTION: whether the section's own cleanup ran (the EXIT trap has not fired yet)
    script = (prelude() + f'ASSETS={str(assets)!r}\n' + text
              + 'echo "DRIFT_TMP_AFTER_SECTION=$([ -d "${DRIFT_TMP:-}" ] && echo present || echo gone)"\n'
              + 'echo "DRIFT_TMP_CLEARED=$([ -z "${DRIFT_TMP:-}" ] && echo yes || echo no)"\n'
              + 'echo "HARD_FAILS=$HARD_FAILS"\n')
    p = subprocess.run(['bash', '-c', script], capture_output=True, text=True, cwd=root, env=env)
    # the temp path of the assets is reported as @ASSETS@, so an expected line need not know it
    out = ANSI.sub('', p.stdout + p.stderr).replace(str(assets), '@ASSETS@')
    return p.returncode, out + f'TMP_LEFT={len(list(tmp.iterdir()))}\n'


def hard(out: str) -> int:
    m = re.findall(r'^HARD_FAILS=(\d+)$', out, re.M)
    return int(m[-1]) if m else -1


# The exact lines of the healthy run, so that a denominator leaving, a count appearing where it
# should not, or a half going silent is a mismatch and not a quieter pass.
CLEAN = [
    'INFO  Common index: 6 baseline row(s) compared with 6 live row(s)',
    'INFO  0 changed Common assets — docs verified against this build still apply',
    'INFO  Server/Cosmetics index: 6 baseline row(s) compared with 6 row(s) hashed from the extracted tree',
    'INFO  0 changed Server/Cosmetics assets — data-format docs verified against this build still apply',
]
C_DONE = 'INFO  0 changed Common assets'
S_DONE = 'INFO  0 changed Server/Cosmetics assets'


def body(out: str) -> list[str]:
    return [l.strip() for l in out.splitlines()
            if l.strip() and not l.startswith(('HARD_FAILS=', '== ', 'DRIFT_TMP_AFTER_SECTION=', 'DRIFT_TMP_CLEARED=', 'TMP_LEFT='))]


def all_cases(text: str, tpl, work) -> dict[str, list[str]]:
    res: dict[str, list[str]] = {}

    def case(label, rc_out, *, hf, exact=None, must=(), must_not=(), want_rc=0, cleaned='section'):
        """cleaned: 'section' - the section removed its temp dir before it ended (the marker says so);
        'exit' - the section did not end (an exit inside it) and only the EXIT trap could have; in
        both, nothing is left in TMPDIR once the process is gone."""
        rc, out = rc_out
        pr = []
        if rc != want_rc:
            pr.append(f'harness exit {rc}, wanted {want_rc}: {out[-300:]!r}')
        if hf is not None and hard(out) != hf:
            pr.append(f'HARD_FAILS {hard(out)}, wanted {hf}')
        if 'TMP_LEFT=0\n' not in out:
            pr.append(f'the temp dir was not removed: {re.findall("TMP_LEFT=.*", out)}')
        if cleaned == 'section' and 'DRIFT_TMP_AFTER_SECTION=gone' not in out:
            pr.append('the section left its temp dir in place when it ended')
        if cleaned == 'section' and 'DRIFT_TMP_CLEARED=yes' not in out:
            pr.append('the section left DRIFT_TMP set to the removed path (the EXIT trap would act on it)')
        if cleaned == 'exit' and 'DRIFT_TMP_AFTER_SECTION' in out:
            pr.append('the section was meant to exit before its end')
        if exact is not None and body(out) != exact:
            pr.append(f'lines {body(out)!r}, wanted {exact!r}')
        pr += [f'missing {m!r}' for m in must if m not in out]
        pr += [f'unexpected {m!r}' for m in must_not if m in out]
        res[label] = pr

    n = [0]

    def go(**kw):
        n[0] += 1
        return run_section(text, tpl, work, f'c{n[0]}', **kw)

    case('healthy: both halves print their denominator and "0 changed", nothing else', go(), hf=0, exact=CLEAN)
    # (the template's live Common index is in the reverse order of the baseline: the healthy case
    # reading 0 changed is what shows the sorts do their job.)

    # DRIFT. Common: one hash changed (2 lines) and one row added (1). Server: a file changed (2) and added (1).
    live = [r for r in (f'{i + 1:064x} {p}' for i, p in enumerate(COMMON))]
    live[0] = f'{0xdead:064x} {COMMON[0]}'
    live.append(f'{0xbeef:064x} Common/New/n.png')

    def edit(a):
        (a / 'Server/Item/Items/A.json').write_text('{"a":99}\n')
        (a / 'Server/Item/Items/G.json').write_text('{"g":7}\n')
    case('drift: changed, added and denominators of the two sides differ; WARN, not FAIL', go(common_live=live, server_edit=edit),
         hf=0, exact=[
             'INFO  Common index: 6 baseline row(s) compared with 7 live row(s)',
             'WARN  3 changed line(s) vs baseline — re-verify docs referencing those assets',
             'INFO  see: diff <(LC_ALL=C sort maintenance/baseline/CommonAssetsIndex.hashes) <(LC_ALL=C sort "@ASSETS@/CommonAssetsIndex.hashes")',
             'INFO  Server/Cosmetics index: 6 baseline row(s) compared with 7 row(s) hashed from the extracted tree',
             'WARN  3 changed line(s) vs ServerAssetsIndex baseline — re-verify docs referencing those assets',
             'INFO  see: maintenance/scripts/hash-server-assets.sh "@ASSETS@" | diff maintenance/baseline/ServerAssetsIndex.hashes -'])

    # THE DOSE. A baseline with k rows deleted must read exactly k changed, in each half.
    for k in (1, 3):
        case(f'dose: a baseline with {k} row(s) deleted prints exactly {k} changed, in each half', go(drop=k), hf=0,
             must=(f'Common index: {6 - k} baseline row(s) compared with 6 live row(s)',
                   f'WARN  {k} changed line(s) vs baseline',
                   f'Server/Cosmetics index: {6 - k} baseline row(s) compared with 6 row(s)',
                   f'WARN  {k} changed line(s) vs ServerAssetsIndex baseline'),
             must_not=('0 changed', '  FAIL  '))

    sortfail = lambda arg: {'SHIM_SORT_FAIL_ARG': arg}
    cb, cl = 'maintenance/baseline/CommonAssetsIndex', '@ASSETS@/CommonAssetsIndex'

    def common_failed(label, rc_out, what, hf=1):
        case(label, rc_out, hf=hf, must=(what, S_DONE), must_not=('changed line(s) vs baseline', C_DONE, 'Common index:'))

    common_failed('sort of the baseline fails (live fine): FAIL naming the step and its status, no count',
                  go(shims=sortfail(cb)), 'FAIL  asset drift (Common): could not sort the indexes for the diff (the baseline sort exited 2, the live index\'s 0;')
    common_failed('sort of the live index fails (baseline fine): FAIL naming the step and its status, no count',
                  go(shims=sortfail(cl)), 'FAIL  asset drift (Common): could not sort the indexes for the diff (the baseline sort exited 0, the live index\'s 2;')
    # a sort that writes two rows and THEN fails: the only input that reaches the status guard (a sort that
    # writes nothing is caught by the 0-row guard as well, so the cases above do not isolate it)
    partial = lambda arg: {'SHIM_SORT_FAIL_ARG': arg, 'SHIM_SORT_PARTIAL': '1'}
    common_failed('a baseline sort that writes 2 rows then exits 2: FAIL on the status, not a count of the short index',
                  go(shims=partial(cb)), 'FAIL  asset drift (Common): could not sort the indexes for the diff (the baseline sort exited 2, the live index\'s 0;')
    common_failed('a live-index sort that writes 2 rows then exits 2: FAIL on the status, not a count of the short index',
                  go(shims=partial(cl)), 'FAIL  asset drift (Common): could not sort the indexes for the diff (the baseline sort exited 0, the live index\'s 2;')
    common_failed('both sorts fail: FAIL, and no "0 changed Common assets ... still apply"',
                  go(shims=sortfail('CommonAssetsIndex.hashes')), 'the baseline sort exited 2, the live index\'s 2;')
    common_failed('diff of the Common indexes exits 2: FAIL naming diff and its status, no count',
                  go(shims={'SHIM_DIFF_FAIL_CALL': '1'}), 'FAIL  asset drift (Common): diff of the indexes exited 2 (0 and 1 are normal)')
    common_failed('the changed-line count of the Common diff exits 2: FAIL, no count',
                  go(shims={'SHIM_GREP_FAIL_CALL': '1'}), 'FAIL  asset drift (Common): counting the changed lines exited 2')

    def server_failed(label, rc_out, what, hf=1):
        case(label, rc_out, hf=hf, must=(what, C_DONE),
             must_not=('changed line(s) vs ServerAssetsIndex', S_DONE, 'Server/Cosmetics index:', 'data-format docs verified'))

    server_failed('hash script exits 123 after 2 rows: FAIL naming the script and its status, no count',
                  go(hash_stub='partial'), 'FAIL  asset drift (Server/Cosmetics): hash-server-assets.sh exited 123, so the generated index is incomplete')
    server_failed('hash script exits 1 with no rows: FAIL, not "the whole baseline removed"',
                  go(hash_stub='empty1'), 'FAIL  asset drift (Server/Cosmetics): hash-server-assets.sh exited 1, so the generated index is incomplete')
    server_failed('the sort inside the real hash script fails: its nonzero status is FAILed',
                  go(shims=sortfail('-k2')), 'FAIL  asset drift (Server/Cosmetics): hash-server-assets.sh exited 2')
    server_failed('diff of the Server indexes exits 2: FAIL naming diff and its status, no count',
                  go(shims={'SHIM_DIFF_FAIL_CALL': '2'}), 'FAIL  asset drift (Server/Cosmetics): diff of the indexes exited 2 (0 and 1 are normal)')
    server_failed('the changed-line count of the Server diff exits 2: FAIL, no count',
                  go(shims={'SHIM_GREP_FAIL_CALL': '2'}), 'FAIL  asset drift (Server/Cosmetics): counting the changed lines exited 2')

    # Each half stands alone and failures add up: both failing is two FAILs, not one.
    case('both halves fail: two FAILs, no count and no "still apply" line from either', go(shims=sortfail('CommonAssetsIndex.hashes'), hash_stub='partial'),
         hf=2, must=('asset drift (Common)', 'asset drift (Server/Cosmetics)'),
         must_not=(' changed ', 'still apply', 'row(s)'))

    case('mktemp fails: its own FAIL, and neither half is attempted', go(tmpdir='/nonexistent-asset-drift-tmp'), hf=1,
         must=('FAIL  asset drift: could not create a temporary directory (mktemp -d failed',),
         must_not=('could not sort', 'changed', 'Common index:', 'Server/Cosmetics index:'))

    # The skips that were already there stay WARNs: a missing input is not a failed computation.
    case('a missing Common baseline is the existing skip WARN, and the Server half still runs',
         go(no_common_base=True), hf=0,
         exact=['WARN  skipped (missing baseline or live index)'] + CLEAN[2:])
    case('a tree with no Server/ is the existing skip WARN, and the Common half still runs',
         go(no_server=True), hf=0,
         exact=CLEAN[:2] + ['WARN  Server-assets drift skipped (missing ServerAssetsIndex.hashes baseline or extracted Server/)'])
    # LOW-2 of the review: the skip conditions each need a case (a missing LIVE Common index, a missing
    # Server BASELINE), as the two that were there cover only the Common baseline and the Server/ dir.
    case('a missing live Common index is the existing skip WARN, and the Server half still runs',
         go(no_common_live=True), hf=0, exact=['WARN  skipped (missing baseline or live index)'] + CLEAN[2:])
    case('a missing Server baseline is the existing skip WARN, and the Common half still runs',
         go(no_server_base=True), hf=0,
         exact=CLEAN[:2] + ['WARN  Server-assets drift skipped (missing ServerAssetsIndex.hashes baseline or extracted Server/)'])
    # LOW-3: 0 rows on either side of either half is not a comparison. A WARN with the whole index as the
    # count was the old reading of a sort or hash script that exited 0 having written nothing.
    common_failed('the live Common index holds 0 rows: FAIL naming the side, no count',
                  go(empty=('common-live',)), 'FAIL  asset drift (Common): the live index holds 0 rows (baseline 6, live 0)')
    common_failed('the Common baseline holds 0 rows: FAIL naming the side, no count',
                  go(empty=('common-base',)), 'FAIL  asset drift (Common): the baseline index holds 0 rows (baseline 0, live 6)')
    server_failed('a hash script that exits 0 with no rows: FAIL naming the side, not the whole baseline removed',
                  go(hash_stub='norows'), 'FAIL  asset drift (Server/Cosmetics): the generated index holds 0 rows (baseline 6, generated 0; hash-server-assets.sh exited 0)')
    server_failed('the Server baseline holds 0 rows: FAIL naming the side, no count',
                  go(empty=('server-base',)), 'FAIL  asset drift (Server/Cosmetics): the baseline index holds 0 rows (baseline 0, generated 6;')
    # LOW-1: the temp dir. Every case above also asserts nothing is left in its TMPDIR and that the
    # section removed its dir before it ended. This one exits INSIDE the section, where only the trap can.
    mk = 'DRIFT_TMP="$(mktemp -d)" || DRIFT_TMP=""\n'
    case('an exit inside the section still removes the temp dir (the EXIT trap)',
         go(inject=(mk, mk + 'echo "work" > "$DRIFT_TMP/x"; exit 7\n')), hf=None, want_rc=7, cleaned='exit')
    res[CASE['trapcount']] = trap_problems(VERIFY.read_text())
    # the predicate's own control: it must see a second trap in the forms a line-start match misses
    seen = [trap_problems(VERIFY.read_text() + tail) for tail in ("\ntrue; trap 'echo replaced' EXIT\n", "\nx=1 && trap - EXIT\n", "\n( trap 'x' EXIT )\n")]
    res[CASE['trapcontrol']] = [] if all(seen) else [f'a second trap went unseen: {seen}']
    return res


def trap_problems(text: str) -> list[str]:
    """verify-docs.sh must hold exactly one `trap`, the drift section's EXIT trap: a second EXIT trap
    would REPLACE it (a leak) and a `trap - EXIT` would remove it. The word is searched on every line
    that is not a comment, anywhere on the line, not only at its start: `true; trap 'x' EXIT` and
    `x && trap - EXIT` are the forms a line-start match let through. This is static, so it also sees
    code the drift section's run never reaches; a runtime check of `trap -p EXIT` at the end of the
    section would see only the section. A comment and a string that contain the word would need the
    word to be dropped from them: there are none at present, and one would fail here loudly."""
    lines = [l for l in text.splitlines() if re.search(r'\btrap\b', l) and not l.lstrip().startswith('#')]
    ok = len(lines) == 1 and 'DRIFT_TMP' in lines[0] and lines[0].rstrip().endswith('EXIT') and lines[0].startswith('trap ')
    return [] if ok else [f'non-comment lines naming trap: {lines}']


def negative_control(tpl, work) -> int:
    """The section as it stood at fbbb664, both Common sorts failing: it must print the false green."""
    old = OLD_SECTION.read_text()
    rc, out = run_section(old, tpl, work, 'neg', shims={'SHIM_SORT_FAIL_ARG': 'CommonAssetsIndex.hashes'})
    ok = rc == 0 and 'INFO  0 changed Common assets — docs verified against this build still apply' in out and hard(out) == 0
    print(f'CONTROL the section at fbbb664, both Common sorts failing: '
          f'{"prints \"0 changed Common assets ... still apply\" with HARD_FAILS=0 (the defect, reproduced)" if ok else "DID NOT reproduce the false green"}')
    if not ok:
        print(out)
        return 1
    # and the single-sided failure counts the whole index as drift
    rc, out = run_section(old, tpl, work, 'neg2', shims={'SHIM_SORT_FAIL_ARG': 'maintenance/baseline/CommonAssetsIndex'})
    ok = '6 changed line(s) vs baseline' in out and hard(out) == 0
    print(f'CONTROL the section at fbbb664, only the baseline sort failing: '
          f'{"counts all 6 live rows as drift, HARD_FAILS=0 (reproduced)" if ok else "DID NOT reproduce"}')
    if not ok:
        print(out)
        return 1
    rc, out = run_section(old, tpl, work, 'neg3', hash_stub='partial')
    ok = 'changed line(s) vs ServerAssetsIndex baseline' in out and hard(out) == 0
    print(f'CONTROL the section at fbbb664, a hash script exiting 123: '
          f'{"counts the short index as drift, HARD_FAILS=0 (reproduced)" if ok else "DID NOT reproduce"}')
    if not ok:
        print(out)
        return 1
    return 0




# Short names for the cases, so the mutation table below can say which case a guard belongs to.
CASE = {
    'healthy': 'healthy: both halves print their denominator and "0 changed", nothing else',
    'drift': 'drift: changed, added and denominators of the two sides differ; WARN, not FAIL',
    'dose1': 'dose: a baseline with 1 row(s) deleted prints exactly 1 changed, in each half',
    'dose3': 'dose: a baseline with 3 row(s) deleted prints exactly 3 changed, in each half',
    'sortB': 'sort of the baseline fails (live fine): FAIL naming the step and its status, no count',
    'sortL': 'sort of the live index fails (baseline fine): FAIL naming the step and its status, no count',
    'sortBoth': 'both sorts fail: FAIL, and no "0 changed Common assets ... still apply"',
    'diffC': 'diff of the Common indexes exits 2: FAIL naming diff and its status, no count',
    'grepC': 'the changed-line count of the Common diff exits 2: FAIL, no count',
    'hash123': 'hash script exits 123 after 2 rows: FAIL naming the script and its status, no count',
    'hash1': 'hash script exits 1 with no rows: FAIL, not "the whole baseline removed"',
    'hashsort': 'the sort inside the real hash script fails: its nonzero status is FAILed',
    'diffS': 'diff of the Server indexes exits 2: FAIL naming diff and its status, no count',
    'grepS': 'the changed-line count of the Server diff exits 2: FAIL, no count',
    'both': 'both halves fail: two FAILs, no count and no "still apply" line from either',
    'mktemp': 'mktemp fails: its own FAIL, and neither half is attempted',
    'skipC': 'a missing Common baseline is the existing skip WARN, and the Server half still runs',
    'skipS': 'a tree with no Server/ is the existing skip WARN, and the Common half still runs',
    'skipCL': 'a missing live Common index is the existing skip WARN, and the Server half still runs',
    'skipSB': 'a missing Server baseline is the existing skip WARN, and the Common half still runs',
    'zeroCL': 'the live Common index holds 0 rows: FAIL naming the side, no count',
    'zeroCB': 'the Common baseline holds 0 rows: FAIL naming the side, no count',
    'zeroSH': 'a hash script that exits 0 with no rows: FAIL naming the side, not the whole baseline removed',
    'zeroSB': 'the Server baseline holds 0 rows: FAIL naming the side, no count',
    'early': 'an exit inside the section still removes the temp dir (the EXIT trap)',
    'trapcount': "verify-docs.sh sets exactly one EXIT trap, the drift section's (a second would replace it)",
    'trapcontrol': "the trap check sees a second trap written as `true; trap ...`, `x && trap - EXIT` or `( trap ... )`",
    'sortBp': 'a baseline sort that writes 2 rows then exits 2: FAIL on the status, not a count of the short index',
    'sortLp': 'a live-index sort that writes 2 rows then exits 2: FAIL on the status, not a count of the short index',
}
MUTATIONS: dict = {}
MEAS = None      # an expected red set not yet pinned: main() prints the measured one and fails


def mut(label, old, new, names, expect):
    """names: the cases this guard exists for, which must go red. expect: the exact set that goes
    red (the guard's neighbours included), pinned so a case that stops detecting is a failure."""
    MUTATIONS[label] = (old, new, {CASE[n] for n in names}, None if expect is None else {CASE[n] for n in expect})


SB, SL = '[ "$SORT_RC_B" != 0 ]', '[ "$SORT_RC_L" != 0 ]'
mut('IDENTITY (no change - the harness control)', 'DRIFT_TMP="$(mktemp -d)" ||', 'DRIFT_TMP="$(mktemp -d)" ||', [], [])
mut('sort guard ignores the baseline sort', f'if {SB} || {SL}; then', f'if {SL}; then', ['sortB', 'sortBp'], ['sortB', 'sortBp'])
mut('sort guard ignores the live-index sort', f'if {SB} || {SL}; then', f'if {SB}; then', ['sortL', 'sortLp'], ['sortL', 'sortLp'])
mut('sort guard removed (the original false green)', f'if {SB} || {SL}; then', 'if false; then', ['sortB', 'sortL', 'sortBoth', 'sortBp', 'sortLp'], ['sortB', 'sortL', 'sortBoth', 'sortBp', 'sortLp'])
mut('Common diff status >= 2 not read', '-ge 2 ]; then\n        fail "asset drift (Common): diff', '-ge 3 ]; then\n        fail "asset drift (Common): diff', ['diffC'], ['diffC'])
mut('Server diff status >= 2 not read', '-ge 2 ]; then\n        fail "asset drift (Server/Cosmetics): diff', '-ge 3 ]; then\n        fail "asset drift (Server/Cosmetics): diff', ['diffS'], ['diffS'])
mut('Common count status >= 2 not read', '-ge 2 ]; then\n          fail "asset drift (Common): counting', '-ge 3 ]; then\n          fail "asset drift (Common): counting', ['grepC'], ['grepC'])
mut('Server count status >= 2 not read', '-ge 2 ]; then\n          fail "asset drift (Server/Cosmetics): counting', '-ge 3 ]; then\n          fail "asset drift (Server/Cosmetics): counting', ['grepS'], ['grepS'])
mut('hash script status not read', 'if [ "$HASH_RC" != 0 ]; then', 'if false; then', ['hash123', 'hash1', 'hashsort'], ['hash123', 'hash1', 'hashsort', 'both'])
mut('mktemp failure not read', 'if [ -z "$DRIFT_TMP" ]; then', 'if false; then', ['mktemp'], ['mktemp'])
mut('sort failure is a WARN, not a FAIL', 'fail "asset drift (Common): could not sort', 'warn "asset drift (Common): could not sort', ['sortB', 'sortL', 'sortBoth', 'sortBp', 'sortLp'], ['sortB', 'sortL', 'sortBoth', 'sortBp', 'sortLp', 'both'])
mut('hash failure is a WARN, not a FAIL', 'fail "asset drift (Server/Cosmetics): hash-server-assets.sh exited', 'warn "asset drift (Server/Cosmetics): hash-server-assets.sh exited', ['hash123', 'hash1', 'hashsort'], ['hash123', 'hash1', 'hashsort', 'both'])
mut('Common live denominator counts the baseline', 'compared with $N_LIVE live row(s)', 'compared with $N_BASE live row(s)', ['drift'], ['drift', 'dose1', 'dose3'])
mut('Server denominator counts the baseline', 'compared with $N_LIVE row(s) hashed', 'compared with $N_BASE row(s) hashed', ['drift'], ['drift', 'dose1', 'dose3'])
mut('Common denominator not printed', 'info "Common index:', ': "Common index:', ['healthy'], ['healthy', 'drift', 'dose1', 'dose3', 'skipS', 'skipSB'])
mut('Server denominator not printed', 'info "Server/Cosmetics index:', ': "Server/Cosmetics index:', ['healthy'], ['healthy', 'drift', 'dose1', 'dose3', 'skipC', 'skipCL'])
mut('Common skip WARN dropped', 'warn "skipped (missing baseline or live index)"', ': "skipped"', ['skipC'], ['skipC', 'skipCL'])
mut('Server skip WARN dropped', 'warn "Server-assets drift skipped (missing ServerAssetsIndex.hashes baseline or extracted Server/)"', ': "skipped"', ['skipS'], ['skipS', 'skipSB'])

mut('Common guard ignores an empty live index', 'if [ "$N_BASE" -eq 0 ] || [ "$N_LIVE" -eq 0 ]; then\n        fail "asset drift (Common)',
    'if [ "$N_BASE" -eq 0 ]; then\n        fail "asset drift (Common)', ['zeroCL'], ['zeroCL'])
mut('Common guard ignores an empty baseline', 'if [ "$N_BASE" -eq 0 ] || [ "$N_LIVE" -eq 0 ]; then\n        fail "asset drift (Common)',
    'if [ "$N_LIVE" -eq 0 ]; then\n        fail "asset drift (Common)', ['zeroCB'], ['zeroCB'])
mut('Server guard ignores an empty generated index', 'if [ "$N_BASE" -eq 0 ] || [ "$N_LIVE" -eq 0 ]; then\n        fail "asset drift (Server/Cosmetics)',
    'if [ "$N_BASE" -eq 0 ]; then\n        fail "asset drift (Server/Cosmetics)', ['zeroSH'], ['zeroSH'])
mut('Server guard ignores an empty baseline', 'if [ "$N_BASE" -eq 0 ] || [ "$N_LIVE" -eq 0 ]; then\n        fail "asset drift (Server/Cosmetics)',
    'if [ "$N_LIVE" -eq 0 ]; then\n        fail "asset drift (Server/Cosmetics)', ['zeroSB'], ['zeroSB'])
mut('EXIT trap removed', "trap 'rm -rf \"${DRIFT_TMP:-}\"' EXIT\n", '', ['early'], ['early'])
mut('section-end rm -rf removed', '  rm -rf "$DRIFT_TMP"\n', '', ['healthy'], ['sortBp', 'sortLp', 'both', 'diffC', 'diffS', 'dose1', 'dose3', 'drift', 'grepC', 'grepS', 'hash1', 'hash123', 'hashsort', 'healthy', 'skipC', 'skipCL', 'skipS', 'skipSB', 'sortB', 'sortBoth', 'sortL', 'zeroCB', 'zeroCL', 'zeroSB', 'zeroSH'])
mut('DRIFT_TMP not cleared after the section-end rm', '  DRIFT_TMP=""      # the EXIT cleanup must not act on a path that is already gone\n', '', ['healthy'],
    ['both', 'diffC', 'diffS', 'dose1', 'dose3', 'drift', 'grepC', 'grepS', 'hash1', 'hash123', 'hashsort', 'healthy', 'skipC', 'skipCL', 'skipS', 'skipSB', 'sortB', 'sortBoth', 'sortBp', 'sortL', 'sortLp', 'zeroCB', 'zeroCL', 'zeroSB', 'zeroSH'])
mut('Common condition ignores the live index', '[ -f maintenance/baseline/CommonAssetsIndex.hashes ] && [ -f "$ASSETS/CommonAssetsIndex.hashes" ]',
    '[ -f maintenance/baseline/CommonAssetsIndex.hashes ]', ['skipCL'], ['skipCL'])
mut('Common condition ignores the baseline', '[ -f maintenance/baseline/CommonAssetsIndex.hashes ] && [ -f "$ASSETS/CommonAssetsIndex.hashes" ]',
    '[ -f "$ASSETS/CommonAssetsIndex.hashes" ]', ['skipC'], ['skipC'])
mut('Server condition ignores the baseline', '[ -f maintenance/baseline/ServerAssetsIndex.hashes ] && [ -d "$ASSETS/Server" ]',
    '[ -d "$ASSETS/Server" ]', ['skipSB'], ['skipSB'])
mut('Server condition ignores Server/', '[ -f maintenance/baseline/ServerAssetsIndex.hashes ] && [ -d "$ASSETS/Server" ]',
    '[ -f maintenance/baseline/ServerAssetsIndex.hashes ]', ['skipS'], ['skipS'])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    text = section_text(VERIFY.read_text())
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        work = pathlib.Path(td)
        tpl = work / 'tpl'
        build_template(tpl)
        if negative_control(tpl, work):
            return 1
        (work / 'base').mkdir()
        res = all_cases(text, tpl, work / 'base')
        if len(res) < MIN_CASES:
            print(f'  FAIL  {len(res)} case(s) ran, floor is {MIN_CASES}. A fixture that examines nothing '
                  f'reports the same thing as one that passes.')
            return 1
        fails = {k: v for k, v in res.items() if v}
        for label in res:
            if a.verbose and not res[label]:
                print(f'  ok   {label}')
        print(f'\nFIXTURE {len(res)} case(s): {len(res) - len(fails)} passed, {len(fails)} failed')
        for k, v in fails.items():
            print(f'  FAIL {k}: ' + '; '.join(v))
        rc = 1 if fails else 0
        if not a.mutations:
            return rc
        if len(MUTATIONS) < MIN_MUTATIONS:
            print(f'  FAIL  {len(MUTATIONS)} mutation(s) defined, floor is {MIN_MUTATIONS}.')
            return 1
        if not any(k.startswith('IDENTITY') for k in MUTATIONS):
            print('  FAIL  no IDENTITY control in MUTATIONS')
            return 1
        print(f'\nMUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
        for k, (label, (old, new, names, expect)) in enumerate(MUTATIONS.items()):
            n = text.count(old)
            if n != 1:
                print(f'  FAIL {label}: the anchor occurs {n} time(s) in the section, not once')
                rc = 1
                continue
            mdir = work / f'm{k}'
            mdir.mkdir()
            mres = all_cases(text.replace(old, new, 1), tpl, mdir)
            red = {c for c, v in mres.items() if v}
            if label.startswith('IDENTITY') and red:
                print(f'  FAIL {label}: the control reddened {len(red)} case(s); the harness is broken. Aborting.')
                for x in sorted(red):
                    print(f'         {x}')
                return 1
            if names - red:
                rc = 1
                print(f'  FAIL {label}: the case this defect belongs to stayed GREEN')
                for x in sorted(names - red):
                    print(f'         {x}')
                continue
            if expect is None:
                rc = 1
                print(f'  MEASURED {label}: ' + repr(sorted(k for k, c in CASE.items() if c in red)))
            elif red == expect:
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
