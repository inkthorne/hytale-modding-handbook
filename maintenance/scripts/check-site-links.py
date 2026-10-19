#!/usr/bin/env python3
"""
Every link in the BUILT docs site resolves, checked on the HTML and with nothing from Zensical.

WHY ON THE OUTPUT. zensical validates the markdown source (its link check is all-or-nothing per kind, and it
exits 0 with warnings), and the site is what readers get: a link rewritten wrongly by handbook_md.py, an id the
slug did not produce, a stylesheet the theme did not copy all pass the source check. This script reads the
built `*.html` and shares nothing with zensical but the files it wrote. Standard library only.

  check-site-links.py SITE_DIR --repo ROOT --ref REF [--site-url URL] [--repo-url URL] [--docs DOCS_DIR]
                      [--min-pages 79] [--min-rewritten 9]

WHAT IS CHECKED
  - Every same-site `href` and `src` (a, link, img, script, source, iframe) resolves to a file under SITE_DIR
    (`dir/` to `dir/index.html`), and every `#fragment` on an `.html` target is an `id` (or a `name`) of that
    page. An absolute `https://...` URL under --site-url is same-site, and so is a root-relative one that starts
    with the site's path (404.html carries /hytale-modding-handbook/assets/...). Any other root-relative link
    (`/x`) FAILs: the site is served from a sub-path, where it points at the wrong site.
  - Off-site links are COUNTED, never fetched.
  - A link to this repository's GitHub (--repo-url) of the form `/blob/<ref>/<path>` or `/tree/<ref>/<path>`
    must name an existing path in --repo, a file for blob and a directory for tree. Those whose ref is --ref
    are the links handbook_md.py rewrote (the docs' ../examples/... and ../CLAUDE.md); one authored with another
    ref (blocks-java-api.md links tree/main/examples/item-respawner) is checked for the path and not counted as
    rewritten. `.md` targets among the rewritten are counted too: check-site-build.py needs that figure.
  - With --docs: for every docs page, every anchor check-links.py computes from its headings (the ones the
    markdown gates and GitHub link to) must be an `id` on a heading of the built page. Zensical's own slug and
    the duplicate numbering are the extension's; that they agree with GitHub's is measured here, per page.
    A FAIL names the page, the anchor and the nearest heading id the build has.

FLOORS. Exit 1, whatever else is true, when fewer than --min-pages pages (every .html under SITE_DIR) were
parsed (78 docs pages and 404.html = 79), when there are 0 internal links, or when fewer than --min-rewritten
links were rewritten (9 leave docs/ today: 8 into ../examples/ and ../CLAUDE.md). A checker that visited
nothing is not a clean run.

Prints `SITE <p> page(s) parsed, <n> internal link(s) resolved (<f> with a fragment), <o> off-site link(s)
counted, not fetched, <r> rewritten GitHub link(s) at <ref> (<m> to .md files)` and, with --docs, an
`ANCHORS` line. Exit 0 clean, 1 findings or a floor, 2 SITE_DIR unreadable.
"""
from __future__ import annotations
import argparse, difflib, importlib.util, os, pathlib, posixpath, re, sys, urllib.parse
from html.parser import HTMLParser

LINK_ATTRS = {'a': 'href', 'link': 'href', 'area': 'href', 'img': 'src', 'script': 'src', 'source': 'src',
              'iframe': 'src', 'video': 'src', 'audio': 'src'}
HEADINGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.heading_ids: set[str] = set()
        self.links: list[tuple[str, str]] = []      # (tag, url)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ('id', 'name'):
            if a.get(k):
                self.ids.add(a[k])
        if tag in HEADINGS and a.get('id'):
            self.heading_ids.add(a['id'])
        attr = LINK_ATTRS.get(tag)
        if attr and a.get(attr) is not None:
            self.links.append((tag, a[attr]))

    handle_startendtag = handle_starttag


def parse(path: pathlib.Path) -> Page:
    p = Page()
    p.feed(path.read_text(errors='replace'))
    p.close()
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--ref', required=True)
    ap.add_argument('--site-url', default='')
    ap.add_argument('--repo-url', default='https://github.com/inkthorne/hytale-modding-handbook')
    ap.add_argument('--docs', default='')
    ap.add_argument('--min-pages', type=int, default=79)
    ap.add_argument('--min-rewritten', type=int, default=9)
    a = ap.parse_args()
    site = pathlib.Path(a.site)
    repo = pathlib.Path(a.repo)
    if not site.is_dir():
        print(f'  FAIL  {a.site} is not a directory')
        return 2
    site_url = a.site_url.rstrip('/') + '/' if a.site_url else ''
    repo_url = a.repo_url.rstrip('/')
    site_path = urllib.parse.urlsplit(site_url).path if site_url else ''     # /hytale-modding-handbook/
    if site_path == '/':
        site_path = ''

    files = {p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}
    htmls = sorted(f for f in files if f.endswith('.html'))
    cache: dict[str, Page] = {}

    def page(rel: str) -> Page:
        if rel not in cache:
            cache[rel] = parse(site / rel)
        return cache[rel]

    fails: list[str] = []
    internal = with_frag = offsite = other = rewritten = rewritten_md = 0
    for rel in htmls:
        pg = page(rel)
        for tag, url in pg.links:
            url = url.strip()
            if not url:
                continue
            sp = urllib.parse.urlsplit(url)
            if sp.scheme in ('http', 'https') or url.startswith('//'):
                if site_url and url.startswith(site_url):
                    url = url[len(site_url):]
                    sp = urllib.parse.urlsplit(url)
                else:
                    offsite += 1
                    # this repository's GitHub: a blob or tree link must name a path that exists
                    m = re.match(re.escape(repo_url) + r'/(blob|tree)/([^/]+)/([^?#]*)(?:#.*)?$', url)
                    if m:
                        kind, ref, path = m.group(1), m.group(2), urllib.parse.unquote(m.group(3))
                        target = repo / path
                        ok = target.is_file() if kind == 'blob' else target.is_dir()
                        if not ok:
                            fails.append(f'{rel}: GitHub link {url} names {path!r}, which is not a '
                                         f'{"file" if kind == "blob" else "directory"} in the repository')
                        if ref == a.ref:
                            rewritten += 1
                            rewritten_md += path.endswith('.md')
                    elif url.startswith(repo_url + '/blob/') or url.startswith(repo_url + '/tree/'):
                        fails.append(f'{rel}: GitHub link {url} is not of the form {repo_url}/(blob|tree)/<ref>/<path>')
                    continue
            elif sp.scheme:
                other += 1                  # mailto:, javascript:, data:, tel:
                continue
            if site_path and url.startswith(site_path):
                url = url[len(site_path):]          # 404.html is served for any depth, so its links carry the base path
                sp = urllib.parse.urlsplit(url)
            if url.startswith('/'):
                fails.append(f'{rel}: {tag} {url} is root-relative; the site is served from a sub-path')
                continue
            internal += 1
            path = urllib.parse.unquote(sp.path)
            if not path:
                target = rel
            else:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
                if path.endswith('/') or (target not in files and f'{target}/index.html' in files):
                    target = posixpath.join(target, 'index.html')
            if target not in files:           # (a link out of SITE_DIR normalises to `../...`, which is no file)
                fails.append(f'{rel}: {tag} {url} -> no such file in the built site ({target})')
                continue
            frag = urllib.parse.unquote(sp.fragment)
            if frag and target.endswith('.html'):
                with_frag += 1
                if frag not in page(target).ids:
                    fails.append(f'{rel}: {tag} {url} -> no element with id {frag!r} in {target}')

    print(f'SITE {len(htmls)} page(s) parsed, {internal} internal link(s) resolved ({with_frag} with a fragment), '
          f'{offsite} off-site link(s) counted, not fetched, {rewritten} rewritten GitHub link(s) at {a.ref} '
          f'({rewritten_md} to .md files)')

    if a.docs:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        spec = importlib.util.spec_from_file_location('check_links_for_site', pathlib.Path(__file__).resolve().parent / 'check-links.py')
        cl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cl)
        n_pages = n_anchors = 0
        for md in sorted(pathlib.Path(a.docs).glob('*.md')):
            built = md.with_suffix('.html').name
            if built not in files:
                fails.append(f'docs/{md.name}: no built page {built}')
                continue
            n_pages += 1
            have = page(built).heading_ids
            anchors, _ = cl.anchors_of(md.read_text(errors='replace'))
            for an in sorted(anchors):
                n_anchors += 1
                if an not in have:
                    near = difflib.get_close_matches(an, sorted(have), n=1, cutoff=0.0)
                    fails.append(f'docs/{md.name}: anchor {an!r} (check-links) is not a heading id of {built} '
                                 f'(nearest built id: {near[0] if near else "none"})')
        print(f'ANCHORS {n_anchors} heading anchor(s) of {n_pages} docs page(s) computed by check-links.py, each looked up '
              f'in the heading ids of its built page')
        if n_pages == 0 or n_anchors == 0:
            fails.append('the anchor cross-check read 0 pages or 0 anchors, so it checked nothing')

    if len(htmls) < a.min_pages:
        fails.append(f'only {len(htmls)} page(s) were parsed, floor is {a.min_pages}: the build is incomplete or this is the wrong directory')
    if internal == 0:
        fails.append('0 internal links were found: a checker that read none is not a clean run')
    if rewritten < a.min_rewritten:
        fails.append(f'{rewritten} link(s) were rewritten to GitHub at {a.ref}, floor is {a.min_rewritten}: '
                     f'handbook_md.py did not rewrite the links that leave docs/')
    for f in fails:
        print(f'  FAIL  {f}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
