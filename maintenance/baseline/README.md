# Asset Baseline

Snapshot of the Hytale game build that the `docs/` were fact-checked against.
When the docs make claims about asset structure or file formats (e.g.
`blockymodel-format.md`, `blockyanim-format.md`, `02-structure.md`), they were
verified against the build recorded here. Diff against this baseline after a
game update to see exactly which assets changed before re-checking docs.

## Current baseline

| Field | Value |
|-------|-------|
| Build | `0.5.1` (Update 5; `Implementation-Version` = `0.5.1`, from `install/release/package/sig/build-14/`) |
| Captured | 2026-05-26 (build-13); re-verified 2026-05-27 against build-14 |
| `Assets.zip` mtime | 2026-05-26 15:00 (build-14; was 10:23 on build-13) |
| `Assets.zip` size | 3,428,476,129 bytes (~3.4 GB; build-13 was 3,428,474,018 — Server-side delta only) |
| `CommonAssetsIndex.hashes` | 24,914 entries; sha256 `77b9732421d6ed116376ba0eb3cf1921b937d96f05d50bd46258c50e7120f736` — **unchanged** from build-13 (Common assets byte-identical) |

`CommonAssetsIndex.hashes` is Hytale's own per-asset SHA-256 index (paths are
relative to `Common/`), copied verbatim from the extracted assets. It is the
authoritative drift detector — one line per Common asset.

## Detecting drift after a game update

Re-extract the current assets (see CLAUDE.md → "Inspecting assets on Linux"),
then diff the live index against this baseline:

```bash
diff maintenance/baseline/CommonAssetsIndex.hashes ~/.cache/hytale-assets/CommonAssetsIndex.hashes
```

- No output → Common assets are byte-identical; format docs almost certainly still hold.
- Changed/added/removed lines → those exact assets changed. Re-verify any doc
  that references them (asset paths whose hash changed are the ones to re-check).

Also compare the build marker: if `install/.../sig/` now shows `build-14+`
(or `Implementation-Version` advances past `0.5.0`), the game updated. Update the
table above and refresh this snapshot once the docs have been re-verified against
the new build.
