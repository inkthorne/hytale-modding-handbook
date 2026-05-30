---
title: "Trigger Volumes"
description: "Hytale's Trigger Volume system — author scripted encounters as JSON effect assets, and extend it from a plugin with custom TriggerEffect and TriggerCondition types registered against the effect/condition codecs."
seo:
  type: TechArticle
---

# Trigger Volumes

**Doc type:** Java API + JSON asset format · **Assets:** `Server/TriggerVolumes` · **Verified against 0.5.3**

New in Update 5. A **trigger volume** is a 3D region (box, sphere, or cylinder) that runs a list of **effects**
when something happens inside it — a player enters, a creature leaves, a block breaks, a tick elapses. Designers
place and configure volumes in-world with the Trigger Volume Tool (no code), but the system was **built with mod
support in mind**: a plugin can register its own effect and condition types so they show up in the tool and can be
used from JSON, exactly like the built-ins.

This page covers the two things a plugin author cares about:
1. **Authoring effect assets** — the JSON shape volumes run (`Server/TriggerVolumes/Effects/<id>.json`).
2. **Extending the system** — writing a custom `TriggerEffect` / `TriggerCondition` in Java and registering it.

It also documents the runtime API (`TriggerVolumeManager`, the `TriggerVolume` component, `TriggerVolumeEvent`,
shapes) for reading or driving volumes programmatically.

## Architecture
```
com.hypixel.hytale.builtin.triggervolumes
├── effect
│   ├── TriggerEffect        abstract — subclass + override execute(TriggerContext); registered in TriggerEffect.CODEC
│   ├── TriggerCondition     abstract — subclass + override test(TriggerContext);    registered in TriggerCondition.CODEC
│   ├── TriggerContext       what an effect/condition receives at fire time (entity, store, volume, event, block…)
│   ├── TriggerEventType     ENTER / EXIT / TICK / TAG_ADDED / TAG_REMOVED / BLOCK_PLACED / BLOCK_BROKEN
│   ├── TriggerVolumeCodecs  tolerant array codecs for the effect / condition lists in JSON
│   └── builtin.*            the ~22 shipped effects + 8 conditions (Type names below)
├── asset.TriggerEffectAsset reusable effect bundle loaded from Server/TriggerVolumes/Effects/
├── component
│   ├── TriggerVolume        ECS component: shape + effects + enabled flag (one placed volume)
│   └── TriggerVolumeGroup   a named group of volumes
├── manager.TriggerVolumeManager   per-world Resource: register / lookup / enumerate volumes & groups
├── shape.{BoxShape, SphereShape, CylinderShape}  : TriggerVolumeShape
├── event.TriggerVolumeEvent       IEvent<String> fired when a volume triggers
├── EntityTargetType        PLAYER / NPC / ITEM_DROP / PROJECTILE (who a volume reacts to)
└── command.*               the /triggervolume command family (tooling)
```

## Effect asset JSON

A `TriggerEffectAsset` is a reusable bundle of effects (and optional conditions) that a volume can run. Drop one in
`Server/TriggerVolumes/Effects/<id>.json` — in the base game or your plugin's asset pack — and volumes reference it
by id. Here is the shipped sample (`Server/TriggerVolumes/Effects/sample_bounce_pad.json`), a bounce pad that
launches and chimes when a player enters:

```json
{
  "Effects": [
    {
      "Type": "SetVelocity",
      "Event": "ENTER",
      "Velocity": { "X": 0.0, "Y": 15.0, "Z": 0.0 },
      "Additive": false
    },
    {
      "Type": "PlaySound",
      "Event": "ENTER",
      "SoundEvent": "SFX_Player_Pickup_Item",
      "Volume": 1.0,
      "Pitch": 1.5
    },
    {
      "Type": "SendMessage",
      "Event": "ENTER",
      "Message": "server.builderTools.triggerVolumes.sample.bounce"
    }
  ],
  "TargetTypes": ["Player"]
}
```

### Top-level fields

| Key | Type | Description |
|-----|------|-------------|
| `Effects` | array | Effects to run. Tolerant array — an unknown/malformed entry is skipped, not fatal. |
| `Conditions` | array | Optional gate (see [Conditions](#conditions)). All must pass for the effects to run. |
| `RejectionEffects` | array | Optional effects run when a condition **fails** (e.g. a "denied" message). |
| `ConditionTiming` | enum | When conditions are evaluated relative to the effects (`ConditionTiming`). |
| `TargetTypes` | array | Which entity kinds the volume reacts to. The sample uses `"Player"`; values map to [`EntityTargetType`](#entitytargettype). |

### Effect entry fields

Every effect entry carries the base keys below (from `TriggerEffect`), plus its own type-specific fields:

| Key | Type | Description |
|-----|------|-------------|
| `Type` | string | **Discriminator** — selects the effect type (table below). Required. |
| `Event` | `TriggerEventType` | Which event fires this effect (`ENTER`, `EXIT`, …). |
| `Interval` | float | For `TICK` effects: seconds between repeats. |
| `Delay` | float | Seconds to wait after the event before running. |

## Built-in effect types

The `Type` value selects the effect. These are the names registered by the built-in `TriggerVolumesPlugin`
(verified against the jar) — type-specific fields aside from the base keys above are not all enumerated here;
inspect the corresponding `…effect.builtin.<Name>Effect` class or the in-game inspector for each.

| `Type` | Effect | Notes |
|--------|--------|-------|
| `SetVelocity` | Launch/push the entity | `Velocity` (Vector3d), `Additive` (bool) |
| `Teleport` | Move the entity | |
| `SendMessage` | Send a chat message | `Message` (i18n key or text) |
| `PlaySound` | Play a sound | `SoundEvent`, `Volume`, `Pitch` |
| `PlayVfx` | Spawn a particle system | `ParticleSystem` |
| `SetWeather` | Change weather | `Weather` |
| `SetMusic` | Set music | `MusicContainer` |
| `ShowEventTitle` | Show an on-screen title | |
| `EntityEffect` | Apply/remove a status effect | `EntityEffect` (see [effects-stats](effects-stats.md)) |
| `DamageEntity` | Deal damage | |
| `GiveItem` | Give an item | `Item` |
| `PlaceBlock` | Place a block | `BlockType` |
| `ReplaceBlockType` | Swap block types in range | `FromBlockTypes`, `ToBlockType` |
| `ControlDoors` | Open/close doors | |
| `PastePrefab` | Paste a prefab | `Prefab` / `PrefabList` |
| `TriggerNpcMarkers` | Activate NPC spawn markers | `MarkerType`, `ManualSpawnMarker` |
| `RunRootInteraction` | Run an interaction graph | `RootInteraction` (see [interactions](interactions.md)) |
| `SetGameMode` | Change the entity's game mode | |
| `ModifyTags` | Add/remove volume tags | |
| `EnableVolume` / `DisableVolume` / `DeleteVolume` | Toggle/remove another volume | by tag |

## Conditions

Conditions gate an asset's effects: list them under `Conditions`, and the effects run only if every condition's
`test(...)` passes (otherwise `RejectionEffects`, if any, run). Like effects they carry an `Event` and a `Type`.

| `Type` | Condition |
|--------|-----------|
| `PermissionCondition` | Entity (player) has a permission |
| `CooldownCondition` | Enforce a per-volume cooldown |
| `GameModeCondition` | Entity is in a given game mode |
| `ItemCondition` | Entity holds / has an item |
| `RandomChanceCondition` | Random roll |
| `PlayerCountCondition` | Number of players in the volume |
| `TagCondition` | Volume has a tag |
| `BlockTypeCondition` | Block at the event position is a given type |

> Note the naming asymmetry: **effect** type names drop the `Effect` suffix (`SendMessageEffect` → `"SendMessage"`),
> while **condition** type names keep the full class name (`PermissionCondition` → `"PermissionCondition"`).

## TriggerEventType

The event that fires an effect/condition (field `Event`):

| Value | Fires when |
|-------|-----------|
| `ENTER` | A target entity enters the volume |
| `EXIT` | A target entity leaves the volume |
| `TICK` | Repeatedly while a target is inside (paced by `Interval`) |
| `TAG_ADDED` / `TAG_REMOVED` | A tag is added to / removed from the volume |
| `BLOCK_PLACED` / `BLOCK_BROKEN` | A block is placed / broken inside the volume |

## EntityTargetType

Which entity kinds a volume reacts to (`TargetTypes`): `PLAYER`, `NPC`, `ITEM_DROP`, `PROJECTILE`. (The sample pack
writes `"Player"`; use the name matching the inspector/your target build.)

---

## Extending: a custom effect in Java

The effect list is backed by a `CodecMapCodec<TriggerEffect>` keyed on the `Type` string (`TriggerEffect.CODEC`).
Register your own type and it becomes usable from any effect asset's JSON — and selectable in the in-game tool.

A custom effect:
1. **extends `TriggerEffect`** and overrides `execute(TriggerContext)`,
2. exposes a **`BuilderCodec`** describing its JSON fields, and
3. is **registered** into `TriggerEffect.CODEC` during your plugin's `setup()`.

```java
import com.hypixel.hytale.builtin.triggervolumes.effect.TriggerEffect;
import com.hypixel.hytale.builtin.triggervolumes.effect.TriggerContext;
import com.hypixel.hytale.codec.builder.BuilderCodec;

public class GreetEffect extends TriggerEffect {
    // A BuilderCodec describing this effect's JSON fields (see codecs.md). The base
    // keys (Type/Event/Interval/Delay) are contributed by TriggerEffect.BASE_CODEC.
    public static final BuilderCodec<GreetEffect> CODEC = /* …build it here… */ null;

    private String greeting = "Welcome!";

    public GreetEffect() {}   // no-arg ctor required by the codec

    @Override
    public void execute(TriggerContext ctx) {
        // ctx gives you the triggering entity, the world store, the volume, the
        // event type, and (for block events) the block position/id.
        var ref   = ctx.getEntityRef();
        var store = ctx.getStore();
        // …apply your effect to the entity here…
    }
}
```

Register it during plugin setup so the codec can resolve `"Type": "Greet"`:

```java
@Override
protected void setup() {
    // typeId, implementing class, field codec
    TriggerEffect.CODEC.register("Greet", GreetEffect.class, GreetEffect.CODEC);
}
```

Authors can now use it in any effect asset:

```json
{ "Effects": [ { "Type": "Greet", "Event": "ENTER", "Greeting": "Hi there" } ], "TargetTypes": ["Player"] }
```

> Register **before** worlds/effect assets load (in `setup()`). The base game registers its built-ins the same way
> from `TriggerVolumesPlugin`, logging `Registered trigger effect type '<id>' (<class>)`.

### Custom conditions

Conditions follow the identical pattern against `TriggerCondition.CODEC`: subclass `TriggerCondition`, override
`boolean test(TriggerContext)` (return `true` to allow the effects), optionally `applyOnAccept(TriggerContext)`, and
register `TriggerCondition.CODEC.register("MyCondition", MyCondition.class, MyCondition.CODEC)`.

### TriggerContext

What `execute`/`test` receive at fire time:

| Method | Returns | Description |
|--------|---------|-------------|
| `getEntityRef()` | `Ref<EntityStore>` | The triggering entity (player/NPC/…) |
| `getStore()` | `Store<EntityStore>` | The world's entity store, for component access |
| `getEventType()` | `TriggerEventType` | Which event fired |
| `getVolume()` | `VolumeEntry` | The volume that fired |
| `getSpatialVolumes()` | `List<VolumeEntry>` | Other volumes overlapping the point |
| `getTagKey()` / `getTagValue()` | `String` | For `TAG_ADDED` / `TAG_REMOVED` events |
| `getBlockPosition()` | `Vector3d` | For `BLOCK_PLACED` / `BLOCK_BROKEN` events |
| `getBlockId()` | `String` | The block involved, for block events |

> The effect/condition instance is shared across firings — keep per-entity state out of fields. `TriggerEffect` and
> `TriggerCondition` provide an `onEntityExit(UUID)` hook for cleaning up any per-entity tracking you do keep.

---

## Runtime API

### TriggerVolume (component)

The ECS component on a placed volume entity. A `TriggerVolume` bundles a [shape](#shapes), a list of
`TriggerEffect`s, an enabled flag, and an optional group link.

Its `ComponentType` is **owned by the TriggerVolumes plugin**, not exposed as a static on the class — obtain it
from that plugin via `TriggerVolumesPlugin#getTriggerVolumeComponentType()` (look the plugin up through the plugin
manager / a declared dependency), then read the component normally:

```java
ComponentType<EntityStore, TriggerVolume> type = triggerVolumes.getTriggerVolumeComponentType();
TriggerVolume tv = store.getComponent(ref, type);

TriggerVolumeShape shape = tv.getShape();
List<TriggerEffect> effects = tv.getEffects();
boolean enabled = tv.isEnabled();
tv.setEnabled(false);                 // disable without deleting
String group = tv.getGroupLinkId();   // group membership, if any
```

### TriggerVolumeManager (per-world resource)

A world-scoped `Resource` that owns the live volume registry. Use it to enumerate or look up volumes by id, or to
register/unregister them programmatically.

```java
TriggerVolumeManager mgr = /* world resource */;
Collection<VolumeEntry> all = mgr.getVolumes();
VolumeEntry v = mgr.getVolume("my-volume-id");
boolean exists = mgr.hasVolume("my-volume-id");
mgr.register("my-volume-id", volumeEntry);
mgr.unregister("my-volume-id");
```

### TriggerVolumeEvent

Fired (as an `IEvent<String>`, keyed by world name) whenever a volume triggers — observe it to react to volumes
from your own systems without authoring an effect:

```java
// getWorldName(), getTriggerEventType(), getVolumeId(),
// getEntityRef(), getEntityUuid(), getVolumeTagIndexes()
```

### Shapes

`TriggerVolumeShape` is the abstract base (a `CodecMapCodec`, so shapes are also extensible) with three built-ins —
`BoxShape`, `SphereShape`, `CylinderShape`. Key methods: `contains(point, origin)`, `getBoundingRadius()`,
`getWorldAABB(origin, minOut, maxOut)`, `rotateInPlace(degrees)`, `copy()`.

---

## Commands (tooling)

The `/triggervolume` family backs the in-game tool and is handy for testing from chat. A selection (notable ones):

| Command | Purpose |
|---------|---------|
| `/triggervolume create` | Create a volume from the current selection/tool |
| `/triggervolume list` | List volumes in the world |
| `/triggervolume info` | Inspect a volume |
| `/triggervolume assigneffect` | Attach an effect asset to a volume |
| `/triggervolume enable` / `disable` | Toggle a volume (also `enabletag` / `disabletag` by tag) |
| `/triggervolume test` | Fire a volume's effects for testing |
| `/triggervolume remove` | Delete a volume |

---

## Gotchas & Errors

- **Effect/condition lists are tolerant.** `TriggerVolumeCodecs.TOLERANT_EFFECTS` / `TOLERANT_CONDITIONS` skip an
  entry that fails to decode rather than failing the whole asset. A typo'd `Type` silently drops that one effect —
  check the server log for the load, not just the absence of an error.
- **Register custom types early.** A volume that names a `Type` you haven't registered loses that effect; register
  in `setup()` before worlds load.
- **Missing effect asset.** A volume referencing an effect-asset id that doesn't exist logs
  `Volume '<id>' references missing effect asset '<assetId>'` and runs nothing — confirm the asset id matches the
  file under `Server/TriggerVolumes/Effects/`.
- **`Type` is the discriminator key**, not `"Effect"` or `"Name"`. The base codec also reads `Event`, `Interval`,
  `Delay`; everything else is type-specific.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
