# Custom Drop — make your item drop from a mob

A no-code, no-art Hytale pack, just like [`custom-food`](../custom-food/) — **nothing
but JSON text.** No Java, no compiler, no Gradle, no drawing. Where `custom-food`
*defined* the **Hearty Snack**, this pack makes that snack something you **find in the
world**: it drops when you kill a chicken. It does that by overriding the chicken's
shipped loot table.

> **Builds on `custom-food`.** The dropped item, `Food_Hearty_Snack`, is defined in the
> `custom-food` pack — so **both packs must be installed**. That's a teachable point in
> itself: packs *compose*, referencing each other's content by id. (If you only install
> this pack, the chicken's other drops still work; the snack line just resolves to
> nothing because no item with that id is registered.)

> **Pack vs Plugin:** A *pack* is pure content (JSON/assets) the game loads directly — no
> code runs. A *plugin* is compiled Java. The `commands/`, `ui/`, `inventory/`, and
> `entity-count/` examples are plugins; this one is a pack, like `custom-food`. See
> [Pack vs Plugin Directory Structure](../../docs/02-structure.md).

## The big idea: a loot table is a composition tree, not an inheritance

`custom-food` taught **inheritance**: take one template (`Template_Food`) and override a
few fields to make a variant. A drop table is the opposite shape — **composition**. You
*build up* an outcome from a tree of nested containers:

- **`Multiple`** — evaluate **every** child. Use it for "roll each of these independently."
- **`Choice`** — pick **one** child, by weight. Use it for "pick one of these."
- **`Single`** — a leaf that drops one actual `Item`.
- **`Empty`** — a "nothing" outcome, only valid *inside* a `Choice`/`Multiple`.

The headline gotcha is **`Multiple` vs `Choice`**: in a `Multiple`, a child's `Weight` is
an *independent* 0–100% chance (each child rolls on its own); in a `Choice`, a child's
chance is *relative* — `childWeight / sum(weights)` — and exactly one child wins. Mix
these up and you get the wrong drops. This pack uses both, side by side, so you can see
the difference.

## What's in this pack

```
custom-drop/
├── manifest.json                                    # declares the pack to the game
└── Server/
    └── Drops/
        └── NPCs/
            └── Livestock/
                └── Drop_Chicken.json                # overrides the chicken's loot table
```

The whole pack is **one drop file placed at the exact path the game ships it**:
`Server/Drops/NPCs/Livestock/Drop_Chicken.json`. The game resolves a drop table by that
path/id, so a pack file at the identical path **replaces** the shipped one. The chicken's
NPC role wires up its loot with `"DropList": "Drop_Chicken"`, so overriding this file is
all it takes — no NPC edits needed.

> **Override = full replacement, not a merge.** Your file doesn't *add to* the shipped
> table; it *becomes* the table. So to keep the chicken's normal raw-chicken + hide drops,
> you must **re-include them** in your file (we do). Delete them and the chicken would drop
> *only* the snack.

JSON files **cannot contain comments**, so every field is explained here in the README.
Drop files do, however, support a `$Comment` string the game ignores — we use it in the
JSON to self-document.

### `manifest.json` — declaring the pack

```json
{
  "Group": "inkthorne",
  "Name": "Custom Drop",
  "Version": "1.0.0",
  "Authors": [
    { "Name": "inkthorne" }
  ],
  "ServerVersion": "0.5.0",
  "IncludesAssetPack": true
}
```

| Field | What it does |
|-------|--------------|
| `Group` | Your namespace. Use your name or team name; keeps your assets from clashing with others. |
| `Name` | Human-readable pack name shown in mod lists. |
| `Version` | Your pack's version. Bump it when you change things. |
| `Authors` | Who made it. A list of `{ "Name": "..." }` objects. |
| `IncludesAssetPack` | `true` because this pack contains assets (the drop file). |
| `ServerVersion` | The exact game build this pack targets. **Build-specific** — see the note below. |

> **About `ServerVersion`:** it must *exactly* match the game's own version string, which
> changes with every game update. If it doesn't match, the server still loads the pack but
> logs a warning. To read the current value:
> ```bash
> unzip -p "$HYTALE_JAR" META-INF/MANIFEST.MF | grep Implementation-Version
> ```
> Re-pin this field after a game update. Full details:
> [02-structure.md → ServerVersion](../../docs/02-structure.md#serverversion-target-server-version).

### `Server/Drops/NPCs/Livestock/Drop_Chicken.json` — the drop file

```json
{
  "Container": {
    "Type": "Multiple",
    "Containers": [
      {
        "Type": "Choice",
        "Weight": 100,
        "Containers": [
          { "Type": "Single", "Item": { "ItemId": "Food_Chicken_Raw", "QuantityMin": 1, "QuantityMax": 2 } }
        ]
      },
      {
        "Type": "Choice",
        "Weight": 100,
        "Containers": [
          { "Type": "Single", "Item": { "ItemId": "Ingredient_Hide_Light", "QuantityMin": 1, "QuantityMax": 2 } }
        ]
      },
      {
        "Type": "Choice",
        "Weight": 100,
        "Containers": [
          { "Type": "Single", "Weight": 100, "Item": { "ItemId": "Food_Hearty_Snack", "QuantityMin": 1, "QuantityMax": 1 } },
          { "Type": "Empty", "Weight": 0 }
        ]
      }
    ]
  }
}
```

The first two `Choice` blocks are the chicken's **original** shipped drops, copied
verbatim (raw chicken + light hide, each always dropping). The third `Choice` is the
**new** part. Reading the tree top-down:

| Field | What it does |
|-------|--------------|
| `Container` | **The required root.** Every drop file wraps its tree in one top-level `Container`. (The only no-drop file is literally `{}`.) |
| `Type` | The container kind: `Multiple`, `Choice`, `Single`, `Empty`, or `Droplist`. |
| `Containers` | The child containers, for `Multiple` and `Choice`. |
| `Item` | The dropped item, for a `Single` leaf. |
| `ItemId` | **Case-sensitive** id of a registered item. `Food_Chicken_Raw` and `Ingredient_Hide_Light` ship with the game; `Food_Hearty_Snack` comes from the `custom-food` pack. |
| `QuantityMin` / `QuantityMax` | Drop count. When they differ, a value is picked uniformly in that range (e.g. 1–2). |
| `Weight` | Means **different things** by parent — see below. |
| `Empty` | A "drop nothing" outcome. Only valid as a child of a `Choice`/`Multiple`, never as the file root. |

**Why `Weight` means two different things here — the key lesson:**

- The **root is `Multiple`**, so it evaluates *all three* of its `Choice` children. Each
  `Choice` carries `Weight: 100`, i.e. a **100% independent chance** to fire. (Drop that to
  `25` and that branch would fire only ~25% of kills.)
- The **third child is a `Choice`**, so among *its* children exactly **one** wins, with
  probability `weight / sum(weights)`. With `Snack: 100` and `Empty: 0`, the sum is 100 and
  the snack wins `100/100 = 100%` of the time — guaranteed, on purpose, so a single kill
  proves the wiring. Make it `Snack: 5`, `Empty: 95` and you get a realistic `5/100 = 5%`
  drop.

So a child `Weight` under `Multiple` is an absolute percentage; a child `Weight` under
`Choice` is a share of the total. Same word, different math.

## How to change it

- **Make the snack rare (for real play).** In the third `Choice`, lower the snack's
  `Weight` and raise `Empty`'s — e.g. `Snack: 5`, `Empty: 95` for a 5% drop. Start high to
  confirm it works, then dial it down; that makes the weight math tangible.
- **Drop a different item.** Swap the snack's `ItemId` for any registered item — a shipped
  one like `Plant_Fruit_Apple`, or another of your own pack's items.
- **Add more possibilities.** Add a third child to that `Choice` (e.g. a rare feather), and
  the weights redistribute across all of them automatically.
- **Multi-roll it.** Add `"RollsMin": 1, "RollsMax": 3` to a `Choice` to pick several times
  with replacement (each roll can repeat an item).
- **Share a loot pool.** Replace a child with `{ "Type": "Droplist", "DroplistId": "<flat id>" }`
  to pull in another drop file by its **flat** id (not a path). Good for reusing one table
  across many creatures.
- **Override a different creature.** Copy a different shipped table from
  `Server/Drops/NPCs/Livestock/` (cow, pig, boar…) to the matching path and edit that
  instead.

## How to test it in your dev game

1. **Install both packs.** This pack drops an item defined in `custom-food`, so deploy
   that one too:
   ```bash
   ../custom-food/deploy.sh
   ./deploy.sh
   ```
   Each `deploy.sh` copies its pack into its own folder under your Hytale Mods directory
   (Windows `%APPDATA%\Hytale\UserData\Mods\`, or the Flatpak path on Linux).
2. **Start the game / server.** Watch the log — a pack with a broken asset reference fails
   *loudly* on boot (the server validates assets at startup). A clean boot with no
   `Custom Drop`/`Custom Food`-related errors means both packs loaded.
3. **Find a chicken.** Chickens are common in early-game grassland; they're also low-HP, so
   one hit settles it — a clean single-action test.
4. **Kill it and look at the drops.** With the shipped weights (`Snack: 100`, `Empty: 0`)
   the chicken drops raw chicken, a light hide, **and** a Hearty Snack every time. Pick the
   snack up and confirm it's the real item (right name, eats correctly per `custom-food`).
5. **Tune it.** Once the wiring is confirmed, lower the snack weight (e.g. `5` / `95`) and
   kill several chickens to feel the rarity. Re-deploy after each edit.

> **If the snack never drops** but raw chicken and hide do: the chicken table loaded but
> the snack id isn't resolving. Check that the `custom-food` pack is installed (that's
> where `Food_Hearty_Snack` is defined) and that the `ItemId` matches exactly,
> case-included.

> [!note]
> The JSON here is fully verified against the game's shipped assets (build
> `0.5.0`): the override path, the chicken's original drop contents, and
> every `ItemId` were copied from the extracted `Assets.zip`, and the chicken role's
> `"DropList": "Drop_Chicken"` confirms a same-path file overrides the shipped table. The
> end-to-end in-game kill test (steps 3–5) is the one thing to run yourself — it needs a
> live game session.

## Where the real assets live (to verify or extend)

This pack copies a real shipped drop table. To browse the originals, extract the game's
`Assets.zip` once:

```bash
unzip -q -o ~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Assets.zip -d ~/.cache/hytale-assets
```

Then look in:
- `Server/Drops/` — every shipped loot table: `NPCs/` (creatures), `Items/` (destructible
  containers like pots and barrels), `Crop/`, `Rock/`, `Prefabs/`, and more.
- `Server/Drops/NPCs/Livestock/Drop_Chicken.json` — the exact file this pack overrides.
- `Server/Item/Items/` — item definitions, to confirm any `ItemId` you reference.

## Related documentation

- [Drop System](../../docs/drops.md) — the full loot-table format: every container type, weights, multi-roll, and `Droplist` composition.
- [Item Definitions](../../docs/items.md) — item ids and the `Parent` inheritance system (how the snack itself is built).
- [NPC Roles](../../docs/npc-roles.md) — how a creature's role wires up its `DropList`.
- [Pack vs Plugin Directory Structure](../../docs/02-structure.md) — what a pack is and how it's laid out.
