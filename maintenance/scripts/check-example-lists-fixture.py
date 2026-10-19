#!/usr/bin/env python3
"""
Fixture for check-example-lists.py: the gate that holds docs/examples.md, examples/README.md and README.md's
`## Examples` section to the tracked directories of examples/.

WHAT IT PROTECTS. A list that drops an example, lists one twice, links a directory without its slash, or links
something under examples/ that is not an example. The gate reads its population from `git ls-files`, so every case
builds a throwaway git repository (an index is all `ls-files` needs) from the corpus below plus its edits.

THE PROTOCOL is check-links-fixture.py's. Every case is a labelled check. `--mutations` copies the scripts,
reverts one guard of check-example-lists.py at a time, runs every case against the copy, and requires the set of
red labels to equal the one written beside the mutation. A mutation whose text no longer occurs once in the
script is stale and fails the run, and the IDENTITY mutation (no change) must leave nothing red. A case is red
when its check returns something other than the value written for it; a label carries no tab, which the runner
splits on. Most mutations redden only the cases built for them. Two redden nearly everything, and say so by
naming the few cases that stay green (ALL_CASES minus a short set): the population read wrongly, and the base of
every relative link.

Usage: python3 maintenance/scripts/check-example-lists-fixture.py [-v] [--mutations]
"""
from __future__ import annotations
import argparse, concurrent.futures, os, pathlib, shutil, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true')
ap.add_argument('--from-dir', default=str(HERE))
ap.add_argument('--mutations', action='store_true')
A = ap.parse_args()
FROM = pathlib.Path(A.from_dir)

MIN_CASES = 35
MIN_MUTATIONS = 40
fails: list[str] = []
seen: list[str] = []

# ---- the corpus: two examples, a stray file at the top of examples/, three consistent lists ------------------
CORPUS = {
    'README.md': '# R\n\n## Documentation\n\n- [Overview](./docs/00.md)\n\n## Examples\n\n'
                 '### [examples/alpha/](./examples/alpha/)\nAlpha.\n\n'
                 '### [examples/beta/](./examples/beta/)\nBeta.\n\n## Requirements\n\nJava.\n',
    'docs/examples.md': '# Examples\n\n### [alpha](../examples/alpha/)\n\n### [beta](../examples/beta/)\n',
    'examples/README.md': '# Examples\n\n| Example | Type |\n|---|---|\n| [alpha/](./alpha/) | Pack |\n'
                          '| [beta/](./beta/) | Plugin |\n\nBuild notes.\n',
    'examples/alpha/README.md': '# A\n',
    'examples/alpha/x.json': '{}\n',
    'examples/beta/README.md': '# B\n',
    'examples/beta/Foo.java': 'class Foo {}\n',
    'examples/hytale-paths.sh': '#!/bin/sh\n',
}
EX = CORPUS['docs/examples.md']
GAMMA = {'examples/gamma/README.md': '# G\n', 'examples/gamma/y.json': '{}\n'}


def run(root):
    p = subprocess.run([sys.executable, str(FROM / 'check-example-lists.py'), '--root', str(root)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def broken(edits=None, untracked=(), git=True):
    """Build the corpus with `edits` (path -> text, or None to delete), `git add` it, `git rm --cached` the
    `untracked` paths, run the gate. -> (rc, sorted FAIL bodies, whole output)."""
    files = dict(CORPUS)
    for k, v in (edits or {}).items():
        if v is None:
            files.pop(k, None)
        else:
            files[k] = v
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        for rel, body in files.items():
            f = tmp / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body)
        if git:
            subprocess.run(['git', 'init', '-q', str(tmp)], check=True)
            subprocess.run(['git', '-C', str(tmp), 'add', '-A'], check=True)
            for u in untracked:
                subprocess.run(['git', '-C', str(tmp), 'rm', '-q', '--cached', u], check=True)
        rc, out = run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = sorted(l.strip()[6:].strip() for l in out.split('\n') if l.strip().startswith('FAIL'))
    return rc, bad, out


def check(label, thunk, want):
    seen.append(label)
    try:
        got = thunk()
    except Exception as e:                      # noqa: BLE001
        fails.append(f'{label}\traised {type(e).__name__}: {e}')
        return
    if got != want:
        fails.append(f'{label}\t{got!r} != {want!r}')
    elif A.verbose:
        print(f'  ok   {label}')


# ---- labels ------------------------------------------------------------------------------------------------
L_HEALTHY = 'a corpus whose three lists name each of the two directories once passes, exit 0'
L_LINE = 'and the PASS line says 2 example dir(s) and how many each list links'
L_TOPFILE = 'a tracked file at the top of examples/ (hytale-paths.sh) is not an example directory'
L_NOREADME = 'a directory without a tracked README.md FAILs, naming it'
L_NOREADME_UT = 'a README.md that is on disk but not tracked does not count (the population is git ls-files)'
L_UNTRACKED = 'an untracked directory under examples/ is not an example'
L_ZERO = 'a repository with 0 tracked example directories SKIPs, exit 2, saying it is a broken check'
L_NOGIT = 'a tree that is not a git work tree FAILs, naming git'
L_MISSING = 'a list file that does not exist FAILs, naming it'
L_NOSECTION = 'a README.md without an `## Examples` section FAILs, naming the section'
L_NOTLINKED = 'a directory missing from a list FAILs, naming the list and the directory (all three lists)'
L_DUP = 'a directory linked twice from one list FAILs, naming both lines'
L_SLASH = 'a directory link without its trailing slash FAILs, naming the link (all three lists)'
L_GHOST = 'a link under examples/ to something that is not an example directory FAILs (a missing one, a top-level file, in all three lists)'
L_DEEPGHOST = 'and so does a link to a file inside a directory that is not an example'
L_DEEP = 'a link to a file inside an example (its README, a source file) is neither an entry nor a finding'
L_CODESPAN = 'a link inside a code span is no link, it neither satisfies a list nor duplicates an entry'
L_FENCE = 'a link inside a code fence is no link'
L_ALLOWED = 'a link to examples/README.md is allowed and not a member, and the run counts it'
L_TOURNOT = 'and linking examples/README.md does not stand in for a missing example'
L_ROWS = 'the headings of examples/README.md that link a directory again are not list entries, only its table rows are'
L_SECTION = 'a link to an example outside the `## Examples` section of README.md is not an entry'
L_SECTION_END = 'and the section ends at the next `## ` heading'
L_RESOLVE = 'a link resolves against the file it is in, so alpha/ and ../examples/beta/ in examples/README.md name the directories'
L_FRAG = 'a fragment or a query on a directory link does not stop it being found'
L_URL = 'a URL that ends in examples/alpha/ is not a link into examples/ (a table row of examples/README.md, and examples.md)'
L_OUT = "a link that leaves examples/ (to docs/, to the repo root) is not this gate's business"
L_RC = 'a finding exits 1'
L_REFLINK = 'a reference-style link in a list ([x][r], [x][], [x] with a definition) FAILs, naming the line, in all three lists'
L_REFLINK_OK = 'and brackets no definition makes a link are text, and a reference link outside the part that is the list is no finding'
L_COMMENT = 'a link inside an HTML comment (one line or several) is no link: it neither satisfies a list nor duplicates an entry'
L_ICODE = 'a link inside an indented code block is no link either'
L_ICODE_LIST = 'but an indented line that goes on with a list item is not code, and its link counts'
L_ICODE_PARA = 'and neither is an indented line directly under a paragraph line (a lazy continuation)'
L_ALLCASES = 'ALL_CASES lists exactly the labels the fixture checks'

ALL_CASES = {L_HEALTHY, L_LINE, L_TOPFILE, L_NOREADME, L_NOREADME_UT, L_UNTRACKED, L_ZERO, L_NOGIT, L_MISSING,
             L_NOSECTION, L_NOTLINKED, L_DUP, L_SLASH, L_GHOST, L_DEEPGHOST, L_DEEP, L_CODESPAN, L_FENCE, L_ALLOWED,
             L_TOURNOT, L_ROWS, L_SECTION, L_SECTION_END, L_RESOLVE, L_FRAG, L_URL, L_OUT, L_RC, L_REFLINK, L_REFLINK_OK, L_COMMENT,
             L_ICODE, L_ICODE_LIST, L_ICODE_PARA}

# ---- the mutations -----------------------------------------------------------------------------------------
if A.mutations:
    # Each entry: the text of check-example-lists.py that occurs exactly once, its replacement, and the EXACT set of
    # case labels the edit must redden.
    MUTATIONS = {
        'IDENTITY (no change, the harness control)': (
            '#!/usr/bin/env python3', '#!/usr/bin/env python3\n# (identity)', set()),
        'a tracked file at the top of examples/ is a directory': (
            "return {p.split('/')[1] for p in tracked if p.count('/') >= 2}, tracked",
            "return {p.split('/')[1] for p in tracked if p.count('/') >= 1}, tracked",
            # README.md and hytale-paths.sh join the population, so every list "does not link" them and every case
            # that expects an exact finding list, or none, goes red; only the git failure has no list to read.
            ALL_CASES - {L_NOGIT, L_RC}),
        'untracked directories are examples': (
            "'ls-files', '--', 'examples/'", "'ls-files', '--cached', '--others', '--', 'examples/'",
            # --others also lists the untracked README.md, which is how L_NOREADME_UT goes red too
            {L_UNTRACKED, L_NOREADME_UT}),
        'the README test reads the disk, not the index': (
            "if f'examples/{d}/README.md' not in tracked:",
            "if not (root / 'examples' / d / 'README.md').is_file():",
            {L_NOREADME_UT}),
        'a directory without a README passes': (
            "findings.append(f'examples/{d}/ has no tracked README.md, and each list sends the reader to it')",
            "pass",
            {L_NOREADME, L_NOREADME_UT}),
        '0 directories is a clean run': (
            "    if not pop:\n        print(f'  SKIP  0 example directories",
            "    if False:\n        print(f'  SKIP  0 example directories",
            {L_ZERO}),
        'a git failure is not a FAIL': (
            "    if pop_tracked is None:\n        print(f'  FAIL  the gate needs a git work tree",
            "    if False:\n        print(f'  FAIL  the gate needs a git work tree",
            {L_NOGIT}),
        'a missing list file is skipped': (
            "            findings.append(f'{rel}: the list is missing')\n            continue",
            "            continue",
            {L_MISSING}),
        'a missing README.md section is skipped': (
            "            findings.append(f'{rel}: no `{SECTION}` section, so no list')\n            continue",
            "            continue",
            {L_NOSECTION}),
        'a directory missing from a list is not a finding': (
            "                findings.append(f'{rel} does not link examples/{d}/')",
            "                pass",
            {L_NOTLINKED, L_TOURNOT, L_CODESPAN, L_FENCE, L_COMMENT, L_ICODE, L_REFLINK}),
        'a directory linked twice is not a finding': (
            "                findings.append(f'{rel} links examples/{d}/ {n} times (lines {\", \".join(map(str, hits[d]))})')",
            "                pass",
            {L_DUP}),
        'a slash-less directory link is accepted': (
            "                    findings.append(f'{rel}:{ln} links {raw} without the trailing slash (write {raw}/)')",
            "                    pass",
            {L_SLASH}),
        'a link to a non-example under examples/ is ignored': (
            "                findings.append(f'{rel}:{ln} links {raw}, which is not an example directory')",
            "                pass",
            {L_GHOST, L_DEEPGHOST}),
        'a link to a file inside an example is an entry': (
            "            elif len(segs) == 1:\n                if not slash:",
            "            else:\n                if not slash:",
            # the README link L_NOTLINKED puts where the beta directory link was now counts as the entry
            {L_DEEP, L_NOTLINKED}),
        'a link to a file inside a non-example is ignored': (
            "            elif name not in pop:",
            "            elif name not in pop and len(segs) == 1:",
            {L_DEEPGHOST}),
        'a link to a URL is read as a path': (
            "            if CL.SCHEME.match(path):",
            "            if False:",
            {L_URL}),
        'links are read from the text, code spans and all': (
            "CL.link_dests(text, fenced)",
            "[(n, m) for n, l in enumerate(text.split('\\n'), 1) if n not in fenced for m in re.findall(r'\\]\\(([^)\\s]+)', l)]",
            {L_CODESPAN, L_REFLINK}),
        'links in code fences are read': (
            "CL.link_dests(text, fenced)", "CL.link_dests(text, set())",
            {L_FENCE}),
        'a link that leaves examples/ is judged': (
            "            if not joined.startswith('examples/'):\n                continue",
            "            if False:\n                continue",
            {L_OUT}),
        'the link to examples/README.md is not allowed': (
            "            if segs == ['README.md']:\n                allowed[rel] += 1\n            elif name not in pop:",
            "            if False:\n                allowed[rel] += 1\n            elif name not in pop:",
            {L_ALLOWED, L_TOURNOT, L_COMMENT}),
        'the allowed links are not counted': (
            "                allowed[rel] += 1", "                pass",
            {L_ALLOWED}),
        'examples/README.md is read whole, not by its table rows': (
            "        return {n for n, l in enumerate(lines, 1) if l.lstrip().startswith('|')}",
            "        return set(range(1, len(lines) + 1))",
            {L_ROWS, L_REFLINK}),
        'README.md is read whole, not by its section': (
            "    return set(range(start + 1, end))",
            "    return set(range(1, len(lines) + 1))",
            {L_SECTION, L_SECTION_END, L_REFLINK, L_REFLINK_OK}),
        'the README.md section runs to the end of the file': (
            "if n not in fenced and lines[n - 1].startswith('## ')), len(lines) + 1)",
            "if False), len(lines) + 1)",
            {L_SECTION_END, L_REFLINK, L_REFLINK_OK}),
        'a link resolves against the repository root, not its own file': (
            "joined = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))",
            "joined = posixpath.normpath(path)",
            # no relative link reaches examples/ any more, so every case that reads one is red
            ALL_CASES - {L_ZERO, L_NOGIT, L_RC, L_TOPFILE}),
        'a fragment and a query stay on the path': (
            "path = urllib.parse.unquote(raw.partition('#')[0].partition('?')[0])",
            "path = urllib.parse.unquote(raw)",
            {L_FRAG}),
        'a finding exits 0': (
            "    if findings:\n        return 1",
            "    if findings:\n        return 0",
            {L_RC}),
        'a reference-style link in a list is not a finding': (
            "            if ln in scope:\n                findings.append(f'{rel}:{ln} has a reference-style link",
            "            if False:\n                findings.append(f'{rel}:{ln} has a reference-style link",
            {L_REFLINK}),
        'a reference-style link is a finding wherever it stands': (
            "            if ln in scope:\n                findings.append(f'{rel}:{ln} has a reference-style link",
            "            if True:\n                findings.append(f'{rel}:{ln} has a reference-style link",
            {L_REFLINK_OK}),
        'every bracket pair is a reference-style use (check-links.reference_uses)': (
            "return [(ln, src) for ln, src, label in uses if label in defs]",
            "return [(ln, src) for ln, src, label in uses if True]",
            {L_REFLINK_OK}, 'check-links.py'),
        'the label of [text][label] is ignored (check-links.reference_uses)': (
            "            label = mm.group(2) or mm.group(1)\n            uses.append(",
            "            label = mm.group(1)\n            uses.append(",
            {L_REFLINK}, 'check-links.py'),
        'HTML comments are links': (
            "    spans = [m.span() for m in re.finditer(r'<!--.*?(?:-->|\\Z)', probe, re.S)]",
            "    spans = []",
            {L_COMMENT}),
        'a comment opened in a code fence hides what follows': (
            "probe = '\\n'.join(' ' * len(l) if n in fenced else l for n, l in enumerate(lines, 1))",
            "probe = '\\n'.join(l for n, l in enumerate(lines, 1))",
            {L_COMMENT}),
        'an unclosed comment hides nothing': (
            "re.finditer(r'<!--.*?(?:-->|\\Z)', probe, re.S)", "re.finditer(r'<!--.*?-->', probe, re.S)",
            {L_COMMENT}),
        'indented code blocks are links': (
            "                lines[n - 1] = ' ' * len(l)", "                pass",
            {L_ICODE}),
        'a tab does not indent code': (
            "if l.startswith('    ') or l.startswith('\\t'):", "if l.startswith('    '):",
            {L_ICODE}),
        'an indented line directly under a code line is not code': (
            "if (after_blank or in_code) and not in_list:", "if after_blank and not in_list:",
            {L_ICODE}),
        'a list never ends, so code after it is a list continuation': (
            "            elif after_blank and not l.startswith(' '):\n                in_list = False",
            "            elif after_blank and not l.startswith(' '):\n                pass",
            {L_ICODE}),
        'an indented line in a list item is code': (
            "if (after_blank or in_code) and not in_list:", "if (after_blank or in_code):",
            {L_ICODE_LIST}),
        'an indented line under a paragraph line is code': (
            "if (after_blank or in_code) and not in_list:", "if not in_list:",
            {L_ICODE_PARA}),
    }
    print(f'MUTATIONS {len(MUTATIONS)} defect(s) reintroduced, expected red set asserted exactly')
    if len(MUTATIONS) < MIN_MUTATIONS:
        print(f'  FAIL  {len(MUTATIONS)} mutation(s), floor {MIN_MUTATIONS}')
        sys.exit(1)
    if not any(k.startswith('IDENTITY') for k in MUTATIONS):
        print('  FAIL  no IDENTITY control')
        sys.exit(1)

    def one(item):
        label, (old, new, expect, *rest) = item
        target = rest[0] if rest else 'check-example-lists.py'
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            for f in HERE.glob('*.py'):
                shutil.copy2(f, tmp / f.name)
            body = (tmp / target).read_text()
            if body.count(old) != 1:
                return label, None, f'text occurs {body.count(old)}x in {target}, wanted 1: the mutation is stale and measured nothing'
            (tmp / target).write_text(body.replace(old, new, 1))
            r = subprocess.run([sys.executable, str(HERE / pathlib.Path(__file__).name), '--from-dir', str(tmp)],
                               capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            out = r.stdout + r.stderr
            red = {l[len('  FAIL '):].split('\t')[0] for l in out.split('\n') if l.startswith('  FAIL ') and '\t' in l}
            return label, red, out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    t0 = time.time()
    rc = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, MUTATIONS.items()))
    for label, red, out in results:
        expect = MUTATIONS[label][2]
        if red is None:
            rc = 1
            print(f'  FAIL  {label}: {out}')
        elif red == expect:
            print(f'  ok    {label}  ({len(red)} case(s) red)')
        else:
            rc = 1
            print(f'  FAIL  {label}')
            for m in sorted(expect - red):
                print(f'          expected red, stayed green: {m}')
            for m in sorted(red - expect):
                print(f'          reddened unexpectedly:      {m}')
    print('MUTATIONS ' + ('all expected red sets matched' if rc == 0 else 'a red set did not match, see above')
          + f' ({time.time() - t0:.0f} s)')
    sys.exit(rc)

# ---- the healthy corpus ------------------------------------------------------------------------------------
_rc, _bad, _out = broken()
check(L_HEALTHY, lambda: (_rc, _bad), (0, []))
check(L_LINE, lambda: next((l.strip() for l in _out.split('\n') if 'PASS' in l), ''),
      'PASS  2 example dir(s); examples.md 2, examples/README.md 2, README.md 2 '
      '(each directory linked once, with its slash, from each list)')
check(L_TOPFILE, lambda: 'hytale-paths' in _out, False)

# ---- the population ----------------------------------------------------------------------------------------
check(L_NOREADME, lambda: broken({'examples/beta/README.md': None})[1],
      ['examples/beta/ has no tracked README.md, and each list sends the reader to it'])
check(L_NOREADME_UT, lambda: broken(untracked=('examples/beta/README.md',))[1],
      ['examples/beta/ has no tracked README.md, and each list sends the reader to it'])
check(L_UNTRACKED, lambda: broken(GAMMA, untracked=tuple(GAMMA))[1], [])
_zero = lambda: broken({k: None for k in CORPUS if k.startswith('examples/') and k.count('/') >= 2})
check(L_ZERO, lambda: (_zero()[0], 'a broken check, not a clean run' in _zero()[2]), (2, True))
check(L_NOGIT, lambda: (broken(git=False)[0], any('git work tree' in b for b in broken(git=False)[1])), (1, True))

# ---- the lists exist ---------------------------------------------------------------------------------------
check(L_MISSING, lambda: broken({'docs/examples.md': None})[1], ['docs/examples.md: the list is missing'])
check(L_NOSECTION, lambda: broken({'README.md': '# R\n\n## Documentation\n\n[x](./docs/00.md)\n'})[1],
      ['README.md: no `## Examples` section, so no list'])

# ---- membership: once, with a slash, and nothing else ------------------------------------------------------
check(L_NOTLINKED, lambda: [
    broken({'docs/examples.md': EX.replace('(../examples/beta/)', '(../examples/beta/README.md)')})[1],
    broken({'examples/README.md': CORPUS['examples/README.md'].replace('| [beta/](./beta/) | Plugin |\n', '')})[1],
    broken({'README.md': CORPUS['README.md'].replace('### [examples/beta/](./examples/beta/)\n', '### examples/beta/\n')})[1]],
    [['docs/examples.md does not link examples/beta/'],
     ['examples/README.md does not link examples/beta/'],
     ['README.md does not link examples/beta/']])
check(L_DUP, lambda: broken({'docs/examples.md': EX + '\nAgain [alpha](../examples/alpha/).\n'})[1],
      ['docs/examples.md links examples/alpha/ 2 times (lines 3, 7)'])
check(L_SLASH, lambda: [
    broken({'docs/examples.md': EX.replace('(../examples/alpha/)', '(../examples/alpha)')})[1],
    broken({'examples/README.md': CORPUS['examples/README.md'].replace('(./alpha/)', '(./alpha)')})[1],
    broken({'README.md': CORPUS['README.md'].replace('(./examples/alpha/)', '(./examples/alpha)')})[1]],
    [['docs/examples.md:3 links ../examples/alpha without the trailing slash (write ../examples/alpha/)'],
     ['examples/README.md:5 links ./alpha without the trailing slash (write ./alpha/)'],
     ['README.md:9 links ./examples/alpha without the trailing slash (write ./examples/alpha/)']])
check(L_GHOST, lambda: [
    broken({'docs/examples.md': EX + '\n[g](../examples/ghost/)\n'})[1],
    broken({'docs/examples.md': EX + '\n[g](../examples/hytale-paths.sh)\n'})[1],
    broken({'examples/README.md': CORPUS['examples/README.md'] + '| [g](./ghost/) | x |\n'})[1],
    broken({'README.md': CORPUS['README.md'].replace('Beta.\n', 'Beta.\n\n### [g](./examples/ghost/)\n')})[1]],
    [['docs/examples.md:7 links ../examples/ghost/, which is not an example directory'],
     ['docs/examples.md:7 links ../examples/hytale-paths.sh, which is not an example directory'],
     ['examples/README.md:9 links ./ghost/, which is not an example directory'],
     ['README.md:15 links ./examples/ghost/, which is not an example directory']])
check(L_DEEPGHOST, lambda: broken({'docs/examples.md': EX + '\n[g](../examples/ghost/README.md)\n'})[1],
      ['docs/examples.md:7 links ../examples/ghost/README.md, which is not an example directory'])
check(L_DEEP, lambda: broken({'docs/examples.md': EX + '\n[r](../examples/alpha/README.md) [s](../examples/beta/Foo.java)\n'})[1], [])

# ---- how a link is read ------------------------------------------------------------------------------------
check(L_CODESPAN, lambda: [
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '### beta `[beta](../examples/beta/)`')})[1],
    broken({'docs/examples.md': EX + '\nWrite `[alpha](../examples/alpha/)` in a list.\n'})[1]],
    [['docs/examples.md does not link examples/beta/'], []])
check(L_FENCE, lambda: [
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '```md\n[beta](../examples/beta/)\n```')})[1],
    broken({'docs/examples.md': EX + '\n```md\n[alpha](../examples/alpha/)\n```\n'})[1]],
    [['docs/examples.md does not link examples/beta/'], []])
_TOUR = EX + '\nThe [tour](../examples/README.md).\n'
check(L_ALLOWED, lambda: (broken({'docs/examples.md': _TOUR})[1],
                          next((l.strip() for l in broken({'docs/examples.md': _TOUR})[2].split('\n') if 'INFO' in l), '')),
      ([], 'INFO  1 link(s) to examples/README.md allowed, not members: docs/examples.md 1, examples/README.md 0, README.md 0'))
check(L_TOURNOT, lambda: broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '[tour](../examples/README.md)')})[1],
      ['docs/examples.md does not link examples/beta/'])
check(L_ROWS, lambda: broken({'examples/README.md': CORPUS['examples/README.md']
                              + '\n### [alpha/](./alpha/)\n\n### [beta/](./beta/)\n'})[1], [])
check(L_SECTION, lambda: broken({'README.md': CORPUS['README.md'].replace(
    '- [Overview](./docs/00.md)\n', '- [Overview](./docs/00.md)\n- [a](./examples/alpha/)\n')})[1], [])
check(L_SECTION_END, lambda: broken({'README.md': CORPUS['README.md'].replace('Java.\n', 'Java.\n\n[a](./examples/alpha/)\n')})[1], [])
check(L_RESOLVE, lambda: broken({'examples/README.md': CORPUS['examples/README.md'].replace('(./alpha/)', '(alpha/)')
                                 .replace('(./beta/)', '(../examples/beta/)')})[1], [])
check(L_FRAG, lambda: broken({'docs/examples.md': EX.replace('(../examples/alpha/)', '(../examples/alpha/#top)')
                              .replace('(../examples/beta/)', '(../examples/beta/?plain=1)')})[1], [])
check(L_URL, lambda: [
    broken({'docs/examples.md': EX + '\n[gh](https://github.com/o/r/tree/main/examples/alpha/)\n'})[1],
    broken({'examples/README.md': CORPUS['examples/README.md'] + '| [gh](https://github.com/o/r/tree/main/examples/alpha/) | x |\n'})[1]],
    [[], []])
check(L_OUT, lambda: broken({'docs/examples.md': EX + '\n[i](01-index.md) [r](../README.md) [d](../docs/)\n'})[1], [])
check(L_RC, lambda: broken({'docs/examples.md': None})[0], 1)

# ---- what renders as a link --------------------------------------------------------------------------------
_REFMSG = lambda rel, n, text: (f'{rel}:{n} has a reference-style link {text}: write the entry as an inline link, '
                                f'[text](dir/), so its destination is read where it stands')
check(L_REFLINK, lambda: [
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '### [beta][b]') + '\n[b]: ../examples/beta/\n'})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '### [beta][]') + '\n[beta]: ../examples/beta/\n'})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '### [beta]') + '\n[beta]: ../examples/beta/\n'})[1],
    broken({'examples/README.md': CORPUS['examples/README.md'].replace('| [beta/](./beta/) | Plugin |', '| [beta/][b] | Plugin |')
            + '\n[b]: ./beta/\n'})[1],
    broken({'README.md': CORPUS['README.md'].replace('### [examples/beta/](./examples/beta/)', '### [examples/beta/][b]')
            + '\n[b]: ./examples/beta/\n'})[1]],
    [[_REFMSG('docs/examples.md', 5, '[beta][b]')],
     [_REFMSG('docs/examples.md', 5, '[beta][]')],
     [_REFMSG('docs/examples.md', 5, '[beta]')],
     ['examples/README.md does not link examples/beta/', _REFMSG('examples/README.md', 6, '[beta/][b]')],
     ['README.md does not link examples/beta/', _REFMSG('README.md', 12, '[examples/beta/][b]')]])
check(L_REFLINK_OK, lambda: (broken({'docs/examples.md': EX + '\nSee [the notes] and [x][nodef].\n'})[1],
                             broken({'README.md': CORPUS['README.md'].replace('Java.\n', 'Java, see [the docs][d].\n\n[d]: ./docs/00.md\n')})[1]),
      ([], []))
check(L_COMMENT, lambda: [
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '<!-- [beta](../examples/beta/) -->')})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', '<!--\n[beta](../examples/beta/)\n-->')})[1],
    broken({'docs/examples.md': EX + '\n<!-- [alpha](../examples/alpha/) -->\n'})[1],
    broken({'docs/examples.md': EX + '\nA [tour](../examples/README.md) <!-- note --> and more.\n'})[1],
    broken({'docs/examples.md': '# Examples\n\n```html\n<!-- open\n```\n\n### [alpha](../examples/alpha/)\n\n### [beta](../examples/beta/)\n'})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', 'Text <!-- never closed\n[beta](../examples/beta/)\n')})[1]],
    [['docs/examples.md does not link examples/beta/'], ['docs/examples.md does not link examples/beta/'], [], [], [],
     ['docs/examples.md does not link examples/beta/']])
check(L_ICODE, lambda: [
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', 'Intro.\n\n    [beta](../examples/beta/)\n')})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', 'Intro.\n\n\t[beta](../examples/beta/)\n')})[1],
    broken({'docs/examples.md': EX + '\nIntro.\n\n    [alpha](../examples/alpha/)\n'})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)', 'Intro.\n\n    first line\n    [beta](../examples/beta/)\n')})[1],
    broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)',
                                           '- item\n\nParagraph.\n\n    [beta](../examples/beta/)\n')})[1]],
    [['docs/examples.md does not link examples/beta/'], ['docs/examples.md does not link examples/beta/'], [],
     ['docs/examples.md does not link examples/beta/'], ['docs/examples.md does not link examples/beta/']])
check(L_ICODE_LIST, lambda: broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)',
                                                                '- item\n\n    [beta](../examples/beta/)\n')})[1], [])
check(L_ICODE_PARA, lambda: broken({'docs/examples.md': EX.replace('### [beta](../examples/beta/)',
                                                                'Intro line\n    [beta](../examples/beta/)\n')})[1], [])

# ---- the report --------------------------------------------------------------------------------------------
check(L_ALLCASES, lambda: sorted(set(seen) - {L_ALLCASES}), sorted(ALL_CASES))
print(f'\nFIXTURE {len(seen)} check(s): {len(seen) - len(fails)} passed, {len(fails)} failed')
for f in fails:
    print(f'  FAIL {f}')
if len(seen) < MIN_CASES:
    print(f'  FAIL floor: {len(seen)} check(s) ran, at least {MIN_CASES} expected')
    sys.exit(1)
sys.exit(1 if fails else 0)
