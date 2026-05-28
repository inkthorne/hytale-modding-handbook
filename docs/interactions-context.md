---
title: "InteractionContext"
description: "The Hytale InteractionContext — access entity references (owner, executor, targets), the held item, the meta store (hit locations, targets), and item-defined InteractionVars at runtime."
seo:
  type: TechArticle
---

# InteractionContext

**Doc type:** Java API · **Verified against 0.5.2**

> **Prerequisites:** Read [interactions.md](interactions.md) and [Operation System](interactions-operations.md) first.
>
> **See also:** [Item Definitions](items.md) for `InteractionVars`, [entities.md](entities.md#interactionmanager) for `InteractionManager`.

`InteractionContext` is the execution state container passed to operations during interaction execution. It provides access to entities, items, targeting data, and flow control.

## Overview

When an interaction runs, `InteractionContext` carries:

- **Entity references** - The owning entity, executing entity, and targets
- **Item state** - The held item being used
- **Meta store** - Key-value data like hit locations and targets (`DynamicMetaStore`)
- **InteractionVars** - Item-defined variables for customization (a `Map<String, String>`)
- **Flow control** - Labels and jump capabilities
- **Chain management** - Current chain and entry tracking

Understanding `InteractionContext` is essential for:
- Accessing targets selected by `Selector` interactions
- Reading item-specific variables
- Passing data between operations
- Implementing custom interactions

## Architecture
```
InteractionContext (passed to every operation tick)
├── Entity references (getEntity / getOwningEntity / getTargetEntity)
├── Item state (getHeldItem / getHeldItemSlot / getOriginalItemType)
├── Meta store (DynamicMetaStore via getMetaStore)
│   └── MetaKey<T> keys (standard keys defined on Interaction)
├── InteractionVars (item-defined Map<String, String>)
├── Flow control (jump(Label) / operation counter / labels)
└── Chain management
    ├── InteractionChain (getChain) + fork(...)
    └── InteractionEntry (getEntry)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `InteractionContext` | `server.core.entity` | Execution-state container passed to operations |
| `DynamicMetaStore` | `server.core` (returned by `getMetaStore`) | Key-value store for passing data between operations |
| `MetaKey<T>` | `server.core.meta` | Type-safe key for meta-store values (registered internally) |
| `InteractionChain` | `server.core.entity` | Full chain execution context (id, type, server state, root) |
| `InteractionEntry` | `server.core.entity` | Per-entry execution state within a chain |

---

## InteractionContext Class

**Package:** `com.hypixel.hytale.server.core.entity`

### Core Methods

```java
public class InteractionContext {
    // Entity access
    Ref<EntityStore> getEntity();           // Entity executing the interaction
    Ref<EntityStore> getOwningEntity();     // Entity that owns the interaction chain
    Ref<EntityStore> getTargetEntity();     // Current target (from Selector)

    // Item access
    ItemStack getHeldItem();                // The item being used
    byte getHeldItemSlot();                 // Slot index of held item
    Item getOriginalItemType();             // Item config when chain started

    // Meta store (dynamic data)
    DynamicMetaStore<InteractionContext> getMetaStore();

    // InteractionVars (item-defined variables, a plain String->String map)
    Map<String, String> getInteractionVars();
    void setInteractionVarsGetter(Function<InteractionContext, Map<String, String>> getter);

    // Flow control
    void jump(Label label);
    int getOperationCounter();
    void setOperationCounter(int counter);
    void setLabels(Label... labels);

    // Chain management
    InteractionChain getChain();
    InteractionEntry getEntry();
    // fork(...) overloads return InteractionChain and take args, e.g.:
    InteractionChain fork(InteractionType type, InteractionContext ctx,
                          RootInteraction root, boolean flag);
}
```

> **Note:** `InteractionContext` does **not** expose `getMeta`/`setMeta` convenience
> methods. Meta values are accessed through the `DynamicMetaStore` returned by
> `getMetaStore()`. There is no `advanceOperation()` and no static factory method.

---

## Entity References

### Owning vs Executing Entity

In most cases, these are the same entity. They differ in delegated interactions:

| Method | Description | Example |
|--------|-------------|---------|
| `getOwningEntity()` | Entity that initiated the chain | Player who summoned a minion |
| `getEntity()` | Entity currently executing | The minion attacking |

```java
@Override
public void tick(..., InteractionContext context, ...) {
    Ref<EntityStore> owner = context.getOwningEntity();
    Ref<EntityStore> executor = context.getEntity();

    // Usually the same
    if (owner.equals(executor)) {
        // Direct execution
    } else {
        // Delegated (e.g., summon, pet, turret)
    }
}
```

### Target Entity

Set by `Selector` interactions (melee hitbox, raycast, AOE):

```java
@Override
public void tick(..., InteractionContext context, ...) {
    Ref<EntityStore> target = context.getTargetEntity();

    if (target != null && target.isValid()) {
        // Apply effect to target
        LivingEntity targetEntity = target.get(LivingEntity.class);
        if (targetEntity != null) {
            // Deal damage, apply effect, etc.
        }
    }
}
```

---

## Item Access

### Held Item

```java
@Override
public void tick(..., InteractionContext context, ...) {
    ItemStack heldItem = context.getHeldItem();

    if (heldItem != null && !heldItem.isEmpty()) {
        ItemType itemType = heldItem.getItemType();
        int count = heldItem.getCount();

        // Access item data
        // ...
    }
}
```

### Original Item Type

Tracks the item config when the chain started. Useful for detecting item swaps.
`getOriginalItemType()` returns an `Item` (the item config type), not an `ItemType`:

```java
@Override
public void tick(..., InteractionContext context, ...) {
    Item original = context.getOriginalItemType();
    ItemStack current = context.getHeldItem();

    if (current != null && !current.getItemType().equals(original)) {
        // Item changed during interaction - might want to cancel
    }
}
```

### Held Item Slot

```java
byte slot = context.getHeldItemSlot();
// Use for inventory operations
```

---

## Meta Store

The meta store is a key-value map for passing data between operations. Standard keys are defined on the `Interaction` class. Access it via `context.getMetaStore()`, which returns a `DynamicMetaStore`; read with `getMetaObject(key)` and write with `putMetaObject(key, value)`.

### Standard Meta Keys

| Key | Type | Set By | Description |
|-----|------|--------|-------------|
| `TARGET_ENTITY` | `Ref<EntityStore>` | Selector | Entity hit by selector |
| `HIT_LOCATION` | `Vector4d` | Selector | World position of hit |
| `HIT_DETAIL` | `String` | Selector | Hit detail info |
| `TARGET_BLOCK` | `BlockPosition` | Block targeting | Block being interacted with |
| `TARGET_BLOCK_RAW` | `BlockPosition` | Block targeting | Raw block position |
| `TARGET_SLOT` | `Integer` | Inventory ops | Target inventory slot |
| `TIME_SHIFT` | `Float` | Timing ops | Time offset |
| `DAMAGE` | `Damage` | Damage ops | Damage calculation result |

### Reading Meta Values

```java
@Override
public void tick(..., InteractionContext context, ...) {
    DynamicMetaStore<InteractionContext> meta = context.getMetaStore();

    // Get target from selector
    Ref<EntityStore> target = meta.getMetaObject(Interaction.TARGET_ENTITY);

    // Get hit position
    Vector4d hitPos = meta.getMetaObject(Interaction.HIT_LOCATION);

    // Get damage info
    Damage damage = meta.getMetaObject(Interaction.DAMAGE);

    if (target != null && hitPos != null) {
        // Spawn hit effect at location
    }
}
```

### Writing Meta Values

```java
@Override
public void tick(..., InteractionContext context, ...) {
    DynamicMetaStore<InteractionContext> meta = context.getMetaStore();

    // Store data for later operations
    meta.putMetaObject(Interaction.TARGET_ENTITY, foundTarget);
    meta.putMetaObject(Interaction.HIT_LOCATION, hitPosition);
}
```

### MetaKey and the Meta Store

The meta system provides type-safe key-value storage for passing data between operations during interaction execution.

#### MetaKey<T>

`MetaKey<T>` is a type-safe key class that identifies stored values and enforces their type at compile time.

**Package:** `com.hypixel.hytale.server.core.meta`

`MetaKey` has a package-private constructor (keys are registered internally) and exposes only `getId()`. There is no public `MetaKey.create(...)` factory, so plugins use the predefined standard keys on the `Interaction` class rather than creating their own.

#### DynamicMetaStore

The store is accessed via `context.getMetaStore()`, which returns a
`DynamicMetaStore<InteractionContext>`. Read and write values directly on it:

```java
DynamicMetaStore<InteractionContext> meta = context.getMetaStore();

Ref<EntityStore> target = meta.getMetaObject(Interaction.TARGET_ENTITY);
boolean has = meta.hasMetaObject(Interaction.DAMAGE);
meta.putMetaObject(Interaction.TARGET_ENTITY, foundTarget);
```

#### Standard Keys on Interaction Class

The `Interaction` class defines standard keys used by built-in operations:

| Key | Type | Set By | Description |
|-----|------|--------|-------------|
| `Interaction.TARGET_ENTITY` | `Ref<EntityStore>` | Selector | Entity hit by selector |
| `Interaction.HIT_LOCATION` | `Vector4d` | Selector | World position of hit |
| `Interaction.HIT_DETAIL` | `String` | Selector | Hit detail info |
| `Interaction.TARGET_BLOCK` | `BlockPosition` | Block targeting | Block being interacted with |
| `Interaction.DAMAGE` | `Damage` | Damage ops | Damage calculation result |

> **Note:** `MetaKey` instances are registered internally and have no public
> `create(...)` factory, so plugins cannot define arbitrary custom keys. Use the
> predefined standard keys above. To carry your own data between operations, prefer
> the item's `InteractionVars` (see below).

#### Operation Communication Pattern

Operations communicate by writing to and reading from the meta store:

```java
// First operation: Read a target stored by an earlier Selector
public class ApplyDamageOp implements Operation {
    @Override
    public void tick(..., InteractionContext context, ...) {
        DynamicMetaStore<InteractionContext> meta = context.getMetaStore();

        Ref<EntityStore> target = meta.getMetaObject(Interaction.TARGET_ENTITY);
        Damage damage = meta.getMetaObject(Interaction.DAMAGE);

        if (target != null && damage != null) {
            // Apply damage to target
        }
    }
}
```

#### Best Practices

1. **Use the standard keys** - The `Interaction` constants cover targeting, hits, and damage
2. **Check for null** - Meta values may not be set if earlier operations were skipped
3. **Type safety** - The `MetaKey<T>` generic ensures compile-time type checking

---

## InteractionVars

`InteractionVars` are item-defined variables that customize interaction behavior. They allow a single interaction definition to behave differently based on the item using it.

### Accessing InteractionVars

`getInteractionVars()` returns a plain `Map<String, String>` — there are no typed
accessors. Parse values yourself:

```java
@Override
public void tick(..., InteractionContext context, ...) {
    Map<String, String> vars = context.getInteractionVars();

    // Values are strings; parse and apply defaults manually
    float damage = vars.containsKey("Damage")
        ? Float.parseFloat(vars.get("Damage")) : 10.0f;
    String effectId = vars.getOrDefault("EffectId", "none");
    int count = vars.containsKey("HitCount")
        ? Integer.parseInt(vars.get("HitCount")) : 1;
}
```

### Item Definition with InteractionVars

Items define vars in their JSON:

```json
{
  "Type": "Item",
  "InteractionVars": {
    "Damage": 25.0,
    "EffectId": "Burn",
    "HitCount": 3
  }
}
```

### Common InteractionVars Patterns

Weapon damage scaling:
```json
{
  "InteractionVars": {
    "Damage": 15,
    "DamageStat": "Vigor",
    "KnockbackForce": 800
  }
}
```

Ability customization:
```json
{
  "InteractionVars": {
    "ProjectileSpeed": 50,
    "ProjectileCount": 3,
    "SpreadAngle": 15
  }
}
```

See [items.md](items.md) for full `InteractionVars` documentation.

---

## Flow Control

### Jumping to Labels

Operations can jump to labels set during compilation:

```java
@Override
public void tick(..., InteractionContext context, ...) {
    if (conditionFailed) {
        // Jump to skip label (set via addOperation(..., skipLabel))
        context.jump(skipLabel);
    }
}
```

### Operation Counter

Track and set the current position in the operation array. There is no
`advanceOperation()` convenience method; the operation counter is read and written
directly:

```java
int currentOp = context.getOperationCounter();
context.setOperationCounter(currentOp + 1);  // Move to next operation
```

---

## Chain Management

### InteractionChain

The chain represents the full execution context (package
`com.hypixel.hytale.server.core.entity`):

```java
InteractionChain chain = context.getChain();

// Chain identification and type
int chainId = chain.getChainId();
InteractionType type = chain.getType();

// Server-side state and the root interaction
InteractionState state = chain.getServerState();
RootInteraction root = chain.getRootInteraction();
```

### InteractionEntry

The entry tracks per-entry execution state (package
`com.hypixel.hytale.server.core.entity`):

```java
InteractionEntry entry = context.getEntry();
int index = entry.getIndex();
```

### Forking Contexts

`fork(...)` starts a new (forked) chain. Unlike a no-arg copy, the overloads take
arguments and return an `InteractionChain`:

```java
// fork(InteractionType, InteractionContext, RootInteraction, boolean)
InteractionChain forked = context.fork(type, context, rootInteraction, false);
```

---

## Receiving Contexts

`InteractionContext` is created by the interaction system (via internal static
factories such as `forInteraction(...)`); plugins do not construct it directly.

### Context in Custom Interactions

When implementing custom interactions, you receive the context:

```java
@Override
public void tick(Ref<EntityStore> ref, LivingEntity entity, boolean isFirstTick,
                 float deltaTime, InteractionType type, InteractionContext context,
                 CooldownHandler cooldown) {
    // Context is fully initialized
    // Access any data you need
}
```

---

## Usage Examples

### Complete Custom Operation

```java
public class ApplyBurnOp implements Operation {
    @Override
    public void tick(Ref<EntityStore> ref, LivingEntity entity, boolean isFirstTick,
                     float deltaTime, InteractionType type, InteractionContext context,
                     CooldownHandler cooldown) {
        if (!isFirstTick) {
            return;
        }

        DynamicMetaStore<InteractionContext> meta = context.getMetaStore();

        // Get target from previous Selector operation
        Ref<EntityStore> target = meta.getMetaObject(Interaction.TARGET_ENTITY);
        if (target == null || !target.isValid()) {
            return;
        }

        // Get burn duration from item's InteractionVars (a String->String map)
        Map<String, String> vars = context.getInteractionVars();
        float burnDuration = vars.containsKey("BurnDuration")
            ? Float.parseFloat(vars.get("BurnDuration")) : 5.0f;

        // Apply burn effect to target
        LivingEntity targetEntity = target.get(LivingEntity.class);
        if (targetEntity != null) {
            // Apply effect logic...
        }
    }

    // ... other Operation methods
}
```

### Conditional Branching with Meta

```java
public class CheckCriticalHitOp implements Operation {
    private final Label critLabel;
    private final Label normalLabel;

    public CheckCriticalHitOp(Label critLabel, Label normalLabel) {
        this.critLabel = critLabel;
        this.normalLabel = normalLabel;
    }

    @Override
    public void tick(..., InteractionContext context, ...) {
        Damage damage = context.getMetaStore().getMetaObject(Interaction.DAMAGE);

        if (damage != null && damage.isCritical()) {
            context.jump(critLabel);
        } else {
            context.jump(normalLabel);
        }
    }
}
```

---

## Related Documentation

- [Operation System](interactions-operations.md) - Execution model and OperationsBuilder
- [interactions.md](interactions.md) - Interaction types and configuration
- [items.md](items.md) - Item definitions and InteractionVars
- [entities.md](entities.md#interactionmanager) - InteractionManager component

---

## Gotchas & Errors

- **Symptom:** code won't compile against `context.getMeta(...)` / `setMeta(...)` → `InteractionContext` exposes no such convenience methods. Fix: go through the `DynamicMetaStore` from `getMetaStore()`, using `getMetaObject(key)` / `putMetaObject(key, value)`.
- **Symptom:** `context.advanceOperation()` won't compile → there is no `advanceOperation()` method. Fix: read/write the position directly with `getOperationCounter()` / `setOperationCounter(counter + 1)`.
- **Symptom:** you can't construct your own `MetaKey<T>` → `MetaKey` has a package-private constructor and no public `create(...)` factory, so plugins cannot define arbitrary keys. Fix: use the predefined standard keys on `Interaction` (e.g. `Interaction.TARGET_ENTITY`), or carry custom data via the item's `InteractionVars`.
- **Symptom:** a meta read returns `null` mid-chain → meta values are only present if an earlier operation set them, and a skipped/branched-past operation never runs. Fix: null-check every `getMetaObject(...)` result before use (e.g. `TARGET_ENTITY` is unset until a `Selector` runs).
- **Symptom:** `getInteractionVars()` values come back as the wrong type → it returns a plain `Map<String, String>`; there are no typed accessors. Fix: parse manually (`Float.parseFloat`, `Integer.parseInt`) and supply your own defaults.
- **Symptom:** `getOriginalItemType()` doesn't `.equals()` an `ItemType` → it returns an `Item` (the item config), not an `ItemType`. Fix: compare against the right type when detecting item swaps.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
