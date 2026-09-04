# maintenance/

Maintainer-only tooling and data for keeping this repository accurate. **None of
this is needed to use the docs or build the examples** — if you're here to learn
plugin development, you can ignore this directory.

## Contents

- **[scripts/](./scripts/)** — `update-build.sh`, the one-command mechanical
  half of a game-update pass (snapshots the old API index, rebuilds both caches,
  reports asset + API drift with triage greps, runs the checker, prints the
  remaining judgment checklist); `verify-docs.sh`, the regression checker that
  validates `docs/` and `examples/` against the installed Hytale build;
  `build-jar-cache.sh`, which builds the greppable jar cache;
  `hash-server-assets.sh`, which generates the `Server/`+`Cosmetics/` hash
  index (Hytale ships one for `Common/` only); and `check-for-update.sh`, a
  headless installed-version vs docs-stamp comparison for a scheduler (exit 10
  + desktop notification + `~/.cache/hytale-update-pending` marker on
  divergence — the maintainer runs it from a weekly systemd user timer). See
  [CLAUDE.md](../CLAUDE.md#verifying-documentation).
- **[registry-oracle-notes.md](./registry-oracle-notes.md)** — constraints the queued
  registration/type-value oracle (gate 1) has to satisfy, with the evidence for each: the
  two registration forms and the 28% under-count from mining only the first, registries
  that are not statically enumerable and therefore need an "open — not checkable" verdict,
  and the parsing traps that produce confident wrong answers rather than errors.
- **[baseline/](./baseline/)** — a snapshot of the game build the docs were
  fact-checked against, used to detect which assets changed after an update. See
  [baseline/README.md](./baseline/README.md).
