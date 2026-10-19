---
title: "Examples"
description: "The handbook's runnable example mods: no-code packs you install by copying a folder, and Gradle plugins you build and deploy. What each one demonstrates, the docs pages it pairs with, and how to build, deploy or install it."
seo:
  type: TechArticle
---

# Examples

**Doc type:** Index

The `examples/` directory of the repository holds runnable mods. Each section below says what one of them demonstrates, which pages explain the same thing, and where its code is. A **pack** is JSON content the game loads directly; a **plugin** is compiled Java. [Pack vs Plugin Directory Structure](02-structure.md) shows how they are laid out.

**Start with a pack.** It needs a text editor, no compiler and no art. The repository's own tour of the examples, with a table of the commands each plugin adds, is [examples/README.md](../examples/README.md).

---

## No code: packs

A pack deploys by copying its folder into the Hytale Mods folder. On Linux, each pack's `deploy.sh` does the copy; there is no `deploy.bat`, so on Windows copy the folder by hand.

### custom-food

One new item, the Hearty Snack, built by extending the game's own `Template_Food`: it reuses an icon, a model and the heal and buff effects that already ship, so there is nothing to draw or compile. It teaches the pattern that most JSON modding rests on, copy a template and override a few fields.

- **Code:** [examples/custom-food/](../examples/custom-food/)
- **Install:** run `./deploy.sh` in the folder, or copy `manifest.json` and `Server/` into the Mods folder. Then `/give Food_Hearty_Snack 1`, and eat it in Adventure mode: the consume interaction is gated to that mode.
- **Pairs with:** [Item Definitions](items.md), [Consumable Items](items-consumables.md), [Effects & Stats](effects-stats.md).
- **Read more:** the example's [README](../examples/custom-food/README.md) explains every field.

### custom-drop

Makes that snack drop in the world by overriding the chicken's shipped loot table. It teaches the drop system's composition tree (`Multiple` and `Choice`, weights, `Empty`, multiple rolls), and that an override of a shipped file replaces the whole file. It drops an item that `custom-food` defines, so install both: packs compose by referring to each other's ids.

- **Code:** [examples/custom-drop/](../examples/custom-drop/)
- **Install:** from the `custom-drop` folder, run `../custom-food/deploy.sh` and then `./deploy.sh`, or copy both folders by hand.
- **Pairs with:** [Drop System](drops.md), [Item Definitions](items.md), [NPC Roles](npc-roles.md).
- **Read more:** the example's [README](../examples/custom-drop/README.md), including the in-game test.

---

## Java plugins

**Requirements**, once for every plugin: Java 25 or newer, and a local Hytale install. Each build compiles against the `HytaleServer.jar` of that install, which `examples/hytale-paths.gradle` finds per platform (the `APPDATA` folder first, then the Linux Flatpak install). The Gradle wrapper is in each example.

**Build and deploy**, from the example's own directory:

```bash
# Linux / bash
./gradlew build   # compile; produces build/libs/*.jar
./deploy.sh       # build if needed, then copy the jar into the Mods folder
```

```batch
:: Windows
build.bat         :: compile
deploy.bat        :: build and copy the jar into the Mods folder
```

The Mods folder is `%APPDATA%\Hytale\UserData\Mods\` on Windows and `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/UserData/Mods/` on a Linux Flatpak launcher. Two examples register a command the game already has: `commands` adds `/tp` and `inventory` adds `/give`. Each replaces the built-in of that name, and unloading the example removes whatever holds the name until the server restarts. Their READMEs explain it; a real plugin should pick a name nothing else uses.

### commands

The command system, and the place to start with plugins: registering a command, declaring arguments, and reading them, including relative position arguments (`~10 ~ ~-5`). Adds `/hello` and `/tp <x> <y> <z>`.

- **Code:** [examples/commands/](../examples/commands/)
- **Pairs with:** [Commands API](commands.md).
- **Read more:** [README](../examples/commands/README.md).

### ui

Custom UI: opening a page from a `.ui` layout file, toggling built-in HUD components, and driving a persistent custom HUD with live updates. Adds `/menu`, `/hud <show|hide>` and `/statushud <show|hide|update>`. Its manifest sets `IncludesAssetPack`, which the `.ui` files need.

- **Code:** [examples/ui/](../examples/ui/)
- **Pairs with:** [UI System](ui.md), [UI Java API](ui-api.md).
- **Read more:** [README](../examples/ui/README.md).

### inventory

The inventory API: adding items with transaction handling, clearing sections, reading what a player holds, and sorting storage. Adds `/give <item> <quantity>`, `/inv-clear <section>`, `/inspect` and `/sort <type>`. It also documents the case-sensitive item id gotcha.

- **Code:** [examples/inventory/](../examples/inventory/)
- **Pairs with:** [Inventory API](inventory.md).
- **Read more:** [README](../examples/inventory/README.md).

### entity-count

The Entity Component System's ticking system: code that runs every tick on the world thread, counts entities by the components they carry, and pushes the totals to a live HUD. Adds `/entitycount <show|hide>`.

- **Code:** [examples/entity-count/](../examples/entity-count/)
- **Pairs with:** [Components (ECS) API](components.md), [Events API](events.md), [UI Java API](ui-api.md).
- **Read more:** [README](../examples/entity-count/README.md).

### events

Both event mechanisms side by side: the global event bus, for server-level events such as a player connecting or disconnecting, and an ECS `EntityEventSystem`, for gameplay events such as a block being broken, with the acting entity's components in reach. It adds no commands.

- **Code:** [examples/events/](../examples/events/)
- **Pairs with:** [Events API](events.md), [Player API](player.md#player-events).
- **Read more:** [README](../examples/events/README.md).

### item-respawner

The most involved example: a placeable block with state that persists. A custom block-entity component, a ticking system over the chunk store, an item entity it spawns and respawns once the last one is gone, and a press-F settings page that edits the block in the world. It adds no commands.

- **Code:** [examples/item-respawner/](../examples/item-respawner/)
- **Pairs with:** [Custom block-entity components](blocks-java-api.md#custom-block-entity-components), [Components (ECS) API](components.md), [UI Java API](ui-api.md).
- **Read more:** [README](../examples/item-respawner/README.md).
