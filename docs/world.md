---
title: "World API"
description: "Work with the Hytale World in Java — the World tick thread exposing players, entities and ECS stores, gameplay and world configuration, world time, game flags, and the world map marker system."
seo:
  type: TechArticle
---

# World API

**Doc type:** Java API + JSON asset format · **Verified against 0.6.3**

Covers the runtime `World` object, its configuration classes, world time, game flags and the world map
markers a plugin can add. Two halves were split out on 2026-09-04: the per-chunk API — `WorldChunk`,
the chunk accessors, block-write settings flags and `ChunkTracker` — is in
[world-chunks.md](world-chunks.md), and the world and chunk lifecycle event classes are in
[world-lifecycle-events.md](world-lifecycle-events.md).

## Overview

Implemented in `com.hypixel.hytale.server.core.universe.world` (and related asset/event subpackages) and provides:
- A `World` tick thread exposing players, entities, chunks, and ECS stores
- Direct block/state/terrain access per `WorldChunk`
- Per-player chunk loading and visibility control via `ChunkTracker`
- Layered gameplay configuration (`GameplayConfig`, `WorldConfig`, `DeathConfig`)
- Per-world client feature toggles (`ClientFeature`)
- World-lifecycle and chunk events (add/remove/start/load, save/unload, moon phase)

## Architecture
```
World (tick thread)
├── Players (getPlayers / addPlayer / PlayerRef)
│   └── ChunkTracker (per-player chunk loading + visibility)
├── Chunks (getChunk* / WorldChunk)
│   ├── Block + state + terrain access
│   └── ChunkFlag (per-chunk state flags)
├── ECS Stores (ChunkStore, EntityStore)
├── Configuration
│   └── GameplayConfig
│       ├── WorldConfig (block rules, day/night, sleep)
│       └── DeathConfig (item loss, respawn)
├── ClientFeature toggles (per-world, broadcast to clients)
└── Events
    ├── World lifecycle (Add / Remove / Start / AllWorldsLoaded)
    └── Chunk (ChunkPreLoadProcess / ChunkSave / ChunkUnload / MoonPhaseChange)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `World` | `server.core.universe.world` | The game world; tick thread exposing players, entities, chunks, and config |
| `WorldChunk` | `server.core.universe.world.chunk` | A loaded chunk; block, state, and terrain data access |
| `ChunkFlag` | `server.core.universe.world.chunk` | Enum of per-chunk state flags |
| `ChunkTracker` | `server.core.modules.entity.player` | Per-player chunk loading rate and visibility |
| `GameplayConfig` | `server.core.asset.type.gameplay` | Master gameplay configuration; holds sub-configs |
| `WorldConfig` (gameplay) | `server.core.asset.type.gameplay` | Block rules, day/night cycle, sleep settings |
| `DeathConfig` | `server.core.asset.type.gameplay` | Death/respawn and item-loss behavior |
| `ClientFeature` | `protocol.packets.setup` | Enum of per-world client feature toggles |
| `WorldEvent` | `server.core.universe.world.events` | Base for world-lifecycle events (keyed by String) |
| `ChunkEvent` | `server.core.universe.world.events` | Base for chunk events |
| `ChunkSaveEvent` / `ChunkUnloadEvent` | `server.core.universe.world.events.ecs` | ECS events for chunk save/unload |
| `MoonPhaseChangeEvent` | `server.core.universe.world.events.ecs` | ECS event fired on moon phase change |
| `SetBlockSettings` | `server.core.universe.world` | Bit flags controlling `setBlock`/`breakBlock` side effects |
| `ChunkAccessor` / `LocalCachedChunkAccessor` | `server.core.universe.world.accessor` | World-coordinate block access; cached accessor for area edits |
| `ChunkColumn` / `ChunkSection` / `BlockSection` / `FluidSection` | `server.core.universe.world.chunk(.section)` | ECS chunk-column component, the per-section entity component, and per-section block/fluid storage |
| `GetChunkFlags` | `server.core.universe.world.storage` | Bit flags for async chunk loading via `ChunkStore` |
| `WorldTimeResource` | `server.core.modules.time` | Per-world game clock resource (time of day, moon phase, sun) |
| `MapMarkerBuilder` / `MarkersCollector` | `server.core.universe.world.worldmap.markers` | Building and collecting world-map markers |
| `PlayerUtil` | `server.core.universe.world` | Static broadcast helpers (messages/packets to players) |

## World
**Package:** `com.hypixel.hytale.server.core.universe.world`

Represents a game world. Extends TickingThread, implements Executor.

### Core Properties
```java
String getName()
boolean isAlive()
boolean isTicking()
void setTicking(boolean ticking)
boolean isPaused()
void setPaused(boolean paused)
long getTick()
HytaleLogger getLogger()
```

### Configuration
```java
WorldConfig getWorldConfig()
DeathConfig getDeathConfig()
GameplayConfig getGameplayConfig()
int getDaytimeDurationSeconds()
int getNighttimeDurationSeconds()
void setTps(int tps)
static void setTimeDilation(float dilation, ComponentAccessor<EntityStore> accessor)
```

See [Configuration Classes](#configuration-classes) below for details on WorldConfig, DeathConfig, and GameplayConfig.

### Players
```java
List<Player> getPlayers()          // @Deprecated(forRemoval=true) — prefer getPlayerRefs()
int getPlayerCount()
int getNonSpectatorPlayerCount()
Collection<PlayerRef> getPlayerRefs()
void trackPlayerRef(PlayerRef ref)
void untrackPlayerRef(PlayerRef ref)

// Adding players
CompletableFuture<PlayerRef> addPlayer(PlayerRef ref)
CompletableFuture<PlayerRef> addPlayer(PlayerRef ref, Transform position)
CompletableFuture<PlayerRef> addPlayer(PlayerRef ref, Transform position, Boolean teleport, Boolean respawn)
CompletableFuture<Void> drainPlayersTo(World targetWorld, Collection<PlayerRef> players)
```

### Entities
```java
Entity getEntity(UUID uuid)
Ref<EntityStore> getEntityRef(UUID uuid)
<T extends Entity> T spawnEntity(T entity, Vector3d position, Rotation3f rotation)
<T extends Entity> T addEntity(T entity, Vector3d position, Rotation3f rotation, AddReason reason)
```

### Chunks
```java
WorldChunk loadChunkIfInMemory(long chunkKey)
WorldChunk getChunkIfInMemory(long chunkKey)                        // @Deprecated
WorldChunk getChunkIfLoaded(long chunkKey)                          // @Deprecated
WorldChunk getChunkIfNonTicking(long chunkKey)                      // @Deprecated
CompletableFuture<WorldChunk> getChunkAsync(long chunkKey)          // @Deprecated
CompletableFuture<WorldChunk> getNonTickingChunkAsync(long chunkKey) // @Deprecated
```

> As of 0.6.3 the five `@Deprecated` getters above carry a plain `@Deprecated` (no `forRemoval`), as does
> the whole `IChunkAccessorSync` interface they come from — they still work. The un-deprecated route to a
> chunk is the `ChunkStore` reference API: `world.getChunkStore().getChunkReferenceAsync(chunkKey, flags)`
> (see [GetChunkFlags](world-chunks.md#getchunkflags)) and `getChunkComponent(chunkKey, WorldChunk.getComponentType())`.

### ECS Stores
```java
ChunkStore getChunkStore()
EntityStore getEntityStore()
```

### Messaging
```java
void sendMessage(Message msg)  // Broadcast to all players in world
```

### Features
```java
Map<ClientFeature, Boolean> getFeatures()
boolean isFeatureEnabled(ClientFeature feature)
void registerFeature(ClientFeature feature, boolean enabled)
void broadcastFeatures()
```

See [ClientFeature](#clientfeature) enum below.

### Other
```java
ChunkLightingManager getChunkLighting()
WorldMapManager getWorldMapManager()
WorldPathConfig getWorldPathConfig()
WorldNotificationHandler getNotificationHandler()
EventRegistry getEventRegistry()
Path getSavePath()

// Lifecycle
CompletableFuture<World> init()
void stopIndividualWorld()
void execute(Runnable task)  // Execute on world thread
ScheduledFuture<?> scheduleAfter(Runnable task, long delay, TimeUnit unit)  // run on the world thread after a delay
```

> **See also:** [ECS Components](components.md#common-store-types)

---

## PlayerUtil
**Package:** `com.hypixel.hytale.server.core.universe.world`

Static helpers for broadcasting to the players of a world's `EntityStore`. Useful from systems that need to notify every player — or only the players who can currently see a given entity.

```java
// Run a callback for each player whose entity tracker can see `entityRef`
static void forEachPlayerThatCanSeeEntity(Ref<EntityStore> entityRef,
        TriConsumer<Ref<EntityStore>, PlayerRef, ComponentAccessor<EntityStore>> callback,
        ComponentAccessor<EntityStore> accessor)

// Broadcast a chat message to all players; players who have hidden
// sourcePlayerUuid (nullable) are skipped
static void broadcastMessageToPlayers(UUID sourcePlayerUuid, Message message, Store<EntityStore> store)

// Broadcast raw packets to all players in the store
static void broadcastPacketToPlayers(ComponentAccessor<EntityStore> accessor, ToClientPacket packet)
static void broadcastPacketToPlayers(ComponentAccessor<EntityStore> accessor, ToClientPacket... packets)
static void broadcastPacketToPlayersNoCache(ComponentAccessor<EntityStore> accessor, ToClientPacket packet)

// Force a player's model to be rebuilt/resent
static void resetPlayerModel(Ref<EntityStore> playerRef, ComponentAccessor<EntityStore> accessor)
```

### Usage Example
```java
// Send an animation packet only to players who can see the entity
PlayerUtil.forEachPlayerThatCanSeeEntity(ref,
        (playerEntityRef, playerRef, accessor) ->
                playerRef.getPacketHandler().write(animationPacket),
        store);
```

For a plain world-wide chat broadcast, `world.sendMessage(Message msg)` (above) is simpler.

---

## Usage Example
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // Get world info
    String worldName = world.getName();
    int playerCount = world.getPlayerCount();

    // Broadcast to all players in world
    world.sendMessage(Message.raw("Hello everyone!"));

    // Get all players (getPlayerRefs() — getPlayers() is deprecated for removal)
    for (PlayerRef ref : world.getPlayerRefs()) {
        ref.sendMessage(Message.raw("Individual message"));
    }
}
```

---

## Configuration Classes

### GameplayConfig
**Package:** `com.hypixel.hytale.server.core.asset.type.gameplay`

Master configuration class containing all gameplay settings for a world. Implements `JsonAssetWithMap`.

#### Getting the Config
```java
// From World
GameplayConfig config = world.getGameplayConfig();

// From asset store (ids are the asset file names, e.g. "Default" — use the constant).
// The lookup method is getAsset(key), inherited from DefaultAssetMap — there is no get(key).
GameplayConfig config = GameplayConfig.getAssetMap().getAsset(GameplayConfig.DEFAULT_ID);
```

#### Key Methods
```java
// Identity
String getId()

// Sub-configs
WorldConfig getWorldConfig()
DeathConfig getDeathConfig()
CombatConfig getCombatConfig()
GatheringConfig getGatheringConfig()
WorldMapConfig getWorldMapConfig()
ItemDurabilityConfig getItemDurabilityConfig()
ItemEntityConfig getItemEntityConfig()
RespawnConfig getRespawnConfig()
PlayerConfig getPlayerConfig()
CameraEffectsConfig getCameraEffectsConfig()
CraftingConfig getCraftingConfig()
SpawnConfig getSpawnConfig()

// Settings
boolean getShowItemPickupNotifications()
int getMaxEnvironmentalNPCSpawns()
String getCreativePlaySoundSet()
int getCreativePlaySoundSetIndex()
String getCreativeEraserInteraction()   // 0.6.3+: interaction id used by the creative eraser tool

// Plugin extensions
MapKeyMapCodec.TypeMap<Object> getPluginConfig()
```

#### Constants
```java
static final String DEFAULT_ID = "Default";   // Default config ID (matches Server/GameplayConfigs/Default.json)
static final GameplayConfig DEFAULT;          // Default config instance
```

---

### WorldConfig
**Package:** `com.hypixel.hytale.server.core.asset.type.gameplay`

Configuration for world-specific gameplay settings like block rules and day/night cycle.

> **Note: two distinct `WorldConfig` classes exist.** The gameplay settings below
> (`isBlockBreakingAllowed`, `getSleepConfig`, day/night durations, `DEFAULT_*_DURATION_SECONDS`)
> live on `com.hypixel.hytale.server.core.asset.type.gameplay.WorldConfig`, reached via
> `world.getGameplayConfig().getWorldConfig()`. The separate `World.getWorldConfig()` method
> returns a *different* class, `com.hypixel.hytale.server.core.universe.world.WorldConfig`,
> which does **not** expose these gameplay accessors. (The universe `WorldConfig` is where
> `get/setSpawnProvider` live — see [Controlling Respawn Location](#controlling-respawn-location).)

#### Key Methods
```java
// Block rules
boolean isBlockBreakingAllowed()
boolean isBlockGatheringAllowed()
boolean isBlockPlacementAllowed()
float getBlockPlacementFragilityTimer()

// Day/night cycle
int getDaytimeDurationSeconds()
int getNighttimeDurationSeconds()
int getTotalMoonPhases()

// Sleep
SleepConfig getSleepConfig()
```

#### Constants
```java
static final int DEFAULT_TOTAL_DAY_DURATION_SECONDS = 2880;
static final int DEFAULT_DAYTIME_DURATION_SECONDS   = 1728;
static final int DEFAULT_NIGHTTIME_DURATION_SECONDS = 1151;   // was 1728 before 0.6.3 — nights are now shorter by default
```

#### Usage Example
```java
// Gameplay WorldConfig is reached through the gameplay config, not world.getWorldConfig()
WorldConfig config = world.getGameplayConfig().getWorldConfig();

if (config.isBlockBreakingAllowed()) {
    // Players can break blocks
}

int dayLength = config.getDaytimeDurationSeconds();
int nightLength = config.getNighttimeDurationSeconds();
```

---

### DeathConfig
**Package:** `com.hypixel.hytale.server.core.asset.type.gameplay`

Configuration for death and respawn behavior.

#### Key Methods
```java
// Respawn
RespawnController getRespawnController()

// Item loss on death
ItemsLossMode getItemsLossMode()
double getItemsAmountLossPercentage()
double getItemsDurabilityLossPercentage()

// 0.6.3+: game-mode type to switch the player to on death (null = not set). World.getGameModeTypeOnDeath()
// returns this when set and otherwise falls back to the server config's Defaults.GameModeTypeOnDeath
String getGameModeTypeOnDeath()
```

#### ItemsLossMode Enum

`DeathConfig.ItemsLossMode` (JSON key `ItemsLossMode`, e.g. `"Configured"` in `Server/GameplayConfigs/Default.json`):

| Value | Description |
|-------|-------------|
| `NONE` | Keep everything on death |
| `ALL` | Drop/lose the whole inventory |
| `CONFIGURED` | Apply `ItemsAmountLossPercentage` / `ItemsDurabilityLossPercentage` |

#### Usage Example
```java
DeathConfig config = world.getDeathConfig();

ItemsLossMode lossMode = config.getItemsLossMode();
double lossPercent = config.getItemsAmountLossPercentage();
```

#### Respawn flow

`getRespawnController()` returns the policy that decides where a dead player reappears. Two built-ins
exist (`com.hypixel.hytale.server.core.asset.type.gameplay.respawn`):

| Controller | Behavior |
|------------|----------|
| `HomeOrSpawnPoint` (default) | Uses the player's personal respawn point if set, else the world spawn provider |
| `WorldSpawnPoint` | Always uses the world spawn provider |

Both ultimately delegate placement to the world's **spawn provider**, which is the seam to override —
see below.

---

### Controlling Respawn Location

To control where players spawn (and respawn), install an `ISpawnProvider` rather than teleporting
players manually. The respawn controller calls the provider and adds the `Teleport` component itself,
so there is no manual-teleport race.

**Package:** `com.hypixel.hytale.server.core.universe.world.spawn` (note: *not* under
`asset.type.gameplay.respawn`). The provider lives on the **universe** `WorldConfig`
(`World.getWorldConfig()`), distinct from the gameplay `WorldConfig`/`DeathConfig` above:

```java
world.getWorldConfig().setSpawnProvider(provider);   // universe.world.WorldConfig
```

The interface has several overloads, but the only one you must implement is
`Transform getSpawnPoint(World, UUID)` — the default `getSpawnPoint(Ref, ComponentAccessor)` and
`getSpawnPoint(Entity)` overloads resolve the UUID/World for you and delegate to it (`getSpawnPoint(Entity)`
is `@Deprecated(forRemoval=true)`; `getSpawnPoints()` is `@Deprecated` but still abstract).

```java
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.spawn.ISpawnProvider;
import java.util.UUID;

public class ArenaSpawnProvider implements ISpawnProvider {
    @Override
    public Transform getSpawnPoint(World world, UUID player) {
        return pickSpawn(player);   // your placement logic
    }

    @Override public Transform[] getSpawnPoints() { return new Transform[0]; } // deprecated, still abstract
    @Override public boolean isWithinSpawnDistance(org.joml.Vector3d p, double d) { return true; }
}
```

Built-ins worth referencing instead of rolling your own:

| Provider | Use |
|----------|-----|
| `GlobalSpawnProvider(Transform)` | One fixed spawn for everyone |
| `IndividualSpawnProvider(Transform[])` | Round-robins / assigns from a set of points |
| `FitToHeightMapSpawnProvider(ISpawnProvider)` | Wraps another provider and ground-snaps a sentinel `y < 0` to the terrain height |

> **⚠️ `getSpawnPoint` is polled, not called once.** It can be invoked repeatedly while the death
> screen is open, not only at the instant of respawn. A provider that returns a *fresh random* point
> each call makes the spawn visibly jitter every tick. Compute once and **cache per player** (keyed on
> the `UUID`), invalidating the cache on respawn (e.g. from a `RespawnSystems.OnRespawnSystem` — see
> [combat.md → Reacting to Death & Respawn](combat.md#reacting-to-death--respawn)).

> **⚠️ `getSpawnPoint` runs OFF the world thread — reading the `Store` there crashes the join.**
> The engine invokes it from `World.addPlayer` (→ `SpawnUtil.applyFirstSpawnTransform`) on a
> **`ServerWorkerGroup`** thread, not the world thread. Any `Store` read inside the provider —
> `Store.forEachChunk(...)`, `World.getNonTickingChunk(...)`, component reads — hits
> `Store.assertThread` and throws `IllegalStateException: Assert not in thread!`. The server then
> logs `SEVERE … Exception when player adding to universe` and disconnects the client with
> `client.general.disconnect.universeException`, which the client shows as a **blank loading screen**
> (`Server closed connection (code=0)` after everything reports "Prepared"). If the provider caches
> per-`UUID`, the *first* joiner populates the cache off-thread without reading the store and joins
> fine, so the crash only fires on the **second** joiner — "works solo, kicks the 2nd player" is the
> signature. To read the store from a provider, marshal onto the world thread (`World` implements
> `Executor`; `Store.isInThread()` detects whether you are already on it — guard to avoid self-deadlock):
>
> ```java
> private Transform computeSpawn(World world, UUID uuid) {
>     if (world.getChunkStore().getStore().isInThread()) {
>         return computeOnThread(world, uuid);   // already on the world thread
>     }
>     CompletableFuture<Transform> r = new CompletableFuture<>();
>     world.execute(() -> {                       // queue onto the world thread, block for the result
>         try { r.complete(computeOnThread(world, uuid)); }
>         catch (Throwable t) { r.completeExceptionally(t); }
>     });
>     return r.join();
> }
> ```
>
> This applies more broadly: engine **callbacks** (spawn providers, and likely other connection/setup
> hooks) may run on a `ServerWorkerGroup` thread, where touching a `Store` throws. Ticking **Systems**
> always run on the world thread and are safe; engine callbacks are not.

Because no world exists at plugin `setup()` time, install the provider per-world from a
`StartWorldEvent` handler — see [World Events](world-lifecycle-events.md#world-events) below.

---

## World Time
**Package:** `com.hypixel.hytale.server.core.modules.time`

Two ECS **resources** on the world's `EntityStore` hold time state. Retrieve them with `store.getResource(...)` from any system running on the world thread.

### WorldTimeResource

The per-world game clock: time of day, calendar date, moon phase, and sun position. This is what ticking systems read to gate day/night behavior, and what you set to change the world's time.

```java
static ResourceType<EntityStore, WorldTimeResource> getResourceType()

// Reading time
Instant getGameTime()
LocalDateTime getGameDateTime()
int getCurrentHour()
float getDayProgress()               // 0.0–1.0 through the current day
double getSunlightFactor()
Vector3d getSunDirection()
boolean isDayTimeWithinRange(double minTime, double maxTime)   // 0–1 fractions; wraps midnight
boolean isScaledDayTimeWithinRange(double minTime, double maxTime)
boolean isYearWithinRange(double min, double max)

// Setting time (broadcasts the update to clients)
void setGameTime(Instant gameTime, World world, ComponentAccessor<EntityStore> accessor)
void setDayTime(double dayTime, World world, ComponentAccessor<EntityStore> accessor)  // 0.0–1.0; rolls forward, never backward
Instant dayProgressToInstant(double dayProgress)                                        // 0.6.3+: the Instant a 0–1 day fraction maps to today

// Smooth time skips (0.6.3+): animate the clock to targetDayProgress over durationSeconds
void startDayTimeInterpolation(double targetDayProgress, double durationSeconds, boolean forward,
                               boolean pauseOnComplete, World world, ComponentAccessor<EntityStore> accessor)
boolean isInterpolating()
void cancelInterpolation()

// Moon phase (see MoonPhaseChangeEvent above)
int getMoonPhase()
void setMoonPhase(int phase, ComponentAccessor<EntityStore> accessor)
void updateMoonPhase(World world, ComponentAccessor<EntityStore> accessor)
boolean isMoonPhaseWithinRange(World world, int min, int max)

// Client sync
void broadcastTimePacket(ComponentAccessor<EntityStore> accessor)
void sendTimePackets(PlayerRef playerRef)

// Statics
static double getSecondsPerTick(World world)
```

Useful constants: `SECONDS_PER_DAY`, `HOURS_PER_DAY`, `DAYS_PER_YEAR`, `DAYTIME_PORTION_PERCENTAGE` (0.6 — daylight fraction of a day), `DAYTIME_SECONDS`, `NIGHTTIME_SECONDS`, `SUNRISE_SECONDS`.

#### Usage Example
```java
WorldTimeResource time = store.getResource(WorldTimeResource.getResourceType());

// Gate behavior on night time (0.75 = midnight-ish, wrapping ranges supported)
if (time.isDayTimeWithinRange(0.7, 0.3)) { /* it's night */ }

// Skip to the next morning
time.setDayTime(0.25, world, store);
```

The day/night *durations* come from the gameplay config — see `getDaytimeDurationSeconds()` / `getNighttimeDurationSeconds()` under [WorldConfig](#worldconfig).

### TimeResource

The tick-advanced wall clock (an `Instant` moved forward each tick, scaled by the time-dilation modifier). `World.setTimeDilation(float, ComponentAccessor)` (see [Configuration](#configuration)) validates the range (0.01–4.0], writes `setTimeDilationModifier`, and syncs clients.

```java
static ResourceType<EntityStore, TimeResource> getResourceType()

Instant getNow()
void setNow(Instant now)
void add(Duration duration)
void add(long amount, TemporalUnit unit)
float getTimeDilationModifier()
void setTimeDilationModifier(float modifier)
```

---

## Game Flags
**Package:** `com.hypixel.hytale.builtin.gameflags` (0.6.3+)

A flat map of **named integer flags**, shared by every world in the universe and persisted with the
save. The bundled `Hytale:GameFlags` plugin describes itself as *"Universe-wide named integer flags
for campaign progression and settings, with asset-authorable read/write interactions"* — it is the
engine's answer to "has the player finished the tutorial yet?", "which gate has this save unlocked?",
"is hard mode on?".

Two properties make it different from the per-world resources above:

- **Scope is the universe, not the world.** `GameFlagsResource` is a
  [universe resource](universe-saves.md#universe-resources) (id `GameFlags`), not an ECS resource on a
  world's store. Every world, and every player, reads and writes the same map. There is **no**
  per-world or per-player game-flag store — for per-player progression use player components or
  `PlayerConfigData` instead.
- **A missing flag reads as `0`.** The codec documents the map as *"Flag name to integer value; a
  missing flag is 0."* There is no "unset" state to test for; `remove(key)` and `set(key, 0)` are
  indistinguishable to a reader.

### GameFlagsResource

```java
static GameFlagsResource get()            // Universe.get().getResource(GameFlagsPlugin.get().getResourceType())
```

| Method | Description |
|--------|-------------|
| `static get()` | The universe's single `GameFlagsResource`. Throws `Universe resources are not loaded yet` before the universe starts |
| `getLevel(String key)` → `int` | The flag's value, or `0` if it was never set |
| `set(String key, int value)` | Overwrite the flag |
| `raise(String key, int level)` | `max(current, level)` — monotonic progression that can never go backwards |
| `remove(String key)` | Drop the flag (subsequent reads return `0`) |
| `snapshot()` → `Map<String, Integer>` | A sorted (`TreeMap`) copy of every flag — safe to iterate |
| `static flush()` | Ask the universe to write `GameFlags.json` now (`Universe.flushResource(...)`) |
| `static final String ID` | `"GameFlags"` — the resource id, and the filename stem |

The backing map is a `ConcurrentHashMap`, so reads and writes are safe from any thread; the
`snapshot()` copy is what you iterate, not the live map.

```java
// Gate a feature on campaign progress
if (GameFlagsResource.get().getLevel("Campaign_Chapter") >= 3) {
    // chapter 3+ content
}

// Advance progression without ever regressing it, then persist immediately
GameFlagsResource flags = GameFlagsResource.get();
flags.raise("Campaign_Chapter", 3);
GameFlagsResource.flush();
```

This `raise`-then-`flush` pair is exactly what the built-in augment-blocks progression does
(`AugmentProgression.raise(...)`).

### Persistence

Writes go into memory immediately; the file on disk is only rewritten when someone flushes.

- Stored as `universe/resources/GameFlags.json` under the single key `Flags` (a string→int map).
- The universe flushes **all** its resources every 10 seconds, before a backup, and on shutdown — so
  a plain `set(...)` does eventually reach disk. `GameFlagsResource.flush()` is for the cases where
  losing the last few seconds matters (the `/gameflags` commands and both interaction types flush).
- See [Universe resources](universe-saves.md#universe-resources) for the storage provider, the
  `.bak` rotation, and the shutdown-flush timeout.

### Asset-authorable interactions

`GameFlagsPlugin.setup()` registers two [interaction](interactions.md) types, so content can read and
write flags without any Java. Both extend `SimpleInstantInteraction`, so they also accept the
inherited `Next` / `Failed` keys and run server-side (`WaitForDataFrom.Server`).

**`SetGameFlag`** — *"An interaction that writes the given game flag."*

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Type` | string | Required | Always `"SetGameFlag"` |
| `Key` | string | Required | Flag name (validated non-null) |
| `Value` | int | `1` | Value to write |
| `Raise` | bool | `false` | *"Whether to only ever raise the flag instead of overwriting it."* — `true` uses `raise(...)`, `false` uses `set(...)` |

**`GameFlagCondition`** — *"An interaction that is successful while the given game flag is at least
(or exactly) the given level."*

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Type` | string | Required | Always `"GameFlagCondition"` |
| `Key` | string | Required | Flag name (validated non-null) |
| `Level` | int | `1` | Level to compare against |
| `Exact` | bool | `false` | *"Whether the flag must equal the level instead of being at least the level."* — `false` tests `flag >= Level`, `true` tests `flag == Level` |

The condition finishes the chain when the test passes and **fails** it when it does not, so the
inherited `Next` / `Failed` branches work the same way as on the other `*Condition` types:

```json
{
  "Type": "GameFlagCondition",
  "Key": "Campaign_Chapter",
  "Level": 3,
  "Next": {
    "Type": "SetGameFlag",
    "Key": "Campaign_GateOpened",
    "Value": 1,
    "Raise": true,
    "Next": "Gate_Open_Anim"
  },
  "Failed": "Gate_Locked_Message"
}
```

No shipped asset uses either type yet — they exist for mod and campaign content.

### `/gameflags`

`GameFlagsCommand` registers a sub-command collection gated on the `hytale:WorldEditor` permission
group:

| Command | Effect |
|---------|--------|
| `/gameflags list` | Print every flag as `key = value` (or "No game flags set") |
| `/gameflags get <key>` | Print `key = value` (`0` for an unset flag) |
| `/gameflags set <key> <value>` | Set the flag and flush |
| `/gameflags remove <key>` | Remove the flag and flush |

> **Gotchas**
> - **`GameFlagsResource.get()` throws `Universe resources are not loaded yet`** → it was called
>   before the universe started (e.g. from a plugin's `setup()`). Read flags from `start()`, a
>   command, or a system tick — never at registration time.
> - **A plugin that touches game flags must depend on the bundled plugin.** Add
>   `"Hytale:GameFlags": "*"` to your manifest's `Dependencies`
>   (see [plugin-lifecycle.md](plugin-lifecycle.md#dependencies-format)); the class lives in the
>   server jar but `GameFlagsPlugin.get()` is `null` until that plugin has run `setup()`, and
>   `GameFlagsResource.get()` goes through it.
> - **Flags are not per world.** Setting a flag in one world changes it for every world in the save.
>   Prefix keys per feature (`MyPlugin_Chapter`) — ids are global and case-sensitive.
> - **`remove` is not "unset".** A removed flag reads back as `0`, exactly like one that was set to
>   `0`; design levels so `0` means "not started".
> - **Flags survive world deletion.** They live in `universe/resources/`, not in
>   `universe/worlds/<name>/` — deleting a world does not reset its progression flags.

---

## ClientFeature
**Package:** `com.hypixel.hytale.protocol.packets.setup`

Enum defining client-side features that can be enabled or disabled per world.

### Values

| Value | Description |
|-------|-------------|
| `SplitVelocity` | Split velocity calculations |
| `Mantling` | Allow mantling/climbing over obstacles |
| `SprintForce` | Sprint force mechanics |
| `CrouchSlide` | Crouch sliding movement |
| `SafetyRoll` | Safety roll on landing |
| `DisplayHealthBars` | Show health bars over entities |
| `DisplayCombatText` | Show combat damage numbers |
| `CanHideHelmet` | Allow the client's hide-helmet cosmetic toggle (0.6.3+) |
| `CanHideCuirass` | Allow hiding the cuirass (0.6.3+) |
| `CanHideGauntlets` | Allow hiding the gauntlets (0.6.3+) |
| `CanHidePants` | Allow hiding the pants (0.6.3+) |

### Methods
```java
static ClientFeature[] values()
static ClientFeature valueOf(String name)
int getValue()
static ClientFeature fromValue(int value)
```

### Usage Example
```java
World world = ...;

// Check if a feature is enabled
if (world.isFeatureEnabled(ClientFeature.DisplayHealthBars)) {
    // Health bars are visible
}

// Enable/disable features
world.registerFeature(ClientFeature.DisplayCombatText, true);
world.registerFeature(ClientFeature.CrouchSlide, false);

// Broadcast changes to all players
world.broadcastFeatures();
```

---

## World Map Markers
**Package:** `com.hypixel.hytale.server.core.universe.world.worldmap.markers`

Plugins add markers to the in-game world map by registering a **marker provider** on the world's `WorldMapManager` (`world.getWorldMapManager()`). The engine calls every registered provider when it refreshes a player's map, passing a `MarkersCollector` to fill. Built-in providers supply the spawn, death, respawn, other-player, and POI markers.

### WorldMapManager.MarkerProvider

```java
// Nested interface WorldMapManager$MarkerProvider — the extension point
void update(World world, Player player, MarkersCollector collector)

// Registration (WorldMapManager)
void addMarkerProvider(String key, WorldMapManager.MarkerProvider provider)
Map<String, WorldMapManager.MarkerProvider> getMarkerProviders()

// Marker overrides (0.6.3+): per-marker-id tweaks layered over what providers emit.
// MapMarkerOverride is a record (server.core.universe.world.worldmap.markers):
//   MapMarkerOverride(UUID id, String icon, Boolean global), or MapMarkerOverride(String icon, Boolean global)
//   (nullable icon/global = leave that property untouched)
Map<String, MapMarkerOverride> getMarkerOverridesView()
boolean addMarkerOverride(String markerId, MapMarkerOverride override)
boolean removeMarkerOverride(String markerId)
boolean removeMarkerOverride(String markerId, MapMarkerOverride override)
void removeAllMarkerOverrides()
```

### MapMarkerBuilder

Builder for the `MapMarker` packet objects a provider adds to the collector:

```java
MapMarkerBuilder(String id, String image, Transform transform)   // image e.g. "Spawn.png"

MapMarkerBuilder withName(Message name)
MapMarkerBuilder withCustomName(String name)
MapMarkerBuilder withContextMenuItem(ContextMenuItem item)
MapMarkerBuilder withComponent(MapMarkerComponent component)
MapMarker build()
```

### MarkersCollector

Passed to `update()`; collects the markers for the player currently being refreshed:

```java
void add(MapMarker marker)                        // respects map view distance
void addIgnoreViewDistance(MapMarker marker)
boolean isInViewDistance(Transform transform)
boolean isInViewDistance(Vector3d position)
boolean isInViewDistance(double x, double z)
Predicate<PlayerRef> getPlayerMapFilter()
```

### Usage Example

Modeled on the built-in `SpawnMarkerProvider`:

```java
import com.hypixel.hytale.server.core.universe.world.worldmap.WorldMapManager;
import com.hypixel.hytale.server.core.universe.world.worldmap.markers.MapMarkerBuilder;
import com.hypixel.hytale.server.core.universe.world.worldmap.markers.MarkersCollector;

public class ArenaMarkerProvider implements WorldMapManager.MarkerProvider {
    @Override
    public void update(World world, Player player, MarkersCollector collector) {
        collector.add(new MapMarkerBuilder("Arena", "Spawn.png", new Transform(arenaCenter))
                .withCustomName("The Arena")
                .build());
    }
}

// Register per world, e.g. from a StartWorldEvent handler (see World Events below):
world.getWorldMapManager().addMarkerProvider("arena", new ArenaMarkerProvider());
```

### RevealMapMarkersInView

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.RevealMapMarkersInViewInteraction`

The JSON interaction side of the marker system: a `Type` value written in an item's `Interactions`
block that reveals discoverable markers the player is looking at. Codec doc: "Reveals the
discoverable world map markers that sit inside the view cone of the player." Extends
`SimpleInteraction`, and it keeps scanning while it runs rather than firing once.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `FieldOfView` | float | `30.0` | Full cone angle **in degrees**; a marker matches within half this angle of the look direction. Validated `> 0` and `<= 360` |
| `MaxDistance` | double | `128.0` | Maximum distance in blocks from the player's eye. Validated `> 0` |
| `ScanInterval` | float | `0.25` | Seconds between scans; the first runs immediately and `0` scans every tick. Validated `0..60` |
| `RunWhile` | condition[] | — | Conditions that must all hold for scanning to continue. Omit it, or give an empty list, to **scan once** |
| `ConditionGrace` | float | `1.0` | Seconds the `RunWhile` conditions have to start holding. Does nothing without `RunWhile`. Validated `0..60` |
| `RevealParticles` | particle[] | — | Particles spawned on a revealed marker's block, seen only by the player who revealed it |

**None of the six is required**, so the interaction is usable with no properties at all — that form
scans once, in a 30° cone, out to 128 blocks. No shipped asset uses the type.

- **`MaxDistance` is not an occlusion test.** The codec says so: a marker behind terrain is still
  found. Distance and angle are the only filters.
- **`ScanInterval` is a cost knob as much as a timing one.** One scan tests every marker in the
  world, so a short interval on a marker-heavy world is expensive — and because the run ends *on* a
  scan, the interval also bounds how long the interaction takes to stop.
- **`ConditionGrace` exists for a specific failure.** Raise it above the windup of whatever
  interaction this runs beside, or that windup ends the run before the conditions ever begin to
  hold. `0` ends the run at the first scan where they do not hold. The grace applies only until the
  conditions **first** hold: after that a later failure ends the run immediately, however much of
  the grace period is left.
- **It reads the *owning* entity, not the interacting one**, and ends `Failed` when that is null or
  is not a player — so this is player-only, and on an item chain it is the holder that is scanned.
  Same distinction [`SendBeacon`](npc-roles.md#sendbeacon) draws.

Revealing is per player, which is why the particles are too.

---

## World Paths
**Package:** `com.hypixel.hytale.server.core.universe.world.path`

Named waypoint paths stored per world (loaded into the `WorldPathConfig` reachable via `world.getWorldPathConfig()`); NPC behaviors use them for patrol routes.

```java
// IPath<Waypoint extends IPathWaypoint>
UUID getId()
String getName()
List<Waypoint> getPathWaypoints()
int length()
Waypoint get(int index)

// IPathWaypoint
int getOrder()
Vector3d getWaypointPosition(ComponentAccessor<EntityStore> accessor)
Rotation3f getWaypointRotation(ComponentAccessor<EntityStore> accessor)
double getPauseTime()
float getObservationAngle()
```

`SimplePathWaypoint(int order, Transform transform)` is the ready-made fixed-position `IPathWaypoint` implementation (position/rotation from the transform; pause time and observation angle 0).

---

## Other World Classes

| Class | Package | Description |
|-------|---------|-------------|
| `ValidationOption` | `server.core.universe.world` | Enum of prefab-validation checks — `PHYSICS`, `BLOCKS`, `BLOCK_STATES`, `ENTITIES`, `BLOCK_FILLER`; consumed by `PrefabBufferValidator.validate` / `validateAllPrefabs` / `validatePrefabsInPath` |
| `INonPlayerCharacter` | `server.core.universe.world.npc` | Minimal NPC handle — `getNPCTypeId()`, `getNPCTypeIndex()`; returned (paired with the entity `Ref`) by `NPCPlugin.spawnNPC` |
| `WorldLocationCondition` | `server.core.universe.world.worldlocationcondition` | Abstract JSON-polymorphic position predicate — `test(World, x, y, z)`; subtypes register on its `CodecMapCodec` `CODEC` (the adventure plugin registers `"NeighbourBlockTags"` → `NeighbourBlockTagsLocationCondition`); consumed by treasure-map objectives, spawn-beacon objectives, and farming spread |

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the world system (verified against `HytaleServer.jar`).

- **`Player is already in a world`** → you called `addPlayer()` for a `PlayerRef` that is already in a world. Fix: remove it from its current world first, or skip the add.
- **`Entity is already in a world!`** → `addEntity()` was called on an entity already added to a world. Fix: add each entity once; check before re-adding.
- **`Entity is already not in a world!`** → a remove was called on an entity that is not in any world. Fix: guard the removal so it only runs for entities currently in a world.
- **`This world has already been shutdown!`** → an operation ran against a world that was already shut down. Fix: stop touching the world reference after shutdown.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
