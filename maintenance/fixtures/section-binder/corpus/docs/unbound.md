# Unbound

Three ways a section fails to bind. Each must be *counted*, not skipped silently —
an unbound section is a section the downstream checks cannot see, so the denominator
is what says how much of the corpus those checks actually cover.

### Sprocket

**Package:** `binderpkg`

Resolves to no source file: `binderpkg.Sprocket` does not exist.

### Doohickey

**Package:** `config`

An abbreviated Package line. Forty of these exist in the real corpus, and they name
no resolvable package at all.

### Thingummy

No `**Package:**` line under this heading, so there is nothing to resolve it with.

### Sprinkler Component

**Package:** `binderpkg`

Resolves to a real file that declares **no codec chain** — the common case, since
most `### ClassName` sections document a component, a system or an event. Also a
**multi-word heading**: the binder must take the first CamelCase token, and with a
single-word heading in every fixture section that behaviour was untested.
