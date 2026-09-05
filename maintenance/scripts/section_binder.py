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
PACKAGE = re.compile(r'^\*\*Package:\*\*\s*`?([A-Za-z0-9_.]+)`?', re.M)
# Headings are "Widget", "InteractionType Enum", "Interaction Base Class" — take the
# first CamelCase token rather than the whole heading.
CLASSNAME = re.compile(r'\b([A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)*)\b')

PACKAGE_GAP_LINES = 4


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


def bind_all(docs: pathlib.Path, src: pathlib.Path) -> BindResult:
    """Bind every section in `docs` that can be bound, and COUNT the ones that cannot.

    Floors are exceptions rather than an empty result, because "0 bound, 0 unbound"
    is indistinguishable from a clean run over an absent corpus — the sentence this
    gate family has produced seven times.
    """
    for label, p in (('docs corpus', docs), ('source tree', src)):
        if not p.exists():
            raise BindFloor(f'{label} not found at {p}')

    r = BindResult()
    pkg_dirs = {str(d.relative_to(src)).replace('/', '.')
                for d in src.rglob('*') if d.is_dir()}

    for page in sorted(docs.glob('*.md')):
        text = page.read_text(errors='replace')
        for title, pkg in _sections(text):
            r.seen += 1
            if pkg is None:
                r.unbound.append(Unbound(page.name, title, 'no Package line'))
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
