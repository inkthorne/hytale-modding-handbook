#!/usr/bin/env python3
"""
check-sigblocks.py — REVIEW-ONLY. Not a gate, not wired into verify-docs.sh, no
fixture. Run it by hand; read the buckets before you read the findings.

WHAT IT IS. `check-symbols.py` only binds members written as `Receiver.member`, so
a fence of bare signatures under a `### ClassName` heading is verified by nothing:

    ### Chunk Access
    ```java
    Ref<ChunkStore> getChunkRef()        // no receiver token anywhere
    ```

This binds such a fence to a class its heading names and reports signatures whose
method name is absent from that class, walking superclasses via check-symbols.py's
own index so both agree on what "exists".

WHY IT IS NOT A GATE, AND THIS IS THE POINT OF LANDING IT. CLAUDE.md's queued
item 2 said a prototype "found 19 verified-dead signatures". That is true history
and false as a claim about the corpus: **all 19 were fixed on 2026-09-03** during
the 0.6.3 pass, routed to the owning agents ("all 19 previously verified-dead
signatures cleared, with zero true positives remaining"). The figure motivating
the gate named defects that no longer exist, and nobody had re-derived it.

Re-derived 2026-09-05, and it does not support building a gate yet:

    546 java fence(s) containing signatures; 2653 signature(s)
    130 fence(s) bind to no heading class      (513 signatures unchecked)
    2140 bound: 2024 resolve, 116 flagged      (5.4%)
    0 live defects found among the 116

FOUR FALSE-POSITIVE CLASSES account for what was read, and none of the 116 has yet
been confirmed as a real dead signature:

  * CONSTRUCTORS (20). `members_of` discards `<init>`, so every
    `public FileCommonAsset(Path, String, byte[])` is flagged. Trivial to fix.
  * EXAMPLE CODE WITH BODIES (12 by the script's own count). `assets.md`'s walkthrough defines the reader's
    own class; the fence-binding rule accepted it because a DIFFERENT line in the
    same fence resolved.
  * FIRST CANDIDATE, NOT BEST. `bind_fence` takes the first heading token with any
    resolving member rather than the one with the most, so `worldgen.md:473` binds
    `World.getRotationIndex()` under a `### GeneratedChunk and its buffers`
    heading.
  * NESTED TYPES. `codecs.md:232`'s `FieldBuilder addValidator(...)` is bound to
    the enclosing `BuilderCodec`.

Top bound classes — World 20, PrefabBuffer 16, Position 12, Asset 11, Velocity 11
— read like heading-binding noise rather than rot.

THE HEADING RULE IS CLAUDE.md's AND IT IS LOAD-BEARING: trust a heading only when
at least one signature under it resolves there. Without it the same corpus flags
**588** instead of 116, because `### Section Loading Rates` binds to the jar class
`Section` and `## World Paths` to `World`. A reconstruction that omits it looks
like a working instrument and is not.

PROVENANCE. This is a RECONSTRUCTION, not the original. The 2026-09-03 prototype
is not in the repo; its source was recovered from the session transcript via
`recall` (id 291094) and the tail was truncated, so the reporting half is rewritten
and the filters below may differ from the ones that produced 19. Treat the 116 as
this script's figure, not as the prototype's.

Usage: python3 maintenance/scripts/check-sigblocks.py <HytaleServer.jar> [docs_glob]
"""

import re, sys, os, glob, io, importlib.util, contextlib, collections

JAR = sys.argv[1]
DOCS = sys.argv[2] if len(sys.argv) > 2 else "docs/*.md"
CHECKER = os.path.join(os.getcwd(), "maintenance/scripts/check-symbols.py")
spec = importlib.util.spec_from_file_location("cs", CHECKER)
cs = importlib.util.module_from_spec(spec)
_argv = sys.argv; sys.argv = ["check-symbols.py", JAR]
try:
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(cs)
finally:
    sys.argv = _argv

heading_re = re.compile(r"^(#{2,4})\s+(.*?)\s*$")
fence_re   = re.compile(r"^```([a-zA-Z]*)\s*$")
ident_re   = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")
MODS = r"(?:public|protected|private|static|final|abstract|default|synchronized|native)\s+"
sig_re = re.compile(r"^\s*(?:" + MODS + r")*(?:<[^>]+>\s+)?"
                    r"([A-Za-z_][\w.$]*(?:\s*<[^;{}]*>)?(?:\s*\[\s*\])*)"
                    r"\s+([a-zA-Z_]\w*)\s*\(")

def is_sig_line(line):
    s = line.split("//")[0].rstrip()
    if not s or "=" in s.split("(")[0]: return False
    if s.endswith("{") or s.lstrip().startswith(("@","*","/","}","return ","new ","if ","for ","while ","throw ")):
        return False
    if "." in s.split("(")[0]: return False
    m = sig_re.match(s)
    if not m: return False
    rtype, name = m.group(1), m.group(2)
    if rtype in ("return","new","if","for","while","else","throw","case","assert"): return False
    return name

def candidates(stack):
    """Every heading token that names exactly one jar class, deepest first."""
    out = []
    for _lvl, text in reversed(stack):
        for tok in ident_re.findall(text):
            if tok in cs.JDK_SKIP: continue
            c = cs.resolve_class(tok)
            if len(c) == 1: out.append((tok, next(iter(c))))
    return out


def bind_fence(stack, names):
    """CLAUDE.md's rule: trust a heading only when AT LEAST ONE signature under it
    resolves there. Without it a `### Section Loading Rates` heading binds to the
    jar class `Section` and flags every line under it."""
    for tok, internal in candidates(stack):
        if any(n in cs.members_of(internal) for n in names):
            return tok, internal
    return None, None

tally = collections.Counter(); dead = []; rows = []
for f in sorted(glob.glob(DOCS)):
    bn = os.path.basename(f); stack = []; lang = None; ln = 0
    fence = []                     # (lineno, name, raw) for the open fence
    for line in open(f, errors="replace"):
        ln += 1
        fm = fence_re.match(line)
        if fm:
            if lang is None:
                lang = fm.group(1) or ""; fence = []
            else:
                if lang == "java" and fence:
                    tally["java fence(s) with signatures"] += 1
                    names = [n for _, n, _ in fence]
                    tally["signatures"] += len(names)
                    tok, internal = bind_fence(stack, names)
                    if internal is None:
                        tally["fence binds to no heading class"] += 1
                        tally["signatures in unbound fences"] += len(names)
                    else:
                        tally["bound"] += len(names)
                        ms = cs.members_of(internal)
                        for l2, n2, raw in fence:
                            if n2 in ms: tally["resolves"] += 1
                            else:
                                tally["DEAD"] += 1
                                dead.append(f"{bn}:{l2}  {tok}.{n2}()  | {raw[:70]}")
                                rows.append((bn, tok, n2, raw))
                lang = None
            continue
        if lang is None:
            hm = heading_re.match(line)
            if hm:
                lvl = len(hm.group(1))
                while stack and stack[-1][0] >= lvl: stack.pop()
                stack.append((lvl, hm.group(2)))
            continue
        if lang != "java": continue
        name = is_sig_line(line)
        if name: fence.append((ln, name, line.strip()))
# Denominators first, findings second — invariant 6, and here the denominators
# are the whole story: 116 of 2140 is a 5.4% flag rate with four known
# false-positive classes and no confirmed defect.
print(f'  INFO  {tally["java fence(s) with signatures"]} java fence(s) with signatures; '
      f'{tally["signatures"]} signature(s)')
print(f'  INFO  {tally["fence binds to no heading class"]} fence(s) bind to no heading '
      f'class ({tally["signatures in unbound fences"]} signature(s) unchecked)')
print(f'  INFO  {tally["bound"]} bound: {tally["resolves"]} resolve, {tally["DEAD"]} flagged')

# The false-positive classes, counted rather than described, so the next person
# sees how much of the list is instrument before reading any of it.
ctor = sum(1 for _, c, n, _ in rows if c == n)
body_lines = sum(1 for _, _, _, raw in rows if raw.rstrip().endswith('}'))
print(f'  INFO  known false-positive classes among the {len(rows)} flagged: '
      f'{ctor} constructor(s), {body_lines} line(s) with a method body (example code); '
      f'the rest are first-candidate-not-best receivers and nested types')
by_cls = collections.Counter(c for _, c, _, _ in rows)
print(f'  INFO  top bound classes: '
      + ', '.join(f'{c} {n}' for c, n in by_cls.most_common(5)))
for d in dead:
    print("  FLAG ", d)
