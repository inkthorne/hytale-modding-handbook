---
title: "Permissions API"
description: "Check Hytale permissions in Java — the PermissionHolder interface (implemented by PlayerRef), permission checks with default values, command-level permissions, and permission events."
seo:
  type: TechArticle
---

# Permissions API

**Doc type:** Java API · **Verified against 0.5.9**

This page covers the role-based permission system: checking permissions on players and commands, the built-in group hierarchy, registering your own permission nodes and groups, swapping the permission backend, and the events fired when player or group permissions change.

> **Reworked in Update 5.** Permissions are now **role-based and no longer tied to game mode**. `/op` is a *group*
> (`hytale:Admin`) rather than a flag that grants everything; groups support **inheritance**, permission nodes are
> **namespaced** (`hytale.editor.asset`), and the backing store is a swappable `PermissionProvider`. The old
> game-mode-keyed command API (`setPermissionGroup(GameMode)`) is deprecated in favour of
> `setPermissionGroups(String...)`.

## Overview

Implemented in `com.hypixel.hytale.server.core.permissions` (with permission events in `com.hypixel.hytale.server.core.event.events.permissions`) and provides:
- A `PermissionHolder` interface for permission checks (implemented by `PlayerRef` and `ConsoleSender` — not by the entity `Player`)
- `PermissionQuery` (0.6.3+) — a pre-split node used by the `hasPermission` overloads and by command gating
- A role/group model with inheritance, served by a pluggable `PermissionProvider` (default: disk-backed `HytalePermissionsProvider`)
- `PermissionsModule` — register permission nodes, assign users/groups, swap providers
- Namespaced node + group naming, validated by `PermissionValidation`
- Command-level gating via `requirePermission()` / `setPermissionGroups(String...)`
- Events for player permission, player group, and group permission changes

## Architecture
```
Permission checks
├── PermissionHolder (PlayerRef / ConsoleSender implement it)
│   └── hasPermission(node | PermissionQuery) / hasPermission(…, default)   (Admin group holds "*" = all)
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
| `PermissionHolder` | `server.core.permissions` | Interface for anything that can hold permissions; `PlayerRef` (and `ConsoleSender`) implement it |
| `PermissionQuery` | `server.core.permissions` | (0.6.3+) A node id pre-split into its wildcard/deny forms; `PermissionQuery.of(id)`, `getId()` |
| `PermissionsModule` | `server.core.permissions` | Core module (`get()` singleton): register nodes, assign users/groups, manage providers, `reload()` |
| `HytalePermissions` | `server.core.permissions` | Built-in node constants (`PermissionQuery`s as of 0.6.3) + `fromCommand(...)` / `toolPermission(...)` helpers |
| `PermissionValidation` | `server.core.permissions` | `isValidPermissionNode(String)` / `isValidGroupName(String)` |
| `PermissionProvider` | `server.core.permissions.provider` | SPI for the permission backend (users, groups, inheritance) |
| `HytalePermissionsProvider` | `server.core.permissions.provider` | Default disk-backed provider; defines the built-in groups |
| `PlayerPermissionChangeEvent` | `server.core.event.events.permissions` | Abstract base for player permission/group change events |
| `PlayerGroupEvent` | `server.core.event.events.permissions` | Player group membership changes (`Added` / `Removed`) |
| `GroupPermissionChangeEvent` | `server.core.event.events.permissions` | Permission group's permissions change (`Added` / `Removed`) |

## PermissionHolder
**Package:** `com.hypixel.hytale.server.core.permissions`

Interface for anything that can hold permissions. `PlayerRef` implements it (as does the
console's `ConsoleSender`); the entity component `Player` does **not** — get the `PlayerRef`
from your command's `execute` parameters, from `player.getPlayerRef()`, or from the store
(`PlayerRef.getComponentType()`).

### Methods
```java
boolean hasPermission(String permission)
boolean hasPermission(String permission, boolean defaultValue)
boolean hasPermission(PermissionQuery query)                        // (0.6.3+) default method
boolean hasPermission(PermissionQuery query, boolean defaultValue)  // (0.6.3+) default method
```

`PlayerRef` forwards every overload to `PermissionsModule.get().hasPermission(uuid, …)`; the
single-argument forms default to `false` when the node is unset.

**Resolution (0.6.3):** matching happens **one node set at a time**, and the first set that
says anything decides — it is not a single merged set. For each registered provider, in
order: the user's own grants, then, for each of the user's groups, that group's stored nodes,
its **virtual** nodes, then its parent chain walked upward (capped at 32 groups, so a cycle
degrades to a warning rather than a hang). If nothing matches, `hasPermission` returns the
default value (`false` for the single-argument overloads).

*Virtual* nodes are the group assignments that live in code rather than in `permissions.json`:
the group lists passed to `PermissionsModule.registerPermission(node, groups…)` plus the
`setPermissionGroups(...)` declarations of every registered command (`CommandManager.createVirtualPermissionGroups()`).
They are rebuilt at startup and on every `PermissionsModule.reload()` / `refreshVirtualGroups()`.

Within one node set the query is tested in this order — `-*` (deny all) → `-a.b.c` (exact
deny) → `a.b.c` (exact grant) → deny wildcards, **most specific first** (`-a.b.c.*`, then
`-a.b.*`, then `-a.*`) → `*` → grant wildcards, **least specific first** (`a.*`, then
`a.b.*`, then `a.b.c.*`).

Two consequences worth internalising: within a set a deny beats a grant, but **a user-level
grant is consulted before any group**, so a direct grant overrides a group-level deny; and
the `hytale:Admin` group's `*` is why operators pass every check unless something more
specific denies the node first.

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
| `GROUP_ADMIN` | `hytale:Admin` | Everything (holds the `*` wildcard); the group `/op self` assigns. (The older alias constant `OP_GROUP` still resolves to the same string but is `@Deprecated` as of 0.6.3 — use `GROUP_ADMIN`.) |

So **opping no longer means "all flags on"** — `/op self` (or `/op add <player>`) adds a player to `hytale:Admin`,
a normal group that happens to hold `*`. You can re-scope what admin can do, or assign any other group instead.

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

The engine's own feature nodes are also constants on `HytalePermissions` — as of 0.6.3 they
are `PermissionQuery` values rather than `String`s (`ASSET_EDITOR`, `BUILDER_TOOLS_EDITOR`,
`EDITOR_BRUSH_USE`, `FLY_CAM`, `NO_CLIP`, `SERVER_JOIN`, `WORLD_MAP_MARKER_TELEPORT`, …), so
pass them to the `hasPermission(PermissionQuery)` overload or call `getId()` for the string.
`HytalePermissions.toolPermission(String)` builds `hytale.editor.tool.<toolid>` for editor tools —
it **lowercases** the tool id it is given, so `toolPermission("LaserPointer")` is
`hytale.editor.tool.laserpointer`. The prefix on its own is the `String` constant
`EDITOR_TOOL_BASE` (`"hytale.editor.tool"`); the built-in tools are exposed as the
`PermissionQuery` constants `EDITOR_TOOL_ENTITY`, `EDITOR_TOOL_RULER` and
`EDITOR_TOOL_LASER_POINTER`.

```java
// 0.5.x: playerRef.hasPermission(HytalePermissions.FLY_CAM)          — String
// 0.6.3: still compiles — resolves to the PermissionQuery overload
if (playerRef.hasPermission(HytalePermissions.FLY_CAM)) { /* ... */ }
String id = HytalePermissions.FLY_CAM.getId();   // "hytale.camera.flycam"
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

// Check a user directly (no PlayerRef needed — works for offline players too)
boolean ok = perms.hasPermission(playerUuid, "myplugin.shop.use");
boolean ok2 = perms.hasPermission(playerUuid, PermissionQuery.of("myplugin.shop.use"), false);

perms.reload();   // re-read the provider's backing store (also exposed as /perm reload)
```

Bulk / reverse-lookup helpers added in 0.6.3 (these back the join-grant "whitelist" — see
[Access Control](#access-control-bans--join-permission)):

| Method | Purpose |
|--------|---------|
| `addUserPermission(Collection<UUID>, Set<String>)` | Grant nodes to many users at once; returns the UUIDs actually changed |
| `removeUserPermissionFromAll(String node)` | Revoke one node from every user that holds it directly; returns the affected UUIDs |
| `hasUserGrant(UUID, String node)` | `true` only if the node is a **direct user grant** (ignores groups and wildcards) |
| `getUsersWithPermission(String node)` | Every user with that direct grant |
| `hasPermission(UUID, PermissionQuery[, boolean])` | The `PermissionQuery` form of the per-user check |
| `ROOT` / `ROOT_DENY` | The `"*"` grant-all and `"-*"` deny-all node strings |

`registerPermission` validates its inputs and throws `IllegalArgumentException`
(`Invalid permission node: …` / `Invalid group name: …`) rather than failing silently.

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
| `getUsersWithPermission(String)` | **Abstract as of 0.6.3** — a custom provider must implement this reverse lookup (used by the join-grant commands) |
| `addUserPermissions(Collection<UUID>, Set)` / `removeUserPermissionFromAll(String)` | `default` bulk methods (0.6.3+) built on the per-user ones; override for efficiency |

## Usage

### Check Permission in Command
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // PlayerRef is the PermissionHolder (the Player component is not)
    if (playerRef.hasPermission("myplugin.admin")) {
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
boolean canUse = playerRef.hasPermission("myplugin.feature", true);

// Returns false if permission not explicitly set
boolean isAdmin = playerRef.hasPermission("myplugin.admin", false);
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
| `requirePermission(PermissionQuery query)` | Same, with a pre-built `PermissionQuery` (0.6.3+) |
| `requireNoPermission()` | Skip the auto-generated per-command node so everyone can run it (0.6.3+; replaces the `canGeneratePermission()` override removed by 0.6.3) |
| `registerExtendedPermission(String suffix)` | (0.6.3+, `protected`) Register and return `<command node>.<suffix>` as a `PermissionQuery` for finer gating inside the command. **Not a constructor call**: it returns `null` while the command's node is unset, and the node only exists after `setOwner()` at registration — call it from an override of `completeRegistration()`, after `super.completeRegistration()` (the engine's target-player bases derive `.other` / `.all` this way) |
| `setPermissionGroups(String... groups)` | Assign the command to permission group(s) — the role-based form |
| `setPermissionGroup(GameMode)` | **Deprecated** (Update 5) — the old game-mode-keyed form; use `setPermissionGroups(String...)` |

If you don't gate explicitly, a command auto-generates a node at registration — `<plugin base permission>.command.<name>`,
where the base permission is the manifest's `Group.Name` lowercased (spaces → `_`; `PluginBase.getBasePermission()`),
sub-commands append their own segment, and `CommandManager`-owned commands use `hytale.system.command.<name>`. Ordinary
players (`hytale:Adventurer`) don't hold it, so it reads as "no permission" until granted (the `hytale:Admin` wildcard
`*` is why ops can always run it). Call `requireNoPermission()` in the constructor for a command any player should run.
(`HytalePermissions.fromCommand(name)` → `hytale.command.<name>` is a constant helper, not what registration generates.
`CommandUtil.requirePermission(holder, node)` — `String` or, as of 0.6.3, `PermissionQuery` — is the static check used
internally; it throws a `CommandException` that reaches the sender as *"no permission"*.)

As of 0.6.3 the command's stored permission is a **`PermissionQuery`** (`server.core.permissions`): `PermissionQuery.of(id)`
pre-splits the node into its wildcard ancestors (`a.*`, `a.b.*`, …) and deny forms (`-a.b.c`, `-a.*`, …) so `hasPermission` can
match them without re-parsing; `getId()` returns the plain node string (see [PermissionHolder](#permissionholder) for the
match order).

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
| `/op self` | Toggle **your own** membership of `hytale:Admin` (see the gating note below) |
| `/op add <player>`, `/op remove <player>` | Add/remove another player from `hytale:Admin` |

> **Gotcha:** `/op` on its own is a command collection — it prints usage, it does not op you.
> The self-op sub-command is `/op self`, and it is deliberately hard to reach: in singleplayer
> only the save owner may run it, and on a standalone server it refuses unless the server was
> launched with `--allow-op`, telling you instead to add your UUID to `permissions.json` while
> the server is off. It also refuses when a plugin has replaced the permission provider
> (`PermissionsModule.areProvidersTampered()`).

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
```

---

## Access Control (Bans & Join Permission)

**Package:** `com.hypixel.hytale.server.core.modules.accesscontrol`

A separate subsystem from permissions, access control decides **whether a player may connect at all** (bans, join
allow-list) rather than what an already-connected player is allowed to do. It ships as a core `JavaPlugin` module
(`AccessControlModule`) and provides the built-in `/ban`, `/unban`, and `/whitelist …` commands
(`add`, `remove`, `clear`, `list`, `status`, and `enable` / `disable` — the last two flip the
`RequireJoinPermission` config flag rather than editing a list) — but it is also an
**extension point**: a plugin can register its own access source or swap the ban store.

> **Reworked by 0.6.3.** The ban model is now a single codec-backed `Ban` value behind a `BanProvider` SPI —
> `BanParser`, `InfiniteBan`, `TimedBan`, `AbstractBan`, `registerBanParser(...)` and `parseBan(...)` were removed. The
> whitelist became a **permission**: `HytalePermissions.SERVER_JOIN` (`hytale.server.join`), enforced by
> `JoinPermissionProvider` when the server config's `RequireJoinPermission` is on (`HytaleServerConfig.isRequireJoinPermission()`);
> `HytaleWhitelistProvider` is gone and an existing `whitelist.json` is migrated once into per-user grants
> (`WhitelistMigration`, which renames the file). Because it is an ordinary permission, a **group or wildcard grant also
> satisfies it** — `hytale:Admin`'s `*` lets ops join a join-restricted server without an explicit entry.

### Key Classes

| Class | Description |
|-------|-------------|
| `AccessControlModule` | Core module; singleton via `AccessControlModule.get()`. Entry points below |
| `AccessProvider` (SPI, `.provider`) | A pluggable access source. `getDisconnectReason(UUID)` returns `CompletableFuture<Optional<Message>>` — a present `Message` denies the connection with that reason; empty allows it |
| `JoinPermissionProvider` (`.provider`) | The built-in join gate: allows everyone unless `RequireJoinPermission` is set, then requires `hytale.server.join` |
| `BanProvider` (SPI, `.provider`) | Extends `AccessProvider`; the ban store: `hasBan(UUID)`, `getBan(UUID)`, `addBan(Ban)`, `removeBan(UUID)`, `getBans()`, plus `default` no-op `load()` / `save()`. Its `default getDisconnectReason` denies with the ban's own `getDisconnectReason()` when `getBan(uuid)` is non-null, else denies with the generic `UNDESCRIBED_BAN` message when `hasBan(uuid)`, else allows (`NO_REASON`, an empty `Optional`). Expiry is the implementation's job — filter on `Ban.isInEffect()` inside `getBan`/`hasBan`, as `HytaleBanProvider` does |
| `HytaleBanProvider` (`.provider`) | Default disk `BanProvider` (`bans.json`, `BAN_FILE_PATH`) |
| `BanStorageProvider` (`.provider`) | Codec-selected factory (`CODEC`, keyed by id) that yields the `BanProvider` — `DiskBanStorageProvider` (`"Disk"`) is the built-in |
| `Ban` (`.ban`) | A single ban (final, codec-backed `CODEC`): `new Ban(target, by, timestamp, expiresOn, reason)` — `expiresOn == null` is permanent; `getTarget()`, `getBy()`, `getTimestamp()`, `getExpiresOn()`, `getReason()`, `isInEffect()`, `getDisconnectReason()`, plus typed metadata via `getMetadata(KeyedCodec)` / `withMetadata(...)` |

### AccessControlModule entry points

| Method | Description |
|--------|-------------|
| `registerAccessProvider(AccessProvider)` | Add a custom gate consulted on every connection (the `SingleplayerModule` uses this) |
| `getBanProvider()` / `setBanProvider(BanProvider)` / `restoreBanProvider(expected, previous)` | Read or swap the ban store; `setBanProvider` returns the previous one and `restoreBanProvider` puts it back only if the current one is still `expected` |
| `ban(Ban)` / `unban(UUID)` / `isBanned(UUID)` | Ban bookkeeping through the active provider |
| `isJoinPermissionRequired()` / `setJoinPermissionRequired(boolean)` | Read / persist the config flag (`CompletableFuture<Void>`) |
| `allowJoin(UUID)` / `allowJoin(Collection<UUID>)` / `disallowJoin(UUID)` / `disallowAllJoins()` | Grant / revoke the `hytale.server.join` **user** grant (the `/whitelist add|remove|clear` commands) |
| `isAllowedToJoin(UUID)` / `getUsersWithJoinGrant()` | Effective check (groups/wildcards count) / the direct grants only |

```java
AccessControlModule.get().registerAccessProvider(uuid ->
    isOnMyExternalBlocklist(uuid)
        ? CompletableFuture.completedFuture(Optional.of(Message.raw("Blocked by external list")))
        : CompletableFuture.completedFuture(Optional.empty()));

// Ban for 24 hours
AccessControlModule.get().ban(new Ban(targetUuid, adminUuid, Instant.now(),
        Instant.now().plus(Duration.ofHours(24)), "Griefing"));
```

> [!WARNING]
> Verified against `HytaleServer.jar` (0.6.3). Apart from `SingleplayerModule`, no first-party plugin registers an
> `AccessProvider` or swaps the `BanProvider`, so those entry points are documented from their signatures — register
> during your plugin `setup()` and test against your target build.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the server (verified against `HytaleServer.jar`).

- **`Cannot change permissions when a command has already completed registration`** → `requirePermission(...)`, `setPermissionGroups(...)`, or another permission setter was called after the command was registered. Fix: call it in the command constructor, before `registerCommand()`.
- **Symptom:** `hasPermission("node")` returns `false` for a node nobody has explicitly set → the single-arg overload defaults to `false` when the node is unset. Fix: use `hasPermission("node", true)` when "unset" should mean allowed (see [With Default Value](#with-default-value)).
- **Symptom:** a freshly registered command replies *"no permission"* for ordinary players even without `requirePermission(...)` → every command auto-generates a node (`<group>.<name>.command.<cmd>`, from the plugin manifest) that the default `hytale:Adventurer` group doesn't hold; only `hytale:Admin` (via the `*` wildcard) does. Fix: call `requireNoPermission()` in the constructor, or grant the node to a group via `PermissionsModule`. See [Commands: Permission model](commands.md#permission-model-why-a-new-command-says-no-permission).
- **Symptom:** `setPermissionGroup(GameMode)` no longer behaves as expected → it's **deprecated** in Update 5 and permissions are no longer game-mode-keyed. Fix: use `setPermissionGroups(String...)` with group names (e.g. `"hytale:Admin"`).
- **`Invalid permission node: <node>`** / **`Invalid group name: <group>`** (`IllegalArgumentException` from `PermissionsModule.registerPermission`) → the name failed validation. Fix: namespace nodes (`myplugin.feature`) and groups (`myplugin:Role`), and pre-check with `PermissionValidation.isValidPermissionNode` / `isValidGroupName`.
- **Symptom:** `player.hasPermission(...)` does not compile → the entity `Player` is not a `PermissionHolder`. Fix: check on the `PlayerRef` (`playerRef.hasPermission(...)`) or by UUID via `PermissionsModule.get().hasPermission(uuid, node)`.
- **Symptom:** a player who is not on the join list can still connect with `RequireJoinPermission` on → `hytale.server.join` is a normal permission, so a group grant or wildcard (`hytale:Admin`'s `*`) satisfies it. Fix: this is by design; deny it explicitly (`-hytale.server.join`) on the group if you need a hard block.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
