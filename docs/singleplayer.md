# Singleplayer API

**Doc type:** Java API · **Verified against build-12**

Events for singleplayer-specific functionality.

This page covers the event fired in singleplayer/local server mode when an access level is requested.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.singleplayer` and provides:
- A singleplayer access-request event (`SingleplayerRequestAccessEvent`) exposing the requested `Access` level

## Architecture
```
com.hypixel.hytale.server.core.modules.singleplayer
└── SingleplayerRequestAccessEvent (IEvent<Void>)
    └── getAccess() → Access (requested access level)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `SingleplayerRequestAccessEvent` | `server.core.modules.singleplayer` | Fired when singleplayer requests a specific access level |

---

## SingleplayerRequestAccessEvent

**Package:** `com.hypixel.hytale.server.core.modules.singleplayer`

Implements `IEvent<Void>`. Fired when singleplayer requests a specific access level.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAccess()` | `Access` | The requested access level |

> **See also:** [Event Registry](plugin-lifecycle.md#pluginevent-base-class)

---

## Usage Example

```java
import com.hypixel.hytale.server.core.modules.singleplayer.SingleplayerRequestAccessEvent;

@Override
protected void setup() {
    // Listen for singleplayer access requests
    getEventRegistry().register(SingleplayerRequestAccessEvent.class, event -> {
        System.out.println("Singleplayer requesting access: " + event.getAccess());
    });
}
```

> **See also:** [Player API](player.md)

---

## Notes

- This event is specific to singleplayer/local server mode
- Use this to customize behavior based on access level in singleplayer scenarios

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 singleplayer module (verified against `HytaleServer.jar`).

- **`SetServerAccess can only be used by the owner of the singleplayer world!`** / **`UpdateServerAccess can only be by the owner of the singleplayer world!`** → a non-owner attempted to set or change the singleplayer world's access level. Fix: only the world owner may change access; gate any access-changing logic on owner identity.
- **`Offline singleplayer mode requires the game must be launched through the official launcher.`** → offline singleplayer was started outside the official launcher. Fix: launch through the official Hytale launcher.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
