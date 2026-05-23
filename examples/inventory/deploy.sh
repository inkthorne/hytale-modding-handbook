#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=../hytale-paths.sh
source ../hytale-paths.sh

MODS_DIR="$HYTALE_MODS_DIR"
JAR_FILE="build/libs/example-inventory.jar"

if [ ! -f "$JAR_FILE" ]; then
    echo "JAR not found. Building first..."
    ./gradlew build
fi

if [ ! -d "$MODS_DIR" ]; then
    echo "Creating mods directory..."
    mkdir -p "$MODS_DIR"
fi

echo "Deploying to $MODS_DIR..."
cp -f "$JAR_FILE" "$MODS_DIR/"
echo "Deployed successfully!"
