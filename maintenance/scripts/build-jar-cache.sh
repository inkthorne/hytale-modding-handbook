#!/usr/bin/env bash
#
# build-jar-cache.sh — build a local, greppable cache of the Hytale server jar
# so API exploration is a `grep`, not dozens of per-class `javap` JVM launches.
#
# Produces (outside the repo, never committed — mirrors the assets cache):
#   ~/.cache/hytale-jar/javap-index.txt   signatures + constant values of every com.hypixel.* class
#   ~/.cache/hytale-jar/src/              decompiled .java for com.hypixel.hytale.*
#   ~/.cache/hytale-jar/class-hashes.txt  sha256 (16 hex) of every com/hypixel/hytale class's bytes
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
  for f in javap-index.txt class-hashes.txt cache-meta.txt; do
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
