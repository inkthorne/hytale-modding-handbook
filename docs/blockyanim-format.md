---
title: "Block Animation Format (.blockyanim)"
description: "The Hytale .blockyanim format — animate block-model parts (move, rotate, scale, toggle visibility) over time for doors, chests, fire, and mechanical effects."
seo:
  type: TechArticle
---

# Block Animation Format (.blockyanim)

**Doc type:** JSON asset format · **Assets:** `Common` · **Verified against 0.6.3**

This document describes the `.blockyanim` file format used for animating block states in Hytale.

## Overview

Blockyanim files define animations for block models, controlling how individual parts of a block move, rotate, scale, and change visibility over time. These are commonly used for:

- Doors opening and closing
- Chests opening
- Fire and light flickering effects
- Mechanical block animations
- Environmental decorations

## Architecture
```
.blockyanim (JSON)
├── formatVersion / duration / holdLastKeyframe  (top-level fields)
└── nodeAnimations          map of node name → animation tracks
    └── per-node tracks
        ├── position         {x, y, z}
        ├── orientation       {x, y, z, w} quaternion
        ├── shapeStretch      {x, y, z} scale
        ├── shapeVisible       boolean (instant switch)
        └── shapeUvOffset      {x, y} texture-pixel offset
            └── keyframes      time (frame @ 60 FPS) + delta + interpolationType (smooth | linear)
```

## Key Classes

| Section | Location | Description |
|---------|----------|-------------|
| Top-level fields | `.blockyanim` root | `formatVersion`, `duration`, `holdLastKeyframe`, `nodeAnimations` |
| `nodeAnimations` | `.blockyanim` root | Map of node name (from `.blockymodel`) to its animation tracks |
| `position` / `orientation` / `shapeStretch` / `shapeUvOffset` track | node track | Interpolated transform/UV tracks of keyframes |
| `shapeVisible` track | node track | Boolean visibility track (no interpolation) |
| Keyframe | track entry | `time` (frame) + `delta` value + `interpolationType` |

## File Location

Despite the "block animation" name, `.blockyanim` files animate any blockymodel — and in the shipped assets they are overwhelmingly used for **characters and NPCs**, not blocks. Distribution of the 6,736 shipped files under `Common/` (0.6.3):

| Location | Files | Typical use |
|----------|-------|-------------|
| `NPC/` | 4,310 | NPC/creature animations |
| `Characters/` | 2,309 | Player and character animations |
| `Blocks/` | 77 | Doors, chests, benches, lights, mechanical blocks |
| `Items/` | 37 | Item animations |
| `VFX/`, `Resources/` | 3 | Effect animations |

The generic block clips live under `Common/Blocks/Animations/`, one folder per block kind: `Door/` (6 — `Door_Open_In`,
`Door_Open_Out`, `Door_Close_In`, `Door_Close_Out`, `Door_Open_Slide_In`, `Door_Open_Slide_Out`), `Chest/` (`Chest_Open`,
`Chest_Close`), `Trapdoor/`, `Wardrobe/`, `Coffin/`, `Light/`, `Fire/`, `Candle/`. The remaining block animations sit
beside their models — `Blocks/Benches/` (20), `Blocks/Decorative_Sets/<Set>/`, `Blocks/Tinkering/Traps/`, etc.

The server validates a block's `CustomModelAnimation` path with `CommonAssetValidator.ANIMATION_ITEM_BLOCK`: it must start
with `Blocks/`, `Items/`, `Resources/`, `NPC/`, `VFX/` or `Consumable/`, end in `.blockyanim`, and exist in the
common-asset registry.

## Frame Rate

Animations run at **60 frames per second**. All time values in keyframes are specified in frames at this rate — the
server's `BlockyAnimationCache.BlockyAnimation.FRAMES_PER_SECOND` is `60.0`, with `getDurationFrames()`,
`getDurationMillis()` (`duration * 1000 / 60`) and `getDurationSeconds()` (`duration / 60`) reading off it. (The
shipped `Door_Open_Out` clip is `duration: 60` — one second — and the `Door` node's own swing is finished by frame 20;
the trailing frames are the knocker settling.) `BlockyAnimationCache` is also the *only* thing the server reads from a
`.blockyanim`: `BlockyAnimation.CODEC` decodes just the (required) `duration` key; the tracks are consumed by the
client.

## File Structure

```json
{
  "formatVersion": 1,
  "duration": 10,
  "holdLastKeyframe": true,
  "nodeAnimations": {
    "NodeName": {
      "position": [...],
      "orientation": [...],
      "shapeStretch": [...],
      "shapeVisible": [...],
      "shapeUvOffset": [...]
    }
  }
}
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `formatVersion` | integer | Usually | Schema version, currently `1`. Present in 6,732 of 6,736 shipped files |
| `duration` | integer | Yes | Total animation length in frames (at 60 FPS). Shipped range 9–600; block clips 21–180 (median 50) |
| `holdLastKeyframe` | boolean | Yes in practice | If `true`, animation holds the final keyframe values when complete; if `false` it loops. Every shipped file sets it explicitly (5,741 `false`, 995 `true`) — do not rely on a default |
| `nodeAnimations` | object | Yes | Map of node names to their animation tracks |

## Node Animations

The `nodeAnimations` object maps node names (as defined in the block's `.blockymodel`) to animation data. Each node can use any combination of the five track types — but the editor always writes **all five keys**, with `[]` for unused tracks (every one of the 129,603 shipped node entries lists all five), so do the same.

### Animation Track Types

| Track | Value Type | Description |
|-------|------------|-------------|
| `position` | `{"x", "y", "z"}` | Translates the node in 3D space |
| `orientation` | `{"x", "y", "z", "w"}` | Rotates the node using quaternion values |
| `shapeStretch` | `{"x", "y", "z"}` | Scales the node along each axis |
| `shapeVisible` | `boolean` | Shows or hides the node |
| `shapeUvOffset` | `{"x", "y"}` | Offsets the shape's texture-atlas origin in **texture pixels** (e.g. `{"x": 160, "y": 0}` to swap a face to the next sprite); used for mouth/eye sprite swaps and scrolling. The keys are `x`/`y`, **not** `u`/`v` — all 651 shipped keyframes use `x`/`y` |

## Keyframe Structure

Each track contains an array of keyframes. Keyframe structure varies by track type:

### Position/Orientation/ShapeStretch/ShapeUvOffset Keyframes

```json
{
  "time": 0,
  "delta": {"x": 0.0, "y": 0.5, "z": 0.0},
  "interpolationType": "smooth"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `time` | integer | Frame number (at 60 FPS) when this keyframe occurs |
| `delta` | object | The value at this keyframe (format depends on track type) |
| `interpolationType` | string | How to interpolate to this keyframe. Optional — omitted on 936 shipped keyframes (most of them `shapeUvOffset`, which is a sprite swap rather than a blend) |

### ShapeVisible Keyframes

```json
{
  "time": 5,
  "delta": false
}
```

Visibility keyframes don't use interpolation - they switch instantly.

## Interpolation Types

| Type | Description |
|------|-------------|
| `smooth` | Smooth interpolation (most common) |
| `linear` | Linear interpolation between keyframes |

## Examples

### Simple Door Animation

A door that swings open over 20 frames (⅓ s) and holds:

```json
{
  "formatVersion": 1,
  "duration": 20,
  "holdLastKeyframe": true,
  "nodeAnimations": {
    "Door": {
      "position": [],
      "orientation": [
        {
          "time": 0,
          "delta": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
          "interpolationType": "smooth"
        },
        {
          "time": 20,
          "delta": {"x": 0.0, "y": 0.707, "z": 0.0, "w": 0.707},
          "interpolationType": "smooth"
        }
      ],
      "shapeStretch": [],
      "shapeVisible": [],
      "shapeUvOffset": []
    }
  }
}
```

The shipped `Blocks/Animations/Door/Door_Open_Out.blockyanim` is the same idea with more keys (`duration: 60`, orientation
keys at frames 0/10/15/20 for a little overshoot) plus knocker and knob nodes.

### Visibility Switching

`shapeVisible` swaps which nodes of a model are drawn. The shipped `Blocks/Animations/Light/Light_On.blockyanim` is the
minimal case — a single key per node, no motion at all, used to pick the lit or unlit variant of a lamp model (its
sibling `Light_Off.blockyanim` is the same file with the two `delta` values swapped):

```json
{
  "formatVersion": 1,
  "duration": 60,
  "holdLastKeyframe": false,
  "nodeAnimations": {
    "Light_Off": { "shapeVisible": [ { "time": 0, "delta": false } ] },
    "Light_On":  { "shapeVisible": [ { "time": 0, "delta": true  } ] }
  }
}
```

*(empty tracks elided — the real file also carries the four empty transform tracks per node).* Add more keys to the
same track for a flicker; because `holdLastKeyframe` is `false` the clip loops, so the toggles repeat every
`duration` frames. The shipped fire and candle clips take the other route and animate `position` / `shapeStretch` /
`shapeUvOffset` instead (`Fire_Burn.blockyanim`, `duration: 30`; `Candle_Burn.blockyanim`, `duration: 40`).

### UV Offset (Sprite Swap / Scroll)

`shapeUvOffset` shifts where the shape samples its texture, in texture pixels. The shipped assets use it as a sprite
swap — e.g. the `Mouth` node of `NPC/Intelligent/Kweebec_Sapling/Animations/Default/Alerted.blockyanim` jumps
between mouth sprites laid out 160 px apart, with no `interpolationType` so each key snaps:

```json
{
  "formatVersion": 1,
  "duration": 40,
  "holdLastKeyframe": false,
  "nodeAnimations": {
    "Mouth": {
      "shapeUvOffset": [
        {"time": 0,  "delta": {"x": 0,   "y": 0}},
        {"time": 10, "delta": {"x": 160, "y": 0}},
        {"time": 20, "delta": {"x": 140, "y": -20}},
        {"time": 30, "delta": {"x": 0,   "y": -32}}
      ]
    }
  }
}
```

Add `"interpolationType": "linear"` to the keys for a continuous scroll (water, conveyors).

### Chest Opening with Multiple Nodes

A chest whose lid rotates while a button sinks, then pops back — trimmed from the shipped
`Blocks/Animations/Chest/Chest_Open.blockyanim` (`duration: 35`; position deltas are in model pixels):

```json
{
  "formatVersion": 1,
  "duration": 35,
  "holdLastKeyframe": true,
  "nodeAnimations": {
    "Lid": {
      "orientation": [
        {"time": 0,  "delta": {"x": 0, "y": 0, "z": 0, "w": 1}, "interpolationType": "smooth"},
        {"time": 5,  "delta": {"x": 0, "y": 0, "z": 0, "w": 1}, "interpolationType": "smooth"},
        {"time": 10, "delta": {"x": 0.043619, "y": 0, "z": 0, "w": 0.999048}, "interpolationType": "smooth"}
      ]
    },
    "Button": {
      "position": [
        {"time": 0,  "delta": {"x": 0, "y": 0, "z": 0},  "interpolationType": "smooth"},
        {"time": 5,  "delta": {"x": 0, "y": 0, "z": -2}, "interpolationType": "smooth"},
        {"time": 10, "delta": {"x": 0, "y": 0, "z": -1}, "interpolationType": "smooth"}
      ]
    },
    "Padlock-Shackle-Gap": {
      "shapeVisible": [
        {"time": 0,  "delta": true},
        {"time": 10, "delta": false},
        {"time": 35, "delta": false}
      ]
    }
  }
}
```

## Integration with Blocks

Blocks reference animations through the `CustomModelAnimation` property of their `BlockType`. It can sit directly on
the `BlockType` (28 of the 367 shipped references — always-on loops such as fires and lights), but the usual place is a
**block-state definition** under `BlockType.State.Definitions.<State>` (338, six of them nested one level deeper), so
that each state — open, closed — plays its own clip. Abridged from
`Server/Item/Items/Furniture/Desert/Furniture_Desert_Door.json`:

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Decorative_Sets/Desert/Door.blockymodel",
    "State": {
      "Definitions": {
        "OpenDoorOut": {
          "HitboxType": "Door_Open_Out",
          "InteractionSoundEventId": "SFX_Door_Desert_Open",
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_Out.blockyanim"
        },
        "CloseDoorOut": {
          "InteractionSoundEventId": "SFX_Door_Desert_Close",
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_Out.blockyanim"
        }
      }
    }
  }
}
```

The animation path is relative to `Common/` and **includes** the `.blockyanim` extension — all 367 shipped references
do, and `CommonAssetValidator.ANIMATION_ITEM_BLOCK` rejects a path without it (`Common Asset '<path>' must have the
extension blockyanim`).

| `BlockType` key | Type | Description |
|-----------------|------|-------------|
| `CustomModelAnimation` | string | Path of the `.blockyanim` to play on the block's `CustomModel` (per state or block-wide) |
| `CustomModelAnimationSpeed` | float | Playback-speed multiplier; `1` is the authored speed. Validated `0 <= v < 100` (`BlockType.MAX_CUSTOM_MODEL_ANIMATION_SPEED` is `100.0f`). Added as of 0.6.3 (`BlockType.getCustomModelAnimationSpeed()`); no shipped asset sets it yet |

## Looping Behavior

- If `holdLastKeyframe` is `false`, the animation loops back to the start
- If `holdLastKeyframe` is `true`, the animation plays once and holds the final values
- Looping animations (fire, water) typically set `holdLastKeyframe: false`
- State transitions (doors, chests) typically set `holdLastKeyframe: true`

## Best Practices

1. **Keep durations short** - Shipped block clips run 21–180 frames (median 50, i.e. ⅓–3 s at 60 FPS); doors and chests finish their motion within the first 20–35 frames and hold
2. **Use smooth for mechanical motion** - Doors and lids feel more natural with smooth interpolation (429,461 of the shipped keyframes are `smooth`, 18,339 `linear`)
3. **Match node names exactly** - Node names must match those in the `.blockymodel` file
4. **Consider reverse animations** - Doors need both open and close animations (the shipped set pairs `Door_Open_Out`/`Door_Close_Out`, `Chest_Open`/`Chest_Close`)
5. **Time at 60 FPS** - Remember the fixed frame rate when timing animations (60 frames = 1 second)

## Gotchas & Errors

- **Symptom:** an animation has no visible effect on the model → its node animations name nodes that don't exist in the target `.blockymodel`. Fix: node names must match exactly between the `.blockyanim` and the `.blockymodel`.
- **Symptom:** timings feel too fast or too slow → keyframe time values are interpreted as frames at a **fixed 60 FPS** (`BlockyAnimationCache.BlockyAnimation.FRAMES_PER_SECOND`), not seconds or 20 FPS ticks. Fix: convert seconds to frames (1 second = 60 frames).
- **Symptom:** a one-shot animation (door, chest) snaps back to its start instead of holding → `holdLastKeyframe` is `false`. Fix: set `"holdLastKeyframe": true` for play-once animations; set it `false` for looping ones (always write it explicitly).
- **Symptom:** UV animation does nothing → the `shapeUvOffset` deltas were written as `{u, v}`. Fix: the keys are `{x, y}`, in texture pixels.
- **`Common Asset '`** → the start of the three `CommonAssetValidator.ANIMATION_ITEM_BLOCK` failures, each assembled by concatenation: `Common Asset '<path>' must have the extension blockyanim`, `Common Asset '<path>' must be within the root: [Blocks/, Items/, Resources/, NPC/, VFX/, Consumable/]`, and `Common Asset '<path>' doesn't exist!`. Fix: include the `.blockyanim` extension, keep the clip under an allowed root, and make sure the file ships in the pack.
