# Block Definitions

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item` · **Verified against build-12**

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
| `Server/Item/Items/<Category>/` | Block item definitions (449 files) |
| `Server/Item/Block/Fluids/` | Fluid block definitions |
| `Server/Item/Block/Hitboxes/` | Collision shape definitions |
| `Server/Item/Block/Sounds/` | Sound set mappings (76 files) |
| `Server/Item/Block/Particles/` | Particle set mappings (50+ files) |
| `Server/Item/Block/BreakingDecals/` | Breaking texture effects |
| `Server/Item/Block/FluidFX/` | Fluid visual effects |
| `Server/Item/CustomConnectedBlockTemplates/` | Connected block rules (11 templates) |
| `Server/BlockTypeList/` | Block categorization lists (12 files) |
| `Common/Blocks/` | Visual models and animations (1,040 files) |

### Block Categories

Blocks are organized into categories for the Creative Library:

| Category | Examples |
|----------|----------|
| `Blocks.Rocks` | Stone, sandstone, marble, ores |
| `Blocks.Soils` | Dirt, grass, sand, gravel |
| `Blocks.Wood` | Planks, logs, bark |
| `Blocks.Cloth` | Wool, fabric blocks |
| `Blocks.Furniture` | Chairs, tables, beds |
| `Blocks.Containers` | Chests, barrels, crates |
| `Blocks.Lighting` | Torches, lanterns, candles |
| `Blocks.Plants` | Flowers, crops, trees |

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
| `MaxStack` | int | Inventory stack limit (default: 10 for blocks) |
| `ItemSoundSetId` | string | Sound effects when handling item |
| `PlayerAnimationsId` | string | Player animation when placing |
| `BlockType` | object | Block-specific configuration |

### Example: Simple Block Item

```json
{
  "TranslationProperties": {
    "Name": "server.items.Rock_Stone.name"
  },
  "Icon": "Icons/ItemsGenerated/Rock_Stone.png",
  "Categories": ["Blocks.Rocks"],
  "Set": "Rock_Stone",
  "Tags": {
    "Type": ["Rock"],
    "Family": ["Stone"]
  },
  "MaxStack": 10,
  "PlayerAnimationsId": "Block",
  "ItemSoundSetId": "ISS_Items_Rock",
  "BlockType": {
    "Material": "Solid",
    "DrawType": "Cube",
    "Opacity": "Opaque",
    "Group": "Rock",
    "Textures": [
      { "Weight": 1, "All": "BlockTextures/Rock_Stone.png" }
    ],
    "BlockSoundSetId": "Stone",
    "BlockParticleSetId": "Rock",
    "ParticleColor": "#808080",
    "Gathering": {
      "Breaking": {
        "GatherType": "Rocks"
      }
    }
  }
}
```

---

## BlockType Properties

The `BlockType` object defines how a block renders, collides, and behaves in the world.

### Rendering Properties

| Property | Type | Description |
|----------|------|-------------|
| `DrawType` | string | Rendering mode: `"Cube"`, `"Model"` |
| `Material` | string | Physical type: `"Solid"`, `"Empty"` |
| `Opacity` | string | Visual transparency: `"Opaque"`, `"Transparent"` |
| `Group` | string | Block family for texture blending |
| `Textures` | array | Texture definitions with variants |
| `CustomModel` | string | Path to `.blockymodel` file |
| `CustomModelTexture` | array | Texture assignments for model |
| `CustomModelAnimation` | string | Path to `.blockyanim` file |
| `CustomModelScale` | float | Scale multiplier for model |
| `Light` | object | Light emission properties |

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
      "Top": "BlockTextures/Grass_Top.png",
      "Bottom": "BlockTextures/Dirt.png",
      "Side": "BlockTextures/Grass_Side.png"
    }
  ]
}
```

| Face Property | Description |
|---------------|-------------|
| `All` | Apply to all faces |
| `Top` | Top face (+Y) |
| `Bottom` | Bottom face (-Y) |
| `Side` | All side faces |
| `North`, `South`, `East`, `West` | Individual side faces |

### Light Emission

Blocks can emit colored light:

```json
{
  "Light": {
    "Color": [255, 200, 100],
    "Intensity": 15
  }
}
```

### Collision Properties

| Property | Type | Description |
|----------|------|-------------|
| `HitboxType` | string | Reference to hitbox definition |
| `Support` | string | Support requirements: `"Down"`, `"Up"`, `"All"` |

### Behavior Properties

| Property | Type | Description |
|----------|------|-------------|
| `Gathering` | object | Tool type and drop configuration |
| `VariantRotation` | string | Rotation support: `"NESW"` |
| `Flags` | object | Boolean flags (e.g., `IsUsable`) |
| `Interactions` | object | Primary, Use, Collision handlers |
| `State` | object | State machine configuration |
| `Ticker` | object | Automatic update behavior |

### Gathering Configuration

Defines what tool breaks the block and what it drops:

```json
{
  "Gathering": {
    "Breaking": {
      "GatherType": "Rocks",
      "DropList": [
        {
          "ItemId": "Rock_Stone",
          "Quantity": 1,
          "Chance": 1.0
        },
        {
          "ItemId": "Ingredient_Stone_Chip",
          "Quantity": [1, 3],
          "Chance": 0.25
        }
      ]
    }
  }
}
```

| GatherType | Tool Required |
|------------|---------------|
| `Rocks` | Pickaxe |
| `Woods` | Hatchet |
| `SoftBlocks` | Shovel |
| `Plants` | Hand/Sickle |
| `Ores` | Pickaxe |

### VariantRotation

Enables directional placement based on player facing:

```json
{
  "VariantRotation": "NESW"
}
```

| Value | Description |
|-------|-------------|
| `"NESW"` | 4 cardinal directions (North, East, South, West) |

### Flags

Boolean behavior flags:

```json
{
  "Flags": {
    "IsUsable": true
  }
}
```

| Flag | Description |
|------|-------------|
| `IsUsable` | Block responds to Use interaction |

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
    "Flags": { "IsUsable": true },
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
        "CloseDoor": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close.blockyanim",
          "HitboxType": "Door",
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

Connected blocks automatically select models and states based on neighboring blocks. 11 templates are available:

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

Reference the template in the block definition:

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "Wall"
    }
  }
}
```

### Template Structure

Templates define material connections and shape patterns:

```json
{
  "MaterialName": "Wall",
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

| Property | Type | Description |
|----------|------|-------------|
| `MaterialName` | string | Material identifier for connection matching |
| `ConnectsToOtherMaterials` | boolean | Connect to different material types |
| `DefaultShape` | string | Shape when no patterns match |
| `Shapes` | object | Map of shape names to pattern rules |
| `FaceTags` | object | Tags on each face for connection matching |
| `PatternsToMatchAnyOf` | array | Pattern rules for shape selection |

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
    "BlockParticleSetId": "Rock",
    "ParticleColor": "#808080"
  }
}
```

### Common Particle Set IDs

| ID | Effect Type |
|----|-------------|
| `Rock` | Stone chips |
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

```json
{
  "TranslationProperties": {
    "Name": "server.items.Water_Source.name"
  },
  "BlockType": {
    "Material": "Empty",
    "Opacity": "Transparent",
    "MaxFluidLevel": 1,
    "FluidFXId": "Water",
    "Effect": ["Water"],
    "Tags": {
      "Fluid": ["Water"]
    },
    "Ticker": {
      "CanDemote": true,
      "SpreadFluid": true,
      "Collisions": [
        {
          "FluidTag": "Lava",
          "Result": "Rock_Obsidian"
        }
      ]
    },
    "Interactions": {
      "Collision": "Fluid_Water_Collision"
    }
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

Controls automatic fluid behavior:

```json
{
  "Ticker": {
    "CanDemote": true,
    "SpreadFluid": true,
    "SpreadDelay": 5,
    "Collisions": [
      {
        "FluidTag": "Lava",
        "Result": "Rock_Obsidian"
      }
    ]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `CanDemote` | boolean | Fluid level can decrease |
| `SpreadFluid` | boolean | Fluid spreads to neighbors |
| `SpreadDelay` | int | Ticks between spread updates |
| `Collisions` | array | Fluid-to-fluid transformation rules |

### Fluid Collision Transformations

When fluids touch, they can transform into blocks:

| Water + | Result |
|---------|--------|
| Lava (source) | Obsidian |
| Lava (flowing) | Cobblestone |

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
    "Flags": { "IsUsable": true },
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

See [Items - Blocks](items-blocks.md) for detailed BlockEntity documentation.

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
    "Opacity": "Opaque",
    "Group": "Rock",
    "Textures": [
      { "Weight": 1, "All": "BlockTextures/My_Block.png" }
    ],
    "BlockSoundSetId": "Stone",
    "BlockParticleSetId": "Rock",
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
    "Flags": { "IsUsable": true },
    "State": {
      "Id": "door",
      "Definitions": {
        "OpenDoorIn": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Open_In.blockyanim",
          "HitboxType": "Door_Open_In",
          "InteractionSoundEventId": "SFX_Door_Wooden_Open"
        },
        "CloseDoor": {
          "CustomModelAnimation": "Blocks/Animations/Door/Door_Close.blockyanim",
          "HitboxType": "Door",
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
    "Flags": { "IsUsable": true },
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
            player.sendMessage(Message.raw("You used a block!"));
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
            player.sendMessage(Message.raw("You broke a block at " + pos.x + ", " + pos.y + ", " + pos.z));
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
                player.sendMessage(Message.raw("Cannot place blocks above y=100"));
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
> This is engine-internal infrastructure exposed publicly; no first-party content plugin in build-12 references it. The class/method surface above is verified against `HytaleServer.jar`, but the intended end-to-end authoring flow (how a custom block declares its max health and regen) is not exercised by any shipped plugin — treat the worked example as illustrative of the API shape, not a guaranteed recipe.

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

Backtick-quoted error strings below are the literal messages thrown by the build-12 block system (verified against `HytaleServer.jar`).

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
