#!/usr/bin/env bash
# Deploy the Custom Food pack into the Hytale Mods folder.
# Unlike the plugin examples there is nothing to build — a pack is just JSON, so
# this copies the asset files (manifest.json + Server/) into a pack subfolder.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=../hytale-paths.sh
source ../hytale-paths.sh

MODS_DIR="$HYTALE_MODS_DIR"
PACK_DIR="$MODS_DIR/custom-food"

if [ ! -d "$MODS_DIR" ]; then
    echo "Creating mods directory..."
    mkdir -p "$MODS_DIR"
fi

echo "Deploying Custom Food pack to $PACK_DIR..."
# Fresh copy: clear any previous deploy, then copy only the asset content.
rm -rf "$PACK_DIR"
mkdir -p "$PACK_DIR"
cp -f manifest.json "$PACK_DIR/"
cp -r Server "$PACK_DIR/"
echo "Deployed successfully!"
echo "Start Hytale, then run: /give Food_Hearty_Snack 1"
