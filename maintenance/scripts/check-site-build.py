#!/usr/bin/env python3
"""
Judge the output of `zensical build`: no warning that is not explained, and no line this script does not
understand. verify-docs.sh runs it on its build and .github/workflows/pages.yml on the deploy build, so the
two cannot disagree about what a clean build is.

WHY A GRAMMAR AND NOT A GREP. `zensical build` exits 0 with warnings (its `--strict` is unusable here: the one
warning below would abort it), so the exit status says nothing about the links. A filter that greps for
`Warning:` passes a build whose output format changed, whose warning wording is new, or that printed an error
without the word. So every line of the output must belong to the grammar of a build, and anything else is a
FAIL:

    Build started
    Warning: <message>                      (one block per warning: the position, then the source line
        ╭─[ <file>:<line>:<col> ]            with a marker under the link target, closed by a rule ending ╯)
        │ ...
    ────╯
    No issues found | <N> issue(s) found
    Build finished in <time>

zensical colours its output whatever the environment (NO_COLOR, CLICOLOR_FORCE, TERM=dumb and a pipe instead of a
terminal were each tried, 12 environments, and every line stayed coloured; review of d361e13..9f19ac9), so the ANSI
sequences are stripped here and no variable is set to ask for plain text. The count in the summary must equal the
number of warning blocks.

WHAT IS EXPLAINED. Exactly one kind of warning is expected, and only when it is what it looks like: `page does
not exist`, at a position (file:line:col, col the first character of a link's target) where the source line
holds `](<target>` and the target resolves, from docs/, to a path OUTSIDE docs/ that exists in the repository.
That is a link to `../CLAUDE.md`: handbook_md.py rewrites it to GitHub in the output, but zensical validates
the source text and warns anyway. Every other warning (a missing page, a missing anchor, a link that
resolves nowhere, a raw `<a href>`, a warning kind not seen before) is unexplained. With --rewritten-md N the
number of explained warnings must equal N, the `.md` links check-site-links.py counted as rewritten in the
built pages, so a warning cannot be explained by a link the build did not actually rewrite.

  check-site-build.py LOG --docs docs --repo . [--rewritten-md N]

Prints `BUILD <W> warning(s), <E> explained, <I> issue(s) reported, finished in <T>`. Exit 0 clean, 1 on any
FAIL line, 2 when LOG or --docs cannot be read.
"""
from __future__ import annotations
import argparse, os, pathlib, re, sys

ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
POS = re.compile(r'^\s*╭─\[ (?P<file>\S+):(?P<line>\d+):(?P<col>\d+) \]\s*$')
SRC = re.compile(r'^\s*(?P<n>\d+) │ ?(?P<text>.*)$')
BAR = re.compile(r'^\s*│.*$')
END = re.compile(r'^─+╯\s*$')
WARN = re.compile(r'^Warning: (?P<msg>.+)$')
SUMMARY = re.compile(r'^(?:No issues found|(?P<n>\d+) issues? found)$')
FINISHED = re.compile(r'^Build finished in (?P<t>[0-9.]+ ?m?s)$')


def judge(log: str, docs: pathlib.Path, repo: pathlib.Path):
    """-> (warnings, explained, issues reported, finish time, [FAIL text])"""
    fails: list[str] = []
    lines = [ANSI.sub('', l).rstrip() for l in log.splitlines()]
    started = finished = 0
    summary = None
    blocks = []
    cur = None
    finish_t = ''
    for no, l in enumerate(lines, 1):
        if cur is not None:
            if END.match(l):
                blocks.append(cur)
                cur = None
            elif (m := POS.match(l)):
                if cur['pos']:
                    fails.append(f'build output line {no}: a second position inside one warning block')
                cur['pos'] = (m['file'], int(m['line']), int(m['col']))
            elif (m := SRC.match(l)):
                cur['src'].append((int(m['n']), m['text']))
            elif BAR.match(l) or not l.strip():
                pass
            else:
                fails.append(f'build output line {no}: {l!r} is not part of a warning block')
            continue
        if not l.strip():
            continue
        if l == 'Build started':
            started += 1
            if blocks or summary is not None or finished:
                fails.append(f'build output line {no}: "Build started" is not the first line')
        elif (m := WARN.match(l)):
            cur = {'msg': m['msg'], 'pos': None, 'src': [], 'line': no}
        elif (m := SUMMARY.match(l)):
            if summary is not None:
                fails.append(f'build output line {no}: a second issue count')
            summary = int(m['n'] or 0)
        elif (m := FINISHED.match(l)):
            finished += 1
            finish_t = m['t']
        else:
            fails.append(f'build output line {no}: {l!r} is not a line of a zensical build')
    if cur is not None:
        fails.append(f'build output line {cur["line"]}: a warning block that never closed')
    if started != 1:
        fails.append(f'"Build started" appears {started} time(s), not once')
    if finished != 1:
        fails.append(f'"Build finished in ..." appears {finished} time(s), not once: the build did not finish')
    if summary is None:
        fails.append('the build printed no issue count ("No issues found" or "N issues found")')
    elif summary != len(blocks):
        fails.append(f'the build reports {summary} issue(s) and {len(blocks)} warning block(s) were parsed')

    explained = 0
    docs_abs = pathlib.Path(os.path.abspath(docs))
    repo_abs = pathlib.Path(os.path.abspath(repo))
    for b in blocks:
        where = f'{b["pos"][0]}:{b["pos"][1]}:{b["pos"][2]}' if b['pos'] else 'no position'
        if b['msg'] != 'page does not exist':
            fails.append(f'unexplained warning at {where}: {b["msg"]}')
            continue
        if not b['pos']:
            fails.append(f'unexplained warning: {b["msg"]} (the block names no position)')
            continue
        f, ln, col = b['pos']
        try:
            text = (docs / f).read_text().split('\n')[ln - 1]
        except (OSError, IndexError):
            fails.append(f'unexplained warning at {where}: {b["msg"]} (cannot read that line of docs/{f})')
            continue
        shown = [t for n, t in b['src'] if n == ln]
        if shown and shown[0].rstrip() != text.rstrip():
            fails.append(f'unexplained warning at {where}: the source line the build shows is not docs/{f}:{ln}')
            continue
        if col < 3 or text[col - 3:col - 1] != '](':
            fails.append(f'unexplained warning at {where}: {b["msg"]} (the position is not the target of a [text](target) link)')
            continue
        m = re.match(r'[^)\s]*', text[col - 1:])
        target = m.group(0).partition('#')[0] if m else ''
        dest = pathlib.Path(os.path.abspath(docs_abs / target)) if target else None
        if dest is None or dest == docs_abs or docs_abs in dest.parents:
            fails.append(f'unexplained warning at {where}: {b["msg"]} (the link {target!r} resolves inside docs/, so the page really is missing)')
            continue
        if repo_abs not in dest.parents or not dest.exists():
            fails.append(f'unexplained warning at {where}: {b["msg"]} (the link {target!r} resolves outside docs/ to {dest}, which is not a path in the repository)')
            continue
        explained += 1
    return len(blocks), explained, summary, finish_t, fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--docs', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--rewritten-md', type=int, default=None)
    a = ap.parse_args()
    try:
        log = pathlib.Path(a.log).read_text()
    except OSError as e:
        print(f'  FAIL  cannot read the build log {a.log}: {e}')
        return 2
    docs, repo = pathlib.Path(a.docs), pathlib.Path(a.repo)
    if not docs.is_dir():
        print(f'  FAIL  --docs {a.docs} is not a directory')
        return 2
    w, e, issues, t, fails = judge(log, docs, repo)
    if a.rewritten_md is not None and e != a.rewritten_md:
        fails.append(f'{e} warning(s) explained, but check-site-links.py counted {a.rewritten_md} rewritten .md link(s): '
                     f'an explained warning must be a link the build rewrote, and a rewritten one has to be warned about')
    print(f'BUILD {w} warning(s), {e} explained, {"0" if issues is None else issues} issue(s) reported, finished in {t or "?"}')
    for f in fails:
        print(f'  FAIL  {f}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
