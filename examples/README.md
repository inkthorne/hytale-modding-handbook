# Examples

Each subdirectory demonstrates one aspect of Hytale modding. Most are standalone
Gradle/Java **plugins**; `custom-food/` is a no-code **pack** (pure JSON). They're
ordered roughly from simplest to most involved — if you write code, start with
`commands/`; if you don't, start with `custom-food/`.

| Example | Type | What it demonstrates | Commands |
|---------|------|----------------------|----------|
| [commands/](./commands/) | Plugin | The command system: registering commands and reading arguments | `/hello`, `/tp <x> <y> <z>` |
| [ui/](./ui/) | Plugin | Custom UI pages and HUD management | `/menu`, `/hud <show\|hide>`, `/statushud <show\|hide\|update>` |
| [inventory/](./inventory/) | Plugin | The inventory API: item stacks, containers, transactions | `/give <item> <qty>`, `/inv-clear <section>` |
| [entity-count/](./entity-count/) | Plugin | The ECS ticking-system pattern: per-tick code that reads the entity store | `/entitycount <show\|hide>` |
| [custom-food/](./custom-food/) | Pack | Pure-JSON content: a custom food item from a template, no code or art | — |

## What each one covers

### [commands/](./commands/)
The starting point. Shows how to register a command, declare required arguments,
and read them when the command runs — including relative position arguments
(`~10 ~ ~-5`) for the teleport command.

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

### [custom-food/](./custom-food/)
The no-code starting point. A **pack** — pure JSON, no Gradle and no Java. It adds a
custom food item by extending the game's real `Template_Food`, reusing an existing
in-game icon and shipped heal/buff effects (so there's nothing to compile or draw).
Teaches the "copy a template, override a few fields" pattern that underlies most JSON
modding. See its own [README](./custom-food/README.md) for install/test steps —
it deploys by copying the folder, not by building a jar.

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
