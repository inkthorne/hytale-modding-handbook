---
title: "Networking API"
description: "Hytale network serialization in Java — the NetworkSerializable<Packet> interface for protocol communication, implemented by asset types like ProjectileConfig, Interaction, and Model."
seo:
  type: TechArticle
---

# Networking API

**Doc type:** Java API · **Verified against 0.6.3**

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
| `NetworkSerializer<Type, Packet>` | `server.core.io` | Interface for external converters that turn a server type into its protocol packet |
| `IPacketHandler` | `server.core.io.handlers` | Registration surface handed to sub-handlers (`registerHandler`, `getPlayerRef`) |
| `SubPacketHandler` | `server.core.io.handlers` | **The plugin hook** — a bundle of per-packet-ID handlers attached to each connection |
| `IWorldPacketHandler<T>` | `server.core.io.handlers` | Functional helper that runs a packet handler on the world thread |
| `GenericPacketHandler` | `server.core.io.handlers` | Abstract packet-ID → handler dispatch table (engine base class) |
| `ServerManager` | `server.core.io` | Core network module: listeners, binding, sub-packet-handler registration |
| `ProtocolVersion` | `server.core.io` | Wrapper around the protocol CRC negotiated at connect |
| `PlayerAuthentication` | `server.core.auth` | Authenticated identity of a connection (UUID, username, skin, referral data) |
| `AssetPacketGenerator` | `server.core.asset.packet` | Generates the init/update/remove packets that sync an asset store to clients |
| `ClientFeatureRegistration` | `server.core.registry` | Registration handle for a `ClientFeature` enabled by a plugin |

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
ProjectileConfig config = ProjectileConfig.getAssetMap().getAsset("arrow");
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

As of 0.6.3 the generated protocol types serialize to and from a `java.lang.foreign.MemorySegment`
(the Java FFM API) rather than a Netty `ByteBuf`. The `ByteBuf`-based `serialize(ByteBuf)` /
`deserialize(ByteBuf, int)` / `computeBytesConsumed` / `validateStructure` methods — and the
`protocol.io.ValidationResult` type they returned — were removed by 0.6.3; the replacements are:

```java
// Serialize into a segment at offset; returns the number of bytes written
int serialize(MemorySegment segment, int offset)
int computeSize()

// Deserialize from a segment (ReadCursor = com.hypixel.hytale.protocol.io.ReadCursor)
static Direction toObject(MemorySegment segment)
static Direction toObject(MemorySegment segment, int offset)
static Direction toObject(MemorySegment segment, int offset, ReadCursor cursor)

// Bounds check — throws ProtocolException("...: buffer too small, ...") if the
// segment holds fewer than FIXED_BLOCK_SIZE bytes past offset
static void requireBounds(MemorySegment segment, int offset)

// Zero-copy field accessors (read one field without materializing the object)
static float getYaw(MemorySegment segment)     static float getYaw(MemorySegment segment, int offset)
static float getPitch(MemorySegment segment)   static float getPitch(MemorySegment segment, int offset)
static float getRoll(MemorySegment segment)    static float getRoll(MemorySegment segment, int offset)
```

Every generated protocol class follows this same shape (`toObject` / `requireBounds` / per-field
`getX(MemorySegment[, int])` statics); a malformed buffer surfaces as a
`com.hypixel.hytale.protocol.io.ProtocolException` (see [Gotchas](#gotchas--errors)).

### Constants
```java
static final int NULLABLE_BIT_FIELD_SIZE = 0;   // Bytes of nullable-flag bitfield (none: all fields required)
static final int FIXED_BLOCK_SIZE = 12;         // Fixed serialization size (3 floats)
static final int VARIABLE_FIELD_COUNT = 0;      // Variable-length fields (none)
static final int VARIABLE_BLOCK_START = 12;     // Variable block offset
static final int MAX_SIZE = 12;                 // Maximum serialized size
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

> **See also:** [Math API](math.md#rotation3f). The `SetServerCamera` packet's
> `ServerCameraSettings.rotation` is a `Direction` in **radians** (not the degrees used in JSON
> assets) — see [Camera Control](camera.md#servercamerasettings).

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
- Serialization targets `java.lang.foreign.MemorySegment` (as of 0.6.3; previously Netty's `io.netty.buffer.ByteBuf`) — see [`MemorySegmentUtil`](codecs.md#memorysegmentutil) for the low-level helpers
- Serialization follows a consistent pattern across all protocol types
- Direction is distinct from `Vector3f` - it represents rotation, not position/velocity

---

## Packet Handler Hierarchy

**Package:** `com.hypixel.hytale.server.core.io.handlers` (base class in `com.hypixel.hytale.server.core.io`)

How the server dispatches incoming protocol packets. Every connection has exactly one active
`PacketHandler` (the channel handler — the same class whose `write` / `writeNoCache` you reach via
[`PlayerRef.getPacketHandler()`](entities.md#playerref)); during login the server swaps handlers as
the connection advances, ending at the in-game `GamePacketHandler`. Plugins never subclass these —
the supported hook is [`SubPacketHandler`](#subpackethandler), registered through
[`ServerManager`](#servermanager).

```
PacketHandler (abstract, server.core.io)   per-connection channel handler — write(), writeNoCache(), disconnect()
├── InitialPacketHandler                   first handler: validates Connect (protocol CRC, build), picks auth flow
├── login.HandshakeHandler                 (internal) identity-token handshake base
│   └── login.AuthenticationPacketHandler  (internal) token verification + max-player check
└── GenericPacketHandler (abstract)        packet-ID → Consumer dispatch table
    └── game.GamePacketHandler             the in-game handler; implements IPacketHandler

IPacketHandler   (interface)   registration surface handed to sub-handlers
SubPacketHandler (interface)   ← the plugin hook: bundle of per-packet-ID handlers
IWorldPacketHandler<T>         functional helper: handle a packet on the world thread
```

Login chain (authenticated mode): `InitialPacketHandler` → `AuthenticationPacketHandler` →
password/setup handlers (internal) → `GamePacketHandler`. Only the pieces below are plugin-facing.

### IPacketHandler

The registration surface a `SubPacketHandler` receives. Implemented by `GamePacketHandler`.

```java
void registerHandler(int packetId, Consumer<ToServerPacket> handler)  // handle one packet ID
void registerNoOpHandlers(int... packetIds)  // swallow packet IDs silently
PlayerRef getPlayerRef()                     // the connected player
String getIdentifier()                       // debug identifier used in logs
```

Packet IDs come from the protocol classes (`Packet.getId()`).

### SubPacketHandler

**The plugin hook for handling client→server packets.** One method:

```java
void registerHandlers()  // register your per-packet-ID handlers
```

Register a factory once in your plugin's setup; the server constructs one instance per connecting
player, passing that connection's `IPacketHandler`:

```java
// In your plugin's setup():
ServerManager.get().registerSubPacketHandlers(MyPacketHandler::new);

public class MyPacketHandler implements SubPacketHandler {
    private final IPacketHandler packetHandler;

    public MyPacketHandler(IPacketHandler packetHandler) {
        this.packetHandler = packetHandler;
    }

    @Override
    public void registerHandlers() {
        // 294 = DismountNPC (see the protocol packet classes for IDs)
        this.packetHandler.registerHandler(294,
            packet -> this.handle((DismountNPC) packet));
    }

    private void handle(DismountNPC packet) {
        PlayerRef playerRef = this.packetHandler.getPlayerRef();
        // Handlers run on the network thread — resolve the player's Ref
        // and world.execute(...) before touching ECS state.
    }
}
```

This is exactly how the engine's own optional handlers attach (`MountGamePacketHandler`,
`BuilderToolsPacketHandler`, `TriggerVolumeToolPacketHandler`, the asset-editor and voice
handlers). Sub-handler registration runs **after** the vanilla handlers, and `registerHandler` is
last-write-wins per packet ID — so a sub-handler can also override a built-in handler.

### IWorldPacketHandler

Functional interface that lifts a raw packet handler onto the world thread — it resolves the
`PlayerRef`, schedules onto the player's `World`, and hands you the ECS context:

```java
void handle(T packet, PlayerRef playerRef, Ref<EntityStore> ref,
            World world, Store<EntityStore> store)

// Registration helpers (wrap IPacketHandler.registerHandler):
static <T extends Packet> void registerHandler(
    IPacketHandler packetHandler, int packetId, IWorldPacketHandler<T> handler)
static <T extends Packet> void registerHandler(
    IPacketHandler packetHandler, int packetId, IWorldPacketHandler<T> handler,
    Predicate<PlayerRef> filter)   // gate, e.g. a permission check
```

```java
// From the engine's trigger-volumes tool handler:
IWorldPacketHandler.registerHandler(this.packetHandler, 480,
    this::handleCreate, TriggerVolumeToolPacketHandler::hasPermission);
```

Prefer this over a raw `registerHandler` whenever the handler touches world or entity state.

### GenericPacketHandler

Abstract engine base for table-driven dispatch — `GamePacketHandler` is the concrete in-game
subclass. Plugins don't extend it, but its methods are what `IPacketHandler` registration lands on:

```java
GenericPacketHandler(ChannelConnection channel, ProtocolVersion protocolVersion)

void registerSubPacketHandler(SubPacketHandler subPacketHandler)
<T extends SubPacketHandler> T getSubPacketHandler(Class<T> type)  // 0.6.3+: look up a registered sub-handler by class
void registerHandler(int packetId, Consumer<ToServerPacket> handler)
void registerNoOpHandlers(int... packetIds)
final void accept(ToServerPacket packet)  // dispatch on packet.getId()
static Consumer<ToServerPacket>[] newHandlerArray(int size)
```

Dispatch is an array indexed by packet ID. A packet with **no** registered handler throws
`RuntimeException("No handler is registered for ...")`, and a handler that throws is rethrown as
`RuntimeException("Could not handle packet ...")` — so an unregistered or crashing handler kills
the connection, not just the packet.

### Login pipeline (engine plumbing)

Internal handlers that run before a connection reaches `GamePacketHandler`. Listed for
orientation only — there is no plugin surface here.

| Class | Role |
|-------|------|
| `InitialPacketHandler` | First handler on a fresh connection. Validates the `Connect` packet — protocol CRC, client build number, referral-data size (max 4096 bytes) — then starts the authenticated flow (`AuthenticationPacketHandler`) or the insecure flow, per the server's auth mode. |
| `login.AuthenticationPacketHandler` | Authenticated mode: verifies the client's identity token, enforces the max-player cap, then swaps in the next handler (password check, then setup) which ends at `GamePacketHandler`. |

---

## ServerManager

**Package:** `com.hypixel.hytale.server.core.io`

Core `JavaPlugin` module that owns the network transport and listeners. Singleton via
`ServerManager.get()`.

### Methods

```java
static ServerManager get()

// Plugin surface — register once at setup; one SubPacketHandler instance
// is created per connecting player (see SubPacketHandler above)
void registerSubPacketHandlers(Function<IPacketHandler, SubPacketHandler> supplier)

// Listeners / binding
CompletableFuture<Integer> bind(InetSocketAddress address)   // completes with the bound port (0 = bind failed); returned Boolean before 0.6.3
boolean unbind(ServerListener listener)
void unbindAllListeners()
List<ServerListener> getListeners()
void waitForBindComplete()

// Address helpers
InetSocketAddress getLocalOrPublicAddress() throws SocketException
InetSocketAddress getNonLoopbackAddress() throws SocketException
InetSocketAddress getPublicAddress() throws SocketException

// Engine plumbing — called by GamePacketHandler's constructor
void populateSubPacketHandlers(GamePacketHandler packetHandler)
```

For plugin authors the interesting method is `registerSubPacketHandlers` — everything else is
server bootstrap (binding QUIC listeners at boot, unbinding at shutdown).

---

## ProtocolVersion

**Package:** `com.hypixel.hytale.server.core.io`

Thin wrapper around the protocol CRC the client sends in its `Connect` packet. Created by
`InitialPacketHandler` after the CRC check passes and threaded through every subsequent handler
constructor.

```java
ProtocolVersion(int crc)
int getCrc()
// plus equals / hashCode / toString
```

Client and server protocols must match exactly — a mismatched CRC is rejected at connect with a
client-outdated or server-outdated error before this object is ever constructed.

---

## PlayerAuthentication

**Package:** `com.hypixel.hytale.server.core.auth`

The authenticated identity of a connection, produced by the login pipeline and carried into
`GamePacketHandler` — this is where the player's UUID, username, and skin come from.

```java
PlayerAuthentication()
PlayerAuthentication(UUID uuid, String username)

UUID getUuid()                       void setUuid(UUID uuid)
String getUsername()                 void setUsername(String username)
PlayerSkin getSkin()                 void setSkin(PlayerSkin skin)
byte[] getReferralData()             void setReferralData(byte[] data)
HostAddress getReferralSource()      void setReferralSource(HostAddress source)

static final int MAX_REFERRAL_DATA_SIZE  // 4096
```

Referral data is an opaque byte payload (≤ 4096 bytes) the client presents when another server
referred it here (server transfer), together with the referring server's `HostAddress`.

---

## NetworkSerializer

**Package:** `com.hypixel.hytale.server.core.io`

Counterpart to [NetworkSerializable](#networkserializable): where `NetworkSerializable` lets a type
convert *itself*, `NetworkSerializer<Type, Packet>` is an **external converter** given the value to
convert.

```java
Packet toPacket(Type value)
```

Used where the packet form is built from a different object than the one being serialized — e.g.
adventure-mode objective tasks implement `NetworkSerializer<Objective, ObjectiveTask>` to build
their protocol representation from the owning objective.

---

## Asset Packet Generators

**Package:** `com.hypixel.hytale.server.core.asset.packet`

How server-side asset stores are synced to clients: each asset type's store owns an
`AssetPacketGenerator` that builds the `ToClientPacket`s for the initial full sync and for
later updates/removals (asset-editor live edits, pack reloads).

### AssetPacketGenerator

```java
abstract class AssetPacketGenerator<K, T extends JsonAssetWithMap<K, M>,
                                    M extends AssetMap<K, T>>

abstract ToClientPacket generateInitPacket(M assetMap, Map<K, T> assets)
abstract ToClientPacket generateUpdatePacket(M assetMap, Map<K, T> assets, AssetUpdateQuery query)
abstract ToClientPacket generateRemovePacket(M assetMap, Set<K> keys, AssetUpdateQuery query)
```

### SimpleAssetPacketGenerator

Convenience subclass for generators that don't care about the `AssetUpdateQuery` — it implements
the query variants by delegating to two simpler hooks:

```java
abstract ToClientPacket generateInitPacket(M assetMap, Map<K, T> assets)
protected abstract ToClientPacket generateUpdatePacket(M assetMap, Map<K, T> assets)
protected abstract ToClientPacket generateRemovePacket(M assetMap, Set<K> keys)
```

A `DefaultAssetPacketGenerator` variant further pins the map type to `DefaultAssetMap`. The engine
ships one generator per client-synced asset type (`BlockTypePacketGenerator`,
`EnvironmentPacketGenerator`, `AmbienceFXPacketGenerator`, ...). A generator is wired to a store
with `HytaleAssetStore.Builder.setPacketGenerator(...)` — see
[Creating Custom Asset Types](assets.md#creating-custom-asset-types).

---

## ClientFeatureRegistration

**Package:** `com.hypixel.hytale.server.core.registry`

Registration handle returned when a plugin enables a client-side feature. You normally interact
with the registry, not this object:

```java
// From your plugin (see PluginBase in Plugin Lifecycle):
getClientFeatureRegistry().register(ClientFeature.CrouchSlide);  // returns ClientFeatureRegistration
getClientFeatureRegistry().registerClientTag("Allows=Movement");
```

```java
ClientFeatureRegistration(ClientFeature feature)
ClientFeatureRegistration(ClientFeature feature, BooleanSupplier precondition, Runnable shutdown)
ClientFeature getFeature()
```

Like other `Registration` objects, it is auto-unregistered on plugin shutdown. For the
`ClientFeature` enum values and per-world feature toggles, see
[ClientFeature](world.md#clientfeature); for `getClientFeatureRegistry()`, see
[PluginBase](plugin-lifecycle.md#pluginbase).

---

## Voice Chat

**Package:** `com.hypixel.hytale.server.core.modules.voice`

A core `JavaPlugin` module implements **proximity voice chat** — routing client voice packets to nearby players based on distance. Plugins do not handle the raw audio (that is internal packet plumbing via `VoiceRouter`/`VoicePacketHandler`), but the module exposes a control surface for toggling voice and reading per-player state.

### Key Classes

| Class | Description |
|-------|-------------|
| `VoiceModule` | Core module; singleton via `VoiceModule.get()` |
| `VoiceModuleConfig` | Proximity tuning: `isVoiceEnabled()`, `getMaxHearingDistance()`, `getFullVolumeDistance()`, `getMutedPlayers()` (codec-backed config) |
| `VoicePlayerState` | Per-player voice state, fetched via `VoiceModule.get().getPlayerState(UUID)` |
| `VoiceRouter` | Internal distance-based router (`getVoiceRouter()`); not part of the plugin-authoring surface |

### Control surface

| `VoiceModule` method | Description |
|----------------------|-------------|
| `static VoiceModule get()` | The module singleton |
| `isVoiceEnabled()` / `setVoiceEnabled(boolean)` | Globally toggle voice chat |
| `isDeadPlayersCanHear()` | Whether dead players still receive voice |
| `getPlayerState(UUID)` | The `VoicePlayerState` for a player |
| `getMaxHearingDistance()` / `setMaxHearingDistance(float)` | Proximity cutoff |
| `isPlayerMuted(UUID)` / `mutePlayer(UUID)` / `unmutePlayer(UUID)` / `getGloballyMutedPlayers()` | Server-side global mute list |
| `setPlayerVoiceChannel(UUID, String channel)` | (0.6.3+) Put a player in a named voice channel (`null` = back to the default proximity channel); players only hear others in the same channel |
| `addPlayerVoiceInterceptor(PlayerVoiceInterceptor)` / `(EventPriority, …)` | (0.6.3+) Hook every inbound player voice frame; returns a `Registration` |
| `openEntityVoice(Ref<EntityStore>)` | (0.6.3+) A `VoiceSpeaker` that emits from an entity's position |
| `openPositionalVoice(World, Vector3d)` | (0.6.3+) A `PositionalVoiceSpeaker` at a fixed world position (`setPosition(Vector3d)` to move it) |
| `openDirectVoice(Collection<UUID>)` | (0.6.3+) A `VoiceSpeaker` heard only by the listed players, regardless of distance |
| `getVoiceRouter()` | The internal router (advanced/internal use) |
| `scheduleImmediatePositionUpdate(PlayerRef)` | Force a speaker-position refresh for a player |

### Server-originated audio and voice interception (0.6.3+)

`VoiceSpeaker` (`com.hypixel.hytale.server.core.modules.voice.VoiceSpeaker`) is a server-owned voice
source: `pushOpus(byte[])` streams one Opus frame (≤ `VoiceSpeaker.MAX_OPUS_FRAME_BYTES` = 512
bytes), `play(List<byte[]>)` queues a whole clip and returns a `ClipPlayback` (`cancel()`,
`isDone()`, `completion()`), and `close()` tears the speaker down. `PlayerVoiceInterceptor.intercept(PlayerVoiceFrame)`
sees each frame a player sends before routing: `PlayerVoiceFrame` exposes `speaker()`, `position()`,
`opus()`, and the routing verbs `drop()`, `deliverByProximity()`, `restrictProximityTo(Set<UUID>)`,
`excludeListener(UUID)`, `deliverTo(Collection<UUID>)`.

> [!WARNING]
> Verified against `HytaleServer.jar`, but no inspectable first-party plugin uses this module beyond the engine's own voice command, and audio routing is internal. The toggle/state surface above is real; treat anything below it (router internals) as engine plumbing, not a stable plugin API. (`updatePositionCache(...)` on `VoiceModule` was removed by 0.6.3.)

---

## Gotchas & Errors

Backtick-quoted error strings below are literal message fragments thrown by the protocol deserializer (verified against `HytaleServer.jar`). As of 0.6.3 every malformed-buffer failure is a `com.hypixel.hytale.protocol.io.ProtocolException` built by one of its static factories, and every message starts with the offending **field name** followed by a colon. (The pre-0.6.3 `Buffer too small: expected at least` / `Buffer overflow reading` messages no longer exist.)

- **`: buffer too small, need`** → the full message is `<field>: buffer too small, need <N> bytes but only <M> available` (`ProtocolException.bufferTooSmall`): deserialization would read past the end of the `MemorySegment`; the buffer held fewer bytes than the field required. Fix: call the type's `requireBounds(segment, offset)` before reading, and ensure the writer wrote the full `computeSize()` payload.
- **`is out of bounds (buffer length:`** → `<field>: offset <O> is out of bounds (buffer length: <L>)` (`invalidOffset`); the sibling messages `does not match the canonical layout position` (`nonCanonicalLayout`) and `consumed no bytes` (`nonAdvancingEntry`) mean the same family of fault: a variable-block offset table is inconsistent with the bytes actually present — the length prefixes and the payload disagree. Fix: ensure reader and writer use the same field order/encoding and that every length prefix matches the bytes written.
- **`exceeds maximum`** → `<field>: array length <A> exceeds maximum <M>` / `string length …` / `dictionary count …` (`arrayTooLong` / `stringTooLong` / `dictionaryTooLarge`, with matching `is below minimum` forms): a collection or string field violates the schema's size bounds. Fix: respect the field's declared min/max (they are what the generated `MAX_SIZE` is computed from).
- **`: invalid or incomplete VarInt`** (`invalidVarInt`) → a VarInt was truncated. The related `: unknown polymorphic type ID` (`unknownPolymorphicType`), `: duplicate key '` (`duplicateKey`), and `: invalid enum value` messages mean a polymorphic type tag is unknown to this build, a map carried the same key twice, or an enum ordinal is out of range — usually a client/server protocol mismatch. Fix: make sure both sides run the same protocol CRC (see [ProtocolVersion](#protocolversion)).
- **Symptom:** a custom `NetworkSerializable` round-trips incorrectly or over/under-reads → reader and writer disagree on field order or `MAX_SIZE`. Fix: serialize and deserialize fields in the exact same order, and size the buffer to `MAX_SIZE`.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
