---
title: "Commands API"
description: "Create Hytale server commands in Java — player, world, and target base classes, typed argument parsing and validation, subcommands, permissions, and built-in arg types."
seo:
  type: TechArticle
---

# Commands API

**Doc type:** Java API · **Verified against 0.5.9**

The command system lets plugins register console- and player-executable commands with typed, validated arguments and tab completion.

## Overview

Implemented in `com.hypixel.hytale.server.core.command.system` and provides:
- Player, world, and target-player command base classes
- Typed argument parsing with validation (required, optional, default, flag, and list variants)
- Tab completion via suggestions
- Aliases, subcommands, and usage variants
- Auto-generated, permission-gated command nodes
- A factory (`ArgTypes`) of built-in argument types for primitives, positions, assets, and game enums

## Architecture
```
CommandRegistry
├── Registered AbstractCommands
│   ├── AbstractPlayerCommand
│   ├── AbstractWorldCommand
│   └── AbstractTargetPlayerCommand
├── Argument System (withRequiredArg / withOptionalArg / withDefaultArg / withFlagArg + list variants)
├── ArgumentType<D> (SingleArgumentType / custom)
│   └── ArgTypes (factory for built-in types)
├── CommandContext (parsed args + sender)
└── Permission model (auto-generated nodes via CommandOwner)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `AbstractCommand` | `server.core.command.system` | Base class for all commands; argument and permission API |
| `AbstractAsyncCommand` | `server.core.command.system.basecommands` | Async command base; all player commands inherit from it |
| `AbstractPlayerCommand` | `server.core.command.system.basecommands` | Most common base for player-executed commands |
| `AbstractWorldCommand` | `server.core.command.system.basecommands` | Base for commands operating on a world context |
| `AbstractTargetPlayerCommand` | `server.core.command.system.basecommands` | Base for commands targeting another player |
| `CommandContext` | `server.core.command.system` | Execution context with parsed args and sender access |
| `CommandRegistry` | `server.core.command.system` | Registers commands with the server |
| `CommandRegistration` | `server.core.command.system` | Handle returned from registration (for unregistering) |
| `CommandSender` | `server.core.command.system` | Interface for anything that sends commands / receives messages |
| `CommandOwner` | `server.core.command.system` | Interface for command owners (typically plugins) |
| `ArgumentType<D>` | `server.core.command.system.arguments.types` | Abstract base for argument types |
| `ArgTypes` | `server.core.command.system.arguments.types` | Factory of built-in argument types |
| `CommandBase` | `server.core.command.system.basecommands` | Simplest sync base; no player or world context required |
| `AbstractAsyncPlayerCommand` | `server.core.command.system.basecommands` | Async variant of the player command base (returns a future) |
| `AbstractTargetPlayersCommand` | `server.core.command.system.basecommands` | Base for commands targeting self, `--player=X`, or `--all=true` |
| `AbstractOptionalArg` | `server.core.command.system.arguments.system` | Base of optional/default/flag args; aliases, per-arg permissions, dependencies |
| `EnumArgumentType` | `server.core.command.system.arguments.types` | Argument type for any enum — what `ArgTypes.forEnum` returns |
| `AssetArgumentType` | `server.core.command.system.arguments.types` | Argument type for any string-keyed JSON asset class |
| `GeneralCommandException` | `server.core.command.system.exceptions` | Throw with a `Message` to abort a command and message the sender |
| `CommandManager` | `server.core.command.system` | The engine-side registry/dispatcher (`CommandManager.get()`); owns system commands, resolves and tab-completes input |
| `CommandCompletion` | `server.core.command.system` | Static tab-completion resolver behind `CommandManager.suggestCompletions` (0.6.3+) |

## Class Hierarchy
```
AbstractCommand
  └── AbstractAsyncCommand
        ├── AbstractPlayerCommand  (use this for player commands)
        ├── AbstractWorldCommand
        └── AbstractTargetPlayerCommand

CommandSender (interface)
  ├── PlayerRef (player sender — the entity `Player` does NOT implement it)
  └── ConsoleSender (server.core.console)

CommandOwner (interface)
  ├── PluginBase (implementation)
  └── CommandManager (owner of the engine's system commands)

ArgumentType<D> (abstract)
  └── SingleArgumentType<D>

ArgTypes (factory for built-in argument types)
```

## Argument syntax (input format)

How the parser reads the text **after** the command name. These rules come from
the parser in `com.hypixel.hytale.server.core.command.system` and the errors it
emits at runtime — they apply to every command, built-in or plugin:

- **Required arguments are positional** — the bare value, in declared order:
  `/npc spawn <role>`.
- **Optional valued arguments are `--name=value`** (e.g. `--count=5`).
- **Boolean flags are a bare `--name`** with no value (e.g. `--frozen`).
- **Quote any value containing a space** with `"` or `'`.
- **A bare comma is a list separator** (and `[ ]` delimit a list). A value that
  itself contains commas must be **quoted** so it isn't split into a list —
  e.g. `/npc debug set "DisplayState,DisplayFlock"`. Unquoted, the server
  rejects it with *"you have specified a list of argument values for an argument
  that does not accept a list."*

Two common mistakes:

- Passing an optional as a bare `name value` pair (no `--` / `=`) makes those
  tokens count as **positional** arguments, giving *"the wrong number of
  required argument was specified."*
- **Parse errors are sent to the caller's chat, not the server log.** The log
  only records the echo (`[CommandManager] <user> executed command: <text>`), so
  when a command "errors," read the on-screen message — the log won't show why.

## AbstractPlayerCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Most common base class for player-executed commands.

### Constructors
```java
AbstractPlayerCommand(String name, String description)
AbstractPlayerCommand(String name, String description, boolean requiresConfirmation)
AbstractPlayerCommand(String name)  // no description
```

The third-argument boolean on every base-class constructor is `requiresConfirmation`
(`AbstractCommand(String, String, boolean)`): when `true` the parser refuses to run
the command unless the caller appends `--confirm` (`ParserContext.isConfirmationSpecified()`),
and the usage text gains a "requires confirmation" line — the engine uses it for
destructive commands such as `/npc clean`.

### Abstract Method to Implement
```java
protected abstract void execute(
    CommandContext commandContext,
    Store<EntityStore> store,
    Ref<EntityStore> ref,
    PlayerRef playerRef,
    World world
);
```

### Usage Example

Full working example: [`examples/commands/.../HelloCommand.java`](../examples/commands/src/main/java/hytale/examples/commands/HelloCommand.java) (compiles against the 0.6.3 jar).

```java
public class HelloCommand extends AbstractPlayerCommand {

    public HelloCommand() {
        super("hello", "Sends a friendly greeting");
        // By default each command auto-generates a permission node (here
        // "<group>.<name>.command.hello", from the plugin's manifest) that only
        // ops hold (the hytale:Admin group carries the '*' wildcard), so a normal player
        // gets "no permission". requireNoPermission() opts out of node generation,
        // leaving the command open to everyone. Use requirePermission("...") to
        // gate instead. Must be called before registration.
        requireNoPermission();
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        playerRef.sendMessage(Message.raw("Hello, " + playerRef.getUsername() + "!"));
    }
}
```

> **See also:** [Message Formatting API](player.md#message)

## CommandContext
**Package:** `com.hypixel.hytale.server.core.command.system`

Provides access to command arguments and sender information.

### Methods
```java
<T> T get(Argument<?, T> arg)           // Get argument value
String[] getInput(Argument<?, ?> arg)   // Get raw input for argument
boolean provided(Argument<?, ?> arg)    // Check if optional arg was provided
String getInputString()                 // Full input string
void sendMessage(Message msg)           // Send message to sender
boolean isPlayer()                      // Check if sender is player
<T extends CommandSender> T senderAs(Class<T> clazz)  // Cast sender
Ref<EntityStore> senderAsPlayerRef()    // Get player ref
CommandSender sender()                  // Get sender
AbstractCommand getCalledCommand()      // Get command that was called
```

## CommandRegistry
**Package:** `com.hypixel.hytale.server.core.command.system`

Register commands with the server.

```java
CommandRegistration registerCommand(AbstractCommand command)
```

### Registration Example
```java
@Override
protected void setup() {
    getCommandRegistry().registerCommand(new MyCommand());
}
```

> **See also:** [Plugin Lifecycle](plugin-lifecycle.md#plugin-lifecycle-api)

### Tab completion (CommandManager / CommandCompletion)

Registration hands the command to the engine's `CommandManager` (`CommandManager.get()`,
`server.core.command.system`), which is also what serves the client's tab completion.
As of 0.6.3 that resolver is exposed:

```java
AbstractCommand resolveCommand(String name)                                   // by name or alias, or null
List<String> suggestCompletions(CommandSender sender, List<String> words, int wordIndex)
```

`suggestCompletions` delegates to the static `CommandCompletion.suggest(sender, commands,
resolver, words, wordIndex)`: word 0 completes command names the sender may run, later
words walk sub-commands (`AbstractCommand.getSubCommand(name)`), then offer required-arg
suggestions, `--optional` names (`getOptionalArgument(name)`), or inline `--name=value`
values — permission-filtered via `hasPermission(sender)` at every step. Plugins normally
only feed it indirectly, by overriding `ArgumentType.suggest(...)` on custom argument
types.

## AbstractCommand Arguments
**Package:** `com.hypixel.hytale.server.core.command.system`

Define command arguments in your command class.

### Argument Types
```java
// Required argument (must be provided)
withRequiredArg(String name, String description, ArgumentType<D> type)

// Optional argument (may be omitted)
withOptionalArg(String name, String description, ArgumentType<D> type)

// Default argument (uses default if omitted)
withDefaultArg(String name, String description, ArgumentType<D> type, D defaultValue, String defaultDisplay)

// Flag argument (boolean switch like --verbose)
withFlagArg(String name, String description)

// List variants
withListRequiredArg(...)
withListOptionalArg(...)
withListDefaultArg(...)
```

### Other AbstractCommand Methods
```java
// Aliases & Subcommands
void addAliases(String... aliases)              // Add command aliases
void addSubCommand(AbstractCommand cmd)         // Add subcommand
void addUsageVariant(AbstractCommand cmd)       // Add usage variant

// Command Info
String getName()                                // Get command name
String getDescription()                         // Get description
String getFullyQualifiedName()                  // Get full command path (e.g., "parent subcommand")
Message getUsageString(CommandSender sender)    // Get usage help
Message getUsageShort(CommandSender sender, boolean showAliases)  // Get short usage

// Permissions
void requirePermission(String permission)       // Require a permission node
void requirePermission(PermissionQuery query)   // Same, with a pre-built PermissionQuery (0.6.3+)
void requireNoPermission()                      // Opt out of the auto-generated node — open to everyone (0.6.3+; replaces canGeneratePermission())
protected PermissionQuery registerExtendedPermission(String suffix)  // Register + return "<this command's node>.<suffix>" (0.6.3+) — see note below
protected void setPermissionGroups(String... groups)      // Assign command to permission group(s)
protected void setPermissionGroup(GameMode mode)          // @Deprecated(forRemoval) (Update 5) — use setPermissionGroups(String...)
boolean hasPermission(CommandSender sender)     // Check permission
String getPermission()                          // The node's id, or null when open
protected String generatePermissionNode()       // This command's own segment of the node (name lowercased)

// Configuration
protected void setUnavailableInSingleplayer(boolean unavailable)  // Mark multiplayer-only
void setAllowsExtraArguments(boolean allows)    // Allow trailing arguments
void setOwner(CommandOwner owner)               // Set owning plugin
void completeRegistration()                     // Called by the registry once; overridable hook (call super first)

// Introspection (0.6.3+ additions marked)
Map<String, AbstractCommand> getSubCommands()
AbstractCommand getSubCommand(String name)                  // (0.6.3+) null if none
Map<String, AbstractOptionalArg<?, ?>> getOptionalArguments()
AbstractOptionalArg<?, ?> getOptionalArgument(String name)  // (0.6.3+) null if none
List<RequiredArg<?>> getRequiredArguments()
boolean hasBeenRegistered()

// Matching
MatchResult matches(String input, String alias, int depth)  // Check if input matches command
```

> **`registerExtendedPermission` timing:** it returns `null` whenever the command's own
> node is still unset, and that node is only populated by `setOwner()` during registration —
> so calling it from the constructor always yields `null`. Call it from an override of
> `completeRegistration()`, **after** `super.completeRegistration()`, exactly as the engine's
> `AbstractTargetPlayerCommand` (`.other`) and `AbstractTargetPlayersCommand` (`.other`,
> `.all`) do. `requirePermission(...)` / `requireNoPermission()`, by contrast, must run
> *before* registration.

> **See also:** [Permissions API](permissions.md#permissionholder)

### Permission model (why a new command says "no permission")

> Verified against 0.5.9 (`AbstractCommand.setOwner`/`hasPermission`, `AssetModule`, `permissions/commands/op`).

When a command is registered, `setOwner()` runs:

```java
if (this.permission == null && !this.openToEveryone)            // openToEveryone is set only by requireNoPermission()
    this.permission = PermissionQuery.of(generatePermission());  // e.g. "myorg.myplugin.command.menu"
```

The generated node is `<plugin base permission>.command.<name>` for a plugin-owned command, where the base permission is the manifest's `Group.Name` lowercased with spaces replaced by `_` (`PluginBase.getBasePermission()`); sub-commands append their own segment to the parent's node (`....command.perm.reload`), and commands owned by the `CommandManager` itself use `hytale.system.command.<name>`. (`HytalePermissions.fromCommand(name)` → `hytale.command.<name>` still exists as a constant helper, but it is **not** what registration generates.) As of 0.6.3 the field is a `PermissionQuery` (`server.core.permissions`), a pre-split wrapper around the node id that `PermissionHolder.hasPermission(PermissionQuery)` matches against wildcards; `getPermission()` still returns the plain id string.

So **every command auto-generates a permission node by default**, and `hasPermission(sender)` only passes if the node is `null`, or the sender holds it. A normal player holds nothing, so a freshly written `/menu` replies *"no permission"* until you do one of:

| Option | How | When to use |
|--------|-----|-------------|
| **Open the command** | Call `requireNoPermission()` in the constructor (leaves the node `null` and flags the command open → everyone passes; replaces the `canGeneratePermission()` override removed by 0.6.3) | Examples / commands meant for all players |
| **Explicit node** | Call `requirePermission("ui.menu")` in the constructor, then grant that node | Real permission-gated commands |
| **Become op** | Run `/op` in-game; it adds you to the `hytale:Admin` group, which carries the `*` wildcard, satisfying every node | Testing/admin |

```java
public MenuCommand() {
    super("menu", "Opens a custom menu");
    // Opt out of the auto-generated node so any player can run this command.
    // Like requirePermission(...), this must run before registration.
    requireNoPermission();
}
```

Notes:
- `/op` (self) is itself gated: it works in local/singleplayer, but a dedicated server requires the `--allow-op` launch arg or your UUID in `permissions.json`.
- The example plugins all call `requireNoPermission()` so they run without op.
- `canGeneratePermission()` (the 0.5.x override-to-`false` opt-out) was **removed by 0.6.3**; an `@Override` of it now fails to compile ("method does not override or implement a method from a supertype").

## AbstractAsyncCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Base class for async commands. All player commands inherit from this.

```java
// Execute async (override this for custom async commands)
protected abstract CompletableFuture<Void> executeAsync(CommandContext context)

// Run task asynchronously
CompletableFuture<Void> runAsync(CommandContext ctx, Runnable task, Executor executor)
```

---

## AbstractAsyncPlayerCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Async variant of the player command base: the same five parameters as
`AbstractPlayerCommand.execute`, but you return a `CompletableFuture<Void>` so
the command can chain further async work (asset loads, cross-world teleports).
The engine's prefab-editor commands (`/prefabedit load`, `/prefabedit save`, …)
are built on it.

### Constructors
```java
AbstractAsyncPlayerCommand(String name, String description)
AbstractAsyncPlayerCommand(String name, String description, boolean requiresConfirmation)
AbstractAsyncPlayerCommand(String name)  // no description
```

### Abstract Method to Implement
```java
protected abstract CompletableFuture<Void> executeAsync(
    CommandContext context,
    Store<EntityStore> store,
    Ref<EntityStore> ref,
    PlayerRef playerRef,
    World world
);
```

The framework resolves the sender to a player ref (console gets the
*"playerOrArg"* error, a player outside a world gets *"playerNotInWorld"*),
schedules your `executeAsync` **on the world thread** (the `World` is the
executor), and then waits on the future you return — so the future completes
the command, not the method returning.

---

## CommandBase
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

The simplest base class: sender-agnostic and synchronous. There is no player,
world, or store parameter — just the `CommandContext` — so it works identically
from the console and from a player. Reach for it when the command only reads
its arguments and sends messages, or talks to services that don't need a world
thread. The engine uses it for `/warp list`, `/warp reload`, and most server
debug/stats commands.

```java
CommandBase(String name, String description)
CommandBase(String name, String description, boolean requiresConfirmation)
CommandBase(String name)  // no description

// Implement this — runs synchronously
protected abstract void executeSync(CommandContext context);
```

---

## AbstractWorldCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Base class for commands that operate on a world context.

### Constructors
```java
AbstractWorldCommand(String name)
AbstractWorldCommand(String name, String description)
AbstractWorldCommand(String name, String description, boolean requiresConfirmation)
```

### Abstract Method to Implement
```java
protected abstract void execute(
    CommandContext commandContext,
    World world,
    Store<EntityStore> store
);
```

### Example: bulk entity operations

A world command receives the `Store`, which is the entry point for iterating and
mutating entities in bulk — for example a "remove every NPC of a given role"
command. (The engine ships `/npc clean`, which removes *all* NPCs, but nothing
that filters by role.)

```java
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractWorldCommand;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.component.RemoveReason;

public class KillRoleCommand extends AbstractWorldCommand {
    private final RequiredArg<String> roleArg;

    public KillRoleCommand() {
        super("killrole", "Remove every NPC of the given role");
        roleArg = withRequiredArg("role", "Role name", ArgTypes.STRING);
        setPermissionGroups("hytale:ServerEditor");
    }

    @Override
    protected void execute(CommandContext ctx, World world, Store<EntityStore> store) {
        String target = ctx.get(roleArg);
        store.forEachEntityParallel(NPCEntity.getComponentType(), (index, chunk, buffer) -> {
            NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
            if (npc != null && target.equals(npc.getRoleName())) {
                buffer.removeEntity(chunk.getReferenceTo(index), RemoveReason.REMOVE);
            }
        });
    }
}
```

Key points:

- `store.forEachEntityParallel(query, consumer)` walks every entity matching the
  `Query` — a `ComponentType` *is* a `Query`, so passing `NPCEntity.getComponentType()`
  selects every entity with that component — across archetype chunks in parallel. The
  consumer (`com.hypixel.hytale.function.consumer.IntBiObjectConsumer`) receives
  `(int index, ArchetypeChunk, CommandBuffer)`.
- Inside it, read a component with `chunk.getComponent(index, type)` (generic on the
  component type, so no cast is needed), and get the entity's `Ref` with
  `chunk.getReferenceTo(index)`.
- Queue structural edits on the `CommandBuffer`, which applies *after* the
  iteration, so removing while iterating is safe:
  `buffer.removeEntity(ref, RemoveReason.REMOVE)`. `RemoveReason`
  (`com.hypixel.hytale.component`) is one of `REMOVE`, `UNLOAD`, or
  `BUILDER_TOOLS_UNDO`.

---

## AbstractTargetPlayerCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Base class for commands that target another player (e.g., admin commands).

### Constructors
```java
AbstractTargetPlayerCommand(String name)
AbstractTargetPlayerCommand(String name, String description)
AbstractTargetPlayerCommand(String name, String description, boolean requiresConfirmation)
```

Targeting another player additionally requires the derived node `<permission>.other`,
which the base registers in its `completeRegistration()` override via
`registerExtendedPermission("other")` (0.6.3+).

### Abstract Method to Implement
```java
protected abstract void execute(
    CommandContext commandContext,
    Ref<EntityStore> ref,
    Ref<EntityStore> targetRef,
    PlayerRef targetPlayer,
    World world,
    Store<EntityStore> store
);
```

### Usage Example
```java
public class KickCommand extends AbstractTargetPlayerCommand {
    public KickCommand() {
        super("kick", "Kick a player from the server");
        requirePermission("server.kick");
    }

    @Override
    protected void execute(CommandContext ctx, Ref<EntityStore> ref,
                          Ref<EntityStore> targetRef, PlayerRef targetPlayer,
                          World world, Store<EntityStore> store) {
        // targetPlayer is the player being kicked (not the sender)
        targetPlayer.sendMessage(Message.raw("You have been kicked!"));
        // Kick logic here
    }
}
```

---

## AbstractTargetPlayersCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Base for commands that act on a *set* of players. Target selection is built in:

- **No args** → targets the sender (console without `--player` gets the
  *"playerOrArg"* error).
- **`--player=<name>`** → targets that player; the sender must additionally
  hold the auto-derived node `<permission>.other`.
- **`--all=true`** → targets every player in the sender's world; requires
  `<permission>.all`.
- Passing both `--player` and `--all` is rejected with a target-conflict error.

The `.other` / `.all` nodes are derived in the base's `completeRegistration()` override
(`registerExtendedPermission("all")` / `("other")`, 0.6.3+), so they exist only when the
command itself has a node — an open (`requireNoPermission()`) command skips both checks.
The engine's `/audio music clear` and `/audio music force` use this base.

### Constructors
```java
AbstractTargetPlayersCommand(String name, String description)
AbstractTargetPlayersCommand(String name, String description, boolean requiresConfirmation)
AbstractTargetPlayersCommand(String name)  // no description
```

### Abstract Method to Implement
```java
protected abstract void execute(
    CommandContext commandContext,
    World world,
    Store<EntityStore> store,
    List<Ref<EntityStore>> targets   // resolved target player refs
);
```

> **Gotcha:** `all` is declared as an optional **boolean** argument, not a flag
> — a bare `--all` is rejected by the parser; it must be `--all=true`.

---

## Sub-commands (command collections)

To group related sub-commands under one name — `/mytools killrole`,
`/mytools count`, etc. — extend `AbstractCommandCollection` and register each child in the
constructor with `addSubCommand(...)`. Children are ordinary commands (any
`AbstractCommand` subclass), so a collection can even nest other collections.
This is exactly how the engine builds its own `/npc ...` family.

```java
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractCommandCollection;

public class MyToolsCommand extends AbstractCommandCollection {
    public MyToolsCommand() {
        super("mytools", "Admin tools");
        addSubCommand(new KillRoleCommand());   // -> /mytools killrole <role>
        // addSubCommand(new CountCommand());   // -> /mytools count
    }
}
```

Register only the parent — its sub-commands come with it:

```java
getCommandRegistry().registerCommand(new MyToolsCommand());
```

`addSubCommand(AbstractCommand)` is public on `AbstractCommand`. Each sub-command
needs a unique, non-empty name, and a given instance may only be added to **one**
parent (see [Gotchas & Errors](#gotchas--errors)).

---

## CommandSender
**Package:** `com.hypixel.hytale.server.core.command.system`

Interface for anything that can send commands and receive messages.

**Extends:** `IMessageReceiver`, `PermissionHolder`

### Methods
```java
String getUsername()  // Username of sender (renamed from getDisplayName() in Update 5)
UUID getUuid()        // UUID of sender
```

`CommandSender` extends `PermissionHolder`, so a sender can be permission-checked directly (`hasPermission(node)`).

### Implementations
- `PlayerRef` - the player command sender (implements `CommandSender` + `PermissionHolder`). **Note (Update 5):** `Player` no longer implements `CommandSender`/`PermissionHolder` — use the `PlayerRef` the framework hands you.
- `ConsoleSender` (`server.core.console`) - the server console sender

### Usage
```java
CommandSender sender = ctx.sender();
sender.sendMessage(Message.raw("Hello!"));

if (ctx.isPlayer()) {
    PlayerRef playerRef = ctx.senderAs(PlayerRef.class);   // senderAs needs a CommandSender subtype
}
```

---

## CommandOwner
**Package:** `com.hypixel.hytale.server.core.command.system`

Interface for command owners (typically plugins).

### Methods
```java
String getName()  // Name of the owner
```

### Implementations
- `PluginBase` - All plugins implement CommandOwner

### Usage
```java
// In AbstractCommand
void setOwner(CommandOwner owner)
```

---

## CommandRegistration
**Package:** `com.hypixel.hytale.server.core.command.system`

Result of registering a command with the server. Extends `Registration`.

### Usage
```java
CommandRegistration registration = getCommandRegistry().registerCommand(new MyCommand());
// Registration can be used to unregister the command later
```

---

## ArgumentType<D>
**Package:** `com.hypixel.hytale.server.core.command.system.arguments.types`

Abstract base class for command argument types. Extend this to create custom argument types.

### Key Methods
```java
abstract D parse(String[] input, ParseResult result)  // Parse input to value
void suggest(CommandSender sender, String input, int cursor, SuggestionResult result)
Message getArgumentUsage()   // Usage text for help
Message getName()            // Argument name
String[] getExamples()       // Example values
int getNumberOfParameters()  // Number of input tokens consumed
boolean isListArgument()     // Whether this accepts multiple values
boolean isGreedyString()     // Whether this consumes the rest of the line
ArgumentType<D> withSharedSuggestions(ArgumentType<?> other)  // Reuse another type's suggestion cache (return type narrowed to ArgumentType<D> in 0.6.3)
```

### SingleArgumentType<D>
Base class for arguments that consume a single input token:

```java
abstract D parse(String input, ParseResult result)  // Parse single string
```

---

## ArgTypes
**Package:** `com.hypixel.hytale.server.core.command.system.arguments.types`

Factory class containing built-in argument types.

### Primitive Types
```java
ArgTypes.BOOLEAN   // Boolean (true/false)
ArgTypes.INTEGER   // Integer
ArgTypes.FLOAT     // Float
ArgTypes.DOUBLE    // Double
ArgTypes.STRING    // String
ArgTypes.GREEDY_STRING // String consuming the rest of the line (must be the last required arg)
ArgTypes.UUID      // UUID
ArgTypes.COLOR     // Color (integer)
```

### Player & Entity Types
```java
ArgTypes.PLAYER_UUID  // Player UUID with suggestions
ArgTypes.PLAYER_REF   // PlayerRef with tab completion
ArgTypes.ENTITY_ID    // Entity UUID (an ArgWrapper<EntityWrappedArg, UUID>)
```

### World & Position Types
```java
ArgTypes.WORLD                    // World reference
ArgTypes.RELATIVE_POSITION        // Double position with ~ support (e.g., ~10 ~ ~-5)
ArgTypes.RELATIVE_BLOCK_POSITION  // Integer position with ~ support
ArgTypes.RELATIVE_CHUNK_POSITION  // Chunk position with ~ support
ArgTypes.VECTOR3I                 // Vector3i (x y z integers)
ArgTypes.VECTOR2I                 // Vector2i (x y integers)
ArgTypes.ROTATION                 // Rotation3fc (pitch/yaw/roll)
ArgTypes.RELATIVE_INTEGER         // Integer with ~ support
ArgTypes.RELATIVE_FLOAT           // Float with ~ support
```

### Asset Types
```java
ArgTypes.BLOCK_TYPE_ASSET   // BlockType asset
ArgTypes.ITEM_ASSET         // Item asset
ArgTypes.MODEL_ASSET        // Model asset
ArgTypes.WEATHER_ASSET      // Weather asset
ArgTypes.EFFECT_ASSET       // EntityEffect asset
ArgTypes.ENVIRONMENT_ASSET  // Environment asset
ArgTypes.SOUND_EVENT_ASSET  // Sound event asset
ArgTypes.PARTICLE_SYSTEM    // Particle system asset
```

### Game Types
```java
ArgTypes.GAME_MODE      // GameMode enum
ArgTypes.SOUND_CATEGORY // Sound category
ArgTypes.TICK_RATE      // Tick rate integer
```

### Block Types
```java
ArgTypes.BLOCK_TYPE_KEY    // Block type string key
ArgTypes.BLOCK_ID          // Block ID integer
ArgTypes.BLOCK_PATTERN     // Block pattern for commands
ArgTypes.BLOCK_MASK        // Block mask for filtering
ArgTypes.WEIGHTED_BLOCK_TYPE // Block type with weight
```

### Provider keys (0.6.3+)
```java
ArgTypes.WORLD_GEN_PROVIDER_KEY                 // registered world-generator provider id
ArgTypes.WORLD_GEN_PROVIDER_KEY_OR_DEFAULT      // same, also accepting "default"
ArgTypes.WORLD_MAP_PROVIDER_KEY                 // world-map provider id
ArgTypes.CHUNK_STORAGE_PROVIDER_KEY             // chunk-storage provider id
ArgTypes.CHUNK_STORAGE_PROVIDER_KEY_OR_DEFAULT  // same, also accepting "default"
ArgTypes.AUTH_STORE_PROVIDER_KEY                // auth-store provider id
```
All are `SingleArgumentType<String>` with tab completion over the registered provider ids;
they back the `/world create …` and storage/auth admin commands.

### Enum Helper
```java
// Create argument type for any enum
ArgTypes.forEnum(String name, Class<E> enumClass)
```

### Usage Example
```java
public class TeleportCommand extends AbstractPlayerCommand {
    private final RequiredArg<RelativeDoublePosition> posArg;

    public TeleportCommand() {
        super("tp", "Teleport to a position");
        posArg = withRequiredArg("position", "Target position", ArgTypes.RELATIVE_POSITION);
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        RelativeDoublePosition relPos = ctx.get(posArg);
        Transform current = playerRef.getTransform();
        Vector3d target = relPos.getRelativePosition(current.getPosition(), world);
        // Teleport to target
    }
}
```

`withRequiredArg` returns a `RequiredArg<D>` (`server.core.command.system.arguments.system`);
`withOptionalArg` / `withDefaultArg` / `withFlagArg` return `OptionalArg<D>` / `DefaultArg<D>` /
`FlagArg`. Declare fields with those concrete types — the shared base is
`Argument<Arg extends Argument<Arg, D>, D>`, so `Argument<String, String>` is not a valid type.

### Relative Position Resolution

`RelativeDoublePosition` supports Minecraft-style relative coordinates using `~` (tilde):
- `100 64 200` - Absolute coordinates
- `~ ~ ~` - Player's current position
- `~10 ~ ~-5` - 10 blocks east, same height, 5 blocks south

**Full resolution pattern:**
```java
public class SpawnCommand extends AbstractPlayerCommand {
    private final RequiredArg<RelativeDoublePosition> posArg;

    public SpawnCommand() {
        super("spawn", "Spawn entity at position");
        posArg = withRequiredArg("position", "Target position", ArgTypes.RELATIVE_POSITION);
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        // Get the relative position from command args
        RelativeDoublePosition relPos = ctx.get(posArg);

        // Get player's current transform (position + rotation)
        Transform transform = playerRef.getTransform();

        // Resolve relative coordinates against player's position and world
        // ~10 ~ ~-5 becomes (playerX+10, playerY, playerZ-5)
        Vector3d targetPosition = relPos.getRelativePosition(transform.getPosition(), world);

        // Use the resolved absolute position
        playerRef.sendMessage(Message.raw(
            "Spawning at: " + targetPosition.x() + ", " +
            targetPosition.y() + ", " + targetPosition.z()
        ));
    }
}
```

**Key methods:**
- `relPos.getRelativePosition(Vector3d origin, World world)` - Resolves relative coords against origin
- `relPos.isRelative()` - Check whether the position uses `~` (relative) coordinates

### Custom Enum Argument Example
```java
public enum Difficulty { EASY, NORMAL, HARD }

public class DifficultyCommand extends AbstractPlayerCommand {
    private final RequiredArg<Difficulty> diffArg;

    public DifficultyCommand() {
        super("difficulty", "Set difficulty");
        diffArg = withRequiredArg("level", "Difficulty level",
            ArgTypes.forEnum("difficulty", Difficulty.class));
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        Difficulty diff = ctx.get(diffArg);
        playerRef.sendMessage(Message.raw("Set difficulty to " + diff));
    }
}
```

> **See also:** [Math/Vector API](math.md#core-types)

## Relative argument value types
**Package:** `com.hypixel.hytale.server.core.command.system.arguments.types`

The relative `ArgTypes` constants don't hand you a plain number — they parse
into small value objects that you **resolve against a base** (usually the
sender's position) inside `execute`. Which constant produces which class:

| Argument type constant | Parses to | Resolve with |
|------------------------|-----------|--------------|
| `ArgTypes.RELATIVE_INTEGER` | `RelativeInteger` | `resolve(int base)` |
| `ArgTypes.RELATIVE_FLOAT` | `RelativeFloat` | `resolve(float base)` |
| `ArgTypes.RELATIVE_INT_RANGE` | `RelativeIntegerRange` | `getNumberInRange(int base)` |
| `ArgTypes.RELATIVE_VECTOR3I` | `RelativeVector3i` | `resolve(Vector3i base)` |
| `ArgTypes.RELATIVE_DOUBLE_COORD` | `Coord` | `resolveXZ` / `resolveYAtWorldCoords` |
| `ArgTypes.RELATIVE_INT_COORD` | `IntCoord` | integer analog of `Coord` |
| `ArgTypes.RELATIVE_POSITION` | `RelativeDoublePosition` | see [Relative Position Resolution](#relative-position-resolution) |
| `ArgTypes.RELATIVE_BLOCK_POSITION` | `RelativeIntPosition` | `getBlockPosition(...)` |
| `ArgTypes.RELATIVE_CHUNK_POSITION` | `RelativeChunkPosition` | chunk analog |
| `RelativeDirection.ARGUMENT_TYPE` | `RelativeDirection` | `toDirectionVector` / `toAxis` |

### Coord
One coordinate of a position, with its parse-time modifiers preserved:

```java
static Coord parse(String str)
double getValue()
boolean isRelative()   // "~" prefix
boolean isChunk()      // "c" prefix
boolean isHeight()     // "_" prefix (Y only)
double resolveXZ(double base)
double resolveYAtWorldCoords(double base, World world, double x, double z)
    throws GeneralCommandException
```

Prefixes accepted by `parse` (verified in source): `~N` is an offset from the
base, `cN` is a chunk coordinate (multiplied by 32 blocks on resolve), and `_N`
is terrain-relative — `resolveYAtWorldCoords` returns the terrain surface
height + 1 + N, and throws [`GeneralCommandException`](#generalcommandexception)
if the chunk at (x, z) isn't loaded.

### RelativeInteger & RelativeFloat
The values behind `ArgTypes.RELATIVE_INTEGER` / `ArgTypes.RELATIVE_FLOAT`
(`5` absolute, `~5` relative):

```java
RelativeInteger(int value, boolean isRelative)
int getRawValue()       // the number as typed (offset if relative)
boolean isRelative()
int resolve(int base)   // value + base when relative, else value
```

`RelativeFloat` is identical with `float`. Both also expose a static
`parse(String, ParseResult)` and a `CODEC`, so they can double as fields in
codec-backed asset configs.

### RelativeIntegerRange
Behind `ArgTypes.RELATIVE_INT_RANGE` — a min/max pair of `RelativeInteger`s:

```java
RelativeIntegerRange(RelativeInteger min, RelativeInteger max)
RelativeIntegerRange(int min, int max)
int getNumberInRange(int base)
```

> **Gotcha:** `getNumberInRange` is not a clamp — it resolves both ends against
> `base` and returns a **uniformly random** value in `[min, max]` (inclusive);
> only when min and max are equal does it return that value directly.

### RelativeVector3i
Behind `ArgTypes.RELATIVE_VECTOR3I` — three `RelativeInteger`s, each
independently absolute or `~`-relative:

```java
static final RelativeVector3i ZERO
RelativeVector3i(RelativeInteger x, RelativeInteger y, RelativeInteger z)
Vector3i resolve(int x, int y, int z)
Vector3i resolve(Vector3i base)
boolean isRelativeX() / isRelativeY() / isRelativeZ()
```

### RelativeIntPosition
Behind `ArgTypes.RELATIVE_BLOCK_POSITION` — the integer/block analog of
`RelativeDoublePosition`:

```java
Vector3i getBlockPosition(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)
Vector3i getBlockPosition(CommandContext context, ComponentAccessor<EntityStore> accessor)
Vector3i getBlockPosition(Vector3d base, ChunkStore chunkStore)
boolean isRelative()
```

The `Ref` overload resolves `~` coordinates against that entity's
`TransformComponent` position (the `CommandContext` overload uses the sender),
so you can pass the sender's ref for "relative to me" or any entity's ref for
"relative to it".

### RelativeDirection
An enum argument for player-relative directions: `FORWARD`, `BACKWARD`, `LEFT`,
`RIGHT`, `UP`, `DOWN`. Its argument type lives **on the enum itself**
(`RelativeDirection.ARGUMENT_TYPE`), not in `ArgTypes`:

```java
static final SingleArgumentType<RelativeDirection> ARGUMENT_TYPE
static Vector3i toDirectionVector(RelativeDirection direction, HeadRotation headRotation)
static Axis toAxis(RelativeDirection direction, HeadRotation headRotation)
```

Resolution needs the player's `HeadRotation` component — `FORWARD` is the
horizontal direction the player is facing. This is how the builder-tools
`/move` and `/stack` commands take their direction argument:

```java
private final RequiredArg<RelativeDirection> directionArg =
    withRequiredArg("direction", "Direction to move", RelativeDirection.ARGUMENT_TYPE);

// in execute():
HeadRotation head = store.getComponent(ref, HeadRotation.getComponentType());
Vector3i dir = RelativeDirection.toDirectionVector(ctx.get(directionArg), head);
```

---

## EnumArgumentType
**Package:** `com.hypixel.hytale.server.core.command.system.arguments.types`

The class behind `ArgTypes.forEnum(name, enumClass)` (the factory method simply
constructs one) — you can also instantiate it directly, e.g. as a
`static final` field shared across commands, which is the engine's own pattern:

```java
EnumArgumentType(String name, Class<E> enumClass)   // E extends Enum<E>
E parse(String input, ParseResult result)
void suggest(CommandSender sender, String input, int cursor, SuggestionResult result)
```

Matching is **case-insensitive** against the enum constant names; on a miss the
parse fails with a "no such value" error plus fuzzy *did-you-mean* suggestions,
and tab completion offers the constant names.

## AssetArgumentType
**Package:** `com.hypixel.hytale.server.core.command.system.arguments.types`

Argument type for any **string-keyed JSON asset** class — the way to accept a
custom asset as a command argument when `ArgTypes` has no ready-made constant
for it:

```java
// DataType extends JsonAssetWithMap<String, M>
AssetArgumentType(String name, Class<DataType> type, String argumentUsage)
```

`parse` looks the input up in the asset class's `AssetMap` and fails with a
*"not found"* error plus fuzzy suggestions; tab completion suggests the
registered asset keys. Engine usage, e.g. the `/fluid` command:

```java
private static final SingleArgumentType<Fluid> FLUID_ARG =
    new AssetArgumentType("Fluid", Fluid.class, "The fluid asset id");
```

---

## AbstractOptionalArg
**Package:** `com.hypixel.hytale.server.core.command.system.arguments.system`

Shared base of `OptionalArg`, `DefaultArg`, and `FlagArg` — i.e. the objects
`withOptionalArg` / `withDefaultArg` / `withFlagArg` return. It carries the
fluent modifiers you can chain onto an optional argument when declaring it in
the constructor:

```java
Arg addAliases(String... aliases)        // extra --names for the same arg
Arg setPermission(String permission)     // sender needs this node to use the arg
Arg requiredIf(AbstractOptionalArg<?,?> other, AbstractOptionalArg<?,?>... more)
Arg requiredIfAbsent(AbstractOptionalArg<?,?> other, AbstractOptionalArg<?,?>... more)
Arg availableOnlyIfAll(AbstractOptionalArg<?,?> other, AbstractOptionalArg<?,?>... more)
Arg availableOnlyIfAllAbsent(AbstractOptionalArg<?,?> other, AbstractOptionalArg<?,?>... more)
boolean hasPermission(CommandSender sender)
```

This is the mechanism for per-argument permission gating and for declaring
dependent or mutually-exclusive optionals (`--foo` only valid together with
`--bar`, `--a` required when `--b` is absent, …) — the dependency sets are
verified at parse time, before your `execute` runs.

## GeneralCommandException
**Package:** `com.hypixel.hytale.server.core.command.system.exceptions`

```java
GeneralCommandException(Message message)
void sendTranslatedMessage(CommandSender sender)
String getMessageText()
```

Throw it from inside a command to abort with a user-facing error. It extends
`CommandException` (a `RuntimeException`, so no `throws` declaration needed);
the command manager catches `CommandException` during execution and sends the
message to the **sender's chat** instead of logging a stack trace — consistent
with the parse-error behavior described in
[Argument syntax](#argument-syntax-input-format). Any *other* exception type is
logged at SEVERE and reported to the sender as a generic command error.

## EntityRemoveCommand
**Package:** `com.hypixel.hytale.server.core.command.commands.world.entity`

The built-in `/entity remove` (an `AbstractWorldCommand` subcommand of the
`/entity` collection): removes the entity given by `--entity=<id>` or, when
omitted, the entity the sender is looking at; the `--others` flag instead
removes every entity *except* the target and players. Useful to plugins mainly
for its public static helper:

```java
static void removeEntity(Ref<EntityStore> playerRef, Ref<EntityStore> entityRef,
                         ComponentAccessor<EntityStore> accessor)
```

which refuses to remove an entity the given player can't currently see (entity
tracker visibility check, with a chat message) and otherwise removes it with
`RemoveReason.REMOVE`.

## Gotchas & Errors

Error strings below are the literal messages thrown by the 0.6.3 command system (verified against `HytaleServer.jar`).

- **`Registered commands must define a name`** → you constructed a command with a null/empty name. Fix: pass a non-empty name to `super("name", ...)`.
- **`Cannot create a Required Argument with 0 parameters.`** → a custom `ArgumentType` reports zero input tokens. Fix: make `getNumberOfParameters()` return ≥ 1.
- **`Cannot register additional required arguments after a greedy string argument`** → a greedy/list string argument consumes the rest of the line, so nothing may follow it. Fix: declare the greedy argument last.
- **`Cannot add a subcommand with no name`** / **`Cannot have multiple subcommands with the same name`** → `addSubCommand()` got an unnamed or duplicate child. Fix: give each subcommand a unique, non-empty name.
- **`Cannot re-use subcommands. Only one parent command allowed for each subcommand`** → the same `AbstractCommand` instance was added under two parents. Fix: construct a separate instance per parent.
- **`Cannot change permissions when a command has already completed registration`** → `requirePermission(...)` / `requireNoPermission()` was called after the command was registered. Fix: call it in the constructor.
- **`Cannot add new arguments when a command has already completed registration`** → you called `withRequiredArg`/`addAliases`/`requirePermission`/etc. after the command was registered. Fix: declare all arguments, aliases, and permissions in the constructor, before `registerCommand()`. (The same guard exists as `Cannot add aliases…`, `Cannot change permissions…`, `Cannot add new subcommands…`.)
- **`Unknown owner type, please use PluginBase or CommandManager`** → `setOwner()` received something that is neither a plugin nor the command manager. Fix: register through `getCommandRegistry()` from your `JavaPlugin`.
- **Symptom:** a freshly registered `/mycommand` replies *"no permission"* for ordinary players → every command auto-generates a permission node that the default `hytale:Adventurer` group doesn't hold (only `hytale:Admin`, via its `*` wildcard, does). Fix: call `requireNoPermission()` in the constructor, or grant the node to a group (see [Permissions](permissions.md)). See [Permission model](#permission-model-why-a-new-command-says-no-permission).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
