---
title: "Beams"
description: "Hytale's beam subsystem (0.7.2+) — the Beam asset under Server/Entity/Beams, the AttachBeam interaction, the BeamComponent and AttachedBeam Java API for tethers between entities or to fixed points, free-standing beam entities, the /beam command, and how beams reach clients."
seo:
  type: TechArticle
---

# Beams

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Entity/Beams` · **Verified against 0.7.2**

New in 0.7.2. A **beam** is a textured strip the client draws between two points, where at least one
end is an entity: from an entity to another entity (a rope from a grappling hook back to the
shooter's hand), or from an entity to a fixed point in the world. The server never draws anything.
It keeps a list of beams on the **source** entity, as a `BeamComponent`, and sends that list to every
client that can see the entity. The client draws each beam with the texture that its **`Beam`
asset** names.

The whole subsystem is one bundled plugin, `BeamPlugin` (`com.hypixel.hytale.builtin.beam`, manifest
identity `Hytale:Beam`, depends on `Hytale:EntityModule`). It is absent from
`Constants.CORE_PLUGINS`, so the `Beam` asset store, the `AttachBeam` interaction type and the
`/beam` command exist only while the plugin is loaded. A plugin that uses them should declare
`"Dependencies": { "Hytale:Beam": "*" }`.

> **Reading the examples.** An example that names a shipped source file is taken from the shipped
> assets. In the others, every id that starts with `MyMod_` is a placeholder for an asset you write
> yourself: a `Beam` asset, an interaction or a projectile config. All other ids are real shipped
> ids. References resolve by file name, so a `MyMod_` id fails validation until an asset of that name
> exists in your pack.

---

## Overview

| Piece | What it is | Section |
|-------|------------|---------|
| `Beam` asset | One key, `TexturePath`. 4 ship under `Server/Entity/Beams/` | [The Beam asset](#the-beam-asset) |
| `AttachBeam` interaction | Adds one beam from the entity running the chain to another entity | [The AttachBeam interaction](#the-attachbeam-interaction) |
| `BeamComponent` | The per-entity list of beams, at most 64, never saved | [BeamComponent](#beamcomponent) |
| `AttachedBeam` | One beam: asset index, scales, nodes, offsets, and an entity or position target | [AttachedBeam](#attachedbeam) |
| `BeamSystems` | `Tracker` sends the list to viewers; `Remove` clears it from them | [How beams reach clients](#how-beams-reach-clients) |
| `/beam` | `entity`, `position`, `spawn` and `clear` subcommands for testing | [The /beam command](#the-beam-command) |

Shipped content uses beams in exactly two places, both on a projectile's `ProjectileSpawn` chain:
the Hookshot tool's rope and the Chain Hook rune's chain. See
[How shipped content uses beams](#how-shipped-content-uses-beams).

## Key Classes

| Class | Package | Role |
|-------|---------|------|
| `BeamPlugin` | `com.hypixel.hytale.builtin.beam` | Registers the store, the component, both systems, `/beam` and `AttachBeam` |
| `Beam` | `com.hypixel.hytale.builtin.beam.asset` | The asset: an id and a texture path |
| `BeamPacketGenerator` | `com.hypixel.hytale.builtin.beam.asset` | Sends `Beam` assets to clients as `UpdateBeamConfigs` |
| `BeamComponent` | `com.hypixel.hytale.builtin.beam` | ECS component on the source entity |
| `AttachedBeam` | `com.hypixel.hytale.builtin.beam` | A record describing one beam |
| `BeamSystems.Tracker` / `BeamSystems.Remove` | `com.hypixel.hytale.builtin.beam` | Network sync |
| `AttachBeamInteraction` | `com.hypixel.hytale.builtin.beam.interaction` | The `AttachBeam` interaction type |
| `BeamCommand` | `com.hypixel.hytale.builtin.beam.command` | `/beam` |

---

## The Beam asset

### Beam

**Package:** `com.hypixel.hytale.builtin.beam.asset.Beam`

Stored at `Server/Entity/Beams/<Id>.json` (the store's path is `Entity/Beams`). The id is the file
name. The store is an `IndexedLookupTableAssetMap`, so every beam also has an integer **index**, and
that index, not the id, is what an `AttachedBeam` carries and what goes over the wire. The store is
declared to load before `Interaction`, so an `AttachBeam` interaction can resolve its beam id to an
index while it decodes.

| Key | Type | Default | Requiredness (engine-measured) | Description |
|-----|------|---------|-------------------------------|-------------|
| `TexturePath` | string | none (`null`) | **Required.** Omitting it fails decode | The texture tiled along the beam, a `.png` path relative to `Common/`. Declared with `appendInherited`, so a `Parent` beam can supply it |

That is the whole codec. `TexturePath` carries `Validators.nonNull()` and its field starts `null`,
so the engine rejects an asset without it. This was measured, not read: running
`maintenance/probes/requiredness/effective-required.py` against the 0.7.2 jar reports `TexturePath` as
the one key `Beam` rejects when it is omitted.

It also carries `CommonAssetValidator.TEXTURE_BEAM`, which requires the path to:

- sit under `Beams/` or `Trails/` (relative to `Common/`),
- end in `png`,
- name a common asset that exists.

A failure produces one of these messages, quoted from `CommonAssetValidator`:

- `Common Asset '<path>' must be within the root: [Beams/, Trails/]`
- `Common Asset '<path>' must have the extension png`
- `Common Asset '<path>' doesn't exist!`

Only the texture is sent to the client. `Beam.toPacket()` copies `TexturePath` into a
`BeamConfig` packet object, whose only field is `texture`. Width comes from each beam's scale, set
where the beam is attached, not from the asset.

### Shipped beams

All four use a texture from `Common/Trails/`, and no shipped asset uses a `Beams/` path.

| Id | `TexturePath` | Used by |
|----|---------------|---------|
| `Basic` | `Trails/Charged_Blue.png` | Nothing shipped. Reachable through `/beam` or Java |
| `Chain` | `Trails/Chain.png` | `Server/ProjectileConfigs/Abilities/Projectile_Config_ChainHook.json` |
| `Fire` | `Trails/Fire.png` | Nothing shipped |
| `Rope` | `Trails/Rope.png` | `Server/ProjectileConfigs/Tools/Projectile_Config_Hookshot.json` |

The whole of `Server/Entity/Beams/Rope.json`:

```json
{
  "TexturePath": "Trails/Rope.png"
}
```

### Writing a beam asset

A beam that reuses a shipped trail texture needs no art. In your pack, at
`Server/Entity/Beams/MyMod_Laser.json`:

```json
{
  "TexturePath": "Trails/Charged_Red.png"
}
```

For your own texture, put the PNG in your pack's `Common/` folder under `Beams/` (or `Trails/`) and
point `TexturePath` at it, for example `Beams/MyMod_Laser.png`. A texture under `Beams/` cannot be
shared with a `Trail` asset: `Trail`'s `CommonAssetValidator.TEXTURE_TRAIL` accepts `Trails/` only.

---

## The AttachBeam interaction

**Package:** `com.hypixel.hytale.builtin.beam.interaction.AttachBeamInteraction`

**Extends:** `SimpleInstantInteraction`, so it also takes the base interaction keys and
`SimpleInteraction`'s `Next` / `Failed` (see [SimpleInstantInteraction](interactions.md#simpleinstantinteraction)).
It is registered as `"Type": "AttachBeam"` by `BeamPlugin`.

It adds one beam whose **source is always the entity the chain runs for** (`context.getEntity()`, the
`User`). The keys choose only the far end, the asset, the width and the model nodes.

| Key | Type | Default | Requiredness (engine-measured) | Description |
|-----|------|---------|-------------------------------|-------------|
| `TargetEntity` | enum `User` / `Owner` / `Target` | `User` | Optional. It is null-validated, but the field already holds `User`, so the engine accepts the key's omission | Which entity the beam ends at, resolved from the context. `User` is the entity running the chain, `Owner` the entity that owns it, `Target` the chain's target entity |
| `BeamConfig` | string (a `Beam` id); the codec also takes an inline `Beam` object | none (`null`) | **Required.** Omitting it fails decode | The beam asset. An unknown id fails validation: `Asset '<id>' of type com.hypixel.hytale.builtin.beam.asset.Beam doesn't exist!`. Use an id: see [An inline BeamConfig](#an-inline-beamconfig) |
| `Scale` | float | `1.0` | Optional | Width of the beam. The one value is used for both ends |
| `SourceNodeName` | string | none | Optional | Model node on the source entity where the beam starts. Unset, it starts at the entity's position |
| `TargetNodeName` | string | none | Optional | Model node on the target entity where the beam ends. Unset, it ends at the entity's position |

`effective-required.py` reports `BeamConfig` as the only key `AttachBeamInteraction` rejects when
omitted. Both `TargetEntity` and `BeamConfig` carry `Validators.nonNull()`; the difference is the
default. The interaction has no keys for offsets, for a different width at each end, or for a target
position. Those are Java-only (see [AttachedBeam](#attachedbeam)).

What `firstRun` does, in order:

1. Returns silently if the running entity or the owning entity is no longer valid, or there is no
   command buffer.
2. Resolves `TargetEntity`. It returns silently when that yields no entity, as `Target` does in a
   chain that has no target.
3. Builds `AttachedBeam.toEntity(beamIndex, Scale, SourceNodeName, target, TargetNodeName)` and queues
   `addComponent` of a **new** `BeamComponent` holding just that beam onto the running entity.

Step 3 is an add, never a merge. See the first item under [Gotchas](#gotchas--errors).

The interaction does not end the beam, and no `DetachBeam` type exists. A beam lasts as long as
its `BeamComponent` stays on the entity. The shipped uses put it on a short-lived projectile, so the
beam ends when the projectile is removed.

### An inline BeamConfig

The key's codec is `Beam.CHILD_ASSET_CODEC`, a `ContainedAssetCodec`, so it decodes an inline object
as well as an id: `"BeamConfig": { "TexturePath": "Trails/Fire.png" }`. `ContainedAssetCodec` gives
such an object a generated id, `*<containing asset's id>_<key path>`, and queues it on the containing
asset to be loaded into the `Beam` store afterwards. The load-time existence check passes, because
`AssetStore.validate` accepts an id that the asset's own container holds.

No shipped asset writes it this way, and it was not run. Read from the source, it would not get a
valid index on a first load. `AttachBeamInteraction` turns the id into an index in its `afterDecode`
hook (`processConfig`, through `Beam.getAssetMap().getIndex`), and `AssetStore` loads an asset's
contained assets only after that asset has decoded. At that moment the generated id is not in the
`Beam` store yet, so the lookup returns `Integer.MIN_VALUE` and every beam the interaction adds
carries that index. Name a `Beam` asset file instead.

### How shipped content uses beams

Both uses run `AttachBeam` first in a projectile config's `ProjectileSpawn` chain. In that chain the
`User` is the projectile and the `Owner` is the shooter (`ProjectileModule` builds the context with
`InteractionContext.forProxyEntity(manager, creatorRef, projectileRef, store)`). So the beam lives on
the projectile and runs back to the shooter's `R-Attachment` node, a node that
`Common/Characters/Player.blockymodel` defines.

That context is the one the server builds when it starts the chain itself, which
`ProjectileModule.spawnProjectile` does only for a projectile that is not client-predicted, such as
the Chain Hook's (`LaunchAbilityProjectile` spawns through the overload without a prediction id). A
player's `Projectile` interaction, which the Hookshot uses, can spawn a client-predicted projectile
instead. The server does not start that projectile's `ProjectileSpawn` chain; `ProjectileSpawn` is
one of the four types `InteractionValidation` lets a client run for a predicted projectile. That
path was not traced here.

`Server/ProjectileConfigs/Tools/Projectile_Config_Hookshot.json` (the `Tool_Hookshot` item fires it
through a `Projectile` interaction), its `ProjectileSpawn` entry:

```json
{
  "ProjectileSpawn": {
    "Interactions": [
      {
        "Type": "AttachBeam",
        "BeamConfig": "Rope",
        "TargetEntity": "Owner",
        "Scale": 0.25,
        "TargetNodeName": "R-Attachment"
      },
      {
        "Type": "Simple",
        "RunTime": 0.5,
        "Next": {
          "Type": "RemoveEntity",
          "Entity": "User"
        }
      }
    ]
  }
}
```

The second entry removes the hook, and with it the rope, after half a second. The `ProjectileHit`
and `ProjectileMiss` chains each end in their own `RemoveEntity` (both of the miss chain's branches
do). Only the miss chain interrupts `ProjectileSpawn`: it declares
`"Rules": { "Interrupting": ["ProjectileSpawn"] }`, the root rule `InteractionManager` checks when a
chain starts. The hit chain writes `"Interrupting": ["ProjectileSpawn"]` at the top level of the
root, beside `Interactions`. `RootInteraction`'s codec has no key of that name there; `Interrupting`
is read only inside `Rules`. So the hit chain interrupts nothing, and the asset store logs the key as
unused (see [Gotchas](#gotchas--errors)).

`Server/ProjectileConfigs/Abilities/Projectile_Config_ChainHook.json` runs the same `AttachBeam`
with `"BeamConfig": "Chain"` and `"Scale": 0.5`, but its `ProjectileSpawn` chain holds only that
entry, with no timed `RemoveEntity`. The chain of calls that reaches it starts at `Rune_ChainHook` and
runs through `Root_Ability_ChainHook` and `Ability_ChainHook_Cast`, which launches the projectile with
`LaunchAbilityProjectile` and a `Lifetime` of `0.5`. That lifetime is what removes it: for a
projectile that does not pierce, `AbilityProjectileLauncher` gives it a `DespawnComponent` that
expires after `Lifetime` seconds. Its `ProjectileHit` and `ProjectileMiss` chains declare no `Rules`;
each waits 0.2 s and ends in `Weapon_Stick_Fire_Projectile_Despawn`, a `RemoveEntity` of the `User`.

### Example: a tethered bolt

A projectile config of your own whose bolt trails a red beam back to the shooter's hand. `Model` is
the one key a projectile config cannot omit: the engine rejects a config without it. This one borrows
the shipped `Ice_Bolt` model. The other keys of a projectile config are on
[the Projectiles page](projectiles.md).

```json
{
  "Model": "Ice_Bolt",
  "Interactions": {
    "ProjectileSpawn": {
      "Interactions": [
        {
          "Type": "AttachBeam",
          "BeamConfig": "MyMod_Laser",
          "TargetEntity": "Owner",
          "Scale": 0.15,
          "TargetNodeName": "R-Attachment"
        }
      ]
    }
  }
}
```

Put `AttachBeam` on the projectile, not on the player. A player that runs `AttachBeam` gets a
`BeamComponent` that stays until something removes it, and its next `AttachBeam` fails (see
[Gotchas](#gotchas--errors)).

---

## Java API

The component can be read and changed from any plugin that depends on `Hytale:Beam`. Every
`BeamComponent` method that changes the list marks it for resend, so changing the component in place
is enough: no `replaceComponent` is needed.

### BeamPlugin

**Package:** `com.hypixel.hytale.builtin.beam.BeamPlugin`

```java
static BeamPlugin getInstance()
ComponentType<EntityStore, BeamComponent> getBeamComponentType()
```

### BeamComponent

**Package:** `com.hypixel.hytale.builtin.beam.BeamComponent`

```java
static final int MAX_BEAMS = 64
static final float NO_LIFETIME = -1.0f

static ComponentType<EntityStore, BeamComponent> getComponentType()
static Ref<EntityStore> spawn(Store<EntityStore> store, Vector3d position, AttachedBeam... beams)
static Ref<EntityStore> spawn(Store<EntityStore> store, Vector3d position, float lifetime, AttachedBeam... beams)

BeamComponent()
BeamComponent(AttachedBeam... beams)
BeamComponent(BeamComponent other)

List<AttachedBeam> getBeams()            // unmodifiable view
void add(AttachedBeam beam)              // refused (logged) past 64
boolean remove(AttachedBeam beam)        // record equality
void set(List<AttachedBeam> newBeams)    // keeps the first 64, logs the rest
void clear()
boolean isEmpty()
void removeInvalid()                     // drops beams whose target entity is gone
boolean consumeNetworkOutdated()         // used by BeamSystems.Tracker
```

`BeamPlugin` registers the component with a supplier and no codec, so it is never written with the
entity: `Holder.createComponentsMap`, which builds the map an entity is saved from, skips every
component without a codec. A beam therefore does not survive the entity being saved and loaded again
(a chunk unload, a restart).

`BeamComponent.spawn` creates a free-standing beam entity at `position`, holding these components:

- `NetworkId`,
- a `TransformComponent` with zero rotation,
- the `BeamComponent`,
- a `UUIDComponent`,
- the store's non-serialized marker,
- a `DespawnComponent`, when `lifetime >= 0` (in seconds).

With the overload that takes no lifetime, which passes `NO_LIFETIME`, the entity has no
`DespawnComponent` and lasts until it is removed; being non-serialized, it is not saved with its
chunk. `/beam spawn` always calls the overload that takes a lifetime, and its `--lifetime` must be
greater than 0, so the command never creates a beam without one.

### AttachedBeam

**Package:** `com.hypixel.hytale.builtin.beam.AttachedBeam`

A record. Exactly one of `targetEntity` and `targetPosition` is non-null; the canonical constructor
throws `IllegalArgumentException("A beam needs exactly one of a target entity or a target position")`
otherwise.

```java
record AttachedBeam(int beamIndex, float sourceScale, String sourceNode, Vector3fc sourceOffset,
                    float targetScale, Ref<EntityStore> targetEntity, String targetNode,
                    Vector3fc targetOffset, Vector3dc targetPosition)

// to an entity (offsets default to zero; a single scale is used for both ends)
static AttachedBeam toEntity(int beamIndex, float scale, String sourceNode, Ref<EntityStore> target, String targetNode)
static AttachedBeam toEntity(int beamIndex, float sourceScale, float targetScale, String sourceNode, Ref<EntityStore> target, String targetNode)
static AttachedBeam toEntity(int beamIndex, float scale, String sourceNode, Vector3fc sourceOffset, Ref<EntityStore> target, String targetNode, Vector3fc targetOffset)
static AttachedBeam toEntity(int beamIndex, float sourceScale, float targetScale, String sourceNode, Vector3fc sourceOffset, Ref<EntityStore> target, String targetNode, Vector3fc targetOffset)

// to a fixed world position
static AttachedBeam toPosition(int beamIndex, float scale, String sourceNode, Vector3dc target)
static AttachedBeam toPosition(int beamIndex, float sourceScale, float targetScale, String sourceNode, Vector3dc target)
static AttachedBeam toPosition(int beamIndex, float scale, String sourceNode, Vector3fc sourceOffset, Vector3dc target)
static AttachedBeam toPosition(int beamIndex, float sourceScale, float targetScale, String sourceNode, Vector3fc sourceOffset, Vector3dc target)

// to the centre of a block: toPosition at (x + 0.5, y + 0.5, z + 0.5)
static AttachedBeam toBlock(int beamIndex, float scale, String sourceNode, int x, int y, int z)
static AttachedBeam toBlock(int beamIndex, float sourceScale, float targetScale, String sourceNode, int x, int y, int z)

boolean isValid()   // true for a position beam; for an entity beam, whether the target Ref is still valid
```

`beamIndex` is the `Beam` store index. Get it with `Beam.getAssetMap().getIndex(id)`, which returns
`Integer.MIN_VALUE` for an id that is not loaded, or with `getIndexOrDefault(id, -1)` as the walkthrough
below does. A position target never goes stale. `toPosition` with a `targetOffset` is not offered:
the position factories always pass a zero target offset and a `null` target node.

### Walkthrough: tethers from Java

A complete helper class, compile-checked against the 0.7.2 jar. Every method uses the `Store`
directly, so call them on the world thread and outside a system's tick (from a command, or inside
`world.execute(...)`).

```java
package com.example.beams;

import com.hypixel.hytale.builtin.beam.AttachedBeam;
import com.hypixel.hytale.builtin.beam.BeamComponent;
import com.hypixel.hytale.builtin.beam.asset.Beam;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.ArrayList;
import java.util.List;
import org.joml.Vector3d;

/** Beam helpers. Every method touches the Store, so call them on the world thread. */
public final class Tethers {
    private Tethers() {
    }

    /** The index an AttachedBeam carries, or -1 when no Beam asset has this id. */
    public static int beamIndex(String beamId) {
        return Beam.getAssetMap().getIndexOrDefault(beamId, -1);
    }

    /** Add a beam from source to target, keeping any beams source already has. */
    public static boolean tether(Store<EntityStore> store, Ref<EntityStore> source,
                                 Ref<EntityStore> target, String beamId) {
        int index = beamIndex(beamId);
        if (index < 0 || !source.isValid() || !target.isValid()) {
            return false;
        }
        BeamComponent beams = store.ensureAndGetComponent(source, BeamComponent.getComponentType());
        beams.add(AttachedBeam.toEntity(index, 0.25f, null, target, null));
        return true;
    }

    /** Remove every beam from source that ends at target. */
    public static int untether(Store<EntityStore> store, Ref<EntityStore> source, Ref<EntityStore> target) {
        BeamComponent beams = store.getComponent(source, BeamComponent.getComponentType());
        if (beams == null) {
            return 0;
        }
        List<AttachedBeam> ending = new ArrayList<>();
        for (AttachedBeam beam : beams.getBeams()) {
            if (target.equals(beam.targetEntity())) {
                ending.add(beam);
            }
        }
        ending.forEach(beams::remove);
        if (beams.isEmpty()) {
            store.removeComponentIfExists(source, BeamComponent.getComponentType());
        }
        return ending.size();
    }

    /** A free-standing vertical beam that despawns after the given number of seconds. */
    public static Ref<EntityStore> pillar(Store<EntityStore> store, Vector3d base, double height,
                                         String beamId, float seconds) {
        int index = beamIndex(beamId);
        if (index < 0) {
            return null;
        }
        Vector3d top = new Vector3d(base).add(0.0, height, 0.0);
        return BeamComponent.spawn(store, base, seconds, AttachedBeam.toPosition(index, 0.5f, null, top));
    }
}
```

`tether` uses `ensureAndGetComponent` and `add`, the way `/beam entity` does, so it appends to an
existing list where `AttachBeam` would fail. `untether` removes the component once the list is empty.
That matters if an `AttachBeam` may later run on the same entity, because an empty `BeamComponent`
still blocks it.

---

## How beams reach clients

`BeamSystems.Tracker` is an `EntityTickingSystem` in `EntityTrackerSystems.QUEUE_UPDATE_GROUP`. Its
query is the entity tracker's `Visible` component plus `BeamComponent`. Each tick, for each such
entity, it:

1. calls `removeInvalid()`, which drops every beam whose target entity is gone;
2. builds a `BeamsUpdate` if the list changed since the last send, or if a viewer has just started
   seeing the entity;
3. queues that update to every viewer when the list changed, or else only to the new viewers.

The update carries the whole list, one `BeamInstance` per beam, with the target entity given by its
`NetworkId`. A beam whose target entity has no `NetworkId` is **left out of the packet** without a
log line, though it stays in the component.

`BeamSystems.Remove` is a `RefChangeSystem` on `BeamComponent`. When the component is removed, it
queues a removal of `ComponentUpdateType.Beams` to every viewer, which clears the beams on their
clients.

The asset side is separate. `BeamPacketGenerator` sends every `Beam` as `UpdateBeamConfigs` (packet
id 93), keyed by index, on join and whenever beam assets are added, changed or removed. A removed
`Beam` is replaced by `Beam.getUnknownFor(id)`, which has no texture, and clients get an empty
`BeamConfig` at its index.

The wire caps match the component. `BeamsUpdate` rejects more than 64 beams on both write and read
(`ProtocolException.arrayTooLong("Beams", n, 64)`). Each node name is written as ASCII of at most 96
bytes. `PacketIO.writeVarAsciiString` encodes it with `String.getBytes(US_ASCII)`, which replaces
every character outside ASCII with `?` without an error, so such a name reaches the client altered.
A name longer than 96 bytes throws `ProtocolException("String exceeds max bytes: <n> > 96")` when
the update is serialized. Scales and offsets must be finite (`PacketIO.requireFinite`). Nothing checks a node
name against the model on the server. What the client does with a node name the model lacks was not
verified.

---

## The /beam command

`BeamCommand` registers `/beam`, a command collection in the `hytale:WorldEditor` permission group
(`setPermissionGroups("hytale:WorldEditor")`). Every subcommand is a player command and acts on the
sender. It defaults to a scale of `0.25`, unlike the interaction's `1.0`. Optional arguments are
`--name=value`.

| Subcommand | Arguments | Does |
|------------|-----------|------|
| `/beam entity <beam>` | `--entity` (an entity UUID; default: the entity in view), `--sourceNode`, `--targetNode`, `--scale`, `--targetScale` (default: `scale`) | Adds a beam from you to the entity. Without `--entity` and with no entity in view it replies `No entity in view! Either look at an entity or use --entity=<uuid>` (`server.commands.errors.no_entity_in_view`). A UUID that names no entity in your world replies `Target <uuid> not found` |
| `/beam position <beam>` | `--height` (default `5.0`, must be > 0), `--sourceNode`, `--scale`, `--targetScale` | Adds a beam from you to the point `height` blocks above your feet |
| `/beam spawn <beam>` | `--length` (default `8.0`, must be > 0), `--lifetime` (seconds, default `30.0`, must be > 0), `--scale`, `--targetScale` | Spawns a free-standing vertical beam at your position via `BeamComponent.spawn` |
| `/beam clear` | none | Removes your `BeamComponent`: "Removed your beams." or "You have no beams to remove." |

`entity` and `position` reply "Attached the beam." and `spawn` replies "Spawned the beam." (all from
`Server/Languages/en-US/server.lang`). Because `entity` and `position` add to your own list, the beams
stay on you until `/beam clear`, a restart, or the target entity going away.

---

## Gotchas & Errors

- **Symptom:** a second `AttachBeam` on the same entity breaks the chain, or a server log shows
  `Entity already contains component type` → `AttachBeam` queues `addComponent` of a new
  `BeamComponent`, and `Store.addComponent` throws `IllegalArgumentException("Entity already contains component type: …")`
  when the entity already has one. That includes an empty list left by `clear()`, and beams from
  `/beam entity` on a player. The exception is thrown when the command buffer is applied; what it
  does to the running chain and tick was not measured. Fix: run `AttachBeam` on a fresh entity (a
  projectile), or add beams from Java with `ensureAndGetComponent(...).add(...)`.
- **Symptom:** the beam loops back on its own entity, or never appears → `TargetEntity` defaults to
  `User`, which is the source entity too. Set `"TargetEntity": "Owner"` (or `"Target"`). With
  `Target` and no target entity on the chain, `AttachBeam` does nothing and logs nothing.
- **Symptom:** an interaction asset with `AttachBeam` fails to load → `BeamConfig` is missing (the
  engine rejects its omission) or names no loaded `Beam`:
  `Asset '<id>' of type com.hypixel.hytale.builtin.beam.asset.Beam doesn't exist!`. Without the
  `Hytale:Beam` plugin, the `AttachBeam` type itself is unregistered.
- **Symptom:** a beam asset is rejected → `TexturePath` is missing, outside `Beams/` and
  `Trails/`, not a `.png`, or not an existing common asset. The messages are listed under
  [The Beam asset](#the-beam-asset).
- **Symptom:** the server log shows `Cannot add more than 64 beams to an entity` → `add` refused a
  65th beam and dropped it. `set` keeps the first 64 and logs
  `Dropped <n> beams over the limit of 64`.
- **Symptom:** `IllegalArgumentException: A beam needs exactly one of a target entity or a target position`
  → the `AttachedBeam` constructor was called with both or neither. Use the `toEntity` /
  `toPosition` / `toBlock` factories.
- **Symptom:** `IllegalStateException: Store is currently processing! Ensure you aren't calling a store method from a system.`
  → `BeamComponent.spawn` (which calls `store.addEntity`) or `ensureAndGetComponent` was called
  inside a system's tick. Do it from a command or `world.execute(...)`, or build the entity through
  the system's `CommandBuffer` yourself.
- **Symptom:** beams vanish after a restart or chunk reload → `BeamComponent` has no codec and is
  never saved. `BeamComponent.spawn` entities are also marked non-serialized. Re-create beams when
  the entity loads.
- **Symptom:** a beam to an entity never shows, while the entity itself does → the target has no
  `NetworkId`, so `Tracker` leaves that beam out of every update without logging.
- **Symptom:** a beam disappears on its own → its target entity was removed. `removeInvalid()` prunes
  such beams on the next tick (only on entities a viewer can see).
- **Symptom:** a beam asset's texture shows on a beam but not on a trail → `Beams/` is accepted by
  beams only; `Trail` assets require `Trails/`.
- **Symptom:** a chain does not interrupt the one it names, and the log shows
  `Unused key(s) in '<id>' file <path>: Interrupting` → `Interrupting` sits at the top level of the
  root interaction, beside `Interactions`. `RootInteraction` reads it only inside `Rules`. Write
  `"Rules": { "Interrupting": ["ProjectileSpawn"] }`, as the Hookshot's `ProjectileMiss` does; its
  `ProjectileHit` carries the top-level form, which does nothing.
- **Note:** the builder tools' laser pointer (`LaserPointerOperation`, the `BuilderToolLaserPointer`
  packet) is a separate mechanism and uses none of these classes.

---

## Related

- [Interactions API](interactions.md#attachbeam) — the `AttachBeam` row in the type registry
- [SimpleInstantInteraction](interactions.md#simpleinstantinteraction) — the keys `AttachBeam` inherits
- [Projectiles API](projectiles.md) — projectile configs and the `ProjectileSpawn` chain both shipped beams run on
- [Abilities and Runes](abilities.md) — `LaunchAbilityProjectile`, which fires the Chain Hook projectile
- [Components (ECS) API](components.md) — `Store`, `CommandBuffer`, and why store methods are refused inside systems
- [Commands API](commands.md) — `AbstractPlayerCommand` and `--name=value` arguments
- [Permissions API](permissions.md) — permission groups such as `hytale:WorldEditor`
