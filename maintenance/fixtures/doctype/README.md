# doctype provenance-exclusion fixtures

Regression suite for the `**Package:**` provenance exclusion in the doc-type
consistency check (`verify-docs.sh`, `[ADVISORY] Doc-type tags are present and
consistent`). Every fixture here defeated some version of that rule; each is kept
so a future edit cannot silently reopen the hole.

**A check you wrote is not trustworthy until it has been run against an input you
know it must flag.** These are those inputs.

To run: extract the check's python block and point it at this directory.

    python3 - <<'PY'
    import pathlib
    t=pathlib.Path("maintenance/scripts/verify-docs.sh").read_text()
    i=t.index('section "[ADVISORY] Doc-type tags are present')
    b=t[i:]; s=b.index("<<'PY'\n")+7; e=b.index("\nPY\n", s)
    pathlib.Path("/tmp/doctype.py").write_text(b[s:e])
    PY
    mkdir -p /tmp/fx/docs /tmp/fx/maintenance/scripts
    cp maintenance/fixtures/doctype/*.md /tmp/fx/docs/
    rm /tmp/fx/docs/README.md
    : > /tmp/fx/maintenance/scripts/doctype-skiplist.txt
    (cd /tmp/fx && python3 /tmp/doctype.py)

| Fixture | Shape | Required outcome |
|---|---|---|
| `a-json-provenance.md` | Package line above a Property table / json fence | **excluded** (the whole point of the rule) |
| `b-java-surface.md` | Package line above a ```java fence | MISMATCH |
| `c-leaks-outside.md` | Package provenance, same class also named in prose | MISMATCH — every occurrence must be a citation |
| `fixture-d.md` | Java surface in a *different* section, written with simple names | MISMATCH — page-level backstop |
| `fixture-e.md` | Bare signature fence in one of two cited sections | that section's class must NOT be excluded (the page itself falls under the >=2 threshold) |
| `fixture-e2.md` | Bare signature fence in *both* cited sections | MISMATCH |
| `fixture-f.md` | `\| Field \|` table documenting a Java field | MISMATCH — `Field` is not positive JSON evidence |
| `fixture-g.md` | `\| Signature \|` table beside a Property table | MISMATCH |
| `fixture-h.md` | `\| Methods \|` — the plural escaping a singular-anchored pattern | MISMATCH |
| `fixture-i.md` | ` ```Java ` — an uppercase fence tag, exercising a *third* class by simple name | MISMATCH |
| `fixture-j.md` | bare ASCII diagram containing a line starting with `## `, in a separate section | **must NOT flag** — this is the real-corpus shape |

Expected on the whole set: MISMATCH for b, c, d, e2, f, g, h, i; no MISMATCH for
a, e or j; `DENOM` reporting a non-zero provenance count and `FELL` naming a, e
and j.

`fixture-j.md` is deliberately a negative test. A suite of only-positives cannot
catch a rule that has become *too strict*, and j is the shape both live excluded
pages actually have — one bare architecture diagram, cited sections otherwise
clean JSON. If j ever starts flagging, the rule has regressed toward the false
positives this change exists to remove.

## Why the FELL counter exists

The D backstop is a **blacklist of Java-surface signals** — ```java fences,
`| Method` tables — and H and I were simply two entries missing from it. "How
someone might write Java on a page" is open-ended, so that list can never be
closed by enumeration. What *can* be closed is the visibility gap: a page whose
exclusions drop it from candidate to non-candidate used to be indistinguishable
from a page that never had two FQCNs. `FELL` reports that transition by name, so
every escape of D's, H's or I's shape is a number someone can look at whether or
not the blacklist ever learns its cause. It would have surfaced all three
without any of the six fixes.

## The FELL pages are brittle, and the tempting fix is the wrong one

A page named by `FELL` sits at exactly the threshold with all of its FQCNs
excluded, so it passes *only* because provenance exclusion fires. Both current
entries are in that state:

| Page | FQCNs | Tag |
|---|---|---|
| `items-blocks.md` | `FarmingUtil`, `HarvestCropInteraction` | `JSON asset format` |
| `items-weapons.md` | `UseEntityInteraction`, `DurabilityConditionInteraction` | `JSON asset format` |

Adding **any** ```java fence or `| Method` / `| Methods` / `| Signature` table
anywhere on such a page trips the D backstop, restores both citations, and the
page warns. Measured, not reasoned: appending a four-line `| Method | Returns |`
table to a copy of `items-weapons.md` turns `FELL items-weapons.md` into
`MISMATCH items-weapons.md`.

That is the rule working. A page with real Java surface is not a JSON page with
citations, and the correct response is to **retag it** `Java API + JSON asset
format` — not to add a skip-list entry. The skip list is the residual for
citations the rule cannot classify; a method table is not that. The failure will
arrive as a WARN naming the page, and the entry is the tempting wrong fix.

Corollary for new subsystem pages: a page carrying genuine Java API (components,
method tables, fences) should be tagged `Java API + …` from the start, which
short-circuits the check before provenance is ever consulted. Do not land a
Java-heavy subsystem on an existing JSON-tagged page.
