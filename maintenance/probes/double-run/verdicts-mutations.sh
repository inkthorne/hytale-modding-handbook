#!/usr/bin/env bash
# Mutation test of the 13b guards in verdicts.sh.
#   maintenance/probes/double-run/verdicts-mutations.sh GOODRUN WORKDIR [FROM TO]
#
# verdicts-test.sh damages the LOGS and checks that the judge notices. This script damages the JUDGE: for every guard in the 13b part
# of verdicts.sh (each `if`/`elif ... ; then` line after the "Item 13b" marker, and the three tests of realverdict) it writes a copy of
# verdicts.sh in which that one condition is replaced by `false` (the guard never fires), and runs verdicts-test.sh against the copy with
# VT_ONLY set to the sabotages of that guard's block. Every mutation must turn that run RED: a guard that can be deleted while its block's
# sabotages stay green is not tested by them (the rule: delete the check, run the suite, a test that stays green is not about that check).
#
# The unmutated copy is the identity control: it must stay green on every block (else the mutations prove nothing). FROM TO (1-based, inclusive)
# run a slice of the mutations (a slice of about 5 fits the 600 s foreground limit; the whole list is about 60). WORKDIR must be absent, empty, or
# carry the marker .double-run-verdicts-mutations.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
good="${1:?usage: verdicts-mutations.sh GOODRUN WORKDIR [FROM TO]}"; work="${2:?usage: verdicts-mutations.sh GOODRUN WORKDIR [FROM TO]}"
from="${3:-1}"; to="${4:-100000}"
case "$work" in /*) ;; *) echo "FAIL  WORKDIR must be absolute" >&2; exit 3;; esac
work="$(realpath -m -- "$work")"
if [ -e "$work" ] && [ ! -f "$work/.double-run-verdicts-mutations" ]; then
  if [ ! -d "$work" ] || [ -n "$(ls -A -- "$work")" ]; then echo "FAIL  WORKDIR $work exists, is not empty and has no marker; give a new path" >&2; exit 3; fi
fi
rm -rf -- "$work"; mkdir -p "$work"; : > "$work/.double-run-verdicts-mutations"

python3 -I - "$here/verdicts.sh" "$work/list.txt" <<'EOF'
import re, sys
src, out = sys.argv[1], sys.argv[2]
lines = open(src).read().split('\n')
start = next(i for i, l in enumerate(lines) if l.startswith('# Item 13b.'))
real = next(i for i, l in enumerate(lines) if l.startswith('realverdict() {'))
# case-name prefix -> regex over the sabotage labels of that block (a label names the case, or the type, or both)
KEYS = [('Explode', 'Explode'), ('Cooldown', 'Cooldown'), ('Force', 'Force'), ('Repeat', 'Repeat'), ('Clear', 'Clear'),
        ('Proj', 'Proj'), ('InvAdj', 'InvAdj|AdjustHeldItemQuantity'), ('Destroy', 'Destroy')]
REAL_KEY = 'realnpc|real NPC'
rows = []
def cond_of(l):
    m = re.match(r'^(\s*)(elif|if) (.*?); then(.*)$', l)
    return m
def emit(i, key):
    m = cond_of(lines[i])
    if not m:
        return
    cond = m.group(3)
    if cond.startswith('need ') or cond.startswith('[ "$(result_line'):
        return
    rows.append((i + 1, key, cond))
# the realverdict function: three tests
for i in range(real, real + 8):
    if re.match(r'^\s*(if|elif) ', lines[i]):
        emit(i, REAL_KEY)
cur = None
for i in range(start, real):
    l = lines[i]
    mm = re.search(r'(?:need|result_line) ([A-Za-z0-9]+)\.', l)
    if mm and re.match(r'^\s*if ', l) and ('need ' in l or 'result_line' in l):
        name = mm.group(1)
        cur = None
        for pre, key in KEYS:
            if name.startswith(pre):
                cur = key
        if 'realnpc' in l:
            cur = REAL_KEY
    if cur and re.match(r'^\s*(if|elif) ', l):
        emit(i, cur)
with open(out, 'w') as f:
    for n, key, cond in rows:
        f.write(f'{n}\t{key}\t{cond}\n')
print(len(rows), 'guards listed', file=sys.stderr)
EOF
[ -s "$work/list.txt" ] || { echo "VOID  no guard found in the 13b part of verdicts.sh (the marker or the shape changed)"; exit 2; }
total=$(wc -l < "$work/list.txt")
echo "$total guards in the 13b part of verdicts.sh"

runsuite() { # dir only-regex -> rc and the last line
  local d="$1" only="$2"
  VT_ONLY="$only" bash "$d/verdicts-test.sh" "$good" "$d/t" 2>&1
}
mkdir -p "$work/id"; cp "$here/verdicts.sh" "$here/verdicts-test.sh" "$work/id/"
if [ "$from" = 1 ]; then
  out="$(runsuite "$work/id" 'Explode|Cooldown|Force|Repeat|Clear|Proj|InvAdj|AdjustHeldItemQuantity|Destroy|realnpc|real NPC')"; rc=$?
  last=$(printf '%s\n' "$out" | tail -n 1)
  if [ "$rc" != 0 ]; then echo "VOID  the unmutated judge is not green on the 13b sabotages ($last)"; printf '%s\n' "$out" | /usr/bin/grep -v '^PASS' | sed -n 1,10p; exit 2; fi
  echo "identity: green ($last)"
fi

caught=0; survived=0; n=0
while IFS=$'\t' read -r lineno key cond; do
  n=$((n+1)); [ "$n" -ge "$from" ] && [ "$n" -le "$to" ] || continue
  d="$work/m$n"; mkdir -p "$d"; cp "$here/verdicts-test.sh" "$d/"
  python3 -I - "$here/verdicts.sh" "$d/verdicts.sh" "$lineno" <<'EOF'
import re, sys
src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
lines = open(src).read().split('\n')
m = re.match(r'^(\s*)(elif|if) (.*?); then(.*)$', lines[n - 1])
lines[n - 1] = f'{m.group(1)}{m.group(2)} false; then{m.group(4)}'
open(dst, 'w').write('\n'.join(lines))
EOF
  # the key regex selects the sabotages of that guard's block
  out="$(runsuite "$d" "$key")"; rc=$?
  last=$(printf '%s\n' "$out" | tail -n 1)
  if [ "$rc" != 0 ] && ! printf '%s\n' "$out" | /usr/bin/grep -q '^baseline: '; then
    # the unharmed logs already turn the mutated judge red: the guard is on the good run's own path (a verdict's gate), so the identity run catches it
    caught=$((caught+1)); echo "CAUGHT    #$n verdicts.sh:$lineno [$key] guard removed: $cond  (by the unharmed run: $last)"
  elif [ "$rc" != 0 ]; then caught=$((caught+1)); echo "CAUGHT    #$n verdicts.sh:$lineno [$key] guard removed: $cond  (by a sabotage: $last)"
  else survived=$((survived+1)); echo "SURVIVED  #$n verdicts.sh:$lineno [$key] guard removed: $cond  ($last)"; fi
  rm -rf -- "$d"
done < "$work/list.txt"
echo "---- $caught caught, $survived survived (of the slice $from..$to of $total)"
[ "$survived" = 0 ] && [ "$caught" -gt 0 ]
