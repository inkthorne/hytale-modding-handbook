---
title: "Block Model Format (.blockymodel)"
description: "The Hytale .blockymodel format — build 3D models from a hierarchical node system of mesh shapes and child nodes, for non-cube blocks, furniture, items, and decorations."
seo:
  type: TechArticle
---

# Block Model Format (.blockymodel)

**Doc type:** JSON asset format · **Assets:** `Common` · **Verified against 0.6.3**

This document describes the `.blockymodel` file format used for defining 3D geometry in Hytale.

## Overview

Blockymodel files define 3D models using a hierarchical node system. Each node can contain mesh geometry (shapes) and child nodes, allowing complex models to be built from simple primitives. These are used for:

- Non-cube block shapes (doors, furniture, decorations)
- Item models (weapons, tools, consumables)
- Character models (players, NPCs, creatures)
- Environmental props and vegetation

Blockymodel files work closely with `.blockyanim` files - the model defines geometry and node names, while animations reference those nodes to apply transformations over time.

## Architecture
```
.blockymodel (JSON)
├── lod                "auto" | "off" | "disappear" | "billboard"
├── format             optional: "character" | "prop"
└── nodes[]            hierarchical node tree
    └── node           id, name, position, orientation
        ├── shape       mesh geometry
        │   ├── box      sized cuboid
        │   ├── quad     flat 2D plane
        │   └── none     transform-only (no mesh)
        │       └── textureLayout  per-face UV layout
        └── children[]  nested nodes
```

## Key Classes

| Section | Location | Description |
|---------|----------|-------------|
| Top-level fields | `.blockymodel` root | `nodes` array, optional `lod` mode and `format` tag |
| Node | `nodes[]` entry | `id`, `name`, `position`, `orientation`, optional `shape` and `children` |
| `box` shape | node `shape` | Cuboid mesh defined by `size` per dimension |
| `quad` shape | node `shape` | Flat 2D plane (foliage, flat decorations) |
| `none` shape | node `shape` | Transform-only node with no mesh |
| `textureLayout` | node `shape` | Per-face UV/texture layout |

## File Location

Models live under `Common/`, grouped by what they are for (counts are the shipped `.blockymodel` files as of 0.6.3, 2,830 in total):

| Category | Location | Shipped files |
|----------|----------|---------------|
| Block models | `Common/Blocks/<Category>/` — `Decorative_Sets/`, `Structures/`, `Foliage/`, `Benches/`, `Miscellaneous/`, `Dungeons/`, `Tinkering/`, `Stone/`, `Farming/` … | 1,151 |
| NPC models | `Common/NPC/` | 669 |
| Item models | `Common/Items/` | 454 |
| Cosmetics (haircuts, etc.) | `Common/Cosmetics/` | 285 |
| Character models | `Common/Characters/` | 168 |
| Resource/ingredient models | `Common/Resources/` | 101 |
| Effect models | `Common/VFX/` | 2 |

There is no `Common/Blocks/Models/` folder — block models sit beside their textures and animations inside a category
folder (e.g. `Blocks/Decorative_Sets/Desert/Door.blockymodel` next to `Door_Texture.png`).

Asset **validation** only checks the model's *path*: a block's `CustomModel` goes through
`CommonAssetValidator.MODEL_ITEM`, which requires the path to start with one of `Blocks/`, `Items/`, `Resources/`,
`NPC/`, `VFX/` or `Consumable/`, to end in `.blockymodel`, and to exist in the common-asset registry
(`MODEL_CHARACTER` is the equivalent for character models: `Characters/`, `NPC/`, `Items/`, `VFX/`).

The geometry itself is rendered by the client, but the server does read one thing out of it:
`BlockyModelBoundsParser.computeBounds(String modelPath)` walks the `nodes` tree — honouring `position`,
`orientation`, `shape.offset`, `shape.stretch`, `shape.settings.size`, `shape.settings.normal` and `shape.visible` —
and returns the model's world-space `Box`. Invisible nodes (`"visible": false`) and `none` shapes contribute nothing;
a model whose every shape is invisible yields `null`. A file it cannot parse logs
`Failed to compute bounds for blockymodel: <name>` and yields `null` rather than failing the asset.

## File Structure

```json
{
  "nodes": [...],
  "lod": "auto"
}
```

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodes` | array | Yes | Array of root-level node objects defining the model hierarchy (688 shipped models have more than one root) |
| `lod` | string | No | Level-of-detail mode: `"auto"` (2,673 files), `"off"` (132), `"disappear"` (6 — foliage such as `Blocks/Foliage/Plants/Mushroom.blockymodel`) or `"billboard"` (6 — leaves such as `Blocks/Foliage/Leaves/PineShape.blockymodel`). 13 files omit it |
| `format` | string | No | Model kind tag written by the editor: `"character"` (272 files — mostly `Characters/` (120), `Cosmetics/` (76) and `NPC/` (39), but also `Items/` (26), `Resources/` (6) and `Blocks/` (5)) or `"prop"` (93 files, all under `Blocks/`). Absent from 2,465 of the 2,830 files |
| `lodFriendly` | boolean | No | Rare editor flag (3 files) |
| `editor` | string | No | Rare provenance tag, e.g. `"blockbench"` (15 files) |

## Node Structure

Each node in the hierarchy can contain geometry and/or child nodes:

```json
{
  "id": "1",
  "name": "Body",
  "position": {"x": 0.0, "y": 0.0, "z": 0.0},
  "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
  "shape": {...},
  "children": [...]
}
```

### Node Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for the node within the model. Stored as a quoted string even when numeric (e.g. `"146"`) |
| `name` | string | Yes | Human-readable name (referenced by animations) |
| `position` | object | No | 3D position offset `{x, y, z}` relative to parent's mesh center (parent node position + parent shape offset) |
| `orientation` | object | No | Quaternion rotation `{x, y, z, w}` |
| `shape` | object | No | Mesh geometry definition |
| `children` | array | No | Array of child node objects |

In practice every node in the shipped assets carries all of `id`, `name`, `position`, `orientation` and `shape`
(39,440 of 39,440 nodes); only `children` is ever omitted. Write all five to match the editor's output.

### Position and Orientation

Position values are in model units — **32 units = 1 block**. The server's `BlockyModelBoundsParser` converts model
space to world space with `BLOCK_SCALE = 0.03125f` (1/32), and the shipped `Blocks/Structures/Base_Shapes/`
primitives confirm it: `HalfBlock.blockymodel` measures 32 × 16 × 32 units and `QuarterBlock.blockymodel`
32 × 8 × 32, i.e. 1 × ½ × 1 and 1 × ¼ × 1 blocks. Orientation uses quaternion format where
`{x: 0, y: 0, z: 0, w: 1}` represents no rotation.

Common quaternion values:

| Rotation | Quaternion |
|----------|------------|
| No rotation | `{x: 0, y: 0, z: 0, w: 1}` |
| 90° around Y | `{x: 0, y: 0.707, z: 0, w: 0.707}` |
| 180° around Y | `{x: 0, y: 1, z: 0, w: 0}` |
| 90° around X | `{x: 0.707, y: 0, z: 0, w: 0.707}` |

## Shape Types

The `shape` object defines the mesh geometry for a node. The `type` field determines what kind of primitive is used.

### Box Shape

Cuboid meshes defined by size in each dimension:

```json
{
  "type": "box",
  "offset": {"x": 0, "y": 0, "z": 0},
  "stretch": {"x": 1.0, "y": 1.0, "z": 1.0},
  "settings": {
    "size": {"x": 8, "y": 8, "z": 8}
  },
  "visible": true,
  "doubleSided": false,
  "shadingMode": "standard",
  "unwrapMode": "custom",
  "textureLayout": {...}
}
```

Size values are in model units (32 units = 1 block). The box is centred on the node's shape origin — `size` is the
full span, so the corners sit at ±`size/2` before `stretch` is applied.

| Field | Type | Description |
|-------|------|-------------|
| `settings.size` | object | Box dimensions in model units `{x, y, z}` (always present) |
| `settings.isPiece` | boolean | Optional editor flag (3,564 boxes; also on every `none` shape) |
| `settings.isStaticBox` | boolean | Optional editor flag (931 boxes) |

### Quad Shape

Flat 2D planes, commonly used for foliage and flat decorations:

```json
{
  "type": "quad",
  "offset": {"x": 0, "y": 0, "z": 0},
  "settings": {
    "size": {"x": 32, "y": 32},
    "normal": "+Z"
  },
  "doubleSided": true,
  "textureLayout": {...}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `settings.size` | object | Width and height in model units — `{x, y}` on 10,980 shipped quads, `{x, y, z}` on 319 (the `z` is ignored) |
| `settings.normal` | **string** | Axis the quad lies on: `"+Z"` (9,385 shipped quads), `"-Z"` (767), `"+Y"` (295), `"+X"` (263), `"-X"` (167), `"-Y"` (52). Present on 10,929 of 11,299 quads; `BlockyModelBoundsParser` defaults a missing one to `"+Z"`. It is **not** a `{x, y, z}` vector |
| `settings.isPiece` / `settings.isStaticBox` | boolean | Optional editor flags, as for boxes |

The `±X` / `±Y` / `±Z` pairs each select the same corner set, so the sign only affects which way the face is lit and
textured, not the quad's extent.

### None Shape

Structural nodes without visible geometry. Used for grouping, attachment points, and animation pivots:

```json
{
  "type": "none"
}
```

> **Note:** `{"type": "none"}` is the minimal logical form. In practice, none-shapes exported by the asset editor still carry the full set of shape fields (`offset`, `stretch`, `settings`, `visible`, `doubleSided`, `shadingMode`, `unwrapMode`, `textureLayout`) just like a box — only `type` distinguishes them. All none-shapes in the shipped assets include these fields.

## Shape Properties

### Common Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `offset` | object | `{x:0, y:0, z:0}` | Position offset within the shape |
| `stretch` | object | `{x:1, y:1, z:1}` | Scale factors (can be negative for mirroring) |
| `visible` | boolean | `true` | Whether the shape renders |
| `doubleSided` | boolean | `false` | Render both front and back faces |

> **Note:** The `offset` property affects where child nodes are positioned. Children with a `position` are placed relative to the parent's mesh center (parent position + parent offset), not just the parent's node origin. This allows attachment points to be relative to the visible mesh rather than the pivot point.

### Shading Modes

| Mode | Shipped shapes | Description |
|------|----------------|-------------|
| `"flat"` | 29,722 | Flat/unlit shading, no shadows — the most common value |
| `"standard"` | 8,844 | Normal lighting and shading |
| `"fullbright"` | 765 | Always fully lit (emissive-looking) |
| `"reflective"` | 106 | Reflective surface rendering |

### Unwrap Modes

| Mode | Shipped shapes | Description |
|------|----------------|-------------|
| `"custom"` | 38,587 | Use the explicit `textureLayout` for UV coordinates — effectively the default |
| `"full"` | 613 | Automatic unwrap of the whole shape |
| `"collapsed"` | 240 | Automatic unwrap with all faces collapsed onto one region |

There is **no** `"standard"` unwrap mode — it appears in no shipped model.

## Texture Layout

The `textureLayout` object defines how textures map to each face of a shape.

### Box Texture Layout

Boxes have six faces that can each be configured:

```json
{
  "textureLayout": {
    "top": {"offset": {"x": 16, "y": 0}, "mirror": {"x": false, "y": false}, "angle": 0},
    "bottom": {"offset": {"x": 16, "y": 16}, "mirror": {"x": false, "y": false}, "angle": 0},
    "front": {"offset": {"x": 0, "y": 8}, "mirror": {"x": false, "y": false}, "angle": 0},
    "back": {"offset": {"x": 24, "y": 8}, "mirror": {"x": false, "y": false}, "angle": 0},
    "left": {"offset": {"x": 8, "y": 8}, "mirror": {"x": false, "y": false}, "angle": 0},
    "right": {"offset": {"x": 32, "y": 8}, "mirror": {"x": false, "y": false}, "angle": 0}
  }
}
```

### Quad Texture Layout

Quads have a single `front` face (a `back` entry appears on only 16 of 11,299 shipped quads):

```json
{
  "textureLayout": {
    "front": {"offset": {"x": 0, "y": 0}, "mirror": {"x": false, "y": false}, "angle": 0}
  }
}
```

### Face Layout Properties

| Property | Type | Description |
|----------|------|-------------|
| `offset` | object | Texture coordinates `{x, y}` in pixels from top-left of texture |
| `mirror` | object | Flip texture on X and/or Y axis `{x: bool, y: bool}` |
| `angle` | integer | Rotation angle in degrees (0, 90, 180, 270) |

## Examples

### Simple Single-Box Model

A full-block cube (32 units on a side):

```json
{
  "nodes": [
    {
      "id": "1",
      "name": "Cube",
      "shape": {
        "type": "box",
        "settings": {
          "size": {"x": 32, "y": 32, "z": 32}
        },
        "shadingMode": "standard",
        "textureLayout": {
          "top": {"offset": {"x": 16, "y": 0}},
          "bottom": {"offset": {"x": 32, "y": 0}},
          "front": {"offset": {"x": 0, "y": 16}},
          "back": {"offset": {"x": 16, "y": 16}},
          "left": {"offset": {"x": 32, "y": 16}},
          "right": {"offset": {"x": 48, "y": 16}}
        }
      }
    }
  ]
}
```

### Multi-Part Model with Hierarchy

A chest with a separate lid for animation — trimmed from the shipped
`Common/Blocks/Decorative_Sets/Kweebec/Chest.blockymodel` (the `textureLayout` blocks are elided). Note that the
`Lid` is a **child of `Base`**, positioned in model units at the hinge, with its box `offset` pushing the mesh forward so the
node origin is the pivot; the `Chest_Open.blockyanim` rotates the `Lid` node about that origin:

```json
{
  "lod": "auto",
  "nodes": [
    {
      "id": "22",
      "name": "R-Attachment",
      "position": {"x": -9, "y": 0, "z": 0},
      "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
      "shape": {"type": "none", "offset": {"x": -7, "y": 0, "z": 0}, "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"isPiece": true}, "visible": true, "doubleSided": false,
                "shadingMode": "standard", "unwrapMode": "custom", "textureLayout": {}},
      "children": [
        {
          "id": "1",
          "name": "Base",
          "position": {"x": 0, "y": 10, "z": 0},
          "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
          "shape": {
            "type": "box",
            "offset": {"x": 0, "y": 0, "z": 0},
            "stretch": {"x": 0.95, "y": 1, "z": 0.95},
            "settings": {"size": {"x": 52, "y": 12, "z": 26}},
            "visible": true, "doubleSided": false,
            "shadingMode": "standard", "unwrapMode": "custom",
            "textureLayout": {...}
          },
          "children": [
            {
              "id": "3",
              "name": "Lid",
              "position": {"x": 0, "y": 6, "z": -12},
              "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
              "shape": {
                "type": "box",
                "offset": {"x": 0, "y": 7, "z": 12},
                "stretch": {"x": 1, "y": -1, "z": 1},
                "settings": {"size": {"x": 51, "y": 14, "z": 26}},
                "visible": true, "doubleSided": false,
                "shadingMode": "standard", "unwrapMode": "custom",
                "textureLayout": {...}
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Quad-Based Foliage Model

A simple grass or flower using crossed quads. `32 × 32` is the most common shipped foliage quad size (a full block
face); the two quads share the same `+Z` normal and are crossed by their node `orientation`:

```json
{
  "nodes": [
    {
      "id": "1",
      "name": "Plant",
      "shape": {"type": "none"},
      "children": [
        {
          "id": "2",
          "name": "Quad1",
          "orientation": {"x": 0, "y": 0.383, "z": 0, "w": 0.924},
          "shape": {
            "type": "quad",
            "settings": {
              "size": {"x": 32, "y": 32},
              "normal": "+Z"
            },
            "doubleSided": true,
            "shadingMode": "flat"
          }
        },
        {
          "id": "3",
          "name": "Quad2",
          "orientation": {"x": 0, "y": -0.383, "z": 0, "w": 0.924},
          "shape": {
            "type": "quad",
            "settings": {
              "size": {"x": 32, "y": 32},
              "normal": "+Z"
            },
            "doubleSided": true,
            "shadingMode": "flat"
          }
        }
      ]
    }
  ]
}
```

### Model with Animated Nodes

A door model with nodes named for animation compatibility — trimmed from the shipped
`Common/Blocks/Decorative_Sets/Desert/Door.blockymodel`. The `Door` node sits at the hinge edge (`x: -16`) and its
box is offset by half its width so the node origin is the rotation pivot:

```json
{
  "lod": "auto",
  "nodes": [
    {
      "id": "22",
      "name": "R-Attachment",
      "position": {"x": 0, "y": 16, "z": 0},
      "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
      "shape": {"type": "none", "offset": {"x": 0, "y": 0, "z": 0}, "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"isPiece": true}, "visible": true, "doubleSided": false,
                "shadingMode": "standard", "unwrapMode": "custom", "textureLayout": {}},
      "children": [
        {
          "id": "7",
          "name": "Door",
          "position": {"x": -16, "y": 16, "z": 0},
          "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
          "shape": {
            "type": "box",
            "offset": {"x": 16, "y": 0, "z": 0},
            "stretch": {"x": 1, "y": 1, "z": 1},
            "settings": {"size": {"x": 32, "y": 64, "z": 4}},
            "visible": true, "doubleSided": false,
            "shadingMode": "standard", "unwrapMode": "custom",
            "textureLayout": {...}
          },
          "children": [
            {
              "id": "9",
              "name": "MetalKnob",
              "position": {"x": 11, "y": 0, "z": 0},
              "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
              "shape": {
                "type": "box",
                "offset": {"x": 0, "y": 0, "z": 0},
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"size": {"x": 3, "y": 6, "z": 10}},
                "visible": true, "doubleSided": false,
                "shadingMode": "standard", "unwrapMode": "custom",
                "textureLayout": {...}
              }
            }
          ]
        }
      ]
    }
  ]
}
```

The corresponding `.blockyanim` references the `Door` node to swing it open (trimmed from the shipped
`Common/Blocks/Animations/Door/Door_Open_Out.blockyanim`; times are frames at **60 FPS**, so the swing lands at
frame 20 = ⅓ s and the 60-frame clip then holds):

```json
{
  "formatVersion": 1,
  "duration": 60,
  "holdLastKeyframe": true,
  "nodeAnimations": {
    "Door": {
      "position": [],
      "orientation": [
        {"time": 0, "delta": {"x": 0, "y": 0, "z": 0, "w": 1}, "interpolationType": "smooth"},
        {"time": 10, "delta": {"x": 0, "y": 0.73728, "z": 0, "w": 0.67559}, "interpolationType": "smooth"},
        {"time": 20, "delta": {"x": 0, "y": 0.70091, "z": 0, "w": 0.71325}, "interpolationType": "smooth"}
      ],
      "shapeStretch": [],
      "shapeVisible": [],
      "shapeUvOffset": []
    }
  }
}
```

## Integration with Blocks and Items

### Block Usage

Blocks reference models through `CustomModel` in their definition (from
`Server/Item/Items/Furniture/Desert/Furniture_Desert_Door.json`):

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Decorative_Sets/Desert/Door.blockymodel",
    "CustomModelTexture": [
      {"Texture": "Blocks/Decorative_Sets/Desert/Door_Texture.png", "Weight": 1}
    ]
  }
}
```

`CustomModelTexture` is an array of `{Texture: string, Weight: integer}` entries (of the 2,884 shipped entries, 2,835
carry `Weight` and 49 omit it); several entries make the game pick a texture variant by weight. The texture path is
relative to `Common/` — usually beside the model (`Blocks/…`), sometimes under `BlockTextures/`. `CustomModelScale`
(float, e.g. `0.5`–`1`) is optional and appears 319 times across 235 shipped asset files (block-state definitions can
each set their own). Animated blocks add `CustomModelAnimation` — see
[Block Animation Format](blockyanim-format.md#integration-with-blocks).

### Item Usage

Items reference models through the `Model` field:

```json
{
  "Model": "Items/Weapons/Sword/Iron.blockymodel"
}
```

Model paths are relative to `Common/` and include the `.blockymodel` extension.

## Best Practices

1. **Root node naming is free for blocks** - `R-Attachment` is the character/NPC convention (the root of the player and most NPC rigs, where attachments hang off named nodes), and 234 of the 1,151 shipped block models use it too — but `Node`, `Origin`, `Block` and `Base` are just as common for blocks, and the server code never references the name

2. **Name nodes for animation** - Use clear, descriptive names that match what you'll reference in `.blockyanim` files

3. **Keep IDs unique** - Each node needs a unique `id` within the model for proper referencing

4. **Use hierarchy for animation** - Child nodes inherit parent transformations, making complex animations easier

5. **Consider LOD settings** - Use `"lod": "auto"` for most models; only disable with `"lod": "off"` if auto-LOD causes issues. Foliage uses `"disappear"` (cull at distance) or `"billboard"` (flatten to a sprite at distance)

6. **Units** - Both sizes and positions are in model units, **32 units = 1 block** (`BlockyModelBoundsParser.BLOCK_SCALE` is `1/32`); texture-layout `offset` values are a separate space, measured in texture pixels

7. **Pivot placement** - Position offsets in shapes determine where the pivot point is - this affects how the shape rotates

8. **Use doubleSided for thin geometry** - Quads and thin boxes should usually have `"doubleSided": true` to be visible from both sides

9. **Match texture layouts to your texture atlas** - Coordinate the `textureLayout` offsets with your actual texture file layout

## Gotchas & Errors

Asset validation only checks the *path* an asset points at (`CommonAssetValidator`). Backtick-quoted strings are its
literal failure messages. Geometry problems surface on the client — the server's only look at the geometry is
`BlockyModelBoundsParser`, which computes a bounding box and never rejects a file.

`CommonAssetValidator` assembles its three failures by concatenation, so the log line reads
`Common Asset '<path>' <tail>` where `<tail>` is one of the three below.

- **`' must be within the root: `** — full line `Common Asset '<path>' must be within the root: [Blocks/, Items/, Resources/, NPC/, VFX/, Consumable/]` → a block's `CustomModel` points outside the allowed top-level folders. Fix: keep block models under one of those roots (character models: `Characters/`, `NPC/`, `Items/`, `VFX/`).
- **`' must have the extension `** — full line `Common Asset '<path>' must have the extension blockymodel` → the path omitted `.blockymodel`. Fix: model references always include the extension.
- **`' doesn't exist!`** — full line `Common Asset '<path>' doesn't exist!` → the file is not in the common-asset registry (typo, wrong folder, or the pack lacks `"IncludesAssetPack": true`). Fix: check the path against `Common/` and the manifest.
- **Symptom:** a shape has no visible size → a `size` component of `0`. Fix: keep every box/quad dimension `> 0` (the asset editor enforces this; the server does not).
- **Symptom:** an animation does not move the part you expect → a `.blockyanim` references a node name that does not exist in this model. Fix: node names must match exactly between the `.blockymodel` and the `.blockyanim`.
- **Symptom:** the model is not picked up by the game → it is in the wrong folder. Fix: place models under an allowed `Common/` root for their kind (blocks: `Blocks/`, `Items/`, `Resources/`, `NPC/`, `VFX/`, `Consumable/`; characters: `Characters/`, `NPC/`, `Items/`, `VFX/`) and reference them with the `.blockymodel` extension.
- **Symptom:** thin geometry is invisible from one side → quads/thin boxes default to single-sided. Fix: set `"doubleSided": true`.
- **Symptom:** a quad renders edge-on or in the wrong plane → `settings.normal` was written as a `{x, y, z}` object. Fix: it is a **string** — one of `"+X"`, `"-X"`, `"+Y"`, `"-Y"`, `"+Z"`, `"-Z"`; anything unrecognised is treated as `"+Z"`.
- **Symptom:** the model is twice (or half) the size you intended → model units are **1/32 of a block**, not 1/16. Fix: a full-block shape is `32 × 32 × 32`, matching `Blocks/Structures/Base_Shapes/`.
- **`Failed to compute bounds for blockymodel: %s`** (WARN, `%s` is the asset name) → `BlockyModelBoundsParser` could not parse the file (malformed JSON, or a `size`/`normal` of the wrong JSON type). The model is not rejected, but anything relying on its bounds falls back to `null`.
