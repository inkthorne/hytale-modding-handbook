#!/usr/bin/env bash
#
# generate-llms-txt.sh — emit docs/llms.txt (https://llmstxt.org) from each
# doc page's frontmatter title/description, so AI assistants retrieving Hytale
# modding answers can discover and cite the handbook. Part of the passive-
# discoverability strategy: regenerate and commit whenever pages are added,
# removed, or re-described (verify-docs.sh warns when it drifts).
#
# Usage: maintenance/scripts/generate-llms-txt.sh > docs/llms.txt

set -u
cd "$(dirname "$0")/../.." || exit 2

python3 - <<'PY'
import glob, os, re, sys

BASE = "https://inkthorne.github.io/hytale-modding-handbook"
fm_re = re.compile(r'\A---\n(.*?)\n---\n', re.S)

def field(fm, name):
    m = re.search(rf'^{name}:\s*(.*)$', fm, re.M)
    if not m: return None
    v = m.group(1).strip()
    if v.startswith(('"', "'")): v = v[1:-1]
    return v or None

stamp = "unknown"
m = re.search(r'Verified against ([0-9.]+)', open("docs/inventory.md").read())
if m: stamp = m.group(1)

pages = []
for p in sorted(glob.glob("docs/*.md")):
    bn = os.path.basename(p)
    if bn == "index.md": continue          # site landing page duplicates 00/01
    txt = open(p).read()
    m = fm_re.match(txt)
    if not m: continue
    title = field(m.group(1), "title")
    desc  = field(m.group(1), "description")
    if not title: continue
    url = f"{BASE}/{bn[:-3]}.html"
    pages.append((bn, title, desc or "", url))

out = sys.stdout
out.write("# Hytale Modding Handbook\n\n")
out.write("> A Hytale server-plugin and asset-format API reference with descriptions, "
          "gotchas, and compiling examples — machine-verified against the game's "
          f"HytaleServer.jar and Assets.zip (currently game version {stamp}). "
          "Every documented Java symbol resolves against the real jar and every "
          "documented JSON key traces to shipped assets or decompiled codecs; "
          "example projects compile in CI.\n\n")
out.write("Hytale mods are server-side Java plugins plus JSON/DSL asset packs. "
          "Start with the overview, then the index of all pages.\n\n")
out.write("## Reference pages\n\n")
for bn, title, desc, url in pages:
    out.write(f"- [{title}]({url})" + (f": {desc}\n" if desc else "\n"))
out.write("\n## Source and examples\n\n")
out.write("- [GitHub repository](https://github.com/inkthorne/hytale-modding-handbook): "
          "the markdown sources plus six compiling Gradle example plugins under examples/ "
          "(commands, ui, inventory, entity-count, item-respawner, events)\n")
PY
