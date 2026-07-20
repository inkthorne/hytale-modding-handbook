# Asset Baseline

Snapshot of the Hytale game build that the `docs/` were fact-checked against.
When the docs make claims about asset structure or file formats (e.g.
`blockymodel-format.md`, `blockyanim-format.md`, `02-structure.md`), they were
verified against the build recorded here. Diff against this baseline after a
game update to see exactly which assets changed before re-checking docs.

## Current baseline

| Field | Value |
|-------|-------|
| Build | `0.5.7` (Update 5 patch; `Implementation-Version` = `0.5.7`, from `install/release/package/sig/build-20/`) |
| Captured | 2026-07-19 (build-20); prior baselines build-17 (0.5.4), build-16 (0.5.3), build-15 (0.5.2), build-14 (0.5.1) and build-13 (0.5.0) |
| `Assets.zip` mtime | 2026-07-19 18:17 (build-20; was 2026-06-10 00:43 on build-17) |
| `Assets.zip` size | 3,428,472,949 bytes (~3.4 GB; build-17 was 3,428,514,410) |
| `CommonAssetsIndex.hashes` | 24,914 entries; sha256 `0626935000b2399ba35ccf53d92dabb42f0857682a2abcc4f234f16af050c94d` — first real Common drift since build-15: **36 assets changed content** vs build-17 (door blockyanims, decorative-set models/textures, localization files, `UI/Custom/Pages/TriggerVolume/TriggerVolumeInspectorPage.ui`), none added or removed; docs re-verified against the changed files 2026-07-19 (build-17 sha was `fd7f4c907dd2d370ad38a056404d0f6cedeeff94e38b7f47169c3fa0fa275a79`) |

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

> **Caveat — reordering vs. content drift.** The index is not stably sorted, so a
> patch can re-shuffle its line order without changing any asset, producing a huge
> raw `diff` (the build-14 → build-15 bump was a 5.4 MB diff that turned out to be
> *zero* content changes). When the raw diff looks large, compare content only:
>
> ```bash
> diff <(LC_ALL=C sort maintenance/baseline/CommonAssetsIndex.hashes) \
>      <(LC_ALL=C sort ~/.cache/hytale-assets/CommonAssetsIndex.hashes)
> ```
>
> Empty output here = Common assets byte-identical despite the reordering (refresh
> the baseline file anyway so the cheap raw `diff` goes clean next time).

Also compare the build marker: if `install/.../sig/` now shows `build-17+`
(or `Implementation-Version` advances past `0.5.4`), the game updated. Update the
table above and refresh this snapshot once the docs have been re-verified against
the new build.
