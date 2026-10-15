---
title: "Music"
description: "Author Hytale music in JSON — music selectors, MusicContainer graphs (single track, playlists, horizontal phases, layered segments), audio-state axes, music transitions, stingers and music events — and drive it from a plugin."
seo:
  type: TechArticle
---

# Music

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Audio` · **Verified against 0.7.2**

> Part of the [Audio System](audio.md). Sound events, categories, ambience beds and emitters, EQ and reverb live there.

Hytale's music is a small graph of JSON assets. A **selector** or a gameplay system picks a
**music container**; containers nest into playlists, phase sets and layered segments; **audio states**
crossfade layers and pick phases; **music transitions** shape the handover from one container to the
next; and **stingers** are short accents that answer named **music events**. All of it is resolved and
played on the client — the server loads and validates the assets, sends them, and drives the
per-player inputs (forced music and server-authority audio states).

## Overview

| Asset | Directory | Shipped (0.7.2) | Section |
|-------|-----------|-----------------|---------|
| Music selector (an `AmbienceFX`) | `Server/Audio/AmbienceFX/Music/` | 47 | [Music Selectors](#music-selectors) |
| Music container | `Server/Audio/MusicContainers/` | 275 | [MusicContainer](#musiccontainer) |
| Audio state | `Server/Audio/AudioStates/` | 9 | [AudioState Transitions](#audiostate-transitions) |
| Music transition | `Server/Audio/MusicTransitions/` | 5 | [MusicTransition](#musictransition) (0.7.2+) |
| Stinger | `Server/Audio/Stingers/` | 2 | [Stinger](#stinger) (0.7.2+) |

How the pieces connect, using the shipped Deepworks dungeon music as the worked example:

```
AmbienceFX/Music/Dungeons/Mus_Dungeon_Goblin.json        selector: Conditions → "MusicContainer": "Track_Z1D_The_Deepworks"
  └─ MusicContainers/Tracks/Dungeons/Track_Z1D_The_Deepworks.json   Segment, two layers bound to AudioState_Dungeon_Intensity
       ├─ layer "explore" / layer "combat"                 StateBindings mute one layer per state value
       └─ Stingers: Combat_Enter → Stinger_Z1D_The_Deepworks_Combat (PlayAt NextBar)
EncounterManager/Combat_Music_Encounter_Deepworks.json   SetEncounterAudioState → AudioState_Dungeon_Intensity = Combat
  └─ AudioStates/AudioState_Dungeon_Intensity.json        edge Explore → Combat: "PostEvent": "Combat_Enter"
```

The encounter flips the axis; the axis's edge both crossfades the two layers and posts `Combat_Enter`;
the playing container binds that event to a stinger, which lands on the next bar.

---

## Music Selectors

Music selectors under `AmbienceFX/Music/` (47 files in 0.7.2) are ordinary `AmbienceFX` assets whose `Conditions`
and `Priority` (see [AmbienceFX](audio.md#ambiencefx)) are paired with a **`MusicContainer`** reference. The value is either a container id string or an inline container
object that inherits one through `Parent` (both forms decode through `MusicContainer.CHILD_ASSET_CODEC`);
the inline form lets the selector override `AudioCategory`/`LoopCount` without a new container file.
`AmbienceFX/Music/Zone3/Mus_Zone3_Dungeon.json` as shipped in 0.7.2:

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

> **Legacy `Music` block (Update 5).** The older `Music` object (`Tracks` — a non-empty array of `.ogg`
> paths rooted at `Common/`, which the `CommonAssetValidator.MUSIC` validator requires to sit under
> `Music/` — plus optional `Volume` in dB, −100 to 10) is
> **deprecated** (the codec's own documentation string reads "Deprecated: Use MusicContainer instead.")
> and is **auto-migrated at runtime** into a generated `RandomMusicContainer`
> (`RandomMusicContainer.fromLegacy(...)`, fed by `AmbienceFX.consumeLegacyMusic()`). As of 0.7.2 only
> one shipped asset still uses it (`AmbFX_Void.json`, `"Music": { "Tracks": ["Music/Unique/Silence.ogg"], "Volume": -10 }`).
> It decodes into `com.hypixel.hytale.server.core.asset.type.ambiencefx.config.AmbienceFXMusic`
> (`AmbienceFXMusic.CODEC`; both fields inherit through `Parent`) — `getTracks()`, `getDecibels()` (raw dB),
> `getVolume()` (linear gain), and an `AmbienceFXMusic(String[] tracks, float decibels)` constructor.
> Author new music as MusicContainer assets.

Ambience selection is one of two ways music starts. The other is **forced music**, a per-player
container the server sets — see [Who starts music](#who-starts-music).

---

## MusicContainer

**Location:** `Server/Audio/MusicContainers/` · **Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config`

New in Update 5. A **music container** is a node in a small graph that describes *how* music plays — a single track,
a weighted-random or sequential playlist, or layered/segmented arrangements that crossfade with game state. Each
`.json` file is one container, keyed by its **id** (the filename without `.json`); containers reference each other
by id, so you compose larger arrangements from smaller ones. This replaces the flat
[AmbienceFX `Music` block](#music-selectors), which is now auto-migrated into a generated `RandomMusicContainer`;
an ambience selects music with its `MusicContainer` key. **275 container files** ship in 0.7.2, holding 364
container nodes in total — 302 `SingleTrack`, 35 `Segment`, 19 `Random`, 5 `Sequence` and 3 `Horizontal` (nodes
outnumber files because a `Segment`'s layers hold inline `SingleTrack` containers).

> The folder layout (`Tracks/`, `Playlists/`, …) is just organization — every `.json` under `MusicContainers/`
> loads as a container regardless of subfolder.

### Container types

The object's `"Type"` field selects the container kind:

| `Type` | Class | Plays |
|--------|-------|-------|
| `SingleTrack` | `SingleTrackMusicContainer` | One audio file (`Track`, an `.ogg` path under `Common/Music/`, where sound effects use `Common/Sounds/`; the `Music/` root is enforced by `CommonAssetValidator.MUSIC`, and `SoundFileValidators.MUSIC_SAMPLE_RATE` checks the file's sample rate) |
| `Random` | `RandomMusicContainer` | A `Children` list picked by weight; `Mode` is `Random` or `Shuffle` |
| `Sequence` | `SequenceMusicContainer` | A `Children` list in order |
| `Horizontal` | `HorizontalMusicContainer` | Phases (`Children`) moved between by phase transitions; an `AudioState` can pick the phase |
| `Segment` | `SegmentMusicContainer` | Simultaneous `Layers` on one timeline, mixed/crossfaded by audio state (bar/beat aligned) |

### Common fields

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.MusicContainer`

All container types share these (`MusicContainer.ABSTRACT_CODEC`; each key is optional, and an inline child that names a `Parent` takes its `Type` from it). Every key except
`StateBindings` and `Stingers` inherits through `Parent`, and so does the standard asset `Tags` map, which a
[MusicTransition](#musictransition)'s `TagPattern` matches against.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `Type` | string | — | Discriminator — one of the types above |
| `AudioCategory` | string | — | Mixing category (commonly `AudioCat_Music_In_Game`); honoured on any container, and the nearest one above a playing leaf wins |
| `NameTranslationKey` | string | — | i18n key for the displayed track name |
| `Volume` | float | 0 dB | Volume in dB, −100 to 10 |
| `LoopCount` | int | `1` | Times to loop (`0` = forever); minimum 0 |
| `Weight` | float | `1.0` | Selection weight when this container is a child of a `Random` container; minimum 0.001 |
| `SilenceAfter` | range | — | `{ "Min": s, "Max": s }` silence (seconds) after this container completes as a child |
| `ExitSilence` | range | — | `{ "Min": s, "Max": s }` silence (seconds) when this top-level container is replaced by another; only valid on a top-level container |
| `FadeInDuration` / `FadeOutDuration` | float | `0.0` | Fades (seconds), non-negative |
| `TransitionType` | enum | `FadeOutFadeIn` | `Crossfade`, `FadeOutFadeIn` or `Immediate` — how a switch into this container behaves when no [MusicTransition](#musictransition) matches, and how a `Horizontal` parent moves into it. **0.6.8 defaulted to `Crossfade`**, so a container that omits the key now fades out and in |
| `TransitionDuration` | float | `0.0` | Transition length (seconds); `0` uses the parent's default |
| `ExitAt` | object | — | When the playing container hands over to this one, as a [sync point](#sync-points-and-musical-time) on the *outgoing* container's grid (0.7.2+). Omitted, `TransitionType` decides: `Immediate` hands over at once, `Crossfade` at the outgoing container's exit marker, `FadeOutFadeIn` on the next bar |
| `Align` | enum | — | Where this container starts on its own timeline when a transition places it (0.7.2+): `EntryMarker` (its downbeat lands on the handoff — the behaviour when omitted), `NamedMarker`, or `SamePosition` (carries the outgoing playhead across; lines up only between arrangements sharing a grid and loop length, so it suits a `Horizontal` phase) |
| `AlignMarker` | string | — | The marker `Align: NamedMarker` lands on (0.7.2+). Only a `Segment` can declare markers |
| `PlayToCompletion` | bool | `false` | Finish this container before yielding to higher-priority music |
| `ResumeMemoryDuration` | float | `30.0` | How long (seconds) the container remembers its position so a return resumes mid-track; a `Random` container starts at 600 |
| `Tempo` | object | — | `Bpm` (1–1000), `BeatsPerBar` (1–32), `BeatValue` (1–32); needed for anything authored in bars or beats |
| `StateBindings` | array | — | Per-[AudioState](#state-bindings) deltas applied to this container and its descendants |
| `Stingers` | array | — | Music-event → stinger [bindings](#stinger-bindings), inherited by descendants (0.7.2+) |

A matched [MusicTransition](#musictransition) overrides `ExitAt`, `Align` and `AlignMarker`. The container's
validator rejects `Align: NamedMarker` without an `AlignMarker` (and an `AlignMarker` under any other `Align`),
and rejects `NamedMarker` on any type other than `Segment` ("Align: NamedMarker needs a container that can declare
Markers, and … cannot").

### SingleTrack

The leaf — points at one audio file:

```json
{ "Type": "SingleTrack", "Track": "Music/Caves/Z1_Cave_Shallow_01.ogg" }
```

### Random / Sequence

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.RandomMusicContainer` (and `SequenceMusicContainer`)

A playlist of child containers under `Children` — a non-empty array whose entries are container ids or inline
containers (usually an inline container that inherits a track via `Parent`, plus per-child overrides such as
`SilenceAfter` / `Weight` — the same `CHILD_ASSET_CODEC` an ambience's `MusicContainer` key uses). `Sequence` plays
in order. `Random` adds two keys:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `Mode` | enum | `Shuffle` | `Shuffle` spreads picks evenly; `Random` is a weighted pick each time (children's `Weight`) |
| `AvoidRepeatCount` | int | `0` | How many recently played children to avoid re-selecting |

`Tracks/MC_Z1_Caves.json` (truncated):

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

### Horizontal

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.HorizontalMusicContainer`

Phases that hand over horizontally (exploration → combat, boss phase 1 → phase 2), each phase one of the
`Children`. Three ship in 0.7.2, and all three pick their phase from an audio state.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `Children` | array | — | The phases, in order — container ids or inline containers; non-empty |
| `DefaultPhaseTransitionType` | enum | `Crossfade` | `MusicTransitionType` for every phase change. A child overrides it with its own `TransitionType` only when that child also sets a `TransitionDuration`, since `TransitionType` has no "unset" value |
| `DefaultPhaseTransitionDuration` | float | `0.0` | Default phase-transition length (seconds) |
| `AudioState` | string | — | Axis that selects the phase (0.7.2+). Omitted, the container only advances sequentially |
| `Phases` | array | — | `{ "Value": <state value>, "Phase": <index into Children> }` entries (0.7.2+). A state value left unlisted leaves the current phase alone |

Validation ties the two new keys together: `Phases` without an `AudioState` fails ("maps phases but names no
AudioState"); an `AudioState` with no `Phases` only warns ("names AudioState … but maps no phases, so the axis does
nothing"); each entry needs a `Value` that is a value of that axis, listed once, and a `Phase` inside the
`Children` range. `Tracks/Zone1/Track_Z1D_Goblin_Boss.json` (truncated) maps the five values of
`AudioState_Goblin_Boss_Phase` onto its five children:

```json
{
  "Type": "Horizontal",
  "AudioCategory": "AudioCat_Music_In_Game",
  "TransitionType": "Immediate",
  "DefaultPhaseTransitionType": "Immediate",
  "DefaultPhaseTransitionDuration": 0.0,
  "AudioState": "AudioState_Goblin_Boss_Phase",
  "Phases": [
    { "Value": "Phase1", "Phase": 0 },
    { "Value": "Interlude", "Phase": 1 },
    { "Value": "Phase2", "Phase": 2 },
    { "Value": "Phase3", "Phase": 3 },
    { "Value": "Ending", "Phase": 4 }
  ],
  "Children": [
    "Track_Z1D_Goblin_Boss_Phase1",
    "Track_Z1D_Goblin_Boss_Interlude",
    "Track_Z1D_Goblin_Boss_Phase2",
    "Track_Z1D_Goblin_Boss_Phase3",
    "Track_Z1D_Goblin_Boss_Ending"
  ]
}
```

A phase change is a container handover like any other, so a [MusicTransition](#musictransition) whose `From`/`To`
name two phases shapes it — that is exactly what the five shipped transitions do for this boss.

### Segment (layered)

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.SegmentMusicContainer`

Simultaneous **layers** on one timeline, mixed by **audio state** — the engine's cave music uses this to crossfade
between shallow / volcanic / deep beds as the player moves. The active region runs from `EntryMarker` (the downbeat)
to `ExitMarker` (the loop point, or for a play-once Segment inside a `Sequence`, the trigger for the next child).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `Layers` | array | — | `LayerPlacement`s (below); non-empty, layer names unique |
| `EntryMarker` | `BarBeatDuration` | — | Downbeat position from segment-time 0. Layers without a `ClipStart` get this much pre-entry material (a stinger's "pickup") |
| `ExitMarker` | `BarBeatDuration` | — | Exit / loop position from segment-time 0; must resolve after `EntryMarker` |
| `Markers` | array | — | Named positions (0.7.2+): `{ "Name": …, "At": { "Bar": 1, "Beat": 1, "Ms": 0 } }`, counted from the downbeat, that `NextMarker` sync points and `Align: NamedMarker` target |

Any bar or beat component in `EntryMarker`, `ExitMarker` or a layer's `ClipStart` makes `Tempo` mandatory ("Segment
requires a Tempo when EntryMarker, ExitMarker, or ClipStart use bar/beat components"); so does a marker placed off
`Bar 1 Beat 1`. A marker that resolves past the exit marker fails validation. No shipped 0.7.2 asset declares
`Markers` yet.

Each **`LayerPlacement`**:

| Field | Type | Description |
|-------|------|-------------|
| `Name` | string | **Required** (`Validators.nonNull()`). Unique within the Segment |
| `Container` | string or object | **Required** (`Validators.nonNull()`). The layer's container — an id or an inline container |
| `ClipStart` | `BarBeatDuration` | Where the clip's byte 0 sits on the Segment's timeline; `0` = the downbeat, negative = pre-entry. A positive value fails validation |
| `StateBindings` | array | Per-layer [state bindings](#state-bindings) — volume (`VolumeDb`), pitch (`PitchSemitones`), `Mute` and an optional per-subscriber `Fade` per audio-state value |

`Tracks/Track_Z1_Cave_01.json` (truncated to one of its three layers):

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

### Who starts music

Containers are referenced by id — by other containers (`Children` / `Parent`, layer `Container`, a stinger's
`MusicContainer`) and by gameplay. Two channels start music for a player:

- **Ambience selection** — the [music selectors](#music-selectors) above.
- **Forced music** — one container index per player, held server-side in the `ForcedMusicTracker` component
  (`com.hypixel.hytale.builtin.audio.components`) and sent with the `UpdateForcedMusic` packet whenever it changes;
  index `0` (the empty container) means none. Every built-in writer goes through it: the encounter actions
  `StartEncounterMusic` / `StopEncounterMusic` ([encounters](encounters.md)), the Trigger Volume
  [`SetMusic` effect](trigger-volumes.md#built-in-effect-types) (`MusicContainer`, or `ClearMusic`), a void-event
  stage's `MusicContainer`, and the `/audio music force <musicContainerId>` / `/audio music clear` commands. A
  plugin writes it the same way — see [Driving Music from Java](#driving-music-from-java).

The config classes in `com.hypixel.hytale.server.core.asset.type.musiccontainer.config` each have a
`getChildIds()` and a `CODEC`; `MusicContainer.getAssetMap()` resolves ids.

---

## Sync Points and Musical Time

Three small value types recur across containers, transitions, stingers and audio states.

### BarBeatDuration

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.BarBeatDuration`

A length (or signed offset) summed from three parts against the tempo of whatever it is
measured on; with no tempo only `Ms` counts.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Bars` | int | `0` | Whole bars |
| `Beats` | float | `0.0` | Beats, fractional allowed (against a quarter-note beat, `0.5` is an eighth). A float as of 0.7.2 |
| `Ms` | float | `0.0` | Milliseconds added on top — `{ "Ms": 1234 }` alone is a plain duration |

Bars and beats are limited to ±100000 and `Ms` to ±3600000.

### BarBeatPosition

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.BarBeatPosition`

A 1-indexed *position* (a `Segment` marker's `At`): `Bar` (int, default `1`, minimum 1),
`Beat` (int, default `1`, minimum 1) and `Ms` (non-negative offset past the bar and beat). `Bar 1 Beat 1` is the downbeat.

### MusicSyncConfig

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.MusicSyncConfig`

A **sync point**: *when*, on the playing music's grid, something happens. Used by a
container's or transition's `ExitAt`, a stinger binding's `PlayAt`, and an audio state's `SyncTo` / `DefaultSyncTo`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Point` | enum | `Immediate` | Boundary to wait for: `Immediate`, `NextBeat`, `NextBar`, `ExitMarker` or `NextMarker` |
| `Marker` | string | — | Marker name for `Point: NextMarker`; omit to take the next marker of any name |
| `Offset` | `BarBeatDuration` | — | Signed offset from the boundary; negative fires early (lead-ins, landing on a phrase's last bar) |
| `BarMultiple` | int | `0` | With `Point: NextBar`, wait for every Nth bar from the grid origin (`4` = four-bar phrases); `0` and `1` both mean every bar. Range 0–1024 |

A `Marker` under any `Point` other than `NextMarker`, or a `BarMultiple` above 1 under any `Point` other than
`NextBar`, fails validation.

---

## MusicTransition

**Location:** `Server/Audio/MusicTransitions/`
**Package:** `com.hypixel.hytale.server.core.asset.type.musictransition.config.MusicTransition`

New in 0.7.2. A **music transition** is a rule for how the music moves from one container to another — a
top-level switch, or a phase change inside a `Horizontal` container. When a handover happens, the matching rule with
the highest `Priority` wins; ties go to the rule that matches more narrowly (a named `Container` beats a `TagPattern`,
which beats a side left open, and the `From` side weighs more than `To` — the packet carries
`specificity = from × 3 + to`). With no matching rule the incoming container's own `TransitionType`, `ExitAt` and
`Align` apply. **5 ship**, all for the Goblin boss fight.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `From` | object | — | The outgoing side: `{ "Container": <id> }` or `{ "TagPattern": <id or inline pattern> }` (setting both fails). Omit to match any container |
| `To` | object | — | The incoming side, same shape. Omit to match any container |
| `ExitAt` | [sync point](#sync-points-and-musical-time) | — | When the handoff happens, on the outgoing container's grid. Omit to fall back to the incoming container's `ExitAt`, then to its `TransitionType`'s boundary |
| `Align` | enum | `EntryMarker` | Where the incoming container begins on its own timeline: `EntryMarker`, `NamedMarker`, `SamePosition` |
| `AlignMarker` | string | — | Marker of the incoming container for `Align: NamedMarker` (and only then) |
| `FadeOutDuration` | `BarBeatDuration` | — | Outgoing ramp length from the handoff, against the grid the handoff sits on. Omit (or all zeros) to hold it at full gain |
| `FadeOutCurve` | `FadeCurve` | `EqualPowerSine` | Shape of the outgoing ramp. `Linear` dips about 3 dB through the middle of a crossfade |
| `FadeOutDelay` | `BarBeatDuration` | — | How long the outgoing container holds full gain past the handoff before ramping |
| `FadeInDuration` | `BarBeatDuration` | — | Incoming ramp length from the handoff |
| `FadeInCurve` | `FadeCurve` | `EqualPowerSine` | Shape of the incoming ramp |
| `PlayPostExit` | bool | `false` | Let the outgoing container run to the end of its file after the handoff so an authored tail rings out. Top-level switches only; a phase change inside a `Horizontal` always stops the outgoing phase |
| `PostEvent` | string | — | [Music event](#music-events) posted at the handoff — what lets a stinger cover the seam |
| `Priority` | int | `0` | Higher wins |

`FadeCurve` is `Linear`, `Logarithmic`, `Exponential`, `SCurve` or `EqualPowerSine`. The matched sides' container
ids are resolved to indices when the asset is sent, so a `TagPattern` side covers every container whose `Tags`
satisfy the pattern at that moment (no shipped 0.7.2 container carries `Tags`; [tag-pattern](audio.md#tag-patterns)
assets live under `Server/TagPatterns/`).

The validator **fails** a negative `FadeOutDuration` / `FadeOutDelay` / `FadeInDuration`, a blank `PostEvent`
("PostEvent is blank, which can never match a binding"), `NamedMarker` without `AlignMarker` or the reverse, and an
`ExitAt` of `NextBeat`/`NextBar` when a `From` container has no tempo ("ExitAt Point … needs a Tempo on From
container …"). It **warns** when a side matches no container ("From matches no container, so this rule can never
apply"), on `PlayPostExit` against a `From` container that loops forever, on `SamePosition` across different loop
lengths, and on an overlapping transition (one with `PlayPostExit`, a fade-out or a fade-out delay) across different
tempos.

`MusicTransitions/MT_Z1D_Goblin_Boss_Phase1_Interlude.json` — on the next bar, the interlude enters at full level on
its downbeat while phase 1 holds for a beat and a half and then fades out over one beat:

```json
{
  "From": { "Container": "Track_Z1D_Goblin_Boss_Phase1" },
  "To": { "Container": "Track_Z1D_Goblin_Boss_Interlude" },
  "ExitAt": { "Point": "NextBar" },
  "Align": "EntryMarker",
  "FadeOutDuration": { "Beats": 1 },
  "FadeOutCurve": "Linear",
  "FadeOutDelay": { "Beats": 1.5 },
  "FadeInDuration": { "Ms": 0 },
  "PlayPostExit": false,
  "Priority": 40
}
```

The other four (`MT_Z1D_Goblin_Boss_Phase2_Interlude`, `…_Interlude_Phase2`, `…_Interlude_Phase3`,
`…_Phase3_Ending`) differ only in their containers and a `FadeOutDelay` of `1.5` or `0.5` beats.

---

## Stinger

**Location:** `Server/Audio/Stingers/`
**Package:** `com.hypixel.hytale.server.core.asset.type.stinger.config.Stinger`

New in 0.7.2. A **stinger** is a musical one-shot played *over* the current music rather than replacing it. A
stinger plays only when a container that is playing [binds](#stinger-bindings) a music event to it. **2 ship**, both
for the Deepworks dungeon.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `MusicContainer` | string or object | — | What to play — a container id or an inline container. A `Random` container gives free variation; a `Segment` allows a tempo and pre-entry pickup |
| `Priority` | short | `0` | Rank within `ExclusionGroup`; higher wins |
| `ExclusionGroup` | string | — | Stingers sharing a group compete: a firing stinger is dropped when an active one outranks it, and replaces it otherwise. Omit to compete with nothing |
| `MaxInstance` | int | `1` | Concurrent voices of this stinger (per asset); minimum 1 |
| `AudioCategory` | string | — | Category the stinger routes to; a dedicated one lets it duck the bed independently |
| `Volume` | float | 0 dB | Volume in dB, −100 to 10 |
| `DuckingRules` | array | — | While the stinger is audible, each rule attenuates its `TargetCategory` — the same rule shape as an [audio category's ducking](audio.md#ducking) |

A stinger plays one voice, so the validator **warns** when its content reaches a non-`Random` container with more
than one part ("… but a stinger plays one voice, so only the first would sound"), and when anything it reaches sets
an `Align` other than `EntryMarker` (a stinger is placed by its binding's `PlayAt`, so alignment has no effect).

`Stingers/Stinger_Z1D_The_Deepworks_Combat.json`:

```json
{
  "MusicContainer": {
    "Type": "SingleTrack",
    "Track": "Music/Zone1/Z1D_The_Deepworks_Combat_Stinger_120_4-4_S1-0.ogg"
  },
  "AudioCategory": "AudioCat_Music_In_Game",
  "ExclusionGroup": "Deepworks_Intensity",
  "Volume": 8.0
}
```

`Stinger_Z1D_The_Deepworks_Explore` is the same shape at `"Volume": 7.0`. Sharing `Deepworks_Intensity` means a
combat stinger and an explore stinger never overlap: the later one replaces the earlier (both are priority 0).

### Stinger bindings

**Package:** `com.hypixel.hytale.server.core.asset.type.musiccontainer.config.StingerBindingConfig`

A container's `Stingers` array (`StingerBindingConfig`) maps event names to stingers. Bindings are inherited by
descendants and the deepest binding for an event wins, so a parent can give a default that a child overrides.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `MusicEvent` | string | — | The event this binding answers — a free-form name, matched against what a state edge, a transition rule or a `PostMusicEvent` posts |
| `Stinger` | string | — | The `Stinger` id to play |
| `PlayAt` | [sync point](#sync-points-and-musical-time) | — | Where on the playing music's grid the stinger lands; omit to play immediately |
| `MinRepeatIntervalSeconds` | float | `0.0` | Window in which the named stinger will not play again — counted per stinger asset, so binding one stinger from two events cannot bypass it |
| `ShortLead` | enum | `DropPickup` | When the sync point is closer than the stinger's own pickup: `DropPickup` plays from the entry marker so the accent still lands on the boundary; `Skip` drops it; `Defer` waits for the next occurrence (arrives late); `TrimPickup` keeps whatever pickup fits |

The container's validator fails a binding with no `MusicEvent` or no `Stinger`, a blank event name, and the same
event bound twice on one container. The `Stinger` id is checked against the stinger store, and one that still fails
to resolve when the container is sent is logged ("Stinger binding references unknown stinger '…'; the binding will
do nothing").
`Tracks/Dungeons/Track_Z1D_The_Deepworks.json` binds both shipped stingers:

```json
"Stingers": [
  { "MusicEvent": "Combat_Enter", "Stinger": "Stinger_Z1D_The_Deepworks_Combat", "PlayAt": { "Point": "NextBar" } },
  { "MusicEvent": "Combat_Exit",  "Stinger": "Stinger_Z1D_The_Deepworks_Explore", "PlayAt": { "Point": "NextBar" } }
]
```

---

## Music Events

A **music event** is a bare name. Nothing declares the set; a binding answers whatever name it lists. The client
matches each posted event against the `Stingers` bindings of the music that is playing — the server jar holds the
bindings only as data it validates and sends. Three things post one:

| Source | Posted when | Shipped use |
|--------|-------------|-------------|
| An audio-state edge's `PostEvent` ([`StateTransitionConfig`](#audiostate-transitions)) | that edge is taken — the axis moves from `From` to `To` | `AudioState_Dungeon_Intensity` posts `Combat_Enter` on `Explore → Combat` and `Combat_Exit` on the way back |
| A [MusicTransition](#musictransition)'s `PostEvent` | at the handoff the rule governs | none in 0.7.2 |
| The `PostMusicEvent` packet (`com.hypixel.hytale.protocol.packets.world`, to-client, id 180, one `musicEvent` string) | a plugin sends it | none — no 0.7.2 server code constructs it |

So in practice an event follows a **state change**, and state changes come from: the encounter action
`SetEncounterAudioState` (server-authority axes — how the shipped Deepworks and Goblin boss music is driven), an ambience's
`SetStates` (client-authority axes), the `/audio state set` command, or a plugin. The Deepworks chain end to end:
`Combat_Music_Encounter_Deepworks` sets `AudioState_Dungeon_Intensity` to `Combat` when a hostile in the
`Combat_Music_Targets_Deepworks` group attacks, lands a hit or is hit; the axis's `Explore → Combat` edge crossfades the
container's two layers over one bar and posts `Combat_Enter`; `Track_Z1D_The_Deepworks` binds that event to
`Stinger_Z1D_The_Deepworks_Combat` at `NextBar`. (The encounter also listens for a `Combat_Ping` beacon message,
which its own comment describes as "Explicit ping from an NPC or a plugin.")

---

## AudioState Transitions

**Location:** `Server/Audio/AudioStates/`
**Package:** `com.hypixel.hytale.server.core.asset.type.audiostate.config.AudioState`

`AudioState` assets define the named state axes (e.g. `AudioState_CaveRegion` with values
`Shallow` / `Volcanic` / `Deep`) that [state bindings](#state-bindings) on segment layers, containers, sound
events, audio categories and ambience react to, and that a `Horizontal` container's `Phases` read.
Nine ship in 0.7.2 — two client-authoritative (`AudioState_CaveRegion`, `AudioState_Void_Escalation`) and seven
server-authoritative (among them `AudioState_Combat`, `AudioState_Dungeon_Intensity` and
`AudioState_Goblin_Boss_Phase`). `AudioStates/AudioState_Dungeon_Intensity.json`:

```json
{
  "Authority": "Server",
  "Values": ["Explore", "Combat"],
  "DefaultValue": "Explore",
  "DefaultSyncTo": { "Point": "NextBar" },
  "DefaultTransition": { "Duration": { "Beats": 2 }, "Curve": "SCurve" },
  "Transitions": [
    { "From": "Explore", "To": "Combat",  "Duration": { "Bars": 1 }, "Curve": "SCurve", "PostEvent": "Combat_Enter" },
    { "From": "Combat",  "To": "Explore", "Duration": { "Bars": 1 }, "Curve": "SCurve", "PostEvent": "Combat_Exit" }
  ]
}
```

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Authority` | `Server` / `Client` | `Server` | Which side writes the value (`AudioState.getAuthority()`): server-authority axes are set by server logic and broadcast; client-authority axes are written locally by an ambience's `SetStates` |
| `Values` | array | — | Ordered value names (`getValues()`); non-empty, unique, and `*` is reserved |
| `DefaultValue` | string | — | Initial value (`getDefaultValue()` / `getDefaultValueIndex()`); must be one of `Values` |
| `DefaultSyncTo` | object | — | Default [sync point](#sync-points-and-musical-time) for edges with no `SyncTo`; omit to switch immediately |
| `DefaultTransition` | object | — | Fallback edge (a `StateTransitionConfig` without `From`/`To`) |
| `Transitions` | array | — | Per-edge overrides (below) |
| `RevertWhenInactive` | boolean | `false` | Return to `DefaultValue` when every ambience writing the axis goes inactive. Valid only with `Authority: Client` — the validator fails it otherwise |

### StateTransitionConfig

**Package:** `com.hypixel.hytale.server.core.asset.type.audiostate.config.StateTransitionConfig`

An audio state's `Transitions` array declares per-edge fade behaviour; each edge
decodes into a **`StateTransitionConfig`** (`StateTransitionConfig.CODEC`):

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `From` | string | — | State value name this edge transitions from; `"*"` for wildcard |
| `To` | string | — | State value name this edge transitions to; `"*"` for wildcard |
| `Duration` | object | — | `BarBeatDuration` — `{ "Bars": …, "Beats": …, "Ms": … }`, summed against each subscribed voice's tempo; a voice with no tempo takes `Ms` alone. Must be non-negative. Omit to fall back to `DefaultTransition` |
| `Curve` | `FadeCurve` | `Linear` | `Linear`, `Logarithmic`, `Exponential`, `SCurve`, `EqualPowerSine`; read only alongside a `Duration` |
| `SyncTo` | object | — | [Sync point](#sync-points-and-musical-time) at which the transition begins; a signed `Offset` moves the start off the boundary. Omit to use `DefaultSyncTo`. A voice with no tempo and no markers begins immediately regardless |
| `Delay` | object | — | `BarBeatDuration` a voice holds its old level past the boundary before ramping (non-negative; an audio category has no hold, so there it lengthens the ramp) |
| `PostEvent` | string | — | [Music event](#music-events) posted when the edge is taken (0.7.2+); a blank value fails validation |

> **Changed in 0.7.2:** `DurationMs` (a float) was replaced by `Duration`, a `BarBeatDuration` object — write
> `"Duration": { "Ms": 2000 }` where 0.6.8 took `"DurationMs": 2000.0` — and `SyncTo` / `DefaultSyncTo` changed from a
> bare `SyncPoint` string to an object (`{ "Point": "NextBar" }`). `Delay` and `PostEvent` are new.

The same `StateTransitionConfig` shape is an ambience `SetStates` write's `TransitionOverride`, where `From`/`To`
are unused.

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

### State bindings

**Package:** `com.hypixel.hytale.server.core.asset.type.audiostate.config.StateDeltaConfig` (with `StateBindingConfig` and `StateFadeConfig`)

Anything that reacts to an axis carries a `StateBindings` array of **`StateBindingConfig`** — `AudioState` (the axis
id) and `Deltas`, one **`StateDeltaConfig`** per value; values left unlisted have no effect. At most one binding per
axis per subscriber.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Value` | string | — | State value this delta applies to (`*` is rejected here — wildcards are for transitions only) |
| `VolumeDb` | float | `0.0` | Signed dB offset while this value is active, −144 to 10; ignored when `Mute` is true |
| `Mute` | boolean | `false` | Silence the subscriber for this value (fading still applies) |
| `PitchSemitones` | float | `0.0` | Signed semitone offset, −60 to 12 (`-60` is a "time-stop" freeze) |
| `Fade` | object | — | This subscriber's own ramp onto the value (0.7.2+), overriding the axis transition field by field (below) |

A **`StateFadeConfig`** (`Fade`) has `Duration` (`BarBeatDuration`), `Curve` (`FadeCurve`, default `Linear`, read
only alongside a `Duration`) and `Delay` (`BarBeatDuration`, non-negative). A `Fade` with neither `Duration` nor
`Delay` fails validation. A transition override sent with the state change still outranks it. Bars and beats need a
tempo: only music containers have one (their own, or that of the `Segment` they are a direct layer of), so on sound
events, audio categories and ambience a `Fade` must be written in `Ms` — anything else fails with
"Duration is in bars or beats, which this subscriber has no tempo to resolve. Use Ms". Where several bindings cover
one axis for a voice, later ones refine earlier ones: music composes ancestors, then the `Segment`, then the
`LayerPlacement`, then the leaf container. `Tracks/Events/Track_The_Veil_Draws_In.json` gives each layer delta a
`"Fade": { "Duration": { "Beats": 4 }, "Curve": "Logarithmic" }`.

---

## Driving Music from Java

**Package:** `com.hypixel.hytale.builtin.audio.components`

The `builtin.audio` plugin attaches two components to every player, and they are the server-side handles on
that player's music. Both are registered without an id or codec, so neither is written to the player's save; a player starts each
session with no forced music and every axis at its default.

- **`ForcedMusicTracker`** — `setCurrentContainerIndex(int)` / `getCurrentContainerIndex()`. A tick system sends
  `UpdateForcedMusic` whenever the index differs from the last one sent; `0` clears it.
- **`AudioStateComponent`** — `setValue(int axisIndex, int valueIndex, StateTransition transitionOverride)`. It
  ignores axes whose `Authority` is `Client`, out-of-range values, and a repeat of the current value with the same
  override. A tick system sends one `SetAudioState` per changed axis. Pass `null` as the override to let the
  axis's own `Transitions` apply (the path the shipped encounters take, and the one that posts an edge's
  `PostEvent`); `AudioStateSetCommand` builds an override from a bare fade length when one is wanted.

The helper below is assembled from `AudioMusicForceCommand` and `AudioStateSetCommand`. It touches the entity
store, so call it on the world thread (inside `world.execute(...)` from elsewhere).

```java
package com.example.music;

import com.hypixel.hytale.builtin.audio.components.AudioStateComponent;
import com.hypixel.hytale.builtin.audio.components.ForcedMusicTracker;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.AudioStateAuthority;
import com.hypixel.hytale.protocol.packets.world.PostMusicEvent;
import com.hypixel.hytale.server.core.asset.type.audiostate.config.AudioState;
import com.hypixel.hytale.server.core.asset.type.audiostate.config.AudioStateResolver;
import com.hypixel.hytale.server.core.asset.type.musiccontainer.config.MusicContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public final class MusicControl {
    private MusicControl() {
    }

    /** Force a music container on one player; a null id clears it. */
    public static boolean forceMusic(Store<EntityStore> store, Ref<EntityStore> player, String containerId) {
        ForcedMusicTracker tracker = store.getComponent(player, ForcedMusicTracker.getComponentType());
        if (tracker == null) {
            return false;
        }
        int index = 0; // 0 is the empty container
        if (containerId != null) {
            index = MusicContainer.getAssetMap().getIndex(containerId);
            if (index == Integer.MIN_VALUE) {
                return false; // unknown container id
            }
        }
        tracker.setCurrentContainerIndex(index);
        return true;
    }

    /** Move a Server-authority audio state for one player, through the axis's own edges. */
    public static boolean setAudioState(Store<EntityStore> store, Ref<EntityStore> player, String audioStateId, String value) {
        AudioState axis = AudioState.getAssetMap().getAsset(audioStateId);
        if (axis == null || axis.getAuthority() != AudioStateAuthority.Server) {
            return false;
        }
        int valueIndex = AudioStateResolver.resolveValueIndex(value, axis.getValues());
        AudioStateComponent states = store.getComponent(player, AudioStateComponent.getComponentType());
        if (valueIndex < 0 || states == null) {
            return false;
        }
        states.setValue(AudioState.getAssetMap().getIndex(audioStateId), valueIndex, null);
        return true;
    }

    /** Post a music event to one client; the playing music's Stingers bindings decide what it plays. */
    public static void postMusicEvent(PlayerRef playerRef, String musicEvent) {
        playerRef.getPacketHandler().write(new PostMusicEvent(musicEvent));
    }
}
```

**An encounter overwrites both every tick.** Every encounter entity carries an `EncounterAudioState`, and
`EncounterAudioState.applyToPlayer` runs for each tracked member on every tick: it writes the encounter's desired
container to `ForcedMusicTracker` (`0` until a `StartEncounterMusic` runs) and any axis values its
`SetEncounterAudioState` actions set. On release it resets the container to `0` and those axes to their defaults.
So forced music a plugin sets lasts one tick for a player any encounter is tracking, as does a plugin-set value on
an axis that encounter drives.

---

## Gotchas & Errors

- **`AudioState value name '*' is reserved for wildcard matching in transitions`** → an [`AudioState`](#audiostate-transitions) asset put the literal `*` in its `Values` array. Fix: `*` is only legal as a `From`/`To` wildcard inside a `Transitions` edge; rename the value.
- **`RevertWhenInactive requires Authority: Client`** → `RevertWhenInactive: true` on a server-authority axis. Server-authority axes are reverted by whatever set them (an encounter reverts its members on release).
- **`Segment requires a Tempo when EntryMarker, ExitMarker, or ClipStart use bar/beat components`** → give the Segment a `Tempo`, or author those positions in `Ms`.
- **`Align: NamedMarker needs a container that can declare Markers`** → `NamedMarker` on a non-`Segment` container. Wrap the track in a `Segment` that declares the marker.
- **`needs a Tempo on From container`** (the full message starts `ExitAt Point NextBeat` or `NextBar`) → a [MusicTransition](#musictransition) waits for a beat or bar of a container with no tempo (its own, or one found among its children). Add a `Tempo`, or use `Immediate` / `ExitMarker`.
- **`maps phases but names no AudioState`** → a `Horizontal` container has `Phases` without `AudioState`.
- **A stinger never plays.** The event must be bound on a container that is *playing* when the event is posted (or on one of its ancestors), the `Stinger` id must resolve (an unknown one only logs "the binding will do nothing" when the container is sent), and `MinRepeatIntervalSeconds` or an outranking stinger in the same `ExclusionGroup` may be suppressing it.
- **A container without `TransitionType` switches differently than in 0.6.8.** The default moved from `Crossfade` to `FadeOutFadeIn`; set `"TransitionType": "Crossfade"` to keep the old behaviour.
- **Forced music or an axis set from a plugin snaps back.** An encounter tracking that player re-applies its own values every tick — see [Driving Music from Java](#driving-music-from-java).
