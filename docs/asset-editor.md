---
title: "Asset Editor Events API"
description: "Hook Hytale's in-game Asset Editor in Java — the EditorClientEvent base, button and asset-creation events, selection and disconnect events, and async autocomplete/dataset requests."
seo:
  type: TechArticle
---

# Asset Editor Events API

**Doc type:** Java API · **Verified against 0.6.3**

Events for the built-in asset editor system.

This page covers the server-side events fired by Hytale's built-in asset editor as clients connect, select/create assets, and request data.

## Overview

Implemented in `com.hypixel.hytale.builtin.asseteditor.event` and provides:
- A generic base event (`EditorClientEvent<KeyType>`) carrying the `EditorClient`
- Button activation and asset creation events
- Asset selection and client disconnect events
- Async events for autocomplete and dataset requests (settable results)
- A weather preview lock event

## Architecture
```
EditorClientEvent<KeyType> (base — exposes EditorClient)
├── Synchronous events
│   ├── AssetEditorActivateButtonEvent
│   ├── AssetEditorAssetCreatedEvent
│   ├── AssetEditorClientDisconnectEvent
│   ├── AssetEditorSelectAssetEvent
│   └── AssetEditorUpdateWeatherPreviewLockEvent
└── Async events (IAsyncEvent<String>, set results)
    ├── AssetEditorFetchAutoCompleteDataEvent
    └── AssetEditorRequestDataSetEvent
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `EditorClientEvent<KeyType>` | `builtin.asseteditor.event` | Abstract base for editor events; exposes `getEditorClient()` |
| `AssetEditorActivateButtonEvent` | `builtin.asseteditor.event` | Fired when an editor button is activated |
| `AssetEditorAssetCreatedEvent` | `builtin.asseteditor.event` | Fired when an asset is created |
| `AssetEditorClientDisconnectEvent` | `builtin.asseteditor.event` | Fired when an editor client disconnects |
| `AssetEditorSelectAssetEvent` | `builtin.asseteditor.event` | Fired when an asset is selected |
| `AssetEditorFetchAutoCompleteDataEvent` | `builtin.asseteditor.event` | Async; supplies autocomplete results |
| `AssetEditorRequestDataSetEvent` | `builtin.asseteditor.event` | Async; supplies dataset results |
| `AssetEditorUpdateWeatherPreviewLockEvent` | `builtin.asseteditor.event` | Fired when weather preview lock changes |

---

## Event Summary

| Class | Key Type | Description |
|-------|----------|-------------|
| [`EditorClientEvent<K>`](#editorclienteventkeytype-base-class) | Generic | Abstract base for editor events |
| [`AssetEditorActivateButtonEvent`](#asseteditoractivatebuttonevent) | `String` — the **button id** | Button activated |
| [`AssetEditorAssetCreatedEvent`](#asseteditorassetcreatedevent) | `String` — the **asset-type id** | Asset created |
| [`AssetEditorClientDisconnectEvent`](#asseteditorclientdisconnectevent) | `Void` | Client disconnected |
| [`AssetEditorSelectAssetEvent`](#asseteditorselectassetevent) | `Void` | Asset selected |
| [`AssetEditorFetchAutoCompleteDataEvent`](#asseteditorfetchautocompletedataevent) | `String` — the **dataset name** | Async - autocomplete fetch |
| [`AssetEditorRequestDataSetEvent`](#asseteditorrequestdatasetevent) | `String` — the **dataset name** | Async - dataset request |
| [`AssetEditorUpdateWeatherPreviewLockEvent`](#asseteditorupdateweatherpreviewlockevent) | `Void` | Weather preview lock |

---

## EditorClientEvent<KeyType> (Base Class)

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Abstract base class for all asset editor events.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getEditorClient()` | `EditorClient` | The editor client |

### EditorClient

**Package:** `com.hypixel.hytale.builtin.asseteditor`

The connected editor session every event above hands you. Implements
`com.hypixel.hytale.server.core.permissions.PermissionHolder`, so it can be permission-checked exactly
like a player.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getUuid()` | `UUID` | Account UUID of the editing user |
| `getUsername()` | `String` | Account name |
| `getLanguage()` / `setLanguage(String)` | `String` / `void` | The client's language tag (drives `Message` localization) |
| `getAuth()` | `PlayerAuthentication` | Authentication data for the session |
| `getPacketHandler()` | `PacketHandler` | The underlying connection |
| `tryGetPlayer()` | `PlayerRef` | The in-world player for this user, or `null` if they are editor-only / disconnected |
| `hasPermission(String)` / `hasPermission(String, boolean)` | `boolean` | Permission check by node (the `boolean` is the default when unset) |
| `hasPermission(PermissionQuery)` / `hasPermission(PermissionQuery, boolean)` | `boolean` | Query-object overloads (0.6.3+) |
| `sendPopupNotification(AssetEditorPopupNotificationType, Message)` | `void` | Show a popup in the editor UI |
| `sendSuccessReply(int)` / `sendSuccessReply(int, Message)` | `void` | Acknowledge a request id as succeeded |
| `sendFailureReply(int, Message)` | `void` | Reject a request id with a message |

> **Gotcha:** `tryGetPlayer()` is nullable by design — an asset-editor connection is its own
> connection type and need not have a player in a world. Never assume a `PlayerRef`.

> **See also:** [Asset Registry](assets.md#assetregistry) · [Permissions](permissions.md)

---

## AssetEditorActivateButtonEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Extends `EditorClientEvent<String>`. Fired when a button is activated in the asset editor.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getButtonId()` | `String` | The activated button ID |

---

## AssetEditorAssetCreatedEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Extends `EditorClientEvent<String>`. Fired when an asset is created in the asset editor.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetType()` | `String` | Type of asset created |
| `getAssetPath()` | `Path` | File path of asset |
| `getData()` | `byte[]` | Raw asset data |
| `getButtonId()` | `String` | Button that triggered creation |

---

## AssetEditorClientDisconnectEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Extends `EditorClientEvent<Void>`. Fired when an asset editor client disconnects.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDisconnectReason()` | `PacketHandler.DisconnectReason` | Why client disconnected (`com.hypixel.hytale.server.core.io.PacketHandler$DisconnectReason` — a nested class, not a top-level `DisconnectReason`) |

---

## AssetEditorSelectAssetEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Extends `EditorClientEvent<Void>`. Fired when an asset is selected in the asset editor.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetType()` | `String` | Selected asset type — `null` when the selection was *cleared* |
| `getAssetFilePath()` | `AssetPath` | Selected asset path — `null` when the selection was cleared |
| `getPreviousAssetType()` | `String` | Previously selected type — `null` on the client's first selection |
| `getPreviousAssetFilePath()` | `AssetPath` | Previous asset path — `null` on the first selection, `AssetPath.EMPTY_PATH` after a clear |

`AssetPath` here is the server-side record `com.hypixel.hytale.builtin.asseteditor.AssetPath`
— components `packId()` (`String`) and `path()` (`java.nio.file.Path`), with `EMPTY_PATH` for "nothing
selected" and `toPacket()` to convert to the wire type
`com.hypixel.hytale.protocol.packets.asseteditor.AssetPath`. Don't confuse the two.

---

## AssetEditorFetchAutoCompleteDataEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Implements `IAsyncEvent<String>`. Async event for fetching autocomplete data.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getQuery()` | `String` | Autocomplete query |
| `getDataSet()` | `String` | Dataset to search |
| `getEditorClient()` | `EditorClient` | The editor client |
| `getResults()` | `String[]` | Get results |
| `setResults(String[])` | `void` | Set results |

---

## AssetEditorRequestDataSetEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Implements `IAsyncEvent<String>`. Async event for requesting a dataset.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getDataSet()` | `String` | Requested dataset |
| `getEditorClient()` | `EditorClient` | The editor client |
| `getResults()` | `String[]` | Get results |
| `setResults(String[])` | `void` | Set results |

---

## AssetEditorUpdateWeatherPreviewLockEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Extends `EditorClientEvent<Void>`. Fired when weather preview lock state changes.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `isLocked()` | `boolean` | Whether preview is locked |

---

## Usage Example

```java
import com.hypixel.hytale.builtin.asseteditor.event.*;

@Override
protected void setup() {
    // Listen for asset creation
    getEventRegistry().registerGlobal(AssetEditorAssetCreatedEvent.class, event -> {
        System.out.println("Asset created: " + event.getAssetType() +
            " at " + event.getAssetPath());
    });

    // Listen for client disconnects
    getEventRegistry().register(AssetEditorClientDisconnectEvent.class, event -> {
        System.out.println("Editor client disconnected: " +
            event.getDisconnectReason());
    });

    // Handle autocomplete requests (async)
    getEventRegistry().registerAsyncGlobal(
        AssetEditorFetchAutoCompleteDataEvent.class,
        future -> future.thenApply(event -> {
            if ("my_dataset".equals(event.getDataSet())) {
                event.setResults(new String[]{"option1", "option2", "option3"});
            }
            return event;
        })
    );
}
```

> **See also:** [Event Registration](plugin-lifecycle.md#server-lifecycle-events)

---

## Gotchas & Errors

Backtick-quoted strings below are literal identifiers verified against `HytaleServer.jar`.

- **Symptom:** an editor packet arrives referencing a player who has disconnected or whose ref is no longer valid (through build-17 this logged the literal `Unable to process AssetEditorUpdateJsonAsset packet. Player ref is invalid!`; 0.5.7 removed that exact string, and it is still absent in 0.6.3, but the invalid-ref condition remains). Fix: this is a transient/disconnect condition rather than a plugin bug; handle `AssetEditorClientDisconnectEvent` and avoid relying on a player ref after disconnect.
- **Symptom:** an autocomplete request never returns results → an `AssetEditorFetchAutoCompleteDataEvent` handler registered via `registerAsyncGlobal` did not complete its future. Fix: always return the event from the `thenApply` chain (and call `setResults(...)`), so the future completes.
- **Symptom:** a handler registered with plain `register(EventClass, handler)` never fires for `AssetEditorActivateButtonEvent`, `AssetEditorAssetCreatedEvent`, `AssetEditorFetchAutoCompleteDataEvent` or `AssetEditorRequestDataSetEvent` → these four are dispatched **keyed** (button id, asset-type id, dataset name, dataset name respectively), so the `Void`-key overload never matches. Fix: use `registerGlobal` / `registerAsyncGlobal`, or pass the key you care about. The `Void`-keyed events (`AssetEditorClientDisconnectEvent`, `AssetEditorSelectAssetEvent`, `AssetEditorUpdateWeatherPreviewLockEvent`) work with plain `register`.
- **Symptom:** your listener never fires at all → these are dispatched on the **server-wide event bus** (`HytaleServer.get().getEventBus()`), and only when a listener already exists (`dispatchFor(...).hasListener()`). Fix: register in `setup()`, before any editor client connects.
- **Failure replies** the editor itself sends are `Message` constants on `com.hypixel.hytale.builtin.asseteditor.Messages` (`USAGE_DENIED`, `ASSETS_READ_ONLY`, `INVALID_ASSET_TYPE`, `RENAME_ASSET_CROSS_PACK_UNSUPPORTED`, …). Match on those rather than on rendered English text.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
