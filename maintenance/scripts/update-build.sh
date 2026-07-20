#!/usr/bin/env bash
#
# update-build.sh — mechanical front half of a game-update pass, in one command.
# Run it after the Hytale launcher installs a new build; it gathers all the
# evidence a maintainer (human or agent) needs to re-verify the docs:
#
#   1. snapshot the previous javap index (for a jar→docs new-API diff)
#   2. rebuild the assets cache   (wipe-first extract, count-verified)
#   3. rebuild the jar cache      (build-jar-cache.sh)
#   4. asset drift report         (changed/added/removed Common assets vs baseline)
#   5. API drift report           (classes whose signatures changed old→new)
#   6. triage greps               (which docs/examples mention the changed things)
#   7. verify-docs.sh             (hard gates + advisories against the new build)
#
# It deliberately does NOT edit the repo: no stamp bumps, no baseline refresh.
# Those belong after human/agent judgment on the drift it reports — it prints
# the remaining checklist instead.
#
# Usage:
#   maintenance/scripts/update-build.sh                # full run
#   maintenance/scripts/update-build.sh --skip-caches  # reuse existing caches (re-triage)
#   maintenance/scripts/update-build.sh --no-src       # skip jar decompilation (faster)
#   maintenance/scripts/update-build.sh --no-build     # skip example compilation (faster)
#
# Env overrides:
#   HYTALE_JAR / HYTALE_ASSETS / HYTALE_JAR_CACHE   as in the other scripts
#   UPDATE_REPORT   Report dir (default ~/.cache/hytale-update-report; wiped each run)
#
# Exit code: non-zero if a cache step fails or verify-docs.sh hard-fails.

set -u
cd "$(dirname "$0")/../.." || exit 2
REPO="$(pwd)"

SKIP_CACHES=0; NO_SRC=""; NO_BUILD=""
for arg in "$@"; do
  case "$arg" in
    --skip-caches) SKIP_CACHES=1 ;;
    --no-src)      NO_SRC="--no-src" ;;
    --no-build)    NO_BUILD="--no-build" ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

section() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
info()    { printf '  INFO  %s\n' "$1"; }
warn()    { printf '  \033[33mWARN\033[0m  %s\n' "$1"; }
fail()    { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; }

# ---- resolve the Hytale install (mirrors verify-docs.sh) ----
if [ -n "${APPDATA:-}" ]; then
  ROOT="$APPDATA/Hytale"
elif [ -d "$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale" ]; then
  ROOT="$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale"
else
  ROOT="$HOME/AppData/Roaming/Hytale"
fi
ZIP="$ROOT/install/release/package/game/latest/Assets.zip"
JAR="${HYTALE_JAR:-$ROOT/install/release/package/game/latest/Server/HytaleServer.jar}"
ASSETS="${HYTALE_ASSETS:-$HOME/.cache/hytale-assets}"
JAR_CACHE="${HYTALE_JAR_CACHE:-$HOME/.cache/hytale-jar}"
REPORT="${UPDATE_REPORT:-$HOME/.cache/hytale-update-report}"
BASELINE="$REPO/maintenance/baseline/CommonAssetsIndex.hashes"

section "Environment"
[ -f "$JAR" ] || { fail "jar not found: $JAR"; exit 2; }
[ -f "$ZIP" ] || { fail "Assets.zip not found: $ZIP"; exit 2; }
NEW_VER="$(unzip -p "$JAR" META-INF/MANIFEST.MF 2>/dev/null | tr -d '\r' | sed -n 's/^Implementation-Version: //p')"
BUILD_MARKER="$(find "$ROOT/install/release/package/sig" -maxdepth 1 -name 'build-*' 2>/dev/null | head -1)"
OLD_VER="$(grep -m1 -o 'Verified against [0-9.]*' docs/inventory.md 2>/dev/null | awk '{print $3}')"
info "installed:  ${NEW_VER:-unknown} ($( [ -n "$BUILD_MARKER" ] && basename "$BUILD_MARKER" || echo 'no build marker'))"
info "docs stamp: ${OLD_VER:-unknown}"
[ -n "$NEW_VER" ] && [ "$NEW_VER" = "${OLD_VER:-}" ] && \
  warn "installed build matches the docs stamp — nothing may have updated (continuing anyway)"
rm -rf "$REPORT" && mkdir -p "$REPORT"
info "report dir: $REPORT (wiped)"

# ---- 1. snapshot the previous javap index ----
section "Snapshot previous javap index"
if [ -f "$JAR_CACHE/javap-index.txt" ]; then
  cp "$JAR_CACHE/javap-index.txt" "$REPORT/javap-index-old.txt"
  info "saved $(wc -l < "$REPORT/javap-index-old.txt") lines → javap-index-old.txt"
else
  warn "no existing javap index — the API drift report will be skipped"
fi

# ---- 2+3. rebuild caches ----
if [ "$SKIP_CACHES" = 1 ]; then
  section "Caches"; info "--skip-caches: reusing $ASSETS and $JAR_CACHE as-is"
else
  section "Rebuild assets cache (wipe-first)"
  rm -rf "$ASSETS"
  unzip -q "$ZIP" -d "$ASSETS" || { fail "extraction failed"; exit 2; }
  EXTRACTED=$(find "$ASSETS" -type f | wc -l)
  IN_ZIP=$(unzip -Z1 "$ZIP" | grep -vc '/$')
  if [ "$EXTRACTED" = "$IN_ZIP" ]; then
    info "extracted $EXTRACTED files (matches zip entry count)"
  else
    fail "extracted $EXTRACTED files but zip holds $IN_ZIP"; exit 2
  fi

  section "Rebuild jar cache"
  # shellcheck disable=SC2086
  "$REPO/maintenance/scripts/build-jar-cache.sh" $NO_SRC || { fail "build-jar-cache.sh failed"; exit 2; }
fi

# ---- 4. asset drift vs baseline ----
section "Asset drift vs baseline"
if [ -f "$BASELINE" ] && [ -f "$ASSETS/CommonAssetsIndex.hashes" ]; then
  diff <(LC_ALL=C sort "$BASELINE") <(LC_ALL=C sort "$ASSETS/CommonAssetsIndex.hashes") \
    > "$REPORT/assets-drift.diff"
  # index lines are "<sha256> <path>"; split the diff into per-path buckets
  grep '^<' "$REPORT/assets-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/assets-old-paths.txt"
  grep '^>' "$REPORT/assets-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/assets-new-paths.txt"
  comm -12 "$REPORT/assets-old-paths.txt" "$REPORT/assets-new-paths.txt" > "$REPORT/assets-modified.txt"
  comm -23 "$REPORT/assets-old-paths.txt" "$REPORT/assets-new-paths.txt" > "$REPORT/assets-removed.txt"
  comm -13 "$REPORT/assets-old-paths.txt" "$REPORT/assets-new-paths.txt" > "$REPORT/assets-added.txt"
  N_MOD=$(wc -l < "$REPORT/assets-modified.txt")
  N_DEL=$(wc -l < "$REPORT/assets-removed.txt")
  N_ADD=$(wc -l < "$REPORT/assets-added.txt")
  if [ "$N_MOD$N_DEL$N_ADD" = "000" ]; then
    info "no Common-asset drift — content identical to the baseline"
  else
    warn "$N_MOD modified, $N_ADD added, $N_DEL removed (assets-{modified,added,removed}.txt)"
    sed 's/^/        M /' "$REPORT/assets-modified.txt"
    sed 's/^/        A /' "$REPORT/assets-added.txt"
    sed 's/^/        D /' "$REPORT/assets-removed.txt"
  fi
else
  warn "baseline or extracted index missing — asset drift skipped"
fi

# ---- 5. API drift old→new ----
section "API drift (javap index old → new)"
if [ -f "$REPORT/javap-index-old.txt" ] && [ -f "$JAR_CACHE/javap-index.txt" ]; then
  diff "$REPORT/javap-index-old.txt" "$JAR_CACHE/javap-index.txt" > "$REPORT/javap-drift.diff"
  # attribute each changed member line to its declaring class
  python3 - "$REPORT/javap-index-old.txt" "$JAR_CACHE/javap-index.txt" <<'PY' > "$REPORT/api-changed-classes.txt"
import re, sys
def members(path):
    decl = re.compile(r'(?:class|interface|enum|record) +([\w.$]+)')
    out, cur = {}, None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.startswith(" "):                 # class-declaration line
            m = decl.search(line)
            if m: cur = m.group(1); out.setdefault(cur, set()).add(line)
        elif cur:
            out[cur].add(line)
    return out
old, new = members(sys.argv[1]), members(sys.argv[2])
for cls in sorted(old.keys() | new.keys()):
    if cls not in new:   print(f"REMOVED {cls}")
    elif cls not in old: print(f"ADDED   {cls}")
    elif old[cls] != new[cls]:
        print(f"CHANGED {cls}")
        for line in sorted(old[cls] - new[cls]): print(f"  - {line.strip()}")
        for line in sorted(new[cls] - old[cls]): print(f"  + {line.strip()}")
PY
  N_CLS=$(grep -c '^\(ADDED\|REMOVED\|CHANGED\)' "$REPORT/api-changed-classes.txt" || true)
  if [ "$N_CLS" = 0 ]; then
    info "no signature changes"
  else
    warn "$N_CLS class(es) added/removed/changed (api-changed-classes.txt)"
    grep '^\(ADDED\|REMOVED\|CHANGED\)' "$REPORT/api-changed-classes.txt" | sed 's/^/        /'
  fi
else
  warn "old index unavailable — API drift skipped"
fi

# ---- 6. triage greps: what do the docs/examples say about the changed things ----
section "Triage: docs/examples referencing the drift"
TOUCHED=0
if [ -s "$REPORT/assets-modified.txt" ] || [ -s "$REPORT/assets-removed.txt" ]; then
  while IFS= read -r p; do
    base="$(basename "$p")"
    hits="$(grep -rl -F "$base" docs/ examples/ 2>/dev/null | tr '\n' ' ')"
    [ -n "$hits" ] && { printf '        asset %s → %s\n' "$p" "$hits"; TOUCHED=1; }
  done < <(cat "$REPORT/assets-modified.txt" "$REPORT/assets-removed.txt")
fi
if [ -s "$REPORT/api-changed-classes.txt" ]; then
  while IFS= read -r cls; do
    simple="${cls##*.}"; simple="${simple##*$}"
    hits="$(grep -rlw "$simple" docs/ examples/ 2>/dev/null | tr '\n' ' ')"
    [ -n "$hits" ] && { printf '        class %s → %s\n' "$cls" "$hits"; TOUCHED=1; }
  done < <(grep '^\(ADDED\|REMOVED\|CHANGED\)' "$REPORT/api-changed-classes.txt" | awk '{print $2}' | sort -u)
fi
[ "$TOUCHED" = 0 ] && info "no doc/example mentions the changed assets or classes"

# ---- 7. verify-docs ----
section "verify-docs.sh"
# shellcheck disable=SC2086
"$REPO/maintenance/scripts/verify-docs.sh" $NO_BUILD
VERIFY_RC=$?

# ---- remaining judgment checklist ----
section "Next steps (judgment — not automated)"
cat <<EOF
  1. Re-verify every doc/example the triage section flagged, against
     $ASSETS and $JAR_CACHE/src.
  2. Review api-changed-classes.txt for NEW plugin-facing API worth documenting.
  3. Bump the doc stamps once everything is re-verified:
       sed -i 's/${OLD_VER:-<old>}/${NEW_VER:-<new>}/g' docs/*.md
     …then rewrite the verification paragraph in CLAUDE.md by hand.
  4. Refresh the baseline (only after the docs are re-verified):
       cp $ASSETS/CommonAssetsIndex.hashes maintenance/baseline/
     …and update maintenance/baseline/README.md's table (build, date,
     Assets.zip mtime/size, entry count, sha256).
  5. Re-run maintenance/scripts/verify-docs.sh — hard gates green, drift 0.
  6. Commit: chore: re-verify handbook against ${NEW_VER:-<new>} ($( [ -n "$BUILD_MARKER" ] && basename "$BUILD_MARKER" || echo build-N))
  Full reports: $REPORT
EOF

exit "$VERIFY_RC"
