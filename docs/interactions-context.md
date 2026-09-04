---
title: "InteractionContext"
description: "The Hytale InteractionContext — access entity references (owner, executor, targets), the held item, the meta store (hit locations, targets), and item-defined InteractionVars at runtime."
seo:
  type: TechArticle
---

# InteractionContext

**Doc type:** Java API · **Verified against 0.6.3**

> **Prerequisites:** Read [interactions.md](interactions.md) and [Operation System](interactions-operations.md) first.
>
> **See also:** [Item Definitions](items.md) for `InteractionVars`, [entities.md](entities.md#interactionmanager) for `InteractionManager`.

`InteractionContext` is the execution state container passed to operations during interaction execution. It provides access to entities, items, targeting data, and flow control.

## Overview

When an interaction runs, `InteractionContext` carries:

- **Entity references** - The owning entity, executing entity, and targets
- **Item state** - The held item being used
- **Meta store** - Key-value data like hit locations and targets (`DynamicMetaStore`)
- **InteractionVars** - Item-defined variable → `RootInteraction` bindings (a `Map<String, String>`)
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
├── InteractionVars (item-defined Map<varName, RootInteraction id>)
├── Flow control (jump(Label) / operation counter / labels)
└── Chain management
    ├── InteractionChain (getChain) + fork(...)
    └── InteractionEntry (getEntry)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `InteractionContext` | `server.core.entity` | Execution-state container passed to operations |
| `DynamicMetaStore` | `server.core.meta` (returned by `getMetaStore`) | Key-value store for passing data between operations |
| `MetaKey<T>` | `server.core.meta` | Type-safe key for meta-store values (obtained from a `MetaRegistry`, see [Custom Keys](#custom-meta-keys)) |
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
    BlockPosition getTargetBlock();         // Targeted block (meta TARGET_BLOCK), or null
    BlockPosition getTargetBlockRaw();      // 0.6.3+: raw client target (meta TARGET_BLOCK_RAW), or null
    CommandBuffer<EntityStore> getCommandBuffer();   // ECS access for the current tick (also a ComponentAccessor)
    InteractionManager getInteractionManager();

    // Item access
    ItemStack getHeldItem();                // The item being used
    void setHeldItem(ItemStack stack);
    byte getHeldItemSlot();                 // Slot index of held item
    ItemContainer getHeldItemContainer();   // Container the held item lives in
    Item getOriginalItemType();             // Item config when chain started

    // Meta store (dynamic data)
    DynamicMetaStore<InteractionContext> getMetaStore();     // context-scoped keys
    DynamicMetaStore<Interaction> getInstanceStore();        // per-entry keys (e.g. TIME_SHIFT)

    // InteractionVars (item-defined var -> RootInteraction id; may be null)
    Map<String, String> getInteractionVars();
    void setInteractionVarsGetter(Function<InteractionContext, Map<String, String>> getter);

    // Flow control
    void jump(Label label);                 // = setOperationCounter(label.getIndex())
    int getOperationCounter();
    void setOperationCounter(int counter);
    void setLabels(Label[] labels);         // set by the framework for labels passed to addOperation(op, labels...)
    boolean hasLabels();
    Label getLabel(int index);

    // Per-operation sync state (what an operation sets to finish/fail)
    InteractionSyncData getState();         // getState().state = InteractionState.Finished / Failed

    // Chain management
    InteractionChain getChain();
    InteractionEntry getEntry();
    InteractionContext duplicate();
    void execute(RootInteraction root);      // run a root interaction in this context
    // fork(...) overloads return InteractionChain and take args, e.g.:
    InteractionChain fork(InteractionType type, InteractionContext ctx,
                          RootInteraction root, boolean flag);

    // Static factories (used by the framework; see "Receiving Contexts")
    static InteractionContext forInteraction(InteractionManager mgr, Ref<EntityStore> ref,
                          InteractionType type, ComponentAccessor<EntityStore> accessor);
    static InteractionContext withoutEntity();
}
```

> **Note:** `InteractionContext` does **not** expose `getMeta`/`setMeta` convenience
> methods. Meta values are accessed through the `DynamicMetaStore` returned by
> `getMetaStore()`. There is no `advanceOperation()`: an operation finishes by setting
> `context.getState().state = InteractionState.Finished` (or `Failed`), after which
> `InteractionManager` advances the chain to the next operation.

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
        // Read the target's components through the tick's CommandBuffer
        TransformComponent transform =
            context.getCommandBuffer().getComponent(target, TransformComponent.getComponentType());
        if (transform != null) {
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
        Item item = heldItem.getItem();        // item config (there is no ItemType class)
        String itemId = heldItem.getItemId();
        int count = heldItem.getQuantity();

        // Access item data
        // ...
    }
}
```

### Original Item Type

Tracks the item config when the chain started. Useful for detecting item swaps.
`getOriginalItemType()` returns an `Item` (the item config); compare it with `ItemStack.getItem()`:

```java
@Override
public void tick(..., InteractionContext context, ...) {
    Item original = context.getOriginalItemType();
    ItemStack current = context.getHeldItem();

    if (current != null && current.getItem() != original) {
        // Item changed during interaction - might want to cancel
    }
}
```

The framework already handles this case for you: each interaction's `OnItemChangeBehavior`
(`Cancel` by default) decides what happens when the held item changes — see
[Held-Item Change Behavior](interactions.md#held-item-change-behavior).

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
| `TARGET_BLOCK_TYPE` | `BlockType` | Block targeting | 0.6.3+. Resolved `BlockType` of the targeted block |
| `TARGET_BLOCK_ROTATION_INDEX` | `Integer` | Block targeting | 0.6.3+. Rotation index of the targeted block |
| `TARGET_SLOT` | `Integer` | Inventory ops | Target inventory slot |
| `DAMAGE` | `Damage` | Damage ops | Damage calculation result |

> **`TIME_SHIFT` is not a context key.** `Interaction.TIME_SHIFT` (`MetaKey<Float>`) is
> registered on `Interaction.META_REGISTRY`, not `CONTEXT_META_REGISTRY`, so it lives in the
> per-entry store returned by `context.getInstanceStore()`
> (`DynamicMetaStore<Interaction>`) — the framework writes the leftover run time there when an
> interaction overruns. Reading it from `getMetaStore()` compiles but resolves the wrong slot.

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

`MetaKey` has a package-private constructor and exposes only `getId()`. There is no `MetaKey.create(...)` factory: keys come from a `MetaRegistry` — the standard ones are registered on `Interaction.CONTEXT_META_REGISTRY`, and plugins can register their own there (see [Custom Meta Keys](#custom-meta-keys)).

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
| `Interaction.TARGET_BLOCK_RAW` | `BlockPosition` | Block targeting | Raw client target position |
| `Interaction.TARGET_BLOCK_TYPE` | `BlockType` | Block targeting | 0.6.3+ |
| `Interaction.TARGET_BLOCK_ROTATION_INDEX` | `Integer` | Block targeting | 0.6.3+ |
| `Interaction.TARGET_SLOT` | `Integer` | Inventory ops | Target inventory slot |
| `Interaction.DAMAGE` | `Damage` | Damage ops | Damage calculation result |

One further key, `Interaction.TIME_SHIFT` (`MetaKey<Float>`), is registered on
`Interaction.META_REGISTRY` instead and therefore belongs to `context.getInstanceStore()`, not
the context store above.

#### Custom Meta Keys

`Interaction.CONTEXT_META_REGISTRY` is a public `MetaRegistry<InteractionContext>`; register a key
**once**, at plugin setup (a static field is the usual home), before any context is created. The
function supplies the initial value the store creates on first access:

```java
public static final MetaKey<Integer> BOUNCES =
    Interaction.CONTEXT_META_REGISTRY.registerMetaObject(ctx -> 0);

// later, inside an operation:
DynamicMetaStore<InteractionContext> meta = context.getMetaStore();
meta.putMetaObject(BOUNCES, meta.getMetaObject(BOUNCES) + 1);
```

`registerMetaObject(Function<K,T> initial, String keyName, Codec<T> codec)` registers a
*persistent* key (serialized with the store; the key name must be unique, or the registry throws
`Codec key is already registered.`). For item-driven tuning values, the item's `InteractionVars`
(below) are usually the simpler channel.

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

1. **Use the standard keys** where they fit - The `Interaction` constants cover targeting, hits, and damage; register your own on `Interaction.CONTEXT_META_REGISTRY` for anything else
2. **Check for null** - Meta values may not be set if earlier operations were skipped (`getIfPresentMetaObject` reads without creating a default)
3. **Type safety** - The `MetaKey<T>` generic ensures compile-time type checking

---

## InteractionVars

`InteractionVars` are per-item **bindings from a variable name to a `RootInteraction`**. A shared
chain leaves a hole — a `Replace` step naming a variable — and each item fills that hole with its
own root interaction, so one chain definition can serve every weapon that reuses it.

They are **not** loose tuning values: every value must resolve to a `RootInteraction`
(`Item.InteractionVars` is read with `RootInteraction.CHILD_ASSET_CODEC` and validated against
the `RootInteraction` asset store).

### Accessing InteractionVars

`getInteractionVars()` returns a plain `Map<String, String>` of *variable name → root-interaction
id*, and it can be `null`. By default it is the map of the item the chain started with
(`getOriginalItemType().getInteractionVars()`); `setInteractionVarsGetter(...)` swaps in another
source — NPC combat actions use this so an ability supplies its own vars.

```java
@Override
public void tick(..., InteractionContext context, ...) {
    Map<String, String> vars = context.getInteractionVars();
    String rootId = vars == null ? null : vars.get("Staff_Cast_Summon_Launch");

    if (rootId != null) {
        RootInteraction root = RootInteraction.getRootInteractionOrUnknown(rootId);
        context.execute(root);
    }
}
```

### Who reads them: the `Replace` interaction

`Replace` (`...interaction.config.none.ReplaceInteraction`) is the only interaction that consults
the map — *"Runs the interaction defined by the interaction variables if defined."*

| Key | Type | Description |
|-----|------|-------------|
| `Var` | string | Required. Name looked up in the item's `InteractionVars` |
| `DefaultValue` | RootInteraction | Used when the variable is absent — an id **or** an inline definition |
| `DefaultOk` | boolean | When `true`, falling back to `DefaultValue` is expected; otherwise a missing variable is logged at `SEVERE` (`Missing replacement interactions for interaction: …`) |

If neither the variable nor `DefaultValue` resolves, the step ends as `InteractionState.Failed`.

```json
{
  "Type": "Replace",
  "Var": "Fireball_Impact_2",
  "DefaultOk": true,
  "DefaultValue": {
    "Interactions": ["Weapon_Stick_Fire_Impact_Base"]
  }
}
```

(from `Server/ProjectileConfigs/Weapons/Stick/Projectile_Config_Fireball_Charged_2.json`)

### Item Definition with InteractionVars

Each value is either an id or an **inline `RootInteraction`** — which is how per-item tuning is
actually expressed: inherit a shared interaction with `Parent`, then override its fields.

```json
{
  "InteractionVars": {
    "Staff_Cast_Summon_Launch": "Staff_Cast_Launch",
    "Staff_Cast_Summon_Effect": "Staff_Cast_Effect",
    "Staff_Cast_Summon_Cost": {
      "Interactions": [
        { "Parent": "Staff_Cast_Cost", "StatModifiers": { "Mana": -50 } }
      ]
    }
  }
}
```

(condensed from `Server/Item/Items/Weapon/Staff/Weapon_Staff_Frost.json`)

Common shipped variable names are chain-slot names, not settings: `Staff_Cast_Summon_Launch`,
`Spear_Swing_Left_Damage`, `Guard_Wield`, `Item_Throw_Projectile`, `SpawnNPC_Entity`.

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
`advanceOperation()` convenience method — an operation ends its own turn by setting the
sync state, and the manager then advances the counter:

```java
context.getState().state = InteractionState.Finished;   // done; move to the next operation
context.getState().state = InteractionState.Failed;     // done; take the Failed branch (if any)

// The counter itself is also readable/writable (this is what jump(label) does):
int currentOp = context.getOperationCounter();
context.setOperationCounter(currentOp + 1);
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

`InteractionContext` is created by the interaction system (via the static factories
`forInteraction(...)`, `forProxyEntity(...)` and `withoutEntity()`); plugins normally do not
construct it directly.

### Context in Custom Interactions

When implementing custom interactions, you receive the context (there is no `LivingEntity`
parameter — resolve components from `ref` via `context.getCommandBuffer()`):

```java
@Override
public void tick(Ref<EntityStore> ref, boolean isFirstTick, float deltaTime,
                 InteractionType type, InteractionContext context,
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
    public void tick(Ref<EntityStore> ref, boolean isFirstTick, float deltaTime,
                     InteractionType type, InteractionContext context,
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

        // Apply burn effect to target (e.g. EffectControllerComponent.addEffect(...) via
        // context.getCommandBuffer(); see interactions-combat.md#applyeffect)
        // ...
        context.getState().state = InteractionState.Finished;
    }

    // ... other Operation methods
}
```

### Conditional Branching with Meta

```java
public class CheckCriticalHitOp implements Operation {
    private static final float CRIT_THRESHOLD = 20f;
    private final Label critLabel;
    private final Label normalLabel;

    public CheckCriticalHitOp(Label critLabel, Label normalLabel) {
        this.critLabel = critLabel;
        this.normalLabel = normalLabel;
    }

    @Override
    public void tick(..., InteractionContext context, ...) {
        Damage damage = context.getMetaStore().getIfPresentMetaObject(Interaction.DAMAGE);

        // Damage has no "critical" flag; branch on the amount (or your own meta key)
        if (damage != null && damage.getAmount() >= CRIT_THRESHOLD) {
            context.jump(critLabel);
        } else {
            context.jump(normalLabel);
        }
        context.getState().state = InteractionState.Finished;
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
- **Symptom:** `context.advanceOperation()` won't compile → there is no `advanceOperation()` method. Fix: finish the operation with `context.getState().state = InteractionState.Finished` (or `Failed`); the manager advances the counter. `setOperationCounter(...)`/`jump(label)` exist for explicit repositioning.
- **Symptom:** you can't construct your own `MetaKey<T>` → `MetaKey` has a package-private constructor and no `create(...)` factory. Fix: register the key once on `Interaction.CONTEXT_META_REGISTRY.registerMetaObject(ctx -> initialValue)` (see [Custom Meta Keys](#custom-meta-keys)), or carry item-driven values via `InteractionVars`.
- **Symptom:** `tick(..., LivingEntity entity, ...)` doesn't override anything → neither `Operation.tick` nor `Interaction.tick` takes a `LivingEntity`; the signature is `tick(Ref<EntityStore>, boolean, float, InteractionType, InteractionContext, CooldownHandler)`. Fix: drop the parameter and resolve components from `ref` through `context.getCommandBuffer()`.
- **Symptom:** a meta read returns `null` mid-chain → meta values are only present if an earlier operation set them, and a skipped/branched-past operation never runs. Fix: null-check every `getMetaObject(...)` result before use (e.g. `TARGET_ENTITY` is unset until a `Selector` runs).
- **Symptom:** an `InteractionVars` entry like `"Damage": 25.0` fails validation, or `getInteractionVars()` never returns the number you put there → the map is *variable name → `RootInteraction` id*, not a bag of tuning values; `Item.InteractionVars` is read with `RootInteraction.CHILD_ASSET_CODEC` and every value is validated against the RootInteraction asset store. Fix: bind the variable to a root interaction (an id, or an inline definition with `Parent` plus overrides) and put the numbers inside that interaction.
- **Symptom:** `getInteractionVars()` throws `NullPointerException` → it returns `null` when the chain has no originating item (`getOriginalItemType()` is null) and no custom getter was installed. Fix: null-check the map before `get(...)`.
- **Symptom:** `ItemStack.getItemType()` / `getCount()` won't compile → there is no `ItemType` class in the item API; the accessors are `getItem()` (the `Item` config), `getItemId()` and `getQuantity()`. `getOriginalItemType()` likewise returns an `Item` — compare it with `getHeldItem().getItem()` when detecting item swaps (or just set `OnItemChangeBehavior`). (Grepping the jar does turn up one `ItemType`: a private nested enum in `SortType` that classifies items for inventory sorting. It is unrelated to `ItemStack`.)

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
