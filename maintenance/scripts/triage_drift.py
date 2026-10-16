#!/usr/bin/env python3
"""triage_drift.py — which docs/examples mention the things a game update changed.

Usage: triage_drift.py REPORT_DIR ASSETS_DIR [CORPUS_ROOT]

Reads update-build.sh's report files (assets-/server-{modified,removed}.txt,
api-changed-classes.txt, src-changed-classes.txt, resource-drift.txt,
resources-old.txt, resources-new.txt, ServerAssetsIndex.hashes) and
the extracted assets' CommonAssetsIndex.hashes, and searches CORPUS_ROOT/docs and
CORPUS_ROOT/examples (default: the current directory). It prints one line per
changed thing that some file mentions:

    <kind> <thing> → <file> <file> ...

kind is "asset", "resource" (a Hypixel-owned non-class jar entry that was added,
removed or changed), "class" (signature changed) or "body" (source changed with no
signature change on the top-level class, or a bytecode-only change inside a
method the decompiler could not render). An anonymous or local class is reported
under its enclosing class, as "body" (see ANON). The last line is
"#SUMMARY <checked> changed thing(s) checked, <n> referenced in docs/examples".

Exit status. 0, or 2 when the report could not be read in full: a line of
resource-drift.txt that is not `<ADDED|REMOVED|CHANGED> <hypixel|third-party> <rule>
<path>` (<rule> is a letter, or `-` where no owners file recorded the path), or a
Hypixel row whose path is missing from the resources-old.txt / resources-new.txt of a
build it needs. The triage is still printed, with what the path, brace and wildcard
rules can match, and an `#ERROR` line (in the report on stdout, before #SUMMARY, and on
stderr) says which file and how many rows lost the match. No
resource-drift.txt, or one with no Hypixel rows, needs neither list.

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
Resource keys (kind "resource"; a path inside HytaleServer.jar such as
migration/blocks/3_4.json or bundledDefaults/server.lang, which no asset index
holds). Only Hypixel-owned rows are triaged; a third-party library's file is not
something a page documents. A doc names one in three ways:
  - by its full path, `migration/blocks/3_4.json`, or in a brace list,
    `migration/blocks/{0_1,3_4}.json`;
  - by a wildcard over its directory, `bundledDefaults/*.lang`, `bundledDefaults/*`
    (docs/i18n.md cites the first). Matched for every file that wildcard spans:
    `dir/*.lang` does not span a .json, a bare `dir/*` is not `dir/*.ext`, and
    neither spans a `/` (`dir/*/sub` is not `dir/*`);
  - by its bare name, ONLY when that name is unique among the jar's resources of a
    build the row's path exists in (the old build for a REMOVED row, the new for an
    ADDED one, either for a CHANGED one) AND absent from the shipped assets. Counted
    per build, never over the union: a resource that moved (REMOVED cfg/x, ADDED
    auth/x) would otherwise share its bare name with itself and flag no page.
    `server.lang` names a jar resource and 20+ shipped files, so a page citing
    `en-US/server.lang` is not flagged by a change to bundledDefaults/server.lang:
    the bare name could mean either.
Files under build/ and .gradle/ and binary files (containing NUL) are skipped.
"""
import collections, os, re, sys


# An id is shared across asset types by design: Bench_Alchemy is an item JSON, a
# block hitbox JSON and a generated icon. Five covers such a family; beyond it the
# stem is a generic name (Walk_Backward names 143 animation files) and falls back
# to the parent/name key.
MAX_ID_FILES = 5

# An anonymous class (`World$1`) or a local one (`World$1Helper`), and anything
# nested in either, has no name a doc can cite: searched by its simple name, `1`,
# `World$1` flagged every gradlew and deploy.bat in the 0.7.2 triage (59 such
# rows). Such a class is part of its enclosing class's body, so its row is folded
# onto that class as a "body" change; a signature change on the enclosing class
# itself still wins.
ANON = re.compile(r"\$\d.*$")


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


RES_END = r"(?![\w-]|\.\w)"
# A wildcard is a shell glob: its `*` does not cross a `/`, so `dir/*/sub` and
# `dir/*.lang/sub` name files below a directory called `*` and are not `dir/*`.
WILD_END = r"(?![\w/-]|\.\w)"


def resource_rx(path, res_names, asset_names):
    """res_names: one Counter of bare names per build the row's path exists in."""
    d, name = os.path.split(path)
    stem, ext = os.path.splitext(name)
    alts = [r"(?<![\w-])" + re.escape(path) + RES_END]
    if d:
        wild_ext = re.escape(ext) if ext else ""
        alts.append(r"(?<![\w-])" + re.escape(d) + r"/\*" + wild_ext + WILD_END)
        alts.append(r"(?<![\w-])" + re.escape(d) + r"/\*(?![\w*./-])")
        alts.append(r"(?<![\w-])" + re.escape(d) + r"/\{(?:[^{}]*,)?\s*" + re.escape(stem) + r"\s*(?:,[^{}]*)?\}" + re.escape(ext))
    if any(c[name] == 1 for c in res_names) and asset_names.get(name, 0) == 0:
        alts.append(r"(?<![\w-])" + re.escape(name) + r"(?![\w.-])")
    return re.compile("|".join(alts))


# A line of resource-drift.txt, as update-build.sh section 5c writes it. <rule> is the
# letter build-jar-cache.sh's owners file records, or `-` when no owners file records
# the path (the row then stays on the Hypixel side by default).
ROW = re.compile(r"(ADDED|REMOVED|CHANGED) (hypixel|third-party) ([a-z]|-) (.+)")


def main(report, assets, root="."):
    """Print the triage; return 0, or 2 when the report could not be read in full.

    Exit 2 means some drift rows lost a match they would have had, and the triage
    printed is INCOMPLETE: a resource-drift row that is not `<state> <owner> <rule>
    <path>` (silently skipped before), and a Hypixel row whose path is not in the
    resources-old.txt / resources-new.txt of each build it needs (REMOVED: old,
    ADDED: new, CHANGED: both). Without that list a bare-name match is impossible
    and the row got no bare-name match, with nothing to say so. What the path, brace
    and wildcard rules can still match is printed first."""
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
    # jar resources: "<ADDED|REMOVED|CHANGED> <owner> <rule> <path>"; resources-old.txt
    # and resources-new.txt list every path of each build so a bare name can be tested
    # for uniqueness within a build
    listed = {b: set(p for p in lines(f"resources-{b}.txt") if p) for b in ("old", "new")}
    res_names = {b: collections.Counter(os.path.basename(p) for p in listed[b]) for b in ("old", "new")}
    malformed, unlisted = [], {"old": [], "new": []}
    for l in lines("resource-drift.txt"):
        if not l:
            continue
        m = ROW.fullmatch(l)
        if not m:
            malformed.append(l)
            continue
        state, owner, _rule, path = m.groups()
        if owner == "hypixel":
            builds = {"ADDED": ("new",), "REMOVED": ("old",)}.get(state, ("old", "new"))
            for b in builds:
                if path not in listed[b]:
                    unlisted[b].append(path)
            rx = resource_rx(path, [res_names[b] for b in builds], matcher.names)
            out.append(("resource", path, sorted(k for k, t in corpus.items() if rx.search(t))))
    classes = {}
    for l in lines("api-changed-classes.txt"):
        m = re.match(r"(?:ADDED|REMOVED|CHANGED) +(\S+)", l)
        if m:
            outer = ANON.sub("", m.group(1))
            if outer == m.group(1):
                classes[outer] = "class"
            else:
                classes.setdefault(outer, "body")
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
    errors = []
    if malformed:
        errors.append(f"{len(malformed)} line(s) of resource-drift.txt are not "
                      f"`<ADDED|REMOVED|CHANGED> <hypixel|third-party> <rule> <path>` and were NOT triaged "
                      f"(first: {malformed[0]!r}); the triage is incomplete")
    for b in ("old", "new"):
        if unlisted[b]:
            f = f"resources-{b}.txt"
            why = ("is missing" if not os.path.exists(os.path.join(report, f))
                   else "is empty" if not listed[b] else "does not list their paths")
            errors.append(f"{f} {why}, so {len(unlisted[b])} Hypixel resource row(s) "
                          f"(first: {unlisted[b][0]}) were matched by path and wildcard only, never by bare name; "
                          f"the triage is incomplete")
    # on stdout too, so the report file (update-build.sh keeps stdout as triage.txt) records
    # that it is incomplete; the SUMMARY stays the last line
    for e in errors:
        print(f"#ERROR {e}")
    print(f"#SUMMARY {len(out)} changed thing(s) checked, {sum(1 for o in out if o[2])} referenced in docs/examples")
    sys.stdout.flush()
    for e in errors:
        print(f"triage_drift: {e}", file=sys.stderr)
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
