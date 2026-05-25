# Examples

Each subdirectory demonstrates one aspect of Hytale modding. `custom-food/` is a
no-code **pack** (pure JSON); the rest are standalone Gradle/Java **plugins**.
They're ordered simplest to most involved — **start with `custom-food/`** (no code,
no build), then move on to the plugins once you want to run code.

| Example | Type | What it demonstrates | Commands |
|---------|------|----------------------|----------|
| [custom-food/](./custom-food/) | Pack | Pure-JSON content: a custom food item from a template, no code or art | — |
| [custom-drop/](./custom-drop/) | Pack | Pure-JSON loot tables: override a creature's drop table so your item drops in the world | — |
| [commands/](./commands/) | Plugin | The command system: registering commands and reading arguments | `/hello`, `/tp <x> <y> <z>` |
| [ui/](./ui/) | Plugin | Custom UI pages and HUD management | `/menu`, `/hud <show\|hide>`, `/statushud <show\|hide\|update>` |
| [inventory/](./inventory/) | Plugin | The inventory API: item stacks, containers, transactions | `/give <item> <qty>`, `/inv-clear <section>` |
| [entity-count/](./entity-count/) | Plugin | The ECS ticking-system pattern: per-tick code that reads the entity store | `/entitycount <show\|hide>` |
| [item-respawner/](./item-respawner/) | Plugin | A stateful, editable placeable block: custom block-entity component + chunk-store ticking + item spawning, persisted across reloads, with a press-F settings GUI | — |

## What each one covers

### [custom-food/](./custom-food/)
The no-code starting point. A **pack** — pure JSON, no Gradle and no Java. It adds a
custom food item by extending the game's real `Template_Food`, reusing an existing
in-game icon and shipped heal/buff effects (so there's nothing to compile or draw).
Teaches the "copy a template, override a few fields" pattern that underlies most JSON
modding. See its own [README](./custom-food/README.md) for install/test steps —
it deploys by copying the folder, not by building a jar.

### [custom-drop/](./custom-drop/)
The level-2 pack — still pure JSON, no build. Where `custom-food` *defines* an item,
this makes it **drop in the world** by overriding a chicken's loot table. Teaches the
drop-system **composition tree** (`Multiple` vs `Choice`, weights, `Empty`, multi-roll)
as a contrast to `custom-food`'s inheritance, plus that an override **replaces the whole
file**. Depends on `custom-food` for the dropped item — packs compose. See its own
[README](./custom-drop/README.md).

### [commands/](./commands/)
The starting point for plugins. Shows how to register a command, declare required
arguments, and read them when the command runs — including relative position
arguments (`~10 ~ ~-5`) for the teleport command.

### [ui/](./ui/)
The UI system. Opens a custom page from a `.ui` layout file, toggles built-in HUD
components on and off, and drives a persistent custom HUD overlay with live
updates.

### [inventory/](./inventory/)
The inventory API. Adds items to a player with proper transaction handling, clears
inventory sections (hotbar / storage / armor / all), and sorts storage. Also
documents the case-sensitive item-ID gotcha.

### [entity-count/](./entity-count/)
The Entity Component System (ECS). An `EntityTickingSystem` runs every tick on the
world thread, counts entities by the components they carry
(`Total` / `Players` / `NPCs` / `Other`), and pushes the live numbers to a
`CustomUIHud`. The clearest example of "run code on the server's heartbeat."

### [item-respawner/](./item-respawner/)
The most involved example: a **stateful, editable placeable block**. It combines a
custom block-item, a custom **block-entity component** (`Component<ChunkStore>`
with a persistence codec), a **ticking system over the chunk store**
(`EntityTickingSystem<ChunkStore>`), **item-entity spawning**, and a **press-F
settings GUI** bound to the block — a pedestal that drops an item and respawns it
on an interval, only when the previous one is gone, surviving world reloads
without duplicating, with the item and delay editable in-world. The verified
recipe behind it is in
[`docs/blocks.md`](../docs/blocks.md#custom-block-entity-components).

## Building and deploying

The plugin examples build independently from their own directory (`custom-food/` is a
pack — copy the folder into the Mods folder instead, per its README):

```bash
./gradlew build     # build the plugin jar
./deploy.sh         # build (if needed) and copy it into the Hytale Mods folder
```

On Windows use `build.bat` / `deploy.bat`. See the top-level
[README](../README.md#deployment) for the Mods folder location per platform.

## Shared configuration

These files are shared by every example so the Hytale install path is defined in
one place (all resolve `APPDATA` first, then the Linux Flatpak install, then a
fallback):

- `hytale-paths.gradle` — used by each `build.gradle` to locate `HytaleServer.jar`
- `hytale-paths.bat` — used by `deploy.bat` scripts (Windows)
- `hytale-paths.sh` — used by `deploy.sh` scripts (Linux / bash)
