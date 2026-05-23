# Tasks API

**Doc type:** Java API

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
