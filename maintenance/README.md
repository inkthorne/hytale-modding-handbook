# maintenance/

Maintainer-only tooling and data for keeping this repository accurate. **None of
this is needed to use the docs or build the examples** — if you're here to learn
plugin development, you can ignore this directory.

## Contents

- **[scripts/](./scripts/)** — `verify-docs.sh`, the regression checker that
  validates `docs/` and `examples/` against the installed Hytale build (run it
  after a game update). See [CLAUDE.md](../CLAUDE.md#verifying-documentation).
- **[baseline/](./baseline/)** — a snapshot of the game build the docs were
  fact-checked against, used to detect which assets changed after an update. See
  [baseline/README.md](./baseline/README.md).
