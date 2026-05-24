# NPC API

**Doc type:** Java API

This document covers NPC loading events and AI sensor systems.

## Overview

Implemented in `com.hypixel.hytale.server.npc` (with `spawning` and `npc.corecomponents.world` subsystems) and provides:
- NPC loading events (`AllNPCsLoadedEvent`, `LoadedNPCEvent`)
- `BuilderInfo`, metadata describing each loaded NPC definition
- AI sensor events (`SensorEvent`, `SensorEntityEvent`) for entity detection
- Sensor builder classes for configuring detection range and target search
- `EventSearchType` for controlling player-vs-NPC search priority

## Architecture
```
NPC System
├── Loading Events
│   ├── AllNPCsLoadedEvent   (all NPCs finished loading)
│   ├── LoadedNPCEvent       (individual NPC loaded)
│   └── BuilderInfo          (per-NPC definition metadata)
└── AI Sensors
    ├── SensorEvent          (base sensor event, extends SensorBase)
    │   └── SensorEntityEvent (entity detection)
    ├── EventSearchType      (player/NPC search priority)
    └── Builders
        ├── BuilderSensorEvent
        └── BuilderSensorEntityEvent
```

## Key Classes
| Class | Location | Description |
|-------|----------|-------------|
| `AllNPCsLoadedEvent` | `server.npc` | Fired once when all NPCs finish loading |
| `LoadedNPCEvent` | `server.spawning` | Fired when an individual NPC definition loads |
| `BuilderInfo` | `server.npc.asset.builder` | Metadata about an NPC definition |
| `SensorEvent` | `server.npc.corecomponents.world` | Abstract base for sensor events |
| `SensorEntityEvent` | `server.npc.corecomponents.world` | Entity-specific sensor event |
| `EventSearchType` | `server.npc.corecomponents.world.SensorEvent` | Enum controlling sensor target search |
| `BuilderSensorEvent` | `server.npc.corecomponents.world.builders` | Builder for sensor event configuration |
| `BuilderSensorEntityEvent` | `server.npc.corecomponents.world.builders` | Builder adding entity-specific sensor config |

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [NPC Roles](npc-roles.md) | `npc-roles.md` | Asset definitions: templates, variants, behaviors, spawning (897 roles) |

---

## NPC Events

Events related to NPC (Non-Player Character) loading and management.

### AllNPCsLoadedEvent

**Package:** `com.hypixel.hytale.server.npc`

Fired once when all NPCs have finished loading. This is a **non-keyed event**.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAllNPCs()` | `Int2ObjectMap<BuilderInfo>` | Map of all NPC definitions (by ID) |
| `getLoadedNPCs()` | `Int2ObjectMap<BuilderInfo>` | Map of NPCs loaded in this batch |

```java
getEventRegistry().register(AllNPCsLoadedEvent.class, event -> {
    var allNpcs = event.getAllNPCs();
    System.out.println("Total NPCs loaded: " + allNpcs.size());
});
```

> **See also:** [Event Registration](plugin-lifecycle.md#server-lifecycle-events)

### LoadedNPCEvent

**Package:** `com.hypixel.hytale.server.spawning`

Fired when an individual NPC definition is loaded. This is a **non-keyed event**.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getBuilderInfo()` | `BuilderInfo` | The NPC's builder information |

```java
getEventRegistry().register(LoadedNPCEvent.class, event -> {
    var builderInfo = event.getBuilderInfo();
    System.out.println("NPC loaded: " + builderInfo);
});
```

---

## BuilderInfo

**Package:** `com.hypixel.hytale.server.npc.asset.builder`

Contains metadata about an NPC definition. Returned by `AllNPCsLoadedEvent.getAllNPCs()`, `AllNPCsLoadedEvent.getLoadedNPCs()`, and `LoadedNPCEvent.getBuilderInfo()`.

### Identity

```java
int getIndex()           // NPC definition index (unique ID)
String getKeyName()      // NPC key/identifier name (e.g., "zombie", "skeleton")
Path getPath()           // File path of the NPC definition asset
```

### Builder Access

```java
Builder<?> getBuilder()  // The NPC builder instance for spawning
```

### Validation State

```java
boolean isValid()           // Whether the NPC definition is valid
boolean isValidated()       // Whether validation has been performed
boolean needsValidation()   // Whether validation is pending
boolean canBeValidated()    // Whether the NPC can be validated
```

### State Management

```java
void setNeedsValidation()   // Mark for re-validation
void setNeedsReload()       // Mark for reload
void setForceValidation()   // Force validation
boolean setValidated(boolean validated)  // Set validation state
```

### Removal

```java
boolean isRemoved()         // Whether NPC definition was removed
void setRemoved()           // Mark as removed
```

### Usage Example

```java
getEventRegistry().register(AllNPCsLoadedEvent.class, event -> {
    event.getAllNPCs().forEach((id, builderInfo) -> {
        String name = builderInfo.getKeyName();
        int index = builderInfo.getIndex();
        boolean valid = builderInfo.isValid();

        getLogger().atInfo().log("NPC %d (%s) - valid: %b", index, name, valid);
    });
});
```

---

## Sensor Events

Events and classes related to NPC AI sensors. Sensors detect entities and trigger NPC behaviors.

> **See also:** [ECS Event System](components.md#event-type-registration)

**Package:** `com.hypixel.hytale.server.npc.corecomponents.world`

### SensorEvent (Base Class)

Abstract base class for sensor events. Extends `SensorBase`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `matches(Ref, Role, double, Store)` | `boolean` | Check if sensor matches given criteria |
| `getSensorInfo()` | `InfoProvider` | Get sensor information provider |

### SensorEntityEvent

Entity-specific sensor event. Extends `SensorEvent`.

Used for detecting entities within an NPC's sensor range.

---

## EventSearchType Enum

**Package:** `com.hypixel.hytale.server.npc.corecomponents.world.SensorEvent`

Controls how sensors search for targets.

| Value | Description |
|-------|-------------|
| `PlayerFirst` | Search players before NPCs |
| `PlayerOnly` | Only search for players |
| `NpcFirst` | Search NPCs before players |
| `NpcOnly` | Only search for NPCs |

---

## Builder Classes

Sensor events use builder patterns for configuration.

### BuilderSensorEvent

**Package:** `com.hypixel.hytale.server.npc.corecomponents.world.builders`

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getRange(BuilderSupport)` | `double` | Sensor detection range |
| `getEventSearchType(BuilderSupport)` | `EventSearchType` | Target search strategy |
| `getLockOnTargetSlot(BuilderSupport)` | `int` | Blackboard slot for locked target |

### BuilderSensorEntityEvent

Extends `BuilderSensorEvent` with additional entity-specific configuration:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getNPCGroup(BuilderSupport)` | `int` | NPC group filter |
| `getEventType(BuilderSupport)` | `EntityEventType` | Entity event type to detect |
| `isFlockOnly(BuilderSupport)` | `boolean` | Whether to only detect flock members |

---

## Sensor Usage Notes

Sensors are primarily used internally by the NPC AI system. They are typically configured through NPC definition files rather than directly in plugin code. The events provide hooks for:

- Detecting when NPCs notice players or other entities
- Customizing target selection logic
- Filtering sensor responses based on entity types

### Example: Listen for NPC Loading

```java
import com.hypixel.hytale.server.npc.AllNPCsLoadedEvent;
import com.hypixel.hytale.server.spawning.LoadedNPCEvent;

@Override
protected void setup() {
    // Listen for individual NPC loads
    getEventRegistry().register(LoadedNPCEvent.class, event -> {
        var info = event.getBuilderInfo();
        System.out.println("Loaded NPC: " + info);
    });

    // Listen for all NPCs finished loading
    getEventRegistry().register(AllNPCsLoadedEvent.class, event -> {
        var allNpcs = event.getAllNPCs();
        System.out.println("All " + allNpcs.size() + " NPCs have been loaded");

        // Iterate loaded NPCs
        allNpcs.forEach((id, builderInfo) -> {
            System.out.println("NPC ID " + id + ": " + builderInfo);
        });
    });
}
```

---

## Integration with AI Systems

NPCs use sensors to detect and respond to entities in the world. The sensor system integrates with the NPC blackboard (memory) system to track targets.

### Sensor Detection Flow

1. Sensor scans for entities within range
2. `EventSearchType` determines search priority (players vs NPCs)
3. Matching entities trigger sensor events
4. Target can be locked to a blackboard slot for AI decision-making

### Example: Custom NPC Behavior on Player Detection

While direct sensor manipulation is limited, you can respond to NPC-related events:

```java
@Override
protected void setup() {
    // Track when NPCs are loaded to log their configurations
    getEventRegistry().register(AllNPCsLoadedEvent.class, event -> {
        event.getAllNPCs().forEach((id, info) -> {
            getLogger().atInfo().log("NPC %d loaded with config: %s", id, info);
        });
    });
}
```
