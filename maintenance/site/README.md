# `maintenance/site/` — the docs site

The site (https://inkthorne.github.io/hytale-modding-handbook/) is Zensical's build of `docs/`, deployed by
`.github/workflows/pages.yml`. Everything it needs beyond `docs/` and `zensical.toml` is here.

| file | what |
|---|---|
| `requirements.in` / `requirements.txt` | the pin (zensical 0.0.71) and its hashed lock, Python 3.12 |
| `handbook_md.py` | the Python-Markdown extension: links out of `docs/` to GitHub at the built ref, GitHub's `-N` duplicate anchors, GitHub's heading slug, lists after a paragraph line, separate adjacent blockquotes, CommonMark inline HTML and escapes |
| `overrides/main.html` | the head tags Jekyll's seo-tag emitted: google-site-verification, og:*, twitter:*, JSON-LD |
| `check-extension.py` | cases for the extension, run with the site venv's python; `check-site-fixture.py` runs it and mutates the extension |

The sidebar is generated from the README (`maintenance/scripts/generate-site-nav.py`). The site is built and its
warnings judged by `check-site-build.py`, and its links checked by `check-site-links.py`; `verify-docs.sh` runs both.

## Building it

    maintenance/scripts/site-env.sh                      # creates ~/.cache/handbook-site/venv from the hashed lock
    export HANDBOOK_SITE_PY=~/.cache/handbook-site/venv/bin/python
    cd "$(mktemp -d)" && cp -r REPO/zensical.toml REPO/docs . && mkdir -p maintenance && cp -r REPO/maintenance/site maintenance/ \
        && mkdir maintenance/scripts && cp REPO/maintenance/scripts/{check-links,doc_fences}.py maintenance/scripts/
    PYTHONPATH=maintenance/site HANDBOOK_REF=main $HANDBOOK_SITE_PY -m zensical build --clean

zensical writes `.cache/` beside its config and its cache once served a stale `HANDBOOK_REF`, and its `site_dir` and
`docs_dir` must lie inside the config's directory, so every build is in a copy and passes `--clean`. The extension
resolves its paths from `__file__`, so the copy keeps the layout.

## Bumping zensical

A version bump is its own item. The link rewrite and the duplicate-anchor numbering in `handbook_md.py` ride on
the Python-Markdown path that upstream says it is moving to Rust (`zensical/markdown/render.py`), so a bump can
remove them without a warning. Re-run, in this order: `check-extension.py`; a build of the new HEAD and the
parity comparison against GitHub's own rendering (li, ol, ul, table, tr, pre, blockquote and h2-h4 counts, the
text of every page, the heading ids); the cross-check of every anchor check-links computes against the built ids;
`check-site-links.py`; and the negative control of the first item (a build with no extension and no heading
fixes must fail exactly the 9 links and the anchors it did).

## Accepted differences from GitHub (measured, and left)

The site is meant to show what GitHub shows. These differences were found by comparing built pages with GitHub's own
rendering and are accepted, because a reader cannot tell them apart or they cost more to remove than they are worth.
A difference not listed here is a defect.

- A code span that starts or ends with a space loses it on the site (Python-Markdown trims; CommonMark trims one space
  from each side only when both are there): 25 spans. Spaces inside a code span are not visible.
- A code span that holds a line break shows it as a space in one of the two renderers: 19 spans. Same look.
- Typographic quotes and dashes: the Jekyll site printed curly quotes and en/em dashes (kramdown's smartypants);
  GitHub and the new site print the ASCII characters as written.
- The page title separator is ` - ` (`Commands API - Hytale Modding Handbook`), where Jekyll's was ` | `.
- GitHub alerts (`> [!WARNING]`) are plain blockquotes with the literal `[!WARNING]` on the site, as they were on Jekyll.
