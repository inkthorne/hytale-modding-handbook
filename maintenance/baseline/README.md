# Asset Baseline

Snapshot of the Hytale game build that the `docs/` were fact-checked against.
When the docs make claims about asset structure or file formats (e.g.
`blockymodel-format.md`, `blockyanim-format.md`, `02-structure.md`), they were
verified against the build recorded here. Diff against this baseline after a
game update to see exactly which assets changed before re-checking docs.

## Current baseline

| Field | Value |
|-------|-------|
| Build | `0.5.2` (Update 5; `Implementation-Version` = `0.5.2`, from `install/release/package/sig/build-15/`) |
| Captured | 2026-05-27 (build-15); prior baselines build-14 (0.5.1) and build-13 (0.5.0) |
| `Assets.zip` mtime | 2026-05-27 22:08 (build-15; was 2026-05-26 15:00 on build-14) |
| `Assets.zip` size | 3,428,485,136 bytes (~3.4 GB; build-14 was 3,428,476,129 — Server-side delta only) |
| `CommonAssetsIndex.hashes` | 24,914 entries; sha256 `fd7f4c907dd2d370ad38a056404d0f6cedeeff94e38b7f47169c3fa0fa275a79` — content **unchanged** from build-14 (Common assets byte-identical; only the index's internal line ordering changed, so the raw sha differs from build-14's `77b9732421d6ed116376ba0eb3cf1921b937d96f05d50bd46258c50e7120f736`) |

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

Also compare the build marker: if `install/.../sig/` now shows `build-15+`
(or `Implementation-Version` advances past `0.5.2`), the game updated. Update the
table above and refresh this snapshot once the docs have been re-verified against
the new build.
