#!/usr/bin/env python3
"""
Run verify-docs.sh's OWN "The double-run table matches the population and the source" section on
stub probe scripts under injected failures, and (with --mutations) verify that each guard in it is
the thing that catches its failure.

WHY THE SECTION'S TEXT AND NOT A COPY OF ITS LOGIC. Same reason as check-asset-drift-fixture.py: a
helper with a fixture of its own tests the helper and leaves the wrapper that reads the helper's
status untested. The section is cut out of verify-docs.sh (from its `section "[HARD] The double-run
table` line to the next `# =====` line) and run under the real section()/pass()/fail()/warn()/info()
definitions. If the section is renamed, the anchor moves with it (the cut asserts it finds one).

WHAT IT STANDS ON. The section reads DR_DIR, DR_PAGE and DR_BUILD from the environment (defaults:
the real probe directory, the real page, 0.7.2), so this fixture points them at a temp tree whose
four scripts (usage.py, census.py, census-test.py, usage-test.py) are stubs (see PY_SHIM: a bash
function behind a `python3` shim, so a case costs no interpreter start for them). A stub prints a
file (name.out, with @SRC@ and @ASSETS@ replaced by the --src and --assets it was given, so the
cache path changes between runs exactly as under HYTALE_ASSETS), writes name.err to stderr, writes
name.tables to its --tables file, creates the work dir it is given, logs its argv, and exits with
name.rc. The snapshots are the same text with the cache path of the real ones. The real-tree run
(the real probes, the real page) is verify-docs.sh's own.

THE NEGATIVE CONTROL. The defect this section exists for is that a stale table passes. The first
thing run is therefore the healthy tree with ONE row of the page changed: the section must FAIL it.
A section that passes a stale page has nothing to say about anything else, and the run is refused.

Every case runs in a temp root of its own with a TMPDIR of its own and asserts that nothing is left
in it and that the section cleared DR_TMP. Cases and mutations run on a thread pool: each is a bash
process and a few python starts, about 0.15 s, and the mutation pass is cases x guards.

Usage:
  python3 maintenance/scripts/check-double-run-fixture.py [-v]
  python3 maintenance/scripts/check-double-run-fixture.py --mutations [-v]
"""
from __future__ import annotations
import argparse, concurrent.futures, os, pathlib, re, shutil, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / 'verify-docs.sh'
ANCHOR = 'section "[HARD] The double-run table matches the population and the source"'
REAL_PY = shutil.which('python3') or sys.exit('python3 not found on PATH')
ANSI = re.compile(r'\x1b\[[0-9;]*m')

# FLOORS, as in the other fixtures: lowering one needs a reason in the commit message.
MIN_CASES = 54
MIN_MUTATIONS = 73

BUILD = '9.9.9'
SRC_ALT, ASSETS_ALT = 'cache-src', 'cache-assets'      # the stub caches: not the snapshots' ~/.cache paths


def section_text(src: str) -> str:
    n = src.count(ANCHOR)
    if n != 1:
        raise SystemExit(f'FAIL  {ANCHOR!r} occurs {n} time(s) in verify-docs.sh, not once - '
                         f'the section was renamed or duplicated; move this anchor with it')
    s = src.index(ANCHOR)
    return src[s:src.index('\n# =====', s)] + '\n'


def prelude() -> str:
    """`set -u` and the real HARD_FAILS/section/pass/fail/warn/info definitions of verify-docs.sh, verbatim."""
    v = VERIFY.read_text()
    assert v.count('\nset -u\n') == 1, 'verify-docs.sh no longer has exactly one `set -u` line'
    a = v.index('\nHARD_FAILS=0\n') + 1
    i = v.index('\ninfo()', a) + 1
    return 'set -u\n' + v[a:v.index('\n', i) + 1]


def floors(text: str) -> tuple[int, int]:
    m = re.search(r'^DR_MIN_CT=(\d+); DR_MIN_UT=(\d+)$', text, re.M)
    assert m, 'the section no longer sets DR_MIN_CT and DR_MIN_UT on one line'
    return int(m.group(1)), int(m.group(2))


# The four probe scripts are stubs, and a stub is a bash function in a `python3` shim on PATH, not a python file: the
# mutation pass runs every case once per guard, and four interpreter starts per case cost more than the whole budget.
# The shim answers `python3 -I <probe dir>/<name>.py ARGS` for the four names and passes everything else (the section's
# own inline `python3 -I - ...` page comparison) to the real python. A stub prints name.out with @SRC@ and @ASSETS@
# replaced by the --src and --assets it was given, writes name.err to stderr, writes name.tables to its --tables
# file, creates the work dir it is given (the -test ones), logs its argv to argv.log, and exits with name.rc.
PY_SHIM = '''#!/usr/bin/env bash
if [ "${1:-}" = "-I" ] && [ "${2:-}" != "-" ]; then
  script="$2"; shift 2
  case "$script" in
    */usage.py|*/census.py|*/census-test.py|*/usage-test.py)
      here="$(dirname "$script")"; name="$(basename "$script" .py)"
      echo "$name $*" >> "$here/argv.log"
      src=""; assets=""; tables=""; prev=""
      for a in "$@"; do
        case "$prev" in --src) src="$a" ;; --assets) assets="$a" ;; --tables) tables="$a" ;; esac
        prev="$a"
      done
      [ -f "$here/$name.out" ] && sed -e "s|@SRC@|$src|g" -e "s|@ASSETS@|$assets|g" "$here/$name.out"
      [ -f "$here/$name.err" ] && cat "$here/$name.err" >&2
      if [ "$name" = usage ] && [ -n "$tables" ] && [ -f "$here/usage.tables" ]; then cat "$here/usage.tables" > "$tables"; fi
      case "$name" in *-test) mkdir -p "$1"; echo x > "$1/payload" ;; esac
      if [ -f "$here/$name.rc" ]; then exit "$(cat "$here/$name.rc")"; fi
      exit 0 ;;
  esac
  set -- -I "$script" "$@"
fi
exec @REAL@ "$@"
'''

CENSUS = '''build: version=9.9.9 jar_sha=0123456789abcdef src=ok src_files=3 decompiler=jar fedcba
source: @SRC@
DENOMINATOR
  registry: Foo.CODEC (closed, key "Type")
  names registered (miner sites): 3; distinct names: 3
  names whose class was parsed: 3; names whose class could not be parsed: 0
  distinct classes: 3; classes carrying more than one name: 0
  classes whose superclass chain did not reach Interaction: 0

PER CLASS
Alpha
    sim  firstRun
'''
USAGE = '''assets: @ASSETS@/Server
registered interaction types: 3
seeds: NPC 5 files; encounter 1; ability 2
   run-reached with the routes of 2b added: 2 of 3 types; ModifyInventory 1 objects, ChangeStat 0
6. VERDICT TABLE (verdict-table.tsv): 2 rows for 2 run-reached types; outcomes once 1, reads 1; basis read 2
   unknown: 0 (limit 5); 0 problem(s)
   wrote the page tables to tables13b.md

registered types never reached by either population: 1 of 3
'''
HEAD = '| Type | Objects (runs on) | Basis | Write | Deciding line and why |\n|------|-------------------|-------|-------|-----------------------|\n'
ROW_A = '| `Alpha` | 4 (NPC 4) | read | none | `A.java:1` first |\n'
ROW_A2 = '| `Alpha2` | 3 (NPC 3) | read | none | `A2.java:9` same table |\n'
ROW_B = '| `Beta` | 2 (NPC 2) | read | none | `B.java:2` second |\n'
TABLES = f'### Once: the simulation pass does nothing (2)\n\n{HEAD}{ROW_A}{ROW_A2}\n### Reads only (1)\n\n{HEAD}{ROW_B}'
# the real page: a fenced START and END line before the real START (fences must be skipped), then the span, then END
PAGE_HEAD = ('# Page\n\nintro\n\n```\n### The population (counted)\n### Outcomes that depend on a field (fenced)\n```\n\n'
             '### The population (counted)\n\ncounted text\n\nVerdicts: **x measured**.\n\n')
PAGE_TAIL = '\n### Outcomes that depend on a field (counted over the run-reached objects)\n\n| x |\n\n### Gotchas\n\ntext\n'
PAGE = PAGE_HEAD + TABLES + PAGE_TAIL


def build_template(tpl: pathlib.Path, ct: int, ut: int):
    p = tpl / 'probe'
    p.mkdir(parents=True)
    (p / 'census.out').write_text(CENSUS)
    (p / 'usage.out').write_text(USAGE)
    (p / 'usage.tables').write_text(TABLES)
    (p / 'census-test.out').write_text(''.join(f'PASS  case {i}\n' for i in range(ct)) + '---- 0 failed\n')
    (p / 'usage-test.out').write_text(''.join(f'PASS  check {i}\n' for i in range(ut)) + '---- 0 failed\n')
    (tpl / 'page.md').write_text(PAGE)
    (tpl / SRC_ALT).mkdir()
    (tpl / ASSETS_ALT).mkdir()


def snapshots(probe: pathlib.Path):
    """The snapshots are the live outputs with the real caches' paths, as the committed ones are."""
    for n, home in (('census', ('@SRC@', '~/.cache/hytale-jar/src')), ('usage', ('@ASSETS@', '~/.cache/hytale-assets'))):
        (probe / f'{n}-{BUILD}.txt').write_text((probe / f'{n}.out').read_text().replace(*home))


DIFF_SHIM = '#!/usr/bin/env bash\necho "diff: shim: injected failure" >&2\nexit 2\n'


def run_section(text: str, tpl: pathlib.Path, work: pathlib.Path, name: str, *, put=None, edit=None, edit_live=None,
                edit_snap=None, rm=(), rc=None, err=None, page=None, no_src=False, no_assets=False, tmpdir=None,
                diff_shim=False, extra_env=None):
    """Run `text` in a copy of the template. put: {file in probe/: text}. edit: {file: fn(text)} applied to the
    live output AND its snapshot; edit_live / edit_snap: to one side only. Returns (status, output, argv log)."""
    root = work / name
    shutil.copytree(tpl, root)
    probe = root / 'probe'
    for f, fn in (edit or {}).items():
        (probe / f).write_text(fn((probe / f).read_text()))
    for f, t in (put or {}).items():
        (probe / f).write_text(t)
    snapshots(probe)
    for f, fn in (edit_snap or {}).items():
        sp = probe / f'{f}-{BUILD}.txt'
        sp.write_text(fn(sp.read_text()))
    for f, fn in (edit_live or {}).items():
        (probe / f'{f}.out').write_text(fn((probe / f'{f}.out').read_text()))
    for f in rm:
        (probe / f).unlink()
    for n_, v in (rc or {}).items():
        (probe / f'{n_}.rc').write_text(str(v))
    for n_, v in (err or {}).items():
        (probe / f'{n_}.err').write_text(v)
    if page is not None:
        (root / 'page.md').write_text(page)
    if no_src:
        shutil.rmtree(root / SRC_ALT)
    if no_assets:
        shutil.rmtree(root / ASSETS_ALT)
    tmp = root / 'tmp'
    tmp.mkdir()
    shims = root / 'shims'
    shims.mkdir()
    (shims / 'python3').write_text(PY_SHIM.replace('@REAL@', REAL_PY))
    (shims / 'python3').chmod(0o755)
    if diff_shim:
        (shims / 'diff').write_text(DIFF_SHIM)
        (shims / 'diff').chmod(0o755)
    env = dict(os.environ, PATH=f'{shims}{os.pathsep}{os.environ["PATH"]}', TMPDIR=tmpdir or str(tmp), PYTHONDONTWRITEBYTECODE='1',
               DR_DIR='probe', DR_PAGE='page.md', DR_BUILD=BUILD)
    env.update(extra_env or {})
    script = (prelude() + f'ASSETS={str(root / ASSETS_ALT)!r}\nSRC_CACHE={str(root / SRC_ALT)!r}\n' + text
              + 'echo "DR_TMP_AFTER_SECTION=$([ -d "${DR_TMP:-}" ] && echo present || echo gone)"\n'
              + 'echo "DR_TMP_CLEARED=$([ -z "${DR_TMP:-}" ] && echo yes || echo no)"\n'
              + 'echo "HARD_FAILS=$HARD_FAILS"\n')
    p = subprocess.run(['bash', '-c', script], capture_output=True, text=True, cwd=root, env=env)
    out = ANSI.sub('', p.stdout + p.stderr)
    log = (probe / 'argv.log').read_text() if (probe / 'argv.log').exists() else ''
    # the temp paths are reported as @ROOT@ and @TMP@, so an expected line need not know them
    left = len(list(tmp.iterdir()))
    out = re.sub(re.escape(str(tmp)) + r'/tmp\.[A-Za-z0-9]+', '@TMP@', out).replace(str(root), '@ROOT@')
    log = re.sub(re.escape(str(tmp)) + r'/tmp\.[A-Za-z0-9]+', '@TMP@', log).replace(str(root), '@ROOT@')
    return p.returncode, out + f'TMP_LEFT={left}\n', log


def hard(out: str) -> int:
    m = re.findall(r'^HARD_FAILS=(\d+)$', out, re.M)
    return int(m[-1]) if m else -1


def body(out: str) -> list[str]:
    return [l.strip() for l in out.splitlines()
            if l.strip() and not l.startswith(('HARD_FAILS=', '== ', 'DR_TMP_AFTER_SECTION=', 'DR_TMP_CLEARED=', 'TMP_LEFT='))]


def clean_lines(ct: int, ut: int) -> list[str]:
    return [
        'INFO  page: 2 tables, 3 rows (7 table lines) of page.md equal the tables usage.py generates',
        'INFO  census.py: 3 name(s), 3 class(es); stdout equals census-9.9.9.txt (11 lines compared, the source: line dropped)',
        'INFO  usage.py: 3 registered type(s), 2 run-reached, 2 table row(s), 0 unknown (limit 5), 0 problem(s); stdout equals usage-9.9.9.txt (8 lines compared, the assets: line dropped)',
        f'INFO  census-test.py: {ct} PASS (floor {ct}), ---- 0 failed; usage-test.py: {ut} PASS (floor {ut}), ---- 0 failed',
        'PASS  the double-run table holds: 2 run-reached type(s) in 2 row(s), the page tables equal the generated ones, both snapshots equal, both controls green',
    ]


def with_page(tables: str) -> str:
    return PAGE_HEAD + tables + PAGE_TAIL


def trap_exit_problems(text: str) -> list[str]:
    """The section must hold no `trap` and no `exit`: the asset-drift section owns the script's only EXIT hook, and an
    exit inside a section ends verify-docs.sh before its summary. Searched on every line that is not a comment, anywhere on it;
    `sys.exit` in the section's inline python is not a shell exit and is not matched."""
    lines = [l for l in text.splitlines() if re.search(r'(?<![.\w])(trap|exit)\b', l) and not l.lstrip().startswith('#')]
    return [f'non-comment lines naming trap or exit: {lines}'] if lines else []


def all_cases(text: str, tpl: pathlib.Path, work: pathlib.Path, pool) -> dict[str, list[str]]:
    ct, ut = floors(text)
    CLEAN = clean_lines(ct, ut)
    jobs: list = []

    def case(tag, label, kw=None, *, hf, exact=None, must=(), must_not=(), argv=None, ran=True, cleaned=True):
        """Queue one run, keyed by its tag (the mutation table names tags). hf: HARD_FAILS wanted. ran: the stubs were run (their argv log exists). A run that
        FAILs must not print PASS."""
        n = len(jobs)
        fut = pool.submit(run_section, text, tpl, work, f'c{n}', **(kw or {}))
        assert tag not in LABELS or LABELS[tag] == label, tag
        LABELS[tag] = label
        jobs.append((tag, fut, hf, exact, must, must_not, argv, ran, cleaned))

    # ---- the negative control comes first and is judged first (see main): the page with one row changed
    case('neg', 'NEGATIVE CONTROL: a page with one row of its tables changed is a FAIL (a section that passes a stale page says nothing)',
         dict(page=with_page(TABLES.replace('first', 'FIRST'))), hf=1, must=('FAIL  page.md does not match the tables usage.py generates',))
    case('healthy', 'healthy: every step prints its denominator; the cache paths differ from the snapshots\' and the source:/assets: lines are dropped',
         hf=0, exact=CLEAN, argv=[
             'usage --assets @ROOT@/cache-assets --src @ROOT@/cache-src --tables @TMP@/tables13b.md',
             'census --src @ROOT@/cache-src',
             'census-test @TMP@/ct --src @ROOT@/cache-src',
             'usage-test @TMP@/ut --assets @ROOT@/cache-assets --src @ROOT@/cache-src'])
    # ---- missing inputs (R2): one WARN and no step runs
    case('nosrc', 'a missing decompiled source cache is one WARN and nothing runs', dict(no_src=True), hf=0, ran=False,
         exact=['WARN  skipped (no decompiled source cache at @ROOT@/cache-src — build-jar-cache.sh)'])
    case('noassets', 'a missing asset cache is one WARN and nothing runs', dict(no_assets=True), hf=0, ran=False,
         exact=['WARN  skipped (no asset cache)'])
    case('mktemp', 'mktemp fails: its own FAIL and no step runs', dict(tmpdir='/nonexistent-double-run-tmp'), hf=1, ran=False, cleaned=False,
         must=('FAIL  double-run: could not create a temporary directory (mktemp -d failed',))

    # ---- usage.py: exit status and summary line (R1)
    prob = lambda t: t.replace('   unknown: 0 (limit 5); 0 problem(s)\n', '   PROBLEM  verdict-table.tsv:3: Foo has no row\n   unknown: 0 (limit 5); 1 problem(s)\n')
    case('u_rc1prob', 'usage.py exits 1 on a table problem: FAIL printing the PROBLEM line and the stderr tail',
         dict(edit={'usage.out': prob}, rc={'usage': 1}, err={'usage': 'boom-line\n'}), hf=1,
         must=('FAIL  usage.py exited 1', '    PROBLEM  verdict-table.tsv:3: Foo has no row', '    stderr: boom-line'), must_not=('stdout differs',))
    case('u_rc1none', 'usage.py exits 1 with no output (no Server/NPC, an empty seed set, a crash): FAIL printing stderr; the tables are not there either',
         dict(put={'usage.out': ''}, rm=['usage.tables'], rc={'usage': 1}, err={'usage': 'FAIL  no ~/.cache/hytale-assets/Server/NPC\n'}), hf=2,
         must=('FAIL  usage.py exited 1', '    stderr: FAIL  no ~/.cache/hytale-assets/Server/NPC', 'FAIL  the page tables were not compared: usage.py wrote no @TMP@/tables13b.md'),
         must_not=('stdout differs',))
    case('u_rc2', 'usage.py exits 2 (a refused --tables): FAIL printing stderr',
         dict(put={'usage.out': ''}, rm=['usage.tables'], rc={'usage': 2}, err={'usage': 'FAIL  --tables x resolves to y, inside the repository\n'}), hf=2,
         must=('FAIL  usage.py exited 2', '    stderr: FAIL  --tables x resolves to y, inside the repository', 'FAIL  the page tables were not compared: usage.py wrote no @TMP@/tables13b.md'))
    no_unk = lambda t: t.replace('   unknown: 0 (limit 5); 0 problem(s)\n', '')
    case('u_nosum', 'usage.py exits 0 but prints no unknown/problem summary line: FAIL, "it ran, or did it?"',
         dict(edit={'usage.out': no_unk}), hf=1, must=("FAIL  usage.py exited 0 but printed the line 'unknown: N (limit 5); 0 problem(s)' 0 time(s)",),
         must_not=('stdout differs',))
    one_prob = lambda t: t.replace('0 problem(s)', '1 problem(s)')
    case('u_onep', 'usage.py exits 0 but its summary line counts 1 problem: FAIL (the exit status is not the only witness)',
         dict(edit={'usage.out': one_prob}), hf=1, must=("FAIL  usage.py exited 0 but printed the line 'unknown: N (limit 5); 0 problem(s)' 0 time(s)",),
         must_not=('stdout differs',))
    twice = lambda t: t.replace('   unknown: 0 (limit 5); 0 problem(s)\n', '   unknown: 0 (limit 5); 0 problem(s)\n' * 2)
    case('u_twice', 'usage.py prints its summary line twice: FAIL (exactly once)', dict(edit={'usage.out': twice}), hf=1,
         must=("printed the line 'unknown: N (limit 5); 0 problem(s)' 2 time(s)",))
    no_run = lambda t: t.replace('   run-reached with the routes of 2b added', '   run-reached WITHOUT the routes of 2b added')
    case('u_norun', 'usage.py does not print the run-reached figure: FAIL naming the missing denominator',
         dict(edit={'usage.out': no_run}), hf=1, must=("did not print its population figures once each (registered types '3', run-reached '', verdict table rows '2')",))
    rows3 = lambda t: t.replace('2 rows for 2 run-reached', '3 rows for 2 run-reached')
    case('u_rows', 'the verdict table has more rows than there are run-reached types: FAIL', dict(edit={'usage.out': rows3}), hf=1,
         must=('FAIL  usage.py: 3 verdict table row(s) for 2 run-reached type(s)',))
    zero = lambda t: t.replace('2 of 3 types;', '0 of 3 types;').replace('2 rows for 2 run-reached', '0 rows for 0 run-reached')
    case('u_zero', 'a population of 0 run-reached types is not a population: FAIL', dict(edit={'usage.out': zero}), hf=1,
         must=('FAIL  usage.py: 0 verdict table row(s) for 0 run-reached type(s)',))

    # ---- the snapshots (R0)
    case('s_census', 'a census line other than source: differs from the snapshot: FAIL with the diff',
         dict(edit_live={'census': lambda t: t.replace('jar_sha=0123456789abcdef', 'jar_sha=ffffffffffffffff')}), hf=1,
         must=('FAIL  census: stdout differs from probe/census-9.9.9.txt', '-build: version=9.9.9 jar_sha=0123456789abcdef', '+build: version=9.9.9 jar_sha=ffffffffffffffff'))
    case('s_usage', 'a usage line other than assets: differs from the snapshot: FAIL with the diff',
         dict(edit_live={'usage': lambda t: t.replace('seeds: NPC 5 files', 'seeds: NPC 6 files')}), hf=1,
         must=('FAIL  usage: stdout differs from probe/usage-9.9.9.txt', '-seeds: NPC 5 files', '+seeds: NPC 6 files'))
    case('s_wrote', 'the wrote-the-page-tables line differs from the snapshot (another file name): FAIL, it is not excepted',
         dict(edit_live={'usage': lambda t: t.replace('to tables13b.md', 'to other.md')}), hf=1,
         must=('FAIL  usage: stdout differs from probe/usage-9.9.9.txt', '+   wrote the page tables to other.md'))
    case('s_snapx', 'a census snapshot line that live no longer prints: FAIL (the comparison runs both ways)',
         dict(edit_snap={'census': lambda t: t + 'extra snapshot line\n'}), hf=1, must=('FAIL  census: stdout differs', '-extra snapshot line'))
    case('s_nocsnap', 'a missing census snapshot is a FAIL naming it', dict(rm=['census-9.9.9.txt']), hf=1,
         must=('FAIL  census: the snapshot probe/census-9.9.9.txt does not exist',))
    case('s_nousnap', 'a missing usage snapshot is a FAIL naming it', dict(rm=['usage-9.9.9.txt']), hf=1,
         must=('FAIL  usage: the snapshot probe/usage-9.9.9.txt does not exist',))
    case('s_nosource', 'the census prints no source: line: FAIL (the exception must match exactly once)',
         dict(edit_live={'census': lambda t: t.replace('source: @SRC@\n', '')}), hf=1,
         must=('FAIL  census: the line /^source: / occurs 0 time(s) in the live output and 1 in probe/census-9.9.9.txt',))
    case('s_noassetssnap', 'the usage snapshot has no assets: line: FAIL', dict(edit_snap={'usage': lambda t: re.sub(r'^assets: .*\n', '', t)}), hf=1,
         must=('FAIL  usage: the line /^assets: / occurs 1 time(s) in the live output and 0 in probe/usage-9.9.9.txt',))
    case('s_twosrc', 'the census prints two source: lines: FAIL', dict(edit_live={'census': lambda t: t.replace('source: @SRC@\n', 'source: @SRC@\nsource: again\n')}), hf=1,
         must=('FAIL  census: the line /^source: / occurs 2 time(s) in the live output and 1 in',))
    case('s_diff2', 'diff exits 2 on the snapshots: FAIL naming its status, once per snapshot', dict(diff_shim=True), hf=2,
         must=('FAIL  census: diff of the output and probe/census-9.9.9.txt exited 2', 'FAIL  usage: diff of the output and probe/usage-9.9.9.txt exited 2'))

    # ---- census.py
    case('c_rc1', 'census.py exits 1: FAIL printing stderr', dict(rc={'census': 1}, err={'census': 'census-boom\n'}), hf=1,
         must=('FAIL  census.py exited 1:', '    stderr: census-boom'))
    case('c_nodenom', 'census.py exits 0 but prints no denominator: FAIL, "it ran, or did it?"',
         dict(edit={'census.out': lambda t: t.replace('  names registered (miner sites): 3; distinct names: 3\n', '')}), hf=1,
         must=('FAIL  census.py exited 0 but printed its denominator lines 0 and 1 time(s)',))
    case('c_zeronames', 'census.py reports 0 names: FAIL, not a comparison of two empty censuses',
         dict(edit={'census.out': lambda t: t.replace('names registered (miner sites): 3; distinct names: 3', 'names registered (miner sites): 0; distinct names: 0')}), hf=1,
         must=('FAIL  census.py: 0 name(s) in 3 class(es) - a census that visited nothing',))
    case('c_zeroclasses', 'census.py reports 0 classes: FAIL',
         dict(edit={'census.out': lambda t: t.replace('distinct classes: 3;', 'distinct classes: 0;')}), hf=1,
         must=('FAIL  census.py: 3 name(s) in 0 class(es) - a census that visited nothing',))
    case('c_noclasses', 'census.py exits 0 but prints no classes line: FAIL naming which denominator is missing',
         dict(edit={'census.out': lambda t: t.replace('  distinct classes: 3; classes carrying more than one name: 0\n', '')}), hf=1,
         must=('FAIL  census.py exited 0 but printed its denominator lines 1 and 0 time(s)',))

    # the diff is capped at 40 lines and says how long it was
    many = lambda t: t + ''.join(f'extra-line-{i:02d}\n' for i in range(60))
    case('s_bigdiff', 'a snapshot that differs in 60 lines prints the first 40 diff lines and the count of all of them',
         dict(edit_live={'census': many}), hf=1, must=('FAIL  census: stdout differs from probe/census-9.9.9.txt (66 diff lines, the first 40;', '+extra-line-05'),
         must_not=('+extra-line-45',))
    # ---- the page (R4): the span between the anchors, byte for byte
    lines = TABLES.split('\n')
    def swap(a, b):
        t = TABLES
        return t.replace(a, '@@').replace(b, a).replace('@@', b)
    for tag, label, tabs in (
            ('p_extra', 'a stale extra row on the page', TABLES.replace(ROW_B, ROW_B + '| `Gamma` | 1 (NPC 1) | read | none | `G.java:1` stale |\n')),
            ('p_removed', 'a row removed from the page', TABLES.replace(ROW_A2, '')),
            ('p_reorder', 'two rows reordered on the page', swap(ROW_A, ROW_A2)),
            ('p_otherhead', 'a row filed under another heading on the page', TABLES.replace(ROW_A2, '').replace(ROW_B, ROW_A2 + ROW_B)),
            ('p_newhead', 'a heading added inside the span on the page', TABLES + '\n### Not classified (0)\n\n' + HEAD)):
        case(tag, f'{label}: FAIL with the diff', dict(page=with_page(tabs)), hf=1,
             must=('FAIL  page.md does not match the tables usage.py generates (compare status 1):', 'DIFF '))
    many_rows = ''.join(f'| `R{i:02d}` | 1 (NPC 1) | read | none | `R.java:{i}` stale |\n' for i in range(60))
    case('p_bigdiff', 'sixty stale rows on the page: FAIL with the first 40 diff lines and the count of all of them', dict(page=with_page(TABLES + many_rows)), hf=1,
         must=('DIFF 64 diff line(s) (the first 40;', 'R05'), must_not=('R50',))
    case('p_trailing', 'trailing blank lines after the last table differ: still equal (normalised)', dict(page=with_page(TABLES + '\n\n\n')), hf=0, exact=CLEAN)
    case('p_nostart', 'the start anchor is missing from the page: FAIL naming both counts', dict(page=PAGE.replace('### The population (counted)\n\ncounted text', 'x\n\ncounted text').replace('```\n### The population (counted)\n', '```\nx\n')),
         hf=1, must=('ANCHOR page.md: "### The population (counted)" occurs 0 time(s) and "### Outcomes that depend on a field" 1, wanted once each',))
    case('p_noend', 'the end anchor is missing from the page: FAIL', dict(page=PAGE.replace('\n### Outcomes that depend on a field (counted over', '\n### Other (counted over')),
         hf=1, must=('occurs 1 time(s) and "### Outcomes that depend on a field" 0, wanted once each',))
    case('p_dupstart', 'the start anchor occurs twice outside a fence: FAIL', dict(page=PAGE.replace('Verdicts: **x measured**.', '### The population (counted)\n')),
         hf=1, must=('occurs 2 time(s)',))
    case('p_nohead', 'no ### heading between the anchors: FAIL', dict(page=PAGE_HEAD + 'no tables\n' + PAGE_TAIL), hf=1,
         must=('ANCHOR page.md: no ### heading between "### The population (counted)" and "### Outcomes that depend on a field"',))
    case('p_emptygen', 'usage.py exits 0 and writes an empty tables file: FAIL, there is nothing to compare', dict(put={'usage.tables': ''}), hf=1,
         must=('EMPTY the generated tables hold 0 table(s) and 0 row(s): there is nothing to compare',))
    case('p_notables', 'usage.py exits 0 and writes no tables file: FAIL naming it', dict(rm=['usage.tables']), hf=1,
         must=('FAIL  the page tables were not compared: usage.py wrote no @TMP@/tables13b.md',))
    case('p_nopage', 'the page does not exist: FAIL with the python error', dict(extra_env={'DR_PAGE': 'no-such-page.md'}), hf=1,
         must=('FAIL  no-such-page.md does not match the tables usage.py generates (compare status 1):', 'FileNotFoundError'))

    # ---- the negative controls (R1's floors)
    case('t_ct1', 'census-test.py exits 1: FAIL printing its FAIL line and stderr',
         dict(edit={'census-test.out': lambda t: t.replace('---- 0 failed', 'FAIL  planted defect not seen\n---- 1 failed')}, rc={'census-test': 1}, err={'census-test': 'ct-boom\n'}),
         hf=1, must=('FAIL  census-test.py exited 1:', '    FAIL  planted defect not seen', '    stderr: ct-boom'))
    case('t_ut1', 'usage-test.py exits 1: FAIL', dict(rc={'usage-test': 1}), hf=1, must=('FAIL  usage-test.py exited 1:',))
    case('t_ctnosum', 'census-test.py exits 0 without a ---- 0 failed line: FAIL', dict(edit={'census-test.out': lambda t: t.replace('---- 0 failed\n', '')}), hf=1,
         must=("FAIL  census-test.py exited 0 but printed the line '---- 0 failed' 0 time(s)",))
    case('t_utwice', 'usage-test.py prints ---- 0 failed twice: FAIL (exactly once)', dict(edit={'usage-test.out': lambda t: t + '---- 0 failed\n'}), hf=1,
         must=("FAIL  usage-test.py exited 0 but printed the line '---- 0 failed' 2 time(s)",))
    case('t_ctfloor', 'census-test.py prints one PASS line fewer than its floor: FAIL', dict(edit={'census-test.out': lambda t: t.replace('PASS  case 0\n', '')}), hf=1,
         must=(f'FAIL  census-test.py printed {ct - 1} PASS line(s), the floor is {ct}',))
    case('t_utfloor', 'usage-test.py prints one PASS line fewer than its floor: FAIL', dict(edit={'usage-test.out': lambda t: t.replace('PASS  check 0\n', '')}), hf=1,
         must=(f'FAIL  usage-test.py printed {ut - 1} PASS line(s), the floor is {ut}',))
    case('t_both', 'both controls fail: two FAILs and no PASS', dict(rc={'census-test': 1, 'usage-test': 1}), hf=2,
         must=('FAIL  census-test.py exited 1:', 'FAIL  usage-test.py exited 1:'))

    # ---- everything fails at once: failures add up and no step is skipped by another's failure
    case('all3', 'usage.py and both controls fail: three FAILs, the census and the page are still compared (and pass)',
         dict(rc={'usage': 1, 'census-test': 1, 'usage-test': 1}), hf=3, must=('FAIL  usage.py exited 1', 'FAIL  census-test.py exited 1:', 'FAIL  usage-test.py exited 1:'),
         must_not=('FAIL  census:',))

    # collect: a run that fails must not print PASS, the temp dir must be gone
    res: dict[str, list[str]] = {}
    for tag, fut, hf, exact, must, must_not, argv, ran, cleaned in jobs:
        rc_, out, log = fut.result()
        pr = []
        if rc_ != 0:
            pr.append(f'harness exit {rc_}: {out[-300:]!r}')
        if hard(out) != hf:
            pr.append(f'HARD_FAILS {hard(out)}, wanted {hf}')
        if 'TMP_LEFT=0\n' not in out:
            pr.append(f'the temp dir was not removed: {re.findall("TMP_LEFT=.*", out)}')
        if cleaned and 'DR_TMP_AFTER_SECTION=gone' not in out:
            pr.append('the section left its temp dir in place when it ended')
        if cleaned and 'DR_TMP_CLEARED=yes' not in out:
            pr.append('the section left DR_TMP set to the removed path')
        if hf and '  PASS  ' in out:
            pr.append('a run with a FAIL printed a PASS line')
        if ran and not log:
            pr.append('the stubs never ran')
        if not ran and log:
            pr.append(f'a step ran when none should have: {log!r}')
        if exact is not None and body(out) != exact:
            pr.append(f'lines {body(out)!r}, wanted {exact!r}')
        if argv is not None and log.strip().split('\n') != argv:
            pr.append(f'argv {log.strip().splitlines()!r}, wanted {argv!r}')
        pr += [f'missing {m!r}' for m in must if m not in out]
        pr += [f'unexpected {m!r}' for m in must_not if m in out]
        res[tag] = pr
    # ---- static: no trap and no exit in the section; the predicate sees the forms a line-start match misses
    LABELS['x_static'] = 'the section holds no trap and no exit (the asset-drift section owns the only EXIT hook)'
    LABELS['x_staticctl'] = 'the trap/exit check sees `true; exit 1`, `x && trap - EXIT`, `( exit 3 )` and a bare trap'
    res['x_static'] = trap_exit_problems(text)
    seen = [trap_exit_problems(text + tail) for tail in ("true; exit 1\n", "x=1 && trap - EXIT\n", "( exit 3 )\n", "trap 'x' EXIT\n")]
    res['x_staticctl'] = [] if all(seen) else [f'a trap/exit went unseen: {seen}']
    return res


LABELS: dict = {}
MUTATIONS: dict = {}


def mut(label, old, new, names, expect=None):
    """names: the case tags this guard exists for, which must go red. expect: the exact set of tags that go red;
    None = not yet pinned, main() prints the measured set."""
    MUTATIONS[label] = (old, new, tuple(names), None if expect is None else tuple(expect))



# ---- the mutations. Each reintroduces ONE defect by deleting or weakening ONE guard of the section; `names` are the cases that guard
# exists for (they must go red) and `expect` is the exact red set. A mutation whose patch text is no longer unique in the section is an
# error, not a skipped mutation.
SKIP_SRC = 'if [ ! -d "$SRC_CACHE" ]; then\n  warn "skipped (no decompiled'
mut('IDENTITY (no change - the harness control)', 'DR_COMPARED=""\n', 'DR_COMPARED=""\n', [], [])
mut('missing source cache not skipped', SKIP_SRC, 'if false; then\n  warn "skipped (no decompiled', ['nosrc'], ('nosrc',))
mut('missing asset cache not skipped', 'elif [ ! -d "$ASSETS" ]; then', 'elif false; then', ['noassets'], ('noassets',))
mut('mktemp failure not read', 'if [ -z "$DR_TMP" ]; then\n    fail "double-run:', 'if false; then\n    fail "double-run:', ['mktemp'], ('mktemp',))
mut('usage.py exit status not read', 'if [ "$RC" -ne 0 ]; then\n      DR_OK=0; fail "usage.py exited', 'if false; then\n      DR_OK=0; fail "usage.py exited', ['u_rc1prob', 'u_rc1none', 'u_rc2'], ('all3', 'u_rc1none', 'u_rc1prob', 'u_rc2'))
mut('usage.py summary line not required', 'elif [ "${DR_U_OK:-x}" != 1 ]; then', 'elif false; then', ['u_nosum', 'u_onep', 'u_twice'], ('u_nosum', 'u_onep', 'u_twice'))
mut('usage.py summary accepts any problem count', "DR_U_OK=\"$(dr_count '^   unknown: [0-9]+ \\(limit 5\\); 0 problem\\(s\\)$'", "DR_U_OK=\"$(dr_count '^   unknown: [0-9]+ \\(limit 5\\); [0-9]+ problem\\(s\\)$'", ['u_onep'], ('u_onep',))
mut('usage.py population figures not required', '*[!0-9/]*) DR_OK=0; fail "usage.py exited 0 but did not print', '*[!0-9/]*) DR_OK=0; : "usage.py exited 0 but did not print', ['u_norun'], ('u_norun',))
mut('rows == run-reached not required', 'if [ "$DR_RUN" -eq 0 ] || [ "$DR_ROWS" -ne "$DR_RUN" ]; then', 'if [ "$DR_RUN" -eq 0 ]; then', ['u_rows'], ('u_rows',))
mut('0 run-reached types accepted', 'if [ "$DR_RUN" -eq 0 ] || [ "$DR_ROWS" -ne "$DR_RUN" ]; then', 'if [ "$DR_ROWS" -ne "$DR_RUN" ]; then', ['u_zero'], ('u_zero',))
mut('usage snapshot not compared', 'if [ "${DR_U_END:-0}" -eq 1 ]; then', 'if false; then', ['s_usage', 's_wrote', 's_nousnap'], ('healthy', 'p_trailing', 's_diff2', 's_noassetssnap', 's_nousnap', 's_usage', 's_wrote'))
mut('census snapshot not compared', 'elif dr_snapshot census', 'elif true || dr_snapshot census', ['s_census', 's_nocsnap'], ('healthy', 'p_trailing', 's_bigdiff', 's_census', 's_diff2', 's_nocsnap', 's_nosource', 's_snapx', 's_twosrc'))
mut('the dropped line is not dropped from the live output', 'grep -v -E -e "$drop" "$live" >', 'cat "$live" >', ['healthy'], ('ALLBUT', 'mktemp', 'noassets', 'nosrc', 's_diff2', 'x_static', 'x_staticctl'))
mut('the dropped line is not dropped from the snapshot', 'grep -v -E -e "$drop" "$snap" >', 'cat "$snap" >', ['healthy'], ('ALLBUT', 'mktemp', 'noassets', 'nosrc', 's_diff2', 'x_static', 'x_staticctl'))
mut('exactly-once test of the dropped line removed', 'if [ "${nl:-x}" != 1 ] || [ "${ns:-x}" != 1 ]; then', 'if false; then', ['s_nosource', 's_noassetssnap', 's_twosrc'], ('s_noassetssnap', 's_nosource', 's_twosrc'))
mut('exactly-once test ignores the live output', 'if [ "${nl:-x}" != 1 ] || [ "${ns:-x}" != 1 ]; then', 'if [ "${ns:-x}" != 1 ]; then', ['s_nosource', 's_twosrc'], ('s_nosource', 's_twosrc'))
mut('exactly-once test ignores the snapshot', 'if [ "${nl:-x}" != 1 ] || [ "${ns:-x}" != 1 ]; then', 'if [ "${nl:-x}" != 1 ]; then', ['s_noassetssnap'], ('s_noassetssnap',))
mut('missing snapshot not reported', 'if [ ! -f "$snap" ]; then', 'if false; then', ['s_nocsnap', 's_nousnap'], ('s_nocsnap', 's_nousnap'))
mut('diff status >= 2 not read', 'if [ "$drc" -ge 2 ]; then', 'if [ "$drc" -ge 3 ]; then', ['s_diff2'], ('s_diff2',))
mut('a differing snapshot is not a FAIL', 'elif [ "$drc" -eq 1 ]; then', 'elif false; then', ['s_census', 's_usage', 's_wrote', 's_snapx'], ('s_bigdiff', 's_census', 's_snapx', 's_usage', 's_wrote'))
mut('census.py exit status not read', 'if [ "$RC" -ne 0 ]; then\n      DR_OK=0; fail "census.py exited', 'if false; then\n      DR_OK=0; fail "census.py exited', ['c_rc1'], ('c_rc1',))
mut('census names line not required', 'elif [ "${DR_CN:-x}" != 1 ] || [ "${DR_CC:-x}" != 1 ]; then', 'elif [ "${DR_CC:-x}" != 1 ]; then', ['c_nodenom'], ('c_nodenom',))
mut('census classes line not required', 'elif [ "${DR_CN:-x}" != 1 ] || [ "${DR_CC:-x}" != 1 ]; then', 'elif [ "${DR_CN:-x}" != 1 ]; then', ['c_noclasses'], ('c_noclasses',))
mut('a census of 0 names accepted', 'if [ "$DR_NAMES" -eq 0 ] || [ "$DR_CLASSES" -eq 0 ]; then', 'if [ "$DR_CLASSES" -eq 0 ]; then', ['c_zeronames'], ('c_zeronames',))
mut('a census of 0 classes accepted', 'if [ "$DR_NAMES" -eq 0 ] || [ "$DR_CLASSES" -eq 0 ]; then', 'if [ "$DR_NAMES" -eq 0 ]; then', ['c_zeroclasses'], ('c_zeroclasses',))
mut('absent tables file not reported', 'if [ ! -f "$DR_TMP/tables13b.md" ]; then', 'if false; then', ['p_notables', 'u_rc1none', 'u_rc2'], ('p_notables', 'u_rc1none', 'u_rc2'))
mut('page anchors not required exactly once', 'if len(starts) != 1 or len(ends) != 1:', 'if False:', ['p_nostart', 'p_noend', 'p_dupstart'], ('p_dupstart', 'p_noend', 'p_nostart'))
mut('a span with no table heading accepted', 'if not first:', 'if False:', ['p_nohead'], ('p_nohead',))
mut('empty generated tables accepted', 'if not tables or not rows:', 'if False:', ['p_emptygen'], ('p_emptygen',))
mut('page span not compared with the generated tables', 'if span != want:', 'if False:', ['neg', 'p_extra', 'p_removed', 'p_reorder', 'p_otherhead', 'p_newhead'], ('neg', 'p_bigdiff', 'p_extra', 'p_newhead', 'p_otherhead', 'p_removed', 'p_reorder'))
mut('trailing blank lines not normalised', 'while ls and not ls[-1].strip():\n        ls.pop()', 'while False:\n        ls.pop()', ['p_trailing'], ('p_bigdiff', 'p_trailing'))
mut('fenced headings counted as anchors', 'if l.startswith(\'```\'):\n        fence = not fence', 'if l.startswith(\'```\'):\n        pass', ['healthy'], ('ALLBUT', 'mktemp', 'neg', 'noassets', 'nosrc', 'p_nopage', 'p_notables', 'u_rc1none', 'u_rc2', 'x_static', 'x_staticctl'))
mut('end anchor must equal the whole heading', 'ends = [i for i, l in heads if l.startswith(END)]', 'ends = [i for i, l in heads if l == END]', ['healthy'], ('ALLBUT', 'mktemp', 'neg', 'noassets', 'nosrc', 'p_dupstart', 'p_noend', 'p_nopage', 'p_notables', 'u_rc1none', 'u_rc2', 'x_static', 'x_staticctl'))
mut('page comparison status not read', 'if [ "$RC" -eq 0 ]; then\n        info "page:', 'if true; then\n        info "page:', ['neg', 'p_extra', 'p_nostart', 'p_nopage'], ('neg', 'p_bigdiff', 'p_dupstart', 'p_emptygen', 'p_extra', 'p_newhead', 'p_noend', 'p_nohead', 'p_nopage', 'p_nostart', 'p_otherhead', 'p_removed', 'p_reorder'))
mut('control exit status not read', 'if [ "$rc" -ne 0 ]; then\n    fail "$name exited $rc:"', 'if false; then\n    fail "$name exited $rc:"', ['t_ct1', 't_ut1', 't_both'], ('all3', 't_both', 't_ct1', 't_ut1'))
mut('control "---- 0 failed" line not required once', 'elif [ "${nz:-x}" != 1 ]; then', 'elif false; then', ['t_ctnosum', 't_utwice'], ('t_ctnosum', 't_utwice'))
mut('control PASS floor not enforced', 'elif [ "${np:-0}" -lt "$min" ]; then', 'elif false; then', ['t_ctfloor', 't_utfloor'], ('t_ctfloor', 't_utfloor'))
mut('census-test.py floor is 0', 'dr_control census-test.py "$DR_MIN_CT"', 'dr_control census-test.py 0', ['t_ctfloor'], ('t_ctfloor',))
mut('usage-test.py floor is 0', 'dr_control usage-test.py "$DR_MIN_UT"', 'dr_control usage-test.py 0', ['t_utfloor'], ('t_utfloor',))
mut('census-test.py not run', 'if dr_control census-test.py', 'if true || dr_control census-test.py', ['healthy', 't_ct1'], ('ALLBUT', 'mktemp', 'noassets', 'nosrc', 'x_static', 'x_staticctl'))
mut('usage-test.py not run', 'if dr_control usage-test.py', 'if true || dr_control usage-test.py', ['healthy', 't_ut1'], ('all3', 'healthy', 'p_trailing', 't_both', 't_ct1', 't_ctfloor', 't_ctnosum', 't_ut1', 't_utfloor', 't_utwice'))
mut('usage.py not given --assets', '--assets "$ASSETS" --src "$SRC_CACHE" --tables', '--src "$SRC_CACHE" --tables', ['healthy'], ('healthy',))
mut('usage.py not given --src', '--assets "$ASSETS" --src "$SRC_CACHE" --tables', '--assets "$ASSETS" --tables', ['healthy'], ('healthy',))
mut('usage.py not given --tables', ' --tables "$DR_TMP/tables13b.md" >', ' >', ['healthy'], ('ALLBUT', 'mktemp', 'noassets', 'nosrc', 'p_notables', 'u_rc1none', 'u_rc2', 'x_static', 'x_staticctl'))
mut('census.py not given --src', '"$DR_DIR/census.py" --src "$SRC_CACHE" >', '"$DR_DIR/census.py" >', ['healthy'], ('healthy',))
mut('census-test.py not given --src', '"$DR_TMP/ct" --src "$SRC_CACHE"', '"$DR_TMP/ct"', ['healthy'], ('healthy',))
mut('usage-test.py not given --assets', '"$DR_TMP/ut" --assets "$ASSETS" --src "$SRC_CACHE"', '"$DR_TMP/ut" --src "$SRC_CACHE"', ['healthy'], ('healthy',))
mut('usage-test.py not given --src', '"$DR_TMP/ut" --assets "$ASSETS" --src "$SRC_CACHE"', '"$DR_TMP/ut" --assets "$ASSETS"', ['healthy'], ('healthy',))
mut('temp dir not removed', '    rm -rf "$DR_TMP"\n    DR_TMP=""\n', '    DR_TMP=""\n', ['healthy'], ('ALLBUT', 'mktemp', 'noassets', 'nosrc', 'x_static', 'x_staticctl'))
mut('DR_TMP not cleared after the removal', '    rm -rf "$DR_TMP"\n    DR_TMP=""\n', '    rm -rf "$DR_TMP"\n', ['healthy'], ('ALLBUT', 'mktemp', 'noassets', 'nosrc', 'x_static', 'x_staticctl'))
mut('PASS printed whatever failed', 'if [ "$DR_OK" -eq 1 ]; then\n      info "census.py:', 'if true; then\n      info "census.py:', ['u_rc1prob'], ('ALLBUT', 'healthy', 'mktemp', 'noassets', 'nosrc', 'p_trailing', 'x_static', 'x_staticctl'))

# the failure flag: a FAIL whose branch no longer clears DR_OK lets the PASS line print beside it
mut('failed usage.py exit status leaves DR_OK set', 'DR_OK=0; fail "usage.py exited $RC', 'fail "usage.py exited $RC', ['u_rc1prob'], ('u_rc1prob',))
mut('failed usage.py summary line leaves DR_OK set', 'DR_OK=0; fail "usage.py exited 0 but printed the line', 'fail "usage.py exited 0 but printed the line', ['u_nosum', 'u_onep', 'u_twice'], ('u_nosum', 'u_onep', 'u_twice'))
mut('failed usage.py population figures leave DR_OK set', '*[!0-9/]*) DR_OK=0; fail', '*[!0-9/]*) fail', ['u_norun'], ('u_norun',))
mut('failed usage.py row count leaves DR_OK set', 'DR_OK=0; fail "usage.py: $DR_ROWS', 'fail "usage.py: $DR_ROWS', ['u_rows', 'u_zero'], ('u_rows', 'u_zero'))
mut('failed usage snapshot leaves DR_OK set', 'then DR_USAGE_CMP="$DR_COMPARED"; else DR_OK=0; DR_USAGE_CMP=""; fi', 'then DR_USAGE_CMP="$DR_COMPARED"; else DR_USAGE_CMP=""; fi', ['s_usage', 's_wrote', 's_nousnap'], ('s_noassetssnap', 's_nousnap', 's_usage', 's_wrote'))
mut('failed census.py exit status leaves DR_OK set', 'DR_OK=0; fail "census.py exited $RC:"', 'fail "census.py exited $RC:"', ['c_rc1'], ('c_rc1',))
mut('failed census.py denominator leaves DR_OK set', 'DR_OK=0; fail "census.py exited 0 but', 'fail "census.py exited 0 but', ['c_nodenom', 'c_noclasses'], ('c_noclasses', 'c_nodenom'))
mut('failed census.py empty census leaves DR_OK set', 'DR_OK=0; fail "census.py: $DR_NAMES', 'fail "census.py: $DR_NAMES', ['c_zeronames', 'c_zeroclasses'], ('c_zeroclasses', 'c_zeronames'))
mut('failed census snapshot leaves DR_OK set', '      else\n        DR_OK=0\n      fi', '      else\n        :\n      fi', ['s_census', 's_nocsnap'], ('s_bigdiff', 's_census', 's_nocsnap', 's_nosource', 's_snapx', 's_twosrc'))
mut('absent tables file leaves DR_OK set', 'DR_OK=0; fail "the page tables were not compared', 'fail "the page tables were not compared', ['p_notables'], ('p_notables',))
mut('failed page comparison leaves DR_OK set', 'DR_OK=0; fail "$DR_PAGE does not match', 'fail "$DR_PAGE does not match', ['neg', 'p_extra', 'p_nostart'], ('neg', 'p_bigdiff', 'p_dupstart', 'p_emptygen', 'p_extra', 'p_newhead', 'p_noend', 'p_nohead', 'p_nopage', 'p_nostart', 'p_otherhead', 'p_removed', 'p_reorder'))
mut('failed census-test.py leaves DR_OK set', 'then DR_CT="$DR_PASSES"; else DR_OK=0; fi', 'then DR_CT="$DR_PASSES"; else :; fi', ['t_ct1', 't_ctnosum', 't_ctfloor'], ('t_ct1', 't_ctfloor', 't_ctnosum'))
mut('failed usage-test.py leaves DR_OK set', 'then DR_UT="$DR_PASSES"; else DR_OK=0; fi', 'then DR_UT="$DR_PASSES"; else :; fi', ['t_ut1', 't_utwice', 't_utfloor'], ('t_ut1', 't_utfloor', 't_utwice'))
# a failing helper must return failure to its caller
mut('a missing snapshot does not return failure', '(a game update renames it; DR_BUILD is $DR_BUILD)"; return 1', '(a game update renames it; DR_BUILD is $DR_BUILD)"', ['s_nocsnap', 's_nousnap'], ('s_nocsnap', 's_nousnap'))
mut('a bad exactly-once test does not return failure', 'would compare something other than the two outputs"; return 1', 'would compare something other than the two outputs"', ['s_nosource', 's_noassetssnap', 's_twosrc'], ('s_noassetssnap', 's_nosource', 's_twosrc'))
mut('a diff status >= 2 does not return failure', 'exited $drc (0 and 1 are normal)"; return 1', 'exited $drc (0 and 1 are normal)"', ['s_diff2'], ('s_diff2',))
mut('a differing snapshot does not return failure', "sed -n '1,40p' \"$DR_TMP/$label.diff\" | sed 's/^/    /'; return 1", "sed -n '1,40p' \"$DR_TMP/$label.diff\" | sed 's/^/    /'", ['s_census', 's_usage', 's_wrote', 's_snapx', 's_bigdiff'], ('s_bigdiff', 's_census', 's_snapx', 's_usage', 's_wrote'))
mut('a failed control exit status does not return failure', "tail -n 20 \"$DR_TMP/$name.err\" | sed 's/^/    stderr: /'; return 1", "tail -n 20 \"$DR_TMP/$name.err\" | sed 's/^/    stderr: /'", ['t_ct1', 't_ut1', 't_both'], ('t_both', 't_ct1', 't_ut1'))
mut('a missing "---- 0 failed" line does not return failure', 'wanted once - it ran, or did it?"; return 1', 'wanted once - it ran, or did it?"', ['t_ctnosum', 't_utwice'], ('t_ctnosum', 't_utwice'))
mut('a PASS count under the floor does not return failure', "reports '0 failed' as well\"; return 1", "reports '0 failed' as well\"", ['t_ctfloor', 't_utfloor'], ('t_ctfloor', 't_utfloor'))
# the diff caps
mut('the snapshot diff is not capped', "sed -n '1,40p' \"$DR_TMP/$label.diff\"", 'cat "$DR_TMP/$label.diff"', ['s_bigdiff'], ('s_bigdiff',))
mut('the page diff is not capped', 'for l in d[:40]:', 'for l in d:', ['p_bigdiff'], ('p_bigdiff',))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mutations', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    text = section_text(VERIFY.read_text())
    ct, ut = floors(text)
    workers = min(32, os.cpu_count() or 4)
    with tempfile.TemporaryDirectory() as td, concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        work = pathlib.Path(td)
        tpl = work / 'tpl'
        build_template(tpl, ct, ut)
        (work / 'base').mkdir()
        res = all_cases(text, tpl, work / 'base', pool)
        # the negative control is judged first: a section that passes a stale page has nothing to say
        if res.get('neg') != []:
            print(f'VOID  the negative control did not behave: {res.get("neg")}. A section that passes a stale page proves nothing.')
            return 2
        if len(res) < MIN_CASES:
            print(f'  FAIL  {len(res)} case(s) ran, floor is {MIN_CASES}. A fixture that examines nothing reports the same thing as one that passes.')
            return 1
        fails = {k: v for k, v in res.items() if v}
        if a.verbose:
            for label in res:
                if not res[label]:
                    print(f'  ok   [{label}] {LABELS[label]}')
        print(f'FIXTURE {len(res)} case(s): {len(res) - len(fails)} passed, {len(fails)} failed')
        for k, v in fails.items():
            print(f'  FAIL [{k}] {LABELS[k]}: ' + '; '.join(v))
        rc = 1 if fails else 0
        if not a.mutations:
            print(f'FIXTURE time {time.time() - t0:.1f} s')
            return rc
        if len(MUTATIONS) < MIN_MUTATIONS:
            print(f'  FAIL  {len(MUTATIONS)} mutation(s) defined, floor is {MIN_MUTATIONS}.')
            return 1
        if not any(k.startswith('IDENTITY') for k in MUTATIONS):
            print('  FAIL  no IDENTITY control in MUTATIONS')
            return 1
        print(f'MUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
        for k, (label, (old, new, names, expect)) in enumerate(MUTATIONS.items()):
            n = text.count(old)
            if n != 1:
                print(f'  FAIL {label}: the anchor occurs {n} time(s) in the section, not once')
                rc = 1
                continue
            mdir = work / f'm{k}'
            mdir.mkdir()
            mres = all_cases(text.replace(old, new, 1), tpl, mdir, pool)
            shutil.rmtree(mdir, ignore_errors=True)
            red = {c for c, v in mres.items() if v}
            if label.startswith('IDENTITY') and red:
                print(f'  FAIL {label}: the control reddened {len(red)} case(s); the harness is broken. Aborting.')
                for x in sorted(red):
                    print(f'         [{x}] {LABELS[x]}')
                return 1
            want = set(names)
            if not names and not label.startswith('IDENTITY'):
                print(f'  FAIL {label}: no case is named for this guard')
                rc = 1
                continue
            if want - red:
                rc = 1
                print(f'  FAIL {label}: the case this defect belongs to stayed GREEN')
                for x in sorted(want - red):
                    print(f'         [{x}] {LABELS[x]}')
                continue
            exp = None if expect is None else (set(mres) - set(expect[1:]) if expect[:1] == ('ALLBUT',) else set(expect))
            if exp is None:
                rc = 1
                print(f'  MEASURED {label}: ' + (repr(sorted(red)) if len(red) * 2 <= len(mres) else 'ALLBUT ' + repr(sorted(set(mres) - red))))
            elif red == exp:
                print(f'  ok   {label} -> {len(red)} case(s) red, exactly as expected')
                if a.verbose:
                    for r in sorted(red):
                        print(f'         [{r}] {LABELS[r]}')
            else:
                rc = 1
                print(f'  FAIL {label}:')
                for x in sorted(exp - red):
                    print(f'         expected red, stayed green: [{x}] {LABELS[x]}')
                for x in sorted(red - exp):
                    print(f'         unexpectedly red: [{x}] {LABELS[x]}')
        print(f'FIXTURE time {time.time() - t0:.1f} s')
    return rc


if __name__ == '__main__':
    sys.exit(main())
