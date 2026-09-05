# Bound

### Widget

**Package:** `binderpkg`

A section that binds: the heading names a class, the Package line resolves it, and
the class declares a codec chain.

### Gadget

**Package:** `binderpkg`

A second bound section, so the bound count is not 1 (a count of 1 cannot
distinguish "bound" from "bound the only thing there was").

### Learning Widgets

**Package:** `binderpkg.Gadget`

The Package line is a **fully-qualified class name**, not a package — 28 real
sections are written this way and every one of them resolves. The heading is
deliberately hostile: its first CamelCase token is `Learning`, so binding on the
heading gives `binderpkg.Gadget.Learning` and fails. When the Package value's last
segment is CamelCase, it *is* the class, and the heading heuristic must not run.

### Nested

**Package:** `sub/Nested`

A **path-style** Package value, relative to a root the caller supplies. Forty real
sections on the four `interactions-*` pages are written this way
(`config/server/SpawnPrefabInteraction` and the like, relative to
`…modules.interaction.interaction`), and all forty resolve. They are also the
JSON-heaviest pages in the corpus, which is why this rule exists.
