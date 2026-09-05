---
title: "Block Definitions"
description: "Define Hytale blocks — visual assets (.blockymodel models, .blockyanim animations) in Common/Blocks and JSON game logic in Server/Item with properties, interactions, and behavior."
seo:
  type: TechArticle
---

# Block Definitions

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item` · **Verified against 0.6.3**

Block definitions configure every placeable block in Hytale, from terrain and ores to furniture, doors, and fluids. Blocks are defined as items with a `BlockType` property that specifies rendering, collision, sounds, particles, and interaction behavior.

This page is the **JSON** side. The Java classes behind it — `BlockType`, ticking, block
events, world block access and custom block-entity components — are in
[blocks-java-api.md](blocks-java-api.md), and the connected-block rule sets are in
[blocks-connected.md](blocks-connected.md).

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Connected Blocks](blocks-connected.md) | `blocks-connected.md` | `ConnectedBlockRuleSet` types and patterned rule sets |
| [Blocks Java API](blocks-java-api.md) | `blocks-java-api.md` | `BlockType`, ticking, block events, world block access |
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

| Category | Examples (block items using it in 0.6.3) |
|----------|----------|
| `Blocks.Wood` | Planks, logs, bark (315 items) |
| `Blocks.Rocks` | Stone, sandstone, marble (189) |
| `Blocks.Plants` | Flowers, crops, leaves (189) |
| `Blocks.Deco` | Rubble, scatter, decorative odds and ends (172) |
| `Blocks.Soils` | Dirt, grass, sand, gravel (138) |
| `Blocks.Cloth` | Wool, fabric blocks (119) |
| `Blocks.Metal` | Metal blocks (100) |
| `Blocks.Ores` | Ore blocks (66) |
| `Blocks.Portals` / `Blocks.Fluids` | Portal blocks (18) / fluid blocks (9) |

Furniture is **not** under `Blocks.*` — it has its own top-level namespace, and so do the
builder-tool blocks:

| Category | Examples (block items using it in 0.6.3) |
|----------|----------|
| `Furniture.Containers` | Chests, barrels, crates (89) |
| `Furniture.Doors` | Doors, gates, trapdoors (83) |
| `Furniture.Furniture` | Chairs, tables, stools (68) |
| `Furniture.Lighting` | Lamps, braziers, torches (52) |
| `Furniture.Shelves` / `Furniture.Signs` | Shelves (41) / signs (33) |
| `Furniture.Benches` / `Furniture.Beds` | Crafting benches (22) / beds (15) |
| `Tool.TechnicalBlocks` | Barrier and other technical blocks (74) |
| `Tool.BrushFilters` / `Tool.PrefabEditing` / `Tool.Machinima` | Builder-tool blocks (13 / 8 / 1) |

There is no `Blocks.Furniture`, `Blocks.Containers`, `Blocks.Doors` or `Blocks.Lighting` — use the
`Furniture.*` names above. (One shipped block carries a singular `Blocks.Soil`; that is a typo in
the asset, not a real category.)

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
| `WorldChunk` | `server.core.universe.world.chunk` | Block read/write access (see [world.md](world-chunks.md#worldchunk)) |
| `PlaceBlockEvent` | `server.core.event.events.ecs` | ECS event fired when a block is placed (cancellable) |
| `BreakBlockEvent` | `server.core.event.events.ecs` | ECS event fired when a block is broken (cancellable) |
| `DamageBlockEvent` | `server.core.event.events.ecs` | ECS event fired during mining progress (cancellable) |
| `UseBlockEvent` | `server.core.event.events.ecs` | ECS event for block use; `Pre` (cancellable) / `Post` |
| `BlockBoundingBoxes` | `server.core.asset.type.blockhitbox` | Hitbox asset (`Server/Item/Block/Hitboxes`); see [BlockBoundingBoxes](blocks-java-api.md#blockboundingboxes) |
| `BlockTickManager` | `server.core.asset.type.blocktick` | Static holder for the block-tick provider; see [Block Ticking](blocks-java-api.md#block-ticking) |
| `BlockTypeModule` | `server.core.blocktype` | Core `JavaPlugin` module behind block types: registers the `Bench` codec variants and the block-physics component; `BlockTypeModule.get()` |
| `BlockSetModule` | `server.core.modules.blockset` | Core `JavaPlugin` module resolving named `BlockSet` assets to block-id sets (`blockInSet`, `getBlockSets`, singleton `BlockSetModule.getInstance()`); still carries `@Deprecated(forRemoval = true)` as of 0.6.3 |

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
    { "Weight": 2, "All": "BlockTextures/Rock_Stone.png" },
    { "Weight": 1, "All": "BlockTextures/Rock_Stone_2.png" },
    { "Weight": 1, "All": "BlockTextures/Rock_Stone_3.png" }
  ]
}
```
*(from `Rock_Stone.json` — the base texture is picked twice as often as either variant)*

**Per-face textures:**

```json
{
  "Textures": [
    {
      "Weight": 1,
      "Up": "BlockTextures/Soil_Grass_GS.png",
      "Down": "BlockTextures/Soil_Dirt.png",
      "Sides": "BlockTextures/Soil_Grass_Side.png"
    },
    {
      "Weight": 1,
      "Up": "BlockTextures/Soil_Grass_GS_02.png",
      "Down": "BlockTextures/Soil_Dirt.png",
      "Sides": "BlockTextures/Soil_Grass_Side.png"
    }
  ]
}
```
*(from `Soil_Grass.json` — per-face and weighted variants combine freely)*

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

`Light` decodes through `ProtocolCodecs.COLOR_LIGHT` (`com.hypixel.hytale.server.core.codec`) into a `ColorLight`: `Color` is a hex string (`"#RGB"` or `"#RRGGBB"`) and `Radius` a **byte** (so `0–127`); there is no `Intensity` key. Shipped fluids and lamps set only `Color` (e.g. `"Light": { "Color": "#765" }`).

### Collision Properties

| Property | Type | Description |
|----------|------|-------------|
| `HitboxType` | string | Reference to hitbox definition (file basename under `Server/Item/Block/Hitboxes/`) |
| `Support` | object | Required support, keyed by face (`Up`/`Down`/`North`/`South`/`East`/`West`) → array of `RequiredBlockFaceSupport` entries, e.g. `"Support": { "Down": [ { "FaceType": "Full" } ] }` |
| `Supporting` | object | Which faces this block offers as support to neighbors, same face-keyed shape (e.g. `{ "Up": [ { "FaceType": "Full" } ] }`) |
| `SupportsRequiredFor` | string | `"Any"` / `"All"` — see [BlockSupportsRequiredForType](blocks-java-api.md#blocksupportsrequiredfortype) |
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
| `TickProcedure` / `RandomTickProcedure` | object | Scheduled / random ticking — see [Block Ticking](blocks-java-api.md#block-ticking). (There is no `Ticker` key on a `BlockType`; `Ticker` belongs to fluid blocks.) |

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

`Breaking` either names a direct drop (`ItemId` + optional `Quantity` / `Quality`) or goes through a
drop table via `DropList`. `DropList` is a `ContainedAssetCodec`, so it accepts **either** the id of a
shipped [drop table](drops.md) — `"DropList": "Iron_Stack"`, as `Deco_Iron_Stack.json` does — **or** an
inline `ItemDropList` object, whose single key is `Container`:

```json
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
}
```
*(from `Furniture_Kweebec_Chest_Large.json`)*

What `DropList` is **not** is a bare array of item entries — `[{ "ItemId": …, "Quantity": … }]` fails to decode.

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
*(from `Furniture_Kweebec_Chest_Large.json`)*

| Property | Type | Description |
|----------|------|-------------|
| `Definitions` | object | Map of state name → per-state `BlockType` override |

`Definitions` is the **only** key `StateData.CODEC` accepts — there is no `Id` and no `Capacity` on
`State`. A container's slot count lives on its block-entity component instead:
`"BlockEntity": { "Components": { "ItemContainerBlock": { "Capacity": 36 } } }` (see
[Block Items](items-blocks.md)). All 935 shipped blocks with a `State` use only `Definitions`.

State names are not free-form either: the engine looks up specific names (`OpenDoorIn`,
`CloseWindow`, `Corner_Right`, `Topper`, `On`/`Off`, `Stage1`…) depending on which system drives the
block — the door interaction, the container window, a `Roof`/`Stair` connected rule set, farming
stages. Copy the set a shipped block of the same kind uses.

### State Definition Properties

Each entry is a **partial `BlockType`**: any [`BlockType` key](#blocktype-properties) may appear and
overrides the base block for that state. The keys shipped blocks actually use, most common first:

| Property | Type | Description |
|----------|------|-------------|
| `HitboxType` | string | Collision shape for this state (2,248 uses) |
| `CustomModel` | string | Model for this state (2,016) |
| `FlipType` | string | `ORTHOGONAL` or `SYMMETRIC` — the two `BlockFlipType` values (1,744) |
| `Supporting` | object | Faces this state offers as support (1,696) |
| `Gathering` | object | Per-state drops (597) |
| `CustomModelAnimation` | string | Animation played on entering the state (333) |
| `InteractionSoundEventId` | string | Sound when entering the state (331) |
| `InteractionHitboxType` | string | Separate interaction hitbox (240) |
| `InteractionHint` | string | Localization key for the interact prompt (180) |
| `SoundOcclusionOpacity` | float | How much this state muffles sound through it (75) |

plus `CustomModelTexture`, `Textures`, `Material`, `DrawType`, `Light`, `BlockSoundSetId`,
`BlockParticleSetId`, `ParticleColor`, `Opacity`, `Interactions`, `Flags`, and the rest of the
`BlockType` vocabulary.

### Example: Door with Multiple States

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Decorative_Sets/Desert/Door.blockymodel",
    "HitboxType": "Door",
    "VariantRotation": "NESW",
    "IsDoor": true,
    "State": {
      "Definitions": {
        "OpenDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_In.blockyanim",
          "HitboxType": "Door_Open_In",
          "InteractionHitboxType": "Door_Open_In_Interaction",
          "InteractionSoundEventId": "SFX_Door_Desert_Open",
          "InteractionHint": "server.interactionHints.closeDoor",
          "SoundOcclusionOpacity": 0.0
        },
        "OpenDoorOut": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_Out.blockyanim",
          "HitboxType": "Door_Open_Out",
          "InteractionHitboxType": "Door_Open_Out_Interaction",
          "InteractionSoundEventId": "SFX_Door_Desert_Open",
          "InteractionHint": "server.interactionHints.closeDoor",
          "SoundOcclusionOpacity": 0.0
        },
        "CloseDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_In.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Desert_Close"
        },
        "CloseDoorOut": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close_Out.blockyanim",
          "InteractionSoundEventId": "SFX_Door_Desert_Close"
        },
        "DoorBlocked": {}
      }
    },
    "Interactions": {
      "Use": "Door"
    },
    "ConnectedBlockRuleSet": {
      "Type": "CustomTemplate",
      "TemplateShapeAssetId": "DoorConnectedBlockTemplate",
      "TemplateShapeBlockPatterns": { "Default": "Furniture_Desert_Door" }
    }
  }
}
```
*(from `Furniture_Desert_Door.json`. The `Use` interaction is the shipped `Door` interaction — there
is no `Door_Toggle`. `DoorBlocked` is an empty state the engine selects when the swing is obstructed.)*

### Roof/Corner State Example

Blocks with connected states use shape-based state selection; the `Roof` rule set picks the state by
shape name and the `State.Definitions` supply the per-shape model and hitbox:

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Blocks/Structures/Roofs/Dev_Roof_Steep.blockymodel",
    "HitboxType": "Stairs_Steep",
    "ConnectedBlockRuleSet": {
      "Type": "Roof",
      "MaterialName": "Roof_Steep",
      "Regular": {
        "Straight": { "State": "default" },
        "Corner_Right": { "State": "Corner_Right" },
        "Corner_Left": { "State": "Corner_Left" },
        "Inverted_Corner_Right": { "State": "Inverted_Corner_Right" },
        "Inverted_Corner_Left": { "State": "Inverted_Corner_Left" }
      }
    },
    "State": {
      "Definitions": {
        "Corner_Right": {
          "CustomModel": "Blocks/Structures/Roofs/Dev_Roof_Steep_Corner_Right.blockymodel",
          "HitboxType": "Stairs_Corner_Steep_Right",
          "FlipType": "Orthogonal",
          "Supporting": { "Down": [ {} ] }
        },
        "Inverted_Corner_Right": {
          "CustomModel": "Blocks/Structures/Roofs/Dev_Roof_Steep_Corner_Inverted_Right.blockymodel",
          "HitboxType": "Roof_Corner_Steep_Inverted_Right",
          "FlipType": "Orthogonal",
          "Supporting": { "Down": [ {} ] }
        }
      }
    }
  }
}
```
*(abridged from `Build_White_Roof_Steep.json` — the real file also defines `Corner_Left` and
`Inverted_Corner_Left`. `FlipType` values are `Orthogonal` / `Symmetric`, parsed case-insensitively
against the `BlockFlipType` enum's `ORTHOGONAL` / `SYMMETRIC`; there is no `MirrorX`.)*

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

244 hitbox assets ship. A representative slice:

| Hitbox | Description |
|--------|-------------|
| `Full` | Full cube. The engine default (`BlockBoundingBoxes.DEFAULT`, id `0`) — it has no `.json` file; a block that omits `HitboxType` gets it |
| `Block_Half` / `Block_Quarter` / `Block_Flat` | Slab, quarter-height, carpet/rug height (also `Block_One_Eighth`, `Block_Three_Eighth`, `Block_Five_Eighth`, `Block_Seven_Eighth`, `Block_Three_Quarter`, `Block_Five_Quarter`) |
| `Block_Vertical_Half`, `Block_Vertical_Quarter`, … | The same slice thicknesses on a vertical axis |
| `Door` | Closed door collision (`Door_Medium`, `Door_Large`, `Door_Kweebec`, … for the other sizes) |
| `Door_Open_In` / `Door_Open_Out` | Door swung inward / outward, each with a `_Interaction` companion used as `InteractionHitboxType` |
| `Chest_Small` / `Chest_Large` | Chest closed (`Chest_Small_Open` / `Chest_Large_Open` while open) |
| `Fence` / `Fence_Thin` / `Fence_Thick` / `Fence_Corner` / `Fence_Gate` | Fence posts, corners and gates |
| `Stairs` | Stair step collision (`Stairs_Steep`, `Stairs_Shallow`, `Stairs_Flat`, `Stairs_Thin`, and `Stairs_Corner_*` / `Stairs_Inverted_Corner_*`) |
| `Roof_Corner_Steep_Inverted_Left`, `Roof_Corner_Shallow_Right`, … | Roof corner pieces |
| `Chair` / `Furniture_Stool` | Seating |

(There is no `Block_Full` or `Wall` hitbox asset — a full cube is `Full`, and walls/fences use the
`Fence*` set.)

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

`BlockSoundSet.CODEC` declares two keys, plus the `Parent` inheritance every asset codec supports:

| Property | Type | Description |
|----------|------|-------------|
| `SoundEvents` | object | Map of `BlockSoundEvent` → sound-event id. **The events do not sit at the top level.** |
| `MoveInRepeatRange` | `FloatRange` | Retrigger interval for the repeating `MoveIn` sound (no shipped set uses it) |
| `Parent` | string | Inherit another sound set and override selected events (19 of the 57 shipped sets do this) |

### Sound Event Types

The `SoundEvents` keys are the `BlockSoundEvent` enum — nine values, all of them:

| Event | Description |
|-------|-------------|
| `Walk` | Footstep sounds |
| `Land` | Landing after fall |
| `Hit` | Block being damaged |
| `Break` | Block destroyed |
| `Build` | Block placed |
| `Harvest` | Block harvested rather than broken |
| `Clone` | Block picked/cloned (creative) |
| `MoveIn` | Entity enters the block (fluids) |
| `MoveOut` | Entity exits the block (fluids) |

### Example Sound Set

```json
{
  "SoundEvents": {
    "Walk": "SFX_Stone_Walk",
    "Land": "SFX_Stone_Land",
    "Hit": "SFX_Stone_Hit",
    "Break": "SFX_Stone_Break",
    "Build": "SFX_Default_Build",
    "Harvest": "SFX_Stone_Harvest"
  }
}
```
*(`Server/Item/Block/Sounds/Stone.json`, verbatim)*

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

A particle set nests its events under `Particles`, and may also set defaults for how those particles
are emitted (`BlockParticleSet.CODEC`):

| Property | Type | Description |
|----------|------|-------------|
| `Particles` | object | Map of `BlockParticleEvent` → particle-system id. **The events do not sit at the top level.** |
| `Color` / `Scale` / `PositionOffset` / `RotationOffset` | — | Emission defaults applied to the set's particles |

### Particle Event Types

The `Particles` keys are the `BlockParticleEvent` enum — ten values, all of them:

| Event | Description |
|-------|-------------|
| `Walk` | Walking on the block |
| `Run` | Running on the block |
| `Sprint` | Sprinting on the block |
| `Hit` | Block being damaged |
| `Break` | Block destroyed |
| `Build` | Block placed |
| `SoftLand` | Light landing |
| `HardLand` | Heavy landing |
| `Physics` | Physics interactions |
| `MoveOut` | Entity exits the block |

### Example Particle Set

```json
{
  "Particles": {
    "Hit": "Block_Hit_Stone",
    "Break": "Block_Break_Stone",
    "Sprint": "Block_Sprint_Stone",
    "SoftLand": "Block_Land_Soft_Stone",
    "HardLand": "Block_Land_Hard_Stone",
    "Build": "Block_Build_Generic_Dust"
  }
}
```
*(`Server/Item/Block/Particles/Stone.json`, verbatim)*

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

### Particle Set IDs

All 30 shipped sets: `Clay`, `Crystal`, `Dirt`, `Dust`, `Flower`, `Glass`, `GlassEmpty`,
`GlassEmptySmall`, `GlassMagic`, `GlassPoison`, `GlassSmall`, `Grass`, `Grass_Earth`, `Ice`, `Lava`,
`Leaves`, `Leaves_Branches`, `Leaves_Fir`, `Leaves_Fir_Snow`, `Leaves_Round`, `Leaves_Sharp`,
`Metal`, `Mud`, `Ore`, `Sand`, `Snow`, `Stone`, `Tar`, `Water`, `Wood`.

(The leaf sets are named `Leaves*` — there is no `Leaf`.)

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

`BlockType.Interactions` is a map keyed by [`InteractionType`](interactions.md#interactiontype-enum);
a value is either a nested-interaction id or an inline interaction object. The keys shipped blocks
use, with their usage counts in 0.6.3:

| Slot | Trigger | Uses | Description |
|------|---------|------|-------------|
| `Use` | Interact (F) | 205 | Opening, seating, toggling |
| `CollisionEnter` | Entity enters the block | 20 | Damage/effect on stepping in |
| `Collision` | Entity overlapping the block | 19 | Continuous physics response |
| `Primary` | Left click | 16 | Gate or replace the break |
| `OnBreak` | Block broken | 1 | 0.6.3+ — fired by `BlockHarvestUtils.fireOnBreakInteraction` |
| `OnBreakImpact` | Break impact resolved | 1 | 0.6.3+ — queued by `BlockHarvestUtils.queueOnBreakImpactInteraction` |

### Example: Interactive Block

```json
{
  "BlockType": {
    "Interactions": {
      "Primary": "Break_Treasure_Container",
      "Use": "Open_Container"
    }
  }
}
```

(`Break_Treasure_Container` and `Open_Container` are shipped interaction ids under
`Server/Item/Interactions/`; the other shipped `Primary` value is `Check_Can_Break_Respawn`, used by
beds. There is no `Break_Container`.)

### BlockEntity Components

Some blocks have associated entity components:

These are `ChunkStore` components nested under `BlockType.BlockEntity.Components`, keyed by their
registered name. The names shipped blocks actually use, with counts:

| Component | Usage |
|-----------|-------|
| `FarmingBlock` (70) | Crops and growth stages |
| `ItemContainerBlock` (47) | Storage blocks — carries the `Capacity` |
| `BenchBlock` (16) / `ProcessingBenchBlock` (4) | Crafting and processing stations |
| `RespawnBlock` (15) | Bed spawn point |
| `MusicEmitterBlock` (4) / `MusicPlayerBlock` (1) | Ambient music sources |
| `SpawnMarkerBlock` (2) / `BlockSpawner` (2) / `Coop` (1) | Entity spawners |
| `LaunchPad`, `Teleporter`, `Portal`, `TilledSoil`, `TrackedPlacement`, `InstanceConfig`, `BlockMapMarker`, `PrefabSpawner`, `TreasureChest` | One shipped block each |

(There is no `Container` or `CraftingBench` component key — those are `ItemContainerBlock` and
`BenchBlock`.)

See [Items - Blocks](items-blocks.md) for detailed BlockEntity documentation, and [Custom Block-Entity Components](blocks-java-api.md#custom-block-entity-components) below for a verified end-to-end recipe (define your own component, tick it, spawn entities from it, and persist its state).

---

## Block Type Lists

Block type lists categorize blocks for world generation and game systems.

**Location:** `Server/BlockTypeList/<Category>.json`

The asset class is `BlockTypeListAsset`; a block points at one with `BlockType.BlockListAssetId`.

### Available Lists

All 13 shipped lists:

| List | Description |
|------|-------------|
| `Soils.json` | Dirt, grass and leaf-litter variants (16 blocks) |
| `Rock.json` | Stone types (16) |
| `Gravel.json` | Gravel blocks |
| `Ores.json` | Ore blocks |
| `TreeWood.json` / `TreeLeaves.json` / `TreeWoodAndLeaves.json` | Wood, leaves, and the two combined |
| `PlantsAndTrees.json` | Plants and trees (620) |
| `AllScatter.json` | All scatter blocks |
| `PlantScatter.json` | Plant scatter blocks |
| `Snow.json` | Snow blocks |
| `Fluids.json` | Fluid blocks |
| `Empty.json` | Empty/air blocks |

### List Structure

The single key is `Blocks` — an array of block type keys:

```json
{
  "Blocks": [
    "Soil_Leaves",
    "Soil_Sand",
    "Soil_Dirt",
    "Soil_Grass"
  ]
}
```
*(abridged from `Soils.json`. There is no `Types` key.)*

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
    "Opacity": "Transparent",
    "CustomModel": "Blocks/Decorative_Sets/Human_Ruins/Chair.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Blocks/Decorative_Sets/Human_Ruins/Chair_Texture.png", "Weight": 1 }
    ],
    "HitboxType": "Chair",
    "VariantRotation": "NESW",
    "Support": { "Down": [ { "FaceType": "Full" } ] },
    "Seats": [ { "Offset": { "X": 0, "Y": 0.01, "Z": 0.15 }, "Yaw": 0 } ],
    "Interactions": { "Use": "Block_Seat" }
  }
}
```
*(abridged from `Furniture_Human_Ruins_Chair.json`. A `Model` block sets `Opacity: "Transparent"`;
`CustomModelTexture` paths are model-relative textures under `Common/`, not `BlockTextures/` cube
textures.)*

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

Sets the override on the block the caller is looking at (max 10 blocks, via
`TargetUtil.getTargetBlock`). Permission group `hytale:WorldEditor`.

> The command is stricter than the API: when `canBlockAnimate` is `false` it sends
> `server.commands.blockAnimationSpeed.notAnimated` and **returns without applying anything**.
> The shipped en-US string for that key reads *"Set the speed at {position}, but this block has no
> model animation"*, which suggests it did apply — it did not. Calling
> `setBlockAnimationSpeed(...)` directly does store the override on a non-animating block (it never
> consults `canBlockAnimate`); only the command refuses.

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
  "Categories": ["Furniture.Furniture"],
  "MaxStack": 5,
  "BlockType": {
    "DrawType": "Model",
    "Opacity": "Transparent",
    "CustomModel": "Blocks/Furniture/My_Furniture.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Blocks/Furniture/My_Furniture_Texture.png", "Weight": 1 }
    ],
    "HitboxType": "Chair",
    "VariantRotation": "NESW",
    "Support": { "Down": [ { "FaceType": "Full" } ] },
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
  "Categories": ["Furniture.Doors"],
  "BlockType": {
    "DrawType": "Model",
    "Opacity": "Transparent",
    "CustomModel": "Blocks/Doors/My_Door.blockymodel",
    "HitboxType": "Door",
    "VariantRotation": "NESW",
    "IsDoor": true,
    "State": {
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
        },
        "DoorBlocked": {}
      }
    },
    "Interactions": {
      "Use": "Door"
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
  "Categories": ["Furniture.Containers"],
  "BlockType": {
    "DrawType": "Model",
    "Opacity": "Transparent",
    "CustomModel": "Blocks/Containers/My_Chest.blockymodel",
    "HitboxType": "Chest_Small",
    "VariantRotation": "NESW",
    "Support": { "Down": [ { "FaceType": "Full" } ] },
    "Supporting": { "Up": [ { "FaceType": "Full" } ] },
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
    },
    "BlockEntity": {
      "Components": {
        "ItemContainerBlock": { "Capacity": 27 }
      }
    },
    "Interactions": {
      "Use": "Open_Container"
    },
    "InteractionHint": "server.interactionHints.openDoor",
    "BlockSoundSetId": "Wood",
    "Gathering": {
      "Breaking": {
        "GatherType": "Woods",
        "DropList": {
          "Container": {
            "Type": "Single",
            "Item": { "ItemId": "My_Chest", "QuantityMin": 1, "QuantityMax": 1 }
          }
        }
      }
    }
  }
}
```
*(Modelled on `Furniture_Kweebec_Chest_Large.json`. The slot count is on the `ItemContainerBlock`
block-entity component, not on `State`, and `DropList` is a drop-table id or an inline
`{ "Container": … }` object — never an array.)*

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
    "ParticleColor": "#667142"
  }
}
```

*(Illustrative: 2,159 shipped item files use `Parent`, but the real `Rock_Stone_Mossy.json` is
standalone — it repeats the whole `BlockType`. `Parent` inheritance is an [item](items.md) feature and
merges the parent's `BlockType` key-by-key, so a child only restates what it changes.)*

---

## Notes
- Block states persist additional data per-block instance
- The Java-side notes that used to sit here — chunk accessors, chunk-load checks, async loading, ECS block events and shape iteration — moved with their subject to [Blocks Java API](blocks-java-api.md#notes)

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the block system (verified against `HytaleServer.jar`).

- **`One and only one of BlockTag or ItemId must be set!`** → a config entry set both `BlockTag` and `ItemId`, or neither. Fix: specify exactly one of the two.
- **`Block entry cannot be empty`** → a block list/entry was left blank. Fix: provide a non-empty block type key.
- **`Cannot select from empty blocks list`** → a block-selection operation ran against an empty list. Fix: ensure the list contains at least one block before selecting.
- **Symptom:** a block listed in a `Server/BlockTypeList/<Category>.json` `Types[]` array is dropped at load (the loader reports it `contains invalid block … skipping`) → the key does not resolve to a real `BlockType`. Fix: use exact, correctly-cased block type keys (see [Block Type Lists](#block-type-lists)).

---

## Related Documentation

- [Blocks Java API](blocks-java-api.md) - `BlockType`, block events, world block access
- [Connected Blocks](blocks-connected.md) - Connected and patterned rule sets
- [Items](items.md) - Item system and inheritance
- [Block Items](items-blocks.md) - Furniture, containers, crafting benches
- [Interactions](interactions.md) - Block use and break interactions
- [Components](components.md) - ECS components including BlockEntity
- [Events](events.md) - Block-related events
- [Drops](drops.md) - Drop tables and loot configuration

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
