# `site/` — fixtures for the docs site's gates

Read by `maintenance/scripts/check-site-fixture.py`, which runs three verify-docs sections ("The sidebar is
generated from README.md", "Docs markdown renders the same on GitHub and on the site", "The site builds with no
unexplained warning") and `check-site-links.py` against the planted corpora here. Nothing in this directory is
a docs page: the corpora are small on purpose, and every defect is planted by the case that tests it, on top of
a base that is clean, so a red case is red for the one defect it names.

`md-base/` is the clean docs corpus of the markdown lint: one page holding a heading with a generic in a code
span (the form the lint wants) and a list, so the lint's denominators are never 0 on a healthy run.
