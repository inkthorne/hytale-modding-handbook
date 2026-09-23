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
# The *-old snapshots are the only record of the previous build: once the caches
# are rebuilt, nothing else holds it. A --skip-caches re-triage therefore keeps
# them from the previous run instead of re-snapshotting the caches it did not
# rebuild. Re-snapshotting would make "old" equal "new" and empty every drift
# section on exactly the run meant to re-read them.
KEEP="$(mktemp -d)"
if [ "$SKIP_CACHES" = 1 ]; then
  for f in javap-index-old.txt src-old; do
    [ -e "$REPORT/$f" ] && mv "$REPORT/$f" "$KEEP/"
  done
fi
rm -rf "$REPORT" && mkdir -p "$REPORT"
info "report dir: $REPORT (wiped)"

# ---- 1. snapshot the previous build's jar cache ----
section "Snapshot previous javap index and decompiled source"
if [ "$SKIP_CACHES" = 1 ]; then
  for f in javap-index-old.txt src-old; do
    if [ -e "$KEEP/$f" ]; then mv "$KEEP/$f" "$REPORT/"; info "kept $f from the previous run (--skip-caches)"
    else warn "--skip-caches: no $f from a previous run — its drift section will be skipped"; fi
  done
else
  if [ -f "$JAR_CACHE/javap-index.txt" ]; then
    cp "$JAR_CACHE/javap-index.txt" "$REPORT/javap-index-old.txt"
    info "saved $(wc -l < "$REPORT/javap-index-old.txt") lines → javap-index-old.txt"
  else
    warn "no existing javap index — the API drift report will be skipped"
  fi
  # The source snapshot is what exposes changes a signature diff cannot see:
  # method bodies, annotations such as @Deprecated, and reads of inlined
  # compile-time constants. CFR output is deterministic for a given jar
  # (measured 2026-09-23: 6,564 files re-decompiled, 0 differing), so every
  # file the diff reports is a real change.
  if [ -d "$JAR_CACHE/src" ] && [ -z "$NO_SRC" ]; then
    cp -a "$JAR_CACHE/src" "$REPORT/src-old"
    info "saved $(find "$REPORT/src-old" -name '*.java' | wc -l) decompiled files → src-old/"
  elif [ -n "$NO_SRC" ]; then
    info "--no-src: source drift will be skipped"
  else
    warn "no existing decompiled source — the source drift report will be skipped"
  fi
fi
rm -rf "$KEEP"

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

section "Server/Cosmetics asset drift vs baseline (generated index)"
if [ -f "$REPO/maintenance/baseline/ServerAssetsIndex.hashes" ] && [ -d "$ASSETS/Server" ]; then
  "$REPO/maintenance/scripts/hash-server-assets.sh" "$ASSETS" > "$REPORT/ServerAssetsIndex.hashes"
  diff "$REPO/maintenance/baseline/ServerAssetsIndex.hashes" "$REPORT/ServerAssetsIndex.hashes" \
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
section "Source drift (decompiled source old → new)"
if [ -d "$REPORT/src-old" ] && [ -d "$JAR_CACHE/src" ]; then
  diff -ru "$REPORT/src-old" "$JAR_CACHE/src" > "$REPORT/src-drift.diff"
  python3 - "$REPORT/src-old" "$JAR_CACHE/src" "$REPORT/api-changed-classes.txt" "$REPORT/src-drift.diff" <<'PY' > "$REPORT/src-changed-classes.txt"
import os, re, sys, filecmp
old_root, new_root, api_path, diff_path = sys.argv[1:5]
def files(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".java"):
                p = os.path.join(d, f)
                out[os.path.relpath(p, root)[:-5].replace(os.sep, ".")] = p
    return out
old, new = files(old_root), files(new_root)
# classes whose signatures the javap diff already reported; a file covers its
# nested classes, so Outer$Inner counts against Outer
sig = set()
if os.path.exists(api_path):
    for line in open(api_path):
        m = re.match(r"(?:ADDED|REMOVED|CHANGED) +(\S+)", line)
        if m: sig.add(m.group(1).split("$")[0])
changed = sorted(c for c in old.keys() & new.keys() if not filecmp.cmp(old[c], new[c], shallow=False))
for c in changed:
    print(f"{'SIG+BODY' if c in sig else 'BODY    '} {c}")
# @Deprecated lines added or removed, attributed to their file
cur = None
for line in open(diff_path, encoding="utf-8", errors="replace"):
    if line.startswith("+++ "):
        p = line[4:].split("\t")[0].strip()
        cur = os.path.relpath(p, new_root)[:-5].replace(os.sep, ".") if p.endswith(".java") else None
    elif cur and line[:1] in "+-" and not line.startswith(("+++", "---")) and "@Deprecated" in line:
        print(f"DEPRECATION {'added  ' if line[0] == '+' else 'removed'} {cur}: {line[1:].strip()}")
PY
  N_BODY=$(grep -c '^BODY ' "$REPORT/src-changed-classes.txt" || true)
  N_BOTH=$(grep -c '^SIG+BODY' "$REPORT/src-changed-classes.txt" || true)
  N_DEP=$(grep -c '^DEPRECATION' "$REPORT/src-changed-classes.txt" || true)
  N_OLD=$(find "$REPORT/src-old" -name '*.java' | wc -l); N_NEW=$(find "$JAR_CACHE/src" -name '*.java' | wc -l)
  info "compared $N_OLD old / $N_NEW new decompiled file(s); full diff in src-drift.diff"
  if [ "$((N_BODY + N_BOTH + N_DEP))" = 0 ]; then
    info "no source changes in files present in both builds (added/removed classes are in the API drift above)"
  else
    warn "$N_BODY file(s) changed with NO signature change (behaviour-only; invisible to the API drift above), $N_BOTH also changed signatures, $N_DEP @Deprecated line(s) added/removed (src-changed-classes.txt)"
    grep -E '^(BODY |DEPRECATION)' "$REPORT/src-changed-classes.txt" | head -60 | sed 's/^/        /'
    [ "$((N_BODY + N_DEP))" -gt 60 ] && info "(list truncated at 60 lines — full list in the report dir)"
  fi
else
  info "no src-old snapshot (first run, --no-src, or no decompiler) — source drift skipped"
fi

# ---- 6. triage greps: what do the docs/examples say about the changed things ----
section "Triage: docs/examples referencing the drift"
# Asset keys. A doc names an asset in one of three ways, and each needs its own key:
#   - by id: `Tool_Shears_Basic`, with no extension. Matched on the file's stem,
#     as a whole word, but only when that stem names exactly one shipped file AND
#     is id-shaped (contains "_"). Measured over all 60,693 shipped paths
#     (2026-09-23): unique-but-plain stems such as `Migrations/0.json`, `Entity.png`
#     or `None.json` flagged up to 134 files each until the "_" rule was added.
#   - by a unique file name with a plain stem: `Entity.png`. Matched as the whole
#     name with its extension, bounded so that `1.json` does not match
#     `Zone1_Plains1.json`.
#   - by an ambiguous file name: `en-US/server.lang`. Matched as parent/name,
#     so a pt-BR change does not flag pages that cite only en-US.
#   - by a wildcard: `Server/Languages/*/server.lang`, `<lang>/server.lang`.
#     Matched for every file of that name, because such a claim spans all of them.
# Output lines are "<kind> <thing> → <files>"; kind "body" marks a class whose
# source changed with no signature change (section 5b).
python3 - "$REPORT" "$ASSETS" <<'PY' > "$REPORT/triage.txt"
import os, re, sys, collections
report, assets = sys.argv[1:3]
def lines(name):
    p = os.path.join(report, name)
    return [l.strip() for l in open(p)] if os.path.exists(p) else []
corpus = {}
for root in ("docs", "examples"):
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ("build", ".gradle")]
        for f in fs:
            p = os.path.join(d, f)
            b = open(p, "rb").read()
            if b"\0" not in b:                       # skip binaries, like grep -I
                corpus[p] = b.decode("utf-8", "replace")
# every shipped path, to decide whether a name is ambiguous
shipped = []
idx = os.path.join(assets, "CommonAssetsIndex.hashes")
if os.path.exists(idx):
    shipped += [l.split(" ", 1)[1].strip() for l in open(idx) if " " in l]
shipped += [l.split(" ", 1)[1].strip() for l in lines("ServerAssetsIndex.hashes") if " " in l]
names = collections.Counter(os.path.basename(p) for p in shipped)
stems = collections.Counter(os.path.splitext(os.path.basename(p))[0] for p in shipped)
def hits(pred):
    return sorted(k for k, t in corpus.items() if pred(t))
def asset_hits(p):
    name = os.path.basename(p); stem = os.path.splitext(name)[0]
    if names[name] <= 1 and stems[stem] <= 1 and "_" in stem and len(stem) >= 5 \
            and re.fullmatch(r"\w+", stem):
        rx = re.compile(r"(?<![\w])" + re.escape(stem) + r"(?![\w])")
        return hits(rx.search)
    if names[name] <= 1:
        rx = re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w.])")
        return hits(rx.search)
    key = os.path.basename(os.path.dirname(p)) + "/" + name
    wild = re.compile(r"(?:\*|<[^<>/\s]+>)/" + re.escape(name) + r"(?![\w.])")
    return hits(lambda t: key in t or wild.search(t))
out = []
for f in ("assets-modified.txt", "assets-removed.txt", "server-modified.txt", "server-removed.txt"):
    for p in lines(f):
        if p: out.append(("asset", p, asset_hits(p)))
classes = {}
for l in lines("api-changed-classes.txt"):
    m = re.match(r"(?:ADDED|REMOVED|CHANGED) +(\S+)", l)
    if m: classes[m.group(1)] = "class"
for l in lines("src-changed-classes.txt"):
    m = re.match(r"BODY +(\S+)", l)
    if m: classes.setdefault(m.group(1), "body")
for cls, kind in sorted(classes.items()):
    simple = cls.split(".")[-1].split("$")[-1]
    rx = re.compile(r"(?<![\w])" + re.escape(simple) + r"(?![\w])")
    out.append((kind, cls, hits(rx.search)))
for kind, thing, h in out:
    if h: print(f"{kind} {thing} → {' '.join(h)}")
print(f"#SUMMARY {len(out)} changed thing(s) checked, {sum(1 for o in out if o[2])} referenced in docs/examples")
PY
grep -v '^#SUMMARY' "$REPORT/triage.txt" | sed 's/^/        /'
info "$(sed -n 's/^#SUMMARY //p' "$REPORT/triage.txt") (triage.txt)"

# ---- 7. verify-docs ----
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
