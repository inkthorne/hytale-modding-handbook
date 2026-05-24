# Commands Example Plugin

Demonstrates the Hytale command system with two example commands.

## Commands

### `/hello`
Simple command with no arguments. Sends a greeting message to the player.

**Example:** `/hello` → "Hello, PlayerName!"

### `/tp <x> <y> <z>`
Teleport command demonstrating position arguments. Supports relative coordinates.

**Examples:**
- `/tp 100 64 200` - Teleport to absolute coordinates
- `/tp ~10 ~ ~-5` - Move 10 blocks on X, stay same Y, move -5 on Z

## Building

```batch
build.bat
```

Or:

```batch
gradlew build
```

## Installation

Copy `build/libs/example-commands.jar` to:
```
%APPDATA%\Hytale\UserData\Mods\
```

## Code Structure

- `CommandsPlugin.java` - Main plugin class, registers commands
- `HelloCommand.java` - Simplest command example (extends `AbstractPlayerCommand`)
- `TeleportCommand.java` - Command with `RELATIVE_POSITION` argument

## Key API Patterns

### Plugin Setup
```java
public class CommandsPlugin extends JavaPlugin {
    public CommandsPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        getCommandRegistry().registerCommand(new HelloCommand());
        getCommandRegistry().registerCommand(new TeleportCommand());

        getLogger().atInfo().log("CommandsExample plugin loaded!");
    }
}
```

### Command with Arguments
```java
public class TeleportCommand extends AbstractPlayerCommand {
    private final RequiredArg<RelativeDoublePosition> positionArg;

    public TeleportCommand() {
        super("tp", "Teleport to a position");
        positionArg = withRequiredArg("position", "Target position", ArgTypes.RELATIVE_POSITION);
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        RelativeDoublePosition pos = ctx.get(positionArg);
        // Use pos...
    }
}
```

### Opening Commands to Non-Ops
By default each command auto-generates a permission node that only ops hold, so
a normal player gets "no permission". Both example commands override
`canGeneratePermission()` to return `false` so anyone can run them:
```java
// By default each command auto-generates a permission node (here "hello")
// that only ops hold (the OP group carries the '*' wildcard), so a normal
// player gets "no permission". Returning false skips node generation, leaving
// the command open to everyone. Use requirePermission("...") to gate instead.
@Override
protected boolean canGeneratePermission() {
    return false;
}
```
