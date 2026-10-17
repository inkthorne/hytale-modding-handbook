# Memory

You have `remember`, a persistent memory CLI that works across sessions.
Memory is per-project: this project's store lives at `.remember/` at the
project root, and it is the only store.

- Save any durable fact, decision, preference, or correction the user
  states — even when not asked to. One entry per fact:
  `remember save -t <topic> <the fact, one line>`
- When a fact changes, save the new value as a fresh entry the same way —
  the ledger keeps history; newest wins.
- Before answering anything that could depend on prior sessions, and
  before asking the user anything or calling one of their machines,
  accounts, people or projects by a description ("your router") instead
  of its name, search: `remember search <terms>` (try a couple of 1-3
  word variants, including any address or identifier in front of you).
- Results are newest-first. When a newer entry supersedes an older one
  (a correction saved with `--supersedes`; search hides the old value),
  the newest is the only truth: state it and nothing else. Never
  mention, quote, or compare against a superseded value — reply as if
  only the newest entry exists. Entries that stand together under a
  tag with no supersession between them are all current: report each.
- Also search before doing any task — writing, coding, drafting — not
  just when asked a question: saved preferences and conventions apply
  even when the task doesn't mention them. Before any work product,
  always run both `remember search <task topic>` and, verbatim,
  `remember search style` and `remember search preference` — vocabulary
  rarely matches, so try broad words, not task-specific ones.
- When the user corrects or replaces a fact you saved earlier, look up
  the old entry (`remember search <terms>`) and save the new value with
  `--supersedes <id>`.
- `remember dump` prints everything; `remember tags` lists topics.
