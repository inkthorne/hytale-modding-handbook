# Defaults

### Widget

**Package:** `defpkg`

The bound section. Every row below is a case; the Description column says which.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Radius` | double | `1.5` | AGREE — a plain setter and a literal initialiser |
| `Ratio` | float | `30.0` | AGREE — `30.0f` in source, `30.0` documented; the `f` suffix is not a difference |
| `Count` | int | `0` | AGREE — no initialiser, so the default is Java's zero for the type |
| `Enabled` | boolean | `false` | AGREE — no initialiser, boolean |
| `Name` | string | — | NOT A LITERAL — an em dash states no default and must not be compared |
| `Mode` | string | `Fast` | AGREE — `Mode.Fast`; the enum constant is compared, not the qualified name |
| `Cased` | string | `"user"` | AGREE — `Target.USER`; the same constant exists as `User` and `USER` in two packages and renders identically to JSON, so case is not a difference |
| `Retries` | int | `3` | AGREE — the key is on the PARENT's chain and the field is on the parent |
| `Shared` | double | `0` | AGREE — the key is on THIS chain, the field is declared on the parent |
| `Label` | string | *inherited from Base* | NOT A LITERAL — italic prose |
| `Grace` | float | `2.0` | UNRESOLVED — the setter assigns two fields, so which one is the default is not decidable |
| `Tag` | string | `t` | UNRESOLVED — the setter is a method reference, not a lambda |
| `Extras` | array | `[]` | UNRESOLVED — the setter calls a method, it does not assign |
| `Boxed` | boolean | `null` | AGREE — a BOXED `Boolean` with no initialiser is `null`, not `false`; only a primitive has a zero |
| `BoxedNum` | int | `null` | AGREE — the same for `Integer`; reading a box as its primitive invents a default of `0` |
| `Quoted` | string | `"Fast"` | AGREE — a cell written as a JSON literal carries quotes that are not part of the value |
| `Missing` | int | `7` | UNRESOLVED — no such key on the chain or any ancestor |
| `Radius.x` | double | `1.5` | NOT A KEY — a dotted path is not a top-level key, and dropping it silently is a filter whose output nothing counts |
| *(any other key)* | — | — | NOT A KEY — a prose cell in the key column, which several real tables use as a catch-all row |
| `Ragged` | double |

#### Wrong Defaults

Inherits `Widget` and is accepted on its keys. Every row here is a **disagreement**
— the positive control. A defaults gate that cannot go red on this table is not a
gate, and on this repo's evidence the case that has never been red is the one that
was never verified.

| Key | Type | Default |
|-----|------|---------|
| `Radius` | double | `2.5` |
| `Count` | int | `1` |
| `Mode` | string | `Slow` |

### Plain

**Package:** `defpkg`

Names a class that declares **no codec chain**, so the binder records it unbound
and its table contributes no rows. It exists so that "tables in a bound section" is
not the same number as "tables scanned" — a coverage figure that cannot differ from
its own denominator is not measuring anything.

| Key | Type | Default |
|-----|------|---------|
| `x` | int | `4` |

### Loose

No `**Package:**` line, so this section is unbound and its Default table is
**counted but not checked** — the coverage figure the gate must print is exactly
this ratio.

| Key | Type | Default |
|-----|------|---------|
| `Radius` | double | `999.0` |
