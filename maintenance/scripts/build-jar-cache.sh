#!/usr/bin/env bash
#
# build-jar-cache.sh — build a local, greppable cache of the Hytale server jar
# so API exploration is a `grep`, not dozens of per-class `javap` JVM launches.
#
# Produces (outside the repo, never committed — mirrors the assets cache):
#   ~/.cache/hytale-jar/javap-index.txt   signatures + constant values of every com.hypixel.* class
#   ~/.cache/hytale-jar/src/              decompiled .java for com.hypixel.hytale.*
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
#   DECOMPILER_JAR    Path to a CFR/Vineflower/Fernflower jar to use for --src
#
# Re-run after a game update (the cache is wiped each run, like the assets cache,
# so renamed/removed classes don't linger and mask dead references in the docs).

set -u

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
INDEXED="$(grep -cE '^(Compiled from|(public |final |abstract |private |protected |static |sealed |non-sealed )*(class|interface|enum|record) )' "$INDEX" 2>/dev/null || echo '?')"
note "index written: $INDEX ($(du -h "$INDEX" | cut -f1), ~$INDEXED type decls)"

# ---- decompiled source (best effort) ----
if [ "$DO_SRC" = "1" ]; then
  step "Decompiled source"

  # find a decompiler: env override -> PATH command -> cached cfr.jar -> download
  DEC_KIND=""; DEC=""
  if [ -n "${DECOMPILER_JAR:-}" ] && [ -f "${DECOMPILER_JAR:-}" ]; then
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
  else
    command -v java >/dev/null 2>&1 || { echo "  java missing — cannot decompile" >&2; exit 2; }
    mkdir -p "$SRC"
    note "decompiler: $DEC_KIND ($DEC)"
    note "decompiling com.hypixel.hytale.* -> $SRC (this takes a few minutes)"
    case "$DEC_KIND" in
      jar|cfr-cmd)
        # CFR: --jarfilter scopes which classes get written
        RUN=(java -jar "$DEC"); [ "$DEC_KIND" = "cfr-cmd" ] && RUN=(cfr)
        "${RUN[@]}" "$JAR" --jarfilter 'com\.hypixel\.hytale\..*' \
          --outputdir "$SRC" --silent true --comments false 2>/dev/null
        ;;
      vineflower)
        vineflower -dgs=1 "$JAR" "$SRC" >/dev/null 2>&1
        ;;
    esac
    JAVAFILES="$(find "$SRC" -name '*.java' 2>/dev/null | wc -l | tr -d ' ')"
    note "decompiled: $JAVAFILES .java files ($(du -sh "$SRC" 2>/dev/null | cut -f1))"
  fi
fi

step "Done"
note "Signatures:  grep -n 'registerCoreComponentType' $INDEX"
[ "$DO_SRC" = "1" ] && note "Source:      grep -rn 'readCommonConfig' $SRC/com/hypixel/hytale/server/flock/"
note "Re-run this script after a game update to refresh the cache."
