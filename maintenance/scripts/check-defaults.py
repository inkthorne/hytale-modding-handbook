#!/usr/bin/env python3
"""
Step 5 of queued gate 1: a documented `Default` must be the value the field holds.

A `| Key | Type | Default |` table is the most falsifiable thing on a JSON page and
nothing reads the Default column. `check-symbols.py` skips JSON key paths entirely;
the fields check confirms documented-key -> real for NAMES and never looks at
values. So a default that changed in a new build reads exactly like one that did
not — the silent-falsification shape CLAUDE.md's queued entry names for closure
claims, arriving one column to the right.

WHAT IT CAN SEE, and the denominator is the point. A row is checkable only when
three things hold: its SECTION binds to a codec class, its Default cell states a
backticked LITERAL, and the key's setter names a single field. Every row that fails
one of those is counted under the reason it failed, never dropped. On build-26 that
is a minority of the corpus, and printing the minority is the whole discipline: the
snippet gate's green line read as corpus coverage for a year while compiling 5 of
1091 blocks.

WHY IT FAILS HARD ON DISAGREEMENT. Measured over the real corpus before this file
existed: 0 disagreements against 35 comparable rows. The first prototype reported
14, and all 14 were the instrument — an enum-tail normaliser that read `1.3` as
`3`, and a literal-detector that read the marker word `Required` as a value. Both
are fixture cases now (check-defaults-fixture.py). A gate that hard-fails correct
pages is worse than no gate, and shipping it behind a warning is invariant 1
wallpaper, so it lands hard only because the false-positive rate was measured at
zero rather than assumed.

Usage: python3 maintenance/scripts/check-defaults.py [--docs DIR] [--src DIR] [-v]
Exit 0 pass, 1 findings, 2 SKIP (an oracle is absent — never a pass).
"""
from __future__ import annotations
import argparse, collections, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import defaults_probe as dp
import section_binder as sb

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

KEY_HEADERS = ('key', 'property', 'field', 'name')


def _is_key_header(h: str) -> bool:
    """Does this header name a column of key names?

    The trailing-word rule is not decoration. `camera.md` heads two Default-column
    tables `JSON key`, and an exact-match predicate skipped both — found by a
    reviewer whose independent extraction counted 62 tables against this gate's 60,
    which is the entire value of counting a population twice from two directions.
    It stays narrow at the other end: `interactions-flow.md` has a
    `| DefaultOk | Variable Missing | Result |` table whose FIRST cell begins with
    `Default`, and a predicate keyed on the Default column alone claims it.
    """
    h = h.strip().lower()
    return h in KEY_HEADERS or h.rsplit(' ', 1)[-1] in KEY_HEADERS


def default_tables(body: str):
    """Yield (key_col, default_col, header, rows) for each Default-column key table.

    The predicate is written out because two earlier passes counted this population
    differently and neither said how — 42 sections on 20 pages against 53 on 19,
    from the same corpus (registry-oracle-notes.md §13). A first column headed
    Key/Property/Field/Name, and any header beginning `Default`; build-26 has 59
    plain `Default` headers and one `Default (shipped ...)`.
    """
    for m in sb.TABLE.finditer(body):
        hdr = [c.strip().strip('*`') for c in m.group(1).split('|')]
        ki = next((i for i, h in enumerate(hdr) if _is_key_header(h)), None)
        di = next((i for i, h in enumerate(hdr) if h.lower().startswith('default')), None)
        if ki is None or di is None:
            continue
        yield ki, di, hdr, m.group(2).strip().split('\n')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--docs', default=str(REPO / 'docs'))
    ap.add_argument('--src', default=os.path.expanduser('~/.cache/hytale-jar/src'))
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()
    docs, src = pathlib.Path(a.docs), pathlib.Path(a.src)

    # A SKIP must not share an exit code with a PASS. `check-type-values.py`
    # returned 0 on a missing cache and the caller printed a bare `PASS` with no
    # message; build-jar-cache.sh wipes before rebuilding, so an interrupted
    # rebuild produces exactly that state.
    #
    # THE TWO-SPACE INDENT IS LOAD-BEARING, and this file shipped without it for an
    # hour. verify-docs.sh renders findings with `grep -E '^  (FAIL|SKIP)'`; a SKIP
    # printed at column 0 matches nothing, so a skipped run rendered as a `FAIL`
    # with an empty body — the same defect that made a stale-skiplist-only run of
    # the type-values gate print a header naming the wrong problem over no lines.
    # The exit code and the rendering are two separate things and both have to be
    # right.
    for label, p in (('docs corpus', docs), ('decompiled source', src)):
        if not p.exists():
            print(f'  SKIP  {label} not found at {p}')
            return 2

    try:
        r = sb.bind_all(docs, src)
    except sb.BindFloor as e:
        print(f'  SKIP  section binder floor: {e}')
        return 2

    # A section's identity is (page, index). Titles are NOT unique —
    # interactions-flow.md has five `#### Core Properties` under five different
    # ancestors — and keying on the title collapses them onto the last one's
    # class, which is exactly how the first audit of the inherited guard produced
    # a page of phantom findings (§13).
    usable: dict[tuple[str, int], tuple[str, str]] = {}
    for b in r.bound:
        usable[(b.page, b.index)] = (b.fqcn, 'direct')
    for i in r.inherited_accepted:
        usable[(i.page, i.index)] = (i.fqcn, 'inherited')

    tables = tables_bound = rows = all_rows = 0
    spellings = collections.Counter()
    pages_with_tables: set[str] = set()
    by_binding = collections.Counter()
    rows_by_binding = collections.Counter()
    bucket = collections.Counter()
    unresolved = collections.Counter()
    noncell = collections.Counter()
    origins = collections.Counter()
    truncated: list = []
    findings: list[tuple[str, str, str, str, str, str]] = []
    probes: dict[str, dict[str, dp.Default]] = {}

    for page in sorted(docs.glob('*.md')):
        for idx, title, _pkg, _lvl, body in sb._sections(page.read_text(errors='replace')):
            here = usable.get((page.name, idx))
            for ki, di, _hdr, table_rows in default_tables(body):
                tables += 1
                spellings[_hdr[di]] += 1
                pages_with_tables.add(page.name)
                # ROWS IN UNBOUND TABLES ARE COUNTED TOO. Reporting only the rows
                # the gate can reach makes a green line read as corpus coverage —
                # the exact misreading the snippet gate's "all 5 complete
                # snippet(s) compile" produced for a year. The table denominator
                # narrowed and said so; the ROW denominator stopped at the
                # boundary, so a reader saw 161/84 and could not tell that over
                # half of the corpus's Default rows are outside the check.
                # Raised by review, and it is the third passing-path defect in
                # this gate: not a dropped row, a row that never enters.
                all_rows += len(table_rows)
                if here is None:
                    continue
                fqcn, how = here
                tables_bound += 1
                by_binding[how] += 1
                rows_by_binding[how] += len(table_rows)
                if fqcn not in probes:
                    try:
                        probes[fqcn] = dp.probe(fqcn, src, truncations=truncated)
                    except dp.ProbeFloor:
                        # An empty dict here would report every row as "key is on
                        # no chain", which is a wrong reason rather than a missing
                        # one — and a wrong reason is worse, because it is
                        # actionable and points nowhere.
                        probes[fqcn] = {}
                keys = probes[fqcn]
                for row in table_rows:
                    rows += 1
                    # EVERY row is counted before any filter runs. A filter whose
                    # output is never counted is an unaudited skip list — the
                    # shape that reduced check-symbols.py's 2811 hits to 750
                    # through eight unreported filters, one of which alone ate
                    # 283. These two drop few rows and that is not the point.
                    cells = [c.strip() for c in row.strip().strip('|').split('|')]
                    if max(ki, di) >= len(cells):
                        bucket['row states no key'] += 1
                        noncell['row has fewer cells than the header'] += 1
                        continue
                    key = cells[ki].strip().strip('*`')
                    if not key or not key.replace('_', 'a').isalnum():
                        bucket['row states no key'] += 1
                        noncell['key cell is not a plain identifier'] += 1
                        continue
                    documented = dp.doc_value(cells[di])
                    if documented is None:
                        bucket['cell states no literal'] += 1
                        continue
                    d = keys.get(key)
                    if d is None:
                        bucket['unresolved'] += 1
                        unresolved['the class has no readable chain' if not keys
                                   else 'key is on no chain in the ancestry'] += 1
                        continue
                    if d.value is None:
                        bucket['unresolved'] += 1
                        unresolved[d.reason or 'no reason recorded'] += 1
                        continue
                    origins[d.origin] += 1
                    if dp.agrees(documented, d.value):
                        bucket['agree'] += 1
                        if a.verbose:
                            print(f'  ok    {page.name}::{title} {key} = {d.value}')
                    else:
                        bucket['disagree'] += 1
                        findings.append((page.name, title, key, documented,
                                         d.value, f'{d.declared_on}.{d.field}'))

    # Zero-floors. "0 findings over 0 rows" is the sentence this gate family has
    # produced seven times, every one in the guard added most recently.
    if tables == 0 or rows == 0 or not usable:
        print(f'  SKIP  nothing to check: {tables} Default-column table(s), '
              f'{rows} row(s), {len(usable)} bound section(s) — an oracle is '
              f'missing, not clean')
        return 2

    checked = bucket['agree'] + bucket['disagree']
    bucketed = sum(bucket.values())
    if bucketed != rows:
        print(f'  FAIL  tally does not reconcile: {rows} row(s) seen but '
              f'{bucketed} bucketed — one pass, one source of truth')
        return 1
    if sum(unresolved.values()) != bucket['unresolved'] or \
            sum(noncell.values()) != bucket['row states no key']:
        print('  FAIL  a reason breakdown does not sum to its bucket — a figure '
              'summed over causes cannot show one cause reaching zero')
        return 1

    print(f'  INFO  {tables} Default-column key table(s) on {len(pages_with_tables)} page(s); '
          f'{tables_bound} in a bound section '
          f'({by_binding["direct"]} direct, {by_binding["inherited"]} inherited-accepted)')
    # The composition of the population, printed rather than described, so that
    # widening the predicate cannot leave a stale figure behind. Only the
    # non-plain spellings, because listing `Default x61` every run is noise and a
    # line nobody reads is the same as no line.
    for spelling, n in sorted(spellings.items()):
        if spelling.strip().lower() != 'default':
            print(f'  INFO    header spelling other than a plain "Default": '
                  f'{spelling!r} x{n}')
    print(f'  INFO  {all_rows} row(s) in those tables; {rows} in a bound section '
          f'({rows_by_binding["direct"]} direct, '
          f'{rows_by_binding["inherited"]} inherited-accepted), '
          f'{all_rows - rows} outside the check')
    print(f'  INFO  of those {rows}: {checked} comparable '
          f'({bucket["agree"]} agree, {bucket["disagree"]} disagree), '
          f'{bucket["cell states no literal"]} state no literal, '
          f'{bucket["unresolved"]} unresolved, '
          f'{bucket["row states no key"]} state no key')
    # WHAT THE COMPARABLE ROWS ACTUALLY COMPARE. Roughly half are "the doc states
    # the type's zero and the field has no initialiser", which is a real comparison
    # — a doc claiming `5` for an uninitialised int fails — but it is weaker
    # evidence than a written initialiser matched exactly, and a reader deciding
    # how much the zero is worth should not have to derive the split. Raised by
    # review. The predicate is the DEFAULT'S ORIGIN, not the documented value:
    # counting `true`/`false` cells instead gives a different number for a
    # different question.
    print(f'  INFO  of those {checked} comparable: '
          f'{origins["initialiser"]} match a written initialiser, '
          f'{origins["java-zero"]} match the type\'s implicit zero')
    # A WALK THAT STOPPED SHORT IS REPORTED, even though no finding depends on
    # one. `0 state no key` is a true count, and over a silently narrowed key set
    # it reads as "every documented key was found" when part of what it means is
    # "we never looked past hop 1" — eleven bound classes were in that state, two
    # inside the 13 direct-bound tables, and no figure said so.
    trunc = collections.Counter(f'{t.parent} ({t.reason})' for t in truncated)
    for what, n in sorted(trunc.items(), key=lambda kv: -kv[1]):
        print(f'  INFO    ancestry truncated: {what} x{n}')
    for reason, n in sorted(unresolved.items(), key=lambda kv: -kv[1]):
        print(f'  INFO    unresolved: {reason} x{n}')
    for reason, n in sorted(noncell.items(), key=lambda kv: -kv[1]):
        print(f'  INFO    no key: {reason} x{n}')

    for page, title, key, documented, actual, field in findings:
        print(f'  FAIL  {page} § {title}: `{key}` is documented as `{documented}` '
              f'but {field} initialises to `{actual}`')
    if findings:
        print('        Suspect the docs OR this checker, in that order only after '
              'reading the field: the first prototype of this comparison reported '
              '14 disagreements and every one was its own normaliser.')
        return 1
    print(f'  PASS  all {checked} comparable Default cell(s) match the field they name')
    return 0


if __name__ == '__main__':
    sys.exit(main())
