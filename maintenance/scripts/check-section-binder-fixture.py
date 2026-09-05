#!/usr/bin/env python3
"""
Fixture for section_binder.py — WRITTEN BEFORE THE BINDER, deliberately.

Seven times over 2026-09-04/05 the same sentence appeared in this gate family — a
clean result reported over nothing — and every instance was in the guard added most
recently. Three of those times the new guard carried the exact defect it was written
to prevent. The structural cause is ordering: a guard added in response to review is
last relative to its own verification, and a case that has never been red has never
been shown to fire.

So this file exists before `section_binder.py` does. Every case below is currently
red, and each one goes green only when the binder is built to satisfy it. The floor
cases in particular are written first on purpose, because on this gate's evidence the
floor is what ends up unverified.

Usage: python3 maintenance/scripts/check-section-binder-fixture.py [-v]
"""
from __future__ import annotations
import argparse, pathlib, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE.parents[0] / 'fixtures' / 'section-binder'
CORPUS = FIX / 'corpus'
sys.path.insert(0, str(HERE))

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
A = ap.parse_args()

fails: list[str] = []
checks = 0


def check(label, thunk, want):
    """A crash is a FAILURE, not an absence of one. `thunk` is ALWAYS a callable.

    A mutation that made parse_chain return None took this file down with an
    AttributeError, and a harness reading only `^  FAIL` lines saw no reds and
    scored the mutation as undetected — the crashing-mutant lesson from
    check-type-values-fixture.py, one file later, in the harness written after it.

    The first repair was worse than the bug: `if callable(got)` made the two calls
    that had crashed lazy and left the rest eager, so a `next(...)` in an argument
    still raised StopIteration BEFORE check() was entered and the mutation still
    scored zero reds. Fixing the reported instance and leaving its neighbours is
    the same defect as a derived count beside a hardcoded list. Every call site
    passes a lambda; the signature enforces it.
    """
    global checks
    checks += 1
    if not callable(thunk):
        fails.append(f'{label}: check() takes a callable, got {type(thunk).__name__} '
                     f'— an eagerly-evaluated argument crashes before check() sees it')
        return
    try:
        got = thunk()
    except Exception as e:                      # noqa: BLE001
        fails.append(f'{label}: raised {type(e).__name__}: {e}')
        return
    if got != want:
        fails.append(f'{label}: {got!r} != {want!r}')
    elif A.verbose:
        print(f'  ok   {label}')


def expect_raises(label, fn, wanted_substr):
    """A floor must FAIL, and fail saying why. `pytest.raises` in longhand."""
    global checks
    checks += 1
    try:
        fn()
    except Exception as e:                      # noqa: BLE001 - any failure is the point
        if wanted_substr in str(e):
            if A.verbose:
                print(f'  ok   {label}')
            return
        fails.append(f'{label}: raised {e!r}, wanted a message containing '
                     f'{wanted_substr!r}')
        return
    fails.append(f'{label}: did NOT fail — a floor that does not fire is not a floor')


try:
    import section_binder as sb
except ImportError as e:
    print(f'  FAIL  section_binder not importable yet: {e}')
    print( '        Expected while the cases are being written before the binder.')
    sys.exit(1)

docs, src = CORPUS / 'docs', CORPUS / 'src'

# ---- the floors, first, because they are what ends up unverified ------------
expect_raises('floor: an empty docs corpus is not a clean bind',
              lambda: sb.bind_all(pathlib.Path(tempfile.mkdtemp()), src),
              'scanned nothing')
expect_raises('floor: a missing docs corpus is not a clean bind',
              lambda: sb.bind_all(docs / 'no-such-dir', src),
              'not found')
expect_raises('floor: a missing source tree is not a clean bind',
              lambda: sb.bind_all(docs, src / 'no-such-dir'),
              'not found')

# ---- the denominator, before the binding logic ------------------------------
# The setup call is crash-safe too, and it took a third instance to get here.
# check() rejects a non-callable so every ASSERTION survives a crash — but this
# call is not an assertion, and a mutation that made the FQCN path skip its resolve
# check took the whole file down with an AttributeError, printing no FAIL line and
# scoring as "no reds". Making check() uniform and leaving the one call that is not
# a check is the same defect as fixing the reported field and leaving its
# neighbours, which is the defect this fixture already carries two notes about.
try:
    r = sb.bind_all(docs, src, path_style_root='binderpkg')
except Exception as e:                          # noqa: BLE001
    print(f'  FAIL  bind_all raised on the fixture corpus: {type(e).__name__}: {e}')
    print( '        Every case below depends on this call; none of them ran.')
    print(f'\nFIXTURE {checks} check(s): setup failed before the assertions')
    sys.exit(1)
check('sections seen', lambda: r.seen, 21)
check('sections bound', lambda: len(r.bound), 6)
check('sections unbound', lambda: len(r.unbound), 10)
# The sum invariant now has FOUR terms. Every section lands in exactly one class,
# so a section that silently falls out of the classification is a failure rather
# than a smaller number nobody notices.
check('seen == direct + inherited-accepted + inherited-rejected + unbound',
      lambda: sum(r.counts().values()), r.seen)
check('the four counts are all reported',
      lambda: sorted(r.counts()),
      ['direct', 'inherited-accepted', 'inherited-rejected', 'unbound'])

# Each unbound section is counted WITH ITS REASON. "Unbound" as a bare number is
# the aggregate that cannot show one cause reaching zero — the third instance of
# that shape in this gate.
check('unbound reasons, counted separately', lambda: sorted(r.unbound_by_reason.items()),
      sorted([('no Package line', 4),
              ('package does not resolve', 2),
              ('no source file for the class', 3),
              ('class declares no codec chain', 1)]))
# Without a resolve check the FQCN path binds anything with a dot and a capital.
check('a path-style value naming a missing class does not bind',
      lambda: [u.reason for u in r.unbound if u.section == 'Ghost'],
      ['no source file for the class'])
check('an FQCN naming a missing class does not bind',
      lambda: [u.reason for u in r.unbound if u.section == 'Phantom'],
      ['no source file for the class'])
# A directory with no .java is not a package. Counted as one, this section falls
# through to the class lookup and the two reasons trade members.
check('a package directory with no .java does not resolve',
      lambda: [u.reason for u in r.unbound
               if u.section == 'Widget' and u.page == 'unbound.md'],
      ['package does not resolve'])

# ---- the binding itself -----------------------------------------------------
check('bound section names', lambda: sorted(b.section for b in r.bound),
      ['Derived', 'Gadget', 'Learning Widgets', 'Nested', 'SubWidget', 'Widget'])
# 28 real sections put an FQCN on the Package line. Binding on the heading gives
# `binderpkg.Gadget.Learning` — the heading heuristic must not run at all here.
# 40 real sections on the interactions-* pages are path-style, and all 40 resolve.
# --- inherited scope: a hypothesis the CONTENT confirms, not binding by position -
# A subsection under a bound class inherits its binding only if every top-level key
# it names exists on that class's parsed chain (parents walked). One unknown key
# rejects it, and the rejection names the key. A misattributed table's keys do not
# exist on the ancestor, so the guard fails toward refusing rather than accusing.
check('a subsection whose keys all exist on the ancestor is ACCEPTED',
      lambda: sorted(b.section for b in r.inherited_accepted),
      ['Derived Properties', 'SubWidget Properties', 'Widget Discriminated',
       'Widget Properties'])
check('a subsection naming a foreign key is REJECTED, not bound',
      lambda: [(x.section, x.failing_key) for x in r.inherited_rejected],
      [('Widget Examples', 'Colour')])
check('an accepted inherited binding carries the ANCESTOR fqcn',
      lambda: next(b.fqcn for b in r.inherited_accepted
                   if b.section == 'Widget Properties'), 'binderpkg.Widget')
check('inheritance does not inflate the DIRECT count',
      lambda: len(r.bound), 6)

# A subsection's table routinely documents keys inherited from a parent codec.
# An inherited binding with nothing to confirm it is binding by POSITION, which is
# what the guard refuses. Absence of evidence is not evidence.
check('a subsection with no keys is not accepted on position alone',
      lambda: [u.reason for u in r.unbound if u.section == 'Widget Notes'],
      ['no Package line'])
check('the fingerprint walks parent chains',
      lambda: [b.fqcn for b in r.inherited_accepted
               if b.section == 'SubWidget Properties'], ['binderpkg.SubWidget'])
# A sibling heading ends the scope: `#### Orphan Details` must not reach SubWidget.
# Two SimpleInteraction.java exist in the real tree, so a unique-filename lookup
# refuses and the walk stops at hop 0. The decoy binderpkg/decoy/Widget.java
# reproduces that; resolution must prefer the sibling package.
check('an ambiguous parent simple name still resolves, sibling-first',
      lambda: [b.fqcn for b in r.inherited_accepted
               if b.section == 'SubWidget Properties'], ['binderpkg.SubWidget'])
# Interaction.ABSTRACT_CODEC is the real case for this one.
check('a parent whose codec field is not CODEC is walked',
      lambda: [b.fqcn for b in r.inherited_accepted
               if b.section == 'Derived Properties'], ['binderpkg.Derived'])
check('a sibling heading ends the inherited scope',
      lambda: [u.reason for u in r.unbound if u.section == 'Orphan Details'],
      ['no Package line'])

check('a path-style Package value binds under the supplied root',
      lambda: next(b.fqcn for b in r.bound if b.section == 'Nested'),
      'binderpkg.sub.Nested')
check('an FQCN Package line binds on itself, not on the heading',
      lambda: next(b.fqcn for b in r.bound if b.section == 'Learning Widgets'),
      'binderpkg.Gadget')
check('Widget resolves to its FQCN',
      lambda: next(b.fqcn for b in r.bound if b.section == 'Widget'), 'binderpkg.Widget')
check('Widget hands back its parsed chain (2 keys)',
      lambda: len(next(b.chain.keys for b in r.bound if b.section == 'Widget')), 2)
check('Gadget hands back its parsed chain (1 key)',
      lambda: len(next(b.chain.keys for b in r.bound if b.section == 'Gadget')), 1)
# A multi-word heading: the binder must take the first CamelCase token. With every
# fixture heading a single word, `cls = title` passed identically and the behaviour
# was untested.
check('a multi-word heading binds on its first class token',
      lambda: [u.detail for u in r.unbound if u.section == 'Sprinkler Component'],
      ['binderpkg.Sprinkler'])

print(f'\nFIXTURE {checks} check(s): {checks - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
sys.exit(1 if fails else 0)
