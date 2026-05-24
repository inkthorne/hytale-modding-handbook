#!/usr/bin/env bash
#
# verify-docs.sh — regression checks for docs/ and examples/ against the
# installed Hytale game build. Catches outdated/fabricated documentation after
# a game update.
#
# Usage:
#   maintenance/scripts/verify-docs.sh [--no-build] [--fields]
#
#   --no-build   Skip compiling the example projects (faster).
#   --fields     Enable the (noisy, advisory) per-format field-existence check.
#
# Env overrides:
#   HYTALE_JAR      Path to HytaleServer.jar
#   HYTALE_ASSETS   Path to the extracted Assets.zip dir (default ~/.cache/hytale-assets)
#
# Exit code: non-zero if any HARD check fails. Advisory/INFO checks never fail
# the run (they print findings for human review).

set -u
# Resolve repo root: this script lives at maintenance/scripts/, so go up two levels.
cd "$(dirname "$0")/../.." || exit 2
REPO="$(pwd)"

NO_BUILD=0
DO_FIELDS=0
for arg in "$@"; do
  case "$arg" in
    --no-build) NO_BUILD=1 ;;
    --fields)   DO_FIELDS=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

HARD_FAILS=0
section() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
pass()    { printf '  \033[32mPASS\033[0m  %s\n' "$1"; }
fail()    { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; HARD_FAILS=$((HARD_FAILS+1)); }
warn()    { printf '  \033[33mWARN\033[0m  %s\n' "$1"; }
info()    { printf '  INFO  %s\n' "$1"; }

# ---- resolve the Hytale install (mirrors examples/hytale-paths.gradle) ----
if [ -n "${APPDATA:-}" ]; then
  ROOT="$APPDATA/Hytale"
elif [ -d "$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale" ]; then
  ROOT="$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale"
else
  ROOT="$HOME/AppData/Roaming/Hytale"
fi
JAR="${HYTALE_JAR:-$ROOT/install/release/package/game/latest/Server/HytaleServer.jar}"
ASSETS="${HYTALE_ASSETS:-$HOME/.cache/hytale-assets}"

section "Environment"
if [ -f "$JAR" ]; then info "jar:    $JAR"; else warn "jar not found: $JAR (jar-based checks will be skipped)"; fi
if [ -d "$ASSETS" ]; then info "assets: $ASSETS"; else warn "assets not found: $ASSETS (asset checks skipped; see CLAUDE.md to extract)"; fi
# report the installed build marker if present
BUILD_MARKER="$(find "$ROOT/install/release/package/sig" -maxdepth 1 -name 'build-*' 2>/dev/null | head -1)"
[ -n "$BUILD_MARKER" ] && info "build:  $(basename "$BUILD_MARKER")"

# =====================================================================
section "[HARD] Class references resolve via javap"
# Every com.hypixel.* class named in docs/ must exist in the jar.
if [ -f "$JAR" ] && command -v javap >/dev/null 2>&1; then
  OUT="$(python3 - "$JAR" <<'PY'
import re, subprocess, sys, glob
jar = sys.argv[1]
fqcn = re.compile(r'com\.hypixel\.hytale(?:\.[a-z0-9_]+)+\.[A-Z][A-Za-z0-9_]*')
refs = {}
for f in glob.glob("docs/*.md"):
    for m in fqcn.findall(open(f).read()):
        refs.setdefault(m, set()).add(f.split('/')[-1])
missing = []
for c in sorted(refs):
    if subprocess.run(["javap","-cp",jar,c],capture_output=True).returncode != 0:
        a = c.rsplit(".",1)                       # try inner-class form Foo$Bar
        if subprocess.run(["javap","-cp",jar,a[0]+"$"+a[1]],capture_output=True).returncode != 0:
            missing.append((c, ", ".join(sorted(refs[c]))))
print(f"CHECKED {len(refs)}")
for c, files in missing:
    print(f"MISSING {c}  ({files})")
PY
)"
  CHECKED="$(echo "$OUT" | awk '/^CHECKED/{print $2}')"
  MISS="$(echo "$OUT" | grep -c '^MISSING' || true)"
  if [ "$MISS" -eq 0 ]; then
    pass "$CHECKED class references all resolve"
  else
    fail "$MISS unresolved class reference(s):"
    echo "$OUT" | grep '^MISSING' | sed 's/^MISSING/      /'
  fi
else
  warn "skipped (no jar or javap)"
fi

# =====================================================================
section "[HARD] Intra-doc anchor links resolve"
OUT="$(python3 - <<'PY'
import re, glob, os
from collections import defaultdict
def slug(t):
    s=t.strip().lower(); s=re.sub(r"[^\w\- ]","",s); return s.replace(" ","-")
anchors={}
for f in glob.glob("docs/*.md"):
    seen=defaultdict(int); a=set()
    for line in open(f):
        m=re.match(r"^#{1,6}\s+(.*?)\s*#*$",line)
        if m:
            b=slug(m.group(1)); n=seen[b]; seen[b]+=1; a.add(b if n==0 else f"{b}-{n}")
    anchors[os.path.basename(f)]=a
bad=0
lr=re.compile(r"\[[^\]]*\]\(([a-zA-Z0-9_\-]+\.md)?#([a-zA-Z0-9_\-]+)\)")
for f in glob.glob("docs/*.md"):
    bn=os.path.basename(f)
    for ln,line in enumerate(open(f),1):
        for m in lr.finditer(line):
            tf=m.group(1) or bn; an=m.group(2)
            if tf not in anchors or an not in anchors[tf]:
                bad+=1; print(f"BROKEN {bn}:{ln} -> {tf}#{an}")
print(f"COUNT {bad}")
PY
)"
BAD="$(echo "$OUT" | awk '/^COUNT/{print $2}')"
if [ "$BAD" -eq 0 ]; then pass "all anchor links resolve"; else
  fail "$BAD broken anchor link(s):"; echo "$OUT" | grep '^BROKEN' | sed 's/^BROKEN/      /'
fi

# =====================================================================
section "[ADVISORY] Referenced asset files exist"
# High-signal media references (.blockymodel/.blockyanim/.png/.ogg under
# Common/Server). JSON paths are skipped — many are illustrative examples.
if [ -d "$ASSETS" ]; then
  OUT="$(python3 - "$ASSETS" <<'PY'
import re, glob, os, sys
assets=sys.argv[1]
pat=re.compile(r'\b((?:Common|Server|Cosmetics)/[\w/\-]+\.(?:blockymodel|blockyanim|png|ogg|ui))')
missing=set(); seen=0
for f in glob.glob("docs/*.md"):
    for p in pat.findall(open(f).read()):
        seen+=1
        if not os.path.exists(os.path.join(assets,p)): missing.add(p)
print(f"SEEN {seen}")
for p in sorted(missing): print(f"MISS {p}")
PY
)"
  M="$(echo "$OUT" | grep -c '^MISS' || true)"
  if [ "$M" -eq 0 ]; then pass "all referenced media asset paths exist"; else
    warn "$M media path(s) not found (may be renamed/removed, or intentional examples):"
    echo "$OUT" | grep '^MISS' | sed 's/^MISS/      /'
  fi
else
  warn "skipped (no extracted assets)"
fi

# =====================================================================
section "[INFO] Asset drift vs baseline"
# Tells you exactly which Common assets changed since the baseline was captured.
if [ -f maintenance/baseline/CommonAssetsIndex.hashes ] && [ -f "$ASSETS/CommonAssetsIndex.hashes" ]; then
  D="$(diff <(sort maintenance/baseline/CommonAssetsIndex.hashes) <(sort "$ASSETS/CommonAssetsIndex.hashes") | grep -c '^[<>]' || true)"
  if [ "$D" -eq 0 ]; then
    info "0 changed Common assets — docs verified against this build still apply"
  else
    warn "$D changed line(s) vs baseline — re-verify docs referencing those assets"
    info "see: diff maintenance/baseline/CommonAssetsIndex.hashes \"$ASSETS/CommonAssetsIndex.hashes\""
  fi
else
  warn "skipped (missing baseline or live index)"
fi

# =====================================================================
section "[ADVISORY] JSON code blocks parse"
# Note: these docs intentionally use fenced fragments (e.g. \"Field\": { ... });
# non-parsing blocks are usually fragments, not errors. Reported for awareness.
OUT="$(python3 - <<'PY'
import re, glob, os
bad=0
for f in glob.glob("docs/*.md"):
    for i,b in enumerate(re.findall(r'```json\n(.*?)```', open(f).read(), re.S)):
        if "..." in b or "//" in b or "$" in b: continue
        try:
            import json; json.loads(b)
        except Exception:
            bad+=1
print(f"FRAG {bad}")
PY
)"
FRAG="$(echo "$OUT" | awk '/^FRAG/{print $2}')"
info "$FRAG json block(s) are fragments / not standalone-parseable (expected for this doc style)"

# =====================================================================
section "[ADVISORY] Doc-type tags are present and consistent"
# Every doc should declare **Doc type:**. A doc not tagged "Java API" that
# references >=2 distinct com.hypixel.* classes may be mis-tagged (a single
# incidental base-class mention in a JSON/DSL doc is normal and not flagged).
OUT="$(python3 - <<'PY'
import re, glob, os
untagged=[]; mismatch=[]; counts={}
type_re=re.compile(r'\*\*Doc type:\*\*\s*([^\n·]+?)(?:\s*·|\n)')
cls_re=re.compile(r'com\.hypixel\.hytale(?:\.[a-z0-9_]+)+\.[A-Z][A-Za-z0-9_]*')
for p in sorted(glob.glob("docs/*.md")):
    bn=os.path.basename(p); txt=open(p).read()
    m=type_re.search(txt)
    if not m:
        untagged.append(bn); continue
    typ=m.group(1).strip(); counts[typ]=counts.get(typ,0)+1
    classes=set(cls_re.findall(txt))
    if "Java API" not in typ and len(classes) >= 2:
        mismatch.append((bn,typ,len(classes)))
for t in sorted(counts): print(f"COUNT {counts[t]} {t}")
for u in untagged: print(f"UNTAGGED {u}")
for bn,typ,n in mismatch: print(f"MISMATCH {bn} [{typ}] references {n} distinct com.hypixel.* classes")
PY
)"
echo "$OUT" | awk '/^COUNT/{printf "  %-4s %s\n",$2,substr($0,index($0,$3))}'
U="$(echo "$OUT" | grep -c '^UNTAGGED' || true)"
MM="$(echo "$OUT" | grep -c '^MISMATCH' || true)"
[ "$U" -eq 0 ] && pass "all docs carry a **Doc type:** tag" || { warn "$U untagged doc(s):"; echo "$OUT" | grep '^UNTAGGED' | sed 's/^UNTAGGED/      /'; }
if [ "$MM" -eq 0 ]; then pass "no JSON/DSL-tagged doc references Java classes"; else
  warn "$MM doc(s) tagged non-Java but reference com.hypixel.* classes (review tag or refs):"
  echo "$OUT" | grep '^MISMATCH' | sed 's/^MISMATCH/      /'
fi

# =====================================================================
section "[ADVISORY] Gotcha error strings trace to the jar"
# In a "## Gotchas" section, a literal runtime/game error string is written as a
# bold-backtick lead at the start of a bullet:  - **`exact string`** -> cause...
# This check verifies each such string actually occurs in the jar's string pool,
# so a fabricated or stale error message gets flagged (it can't silently rot).
# Bullets that lead with **Symptom:** or **Compile error** are NOT jar-checked
# (compiler text and behavioral symptoms aren't game-jar string constants).
if [ -f "$JAR" ]; then
  POOL="$(mktemp)"
  # Extract string constants from the game classes once (a few seconds).
  TMPCLS="$(mktemp -d)"
  ( cd "$TMPCLS" && unzip -oq "$JAR" 'com/hypixel/*' 2>/dev/null )
  find "$TMPCLS" -name '*.class' -print0 | xargs -0 strings -n 6 2>/dev/null > "$POOL"
  OUT="$(python3 - "$POOL" <<'PY'
import re, glob, os, sys
pool = open(sys.argv[1], encoding="utf-8", errors="replace").read()
# capture the bullet lead: - **`...`**  (only inside a "## Gotchas" section)
lead = re.compile(r'^\s*-\s+\*\*`([^`]+)`\*\*')
skip = re.compile(r'^\s*-\s+\*\*(Symptom|Compile)', re.I)
checked = miss = 0
misses = []
for f in sorted(glob.glob("docs/*.md")):
    bn = os.path.basename(f)
    in_g = False
    for ln, line in enumerate(open(f), 1):
        h = re.match(r'^##\s+(.*)', line)
        if h:
            in_g = "gotcha" in h.group(1).lower()
            continue
        if not in_g or skip.match(line):
            continue
        m = lead.match(line)
        if not m:
            continue
        s = m.group(1).strip()
        checked += 1
        if s not in pool:
            miss += 1
            misses.append(f"{bn}:{ln}: {s}")
print(f"CHECKED {checked}")
for x in misses:
    print(f"MISS {x}")
PY
)"
  C="$(echo "$OUT" | awk '/^CHECKED/{print $2}')"
  M="$(echo "$OUT" | grep -c '^MISS' || true)"
  if [ "${C:-0}" -eq 0 ]; then
    info "no bold-backtick gotcha strings to verify yet"
  elif [ "$M" -eq 0 ]; then
    pass "$C gotcha error string(s) all trace to the jar"
  else
    warn "$M of $C gotcha error string(s) not found in the jar (fabricated, paraphrased, or stale?):"
    echo "$OUT" | grep '^MISS' | sed 's/^MISS/      /'
  fi
  rm -rf "$TMPCLS" "$POOL"
else
  warn "skipped (no jar)"
fi

# =====================================================================
section "[INFO] Version stamps on topic pages"
# Topic pages should carry a build stamp so readers know what build the page
# describes. Navigational pages (00/01/02) are exempt.
python3 - <<'PY'
import re, glob, os
nav = {"00-overview.md", "01-index.md", "02-structure.md"}
stamp = re.compile(r'Verified against build-\d+')
missing = []
total = 0
for p in sorted(glob.glob("docs/*.md")):
    bn = os.path.basename(p)
    if bn in nav:
        continue
    total += 1
    if not stamp.search(open(p).read()):
        missing.append(bn)
print(f"  {total-len(missing)}/{total} topic pages carry a build stamp")
for m in missing:
    print(f"      unstamped: {m}")
PY

# =====================================================================
if [ "$DO_FIELDS" -eq 1 ]; then
section "[ADVISORY] Documented JSON fields appear in real assets"
if [ -d "$ASSETS" ]; then
  python3 - "$ASSETS" <<'PY'
import re, glob, os, sys, subprocess
assets=sys.argv[1]
# asset dir comes from each doc's "**Assets:** `dir`" tag (single source of truth)
key_re = re.compile(r'"([A-Za-z][A-Za-z0-9_]+)"\s*:')
adir_re = re.compile(r'\*\*Assets:\*\*\s*`([^`]+)`')
checked=0
for p in sorted(glob.glob("docs/*.md")):
    txt=open(p).read()
    m=adir_re.search(txt)
    if not m: continue                     # only docs that declare an asset dir
    adir=m.group(1)
    if adir=="Common": continue            # too broad to field-check meaningfully
    keys=set()
    for b in re.findall(r'```json\n(.*?)```', txt, re.S):
        keys.update(key_re.findall(b))
    if not keys: continue
    d=os.path.join(assets,adir); checked+=1
    suspect=[k for k in sorted(keys)
             if subprocess.run(["grep","-rl",f'"{k}"',d],capture_output=True).returncode!=0]
    doc=os.path.basename(p)
    if suspect:
        print(f"  {doc}: {len(suspect)} documented key(s) absent from {adir} (review — may be example/user-defined):")
        print("      "+", ".join(suspect))
    else:
        print(f"  {doc}: all documented keys present in {adir}")
print(f"  ({checked} docs field-checked via their **Assets:** tag)")
PY
else
  warn "skipped (no extracted assets)"
fi
fi

# =====================================================================
if [ "$NO_BUILD" -eq 0 ]; then
section "[HARD] Example projects compile against the jar"
if [ -f "$JAR" ]; then
  for d in examples/*/; do
    [ -f "$d/build.gradle" ] || continue
    name="$(basename "$d")"
    if ( cd "$d" && ./gradlew -q jar >/tmp/vd-$name.log 2>&1 ); then
      pass "$name builds"
    else
      fail "$name failed to build (see /tmp/vd-$name.log):"
      grep -iE "error:" "/tmp/vd-$name.log" | head -5 | sed 's/^/      /'
    fi
  done
else
  warn "skipped (no jar)"
fi
else
  section "[HARD] Example builds"; info "skipped (--no-build)"
fi

# =====================================================================
section "Summary"
if [ "$HARD_FAILS" -eq 0 ]; then
  printf '  \033[32mAll hard checks passed.\033[0m Review any WARN items above.\n'
  exit 0
else
  printf '  \033[31m%d hard check(s) failed.\033[0m\n' "$HARD_FAILS"
  exit 1
fi
