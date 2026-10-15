# Requiredness probes

What does "required" mean for a codec key? Measured against the installed `HytaleServer.jar`
(0.7.2), not read from source. Run from the repo root; each needs `javac`, `java` and the jar
(`$HYTALE_SERVER_JAR` or the Flatpak default), and `effective-required.py` also needs the
decompiled source cache (`maintenance/scripts/build-jar-cache.sh`). Flags: `run.sh --jar JAR --assets DIR`;
`effective-required.py --jar JAR --src DIR`. A missing input exits 3.

| Probe | Decides | Time |
|---|---|---|
| `run.sh [--self-test]` | One key built five ways (true flag / nonNull / both / neither / nonEmpty*) decoded on four paths with a missing key, an explicit null and a value; RecordCodec; a Parent; real shipped codecs. | ~1 s |
| `effective-required.py [-v] [--out F]` | For every `CODEC` in the jar: decode `{}` and list the keys the engine rejects, then compare with `codec_parser`'s `null_validated`. | ~5 s |

Results at 0.7.2. `run.sh` pins the decode matrix, the Parent rows and the real-codec rows (`EXPECTATION
CHANGED` + exit 1 if one moves). `effective-required.py` pins the BASELINE figures below (exit 1 with
"pinned figure moved" and instructions to re-derive; a parser that stops reading validators moves
`predicted` but not `rejected`, and is caught by that pin, not by the subset check). The seven codec-level hook classes are pinned by name, and the holder parser and the crash classifier are tested on real ValidationResults / synthetic frames before use (exit 2 if they fail). The last stdout line starting `PINNED` is the stable summary for callers to echo:

- The `true` third `KeyedCodec` argument (`strict_null`) never rejects an omitted key, on any path.
  It only changes an explicit `null` on the BSON inherit path.
- A key rejects its omission only if its validator chain holds a `NonNullValidator` instance
  (`nonNull()`, `nonEmptyArray()`, `nonEmptyMap()`) **and** its field is still null after
  construction. Of 545 null-validated keys in 1257 decodable classes, the engine rejects the
  omission of 258 and accepts it for 287: 252 on a resolved non-null field default, 5 on an
  initialiser that reads null but is assigned elsewhere, 30 on a default `defaults_probe` cannot
  resolve.
- A Parent satisfies a nonNull key only if it is declared `appendInherited`.
- Codec-level validators and `afterDecode` hooks can reject an empty document no per-key attribute
  sees: 6 classes name no key for it (BlockTagOrItemIdField, ReputationRank, StateFadeConfig, Box,
  AnchorDensityAsset, and SpawnMarker alongside failing keys), and 1 more (BlockSpawnerTable) has a
  validator that crashes on an omitted `Entries`. 7 classes in all.

`run.sh --self-test` first sabotages `nonNull` out of the harness and requires the run to report
VOID (exit 2): a probe that cannot see the defect may not report. `effective-required.py` goes
void (exit 2) if `PluginManifest` stops failing on `Name`, or if `AugmentConditionInteraction`
(nonNull on a key with a default) stops decoding clean.

## Corpus figures behind the parser change (0.7.2 decompiled source)

The `true` flag is `strict_null`; `null_validated` is a `NonNullValidator` instance on the key.
"First CODEC" is `parse_chain(src)` over every file containing `KeyedCodec` (the population the
earlier 623 / 413 / 19 came from: reproduced exactly with the old parser); "all chains" is
`all_chains(src)`.

| | first CODEC (1294 chains) | all chains (1720) |
|---|---|---|
| keys | 4585 | 5303 |
| `strict_null` only (was counted required) | 608 | 684 |
| `null_validated` only | 438 | 502 |
| both | 34 | 35 |
| neither | 3505 | 4082 |
| old arg-only / validator-only / both | 623 / 413 / 19 | 699 / 476 / 20 |
| keys carrying `nonEmptyArray()` / `nonEmptyMap()` | 28 / 2 | 34 / 2 |
| of those, carrying no `nonNull()` (missed by the old parser) | 21 | 23 |

The old parser's validator attribute also moved the other way for 6 keys, which a correction to
6aa3c67's message (it says three) records here: four RecordCodec keys (`WorldEventRecord.Id`,
`EffectsAction.Radius`, `VoidEventTitle.Icon`, `TriggerVolumeCreateAction.Offset`) and two
`.addField()` keys (`ModelAsset.Animation` `Looping`, `Weight`) were credited with the next key's
validator. In the other direction the parser now reads the validators of 23 RecordCodec keys
it used to miss.
