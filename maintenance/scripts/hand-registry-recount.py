#!/usr/bin/env python3
"""Independent (non-miner) recount of the registry fixture's hand-derived figures.

Route: plain text sweeps over decompiled source, statement = text up to the next
top-level ';'. Shares no code with registry_miner.py. After a game update, run it on the
previous build's snapshot (~/.cache/hytale-update-snapshot/src) FIRST: it must reproduce
the fixture's figures there before its output for the new build means anything. A review
tool, not a gate; see registry-oracle-notes.md §15.

Usage: python3 -I maintenance/scripts/hand-registry-recount.py SRC_ROOT
"""
import os, re, sys, collections

root = sys.argv[1]
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
