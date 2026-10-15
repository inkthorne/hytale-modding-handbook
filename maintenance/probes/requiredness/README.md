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
