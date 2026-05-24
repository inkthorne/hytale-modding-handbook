# Custom Food — a no-code, no-art Pack

This is the simplest possible Hytale mod: **a pack made of nothing but JSON text.**
No Java, no compiler, no Gradle, and no drawing — it reuses art and effects that
already ship with the game. If you can edit a text file, you can build this.

It adds one new item, the **Hearty Snack**: eat it to instantly restore health and
gain a short "Hearty" buff (+5% max health for 45 seconds).

> **Pack vs Plugin:** A *pack* is pure content (JSON/assets) the game loads
> directly — no code runs. A *plugin* is compiled Java. The other examples in this
> repo (`commands/`, `ui/`, `inventory/`, `entity-count/`) are plugins; this one is
> a pack. See [Pack vs Plugin Directory Structure](../../docs/02-structure.md).

## The big idea: copy a template, override a few fields

Almost every item in Hytale is built by **inheriting from a template** and changing
only what makes it different. Bread, apple pie, and stew are all the same
`Template_Food` with a different name, icon, and effect. You do the exact same thing
here. This "extend a parent, override a handful of fields" pattern is the master
key to most JSON modding — items, NPCs, potions, drops, and more all work this way.

## What's in this pack

```
custom-food/
├── manifest.json                       # declares the pack to the game
└── Server/
    ├── Item/
    │   └── Food_Hearty_Snack.json       # the new item
    └── Languages/
        └── en-US/
            └── server.lang              # the item's display name + description
```

JSON files **cannot contain comments**, so every field is explained here in the
README instead of inline.

### `manifest.json` — declaring the pack

```json
{
  "Group": "inkthorne",
  "Name": "Custom Food",
  "Version": "1.0.0",
  "Authors": [
    { "Name": "inkthorne" }
  ],
  "ServerVersion": "2026.03.26-89796e57b",
  "IncludesAssetPack": true
}
```

| Field | What it does |
|-------|--------------|
| `Group` | Your namespace. Use your name or team name; keeps your assets from clashing with others. |
| `Name` | Human-readable pack name shown in mod lists. |
| `Version` | Your pack's version. Bump it when you change things. |
| `Authors` | Who made it. A list of `{ "Name": "..." }` objects. |
| `IncludesAssetPack` | `true` because this pack contains assets (the item + language files). |
| `ServerVersion` | The exact game build this pack targets. **Build-specific** — see the note below. |

> **About `ServerVersion`:** it must *exactly* match the game's own version string,
> which changes with every game update. If it doesn't match, the server still loads
> the pack but logs a warning. To read the current value:
> ```bash
> unzip -p "$HYTALE_JAR" META-INF/MANIFEST.MF | grep Implementation-Version
> ```
> Re-pin this field after a game update. Full details: [02-structure.md → ServerVersion](../../docs/02-structure.md#serverversion-target-server-version).

### `Server/Item/Food_Hearty_Snack.json` — the item

```json
{
  "Parent": "Template_Food",
  "TranslationProperties": {
    "Name": "server.items.Food_Hearty_Snack.name",
    "Description": "server.items.Food_Hearty_Snack.description"
  },
  "Quality": "Uncommon",
  "Icon": "Icons/ItemsGenerated/Food_Pie_Apple.png",
  "BlockType": {
    "Material": "Empty",
    "DrawType": "Model",
    "CustomModel": "Items/Consumables/Food/Pie.blockymodel",
    "CustomModelTexture": [
      { "Texture": "Items/Consumables/Food/Pie_Textures/Apple.png", "Weight": 1 }
    ],
    "ParticleColor": "#e5b132"
  },
  "MaxStack": 16,
  "InteractionVars": {
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

| Field | What it does |
|-------|--------------|
| `Parent` | **The most important line.** Inherits everything from `Template_Food` — the eat animation, the right-click-to-consume behaviour, sounds, stack handling. You only override what's different below. |
| `TranslationProperties.Name` / `.Description` | Point to text *keys*, not the text itself. The actual words live in `server.lang` (see below). The `server.` prefix maps to the `server.lang` file. |
| `Quality` | Rarity tier — sets the item's border colour and sort order. `Uncommon` = green. (Tiers: Common, Uncommon, Rare, Epic, Legendary.) |
| `Icon` | The inventory picture. **This is the "no art" trick:** it points at an icon that already ships with the game (apple pie), so you draw nothing. |
| `BlockType` | The 3D model shown when the item is **held or dropped** in the world (the `Icon` only covers the inventory thumbnail). We reuse the game's apple-pie model + texture so the held item matches the icon — again, no new art. **If you omit this**, the item inherits `Template_Food`'s default held model, which is a corn cob — so you'd get an apple-pie icon but a corn cob in hand. |
| `MaxStack` | How many stack in one slot. The template's default is 25; we override to 16 just to show an override taking effect. |
| `InteractionVars.Effect` | What happens when you eat it. A list of `ApplyEffect` entries, each naming a real effect by `EffectId`. |

The two effects, both shipped with the game:

| `EffectId` | Effect |
|------------|--------|
| `Food_Instant_Heal_T2` | Instantly restores 10% health. |
| `Meat_Buff_T1` | "Hearty" buff: +5% max health for 45 seconds. |

Everything else the food needs — the consume timing, the chewing animation, the
eating sound — is inherited from `Template_Food`, so it isn't repeated here. That's
the payoff of `Parent`.

### `Server/Languages/en-US/server.lang` — the words players see

```
items.Food_Hearty_Snack.name = Hearty Snack
items.Food_Hearty_Snack.description = Instantly restores health and grants a short Hearty buff (+5% max health for 45s).
```

Each line is `key = value`. The item's `TranslationProperties.Name` of
`server.items.Food_Hearty_Snack.name` resolves to the `items.Food_Hearty_Snack.name`
key here (the `server.` prefix selects the `server.lang` file). Without this file the
item would display the raw key text instead of "Hearty Snack". `.lang` files *do*
allow `#` comments.

## How to change it

You now have everything you need to make your own food. Try editing one field at a
time and reloading:

- **Different look?** Swap the `Icon` for another shipped icon, e.g.
  `Icons/ItemsGenerated/Food_Bread.png`, `Icons/ItemsGenerated/Food_Skewer_Meat.png`,
  or `Icons/ItemsGenerated/Food_Pie_Meat.png`. (Icon filenames don't always match the
  item name — browse the game's `Common/Icons/ItemsGenerated/` for the real list; see
  "Where the real assets live" below.) If you want the held model to match too, point
  `BlockType.CustomModel` / `CustomModelTexture` at a model under
  `Common/Items/Consumables/Food/`.
- **Different effect?** Change an `EffectId`. Other real food effects include
  `Food_Instant_Heal_T1` / `_T3` (weaker / stronger heal), `HealthRegen_Buff_T2`
  (heal-over-time), and `FruitVeggie_Buff_T1` (+max stamina).
- **Different name?** Edit the right-hand side of the lines in `server.lang`.

## How to test it in your dev game

1. **Install the pack.** On Linux/bash, run the deploy script — it copies the asset
   files into a `custom-food/` pack folder in your Mods directory (resolving the path
   the same way the plugin examples do):
   ```bash
   ./deploy.sh
   ```
   Or copy it by hand into your Hytale Mods folder (the pack is just `manifest.json`
   + `Server/`):
   - **Windows:** `%APPDATA%\Hytale\UserData\Mods\`
   - **Linux (Flatpak launcher):** `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/UserData/Mods/`
2. **Start the game / server.** Watch the log — a pack with a broken asset reference
   fails *loudly* on boot (the server validates assets at startup). A clean boot with
   no `Custom Food`-related errors means the pack loaded.
3. **Give yourself the item.** In-game, use the give command with the item's id:
   ```
   /give Food_Hearty_Snack 1
   ```
   (The id is the JSON file's name without `.json`. Item ids are case-sensitive.)
4. **Eat it.** Hold it and **right-click** (the consume slot). Watch your health bar
   jump, then watch the +5% max-health "Hearty" buff appear in your status effects
   for 45 seconds.

> If the item appears but shows the name `server.items.Food_Hearty_Snack.name`
> instead of "Hearty Snack", the `server.lang` file isn't being picked up — check it
> sits at exactly `Server/Languages/en-US/server.lang`.

## Where the real assets live (to verify or extend)

This pack copies a real game template and reuses real game assets. To browse them
yourself, extract the game's `Assets.zip` once:

```bash
unzip -q -o ~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Assets.zip -d ~/.cache/hytale-assets
```

Then look in:
- `Server/Item/Items/Food/` — the food template and every shipped food item to copy from.
- `Server/Entity/Effects/Food/` — the heal/buff effects you can reference by `EffectId`.
- `Common/Icons/ItemsGenerated/` — the icons you can reuse with no drawing.

## Next step

Want your food to drop from a chest or mob instead of being given by command? That's
another small JSON file — a loot table. See [Drop System](../../docs/drops.md).

## Related documentation

- [Pack vs Plugin Directory Structure](../../docs/02-structure.md) — what a pack is and how it's laid out.
- [Items Reference](../../docs/items.md) — common item fields, the `Parent` inheritance system, and quality tiers.
- [Consumable Items](../../docs/items-consumables.md) — food and potion templates in depth.
- [Effects & Stats](../../docs/effects-stats.md) — how the heal and buff effects are defined.
