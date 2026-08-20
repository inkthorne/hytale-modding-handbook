---
title: "Player API"
description: "Work with Hytale players in Java — the fluent Message builder for chat text, formatting and translations; connection, chat, interaction, craft, and input events; and player permissions."
seo:
  type: TechArticle
---

# Player API

**Doc type:** Java API · **Verified against 0.5.9**

This document covers player-related events and messaging APIs.

## Overview

Implemented across `com.hypixel.hytale.server.core` (messaging) and `com.hypixel.hytale.server.core.event.events.player` (events), and provides:
- A fluent `Message` builder for chat text, formatting, translations, and composition
- Player connection, chat, interaction, craft, and input events
- A keyed `PlayerInteractEvent` exposing the action type, held item, and target
- The `InteractionType` enum categorizing interaction kinds
- An ECS `ChangeGameModeEvent` for intercepting game-mode changes
- A `HiddenPlayersManager` for per-player visibility (vanish/spectator systems)

> **See also:** To put a player into a top-down / side-scroller / custom view (the per-player
> camera state), see [Camera Control](camera.md) — and reset it on `PlayerDisconnectEvent`.

## Architecture
```
Messaging
└── Message ──▶ FormattedMessage (wire format)

Player Events  (com.hypixel.hytale.server.core.event.events.player)
├── PlayerConnectEvent / PlayerDisconnectEvent / PlayerReadyEvent
├── PlayerChatEvent          (keyed by String)
├── PlayerInteractEvent      (keyed by String)
│   └── InteractionType (action category)
└── PlayerCraft / Mouse / SetupConnect / world add-remove events

ECS Events
└── ChangeGameModeEvent ──▶ GameMode

Player-scoped managers
└── HiddenPlayersManager (visibility)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Message` | `server.core` | Fluent chat-message builder (formatting, translations, composition) |
| `HiddenPlayersManager` | `server.core.entity.entities.player` | Per-player visibility control |
| `PlayerInteractEvent` | `server.core.event.events.player` | Keyed event fired on player interactions |
| `InteractionType` | `protocol` | Enum of interaction kinds returned by `getActionType()` |
| `ChangeGameModeEvent` | `server.core.event.events.ecs` | Cancellable ECS event for game-mode changes |

## Message
**Package:** `com.hypixel.hytale.server.core`

Create and format chat messages.

### Static Factory Methods
```java
Message.raw(String text)           // Plain text message
Message.translation(String key)    // Translated message (i18n key)
Message.parse(String text)         // Parse formatted text
Message.empty()                    // Empty message
Message.join(Message... messages)  // Concatenate messages
```

### Formatting (Fluent API)
All formatting methods return `Message` for chaining:
```java
Message bold(boolean bold)
Message italic(boolean italic)
Message monospace(boolean mono)
Message color(String hexColor)       // e.g., "#FF0000"
Message color(Color awtColor)
Message link(String url)
```

### Parameters (for translations)
```java
Message param(String key, String value)
Message param(String key, boolean value)
Message param(String key, int value)
Message param(String key, long value)
Message param(String key, float value)
Message param(String key, double value)
Message param(String key, Message value)
```

### Composition
```java
Message insert(Message child)
Message insert(String text)
Message insertAll(Message... children)
Message insertAll(List<Message> children)
```

### Getters
```java
String getRawText()
String getMessageId()
String getColor()
List<Message> getChildren()
String getAnsiMessage()
FormattedMessage getFormattedMessage()  // Internal protocol format (see note below)
```

> **`getRawText()` and `getMessageId()` are mutually exclusive** — exactly one is set,
> depending on how the `Message` was built. `Message.raw(text)` stores `text` in `rawText`
> (so `getRawText()` returns it, `getMessageId()` is `null`); `Message.translation(key)`
> stores `key` in `messageId` (so `getMessageId()` returns it, `getRawText()` is `null`).
> This matters when inspecting a `Message` you didn't build: an entity's
> `DisplayNameComponent.getDisplayName()` is a **translation**, so read `getMessageId()`
> (then resolve it server-side — see [i18n: resolving a key to text](i18n.md#resolving-a-key-to-text-server-side)), not `getRawText()`.

### FormattedMessage (Internal)

**Package:** `com.hypixel.hytale.protocol`

`FormattedMessage` is the wire-format representation used for network transmission. It contains the same information as `Message` but in a protocol-friendly structure. Generally, you should use the `Message` class for all messaging operations - `FormattedMessage` is primarily for internal/advanced use cases.

### Simple Message
```java
playerRef.sendMessage(Message.raw("Hello, World!"));
```

### Formatted Message
```java
Message msg = Message.raw("Important: ")
    .bold(true)
    .color("#FF0000")
    .insert(Message.raw("You have mail!").italic(true));
playerRef.sendMessage(msg);
```

### Translation with Parameters
```java
Message msg = Message.translation("welcome.player")
    .param("name", playerRef.getUsername())
    .param("count", 5);
playerRef.sendMessage(msg);
```

### Joining Messages
```java
Message combined = Message.join(
    Message.raw("Score: ").bold(true),
    Message.raw("100").color("#00FF00"),
    Message.raw(" points")
);
```

### Broadcast to World
```java
world.sendMessage(Message.raw("Server announcement!"));
```

---

## HiddenPlayersManager
**Package:** `com.hypixel.hytale.server.core.entity.entities.player`

Manages player visibility - allows hiding players from each other. Useful for vanish systems, spectator modes, or game-specific visibility rules.

### Getting the Manager
```java
HiddenPlayersManager manager = playerRef.getHiddenPlayersManager();
```

### Methods
```java
void hidePlayer(UUID uuid)          // Hide a player from this player
void showPlayer(UUID uuid)          // Show a previously hidden player
boolean isPlayerHidden(UUID uuid)   // Check if a player is hidden
```

### Usage Example
```java
// Vanish system - hide admin from all other players
public void vanishPlayer(PlayerRef adminRef, World world) {
    UUID adminUuid = adminRef.getUuid();

    for (PlayerRef otherRef : world.getPlayerRefs()) {
        if (!otherRef.getUuid().equals(adminUuid)) {
            HiddenPlayersManager manager = otherRef.getHiddenPlayersManager();
            manager.hidePlayer(adminUuid);
        }
    }
    adminRef.sendMessage(Message.raw("You are now vanished"));
}

// Unvanish - show admin to all players again
public void unvanishPlayer(PlayerRef adminRef, World world) {
    UUID adminUuid = adminRef.getUuid();

    for (PlayerRef otherRef : world.getPlayerRefs()) {
        if (!otherRef.getUuid().equals(adminUuid)) {
            HiddenPlayersManager manager = otherRef.getHiddenPlayersManager();
            manager.showPlayer(adminUuid);
        }
    }
    adminRef.sendMessage(Message.raw("You are now visible"));
}
```

---

## Player Events

**Package:** `com.hypixel.hytale.server.core.event.events.player`

Events related to player connections, interactions, and input.

### Event Summary

| Class | Description | Keyed |
|-------|-------------|-------|
| `PlayerConnectEvent` | Player connects to server | No |
| `PlayerDisconnectEvent` | Player disconnects from server | No |
| `PlayerReadyEvent` | Player is ready (fully loaded) | No |
| `PlayerChatEvent` | Player sends a chat message | Yes (String) |
| `PlayerInteractEvent` | Player interacts with something | Yes (String) |
| `PlayerCraftEvent` | Player crafts an item | No |
| `PlayerMouseButtonEvent` | Player mouse button input | No |
| `PlayerMouseMotionEvent` | Player mouse movement | No |
| `AddPlayerToWorldEvent` | Player added to a world | No |
| `DrainPlayerFromWorldEvent` | Player removed from a world | No |
| `PlayerSetupConnectEvent` | Player setup phase connect | No |
| `PlayerSetupDisconnectEvent` | Player setup phase disconnect | No |
| `RemovedPlayerFromWorldEvent` | Player entity removed from a world; leave-message control | Yes (String, world name) |
| `ChangeGameModeEvent` | Player game mode changes (ECS, cancellable) | No |

**Note:** `PlayerMouseButtonEvent` is client-side only and does not fire on the server.

### Registration Example

```java
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.player.PlayerConnectEvent;

@Override
protected void setup() {
    // Non-keyed event: use register()
    getEventRegistry().register(PlayerConnectEvent.class, event -> {
        event.getPlayerRef().sendMessage(Message.raw("Welcome!"));
    });
}
```

---

## PlayerInteractEvent

**Package:** `com.hypixel.hytale.server.core.event.events.player`

Fired when a player interacts with blocks, entities, items, or triggers game actions. This is a **keyed event** where the key is the interaction ID string.

### Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getActionType()` | `InteractionType` | The type of interaction performed |
| `getItemInHand()` | `ItemStack` | The item the player was holding |
| `getTargetBlock()` | `Vector3i` | Block position interacted with (may be null) |
| `getTargetEntity()` | `Entity` | Entity interacted with (may be null) |
| `getTargetRef()` | `Ref<EntityStore>` | Entity reference for ECS access |
| `getClientUseTime()` | `long` | Client-side timestamp of the interaction |
| `getPlayer()` | `Player` | The player who triggered the interaction |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the event |

### Registration

Since `PlayerInteractEvent` is keyed by String (interaction ID), use `registerGlobal()` to catch all interactions:

```java
getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
    // Handle all interactions
});
```

Or register for a specific interaction key:

```java
getEventRegistry().register(PlayerInteractEvent.class, "some_interaction_id", event -> {
    // Handle specific interaction
});
```

---

## InteractionType

**Package:** `com.hypixel.hytale.protocol`

Enum representing the type of interaction in a `PlayerInteractEvent`. Use `event.getActionType()` to get the interaction type.

### Enum Values by Category

**Player Input Actions:**

| Value | Description |
|-------|-------------|
| `Primary` | Primary action (left click / attack) |
| `Secondary` | Secondary action (right click / use) |
| `Ability1` | First ability slot |
| `Ability2` | Second ability slot |
| `Ability3` | Third ability slot |

**Object Interactions:**

| Value | Description |
|-------|-------------|
| `Use` | Using an object |
| `Pick` | Picking/selecting a target |
| `Pickup` | Picking up an item |

**Collision Events:**

| Value | Description |
|-------|-------------|
| `CollisionEnter` | Entity enters collision |
| `CollisionLeave` | Entity leaves collision |
| `Collision` | Ongoing collision |

**Inventory Events:**

| Value | Description |
|-------|-------------|
| `SwapTo` | Swapping to a slot |
| `SwapFrom` | Swapping from a slot |
| `Held` | Item held in main hand |
| `HeldOffhand` | Item held in offhand |
| `Equipped` | Item equipped |

**Projectile Events:**

| Value | Description |
|-------|-------------|
| `ProjectileSpawn` | Projectile created |
| `ProjectileHit` | Projectile hit target |
| `ProjectileMiss` | Projectile missed |
| `ProjectileBounce` | Projectile bounced |

**Other Events:**

| Value | Description |
|-------|-------------|
| `Death` | Entity death |
| `Dodge` | Dodge action |
| `GameModeSwap` | Game mode changed |
| `EntityStatEffect` | Stat effect applied |
| `Wielding` | Wielding state change |

> **See also:** [Complete InteractionType Reference](interactions.md#interactiontype-enum)

---

## PlayerInteractEvent Usage Examples

### Detecting Primary Attacks

```java
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.player.PlayerInteractEvent;

@Override
protected void setup() {
    getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
        if (event.getActionType() == InteractionType.Primary) {
            event.getPlayer().getPlayerRef().sendMessage(Message.raw("You attacked!"));
        }
    });
}
```

### Checking Held Item During Interaction

```java
getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
    var item = event.getItemInHand();
    if (item != null) {
        event.getPlayer().getPlayerRef().sendMessage(
            Message.raw("Interacted while holding: " + item.getItemType().getName())
        );
    }
});
```

### Cancelling Interactions

```java
getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
    // Prevent all secondary (right-click) actions
    if (event.getActionType() == InteractionType.Secondary) {
        event.setCancelled(true);
        event.getPlayer().getPlayerRef().sendMessage(Message.raw("Secondary actions disabled!"));
    }
});
```

### Filtering Multiple Interaction Types

```java
import java.util.Set;

@Override
protected void setup() {
    Set<InteractionType> combatActions = Set.of(
        InteractionType.Primary,
        InteractionType.Ability1,
        InteractionType.Ability2,
        InteractionType.Ability3
    );

    getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
        if (combatActions.contains(event.getActionType())) {
            // Handle combat-related interactions
            event.getPlayer().getPlayerRef().sendMessage(Message.raw("Combat action: " + event.getActionType()));
        }
    });
}
```

### Detecting Projectile Hits

```java
getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
    if (event.getActionType() == InteractionType.ProjectileHit) {
        var targetEntity = event.getTargetEntity();
        if (targetEntity != null) {
            event.getPlayer().getPlayerRef().sendMessage(
                Message.raw("Your projectile hit an entity!")
            );
        }
    }
});
```

---

## Complete Usage Example

```java
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.player.PlayerConnectEvent;
import com.hypixel.hytale.server.core.event.events.player.PlayerInteractEvent;

@Override
protected void setup() {
    // Non-keyed event: use register()
    getEventRegistry().register(PlayerConnectEvent.class, event -> {
        event.getPlayerRef().sendMessage(Message.raw("Welcome!"));
    });

    // Keyed event: use registerGlobal() to catch ALL interactions
    getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
        event.getPlayer().getPlayerRef().sendMessage(Message.raw("You interacted!"));
    });
}
```

---

## ChangeGameModeEvent

**Package:** `com.hypixel.hytale.server.core.event.events.ecs`

ECS event fired when a player's game mode changes. Extends `CancellableEcsEvent`.

### Methods

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getGameMode()` | `GameMode` | Get the new game mode |
| `setGameMode(GameMode)` | `void` | Change the target game mode |
| `isCancelled()` | `boolean` | Whether the event is cancelled |
| `setCancelled(boolean)` | `void` | Cancel the mode change |

### GameMode Enum

**Package:** `com.hypixel.hytale.protocol`

| Value | Description |
|-------|-------------|
| `Adventure` | Survival/adventure mode |
| `Creative` | Creative mode with unlimited resources |

### Usage Example

Handle game mode changes using an `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.ChangeGameModeEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class GameModeChangeSystem extends EntityEventSystem<EntityStore, ChangeGameModeEvent> {

    public GameModeChangeSystem() {
        super(ChangeGameModeEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       ChangeGameModeEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player != null) {
            player.getPlayerRef().sendMessage(Message.raw("Switching to " + event.getGameMode() + " mode"));

            // Optionally prevent the mode change
            // event.setCancelled(true);

            // Or change to a different mode
            // event.setGameMode(GameMode.Creative);
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

### Registration

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new GameModeChangeSystem());
}
```

> **See also:** [ECS Event Handling](components.md#event-type-registration)

---

## RemovedPlayerFromWorldEvent

**Package:** `com.hypixel.hytale.server.core.event.events.player`

Fired when a player entity has been removed from a world (world switch, disconnect, or drain). It is a **keyed event** — the key is the **world name** — so you can listen per-world or globally. The player arrives as a detached `Holder<EntityStore>`: the entity is already out of the store, so read components from the holder rather than expecting a live `Ref`.

Its headline feature is **leave-message control**:

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getHolder()` | `Holder<EntityStore>` | The removed player entity (detached holder) |
| `getWorld()` | `World` | The world the player was removed from |
| `getLeaveMessage()` | `Message` | The pending leave broadcast (may be null) |
| `setLeaveMessage(Message)` | `void` | Replace the leave broadcast |
| `shouldBroadcastLeaveMessage()` | `boolean` | False once suppressed (or when no message is set) |
| `setBroadcastLeaveMessage(boolean)` | `void` | Suppress (or re-enable) the broadcast |

```java
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.player.RemovedPlayerFromWorldEvent;

// Keyed by world name: registerGlobal catches removals from every world
getEventRegistry().registerGlobal(RemovedPlayerFromWorldEvent.class, event -> {
    if (event.getWorld().getName().equals("lobby")) {
        event.setBroadcastLeaveMessage(false);   // silent leaves in the lobby
    } else {
        event.setLeaveMessage(Message.raw("A hero departs..."));
    }
});
```

---

## Crafting Events

For crafting-related events (`CraftRecipeEvent`, `CraftRecipeEvent.Pre`, `CraftRecipeEvent.Post`), see [inventory.md](inventory.md#crafting-events).

---

## Cosmetics (Player Skins & Emotes)

**Package:** `com.hypixel.hytale.server.core.cosmetics`

A core `JavaPlugin` module manages player appearance — the layered skin parts (face, eyes, eyebrows, ears, hair, underwear, body characteristics), skin-tone gradients, eye colors, and emotes. Plugins use it to build the renderable model for a skin, validate a skin, or enumerate the cosmetic catalog.

### Key Classes

| Class | Description |
|-------|-------------|
| `CosmeticsModule` | Core module; singleton via `CosmeticsModule.get()`. Builds models from skins and validates skins |
| `CosmeticRegistry` | The cosmetic catalog — typed maps of available emotes, eye colors, gradient sets, and body-part assets |
| `Emote` | A single emote: `getId()`, `getName()`, `getAnimation()` |
| `CosmeticType` (enum) | Catalog categories: `EMOTES`, `EMOTES_INGAME`, `SKIN_TONES`, `EYE_COLORS`, `GRADIENT_SETS`, `BODY_CHARACTERISTICS`, `UNDERWEAR`, `EYEBROWS`, `EARS`, `EYES`, `FACE`, `MOUTHS`, … |
| `BodyType` (enum) | `Masculine`, `Feminine` |

> [!NOTE]
> Two different `PlayerSkin` types exist. `CosmeticsModule`'s API takes the **protocol** skin `com.hypixel.hytale.protocol.PlayerSkin` (the wire representation), while `com.hypixel.hytale.server.core.cosmetics.PlayerSkin` is the BSON-backed storage form. Don't mix them.

### CosmeticsModule methods

| Method | Description |
|--------|-------------|
| `static CosmeticsModule get()` | The module singleton |
| `getRegistry()` | The `CosmeticRegistry` catalog |
| `createModel(protocol.PlayerSkin)` | Builds the renderable `Model` (`...asset.type.model.config.Model`) for a skin |
| `createModel(protocol.PlayerSkin, float scale)` | As above, at a given scale |
| `createRandomModel(Random)` | A randomized model |
| `generateRandomSkin(Random)` | A randomized `protocol.PlayerSkin` |
| `validateSkin(protocol.PlayerSkin)` | Throws `CosmeticsModule.InvalidSkinException` if the skin references unknown parts |

### CosmeticRegistry accessors

Each returns a `Map<String, …>` keyed by asset id: `getEmotes()`, `getEmotesInGame()`, `getEyeColors()` (→ `PlayerSkinTintColor`), `getGradientSets()` (→ `PlayerSkinGradientSet`), `getBodyCharacteristics()`, `getUnderwear()`, `getEyebrows()`, `getEars()`, `getEyes()` (→ `PlayerSkinPart`).

```java
CosmeticsModule cosmetics = CosmeticsModule.get();

// Enumerate available emotes
for (Emote emote : cosmetics.getRegistry().getEmotes().values()) {
    System.out.println(emote.getId() + " -> " + emote.getAnimation());
}

// Build a renderable model from a (protocol) skin, validating first
cosmetics.validateSkin(skin);           // throws InvalidSkinException if invalid
Model model = cosmetics.createModel(skin);
```

> [!WARNING]
> Publicly exposed, but no first-party content plugin in build-12 references these classes (only `CosmeticsModule` itself, 8×, from the server bootstrap). Signatures above are verified against `HytaleServer.jar`; the end-to-end "apply this skin to a live player entity" flow is not demonstrated by any inspectable plugin and is intentionally not invented here.

---

## PlayerSkinComponent

**Package:** `com.hypixel.hytale.server.core.modules.entity.player`

The ECS component that holds a player entity's **wire-format skin** (`com.hypixel.hytale.protocol.PlayerSkin`) — the thing the entity tracker actually streams to nearby clients. This is the missing link for the [Cosmetics](#cosmetics-player-skins--emotes) classes above: read it to inspect what a player currently looks like.

```java
PlayerSkinComponent skin = store.getComponent(ref, PlayerSkinComponent.getComponentType());
PlayerSkin current = skin.getPlayerSkin();   // protocol PlayerSkin (wire form)
skin.setNetworkOutdated();                   // force a re-send to viewers next tick
```

| Method | Description |
|--------|-------------|
| `static getComponentType()` | `ComponentType<EntityStore, PlayerSkinComponent>` for store access |
| `new PlayerSkinComponent(protocol.PlayerSkin)` | Wrap a skin in a component |
| `getPlayerSkin()` | The current `protocol.PlayerSkin` |
| `setNetworkOutdated()` | Mark dirty so viewers get a skin update |
| `consumeNetworkOutdated()` | Engine-side dirty-flag read (tracker uses this) |

There is no setter for the skin itself — to change it, `putComponent` a new `PlayerSkinComponent` (the built-in `/model` command does exactly this).

---

## PlayerCreativeSettings

**Package:** `com.hypixel.hytale.server.core.modules.entity.player`

An immutable record of the client's **creative-mode preferences**, sent by the client and stored on the player inside the `PlayerSettings` component (`PlayerSettings.creativeSettings()`). Useful for respecting the player's own builder-tool choices in build-mode plugins.

| Accessor | Type | Meaning |
|----------|------|---------|
| `allowNPCDetection()` | `boolean` | NPCs may notice/target this creative player |
| `respondToHit()` | `boolean` | Creative player still reacts to being hit |
| `placeMode()` | `String` | Block place mode (client default: `"default"`) |
| `creativeInteractionDistance()` | `int` | Extended reach distance in creative |
| `showBuilderToolsNotifications()` | `boolean` | Show builder-tools toast messages |
| `noPhysics()` | `boolean` | Free-flight without collision |

```java
PlayerSettings settings = store.getComponent(ref, PlayerSettings.getComponentType());
PlayerCreativeSettings creative = settings.creativeSettings();
if (creative.noPhysics()) { /* skip collision checks for this builder */ }
```

These are **client-owned** values (re-sent whenever the player changes settings) — treat them as read-only input, not server state to mutate.

---

## Movement Settings (MovementManager & MovementConfig)

**Package:** `com.hypixel.hytale.server.core.entity.entities.player.movement`

Player movement tuning is split across two classes:

- **`MovementConfig`** — a JSON **asset** (jump forces, base/climb/fly speeds, air control, auto-jump, slide and roll parameters). Loaded into an indexed asset map; `"BuiltinDefault"` (`MovementConfig.DEFAULT_ID`) is the stock config, also exposed as `MovementConfig.DEFAULT_MOVEMENT`.
- **`MovementManager`** — the per-player **ECS component** holding the active `MovementSettings` (protocol object) plus the defaults to fall back to. Because player movement is client-authoritative, a change only takes effect when the manager sends the settings packet to the client.

### MovementConfig (asset)

```java
MovementConfig config = MovementConfig.getAssetMap().getAsset("BuiltinDefault");
float jump = config.getJumpForce();
MovementSettings packet = config.toPacket();   // protocol form for MovementManager
```

Every tuning field has a getter — a sampling: `getBaseSpeed()`, `getAcceleration()`, `getJumpForce()`, `getSwimJumpForce()`, `getClimbSpeed()`, `getHorizontalFlySpeed()`, `getVerticalFlySpeed()`, `getForwardSprintSpeedMultiplier()`, `getAirSpeedMultiplier()`, `getMinSlideEntrySpeed()`, `getRollTimeToComplete()`, `getFallDamagePartialMitigationPercent()`. (The full list mirrors the asset's JSON fields — see the auto-generated API reference linked at the bottom of this page.)

### MovementManager (component)

| Method | Description |
|--------|-------------|
| `static getComponentType()` | Component type for store access |
| `getSettings()` | The live `MovementSettings` currently applied |
| `getDefaultSettings()` | The player's baseline settings |
| `setDefaultSettings(MovementSettings, PhysicsValues, GameMode)` | Replace the baseline |
| `applyDefaultSettings()` | Copy defaults → live settings |
| `update(PacketHandler)` | **Push the live settings to the client** |
| `refreshDefaultSettings(Ref, ComponentAccessor)` | Recompute defaults from the player's current state |
| `resetDefaultsAndUpdate(Ref, ComponentAccessor)` | Reset to engine defaults *and* sync the client |

### Changing a player's movement at runtime

This is the exact pattern the built-in mounts plugin uses (apply on mount, reset on dismount):

```java
MovementConfig movementConfig = MovementConfig.getAssetMap().getAsset("MyPlugin_Slowed");
PhysicsValues physics = store.getComponent(ref, PhysicsValues.getComponentType());
Player player = store.getComponent(ref, Player.getComponentType());

MovementManager movement = store.getComponent(ref, MovementManager.getComponentType());
movement.setDefaultSettings(movementConfig.toPacket(), physics, player.getGameMode());
movement.applyDefaultSettings();
movement.update(playerRef.getPacketHandler());   // nothing changes client-side without this

// ...later, restore stock movement:
movement.resetDefaultsAndUpdate(ref, store);
```

> **Temporary speed changes** (potions, stuns) are better done with status effects (`StatModifiers` on `HorizontalSpeed`, or `HorizontalSpeedMultiplier`) — see [Effects & Stats](effects-stats.md). `MovementManager` is for wholesale movement-profile swaps.

---

## PlayerInput

**Package:** `com.hypixel.hytale.server.core.modules.entity.player`

The ECS component where the client's movement packets land before the engine applies them. Each network update is queued as a `PlayerInput.InputUpdate`; the engine's input-processing tick system drains the queue every tick and applies each update to the player's transform/velocity/movement-state components. Plugins that need to intercept or synthesize player motion (the mounts plugin is the canonical example) work with this queue.

| Method | Description |
|--------|-------------|
| `static getComponentType()` | Component type for store access |
| `queue(InputUpdate)` | Append an update to the queue |
| `getMovementUpdateQueue()` | `List<InputUpdate>` — the live queue (inspect, rewrite, or `clear()`) |
| `getMountId()` / `setMountId(int)` | Network ID of the entity the input is steering (mounts) |

### InputUpdate implementations

All are nested in `PlayerInput` and implement `InputUpdate` (`apply(CommandBuffer, ArchetypeChunk, int)` + `clone()`):

| Class | Payload | Meaning |
|-------|---------|---------|
| `AbsoluteMovement` | x, y, z (`double`) | Move to an absolute position |
| `RelativeMovement` | x, y, z (`double`) | Move by a delta |
| `WishMovement` | x, y, z (`double`) | Directional movement intent |
| `SetBody` | `direction()` (`Direction`) | Body facing |
| `SetHead` | `direction()` (`Direction`) | Head facing |
| `SetMovementStates` | `movementStates()` (`MovementStates`) | Sprint/crouch/fly/... flag set |
| `SetRiderMovementStates` | `movementStates()` (`MovementStates`) | Same, for the mounted rider |
| `SetClientVelocity` | `getVelocity()` (`Vector3d`) | Client-reported velocity |

> **New in 0.5.7:** every `InputUpdate` implementation now supports `clone()` (the interface requires it), so a queued update can be deep-copied before you mutate or re-route it — `PlayerInput.clone()` itself relies on this to deep-copy the whole queue when the component is cloned.

```java
// Inspect queued inputs (e.g., in a ticking system that runs before input processing)
PlayerInput input = chunk.getComponent(index, PlayerInput.getComponentType());
for (PlayerInput.InputUpdate update : input.getMovementUpdateQueue()) {
    if (update instanceof PlayerInput.SetMovementStates states
            && states.movementStates().sprinting) {
        // player is asking to sprint this tick
    }
}
```

For the *applied* result of these inputs (the entity's current sprint/crouch/glide flags), read [`MovementStatesComponent`](entities.md#movementstatescomponent).

---

## Persistent Player Data (PlayerConfigData)

**Package:** `com.hypixel.hytale.server.core.entity.entities.player.data`

`PlayerConfigData` is the player's **saved profile** — the codec-backed object persisted to the player's config file. Get it from the full `Player` component: `player.getPlayerConfigData()`. Built-in plugins use it for known recipes, discovered zones, reputation, and active objectives; your plugin can read the same state.

### PlayerConfigData

| Member | Description |
|--------|-------------|
| `getWorld()` / `setWorld(String)` | Name of the world the player saves into |
| `getKnownRecipes()` / `setKnownRecipes(Set<String>)` | Learned crafting recipes |
| `getDiscoveredZones()` / `setDiscoveredZones(Set<String>)` | Map-discovered zone ids |
| `getDiscoveredInstances()` / `setDiscoveredInstances(Set<UUID>)` | Discovered instance UUIDs |
| `getReputationData()` / `setReputationData(Object2IntMap<String>)` | Faction reputation scores |
| `getActiveObjectiveUUIDs()` / `setActiveObjectiveUUIDs(Set<UUID>)` | In-progress objectives |
| `getPerWorldData()` / `getPerWorldData(String)` | Per-world state (creates on demand for the keyed overload) |
| `lastSavedPosition` / `lastSavedRotation` | Public final fields — last persisted transform |
| `markChanged()` | Flag the profile dirty so it gets saved |
| `consumeHasChanged()` | Engine-side dirty-flag read |

> After mutating anything here, call `markChanged()` — persistence is flush-on-dirty, and the collection getters hand you unmodifiable views in some paths (built-ins mutate via the setters or the returned live maps, then mark changed).

### PlayerWorldData

Per-world slice of the profile, from `getPerWorldData(worldName)`:

| Member | Description |
|--------|-------------|
| `getLastPosition()` / `setLastPosition(Transform)` | Where the player last was in this world |
| `getLastMovementStates()` | Saved movement states (`SavedMovementStates`) |
| `setLastMovementStates(MovementStates, boolean)` | Update them from live states |
| `isFirstSpawn()` / `setFirstSpawn(boolean)` | First-ever spawn in this world |
| `getRespawnPoints()` / `setRespawnPoints(PlayerRespawnPointData[])` | Bound respawn points |
| `getDeathPositions()` | Recent death locations (engine keeps the last 5) |
| `addLastDeath(String, Transform, int)` / `removeLastDeath(String)` | Death-position bookkeeping |
| `getUserMapMarkers()` / `getUserMapMarker(String)` / `setUserMapMarkers(...)` | The player's custom map markers |

### PlayerRespawnPointData

One bound respawn point (a bed/waystone-style anchor): `getBlockPosition()` (`Vector3i` of the anchor block), `getRespawnPosition()` (`Vector3d` where the player actually appears), `getName()` / `setName(String)`. Constructed as `new PlayerRespawnPointData(blockPos, respawnPos, name)`. These are what `Player.getRespawnPosition(...)` resolves against.

---

## Container Windows

**Package:** `com.hypixel.hytale.server.core.entity.entities.player.windows`

Windows are the overlay UIs opened through the [`WindowManager`](ui.md) / `PageManager`. Beyond the base classes covered in the [UI docs](ui-api.md), three types matter for chest- and bench-style plugins:

### ContainerBlockWindow

A window backed by an `ItemContainer` that lives on a **block** (chest, treasure pot). Extends `BlockWindow` (which ties the window to block coordinates and auto-closes when the player walks away or the block changes) and implements `ItemContainerWindow`.

```java
// Open a chest-style window on the container block at pos (built-in treasure-chest flow)
ContainerBlockWindow window = new ContainerBlockWindow(
        pos.x, pos.y, pos.z, rotationIndex, blockType, itemContainer);

player.getPageManager().setPageWithWindows(ref, store, Page.Bench, true, window);

window.registerCloseEvent(event -> {
    // e.g. flip the block back to its closed visual state
});
```

| Method | Description |
|--------|-------------|
| `getItemContainer()` | The backing `ItemContainer` |
| `getData()` | The window's JSON payload sent to the client |
| `handleAction(Ref, Store, WindowAction)` | Server-side handling of client window actions |

`registerCloseEvent(Consumer<Window.WindowCloseEvent>)` is inherited from `Window` — use it for cleanup, as above.

### MaterialContainerWindow & MaterialExtraResourcesSection

`MaterialContainerWindow` is the interface implemented by **crafting-style windows** (the built-in bench and hand-crafting windows) that show an "extra resources" strip — the materials pulled from nearby containers:

```java
MaterialExtraResourcesSection getExtraResourcesSection();
void invalidateExtraResources();   // force a refresh of the strip
boolean isValid();
```

`MaterialExtraResourcesSection` is that strip's state: `setExtraMaterials(ItemQuantity[])`, `getItemContainer()` / `setItemContainer(ItemContainer)`, `isValid()` / `setValid(boolean)`, and `toPacket()` (protocol `ExtraResources`). You'll only touch these when building a custom crafting window; for normal crafting flows see [Crafting](items-crafting.md).

---

## Choice Pages

**Package:** `com.hypixel.hytale.server.core.entity.entities.player.pages.choices`

A small framework for **menu pages** — a full-screen list of buttons where each button has requirements (shown-but-locked when unmet) and interactions (what happens on click). The built-in **shop** (`ShopPage`/`ShopElement`), **objective**, and **reputation** systems are all built on it. Use it when you want a data-driven dialog/menu without hand-writing a whole `CustomUIPage`.

| Class | Role |
|-------|------|
| `ChoiceBasePage` | Abstract page (extends `InteractiveCustomUIPage`); renders elements, dispatches clicks |
| `ChoiceElement` | One entry: display/description keys + its interactions and requirements |
| `ChoiceInteraction` | Abstract action run when the element is clicked |
| `ChoiceRequirement` | Abstract gate deciding whether the element can be used |

All four are codec-backed (`CODEC` / `BASE_CODEC`), so element lists can come straight from JSON assets — that's how shop inventories are defined.

### Subclassing

```java
public class MyMenuPage extends ChoiceBasePage {
    public MyMenuPage(PlayerRef playerRef, ChoiceElement[] elements) {
        super(playerRef, elements, "Pages/ShopPage.ui");   // .ui layout to render into
    }
}

public class BroadcastInteraction extends ChoiceInteraction {
    @Override
    public void run(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef) {
        playerRef.sendMessage(Message.raw("You chose wisely."));
    }
}

public class AlwaysAllowed extends ChoiceRequirement {
    @Override
    public boolean canFulfillRequirement(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef) {
        return true;
    }
}
```

- `ChoiceElement` subclasses implement `addButton(UICommandBuilder, UIEventBuilder, String, PlayerRef)` to render themselves; `canFulfillRequirements(store, ref, playerRef)` AND-combines the element's requirements.
- `ChoiceBasePage.handleDataEvent(...)` receives a `ChoicePageEventData` whose `getIndex()` is the clicked element's index, checks requirements, then runs every `ChoiceInteraction` on that element — you get that flow for free by subclassing.
- Open it like any custom page: `player.getPageManager().openCustomPage(ref, store, new MyMenuPage(playerRef, elements))` — see [PageManager](ui-api.md#pagemanager).

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 color parser (verified against `HytaleServer.jar`).

- **`Hex color must start with '#'`** → you passed a hex string without the leading `#` to `Message.color(String hexColor)`. Fix: include it, e.g. `.color("#FF0000")` (see [Message](#message)).
- **`Invalid color format, expected: #RGBA, #RRGGBBAA, rgba(#RGB,A), rgba(#RRGGBB,A) or rgba(R,G,B,A)`** → the color string passed to `Message.color(...)` didn't match a supported form. Fix: use a documented hex form such as `#RRGGBB` (e.g. `.color("#00FF00")`).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
