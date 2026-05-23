# Permissions API

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
