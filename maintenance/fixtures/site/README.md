# `site/` — fixtures for the docs site's gates

Read by `maintenance/scripts/check-site-fixture.py`, which runs three verify-docs sections ("The sidebar is
generated from README.md", "Docs markdown renders the same on GitHub and on the site", "The site builds with no
unexplained warning") and `check-site-links.py` against the planted corpora here. Nothing in this directory is
a docs page: the corpora are small on purpose, and every defect is planted by the case that tests it, on top of
a base that is clean, so a red case is red for the one defect it names.

`md-base/` is the clean docs corpus of the markdown lint: one page holding a heading with a generic in a code
span (the form the lint wants) and a list, so the lint's denominators are never 0 on a healthy run.

`nav-base/` is a three-page README (two categories, one page each but one) beside a `docs/` and a committed
`zensical.toml` whose `nav` is the generator's output for it. Its README also holds an `## Examples` section that
lists `docs/a.md` again: a generator that reads past the Documentation section sees a page twice and refuses, so
that mutation is a red case. `site-base/` is the tree the site-build section copies: a `zensical.toml` with a
`site_url`, two docs pages (one links `../CLAUDE.md`, the link whose warning is the one explained warning), the
files the built pages' GitHub links name, and `maintenance/site/`. There are no HTML or log corpora on disk: the
fixture writes a built site (79 pages) and the zensical logs it needs, because a defect is one edited line of
them and the case that plants it should say which.

The extension's own cases are not here but in `maintenance/site/check-extension.py`, which needs the site venv
(`markdown` and `pymdownx`); the fixture runs it with `$HANDBOOK_SITE_PY`, on the real extension and on a copy
with one line of `handbook_md.py` changed per mutation. With no venv that part is skipped and the `FIXTURE` line
says how many cases and mutations it did not run, so a machine without the venv can tell a short run from a full one.
