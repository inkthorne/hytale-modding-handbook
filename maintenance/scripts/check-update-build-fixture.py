#!/usr/bin/env python3
"""
Fixture for update-build.sh's drift sections and triage_drift.py's asset rules.

WHY IT EXISTS. Review of 6ba38ce found three MAJOR defects that the manual runs
behind that commit could not see:
  - a failed decompile, or a second full run on the same build, destroyed the
    previous build's snapshot and reported "no changes";
  - a body change was dropped whenever a NESTED class of the same file changed
    signature;
  - the bare-id asset rule applied to ~20% of item ids, and the one example
    that "confirmed" it had matched by a different rule.
Every one of those passed a hand-run fixture, so the behaviour now rests on
this runner instead.

WHAT IT DOES. Part 1 builds two tiny HytaleServer.jar versions (javac + jar)
and a tiny Assets.zip, installs them under a fake APPDATA root, and runs the real
update-build.sh (--no-verify --no-build) with every cache, report and snapshot
path pointed into a temp dir. v1 -> v2:
    BlockHarvestUtils  outer body changes AND nested Qx gains a method
    KickCommand        body-only change
    Dep                gains @Deprecated
    Gone / Fresh       removed / added
Part 2 unit-tests triage_drift.AssetMatcher against a synthetic corpus: one case
per matching rule plus the negative controls that each rule exists to protect.

Needs javac, jar, zip and a decompiler (the same resolution build-jar-cache.sh
uses; ~/.cache/hytale-jar-tools/cfr.jar is used when present).

With --mutations it then reintroduces each defect the review found, one at a
time, in a temp copy of the scripts, and asserts that the checks written for it
go red. A fixture that has only ever passed has not shown it can fail.

Usage: python3 maintenance/scripts/check-update-build-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
import importlib.util

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()

MIN_CHECKS = 50
MIN_MUTATIONS = 6


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


R: Run  # the pass in progress


def check(cond, what):
    R.check(cond, what)


# ---------------------------------------------------------------- part 1
P = 'com/hypixel/hytale/demo'
SRC = {
    'v1': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x1000; } public static class Qx { public int a(){return 1;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "old"; } }',
        'Gone': 'public class Gone { public void g(){} }',
        'Dep': 'public class Dep { public void d(){} }',
    },
    'v2': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x2000; } public static class Qx { public int a(){return 1;} public int b(){return 2;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "new"; } }',
        'Fresh': 'public class Fresh { public void h(){} }',
        'Dep': 'public class Dep { @Deprecated public void d(){} }',
    },
}
VERSIONS = {'v1': '0.9.1', 'v2': '0.9.2'}


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def build(tmp: pathlib.Path):
    for v, classes in SRC.items():
        src, cls = tmp / v / 'src' / P, tmp / v / 'cls'
        src.mkdir(parents=True); cls.mkdir(parents=True)
        for name, body in classes.items():
            (src / f'{name}.java').write_text(f'package {P.replace("/", ".")}; {body}\n')
        r = sh(f'javac --release 21 -d "{cls}" {P}/*.java', cwd=tmp / v / 'src')
        if r.returncode:
            sys.exit(f"javac failed: {r.stderr}")
        (tmp / v / 'MANIFEST.MF').write_text(f'Implementation-Version: {VERSIONS[v]}\n')
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
    # baselines matching the tiny assets, so asset drift is zero and the run
    # does not triage the repo's real 60k-path baselines against them
    b = tmp / 'baseline'; b.mkdir()
    shutil.copy(a / 'CommonAssetsIndex.hashes', b / 'CommonAssetsIndex.hashes')
    r = sh(f'"{HERE / "hash-server-assets.sh"}" "{a}" > "{b / "ServerAssetsIndex.hashes"}"')
    if r.returncode:
        sys.exit(f"hash-server-assets.sh failed: {r.stderr}")


def install(tmp, v):
    lat = tmp / 'appdata/Hytale/install/release/package/game/latest'
    (lat / 'Server').mkdir(parents=True, exist_ok=True)
    shutil.copy(tmp / v / 'HytaleServer.jar', lat / 'Server/HytaleServer.jar')
    shutil.copy(tmp / 'Assets.zip', lat / 'Assets.zip')


def run(tmp, state, *args, decompiler=None):
    env = dict(os.environ, APPDATA=str(tmp / 'appdata'),
               HYTALE_ASSETS=str(state / 'cache-assets'), HYTALE_JAR_CACHE=str(state / 'cache-jar'),
               UPDATE_REPORT=str(state / 'report'), UPDATE_SNAPSHOT=str(state / 'snapshot'),
               UPDATE_BASELINE_DIR=str(tmp / 'baseline'))
    if decompiler:
        env['DECOMPILER_JAR'] = decompiler
    elif (pathlib.Path.home() / '.cache/hytale-jar-tools/cfr.jar').exists():
        env['DECOMPILER_JAR'] = str(pathlib.Path.home() / '.cache/hytale-jar-tools/cfr.jar')
    r = subprocess.run([str(R.scripts / 'update-build.sh'), '--no-verify', '--no-build', *args],
                       env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    rep = state / 'report'
    rd = lambda f: (rep / f).read_text() if (rep / f).exists() else ''
    return r.returncode, out, rd('src-changed-classes.txt'), rd('api-changed-classes.txt'), rd('triage.txt')


D = 'com.hypixel.hytale.demo.'


def expect_v1_to_v2(label, rc, out, src, api, tri):
    check(rc == 0, f"{label}: exit 0 (got {rc})")
    check(f'BODY     {D}KickCommand' in src, f"{label}: body-only change reported (KickCommand)")
    # MAJOR-2: the outer body changed while only the NESTED class changed signature
    check(f'BODY     {D}BlockHarvestUtils  (nested signature change: BlockHarvestUtils$Qx)' in src,
          f"{label}: outer body change kept as BODY despite a nested signature change")
    check(f'SIG+BODY {D}BlockHarvestUtils' not in src, f"{label}: nested change does not relabel the file SIG+BODY")
    check(f'DEPRECATION added   {D}Dep: @Deprecated' in src, f"{label}: @Deprecated addition reported")
    check(f'CHANGED {D}BlockHarvestUtils$Qx' in api, f"{label}: API drift has the nested signature change")
    check(f'ADDED   {D}Fresh' in api and f'REMOVED {D}Gone' in api, f"{label}: API drift has the added and removed classes")
    check(f'body {D}BlockHarvestUtils →' in tri, f"{label}: triage flags pages naming BlockHarvestUtils as a body change")
    check('compared 3 file(s) present in both builds (1 only in the old, 1 only in the new' in out,
          f"{label}: source-drift denominator printed")


def part1():
    for tool in ('javac', 'jar', 'zip', 'javap'):
        if not shutil.which(tool):
            sys.exit(f"missing required tool: {tool}")
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        build(tmp)

        # A. first run, v1: nothing to snapshot yet
        st = tmp / 'A'
        install(tmp, 'v1'); rc, out, *_ = run(tmp, st)
        check(rc == 0 and 'no existing jar cache to snapshot' in out, "first run: exits 0 and says there is no cache to snapshot")
        check('no snapshot of a previous build' in out, "first run: API/source drift skipped with a WARN")
        # B. update to v2
        install(tmp, 'v2'); r = run(tmp, st)
        check('snapshot of 0.9.1 taken' in r[1], "update: snapshot of the previous build taken")
        expect_v1_to_v2('update', *r)
        # C. MAJOR-1: a second full run on the same build keeps the snapshot
        r = run(tmp, st)
        check('already built from the installed 0.9.2' in r[1], "re-run: recognises the cache as the installed build")
        check('compares 0.9.2 with itself' not in r[1], "re-run: does not compare the build with itself")
        expect_v1_to_v2('re-run', *r)
        # D. --skip-caches uses the same snapshot
        r = run(tmp, st, '--skip-caches')
        expect_v1_to_v2('--skip-caches', *r)

        # E. MAJOR-1: a broken decompiler fails loudly, and the recovery run still
        #    diffs against the v1 snapshot rather than snapshotting half-built v2
        st = tmp / 'E'
        install(tmp, 'v1'); run(tmp, st)
        install(tmp, 'v2')
        bad = tmp / 'notajar.jar'; bad.write_text('not a jar\n')
        rc, out, *_ = run(tmp, st, decompiler=str(bad))
        check(rc != 0 and 'build-jar-cache.sh failed' in out, "broken decompiler: the run fails instead of reporting no changes")
        r = run(tmp, st)
        check('already built from the installed 0.9.2' in r[1], "recovery run: keeps the v1 snapshot")
        expect_v1_to_v2('recovery', *r)

        # F. MEDIUM-2: an unwritable snapshot store fails before the caches are rebuilt
        st = tmp / 'F'
        install(tmp, 'v1'); run(tmp, st)
        install(tmp, 'v2')
        (st / 'snapshot').mkdir(exist_ok=True)
        ro = st / 'ro'; ro.mkdir(); os.chmod(ro, 0o555)
        env_snap = str(ro / 'snapshot')
        try:
            env = dict(os.environ, APPDATA=str(tmp / 'appdata'), HYTALE_ASSETS=str(st / 'cache-assets'),
                       HYTALE_JAR_CACHE=str(st / 'cache-jar'), UPDATE_REPORT=str(st / 'report'),
                       UPDATE_SNAPSHOT=env_snap, UPDATE_BASELINE_DIR=str(tmp / 'baseline'))
            p = subprocess.run([str(R.scripts / 'update-build.sh'), '--no-verify', '--no-build'],
                               env=env, capture_output=True, text=True)
            meta = (st / 'cache-jar/cache-meta.txt').read_text()
            # the script's own message, not cp's "cannot create regular file",
            # which a missing guard also produces (found by the mutation below)
            check(p.returncode != 0 and re.search(r'FAIL\S*\s+cannot create \S*snapshot\.new\.', p.stdout + p.stderr),
                  "unwritable snapshot store: the run fails at its own guard")
            check('version=0.9.1' in meta, "unwritable snapshot store: the v1 cache is NOT rebuilt (still the only record)")
        finally:
            os.chmod(ro, 0o755)


# ---------------------------------------------------------------- part 2
def part2():
    spec = importlib.util.spec_from_file_location(f"triage_drift_{id(R)}", R.scripts / 'triage_drift.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    AssetMatcher = mod.AssetMatcher
    shipped = [
        'Server/Item/Items/Bench/Bench_Alchemy.json', 'Server/Item/Block/Hitboxes/Bench/Bench_Alchemy.json',
        'Icons/ItemsGenerated/Bench_Alchemy.png',
        'Server/Languages/en-US/server.lang', 'Server/Languages/pt-BR/server.lang',
        'Server/Item/Block/Migrations/1.json', 'Icons/Items/EditorTools/Entity.png',
    ] + [f'Characters/Anim{i}/Walk_Backward.blockyanim' for i in range(6)]
    m = AssetMatcher(shipped)
    corpus = {
        'docs/a.md': 'Craft it at the `Bench_Alchemy`.',
        'docs/b.md': 'Keys live in `Server/Languages/en-US/server.lang`.',
        'docs/c.md': 'Every `Server/Languages/*/server.lang` carries the key.',
        'docs/d.md': 'See `Zone1_Plains1.json`.',
        'docs/e.md': 'The `Entity.png` icon.',
        'docs/f.md': 'Plays `Walk_Backward`.',
        'docs/g.md': 'Its sibling `Bench_Alchemy_Upgraded` is different.',
    }
    h = lambda p: m.hits(p, corpus)
    check(m.rule('Server/Item/Items/Bench/Bench_Alchemy.json')[0] == 'stem', "rule: an id shared by item, hitbox and icon is still an id")
    check(h('Server/Item/Items/Bench/Bench_Alchemy.json') == ['docs/a.md'], "id: bare-id citation matched, a longer id is not")
    check(h('Server/Item/Block/Hitboxes/Bench/Bench_Alchemy.json') == ['docs/a.md'], "id: the hitbox sharing the id is matched too")
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


# Each mutation reverts one fix, as the literal defect the review found, and
# names the checks that must go red. It fails if the patch no longer applies
# (the code moved; update the mutation) or if a named check stays green.
MUTATIONS = [
    ("MAJOR-1: every full run re-snapshots the cache", 'update-build.sh',
     'elif [ "$CACHE_VER" = "${NEW_VER:-?}" ]; then', 'elif false; then',
     {"re-run: recognises the cache as the installed build", "re-run: does not compare the build with itself",
      "recovery run: keeps the v1 snapshot"}),
    ("MAJOR-1: a failed decompile exits 0", 'build-jar-cache.sh',
     '      exit 3\n', '      :\n',
     {"broken decompiler: the run fails instead of reporting no changes"}),
    ("MAJOR-2: a nested signature change relabels the outer file", 'update-build.sh',
     'if m: api.add(m.group(1))', 'if m: api.add(m.group(1).split("$")[0])',
     {"update: outer body change kept as BODY despite a nested signature change",
      "update: nested change does not relabel the file SIG+BODY",
      "update: triage flags pages naming BlockHarvestUtils as a body change"}),
    ("MAJOR-3: an id must be a unique stem", 'triage_drift.py',
     'self.stems[stem] <= MAX_ID_FILES', 'self.stems[stem] <= 1',
     {"rule: an id shared by item, hitbox and icon is still an id", "id: bare-id citation matched, a longer id is not"}),
    ("wildcard citations are not matched", 'triage_drift.py',
     ' + "|" + wild + ', ' + ',
     {"parent: pt-BR matches only the wildcard, not an en-US citation",
      "parent: en-US matches its own citation and the wildcard"}),
    ("MEDIUM-2: a snapshot-store failure is ignored", 'update-build.sh',
     '{ rm -rf "$TMP" && mkdir -p "$TMP"; } || { fail "cannot create $TMP"; exit 2; }',
     'mkdir -p "$TMP" 2>/dev/null || true',
     {"unwritable snapshot store: the run fails at its own guard"}),
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
            old_s, new_s = old.replace('\\n', '\n'), new.replace('\\n', '\n')
            if src.count(old_s) != 1:
                bad.append(f"{label}: patch no longer applies to {fname} ({src.count(old_s)} match(es))")
                continue
            f.write_text(src.replace(old_s, new_s))
            r = one_pass(root / 'maintenance/scripts')
            ran += 1
            stayed_green = sorted(must_red - set(r.fails))
            if stayed_green:
                bad.append(f"{label}: still green: {'; '.join(stayed_green)}")
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
