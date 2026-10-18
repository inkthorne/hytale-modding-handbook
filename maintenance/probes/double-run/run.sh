#!/usr/bin/env bash
# Run one headless double-run probe.   maintenance/probes/double-run/run.sh SCRATCH CASE
#
# SCRATCH is a directory outside the repo. Each case gets SCRATCH/CASE/{cwd,universe,mods} and writes
# SCRATCH/CASE.log and SCRATCH/CASE.result (exit code and seconds). Nothing under the launcher install or
# UserData is written: the server runs from the scratch cwd, with a scratch --universe, --bind
# 127.0.0.1:5599 (PROBE_BIND), --auth-mode offline, --disable-sentry, under `timeout`.
# The scratch guard is the one of ../beams/run.sh (tested by ../beams/guard-test.sh, which takes this
# script as its second argument; see the README).
#
# Cases:
#   boot            offline boot with an empty mods dir, then `stop`
#   ROOT.MANAGER    ROOT is a RootInteraction of the probe plugin's pack (DR_<ROOT>), MANAGER is
#                     npc      host entity, manager as an NPC's: new InteractionManager(null, NPCInteractionSimulationHandler)
#                     remote   the same host with setHasRemoteClient(true): what a player's manager looks like
#                     realnpc  a shipped NPC role (Chicken) spawned headless; the chain runs on its own manager
#                   ROOT is one of: Log1 Damage1 Damage2 Launch1 Launch2 Stat1 Stat2 StatSet1 Beam1 Beam2 Inv1 Inv2 InvSelf1 InvIgnoreSelf1 InvNoneSelf1 LogS1 LogQ1
#                   and the 13b roots Explode1 Explode2 (a Sheep target is damaged), Cooldown1 Cooldown2 (a cooldown of 3 charges, id DR_CD),
#                   CooldownOne1 (the same with 1 charge), Force1 Force2 (ApplyForce; the host gets a Velocity), Repeat1 Repeat2 (a fork of
#                   LaunchProjectile), Clear1 (ClearEntityEffect of an effect applied to the Sheep first) and Clear0 (the same set-up, a chain
#                   that clears nothing: the instrument sees the effect still present), Proj1 Proj2 (the Projectile type), and InvAdjSelf1 InvAdjSelf2
#                   InvAdjOneSelf1 (ModifyInventory AdjustHeldItemQuantity -1, owner == entity, the active slot holding 5 Food_Egg, and 1 for AdjOne)
#                   (the suffix is the number of times the type is in the chain). InvSelf1 is Inv1 with the
#                   owner == the running entity (no proxy context), see dr.self in Driver.java; InvIgnoreSelf1 is
#                   the same with "OnItemChangeBehavior": "Ignore" in the interaction. InvNoneSelf1 is InvSelf1 with the
#                   plugin's ProbeInvNone type: ModifyInventory with getWaitForDataFrom() = None, nothing else.
# Environment: HYTALE_GAME (default: the Flatpak install's .../game/latest). PROBE_BIND=host:port moves the
# listen address. DR_STACK=1 makes ProbeLog write the frames that called it.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scratch="${1:?usage: run.sh SCRATCH CASE}"; case_="${2:?usage: run.sh SCRATCH CASE}"

refuse() { echo "FAIL  $*" >&2; exit 3; }
roots="Log1 Damage1 Damage2 Launch1 Launch2 Stat1 Stat2 StatSet1 Beam1 Beam2 Inv1 Inv2 InvSelf1 InvIgnoreSelf1 InvNoneSelf1 LogS1 LogQ1 Explode1 Explode2 Cooldown1 Cooldown2 CooldownOne1 Force1 Force2 Repeat1 Repeat2 Clear1 Clear0 Proj1 Proj2 InvAdjSelf1 InvAdjSelf2 InvAdjOneSelf1 Destroy1 Destroy2"
mgrs="npc remote realnpc"
root=""; mgr=""
# listed WORD LIST...: WORD is exactly one of the list's elements. (A substring test of the joined list accepted
# "Log1 Damage1.npc remote": root "Log1 Damage1" and manager "npc remote" are each a run of adjacent words.)
listed() { local w="$1" e; shift; for e in "$@"; do [ "$e" = "$w" ] && return 0; done; return 1; }
case "$case_" in
  boot) ;;
  *.*) root="${case_%%.*}"; mgr="${case_#*.}"
       listed "$root" $roots || refuse "unknown root '$root' in case '$case_' (see the header of $0)"
       listed "$mgr" $mgrs || refuse "unknown manager '$mgr' in case '$case_' (see the header of $0)" ;;
  *) refuse "unknown case '$case_' (see the header of $0)" ;;
esac
case "$scratch" in /*) ;; *) refuse "SCRATCH must be an absolute path, got '$scratch'" ;; esac
canon_scratch="$(realpath -m -- "$scratch")" || refuse "cannot canonicalise '$scratch'"
canon_home="$(realpath -m -- "$HOME")"
under() { [ "$1" = "$2" ] || case "$1" in "$2"/*) return 0 ;; *) return 1 ;; esac; }
[ "$canon_scratch" != / ] || refuse "SCRATCH is /"
[ "$canon_scratch" != "$canon_home" ] || refuse "SCRATCH is \$HOME"
for guarded in "$canon_home/.var" "$canon_home"/.cache/hytale-*; do
  [ -e "$guarded" ] || continue
  under "$canon_scratch" "$(realpath -m -- "$guarded")" && refuse "SCRATCH '$scratch' is inside $guarded"
done
game="${HYTALE_GAME:-$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest}"
under "$canon_scratch" "$(realpath -m -- "$game")" && refuse "SCRATCH is inside the game directory $game"
jar="$game/Server/HytaleServer.jar"; assets="$game/Assets.zip"
[ -f "$jar" ] && [ -f "$assets" ] || refuse "no HytaleServer.jar / Assets.zip under $game"
bind="${PROBE_BIND:-127.0.0.1:5599}"
plugin_jar="$here/plugin/build/libs/double-run-probe.jar"

d="$canon_scratch/$case_"
under "$(realpath -m -- "$d")" "$canon_scratch" && [ "$(realpath -m -- "$d")" != "$canon_scratch" ] || refuse "case dir '$d' escapes SCRATCH"
# Only a directory this script made is removed: it carries a marker.
if [ -e "$d" ]; then [ -f "$d/.double-run-case" ] || refuse "$d exists and is not a double-run case dir; not removing it"; rm -rf -- "$d"; fi
mkdir -p "$d/cwd" "$d/universe" "$d/mods" && : > "$d/.double-run-case"

jvm=(); extra=(); tmo=300
if [ "$case_" = boot ]; then
  extra=(--boot-command stop)
else
  [ -f "$plugin_jar" ] || { echo "FAIL  build the plugin first: $here/build.sh" >&2; exit 3; }
  cp "$plugin_jar" "$d/mods/"
  self=(); case "$root" in InvSelf1) root=Inv1; self=(-Ddr.self=true) ;; InvIgnoreSelf1) root=InvIgnore1; self=(-Ddr.self=true) ;; InvNoneSelf1) root=InvNone1; self=(-Ddr.self=true) ;;
    InvAdjSelf1) root=InvAdj1; self=(-Ddr.self=true -Ddr.held=Food_Egg:5) ;; InvAdjSelf2) root=InvAdj2; self=(-Ddr.self=true -Ddr.held=Food_Egg:5) ;;
    InvAdjOneSelf1) root=InvAdj1; self=(-Ddr.self=true -Ddr.held=Food_Egg:1) ;; esac
  jvm=("-Ddr.root=DR_$root" "-Ddr.manager=$mgr" -Ddr.exitMs=12000 "${self[@]}" ${DR_STACK:+-Ddr.stack=true})
  [ "$mgr" = realnpc ] && jvm+=(-Ddr.exitMs=16000 -Ddr.targetRole=Sheep)
  case "$root" in Inv*) jvm+=(-Ddr.inventory=true) ;; esac
  case "$root" in
    Explode*) jvm+=(-Ddr.targetRole=Sheep) ;;
    Clear*) jvm+=(-Ddr.targetRole=Sheep -Ddr.effect=Drop_Rare) ;;
    Cooldown*) jvm+=(-Ddr.cooldownId=DR_CD) ;;
    Force*) jvm+=(-Ddr.velocity=true) ;;
    Destroy*) jvm+=(-Ddr.destroyBlock=true -Ddr.targetRole=none) ;;
  esac
fi

start=$(date +%s)
( cd "$d/cwd" && timeout "$tmo" java "${jvm[@]}" -jar "$jar" --assets "$assets" --auth-mode offline \
    --disable-sentry --bind "$bind" --universe "$d/universe" --mods "$d/mods" "${extra[@]}" ) \
  > "$canon_scratch/$case_.log" 2>&1
rc=$?
echo "exit=$rc seconds=$(( $(date +%s) - start ))" | tee "$canon_scratch/$case_.result"
