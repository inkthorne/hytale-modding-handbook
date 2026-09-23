#!/usr/bin/env python3
"""triage_drift.py — which docs/examples mention the things a game update changed.

Usage: triage_drift.py REPORT_DIR ASSETS_DIR [CORPUS_ROOT]

Reads update-build.sh's report files (assets-/server-{modified,removed}.txt,
api-changed-classes.txt, src-changed-classes.txt, ServerAssetsIndex.hashes) and
the extracted assets' CommonAssetsIndex.hashes, and searches CORPUS_ROOT/docs and
CORPUS_ROOT/examples (default: the current directory). It prints one line per
changed thing that some file mentions:

    <kind> <thing> → <file> <file> ...

kind is "asset", "class" (signature changed) or "body" (source changed with no
signature change on the top-level class, or a bytecode-only change inside a
method the decompiler could not render). The last line is
"#SUMMARY <checked> changed thing(s) checked, <n> referenced in docs/examples".

Asset keys. A doc names an asset in one of four ways, and each needs its own key:
  - by id: `Tool_Shears_Basic`, with no extension. Matched on the file's stem, as
    a whole word, when the stem is id-shaped (contains "_", 5+ chars) and names at
    most MAX_ID_FILES shipped files. The first version required the stem to be
    UNIQUE, which made nearly every item id ineligible: an item JSON shares its
    stem with its generated icon and often a hitbox. Review of 6ba38ce measured
    211 item JSONs cited by bare id in 292 places that it left unmatched.
  - by a unique file name with a plain stem: `Entity.png`. Matched as the whole
    name, bounded so `1.json` does not match inside `Zone1_Plains1.json`.
    Plain stems are not matched bare: `Migrations/0.json`, `Entity.png` and
    `None.json` flagged up to 134 files each that way.
  - by an ambiguous name: `en-US/server.lang`. Matched as parent/name, so a pt-BR
    change does not flag pages that cite only en-US.
  - by a wildcard: `Server/Languages/*/server.lang`, `<lang>/server.lang`. Matched
    for every file of that name, because such a claim spans all of them.
Files under build/ and .gradle/ and binary files (containing NUL) are skipped.
"""
import collections, os, re, sys


# An id is shared across asset types by design: Bench_Alchemy is an item JSON, a
# block hitbox JSON and a generated icon. Five covers such a family; beyond it the
# stem is a generic name (Walk_Backward names 143 animation files) and falls back
# to the parent/name key.
MAX_ID_FILES = 5


def load_corpus(root):
    corpus = {}
    for top in ("docs", "examples"):
        for d, dirs, fs in os.walk(os.path.join(root, top)):
            dirs[:] = [x for x in dirs if x not in ("build", ".gradle")]
            for f in fs:
                p = os.path.join(d, f)
                b = open(p, "rb").read()
                if b"\0" not in b:
                    corpus[os.path.relpath(p, root)] = b.decode("utf-8", "replace")
    return corpus


class AssetMatcher:
    def __init__(self, shipped):
        self.names = collections.Counter(os.path.basename(p) for p in shipped)
        self.stems = collections.Counter(
            os.path.splitext(os.path.basename(p))[0] for p in shipped)

    def rule(self, p):
        name = os.path.basename(p)
        stem = os.path.splitext(name)[0]
        if (self.stems[stem] <= MAX_ID_FILES and "_" in stem and len(stem) >= 5
                and re.fullmatch(r"\w+", stem)):
            return "stem", re.compile(r"(?<![\w])" + re.escape(stem) + r"(?![\w])")
        if self.names[name] <= 1:
            return "name", re.compile(r"(?<![\w-])" + re.escape(name) + r"(?![\w.])")
        key = re.escape(os.path.basename(os.path.dirname(p)) + "/" + name)
        wild = r"(?:\*|<[^<>/\s]+>)/" + re.escape(name)
        return "parent", re.compile(r"(?:" + key + "|" + wild + r")(?![\w.])")

    def hits(self, p, corpus):
        rx = self.rule(p)[1]
        return sorted(k for k, t in corpus.items() if rx.search(t))


def main(report, assets, root="."):
    def lines(name):
        p = os.path.join(report, name)
        return [l.strip() for l in open(p)] if os.path.exists(p) else []
    corpus = load_corpus(root)
    shipped = []
    idx = os.path.join(assets, "CommonAssetsIndex.hashes")
    if os.path.exists(idx):
        shipped += [l.split(" ", 1)[1].strip() for l in open(idx) if " " in l]
    shipped += [l.split(" ", 1)[1].strip() for l in lines("ServerAssetsIndex.hashes") if " " in l]
    matcher = AssetMatcher(shipped)
    out = []
    for f in ("assets-modified.txt", "assets-removed.txt", "server-modified.txt", "server-removed.txt"):
        for p in lines(f):
            if p:
                out.append(("asset", p, matcher.hits(p, corpus)))
    classes = {}
    for l in lines("api-changed-classes.txt"):
        m = re.match(r"(?:ADDED|REMOVED|CHANGED) +(\S+)", l)
        if m:
            classes[m.group(1)] = "class"
    for l in lines("src-changed-classes.txt"):
        m = re.match(r"(?:BODY|BYTECODE|BLIND) +(\S+)", l)
        if m:
            classes.setdefault(m.group(1), "body")
    for cls, kind in sorted(classes.items()):
        simple = cls.split(".")[-1].split("$")[-1]
        rx = re.compile(r"(?<![\w])" + re.escape(simple) + r"(?![\w])")
        out.append((kind, cls, sorted(k for k, t in corpus.items() if rx.search(t))))
    for kind, thing, h in out:
        if h:
            print(f"{kind} {thing} → {' '.join(h)}")
    print(f"#SUMMARY {len(out)} changed thing(s) checked, {sum(1 for o in out if o[2])} referenced in docs/examples")


if __name__ == "__main__":
    main(*sys.argv[1:4])
