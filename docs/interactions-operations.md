---
title: "Operation System"
description: "Hytale's interaction Operation system — how interactions compile to operation arrays via OperationsBuilder, execute per-tick, control flow with labels and jumps, and sync to clients."
seo:
  type: TechArticle
---

# Operation System

**Doc type:** Java API · **Verified against 0.7.2**

> **Prerequisites:** Read [interactions.md](interactions.md) first for an overview of the interaction system.
>
> **See also:** [InteractionContext](interactions-context.md) for execution state, [interactions.md](interactions.md) for interaction types.

The Operation system is the low-level execution model that powers all interactions. Each root interaction is compiled, when its assets load, into a flat sequence of Operations that a chain then executes tick by tick.

## Overview

Every `Interaction` implements the `Operation` interface. The interaction system:

1. **Compiles** interactions into operation arrays via `OperationsBuilder`
2. **Executes** operations sequentially, calling `tick()` each frame
3. **Controls flow** using labels and conditional jumps
4. **Synchronizes** client/server: for an entity with no remote client, the server also plays the client's part through `simulateTick()`

Understanding Operations is essential for:
- Creating custom interactions with complex control flow
- Debugging interaction execution
- Understanding timing and frame-by-frame behavior

## Architecture
```
Operation System
├── Operation interface (tick / simulateTick / handle + getWaitForDataFrom / getRules / getTags)
├── Loading phase (RootInteraction.build)
│   └── compile(OperationsBuilder) — flatten tree to Operation[]
├── On-demand analysis
│   └── walk(Collector) — tree traversal, metadata collection
│       ├── Collector (ListCollector / SingleCollector / TreeCollector)
│       └── CollectorTag (SerialTag / ParallelTag / ChainingTag / ...)
├── OperationsBuilder (addOperation + Label flow control)
│   └── Label system (createLabel / createUnresolvedLabel / resolveLabel / jump)
└── Runtime execution
    ├── per tick: tick() → handle(); for an entity with no remote client also simulateTick(), before tick() (after it for a Server wait)
    ├── operation counter — moving it is what advances the chain
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
    void tick(Ref<EntityStore> ref, boolean firstRun, float time,
              InteractionType type, InteractionContext context, CooldownHandler cooldown);

    // Server-side stand-in for the client's run of the same operation (mirrors tick)
    void simulateTick(Ref<EntityStore> ref, boolean firstRun, float time,
                      InteractionType type, InteractionContext context, CooldownHandler cooldown);

    // Called after every server tick of this operation, and once more when its chain
    // is cancelled (default: no-op)
    default void handle(Ref<EntityStore> ref, boolean firstRun, float time,
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
| `simulateTick()` | Server, only for an entity with **no remote client** | `InteractionManager` builds its `hasRemoteClient` flag from whether the entity has a `PlayerRef`. For a player the client runs its own half and reports the result, so `simulateTick` never runs; for an NPC (or any entity without a player) the server plays that half itself, ticks both, and throws `Simulation and server tick are not in sync` when the two land on different operations. The default hook of `SimpleInstantInteraction` calls `firstRun` again, so the **effect** runs in both passes. See [the double run](interactions.md#managers-with-no-remote-client-the-double-run) for which types double, which are guarded and which throw |

Both methods receive identical parameters:
- `ref` - Entity store reference for the executing entity
- `firstRun` - `true` on the first tick of this operation
- `time` - Seconds **since this operation started** (shifted on the first tick by any time carried over from the previous operation, and scaled by the world's time dilation). It is an elapsed time, **not** a per-frame delta: `Interaction` itself finishes once `time >= RunTime`
- `type` - The `InteractionType` (`Primary`, `Secondary`, etc.)
- `context` - Execution state container (see [InteractionContext](interactions-context.md))
- `cooldown` - Manages cooldown timers (see [Cooldowns](interactions.md#cooldown-system))

### WaitForDataFrom Enum

Controls synchronization between client and server:

**Package:** `com.hypixel.hytale.protocol`

| Value | Behavior |
|-------|----------|
| `None` | Execute immediately on both client and server |
| `Server` | Client waits for server confirmation before executing. On a manager with no remote client, the server pass runs first and the simulation pass after it (measured) |
| `Client` | Server waits for client data (rare, for client-authoritative actions) |

---

## Interaction Lifecycle

Understanding when each method is called helps when implementing custom interactions.

### Overview Diagram

```
ASSET LOADING PHASE
───────────────────
1. JSON parsed → Interaction tree built
2. RootInteraction.build() → compile(builder) → flat Operation[] array

RUNTIME EXECUTION PHASE (per server tick)
─────────────────────────────────────────
3. simulateTick()  → only for an entity with no remote client; before tick(),
                     or after it when the operation waits for Server
4. tick()          → firstRun is true on the operation's first tick
5. handle()        → right after tick(), same firstRun
6. If the operation moved the operation counter, the manager continues with the
   operation the counter now points at in the same tick; otherwise it stops for this tick

ON DEMAND (any time)
────────────────────
walk(collector) → InteractionManager.walkChain(...) traverses the tree for analysis
```

### Method Call Timing

| Method | Phase | When Called | Purpose |
|--------|-------|-------------|---------|
| `compile()` | Loading | When a `RootInteraction` asset loads, and again for every root whenever `Interaction` assets load or are removed (`RootInteraction.build()`, driven by `InteractionModule`'s asset-event handlers) | Build flat Operation[] from tree |
| `walk()` | On demand | Whenever some code asks for a traversal through `InteractionManager.walkChain(...)` — damage-data collection for item tooltips, NPC combat validation and evaluation, the ability keyword audit | Traverse interaction tree, collect metadata. It is **not** a step of compilation |
| `tick()` | Runtime | Every server tick while the operation is current | Execute operation logic |
| `simulateTick()` | Runtime | Every tick, for an entity with no remote client | Server-side stand-in for the client's run |
| `handle(firstRun, …)` | Runtime | Right after **every** `tick()`, with the same `firstRun`; and once with `firstRun == false` when the chain is cancelled | `Interaction.handle` uses it to send the play/cancel interaction packets |

---

## walk() Method

The `walk()` method traverses the interaction tree using the Visitor pattern. It is invoked on demand through `InteractionManager.walkChain(...)` — for example by `WeaponDamageDataCollector` (damage figures for item tooltips), by NPC combat validation and evaluation, and by the 0.7.2 ability keyword audit — and is independent of `compile()`.

### Method Signature

```java
boolean walk(Collector collector, InteractionContext context)
```

**Returns:** `true` to stop traversal early, `false` to continue. A container returns `true` when `InteractionManager.walkInteraction(...)` for one of its children did — which happens only when the collector's `collect(...)` returned `true` for that child. `walkInteraction` discards the value of the child's own nested `walk(...)`, so a stop requested deeper down ends only the container directly around it, not the whole traversal.

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
the interaction that emits them**, and two of them are `private`, so a plugin can compare
tags via `equals`/`toString` but cannot name their types:

| Interaction Type | Tag | Declared on | Visibility |
|-----------------|-----|-------------|------------|
| `Serial` | `SerialTag.of(int index)` | `SerialInteraction` (`config.none`) | `private static` |
| `Parallel` | `ParallelTag.of(int index)` | `ParallelInteraction` (`config.none`) | `private static` |
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

Compilation happens when assets load, not when a chain starts. `RootInteraction.build()`:

1. **Looks up** each id in the root's `Interactions` list (ids missing from the asset map are skipped)
2. **Calls** `compile(OperationsBuilder)` on each
3. **Builds** the final `Operation[]` array and stores it on the root
4. **Checks** that every operation that waits for client data (`WaitForDataFrom.Client`) also reports `needsRemoteSync()`, throwing `IllegalArgumentException` (`… needs client data but isn't marked as requiring syncing to remote clients`) otherwise

At runtime a chain only walks the stored array. `InteractionModule` runs `build()` for every root
when roots load, and rebuilds every already-built root whenever `Interaction` assets load or are
removed.

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

Each server tick, `InteractionManager` runs the chain's current operation and then looks at the
**operation counter**:

1. **Get current operation** — `root.getOperation(counter)`
2. **Call** `tick()` (and, for an entity with no remote client, `simulateTick()`), then `handle()`
3. **If the counter moved**, continue with the operation it now points at, in the same tick
4. **If it did not move**, stop until the next tick — the operation is still running
5. **Repeat** until the counter passes the end of the array

**The counter is what advances a chain, not the sync state.** `Interaction.tick` (which every
built-in interaction inherits, and which is `final`) increments the counter itself once the
interaction's state is `Finished`, `Failed` or `Skip`, unless the interaction already moved it with
a jump. `JumpOperation` sets the counter to its label. An operation that implements `Operation`
directly gets neither: it must move the counter itself.

### Operation Lifecycle

```
tick(firstRun=true) → handle(firstRun=true) → tick(false) → handle(false) → ... → counter moves
```

- `firstRun` is `true` only on the operation's first tick
- `handle()` runs after **every** `tick()`, and once more (with `firstRun == false`) if the chain is cancelled

---

## Custom Operation Implementation

The simpler route is to extend `SimpleInstantInteraction` (see
[interactions.md](interactions.md#simpleinstantinteraction)): it inherits `Interaction.tick`, which
handles timing, the held-item check and advancing the counter. Implement `Operation` directly only
when you need something an `Interaction` cannot be, and then advance the counter yourself, the way
`JumpOperation` does:

```java
public class MyCustomOp implements Operation {
    private final float duration;

    public MyCustomOp(float duration) {
        this.duration = duration;
    }

    @Override
    public void tick(Ref<EntityStore> ref, boolean firstRun, float time,
                     InteractionType type, InteractionContext context,
                     CooldownHandler cooldown) {
        // `time` is already the seconds elapsed since this operation started
        if (time < duration) {
            context.getState().state = InteractionState.NotFinished;
            return;
        }
        context.getState().state = InteractionState.Finished;
        // A raw Operation must move the counter itself. Leave it where it is, and the
        // manager stops for this tick and runs the same operation again on the next one.
        context.setOperationCounter(context.getOperationCounter() + 1);
    }

    @Override
    public void simulateTick(Ref<EntityStore> ref, boolean firstRun, float time,
                             InteractionType type, InteractionContext context,
                             CooldownHandler cooldown) {
        // Must reach the same counter/state as tick()
        tick(ref, firstRun, time, type, context, cooldown);
    }

    @Override
    public void handle(Ref<EntityStore> ref, boolean firstRun, float time,
                       InteractionType type, InteractionContext context) {
        // Optional: runs after every tick()
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

The `time` argument already **is** the elapsed time, so compare it directly; summing it frame by
frame overcounts. This is what `Interaction` does with `RunTime`:

```java
@Override
public void tick(..., float time, ..., InteractionContext context, ...) {
    if (time >= runTime) {
        context.getState().state = InteractionState.Finished;
        // plus context.setOperationCounter(...) in a raw Operation — see above
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
public void tick(..., boolean firstRun, ...) {
    if (firstRun) {
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
- **`Simulation and server tick are not in sync (operation position).`** / **`... (root interaction).`** → `simulateTick()` and `tick()` diverged (different jump, or one finished and the other didn't), so the two passes are at different counters. It is thrown from `doTickChain` for an entity with no remote client, and `TickInteractionManagerSystem` catches it and **removes the entity that runs the chain**. Measured cause: an interaction that puts an item into the held slot of the entity running it (`ModifyInventory` with the owner the same entity). The second pass sees a changed held item, sets `ItemChanged` and never calls its hook (`Counter: 1 vs 0`); `"OnItemChangeBehavior": "Ignore"` removes the exception. Fix: `simulateTick` must mirror `tick`'s flow control exactly (same `jump`/`Finished`/`Failed` decisions). It need not mirror the side effects: the default hook of `SimpleInstantInteraction` runs them again, which is usually what you do not want, see [the double run](interactions.md#managers-with-no-remote-client-the-double-run).
- **`Can't shift backwards`** (`InteractionManager.setGlobalTimeShift`) → a negative time shift was requested. Fix: time shifts are forward-only.
- **`Failed to find interaction: `** — the offending id follows → a chain referenced an interaction id that is not in the asset map. Fix: see [interactions.md — Gotchas](interactions.md#gotchas--errors).
- **Symptom:** your operation never ends — it runs on every tick, or restarts with `firstRun == true` over and over → nothing moved the operation counter. `InteractionManager` advances a chain only when the counter changes; a `Finished` state on its own does not do it. Fix: extend `SimpleInstantInteraction`/`SimpleInteraction` (whose inherited `Interaction.tick` increments the counter once the state is `Finished`/`Failed`), or, in a raw `Operation`, set the state **and** call `context.setOperationCounter(context.getOperationCounter() + 1)`. There is no `advanceOperation()`.
- **Symptom:** a timed operation finishes far too early → it summed the `time` argument each tick. `time` is the elapsed time since the operation started, not a per-frame delta. Fix: compare `time` against the duration directly.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
