---
title: "Audio System"
description: "Define Hytale audio with JSON formats — multi-layer sound events with volume/pitch variation and spatial attenuation, audio categories for mixing, and ambient soundscapes."
seo:
  type: TechArticle
---

# Audio System

**Doc type:** JSON asset format · **Assets:** `Server/Audio` · **Verified against build-12**

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
│   ├── Music         track playlists
│   └── Conditions    Environment/Weather tag patterns, light/time/altitude/walls
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
| Music | `Server/Audio/AmbienceFX/Music/*.json` | Background music track playlists |
| EQ Preset | `Server/Audio/EQ/*.json` | 4-band parametric equalizer settings |
| Reverb Preset | `Server/Audio/Reverb/*.json` | Acoustic environment reverb settings |
| Item Sounds | `Server/Audio/ItemSounds/ISS_*.json` | Inventory drag/drop sound set (`ItemSoundSetId`) |
| Sound Set | `Server/Audio/SoundSets/*.json` | Named sound-event collection |

## Quick Navigation

| Section | Directory | Files | Description |
|---------|-----------|-------|-------------|
| [SoundEvents](#soundevents) | `SoundEvents/` | 1,176 | Individual sound definitions with layers |
| [AudioCategories](#audiocategories) | `AudioCategories/` | 95 | Volume/mixing groups with inheritance |
| [AmbienceFX](#ambiencefx) | `AmbienceFX/` | 175 | Ambient soundscapes with conditions |
| [EQ](#eq-equalizer) | `EQ/` | 2 | Equalizer presets |
| [Reverb](#reverb) | `Reverb/` | 21 | Environment reverb settings |
| [ItemSounds](#itemsounds) | `ItemSounds/` | 36 | Inventory drag/drop sounds |
| [SoundSets](#soundsets) | `SoundSets/` | 1 | Named sound event collections |

**Total: 1,506 audio asset files**

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

| Property | Type | Description |
|----------|------|-------------|
| `Layers` | array | One or more concurrent sound layers (see below). Sound files are referenced only via `Files` inside a layer — there is no top-level `Files` field |
| `Volume` | float | Base volume in dB (default: 0) |
| `RandomSettings` | object | Pitch/volume variation |
| `Looping` | boolean | Whether sound loops continuously |
| `StartDelay` | float | Delay before playback starts (seconds) |
| `Probability` | float | Chance to play (0.0-1.0) |
| `RoundRobinHistorySize` | int | Prevents repeating same file in sequence |
| `PreventSoundInterruption` | boolean | Don't interrupt if already playing |
| `MaxInstance` | int | Maximum concurrent instances |
| `Parent` | string | Inherit from another sound event |
| `AudioCategory` | string | Mixing category reference |
| `MaxDistance` | float | Distance at which sound is silent |
| `StartAttenuationDistance` | float | Distance at which falloff begins |

### Layer System

Every sound event holds its files in one or more layers. Each layer has its own
`Files` array plus optional per-layer `Volume`, `RandomSettings`, `StartDelay`, and
`Looping`. Layers play concurrently (e.g. an impact layer plus a debris layer):

```json
{
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
      "Files": ["Sounds/Weapons/Mace/Mace_Impact_01.ogg"],
      "Volume": -2
    }
  ],
  "Parent": "SFX_Attn_Loud"
}
```

Real attenuation presets (quietest to loudest):
- `SFX_Attn_ExtremelyQuiet`
- `SFX_Attn_VeryQuiet`
- `SFX_Attn_Quiet`
- `SFX_Attn_Moderate`
- `SFX_Attn_Loud`
- `SFX_Attn_VeryLoud`

`SFX_Attn_Moderate` and `SFX_Attn_Quiet` account for the large majority of `Parent`
references. A sound event may also inherit from another concrete sound event.

### Examples

**Block Sound (multi-file with variation):**

```json
{
  "Layers": [
    {
      "Files": [
        "Sounds/Blocks/Glass/Glass_Break_01.ogg",
        "Sounds/Blocks/Glass/Glass_Break_02.ogg",
        "Sounds/Blocks/Glass/Glass_Break_03.ogg",
        "Sounds/Blocks/Glass/Glass_Break_04.ogg"
      ],
      "Volume": 6.0,
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

**Attenuation Preset (defines distance falloff for children):**

```json
{
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

**Looping Sound:**

```json
{
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
  "Parent": "SFX_Attn_VeryQuiet"
}
```

---

## AudioCategories

**Location:** `Server/Audio/AudioCategories/`

Audio categories define volume mixing groups with hierarchical inheritance. They allow grouping sounds for volume control (e.g., all NPC sounds, all weapon sounds).

### Directory Structure

```
AudioCategories/
├── AudioCat_*.json  - Root mixing groups (Music, UI, NPC, Footsteps, ...)
├── NPC/             - Per-NPC audio categories (AudioCat_NPC_Wolf, ...)
├── UI/              - UI sub-categories
└── Weapons/         - Per-weapon audio categories (AudioCat_Sword, ...)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Volume` | float | Volume adjustment in dB (can be negative) |
| `Parent` | string | Parent category for inheritance |

### Hierarchy Example

```json
// AudioCat_NPC.json (parent)
{
  "Volume": 0
}

// AudioCat_NPC_Wolf.json
{
  "Volume": 0,
  "Parent": "AudioCat_NPC"
}
```

### Common Categories

Root categories (top of `AudioCategories/`):

| Category | Purpose |
|----------|---------|
| `AudioCat_Music` | Background music |
| `AudioCat_UI` | User interface sounds |
| `AudioCat_Footsteps` | Footstep sounds |
| `AudioCat_NPC` | NPC vocalizations |
| `AudioCat_Weapons` | Weapon sounds |
| `AudioCat_Discovery` | Discovery / progression stingers |
| `AudioCat_Inventory` | Inventory interaction sounds |

Sub-categories inherit via `Parent`. Examples:

- `AudioCat_NPC_*` (e.g. `AudioCat_NPC_Wolf`, `AudioCat_NPC_Dragon`) inherit `AudioCat_NPC`
- Per-weapon categories (e.g. `AudioCat_Sword`, `AudioCat_Battleaxe`, `AudioCat_Mace`, `AudioCat_Daggers`, `AudioCat_Shield`, `AudioCat_Shortbow`, `AudioCat_Magic_Staff`) inherit `AudioCat_Weapons`
- `AudioCat_UI_Sleep` inherits `AudioCat_UI`

---

## AmbienceFX

**Location:** `Server/Audio/AmbienceFX/`

Ambient audio defines soundscapes that play based on environmental conditions. Includes ambient beds (continuous background), emitter sounds (periodic triggers), and music.

### Directory Structure

```
AmbienceFX/
├── Ambience/      - Ambient soundscapes (beds + emitters)
│   ├── Global/      - Cave, Lava, Dungeon, Mineshaft, Underwater, Weather, ...
│   ├── Zone1/ ... Zone4/  - Per-zone Environments/ and Global/
│   └── Unique/      - Named locations (Forgotten_Temple, Dread_Wade, ...)
├── Music/         - Background music (Global/, Zone0/ ... Zone4/, Unique/)
├── ReverbZones/   - Reverb zone definitions (Forest, Mountain, Plains, Swamp, Underground, Prefabs)
├── AmbFX_*.json   - Top-level ambience definitions (e.g. AmbFX_Void)
└── Z2_Dungeon.json
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Conditions` | object | When this ambience plays |
| `AmbientBed` | object | Continuous background sound |
| `Sounds` | array | Triggered emitter sounds |
| `Music` | object | Background music configuration |
| `AudioCategory` | string | Mixing category (commonly `AudioCat_Music`) |
| `Priority` | int | Selection priority when multiple definitions match |

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

### Emitter Sounds

Periodic triggered sounds with spatial positioning. Each entry references a sound
event by `SoundEventId` and uses `Frequency` and `Radius` ranges (each an
object with `Min`/`Max`):

```json
{
  "Sounds": [
    {
      "SoundEventId": "SFX_Z3_Forest_Day_Birds",
      "Frequency": {
        "Min": 2,
        "Max": 5
      },
      "Radius": {
        "Min": 3,
        "Max": 10
      }
    }
  ]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `SoundEventId` | string | Sound event to trigger |
| `Frequency` | object | `Min`/`Max` range controlling how often the sound triggers |
| `Radius` | object | `Min`/`Max` spawn distance range from the player |

### Music Configuration

Background music track playlists. `Tracks` is an array of plain `.ogg` file path
strings (rooted at `Common/Sounds/`, typically under `Music/`). Music definitions
usually pair the `Music` block with `AudioCategory: "AudioCat_Music"` and a `Priority`:

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
  "Music": {
    "Tracks": [
      "Music/Zone3/Z3D-OutlanderDungeon.ogg"
    ]
  },
  "AudioCategory": "AudioCat_Music",
  "Priority": 80
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Tracks` | array | List of `.ogg` file path strings |
| `Volume` | float | Optional volume in dB |

### Complete Example

```json
{
  "Conditions": {
    "SunLightLevel": { "Min": 10, "Max": 15 },
    "DayTime": { "Min": 5, "Max": 19 },
    "EnvironmentIds": ["Env_Zone3_Mountains"],
    "WeatherTagPattern": {
      "Op": "Not",
      "Pattern": { "Op": "Equals", "Tag": "Rain" }
    },
    "Walls": { "Min": 0, "Max": 3 }
  },
  "Sounds": [
    {
      "SoundEventId": "SFX_Z3_Forest_Day_Birds",
      "Frequency": { "Min": 2, "Max": 5 },
      "Radius": { "Min": 3, "Max": 10 }
    }
  ]
}
```

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

The 21 presets are biome/zone and location based:

| Preset | Description |
|--------|-------------|
| `Rev_Default` | Default fallback reverb |
| `Rev_Cave` | Cave acoustics |
| `Rev_Forest`, `Rev_Forest_Desert`, `Rev_Forest_Fog`, `Rev_Forest_Snow` | Forest biome variants |
| `Rev_Mountain`, `Rev_Mountain_Fog`, `Rev_Mountain_Snow` | Mountain biome variants |
| `Rev_Plains`, `Rev_Plains_Desert`, `Rev_Plains_Fog`, `Rev_Plains_Snow` | Plains biome variants |
| `Rev_Swamp`, `Rev_Swamp_Foggy` | Swamp biome variants |
| `Rev_Mineshaft` | Mineshaft interiors |
| `Rev_Temple`, `Rev_Temple_Grand` | Temple interiors |
| `Rev_Village` | Village ambience |
| `Rev_Mage_Tower` | Mage Tower interior |
| `Rev_Reflective_Slap` | Hard reflective slap-back |

---

## ItemSounds

**Location:** `Server/Audio/ItemSounds/`

Item sounds define drag and drop sounds for inventory interactions. Items reference
these via `ItemSoundSetId` (1,645 references across the server assets). The files are
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

## Integration with Other Systems

### Block Sounds

Blocks reference sound events by material type. The BlockType's material name maps to files in `BlockSounds/`:

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
`Metal`, `Glass`, `Ice`, `Snow`, `Mud`, `Leaves`, `Cloth`, `Bone`, and many more.

Block types specify their material in their definition, and the audio system automatically loads the corresponding sounds.

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

NPCs reference sound events in their animation definitions. Animation events can trigger sounds at specific keyframes:

```json
{
  "AnimationId": "Attack",
  "Events": [
    {
      "Time": 0.2,
      "Type": "Sound",
      "SoundEventId": "SFX_Zombie_Attack_Bite"
    }
  ]
}
```

### Weapon Audio Categories

Weapons define their audio category for mixing control:

```json
{
  "ItemId": "Sword_T1",
  "AudioCategory": "AudioCat_Sword"
}
```

The category hierarchy allows adjusting all sword sounds together (via `AudioCat_Sword`)
while still inheriting from the parent `AudioCat_Weapons` category.

---

## File Format Reference

All audio assets use JSON format:

| Asset Type | Location | Purpose |
|------------|----------|---------|
| Sound Event | `SoundEvents/*.json` | Individual sounds |
| Audio Category | `AudioCategories/*.json` | Mixing groups |
| Ambience | `AmbienceFX/Ambience/*.json` | Ambient soundscapes |
| Music | `AmbienceFX/Music/*.json` | Background music |
| EQ Preset | `EQ/*.json` | Equalizer settings |
| Reverb Preset | `Reverb/*.json` | Reverb environments |
| Item Sounds | `ItemSounds/ISS_*.json` | Inventory sounds |
| Sound Set | `SoundSets/*.json` | Named sound groups |

Sound files themselves are `.ogg` format located in `Common/Sounds/`.

---

## Gotchas & Errors

Backtick-quoted error strings below are literal message fragments thrown by the build-12 audio system (verified against `HytaleServer.jar`).

- **`has a looping layer and is not a oneshot sound`** → a sound event used as a one-shot contains a layer marked `"Looping": true`. Fix: a one-shot sound's layers must not loop; clear `Looping` on those layers, or play it as a continuous/ambient sound instead.
- **Symptom:** a referenced `.ogg` plays as silence or fails to load → the `Files`/`Track` path is wrong or the file is missing. Fix: sound files live under `Common/Sounds/`; reference them by their path relative to that root (e.g. `Sounds/Items/Candle/Candle_Loop_01.ogg`).
