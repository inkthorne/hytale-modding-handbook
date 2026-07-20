#!/usr/bin/env bash
#
# hash-server-assets.sh — emit a sha256 index of the non-Common game assets
# (Server/ and Cosmetics/) to stdout, in the same "<sha256> <path>" shape as
# Hytale's own CommonAssetsIndex.hashes (paths relative to the assets root).
#
# Hytale ships a hash index for Common/ only, so Server-side data drift — the
# item/drop/prefab/worldgen/NPC JSON configs that a large share of the docs
# document — was previously invisible to the baseline diff. This generates the
# missing half; the checked-in snapshot lives at
# maintenance/baseline/ServerAssetsIndex.hashes.
#
# Usage:
#   maintenance/scripts/hash-server-assets.sh                # index the default cache
#   maintenance/scripts/hash-server-assets.sh /path/to/assets
#
# Refresh the baseline (only after docs are re-verified against the new build):
#   maintenance/scripts/hash-server-assets.sh > maintenance/baseline/ServerAssetsIndex.hashes
#
# Output is LC_ALL=C sorted by path, so plain `diff` against the baseline is a
# stable content comparison (no reorder noise). manifest.json is excluded — it
# is build metadata, not an asset, and would show drift on every build.

set -u

ASSETS="${1:-${HYTALE_ASSETS:-$HOME/.cache/hytale-assets}}"
[ -d "$ASSETS/Server" ] || { echo "no Server/ under $ASSETS — extract Assets.zip first (see CLAUDE.md)" >&2; exit 2; }

cd "$ASSETS" || exit 2
find Server Cosmetics -type f -print0 2>/dev/null \
  | xargs -0 sha256sum \
  | sed 's/  / /' \
  | LC_ALL=C sort -k2
