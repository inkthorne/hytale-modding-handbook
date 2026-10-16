#!/usr/bin/env python3
"""
Run registry_miner against the phase-(b) fixture.

The fixture separates two kinds of figure and only one of them can validate the
miner. `independent` figures were derived BY HAND in registry-oracle-notes.md
§1-§2 before this miner existed, or by hand-registry-recount.py (a route sharing no
code with the miner); reproducing them is evidence. `measured` figures came from
this miner and are regression baselines only — checking a miner against its own
output proves nothing, which is the same circularity CLAUDE.md invariant 7 warns
about for detectors and their matches.

THREE POPULATIONS, kept apart because they were not independent of each other:

  * QUALIFIED sites (`Receiver.FIELD.register(…)`, `getCodecRegistry(Receiver.FIELD)`).
    The hand-derived §1/§2 figures describe these and ONLY these, so they are checked
    against the qualified population and never against the miner's whole output.
  * UNQUALIFIED sites (a bare `CODEC.register(…)` inside the declaring class, and
    `getCodecRegistry(PAGE_CODEC)`). Their figures are the recount's, under their own
    keys, never pasted from the miner. A review of the 0.7.2 pass found that both the
    miner and the recount matched only the qualified spelling, so their agreement
    certified nothing about 69 sites in 20 classes.
  * A SYNTHETIC tree (fixtures/registry-oracle/synthetic/src), hand-written with one
    instance of every binding rule: a nested class registering into the outer class's
    field, a nested class declaring its own same-named field, a shadowing local and
    parameter, `this.`/`super.` receivers, a cast-literal id, an interface field, an
    inherited (unresolvable) field. Run through both scripts.

AGREEMENT. Beyond matching recorded figures, the miner's unqualified output is compared
LIVE with hand-registry-recount.py's on the same tree: site count, registry set, and per
registry the site count, the name set and the count of sites with no resolved name. The
recorded figures can rot; the agreement is recomputed on whatever tree is given.

--mutations reverts each guard the unqualified-binding work added and requires the named
checks to go red (style of check-update-build-fixture.py --mutations). It re-runs this
fixture as a subprocess per mutation, against a patched COPY of the scripts.

Usage: python3 maintenance/scripts/check-registry-fixture.py [--src DIR] [--prev-src DIR] [-v]
                                                              [--mutations]
"""
import argparse, collections, json, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
ap.add_argument('--prev-src', default=os.path.expanduser('~/.cache/hytale-update-snapshot/src'),
                help="previous build's decompiled source, for the recount's validation run")
ap.add_argument('--fixtures', default=str(HERE.parent / 'fixtures/registry-oracle'),
                help='fixture directory (overridable so --mutations can run a patched copy)')
ap.add_argument('--assets', default=os.path.expanduser('~/.cache/hytale-assets'),
                help="shipped assets, for the one route that shares nothing with either script: every id the "
                     "enum evaluation closes must be a value under its registry's key there")
ap.add_argument('--no-assets', action='store_true', help=argparse.SUPPRESS)
ap.add_argument('--no-recount', action='store_true', help=argparse.SUPPRESS)
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--mutations', action='store_true')
a = ap.parse_args()

sys.path.insert(0, str(HERE))
import registry_miner as rm

FIXDIR = pathlib.Path(a.fixtures)
MIN_MUTATIONS = 50     # = len(MUTATIONS); a deleted mutation fails the floor instead of shrinking the run
MIN_CHECKS = 560       # what runs when the previous-build snapshot is NOT the recorded build (about 950 today)

fails, checks = [], 0
agree_checks = 0
a_root_of = {}     # tag -> tree root, so an agreement check can ask the miner for the same defaults


def check(label, got, want):
    """`label` is stable text: --mutations names the checks it expects to go red."""
    global checks
    checks += 1
    if got != want:
        fails.append(f"{label} => {got!r} != {want!r}")
    elif a.verbose:
        print(f"  ok  {label} = {got!r}")


def qualified_view(regs):
    """The registries restricted to their QUALIFIED sites (those with none vanish)."""
    out = {}
    for k, r in regs.items():
        qs = r.of_spelling('qualified')
        if qs:
            out[k] = rm.Registry(r.declaring_type, r.field, qs)
    return out


def short(key):
    return '.'.join(key.rsplit('.', 3)[-2:]) if key.count('.') > 2 else key


def run_recount(root, label):
    """hand-registry-recount.py --unqualified-only on `root`; its JSON, or None."""
    if a.no_recount:
        return None
    with tempfile.TemporaryDirectory() as t:
        out = pathlib.Path(t) / 'rc.json'
        r = subprocess.run([sys.executable, '-I', str(HERE / 'hand-registry-recount.py'), str(root),
                            '--unqualified-only', '--json', str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            fails.append(f"{label} recount ran: exit {r.returncode}: {r.stderr.strip()[-300:]}")
            return None
        return json.loads(out.read_text())


def names_of(sites):
    """Names as the miner itself defines them (Registry.names), so a decision made there
    (the empty id is not a name) is pinned here rather than recomputed."""
    return rm.Registry('', '', list(sites)).names


def figures(regs, skipped):
    """The miner's unqualified figures, in the shape the recount reports."""
    unq = {}
    for k, r in regs.items():
        ss = r.of_spelling('unqualified')
        if ss:
            unq[k] = ss
    return unq


def check_agreement(tag, regs, skipped, rc):
    """Miner vs recount on one tree. Every comparison is a check; a recount that
    visited nothing fails the first."""
    global agree_checks
    n0 = checks
    unq = figures(regs, skipped)
    check(f"{tag} agreement: unqualified site count", sum(len(v) for v in unq.values()), rc['sites'])
    check(f"{tag} agreement: unqualified registry set", sorted(unq), sorted(rc['registries']))
    for k in sorted(set(unq) | set(rc['registries'])):
        ss, rr = unq.get(k, []), rc['registries'].get(k)
        if rr is None:
            continue
        lab = f"{tag} agreement: {short(k)}"
        check(f"{lab} sites", len(ss), rr['sites'])
        check(f"{lab} names", names_of(ss), rr['names'])
        check(f"{lab} no-name sites", sum(1 for s in ss if s.name is None), len(rr['no_name']))
        check(f"{lab} empty-id sites", sum(1 for s in ss if s.name == ''), rr['empty_id_sites'])
    miner_new = sorted(k for k, r in regs.items() if not r.of_spelling('qualified'))
    check(f"{tag} agreement: registries with no qualified site", miner_new, rc['new_keys'])
    check(f"{tag} agreement: unresolved owners", sum(1 for s in skipped if s.reason == 'unresolved'),
          rc['unresolved'])
    check(f"{tag} agreement: excluded calls by reason",
          dict(collections.Counter(s.reason for s in skipped if s.reason != 'unresolved')),
          dict(collections.Counter(e['reason'] for e in rc['excluded'])))
    # The discriminator key of EVERY registry (not only the unqualified population), against the
    # recount's declaration-driven sweep. A registry the recount finds no `new` declaration for is
    # UNKNOWN there, which is the miner's own word for it.
    decl = rc['declared_keys']

    def recount_key(r):
        cands = decl.get(r.key)
        if cands is None:
            tail = '.'.join(c for c in r.declaring_type.split('.') if c[:1].isupper())
            hit = [v for k, v in decl.items() if k.endswith('.' + tail + '.' + r.field)]
            cands = hit[0] if len(hit) == 1 else None
        if cands is None or len(cands) != 1:
            return (None, 'unknown')
        return tuple(cands[0])
    codec_regs = {k: r for k, r in regs.items() if r.field != rm.CORE_COMPONENT_FIELD}
    check(f"{tag} agreement: registries whose key was compared (a recount that visited nothing fails)",
          len(codec_regs) > 0 and len(decl) > 0, True)
    for k, r in sorted(codec_regs.items()):
        check(f"{tag} agreement: discriminator key of {short(k)}", (r.discriminator, r.disc_how), recount_key(r))
    check(f"{tag} agreement: form-3 registries' key vs the factories' literal type tags",
          sorted({r.discriminator for r in regs.values() if r.field == rm.CORE_COMPONENT_FIELD}),
          sorted(rc['factory_tags']))
    check(f"{tag} agreement: constructor-family defaults the two scripts read",
          rm.constructor_defaults(pathlib.Path(a_root_of[tag])), rc['library_defaults'])
    agree_checks += checks - n0


def check_residue(tag, rc, want):
    """What neither spelling covers, as counted by the recount: registries held in a
    variable and getCodecRegistry( calls whose argument is not a field. Pinned, so
    "nothing else is left" is a measurement that can move."""
    for k, v in want.items():
        check(f"{tag} residue: {k}", rc['residue'][k], v)


def check_unqualified_block(tag, regs, skipped, block):
    """The miner against the recount's RECORDED figures for a build (not live)."""
    unq = figures(regs, skipped)
    check(f"{tag} unqualified sites", sum(len(v) for v in unq.values()), block['sites'])
    check(f"{tag} unqualified form-1 sites",
          sum(1 for v in unq.values() for s in v if s.form == 1), block['form1_sites'])
    check(f"{tag} unqualified form-2 sites",
          sum(1 for v in unq.values() for s in v if s.form == 2), block['form2_sites'])
    check(f"{tag} unqualified declaring classes", len(unq), block['declaring_classes'])
    check(f"{tag} UNRESOLVED owners (pinned at zero)",
          sum(1 for s in skipped if s.reason == 'unresolved'), block['unresolved_owner'])
    check(f"{tag} calls excluded by property", sum(1 for s in skipped if s.reason != 'unresolved'),
          block['excluded'])
    check(f"{tag} registries with unqualified sites", sorted(unq), sorted(block['registries']))
    check(f"{tag} registries with no qualified site (the new keys)",
          sorted(k for k, r in regs.items() if not r.of_spelling('qualified')),
          sorted(block['new_registry_keys']))
    for k, want in block['registries'].items():
        ss, lab = unq.get(k, []), f"{tag} {short(k)}"
        check(f"{lab} sites", len(ss), want['sites'])
        check(f"{lab} form-1/form-2", [sum(1 for s in ss if s.form == 1), sum(1 for s in ss if s.form == 2)],
              [want['form1'], want['form2']])
        check(f"{lab} names", names_of(ss), want['names'])
        check(f"{lab} no-name sites", sum(1 for s in ss if s.name is None), want['no_name'])
        check(f"{lab} empty-id sites", sum(1 for s in ss if s.name == ''), want['empty_id_sites'])


def key_label(r):
    return r.discriminator if r.disc_how not in ('map-key', 'unknown', 'unread') else '<' + r.disc_how + '>'


def check_key_block(tag, regs, want, key_counts):
    """Registries per discriminator key, against the recount's declaration-driven counts (plus
    form 3's category registries, which all sit under BuilderFactory.DEFAULT_TYPE). UNKNOWN is
    pinned: a nonzero count is a registry whose names this reader cannot place under any key."""
    got = collections.Counter(key_label(r) for r in regs.values())
    exp = collections.Counter(key_counts)
    form3 = sum(1 for r in regs.values() if r.field == rm.CORE_COMPONENT_FIELD)
    exp[want['library_defaults']['factory']] += form3
    check(f"{tag} registries per discriminator key", dict(sorted(got.items())), dict(sorted(exp.items())))
    check(f"{tag} registries whose key cannot be read (pinned at zero)", got.get('<unknown>', 0), want['unknown_pinned_at'])
    check(f"{tag} form-3 registries (key from BuilderFactory.DEFAULT_TYPE)", form3, want['form3_registries'])


root = pathlib.Path(a.src)
if not root.exists():
    sys.exit(f"FAIL  decompiled source not found at {root}\n"
             "      build it with maintenance/scripts/build-jar-cache.sh")

fx = json.loads((FIXDIR / 'registries.json').read_text())
ind, meas, synth = fx['independent'], fx['measured'], fx['synthetic']
skipped = []
regs = rm.mine(root, skipped)
qual = qualified_view(regs)

# --- Interaction.CODEC: the headline §1 measurement (QUALIFIED population) --
i = next((r for r in qual.values() if r.key.endswith('.Interaction.CODEC')), None)
if i is None:
    fails.append("Interaction.CODEC not found at all")
else:
    e = ind['interaction_codec']
    check("Interaction.CODEC names", len(i.names), e['names'])
    check("Interaction.CODEC form-1 registrations", i.forms()[1], e['form1_registrations'])
    check("Interaction.CODEC form-2 registrations", i.forms()[2], e['form2_registrations'])
    check("Interaction.CODEC form-2 statements", i.statements(2), e['form2_statements'])
    check("Interaction.CODEC verdict", i.verdict, e['verdict'])
    check("Interaction.CODEC has no unqualified site",
          len(regs[i.key].of_spelling('unqualified')), 0)

# --- field table, counted in STATEMENTS of the QUALIFIED population ---------
stmt = collections.defaultdict(lambda: [0, 0])
for r in qual.values():
    stmt[r.field][0] += r.statements(2)
    stmt[r.field][1] += r.statements(1)
for fld, want in ind['field_statements'].items():
    check(f"{fld} form-2 statements", stmt[fld][0], want['form2'])
    check(f"{fld} form-1 statements", stmt[fld][1], want['form1'])

# --- the three verdicts: of the registry AS A WHOLE (what the gate would see) -
for key in ind['open_registries'] + ind['indirect_registries']:
    r = regs.get(key)
    check(f"open verdict: {key.rsplit('.',2)[-2]}.{key.rsplit('.',1)[-1]}",
          r.verdict if r else 'MISSING', 'open')
for key in ind['closed_despite_nonliteral_arg0']['examples']:
    r = regs.get(key)
    check(f"closed despite non-literal arg0: {key.rsplit('.',2)[-2]}.{key.rsplit('.',1)[-1]}",
          r.verdict if r else 'MISSING', 'closed')

check("open registry count (qualified population)",
      sum(1 for r in qual.values() if r.verdict == 'open'), ind['open_registry_count']['value'])
check("open registry count (all spellings)",
      sum(1 for r in regs.values() if r.verdict == 'open'),
      ind['unqualified']['open_registry_count_all_spellings'])
amb = [(r.key, s) for r in regs.values() for s in r.sites if s.kind == 'ambiguous']
check("register calls with two top-level literals", len(amb), 0)

# --- form 3: core-component types, categorised by category() ----------------
# The independent route here is a NAMING CONVENTION (`Builder<Category>*`) plus the
# three constant-named sites it structurally cannot see. It agrees with category()
# resolution only after both corrections are applied, which is exactly why it is
# worth checking: a resolver bug would have to reproduce the convention's own blind
# spots to stay hidden.
cc = {k.rsplit('.', 1)[0]: r for k, r in regs.items()
      if r.field == rm.CORE_COMPONENT_FIELD}
c3 = ind['core_component_types']
check("core-component call sites",
      sum(len(r.sites) for r in cc.values()), c3['call_sites'])
check("core-component sites named by a constant",
      sum(1 for r in cc.values() for s in r.sites if s.kind == 'constant'),
      c3['constant_named'])
check("core-component categories", len(cc), len(c3['categories_resolved']))
for cat, want in c3['categories_resolved'].items():
    r = cc.get(cat)
    check(f"category {cat.rsplit('.', 1)[-1]}", len(r.sites) if r else 'MISSING', want)
check("core-component categories unresolved",
      len(cc.get(rm.UNRESOLVED_CATEGORY, rm.Registry('', '')).sites),
      c3['unresolved_categories'])
conv = c3['by_name_convention']
check("convention total + constants == call sites",
      conv['total'] + c3['constant_named'], c3['call_sites'])
diag = rm.core_component_diagnostics(root)
z = c3['zero_pins']
for k in ('files_with_two_category_declarations',
          'extends_first_match_not_own_class',
          'builder_simple_names_ambiguous_in_tree'):
    check(f"zero-pin {k}", diag[k], z[k])
# The type-variable pin is checked by asking the resolver directly: Builder
# declares `Class<T> category()`, so if the guard is removed this returns a
# plausible FQCN instead of None and the whole resolver can silently mis-key.
check("zero-pin category_returning_a_type_variable",
      0 if rm._category_of(
          'Builder',
          {'Builder': 'com.hypixel.hytale.server.npc.asset.builder.Builder'},
          '', root) is None else 1,
      z['category_returning_a_type_variable'])

own_decl, inherited = [], 0
for p_ in root.rglob('*.java'):
    text = p_.read_text(errors='replace')
    if 'registerCoreComponentType' not in text:
        continue
    pkg_m = rm._PKG.search(text)
    imps = {x.rsplit('.', 1)[-1]: x for x in rm._IMPORT.findall(text)}
    for m_ in rm._FORM3.finditer(text):
        o = m_.end() - 1
        try:
            cl = rm._scan(text, o)
            ar = rm._split_args(text[o + 1:cl - 1])
        except (ValueError, AssertionError):
            continue
        if len(ar) < 2 or rm._DECLARATION.match(text, cl):
            continue
        ref = rm._CTOR_REF.match(ar[1].strip())
        if not ref:
            continue
        b = ref.group(1).split('.')[-1]
        f = (rm.find_source(rm._resolve_type(b, imps, pkg_m.group(1) if pkg_m else ''), root)
             or rm.find_source(b, root))
        if f and rm._CATEGORY.search(f.read_text(errors='replace')):
            own_decl.append(b)
        else:
            inherited += 1
check("categories resolved by inheritance", inherited, c3['resolved_by_inheritance'])
check("categories declared on the builder itself", len(own_decl),
      c3['resolved_by_own_declaration'])
check("which builders declare their own category",
      sorted(set(own_decl)), sorted(c3['own_declaration_builders']))

slots = collections.defaultdict(list)
for cat, r in cc.items():
    for n in r.names:
        slots[n].append(cat.rsplit('.', 1)[-1])
for name, want in c3['probes'].items():
    check(f"probe {name}", sorted(slots.get(name, [])), sorted(want))

# --- UNQUALIFIED registrations (the recount's figures, not the miner's) -----
check_unqualified_block("0.7.2", regs, skipped, ind['unqualified'])
disc = ind['discriminators']
check_key_block("0.7.2", regs, disc, disc['declared_by_key_0.7.2'])
# Compared by the LAST TWO name components (`Condition.CODEC`): the recount names the nested
# interface WorldMapManager.MarkerReference, which the miner (resolving a bare receiver to the
# registering file's package) calls worldmap.MarkerReference. Both are the same field.
def tail2(k):
    return '.'.join(k.rsplit('.', 2)[-2:])


check("0.7.2 Id-keyed registries",
      sorted(tail2(k) for k, r in regs.items() if r.discriminator == 'Id'),
      sorted(tail2(k) for k in disc['id_registries_0.7.2']))
check("0.7.2 every registry whose key is not Type: (key, registry)",
      sorted((r.discriminator or key_label(r), tail2(k)) for k, r in regs.items()
             if r.disc_how != 'factory' and r.discriminator != 'Type'),
      sorted((v or '<map-key>', tail2(k)) for k, v in disc['non_type_registries_0.7.2'].items()))
check("0.7.2 form-3 key is the factories' own literal tag",
      sorted(rm.factory_type_tags(root)), sorted(disc['factory_tags']))
# ItemAbility: `.name()` closes it; Bench (an `(Object)BenchType.X` id) stays open
ia = next((r for r in regs.values() if r.key.endswith('.ItemAbility.CODEC')), None)
check("0.7.2 ItemAbility.CODEC names (E.C.name() closes)", ia.names if ia else 'MISSING', ['Core', 'Support'])
check("0.7.2 ItemAbility.CODEC verdict and key", (ia.verdict, ia.discriminator) if ia else 'MISSING', ('closed', 'Slot'))
check("0.7.2 ItemAbility.CODEC sites are enum-name sites",
      sorted(s.kind for s in ia.sites) if ia else 'MISSING', ['enum-name', 'enum-name'])
bench = next((r for r in regs.values() if r.key.endswith('.Bench.CODEC')), None)
check("0.7.2 Bench.CODEC stays open ((Object)BenchType.X is not name())",
      (bench.verdict, bench.discriminator) if bench else 'MISSING', ('open', 'Type'))
a_root_of['0.7.2'] = str(root)
if a.verbose:
    for k, r in sorted(regs.items(), key=lambda kv: (str(kv[1].discriminator), kv[0])):
        if r.disc_how != 'factory' and r.discriminator != 'Type':
            print(f"  key {r.discriminator or '<' + r.disc_how + '>'!s:10} {r.disc_how:9} {k}  <- {r.disc_at}")
rc = run_recount(root, "0.7.2")
if rc is not None:
    check_agreement("0.7.2", regs, skipped, rc)
    check_residue("0.7.2", rc, ind['unqualified']['residue'])

# --- the previous build, if its snapshot is the one the fixture records -----
prev_note = None
prev = pathlib.Path(a.prev_src)
want_ver = ind['unqualified_previous_build']['build'].split()[0]
meta = prev.parent / 'cache-meta.txt'
prev_ver = None
if meta.exists():
    m_ = re.search(r'^version=(.*)$', meta.read_text(), re.M)
    prev_ver = m_.group(1).strip() if m_ else None
if prev.exists() and prev_ver == want_ver:
    pskipped = []
    pregs = rm.mine(prev, pskipped)
    check_unqualified_block("0.6.8", pregs, pskipped, ind['unqualified_previous_build'])
    check_key_block("0.6.8", pregs, disc, disc['declared_by_key_0.6.8'])
    a_root_of['0.6.8'] = str(prev)
    prc = run_recount(prev, "0.6.8")
    if prc is not None:
        check_agreement("0.6.8", pregs, pskipped, prc)
        check_residue("0.6.8", prc, ind['unqualified_previous_build']['residue'])
        # The recount's own figures against the RECORDED previous-build figures: the
        # recount must reproduce the known answer for the old build before its answer
        # for the new one means anything (§15).
        pb = ind['unqualified_previous_build']
        check("0.6.8 recount: unqualified sites", prc['sites'], pb['sites'])
        check("0.6.8 recount: registries", sorted(prc['registries']), sorted(pb['registries']))
        check("0.6.8 recount: new registry keys", prc['new_keys'], sorted(pb['new_registry_keys']))
else:
    prev_note = (f"previous-build check SKIPPED: snapshot at {prev} is "
                 f"{'version ' + prev_ver if prev_ver else 'absent or unstamped'}, the fixture records {want_ver}")

# --- the route that shares nothing with either script: shipped assets -------
# Every id the enum evaluation closes must occur as a value under the registry's own key in the
# shipped assets (Core and Support under "Slot"). Neither script reads an asset, so a rule both
# got wrong (the enum rule is shared between them) cannot be wrong the same way here.
enum_regs = [r for r in regs.values() if any(s.kind == 'enum-name' for s in r.sites)]
check("0.7.2 registries with an enum-name site (the assets route has something to say)",
      sorted(r.key.rsplit('.', 2)[-2] for r in enum_regs), ['ItemAbility'])
asset_note = None
assets = pathlib.Path(a.assets)
if a.no_assets:
    asset_note = None
elif assets.exists():
    for r in enum_regs:
        seen = set()
        pat = re.compile(r'"' + re.escape(r.discriminator) + r'"\s*:\s*"([^"]*)"')
        for f_ in assets.rglob('*.json'):
            seen.update(pat.findall(f_.read_text(errors='replace')))
        for name in sorted({s.name for s in r.sites if s.kind == 'enum-name'}):
            check(f"0.7.2 {r.key.rsplit('.', 2)[-2]}: closed name {name} is a shipped-asset value under {r.discriminator!r}",
                  name in seen, True)
else:
    asset_note = f"asset route SKIPPED: no shipped assets at {assets}"
if asset_note:
    prev_note = (prev_note + "; " if prev_note else "") + asset_note

# --- the synthetic tree: one instance of every binding rule -----------------
syn_root = FIXDIR / 'synthetic/src'
if not syn_root.exists():
    fails.append(f"synthetic tree missing at {syn_root}")
else:
    sskipped = []
    sregs = rm.mine(syn_root, sskipped)
    sunq = figures(sregs, sskipped)
    check("synthetic: unqualified sites", sum(len(v) for v in sunq.values()), synth['unqualified_sites'])
    check("synthetic: qualified sites",
          sum(len(r.of_spelling('qualified')) for r in sregs.values()), synth['qualified_sites'])
    check("synthetic: registry set", sorted(sregs), sorted(synth['registries']))
    for k, want in synth['registries'].items():
        r, lab = sregs.get(k), f"synthetic {short(k)}"
        us = r.of_spelling('unqualified') if r else []
        qs = r.of_spelling('qualified') if r else []
        check(f"{lab}: unqualified names", names_of(us), want['unqualified_names'])
        check(f"{lab}: qualified names", names_of(qs), want['qualified_names'])
        check(f"{lab}: unqualified sites", len(us), want['unqualified_sites'])
        check(f"{lab}: no-name sites", sum(1 for s in us if s.name is None), want['no_name'])
        if 'form2' in want:
            check(f"{lab}: form-2 sites", sum(1 for s in us if s.form == 2), want['form2'])
        if 'empty_id_sites' in want:
            check(f"{lab}: empty-id sites", sum(1 for s in us if s.name == ''), want['empty_id_sites'])
        check(f"{lab}: discriminator (key, how)", [r.discriminator, r.disc_how] if r else 'MISSING',
              want['discriminator'])
    # One check per enum case, each on a NAME that only that case can supply, so a mutation of one
    # guard reddens its own check and not the others'.
    ec = sregs.get('synth.gamma.EnumCases.CODEC')
    en = set(ec.names) if ec else set()
    for nm, closes, why in (('Alpha', True, 'constant with an argument'), ('Beta', True, 'constant with a body'),
                            ('Low', True, 'enum reached through an import'),
                            ('Red', True, 'enum nested in the registering file'),
                            ('Epsilon', False, 'the enum has no such constant'),
                            ('Gamma', False, 'a class with a static field of that name, not an enum'),
                            ('Gamma9', False, 'toString() is overridable'),
                            ('Delta9', False, '(Object)E.C goes through the key codec')):
        check(f"synthetic enum: {nm} ({why}) {'closes' if closes else 'stays open'}", nm in en, closes)
    reg_ = sregs.get('synth.alpha.Registry.CODEC')
    check("synthetic enum: Core (Slot.Core.name(), Slot is not in the tree) stays open",
          'Core' in (reg_.names if reg_ else ['MISSING']), False)
    check("synthetic: registries with no qualified site",
          sorted(k for k, r in sregs.items() if not r.of_spelling('qualified')), synth['new_registry_keys'])
    check("synthetic: calls excluded by property",
          dict(collections.Counter(s.reason for s in sskipped if s.reason != 'unresolved')), synth['excluded'])
    check("synthetic: unresolved owners",
          sum(1 for s in sskipped if s.reason == 'unresolved'), synth['unresolved_owner'])
    check("synthetic: no registry is keyed on this/super or the unresolved sentinel",
          sorted(k for k in sregs if '.this.' in k or '.super.' in k or rm.UNRESOLVED_OWNER in k), [])
    check("synthetic: open registries",
          sorted(k for k, r in sregs.items() if r.verdict == 'open'), synth['open_registries'])
    check("synthetic: registries per discriminator key", dict(sorted(collections.Counter(
          key_label(r) for r in sregs.values()).items())), dict(sorted(synth['registries_by_key'].items())))
    check("synthetic: registries whose key cannot be read",
          sorted(k for k, r in sregs.items() if r.disc_how == 'unknown'), synth['unknown_key_registries'])
    check("synthetic: the key defaults were read from the stubs, not assumed",
          rm.constructor_defaults(syn_root), {'id': 'Disc', 'asset': 'Form', 'factory': 'Variant'})
    a_root_of['synthetic'] = str(syn_root)
    src_text = ' '.join(p.read_text() for p in syn_root.rglob('*.java'))
    check("synthetic: the tree has a local, a this and a super shadow to exclude",
          [x in src_text for x in ('CodecMapCodec<Outer> CODEC', 'this.CODEC.register', 'super.CODEC.register')],
          [True, True, True])
    src_rc = run_recount(syn_root, "synthetic")
    if src_rc is not None:
        check_agreement("synthetic", sregs, sskipped, src_rc)
        check_residue("synthetic", src_rc, synth['residue'])

# --- regression baselines (cannot validate, only detect drift) --------------
drift = []
if len(regs) != meas['registries']:
    drift.append(f"registry count {len(regs)} != {meas['registries']}")
if len(qual) != meas['registries_before_unqualified']:
    drift.append(f"qualified registry count {len(qual)} != {meas['registries_before_unqualified']}")
nreg = sum(len(r.sites) for r in regs.values())
if nreg != meas['registrations']:
    drift.append(f"registrations {nreg} != {meas['registrations']}")
nqreg = sum(len(r.sites) for r in qual.values())
if nqreg != meas['registrations_before_unqualified']:
    drift.append(f"qualified registrations {nqreg} != {meas['registrations_before_unqualified']}")
got2 = sorted(r.key for r in regs.values() if r.forms()[1] == 0 and r.forms()[2] > 0)
if got2 != meas['second_form_only']:
    drift.append(f"second-form-only set changed ({len(got2)} vs {len(meas['second_form_only'])})")

MUTATIONS = []   # filled in below; defined here so the base run does not need it


def mutate():
    """Reintroduce each guard's absence in a patched COPY of the scripts and require the
    named checks to go red. A patch that no longer applies is a failure (the code moved:
    update the mutation); so is a named check that stays green or does not exist."""
    ran, bad = 0, []
    for label, fname, patches, must_red in MUTATIONS:
        with tempfile.TemporaryDirectory() as t:
            scripts = pathlib.Path(t) / 'scripts'
            scripts.mkdir()
            for f in ('codec_parser.py', 'registry_miner.py', 'hand-registry-recount.py',
                      'check-registry-fixture.py'):
                shutil.copy(HERE / f, scripts / f)
            target = scripts / fname
            text = target.read_text()
            ok = True
            for old, new in patches:
                if text.count(old) != 1:
                    bad.append(f"{label}: patch no longer applies to {fname} ({text.count(old)} match(es))")
                    ok = False
                    break
                text = text.replace(old, new)
            if not ok:
                continue
            target.write_text(text)
            cmd = [sys.executable, '-I', str(scripts / 'check-registry-fixture.py'),
                   '--src', a.src, '--prev-src', a.prev_src, '--fixtures', str(FIXDIR), '--no-assets']
            r = subprocess.run(cmd, capture_output=True, text=True)
            ran += 1
            red = {m.group(1) for m in re.finditer(r'^  FAIL (.*?) => ', r.stdout, re.M)}
            if r.returncode == 0:
                bad.append(f"{label}: the whole fixture stayed green")
                continue
            if re.search(r'Traceback', r.stderr + r.stdout) and not red:
                bad.append(f"{label}: crashed instead of going red: {r.stderr.strip()[-200:]}")
                continue
            stayed = sorted(must_red - red)
            if stayed:
                bad.append(f"{label}: still green: {'; '.join(stayed)}")
            elif a.verbose:
                print(f"  red {label}: {len(red)} check(s) failed, including all {len(must_red)} expected")
    return ran, bad


P = 'registry_miner.py'
R = 'hand-registry-recount.py'
MUTATIONS += [
    ("unqualified matching disabled (the defect the review found: the old miner)", P,
     [("_FORM2U = re.compile(r'getCodecRegistry\\s*\\(\\s*(' + CODEC_FIELD + r')\\s*\\)')",
       "_FORM2U = re.compile(r'(?!)')"),
      ("_FORM1U = re.compile(r'(?<![\\w.$])(' + CODEC_FIELD + r')\\s*\\.register\\s*\\(')",
       "_FORM1U = re.compile(r'(?!)')")],
     {"0.7.2 unqualified sites", "0.7.2 unqualified declaring classes",
      "0.7.2 registries with unqualified sites",
      "0.7.2 registries with no qualified site (the new keys)",
      "0.7.2 agreement: unqualified site count", "0.7.2 agreement: unqualified registry set",
      "synthetic: unqualified sites", "synthetic: registry set",
      "synthetic Outer.CODEC: unqualified names", "open registry count (all spellings)"}),
    ("unqualified form-2 spelling disabled (getCodecRegistry(PAGE_CODEC))", P,
     [("_FORM2U = re.compile(r'getCodecRegistry\\s*\\(\\s*(' + CODEC_FIELD + r')\\s*\\)')",
       "_FORM2U = re.compile(r'(?!)')")],
     {"0.7.2 unqualified form-2 sites", "synthetic PageHolder.PAGE_CODEC: form-2 sites",
      "open verdict: OpenCustomUIInteraction.PAGE_CODEC",
      "0.7.2 agreement: unqualified site count"}),
    ("unqualified form-1 spelling disabled (CODEC.register)", P,
     [("_FORM1U = re.compile(r'(?<![\\w.$])(' + CODEC_FIELD + r')\\s*\\.register\\s*\\(')",
       "_FORM1U = re.compile(r'(?!)')")],
     {"0.7.2 unqualified form-1 sites", "synthetic Own.CODEC: unqualified names",
      "0.7.2 agreement: unqualified site count"}),
    ("binding to the file's top-level class instead of the innermost declaring class", P,
     [("                if fld in sc.fields:\n                    return 'class'",
       "                if fld in sc.fields and k == 0:\n                    return 'class'")],
     {"synthetic: registry set", "synthetic Own.CODEC: unqualified names",
      "synthetic Outer.CODEC: unqualified names", "synthetic agreement: unqualified registry set"}),
    ("property exclusion removed: a local or parameter shadowing the field is admitted", P,
     [("                if self._owner(lm.start(1)) is sc:\n                    return 'local', None",
       "                if self._owner(lm.start(1)) is sc:\n                    continue")],
     {"synthetic: calls excluded by property", "synthetic Outer.CODEC: unqualified names",
      "synthetic agreement: excluded calls by reason"}),
    ("property exclusion removed: a this./super. receiver is admitted", P,
     [("            if recv.split('.')[-1] in ('this', 'super'):      # property: an instance receiver",
       "            if False:      # property: an instance receiver")],
     {"synthetic: calls excluded by property",
      "synthetic: no registry is keyed on this/super or the unresolved sentinel",
      "synthetic: registry set"}),
    ("cast-literal ids unresolved", P,
     [("    m = _LITERAL.match(a) or _CAST_LITERAL.match(a)", "    m = _LITERAL.match(a)")],
     {"0.7.2 Schema.CODEC no-name sites", "0.7.2 Schema.CODEC names",
      "synthetic Outer.CODEC: unqualified names", "0.7.2 agreement: Schema.CODEC no-name sites"}),
    ("an unresolvable owner is guessed (the outermost lexical class) instead of reported", P,
     [("                    return 'local', None\n        return 'unresolved', None\n",
       "                    return 'local', None\n        return 'class', [c.cls for c in chain if c.cls][:1]\n")],
     {"synthetic: unresolved owners", "synthetic: registry set"}),
    ("interface fields no longer implicitly static", P,
     [("                static = sc.iface or bool(re.search(r'\\bstatic\\b', head))",
       "                static = bool(re.search(r'\\bstatic\\b', head))")],
     {"synthetic: registry set", "synthetic: calls excluded by property"}),
    ("comments and string literals not masked before reading braces", P,
     [("        m = self.masked = masked if masked is not None else _mask(src)", "        m = self.masked = src")],
     {"synthetic: registry set"}),
    ("recount: cast-literal ids unresolved", R,
     [("        m = re.fullmatch(r'\"([^\"]*)\"', a) or re.fullmatch(CAST_LIT, a)",
       "        m = re.fullmatch(r'\"([^\"]*)\"', a)")],
     {"0.7.2 agreement: Schema.CODEC names", "synthetic agreement: Outer.CODEC names"}),
    ("recount: local shadow not looked for", R,
     [("                if shadow:\n", "                if False:\n")],
     {"synthetic agreement: excluded calls by reason", "synthetic agreement: Outer.CODEC sites"}),
    ("inheritance guard removed: a class that may inherit the name is walked past", P,
     [("                if sc.inherits:\n                    return 'unresolved', None",
       "                if False:\n                    return 'unresolved', None")],
     {"synthetic: unresolved owners", "synthetic Host.CODEC: unqualified names"}),
    ("anonymous-class guard removed: `new Base() { … }` is walked past", P,
     [("            if sc.anon:\n                return 'unresolved', None",
       "            if False:\n                return 'unresolved', None")],
     {"synthetic: unresolved owners", "synthetic Host.CODEC: unqualified names"}),
    ("instance-field guard removed: an inner instance CODEC binds to the outer static one", P,
     [("                if fld in sc.inst:\n                    return 'instance', None",
       "                if False:\n                    return 'instance', None")],
     {"synthetic: calls excluded by property", "synthetic: registry set"}),
    ("lambda-parameter shadow not looked for", P,
     [("            for lm in lam.finditer(self.masked, sc.header, off):", "            for lm in ():")],
     {"synthetic Host.CODEC: unqualified names", "synthetic: calls excluded by property"}),
    ("only the innermost block is searched for a shadowing local", P,
     [("            for lm in local.finditer(self.masked, sc.header, off):",
       "            for lm in (local.finditer(self.masked, sc.header, off) if k == len(chain) - 1 else ()):")],
     {"synthetic Host.CODEC: unqualified names", "synthetic: calls excluded by property"}),
    ("anchors read from unmasked text: a registration in a comment counts", P,
     [("        mstmt = masked[off:off + len(stmt)]", "        mstmt = stmt")],
     {"synthetic Host.CODEC: unqualified names", "synthetic Host.CODEC: unqualified sites"}),
    ("second declarator of a static declaration not seen", P,
     [("                names += _FIELD_DECLARATOR.findall(seg)", "                pass")],
     {"synthetic: unresolved owners", "synthetic: registry set"}),
    ("a `}` followed by `;` ends a field member (lambda in a field initialiser)", P,
     [("                if depth == 0 and not re.match(r'\\s*[;,).\\]]', m[i + 1:i + 40]):",
       "                if depth == 0:")],
     {"0.7.2 unqualified sites", "0.7.2 agreement: unqualified site count"}),
    ("the empty id counted as a vocabulary name", P,
     [("        return sorted({s.name for s in self.sites if s.name})",
       "        return sorted({s.name for s in self.sites if s.name is not None})")],
     {"0.7.2 Schema.CODEC names", "synthetic Registry.CODEC: unqualified names"}),
    ("recount: an inheriting class is walked past", R,
     [("                    if classes[k]['inherits']:", "                    if False:")],
     {"synthetic agreement: unresolved owners"}),
    ("recount: an instance field is not recognised", R,
     [("                    if fld in classes[k]['inst']:", "                    if False:")],
     {"synthetic agreement: excluded calls by reason"}),
    ("recount: a local in a closed sibling block still shadows", R,
     [("\n                          and still_open(code, lm.start(1), at)]", "]")],
     {"synthetic agreement: Host.CODEC sites"}),
    ("expression-lambda parameters ahead of the site in its statement not looked for", P,
     [("        for lm in lam.finditer(self.masked, st, off):", "        for lm in ():")],
     {"synthetic Scopes.CODEC: unqualified names", "synthetic: calls excluded by property"}),
    ("a typed lambda parameter is read as a local of the whole enclosing block", P,
     [("                if self._lambda_parameter(lm.end() - 1):\n                    continue",
       "                if False:\n                    continue")],
     {"synthetic Scopes.CODEC: unqualified names", "synthetic agreement: Scopes.CODEC names"}),
    ("text blocks not masked", P,
     [("        if src.startswith('\"\"\"', i):\n            j = _text_block_end(src, i)\n            for k",
       "        if False:\n            j = _text_block_end(src, i)\n            for k")],
     {"synthetic Scopes.CODEC: unqualified names", "synthetic agreement: Scopes.CODEC names"}),
    ("recount: a catch/for/parameter name outlives the block that follows its parentheses", R,
     [("        if k < len(code) and code[k] == '{':\n            return k < at <= block_end(code, k)",
       "        if False:\n            return k < at <= block_end(code, k)")],
     {"synthetic agreement: Scopes.CODEC names"}),
    ("recount: a typed lambda parameter outlives the lambda", R,
     [("        if code.startswith('->', k):", "        if False:")],
     {"synthetic agreement: Scopes.CODEC names"}),
    ("recount: text blocks not masked", R,
     [('|\\"\\"\\"(?:\\\\.|[^\\\\])*?\\"\\"\\"', "")],
     {"synthetic agreement: Scopes.CODEC names"}),
    ("recount: registries held in a variable not counted", R,
     [("    for m in re.finditer(r'=\\s*[\\w.()]*getCodecRegistry\\s*\\(', code):",
       "    for m in re.finditer(r'(?!)', code):")],
     {"synthetic residue: variable_held_registries"}),
    ("recount: a non-field getCodecRegistry( argument is skipped like a field", R,
     [("            if arg_ok.match(code[m.end():close]):", "            if True:")],
     {"synthetic residue: non_field_argument_calls", "synthetic residue: non_field_argument_declarations",
      "0.7.2 residue: non_field_argument_declarations"}),
    # ---- discriminator keys (2026-10-15) -------------------------------------------------
    ("key defaults assumed (Id / Type / Type), not read from the library source", P,
     [("    out = {'id': None, 'asset': None, 'factory': None}\n    f = _only_file(root, 'ACodecMapCodec.java')",
       "    out = {'id': 'Id', 'asset': 'Type', 'factory': 'Type'}\n    _DEFAULTS_CACHE[ck] = out\n    return out\n    f = _only_file(root, 'ACodecMapCodec.java')")],
     {"synthetic Dflt.CODEC: discriminator (key, how)", "synthetic AssetDefault.CODEC: discriminator (key, how)",
      "synthetic Widget.CORE_COMPONENT_TYPES: discriminator (key, how)",
      "synthetic: the key defaults were read from the stubs, not assumed",
      "synthetic agreement: constructor-family defaults the two scripts read"}),
    ("a key the constructor does not spell readably is guessed instead of UNKNOWN", P,
     [("    return None, 'unknown'\n\n\ndef declared_key",
       "    return defaults.get('id'), 'default'\n\n\ndef declared_key")],
     {"synthetic Unreadable.CODEC: discriminator (key, how)", "synthetic: registries whose key cannot be read",
      "synthetic agreement: discriminator key of Unreadable.CODEC"}),
    ("a field with no `new` declaration is guessed instead of UNKNOWN", P,
     [("    return None, 'unknown', where\n\n\n", "    return defaults.get('id'), 'default', where\n\n\n")],
     {"synthetic NotNew.CODEC: discriminator (key, how)", "synthetic: registries whose key cannot be read",
      "synthetic agreement: discriminator key of NotNew.CODEC"}),
    ("a declaration is not bound to its class chain: two TYPE_CODECs in one file are confused", P,
     [("            if not tail or chain[-len(tail):] != tail:\n                continue",
       "            if False:\n                continue")],
     {"synthetic Pair.TYPE_CODEC: discriminator (key, how)", "synthetic Inner.TYPE_CODEC: discriminator (key, how)",
      "synthetic agreement: discriminator key of Pair.TYPE_CODEC"}),
    ("the registering files are not searched when the declaring type's own file is absent", P,
     [("    cands += [pathlib.Path(x) for x in files if pathlib.Path(x) not in cands]", "    cands += []")],
     {"synthetic Marker.CODEC: discriminator (key, how)", "0.7.2 registries whose key cannot be read (pinned at zero)",
      "synthetic agreement: discriminator key of Marker.CODEC"}),
    ("form 3's key assumed to be Type instead of read from BuilderFactory.DEFAULT_TYPE", P,
     [("            r.discriminator, r.disc_how = defaults['factory'], 'factory' if defaults['factory'] else 'unknown'",
       "            r.discriminator, r.disc_how = 'Type', 'factory'")],
     {"synthetic Widget.CORE_COMPONENT_TYPES: discriminator (key, how)",
      "synthetic agreement: form-3 registries' key vs the factories' literal type tags"}),
    ("MapKeyMapCodec read as a discriminator-keyed registry", P,
     [("        return None, 'map-key'            # object KEYS are the names; there is no discriminator",
       "        return defaults.get('id'), 'default'")],
     {"synthetic MapKeyed.PLUGIN_CODEC: discriminator (key, how)", "0.7.2 registries per discriminator key",
      "synthetic agreement: discriminator key of MapKeyed.PLUGIN_CODEC"}),
    ("a string constant passed as the key is not resolved through the file's constant table", P,
     [("        if first in consts:\n            return consts[first], 'constant'", "        if False:\n            return consts[first], 'constant'")],
     {"synthetic ConstKey.CODEC: discriminator (key, how)", "synthetic agreement: discriminator key of ConstKey.CODEC"}),
    ("AssetCodecMapCodec's no-key default taken from the string family instead", P,
     [("        return (defaults.get('asset'), 'default') if defaults.get('asset') else (None, 'unknown')",
       "        return (defaults.get('id'), 'default') if defaults.get('id') else (None, 'unknown')")],
     {"synthetic AssetDefault.CODEC: discriminator (key, how)", "0.7.2 registries per discriminator key",
      "synthetic agreement: discriminator key of AssetDefault.CODEC"}),
    ("recount: the library defaults assumed instead of read", R,
     [("    return {'id': next(iter(id_)) if len(id_) == 1 else None,\n            'asset': next(iter(asset)) if len(asset) == 1 else None,\n            'factory': fac[0] if len(fac) == 1 else None}",
       "    return {'id': 'Id', 'asset': 'Type', 'factory': 'Type'}")],
     {"synthetic agreement: constructor-family defaults the two scripts read",
      "synthetic agreement: discriminator key of Dflt.CODEC"}),
    ("recount: MapKeyMapCodec not recognised as keyless", R,
     [("            if fam == 'MapKeyMapCodec':\n                res = (None, 'map-key')", "            if False:\n                res = (None, 'map-key')")],
     {"synthetic agreement: discriminator key of MapKeyed.PLUGIN_CODEC"}),
    # ---- enum constants as ids: one mutation per guard, each judged on the case only it can change
    ("enum guard E-resolves removed: a type not found in the tree is accepted", P,
     [("        if f is None:                                      # GUARD E-resolves\n            return None",
       "        if f is None:                                      # GUARD E-resolves\n            return const")],
     {"synthetic enum: Core (Slot.Core.name(), Slot is not in the tree) stays open"}),
    ("enum guard enum-kind removed: a class with a static field of that name is read as an enum", P,
     [("    if m.group(1) != 'enum':                     # GUARD enum-kind\n        return None", "    if False:\n        return None")],
     {"synthetic enum: Gamma (a class with a static field of that name, not an enum) stays open"}),
    ("enum guard constant-in-list removed: any C is accepted once E is an enum", P,
     [("    if consts is None or const not in consts:             # GUARD constant-in-list", "    if consts is None:")],
     {"synthetic enum: Epsilon (the enum has no such constant) stays open"}),
    ("enum declared in the registering file not looked for", P,
     [("    if any((cm.group(2) or cm.group(4)) == head for cm in _CLASS_HEADER.finditer(own_masked)):", "    if False:")],
     {"synthetic enum: Red (enum nested in the registering file) closes"}),
    ("toString() accepted like name()", P,
     [(r"\s*\.\s*name\s*\(\s*\)$')", r"\s*\.\s*(?:name|toString)\s*\(\s*\)$')")],
     {"synthetic enum: Gamma9 (toString() is overridable) stays open"}),
    ("(Object)E.C accepted as the constant's name", P,
     [(r"_ENUM_NAME = re.compile(r'^([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\.([A-Za-z_]\w*)\s*\.\s*name\s*\(\s*\)$')",
       r"_ENUM_NAME = re.compile(r'^(?:\(\s*Object\s*\)\s*)?([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\.([A-Za-z_]\w*)(?:\s*\.\s*name\s*\(\s*\))?$')")],
     {"synthetic enum: Delta9 ((Object)E.C goes through the key codec) stays open",
      "0.7.2 Bench.CODEC stays open ((Object)BenchType.X is not name())"}),
    ("recount: an enum constant is accepted without looking it up in the constant list", R,
     [("    return c if c in next(iter(enums[e].values())) else None", "    return c")],
     {"synthetic agreement: EnumCases.CODEC names"}),
]

# ----------------------------------------------------------------------------
# The previous-build note rides on THE SUMMARY LINE, not an INFO line of its own:
# verify-docs.sh shows only the lines starting INDEPENDENT/MUTATIONS/..., so a separate
# INFO line explaining why the check count fell was invisible exactly when it mattered.
print(f"\nINDEPENDENT {checks} check(s) against hand-derived §1/§2 figures, the recount's unqualified "
      f"figures and the synthetic tree: {checks - len(fails)} reproduced, {len(fails)} failed"
      + (f"; {prev_note}" if prev_note else ""))
print(f"AGREEMENT   {agree_checks} of those compare the miner with hand-registry-recount.py live "
      f"(sites, registry set, names and no-name sites per registry)")
print(f"BASELINE    {len(regs)} registries, {sum(len(r.sites) for r in regs.values())} registrations, "
      f"{sum(1 for r in regs.values() if r.verdict == 'open')} open"
      + ("" if not drift else "  — DRIFT:"))
for d in drift:
    print(f"  drift {d}")
if checks < MIN_CHECKS:
    fails.append(f"floor: only {checks} check(s) ran, floor is {MIN_CHECKS}"
                 + (f" ({prev_note})" if prev_note else ""))
if a.mutations:
    ran, bad = mutate()
    if ran < MIN_MUTATIONS or len(MUTATIONS) < MIN_MUTATIONS:
        bad.append(f"only {ran} of {len(MUTATIONS)} mutation(s) ran, floor is {MIN_MUTATIONS}")
    print(f"MUTATIONS {ran} guard(s) removed, "
          f"{ran - len([b for b in bad if 'still green' in b or 'stayed green' in b])} turned their checks red")
    fails += bad
for f in fails:
    print(f"  FAIL {f}")
sys.exit(1 if fails else 0)
