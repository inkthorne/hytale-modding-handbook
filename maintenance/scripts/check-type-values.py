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
#
# Two things this cannot do, both measured as absent from build-26's corpus (2036
# fences, 4072 line-initial markers, exactly 2x; no four-backtick fences; no fence
# whose closing indent differs from its opening): the indent group is captured and
# unused, so a closer need not match its opener; and a four-backtick fence would be
# sliced at its first three. Both fail by UNDER-COUNTING — a mis-paired json fence
# stops being scanned rather than being scanned wrongly — which is why the
# `N json fence(s) of M` denominator this gate prints is the thing that would catch
# it, and why the exposure is acceptable rather than a gap.
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
    ap.add_argument('--skiplist', default=str(HERE / 'type-value-skiplist.txt'),
                    help='audited exemptions; overridable so the fixture can drive '
                         'the stale-entry and mixed-source paths on its own corpus')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    docs, src, assets = (pathlib.Path(a.docs), pathlib.Path(a.src),
                         pathlib.Path(a.assets))
    # Exit 2, NOT 0. Returning 0 here made verify-docs.sh print a bare `PASS` with
    # no message over output that contained no PASS line: the shell filtered the
    # column-0 SKIP away, saw RC=0, and reported a clean run of a check that had
    # examined nothing. That is the silent zero this gate family exists to
    # prevent, in the gate whose docstring explains it. `build-jar-cache.sh`
    # wipes before it rebuilds, so an interrupted rebuild leaves exactly this
    # state — the branch is not hypothetical.
    for label, p, how in (('decompiled source', src, 'maintenance/scripts/build-jar-cache.sh'),
                          ('asset cache', assets, 'the unzip command in CLAUDE.md')):
        if not p.exists():
            print(f"  SKIP  {label} not found at {p} — build it with {how}")
            return 2

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

    skip_path = pathlib.Path(a.skiplist)
    if not skip_path.exists():
        # Exit 2, like a missing cache. A missing exemption list is a missing INPUT,
        # not a crash and certainly not a pass: without it every waived value reads
        # as a fabrication. Left as a bare FileNotFoundError it was the one input
        # whose absence produced a traceback rather than a status the caller can act on.
        print(f"  SKIP  skiplist not found at {skip_path}")
        return 2
    skip = load_skiplist(skip_path)
    values, page_local, (n_fence, n_json, n_java) = docs_values(docs, src)

    # Resolution is per (value, page): the page's own java fence and the skiplist are
    # both page-scoped, so a value legitimate on one page is not thereby legitimate
    # on another. The tally is derived from THAT SAME PASS rather than re-derived,
    # which is not tidiness — an earlier version decided findings per (value, page)
    # and then recomputed the tally with `all(... for page in pages)`, and the two
    # could disagree whenever different pages resolved a value by different
    # page-scoped sources. It printed `unresolved 1` and `PASS` on the same run.
    # A reported denominator that can contradict the verdict beside it is the exact
    # defect invariant 6 exists to prevent, so there is now one pass and one source
    # of truth.
    PRECEDENCE = ('registry', 'assets', 'page-local', 'skiplist')
    findings, used_skips = [], set()
    sources = {}                       # value -> set of sources that resolved it
    for value, pages in sorted(values.items()):
        used = set()
        for page in sorted(pages):
            if value in registered:
                used.add('registry')
            elif value in asset_types:
                used.add('assets')
            elif value in page_local.get(page, ()):
                used.add('page-local')
            elif page in skip.get(value, {}):
                used.add('skiplist')
                used_skips.add((value, page))
            else:
                used.add('unresolved')
                findings.append((value, page, pages[page]))
        sources[value] = used

    by_source = collections.Counter()
    for value, used in sources.items():
        if 'unresolved' in used:
            by_source['unresolved'] += 1
        else:
            by_source[next(k for k in PRECEDENCE if k in used)] += 1

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
    # The five buckets count DISTINCT VALUES by first source, so they sum to the
    # distinct count. That makes the skiplist bucket a FLOOR on how much is being
    # waived, not the answer: a value waived on one page and legitimate on another
    # is claimed by the higher-priority bucket and never counted here. `used_skips`
    # is the honest figure for "how much is being waived", and it is what staleness
    # detection reads — so the two are reported side by side rather than one of
    # them silently standing in for the other.
    print(f"  INFO  resolved by: registry {by_source['registry']}, "
          f"shipped assets {by_source['assets']}, page's own java fence "
          f"{by_source['page-local']}, audited skiplist {by_source['skiplist']}, "
          f"unresolved {by_source['unresolved']} "
          f"(distinct values by first source; {len(used_skips)} live "
          f"(value, page) exemption(s) in total)")
    if tally != len(values):
        print(f"  FAIL  the by-source tally is {tally} but there are {len(values)} "
              f"distinct value(s) — a value is being counted twice or not at all")
        return 1
    if by_source['unresolved'] != len({v for v, _, _ in findings}):
        print(f"  FAIL  the tally says {by_source['unresolved']} unresolved value(s) "
              f"but {len({v for v, _, _ in findings})} are reported below — the "
              f"denominator and the verdict disagree")
        return 1
    if a.verbose:
        print(f"  INFO  oracle sizes: {len(registered)} registered name(s), "
              f"{len(asset_types)} asset \"Type\" value(s) over {n_assets} json file(s), "
              f"{n_java} java fence(s) mined")

    rc = 0
    if missed:
        print(f"  FAIL  known-positive probe passed the oracle: {', '.join(missed)}")
        print( "        Either the union of four oracles now accepts a value "
               "registered nowhere — in which case a clean run below proves "
               "nothing — OR the value became real in a new build, in which case "
               "replace the canary. Check which before touching the oracles: "
               "`Furniture` is already live in the asset tree as an \"Id\" and a "
               "\"Tag\", one key away from becoming a \"Type\".")
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
# names corpus-wide. That is §3's lesson arriving from a third direction.
#
# The full measurement, the counterexample, and the reason the "safe subset"
# cannot be carved out either (the instrument that would select it is the broken
# one) are in maintenance/registry-oracle-notes.md §12 — in the notes rather than
# only in this comment, because these are the numbers that stop the next person
# concluding "156 bind uniquely, ship the scoped gate".

if __name__ == '__main__':
    sys.exit(main())
