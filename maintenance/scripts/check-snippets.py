#!/usr/bin/env python3
"""
check-snippets.py — compile the docs' complete Java snippets against the jar.

Contract: a ```java fenced block whose first line starts with `package ` is a
COMPLETE COMPILATION UNIT and must compile against HytaleServer.jar. Fragment
blocks (signature lists, method bodies) are exempt — they don't start with
`package`. To make a snippet compile-checked, write it as a complete unit.

Why this exists: the symbol checker verifies `Receiver.member` references but
cannot type local variables, so a call like `player.sendMessage(...)` on an
entity `Player` (which has no such method) passed every check until a real
example project failed to compile — 18 doc snippets carried the bug. This
closes that class of rot for every snippet that opts in.

Usage: check-snippets.py <HytaleServer.jar>
Output: PASS/FAIL per snippet; exit 1 on any failure. Called by verify-docs.sh
as a HARD gate. Snippets referencing types defined in a *previous* package-led
snippet of the same doc are compiled together with it (same package = one
javac invocation), so multi-class walkthroughs work.
"""
import glob, os, re, shutil, subprocess, sys, tempfile

if len(sys.argv) != 2:
    print("usage: check-snippets.py <HytaleServer.jar>"); sys.exit(2)
JAR = sys.argv[1]

BLOCK = re.compile(r'^```java\n(package [^\n]+\n.*?)^```$', re.M | re.S)
# Every ```java fence, package-led or not — the denominator. This gate is opt-in
# by design (a fragment cannot compile), but without the total, "all N compile"
# reads as corpus coverage when it is a small opt-in subset.
ANY_JAVA = re.compile(r'^```java\n.*?^```$', re.M | re.S)
CLS = re.compile(r'^(?:public\s+)?(?:final\s+|abstract\s+)*(?:class|interface|enum|record)\s+(\w+)', re.M)
PKG = re.compile(r'^package\s+([\w.]+)\s*;')

failures = 0
checked = 0
total_blocks = 0
docs_with_java = set()
docs_compiled = set()
# group snippets per (doc, package) so multi-class walkthroughs co-compile
groups = {}
for doc in sorted(glob.glob("docs/*.md")):
    text = open(doc).read()
    n_any = len(ANY_JAVA.findall(text))
    total_blocks += n_any
    if n_any:
        docs_with_java.add(doc)
    if BLOCK.search(text):
        docs_compiled.add(doc)
    for m in BLOCK.finditer(text):
        src = m.group(1)
        line = text[:m.start()].count("\n") + 2  # first line of the snippet
        pm = PKG.match(src)
        cm = CLS.search(src)
        if not pm or not cm:
            print(f"  FAIL {doc}:{line}: package-led block without a parseable "
                  f"package/type declaration")
            failures += 1
            continue
        groups.setdefault((doc, pm.group(1)), []).append((line, cm.group(1), src))

for (doc, pkg), snippets in sorted(groups.items()):
    work = tempfile.mkdtemp(prefix="snippets-")
    try:
        pkgdir = os.path.join(work, *pkg.split("."))
        os.makedirs(pkgdir, exist_ok=True)
        for line, cls, src in snippets:
            open(os.path.join(pkgdir, cls + ".java"), "w").write(src)
        files = [os.path.join(pkgdir, cls + ".java") for _, cls, _ in snippets]
        r = subprocess.run(
            ["javac", "-proc:none", "-nowarn", "-cp", JAR, "-d", work] + files,
            capture_output=True, text=True)
        checked += len(snippets)
        where = ", ".join(f"{doc}:{line} {cls}" for line, cls, _ in snippets)
        if r.returncode == 0:
            print(f"  PASS {where}")
        else:
            failures += 1
            print(f"  FAIL {where}")
            for l in (r.stderr or r.stdout).splitlines()[:6]:
                print(f"       {l}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

print(f"CHECKED {checked}")
print(f"BLOCKS {total_blocks}")
print(f"DOCS {len(docs_compiled)} {len(docs_with_java)}")
sys.exit(1 if failures else 0)
