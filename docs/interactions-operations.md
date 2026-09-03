---
title: "Operation System"
description: "Hytale's interaction Operation system — how interactions compile to operation arrays via OperationsBuilder, execute per-tick, control flow with labels and jumps, and sync to clients."
seo:
  type: TechArticle
---

# Operation System

**Doc type:** Java API · **Verified against 0.5.9**

> **Prerequisites:** Read [interactions.md](interactions.md) first for an overview of the interaction system.
>
> **See also:** [InteractionContext](interactions-context.md) for execution state, [interactions.md](interactions.md) for interaction types.

The Operation system is the low-level execution model that powers all interactions. When an interaction runs, it compiles into a sequence of Operations that execute frame-by-frame.

## Overview

Every `Interaction` implements the `Operation` interface. The interaction system:

1. **Compiles** interactions into operation arrays via `OperationsBuilder`
2. **Executes** operations sequentially, calling `tick()` each frame
3. **Controls flow** using labels and conditional jumps
4. **Synchronizes** client/server via `simulateTick()` for prediction

Understanding Operations is essential for:
- Creating custom interactions with complex control flow
- Debugging interaction execution
- Understanding timing and frame-by-frame behavior

## Architecture
```
Operation System
├── Operation interface (tick / simulateTick / handle + getWaitForDataFrom / getRules / getTags)
├── Loading phase
│   ├── walk(Collector) — tree traversal, metadata collection
│   │   ├── Collector (ListCollector / SingleCollector / TreeCollector)
│   │   └── CollectorTag (SerialTag / ParallelTag / ChainingTag / ...)
│   └── compile(OperationsBuilder) — flatten tree to Operation[]
├── OperationsBuilder (addOperation + Label flow control)
│   └── Label system (createLabel / createUnresolvedLabel / resolveLabel / jump)
└── Runtime execution
    ├── handle(isStart) → tick()/simulateTick() per frame → handle(end)
    └── WaitForDataFrom (None / Server / Client) — client/server sync
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Operation` | `server.core.modules.interaction.interaction.operation` | Interface for executable interaction steps |
| `OperationsBuilder` | `server.core.modules.interaction.interaction.operation` | Builds operation sequences with label-based flow control |
| `Label` | `interaction.operation` | Jump target within an operation sequence |
| `Collector` | `interaction.config.data` | Visitor receiving callbacks during `walk()` traversal (`ListCollector`, `SingleCollector`, `TreeCollector` live here too) |
| `CollectorTag` | `interaction.config.data` | Identifies which branch is visited. `StringTag` is the generic implementation and lives here too; the indexed tags are nested classes on the interaction that emits them (see [CollectorTag](#collectortag)) |
| `WaitForDataFrom` | `protocol` | Enum controlling client/server execution sync |

---

## Operation Interface

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.operation`

The `Operation` interface defines the contract for executable interaction steps.

### Core Methods

```java
public interface Operation {
    // Server-side execution (called every frame while active)
    void tick(Ref<EntityStore> ref, boolean isFirstTick, float deltaTime,
              InteractionType type, InteractionContext context, CooldownHandler cooldown);

    // Server-side simulation of the client's prediction (mirrors tick)
    void simulateTick(Ref<EntityStore> ref, boolean isFirstTick, float deltaTime,
                      InteractionType type, InteractionContext context, CooldownHandler cooldown);

    // Called when operation becomes active / ends (default: no-op)
    default void handle(Ref<EntityStore> ref, boolean isStart, float deltaTime,
                        InteractionType type, InteractionContext context);

    // Determines client/server sync behavior
    WaitForDataFrom getWaitForDataFrom();

    // Returns conflict resolution rules (default: null — "no rules of my own")
    @Nullable default InteractionRules getRules();

    // Tag-based metadata for the operation (default: Int2ObjectMaps.emptyMap())
    default Int2ObjectMap<IntSet> getTags();

    // Unwraps decorators (default: follows Operation.NestedOperation.inner()
    // until a non-nested operation is reached, so a plain operation returns itself)
    default Operation getInnerOperation();
}
```

There is **no** `LivingEntity` parameter — resolve components from `ref` through
`context.getCommandBuffer()`. Only `tick`, `simulateTick` and `getWaitForDataFrom` are abstract.

> **Gotcha:** the two easy-to-guess defaults are both wrong. `getRules()` defaults to `null`,
> **not** `InteractionRules.DEFAULT_RULES`; and `getInnerOperation()` defaults to *unwrapping*
> (`while (op instanceof NestedOperation) op = op.inner();`), so it returns `this` for an
> ordinary operation and never `null`. Override either only if you mean to change that.

### tick() vs simulateTick()

| Method | Runs On | Purpose |
|--------|---------|---------|
| `tick()` | Server | Authoritative execution with full world access |
| `simulateTick()` | Server, replaying the client's prediction | Mirrors what the client predicted so the two chains can be compared (`InteractionManager` throws `Simulation and server tick are not in sync` when they diverge) |

Both methods receive identical parameters:
- `ref` - Entity store reference for the executing entity
- `isFirstTick` - `true` on the first frame of this operation
- `deltaTime` - Time since last frame (for timing calculations)
- `type` - The `InteractionType` (`Primary`, `Secondary`, etc.)
- `context` - Execution state container (see [InteractionContext](interactions-context.md))
- `cooldown` - Manages cooldown timers (see [Cooldowns](interactions.md#cooldown-system))

### WaitForDataFrom Enum

Controls synchronization between client and server:

**Package:** `com.hypixel.hytale.protocol`

| Value | Behavior |
|-------|----------|
| `None` | Execute immediately on both client and server |
| `Server` | Client waits for server confirmation before executing |
| `Client` | Server waits for client data (rare, for client-authoritative actions) |

---

## Interaction Lifecycle

Understanding when each method is called helps when implementing custom interactions.

### Overview Diagram

```
ASSET LOADING PHASE
───────────────────
1. JSON parsed → Interaction tree built
2. walk(collector) → Traverse tree, collect metadata
3. compile(builder) → Build flat Operation[] array

RUNTIME EXECUTION PHASE
───────────────────────
4. handle(isStart=true) → Operation becomes active
5. tick() / simulateTick() → Called every frame
6. handle(isStart=false) → Operation completes
7. Advance to next operation → Repeat from step 4
```

### Method Call Timing

| Method | Phase | When Called | Purpose |
|--------|-------|-------------|---------|
| `walk()` | Loading | Asset compilation | Traverse interaction tree, collect metadata |
| `compile()` | Loading | After walk() | Build flat Operation[] from tree |
| `handle(true)` | Runtime | Operation starts | Initialize operation state |
| `tick()` | Runtime | Every server frame | Execute operation logic |
| `simulateTick()` | Runtime | Every frame of a predicted chain | Server-side replay of the client prediction |
| `handle(false)` | Runtime | Operation ends | Cleanup operation state |

---

## walk() Method

The `walk()` method traverses the interaction tree using the Visitor pattern. It's called during asset loading to collect metadata about all nested interactions.

### Method Signature

```java
boolean walk(Collector collector, InteractionContext context)
```

**Returns:** `true` to stop traversal early, `false` to continue

### Collector Interface

`Collector` is a visitor that receives callbacks as the tree is traversed:

```java
public interface Collector {
    void start();           // Called once at traversal start
    void into(InteractionContext ctx, Interaction interaction);   // Entering nested interaction
    boolean collect(CollectorTag tag, InteractionContext ctx, Interaction interaction);  // Process node
    void outof();           // Exiting nested interaction
    void finished();        // Called once at traversal end
}
```

### Traversal Flow

```
InteractionManager.walkInteraction(collector, context, tag, interactionId)
  → collector.collect(tag, context, interaction)
  → collector.into(context, interaction)
  → interaction.walk(collector, context)   // Recursive
  → collector.outof()
```

### Collector Implementations

| Implementation | Purpose | Behavior |
|---------------|---------|----------|
| `ListCollector<T>` | Collect all interactions | Builds flat list, never stops early |
| `SingleCollector<T>` | Find first match | Stops when result found |
| `TreeCollector<T>` | Build tree structure | Maintains parent-child relationships |

### CollectorTag

Tags identify which branch is being visited in container interactions. Only `CollectorTag.ROOT`
and `StringTag` (`interaction.config.data`) are generic; the indexed tags are **nested classes on
the interaction that emits them**, and two of them are package-private, so a plugin can compare
tags via `equals`/`toString` but cannot name their types:

| Interaction Type | Tag | Declared on | Visibility |
|-----------------|-----|-------------|------------|
| `Serial` | `SerialTag.of(int index)` | `SerialInteraction` (`config.none`) | package-private |
| `Parallel` | `ParallelTag.of(int index)` | `ParallelInteraction` (`config.none`) | package-private |
| `Chaining` | `ChainingTag.of(int index)` | `ChainingInteraction` (`config.client`) | `public final` |
| `Charging` | `ChargingTag.of(float seconds)` | `ChargingInteraction` (`config.client`) | `public final` (`getSeconds()` returns `double`) |
| `FirstClick` | `StringTag.of(String)` | `config.data` | `public`; the instances are `FirstClickInteraction.TAG_CLICK` / `TAG_HELD` |

The root of every traversal is tagged `CollectorTag.ROOT`.

### Implementation Patterns

**Container interactions** (have children):
```java
@Override
public boolean walk(Collector collector, InteractionContext context) {
    for (int i = 0; i < interactions.length; i++) {
        if (InteractionManager.walkInteraction(
                collector, context, SerialTag.of(i), interactions[i])) {
            return true;  // Stop if collector signals done
        }
    }
    return false;
}
```

**Leaf interactions** (no children):
```java
@Override
public boolean walk(Collector collector, InteractionContext context) {
    return false;  // Nothing to traverse
}
```

---

## OperationsBuilder

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.operation`

`OperationsBuilder` constructs operation sequences with label-based flow control. Interactions override `compile(OperationsBuilder)` to build their operation sequence.

### Building Operation Sequences

```java
public class OperationsBuilder {
    // Add an operation to the sequence
    void addOperation(Operation operation);
    // Add an operation that may jump to the given labels (wrapped so context.getLabel(i) sees them)
    void addOperation(Operation operation, Label... jumpTargets);

    // Build the final operation array
    Operation[] build();
}
```

### Basic Usage

```java
@Override
public void compile(OperationsBuilder builder) {
    // Operations execute in order
    builder.addOperation(new PlayAnimationOp("SwingDown"));
    builder.addOperation(new WaitOp(0.2f));
    builder.addOperation(new DealDamageOp());
}
```

---

## Label System

Labels enable non-linear control flow within operation sequences. This is how conditional branching, loops, and early exits work.

### Creating Labels

```java
public class OperationsBuilder {
    // Create a label at the current position
    Label createLabel();

    // Create a placeholder label (position set later)
    Label createUnresolvedLabel();

    // Set an unresolved label to the current position
    void resolveLabel(Label label);

    // Jump to a label from current position
    void jump(Label target);
}
```

### Control Flow Patterns

#### Conditional Branch

```java
@Override
public void compile(OperationsBuilder builder) {
    Label skipDamage = builder.createUnresolvedLabel();

    // Check condition - operation may jump to skipDamage
    builder.addOperation(new ConditionalCheckOp(), skipDamage);

    // Damage (skipped if condition fails)
    builder.addOperation(new DealDamageOp());

    // Target for skip
    builder.resolveLabel(skipDamage);

    // Continue with cleanup (always runs)
    builder.addOperation(new CleanupOp());
}
```

#### Early Exit

```java
@Override
public void compile(OperationsBuilder builder) {
    Label exit = builder.createUnresolvedLabel();

    builder.addOperation(new ValidateOp(), exit);  // Jump to exit on failure
    builder.addOperation(new ExecuteOp());
    builder.addOperation(new FinishOp());

    builder.resolveLabel(exit);  // Exit point
}
```

#### Loop

```java
@Override
public void compile(OperationsBuilder builder) {
    Label loopStart = builder.createLabel();  // Mark loop start
    Label loopEnd = builder.createUnresolvedLabel();

    builder.addOperation(new CheckLoopConditionOp(), loopEnd);  // Exit when done
    builder.addOperation(new LoopBodyOp());
    builder.jump(loopStart);  // Jump back to start

    builder.resolveLabel(loopEnd);  // Exit point
}
```

### Runtime Jumps

Operations can trigger jumps at runtime via `InteractionContext`:

```java
// Inside an Operation's tick() method
public void tick(..., InteractionContext context, ...) {
    if (shouldSkip) {
        // Jump to a label set during compilation
        context.jump(skipLabel);
    }
}
```

The labels passed to `addOperation()` become available for the operation to jump to during execution — the builder wraps it in a `LabelOperation` that calls `context.setLabels(labels)` before each `tick`/`simulateTick`/`handle`, so inside the operation `context.getLabel(i)` (guarded by `context.hasLabels()`) returns the *i*-th label you passed. A `builder.jump(label)` emits a `JumpOperation` that sets the counter to `label.getIndex()` and finishes.

---

## How Interactions Compile to Operations

When an interaction chain starts, the system:

1. **Collects** all interactions in the chain
2. **Calls** `compile(OperationsBuilder)` on each
3. **Builds** the final `Operation[]` array
4. **Executes** operations sequentially via `tick()`

### Compilation Example

`Interaction.compile` defaults to `builder.addOperation(this)` — a leaf interaction *is* its own
operation. Containers override it. `Serial` simply inlines its children in order:

```java
// SerialInteraction
@Override
public void compile(OperationsBuilder builder) {
    for (String id : this.interactions) {
        Interaction.getInteractionOrUnknown(id).compile(builder);
    }
}
// Result: [A-ops..., B-ops...]
```

`FirstClick` is the shipped example of label-based branching — it registers itself with a
`failedLabel` it can jump to at runtime, then resolves both arms:

```java
// FirstClickInteraction (condensed)
@Override
public void compile(OperationsBuilder builder) {
    if (this.click == null && this.held == null) {
        builder.addOperation(this);      // nothing to branch to
        return;
    }
    Label failedLabel = builder.createUnresolvedLabel();
    Label endLabel = builder.createUnresolvedLabel();

    builder.addOperation(this, failedLabel);        // this op may jump to failedLabel
    if (this.click != null) {
        Interaction.getInteractionOrUnknown(this.click).compile(builder);
    }
    if (this.held != null) {
        builder.jump(endLabel);                     // skip the held arm
    }
    builder.resolveLabel(failedLabel);
    if (this.held != null) {
        Interaction.getInteractionOrUnknown(this.held).compile(builder);
    }
    builder.resolveLabel(endLabel);
}
```

> **Not every container compiles to operations.** `Parallel` does **not** override `compile()`
> and uses no labels: it is a single operation whose `tick0` runs its first entry with
> `context.execute(RootInteraction.getRootInteractionOrUnknown(interactions[0]))` and forks the
> rest with `context.fork(context.duplicate(), root, true)`, then finishes. Its `Interactions`
> are `RootInteraction` ids (minimum two), not `Interaction` ids like `Serial`'s.

---

## Execution Flow

### Frame-by-Frame Execution

Each frame during an interaction:

1. **Get current operation** from the operation array
2. **Call** `tick()` with current context
3. **Check** if operation is complete
4. **Advance** to next operation (or jump if label triggered)
5. **Repeat** until all operations complete

### Operation Lifecycle

```
handle(isStart=true)  →  tick() [frame 1]  →  tick() [frame 2]  →  ...  →  handle(isStart=false)
```

- `handle(isStart=true)` - Called when operation becomes active
- `tick()` - Called every frame while active
- `handle(isStart=false)` - Called when operation completes/exits

---

## Custom Operation Implementation

To create a custom operation, implement the `Operation` interface:

```java
public class MyCustomOp implements Operation {
    private final float duration;
    private float elapsed = 0f;

    public MyCustomOp(float duration) {
        this.duration = duration;
    }

    @Override
    public void tick(Ref<EntityStore> ref, boolean isFirstTick, float deltaTime,
                     InteractionType type, InteractionContext context,
                     CooldownHandler cooldown) {
        if (isFirstTick) {
            // Initialize on first frame
            elapsed = 0f;
        }

        elapsed += deltaTime;

        if (elapsed >= duration) {
            // Operation complete - the manager advances to the next operation
            context.getState().state = InteractionState.Finished;
        }
    }

    @Override
    public void simulateTick(Ref<EntityStore> ref, boolean isFirstTick, float deltaTime,
                             InteractionType type, InteractionContext context,
                             CooldownHandler cooldown) {
        // Client-prediction mirror - must reach the same counter/state as tick()
        tick(ref, isFirstTick, deltaTime, type, context, cooldown);
    }

    @Override
    public void handle(Ref<EntityStore> ref, boolean isStart, float deltaTime,
                       InteractionType type, InteractionContext context) {
        // Optional: Setup/cleanup logic
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.None;  // No sync needed
    }

    // getRules(), getTags() and getInnerOperation() have usable defaults —
    // override getRules() only to declare conflict rules of your own:
    @Override
    public InteractionRules getRules() {
        return InteractionRules.DEFAULT_RULES;
    }
}
```

---

## Common Operation Patterns

### Timed Operations

Most operations track elapsed time:

```java
@Override
public void tick(..., float deltaTime, ..., InteractionContext context, ...) {
    elapsed += deltaTime;
    if (elapsed >= runTime) {
        context.getState().state = InteractionState.Finished;
    }
}
```

### Conditional Completion

Some operations complete based on conditions:

```java
@Override
public void tick(..., InteractionContext context, ...) {
    if (targetReached) {
        context.getState().state = InteractionState.Finished;
    } else if (cancelled) {
        context.getState().state = InteractionState.Failed;   // takes the Failed branch, if any
    }
}
```

### Triggering Effects

Effects typically fire on first tick:

```java
@Override
public void tick(..., boolean isFirstTick, ...) {
    if (isFirstTick) {
        playSound();
        playAnimation();
        spawnParticles();
    }
}
```

---

## Related Documentation

- [InteractionContext](interactions-context.md) - Execution state and data access
- [interactions.md](interactions.md) - Interaction types and configuration
- [interactions-combo.md](interactions-combo.md) - Combo and chaining systems
- [interactions-flow.md](interactions-flow.md) - Control flow interactions

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the interaction operation system (`OperationsBuilder` / `InteractionManager`, verified against `HytaleServer.jar`).

- **`Label already resolved`** (`IllegalArgumentException` from `OperationsBuilder.resolveLabel`) → `resolveLabel(...)` was called on a label that already has a position — either twice on the same unresolved label, or on a label made with `createLabel()` (which is resolved at creation). Fix: resolve each `createUnresolvedLabel()` exactly once; never call `resolveLabel` on a `createLabel()` label.
- **`Failed to find operation during simulation tick of chain '`** — assembled line ends with the root id and a closing quote (`IllegalStateException`) → the operation counter points outside the built `Operation[]`. An unresolved label still holds `Integer.MIN_VALUE`, so jumping to one you forgot to `resolveLabel(...)` lands here; so does `setOperationCounter(...)` with an arbitrary index. Fix: pair every `createUnresolvedLabel()` with a `resolveLabel(...)` before `build()`, and keep the counter within `[0, build().length - 1]`.
- **`Simulation and server tick are not in sync (operation position).`** / **`... (root interaction).`** → `simulateTick()` and `tick()` diverged (different jump, or one finished and the other didn't), so the server's prediction replay and its authoritative run are at different counters. Fix: `simulateTick` must mirror `tick`'s flow control exactly (same `jump`/`Finished`/`Failed` decisions), differing only in world side-effects.
- **`Can't shift backwards`** (`InteractionManager.setGlobalTimeShift`) → a negative time shift was requested. Fix: time shifts are forward-only.
- **`Failed to find interaction: `** — the offending id follows → a chain referenced an interaction id that is not in the asset map. Fix: see [interactions.md — Gotchas](interactions.md#gotchas--errors).
- **Symptom:** your operation runs once and the chain hangs on it → nothing set the sync state. Fix: an operation must end its turn with `context.getState().state = InteractionState.Finished` (or `Failed`); there is no `advanceOperation()`.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
