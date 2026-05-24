#!/usr/bin/env python3
"""
check-symbols.py — symbol-resolution check for docs/ against HytaleServer.jar.

Verifies that the API symbols the docs *name* actually resolve in the build:
  * Class names (FQCN or capitalized simple name used in a code context) exist
    as real classes under com.hypixel.hytale.**.
  * Members written in the high-confidence static/qualified form `Receiver.member`
    (where Receiver resolves to a real jar class) appear among that class's
    members, walking superclasses and interfaces so inherited members count.

Receivers that don't resolve to a com.hypixel jar class are skipped — they are
local variables, JDK types, or illustrative example identifiers, and attaching a
member to them would require type inference we deliberately don't attempt.

Output: an advisory findings list grouped by doc page. Pure reporting; exit 0.

Usage: check-symbols.py <HytaleServer.jar>
"""
import re, sys, os, glob, zipfile, struct
from collections import defaultdict

JAR = sys.argv[1]

# ---- jar class index -------------------------------------------------------
# Members are read by parsing the class files directly (constant pool + the
# fields/methods tables), the same technique as the coverage check — far faster
# than spawning javap per class, which matters for a per-build gate.
#
# Classes are keyed by their slashed *internal* name (com/hypixel/.../Foo$Bar).
ZF = zipfile.ZipFile(JAR)
entry_set = set()                       # internal names (no .class) present in jar
simple_map = defaultdict(set)           # simple name -> {internal name, ...}
for n in ZF.namelist():
    if not n.endswith(".class") or not n.startswith("com/hypixel/"):
        continue
    internal = n[:-6]                   # com/hypixel/.../Foo$Bar
    entry_set.add(internal)
    # Key a class by its OWN simple name only (the last $-segment): Foo$Bar -> Bar.
    # Indexing every ancestor segment would make "Foo" resolve to all of Foo's
    # anonymous inners (Foo$1, Foo$2, ...) and inflate ambiguity. Anonymous
    # inners (last segment is numeric) are not addressable by name and skipped.
    own = internal.rsplit("/", 1)[-1].rsplit("$", 1)[-1]
    if own and own[0].isupper():
        simple_map[own].add(internal)

OBJECT_MEMBERS = {"equals", "hashCode", "toString", "getClass", "notify",
                  "notifyAll", "wait", "clone", "finalize"}

def _parse_classfile(internal):
    """(member_names:set, super_internals:[str]) by parsing the class file.

    Reads the constant pool (for Utf8 + Class-ref names), then the super_class,
    interfaces, fields and methods tables — each member's name_index points at a
    Utf8 entry. Returns ([],[]) on any structural surprise (parsed defensively).
    """
    try:
        d = ZF.read(internal + ".class")
    except KeyError:
        return set(), []
    if d[:4] != b"\xca\xfe\xba\xbe":
        return set(), []
    n = struct.unpack_from(">H", d, 8)[0]; off = 10
    utf = {}; cls_ni = {}; i = 1
    while i < n:
        t = d[off]; off += 1
        if t == 1:
            ln = struct.unpack_from(">H", d, off)[0]; off += 2
            utf[i] = d[off:off+ln].decode("utf-8", "replace"); off += ln
        elif t in (3, 4): off += 4
        elif t in (5, 6): off += 8; i += 1
        elif t == 7: cls_ni[i] = struct.unpack_from(">H", d, off)[0]; off += 2
        elif t == 8: off += 2
        elif t in (9, 10, 11, 12): off += 4
        elif t == 15: off += 3
        elif t == 16: off += 2
        elif t in (17, 18): off += 4
        elif t in (19, 20): off += 2
        else: return set(), []
        i += 1
    off += 2                                       # access_flags
    off += 2                                       # this_class
    super_ix = struct.unpack_from(">H", d, off)[0]; off += 2
    supers = []
    if super_ix and super_ix in cls_ni:
        supers.append(utf.get(cls_ni[super_ix], ""))
    ic = struct.unpack_from(">H", d, off)[0]; off += 2
    for _ in range(ic):
        ix = struct.unpack_from(">H", d, off)[0]; off += 2
        if ix in cls_ni:
            supers.append(utf.get(cls_ni[ix], ""))
    members = set()
    for _table in range(2):                        # fields, then methods
        cnt = struct.unpack_from(">H", d, off)[0]; off += 2
        for _ in range(cnt):
            off += 2                               # access_flags
            ni = struct.unpack_from(">H", d, off)[0]; off += 2
            off += 2                               # descriptor_index
            members.add(utf.get(ni, ""))
            ac = struct.unpack_from(">H", d, off)[0]; off += 2
            for _a in range(ac):                   # skip attributes
                off += 2                           # attribute_name_index
                al = struct.unpack_from(">I", d, off)[0]; off += 4
                off += al
    members.discard("<init>"); members.discard("<clinit>")
    return members, [s for s in supers if s]

_member_cache = {}

def members_of(internal, _seen=None):
    """All member names of a class, walking Hytale supers/interfaces. Object
    methods are whitelisted; non-Hytale supers (JDK, fastutil, bson) are not
    walked — the static `Class.member` form we check targets Hytale members."""
    if internal in _member_cache:
        return _member_cache[internal]
    if _seen is None:
        _seen = set()
    if internal in _seen:
        return set()
    _seen.add(internal)
    mem, supers = _parse_classfile(internal)
    acc = set(mem) | OBJECT_MEMBERS
    for sup in supers:
        if sup.startswith("com/hypixel/") and sup in entry_set:
            acc |= members_of(sup, _seen)
    _member_cache[internal] = acc
    return acc

def class_exists_internal(name):
    """True if a name (with '/' for package, possibly '.'-nested) is a jar class."""
    if name in entry_set:
        return True
    if "." in name:                                # Receiver.Nested -> .../$Nested
        head, tail = name.rsplit(".", 1)
        return (head + "$" + tail) in entry_set
    return False

def resolve_class(simple):
    """Return set of internal names a capitalized simple name maps to."""
    return simple_map.get(simple, set())

# ---- harvest documented symbols --------------------------------------------
# Only ```java fenced blocks and inline `...` spans are treated as Java contexts.
# JSON / bash / untagged blocks use dotted paths (BlockType.Components) and file
# names (Foo.json) that collide with class names but are not Java member access.
java_block = re.compile(r"^```java\s*\n(.*?)^```", re.S | re.M)
inline = re.compile(r"`[^`\n]+`")
# Receiver.member in a code context. Receiver is a capitalized simple name;
# member is the final identifier, optionally a call.
acc_re = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*(\()?")

# member tokens that are never Java members: the `Foo.class` literal and bare
# file-extension references that appear in inline code (HytaleServer.jar, Foo.json).
FILE_EXT = {"class", "jar", "zip", "java", "json", "jsonc", "png", "ogg", "ui",
            "blockymodel", "blockyanim", "md", "bat", "sh", "gradle", "txt",
            "properties", "yml", "yaml", "xml", "wav", "mp3", "html", "css", "js"}

# Identifiers that are JDK/std types or common locals we never want to treat as
# Hytale classes even if a same-named class happens to exist in the jar.
JDK_SKIP = {"System", "Math", "String", "Integer", "Long", "Double", "Float",
            "Boolean", "Optional", "List", "Map", "Set", "Arrays", "Objects",
            "Collections", "Stream", "Files", "Paths", "Path", "UUID",
            "CompletableFuture", "Comparator", "Class", "Thread", "Override",
            "Deprecated", "FunctionalInterface", "SuppressWarnings", "Exception",
            "RuntimeException", "IllegalArgumentException", "IllegalStateException",
            "Runnable", "Function", "Consumer", "Supplier", "Predicate", "T", "E",
            "K", "V", "R", "U"}

# Negation cues: docs deliberately cite non-existent symbols to teach what NOT
# to write ("There is no `Codec.BOOL`", "the method is `getDefaultValue()`").
# A prose line carrying any of these is treated as a negative example, so inline
# symbols on it are not flagged. This guard applies to PROSE only; symbols inside
# ```java blocks are real code and are always checked.
NEG = re.compile(r"\b(no|not|never|cannot|don't|doesn't|isn't|aren't|won't|"
                 r"instead|rather than|no such|no longer|wrong|invalid|removed|"
                 r"renamed|deprecated)\b|n't\b|❌|🚫|⚠", re.I)

# fence-open with a language tag, e.g. ```java
fence_open = re.compile(r"^```([a-zA-Z]*)\s*$")

findings = defaultdict(list)        # doc -> [ (kind, detail) ]
checked_members = 0

def scan_fragment(frag, recv_member_sink):
    for m in acc_re.finditer(frag):
        recv_member_sink.append((m.group(1), m.group(2), bool(m.group(3))))

# types declared in the example code itself (public enum Mode { SHOW, HIDE }):
# their members are user-defined, not jar symbols, so the receiver must be
# excluded even when its name collides with a real jar class.
local_decl = re.compile(r"\b(?:class|interface|enum|record)\s+([A-Z]\w*)")

for f in sorted(glob.glob("docs/*.md")):
    bn = os.path.basename(f)
    fence_lang = None                  # None = prose; "" = untagged block; else lang
    refs = []                          # (recv, member, is_call) for this doc
    local_types = set()
    txt_all = open(f).read()
    for blk in java_block.findall(txt_all):
        local_types.update(local_decl.findall(blk))
    for line in open(f):
        fm = fence_open.match(line)
        if fm:
            if fence_lang is None:
                fence_lang = fm.group(1) or ""     # opening a fence
            else:
                fence_lang = None                  # closing a fence
            continue
        if fence_lang == "java":
            scan_fragment(line, refs)              # real code: always scan
        elif fence_lang is None:
            if NEG.search(line):                   # prose negative example: skip line
                continue
            for span in inline.findall(line):      # only inline `...` in prose
                scan_fragment(span, refs)
        # other fenced langs (json/bash/untagged) contribute no member refs

    seen_member = set()
    for recv, member, is_call in refs:
        if recv in JDK_SKIP or recv in local_types or member in FILE_EXT:
            continue
        cands = resolve_class(recv)
        if not cands:
            continue                       # receiver isn't a known jar class -> skip
        # PascalCase member (mixed-case, leading capital) is a Java *type*
        # reference, not a method/field. If it's a real nested class, fine; if
        # not, it's a JSON/DSL key path (BlockType.Components) leaking through a
        # snippet — not a Java member, so don't flag it. Only camelCase
        # methods/fields and ALL_CAPS constants are checked as members.
        is_pascal = member[0].isupper() and not member.isupper()
        if member[0].isupper() and any(class_exists_internal(c + "." + member) for c in cands):
            continue                       # legitimate nested-class reference
        if is_pascal:
            continue                       # PascalCase non-class -> JSON/DSL key, skip
        key = (recv, member)
        if key in seen_member:
            continue
        seen_member.add(key)
        checked_members += 1
        ok = False
        for c in cands:
            if member in members_of(c):
                ok = True
                break
        if not ok:
            amb = "" if len(cands) == 1 else f" [ambiguous: {len(cands)} classes]"
            findings[bn].append(("member", f"{recv}.{member}{'()' if is_call else ''} — no such member on {recv}{amb}"))

# ---- report ----------------------------------------------------------------
total = sum(len(v) for v in findings.values())
print(f"CHECKED_MEMBERS {checked_members}")
print(f"FINDINGS {total}")
for bn in sorted(findings):
    for kind, detail in findings[bn]:
        print(f"FIND {bn}: {detail}")
