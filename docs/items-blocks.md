---
title: "Block Items"
description: "Define Hytale block items in JSON — the BlockType property (Material, DrawType, Opacity, HitboxType, Flags), textures and custom models, gathering and drops, and light and particles."
seo:
  type: TechArticle
---

# Block Items

**Doc type:** JSON asset format · **Assets:** `Server/Item` · **Verified against 0.6.3**

> Part of the [Items API](items.md). For common item properties, see [Items Reference](items.md#common-properties).
>
> **See also:** [Drop System](drops.md) for `DropList` loot tables
>
> All structures and examples below are taken directly from real asset files under
> `Server/Item/Items/`. Counts cited are from the shipped assets: 2,952 item files carry a `BlockType` in 0.6.3.

This page documents the `BlockType` property an item carries to become a placeable block — rendering, collision, gathering, states, connections, interactions, and block-entity components.

## Overview

Defined as JSON assets under `Server/Item` (the `BlockType` property of item files) and covers:
- Core block properties: `Material`, `DrawType`, `Opacity`, `HitboxType`, `Flags`
- Textures and custom models for cube and model blocks
- `Gathering` (how a block is broken/harvested and what it drops)
- Light, particles, rotation, placement, and support rules
- Block `State` machines (On/Off, Open/Close, doors), connected-block rule sets, and farming/soil stages
- Block-entity components (`ItemContainerBlock`, `BenchBlock`, `ProcessingBenchBlock`, `FarmingBlock`, etc.) and block interactions

## Architecture
```
BlockType (item property)
├── Appearance & collision (Material, DrawType, Opacity, HitboxType, Flags)
├── Visuals (Textures, custom Models, ParticleColor, Light, Particles)
├── Gathering & Drops (→ drops.md DropList)
├── Placement (VariantRotation, PlacementSettings, Support)
├── State machine (On/Off, Open/Close, Doors)
├── Connected blocks (Stair, Roof, CustomTemplate rule sets)
├── Farming (SoilConfig, Stages)
└── BlockEntity.Components
    ├── ItemContainerBlock  (containers)
    ├── BenchBlock / ProcessingBenchBlock  (benches)
    └── FarmingBlock, RespawnBlock, TreasureChest, SpawnMarkerBlock, …
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `BlockType` | item property | Block config attached to an item to make it placeable |
| `Gathering` | `BlockType.Gathering` | Break/harvest rules and drop output |
| `State` | `BlockType.State` | Block state machine (On/Off, Open/Close, doors) |
| `BlockEntity.Components` | `BlockType.BlockEntity.Components` | Per-block entity component map |
| `ItemContainerBlock` | block-entity component | Storage container (e.g. chests); has `Capacity` |
| `BenchBlock` | block-entity component | Crafting bench block entity |
| `ProcessingBenchBlock` | block-entity component | Fuel/timed processing bench block entity |
| `FarmingBlock` | block-entity component | Farming/soil block entity |

## Quick Navigation

| Category | Examples | Key Features |
|----------|----------|--------------|
| [Basic Blocks](#basic-blocks) | Build_Grey_Cube, Soil_Dirt | `DrawType: Cube`, `Textures`, `Gathering` |
| [Furniture & Lighting](#furniture--lighting) | Deco_Lantern | `DrawType: Model`, `Light`, `State` On/Off |
| [Doors & Ladders](#doors--ladders) | Furniture_Temple_Wind_Door_Large, Ladders | `IsDoor`, `MovementSettings`, `ConnectedBlockRuleSet` |
| [Containers](#containers) | Furniture_Kweebec_Chest_Large | `BlockEntity` → `ItemContainerBlock` |
| [Benches](#benches) | Bench_Tannery | `BlockEntity` → `BenchBlock` / `ProcessingBenchBlock` |
| [Farming & Soil](#farming--soil) | Soil_Dirt_Tilled, Plant_Sapling_Camphor | `Farming.SoilConfig`, `Farming.Stages` |

---

## BlockType Properties

Items with placeable blocks define their block configuration in the `BlockType` property.
Many block items use `Parent` to inherit a template (e.g. `"Parent": "Template_Soil"`), so
a given file may only specify the fields it overrides.

### Core Properties

| Property | Type | Description |
|----------|------|-------------|
| `Material` | string | Collision: `Solid` or `Empty` |
| `DrawType` | string | Rendering: `Cube`, `Model`, `CubeWithModel`, or `Empty` |
| `Opacity` | string | Light/draw mode: `Solid`, `Transparent`, `Cutout`, `Semitransparent` |
| `HitboxType` | string | Named hitbox shape (see [HitboxType](#hitboxtype)) |
| `Group` | string | Internal grouping tag (e.g. `Dev`) |
| `Flags` | object | Item/block flags (see [Flags](#flags)) |
| `ParticleColor` | string | Hex tint for break/impact particles |
| `BlockSoundSetId` | string | Sound set for footsteps and impacts |
| `BlockParticleSetId` | string | Particle set for breaking effects |
| `CubeShadingMode` | string | Cube shading: `Standard`, `Flat`, `Fullbright`, `Reflective` |
| `Gathering` | object | How the block is broken/harvested and what it drops |
| `PhysicalMaterialId` | string | Physical material for hit/impact response (e.g. `Wood`, `Wool`, `Glass`, `Foliage`) |
| `TextureComputedColor` | string | Hex average colour of the block's texture (generated; present on most shipped blocks) |
| `ExplosionReactionState` | string | State to switch to when an explosion reaches the block (as of 0.6.3; only `Debug_Explosive` uses it, with `"Exploding"`) |

### Material

| Material | Description |
|----------|-------------|
| `Solid` | Full collision (most blocks) |
| `Empty` | No collision (plants, some furniture) |

```json
{ "BlockType": { "Material": "Solid" } }
```

### DrawType

| DrawType | Description |
|----------|-------------|
| `Cube` | Standard voxel cube using `Textures` |
| `Model` | Custom `.blockymodel` (most furniture, plants, doors) |
| `CubeWithModel` | A cube combined with a model overlay |
| `Empty` | Not rendered |
| `GizmoCube` | Editor gizmo cube (dev-only; no shipped block uses it) |

```json
{ "BlockType": { "DrawType": "Cube" } }
```

### Opacity

| Opacity | Description |
|---------|-------------|
| `Solid` | Fully opaque (blocks light) |
| `Transparent` | Drawn with transparency (models, glass) |
| `Cutout` | Alpha-tested cutout (foliage) |
| `Semitransparent` | Partial transparency |

### HitboxType

`HitboxType` (1,277 of the 2,952 shipped block items) selects a named, predefined collision/selection shape rather
than describing one inline. `Full` is the standard whole-block hitbox; the rest are
shape- or asset-specific names.

```json
{ "BlockType": { "HitboxType": "Full" } }
```

Common values include `Full`, `Block_Half`, `Block_Vertical_Flat`, `Stairs`, `Door`,
`Ladder`, `Window`, `Chest_Small`, `Chest_Large`, `Fence`, `Branch`, `Plant_Full`,
`Plant_Medium`, `Torch`, and many model-specific names (e.g. `Door_Temple_Wind_Large`).
244 hitbox assets ship under `Server/Item/Block/Hitboxes/`; `Full` is the exception with no
file of its own — it is `BlockBoundingBoxes.DEFAULT`, id `0`, and is also what a block that omits
`HitboxType` gets.

### Flags

`Flags` (1,285 blocks) is usually `{}` but may carry boolean behavior flags:

```json
{ "BlockType": { "Flags": { "IsStackable": false } } }
```

| Flag | Type | Description |
|------|------|-------------|
| `IsStackable` | boolean | Whether the builder tool's scatter may stack this block on a like block (default `true`; 73 blocks set it to `false`, 42 set it to `true` explicitly) |

`IsStackable` is the **only** key the `BlockFlags` codec accepts as of 0.6.3 (the
`IsUsable` flag was removed by 0.6.3 — whether a block responds to Use is decided solely
by `BlockType.Interactions.Use`, see [Block Interactions](#block-interactions)).

### ParticleColor

`ParticleColor` (2,725 blocks) is a hex string used to tint break/impact particles:

```json
{ "BlockType": { "ParticleColor": "#969696" } }
```

---

## Textures & Models

### Cube Textures

For `DrawType: Cube`, `Textures` is an **array** of texture entries. Each entry uses the
**face name as the key** (not a `"Face"`/`"Texture"` pair) plus a `Weight`. Multiple
entries provide weighted random variation per placed block.

```json
{
  "BlockType": {
    "DrawType": "Cube",
    "Textures": [
      {
        "Weight": 1,
        "Sides": "BlockTextures/Dev_Grey_Neutral_Side.png",
        "UpDown": "BlockTextures/Dev_Grey_Neutral_Top.png"
      }
    ]
  }
}
```

**Face keys** (only these appear inside `Textures` entries):

| Key | Description |
|-----|-------------|
| `Weight` | Selection weight when several entries are listed (not a face) |
| `All` | Apply one texture to every face |
| `Sides` | The four side faces |
| `UpDown` | Both top and bottom faces |
| `Up` | Top face (+Y) only |
| `Down` | Bottom face (-Y) only |
| `North` / `South` / `East` / `West` | Individual side faces (rare; debug blocks) |

> There is no `Top`, `Bottom`, or `Face`/`Texture` key. Use `UpDown` (or `Up`/`Down`)
> for vertical faces.

**Single texture (e.g. `Soil_Dirt`):**

```json
{ "BlockType": { "Textures": [ { "All": "BlockTextures/Soil_Dirt.png", "Weight": 1 } ] } }
```

**Distinct sides vs. top/bottom (`Soil_Dirt_Crystal`):**

```json
{
  "BlockType": {
    "Textures": [
      {
        "Sides": "BlockTextures/Soil_Dirt_Crystal_Side.png",
        "Weight": 1,
        "Up": "BlockTextures/Soil_Dirt_Crystal.png",
        "Down": "BlockTextures/Soil_Dirt_Crystal_Side.png"
      }
    ]
  }
}
```

Soil-type cube blocks may also define `TransitionTexture` for blending with neighbors.

### Custom Models

For `DrawType: Model`, a `.blockymodel` is referenced and textured via
`CustomModelTexture` (also an array of weighted entries, here keyed by `Texture`).

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Decorative_Sets/Village/Lantern.blockymodel",
    "CustomModelTexture": [
      { "Weight": 1, "Texture": "Blocks/Decorative_Sets/Village/Lantern_Texture.png" }
    ],
    "CustomModelScale": 0.8
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `CustomModel` | string | Path to `.blockymodel` file |
| `CustomModelTexture` | array | Weighted `{ "Weight", "Texture" }` entries |
| `CustomModelScale` | float | Model scale multiplier |
| `CustomModelAnimation` | string | `.blockyanim` to play (often set per state, see [Block States](#block-states)) |
| `CustomModelAnimationSpeed` | float | Playback-speed multiplier for `CustomModelAnimation` (`1` = authored speed; validated `0 ≤ x < 100`). Added as of 0.6.3; no shipped block sets it yet |

---

## Gathering & Drops

`Gathering` (2,311 blocks) defines how a block is broken/harvested and what it produces.
It groups by interaction mode; `Breaking` is the most common.

```json
{
  "BlockType": {
    "Gathering": {
      "Breaking": {
        "GatherType": "SoftBlocks",
        "DropList": "Rubble_Lime"
      }
    }
  }
}
```

| Sub-key | Description |
|---------|-------------|
| `Breaking` | Breaking with a tool/hand |
| `Soft` | Soft/instant gathering |
| `Harvest` | Harvesting (e.g. mature crops) |
| `Physics` | Physics-driven gathering |
| `Tools` | Tool-specific gathering rules |
| `UseDefaultDropWhenPlaced` | Use the default drop for placed instances |

Inside a gathering mode:

| Field | Description |
|-------|-------------|
| `GatherType` | Required gathering category (see below) |
| `ItemId` | Item produced directly |
| `DropList` | Drop table reference (string) or inline drop definition (object) — see [Drop System](drops.md) |
| `Quality` | Integer quality override on the produced item (`Breaking` only) |
| `IsWeaponBreakable` | `Soft` only — `false` stops weapons breaking the block (170 blocks, e.g. `Deco_Lantern`) |

**`GatherType` values:** `Rocks`, `Woods`, `SoftBlocks`, `Soils`, `VolcanicRocks`,
`Benches`, `SoftWoods`, `Unbreakable`, and ore tiers (`OreIron`, `OreGold`, `OreCopper`,
`OreSilver`, `OreThorium`, `OreCobalt`, `OreAdamantite`, `OreMithril`).

> Java side: `Breaking` / `Harvest` / `Soft` decode into `BlockBreakingDropType` /
> `HarvestingDropType` / `SoftBlockDropType` — see
> [Gathering Drop Types](blocks.md#gathering-drop-types).

`DropList` can be an inline object (used by chests to drop their item form):

```json
{
  "Gathering": {
    "Breaking": {
      "GatherType": "SoftBlocks",
      "DropList": {
        "Container": {
          "Type": "Single",
          "Item": { "ItemId": "Furniture_Kweebec_Chest_Small", "QuantityMin": 2, "QuantityMax": 2 }
        }
      }
    }
  }
}
```

---

## Light & Particles

### Light

Blocks may emit colored light. `Color` is a hex string; `Radius` controls range (a
`Radius` of `0` lets the configured falloff/state logic drive it).

```json
{ "BlockType": { "Light": { "Color": "#dca", "Radius": 0 } } }
```

A state may set `"Light": null` to turn emission off (see [Block States](#block-states)).

### Particles

`Particles` is an array of attached particle systems:

```json
{
  "BlockType": {
    "Particles": [
      { "SystemId": "Block_Gem_Sparks", "Color": "#ffce76", "TargetEntityPart": "Entity" }
    ]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `SystemId` | string | Particle system ID |
| `Scale` | float | Scale multiplier |
| `Color` | string | Tint color |
| `TargetNodeName` | string | Model node to attach to |
| `PositionOffset` | object | Offset from the node |
| `RotationOffset` | object | `{ "Pitch", "Yaw" }` rotation offset |
| `TargetEntityPart` | string | Entity part to attach to |
| `DetachedFromModel` | boolean | Whether the system is detached from the model |
| `ClearParticlesOnRemove` | boolean | Clear live particles when the block/state goes away |

---

## Rotation & Placement

### VariantRotation

Controls which rotation variants a block supports.

```json
{ "BlockType": { "VariantRotation": "NESW" } }
```

| VariantRotation | Description |
|-----------------|-------------|
| `None` | No rotation variants |
| `NESW` | Four horizontal facings |
| `UpDownNESW` | Horizontal facings plus up/down |
| `UpDown` | Vertical orientation only |
| `Wall` | Wall-mounted orientations |
| `Pipe` / `DoublePipe` | Pipe-style connections |
| `All` | All orientations |

### PlacementSettings

```json
{
  "BlockType": {
    "PlacementSettings": {
      "RotationMode": "StairFacingPlayer",
      "CeilingPlacementOverrideBlockId": "Deco_Lantern_Ceiling"
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `RotationMode` | string | `Default`, `FacingPlayer`, `BlockNormal`, or `StairFacingPlayer` (shipped blocks use only the last two: 127 `StairFacingPlayer`, 25 `BlockNormal`) |
| `PlaceInEmptyBlocks` | boolean | Allow placement into empty/air blocks |
| `AllowBreakReplace` | boolean | Allow replacing a breakable block on placement |
| `AllowRotationKey` | boolean | Allow the player to rotate while placing |
| `WallPlacementOverrideBlockId` | string | Block placed when targeting a wall |
| `CeilingPlacementOverrideBlockId` | string | Block placed on a ceiling |
| `FloorPlacementOverrideBlockId` | string | Block placed on a floor |
| `BlockPreviewVisibility` | string | `Default`, `AlwaysVisible`, or `AlwaysHidden` |

---

## Support System

Blocks can require support from neighboring blocks. `Support` maps direction names to
arrays of accepted support entries (any one entry satisfies that direction).

```json
{
  "BlockType": {
    "Support": {
      "Down": [
        { "FaceType": "Full" },
        { "FaceType": "Branch" },
        { "FaceType": "Fence" },
        { "BlockTypeId": "Deco_Iron_Chain_Small" }
      ],
      "Up": [ { "FaceType": "Full", "Filler": [] } ]
    }
  }
}
```

**Support directions:** any `BlockFace` name — the six faces (`Down`, `Up`, `North`, `South`,
`East`, `West`), the twelve edges (`DownNorth`, `UpEast`, `NorthWest`, …) and the eight corners
(`DownNorthEast`, `UpSouthWest`, …) — plus the six `MergedBlockFaces` groups, which expand to
several faces at once: `All`, `BlockSides`, `CardinalDirections` (the four sides), `Horizontal`,
`UpCardinalDirections`, `DownCardinalDirections`.

**Support entry forms:**

| Form | Description |
|------|-------------|
| `{ "FaceType": "Full" }` | Requires a face of the given type |
| `{ "FaceType": "Full", "Filler": [] }` | Face type plus optional filler shapes |
| `{ "BlockTypeId": "..." }` | Requires a specific block type as the supporter |
| `{ "TagId": "Family=Leaves" }` | Requires a supporter carrying the given item tag (fruit hanging from leaves) |

The sibling key `Supporting` uses the same direction map to declare which faces *this*
block offers to neighbours (e.g. a chest's `"Supporting": { "Up": [ { "FaceType": "Full" } ] }`).

**`FaceType` is a free-form string, not an enum** — codec doc: *"Can be any string. Compared with
FaceType in \"Supporting\" of other blocks. A LOT of blocks use 'Full'."* A custom block may invent
its own face type as long as the supporting block advertises the same string. The 17 used by shipped
blocks: `Full` (834 uses), `Branch` (168), `Rock_Beam` (76), `Shelf` (51), `Window` (46), `Wall`
(45), `Fence` (39), `Platform` (34), `Rope` (29), `Wood_Beam` (29), `Fence_Corner` (23),
`Wall_Corner` (23), `Bushes` (20), `Rail` (8), `Barrel` (6), `Vines` (3), `BushBase` (1).

A `Support` entry (`RequiredBlockFaceSupport`) accepts more than the four forms above — the full key
set is `FaceType`, `SelfFaceType`, `BlockSetId`, `BlockTypeId`, `FluidId`, `TagId`, `MatchSelf`,
`Support`, `AllowSupportPropagation`, `Rotate`, `Filler`. A `Supporting` entry (`BlockFaceSupport`)
accepts only `FaceType` and `Filler`.

A sibling `BlockType` key, `SupportsRequiredFor` (`"Any"` or `"All"`, default `All`),
controls whether one satisfied direction is enough or every declared direction must
hold — see [BlockSupportsRequiredForType](blocks.md#blocksupportsrequiredfortype).

---

## Block States

Blocks with multiple states declare them under `State.Definitions`. Each named definition
overrides specific fields (model animation, hitbox, light, particles, sounds, hints) for
that state. There is no `StateType`/`DefaultState`/`States` wrapper.

### On / Off (lights)

`Deco_Lantern`:

```json
{
  "BlockType": {
    "State": {
      "Definitions": {
        "On": {
          "AmbientSoundEventId": "SFX_Torch_Default_Loop"
        },
        "Off": {
          "InteractionHint": "server.interactionHints.turnon",
          "Light": null,
          "Particles": null,
          "InteractionSoundEventId": "SFX_Torch_Off",
          "AmbientSoundEventId": null,
          "CustomModelAnimation": "Blocks/Animations/Light/Light_Off.blockyanim"
        }
      }
    }
  }
}
```

### Open / Close (chests, windows)

Chest-style blocks use `OpenWindow` / `CloseWindow`:

```json
{
  "BlockType": {
    "State": {
      "Definitions": {
        "OpenWindow": {
          "InteractionSoundEventId": "SFX_Chest_Wooden_Open",
          "CustomModelAnimation": "Blocks/Animations/Chest/Chest_Open.blockyanim"
        },
        "CloseWindow": {
          "InteractionSoundEventId": "SFX_Chest_Wooden_Close",
          "CustomModelAnimation": "Blocks/Animations/Chest/Chest_Close.blockyanim"
        }
      }
    }
  }
}
```

### Doors and trapdoors

Doors use directional open/close states; a state may change the `HitboxType` while open:

```json
{
  "BlockType": {
    "State": {
      "Definitions": {
        "OpenDoorOut": {
          "SoundOcclusionOpacity": 0.0,
          "HitboxType": "Door_Temple_Wind_Large_Open",
          "CustomModelAnimation": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Open.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Temple_Light_Open",
          "InteractionHint": "server.interactionHints.closeDoor"
        },
        "CloseDoorOut": {
          "CustomModelAnimation": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Close.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Temple_Light_Close"
        }
      }
    }
  }
}
```

**Commonly used state names** in assets: `On`/`Off`, `OpenWindow`/`CloseWindow`,
`OpenDoorIn`/`CloseDoorIn`, `OpenDoorOut`/`CloseDoorOut`, `DoorBlocked`, connected-block
shape states (`Corner_Left`, `Corner_Right`, `Inverted_Corner_Left`,
`Inverted_Corner_Right`, `Straight`/`Block`, `Topper`, `T`, `Cross`), and crop stages
(`Stage1`…`StageFinal`).

---

## Connected Blocks

Blocks that connect to neighbors (stairs, roofs, walls/bars, doors) use
`ConnectedBlockRuleSet` (554 blocks). Its shape depends on `Type`.

### Stair

`Build_White_Stairs`:

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "Stair",
      "Straight": { "State": "default" },
      "Corner_Left": { "State": "Corner_Left" },
      "Corner_Right": { "State": "Corner_Right" },
      "Inverted_Corner_Left": { "State": "Inverted_Corner_Left" },
      "Inverted_Corner_Right": { "State": "Inverted_Corner_Right" }
    }
  }
}
```

### Roof

Roofs nest the shape states under `Regular`, name the material via `MaterialName`, and
add a `Topper`; some declare a `Width`:

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "Roof",
      "MaterialName": "Roof",
      "Regular": {
        "Straight": { "State": "default" },
        "Corner_Right": { "State": "Corner_Right" },
        "Corner_Left": { "State": "Corner_Left" },
        "Inverted_Corner_Right": { "State": "Inverted_Corner_Right" },
        "Inverted_Corner_Left": { "State": "Inverted_Corner_Left" }
      },
      "Topper": { "State": "Topper" }
    }
  }
}
```

A shallow roof variant: `{ "Type": "Roof", "Width": 2, "MaterialName": "Roof_Shallow" }`.

### CustomTemplate

Walls, bars, and doors reference an external template asset and map shape patterns to
block IDs (a `*` prefix references another block's state definitions):

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "CustomTemplate",
      "TemplateShapeAssetId": "WallConnectedBlockTemplate",
      "TemplateShapeBlockPatterns": {
        "Straight": "Deco_Iron_Bars",
        "Corner": "Deco_Iron_Bars_Corner",
        "T_Junction": "*Deco_Iron_Bars_State_Definitions_T",
        "Cross_Junction": "*Deco_Iron_Bars_State_Definitions_Cross"
      }
    }
  }
}
```

| Key | Description |
|-----|-------------|
| `Type` | `Stair` (~163 blocks), `Roof` (~241), or `CustomTemplate` (~135). A fourth type, `Patterned`, is registered as of 0.6.3 but no shipped block uses it — see [Patterned Connected Block Rule Sets](blocks.md#patterned-connected-block-rule-sets) |
| `Regular` / shape keys | Per-shape `{ "State": "<state name>" }` mappings |
| `MaterialName` | Material/group name (Roof) |
| `Topper` | Top-piece state (Roof) |
| `Width` | Optional width (Roof) |
| `TemplateShapeAssetId` | External template asset (CustomTemplate) |
| `TemplateShapeBlockPatterns` | Shape → block-ID/state-ref map (CustomTemplate) |

---

## Block Interactions

A block's primary use is configured via `BlockType.Interactions.Use`. It is either a
**named interaction reference** (a string) or an **inline interaction object**.

### Named Use references

```json
{ "BlockType": { "Interactions": { "Use": "Open_Container" } } }
```

| `Use` value | Behavior | Example |
|-------------|----------|---------|
| `Open_Container` | Open a container UI | Chests |
| `Open_Treasure_Container` | Open a treasure container | Treasure chests |
| `Door` | Toggle a door | Doors |
| `Door_Horizontal` | Toggle a horizontal door/trapdoor | Trapdoors |
| `Block_Seat` | Sit on the block | Chairs, stools |
| `Open_Processing_Bench` | Open a processing bench UI | Benches |

### Inline Use (ChangeState)

`Deco_Lantern` toggles its own state inline:

```json
{
  "BlockType": {
    "Interactions": {
      "Use": {
        "Interactions": [
          {
            "Type": "ChangeState",
            "Changes": { "default": "Off", "On": "Off", "Off": "On" }
          }
        ]
      }
    }
  }
}
```

`InteractionHint` (on the block or per state) supplies the localized prompt string, e.g.
`"server.interactionHints.openDoor"`.

> **Gotcha — `null` removes an inherited interaction.** `BlockType.Interactions` allows
> `null` values: a state (or a child template) that sets `"Use": null` drops the parent's
> `Use` entirely, so e.g. a one-shot switch can become inert once flipped. (Documented on
> the `Interactions` codec in `BlockType`.)

The top-level item also wires placement interactions in its own `Interactions` map:

```json
{ "Interactions": { "Primary": "Block_Primary", "Secondary": "Block_Secondary" } }
```

---

## Block Entity Components

Blocks with server-side state (containers, benches, farming soil, spawners, etc.) declare
it under `BlockType.BlockEntity.Components` (164 blocks).

```json
{
  "BlockType": {
    "BlockEntity": {
      "Components": {
        "ItemContainerBlock": { "Capacity": 36 }
      }
    }
  }
}
```

**Component types seen in assets:** `FarmingBlock`, `ItemContainerBlock`, `BenchBlock`,
`ProcessingBenchBlock`, `RespawnBlock`, `MusicEmitterBlock`, `TreasureChest`,
`SpawnMarkerBlock`, `BlockSpawner`, `PrefabSpawner`, `Teleporter`, `Portal`, `LaunchPad`,
`Coop`, `TilledSoil`, `TrackedPlacement`, `BlockMapMarker`, `InstanceConfig`. As of 0.6.3
the jar also registers `AugmentBlock` (`GrantsAugmentTags`, `Radius`, upgrade levels) —
a bench near an augment block collects its tags, which recipes can demand via
`BenchRequirement.RequiredAugmentTags` (see [Crafting](items-crafting.md#benchrequirement));
no shipped block declares it yet.

> Note: container capacity lives at
> `BlockType.BlockEntity.Components.ItemContainerBlock.Capacity` — not under a
> `container` component. The break drop (e.g. dropping the item form) is configured via
> `Gathering.Breaking.DropList`, not as a sibling of `Components`.

---

## Special Block Properties

### IsDoor

Marks a block as a door (46 blocks), used together with the `Door` Use interaction and
the directional door states:

```json
{ "BlockType": { "IsDoor": true } }
```

### MovementSettings (climbable)

Ladders and similar blocks set climb behavior under `MovementSettings`:

```json
{ "BlockType": { "MovementSettings": { "IsClimbable": true } } }
```

---

## Farming & Soil

There are two distinct `Farming` shapes in the assets.

### SoilConfig (tilled soil)

`Soil_Dirt_Tilled` defines a lifetime range (in ticks) and the block it reverts to:

```json
{
  "BlockType": {
    "Farming": {
      "SoilConfig": {
        "Lifetime": { "Min": 103680, "Max": 129600 },
        "TargetBlock": "Soil_Mud_Dry"
      }
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `Lifetime` | `{ "Min", "Max" }` lifetime range before reverting |
| `TargetBlock` | Block ID this soil becomes after its lifetime |

### Stages (growing plants/crops)

Growing plants list growth `Stages` keyed by stage set, a `StartingStageSet`, and the
modifiers that affect growth. Each stage entry has a `Type` (`BlockState` is the most
common in shipped crops, then `Prefab`, `BlockType`, and `Spread`), a `Duration` range, and
the block/prefab to display.

`Plant_Sapling_Camphor` (abridged):

```json
{
  "BlockType": {
    "Farming": {
      "StartingStageSet": "Default",
      "ActiveGrowthModifiers": ["Fertilizer", "Water", "LightLevel"],
      "Stages": {
        "Default": [
          {
            "Type": "BlockType",
            "Block": "Plant_Sapling_Camphor",
            "Duration": { "Min": 40000, "Max": 60000 }
          },
          {
            "Type": "Prefab",
            "Prefabs": [ { "Path": "Trees/Camphor/Stage_00/Camphor_Stage00_001.prefab.json", "Weight": 1 } ],
            "Duration": { "Min": 40000, "Max": 60000 },
            "ReplaceMaskTags": ["Soil"],
            "TolerateObstructionsBelowY": -1,
            "SoundEventId": "SFX_Crops_Grow"
          }
        ]
      }
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `StartingStageSet` | Which stage set to begin in |
| `Stages` | Stage-set name → ordered array of stage entries |
| `ActiveGrowthModifiers` | Modifiers that affect growth (`Fertilizer`, `Water`, `LightLevel`) |
| `StageSetAfterHarvest` | Stage set to switch to after harvesting |

Stage entry fields: `Type` (`BlockType`/`BlockState`/`Prefab`/`Spread`), `Block` or
`Prefabs[]`, `Duration { Min, Max }`, optional `ReplaceMaskTags`, `SoundEventId`, and (for
`Prefab` stages) `TolerateObstructionsBelowY`.

> Java side: stage entries decode into `FarmingStageData` subtypes (registered `Type`
> values: `BlockType`, `BlockState`, `Prefab`, `Spread`), and each id in
> `ActiveGrowthModifiers` names a `GrowthModifierAsset` under `Server/Farming/Modifiers/`
> — see [Farming Config Classes](blocks.md#farming-config-classes).

### HarvestCrop Interaction

**Package:** `com.hypixel.hytale.builtin.adventure.farming.interactions.HarvestCropInteraction` · registered by
`FarmingPlugin`

The interaction that reads the `Farming` config above. Codec doc: "Harvests the resources from
the target farmable block." Extends
[SimpleBlockInteraction](interactions.md#simpleblockinteraction), so it acts on the block the
client is targeting. It is the most-used of the farming interaction types — 25 shipped assets.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `RequireNotBroken` | boolean | `false` | Codec doc: "If true, the interaction will fail if the held item is broken (durability = 0)." |

Two shapes ship. A crop block harvests itself from its own `Use` chain, with no properties —
this is the bare-hand pick, and the 22 crop blocks all look like this (from
`Plant_Crop_Wheat_Block_Eternal.json`):

```json
{
  "InteractionHint": "server.interactionHints.harvest",
  "Interactions": {
    "Use": {
      "Interactions": [
        { "Type": "HarvestCrop" }
      ]
    }
  }
}
```

The sickle drives the same interaction from a swing's `HitBlock` branch, guarding on durability
and paying for the harvest with it (verbatim from
`Server/Item/Interactions/Weapons/Sickle/Attacks/Swing_Right/Sickle_Swing_Right_Selector.json`):

```json
{
  "Type": "HarvestCrop",
  "RequireNotBroken": true,
  "Next": {
    "Type": "ModifyInventory",
    "AdjustHeldItemDurability": -1
  },
  "Failed": "Block_Break_Adventure"
}
```

Behavior (from `com.hypixel.hytale.builtin.adventure.farming.FarmingUtil.harvest`, which the interaction delegates to):

- **Two prerequisites, both of which end the interaction `Failed`.** The target `BlockType` must
  declare `Gathering.Harvest` (a `HarvestingDropType` — see [drops.md](drops.md)), and the
  world's `WorldConfig.isBlockGatheringAllowed()` must be true. Neither produces a message; the
  chain simply takes its `Failed` branch, which is why the sickle supplies one.
- **Without a `StageSetAfterHarvest`** — including any block that is not farmable at all — the
  drops are given and **the block is removed** (set to empty). This is the path a one-shot
  gatherable takes.
- **With a `StageSetAfterHarvest`**, the drops are given and the block stays, switching to that
  stage set: its `FarmingBlock` component gets growth progress `0`, executions `0`, generation
  `+1`, and its last-tick time reset to now. A `FarmingBlock` component is created if the block
  did not already have one. This is the replant-in-place path that makes a crop re-grow.

> **Gotcha — the drops are paid before the stage config is validated, so a bad stage-set name
> costs items either way.** In the replant branch, `giveDrops` runs at `FarmingUtil.java:243`,
> *before* either stage-set lookup. Two different names can be wrong, and they fail differently:
>
> | Bad key | What happens | Cost |
> |---|---|---|
> | `StartingStageSet` not present in `Stages` | drops given, `return false` — **the block is never touched** (`:245-247`) | **repeatable**: the crop is still there and still harvestable, so the same block pays out again on every use |
> | `StageSetAfterHarvest` missing from `Stages` **or present but empty** | drops given, block set to `EMPTY`, `return false` (`:251-255`) | one-shot: the crop is destroyed |
>
> Both end the interaction `Failed`, so a `Failed` branch fires while the player keeps the loot.
> The first is the dangerous one — it is an item-duplication loop rather than a lost crop — and
> note the second triggers on an *empty* stage array too, not only a missing key. Neither is
> caught at load time: `Stages` keys are plain map entries with no cross-validation against
> `StartingStageSet` or `StageSetAfterHarvest`.

---

## Basic Blocks

Simple cube blocks for building.

### Build_Grey_Cube

**Location:** `Server/Item/Items/Build/Build_Grey/Build_Grey_Cube.json`

A standard textured cube.

```json
{
  "TranslationProperties": { "Name": "server.items.Build_Grey_Cube.name" },
  "ItemLevel": 10,
  "MaxStack": 100,
  "Icon": "Icons/ItemsGenerated/Build_Grey_Cube.png",
  "Categories": ["Tool.TechnicalBlocks"],
  "SubCategory": "BlockSets",
  "PlayerAnimationsId": "Block",
  "Set": "Build",
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Cube",
    "Group": "Dev",
    "HitboxType": "Full",
    "Flags": {},
    "Gathering": { "Breaking": { "GatherType": "Rocks" } },
    "BlockParticleSetId": "Dust",
    "Textures": [
      {
        "Weight": 1,
        "Sides": "BlockTextures/Dev_Grey_Neutral_Side.png",
        "UpDown": "BlockTextures/Dev_Grey_Neutral_Top.png"
      }
    ],
    "ParticleColor": "#969696",
    "BlockSoundSetId": "Soft",
    "PhysicalMaterialId": "Wool",
    "CubeShadingMode": "Standard",
    "TextureComputedColor": "#727272"
  },
  "Tags": { "Type": ["Soil"], "Family": ["Build"] },
  "Quality": "Technical",
  "ItemSoundSetId": "ISS_Blocks_Stone",
  "IconProperties": {
    "Scale": 0.58823,
    "Rotation": [22.5, 45, 22.5],
    "Translation": [0, -13.5]
  }
}
```

### Soil_Dirt (template child)

**Location:** `Server/Item/Items/Soil/Dirt/Soil_Dirt.json`

Inherits most of its block config from `Template_Soil` and only overrides texture and
particle color.

```json
{
  "TranslationProperties": { "Name": "server.items.Soil_Dirt.name" },
  "ItemLevel": 10,
  "Parent": "Template_Soil",
  "Icon": "Icons/ItemsGenerated/Soil_Dirt.png",
  "BlockType": {
    "Textures": [ { "All": "BlockTextures/Soil_Dirt.png", "Weight": 1 } ],
    "ParticleColor": "#98743b",
    "TransitionTexture": "BlockTextures/Transition_Soil_Dirt.png",
    "TextureComputedColor": "#88632B"
  },
  "Tags": {
    "Type": ["Soil"],
    "Family": ["Dirt"],
    "Spreadable": ["Grass"]
  }
}
```

---

## Furniture & Lighting

### Deco_Lantern

**Location:** `Server/Item/Items/Deco/Deco_Lantern.json`

A model block with light, an On/Off state toggled by an inline `ChangeState` use
interaction, and a long list of support options.

```json
{
  "TranslationProperties": { "Name": "server.items.Deco_Lantern.name" },
  "Icon": "Icons/ItemsGenerated/Deco_Lantern.png",
  "Categories": ["Blocks.Deco", "Furniture.Lighting", "Blocks.Deco"],
  "Recipe": {
    "Input": [
      { "ResourceTypeId": "Wood_Trunk", "Quantity": 2 },
      { "ItemId": "Furniture_Crude_Candle", "Quantity": 1 },
      { "ItemId": "Ingredient_Tree_Sap", "Quantity": 4 }
    ],
    "BenchRequirement": [
      { "Type": "Crafting", "Categories": ["Furniture_Lighting"], "Id": "Furniture_Bench" }
    ]
  },
  "BlockType": {
    "PlacementSettings": { "CeilingPlacementOverrideBlockId": "Deco_Lantern_Ceiling" },
    "Material": "Solid",
    "DrawType": "Model",
    "Opacity": "Transparent",
    "CustomModelTexture": [
      { "Weight": 1, "Texture": "Blocks/Decorative_Sets/Village/Lantern_Texture.png" }
    ],
    "HitboxType": "Plant_Full",
    "Light": { "Radius": 0, "Color": "#dca" },
    "Flags": {},
    "Gathering": { "Soft": { "IsWeaponBreakable": false } },
    "BlockParticleSetId": "Dust",
    "BlockSoundSetId": "Wood",
    "PhysicalMaterialId": "Wood",
    "Support": {
      "Down": [
        { "FaceType": "Full" },
        { "FaceType": "Full", "Filler": [] },
        { "FaceType": "Branch" },
        { "FaceType": "Rock_Beam" },
        { "FaceType": "Wood_Beam" },
        { "FaceType": "Fence" },
        { "FaceType": "Fence_Corner" },
        { "FaceType": "Wall" },
        { "FaceType": "Wall_Corner" },
        { "FaceType": "Rope" },
        { "BlockTypeId": "Deco_Iron_Chain_Small" },
        { "BlockTypeId": "Deco_Iron_Chains_Vertical" }
      ],
      "Up": [ { "FaceType": "Full", "Filler": [] }, { "FaceType": "Branch" }, { "FaceType": "Rope" } ]
    },
    "CustomModel": "Blocks/Decorative_Sets/Village/Lantern.blockymodel",
    "Interactions": {
      "Use": {
        "Interactions": [
          { "Type": "ChangeState", "Changes": { "default": "Off", "On": "Off", "Off": "On" } }
        ]
      }
    },
    "State": {
      "Definitions": {
        "On": { "AmbientSoundEventId": "SFX_Torch_Default_Loop" },
        "Off": {
          "InteractionHint": "server.interactionHints.turnon",
          "Light": null,
          "Particles": null,
          "InteractionSoundEventId": "SFX_Torch_Off",
          "AmbientSoundEventId": null,
          "CustomModelAnimation": "Blocks/Animations/Light/Light_Off.blockyanim"
        }
      }
    },
    "InteractionHint": "server.interactionHints.turnoff",
    "CustomModelScale": 0.8,
    "TextureComputedColor": "#673D25"
  },
  "PlayerAnimationsId": "Block",
  "Tags": { "Type": ["Deco"] },
  "ItemSoundSetId": "ISS_Blocks_Wood"
}
```

---

## Doors & Ladders

### Furniture_Temple_Wind_Door_Large

**Location:** `Server/Item/Items/Furniture/Temple_Wind/Unique/Furniture_Temple_Wind_Door_Large.json`

A door: `IsDoor: true`, the `Door` use interaction, directional door states (each open
state swaps in an open hitbox), and a `CustomTemplate` connected-block rule set.

```json
{
  "TranslationProperties": { "Name": "server.items.Furniture_Temple_Wind_Door_Large.name" },
  "PlayerAnimationsId": "Block",
  "Categories": ["Furniture.Doors"],
  "Set": "Furniture_Temple_Wind",
  "Interactions": { "Primary": "Block_Primary", "Secondary": "Block_Secondary" },
  "BlockType": {
    "BlockParticleSetId": "Stone",
    "CustomModel": "Blocks/Decorative_Sets/Temple_Wind/Door_Large.blockymodel",
    "CustomModelTexture": [ { "Texture": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Texture.png" } ],
    "DrawType": "Model",
    "Gathering": { "Breaking": { "GatherType": "Rocks" } },
    "Material": "Solid",
    "State": {
      "Definitions": {
        "CloseDoorIn":  { "CustomModelAnimation": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Close.blockyanim", "InteractionSoundEventId": "SFX_Door_Temple_Light_Close" },
        "CloseDoorOut": { "CustomModelAnimation": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Close.blockyanim", "InteractionSoundEventId": "SFX_Door_Temple_Light_Close" },
        "OpenDoorIn":   { "SoundOcclusionOpacity": 0.0, "HitboxType": "Door_Temple_Wind_Large_Open", "CustomModelAnimation": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Open.blockyanim", "InteractionSoundEventId": "SFX_Door_Temple_Light_Open", "InteractionHint": "server.interactionHints.closeDoor" },
        "OpenDoorOut":  { "SoundOcclusionOpacity": 0.0, "HitboxType": "Door_Temple_Wind_Large_Open", "CustomModelAnimation": "Blocks/Decorative_Sets/Temple_Wind/Door_Large_Open.blockyanim", "InteractionSoundEventId": "SFX_Door_Temple_Light_Open", "InteractionHint": "server.interactionHints.closeDoor" }
      }
    },
    "VariantRotation": "NESW",
    "HitboxType": "Door_Temple_Wind_Large",
    "BlockSoundSetId": "Stone",
    "InteractionHint": "server.interactionHints.openDoor",
    "IsDoor": true,
    "Interactions": { "Use": "Door" },
    "ParticleColor": "#cca159",
    "ConnectedBlockRuleSet": {
      "Type": "CustomTemplate",
      "TemplateShapeAssetId": "DoorConnectedBlockTemplate",
      "TemplateShapeBlockPatterns": { "Default": "Furniture_Temple_Wind_Door_Large" }
    }
  },
  "Icon": "Icons/ItemsGenerated/Furniture_Temple_Wind_Door_Large.png",
  "Tags": { "Type": ["Furniture"], "Family": ["Temple"] },
  "ItemSoundSetId": "ISS_Blocks_Stone"
}
```

### Ladders

**Example:** `Server/Item/Items/Furniture/Desert/Furniture_Desert_Ladder.json`

Ladders use a `Ladder` hitbox and `MovementSettings.IsClimbable`:

```json
{
  "BlockType": {
    "HitboxType": "Ladder",
    "MovementSettings": { "IsClimbable": true }
  }
}
```

---

## Containers

### Furniture_Kweebec_Chest_Large

**Location:** `Server/Item/Items/Container/Furniture_Kweebec_Chest_Large.json`

A container: `ItemContainerBlock` capacity, `Open_Container` use, open/close window
states, and a `DropList` (under `Gathering.Breaking`) that drops two small chests when
broken (abridged — model, texture, support and sound keys omitted).

```json
{
  "Categories": ["Furniture.Containers"],
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Model",
    "HitboxType": "Chest_Large",
    "VariantRotation": "NESW",
    "Interactions": { "Use": "Open_Container" },
    "BlockEntity": {
      "Components": { "ItemContainerBlock": { "Capacity": 36 } }
    },
    "State": {
      "Definitions": {
        "OpenWindow":  { "InteractionSoundEventId": "SFX_Chest_Wooden_Open",  "CustomModelAnimation": "Blocks/Animations/Chest/Chest_Open.blockyanim" },
        "CloseWindow": { "InteractionSoundEventId": "SFX_Chest_Wooden_Close", "CustomModelAnimation": "Blocks/Animations/Chest/Chest_Close.blockyanim" }
      }
    },
    "Gathering": {
      "Breaking": {
        "GatherType": "Woods",
        "DropList": {
          "Container": {
            "Type": "Single",
            "Item": { "ItemId": "Furniture_Kweebec_Chest_Small", "QuantityMin": 2, "QuantityMax": 2 }
          }
        }
      }
    },
    "Supporting": { "Up": [ { "FaceType": "Full" } ] },
    "Support": { "Down": [ { "FaceType": "Full" } ] }
  }
}
```

Treasure chests add a `TreasureChest` component and use the `Open_Treasure_Container`
interaction:

```json
{
  "BlockType": {
    "BlockEntity": {
      "Components": { "ItemContainerBlock": { "Capacity": 36 }, "TreasureChest": {} }
    }
  }
}
```

---

## Benches

### Bench_Tannery

**Location:** `Server/Item/Items/Bench/Bench_Tannery.json`

Processing benches combine the `Open_Processing_Bench` use with `BenchBlock` /
`ProcessingBenchBlock` components.

```json
{
  "BlockType": {
    "Interactions": { "Use": "Open_Processing_Bench" },
    "BlockEntity": {
      "Components": {
        "BenchBlock": {},
        "ProcessingBenchBlock": {}
      }
    }
  }
}
```

Recipes themselves live on the crafted items (`Recipe.BenchRequirement`), but the bench
definition — tier levels, upgrade costs, categories — is carried inline by the bench
item's `BlockType.Bench` object (e.g. `Bench_Weapon.json` defines `Type`, `Id`, and
`TierLevels` there). See [Bench Configuration](blocks.md#bench-configuration) for the
`Type` variants (`Crafting`, `Processing`, `DiagramCrafting`, `StructuralCrafting`) and
the tier/upgrade keys.

---

## Block Item Patterns

### Custom solid cube block

```json
{
  "TranslationProperties": { "Name": "server.items.My_Custom_Block.name" },
  "MaxStack": 100,
  "Icon": "Icons/ItemsGenerated/My_Custom_Block.png",
  "Categories": ["Blocks.Rocks"],
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Cube",
    "HitboxType": "Full",
    "Flags": {},
    "Gathering": { "Breaking": { "GatherType": "Rocks", "ItemId": "My_Custom_Block" } },
    "Textures": [ { "All": "BlockTextures/My_Custom_Block.png", "Weight": 1 } ],
    "ParticleColor": "#888888",
    "BlockParticleSetId": "Stone",
    "BlockSoundSetId": "Stone",
    "CubeShadingMode": "Standard"
  }
}
```

### Toggleable model light

```json
{
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Model",
    "CustomModel": "Blocks/My_Lamp.blockymodel",
    "Light": { "Color": "#ffffff", "Radius": 0 },
    "Support": { "Down": [ { "FaceType": "Full" } ] },
    "Interactions": {
      "Use": {
        "Interactions": [
          { "Type": "ChangeState", "Changes": { "default": "Off", "On": "Off", "Off": "On" } }
        ]
      }
    },
    "State": {
      "Definitions": {
        "On": { "AmbientSoundEventId": "SFX_Torch_Default_Loop" },
        "Off": { "Light": null, "InteractionHint": "server.interactionHints.turnon" }
      }
    }
  }
}
```

### Interactive container

```json
{
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Model",
    "CustomModel": "Blocks/My_Box.blockymodel",
    "HitboxType": "Chest_Small",
    "Interactions": { "Use": "Open_Container" },
    "BlockEntity": {
      "Components": { "ItemContainerBlock": { "Capacity": 27 } }
    }
  }
}
```

---

## Block_Secondary Interaction

**Location:** `Server/Item/Interactions/Block_Secondary.json`

The interaction referenced by an item's `Secondary` slot. It attempts to use the targeted
block first, and on failure falls back to placing the held block. As of 0.6.3 the fallback
is no longer a bare `PlaceBlock`: it is a `PlaceModeSelect` that dispatches to one
interaction chain per placement mode (drag-place by default; replace/retype/extrude/
surface-draw in Creative):

```json
{
  "Type": "UseBlock",
  "Failed": {
    "Type": "PlaceModeSelect",
    "DefaultInteractions": "Place_Drag",
    "ReplaceInteractions": "Creative_Place_Replace",
    "RetypeInteractions": "Creative_Place_Retype",
    "ExtrudeInteractions": "Creative_Place_Extrude",
    "SurfaceDrawInteractions": "Creative_Place_SurfaceDraw",
    "FastPlaceInteractions": "Place_Drag"
  }
}
```

`PlaceModeSelect` accepts exactly those six keys (`DefaultInteractions`,
`ReplaceInteractions`, `RetypeInteractions`, `ExtrudeInteractions`,
`SurfaceDrawInteractions`, `FastPlaceInteractions`), each naming an interaction. The default
chain, `Server/Item/Interactions/Place_Drag.json`, is a `DragPlaceBlock` (`MaxBlocksPerTick`
4, `MaxBlocksPerGesture` 512) that forks to `Place_Single` — the single-block placement
lives there rather than in `Block_Secondary` itself.

A matching root interaction (`Server/Item/RootInteractions/Block_Secondary.json`) wraps it
with a cooldown (`BlockInteraction`, 0.278 s, `ClickBypass`) and creative settings
(`AllowSkipChainOnClick`) and references the interaction by name.

---

## Gotchas & Errors

Backtick-quoted strings below are literal messages from `HytaleServer.jar`.

- **`Block type not found`** (`TeleportConfigInstanceInteraction`) → a `BlockType` key referenced for placement/lookup does not resolve to a loaded block. Fix: confirm the owning item loaded and the key matches the item's id exactly (case-sensitive).
- **`does not have an associated item!`** (`BenchWindow`) → a block type exists but no item carries it, so it cannot be obtained or placed. Fix: define the `BlockType` inside an item file rather than as a standalone block — `BlockType.CODEC`'s own documentation says *"The definition for a block in the game. Can only be defined within an **Item** and not standalone."*
- **`itemId cannot be BlockTypeKey.EMPTY!`** → an item/block operation was handed the empty block-type key. Fix: pass a real block-bearing item id, not an empty/placeholder key.
- **Symptom:** a placeable block fails to register even though the JSON parses → the `BlockType` block was placed in a standalone block file instead of under an item's `BlockType` property. Fix: nest `BlockType` inside the item definition under `Server/Item/Items/`.

---

## Related Documentation

- [Items Reference](items.md) - Common properties and systems
- [Blocks API](blocks.md) - BlockType class and events
- [Drop System](drops.md) - `DropList` loot tables for blocks and containers
- [Interactions API](interactions.md) - Block interactions
- [Entity & World Interactions](interactions-world.md) - PlaceBlock, BreakBlock
- [Tools Reference](items-tools.md) - Block-breaking tools
