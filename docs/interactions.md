# Interactions API

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Interactions`

> **Note:** For `InteractionManager` (the entity component that manages interaction chains), see [entities.md](entities.md#interactionmanager).
>
> **See also:**
> - [Operation System](interactions-operations.md) - Low-level execution model and flow control
> - [InteractionContext](interactions-context.md) - Execution state and data access
> - [Item Definitions](items.md) - How items define and customize interactions via `InteractionVars`

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
- [ChangeState](interactions-world.md#changestate) - Change entity state machine state
- [LaunchPadInteraction](interactions-world.md#launchpadinteraction) - Launch pad physics
- [WieldingInteraction](interactions-world.md#wieldinginteraction) - Blocking and guarding mechanics

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

// Get interaction by ID (returns unknown if not found)
Interaction interaction = Interaction.getInteractionOrUnknown("hytale:sword_swing");
int interactionId = Interaction.getInteractionIdOrUnknown("hytale:sword_swing");
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
boolean isCancelOnItemChange()         // Cancel when item changes

// Rules and settings
InteractionRules getRules()
Map<GameMode, InteractionSettings> getSettings()

// Execution (called by framework)
void tick(Ref<EntityStore> ref, LivingEntity entity, boolean flag, float time,
          InteractionType type, InteractionContext context, CooldownHandler cooldown)

// Override in subclasses
void compile(OperationsBuilder builder)
boolean walk(Collector collector, InteractionContext context)  // Visitor pattern for tree traversal and metadata collection
boolean needsRemoteSync()

// Network
Interaction toPacket()
```

### Utility Methods

```java
// Check if interaction state indicates failure
static boolean failed(InteractionState state)
```

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

### InteractionType Enum

**Package:** `com.hypixel.hytale.protocol`

Enum representing the type of interaction trigger.

See [Player Documentation](player.md) for full details.

### Usage Examples

#### Getting an Interaction

```java
// Get interaction from assets
Interaction swordSwing = Interaction.getInteractionOrUnknown("hytale:sword_swing");

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

Root interactions are defined in `Server/Item/RootInteractions/` and configure how interactions are triggered:

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
| `Cooldown` | object | Minimum delay between attacks |
| `Interactions` | array | List of interactions to execute |

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
| `Id` | string | Unique cooldown identifier |
| `Cooldown` | float | Cooldown duration in seconds |
| `ClickBypass` | boolean | If true, clicking can bypass cooldown |

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
    "BlockedBy": ["SECONDARY"],
    "InterruptedBy": ["DODGE"],
    "Interrupting": ["PRIMARY"]
  }
}
```

| Property | Type | Description |
|----------|------|-------------|
| `BlockedBy` | array | Interaction types that prevent starting |
| `Blocking` | array | Interaction types this blocks |
| `InterruptedBy` | array | Types that can cancel mid-execution |
| `Interrupting` | array | Types this cancels |
| `*Bypass` | string | Condition name that bypasses the rule |

#### Common Patterns

**Heavy Attack (can be interrupted by dodge):**
```json
{
  "Rules": {
    "InterruptedBy": ["DODGE", "BLOCK"]
  }
}
```

**Blocking Stance (blocks attacks from starting):**
```json
{
  "Rules": {
    "Blocking": ["PRIMARY", "SECONDARY"]
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
        "Cooldown": 0.0,
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
        "Cooldown": 0.0,
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
    "Left": "Dodge_Left",
    "Right": "Dodge_Right"
  }
}
```

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
