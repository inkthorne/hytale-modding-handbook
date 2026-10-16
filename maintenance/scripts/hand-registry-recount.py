#!/usr/bin/env python3
"""Independent (non-miner) recount of the registry fixture's hand-derived figures.

Route: plain text sweeps over decompiled source, statement = text up to the next
top-level ';'. Shares no code with registry_miner.py. After a game update, run it on the
previous build's snapshot (~/.cache/hytale-update-snapshot/src) FIRST: it must reproduce
the fixture's figures there before its output for the new build means anything. A review
tool, not a gate; see registry-oracle-notes.md §15.

The UNQUALIFIED section (bottom of the file) covers `CODEC.register(...)` and
`getCodecRegistry(PAGE_CODEC)` written WITHOUT a `Receiver.` — the spelling the sweeps
above cannot see (the review of the 0.7.2 pass found 68 such sites in 19 classes; with the
form-2 site it is 69 in 20 at 0.7.2 and 68 in 18 at 0.6.8). It binds each site by a
DIFFERENT WALK from registry_miner's: one forward pass over comment- and string-stripped
text keeping a stack of open classes (class names read forward, held `pending` until the
`{`; anonymous bodies found by walking back over `new Type(args)`), class-level fields
found as declarators whose enclosing member starts at the class's own depth (static or
instance by the modifiers in front, so a second declarator is seen), a shadowing local
searched in the site's enclosing member and kept only while the running brace depth has not
fallen below its own, and a lambda parameter's extent measured as a text span.

WHAT IT SHARES WITH THE MINER, stated so the agreement is not over-read: the decision
table (innermost declaring class binds; instance field or local excludes; a class that may
inherit leaves the site UNRESOLVED) and SIX PATTERNS — the field character class, the
class-keyword regex, the not-a-type keyword set, the typed-local regex, the cast-literal
regex and the lambda-parameter regex — were written into the miner first and copied here.
A bug in one of those is in both, and agreement cannot see it; the synthetic tree, whose
expected figures were read off the source by hand, is what covers them. What the second
route does buy is that the scope WALK (which class, which block, how far a shadow reaches)
is implemented twice: the 2026-10-15 review's sibling-block and second-declarator cases
disagreed between the two until each was fixed.

It must reproduce the previous build's known figures (68 sites: 67 form-1 + 1 form-2 at
0.6.8) before its 0.7.2 output means anything.

DISCRIMINATOR KEYS and ENUM IDS (2026-10-15). Two more things are derived here, again by a
walk that is not the miner's: (1) `declared_keys()` is DECLARATION-driven where the miner is
registration-driven: it sweeps every `FIELD = new <X>CodecMapCodec(...)` in the tree, binds it
to its class chain with this file's own `structure()` and reads the JSON key the names are
written under (explicit string, or the constructor family's default read out of the codec
library's source); the fixture then looks each miner registry up here, so the two agree per
registry on the key, not on a shared traversal. (2) `E.C.name()` ids are evaluated against a
tree-wide ENUM INDEX (an enum is accepted only when its simple name is declared exactly once in
the tree and as an enum) instead of the miner's import-based resolution. WHAT IS SHARED, and so
not vouched for by agreement: the constructor-family decision table (a first argument that is a
string is the key; no key means the family default; `MapKeyMapCodec` has none) and the rule
that only `E.C.name()` closes (`toString()` and `(Object)E.C` stay open). The route that shares
nothing is a shipped asset: every name this closes appears as a value under its registry's key.

Usage: python3 -I maintenance/scripts/hand-registry-recount.py SRC_ROOT [--json OUT]
       python3 -I maintenance/scripts/hand-registry-recount.py SRC_ROOT --unqualified-only [--json OUT]
"""
import json, os, re, sys, collections

root = sys.argv[1]
JSON_OUT = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
UNQ_ONLY = '--unqualified-only' in sys.argv
files = {}
for d, _, fs in os.walk(root):
    for f in fs:
        if f.endswith('.java'):
            p = os.path.join(d, f)
            files[p] = open(p, encoding='utf-8', errors='replace').read()


def statement_at(text, i):
    """From index i to the ';' that ends the statement (paren/brace depth 0)."""
    depth = 0
    j = i
    while j < len(text):
        c = text[j]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth < 0:
                return text[i:j]
        elif c == ';' and depth == 0:
            return text[i:j]
        elif c == '"':
            j += 1
            while text[j] != '"':
                j += 2 if text[j] == '\\' else 1
        j += 1
    return text[i:]


def split_args(s):
    """Top-level args of the call whose '(' is s[0]."""
    depth, cur, out, k = 0, '', [], 0
    while k < len(s):
        c = s[k]
        if c == '"':
            e = k + 1
            while s[e] != '"':
                e += 2 if s[e] == '\\' else 1
            cur += s[k:e + 1]; k = e + 1; continue
        if c in '([{<':
            depth += 1
            if depth == 1 and c == '(':
                k += 1; continue
        elif c in ')]}>':
            depth -= 1
            if depth == 0 and c == ')':
                out.append(cur.strip()); return out
        elif c == ',' and depth == 1:
            out.append(cur.strip()); cur = ''; k += 1; continue
        if depth >= 1:
            cur += c
        k += 1
    return out


def consts(text):
    return dict(re.findall(r'static final String (\w+) = "([^"]*)";', text))


def reg_name(args, cs):
    """The id of one register(...) call: first literal/constant arg among the first two."""
    for a in args[:2]:
        m = re.fullmatch(r'"([^"]*)"', a)
        if m:
            return m.group(1)
        if re.fullmatch(r'[A-Z_][A-Z0-9_]*', a) and a in cs:
            return cs[a]
        if re.fullmatch(r'\w+\.class', a):
            continue
        if a.startswith('Priority.'):
            continue
    return None


def qualified_sweeps():
    global files
    # ---- Interaction.CODEC
    f1, f2, f2stmts = [], [], 0
    for p, t in files.items():
        cs = consts(t)
        for m in re.finditer(r'(?<![\w.])Interaction\.CODEC\.register\(', t):
            args = split_args(t[m.end() - 1:])
            f1.append(reg_name(args, cs))
        for m in re.finditer(r'getCodecRegistry\(Interaction\.CODEC\)', t):
            st = statement_at(t, m.end())
            f2stmts += 1
            for r in re.finditer(r'\.register\(', st):
                f2.append(reg_name(split_args(st[r.end() - 1:]), cs))
    names = set(f1) | set(f2)
    print(f"Interaction.CODEC: form1 regs {len(f1)}, form2 regs {len(f2)} in {f2stmts} stmts, "
          f"names {len(names)} (None ids: {sum(x is None for x in f1 + f2)}), overlap {len(set(f1) & set(f2))}")
    print("  NAMES", sorted(n for n in names if n))

    # ---- field table: statements per field per form
    tab = collections.defaultdict(lambda: [0, 0])
    for p, t in files.items():
        for m in re.finditer(r'getCodecRegistry\([\w.]*?\.([A-Z_]*CODEC)\)', t):
            tab[m.group(1)][0] += 1
        for m in re.finditer(r'(?<![\w])(?:[A-Z]\w*\.)+([A-Z_]*CODEC)\.register\(', t):
            tab[m.group(1)][1] += 1
    for fld in ('CODEC', 'TYPE_CODEC', 'PLUGIN_CODEC', 'PAGE_CODEC', 'OPERATION_CODEC'):
        print(f"field {fld}: form2 stmts {tab[fld][0]}, form1 stmts {tab[fld][1]}")

    # ---- core components (form 3)
    occ, sites, lit, constnamed = 0, [], 0, []
    for p, t in files.items():
        cs = consts(t)
        for m in re.finditer(r'\bregisterCoreComponentType\(', t):
            occ += 1
            args = split_args(t[m.end() - 1:])
            # a declaration: params carry types, followed by a body '{'
            after = t[m.end() - 1:]
            close = after.find(')')
            if re.match(r'\s*\{', after[close + 1:]) or re.match(r'\s*(throws|@)', after[close + 1:]):
                continue
            a0 = args[0] if args else ''
            b = re.match(r'(\w+)::new', args[1]) if len(args) > 1 else None
            if a0.startswith('"'):
                lit += 1
            elif a0 in cs:
                constnamed.append((a0, cs[a0]))
            sites.append((a0, b.group(1) if b else args[1:]))
    print(f"core components: occurrences {occ}, call sites {len(sites)}, literal ids {lit}, constant ids {constnamed}")
    conv = collections.Counter()
    nocat = []
    for a0, b in sites:
        if not a0.startswith('"') or not isinstance(b, str):
            continue
        m = re.match(r'Builder(Action|Sensor|EntityFilter|BodyMotion|HeadMotion)', b)
        if m:
            conv[m.group(1)] += 1
        else:
            nocat.append(b)
    print(f"  by name convention: {dict(conv)}, no category: {nocat}, total {sum(conv.values()) + len(nocat)}")

    # category by category() return type, following `extends` within the tree
    byname = {}
    for p, t in files.items():
        byname.setdefault(os.path.basename(p)[:-5], []).append(t)
    def category(cls, seen=()):
        ts = byname.get(cls)
        if not ts or cls in seen:
            return None, 0
        t = ts[0]
        m = re.search(r'public (?:final )?Class<(\w+)> category\(\)', t)
        if m:
            return m.group(1), 0
        e = re.search(r'class ' + cls + r'(?:<[^{]*?>)?\s+extends\s+(\w+)', t)
        if not e:
            return None, 0
        c, hops = category(e.group(1), seen + (cls,))
        return c, hops + 1
    res = collections.Counter(); inherited = 0; unres = []
    for a0, b in sites:
        if isinstance(b, str):
            c, hops = category(b)
            res[c] += 1
            inherited += hops > 0
            if c is None:
                unres.append(b)
    print(f"  by category(): {dict(res)}, resolved by inheritance {inherited}, unresolved {unres}")


if not UNQ_ONLY:
    qualified_sweeps()


# =====================================================================================
# UNQUALIFIED registrations: `CODEC.register(...)` and `getCodecRegistry(PAGE_CODEC)`
# =====================================================================================
FIELD = r'[A-Z0-9_]*CODEC'
U1 = re.compile(r'(?<![\w.$])(' + FIELD + r')\s*\.register\(')
U2 = re.compile(r'getCodecRegistry\(\s*(' + FIELD + r')\s*\)')
SELFQ = re.compile(r'(?<![\w$])(this|super)\s*\.\s*(' + FIELD + r')\s*\.register\(')
Q1 = re.compile(r'(?<![\w])((?:[A-Z]\w*\.)+)(' + FIELD + r')\.register\(')
Q2 = re.compile(r'getCodecRegistry\(\s*((?:[\w]+\.)+)(' + FIELD + r')\s*\)')
CLASSKW = re.compile(r'(?<![\w.$])(class|interface|enum)\s+(\w+)|(?<![\w.$])record\s+(\w+)\s*[(<]')
DECLARATOR = re.compile(r'(?<![\w.$])(' + FIELD + r')\s*(?:=|;|,)')
LAMBDA = re.compile(r'(?<![\w.$])FLD\s*->|\((?:[^()]*,)?\s*FLD\s*(?:,[^()]*)?\)\s*->')
NOT_TYPE = {'return', 'throw', 'new', 'else', 'case', 'assert', 'yield', 'instanceof', 'in', 'do'}
CAST_LIT = re.compile(r'\(\s*[\w.$<>?,\s]+\s*\)\s*"([^"]*)"')


def strip_noncode(t):
    """Blank comments and the CONTENTS of string/char literals (offsets and newlines
    kept). ONE left-to-right alternation, so whichever token starts first wins: a quote
    inside a comment, or `//` inside a string, is not mistaken for the other."""
    def blank(m):
        x = m.group(0)
        if x[0] in '"\'':
            return x[0] + re.sub(r'[^\n]', ' ', x[1:-1]) + x[-1]
        return re.sub(r'[^\n]', ' ', x)
    return re.sub(r"//[^\n]*|/\*.*?\*/|\"\"\"(?:\\.|[^\\])*?\"\"\"|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", blank, t, flags=re.S)


_code_cache, _structure_cache = {}, {}


def code_of(p):
    """strip_noncode of file `p`, once: the unqualified sweep and the declaration sweep both read it."""
    if p not in _code_cache:
        _code_cache[p] = strip_noncode(files[p])
    return _code_cache[p]


def classes_of(p):
    """structure() of file `p`, once. The unqualified sweep adds each class's CODEC-shaped fields to
    these dicts; the declaration sweep only reads names and nesting, so sharing them is harmless."""
    if p not in _structure_cache:
        _structure_cache[p] = structure(code_of(p))
    return _structure_cache[p]


def without_angles(text):
    """`<T extends Bar<U>>` removed (depth-counted): a type-parameter bound is no clause."""
    out, d = [], 0
    for ch in text:
        if ch == '<':
            d += 1
        elif ch == '>' and d:
            d -= 1
        elif not d:
            out.append(ch)
    return ''.join(out)


def anonymous_before(code, i):
    """True if the `{` at code[i] opens `new Type(args) {`: walk back over the balanced
    argument list and look for `new Type` in front of it."""
    j = i - 1
    while j >= 0 and code[j].isspace():
        j -= 1
    if j < 0 or code[j] != ')':
        return False
    d = 0
    while j >= 0:
        d += (code[j] == ')') - (code[j] == '(')
        if d == 0:
            break
        j -= 1
    return j > 0 and bool(re.search(r'\bnew\s+[\w.$]+(?:\s*<[^;{}()]*>)?\s*$', code[max(0, j - 160):j]))


def structure(code):
    """One forward pass over stripped code; returns the classes as dicts with name, open,
    close, iface, anon, inherits, fields (static), inst (instance) and parent (index of
    the enclosing class). A class name is read FORWARD and held as `pending` until the
    next `{` (a `;` first means it was no declaration); everything between the keyword and
    that `{` is its header, searched for an extends/implements clause once generics are
    stripped. A `{` with nothing pending is an ANONYMOUS class when it follows
    `new Type(args)` and a plain block otherwise."""
    classes, stack, pending, iface, kw_end = [], [], None, False, 0
    i, n = 0, len(code)

    def add(name, anon, inherits, ifc):
        classes.append({'name': name, 'open': i, 'close': n, 'iface': ifc, 'anon': anon,
                        'inherits': inherits, 'fields': set(), 'inst': set(),
                        'parent': next((stack[j] for j in range(len(stack) - 1, -1, -1)
                                        if stack[j] is not None), None)})
        stack.append(len(classes) - 1)

    while i < n:
        c = code[i]
        if c == '{':
            if pending:
                add(pending, False,
                    bool(re.search(r'\b(?:extends|implements)\b', without_angles(code[kw_end:i]))), iface)
            elif anonymous_before(code, i):
                add(None, True, True, False)
            else:
                stack.append(None)
            pending, iface = None, False
        elif c == '}':
            if stack:
                k = stack.pop()
                if k is not None:
                    classes[k]['close'] = i
        elif c == ';':
            pending = None
        else:
            m = CLASSKW.match(code, i) if c in 'cier' else None
            if m:
                pending = m.group(2) or m.group(3)
                iface = m.group(1) == 'interface'
                kw_end = m.end()
                i = m.end(); continue
        i += 1
    return classes


def innermost_class(classes, off):
    best = None
    for k, c in enumerate(classes):
        if c['open'] < off < c['close'] and (best is None or c['open'] > classes[best]['open']):
            best = k
    return best


def chain_of(classes, k):
    out = []
    while k is not None:
        out.append(k)
        k = classes[k]['parent']
    return out[::-1]


def member_start(code, classes, k, off):
    """Start of the class-`k` member containing `off`: just after the last ';' or '}'
    that sat at k's own body depth before `off` (so a method's parameters are in it)."""
    c = classes[k]
    depth, last = 0, c['open']
    for j in range(c['open'] + 1, off):
        ch = code[j]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                last = j
        elif ch == ';' and depth == 0:
            last = j
    return last + 1


def block_end(code, i):
    """Offset of the `}` matching the `{` at code[i]."""
    d = 0
    for z in range(i, len(code)):
        d += (code[z] == '{') - (code[z] == '}')
        if d == 0:
            return z
    return len(code)


def still_open(code, d, at):
    """Is the declaration at `d` in scope at `at`?
    A name declared inside a PARENTHESISED HEADER — a method's parameters, a `catch (E x)`,
    a `for (T x : xs)`, a lambda's `(T x) ->` — lives exactly as long as what follows the
    closing paren: the `{…}` block, or the lambda's body (a block or one expression).
    Anything else is a plain local, in scope until a `}` closes the block it sits in
    (the running brace depth from `d` never goes below zero)."""
    pd, j = 0, d
    while j < at:
        if code[j] == '(':
            pd += 1
        elif code[j] == ')':
            if pd == 0:
                break
            pd -= 1
        j += 1
    if j < at and code[j] == ')':
        k = j + 1
        while k < len(code) and code[k].isspace():
            k += 1
        if code.startswith('->', k):
            k += 2
            while code[k].isspace():
                k += 1
            body_end = (block_end(code, k) if code[k] == '{' else k + len(statement_at(code, k)))
            return at <= body_end
        if k < len(code) and code[k] == '{':
            return k < at <= block_end(code, k)
    depth = 0
    for ch in code[d:at]:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0:
                return False
    return True


def unqualified():
    sites, excluded, unresolved = [], [], []
    qualified_recv = collections.defaultdict(set)      # field -> receiver texts seen qualified
    nfiles = 0
    for p, t in sorted(files.items()):
        if '.register(' not in t:
            continue
        code = code_of(p)
        pkg = (re.search(r'^package\s+([\w.]+);', code, re.M) or [None, ''])[1]
        for m in Q1.finditer(code):
            qualified_recv[m.group(2)].add(m.group(1).rstrip('.'))
        for m in Q2.finditer(code):
            qualified_recv[m.group(2)].add(m.group(1).rstrip('.'))
        hits = [(m.start(1), 1, m.group(1)) for m in U1.finditer(code)] + \
               [(m.start(1), 2, m.group(1)) for m in U2.finditer(code)]
        for m in SELFQ.finditer(code):
            excluded.append((p, code.count('\n', 0, m.start()) + 1, m.group(2), 'this-super'))
        if not hits:
            continue
        nfiles += 1
        classes = None
        cs = consts(t)
        for at, form, fld in sorted(hits):
            if classes is None:
                classes = classes_of(p)
                for dm in DECLARATOR.finditer(code):
                    k = innermost_class(classes, dm.start(1))
                    if k is None or not enclosing_is_class(code, classes, k, dm.start(1)):
                        continue
                    seg = code[member_start(code, classes, k, dm.start(1)):dm.start(1)]
                    if seg.count('(') > seg.count(')'):      # inside a parameter list
                        continue
                    static = classes[k]['iface'] or re.search(r'\bstatic\b', seg)
                    classes[k]['fields' if static else 'inst'].add(dm.group(1))
            line = code.count('\n', 0, at) + 1
            k0 = innermost_class(classes, at)
            owner = None
            if k0 is not None:
                ms = member_start(code, classes, k0, at)
                local = re.compile(r'(?<![\w.$])([\w$.]+(?:\s*<[^;(){}=]*?>)?(?:\s*\[\s*\])*)\s+'
                                   + re.escape(fld) + r'\s*[=;,:)]')
                shadow = [lm for lm in local.finditer(code, ms, at)
                          if lm.group(1).split('.')[-1] not in NOT_TYPE
                          and still_open(code, lm.start(1), at)]
                if shadow:
                    excluded.append((p, line, fld, 'local'))
                    continue
                # an untyped lambda parameter shadows for the extent of its own body
                lam_hit = False
                for lm in re.finditer(LAMBDA.pattern.replace('FLD', fld), code[ms:at]):
                    e = ms + lm.end()
                    while code[e].isspace():
                        e += 1
                    if code[e] == '{':
                        d, z = 0, e
                        while z < len(code):
                            d += (code[z] == '{') - (code[z] == '}')
                            if d == 0:
                                break
                            z += 1
                        body_end = z
                    else:
                        body_end = e + len(statement_at(code, e))
                    lam_hit = lam_hit or ms + lm.start() < at <= body_end
                if lam_hit:
                    excluded.append((p, line, fld, 'local'))
                    continue
                verdict = None
                for k in reversed(chain_of(classes, k0)):
                    if fld in classes[k]['fields']:
                        owner, verdict = k, 'class'
                        break
                    if fld in classes[k]['inst']:
                        verdict = 'instance'
                        break
                    if classes[k]['inherits']:
                        verdict = 'inherited'
                        break
                if verdict == 'instance':
                    excluded.append((p, line, fld, 'instance-field'))
                    continue
            if owner is None:
                unresolved.append((p, line, fld))
                continue
            key = '.'.join(([pkg] if pkg else []) +
                           [classes[k]['name'] for k in chain_of(classes, owner) if classes[k]['name']] + [fld])
            # the arguments of every `.register(` in the statement the anchor starts: form 1
            # anchors at the field, form 2 at the closing paren of getCodecRegistry(FIELD)
            start = at if form == 1 else code.index(')', at) + 1
            st_args = [split_args(t[start + r.end() - 1:])
                       for r in re.finditer(r'\.register\(', t[start:start + len(statement_at(t, start))])]
            for args in st_args:
                nm, expr = unq_name(args, cs)
                sites.append({'key': key, 'field': fld, 'form': form, 'file': p, 'line': line,
                              'name': nm, 'expr': expr})
    return sites, excluded, unresolved, qualified_recv, nfiles


def enclosing_is_class(code, classes, k, off):
    """True if the innermost open brace at `off` is class k's own (not a nested block)."""
    c = classes[k]
    depth = 0
    for j in range(c['open'] + 1, off):
        ch = code[j]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    return depth == 0


ENUM_NAME = re.compile(r'((?:[A-Za-z_]\w*\.)*)([A-Z]\w*)\.(\w+)\s*\.\s*name\s*\(\s*\)')
_enum_cache = {}


def enum_lookup(e):
    """(how many types named `e` the tree declares, {path: constants} for those declared as an
    enum), found by scanning every file for the declaration of that one name. A tree-wide lookup by
    SIMPLE NAME, not the miner's import-based resolution: an enum is evaluated only when its name is
    unambiguous. Per name, cached; a raw-text prefilter keeps the full strip_noncode for the few files
    that mention the name in a declaration."""
    if e in _enum_cache:
        return _enum_cache[e]
    decl = re.compile(r'(?<![\w.$])(class|interface|enum)\s+' + re.escape(e) + r'\b'
                      r'|(?<![\w.$])record\s+' + re.escape(e) + r'\s*[(<]')
    declared, enums = 0, {}
    for p, t in files.items():
        if e not in t or not decl.search(t):
            continue
        code = code_of(p)
        for m in decl.finditer(code):
            declared += 1
            if m.group(1) == 'enum':
                b = code.find('{', m.end())
                top, d = [], 0
                for ch in code[b + 1:]:
                    if ch in '({[':
                        d += 1
                    elif ch in ')]':
                        d -= 1
                    elif ch == '}':
                        if d == 0:
                            break
                        d -= 1
                    elif ch == ';' and d == 0:
                        break
                    elif d == 0:
                        top.append(ch)
                enums[p] = re.findall(r'(?:^|,)\s*(?:@\w+\s*)*(\w+)', ''.join(top))
    _enum_cache[e] = (declared, enums)
    return _enum_cache[e]


def enum_const(a):
    """C when `a` is `E.C.name()` and E is an enum declared once in the tree with constant C."""
    m = ENUM_NAME.fullmatch(a.strip())
    if not m:
        return None
    e, c = m.group(2), m.group(3)
    declared, enums = enum_lookup(e)
    if declared != 1 or len(enums) != 1:
        return None
    return c if c in next(iter(enums.values())) else None


def unq_name(args, cs):
    """(name or None, raw expression of the id position). Literal, constant or cast
    literal among the first two arguments, as reg_name does; then an enum constant's
    `.name()`; the raw expression reported for a nameless site is the first argument
    that is not a Class or Priority."""
    for a in args[:2]:
        m = re.fullmatch(r'"([^"]*)"', a) or re.fullmatch(CAST_LIT, a)
        if m:
            return m.group(1), a
        if re.fullmatch(r'[A-Z_][A-Z0-9_]*', a) and a in cs:
            return cs[a], a
        ec = enum_const(a)
        if ec is not None:
            return ec, a
    for a in args[:2]:
        if not (re.fullmatch(r'[\w.]+\.class', a) or a.startswith('Priority.')):
            return None, a
    return None, args[0] if args else ''


def residue():
    """Registration shapes NEITHER spelling above covers, counted so the claim "nothing else
    is left" is a measurement: a registry held in a variable (`x = …getCodecRegistry(…)`
    then `x.register(…)`), and a getCodecRegistry( whose argument is not `[Receiver.]FIELD`
    — split into declarations (a method taking a codec parameter, followed by a body) and
    calls (which would be a registration this sweep cannot attribute)."""
    held, calls, decls = [], [], []
    arg_ok = re.compile(r'\s*(?:[\w.]+\.)?' + FIELD + r'\s*$')
    for p, t in sorted(files.items()):
        if 'getCodecRegistry' not in t:
            continue
        code = strip_noncode(t)
        for m in re.finditer(r'=\s*[\w.()]*getCodecRegistry\s*\(', code):
            held.append((p, code.count('\n', 0, m.start()) + 1))
        for m in re.finditer(r'getCodecRegistry\s*\(', code):
            close = code.index(')', m.end())
            if arg_ok.match(code[m.end():close]):
                continue
            row = (p, code.count('\n', 0, m.start()) + 1)
            (decls if re.match(r'\s*(\{|throws\b)', code[close + 1:]) else calls).append(row)
    return held, calls, decls


def library_defaults():
    """The constructor families' default JSON keys, read out of the codec library's own source
    with patterns that are not the miner's. None for any that cannot be read."""
    def only(basename):
        ps = [p for p in files if os.path.basename(p) == basename]
        return files[ps[0]] if len(ps) == 1 else ''
    id_ = set(re.findall(r'\bthis\(\s*"([^"]*)"\s*,\s*keyCodec', only('ACodecMapCodec.java')))
    asset = set(re.findall(r'\bsuper\(\s*"([^"]*)"', only('AssetCodecMapCodec.java')))
    fac = re.findall(r'DEFAULT_TYPE\s*=\s*"([^"]*)"', only('BuilderFactory.java'))
    return {'id': next(iter(id_)) if len(id_) == 1 else None,
            'asset': next(iter(asset)) if len(asset) == 1 else None,
            'factory': fac[0] if len(fac) == 1 else None}


def declared_keys():
    """Every `FIELD = new <X>CodecMapCodec(...)` in the tree, keyed 'pkg.Chain.FIELD', with the
    JSON key its names are written under: (key | None, how). Declaration-driven, unlike the
    miner's registration-driven walk. Also the literal type tags of every
    `new BuilderFactory<…>(Category.class, "<tag>"…)` (form 3's key by a route that does not
    read DEFAULT_TYPE)."""
    dflt = library_defaults()
    out, tags, nfiles = {}, collections.Counter(), 0
    ctor = re.compile(r'(?<![\w.$])(' + FIELD + r')\s*=\s*new\s+((?:[\w.]*\.)?(?:\w*CodecMapCodec|MapKeyMapCodec))\s*(<[^;(){}]*>)?\s*\(')
    for p, t in sorted(files.items()):
        if 'new BuilderFactory' in t:
            for m in re.finditer(r'new\s+BuilderFactory\s*<[^;]*?>\s*\(([^;]*?)\)\s*[;)]', t, re.S):
                a = split_args('(' + m.group(1) + ')')
                if len(a) >= 2:
                    q = re.fullmatch(r'"([^"]*)"', a[1])
                    tags[q.group(1) if q else '<non-literal>'] += 1
        if 'CodecMapCodec' not in t and 'MapKeyMapCodec' not in t:
            continue
        code = code_of(p)
        pkg = (re.search(r'^package\s+([\w.]+);', code, re.M) or [None, ''])[1]
        classes = None
        for m in ctor.finditer(code):
            if classes is None:
                classes = classes_of(p)
                nfiles += 1
            k0 = innermost_class(classes, m.start())
            chain = [classes[k]['name'] for k in chain_of(classes, k0) if classes[k]['name']] if k0 is not None else []
            fam = m.group(2).split('.')[-1]
            args = [a for a in split_args(t[m.end() - 1:]) if a != '']
            first = args[0] if args else ''
            lit = re.fullmatch(r'"([^"]*)"', first)
            kc = consts(t)
            if fam == 'MapKeyMapCodec':
                res = (None, 'map-key')
            elif lit:
                res = (lit.group(1), 'explicit')
            elif first in kc:
                res = (kc[first], 'constant')
            elif fam in ('CodecMapCodec', 'StringCodecMapCodec', 'BuilderCodecMapCodec') and \
                    (not args or first in ('true', 'false')):
                res = (dflt['id'], 'default') if dflt['id'] else (None, 'unknown')
            elif fam == 'ObjectCodecMapCodec' and re.match(r'(new\s|Codec\.)', first):
                res = (dflt['id'], 'default') if dflt['id'] else (None, 'unknown')
            elif fam == 'AssetCodecMapCodec' and re.match(r'(new\s|Codec\.)', first):
                res = (dflt['asset'], 'default') if dflt['asset'] else (None, 'unknown')
            else:
                res = (None, 'unknown')
            key = '.'.join(([pkg] if pkg else []) + chain + [m.group(1)])
            out.setdefault(key, set()).add(res)
    return dflt, out, tags, nfiles


sites, excluded, unresolved, qrecv, nfiles = unqualified()
r_held, r_calls, r_decls = residue()
by = collections.defaultdict(list)
for s_ in sites:
    by[s_['key']].append(s_)
classes_n = len({'.'.join(k.split('.')[:-1]) for k in by})


def has_qualified(key):
    parts = key.split('.')
    fld = parts[-1]
    chain = parts[:-1]
    # the qualified receiver text must be a suffix of the declaring chain (class names are
    # the trailing capitalised components; the package is lower-case)
    cls = [x for x in chain if x[:1].isupper()]
    return any(r.split('.') == cls[len(cls) - len(r.split('.')):] and len(r.split('.')) <= len(cls)
               for r in qrecv.get(fld, ()))


print(f"UNQUALIFIED: {len(sites)} register site(s) in {len(by)} registr(y/ies), "
      f"{classes_n} declaring class(es), {nfiles} file(s) with a hit; "
      f"{len(unresolved)} unresolved owner(s), excluded {dict(collections.Counter(e[3] for e in excluded))}")
report = {}
for key in sorted(by):
    ss = by[key]
    names = sorted({x['name'] for x in ss if x['name']})
    none = [x for x in ss if x['name'] is None]
    empty = sum(1 for x in ss if x['name'] == '')
    report[key] = {'field': ss[0]['field'], 'sites': len(ss),
                   'form1': sum(1 for x in ss if x['form'] == 1),
                   'form2': sum(1 for x in ss if x['form'] == 2),
                   'names': names, 'empty_id_sites': empty,
                   'no_name': [{'expr': x['expr'], 'file': os.path.relpath(x['file'], root),
                                'line': x['line']} for x in none],
                   'has_qualified_site': has_qualified(key)}
    r = report[key]
    print(f"  {key}: {r['sites']} site(s) (form1 {r['form1']}, form2 {r['form2']}), "
          f"{len(names)} name(s), no-name {len(none)}"
          + (f", empty-id {empty}" if empty else '')
          + ('' if r['has_qualified_site'] else '  [NEW: no qualified site]'))
    for x in r['no_name']:
        print(f"      no-name: {x['expr']!r} at {x['file']}:{x['line']}")
new_keys = sorted(k for k, r in report.items() if not r['has_qualified_site'])
print(f"NEW REGISTRY KEYS ({len(new_keys)}): none of their sites is qualified")
for k in new_keys:
    print("  ", k)
print(f"RESIDUE: registries held in a variable {len(r_held)}; getCodecRegistry( with a non-field "
      f"argument: {len(r_calls)} call(s), {len(r_decls)} declaration(s)")
dflt_keys, decl_keys, factory_tags, decl_files = declared_keys()
by_key = collections.Counter(next(iter(v)) if len(v) == 1 else ('<disagree>', 'x') for v in decl_keys.values())
print(f"DECLARED KEYS: {len(decl_keys)} registry-shaped declaration(s) in {decl_files} file(s); library defaults {dflt_keys}; "
      f"form-3 factory tags {dict(factory_tags)}")
for (k_, how_), n_ in sorted(by_key.items(), key=str):
    print(f"  key {k_!r} ({how_}): {n_}")
for e in excluded:
    print("  EXCLUDED", e[3], os.path.relpath(e[0], root), e[1], e[2])
for u in unresolved:
    print("  UNRESOLVED", os.path.relpath(u[0], root), u[1], u[2])
if JSON_OUT:
    json.dump({'sites': len(sites), 'declaring_classes': classes_n, 'unresolved': len(unresolved),
               'excluded': [{'reason': e[3], 'file': os.path.relpath(e[0], root), 'line': e[1]}
                            for e in excluded],
               'residue': {'variable_held_registries': len(r_held),
                           'non_field_argument_calls': len(r_calls),
                           'non_field_argument_declarations': len(r_decls)},
               'registries': report, 'new_keys': new_keys,
               'library_defaults': dflt_keys, 'factory_tags': dict(factory_tags),
               'declared_keys': {k_: sorted([list(x) for x in v], key=str) for k_, v in decl_keys.items()}},
              open(JSON_OUT, 'w'), indent=1, sort_keys=True)
