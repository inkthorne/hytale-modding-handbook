---
title: Home
nav_order: 0
---

# Hytale Modding Handbook

**Doc type:** Index

A server-plugin & asset API reference with the **descriptions, gotchas, and
working examples**.

**Verified against Hytale 0.7.2 (build-34).** Each topic page carries its own "Verified against" stamp, and a game
update can invalidate any of them until the next re-verification pass. Each verified build is tagged on the
[releases page](https://github.com/inkthorne/hytale-modding-handbook/releases).

## Who it is for

An intermediate reference for server plugins and asset packs. Java plugins assume you already write Java; packs are JSON and need no Java at all. If you are new to Hytale modding, read the [Overview](00-overview.md), then run an [example](examples.md): the packs need a text editor and nothing else.

## Find it by task

Each line links the section that does the job, names the API or key it turns on, and links an example where the repository has one.

### In Java (plugins)

- **Add a chat command** — [AbstractPlayerCommand](commands.md#abstractplayercommand), [registering it](commands.md#registration-example). API: `CommandRegistry.registerCommand`. Example: [CommandsPlugin](../examples/commands/src/main/java/hytale/examples/commands/CommandsPlugin.java).
- **Listen for a player joining** — [Player events](player.md#registration-example). API: `EventRegistry.register`. Example: [EventsPlugin](../examples/events/src/main/java/hytale/examples/events/EventsPlugin.java).
- **React when a block is broken or placed** — [EntityEventSystem](events.md#creating-an-entityeventsystem). API: `EntityEventSystem.handle`. Example: [BreakBlockNotifierSystem](../examples/events/src/main/java/hytale/examples/events/BreakBlockNotifierSystem.java).
- **Run code every tick** — [EntityTickingSystem](components.md#entitytickingsystemecs_type). API: `EntityTickingSystem.tick`. Example: [EntityCountTickingSystem](../examples/entity-count/src/main/java/hytale/examples/entitycount/EntityCountTickingSystem.java).
- **Give a player an item** — [A combined container in a system](inventory.md#combined-container-from-an-ecs-system-clear--grant-loadout). API: `InventoryComponent.getCombined`. Example: [GiveCommand](../examples/inventory/src/main/java/hytale/examples/inventory/GiveCommand.java).
- **Read or set a block** — [Reading](block-access.md#reading), [writing](block-access.md#writing-with-blockoperations). API: `BlockSection.get`, `BlockOperations.setBlock`.
- **Open a custom UI page** — [UI System: Quick Start](ui.md#quick-start). API: `PageManager.openCustomPage`. Example: [MenuCommand](../examples/ui/src/main/java/hytale/examples/ui/MenuCommand.java).
- **Show a custom HUD** — [CustomUIHud](ui-api.md#customuihud). API: `HudManager.addCustomHud`. Example: [StatusHudCommand](../examples/ui/src/main/java/hytale/examples/ui/StatusHudCommand.java).

### In JSON (no Java)

- **Make a custom item** — [Inheritance](items.md#inheritance-system). Key: `Parent`. Example: [custom-food](../examples/custom-food/Server/Item/Items/Food/Food_Hearty_Snack.json).
- **Change what a mob drops** — [A creature's drop table](drops.md#creature-with-guaranteed-and-chance-drops), [how a role picks its table](drops.md#npc-drops-1). Key: `Container`; the role names the table with `DropList`. Example: [custom-drop](../examples/custom-drop/Server/Drops/NPCs/Livestock/Drop_Chicken.json).
- **Create a custom weapon** — [Example child: Iron Sword](items-weapons.md#example-child-iron-sword), [the Weapon property](items.md#weapon-property). Key: `Parent`, a `Template_Weapon_*` that supplies the `Weapon` property the engine tests for.
- **Create a custom tool** — [Example child: Iron Pickaxe](items-tools.md#example-child-iron-pickaxe). Key: `Tool`.
- **Define a crafting recipe** — [Embedded recipe](items-crafting.md#embedded-recipe-item-definition). Key: `Recipe`.
- **Change how an NPC behaves** — [Behavior system](npc-roles.md#behavior-system-instructions), [Variants](npc-roles.md#variants). Key: `Instructions`. To retune a shipped template instead, write a `Variant`: 545 of the 1,148 shipped roles are, overriding properties such as `MaxSpeed` under `Modify`, and none of them overrides `Instructions`.
- **Spawn an NPC from an item or block** — [SpawnNPC interaction](npc-spawning.md#spawnnpc-interaction). Key: `"Type": "SpawnNPC"`.
- **Script what happens when an item is used** — [the item's Interactions property](items.md#interactions-property), then [Interactions: Quick Start](interactions.md#quick-start). Key: `Interactions`. Example: [custom-food](../examples/custom-food/Server/Item/Items/Food/Food_Hearty_Snack.json) overrides what eating does, through `InteractionVars`.
- **Customize world generation** — [Asset layout](worldgen.md#asset-layout), [binding a world to its structure](universe-saves.md#worldgen--binding-to-a-structure). Key: `WorldStructures/*.json`, which a world's `WorldGen.WorldStructure` selects by file name.
- **Animate a block** — [A door animation](blockyanim-format.md#simple-door-animation), [attaching it](blockyanim-format.md#integration-with-blocks). Key: `CustomModelAnimation`.

## How to read a page

- **Doc type.** The line under each title says what the page documents, for example a Java API, a JSON asset format, a UI DSL, a guide or an index. A page can be two of these.
- **Verified against.** On a topic page that line also carries the game build whose server jar and assets the page was checked against. A page whose stamp is older than the build named above has not been re-checked since. The navigation pages (Home, Overview, Index, Structure, Examples) carry no stamp.
- **Gotchas & Errors.** Most pages have a section of that name: the errors and silent failures the page's API produces, with causes and fixes. Read it before you copy an example.

## More

- [Examples](examples.md): the runnable mods in the repository, with the pages each pairs with.
- [Documentation index](01-index.md): the reference pages by topic and by type.
- [Directory structure](02-structure.md): pack and plugin layout, and manifests.
- [`llms.txt`](llms.txt): for AI tools, a plain-text list of the pages with a description of each.
