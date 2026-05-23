# Entity Count Example Plugin

Demonstrates the **ECS ticking-system** pattern — the foundational primitive the
other examples skip — by counting the entities in the world every tick and
streaming the totals to a live HUD overlay.

This example deliberately wires several subsystems together so you can see how
they compose:

- an **ECS ticking system** (`EntityTickingSystem`) that runs on the world thread,
- the **component query** API to count and classify entities, and
- a **custom HUD** (`CustomUIHud`) that the system updates in place.

## Commands

### `/entitycount <show|hide>`
Toggles the entity-count HUD in the top-right corner.

- `/entitycount show` — shows the overlay; numbers then update ~4×/second
- `/entitycount hide` — hides the overlay

The HUD displays:
- **Total** — every entity in the world's store (`store.getEntityCount()`)
- **Players** — entities with a `Player` component (`store.getEntityCountFor(Player.getComponentType())`)
- **NPCs** — entities with an `NPCMarkerComponent` (`store.getEntityCountFor(NPCMarkerComponent.getComponentType())`)
- **Other** — the remainder (`Total − Players − NPCs`): projectiles, dropped items, and internal entities

To see the numbers move, walk near mobs, drop items, or have another player join.

> **ECS aside:** there is no "mob" or "NPC" entity *type* in Hytale — every
> creature is a generic entity tagged with an `NPCMarkerComponent`. You don't
> ask "what type is this entity?", you ask "which components does it carry?".
> That is why each HUD line is a component query, and why **Total counts the
> store, not visible objects** — the store also holds internal entities.

## How it works

The interesting part is the split of responsibilities:

| Piece | Role |
|-------|------|
| `EntityCountCommand` | Handles user intent — shows/hides the HUD, records it in the registry. Never computes a count. |
| `EntityCountTickingSystem` | Runs every tick on the world thread. Reads counts from the `Store` and pushes them to each player's HUD. |
| `EntityCountHud` | A "dumb" overlay — knows how to render and update its labels, nothing else. |
| `HudRegistry` | Shared map of active HUDs by player UUID; the bridge between command and system. |

Because an `EntityTickingSystem` is invoked by the engine **on the world thread**,
it is safe to query the `Store` directly inside `tick()` — no manual threading or
locking. The system filters to players via `getQuery()`, so `tick()` is called
once per player per tick, and uses the `deltaTime` argument to throttle HUD
refreshes instead of updating on every single tick.

## Building

```batch
build.bat
```

Or (portable):

```bash
./gradlew build
```

## Installation

```bash
./deploy.sh     # Linux / bash
deploy.bat      # Windows
```

Or copy `build/libs/example-entity-count.jar` to your Mods folder manually.

**Important:** `manifest.json` must have `"IncludesAssetPack": true` for the
`.ui` file to load.

## Code Structure

- `EntityCountPlugin.java` — main plugin class; registers the command and the ticking system
- `EntityCountCommand.java` — `/entitycount <show|hide>`; toggles the HUD
- `EntityCountTickingSystem.java` — the ECS ticking system that counts entities and updates HUDs
- `EntityCountHud.java` — custom HUD overlay with an `updateCounts()` method
- `HudRegistry.java` — shared registry of active HUDs keyed by player UUID
- `Common/UI/Custom/EntityCountHud.ui` — HUD layout (DSL format)

## Related docs

- [`docs/components.md`](../../docs/components.md) — ECS, queries, and ticking systems
- [`docs/events.md`](../../docs/events.md) — `EntityEventSystem` (event-driven counterpart)
- [`docs/ui-api.md`](../../docs/ui-api.md) — `CustomUIHud` and `UICommandBuilder`
