---
title: "Commands API"
description: "Create Hytale server commands in Java — player, world, and target base classes, typed argument parsing and validation, subcommands, permissions, and built-in arg types."
seo:
  type: TechArticle
---

# Commands API

**Doc type:** Java API · **Verified against 0.5.2**

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

## Class Hierarchy
```
AbstractCommand
  └── AbstractAsyncCommand
        ├── AbstractPlayerCommand  (use this for player commands)
        ├── AbstractWorldCommand
        └── AbstractTargetPlayerCommand

CommandSender (interface)
  └── Player (implementation)

CommandOwner (interface)
  └── PluginBase (implementation)

ArgumentType<D> (abstract)
  └── SingleArgumentType<D>

ArgTypes (factory for built-in argument types)
```

## AbstractPlayerCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Most common base class for player-executed commands.

### Constructors
```java
AbstractPlayerCommand(String name, String description)
AbstractPlayerCommand(String name, String description, boolean hidden)
AbstractPlayerCommand(String name)  // no description
```

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

Full working example: [`examples/commands/.../HelloCommand.java`](../examples/commands/src/main/java/hytale/examples/commands/HelloCommand.java) (compiles against the 0.5.0 jar).

```java
public class HelloCommand extends AbstractPlayerCommand {

    public HelloCommand() {
        super("hello", "Sends a friendly greeting");
    }

    // By default each command auto-generates a permission node (here "hello")
    // that only ops hold (the OP group carries the '*' wildcard), so a normal
    // player gets "no permission". Returning false skips node generation, leaving
    // the command open to everyone. Use requirePermission("...") to gate instead.
    @Override
    protected boolean canGeneratePermission() {
        return false;
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
void requirePermission(String permission)       // Require permission
void setPermissionGroups(String... groups)      // Assign command to permission group(s)
void setPermissionGroup(GameMode mode)          // @Deprecated (Update 5) — use setPermissionGroups(String...)
boolean hasPermission(CommandSender sender)     // Check permission
boolean canGeneratePermission()                 // Check if can auto-generate permission
String generatePermissionNode()                 // Generate permission node string

// Configuration
void setUnavailableInSingleplayer(boolean unavailable)  // Mark multiplayer-only
void setAllowsExtraArguments(boolean allows)    // Allow trailing arguments
void setOwner(CommandOwner owner)               // Set owning plugin

// Matching
MatchResult matches(String input, String alias, int depth)  // Check if input matches command
```

> **See also:** [Permissions API](permissions.md#permissionholder)

### Permission model (why a new command says "no permission")

> Verified against 0.5.2 (`AbstractCommand.setOwner`/`hasPermission`, `AssetModule`, `permissions/commands/op`).

When a command is registered, `setOwner()` runs:

```java
if (this.permission == null && canGeneratePermission())   // canGeneratePermission() defaults to true
    this.permission = generatePermission();                // node = command name lowercased, e.g. "menu"
```

So **every command auto-generates a permission node by default**, and `hasPermission(sender)` only passes if the node is `null`, or the sender holds it. A normal player holds nothing, so a freshly written `/menu` replies *"no permission"* until you do one of:

| Option | How | When to use |
|--------|-----|-------------|
| **Open the command** | Override `canGeneratePermission()` to return `false` (leaves the node `null` → everyone passes) | Examples / commands meant for all players |
| **Explicit node** | Call `requirePermission("ui.menu")` in the constructor, then grant that node | Real permission-gated commands |
| **Become op** | Run `/op` in-game; the `OP` group carries the `*` wildcard, satisfying every node | Testing/admin |

```java
public MenuCommand() {
    super("menu", "Opens a custom menu");
}

// Opt out of the auto-generated node so any player can run this command.
@Override
protected boolean canGeneratePermission() {
    return false;
}
```

Notes:
- `/op` (self) is itself gated: it works in local/singleplayer, but a dedicated server requires the `--allow-op` launch arg or your UUID in `permissions.json`.
- The example plugins all override `canGeneratePermission()` so they run without op.

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

## AbstractWorldCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Base class for commands that operate on a world context.

### Constructors
```java
AbstractWorldCommand(String name)
AbstractWorldCommand(String name, String description)
AbstractWorldCommand(String name, String description, boolean allowsExtraArgs)
```

### Abstract Method to Implement
```java
protected abstract void execute(
    CommandContext commandContext,
    World world,
    Store<EntityStore> store
);
```

---

## AbstractTargetPlayerCommand
**Package:** `com.hypixel.hytale.server.core.command.system.basecommands`

Base class for commands that target another player (e.g., admin commands).

### Constructors
```java
AbstractTargetPlayerCommand(String name)
AbstractTargetPlayerCommand(String name, String description)
AbstractTargetPlayerCommand(String name, String description, boolean allowsExtraArgs)
```

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
- `ConsoleSender` - server console / command-block sender

### Usage
```java
CommandSender sender = ctx.sender();
sender.sendMessage(Message.raw("Hello!"));

if (ctx.isPlayer()) {
    Player player = ctx.senderAs(Player.class);
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

### Enum Helper
```java
// Create argument type for any enum
ArgTypes.forEnum(String name, Class<E> enumClass)
```

### Usage Example
```java
public class TeleportCommand extends AbstractPlayerCommand {
    private final Argument<RelativeDoublePosition, RelativeDoublePosition> posArg;

    public TeleportCommand() {
        super("tp", "Teleport to a position");
        posArg = withRequiredArg("position", "Target position", ArgTypes.RELATIVE_POSITION);
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        RelativeDoublePosition relPos = ctx.get(posArg);
        Transform current = playerRef.getTransform();
        Vector3d target = relPos.resolve(current.getPosition());
        // Teleport to target
    }
}
```

### Relative Position Resolution

`RelativeDoublePosition` supports Minecraft-style relative coordinates using `~` (tilde):
- `100 64 200` - Absolute coordinates
- `~ ~ ~` - Player's current position
- `~10 ~ ~-5` - 10 blocks east, same height, 5 blocks south

**Full resolution pattern:**
```java
public class SpawnCommand extends AbstractPlayerCommand {
    private final Argument<RelativeDoublePosition, RelativeDoublePosition> posArg;

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
    private final Argument<Difficulty, Difficulty> diffArg;

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

## Gotchas & Errors

Error strings below are the literal messages thrown by the 0.5.0 command system (verified against `HytaleServer.jar`).

- **`Registered commands must define a name`** → you constructed a command with a null/empty name. Fix: pass a non-empty name to `super("name", ...)`.
- **`Cannot create a Required Argument with 0 parameters.`** → a custom `ArgumentType` reports zero input tokens. Fix: make `getNumberOfParameters()` return ≥ 1.
- **`Cannot register additional required arguments after a greedy string argument`** → a greedy/list string argument consumes the rest of the line, so nothing may follow it. Fix: declare the greedy argument last.
- **`Cannot add a subcommand with no name`** / **`Cannot have multiple subcommands with the same name`** → `addSubCommand()` got an unnamed or duplicate child. Fix: give each subcommand a unique, non-empty name.
- **`Cannot re-use subcommands. Only one parent command allowed for each subcommand`** → the same `AbstractCommand` instance was added under two parents. Fix: construct a separate instance per parent.
- **`Cannot add new arguments when a command has already completed registration`** → you called `withRequiredArg`/`addAliases`/`requirePermission`/etc. after the command was registered. Fix: declare all arguments, aliases, and permissions in the constructor, before `registerCommand()`. (The same guard exists as `Cannot add aliases…`, `Cannot change permissions…`, `Cannot add new subcommands…`.)
- **`Unknown owner type, please use PluginBase or CommandManager`** → `setOwner()` received something that is neither a plugin nor the command manager. Fix: register through `getCommandRegistry()` from your `JavaPlugin`.
- **Symptom:** a freshly registered `/mycommand` replies *"no permission"* for ordinary players → every command auto-generates a permission node that the default `hytale:Adventurer` group doesn't hold (only `hytale:Admin`, via its `*` wildcard, does). Fix: override `canGeneratePermission()` to return `false`, or grant the node to a group (see [Permissions](permissions.md)). See [Permission model](#permission-model-why-a-new-command-says-no-permission).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
