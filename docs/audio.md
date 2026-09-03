---
title: "Audio System"
description: "Define Hytale audio with JSON formats — multi-layer sound events with volume/pitch variation and spatial attenuation, audio categories for mixing, and ambient soundscapes."
seo:
  type: TechArticle
---

# Audio System

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Audio` · **Verified against 0.5.9**

Hytale's audio system is defined through JSON assets in `Server/Audio/`. The system supports multi-layer sound events, hierarchical audio categories for mixing, ambient soundscapes with environmental conditions, and spatial audio effects.

## Overview

Defined as a set of JSON asset formats under `Server/Audio/` and provides:
- Multi-layer sound events with volume/pitch variation, looping, and spatial attenuation
- Hierarchical audio categories for volume mixing (with `Parent` inheritance)
- Ambient soundscapes (beds, emitters, music) gated by environmental conditions
- Equalizer and reverb presets for environmental filtering
- Item sound sets for inventory drag/drop interactions
- Named sound-event collections (sound sets) referenced by other systems

## Architecture
```
Server/Audio/
├── SoundEvents/      core sound units (Layers → Files, RandomSettings, attenuation)
│   └── SFX_Attn_*    shared attenuation parent presets (inherited via Parent)
├── AudioCategories/  volume mixing groups (Parent inheritance)
├── AmbienceFX/       ambient soundscapes
│   ├── AmbientBed    continuous looping Track
│   ├── Sounds        periodic emitters (SoundEventId, Frequency, Radius)
│   ├── Music         track playlists (legacy — superseded by MusicContainers, auto-migrated)
│   └── Conditions    Environment/Weather tag patterns, light/time/altitude/walls
├── MusicContainers/  composable music graph (Update 5): SingleTrack / Random / Sequence / Horizontal / Segment
├── AudioStates/      named state axes (Values, DefaultTransition) that Segment layers/StateBindings react to
├── EQ/               equalizer presets (4-band parametric)
├── Reverb/           environment reverb presets
├── ItemSounds/       ISS_* inventory drag/drop sound sets
└── SoundSets/        named sound-event collections
```

## Key Classes

| Section | Location | Description |
|---------|----------|-------------|
| Sound Event | `Server/Audio/SoundEvents/*.json` | Layered sound definition with variation and attenuation |
| Attenuation Preset | `Server/Audio/SoundEvents/SFX_Attn_*.json` | Shared `MaxDistance`/`StartAttenuationDistance` parents |
| Audio Category | `Server/Audio/AudioCategories/*.json` | Volume mixing group with `Parent` inheritance |
| Ambience | `Server/Audio/AmbienceFX/Ambience/*.json` | Conditional soundscape (bed + emitters) |
| Music | `Server/Audio/AmbienceFX/Music/*.json` | Background music track playlists (legacy — see MusicContainer) |
| Music Container | `Server/Audio/MusicContainers/*.json` | Composable music graph (Update 5): single track, random/sequence playlists, horizontal/segment layering |
| Audio State | `Server/Audio/AudioStates/*.json` | Named state axis (`Values`, `DefaultValue`, `DefaultTransition`) driving `StateBindings` |
| EQ Preset | `Server/Audio/EQ/*.json` | 4-band parametric equalizer settings |
| Reverb Preset | `Server/Audio/Reverb/*.json` | Acoustic environment reverb settings |
| Item Sounds | `Server/Audio/ItemSounds/ISS_*.json` | Inventory drag/drop sound set (`ItemSoundSetId`) |
| Sound Set | `Server/Audio/SoundSets/*.json` | Named sound-event collection |

## Quick Navigation

| Section | Directory | Files | Description |
|---------|-----------|-------|-------------|
| [SoundEvents](#soundevents) | `SoundEvents/` | 1,213 | Individual sound definitions with layers |
| [AudioCategories](#audiocategories) | `AudioCategories/` | 103 | Volume/mixing groups with inheritance |
| [AmbienceFX](#ambiencefx) | `AmbienceFX/` | 206 | Ambient soundscapes with conditions |
| [MusicContainer](#musiccontainer) | `MusicContainers/` | 212 | Composable music graph (Update 5) |
| [AudioState](#audiostate-transitions) | `AudioStates/` | 2 | Named state axes for music/ambience bindings |
| [EQ](#eq-equalizer) | `EQ/` | 2 | Equalizer presets |
| [Reverb](#reverb) | `Reverb/` | 28 | Environment reverb settings |
| [ItemSounds](#itemsounds) | `ItemSounds/` | 36 | Inventory drag/drop sounds |
| [SoundSets](#soundsets) | `SoundSets/` | 1 | Named sound event collections |

**Total: 1,803 audio asset files** (counts as of 0.6.3)

---

## SoundEvents

**Location:** `Server/Audio/SoundEvents/`

Sound events are the core audio units. Each defines one or more sound layers, volume/pitch variation, looping behavior, and spatial attenuation.

### Directory Structure

```
SoundEvents/
├── BlockSounds/     - Per-material break/build/hit/harvest/walk/land sounds
├── SFX/             - Player, NPC, weapons, UI, effects, etc.
│   ├── Chests/
│   ├── Crafting/
│   ├── CreativePlay/
│   ├── Deployables/
│   ├── Effects/
│   ├── Items/
│   ├── Magic/
│   ├── NPC/
│   ├── Player/
│   ├── Projectiles/
│   ├── Test/
│   ├── Tools/
│   ├── UI/
│   ├── Utility/
│   └── Weapons/
├── Environments/    - Environmental emitters
└── SFX_Attn_*.json  - Shared attenuation parent presets (see Parent Inheritance)
```

### Properties

Top-level keys (`SoundEvent.CODEC`):

| Property | Type | Description |
|----------|------|-------------|
| `Layers` | array | One or more concurrent sound layers (see below). Sound files are referenced only via `Files` inside a layer — there is no top-level `Files` field |
| `Volume` | float | Base volume in dB (default: 0) |
| `Pitch` | float | Base pitch offset (rare — 23 assets) |
| `SpatialBlend` | float | 2D↔3D blend for positioned playback (125 assets) |
| `PreventSoundInterruption` | boolean | Don't interrupt if already playing |
| `MaxInstance` | int | Maximum concurrent instances |
| `Parent` | string | Inherit from another sound event (generic asset inheritance) |
| `AudioCategory` | string | Mixing category reference |
| `MaxDistance` | float | Distance at which sound is silent |
| `StartAttenuationDistance` | float | Distance at which falloff begins |
| `StateBindings` | array | Per-[AudioState](#audiostate-transitions) volume/pitch deltas (`AudioState` + `Deltas`) |
| `DuckingRules` | array | Duck other categories while this event plays — see [Ducking](#ducking) (0.6.3+) |
| `BypassDucking` | boolean | Exempt this event from ducking applied to its category (0.6.3+) |

`Looping`, `StartDelay`, `Probability`, `RandomSettings` and `RoundRobinHistorySize` are **per-layer** keys
(`SoundEventLayer.CODEC`), not top-level — no shipped sound event sets them at the top level:

| Layer property | Type | Description |
|----------------|------|-------------|
| `Files` | array | `.ogg` paths rooted at `Common/Sounds/`; one is picked per play |
| `Volume` | float | Layer volume in dB |
| `StartDelay` | float | Delay before the layer starts (seconds) |
| `FadeIn` | float | Fade-in length (0.6.3+; `getFadeIn()`) |
| `Looping` | boolean | Whether the layer loops continuously |
| `Probability` | int | Chance to play the layer |
| `ProbabilityRerollDelay` | float | Delay before re-rolling a failed probability check |
| `RandomSettings` | object | Pitch/volume variation (see below) |
| `RoundRobinHistorySize` | int | Prevents repeating the same file in sequence |

### Layer System

Every sound event holds its files in one or more layers. Each layer has its own
`Files` array plus optional per-layer `Volume`, `RandomSettings`, `StartDelay`, `FadeIn`, and
`Looping`. Layers play concurrently (e.g. an impact layer plus a debris layer):

```json
{
  "AudioCategory": "AudioCat_BlockSounds",
  "Layers": [
    {
      "Files": [
        "Sounds/Blocks/Stone/Stone_Break_01.ogg",
        "Sounds/Blocks/Stone/Stone_Break_02.ogg"
      ],
      "RandomSettings": {
        "MinVolume": -1,
        "MinPitch": -3,
        "MaxPitch": 3
      },
      "StartDelay": 0,
      "Volume": 6
    },
    {
      "Files": [
        "Sounds/Blocks/Stone/Stone_Break_Debris_01.ogg",
        "Sounds/Blocks/Stone/Stone_Break_Debris_03.ogg"
      ],
      "StartDelay": 0.1,
      "Volume": -4
    }
  ],
  "Volume": 0,
  "PreventSoundInterruption": true,
  "Parent": "SFX_Attn_Quiet"
}
```

Sound file paths are rooted at `Common/Sounds/`. Real top-level prefixes include
`Sounds/Blocks`, `Sounds/Weapons`, `Sounds/NPC`, `Sounds/Environments`,
`Sounds/PlayerActions`, `Sounds/Items`, `Sounds/Movement`, `Sounds/Projectiles`,
`Sounds/UI`, `Sounds/Tools`, `Sounds/Magic`, `Sounds/Effects`, `Sounds/Deployables`,
`Sounds/CreativePlay`, and `Sounds/Crafting`. There is no `SFX/` segment in any
sound file path.

**Java side:** each layer decodes into a
`com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEventLayer`
(`SoundEventLayer.CODEC`; a `NetworkSerializable<protocol.SoundEventLayer>` with `toPacket()`).
Read-only getters mirror the JSON: `getFiles()`, `getVolume()` (resolved linear volume, not the
raw dB), `getStartDelay()`, `getFadeIn()`, `isLooping()`, `getProbability()`, `getProbabilityRerollDelay()`,
`getRandomSettings()`, `getRoundRobinHistorySize()`, plus `getHighestNumberOfChannels()`
(computed from the referenced `.ogg` files). The nested `SoundEventLayer.RandomSettings`
exposes `getMinVolume()` / `getMaxVolume()` / `getMinPitch()` / `getMaxPitch()` /
`getMaxStartOffset()` and a `RandomSettings.DEFAULT` instance.

### RandomSettings

Add variation to prevent repetitive sounds:

| Property | Type | Description |
|----------|------|-------------|
| `MinPitch` | float | Minimum pitch multiplier (default: 1.0) |
| `MaxPitch` | float | Maximum pitch multiplier (default: 1.0) |
| `MinVolume` | float | Minimum volume offset in dB |
| `MaxVolume` | float | Maximum volume offset in dB |

### Parent Inheritance

Sound events can inherit from presets to share attenuation settings (`MaxDistance` /
`StartAttenuationDistance`). The shared attenuation presets live as `SFX_Attn_*.json`
files at the root of `SoundEvents/`:

```json
{
  "Layers": [
    {
      "Files": ["Sounds/Weapons/Mace/Mace_T2_Signature_Impact_01.ogg"],
      "Volume": -2
    }
  ],
  "Parent": "SFX_Attn_Loud"
}
```

Real attenuation presets (quietest to loudest), with their distances as shipped in 0.6.3:

| Preset | `StartAttenuationDistance` | `MaxDistance` |
|--------|---------------------------|---------------|
| `SFX_Attn_ExtremelyQuiet` | 1 | 5 |
| `SFX_Attn_VeryQuiet` | 2 | 10 |
| `SFX_Attn_Quiet` | 4 | 15 |
| `SFX_Attn_Moderate` | 8 | 25 |
| `SFX_Attn_Loud` | 15 | 45 |
| `SFX_Attn_VeryLoud` | 25 | 70 |

All six presets also set `"AudioCategory": "AudioCat_SFX"`, so a child that omits `AudioCategory`
inherits the SFX mix bus. `SFX_Attn_Moderate` (519) and `SFX_Attn_Quiet` (397) account for the large
majority of the ~1,000 `Parent` references. A sound event may also inherit from another concrete
sound event (e.g. `SFX_Stone_Break`, `SFX_Mud_Walk`).

### Examples

**Block Sound (`SFX_Glass_Break`, multi-file with variation):**

```json
{
  "AudioCategory": "AudioCat_BlockSounds",
  "Layers": [
    {
      "Files": [
        "Sounds/Blocks/Glass/Glass_Break_01.ogg",
        "Sounds/Blocks/Glass/Glass_Break_02.ogg",
        "Sounds/Blocks/Glass/Glass_Break_03.ogg",
        "Sounds/Blocks/Glass/Glass_Break_04.ogg",
        "Sounds/Blocks/Glass/Glass_Break_05.ogg"
      ],
      "Volume": 6.0,
      "RoundRobinHistorySize": 2,
      "RandomSettings": {
        "MinPitch": -1,
        "MaxPitch": 1,
        "MinVolume": -1
      }
    }
  ],
  "PreventSoundInterruption": true,
  "Volume": 0,
  "Parent": "SFX_Attn_Quiet"
}
```

**Attenuation Preset (`SFX_Attn_Loud`, defines distance falloff for children):**

```json
{
  "AudioCategory": "AudioCat_SFX",
  "Layers": [
    {
      "Files": ["Sounds/TEST/SFX_Test_Blip_A.ogg"],
      "RandomSettings": {
        "MinPitch": 0,
        "MaxPitch": 0,
        "MinVolume": 0
      },
      "Volume": 6.0
    }
  ],
  "Volume": 0,
  "MaxDistance": 45,
  "StartAttenuationDistance": 15
}
```

**Looping Sound (`SFX_Candle_Loop`):**

```json
{
  "AudioCategory": "AudioCat_Ambient",
  "Layers": [
    {
      "Files": ["Sounds/Items/Candle/Candle_Loop_01.ogg"],
      "Volume": -6.0,
      "RandomSettings": {
        "MinPitch": 0,
        "MaxPitch": 0,
        "MinVolume": 0,
        "MaxStartOffset": 10
      },
      "Looping": true
    }
  ],
  "Volume": 0,
  "Parent": "SFX_Attn_ExtremelyQuiet"
}
```

---

## AudioCategories

**Location:** `Server/Audio/AudioCategories/`

Audio categories define volume mixing groups with hierarchical inheritance. They allow grouping sounds for volume control (e.g., all NPC sounds, all weapon sounds).

### Directory Structure

```
AudioCategories/
├── AudioCat_*.json  - Root buses and top-level groups (Music, Ambient, SFX, UI, Voice, NPC, ...)
├── NPC/             - Per-NPC audio categories (AudioCat_NPC_Wolf, ...)
├── UI/              - UI sub-categories (AudioCat_UI_Sleep)
└── Weapons/         - Per-weapon audio categories (AudioCat_Sword, ...)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Volume` | float | Volume adjustment in dB (can be negative) |
| `Parent` | string | Parent category for inheritance |
| `StateBindings` | array | Per-[AudioState](#audiostate-transitions) deltas (`AudioState` + `Deltas`) |
| `DuckingRules` | array | Duck other categories while anything in this category plays — see [Ducking](#ducking) (0.6.3+) |
| `MaxDuckingDb` | float | Cap on how far *this* category can be ducked by others (0.6.3+) |

### Hierarchy Example

```json
// AudioCat_SFX.json (well-known root bus)
{
  "Volume": 0
}

// AudioCat_NPC.json
{
  "Parent": "AudioCat_SFX",
  "Volume": 0
}

// NPC/AudioCat_NPC_Wolf.json
{
  "Volume": 0,
  "Parent": "AudioCat_NPC"
}
```

### Common Categories

The five **well-known root buses** are named as constants on
`com.hypixel.hytale.server.core.asset.type.audiocategory.config.AudioCategory`
(`AudioCategory.MUSIC` / `AMBIENT` / `SFX` / `VOICE` / `UI`, collected in `AudioCategory.WELL_KNOWN_ROOT_NAMES`)
and every other category descends from one of them via `Parent`:

| Category | Parent | Purpose |
|----------|--------|---------|
| `AudioCat_Music` | — | Music bus (root) |
| `AudioCat_Ambient` | — | Ambience bus (root) |
| `AudioCat_SFX` | — | Sound-effects bus (root) |
| `AudioCat_UI` | — | User-interface bus (root) |
| `AudioCat_Voice` | — | Voice bus (root) |
| `AudioCat_Music_In_Game` | `AudioCat_Music` | In-game music containers (−14 dB) |
| `AudioCat_AmbientMusic` | `AudioCat_Ambient` | Ambient music; carries the shipped `DuckingRules` example |
| `AudioCat_BlockSounds` | `AudioCat_SFX` | Block break/build/hit sounds |
| `AudioCat_Footsteps` | `AudioCat_SFX` | Footstep sounds |
| `AudioCat_NPC` | `AudioCat_SFX` | NPC vocalizations |
| `AudioCat_Weapons` | `AudioCat_SFX` | Weapon sounds |
| `AudioCat_Discovery` | `AudioCat_UI` | Discovery / progression stingers |
| `AudioCat_Inventory` | `AudioCat_UI` | Inventory interaction sounds |

Sub-categories inherit via `Parent`. Examples:

- `AudioCat_NPC_*` (e.g. `AudioCat_NPC_Wolf`, `AudioCat_NPC_Dragon`) inherit `AudioCat_NPC`
- Per-weapon categories (e.g. `AudioCat_Sword`, `AudioCat_Battleaxe`, `AudioCat_Mace`, `AudioCat_Daggers`, `AudioCat_Shield`, `AudioCat_Shortbow`, `AudioCat_Hand_Crossbow`, `AudioCat_Magic_Staff`) inherit `AudioCat_Weapons`
- `AudioCat_UI_Sleep` inherits `AudioCat_UI`

### Ducking

As of 0.6.3 ducking is data-driven: a `DuckingRules` array on an audio category *or* on an individual
sound event lowers the volume of a **target category** while the source is audible. Each rule decodes
into `com.hypixel.hytale.server.core.asset.type.audiocategory.config.AudioCategoryDuckingRuleConfig`
(`AudioCategoryDuckingRuleConfig.CODEC`; targets must be unique per owner):

| Property | Type | Description |
|----------|------|-------------|
| `TargetCategory` | string | Category id to duck |
| `DuckingVolumeDb` | float | Attenuation applied to the target (dB; `MIN_DUCKING_DB` −100 … `MAX_DUCKING_DB` 0) |
| `AttackMs` / `HoldMs` / `ReleaseMs` | float | Envelope timings (ms, each ≤ `MAX_PHASE_MS` 60000) |
| `Curve` / `ReleaseCurve` | `FadeCurve` | `Linear` (default), `Logarithmic`, `Exponential`, `SCurve`, `EqualPowerSine` |
| `Priority` | int | Higher-priority rules win when several duck the same target |

The shipped example is `SFX/SFX_Memories_Bench_Ducker.json` — a silent looping event whose only job is
to duck music and NPC/block sounds while it plays:

```json
{
  "AudioCategory": "AudioCat_Ambient",
  "Layers": [{ "Files": ["Sounds/Silence.ogg"], "Looping": true, "Volume": 6.0 }],
  "Volume": 0,
  "MaxDistance": 7,
  "PreventSoundInterruption": true,
  "DuckingRules": [
    { "TargetCategory": "AudioCat_Music", "DuckingVolumeDb": -6,   "AttackMs": 1000, "ReleaseMs": 5000, "Curve": "SCurve", "ReleaseCurve": "SCurve" },
    { "TargetCategory": "AudioCat_NPC",   "DuckingVolumeDb": -100, "AttackMs": 1000, "ReleaseMs": 5000, "Curve": "SCurve", "ReleaseCurve": "SCurve" }
  ]
}
```

A sound event can opt out of ducking aimed at its category with `"BypassDucking": true`; a category can
clamp incoming ducking with `MaxDuckingDb`. (The 0.5.9 per-event `MusicDuckingVolume` /
`AmbientDuckingVolume` fields and their getters were removed by 0.6.3 — use `DuckingRules`.)

---

## AmbienceFX

**Location:** `Server/Audio/AmbienceFX/`

Ambient audio defines soundscapes that play based on environmental conditions. Includes ambient beds (continuous background), emitter sounds (periodic triggers), and music.

### Directory Structure

```
AmbienceFX/
├── Ambience/      - Ambient soundscapes (beds + emitters)
│   ├── Global/      - Cave, Dungeon, Interior, Lava, Mage_Tower, Mineshaft, Underwater, Weather
│   ├── Zone1/ ... Zone4/  - Per-zone Environments/ and Global/
│   └── Unique/      - Named locations (Forgotten_Temple, Dread_Wade, ...)
├── Music/         - Music selectors (Global/, Zone0/ ... Zone4/, Unique/) — Conditions + a MusicContainer reference
├── ReverbZones/   - Reverb zone definitions (Cave/, Exterior/, Interior/, Prefabs/ — Rev_Zone_*.json)
├── States/        - Ambience definitions that only write AudioStates (SetStates)
├── AmbFX_*.json   - Top-level ambience definitions (AmbFX_Void, AmbFX_Placeholder)
└── Z2_Dungeon.json
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Conditions` | object | When this ambience plays |
| `AmbientBed` | object | Continuous background sound |
| `Sounds` | array | Triggered emitter sounds |
| `MusicContainer` | string or object | Music to play — a [MusicContainer](#musiccontainer) id, or an inline container that inherits one via `Parent` |
| `Music` | object | **Legacy** background music configuration (see below) |
| `SoundEffect` | object | Environmental filtering: `ReverbEffectId`, `EqualizerEffectId`, `IsInstant` |
| `AudioCategory` | string | Mixing category (`AudioCat_Ambient` for soundscapes; music selectors put the category on the container) |
| `Priority` | int | Selection priority when multiple definitions match |
| `BlockedAmbienceFxIds` | array | Other ambience ids suppressed while this one is active |
| `SetStates` | array | [AudioState](#audiostate-transitions) writes (`AudioState`, `Value`, optional `TransitionOverride`) applied while active |

### Conditions System

Conditions determine when ambient audio plays:

| Condition | Type | Description |
|-----------|------|-------------|
| `EnvironmentIds` | array | Specific environment IDs |
| `EnvironmentTagPattern` | object | Tag pattern matching (see below) |
| `WeatherTagPattern` | object | Weather condition matching |
| `SunLightLevel` | object | Light level range (Min/Max, 0-15) |
| `DayTime` | object | Time of day range (Min/Max, hours; Min may be greater than Max to wrap past midnight) |
| `Altitude` | object | Height range (Min/Max) |
| `Walls` | object | Range (Min/Max) for the number of surrounding walls (enclosure) |
| `Shelter` | string | Enclosure classification: `Any`, `Open`, `Partial`, `Sheltered`, `Enclosed` (`ShelterType`; the most-used condition after tag patterns) |
| `RoofState` | string | `Any`, `Roofed`, `Unroofed` |
| `Roof` / `Floor` | boolean | Require (or forbid) a roof / floor |
| `WeatherIds` | array | Specific weather ids (alternative to `WeatherTagPattern`) |
| `TorchLightLevel` / `GlobalLightLevel` | object | Additional light ranges (Min/Max) |
| `SurfacePhysicalMaterials`, `ExteriorRoofPhysicalMaterials`, `SurroundingBlockSoundSets` | array | Material-composition conditions (`PhysicalMaterialId`/`BlockSoundSetId` + `Percent`) |
| `Never` | boolean | Disable the definition without deleting it |

(Every condition is optional; `AmbienceFXConditions.CODEC` also accepts `Space`/`SpaceScale*Range`,
`RoofDistanceRange`, `RoofMaterialTagPattern`, `FluidFXIds` and ray-based `*CoeffRange` keys, all rarely used.)

### Tag Patterns

Tag patterns use boolean logic to match environment/weather tags. Each node has an
`Op` field; the rest of the node depends on the operator:

```json
{
  "EnvironmentTagPattern": {
    "Op": "And",
    "Patterns": [
      { "Op": "Equals", "Tag": "Zone3" },
      { "Op": "Not", "Pattern": { "Op": "Equals", "Tag": "Dungeons" } }
    ]
  }
}
```

**Operators:**
- `Equals` - Exact tag match; uses a `Tag` string
- `And` - All sub-patterns must match; uses a `Patterns` array
- `Or` - Any sub-pattern must match; uses a `Patterns` array
- `Not` - Inverts a single nested `Pattern`

### AmbientBed

Continuous looping background sound. The bed references an `.ogg` file directly via
`Track` (not a sound event):

```json
{
  "AmbientBed": {
    "Track": "Sounds/Environments/Zone3/Environments/Frozen/Night/Z3_Frozen_Night_Stereo_LOOP.ogg",
    "Volume": 3.0
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Track` | string | Path to the looping `.ogg` file (rooted at `Common/Sounds/`) |
| `Volume` | float | Volume in dB |
| `TransitionSpeed` | string | Crossfade speed when the bed changes (`Fast`, `Instant`, …) |
| `StateBindings` | array | Per-[AudioState](#audiostate-transitions) deltas |

### Emitter Sounds

Periodic triggered sounds with spatial positioning. Each entry references a sound
event by `SoundEventId` and uses `Frequency` and `Radius` ranges (each an
object with `Min`/`Max`):

```json
{
  "Sounds": [
    {
      "SoundEventId": "SFX_Z3_Forest_Day_Birds",
      "Play3D": "Random",
      "Radius": {
        "Min": 5,
        "Max": 10
      },
      "Frequency": {
        "Min": 2,
        "Max": 5
      }
    },
    {
      "SoundEventId": "SFX_Z3_Emit_Tree_Creak",
      "Frequency": { "Min": 5, "Max": 10 },
      "Radius": { "Min": 0, "Max": 10 },
      "Play3D": "LocationNameRandom",
      "BlockSoundSetId": "Wood"
    }
  ]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `SoundEventId` | string | Sound event to trigger |
| `Frequency` | object | `Min`/`Max` range controlling how often the sound triggers |
| `Radius` | object | `Min`/`Max` spawn distance range from the player |
| `Play3D` | string | Emitter placement: `Random` (anywhere in `Radius`), `LocationNameRandom` / `LocationName` (on a block whose sound set matches `BlockSoundSetId`) |
| `BlockSoundSetId` | string | Block sound set the emitter must be placed on (with `Play3D: LocationName*`) |
| `Altitude` | string | `Normal`, `Lowest`, `Highest`, `Random` — vertical placement preference |
| `SunlightRange` | object | `Min`/`Max` sunlight at the emitter position |
| `MaxBodiesPerEmitter` | int | Cap on simultaneous instances per emitter |
| `StateBindings` | array | Per-[AudioState](#audiostate-transitions) deltas |

(Each entry decodes into `com.hypixel.hytale.server.core.asset.type.ambiencefx.config.AmbienceFXSound`
— `getSoundEventId()`, `getPlay3D()`, `getBlockSoundSetId()`, `getAltitude()`, `getFrequency()`, `getRadius()`,
`getMaxBodiesPerEmitter()`.)

### Music Configuration

Music selectors under `AmbienceFX/Music/` pair `Conditions` and a `Priority` with a
**`MusicContainer`** reference. The value is either a container id string or an inline container
object that inherits one through `Parent` (both forms decode through `MusicContainer.CHILD_ASSET_CODEC`);
the inline form lets the selector override `AudioCategory`/`LoopCount` without a new container file.
`AmbienceFX/Music/Zone3/Mus_Zone3_Dungeon.json` as shipped in 0.6.3:

```json
{
  "Conditions": {
    "Altitude": { "Min": 0, "Max": 150 },
    "EnvironmentTagPattern": {
      "Op": "And",
      "Patterns": [
        { "Op": "Equals", "Tag": "Zone3" },
        { "Op": "Equals", "Tag": "Dungeons" }
      ]
    }
  },
  "MusicContainer": {
    "Parent": "Track_Z3D_Outlander_Dungeon",
    "AudioCategory": "AudioCat_Music_In_Game",
    "LoopCount": 0
  },
  "Priority": 80
}
```

The string form is equally common (`"MusicContainer": "MC_Zone4_Jungle"`). On the Java side
`AmbienceFX.getMusicContainerIndex()` returns the resolved container index.

> **Legacy `Music` block (Update 5).** The older `Music` object (`Tracks` — an array of plain `.ogg`
> paths rooted at `Common/`, typically under `Music/` — plus optional `Volume` in dB, −100 to 10) is
> **deprecated** (the codec's own documentation string reads "Deprecated: Use MusicContainer instead.")
> and is **auto-migrated at runtime** into a generated `RandomMusicContainer`
> (`RandomMusicContainer.fromLegacy(...)`, fed by `AmbienceFX.consumeLegacyMusic()`). As of 0.6.3 only
> one shipped asset still uses it (`AmbFX_Void.json`, `"Music": { "Tracks": ["Music/Unique/Silence.ogg"], "Volume": -10 }`).
> It decodes into `com.hypixel.hytale.server.core.asset.type.ambiencefx.config.AmbienceFXMusic`
> (`AmbienceFXMusic.CODEC`; both fields inherit through `Parent`) — `getTracks()`, `getDecibels()` (raw dB),
> `getVolume()` (linear gain), and an `AmbienceFXMusic(String[] tracks, float decibels)` constructor.
> Author new music as MusicContainer assets.

### Complete Example

```json
{
  "Conditions": {
    "SunLightLevel": { "Min": 10, "Max": 15 },
    "DayTime": { "Min": 5, "Max": 19 },
    "EnvironmentIds": ["Env_Zone3_Forests"],
    "WeatherTagPattern": {
      "Op": "Not",
      "Pattern": { "Op": "Equals", "Tag": "Rain" }
    },
    "Walls": { "Min": 0, "Max": 3 }
  },
  "Sounds": [
    {
      "SoundEventId": "SFX_Z3_Forest_Day_Birds",
      "Play3D": "Random",
      "Frequency": { "Min": 2, "Max": 5 },
      "Radius": { "Min": 5, "Max": 10 }
    }
  ]
}
```

---

## MusicContainer

**Location:** `Server/Audio/MusicContainers/`

New in Update 5. A **music container** is a node in a small graph that describes *how* music plays — a single track,
a weighted-random or sequential playlist, or layered/segmented arrangements that crossfade with game state. Each
`.json` file is one container, keyed by its **id** (the filename without `.json`); containers reference each other
by id, so you compose larger arrangements from smaller ones. This replaces the flat
[AmbienceFX `Music` block](#music-configuration), which is now auto-migrated into a generated `RandomMusicContainer`;
an ambience selects music with its `MusicContainer` key. 212 containers ship in 0.6.3 (`Playlists/MC_*` selectors
and `Tracks/Track_*` leaves).

> The folder layout (`Tracks/`, `Playlists/`, …) is just organization — every `.json` under `MusicContainers/`
> loads as a container regardless of subfolder.

### Container types

The object's `"Type"` field selects the container kind:

| `Type` | Class | Plays |
|--------|-------|-------|
| `SingleTrack` | `SingleTrackMusicContainer` | One audio file (`Track`, an `.ogg` path under `Common/Sounds/`) |
| `Random` | `RandomMusicContainer` | A `Children` list picked by weight; `Mode` is `Random` or `Shuffle` |
| `Sequence` | `SequenceMusicContainer` | A `Children` list in order |
| `Horizontal` | `HorizontalMusicContainer` | Phases (`Children`) transitioned horizontally with a default phase transition |
| `Segment` | `SegmentMusicContainer` | Simultaneous `Layers` mixed/crossfaded by audio state (bar/beat aligned) |

### Common fields

All container types share these (from the `MusicContainer` base; omit any you don't need):

| Field | Type | Description |
|-------|------|-------------|
| `Type` | string | Discriminator — one of the types above |
| `AudioCategory` | string | Mixing category (commonly `AudioCat_Music_In_Game`) |
| `NameTranslationKey` | string | i18n key for the displayed track name |
| `Volume` | float | Volume in dB |
| `LoopCount` | int | Times to loop (`0` = forever) |
| `Weight` | float | Selection weight when this container is a child of a `Random` container |
| `SilenceAfter` / `ExitSilence` | range | `{ "Min": s, "Max": s }` silence (seconds) after playing / on exit |
| `FadeInDuration` / `FadeOutDuration` | float | Fades (seconds) |
| `TransitionType` | enum | `Crossfade`, `FadeOutFadeIn`, or `Immediate` |
| `TransitionDuration` | float | Transition length (seconds) |
| `PlayToCompletion` | bool | Finish the current track before transitioning |
| `ResumeMemoryDuration` | float | How long (seconds) the container remembers its position to resume from |
| `Tempo` | object | `Bpm` (1–1000), `BeatsPerBar`, `BeatValue` (1–32) — needed for bar/beat-aligned markers |
| `StateBindings` | array | Per-[AudioState](#audiostate-transitions) deltas |

### SingleTrack

The leaf — points at one audio file:

```json
{ "Type": "SingleTrack", "Track": "Music/Caves/Z1_Cave_Shallow_01.ogg" }
```

### Random / Sequence

A playlist of child containers referenced by id under `Children` (each entry is an inline container that
inherits the referenced one via `Parent`, plus optional per-child overrides such as `SilenceAfter` / `Weight` — the
same `CHILD_ASSET_CODEC` an ambience's `MusicContainer` key uses). `Random` shuffles/weights (`Mode`: `Random` or
`Shuffle`); `Sequence` plays in order. `Tracks/MC_Z1_Caves.json` (truncated):

```json
{
  "Type": "Random",
  "AudioCategory": "AudioCat_Music_In_Game",
  "Mode": "Random",
  "LoopCount": 0,
  "AvoidRepeatCount": 3,
  "ExitSilence": { "Min": 10, "Max": 20 },
  "Children": [
    { "Parent": "Track_Z1_Cave_01", "SilenceAfter": { "Min": 10, "Max": 20 } },
    { "Parent": "Track_Z1_Cave_02", "SilenceAfter": { "Min": 10, "Max": 20 } },
    { "Parent": "Track_Silence", "Weight": 0.95 }
  ]
}
```

`AvoidRepeatCount` (Random only) avoids replaying the last *n* picks. Children are other container ids — here
`SingleTrack` tracks and a silence track.

### Horizontal

Phases that transition horizontally (e.g. exploration → combat) sharing a tempo. Adds
`DefaultPhaseTransitionType` (a `MusicTransitionType`) and `DefaultPhaseTransitionDuration`; `Children` are the phase
containers.

### Segment (layered)

Simultaneous **layers** mixed by **audio state** — the engine's cave music uses this to crossfade between shallow /
volcanic / deep beds as the player moves. Each `LayerPlacement` has a `Name`, a nested `Container`, an optional
`ClipStart`, and `StateBindings` that adjust each layer's volume (or `Mute`) per audio-state value. `EntryMarker` /
`ExitMarker` are bar/beat-aligned points (`BarBeatDuration` = `bars` + `beats` + `ms`).

```json
{
  "Type": "Segment",
  "AudioCategory": "AudioCat_Music_In_Game",
  "LoopCount": 1,
  "Layers": [
    {
      "Name": "shallow",
      "Container": { "Type": "SingleTrack", "Track": "Music/Caves/Z1_Cave_Shallow_01.ogg" },
      "StateBindings": [
        {
          "AudioState": "AudioState_CaveRegion",
          "Deltas": [
            { "Value": "Shallow",  "VolumeDb": 0.0 },
            { "Value": "Volcanic", "Mute": true },
            { "Value": "Deep",     "Mute": true }
          ]
        }
      ]
    }
  ]
}
```

### Referencing a container

Containers are referenced by id — by other containers (`Children` / `Parent`, layer `Container`) and by gameplay.
The Trigger Volume [`SetMusic` effect](trigger-volumes.md#built-in-effect-types) takes a `MusicContainer` id, and a
plugin can build one in Java via the `*MusicContainer` config classes
(`com.hypixel.hytale.server.core.asset.type.musiccontainer.config`) — each has a `getChildIds()` and a `CODEC`;
`MusicContainer.getAssetMap()` resolves ids. The legacy migration path is `RandomMusicContainer.fromLegacy(...)`.

> The 0.6.3 wire format (`com.hypixel.hytale.protocol.MusicContainer`) carries extra per-container fields — `exitAt`
> (`MusicSync`), `align` (`DestinationAlign`), `alignMarkerName`, `stingers` (`StingerBinding[]`), and `markers`
> (`MusicMarker[]`) on segments — but the server config codecs expose **no JSON keys** for them yet, so they cannot be
> authored in assets.

---

## AudioState Transitions

**Location:** `Server/Audio/AudioStates/` · **Package:** `com.hypixel.hytale.server.core.asset.type.audiostate.config`

`AudioState` assets define the named state axes (e.g. `AudioState_CaveRegion` with values
`Shallow` / `Volcanic` / `Deep`) that a [Segment container's](#segment-layered) `StateBindings`
react to (and that an ambience's `SetStates` writes). Two ship in 0.6.3: `AudioState_CaveRegion`
(client-authoritative) and `AudioState_Test_EncounterIntensity` (server-authoritative):

```json
{
  "Authority": "Client",
  "Values": ["Shallow", "Volcanic", "Deep"],
  "DefaultValue": "Shallow",
  "DefaultSyncTo": "Immediate",
  "DefaultTransition": { "DurationMs": 2000.0, "Curve": "SCurve" }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Authority` | `Server` / `Client` | Which side owns the value (`AudioState.getAuthority()`) |
| `Values` | array | Ordered value names (`getValues()`) |
| `DefaultValue` | string | Initial value (`getDefaultValue()` / `getDefaultValueIndex()`) |
| `DefaultSyncTo` | `SyncPoint` | Default musical sync point for switches |
| `DefaultTransition` | object | Fallback edge (a `StateTransitionConfig` without `From`/`To`) |
| `Transitions` | array | Per-edge overrides (below) |
| `RevertWhenInactive` | boolean | Return to `DefaultValue` when nothing is writing the state |

An audio state's `Transitions` array declares per-edge fade behaviour; each edge
decodes into a **`StateTransitionConfig`** (`StateTransitionConfig.CODEC`):

| Property | Type | Description |
|----------|------|-------------|
| `From` | string | State value name this edge transitions from; `"*"` for wildcard |
| `To` | string | State value name this edge transitions to; `"*"` for wildcard |
| `DurationMs` | float | Transition duration in milliseconds (≥ 0) |
| `Curve` | `FadeCurve` | `Linear`, `Logarithmic`, `Exponential`, `SCurve`, `EqualPowerSine` |
| `SyncTo` | `SyncPoint` | `Immediate`, `NextBeat`, `NextBar`, `ExitMarker`, or `NextMarker` (0.6.3+) |

```java
public class StateTransitionConfig {
    public static final String WILDCARD = "*";
    public static final int WILDCARD_INDEX = -1;
    public static final BuilderCodec<StateTransitionConfig> CODEC;
    public StateTransition toPacket();   // protocol form, with names resolved to indices
}
```

The value name `*` is reserved for wildcard matching (an `AudioState` value literally named `*`
fails validation with `AudioState value name '*' is reserved for wildcard matching in transitions`).
When no edge matches a from/to pair, the asset's `DefaultTransition` (also a
`StateTransitionConfig`) applies; if that is omitted too, the switch is immediate (0 ms).

---

## EQ (Equalizer)

**Location:** `Server/Audio/EQ/`

Equalizer presets for audio filtering, typically used for environmental effects like underwater audio.

There are two EQ presets: `EQ_Default` and `EQ_Underwater`.

### Properties

A 4-band parametric equalizer (low shelf, two mid peaking bands, high shelf) defined
with flat fields — there are no nested band objects:

| Property | Type | Description |
|----------|------|-------------|
| `LowGain` | float | Low shelf gain in dB |
| `LowCutOff` | float | Low shelf cutoff frequency (Hz) |
| `LowMidGain` | float | Low-mid peaking gain in dB |
| `LowMidCenter` | float | Low-mid center frequency (Hz) |
| `LowMidWidth` | float | Low-mid bandwidth |
| `HighMidGain` | float | High-mid peaking gain in dB |
| `HighMidCenter` | float | High-mid center frequency (Hz) |
| `HighMidWidth` | float | High-mid bandwidth |
| `HighGain` | float | High shelf gain in dB |
| `HighCutOff` | float | High shelf cutoff frequency (Hz) |

### Example (EQ_Underwater)

```json
{
  "LowGain": 0,
  "LowCutOff": 300,
  "LowMidGain": -17.19,
  "LowMidCenter": 1000,
  "LowMidWidth": 1,
  "HighMidGain": -17.9,
  "HighMidCenter": 1500,
  "HighMidWidth": 1,
  "HighGain": -17.9,
  "HighCutOff": 4000
}
```

---

## Reverb

**Location:** `Server/Audio/Reverb/`

Reverb presets simulate acoustic environments. They are organized by biome/zone and
special locations rather than generic room shapes.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `DryGain` | float | Dry (unprocessed) signal gain in dB |
| `ModalDensity` | float | Modal density (texture of the reverb) |
| `Diffusion` | float | Echo density / diffusion |
| `Gain` | float | Overall reverb gain in dB |
| `HighFrequencyGain` | float | High-frequency gain in dB |
| `DecayTime` | float | Reverb tail duration (seconds) |
| `HighFrequencyDecayRatio` | float | HF decay relative to mid frequencies |
| `ReflectionGain` | float | Early reflection gain in dB |
| `ReflectionDelay` | float | Early reflection delay (seconds) |
| `LateReverbGain` | float | Late reverb gain in dB |
| `LateReverbDelay` | float | Late reverb delay (seconds) |
| `RoomRolloffFactor` | float | Distance-based attenuation factor |
| `AirAbsorbptionHighFrequencyGain` | float | Air absorption HF gain (field spelled as in the assets) |
| `LimitDecayHighFrequency` | boolean | Clamp HF decay time |

### Example (Rev_Cave)

```json
{
  "DryGain": 0,
  "ModalDensity": 1,
  "Diffusion": 1,
  "Gain": -10,
  "HighFrequencyGain": -8,
  "DecayTime": 3,
  "HighFrequencyDecayRatio": 1.3,
  "ReflectionGain": -10.4,
  "ReflectionDelay": 0.015,
  "LateReverbGain": -3,
  "LateReverbDelay": 0.02,
  "RoomRolloffFactor": 0,
  "AirAbsorbptionHighFrequencyGain": -0.05,
  "LimitDecayHighFrequency": false
}
```

### Presets

The 28 presets are biome/zone and location based:

| Preset | Description |
|--------|-------------|
| `Rev_Default` | Default fallback reverb |
| `Rev_Cave`, `Rev_Cave_Large`, `Rev_Ice_Cave`, `Rev_Tunnel` | Cave / tunnel acoustics |
| `Rev_Forest`, `Rev_Forest_Desert`, `Rev_Forest_Fog`, `Rev_Forest_Snow` | Forest biome variants |
| `Rev_Mountain`, `Rev_Mountain_Fog`, `Rev_Mountain_Snow` | Mountain biome variants |
| `Rev_Plains`, `Rev_Plains_Desert`, `Rev_Plains_Fog`, `Rev_Plains_Snow` | Plains biome variants |
| `Rev_Swamp`, `Rev_Swamp_Foggy` | Swamp biome variants |
| `Rev_Mineshaft` | Mineshaft interiors |
| `Rev_Temple`, `Rev_Temple_Grand` | Temple interiors |
| `Rev_Village` | Village ambience |
| `Rev_Mage_Tower` | Mage Tower interior |
| `Rev_Room_Dead`, `Rev_Room_Stone`, `Rev_Room_Wood`, `Rev_Sheltered` | Interior room / shelter presets used by `ReverbZones/Interior/` |
| `Rev_Reflective_Slap` | Hard reflective slap-back |

---

## ItemSounds

**Location:** `Server/Audio/ItemSounds/`

Item sounds define drag and drop sounds for inventory interactions. Items reference
these via `ItemSoundSetId` (1,656 references across the server assets). The files are
named `ISS_*.json` (e.g. `ISS_Armor_Cloth.json`, `ISS_Items_Metal.json`,
`ISS_Weapons_Wood.json`, `ISS_Default.json`).

### Properties

The `Drag` and `Drop` sound-event references are nested under a `SoundEvents` object:

| Property | Type | Description |
|----------|------|-------------|
| `SoundEvents.Drop` | string | Sound event when placing/dropping the item |
| `SoundEvents.Drag` | string | Sound event when picking up the item |

### Example (`ISS_Armor_Cloth.json`)

```json
{
  "SoundEvents": {
    "Drop": "SFX_Drop_Armor_Cloth",
    "Drag": "SFX_Drag_Armor_Cloth"
  }
}
```

### Integration with Items

In item definitions (`Server/Item/`), the `ItemSoundSetId` matches an `ISS_*` set name:

```json
{
  "Name": "Iron Sword",
  "ItemSoundSetId": "ISS_Items_Metal"
}
```

---

## SoundSets

**Location:** `Server/Audio/SoundSets/`

Sound sets group related sound events under named keys for reference by other systems.
The named keys are nested under a `SoundEvents` object, alongside a top-level
`Category` field naming the audio category. The only sound set is
`CreativePlayDefaults.json`.

### Example (`CreativePlayDefaults.json`, truncated)

```json
{
  "SoundEvents": {
    "Error": "SFX_Creative_Play_Error",
    "Rotate_Yaw": "SFX_Rotate_Yaw_Default",
    "Rotate_Pitch": "SFX_Rotate_Pitch_Default",
    "Eyedropper_Select": "SFX_Creative_Play_Eyedropper_Select",
    "Brush_Paint": "SFX_Creative_Play_Brush_Paint_Base",
    "Brush_Erase": "SFX_Creative_Play_Brush_Erase",
    "Paste": "SFX_Creative_Play_Paste"
  },
  "Category": "UI"
}
```

---

## Playing Sounds from Java

The JSON formats above *define* sounds; to actually **play** one from plugin code, call
`com.hypixel.hytale.server.core.universe.world.SoundUtil` (every method is `static`). The wire
packets (`PlaySoundEvent2D` / `PlaySoundEvent3D` / `PlaySoundEventLocalPlayer` /
`PlaySoundEventEntity`, in `com.hypixel.hytale.protocol.packets.world`) take an **`int` sound-event
index, not the string id** — `SoundUtil` is the wrapper that resolves, builds, and sends them.

### Resolving a sound-event index

Every method takes the sound event as an `int` index. Resolve a string id to its index through the
sound-event asset map:

```java
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;

int idx = SoundEvent.getAssetMap().getIndex("SFX_Sword_T2_Impact");
```

`getAssetMap()` returns an `IndexedLookupTableAssetMap<String, SoundEvent>`. `getIndex(id)` returns
**`Integer.MIN_VALUE` for an unknown id** and **`SoundEvent.EMPTY_ID` (`0`)** for the empty-sentinel
id — guard against both before playing:

```java
if (idx != Integer.MIN_VALUE && idx != SoundEvent.EMPTY_ID) {
    // safe to play
}
```

If you take the id from a command argument, `ArgTypes.SOUND_EVENT_ASSET` parses (with tab
completion) to a `SoundEvent`; call `.getId()` and resolve the index as above. See
[ArgTypes → Asset Types](commands.md#asset-types).

### SoundCategory

Every play call takes a `com.hypixel.hytale.protocol.SoundCategory` for mixing — one of `Music`,
`Ambient`, `SFX`, `UI`, `Voice`. (`ArgTypes.SOUND_CATEGORY` parses one from a command.)

### Choosing a method

| Method | Heard by | Use for |
|--------|----------|---------|
| `playSoundEvent2dToPlayer(PlayerRef, int idx, SoundCategory[, float vol, float pitch])` | one player, non-spatial | UI clicks, previews, local feedback |
| `playLocalPlayerSoundEvent(PlayerRef, int localIdx, int worldIdx, SoundCategory[, float vol, float pitch])` | one player | a local-vs-world paired sound |
| `playSoundEvent3d(int idx, SoundCategory, double x, double y, double z, ComponentAccessor<EntityStore>)` | everyone nearby, spatial | combat hits, world events |
| `playSoundEvent3d(int idx, SoundCategory, Vector3d pos, ComponentAccessor<EntityStore>)` | everyone nearby, spatial | same, with a JOML `Vector3d` |
| `playSoundEvent3d(int, SoundCategory, double x,y,z, float vol, float pitch, Predicate<Ref<EntityStore>>, ComponentAccessor<EntityStore>)` | nearby listeners that pass the predicate | spatial sound with a listener filter |
| `playSoundEvent3dToPlayer(Ref<EntityStore>, int, SoundCategory, double x,y,z[, float vol, float pitch], ComponentAccessor<EntityStore>)` | one player, spatial | a positioned sound for a single listener |
| `playSoundEvent2d(int idx, SoundCategory[, float vol, float pitch], ComponentAccessor<EntityStore>)` | every player in the world, non-spatial | a world-wide stinger/announcement (a `Ref<EntityStore>`-first overload targets one entity's viewer) |
| `playSoundEventEntity(int idx, int entityId[, float vol, float pitch], ComponentAccessor<EntityStore>)` | nearby, follows the entity | a sound attached to a moving entity |
| `playItemSoundEvent(Ref<EntityStore>, Store<EntityStore>, Item, ItemSoundEvent)` | — | an item's `Drag`/`Drop` inventory sound |

`Vector3d` is `org.joml.Vector3d` (see [math.md](math.md)). `vol`/`pitch` default to `1.0f` when
omitted and are **multipliers** layered on top of the sound event's own `Volume`/`RandomSettings`,
not absolute values.

### Example: a spatial impact sound on hit

```java
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.protocol.SoundCategory;

int idx = SoundEvent.getAssetMap().getIndex("SFX_Sword_T2_Impact");
if (idx != Integer.MIN_VALUE && idx != SoundEvent.EMPTY_ID) {
    SoundUtil.playSoundEvent3d(idx, SoundCategory.SFX, x, y, z, accessor);
}
```

`SoundUtil.playSoundEvent3d` is the same path the trigger-volume
[`PlaySound` effect](trigger-volumes.md#built-in-effect-types) and a JSON `WorldSoundEventId`
ultimately resolve to.

### Validating sound-event references in custom codecs

**Package:** `com.hypixel.hytale.server.core.asset.type.soundevent.validator`

When a custom asset/config field holds a sound-event **id string**, attach a validator so a bad
reference fails at load time instead of silently playing nothing. Beyond the generic existence
check (`SoundEvent.VALIDATOR_CACHE.getValidator()`), `SoundEventValidators` provides constants
that also check the *shape* of the referenced sound event:

```java
public class SoundEventValidators {
    public static final SoundEventValidators.LoopValidator LOOPING;     // must have a looping layer
    public static final SoundEventValidators.LoopValidator ONESHOT;     // must have no looping layer
    public static final SoundEventValidators.ChannelValidator MONO;     // highest channel count must be 1 (mono)
    public static final SoundEventValidators.ChannelValidator STEREO;   // highest channel count must be 2 (stereo)

    public static final ValidatorCache<String> MONO_VALIDATOR_CACHE;
    public static final ValidatorCache<String> STEREO_VALIDATOR_CACHE;
    public static final ValidatorCache<String> ONESHOT_VALIDATOR_CACHE;
}
```

Use the `*_VALIDATOR_CACHE.getValidator()` form in a `BuilderCodec` field, the same way
[`SleepSoundsConfig`](#sleep-sounds) attaches `SoundEvent.VALIDATOR_CACHE`:

```java
.append(new KeyedCodec<>("AlarmSound", Codec.STRING), MyCfg::setAlarm, MyCfg::getAlarm)
.addValidator(SoundEventValidators.ONESHOT_VALIDATOR_CACHE.getValidator())
.add()
```

The `has a looping layer and is not a oneshot sound` load error in
[Gotchas](#gotchas--errors) is the `ONESHOT` validator firing.

---

## Integration with Other Systems

### Block Sounds

A block type names a **block sound set** with `BlockSoundSetId` (1,595 block definitions do); the set is a
`Server/Item/Block/Sounds/<SetId>.json` (57 sets) that maps action keys to sound events, and decodes into
`com.hypixel.hytale.server.core.asset.type.blocksound.config.BlockSoundSet`:

```json
// Server/Item/Block/Sounds/Leaves.json
{
  "SoundEvents": {
    "Hit": "SFX_Leaves_Hit",
    "Break": "SFX_Leaves_Break",
    "Build": "SFX_Default_Build"
  }
}
```

Keys seen across the shipped sets: `Break`, `Build`, `Hit`, `Walk`, `Land`, `Harvest`, `MoveIn`, `MoveOut`,
`Clone` (plus a top-level `MoveInRepeatRange` and `Parent` inheritance). By convention the referenced sound
events live under `SoundEvents/BlockSounds/<Material>/`:

```
BlockSounds/
├── Bone/
│   ├── SFX_Bone_Break.json
│   ├── SFX_Bone_Build.json
│   ├── SFX_Bone_Hit.json
│   ├── SFX_Bone_Land.json
│   └── SFX_Bone_Walk.json
├── Stone/
│   ├── SFX_Stone_Break.json
│   ├── SFX_Stone_Harvest.json
│   └── ...
└── Wood/
    └── ...
```

Material directories include `Stone`, `Wood`, `Dirt`, `Grass`, `Sand`, `Gravel`,
`Metal`, `Glass`, `Ice`, `Snow`, `Mud`, `Leaves`, `Cloth`, `Bone`, and many more. The same set ids are what
an ambience emitter's `BlockSoundSetId` / `SurroundingBlockSoundSets` condition refers to.

### Interactions

Interactions can trigger sounds via `WorldSoundEventId` (spatial, heard by all nearby) or `LocalSoundEventId` (only heard by the acting player):

```json
{
  "Type": "Simple",
  "RunTime": 0.2,
  "Effects": {
    "WorldSoundEventId": "SFX_Sword_T1_Swing_Down",
    "LocalSoundEventId": "SFX_Sword_T1_Swing_Down_Local"
  }
}
```

See [interactions.md](interactions.md) for full interaction documentation.

### NPC Audio

Model assets reference sound events in their animation definitions. Each entry in an
animation set's `Animations` array (`ModelAsset.Animation`) supports two sound hooks:
`SoundEventId` — a sound event played with the animation — and `FootstepIntervals` —
an array of percentages (0–100) of the animation duration at which footsteps occur,
used for timing footstep sound effects on movement animations. From
`Server/Models/Human/Player.json`:

```json
{
  "AnimationSets": {
    "Run": {
      "Animations": [
        {
          "Animation": "Characters/Animations/Default/Run.blockyanim",
          "Speed": 0.9,
          "FootstepIntervals": [25, 75]
        }
      ]
    },
    "SafetyRoll": {
      "Animations": [
        {
          "Animation": "Characters/Animations/Roll/Roll.blockyanim",
          "BlendingDuration": 0.1,
          "Looping": false,
          "SoundEventId": "SFX_Player_Roll"
        }
      ]
    }
  }
}
```

### Weapon Audio Categories

Item definitions carry **no** `AudioCategory` field; a weapon's mixing category is set on its
*sound events*. Every `SFX_Sword_*` / shared light-melee event under `SoundEvents/SFX/Weapons/` names
the per-weapon category (`SoundEvents/SFX/Weapons/Shared/SFX_Light_Melee_T1_Swing.json`, tail):

```json
{
  "Layers": [ "..." ],
  "AudioCategory": "AudioCat_Sword",
  "Parent": "SFX_Attn_Moderate"
}
```

The category hierarchy allows adjusting all sword sounds together (via `AudioCat_Sword`, −6 dB)
while still inheriting from the parent `AudioCat_Weapons` → `AudioCat_SFX` chain.

### Sleep Sounds

The bed/sleep system's audio hooks live in the gameplay `WorldConfig`: its `SleepConfig` has a
`Sounds` object that decodes into
`com.hypixel.hytale.server.core.asset.type.gameplay.sleep.SleepSoundsConfig`
(`SleepSoundsConfig.CODEC`). Every reference is a sound-event id (validated against the
sound-event store):

| Property | Type | Description |
|----------|------|-------------|
| `Success` | string | Played when sleep succeeds (time skips) |
| `Fail` | string | Played when the sleep attempt fails |
| `Notification` | string | "Someone wants to sleep" notification sound |
| `NotificationLoop` | string | Looping variant of the notification |
| `NotificationCooldownSeconds` | int | Cooldown between notification plays |
| `NotificationLoopEnabled` | boolean | Whether the looping notification is used |

Java getters pair each id with a resolved index for the play path: `getSuccess()` /
`getSuccessIndex()`, `getFail()` / `getFailIndex()`, `getNotification()` / `getNotificationIndex()`,
`getNotificationLoop()` / `getNotificationLoopIndex()`, plus `getNotificationCooldownSeconds()`,
`getNotificationLoopCooldownMs()`, and `isNotificationLoopEnabled()`. Reached from
`WorldConfig` via `getSleepConfig().getSounds()`.

---

## File Format Reference

All audio assets use JSON format:

| Asset Type | Location | Purpose |
|------------|----------|---------|
| Sound Event | `SoundEvents/*.json` | Individual sounds |
| Audio Category | `AudioCategories/*.json` | Mixing groups |
| Ambience | `AmbienceFX/Ambience/*.json` | Ambient soundscapes |
| Music | `AmbienceFX/Music/*.json` | Music selectors (Conditions + `MusicContainer`) |
| Music Container | `MusicContainers/**/*.json` | Music graph nodes |
| Audio State | `AudioStates/*.json` | State axes for bindings |
| EQ Preset | `EQ/*.json` | Equalizer settings |
| Reverb Preset | `Reverb/*.json` | Reverb environments |
| Item Sounds | `ItemSounds/ISS_*.json` | Inventory sounds |
| Sound Set | `SoundSets/*.json` | Named sound groups |

Sound files themselves are `.ogg` format located in `Common/Sounds/`.

---

## Gotchas & Errors

Backtick-quoted error strings below are literal message fragments thrown by the audio system (verified against `HytaleServer.jar`).

- **`has a looping layer and is not a oneshot sound`** → a sound event used as a one-shot contains a layer marked `"Looping": true`. Fix: a one-shot sound's layers must not loop; clear `Looping` on those layers, or play it as a continuous/ambient sound instead.
- **Symptom:** a referenced `.ogg` plays as silence or fails to load → the `Files`/`Track` path is wrong or the file is missing. Fix: sound files live under `Common/Sounds/`; reference them by their path relative to that root (e.g. `Sounds/Items/Candle/Candle_Loop_01.ogg`).
