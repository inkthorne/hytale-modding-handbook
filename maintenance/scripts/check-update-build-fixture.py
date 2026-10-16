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
  round 3 (c6a46fa) — a scratch cache overwrote the default store; an old-style
    snapshot identical to the installed build went unwarned; six guards had no
    test.
So the behaviour rests on this runner, and --mutations proves each check can go
red by reverting each fix.

WHAT IT DOES. Resource drift (acceptance 8) closed the first gap invariant 4 listed as "not covered":
the jar's non-class entries. Cases below: W (resource-only update), X (timestamps only),
Y/Z (BLIND and old-style snapshots), R (snapshot copy list), B (writer failures), and the
resource rows of every v1 -> v2 run; one mutation per guard, each named after its check.

Part 1 builds tiny HytaleServer.jar versions (javac + jar) and a
tiny Assets.zip, installs them under a fake APPDATA root, and runs the real
scripts with every cache, report, snapshot and baseline path in a temp dir.
v1 -> v2:
    BlockHarvestUtils  outer body changes AND nested Qx gains a method
    KickCommand        body-only change
    Dep                gains @Deprecated
    PluginManager      a returned string changes inside a method CFR cannot
                       decompile (a sealed-interface pattern switch in nested In)
    Gone / Fresh       removed / added
    resources          the jar's NON-class entries (migration/blocks, bundledDefaults,
                       services files, natives, a vendor package ...) are hashed by
                       content: one changed, one removed, one added, one unchanged
                       beside them, in the Hypixel and third-party groups both.
    v1r                v1 with ONE migration file changed, classes identical: a
                       resource-only update, which the self-compare warning must not hide.
    v1t                v1 repacked with different zip timestamps and no byte changed:
                       NOT reported.
Part 2 unit-tests triage_drift.AssetMatcher on a synthetic corpus, and runs
triage_drift.main on a synthetic report to test how class rows and resource rows
are keyed.

Needs javac, jar, zip, javap and CFR at ~/.cache/hytale-jar-tools/cfr.jar.

Usage: python3 maintenance/scripts/check-update-build-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, contextlib, hashlib, importlib.util, io, os, pathlib, re, shutil, stat, subprocess, sys, tempfile, zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
CFR = pathlib.Path.home() / '.cache/hytale-jar-tools/cfr.jar'

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()

MIN_CHECKS = 437
MIN_MUTATIONS = 63


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
# The stub-hidden change sits in a NESTED class (In) of a class the docs name,
# so the fixture holds both the member-level bytecode compare and its triage.
SW = '''public class PluginManager {
  sealed interface R permits E, Rec {}
  enum E implements R { A, B }
  record Rec(int x) implements R {}
  static class In {
    static String m(R r) {
      return switch (r) {
        case E.A -> "%s-a";
        case E.B -> "b";
        case Rec q -> "rec" + q.x();
      };
    }
  }
}'''
SRC = {
    'v1': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x1000; } public static class Qx { public int a(){return 1;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "old"; } }',
        'Gone': 'public class Gone { public void g(){} }',
        'Dep': 'public class Dep { public void d(){} }',
        'PluginManager': SW % 'old',
    },
    'v2': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x2000; } public static class Qx { public int a(){return 1;} public int b(){return 2;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "new"; } }',
        'Fresh': 'public class Fresh { public void h(){} }',
        'Dep': 'public class Dep { @Deprecated public void d(){} }',
        'PluginManager': SW % 'new',
    },
}


# Non-class jar entries. Each has one job (the rule letters are build-jar-cache.sh's):
#   migration/blocks/3_4.json   Hypixel (d): CHANGED          .../0_1.json: unchanged beside it
#   jwks_bundled.json           Hypixel (d): REMOVED          brandnew/data.json: ADDED, a
#                                            top-level directory the jar has never shown
#   com/hypixel/.../data.json   Hypixel (x): under com/, which ALSO holds a vendor package
#   META-INF/services/...Svc    Hypixel (c): its PATH names com.hypixel
#   META-INF/services/other.Spi Hypixel (c): its BYTES name com.hypixel
#   META-INF/services/vendor.Spi third-party (c)
#   native/...libx.so, win-x64/x.dll, osx-arm64/libgone.dylib   third-party (b): CHANGED/ADDED/REMOVED
#   com/vendor/messages.properties   third-party (a): com/ holds com/vendor/lib/Ext.class
#   vendor/lib/schema.proto          third-party (e): beside com/vendor/lib/Ext.class
R1 = {
    'migration/blocks/0_1.json': b'{"from":0}\n',
    'migration/blocks/3_4.json': b'{"to":4,"map":"a"}\n',
    'bundledDefaults/server.lang': b'hello = Hello\n',
    'jwks_bundled.json': b'{"keys":[]}\n',
    'update/start.sh': b'#!/bin/sh\n',
    'com/hypixel/hytale/demo/data.json': b'{"x":1}\n',
    'META-INF/services/com.hypixel.hytale.demo.Svc': b'impl-a\n',
    'META-INF/services/other.Spi': b'com.hypixel.hytale.demo.Dep\n',
    'META-INF/services/vendor.Spi': b'org.vendor.ImplA\n',
    'native/linux-x64/libx.so': b'\x7fELF-a',
    'native/osx-arm64/libgone.dylib': b'gone',
    'com/vendor/messages.properties': b'a=1\n',
    'vendor/lib/schema.proto': b'syntax = "proto3"; // a\n',
}
R2 = {k: v for k, v in R1.items() if k not in ('jwks_bundled.json', 'native/osx-arm64/libgone.dylib')}
R2.update({
    'migration/blocks/3_4.json': b'{"to":4,"map":"b"}\n',
    'brandnew/data.json': b'{"new":true}\n',
    'com/hypixel/hytale/demo/data.json': b'{"x":2}\n',
    'META-INF/services/com.hypixel.hytale.demo.Svc': b'impl-b\n',
    'META-INF/services/other.Spi': b'com.hypixel.hytale.demo.Fresh\n',
    'META-INF/services/vendor.Spi': b'org.vendor.ImplB\n',
    'native/linux-x64/libx.so': b'\x7fELF-b',
    'native/win-x64/x.dll': b'MZ',
    'com/vendor/messages.properties': b'a=2\n',
    'vendor/lib/schema.proto': b'syntax = "proto3"; // b\n',
})
R1R = dict(R1, **{'migration/blocks/3_4.json': b'{"to":4,"map":"r"}\n'})
VENDOR = 'package com.vendor.lib; public class Ext { public int e(){ return 1; } }\n'
D1, D2 = (2020, 1, 2, 3, 4, 6), (2021, 5, 6, 7, 8, 10)     # zip entry timestamps
RES_DRIFT_V1_V2 = [   # state owner rule path: the whole resource drift of v1 -> v2
    'CHANGED hypixel d migration/blocks/3_4.json', 'REMOVED hypixel d jwks_bundled.json',
    'ADDED hypixel d brandnew/data.json', 'CHANGED hypixel x com/hypixel/hytale/demo/data.json',
    'CHANGED hypixel c META-INF/services/com.hypixel.hytale.demo.Svc', 'CHANGED hypixel c META-INF/services/other.Spi',
    'CHANGED third-party c META-INF/services/vendor.Spi', 'CHANGED third-party b native/linux-x64/libx.so',
    'ADDED third-party b native/win-x64/x.dll', 'REMOVED third-party b native/osx-arm64/libgone.dylib',
    'CHANGED third-party a com/vendor/messages.properties', 'CHANGED third-party e vendor/lib/schema.proto',
]


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]


def pack(base, dest, resources, dt, manifest=True, store=False):
    """Repack a jar with the resources added and EVERY entry's timestamp set to dt,
    so which bytes differ between two jars is decided here and not by the clock."""
    with zipfile.ZipFile(base) as zi, zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            if not manifest and info.filename.startswith('META-INF'):
                continue
            zinfo = zipfile.ZipInfo(info.filename, dt)
            zinfo.compress_type, zinfo.external_attr = zipfile.ZIP_DEFLATED, info.external_attr
            zo.writestr(zinfo, zi.read(info.filename))
        for name, data in resources.items():
            zinfo = zipfile.ZipInfo(name, dt)
            zinfo.compress_type = zipfile.ZIP_STORED if store else zipfile.ZIP_DEFLATED
            zo.writestr(zinfo, data)


def build(tmp: pathlib.Path):
    # v1/v2 carry Implementation-Version; v1n/v2n have the same classes and none;
    # v1r / v1t are v1 with one resource changed / with only the zip timestamps changed
    for v, ver, classes, res, dt in (('v1', '0.9.1', SRC['v1'], R1, D1), ('v2', '0.9.2', SRC['v2'], R2, D1),
                                     ('v1n', None, SRC['v1'], R1, D1), ('v2n', None, SRC['v2'], R2, D1),
                                     ('v1r', '0.9.1', SRC['v1'], R1R, D1), ('v1t', '0.9.1', SRC['v1'], R1, D2)):
        src, cls = tmp / v / 'src' / P, tmp / v / 'cls'
        src.mkdir(parents=True); cls.mkdir(parents=True)
        (tmp / v / 'src/com/vendor/lib').mkdir(parents=True)
        (tmp / v / 'src/com/vendor/lib/Ext.java').write_text(VENDOR)
        for name, body in classes.items():
            (src / f'{name}.java').write_text(f'package {P.replace("/", ".")}; {body}\n')
        r = sh(f'javac --release 21 -d "{cls}" {P}/*.java com/vendor/lib/*.java', cwd=tmp / v / 'src')
        if r.returncode:
            sys.exit(f"javac failed: {r.stderr}")
        (tmp / v / 'MANIFEST.MF').write_text(f'Implementation-Version: {ver}\n' if ver else 'Created-By: fixture\n')
        r = sh(f'jar cfm "{tmp / v / "base.jar"}" "{tmp / v / "MANIFEST.MF"}" com', cwd=cls)
        if r.returncode:
            sys.exit(f"jar failed: {r.stderr}")
        pack(tmp / v / 'base.jar', tmp / v / 'HytaleServer.jar', res, dt)
    # a jar with no non-class entry at all (not even a manifest), and one whose
    # resource cannot be read back (bad CRC): the two ways the writer can fail
    pack(tmp / 'v1/base.jar', tmp / 'v0.jar', {}, D1, manifest=False)
    pack(tmp / 'v1/base.jar', tmp / 'vbad.jar', {'migration/blocks/3_4.json': b'CORRUPT-ME-CORRUPT-ME'}, D1, store=True)
    raw = (tmp / 'vbad.jar').read_bytes()
    assert raw.count(b'CORRUPT-ME-CORRUPT-ME') == 1
    (tmp / 'vbad.jar').write_bytes(raw.replace(b'CORRUPT-ME-CORRUPT-ME', b'CORRUPT-XX-CORRUPT-ME'))
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
    for k in [k for k, v in env.items() if v is None]:   # None = unset, to exercise a default
        del env[k]
    extra = ['--no-verify', '--no-build'] if script == 'update-build.sh' else []
    r = subprocess.run([str(R.scripts / script), *extra, *args], env=env, capture_output=True, text=True, cwd=cwd)
    rep = state / 'report'
    rd = lambda f: (rep / f).read_text() if (rep / f).exists() else ''
    return (r.returncode, r.stdout + r.stderr, rd('src-changed-classes.txt'), rd('api-changed-classes.txt'),
            rd('triage.txt'), rd('resource-drift.txt'))


D = 'com.hypixel.hytale.demo.'
SELF = 'the snapshot IS the installed build'


def expect_resources(label, out, res, manifest=True):
    """The v1 -> v2 resource drift: exactly these rows, each with the owner and rule
    that decided it, and nothing for the entries that did not change."""
    want = RES_DRIFT_V1_V2 + (['CHANGED third-party c META-INF/MANIFEST.MF'] if manifest else [])
    rows = res.splitlines()
    for row in want:
        check(row in rows, f"{label}: resource drift has `{row}`")
    check(len(rows) == len(want), f"{label}: resource drift has exactly {len(want)} row(s) (got {len(rows)})")
    for quiet in ('migration/blocks/0_1.json', 'bundledDefaults/server.lang', 'update/start.sh'):
        check(quiet not in res, f"{label}: unchanged resource {quiet} is not reported")
    n_old, n_new = len(R1) + 1, len(R2) + 1      # + the manifest, which every jar carries
    check(f'compared {n_old} resource(s) in the snapshot with {n_new} in the new build' in out,
          f"{label}: resource denominator printed")
    check('Hypixel-owned resource(s) added/removed/changed' in out and 'CHANGED d migration/blocks/3_4.json' in out,
          f"{label}: Hypixel-owned resources listed one by one")
    check('libx.so' not in out and 'CHANGED native/linux-x64 1' in out,
          f"{label}: third-party resources collapsed to counts, not listed")
    check('holds:' in out and 'ownership: Hypixel' in out, f"{label}: the ownership rule and what each side holds are printed")


def expect_update(label, rc, out, src, api, tri, res='', manifest=True):
    """The v1 -> v2 drift, however the run got there."""
    expect_resources(label, out, res, manifest)
    check(rc == 0, f"{label}: exit 0 (got {rc})")
    check(f'BODY     {D}KickCommand' in src, f"{label}: body-only change reported (KickCommand)")
    check(f'BODY     {D}BlockHarvestUtils  (nested signature change: BlockHarvestUtils$Qx)' in src,
          f"{label}: outer body change kept as BODY despite a nested signature change")
    check(f'SIG+BODY {D}BlockHarvestUtils' not in src, f"{label}: nested change does not relabel the file SIG+BODY")
    check(f'BYTECODE {D}PluginManager' in src, f"{label}: change inside a failed decompile (nested class) reported as BYTECODE")
    check(f'body {D}PluginManager →' in tri, f"{label}: triage flags pages naming a BYTECODE class")
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
        # the resources are hashed BEFORE the decompile, so a failed decompile still leaves them
        check((st / 'cache-jar/resource-hashes.txt').exists() and (st / 'cache-jar/resource-owners.txt').exists(),
              "broken decompiler: the cache still has the resource hashes (written before the decompile)")
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
        expect_update('no-version update', *run(tmp, st), manifest=False)
        r = run(tmp, st)
        check('built from this same jar' in r[1], "no-version re-run: the cache is recognised by content, not version")
        expect_update('no-version re-run', *r, manifest=False)

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

        # S (r3 MEDIUM-1): a scratch cache never touches the default store
        home = tmp / 'S-home'; home.mkdir()
        st = tmp / 'S'
        def_store = home / '.cache/hytale-update-snapshot'
        install(tmp, 'v1'); run(tmp, st, HOME=str(home), HYTALE_JAR_CACHE=None, UPDATE_SNAPSHOT=None)
        install(tmp, 'v2'); run(tmp, st, HOME=str(home), HYTALE_JAR_CACHE=None, UPDATE_SNAPSHOT=None)
        before = (def_store / 'cache-meta.txt').read_text() if (def_store / 'cache-meta.txt').exists() else ''
        check('version=0.9.1' in before, "default paths: the default store holds the previous build (setup)")
        for v in ('v1n', 'v2n'):
            run(tmp, st, script='build-jar-cache.sh', HOME=str(home), UPDATE_SNAPSHOT=None,
                HYTALE_JAR=str(tmp / v / 'HytaleServer.jar'), HYTALE_JAR_CACHE=str(st / 'scratch-cache'))
        after = (def_store / 'cache-meta.txt').read_text() if (def_store / 'cache-meta.txt').exists() else ''
        check(after == before, "scratch cache: the default store is untouched")
        check((st / 'scratch-cache.snapshot/javap-index.txt').exists(), "scratch cache: its previous build goes to a store beside it")
        # a store that belongs to another cache is never replaced from this one
        run(tmp, st, script='build-jar-cache.sh', HOME=str(home), UPDATE_SNAPSHOT=str(def_store),
            HYTALE_JAR=str(tmp / 'v1n/HytaleServer.jar'), HYTALE_JAR_CACHE=str(st / 'scratch-cache'))
        check((def_store / 'cache-meta.txt').read_text() == before, "a store owned by another cache is NOT replaced")

        # T (r3 LOW-2): the early stamp — a --no-src cache is still stamped, so it is saved as the previous build
        st = tmp / 'T'
        install(tmp, 'v1'); run(tmp, st, '--no-src')
        install(tmp, 'v2'); rc, out, _src, _api, _tri, res = run(tmp, st)
        check('saved the previous build (0.9.1' in out and 'no jar_sha stamp' not in out,
              "--no-src cache: stamped, and saved as the previous build")
        expect_resources('--no-src cache, then a full run', out, res)

        # U (r3 LOW-2): a failed copy, and a failed rename, both leave the cache unwiped
        st = fresh(tmp, 'U'); install(tmp, 'v2')
        victim = next((st / 'cache-jar/src').rglob('*.java')); os.chmod(victim, 0)
        try:
            rc, out, *_ = run(tmp, st)
            check(rc != 0 and 'snapshot copy of src/' in out, "unreadable cache file: the snapshot copy fails at its own guard")
            check('jar_sha=' + sha(tmp / 'v1/HytaleServer.jar') in (st / 'cache-jar/cache-meta.txt').read_text(),
                  "failed snapshot copy: the v1 cache is NOT wiped")
        finally:
            os.chmod(victim, 0o644)
        st = fresh(tmp, 'U2'); install(tmp, 'v2')
        stuck = st / 'snapshot.prev'; (stuck / 'x').mkdir(parents=True); os.chmod(stuck, 0o555)
        try:
            rc, out, *_ = run(tmp, st)
            check(rc != 0 and 'could not move the snapshot into place' in out, "a stuck snapshot.prev: the rename fails at its own guard")
            check('jar_sha=' + sha(tmp / 'v1/HytaleServer.jar') in (st / 'cache-jar/cache-meta.txt').read_text(),
                  "failed snapshot rename: the v1 cache is NOT wiped")
        finally:
            os.chmod(stuck, 0o755)

        # V (r3 LOW-1): a pre-jar_sha snapshot identical to the installed build is flagged
        st = fresh(tmp, 'V')
        shutil.copytree(st / 'cache-jar', st / 'snapshot')
        (st / 'snapshot/class-hashes.txt').unlink()
        m = st / 'snapshot/cache-meta.txt'; m.write_text(re.sub(r'jar_sha=.*\n', '', m.read_text()))
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check('no jar_sha/class hashes/resource hashes to tell them apart' in out, "old-style snapshot identical to the installed build: warned")
        check('could NOT be checked (no class hashes on one side)' in out, "BLIND rows are counted in a WARN")

        # Q (r2 LOW-3): an interrupted copy's leftovers are removed
        st = fresh(tmp, 'Q'); install(tmp, 'v2')
        (st / 'snapshot.new.99999').mkdir()
        run(tmp, st)
        check(not (st / 'snapshot.new.99999').exists(), "leftover snapshot.new.* from an interrupted copy is removed")

        # W (resource-only update): same classes, one migration file changed
        st = fresh(tmp, 'W'); install(tmp, 'v1r')
        rc, out, src, api, tri, res = run(tmp, st)
        check(rc == 0 and res.splitlines() == ['CHANGED hypixel d migration/blocks/3_4.json'],
              "resource-only update: exactly the changed migration file is reported, as Hypixel-owned")
        check(SELF not in out, "resource-only update: the snapshot is NOT called the installed build (SELF absent)")
        check('no signature changes' in out and 'no source changes' in out,
              "resource-only update: the class sections are empty, so the resource section is the only evidence")

        # X (control for W): the same bytes under different zip timestamps are NOT a change
        st = fresh(tmp, 'X'); install(tmp, 'v1t')
        with zipfile.ZipFile(tmp / 'v1/HytaleServer.jar') as a, zipfile.ZipFile(tmp / 'v1t/HytaleServer.jar') as b:
            e1, e2 = a.getinfo('migration/blocks/3_4.json'), b.getinfo('migration/blocks/3_4.json')
            check(e1.date_time != e2.date_time and e1.CRC == e2.CRC and a.read(e1.filename) == b.read(e2.filename),
                  "timestamp control: the jars differ in the entry's zip date and not in a byte")
        check(sha(tmp / 'v1/HytaleServer.jar') != sha(tmp / 'v1t/HytaleServer.jar'), "timestamp control: the two jars differ as files")
        rc, out, src, api, tri, res = run(tmp, st)
        check(rc == 0 and res == '' and 'no resource drift in the' in out,
              "same bytes, different zip timestamps: no resource reported")
        check(SELF in out, "same content in a repacked jar: the identical-snapshot warning still governs")

        # Y: BLIND, in both directions
        st = fresh(tmp, 'Y'); install(tmp, 'v2'); run(tmp, st)
        for f in ('resource-hashes.txt', 'resource-owners.txt'):
            (st / 'snapshot' / f).unlink(missing_ok=True)  # a mutated script may not have written it
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check('BLIND: the previous-build snapshot has no resource-hashes.txt' in out,
              "snapshot without resource hashes: BLIND, said in a WARN")
        check('compared' not in out.split('Resource drift')[1].split('== Triage')[0] and rc == 0,
              "snapshot without resource hashes: no comparison is attempted or claimed")
        st = fresh(tmp, 'Y2'); install(tmp, 'v2'); run(tmp, st)
        (st / 'cache-jar/resource-hashes.txt').unlink(missing_ok=True)
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check('BLIND: the new cache has no resource-hashes.txt' in out, "cache without resource hashes: BLIND, said in a WARN")

        # Z: a snapshot that predates resource hashing, same index and class hashes as the installed build
        st = fresh(tmp, 'Z'); install(tmp, 'v1r'); run(tmp, st)
        for f in ('resource-hashes.txt', 'resource-owners.txt'):
            (st / 'snapshot' / f).unlink(missing_ok=True)  # a mutated script may not have written it
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check('no jar_sha/class hashes/resource hashes to tell them apart' in out,
              "snapshot with class hashes but no resource hashes, identical index: cannot prove it differs, warned")

        # R: the snapshot copy list carries the resource files
        st = fresh(tmp, 'R')
        before = {f: (st / 'cache-jar' / f).read_text() for f in ('resource-hashes.txt', 'resource-owners.txt')}
        check(all(before.values()) and len(before['resource-hashes.txt'].splitlines()) == len(R1) + 1,
              "v1 cache: every non-class entry hashed, nothing filtered (the manifest included)")
        check(all(re.fullmatch(r'[0-9a-f]{64}  \S.*', l) for l in before['resource-hashes.txt'].splitlines()),
              "resource-hashes.txt lines are `sha256  path`")
        install(tmp, 'v2'); run(tmp, st)
        for f, text in before.items():
            check((st / 'snapshot' / f).exists() and (st / 'snapshot' / f).read_text() == text,
                  f"update: snapshot/{f} equals the v1 cache's (so the first real update is not BLIND)")

        # B: the writer's two failure modes stop the build
        st = tmp / 'B'
        rc, out, *_ = run(tmp, st, script='build-jar-cache.sh', HYTALE_JAR=str(tmp / 'v0.jar'))
        check(rc != 0 and "resource hashing wrote '0' entries" in out,
              "a jar with no non-class entry: the build fails (an empty record is not a record)")
        rc, out, *_ = run(tmp, st, script='build-jar-cache.sh', HYTALE_JAR=str(tmp / 'vbad.jar'))
        check(rc != 0 and "could not hash the jar's resources" in out,
              "a resource that cannot be read back: the build fails at its own guard")
        rc, out, *_ = run(tmp, st, script='build-jar-cache.sh', HYTALE_JAR=str(tmp / 'v1/HytaleServer.jar'))
        check(rc == 0 and f'resources hashed: {len(R1) + 1}' in out, "build-jar-cache.sh prints `resources hashed: N`")


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
      + [f'Family/F{i}/Five_Member.json' for i in range(5)] + ['Server/X/A_B.json'])
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
    check(m.rule('Server/X/A_B.json')[0] != 'stem', "rule: a stem shorter than 5 characters is never matched bare")
    check(h('Server/Languages/en-US/server.lang') == ['docs/b.md', 'docs/c.md'], "parent: en-US matches its own citation and the wildcard")
    check(h('Server/Languages/pt-BR/server.lang') == ['docs/c.md'], "parent: pt-BR matches only the wildcard, not an en-US citation")
    check(h('Server/Item/Block/Migrations/1.json') == [], "name: `1.json` does not match inside `Zone1_Plains1.json`")
    check(m.rule('Icons/Items/EditorTools/Entity.png')[0] == 'name', "rule: a unique plain name uses the whole-name rule")
    check(h('Icons/Items/EditorTools/Entity.png') == ['docs/e.md'], "name: whole-name citation matched")
    check(m.rule('Characters/Anim0/Walk_Backward.blockyanim')[0] == 'parent', "rule: an id-shaped stem shared by 6 files is generic")
    check(h('Characters/Anim0/Walk_Backward.blockyanim') == [], "parent: a generic shared name does not match its bare word")

    # Class rows. An anonymous class's simple name is a number: `World$1` searched
    # as the word `1` flagged every gradlew and deploy.bat in the 0.7.2 triage
    # (59 rows). Docs cannot name one, so its change is the enclosing class's body.
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        (t / 'report').mkdir(); (t / 'assets').mkdir()
        (t / 'report/api-changed-classes.txt').write_text(
            'CHANGED a.b.World$1\nCHANGED a.b.Outer$Named\nCHANGED a.b.Lonely$2Local$In\n'
            'CHANGED a.b.Mixed\nCHANGED a.b.Mixed$1\n')  # outer first: its row must survive
        (t / 'report/src-changed-classes.txt').write_text('BODY a.b.Mixed\n')
        for rel, text in {'docs/x.md': 'The `World` guide, step 1.', 'docs/y.md': 'A `Named` thing.',
                          'examples/gradlew': 'exit 1', 'docs/z.md': 'Use `2Local` or `In`.',
                          'docs/m.md': 'The `Mixed` class.'}.items():
            (t / rel).parent.mkdir(parents=True, exist_ok=True); (t / rel).write_text(text)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mod.main(str(t / 'report'), str(t / 'assets'), str(t))
        out = buf.getvalue()
    check('body a.b.World → docs/x.md\n' in out, "triage: an anonymous class is folded onto its enclosing class, as a body change")
    check(not re.search(r'\$\d', out), "triage: no row names an anonymous or local class")
    check('gradlew' not in out and 'docs/z.md' not in out, "triage: a numeric simple name does not flag every file")
    check('class a.b.Outer$Named → docs/y.md\n' in out, "triage: a named nested class is still matched by its simple name")
    check('class a.b.Mixed → docs/m.md\n' in out, "triage: a folded row keeps the enclosing class's own signature change")
    check('#SUMMARY 4 changed' in out, "triage: folded rows are counted once, under the enclosing class")

    # Resource rows: a path inside the jar, keyed by full path, a dir/*.ext wildcard
    # (docs/i18n.md cites `bundledDefaults/*.lang`) or a bare name that is unique
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        (t / 'report').mkdir(); (t / 'assets').mkdir()
        (t / 'assets/CommonAssetsIndex.hashes').write_text(
            '0 Server/Languages/en-US/server.lang\n0 Server/Languages/pt-BR/server.lang\n0 Icons/Thing.png\n')
        (t / 'report/resource-drift.txt').write_text(
            'CHANGED hypixel d bundledDefaults/server.lang\nCHANGED hypixel d migration/blocks/3_4.json\n'
            'ADDED hypixel d cfg/manifests.json\nCHANGED hypixel d x/data.json\nREMOVED hypixel d res/Thing.png\n'
            'CHANGED third-party b native/linux-x64/libx.so\n')
        (t / 'report/resources-all.txt').write_text(
            'bundledDefaults/server.lang\nmigration/blocks/3_4.json\ncfg/manifests.json\nx/data.json\ny/data.json\n'
            'res/Thing.png\nnative/linux-x64/libx.so\n')
        for rel, text in {'docs/p1.md': 'Bundled strings live in `bundledDefaults/*.lang`.',
                          'docs/p2.md': 'Edit `Server/Languages/en-US/server.lang`.',
                          'docs/p3.md': 'Block migrations: `migration/blocks/3_4.json`.',
                          'docs/p4.md': 'See `migration/blocks/{0_1,3_4}.json`.',
                          'docs/p5.md': 'The `manifests.json` index.',
                          'docs/p6.md': 'A `server.lang` file.',
                          'docs/p7.md': 'The `libx.so` library.',
                          'docs/p8.md': 'The `data.json` file.',
                          'docs/p9.md': 'The `Thing.png` icon.',
                          'docs/p10.md': 'Everything under `bundledDefaults/*` ships.',
                          'docs/p11.md': 'Only `migration/blocks/0_1.json` is old.',
                          'docs/p12.md': 'The `bundledDefaults/*.json` files.'}.items():
            (t / rel).parent.mkdir(parents=True, exist_ok=True); (t / rel).write_text(text)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mod.main(str(t / 'report'), str(t / 'assets'), str(t))
        out = buf.getvalue()
    check('resource bundledDefaults/server.lang \u2192 docs/p1.md docs/p10.md\n' in out,
          "resource triage: `bundledDefaults/*.lang` and `bundledDefaults/*` flag a change to bundledDefaults/server.lang, and en-US/server.lang and a bare `server.lang` do not")
    check('docs/p12.md' not in out, "resource triage: `dir/*.json` does not span a .lang file")
    check('resource migration/blocks/3_4.json \u2192 docs/p3.md docs/p4.md\n' in out,
          "resource triage: a full path and a brace list flag the change; another file of the brace's directory does not")
    check('resource cfg/manifests.json \u2192 docs/p5.md\n' in out, "resource triage: a bare name unique among jar resources and shipped assets matches")
    check('docs/p8.md' not in out, "resource triage: a bare name shared by two jar resources does not match")
    check('docs/p9.md' not in out, "resource triage: a bare name that is also a shipped asset does not match")
    check('libx.so' not in out and 'docs/p7.md' not in out, "resource triage: a third-party resource is not triaged")
    check('#SUMMARY 5 changed thing(s) checked, 3 referenced' in out,
          "resource triage: every Hypixel row is counted, and only those with a citing page are referenced")


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
     {"update: change inside a failed decompile (nested class) reported as BYTECODE"}),
    ("r3 LOW-2: bytecode compared on the top-level class only", U,
     'members = [k for k in (oh.keys() | nh.keys()) if k == c or k.startswith(c + "$")]', 'members = [c]',
     {"update: change inside a failed decompile (nested class) reported as BYTECODE"}),
    ("r3 LOW-2: triage ignores BYTECODE rows", T, r'(?:BODY|BYTECODE|BLIND) +(\S+)', r'(?:BODY) +(\S+)',
     {"update: triage flags pages naming a BYTECODE class"}),
    ("r3 LOW-2: no early stamp", B, 'write_meta none\n', '',
     {"--no-src cache: stamped, and saved as the previous build"}),
    ("r3 LOW-2: snapshot copy failure ignored", B,
     '|| { rm -rf "$TMP"; echo "  FAILED: snapshot copy of src/ — the cache is NOT wiped" >&2; exit 4; }', '|| true',
     {"unreadable cache file: the snapshot copy fails at its own guard"}),
    ("r3 LOW-2: snapshot rename failure ignored", B,
     '|| { echo "  FAILED: could not move the snapshot into place at $SNAP — the cache is NOT wiped" >&2; exit 4; }', '|| true',
     {"a stuck snapshot.prev: the rename fails at its own guard"}),
    ("r3 MEDIUM-1: every cache writes the default store", B,
     'else SNAP="$C_ABS.snapshot"; fi', 'else SNAP="$HOME/.cache/hytale-update-snapshot"; fi',
     # not "the default store is untouched": the ownership check below protects it
     # on its own (this mutation first stayed green for that reason), so what only
     # the per-cache default provides is the scratch cache's own record
     {"scratch cache: its previous build goes to a store beside it"}),
    ("r3 MEDIUM-1: store ownership not checked", B,
     '&& [ "$(meta "$SNAP/cache-meta.txt" cache)" != "$C_ABS" ]; then', '&& false; then',
     {"a store owned by another cache is NOT replaced"}),
    ("r3 LOW-1: old-style snapshot self-compare not warned", U,
     'elif { [ -z "$SNAP_SHA" ]', 'elif false && { [ -z "$SNAP_SHA" ]',
     {"old-style snapshot identical to the installed build: warned"}),
    ("r3 LOW-2: id length rule dropped", T, ' and "_" in stem and len(stem) >= 5', ' and "_" in stem',
     {"rule: a stem shorter than 5 characters is never matched bare"}),
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
    ("0.7.2 triage: anonymous classes matched by their numeric name", T,
     'ANON = re.compile(r"\\$\\d.*$")', 'ANON = re.compile(r"(?!)")',
     {"triage: no row names an anonymous or local class", "triage: a numeric simple name does not flag every file",
      "triage: an anonymous class is folded onto its enclosing class, as a body change",
      "triage: folded rows are counted once, under the enclosing class"}),
    ("0.7.2 triage: every nested class folded", T,
     'ANON = re.compile(r"\\$\\d.*$")', 'ANON = re.compile(r"\\$.*$")',
     {"triage: a named nested class is still matched by its simple name"}),
    ("0.7.2 triage: a folded row reported as a signature change", T,
     'classes.setdefault(outer, "body")', 'classes.setdefault(outer, "class")',
     {"triage: an anonymous class is folded onto its enclosing class, as a body change"}),
    ("0.7.2 triage: a folded row overrides the enclosing class's own row", T,
     'classes.setdefault(outer, "body")', 'classes[outer] = "body"',
     {"triage: a folded row keeps the enclosing class's own signature change"}),
    # ---- jar resources (acceptance 8): one mutation per guard, each named by the
    # check that only that guard can turn red
    ("resources: hashed by zip metadata, not content", B,
     'hashlib.sha256(data).hexdigest()}  {n}', 'hashlib.sha256(data + repr(z.getinfo(n).date_time).encode()).hexdigest()}  {n}',
     {"same bytes, different zip timestamps: no resource reported"}),
    ("resources: an allowlist of paths", B,
     'if not n.endswith("/") and not n.endswith(".class"))',
     'if not n.endswith("/") and not n.endswith(".class") and n.startswith(("migration/", "bundledDefaults/")))',
     {"v1 cache: every non-class entry hashed, nothing filtered (the manifest included)"}),
    ("resources rule a: a top-level directory that holds foreign classes", B,
     'elif top in foreign_top:', 'elif False:',
     {"update: resource drift has `CHANGED third-party a com/vendor/messages.properties`"}),
    ("resources rule b: native libraries", B,
     'if n.endswith(NATIVE):', 'if False:',
     {"update: resource drift has `CHANGED third-party b native/linux-x64/libx.so`"}),
    ("resources rule c: META-INF is third-party", B,
     'elif top == "META-INF":', 'elif False:',
     {"update: resource drift has `CHANGED third-party c META-INF/services/vendor.Spi`"}),
    ("resources rule c: a path naming com.hypixel is not enough", B,
     'hyp = "com.hypixel" in n or b"com.hypixel" in data', 'hyp = b"com.hypixel" in data',
     {"update: resource drift has `CHANGED hypixel c META-INF/services/com.hypixel.hytale.demo.Svc`"}),
    ("resources rule c: bytes naming com.hypixel are not enough", B,
     'hyp = "com.hypixel" in n or b"com.hypixel" in data', 'hyp = "com.hypixel" in n',
     {"update: resource drift has `CHANGED hypixel c META-INF/services/other.Spi`"}),
    ("resources rule x: com/hypixel/ is always Hypixel's", B,
     'elif n.startswith("com/hypixel/"):', 'elif False:',
     {"update: resource drift has `CHANGED hypixel x com/hypixel/hytale/demo/data.json`"}),
    ("resources rule e: a directory that mirrors a foreign package", B,
     'elif "/" in n and ("com/" + n.rsplit("/", 1)[0]) in foreign_dirs:', 'elif False:',
     {"update: resource drift has `CHANGED third-party e vendor/lib/schema.proto`"}),
    ("resources rule d: Hypixel-owned is the default", B,
     'owner, rule = "hypixel", "d"', 'owner, rule = "third-party", "d"',
     {"update: resource drift has `ADDED hypixel d brandnew/data.json`"}),
    ("resources: written after the decompile, not before", B,
     'RES_N="$(write_resources)"',
     lambda src: (lambda a, b: src[:a] + src[b:])(*[src.index('RES_N="$(write_resources)"'), src.index('INDEXED="$(grep')]
                  ).replace('step "Done"\n', src[src.index('RES_N="$(write_resources)"'):src.index('INDEXED="$(grep')] + 'step "Done"\n', 1),
     {"broken decompiler: the cache still has the resource hashes (written before the decompile)"}),
    ("resources: the snapshot copy list drops the hashes", B,
     'class-hashes.txt resource-hashes.txt resource-owners.txt cache-meta.txt', 'class-hashes.txt resource-owners.txt cache-meta.txt',
     {"update: snapshot/resource-hashes.txt equals the v1 cache's (so the first real update is not BLIND)"}),
    ("resources: the snapshot copy list drops the owners", B,
     'class-hashes.txt resource-hashes.txt resource-owners.txt cache-meta.txt', 'class-hashes.txt resource-hashes.txt cache-meta.txt',
     {"update: snapshot/resource-owners.txt equals the v1 cache's (so the first real update is not BLIND)"}),
    ("resources: zero entries accepted", B,
     "case \"$RES_N\" in ''|0|*[!0-9]*)", "case \"$RES_N\" in ''|*[!0-9]*)",
     {"a jar with no non-class entry: the build fails (an empty record is not a record)"}),
    ("resources: a writer failure ignored", B,
     '|| { echo "  FAILED: could not hash the jar\'s resources" >&2; exit 5; }', '|| true',
     {"a resource that cannot be read back: the build fails at its own guard"}),
    ("resources: the self-compare test ignores resource hashes", U,
     ' \\\n       && cmp -s "$SNAP/resource-hashes.txt" "$JAR_CACHE/resource-hashes.txt"; }; then', '; }; then',
     {"resource-only update: the snapshot is NOT called the installed build (SELF absent)"}),
    ("resources: a snapshot without resource hashes is not 'old-style'", U,
     ' || [ ! -f "$SNAP/resource-hashes.txt" ]; } && cmp -s "$SNAP/javap-index.txt"', '; } && cmp -s "$SNAP/javap-index.txt"',
     {"snapshot with class hashes but no resource hashes, identical index: cannot prove it differs, warned"}),
    ("resources: a snapshot without resource hashes is not BLIND", U,
     'elif [ ! -f "$OLD_RH" ]; then', 'elif false; then',
     {"snapshot without resource hashes: BLIND, said in a WARN"}),
    ("resources: a cache without resource hashes is not BLIND", U,
     'elif [ ! -f "$NEW_RH" ]; then', 'elif false; then',
     {"cache without resource hashes: BLIND, said in a WARN"}),
    ("resources: a removed resource takes its owner from the new build", U,
     'elif p not in nh: rows.append(("REMOVED", *own(oo, p), p))', 'elif p not in nh: rows.append(("REMOVED", *own(no, p), p))',
     {"update: resource drift has `REMOVED third-party b native/osx-arm64/libgone.dylib`"}),
    ("resources: third-party rows listed one by one", U,
     '    if o == "hypixel": print(f"HYP {st} {r} {p}")', '    print(f"HYP {st} {r} {p}")',
     {"update: third-party resources collapsed to counts, not listed"}),
    ("resources: an unchanged resource reported", U,
     'elif oh[p] != nh[p]: rows.append', 'elif True: rows.append',
     {"update: unchanged resource migration/blocks/0_1.json is not reported"}),
    ("resources: Hypixel rows not listed", U,
     "sed -n 's/^HYP /        /p'", "sed -n 's/^HYPX /        /p'",
     {"update: Hypixel-owned resources listed one by one"}),
    ("resources: the ownership rule and sides not printed", U,
     ";s/^#HOLDS /          holds: /p'", "'",
     {"update: the ownership rule and what each side holds are printed"}),
    ("resources triage: third-party rows are triaged", T,
     'len(parts) == 4 and parts[1] == "hypixel"', 'len(parts) == 4',
     {"resource triage: a third-party resource is not triaged"}),
    ("resources triage: `dir/*.ext` wildcard", T,
     'alts.append(r"(?<![\\w-])" + re.escape(d) + r"/\\*" + wild_ext + RES_END)', 'pass',
     {"resource triage: `bundledDefaults/*.lang` and `bundledDefaults/*` flag a change to bundledDefaults/server.lang, and en-US/server.lang and a bare `server.lang` do not"}),
    ("resources triage: bare `dir/*` wildcard", T,
     'alts.append(r"(?<![\\w-])" + re.escape(d) + r"/\\*(?![\\w*-])")', 'pass',
     {"resource triage: `bundledDefaults/*.lang` and `bundledDefaults/*` flag a change to bundledDefaults/server.lang, and en-US/server.lang and a bare `server.lang` do not"}),
    ("resources triage: brace list", T,
     'alts.append(r"(?<![\\w-])" + re.escape(d) + r"/\\{', 'pass; (r"(?<![\\w-])" + re.escape(d) + r"/\\{',
     {"resource triage: a full path and a brace list flag the change; another file of the brace's directory does not"}),
    ("resources triage: a bare name need not be unique among jar resources", T,
     'if res_names[name] == 1 and asset_names', 'if asset_names',
     {"resource triage: a bare name shared by two jar resources does not match"}),
    ("resources triage: a bare name may also be a shipped asset", T,
     ' and asset_names.get(name, 0) == 0:', ':',
     {"resource triage: a bare name that is also a shipped asset does not match"}),
    ("resources triage: bare names never match", T,
     'if res_names[name] == 1 and asset_names.get(name, 0) == 0:', 'if False:',
     {"resource triage: a bare name unique among jar resources and shipped assets matches"}),
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
            f.write_text(new(src) if callable(new) else src.replace(old, new))
            try:
                r = one_pass(root / 'maintenance/scripts')
            except Exception as e:   # a crash must cost one mutation, not the whole pass
                bad.append(f"{label}: the pass CRASHED ({type(e).__name__}: {e}) - make the case tolerate this mutation's output")
                continue
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
