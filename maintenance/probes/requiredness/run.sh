#!/usr/bin/env bash
# Compile and run the requiredness probe against the installed HytaleServer.jar.
#   maintenance/probes/requiredness/run.sh [--self-test] [--jar PATH] [--assets DIR]
# Exit 0: matrix printed, pinned expectations held.  2: negative control failed (run VOID).
# 1: a pinned expectation changed.  3: no jar / no javac.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
jar="${HYTALE_SERVER_JAR:-$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Server/HytaleServer.jar}"
assets="${HYTALE_ASSETS_CACHE:-$HOME/.cache/hytale-assets}"
self_test=0
while [ $# -gt 0 ]; do
  case "$1" in --jar) jar="$2"; shift 2;; --assets) assets="$2"; shift 2;; --self-test) self_test=1; shift;; *) echo "unknown arg $1" >&2; exit 3;; esac
done
[ -f "$jar" ] || { echo "FAIL  HytaleServer.jar not found at $jar" >&2; exit 3; }
command -v javac >/dev/null || { echo "FAIL  javac not on PATH" >&2; exit 3; }
out="$(mktemp -d)"; trap 'rm -rf "$out"' EXIT
echo "jar: $jar ($(unzip -p "$jar" META-INF/MANIFEST.MF | tr -d '\r' | /usr/bin/grep -i '^Implementation-Version'))"
javac -nowarn -proc:none -cp "$jar" -d "$out" "$here/RequirednessProbe.java" 2>&1 | /usr/bin/grep -v '^Note:' >&2
[ -f "$out/RequirednessProbe.class" ] || { echo "FAIL  harness did not compile" >&2; exit 3; }
if [ "$self_test" = 1 ]; then
  # The probe must see the defect before it may report: with nonNull sabotaged away the negative
  # control (nonNull + omitted key on the asset path) cannot throw, and the run must be VOID (2).
  msg="$(java -Dprobe.sabotage=1 -cp "$out:$jar" RequirednessProbe "$assets" 2>&1)"; rc=$?
  if [ "$rc" = 2 ] && printf '%s' "$msg" | /usr/bin/grep -q '^VOID: nonNull on an omitted key did not throw CodecValidationException'; then
    echo "self-test: sabotaged run is VOID as required"
  else
    echo "FAIL  self-test: sabotaged run exited $rc and did not report VOID -- the probe cannot see its own defect" >&2; exit 1
  fi
fi
java -cp "$out:$jar" RequirednessProbe "$assets"
