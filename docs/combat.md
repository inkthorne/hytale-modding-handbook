---
title: "Combat API"
description: "Handle Hytale combat in Java — the Damage ECS event and DamageEventSystem, damage source types (entity, environment, projectile, command), and JSON-driven combat config."
seo:
  type: TechArticle
---

# Combat API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.6.3**

This document covers damage events, combat systems, and kill feed customization.

> **See also:** For JSON-based combat configuration (damage interactions, effects, target selectors), see [Interactions API Reference](interactions.md#reference). For effect and stat asset definitions, see [Effects & Stats Reference](effects-stats.md).

> **Player-vs-player is gated per world, not globally.** Damage between players is enabled by
> the `IsPvpEnabled` flag in each world's `config.json` (default `false` on the shipped
> worlds). The `Damage` events and systems below fire only once PvP is enabled for that world.
> See [Universes & Save Format → per-world `config.json`](universe-saves.md#the-per-world-configjson).

## Overview

Implemented mainly in `com.hypixel.hytale.server.core.modules.entity.damage` (with JSON-driven combat config) and provides:
- The `Damage` ECS event and `DamageEventSystem` base class for handling damage
- Damage source types (`EntitySource`, `EnvironmentSource`, `ProjectileSource`, `CommandSource`)
- `DamageCause` constants and `DamageDataComponent` for damageable entities
- Kill feed events (`KillFeedEvent.Display`, `KillerMessage`, `DecedentMessage`)
- A component-based `KnockbackComponent` system with armor/wielding reduction
- JSON config for stats-on-hit, blocking, parry, and knockback

## Architecture
```
Combat
├── Damage Pipeline
│   ├── Damage (event, fires on victim) + DamageEventSystem
│   ├── Damage.Source → EntitySource / EnvironmentSource / ProjectileSource / CommandSource
│   ├── DamageCause (PHYSICAL, FALL, DROWNING, ...)
│   └── DamageDataComponent (marks damageable entities)
├── Kill Feed (KillFeedEvent)
│   ├── KillerMessage / DecedentMessage / Display
├── Knockback
│   ├── KnockbackComponent (temporary, timer-driven)
│   ├── KnockbackSystems.ApplyKnockback / ApplyPlayerKnockback
│   └── DamageSystems.ArmorKnockbackReduction / WieldingKnockbackReduction
└── JSON Combat Config (Server/Item/Interactions)
    ├── EntityStatsOnHit
    ├── Blocking / Wielding (DamageModifiers, StaminaCost)
    └── Knockback parameters
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Damage` | `server.core.modules.entity.damage` | ECS event fired when damage occurs; cancellable |
| `DamageEventSystem` | `server.core.modules.entity.damage` | Base class for handling Damage events |
| `Damage.Source` | `server.core.modules.entity.damage` | Interface for damage sources |
| `Damage.EntitySource` | `server.core.modules.entity.damage` | Source when damage comes from an entity |
| `DamageCause` | `server.core.modules.entity.damage` | Asset type for damage cause (FALL, PHYSICAL, etc.) |
| `DamageDataComponent` | `server.core.entity.damage` | Component on entities that can receive damage |
| `KillFeedEvent` | `server.core.modules.entity.damage.event` | Container for kill feed events (Display/KillerMessage/DecedentMessage) |
| `KnockbackComponent` | `server.core.entity.knockback` | Temporary component managing knockback state |

## Damage Events (DamageEventSystem)

Handle damage events when entities receive damage. Extend `DamageEventSystem` (not raw `EntityEventSystem`).

**Package:** `com.hypixel.hytale.server.core.modules.entity.damage`

### Key Classes

| Class | Description |
|-------|-------------|
| `Damage` | ECS event fired when damage occurs. Extends `CancellableEcsEvent` |
| `DamageEventSystem` | Abstract base class for handling Damage events |
| `Damage.Source` | Interface for damage sources |
| `Damage.EntitySource` | Source when damage comes from an entity (player/mob) |
| `Damage.EnvironmentSource` | Source for environmental damage (fall, drowning) |
| `Damage.ProjectileSource` | Source for projectile damage (arrows) |
| `Damage.CommandSource` | Source for damage from commands |
| `DamageCause` | Asset type for damage cause (FALL, DROWNING, PHYSICAL, etc.) |
| `DamageDataComponent` | Component on entities that can receive damage |

---

## Damage Class

The main ECS event fired when an entity takes damage.

### Methods

```java
// Who/what caused the damage
Damage.Source getSource()
void setSource(Damage.Source)

// Damage amount — getAmount() is the live, modifiable value; getInitialAmount() is a final field
// seeded from the same constructor argument, so it survives every setAmount() a system applies
float getAmount()
void setAmount(float)
float getInitialAmount()

// Damage cause
DamageCause getCause()
int getDamageCauseIndex()
void setDamageCauseIndex(int)

// The death message this damage would produce (used by DeathComponent / the kill feed)
Message getDeathMessage(Ref<EntityStore>, ComponentAccessor<EntityStore>)

// Cancellable (final methods on CancellableEcsEvent)
boolean isCancelled()
void setCancelled(boolean)
```

`Damage` also implements `IMetaStore<Damage>`, so per-hit extras ride along as `MetaKey`s rather than
fields: `Damage.HIT_LOCATION` (`Vector4d`), `HIT_ANGLE`, `IMPACT_PARTICLES`, `IMPACT_SOUND_EFFECT`,
`PLAYER_IMPACT_SOUND_EFFECT`, `CAMERA_EFFECT`, `DEATH_ICON`, `BLOCKED`, `STAMINA_DRAIN_MULTIPLIER`,
`CAN_BE_PREDICTED` and `KNOCKBACK_COMPONENT`. `DeathSystems.KillFeed`, for instance, reads
`deathInfo.getIfPresentMetaObject(Damage.DEATH_ICON)` to seed `KillFeedEvent.Display.getIcon()`.

### Important Notes

1. **Event fires on VICTIM**: The Damage event is invoked on the entity receiving damage, not the attacker
2. **Getting the attacker**: Use `Damage.EntitySource.getRef()` to get the attacker's entity reference
3. **getQuery() required**: Must return a valid query — **never `null`**, which NPEs at registration. Use `DamageDataComponent.getComponentType()` (or `Archetype.empty()` to match every entity)
4. **Extend DamageEventSystem**: Use the provided base class, not raw `EntityEventSystem<EntityStore, Damage>`

---

## Damage Source Types

### Damage.Source (Interface)

Base interface for all damage sources. Its one member is a default
`getDeathMessage(Damage, Ref<EntityStore>, ComponentAccessor<EntityStore>)`, which each subtype
overrides to phrase the kill; `Damage.NULL_SOURCE` is the no-attacker instance.

### Damage.EntitySource

Source when damage comes from another entity (player or mob).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getRef()` | `Ref<EntityStore>` | Reference to the attacking entity (the attacker for melee, the shooter for projectiles) |

> **`ProjectileSource extends EntitySource`** (verified in the jar). A single
> `if (source instanceof Damage.EntitySource es)` therefore catches **both melee and
> projectile** kills, and `es.getRef()` returns the **attacker/shooter** in both cases —
> which is what you want for attributing kills in a shooter. Only add a separate
> [`Damage.ProjectileSource`](#damageprojectilesource) branch if you need the projectile
> entity itself; check it **before** the `EntitySource` branch (subtype first).

### Damage.EnvironmentSource

Source for environmental damage (fall damage, drowning, lava, etc.).

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getType()` | `String` | The free-form environment tag the source was constructed with (`new Damage.EnvironmentSource(String)`). The engine's explosion source, for example, is `ExplodeInteraction.DAMAGE_SOURCE_EXPLOSION` = `new Damage.EnvironmentSource("explosion")`. It is **not** the `DamageCause` id — read the cause from `event.getCause()` |

### Damage.ProjectileSource

Source for projectile damage (arrows, thrown items). **Extends [`Damage.EntitySource`](#damageentitysource)**, so it inherits `getRef()` (the shooter) and adds `getProjectile()`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getRef()` | `Ref<EntityStore>` | The shooter (inherited from `EntitySource`) |
| `getProjectile()` | `Ref<EntityStore>` | The projectile entity (arrow, etc.) |

### Damage.CommandSource

Source for damage inflicted via commands.

---

## DamageCause

**Package:** `com.hypixel.hytale.server.core.modules.entity.damage`

Asset type representing the cause/type of damage. Returned by `Damage.getCause()`.

### Predefined Constants (all `@Deprecated`)

> **⚠️ All eight `DamageCause.*` static fields carry `@Deprecated` + `@Nullable`** (a bare
> `@Deprecated`; the 0.6.3 jar records no `since` element on it). `DamageCause`
> is now an asset-store-backed type — the causes live as JSON assets under `Server/Entity/Damage/`,
> and the static convenience fields are deprecated in favor of looking the cause up by id. See
> [Obtaining a cause](#obtaining-a-cause-non-deprecated) below for the current API.

```java
@Deprecated static DamageCause PHYSICAL       // Melee/physical attacks
@Deprecated static DamageCause PROJECTILE     // Arrow/thrown item damage
@Deprecated static DamageCause COMMAND        // Damage from commands
@Deprecated static DamageCause DROWNING       // Underwater suffocation
@Deprecated static DamageCause ENVIRONMENT    // Environmental hazards (lava, etc.)
@Deprecated static DamageCause FALL           // Fall damage
@Deprecated static DamageCause OUT_OF_WORLD   // Void damage
@Deprecated static DamageCause SUFFOCATION    // Block suffocation
```

> **Beyond being deprecated, these are *not* compile-time constants — they are runtime asset
> lookups.** The fields are `public static` but **non-final**, populated by the asset system, which
> finishes loading *after* plugin `setup()`. They are **`null` until then**. Referencing one (or any
> looked-up cause) in a `static final` field, at class-load, or at `setup()` time throws
> `ExceptionInInitializerError` / `NullPointerException`. Resolve and build `Damage` lazily, at
> gameplay time.

### Obtaining a cause (non-deprecated)

Look the cause up by id from the asset map instead of referencing the deprecated static field. The id
is the asset filename — e.g. `Physical`, `Fall`, `Drowning`, `Projectile`, `Environment`, `Command`,
`OutOfWorld`, `Suffocation` (plus `Bludgeoning`, `Elemental`, `Environmental`, `Fire`, `Ice`, `Poison`, `Slashing` — the files under `Server/Entity/Damage/`).

> **Gotcha:** the map is an `IndexedLookupTableAssetMap`, which exposes `getIndex(String)` and
> `getAsset(int)` but **no `getAsset(String)`** (unlike some other asset maps). Go id → index → cause:

```java
// id -> index -> cause
int idx = DamageCause.getAssetMap().getIndex("Command");
DamageCause cause = DamageCause.getAssetMap().getAsset(idx);
```

`Damage` also has an **index-based constructor**, so for construction you can skip resolving the
object entirely (still lazily, once assets are loaded):

```java
// public Damage(Damage.Source, int causeIndex, float amount)
int idx = DamageCause.getAssetMap().getIndex("Command");
Damage d = new Damage(Damage.NULL_SOURCE, idx, amount);
```

> `DeathComponent.getDeathCause()` returns the cause of a death — handy for ignoring admin/`Command`
> kills in scoring. Prefer comparing by `getId()` (or index) over `==` against the deprecated static.

### Methods
```java
String getId()
String getInherits()              // Parent cause for inheritance
String getAnimationId()           // Animation to play on damage
String getDeathAnimationId()      // Animation to play on death
boolean isDurabilityLoss()        // Does this cause item durability loss?
boolean isStaminaLoss()           // Does this cause stamina loss?
boolean doesBypassResistances()   // Does this ignore damage resistances?
```

### Usage Example
```java
@Override
public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                   Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                   Damage event) {
    DamageCause cause = event.getCause();

    // Compare by id rather than `== DamageCause.FALL` (the statics are deprecated).
    String causeId = cause.getId();
    if ("Fall".equals(causeId)) {
        // Handle fall damage specially
        event.setCancelled(true);  // No fall damage
    } else if ("Drowning".equals(causeId)) {
        // Reduce drowning damage
        System.out.println("Drowning damage: " + event.getAmount());
    }
}
```

---

## Creating a Damage Handler

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.damage.DamageDataComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

public class MyDamageSystem extends DamageEventSystem {

    public MyDamageSystem() {
        super();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       Damage event) {
        // NOTE: This fires on the VICTIM entity (receiving damage)

        Damage.Source source = event.getSource();
        if (source instanceof Damage.EntitySource entitySource) {
            // Get the attacker's entity reference
            Ref<EntityStore> attackerRef = entitySource.getRef();

            // Check if attacker is a player
            Player attacker = store.getComponent(attackerRef, Player.getComponentType());
            if (attacker != null) {
                attacker.getPlayerRef().sendMessage(Message.raw("You hit something for " + event.getAmount() + " damage!"));
            }
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        // Match entities that can receive damage
        return DamageDataComponent.getComponentType();
    }
}
```

### Registering the Damage System

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new MyDamageSystem());
}
```

---

## DamageDataComponent

**Package:** `com.hypixel.hytale.server.core.entity.damage`

Component attached to entities that can receive damage. Use this in your query to match damageable entities.

```java
@Override
public Query<EntityStore> getQuery() {
    return DamageDataComponent.getComponentType();
}
```

---

## KillFeedEvent

**Package:** `com.hypixel.hytale.server.core.modules.entity.damage.event`

Container class for kill feed related events. Contains three nested event classes that fire when an entity is killed.

### KillFeedEvent.Display

ECS event fired to display the kill in the kill feed UI. Extends `CancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDamage()` | `Damage` | The damage that caused the kill |
| `getBroadcastTargets()` | `List<PlayerRef>` | Players who will see this kill feed entry |
| `getIcon()` | `String` | Icon to display in kill feed |
| `setIcon(String)` | `void` | Change the display icon |
| `isCancelled()` | `boolean` | Whether display is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the display |

### KillFeedEvent.KillerMessage

ECS event fired to send a message to the killer. Extends `CancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDamage()` | `Damage` | The damage that caused the kill |
| `getTargetRef()` | `Ref<EntityStore>` | Reference to the killed entity |
| `getMessage()` | `Message` | Message to show the killer |
| `setMessage(Message)` | `void` | Change the message |
| `isCancelled()` | `boolean` | Whether message is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the message |

### KillFeedEvent.DecedentMessage

ECS event fired to send a message to the deceased (victim). Extends `CancellableEcsEvent`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDamage()` | `Damage` | The damage that caused death |
| `getMessage()` | `Message` | Message to show the deceased |
| `setMessage(Message)` | `void` | Change the message |
| `isCancelled()` | `boolean` | Whether message is cancelled |
| `setCancelled(boolean)` | `void` | Cancel or uncancel the message |

---

## KillFeedEvent Usage

Handle kill feed events using `EntityEventSystem`:

```java
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.damage.event.KillFeedEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

// Customize message shown to killer
public class KillerMessageSystem extends EntityEventSystem<EntityStore, KillFeedEvent.KillerMessage> {

    public KillerMessageSystem() {
        super(KillFeedEvent.KillerMessage.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       KillFeedEvent.KillerMessage event) {
        // Customize the kill message
        event.setMessage(Message.raw("You eliminated a target!"));
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}

// Customize or suppress kill feed display
public class KillFeedDisplaySystem extends EntityEventSystem<EntityStore, KillFeedEvent.Display> {

    public KillFeedDisplaySystem() {
        super(KillFeedEvent.Display.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       KillFeedEvent.Display event) {
        // Change the icon or cancel the display
        event.setIcon("custom_kill_icon");

        // Or suppress kill feed entirely
        // event.setCancelled(true);
    }

    @Override
    public Query<EntityStore> getQuery() {
        // Match every entity — this is the query the engine's own DeathSystems.KillFeed uses.
        return Archetype.empty();
    }
}
```

> **Never return `null` from `getQuery()`.** `QuerySystem.getQuery()` is annotated `@Nullable`, but
> `ComponentRegistry.registerSystem(...)` calls `query.validateRegistry(this)` with no null check, so a
> null query **throws an NPE at registration**, and the dispatch paths that *do* null-check treat a
> null query as "skip this system" — never as "match everything". The match-everything query is
> `Archetype.empty()` (`com.hypixel.hytale.component.Archetype`).

### Registration

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new KillerMessageSystem());
    getEntityStoreRegistry().registerSystem(new KillFeedDisplaySystem());
}
```

### Kill Feed Event Flow

`DeathSystems.KillFeed` (an `OnDeathSystem` with an `Archetype.empty()` query) drives the sequence
when an entity is killed:

1. `KillFeedEvent.KillerMessage` — invoked **on the killer**, and **only** when the killing `Damage`
   has a `Damage.EntitySource` whose ref is still valid. Cancelling it aborts the whole sequence.
2. `KillFeedEvent.DecedentMessage` — invoked **on the victim**. Cancelling it aborts the sequence.
3. `KillFeedEvent.Display` — invoked **on the victim**, then broadcast as a `KillFeedMessage` packet
   to `getBroadcastTargets()` (initialised to every `PlayerRef` in the world).

> **Gotcha:** if the killer message *and* the decedent message both end up `null`, the engine returns
> before step 3 — so a `Display` handler never runs for a kill nobody has a message for. Note also
> that a `KillerMessage` system's query is matched against the **killer**, which is why
> `Player.getComponentType()` there means "only player killers".

---

## Reacting to Death & Respawn

`KillFeedEvent` is the hook for *messaging* (kill-feed entry, killer/victim notifications) — not the
hook for reacting to the death/respawn lifecycle itself. The engine signals death and respawn by
**adding and removing a component**, not by firing an event:

- On death, the engine **adds** `DeathComponent`
  (`com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent`) to the entity.
- On respawn, it **removes** that component.

Observe those transitions with a `RefChangeSystem<EntityStore, DeathComponent>`. Two engine base
classes (in `...modules.entity.damage`) make this turnkey by hardcoding the component type and leaving
exactly one callback for you to override:

| Base class | Override | Fires |
|------------|----------|-------|
| `DeathSystems.OnDeathSystem` | `onComponentAdded(...)` | when the entity dies |
| `RespawnSystems.OnRespawnSystem` | `onComponentRemoved(...)` | when the entity respawns |

Both extend `RefChangeSystem` (`com.hypixel.hytale.component.system.RefChangeSystem`), which is a
`QuerySystem` — so you must supply `getQuery()`. A `ComponentType` is usable as a `Query`, so returning
`Player.getComponentType()` scopes the system to players (this is exactly what the engine's own
`ResetPlayerRespawnSystem` does).

```java
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.RespawnSystems;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

// Fires the moment a player dies.
public class OnPlayerDeath extends DeathSystems.OnDeathSystem {
    @Override
    public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death,
                                 Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        // The Damage that killed them is on the component; the killer (if any) is its source.
        // Damage dmg = death.getDeathInfo();
        // if (dmg.getSource() instanceof Damage.EntitySource es) { Ref<EntityStore> killer = es.getRef(); }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}

// Fires the moment a player respawns.
public class OnPlayerRespawn extends RespawnSystems.OnRespawnSystem {
    @Override
    public void onComponentRemoved(Ref<EntityStore> ref, DeathComponent death,
                                   Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        // e.g. reset inventory / grant a loadout here (see inventory.md)
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }
}
```

Register them from `setup()` like any other system:

```java
getEntityStoreRegistry().registerSystem(new OnPlayerDeath());
getEntityStoreRegistry().registerSystem(new OnPlayerRespawn());
```

> The killer/victim refs are reconstructed from the `Damage` (see [Damage Source Types](#damage-source-types)):
> `getTargetRef()` on `KillFeedEvent.KillerMessage` is the **victim**, and `Damage.EntitySource.getRef()`
> is the **attacker**. `DeathComponent.getDeathInfo()` gives you the same `Damage` from inside an
> `OnDeathSystem`.

To control *where* a player respawns, override the world's spawn provider rather than teleporting
manually — see [world.md → Controlling Respawn Location](world.md#controlling-respawn-location).

### The death screen *is* the respawn trigger

A natural instinct is to replace Hytale's death screen with a custom page (custom respawn UI, a
death-cam, a "you died" overlay with your own button). **As of 0.6.3 this is not cleanly moddable**,
because the engine's death screen and the respawn action are the same object.

The flow, for a player whose `DeathComponent` was just added:

- `DeathSystems$PlayerDeathScreen` (an `OnDeathSystem`, query `Player` **and** `TransformComponent`)
  runs. As of 0.6.3 it first settles the **game-mode-on-death / hardcore** bookkeeping:
  - It reads `World.getGameModeTypeOnDeath()` — the world's `DeathConfig.GameModeTypeOnDeath`,
    falling back to the server-wide `HytaleServerConfig.Defaults.GameModeTypeOnDeath`. **If that does
    not name a real `GameModeType` asset, none of the hardcore logic runs** and the ordinary respawn
    screen opens (a `null` is silent; a non-null unknown id logs
    `GameModeTypeOnDeath %s is not a known GameModeType`).
  - Otherwise a life is burned. `HytaleServerConfig.Defaults` also gained `HardcoreMode`
    (`None` / `PerPlayer` / `Global`) and `HardcoreLives`. `PerPlayer` decrements the `PlayerLives`
    component (`com.hypixel.hytale.server.core.modules.entity.component.PlayerLives`); `Global`
    decrements the shared pool held in the `HardcoreState` universe resource (see
    [universe-saves.md → Universe resources](universe-saves.md#universe-resources)). Two shortcuts
    matter: `HardcoreMode: None` reports **zero lives left immediately** (so *every* death takes the
    permadeath branch below), and a player whose effective `GameMode` is not `Adventure` reports
    `-1` and never permadies.
  - **Lives left ≠ 0** → the ordinary respawn screen, carrying the remaining count.
    **Lives left == 0** → `GameModeTypes.enterOnDeath(ref, store, gameModeTypeId)` removes the
    `DeathComponent` and moves the player into that game-mode type (the id the server writes for
    hardcore saves is `HardcoreSpectator`; see
    [player.md → Spectator Mode](player.md#spectator-mode)).
- Then, **if `DeathComponent.isShowDeathMenu()` is true**, it opens the death screen via
  `player.getPageManager().openCustomPage(ref, store, page)`, where `page` comes from one of
  `RespawnPage`'s static factories (the constructor is private as of 0.6.3):
  - `RespawnPage.forRespawn(playerRef, deathMessage, displayDataOnDeathScreen, deathItemLoss, livesRemaining)`
    — the normal screen (a `livesRemaining` greater than 0 adds a "lives remaining" note), or
  - `RespawnPage.forPermadeath(playerRef, deathMessage, displayDataOnDeathScreen, deathItemLoss, permadeathMessage)`
    — used **only** when the entered `GameModeType` defines a `DeathScreenMessage` (or a global
    hardcore game-over is active). It hides the Respawn button and shows a Spectate button whose only
    action **closes the page without respawning**. If the game-mode type defines no such message,
    **no screen opens at all** — the player simply wakes up inside the new game-mode type.
- **`RespawnPage` *is* the respawn trigger.** Both exit paths of the normal (`forRespawn`) page call
  `DeathComponent.respawn(...)`:
  - the **Respawn button** (`handleDataEvent`, action `"Confirm"`), and
  - **`RespawnPage.onDismiss(...)`** — if the entity still has a `DeathComponent`.

Because `PageManager` holds a **single** current page and `openCustomPage(...)` fires the **previous
page's `onDismiss`** before showing the new one (see [ui-api.md → Live updates & page replacement](ui-api.md#live-updates--page-replacement)),
**replacing the death screen respawns the player out from under your page.** You cannot swap in your
own death/respawn page.

**Can you suppress it instead?** `showDeathMenu` is the off-switch, but it is impractical to reach:

- It **defaults `true`** (a field initializer on `DeathComponent`).
- It is **not configurable from an asset** — `DeathConfig` has no field for it, and jar-wide **only
  `DeathComponent` itself** calls `setShowDeathMenu`. (`DeathComponent.CODEC` does carry a
  `ShowDeathMenu` key, but that codec only serialises an already-dead entity's component into the
  save; there is no authoring surface that creates the component with it set.)
- You would have to set it `false` **before `PlayerDeathScreen` runs**. By default engine systems
  run before plugin-registered ones, so by the time your `OnDeathSystem` fires `RespawnPage` is
  already open. There *is* an ordering API, though: `ISystem.getDependencies()` returns a
  `Set<Dependency<EntityStore>>`, and `ComponentRegistry` topologically sorts every registered system
  (including `RefChangeSystem`s) by those edges — so an `OnDeathSystem` that overrides it to return
  `Set.of(new SystemDependency<>(Order.BEFORE, DeathSystems.PlayerDeathScreen.class))`
  (`com.hypixel.hytale.component.dependency.SystemDependency` / `Order`) is *meant* to run first.
  This has not been exercised in-game against `PlayerDeathScreen`; treat it as an API-level lead,
  not a verified recipe.

There is also **no auto-respawn timer** — `DeathComponent.respawn(...)` is only called by `RespawnPage`
and `PlayerRespawnCommand`, so a dead player waits on the death screen until the button/dismiss. And
`respawn(...)` is a **no-op on a live entity** (it returns a completed future if there's no
`DeathComponent`), so you can't force-respawn someone you haven't killed.

**Viable patterns instead of replacing the screen:**

- **Let the native screen show, then drive an auto-respawn timer** — schedule
  `DeathComponent.respawn(accessor, ref)` N seconds after death from your `OnDeathSystem`, and layer
  your own info as a HUD/overlay ([ui-api.md](ui-api.md)).
- **Re-skin the existing screen** by overriding its asset at
  `Common/UI/Custom/Pages/RespawnPage.ui`. This is **global** — it affects every world on the server.

---

## Damage Handling Examples

### Cancel Damage

```java
public class NoDamageSystem extends DamageEventSystem {
    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       Damage event) {
        // Cancel all damage
        event.setCancelled(true);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return DamageDataComponent.getComponentType();
    }
}
```

### Modify Damage Based on Source

```java
public class DamageModifierSystem extends DamageEventSystem {
    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       Damage event) {
        Damage.Source source = event.getSource();

        if (source instanceof Damage.EnvironmentSource) {
            // Could log environmental damage
            System.out.println("Environmental damage: " + event.getAmount());
        } else if (source instanceof Damage.ProjectileSource) {
            // Could modify projectile damage
            System.out.println("Projectile damage: " + event.getAmount());
        } else if (source instanceof Damage.EntitySource entitySource) {
            // Player or mob attack
            System.out.println("Entity damage: " + event.getAmount());
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return DamageDataComponent.getComponentType();
    }
}
```

### Notify Attacker on Hit

```java
public class HitNotificationSystem extends DamageEventSystem {
    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       Damage event) {
        if (event.getSource() instanceof Damage.EntitySource entitySource) {
            Ref<EntityStore> attackerRef = entitySource.getRef();
            Player attacker = store.getComponent(attackerRef, Player.getComponentType());

            if (attacker != null) {
                float damage = event.getAmount();
                attacker.getPlayerRef().sendMessage(Message.raw("Dealt " + damage + " damage!").color("#FF6600"));
            }
        }
    }

    @Override
    public Query<EntityStore> getQuery() {
        return DamageDataComponent.getComponentType();
    }
}
```

---

## Stat Modification on Hit (JSON)

Damage interactions can grant stats to the attacker when they successfully hit an entity. This is configured via the `EntityStatsOnHit` property in damage interaction JSON files.

> **See also:** [DamageEntity Interaction](interactions-combat.md#damageentity) for the complete structure including damage effects and target selectors. For how **NPCs** deal melee damage without a CAE — the `Root_NPC_Attack_Melee` interaction-var chain (`Melee_Start` → `Melee_Selector` → `Melee_Damage`) and its directional swept-arc selector — see [Melee attacks without a CAE](npc-roles.md#melee-attacks-without-a-cae).

**File locations:** `Server/Item/Interactions/Weapons/{WeaponType}/Primary/*_Damage.json`

### EntityStatsOnHit

An array of stat modifications applied to the attacker on successful hit:

```json
{
  "Type": "DamageEntity",
  "EntityStatsOnHit": [
    { "EntityStatId": "SignatureEnergy", "Amount": 1 }
  ],
  "DamageCalculator": {
    "BaseDamage": {
      "Physical": 10
    }
  }
}
```

### Structure

Each entry in the `EntityStatsOnHit` array has:

| Property | Type | Description |
|----------|------|-------------|
| `EntityStatId` | string | The stat to modify (must name a `Server/Entity/Stats/` asset) |
| `Amount` | number | Base amount for a single-entity hit |
| `MultipliersPerEntitiesHit` | float[] | Multiplier applied to `Amount` by how many entities the same swing has hit so far (index 0 = first). Default `[1.0, 0.6, 0.4, 0.2, 0.1]`; must be non-empty |
| `MultiplierPerExtraEntityHit` | number | Multiplier for every entity beyond the array's length. Default `0.05` |

### Available Stats

- `SignatureEnergy` - Ultimate/signature ability resource
- `Stamina` - Used for blocking, sprinting, dodging
- `Health` - Entity health
- `Mana` - Magic resource

### Example: Sword Granting Signature Energy

From `Common_Melee_Damage.json` (abridged):

```json
{
  "Parent": "DamageEntityParent",
  "DamageCalculator": {
    "BaseDamage": {
      "Physical": 6
    }
  },
  "EntityStatsOnHit": [
    { "EntityStatId": "SignatureEnergy", "Amount": 1 }
  ]
}
```

This grants 1 signature energy to the attacker each time they land a hit.

---

## Blocking Mechanics (JSON)

Blocking is implemented via the `Wielding` interaction type. See [WieldingInteraction](interactions-world.md#wieldinginteraction) for full details.

> **See also:** [ChangeStat Interaction](interactions-combat.md#changestat) for granting stats on successful blocks, and [ApplyForce](interactions-combat.md#applyforce) for knockback effects.

### How Blocking Reduces Damage

The `DamageModifiers` property in `AngledWielding` controls damage reduction per damage type:

```json
"AngledWielding": {
  "Angle": 0,
  "AngleDistance": 90,
  "DamageModifiers": {
    "Physical": 0,
    "Projectile": 0.5,
    "Fire": 1
  }
}
```

| Value | Effect |
|-------|--------|
| `0` | Full block (no damage taken) |
| `0.5` | 50% damage reduction |
| `1` | No reduction (full damage) |

### Stamina Consumption on Block

Blocking consumes stamina based on the `StaminaCost` property:

```json
"StaminaCost": {
  "CostType": "Damage",
  "Value": 0.5
}
```

- **CostType** — how the stamina loss is computed: `Damage` (`Value` = how much damage one stamina point is worth, so `0.5` drains 2 stamina per point of blocked damage) or `MaxHealthPercentage` (the default; `Value` = the fraction of the blocker's max health one stamina point is worth, default `0.04` = 4%)
- **Value** — the per-stamina-point worth described above (the key is `Value`, not `Cost`)

### Granting Stats on Successful Block

Use `BlockedInteractions` with `ChangeStat` to grant stats when a block succeeds:

```json
{
  "Type": "Wielding",
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "ChangeStat",
        "StatModifiers": {
          "SignatureEnergy": 5
        }
      }
    ]
  },
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 90,
    "DamageModifiers": { "Physical": 0 }
  },
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Shield_T2_Impact"
  }
}
```

This configuration:
1. Blocks all physical damage from the front 180° arc
2. Plays a sound effect on successful block
3. Grants 5 signature energy to the blocker

### Guard Break

When stamina is depleted during a block, the `Failed` interaction triggers. `Failed` is a
`ChargingInteraction` key whose value is a **single interaction** (an id, or an inline definition —
it is an `Interaction.CHILD_ASSET_CODEC`), not a list. The shipped guards use one of two shapes:

```json
// Server/Item/Interactions/Weapons/Stick/Block/Stick_Block_Damage.json — play a shatter effect
"Failed": {
  "Type": "Simple",
  "Effects": {
    "Particles": [
      { "SystemId": "Shield_Shatter" }
    ]
  }
}
```

```json
// Server/Item/Interactions/Weapons/Common/Guarding/Common_Guard_Wield.json — defer to an
// interaction var so each weapon can supply its own guard-break
"Failed": {
  "Type": "Replace",
  "Var": "Guard_Break",
  "DefaultOk": true,
  "DefaultValue": { "Interactions": [ { "Type": "Simple", "Effects": { } } ] }
}
```

> **There is no `Stagger` interaction type.** The valid `Type` values are exactly the ids
> `InteractionModule` registers on `Interaction.CODEC` (`Simple`, `Replace`, `Parallel`, `Serial`,
> `ApplyForce`, `ChangeStat`, `ResetCooldown`, `DamageEntity`, `Wielding`, …). An **unrecognised
> `Type` value fails silently**: `ACodecMapCodec` falls back to the first-registered codec —
> `Simple` — so a typo'd type quietly becomes a do-nothing `Simple` interaction with no warning.
> (An unrecognised *key*, by contrast, does log: `Unused key(s) in '<id>' file <path>: <key>`.)

### Timed Blocking and Parry Mechanics

The `Wielding` interaction supports time-limited blocks and parry windows through properties inherited from `ChargingInteraction`.

#### RunTime

Sets a **maximum duration** for the block. The interaction ends at whichever comes first: the player releasing the input button, or the `RunTime` expiring.

```json
{
  "Type": "Wielding",
  "RunTime": 0.5,
  "DamageModifiers": { "Physical": 0 }
}
```

- Without `RunTime`: Block continues while input is held (standard guard)
- With `RunTime`: Block lasts up to the specified duration, but still ends early if input is released

> **Note:** There is no JSON-only way to create a "click-once-to-block-for-X-seconds" mechanic where releasing the button doesn't end the block. The `RunTime` property only provides an upper bound—it does not commit the player to blocking for the full duration.

#### FailOnDamage

When `true`, the interaction ends immediately when the entity is hit.

```json
{
  "Type": "Wielding",
  "RunTime": 5,
  "FailOnDamage": true,
  "DamageModifiers": { "Physical": 0 },
  "BlockedInteractions": {
    "Interactions": [
      { "Type": "ChangeStat", "StatModifiers": { "SignatureEnergy": 5 } }
    ]
  }
}
```

**Important:** `FailOnDamage` triggers when the entity is **hit**, not when actual damage is taken. This means it fires even if the attack was fully blocked (damage reduced to 0). This enables parry mechanics where:

1. Player initiates parry (short `RunTime` window)
2. If hit during window → `BlockedInteractions` triggers (e.g., counter-attack, stat grant), then interaction ends
3. If not hit → interaction ends after `RunTime` expires

#### Example: Parry Window

From `Server/Item/Interactions/_Debug/Debug_Stick_Parry.json` (abridged — the shipped file also sets `Effects.ItemAnimationId: "Guard"`, a `VelocityConfig` on the force, and a trailing `ResetCooldown` step):

```json
{
  "Type": "Wielding",
  "RunTime": 5,
  "FailOnDamage": true,
  "DamageModifiers": { "Physical": 0 },
  "BlockedInteractions": {
    "Interactions": [
      {
        "Type": "Parallel",
        "Interactions": [
          {
            "Interactions": [
              { "Type": "ApplyForce", "Forces": [{ "Direction": { "Z": -1 }, "Force": 10 }] }
            ]
          },
          { "Interactions": ["Stick_Attack"] }
        ]
      }
    ]
  }
}
```

This creates a 5-second parry window that:
- Blocks all physical damage
- On successful parry: knocks back attacker and triggers a counter-attack
- Ends after being hit once (`FailOnDamage`) or after 5 seconds (`RunTime`)

#### Example: Timed Block with Maximum Duration

A block with a maximum duration that still ends early if the player releases the input:

```json
{
  "Type": "Wielding",
  "RunTime": 0.5,
  "FailOnDamage": false,
  "CancelOnOtherClick": true,
  "AngledWielding": {
    "Angle": 0,
    "AngleDistance": 90,
    "DamageModifiers": { "Physical": 0 }
  },
  "BlockedEffects": {
    "WorldSoundEventId": "SFX_Shield_T2_Impact"
  }
}
```

| Property | Value | Effect |
|----------|-------|--------|
| `RunTime` | `0.5` | Block lasts up to 0.5 seconds (ends early if input released) |
| `FailOnDamage` | `false` | Block continues even after being hit |
| `CancelOnOtherClick` | `true` | Block cancels if player clicks another input (defaults to `true`) |

> **`AllowIndefiniteHold` is not a `Wielding` key.** It is registered on `ChargingInteraction.CODEC`
> — the concrete `"Type": "Charging"` codec — not on the `ABSTRACT_CODEC` that `WieldingInteraction`
> builds on, so writing it into a `Wielding` block does nothing but earn an `Unused key(s)` warning.
> `WieldingInteraction`'s own `afterDecode` unconditionally sets `allowIndefiniteHold = true`. (It
> gates the *charge-value* forks, not `RunTime`, so it would not have bounded a block anyway.)

> **Limitation:** This configuration still requires holding the input to maintain the block. Releasing the button ends the block early. A true "click-once-to-block" mechanic (where the block persists for the full duration regardless of input) would require custom Java code.

> **Inherited Properties:** `FailOnDamage` and `CancelOnOtherClick` come from `ChargingInteraction`'s abstract codec, which `WieldingInteraction` extends; `RunTime` comes from the `Interaction` base codec, so every interaction type accepts it. See [WieldingInteraction](interactions-world.md#wieldinginteraction) for the full property list.

> **In-Game Verification:** When testing blocking mechanics, use the debug stick items found in `Server/Item/Interactions/_Debug/` as reference implementations. The `Debug_Stick_Parry.json` demonstrates timed blocking with counter-attacks.

---

## Knockback System

Knockback is a temporary component-based system that applies velocity changes to entities when they take damage. The `KnockbackComponent` is added to entities during combat and automatically removed when the knockback effect completes.

> **See also:** [ApplyForce Interaction](interactions-combat.md#applyforce) for direct force application via JSON, and [Control Flow Interactions](interactions-flow.md) for combining knockback with other effects.

### KnockbackComponent

**Package:** `com.hypixel.hytale.server.core.entity.knockback`

A temporary ECS component that manages knockback state on entities.

#### Lifecycle

1. **Added**: When an entity takes damage from an attack with a `Knockback` configuration
2. **Active**: The `ApplyKnockback` system applies velocity each tick while `timer < duration`
3. **Removed**: Automatically removed when `timer >= duration`

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `velocity` | `Vector3d` | Direction and magnitude of knockback force |
| `velocityType` | `ChangeVelocityType` | How velocity is applied (SET, ADD, etc.) |
| `velocityConfig` | `VelocityConfig` | Additional velocity configuration |
| `modifiers` | `DoubleList` | Reduction multipliers (armor, wielding, etc.) |
| `duration` | `float` | Total knockback duration in seconds |
| `timer` | `float` | Elapsed time since knockback started |

### JSON Configuration

Knockback is configured in damage interaction JSON files using the `Knockback` property.

**File locations:** `Server/Item/Interactions/Weapons/{WeaponType}/Primary/*_Damage.json`

#### Basic Knockback

From `Server/Item/Interactions/Weapons/Weapon_Damage.json` — `Knockback` sits inside
`DamageEffects`:

```json
{
  "Type": "DamageEntity",
  "DamageCalculator": {
    "BaseDamage": {
      "Physical": 5
    }
  },
  "DamageEffects": {
    "Knockback": {
      "Force": 0.5,
      "RelativeX": -5,
      "RelativeZ": -5,
      "VelocityY": 5
    },
    "WorldSoundEventId": "SFX_Unarmed_Impact",
    "WorldParticles": [
      { "SystemId": "Impact_Blade_01" }
    ]
  }
}
```

#### Knockback Properties

| Property | Type | Description |
|----------|------|-------------|
| `Force` | float | Base knockback strength multiplier |
| `RelativeX` | float | Knockback in local X axis (relative to attacker facing) |
| `RelativeZ` | float | Knockback in local Z axis (push away from attacker) |
| `VelocityY` | float | Upward velocity component |
| `Duration` | float | How long knockback lasts (optional) |

### Knockback Types

`Knockback` is a `Type`-dispatched codec (`Knockback.CODEC`, a `CodecMapCodec` keyed on `"Type"`) with three subclasses registered by `InteractionModule`. When `Type` is omitted the first registration — `Directional` — is used, which is why the relative form above carries no `Type`:

| `Type` | Class | Type-specific keys |
|--------|-------|--------------------|
| `Directional` (default) | `DirectionalKnockback` | `RelativeX`, `RelativeZ`, `VelocityY` — fixed direction relative to the attacker's facing |
| `Point` | `PointKnockback` | `OffsetX`, `OffsetZ`, `RotateY`, `VelocityY` — push away from a point (explosions, `Bomb_Explode_Stun`) |
| `Force` | `ForceKnockback` | `Direction` `{ X, Y, Z }` — push along a direction scaled by `Force` (`Common_Melee_Damage`) |

All three share the base keys `Force`, `Duration`, `VelocityType` (a `ChangeVelocityType`; default `Add`, vanilla weapons use `Set`) and `VelocityConfig` (`AirResistance`, `AirResistanceMax`, `GroundResistance`, `GroundResistanceMax`, `Threshold`, `Style`).

### Knockback Resistance

Multiple systems can reduce knockback effectiveness:

#### Armor Reduction

The `DamageSystems.ArmorKnockbackReduction` system reduces knockback based on equipped armor. Armor pieces with knockback resistance add reduction modifiers to the `KnockbackComponent.modifiers` list.

#### Wielding Reduction

The `DamageSystems.WieldingKnockbackReduction` system reduces knockback when blocking or wielding items. Shields and weapons can provide knockback resistance while held.

#### Status Effects

Certain status effects can modify knockback resistance, either increasing or decreasing the final knockback applied.

### Related Systems

| System | Description |
|--------|-------------|
| `KnockbackSystems.ApplyKnockback` | Main system that applies velocity and removes component when done |
| `KnockbackSystems.ApplyPlayerKnockback` | Separate system for player-specific knockback handling |
| `DamageSystems.ArmorKnockbackReduction` | Calculates armor-based knockback reduction |
| `DamageSystems.WieldingKnockbackReduction` | Calculates wielding-based knockback reduction |

### Applying Knockback via Code

To apply knockback programmatically, add a `KnockbackComponent` to an entity:

```java
import com.hypixel.hytale.server.core.entity.knockback.KnockbackComponent;
import org.joml.Vector3d;

// In an ECS system with access to CommandBuffer
KnockbackComponent knockback = new KnockbackComponent();
knockback.setVelocity(new Vector3d(0, 5, -10));  // Up and backward
knockback.setDuration(0.5f);  // Half second duration
knockback.setTimer(0f);

buffer.setComponent(entityRef, KnockbackComponent.getComponentType(), knockback);
```

> **Note:** Knockback applied via code bypasses the armor/wielding reduction systems unless you manually calculate and apply modifiers.

> **See also:** For direct velocity manipulation without the component system, see [Knockback from Damage in entities.md](entities.md#example-knockback-from-damage).

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages the combat subsystem produces (verified against `HytaleServer.jar`). Two of them are assembled at runtime from a class name, so they will not be found by grepping the jar for the whole sentence.

- **`' doesn't exist!`** — assembled line `Asset '<id>' of type com.hypixel.hytale.server.core.modules.entity.damage.DamageCause doesn't exist!` (logged under `Failed to validate asset!`; this replaced the pre-0.6.3 `Invalid DamageCause` wording, which no longer appears anywhere in the jar) → a key in `DamageCalculator.BaseDamage` — or in a `DamageModifiers` / `KnockbackModifiers` map on `Wielding` or `AngledWielding` — names a cause that isn't a `DamageCause` asset. All four maps run their keys through `DamageCause.VALIDATOR_CACHE.getMapKeyValidator()`, which lands in `AssetStore.validate`. Fix: use a valid id such as `Physical`, `Fire`, `Ice`, `Slashing`, `Fall`, `Drowning`, `Projectile`, `Environment`, or `Command`.
- **`Missing default DamageCause assets`** → the default `DamageCause` assets failed to load. Fix: an asset-pack/install problem, not a plugin bug; verify the game install and `Assets.zip`.
- **`Can't be null!`** on `EntityStatId`, or the same **`' doesn't exist!`** line for `...entitystats.asset.EntityStatType` (these replaced the pre-0.6.3 `Invalid EntityStatOnHit in EntityStatsOnHit` wording) → an entry in a damage interaction's `EntityStatsOnHit` array is missing its `EntityStatId` or names a stat with no `Server/Entity/Stats/` asset. A related **`Array can't be empty!`** means `MultipliersPerEntitiesHit` was set to `[]`. Fix: each entry needs a valid `EntityStatId` (e.g. `SignatureEnergy`, `Stamina`, `Health`, `Mana`) and a numeric `Amount`; omit `MultipliersPerEntitiesHit` to keep the default.
- **Symptom:** a `DamageEventSystem` throws or matches nothing because `getQuery()` returned `null` → unlike `KillFeedEvent` handlers, a damage system needs a real query. Fix: return `DamageDataComponent.getComponentType()` from `getQuery()`.
- **Symptom:** your damage handler reads the wrong entity as the attacker → the `Damage` event fires on the **victim**. Fix: cast `getSource()` to `Damage.EntitySource` and call `getRef()` for the attacker.
- **Symptom:** `KnockbackComponent` added via code ignores armor/shield reduction → code-applied knockback bypasses the `ArmorKnockbackReduction`/`WieldingKnockbackReduction` systems. Fix: apply knockback through a damage interaction's `Knockback` config, or compute and add the `modifiers` yourself.
- **Symptom:** a `RunTime` "click-once-to-block" never persists after releasing input → `RunTime` is only an upper bound on a held block, not a commitment. Fix: there is no JSON-only persistent block; it requires custom Java (see [Timed Blocking](#timed-blocking-and-parry-mechanics)).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
