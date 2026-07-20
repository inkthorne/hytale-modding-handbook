#!/usr/bin/env bash
#
# check-for-update.sh — headless "did the game update?" check, for a scheduler.
# Compares the installed HytaleServer.jar's Implementation-Version against the
# docs' "Verified against" stamp. On divergence it notifies (desktop
# notification when available, always the exit message + a marker file) so the
# maintainer knows to run maintenance/scripts/update-build.sh.
#
# Exit codes: 0 = in sync (or jar missing — nothing to compare), 10 = update
# detected. Designed for a systemd user timer; see the repo README/CLAUDE.md.
#
# Env overrides: HYTALE_JAR as in the other scripts;
#   UPDATE_MARKER  marker-file path (default ~/.cache/hytale-update-pending)

set -u
cd "$(dirname "$0")/../.." || exit 2

if [ -n "${APPDATA:-}" ]; then
  ROOT="$APPDATA/Hytale"
elif [ -d "$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale" ]; then
  ROOT="$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale"
else
  ROOT="$HOME/AppData/Roaming/Hytale"
fi
JAR="${HYTALE_JAR:-$ROOT/install/release/package/game/latest/Server/HytaleServer.jar}"
MARKER="${UPDATE_MARKER:-$HOME/.cache/hytale-update-pending}"

if [ ! -f "$JAR" ]; then
  echo "hytale-update-check: jar not found ($JAR) — skipping"
  exit 0
fi

INSTALLED="$(unzip -p "$JAR" META-INF/MANIFEST.MF 2>/dev/null | tr -d '\r' | sed -n 's/^Implementation-Version: //p')"
STAMPED="$(grep -m1 -o 'Verified against [0-9.]*' docs/inventory.md 2>/dev/null | awk '{print $3}')"
BUILD="$(find "$ROOT/install/release/package/sig" -maxdepth 1 -name 'build-*' 2>/dev/null | head -1)"
BUILD="${BUILD:+$(basename "$BUILD")}"

if [ -z "$INSTALLED" ] || [ -z "$STAMPED" ]; then
  echo "hytale-update-check: could not read versions (installed='$INSTALLED' stamped='$STAMPED')"
  exit 0
fi

if [ "$INSTALLED" = "$STAMPED" ]; then
  echo "hytale-update-check: in sync ($INSTALLED${BUILD:+, $BUILD})"
  rm -f "$MARKER"
  exit 0
fi

MSG="Hytale updated: installed $INSTALLED${BUILD:+ ($BUILD)}, handbook verified against $STAMPED. Run maintenance/scripts/update-build.sh in the handbook repo."
echo "hytale-update-check: $MSG"
printf '%s\n' "$MSG" > "$MARKER"
command -v notify-send >/dev/null 2>&1 && \
  notify-send -u critical -a "Hytale handbook" "Hytale game updated" \
    "Installed $INSTALLED${BUILD:+ ($BUILD)} vs docs $STAMPED — run update-build.sh" 2>/dev/null
exit 10
