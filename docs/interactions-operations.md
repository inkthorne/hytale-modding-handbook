# Operation System

**Doc type:** Java API · **Verified against build-12**

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
| `Collector` | `interaction.operation` | Visitor receiving callbacks during `walk()` traversal |
| `CollectorTag` | `interaction.operation` | Identifies which branch is visited (SerialTag, ParallelTag, ...) |
| `WaitForDataFrom` | `protocol` | Enum controlling client/server execution sync |

---

## Operation Interface

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.operation`

The `Operation` interface defines the contract for executable interaction steps.

### Core Methods

```java
public interface Operation {
    // Server-side execution (called every frame while active)
    void tick(Ref<EntityStore> ref, LivingEntity entity, boolean isFirstTick,
              float deltaTime, InteractionType type, InteractionContext context,
              CooldownHandler cooldown);

    // Client-side prediction (mirrors tick for client simulation)
    void simulateTick(Ref<EntityStore> ref, LivingEntity entity, boolean isFirstTick,
                      float deltaTime, InteractionType type, InteractionContext context,
                      CooldownHandler cooldown);

    // Called when operation becomes active
    void handle(Ref<EntityStore> ref, boolean isStart, float deltaTime,
                InteractionType type, InteractionContext context);

    // Determines client/server sync behavior
    WaitForDataFrom getWaitForDataFrom();

    // Returns conflict resolution rules
    InteractionRules getRules();

    // Tag-based metadata for the operation
    Int2ObjectMap<IntSet> getTags();

    // For wrapped/decorated operations
    Operation getInnerOperation();
}
```

### tick() vs simulateTick()

| Method | Runs On | Purpose |
|--------|---------|---------|
| `tick()` | Server | Authoritative execution with full world access |
| `simulateTick()` | Client | Prediction for responsive feel; may be corrected |

Both methods receive identical parameters:
- `ref` - Entity store reference for the executing entity
- `entity` - The `LivingEntity` performing the operation
- `isFirstTick` - `true` on the first frame of this operation
- `deltaTime` - Time since last frame (for timing calculations)
- `type` - The `InteractionType` (PRIMARY, SECONDARY, etc.)
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
| `simulateTick()` | Runtime | Every client frame | Client-side prediction |
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

Tags identify which branch is being visited in container interactions:

| Interaction Type | Tag | Example |
|-----------------|-----|---------|
| `Serial` | `SerialTag.of(index)` | `SerialTag.of(0)`, `SerialTag.of(1)` |
| `Parallel` | `ParallelTag.of(index)` | `ParallelTag.of(0)` |
| `Chaining` | `ChainingTag.of(index)` | `ChainingTag.of(2)` |
| `Charging` | `ChargingTag.of(level)` | `ChargingTag.of(0.5f)` |
| `FirstClick` | `StringTag` | `TAG_CLICK`, `TAG_HELD` |

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

The labels passed to `addOperation()` become available for the operation to jump to during execution.

---

## How Interactions Compile to Operations

When an interaction chain starts, the system:

1. **Collects** all interactions in the chain
2. **Calls** `compile(OperationsBuilder)` on each
3. **Builds** the final `Operation[]` array
4. **Executes** operations sequentially via `tick()`

### Compilation Example

A `Serial` interaction containing two children compiles like this:

```java
// Serial with children A, B
@Override
public void compile(OperationsBuilder builder) {
    childA.compile(builder);  // Add A's operations
    childB.compile(builder);  // Add B's operations
}
// Result: [A-ops..., B-ops...]
```

A `Parallel` interaction is more complex, using labels to coordinate:

```java
// Parallel with children A, B
@Override
public void compile(OperationsBuilder builder) {
    Label aEnd = builder.createUnresolvedLabel();
    Label bEnd = builder.createUnresolvedLabel();

    // A's operations (jump to aEnd when done)
    childA.compile(builder);
    builder.jump(aEnd);

    // B's operations
    childB.compile(builder);
    builder.resolveLabel(bEnd);

    builder.resolveLabel(aEnd);
    // Continue after both complete
}
```

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
    public void tick(Ref<EntityStore> ref, LivingEntity entity, boolean isFirstTick,
                     float deltaTime, InteractionType type, InteractionContext context,
                     CooldownHandler cooldown) {
        if (isFirstTick) {
            // Initialize on first frame
            elapsed = 0f;
        }

        elapsed += deltaTime;

        if (elapsed >= duration) {
            // Operation complete - advance to next
            context.advanceOperation();
        }
    }

    @Override
    public void simulateTick(Ref<EntityStore> ref, LivingEntity entity, boolean isFirstTick,
                             float deltaTime, InteractionType type, InteractionContext context,
                             CooldownHandler cooldown) {
        // Client prediction - usually mirrors tick()
        tick(ref, entity, isFirstTick, deltaTime, type, context, cooldown);
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

    @Override
    public InteractionRules getRules() {
        return InteractionRules.DEFAULT_RULES;
    }

    @Override
    public Int2ObjectMap<IntSet> getTags() {
        return Int2ObjectMaps.emptyMap();
    }

    @Override
    public Operation getInnerOperation() {
        return null;  // Not wrapping another operation
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
        context.advanceOperation();
    }
}
```

### Conditional Completion

Some operations complete based on conditions:

```java
@Override
public void tick(..., InteractionContext context, ...) {
    if (targetReached || cancelled) {
        context.advanceOperation();
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

Backtick-quoted error strings below are the literal messages thrown by the build-12 operation system (verified against `HytaleServer.jar`).

- **`No operations to execute`** → an interaction compiled to an empty `Operation[]` (e.g. a container interaction whose children all dropped out). Fix: ensure `compile(OperationsBuilder)` adds at least one operation.
- **`Could not find the origin for the operation.`** → the runtime could not locate the operation's origin while resolving a jump/label. Fix: every `createUnresolvedLabel()` must be paired with a `resolveLabel(...)` before `build()` (see [Label System](#label-system)).
- **`This operation does not allow you to jump to an operation in the future, only the past. Index name:`** → a runtime `context.jump(...)` targeted a label resolved *later* in the sequence. Fix: only jump backward (e.g. loops); for skip-forward branching, structure with a label resolved at the skip point rather than jumping past unresolved operations.
- **`Cannot set a negative operation index:`** / **`Cannot set an operation index higher than the highest operation index:`** → `setOperationCounter(...)` (or a jump) addressed a slot outside the built operation array. Fix: keep the counter within `[0, build().length - 1]`; advance by `+1` rather than computing arbitrary indices.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
