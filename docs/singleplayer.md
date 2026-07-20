---
title: "Singleplayer API"
description: "The Hytale singleplayer API in Java — the SingleplayerRequestAccessEvent exposing the requested Access level for gating singleplayer access."
seo:
  type: TechArticle
---

# Singleplayer API

**Doc type:** Java API · **Verified against 0.5.7**

Events for singleplayer-specific functionality.

This page covers the event fired in singleplayer/local server mode when an access level is requested.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.singleplayer` and provides:
- A singleplayer access-request event (`SingleplayerRequestAccessEvent`) exposing the requested `Access` level
- The `SingleplayerModule` itself — owner identity (`getUuid()` / `isOwner(...)`), the current/requested `Access` level, and `requestServerAccess(...)`

## Architecture
```
com.hypixel.hytale.server.core.modules.singleplayer
├── SingleplayerModule (JavaPlugin; SingleplayerModule.get())
│   ├── owner identity: getUuid() / getUsername() / isOwner(...)
│   └── access level: getAccess() / requestServerAccess(Access)
└── SingleplayerRequestAccessEvent (IEvent<Void>)
    └── getAccess() → Access (requested access level)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `SingleplayerRequestAccessEvent` | `server.core.modules.singleplayer` | Fired when singleplayer requests a specific access level |
| `SingleplayerModule` | `server.core.modules.singleplayer` | Module singleton: world-owner identity and the shared-access level |

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

## SingleplayerModule

**Package:** `com.hypixel.hytale.server.core.modules.singleplayer`

The core module (`extends JavaPlugin`) behind singleplayer/local-server behavior. Obtain it with `SingleplayerModule.get()`. Its most useful surface is the **static owner-identity helpers**, which work off the launch options the client passes to the local server:

| Member | Return Type | Description |
|--------|-------------|-------------|
| `SingleplayerModule.get()` | `SingleplayerModule` | Static module singleton |
| `getUuid()` | `UUID` | *(static)* The world owner's UUID |
| `getUsername()` | `String` | *(static)* The world owner's username |
| `isOwner(PlayerRef)` | `boolean` | *(static)* Whether this player is the world owner |
| `isOwner(UUID)` | `boolean` | *(static)* Same, by UUID |
| `getAccess()` | `Access` | Current access level of the local server |
| `getRequestedAccess()` | `Access` | Access level currently being requested/negotiated |
| `requestServerAccess(Access)` | `void` | Ask the client/launcher to share the world at the given level; binds a network port for anything above `Private` |
| `checkClientPid()` | `void` | *(static)* Shuts the server down if the owning client process is gone (run automatically every 60s when launched by the client) |

`Access` (`com.hypixel.hytale.protocol.packets.serveraccess.Access`) has four levels: `Private`, `LAN`, `Friend`, `Open`.

```java
import com.hypixel.hytale.server.core.modules.singleplayer.SingleplayerModule;

// Gate an admin-ish feature to the world owner in singleplayer
if (SingleplayerModule.isOwner(playerRef)) {
    // owner-only behavior
}
```

> `requestServerAccess` throws `IllegalArgumentException` (`Server access can only be modified in singleplayer!`) on a dedicated server — guard with `Constants.SINGLEPLAYER` semantics (the module only registers its access provider and connect hooks in singleplayer mode). On dedicated servers the owner-identity helpers are meaningless (`getUuid()` reflects a launch option that isn't set).

---

## Notes

- This event is specific to singleplayer/local server mode
- Use this to customize behavior based on access level in singleplayer scenarios

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 singleplayer module (verified against `HytaleServer.jar`).

- **`SetServerAccess can only be used by the owner of the singleplayer world!`** / **`UpdateServerAccess can only be by the owner of the singleplayer world!`** → a non-owner attempted to set or change the singleplayer world's access level. Fix: only the world owner may change access; gate any access-changing logic on owner identity.
- **Symptom:** offline singleplayer refuses to start when the game was launched outside the official launcher, with a message like "Offline singleplayer mode requires the game must be launched through the official launcher." That text is **client/launcher-side** — it does not appear in `HytaleServer.jar` (the server's own related string is `offline mode is only valid in singleplayer`, logged when a remote connection arrives in offline mode). Fix: launch through the official Hytale launcher.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
