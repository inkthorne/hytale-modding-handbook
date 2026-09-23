#!/usr/bin/env python3
"""
Fixture for the update pipeline: build-jar-cache.sh's snapshot store,
update-build.sh's drift sections, and triage_drift.py's asset rules.

WHY IT EXISTS. Two review rounds found defects that every hand-run check had
passed:
  round 1 (6ba38ce) — a second full run, or a failed decompile, destroyed the
    previous build's snapshot and reported "no changes"; a body change was
    dropped whenever a NESTED class of the file changed signature; the bare-id
    asset rule covered ~20% of item ids;
  round 2 (f172e02) — keying the snapshot on the version string let a jar with
    no Implementation-Version, or an unstamped cache, compare a build with
    itself; changes inside methods CFR cannot decompile were invisible; running
    build-jar-cache.sh by hand destroyed the previous build; a partial decompile
    dropped changes silently; --skip-caches did not check which build the cache
    held; relative or nested store paths were not guarded.
So the behaviour rests on this runner, and --mutations proves each check can go
red by reverting each fix.

WHAT IT DOES. Part 1 builds tiny HytaleServer.jar versions (javac + jar) and a
tiny Assets.zip, installs them under a fake APPDATA root, and runs the real
scripts with every cache, report, snapshot and baseline path in a temp dir.
v1 -> v2:
    BlockHarvestUtils  outer body changes AND nested Qx gains a method
    KickCommand        body-only change
    Dep                gains @Deprecated
    Sw                 a returned string changes inside a method CFR cannot
                       decompile (sealed-interface pattern switch)
    Gone / Fresh       removed / added
Part 2 unit-tests triage_drift.AssetMatcher on a synthetic corpus.

Needs javac, jar, zip, javap and CFR at ~/.cache/hytale-jar-tools/cfr.jar.

Usage: python3 maintenance/scripts/check-update-build-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, os, pathlib, re, shutil, stat, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
CFR = pathlib.Path.home() / '.cache/hytale-jar-tools/cfr.jar'

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()

MIN_CHECKS = 80
MIN_MUTATIONS = 18


class Run:
    """One pass of both parts against one copy of the scripts."""
    def __init__(self, scripts: pathlib.Path, verbose=False):
        self.scripts, self.verbose = scripts, verbose
        self.fails: list[str] = []
        self.checks = 0

    def check(self, cond, what):
        self.checks += 1
        if not cond:
            self.fails.append(what)
        elif self.verbose:
            print(f"  ok  {what}")


R: Run


def check(cond, what):
    R.check(cond, what)


# ---------------------------------------------------------------- jars
P = 'com/hypixel/hytale/demo'
SW = '''public class Sw {
  sealed interface R permits E, Rec {}
  enum E implements R { A, B }
  record Rec(int x) implements R {}
  static String m(R r) {
    return switch (r) {
      case E.A -> "%s-a";
      case E.B -> "b";
      case Rec q -> "rec" + q.x();
    };
  }
}'''
SRC = {
    'v1': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x1000; } public static class Qx { public int a(){return 1;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "old"; } }',
        'Gone': 'public class Gone { public void g(){} }',
        'Dep': 'public class Dep { public void d(){} }',
        'Sw': SW % 'old',
    },
    'v2': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x2000; } public static class Qx { public int a(){return 1;} public int b(){return 2;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "new"; } }',
        'Fresh': 'public class Fresh { public void h(){} }',
        'Dep': 'public class Dep { @Deprecated public void d(){} }',
        'Sw': SW % 'new',
    },
}


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def build(tmp: pathlib.Path):
    # v1/v2 carry Implementation-Version; v1n/v2n have the same classes and none
    for v, ver, classes in (('v1', '0.9.1', SRC['v1']), ('v2', '0.9.2', SRC['v2']),
                            ('v1n', None, SRC['v1']), ('v2n', None, SRC['v2'])):
        src, cls = tmp / v / 'src' / P, tmp / v / 'cls'
        src.mkdir(parents=True); cls.mkdir(parents=True)
        for name, body in classes.items():
            (src / f'{name}.java').write_text(f'package {P.replace("/", ".")}; {body}\n')
        r = sh(f'javac --release 21 -d "{cls}" {P}/*.java', cwd=tmp / v / 'src')
        if r.returncode:
            sys.exit(f"javac failed: {r.stderr}")
        (tmp / v / 'MANIFEST.MF').write_text(f'Implementation-Version: {ver}\n' if ver else 'Created-By: fixture\n')
        r = sh(f'jar cfm "{tmp / v / "HytaleServer.jar"}" "{tmp / v / "MANIFEST.MF"}" com', cwd=cls)
        if r.returncode:
            sys.exit(f"jar failed: {r.stderr}")
    a = tmp / 'assets'
    (a / 'Common/Blocks').mkdir(parents=True); (a / 'Server/Item/Items').mkdir(parents=True)
    (a / 'Common/Blocks/Demo_Block.png').write_text('x\n')
    (a / 'Server/Item/Items/Demo_Item.json').write_text('{}\n')
    sh('cd Common && sha256sum Blocks/Demo_Block.png | sed "s/  / /" > ../CommonAssetsIndex.hashes', cwd=a)
    r = sh(f'zip -qr "{tmp / "Assets.zip"}" .', cwd=a)
    if r.returncode:
        sys.exit(f"zip failed: {r.stderr}")
    # baselines matching the tiny assets: asset drift is zero, and the run does
    # not triage the repo's real 60k-path baselines against them
    b = tmp / 'baseline'; b.mkdir()
    shutil.copy(a / 'CommonAssetsIndex.hashes', b / 'CommonAssetsIndex.hashes')
    r = sh(f'"{HERE / "hash-server-assets.sh"}" "{a}" > "{b / "ServerAssetsIndex.hashes"}"')
    if r.returncode:
        sys.exit(f"hash-server-assets.sh failed: {r.stderr}")
    # fake decompilers with CFR's command line, for DECOMPILER_CMD
    for name, body in (('short', 'find "$OUT" -name KickCommand.java -delete; exit 0'),
                       ('exit1', 'exit 1')):
        f = tmp / f'dec-{name}'
        f.write_text('#!/usr/bin/env bash\n'
                     'OUT=""; prev=""; for a in "$@"; do [ "$prev" = --outputdir ] && OUT="$a"; prev="$a"; done\n'
                     f'java -jar "{CFR}" "$@" >/dev/null 2>&1\n{body}\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)


def install(tmp, v):
    lat = tmp / 'appdata/Hytale/install/release/package/game/latest'
    (lat / 'Server').mkdir(parents=True, exist_ok=True)
    shutil.copy(tmp / v / 'HytaleServer.jar', lat / 'Server/HytaleServer.jar')
    shutil.copy(tmp / 'Assets.zip', lat / 'Assets.zip')


def run(tmp, state, *args, cwd=None, script='update-build.sh', **over):
    env = dict(os.environ, APPDATA=str(tmp / 'appdata'),
               HYTALE_ASSETS=str(state / 'cache-assets'), HYTALE_JAR_CACHE=str(state / 'cache-jar'),
               UPDATE_REPORT=str(state / 'report'), UPDATE_SNAPSHOT=str(state / 'snapshot'),
               UPDATE_BASELINE_DIR=str(tmp / 'baseline'), DECOMPILER_JAR=str(CFR))
    env.pop('DECOMPILER_CMD', None); env.pop('HYTALE_JAR', None)
    env.update(over)
    extra = ['--no-verify', '--no-build'] if script == 'update-build.sh' else []
    r = subprocess.run([str(R.scripts / script), *extra, *args], env=env, capture_output=True, text=True, cwd=cwd)
    rep = state / 'report'
    rd = lambda f: (rep / f).read_text() if (rep / f).exists() else ''
    return r.returncode, r.stdout + r.stderr, rd('src-changed-classes.txt'), rd('api-changed-classes.txt'), rd('triage.txt')


D = 'com.hypixel.hytale.demo.'
SELF = 'the snapshot IS the installed build'


def expect_update(label, rc, out, src, api, tri):
    """The v1 -> v2 drift, however the run got there."""
    check(rc == 0, f"{label}: exit 0 (got {rc})")
    check(f'BODY     {D}KickCommand' in src, f"{label}: body-only change reported (KickCommand)")
    check(f'BODY     {D}BlockHarvestUtils  (nested signature change: BlockHarvestUtils$Qx)' in src,
          f"{label}: outer body change kept as BODY despite a nested signature change")
    check(f'SIG+BODY {D}BlockHarvestUtils' not in src, f"{label}: nested change does not relabel the file SIG+BODY")
    check(f'BYTECODE {D}Sw' in src, f"{label}: change inside a failed decompile reported as BYTECODE")
    check(f'DEPRECATION added   {D}Dep: @Deprecated' in src, f"{label}: @Deprecated addition reported")
    check(f'CHANGED {D}BlockHarvestUtils$Qx' in api, f"{label}: API drift has the nested signature change")
    check(f'ADDED   {D}Fresh' in api and f'REMOVED {D}Gone' in api, f"{label}: API drift has the added and removed classes")
    check(f'body {D}BlockHarvestUtils →' in tri, f"{label}: triage flags pages naming BlockHarvestUtils as a body change")
    check('compared 4 file(s) present in both builds (1 only in the old, 1 only in the new); 3 changed; '
          '1 unchanged file(s) contain a failed decompile' in out, f"{label}: source-drift denominator printed")
    check(SELF not in out, f"{label}: no self-compare warning")
    check('UNEXPLAINED' not in src, f"{label}: every one-sided file is an added/removed class")


def fresh(tmp, name, first='v1'):
    st = tmp / name
    install(tmp, first); run(tmp, st)
    return st


def part1():
    for tool in ('javac', 'jar', 'zip', 'javap'):
        if not shutil.which(tool):
            sys.exit(f"missing required tool: {tool}")
    if not CFR.exists():
        sys.exit(f"missing CFR jar: {CFR} (run maintenance/scripts/build-jar-cache.sh once to download it)")
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        build(tmp)

        # A: first run, update, same-build re-run, --skip-caches
        st = tmp / 'A'
        install(tmp, 'v1'); rc, out, *_ = run(tmp, st)
        check(rc == 0 and 'no existing cache — nothing to preserve' in out, "first run: exits 0, nothing to preserve")
        check('no snapshot of a previous build' in out, "first run: API/source drift skipped with a WARN")
        install(tmp, 'v2'); r = run(tmp, st)
        check('saved the previous build (0.9.1' in r[1], "update: the previous build is saved before the cache is wiped")
        expect_update('update', *r)
        r = run(tmp, st)
        check('built from this same jar' in r[1], "re-run: recognises the cache as the installed jar")
        expect_update('re-run', *r)
        r = run(tmp, st, '--skip-caches')
        check('--skip-caches: the jar cache was built from' not in r[1], "--skip-caches on a current cache: no mismatch warning")
        expect_update('--skip-caches', *r)

        # E: broken decompiler, then recovery
        st = fresh(tmp, 'E'); install(tmp, 'v2')
        bad = tmp / 'notajar.jar'; bad.write_text('not a jar\n')
        rc, out, *_ = run(tmp, st, DECOMPILER_JAR=str(bad))
        check(rc != 0 and 'build-jar-cache.sh failed' in out, "broken decompiler: the run fails instead of reporting no changes")
        expect_update('recovery after broken decompiler', *run(tmp, st))

        # F: an unwritable snapshot store fails before the cache is wiped
        st = fresh(tmp, 'F'); install(tmp, 'v2')
        ro = st / 'ro'; ro.mkdir(); os.chmod(ro, 0o555)
        try:
            rc, out, *_ = run(tmp, st, UPDATE_SNAPSHOT=str(ro / 'snapshot'))
            check(rc != 0 and re.search(r'FAIL\S*\s+cannot create \S*snapshot\.new\.', out),
                  "unwritable snapshot store: the run fails at its own guard")
            check('jar_sha=' + sha(tmp / 'v1/HytaleServer.jar') in (st / 'cache-jar/cache-meta.txt').read_text(),
                  "unwritable snapshot store: the v1 cache is NOT wiped (still the only record)")
        finally:
            os.chmod(ro, 0o755)

        # G (r2 MAJOR-1): jars with NO Implementation-Version
        st = fresh(tmp, 'G', 'v1n'); install(tmp, 'v2n')
        expect_update('no-version update', *run(tmp, st))
        r = run(tmp, st)
        check('built from this same jar' in r[1], "no-version re-run: the cache is recognised by content, not version")
        expect_update('no-version re-run', *r)

        # H (r2 MEDIUM-2): build-jar-cache.sh run by hand before update-build.sh
        st = fresh(tmp, 'H'); install(tmp, 'v2')
        rc, out, *_ = run(tmp, st, script='build-jar-cache.sh')
        check(rc == 0 and 'saved the previous build' in out, "manual build-jar-cache: saves the previous build itself")
        expect_update('update after a manual cache build', *run(tmp, st))

        # I (r2 MEDIUM-3): an unstamped cache never replaces an existing snapshot
        st = fresh(tmp, 'I'); install(tmp, 'v2'); run(tmp, st)
        (st / 'cache-jar/cache-meta.txt').unlink()
        r = run(tmp, st)
        check('keeping the snapshot, NOT replacing it' in r[1], "unstamped cache: the existing snapshot is kept")
        expect_update('re-run over an unstamped cache', *r)

        # J (r2 MEDIUM-4): --skip-caches on a cache that is not the installed build
        st = fresh(tmp, 'J'); install(tmp, 'v2')
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check('--skip-caches: the jar cache was built from' in out, "--skip-caches on a stale cache: warns")

        # K: the self-compare warning fires when it should
        st = fresh(tmp, 'K')
        shutil.copytree(st / 'cache-jar', st / 'snapshot')
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check(SELF in out, "snapshot equal to the installed build: the self-compare warning fires")

        # L (r1 LOW-1): --no-src still preserves the previous build's source
        st = fresh(tmp, 'L'); install(tmp, 'v2')
        run(tmp, st, '--no-src')
        expect_update('full run after a --no-src update', *run(tmp, st))

        # M (r2 LOW-1): partial and failing decompiles fail the run
        for name, what in (('short', 'exits 0 one file short'), ('exit1', 'exits 1 with every file')):
            st = fresh(tmp, f'M{name}'); install(tmp, 'v2')
            rc, out, *_ = run(tmp, st, DECOMPILER_CMD=str(tmp / f'dec-{name}'))
            check(rc != 0 and 'build-jar-cache.sh failed' in out, f"decompiler that {what}: the run fails")

        # N (r2 MEDIUM-1): an incomplete or truncated snapshot decompile is reported, not silent
        st = fresh(tmp, 'N'); install(tmp, 'v2'); run(tmp, st)
        meta, ghost_dir = st / 'snapshot/cache-meta.txt', st / 'snapshot/src' / P
        # a mutated script may leave no snapshot source at all: record that as a
        # failure rather than crash the pass and lose every later check
        if meta.exists() and ghost_dir.is_dir():
            meta.write_text(meta.read_text().replace('src=ok', 'src=failed (exit 1, 4 files)'))
            (ghost_dir / 'Ghost.java').write_text('package com.hypixel.hytale.demo; class Ghost {}\n')
            rc, out, src, *_ = run(tmp, st, '--skip-caches')
        else:
            out = src = ''
        check("the snapshot's decompile is not complete" in out, "incomplete snapshot decompile: warns")
        check(f'UNEXPLAINED only-in-old {D}Ghost' in src and 'WITHOUT being an added/removed class' in out,
              "a one-sided file that is not an added/removed class: reported and warned")

        # O (r2 LOW-2): a store inside the report dir or the cache is refused
        st = fresh(tmp, 'O')
        for inside in ('report', 'cache-jar'):
            rc, out, *_ = run(tmp, st, UPDATE_SNAPSHOT=str(st / inside / 'snap'))
            check(rc != 0 and 'is inside the' in out, f"snapshot store inside the {inside}: refused")

        # P (r2 LOW-2): a relative store path is resolved against the caller's cwd
        st = tmp / 'P'; st.mkdir()
        install(tmp, 'v1'); run(tmp, st, cwd=st, UPDATE_SNAPSHOT='relsnap')
        install(tmp, 'v2'); r = run(tmp, st, cwd=st, UPDATE_SNAPSHOT='relsnap')
        check((st / 'relsnap/javap-index.txt').exists(), "relative UPDATE_SNAPSHOT: store created under the caller's cwd")
        check(not (R.scripts.parents[1] / 'relsnap').exists(), "relative UPDATE_SNAPSHOT: nothing created inside the repo")
        expect_update('relative store path', *r)

        # Q (r2 LOW-3): an interrupted copy's leftovers are removed
        st = fresh(tmp, 'Q'); install(tmp, 'v2')
        (st / 'snapshot.new.99999').mkdir()
        run(tmp, st)
        check(not (st / 'snapshot.new.99999').exists(), "leftover snapshot.new.* from an interrupted copy is removed")


# ---------------------------------------------------------------- part 2
def part2():
    spec = importlib.util.spec_from_file_location(f"triage_drift_{id(R)}", R.scripts / 'triage_drift.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    m = mod.AssetMatcher([
        'Server/Item/Items/Bench/Bench_Alchemy.json', 'Server/Item/Block/Hitboxes/Bench/Bench_Alchemy.json',
        'Icons/ItemsGenerated/Bench_Alchemy.png',
        'Server/Languages/en-US/server.lang', 'Server/Languages/pt-BR/server.lang',
        'Server/Item/Block/Migrations/1.json', 'Icons/Items/EditorTools/Entity.png',
    ] + [f'Characters/Anim{i}/Walk_Backward.blockyanim' for i in range(6)]
      + [f'Family/F{i}/Five_Member.json' for i in range(5)])
    corpus = {
        'docs/a.md': 'Craft it at the `Bench_Alchemy`.',
        'docs/b.md': 'Keys live in `Server/Languages/en-US/server.lang`.',
        'docs/c.md': 'Every `Server/Languages/*/server.lang` carries the key.',
        'docs/d.md': 'See `Zone1_Plains1.json`.',
        'docs/e.md': 'The `Entity.png` icon.',
        'docs/f.md': 'Plays `Walk_Backward`.',
        'docs/g.md': 'Its sibling `Bench_Alchemy_Upgraded` is different.',
        'docs/h.md': 'The `Five_Member` id.',
    }
    h = lambda p: m.hits(p, corpus)
    check(m.rule('Server/Item/Items/Bench/Bench_Alchemy.json')[0] == 'stem', "rule: an id shared by item, hitbox and icon is still an id")
    check(h('Server/Item/Items/Bench/Bench_Alchemy.json') == ['docs/a.md'], "id: bare-id citation matched, a longer id is not")
    check(h('Server/Item/Block/Hitboxes/Bench/Bench_Alchemy.json') == ['docs/a.md'], "id: the hitbox sharing the id is matched too")
    check(h('Family/F0/Five_Member.json') == ['docs/h.md'], "id: a 5-file family is still an id (the MAX_ID_FILES boundary)")
    check(h('Server/Languages/en-US/server.lang') == ['docs/b.md', 'docs/c.md'], "parent: en-US matches its own citation and the wildcard")
    check(h('Server/Languages/pt-BR/server.lang') == ['docs/c.md'], "parent: pt-BR matches only the wildcard, not an en-US citation")
    check(h('Server/Item/Block/Migrations/1.json') == [], "name: `1.json` does not match inside `Zone1_Plains1.json`")
    check(m.rule('Icons/Items/EditorTools/Entity.png')[0] == 'name', "rule: a unique plain name uses the whole-name rule")
    check(h('Icons/Items/EditorTools/Entity.png') == ['docs/e.md'], "name: whole-name citation matched")
    check(m.rule('Characters/Anim0/Walk_Backward.blockyanim')[0] == 'parent', "rule: an id-shaped stem shared by 6 files is generic")
    check(h('Characters/Anim0/Walk_Backward.blockyanim') == [], "parent: a generic shared name does not match its bare word")


def one_pass(scripts, verbose=False):
    global R
    R = Run(scripts, verbose)
    part1()
    part2()
    return R


# Each mutation reverts one fix, as the literal defect a review found, and names
# the checks that must go red. It fails if its patch no longer applies (the code
# moved: update the mutation) or if a named check stays green.
U, B, T = 'update-build.sh', 'build-jar-cache.sh', 'triage_drift.py'
MUTATIONS = [
    ("r2 MAJOR-1: identity by version string", B,
     '[ -n "$OLD_SHA" ] && [ "$OLD_SHA" = "$JAR_SHA" ]',
     '[ "$(meta "$CACHE/cache-meta.txt" version)" = "${JAR_VER:-?}" ]',
     {"no-version re-run: the cache is recognised by content, not version"}),
    ("r1 MAJOR-1: a failed decompile exits 0", B, '      exit 3\n', '      :\n',
     {"broken decompiler: the run fails instead of reporting no changes"}),
    ("r2 LOW-1: partial decompile guard removed", B, ' || [ "$JAVAFILES" -lt "$WANT" ]', '',
     {"decompiler that exits 0 one file short: the run fails"}),
    ("r2 LOW-1: decompiler exit code ignored", B, '[ "$DEC_RC" != 0 ] || ', '',
     {"decompiler that exits 1 with every file: the run fails"}),
    ("r1 MAJOR-2: a nested signature change relabels the outer file", U,
     'if m.group(1) == "REMOVED": removed.add(m.group(2))\ncommon',
     'if m.group(1) == "REMOVED": removed.add(m.group(2))\napi |= {a.split("$")[0] for a in api}\ncommon',
     {"update: outer body change kept as BODY despite a nested signature change",
      "update: triage flags pages naming BlockHarvestUtils as a body change"}),
    ("r2 MAJOR-2: failed decompiles not checked by bytecode", U,
     'elif any(oh.get(k) != nh.get(k) for k in members):', 'elif False:',
     {"update: change inside a failed decompile reported as BYTECODE"}),
    ("r2 MEDIUM-1: incomplete decompile state not read", U,
     '[ "${side#*:}" = ok ] || warn', 'true || warn',
     {"incomplete snapshot decompile: warns"}),
    ("r2 MEDIUM-1: one-sided files not cross-checked", U,
     '    if c not in removed: print(f"UNEXPLAINED only-in-old {c}")', '    pass',
     {"a one-sided file that is not an added/removed class: reported and warned"}),
    ("r1 MAJOR-3: an id must be a unique stem", T, 'self.stems[stem] <= MAX_ID_FILES', 'self.stems[stem] <= 1',
     {"rule: an id shared by item, hitbox and icon is still an id", "id: bare-id citation matched, a longer id is not"}),
    ("r2 LOW-1: MAX_ID_FILES boundary", T, 'MAX_ID_FILES = 5', 'MAX_ID_FILES = 4',
     {"id: a 5-file family is still an id (the MAX_ID_FILES boundary)"}),
    ("wildcard citations are not matched", T, ' + "|" + wild + ', ' + ',
     {"parent: pt-BR matches only the wildcard, not an en-US citation"}),
    ("r1 MEDIUM-2: a snapshot-store failure is ignored", B,
     '{ mkdir -p "$TMP"; } 2>/dev/null || { echo "  FAILED: cannot create $TMP — the cache is NOT wiped" >&2; exit 4; }',
     'mkdir -p "$TMP" 2>/dev/null || true',
     {"unwritable snapshot store: the run fails at its own guard"}),
    ("r2 MEDIUM-3: an unstamped cache replaces the snapshot", B,
     'elif [ -z "$OLD_SHA" ] && [ -f "$SNAP/javap-index.txt" ]; then', 'elif false; then',
     {"unstamped cache: the existing snapshot is kept"}),
    ("r2 MEDIUM-4: --skip-caches does not check the cache", U,
     'if [ "$CACHE_SHA" != "$INSTALLED_SHA" ]; then', 'if false; then',
     {"--skip-caches on a stale cache: warns"}),
    ("r2 LOW-1: self-compare warning never fires", U,
     'if [ "$SNAP_SHA" = "$INSTALLED_SHA" ] || \\', 'if false && \\',
     {"snapshot equal to the installed build: the self-compare warning fires"}),
    ("r1 LOW-1: --no-src drops the previous source", B,
     '  if [ -d "$CACHE/src" ]; then\n    cp -a', '  if false; then\n    cp -a',
     {"full run after a --no-src update: body-only change reported (KickCommand)"}),
    ("r2 LOW-2: store inside the report dir allowed", U,
     'case "$S_ABS/" in "$d/"*) fail', 'case "$S_ABS/" in "/nonexistent/"*) fail',
     {"snapshot store inside the report: refused"}),
    ("r2 LOW-2: relative paths re-rooted in the repo", U,
     '[ -n "${!v:-}" ] && export "$v=$(realpath -m "${!v}")"', ':',
     {"relative UPDATE_SNAPSHOT: store created under the caller's cwd"}),
    ("r2 LOW-3: interrupted-copy leftovers kept", B, '  rm -rf "$SNAP".new.* 2>/dev/null\n', '',
     {"leftover snapshot.new.* from an interrupted copy is removed"}),
]


def mutations():
    ran, bad = 0, []
    for label, fname, old, new, must_red in MUTATIONS:
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            shutil.copytree(HERE, root / 'maintenance/scripts', ignore=shutil.ignore_patterns('__pycache__'))
            for d in ('docs', 'examples'):
                (root / d).symlink_to(REPO / d)
            f = root / 'maintenance/scripts' / fname
            src = f.read_text()
            if src.count(old) != 1:
                bad.append(f"{label}: patch no longer applies to {fname} ({src.count(old)} match(es))")
                continue
            f.write_text(src.replace(old, new))
            r = one_pass(root / 'maintenance/scripts')
            ran += 1
            stayed = sorted(must_red - set(r.fails))
            if stayed:
                bad.append(f"{label}: still green: {'; '.join(stayed)}")
            elif A.verbose:
                print(f"  red {label}: {len(r.fails)} check(s) failed, including all {len(must_red)} expected")
    return ran, bad


base = one_pass(HERE, A.verbose)
fails = list(base.fails)
if base.checks < MIN_CHECKS:
    fails.append(f"only {base.checks} check(s) ran, floor is {MIN_CHECKS}")
print(f"FIXTURE {base.checks} check(s): {base.checks - len(base.fails)} passed, {len(base.fails)} failed")
if A.mutations:
    ran, bad = mutations()
    if ran < MIN_MUTATIONS:
        bad.append(f"only {ran} mutation(s) ran, floor is {MIN_MUTATIONS}")
    print(f"MUTATIONS {ran} defect(s) reintroduced, {ran - len([b for b in bad if 'still green' in b])} turned their checks red")
    fails += bad
for f in fails:
    print(f"  FAIL {f}")
sys.exit(1 if fails else 0)
