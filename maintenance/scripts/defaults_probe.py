#!/usr/bin/env python3
"""
defaults_probe — what value does a codec key hold when the key is absent?

Queued gate 1, step 5. A `| Key | Type | Default |` table is one of the most
falsifiable things in the corpus and nothing reads it: the fields check confirms
*documented -> real* for key NAMES and says nothing about values, so a default
that changed in the jar reads exactly like one that did not.

THE ANSWER IS THE FIELD INITIALISER, AND THE KEY->FIELD MAP IS NOT THE NAME.
`ClearOutXZ` sets `clearoutXZ`, `DisplayName` sets `displayNameKey`. A casing rule
gets the first and invents the second. The map is written down in the chain — the
append group's SECOND argument is the setter, `(o, s) -> { o.field = s; }` — so it
is read, not guessed.

WHAT THIS REFUSES TO ANSWER, and why refusing is the whole design. Three setter
shapes give no single field: a lambda assigning two of them, a method reference,
and a body that calls rather than assigns. A neighbouring gate's naive version of
this comparison was measured at a 44% false-positive rate, all four flags its own
bug; the first prototype of THIS one reported 14 disagreements and every one was a
normaliser defect (an enum-tail rule that read `1.3` as `3`; a literal-detector
that read the bare word `Required` as a value). So every key the probe cannot
resolve is returned WITH ITS REASON and counted, never dropped and never guessed
at — a check that silently narrows its input is a clean run over nothing, which is
the sentence this gate family has now produced seven times.

A transform in the setter is NOT a refusal. `o.chargeTime = -s` decodes the key
differently; it does not change what the field holds when the key is absent. One
assignment to one field is enough, whatever the right-hand side.

Library only. `check-defaults-fixture.py` was written before this file and every
case in it was red first.
"""
from __future__ import annotations
import pathlib, re
from dataclasses import dataclass

from codec_parser import find_source, parse_chain

# A field declaration. Deliberately anchored to a whole line and rejecting any
# type containing `(`, because a local variable inside a method body has the same
# shape as a field and only the enclosing braces tell them apart — see
# `_fields`, which counts depth rather than trusting this pattern alone.
FIELD = re.compile(
    r'^[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*)*'
    r'(?:public|protected|private)?[ \t]*(?:static[ \t]+)?(?:final[ \t]+)?(?:transient[ \t]+)?'
    r'([A-Za-z_][\w.]*(?:<[^;=]*>)?(?:\[\])*)[ \t]+(\w+)[ \t]*(?:=[ \t]*(.+?))?[ \t]*;[ \t]*$')

# `(o, s) -> { ... }` — a two-parameter lambda with a block body.
LAMBDA = re.compile(r'^\(\s*(\w+)\s*,\s*(\w+)\s*\)\s*->\s*\{(.*)\}$', re.S)
# `<param>.<field> =` at the head of a statement, and NOT `==`.
ASSIGN = re.compile(r'(?:^|[;{])\s*(\w+)\s*\.\s*(\w+)\s*=(?!=)')

# ONLY PRIMITIVES HAVE A ZERO. `private Boolean jumping;` defaults to null;
# reading it as `boolean` gives `false` and accuses five correctly documented rows
# of interactions-flow.md. Five of the eight disagreements on this gate's first
# real run came from one line holding the boxes in here.
PRIMITIVE_ZERO = {'int': '0', 'long': '0', 'short': '0', 'byte': '0',
                  'float': '0', 'double': '0', 'char': '0', 'boolean': 'false'}


class ProbeFloor(Exception):
    """A floor tripped. Raised, not returned, so a caller cannot read it as a result."""


@dataclass
class Truncation:
    """A parent walk that stopped before the ancestry ran out, and why.

    THE WALK IS SUBJECT TO THIS FILE'S OWN CONTRACT and for one release it was
    not. `hops` hit `if parent is None: return` and dropped the remaining
    ancestry with no reason and no counter — eleven of the gate's bound classes
    on build-26, two of them inside the 13 direct-bound Default tables. Nothing
    wrong shipped: `0 state no key` held, so no documented row named a key that
    only lived on a truncated ancestor. What shipped was a key set silently
    smaller than the probe claimed, and a `0` that read as "every documented key
    was found" when part of what it meant was "we never looked past hop 1".
    That is a true count over a quietly narrowed population, which is the same
    defect as a per-file `covered` denominator and a summed floor, one layer in.
    """
    fqcn: str
    parent: str
    reason: str


@dataclass
class Default:
    key: str
    field: str | None = None
    java_type: str | None = None
    expr: str | None = None          # initialiser source, None when there is none
    value: str | None = None         # normalised; None means NOT RESOLVED
    origin: str = ''                 # 'initialiser' | 'java-zero'
    declared_on: str = ''            # fqcn of the class declaring the field
    reason: str = ''                 # why value is None


def _fields(text: str) -> dict[str, tuple[str, str | None]]:
    """Field declarations at class-body depth only.

    A local variable inside a method matches FIELD exactly, so the brace depth is
    counted and only depth 1 (inside the class body, outside every method) is
    accepted. Without this, `float f = scanState.nextScanTime;` inside a method
    shadows a real field of the same name and the probe reports a method-local
    value as the codec default.
    """
    out: dict[str, tuple[str, str | None]] = {}
    depth = 0
    for line in text.split('\n'):
        stripped = line.strip()
        if depth == 1 and not stripped.startswith(('//', '*', '/*')):
            m = FIELD.match(line)
            if m and '(' not in m.group(1) and m.group(1) not in (
                    'return', 'new', 'else', 'case', 'break', 'throw'):
                out.setdefault(m.group(2), (m.group(1), m.group(3)))
        depth += line.count('{') - line.count('}')
    return out


def _setter_field(raw: str) -> tuple[str | None, str]:
    """The single field a setter assigns, or (None, reason)."""
    m = LAMBDA.match(' '.join(raw.split()))
    if m is None:
        return None, 'setter is not a lambda'
    param, body = m.group(1), m.group(3)
    hits = {f for p, f in ASSIGN.findall(body) if p == param}
    if not hits:
        return None, 'setter assigns no field'
    if len(hits) > 1:
        return None, f'setter assigns {len(hits)} fields'
    return hits.pop(), ''


def _fqcn(path: pathlib.Path, src: pathlib.Path) -> str:
    return str(path.relative_to(src)).replace('/', '.')[:-len('.java')]


IMPORT = re.compile(r'^\s*import\s+static\s+([\w.]+)\s*;|^\s*import\s+([\w.]+)\s*;', re.M)


def _resolve_receiver(recv: str, near: pathlib.Path, src: pathlib.Path,
                      text: str | None = None) -> pathlib.Path | None:
    """The child's own import first, then sibling directory, then up the package
    tree, then a unique tree-wide match.

    Simple names collide — two `SimpleInteraction.java` exist in the real tree —
    and a unique-filename lookup refuses, stopping the walk at hop 0. The binder
    learned this by auditing 15 rejections that all blamed a key the parent
    declares (registry-oracle-notes.md §13).

    THE IMPORT COMES FIRST, and it is what the directory rules cannot do. Ten of
    the gate's classes name `SimpleBlockInteraction.CODEC` as their parent; two
    files carry that name (`protocol` and `…interaction.config.client`) and the
    children live under `builtin/adventure/…`, an ancestor of neither, so no
    directory walk can reach the right one. The disambiguating evidence was
    sitting in the child file the whole time as an explicit single-type import —
    the same imports-first resolution `registry_miner._resolve_type` does, and
    the resolution Java itself performs. Reading it is a hop the corpus can make
    rather than a guess.
    """
    if text is not None:
        for static_imp, imp in IMPORT.findall(text):
            fq = imp or static_imp
            if fq.rsplit('.', 1)[-1] == recv:
                hit = find_source(fq, src)
                if hit is not None:
                    return hit
    d = near.parent
    while str(d).startswith(str(src)):
        cand = d / f'{recv}.java'
        if cand.exists():
            return cand
        if d == src:
            break
        d = d.parent
    hit = find_source(recv, src)
    if hit is not None:
        return hit
    cands = list(src.rglob(f'{recv}.java'))
    return cands[0] if len(cands) == 1 else None


def hops(path: pathlib.Path, src: pathlib.Path, codec_field: str = 'CODEC',
         _depth: int = 0, truncations: list | None = None):
    """Yield (path, text, chain) for a class and every ancestor of its chain.

    The parent's FIELD NAME is part of the address: `chain.parent` is
    `Interaction.ABSTRACT_CODEC`, and `Interaction.CODEC` is a map codec with no
    keys at all, so a walk that keeps the receiver and re-parses `CODEC` arrives
    at the wrong codec or none.

    EVERY EARLY RETURN APPENDS A `Truncation`. There is no bare `return` past the
    first hop: a walk that stops short narrows the key set without narrowing any
    figure that says so, and `truncations` is how a caller can print the
    difference. The depth limit routes through the same channel even though
    nothing on build-26 exceeds five hops — an unmeasured guard that has never
    fired is exactly the one that is wrong the first time it does.
    """
    text = path.read_text(errors='replace')
    chain = parse_chain(text, codec_field=codec_field)
    yield path, text, chain
    if chain is None or not chain.parent:
        return

    def stop(reason):
        if truncations is not None:
            truncations.append(Truncation(_fqcn(path, src), chain.parent, reason))

    if _depth >= 8:
        stop(f'walk hit the {8}-hop depth limit')
        return
    recv, _, fld = chain.parent.partition('.')
    if not fld:
        # A parent with NO receiver is another codec field on THIS class, not a
        # class named `ABSTRACT_CODEC`. `partition` turns it into a class name and
        # the walk goes looking for a file that cannot exist — one class on
        # build-26, and a mis-parse rather than an ambiguity.
        yield from hops(path, src, recv, _depth + 1, truncations)
        return
    parent = _resolve_receiver(recv, path, src, text)
    if parent is None:
        n = len(list(src.rglob(f'{recv}.java')))
        stop('ambiguous simple name and no import names it'
             if n > 1 else 'no source file for the parent class')
        return
    yield from hops(parent, src, fld or 'CODEC', _depth + 1, truncations)


def probe(fqcn: str, src: pathlib.Path,
          truncations: list | None = None) -> dict[str, Default]:
    """Every key on `fqcn`'s chain and its ancestors', with its default or a reason.

    Raises rather than returning an empty dict when the tree is absent: "0 keys,
    0 refusals" is indistinguishable from a clean answer over nothing.
    """
    if not src.exists():
        raise ProbeFloor(f'source tree not found at {src}')
    path = find_source(fqcn, src)
    if path is None:
        raise ProbeFloor(f'no source file found for {fqcn} under {src} — '
                         f'class not found in the source tree')

    chain_hops = list(hops(path, src, truncations=truncations))
    field_scopes = [(_fqcn(p, src), _fields(t)) for p, t, _ in chain_hops]

    out: dict[str, Default] = {}
    for hop_path, _text, chain in chain_hops:
        if chain is None:
            continue
        for key in chain.keys:
            if key.name in out:                  # the nearest chain wins
                continue
            d = Default(key=key.name)
            field, why = _setter_field(getattr(key, 'setter', '') or '')
            if field is None:
                d.reason = why or 'no setter recorded'
                out[key.name] = d
                continue
            d.field = field
            for owner, decls in field_scopes:
                if field in decls:
                    d.java_type, d.expr = decls[field]
                    d.declared_on = owner
                    d.value, d.origin = _value(d.java_type, d.expr)
                    break
            else:
                d.reason = f'field `{field}` is declared on no class in the chain'
            out[key.name] = d
    return out


def _value(java_type: str, expr: str | None) -> tuple[str | None, str]:
    """Normalise a field's default to a comparable string."""
    if expr is None:
        base = java_type.split('<')[0]
        if base.endswith('[]'):                  # an array field is a reference
            return 'null', 'java-zero'
        return PRIMITIVE_ZERO.get(base, 'null'), 'java-zero'
    s = expr.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1], 'initialiser'
    if re.fullmatch(r'-?\d[\d_]*(\.\d*)?(e-?\d+)?[fFdDlL]?', s):
        return re.sub(r'[fFdDlL]$', '', s.replace('_', '')), 'initialiser'
    # A qualified constant — `Mode.Fast`, `ValueType.Absolute` — compares on its
    # last segment, because the docs write the constant and not the enum path.
    # Numbers were handled above, so this rule can no longer see `1.3`; when it
    # could, it reported the default of `ClearOutXZ` as `3`.
    if re.fullmatch(r'[A-Za-z_][\w.]*', s) and '.' in s:
        return s.split('.')[-1], 'initialiser'
    return s, 'initialiser'


# ---- the documented side -----------------------------------------------------

def doc_value(cell: str) -> str | None:
    """The value a Default cell CLAIMS, or None when it claims no literal.

    Only a backticked token is a literal. The prototype accepted any bare word and
    read the marker `Required` as a value, reporting three disagreements against
    `null`; every one was the detector's. Em dashes, italics and bold prose all
    state something other than a value and are counted separately rather than
    compared.
    """
    c = cell.strip()
    m = re.fullmatch(r'`([^`]*)`', c)
    if m is None:
        return None
    v = m.group(1)
    # The docs write JSON, so a value cell is routinely `"Absolute"`. The quotes
    # are the format's, not the value's; three of the eight first-run
    # disagreements were nothing but this pair of characters.
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    return v


def agrees(documented: str, actual: str) -> bool:
    """Whether a documented literal and a resolved default are the same value.

    Three rules, and the loosest one is measurably confined to the case it was
    written for. Which rule decided each of build-26's 84 agreements:

        76  exact string equality
         4  numeric        '0'/'0.0' x3, '-1'/'-1.0' x1
         4  case-folded    'User'/'USER' x4

    All four case-folded comparisons are the `InteractionTarget` split —
    `{User, Owner, Target}` in `protocol` against `{USER, OWNER, TARGET}` in
    `server`, which `EnumStyle.detect` renders to the same JSON. The fallback is
    the loosest thing in this file and it fires on four rows, all of them the named
    case; that is a very different statement from "the loosest thing in this file"
    to a future reader deciding whether to tighten it.
    """
    if documented == actual:
        return True
    try:
        return abs(float(documented) - float(actual)) < 1e-9
    except ValueError:
        pass
    return documented.lower() == actual.lower()
