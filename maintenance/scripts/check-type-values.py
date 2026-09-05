#!/usr/bin/env python3
"""
Phase (c) of queued gate 1: every `"Type"` value in a docs JSON fence must be a
name something actually registers.

`"Type"` is the discriminator on nearly every JSON page in this handbook, and a
fabricated one reads exactly like a real one — a `"Type": "Wall"` shipped for at
least a build. Nothing checked these before: `check-symbols.py` deliberately skips
JSON key paths, and the fields check runs documented-key -> real, never value -> real.

WHAT THIS CHECKS, PRECISELY. That a documented value is a REGISTERED NAME
SOMEWHERE. It does NOT check that the name is legal in the slot it appears in.
That distinction is not pedantry: 15 of the 176 core-component names are
registered in more than one category (`Timer` is legal in `BodyMotion`,
`HeadMotion` AND `Sensor`), and §4 records `CameraShake`, `Portal`, `Teleporter`,
`ShowEventTitle` and four more as names registered on two different codecs. So
this gate catches INVENTION and is blind to MISATTRIBUTION. Scoping it needs a
binding from a JSON key to the codec that decodes it, and the obvious version of
that binding was measured and is unsound — see the note at the foot of this file.

FOUR ORACLE SOURCES, and the gate reports how many values each one carried,
because a source that silently stops contributing is how this check would rot:

  1. registry_miner over the decompiled jar — all three registration forms.
  2. `"Type"` values observed in the shipped asset tree. Covers vocabularies
     whose registration mechanism the miner does not model at all (drop-table
     types, recipe types); an id in this set is real by demonstration.
  3. Names the PAGE ITSELF registers, mined out of its own ```java fences with
     the same miner. Every walkthrough that says "register your own type" then
     shows the JSON lands here — `Melt`, `Greet`, `My_Type`, `Orbit`,
     `MyMod_FlockAttackToken`. This is not a convenience: those pages are
     self-registering, so a jar-only oracle has a structural false-positive
     floor, and a skip list for them would be a claim about a fence with the
     fence left unread.
  4. maintenance/scripts/type-value-skiplist.txt, audited, currently one entry.

Usage: python3 maintenance/scripts/check-type-values.py [--docs DIR] [--src DIR]
                                                        [--assets DIR] [-v]
"""
from __future__ import annotations
import argparse, collections, os, pathlib, re, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import registry_miner as rm

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

# Fences may be INDENTED — a ```json nested in a numbered list is still a fence,
# and an `^```' anchor silently skipped interactions.md's `My_Type` example (and,
# by luck, the java fence that registers it, so the two errors cancelled).
FENCE = re.compile(r'^([ \t]*)```(\w*)[^\n]*\n(.*?)^[ \t]*```', re.M | re.S)
TYPE = re.compile(r'"Type"\s*:\s*"([^"]*)"')

# A known-positive probe. The oracle is a union of four large sets, so "nothing was
# flagged" has two causes — a clean corpus, or an oracle that accepts everything —
# and only one is good news. Two of these are real fabrications this repo actually
# shipped (items.md's `Furniture`, effects-stats.md's `FullEnergy_Glow`); the third
# is synthetic. If the gate stops flagging any of them it is broken, not clean.
#
# `Wall` is deliberately NOT here, and the reason is the honest limit of this gate.
# CLAUDE.md cites a fabricated `"Type": "Wall"` as the defect that motivated the
# whole oracle — but `Wall` is a registered name AND a shipped-asset `"Type"`
# value, so its fabrication was MISATTRIBUTION, a real name in the wrong slot.
# This gate would have passed it. Do not read a green run as covering that class.
CANARIES = ('Furniture', 'FullEnergy_Glow', '__NotARegisteredType__')


def load_skiplist(path: pathlib.Path):
    out = collections.defaultdict(dict)
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            sys.exit(f"FAIL  malformed skiplist line (need value, page, justification): {line!r}")
        value, page, why = parts
        out[value][page] = why
    return out


def docs_values(docs: pathlib.Path, src: pathlib.Path):
    """(value -> {page: count}, page -> names the page registers, fence counts)."""
    values = collections.defaultdict(collections.Counter)
    page_local = collections.defaultdict(set)
    n_fence = n_json = n_java = 0
    for d in sorted(docs.glob('*.md')):
        java_blocks = []
        for m in FENCE.finditer(d.read_text()):
            lang, body = m.group(2), m.group(3)
            n_fence += 1
            if lang == 'json':
                n_json += 1
                for v in TYPE.findall(body):
                    values[v][d.name] += 1
            elif lang == 'java':
                n_java += 1
                java_blocks.append(body)
        if java_blocks:
            # The miner wants a file. Write the page's java to a scratch file
            # OUTSIDE the repo — a stray .java under docs/ would be picked up by
            # the next run as if it were corpus.
            with tempfile.NamedTemporaryFile('w', suffix='.java', delete=False) as fh:
                fh.write('\n'.join(java_blocks))
                tmp = pathlib.Path(fh.name)
            try:
                for _, _, site in rm.mine_file(tmp, src):
                    if site.name:
                        page_local[d.name].add(site.name)
            finally:
                tmp.unlink()
    return values, page_local, (n_fence, n_json, n_java)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', default=str(REPO / 'docs'))
    ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
    ap.add_argument('--assets', default=os.path.expanduser('~/.cache/hytale-assets'))
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    docs, src, assets = (pathlib.Path(a.docs), pathlib.Path(a.src),
                         pathlib.Path(a.assets))
    for label, p, how in (('decompiled source', src, 'maintenance/scripts/build-jar-cache.sh'),
                          ('asset cache', assets, 'the unzip command in CLAUDE.md')):
        if not p.exists():
            print(f"SKIP  {label} not found at {p} — build it with {how}")
            return 0

    registered = set()
    for r in rm.mine(src).values():
        registered.update(r.names)

    asset_types = set()
    n_assets = 0
    for p in assets.rglob('*.json'):
        n_assets += 1
        asset_types.update(TYPE.findall(p.read_text(errors='replace')))

    # A zero here would make the gate pass everything for the wrong reason.
    if not registered or not asset_types or not n_assets:
        print(f"FAIL  an oracle source is empty: registry={len(registered)} "
              f"assets={len(asset_types)} from {n_assets} file(s)")
        return 1

    skip = load_skiplist(HERE / 'type-value-skiplist.txt')
    values, page_local, (n_fence, n_json, n_java) = docs_values(docs, src)

    # Resolution is per (value, page): the page's own java fence and the skiplist are
    # both page-scoped, so a value legitimate on one page is not thereby legitimate
    # on another. The by-source tally counts DISTINCT VALUES by the first source
    # that carries them, so the four figures sum to the distinct count and a source
    # that stops contributing is visible as a number that moved.
    by_source = collections.Counter()
    findings, used_skips = [], set()
    for value, pages in sorted(values.items()):
        for page in sorted(pages):
            if value in registered or value in asset_types:
                continue
            if value in page_local.get(page, ()):
                continue
            if page in skip.get(value, {}):
                used_skips.add((value, page))
                continue
            findings.append((value, page, pages[page]))
        if value in registered:
            by_source['registry'] += 1
        elif value in asset_types:
            by_source['assets'] += 1
        elif all(value in page_local.get(pg, ()) for pg in pages):
            by_source['page-local'] += 1
        elif all(pg in skip.get(value, {}) for pg in pages):
            by_source['skiplist'] += 1
        else:
            by_source['unresolved'] += 1

    missed = [c for c in CANARIES
              if c in registered or c in asset_types
              or any(c in s for s in page_local.values())]

    stale = [(v, pg) for v, pgs in skip.items() for pg in pgs
             if (v, pg) not in used_skips]

    total = sum(sum(p.values()) for p in values.values())
    print(f"  INFO  {n_json} json fence(s) of {n_fence} in {len(list(docs.glob('*.md')))} "
          f"page(s); {total} \"Type\" occurrence(s), {len(values)} distinct value(s)")
    tally = (by_source['registry'] + by_source['assets'] + by_source['page-local']
             + by_source['skiplist'] + by_source['unresolved'])
    print(f"  INFO  resolved by: registry {by_source['registry']}, "
          f"shipped assets {by_source['assets']}, page's own java fence "
          f"{by_source['page-local']}, audited skiplist {by_source['skiplist']}, "
          f"unresolved {by_source['unresolved']}")
    if tally != len(values):
        print(f"  FAIL  the by-source tally is {tally} but there are {len(values)} "
              f"distinct value(s) — a value is being counted twice or not at all")
        return 1
    if a.verbose:
        print(f"  INFO  oracle sizes: {len(registered)} registered name(s), "
              f"{len(asset_types)} asset \"Type\" value(s) over {n_assets} json file(s), "
              f"{n_java} java fence(s) mined")

    rc = 0
    if missed:
        print(f"  FAIL  known-positive probe passed the oracle: {', '.join(missed)}")
        print( "        The union of four oracles now accepts a value registered "
               "nowhere, so a clean run below proves nothing.")
        rc = 1
    for value, page in sorted(stale):
        print(f"  WARN  stale skiplist entry: {value!r} on {page} — it resolves now, "
              f"or the page no longer uses it. Remove the line.")
        rc = 1
    for value, page, n in findings:
        print(f"  FAIL  {page}: \"Type\": \"{value}\" (x{n}) is registered nowhere "
              f"and appears in no shipped asset")
    if findings:
        print( "        Before adding a skiplist entry, suspect the oracles: a whole "
               "registration form was missing the first time this ran.")
        rc = 1
    if rc == 0:
        print(f"  PASS  all {len(values)} distinct \"Type\" value(s) trace to a "
              f"registration, a shipped asset, or an audited exemption")
    return rc


# WHY THIS GATE IS NOT SCOPED, and what it would take.
#
# The ruling for phase (c) was a SCOPED check, hard-failing only on closed
# registries. Scoping needs a binding from the enclosing JSON key to the codec
# that decodes its value; the obvious binding is `new KeyedCodec("<Key>", X.CODEC)`
# mined from the corpus, keeping only keys that bind to exactly one codec.
#
# Measured before writing it: 165 JSON keys bind to at least one type-discriminated
# codec and 156 bind to exactly one — but "exactly one" is an artefact of the
# match window, not a fact about the corpus. `Interactions` came back bound
# uniquely to `ChoiceInteraction.CODEC`, whose whole vocabulary is {GiveItem,
# StartObjective}; effects-stats.md's `Interactions` is a `RootInteraction`, so
# that binding would have failed `ChangeStat`, `ApplyEffect` and
# `ClearEntityEffect` on a page that is correct. And the NPC slots that most need
# scoping — `Sensor`, `BodyMotion`, `Instructions`, `MotionControllerList` —
# bind to nothing at all, because form 3 has no KeyedCodec anywhere near it.
#
# A gate that hard-fails correct pages is worse than no gate, and shipping it
# behind a warning is invariant 1 wallpaper. So the sound half ships and the
# scoped half waits for a real key->codec binding: parse the ENCLOSING codec's
# chain and take the key's declared codec argument, rather than matching key
# names corpus-wide. That is §3's lesson arriving from a third direction, and
# it is recorded as arrears in registry-oracle-notes.md rather than half-built.

if __name__ == '__main__':
    sys.exit(main())
