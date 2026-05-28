---
title: "Tasks API"
description: "Schedule Hytale plugin tasks in Java — the TaskRegistry tracking CompletableFuture and ScheduledFuture tasks, TaskRegistration handles, and automatic cleanup on plugin disable."
seo:
  type: TechArticle
---

# Tasks API

**Doc type:** Java API · **Verified against 0.5.2**

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
- Tasks are cleaned up when the plugin is disabled
- Use for operations that need to run outside the main thread

---

## Gotchas & Errors

These are observable behaviors of the build-12 task system; no literal error strings are thrown by `TaskRegistry` itself.

- **Symptom:** a long-running future keeps running after the plugin is disabled/reloaded → you never registered it, so the plugin system can't cancel it on shutdown. Fix: wrap it with `getTaskRegistry().registerTask(future)` (registered tasks are cleaned up when the plugin is disabled).
- **Symptom:** game-state reads inside a `runAsync` task race against the server → registered tasks run outside the main thread. Fix: don't touch the live entity `Store` directly from a task thread; marshal world reads/writes back onto the world thread.
- **Compile error** on `registerTask(...)` → both overloads accept only `CompletableFuture<Void>` or `ScheduledFuture<Void>`. Fix: type the future as `<Void>` (return `null` from a scheduled callable).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
