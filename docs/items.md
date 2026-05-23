# Item Definitions

Item definitions configure every item in Hytale, from weapons and armor to food, potions, and placeable blocks. Items use a template-based inheritance system where child items inherit properties from parent templates and override specific values.

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Weapons](items-weapons.md) | `items-weapons.md` | Swords, daggers, bows, shields, maces (108 items) |
| [Tools](items-tools.md) | `items-tools.md` | Pickaxes, hatchets, shovels, farming tools (40+ items) |
| [Consumables](items-consumables.md) | `items-consumables.md` | Food, potions, healing items (60+ items) |
| [Blocks](items-blocks.md) | `items-blocks.md` | Furniture, lighting, doors, containers, benches (200+ items) |
| [Block System](blocks.md) | `blocks.md` | Block rendering, hitboxes, sounds, particles, fluids |
| [Crafting](items-crafting.md) | `items-crafting.md` | Crafting benches, recipes, processing, tier system |

**Future documentation:**
- `items-armor.md` - Armor sets (coming soon)
- `items-resources.md` - Ingredients, ores, crops (coming soon)

---

## Common Properties

All items support these core properties:

| Property | Type | Description |
|----------|------|-------------|
| `Parent` | string | Template to inherit from (e.g., `"Template_Weapon_Sword"`) |
| `TranslationProperties` | object | Localization keys for name/description |
| `Quality` | string | Rarity tier affecting UI color and sorting |
| `ItemLevel` | int | Power level for sorting and progression |
| `Categories` | array | UI categories for creative library (e.g., `["Items.Weapons"]`) |
| `Icon` | string | Path to inventory icon image |
| `Model` | string | Path to 3D model file (`.blockymodel`) |
| `Texture` | string | Path to texture file (`.png`) |
| `Scale` | float | World render scale multiplier (default: 1.0) |
| `PlayerAnimationsId` | string/object | Animation set for player when holding item |
| `BlockType` | object | Block configuration when item is placed (see [Block Items](items-blocks.md) and [Block System](blocks.md)) |
| `Tags` | object | Classification tags for filtering |
| `MaxStack` | int | Maximum stack size (default: 1 for weapons/tools) |
| `Consumable` | boolean | Whether the item is consumed on use |
| `Utility` | object | Utility-slot flag (`Compatible` or `Usable` boolean) |
| `MaxDurability` | int | Maximum durability points |
| `DurabilityLossOnHit` | float | Durability lost per use |

### TranslationProperties

Configures localization keys:

```json
{
  "TranslationProperties": {
    "Name": "server.items.Weapon_Sword_Iron.name"
  }
}
```

### IconProperties

Controls how the item renders in the inventory:

```json
{
  "IconProperties": {
    "Scale": 0.35,
    "Translation": [-22, -22],
    "Rotation": [45, 90, 0]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Scale` | float | Size multiplier for icon rendering |
| `Translation` | [x, y] | Pixel offset in icon space |
| `Rotation` | [pitch, yaw, roll] | 3D rotation angles in degrees |

### PlayerAnimationsId

Controls which animation set the player uses when holding or using the item. Can be a string referencing a predefined animation set, or an object for custom overrides.

**String format** (common values):

| Category | Values |
|----------|--------|
| Generic | `Item`, `Block`, `Stick`, `Default` |
| Weapons | `Sword`, `Daggers`, `Shield`, `Battleaxe`, `Bow`, `Mace`, `Crossbow` |
| Tools | `Pickaxe`, `Hatchet`, `Shovel`, `Hoe`, `Hammer`, `Shears`, `WateringCan`, `Sickle` |

```json
{
  "PlayerAnimationsId": "Sword"
}
```

**Object format** for custom animation overrides:

```json
{
  "PlayerAnimationsId": {
    "Parent": "Sword",
    "Animations": {
      "Idle": "Custom_Sword_Idle",
      "Walk": "Custom_Sword_Walk"
    }
  }
}
```

### Scale

World render scale multiplier when the item is held or dropped. This is separate from `IconProperties.Scale` (inventory icon) and `BlockType.CustomModelScale` (placed block model).

```json
{
  "Scale": 1.2
}
```

| Value | Effect |
|-------|--------|
| `1.0` | Default size |
| `< 1.0` | Smaller than default |
| `> 1.0` | Larger than default |

### BlockType

Configures block behavior when an item is placed in the world. This property transforms an item into a placeable block with optional interactions, containers, and crafting functionality.

For complete documentation, see [Block Items](items-blocks.md).

```json
{
  "BlockType": {
    "Type": "Furniture",
    "ModelId": "Chair_Wood",
    "SubType": "Seat"
  }
}
```

### Utility

Marks how an item behaves with the player's utility slot. The `Utility` object holds a single boolean flag.

```json
{
  "Utility": {
    "Compatible": true
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Compatible` | boolean | Item may be placed in the utility slot (82 items use this) |
| `Usable` | boolean | Item can be activated/used from the utility slot, e.g. torches and candles (27 items use this) |

Either `Compatible` or `Usable` is present; both are plain booleans.

---

## Quality System

Quality determines an item's rarity tier, affecting its UI border color and sort order:

| Quality | Description | Usage |
|---------|-------------|-------|
| `Template` | Base templates (not obtainable) | Parent items for inheritance |
| `Common` | White border | Basic crafted items |
| `Uncommon` | Green border | Standard equipment |
| `Rare` | Blue border | Advanced equipment |
| `Epic` | Purple border | High-tier equipment |
| `Legendary` | Orange border | Top-tier unique items |
| `Technical` | Hidden from players | System/filter items |
| `Developer` | Debug only | Development tools |
| `Debug` | Debug only | Testing items |
| `Tool` | Editor tools | Creative mode tools |

### Example

```json
{
  "Parent": "Template_Weapon_Sword",
  "Quality": "Rare",
  "ItemLevel": 40
}
```

---

## Inheritance System

Items use a `Parent` field to inherit all properties from a template, then override specific values:

### Template (Parent)

```json
{
  "TranslationProperties": {
    "Name": "server.items.Template_Weapon_Sword.name"
  },
  "Quality": "Template",
  "ItemLevel": 15,
  "PlayerAnimationsId": "Sword",
  "Interactions": {
    "Primary": "Root_Weapon_Sword_Primary",
    "Secondary": "Root_Weapon_Sword_Secondary_Guard",
    "Ability1": "Root_Weapon_Sword_Signature_Vortexstrike"
  },
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Sword"]
  },
  "MaxDurability": 80,
  "DurabilityLossOnHit": 0.21
}
```

### Child Item (Inherits & Overrides)

```json
{
  "Parent": "Template_Weapon_Sword",
  "TranslationProperties": {
    "Name": "server.items.Weapon_Sword_Iron.name"
  },
  "Model": "Items/Weapons/Sword/Iron.blockymodel",
  "Texture": "Items/Weapons/Sword/Iron_Texture.png",
  "Icon": "Icons/ItemsGenerated/Weapon_Sword_Iron.png",
  "Quality": "Uncommon",
  "ItemLevel": 20,
  "MaxDurability": 120,
  "InteractionVars": {
    "Swing_Left_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Left_Damage",
        "DamageCalculator": {
          "BaseDamage": { "Physical": 9 }
        }
      }]
    }
  }
}
```

The child item:
- Inherits `PlayerAnimationsId`, `Interactions`, `Tags`, `DurabilityLossOnHit` from template
- Overrides `Quality`, `ItemLevel`, `MaxDurability`, visual properties
- Adds `InteractionVars` to customize damage values

---

## InteractionVars System

`InteractionVars` allows child items to customize behavior defined in parent interactions without duplicating the entire interaction chain. The template's interactions reference variables by name, and each item provides its own values.

### How It Works

1. **Template defines interactions** that reference variable slots:
   ```json
   {
     "Interactions": {
       "Primary": "Root_Weapon_Sword_Primary"
     }
   }
   ```

2. **Root interaction chains** use `Replace` to inject item-specific values:
   ```json
   {
     "Type": "Replace",
     "Var": "Swing_Left_Damage"
   }
   ```

3. **Child items provide values** via `InteractionVars`:
   ```json
   {
     "InteractionVars": {
       "Swing_Left_Damage": {
         "Interactions": [{
           "Parent": "Weapon_Sword_Primary_Swing_Left_Damage",
           "DamageCalculator": {
             "BaseDamage": { "Physical": 9 }
           }
         }]
       }
     }
   }
   ```

### Common InteractionVar Patterns

**Damage customization:**
```json
{
  "Swing_Left_Damage": {
    "Interactions": [{
      "Parent": "Weapon_Sword_Primary_Swing_Left_Damage",
      "DamageCalculator": {
        "BaseDamage": { "Physical": 9 }
      },
      "DamageEffects": {
        "WorldSoundEventId": "SFX_Sword_T2_Impact",
        "LocalSoundEventId": "SFX_Sword_T2_Impact"
      }
    }]
  }
}
```

**Guard/blocking customization:**
```json
{
  "Guard_Wield": {
    "Interactions": [{
      "Parent": "Weapon_Sword_Secondary_Guard_Wield",
      "StaminaCost": {
        "Value": 10,
        "CostType": "Damage"
      }
    }]
  }
}
```

**Consumable effects:**
```json
{
  "Effect": {
    "Interactions": [{
      "Type": "ApplyEffect",
      "EffectId": "Food_Health_Regen_Small"
    }]
  }
}
```

---

## Tags System

Tags categorize items for filtering and matching:

```json
{
  "Tags": {
    "Type": ["Weapon"],
    "Family": ["Sword"]
  }
}
```

| Tag Category | Values | Usage |
|--------------|--------|-------|
| `Type` | `Weapon`, `Food`, `Potion`, `Tool`, `Armor` | Primary classification |
| `Family` | `Sword`, `Bow`, `Shield`, `Dagger`, `Mace` | Weapon family |

Tags are used by:
- Interaction conditions (e.g., only apply effect to weapons)
- Entity matchers in combat
- Recipe filters
- UI filtering

---

## Categories System

Categories organize items in the Creative Library UI:

```json
{
  "Categories": ["Items.Weapons"]
}
```

**Category hierarchy** (declared in `Server/Item/Category/CreativeLibrary/Items.json`):

| Category ID | Display Name |
|-------------|--------------|
| `Items.Tools` | Tools |
| `Items.Weapons` | Weapons |
| `Items.Armors` | Armors |
| `Items.Foods` | Foods |
| `Items.Potions` | Potions |
| `Items.Recipes` | Recipes |
| `Items.Ingredients` | Ingredients |

Additional `Items.*` category IDs appear directly on item files even though they are not listed as children in `Items.json`:

| Category ID | Items Using It |
|-------------|----------------|
| `Items.Utility` | 3 |
| `Items.Consumables` | 1 |
| `Items.Debug` | 3 |

---

## ResourceTypes System

ResourceTypes group items for recipe input flexibility. Instead of requiring a specific item, recipes can accept any item of a ResourceType.

**Location:** `Server/Item/ResourceTypes/*.json`

### Example ResourceType

```json
{
  "Id": "Foods"
}
```

### Using in Items

Items declare membership via `ResourceTypes`:

```json
{
  "ResourceTypes": [
    { "Id": "Foods" }
  ]
}
```

### Using in Recipes

Recipes accept ResourceTypes as input:

```json
{
  "Recipe": {
    "Input": [
      {
        "ResourceTypeId": "Wood_Trunk",
        "Quantity": 4
      }
    ]
  }
}
```

**Common ResourceTypes:**
- `Foods`, `Fruits`, `Vegetables`, `Meats`
- `Wood_Trunk`, `Wood_All`, `Wood_Blackwood`
- `Rock`, `Rock_Stone`, `Rock_Sandstone`
- `Metal_Bars`, `Salvage_Iron`, `Salvage_Copper`
- `Fish`, `Fish_Common`, `Fish_Rare`

---

## Interactions Property

Defines what happens when the player uses the item:

```json
{
  "Interactions": {
    "Primary": "Root_Weapon_Sword_Primary",
    "Secondary": "Root_Weapon_Sword_Secondary_Guard",
    "Ability1": "Root_Weapon_Sword_Signature_Vortexstrike"
  }
}
```

| Slot | Input | Description |
|------|-------|-------------|
| `Primary` | Left click | Main attack/action |
| `Secondary` | Right click | Block/guard/alternate action |
| `Ability1` | Q key | Signature ability |
| `Ability3` | R key | Reload/special action |
| `SwapFrom` | - | Triggered when switching away from item |

See [Interactions API](interactions.md) for full interaction documentation.

---

## Weapon Property

Weapons have additional configuration in the `Weapon` object:

```json
{
  "Weapon": {
    "EntityStatsToClear": ["SignatureEnergy"],
    "StatModifiers": {
      "SignatureEnergy": [{
        "Amount": 20,
        "CalculationType": "Additive"
      }]
    },
    "RenderDualWielded": true
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `EntityStatsToClear` | array | Stats to reset when equipping |
| `StatModifiers` | object | Stats granted while wielding |
| `RenderDualWielded` | boolean | Show item in both hands (daggers) |

---

## Recipe Property

Defines crafting requirements:

```json
{
  "Recipe": {
    "TimeSeconds": 3.5,
    "KnowledgeRequired": false,
    "Input": [
      { "ItemId": "Ingredient_Bar_Iron", "Quantity": 6 },
      { "ItemId": "Ingredient_Leather_Light", "Quantity": 3 },
      { "ResourceTypeId": "Wood_Trunk", "Quantity": 4 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Weapon_Sword"],
      "Id": "Weapon_Bench",
      "RequiredTierLevel": 1
    }]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `TimeSeconds` | float | Crafting duration |
| `KnowledgeRequired` | boolean | Requires recipe unlock |
| `Input` | array | Required ingredients |
| `Input[].ItemId` | string | Specific item required |
| `Input[].ResourceTypeId` | string | Any item of this type accepted |
| `Input[].Quantity` | int | Amount required |
| `BenchRequirement` | array | Required crafting station |
| `RequiredTierLevel` | int | Minimum bench tier (1-3) |

---

## ItemAppearanceConditions

Changes item appearance based on entity stats (e.g., signature ability ready):

```json
{
  "ItemAppearanceConditions": {
    "SignatureEnergy": [{
      "Condition": [100, 100],
      "ConditionValueType": "Percent",
      "Particles": [{
        "SystemId": "Sword_Signature_Ready",
        "TargetNodeName": "Handle",
        "TargetEntityPart": "PrimaryItem"
      }],
      "ModelVFXId": "Sword_Signature_Status"
    }]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Condition` | [min, max] | Stat range to trigger (e.g., `[100, 100]` = exactly 100%) |
| `ConditionValueType` | string | `"Percent"` or absolute value |
| `Particles` | array | Particle effects to display |
| `Model` | string | Alternative model to use |
| `Texture` | string | Alternative texture to use |
| `ModelVFXId` | string | VFX shader to apply |
| `LocalSoundEventId` | string | Looping sound for player |
| `WorldSoundEventId` | string | Looping sound for world |

---

## Quick Start Examples

### Basic Weapon

```json
{
  "Parent": "Template_Weapon_Sword",
  "TranslationProperties": {
    "Name": "server.items.My_Custom_Sword.name"
  },
  "Model": "Items/Weapons/Sword/Iron.blockymodel",
  "Texture": "Items/Weapons/Sword/Iron_Texture.png",
  "Icon": "Icons/ItemsGenerated/Weapon_Sword_Iron.png",
  "Quality": "Uncommon",
  "ItemLevel": 25,
  "MaxDurability": 100,
  "InteractionVars": {
    "Swing_Left_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Left_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 12 } }
      }]
    },
    "Swing_Right_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Right_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 13 } }
      }]
    },
    "Swing_Down_Damage": {
      "Interactions": [{
        "Parent": "Weapon_Sword_Primary_Swing_Down_Damage",
        "DamageCalculator": { "BaseDamage": { "Physical": 22 } }
      }]
    }
  }
}
```

### Basic Food

```json
{
  "Parent": "Template_Food",
  "TranslationProperties": {
    "Name": "server.items.My_Custom_Food.name"
  },
  "Icon": "Icons/ItemsGenerated/Plant_Crop_Corn.png",
  "Quality": "Common",
  "MaxStack": 25,
  "InteractionVars": {
    "Effect": {
      "Interactions": [{
        "Type": "ApplyEffect",
        "EffectId": "Food_Health_Regen_Medium"
      }]
    }
  }
}
```

---

## Related Documentation

- [Interactions API](interactions.md) - Combat, effects, and item behaviors
- [Effects & Stats](effects-stats.md) - Status effects and stat modifiers
- [Weapons Reference](items-weapons.md) - All weapon templates and variants
- [Tools Reference](items-tools.md) - Gathering and farming tools
- [Consumables Reference](items-consumables.md) - Food and potions
