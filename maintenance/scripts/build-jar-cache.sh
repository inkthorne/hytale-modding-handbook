#!/usr/bin/env bash
#
# build-jar-cache.sh — build a local, greppable cache of the Hytale server jar
# so API exploration is a `grep`, not dozens of per-class `javap` JVM launches.
#
# Produces (outside the repo, never committed — mirrors the assets cache):
#   ~/.cache/hytale-jar/javap-index.txt   signatures + constant values of every com.hypixel.* class
#   ~/.cache/hytale-jar/src/              decompiled .java for com.hypixel.hytale.*
#   ~/.cache/hytale-jar/class-hashes.txt  sha256 (16 hex) of every com/hypixel/hytale class's bytes
#   ~/.cache/hytale-jar/resource-hashes.txt  sha256 (64 hex, of the entry's CONTENT) and path of EVERY
#                                         non-class, non-directory jar entry, no allowlist
#   ~/.cache/hytale-jar/resource-owners.txt  for each of those: hypixel | third-party, the rule that
#                                         decided it, and the path (see the rules at the writer below)
#   ~/.cache/hytale-jar/cache-meta.txt    which jar built this cache (jar_sha = sha256 of the
#                                         jar, 16 hex; version = its Implementation-Version),
#                                         which decompiler, and whether the decompile completed
#
# The previous build is preserved automatically. This script is the only thing
# that destroys the cache, so it is where the old one is saved: before wiping a
# cache built from a DIFFERENT jar, it copies it to the snapshot store
# (~/.cache/hytale-update-snapshot for the default cache), which update-build.sh
# diffs against. Running this script by hand after a game update is therefore
# safe, and a scratch cache (HYTALE_JAR_CACHE) gets its own store beside it.
# Two runs at once against one store are NOT supported. Identity is the
# jar's content hash, never the version string, which can be absent or unchanged.
#
# The decompiler tool itself is cached separately (it survives a cache wipe):
#   ~/.cache/hytale-jar-tools/cfr.jar
#
# Usage:
#   maintenance/scripts/build-jar-cache.sh            # index + decompiled source
#   maintenance/scripts/build-jar-cache.sh --no-src   # signature index only (fast)
#
# Env overrides:
#   HYTALE_JAR        Path to HytaleServer.jar (else auto-resolved per-platform)
#   HYTALE_JAR_CACHE  Cache root (default ~/.cache/hytale-jar)
#   DECOMPILER_JAR    Path to a CFR jar to use for --src (it is driven with CFR's flags)
#   DECOMPILER_CMD    A command taking CFR's command line (<jar> --jarfilter .. --outputdir ..),
#                     e.g. a wrapper script; takes precedence over DECOMPILER_JAR
#   UPDATE_SNAPSHOT   Snapshot store. Default: ~/.cache/hytale-update-snapshot for the
#                     default cache, and <cache>.snapshot for any other cache, so exploring
#                     another jar in a scratch cache never touches the real record.
#
# Re-run after a game update (the cache is wiped each run, like the assets cache,
# so renamed/removed classes don't linger and mask dead references in the docs).

set -u

# absolute paths before anything else, so a relative override means the same
# thing here and in update-build.sh
for v in HYTALE_JAR HYTALE_JAR_CACHE UPDATE_SNAPSHOT DECOMPILER_JAR; do
  [ -n "${!v:-}" ] && export "$v=$(realpath -m "${!v}")"
done

DO_SRC=1
for arg in "$@"; do
  case "$arg" in
    --no-src) DO_SRC=0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

note() { printf '  %s\n' "$1"; }
step() { printf '\n== %s ==\n' "$1"; }

# ---- resolve the jar (mirrors verify-docs.sh / hytale-paths.gradle) ----
if [ -n "${APPDATA:-}" ]; then
  ROOT="$APPDATA/Hytale"
elif [ -d "$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale" ]; then
  ROOT="$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale"
else
  ROOT="$HOME/AppData/Roaming/Hytale"
fi
JAR="${HYTALE_JAR:-$ROOT/install/release/package/game/latest/Server/HytaleServer.jar}"

CACHE="${HYTALE_JAR_CACHE:-$HOME/.cache/hytale-jar}"
TOOLS="$HOME/.cache/hytale-jar-tools"
INDEX="$CACHE/javap-index.txt"
SRC="$CACHE/src"

step "Environment"
if [ ! -f "$JAR" ]; then echo "  jar not found: $JAR" >&2; exit 2; fi
note "jar:   $JAR"
note "cache: $CACHE"
for c in javap unzip; do
  command -v "$c" >/dev/null 2>&1 || { echo "  required tool missing: $c" >&2; exit 2; }
done

meta() { awk -F= -v k="$2" '$1==k{sub(/^[^=]*=/,""); print; exit}' "$1" 2>/dev/null; }
C_ABS="$(realpath -m "$CACHE")"
if [ -n "${UPDATE_SNAPSHOT:-}" ]; then SNAP="$UPDATE_SNAPSHOT"
elif [ "$C_ABS" = "$(realpath -m "$HOME/.cache/hytale-jar")" ]; then SNAP="$HOME/.cache/hytale-update-snapshot"
else SNAP="$C_ABS.snapshot"; fi
S_ABS="$(realpath -m "$SNAP")"
case "$S_ABS/" in "$C_ABS/"*) echo "  snapshot store $SNAP is inside the cache $CACHE, which this script wipes" >&2; exit 2 ;; esac
case "$C_ABS/" in "$S_ABS/"*) echo "  cache $CACHE is inside the snapshot store $SNAP" >&2; exit 2 ;; esac
JAR_SHA="$(sha256sum "$JAR" | cut -c1-16)"
JAR_VER="$(unzip -p "$JAR" META-INF/MANIFEST.MF 2>/dev/null | tr -d '\r' | sed -n 's/^Implementation-Version: //p')"
note "jar:   sha256 $JAR_SHA, version ${JAR_VER:-(none)}"

# ---- preserve the previous build before wiping it ----
step "Previous build"
OLD_SHA="$(meta "$CACHE/cache-meta.txt" jar_sha)"
if [ ! -f "$CACHE/javap-index.txt" ]; then
  note "no existing cache — nothing to preserve"
elif [ -n "$OLD_SHA" ] && [ "$OLD_SHA" = "$JAR_SHA" ]; then
  note "the cache was built from this same jar — rebuilding it; the snapshot store is untouched"
elif [ -f "$SNAP/cache-meta.txt" ] && [ -n "$(meta "$SNAP/cache-meta.txt" cache)" ] \
     && [ "$(meta "$SNAP/cache-meta.txt" cache)" != "$C_ABS" ]; then
  # the store holds another cache's previous build: never overwrite it from this one
  note "WARN: the snapshot store $SNAP holds the previous build of a different cache ($(meta "$SNAP/cache-meta.txt" cache)) — NOT replacing it"
elif [ -z "$OLD_SHA" ] && [ -f "$SNAP/javap-index.txt" ]; then
  # An unstamped cache cannot be proven to be another build, and a snapshot
  # already exists: replacing it on an assumption could swap the only record of
  # the previous build for a copy of the installed one.
  note "WARN: the cache has no jar_sha stamp and a snapshot already exists — keeping the snapshot, NOT replacing it"
else
  [ -z "$OLD_SHA" ] && note "WARN: the cache has no jar_sha stamp and no snapshot exists — saving it as the previous build"
  # Copy beside the store (same filesystem) and rename into place only once the
  # copy is complete, so a failure leaves the previous snapshot intact and the
  # cache unwiped. Leftovers of an interrupted copy are removed first.
  rm -rf "$SNAP".new.* 2>/dev/null
  TMP="$SNAP.new.$$"
  { mkdir -p "$TMP"; } 2>/dev/null || { echo "  FAILED: cannot create $TMP — the cache is NOT wiped" >&2; exit 4; }
  for f in javap-index.txt class-hashes.txt resource-hashes.txt resource-owners.txt cache-meta.txt; do
    [ -f "$CACHE/$f" ] || continue
    cp "$CACHE/$f" "$TMP/$f" || { rm -rf "$TMP"; echo "  FAILED: snapshot copy of $f — the cache is NOT wiped" >&2; exit 4; }
  done
  if [ -d "$CACHE/src" ]; then
    cp -a "$CACHE/src" "$TMP/src" || { rm -rf "$TMP"; echo "  FAILED: snapshot copy of src/ — the cache is NOT wiped" >&2; exit 4; }
  fi
  echo "cache=$C_ABS" >> "$TMP/cache-meta.txt" 2>/dev/null
  { rm -rf "$SNAP.prev" && { [ ! -e "$SNAP" ] || mv "$SNAP" "$SNAP.prev"; } && mv "$TMP" "$SNAP" && rm -rf "$SNAP.prev"; } \
    || { echo "  FAILED: could not move the snapshot into place at $SNAP — the cache is NOT wiped" >&2; exit 4; }
  note "saved the previous build ($(meta "$SNAP/cache-meta.txt" version || true), jar ${OLD_SHA:-unstamped}) → $SNAP"
fi

# ---- wipe & recreate the cache (clean extract, like the assets cache) ----
rm -rf "$CACHE"
mkdir -p "$CACHE"

# ---- signature index: batches of classes per javap, run in parallel ----
step "Signature index"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
unzip -Z1 "$JAR" 2>/dev/null \
  | grep -E '^com/hypixel/.*\.class$' \
  | sed 's#/#.#g; s#\.class$##' \
  | sort > "$WORK/classes.txt"
COUNT="$(wc -l < "$WORK/classes.txt" | tr -d ' ')"
note "classes to index: $COUNT"
# Split into batches (each javap cmdline stays well under ARG_MAX), decompile
# each batch to its OWN file, then concatenate — so parallel writers never
# interleave lines into the index.
split -l 400 "$WORK/classes.txt" "$WORK/batch."
ls "$WORK"/batch.* | xargs -P "$(nproc 2>/dev/null || echo 4)" -I{} \
  sh -c 'javap -p -constants -cp "$1" $(cat "$2") > "$2.sig" 2>/dev/null' _ "$JAR" {}
cat "$WORK"/batch.*.sig > "$INDEX"
# Stamp the cache as soon as the index exists: a later decompile failure must
# still leave a cache that says which jar it came from, or the next run could
# not tell it from a previous build.
META="$CACHE/cache-meta.txt"
write_meta() { { echo "version=${JAR_VER:-unknown}"; echo "jar_sha=$JAR_SHA"; echo "src=$1"; [ -n "${2:-}" ] && echo "$2"; true; } > "$META"; }
write_meta none
# Per-class bytecode hashes: the only record of a change inside a method the
# decompiler cannot render (it emits the same stub whatever the bytecode says).
python3 - "$JAR" > "$CACHE/class-hashes.txt" <<'PY'
import hashlib, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    for n in sorted(z.namelist()):
        if n.startswith("com/hypixel/hytale/") and n.endswith(".class"):
            print(hashlib.sha256(z.read(n)).hexdigest()[:16], n[:-6].replace("/", "."))
PY
# Every non-class, non-directory entry of the jar, hashed by CONTENT (not the
# zip's CRC or timestamps, which a repack changes without changing a byte). The
# class hashes above cover com/hypixel/hytale only, and the javap index and the
# decompiled source cover classes only, so a changed block-id migration
# (migration/blocks/*.json), the bundled .lang, a service file or the manifest
# surfaced nowhere. There is NO allowlist: an allowlist of "interesting" paths is
# the omission this closes.
#
# Ownership is the DEFAULT: a resource is Hypixel's unless the jar itself shows
# it is not, and a mark the jar shows for Hypixel beats the presumption of a
# third party. Mis-sorting a third-party file onto the Hypixel side costs a line
# of noise; the other direction hides a Hypixel change. The first rule that
# applies decides:
#   x  under com/hypixel/ (the package that is Hypixel's by name)       -> hypixel
# Then a third-party presumption, the first of these that applies (b, c, a, e)...
#   b  native library (.so .dll .dylib .jnilib)
#   c  under META-INF/
#   a  its top-level directory also holds classes outside com/hypixel/
#      (com/ holds com/google and others; rule x came first)
#   e  its directory mirrors a package of foreign classes under com/
#      (google/protobuf/*.proto sits beside com/google/protobuf/*.class,
#      which the jar shows; 12 files at 0.7.2)
# ...which a mark of Hypixel's overrides, the first of these that applies:
#   h  its path or its bytes contain "hypixel" or "hytale", in any case -> hypixel
#      (a services file naming a Hypixel class; the "Hypixel Studios Canada Inc"
#      signature and the HytaleClient build path inside the natives Hypixel
#      builds; META-INF/NOTICE, which opens "Hytale Server / Copyright ...
#      Hypixel Studios Canada inc.")
#   l  a class under com/hypixel/ NAMES it: its full path as a string constant
#      ("/native/linux-x64/libzstd.so" in ZstdNative), or, for a native library
#      only, its file name (RocksDbNative builds "/native/" + dir + "/" + name
#      from parts, so only "librocksdb.so" is there). A file NAME alone is not
#      enough for any other resource: MANIFEST.MF and "exec" are names that
#      Hypixel classes contain and a third party's files carry.        -> hypixel
#      "Names" is a whole-name test on the CONSTANT_Utf8 entries of the classes'
#      constant pools, not a substring test on their bytes: a token T is named
#      when some entry holds T at an offset where the byte before it (if any) and
#      the byte after it (if any) are not in [A-Za-z0-9._-]. So "/native/x/libzstd.so",
#      an invokedynamic recipe "/native/\1/librocksdb.so" and a whole constant
#      "librocksdb.so" name their file; "zstd.so" inside "libzstd.so" and
#      "libpart.so" inside "libpart.so.1" do not. A raw search of the class bytes
#      cannot say this: a whole constant sits right after its u2 length, and that
#      byte is a name character for lengths 45, 46, 48-57, 65-90, 95 and 97-122, so such a path would
#      be refused (the dangerous direction). Hence the pools are parsed; a class
#      that does not parse (bad magic, unknown tag, a pool or entry that runs past
#      the end, this_class not naming the entry) FAILS THE BUILD (exit 5), because
#      dropping its constants would file the resources it names as third-party.
# A presumption with no mark stays third-party under its own letter (b, c, a, e).
#   d  anything that matched no presumption, including a top-level directory
#      the jar has not shown before                                    -> hypixel
# At 0.7.2 the overrides move 10 of 197 presumed-third-party entries: META-INF/NOTICE
# and the nine native/* libraries (zstd, quiche, rocksdb). The third-party natives
# (zstd-jni's <os>/<arch>/ libraries, netty's META-INF/native, jline's
# org/jline/nativ) all stay on b, 40 of them at 0.7.2: b is the first presumption
# tested, so a native never reaches c (under META-INF/native) or a (under org/).
# Rule b stays as the presumption for a library nothing Hypixel names: without it
# the zstd-jni libraries, whose top directories (linux/, win/, darwin/) the jar
# shows no foreign class under, would fall to d and be listed on every rebuild.
# The rules are written into resource-owners.txt so the report prints what each
# side holds and a REMOVED resource keeps the owner it had.
write_resources() {
  python3 -I - "$JAR" "$CACHE" <<'PY'
import hashlib, re, sys, zipfile
jar, out = sys.argv[1:3]
NATIVE = (".so", ".dll", ".dylib", ".jnilib")
HYP = re.compile(rb"(?i)hypixel|hytale")
# the one boundary predicate rule l uses, for a full path and for a file name alike
NAMECH = rb"A-Za-z0-9._-"
LEFT, RIGHT = rb"(?<![" + NAMECH + rb"])", rb"(?![" + NAMECH + rb"])"
# constant pool entry widths after the tag byte (tag 1, Utf8, is u2 length + bytes;
# tags 5 and 6, long and double, take two slots)
WIDTH = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4, 12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}


def pool_utf8(name, d):
    """The CONSTANT_Utf8 entries (raw modified-UTF-8 bytes) of one class file. A class
    that does not parse RAISES: its constants would be silently dropped, and every
    resource it names would be filed third-party."""
    def bad(why):
        raise ValueError(f"{name}: not a parseable class file ({why})")
    if d[:4] != b"\xca\xfe\xba\xbe":
        bad("bad magic")
    if len(d) < 10:
        bad("truncated header")
    count, p, i = int.from_bytes(d[8:10], "big"), 10, 1
    utf8, klass = {}, {}
    while i < count:
        if p >= len(d):
            bad("the constant pool runs past the end")
        tag = d[p]
        p += 1
        if tag == 1:
            n = int.from_bytes(d[p:p + 2], "big")
            utf8[i] = d[p + 2:p + 2 + n]
            p += 2 + n
        elif tag in WIDTH:
            if tag == 7:
                klass[i] = int.from_bytes(d[p:p + 2], "big")
            p += WIDTH[tag]
            if tag in (5, 6):
                i += 1
        else:
            bad(f"unknown constant tag {tag}")
        i += 1
    if p + 4 > len(d):
        bad("the constant pool runs past the end")
    this = klass.get(int.from_bytes(d[p + 2:p + 4], "big"))
    if utf8.get(this) != name[:-len(".class")].encode():
        bad("this_class does not name the entry")
    return list(utf8.values())


def named(blob, tok):
    """tok occurs in blob delimited on both sides (blob's ends count as delimiters)."""
    rx = re.compile(LEFT + re.escape(tok) + RIGHT)
    return tok in blob and rx.search(blob) is not None


with zipfile.ZipFile(jar) as z:
    names = sorted(n for n in z.namelist() if not n.endswith("/") and not n.endswith(".class"))
    foreign = [n for n in z.namelist() if n.endswith(".class") and not n.startswith("com/hypixel/")]
    foreign_top = {n.split("/")[0] for n in foreign}
    foreign_dirs = {n.rsplit("/", 1)[0] for n in foreign}
    # every string a class under com/hypixel/ holds, joined by NUL (modified UTF-8
    # never holds a raw NUL, and NUL is not a name character)
    consts, pools = [], 0
    for n in z.namelist():
        if n.startswith("com/hypixel/") and n.endswith(".class"):
            consts.extend(pool_utf8(n, z.read(n)))
            pools += 1
    consts = b"\0".join(consts)
    with open(out + "/resource-hashes.txt", "w") as hf, open(out + "/resource-owners.txt", "w") as of:
        for n in names:
            data = z.read(n)
            top = n.split("/")[0] if "/" in n else ""
            native = n.endswith(NATIVE)
            base = n.rsplit("/", 1)[-1].encode()
            presumed = ("b" if native else "c" if top == "META-INF" else "a" if top in foreign_top
                        else "e" if "/" in n and ("com/" + n.rsplit("/", 1)[0]) in foreign_dirs else None)
            if n.startswith("com/hypixel/"):
                owner, rule = "hypixel", "x"
            elif presumed is None:
                owner, rule = "hypixel", "d"
            elif HYP.search(n.encode()) or HYP.search(data):
                owner, rule = "hypixel", "h"
            elif named(consts, n.encode()) or (native and named(consts, base)):
                owner, rule = "hypixel", "l"
            else:
                owner, rule = "third-party", presumed
            hf.write(f"{hashlib.sha256(data).hexdigest()}  {n}\n")
            of.write(f"{owner} {rule} {n}\n")
print(len(names))
print(pools)
PY
}
RES_OUT="$(write_resources)" || { echo "  FAILED: could not hash the jar's resources" >&2; exit 5; }
RES_N="$(printf '%s\n' "$RES_OUT" | sed -n 1p)"; POOLS_N="$(printf '%s\n' "$RES_OUT" | sed -n 2p)"
case "$RES_N" in ''|0|*[!0-9]*) echo "  FAILED: resource hashing wrote '${RES_N:-nothing}' entries — a jar always carries META-INF/MANIFEST.MF" >&2; exit 5 ;; esac
note "resources hashed: $RES_N (rule l read ${POOLS_N:-?} constant pool(s) of classes under com/hypixel/)"
INDEXED="$(grep -cE '^(Compiled from|(public |final |abstract |private |protected |static |sealed |non-sealed )*(class|interface|enum|record) )' "$INDEX" 2>/dev/null || echo '?')"
note "index written: $INDEX ($(du -h "$INDEX" | cut -f1), ~$INDEXED type decls)"

# ---- decompiled source (best effort) ----
if [ "$DO_SRC" = "1" ]; then
  step "Decompiled source"

  # find a decompiler: env override -> PATH command -> cached cfr.jar -> download
  DEC_KIND=""; DEC=""
  if [ -n "${DECOMPILER_CMD:-}" ]; then
    DEC_KIND="cfr-cmd"; DEC="$DECOMPILER_CMD"
  elif [ -n "${DECOMPILER_JAR:-}" ] && [ -f "${DECOMPILER_JAR:-}" ]; then
    DEC_KIND="jar"; DEC="$DECOMPILER_JAR"
  elif command -v vineflower >/dev/null 2>&1; then DEC_KIND="vineflower"; DEC="vineflower"
  elif command -v cfr        >/dev/null 2>&1; then DEC_KIND="cfr-cmd";   DEC="cfr"
  elif [ -f "$TOOLS/cfr.jar" ]; then DEC_KIND="jar"; DEC="$TOOLS/cfr.jar"
  else
    note "no decompiler found; trying to download CFR to $TOOLS/cfr.jar"
    mkdir -p "$TOOLS"
    CFR_URL="https://repo1.maven.org/maven2/org/benf/cfr/0.152/cfr-0.152.jar"
    if command -v curl >/dev/null 2>&1 && curl -fsSL "$CFR_URL" -o "$TOOLS/cfr.jar"; then
      DEC_KIND="jar"; DEC="$TOOLS/cfr.jar"
    elif command -v wget >/dev/null 2>&1 && wget -q "$CFR_URL" -O "$TOOLS/cfr.jar"; then
      DEC_KIND="jar"; DEC="$TOOLS/cfr.jar"
    else
      rm -f "$TOOLS/cfr.jar"
    fi
  fi

  if [ -z "$DEC_KIND" ]; then
    note "SKIPPED: no decompiler available and download failed."
    note "Provide one with DECOMPILER_JAR=/path/to/cfr.jar (or install 'vineflower'/'cfr'),"
    note "then re-run. The signature index above is complete and usable on its own."
    write_meta "skipped (no decompiler)"
  else
    command -v java >/dev/null 2>&1 || { echo "  java missing — cannot decompile" >&2; exit 2; }
    mkdir -p "$SRC"
    note "decompiler: $DEC_KIND ($DEC)"
    note "decompiling com.hypixel.hytale.* -> $SRC (this takes a few minutes)"
    # The decompiler's identity is recorded because source drift compares two
    # decompilations: a different decompiler (or version) re-renders every file.
    case "$DEC_KIND" in
      jar)     DEC_ID="jar $(sha256sum "$DEC" 2>/dev/null | cut -c1-16)" ;;
      *)       DEC_ID="$DEC_KIND $(command -v "$DEC" || echo "$DEC")" ;;
    esac
    DEC_RC=0
    case "$DEC_KIND" in
      jar|cfr-cmd)
        # CFR: --jarfilter scopes which classes get written
        RUN=(java -jar "$DEC"); [ "$DEC_KIND" = "cfr-cmd" ] && RUN=("$DEC")
        "${RUN[@]}" "$JAR" --jarfilter 'com\.hypixel\.hytale\..*' \
          --outputdir "$SRC" --silent true --comments false 2>/dev/null || DEC_RC=$?
        ;;
      vineflower)
        vineflower -dgs=1 "$JAR" "$SRC" >/dev/null 2>&1 || DEC_RC=$?
        ;;
    esac
    JAVAFILES="$(find "$SRC" -name '*.java' 2>/dev/null | wc -l | tr -d ' ')"
    note "decompiled: $JAVAFILES .java files ($(du -sh "$SRC" 2>/dev/null | cut -f1))"
    # A failed, empty or partial decompile must fail the script. Exiting 0 here
    # once let update-build.sh report "no source changes" over an empty tree.
    # CFR writes one file per top-level class (0.6.8: 6,564 of 6,564), so fewer
    # files than top-level classes means the decompile stopped early.
    WANT="$(grep -c '^com\.hypixel\.hytale\.[^$]*$' "$WORK/classes.txt" || true)"
    if [ "$DEC_RC" != 0 ] || [ "$JAVAFILES" = 0 ] || [ "$JAVAFILES" -lt "$WANT" ]; then
      write_meta "failed (exit $DEC_RC, $JAVAFILES files)" "decompiler=$DEC_ID"
      echo "  FAILED: decompiler exited $DEC_RC and wrote $JAVAFILES file(s) for $WANT top-level class(es)" >&2
      exit 3
    fi
    write_meta ok "src_files=$JAVAFILES
decompiler=$DEC_ID"
  fi
fi

step "Done"
note "Signatures:  grep -n 'registerCoreComponentType' $INDEX"
[ "$DO_SRC" = "1" ] && note "Source:      grep -rn 'readCommonConfig' $SRC/com/hypixel/hytale/server/flock/"
note "Re-run this script after a game update to refresh the cache."
