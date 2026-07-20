# Events Example

Demonstrates Hytale's two event mechanisms side by side:

| Mechanism | Registered via | Runs | Use for |
|-----------|----------------|------|---------|
| **Global event bus** | `getEventRegistry().register(...)` | outside the ECS | server-level events: `PlayerConnectEvent`, `PlayerDisconnectEvent`, … |
| **ECS event system** | `getEntityStoreRegistry().registerSystem(...)` | on the world thread, per matching entity | gameplay events with entity context: `BreakBlockEvent`, `PlaceBlockEvent`, … |

What it does in game:

- Sends a welcome chat message when a player connects (global bus; the
  `EventRegistration` handle is kept so the handler could be unregistered).
- Logs each disconnect with the engine's `DisconnectReason` (global bus).
- Messages the player naming the block type and position whenever they break a
  block (`BreakBlockNotifierSystem`, an `EntityEventSystem` filtered to
  entities with a `Player` component via `getQuery()`).

`BreakBlockEvent` is cancellable (`event.setCancelled(true)`) — the system's
comment shows where a region-protection plugin would veto the break.

## Build & deploy

```bash
./gradlew build   # or build.bat on Windows
./deploy.sh       # or deploy.bat — copies the jar into the Hytale mods dir
```

See [docs/events.md](../../docs/events.md) for the full event-system reference.
