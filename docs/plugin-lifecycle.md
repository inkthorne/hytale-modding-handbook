# Plugin Lifecycle API

**Doc type:** Java API

## Class Hierarchy
```
PluginBase (abstract, implements CommandOwner)
  └── JavaPlugin (abstract)
        └── YourPlugin
```

## JavaPlugin
**Package:** `com.hypixel.hytale.server.core.plugin`

Your plugin must extend this class.

```java
public abstract class JavaPlugin extends PluginBase {
    public JavaPlugin(JavaPluginInit init);
    public Path getFile();
    public PluginClassLoader getClassLoader();
    public final PluginType getType();
}
```

### Required Constructor
```java
public YourPlugin(JavaPluginInit init) {
    super(init);
}
```

## PluginBase
**Package:** `com.hypixel.hytale.server.core.plugin`

Base class providing all plugin functionality.

### Lifecycle Methods
Override these to hook into plugin lifecycle:
```java
protected void setup();                       // Register commands, events, etc.
protected void setup0();                      // Internal setup (called by framework)
protected void start();                       // Called after setup
protected void start0();                      // Internal start (called by framework)
public CompletableFuture<Void> preLoad();     // Async pre-loading
protected void shutdown();                    // Clean up resources
protected void shutdown0(boolean graceful);   // Internal shutdown
```

### Registries (from PluginBase)
Access these via getter methods:
```java
getCommandRegistry()       // CommandRegistry - register commands
getEventRegistry()         // EventRegistry - register event listeners
getTaskRegistry()          // TaskRegistry - schedule tasks
getEntityRegistry()        // EntityRegistry - register entities
getAssetRegistry()         // AssetRegistry - register assets
getEntityStoreRegistry()   // ComponentRegistryProxy<EntityStore>
getChunkStoreRegistry()    // ComponentRegistryProxy<ChunkStore>
getClientFeatureRegistry() // ClientFeatureRegistry
```

> **See also:** [Commands API](commands.md#commandregistry)

### Configuration
```java
// Load configuration from file with default fallback
<T> Config<T> withConfig(BuilderCodec<T> codec)
<T> Config<T> withConfig(String name, BuilderCodec<T> codec)
```

See [Codecs Documentation](codecs.md) for BuilderCodec details.

### Utility Methods
```java
getName()           // String - plugin name from manifest
getLogger()         // HytaleLogger - logging
getIdentifier()     // PluginIdentifier
getManifest()       // PluginManifest
getDataDirectory()  // Path - plugin data folder
getState()          // PluginState - current state
getBasePermission() // String - base permission node
isEnabled()         // boolean
isDisabled()        // boolean
```

---

## Accessing Core Modules

Hytale provides singleton accessor methods for core game modules. All modules follow the same pattern: call the static `.get()` method to retrieve the module instance.

### Standard Pattern
```java
// All modules use the same static .get() accessor pattern
CollisionModule collision = CollisionModule.get();
ProjectileModule projectiles = ProjectileModule.get();
PrefabStore prefabs = PrefabStore.get();
```

### Common Modules

| Module | Package | Description |
|--------|---------|-------------|
| `CollisionModule` | `com.hypixel.hytale.server.core.modules.collision` | Collision detection and raycasting |
| `ProjectileModule` | `com.hypixel.hytale.server.core.modules.projectile` | Projectile spawning and management |
| `PrefabStore` | `com.hypixel.hytale.server.core.prefab` | Load and spawn prefabs |
| `BlockModule` | `com.hypixel.hytale.server.core.modules.block` | Block operations (place, break, query) |
| `DamageModule` | `com.hypixel.hytale.server.core.modules.entity.damage` | Damage calculation and application |
| `ItemModule` | `com.hypixel.hytale.server.core.modules.item` | Item operations |
| `EntityModule` | `com.hypixel.hytale.server.core.modules.entity` | Entity spawning and management |
| `TimeModule` | `com.hypixel.hytale.server.core.modules.time` | Time and tick management |

### Usage Example
```java
import com.hypixel.hytale.server.core.modules.collision.CollisionModule;
import com.hypixel.hytale.server.core.modules.projectile.ProjectileModule;
import com.hypixel.hytale.server.core.prefab.PrefabStore;

@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // Get module instances
    CollisionModule collision = CollisionModule.get();
    ProjectileModule projectiles = ProjectileModule.get();
    PrefabStore prefabs = PrefabStore.get();

    // Use modules for game operations
    // collision.raycast(...);
    // projectiles.spawn(...);
    // prefabs.load(...);
}
```

### When to Use Modules

Modules are accessed at runtime when you need to perform game operations. Common scenarios:
- **Commands** - Access modules in `execute()` to perform actions
- **Event handlers** - Access modules to respond to game events
- **Custom interactions** - Access modules in `tick()` methods

**Note:** Module instances are thread-safe singletons managed by the server. You can safely call `.get()` from any context without caching the reference.

## JavaPluginInit
**Package:** `com.hypixel.hytale.server.core.plugin`

Passed to plugin constructor by server. Do not instantiate yourself.

```java
public class JavaPluginInit extends PluginInit {
    public Path getFile();
    public PluginClassLoader getClassLoader();
    public boolean isInServerClassPath();
}
```

---

## PluginState
**Package:** `com.hypixel.hytale.server.core.plugin`

Enum representing the current lifecycle state of a plugin. Get via `getState()`.

```java
public enum PluginState {
    NONE,      // Initial state before setup
    SETUP,     // Currently in setup() phase
    START,     // Currently in start() phase
    ENABLED,   // Fully enabled and running
    SHUTDOWN,  // Currently shutting down
    DISABLED,  // Fully disabled
    FAILED     // Plugin failed to load or run
}
```

### Usage Example
```java
if (getState() == PluginState.ENABLED) {
    // Plugin is fully running
}
```

---

## PluginIdentifier
**Package:** `com.hypixel.hytale.common.plugin`

Identifies a plugin by group and name. Get via `getIdentifier()`.

### Methods
```java
String getGroup()                              // Plugin group (e.g., "com.example")
String getName()                               // Plugin name
static PluginIdentifier fromString(String s)   // Parse from "group:name" format
```

### Usage Example
```java
PluginIdentifier id = getIdentifier();
String fullName = id.getGroup() + ":" + id.getName();
```

---

## PluginManifest
**Package:** `com.hypixel.hytale.common.plugin`

Contains plugin metadata from `manifest.json`. Get via `getManifest()`.

### Identity
```java
String getGroup()                    // Plugin group
String getName()                     // Plugin name
Semver getVersion()                  // Version (semantic versioning)
String getMain()                     // Main class path
```

### Metadata
```java
String getDescription()              // Plugin description
List<AuthorInfo> getAuthors()        // Author information
String getWebsite()                  // Plugin website URL
```

### Dependencies
```java
Map<PluginIdentifier, SemverRange> getDependencies()          // Required dependencies
Map<PluginIdentifier, SemverRange> getOptionalDependencies()  // Optional dependencies
Map<PluginIdentifier, SemverRange> getLoadBefore()            // Plugins to load before
String getServerVersion()                                      // Required server version
```

### Other
```java
boolean isDisabledByDefault()        // Whether disabled by default
boolean includesAssetPack()          // Whether plugin includes assets
List<PluginManifest> getSubPlugins() // Sub-plugin manifests
```

---

## manifest.json

Every plugin requires a `manifest.json` file in `src/main/resources/`.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `Group` | String | Plugin group/namespace (e.g., `"myplugin"`) |
| `Name` | String | Plugin display name |
| `Main` | String | Fully qualified main class name |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `Version` | String | Semantic version (e.g., `"1.0.0"`) |
| `Description` | String | Plugin description |
| `Website` | String | Plugin website URL |
| `Authors` | Array | List of author objects |
| `IncludesAssetPack` | Boolean | Set to `true` if plugin contains assets (`.ui` files, textures, JSON definitions) |
| `DisabledByDefault` | Boolean | Whether plugin starts disabled |
| `Dependencies` | Object | Required plugin dependencies |
| `OptionalDependencies` | Object | Optional plugin dependencies |
| `LoadBefore` | Object | Plugins that should load after this one |
| `ServerVersion` | String | Required server version range |
| `SubPlugins` | Array | Nested sub-plugin manifests |

### Minimal Example

```json
{
  "Group": "myplugin",
  "Name": "My Plugin",
  "Main": "com.example.MyPlugin"
}
```

### Full Example

```json
{
  "Group": "myplugin",
  "Name": "My Plugin",
  "Version": "1.0.0",
  "Description": "A sample plugin",
  "Website": "https://example.com",
  "Authors": [
    { "Name": "Developer Name" }
  ],
  "Main": "com.example.MyPlugin",
  "IncludesAssetPack": true,
  "DisabledByDefault": false,
  "Dependencies": {
    "othergroup:otherplugin": ">=1.0.0"
  },
  "ServerVersion": ">=0.1.0"
}
```

### Field Details

#### IncludesAssetPack

Set to `true` when your plugin contains:
- `.ui` files (in `Common/UI/Custom/`)
- Textures or images
- JSON asset definitions

Assets must be placed in `src/main/resources/` and will be packaged into the JAR.

#### Dependencies Format

Dependencies use `group:name` as keys with semver ranges as values:

```json
"Dependencies": {
  "core:essentials": ">=1.0.0",
  "utils:helper": "^2.0.0"
}
```

#### Authors Format

```json
"Authors": [
  { "Name": "Primary Author" },
  { "Name": "Contributor" }
]
```

---

## HytaleLogger
**Package:** `com.hypixel.hytale.logger`

Fluent logging API based on Google Flogger. Get via `getLogger()` in your plugin.

### Getting a Logger
```java
// In PluginBase (your plugin)
HytaleLogger logger = getLogger();

// Static access
HytaleLogger logger = HytaleLogger.forEnclosingClass();
HytaleLogger logger = HytaleLogger.get("my.logger.name");
```

### Logging Methods (Fluent API)
```java
// Log at different levels
getLogger().atInfo().log("Server started");
getLogger().atWarning().log("Something might be wrong");
getLogger().atSevere().log("Critical error occurred");
getLogger().atFine().log("Debug information");

// With formatting
getLogger().atInfo().log("Player %s joined", playerName);
getLogger().atInfo().log("Count: %d, Value: %.2f", count, value);

// With exceptions
getLogger().atSevere().withCause(exception).log("Operation failed");
```

### Log Levels
Use `at(Level)` with standard `java.util.logging.Level` values:
- `atSevere()` - Errors
- `atWarning()` - Warnings
- `atInfo()` - Information
- `atFine()` / `atFiner()` / `atFinest()` - Debug levels

### Configuration
```java
logger.setLevel(Level.FINE);        // Set minimum log level
Level level = logger.getLevel();    // Get current level
HytaleLogger sub = logger.getSubLogger("subsystem");  // Create sub-logger
```

### Usage Example
```java
@Override
protected void setup() {
    getLogger().atInfo().log("Plugin setup starting...");

    try {
        // Initialize something
        getLogger().atFine().log("Initialized feature X");
    } catch (Exception e) {
        getLogger().atSevere().withCause(e).log("Failed to initialize");
    }

    getLogger().atInfo().log("Plugin setup complete!");
}
```

## Usage Example
```java
package com.example.myplugin;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;

public class MyPlugin extends JavaPlugin {
    public MyPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        getCommandRegistry().registerCommand(new MyCommand());
        getLogger().atInfo().log("Plugin setup complete!");
    }
}
```

> **See also:** [Event Systems](events.md)

---

## Server Lifecycle Events

**Package:** `com.hypixel.hytale.server.core.event.events`

Events related to server lifecycle.

| Class | Description |
|-------|-------------|
| `BootEvent` | Server boot has completed |
| `ShutdownEvent` | Server is shutting down |
| `PrepareUniverseEvent` | Universe preparation phase (configure worlds) |

---

### PrepareUniverseEvent

Fired during universe preparation, before worlds are loaded. Allows plugins to configure or modify world settings.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getWorldConfigProvider()` | `WorldConfigProvider` | Get the world configuration provider |
| `setWorldConfigProvider(WorldConfigProvider)` | `void` | Set a custom world configuration provider |

```java
getEventRegistry().register(PrepareUniverseEvent.class, event -> {
    var configProvider = event.getWorldConfigProvider();
    getLogger().atInfo().log("Universe preparing with config: " + configProvider);
});
```

### Usage Example

```java
import com.hypixel.hytale.server.core.event.events.BootEvent;
import com.hypixel.hytale.server.core.event.events.ShutdownEvent;

@Override
protected void setup() {
    // Listen for server boot completion
    getEventRegistry().register(BootEvent.class, event -> {
        getLogger().atInfo().log("Server has finished booting!");
    });

    // Listen for server shutdown
    getEventRegistry().register(ShutdownEvent.class, event -> {
        getLogger().atInfo().log("Server is shutting down, saving data...");
    });
}
```

---

## Plugin Events

**Package:** `com.hypixel.hytale.server.core.plugin.event`

Events related to plugin lifecycle. These are **keyed by plugin class** (`Class<? extends PluginBase>`).

### Event Summary

| Class | Description |
|-------|-------------|
| `PluginEvent` | Base class for plugin lifecycle events |
| `PluginSetupEvent` | Plugin setup has completed |

---

### PluginEvent (Base Class)

Abstract base class for plugin-related events. Keyed by plugin class.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPlugin()` | `PluginBase` | The plugin this event relates to |

---

### PluginSetupEvent

Fired when a plugin's setup has completed. Extends `PluginEvent`.

### Constructor

```java
public PluginSetupEvent(PluginBase plugin)
```

### Inherited Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPlugin()` | `PluginBase` | The plugin that completed setup |

### Usage Example

```java
import com.hypixel.hytale.server.core.plugin.event.PluginSetupEvent;

@Override
protected void setup() {
    // Listen for when any plugin completes setup
    getEventRegistry().registerGlobal(PluginSetupEvent.class, event -> {
        System.out.println("Plugin setup completed: " + event.getPlugin());
    });

    // Listen for a specific plugin's setup (keyed by plugin class)
    getEventRegistry().register(PluginSetupEvent.class, MyPlugin.class, event -> {
        System.out.println("MyPlugin setup completed!");
    });
}
```

---

## Complete Lifecycle Example

```java
import com.hypixel.hytale.server.core.event.events.BootEvent;
import com.hypixel.hytale.server.core.event.events.ShutdownEvent;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.plugin.event.PluginSetupEvent;

public class MyPlugin extends JavaPlugin {

    public MyPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        // Register commands
        getCommandRegistry().registerCommand(new MyCommand());

        // Register lifecycle event listeners
        getEventRegistry().register(BootEvent.class, event -> {
            getLogger().atInfo().log("Server boot complete - initializing plugin features");
            // Initialize features that require the server to be fully booted
        });

        getEventRegistry().register(ShutdownEvent.class, event -> {
            getLogger().atInfo().log("Saving plugin data before shutdown...");
            // Save any persistent data
        });

        // Listen for other plugins completing setup
        getEventRegistry().registerGlobal(PluginSetupEvent.class, event -> {
            if (event.getPlugin() != this) {
                getLogger().atInfo().log("Another plugin finished setup: " + event.getPlugin().getName());
            }
        });

        getLogger().atInfo().log("Plugin setup complete!");
    }

    @Override
    protected void shutdown() {
        getLogger().atInfo().log("Plugin shutdown method called");
        // Clean up plugin resources
    }
}
