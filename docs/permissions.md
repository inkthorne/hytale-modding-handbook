# Permissions API

**Doc type:** Java API · **Verified against build-12**

This page covers checking permissions on players and commands, plus events fired when player or group permissions change.

## Overview

Implemented in `com.hypixel.hytale.server.core.permissions` (with permission events in `com.hypixel.hytale.server.core.event.events.permissions`) and provides:
- A `PermissionHolder` interface for permission checks (implemented by `Player`)
- Permission checks with optional default values
- Command-level permission gating via `AbstractCommand.requirePermission()`
- Events for player permission, player group, and group permission changes

## Architecture
```
Permission checks
├── PermissionHolder (Player implements it)
│   └── hasPermission(node) / hasPermission(node, default)
└── Command gating (AbstractCommand.requirePermission(node))

Permission Events (event.events.permissions)
├── PlayerPermissionChangeEvent (base; PermissionsAdded / PermissionsRemoved / GroupAdded / GroupRemoved)
│   └── PlayerGroupEvent (Added / Removed)
└── GroupPermissionChangeEvent (Added / Removed)
```

## Key Classes
| Class | Location | Description |
|-------|----------|-------------|
| `PermissionHolder` | `server.core.permissions` | Interface for entities that can hold permissions; `Player` implements it |
| `PlayerPermissionChangeEvent` | `server.core.event.events.permissions` | Abstract base for player permission/group change events |
| `PlayerGroupEvent` | `server.core.event.events.permissions` | Player group membership changes (`Added` / `Removed`) |
| `GroupPermissionChangeEvent` | `server.core.event.events.permissions` | Permission group's permissions change (`Added` / `Removed`) |

## PermissionHolder
**Package:** `com.hypixel.hytale.server.core.permissions`

Interface for entities that can have permissions. `Player` implements this.

### Methods
```java
boolean hasPermission(String permission)
boolean hasPermission(String permission, boolean defaultValue)
```

## Usage

### Check Permission in Command
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    Player player = store.getComponent(ref, Player.getComponentType());

    if (player.hasPermission("myplugin.admin")) {
        // Admin-only action
        playerRef.sendMessage(Message.raw("Admin access granted"));
    } else {
        playerRef.sendMessage(Message.raw("Permission denied"));
    }
}
```

### With Default Value
```java
// Returns true if permission not explicitly set
boolean canUse = player.hasPermission("myplugin.feature", true);

// Returns false if permission not explicitly set
boolean isAdmin = player.hasPermission("myplugin.admin", false);
```

## Command Permissions

Commands can require permissions using `AbstractCommand`:

```java
public class AdminCommand extends AbstractPlayerCommand {
    public AdminCommand() {
        super("admin", "Admin-only command");
        requirePermission("myplugin.admin");  // Require this permission
    }
}
```

Players without the required permission won't be able to execute the command.

> **See also:** [Commands API](commands.md#other-abstractcommand-methods)

---

## Permission Events

**Package:** `com.hypixel.hytale.server.core.event.events.permissions`

Events related to permission changes for players and groups.

> **See also:** [Event Registry](plugin-lifecycle.md#pluginevent-base-class)

### Event Summary

| Class | Description |
|-------|-------------|
| `PlayerGroupEvent` | Player group changes (has `Added` and `Removed` variants) |
| `PlayerPermissionChangeEvent` | Player permissions change |
| `GroupPermissionChangeEvent` | Group permissions change |

---

### PlayerGroupEvent

Fired when a player's group membership changes. Extends `PlayerPermissionChangeEvent`.

**Variants:**
- `PlayerGroupEvent.Added` - Player added to a group
- `PlayerGroupEvent.Removed` - Player removed from a group

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPlayerUuid()` | `UUID` | The UUID of the player whose group changed (inherited) |
| `getGroupName()` | `String` | The group being added/removed |

---

### PlayerPermissionChangeEvent

Abstract base for player permission/group change events.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPlayerUuid()` | `UUID` | The UUID of the player whose permissions changed |

**Subclasses:**

| Class | Methods |
|-------|---------|
| `PlayerPermissionChangeEvent.PermissionsAdded` | `getAddedPermissions(): Set<String>` |
| `PlayerPermissionChangeEvent.PermissionsRemoved` | `getRemovedPermissions(): Set<String>` |
| `PlayerPermissionChangeEvent.GroupAdded` | `getGroupName(): String` |
| `PlayerPermissionChangeEvent.GroupRemoved` | `getGroupName(): String` |

> **Note:** `PlayerGroupEvent` (and its `Added`/`Removed` variants) also extends this base.

---

### GroupPermissionChangeEvent

Abstract base fired when a permission group's permissions change.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getGroupName()` | `String` | The group whose permissions changed |

**Variants:**

| Class | Methods |
|-------|---------|
| `GroupPermissionChangeEvent.Added` | `getAddedPermissions(): Set<String>` |
| `GroupPermissionChangeEvent.Removed` | `getRemovedPermissions(): Set<String>` |

---

### Permission Events Usage Example

```java
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.permissions.*;

@Override
protected void setup() {
    // Listen for player group additions
    getEventRegistry().register(PlayerGroupEvent.Added.class, event -> {
        var playerUuid = event.getPlayerUuid();
        var group = event.getGroupName();
        System.out.println("Player " + playerUuid + " was added to group: " + group);
    });

    // Listen for player group removals
    getEventRegistry().register(PlayerGroupEvent.Removed.class, event -> {
        var playerUuid = event.getPlayerUuid();
        var group = event.getGroupName();
        System.out.println("Player " + playerUuid + " was removed from group: " + group);
    });

    // Listen for player permission additions
    getEventRegistry().register(PlayerPermissionChangeEvent.PermissionsAdded.class, event -> {
        var playerUuid = event.getPlayerUuid();
        var added = event.getAddedPermissions();  // Set<String>
        System.out.println("Player " + playerUuid + " gained permissions: " + added);
    });

    // Listen for group permission additions
    getEventRegistry().register(GroupPermissionChangeEvent.Added.class, event -> {
        var group = event.getGroupName();
        var added = event.getAddedPermissions();  // Set<String>
        System.out.println("Group " + group + " gained permissions: " + added);
    });
}

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 server (verified against `HytaleServer.jar`).

- **`Cannot change permissions after a command has already been registered`** → `requirePermission(...)` (or a permission-group setter) was called after the command was registered. Fix: call `requirePermission("node")` in the command constructor, before `registerCommand()`.
- **Symptom:** `hasPermission("node")` returns `false` for a node nobody has explicitly set → the single-arg overload defaults to `false` when the node is unset. Fix: use `hasPermission("node", true)` when "unset" should mean allowed (see [With Default Value](#with-default-value)).
- **Symptom:** a freshly registered command replies *"no permission"* for ordinary players even without `requirePermission(...)` → every command auto-generates a permission node that only ops hold. Fix: override `canGeneratePermission()` to return `false`, or `requirePermission("node")` and grant it. See [Commands: Permission model](commands.md#permission-model-why-a-new-command-says-no-permission).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
