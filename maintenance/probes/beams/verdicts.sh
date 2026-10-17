#!/usr/bin/env bash
# Judge the logs run.sh left in SCRATCH.   maintenance/probes/beams/verdicts.sh SCRATCH
#
# Every verdict is a grep on a log, and each one that settles a claim is preceded by the check that
# the probe could see the outcome it reports (its control). A control that fails makes the run VOID
# (exit 2): the verdict after it is then not printed. A verdict that disagrees with the README exits 1.
# A check that finds no log prints FAIL: a missing file is not a pass.
set -u
scratch="${1:?usage: verdicts.sh SCRATCH}"
fails=0; void=0
strip() { sed 's/\x1b\[[0-9;]*m//g' "$scratch/$1.log" 2>/dev/null; }
have() { [ -s "$scratch/$1.log" ] && [ -s "$scratch/$1.result" ]; }
exitcode() { sed -n 's/^exit=\([0-9]*\).*/\1/p' "$scratch/$1.result"; }
ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fails=$((fails+1)); }
voidc() { printf 'VOID  control did not hold: %s\n' "$1"; void=$((void+1)); }
count() { strip "$1" | /usr/bin/grep -c -- "$2"; }

need() { for c in "$@"; do have "$c" || { bad "no log/result for case $c in $scratch"; return 1; }; done; }

# R4: the server boots headless.
if need boot; then
  [ "$(exitcode boot)" = 0 ] && [ "$(count boot 'Hytale Server Booted!')" = 1 ] && ok "R4 boot: exit 0 and 'Hytale Server Booted!' once" || bad "R4 boot"
fi

# C5. Run 0 first: if the shipped tree does not validate clean, exit status says nothing.
if need c5-0 c5-positive c5-trails c5-outside c5-nonpng c5-missing validate-plugin; then
  if [ "$(exitcode c5-0)" != 0 ]; then voidc "c5-0: the shipped assets do not validate clean (exit $(exitcode c5-0))"
  else
    ok "C5 run 0: shipped assets, empty mods dir, exit 0"
    # negative controls: each must fail with its quoted message, and with that message alone
    neg() { # case, message
      local c="$1" msg="$2" n
      n=$(strip "$c" | /usr/bin/grep -c 'FAIL: ')
      if [ "$(exitcode "$c")" != 0 ] && [ "$n" = 1 ] && strip "$c" | /usr/bin/grep -qF "FAIL: $msg"; then ok "C5 $c: nonzero exit and exactly '$msg'"
      else bad "C5 $c: exit $(exitcode "$c"), $n FAIL line(s), wanted exactly '$msg'"; fi
    }
    neg c5-outside "Common Asset 'Textures/Probe_Own.png' must be within the root: [Beams/, Trails/]"
    neg c5-nonpng "Common Asset 'Beams/Probe_Own.jpg' must have the extension png"
    neg c5-missing "Common Asset 'Beams/Probe_Missing.png' doesn't exist!"
    # the controls held (all three refused), so the positives mean something
    for c in c5-outside c5-nonpng c5-missing; do [ "$(exitcode $c)" != 0 ] || voidc "$c did not fail"; done
    for c in c5-positive c5-trails validate-plugin; do
      [ "$(exitcode $c)" = 0 ] && [ "$(count $c 'FAIL: ')" = 0 ] && ok "C5 $c: exit 0, no FAIL line" || bad "C5 $c: exit $(exitcode $c)"
    done
    [ "$(count validate-plugin 'PROBE')" = 0 ] && ok "R4 --shutdown-after-validate stops before the plugin's start(): 0 PROBE lines" || bad "R4 plugin start() ran during validate"
  fi
fi

# C6. The sentinel and the named-id control first.
if need c6; then
  l=$(strip c6)
  s=$(printf '%s\n' "$l" | sed -n "s/.*PROBE c6 sentinel: Beam 'NoSuchBeam' getIndex=\(-\?[0-9]*\).*/\1/p")
  named=$(printf '%s\n' "$l" | sed -n "s/.*AttachBeam interaction id='Probe_C6_Named' .*resolvedBeamIndex=\(-\?[0-9]*\).*/\1/p")
  if [ "$s" != -2147483648 ]; then voidc "sentinel NoSuchBeam is $s, not Integer.MIN_VALUE"
  elif [ -z "$named" ] || [ "$named" -lt 0 ]; then voidc "named-id control Probe_C6_Named resolved to '$named'"
  else
    ok "C6 controls: sentinel is MIN_VALUE, named-id Probe_C6_Named resolved to $named"
    for id in "Probe_C6_Inline" "\*\*Probe_C6_Inline_Interactions_ProjectileSpawn_Interactions_0"; do
      if printf '%s\n' "$l" | /usr/bin/grep -q "AttachBeam interaction id='$id' .*resolvedBeamIndex=-2147483648 (now getIndex(BeamConfig)=[0-9]"; then ok "C6 inline $id: resolvedBeamIndex=MIN_VALUE, generated Beam has a real index now"
      else bad "C6 inline $id"; fi
    done
    printf '%s\n' "$l" | /usr/bin/grep -q "Beam id='Probe_Own' index=[0-9]* texture=Beams/Probe_Own.png" && ok "C5 booted store holds Probe_Own with texture Beams/Probe_Own.png" || bad "C5 Probe_Own not in the booted store"
  fi
fi
if need c6-reload; then
  l=$(strip c6-reload | /usr/bin/grep "AttachBeam interaction id='Probe_R_Inline'")
  first=$(printf '%s\n' "$l" | sed -n 1p | sed -n 's/.*resolvedBeamIndex=\(-\?[0-9]*\).*/\1/p')
  second=$(printf '%s\n' "$l" | sed -n 2p | sed -n 's/.*resolvedBeamIndex=\(-\?[0-9]*\).*/\1/p')
  if [ "$first" != -2147483648 ]; then voidc "c6-reload: first load was '$first', not MIN_VALUE"
  elif [ -n "$second" ] && [ "$second" -ge 0 ]; then ok "C6 reload: MIN_VALUE at boot, $second after the watcher reloaded the file"
  else bad "C6 reload: second read '$second'"; fi
fi
if need c6-chain; then
  strip c6-chain | /usr/bin/grep -q 'BeamComponent ADDED.*\[{index=-2147483648 ' && ok "C6 end to end: the BeamComponent holds beam index -2147483648" || bad "C6 c6-chain"
fi

# C3 server half.
if need c3; then
  l=$(strip c3)
  printf '%s\n' "$l" | /usr/bin/grep -q "case='valid R-Attachment (control)'.*serialize=OK.*readBack='R-Attachment'" || voidc "c3: the valid name did not round-trip"
  printf '%s\n' "$l" | /usr/bin/grep -q "case='96 bytes (boundary)'.*serialize=OK.*readBack.length=96" && ok "C3 96 bytes round-trips" || bad "C3 96 bytes"
  printf '%s\n' "$l" | /usr/bin/grep -qF "case='97 bytes' charLength=97 serialize=THREW com.hypixel.hytale.protocol.io.ProtocolException: String exceeds max bytes: 97 > 96" && ok "C3 97 bytes: ProtocolException 'String exceeds max bytes: 97 > 96'" || bad "C3 97 bytes"
  printf '%s\n' "$l" | /usr/bin/grep -q "case='e-acute (U+00E9)'.*serialize=OK.*readBack='caf?' readBackHex=6361663f" && ok "C3 e-acute reads back as '?' (0x3f), no error" || bad "C3 e-acute"
  printf '%s\n' "$l" | /usr/bin/grep -q "case='CJK'.*readBack='??' readBackHex=3f3f" && ok "C3 two CJK characters read back as '??'" || bad "C3 CJK"
fi

# C1. The control first: one AttachBeam on a player-like manager must not throw.
if need c1-control c1-double c1-npc; then
  if [ "$(count c1-control 'Exception in thread')" != 0 ] || [ "$(count c1-control 'BeamComponent ADDED')" != 1 ]; then
    voidc "c1-control: $(count c1-control 'Exception in thread') exception(s), $(count c1-control 'BeamComponent ADDED') ADDED line(s)"
  elif [ "$(count c1-control "ProbeLog message='control: 0.2 s later'.*beamComponentCommittedNow=true")" != 1 ]; then
    voidc "c1-control: the 0.2 s ProbeLog did not fire"
  else
    ok "C1 control: one AttachBeam, one BeamComponent ADDED, both ProbeLog lines, no exception"
    d=$(count c1-double 'Entity already contains component type')
    [ "$d" -ge 1 ] && [ "$(count c1-double 'BeamComponent ADDED')" = 1 ] \
      && [ "$(count c1-double "ProbeLog message='double: after the second AttachBeam, same tick'.*beamComponentCommittedNow=false")" = 1 ] \
      && [ "$(count c1-double "ProbeLog message='double: 0.2 s later'")" = 0 ] \
      && ok "C1 double: same-tick ProbeLog once, one ADDED, then 'Entity already contains component type', the 0.2 s ProbeLog never fires" \
      || bad "C1 double"
    strip c1-double | /usr/bin/grep -q 'Exception in thread Thread\[#[0-9]*,WorldThread - default' && ok "C1 double: the exception is logged by the world thread" || bad "C1 double: not the world thread"
    strip c1-double | /usr/bin/grep -q 'Reloading crashed world .default. in 5 second' && ok "C1 double: WorldCrashRecoveryHandler schedules a reload" || bad "C1 double: no reload line"
    [ "$(count c1-npc "ProbeLog message='control: after the one AttachBeam, same tick'")" = 2 ] \
      && [ "$(count c1-npc 'Entity already contains component type')" -ge 1 ] \
      && ok "C1 npc-like manager: one AttachBeam runs firstRun twice (two same-tick ProbeLog lines) and throws" || bad "C1 npc-like"
  fi
fi

echo "---- $fails failed, $void void"
[ "$void" -gt 0 ] && exit 2
[ "$fails" -gt 0 ] && exit 1
exit 0
