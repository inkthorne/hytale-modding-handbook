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
# Exit code: non-zero if a cache step fails or verify-docs.sh hard-fails.

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
  if [ "$SNAP_SHA" = "$INSTALLED_SHA" ] || \
     { cmp -s "$SNAP/javap-index.txt" "$JAR_CACHE/javap-index.txt" && cmp -s "$SNAP/class-hashes.txt" "$JAR_CACHE/class-hashes.txt"; }; then
    warn "the snapshot IS the installed build (same jar, or byte-identical index and class hashes) — every drift section below compares it with itself"
  elif { [ -z "$SNAP_SHA" ] || [ ! -f "$SNAP/class-hashes.txt" ]; } && cmp -s "$SNAP/javap-index.txt" "$JAR_CACHE/javap-index.txt"; then
    # a snapshot from before jar_sha/class-hashes existed cannot prove it differs
    warn "the snapshot's index is byte-identical to the installed build's and it has no jar_sha/class hashes to tell them apart — it may be the installed build compared with itself"
  fi
  ln -s "$SNAP/javap-index.txt" "$REPORT/javap-index-old.txt"
  [ -d "$SNAP/src" ] && ln -s "$SNAP/src" "$REPORT/src-old"
else
  warn "no snapshot of a previous build at $SNAP (first run?) — the API and source drift sections will be skipped"
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

section "Server/Cosmetics asset drift vs baseline (generated index)"
if [ -f "$BASELINE_DIR/ServerAssetsIndex.hashes" ] && [ -d "$ASSETS/Server" ]; then
  "$REPO/maintenance/scripts/hash-server-assets.sh" "$ASSETS" > "$REPORT/ServerAssetsIndex.hashes"
  diff "$BASELINE_DIR/ServerAssetsIndex.hashes" "$REPORT/ServerAssetsIndex.hashes" \
    > "$REPORT/server-drift.diff"
  grep '^<' "$REPORT/server-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/server-old-paths.txt"
  grep '^>' "$REPORT/server-drift.diff" | cut -d' ' -f3- | LC_ALL=C sort > "$REPORT/server-new-paths.txt"
  comm -12 "$REPORT/server-old-paths.txt" "$REPORT/server-new-paths.txt" > "$REPORT/server-modified.txt"
  comm -23 "$REPORT/server-old-paths.txt" "$REPORT/server-new-paths.txt" > "$REPORT/server-removed.txt"
  comm -13 "$REPORT/server-old-paths.txt" "$REPORT/server-new-paths.txt" > "$REPORT/server-added.txt"
  N_MOD=$(wc -l < "$REPORT/server-modified.txt")
  N_DEL=$(wc -l < "$REPORT/server-removed.txt")
  N_ADD=$(wc -l < "$REPORT/server-added.txt")
  if [ "$N_MOD$N_DEL$N_ADD" = "000" ]; then
    info "no Server/Cosmetics drift — content identical to the baseline"
  else
    warn "$N_MOD modified, $N_ADD added, $N_DEL removed (server-{modified,added,removed}.txt)"
    head -40 "$REPORT/server-modified.txt" | sed 's/^/        M /'
    head -40 "$REPORT/server-added.txt"    | sed 's/^/        A /'
    head -40 "$REPORT/server-removed.txt"  | sed 's/^/        D /'
    TOTAL=$((N_MOD + N_ADD + N_DEL))
    [ "$TOTAL" -gt 120 ] && info "(lists truncated at 40 lines each — full lists in the report dir)"
  fi
else
  warn "ServerAssetsIndex baseline or extracted Server/ missing — Server drift skipped"
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
  read -r N_COMMON N_ONLYOLD N_ONLYNEW N_CHANGED N_BLIND < <(sed -n 's/^#COUNTS //p' "$REPORT/src-changed-classes.txt")
  sed -i '/^#COUNTS /d' "$REPORT/src-changed-classes.txt"
  N_BODY=$(grep -c '^BODY ' "$REPORT/src-changed-classes.txt" || true)
  N_BOTH=$(grep -c '^SIG+BODY' "$REPORT/src-changed-classes.txt" || true)
  N_BYTE=$(grep -c '^BYTECODE' "$REPORT/src-changed-classes.txt" || true)
  N_BLINDROWS=$(grep -c '^BLIND' "$REPORT/src-changed-classes.txt" || true)
  N_DEP=$(grep -c '^DEPRECATION' "$REPORT/src-changed-classes.txt" || true)
  N_UNEX=$(grep -c '^UNEXPLAINED' "$REPORT/src-changed-classes.txt" || true)
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

# ---- 6. triage greps: what do the docs/examples say about the changed things ----
section "Triage: docs/examples referencing the drift"
python3 "$REPO/maintenance/scripts/triage_drift.py" "$REPORT" "$ASSETS" > "$REPORT/triage.txt"
grep -v '^#SUMMARY' "$REPORT/triage.txt" | sed 's/^/        /'
info "$(sed -n 's/^#SUMMARY //p' "$REPORT/triage.txt") (triage.txt)"

# ---- 7. verify-docs ----
[ "$NO_VERIFY" = 1 ] && { section "verify-docs.sh"; info "skipped (--no-verify)"; exit 0; }
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

exit "$VERIFY_RC"
