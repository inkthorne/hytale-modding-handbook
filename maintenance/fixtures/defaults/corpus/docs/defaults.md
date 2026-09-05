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

Its Default header is also **not spelled plainly**, which is the second thing this
section is for: `adventure.md` heads one `Default (shipped \`Default.json\`)`, and a
predicate matching an exact `| Default |` cell cannot see it. The gate prints every
non-plain spelling it finds rather than describing the composition in a comment —
that comment said "59 plain headers" for as long as it took a predicate widening to
make it 61.

| Key | Type | Default (as shipped) |
|-----|------|----------------------|
| `x` | int | `4` |

### Loose

No `**Package:**` line, so this section is unbound and its Default table is
**counted but not checked** — the coverage figure the gate must print is exactly
this ratio.

| Key | Type | Default |
|-----|------|---------|
| `Radius` | double | `999.0` |

### Orphaned

**Package:** `defpkg`

Its chain names a parent that exists nowhere in the tree, so the walk stops one hop
in. Nothing here produces a *finding* — the one documented key is on its own chain
— and that is the point: the gate must report the truncated ancestry anyway. A walk
that stops short narrows the key set without narrowing any figure that says so, and
`0 state no key` over a quietly shortened ancestry reads as "every documented key
was found" when part of what it means is "we never looked past hop 1".

| Key | Type | Default |
|-----|------|---------|
| `Own` | int | `5` |
