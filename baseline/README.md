# Asset Baseline

Snapshot of the Hytale game build that the `docs/` were fact-checked against.
When the docs make claims about asset structure or file formats (e.g.
`blockymodel-format.md`, `blockyanim-format.md`, `02-structure.md`), they were
verified against the build recorded here. Diff against this baseline after a
game update to see exactly which assets changed before re-checking docs.

## Current baseline

| Field | Value |
|-------|-------|
| Build | `build-12` (from `install/release/package/sig/build-12/`) |
| Captured | 2026-05-22 |
| `Assets.zip` mtime | 2026-05-22 11:08 |
| `Assets.zip` size | 3,411,196,468 bytes (~3.4 GB, 59,518 files) |
| `CommonAssetsIndex.hashes` | 24,748 entries; sha256 `e281861818f20307c04c613b373f2929b13c2aec798b4e72c70fc9057081a2d2` |

`CommonAssetsIndex.hashes` is Hytale's own per-asset SHA-256 index (paths are
relative to `Common/`), copied verbatim from the extracted assets. It is the
authoritative drift detector — one line per Common asset.

## Detecting drift after a game update

Re-extract the current assets (see CLAUDE.md → "Inspecting assets on Linux"),
then diff the live index against this baseline:

```bash
diff baseline/CommonAssetsIndex.hashes ~/.cache/hytale-assets/CommonAssetsIndex.hashes
```

- No output → Common assets are byte-identical; format docs almost certainly still hold.
- Changed/added/removed lines → those exact assets changed. Re-verify any doc
  that references them (asset paths whose hash changed are the ones to re-check).

Also compare the build marker: if `install/.../sig/` now shows `build-13+`,
the game updated. Update the table above and refresh this snapshot once the
docs have been re-verified against the new build.
