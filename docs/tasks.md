---
title: "Tasks API"
description: "Schedule Hytale plugin tasks in Java — the TaskRegistry tracking CompletableFuture and ScheduledFuture tasks, TaskRegistration handles, and automatic cleanup on plugin disable."
seo:
  type: TechArticle
---

# Tasks API

**Doc type:** Java API · **Verified against 0.5.9**

This page covers registering async and scheduled tasks so the plugin system can track them across the plugin lifecycle.

## Overview

Implemented in `com.hypixel.hytale.server.core.task` and provides:
- A `TaskRegistry` for tracking `CompletableFuture` and `ScheduledFuture` tasks
- A `TaskRegistration` handle for unregistering and checking task status
- Automatic cleanup of registered tasks when the plugin is disabled

## Architecture
```
TaskRegistry (getTaskRegistry())
├── registerTask(CompletableFuture<Void>)
├── registerTask(ScheduledFuture<Void>)
└── TaskRegistration (handle: getTask / unregister / isRegistered)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `TaskRegistry` | `server.core.task` | Registers async tasks for lifecycle tracking |
| `TaskRegistration` | `server.core.task` | Handle to unregister a task and check its status (extends `Registration`) |

## TaskRegistry
**Package:** `com.hypixel.hytale.server.core.task`

Register async tasks. Access via `getTaskRegistry()` in your plugin.

**Extends:** `Registry<TaskRegistration>` (`com.hypixel.hytale.registry.Registry`)

### Methods
```java
TaskRegistration registerTask(CompletableFuture<Void> future)
TaskRegistration registerTask(ScheduledFuture<Void> future)
```

> **See also:** [Plugin Lifecycle](plugin-lifecycle.md#plugin-lifecycle-api)

---

## TaskRegistration
**Package:** `com.hypixel.hytale.server.core.task`

Handle returned from registering a task. Allows unregistering and checking status.

**Extends:** `Registration`

### Methods
```java
// Get the underlying Future
Future<?> getTask()

// Inherited from Registration
void unregister()        // Unregister the task
boolean isRegistered()   // Check if still registered
```

### Usage Example
```java
CompletableFuture<Void> task = CompletableFuture.runAsync(() -> {
    // Long-running operation
});

TaskRegistration registration = getTaskRegistry().registerTask(task);

// Later, check if still registered
if (registration.isRegistered()) {
    // Task is still tracked
}

// Or unregister manually
registration.unregister();
```

## Usage Examples

### Simple Async Task
```java
@Override
protected void setup() {
    CompletableFuture<Void> task = CompletableFuture.runAsync(() -> {
        // Long-running operation
        loadDataFromDatabase();
    });
    getTaskRegistry().registerTask(task);
}
```

### Scheduled Task
```java
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

@Override
protected void setup() {
    ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
    ScheduledFuture<Void> future = scheduler.schedule(() -> {
        // Runs after 5 seconds
        getLogger().atInfo().log("Delayed task executed");
        return null;
    }, 5, TimeUnit.SECONDS);

    getTaskRegistry().registerTask(future);
}
```

### Task with Completion Handler
```java
CompletableFuture<Void> task = CompletableFuture
    .runAsync(() -> {
        // Do work
    })
    .thenRun(() -> {
        getLogger().atInfo().log("Task completed!");
    })
    .exceptionally(ex -> {
        getLogger().atSevere().withCause(ex).log("Task failed");
        return null;
    });

getTaskRegistry().registerTask(task);
```

## Notes
- Registered tasks are tracked by the plugin system
- Tasks are cleaned up when the plugin is disabled — cleanup calls `Future.cancel(false)` on each registered task
- Use for operations that need to run outside the main thread

### What "cleanup" actually does

`TaskRegistration`'s unregister action is exactly `task.cancel(false)`; the same action runs for every
registered task when the plugin is disabled (`PluginBase` drains its shutdown list, newest first).

Two consequences worth knowing before you rely on it:

- **`false` means *do not interrupt*.** A task already executing is not interrupted, and a
  `CompletableFuture` from `CompletableFuture.runAsync(...)` keeps running its body to completion —
  cancelling only completes the *future* exceptionally. Long-running loops must poll their own stop
  flag; registration alone will not stop them.
- **A `ScheduledFuture` that has not fired yet is genuinely dropped**, which is the case cleanup
  handles well: use `registerTask` for delayed/periodic work you must not have fire after a reload.

---

## Gotchas & Errors

These are observable behaviors of the task system; no literal error strings are thrown by `TaskRegistry` itself.

- **Symptom:** a long-running future keeps running after the plugin is disabled/reloaded → either you never registered it, or you registered it and expected cancellation to be forceful. Fix: register it with `getTaskRegistry().registerTask(future)` *and* make the body itself interruptible — cleanup calls `cancel(false)`, which never interrupts a task that is already running (see [What "cleanup" actually does](#what-cleanup-actually-does)).
- **`Registry is not enabled!`** (an `IllegalStateException`) → `registerTask(...)` was called after the plugin was disabled; the registry rejects the registration and immediately cancels the future you handed it. Fix: register tasks from `setup()` while the plugin is enabled, not from a shutdown path or a late callback.
- **Symptom:** game-state reads inside a `runAsync` task race against the server → registered tasks run outside the main thread. Fix: don't touch the live entity `Store` directly from a task thread; marshal world reads/writes back onto the world thread.
- **Compile error** on `registerTask(...)` → both overloads accept only `CompletableFuture<Void>` or `ScheduledFuture<Void>`. Fix: type the future as `<Void>` (return `null` from a scheduled callable).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
