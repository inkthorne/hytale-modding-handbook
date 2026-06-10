# Asset Baseline

Snapshot of the Hytale game build that the `docs/` were fact-checked against.
When the docs make claims about asset structure or file formats (e.g.
`blockymodel-format.md`, `blockyanim-format.md`, `02-structure.md`), they were
verified against the build recorded here. Diff against this baseline after a
game update to see exactly which assets changed before re-checking docs.

## Current baseline

| Field | Value |
|-------|-------|
| Build | `0.5.4` (Update 5 patch; `Implementation-Version` = `0.5.4`, from `install/release/package/sig/build-17/`) |
| Captured | 2026-06-10 (build-17); prior baselines build-16 (0.5.3), build-15 (0.5.2), build-14 (0.5.1) and build-13 (0.5.0) |
| `Assets.zip` mtime | 2026-06-10 00:43 (build-17; was 2026-05-30 11:48 on build-16) |
| `Assets.zip` size | 3,428,514,410 bytes (~3.4 GB; build-16 was 3,428,506,917 — Server-side delta only) |
| `CommonAssetsIndex.hashes` | 24,914 entries; sha256 `fd7f4c907dd2d370ad38a056404d0f6cedeeff94e38b7f47169c3fa0fa275a79` — Common assets content **unchanged** since build-15 (set-identical); the line ordering reverted to build-15's exact layout, so the raw sha matches build-15 and differs from build-16's `de2366d85f4ffc97b475788992d1dc798d94f649e4e020a1372394ce5b318563` |

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
