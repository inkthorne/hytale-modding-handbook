---
title: "Trigger Volumes"
description: "Hytale's Trigger Volume system — author scripted encounters as JSON effect assets, and extend it from a plugin with custom TriggerEffect and TriggerCondition types registered against the effect/condition codecs."
seo:
  type: TechArticle
---

# Trigger Volumes

**Doc type:** Java API + JSON asset format · **Assets:** `Server/TriggerVolumes` · **Verified against 0.6.3**

New in Update 5, substantially extended in 0.6.3 (rules, signals, more events/effects). A **trigger volume** is a
3D region (box, sphere, or cylinder) that runs a list of **effects** when something happens inside it — a player
enters, a creature leaves, a block breaks or is used, a signal arrives, an entity dies, a tick elapses. Designers
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
│   ├── TriggerRule          abstract (0.6.3+) — passive rule active while inside the volume; TriggerRule.CODEC
│   ├── TriggerContext       what an effect/condition receives at fire time (entity, store, volume, event, block…)
│   ├── TriggerEventType     ENTER / EXIT / TICK / TAG_ADDED / TAG_REMOVED / BLOCK_PLACED / BLOCK_BROKEN + (0.6.3)
│   │                        VOLUME_CREATE / BLOCK_USED / SIGNAL_RECEIVED / ENTITY_DIED — an open registry, not an enum
│   ├── EffectOrigin, SignalTag  (0.6.3+) origin selector for positional effects; key/value signal payload
│   ├── TriggerVolumeCodecs  tolerant array codecs for the effect / condition / rule lists in JSON
│   └── builtin.*            29 shipped effects, 10 conditions, 11 rules (Type names below)
├── asset.TriggerEffectAsset reusable effect bundle loaded from Server/TriggerVolumes/Effects/
├── component
│   ├── TriggerVolume        ECS component: shape + effects + enabled flag (one placed volume)
│   ├── TriggerVolumeGroup   a named group of volumes
│   └── IgnoreTriggerVolumes (0.6.3+) marker component: entity is invisible to volumes
├── manager.TriggerVolumeManager   per-world Resource: register / lookup / enumerate volumes & groups
├── shape.{BoxShape, SphereShape, CylinderShape}  : TriggerVolumeShape
├── event.TriggerVolumeEvent       IEvent<String> fired when a volume triggers
├── EntityTargetType        PLAYER / NPC / ITEM_DROP / PROJECTILE (who a volume reacts to)
├── interaction.*           (0.6.3+) SpawnTriggerVolume / SignalNearbyVolumes / DestroyTaggedVolumes interaction types
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
| `Rules` | array | 0.6.3+ — passive [rules](#rules) active while an entity is inside (tolerant array, `TriggerVolumeCodecs.TOLERANT_RULES`). |
| `ConditionTiming` | enum | When conditions are evaluated relative to the volume's activation delay: `BEFORE_VOLUME_DELAY` or `AFTER_VOLUME_DELAY` (default). |
| `TargetTypes` | array | Which entity kinds the volume reacts to. The sample uses `"Player"`; values map to [`EntityTargetType`](#entitytargettype). |
| `IncludeVolumeSettings` | bool | 0.6.3+ — when `true`, the asset also carries per-volume settings that are copied onto any volume it is assigned to: `VolumeTags`, `RejectionDelayMode`, `Cooldown` (s), `CooldownMode`, `ActivationDelay` (s), `ProjectileSource`, `KeepLoaded`, `RotateEffectsOnPaste`, `CancelDelayedOnExit`. Ignored (and not written back) when `false`. |

### Effect entry fields

Every effect entry carries the base keys below (from `TriggerEffect`), plus its own type-specific fields:

| Key | Type | Description |
|-----|------|-------------|
| `Type` | string | **Discriminator** — selects the effect type (table below). Required. |
| `Event` | `TriggerEventType` | Which event fires this effect (`ENTER`, `EXIT`, …). |
| `Interval` | float | For `TICK` effects: seconds between repeats. |
| `Delay` | float | Seconds to wait after the event before running. |
| `Entry` | int | 0.6.3+ — groups conditions with the effects they gate: a condition only applies to effects/rejection effects carrying the same `Entry` number (default `0`). Also on conditions. |

## Built-in effect types

The `Type` value selects the effect. These are the names registered by the built-in `TriggerVolumesPlugin`
(verified against the 0.6.3 jar). The JSON keys listed are each effect's codec keys (enum values in
`UPPER_SNAKE`); for semantics read the corresponding `…effect.builtin.<Name>Effect` class or use the in-game inspector.

| `Type` | Effect | Type-specific JSON keys |
|--------|--------|-------------------------|
| `SetVelocity` | Launch/push the entity | `Velocity` (Vector3d), `Additive` (bool), `RelativeMode` (`ABSOLUTE` / `VOLUME_ORIGIN` / `HORIZONTAL_FACING` / `FULL_LOOK`) |
| `Teleport` | Move the entity | `Position`, `World`, `ResetVelocity`, `RelativeToEntity`, `RelativeToVolume`, `UseRotation`, `Rotation` |
| `SendMessage` | Send a chat message | `Message` (i18n key or text), `Recipient` (`TRIGGERING_PLAYER` / `NEAREST_PLAYER` / `PLAYERS_IN_VOLUME` / `ALL_PLAYERS`) |
| `PlaySound` | Play a sound | `SoundEvent`, `Volume`, `Pitch`, `Location` (`VOLUME_CENTER` / `ENTITY` / `EVENT` / `PLAYER`), `Offset` |
| `PlayVfx` | Spawn a particle system | `ParticleSystem`, `Offset`, `Anchor` (`VOLUME` / `ENTITY` / `EVENT`), `Scale`, `Rotation`, `Duration` |
| `CancelParticles` | 0.6.3+ — stop running particle systems | `ParticleSystems`, `Instant` |
| `SetWeather` | Change weather | `Weather`, `PlayerOnly`, `ResetWeather` |
| `SetMusic` | Set music | `MusicContainer`, `ClearMusic` |
| `Time` | 0.6.3+ — pause/resume/set the world clock | `Mode` (`PAUSE` / `RESUME` / `SET`), `TargetHour`, `DurationSeconds`, `Forward`, `PauseOnComplete`, `PlayerOnly` |
| `ShowEventTitle` | Show an on-screen title | `PrimaryTitle`, `SecondaryTitle`, `IsMajor`, `Icon`, `Duration`, `FadeInDuration`, `FadeOutDuration` |
| `EntityEffect` | Apply/remove a status effect | `Effect` (the entity-effect id — **not** `EntityEffect`; see [effects-stats](effects-stats.md)), `Mode` (`APPLY` / `REMOVE`), `Duration` |
| `DamageEntity` | Deal damage | `Mode` (`FLAT` / `PERCENT_MAX` / `PERCENT_CURRENT`), `Amount` |
| `RemoveEntities` | 0.6.3+ — kill or delete entities in the volume | `Mode` (`KILL` / `REMOVE`), `IncludeNpcs`, `IncludePlayers`, `IgnoreInvulnerability`, `Roles`, `MaxCount` |
| `GiveItem` | Give an item | `Item`, `Quantity`, `OverflowBehavior` (`DROP_REMAINDER` / `IGNORE_REMAINDER` / `REQUIRE_FULL_STACK`) |
| `PlaceBlock` | Place a block | `BlockType`, `BlockState`, `Position`, `Origin`, `ReplaceMode` (`ALWAYS` / `ONLY_AIR`), `Rotation`, `Pitch`, `Roll` |
| `ReplaceBlockType` | Swap block types in range | `FromBlockTypes`, `FromBlockState`, `ToBlockType`, `ToBlockState`, `Bounds` (`SHAPE` / `AABB`), `X`, `Y`, `Z`, `Offset`, `Origin`, `Rotation`, `Pitch`, `Roll` |
| `ControlDoors` | Open/close doors | `Action` |
| `PastePrefab` | Paste a prefab | `Prefab` / `PrefabList`, `Position`, `Origin`, `Rotation`, `ShowParticles` |
| `TriggerNpcMarkers` | Activate NPC spawn markers | `MarkerType`, `Range`, `MatchTag`, `Radius`, `Center` |
| `SpawnNpc` | 0.6.3+ — spawn NPCs directly | `NpcType`, `GroupType`, `Origin`, `Offset`, `Count`, `Yaw` |
| `PlayAnimation` | 0.6.3+ — play an NPC animation | `NpcType`, `Animation`, `Target` (`TRIGGERING_ENTITY` / `NPCS_IN_VOLUME`), `Duration`, `Stop` |
| `RunRootInteraction` | Run an interaction graph | `RootInteraction`, `InteractionType`, `EquipSlot` (see [interactions](interactions.md)) |
| `SetGameMode` | Change the entity's game mode | `GameMode` |
| `ModifyTags` | Add/remove volume tags | `Operation` (`SET` / `REMOVE` / `INCREMENT` / `TOGGLE` / `REPLACE` / `APPEND`), `TagKey`, `TagValue`, `MatchKey`, `MatchValue`, `Radius`, `Center` |
| `SendSignal` | 0.6.3+ — raise `SIGNAL_RECEIVED` on matching volumes | `MatchKey`, `MatchValue`, `Radius`, `Center`, `SignalKeys`, `SignalValues` |
| `ModifyRules` | 0.6.3+ — edit a volume's rule list at runtime | `Operation` (`SET` / `APPEND` / `SET_FIELD` / `REMOVE` / `SET_RULES_ACTIVE`), `Rule`, `FieldKey`, `Active` |
| `EnableVolume` / `DisableVolume` / `DeleteVolume` | Toggle/remove other volumes | by tag: `MatchKey`, `MatchValue`, `Radius`, `Center` (`VOLUME` / `ENTITY` / `EVENT`); `DeleteVolume` adds `DeleteGroup` |

`Origin` keys take an `EffectOrigin`: `VOLUME_ORIGIN`, `ENTITY`, `EVENT`, or `WORLD_ABSOLUTE` (0.6.3+).

### The `ShowEventTitle` interaction is a different type with the same name

`Interaction.CODEC` also registers a `ShowEventTitle`, and it is **not** the effect in the table
above. The two classes are
`com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.ShowEventTitleInteraction`
and the `ShowEventTitleEffect` behind this page's row; they differ in their key names, so an asset
written for one will not decode as the other. It is documented here rather than beside the other
interactions precisely because this is where the confusion happens.

**The key sets nearly match, which is worse than differing.** Four of the eight names are shared
verbatim; three differ only by a trailing `S`; and the interaction adds one the effect has no
equivalent for:

| Effect (`ShowEventTitleEffect`) | Interaction (`ShowEventTitleInteraction`) |
|---|---|
| — | `Target` |
| `PrimaryTitle` | `PrimaryTitle` |
| `SecondaryTitle` | `SecondaryTitle` |
| `IsMajor` | `IsMajor` |
| `Icon` | `Icon` |
| `Duration` | `DurationS` |
| `FadeInDuration` | `FadeInDurationS` |
| `FadeOutDuration` | `FadeOutDurationS` |

> **Gotcha — copying the effect block on this page into an interaction *works*, by coincidence, until
> someone changes a timing value.** The four shared keys transfer. The three `…Duration` keys are
> silently dropped as unknown, and the interaction falls back to its own defaults — which are `4.0`,
> `1.5` and `1.5`, exactly the values the shipped effect block writes. So the title appears and
> behaves correctly, and nothing indicates that three keys were discarded. The failure surfaces later
> and somewhere else: an author edits `Duration` on what is now an interaction, sees no change, and
> has no reason to suspect the key name. The reverse direction fails the same way. This is not the
> usual "same string, different registry" collision — here the *keys* nearly match, and so do the
> defaults.

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.ShowEventTitleInteraction`

Codec doc: "Shows an event title to the players of one world or of the whole universe." Extends
[SimpleInstantInteraction](interactions.md#simpleinstantinteraction).

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `Target` | enum | `World` | **Required** (`Validators.nonNull()`) *despite having a default* — the field initialises to `World`, but the key must still be written. `World` shows the title to every player of the world the interaction runs in; `Universe` to every player of every live world. Those two are the whole enum |
| `PrimaryTitle` | message | — | **Required** (`Validators.nonNull()`). The main line |
| `SecondaryTitle` | message | *empty* | The line below it; omit for a one-line title |
| `IsMajor` | boolean | `false` | Whether the client presents this as a major event rather than a minor one |
| `Icon` | string | — | Icon shown beside the title; omit for none |
| `DurationS` | float | `4.0` | Seconds on screen **after** the fade in. Validated `>= 0` |
| `FadeInDurationS` | float | `1.5` | Seconds to fade in. Validated `>= 0` |
| `FadeOutDurationS` | float | `1.5` | Seconds to fade out. Validated `>= 0` |

**No shipped asset uses the interaction**, so the table above rests on its codec alone. The single
file in `Assets.zip` carrying `"Type": "ShowEventTitle"` is
`Server/Prefabs/Testing/VolumeShowcase/Trigger_Volume_Showcase.prefab.json` — a trigger-volume
prefab, so it is the *effect*, and it writes all seven of the effect's keys.

The **effect** is in the opposite position: it has two independent confirmations of its key set. That
prefab is one; the other is `Server/Languages/*/server.lang`, whose
`customUI.triggerVolumeEffectEditor.field.ShowEventTitle.<Key>` entries enumerate exactly those seven
names for the in-game effect editor, in all five shipped language files. That pattern generalises —
a `customUI.<editor>.field.<Type>.<Key>` block is a shipped key-set oracle for any type with an
editor UI — and here it agrees with the codec.

**Three things in the jar answer to this name**, so a lookup by simple name has three candidates:
`Interaction.CODEC.register("ShowEventTitle", …)` in `InteractionModule`,
`TriggerEffect.CODEC.register("ShowEventTitle", …)` in `TriggerVolumesPlugin`, and a to-client
protocol packet class also called `ShowEventTitle`. Only the first two are `"Type"` values.

One more trap for anyone mining these keys: the interaction's `PrimaryTitle` and `SecondaryTitle`
are declared with the **raw** `KeyedCodec` form rather than the parameterised one, so a pattern
matching `KeyedCodec<T>` sees six of its eight keys and misses both title fields.

> **Gotcha — `Target` is required and `Universe` is not scoped to anything.** There is no radius,
> no player filter and no volume: `Universe` reaches every player of every live world on the server.
> The narrower option is `World`, and it is still every player in that world.

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
| `TagCondition` | Volume has a tag (`Source`: `EVENT` / `SELF` / `GROUP` / `RADIUS`) |
| `BlockTypeCondition` | Block at the event position is a given type (`PositionSource`: `EVENT` / `VOLUME_ORIGIN` / `ENTITY` / `WORLD_ABSOLUTE`) |
| `EntityCountCondition` | 0.6.3+ — number of entities of `EntityType` in the volume (`Comparison`: `AT_LEAST` / `AT_MOST` / `EXACTLY` / `NOT_EQUALS` / `MORE_THAN` / `LESS_THAN`, `Count`) |
| `TimeOfDay` | 0.6.3+ — world hour within `MinHour`…`MaxHour` (class `TimeOfDayCondition`; note the short `Type` name) |

> Note the naming asymmetry: **effect** type names drop the `Effect` suffix (`SendMessageEffect` → `"SendMessage"`),
> while **condition** type names keep the full class name (`PermissionCondition` → `"PermissionCondition"`) — except
> `TimeOfDayCondition`, registered as plain `"TimeOfDay"` in 0.6.3.

## Rules

A `TriggerRule` is *passive*: rather than firing on an event it stays in force for whatever is inside the volume
(the engine's systems consult `TriggerVolumeManager.hasActiveRule(position, RuleClass)` /
`getActiveRules(...)` on each guarded action). List them under `Rules`; toggle them at runtime with the
`ModifyRules` effect or `VolumeEntry.setRulesActive(boolean)`. Registered `Type` names:

| `Type` | Rule | Keys |
|--------|------|------|
| `NoBuild` / `NoDestroy` / `NoHarvest` / `NoUse` | Deny placing / breaking / harvesting / using blocks | `ExceptBlocks`, `ExceptBlockTags` (`NoDestroy` also `ExceptTools`, `ExceptToolTags`) |
| `NoDamage` | Deny damage | `EntityFilter`, `Entities`, `PvpOnly` |
| `NoDoorOpen` / `NoHeal` / `Fly` / `CreativePlacement` | Deny door use / deny healing / allow flight / creative-style placement | — |
| `DamageMultiplier` | Scale damage | `Multiplier`, `Direction` (`RECEIVED` / `DEALT` / `BOTH`), `EntityFilter`, `Entities` |
| `NoTick` | Suppress block ticking | `ScheduledTick`, `RandomTick` |

The deny rules share `AbstractDenyRule` keys `Target` (`SELF` / `OTHER` / `BOTH`), `MatchKey`, `MatchValue`, `Radius`,
`SignalKeys`, `SignalValues` — a denied action can send a signal to matching volumes. Custom rules follow the
effect pattern against `TriggerRule.CODEC` (`TriggerVolumesPlugin.registerRuleType(...)`).

## TriggerEventType

The event that fires an effect/condition (field `Event`). As of 0.6.3 `TriggerEventType` is a **registry class, not
an enum**: the built-ins are `public static final` instances, `TriggerEventType.values()` returns a `List`, and a
plugin can add its own with `TriggerVolumesPlugin.registerEventType("MY_EVENT")` (or `TriggerEventType.register`)
and raise it via the manager's `enqueue*Event(...)` methods. `TriggerEventType.get(name)` resolves a name.

| Value | Fires when |
|-------|-----------|
| `ENTER` | A target entity enters the volume |
| `EXIT` | A target entity leaves the volume |
| `TICK` | Repeatedly while a target is inside (paced by `Interval`) |
| `TAG_ADDED` / `TAG_REMOVED` | A tag is added to / removed from the volume |
| `BLOCK_PLACED` / `BLOCK_BROKEN` | A block is placed / broken inside the volume |
| `BLOCK_USED` | 0.6.3+ — a block inside the volume is used (interacted with) |
| `VOLUME_CREATE` | 0.6.3+ — the volume itself is created (e.g. by `SpawnTriggerVolume`) |
| `SIGNAL_RECEIVED` | 0.6.3+ — a `SendSignal` effect / `SignalNearbyVolumes` interaction / deny-rule signal targeted this volume (`TriggerContext.getSignalTags()`) |
| `ENTITY_DIED` | 0.6.3+ — a target entity died inside the volume |

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

> Register **before** worlds/effect assets load (in `setup()`). `TriggerVolumesPlugin.get().registerEffectType(id,
> Class, BuilderCodec)` is the equivalent helper (it logs `Registered trigger effect type '<id>' (<class>)`);
> `registerConditionType` / `registerRuleType` / `registerEventType` cover the other extension points.

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
| `getSignalTags()` | `List<SignalTag>` | 0.6.3+ — key/value pairs carried by `TAG_ADDED` / `TAG_REMOVED` / `SIGNAL_RECEIVED` events (`SignalTag(String key, String value)` record). Replaces the 0.5.9 `getTagKey()` / `getTagValue()`, removed by 0.6.3. |
| `getActorPosition()` | `Vector3d` | 0.6.3+ — the triggering entity's position |
| `getEventPosition()` | `Vector3d` | 0.6.3+ — where the event happened (block / hit position) |
| `getBlockPosition()` | `Vector3d` | For `BLOCK_PLACED` / `BLOCK_BROKEN` / `BLOCK_USED` events |
| `getBlockId()` | `String` | The block involved, for block events |
| `getInteractionType()` | `InteractionType` | 0.6.3+ — for `BLOCK_USED` (which click) |
| `resolveOrigin(EffectOrigin, Vector3d offset, MissingActor)` | `Vector3d` | 0.6.3+ — resolve an `Origin` key (volume / entity / event / absolute) to a world position |

> The effect/condition instance is shared across firings — keep per-entity state out of fields. `TriggerEffect` and
> `TriggerCondition` provide an `onEntityExit(UUID)` hook for cleaning up any per-entity tracking you do keep, and
> (0.6.3+) `rotateInPlace(float yawRadians, Vector3d volumeOrigin)`, called when a volume is pasted with a rotation
> (`RotateEffectsOnPaste`) so effects holding positions can rotate them; `getEntry()` / `setEntry(int)` expose the
> `Entry` grouping key.

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

`TriggerVolumesPlugin.get()` is the static accessor. The same plugin also exposes
`getTriggerVolumeGroupComponentType()`, `getManagerResourceType()` (the per-world manager below) and, as of 0.6.3,
`getIgnoreTriggerVolumesComponentType()` — add the `IgnoreTriggerVolumes` marker component (`IgnoreTriggerVolumes.INSTANCE`)
to an entity to make every volume ignore it.

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

// 0.6.3+: rules and custom events
boolean noBuild = mgr.hasActiveRule(position, NoBuildRule.class);
List<DamageMultiplierRule> mults = mgr.getActiveRules(position, DamageMultiplierRule.class);
mgr.enqueueVolumeEvent(myEventType, actorRef, actorUuid, "my-volume-id", List.of(new SignalTag("key", "value")));
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
`getMaxDistanceFromOrigin()`, `getWorldAABB(origin, minOut, maxOut)`, `rotateInPlace(yawRadians)` (a `float` in
**radians**), `copy()`. As of 0.6.3 a `BoxShape` can carry its own rotation (`hasRotation()`, `getRotation()`,
`setRotation(Vector3d)`, plus a `BoxShape(min, max, rotation)` constructor).

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
| `/triggervolume tag` / `listtag` | 0.6.3+ — set/remove tags on a volume; list volumes by tag |
| `/triggervolume test` | Fire a volume's effects for testing |
| `/triggervolume rename` / `tp` / `tool` | 0.6.3+ — rename a volume; teleport to one; give the tool item |
| `/triggervolume benchmark spread\|stacked\|cleanup` | 0.6.3+ — spawn/remove synthetic volumes for performance testing |
| `/triggervolume remove` | Delete a volume |

Three interaction types (0.6.3+) drive volumes from item/NPC interaction graphs: `SpawnTriggerVolume` (`EffectAsset`,
`Shape`, `LifetimeS`, `RequireHitLocation` — creates a temporary volume at the hit point, firing `VOLUME_CREATE`),
`SignalNearbyVolumes` (`MatchKey`, `MatchValue`, `Radius`, `SignalKeys`, `SignalValues`, `RequireHitLocation`) and
`DestroyTaggedVolumes` (`MatchKey`, `MatchValue`, `Radius`).

---

## Gotchas & Errors

- **Effect/condition/rule lists are tolerant.** `TriggerVolumeCodecs.TOLERANT_EFFECTS` / `TOLERANT_CONDITIONS` /
  `TOLERANT_RULES` skip an entry that fails to decode rather than failing the whole asset. A typo'd `Type` silently drops that one effect —
  check the server log for the load, not just the absence of an error.
- **Register custom types early.** A volume that names a `Type` you haven't registered loses that effect; register
  in `setup()` before worlds load.
- **Missing effect asset.** A volume referencing an effect-asset id that doesn't exist logs
  `Volume '<id>' references missing effect asset '<assetId>'` and runs nothing — confirm the asset id matches the
  file under `Server/TriggerVolumes/Effects/`.
- **`Type` is the discriminator key**, not `"Effect"` or `"Name"`. The base codec also reads `Event`, `Interval`,
  `Delay`, `Entry`; everything else is type-specific.
- **`EntityEffect`'s id key is `Effect`.** `{ "Type": "EntityEffect", "EntityEffect": "…" }` never sets the effect id —
  the codec key is `Effect` (plus `Mode`, `Duration`).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
