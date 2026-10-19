---
title: "Getting Started with Hytale Modding"
description: "Get started with Hytale modding — an introduction to building server plugins and asset packs, the toolchain, project structure, and where to go next."
seo:
  type: TechArticle
---

# Getting Started with Hytale Modding

**Doc type:** Guide

Welcome to the Hytale Plugin & Asset documentation. This guide will help you get started creating custom content for Hytale servers.

> **Looking for a quick reference?** See the [Documentation Index](01-index.md) for a complete list of all files, asset types, and Java classes.

## What This Documentation Covers

This documentation covers two main areas:

1. **Java Plugins** - Server-side code that adds commands, events, and custom logic
2. **Asset Definitions** - JSON files that define items, weapons, NPCs, world generation, and more

Most custom content in Hytale is created through asset definitions rather than code. The data-driven approach means you can create new weapons, tools, and items by writing JSON files that inherit from templates.

For details on how to organize your files, see [Pack vs Plugin Directory Structure](02-structure.md).

## Your First Custom Asset

The easiest way to start modding is to create a custom weapon or tool. Hytale provides templates that handle all the combat logic, animations, and effects - you just customize the properties.

### Creating a Custom Weapon

The [Weapon Items](items-weapons.md) documentation shows how to create weapons using templates. The **Iron Sword example** demonstrates the pattern:

1. Inherit from a template (e.g., `Template_Weapon_Sword`)
2. Set your model, texture, and icon
3. Define quality, durability, and item level
4. Configure damage values through `InteractionVars`

See the [Iron Sword example](items-weapons.md#example-child-iron-sword) for a complete working definition.

### Creating a Custom Tool

Tools follow the same inheritance pattern. The [Tool Items](items-tools.md) documentation covers pickaxes, axes, shovels, and other gathering tools with examples showing how to customize mining speed and durability.

## Common Tasks

| Task | Documentation |
|------|---------------|
| Create a custom weapon | [Weapon Items](items-weapons.md) |
| Create a custom tool | [Tool Items](items-tools.md) |
| Add a server command | [Commands](commands.md) |
| Build custom UI | [UI System](ui.md) |
| Understand interactions | [Interactions](interactions.md) |
| Define crafting recipes | [Crafting System](items-crafting.md) |
| Configure NPC behaviors | [NPC Roles](npc-roles.md) |
| Customize world generation | [World Generation](worldgen.md) |
| Animate blocks | [Block Animation Format](blockyanim-format.md) |

## Documentation Structure

The reference pages cluster into these areas:

- **Core** - Plugin lifecycle, commands, events, and ECS components
- **Items** - Weapons, tools, consumables, and crafting
- **Interactions** - Combat system, combo chains, and ability effects
- **World** - Blocks, prefabs, world management, and saves/universes
- **World Generation** - Zones, biomes, terrain, and caves
- **Entities** - Players, NPCs, encounters, and entity systems
- **UI** - Custom pages, HUD, and styling

The index groups the same pages two other ways: by **documentation type** (Java API,
JSON asset format, UI DSL, guide) and by **topic**.

For a complete list of all documentation files with descriptions, see the [Documentation Index](01-index.md).

## Next Steps

### Working Examples

The repository's `examples/` directory holds no-code packs and working Gradle plugins. The [Examples](examples.md) page says what each one demonstrates, which pages of this handbook it pairs with, and how to install it, or to build and deploy it. Start with a pack: `custom-food` needs a text editor and no compiler.

### Reference Files

Your Hytale installation contains useful reference files:

- **HytaleServer.jar** (`...install/release/package/game/latest/Server/`) - Decompile to explore API classes
- **Assets.zip** (`...install/release/package/game/latest/`) - Contains all vanilla asset definitions as examples

The install root is `%APPDATA%\Hytale\` on Windows and `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/` on the Linux Flatpak launcher. See [CLAUDE.md](../CLAUDE.md) for extracting `Assets.zip` to inspect assets on Linux.
