#!/usr/bin/env python3
"""
section_binder — map a docs SECTION to the codec class it documents.

Three queued checks need this one thing and none of them can be built without it:
negative-closure claims need the quoted name checked against a codec; the defaults
check needs a Default column checked against a class's field initialisers; and the
SCOPED half of the "Type"-value gate needs a root codec to walk a JSON fence from.
Built once, per hytale-supervisor's ruling of 2026-09-05.

WHY A SECTION AND NOT A PAGE. registry-oracle-notes.md §3 measured four names that a
corpus-wide match scored as documented when none of them were — `Bed` landing on a
block tag, `Teleporter`/`Portal` on block-entity components, `CameraShake` on a
protocol type. The unit that makes a claim is the section, so the unit that binds
must be the section.

WHAT IT BINDS ON. The `### ClassName` + `**Package:** pkg` convention the doc-type
check already reads for provenance. 51 pages carry one.

WHAT IT DOES NOT DO, and this is the point of the denominator: it binds SOME
sections. Roughly forty `**Package:**` lines in the real corpus read just `config`
and name no resolvable package at all. Every unbound section is counted WITH ITS
REASON — not as one aggregate, because a figure summed over causes cannot show one
cause reaching zero, which is a failure this gate family has now produced three
times (a per-file `covered` denominator over a per-chain numerator; a bucket reading
zero because a higher-priority source claimed the value; a floor summed across three
runners so one silent runner passed).

Library only. `check-section-binder-fixture.py` was written BEFORE this file and every
case in it was red first — see its docstring for why that ordering is the rule here.
"""
from __future__ import annotations
import collections, pathlib, re, sys
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from codec_parser import find_source, parse_chain

# A section heading at any level, then a Package line within a few lines of it. The
# gap is bounded because a `**Package:**` far below its heading belongs to prose in
# between, not to the heading — and an unbounded search would bind a section to the
# next section's package.
HEADING = re.compile(r'^(#{2,4})\s+(.+?)\s*$', re.M)
PACKAGE = re.compile(r'^\*\*Package:\*\*\s*`?([A-Za-z0-9_./]+)`?', re.M)
# Headings are "Widget", "InteractionType Enum", "Interaction Base Class" — take the
# first CamelCase token rather than the whole heading.
CLASSNAME = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)*)\b')

# Measured on the real corpus, 481 Package lines that have a heading above them:
#   gap 1: 204   gap 2: 264   gap 4: 8   gap 6: 3   gap 11: 1   gap 34: 1
# Nothing at 3 or 5, and the mass sits at 1-2, so 4 is a cut through empty space
# rather than an arbitrary number; 6 would recover three more. The gap-34 line is
# genuinely detached from its heading and SHOULD be missed — an unbounded search
# binds a section to the NEXT section's package, which is worse than not binding.
PACKAGE_GAP_LINES = 4

# A Package value whose last segment is CamelCase is a fully-qualified CLASS name,
# not a package. 28 real sections are written that way and all 28 resolve; the
# binder used to append the heading's class to them, look for
# `...TeleporterInteraction.Teleporter`, and record "package does not resolve" —
# sending a reader after a missing package when the FQCN was stated outright. These
# are the most bindable sections in the corpus. Taking the value as the class also
# REMOVES the heading heuristic for them rather than tuning it, which matters where
# the heading would mislead: `### Learning Recipes` binds on `Learning`.
FQCN_TAIL = re.compile(r'\.([A-Z][A-Za-z0-9_]*)$')

# A SECOND BINDING RULE, reported under its own label. Forty sections across the
# four `interactions-*` pages write their Package value as a PATH relative to the
# interaction package — `config/server/SpawnPrefabInteraction`,
# `config/none/simple/...` — rather than as a dotted package. All forty resolve
# under the root below, measured. They earn a rule of their own rather than a
# rewrite of the pages because those four are the JSON-heaviest in the corpus, so
# this is the single largest available widening of the scoped-"Type" check's input.
# The root is a parameter, not a constant, because it is corpus-specific: nothing
# about the shape says "interaction", and a caller with a different tree must say so.
PATH_STYLE_ROOT = 'com.hypixel.hytale.server.core.modules.interaction.interaction'
PATH_STYLE = re.compile(r'^[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)+$')


@dataclass
class Bound:
    page: str
    section: str
    fqcn: str
    chain: object            # codec_parser.Chain


@dataclass
class Unbound:
    page: str
    section: str
    reason: str
    detail: str = ''


@dataclass
class BindResult:
    seen: int = 0
    bound: list[Bound] = field(default_factory=list)
    unbound: list[Unbound] = field(default_factory=list)

    @property
    def unbound_by_reason(self) -> dict[str, int]:
        return dict(collections.Counter(u.reason for u in self.unbound))


class BindFloor(Exception):
    """A floor tripped. Raised, not returned, so a caller cannot read it as a result."""


def _sections(text: str):
    """Yield (section_title, package_or_None) for every heading in a page."""
    lines = text.split('\n')
    for m in HEADING.finditer(text):
        title = m.group(2).strip()
        start = text.count('\n', 0, m.start()) + 1
        window = '\n'.join(lines[start:start + PACKAGE_GAP_LINES])
        pm = PACKAGE.search(window)
        yield title, (pm.group(1) if pm else None)


def bind_all(docs: pathlib.Path, src: pathlib.Path,
             path_style_root: str = PATH_STYLE_ROOT) -> BindResult:
    """Bind every section in `docs` that can be bound, and COUNT the ones that cannot.

    Floors are exceptions rather than an empty result, because "0 bound, 0 unbound"
    is indistinguishable from a clean run over an absent corpus — the sentence this
    gate family has produced seven times.
    """
    for label, p in (('docs corpus', docs), ('source tree', src)):
        if not p.exists():
            raise BindFloor(f'{label} not found at {p}')

    r = BindResult()
    # A directory with no .java in it is not a package for this purpose. 29 of the
    # 1083 directories are like that, and counting them as resolving pushed those
    # sections into "no source file for the class" instead — so the split between
    # those two buckets partly reflected which check ran first rather than the
    # cause. The whole point of the per-reason breakdown is that a cause reaching
    # zero must be visible, which it cannot be if two causes trade members.
    pkg_dirs = {str(d.relative_to(src)).replace('/', '.')
                for d in src.rglob('*') if d.is_dir() and any(d.glob('*.java'))}

    for page in sorted(docs.glob('*.md')):
        text = page.read_text(errors='replace')
        for title, pkg in _sections(text):
            r.seen += 1
            if pkg is None:
                r.unbound.append(Unbound(page.name, title, 'no Package line'))
                continue
            # Rule 2: a path-style value, resolved under the caller's root. Tried
            # before the FQCN rule because a path contains no dots and would
            # otherwise fall through to the package-directory lookup and be
            # recorded as "package does not resolve" — the same mislabelling the
            # FQCN rule was added to fix.
            if PATH_STYLE.match(pkg):
                fqcn = f'{path_style_root}.' + pkg.replace('/', '.')
                path = find_source(fqcn, src)
                if path is None:
                    r.unbound.append(Unbound(page.name, title,
                                             'no source file for the class', fqcn))
                    continue
                chain = parse_chain(path.read_text(errors='replace'))
                if chain is None:
                    r.unbound.append(Unbound(page.name, title,
                                             'class declares no codec chain', fqcn))
                    continue
                r.bound.append(Bound(page.name, title, fqcn, chain))
                continue
            # An FQCN Package line names the class itself; the heading is not
            # consulted at all for these.
            tail = FQCN_TAIL.search(pkg)
            if tail is not None:
                fqcn = pkg
                path = find_source(fqcn, src)
                if path is None:
                    r.unbound.append(Unbound(page.name, title,
                                             'no source file for the class', fqcn))
                    continue
                chain = parse_chain(path.read_text(errors='replace'))
                if chain is None:
                    r.unbound.append(Unbound(page.name, title,
                                             'class declares no codec chain', fqcn))
                    continue
                r.bound.append(Bound(page.name, title, fqcn, chain))
                continue
            cm = CLASSNAME.search(title)
            if cm is None:
                r.unbound.append(Unbound(page.name, title, 'heading names no class'))
                continue
            cls = cm.group(1)
            if pkg not in pkg_dirs:
                # `config`, and ~39 others like it: an abbreviated Package line that
                # names no package in the tree. Distinguished from "the class is
                # missing" because they call for different repairs — one is a doc
                # that under-specifies, the other a doc that names a dead class.
                r.unbound.append(Unbound(page.name, title,
                                         'package does not resolve', pkg))
                continue
            fqcn = f'{pkg}.{cls}'
            path = find_source(fqcn, src)
            if path is None:
                r.unbound.append(Unbound(page.name, title,
                                         'no source file for the class', fqcn))
                continue
            chain = parse_chain(path.read_text(errors='replace'))
            if chain is None:
                # The class resolves but declares no codec chain, which is the
                # COMMON case: most `### ClassName` sections document a component,
                # a system or an event, not a codec. Counted, not crashed on — an
                # earlier version passed the None straight into Bound and the first
                # such section would have taken the binder down.
                r.unbound.append(Unbound(page.name, title,
                                         'class declares no codec chain', fqcn))
                continue
            r.bound.append(Bound(page.name, title, fqcn, chain))

    if r.seen == 0:
        raise BindFloor(
            f'scanned nothing: 0 section(s) across '
            f'{len(list(docs.glob("*.md")))} page(s) under {docs}')
    return r
