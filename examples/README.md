# Examples

Each subdirectory is a standalone Gradle project demonstrating one aspect of the
Hytale plugin API. They're ordered roughly from simplest to most involved — if
you're new, start with `commands/`.

| Example | What it demonstrates | Commands |
|---------|----------------------|----------|
| [commands/](./commands/) | The command system: registering commands and reading arguments | `/hello`, `/tp <x> <y> <z>` |
| [ui/](./ui/) | Custom UI pages and HUD management | `/menu`, `/hud <show\|hide>`, `/statushud <show\|hide\|update>` |
| [inventory/](./inventory/) | The inventory API: item stacks, containers, transactions | `/give <item> <qty>`, `/inv-clear <section>` |
| [entity-count/](./entity-count/) | The ECS ticking-system pattern: per-tick code that reads the entity store | `/entitycount <show\|hide>` |

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

## Building and deploying

Each example builds independently from its own directory:

```bash
./gradlew build     # build the plugin jar
./deploy.sh         # build (if needed) and copy it into the Hytale Mods folder
```

On Windows use `build.bat` / `deploy.bat`. See the top-level
[README](../README.md#build-commands) for the Mods folder location per platform.

## Shared configuration

These files are shared by every example so the Hytale install path is defined in
one place (all resolve `APPDATA` first, then the Linux Flatpak install, then a
fallback):

- `hytale-paths.gradle` — used by each `build.gradle` to locate `HytaleServer.jar`
- `hytale-paths.bat` — used by `deploy.bat` scripts (Windows)
- `hytale-paths.sh` — used by `deploy.sh` scripts (Linux / bash)
