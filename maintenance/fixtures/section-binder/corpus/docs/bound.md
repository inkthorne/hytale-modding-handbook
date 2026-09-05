# Bound

### Widget

**Package:** `binderpkg`

A section that binds: the heading names a class, the Package line resolves it, and
the class declares a codec chain.

#### Widget Properties

Inherits Widget's binding and is **accepted**: every top-level key below exists on
`Widget`'s parsed chain.

| Key | Type | Default |
|-----|------|---------|
| `Name` | string | — |
| `Size` | int | `1` |

#### Widget Notes

Prose only — no key table, no JSON fence, so **no fingerprint**. It must NOT be
accepted: an inherited binding with no content to confirm it is binding by
position, which is the thing the guard exists to refuse. Absence of evidence is
not evidence.

#### Widget Discriminated

A fence whose root object carries a **discriminator** — `Kind`, declared by
`new CodecMapCodec("Kind")` in this corpus. A discriminator is not an appended key,
so it appears on no chain, and without an exemption every fence documenting a
discriminated type is rejected on it. In the real tree the discriminators are
`Type` (38 declarations), `component`, `Id` and `type`, mined rather than assumed.

```json
{
  "Kind": "Small",
  "Name": "a",
  "Size": 2
}
```

A one-line fence (`{ "Kind": "Small" }`) yields **no** root keys, because the first
key sits after `{ ` rather than at the start of a line. That is a coverage loss,
not a correctness bug — no keys means no fingerprint means not accepted, which is
the safe direction — but it is why this fence is written out.

#### Widget Examples

Inherits Widget's binding and is **rejected**: `Colour` is a `Gadget` key, not a
`Widget` one, so the fingerprint fails and the binding is refused rather than
accused. This is the misattribution case the guard exists for — a subsection under
one class that is about another.

| Key | Type | Default |
|-----|------|---------|
| `Name` | string | — |
| `Colour` | string | `red` |

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

### SubWidget

**Package:** `binderpkg`

Declares `Extra` and inherits `Name` and `Size` from `Widget.CODEC`.

#### SubWidget Properties

Uses a **parent-chain** key. A fingerprint that stopped at the declared chain would
reject this — the safe direction, but uselessly, since a subsection's table
routinely documents inherited keys.

| Key | Type | Default |
|-----|------|---------|
| `Extra` | int | `0` |
| `Name` | string | — |

### Orphan

No `**Package:**` line, so this section is unbound — and being a **sibling** of the
bound sections above, it must END their scope.

#### Orphan Details

Must be unbound. If a sibling heading did not pop the scope stack, this would
inherit `SubWidget` on the strength of a key it shares.

| Key | Type |
|-----|------|
| `Extra` | int |

### Derived

**Package:** `binderpkg`

Its parent codec field is `ABSTRACT_CODEC`, not `CODEC`.

#### Derived Properties

Uses `Inherited`, which lives on the parent's **non-`CODEC`** field. A walk that
keeps the receiver and drops the field name never finds it.

| Key | Type | Default |
|-----|------|---------|
| `Own` | int | `0` |
| `Inherited` | string | — |
