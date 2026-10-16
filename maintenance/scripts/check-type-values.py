#!/usr/bin/env python3
"""
Phase (c) of queued gate 1: every discriminator value in a docs JSON fence must be a
name something actually registers UNDER THAT KEY.

THE KEY MATTERS (2026-10-15). A registry's names are written under its own discriminator key,
and it is not always "Type": `ItemAbility.CODEC` is keyed "Slot", `Condition.CODEC` "Id",
`TagPattern.CODEC` "Op", `Schema.CODEC` "type", `UIEditor.CODEC` "component" (registry_miner
reads each from the declaration). Until then this gate unioned every registry's names into one
oracle and checked only "Type", so a fabricated `"Type": "Core"` passed because ItemAbility
registers `Core` under "Slot". Now each key K that some registry uses is checked on its own:
a value under K resolves only against names of registries keyed K, shipped values under K,
the page's own java fence (when it registers into a K-keyed registry) and the skiplist. A name
registered under another key never resolves a value under K.

TWO KINDS OF KEY, told apart by a measurement made before any docs value is looked at: the
shipped assets. share(K) = (distinct shipped values under K that are names of K-keyed
registries) / (distinct shipped values under K). A key whose share is at least SHARE_FLOOR is
DISCRIMINATOR-DOMINATED ("checked"): shipped values under it are mostly registered names, so
they are a legitimate extra oracle and an unresolved value FAILS. A key below it (or with no
shipped value at all) is MIXED: it is also an ordinary field somewhere else ("Id" holds
essentially every asset id; "Slot" holds an NPC blackboard slot 697 times beside 24 files of
ItemAbility), so an unregistered value under it may be a perfectly good ordinary value. Values
under a mixed key that ARE registered names are CONFIRMED; the rest are UNCHECKED, counted and
printed, and never passed. That is a judgment about false positives: flagging the ordinary
ids of `"Id": "Workbench"` would breed skiplist entries justified by this checker's own
output. 0.7.2 measures Type 0.86, Op 1.00, Slot 0.07, Id 0.04, type and component no shipped
value; any floor between 0.08 and 0.85 classifies them identically.

KNOWN BLIND SPOT, unchanged: key matching is POSITION-BLIND, like the "Type" check (notes §12).
The keyed oracle catches a value filed under the wrong key, not a value in the wrong slot.

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

  1. registry_miner over the decompiled jar — all three registration forms, in BOTH
     spellings: `Receiver.CODEC.register(…)` and the unqualified in-class
     `CODEC.register(…)` / `getCodecRegistry(PAGE_CODEC)` (69 sites in 20 classes at
     0.7.2), the latter bound to the class that declares the field by lexical scope
     (registry_miner._Lexical; registry-oracle-notes.md §15). Until 2026-10-15 only the
     qualified spelling was mined, so this oracle could only under-resolve. This oracle
     is UNSCOPED, and the unqualified registries widened it with names that are common
     words — UIEditor's `Text`/`Number`/`Icon`, Schema's `string`/`number`/`object`, and
     `Single`/`Random`/`Switch`/`Weighted` — so a docs `"Type": "Number"` now resolves
     here whatever slot it is in. None of the UIEditor or Schema names is a docs value today (measured
     2026-10-15), and `-v` lists the docs values that ONLY an unqualified registration
     supplies, which is the exposure this change added.
  2. Values observed under the SAME KEY in the shipped asset tree (for a checked key only).
     Covers vocabularies whose registration mechanism the miner does not model at all
     (drop-table types, recipe types); an id in this set is real by demonstration.
  3. Names the PAGE ITSELF registers into a registry of that key, mined out of its own
     ```java fences with the same miner. Every walkthrough that says "register your own type" then
     shows the JSON lands here — `Melt`, `Greet`, `My_Type`, `Orbit`,
     `MyMod_FlockAttackToken`. This is not a convenience: those pages are
     self-registering, so a jar-only oracle has a structural false-positive
     floor, and a skip list for them would be a claim about a fence with the
     fence left unread.
  4. maintenance/scripts/type-value-skiplist.txt, audited, currently empty (its one entry, IntervalCondition,
     resolves through shipped assets as of 0.7.2).

Usage: python3 maintenance/scripts/check-type-values.py [--docs DIR] [--src DIR]
                                                        [--assets DIR] [-v]
       -v also lists, per key, the docs values it confirmed, left unchecked, or resolved only
       through shipped values, and the docs values that only an unqualified registration
       supplies.
"""
from __future__ import annotations
import argparse, collections, os, pathlib, re, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import registry_miner as rm
import doc_fences

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

# Fences come from doc_fences.py, the one reader every gate shares. They may be INDENTED
# (a ```json nested in a numbered list is a fence; an `^```' anchor silently skipped
# interactions.md's `My_Type` example and, by luck, the java fence that registers it, so
# the two errors cancelled) and they may sit inside a BLOCKQUOTE (four do, and this gate
# did not see them until 2026-10-15). The reader requires a closer with the opener's prefix
# shape and the census in verify-docs.sh fails on any marker that belongs to no fence, so
# the under-counting this file used to document as "acceptable because the denominator
# would show it" is now caught by something that does not depend on someone reading a
# number. The `N json fence(s) of M` denominator this gate prints is still the figure
# verify-docs.sh compares with the census.
SHARE_FLOOR = 0.5      # pre-registered; see the docstring. Any floor in (0.07, 0.86) gives the same answer at 0.7.2.
PRIMARY = 'Type'       # the key every JSON page leans on; it must be checked or the gate has collapsed


def key_pattern(keys):
    r"""`"K"\s*:\s*"value"` for any K in `keys`: a whitespace CLASS, not a space (notes §12: the
    tab dialect under Server/HytaleGenerator is 112 values a space-only pattern loses)."""
    return re.compile(r'"(' + '|'.join(re.escape(k) for k in sorted(keys, key=lambda k: (-len(k), k)))
                      + r')"\s*:\s*"([^"]*)"')

# A known-positive probe. The oracle is a union of large sets, so "nothing was
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


def _tail2(key: str) -> str:
    return '.'.join(key.rsplit('.', 2)[-2:])


class RegistryIndex:
    """The mined registries seen by key: names per discriminator key, plus the lookups a page's
    own `Receiver.CODEC.register(...)` needs to learn which key it registers under."""
    def __init__(self, mined, src):
        self.src = src
        self.mined = mined
        self.defaults = rm.constructor_defaults(src)
        self.names = collections.defaultdict(set)         # key -> registered names
        self.count = collections.Counter()                 # key -> registries
        self.keyless = []                                  # MapKeyMapCodec registries (no discriminator)
        self.unknown = []                                  # registries whose key could not be read
        self.by_tail = collections.defaultdict(set)        # 'Foo.CODEC' -> {(key, how)}
        for k, r in mined.items():
            if r.disc_how == 'map-key':
                self.keyless.append(k)
            elif r.discriminator is None:
                self.unknown.append(k)
            else:
                self.names[r.discriminator].update(r.names)
                self.count[r.discriminator] += 1
            self.by_tail[_tail2(k)].add((r.discriminator, r.disc_how))

    def page_key(self, declaring, fld, tmp):
        """(key | None, how) for a registration a docs java fence makes. The page's own
        declaration wins (Java would bind its class first); then a jar registry of the same
        `Class.FIELD` tail, if its key is unambiguous; form 3 sits under BuilderFactory's tag."""
        if fld == rm.CORE_COMPONENT_FIELD:
            return self.defaults['factory'], 'factory'
        key, how, _ = rm.declared_key(declaring, fld, [tmp], self.src)
        if how not in ('unknown',):
            return key, how
        cands = {c for c in self.by_tail.get(_tail2(f'{declaring}.{fld}'), ()) if c[1] not in ('unknown', 'unread')}
        if len(cands) == 1:
            return next(iter(cands))
        return None, 'unknown'


def scan_assets(assets: pathlib.Path, pat):
    """key -> set of shipped values, and the file count."""
    ship = collections.defaultdict(set)
    n = 0
    for p in assets.rglob('*.json'):
        n += 1
        for k, v in pat.findall(p.read_text(errors='replace')):
            ship[k].add(v)
    return ship, n


def docs_values(docs: pathlib.Path, src: pathlib.Path, pat, index: RegistryIndex):
    """(key -> value -> {page: count}, page -> key -> names the page registers,
    fence counts, page-local sites whose key could not be read)."""
    values = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    page_local = collections.defaultdict(lambda: collections.defaultdict(set))
    n_fence = n_json = n_java = 0
    unkeyed = []
    for d in sorted(docs.glob('*.md')):
        java_blocks = []
        for fence in doc_fences.fences(d.read_text()):
            lang, body = fence.lang, fence.body
            n_fence += 1
            if lang == 'json':
                n_json += 1
                for k, v in pat.findall(body):
                    values[k][v][d.name] += 1
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
                for declaring, fld, site in rm.mine_file(tmp, src):
                    if not site.name:
                        continue
                    key, how = index.page_key(declaring, fld, tmp)
                    if key is None:
                        unkeyed.append((d.name, site.name, how))
                    else:
                        page_local[d.name][key].add(site.name)
            finally:
                tmp.unlink()
    return values, page_local, (n_fence, n_json, n_java), unkeyed


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
    # The docs corpus is guarded HERE, beside the oracles, and that placement is the
    # point: it was the only input whose validity was inferred from where this file
    # sits (REPO = HERE.parents[1]) rather than checked.
    for label, p, how in (('docs corpus', docs, 'check the --docs path'),
                          ('decompiled source', src, 'build it with maintenance/scripts/build-jar-cache.sh'),
                          ('asset cache', assets, 'build it with the unzip command in CLAUDE.md')):
        if not p.exists():
            print(f"  SKIP  {label} not found at {p} — {how}")
            return 2

    mined = rm.mine(src)
    index = RegistryIndex(mined, src)
    registered_any = set()                 # the union, kept ONLY for the canary probe
    for r in mined.values():
        registered_any.update(r.names)
    # Names supplied ONLY by an unqualified registration: the part of this oracle that
    # did not exist before the miner learned that spelling (reported under -v).
    qualified_names = {s.name for r in mined.values() for s in r.sites
                       if s.name and s.spelling == 'qualified'}
    unqualified_only = collections.defaultdict(set)
    for r in mined.values():
        for s in r.sites:
            if s.name and s.spelling == 'unqualified' and s.name not in qualified_names:
                unqualified_only[s.name].add(r.key)

    keys = sorted(index.names, key=lambda k: (k != PRIMARY, k))
    pat = key_pattern(keys) if keys else None
    if not keys or PRIMARY not in index.names:
        print(f"FAIL  no registry is keyed {PRIMARY!r}: the miner read {len(mined)} registr(y/ies), "
              f"{len(index.unknown)} with an unreadable key. Either the key reader collapsed or the "
              f"source cache is not the codec library — a clean run over that proves nothing.")
        return 1
    ship, n_assets = scan_assets(assets, pat)

    # A zero here would make the gate pass everything for the wrong reason.
    if not index.names[PRIMARY] or not ship[PRIMARY] or not n_assets:
        print(f"FAIL  an oracle source is empty: registry={len(index.names[PRIMARY])} "
              f"assets={len(ship[PRIMARY])} from {n_assets} file(s)")
        return 1

    # The classification, made from the registries and the shipped assets alone.
    mode, share = {}, {}
    for k in keys:
        both = ship[k] & index.names[k]
        share[k] = (len(both) / len(ship[k])) if ship[k] else None
        mode[k] = 'checked' if share[k] is not None and share[k] >= SHARE_FLOOR else 'mixed'
    if mode[PRIMARY] != 'checked':
        print(f"FAIL  {PRIMARY!r} classifies as a MIXED key (share {share[PRIMARY]}): the shipped "
              f"values under it are mostly not registered names, so either the registry oracle or "
              f"the asset oracle has collapsed — and every value under it would read UNCHECKED.")
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
    values, page_local, (n_fence, n_json, n_java), unkeyed = docs_values(docs, src, pat, index)

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
    sources = {k: {} for k in keys}                # key -> value -> set of sources that resolved it
    for k in keys:
        for value, pages in sorted(values.get(k, {}).items()):
            used = set()
            for page in sorted(pages):
                if value in index.names[k]:
                    used.add('registry')
                elif mode[k] == 'checked' and value in ship[k]:
                    used.add('assets')
                elif value in page_local.get(page, {}).get(k, ()):
                    used.add('page-local')
                elif mode[k] == 'checked' and k == PRIMARY and page in skip.get(value, {}):
                    used.add('skiplist')
                    used_skips.add((value, page))
                elif mode[k] == 'checked':
                    used.add('unresolved')
                    findings.append((k, value, page, pages[page]))
                else:
                    used.add('unchecked')
            sources[k][value] = used

    # ZERO-FLOOR ON THE SUBJECT, not just on the oracles. Every input this gate
    # READS is guarded above; the thing it is ABOUT was not, and an absent or empty
    # --docs produced `0 json fence(s) of 0 in 0 page(s)` followed by PASS and exit
    # 0. That is the third appearance of one shape in this gate — a bare PASS over
    # an absent oracle, a PASS beside `unresolved 1`, a PASS over an absent corpus —
    # and the asymmetry is why it survived a round spent on exactly this: an absent
    # ORACLE makes everything fail, which is loud and gets fixed; an absent SUBJECT
    # makes everything pass, which is silent. The fixture was built from the
    # category "a missing-cache run" and every remedy followed the oracles;
    # "a missing-corpus run" is its mirror image and nobody wrote it down.
    # Precedent for failing rather than passing on a zero denominator: the README
    # gate's `RM_PAGES -eq 0`.
    n_pages = len(list(docs.glob('*.md')))
    primary = values.get(PRIMARY, {})
    if n_pages == 0 or n_json == 0 or not primary:
        print(f"  FAIL  scanned nothing: {n_pages} page(s), {n_json} json fence(s), "
              f"{len(primary)} distinct value(s) under {docs}")
        print( "        A clean run over an empty corpus is the sentence invariant 6 "
               "exists to make impossible.")
        return 1

    def tally(k):
        c = collections.Counter()
        for value, used in sources[k].items():
            if 'unresolved' in used:
                c['unresolved'] += 1
            elif 'unchecked' in used:
                c['unchecked'] += 1
            else:
                c[next(x for x in PRECEDENCE if x in used)] += 1
        return c

    by_source = tally(PRIMARY)
    stale = [(v, pg) for v, pgs in skip.items() for pg in pgs
             if (v, pg) not in used_skips]
    missed = [c for c in CANARIES
              if c in registered_any or c in ship[PRIMARY]
              or any(c in names.get(PRIMARY, ()) for names in page_local.values())]

    total = sum(sum(p.values()) for p in primary.values())
    print(f"  INFO  {n_json} json fence(s) of {n_fence} in {n_pages} "
          f"page(s); {total} \"Type\" occurrence(s), {len(primary)} distinct value(s)")
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
    sums = sum(by_source[x] for x in PRECEDENCE) + by_source['unresolved']
    if sums != len(primary):
        print(f"  FAIL  the by-source tally is {sums} but there are {len(primary)} "
              f"distinct value(s) — a value is being counted twice or not at all")
        return 1
    if by_source['unresolved'] != len({v for k, v, _, _ in findings if k == PRIMARY}):
        print(f"  FAIL  the tally says {by_source['unresolved']} unresolved value(s) "
              f"but {len({v for k, v, _, _ in findings if k == PRIMARY})} are reported below — the "
              f"denominator and the verdict disagree")
        return 1

    # One line per discriminator key: its denominator, the size of its shipped-value oracle, and
    # how its values were resolved. Every key is accounted for to the distinct value.
    n_unchecked_vals = n_unchecked_occ = 0
    per_key = {}
    for k in keys:
        c = tally(k)
        vals = values.get(k, {})
        occ = sum(sum(p.values()) for p in vals.values())
        ship_only = sorted(v for v, u in sources[k].items()
                           if 'assets' in u and v not in index.names[k]
                           and not any(v in names.get(k, ()) for names in page_local.values()))
        per_key[k] = (c, vals, ship_only)
        sh = '-' if share[k] is None else f"{share[k]:.2f}"
        head_ = (f"  INFO  key {k!r}: {mode[k]} (share {sh}); {index.count[k]} registr(y/ies) naming "
                 f"{len(index.names[k])}; shipped oracle {len(ship[k])} value(s); docs {occ} occurrence(s), "
                 f"{len(vals)} distinct")
        if mode[k] == 'checked':
            if k == PRIMARY:
                print(head_ + f"; resolved only through shipped values {len(ship_only)}")
            else:
                print(head_ + f"; registry {c['registry']}, shipped only {len(ship_only)}, "
                      f"page's own java fence {c['page-local']}, unresolved {c['unresolved']}")
        else:
            unchecked_occ = sum(sum(vals[v].values()) for v, u in sources[k].items() if 'unchecked' in u)
            n_unchecked_vals += c['unchecked']
            n_unchecked_occ += unchecked_occ
            print(head_ + f"; CONFIRMED by a registry keyed {k!r} {c['registry'] + c['page-local']}, "
                  f"UNCHECKED {c['unchecked']} ({unchecked_occ} occurrence(s)) — not a pass")
    print(f"  INFO  registries: {sum(index.count.values())} keyed by {len(keys)} key(s) "
          f"({', '.join(f'{k} {index.count[k]}' for k in keys)}); {len(index.keyless)} without a "
          f"discriminator (MapKeyMapCodec, names are object keys); {len(index.unknown)} whose key could "
          f"not be read; {len(unkeyed)} page-local registration(s) whose registry key could not be read")
    if a.verbose:
        print(f"  INFO  oracle sizes: {len(registered_any)} registered name(s) over all keys, "
              f"{sum(len(v) for v in ship.values())} shipped (key, value) pair(s) over {n_assets} json file(s), "
              f"{n_java} java fence(s) mined")
        for k in keys:
            c, vals, ship_only = per_key[k]
            if ship_only:
                print(f"  INFO  {k!r}: resolved ONLY through shipped values: {', '.join(ship_only)}")
            if mode[k] == 'mixed':
                un = sorted(v for v, u in sources[k].items() if 'unchecked' in u)
                cf = sorted(v for v, u in sources[k].items() if 'unchecked' not in u)
                print(f"  INFO  {k!r}: confirmed: {', '.join(cf) or '-'}")
                print(f"  INFO  {k!r}: UNCHECKED: {', '.join(un) or '-'}")
        shifted = sorted(v for v in primary if v in unqualified_only)
        print(f"  INFO  docs value(s) that ONLY an unqualified registration supplies to the "
              f"registry oracle: {len(shifted)} of {len(primary)}")
        for v in shifted:
            regs_ = sorted(k.replace('com.hypixel.hytale.', '') for k in unqualified_only[v])
            print(f"          {v}  <- {', '.join(regs_)}")
        for pg, nm, how in unkeyed:
            print(f"  INFO  page-local registration with no readable key: {pg}: {nm} ({how})")

    rc = 0
    if missed:
        print(f"  FAIL  known-positive probe passed the oracle: {', '.join(missed)}")
        print( "        Either the union of the oracles now accepts a value "
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
    for k, value, page, n in findings:
        print(f"  FAIL  {page}: \"{k}\": \"{value}\" (x{n}) is registered nowhere "
              f"under {k!r} and appears in no shipped asset under it"
              if k == PRIMARY else
              f"  FAIL  {page}: \"{k}\": \"{value}\" (x{n}) is not a name any registry keyed {k!r} "
              f"registers and appears in no shipped asset under {k!r}")
    if findings:
        print( "        Before adding a skiplist entry, suspect the oracles: a whole "
               "registration form was missing the first time this ran.")
        rc = 1
    if rc == 0:
        checked = [k for k in keys if mode[k] == 'checked']
        mixed = [k for k in keys if mode[k] == 'mixed']
        n_checked = sum(len(values.get(k, {})) for k in checked)
        msg = (f"all {n_checked} distinct value(s) under {len(checked)} checked key(s) "
               f"({', '.join(checked)}) trace to a registration, a shipped asset, or an audited exemption")
        if mixed:
            msg += (f"; {n_unchecked_vals} distinct value(s) ({n_unchecked_occ} occurrence(s)) under "
                    f"{len(mixed)} mixed key(s) ({', '.join(mixed)}) are UNCHECKED, not passed")
        print(f"  PASS  {msg}")
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
