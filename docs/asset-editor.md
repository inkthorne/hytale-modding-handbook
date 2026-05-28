---
title: "Asset Editor Events API"
description: "Hook Hytale's in-game Asset Editor in Java — the EditorClientEvent base, button and asset-creation events, selection and disconnect events, and async autocomplete/dataset requests."
seo:
  type: TechArticle
---

# Asset Editor Events API

**Doc type:** Java API · **Verified against 0.5.2**

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
| [`AssetEditorActivateButtonEvent`](#asseteditoractivatebuttonevent) | `String` | Button activated |
| [`AssetEditorAssetCreatedEvent`](#asseteditorassetcreatedevent) | `String` | Asset created |
| [`AssetEditorClientDisconnectEvent`](#asseteditorclientdisconnectevent) | `Void` | Client disconnected |
| [`AssetEditorSelectAssetEvent`](#asseteditorselectassetevent) | `Void` | Asset selected |
| [`AssetEditorFetchAutoCompleteDataEvent`](#asseteditorfetchautocompletedataevent) | `String` | Async - autocomplete fetch |
| [`AssetEditorRequestDataSetEvent`](#asseteditorrequestdatasetevent) | `String` | Async - dataset request |
| [`AssetEditorUpdateWeatherPreviewLockEvent`](#asseteditorupdateweatherpreviewlockevent) | `Void` | Weather preview lock |

---

## EditorClientEvent<KeyType> (Base Class)

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Abstract base class for all asset editor events.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getEditorClient()` | `EditorClient` | The editor client |

> **See also:** [Asset Registry](assets.md#assetregistry)

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
| `getDisconnectReason()` | `DisconnectReason` | Why client disconnected |

---

## AssetEditorSelectAssetEvent

**Package:** `com.hypixel.hytale.builtin.asseteditor.event`

Extends `EditorClientEvent<Void>`. Fired when an asset is selected in the asset editor.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetType()` | `String` | Selected asset type |
| `getAssetFilePath()` | `AssetPath` | Selected asset path |
| `getPreviousAssetType()` | `String` | Previously selected type |
| `getPreviousAssetFilePath()` | `AssetPath` | Previous asset path |

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

Backtick-quoted error strings below are the literal messages thrown by the build-12 asset-editor system (verified against `HytaleServer.jar`).

- **`Unable to process AssetEditorUpdateJsonAsset packet. Player ref is invalid!`** → an editor packet arrived referencing a player who has disconnected or whose ref is no longer valid. Fix: this is a transient/disconnect condition rather than a plugin bug; handle `AssetEditorClientDisconnectEvent` and avoid relying on a player ref after disconnect.
- **Symptom:** an autocomplete request never returns results → an `AssetEditorFetchAutoCompleteDataEvent` handler registered via `registerAsyncGlobal` did not complete its future. Fix: always return the event from the `thenApply` chain (and call `setResults(...)`), so the future completes. see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
