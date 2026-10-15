# Requiredness probes

What does "required" mean for a codec key? Measured against the installed `HytaleServer.jar`
(0.7.2), not read from source. Run from the repo root; each needs `javac`, `java` and the jar
(`$HYTALE_SERVER_JAR` or the Flatpak default), and `effective-required.py` also needs the
decompiled source cache (`maintenance/scripts/build-jar-cache.sh`).

| Probe | Decides | Time |
|---|---|---|
| `run.sh [--self-test]` | One key built five ways (true flag / nonNull / both / neither / nonEmpty*) decoded on four paths with a missing key, an explicit null and a value; RecordCodec; a Parent; real shipped codecs. | ~1 s |
| `effective-required.py [-v] [--out F]` | For every `CODEC` in the jar: decode `{}` and list the keys the engine rejects, then compare with `codec_parser`'s `null_validated`. | ~5 s |

Results at 0.7.2, each also pinned in the probe so a game update that moves one fails it:

- The `true` third `KeyedCodec` argument (`strict_null`) never rejects an omitted key, on any path.
  It only changes an explicit `null` on the BSON inherit path.
- A key rejects its omission only if its validator chain holds a `NonNullValidator` instance
  (`nonNull()`, `nonEmptyArray()`, `nonEmptyMap()`) **and** its field is still null after
  construction. Of 545 null-validated keys in 1257 decodable classes, the engine rejects the
  omission of 258; 252 hold a non-null default.
- A Parent satisfies a nonNull key only if it is declared `appendInherited`.
- Codec-level validators and `afterDecode` hooks can reject an empty document with no key
  attached (5 classes); no per-key attribute sees them.

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
