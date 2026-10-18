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
# Only the logs and result files are copied: verdicts.sh reads nothing else, and the case directories (universe, mods) of a good run weigh a gigabyte.
fresh() { rm -rf "$work/c"; mkdir "$work/c"; cp -a "$good"/*.log "$good"/*.result "$work/c"/; }
fresh
base="$(bash "$here/verdicts.sh" "$work/c")"; brc=$?
npass=$(printf '%s\n' "$base" | /usr/bin/grep -c '^PASS')
if [ "$brc" != 0 ] || [ "$npass" -lt 10 ]; then echo "VOID  the unharmed copy is not clean (rc $brc, $npass PASS)"; printf '%s\n' "$base" | /usr/bin/grep -v '^PASS'; exit 2; fi
echo "baseline: $npass PASS, rc 0"
fails=0; nrun=0
# edit the DR RESULT line of a case: field=value
setfield() { # case field value
  sed -i "s/\\( $2=\\)[^ ]*/\\1$3/" "$work/c/$1.log"
}
expect() { # label, wanted-rc, fragment, expected-PASS-count-lost
  # VT_ONLY=REGEX runs only the sabotages whose label matches (verdicts-mutations.sh uses it to run one block's cases per mutation)
  if [ -n "${VT_ONLY:-}" ] && ! printf '%s' "$1" | /usr/bin/grep -Eq -- "$VT_ONLY"; then return 0; fi
  nrun=$((nrun+1))
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

# ---------------------------------------------------------------------------------------------------------------------
# Item 13b: a sabotage for each new verdict. Same rule: the damaged verdict turns VOID (a control) or FAIL (the verdict) with the message,
# and at most the PASS lines of its own block go.
# Explode (a block of three PASS lines: controls, the health verdict, the event count)
fresh; setfield Explode2.remote target_health_delta -1.0; expect "Explode dose control broken" 2 "Explode (doubled) dose control" 3
fresh; setfield Explode1.remote target_health_delta 0.0; expect "Explode unit control broken" 2 "Explode (doubled) unit control" 3
fresh; setfield Explode1.npc target_health_delta -1.0; expect "Explode read as once" 1 "Explode1.npc: read -1.0, predicted 2 x unit" 1
fresh; setfield Explode1.npc damage_other_raised 1; expect "Explode raised one event" 1 "Explode1.npc raised 1 Damage event(s) at the target, predicted 2" 1
fresh; setfield Explode2.remote damage_other_raised 1; expect "Explode event counter broken on the dose control" 2 "Explode event counter" 1
fresh; addline Explode1.npc "$SYNC"; expect "Explode1.npc: a desync line" 1 "Explode1.npc: the run does not count" 1
fresh; addline Explode1.remote "$REMV"; expect "Explode1.remote control: a caught tick exception" 2 "control run Explode1.remote does not count" 3
fresh; sed -i 's/chain_server_state=Finished/chain_server_state=Failed/' "$work/c/Explode2.remote.log"; expect "Explode2.remote control: chain Failed" 2 "control run Explode2.remote does not count" 3
fresh; rm -f "$work/c/Explode1.npc.log"; expect "Explode1.npc log missing" 1 "no log/result for case Explode1.npc" 3
fresh; setfield Explode1.realnpc damage_other_raised 1; expect "real NPC Explode raised one event" 1 "real NPC (Chicken hits a Sheep) Explode: read '1', predicted 2" 1
fresh; sed -i 's/simulationHandler=NPCInteractionSimulationHandler/simulationHandler=InteractionSimulationHandler/; s/DR manager=realnpc/DR manager=remote/' "$work/c/Explode1.realnpc.log"; expect "Explode1.realnpc: subject not on an NPC manager" 2 "Explode: the subject's manager" 1
fresh; addline Explode1.realnpc "$GONE"; expect "Explode1.realnpc: an entity REMOVED" 2 "real NPC (Chicken hits a Sheep) Explode does not count" 1
# TriggerCooldown (controls, the 3-charge verdict, the 1-charge verdict)
fresh; setfield Cooldown2.remote cooldown_charges 2.0; expect "TriggerCooldown dose control broken" 2 "TriggerCooldown dose control" 3
fresh; setfield Cooldown1.remote cooldown_charges 3.0; expect "TriggerCooldown unit control broken (nothing used)" 2 "TriggerCooldown unit control: Cooldown1.remote" 4
fresh; setfield CooldownOne1.remote cooldown_charges 1.0; expect "TriggerCooldown one-charge unit control broken" 2 "TriggerCooldown unit control: CooldownOne1.remote" 3
fresh; setfield Cooldown1.npc cooldown_charges 2.0; expect "TriggerCooldown read as once with 3 charges" 1 "Cooldown1.npc: used '1' of 3 charges, predicted 2 x the unit" 1
fresh; setfield CooldownOne1.npc cooldown_charges -1.0; expect "TriggerCooldown read as doubled with 1 charge" 1 "CooldownOne1.npc: used '2' of 1 charge, predicted the unit" 1
fresh; addline Cooldown1.npc "$SYNC"; expect "Cooldown1.npc: a desync line" 1 "TriggerCooldown Cooldown1.npc: the run does not count" 1
fresh; addline CooldownOne1.npc "$REMV"; expect "CooldownOne1.npc: a caught tick exception" 1 "TriggerCooldown CooldownOne1.npc: the run does not count" 1
fresh; addline Cooldown1.remote "$REMV"; expect "Cooldown1.remote control: a caught tick exception" 2 "TriggerCooldown control run does not count" 3
fresh; echo "Exception in thread Thread[#1,WorldThread - default" >> "$work/c/Cooldown1.npc.log"; expect "Cooldown1.npc: an exception" 2 "TriggerCooldown: an exception in a run that should have none" 3
fresh; setfield Cooldown1.realnpc cooldown_charges 2.0; expect "real NPC TriggerCooldown read as once" 1 "real NPC TriggerCooldown (3 charges): read '1', predicted 2" 1
# ApplyForce (controls, the verdict)
fresh; setfield Force2.npc force_instructions 5.0; expect "ApplyForce dose control broken" 2 "ApplyForce dose control" 2
fresh; setfield Force1.remote force_instructions 5.0; expect "ApplyForce flagged manager applied a force" 2 "ApplyForce flagged control" 2
fresh; setfield Force1.npc force_instructions 10.0; expect "ApplyForce read as doubled" 1 "ApplyForce Force1.npc: read '10.0'" 1
fresh; setfield Force1.npc force_instructions 0.0; expect "ApplyForce read as never applied" 1 "ApplyForce Force1.npc: read '0.0'" 1
fresh; sed -i 's/chain_server_state=Failed/chain_server_state=Finished/' "$work/c/Force1.remote.log"; expect "Force1.remote control: chain Finished" 2 "ApplyForce control run does not count" 2
fresh; addline Force1.npc "$GONE"; expect "Force1.npc: an entity REMOVED" 1 "ApplyForce Force1.npc: the run does not count" 1
# Repeat (a block of two PASS lines)
fresh; setfield Repeat2.remote projectiles 1; expect "Repeat dose control broken" 2 "Repeat (guarded) dose control" 2
fresh; setfield Repeat1.remote projectiles 0; expect "Repeat unit control broken" 2 "Repeat (guarded) unit control" 3
fresh; setfield Repeat1.npc projectiles 2; expect "Repeat read as doubled" 1 "Repeat1.npc: read 2, predicted 1 x unit" 1
fresh; sed -i 's/chain_server_state=Failed/chain_server_state=Finished/' "$work/c/Repeat1.remote.log"; expect "Repeat1.remote control: chain Finished" 2 "control run Repeat1.remote does not count" 2
fresh; addline Repeat1.npc "$REMV"; expect "Repeat1.npc: a caught tick exception" 1 "Repeat1.npc: the run does not count" 1
fresh; setfield Repeat1.realnpc projectiles 2; expect "real NPC Repeat read as doubled" 1 "real NPC Repeat: read '2', predicted 1" 1
# ClearEntityEffect
fresh; setfield Clear0.npc effect_present 0.0; expect "ClearEntityEffect negative control broken (nothing to see)" 2 "ClearEntityEffect negative control" 2
fresh; setfield Clear1.remote effect_present 1.0; expect "ClearEntityEffect unit control broken" 2 "ClearEntityEffect unit control" 1
fresh; setfield Clear1.npc effect_present 1.0; expect "ClearEntityEffect effect left on the NPC-shaped manager" 1 "Clear1.npc: effect_present '1.0', predicted 0.0" 1
fresh; addline Clear1.npc "$SYNC"; expect "Clear1.npc: a desync line" 1 "ClearEntityEffect Clear1.npc: the run does not count" 1
fresh; addline Clear0.npc "$REMV"; expect "Clear0.npc control: a caught tick exception" 2 "ClearEntityEffect control run does not count" 2
fresh; setfield Clear1.realnpc effect_present 1.0; expect "real NPC ClearEntityEffect left the effect" 1 "real NPC ClearEntityEffect: read '1.0', predicted 0" 1
# Projectile
fresh; setfield Proj1.remote projectiles_new 1; expect "Projectile flagged manager spawned one" 2 "Projectile flagged control" 1
fresh; setfield Proj2.npc projectiles_new 1; expect "Projectile dose control broken" 2 "Projectile dose control" 2
fresh; setfield Proj1.npc projectiles_new 2; expect "Projectile read as doubled" 1 "Proj1.npc: read '2' projectile entities, predicted 1" 1
fresh; sed -i 's/chain_server_state=Failed/chain_server_state=Finished/' "$work/c/Proj1.remote.log"; expect "Proj1.remote control: chain Finished" 2 "Projectile control run does not count" 1
fresh; addline Proj1.npc "$REMV"; expect "Proj1.npc: a caught tick exception" 1 "Projectile Proj1.npc: the run does not count" 1
fresh; setfield Proj1.realnpc projectiles_new 2; expect "real NPC Projectile read as doubled" 1 "real NPC Projectile: read '2', predicted 1" 1
# ModifyInventory AdjustHeldItemQuantity
fresh; setfield InvAdjSelf2.remote inv_items_delta -1.0; expect "AdjustHeldItemQuantity dose control broken" 2 "AdjustHeldItemQuantity dose control" 3
fresh; setfield InvAdjSelf1.remote inv_items_delta 0.0; expect "AdjustHeldItemQuantity unit control broken" 2 "AdjustHeldItemQuantity unit control: InvAdjSelf1.remote" 3
fresh; setfield InvAdjOneSelf1.remote inv_items_delta -2.0; expect "AdjustHeldItemQuantity stack-of-1 unit control broken" 2 "AdjustHeldItemQuantity unit control: InvAdjOneSelf1.remote" 3
fresh; setfield InvAdjSelf1.npc inv_items_delta -1.0; expect "AdjustHeldItemQuantity read as once" 1 "InvAdjSelf1.npc: read '-1.0', predicted 2 x the unit" 1
fresh; setfield InvAdjOneSelf1.npc inv_items_delta -2.0; expect "AdjustHeldItemQuantity stack of 1 read as doubled" 1 "InvAdjOneSelf1.npc: read '-2.0', predicted the unit" 1
fresh; addline InvAdjSelf1.npc "$SYNC"; expect "InvAdjSelf1.npc: a desync line" 1 "InvAdjSelf1.npc: the run does not count" 1
fresh; addline InvAdjSelf1.remote "$GONE"; expect "InvAdjSelf1.remote control: an entity REMOVED" 2 "AdjustHeldItemQuantity control run does not count" 3
# DestroyBlock
fresh; setfield Destroy1.remote break_events 0; expect "DestroyBlock unit control broken (no event)" 2 "DestroyBlock unit control" 2
fresh; setfield Destroy1.remote block_id_after 953; expect "DestroyBlock unit control broken (block still there)" 2 "DestroyBlock unit control" 2
fresh; setfield Destroy2.remote break_events 2; expect "DestroyBlock second-break control broken" 2 "DestroyBlock second-break control" 2
fresh; setfield Destroy1.npc break_events 2; expect "DestroyBlock read as broken twice" 1 "DestroyBlock Destroy1.npc: raised '2' BreakBlockEvent(s)" 1
fresh; setfield Destroy1.npc block_id_after 953; expect "DestroyBlock left the block" 1 "DestroyBlock Destroy1.npc: raised '1' BreakBlockEvent(s), block '953' -> '953'" 1
fresh; addline Destroy1.npc "$GONE"; expect "Destroy1.npc: an entity REMOVED" 1 "DestroyBlock Destroy1.npc: the run does not count" 1
fresh; setfield Destroy1.realnpc break_events 2; expect "real NPC DestroyBlock read as broken twice" 1 "real NPC DestroyBlock: read '2', predicted 1" 1
# exception in a run that should have none: one per custom block (the guard is one condition; Explode and Repeat use block(), tested above)
EXC="Exception in thread Thread[#1,WorldThread - default"
fresh; echo "$EXC" >> "$work/c/Force1.npc.log"; expect "ApplyForce: an exception in a run that should have none" 2 "ApplyForce: an exception in a run that should have none" 2
fresh; echo "$EXC" >> "$work/c/Clear1.npc.log"; expect "ClearEntityEffect: an exception in a run that should have none" 2 "ClearEntityEffect: an exception in a run that should have none" 2
fresh; echo "$EXC" >> "$work/c/Proj1.npc.log"; expect "Projectile: an exception in a run that should have none" 2 "Projectile: an exception in a run that should have none" 1
fresh; echo "$EXC" >> "$work/c/InvAdjSelf1.npc.log"; expect "AdjustHeldItemQuantity: an exception in a run that should have none" 2 "AdjustHeldItemQuantity: an exception in a run that should have none" 3
fresh; echo "$EXC" >> "$work/c/Destroy1.npc.log"; expect "DestroyBlock: an exception in a run that should have none" 2 "DestroyBlock: an exception in a run that should have none" 2
fresh; addline InvAdjOneSelf1.npc "$REMV"; expect "InvAdjOneSelf1.npc: a caught tick exception" 1 "InvAdjOneSelf1.npc: the run does not count" 1
fresh; addline Destroy1.remote "$SYNC"; expect "Destroy1.remote control: a desync line" 2 "DestroyBlock control run does not count" 3
fresh; addline Destroy2.remote "$REMV"; expect "Destroy2.remote control: a caught tick exception" 2 "DestroyBlock control run does not count" 3
echo "---- $fails failed, $nrun sabotage(s) run"
[ "$nrun" -gt 0 ] && [ "$fails" = 0 ]
