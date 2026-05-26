---
title: "Combat API"
description: "Handle Hytale combat in Java — the Damage ECS event and DamageEventSystem, damage source types (entity, environment, projectile, command), and JSON-driven combat config."
seo:
  type: TechArticle
---

# Combat API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against build-12**

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
// Get who/what caused the damage
Damage.Source getSource()

// Get damage amount
float getAmount()
float getInitialAmount()

// Get damage cause
DamageCause getCause()
int getDamageCauseIndex()

// Cancellable
boolean isCancelled()
void setCancelled(boolean)
```

### Important Notes

1. **Event fires on VICTIM**: The Damage event is invoked on the entity receiving damage, not the attacker
2. **Getting the attacker**: Use `Damage.EntitySource.getRef()` to get the attacker's entity reference
3. **getQuery() required**: Must return a valid query (not null). Use `DamageDataComponent.getComponentType()`
4. **Extend DamageEventSystem**: Use the provided base class, not raw `EntityEventSystem<EntityStore, Damage>`

---

## Damage Source Types

### Damage.Source (Interface)

Base interface for all damage sources.

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

### Predefined Constants
```java
static DamageCause PHYSICAL       // Melee/physical attacks
static DamageCause PROJECTILE     // Arrow/thrown item damage
static DamageCause COMMAND        // Damage from commands
static DamageCause DROWNING       // Underwater suffocation
static DamageCause ENVIRONMENT    // Environmental hazards (lava, etc.)
static DamageCause FALL           // Fall damage
static DamageCause OUT_OF_WORLD   // Void damage
static DamageCause SUFFOCATION    // Block suffocation
```

> **These are *not* compile-time constants — they are runtime asset lookups.** The fields are
> `public static` but **non-final**, populated by the asset system, which finishes loading *after*
> plugin `setup()`. They are **`null` until then**. Referencing one in a `static final` field (or
> anywhere at class-load / `setup()` time) throws `ExceptionInInitializerError` /
> `NullPointerException` (`DamageCause.getId()` on a null cause). Build `Damage` lazily, at
> gameplay time, instead:
> ```java
> // NOT a static field. Construct at use-time, once assets are loaded:
> Damage d = new Damage(Damage.NULL_SOURCE, DamageCause.COMMAND, amount);
> ```
> `DeathComponent.getDeathCause()` returns the cause of a death — handy for ignoring admin/`COMMAND`
> kills in scoring.

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

    if (cause == DamageCause.FALL) {
        // Handle fall damage specially
        event.setCancelled(true);  // No fall damage
    } else if (cause == DamageCause.DROWNING) {
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
                attacker.sendMessage(Message.raw("You hit something for " + event.getAmount() + " damage!"));
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
        return null;
    }
}
```

> **Note:** Unlike `DamageEventSystem`, `KillFeedEvent` handlers can return `null` from `getQuery()` to handle all entities.

### Registration

```java
@Override
protected void setup() {
    getEntityStoreRegistry().registerSystem(new KillerMessageSystem());
    getEntityStoreRegistry().registerSystem(new KillFeedDisplaySystem());
}
```

### Kill Feed Event Flow

When an entity is killed, the events fire in this order:
1. `KillFeedEvent.KillerMessage` - Allows customizing/cancelling the killer's notification
2. `KillFeedEvent.DecedentMessage` - Allows customizing/cancelling the victim's death message
3. `KillFeedEvent.Display` - Allows customizing/cancelling the kill feed UI broadcast

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
death-cam, a "you died" overlay with your own button). **In build-12 this is not cleanly moddable**,
because the engine's death screen and the respawn action are the same object.

The flow, for a player whose `DeathComponent` was just added:

- `DeathSystems$PlayerDeathScreen` (an `OnDeathSystem`) runs and, **if
  `DeathComponent.isShowDeathMenu()` is true**, opens the death screen via
  `player.getPageManager().openCustomPage(ref, store, new RespawnPage(...))`.
- **`RespawnPage` *is* the respawn trigger.** Both of its exit paths call `DeathComponent.respawn(...)`:
  - the **Respawn button** (`handleDataEvent`, action `"Respawn"`), and
  - **`RespawnPage.onDismiss(...)`** — if the entity still has a `DeathComponent`.

Because `PageManager` holds a **single** current page and `openCustomPage(...)` fires the **previous
page's `onDismiss`** before showing the new one (see [ui-api.md → Live updates & page replacement](ui-api.md#live-updates--page-replacement)),
**replacing the death screen respawns the player out from under your page.** You cannot swap in your
own death/respawn page.

**Can you suppress it instead?** `showDeathMenu` is the off-switch, but it is impractical to reach:

- It **defaults `true`** (hard-coded in the `DeathComponent` constructor).
- It is **not configurable** — `DeathConfig` has no field for it, and jar-wide **only `DeathComponent`
  itself** calls `setShowDeathMenu`.
- You would have to set it `false` **before `PlayerDeathScreen` runs** — but **engine systems run
  before plugin-registered systems, and there is no system-ordering / priority API** (`System`,
  `RefChangeSystem`, and `QuerySystem` expose no `getOrder`/`priority`/`runsBefore`). By the time your
  `OnDeathSystem` fires, `RespawnPage` is already open.

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
                attacker.sendMessage(Message.raw("Dealt " + damage + " damage!").color("#FF6600"));
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

> **See also:** [DamageEntity Interaction](interactions-combat.md#damageentity) for the complete structure including damage effects and target selectors.

**File locations:** `Server/Item/Interactions/Weapons/{WeaponType}/Primary/*_Damage.json`

### EntityStatsOnHit

An array of stat modifications applied to the attacker on successful hit:

```json
{
  "Type": "DamageEntity",
  "EntityStatsOnHit": [
    { "EntityStatId": "SignatureEnergy", "Amount": 1 }
  ],
  "DamageParameters": {
    "DamageAmount": 10,
    "DamageCauseId": "Physical"
  }
}
```

### Structure

Each entry in the `EntityStatsOnHit` array has:

| Property | Type | Description |
|----------|------|-------------|
| `EntityStatId` | string | The stat to modify |
| `Amount` | number | Amount to add to the stat |

### Available Stats

- `SignatureEnergy` - Ultimate/signature ability resource
- `Stamina` - Used for blocking, sprinting, dodging
- `Health` - Entity health
- `Mana` - Magic resource

### Example: Sword Granting Signature Energy

From `Common_Melee_Damage.json`:

```json
{
  "Type": "DamageEntity",
  "EntityStatsOnHit": [
    { "EntityStatId": "SignatureEnergy", "Amount": 1 }
  ],
  "DamageParameters": {
    "DamageAmount": 5,
    "DamageCauseId": "Physical"
  }
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
    "Magical": 0.5,
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
  "Cost": 0.5
}
```

- **CostType: "Damage"** - Stamina cost scales with incoming damage
- **Cost** - Multiplier (0.5 = consume 0.5 stamina per point of damage blocked)

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

When stamina is depleted during a block, the `Failed` interactions trigger:

```json
"Failed": {
  "Interactions": [
    { "Type": "Stagger" }
  ]
}
```

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

From `Server/Item/Interactions/_Debug/Debug_Stick_Parry.json`:

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
  "allowIndefiniteHold": false,
  "cancelOnOtherClick": true,
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
| `allowIndefiniteHold` | `false` | Block cannot exceed `RunTime` even if input is held |
| `cancelOnOtherClick` | `true` | Block cancels if player clicks another input |

> **Limitation:** This configuration still requires holding the input to maintain the block. Releasing the button ends the block early. A true "click-once-to-block" mechanic (where the block persists for the full duration regardless of input) would require custom Java code.

> **Inherited Properties:** These properties (`RunTime`, `FailOnDamage`, `allowIndefiniteHold`, `cancelOnOtherClick`) are inherited from `ChargingInteraction`, which `WieldingInteraction` extends. See [WieldingInteraction](interactions-world.md#wieldinginteraction) for the full property list.

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

```json
{
  "Type": "DamageEntity",
  "DamageParameters": {
    "DamageAmount": 10,
    "DamageCauseId": "Physical"
  },
  "Knockback": {
    "Force": 0.5,
    "RelativeX": -5,
    "RelativeZ": -5,
    "VelocityY": 5
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

The knockback system supports multiple types through different `VelocityConfig` implementations:

| Type | Description |
|------|-------------|
| `DirectionalKnockback` | Applies knockback in a fixed direction relative to the attacker |
| `ForceKnockback` | Applies knockback based on force magnitude |
| `PointKnockback` | Applies knockback away from a specific point (explosions) |

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

Backtick-quoted error strings below are the literal messages thrown by the build-12 combat subsystem (verified against `HytaleServer.jar`).

- **`Invalid DamageCause`** → a `DamageCauseId` (in `DamageParameters`) names a cause that isn't a registered `DamageCause` asset. Fix: use a valid id such as `Physical`, `Fall`, `Drowning`, `Projectile`, `Environment`, or `Command`.
- **`Missing default DamageCause assets`** → the default `DamageCause` assets failed to load. Fix: an asset-pack/install problem, not a plugin bug; verify the game install and `Assets.zip`.
- **`Invalid EntityStatOnHit in EntityStatsOnHit`** → an entry in a damage interaction's `EntityStatsOnHit` array is malformed. Fix: each entry needs a valid `EntityStatId` (e.g. `SignatureEnergy`, `Stamina`, `Health`, `Mana`) and a numeric `Amount`.
- **Symptom:** a `DamageEventSystem` throws or matches nothing because `getQuery()` returned `null` → unlike `KillFeedEvent` handlers, a damage system needs a real query. Fix: return `DamageDataComponent.getComponentType()` from `getQuery()`.
- **Symptom:** your damage handler reads the wrong entity as the attacker → the `Damage` event fires on the **victim**. Fix: cast `getSource()` to `Damage.EntitySource` and call `getRef()` for the attacker.
- **Symptom:** `KnockbackComponent` added via code ignores armor/shield reduction → code-applied knockback bypasses the `ArmorKnockbackReduction`/`WieldingKnockbackReduction` systems. Fix: apply knockback through a damage interaction's `Knockback` config, or compute and add the `modifiers` yourself.
- **Symptom:** a `RunTime` "click-once-to-block" never persists after releasing input → `RunTime` is only an upper bound on a held block, not a commitment. Fix: there is no JSON-only persistent block; it requires custom Java (see [Timed Blocking](#timed-blocking-and-parry-mechanics)).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
