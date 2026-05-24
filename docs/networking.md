# Networking API

**Doc type:** Java API

## Overview

Types for network serialization and protocol communication between client and server.

## Architecture
```
Network serialization
└── NetworkSerializable<Packet>     toPacket() — implemented by asset types
    (ProjectileConfig, Interaction, Model, ...)

Protocol types (com.hypixel.hytale.protocol)
├── Direction          3D rotation (yaw / pitch / roll)
└── WaitForDataFrom    enum for client/server sync mode
```

## Key Classes
| Class | Location | Description |
|-------|----------|-------------|
| `NetworkSerializable<Packet>` | `server.core.io` | Interface for types serializable to network packets (`toPacket()`) |
| `Direction` | `protocol` | Protocol class for a 3D rotation (yaw, pitch, roll) |
| `WaitForDataFrom` | `protocol` | Enum selecting which side data is awaited from |

## Class Hierarchy
```
NetworkSerializable<Packet> (interface)
  └── Implemented by many asset types (ProjectileConfig, Interaction, Model, etc.)

Direction (protocol class for rotation)
WaitForDataFrom (enum for sync mode)
```

---

## NetworkSerializable
**Package:** `com.hypixel.hytale.server.core.io`

Interface for types that can be serialized to network packets.

### Methods
```java
Packet toPacket()  // Convert to network packet representation
```

### Usage
Many asset types implement this interface to support network transmission:
- `ProjectileConfig` implements `NetworkSerializable<ProjectileConfig>`
- `Interaction` implements `NetworkSerializable<Interaction>`
- `Model` implements `NetworkSerializable<Model>`

```java
// Example: sending an asset over the network
ProjectileConfig config = ProjectileConfig.getAssetMap().get("arrow");
ProjectileConfig packet = config.toPacket();  // Get network-ready version
```

> **See also:** [Projectiles API](projectiles.md#projectileconfig)

---

## Direction
**Package:** `com.hypixel.hytale.protocol`

Protocol class representing a 3D rotation (yaw, pitch, roll). Used for spawn rotation offsets and entity orientations.

### Fields
```java
public float yaw;    // Horizontal rotation (degrees)
public float pitch;  // Vertical rotation (degrees)
public float roll;   // Roll rotation (degrees)
```

### Constructors
```java
Direction()                              // Default (all zeros)
Direction(float yaw, float pitch, float roll)
Direction(Direction other)               // Copy constructor
```

### Serialization
```java
// Serialize to buffer
void serialize(ByteBuf buffer)
int computeSize()

// Deserialize from buffer
static Direction deserialize(ByteBuf buffer, int offset)
static int computeBytesConsumed(ByteBuf buffer, int offset)

// Validation
static ValidationResult validateStructure(ByteBuf buffer, int offset)
```

### Constants
```java
static final int NULLABLE_BIT_FIELD_SIZE;   // Bits for nullable flag
static final int FIXED_BLOCK_SIZE;          // Fixed serialization size
static final int VARIABLE_FIELD_COUNT;      // Variable field count
static final int VARIABLE_BLOCK_START;      // Variable block offset
static final int MAX_SIZE;                  // Maximum serialized size
```

### Other Methods
```java
Direction clone()
boolean equals(Object obj)
int hashCode()
```

### Usage Example
```java
// Create a direction for spawn offset
Direction spawnRotation = new Direction(45.0f, 0.0f, 0.0f);  // 45 degrees yaw

// In ProjectileConfig context
Direction offset = projectileConfig.getSpawnRotationOffset();
float yaw = offset.yaw;
float pitch = offset.pitch;
```

> **See also:** [Math API](math.md#vector3f)

---

## WaitForDataFrom
**Package:** `com.hypixel.hytale.protocol`

Enum specifying which side (client or server) should provide data for an interaction.

### Values
| Value | Description |
|-------|-------------|
| `Client` | Wait for data from client before executing |
| `Server` | Wait for data from server before executing |
| `None` | No data synchronization needed |

### Methods
```java
// Get all values
static WaitForDataFrom[] values()
static final WaitForDataFrom[] VALUES;  // Cached array

// Parse from string
static WaitForDataFrom valueOf(String name)

// Numeric conversion
int getValue()
static WaitForDataFrom fromValue(int value)
```

### Usage Example
```java
// Check synchronization mode for an interaction
SimpleInteraction interaction = ...;
WaitForDataFrom syncMode = interaction.getWaitForDataFrom();

switch (syncMode) {
    case Client:
        // Client sends data first
        break;
    case Server:
        // Server sends data first
        break;
    case None:
        // No synchronization needed
        break;
}
```

### Context
This enum is commonly used with:
- `SimpleInteraction.getWaitForDataFrom()` - Determines interaction data flow
- `ProjectileInteraction.getWaitForDataFrom()` - Projectile sync mode

---

## Notes

- Protocol classes are auto-generated from schema definitions
- ByteBuf is from Netty (io.netty.buffer.ByteBuf)
- Serialization follows a consistent pattern across all protocol types
- Direction is distinct from `Vector3f` - it represents rotation, not position/velocity
