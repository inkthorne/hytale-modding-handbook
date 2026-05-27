---
title: "Player API"
description: "Work with Hytale players in Java — the fluent Message builder for chat text, formatting and translations; connection, chat, interaction, craft, and input events; and player permissions."
seo:
  type: TechArticle
---

# Player API

**Doc type:** Java API · **Verified against 0.5.1**

This document covers player-related events and messaging APIs.

## Overview

Implemented across `com.hypixel.hytale.server.core` (messaging) and `com.hypixel.hytale.server.core.event.events.player` (events), and provides:
- A fluent `Message` builder for chat text, formatting, translations, and composition
- Player connection, chat, interaction, craft, and input events
- A keyed `PlayerInteractEvent` exposing the action type, held item, and target
- The `InteractionType` enum categorizing interaction kinds
- An ECS `ChangeGameModeEvent` for intercepting game-mode changes
- A `HiddenPlayersManager` for per-player visibility (vanish/spectator systems)

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
            event.getPlayer().sendMessage(Message.raw("You attacked!"));
        }
    });
}
```

### Checking Held Item During Interaction

```java
getEventRegistry().registerGlobal(PlayerInteractEvent.class, event -> {
    var item = event.getItemInHand();
    if (item != null) {
        event.getPlayer().sendMessage(
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
        event.getPlayer().sendMessage(Message.raw("Secondary actions disabled!"));
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
            event.getPlayer().sendMessage(Message.raw("Combat action: " + event.getActionType()));
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
            event.getPlayer().sendMessage(
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
        event.getPlayer().sendMessage(Message.raw("You interacted!"));
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
            player.sendMessage(Message.raw("Switching to " + event.getGameMode() + " mode"));

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

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 color parser (verified against `HytaleServer.jar`).

- **`Hex color must start with '#'`** → you passed a hex string without the leading `#` to `Message.color(String hexColor)`. Fix: include it, e.g. `.color("#FF0000")` (see [Message](#message)).
- **`Invalid color format, expected: #RGBA, #RRGGBBAA, rgba(#RGB,A), rgba(#RRGGBB,A) or rgba(R,G,B,A)`** → the color string passed to `Message.color(...)` didn't match a supported form. Fix: use a documented hex form such as `#RRGGBB` (e.g. `.color("#00FF00")`).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
