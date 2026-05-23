# Asset Editor Events API

**Doc type:** Java API

Events for the built-in asset editor system.

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
