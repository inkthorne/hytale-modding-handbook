# Digest instructions

You are writing the digest for one tag: a map of what this store knows
about the topic, read by an agent before it reads the raw entries. It
is a map, not the record — every line points back at entries.

- **First line:** one sentence saying what the topic is and where it
  stands now. This line is shown in `remember digest list`. Describe,
  do not judge: never call the entries unrelated, scratch, or random —
  the reader decides what matters, and a later question may hinge on
  any one of them.
- **## Current state** — the facts that hold now, one line each, exact
  strings kept verbatim (hosts, tickets, versions, numbers, names), each
  line ending with the entry ids it rests on: `[e12]` or `[e12 e40]`.
- **## Open loops** — unresolved questions and pending work, with ids.
- **## Disagreements** — only for a tag under `policy=evidence`: each
  point where entries conflict, both sides with their sources and ids.
  Do not pick a winner.
- Superseded facts do not appear: a newer entry replaces an older one on
  the same subject, except under evidence policy.
- Fold the current digest forward rather than rewriting it from scratch:
  keep what still holds, replace what changed, add what is new. Cover
  every entry newer than the current digest.
- Stay under about 8,000 characters. If the packet is too large to hold
  at once, digest the newest entries and store with
  `--through <last id covered>`; the rest can be folded in later.
- Store it with `remember digest put <tag>` (text on stdin, or `-f FILE`).
