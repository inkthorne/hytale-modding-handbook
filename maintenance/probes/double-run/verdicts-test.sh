#!/usr/bin/env bash
# Sabotage test of verdicts.sh.   maintenance/probes/double-run/verdicts-test.sh GOODRUN WORKDIR
#
# GOODRUN is a scratch directory run.sh filled with every case (verdicts.sh must print "0 failed, 0 void" on
# it). WORKDIR must be absent, empty, or one this script made (marker .double-run-verdicts-test); a copy of the
# logs is made there and damaged one way at a time. Each damage must turn the named verdict into the named
# outcome (VOID or FAIL, with the message fragment), and the unharmed copy must still be clean:
#   * the baseline copy must be clean, else the test is VOID itself (a sabotage on a dirty copy proves nothing)
#   * dose control broken      -> VOID  "dose control"
#   * unit control broken      -> VOID  "unit control"
#   * a doubled effect where the guard predicts one -> FAIL "predicted 1 x unit"
#   * a refusal line deleted   -> VOID  "AttachBeam dose control"
#   * the second pass of the NPC-shaped ProbeLog deleted -> FAIL "passes 'server'" (only one line left)
#   * a missing log            -> FAIL  "no log/result"
# Each case also checks that the sabotaged verdict line is the ONLY change: the other verdict blocks keep their
# PASS count (a damage that turns everything red would pass the checks above for the wrong reason).
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
good="${1:?usage: verdicts-test.sh GOODRUN WORKDIR}"; work="${2:?usage: verdicts-test.sh GOODRUN WORKDIR}"
case "$work" in /*) ;; *) echo "FAIL  WORKDIR must be absolute" >&2; exit 3;; esac
work="$(realpath -m -- "$work")"
if [ -e "$work" ] && [ ! -f "$work/.double-run-verdicts-test" ]; then
  if [ ! -d "$work" ] || [ -n "$(ls -A -- "$work")" ]; then echo "FAIL  WORKDIR $work exists, is not empty and has no marker; give a new path" >&2; exit 3; fi
fi
rm -rf -- "$work"; mkdir -p "$work"; : > "$work/.double-run-verdicts-test"
fresh() { rm -rf "$work/c"; mkdir "$work/c"; cp -a "$good"/. "$work/c"/; }
fresh
base="$(bash "$here/verdicts.sh" "$work/c")"; brc=$?
npass=$(printf '%s\n' "$base" | /usr/bin/grep -c '^PASS')
if [ "$brc" != 0 ] || [ "$npass" -lt 10 ]; then echo "VOID  the unharmed copy is not clean (rc $brc, $npass PASS)"; printf '%s\n' "$base" | /usr/bin/grep -v '^PASS'; exit 2; fi
echo "baseline: $npass PASS, rc 0"
fails=0
# edit the DR RESULT line of a case: field=value
setfield() { # case field value
  sed -i "s/\\( $2=\\)[^ ]*/\\1$3/" "$work/c/$1.log"
}
expect() { # label, wanted-rc, fragment, expected-PASS-count-lost
  local out rc lost
  out="$(bash "$here/verdicts.sh" "$work/c")"; rc=$?
  lost=$(( npass - $(printf '%s\n' "$out" | /usr/bin/grep -c '^PASS') ))
  if [ "$rc" = "$2" ] && printf '%s\n' "$out" | /usr/bin/grep -qF -- "$3" && [ "$lost" -ge 1 ] && [ "$lost" -le "$4" ]; then
    echo "PASS  $1: rc $rc, '$3', $lost PASS line(s) lost"
  else echo "FAIL  $1: rc $rc (wanted $2), fragment '$3' present: $(printf '%s\n' "$out" | /usr/bin/grep -cF -- "$3"), PASS lost $lost (wanted 1..$4)"; fails=$((fails+1)); fi
}
fresh; setfield Damage2.remote target_health_delta -3.0; expect "DamageEntity dose control broken" 2 "dose control" 3
fresh; setfield Damage1.remote target_health_delta 0.0;   expect "DamageEntity unit control broken" 2 "unit control" 3
fresh; setfield Damage1.npc target_health_delta -6.0;     expect "DamageEntity doubled on the NPC-shaped manager" 1 "predicted 1 x unit" 1
fresh; setfield Stat1.npc subject_SignatureCharges_delta 5.0; expect "ChangeStat read as guarded" 1 "predicted 2 x unit" 1
fresh; sed -i 's/Entity already contains component type/x/g' "$work/c/Beam2.remote.log"; expect "AttachBeam refusal line deleted from the dose control" 2 "AttachBeam dose control" 3
fresh; sed -i "/PROBE ProbeLog message='log1' pass=server/d" "$work/c/Log1.npc.log"; expect "second pass of ProbeLog deleted" 1 "Log1.npc" 1
fresh; rm -f "$work/c/Launch2.remote.log"; expect "a log is missing" 1 "no log/result" 3
fresh; echo "Exception in thread Thread[#1,WorldThread - default" >> "$work/c/Launch1.remote.log"; expect "exception in a run that should have none" 2 "exception in a run that should have none" 3
echo "---- $fails failed"
[ "$fails" = 0 ]
