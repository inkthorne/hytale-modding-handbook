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
Y/Z (BLIND and old-style snapshots), R (snapshot copy list), B (writer failures, including
classes under com/hypixel/ that do not parse), TF (a failing triage stub), RC (a resource
comparison with no result, alone, with a failing triage, and with a python that exits non-zero
after printing its result) and the resource rows of every v1 -> v2 run; one mutation per guard, each named after its check.
DG (the API drift and source drift guards of update-build.sh: states AD = v1 -> v2, with drift, and AI = v1 -> v1r,
without; one injected defect per guard, each expecting its own FAIL line and exit 3; groups [dg1]..[dg5]).

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
import argparse, contextlib, filecmp, hashlib, importlib.util, io, os, pathlib, re, shutil, stat, subprocess, sys, tempfile, zipfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
CFR = pathlib.Path.home() / '.cache/hytale-jar-tools/cfr.jar'

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--mutations', action='store_true')
ap.add_argument('--only', metavar='TEXT', help='with --mutations: run only the mutations whose label contains TEXT (the floors do not apply)')
A = ap.parse_args()

MIN_CHECKS = 799
MIN_MUTATIONS = 130


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
# The strings a Hypixel class holds, for rule l (build-jar-cache.sh): a resource is
# Hypixel's (l) when a constant names its full path or, for a native, its file name,
# delimited on both sides by anything but [A-Za-z0-9._-]. The same constants are in
# v1 and v2: a CHANGED row is Hypixel's if EITHER build says so, which would hide a
# match found by one build only. WHOLE is a whole-constant path whose u2 length is 50,
# so the byte before it in the class file is '2', a name character.
WHOLE = 'META-INF/vendor-whole-' + 'p' * 24 + '.cfg'
assert len(WHOLE) == 50 and chr(len(WHOLE)).isalnum()
LOADS_CONSTANTS = {
    'B': 'libpart.so',                          # a native's file name, as a whole constant
    'C': 'META-INF/vendor-loaded.properties',   # a full path, whole
    'D': 'vendor.Spi',                          # a file name, but not a native
    'E': 'libover.so.1',                        # right edge: libover.so is a prefix of it
    'F': 'xMETA-INF/vendor-left.cfg',           # left edge, full path: preceded by a name character
    'G': '/META-INF/slash-loaded.properties',   # a full path preceded by `/`
    'H': '/native/\\u0001/libindy.so',           # an indy concat recipe, the shape RocksDbNative's "/native/" + dir + "/" + name has in 0.7.2: the file name
    #                                           # preceded by `/`. It pins nothing G does not (both are a `/` delimiter); kept as the real shape
    'I': WHOLE,                                 # a whole path whose length byte is a name character
    'J': 'xlibq.so;libq.so',                    # an embedded libq.so, then a delimited one
}
LOADS = 'public class Loads { ' + ' '.join(f'public static final String {k} = "{v}";' for k, v in LOADS_CONSTANTS.items()) + ' }'
SRC = {
    'v1': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x1000; } public static class Qx { public int a(){return 1;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "old"; } }',
        'Gone': 'public class Gone { public void g(){} }',
        'Dep': 'public class Dep { public void d(){} }',
        'Loads': LOADS,
        'PluginManager': SW % 'old',
    },
    'v2': {
        'BlockHarvestUtils': 'public class BlockHarvestUtils { public static int f(int x){ return x & 0x2000; } public static class Qx { public int a(){return 1;} public int b(){return 2;} } }',
        'KickCommand': 'public class KickCommand { public String run(){ return "new"; } }',
        'Fresh': 'public class Fresh { public void h(){} }',
        'Dep': 'public class Dep { @Deprecated public void d(){} }',
        'Loads': LOADS,
        'PluginManager': SW % 'new',
    },
}


# Non-class jar entries. Each has one job (the rule letters are build-jar-cache.sh's):
#   migration/blocks/3_4.json   Hypixel (d): CHANGED          .../0_1.json: unchanged beside it
#   jwks_bundled.json           Hypixel (d): REMOVED          brandnew/data.json: ADDED, a
#                                            top-level directory the jar has never shown
#   com/hypixel/.../data.json   Hypixel (x): under com/, which ALSO holds a vendor package
#   com/hypixel/hytale/lib/libhyt.so   Hypixel (x): a native under com/hypixel/ (not b)
#   META-INF/services/...Svc    Hypixel (h): its PATH names com.hypixel
#   META-INF/services/other.Spi Hypixel (h): its BYTES name com.hypixel
#   META-INF/services/lost.Spi  Hypixel (h): names com.hypixel in v1 only (the OLD build says so)
#   META-INF/services/gained.Spi Hypixel (h): names com.hypixel in v2 only (the NEW build says so)
#   META-INF/services/vendor.Spi third-party (c): a Hypixel class names "vendor.Spi", but only its
#                                            file name, which is not enough off a native
#   native/linux-x64/libbranded.so Hypixel (h): bytes carry "Hypixel Studios Canada Inc"
#   native/osx-arm64/libbuild.dylib Hypixel (h): bytes carry only the build path ".../hytale/hytale/"
#   native/linux-x64/libpart.so    Hypixel (l): Loads names its file name only, not its path (a native)
#   META-INF/vendor-loaded.properties Hypixel (l): Loads names its full path (a non-native)
# Rule l is a WHOLE-name test (the byte before and after the match is not in
# [A-Za-z0-9._-]), one predicate for a full path and a file name. Each edge has a case
# that must stay third-party and one that must be Hypixel's:
#   native/linux-arm64/part.so      third-party (b): only inside `libpart.so` (left edge, file name)
#   native/linux-arm64/libover.so   third-party (b): only a prefix of `libover.so.1` (right edge, file name)
#   META-INF/vendor-loaded.prop     third-party (c): a prefix of `META-INF/vendor-loaded.properties` (right edge, path)
#   META-INF/vendor-left.cfg        third-party (c): only inside `xMETA-INF/vendor-left.cfg` (left edge, path)
#   META-INF/slash-loaded.properties Hypixel (l): inside `/META-INF/slash-loaded.properties` (a `/` delimits)
#   native/linux-arm64/libindy.so   Hypixel (l): inside `/native/\u0001/libindy.so` (an indy recipe)
#   META-INF/vendor-whole-ppp...cfg Hypixel (l): a whole constant of length 50; a delimiter test on the RAW
#                                   class bytes sees its u2 length byte, '2', and refuses it
#   native/linux-arm64/libq.so      Hypixel (l): `xlibq.so;libq.so` holds an embedded libq.so BEFORE a delimited one
#   com/vendor/branded.properties  Hypixel (h): under a vendor package (a), but the bytes say HYPIXEL
#   native/linux-x64/libx.so, win-x64/x.dll, osx-arm64/libgone.dylib   third-party (b): CHANGED/ADDED/REMOVED
#   com/vendor/messages.properties   third-party (a): com/ holds com/vendor/lib/Ext.class
#   vendor/lib/schema.proto          third-party (e): beside com/vendor/lib/Ext.class
R1 = {
    'migration/blocks/0_1.json': b'{"from":0}\n',
    'migration/blocks/3_4.json': b'{"to":4,"map":"a"}\n',
    'bundledDefaults/server.lang': b'hello = Hello\n',
    'jwks_bundled.json': b'{"keys":[]}\n',
    'update/start.sh': b'#!/bin/sh\n',
    'com/hypixel/hytale/demo/data.json': b'{"x":1}\n',
    'com/hypixel/hytale/lib/libhyt.so': b'\x7fELF-a',
    'META-INF/services/com.hypixel.hytale.demo.Svc': b'impl-a\n',
    'META-INF/services/other.Spi': b'com.hypixel.hytale.demo.Dep\n',
    'META-INF/services/lost.Spi': b'com.hypixel.hytale.demo.Dep\n',
    'META-INF/services/gained.Spi': b'org.vendor.ImplA\n',
    'META-INF/services/vendor.Spi': b'org.vendor.ImplA\n',
    'META-INF/vendor-loaded.properties': b'a=1\n',
    'native/linux-x64/libx.so': b'\x7fELF-a',
    'native/linux-x64/libbranded.so': b'\x7fELF-Hypixel Studios Canada Inc-a',
    'native/osx-arm64/libbuild.dylib': b'\xcf\xfa/home/runner/work/hytale/hytale/ThirdParty-a',
    'native/linux-x64/libpart.so': b'\x7fELF-a',
    'native/linux-arm64/part.so': b'\x7fELF-a',
    'native/linux-arm64/libover.so': b'\x7fELF-a',
    'META-INF/vendor-loaded.prop': b'a=1\n',
    'META-INF/vendor-left.cfg': b'a=1\n',
    'META-INF/slash-loaded.properties': b'a=1\n',
    'native/linux-arm64/libindy.so': b'\x7fELF-a',
    WHOLE: b'a=1\n',
    'native/linux-arm64/libq.so': b'\x7fELF-a',
    'native/osx-arm64/libgone.dylib': b'gone',
    'com/vendor/messages.properties': b'a=1\n',
    'com/vendor/branded.properties': b'# HYPIXEL a\n',
    'vendor/lib/schema.proto': b'syntax = "proto3"; // a\n',
}
R2 = {k: v for k, v in R1.items() if k not in ('jwks_bundled.json', 'native/osx-arm64/libgone.dylib')}
R2.update({
    'migration/blocks/3_4.json': b'{"to":4,"map":"b"}\n',
    'brandnew/data.json': b'{"new":true}\n',
    'com/hypixel/hytale/demo/data.json': b'{"x":2}\n',
    'com/hypixel/hytale/lib/libhyt.so': b'\x7fELF-b',
    'META-INF/services/com.hypixel.hytale.demo.Svc': b'impl-b\n',
    'META-INF/services/other.Spi': b'com.hypixel.hytale.demo.Fresh\n',
    'META-INF/services/lost.Spi': b'org.vendor.ImplB\n',
    'META-INF/services/gained.Spi': b'com.hypixel.hytale.demo.Fresh\n',
    'META-INF/services/vendor.Spi': b'org.vendor.ImplB\n',
    'META-INF/vendor-loaded.properties': b'a=2\n',
    'native/linux-x64/libx.so': b'\x7fELF-b',
    'native/linux-x64/libbranded.so': b'\x7fELF-Hypixel Studios Canada Inc-b',
    'native/osx-arm64/libbuild.dylib': b'\xcf\xfa/home/runner/work/hytale/hytale/ThirdParty-b',
    'native/linux-x64/libpart.so': b'\x7fELF-b',
    'native/win-x64/x.dll': b'MZ',
    'native/linux-arm64/part.so': b'\x7fELF-b',
    'native/linux-arm64/libover.so': b'\x7fELF-b',
    'META-INF/vendor-loaded.prop': b'a=2\n',
    'META-INF/vendor-left.cfg': b'a=2\n',
    'META-INF/slash-loaded.properties': b'a=2\n',
    'native/linux-arm64/libindy.so': b'\x7fELF-b',
    WHOLE: b'a=2\n',
    'native/linux-arm64/libq.so': b'\x7fELF-b',
    'com/vendor/messages.properties': b'a=2\n',
    'com/vendor/branded.properties': b'# HYPIXEL b\n',
    'vendor/lib/schema.proto': b'syntax = "proto3"; // b\n',
})
R1R = dict(R1, **{'migration/blocks/3_4.json': b'{"to":4,"map":"r"}\n'})
VENDOR = 'package com.vendor.lib; public class Ext { public int e(){ return 1; } }\n'
D1, D2 = (2020, 1, 2, 3, 4, 6), (2021, 5, 6, 7, 8, 10)     # zip entry timestamps
RES_DRIFT_V1_V2 = [   # state owner rule path: the whole resource drift of v1 -> v2
    'CHANGED hypixel d migration/blocks/3_4.json', 'REMOVED hypixel d jwks_bundled.json',
    'ADDED hypixel d brandnew/data.json', 'CHANGED hypixel x com/hypixel/hytale/demo/data.json',
    'CHANGED hypixel x com/hypixel/hytale/lib/libhyt.so',
    'CHANGED hypixel h META-INF/services/com.hypixel.hytale.demo.Svc', 'CHANGED hypixel h META-INF/services/other.Spi',
    'CHANGED hypixel h META-INF/services/lost.Spi', 'CHANGED hypixel h META-INF/services/gained.Spi',
    'CHANGED third-party c META-INF/services/vendor.Spi', 'CHANGED hypixel l META-INF/vendor-loaded.properties',
    'CHANGED third-party b native/linux-x64/libx.so', 'CHANGED hypixel h native/linux-x64/libbranded.so',
    'CHANGED hypixel h native/osx-arm64/libbuild.dylib',
    'CHANGED hypixel l native/linux-x64/libpart.so',
    'CHANGED third-party b native/linux-arm64/part.so', 'CHANGED third-party b native/linux-arm64/libover.so',
    'CHANGED third-party c META-INF/vendor-loaded.prop', 'CHANGED third-party c META-INF/vendor-left.cfg',
    'CHANGED hypixel l META-INF/slash-loaded.properties', 'CHANGED hypixel l native/linux-arm64/libindy.so',
    f'CHANGED hypixel l {WHOLE}', 'CHANGED hypixel l native/linux-arm64/libq.so',
    'ADDED third-party b native/win-x64/x.dll', 'REMOVED third-party b native/osx-arm64/libgone.dylib',
    'CHANGED third-party a com/vendor/messages.properties', 'CHANGED hypixel h com/vendor/branded.properties',
    'CHANGED third-party e vendor/lib/schema.proto',
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
            if (not manifest and info.filename.startswith('META-INF')) or info.filename in resources:
                continue     # an entry given in `resources` replaces the base's own
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
    # jars with ONE class under com/hypixel/ that does not parse, each by exactly one defect
    gone = zipfile.ZipFile(tmp / 'v1/base.jar').read(f'{P}/Gone.class')
    # where Gone's constant pool ends, by a walk of this fixture's own (not the script's)
    cp_count, pool_end, i = int.from_bytes(gone[8:10], 'big'), 10, 1
    while i < cp_count:
        tag = gone[pool_end]; pool_end += 1
        if tag == 1:
            pool_end += 2 + int.from_bytes(gone[pool_end:pool_end + 2], 'big')
        else:
            pool_end += {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4, 12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}[tag]
            i += 1 if tag in (5, 6) else 0
        i += 1
    for name, entries in (
            ('junk', {'com/hypixel/hytale/Bad.class': b'junk'}),
            ('magic', {f'{P}/Gone.class': b'\xda' + gone[1:]}),               # only the first byte differs
            ('alias', {f'{P}/Alias.class': gone}),                              # parses; this_class says Gone
            ('cut', {f'{P}/Gone.class': gone[:40]}),                            # ends inside the constant pool
            ('tag2', {f'{P}/Gone.class': gone[:8] + (cp_count + 1).to_bytes(2, 'big') + gone[10:pool_end] + b'\x02' + gone[pool_end:]}),
            ('poolend', {f'{P}/Gone.class': gone[:pool_end]})):                 # ends exactly where the pool ends
        pack(tmp / 'v1/base.jar', tmp / f'vclass-{name}.jar', entries, D1)
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
    # the printed rule text is the reader's only key to the letters in `rules d:10 h:7 ...`
    # and once printed a rule the writer no longer had (a native is always third-party)
    own_line = next((l for l in out.splitlines() if 'ownership: Hypixel' in l), '')
    letters = set(re.findall(r'(?<![\w/])([a-z]):\d+', '\n'.join(l for l in out.splitlines() if ' rules ' in l)))
    check(letters == set('xdhlbcae') and all(f' {c}: ' in own_line or f'({c}: ' in own_line for c in letters),
          f"{label}: the printed ownership rule describes every rule letter the owners file uses")


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
    check('compared 5 file(s) present in both builds (1 only in the old, 1 only in the new); 3 changed; '
          '1 unchanged file(s) contain a failed decompile' in out, f"{label}: source-drift denominator printed")
    check(SELF not in out, f"{label}: no self-compare warning")
    check('UNEXPLAINED' not in src, f"{label}: every one-sided file is an added/removed class")


def fresh(tmp, name, first='v1'):
    st = tmp / name
    install(tmp, first); run(tmp, st)
    return st


def with_edit(tmp, name, edits):
    """A copy of the scripts whose update-build.sh has each (old, new) edit applied, for a case
    that injects a defect upstream of a guard. Every `old` must occur exactly once: a count is
    a check, so a mutation that moves the injection site fails here and not silently."""
    root = tmp / f'stub-{name}/maintenance/scripts'
    shutil.copytree(R.scripts, root, ignore=shutil.ignore_patterns('__pycache__'))
    ub = (root / 'update-build.sh').read_text()
    check(all(ub.count(old) == 1 for old, _ in edits), f"{name}: the injection site is where the case expects it, once (setup)")
    for old, new in edits:
        ub = ub.replace(old, new)
    (root / 'update-build.sh').write_text(ub)
    return root


def run_with(tmp, st, root, *args, **over):
    real, R.scripts = R.scripts, root
    try:
        return run(tmp, st, *args, **over)
    finally:
        R.scripts = real


def diff_wrapper(tmp, name, pattern):
    """A directory for PATH whose `diff` exits 2 (trouble) for arguments matching the sh case
    PATTERN and is the real diff otherwise: the only way to make diff itself fail on demand."""
    d = tmp / f'diffwrap-{name}'
    d.mkdir()
    (d / 'diff').write_text(f'#!/bin/sh\ncase "$*" in {pattern}) exit 2;; esac\nexec {shutil.which("diff")} "$@"\n')
    (d / 'diff').chmod(0o755)
    return {'PATH': f"{d}:{os.environ['PATH']}"}


DG_BUILD = {'AD': 'v2', 'AI': 'v1r'}      # state -> the build installed over it


def CN(i, kind):
    return f"drift guard {i}: {kind}"


SETS_RENAME = "drift guards: indexes that differ only by a `Compiled from` line and a member order report no FAIL (sets compared)"
SETS_ORDER = "drift guards: indexes that differ only by a member order report no FAIL (sorted)"
CTRL_STRIP = "drift guards: control on real drift: both marker lines are stripped, the rows are kept"


def drift_case(tmp, st, i, edits=(), msg='', absent='', over=None, info=None):
    """One guard: run update-build.sh --skip-caches on the state with the defect injected (or
    PATH wrapped, `over`) and read what the guard says. msg is a regex for the guard's OWN
    message: every guard of a section has a distinct one and a case asserts only its own, so a
    mutation that drops the guard cannot stay red through the next one in the chain. The
    section's 'no changes' line must be absent: it is the defect (a silent loss reads as it)."""
    install(tmp, DG_BUILD[st.name])        # the installed jar is the one the state's cache was built from
    if info is None:
        info = i.startswith('API')         # a failed API drift is said, in the source drift, by every one of its guards
    root = with_edit(tmp, i, list(edits)) if edits else R.scripts
    rc, out, *_ = run_with(tmp, st, root, '--skip-caches', **(over or {}))
    fails = re.findall(r'FAIL\S*\s+(.*)', out)
    check(any(re.search(msg, f) for f in fails), CN(i, "FAIL line has its own message"))
    check(len(fails) == 1, CN(i, f"it is the only FAIL line (got {len(fails)})"))
    check(rc == 3, CN(i, f"exit 3 even with --no-verify (got {rc})"))
    check(absent not in out, CN(i, f"the `{absent}` line is not printed"))
    sect5b = out.split('Source drift')[1].split('== Resource drift')[0] if 'Source drift' in out else ''
    check(('section 5) failed' in sect5b) == info, CN(i, "source drift says the API drift failed" if info else "source drift does not claim the API drift failed"))
    return out


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

        # TF: a triage that cannot read its report fails the run. A stub stands in for it (a real
        # one needs a hand-made bad report, and update-build.sh rewrites the report each run);
        # --no-verify, which every fixture run uses, is the exit the status must survive. Every
        # soft failure exits 3, whichever it is (the header of update-build.sh says why one code).
        st = fresh(tmp, 'TF'); install(tmp, 'v2')
        stub = tmp / 'stubroot/maintenance/scripts'
        shutil.copytree(R.scripts, stub, ignore=shutil.ignore_patterns('__pycache__'))
        real_scripts = R.scripts
        try:
            R.scripts = stub
            for code in (0, 2, 1):
                (stub / 'triage_drift.py').write_text(f'import sys\nprint("stub triage")\nsys.exit({code})\n')
                rc, out, *_ = run(tmp, st)
                if code == 0:
                    check(rc == 0 and 'triage_drift.py exited' not in out, "triage exits 0: update-build.sh exits 0, no FAIL")
                elif code == 2:
                    check(re.search(r'FAIL\S*\s+triage_drift\.py exited 2 \u2014 it could not read the report in full, so the triage shown is INCOMPLETE', out)
                          and 'stub triage' in out,
                          "triage exit (update-build): a triage exiting 2 is a FAIL line, after the partial triage it printed")
                    check(rc == 3, "triage exit (update-build): a triage exiting 2 makes update-build.sh exit 3, even with --no-verify")
                else:
                    check(re.search(r'FAIL\S*\s+triage_drift\.py exited 1 \u2014 it crashed or was killed', out) and 'INCOMPLETE' not in out,
                          "triage exit (update-build): a triage that crashes (exit 1) is a FAIL line saying so, not the unreadable-report one")
                    check(rc == 3, "triage exit (update-build): a triage that crashes exits 3, not 1 (verify-docs.sh's code)")
        finally:
            R.scripts = real_scripts

        # RC: a resource comparison that produces no result is a FAIL and exit 3. A malformed
        # line in the cache's owners file makes the comparison's python raise (no #COUNTS); the run
        # carries on to the end (triage included), so the status must outlive --no-verify.
        st = fresh(tmp, 'RC'); install(tmp, 'v2'); run(tmp, st)
        owners = st / 'cache-jar/resource-owners.txt'
        check(owners.exists(), "update-build exit: the cache has the owners file the case corrupts (setup)")
        if owners.exists():
            with open(owners, 'a') as f:
                f.write('garbage\n')
        rc, out, *_ = run(tmp, st, '--skip-caches')
        check(re.search(r'FAIL\S*\s+the resource comparison produced no result', out),
              "update-build exit: a resource comparison with no result is a FAIL line")
        parts = out.split('Resource drift')
        check(len(parts) > 1 and 'Triage: docs/examples' in out and 'compared' not in parts[1].split('== Triage')[0],
              "update-build exit: the run goes on past the failed comparison, which claims no comparison")
        check(rc == 3, "update-build exit: a resource comparison with no result makes update-build.sh exit 3, even with --no-verify")
        # both soft failures in one run: both FAIL lines, one exit code
        try:
            R.scripts = stub
            (stub / 'triage_drift.py').write_text('import sys\nprint("stub triage")\nsys.exit(2)\n')
            rc, out, *_ = run(tmp, st, '--skip-caches')
        finally:
            R.scripts = real_scripts
        check(re.search(r'FAIL\S*\s+the resource comparison produced no result', out)
              and re.search(r'FAIL\S*\s+triage_drift\.py exited 2', out) and rc == 3,
              "update-build exit: a failed comparison and a failed triage in one run print both FAIL lines and exit 3")
        # a comparison whose python prints its result and THEN exits non-zero is no result either
        st = fresh(tmp, 'RC3'); install(tmp, 'v2')
        stub2 = tmp / 'stubroot2/maintenance/scripts'
        shutil.copytree(R.scripts, stub2, ignore=shutil.ignore_patterns('__pycache__'))
        ub = (stub2 / 'update-build.sh').read_text()
        tail = 'for (st, k), v in sorted(tp.items()): print(f"TP {st} {k} {v}")\n'
        check(ub.count(tail) == 1, "update-build exit: the comparison's last python line is where the case injects its exit (setup)")
        (stub2 / 'update-build.sh').write_text(ub.replace(tail, tail + 'sys.exit(4)\n'))
        try:
            R.scripts = stub2
            rc, out, *_ = run(tmp, st)
        finally:
            R.scripts = real_scripts
        check(re.search(r'FAIL\S*\s+the resource comparison produced no result', out) and rc == 3,
              "update-build exit: a resource comparison whose python exits non-zero is a failure even if it printed #COUNTS")

        # DG: the API drift (5) and source drift (5b) cannot report "no changes" for a result they
        # did not produce. AD (v1 -> v2) has real drift in both sections; AI (v1 -> v1r) has none
        # in either, so there "no signature changes" / "no source changes" are the true answers
        # and a guard that drops out lets them through. Every case injects ONE defect upstream
        # of ONE guard (a python that exits 0 and prints its marker with no rows, a diff that
        # exits 2) and expects that guard's own message and no other FAIL line.
        AD = fresh(tmp, 'AD'); install(tmp, 'v2'); run(tmp, AD)
        AI = fresh(tmp, 'AI'); install(tmp, 'v1r'); run(tmp, AI)
        NOSIG, NOSRC = 'no signature changes', 'no source changes'
        # controls: the unmodified script on both states
        install(tmp, 'v2'); rc, out, src, api, *_ = run(tmp, AD, '--skip-caches')
        check(rc == 0 and 'FAIL' not in out and 'section 5) failed' not in out, "drift guards: control on real drift: exit 0, no FAIL, no claim of a failed API drift")
        check('#COUNTS' not in api and '#COUNTS' not in src and f'CHANGED {D}BlockHarvestUtils$Qx' in api and f'DEPRECATION added   {D}Dep' in src,
              "drift guards: control on real drift: both marker lines are stripped, the rows are kept")
        install(tmp, 'v1r'); rc, out, src, api, *_ = run(tmp, AI, '--skip-caches')
        check(rc == 0 and 'FAIL' not in out and NOSIG in out and NOSRC in out and api == '',
              "drift guards: control without drift: exit 0, no FAIL, both 'no changes' lines")
        M5 = 'print(f"#COUNTS {len(old)} {len(new)} {rows}")\n'
        M5B = 'print(f"#COUNTS {len(common)} {len(old.keys() - new.keys())} {len(new.keys() - old.keys())} {len(changed)} {len(blind)}")\n'
        # --- section 5
        drift_case(tmp, AI, 'API-01', msg=r'API drift: diff of the javap indexes exited 2', absent=NOSIG,
                   over=diff_wrapper(tmp, 'javap', '*javap-index*'))
        drift_case(tmp, AI, 'API-02', [(M5, M5 + 'sys.exit(4)\n')], r'API drift: the python exited 4', NOSIG)
        drift_case(tmp, AI, 'API-03', [(M5, 'pass\n')], r'API drift: the python printed 0 well-formed #COUNTS marker line\(s\), not one', NOSIG)
        drift_case(tmp, AI, 'API-03b', [(M5, M5 + M5)], r'API drift: the python printed 2 well-formed #COUNTS marker line\(s\), not one', NOSIG)
        drift_case(tmp, AI, 'API-03c', [(M5, 'print("#COUNTS 1 2")\n')], r'API drift: the python printed 0 well-formed #COUNTS marker line\(s\), not one', NOSIG)
        drift_case(tmp, AD, 'API-04', [(M5, M5.replace('{rows}', '{rows + 1}'))],
                   r'API drift: the python says it wrote \d+ row\(s\) but api-changed-classes\.txt holds \d+', NOSIG)
        # an index with no class: either side (restored afterwards). Without the guard the python
        # parses 0 = 0 and reports every class of the other build as added or removed
        for side, f in (('old', AI / 'snapshot/javap-index.txt'), ('new', AI / 'cache-jar/javap-index.txt')):
            keep = f.read_text(); f.write_text('')
            try:
                drift_case(tmp, AI, 'API-05' + ('' if side == 'old' else 'b'),
                           msg=r'API drift: an index holds no class \(javap closes ' + ('0 in the old index, \\d+' if side == 'old' else '\\d+ in the old index, 0') + r' in the new', absent=NOSIG)
            finally:
                f.write_text(keep)
        drift_case(tmp, AD, 'API-06', [('decl = re.compile(r\'(?:class|interface|enum|record) +([\\w.$]+)\')\n', "decl = re.compile(r'(?!)')\n")],
                   r'API drift: the python parsed 0 class\(es\) from the old index but javap closes \d+', NOSIG)
        drift_case(tmp, AD, 'API-07', [('old, new = members(sys.argv[1]), members(sys.argv[2])\n',
                                         'old, new = members(sys.argv[1]), members(sys.argv[2])\nnew = dict(list(new.items())[1:])\n')],
                   r'API drift: the python parsed \d+ class\(es\) from the new index but javap closes \d+', NOSIG)
        out = drift_case(tmp, AD, 'API-08', [('for cls in sorted(old.keys() | new.keys()):\n', 'for cls in []:\n')],
                         r'API drift: the javap indexes differ but the python found no class added, removed or changed', NOSIG)
        check('Source drift' in out and '== Triage' in out, CN('API-08', "the run goes on to the source drift and the triage"))
        # --- section 5b
        drift_case(tmp, AI, 'SRC-01', msg=r'source drift: diff -ru of the decompiled trees exited 2', absent=NOSRC,
                   over=diff_wrapper(tmp, 'ru', '-ru\\ *'))
        drift_case(tmp, AI, 'SRC-02', [(M5B, M5B + 'sys.exit(4)\n')], r'source drift: the python exited 4', NOSRC)
        drift_case(tmp, AI, 'SRC-03', [(M5B, 'pass\n')], r'source drift: the python printed 0 well-formed #COUNTS marker line\(s\), not one', NOSRC)
        drift_case(tmp, AI, 'SRC-03b', [(M5B, M5B + M5B)], r'source drift: the python printed 2 well-formed #COUNTS marker line\(s\), not one', NOSRC)
        drift_case(tmp, AI, 'SRC-03c', [(M5B, 'print("#COUNTS 1 2 3")\n')], r'source drift: the python printed 0 well-formed #COUNTS marker line\(s\), not one', NOSRC)
        W5B = 'old, new = files(old_root), files(new_root)\n'
        drift_case(tmp, AI, 'SRC-04', [(W5B, W5B + 'old.pop(sorted(old)[0])\n')],
                   r'source drift: the python counted \d+ \.java file\(s\) in the old tree but find counts \d+', NOSRC)
        drift_case(tmp, AI, 'SRC-05', [(W5B, W5B + 'new.pop(sorted(new)[0])\n')],
                   r'source drift: the python counted \d+ \.java file\(s\) in the new tree but find counts \d+', NOSRC)
        drift_case(tmp, AD, 'SRC-06', [('changed = sorted(c for c in common if not filecmp.cmp(old[c], new[c], shallow=False))\n', 'changed = []\n')],
                   r'source drift: src-drift\.diff has \d+ changed \.java file header\(s\) but the python reports only 0 changed file', NOSRC)
        drift_case(tmp, AD, 'SRC-07', [("print(f\"DEPRECATION {'added  ' if line[0] == '+' else 'removed'} {cur}: {line[1:].strip()}\")", 'pass')],
                   r'source drift: src-drift\.diff has 1 added/removed @Deprecated line\(s\) but the python wrote 0 DEPRECATION row', NOSRC)
        # --- the set comparison of section 5 (check 8): two indexes that differ as FILES but not
        # as sets of lines (a source-file name changed, two members swapped) have nothing to report
        install(tmp, 'v1r')
        f = AI / 'snapshot/javap-index.txt'
        lines = f.read_text().split('\n')
        k_cf = next((n for n, l in enumerate(lines) if l.startswith('Compiled from "')), None)
        k_sw = next((n for n in range(len(lines) - 1) if lines[n].startswith(' ') and lines[n + 1].startswith(' ') and lines[n] != lines[n + 1]), None)
        check(k_cf is not None and k_sw is not None, "drift guards: the index has a `Compiled from` line and two adjacent members to perturb (setup)")
        if k_cf is not None and k_sw is not None:
            lines[k_cf] = 'Compiled from "Renamed.java"'
            lines[k_sw], lines[k_sw + 1] = lines[k_sw + 1], lines[k_sw]
            f.write_text('\n'.join(lines))
            check(not filecmp.cmp(f, AI / 'cache-jar/javap-index.txt', shallow=False), "drift guards: the perturbed indexes differ as files (setup)")
            rc, out, *_ = run(tmp, AI, '--skip-caches')
            check(rc == 0 and 'FAIL' not in out and NOSIG in out,
                  "drift guards: indexes that differ only by a `Compiled from` line and a member order report no FAIL (sets compared)")
            # each half alone: the rename without the swap, the swap without the rename
            lines[k_cf] = next(l for l in (AI / 'cache-jar/javap-index.txt').read_text().split('\n') if l.startswith('Compiled from "'))
            f.write_text('\n'.join(lines))
            rc, out, *_ = run(tmp, AI, '--skip-caches')
            check(rc == 0 and 'FAIL' not in out and NOSIG in out, "drift guards: indexes that differ only by a member order report no FAIL (sorted)")

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
        with zipfile.ZipFile(tmp / 'v1/HytaleServer.jar') as zj:
            n_pools = sum(1 for n in zj.namelist() if n.startswith('com/hypixel/') and n.endswith('.class'))
        check(n_pools > len(SRC['v1']) and f'rule l read {n_pools} constant pool(s)' in out,
              "build-jar-cache.sh prints how many constant pools rule l read (every class under com/hypixel/, nested included)")

        # a class under com/hypixel/ that does not parse stops the build: its constants would be
        # dropped, and every resource it names filed third-party. --no-src: nothing before the
        # resource writer reads the class (javap's stderr goes to /dev/null, the class hashes only hash)
        for name, why, entry, reason in (
                ('junk', 'not a class file at all', 'Bad.class', 'bad magic'),
                ('magic', 'a class whose first byte is wrong', 'Gone.class', 'bad magic'),
                ('alias', 'a class whose this_class names another entry', 'Alias.class', 'this_class does not name the entry'),
                ('cut', 'a class cut inside its constant pool', 'Gone.class', 'the constant pool runs past the end'),
                ('tag2', 'a class whose pool holds an entry with the unused tag 2', 'Gone.class', 'unknown constant tag 2'),
                ('poolend', 'a class cut exactly where its constant pool ends', 'Gone.class', 'the constant pool runs past the end')):
            rc, out, *_ = run(tmp, st, '--no-src', script='build-jar-cache.sh', HYTALE_JAR=str(tmp / f'vclass-{name}.jar'))
            check(rc == 5 and "could not hash the jar's resources" in out
                  and re.search(rf'{entry}: not a parseable class file \({re.escape(reason)}\)', out),
                  f"{why}: the build fails with exit 5, naming the class and `{reason}`")


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
            'CHANGED third-party b native/linux-x64/libx.so\n'
            # a resource that MOVED between builds, one whose name stopped being ambiguous
            # (m/shared.json removed) and one that became ambiguous (q/other.json added)
            'REMOVED hypixel d cfg/moved.json\nADDED hypixel d auth/moved.json\n'
            'CHANGED hypixel d k/shared.json\nREMOVED hypixel d m/shared.json\n'
            'CHANGED hypixel d n/other.json\nADDED hypixel d q/other.json\n'
            'REMOVED hypixel d cfg/gone.json\nADDED hypixel d cfg/fresh.json\n')
        common = ('bundledDefaults/server.lang\nmigration/blocks/3_4.json\nx/data.json\ny/data.json\n'
                  'res/Thing.png\nnative/linux-x64/libx.so\nk/shared.json\nn/other.json\n')
        (t / 'report/resources-old.txt').write_text(common + 'cfg/moved.json\nm/shared.json\ncfg/gone.json\n')
        (t / 'report/resources-new.txt').write_text(common + 'cfg/manifests.json\nauth/moved.json\nq/other.json\ncfg/fresh.json\n')
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
                          'docs/p12.md': 'The `bundledDefaults/*.json` files.',
                          'docs/p13.md': 'The `moved.json` file.',
                          'docs/p14.md': 'The `shared.json` file.',
                          'docs/p15.md': 'The `other.json` file.',
                          'docs/p16.md': 'The `bundledDefaults/*/sub` tree.',
                          'docs/p17.md': 'The `bundledDefaults/*.lang/sub` tree.',
                          'docs/p18.md': 'The `gone.json` file.',
                          'docs/p19.md': 'The `fresh.json` file.'}.items():
            (t / rel).parent.mkdir(parents=True, exist_ok=True); (t / rel).write_text(text)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.main(str(t / 'report'), str(t / 'assets'), str(t))
        out = buf.getvalue()
    check(rc == 0, "resource triage: a complete report (every Hypixel row's path in the lists it needs) exits 0")
    m = re.search(r'^resource bundledDefaults/server\.lang \u2192 (.*)$', out, re.M)
    hits = m.group(1).split() if m else []
    check(bool(hits) and 'docs/p1.md' in hits,
          "resource triage: `bundledDefaults/*.lang` flags a change to bundledDefaults/server.lang")
    check(bool(hits) and 'docs/p10.md' in hits,
          "resource triage: `bundledDefaults/*` flags a change to bundledDefaults/server.lang")
    check(bool(hits) and 'docs/p2.md' not in hits and 'docs/p6.md' not in hits,
          "resource triage: en-US/server.lang and a bare `server.lang` do not flag a change to bundledDefaults/server.lang")
    check(bool(hits) and 'docs/p16.md' not in hits,
          "resource triage: `bundledDefaults/*/sub` is not `bundledDefaults/*`")
    check(bool(hits) and 'docs/p17.md' not in hits,
          "resource triage: `bundledDefaults/*.lang/sub` is not `bundledDefaults/*.lang`")
    check('docs/p12.md' not in out, "resource triage: `dir/*.json` does not span a .lang file")
    check('resource migration/blocks/3_4.json \u2192 docs/p3.md docs/p4.md\n' in out,
          "resource triage: a full path and a brace list flag the change; another file of the brace's directory does not")
    check('resource cfg/manifests.json \u2192 docs/p5.md\n' in out, "resource triage: a bare name unique among jar resources and shipped assets matches")
    check('docs/p8.md' not in out, "resource triage: a bare name shared by two jar resources does not match")
    check('docs/p9.md' not in out, "resource triage: a bare name that is also a shipped asset does not match")
    check('libx.so' not in out and 'docs/p7.md' not in out, "resource triage: a third-party resource is not triaged")
    check('resource cfg/moved.json \u2192 docs/p13.md\n' in out,
          "resource triage: a bare name is tested in the OLD build for a REMOVED row, so a resource that moved is still flagged")
    check('resource cfg/gone.json \u2192 docs/p18.md\n' in out,
          "resource triage: a REMOVED row's bare name that exists only in the old build is flagged")
    check('resource cfg/fresh.json \u2192 docs/p19.md\n' in out,
          "resource triage: an ADDED row's bare name that exists only in the new build is flagged")
    check('resource auth/moved.json \u2192 docs/p13.md\n' in out,
          "resource triage: a bare name is tested in the NEW build for an ADDED row, so a resource that moved is still flagged")
    check('resource k/shared.json \u2192 docs/p14.md\n' in out,
          "resource triage: a CHANGED row's bare name that is unique in the new build only is flagged")
    check('resource m/shared.json' not in out,
          "resource triage: a REMOVED row's bare name that was ambiguous in the old build is not flagged")
    check('resource n/other.json \u2192 docs/p15.md\n' in out,
          "resource triage: a CHANGED row's bare name that is unique in the old build only is flagged")
    check('resource q/other.json' not in out,
          "resource triage: an ADDED row's bare name that is ambiguous in the new build is not flagged")
    check('#SUMMARY 13 changed thing(s) checked, 9 referenced' in out,
          "resource triage: every Hypixel row is counted, and only those with a citing page are referenced")

    # A report the triage cannot read in full exits 2 and says which file and how many
    # rows; what the path, brace and wildcard rules can still match is printed first.
    def triage(report, docs):
        with tempfile.TemporaryDirectory() as t:
            t = pathlib.Path(t)
            (t / 'report').mkdir(); (t / 'assets').mkdir()
            for name, text in report.items():
                (t / 'report' / name).write_text(text)
            for rel, text in docs.items():
                (t / rel).parent.mkdir(parents=True, exist_ok=True); (t / rel).write_text(text)
            o, e = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
                rc = mod.main(str(t / 'report'), str(t / 'assets'), str(t))
        return rc, o.getvalue(), e.getvalue()

    docs = {'docs/c.md': 'Edit `cfg/gone.json`, `cfg/fresh.json`, `cfg/both.json`, `cfg/dash.json` and `cfg/ok.json`.'}
    # a REMOVED row needs the OLD list; with none it is still matched by its path
    rc, out, err = triage({'resource-drift.txt': 'REMOVED hypixel d cfg/gone.json\n', 'resources-new.txt': 'META-INF/MANIFEST.MF\n'}, docs)
    check(rc == 2, "triage exit (lists): a REMOVED Hypixel row with no resources-old.txt exits 2")
    check('resources-old.txt is missing' in err and '1 Hypixel resource row(s)' in err and 'cfg/gone.json' in err,
          "triage exit (lists): the missing list is named on stderr with the number of rows that lost bare-name matching")
    check('resource cfg/gone.json \u2192 docs/c.md\n' in out and '#SUMMARY 1 changed' in out,
          "triage exit (lists): the triage that can be made is still printed, path matches included")
    check('#ERROR resources-old.txt is missing' in out and out.rstrip().splitlines()[-1].startswith('#SUMMARY'),
          "triage exit (lists): the report itself says it is incomplete (an #ERROR line before the #SUMMARY)")
    rc, out, err = triage({'resource-drift.txt': 'ADDED hypixel d cfg/fresh.json\n', 'resources-old.txt': 'META-INF/MANIFEST.MF\n',
                           'resources-new.txt': ''}, docs)
    check(rc == 2 and 'resources-new.txt is empty' in err, "triage exit (lists): an ADDED Hypixel row with an empty resources-new.txt exits 2, naming it")
    rc, out, err = triage({'resource-drift.txt': 'REMOVED hypixel d cfg/gone.json\n', 'resources-old.txt': 'META-INF/MANIFEST.MF\n'}, docs)
    check(rc == 2 and 'resources-old.txt does not list their paths' in err,
          "triage exit (lists): a list that exists and holds paths but not the row's exits 2, naming it")
    rc, out, err = triage({'resource-drift.txt': 'CHANGED hypixel d cfg/both.json\n', 'resources-old.txt': 'cfg/both.json\n',
                           'resources-new.txt': 'META-INF/MANIFEST.MF\n'}, docs)
    check(rc == 2 and 'resources-new.txt' in err and 'resources-old.txt' not in err,
          "triage exit (lists): a CHANGED row needs the NEW list too (old lists it, new lacks it)")
    rc, out, err = triage({'resource-drift.txt': 'CHANGED hypixel d cfg/both.json\n', 'resources-new.txt': 'cfg/both.json\n',
                           'resources-old.txt': 'META-INF/MANIFEST.MF\n'}, docs)
    check(rc == 2 and 'resources-old.txt' in err and 'resources-new.txt' not in err,
          "triage exit (lists): a CHANGED row needs the OLD list too (new lists it, old lacks it)")
    rc, out, err = triage({'resource-drift.txt': 'REMOVED hypixel d cfg/gone.json\nADDED hypixel d cfg/fresh.json\n',
                           'resources-old.txt': 'cfg/gone.json\n', 'resources-new.txt': 'cfg/fresh.json\n'}, docs)
    check(rc == 0 and err == '' and out.count('resource cfg/') == 2,
          "triage exit (lists): a REMOVED row needs only the old list and an ADDED row only the new (exit 0, silent)")
    rc, out, err = triage({'resource-drift.txt': 'CHANGED third-party b native/linux-x64/libx.so\n'}, docs)
    check(rc == 0 and err == '', "triage exit (lists): third-party rows only, no resource lists at all: exit 0")
    rc, out, err = triage({}, docs)
    check(rc == 0 and err == '' and '#SUMMARY 0 changed' in out, "triage exit (lists): no resource-drift.txt at all: exit 0")

    both = {'resources-old.txt': 'cfg/dash.json\ncfg/ok.json\n', 'resources-new.txt': 'cfg/dash.json\ncfg/ok.json\n'}
    rc, out, err = triage(dict(both, **{'resource-drift.txt': 'CHANGED hypixel - cfg/dash.json\n'}), docs)
    check(rc == 0 and err == '' and 'resource cfg/dash.json \u2192 docs/c.md\n' in out,
          "triage exit (grammar): a row with rule `-` (no owners file recorded the path) is well-formed")
    rc, out, err = triage(dict(both, **{'resource-drift.txt': '\nCHANGED hypixel d cfg/ok.json\n\n\n'}), docs)
    check(rc == 0 and err == '' and 'resource cfg/ok.json' in out, "triage exit (grammar): blank lines of resource-drift.txt are skipped")
    for bad in ('CHANGED hypixel d', 'MOVED hypixel d cfg/ok.json', 'CHANGED hypixel dd cfg/ok.json',
                'CHANGED hypixel D cfg/ok.json', 'CHANGED someone d cfg/ok.json', 'CHANGED hypixel 1 cfg/ok.json'):
        rc, out, err = triage(dict(both, **{'resource-drift.txt': f'CHANGED hypixel d cfg/dash.json\n{bad}\n'}), docs)
        check(rc == 2 and 'resource-drift.txt' in err and repr(bad) in err and 'resource cfg/dash.json' in out,
              f"triage exit (grammar): the malformed row `{bad}` exits 2 and is named, the rows around it still triaged")


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
_fl = lambda i: CN(i, "FAIL line has its own message")
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
     '"a" if top in foreign_top', '"a" if False',
     {"update: resource drift has `CHANGED third-party a com/vendor/messages.properties`"}),
    ("resources rule b: native libraries", B,
     'native = n.endswith(NATIVE)', 'native = False',
     {"update: resource drift has `CHANGED third-party b native/linux-x64/libx.so`"}),
    ("resources rule c: META-INF is third-party", B,
     '"c" if top == "META-INF"', '"c" if False',
     {"update: resource drift has `CHANGED third-party c META-INF/services/vendor.Spi`"}),
    ("resources rule h: a path naming com.hypixel is not enough", B,
     'HYP.search(n.encode()) or HYP.search(data)', 'HYP.search(data)',
     {"update: resource drift has `CHANGED hypixel h META-INF/services/com.hypixel.hytale.demo.Svc`"}),
    ("resources rule h: bytes naming com.hypixel are not enough", B,
     'HYP.search(n.encode()) or HYP.search(data)', 'HYP.search(n.encode())',
     {"update: resource drift has `CHANGED hypixel h META-INF/services/other.Spi`"}),
    ("resources rule h: the mark is matched case-sensitively", B,
     'HYP = re.compile(rb"(?i)hypixel|hytale")', 'HYP = re.compile(rb"hypixel|hytale")',
     {"update: resource drift has `CHANGED hypixel h native/linux-x64/libbranded.so`",
      "update: resource drift has `CHANGED hypixel h com/vendor/branded.properties`"}),
    ("resources rule h: \"hytale\" is not a mark", B,
     'HYP = re.compile(rb"(?i)hypixel|hytale")', 'HYP = re.compile(rb"(?i)hypixel")',
     {"update: resource drift has `CHANGED hypixel h native/osx-arm64/libbuild.dylib`"}),
    ("resources rule h: a mark does not beat a native presumption", B,
     'elif HYP.search(n.encode()) or HYP.search(data):', 'elif presumed != "b" and (HYP.search(n.encode()) or HYP.search(data)):',
     {"update: resource drift has `CHANGED hypixel h native/linux-x64/libbranded.so`"}),
    ("resources rule h: a mark does not beat a vendor package", B,
     'elif HYP.search(n.encode()) or HYP.search(data):', 'elif presumed != "a" and (HYP.search(n.encode()) or HYP.search(data)):',
     {"update: resource drift has `CHANGED hypixel h com/vendor/branded.properties`"}),
    ("resources rule l: a Hypixel class naming the full path", B,
     'named(consts, n.encode()) or (native and named(consts, base))', '(native and named(consts, base))',
     {"update: resource drift has `CHANGED hypixel l META-INF/vendor-loaded.properties`"}),
    ("resources rule l: a native's file name named by a Hypixel class", B,
     '(native and named(consts, base))', 'False',
     {"update: resource drift has `CHANGED hypixel l native/linux-x64/libpart.so`"}),
    ("resources rule l: a file name alone is enough for any resource", B,
     '(native and named(consts, base))', 'named(consts, base)',
     {"update: resource drift has `CHANGED third-party c META-INF/services/vendor.Spi`"}),
    # ---- rule l is a whole-name test on the constant pools' Utf8 entries (acceptance 9):
    # one mutation per edge and per term, one for the parse, one per parse guard
    ("rule-l edge: the full path is a substring of a constant", B,
     'named(consts, n.encode()) or', 'n.encode() in consts or',
     {"update: resource drift has `CHANGED third-party c META-INF/vendor-loaded.prop`",
      "update: resource drift has `CHANGED third-party c META-INF/vendor-left.cfg`"}),
    ("rule-l edge: the file name is a substring of a constant", B,
     '(native and named(consts, base))', '(native and base in consts)',
     {"update: resource drift has `CHANGED third-party b native/linux-arm64/part.so`",
      "update: resource drift has `CHANGED third-party b native/linux-arm64/libover.so`"}),
    ("rule-l edge: no left delimiter", B,
     'LEFT, RIGHT = rb"(?<![" + NAMECH + rb"])", rb"(?![" + NAMECH + rb"])"',
     'LEFT, RIGHT = b"", rb"(?![" + NAMECH + rb"])"',
     {"update: resource drift has `CHANGED third-party b native/linux-arm64/part.so`",
      "update: resource drift has `CHANGED third-party c META-INF/vendor-left.cfg`"}),
    ("rule-l edge: no right delimiter", B,
     'LEFT, RIGHT = rb"(?<![" + NAMECH + rb"])", rb"(?![" + NAMECH + rb"])"',
     'LEFT, RIGHT = rb"(?<![" + NAMECH + rb"])", b""',
     {"update: resource drift has `CHANGED third-party b native/linux-arm64/libover.so`",
      "update: resource drift has `CHANGED third-party c META-INF/vendor-loaded.prop`"}),
    ("rule-l edge: only the first occurrence is tested", B,
     'rx.search(blob) is not None', 'rx.match(blob, blob.find(tok)) is not None',
     {"update: resource drift has `CHANGED hypixel l native/linux-arm64/libq.so`"}),
    ("rule-l pool: a delimiter test on the raw class bytes", B,
     'consts.extend(pool_utf8(n, z.read(n)))', 'consts.append(z.read(n))',
     {f"update: resource drift has `CHANGED hypixel l {WHOLE}`"}),
    ("rule-l pool: a class that does not parse is skipped", B,
     '            consts.extend(pool_utf8(n, z.read(n)))\n            pools += 1\n',
     '            try:\n                consts.extend(pool_utf8(n, z.read(n)))\n                pools += 1\n            except ValueError:\n                pass\n',
     {"not a class file at all: the build fails with exit 5, naming the class and `bad magic`",
      "a class whose first byte is wrong: the build fails with exit 5, naming the class and `bad magic`",
      "a class whose this_class names another entry: the build fails with exit 5, naming the class and `this_class does not name the entry`",
      "a class cut inside its constant pool: the build fails with exit 5, naming the class and `the constant pool runs past the end`"}),
    ("rule-l pool: the magic number is not checked", B,
     '    if d[:4] != b"\\xca\\xfe\\xba\\xbe":\n        bad("bad magic")\n', '',
     {"a class whose first byte is wrong: the build fails with exit 5, naming the class and `bad magic`"}),
    ("rule-l pool: this_class is not checked against the entry", B,
     '    if utf8.get(this) != name[:-len(".class")].encode():\n        bad("this_class does not name the entry")\n', '',
     {"a class whose this_class names another entry: the build fails with exit 5, naming the class and `this_class does not name the entry`"}),
    ("resources rule x: com/hypixel/ is always Hypixel's", B,
     'if n.startswith("com/hypixel/"):', 'if False:',
     {"update: resource drift has `CHANGED hypixel x com/hypixel/hytale/demo/data.json`",
      "update: resource drift has `CHANGED hypixel x com/hypixel/hytale/lib/libhyt.so`"}),
    ("resources rule e: a directory that mirrors a foreign package", B,
     '"e" if "/" in n and', '"e" if False and',
     {"update: resource drift has `CHANGED third-party e vendor/lib/schema.proto`"}),
    ("resources rule d: Hypixel-owned is the default", B,
     'owner, rule = "hypixel", "d"', 'owner, rule = "third-party", "d"',
     {"update: resource drift has `ADDED hypixel d brandnew/data.json`"}),
    ("resources: written after the decompile, not before", B,
     'RES_OUT="$(write_resources)"',
     lambda src: (lambda a, b: src[:a] + src[b:])(*[src.index('RES_OUT="$(write_resources)"'), src.index('INDEXED="$(grep')]
                  ).replace('step "Done"\n', src[src.index('RES_OUT="$(write_resources)"'):src.index('INDEXED="$(grep')] + 'step "Done"\n', 1),
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
    ("resources: a changed resource takes its owner from the new build only", U,
     '*own_both(p), p))', '*own(no, p), p))',
     {"update: resource drift has `CHANGED hypixel h META-INF/services/lost.Spi`"}),
    ("resources: a changed resource takes its owner from the old build only", U,
     '*own_both(p), p))', '*own(oo, p), p))',
     {"update: resource drift has `CHANGED hypixel h META-INF/services/gained.Spi`"}),
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
    ("resources: the printed ownership rule omits a rule the owners file uses", U,
     "; l: a com/hypixel class names its path, or a native library's file name)", ")",
     {"update: the printed ownership rule describes every rule letter the owners file uses"}),
    ("resources triage: third-party rows are triaged", T,
     'if owner == "hypixel":', 'if True:',
     {"resource triage: a third-party resource is not triaged"}),
    ("resources triage: `dir/*.ext` wildcard", T,
     'alts.append(r"(?<![\\w-])" + re.escape(d) + r"/\\*" + wild_ext + WILD_END)', 'pass',
     {"resource triage: `bundledDefaults/*.lang` flags a change to bundledDefaults/server.lang"}),
    ("resources triage: `dir/*.ext` spans a `/`", T,
     'r"/\\*" + wild_ext + WILD_END)', 'r"/\\*" + wild_ext + RES_END)',
     {"resource triage: `bundledDefaults/*.lang/sub` is not `bundledDefaults/*.lang`"}),
    ("resources triage: bare `dir/*` spans a `/`", T,
     'r"/\\*(?![\\w*./-])")', 'r"/\\*(?![\\w*.-])")',
     {"resource triage: `bundledDefaults/*/sub` is not `bundledDefaults/*`"}),
    ("resources triage: bare `dir/*` wildcard", T,
     'alts.append(r"(?<![\\w-])" + re.escape(d) + r"/\\*(?![\\w*./-])")', 'pass',
     {"resource triage: `bundledDefaults/*` flags a change to bundledDefaults/server.lang"}),
    ("resources triage: brace list", T,
     'alts.append(r"(?<![\\w-])" + re.escape(d) + r"/\\{', 'pass; (r"(?<![\\w-])" + re.escape(d) + r"/\\{',
     {"resource triage: a full path and a brace list flag the change; another file of the brace's directory does not"}),
    ("resources triage: a bare name need not be unique among jar resources", T,
     'if any(c[name] == 1 for c in res_names) and asset_names', 'if asset_names',
     {"resource triage: a bare name shared by two jar resources does not match"}),
    ("resources triage: a bare name may also be a shipped asset", T,
     ' and asset_names.get(name, 0) == 0:', ':',
     {"resource triage: a bare name that is also a shipped asset does not match",
      "resource triage: en-US/server.lang and a bare `server.lang` do not flag a change to bundledDefaults/server.lang"}),
    ("resources triage: bare-name uniqueness counted over the union of both builds", T,
     '[res_names[b] for b in builds]',
     '[collections.Counter(os.path.basename(p) for p in set(lines("resources-old.txt")) | set(lines("resources-new.txt")))]',
     {"resource triage: a bare name is tested in the OLD build for a REMOVED row, so a resource that moved is still flagged",
      "resource triage: a bare name is tested in the NEW build for an ADDED row, so a resource that moved is still flagged"}),
    ("resources triage: a REMOVED row's bare name tested in the new build", T,
     '{"ADDED": ("new",), "REMOVED": ("old",)}', '{"ADDED": ("new",), "REMOVED": ("new",)}',
     {"resource triage: a REMOVED row's bare name that exists only in the old build is flagged"}),
    ("resources triage: an ADDED row's bare name tested in the old build", T,
     '{"ADDED": ("new",), "REMOVED": ("old",)}', '{"ADDED": ("old",), "REMOVED": ("old",)}',
     {"resource triage: an ADDED row's bare name that exists only in the new build is flagged"}),
    ("resources triage: a CHANGED row's bare name tested in the new build only", T,
     '.get(state, ("old", "new"))', '.get(state, ("new",))',
     {"resource triage: a CHANGED row's bare name that is unique in the old build only is flagged",
      "triage exit (lists): a CHANGED row needs the OLD list too (new lists it, old lacks it)"}),
    ("resources triage: a CHANGED row's bare name tested in the old build only", T,
     '.get(state, ("old", "new"))', '.get(state, ("old",))',
     {"resource triage: a CHANGED row's bare name that is unique in the new build only is flagged",
      "triage exit (lists): a CHANGED row needs the NEW list too (old lists it, new lacks it)"}),
    ("resources triage: a bare name must be unique in every build, not any", T,
     'if any(c[name] == 1 for c in res_names)', 'if all(c[name] == 1 for c in res_names)',
     {"resource triage: a CHANGED row's bare name that is unique in the old build only is flagged",
      "resource triage: a CHANGED row's bare name that is unique in the new build only is flagged"}),
    ("resources triage: bare names never match", T,
     'if any(c[name] == 1 for c in res_names) and asset_names.get(name, 0) == 0:', 'if False:',
     {"resource triage: a bare name unique among jar resources and shipped assets matches"}),
    # ---- a report the triage cannot read in full exits 2 (acceptance 9, fix C)
    ("triage exit (lists): the check that a row's path is listed is removed", T,
     'if path not in listed[b]:', 'if False:',
     {"triage exit (lists): a REMOVED Hypixel row with no resources-old.txt exits 2",
      "triage exit (lists): the missing list is named on stderr with the number of rows that lost bare-name matching",
      "triage exit (lists): an ADDED Hypixel row with an empty resources-new.txt exits 2, naming it",
      "triage exit (lists): a list that exists and holds paths but not the row's exits 2, naming it",
      "triage exit (lists): a CHANGED row needs the NEW list too (old lists it, new lacks it)",
      "triage exit (lists): a CHANGED row needs the OLD list too (new lists it, old lacks it)"}),
    ("triage exit (lists): an empty or missing list is tolerated", T,
     'if path not in listed[b]:', 'if listed[b] and path not in listed[b]:',
     {"triage exit (lists): a REMOVED Hypixel row with no resources-old.txt exits 2",
      "triage exit (lists): an ADDED Hypixel row with an empty resources-new.txt exits 2, naming it"}),
    ("triage exit (lists): a list that lacks the row's path is tolerated", T,
     'if path not in listed[b]:', 'if not listed[b]:',
     {"triage exit (lists): a list that exists and holds paths but not the row's exits 2, naming it",
      "triage exit (lists): a CHANGED row needs the NEW list too (old lists it, new lacks it)",
      "triage exit (lists): a CHANGED row needs the OLD list too (new lists it, old lacks it)"}),
    ("triage exit (grammar): a malformed line is skipped silently", T,
     '            malformed.append(l)\n            continue\n', '            continue\n',
     {f"triage exit (grammar): the malformed row `{b}` exits 2 and is named, the rows around it still triaged"
      for b in ('CHANGED hypixel d', 'MOVED hypixel d cfg/ok.json', 'CHANGED hypixel dd cfg/ok.json',
                'CHANGED hypixel D cfg/ok.json', 'CHANGED someone d cfg/ok.json', 'CHANGED hypixel 1 cfg/ok.json')}),
    ("triage exit (grammar): the rule `-` is not accepted", T,
     '([a-z]|-)', '([a-z])',
     {"triage exit (grammar): a row with rule `-` (no owners file recorded the path) is well-formed"}),
    ("triage exit (grammar): a blank line is malformed", T,
     '        if not l:\n            continue\n        m = ROW', '        m = ROW',
     {"triage exit (grammar): blank lines of resource-drift.txt are skipped"}),
    ("triage exit (update-build): the status is not captured", U,
     'TRIAGE_RC=$?', 'TRIAGE_RC=0',
     {"triage exit (update-build): a triage exiting 2 is a FAIL line, after the partial triage it printed",
      "triage exit (update-build): a triage exiting 2 makes update-build.sh exit 3, even with --no-verify"}),
    ("triage exit (update-build): no FAIL line", U,
     '  soft_fail "triage_drift.py exited 2 ', '  : "triage_drift.py exited 2 ',
     {"triage exit (update-build): a triage exiting 2 is a FAIL line, after the partial triage it printed"}),
    ("triage exit (update-build): the exit status ignores the triage", U,
     'finish() { [ "$1" = 0 ] && [ "$SOFT_RC" != 0 ] && exit "$SOFT_RC"; exit "$1"; }', 'finish() { exit "$1"; }',
     {"triage exit (update-build): a triage exiting 2 makes update-build.sh exit 3, even with --no-verify",
      "update-build exit: a resource comparison with no result makes update-build.sh exit 3, even with --no-verify"}),
    # ---- every mid-run fail that does not exit carries its status to the end (acceptance 9, follow-up)
    ("update-build exit: soft_fail keeps no status", U,
     'fail "$1"; SOFT_RC=3; true; }', 'fail "$1"; true; }',
     {"triage exit (update-build): a triage exiting 2 makes update-build.sh exit 3, even with --no-verify",
      "update-build exit: a resource comparison with no result makes update-build.sh exit 3, even with --no-verify"}),
    ("update-build exit: the resource comparison's fail leaves the status alone", U,
     'soft_fail "the resource comparison', 'fail "the resource comparison',
     {"update-build exit: a resource comparison with no result makes update-build.sh exit 3, even with --no-verify"}),
    ("update-build exit: the resource comparison prints no FAIL line", U,
     'soft_fail "the resource comparison', ': "the resource comparison',
     {"update-build exit: a resource comparison with no result is a FAIL line"}),
    # ---- review of 090b033..5c58f11 (MINOR-1 to MINOR-3 and nits)
    ("update-build exit: soft_fail sets the status but prints no FAIL line", U,
     'soft_fail() { fail "$1"; SOFT_RC=3; true; }', 'soft_fail() { SOFT_RC=3; true; }',
     {"triage exit (update-build): a triage exiting 2 is a FAIL line, after the partial triage it printed",
      "update-build exit: a resource comparison with no result is a FAIL line"}),
    ("update-build exit: a comparison python that exits non-zero after printing #COUNTS passes", U,
     'if [ "$RES_PY_RC" != 0 ] || ! grep -q', 'if ! grep -q',
     {"update-build exit: a resource comparison whose python exits non-zero is a failure even if it printed #COUNTS"}),
    # ---- the API drift (5) and source drift (5b) cannot report "no changes" for a result they did not
    # produce (item 10). One mutation per guard, each dropping exactly that guard's elif; the checks
    # named are the case's own message check, which the next guard in the chain cannot satisfy.
    # Run by group: --only "[dg1]" ... "[dg5]" (<= 5 each).
    ("drift guard [dg1] API-01: the javap diff's exit status is ignored", U, 'if [ "$API_DIFF_RC" -ge 2 ]; then', 'if false; then', {_fl('API-01')}),
    ("drift guard [dg1] API-02: the python's exit status is ignored", U, 'elif [ "$API_PY_RC" != 0 ]; then', 'elif false; then', {_fl('API-02')}),
    ("drift guard [dg1] API-03: the #COUNTS marker is not required", U, 'elif [ "$N_MARKS" != 1 ]; then', 'elif false; then',
     {_fl('API-03'), _fl('API-03b'), _fl('API-03c')}),
    ("drift guard [dg1] API-04: the marker's row count is not compared with the rows", U, 'elif [ "$A_ROWS" != "$N_CLS" ]; then', 'elif false; then', {_fl('API-04')}),
    ("drift guard [dg1] API-05: an index with no class is accepted", U, 'elif [ "$C_OLD" = 0 ] || [ "$C_NEW" = 0 ]; then', 'elif false; then',
     {_fl('API-05'), _fl('API-05b')}),
    ("drift guard [dg2] API-06: classes parsed from the old index are not counted", U, 'elif [ "$A_OLD" != "$C_OLD" ]; then', 'elif false; then', {_fl('API-06')}),
    ("drift guard [dg2] API-07: classes parsed from the new index are not counted", U, 'elif [ "$A_NEW" != "$C_NEW" ]; then', 'elif false; then', {_fl('API-07')}),
    ("drift guard [dg2] API-08: differing indexes with no rows are accepted", U, 'elif [ "$N_CLS" = 0 ] && ! cmp -s', 'elif false && ! cmp -s', {_fl('API-08')}),
    ("drift guard [dg2] API-09: the index sets keep the Compiled from lines", U, "grep -v '^Compiled from ' \"$1\"", 'cat "$1"', {SETS_RENAME}),
    ("drift guard [dg2] API-10: the index sets are not sorted", U, '| LC_ALL=C sort -u; }', '| cat; }', {SETS_ORDER}),
    ("drift guard [dg3] API-11: the source drift does not say the API drift failed", U, '[ "$API_OK" = 1 ] || info "the API drift', 'true || info "the API drift',
     {CN('API-08', "source drift says the API drift failed"), CN('API-02', "source drift says the API drift failed")}),
    ("drift guard [dg3] API-12: a failed API drift is not recorded for the source drift", U, '    API_OK=0\n    soft_fail "$API_BAD; $SUFFIX"', '    soft_fail "$API_BAD; $SUFFIX"',
     {CN('API-08', "source drift says the API drift failed"), CN('API-02', "source drift says the API drift failed")}),
    ("drift guard [dg3] API-13: the API marker line is left in api-changed-classes.txt", U, "sed -i '/^#COUNTS/d' \"$REPORT/api-changed-classes.txt\"", ':', {CTRL_STRIP}),
    ("drift guard [dg3] SRC-01: the source diff's exit status is ignored", U, 'if [ "$SRC_DIFF_RC" -ge 2 ]; then', 'if false; then', {_fl('SRC-01')}),
    ("drift guard [dg3] SRC-02: the python's exit status is ignored", U, 'elif [ "$SRC_PY_RC" != 0 ]; then', 'elif false; then', {_fl('SRC-02')}),
    ("drift guard [dg4] SRC-03: the #COUNTS marker is not required", U, 'elif [ "$N_SMARKS" != 1 ]; then', 'elif false; then',
     {_fl('SRC-03'), _fl('SRC-03b'), _fl('SRC-03c')}),
    ("drift guard [dg4] SRC-04: the old tree's file count is not compared with find", U, 'elif [ "$((N_COMMON + N_ONLYOLD))" != "$F_OLD" ]; then', 'elif false; then', {_fl('SRC-04')}),
    ("drift guard [dg4] SRC-05: the new tree's file count is not compared with find", U, 'elif [ "$((N_COMMON + N_ONLYNEW))" != "$F_NEW" ]; then', 'elif false; then', {_fl('SRC-05')}),
    ("drift guard [dg4] SRC-06: changed files are not compared with the diff's headers", U, 'elif ! [ "$N_CHANGED" -ge "$D_HDRS" ]; then', 'elif false; then', {_fl('SRC-06')}),
    ("drift guard [dg4] SRC-07: DEPRECATION rows are not compared with the diff", U, 'elif [ "$N_DEP" != "$D_DEPS" ]; then', 'elif false; then', {_fl('SRC-07')}),
    ("drift guard [dg5] SRC-08: the source marker line is left in src-changed-classes.txt", U, "sed -i '/^#COUNTS/d' \"$REPORT/src-changed-classes.txt\"", ':', {CTRL_STRIP}),
    ("triage exit (update-build): a triage crash is not a failure", U,
     'elif [ "$TRIAGE_RC" != 0 ]; then', 'elif false; then',
     {"triage exit (update-build): a triage that crashes (exit 1) is a FAIL line saying so, not the unreadable-report one",
      "triage exit (update-build): a triage that crashes exits 3, not 1 (verify-docs.sh's code)"}),
    ("triage exit (lists): the #ERROR lines are not written to the report", T,
     'print(f"#ERROR {e}")', 'pass',
     {"triage exit (lists): the report itself says it is incomplete (an #ERROR line before the #SUMMARY)"}),
    ("rule-l bounds: the in-loop bound is not checked", B,
     '        if p >= len(d):\n            bad("the constant pool runs past the end")\n', '',
     {"a class cut inside its constant pool: the build fails with exit 5, naming the class and `the constant pool runs past the end`"}),
    ("rule-l bounds: the bound after the pool is not checked", B,
     '    if p + 4 > len(d):\n        bad("the constant pool runs past the end")\n', '',
     {"a class cut exactly where its constant pool ends: the build fails with exit 5, naming the class and `the constant pool runs past the end`"}),
    ("rule-l bounds: an unknown constant tag is not refused", B,
     '        else:\n            bad(f"unknown constant tag {tag}")\n', '        else:\n            pass\n',
     {"a class whose pool holds an entry with the unused tag 2: the build fails with exit 5, naming the class and `unknown constant tag 2`"}),
]


def mutations():
    ran, bad = 0, []
    for label, fname, old, new, must_red in MUTATIONS:
        if A.only and A.only not in label:
            continue
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
    if ran < MIN_MUTATIONS and not A.only:
        bad.append(f"only {ran} mutation(s) ran, floor is {MIN_MUTATIONS}")
    print(f"MUTATIONS {ran} defect(s) reintroduced, {ran - len([b for b in bad if 'still green' in b])} turned their checks red")
    fails += bad
for f in fails:
    print(f"  FAIL {f}")
sys.exit(1 if fails else 0)
