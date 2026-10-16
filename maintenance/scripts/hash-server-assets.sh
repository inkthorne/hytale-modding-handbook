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
# Cosmetics/ is optional (a minimal tree has none); Server/ was checked above. find is told only about
# directories that exist, so that a find failure means a real one (an unreadable directory) and not
# a missing optional root.
roots=(Server); [ -d Cosmetics ] && roots+=(Cosmetics)
# pipefail: the pipeline's status was sort's, so a file sha256sum could not read (xargs exits 123)
# or a directory find could not enter left a short index and exit 0, which update-build.sh then
# reported as those files REMOVED (review of 02aaa06..3baa29d, LOW-2). It is now nonzero, and the
# message goes to stderr; the rows already written to stdout are an incomplete index.
# xargs -r: with no file at all GNU xargs would still run sha256sum once, on stdin, and emit a `-` row.
set -o pipefail
find "${roots[@]}" -type f -print0 \
  | xargs -r0 sha256sum \
  | sed 's/  / /' \
  | LC_ALL=C sort -k2
rc=$?
[ "$rc" -eq 0 ] || { echo "hash-server-assets.sh: failed to hash every file under ${roots[*]} (pipeline status $rc) - the index on stdout is incomplete" >&2; exit "$rc"; }
