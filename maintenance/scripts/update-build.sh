#!/usr/bin/env bash
#
# update-build.sh — mechanical front half of a game-update pass, in one command.
# Run it after the Hytale launcher installs a new build; it gathers all the
# evidence a maintainer (human or agent) needs to re-verify the docs:
#
#   1. snapshot the previous javap index and decompiled source (for the old→new diffs)
#   2. rebuild the assets cache   (wipe-first extract, count-verified)
#   3. rebuild the jar cache      (build-jar-cache.sh)
#   4. asset drift report         (changed/added/removed Common assets vs baseline)
#   5. API drift report           (classes whose signatures changed old→new)
#   5b. source drift report       (decompiled source old→new: body-only and @Deprecated changes)
#   5c. resource drift report     (the jar's NON-class entries old→new: migration/blocks/*.json,
#                                  bundledDefaults/server.lang, manifests.json, services files, …)
#   6. triage                     (which docs/examples mention the changed things)
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
#   maintenance/scripts/update-build.sh --no-verify    # stop before verify-docs.sh (used by the fixture)
#
# Env overrides:
#   HYTALE_JAR / HYTALE_ASSETS / HYTALE_JAR_CACHE   as in the other scripts
#   UPDATE_REPORT   Report dir (default ~/.cache/hytale-update-report; wiped each run)
#   UPDATE_BASELINE_DIR  Asset baselines (default maintenance/baseline; the fixture overrides it)
#   UPDATE_SNAPSHOT Previous-build snapshot, written by build-jar-cache.sh whenever it
#                   replaces a cache built from a different jar (default: as there)
#
# Exit code:
#   0  every step ran and verify-docs.sh passed (or --no-verify)
#   1  (or verify-docs.sh's own non-zero status) verify-docs.sh failed; it takes precedence
#   2  a hard stop: bad argument, jar/Assets.zip missing, a store inside a wiped directory,
#      extraction or build-jar-cache.sh failed (nothing after it ran)
#   3  one or more soft failures: a section failed WITHOUT stopping the run, so the rest of the
#      report was still produced. The FAIL lines say which: a Common-asset diff that exited 2, or
#      whose indexes could not be sorted (an unreadable file); a Server/Cosmetics diff that exited 2,
#      or a hash-server-assets.sh that exited non-zero (a file it could not hash); the API drift (5)
#      or the source drift (5b) could not show its result (a diff that exited 2, a python that
#      exited non-zero or printed no #COUNTS marker, or a count or row set that a non-python route
#      contradicts: the classes added, removed and changed by an awk pass over the indexes, the
#      BODY/SIG+BODY rows by the python's own marker; the section then prints no rows and no
#      "no changes" line), the resource comparison produced no result, or triage_drift.py exited
#      non-zero (2: it could not read the report in full, so the triage is incomplete; anything
#      else: it crashed). All of them exit 3, whichever came first.

set -u
# absolute paths before the cd below, so a relative override is not silently
# re-rooted inside the repo
for v in HYTALE_JAR HYTALE_ASSETS HYTALE_JAR_CACHE UPDATE_REPORT UPDATE_SNAPSHOT UPDATE_BASELINE_DIR DECOMPILER_JAR; do
  [ -n "${!v:-}" ] && export "$v=$(realpath -m "${!v}")"
done
cd "$(dirname "$0")/../.." || exit 2
REPO="$(pwd)"

SKIP_CACHES=0; NO_SRC=""; NO_BUILD=""; NO_VERIFY=0
for arg in "$@"; do
  case "$arg" in
    --skip-caches) SKIP_CACHES=1 ;;
    --no-src)      NO_SRC="--no-src" ;;
    --no-build)    NO_BUILD="--no-build" ;;
    --no-verify)   NO_VERIFY=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

section() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
info()    { printf '  INFO  %s\n' "$1"; }
warn()    { printf '  \033[33mWARN\033[0m  %s\n' "$1"; }
fail()    { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; }
# A fail() that does not exit (a section has no result, the run goes on to show the rest)
# must still end the run nonzero: the final status is verify-docs.sh's, and --no-verify makes
# it 0. soft_fail MESSAGE prints the FAIL line and makes finish() exit 3 (the header says why one code).
SOFT_RC=0
soft_fail() { fail "$1"; SOFT_RC=3; true; }

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
BASELINE_DIR="${UPDATE_BASELINE_DIR:-$REPO/maintenance/baseline}"
BASELINE="$BASELINE_DIR/CommonAssetsIndex.hashes"

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
# same default rule as build-jar-cache.sh: the default cache's store, or one beside the cache
if [ -n "${UPDATE_SNAPSHOT:-}" ]; then SNAP="$UPDATE_SNAPSHOT"
elif [ "$(realpath -m "$JAR_CACHE")" = "$(realpath -m "$HOME/.cache/hytale-jar")" ]; then SNAP="$HOME/.cache/hytale-update-snapshot"
else SNAP="$(realpath -m "$JAR_CACHE").snapshot"; fi
export UPDATE_SNAPSHOT="$SNAP"            # build-jar-cache.sh writes the same store
meta() { awk -F= -v k="$2" '$1==k{sub(/^[^=]*=/,""); print; exit}' "$1" 2>/dev/null; }
# The report dir is wiped every run and the cache on every rebuild; the store
# must be outside both or a run would destroy the record it is about to read.
R_ABS="$(realpath -m "$REPORT")"; S_ABS="$(realpath -m "$SNAP")"; C_ABS="$(realpath -m "$JAR_CACHE")"
for pair in "$R_ABS:report dir" "$C_ABS:jar cache"; do
  d="${pair%%:*}"
  case "$S_ABS/" in "$d/"*) fail "snapshot store $SNAP is inside the ${pair#*:} ($d), which is wiped"; exit 2 ;; esac
  case "$d/" in "$S_ABS/"*) fail "the ${pair#*:} ($d) is inside the snapshot store $SNAP"; exit 2 ;; esac
done
INSTALLED_SHA="$(sha256sum "$JAR" | cut -c1-16)"
rm -rf "$REPORT" && mkdir -p "$REPORT"
info "report dir: $REPORT (wiped)"

# ---- 1. the previous build ----
# build-jar-cache.sh (step 3) saves the cache to the snapshot store before wiping
# it, whenever the cache was built from a different jar. Nothing is copied here.
if [ "$SKIP_CACHES" = 1 ]; then
  section "Caches"
  CACHE_SHA="$(meta "$JAR_CACHE/cache-meta.txt" jar_sha)"
  if [ "$CACHE_SHA" != "$INSTALLED_SHA" ]; then
    warn "--skip-caches: the jar cache was built from jar ${CACHE_SHA:-(unstamped)}, not the installed $INSTALLED_SHA — this run would report the wrong pair of builds; run without --skip-caches"
  fi
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

section "Previous build on record"
SNAP_SHA="$(meta "$SNAP/cache-meta.txt" jar_sha)"; SNAP_VER="$(meta "$SNAP/cache-meta.txt" version)"
if [ -f "$SNAP/javap-index.txt" ]; then
  N_SNAPSRC=0; [ -d "$SNAP/src" ] && N_SNAPSRC=$(find "$SNAP/src" -name '*.java' | wc -l)
  info "snapshot: version ${SNAP_VER:-unknown}, jar ${SNAP_SHA:-(unstamped)}, $(wc -l < "$SNAP/javap-index.txt") index lines, $N_SNAPSRC decompiled files ($SNAP)"
  # Content, not version strings: a jar with no Implementation-Version, or an
  # unstamped cache, must not be able to hide a build compared with itself.
  # The resource hashes are part of the content test: a jar whose classes are
  # byte-identical but whose migration/blocks/3_4.json changed is NOT the same
  # build, and calling it one would tell the reader every section is empty.
  if [ "$SNAP_SHA" = "$INSTALLED_SHA" ] || \
     { cmp -s "$SNAP/javap-index.txt" "$JAR_CACHE/javap-index.txt" && cmp -s "$SNAP/class-hashes.txt" "$JAR_CACHE/class-hashes.txt" \
       && cmp -s "$SNAP/resource-hashes.txt" "$JAR_CACHE/resource-hashes.txt"; }; then
    warn "the snapshot IS the installed build (same jar, or byte-identical index, class hashes and resource hashes) — every drift section below compares it with itself"
  elif { [ -z "$SNAP_SHA" ] || [ ! -f "$SNAP/class-hashes.txt" ] || [ ! -f "$SNAP/resource-hashes.txt" ]; } && cmp -s "$SNAP/javap-index.txt" "$JAR_CACHE/javap-index.txt"; then
    # a snapshot from before jar_sha/class-hashes/resource-hashes existed cannot prove it differs
    warn "the snapshot's index is byte-identical to the installed build's and it has no jar_sha/class hashes/resource hashes to tell them apart — it may be the installed build compared with itself"
  fi
  ln -s "$SNAP/javap-index.txt" "$REPORT/javap-index-old.txt"
  [ -d "$SNAP/src" ] && ln -s "$SNAP/src" "$REPORT/src-old"
else
  warn "no snapshot of a previous build at $SNAP (first run?) — the API and source drift sections will be skipped"
fi

# ---- 4. asset drift vs baseline ----
section "Asset drift vs baseline"
if [ -f "$BASELINE" ] && [ -f "$ASSETS/CommonAssetsIndex.hashes" ]; then
  # Each index is sorted to its own temp file and the sort's status read. The diff used to take
  # `<(sort ...)` operands, whose status nothing reads: one unreadable input made diff see an empty
  # file (everything "added" or "removed"), and both unreadable made it see two empty files, exit 0
  # and print "no Common-asset drift - content identical to the baseline" (measured, review of
  # 02aaa06..3baa29d, LOW-1). The temp files live outside the report dir so it holds only reports.
  SORT_DIR="$(mktemp -d)"
  LC_ALL=C sort "$BASELINE" > "$SORT_DIR/baseline" 2>/dev/null; SORT_RC_B=$?
  LC_ALL=C sort "$ASSETS/CommonAssetsIndex.hashes" > "$SORT_DIR/extracted" 2>/dev/null; SORT_RC_X=$?
  if [ "$SORT_RC_B" != 0 ] || [ "$SORT_RC_X" != 0 ]; then
    soft_fail "asset drift: could not sort the Common-asset indexes for the diff (the baseline sort exited $SORT_RC_B, the extracted index's $SORT_RC_X; an unreadable file is the usual cause) — Common-asset drift is NOT reported; this run exits nonzero (3 unless verify-docs.sh fails)"
  else
    diff "$SORT_DIR/baseline" "$SORT_DIR/extracted" > "$REPORT/assets-drift.diff"
    ASSET_DIFF_RC=$?     # 2 or more is trouble (0 same, 1 differs): the buckets below would be cut short
    # index lines are "<sha256> <path>"; split the diff into per-path buckets
    grep '^<' "$REPORT/assets-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/assets-old-paths.txt"
    grep '^>' "$REPORT/assets-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/assets-new-paths.txt"
    comm -12 "$REPORT/assets-old-paths.txt" "$REPORT/assets-new-paths.txt" > "$REPORT/assets-modified.txt"
    comm -23 "$REPORT/assets-old-paths.txt" "$REPORT/assets-new-paths.txt" > "$REPORT/assets-removed.txt"
    comm -13 "$REPORT/assets-old-paths.txt" "$REPORT/assets-new-paths.txt" > "$REPORT/assets-added.txt"
    N_MOD=$(wc -l < "$REPORT/assets-modified.txt")
    N_DEL=$(wc -l < "$REPORT/assets-removed.txt")
    N_ADD=$(wc -l < "$REPORT/assets-added.txt")
    if [ "$ASSET_DIFF_RC" -ge 2 ]; then
      soft_fail "asset drift: diff of the Common-asset indexes exited $ASSET_DIFF_RC (0 and 1 are normal) — Common-asset drift is NOT reported; this run exits nonzero (3 unless verify-docs.sh fails)"
    elif [ "$N_MOD$N_DEL$N_ADD" = "000" ]; then
      info "no Common-asset drift — content identical to the baseline"
    else
      warn "$N_MOD modified, $N_ADD added, $N_DEL removed (assets-{modified,added,removed}.txt)"
      sed 's/^/        M /' "$REPORT/assets-modified.txt"
      sed 's/^/        A /' "$REPORT/assets-added.txt"
      sed 's/^/        D /' "$REPORT/assets-removed.txt"
    fi
  fi
  rm -rf "$SORT_DIR"
else
  warn "baseline or extracted index missing — asset drift skipped"
fi

section "Server/Cosmetics asset drift vs baseline (generated index)"
if [ -f "$BASELINE_DIR/ServerAssetsIndex.hashes" ] && [ -d "$ASSETS/Server" ]; then
  "$REPO/maintenance/scripts/hash-server-assets.sh" "$ASSETS" > "$REPORT/ServerAssetsIndex.hashes"
  HASH_RC=$?
  # hash-server-assets.sh exits nonzero when any file could not be hashed. Its status used to be
  # unread, and it used to be 0: one unreadable file left a short index, which the diff below reports
  # as that file REMOVED, a genuine-looking drift row (measured, review of 02aaa06..3baa29d, LOW-2).
  if [ "$HASH_RC" != 0 ]; then
    soft_fail "asset drift: hash-server-assets.sh exited $HASH_RC — the generated Server/Cosmetics index is incomplete (a file it could not hash would read as REMOVED) and Server/Cosmetics drift is NOT reported; this run exits nonzero (3 unless verify-docs.sh fails)"
  else
    diff "$BASELINE_DIR/ServerAssetsIndex.hashes" "$REPORT/ServerAssetsIndex.hashes" \
      > "$REPORT/server-drift.diff"
    SERVER_DIFF_RC=$?    # as above
    grep '^<' "$REPORT/server-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/server-old-paths.txt"
    grep '^>' "$REPORT/server-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/server-new-paths.txt"
    comm -12 "$REPORT/server-old-paths.txt" "$REPORT/server-new-paths.txt" > "$REPORT/server-modified.txt"
    comm -23 "$REPORT/server-old-paths.txt" "$REPORT/server-new-paths.txt" > "$REPORT/server-removed.txt"
    comm -13 "$REPORT/server-old-paths.txt" "$REPORT/server-new-paths.txt" > "$REPORT/server-added.txt"
    N_MOD=$(wc -l < "$REPORT/server-modified.txt")
    N_DEL=$(wc -l < "$REPORT/server-removed.txt")
    N_ADD=$(wc -l < "$REPORT/server-added.txt")
    if [ "$SERVER_DIFF_RC" -ge 2 ]; then
      soft_fail "asset drift: diff of the Server/Cosmetics indexes exited $SERVER_DIFF_RC (0 and 1 are normal) — Server/Cosmetics drift is NOT reported; this run exits nonzero (3 unless verify-docs.sh fails)"
    elif [ "$N_MOD$N_DEL$N_ADD" = "000" ]; then
      info "no Server/Cosmetics drift — content identical to the baseline"
    else
      warn "$N_MOD modified, $N_ADD added, $N_DEL removed (server-{modified,added,removed}.txt)"
      head -40 "$REPORT/server-modified.txt" | sed 's/^/        M /'
      head -40 "$REPORT/server-added.txt"    | sed 's/^/        A /'
      head -40 "$REPORT/server-removed.txt"  | sed 's/^/        D /'
      TOTAL=$((N_MOD + N_ADD + N_DEL))
      [ "$TOTAL" -gt 120 ] && info "(lists truncated at 40 lines each — full lists in the report dir)"
    fi
  fi
else
  warn "ServerAssetsIndex baseline or extracted Server/ missing — Server drift skipped"
fi

# ---- 5. API drift old→new ----
# Every step below used to be trusted: the python's exit status was never read and a
# crash left api-changed-classes.txt empty or short, which read as "no signature changes"
# (and the source drift and the triage read the same file). A section that cannot show its
# result now says so (soft_fail, exit 3) and prints no rows and no "no changes" line. The
# checks run in this order and only the first that applies speaks, so each has its own
# message and a test that can tell it from the others:
#   1. diff exited 2 or more (1 is "they differ"). The python never reads javap-drift.diff,
#      so this protects the human-facing file only.
#   2. the python's exit status.
#   3. the python's `#COUNTS <classes in the old index> <classes in the new> <rows>` marker,
#      present exactly once (counted among the well-formed lines; a malformed one is none).
#      It is stripped before anything else reads the file.
#   4. the marker's row count equals the ADDED/REMOVED/CHANGED rows the file holds.
#   5. neither index is empty of classes: javap closes every class with one `}` at column 0
#      (measured equal to the declaration lines and the `Compiled from` lines: 10,353 at
#      0.7.2, 9,921 at 0.6.8), so an index with no `}` line is not a build.
#   6, 7. classes parsed: the python must have parsed exactly as many classes from the old
#      index, and from the new, as it has `}` lines. A javap format change that stops the
#      `decl` pattern matching (or misses `record`, `interface`) leaves a python that exits 0
#      and prints its marker, and folds the missed classes' members into the previous class.
#   8. rows: if the two indexes differ as SETS of lines (`Compiled from` lines dropped, the
#      rest sorted unique, so a reorder or a source-file rename is not a difference; the `}`
#      lines are the same in both), at least one row must exist. This catches TOTAL loss of
#      rows only. The sets come from grep and sort, not from the python's parse.
#   9, 10, 11. rows, class by class: an awk pass over the two indexes (index_class_counts, which
#      shares no code with the python) counts the classes only in the new index, only in the old,
#      and in both with different lines, and each count must equal the ADDED, REMOVED and CHANGED
#      rows. Checks 6 and 7 do NOT catch partial loss: a members() that attributes no member line
#      keeps every class parsed and N_CLS above 0, yet drops every CHANGED row (probe memtree,
#      review of 02aaa06..3baa29d, MEDIUM-2: 850 rows became 51 and the exit status stayed 0).
#      The definition of "changed" is the python's own: the SET of a class's lines, its
#      declaration line included, compared as sets (a reorder is no change); the class is keyed
#      by the name after the first class|interface|enum|record on a non-indented line, as
#      members() keys it. Equality, not >=, because the definitions agree: 504 added, 72 removed
#      and 850 changed at 0.6.8 -> 0.7.2 from both routes. They share the declaration pattern;
#      checks 6 and 7 hold that to the `}` count.
API_OK=1     # 0 when this section failed; the source drift (5b) says so
index_set() { grep -v '^Compiled from ' "$1" | LC_ALL=C sort -u; }
# index_class_counts OLD NEW: prints "<added> <removed> <changed>", classes counted as members()
# in the python of section 5 keys them: a non-indented line holding class|interface|enum|record
# and a name opens (or reopens) that class; an indented line belongs to the class last opened; any
# other line is nobody's. A class is CHANGED when it is in both indexes and its set of lines
# differs (size, or a line of one missing from the other).
index_class_counts() {
  LC_ALL=C awk '
    function add(side, cls, line) { if (!((side, cls, line) in has)) { has[side, cls, line] = 1; n[side, cls]++ } }
    { side = (FILENAME == ARGV[1]) ? 1 : 2
      if (side != last) { cur = ""; last = side }
      if (substr($0, 1, 1) != " ") {
        if (match($0, /(class|interface|enum|record) +[A-Za-z0-9_.$]+/)) {
          s = substr($0, RSTART, RLENGTH); sub(/^(class|interface|enum|record) +/, "", s)
          cur = s; seen[side, cur] = 1; add(side, cur, $0)
        }
      } else if (cur != "") add(side, cur, $0)
    }
    END {
      for (k in seen) { split(k, p, SUBSEP); if (p[1] == 1) { if ((2, p[2]) in seen) { if (n[1, p[2]] != n[2, p[2]]) chg[p[2]] = 1 } else removed++ } else if (!((1, p[2]) in seen)) added++ }
      for (k in has) { split(k, p, SUBSEP); if (p[1] == 1 && ((2, p[2]) in seen) && !((2, p[2], p[3]) in has)) chg[p[2]] = 1 }
      for (c in chg) changed++
      print added + 0, removed + 0, changed + 0 }' "$1" "$2"
}
section "API drift (javap index old → new)"
if [ -f "$REPORT/javap-index-old.txt" ] && [ -f "$JAR_CACHE/javap-index.txt" ]; then
  diff "$REPORT/javap-index-old.txt" "$JAR_CACHE/javap-index.txt" > "$REPORT/javap-drift.diff"
  API_DIFF_RC=$?
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
rows = 0
for cls in sorted(old.keys() | new.keys()):
    if cls not in new:   print(f"REMOVED {cls}"); rows += 1
    elif cls not in old: print(f"ADDED   {cls}"); rows += 1
    elif old[cls] != new[cls]:
        print(f"CHANGED {cls}"); rows += 1
        for line in sorted(old[cls] - new[cls]): print(f"  - {line.strip()}")
        for line in sorted(new[cls] - old[cls]): print(f"  + {line.strip()}")
print(f"#COUNTS {len(old)} {len(new)} {rows}")
PY
  API_PY_RC=$?
  API_MARK="$(grep -E '^#COUNTS [0-9]+ [0-9]+ [0-9]+$' "$REPORT/api-changed-classes.txt")"
  N_MARKS=$(grep -cE '^#COUNTS [0-9]+ [0-9]+ [0-9]+$' "$REPORT/api-changed-classes.txt" || true)
  sed -i '/^#COUNTS/d' "$REPORT/api-changed-classes.txt"
  N_CLS=$(grep -c '^\(ADDED\|REMOVED\|CHANGED\)' "$REPORT/api-changed-classes.txt" || true)
  read -r A_OLD A_NEW A_ROWS <<< "${API_MARK#"#COUNTS "}"
  C_OLD=$(grep -c '^}$' "$REPORT/javap-index-old.txt" || true); C_NEW=$(grep -c '^}$' "$JAR_CACHE/javap-index.txt" || true)
  N_ADDED=$(grep -c '^ADDED ' "$REPORT/api-changed-classes.txt" || true)
  N_REMOVED=$(grep -c '^REMOVED ' "$REPORT/api-changed-classes.txt" || true)
  N_CHGROWS=$(grep -c '^CHANGED ' "$REPORT/api-changed-classes.txt" || true)
  read -r X_ADDED X_REMOVED X_CHANGED < <(index_class_counts "$REPORT/javap-index-old.txt" "$JAR_CACHE/javap-index.txt")
  SUFFIX="this run exits nonzero (3 unless verify-docs.sh fails)"
  API_BAD=""
  if [ "$API_DIFF_RC" -ge 2 ]; then
    API_BAD="API drift: diff of the javap indexes exited $API_DIFF_RC (0 and 1 are normal) — javap-drift.diff is unreliable and the API drift is NOT reported"
  elif [ "$API_PY_RC" != 0 ]; then
    API_BAD="API drift: the python exited $API_PY_RC — added/removed/changed classes are NOT reported, and api-changed-classes.txt (read by the source drift and the triage) is incomplete"
  elif [ "$N_MARKS" != 1 ]; then
    API_BAD="API drift: the python printed $N_MARKS well-formed #COUNTS marker line(s), not one, so it cannot be known to have finished — classes are NOT reported"
  elif [ "$A_ROWS" != "$N_CLS" ]; then
    API_BAD="API drift: the python says it wrote $A_ROWS row(s) but api-changed-classes.txt holds $N_CLS — classes are NOT reported"
  elif [ "$C_OLD" = 0 ] || [ "$C_NEW" = 0 ]; then
    API_BAD="API drift: an index holds no class (javap closes $C_OLD in the old index, $C_NEW in the new, one '}' line each) — that is not a build, classes are NOT reported"
  elif [ "$A_OLD" != "$C_OLD" ]; then
    API_BAD="API drift: the python parsed $A_OLD class(es) from the old index but javap closes $C_OLD (one '}' line each) — it did not read the index whole, classes are NOT reported"
  elif [ "$A_NEW" != "$C_NEW" ]; then
    API_BAD="API drift: the python parsed $A_NEW class(es) from the new index but javap closes $C_NEW (one '}' line each) — it did not read the index whole, classes are NOT reported"
  elif [ "$N_CLS" = 0 ] && ! cmp -s <(index_set "$REPORT/javap-index-old.txt") <(index_set "$JAR_CACHE/javap-index.txt"); then
    API_BAD="API drift: the javap indexes differ but the python found no class added, removed or changed — classes are NOT reported"
  elif [ "$N_ADDED" != "${X_ADDED:-?}" ]; then
    API_BAD="API drift: the python wrote $N_ADDED ADDED row(s) but an awk pass over the two indexes finds ${X_ADDED:-?} class(es) only in the new one — classes are NOT reported"
  elif [ "$N_REMOVED" != "${X_REMOVED:-?}" ]; then
    API_BAD="API drift: the python wrote $N_REMOVED REMOVED row(s) but an awk pass over the two indexes finds ${X_REMOVED:-?} class(es) only in the old one — classes are NOT reported"
  elif [ "$N_CHGROWS" != "${X_CHANGED:-?}" ]; then
    API_BAD="API drift: the python wrote $N_CHGROWS CHANGED row(s) but an awk pass over the two indexes finds ${X_CHANGED:-?} class(es) in both whose lines differ — classes are NOT reported"
  fi
  if [ -n "$API_BAD" ]; then
    API_OK=0
    soft_fail "$API_BAD; $SUFFIX"
  elif [ "$N_CLS" = 0 ]; then
    info "no signature changes"
  else
    warn "$N_CLS class(es) added/removed/changed (api-changed-classes.txt)"
    grep '^\(ADDED\|REMOVED\|CHANGED\)' "$REPORT/api-changed-classes.txt" | sed 's/^/        /'
  fi
else
  warn "old index unavailable — API drift skipped"
fi

# ---- 5b. source drift old→new: what the signature diff cannot see ----
# Reports every top-level class whose decompiled source changed. It is labelled
# SIG+BODY only when that top-level class is itself in the signature diff; a
# change confined to a NESTED class's signature does not vouch for the outer
# body, so such a file stays BODY and is triaged as one.
# Two limits, both measured in review:
#  - Noise: CFR output is identical for the same jar and decompiler, but an
#    unchanged caller can re-render (a cast appears) when a callee's generic
#    signature changes. BODY rows can include such callers.
#  - Misses: a method CFR cannot decompile is emitted as the same stub
#    ("Decompilation failed") whatever its bytecode, so a change inside it is
#    invisible in the source (0.6.8 has 9 such methods in 8 files, one of them
#    PluginManager.loadManifest). For those files only, the classes' bytecode
#    hashes are compared and a change is reported as BYTECODE (or BLIND when a
#    side has no class hashes, so nothing could be compared).
section "Source drift (decompiled source old → new)"
OLD_DEC="$(meta "$SNAP/cache-meta.txt" decompiler)"; NEW_DEC="$(meta "$JAR_CACHE/cache-meta.txt" decompiler)"
OLD_SRC_STATE="$(meta "$SNAP/cache-meta.txt" src)"; NEW_SRC_STATE="$(meta "$JAR_CACHE/cache-meta.txt" src)"
if [ ! -d "$REPORT/src-old" ]; then
  warn "no decompiled source in the previous-build snapshot — source drift skipped (body-only and @Deprecated changes are NOT reported)"
elif [ ! -d "$JAR_CACHE/src" ] || [ "$(find "$JAR_CACHE/src" -name '*.java' | wc -l)" = 0 ]; then
  warn "the new cache has no decompiled source (${NEW_SRC_STATE:-state unknown}) — source drift skipped (body-only and @Deprecated changes are NOT reported)"
else
  for side in "snapshot:$OLD_SRC_STATE" "new cache:$NEW_SRC_STATE"; do
    [ "${side#*:}" = ok ] || warn "the ${side%%:*}'s decompile is not complete (src=${side#*:}) — classes missing from it are silently absent from this section"
  done
  [ -n "$OLD_DEC" ] && [ -n "$NEW_DEC" ] && [ "$OLD_DEC" != "$NEW_DEC" ] && \
    warn "decompiler differs between the snapshot ($OLD_DEC) and the new cache ($NEW_DEC) — expect most files to differ for that reason alone"
  diff -ru "$REPORT/src-old" "$JAR_CACHE/src" > "$REPORT/src-drift.diff"
  SRC_DIFF_RC=$?
  python3 - "$REPORT/src-old" "$JAR_CACHE/src" "$REPORT/api-changed-classes.txt" "$REPORT/src-drift.diff" \
            "$SNAP/class-hashes.txt" "$JAR_CACHE/class-hashes.txt" <<'PY' > "$REPORT/src-changed-classes.txt"
import os, re, sys, filecmp
old_root, new_root, api_path, diff_path, old_h, new_h = sys.argv[1:7]
def files(root):
    out = {}
    for d, _, fs in os.walk(root, followlinks=True):
        for f in fs:
            if f.endswith(".java"):
                p = os.path.join(d, f)
                out[os.path.relpath(p, root)[:-5].replace(os.sep, ".")] = p
    return out
def hashes(path):
    out = {}
    if os.path.exists(path):
        for l in open(path):
            h, _, c = l.strip().partition(" ")
            out[c] = h
    return out
old, new = files(old_root), files(new_root)
api, added, removed = set(), set(), set()      # exact names, nested ones keep their $
if os.path.exists(api_path):
    for line in open(api_path):
        m = re.match(r"(ADDED|REMOVED|CHANGED) +(\S+)", line)
        if m:
            api.add(m.group(2))
            if m.group(1) == "ADDED": added.add(m.group(2))
            if m.group(1) == "REMOVED": removed.add(m.group(2))
common = old.keys() & new.keys()
changed = sorted(c for c in common if not filecmp.cmp(old[c], new[c], shallow=False))
for c in changed:
    nested = sorted(a for a in api if a.startswith(c + "$"))
    label = "SIG+BODY" if c in api else "BODY    "
    print(f"{label} {c}" + (f"  (nested signature change: {', '.join(n.split('.')[-1] for n in nested)})" if nested and c not in api else ""))
# files whose decompile failed somewhere: equal source proves nothing there
oh, nh = hashes(old_h), hashes(new_h)
blind = sorted(c for c in common if c not in changed and
               any("Decompilation failed" in open(p, errors="replace").read() for p in (old[c], new[c])))
for c in blind:
    members = [k for k in (oh.keys() | nh.keys()) if k == c or k.startswith(c + "$")]
    if not (oh and nh):
        print(f"BLIND    {c}  (decompile failed in this file and no class hashes to compare)")
    elif any(oh.get(k) != nh.get(k) for k in members):
        print(f"BYTECODE {c}  (decompile failed in this file; its bytecode changed, its rendered source did not)")
# a file on one side only must be an added/removed class; anything else is a hole
for c in sorted(old.keys() - new.keys()):
    if c not in removed: print(f"UNEXPLAINED only-in-old {c}")
for c in sorted(new.keys() - old.keys()):
    if c not in added: print(f"UNEXPLAINED only-in-new {c}")
cur = None
for line in open(diff_path, encoding="utf-8", errors="replace"):
    if line.startswith("+++ "):
        p = line[4:].split("\t")[0].strip()
        cur = os.path.relpath(p, new_root)[:-5].replace(os.sep, ".") if p.endswith(".java") else None
    elif cur and line[:1] in "+-" and not line.startswith(("+++", "---")) and "@Deprecated" in line:
        print(f"DEPRECATION {'added  ' if line[0] == '+' else 'removed'} {cur}: {line[1:].strip()}")
print(f"#COUNTS {len(common)} {len(old.keys() - new.keys())} {len(new.keys() - old.keys())} {len(changed)} {len(blind)}")
PY
  SRC_PY_RC=$?
  # The python's result is not trusted (a crash here used to read as "compared 0 file(s) ...
  # no source changes"). The checks below run in this order and only the first that applies
  # speaks, so each has its own message and its own test. Every figure the python is held
  # to is counted by find, awk or grep, not by the python:
  #   1. diff -ru exited 2 or more (1 is "they differ"): src-drift.diff is truncated or
  #      empty, and the @Deprecated rows are read only from it.
  #   2. the python's exit status.
  #   3. its `#COUNTS` marker, present exactly once, with five numbers (counted among the
  #      well-formed lines; a malformed one is none).
  #   4. N_COMMON + N_ONLYOLD equals find's count of .java files under the old tree, and
  #      likewise N_COMMON + N_ONLYNEW for the new (-L: src-old is a symlink). A python that
  #      walked part of a tree, or none, disagrees.
  #   5. N_CHANGED >= the `+++ ` headers of .java files in the diff. Not `=`: diff reports a
  #      file with a NUL byte as "Binary files ... differ", with no header.
  #   6. N_DEP == the +/- lines naming @Deprecated inside those files (not the `+++ `/`--- `
  #      headers). This is the only guard on the DEPRECATION rows.
  #   7. N_CHANGED == the BODY and SIG+BODY rows the file holds. The python prints one row per
  #      changed file, so equality is exact. Check 5 only holds N_CHANGED to the diff; a python
  #      that computed `changed` and printed none of the rows read as a clean run (probe
  #      rowlosstree, review of 02aaa06..3baa29d, MEDIUM-1: 984 rows became 0 and the exit stayed 0).
  #   8. BYTECODE + BLIND rows <= N_BLIND, not ==. N_BLIND counts the unchanged files that hold a
  #      failed decompile; the python prints a row for such a file only when its bytecode hashes
  #      differ (BYTECODE) or cannot be compared (BLIND), so a file with equal hashes is counted
  #      and has no row. The bound catches excess rows; it cannot catch lost ones.
  SRC_MARK="$(grep -E '^#COUNTS [0-9]+ [0-9]+ [0-9]+ [0-9]+ [0-9]+$' "$REPORT/src-changed-classes.txt")"
  N_SMARKS=$(grep -cE '^#COUNTS [0-9]+ [0-9]+ [0-9]+ [0-9]+ [0-9]+$' "$REPORT/src-changed-classes.txt" || true)
  sed -i '/^#COUNTS/d' "$REPORT/src-changed-classes.txt"
  read -r N_COMMON N_ONLYOLD N_ONLYNEW N_CHANGED N_BLIND <<< "${SRC_MARK#"#COUNTS "}"
  N_BODY=$(grep -c '^BODY ' "$REPORT/src-changed-classes.txt" || true)
  N_BOTH=$(grep -c '^SIG+BODY' "$REPORT/src-changed-classes.txt" || true)
  N_BYTE=$(grep -c '^BYTECODE' "$REPORT/src-changed-classes.txt" || true)
  N_BLINDROWS=$(grep -c '^BLIND' "$REPORT/src-changed-classes.txt" || true)
  N_CHGROWS=$(grep -cE '^(BODY|SIG\+BODY) ' "$REPORT/src-changed-classes.txt" || true)
  N_DEP=$(grep -c '^DEPRECATION' "$REPORT/src-changed-classes.txt" || true)
  N_UNEX=$(grep -c '^UNEXPLAINED' "$REPORT/src-changed-classes.txt" || true)
  F_OLD=$(find -L "$REPORT/src-old" -type f -name '*.java' | wc -l); F_NEW=$(find -L "$JAR_CACHE/src" -type f -name '*.java' | wc -l)
  # the diff's own figures: `+++ ` headers of .java files, and +/- lines naming @Deprecated inside them
  read -r D_HDRS D_DEPS < <(awk '
    /^\+\+\+ / { p = substr($0, 5); sub(/\t.*/, "", p); java = (p ~ /\.java$/); if (java) h++; next }
    /^(\+\+\+|---)/ { next }          # as the python: a line starting +++ or --- is never a content line
    /^[-+]/    { if (java && index($0, "@Deprecated")) d++ }
    END        { print h + 0, d + 0 }' "$REPORT/src-drift.diff")
  SRC_BAD=""
  if [ "$SRC_DIFF_RC" -ge 2 ]; then
    SRC_BAD="source drift: diff -ru of the decompiled trees exited $SRC_DIFF_RC (0 and 1 are normal) — src-drift.diff, which the @Deprecated rows are read from, is truncated or empty and the source drift is NOT reported"
  elif [ "$SRC_PY_RC" != 0 ]; then
    SRC_BAD="source drift: the python exited $SRC_PY_RC — changed files, @Deprecated lines and bytecode changes are NOT reported, and src-changed-classes.txt (read by the triage) is incomplete"
  elif [ "$N_SMARKS" != 1 ]; then
    SRC_BAD="source drift: the python printed $N_SMARKS well-formed #COUNTS marker line(s), not one, so it cannot be known to have finished — changed files are NOT reported"
  elif [ "$((N_COMMON + N_ONLYOLD))" != "$F_OLD" ]; then
    SRC_BAD="source drift: the python counted $((N_COMMON + N_ONLYOLD)) .java file(s) in the old tree but find counts $F_OLD — it did not walk the tree whole, changed files are NOT reported"
  elif [ "$((N_COMMON + N_ONLYNEW))" != "$F_NEW" ]; then
    SRC_BAD="source drift: the python counted $((N_COMMON + N_ONLYNEW)) .java file(s) in the new tree but find counts $F_NEW — it did not walk the tree whole, changed files are NOT reported"
  elif ! [ "$N_CHANGED" -ge "$D_HDRS" ]; then
    SRC_BAD="source drift: src-drift.diff has $D_HDRS changed .java file header(s) but the python reports only $N_CHANGED changed file(s) — changed files are NOT reported"
  elif [ "$N_DEP" != "$D_DEPS" ]; then
    SRC_BAD="source drift: src-drift.diff has $D_DEPS added/removed @Deprecated line(s) but the python wrote $N_DEP DEPRECATION row(s) — @Deprecated changes are NOT reported"
  elif [ "$N_CHGROWS" != "$N_CHANGED" ]; then
    SRC_BAD="source drift: the python reports $N_CHANGED changed file(s) but wrote $N_CHGROWS BODY/SIG+BODY row(s) — changed files are NOT reported"
  elif [ "$((N_BYTE + N_BLINDROWS))" -gt "$N_BLIND" ]; then
    SRC_BAD="source drift: the python wrote $((N_BYTE + N_BLINDROWS)) BYTECODE/BLIND row(s) but counts only $N_BLIND unchanged file(s) with a failed decompile — the rows cannot be trusted"
  fi
  [ "$API_OK" = 1 ] || info "the API drift (section 5) failed, so this section's SIG+BODY / BODY labels and its UNEXPLAINED rows rest on an incomplete api-changed-classes.txt"
  if [ -n "$SRC_BAD" ]; then
    soft_fail "$SRC_BAD; this run exits nonzero (3 unless verify-docs.sh fails)"
  else
    info "compared $N_COMMON file(s) present in both builds ($N_ONLYOLD only in the old, $N_ONLYNEW only in the new); $N_CHANGED changed; $N_BLIND unchanged file(s) contain a failed decompile, $((N_BLIND - N_BLINDROWS)) of them checked by bytecode instead; full diff in src-drift.diff"
    [ "$N_BLINDROWS" -gt 0 ] && warn "$N_BLINDROWS file(s) with a failed decompile could NOT be checked (no class hashes on one side) — a change inside them is invisible (BLIND rows)"
    [ "$N_UNEX" -gt 0 ] && warn "$N_UNEX file(s) exist on one side only WITHOUT being an added/removed class in the API drift — a truncated decompile looks like this; their changes are NOT reported"
    grep -E '^(UNEXPLAINED|BLIND)' "$REPORT/src-changed-classes.txt" | sed -n '1,20p' | sed 's/^/        /'
    if [ "$((N_CHANGED + N_BYTE + N_DEP))" = 0 ]; then
      info "no source changes in the $N_COMMON file(s) present in both builds"
    else
      warn "$N_BODY file(s) changed with NO signature change on their top-level class (behaviour-only; invisible to the API drift above), $N_BOTH also changed signatures, $N_BYTE bytecode-only change(s) inside failed decompiles, $N_DEP @Deprecated line(s) added/removed (src-changed-classes.txt)"
      grep -E '^(BODY |BYTECODE|DEPRECATION)' "$REPORT/src-changed-classes.txt" | sed -n '1,60p' | sed 's/^/        /'
      [ "$((N_BODY + N_BYTE + N_DEP))" -gt 60 ] && info "(list truncated at 60 lines — full list in the report dir)"
    fi
  fi
fi

# ---- 5c. resource drift old→new: the jar's non-class entries ----
# Neither the javap index, the class hashes nor the decompiled source covers a
# resource, and the asset baselines cover Assets.zip only, so a changed
# migration/blocks/3_4.json or bundledDefaults/server.lang appeared nowhere.
# build-jar-cache.sh hashes EVERY non-class entry's content (no allowlist) and
# records an owner for each: Hypixel's by default, third-party only by a
# property the jar shows and no mark of Hypixel's overrides (rules x, b, c, a, e,
# h, l and d, written at the writer). Hypixel rows are
# listed in full; third-party rows collapse to counts by their first two path
# components. A snapshot or cache with no resource hashes is reported BLIND.
section "Resource drift (jar non-class entries, old → new)"
OLD_RH="$SNAP/resource-hashes.txt"; NEW_RH="$JAR_CACHE/resource-hashes.txt"
if [ ! -f "$SNAP/javap-index.txt" ]; then
  warn "no snapshot of a previous build — resource drift skipped"
elif [ ! -f "$NEW_RH" ]; then
  warn "BLIND: the new cache has no resource-hashes.txt (built by an older build-jar-cache.sh) — resources ADDED/REMOVED/CHANGED are NOT reported; rebuild the cache"
elif [ ! -f "$OLD_RH" ]; then
  warn "BLIND: the previous-build snapshot has no resource-hashes.txt (it predates resource hashing) — resources ADDED/REMOVED/CHANGED since that build are NOT reported; list them by hand: unzip -Z1 <old jar> | grep -v '\.class\$' and diff"
else
  python3 -I - "$OLD_RH" "$NEW_RH" "$SNAP/resource-owners.txt" "$JAR_CACHE/resource-owners.txt" "$REPORT/resource-drift.txt" "$REPORT/resources-old.txt" "$REPORT/resources-new.txt" <<'PY' > "$REPORT/resource-summary.txt"
import collections, os, sys
old_h, new_h, old_o, new_o, out_drift, out_old, out_new = sys.argv[1:8]
def hashes(p):
    d = {}
    for l in open(p, encoding="utf-8"):
        l = l.rstrip("\n")
        if l:
            h, path = l.split(maxsplit=1)
            d[path] = h
    return d
def owners(p):
    d = {}
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            l = l.rstrip("\n")
            if l:
                o, r, path = l.split(maxsplit=2)
                d[path] = (o, r)
    return d
oh, nh, oo, no = hashes(old_h), hashes(new_h), owners(old_o), owners(new_o)
# no owner recorded: the default, which keeps the row on the Hypixel side
own = lambda tab, p: tab.get(p, ("hypixel", "-"))
# A resource in both builds takes Hypixel's side if EITHER build puts it there: a
# services file that loses its com.hypixel line is refiled third-party by the new
# build, and taking the owner from the new build alone collapsed exactly the change
# (Hypixel dropping its own provider) a reader needs to see. The rule is the one the
# writer applies, a Hypixel mark beats the third-party presumption.
def own_both(p):
    n, o = own(no, p), own(oo, p)
    return n if n[0] == "hypixel" or o[0] != "hypixel" else o
rows = []
for p in sorted(oh.keys() | nh.keys()):
    if p not in oh:   rows.append(("ADDED", *own(no, p), p))
    elif p not in nh: rows.append(("REMOVED", *own(oo, p), p))
    elif oh[p] != nh[p]: rows.append(("CHANGED", *own_both(p), p))
with open(out_drift, "w") as f:
    for st, o, r, p in rows: f.write(f"{st} {o} {r} {p}\n")
# one list per build: the triage tests a bare name for uniqueness in the build the
# row's path exists in, and a union would make a resource that MOVED between
# builds look ambiguous with itself
for out_path, tab in ((out_old, oh), (out_new, nh)):
    with open(out_path, "w") as f:
        for p in sorted(tab): f.write(p + "\n")
top2 = lambda p: "/".join(p.split("/")[:2]) if p.count("/") > 1 else (p.split("/")[0] if "/" in p else "(root)")
print(f"#COUNTS {len(oh)} {len(nh)} {len(rows)} {sum(1 for r in rows if r[1] == 'hypixel')} {sum(1 for r in rows if r[1] != 'hypixel')} {len(no)}")
for o in ("hypixel", "third-party"):
    paths = [p for p in nh if own(no, p)[0] == o]
    rules = collections.Counter(own(no, p)[1] for p in paths)
    print(f"#SIDE {o} {len(paths)} rules " + " ".join(f"{k}:{v}" for k, v in sorted(rules.items())))
    held = collections.Counter(top2(p) for p in paths).most_common()
    print(f"#HOLDS {o} " + ", ".join(f"{k} ({v})" for k, v in held[:12]) + (f", and {len(held) - 12} more" if len(held) > 12 else ""))
for st, o, r, p in rows:
    if o == "hypixel": print(f"HYP {st} {r} {p}")
tp = collections.Counter((st, top2(p)) for st, o, r, p in rows if o != "hypixel")
for (st, k), v in sorted(tp.items()): print(f"TP {st} {k} {v}")
PY
  RES_PY_RC=$?
  if [ "$RES_PY_RC" != 0 ] || ! grep -q '^#COUNTS ' "$REPORT/resource-summary.txt"; then
    soft_fail "the resource comparison produced no result — resource drift is NOT reported; this run exits nonzero (3 unless verify-docs.sh fails)"
  else
    read -r N_OLDR N_NEWR N_RROWS N_RHYP N_RTP N_OWNED < <(sed -n 's/^#COUNTS //p' "$REPORT/resource-summary.txt")
    info "compared $N_OLDR resource(s) in the snapshot with $N_NEWR in the new build (every non-class, non-directory jar entry, hashed by content)"
    info "ownership: Hypixel's by default (d: no rule below applies); x: under com/hypixel/ is always Hypixel's; a third-party presumption when the jar shows one (b: native library; c: under META-INF/; a: its top-level directory also holds classes outside com/hypixel/; e: its directory mirrors a foreign package under com/) that a mark of Hypixel's overrides (h: hypixel or hytale in its path or bytes, in any case; l: a com/hypixel class names its path, or a native library's file name)"
    [ "$N_OWNED" = 0 ] && warn "the new cache has no resource-owners.txt — every row is classified as Hypixel's by default"
    sed -n 's/^#SIDE /        /p;s/^#HOLDS /          holds: /p' "$REPORT/resource-summary.txt"
    if [ "$N_RROWS" = 0 ]; then
      info "no resource drift in the $N_NEWR resource(s) of the new build (same content, whatever the zip timestamps)"
    else
      if [ "$N_RHYP" -gt 0 ]; then
        warn "$N_RHYP Hypixel-owned resource(s) added/removed/changed (resource-drift.txt)"
        sed -n 's/^HYP /        /p' "$REPORT/resource-summary.txt" | sed -n '1,60p'
      else
        info "no Hypixel-owned resource added, removed or changed"
      fi
      if [ "$N_RTP" -gt 0 ]; then
        info "$N_RTP third-party resource(s) added/removed/changed, collapsed:"
        sed -n 's/^TP /        /p' "$REPORT/resource-summary.txt"
      fi
    fi
  fi
fi

# ---- 6. triage greps: what do the docs/examples say about the changed things ----
section "Triage: docs/examples referencing the drift"
python3 "$REPO/maintenance/scripts/triage_drift.py" "$REPORT" "$ASSETS" > "$REPORT/triage.txt"
TRIAGE_RC=$?
grep -v '^#SUMMARY' "$REPORT/triage.txt" | sed 's/^/        /'
info "$(sed -n 's/^#SUMMARY //p' "$REPORT/triage.txt") (triage.txt)"
# triage_drift.py exits 2 when it could not read the report in full (its #ERROR lines, in the
# triage shown, say which rows and files): the triage is then missing matches. soft_fail
# prints the FAIL line and sets SOFT_RC, which finish() exits with unless verify-docs.sh failed.
if [ "$TRIAGE_RC" = 2 ]; then
  soft_fail "triage_drift.py exited 2 — it could not read the report in full, so the triage shown is INCOMPLETE (its #ERROR lines say which rows and files); this run exits nonzero (3 unless verify-docs.sh fails)"
elif [ "$TRIAGE_RC" != 0 ]; then
  soft_fail "triage_drift.py exited $TRIAGE_RC — it crashed or was killed, so the triage shown is missing or incomplete; this run exits nonzero (3 unless verify-docs.sh fails)"
fi

# exit status: verify-docs.sh's, unless that is 0 and a soft_fail happened (then 3)
finish() { [ "$1" = 0 ] && [ "$SOFT_RC" != 0 ] && exit "$SOFT_RC"; exit "$1"; }

# ---- 7. verify-docs ----
[ "$NO_VERIFY" = 1 ] && { section "verify-docs.sh"; info "skipped (--no-verify)"; finish 0; }
section "verify-docs.sh"
# shellcheck disable=SC2086
"$REPO/maintenance/scripts/verify-docs.sh" $NO_BUILD
VERIFY_RC=$?

# ---- remaining judgment checklist ----
section "Next steps (judgment — not automated)"
cat <<EOF
  1. Re-verify every doc/example the triage section flagged, against
     $ASSETS and $JAR_CACHE/src. For a "body" hit, read
     that class's hunk in src-drift.diff: its behaviour changed with no
     signature change.
  2. Review api-changed-classes.txt and src-changed-classes.txt for NEW
     plugin-facing API or behaviour worth documenting.
  3. Bump the doc stamps once everything is re-verified. Bump ONLY the page stamps
     and in-prose claims about the present build ("ships in", "still deprecated",
     "registered as of"). Never run a blanket replace: it would also rewrite
     introduction markers ("${OLD_VER:-<old>}+", "removed by ${OLD_VER:-<old>}"), which date a change.
       sed -i 's/Verified against ${OLD_VER:-<old>}\*\*/Verified against ${NEW_VER:-<new>}**/' docs/*.md
       grep -n '${OLD_VER:-<old>}' docs/*.md     # then judge each remaining line by hand
     …then rewrite the verification paragraph in CLAUDE.md by hand.
  4. Refresh both baselines (only after the docs are re-verified):
       cp $ASSETS/CommonAssetsIndex.hashes maintenance/baseline/
       maintenance/scripts/hash-server-assets.sh > maintenance/baseline/ServerAssetsIndex.hashes
     …and update maintenance/baseline/README.md's table (build, date,
     Assets.zip mtime/size, entry count, sha256).
  5. Re-run maintenance/scripts/verify-docs.sh — hard gates green, drift 0.
  6. Commit: chore: re-verify handbook against ${NEW_VER:-<new>} ($( [ -n "$BUILD_MARKER" ] && basename "$BUILD_MARKER" || echo build-N))
  Full reports: $REPORT
EOF

finish "$VERIFY_RC"
