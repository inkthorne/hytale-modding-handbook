#!/usr/bin/env bash
# Judge the logs run.sh left in SCRATCH.   maintenance/probes/double-run/verdicts.sh SCRATCH
#
# Every verdict is a read of a "DR RESULT" line (or the lines named below) and is preceded by the
# controls that show the probe could see the outcome it reports:
#   unit control   the type once on the remote-client manager reads exactly one unit
#   dose control   the type twice in one chain on the remote-client manager reads two units
# A control that fails makes the verdict VOID (exit 2) and the verdict after it is not printed. A verdict
# that disagrees with the README's prediction is FAIL (exit 1). A missing log is a FAIL, not a skip.
# The effect is read at the target (health, stat, inventory, projectile entities, BeamComponents); the
# ProbeLog* cases are plugin types whose declared effect IS one log line, and are marked as such.
set -u
scratch="${1:?usage: verdicts.sh SCRATCH}"
fails=0; void=0
strip() { sed 's/\x1b\[[0-9;]*m//g' "$scratch/$1.log" 2>/dev/null; }
have() { [ -s "$scratch/$1.log" ] && [ -s "$scratch/$1.result" ]; }
ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fails=$((fails+1)); }
voidc() { printf 'VOID  control did not hold: %s\n' "$1"; void=$((void+1)); }
count() { strip "$1" | /usr/bin/grep -c -- "$2"; }
need() { for c in "$@"; do have "$c" || { bad "no log/result for case $c in $scratch"; return 1; }; done; }
# field NAME of the single "DR RESULT" line of a case; empty when there is none or more than one
result_line() { local n; n=$(strip "$1" | /usr/bin/grep -c 'PROBE DR RESULT '); [ "$n" = 1 ] && strip "$1" | /usr/bin/grep 'PROBE DR RESULT '; }
field() { printf '%s\n' "$1" | sed -n "s/.* $2=\([^ ]*\).*/\1/p"; }
feq() { awk -v a="$1" -v b="$2" 'BEGIN{ exit !(a != "" && b != "" && a+0 == b+0 && a != "NaN" && b != "NaN") }'; }
fmul() { awk -v a="$1" -v k="$2" 'BEGIN{ printf "%g", a*k }'; }
fneg() { awk -v a="$1" 'BEGIN{ exit !(a != "" && a != "NaN" && a+0 < 0) }'; }
fpos() { awk -v a="$1" 'BEGIN{ exit !(a != "" && a != "NaN" && a+0 > 0) }'; }
exceptions() { count "$1" 'Exception in thread'; }
# A run counts only if no tick was aborted and its chain ended in the state its prediction names. "Exception in thread"
# is the world thread dying; a tick that is caught and ends the entity prints none of that, but leaves one of these three
# lines: the desync, TickInteractionManagerSystem's "Removing!", or the probe's REMOVED reason=REMOVE (a shutdown or an
# unloaded section is reason=UNLOAD). The state is the chain_server_state of the single DR RESULT line; WANTED '-' is for the
# refusals, whose world thread dies before the line is written.
# flawed CASE WANTED: prints why the run does not count and returns 0, or prints nothing and returns 1.
flawed() {
  if [ "$(count "$1" 'not in sync')" != 0 ]; then echo "it has a 'not in sync' desync line"; return 0; fi
  if [ "$(count "$1" 'Exception while ticking entity interactions! Removing!')" != 0 ]; then echo "it has a caught tick exception ('Removing!')"; return 0; fi
  if [ "$(count "$1" 'REMOVED reason=REMOVE')" != 0 ]; then echo "an entity was removed (reason=REMOVE)"; return 0; fi
  if [ "$2" != - ] && [ "$(field "$(result_line "$1")" chain_server_state)" != "$2" ]; then
    echo "chain_server_state='$(field "$(result_line "$1")" chain_server_state)', wanted $2"; return 0; fi
  return 1
}
# The subject's manager: the single "DR manager=" line of a real NPC case names the manager it ran on.
realnpc_manager() { strip "$1" | /usr/bin/grep -q 'PROBE DR manager=realnpc self=false simulationHandler=NPCInteractionSimulationHandler'; }

# R4 of item 12: the harness boots at all.
if need boot; then
  [ "$(count boot 'Hytale Server Booted!')" = 1 ] && ok "boot: the server boots headless with the probe's scratch layout" || bad "boot"
fi

# A generic effect block. NAME UNITFIELD UNIT-SIGN LABEL
#   cases NAME1.remote (unit control), NAME2.remote (dose control), NAME1.npc (verdict), expected npc multiple.
#   RSTATE and NSTATE are the chain_server_state the remote runs and the NPC-shaped run end in (see flawed): DamageEntity
#   needs a client to finish its chain on the remote-client manager, which never comes, so those runs end Failed after the
#   effect has landed (README); every other control ends Finished. A run that was aborted does not count, whatever it read.
block() {
  local name="$1" f="$2" label="$3" expect="$4" what="$5" rstate="$6" nstate="$7" why c
  need "${name}1.remote" "${name}2.remote" "${name}1.npc" || return
  local r1 r2 rn u1 u2 un
  r1=$(result_line "${name}1.remote"); r2=$(result_line "${name}2.remote"); rn=$(result_line "${name}1.npc")
  if [ -z "$r1" ] || [ -z "$r2" ] || [ -z "$rn" ]; then bad "$label: a case has no single DR RESULT line"; return; fi
  u1=$(field "$r1" "$f"); u2=$(field "$r2" "$f"); un=$(field "$rn" "$f")
  if [ "$(exceptions "${name}1.remote")" != 0 ] || [ "$(exceptions "${name}2.remote")" != 0 ] || [ "$(exceptions "${name}1.npc")" != 0 ]; then
    voidc "$label: an exception in a run that should have none"; return; fi
  for c in "${name}1.remote" "${name}2.remote"; do
    if why=$(flawed "$c" "$rstate"); then voidc "$label: control run $c does not count: $why"; return; fi
  done
  if [ "$f" = target_health_delta ]; then
    # damage is negative: the unit is the (negative) delta of one hit; compare as multiples of it
    fneg "$u1" || { voidc "$label unit control: $name 1 on remote read $u1, wanted a drop"; return; }
  else
    fpos "$u1" || { voidc "$label unit control: ${name}1.remote read $u1, wanted a positive count"; return; }
  fi
  if ! feq "$u2" "$(fmul "$u1" 2)"; then voidc "$label dose control: ${name}2.remote read $u2, wanted 2 x $u1 (a second copy in the chain did not land)"; return; fi
  ok "$label controls: one on remote reads $u1, two on remote read $u2"
  if why=$(flawed "${name}1.npc" "$nstate"); then bad "$label ${name}1.npc: the run does not count, $why"; return; fi
  if feq "$un" "$(fmul "$u1" "$expect")"; then ok "$label ${name}1.npc: $un = $expect x unit ($what)"
  else bad "$label ${name}1.npc: read $un, predicted $expect x unit ($u1) ($what)"; fi
}

block Damage target_health_delta "DamageEntity (guarded)" 1 "the second pass finds QUEUED_DAMAGE and does not damage again" Failed Finished
if [ "$(result_line Damage1.remote)" ] && [ "$(result_line Damage2.remote)" ] && [ "$(result_line Damage1.npc)" ]; then
  ev1=$(field "$(result_line Damage1.remote)" damage_raised); ev2=$(field "$(result_line Damage2.remote)" damage_raised); evn=$(field "$(result_line Damage1.npc)" damage_raised)
  if [ "$ev1" = 1 ] && [ "$ev2" = 2 ]; then
    [ "$evn" = 1 ] && ok "DamageEntity Damage1.npc: exactly 1 Damage event was raised on the NPC-shaped manager (remote: 1 and 2 for one and two)" || bad "DamageEntity Damage1.npc raised $evn Damage event(s), predicted 1"
  else voidc "DamageEntity event counter: Damage1.remote raised '$ev1', Damage2.remote '$ev2' (wanted 1 and 2)"; fi
fi
block Launch projectiles "LaunchProjectile" 1 "simulateFirstRun is empty" Finished Finished
block Stat subject_SignatureCharges_delta "ChangeStat (doubled)" 2 "firstRun runs in both passes and adds directly" Finished Finished
# ChangeStat with "Behaviour": "Set" sets the stat to a value, so a second pass gives the same result: one unit, not two.
# Unit control: StatSet1.remote reads a positive unit. Sensitivity control: on the same harness and manager Stat1.npc
# (Behaviour Add, the default) reads two units, so a double run would have shown.
if need StatSet1.remote StatSet1.npc Stat1.remote Stat1.npc; then
  u=$(field "$(result_line StatSet1.remote)" subject_SignatureCharges_delta); n=$(field "$(result_line StatSet1.npc)" subject_SignatureCharges_delta); why=""
  if ! fpos "$u" || why=$(flawed StatSet1.remote Finished); then voidc "ChangeStat Behaviour Set unit control: StatSet1.remote read '$u'; ${why:-it is sound}"
  elif ! feq "$(field "$(result_line Stat1.npc)" subject_SignatureCharges_delta)" "$(fmul "$(field "$(result_line Stat1.remote)" subject_SignatureCharges_delta)" 2)"; then
    voidc "ChangeStat Behaviour Set sensitivity control: Stat1.npc (Add) did not read 2 x Stat1.remote on this harness"
  elif why=$(flawed StatSet1.npc Finished); then bad "ChangeStat Behaviour Set StatSet1.npc: the run does not count, $why"
  elif feq "$n" "$u"; then ok "ChangeStat Behaviour Set StatSet1.npc: $n = the unit $u, not 2 x (setting a stat to a value gives the same result twice; Add on the same harness reads 2 x)"
  else bad "ChangeStat Behaviour Set StatSet1.npc: read '$n', predicted the unit $u"; fi
fi
block Inv inv_items_delta "ModifyInventory (Server wait, doubled)" 2 "firstRun runs in both passes, server pass first" Finished Finished

# ModifyInventory with owner == running entity (the context ActionAttack builds). PREDICTED: the item-change
# check skips the second pass, so 1 egg. MEASURED: the pass that was skipped leaves the simulated operation
# counter behind, and doTickChain throws "Simulation and server tick are not in sync (operation position)";
# TickInteractionManagerSystem catches it and removes the entity. The effect cannot be read afterwards (the
# entity that holds the inventory is gone), which is why the verdict is the desync and the removal.
if need InvSelf1.remote InvSelf1.npc Inv1.npc; then
  u=$(field "$(result_line InvSelf1.remote)" inv_items_delta); why=""
  if ! fpos "$u" || why=$(flawed InvSelf1.remote Finished); then
    voidc "ModifyInventory (owner == entity) unit control: InvSelf1.remote read '$u'; ${why:-it is sound}"
  elif why=$(flawed Inv1.npc Finished); then
    voidc "ModifyInventory desync negative control: Inv1.npc (proxy context) does not count: $why"
  elif [ "$(count InvSelf1.npc 'Simulation and server tick are not in sync (operation position)')" -ge 1 ] \
       && [ "$(count InvSelf1.npc 'Exception while ticking entity interactions! Removing!')" -ge 1 ] \
       && [ "$(count InvSelf1.npc 'REMOVED reason=REMOVE')" -ge 1 ] && [ "$(field "$(result_line InvSelf1.npc)" chain_server_state)" = NotFinished ]; then
    ok "ModifyInventory, owner == running entity: DESYNC. 'Simulation and server tick are not in sync (operation position)', then TickInteractionManagerSystem removes the entity (the one-pass control reads $u)"
  else bad "ModifyInventory InvSelf1.npc: predicted the desync, 'Removing!', the entity REMOVED and chain_server_state=NotFinished; read $(count InvSelf1.npc 'not in sync') desync line(s), $(count InvSelf1.npc 'Removing!') 'Removing!', $(count InvSelf1.npc 'REMOVED reason=REMOVE') removal(s), chain_server_state=$(field "$(result_line InvSelf1.npc)" chain_server_state)"; fi
fi

# The wait decides which pass runs first, and so what the item-change check does. The same chain with only
# getWaitForDataFrom() changed from Server to None (the plugin's ProbeInvNone type): the simulation pass runs first and
# puts the item in the held slot; the server pass then sees a changed held item, ends the chain as ItemChanged
# (Interaction.tick throws ChainCancelledException, which tickChain catches) and never calls tick0. The effect lands once,
# the passes do not desync and the entity is kept. Unit control: the same type on the remote-client manager reads one
# item and finishes. Negative control: InvSelf1.npc, the Server-wait version of the chain, desyncs on the same harness.
if need InvNoneSelf1.remote InvNoneSelf1.npc InvSelf1.npc; then
  u=$(field "$(result_line InvNoneSelf1.remote)" inv_items_delta); why=""
  if ! fpos "$u" || why=$(flawed InvNoneSelf1.remote Finished); then
    voidc "ModifyInventory (wait None) unit control: InvNoneSelf1.remote read '$u'; ${why:-it is sound}"
  elif [ "$(count InvSelf1.npc 'not in sync')" -lt 1 ]; then
    voidc "ModifyInventory (wait None) negative control: InvSelf1.npc, the Server-wait chain, did not desync on this harness"
  else
    n=$(field "$(result_line InvNoneSelf1.npc)" inv_items_delta)
    if feq "$n" "$u" && ! flawed InvNoneSelf1.npc ItemChanged >/dev/null; then
      ok "ModifyInventory, owner == entity, wait None: $n item = the unit $u, chain_server_state=ItemChanged, no desync, entity kept (the simulation pass did the work, the server pass was cancelled as ItemChanged)"
    else bad "ModifyInventory InvNoneSelf1.npc: read '$n' (unit $u), chain_server_state=$(field "$(result_line InvNoneSelf1.npc)" chain_server_state); predicted the unit, ItemChanged, no desync, no removal"; fi
  fi
fi

# The cause, isolated: the same chain with "OnItemChangeBehavior": "Ignore" does not desync and doubles.
if need InvIgnoreSelf1.remote InvIgnoreSelf1.npc; then
  u=$(field "$(result_line InvIgnoreSelf1.remote)" inv_items_delta); n=$(field "$(result_line InvIgnoreSelf1.npc)" inv_items_delta)
  why=""
  if ! fpos "$u" || why=$(flawed InvIgnoreSelf1.remote Finished); then voidc "ModifyInventory (Ignore) unit control: InvIgnoreSelf1.remote read '$u'; ${why:-it is sound}"
  elif [ "$(count InvIgnoreSelf1.npc 'not in sync')" != 0 ]; then bad "ModifyInventory with OnItemChangeBehavior Ignore still desyncs: the item-change explanation is wrong"
  elif why=$(flawed InvIgnoreSelf1.npc Finished); then bad "ModifyInventory InvIgnoreSelf1.npc: the run does not count, $why"
  elif feq "$n" "$(fmul "$u" 2)"; then ok "ModifyInventory, owner == entity, OnItemChangeBehavior Ignore: no desync, $n = 2 x the unit $u (the item-change check was the cause)"
  else bad "ModifyInventory InvIgnoreSelf1.npc: read '$n', predicted 2 x $u"; fi
fi

# negative control: the same harness reads 1 for LaunchProjectile and 2 for ChangeStat on the same manager; checked by the two verdicts above.

# AttachBeam: refuses. Unit control = one on remote reads 1 ADDED and no exception; dose control = two on remote
# read 1 ADDED and the refusal (the instrument sees an add and sees the refusal).
if need Beam1.remote Beam2.remote Beam1.npc Launch1.npc; then
  if [ "$(count Beam1.remote 'BeamComponent ADDED')" != 1 ] || [ "$(exceptions Beam1.remote)" != 0 ]; then
    voidc "AttachBeam unit control: Beam1.remote has $(count Beam1.remote 'BeamComponent ADDED') ADDED and $(exceptions Beam1.remote) exception(s)"
  elif [ "$(count Beam2.remote 'BeamComponent ADDED')" != 1 ] || [ "$(count Beam2.remote 'Entity already contains component type')" -lt 1 ]; then
    voidc "AttachBeam dose control: Beam2.remote has $(count Beam2.remote 'BeamComponent ADDED') ADDED and $(count Beam2.remote 'Entity already contains component type') refusal line(s)"
  elif [ "$(exceptions Launch1.npc)" != 0 ]; then
    voidc "AttachBeam negative control: Launch1.npc has an exception"
  elif why=$(flawed Beam1.remote Finished) || why=$(flawed Beam2.remote -); then
    voidc "AttachBeam control run does not count: $why"
  else
    ok "AttachBeam controls: one on remote adds one and does not throw; two on remote add one and the second is refused"
    if [ "$(count Beam1.npc 'BeamComponent ADDED')" = 1 ] && [ "$(count Beam1.npc 'Entity already contains component type')" -ge 1 ] && ! flawed Beam1.npc - >/dev/null \
       && strip Beam1.npc | /usr/bin/grep -q 'Exception in thread Thread\[#[0-9]*,WorldThread - default'; then
      ok "AttachBeam Beam1.npc: refuses: one BeamComponent ADDED, then 'Entity already contains component type' on the world thread"
    else bad "AttachBeam Beam1.npc: $(count Beam1.npc 'BeamComponent ADDED') ADDED, $(count Beam1.npc 'Entity already contains component type') refusal line(s)"; fi
  fi
fi

if need Beam1.realnpc Beam1.remote Beam2.remote && [ "$(count Beam1.remote 'BeamComponent ADDED')" = 1 ] && [ "$(exceptions Beam1.remote)" = 0 ] && [ "$(count Beam2.remote 'Entity already contains component type')" -ge 1 ]; then
  if realnpc_manager Beam1.realnpc && [ "$(count Beam1.realnpc 'BeamComponent ADDED')" = 1 ] && [ "$(count Beam1.realnpc 'Entity already contains component type')" -ge 1 ] && ! flawed Beam1.realnpc - >/dev/null \
     && strip Beam1.realnpc | /usr/bin/grep -q 'Exception in thread Thread\[#[0-9]*,WorldThread - default'; then
    ok "AttachBeam on a real NPC (Chicken), its own manager: refuses: one BeamComponent ADDED, then 'Entity already contains component type' on the world thread"
  else bad "AttachBeam Beam1.realnpc: $(count Beam1.realnpc 'BeamComponent ADDED') ADDED, $(count Beam1.realnpc 'Entity already contains component type') refusal line(s); on an NPC manager: $(realnpc_manager Beam1.realnpc && echo yes || echo no)"; fi
fi

# Plugin-written types (their declared effect is one log line).
if need Log1.remote Log1.npc LogQ1.npc LogS1.npc; then
  if [ "$(count Log1.remote "ProbeLog message='log1'")" != 1 ] || [ "$(count Log1.remote "pass=server")" -lt 1 ]; then
    voidc "ProbeLog unit control: Log1.remote has $(count Log1.remote "ProbeLog message='log1'") line(s), wanted 1 with pass=server"
  elif why=$(flawed Log1.remote Finished); then
    voidc "ProbeLog unit control: Log1.remote does not count: $why"
  else
    ok "ProbeLog control: on the remote-client manager a firstRun-only type runs once (pass=server)"
    p=$(strip Log1.npc | /usr/bin/grep "PROBE ProbeLog message='log1'" | sed -n 's/.* pass=\([a-z?]*\) .*/\1/p' | tr '\n' ' ')
    if why=$(flawed Log1.npc Finished); then bad "ProbeLog Log1.npc: the run does not count, $why"
    else [ "$p" = "simulation server " ] && ok "ProbeLog Log1.npc: runs twice, simulation pass then server pass" || bad "ProbeLog Log1.npc: passes '$p', predicted 'simulation server'"; fi
    q=$(count LogQ1.npc "ProbeLogQ message='logQ1'")
    if why=$(flawed LogQ1.npc Finished); then bad "ProbeLogQ LogQ1.npc: the run does not count, $why"
    else [ "$q" = 1 ] && ok "ProbeLogQ (simulateFirstRun overridden with an empty body): runs once on the NPC-shaped manager" || bad "ProbeLogQ LogQ1.npc: $q line(s), predicted 1"; fi
    s=$(strip LogS1.npc | /usr/bin/grep "PROBE ProbeLogS message='logS1'" | sed -n 's/.* pass=\([a-z?]*\).*/\1/p' | tr '\n' ' ')
    if why=$(flawed LogS1.npc Finished); then bad "ProbeLogS LogS1.npc: the run does not count, $why"
    else [ "$s" = "server simulation " ] && ok "ProbeLogS (waits for Server): runs twice, server pass first, then simulation pass" || bad "ProbeLogS LogS1.npc: passes '$s', predicted 'server simulation'"; fi
  fi
fi

# Real NPC (fidelity). Controls: the subject has an InteractionManager with NPCInteractionSimulationHandler.
if need Log1.realnpc; then
  if ! realnpc_manager Log1.realnpc; then
    voidc "Log1.realnpc: the subject's manager is not an NPCInteractionSimulationHandler one"
  elif why=$(flawed Log1.realnpc Finished); then
    voidc "Log1.realnpc does not count: $why"
  else
    p=$(strip Log1.realnpc | /usr/bin/grep "PROBE ProbeLog message='log1'" | sed -n 's/.* pass=\([a-z?]*\) .*/\1/p' | tr '\n' ' ')
    [ "$p" = "simulation server " ] && ok "real NPC (Chicken), its own manager: ProbeLog runs twice, simulation pass then server pass" || bad "real NPC Log1: passes '$p', predicted 'simulation server' (0 lines = the chain did not run)"
  fi
fi
if need Stat1.realnpc Stat1.remote; then
  u=$(field "$(result_line Stat1.remote)" subject_SignatureCharges_delta); n=$(field "$(result_line Stat1.realnpc)" subject_SignatureCharges_delta); why=""
  if ! realnpc_manager Stat1.realnpc; then voidc "real NPC Stat1: the subject's manager is not an NPCInteractionSimulationHandler one"
  elif why=$(flawed Stat1.realnpc Finished); then voidc "real NPC Stat1 does not count: $why"
  elif ! fpos "$u"; then voidc "real NPC Stat1: unit control Stat1.remote read '$u'"
  elif feq "$n" "$(fmul "$u" 2)"; then ok "real NPC (Chicken), its own manager: ChangeStat adds $n = 2 x the unit $u"
  else bad "real NPC Stat1: read '$n', predicted 2 x $u"; fi
fi
if need Damage1.realnpc Damage1.remote; then
  u=$(field "$(result_line Damage1.remote)" target_health_delta); n=$(field "$(result_line Damage1.realnpc)" target_health_delta); why=""
  if ! realnpc_manager Damage1.realnpc; then voidc "real NPC Damage1: the subject's manager is not an NPCInteractionSimulationHandler one"
  elif why=$(flawed Damage1.realnpc Finished); then voidc "real NPC Damage1 does not count: $why"
  elif ! fneg "$u"; then voidc "real NPC Damage1: unit control Damage1.remote read '$u'"
  elif [ "$(field "$(result_line Damage1.realnpc)" damage_raised)" != 1 ]; then bad "real NPC Damage1: $(field "$(result_line Damage1.realnpc)" damage_raised) Damage event(s) raised, predicted 1"
  elif feq "$n" "$u"; then ok "real NPC (Chicken hits a Sheep), its own manager: DamageEntity lands once (1 Damage event raised, health $n = the unit $u)"
  else bad "real NPC Damage1: read '$n', predicted the unit $u"; fi
fi

echo "---- $fails failed, $void void"
[ "$void" -gt 0 ] && exit 2
[ "$fails" -gt 0 ] && exit 1
exit 0
