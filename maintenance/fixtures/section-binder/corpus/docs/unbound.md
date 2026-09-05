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

### Phantom

**Package:** `binderpkg.NoSuchClass`

An **FQCN Package line naming a class that does not exist**. The FQCN path must
still resolve before binding — without that check it binds anything with a dot and
a capital in it.

### Widget

**Package:** `binderpkg.emptysub`

A package **directory that exists but declares no classes**. It must read as
"package does not resolve", not "no source file for the class": with the directory
counted as a package the section falls through to the class lookup instead, and the
two reasons trade members so neither means what its label says.
