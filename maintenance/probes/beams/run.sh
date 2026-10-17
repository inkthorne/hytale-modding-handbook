#!/usr/bin/env bash
# Run one headless beams probe.   maintenance/probes/beams/run.sh SCRATCH CASE
#
# SCRATCH is a directory outside the repo. Each case gets SCRATCH/CASE/{cwd,universe,mods}
# and writes SCRATCH/CASE.log and SCRATCH/CASE.result (exit code and seconds). Nothing under
# the launcher install or UserData is written: the server runs from the scratch cwd, with a
# scratch --universe, --bind 127.0.0.1:5599 (PROBE_BIND), --auth-mode offline, --disable-sentry, under
# `timeout`.
#
# Cases (validate = --validate-assets --shutdown-after-validate, exit status is the verdict):
#   boot          offline boot with an empty mods dir, then `stop`           (R4)
#   c5-0          validate, empty mods dir: is the shipped tree clean?       (run 0)
#   c5-positive   validate, one pack: Common/Beams/Probe_Own.png + a Beam pointing at it
#   c5-outside    validate, one pack: texture exists but outside Beams/ and Trails/
#   c5-nonpng     validate, one pack: Beams/Probe_Own.jpg exists
#   c5-missing    validate, one pack: Beams/Probe_Missing.png does not exist
#   c5-trails     validate, one pack: a Beam on the shipped Trails/Fire.png
#   validate-plugin  validate with the probe plugin installed: does the run stop before start()?
#   c6            boot with the probe plugin, log the resolved AttachBeam indexes
#   c3            boot with the probe plugin, serialize BeamsUpdate packets
#   c1-control    probe plugin; host manager flagged hasRemoteClient (as a player's is); one AttachBeam
#   c1-double     the same host, two AttachBeam in a row
#   c1-npc        host manager as an NPC's is (hasRemoteClient false); one AttachBeam
#   c6-chain      the same player-like host fires the inline-BeamConfig projectile; the BeamComponent line shows the index
#   c6-reload     like c6, then rewrite a directory pack's interaction file while the server runs
#   c6-reload-pc  the same with the inline BeamConfig inside a ProjectileConfig (the shipped shape)
# Environment: HYTALE_GAME (default: the Flatpak install's .../game/latest). PROBE_BIND=host:port moves the listen address (default 127.0.0.1:5599). PROBE_STACK=1 makes the c1-* cases log a
# stack trace from ProbeLog and from the removal of the host entity.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scratch="${1:?usage: run.sh SCRATCH CASE}"; case_="${2:?usage: run.sh SCRATCH CASE}"

# Guard, before anything is created or removed. The case name is checked against the known list
# first (it becomes a path under SCRATCH and is rm -rf'd below). SCRATCH must be absolute and,
# once canonical, must not be, or sit inside, anything that holds the game or the user's data.
refuse() { echo "FAIL  $*" >&2; exit 3; }
case "$case_" in
  boot|c5-0|c5-positive|c5-outside|c5-nonpng|c5-missing|c5-trails|validate-plugin|c6|c3|c1-control|c1-double|c1-npc|c6-chain|c6-reload|c6-reload-pc) ;;
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
png="$here/plugin/src/main/resources/Common/Beams/Probe_Own.png"
plugin_jar="$here/plugin/build/libs/beams-probe.jar"

d="$canon_scratch/$case_"
under "$(realpath -m -- "$d")" "$canon_scratch" && [ "$(realpath -m -- "$d")" != "$canon_scratch" ] || refuse "case dir '$d' escapes SCRATCH"
# Only a directory this script made is removed: it carries a marker.
if [ -e "$d" ]; then [ -f "$d/.beams-probe-case" ] || refuse "$d exists and is not a beams-probe case dir; not removing it"; rm -rf -- "$d"; fi
mkdir -p "$d/cwd" "$d/universe" "$d/mods" && : > "$d/.beams-probe-case"

# One-asset pack for the C5 cases: pack NAME TEXTUREPATH [COMMON-FILE-TO-COPY-FROM-PNG]
pack() {
  local p="$d/mods/Probe_C5"; mkdir -p "$p/Server/Entity/Beams"
  printf '{\n  "Group": "probe",\n  "Name": "Probe C5",\n  "Version": "1.0.0",\n  "ServerVersion": "^0.7.0",\n  "IncludesAssetPack": true\n}\n' > "$p/manifest.json"
  printf '{\n  "TexturePath": "%s",\n  "ProbeMarker": true\n}\n' "$1" > "$p/Server/Entity/Beams/Probe_Own.json"
  if [ -n "${2:-}" ]; then mkdir -p "$p/Common/$(dirname "$2")"; cp "$png" "$p/Common/$2"; fi
}
need_plugin() { [ -f "$plugin_jar" ] || { echo "FAIL  build the plugin first: $here/build.sh" >&2; exit 3; }; cp "$plugin_jar" "$d/mods/"; }

jvm=(); extra=(); tmo=300
case "$case_" in
  boot)        extra=(--boot-command stop) ;;
  c5-0)        extra=(--validate-assets --shutdown-after-validate) ;;
  c5-positive) pack "Beams/Probe_Own.png" "Beams/Probe_Own.png"; extra=(--validate-assets --shutdown-after-validate) ;;
  c5-outside)  pack "Textures/Probe_Own.png" "Textures/Probe_Own.png"; extra=(--validate-assets --shutdown-after-validate) ;;
  c5-nonpng)   pack "Beams/Probe_Own.jpg" "Beams/Probe_Own.jpg"; extra=(--validate-assets --shutdown-after-validate) ;;
  c5-missing)  pack "Beams/Probe_Missing.png" ""; extra=(--validate-assets --shutdown-after-validate) ;;
  c5-trails)   pack "Trails/Fire.png" ""; extra=(--validate-assets --shutdown-after-validate) ;;
  c6)          need_plugin; jvm=(-Dbeams.probe=c6) ;;
  validate-plugin) need_plugin; jvm=(-Dbeams.probe=c6); extra=(--validate-assets --shutdown-after-validate) ;;
  c3)          need_plugin; jvm=(-Dbeams.probe=c3) ;;
  c1-control)  need_plugin; jvm=(-Dbeams.probe=ticklog,world:Probe_C1_Control -Dbeams.probe.remoteClient=true -Dbeams.probe.exitMs=25000 ${PROBE_STACK:+-Dbeams.probe.stack=true}) ;;
  c1-double)   need_plugin; jvm=(-Dbeams.probe=ticklog,world:Probe_C1_Double -Dbeams.probe.remoteClient=true -Dbeams.probe.exitMs=30000 ${PROBE_STACK:+-Dbeams.probe.stack=true}) ;;
  c1-npc)      need_plugin; jvm=(-Dbeams.probe=ticklog,world:Probe_C1_Control -Dbeams.probe.exitMs=25000 ${PROBE_STACK:+-Dbeams.probe.stack=true}) ;;
  c6-chain)    need_plugin; jvm=(-Dbeams.probe=ticklog,world:Probe_C6_Inline -Dbeams.probe.remoteClient=true -Dbeams.probe.exitMs=12000) ;;
  c6-reload)   need_plugin
               r="$d/mods/Probe_Reload"; mkdir -p "$r/Server/Item/Interactions"
               printf '{\n  "Group": "probe",\n  "Name": "Probe Reload",\n  "Version": "1.0.0",\n  "ServerVersion": "^0.7.0",\n  "IncludesAssetPack": true\n}\n' > "$r/manifest.json"
               printf '{\n  "Type": "AttachBeam",\n  "BeamConfig": {\n    "TexturePath": "Trails/Fire.png"\n  }\n}\n' > "$r/Server/Item/Interactions/Probe_R_Inline.json"
               jvm=(-Dbeams.probe=c6 "-Dbeams.probe.reload=$r/Server/Item/Interactions/Probe_R_Inline.json"); tmo=120 ;;
  c6-reload-pc) need_plugin
               r="$d/mods/Probe_ReloadPC"; mkdir -p "$r/Server/ProjectileConfigs"
               printf '{\n  "Group": "probe",\n  "Name": "Probe ReloadPC",\n  "Version": "1.0.0",\n  "ServerVersion": "^0.7.0",\n  "IncludesAssetPack": true\n}\n' > "$r/manifest.json"
               sed 's/Probe_C6_Inline/Probe_RP_Inline/g' "$here/plugin/src/main/resources/Server/ProjectileConfigs/Probe_C6_Inline.json" > "$r/Server/ProjectileConfigs/Probe_RP_Inline.json"
               jvm=(-Dbeams.probe=c6 "-Dbeams.probe.reload=$r/Server/ProjectileConfigs/Probe_RP_Inline.json"); tmo=120 ;;
  *) refuse "unknown case $case_" ;;
esac

start=$(date +%s)
( cd "$d/cwd" && timeout "$tmo" java "${jvm[@]}" -jar "$jar" --assets "$assets" --auth-mode offline \
    --disable-sentry --bind "$bind" --universe "$d/universe" --mods "$d/mods" "${extra[@]}" ) \
  > "$canon_scratch/$case_.log" 2>&1
rc=$?
echo "exit=$rc seconds=$(( $(date +%s) - start ))" | tee "$canon_scratch/$case_.result"
