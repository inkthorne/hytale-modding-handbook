# Consumable Items

**Doc type:** JSON asset format · **Assets:** `Server/Item`

> Part of the [Items API](items.md). For common item properties, see [Items Reference](items.md#common-properties).

## Quick Navigation

| Category | Template | Count | Description |
|----------|----------|-------|-------------|
| [Food](#food-system) | Template_Food, Template_Fruit | 30+ | Healing and stat buffs |
| [Potions](#potion-system) | Potion_Template | 30+ | Instant effects and transformations |

---

## Food System

Food items restore health and provide temporary buffs when consumed. The system uses timed consumption with charging mechanics.

### Template_Food

**Location:** `Server/Item/Items/Food/Template_Food.json`

Base template for all prepared food items (bread, pies, kebabs, salads).

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `MaxStack` | 25 |
| `Consumable` | true |
| `Categories` | Items.Foods |

#### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Secondary` | Root_Secondary_Consume_Food_T1 | Timed consumption |

Food uses the `Secondary` (right-click) slot for consumption, leaving `Primary` available for other actions.

#### Tags

```json
{
  "Tags": {
    "Type": ["Food"]
  }
}
```

#### InteractionVars

Child food items customize these variables:

| Variable | Purpose |
|----------|---------|
| `Consume_Charge` | Charging configuration (duration, movement speed) |
| `Effect` | ApplyEffect interaction for healing/buffs |
| `ConsumeSFX` | Sound during consumption |
| `ConsumedSFX` | Sound when consumption completes |

#### Template InteractionVars

```json
{
  "InteractionVars": {
    "Consume_Charge": {
      "Interactions": [{
        "Parent": "Consume_Charge_Food_T1_Inner",
        "Effects": {
          "ItemAnimationId": "Consume"
        }
      }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "ApplyEffect",
        "EffectId": "Food_Health_Regen_Small"
      }]
    },
    "ConsumeSFX": {
      "Interactions": [{
        "Parent": "Consume_SFX",
        "Effects": {
          "LocalSoundEventId": "SFX_Consume_Bread_Local"
        }
      }]
    },
    "ConsumedSFX": {
      "Interactions": [{
        "Parent": "Consumed_SFX",
        "Effects": {
          "LocalSoundEventId": "SFX_Consume_Bread_Local"
        }
      }]
    }
  }
}
```

Each `InteractionVar` extends a shared parent interaction (e.g. `Consume_Charge_Food_T1_Inner`, `Consume_SFX`, `Consumed_SFX`) via the `Parent` field rather than declaring a `Type`.

---

### Template_Fruit

**Location:** `Server/Item/Items/Plant/Fruit/Template_Fruit.json`

Base template for fruit items. Inherits food consumption behavior with fruit-specific properties.

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `MaxStack` | 25 |
| `Consumable` | true |
| `Categories` | Items.Foods |

#### Tags

```json
{
  "Tags": {
    "Type": ["Food"],
    "Family": ["Fruit"]
  }
}
```

#### ResourceTypes

Fruits register with resource types for recipe flexibility:

```json
{
  "ResourceTypes": [
    { "Id": "Foods" },
    { "Id": "Fruits" }
  ]
}
```

---

### Template_Crop_Item

**Location:** `Server/Item/Items/Plant/Crop/_Template/Template_Crop_Item.json`

Base template for harvested vegetables and crops.

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `MaxStack` | 25 |
| `Consumable` | true |
| `Categories` | Items.Foods |

#### Tags

```json
{
  "Tags": {
    "Type": ["Food"],
    "Family": ["Vegetable"]
  }
}
```

#### ResourceTypes

```json
{
  "ResourceTypes": [
    { "Id": "Foods" },
    { "Id": "Vegetables" }
  ]
}
```

---

### Food Tiers

Food items follow a tiered progression affecting healing power and buff strength:

| Tier | Quality | Consume Time | Instant Heal | Regen Buff |
|------|---------|--------------|--------------|------------|
| T1 | Common | 1.5s | 5% | HealthRegen_Buff_T1 |
| T2 | Uncommon | 2.0s | 10% | HealthRegen_Buff_T2 |
| T3 | Rare | 2.5s | 15% | HealthRegen_Buff_T3 |

---

### Food Buff System

Food items can apply various buffs in addition to instant healing:

#### Health Regeneration Buffs

| Buff | Duration | Effect |
|------|----------|--------|
| `HealthRegen_Buff_T1` | 30s | +1 HP/s |
| `HealthRegen_Buff_T2` | 45s | +2 HP/s |
| `HealthRegen_Buff_T3` | 60s | +3 HP/s |

#### Meat Buffs

Cooked meats provide maximum health increases:

| Buff | Duration | Effect |
|------|----------|--------|
| `Meat_Buff_T1` | 120s | +5% Max Health |
| `Meat_Buff_T2` | 180s | +10% Max Health |
| `Meat_Buff_T3` | 240s | +15% Max Health |

#### Fruit/Vegetable Buffs

Plant-based foods boost maximum stamina:

| Buff | Duration | Effect |
|------|----------|--------|
| `FruitVeggie_Buff_T1` | 120s | +10% Max Stamina |
| `FruitVeggie_Buff_T2` | 180s | +15% Max Stamina |
| `FruitVeggie_Buff_T3` | 240s | +20% Max Stamina |

---

### Example Child: Food_Bread

```json
{
  "Parent": "Template_Food",
  "TranslationProperties": {
    "Name": "server.items.Food_Bread.name"
  },
  "Model": "Items/Food/Bread.blockymodel",
  "Texture": "Items/Food/Bread_Texture.png",
  "Icon": "Icons/ItemsGenerated/Food_Bread.png",
  "Quality": "Common",
  "Recipe": {
    "TimeSeconds": 5.0,
    "Input": [
      { "ItemId": "Ingredient_Flour", "Quantity": 3 }
    ],
    "BenchRequirement": [{
      "Type": "Crafting",
      "Categories": ["Food"],
      "Id": "Cooking_Campfire"
    }]
  },
  "InteractionVars": {
    "Consume_Charge": {
      "Interactions": [{
        "Parent": "Consume_Charge_Food_T1_Inner",
        "Effects": {
          "ItemAnimationId": "Consume"
        }
      }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "ApplyEffect",
        "EffectId": "Food_Health_Regen_Small"
      }]
    }
  }
}
```

---

### Food Categories

#### Raw Foods

Unprocessed foods with minimal healing:

| Item | Quality | Healing | Source |
|------|---------|---------|--------|
| `Food_Meat_Raw` | Common | T1 | Animal drops |
| `Plant_Fruit_Apple` | Common | T1 | Apple trees |
| `Plant_Fruit_Berry` | Common | T1 | Berry bushes |
| `Plant_Crop_Carrot` | Common | T1 | Farming |
| `Plant_Crop_Potato` | Common | T1 | Farming |

#### Cooked Foods

Processed at campfire with improved healing:

| Item | Quality | Healing | Buff |
|------|---------|---------|------|
| `Food_Meat_Cooked` | Uncommon | T2 | Meat_Buff_T1 |
| `Food_Meat_Cooked_Prime` | Rare | T3 | Meat_Buff_T2 |
| `Food_Fish_Cooked` | Uncommon | T2 | - |

#### Prepared Foods

Crafted at cooking bench with best effects:

| Item | Quality | Healing | Buff |
|------|---------|---------|------|
| `Food_Bread` | Common | T1 | - |
| `Food_Pie_Apple` | Uncommon | T2 | FruitVeggie_Buff_T1 |
| `Food_Pie_Berry` | Uncommon | T2 | FruitVeggie_Buff_T1 |
| `Food_Salad_Garden` | Uncommon | T2 | FruitVeggie_Buff_T2 |
| `Food_Kebab_Meat` | Rare | T3 | Meat_Buff_T2 |
| `Food_Stew_Hearty` | Rare | T3 | HealthRegen_Buff_T3 |

---

### All Food Variants

Food_Bread, Food_Bread_Baguette, Food_Kebab_Fish, Food_Kebab_Meat, Food_Kebab_Veggie, Food_Meat_Cooked, Food_Meat_Cooked_Prime, Food_Meat_Raw, Food_Pie_Apple, Food_Pie_Berry, Food_Pie_Meat, Food_Salad_Fruit, Food_Salad_Garden, Food_Stew_Fish, Food_Stew_Hearty, Food_Stew_Veggie, Plant_Crop_Beetroot, Plant_Crop_Cabbage, Plant_Crop_Carrot, Plant_Crop_Corn, Plant_Crop_Onion, Plant_Crop_Potato, Plant_Crop_Pumpkin, Plant_Crop_Tomato, Plant_Crop_Wheat, Plant_Fruit_Apple, Plant_Fruit_Berry, Plant_Fruit_Orange, Plant_Fruit_Pear

---

## Potion System

Potions provide instant effects and transformations. Unlike food, potions typically have conditional consumption based on stat checks.

### Potion_Template

**Location:** `Server/Item/Items/Potion/Potion_Template.json`

Base template for all potion items.

#### Base Properties

| Property | Value |
|----------|-------|
| `Quality` | Template |
| `MaxStack` | 10 |
| `Consumable` | true |
| `Categories` | Items.Potions |

#### Interactions

| Slot | Root Interaction | Description |
|------|------------------|-------------|
| `Secondary` | Root_Secondary_Consume_Potion | Instant consumption with stat check |

#### Tags

```json
{
  "Tags": {
    "Type": ["Potion"]
  }
}
```

#### BlockType (Placeable)

Potions define a `BlockType` so they can be placed and emit colored light:

```json
{
  "BlockType": {
    "DrawType": "Model",
    "CustomModel": "Items/Consumables/Potions/Potion.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Items/Consumables/Potions/Potion_Textures/Red.png", "Weight": 1 }
    ],
    "ParticleColor": "#ff3730",
    "Light": {
      "Color": "#522"
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `CustomModel` | string | `.blockymodel` used for the placed block |
| `CustomModelTexture` | array | Weighted texture variants for the model |
| `ParticleColor` | string | Hex color for block-break particles |
| `Light.Color` | string | Hex color of the light the placed potion emits |

#### InteractionVars

| Variable | Purpose |
|----------|---------|
| `Effect` | ApplyEffect / EffectCondition interaction |
| `Stat_Check` | Condition for consumption (e.g., health not full) |
| `RemoveEffect` | Effect to clear on consumption (e.g., poison) |
| `ConsumeSFX` | Sound while drinking |
| `ConsumedSFX` | Sound when consumption completes |

---

### Stat Check Condition

Potions use stat checks to prevent wasting potions when unnecessary:

```json
{
  "Stat_Check": {
    "Interactions": [{
      "Parent": "Stat_Check",
      "Costs": { "Health": 100 },
      "ValueType": "Percent",
      "LessThan": true
    }]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Costs` | object | Stat to check and threshold |
| `ValueType` | string | `"Percent"` or `"Absolute"` |
| `LessThan` | boolean | If true, stat must be below threshold |

Example: `Health: 100` with `LessThan: true` means "only drink if health < 100%".

---

### Health Potions

Restore health instantly with stat check to prevent waste.

| Potion | Quality | EffectId(s) Applied |
|--------|---------|---------------------|
| `Potion_Health_Small` | Common | Potion_Health_Instant_Small, Potion_Health_Regen_Small |
| `Potion_Health_Lesser` | Common | Potion_Health_Instant_Lesser, Potion_Health_Regen_Lesser |
| `Potion_Health` | Common | Potion_Health_Instant, Potion_Health_Regen |
| `Potion_Health_Greater` | Uncommon | Potion_Health_Instant_Greater, Potion_Health_Regen_Greater |
| `Potion_Health_Large` | Rare | Potion_Health_Instant_Large, Potion_Health_Regen_Large |

#### Example: Potion_Health

```json
{
  "Parent": "Potion_Template",
  "TranslationProperties": {
    "Name": "server.items.Potion_Health.name",
    "Description": "server.items.Potion_Health.description"
  },
  "Quality": "Common",
  "ItemLevel": 7,
  "Icon": "Icons/ItemsGenerated/Potion_Health.png",
  "Recipe": {
    "Input": [
      { "ItemId": "Potion_Empty", "Quantity": 1 },
      { "ItemId": "Plant_Fruit_Berries_Red", "Quantity": 12 },
      { "ItemId": "Plant_Petals_Blood", "Quantity": 6 },
      { "ItemId": "Plant_Crop_Health2", "Quantity": 1 }
    ],
    "BenchRequirement": [{
      "Id": "Alchemybench",
      "Type": "Crafting",
      "Categories": ["Alchemy_Potions"],
      "RequiredTierLevel": 3
    }],
    "TimeSeconds": 1
  },
  "InteractionVars": {
    "RemoveEffect": {
      "Interactions": [{ "Type": "Simple" }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "EffectCondition",
        "EntityEffectIds": [
          "Potion_Health_Regen_Greater",
          "Potion_Health_Regen_Large"
        ],
        "Match": "None",
        "Next": {
          "Type": "Serial",
          "Interactions": [
            { "Type": "ClearEntityEffect", "EntityEffectId": "Potion_Health_Regen_Lesser" },
            { "Type": "ClearEntityEffect", "EntityEffectId": "Potion_Health_Regen_Small" },
            { "Type": "ApplyEffect", "EffectId": "Potion_Health_Instant" },
            { "Type": "ApplyEffect", "EffectId": "Potion_Health_Regen" }
          ]
        },
        "Failed": { "Type": "Simple" }
      }]
    }
  }
}
```

---

### Stamina Potions

Restore stamina instantly and apply stamina regen effects.

| Potion | Quality | EffectId(s) Applied |
|--------|---------|---------------------|
| `Potion_Stamina_Small` | Common | Potion_Stamina_Instant_Small, Potion_Stamina_Regen |
| `Potion_Stamina_Lesser` | Common | Potion_Stamina_Instant_Lesser |
| `Potion_Stamina` | Common | Potion_Stamina_Instant |
| `Potion_Stamina_Greater` | Uncommon | Potion_Stamina_Instant_Greater |
| `Potion_Stamina_Large` | Rare | Potion_Stamina_Instant_Large |

---

### Regeneration Potions

Apply over-time recovery effects.

| Potion | Variants |
|--------|----------|
| `Potion_Regen_Health` | `Potion_Regen_Health_Small`, `Potion_Regen_Health`, `Potion_Regen_Health_Large` |
| `Potion_Regen_Stamina` | `Potion_Regen_Stamina_Small`, `Potion_Regen_Stamina`, `Potion_Regen_Stamina_Large` |
| `Potion_Regen_Mana` | `Potion_Regen_Mana_Small`, `Potion_Regen_Mana`, `Potion_Regen_Mana_Large` |

These regen potions inherit from `Decorative_Potion_Template` and override only `Icon` and `BlockType` (model/texture/light), reusing the parent's effect interactions:

```json
{
  "Parent": "Decorative_Potion_Template",
  "TranslationProperties": {
    "Name": "server.items.Potion_Regen_Health.name"
  },
  "Icon": "Icons/ItemsGenerated/Potion_Regen_Health.png",
  "BlockType": {
    "CustomModel": "Items/Consumables/Potions/Potion.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Items/Consumables/Potions/Potion_Textures/Pink.png", "Weight": 1 }
    ],
    "ParticleColor": "#f977be",
    "Light": { "Color": "#414" }
  }
}
```

---

### Morph Potions

Transform the player into creatures for exploration or stealth.

| Potion | Quality | Form |
|--------|---------|------|
| `Potion_Morph_Dog` | Rare | Dog |
| `Potion_Morph_Frog` | Rare | Frog |
| `Potion_Morph_Mouse` | Rare | Mouse |
| `Potion_Morph_Pigeon` | Rare | Pigeon |

#### Morph Effect Structure

The potion's `Effect` var simply applies an effect whose `EffectId` matches a morph effect asset. The transformation details (model, duration) live on the effect, not the item interaction:

```json
{
  "Type": "ApplyEffect",
  "EffectId": "Potion_Morph_Dog"
}
```

The corresponding effect (`Server/Entity/Effects/Potion/Potion_Morph_Dog.json`) sets `ModelChange` (e.g. `"Corgi"`) and `Duration`. See [Effects & Stats](effects-stats.md#model-transformation).

---

### Utility Potions

Special-purpose potions for specific situations.

| Potion | Quality | Effect |
|--------|---------|--------|
| `Potion_Antidote` | Common | Clears `Poison_T1`/`T2`/`T3`, applies `Antidote` |
| `Potion_Purify` | - | Cleansing effect |
| `Potion_Poison` / `Potion_Poison_Minor` / `Potion_Poison_Large` | - | Applies poison |
| `Potion_Mana` / `Potion_Mana_Small` / `Potion_Mana_Large` | - | Restores mana |

#### Example: Potion_Antidote

The antidote clears each poison tier in sequence (via chained `ClearEntityEffect.Next`), then applies the `Antidote` effect:

```json
{
  "TranslationProperties": {
    "Name": "server.items.Potion_Antidote.name"
  },
  "Quality": "Common",
  "Consumable": true,
  "Interactions": {
    "Secondary": "Root_Secondary_Consume_Potion"
  },
  "InteractionVars": {
    "Effect": {
      "Interactions": [{
        "Type": "ClearEntityEffect",
        "EntityEffectId": "Poison_T1",
        "Next": {
          "Type": "ClearEntityEffect",
          "EntityEffectId": "Poison_T2",
          "Next": {
            "Type": "ClearEntityEffect",
            "EntityEffectId": "Poison_T3",
            "Next": {
              "Type": "ApplyEffect",
              "EffectId": "Antidote"
            }
          }
        }
      }]
    }
  }
}
```

---

### Signature Potions

Potions that affect signature energy/charges.

| Potion | EffectId Applied |
|--------|------------------|
| `Potion_Signature_Small` | Potion_Signature_Regen_Small |
| `Potion_Signature_Lesser` | Potion_Signature_Regen_Lesser |
| `Potion_Signature` | Potion_Signature_Regen |
| `Potion_Signature_Greater` | Potion_Signature_Regen_Greater |
| `Potion_Signature_Large` | Potion_Signature_Regen_Large |

---

### All Potion Variants

Potion_Antidote, Potion_Empty, Potion_Empty_Small, Potion_Empty_Large, Potion_Health_Small, Potion_Health_Lesser, Potion_Health, Potion_Health_Greater, Potion_Health_Large, Potion_Mana_Small, Potion_Mana, Potion_Mana_Large, Potion_Morph_Dog, Potion_Morph_Frog, Potion_Morph_Mouse, Potion_Morph_Pigeon, Potion_Poison_Minor, Potion_Poison, Potion_Poison_Large, Potion_Purify, Potion_Regen_Health_Small, Potion_Regen_Health, Potion_Regen_Health_Large, Potion_Regen_Mana_Small, Potion_Regen_Mana, Potion_Regen_Mana_Large, Potion_Regen_Stamina_Small, Potion_Regen_Stamina, Potion_Regen_Stamina_Large, Potion_Signature_Small, Potion_Signature_Lesser, Potion_Signature, Potion_Signature_Greater, Potion_Signature_Large, Potion_Stamina_Small, Potion_Stamina_Lesser, Potion_Stamina, Potion_Stamina_Greater, Potion_Stamina_Large

---

## Common Consumable Patterns

### Consumable Property

All consumable items share these core properties:

```json
{
  "Consumable": true,
  "MaxStack": 25
}
```

The `Consumable: true` flag tells the engine to remove one item from the stack when consumed.

### ApplyEffect Interaction

The standard way to grant buffs from consumables:

```json
{
  "Type": "ApplyEffect",
  "EffectId": "Food_Instant_Heal_T1"
}
```

For effects with custom duration:

```json
{
  "Type": "ApplyEffect",
  "EffectId": "Buff_HealthRegen",
  "Duration": 60.0
}
```

### ChangeStat Interaction

For instant stat modifications without buff effects:

```json
{
  "Type": "ChangeStat",
  "StatModifiers": { "Health": 0.30 },
  "ValueType": "Percent"
}
```

| Property | Type | Description |
|----------|------|-------------|
| `StatModifiers` | object | Stat ID to value mapping |
| `ValueType` | string | `"Percent"` (0.30 = 30%) or `"Absolute"` |

### Consume_Charge (Food)

Food items handle timed consumption by extending a shared charge interaction through the `Consume_Charge` var rather than declaring charge fields inline. The parent (`Consume_Charge_Food_T1_Inner`) defines the charge behavior; the child only supplies effects such as the consume animation:

```json
{
  "Consume_Charge": {
    "Interactions": [{
      "Parent": "Consume_Charge_Food_T1_Inner",
      "Effects": {
        "ItemAnimationId": "Consume"
      }
    }]
  }
}
```

The food tier templates (`Consume_Charge_Food_T1` / `_T2` / `_T3`) compose this via `Type: "Serial"` interactions that `Replace` the `ConsumeSFX` and `Consume_Charge` vars with their defaults.

### ModifyInventory Interaction

Removes consumed item from inventory:

```json
{
  "Type": "ModifyInventory",
  "ItemToRemove": {
    "Self": true,
    "Quantity": 1
  }
}
```

### RemoveEffect / ClearEntityEffect Interaction

Clears active effects. Antidotes use `ClearEntityEffect` keyed on `EntityEffectId`, chaining additional removals through `Next`:

```json
{
  "Type": "ClearEntityEffect",
  "EntityEffectId": "Poison_T1",
  "Next": {
    "Type": "ClearEntityEffect",
    "EntityEffectId": "Poison_T2"
  }
}
```

Potion templates also expose a `RemoveEffect` var that defaults to a no-op (`{ "Type": "Simple" }`) so children can override it when they need to strip an effect on consumption.

---

## Creating Custom Consumables

### Custom Food Item

```json
{
  "Parent": "Template_Food",
  "TranslationProperties": {
    "Name": "server.items.My_Custom_Food.name"
  },
  "Icon": "Icons/ItemsGenerated/My_Food.png",
  "Quality": "Uncommon",
  "MaxStack": 25,
  "InteractionVars": {
    "Consume_Charge": {
      "Interactions": [{
        "Parent": "Consume_Charge_Food_T1_Inner",
        "Effects": {
          "ItemAnimationId": "Consume"
        }
      }]
    },
    "Effect": {
      "Interactions": [
        {
          "Type": "ApplyEffect",
          "EffectId": "Food_Instant_Heal_T2"
        },
        {
          "Type": "ApplyEffect",
          "EffectId": "Meat_Buff_T1"
        }
      ]
    }
  }
}
```

### Custom Potion Item

```json
{
  "Parent": "Potion_Template",
  "TranslationProperties": {
    "Name": "server.items.My_Custom_Potion.name"
  },
  "Icon": "Icons/ItemsGenerated/My_Potion.png",
  "Quality": "Rare",
  "MaxStack": 10,
  "InteractionVars": {
    "Stat_Check": {
      "Interactions": [{
        "Parent": "Stat_Check",
        "Costs": { "Health": 50 },
        "ValueType": "Percent",
        "LessThan": true
      }]
    },
    "Effect": {
      "Interactions": [{
        "Type": "ApplyEffect",
        "EffectId": "My_Custom_Buff",
        "Duration": 90.0
      }]
    }
  }
}
```

---

## Related Documentation

- [Items Reference](items.md) - Common properties and systems
- [Effects & Stats](effects-stats.md) - Status effects and stat modifiers
- [Interactions API](interactions.md) - ApplyEffect, ChangeStat, ModifyInventory
- [Weapons Reference](items-weapons.md) - Combat items
- [Tools Reference](items-tools.md) - Gathering tools
