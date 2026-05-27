---
title: "Block Model Format (.blockymodel)"
description: "The Hytale .blockymodel format — build 3D models from a hierarchical node system of mesh shapes and child nodes, for non-cube blocks, furniture, items, and decorations."
seo:
  type: TechArticle
---

# Block Model Format (.blockymodel)

**Doc type:** JSON asset format · **Assets:** `Common` · **Verified against 0.5.1**

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
├── lod                "auto" | "off"
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
| Top-level fields | `.blockymodel` root | `nodes` array and optional `lod` mode |
| Node | `nodes[]` entry | `id`, `name`, `position`, `orientation`, optional `shape` and `children` |
| `box` shape | node `shape` | Cuboid mesh defined by `size` per dimension |
| `quad` shape | node `shape` | Flat 2D plane (foliage, flat decorations) |
| `none` shape | node `shape` | Transform-only node with no mesh |
| `textureLayout` | node `shape` | Per-face UV/texture layout |

## File Location

Block models are stored in various locations depending on their purpose:

| Category | Location |
|----------|----------|
| Block models | `Common/Blocks/Models/` |
| Character models | `Common/Characters/` |
| Item models | `Common/Items/` |
| NPC models | `Common/NPC/` |

Models are organized into subdirectories by category (e.g., `Doors/`, `Furniture/`, `Tools/`).

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
| `nodes` | array | Yes | Array of root-level node objects defining the model hierarchy |
| `lod` | string | No | Level-of-detail mode: `"auto"` or `"off"`. Default is `"auto"` |

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

### Position and Orientation

Position values are in pixels (16 pixels = 1 block unit). Orientation uses quaternion format where `{x: 0, y: 0, z: 0, w: 1}` represents no rotation.

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
  "unwrapMode": "standard",
  "textureLayout": {...}
}
```

Size values are in pixels (16 pixels = 1 block unit).

### Quad Shape

Flat 2D planes, commonly used for foliage and flat decorations:

```json
{
  "type": "quad",
  "offset": {"x": 0, "y": 0, "z": 0},
  "settings": {
    "size": {"x": 16, "y": 16},
    "normal": {"x": 0, "y": 0, "z": 1}
  },
  "doubleSided": true,
  "textureLayout": {...}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `settings.size` | object | Width and height in pixels `{x, y}` |
| `settings.normal` | object | Direction the quad faces `{x, y, z}` |

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

| Mode | Description |
|------|-------------|
| `"standard"` | Normal lighting and shading (default) |
| `"flat"` | Flat/unlit shading, no shadows |
| `"reflective"` | Reflective surface rendering |

### Unwrap Modes

| Mode | Description |
|------|-------------|
| `"standard"` | Default UV mapping based on shape dimensions |
| `"custom"` | Use explicit textureLayout for UV coordinates |

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

Quads have a single face:

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

A basic cube model:

```json
{
  "nodes": [
    {
      "id": "1",
      "name": "Cube",
      "shape": {
        "type": "box",
        "settings": {
          "size": {"x": 16, "y": 16, "z": 16}
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

A chest with a separate lid for animation:

```json
{
  "nodes": [
    {
      "id": "1",
      "name": "R-Attachment",
      "shape": {"type": "none"},
      "children": [
        {
          "id": "2",
          "name": "Base",
          "position": {"x": 0.0, "y": 0.0, "z": 0.0},
          "shape": {
            "type": "box",
            "offset": {"x": -7, "y": 0, "z": -7},
            "settings": {
              "size": {"x": 14, "y": 10, "z": 14}
            }
          }
        },
        {
          "id": "3",
          "name": "Lid",
          "position": {"x": 0.0, "y": 0.625, "z": -0.4375},
          "shape": {
            "type": "box",
            "offset": {"x": -7, "y": 0, "z": 0},
            "settings": {
              "size": {"x": 14, "y": 4, "z": 14}
            }
          }
        },
        {
          "id": "4",
          "name": "Latch",
          "position": {"x": 0.0, "y": 0.375, "z": 0.5},
          "shape": {
            "type": "box",
            "offset": {"x": -1, "y": 0, "z": 0},
            "settings": {
              "size": {"x": 2, "y": 4, "z": 1}
            }
          }
        }
      ]
    }
  ]
}
```

### Quad-Based Foliage Model

A simple grass or flower using crossed quads:

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
              "size": {"x": 16, "y": 16},
              "normal": {"x": 0, "y": 0, "z": 1}
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
              "size": {"x": 16, "y": 16},
              "normal": {"x": 0, "y": 0, "z": 1}
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

A door model with nodes named for animation compatibility:

```json
{
  "nodes": [
    {
      "id": "1",
      "name": "R-Attachment",
      "shape": {"type": "none"},
      "children": [
        {
          "id": "2",
          "name": "Frame",
          "shape": {
            "type": "box",
            "offset": {"x": -8, "y": 0, "z": -1.5},
            "settings": {
              "size": {"x": 16, "y": 32, "z": 3}
            }
          }
        },
        {
          "id": "3",
          "name": "Door",
          "position": {"x": -0.5, "y": 0.0, "z": 0.0},
          "shape": {
            "type": "box",
            "offset": {"x": 0, "y": 1, "z": -1},
            "settings": {
              "size": {"x": 13, "y": 30, "z": 2}
            }
          }
        }
      ]
    }
  ]
}
```

The corresponding `.blockyanim` file can reference the "Door" node to rotate it open:

```json
{
  "formatVersion": 1,
  "duration": 10,
  "holdLastKeyframe": true,
  "nodeAnimations": {
    "Door": {
      "orientation": [
        {"time": 0, "delta": {"x": 0, "y": 0, "z": 0, "w": 1}, "interpolationType": "smooth"},
        {"time": 10, "delta": {"x": 0, "y": 0.707, "z": 0, "w": 0.707}, "interpolationType": "smooth"}
      ]
    }
  }
}
```

## Integration with Blocks and Items

### Block Usage

Blocks reference models through `CustomModel` in their definition:

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Furniture/Chair_Wood.blockymodel",
    "CustomModelTexture": [
      {"Texture": "BlockTextures/Wood_Oak.png"}
    ],
    "CustomModelScale": 1.0
  }
}
```

### Item Usage

Items reference models through the `Model` field:

```json
{
  "Model": "Items/Weapons/Sword/Iron.blockymodel"
}
```

Model paths are relative to `Common/` and include the `.blockymodel` extension.

## Best Practices

1. **Use R-Attachment root nodes** - Name your root node "R-Attachment" for proper attachment point handling in the game engine

2. **Name nodes for animation** - Use clear, descriptive names that match what you'll reference in `.blockyanim` files

3. **Keep IDs unique** - Each node needs a unique `id` within the model for proper referencing

4. **Use hierarchy for animation** - Child nodes inherit parent transformations, making complex animations easier

5. **Consider LOD settings** - Use `"lod": "auto"` for most models; only disable with `"lod": "off"` if auto-LOD causes issues

6. **Units in pixels** - Both sizes and positions are in pixels (16 pixels = 1 block unit)

7. **Pivot placement** - Position offsets in shapes determine where the pivot point is - this affects how the shape rotates

8. **Use doubleSided for thin geometry** - Quads and thin boxes should usually have `"doubleSided": true` to be visible from both sides

9. **Match texture layouts to your texture atlas** - Coordinate the `textureLayout` offsets with your actual texture file layout

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 model loader (verified against `HytaleServer.jar`).

- **`You cannot set shape width to be less than or equal to zero. Width:`** / **`You cannot set shape height to be less than or equal to zero. Height:`** → a shape was given a non-positive dimension. Fix: every shape dimension must be `> 0`.
- **Symptom:** an animation does not move the part you expect → a `.blockyanim` references a node name that does not exist in this model. Fix: node names must match exactly between the `.blockymodel` and the `.blockyanim`.
- **Symptom:** the model is not picked up by the game → it is in the wrong folder. Fix: place models under the correct `Common/` location for their kind (`Blocks/Models/`, `Characters/`, `Items/`, `NPC/`).
- **Symptom:** thin geometry is invisible from one side → quads/thin boxes default to single-sided. Fix: set `"doubleSided": true`.
