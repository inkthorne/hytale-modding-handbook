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
#   * a stray exception        -> VOID  "exception in a run that should have none"
#   * ModifyInventory with the wait None (InvNoneSelf1): the effect doubled, or the chain not cancelled as
#     ItemChanged, or the entity removed -> FAIL; its unit control broken, or the Server-wait desync control
#     (InvSelf1.npc) not desyncing -> VOID
#   * ChangeStat with Behaviour Set read as doubled -> FAIL; its unit control broken, or the Add sensitivity
#     control (Stat1.npc reads 2 x) broken -> VOID
#   * a run that was aborted or ended in the wrong chain state still reads the predicted effect (the
#     "lands once" verdicts counted only 'Exception in thread'): a desync line, a caught tick exception
#     ("Removing!"), an entity REMOVED with reason=REMOVE, or a chain_server_state other than the prediction's,
#     in a verdict run (-> FAIL "does not count") and in a control run (-> VOID "control run"), one reason at a time
#   * the sim= flag (isUseSimulationState) of the ProbeLog lines not following the pass -> FAIL, and VOID on the control
#   * a real-NPC log whose subject was not on an NPCInteractionSimulationHandler manager -> VOID "subject's manager"
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
fresh; setfield Stat1.npc subject_SignatureCharges_delta 5.0; expect "ChangeStat read as guarded (also breaks the Set verdict's sensitivity control, so VOID)" 2 "predicted 2 x unit" 2
fresh; sed -i 's/Entity already contains component type/x/g' "$work/c/Beam2.remote.log"; expect "AttachBeam refusal line deleted from the dose control" 2 "AttachBeam dose control" 3
fresh; sed -i "/PROBE ProbeLog message='log1' pass=server/d" "$work/c/Log1.npc.log"; expect "second pass of ProbeLog deleted" 1 "Log1.npc" 1
fresh; rm -f "$work/c/Launch2.remote.log"; expect "a log is missing" 1 "no log/result" 3
fresh; echo "Exception in thread Thread[#1,WorldThread - default" >> "$work/c/Launch1.remote.log"; expect "exception in a run that should have none" 2 "exception in a run that should have none" 3
fresh; setfield StatSet1.npc subject_SignatureCharges_delta 10.0; expect "ChangeStat Set read as doubled" 1 "StatSet1.npc: read '10.0', predicted the unit" 1
fresh; setfield StatSet1.remote subject_SignatureCharges_delta 0.0; expect "ChangeStat Set unit control broken" 2 "Behaviour Set unit control: StatSet1.remote" 2
fresh; setfield Stat1.npc subject_SignatureCharges_delta 5.0; expect "ChangeStat Set sensitivity control broken (Add reads once)" 2 "Behaviour Set sensitivity control" 3
fresh; echo "[x SEVERE] [InteractionSystems\$TickInteractionManagerSystem] Exception while ticking entity interactions! Removing!" >> "$work/c/StatSet1.npc.log"; expect "ChangeStat Set run aborted" 1 "StatSet1.npc: the run does not count" 1
fresh; setfield InvNoneSelf1.npc inv_items_delta 2.0;  expect "ModifyInventory wait None read as doubled" 1 "InvNoneSelf1.npc" 1
fresh; setfield InvNoneSelf1.npc chain_server_state Finished; expect "ModifyInventory wait None not cancelled as ItemChanged" 1 "InvNoneSelf1.npc" 1
fresh; echo "[x SEVERE] [InteractionSystems\$TickInteractionManagerSystem] Exception while ticking entity interactions! Removing!" >> "$work/c/InvNoneSelf1.npc.log"; expect "ModifyInventory wait None, entity removed" 1 "InvNoneSelf1.npc" 1
fresh; echo "java.lang.IllegalStateException: Simulation and server tick are not in sync (operation position)." >> "$work/c/InvNoneSelf1.npc.log"; expect "ModifyInventory wait None, desync line" 1 "InvNoneSelf1.npc" 1
fresh; echo "[x INFO] [Log] PROBE entity with an InteractionManager REMOVED reason=REMOVE ref=Ref{index=3}" >> "$work/c/InvNoneSelf1.npc.log"; expect "ModifyInventory wait None, entity REMOVED" 1 "InvNoneSelf1.npc" 1
fresh; setfield InvNoneSelf1.remote inv_items_delta 0.0; expect "ModifyInventory wait None unit control broken" 2 "unit control: InvNoneSelf1.remote" 2
fresh; sed -i 's/not in sync/x/g' "$work/c/InvSelf1.npc.log"; expect "ModifyInventory Server-wait desync control does not desync" 2 "negative control: InvSelf1.npc" 3
# an aborted tick that the effect reads cannot show. One reason at a time, on the verdict run and on a control run.
SYNC="java.lang.IllegalStateException: Simulation and server tick are not in sync (operation position)."
REMV="[x SEVERE] [InteractionSystems\$TickInteractionManagerSystem] Exception while ticking entity interactions! Removing!"
GONE="[x INFO] [Log] PROBE entity with an InteractionManager REMOVED reason=REMOVE ref=Ref{index=3}"
addline() { printf '%s\n' "$2" >> "$work/c/$1.log"; }
fresh; addline Damage1.npc "$SYNC"; expect "Damage1.npc: a desync line" 1 "Damage1.npc: the run does not count, it has a 'not in sync'" 1
fresh; addline Damage1.npc "$REMV"; expect "Damage1.npc: a caught tick exception" 1 "Damage1.npc: the run does not count, it has a caught tick exception" 1
fresh; addline Damage1.npc "$GONE"; expect "Damage1.npc: an entity REMOVED" 1 "Damage1.npc: the run does not count, an entity was removed" 1
fresh; sed -i 's/chain_server_state=Finished/chain_server_state=NotFinished/' "$work/c/Damage1.npc.log"; expect "Damage1.npc: chain NotFinished" 1 "Damage1.npc: the run does not count, chain_server_state='NotFinished'" 1
fresh; addline Launch1.npc "$REMV"; addline Launch1.npc "$SYNC"; sed -i 's/chain_server_state=Finished/chain_server_state=NotFinished/' "$work/c/Launch1.npc.log"; expect "Launch1.npc: aborted, chain NotFinished (the reviewer's S2)" 1 "Launch1.npc: the run does not count" 1
fresh; addline Stat1.npc "$REMV"; expect "Stat1.npc: a caught tick exception" 1 "Stat1.npc: the run does not count" 1
fresh; addline Inv1.npc "$GONE"; expect "Inv1.npc: an entity REMOVED (also the Inv1.npc negative control of the desync verdicts)" 2 "Inv1.npc" 3
fresh; sed -i 's/chain_server_state=Failed/chain_server_state=Finished/' "$work/c/Damage1.remote.log"; expect "Damage1.remote control: chain not Failed" 2 "control run Damage1.remote does not count: chain_server_state='Finished', wanted Failed" 3
fresh; addline Damage2.remote "$SYNC"; expect "Damage2.remote control: a desync line" 2 "control run Damage2.remote does not count: it has a 'not in sync'" 3
fresh; addline Stat1.remote "$REMV"; expect "Stat1.remote control: a caught tick exception" 2 "control run Stat1.remote does not count: it has a caught tick exception" 3
fresh; sed -i 's/chain_server_state=Finished/chain_server_state=ItemChanged/' "$work/c/Launch2.remote.log"; expect "Launch2.remote control: chain ItemChanged" 2 "control run Launch2.remote does not count: chain_server_state='ItemChanged'" 3
fresh; sed -i '/REMOVED reason=REMOVE/d' "$work/c/InvSelf1.npc.log"; expect "InvSelf1.npc: the entity removal not logged" 1 "InvSelf1.npc: predicted the desync" 1
fresh; sed -i 's/chain_server_state=NotFinished/chain_server_state=Finished/' "$work/c/InvSelf1.npc.log"; expect "InvSelf1.npc: chain ended Finished" 1 "InvSelf1.npc: predicted the desync" 1
fresh; addline InvSelf1.remote "$SYNC"; expect "InvSelf1.remote control: a desync line" 2 "unit control: InvSelf1.remote" 3
fresh; addline InvIgnoreSelf1.npc "$GONE"; expect "InvIgnoreSelf1.npc: an entity REMOVED" 1 "InvIgnoreSelf1.npc: the run does not count" 1
fresh; addline InvIgnoreSelf1.remote "$REMV"; expect "InvIgnoreSelf1.remote control: a caught tick exception" 2 "unit control: InvIgnoreSelf1.remote" 2
fresh; addline Beam1.npc "$REMV"; expect "Beam1.npc: a caught tick exception" 1 "AttachBeam Beam1.npc:" 1
fresh; addline Beam2.remote "$SYNC"; expect "Beam2.remote control: a desync line" 2 "AttachBeam control run does not count" 3
fresh; sed -i 's/chain_server_state=Finished/chain_server_state=NotFinished/' "$work/c/Beam1.remote.log"; expect "Beam1.remote control: chain NotFinished" 2 "AttachBeam control run does not count" 3
fresh; addline Log1.npc "$REMV"; expect "Log1.npc: a caught tick exception" 1 "ProbeLog Log1.npc: the run does not count" 1
fresh; addline LogQ1.npc "$GONE"; expect "LogQ1.npc: an entity REMOVED" 1 "ProbeLogQ LogQ1.npc: the run does not count" 1
fresh; addline LogS1.npc "$SYNC"; expect "LogS1.npc: a desync line" 1 "ProbeLogS LogS1.npc: the run does not count" 1
fresh; addline Log1.remote "$SYNC"; expect "Log1.remote control: a desync line" 2 "ProbeLog unit control: Log1.remote does not count" 5
# the flag an interaction can read about its pass (context.getEntry().isUseSimulationState()) must follow the pass
fresh; sed -i "0,/pass=simulation sim=true/s//pass=simulation sim=false/" "$work/c/Log1.npc.log"; expect "Log1.npc: the simulation pass reads isUseSimulationState false" 1 "ProbeLog Log1.npc: passes 'simulation server ', isUseSimulationState 'false false '" 1
fresh; sed -i "s/pass=server sim=false/pass=server sim=true/" "$work/c/LogS1.npc.log"; expect "LogS1.npc: the server pass reads isUseSimulationState true" 1 "ProbeLogS LogS1.npc: passes 'server simulation ', isUseSimulationState 'true true '" 1
fresh; sed -i "s/pass=server sim=false/pass=server sim=true/" "$work/c/Log1.realnpc.log"; expect "Log1.realnpc: the server pass reads isUseSimulationState true" 1 "real NPC Log1: passes 'simulation server ', isUseSimulationState 'true true '" 1
fresh; sed -i "s/pass=server sim=false/pass=server sim=true/" "$work/c/Log1.remote.log"; expect "Log1.remote control: the server pass reads isUseSimulationState true" 2 "ProbeLog unit control: Log1.remote has" 5
fresh; addline Log1.realnpc "$REMV"; expect "Log1.realnpc: a caught tick exception" 2 "Log1.realnpc does not count" 1
fresh; addline Stat1.realnpc "$REMV"; expect "Stat1.realnpc: a caught tick exception" 2 "real NPC Stat1 does not count" 1
fresh; addline Damage1.realnpc "$GONE"; expect "Damage1.realnpc: an entity REMOVED" 2 "real NPC Damage1 does not count" 1
fresh; addline Beam1.realnpc "$SYNC"; expect "Beam1.realnpc: a desync line" 1 "AttachBeam Beam1.realnpc:" 1
# the subject of a real-NPC case must be on an NPC manager (the reviewer's S3), each case on its own
for c in Stat1 Damage1 Beam1 Log1; do
  fresh; sed -i 's/simulationHandler=NPCInteractionSimulationHandler/simulationHandler=InteractionSimulationHandler/; s/DR manager=realnpc/DR manager=remote/' "$work/c/$c.realnpc.log"
  if [ "$c" = Beam1 ]; then expect "$c.realnpc: subject not on an NPC manager" 1 "AttachBeam Beam1.realnpc:" 1
  elif [ "$c" = Log1 ]; then expect "$c.realnpc: subject not on an NPC manager" 2 "Log1.realnpc: the subject's manager" 1
  else expect "$c.realnpc: subject not on an NPC manager" 2 "real NPC $c: the subject's manager" 1; fi
done
echo "---- $fails failed"
[ "$fails" = 0 ]
