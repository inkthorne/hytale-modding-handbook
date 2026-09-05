#!/usr/bin/env bash
#
# verify-docs.sh — regression checks for docs/ and examples/ against the
# installed Hytale game build. Catches outdated/fabricated documentation after
# a game update.
#
# Usage:
#   maintenance/scripts/verify-docs.sh [--no-build] [--no-fields]
#
#   --no-build   Skip compiling the example projects (faster).
#   --no-fields  Skip the JSON field-existence check (advisory; calibrated
#                via maintenance/scripts/fields-skiplist.txt).
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
DO_FIELDS=1
for arg in "$@"; do
  case "$arg" in
    --no-build)  NO_BUILD=1 ;;
    --fields)    DO_FIELDS=1 ;;  # legacy no-op (now the default)
    --no-fields) DO_FIELDS=0 ;;
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
# Decompiled source cache (maintenance/scripts/build-jar-cache.sh). Only the
# "Type"-value gate reads it; every other check works off the jar or the assets.
SRC_CACHE="${HYTALE_SRC_CACHE:-$HOME/.cache/hytale-jar/src}"

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
section "[HARD] Documented API symbols resolve in the jar"
# Beyond class existence (above), this verifies the *members* docs name in the
# high-confidence static/qualified form `Receiver.member` (where Receiver is a
# real jar class) actually exist on that class — walking superclasses so
# inherited members count. Calibrated to skip JSON/DSL key paths, prose negative
# examples ("there is no `Codec.BOOL`"), locally-declared example types, and
# private-but-present members. See maintenance/scripts/check-symbols.py.
if [ -f "$JAR" ]; then
  OUT="$(python3 maintenance/scripts/check-symbols.py "$JAR" 2>&1)"
  C="$(echo "$OUT" | awk '/^CHECKED_MEMBERS/{print $2}')"
  N="$(echo "$OUT" | awk '/^FINDINGS/{print $2}')"
  if [ "${N:-1}" -eq 0 ]; then
    pass "$C documented member symbol(s) all resolve"
  else
    fail "$N documented symbol(s) do not resolve in the jar (stale/typo/fabricated):"
    echo "$OUT" | grep '^FIND' | sed 's/^FIND/      /'
  fi
else
  warn "skipped (no jar)"
fi

# =====================================================================
section "[HARD] Anchor links resolve (cross-doc: target file honoured)"
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
# README.md is the repo's only exhaustive human-facing page list, and nothing
# measured it. Every page split ever performed here left its new pages out —
# npc-spawning.md and npc-combat.md from the 2026-09-04 npc-roles split, then
# world-chunks.md and world-lifecycle-events.md from the world.md one — plus
# substantive pages that simply drifted out (camera, encounters, mounts,
# trigger-volumes, universe-saves, world-events). 16 of 71 were absent when this
# gate was written. Same reasoning as the arrears list: re-reading README cannot
# reveal an omission, because the omission is what is missing from what you read.
# docs/index.md is exempt — a curated "Popular references" landing page, not an
# index of everything.
section "[HARD] Every docs page is listed in README.md"
OUT="$(python3 - <<'RMPY'
import glob, os, re
EXEMPT = {"index.md"}
readme = open("README.md").read()
# Match the explicit link path, not a bare filename: "index.md" is a SUBSTRING of
# "01-index.md", so a substring test reports a page as listed when it is not.
linked = set(re.findall(r'\]\(\./docs/([A-Za-z0-9._-]+\.md)\)', readme))
pages = sorted(os.path.basename(f) for f in glob.glob("docs/*.md"))
for b in pages:
    if b not in linked and b not in EXEMPT:
        print(f"MISSING {b}")
print(f"PAGES {len(pages)}")
print(f"LISTED {len([b for b in pages if b in linked])}")
print(f"EXEMPT {len([b for b in pages if b in EXEMPT])}")
RMPY
)"
RM_PAGES="$(echo "$OUT"  | awk '/^PAGES/{print $2}')"
RM_LISTED="$(echo "$OUT" | awk '/^LISTED/{print $2}')"
RM_EXEMPT="$(echo "$OUT" | awk '/^EXEMPT/{print $2}')"
RM_BAD="$(echo "$OUT" | grep -c '^MISSING ' || true)"
if [ "${RM_PAGES:-0}" -eq 0 ]; then
  fail "README page check scanned 0 docs pages — treating as a broken check, not a clean run"
elif [ "$RM_BAD" -eq 0 ]; then
  pass "all docs pages listed in README ($RM_LISTED of $RM_PAGES linked, $RM_EXEMPT exempt)"
else
  fail "$RM_BAD docs page(s) absent from README.md ($RM_LISTED of $RM_PAGES linked, $RM_EXEMPT exempt):"
  echo "$OUT" | sed -n 's/^MISSING /      not linked from README: /p'
fi

# Nothing measured page sizes before 2026-09-04, so invariant 5's arrears list
# was only ever checked when a human chose to measure — and three pages went
# over the line unlisted that way (npc-roles.md, then world.md and prefabs.md).
# Re-reading the list cannot find an omission: the omission is what is missing
# from the thing being read. This gate does the measuring on every run.
section "[HARD] Page-size arrears list is current"
OUT="$(python3 - <<'PY'
import glob, os, re
THRESHOLD = 1500
LIST = "maintenance/page-size-arrears.txt"

if not os.path.exists(LIST):
    print(f"FATAL list file missing: {LIST}"); print("PARSED 0"); print("MEASURED 0"); raise SystemExit

entries = []
for line in open(LIST):
    line = line.split("#", 1)[0].strip()
    if line:
        entries.append(line)

sizes = {}
for f in sorted(glob.glob("docs/*.md")):
    bn = os.path.basename(f)
    with open(f) as fh:
        sizes[bn] = sum(1 for _ in fh)

listed = set(entries)
over = {b for b, n in sizes.items() if n > THRESHOLD}

for b in sorted(over - listed):
    print(f"UNLISTED {b} {sizes[b]}")
for b in sorted(listed - over):
    if b not in sizes:
        print(f"MISSING {b}")
    else:
        print(f"UNDER {b} {sizes[b]}")
for b in sorted(listed & over):
    print(f"OK {b} {sizes[b]}")

print(f"PARSED {len(entries)}")
print(f"MEASURED {len(sizes)}")
print(f"THRESHOLD {THRESHOLD}")
PY
)"
PS_PARSED="$(echo "$OUT"  | awk '/^PARSED/{print $2}')"
PS_MEASURED="$(echo "$OUT" | awk '/^MEASURED/{print $2}')"
PS_THRESHOLD="$(echo "$OUT" | awk '/^THRESHOLD/{print $2}')"
PS_BAD="$(echo "$OUT" | grep -cE '^(UNLISTED|UNDER|MISSING) ')"
if echo "$OUT" | grep -q '^FATAL'; then
  fail "$(echo "$OUT" | sed -n 's/^FATAL //p')"
elif [ "${PS_PARSED:-0}" -eq 0 ]; then
  # A parser that finds nothing reports zero unlisted pages forever. That is a
  # broken checker, not a clean corpus, so it fails rather than passing quietly.
  fail "arrears list parsed 0 entries (empty or unreadable: maintenance/page-size-arrears.txt) — treating as a broken check, not a clean run"
else
  echo "$OUT" | grep '^OK ' | awk '{printf "        listed: %-26s %s lines\n", $2, $3}'
  if [ "$PS_BAD" -eq 0 ]; then
    pass "arrears list current ($PS_MEASURED page(s) measured, $PS_PARSED entr(y/ies) parsed, threshold $PS_THRESHOLD)"
  else
    warn "$PS_BAD arrears discrepanc(y/ies) ($PS_MEASURED page(s) measured, $PS_PARSED entr(y/ies) parsed, threshold $PS_THRESHOLD):"
    echo "$OUT" | sed -n 's/^UNLISTED \(.*\) \(.*\)$/      over the line and UNLISTED: \1 (\2 lines) — split it, or add it to maintenance\/page-size-arrears.txt/p'
    echo "$OUT" | sed -n 's/^UNDER \(.*\) \(.*\)$/      listed but now UNDER: \1 (\2 lines) — remove it from maintenance\/page-size-arrears.txt/p'
    echo "$OUT" | sed -n 's/^MISSING \(.*\)$/      listed but no such page: \1 — stale entry/p'
  fi
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
# Deliberate "your-file-here" placeholder names used in how-to prose (a real
# path here would mislead readers into thinking the file ships with the game):
PLACEHOLDERS = {
    "Common/UI/Custom/MyCustomPage.ui", "Common/UI/Custom/MyPage.ui",
    "Common/UI/Custom/MyUI.ui", "Common/UI/Custom/Pages/MyPage.ui",
    "Common/UI/Custom/Pages/Settings.ui",
}
def exists(p):
    # Candidate 1: literal path under the assets root.
    cands=[p]
    # Candidate 2: .ui TexturePath form — inside a .ui file, "Common/X.png"
    # resolves relative to Common/UI/Custom/ (the game's own Common.ui uses
    # e.g. "Common/Buttons/Primary.png" for UI/Custom/Common/Buttons/...).
    if p.startswith("Common/"):
        cands.append("Common/UI/Custom/"+p)
    # Each candidate may ship only as its @2x hi-dpi variant on disk.
    for c in list(cands):
        root,ext=os.path.splitext(c)
        cands.append(root+"@2x"+ext)
    return any(os.path.exists(os.path.join(assets,c)) for c in cands)
missing=set(); seen=0
for f in glob.glob("docs/*.md"):
    for p in pat.findall(open(f).read()):
        seen+=1
        if p in PLACEHOLDERS: continue
        if not exists(p): missing.add(p)
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
  # LC_ALL=C: locale collation treats '-'/'_' as equal, making sort order
  # unstable for near-duplicate paths (e.g. Face-Scar.png vs Face_Scar.png)
  D="$(diff <(LC_ALL=C sort maintenance/baseline/CommonAssetsIndex.hashes) <(LC_ALL=C sort "$ASSETS/CommonAssetsIndex.hashes") | grep -c '^[<>]' || true)"
  if [ "$D" -eq 0 ]; then
    info "0 changed Common assets — docs verified against this build still apply"
  else
    warn "$D changed line(s) vs baseline — re-verify docs referencing those assets"
    info "see: diff <(LC_ALL=C sort maintenance/baseline/CommonAssetsIndex.hashes) <(LC_ALL=C sort \"$ASSETS/CommonAssetsIndex.hashes\")"
  fi
else
  warn "skipped (missing baseline or live index)"
fi
# Server/Cosmetics half (our own generated index — Hytale ships one for Common/ only).
if [ -f maintenance/baseline/ServerAssetsIndex.hashes ] && [ -d "$ASSETS/Server" ]; then
  D="$(maintenance/scripts/hash-server-assets.sh "$ASSETS" | diff maintenance/baseline/ServerAssetsIndex.hashes - | grep -c '^[<>]' || true)"
  if [ "$D" -eq 0 ]; then
    info "0 changed Server/Cosmetics assets — data-format docs verified against this build still apply"
  else
    warn "$D changed line(s) vs ServerAssetsIndex baseline — re-verify docs referencing those assets"
    info "see: maintenance/scripts/hash-server-assets.sh | diff maintenance/baseline/ServerAssetsIndex.hashes -"
  fi
else
  warn "Server-assets drift skipped (missing ServerAssetsIndex.hashes baseline or extracted Server/)"
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
untagged=[]; mismatch=[]; counts={}; multi=[]
# Anchored: the tag is a line, never a prose mention. Unanchored, a page whose
# real tag line was dropped would silently adopt the first inline `**Doc type:**`
# in its body — a plausible wrong type AND a false green on the untagged check.
type_re=re.compile(r'^\*\*Doc type:\*\*\s*([^\n·]+?)(?:\s*·|\n)', re.M)
tag_line_re=re.compile(r'^\*\*Doc type:\*\*', re.M)
cls_re=re.compile(r'com\.hypixel\.hytale(?:\.[a-z0-9_]+)+\.[A-Z][A-Za-z0-9_]*')
# Provenance exclusion. A section documenting a JSON "Type" cites the class that
# implements it on a **Package:** line; that is a citation, not an API surface.
# Exclusion requires POSITIVE evidence of JSON documentation, not merely the
# absence of Java — absence alone is how a check turns into a silent pass.
#
# Four scoping rules, each added because a fixture defeated the version without
# it (fixtures D-G, 2026-09-04):
#   D  page-level backstop: any ```java fence or | Method / | Signature table
#      ANYWHERE on the page disqualifies the whole page. Java surface written
#      with simple names in a section that has no **Package:** line is otherwise
#      invisible to both the section scan and the FQCN recurrence test.
#   E  a citation's section may contain no fence other than ```json — strictly
#      stronger than "no ```java", and it covers bare signature fences, the
#      blind spot CLAUDE.md queues as gate 2.
#   F  positive evidence is a ```json fence or a | Property / | Key table.
#      | Field is NOT accepted: it appears 33 times in the corpus and is
#      genuinely ambiguous between a JSON field and a Java one.
#   G  the simple name of an excluded class may not appear inside any non-json
#      fence on the page; the FQCN test alone cannot see how Java is written.
head_re=re.compile(r'^(#{1,6})\s', re.M)
pkg_re=re.compile(r'^\*\*Package:\*\*.*$', re.M)
json_re=re.compile(r'^```json', re.M)
ptab_re=re.compile(r'^\|\s*(?:Property|Key)\s*\|', re.M)
java_re=re.compile(r'^```java', re.M | re.I)
mtab_re=re.compile(r'^\|\s*(?:Methods?|Signatures?)\s*\|', re.M)
fence_re=re.compile(r'^```(\w*)', re.M)
def _tag(s): return s.lower()
def _sections(txt):
    hs=[(m.start(), len(m.group(1))) for m in head_re.finditer(txt)]
    for i,(pos,lvl) in enumerate(hs):
        end=len(txt)
        for pos2,lvl2 in hs[i+1:]:
            if lvl2<=lvl: end=pos2; break
        yield pos,end
def _openers(body):
    return [_tag(m.group(1)) for i,m in enumerate(fence_re.finditer(body)) if i%2==0]
def _nonjson_fence_text(txt):
    out=[]; f=[(m.start(), m.end(), m.group(1)) for m in fence_re.finditer(txt)]
    for i in range(0,len(f)-1,2):
        if _tag(f[i][2])!='json': out.append(txt[f[i][1]:f[i+1][0]])
    return "\n".join(out)
def provenance(txt):
    if java_re.search(txt) or mtab_re.search(txt): return set()      # D
    prov=set(); spans=[]
    for s,e in _sections(txt):
        body=txt[s:e]
        for pm in pkg_re.finditer(body):
            cs=set(cls_re.findall(pm.group(0)))
            if not cs: continue
            if not (json_re.search(body) or ptab_re.search(body)): continue   # F
            if any(tag!='json' for tag in _openers(body)): continue           # E
            prov|=cs; spans.append((s+pm.start(), s+pm.end()))
    if not prov: return set()
    masked=list(txt)
    for a,b in spans:
        for i in range(a,b): masked[i]=' '
    outside=set(cls_re.findall(''.join(masked)))
    nonjson=_nonjson_fence_text(txt)                                          # G
    return {c for c in prov - outside if c.rsplit('.',1)[-1] not in nonjson}
# Calibration skip-list: the residual — citations in prose or fences that the
# provenance rule above cannot classify. See maintenance/scripts/doctype-skiplist.txt.
skip=set()
sl="maintenance/scripts/doctype-skiplist.txt"
if os.path.exists(sl):
    for line in open(sl):
        line=line.split("#",1)[0].strip()
        if line: skip.add(line)
scanned=0; candidates=0; used=set(); prov_cites=0; prov_pages=set(); fell=[]
for p in sorted(glob.glob("docs/*.md")):
    bn=os.path.basename(p); txt=open(p).read()
    scanned+=1
    m=type_re.search(txt)
    if not m:
        untagged.append(bn); continue
    # The page-level tag is whichever comes first, so a second marker further down
    # would silently become the page's type if the first were ever moved or dropped.
    # Count only line-anchored markers: an inline `**Doc type:**` in prose (01-index
    # describes the convention) is a mention, not a tag.
    n_tags=len(tag_line_re.findall(txt))
    if n_tags > 1: multi.append((bn,n_tags))
    typ=m.group(1).strip(); counts[typ]=counts.get(typ,0)+1
    classes=set(cls_re.findall(txt))
    if "Java API" in typ: continue
    # Only computed for non-Java pages, so the reported count is exclusions that
    # actually changed an outcome rather than incidental matches elsewhere.
    prov=provenance(txt)
    if prov:
        prov_cites+=len(prov); prov_pages.add(bn)
        # A page that drops from candidate to non-candidate *because* of exclusion is
        # otherwise indistinguishable from one that never had two FQCNs. The backstop
        # above is a blacklist of Java-surface signals and cannot be closed by
        # enumeration; reporting this transition makes every escape a number someone
        # can look at, whether or not the blacklist ever learns its cause.
        if len(classes) >= 2 and len(classes - prov) < 2: fell.append(bn)
        classes-=prov
    if len(classes) < 2: continue
    candidates+=1
    if bn in skip:
        used.add(bn); continue
    mismatch.append((bn,typ,len(classes)))
# A skip entry that no longer matches a candidate is dead calibration: the page
# was renamed, retagged, or dropped below the threshold. Report it rather than
# letting it sit ready to re-suppress if the file ever returns.
for stale in sorted(skip - used): print(f"STALESKIP {stale}")
print(f"DENOM {scanned} {candidates} {len(used)} {prov_cites} {len(prov_pages)} {len(fell)}")
for b in fell: print(f"FELL {b}")
for t in sorted(counts): print(f"COUNT {counts[t]} {t}")
for u in untagged: print(f"UNTAGGED {u}")
for bn,n in multi: print(f"MULTITAG {bn} carries {n} **Doc type:** lines; only the first is read")
for bn,typ,n in mismatch: print(f"MISMATCH {bn} [{typ}] references {n} distinct com.hypixel.* classes")
PY
)"
echo "$OUT" | awk '/^COUNT/{printf "  %-4s %s\n",$2,substr($0,index($0,$3))}'
U="$(echo "$OUT" | grep -c '^UNTAGGED' || true)"
MM="$(echo "$OUT" | grep -c '^MISMATCH' || true)"
SCANNED="$(echo "$OUT" | awk '/^DENOM/{print $2}')"
DEN="$(echo "$OUT" | awk '/^DENOM/{print $3}')"
SKIPPED="$(echo "$OUT" | awk '/^DENOM/{print $4}')"
PROVC="$(echo "$OUT" | awk '/^DENOM/{print $5}')"
PROVP="$(echo "$OUT" | awk '/^DENOM/{print $6}')"
FELL="$(echo "$OUT" | awk '/^DENOM/{print $7}')"
SS="$(echo "$OUT" | grep -c '^STALESKIP' || true)"
MT="$(echo "$OUT" | grep -c '^MULTITAG' || true)"
[ "$U" -eq 0 ] && pass "all docs carry a **Doc type:** tag" || { warn "$U untagged doc(s):"; echo "$OUT" | grep '^UNTAGGED' | sed 's/^UNTAGGED/      /'; }
EXAMINED=$(( ${DEN:-0} - ${SKIPPED:-0} ))
if [ "$MM" -eq 0 ]; then
  pass "no JSON/DSL-tagged doc references Java classes (${SCANNED:-0} doc(s) scanned, $EXAMINED of ${DEN:-0} candidate(s) examined, ${SKIPPED:-0} audited-skip, ${PROVC:-0} Package-line citation(s) on ${PROVP:-0} page(s) treated as provenance, ${FELL:-0} page(s) fell below threshold because of it)"
else
  warn "$MM of ${DEN:-0} candidate doc(s) tagged non-Java but reference com.hypixel.* classes (review tag or refs; ${PROVC:-0} Package-line citation(s) on ${PROVP:-0} page(s) already treated as provenance):"
  echo "$OUT" | grep '^MISMATCH' | sed 's/^MISMATCH/      /'
fi
[ "$MT" -eq 0 ] || { warn "$MT doc(s) carry more than one **Doc type:** line (only the first is read):"; echo "$OUT" | grep '^MULTITAG' | sed 's/^MULTITAG/      /'; }
[ "$SS" -eq 0 ] || { warn "$SS stale doctype-skiplist entr(ies) — page renamed, retagged, or no longer a candidate:"; echo "$OUT" | grep '^STALESKIP' | sed 's/^STALESKIP/      /'; }

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
  rm -f "$POOL"     # keep $TMPCLS — the coverage check below reuses it
else
  warn "skipped (no jar)"
fi

# =====================================================================
section "[ADVISORY] Documentation coverage vs public API surface"
# Reports plugin-facing public classes that no doc page mentions, so coverage
# holes resurface after every game update. The "plugin-facing surface" is
# inferred from two signals (there is no public/internal annotation in the jar):
#   1. Package  — candidate top-level (no $) classes under server.core.**,
#      component, math that are PUBLIC (read from the class-file access flags).
#   2. Intent   — whether com.hypixel.hytale.builtin.* references the class
#      (Class-pool entries + type descriptors mined from Utf8 constants).
# Builtin-referenced + public = high-confidence plugin API. Absence of a builtin
# reference is a weak signal only: core JavaPlugin *modules* (blockhealth, voice,
# cosmetics, ...) expose APIs they don't themselves call, so a public class in a
# plugin-facing package can still be intended for plugins. Treat this as a guide
# for humans, never a gate.
if [ -n "${TMPCLS:-}" ] && [ -d "$TMPCLS" ]; then
  python3 - "$TMPCLS" <<'PY'
import sys, os, struct, re, glob
from collections import defaultdict
CLS = sys.argv[1]
ACC_PUBLIC = 0x0001
CAND = ("com/hypixel/hytale/server/core/", "com/hypixel/hytale/component/",
        "com/hypixel/hytale/math/")
BUILTIN = "com/hypixel/hytale/builtin"

def parse(path):
    """(access_flags, [class-ref names], [utf8 values]) or None."""
    d = open(path, "rb").read()
    if d[:4] != b"\xca\xfe\xba\xbe": return None
    n = struct.unpack_from(">H", d, 8)[0]; off = 10; u = {}; cl = {}; i = 1
    while i < n:
        t = d[off]; off += 1
        if t == 1:
            ln = struct.unpack_from(">H", d, off)[0]; off += 2
            u[i] = d[off:off+ln].decode("utf-8", "replace"); off += ln
        elif t in (3, 4): off += 4
        elif t in (5, 6): off += 8; i += 1
        elif t == 7: cl[i] = struct.unpack_from(">H", d, off)[0]; off += 2
        elif t == 8: off += 2
        elif t in (9, 10, 11, 12): off += 4
        elif t == 15: off += 3
        elif t == 16: off += 2
        elif t in (17, 18): off += 4
        elif t in (19, 20): off += 2
        else: return None
        i += 1
    acc = struct.unpack_from(">H", d, off)[0]
    return acc, [u[v] for v in cl.values() if v in u], list(u.values())

# 1. candidate public top-level classes
cand = {}
for pre in CAND:
    base = os.path.join(CLS, pre)
    for root, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith(".class") or "$" in fn: continue
            p = parse(os.path.join(root, fn))
            if p and (p[0] & ACC_PUBLIC):
                internal = os.path.relpath(os.path.join(root, fn), CLS)[:-6].replace(os.sep, "/")
                cand[internal] = p[0]

# 2. builtin references (Class entries + type descriptors in Utf8)
bref = set(); dre = re.compile(r'com/hypixel/hytale/[A-Za-z0-9_/$]+')
for root, _, files in os.walk(os.path.join(CLS, BUILTIN)):
    for fn in files:
        if not fn.endswith(".class"): continue
        p = parse(os.path.join(root, fn))
        if not p: continue
        for r in p[1]:
            r = r.strip("[")
            if r.startswith("L") and r.endswith(";"): r = r[1:-1]
            bref.add(r)
        for s in p[2]:
            for m in dre.findall(s): bref.add(m.split("$", 1)[0])

# 3. harvest documented symbols, in tiers, so "described in prose" is not
#    conflated with "absent". For each doc we gather:
#      dfq        - FQCNs mentioned anywhere
#      code_names - capitalized identifiers inside code contexts (fenced ``` or
#                   inline `...`), i.e. used in a signature/snippet
#      alltext    - full concatenated doc text, for plain-prose word matching
dfq = set(); code_names = set(); alltext = []; codetext = []
fq = re.compile(r'com\.hypixel\.hytale(?:\.[a-z0-9_]+)+\.[A-Z][A-Za-z0-9_]*')
fenced = re.compile(r'```.*?```', re.S)
inline = re.compile(r'`[^`\n]+`')
ident = re.compile(r'\b[A-Z][A-Za-z0-9_]*\b')
hump = re.compile(r'[a-z][A-Z]')          # CamelCase marker (RequiredArg, ModelComponent)
for f in glob.glob("docs/*.md"):
    t = open(f).read(); alltext.append(t); dfq.update(fq.findall(t))
    code = " ".join(fenced.findall(t)) + " " + " ".join(inline.findall(t))
    codetext.append(code); code_names.update(ident.findall(code))
alltext = "\n".join(alltext); codetext = "\n".join(codetext)

def prose_mentioned(simple):
    # A bare prose mention only counts for names specific enough not to collide
    # with ordinary capitalized English: CamelCase (has a lower->Upper hump) or
    # reasonably long. Short single-word names (Ban, Coord, Order) must appear
    # in a code context to count, handled by the code_names tier.
    if not (re.search(r'[a-z][A-Z]', simple) or len(simple) >= 6):
        return False
    return re.search(r'\b' + re.escape(simple) + r'\b', alltext) is not None

def tier(internal):
    fqcn = internal.replace("/", "."); simple = internal.rsplit("/", 1)[-1]
    if fqcn in dfq or simple in code_names:
        return "documented"                       # FQCN or whole-word token in code
    # CamelCase names taught via a builder method (RequiredArg -> withRequiredArg)
    # show up only as a substring inside a code context. Restrict to CamelCase so
    # short words (Ban, Order, Coord) can't substring-collide.
    if hump.search(simple) and simple in codetext:
        return "documented"
    if prose_mentioned(simple):
        return "mentioned"
    return "absent"

def subpkg(internal):
    for pre in CAND:
        if internal.startswith(pre):
            rest = internal[len(pre):].split("/"); tag = pre.split("/")[-2]
            return tag + ("/" + "/".join(rest[:-1]) if len(rest) > 1 else "")
    return "?"

pub_b = [c for c in cand if c in bref]
tiers = {"documented": [], "mentioned": [], "absent": []}
for c in pub_b: tiers[tier(c)].append(c)
print(f"  {len(cand)} public top-level candidate classes "
      f"(server.core/component/math)")
print(f"  {len(pub_b)} are also builtin-referenced (high-confidence plugin API). Of those:")
print(f"      documented      {len(tiers['documented']):>4}  (named in a code block / signature)")
print(f"      mentioned-only  {len(tiers['mentioned']):>4}  (in prose but no snippet — thin, candidate to deepen)")
print(f"      ABSENT          {len(tiers['absent']):>4}  (named nowhere — the real coverage gap)")
mg = defaultdict(int)
for c in tiers["mentioned"]: mg[subpkg(c)] += 1
if mg:
    print("  mentioned-only by subpackage:")
    for g in sorted(mg, key=lambda k: (-mg[k], k)):
        print(f"      [{mg[g]:>3}] {g}")
print("  ABSENT by subpackage:")
ag = defaultdict(list)
for c in tiers["absent"]: ag[subpkg(c)].append(c.rsplit("/", 1)[-1])
for g in sorted(ag, key=lambda k: (-len(ag[k]), k)):
    print(f"      [{len(ag[g]):>3}] {g}")
    print("            " + ", ".join(sorted(ag[g])))
PY
  rm -rf "$TMPCLS"
else
  warn "skipped (no extracted game classes)"
fi

# =====================================================================
section "[INFO] Version stamps on topic pages"
# Topic pages should carry a build stamp so readers know what build the page
# describes. Navigational pages (00/01/02) are exempt.
python3 - <<'PY'
import re, glob, os
nav = {"00-overview.md", "01-index.md", "02-structure.md"}
stamp = re.compile(r'Verified against (?:build-\d+|\d+\.\d+\.\d+)')
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
section "[ADVISORY] Documented JSON fields appear in real assets or codecs"
if [ -d "$ASSETS" ]; then
  OUT="$(python3 - "$ASSETS" "${HYTALE_JAR_CACHE:-$HOME/.cache/hytale-jar}/src" <<'FIELDSPY'
import re, glob, os, sys, subprocess
assets=sys.argv[1]; jarsrc=sys.argv[2]
# asset dir comes from each doc's "**Assets:** `dir`" tag (single source of truth)
key_re = re.compile(r'"([A-Za-z][A-Za-z0-9_]+)"\s*:')
adir_re = re.compile(r'\*\*Assets:\*\*\s*`([^`]+)`')
# Calibration skip-list: "doc.md:Key" entries for keys that are deliberately
# user-defined/illustrative in that doc's examples. '#' comments allowed.
skip=set()
sl="maintenance/scripts/fields-skiplist.txt"
if os.path.exists(sl):
    for line in open(sl):
        line=line.split("#",1)[0].strip()
        if line: skip.add(line)
def found_in(needle, d):
    return os.path.isdir(d) and subprocess.run(
        ["grep","-rl",needle,d],capture_output=True).returncode==0
checked=0; flagged=0
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
    doc=os.path.basename(p)
    suspect=[]
    for k in sorted(keys):
        if f"{doc}:{k}" in skip: continue
        needle=f'"{k}"'
        # Resolution ladder: the doc's declared dir -> anywhere in the game
        # assets -> the decompiled jar (codec accepts the key even if no
        # shipped asset uses it) -> flagged.
        if found_in(needle, d): continue
        if found_in(needle, assets): continue
        if found_in(needle, jarsrc): continue
        suspect.append(k)
    if suspect:
        flagged+=len(suspect)
        print(f"SUSPECT {doc}: "+", ".join(suspect))
print(f"CHECKED {checked}")
print(f"FLAGGED {flagged}")
FIELDSPY
)"
  N="$(echo "$OUT" | sed -n 's/^FLAGGED //p')"
  C="$(echo "$OUT" | sed -n 's/^CHECKED //p')"
  if [ "${N:-0}" -eq 0 ]; then
    pass "all documented JSON keys trace to assets or codecs ($C docs checked)"
  else
    warn "$N documented key(s) found in neither assets nor jar codecs (fabricated or renamed?):"
    echo "$OUT" | grep '^SUSPECT' | sed 's/^SUSPECT/      /'
  fi
else
  warn "skipped (no extracted assets)"
fi
fi

# =====================================================================
section "[HARD] The gates' own fixtures pass"
# Until 2026-09-05 nothing ran these. verify-docs.sh ran every PRODUCT gate —
# symbols, snippets, doc-type, page size, type-values — and the three gates that
# verify the gates were exactly the ones left outside it: the repo checked its docs
# on every run and its checkers never. That is "when a component gets a fixture, ask
# what consumes it" one level further out than where it was first applied.
#
# Nothing had rotted when this was wired in (44/44, 51/51, 13/13), so this closes a
# prospective gap rather than a live defect. It compounds with a real one though:
# outside this script, a fixture's expected sets rot invisibly — the checker is
# edited, verify-docs stays green, and the divergence surfaces only when someone
# runs the fixture by hand and meets a wall of red at the worst possible moment,
# which is precisely when "delete the failing mutations" is the cheap repair.
#
# Cost is ~4s against a run that compiles six Gradle projects, so --mutations is
# included rather than deferred behind a flag.
# Floors: MIN_MUTATIONS in each --mutations runner, and FIX_RAN below.
# One runner per LINE, because two of them carry an argument and word-splitting a
# space-separated variable turns `--mutations` into a runner of its own. Reading
# lines also removes an accident the previous form relied on: with the arg-carrying
# runners as literals in the `for`, the loop always executed at least once, so
# FIX_RAN could not reach 0 and its floor below was untestable. Folding them in was
# the obvious tidy-up and would have removed that guarantee silently.
FIXTURE_RUNNERS='check-codec-fixture.py
check-registry-fixture.py
check-section-binder-fixture.py
check-type-values-fixture.py --mutations
check-defaults-fixture.py --mutations'
# The summary prefixes each runner is expected to print. NOT `| ` — an earlier
# version ended the alternation with a bare space, so every indented line counted,
# including a traceback's `  File "..."` lines. Harmless then (a traceback arrives
# with RC!=0 and is caught first) but it meant the counter was not measuring what
# its name said, in a section about figures meaning what they claim.
FIX_SUMMARY='^(CORPUS|FIXTURE|TRAPS|INDEPENDENT|BASELINE|MUTATIONS)\b'
FIX_OK=1; FIX_RAN=0; FIX_NAMES=""
while IFS= read -r R; do
  [ -n "$R" ] || continue
  # shellcheck disable=SC2086
  OUT="$(python3 maintenance/scripts/$R 2>&1)"; RC=$?
  FIX_RAN=$(( FIX_RAN + 1 ))
  FIX_NAMES="${FIX_NAMES}${FIX_NAMES:+, }${R%% *}"
  N="$(printf '%s\n' "$OUT" | grep -cE "$FIX_SUMMARY")"
  if [ "$RC" -ne 0 ]; then
    FIX_OK=0
    fail "${R%% *} failed:"
    printf '%s\n' "$OUT" | sed 's/^/    /'
  elif [ "$N" -eq 0 ]; then
    # PER-RUNNER floor, not per-section. Summed across three runners, one going
    # silent was masked by the other two: stubbing check-codec-fixture.py to
    # `sys.exit(0)` with no output removed `FIXTURE 44 type(s)` and `TRAPS 6
    # case(s)` from the evidence while the section still printed "all 3 ... pass".
    # Same shape as the `covered` denominator aggregated across files, and the
    # `audited skiplist` bucket claimed by a higher-priority source — a figure
    # summed over sources cannot show one source reaching zero.
    FIX_OK=0
    fail "${R%% *} exited 0 but printed no summary line — it ran, or did it?"
  else
    printf '%s\n' "$OUT" | grep -E '^(FIXTURE|TRAPS|INDEPENDENT|MUTATIONS)\b' | sed 's/^/        /'
  fi
done <<< "$FIXTURE_RUNNERS"
# The count is DERIVED from the loop. It used to read "all 3" as a literal while the
# loop was driven by $FIXTURE_RUNNERS plus a runner named outside it, so a fourth
# would have been reported as three — a count that does not come from what it
# counts, which is the thing this gate has spent six commits removing everywhere
# else. It has since gone 3 -> 4 -> 5 and the line moved each time, which is the
# only evidence that it is derived and not merely correct.
if [ "$FIX_RAN" -eq 0 ]; then
  fail "no fixture runners were invoked — \"all 0 gate fixtures pass\" is a claim about nothing"
elif [ "$FIX_OK" -eq 1 ]; then
  # Both the count AND the names come from the loop. Adding a runner used to
  # print "all 4 gate fixtures pass (codec chains, registry oracle, type values)" —
  # the number derived and the list beside it still naming three, which is the same
  # defect one field over and was visible only because the derived count moved.
  pass "all $FIX_RAN gate fixtures pass: $FIX_NAMES"
fi

# =====================================================================
section "[HARD] Every \"Type\" value in a JSON fence is a registered name"
# Queued gate 1, phase (c). `"Type"` is the discriminator on nearly every JSON
# page here and a fabricated one reads exactly like a real one; nothing checked
# these before. The check prints its own denominator and its per-oracle tally —
# a source that stops contributing shows up as a figure that moved, not as a
# quieter run. See maintenance/scripts/check-type-values.py for what it does NOT
# cover (misattribution: a real name in the wrong slot).
# Both caches are guarded HERE as well as in the checker. An earlier version
# guarded only $ASSETS and trusted the checker's exit code for the source cache;
# the checker returned 0 on a missing cache, the column-0 SKIP line was filtered
# out, and the block printed a bare `PASS` with no message over output that
# contained no PASS line. build-jar-cache.sh wipes before it rebuilds, so an
# interrupted rebuild produces exactly that state.
if [ ! -d "$SRC_CACHE" ]; then
  warn "skipped (no decompiled source cache at $SRC_CACHE — build-jar-cache.sh)"
elif [ ! -d "$ASSETS" ]; then
  warn "skipped (no asset cache)"
else
  OUT="$(python3 maintenance/scripts/check-type-values.py --src "$SRC_CACHE" --assets "$ASSETS")"
  RC=$?
  echo "$OUT" | grep -E '^  INFO'
  # A stale skiplist entry is a WARN, and it must go through `warn` so it counts
  # toward the figure invariant 1 reads. Echoed raw it was simultaneously a hard
  # failure with no stated cause and a warning that did not count as one.
  while IFS= read -r line; do
    [ -n "$line" ] && warn "${line#  WARN  }"
  done <<< "$(echo "$OUT" | grep -E '^  WARN' || true)"
  FINDINGS="$(echo "$OUT" | grep -E '^  (FAIL|SKIP)' || true)"
  if [ "$RC" -eq 0 ]; then
    pass "$(echo "$OUT" | sed -n 's/^  PASS  //p')"
  elif [ -n "$FINDINGS" ]; then
    # Name the actual cause. The header used to say "fabricated ... value(s)"
    # whatever the cause, so a stale-skiplist-only run rendered as a FAIL with
    # an empty body under a header naming the wrong problem.
    fail "check-type-values.py reported:"
    echo "$OUT" | grep -E '^  (FAIL|SKIP)|^        ' | sed 's/^  FAIL  /    /; s/^  SKIP  /    /; s/^        /    /'
  else
    fail "stale skiplist entr(y/ies) above — no fabricated values, but the exemption list no longer matches the corpus"
  fi
fi

# =====================================================================
section "[HARD] Every documented Default is the value the field holds"
# Queued gate 1, step 5. A `| Key | Type | Default |` table is the most falsifiable
# thing on a JSON page and nothing read the Default column: check-symbols.py skips
# JSON key paths, and the fields check confirms documented-key -> real for NAMES and
# never for values. So a default that changed in a new build read exactly like one
# that had not.
#
# It prints THREE denominators and they are not the same number: Default-column
# tables scanned, how many of those sit in a bound section, and how many rows of
# those are actually comparable. On build-26 that is 60 -> 34 -> 84 comparable rows
# of 161, and printing the narrowing is the point — the snippet gate's green line
# read as corpus coverage for a year while compiling 5 of 1091 blocks.
#
# The source cache is guarded here as well as in the checker, for the reason the
# block above records: a skip encoded as success plus an output filter that cannot
# see the skip renders as a bare `PASS` with no message.
if [ ! -d "$SRC_CACHE" ]; then
  warn "skipped (no decompiled source cache at $SRC_CACHE — build-jar-cache.sh)"
else
  OUT="$(python3 maintenance/scripts/check-defaults.py --src "$SRC_CACHE")"
  RC=$?
  echo "$OUT" | grep -E '^  INFO'
  while IFS= read -r line; do
    [ -n "$line" ] && warn "${line#  WARN  }"
  done <<< "$(echo "$OUT" | grep -E '^  WARN' || true)"
  if [ "$RC" -eq 0 ]; then
    pass "$(echo "$OUT" | sed -n 's/^  PASS  //p')"
  else
    fail "check-defaults.py reported:"
    echo "$OUT" | grep -E '^  (FAIL|SKIP)|^        ' \
      | sed 's/^  FAIL  /    /; s/^  SKIP  /    /; s/^        /    /'
  fi
fi

# =====================================================================
section "[HARD] Complete doc snippets compile against the jar"
# A ```java block starting with `package ` is a complete compilation unit and
# must compile (same-doc same-package blocks co-compile). Fragments are exempt.
# See maintenance/scripts/check-snippets.py for the contract and rationale.
if [ -f "$JAR" ] && command -v javac >/dev/null 2>&1; then
  OUT="$(python3 maintenance/scripts/check-snippets.py "$JAR")"
  RC=$?
  N="$(echo "$OUT" | sed -n 's/^CHECKED //p')"
  NB="$(echo "$OUT" | sed -n 's/^BLOCKS //p')"
  DC="$(echo "$OUT" | awk '/^DOCS/{print $2}')"
  DJ="$(echo "$OUT" | awk '/^DOCS/{print $3}')"
  FRAG=$(( ${NB:-0} - ${N:-0} ))
  if [ "$RC" -eq 0 ]; then
    # Report the denominator: this gate is opt-in (a fragment cannot compile), so
    # "all N compile" alone reads as corpus coverage when it is a small subset.
    pass "all $N complete snippet(s) compile — $N of ${NB:-?} java block(s), in $DC of $DJ doc(s) carrying java; $FRAG fragment(s) exempt by design"
  else
    fail "snippet compilation failed:"
    echo "$OUT" | grep -vE '^(CHECKED|BLOCKS|DOCS)' | sed 's/^/    /'
  fi
else
  warn "skipped (no jar or no javac)"
fi

# =====================================================================
section "[ADVISORY] llms.txt is current"
# docs/llms.txt is generated from page frontmatter (see generate-llms-txt.sh);
# regenerate + commit it whenever pages or descriptions change.
if [ -f docs/llms.txt ]; then
  if ./maintenance/scripts/generate-llms-txt.sh | cmp -s - docs/llms.txt; then
    pass "docs/llms.txt matches a fresh regeneration"
  else
    warn "docs/llms.txt is stale — regenerate: ./maintenance/scripts/generate-llms-txt.sh > docs/llms.txt"
  fi
else
  warn "docs/llms.txt missing — generate: ./maintenance/scripts/generate-llms-txt.sh > docs/llms.txt"
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
