---
title: "Interactions API"
description: "Hytale interactions in JSON — the Interaction base class and SimpleInteraction hierarchy, root vs nested interactions, input-triggered entry points, and asset-store registration."
seo:
  type: TechArticle
---

# Interactions API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Interactions` · **Verified against 0.5.9**

> **Note:** For `InteractionManager` (the entity component that manages interaction chains), see [entities.md](entities.md#interactionmanager).
>
> **See also:**
> - [Operation System](interactions-operations.md) - Low-level execution model and flow control
> - [InteractionContext](interactions-context.md) - Execution state and data access
> - [Item Definitions](items.md) - How items define and customize interactions via `InteractionVars`

This page covers the interaction system: the data-driven actions entities perform (attacks, abilities, item uses), how they are defined as JSON assets, and how they are triggered, gated, and configured.

## Overview

Implemented in `com.hypixel.hytale.server.core.modules.interaction.interaction.config` and provides:
- A base `Interaction` abstract class with a `SimpleInteraction` / `SimpleInstantInteraction` hierarchy
- Root vs nested interactions: input-triggered entry points and reusable building blocks
- Asset-store lookup of interactions by string ID
- A meta-key store for passing targeting/hit/damage data between steps
- Per-`GameMode` settings and cooldown configuration
- Conflict rules (`InteractionRules`) for blocking and interrupting between interaction types

## Architecture
```
Interaction System
├── RootInteraction (Server/Item/RootInteractions/)
│   ├── triggered by input (PRIMARY, SECONDARY, ...)
│   ├── RootInteractionSettings (per-GameMode + cooldown)
│   └── references nested Interactions
├── Nested Interaction (Server/Item/Interactions/)
│   ├── SimpleInteraction → SimpleInstantInteraction
│   └── composed via Serial / Parallel / Condition (see interactions-flow.md)
├── Asset lookup (Interaction.getInteractionOrUnknown / getAssetStore / getAssetMap)
├── Meta keys (TARGET_ENTITY, HIT_LOCATION, DAMAGE, ...) — see interactions-context.md
├── InteractionRules (blockedBy / blocking / interruptedBy / interrupting)
├── CooldownHandler (per-entity cooldown timers)
└── InteractionSettings / RootInteractionSettings (per-GameMode behavior)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Interaction` | `server.core.modules.interaction.interaction.config` | Abstract base for all interactions; identity, effects, rules, asset lookup |
| `SimpleInteraction` | `server.core.modules.interaction.interaction.config` | Base building-block interaction (delays, animations, sounds, flow) |
| `SimpleInstantInteraction` | `server.core.modules.interaction.interaction.config` | Abstract base for instant (no-duration) interactions |
| `RootInteraction` | `server.core.modules.interaction.interaction.config` | Input-triggered entry-point interaction; holds settings and cooldowns |
| `CooldownHandler` | `server.core.modules.interaction.interaction` | Manages per-entity cooldown timers |
| `InteractionRules` | `server.core.modules.interaction.interaction.config` | Block/interrupt conflict rules between interaction types |
| `InteractionSettings` | `protocol` | Per-`GameMode` settings for a nested interaction |
| `RootInteractionSettings` | `protocol` | Per-`GameMode` settings + cooldown for a root interaction |
| `InteractionType` | `protocol` | Enum of interaction trigger types (PRIMARY, SECONDARY, ...) |
| `SimpleBlockInteraction` | `server.core.modules.interaction.interaction.config.client` | Abstract base for block-targeting interactions (client-supplied target block) |
| `InteractionItemChangeBehavior` | `protocol` | Enum: what an interaction does when the held item changes (`Cancel`/`Fail`/`Finish`/`Ignore`) |
| `InteractionModule` | `server.core.modules.interaction` | Core plugin that registers interaction assets, components, and all built-in `Type` strings |
| `InteractionValidation` | `server.core.modules.interaction.interaction.util` | Static server-side range checks for player block/entity interactions |
| `OriginSource` | `server.core.modules.interaction.interaction.config` | Enum: position interactions relative to the entity or the targeted block |
| `RelativeRotationMode` | `server.core.modules.interaction.interaction.config` | Enum: how much of a reference rotation (none/yaw/full) to apply |

## Quick Navigation

| Category | File | Description |
|----------|------|-------------|
| [Operation System](interactions-operations.md) | `interactions-operations.md` | Low-level execution model, OperationsBuilder, labels |
| [InteractionContext](interactions-context.md) | `interactions-context.md` | Execution state, entity refs, meta store, InteractionVars |
| [Combo Systems](interactions-combo.md) | `interactions-combo.md` | Chaining, charging, input branching |
| [Combat & Effects](interactions-combat.md) | `interactions-combat.md` | Damage, forces, status effects, animations |
| [Control Flow](interactions-flow.md) | `interactions-flow.md` | Serial, parallel, conditions, targeting |
| [Entity & World](interactions-world.md) | `interactions-world.md` | Spawning, inventory, blocks, wielding |

### All Interactions by Category

**Combo Systems** ([interactions-combo.md](interactions-combo.md))
- [ChainingInteraction](interactions-combo.md#chaininginteraction) - Sequential combo chains with timing windows
- [FirstClickInteraction](interactions-combo.md#firstclickinteraction) - Branch based on tap vs hold input
- [ChargingInteraction](interactions-combo.md#charginginteraction) - Charge-and-release mechanics
- [ChainFlagInteraction](interactions-combo.md#chainflaginteraction) - Set flags for cross-chain communication
- [CancelChainInteraction](interactions-combo.md#cancelchaininteraction) - Reset chain state to beginning

**Combat & Effects** ([interactions-combat.md](interactions-combat.md))
- [SimpleInteraction](interactions-combat.md#simpleinteraction) - Delays, animations, sounds, and flow control
- [Selector](interactions-combat.md#selector) - Target selection for melee attacks (hitboxes)
- [DamageEntity](interactions-combat.md#damageentity) - Deal damage with effects, knockback, and stat grants
- [ApplyForce](interactions-combat.md#applyforce) - Apply physics forces for knockback and launches
- [ApplyEffect](interactions-combat.md#applyeffect) - Apply status effects (buffs, debuffs, DoT)
- [ClearEntityEffect](interactions-combat.md#clearentityeffect) - Remove status effects from entities
- [ChangeStat](interactions-combat.md#changestat) - Modify health, stamina, signature energy
- [InterruptInteraction](interactions-combat.md#interruptinteraction) - Cancel an entity's current interaction chain

**Control Flow** ([interactions-flow.md](interactions-flow.md))
- [Serial](interactions-flow.md#serial) - Execute interactions sequentially
- [Parallel](interactions-flow.md#parallel) - Execute interactions concurrently
- [Condition](interactions-flow.md#condition) - Game mode and movement state branching
- [StatsCondition](interactions-flow.md#statscondition) - Branch based on entity stat values
- [EffectCondition](interactions-flow.md#effectcondition) - Branch based on active status effects
- [BlockCondition](interactions-flow.md#blockcondition) - Branch based on block type/state/tag
- [CooldownCondition](interactions-flow.md#cooldowncondition) - Branch based on cooldown completion
- [MovementCondition](interactions-flow.md#movementcondition) - Direction-based input branching
- [PlacementCountCondition](interactions-flow.md#placementcountcondition) - Branch based on block placement count
- [Repeat](interactions-flow.md#repeat) - Loop execution of interactions
- [Replace](interactions-flow.md#replace) - Variable substitution for templates
- [Target Selectors](interactions-flow.md#target-selectors) - AOE, raycast, and sweep targeting

**Entity & World** ([interactions-world.md](interactions-world.md))
- [SpawnPrefab](interactions-world.md#spawnprefab) - Spawn entities at locations
- [RemoveEntity](interactions-world.md#removeentity) - Despawn entities from the world
- [LaunchProjectile](interactions-world.md#launchprojectile) - Fire projectiles
- [SendMessage](interactions-world.md#sendmessage) - Send chat messages to players
- [UI Interactions](interactions-world.md#ui-interactions) - Open UI pages (OpenPage, OpenCustomUI)
- [Inventory Interactions](interactions-world.md#inventory-interactions) - Manage inventory and equipment
- [Block Interactions](interactions-world.md#block-interactions) - Break or place blocks
- [PlaceFluid](interactions-world.md#placefluid) - Place a fluid into the world
- [Door](interactions-world.md#door) - Open/close doors and gates (incl. double doors)
- [OpenContainer](interactions-world.md#opencontainer) - Open a container block's inventory window
- [Explode](interactions-world.md#explode) - Explosion with block and entity damage
- [ChangeState](interactions-world.md#changestate) - Change entity state machine state
- [LaunchPadInteraction](interactions-world.md#launchpadinteraction) - Launch pad physics
- [WieldingInteraction](interactions-world.md#wieldinginteraction) - Blocking and guarding mechanics

**Documented with their subsystem** (0.6.3+)
- [SetGameFlag](world.md#game-flags) - Write a universe-wide named integer flag
- [GameFlagCondition](world.md#game-flags) - Succeed while a game flag is at (or at least) a level
- [SpectateControl](player.md#spectatecontrol-interaction) - Cycle a spectator's follow camera, or detach it to free cam

---

## Quick Start

Interactions are actions entities can perform. Start with `SimpleInteraction` for animations and effects.

### Play an Animation

```json
{
  "Type": "Simple",
  "RunTime": 0.5,
  "Effects": {
    "ItemAnimationId": "SwingDown"
  }
}
```

### Play a Sound Effect

```json
{
  "Type": "Simple",
  "RunTime": 0,
  "Effects": {
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"
  }
}
```

### Animation + Sound + Trail

```json
{
  "Type": "Simple",
  "RunTime": 0.177,
  "Effects": {
    "ItemAnimationId": "SwingDown",
    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing",
    "Trails": [{ "TrailId": "Small_Default", "TargetNodeName": "Handle" }]
  }
}
```

### Delay Between Actions

```json
{
  "Type": "Simple",
  "RunTime": 0.2
}
```

### Chain to Another Interaction

```json
{
  "Type": "Simple",
  "RunTime": 0.2,
  "Next": "Sword_Damage_Hit"
}
```

---

## Reference

This section contains technical details, class hierarchies, and complete property tables.

### Class Hierarchy

```
Interaction (abstract)
  implements Operation, JsonAssetWithMap, NetworkSerializable
  └── SimpleInteraction
        └── SimpleInstantInteraction (abstract)
              ├── ProjectileInteraction (see projectiles.md)
              ├── RunRootInteraction
              └── CancelChainInteraction
```

### Interaction Base Class

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Base class for all interactions. An interaction is an action that an entity can perform (attacks, abilities, item uses, etc.).

**Implements:** `Operation`, `JsonAssetWithMap<String, ...>`, `NetworkSerializable<Interaction>`

### Getting Interactions from Assets

```java
// Get the asset store
AssetStore<String, Interaction, ...> store = Interaction.getAssetStore();

// Get the asset map
IndexedLookupTableAssetMap<String, Interaction> map = Interaction.getAssetMap();

// Get interaction by ID (returns unknown if not found). Note: this is the *nested*
// interaction store — root interactions (e.g. "Melee_Root") live in RootInteraction's store.
Interaction interaction = Interaction.getInteractionOrUnknown("Weapon_Sword_Primary");
int interactionId = Interaction.getInteractionIdOrUnknown("Weapon_Sword_Primary");
```

### Meta Keys

Static meta keys for storing context data during interaction execution:

| Key | Type | Description |
|-----|------|-------------|
| `TARGET_ENTITY` | `Ref<EntityStore>` | Entity being targeted |
| `HIT_LOCATION` | `Vector4d` | Location where hit occurred |
| `HIT_DETAIL` | `String` | Detail about what was hit |
| `TARGET_BLOCK` | `BlockPosition` | Block being targeted |
| `TARGET_BLOCK_RAW` | `BlockPosition` | Raw block position |
| `TARGET_BLOCK_TYPE` | `BlockType` | Resolved type of the targeted block (0.6.3+) |
| `TARGET_BLOCK_ROTATION_INDEX` | `Integer` | Rotation index of the targeted block (0.6.3+) |
| `TARGET_SLOT` | `Integer` | Inventory slot |
| `TIME_SHIFT` | `Float` | Time offset |
| `DAMAGE` | `Damage` | Damage information |

### Key Methods

```java
// Identity
String getId()
boolean isUnknown()

// Configuration
InteractionEffects getEffects()        // Visual/audio effects
float getHorizontalSpeedMultiplier()   // Movement speed during interaction
double getViewDistance()               // View distance modifier
float getRunTime()                     // Duration of interaction
InteractionItemChangeBehavior getOnItemChangeBehavior()   // What happens when the held item changes (see below)

// Rules and settings
InteractionRules getRules()
Map<GameMode, InteractionSettings> getSettings()

// Execution (called by framework; both are final)
void tick(Ref<EntityStore> ref, boolean firstRun, float time,
          InteractionType type, InteractionContext context, CooldownHandler cooldown)
void simulateTick(Ref<EntityStore> ref, boolean firstRun, float time,
          InteractionType type, InteractionContext context, CooldownHandler cooldown)

// Override in subclasses
void compile(OperationsBuilder builder)
protected abstract void tick0(boolean firstRun, float time, InteractionType type,
          InteractionContext context, CooldownHandler cooldown)
protected abstract void simulateTick0(boolean firstRun, float time, InteractionType type,
          InteractionContext context, CooldownHandler cooldown)
abstract boolean walk(Collector collector, InteractionContext context)  // Visitor pattern for tree traversal and metadata collection
abstract boolean needsRemoteSync()

// Network
Interaction toPacket()
```

### Utility Methods

```java
// Check if interaction state indicates failure
static boolean failed(InteractionState state)
```

### Held-Item Change Behavior

Every interaction carries an `OnItemChangeBehavior` (`com.hypixel.hytale.protocol.InteractionItemChangeBehavior`) that decides what happens when the executing entity's held item changes mid-interaction (`isCancelOnItemChange()` / the boolean `cancelOnItemChange` field were removed by 0.6.3 — use `getOnItemChangeBehavior()`):

| Value | Meaning |
|-------|---------|
| `Cancel` | Default. The chain is cancelled |
| `Fail` | The interaction ends in `InteractionState.Failed` (so a `Failed` branch can react) |
| `Finish` | The interaction ends in `InteractionState.Finished` as if it completed |
| `Ignore` | The item change is ignored and the interaction keeps running |

```json
{ "Type": "Simple", "RunTime": 0.5, "OnItemChangeBehavior": "Ignore" }
```

The old boolean `CancelOnItemChange` key is still parsed (codec doc: "Deprecated field for whether the interaction will be cancelled when the entity's held item changes.") — `true` maps to `Cancel`, `false` to `Ignore` — but it is flagged deprecated by the validator; write `OnItemChangeBehavior` in new assets.

### SimpleInstantInteraction

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Abstract base class for instant interactions (no duration, immediate effect).

**Extends:** `SimpleInteraction`

#### Key Methods
```java
// Inherited from SimpleInteraction
WaitForDataFrom getWaitForDataFrom()
boolean needsRemoteSync()
```

#### Codec
```java
public static final BuilderCodec<SimpleInstantInteraction> CODEC;
```

#### Usage
This is the base class for interactions that execute immediately, such as:
- Projectile launches (see `ProjectileInteraction` in projectiles.md)
- Instant abilities
- Quick actions

#### Registering a Custom Interaction Type (Java)

A plugin can register its own interaction `Type` and reference it from JSON. `Interaction.CODEC` is
the `AssetCodecMapCodec<String, Interaction>` type-dispatch map; register into it via
[`PluginBase.getCodecRegistry(...)`](codecs.md#registering-custom-types-via-the-plugin-registry):

1. Extend `SimpleInstantInteraction` and override
   `firstRun(InteractionType, InteractionContext, CooldownHandler)` with your logic.
2. Define a `BuilderCodec<MyInteraction>` (the
   [`BuilderCodec.builder(...).append(...).build()`](codecs.md#defining-a-codec-for-an-object) idiom).
3. Register in `setup()`:
   ```java
   getCodecRegistry(Interaction.CODEC)
       .register("My_Type", MyInteraction.class, MyInteraction.CODEC);
   ```
4. Reference from JSON inline, or as a named interaction asset others reference by id:
   ```json
   { "Type": "My_Type", "MyField": 8 }
   ```

Namespace your `Type` ids (interaction/asset ids resolve globally and case-sensitively) — e.g. a
`MyPlugin_` prefix. Key [`InteractionContext`](interactions-context.md) API inside such an interaction:

- `getEntity()` → `Ref<EntityStore>` of the **executor**. For an interaction running in a projectile's
  `ProjectileHit`/`ProjectileMiss`, this is the **projectile** — its `TransformComponent` position is
  the impact point.
- `getOwningEntity()` → the **caster/shooter** (exclude it from AOE so the shooter isn't self-hit).
- `getCommandBuffer()` → a `CommandBuffer<EntityStore>` that also serves as the `ComponentAccessor`
  for queries like `Selector.selectNearbyEntities(...)` and `EffectControllerComponent.addEffect(...)`.

### SimpleBlockInteraction

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.client`

Abstract base class for interactions that act on a targeted block (`BreakBlock`, `PlaceBlock`, `PlaceFluid`, `UseBlock`, `Door`, `OpenContainer`, and many builtin interactions extend it). It resolves the target block position from the client and hands it to the subclass.

**Extends:** `SimpleInteraction`

#### Key Methods

```java
// Block targets come from the client
WaitForDataFrom getWaitForDataFrom()   // returns WaitForDataFrom.Client
boolean needsRemoteSync()

// Subclasses implement these two — server-side effect and client-side prediction
protected abstract void interactWithBlock(World world, CommandBuffer<EntityStore> commandBuffer,
        InteractionType type, InteractionContext context, ItemStack itemInHand,
        Vector3i targetBlock, CooldownHandler cooldownHandler)
protected abstract void simulateInteractWithBlock(InteractionType type, InteractionContext context,
        ItemStack itemInHand, World world, Vector3i targetBlock)

// Helpers (0.6.3+)
static BlockPosition resolveBaseBlockPosition(World world, BlockPosition pos)  // multi-block: the block's base/anchor position
protected static boolean hasRemovedBlockContext(InteractionContext context)   // true when the targeted block was already removed
```

#### Codec

```java
public static final BuilderCodec<SimpleBlockInteraction> CODEC;
```

JSON property added on top of `SimpleInteraction`:

| Property | Type | Description |
|----------|------|-------------|
| `UseLatestTarget` | boolean | Use the client's latest target block position for this interaction (codec doc: "Determines whether to use the clients latest target block position for this interaction.") |

`UseLatestTarget` is inherited by subclasses whose codec builds on `SimpleBlockInteraction.CODEC` (e.g. `Door`, `OpenContainer`); a few subclasses (e.g. `PlaceFluid`) build directly on `SimpleInteraction.CODEC` and don't expose it.

To write your own block-targeting interaction type, extend `SimpleBlockInteraction`, implement the two abstract methods, and register a `Type` string as described in [Registering a Custom Interaction Type (Java)](#registering-a-custom-interaction-type-java).

### InteractionType Enum

**Package:** `com.hypixel.hytale.protocol`

Enum representing the type of interaction trigger. Members are PascalCase (`Primary`, `Secondary`, `Ability1`–`Ability3`, `Use`, `Pick`, `Pickup`, `CollisionEnter`, `CollisionLeave`, `Collision`, `EntityStatEffect`, `SwapTo`, `SwapFrom`, `Death`, `Wielding`, `ProjectileSpawn`, `ProjectileHit`, `ProjectileMiss`, `ProjectileBounce`, `Held`, `HeldOffhand`, `Equipped`, `Dodge`, `GameModeSwap`, and, as of 0.6.3, `OnBreak` and `OnBreakImpact` — block-break hooks fired via `BlockHarvestUtils.fireOnBreakInteraction` / `queueOnBreakImpactInteraction`). The JSON `EnumCodec` matches names case-insensitively, so `"PRIMARY"` and `"Primary"` both parse; shipped assets use PascalCase.

See [Player Documentation](player.md) for full details.

### OriginSource Enum

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Selects the origin an interaction's position math is based on. Used as the `OriginSource` JSON property of [SpawnPrefab](interactions-world.md#spawnprefab) (and builtin interactions like `SpawnDeployableAtLocation` and the instance-teleport interactions).

| Value | Meaning (codec doc) |
|-------|---------------------|
| `ENTITY` | "The origin will be based on the position of the entity performing the interaction." |
| `BLOCK` | "The origin will be based on the position of the targeted block." |

```java
public static final EnumCodec<OriginSource> CODEC;
```

With `BLOCK`, offsets and yaw are additionally rotated by the targeted block's rotation; if there is no target block the interaction is skipped.

### RelativeRotationMode Enum

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

Controls how much of a reference rotation is applied to an interaction-supplied offset or spawned object. Used by the builtin `SpawnDeployableAtLocation` interaction (`OffsetRotationMode` / `DeployableRotationMode` JSON properties, both defaulting to `NONE`).

| Value | Meaning (codec doc) |
|-------|---------------------|
| `NONE` | "The reference rotation will not be applied. Values are treated as absolute." |
| `YAW` | "Only the yaw (Y-axis) component of the reference rotation will be applied." |
| `FULL` | "The full reference rotation (pitch, yaw, and roll) will be applied." |

```java
public static final EnumCodec<RelativeRotationMode> CODEC;
```

### InteractionModule

**Package:** `com.hypixel.hytale.server.core.modules.interaction`

The core plugin (`extends JavaPlugin`) that owns the interaction system. Its `setup()` registers the `Interaction` and `RootInteraction` asset stores (`Server/Item/Interactions`, `Server/Item/RootInteractions`), every built-in `Type` string listed across these pages (`"Simple"`, `"PlaceBlock"`, `"Door"`, `"Explode"`, ...), and the interaction-related components. Your own `Type` strings go through the same registry — see [Registering a Custom Interaction Type (Java)](#registering-a-custom-interaction-type-java).

#### Key Methods

```java
// Singleton accessor
static InteractionModule get()

// Entry point for mouse-driven interactions (called by the packet handler)
void doMouseInteraction(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        MouseInteraction packet, Player player, PlayerRef playerRef)

// Registered component/resource types
ComponentType<EntityStore, InteractionManager> getInteractionManagerComponent()
ComponentType<EntityStore, Interactions> getInteractionsComponentType()
ComponentType<EntityStore, ChainingInteraction.Data> getChainingDataComponent()
ComponentType<ChunkStore, PlacedByInteractionComponent> getPlacedByComponentType()
ResourceType<ChunkStore, BlockCounter> getBlockCounterResourceType()
ComponentType<ChunkStore, TrackedPlacement> getTrackedPlacementComponentType()

// 0.6.3+
ComponentType<EntityStore, InteractionHost> getInteractionHostComponentType()          // standalone entity that runs an interaction chain at a position (InteractionHost.spawnHost(...))
ComponentType<EntityStore, CarriedBlock> getCarriedBlockComponentType()                // block currently carried (CarryBlock / CarryPlaceBlock / CarryDroppedBlock types)
ResourceType<EntityStore, CarriedBlockSystems.QueueResource> getCarriedBlockQueueResourceType()
```

Built-in `Type` strings added by 0.6.3 (not yet documented on these pages): `DragPlaceBlock`, `ExtrudePlaceBlock`, `SurfaceDrawPlaceBlock`, `DragEraseBlock`, `PlaceModeSelect`, `CarryBlock`, `CarryPlaceBlock`, `CarryDroppedBlock`, `RevealMapMarkersInView`, `ShowEventTitle`. `InteractionModule` also registers `SpectateControl` — documented with the rest of spectator mode in [player.md](player.md#spectatecontrol-interaction).

**Types registered by other plugins.** `Interaction.CODEC` is shared, so bundled plugins add their own `Type` strings in *their* `setup()`, and those types only exist when that plugin is loaded. `Hytale:GameFlags` contributes `SetGameFlag` and `GameFlagCondition` — see [world.md → Game Flags](world.md#game-flags).

#### Static Fields

```java
static final PluginManifest MANIFEST;
static final EnumCodec<InteractionType> INTERACTION_TYPE_CODEC;
static final SetCodec<InteractionType, EnumSet<InteractionType>> INTERACTION_TYPE_SET_CODEC;
```

For `PlacedByInteractionComponent` (the chunk-store component behind `getPlacedByComponentType()`), see [interactions-world.md](interactions-world.md#placedbyinteractioncomponent).

### InteractionValidation

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.util`

Static server-side range checks run before a player's block/entity interactions are accepted.

```java
static boolean canPlayerInteractWithEntity(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, Ref<EntityStore> targetRef)

static boolean canPlayerInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, int blockX, int blockY, int blockZ)
static boolean canPlayerInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, Vector3i pos)
static boolean canPlayerInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, BlockPosition pos)

// 0.6.3+: any entity (players delegate to canPlayerInteractWithBlock)
static boolean canEntityInteractWithBlock(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor,
        ItemStack heldItem, BlockPosition blockPosition, BlockPosition contactPosition)
// 0.6.3+: may `ref` run a projectile-type interaction through `proxy` (a predicted projectile it created)?
static boolean isAccessibleProxyTarget(Ref<EntityStore> ref, Ref<EntityStore> proxy, InteractionType type)
```

How the allowed distance is computed (from the decompiled source):

- Base distance comes from the held item's `InteractionConfiguration.getUseDistance(gameMode)` (default config if no item is held).
- In **Creative**, the client's `creativeInteractionDistance` setting is honored, clamped to `0–128` blocks (default `10` if no settings component), and the larger of the two distances wins.
- A `+2.0` buffer is added before squaring, and distance is measured from the player's **eye height** to the target (block center for blocks).
- A `ref` without a `Player` component always passes (`true`); a player missing a `TransformComponent` always fails.
- `canEntityInteractWithBlock` (0.6.3+): a player delegates to the player check; a non-player without a `StandardPhysicsProvider` always passes; a physics entity must be within **8 blocks** (64 squared, from its position, no eye offset) of `contactPosition`.
- `isAccessibleProxyTarget` (0.6.3+) is `true` only for `ProjectileSpawn`/`ProjectileHit`/`ProjectileMiss`/`ProjectileBounce`, when `proxy` is a valid `PredictedProjectile` whose `StandardPhysicsProvider` creator UUID equals `ref`'s `UUIDComponent`.

### Usage Examples

#### Getting an Interaction

```java
// Get interaction from assets (a nested interaction id, i.e. a file under Server/Item/Interactions/)
Interaction swordSwing = Interaction.getInteractionOrUnknown("Weapon_Sword_Primary");

if (!swordSwing.isUnknown()) {
    float duration = swordSwing.getRunTime();
    InteractionRules rules = swordSwing.getRules();
}
```

#### Checking Interaction Settings per GameMode

```java
Interaction interaction = Interaction.getInteractionOrUnknown("my_interaction");
Map<GameMode, InteractionSettings> settings = interaction.getSettings();

InteractionSettings survivalSettings = settings.get(GameMode.Survival);
if (survivalSettings != null) {
    // Use survival-specific settings
}
```

#### Using Meta Keys in Custom Interactions

```java
// During interaction execution, access meta data via the meta store
DynamicMetaStore<InteractionContext> meta = context.getMetaStore();
Ref<EntityStore> target = meta.getMetaObject(Interaction.TARGET_ENTITY);
Vector4d hitLocation = meta.getMetaObject(Interaction.HIT_LOCATION);
Damage damage = meta.getMetaObject(Interaction.DAMAGE);
```

### Root Interaction Configuration

Root interactions are defined in `Server/Item/RootInteractions/` and configure how interactions are triggered. `Weapons/Sword/Root_Weapon_Sword_Primary.json`:

```json
{
  "RequireNewClick": true,
  "ClickQueuingTimeout": 0.2,
  "Cooldown": { "Cooldown": 0.25 },
  "Interactions": ["Weapon_Sword_Primary"]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `RequireNewClick` | boolean | If true, must click again to chain (holding won't auto-chain) |
| `ClickQueuingTimeout` | float | Buffer window to queue next attack input |
| `Cooldown` | object | Minimum delay between attacks (see [Cooldown Configuration](#cooldown-configuration)) |
| `Interactions` | array | List of interactions to execute (required, non-empty) |
| `Rules` | object | [InteractionRules](#interactionrules) for the whole chain |
| `Settings` | object | Per-`GameMode` [RootInteractionSettings](#rootinteractionsettings) |
| `HudInputBindingEntry` | string | 0.6.3+. Codec doc: "The localization key the client shows as an input binding hint on the HUD for whichever input this root interaction is bound to. When unset, no hint is shown." |

### Cooldown System

Cooldowns prevent interactions from being spammed by enforcing minimum delays between uses.

#### CooldownHandler

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction`

The `CooldownHandler` manages cooldown timers for an entity:

```java
public class CooldownHandler {
    // Check if a cooldown is active
    boolean isOnCooldown(RootInteraction root, String cooldownId, float time,
                         float[] progress, boolean checkOnly);

    // Reset a cooldown timer
    void resetCooldown(String cooldownId, float duration, float[] progress, boolean notify);

    // Get cooldown info
    Cooldown getCooldown(String cooldownId);

    // Update all cooldowns (called each frame)
    void tick(float deltaTime);
}
```

#### Cooldown Configuration

Cooldowns are configured in RootInteraction JSON files:

```json
{
  "Interactions": ["Weapon_Sword_Primary"],
  "Settings": {
    "Adventure": {
      "Cooldown": {
        "Id": "SwordAttack",
        "Cooldown": 0.278
      }
    },
    "Creative": {
      "Cooldown": {
        "Id": "SwordAttack_Creative",
        "Cooldown": 0.0,
        "ClickBypass": true
      }
    }
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `Id` | string | Unique cooldown identifier (codec doc: "Cooldowns can be used on different interactions but share a cooldown.") |
| `Cooldown` | float | Cooldown duration in seconds (must be ≥ 0) |
| `ClickBypass` | boolean | If true, clicking can bypass cooldown |
| `Charges` | float[] | "The charge times available for this interaction." — a charge-based cooldown (see `CooldownHandler.Cooldown.deductCharge()` / `replenishCharge(...)`) |
| `SkipCooldownReset` | boolean | "Determines whether resetting cooldown should be skipped." |
| `InterruptRecharge` | boolean | "Determines whether recharge is interrupted by use." |

#### Cooldown Interactions

Several interactions work with cooldowns:

| Interaction | Description |
|-------------|-------------|
| `TriggerCooldown` | Start a cooldown timer |
| `ResetCooldown` | Reset a cooldown to zero |
| `CooldownCondition` | Branch based on cooldown state |

See [interactions-flow.md#cooldowncondition](interactions-flow.md#cooldowncondition) for conditional usage.

---

### InteractionRules

`InteractionRules` control how interactions conflict with each other. They determine which interactions can be blocked or interrupted by others.

#### Rule Types

```java
public class InteractionRules {
    // Which interaction types block this interaction from starting
    protected Set<InteractionType> blockedBy;
    protected String blockedByBypass;  // Condition to bypass blocking

    // Which interaction types this interaction blocks
    protected Set<InteractionType> blocking;
    protected String blockingBypass;

    // Which interaction types can interrupt this interaction mid-execution
    protected Set<InteractionType> interruptedBy;
    protected String interruptedByBypass;

    // Which interaction types this interaction interrupts
    protected Set<InteractionType> interrupting;
    protected String interruptingBypass;

    // Validation methods (Int2ObjectMap/IntSet are fastutil collections)
    boolean validateInterrupts(InteractionType type, Int2ObjectMap<IntSet> tags,
                               InteractionType otherType, Int2ObjectMap<IntSet> otherTags,
                               InteractionRules otherRules);
    boolean validateBlocked(InteractionType type, Int2ObjectMap<IntSet> tags,
                            InteractionType otherType, Int2ObjectMap<IntSet> otherTags,
                            InteractionRules otherRules);
}
```

#### JSON Configuration

```json
{
  "Type": "Simple",
  "RunTime": 0.5,
  "Rules": {
    "BlockedBy": ["Secondary"],
    "InterruptedBy": ["Dodge"],
    "Interrupting": ["Primary"]
  }
}
```

Values are [`InteractionType`](#interactiontype-enum) names (PascalCase in shipped assets; parsing is case-insensitive).

| Property | Type | Description |
|----------|------|-------------|
| `BlockedBy` | array | Interaction types that prevent starting. Codec doc: "If not set then a set of default rules will be applied based on the interaction type that the interaction is fired with. This is only effective when used on the root interaction of a chain." |
| `Blocking` | array | Interaction types this blocks from starting while running (defaults to blocking nothing) |
| `InterruptedBy` | array | Types that can cancel mid-execution ("only effective when used on the root interaction of a chain") |
| `Interrupting` | array | Types this cancels when it starts |
| `*Bypass` | string | A **tag** that, if matched, bypasses the corresponding rule (`BlockedByBypass`, `BlockingBypass`, `InterruptedByBypass`, `InterruptingBypass`) |

#### Common Patterns

**Heavy Attack (can be interrupted by dodge):**
```json
{
  "Rules": {
    "InterruptedBy": ["Dodge", "Wielding"]
  }
}
```

**Blocking Stance (blocks attacks from starting):**
```json
{
  "Rules": {
    "Blocking": ["Primary", "Secondary"]
  }
}
```

---

### InteractionSettings

**Package:** `com.hypixel.hytale.protocol`

`InteractionSettings` configures per-GameMode behavior for nested interactions (accessed via `Interaction.getSettings()`).

```java
public class InteractionSettings {
    public boolean allowSkipOnClick;
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AllowSkipOnClick` | boolean | If true, clicking can skip this interaction early |

#### JSON Configuration

InteractionSettings can be configured per game mode within nested interaction definitions:

```json
{
  "Type": "Simple",
  "RunTime": 0.5,
  "Settings": {
    "Creative": {
      "AllowSkipOnClick": true
    }
  }
}
```

#### Usage in Code

```java
Interaction interaction = Interaction.getInteractionOrUnknown("my_interaction");
Map<GameMode, InteractionSettings> settings = interaction.getSettings();

InteractionSettings creativeSettings = settings.get(GameMode.Creative);
if (creativeSettings != null && creativeSettings.allowSkipOnClick) {
    // Handle skip behavior
}
```

---

### RootInteractionSettings

**Package:** `com.hypixel.hytale.protocol`

`RootInteractionSettings` configures per-GameMode behavior for root interactions (accessed via `RootInteraction.getSettings()`). Unlike `InteractionSettings`, this class includes cooldown configuration.

```java
public class RootInteractionSettings {
    public boolean allowSkipChainOnClick;
    public InteractionCooldown cooldown;
}
```

| Property | Type | Description |
|----------|------|-------------|
| `AllowSkipChainOnClick` | boolean | If true, clicking can skip the entire interaction chain early |
| `Cooldown` | [InteractionCooldown](#cooldown-configuration) | Cooldown configuration for this game mode |

#### JSON Configuration

RootInteractionSettings are configured in root interaction files (`Server/Item/RootInteractions/`):

```json
{
  "Interactions": ["Block_Primary"],
  "Settings": {
    "Adventure": {
      "Cooldown": {
        "Id": "BlockInteraction",
        "Cooldown": 0.278
      }
    },
    "Creative": {
      "AllowSkipChainOnClick": true,
      "Cooldown": {
        "Id": "BlockInteraction_Creative",
        "Cooldown": 0.278,
        "ClickBypass": true
      }
    }
  }
}
```

#### Difference from InteractionSettings

| Class | Used By | Key Difference |
|-------|---------|----------------|
| `InteractionSettings` | Nested `Interaction` | Has `AllowSkipOnClick` (skips single interaction) |
| `RootInteractionSettings` | `RootInteraction` | Has `AllowSkipChainOnClick` (skips entire chain) + cooldown config |

---

### Root vs Nested Interactions

Interactions are organized into two categories based on their role and file location.

#### Root Interactions

**Location:** `Server/Item/RootInteractions/`

Root interactions are entry points triggered by player input (PRIMARY, SECONDARY, etc.). They:

- Define per-GameMode settings
- Configure cooldowns
- Specify which nested interactions to execute
- Are referenced by items via `PrimaryInteraction`, `SecondaryInteraction`, etc.

**Example:** `Block_Primary.json`
```json
{
  "Interactions": ["Block_Primary"],
  "Settings": {
    "Adventure": {
      "Cooldown": {
        "Id": "BlockInteraction",
        "Cooldown": 0.278
      }
    },
    "Creative": {
      "AllowSkipChainOnClick": true,
      "Cooldown": {
        "Id": "BlockInteraction_Creative",
        "Cooldown": 0.278,
        "ClickBypass": true
      }
    }
  }
}
```

#### Nested Interactions

**Location:** `Server/Item/Interactions/`

Nested interactions are reusable building blocks. They:

- Define the actual behavior (animations, damage, effects)
- Can be referenced by ID from other interactions
- Can be inlined directly in JSON
- Support composition via `Serial`, `Parallel`, `Condition`, etc.

**Example:** `Dodge.json`
```json
{
  "Type": "Condition",
  "Flying": false,
  "Next": {
    "Type": "MovementCondition",
    "ForwardLeft": { "Type": "Simple" },
    "ForwardRight": { "Type": "Simple" },
    "Left": "Dodge_Left",
    "Right": "Dodge_Right",
    "BackLeft": { "Type": "Simple" },
    "BackRight": { "Type": "Simple" }
  }
}
```

(`Dodge_Left` / `Dodge_Right` live in the `Dodge/` subfolder — IDs are filenames, subfolders don't matter.)

#### Reference Patterns

Nested interactions can be referenced in two ways:

**By ID (string reference):**
```json
{
  "Type": "Serial",
  "Interactions": [
    "Sword_Swing_Down",
    "Sword_Damage_Hit"
  ]
}
```

**Inline (direct definition):**
```json
{
  "Type": "Serial",
  "Interactions": [
    {
      "Type": "Simple",
      "RunTime": 0.2,
      "Effects": { "ItemAnimationId": "SwingDown" }
    },
    "Sword_Damage_Hit"
  ]
}
```

#### Asset Discovery

The interaction system loads assets in this order:

1. **Root interactions** from `Server/Item/RootInteractions/`
2. **Nested interactions** from `Server/Item/Interactions/`
3. String references resolve to loaded interaction IDs

IDs are derived from filenames without the `.json` extension.

---

### Complete Interaction Type Reference

**Class Hierarchy Overview**

```
Interaction (abstract)
├── SimpleInteraction
│   └── SimpleInstantInteraction
└── RootInteraction
```

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config`

---

## Gotchas & Errors

Backtick-quoted error strings below are literal messages from the server (verified against `HytaleServer.jar`).

- **`No interaction ID found for`** / **`Failed to find interaction:`** (`InteractionManager`) → a string reference (in `Next`, `Interactions`, `Serial`, etc.) points to an interaction ID that was never loaded. Fix: the ID must match a `.json` filename (minus the extension) under `Server/Item/Interactions/` or `Server/Item/RootInteractions/`; see [Asset Discovery](#asset-discovery). (`No such interaction:` is the NPC combat-action evaluator's version of the same problem, for an `AbilityCombatAction` naming an unknown interaction.)
- **`Missing interaction:`** → an interaction expected at lookup time is absent from the asset store. Fix: ensure the referenced asset ships in your asset pack and loaded without error.
- **`No interactions are defined for`** → a root interaction has an empty (or missing) `Interactions` list, so there is nothing to run. Fix: list at least one nested interaction in the root's `Interactions` array (the codec also rejects a missing/empty list at load time).
- **Symptom:** a `BlockedBy` / `InterruptedBy` rule on a nested interaction has no effect → per the codec docs those two rules are "only effective when used on the root interaction of a chain". Fix: put them in the root interaction's `Rules`.
- **Symptom:** an ID resolves at runtime but the interaction silently does nothing → `getInteractionOrUnknown(...)` returns the *unknown* placeholder rather than throwing for a bad ID. Fix: guard with `!interaction.isUnknown()` before using a looked-up `Interaction` (see [Getting an Interaction](#getting-an-interaction)).
- **Symptom:** an interaction never starts even though the input fires → another interaction's `Rules` block it. `BlockedBy`/`Blocking` (and the default rules applied per `InteractionType` when `Rules` is unset) gate starting. Fix: review the [InteractionRules](#interactionrules) of both interactions, or set a `*Bypass` condition.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
