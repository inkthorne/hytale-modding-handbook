# Hytale Plugin Examples

A reference for Hytale server plugin development with documentation and working examples.

## Documentation

The [docs/](./docs/) directory contains comprehensive API documentation:

### Getting Started
- [Overview](./docs/00-overview.md) - Introduction and getting started
- [Plugin Lifecycle](./docs/plugin-lifecycle.md) - Setup, lifecycle, and server events
- [Permissions](./docs/permissions.md) - Permission system

### Core Systems
- [Components](./docs/components.md) - Entity Component System (ECS)
- [Codecs](./docs/codecs.md) - Serialization and data persistence
- [Networking](./docs/networking.md) - Network protocols
- [Math](./docs/math.md) - Vectors, matrices, shapes

### Commands & UI
- [Commands](./docs/commands.md) - Command system and arguments
- [UI](./docs/ui.md) - Custom UI pages and HUD
- [UI Elements](./docs/ui-elements.md) - UI element types
- [UI Styling](./docs/ui-styling.md) - Styling and layout
- [UI Templates](./docs/ui-templates.md) - Reusable templates
- [UI API](./docs/ui-api.md) - Java UI API
- [i18n](./docs/i18n.md) - Localization

### World & Environment
- [World](./docs/world.md) - World management
- [Blocks](./docs/blocks.md) - Block states and custom blocks
- [Fluids](./docs/fluids.md) - Fluid systems
- [Prefabs](./docs/prefabs.md) - Structure templates
- [Prefab Categories](./docs/prefabs-categories.md) - Category system for prefabs
- [Collision](./docs/collision.md) - Collision queries

### Entities
- [Entities](./docs/entities.md) - Entity hierarchy
- [Player](./docs/player.md) - Player API
- [NPC](./docs/npc.md) - NPC and AI systems
- [NPC Roles](./docs/npc-roles.md) - NPC role templates and behaviors
- [Drops](./docs/drops.md) - Drop system and loot tables
- [Projectiles](./docs/projectiles.md) - Projectile configuration

### Combat & Effects
- [Combat](./docs/combat.md) - Damage and kill feed
- [Effects & Stats](./docs/effects-stats.md) - Status effects and stats

### Items
- [Items](./docs/items.md) - Item definitions overview
- [Block Items](./docs/items-blocks.md) - Block items
- [Consumables](./docs/items-consumables.md) - Consumable items
- [Crafting](./docs/items-crafting.md) - Crafting system
- [Tools](./docs/items-tools.md) - Tool items
- [Weapons](./docs/items-weapons.md) - Weapon templates

### World Generation
- [World Generation](./docs/worldgen.md) - World generation overview
- [Zones](./docs/worldgen-zones.md) - Zone system
- [Biomes](./docs/worldgen-biomes.md) - Biome definitions
- [Terrain](./docs/worldgen-terrain.md) - Terrain layers
- [Caves](./docs/worldgen-caves.md) - Cave system
- [Prefabs](./docs/worldgen-prefabs.md) - Structure placement

### Interactions
- [Interactions](./docs/interactions.md) - Interactions API overview
- [Flow Control](./docs/interactions-flow.md) - Serial, Parallel, Condition
- [Combo System](./docs/interactions-combo.md) - Chaining and charging
- [Context](./docs/interactions-context.md) - Context variables
- [Operations](./docs/interactions-operations.md) - Operation types
- [World Interactions](./docs/interactions-world.md) - Spawning and positioning
- [Combat Interactions](./docs/interactions-combat.md) - Damage and forces

### Assets & Events
- [Assets](./docs/assets.md) - Asset registry
- [Asset Editor](./docs/asset-editor.md) - Editor events
- [Audio](./docs/audio.md) - Audio system
- [Events](./docs/events.md) - Event system overview
- [Adventure](./docs/adventure.md) - Adventure gameplay events
- [Singleplayer](./docs/singleplayer.md) - Singleplayer events

### Utilities
- [Inventory](./docs/inventory.md) - Inventory management
- [Tasks](./docs/tasks.md) - Async task scheduling

## Examples

### [examples/commands/](./examples/commands/)
Demonstrates the command system with:
- Simple no-argument commands
- Commands with position arguments

### [examples/ui/](./examples/ui/)
Demonstrates the UI system with:
- Opening custom UI pages
- Toggling HUD components
- Loading `.ui` definition files

### [examples/inventory/](./examples/inventory/)
Demonstrates the inventory API with:
- Adding items with transaction handling
- Clearing inventory sections
- Inspecting inventory contents
- Sorting storage by name/type/rarity

### [examples/entity-count/](./examples/entity-count/)
Demonstrates the ECS ticking-system pattern with:
- An `EntityTickingSystem` that runs every tick on the world thread
- Counting entities by component (`Total`/`Players`/`NPCs`/`Other`)
- Pushing live values to a `CustomUIHud` overlay

## Requirements

- Hytale installed (uses `HytaleServer.jar` from the local install)
  - **Windows:** `%APPDATA%\Hytale\install\release\package\game\latest\Server\`
  - **Linux (Flatpak launcher):** `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/install/release/package/game/latest/Server/`
- Java 25+
- Gradle (wrapper included)

The build resolves the jar automatically per-platform via `examples/hytale-paths.gradle`.

## Building

Each example can be built independently.

**Windows:**
```batch
cd examples\commands
build.bat        :: build
deploy.bat       :: build and deploy to the mods folder
```

**Linux / macOS** (use the Gradle wrapper directly — the `.bat` scripts are Windows-only):
```bash
cd examples/commands
./gradlew jar    # build (produces build/libs/*.jar)
```

## Deployment

Copy the built JAR from `build/libs/` to the mods folder:
- **Windows:** `%APPDATA%\Hytale\UserData\Mods\`
- **Linux (Flatpak launcher):** `~/.var/app/com.hypixel.HytaleLauncher/data/Hytale/UserData/Mods/`

## Maintenance

The [maintenance/](./maintenance/) directory holds maintainer-only tooling — a
documentation regression checker and the asset baseline used to detect game-build
drift. It is not needed to read the docs or build the examples; see
[maintenance/README.md](./maintenance/README.md) if you're keeping the repo in
sync with a new Hytale build.

## License

MIT License - see [LICENSE](./LICENSE) for details.
