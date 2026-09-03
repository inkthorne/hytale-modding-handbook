---
title: "Block Definitions"
description: "Define Hytale blocks — visual assets (.blockymodel models, .blockyanim animations) in Common/Blocks and JSON game logic in Server/Item with properties, interactions, and behavior."
seo:
  type: TechArticle
---

# Block Definitions

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item` · **Verified against 0.5.9**

Block definitions configure every placeable block in Hytale, from terrain and ores to furniture, doors, and fluids. Blocks are defined as items with a `BlockType` property that specifies rendering, collision, sounds, particles, and interaction behavior.

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Items](items.md) | `items.md` | Parent item system and inheritance |
| [Block Items](items-blocks.md) | `items-blocks.md` | Furniture, containers, crafting benches |
| [Interactions](interactions.md) | `interactions.md` | Block use and break interactions |
| [Components](components.md) | `components.md` | BlockEntity components |
| [Events](events.md) | `events.md` | Block-related events |

---

## Overview

### Architecture

Hytale separates block visual assets from game logic:

- **Visual Assets** (`Common/Blocks/`): 3D models (`.blockymodel`) and animations (`.blockyanim`)
- **Game Logic** (`Server/Item/`): JSON definitions with properties, interactions, and behavior

### File Locations

| Location | Content |
|----------|---------|
| `Server/Item/Items/<Category>/` | Block item definitions (~2,950 item files carry a `BlockType` in 0.6.3) |
| `Server/Item/Block/Fluids/` | Fluid block definitions (14 files) |
| `Server/Item/Block/Hitboxes/<Category>/` | Collision shape definitions |
| `Server/Item/Block/Sounds/` | Sound set mappings (57 files) |
| `Server/Item/Block/Particles/` | Particle set mappings (30 files) |
| `Server/Item/Block/BreakingDecals/` | Breaking texture effects |
| `Server/Item/Block/FluidFX/` | Fluid visual effects |
| `Server/Item/Block/PhysicalMaterials/` | Physical materials referenced by `BlockType.PhysicalMaterialId` (11 files) |
| `Server/Item/Block/Sets/` | Block sets (`BlockSet` assets, 58 files) |
| `Server/Item/Block/Spawners/` | Block-spawner configs (46 files) |
| `Server/Item/CustomConnectedBlockTemplates/` | Connected block rules (11 templates) |
| `Server/BlockTypeList/` | Block categorization lists (13 files) |
| `Common/Blocks/` | Visual models and animations (~2,600 files) |

### Block Categories

Blocks are organized into categories for the Creative Library:

| Category | Examples (shipped usage in 0.6.3) |
|----------|----------|
| `Blocks.Wood` | Planks, logs, bark (315 items) |
| `Blocks.Plants` | Flowers, crops, leaves (217) |
| `Blocks.Rocks` | Stone, sandstone, marble (190) |
| `Blocks.Deco` | Furniture, containers, doors, lighting (173) |
| `Blocks.Soils` | Dirt, grass, sand, gravel (138) |
| `Blocks.Cloth` | Wool, fabric blocks (119) |
| `Blocks.Metal` | Metal blocks (100) |
| `Blocks.Ores` | Ore blocks (76) |
| `Blocks.Portals` / `Blocks.Fluids` | Portal blocks (18) / fluid blocks (9) |

(There are no `Blocks.Furniture` / `Blocks.Containers` / `Blocks.Lighting` categories — those blocks live under `Blocks.Deco`.)

---

## Architecture
```
Block definition (JSON item with a BlockType)
├── BlockType (rendering, material, opacity, light)
│   ├── Textures (per-face / weighted variants)
│   ├── CustomModel (.blockymodel) + CustomModelAnimation (.blockyanim)
│   ├── HitboxType (collision shape)
│   ├── State (multi-state models, e.g. doors/containers)
│   ├── ConnectedBlockRuleSet (neighbor-aware connected blocks)
│   ├── Gathering (tool + drop list)
│   └── Interactions (Primary / Use / Collision)
├── Sound sets (Server/Item/Block/Sounds)
├── Particle sets (Server/Item/Block/Particles)
├── Fluid blocks (MaxFluidLevel, FluidFXId, Ticker)
└── Block type lists (Server/BlockTypeList — categorization)

Java runtime
├── BlockType (config accessors)
├── BlockMaterial / Rotation / RotationTuple (placement)
├── World / WorldChunk (block read/write)
└── Block events (Place / Break / Damage / UseBlock — ECS)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `BlockType` | `server.core.asset.type.blocktype.config` | Core block-type configuration; all block properties |
| `BlockMaterial` | `protocol` | Enum of physical material type (Empty / Solid) |
| `Rotation` | `server.core.asset.type.blocktype.config` | Enum of 90-degree rotation increments |
| `RotationTuple` | `server.core.asset.type.blocktype.config` | Record of yaw/pitch/roll; used for placement rotation |
| `WorldChunk` | `server.core.universe.world.chunk` | Block read/write access (see [world.md](world.md#worldchunk)) |
| `PlaceBlockEvent` | `server.core.event.events.ecs` | ECS event fired when a block is placed (cancellable) |
| `BreakBlockEvent` | `server.core.event.events.ecs` | ECS event fired when a block is broken (cancellable) |
| `DamageBlockEvent` | `server.core.event.events.ecs` | ECS event fired during mining progress (cancellable) |
| `UseBlockEvent` | `server.core.event.events.ecs` | ECS event for block use; `Pre` (cancellable) / `Post` |
| `BlockBoundingBoxes` | `server.core.asset.type.blockhitbox` | Hitbox asset (`Server/Item/Block/Hitboxes`); see [BlockBoundingBoxes](#blockboundingboxes) |
| `BlockTickManager` | `server.core.asset.type.blocktick` | Static holder for the block-tick provider; see [Block Ticking](#block-ticking) |
| `BlockTypeModule` | `server.core.blocktype` | Core `JavaPlugin` module behind block types: registers the `Bench` codec variants and the block-physics component; `BlockTypeModule.get()` |
| `BlockSetModule` | `server.core.modules.blockset` | Core `JavaPlugin` module resolving named `BlockSet` assets to block-id sets (`blockInSet`, `getBlockSets`); deprecated for removal in 0.5.7 |

---

## Common Properties

All block items support standard item properties plus `BlockType`:

| Property | Type | Description |
|----------|------|-------------|
| `Parent` | string | Template to inherit from |
| `TranslationProperties` | object | Localization keys |
| `Categories` | array | Creative Library categories |
| `Set` | string | Block family grouping (e.g., `"Rock_Aqua"`) |
| `Tags` | object | Type and Family classification tags |
| `Icon` | string | Path to inventory icon |
| `Recipe` | object | Crafting requirements |
| `ResourceTypes` | array | Resource type memberships |
| `MaxStack` | int | Inventory stack limit (shipped rock blocks use `100`) |
| `ItemSoundSetId` | string | Sound effects when handling item |
| `PlayerAnimationsId` | string | Player animation when placing |
| `BlockType` | object | Block-specific configuration |

### Example: Simple Block Item

```json
{
  "TranslationProperties": {
    "Name": "server.items.Rock_Stone.name"
  },
  "ItemLevel": 10,
  "MaxStack": 100,
  "Icon": "Icons/ItemsGenerated/Rock_Stone.png",
  "Categories": ["Blocks.Rocks"],
  "PlayerAnimationsId": "Block",
  "Set": "Rock_Stone",
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Cube",
    "Group": "Stone",
    "Flags": {},
    "Gathering": {
      "Breaking": {
        "GatherType": "Rocks",
        "ItemId": "Rock_Stone_Cobble"
      }
    },
    "BlockParticleSetId": "Stone",
    "Textures": [
      { "All": "BlockTextures/Rock_Stone.png", "Weight": 2 },
      { "All": "BlockTextures/Rock_Stone_2.png", "Weight": 1 },
      { "All": "BlockTextures/Rock_Stone_3.png", "Weight": 1 }
    ],
    "ParticleColor": "#737055",
    "BlockSoundSetId": "Stone",
    "PhysicalMaterialId": "Stone",
    "BlockBreakingDecalId": "Breaking_Decals_Rock"
  },
  "ResourceTypes": [ { "Id": "Rock" }, { "Id": "Rock_Stone" } ],
  "Tags": { "Type": ["Rock"] },
  "ItemSoundSetId": "ISS_Blocks_Stone"
}
```
*(abridged from `Server/Item/Items/Rock/Stone/Rock_Stone.json` — `Opacity` is omitted because `Solid` is the default; the real file also carries `Aliases` and `TextureComputedColor`)*

---

## BlockType Properties

The `BlockType` object defines how a block renders, collides, and behaves in the world.

### Rendering Properties

| Property | Type | Description |
|----------|------|-------------|
| `DrawType` | string | Rendering mode: `"Cube"`, `"Model"`, `"CubeWithModel"`, `"Empty"` (invisible), `"GizmoCube"` |
| `Material` | string | Physical type: `"Solid"`, `"Empty"` |
| `Opacity` | string | Visual transparency: `"Solid"`, `"Transparent"`, `"Semitransparent"`, `"Cutout"` |
| `Group` | string | Block family for texture blending |
| `Textures` | array | Texture definitions with variants |
| `CustomModel` | string | Path to `.blockymodel` file |
| `CustomModelTexture` | array | Texture assignments for model (`{ "Texture", "Weight" }`) |
| `CustomModelAnimation` | string | Path to `.blockyanim` file |
| `CustomModelAnimationSpeed` | float | 0.6.3+: playback-speed multiplier for the model animation (1 = authored speed; must be ≥ 0 and < 100 — `BlockType.MAX_CUSTOM_MODEL_ANIMATION_SPEED`) |
| `CustomModelScale` | float | Scale multiplier for model |
| `Light` | object | Light emission: `Color` (hex string) + `Radius` |
| `PhysicalMaterialId` | string | Physical material (`Server/Item/Block/PhysicalMaterials/<id>.json`) |

### Texture Configuration

Textures support per-face assignment and weighted random variants:

```json
{
  "Textures": [
    {
      "Weight": 3,
      "All": "BlockTextures/Rock_Stone.png"
    },
    {
      "Weight": 1,
      "All": "BlockTextures/Rock_Stone_Moss.png"
    }
  ]
}
```

**Per-face textures:**

```json
{
  "Textures": [
    {
      "Weight": 1,
      "Up": "BlockTextures/Grass_Top.png",
      "Down": "BlockTextures/Dirt.png",
      "Sides": "BlockTextures/Grass_Side.png"
    }
  ]
}
```

| Face Property | Description |
|---------------|-------------|
| `All` | Apply to all faces |
| `Up` | Top face (+Y) |
| `Down` | Bottom face (-Y) |
| `UpDown` | Both top and bottom |
| `Sides` | All four side faces |
| `North`, `South`, `East`, `West` | Individual side faces |
| `Weight` | Relative weight of this variant (int) |

(Keys are those of `BlockTypeTextures.CODEC` — there are no `Top` / `Bottom` / `Side` keys.)

### Light Emission

Blocks can emit colored light:

```json
{
  "Light": {
    "Color": "#015",
    "Radius": 1
  }
}
```

`Light` decodes through `ProtocolCodecs.COLOR_LIGHT`: `Color` is a hex string (`"#RGB"` or `"#RRGGBB"`) and `Radius` an int; there is no `Intensity` key. Shipped fluids and lamps set only `Color` (e.g. `"Light": { "Color": "#765" }`).

### Collision Properties

| Property | Type | Description |
|----------|------|-------------|
| `HitboxType` | string | Reference to hitbox definition (file basename under `Server/Item/Block/Hitboxes/`) |
| `Support` | object | Required support, keyed by face (`Up`/`Down`/`North`/`South`/`East`/`West`) → array of `RequiredBlockFaceSupport` entries, e.g. `"Support": { "Down": [ { "FaceType": "Full" } ] }` |
| `Supporting` | object | Which faces this block offers as support to neighbors, same face-keyed shape (e.g. `{ "Up": [ { "FaceType": "Full" } ] }`) |
| `SupportsRequiredFor` | string | `"Any"` / `"All"` — see [BlockSupportsRequiredForType](#blocksupportsrequiredfortype) |
| `MaxSupportDistance` | int | 0–14 |
| `IgnoreSupportWhenPlaced` | boolean | Skip the support check at placement time |

`Support` is not a string — the full rule shape (`FaceType`, `BlockTypeId`, `TagId`, `BlockSetId`, `FluidId`, `MatchSelf`, `Rotate`, …) is documented in [Support System](items-blocks.md#support-system).

### Behavior Properties

| Property | Type | Description |
|----------|------|-------------|
| `Gathering` | object | Tool type and drop configuration |
| `VariantRotation` | string | Rotation support — see [VariantRotation](#variantrotation) |
| `Flags` | object | Boolean flags (only `IsStackable` as of 0.6.3 — see [Flags](#flags)) |
| `Interactions` | object | Primary, Use, Collision, OnBreak, … handlers |
| `State` | object | State definitions (`Definitions` map) |
| `IsDoor` | boolean | Marks a door block (`BlockType.isDoor()`; shipped doors set it) |
| `TickProcedure` / `RandomTickProcedure` | object | Scheduled / random ticking — see [Block Ticking](#block-ticking). (There is no `Ticker` key on a `BlockType`; `Ticker` belongs to fluid blocks.) |

### Gathering Configuration

Defines what tool breaks the block and what it drops:

```json
{
  "Gathering": {
    "Breaking": {
      "GatherType": "Rocks",
      "ItemId": "Rock_Stone_Cobble"
    }
  }
}
```

`Breaking` either names a direct drop (`ItemId` + optional `Quantity` / `Quality`) or references a drop table by id — `"DropList": "Iron_Stack"` (a **string**, resolved against [drop tables](drops.md); `Deco_Iron_Stack.json` does this). `DropList` is not an inline array.

`GatherType` values used by shipped blocks (0.6.3): `Rocks`, `Woods`, `Soils`, `SoftBlocks`, `VolcanicRocks`, `Benches`, `OreCopper` / `OreIron` / `OreSilver` / `OreGold` / `OreCobalt` / `OreThorium` / `OreMithril` / `OreAdamantite`, `Unbreakable`, `SoftWoods`. The string is matched against the tool's gathering capabilities (see [Items](items.md)); it is not an enum.

### VariantRotation

Enables directional placement based on player facing:

```json
{
  "VariantRotation": "NESW"
}
```

| Value | Description |
|-------|-------------|
| `"None"` | No placement rotation |
| `"NESW"` | 4 cardinal directions (North, East, South, West) — the common case (487 shipped items) |
| `"UpDownNESW"` | Cardinal directions plus up/down facing (236) |
| `"Wall"` | Wall-mounted orientation (75) |
| `"UpDown"` | Vertical axis only (44) |
| `"Pipe"` / `"DoublePipe"` | Axis-aligned pipe orientations (58 / 128) |
| `"All"` | Every rotation (1) |

(The `VariantRotation` enum; counts are shipped 0.6.3 usage.)

### Flags

```json
{
  "Flags": {
    "IsStackable": true
  }
}
```

| Flag | Description |
|------|-------------|
| `IsStackable` | Builder-tool scatter may stack this block on top of a like block (`BlockFlags.isStackable`) |

`IsUsable` was removed by 0.6.3 (the `BlockFlags` codec now has only `IsStackable`, and the client packet no longer carries flags). A block is "usable" simply by having a `Use` interaction — shipped doors and chests set `"Flags": {}` and `"Interactions": { "Use": ... }`.

---

## Block States System

Blocks can have multiple states with different models, hitboxes, and animations.

### State Definition Structure

```json
{
  "State": {
    "Id": "container",
    "Capacity": 36,
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
```

| Property | Type | Description |
|----------|------|-------------|
| `Id` | string | State machine identifier |
| `Capacity` | int | Container slot count (for containers) |
| `Definitions` | object | Map of state names to configurations |

### State Definition Properties

| Property | Type | Description |
|----------|------|-------------|
| `CustomModel` | string | Model for this state |
| `CustomModelAnimation` | string | Animation to play |
| `HitboxType` | string | Collision shape for this state |
| `InteractionSoundEventId` | string | Sound when entering state |
| `FlipType` | string | Model transformation |

### Example: Door with Multiple States

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Doors/Door_Wood.blockymodel",
    "HitboxType": "Door",
    "VariantRotation": "NESW",
    "State": {
      "Id": "door",
      "Definitions": {
        "OpenDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_In.blockyanim",
          "HitboxType": "Door_Open_In",
          "InteractionSoundEventId": "SFX_Door_Wooden_Open"
        },
        "OpenDoorOut": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_Out.blockyanim",
          "HitboxType": "Door_Open_Out",
          "InteractionSoundEventId": "SFX_Door_Wooden_Open"
        },
        "CloseDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_In.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Wooden_Close"
        },
        "CloseDoorOut": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_Out.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Wooden_Close"
        }
      }
    },
    "Interactions": {
      "Use": "Door_Toggle"
    }
  }
}
```

### Roof/Corner State Example

Blocks with connected states use shape-based state selection:

```json
{
  "State": {
    "Id": "roof",
    "Definitions": {
      "Corner_Right": {
        "CustomModel": "Blocks/Roof/Roof_Corner_Right.blockymodel",
        "HitboxType": "Roof_Corner",
        "FlipType": "MirrorX"
      },
      "Corner_Left": {
        "CustomModel": "Blocks/Roof/Roof_Corner_Left.blockymodel",
        "HitboxType": "Roof_Corner"
      },
      "Inverted_Corner_Right": {
        "CustomModel": "Blocks/Roof/Roof_Inverted_Corner.blockymodel",
        "HitboxType": "Roof_Inverted",
        "FlipType": "MirrorX"
      }
    }
  }
}
```

---

## Connected Block Templates

Connected blocks automatically select models and states based on neighboring blocks. A block
opts in through `BlockType.ConnectedBlockRuleSet`, a `Type`-tagged object. `ConnectedBlocksModule`
registers four rule-set types:

| `Type` | Java class | Notes |
|--------|-----------|-------|
| `Stair` | `StairConnectedBlockRuleSet` | Built-in stair corner/inverted-corner solver (~163 shipped blocks) |
| `Roof` | `RoofConnectedBlockRuleSet` | Built-in roof solver, adds a `Topper` (~241) |
| `CustomTemplate` | `CustomTemplateConnectedBlockRuleSet` | Data-driven; points at a template in `Server/Item/CustomConnectedBlockTemplates/` (~135) |
| `Patterned` | `PatternedConnectedBlockRuleSet` | Data-driven rule/shape trees; see [Patterned Connected Block Rule Sets](#patterned-connected-block-rule-sets) (new in 0.6.3, no shipped block uses it yet) |

The `CustomTemplate` form is described below; 11 templates ship:

| Template | Description |
|----------|-------------|
| `DoorConnectedBlockTemplate` | Door orientation and state |
| `DoorLargeConnectedBlockTemplate` | Large/double door connections |
| `ChestConnectedBlockTemplate` | Chest orientation |
| `RailsConnectedBlockTemplate` | Railway track connections |
| `WallConnectedBlockTemplate` | Wall/fence post connections |
| `PillarConnectedBlockTemplate` | Pillar stacking |
| `RoofConnectedBlockTemplate` | Roof tile connections |
| `BranchConnectedBlockTemplate` | Organic branch connections |
| `BookshelfConnectedBlockTemplate` | Bookshelf groupings |
| `CobbleCornerConnectedBlockTemplate` | Corner piece connections |
| `VillageConnectedBlockTemplate` | Village structure connections |

### Using a Connected Template

Reference the template by asset id and map every shape key it declares to a block
(`Build_Grey_Fence`; a `*` prefix references another block's state definitions):

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "CustomTemplate",
      "TemplateShapeAssetId": "WallConnectedBlockTemplate",
      "TemplateShapeBlockPatterns": {
        "Straight": "Build_Grey_Fence",
        "Corner": "*Build_Grey_Fence_State_Definitions_Corner"
      }
    }
  }
}
```

`TemplateShapeAssetId` is validated against the `CustomConnectedBlockTemplateAsset` store, and
`TemplateShapeBlockPatterns` values are `BlockPattern`s — the codec's own documentation is *"You
must specify all shapes as a BlockPattern. The shapes are as outlined in the keys of the
ShapeTemplateAsset's map."*

### Template Structure

Templates define shape patterns and the tags neighbors match on:

```json
{
  "ConnectsToOtherMaterials": true,
  "DefaultShape": "Straight",
  "Shapes": {
    "Straight": {
      "FaceTags": {
        "East": ["FenceConnection"],
        "West": ["FenceConnection"]
      },
      "PatternsToMatchAnyOf": [
        {
          "Type": "Custom",
          "AllowedPatternTransformations": {
            "IsCardinallyRotatable": true
          },
          "RulesToMatch": [
            {
              "Position": { "X": -1, "Y": 0, "Z": 0 },
              "IncludeOrExclude": "Include",
              "FaceTags": { "East": ["FenceConnection"] }
            }
          ]
        }
      ]
    },
    "Corner": { },
    "T_Junction": { },
    "Cross_Junction": { }
  }
}
```

The template asset has exactly four top-level keys (`CustomConnectedBlockTemplateAsset.CODEC`):

| Property | Type | Description |
|----------|------|-------------|
| `ConnectsToOtherMaterials` | boolean | Connect to blocks driven by a different template |
| `DefaultShape` | string | Shape used when no pattern matches |
| `DontUpdateAfterInitialPlacement` | boolean | Freeze the shape after placement (drives `CustomTemplateConnectedBlockRuleSet.onlyUpdateOnPlacement`) |
| `Shapes` | object | Map of shape name → `{ FaceTags, PatternsToMatchAnyOf }` |

Each entry of `Shapes` (`ConnectedBlockShape`) has two keys:

| Property | Type | Description |
|----------|------|-------------|
| `FaceTags` | object | Per-direction (`North`/`East`/`South`/`West`/`Up`/`Down`) tag arrays this shape exposes to neighbors |
| `PatternsToMatchAnyOf` | array | Patterns; the shape wins if any one of them matches |

Each pattern is `Type`-tagged; the only registered type is `Custom` (`CustomConnectedBlockPattern`):

| Property | Type | Description |
|----------|------|-------------|
| `AllowedPatternTransformations` | object | `PatternRotationDefinition` — `IsCardinallyRotatable`, `MirrorX`, `MirrorZ`; which transforms of the rule set are tried |
| `RulesToMatch` | array | `ConnectedBlockPatternRule` entries, all of which must hold |
| `TransformRulesToOrientation` | boolean | Rotate the rules by the block's own orientation before testing |
| `RequireFaceTagsMatchingRoll` | boolean | Require the neighbor's roll to line up when comparing face tags |
| `YawToApplyAddReplacedBlockType` | enum | `Rotation` (`None`/`Ninety`/`OneEighty`/`TwoSeventy`) applied to the resulting block |
| `OnlyOnPlacement` / `OnlyOnUpdate` | boolean | Restrict when the pattern is evaluated |

Each rule in `RulesToMatch` (`ConnectedBlockPatternRule`):

| Property | Type | Description |
|----------|------|-------------|
| `Position` | object | `{X, Y, Z}` block offset from the block being solved (default `0,0,0`) |
| `IncludeOrExclude` | enum | **Required.** `Include` (the neighbor must match) or `Exclude` (must not) |
| `FaceTags` | object | Face tags the neighbor must expose toward this block |
| `BlockTypes` | array | Block type keys the neighbor may be |
| `BlockTypeLists` | array | `Server/BlockTypeList/` asset ids the neighbor must belong to |
| `Shapes` | array | `BlockPattern.BlockEntry` set naming the shape blocks that satisfy the rule |
| `PlacementNormals` | array | `Up`/`Down`/`North`/`East`/`South`/`West` — codec doc: *"Queries the face the block was placed against"* |

> There is no `MaterialName` key on a template asset — that key belongs to the `Roof`
> rule set on the block itself (see [items-blocks.md](items-blocks.md#connected-blocks)).

---

## Patterned Connected Block Rule Sets

0.6.3 adds a second data-driven connected-block system alongside
[`CustomTemplate`](#connected-block-templates). Where a `CustomTemplate` asset hard-codes a
fixed shape vocabulary and matches neighbors by face tag, a **patterned** rule set is a
composable rule tree: boolean `And` / `Or` / `Not` nodes over two leaf predicates (face tags
and neighbor shapes), evaluated against a rotatable pattern of block offsets.

> **Nothing in 0.6.3 ships as a patterned rule set.** `Server/Item/ConnectedBlockRuleSets/`
> — the directory the asset store reads — does not exist in `Assets.zip`, and all ~554
> connected blocks still use `Stair`, `Roof` or `CustomTemplate`. The system is fully wired
> (assets, codecs, client packets) and available to plugins, but there is no shipped example
> to copy. Read the JSON below accordingly: **key names, types and requiredness are
> codec-certain** — they are taken from the codec builders and their own documentation strings,
> the same normative source every JSON page here relies on. What is *not* corroborated is
> **nesting and composition** (how deeply rules and shapes nest in practice) and **runtime
> semantics** (what a given combination actually renders). Trust the keys; test the shapes.

### The two halves

| Half | Class | Where |
|------|-------|-------|
| **Rule set asset** — the shared shape/pattern vocabulary | `PatternedConnectedBlockRuleSetAsset` | `Server/Item/ConnectedBlockRuleSets/<Id>.json` |
| **Per-block binding** — which concrete blocks/states play each shape | `PatternedConnectedBlockRuleSet` | `BlockType.ConnectedBlockRuleSet` with `"Type": "Patterned"` |

Many blocks can share one asset; each supplies its own block/state mapping. The asset store
loads after `TagPattern` and before `BlockType`, and a `ConnectedBlockRuleSetPacketGenerator`
replicates the whole asset (patterns, shapes, face tags) to clients so they can predict the
shape locally.

### The per-block binding

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "Patterned",
      "RuleSetId": "MyFenceRuleSet",
      "TemplatedShapes": {
        "Straight": { "State": "default" },
        "Corner": { "State": "Corner" },
        "Gate": { "Block": "My_Fence_Gate" }
      }
    }
  }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `RuleSetId` | string | **Required.** Id of a `PatternedConnectedBlockRuleSetAsset`; codec doc: *"The name of a ConnectedBlockRuleSetAsset asset"* |
| `TemplatedShapes` | object | **Required.** Shape name → `ConnectedBlockOutput`. `State` picks a state definition on this block (`"default"` = the base block); `Block` names a different block type entirely. Both are optional and may be combined |

`PatternedConnectedBlockRuleSet` resolves this map in both directions when block types load
(`updateCachedBlockTypes`): shape name → concrete block index for output, and block index →
shape name so `getShapeIdForBlockType(int)` can tell a neighbor which shape a placed block is
currently playing. Unlike the other rule-set types it always returns `false` from
`onlyUpdateOnPlacement()`, so patterned blocks re-solve on every neighbor update.

### The rule-set asset

```json
{
  "UpdateMode": "PlaceUpdate",
  "Shapes": {
    "Straight": {
      "Type": "Templated",
      "TemplateId": "Straight",
      "FaceTags": { "East": ["FenceConnection"], "West": ["FenceConnection"] }
    },
    "Corner": {
      "Type": "Templated",
      "TemplateId": "Corner",
      "RelativeRotation": { "Yaw": "Ninety" },
      "FaceTags": { "West": ["FenceConnection"], "South": ["FenceConnection"] }
    }
  },
  "Patterns": [
    {
      "Output": { "ShapeId": "Corner" },
      "TransformRulesWithOrientation": false,
      "RotationTransforms": [ { "Yaw": "All" } ],
      "Rule": {
        "Type": "And",
        "Rules": [
          { "Type": "FaceTag", "MatchType": "All",
            "PositionOffset": { "X": -1, "Y": 0, "Z": 0 },
            "FaceTags": { "East": ["FenceConnection"] } },
          { "Type": "Not",
            "Rule": { "Type": "Shape", "ShapeId": "Straight",
                      "PositionOffset": { "X": 1, "Y": 0, "Z": 0 } } }
        ]
      }
    },
    { "Output": { "ShapeId": "Straight" } }
  ]
}
```

| Key | Type | Description |
|-----|------|-------------|
| `Patterns` | array | **Required.** `ConnectedBlockPatternConfig[]`, tried in array order; the first pattern whose rule passes wins |
| `Shapes` | object | **Required.** Shape name → `ConnectedBlockShapeConfig` (`Type`-tagged, see below) |
| `UpdateMode` | enum | `PlaceUpdate` (default), `UpdatePlaceUpdate`, or `IgnoreUpdates`. Overrides `ConnectedBlockRuleSet.getUpdateMode()` for every block using the asset |

A pattern with **no** `Rule` matches unconditionally — put one last in `Patterns` as the
fallback shape (the `CustomTemplate` equivalent of `DefaultShape`).

### Pattern entries

| Key | Type | Description |
|-----|------|-------------|
| `Rule` | object | **Required in practice** — omit only for the catch-all fallback. A `ConnectedBlockRule` tree |
| `Output` | object | `ConnectedBlockPatternOutput` — `{ "ShapeId": "<key in Shapes>" }`. A pattern with no `Output` is skipped |
| `RotationTransforms` | array | Rotation groups to try; each is `{ "Yaw": …, "Pitch": …, "Roll": … }` with `None` / `Ninety` / `OneEighty` / `TwoSeventy` / `All`. Expanded to the cartesian product; defaults to the identity rotation only |
| `TransformRulesWithOrientation` | boolean | When `true`, each candidate rotation is composed with the block's own placed rotation before the rule is tested |

The winning rotation is what the block is placed at: the result rotation is the matching
transform composed with the output shape's `RelativeRotation`. This is how one rule expresses
all four cardinal variants of a corner — write the rule once for the `Yaw: None` case and list
`"RotationTransforms": [ { "Yaw": "All" } ]`.

### Rules

`Rule` objects are `Type`-tagged (`ConnectedBlockRule.CODEC`). Five types are registered:

| `Type` | Class | Keys | Behavior |
|--------|-------|------|----------|
| `And` | `ConnectedBlockAndRule` | `Rules` (required array) | All children must pass; a `null`/empty list passes |
| `Or` | `ConnectedBlockOrRule` | `Rules` (required array) | Any child passes; an empty list fails |
| `Not` | `ConnectedBlockNotRule` | `Rule` (required) | Inverts the child; a missing child fails |
| `FaceTag` | `ConnectedBlockFaceTagRule` | `PositionOffset`, `FaceTags` (required), `MatchType` (required) | Codec doc: *"A connected block rule that checks if there are face tags present from adjacent blocks"* |
| `Shape` | `ConnectedBlockShapeRule` | `PositionOffset`, `ShapeId` (required), `AllowedRotations` | Codec doc: *"A connected block rule that checks if the neighbor at a position offset resolves to a specific shape"* |

`MatchType` on a face-tag rule is `Any` or `All` (`MatchType` enum) — whether *one* listed
direction must be satisfied or *every* one. Within a single direction the tags always match
as a conjunction, and an empty tag array for a direction never matches.

`AllowedRotations` on a shape rule is a single rotation group (same `Yaw`/`Pitch`/`Roll`
shape as `RotationTransforms` entries); codec doc: *"Rotations the neighbor's shape may have.
When omitted, any rotation matches."*

`PositionOffset` is a `{X, Y, Z}` offset in the pattern's **rotated** frame — the active
rotation transform is applied to it before the lookup, which is what makes one authored rule
cover every listed rotation.

### Shapes

`Shapes` values are `Type`-tagged (`ConnectedBlockShapeConfig.CODEC`). Every shape accepts
two shared keys from `ConnectedBlockShapeConfig.BASE_CODEC`:

| Key | Type | Description |
|-----|------|-------------|
| `FaceTags` | object | `ConnectedBlockFaceTags` — per-direction (`North`/`East`/`South`/`West`/`Up`/`Down`) string arrays this shape advertises to neighbors |
| `RelativeRotation` | object | `BlockRotationConfig` — `{ "Yaw": …, "Pitch": …, "Roll": … }`, each a `Rotation` (`None` default). Composed into the placed rotation and un-applied when comparing a neighbor's face tags |

plus one discriminating key:

| `Type` | Class | Key | Matches a block when… |
|--------|-------|-----|------------------------|
| `Block` | `ConnectedBlockBlockTypeShape` | `Block` (required, validated block key) | its id equals `Block`. Codec doc: *"The block id this shape matches"* |
| `TagPattern` | `ConnectedBlockTagShape` | `TagPattern` (required, validated) | its tags satisfy the named `TagPattern` asset. Codec doc: *"A tag pattern to match blocks"* |
| `Templated` | `ConnectedBlockTemplatedShape` | `TemplateId` (required) | the block's own `TemplatedShapes` map binds it to this shape name. Codec doc: *"Key in the block type's TemplatedShapes map"* |

`Templated` is the shape type that pairs with the `TemplatedShapes` binding above: it lets one
rule-set asset be reused by many block families, each mapping the shared shape names onto its
own blocks/states. `Block` and `TagPattern` are absolute — they match a specific block or tag
pattern regardless of which rule set the neighbor uses.

> **Gotchas**
> - **A shape only participates if the block resolves to it.** `ConnectedBlockContext.getShapeForBlockType`
>   walks the *neighbor's* rule set when the neighbor is also `Patterned`, and falls back to
>   this rule set otherwise. A neighbor on a `Stair`/`Roof`/`CustomTemplate` rule set can only
>   be matched by a `Block` or `TagPattern` shape, never a `Templated` one.
> - **Only a 3×3×3 region is fast.** `ConnectedBlockContext` pre-caches the 27 blocks around
>   the origin; offsets outside that range fall back to a per-lookup chunk-section fetch. Keep
>   `PositionOffset` values within ±1 where you can.
> - **Filler blocks read as air.** A position occupied by the filler half of a multi-block
>   reports `null` block type, so a `FaceTag`/`Shape` rule there fails rather than matching the
>   anchor block.
> - **Order is significance.** `Patterns` is first-match-wins, so list the most specific
>   pattern first and the unconditional fallback last.

### Java surface

```java
// com.hypixel.hytale.server.core.universe.world.connectedblocks.config

// PatternedConnectedBlockRuleSetAsset
static DefaultAssetMap<String, PatternedConnectedBlockRuleSetAsset> getAssetMap()
static AssetStore<String, PatternedConnectedBlockRuleSetAsset,
        DefaultAssetMap<String, PatternedConnectedBlockRuleSetAsset>> getAssetStore()
String getId()
ConnectedBlockPatternConfig[] getPatterns()
Map<String, ConnectedBlockShapeConfig> getShapes()
ConnectedBlockUpdateMode getUpdateMode()
ConnectedBlockRuleSetAsset toPacket()          // com.hypixel.hytale.protocol type

// PatternedConnectedBlockRuleSet  (extends ConnectedBlockRuleSet)
PatternedConnectedBlockRuleSetAsset getRuleSetAsset()
String getShapeIdForBlockType(int blockTypeKey)   // null if this block plays no shape
boolean onlyUpdateOnPlacement()                   // always false
Optional<ConnectedBlocksUtil.ConnectedBlockResult> getConnectedBlockType(
        ChunkStore store, Vector3ic blockCoordinate, BlockType blockType,
        int rotation, Vector3ic placementNormal, boolean isPlacement)

// ConnectedBlockPatternConfig
ConnectedBlockRule getRule()
ConnectedBlockPatternOutput getOutput()
List<RotationTuple> getAllowedTransformRotations()
boolean isTransformRulesWithOrientation()

// ConnectedBlockFaceTags
boolean contains(Vector3i direction, String blockFaceTag)
Set<String> getBlockFaceTags(Vector3i direction)
Map<Vector3ic, HashSet<String>> getBlockFaceTags()
Set<Vector3ic> getDirections()
```

`ConnectedBlockRule` itself is `abstract` with one abstract method,
`boolean check(ConnectedBlockRule.Context)`, plus `toPacket()`. To add a rule type from a
plugin, subclass it, give it a `BuilderCodec`, and register the codec on
`ConnectedBlockRule.CODEC` (a `CodecMapCodec` keyed on `"Type"`) — the same pattern
`ConnectedBlocksModule.setup()` uses for the five built-ins. `ConnectedBlockShapeConfig`
works the same way via its own `CODEC` and `BASE_CODEC`.

`ConnectedBlockRule.Context` (implemented by `ConnectedBlockContext`) is what a custom rule
gets to query:

```java
BlockType getLocalBlockType(Vector3ic position)                  // null = air/filler/unloaded
RotationTuple getLocalRotation(Vector3ic position)
ConnectedBlockShapeConfig getShapeForBlockType(BlockType blockType)
ConnectedBlockShapeConfig getShapeById(String shapeId)
```

---

## Hitbox Definitions

Hitboxes define collision shapes using axis-aligned bounding boxes.

**Location:** `Server/Item/Block/Hitboxes/<Category>/<Name>.json`

### Structure

```json
{
  "Boxes": [
    {
      "Min": { "X": 0, "Y": 0, "Z": 0 },
      "Max": { "X": 1, "Y": 0.5, "Z": 1 }
    }
  ]
}
```

Coordinates are in block units (0-1 range per block).

### Common Hitbox Types

| Hitbox | Description |
|--------|-------------|
| `Block_Full` | Full cube (default) |
| `Block_Half` | Half-height slab |
| `Block_Quarter` | Quarter-height |
| `Block_Flat` | Carpet/rug height |
| `Door` | Closed door collision |
| `Door_Open_In` | Door swung inward |
| `Door_Open_Out` | Door swung outward |
| `Chest_Small` | Small chest |
| `Chest_Large` | Large chest |
| `Fence` | Fence post |
| `Wall` | Wall segment |
| `Stairs` | Stair step collision |

### Complex Hitbox Example

Multi-box hitbox for L-shaped collision:

```json
{
  "Boxes": [
    {
      "Min": { "X": 0, "Y": 0, "Z": 0 },
      "Max": { "X": 1, "Y": 1, "Z": 0.5 }
    },
    {
      "Min": { "X": 0, "Y": 0, "Z": 0.5 },
      "Max": { "X": 0.5, "Y": 1, "Z": 1 }
    }
  ]
}
```

---

## Sound Sets

Sound sets define audio events for block interactions.

**Location:** `Server/Item/Block/Sounds/<Name>.json`

### Sound Event Types

| Event | Description |
|-------|-------------|
| `Walk` | Footstep sounds |
| `Land` | Landing after fall |
| `Hit` | Block being damaged |
| `Break` | Block destroyed |
| `Build` | Block placed |

### Fluid-Specific Events

| Event | Description |
|-------|-------------|
| `MoveIn` | Entity enters fluid |
| `MoveOut` | Entity exits fluid |

### Example Sound Set

```json
{
  "Walk": "SFX_Footsteps_Stone",
  "Land": "SFX_Land_Stone",
  "Hit": "SFX_Block_Stone_Hit",
  "Break": "SFX_Block_Stone_Break",
  "Build": "SFX_Block_Stone_Place"
}
```

### Using Sound Sets

Reference in BlockType:

```json
{
  "BlockType": {
    "BlockSoundSetId": "Stone"
  }
}
```

### Common Sound Set IDs

| ID | Material Type |
|----|---------------|
| `Stone` | Rock, brick, ore |
| `Wood` | Planks, logs, furniture |
| `Dirt` | Soil, grass, sand |
| `Cloth` | Wool, fabric |
| `Metal` | Iron, copper blocks |
| `Glass` | Glass panes, windows |
| `Water` | Water blocks |
| `Gravel` | Gravel, pebbles |

---

## Particle Sets

Particle sets define visual effects for block interactions.

**Location:** `Server/Item/Block/Particles/<Name>.json`

### Particle Event Types

| Event | Description |
|-------|-------------|
| `Sprint` | Running on block |
| `Hit` | Block being damaged |
| `Break` | Block destroyed |
| `SoftLand` | Light landing |
| `HardLand` | Heavy landing |
| `Physics` | Physics interactions |

### Using Particle Sets

Reference in BlockType with optional color:

```json
{
  "BlockType": {
    "BlockParticleSetId": "Stone",
    "ParticleColor": "#808080"
  }
}
```

### Common Particle Set IDs

| ID | Effect Type |
|----|-------------|
| `Stone` | Stone chips |
| `Wood` | Wood splinters |
| `Dust` | Soft material dust |
| `Water` | Water splashes |
| `Leaf` | Leaf fragments |
| `Sand` | Sand grains |

---

## Fluid Blocks

Fluid blocks have special properties for flowing behavior and physics.

### Fluid Properties

| Property | Type | Description |
|----------|------|-------------|
| `MaxFluidLevel` | int | Maximum fluid depth (1 for sources) |
| `FluidFXId` | string | Visual effect configuration |
| `Effect` | array | Status effects in fluid |
| `Ticker` | object | Fluid spreading behavior |

### Example: Water Source

From `Server/Item/Block/Fluids/Water_Source.json`:

```json
{
  "MaxFluidLevel": 1,
  "Effect": ["Water"],
  "Opacity": "Transparent",
  "Textures": [
    {
      "Weight": 1,
      "All": "BlockTextures/Fluid_Water.png"
    }
  ],
  "BlockParticleSetId": "Water",
  "BlockSoundSetId": "Water",
  "FluidFXId": "Water",
  "Ticker": {
    "CanDemote": false,
    "SpreadFluid": "Water",
    "Collisions": {
      "Lava": {
        "BlockToPlace": "Rock_Stone_Cobble",
        "SoundEvent": "SFX_Flame_Break"
      },
      "Lava_Source": {
        "BlockToPlace": "Rock_Magma_Cooled",
        "SoundEvent": "SFX_Flame_Break"
      }
    }
  },
  "Tags": {
    "Fluid": ["Water"]
  }
}
```

### Fluid FX Configuration

**Location:** `Server/Item/Block/FluidFX/<Name>.json`

```json
{
  "Fog": "EnvironmentTint",
  "FogDistance": [-437, 190],
  "FogDepthStart": 95,
  "FogDepthFalloff": 1.3,
  "ColorsSaturation": 1.6,
  "ColorsFilter": [1, 1, 1],
  "DistortionAmplitude": 5,
  "DistortionFrequency": 6,
  "MovementSettings": {
    "SwimUpSpeed": 2.5,
    "SwimDownSpeed": -2.5,
    "HorizontalSpeedMultiplier": 0.6,
    "SinkSpeed": -1.35,
    "FieldOfViewMultiplier": 1,
    "EntryVelocityMultiplier": 1
  },
  "Particle": {
    "SystemId": "Underwater_Effects"
  }
}
```

### Ticker Configuration

Controls automatic fluid behavior. Base properties come from `FluidTicker.BASE_CODEC`;
the default ticker (`DefaultFluidTicker.CODEC`) adds spreading and collision rules:

```json
{
  "Ticker": {
    "CanDemote": false,
    "FlowRate": 2.0,
    "SpreadFluid": "Lava",
    "Collisions": {
      "Water": {
        "BlockToPlace": "Rock_Stone_Cobble",
        "SoundEvent": "SFX_Flame_Break"
      },
      "Water_Source": {
        "BlockToPlace": "Rock_Stone",
        "SoundEvent": "SFX_Flame_Break"
      }
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `FlowRate` | float | Tick frequency for this fluid type, in seconds |
| `CanDemote` | boolean | If false, the fluid stays at its level |
| `SupportedBy` | string | Fluid id that sustains this fluid (e.g. `Water` is supported by `Water_Source`) |
| `SpreadFluid` | string | Fluid id placed when this fluid spreads (e.g. sources spread their flowing variant) |
| `Collisions` | object | Map keyed by fluid id — what happens when this fluid tries to spread into that fluid |

Each `Collisions` entry (`FluidCollisionConfig`):

| Property | Type | Description |
|----------|------|-------------|
| `BlockToPlace` | string | The block to place when a collision occurs |
| `SoundEvent` | string | Sound event played on collision |
| `PlaceFluid` | boolean | Whether to still place the fluid on collision (default `false`) |

### Fluid Collision Transformations

When fluids touch, they can transform into blocks (from the shipped `Collisions` maps):

| Collision | Result |
|-----------|--------|
| Water spreading into Lava (flowing) | `Rock_Stone_Cobble` |
| Water spreading into Lava_Source | `Rock_Magma_Cooled` |
| Lava spreading into Water (flowing) | `Rock_Stone_Cobble` |
| Lava spreading into Water_Source | `Rock_Stone` |

---

## Block Interactions

Blocks can respond to player interactions via JSON configuration.

### Interaction Slots

| Slot | Trigger | Description |
|------|---------|-------------|
| `Primary` | Left click | Breaking/attacking |
| `Use` | Right click | Using/opening |
| `Collision` | Entity touch | Physics response |

### Example: Interactive Block

```json
{
  "BlockType": {
    "Interactions": {
      "Primary": "Break_Container",
      "Use": "Open_Container"
    }
  }
}
```

### BlockEntity Components

Some blocks have associated entity components:

| Component | Usage |
|-----------|-------|
| `RespawnBlock` | Bed spawn point |
| `Container` | Storage blocks |
| `CraftingBench` | Crafting stations |

See [Items - Blocks](items-blocks.md) for detailed BlockEntity documentation, and [Custom Block-Entity Components](#custom-block-entity-components) below for a verified end-to-end recipe (define your own component, tick it, spawn entities from it, and persist its state).

---

## Block Type Lists

Block type lists categorize blocks for world generation and game systems.

**Location:** `Server/BlockTypeList/<Category>.json`

### Available Lists

| List | Description |
|------|-------------|
| `Soils.json` | Dirt, grass variants (13 types) |
| `Rock.json` | Stone types (16 types) |
| `Gravel.json` | Gravel blocks |
| `Ores.json` | Ore blocks |
| `TreeWood.json` | Wood block types |
| `TreeLeaves.json` | Leaf block types |
| `PlantsAndTrees.json` | Plants and trees (80+ types) |
| `AllScatter.json` | All scatter blocks |
| `PlantScatter.json` | Plant scatter blocks |
| `Snow.json` | Snow blocks |
| `Empty.json` | Empty/air blocks |

### List Structure

```json
{
  "Types": [
    "Rock_Stone",
    "Rock_Granite",
    "Rock_Marble",
    "Rock_Sandstone"
  ]
}
```

---

## Visual Assets

### Block Models (.blockymodel)

3D models for non-cube blocks.

**Location:** `Common/Blocks/<Category>/<Name>.blockymodel`

Structure includes:
- Node hierarchy
- Mesh data (vertices, faces)
- UV mapping
- Bone references for animation

### Block Animations (.blockyanim)

Animation sequences for block states.

**Location:** `Common/Blocks/Animations/<Category>/<Name>.blockyanim`

Used for:
- Door opening/closing
- Chest lid movement
- Lever toggling
- Mechanical animations

### Using Custom Models

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Furniture/Chair_Wood.blockymodel",
    "CustomModelTexture": [
      { "Texture": "BlockTextures/Wood_Oak.png" }
    ],
    "CustomModelScale": 1.0,
    "HitboxType": "Chair"
  }
}
```

---

## Per-Block Animation Speed

`CustomModelAnimation` sets one playback speed for every instance of a block type. As of
0.6.3 the **block animation module** (`com.hypixel.hytale.server.core.modules.blockanimation`)
adds a *per-placed-block* override on top of it: a single windmill can be slowed, stopped
(`speed = 0`), or nudged into phase with its neighbors without touching the block type.

`BlockAnimationModule` is a core plugin (`PluginManifest.corePlugin`, depends on
`LegacyModule`), so it is always loaded — no manifest `Dependencies` entry is needed. Reach it
with `BlockAnimationModule.get()`.

### API

```java
// com.hypixel.hytale.server.core.modules.blockanimation.BlockAnimationModule
static BlockAnimationModule get()

boolean canBlockAnimate(World world, int x, int y, int z)
boolean setBlockAnimationSpeed(World world, int x, int y, int z, float speed)
boolean setBlockAnimationSpeed(World world, int x, int y, int z, float speed, float phase)
boolean setBlockAnimationPhase(World world, int x, int y, int z, float phase)
boolean clearBlockAnimationSpeed(World world, int x, int y, int z)
OptionalDouble getBlockAnimationSpeedOverride(World world, int x, int y, int z)

ComponentType<ChunkStore, BlockAnimationSection> getBlockAnimationSectionComponentType()
ResourceType<ChunkStore, BlockAnimationDirtySections> getDirtySectionsResourceType()
```

| Method | Description |
|--------|-------------|
| `canBlockAnimate` | `true` if the block *or any sibling state in its `State` family* declares a `CustomModelAnimation`. Setting a speed on a block that can't animate still succeeds — it just has no visible effect |
| `setBlockAnimationSpeed` (5-arg) | Store a speed override, attaching the storage component to the chunk section if needed |
| `setBlockAnimationSpeed` (6-arg) | Same, plus a one-shot phase. **Returns whether the *phase* was applied**, not the speed |
| `setBlockAnimationPhase` | Re-phase a block that already has a speed override. Returns `false` if it has none — it never attaches storage |
| `clearBlockAnimationSpeed` | Drop the override and fall back to the block type's own animation speed |
| `getBlockAnimationSpeedOverride` | The current override, or `OptionalDouble.empty()` when the block has none |

```java
BlockAnimationModule anim = BlockAnimationModule.get();
if (anim.canBlockAnimate(world, x, y, z)) {
    anim.setBlockAnimationSpeed(world, x, y, z, 0.25f);   // quarter speed
    anim.setBlockAnimationSpeed(world, x, y, z, 0.25f, 12f);  // ...starting at frame 12
}
OptionalDouble current = anim.getBlockAnimationSpeedOverride(world, x, y, z);
anim.clearBlockAnimationSpeed(world, x, y, z);
```

### Storage and replication

Overrides live on `BlockAnimationSection`, a `ChunkStore` component registered under the id
`"BlockAnimationSection"` and attached **per chunk section**, holding a block-index → speed
map (`hasSpeed` / `getSpeed` / `setSpeed` / `setPhase` / `removeSpeed` / `isEmpty` /
`getRevision`). Three chunk-store systems keep it honest:

| System | Role |
|--------|------|
| `BlockAnimationSystems.ReplicateChanges` | Drains `BlockAnimationDirtySections` and pushes a `SetBlockAnimationSpeeds` packet to players, then clears pending phases |
| `BlockAnimationSystems.LoadPacket` | Sends the section's current overrides to a player as the chunk loads |
| `BlockAnimationSystems.RemoveEmptySections` | Detaches the component once its last override is gone |

Only **speed** persists (`Index` + `Speed` per entry, plus a `Revision`); a phase is transient
and is cleared as soon as it has been replicated, so treat it as a one-shot resync rather than
stored state. A section rejects more than 32,768 entries on load (one per block in the section).

### `/blockanimspeed`

```
/blockanimspeed <speed>
/blockanimspeed <speed> <phase>
```

Sets the override on the block the caller is looking at (max 10 blocks). Permission group
`hytale:WorldEditor`. It reports `"…but this block has no model animation"` when
`canBlockAnimate` is `false`, and still applies the value.

> **Gotchas**
> - **World thread only.** All of these resolve the chunk section on the calling thread and
>   log `Block animation overrides must be changed on the world thread.` and return `false`
>   otherwise. Marshal with `world.execute(...)` from anywhere else.
> - **Speed range is `0 ≤ speed < 100`.** `BlockAnimationModule.MAX_SPEED` is `100.0f` but the
>   bound is *exclusive*, and `NaN`/infinite values are rejected. An out-of-range value makes
>   the setter return `false` without changing anything.
> - **The 6-arg setter's return value is about the phase.** It returns `true` only when the
>   phase changed, so a speed-only change through it reads as `false`. Use the 5-arg overload
>   when you only care about the speed.
> - **Overrides are dropped when the block changes identity.** `onBlockReplaced` clears the
>   override unless the new block is in the same `State` family as the old one, so a
>   door/lever state swap keeps its speed but replacing the block with something else does not.
> - **Multi-block fillers resolve to the anchor.** Targeting a filler cell walks back to the
>   anchor block, so the override lands once on the real block rather than on each cell.
> - **A new component can't be attached mid-write.** During store write processing the module
>   logs `A block animation component cannot be attached during store write processing.` and
>   refuses; set the speed outside a system's write phase, or on a block that already has one.

---

## Quick Start Examples

### Simple Cube Block

```json
{
  "TranslationProperties": {
    "Name": "server.items.My_Block.name"
  },
  "Categories": ["Blocks.Rocks"],
  "MaxStack": 10,
  "PlayerAnimationsId": "Block",
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Cube",
    "Opacity": "Solid",
    "Group": "Rock",
    "Textures": [
      { "Weight": 1, "All": "BlockTextures/My_Block.png" }
    ],
    "BlockSoundSetId": "Stone",
    "BlockParticleSetId": "Stone",
    "ParticleColor": "#808080",
    "Gathering": {
      "Breaking": {
        "GatherType": "Rocks"
      }
    }
  }
}
```

### Block with Custom Model

```json
{
  "TranslationProperties": {
    "Name": "server.items.My_Furniture.name"
  },
  "Categories": ["Blocks.Furniture"],
  "MaxStack": 5,
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Furniture/My_Furniture.blockymodel",
    "CustomModelTexture": [
      { "Texture": "BlockTextures/Wood_Oak.png" }
    ],
    "HitboxType": "Furniture_Medium",
    "VariantRotation": "NESW",
    "Support": "Down",
    "BlockSoundSetId": "Wood",
    "BlockParticleSetId": "Wood",
    "Gathering": {
      "Breaking": {
        "GatherType": "Woods"
      }
    }
  }
}
```

### Interactive Door

```json
{
  "TranslationProperties": {
    "Name": "server.items.My_Door.name"
  },
  "Categories": ["Blocks.Doors"],
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Doors/My_Door.blockymodel",
    "HitboxType": "Door",
    "VariantRotation": "NESW",
    "State": {
      "Id": "door",
      "Definitions": {
        "OpenDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_In.blockyanim",
          "HitboxType": "Door_Open_In",
          "InteractionSoundEventId": "SFX_Door_Wooden_Open"
        },
        "CloseDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_In.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Wooden_Close"
        },
        "CloseDoorOut": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_Out.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Wooden_Close"
        }
      }
    },
    "Interactions": {
      "Use": "Door_Toggle"
    },
    "BlockSoundSetId": "Wood",
    "BlockParticleSetId": "Wood"
  }
}
```

### Container Block

```json
{
  "TranslationProperties": {
    "Name": "server.items.My_Chest.name"
  },
  "Categories": ["Blocks.Containers"],
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Containers/My_Chest.blockymodel",
    "HitboxType": "Chest_Small",
    "VariantRotation": "NESW",
    "Support": "Down",
    "State": {
      "Id": "container",
      "Capacity": 27,
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
    },
    "Interactions": {
      "Primary": "Break_Container",
      "Use": "Open_Container"
    },
    "BlockSoundSetId": "Wood",
    "Gathering": {
      "Breaking": {
        "GatherType": "Woods",
        "DropList": [
          { "ItemId": "My_Chest", "Quantity": 1 }
        ]
      }
    }
  }
}
```

### Block with Inheritance

```json
{
  "Parent": "Rock_Stone",
  "TranslationProperties": {
    "Name": "server.items.Rock_Stone_Mossy.name"
  },
  "Icon": "Icons/ItemsGenerated/Rock_Stone_Mossy.png",
  "BlockType": {
    "Textures": [
      { "Weight": 1, "All": "BlockTextures/Rock_Stone_Mossy.png" }
    ],
    "ParticleColor": "#507850"
  }
}
```

---

## Java API Reference

### BlockType
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Core class representing a block type configuration. Provides access to all block properties including material, textures, sounds, and behavior settings.

#### Constants
```java
static final BlockType EMPTY;      // Empty/air block
static final BlockType UNKNOWN;    // Unknown block placeholder
static final BlockType DEBUG_CUBE; // Debug cube block
static final BlockType DEBUG_MODEL;// Debug model block

static final String EMPTY_KEY;     // Key for empty block
static final String UNKNOWN_KEY;   // Key for unknown block
static final int EMPTY_ID;         // ID for empty block
static final int UNKNOWN_ID;       // ID for unknown block
```

#### Static Methods
```java
// Get block from string identifier
static BlockType fromString(String id)

// Access the block asset store
static AssetStore<String, BlockType, ...> getAssetStore()
static BlockTypeAssetMap<String, BlockType> getAssetMap()

// Get unknown block for a specific key
static BlockType getUnknownFor(String key)

// Get block ID with fallback to unknown
static int getBlockIdOrUnknown(String key, String context, Object... args)
```

#### Core Properties
```java
String getId()                    // Block identifier
String getGroup()                 // Block group/category
boolean isUnknown()               // Check if this is an unknown block
boolean isState()                 // Check if this is a block state
Item getItem()                    // Get associated item (if any)
```

#### Material & Rendering
```java
BlockMaterial getMaterial()       // Get block material (Empty/Solid)
DrawType getDrawType()            // How the block is drawn
Opacity getOpacity()              // Block opacity
BlockFlags getFlags()             // Block flags (various properties)
ColorLight getLight()             // Light emission
```

#### Textures & Model
```java
BlockTypeTextures[] getTextures() // Block textures
String getCustomModel()           // Custom model path (if any)
float getCustomModelScale()       // Custom model scale
String getCustomModelAnimation()  // Custom model animation
CustomModelTexture[] getCustomModelTexture()
```

#### Sounds & Particles
```java
String getBlockSoundSetId()       // Sound set identifier
int getBlockSoundSetIndex()       // Sound set index
ModelParticle[] getParticles()    // Particle effects
String getBlockParticleSetId()    // Particle set identifier
Color getParticleColor()          // Particle color
String getBlockBreakingDecalId()  // Breaking decal texture
```

#### Rotation & Placement
```java
Rotation getRotationYawPlacementOffset()    // Rotation offset when placed
RandomRotation getRandomRotation()          // Random rotation settings
VariantRotation getVariantRotation()        // Variant rotation settings
BlockFlipType getFlipType()                 // Flip behavior
BlockPlacementSettings getPlacementSettings()// Placement rules
```

#### Collision & Interaction
```java
String getHitboxType()                      // Collision hitbox type
int getHitboxTypeIndex()                    // Collision hitbox index
String getInteractionHitboxType()           // Interaction hitbox type
int getInteractionHitboxTypeIndex()         // Interaction hitbox index
String getInteractionHint()                 // UI interaction hint
boolean isTrigger()                         // Is this a trigger block
int getDamageToEntities()                   // Damage dealt to entities
Map<InteractionType, String> getInteractions()// Interaction mappings
```

#### Block States
```java
BlockType getBlockForState(String state)    // Get block for named state
String getBlockKeyForState(String state)    // Get block key for state
String getDefaultStateKey()                 // Default state key
String getStateForBlock(BlockType block)    // Get state name for block
String getStateForBlock(String blockKey)    // Get state name for key
StateData getState()                        // Get state data config
```

#### Movement & Support
```java
BlockMovementSettings getMovementSettings() // Movement properties
SupportDropType getSupportDropType()        // Support drop behavior
int getMaxSupportDistance()                 // Max support distance
boolean isFullySupportive()                 // Fully supports neighbors
boolean hasSupport()                        // Has support requirements
Map<BlockFace, RequiredBlockFaceSupport[]> getSupport(int rotation)
Map<BlockFace, BlockFaceSupport[]> getSupporting(int rotation)
```

#### Other Properties
```java
ConnectedBlockRuleSet getConnectedBlockRuleSet()
RotatedMountPointsArray getSeats()          // Seat mount points
RotatedMountPointsArray getBeds()           // Bed mount points
TickProcedure getTickProcedure()            // Tick behavior
ShaderType[] getEffect()                    // Shader effects
Bench getBench()                            // Crafting bench data
BlockGathering getGathering()               // Gathering/farming data
FarmingData getFarming()                    // Farming configuration
Holder<ChunkStore> getBlockEntity()         // Block entity template
RailConfig getRailConfig(int rotation)      // Rail configuration
boolean isDoor()                            // Is this a door block
boolean canBePlacedAsDeco()                 // Can be deco placement
void getBlockCenter(int rotation, Vector3d out)// Get block center
```

---

### BlockMaterial
**Package:** `com.hypixel.hytale.protocol`

Simple enum representing the physical material type of a block.

```java
public enum BlockMaterial {
    Empty,  // No collision/air
    Solid   // Solid block with collision
}
```

#### Methods
```java
int getValue()                              // Get numeric value
static BlockMaterial fromValue(int value)   // Get from numeric value
static BlockMaterial[] values()             // All values
static BlockMaterial valueOf(String name)   // Get by name
```

---

### Rotation
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Enum representing 90-degree rotation increments around an axis.

```java
public enum Rotation {
    None,       // 0 degrees
    Ninety,     // 90 degrees
    OneEighty,  // 180 degrees
    TwoSeventy  // 270 degrees
}
```

#### Constants
```java
static final Rotation[] VALUES; // All rotation values
static final Rotation[] NORMAL; // Normal rotations subset
```

#### Methods
```java
int getDegrees()                 // Get rotation in degrees (0, 90, 180, 270)
double getRadians()              // Get rotation in radians
Axis getAxisOfAlignment()        // Get alignment axis
Vector3i getAxisDirection()      // Get axis direction vector

// Rotation operations
Rotation flip()                  // Flip rotation
Rotation flip(Axis axis)         // Flip around axis
Rotation add(Rotation other)     // Add rotations
Rotation subtract(Rotation other)// Subtract rotations

// Vector rotation methods
Vector3i rotateX(Vector3i v, Vector3i out)
Vector3f rotateX(Vector3f v, Vector3f out)
Vector3d rotateX(Vector3d v, Vector3d out)
Vector3i rotateY(Vector3i v, Vector3i out)
Vector3f rotateY(Vector3f v, Vector3f out)
Vector3d rotateY(Vector3d v, Vector3d out)
Vector3i rotateZ(Vector3i v, Vector3i out)
Vector3f rotateZ(Vector3f v, Vector3f out)
Vector3d rotateZ(Vector3d v, Vector3d out)
Vector3i rotateYaw(Vector3i v, Vector3i out)
Vector3f rotateYaw(Vector3f v, Vector3f out)
Vector3i rotatePitch(Vector3i v, Vector3i out)
Vector3f rotatePitch(Vector3f v, Vector3f out)

// Static rotation methods
static Rotation ofDegrees(int degrees)           // Get from degrees
static Rotation closestOfDegrees(float degrees)  // Closest to degrees
static Rotation add(Rotation a, Rotation b)      // Add two rotations
static Vector3i rotate(Vector3i v, Rotation yaw, Rotation pitch)
static Vector3i rotate(Vector3i v, Rotation yaw, Rotation pitch, Rotation roll)
static Vector3f rotate(Vector3f v, Rotation yaw, Rotation pitch, Rotation roll)
static Vector3d rotate(Vector3d v, Rotation yaw, Rotation pitch, Rotation roll)
```

---

### RotationTuple
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Java record combining yaw, pitch, and roll rotations. Used for block placement rotation (see `PlaceBlockEvent.getRotation()`).

```java
public record RotationTuple(int index, Rotation yaw, Rotation pitch, Rotation roll) {
}
```

#### Constants
```java
static final RotationTuple NONE;       // No rotation (all None)
static final int NONE_INDEX;           // Index of NONE
static final RotationTuple[] VALUES;   // All possible rotation tuples
```

#### Factory Methods
```java
// Create from components
static RotationTuple of(Rotation yaw, Rotation pitch, Rotation roll)
static RotationTuple of(Rotation yaw, Rotation pitch)  // roll = None

// Get by index
static RotationTuple get(int index)

// Compute index from components
static int index(Rotation yaw, Rotation pitch, Rotation roll)
```

#### Record Components (Accessors)
```java
int index()        // Pre-computed index
Rotation yaw()     // Yaw rotation
Rotation pitch()   // Pitch rotation
Rotation roll()    // Roll rotation
```

#### Methods
```java
// Apply rotation to vector
Vector3d rotatedVector(Vector3d v)

// Get rotation from array
static RotationTuple getRotation(RotationTuple[] rotations,
                                  RotationTuple tuple, Rotation yaw)
```

#### Usage Example
```java
// In a PlaceBlockEvent handler
PlaceBlockEvent event = ...;
RotationTuple rotation = event.getRotation();

// Access individual components
Rotation yaw = rotation.yaw();
Rotation pitch = rotation.pitch();
Rotation roll = rotation.roll();

// Modify rotation
RotationTuple newRotation = RotationTuple.of(
    Rotation.Ninety,
    Rotation.None,
    Rotation.None
);
event.setRotation(newRotation);
```

---

### Gathering Drop Types
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

These classes back the `Gathering` JSON object (see [Gathering Configuration](#gathering-configuration)). `BlockType.getGathering()` returns a `BlockGathering` whose codec maps each gathering mode to its own config class:

| JSON key (under `Gathering`) | Class | Accessor on `BlockGathering` |
|------------------------------|-------|------------------------------|
| `Breaking` | `BlockBreakingDropType` | `getBreaking()` |
| `Harvest` | `HarvestingDropType` | `getHarvest()` |
| `Soft` | `SoftBlockDropType` | `getSoft()` |
| `Physics` | `PhysicsDropType` | `getPhysics()` |

`BlockGathering` also exposes `isHarvestable()`, `isSoft()`, `getToolData()` (the `Tools` array), and `shouldUseDefaultDropWhenPlaced()`.

#### BlockBreakingDropType

Decodes `Gathering.Breaking` — JSON keys `GatherType`, `Quality`, `ItemId`, `Quantity`, `DropList`:

```java
String getGatherType()   // Required tool category ("Rocks", "Woods", ...)
int getQuality()         // Quality override on the produced item
int getQuantity()        // Direct-drop quantity
String getItemId()       // Item produced directly (alternative to a drop list)
String getDropListId()   // Drop table reference (JSON "DropList")
BlockBreakingDropType withoutDrops() // Copy that keeps the gather type but drops nothing
```

#### HarvestingDropType

Decodes `Gathering.Harvest` — JSON keys `ItemId`, `DropList`:

```java
String getItemId()
String getDropListId()
HarvestingDropType withoutDrops()
```

#### SoftBlockDropType

Decodes `Gathering.Soft` — JSON keys `ItemId`, `DropList`, `IsWeaponBreakable`:

```java
String getItemId()
String getDropListId()
boolean isWeaponBreakable()  // Block can also be broken by weapon hits
SoftBlockDropType withoutDrops()
```

---

### BlockSupportsRequiredForType
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config`

Enum behind the `BlockType` JSON key `SupportsRequiredFor`. When a block declares support requirements (see [Support System](items-blocks.md#support-system)), this decides whether **any one** satisfied direction keeps the block alive or **all** declared directions must hold.

```java
public enum BlockSupportsRequiredForType {
    Any,  // One satisfied support direction is enough
    All   // Every declared support direction must be satisfied
}
```

The default is `All`; no shipped block overrides it in JSON.

---

### BlockMountPoint
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.mountpoints`

One sit/sleep mount point on a block — the entries of the `Seats` and `Beds` arrays in `BlockType` JSON (`BlockType.getSeats()` / `BlockType.getBeds()` return the rotation-aware `RotatedMountPointsArray` wrapper). Per-entry JSON keys: `Offset` (relative to the block center at `.5,.5,.5`; forward on a chair is positive Z) and `Yaw` (degrees).

```json
{
  "BlockType": {
    "Seats": [
      { "Offset": { "X": 0, "Y": 0, "Z": 0.12 }, "Yaw": 0 }
    ]
  }
}
```
*(from `Furniture_Kweebec_Stool.json`)*

```java
static final BlockMountPoint[] EMPTY_ARRAY;

Vector3dc getOffset()             // Offset from the block center
float getYawOffSetDegrees()       // Yaw offset for the seated model, in degrees
BlockMountPoint rotate(Rotation yaw, Rotation pitch, Rotation roll) // Rotated copy
Vector3d computeWorldSpacePosition(Vector3i blockPos) // Absolute world position of the mount
Rotation3f computeRotationEuler(int rotationIndex)    // Final rotation for a placed variant
```

---

### FallingBlockSettings
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.fallingblocks`

Backs the `BlockType` JSON key `FallingBlockSettings` — blocks that detach and fall as entities when unsupported (sand-style). `BlockType.getFallingBlockSettings()` returns it.

```json
{
  "BlockType": {
    "FallingBlockSettings": {
      "HitboxCollisionConfig": "HardCollision",
      "Impact": { "Type": "Explode" }
    }
  }
}
```
*(from `Server/Item/Items/_Debug/Debug_Falling_Explosive.json`)*

```java
static final FallingBlockSettings DEFAULT;

FallingBlockImpact getImpact()          // What happens when the falling entity lands
String getHitboxCollisionConfigId()     // JSON "HitboxCollisionConfig"
```

`FallingBlockImpact` is the abstract landing behavior; its codec dispatches on the `Impact.Type` key. The shipped falling-blocks plugin registers `"Place"` (default — the block is placed back), `"Break"`, and `"Explode"`:

```java
public abstract class FallingBlockImpact {
    public abstract void apply(WorldChunk chunk, World world, BlockType blockType,
                               Vector3d position, RotationTuple rotation,
                               Store<EntityStore> store);
}
```

A plugin can add its own impact by subclassing and calling `FallingBlockImpact.CODEC.register("MyImpact", MyImpact.class, MyImpact.CODEC)` in `setup()`.

---

### Bench Configuration
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.bench`

Backs the `BlockType` JSON key `Bench` — the inline bench definition carried by bench items (e.g. `Server/Item/Items/Bench/Bench_Weapon.json`). `BlockType.getBench()` returns it. `Bench.CODEC` dispatches on the `Type` key using the `BenchType` enum; `BlockTypeModule` registers the variants:

| `Type` value | Class | Shipped example |
|--------------|-------|-----------------|
| `Crafting` | `CraftingBench` | `Bench_Weapon.json` |
| `Processing` | `ProcessingBench` | `Bench_Furnace.json` |
| `DiagramCrafting` | `DiagramCraftingBench` | `Bench_Armory.json` |
| `StructuralCrafting` | `StructuralCraftingBench` | `Bench_Builders.json` |

Base JSON keys (all bench types): `Id`, `DescriptiveLabel`, `TierLevels` (array), and the sound-event ids `LocalOpenSoundEventId`, `LocalCloseSoundEventId`, `CompletedSoundEventId`, `FailedSoundEventId`, `BenchUpgradeSoundEventId`, `BenchUpgradeCompletedSoundEventId`. Each `TierLevels` entry may set `UpgradeRequirement`, `CraftingTimeReductionModifier`, `ExtraInputSlot`, `ExtraOutputSlot`.

```json
{
  "BlockType": {
    "Bench": {
      "Type": "Crafting",
      "Id": "Weapon_Bench",
      "TierLevels": [
        {
          "CraftingTimeReductionModifier": 0.0,
          "UpgradeRequirement": {
            "Material": [
              { "ItemId": "Ingredient_Bar_Iron", "Quantity": 20 },
              { "ItemId": "Ingredient_Leather_Light", "Quantity": 30 }
            ],
            "TimeSeconds": 3
          }
        }
      ]
    }
  }
}
```
*(abridged from `Bench_Weapon.json`)*

#### Bench (base class)

```java
BenchType getType()
String getId()
String getDescriptiveLabel()
BenchTierLevel getTierLevel(int tier)
BenchUpgradeRequirement getUpgradeRequirement(int tier)
RootInteraction getRootInteraction()   // The interaction that opens this bench type
Bench toPacket()                       // protocol.Bench

// Bind the opening interaction for a bench type (engine wiring)
static void registerRootInteraction(BenchType type, RootInteraction interaction)
```

#### BenchUpgradeRequirement

One tier-upgrade cost — JSON keys `Material` (item + quantity list) and `TimeSeconds`:

```java
MaterialQuantity[] getInput()   // JSON "Material"
float getTimeSeconds()
```

#### DiagramCraftingBench

`Type: "DiagramCrafting"`. Extends `CraftingBench` and adds no keys of its own — categories come from `CraftingBench`'s `Categories` array (`getCategories()` returning `BenchCategory[]`, each with `Id`, `Name`, `Icon`, `ItemCategories`).

#### StructuralCraftingBench

`Type: "StructuralCrafting"` — the Builders bench (block-set crafting). Own JSON keys: `Categories` (string array), `HeaderCategories`, `AlwaysShowInventoryHints`, `AllowBlockGroupCycling`.

```java
boolean isHeaderCategory(String category)
int getCategoryIndex(String category)
boolean shouldAllowBlockGroupCycling()
boolean shouldAlwaysShowInventoryHints()
```

---

### Farming Config Classes
**Package:** `com.hypixel.hytale.server.core.asset.type.blocktype.config.farming`

Two classes back the `Farming` JSON documented in [Farming & Soil](items-blocks.md#farming--soil).

#### FarmingStageData

Abstract base for the entries of `Farming.Stages.<set>[]`. `FarmingStageData.CODEC` dispatches on each stage's `Type` key; the shipped farming plugin registers `"BlockType"`, `"BlockState"`, `"Prefab"`, and `"Spread"`. Base JSON keys: `Duration` (`{ "Min", "Max" }` range) and `SoundEventId`.

```java
Rangef getDuration()
String getSoundEventId()
boolean implementsShouldStop()   // Whether this stage type uses shouldStop()
boolean consumesRemainingTime()

boolean shouldStop(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
                   Ref<ChunkStore> ref2, int x, int y, int z)
boolean canApply(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
                 Ref<ChunkStore> ref2, int x, int y, int z)
void apply(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
           Ref<ChunkStore> ref2, int x, int y, int z, FarmingStageData previous)
void remove(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref1,
            Ref<ChunkStore> ref2, int x, int y, int z)
```

A plugin adds a custom stage type by subclassing and registering against `FarmingStageData.CODEC`.

#### GrowthModifierAsset

Asset type for growth-rate modifiers — the ids listed in `Farming.ActiveGrowthModifiers`. Assets load from `Server/Farming/Modifiers/*.json` (shipped: `Fertilizer`, `Water`, `LightLevel`, `Darkness`); each declares a `Type` (`"Fertilizer"`, `"LightLevel"`, or `"Water"` — registered by the farming plugin), a `Modifier` multiplier, and type-specific keys (e.g. `LightLevel` adds `ArtificialLight` / `Sunlight` ranges).

```json
{ "Type": "Fertilizer", "Modifier": 2 }
```
*(from `Server/Farming/Modifiers/Fertilizer.json`)*

```java
static AssetStore<String, GrowthModifierAsset, ...> getAssetStore()
static DefaultAssetMap<String, GrowthModifierAsset> getAssetMap()

String getId()
double getModifier()
double getCurrentGrowthMultiplier(CommandBuffer<ChunkStore> buffer, Ref<ChunkStore> ref1,
                                  Ref<ChunkStore> ref2, int x, int y, int z, boolean flag)
```

---

### BlockBoundingBoxes
**Package:** `com.hypixel.hytale.server.core.asset.type.blockhitbox`

The asset class behind [Hitbox Definitions](#hitbox-definitions) — one asset per file under `Server/Item/Block/Hitboxes/`, decoding the `Boxes` array. A block references one by name via `HitboxType`; `BlockType.getHitboxTypeIndex()` is the index into this asset map.

```java
static final String DEFAULT = "Full";  // Default full-cube hitbox id
static final int DEFAULT_ID = 0;
static final BlockBoundingBoxes UNIT_BOX;

static AssetStore<String, BlockBoundingBoxes, ...> getAssetStore()
static IndexedLookupTableAssetMap<String, BlockBoundingBoxes> getAssetMap()
static BlockBoundingBoxes getUnitBoxFor(String id) // Full-cube stand-in for a removed asset

String getId()
boolean protrudesUnitBox()  // Any box extends outside the 1x1x1 cell
RotatedVariantBoxes get(Rotation yaw, Rotation pitch, Rotation roll)
RotatedVariantBoxes get(int rotationIndex)
Hitbox[] toPacket()
```

`BlockBoundingBoxes.RotatedVariantBoxes` is the box set for one placement rotation:

```java
Box getBoundingBox()     // Enclosing AABB
Box[] getDetailBoxes()   // Individual boxes (multi-box hitboxes)
boolean hasDetailBoxes()
boolean containsPosition(double x, double y, double z)
```

---

### FillerBlockUtil
**Package:** `com.hypixel.hytale.server.core.util`

When a block's hitbox protrudes its own cell (`BlockBoundingBoxes.protrudesUnitBox()`), the engine occupies the overlapped neighbor cells with invisible *filler blocks* so collision and placement stay consistent (large doors, oversized furniture). `FillerBlockUtil` is the static helper for that bookkeeping — mostly engine-driven, but useful when a plugin validates or clears multi-cell blocks.

```java
static final int NO_FILLER = 0;

// Iterate / test the neighbor cells a rotated hitbox spills into
static void forEachFillerBlock(RotatedVariantBoxes boxes, TriIntConsumer consumer)
static boolean testFillerBlocks(RotatedVariantBoxes boxes, TriIntPredicate predicate)

// Filler offsets are packed into one int
static int pack(int x, int y, int z)
static int unpackX(int packed)
static int unpackY(int packed)
static int unpackZ(int packed)

// Engine-side add/remove of the filler blocks around an anchor block
static void setFillerBlocksAt(ComponentAccessor<ChunkStore> accessor, Ref<ChunkStore> ref,
                              BlockSection section, int x, int y, int z,
                              int anchorX, int anchorY, int anchorZ, ChangeReason reason)
static void removeFillerBlocksAt(ComponentAccessor<ChunkStore> accessor, BlockSection section,
                                 int x, int y, int z,
                                 int anchorX, int anchorY, int anchorZ, ChangeReason reason)
```

`FillerBlockUtil.ChangeReason` enum: `NONE`, `NORMAL`, `BY_PHYSICS`. The higher-level entry point is `BlockTypeModule.breakOrSetFillerBlocks(...)`, which breaks or re-places a block's fillers from the asset maps.

---

### World Block Access

#### Via World and Chunks
```java
// Get chunk key from block coordinates
long chunkKey = ...; // Calculate from world position

// Get chunk if loaded (returns null if not loaded)
WorldChunk chunk = world.getChunkIfLoaded(chunkKey);

// Get chunk if in memory (non-ticking)
WorldChunk chunk = world.getChunkIfInMemory(chunkKey);

// Get chunk asynchronously
CompletableFuture<WorldChunk> futureChunk = world.getChunkAsync(chunkKey);
futureChunk.thenAccept(chunk -> {
    // Work with chunk
});
```

#### Chunk Access Methods
```java
// Synchronous access
WorldChunk loadChunkIfInMemory(long chunkKey)
WorldChunk getChunkIfInMemory(long chunkKey)
WorldChunk getChunkIfLoaded(long chunkKey)
WorldChunk getChunkIfNonTicking(long chunkKey)

// Asynchronous access
CompletableFuture<WorldChunk> getChunkAsync(long chunkKey)
CompletableFuture<WorldChunk> getNonTickingChunkAsync(long chunkKey)
```

---

## Block Ticking

**Packages:** `com.hypixel.hytale.server.core.asset.type.blocktick` and `...blocktick.config`

The engine ticks blocks through two separate paths, both configured per block type in JSON and both extensible from a plugin:

| Path | JSON key on `BlockType` | Java accessor | Runs |
|------|--------------------------|---------------|------|
| **Scheduled ticking** | `TickProcedure` | `BlockType.getTickProcedure()` | Every chunk tick, for blocks flagged as *ticking* in their chunk section |
| **Random ticking** | `RandomTickProcedure` | `BlockType.getRandomTickProcedure()` | For a few randomly sampled blocks per chunk section per tick |

Scheduled ticking is driven by the shipped block-tick plugin (`com.hypixel.hytale.builtin.blocktick.BlockTickPlugin`), random ticking by the random-tick plugin (`com.hypixel.hytale.builtin.randomtick.RandomTickPlugin`). Grass spreading is a random tick; both procedure kinds decode polymorphically on a `Type` key.

### IBlockTickProvider & BlockTickManager

`IBlockTickProvider` answers "what runs when this block id gets a scheduled tick":

```java
public interface IBlockTickProvider {
    static final IBlockTickProvider NONE;       // No-op provider
    TickProcedure getTickProcedure(int blockId); // null = this block does not tick
}
```

`BlockTickManager` is the static holder the chunk-tick system reads the provider from:

```java
static void setBlockTickProvider(IBlockTickProvider provider)
static IBlockTickProvider getBlockTickProvider()
static boolean hasBlockTickProvider()
```

The shipped provider is `BlockTickPlugin` itself: its `getTickProcedure(int)` simply returns `BlockType.getAssetMap().getAsset(blockId).getTickProcedure()`, i.e. the block's own `TickProcedure` JSON. A plugin that wants to route scheduled ticks differently (per-world logic, procedures not stored on the asset, …) can install its own provider with `BlockTickManager.setBlockTickProvider(...)` — note there is exactly one global provider, so replacing it takes over scheduled ticking entirely.

### BlockTickStrategy

Every scheduled tick — and every fluid tick (see [Fluids](fluids.md)) — returns a `BlockTickStrategy` telling the chunk what to do with the block's ticking flag:

```java
public enum BlockTickStrategy {
    CONTINUE,                     // Keep ticking this block next tick
    IGNORED,                      // Nothing to do; drop it from the ticking set
    SLEEP,                        // Stop ticking until something re-wakes the block
    WAIT_FOR_ADJACENT_CHUNK_LOAD  // Park it; retried when neighboring chunks load
}
```

A slept/ignored block is re-woken by flagging it again — `BlockChunk.setTicking(x, y, z, true)` (which delegates to the owning `ChunkSection` and marks it for saving; `isTicking(x, y, z)` reads the flag). The 0.5 `setNeighbourBlocksTicking(x, y, z)` 3×3×3 wake helper was **removed by 0.6.3** — wake neighbors with individual `setTicking` calls. `WAIT_FOR_ADJACENT_CHUNK_LOAD` blocks are merged back into the ticking set by the block-tick plugin's systems once the adjacent chunk is available.

### TickProcedure (scheduled ticks)

```java
public abstract class TickProcedure {
    public static final CodecMapCodec<TickProcedure> CODEC;  // dispatches on "Type"

    public abstract BlockTickStrategy onTick(World world, WorldChunk chunk,
                                             int x, int y, int z, int blockId);
}
```

The block-tick plugin registers two growth-style types, `"BasicChance"` (keys `NextId`, `Chance`, `ChanceMin`, `NextTicking`) and `"SplitChance"`. No shipped block asset sets `TickProcedure` in JSON in this build — plant growth ships through the farming system instead — but the codec key is live, and custom types registered here work the same way as random-tick types (below).

### RandomTickProcedure (random ticks)

```java
public interface RandomTickProcedure {
    static final CodecMapCodec<RandomTickProcedure> CODEC;   // dispatches on "Type"

    void onRandomTick(Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer,
                      BlockSection section, int x, int y, int z,
                      int blockId, BlockType blockType);
}
```

Each tick the random-tick system samples a few block positions per chunk section (defaults: 1 per stable section, 3 per recently-changed section) and invokes the sampled block's procedure if it has one. Coordinates passed to `onRandomTick` are world block coordinates.

The random-tick plugin registers `"ChangeIntoBlock"` (key `TargetBlock`) and `"SpreadTo"`. Grass is the shipped example — `Soil_Grass.json`:

```json
{
  "BlockType": {
    "RandomTickProcedure": {
      "Type": "SpreadTo",
      "AllowedTag": "Spreadable=Grass",
      "SpreadDirections": [
        { "X": -1, "Z": 0 }, { "X": 1, "Z": 0 },
        { "X": 0, "Z": -1 }, { "X": 0, "Z": 1 }
      ],
      "MaxY": 1,
      "MinY": -1,
      "RevertBlock": "Soil_Dirt"
    }
  }
}
```
*(abridged — the real file lists all eight horizontal directions)*

### Hooking custom block ticking

Registering a custom procedure type is the supported way for a plugin to tick its own blocks:

```java
public class MeltProcedure implements RandomTickProcedure {
    public static final BuilderCodec<MeltProcedure> CODEC =
        BuilderCodec.builder(MeltProcedure.class, MeltProcedure::new)
            .addField(new KeyedCodec<>("MeltInto", Codec.STRING),
                      (p, v) -> p.meltInto = v, p -> p.meltInto)
            .build();

    private String meltInto = "Empty";

    @Override
    public void onRandomTick(Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer,
                             BlockSection section, int x, int y, int z,
                             int blockId, BlockType blockType) {
        // e.g. replace this block with `meltInto` when its biome is warm
    }
}

// In your plugin's setup():
RandomTickProcedure.CODEC.register("Melt", MeltProcedure.class, MeltProcedure.CODEC);
```

Then reference it from the block's JSON:

```json
{ "BlockType": { "RandomTickProcedure": { "Type": "Melt", "MeltInto": "Water_Source" } } }
```

The same pattern applies to scheduled ticks: extend `TickProcedure`, register via `TickProcedure.CODEC.register(...)`, set the block's `TickProcedure` key, and return a [`BlockTickStrategy`](#blocktickstrategy) from `onTick` (`CONTINUE` to keep ticking, `SLEEP`/`IGNORED` when done). Registration names are global to the codec, so pick a distinctive `Type` string. The shipped `BlockTickPlugin` / `RandomTickPlugin` must be enabled (they are by default) — they own the systems that actually walk ticking blocks and call your procedure.

---

## Block Events

Handle block interactions through the event system. All block events are ECS events and should be handled using `EntityEventSystem`.

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

### Event Summary

| Class | Description | Cancellable |
|-------|-------------|-------------|
| `PlaceBlockEvent` | Block is placed | Yes |
| `BreakBlockEvent` | Block is broken | Yes |
| `DamageBlockEvent` | Block takes damage (mining progress) | Yes |
| `UseBlockEvent.Pre` | Before block is used/interacted with | Yes |
| `UseBlockEvent.Post` | After block is used/interacted with | No |

---

### PlaceBlockEvent

Fired when a block is placed.

```java
public class PlaceBlockEvent extends CancellableEcsEvent {
    ItemStack getItemInHand()
    Vector3i getTargetBlock()
    void setTargetBlock(Vector3i position)
    RotationTuple getRotation()
    void setRotation(RotationTuple rotation)
    boolean isCancelled()
    void setCancelled(boolean)
}
```

---

### BreakBlockEvent

Fired when a block is broken.

```java
public class BreakBlockEvent extends CancellableEcsEvent {
    ItemStack getItemInHand()
    Vector3i getTargetBlock()
    BlockType getBlockType()
    void setTargetBlock(Vector3i position)
    boolean isCancelled()
    void setCancelled(boolean)
}
```

---

### DamageBlockEvent

Fired when a block takes damage (mining progress). This fires during the mining process before the block is actually broken.

```java
public class DamageBlockEvent extends CancellableEcsEvent {
    ItemStack getItemInHand()
    Vector3i getTargetBlock()
    BlockType getBlockType()
    boolean isCancelled()
    void setCancelled(boolean)
}
```

#### DamageBlockEvent Usage

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.DamageBlockEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class DamageBlockEventSystem extends EntityEventSystem<EntityStore, DamageBlockEvent> {

    public DamageBlockEventSystem() {
        super(DamageBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       DamageBlockEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            // Could log mining progress or modify damage
            var blockType = event.getBlockType();
            var pos = event.getTargetBlock();
            System.out.println("Mining " + blockType + " at " + pos);
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

### UseBlockEvent

Fired when a block is used/interacted with. Has `Pre` and `Post` variants.

#### UseBlockEvent.Pre

Fired before the block interaction is processed. Can be cancelled.

```java
public class UseBlockEvent.Pre extends CancellableEcsEvent {
    InteractionType getInteractionType()
    InteractionContext getContext()
    Vector3i getTargetBlock()
    BlockType getBlockType()
    boolean isCancelled()
    void setCancelled(boolean)
}
```

#### UseBlockEvent.Post

Fired after the block interaction is processed. Cannot be cancelled.

```java
public class UseBlockEvent.Post extends EcsEvent {
    InteractionType getInteractionType()
    InteractionContext getContext()
    Vector3i getTargetBlock()
    BlockType getBlockType()
}
```

#### UseBlockEvent Usage

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.UseBlockEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class UseBlockPreSystem extends EntityEventSystem<EntityStore, UseBlockEvent.Pre> {

    public UseBlockPreSystem() {
        super(UseBlockEvent.Pre.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       UseBlockEvent.Pre event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            // Prevent using certain block types
            // event.setCancelled(true);
            player.getPlayerRef().sendMessage(Message.raw("You used a block!"));
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

## Usage Examples

### Handle Block Break Event
```java
// Using EntityEventSystem for ECS events
public class BlockBreakSystem extends EntityEventSystem<EntityStore, BreakBlockEvent> {
    public BlockBreakSystem() {
        super(BreakBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       BreakBlockEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            Vector3i pos = event.getTargetBlock();
            player.getPlayerRef().sendMessage(Message.raw("You broke a block at " + pos.x + ", " + pos.y + ", " + pos.z));
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}

// Register in setup()
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new BlockBreakSystem());
}
```

### Cancel Block Placement
```java
public class BlockPlaceSystem extends EntityEventSystem<EntityStore, PlaceBlockEvent> {
    public BlockPlaceSystem() {
        super(PlaceBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PlaceBlockEvent event) {
        // Cancel placement in certain conditions
        Vector3i target = event.getTargetBlock();
        if (target.y > 100) {
            event.setCancelled(true);
            Player player = chunk.getComponent(index, Player.getComponentType());
            if (player != null) {
                player.getPlayerRef().sendMessage(Message.raw("Cannot place blocks above y=100"));
            }
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

---

## Block Health & Fragility

**Package:** `com.hypixel.hytale.server.core.modules.blockhealth`

A separate runtime subsystem tracks per-block *durability* — how damaged a block is between hits, independent of the one-shot [`DamageBlockEvent`](#damageblockevent) fired on a single strike. It is shipped as a core `JavaPlugin` module (`BlockHealthModule`) that registers a `ChunkStore` component, so damage state is stored and persisted alongside the chunk rather than on individual block instances.

> [!NOTE]
> Block health is stored on the **chunk**, not the block. A `BlockHealthChunk` component holds a sparse map keyed by `Vector3i` block position — only damaged or fragile blocks occupy entries; undamaged blocks have none.

### Key Classes

| Class | Description |
|-------|-------------|
| `BlockHealthModule` | Core `JavaPlugin` module; singleton accessor `BlockHealthModule.get()` exposes the chunk-component type |
| `BlockHealthChunk` | `Component<ChunkStore>` holding the position→health and position→fragility maps for one chunk; carries the damage/repair API |
| `BlockHealth` | Per-block durability state: current health, last-damage game time, destroyed/full-health flags |
| `FragileBlock` | Marks a block position as fragile and records how long (`durationSeconds`) the fragility lasts |

### Accessing the component

`BlockHealthModule.get().getBlockHealthChunkComponentType()` returns the `ComponentType<ChunkStore, BlockHealthChunk>`. Read the `BlockHealthChunk` off a loaded chunk's `ChunkStore` with that type using the standard component-access pattern (see [Components](components.md) and [World block access](#world-block-access)). All mutating calls take the world + block position so the change can be re-broadcast to clients.

```java
// Inside a system/handler that already has the World and a Vector3i block pos:
BlockHealthChunk health = /* chunk's ChunkStore component, via the type above */;

Instant gameTime = /* current game-time Instant */;          // damageBlock stamps this
health.damageBlock(gameTime, world, pos, 5.0f);             // apply 5 damage
float remaining = health.getBlockHealth(pos);               // query current health
health.repairBlock(world, pos, 2.0f);                       // heal 2
health.removeBlock(world, pos);                             // clear all tracked state
```

### BlockHealthChunk methods

| Method | Description |
|--------|-------------|
| `damageBlock(Instant gameTime, World, Vector3i, float amount)` | Applies damage; returns the updated `BlockHealth`. Stamps the last-damage time |
| `repairBlock(World, Vector3i, float amount)` | Heals the block; returns the updated `BlockHealth` |
| `removeBlock(World, Vector3i)` | Drops all health/fragility tracking for the position |
| `getBlockHealth(Vector3i)` | Current health value for the position |
| `makeBlockFragile(Vector3i, float durationSeconds)` | Marks the position fragile for a duration |
| `isBlockFragile(Vector3i)` | Whether the position is currently fragile |
| `getBlockHealthMap()` | `Map<Vector3i, BlockHealth>` of all damaged blocks in the chunk |
| `getBlockFragilityMap()` | `Map<Vector3i, FragileBlock>` of all fragile blocks in the chunk |
| `createBlockDamagePackets(List<ToClientPacket>)` | Appends the chunk's damage-overlay packets (used to sync crack visuals to clients) |

### BlockHealth methods

| Member | Description |
|--------|-------------|
| `NO_DAMAGE_INSTANCE` (static) | Shared instance representing an undamaged block |
| `getHealth()` / `setHealth(float)` | Current durability value |
| `getLastDamageGameTime()` / `setLastDamageGameTime(Instant)` | When the block was last hit (drives regen timing) |
| `isDestroyed()` | Health has reached zero |
| `isFullHealth()` | Block is at maximum durability |

> [!WARNING]
> This is engine-internal infrastructure exposed publicly; re-surveyed against 0.6.3, no first-party *content plugin* references it — the only consumer outside its own package is the engine's own `BlockHarvestUtils`. The class/method surface above is verified against `HytaleServer.jar`, but the intended end-to-end authoring flow (how a custom block declares its max health and regen) is not exercised by any shipped plugin — treat the worked example as illustrative of the API shape, not a guaranteed recipe.

---

## Custom Block-Entity Components

The worked example below compiles against the 0.6.3 jar and is covered by the example-build gate, so the API surface is current. The end-to-end run against a live server was last exercised on an older build and has not been repeated for 0.6.3 — treat the runtime behaviour as unconfirmed rather than guaranteed. Worked example: [`examples/item-respawner`](https://github.com/inkthorne/hytale-modding-handbook/tree/main/examples/item-respawner), a placeable pedestal that drops an item, respawns it on an interval (Quake-style), and is edited in-world through a press-F settings GUI.

A *block-entity component* is your own data attached to individual placed blocks. Unlike a [`DamageBlockEvent`](#damageblockevent) handler (which reacts to player actions), a block-entity component is **persistent per-block state** that you can tick on the server's heartbeat. The shipped `BlockSpawner`, `Container`, and bed `RespawnBlock` all work this way; this section shows how to author your own.

Block-entity components live on the **`ChunkStore`** — the ECS store that backs chunks and blocks (see [Components](components.md)), distinct from the `EntityStore` that holds players, mobs, and dropped items. Living on the `ChunkStore` is what makes the state save and load with the chunk.

### 1. The component

Implement `Component<ChunkStore>`. Give it a `BuilderCodec` (see [Codecs](codecs.md)) that lists the persisted fields, a no-arg constructor, and a `clone()` (the engine clones the JSON-defined template to instantiate each placed block).

```java
public class ItemRespawner implements Component<ChunkStore> {

    public static final BuilderCodec<ItemRespawner> CODEC =
        BuilderCodec.builder(ItemRespawner.class, ItemRespawner::new)
            .addField(new KeyedCodec<>("Item", Codec.STRING),
                      (s, v) -> s.item = v, s -> s.item)
            .addField(new KeyedCodec<>("IntervalSeconds", Codec.INTEGER),
                      (s, v) -> s.intervalSeconds = v, s -> s.intervalSeconds)
            .build();

    private String item = "Weapon_Crossbow_Iron";
    private int intervalSeconds = 20;

    public ItemRespawner() {}

    // getters/setters ...

    @Override
    public ItemRespawner clone() {
        ItemRespawner copy = new ItemRespawner();
        copy.item = this.item;
        copy.intervalSeconds = this.intervalSeconds;
        return copy;
    }
}
```

Each `addField` key (`"Item"`, `"IntervalSeconds"`) is the JSON key authors set in the block definition. Fields absent from the data keep their defaults.

### 2. Wire it to a block

Define a normal block-item, and nest your component under `BlockType.BlockEntity.Components` keyed by the **name you register it under** (step 3). The object's keys map to the codec fields:

```json
{
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Model",
    "Opacity": "Transparent",
    "CustomModel": "Blocks/Structures/Pillars/Pillar_Base.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Blocks/Structures/Pillars/Pillar_Base_Textures/Marble_Brick.png", "Weight": 1 }
    ],
    "Interactions": {
      "Use": {
        "Interactions": [
          {
            "Type": "Condition",
            "RequiredGameMode": "Creative",
            "Next": { "Type": "OpenCustomUI", "Page": { "Id": "ItemRespawner" } }
          }
        ]
      }
    },
    "BlockEntity": {
      "Components": {
        "ItemRespawner": { "Item": "Weapon_Crossbow_Iron", "IntervalSeconds": 20 }
      }
    }
  }
}
```

The carrier block is just a normal block — here a visible, solid pedestal reusing a shipped marble pillar-base model so the spawned item rests on top and the block is targetable (needed for the press-F GUI in step 7). It could equally be a plain cube, or even invisible and walk-through (`Material: "Empty"` + `DrawType: "Empty"`, as shipped crops and the `Barrier` block are) if you don't need to interact with it. The `Use` → `OpenCustomUI` interaction is only needed for the editing GUI; drop it for a fixed-config spawner.

Two deliberate choices here:
- **No `Gathering`.** Omitting the gathering config makes the block unbreakable by mining in adventure/survival (the same way `Rock_Bedrock` and `Barrier` are), while creative's instant-break can still remove it. Add a `Gathering.Breaking` block if you want it mineable.
- **`Condition` → `Creative`.** Wrapping `OpenCustomUI` in a `Condition` with `RequiredGameMode: "Creative"` means the GUI only opens for creative-mode players, so adventure players can't reconfigure the block (see the prompt caveat in step 7).

### 3. Register the component and a system

In your plugin's `setup()`, register against **`getChunkStoreRegistry()`** (not the entity-store registry). `registerComponent` returns the `ComponentType` handle; pass it to your system:

```java
ComponentType<ChunkStore, ItemRespawner> type = getChunkStoreRegistry()
    .registerComponent(ItemRespawner.class, "ItemRespawner", ItemRespawner.CODEC);
getChunkStoreRegistry().registerSystem(new ItemRespawnerSystem(type));
```

The string `"ItemRespawner"` is exactly the JSON key from step 2.

### 4. Tick over placed blocks

`EntityTickingSystem` is generic over the store type, so `EntityTickingSystem<ChunkStore>` ticks block-entities the same way `EntityTickingSystem<EntityStore>` ticks entities — this is the base the engine's own fluid ticker uses. `getQuery()` restricts the tick to block-entities carrying both your component and the engine's `BlockModule.BlockStateInfo` (which every placed block-entity has, and which carries the block's location):

```java
public class ItemRespawnerSystem extends EntityTickingSystem<ChunkStore> {
    private final ComponentType<ChunkStore, ItemRespawner> type;
    private final Query<ChunkStore> query;

    public ItemRespawnerSystem(ComponentType<ChunkStore, ItemRespawner> type) {
        this.type = type;
        this.query = Query.and(type, BlockModule.BlockStateInfo.getComponentType());
    }

    @Override public Query<ChunkStore> getQuery() { return query; }

    // We mutate the EntityStore from here (step 5), so keep the tick single-threaded.
    @Override public boolean isParallel(int chunkCount, int entityCount) { return false; }

    @Override
    public void tick(float deltaTime, int index, ArchetypeChunk<ChunkStore> chunk,
                     Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer) {
        ItemRespawner spawner = chunk.getComponent(index, type);
        var info = chunk.getComponent(index, BlockModule.BlockStateInfo.getComponentType());
        if (spawner == null || info == null) return;
        // ... resolve position (step 4b), then spawn/respawn (step 5) ...
    }
}
```

#### 4b. Resolving the block's world position

`BlockStateInfo` carries a reference to the owning **chunk section** (`getSectionRef()`, a 32×32×32 `ChunkSection`) plus the block's packed section-local index (`getIndex()`). As of 0.6.3 it resolves the world position for you:

```java
Vector3i blockPos = new Vector3i();                  // org.joml
if (!info.fillWorldPos(store, blockPos)) return;     // false: section ref invalid / section unloaded
int x = blockPos.x, y = blockPos.y, z = blockPos.z;

World world = store.getExternalData().getWorld();   // ChunkStore -> World
```

`fillWorldPos(accessor, out)` looks up the `ChunkSection` component through the section ref and does `worldCoordFromLocalCoord(section.getX/Y/Z(), ChunkUtil.xFromIndex/yFromIndex/zFromIndex(index))`; the no-accessor overload `fillWorldPos(out)` uses the ref's own store. (Before 0.6.3 the component exposed `getChunkRef()` to the column `WorldChunk` and you unpacked a column index with `ChunkUtil.{x,y,z}FromBlockInColumn` — both are gone.)

### 5. Spawning an item-entity from the block

The item you drop is a normal entity in the **`EntityStore`**, reached via the `World`. Build a dropped-item `Holder` with `ItemComponent.generateItemDrop(...)` and insert it with `Store.addEntity(...)`:

```java
EntityStore entityStore = world.getEntityStore();
Store<EntityStore> entities = entityStore.getStore();   // also a ComponentAccessor

ItemStack stack = new ItemStack(spawner.getItem(), 1);
Vector3d pos = new Vector3d(x + 0.5, y + 1.1, z + 0.5);   // rest on top of the pedestal
Holder<EntityStore> drop = ItemComponent.generateItemDrop(
        entities, stack, pos, new Rotation3f(), 0f, 0f, 0f);   // Rotation3f + three velocity floats
if (drop == null) return;   // null on an invalid/empty stack
Ref<EntityStore> ref = entities.addEntity(drop, AddReason.SPAWN);
```

`generateItemDrop` attaches everything a pickup needs (transform, velocity, physics, a UUID, and a despawn timer) and returns `null` for an invalid item id, so a bad `Item` value fails safe. The drop carries the engine's standard despawn timer — an untouched pickup eventually despawns, after which your "is it still here?" check (below) treats it as gone.

> Because this mutates the `EntityStore` while iterating the `ChunkStore`, override `isParallel(...)` to return `false` (shown in step 4) so the tick runs single-threaded. The `CommandBuffer<ChunkStore>` the tick receives cannot insert `EntityStore` entities — it's typed to the chunk store — which is why the spawn goes through `world.getEntityStore().getStore()` directly.

### 6. "Only if not already present" + surviving reloads

To avoid spawning a second item while one is still lying there, remember what you spawned and check it each tick. Within one session, hold the `Ref` that `addEntity` returned: `Ref.isValid()` is `true` while the item exists and flips to `false` the instant it's picked up or despawns.

A `Ref` is a transient, in-memory handle — it does **not** survive a reload, but the dropped item (saved with the world) does. To keep the two in sync, also persist the spawned item's `UUID` (add it to the codec with `Codec.UUID_BINARY`) and re-acquire the `Ref` on load via `EntityStore.getRefFromUUID(uuid)`:

```java
// re-acquire after a reload, when the transient Ref is gone but the UUID persisted
Ref<EntityStore> ref = spawner.getSpawnedRef();
if ((ref == null || !ref.isValid()) && spawner.getSpawnedUuid() != null) {
    ref = entityStore.getRefFromUUID(spawner.getSpawnedUuid());
    spawner.setSpawnedRef(ref);
}
if (ref != null && ref.isValid()) {
    // still present — capture the UUID once the engine assigns it (see gotcha), then wait
    return;
}
// gone — count up deltaTime; spawn again once IntervalSeconds elapses
```

The engine provides a ready-made wrapper for exactly this — `com.hypixel.hytale.server.core.entity.reference.PersistentRef` (a UUID + cached `Ref`, with its own `CODEC`, that re-resolves through `getRefFromUUID`). Its `getEntity(accessor)` returns the live `Ref` or `null`. The engine's own mob and chicken-coop spawner blocks (`SpawnMarkerBlock`, `CoopBlock`) persist a `PersistentRef` this way. The example tracks the `Ref` and `UUID` by hand only to make the moving parts explicit.

### 7. Editing block-entity state in-world (press-F GUI)

To let players reconfigure a placed block (its `Item`, `IntervalSeconds`, …) without commands, open a custom UI page bound to that specific block-entity. This is how the shipped `Prefab_Spawner_Block` is edited, and it's three pieces:

**A. A `Use` interaction in the block JSON** (step 2) opens a page by id. Wrap it in a `Condition` so only creative-mode players can edit:

```json
"Interactions": {
  "Use": {
    "Interactions": [
      {
        "Type": "Condition",
        "RequiredGameMode": "Creative",
        "Next": { "Type": "OpenCustomUI", "Page": { "Id": "ItemRespawner" } }
      }
    ]
  }
}
```

> [!NOTE]
> **The interact prompt ("press F") shows for _any_ block with an interaction, in every game mode** — it's emitted by the engine's interaction tracker based solely on the block having interactions, and ignores both game mode and the `Condition` above. So the `Condition` stops adventure players from *opening* the GUI, but they still *see* the prompt. To suppress the prompt entirely (no interaction on the block at all), trigger the GUI from a command instead — open the same page with `player.getPageManager().openCustomPage(...)` from an `AbstractWorldCommand` that targets the looked-at block.

**B. A page extending `InteractiveCustomUIPage<T>`**, where `T` is a small codec-backed data class for the submitted form. `build()` loads the `.ui` layout, seeds each field from the component, and binds the Save button to send the field values back; the base decodes them into `T` and calls `handleDataEvent()`, where you write to the component and persist with `BlockStateInfo.markNeedsSaving()`:

```java
public class ItemRespawnerSettingsPage extends InteractiveCustomUIPage<ItemRespawnerSettingsData> {
    private final BlockModule.BlockStateInfo info;
    private final ItemRespawner state;

    public ItemRespawnerSettingsPage(PlayerRef player, BlockModule.BlockStateInfo info,
                                     ItemRespawner state, CustomPageLifetime lifetime) {
        super(player, lifetime, ItemRespawnerSettingsData.CODEC);   // base decodes the form via this codec
        this.info = info;
        this.state = state;
    }

    @Override
    public void build(Ref<EntityStore> player, UICommandBuilder cmd, UIEventBuilder evt, Store<EntityStore> store) {
        cmd.append("Pages/ItemRespawnerSettingsPage.ui");      // path relative to Common/UI/Custom/
        cmd.set("#Item.Value", state.getItem());              // seed fields from current state
        cmd.set("#IntervalSeconds.Value", (double) state.getIntervalSeconds());
        // on Save, send each named element's value back under the codec's @-keys
        EventData data = new EventData()
                .append("@Item", "#Item.Value")
                .append("@IntervalSeconds", "#IntervalSeconds.Value");
        evt.addEventBinding(CustomUIEventBindingType.Activating, "#SaveButton", data);
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> player, Store<EntityStore> store, ItemRespawnerSettingsData data) {
        state.setItem(data.getItem());
        state.setIntervalSeconds((int) Math.round(data.getIntervalSeconds()));
        info.markNeedsSaving();   // persist the edited block-entity with its chunk
        close();
    }
}
```

The data class is a plain object whose `BuilderCodec` keys are the `@`-names bound in `build()` (`@Item`, `@IntervalSeconds`); the `.ui` file provides the named input elements (`#Item`, `#IntervalSeconds`, `#SaveButton`).

**C. Bind the page id to the block** in `setup()`. `registerBlockEntityCustomPage` hands your supplier the targeted block-entity's `Ref`; read its components (via `ref.getStore()`) and construct the page:

```java
OpenCustomUIInteraction.registerBlockEntityCustomPage(
    this, ItemRespawnerSettingsPage.class, "ItemRespawner",   // id matches OpenCustomUI Page.Id
    (player, blockRef) -> {
        Store<ChunkStore> s = blockRef.getStore();
        var info = s.getComponent(blockRef, BlockModule.BlockStateInfo.getComponentType());
        ItemRespawner state = s.getComponent(blockRef, type);   // the ComponentType from step 3
        return (info == null || state == null) ? null
            : new ItemRespawnerSettingsPage(player, info, state, CustomPageLifetime.CanDismissOrCloseThroughInteraction);
    });
```

Because the supplier reads the components off the targeted block's `Ref`, the page is always bound to the exact block the player pressed F on — edits land on that block's state and persist with it.

### Key classes for this recipe

| Class | Package | Role |
|-------|---------|------|
| `Component<ChunkStore>` | `component` | Interface your block-entity state implements |
| `ComponentRegistryProxy` | `component` | `getChunkStoreRegistry()`; `registerComponent` / `registerSystem` |
| `BlockModule.BlockStateInfo` | `server.core.modules.block` | Per-block-entity component: `getSectionRef()` + `getIndex()`, `fillWorldPos(...)` resolves the world position |
| `ChunkUtil` | `math.util` | `xFromIndex` / `yFromIndex` / `zFromIndex` (section-local index → 0–31) / `worldCoordFromLocalCoord` |
| `EntityTickingSystem<ChunkStore>` | `component.system.tick` | Per-tick system over block-entities |
| `ItemComponent` | `server.core.modules.entity.item` | `generateItemDrop(...)` builds a dropped-item `Holder` |
| `PersistentRef` | `server.core.entity.reference` | Save-surviving reference to a spawned entity |
| `InteractiveCustomUIPage<T>` | `server.core.entity.entities.player.pages` | Form page; decodes the submission into `T` and calls `handleDataEvent` (step 7) |
| `OpenCustomUIInteraction` | `server.core.modules.interaction.interaction.config.server` | `registerBlockEntityCustomPage(...)` binds a page id to a block-entity (step 7) |

### Gotchas

- **Register on the chunk store, not the entity store.** Block-entity components and their systems go through `getChunkStoreRegistry()`. Registering on `getEntityStoreRegistry()` means your `tick()` never sees placed blocks.
- **The JSON key is the registration name.** `BlockEntity.Components.<Key>` must match the string passed to `registerComponent(class, "<Key>", codec)` exactly, or the component silently never attaches.
- **A fresh drop's UUID is null for a tick.** `generateItemDrop` ensures a `UUIDComponent`, but the actual UUID is assigned slightly later — reading it immediately after `addEntity` yields `null`. Capture it lazily on a later tick (the live `Ref` covers the gap), or use `PersistentRef`.
- **`world.getEntity(uuid)` won't find a dropped item.** That method returns high-level `Entity` wrappers (players/NPCs); a bare item holder isn't one. Use `EntityStore.getRefFromUUID(uuid)` (or a `PersistentRef`) for the existence check instead.
- **Keep the tick single-threaded if it spawns entities.** `EntityTickingSystem` may run in parallel by default; override `isParallel(...)` to `false` when the body mutates another store.
- **`Opacity` has no `"Opaque"` value.** The valid `Opacity` values are `Solid`, `Transparent`, `Semitransparent`, and `Cutout`. A `Model`-draw block uses `"Transparent"`; an invalid value fails JSON decode and the whole mod refuses to load. (Likewise, asset *ids* like `BlockParticleSetId` / `ItemSoundSetId` must name a real shipped asset — copy them from a real block of the same material rather than guessing.)
- **A press-F GUI needs a targetable block.** An invisible, non-collidable carrier (`Material/DrawType: "Empty"`) can't be aimed at, so `OpenCustomUI` never fires. Use a visible, solid block (as in step 2) when you want the editing GUI.
- **The interact prompt can't be game-mode-gated from block config.** Any block with an interaction shows the "press F" prompt in every mode; neither game mode nor `Condition` affects it (they gate the *action*, not the prompt). For a prompt-free block, drop the interaction and open the GUI from a command (step 7 note).
- **Omit `Gathering` for an unbreakable block.** A block with no `Gathering.Breaking` can't be mined in adventure/survival (like `Rock_Bedrock`), but creative instant-break still removes it.

---

## Notes
- Block manipulation typically goes through chunk accessors
- Block states persist additional data per-block instance
- Always check if chunk is loaded before accessing blocks
- Use async chunk loading for non-critical operations to avoid blocking
- Block events are ECS events; use `EntityEventSystem` to handle them
- To place blocks in geometric shapes (spheres, cubes, cones, …), use the coordinate iterators in [Block Shape Iteration](math.md#block-shape-iteration)

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the 0.5.0 block system (verified against `HytaleServer.jar`).

- **`itemId cannot be BlockTypeKey.EMPTY!`** → an operation received the empty/air block key where a real block was required. Fix: pass a concrete block type key, not `EMPTY_KEY` (see [Java API Reference](#java-api-reference)).
- **`One and only one of BlockTag or ItemId must be set!`** → a config entry set both `BlockTag` and `ItemId`, or neither. Fix: specify exactly one of the two.
- **`Block entry cannot be empty`** → a block list/entry was left blank. Fix: provide a non-empty block type key.
- **`Cannot select from empty blocks list`** → a block-selection operation ran against an empty list. Fix: ensure the list contains at least one block before selecting.
- **Symptom:** a block listed in a `Server/BlockTypeList/<Category>.json` `Types[]` array is dropped at load (the loader reports it `contains invalid block … skipping`) → the key does not resolve to a real `BlockType`. Fix: use exact, correctly-cased block type keys (see [Block Type Lists](#block-type-lists)).

---

## Related Documentation

- [Items](items.md) - Item system and inheritance
- [Block Items](items-blocks.md) - Furniture, containers, crafting benches
- [Interactions](interactions.md) - Block use and break interactions
- [Components](components.md) - ECS components including BlockEntity
- [Events](events.md) - Block-related events
- [Drops](drops.md) - Drop tables and loot configuration

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
