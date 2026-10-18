# `links/` — fixture for `check-links.py`

    python3 maintenance/scripts/check-links-fixture.py [-v]
    python3 maintenance/scripts/check-links-fixture.py --mutations

Both run by `verify-docs.sh` on every invocation, as the sixth gate fixture.

## What it exists to protect

**The corpus narrowing back to `docs/*.md`.** That is the regression the link
gate's widening exists to prevent, and no total-link floor can see it: 1,883 of
the repo's 1,984 links are under `docs/`, so re-narrowing the glob sails over any
plausible total floor and reports green having re-acquired the bug. The
`outside docs/` population is floored on its own, and one mutation asserts that
the floor fires.

That is invariant 6 one turn further than usual. It is not enough to print a
denominator: **a denominator summed over two populations cannot show one of them
reaching zero**, and the population that carries the gate's whole purpose was 5%
of the number it printed.

## And the floor's own population excluded its own test data — eventually

The first version of the split floored a population that **included this fixture
corpus**: 5 of the repo's 106 "outside" links come from
`maintenance/fixtures/links/**`, against a floor of 1. Rebuilt as the real
regression — a top-rooted corpus reaching no further than `docs/`, with the
fixture directory surviving as it would in any real regression — the outside
population fell 106 → 5, a 95% collapse of exactly what the floor measures, and
the gate passed green. **The scaffolding alone cleared the floor.**

Fixture links are now their own bucket: checked for correctness, excluded from the
number that makes a claim about repo content. Exclusion rather than a bigger
floor, because a calibrated value rots every time an `examples/` README is added —
the argument this repo already settled twice for page sizes.

**Mechanism and calibration are different things, and only one of them was
tested.** The `if pop['outside'] < a.min_outside:` → `if False:` mutation proves
the floor *fires*. Nothing proved the number it fires on was adequate for the
population production sees, because every case ran with `--min-links 3` on a
nine-link corpus and took the default outside floor — calibration meaningless in
both directions, by design. The gap between the two is where the whole finding
lived. `_production_on_narrowed()` closes it: the **production invocation with
production defaults**, over a corpus whose only non-`docs/` markdown is this
repo's real fixture tree. Its `docs/bulk.md` exists so the corpus clears the
production `--min-links` of 100 — without it the *total* floor fires first and
the case passes while asserting nothing about the outside floor, which is the
same trap as `--root docs/` one level along.

## Two corpus subtleties that each cost a red case

**`--root docs/` does not simulate the narrowing.** `inside` is computed relative
to the root, so with the root at `docs/` every file's first path part is its own
filename and the entire corpus reads as *outside*. The run passes and the case
asserts nothing. The regression is a **top-rooted corpus that reaches no further
than `docs/`**, so `_docs_only()` builds exactly that — a copy with `examples/`
removed.

**A case must add files, never overwrite them.** Replacing `docs/alpha.md` to
plant one broken link removed three of the corpus's five, tripping the *total*
floor; the run SKIPped and every "is caught" case saw an empty finding list and
went green for the wrong reason. A fixture that starves its own corpus reports
"no findings" because it looked at nothing. For the same reason the fixture's
`--min-links` sits **below** the corpus size: a floor set at the corpus size
masks whichever floor the mutation was aimed at.

## The one case that needs both properties

`examples/sub/readme.md` sits outside `docs/` **and** reaches into it by a
relative path. Both are required, because either narrowing alone hides its link —
the old gate globbed `docs/*.md` (so the file was never read) *and* used a link
pattern that could not express a path (so the link would not have matched even if
it had been). Two mutations, `the corpus narrows back to docs/` and `the link
pattern loses its path segment`, produce the **identical** red set for that
reason. That is a finding rather than a flaw in the fixture: from the outside the
two defects are indistinguishable, which is why fixing either one alone would
have caught nothing.

## The slug is GitHub's, and the tables are what it was fitted to

`gh-heading-ids.tsv` holds every `docs/` heading at d361e13 that has a `<` in it (51), with the anchor id
GitHub's own file renderer gave it (`gh api -H 'Accept: application/vnd.github.html'
repos/inkthorne/hytale-modding-handbook/contents/docs/X.md?ref=d361e13...`, the `user-content-` anchor after
each heading, read 2026-10-18). `gh-heading-shapes.tsv` holds 42 heading shapes and the text GitHub renders
for them (`gh api -X POST markdown -f mode=gfm -f text='## <heading>'`, tags dropped, entities decoded).
Both are measured data and neither is regenerated by anything: a regenerated table certifies itself.

What they showed: GitHub drops what CommonMark calls inline raw HTML and keeps the rest, so `<KeyType>`, `<T>`
and `<T extends Transaction>` vanish from the id and `<K, T>`, `<Arg, D>` and `<ECS_TYPE>` stay as text. A
`</?name[^>]*>` regex is wrong on `<K, T>`; the tag grammar in `check-links.py` (`RAW_HTML`) is CommonMark's and
agrees with all 93 rows. The character rule alone (`char_slug`) misses 18 of the 51 ids, which is the
fixture's negative control: the gate the tag rule replaced passed `asset-editor.md:58` and `player.md:265`,
both broken on GitHub.

Links to anything but a `.md` page are checked for existence too (eight `../examples/` links and the README's
directory links were not read before). The fixture's non-.md cases add files to the corpus and never rely on
its own three pages, for the reason above: a case that starves the corpus reports no findings.
