---
title: "Permissions API"
description: "Check Hytale permissions in Java — the PermissionHolder interface (implemented by Player), permission checks with default values, command-level permissions, and permission events."
seo:
  type: TechArticle
---

# Permissions API

**Doc type:** Java API · **Verified against 0.5.2**

This page covers the role-based permission system: checking permissions on players and commands, the built-in group hierarchy, registering your own permission nodes and groups, swapping the permission backend, and the events fired when player or group permissions change.

> **Reworked in Update 5.** Permissions are now **role-based and no longer tied to game mode**. `/op` is a *group*
> (`hytale:Admin`) rather than a flag that grants everything; groups support **inheritance**, permission nodes are
> **namespaced** (`hytale.editor.asset`), and the backing store is a swappable `PermissionProvider`. The old
> game-mode-keyed command API (`setPermissionGroup(GameMode)`) is deprecated in favour of
> `setPermissionGroups(String...)`.

## Overview

Implemented in `com.hypixel.hytale.server.core.permissions` (with permission events in `com.hypixel.hytale.server.core.event.events.permissions`) and provides:
- A `PermissionHolder` interface for permission checks (implemented by `Player`)
- A role/group model with inheritance, served by a pluggable `PermissionProvider` (default: disk-backed `HytalePermissionsProvider`)
- `PermissionsModule` — register permission nodes, assign users/groups, swap providers
- Namespaced node + group naming, validated by `PermissionValidation`
- Command-level gating via `requirePermission()` / `setPermissionGroups(String...)`
- Events for player permission, player group, and group permission changes

## Architecture
```
Permission checks
├── PermissionHolder (Player implements it)
│   └── hasPermission(node) / hasPermission(node, default)   (Admin group holds "*" = all)
├── PermissionsModule (singleton; register nodes, assign users/groups, manage providers)
│   └── PermissionProvider (SPI)  ── default: HytalePermissionsProvider (permissions.json on disk)
│         └── groups with inheritance: None ← Adventurer ← Builder ← WorldEditor ← ServerEditor ← Admin
├── HytalePermissions (node + group name constants; fromCommand(...) helper)
├── PermissionValidation (isValidPermissionNode / isValidGroupName)
└── Command gating (requirePermission(node) / setPermissionGroups(group...))

Permission Events (event.events.permissions)
├── PlayerPermissionChangeEvent (base; PermissionsAdded / PermissionsRemoved / GroupAdded / GroupRemoved)
│   └── PlayerGroupEvent (Added / Removed)
└── GroupPermissionChangeEvent (Added / Removed)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `PermissionHolder` | `server.core.permissions` | Interface for entities that can hold permissions; `Player` implements it |
| `PermissionsModule` | `server.core.permissions` | Core module (`get()` singleton): register nodes, assign users/groups, manage providers, `reload()` |
| `HytalePermissions` | `server.core.permissions` | Built-in node/group name constants + `fromCommand(...)` node helper |
| `PermissionValidation` | `server.core.permissions` | `isValidPermissionNode(String)` / `isValidGroupName(String)` |
| `PermissionProvider` | `server.core.permissions.provider` | SPI for the permission backend (users, groups, inheritance) |
| `HytalePermissionsProvider` | `server.core.permissions.provider` | Default disk-backed provider; defines the built-in groups |
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

A holder is granted a node if it (or one of its groups, walking the inheritance chain) holds that exact node — or the wildcard `*`. The `hytale:Admin` group holds `*`, which is why operators pass every check.

## Groups & Roles

A player's permissions come from the **groups** they belong to (plus any user-specific grants). Groups form an
**inheritance chain** — a child group inherits everything its parent has. The built-in groups (constants on
`HytalePermissionsProvider`) escalate like this:

```
hytale:None  ←  hytale:Adventurer  ←  hytale:Builder  ←  hytale:WorldEditor  ←  hytale:ServerEditor  ←  hytale:Admin
 (nothing)        (default play)        (build perms)      (world editing)        (asset packs)         (holds "*")
```

| Group constant | Name | Role |
|----------------|------|------|
| `GROUP_NONE` | `hytale:None` | No permissions |
| `GROUP_ADVENTURER` | `hytale:Adventurer` | Normal gameplay — the **default** group for new players (`DEFAULT_GROUP`) |
| `GROUP_BUILDER` | `hytale:Builder` | Building / fly-cam |
| `GROUP_WORLD_EDITOR` | `hytale:WorldEditor` | Builder-tool / prefab / selection editing |
| `GROUP_SERVER_EDITOR` | `hytale:ServerEditor` | Asset-editor / pack management |
| `GROUP_ADMIN` | `hytale:Admin` | Everything (holds the `*` wildcard); this is the `OP_GROUP` that `/op` assigns |

So **`/op` no longer means "all flags on"** — it adds a player to `hytale:Admin`, a normal group that happens to
hold `*`. You can re-scope what admin can do, or assign any other group instead.

`HytalePermissionsProvider.resolveGroupName(String)` accepts friendly aliases: `op` → `hytale:Admin`,
`default`/`adventure`/`adventurer` → `hytale:Adventurer`, `creative` → `hytale:WorldEditor`.

## Permission Node & Group Naming

Nodes are **dot-namespaced** under a namespace prefix (the engine's own nodes use `hytale.…`, e.g.
`hytale.editor.asset`, `hytale.camera.flycam`). **Use your own namespace** for plugin nodes (e.g.
`myplugin.shop.admin`) — don't register under `hytale.`.

Group names are namespaced with a colon (`hytale:Builder`, `myplugin:Moderator`). Validate either form before use:

```java
PermissionValidation.isValidPermissionNode("myplugin.shop.admin");  // node form
PermissionValidation.isValidGroupName("myplugin:Moderator");        // group form
```

Command nodes follow a fixed convention via `HytalePermissions`:

```java
HytalePermissions.COMMAND_BASE;                 // the command node prefix ("hytale.command")
String node = HytalePermissions.fromCommand("tp");        // the node for command "tp"
String sub  = HytalePermissions.fromCommand("perm", "reload");  // node for a subcommand
```

## PermissionsModule

The core module (`PermissionsModule.get()`) is where you **register permission nodes** and **assign** users/groups
at runtime. Registering a node also declares which groups receive it by default.

```java
PermissionsModule perms = PermissionsModule.get();

// Declare a node (optionally granting it to default groups)
PermissionsModule.registerPermission("myplugin.shop.use");
PermissionsModule.registerPermission("myplugin.shop.admin", "hytale:Admin");

// Assign groups / users
perms.addUserToGroup(playerUuid, "myplugin:Moderator");
perms.setUserGroup(playerUuid, "hytale:Builder");      // replace the user's group
perms.removeUserFromGroup(playerUuid, "myplugin:Moderator");

// Grant nodes directly
perms.addGroupPermission("myplugin:Moderator", Set.of("myplugin.shop.admin"));
perms.addUserPermission(playerUuid, Set.of("myplugin.shop.use"));

// Inspect
Set<String> groups = perms.getGroupsForUser(playerUuid);
Set<String> all    = perms.getAllRegisteredGroups();
Map<String, Set<String>> nodes = PermissionsModule.getRegisteredPermissions();

perms.reload();   // re-read the provider's backing store (also exposed as /perm reload)
```

> Register nodes during your plugin's `setup()` so they exist before checks/commands run. Changes made through the
> module are persisted by the active provider.

## Custom PermissionProvider

The backend that actually stores users, groups, and inheritance is a `PermissionProvider`
(`com.hypixel.hytale.server.core.permissions.provider`). The default is the disk-backed
`HytalePermissionsProvider` (writes `permissions.json`). To back permissions with your own source (a database, an
external auth service), implement the SPI and register it:

```java
PermissionsModule.get().addProvider(myProvider);   // removeProvider(...) / getProviders() also available
```

Key SPI methods (all on `PermissionProvider`):

| Method | Purpose |
|--------|---------|
| `getName()` | Provider identifier |
| `getUserPermissions(UUID)` / `addUserPermissions(UUID, Set)` / `removeUserPermissions(...)` | Per-user nodes |
| `getGroupPermissions(String)` / `addGroupPermissions(...)` / `removeGroupPermissions(...)` | Per-group nodes |
| `getGroupsForUser(UUID)` / `addUserToGroup(...)` / `removeUserFromGroup(...)` / `setUserGroup(...)` | Group membership |
| `getGroupParent(String)` | The parent group (drives **inheritance**) |
| `getEffectiveGroupPermissions(String)` | Inheritance-resolved node set for a group |
| `getAllRegisteredGroups()` | All known groups |

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

`AbstractCommand` offers two ways to gate a command (call them in the constructor, before registration):

```java
public class AdminCommand extends AbstractPlayerCommand {
    public AdminCommand() {
        super("admin", "Admin-only command");

        // (a) Require a specific node — grant it to whichever group(s) you choose.
        requirePermission("myplugin.admin");

        // (b) Or assign the command to permission group(s) directly (Update 5).
        // setPermissionGroups("hytale:Admin");
    }
}
```

| Method | Use |
|--------|-----|
| `requirePermission(String node)` | Gate on a specific permission node |
| `setPermissionGroups(String... groups)` | Assign the command to permission group(s) — the role-based form |
| `setPermissionGroup(GameMode)` | **Deprecated** (Update 5) — the old game-mode-keyed form; use `setPermissionGroups(String...)` |
| `canGeneratePermission()` | Override to `false` to skip the auto-generated per-command node |

If you don't gate explicitly, a command auto-generates a node (`HytalePermissions.fromCommand(name)` →
`hytale.command.<name>`) that ordinary players (`hytale:Adventurer`) don't hold — so it reads as "no permission"
until granted (the `hytale:Admin` wildcard `*` is why ops can always run it). Override `canGeneratePermission()` to
return `false` for a command any player should run. (`CommandUtil.requirePermission(holder, node)` is the static
check used internally.)

Players without the required permission won't be able to execute the command.

> **See also:** [Commands API](commands.md#other-abstractcommand-methods)

---

## Permission Commands (in-game)

The permissions module ships management commands (all support **tab-autocomplete** as of Update 5, so the exact
argument forms are discoverable in chat):

| Command | Purpose |
|---------|---------|
| `/perm group …` | Manage group permissions and inheritance |
| `/perm user …` | Manage a user's groups / permissions |
| `/perm list …` | List groups / nodes |
| `/perm test …` | Test whether a node resolves for a user |
| `/perm reload` | Reload the provider's backing store (`PermissionsModule.reload()`) |
| `/setgroup …` | Set a player's group |
| `/op`, `/op add <player>`, `/op remove <player>` | Add/remove a player from `hytale:Admin` |

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

## Access Control (Bans & Whitelist)

**Package:** `com.hypixel.hytale.server.core.modules.accesscontrol`

A separate subsystem from permissions, access control decides **whether a player may connect at all** (bans, whitelist) rather than what an already-connected player is allowed to do. It ships as a core `JavaPlugin` module (`AccessControlModule`) and provides the built-in `/ban`, `/unban`, and `/whitelist …` commands — but it is also an **extension point**: a plugin can register its own access source.

### Key Classes

| Class | Description |
|-------|-------------|
| `AccessControlModule` | Core module; singleton via `AccessControlModule.get()`. Registration entry points below |
| `AccessProvider` (SPI, `.provider`) | A pluggable access source. `getDisconnectReason(UUID)` returns `CompletableFuture<Optional<Message>>` — a present `Message` denies the connection with that reason; empty allows it |
| `Ban` (SPI, `.ban`) | Extends `AccessProvider`; a single ban with `getTarget()`, `getBy()`, `getTimestamp()`, `getReason()`, `isInEffect()`, `getType()`, `toJsonObject()` |
| `BanParser` (SPI, `.ban`) | Deserializes a `Ban` from a `JsonObject` (`parse(JsonObject)`); register one per ban `type` string |
| `InfiniteBan` / `TimedBan` | Built-in `Ban` implementations (permanent / time-limited) |

### Registering a custom provider

`AccessControlModule.get()` exposes:

| Method | Description |
|--------|-------------|
| `registerAccessProvider(AccessProvider)` | Add a custom gate consulted on every connection |
| `registerBanParser(String type, BanParser)` | Register a deserializer for a custom ban `type` |
| `parseBan(String type, JsonObject)` | Parse a stored ban via the registered parser for `type` |

```java
AccessControlModule.get().registerAccessProvider(uuid ->
    isOnMyExternalBlocklist(uuid)
        ? CompletableFuture.completedFuture(Optional.of(Message.raw("Blocked by external list")))
        : CompletableFuture.completedFuture(Optional.empty()));
```

> [!WARNING]
> Verified against `HytaleServer.jar`. No first-party content plugin in build-12 references this module, so the registration entry points are documented from their signatures; the lifecycle timing (when during startup to call `registerAccessProvider`) is not demonstrated by an inspectable plugin — register during your plugin `setup()` and test against your target build.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the 0.5.0 server (verified against `HytaleServer.jar`).

- **`Cannot change permissions after a command has already been registered`** → `requirePermission(...)`, `setPermissionGroups(...)`, or another permission setter was called after the command was registered. Fix: call it in the command constructor, before `registerCommand()`.
- **Symptom:** `hasPermission("node")` returns `false` for a node nobody has explicitly set → the single-arg overload defaults to `false` when the node is unset. Fix: use `hasPermission("node", true)` when "unset" should mean allowed (see [With Default Value](#with-default-value)).
- **Symptom:** a freshly registered command replies *"no permission"* for ordinary players even without `requirePermission(...)` → every command auto-generates a node (`hytale.command.<name>`) that the default `hytale:Adventurer` group doesn't hold; only `hytale:Admin` (via the `*` wildcard) does. Fix: override `canGeneratePermission()` to return `false`, or grant the node to a group via `PermissionsModule`. See [Commands: Permission model](commands.md#permission-model-why-a-new-command-says-no-permission).
- **Symptom:** `setPermissionGroup(GameMode)` no longer behaves as expected → it's **deprecated** in Update 5 and permissions are no longer game-mode-keyed. Fix: use `setPermissionGroups(String...)` with group names (e.g. `"hytale:Admin"`).
- **Symptom:** a registered permission node or group name is silently rejected → it failed validation. Fix: namespace nodes (`myplugin.feature`) and groups (`myplugin:Role`), and pre-check with `PermissionValidation.isValidPermissionNode` / `isValidGroupName`.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
