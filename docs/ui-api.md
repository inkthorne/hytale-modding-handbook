---
title: "UI Java API"
description: "Build Hytale server-side UI in Java — UICommandBuilder and UIEventBuilder, positioning primitives (Anchor, Area, Value), and event bindings for player interfaces."
seo:
  type: TechArticle
---

# UI Java API

**Doc type:** Java API · **Verified against build-12**

Server-side Java API reference for Hytale's UI system.

## Overview

Implemented in `com.hypixel.hytale.server.core.ui` (and player manager packages under `server.core.entity.entities.player`) and provides:
- Builders for UI update commands and event bindings (`UICommandBuilder`, `UIEventBuilder`)
- Positioning primitives (`Anchor`, `Area`, `Value<T>`)
- Full-screen page management and custom page base classes (`PageManager`, `CustomUIPage`)
- Window lifecycle management (`WindowManager`, `Window` and subclasses)
- HUD visibility control and custom HUD overlays (`HudManager`, `CustomUIHud`)
- Hotbar configuration and a server-side file browser UI

## Architecture
```
UICommandBuilder / UIEventBuilder   (build commands + event bindings)
└── consumed by all UI surfaces below

Player
├── PageManager
│   └── CustomUIPage
│         ├── BasicCustomUIPage
│         └── InteractiveCustomUIPage<T>
├── WindowManager
│   └── Window (ContainerWindow, ItemContainerWindow, BlockWindow, ValidatedWindow)
├── HudManager
│   ├── HudComponent (native elements)
│   └── CustomUIHud
└── HotbarManager

Positioning: Anchor, Area, Value<T>
File browser: FileBrowserConfig ──▶ ServerFileBrowser
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `UICommandBuilder` | `server.core.ui.builder` | Builds UI update commands (append, set, clear, remove) |
| `UIEventBuilder` | `server.core.ui.builder` | Builds client-interaction event bindings |
| `Anchor` | `server.core.ui` | Element anchoring/positioning |
| `Area` | `server.core.ui` | UI area/bounds definition |
| `Value<T>` | `server.core.ui` | Literal or document-reference value container |
| `PageManager` | `server.core.entity.entities.player.pages` | Manages full-screen player pages |
| `CustomUIPage` | `server.core.entity.entities.player.pages` | Abstract base for custom plugin pages |
| `WindowManager` | `server.core.entity.entities.player.windows` | Manages player windows |
| `Window` | `server.core.entity.entities.player.windows` | Abstract base for player windows |
| `HudManager` | `server.core.entity.entities.player.hud` | Controls HUD visibility and custom HUD |
| `CustomUIHud` | `server.core.entity.entities.player.hud` | Abstract base for custom HUD overlays |
| `HotbarManager` | `server.core.entity.entities.player` | Manages player hotbar configurations |
| `FileBrowserConfig` | `server.core.ui.browser` | Configuration for the file browser UI |
| `ServerFileBrowser` | `server.core.ui.browser` | Server-side file browser implementation |

---

## Quick Navigation

| Topic | Description |
|-------|-------------|
| [Positioning Classes](#positioning-classes) | Anchor, Area, Value |
| [UICommandBuilder](#uicommandbuilder) | Build UI update commands |
| [UIEventBuilder](#uieventbuilder) | Build event handlers |
| [PageManager](#pagemanager) | Full-screen page management |
| [CustomUIPage](#customuipage) | Custom page implementation |
| [Registering Pages for OpenCustomUI](#registering-pages-for-opencustomui) | Page suppliers for JSON interactions |
| [WindowManager](#windowmanager) | Window lifecycle management |
| [HudManager](#hudmanager) | HUD visibility control |
| [CustomUIHud](#customuihud) | Custom HUD overlays |
| [HotbarManager](#hotbarmanager) | Hotbar configuration |
| [File Browser](#file-browser-system) | Server file browser UI |
| [WindowCloseEvent](#windowcloseevent) | Window close handling |

**Related:** [UI Overview](ui.md) | [Elements](ui-elements.md) | [Styling](ui-styling.md) | [Templates](ui-templates.md)

---

## Positioning Classes

### Anchor
**Package:** `com.hypixel.hytale.server.core.ui`

UI element anchoring for positioning.

```java
// Setters (void, set-prefixed)
void setLeft(Value<Integer> value)
void setRight(Value<Integer> value)
void setTop(Value<Integer> value)
void setBottom(Value<Integer> value)
void setHeight(Value<Integer> value)
void setWidth(Value<Integer> value)
void setMinWidth(Value<Integer> value)
void setMaxWidth(Value<Integer> value)

// Codec for serialization
static final BuilderCodec<Anchor> CODEC
```

> **Note:** `full`, `horizontal`, and `vertical` are private fields (also set via
> `setFull`/`setHorizontal`/`setVertical`), not standalone preset methods.

### Area
**Package:** `com.hypixel.hytale.server.core.ui`

UI area/bounds definition.

```java
Area setX(int x)
Area setY(int y)
Area setWidth(int width)
Area setHeight(int height)
```

### Value<T>
**Package:** `com.hypixel.hytale.server.core.ui`

Generic value container supporting literal values or document references for dynamic binding.

```java
// Get value
T getValue()
String getDocumentPath()
String getValueName()

// Static factories
static <T> Value<T> ref(String documentPath, String valueName)  // Reference to UI document value
static <T> Value<T> of(T literal)                                // Literal value
```

---

## UICommandBuilder
**Package:** `com.hypixel.hytale.server.core.ui.builder`

Build UI commands for updating client UI elements.

### Element Operations
```java
UICommandBuilder clear(String elementId)            // Clear element contents
UICommandBuilder remove(String elementId)           // Remove element from DOM
```

### Append Operations
```java
UICommandBuilder append(String uiFilePath)                            // Append .ui file to root
UICommandBuilder append(String elementSelector, String uiFilePath)    // Append .ui file to element
UICommandBuilder appendInline(String elementSelector, String dslMarkup)  // Append inline DSL markup
```

**File paths** are relative to `resources/Common/UI/Custom/`. Examples:
- `append("MyUI.ui")` loads `Common/UI/Custom/MyUI.ui`
- `append("Pages/MyPage.ui")` loads `Common/UI/Custom/Pages/MyPage.ui`
- `append("#container", "Components/Button.ui")` appends to element with id "container"

**Inline DSL markup** uses Hytale's curly-brace format (NOT XML):
```java
appendInline("#container", "Label { Text: \"Hello\"; Style: (Alignment: Center); }");
```

**Note:** The selector for `appendInline()` must reference an existing element in the UI. Load a base `.ui` file first with `append()`, then use `appendInline()` to add content to named containers within it.

### Insert Operations
```java
UICommandBuilder insertBefore(String elementSelector, String uiFilePath)
UICommandBuilder insertBeforeInline(String elementSelector, String dslMarkup)
```

### Set Property Operations
```java
// By Value<T>
<T> UICommandBuilder set(String path, Value<T> value)

// By type
UICommandBuilder set(String path, String value)
UICommandBuilder set(String path, Message message)
UICommandBuilder set(String path, boolean value)
UICommandBuilder set(String path, float value)
UICommandBuilder set(String path, int value)
UICommandBuilder set(String path, double value)

// Object and collections
UICommandBuilder setObject(String path, Object value)
<T> UICommandBuilder set(String path, T[] array)
<T> UICommandBuilder set(String path, List<T> list)
UICommandBuilder setNull(String path)
```

### Get Commands
```java
CustomUICommand[] getCommands()
```

---

## UIEventBuilder
**Package:** `com.hypixel.hytale.server.core.ui.builder`

Build UI event handlers for client interaction.

```java
// Add event bindings
UIEventBuilder addEventBinding(CustomUIEventBindingType type, String elementId)
UIEventBuilder addEventBinding(CustomUIEventBindingType type, String elementId, boolean capture)
UIEventBuilder addEventBinding(CustomUIEventBindingType type, String elementId, EventData data)
UIEventBuilder addEventBinding(CustomUIEventBindingType type, String elementId, EventData data, boolean capture)

// Get events
CustomUIEventBinding[] getEvents()
```

### EventData
**Package:** `com.hypixel.hytale.server.core.ui.builder`

Container for UI event data passed to handlers.

### CustomUIEventBindingType
**Package:** `com.hypixel.hytale.protocol.packets.interface_`

Enum defining UI event types for event bindings.

| Value | Description |
|-------|-------------|
| `Activating` | Element activated (clicked/pressed) |
| `RightClicking` | Right mouse button clicked |
| `DoubleClicking` | Double click |
| `MouseEntered` | Mouse entered element bounds |
| `MouseExited` | Mouse exited element bounds |
| `ValueChanged` | Input value changed |
| `ElementReordered` | Element order changed (drag/drop) |
| `Validating` | Input validation triggered |
| `Dismissing` | Element being dismissed |
| `FocusGained` | Element gained focus |
| `FocusLost` | Element lost focus |
| `KeyDown` | Key pressed while focused |
| `MouseButtonReleased` | Mouse button released |
| `SlotClicking` | Inventory slot clicked |
| `SlotDoubleClicking` | Inventory slot double-clicked |
| `SlotMouseEntered` | Mouse entered slot |
| `SlotMouseExited` | Mouse exited slot |
| `DragCancelled` | Drag operation cancelled |
| `Dropped` | Item dropped |
| `SlotMouseDragCompleted` | Slot drag completed |
| `SlotMouseDragExited` | Mouse exited during slot drag |
| `SlotClickReleaseWhileDragging` | Click released while dragging |
| `SlotClickPressWhileDragging` | Click pressed while dragging |
| `SelectedTabChanged` | Tab selection changed |

```java
static CustomUIEventBindingType[] values()
static CustomUIEventBindingType valueOf(String name)
int getValue()
static CustomUIEventBindingType fromValue(int value)
```

### Usage Example
```java
UIEventBuilder events = new UIEventBuilder();
events.addEventBinding(CustomUIEventBindingType.Activating, "submit-button");
events.addEventBinding(CustomUIEventBindingType.ValueChanged, "search-input");
events.addEventBinding(CustomUIEventBindingType.SlotClicking, "inventory-slot");
```

---

## Player UI Managers

Access via `Player`:

```java
Player player = store.getComponent(ref, Player.getComponentType());
WindowManager windows = player.getWindowManager();
PageManager pages = player.getPageManager();
HudManager hud = player.getHudManager();
HotbarManager hotbar = player.getHotbarManager();
```

---

## PageManager
**Package:** `com.hypixel.hytale.server.core.entity.entities.player.pages`

Manage player pages (full-screen UIs).

```java
// Initialization
void init(PlayerRef playerRef, WindowManager windowManager)

// Custom page access
CustomUIPage getCustomPage()

// Set pages
void setPage(Ref<EntityStore> ref, Store<EntityStore> store, Page page)
void setPage(Ref<EntityStore> ref, Store<EntityStore> store, Page page, boolean animate)

// Open custom pages
void openCustomPage(Ref<EntityStore> ref, Store<EntityStore> store, CustomUIPage page)

// With windows
boolean setPageWithWindows(Ref<EntityStore> ref, Store<EntityStore> store, Page page, boolean animate, Window... windows)
boolean openCustomPageWithWindows(Ref<EntityStore> ref, Store<EntityStore> store, CustomUIPage page, Window... windows)

// Update
void updateCustomPage(CustomPage page)

// Event handling
void handleEvent(Ref<EntityStore> ref, Store<EntityStore> store, CustomPageEvent event)
```

### Page Enum
**Package:** `com.hypixel.hytale.protocol.packets.interface_`

Built-in page types.

| Value | Description |
|-------|-------------|
| `None` | No page (close current page) |
| `Bench` | Crafting bench page |
| `Inventory` | Player inventory page |
| `ToolsSettings` | Tools/settings page |
| `Map` | World map page |
| `MachinimaEditor` | Machinima editor page |
| `ContentCreation` | Content creation tools |
| `Custom` | Custom plugin-defined page |

```java
static Page[] values()
static Page valueOf(String name)
int getValue()
static Page fromValue(int value)
```

**Usage:**
```java
PageManager pages = player.getPageManager();

// Open inventory page
pages.setPage(ref, store, Page.Inventory);

// Open with animation
pages.setPage(ref, store, Page.Map, true);

// Close current page
pages.setPage(ref, store, Page.None);
```

---

## CustomUIPage
**Package:** `com.hypixel.hytale.server.core.entity.entities.player.pages`

Abstract base class for custom plugin-defined pages.

```java
// Constructor
CustomUIPage(PlayerRef playerRef, CustomPageLifetime lifetime)

// Lifetime management
void setLifetime(CustomPageLifetime lifetime)
CustomPageLifetime getLifetime()

// Abstract - must implement
abstract void build(Ref<EntityStore> ref, UICommandBuilder cmdBuilder,
                    UIEventBuilder eventBuilder, Store<EntityStore> store)

// Event handling
void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, String data)

// Lifecycle
void onDismiss(Ref<EntityStore> ref, Store<EntityStore> store)
```

### Subclasses

| Class | Description |
|-------|-------------|
| `BasicCustomUIPage` | Basic custom page - use this for display-only pages |
| `InteractiveCustomUIPage<T>` | Interactive page with typed event handling |

**Important:** Use `BasicCustomUIPage` (not `CustomUIPage` directly) for most custom pages.

### CustomPageLifetime

| Value | Description |
|-------|-------------|
| `CantClose` | Page must be closed programmatically |
| `CanDismiss` | Player can dismiss the page (ESC key) |
| `CanDismissOrCloseThroughInteraction` | Player can dismiss, or the page can be closed via an interaction |

### Implementation Example

Full working example: [`examples/ui/.../SimpleMenuPage.java`](../examples/ui/src/main/java/hytale/examples/ui/pages/SimpleMenuPage.java) (a display-only `BasicCustomUIPage` that loads its layout from a `.ui` file).

```java
public class MyCustomPage extends BasicCustomUIPage {
    public MyCustomPage(PlayerRef playerRef) {
        super(playerRef, CustomPageLifetime.CanDismiss);
    }

    @Override
    public void build(UICommandBuilder cmd) {
        // Load UI from .ui file (path relative to Common/UI/Custom/)
        cmd.append("MyCustomPage.ui");
    }

    @Override
    public void onDismiss(Ref<EntityStore> ref, Store<EntityStore> store) {
        // Cleanup when page closes
    }
}

// Open the custom page
Player player = store.getComponent(ref, Player.getComponentType());
PageManager pages = player.getPageManager();
pages.openCustomPage(ref, store, new MyCustomPage(playerRef));
```

### .ui File Requirements

1. **Location:** `resources/Common/UI/Custom/MyCustomPage.ui`
2. **Manifest:** Must include `"IncludesAssetPack": true`
3. **Structure:** Must have an anonymous root Group (see [Elements](ui-elements.md#group))

### Event Handling in Custom Pages

```java
public class InteractivePage extends BasicCustomUIPage {
    public InteractivePage(PlayerRef playerRef) {
        super(playerRef, CustomPageLifetime.CanDismiss);
    }

    @Override
    public void build(Ref<EntityStore> ref, UICommandBuilder cmdBuilder,
                      UIEventBuilder eventBuilder, Store<EntityStore> store) {
        cmdBuilder.append("MyPage.ui");
        // Register button click event by element ID
        eventBuilder.addEventBinding(CustomUIEventBindingType.Activating, "MyButton");
        eventBuilder.addEventBinding(CustomUIEventBindingType.ValueChanged, "MyInput");
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, String data) {
        if ("MyButton".equals(data)) {
            // Handle button click
        }
    }
}
```

> **Note:** The `OnActivating: (SendData: ...)` syntax is NOT valid in .ui files. Events must be registered through the Java API.

---

## Registering Pages for OpenCustomUI

To open custom pages via [`OpenCustomUI`](interactions-world.md#opencustomui) interactions in JSON, you must register a page supplier. This allows JSON asset files to reference your custom page by ID.

### Simple Registration

For pages that don't need additional JSON properties, use `registerSimple()`:

```java
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.OpenCustomUIInteraction;

@Override
protected void setup() {
    OpenCustomUIInteraction.registerSimple(
        this,                               // Plugin instance
        MyPage.class,                       // Page class
        "MyPage",                           // Page ID for JSON
        playerRef -> new MyPage(playerRef)  // Factory function
    );
}
```

Usage in JSON:
```json
{
  "Type": "OpenCustomUI",
  "Page": { "Id": "MyPage" }
}
```

### Custom Supplier Registration

For pages that accept additional properties from JSON, implement `CustomPageSupplier`:

```java
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.OpenCustomUIInteraction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.OpenCustomUIInteraction.CustomPageSupplier;

public class MyPageSupplier implements CustomPageSupplier {
    // Define codec for JSON deserialization (see codecs.md#buildercodect)
    public static final BuilderCodec<MyPageSupplier> CODEC =
        BuilderCodec.builder(MyPageSupplier.class, MyPageSupplier::new)
            .addField(new KeyedCodec<>("customProperty", Codec.STRING),
                      (s, v) -> s.customProperty = v, s -> s.customProperty)
            .build();

    protected String customProperty = "default";   // default when the JSON key is absent

    @Override
    public CustomUIPage tryCreate(Ref<EntityStore> ref,
                                   ComponentAccessor<EntityStore> accessor,
                                   PlayerRef playerRef,
                                   InteractionContext context) {
        return new MyPage(playerRef, customProperty);
    }
}
```

Register the supplier in your plugin:

```java
@Override
protected void setup() {
    OpenCustomUIInteraction.registerCustomPageSupplier(
        this,
        MyPageSupplier.class,
        "MyPage",
        new MyPageSupplier()   // supplier INSTANCE, not a codec
    );
}
```

> **Signature:** `registerCustomPageSupplier(PluginBase plugin, Class<?> pageClass, String id, S supplier)`
> — the 4th argument is an instance of your `CustomPageSupplier`, not a codec.

Usage in JSON with custom properties:
```json
{
  "Type": "OpenCustomUI",
  "Page": {
    "Id": "MyPage",
    "customProperty": "hello"
  }
}
```

### CustomPageSupplier Interface

```java
public interface CustomPageSupplier {
    /**
     * Create a custom UI page for the given context.
     *
     * @param ref Entity reference
     * @param accessor Component accessor for reading entity state
     * @param playerRef Player reference
     * @param context Interaction context
     * @return The custom page, or null if creation fails
     */
    CustomUIPage tryCreate(
        Ref<EntityStore> ref,
        ComponentAccessor<EntityStore> accessor,
        PlayerRef playerRef,
        InteractionContext context
    );
}
```

### Specialized Registration Methods

| Method | Use Case |
|--------|----------|
| `registerSimple()` | Pages with no extra JSON properties |
| `registerCustomPageSupplier()` | Pages with custom JSON properties |
| `registerBlockEntityCustomPage()` | Pages tied to block entities |

### Complete Example

This example shows a custom shop page that accepts a shop ID from JSON:

**ShopPageSupplier.java:**
```java
public class ShopPageSupplier implements OpenCustomUIInteraction.CustomPageSupplier {
    public static final BuilderCodec<ShopPageSupplier> CODEC =
        BuilderCodec.builder(ShopPageSupplier.class, ShopPageSupplier::new)
            .addField(new KeyedCodec<>("shopId", Codec.STRING),
                      (s, v) -> s.shopId = v, s -> s.shopId)
            .build();

    protected String shopId = "default_shop";

    @Override
    public CustomUIPage tryCreate(Ref<EntityStore> ref,
                                   ComponentAccessor<EntityStore> accessor,
                                   PlayerRef playerRef,
                                   InteractionContext context) {
        return new ShopPage(playerRef, shopId);
    }
}
```

**ShopPage.java:**
```java
public class ShopPage extends BasicCustomUIPage {
    private final String shopId;

    public ShopPage(PlayerRef playerRef, String shopId) {
        super(playerRef, CustomPageLifetime.CanDismiss);
        this.shopId = shopId;
    }

    @Override
    public void build(UICommandBuilder cmd) {
        cmd.append("ShopPage.ui");
        cmd.set("#ShopTitle.Text", "Shop: " + shopId);
    }
}
```

**Plugin setup:**
```java
@Override
protected void setup() {
    OpenCustomUIInteraction.registerCustomPageSupplier(
        this,
        ShopPageSupplier.class,
        "MyShop",
        new ShopPageSupplier()   // supplier INSTANCE, not a codec
    );
}
```

**JSON usage (e.g., in an NPC interaction):**
```json
{
  "Type": "OpenCustomUI",
  "Page": {
    "Id": "MyShop",
    "shopId": "blacksmith"
  }
}
```

---

## WindowManager
**Package:** `com.hypixel.hytale.server.core.entity.entities.player.windows`

Manage player windows (inventory, crafting, etc.).

Most lifecycle methods require ECS parameters (`Ref<EntityStore>`, `Store<EntityStore>`,
or `ComponentAccessor<EntityStore>`).

```java
// Initialization
void init(PlayerRef playerRef)

// Open windows
OpenWindow openWindow(Ref<EntityStore> ref, Window window, Store<EntityStore> store)
List<OpenWindow> openWindows(Ref<EntityStore> ref, Store<EntityStore> store, Window... windows)

// Set/Get by slot
void setWindow(int slotId, Window window)
Window getWindow(int slotId)
List<Window> getWindows()

// Update
void updateWindow(Window window)
void updateWindows()
void markWindowChanged(int slotId)

// Close
Window closeWindow(Ref<EntityStore> ref, int slotId, ComponentAccessor<EntityStore> accessor)
void closeAllWindows(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)

// Validation
void validateWindows(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)
```

### Window Class
**Package:** `com.hypixel.hytale.server.core.entity.entities.player.windows`

Abstract base class for player windows.

```java
// Constructor
Window(WindowType type)

// Initialization (called by framework)
void init(PlayerRef playerRef, WindowManager windowManager)

// Abstract - must implement
abstract JsonObject getData()  // Window data for client
protected abstract boolean onOpen0(Ref<EntityStore> ref, Store<EntityStore> store)
protected abstract void onClose0(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)

// Event handling
void handleAction(Ref<EntityStore> ref, Store<EntityStore> store, WindowAction action)

// Properties
WindowType getType()
int getId()
void setId(int id)
PlayerRef getPlayerRef()

// Lifecycle
void close(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)

// Close event registration
EventRegistration registerCloseEvent(Consumer<Window.WindowCloseEvent> handler)
EventRegistration registerCloseEvent(short priority, Consumer<Window.WindowCloseEvent> handler)
EventRegistration registerCloseEvent(EventPriority priority, Consumer<Window.WindowCloseEvent> handler)
```

#### Window Subclasses

| Class | Description |
|-------|-------------|
| `ContainerWindow` | Container-based windows |
| `ItemContainerWindow` | Item container windows |
| `BlockWindow` | Block interaction windows |
| `ValidatedWindow` | Windows with validation |

### WindowType Enum
**Package:** `com.hypixel.hytale.protocol.packets.window`

| Value | Description |
|-------|-------------|
| `Container` | Generic container window |
| `PocketCrafting` | Quick/pocket crafting |
| `BasicCrafting` | Standard crafting table |
| `DiagramCrafting` | Blueprint-based crafting |
| `StructuralCrafting` | Building/structural crafting |
| `Processing` | Processing bench (smelting, etc.) |
| `Memories` | Memories/journal window |

```java
static WindowType[] values()
static WindowType valueOf(String name)
int getValue()
static WindowType fromValue(int value)
```

### OpenWindow
**Package:** `com.hypixel.hytale.protocol.packets.window`

Protocol packet representing an opened window.

```java
// Fields
int id                           // Window slot ID
WindowType windowType            // Type of window
String windowData                // JSON data for client
InventorySection inventory       // Associated inventory
ExtraResources extraResources    // Additional resources

// Methods
int getId()
```

### Usage Example
```java
WindowManager windows = player.getWindowManager();

// Open a window and get reference (ECS params required)
Window myWindow = new MyCustomWindow(WindowType.Container);
OpenWindow opened = windows.openWindow(ref, myWindow, store);

int slotId = opened.getId();

// Later, close by slot ID
windows.closeWindow(ref, slotId, store);
```

---

## HudManager
**Package:** `com.hypixel.hytale.server.core.entity.entities.player.hud`

Manage HUD visibility and custom HUD elements.

```java
// Custom HUD
CustomUIHud getCustomHud()

// Visibility control
Set<HudComponent> getVisibleHudComponents()
void setVisibleHudComponents(PlayerRef playerRef, HudComponent... components)
void setVisibleHudComponents(PlayerRef playerRef, Set<HudComponent> components)

// Show/Hide specific components
void showHudComponents(PlayerRef playerRef, HudComponent... components)
void showHudComponents(PlayerRef playerRef, Set<HudComponent> components)
void hideHudComponents(PlayerRef playerRef, HudComponent... components)

// Custom HUD
void setCustomHud(PlayerRef playerRef, CustomUIHud hud)

// Reset
void resetHud(PlayerRef playerRef)
void resetUserInterface(PlayerRef playerRef)

// Network
void sendVisibleHudComponents(PacketHandler handler)
```

### HudComponent Enum
**Package:** `com.hypixel.hytale.protocol.packets.interface_`

Individual HUD components that can be shown or hidden.

| Value | Description |
|-------|-------------|
| `Hotbar` | Item hotbar at bottom of screen |
| `StatusIcons` | Status effect icons |
| `Reticle` | Crosshair/targeting reticle |
| `Chat` | Chat window |
| `Requests` | Friend/party requests |
| `Notifications` | System notifications |
| `KillFeed` | Combat kill feed |
| `InputBindings` | Key binding hints |
| `PlayerList` | Online player list (Tab) |
| `EventTitle` | Event title display |
| `Compass` | Navigation compass |
| `ObjectivePanel` | Quest/objective panel |
| `PortalPanel` | Portal information |
| `BuilderToolsLegend` | Builder mode tools legend |
| `Speedometer` | Vehicle speed display |
| `UtilitySlotSelector` | Utility item selector |
| `BlockVariantSelector` | Block variant picker |
| `BuilderToolsMaterialSlotSelector` | Builder material selector |
| `Stamina` | Stamina bar |
| `AmmoIndicator` | Ammunition counter |
| `Health` | Health bar |
| `Mana` | Mana bar |
| `Oxygen` | Oxygen/breath bar |
| `Sleep` | Sleep indicator |

```java
static HudComponent[] values()
static HudComponent valueOf(String name)
int getValue()
static HudComponent fromValue(int value)
```

### Usage Example
```java
HudManager hud = player.getHudManager();

// Show only essential HUD elements
hud.setVisibleHudComponents(playerRef,
    HudComponent.Hotbar,
    HudComponent.Health,
    HudComponent.Reticle);

// Hide chat temporarily
hud.hideHudComponents(playerRef, HudComponent.Chat);

// Show stamina bar
hud.showHudComponents(playerRef, HudComponent.Stamina);
```

> **See also:** [Player API](player.md#player-events)

---

## CustomUIHud
**Package:** `com.hypixel.hytale.server.core.entity.entities.player.hud`

Abstract base class for custom HUD overlays. Extend this to add your own icons, text, or other elements to the player's HUD that persist while playing.

### API
```java
// Constructor
CustomUIHud(PlayerRef playerRef)

// Abstract - must implement
protected abstract void build(UICommandBuilder cmd)

// Update HUD
void show()                                    // Force refresh (calls build() internally)
void update(boolean clear, UICommandBuilder cmd)  // Update with commands

// Access
PlayerRef getPlayerRef()
```

### CustomUIHud vs Native HUD Components

CustomUIHud creates a **separate overlay layer** that renders alongside (not instead of) the native HUD components.

| System | What It Controls | How to Use |
|--------|------------------|------------|
| Native HudComponents | Built-in elements (Health bar, Mana bar, Hotbar, etc.) | `hud.showHudComponents()`, `hud.hideHudComponents()` |
| CustomUIHud | Your custom overlay (text, icons, panels) | `hud.setCustomHud()` |

**Key point:** CustomUIHud does NOT modify or extend the native HUD. To display custom health/mana values:
- Create a CustomUIHud with your own Label elements
- The native Health/Mana bars will still appear separately (unless you hide them)

```java
// Example: Custom HUD + selective native components
HudManager hud = player.getHudManager();

// Hide native health/mana bars (optional)
hud.hideHudComponents(playerRef, HudComponent.Health, HudComponent.Mana);

// Show custom HUD with your own health/mana display
hud.setCustomHud(playerRef, new StatusHud(playerRef));
```

### Obtaining ECS Context for UI Operations

Custom HUDs typically need ECS context (store, ref, playerRef) to interact with game state. This context is obtained from command handlers or event callbacks:

**From Commands (most common):**
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    // store, ref, playerRef provided by command framework
    Player player = store.getComponent(ref, Player.getComponentType());
    player.getHudManager().setCustomHud(playerRef, new StatusHud(playerRef));
}
```

**From Events:**
```java
getEventRegistry().register(SomeEvent.class, event -> {
    // Context available from event
    Store<EntityStore> store = event.getStore();
    Ref<EntityStore> ref = event.getRef();
    // ...
});
```

> **`setCustomHud(...)` and any store/chunk access must run on the world thread.** A *global*
> event consumer (e.g. `AddPlayerToWorldEvent`) runs on a `ForkJoinPool.commonPool` worker, so
> attaching a HUD or touching the store there throws
> `IllegalStateException: Assert not in thread! ... but was in Thread[ForkJoinPool.commonPool-worker-N]`.
> `AddPlayerToWorldEvent` also fires **before** the world's chunks/players are loaded
> (`loadedChunksCount=0`), so the store isn't readable yet even on the right thread. Attach from an
> **ECS system tick**, a **command**, or `world.execute(Runnable)` (`World` implements `Executor`)
> instead of a global event handler.

> **See also:** [Commands API](commands.md) for command context details

### Implementation Example

Full working example: [`examples/ui/.../StatusHud.java`](../examples/ui/src/main/java/hytale/examples/ui/StatusHud.java) (and its driver [`StatusHudCommand.java`](../examples/ui/src/main/java/hytale/examples/ui/StatusHudCommand.java), which stores one HUD per player and calls `updateStats`).

```java
public class StatusHud extends CustomUIHud {
    public StatusHud(PlayerRef playerRef) {
        super(playerRef);
    }

    @Override
    protected void build(UICommandBuilder cmd) {
        cmd.append("StatusHud.ui");
    }

    /**
     * Update HUD values dynamically.
     * Call this method whenever stats change.
     */
    public void updateStats(int health, int mana) {
        UICommandBuilder cmd = new UICommandBuilder();
        cmd.set("#HealthLabel.Text", "Health: " + health);   // String — required in a HUD
        cmd.set("#ManaLabel.Text", "Mana: " + mana);
        update(false, cmd);  // false = apply incrementally
    }
}

// Register the custom HUD
Player player = store.getComponent(ref, Player.getComponentType());
HudManager hud = player.getHudManager();
StatusHud statusHud = new StatusHud(playerRef);
hud.setCustomHud(playerRef, statusHud);

// Later, update the HUD
statusHud.updateStats(85, 50);
```

### Dynamic Updates

```java
void update(boolean clear, UICommandBuilder cmd)
```

**Parameters:**
- `clear=false` — Apply commands incrementally (recommended for updates)
- `clear=true` — Remove all content before applying commands (full rebuild)

**When to use each:**

| Scenario | Use |
|----------|-----|
| Updating text, values, properties | `update(false, cmd)` |
| Changing layout structure | `update(true, cmd)` |
| Switching HUD modes/states | `update(true, cmd)` |
| Frequent value updates | `update(false, cmd)` |

**Example:**
```java
// Incremental update (recommended for most cases)
UICommandBuilder cmd = new UICommandBuilder();
cmd.set("#HealthLabel.Text", "Health: 85");
cmd.set("#ManaLabel.Text", "Mana: 50");
customHud.update(false, cmd);

// Full rebuild (use sparingly)
UICommandBuilder rebuildCmd = new UICommandBuilder();
rebuildCmd.append("AlternateHud.ui");
customHud.update(true, rebuildCmd);
```

### show() vs update() Relationship

| Method | When Called | What Happens |
|--------|-------------|--------------|
| `show()` | Initial display or force refresh | Calls `build()` internally, sends full UI to client |
| `update(clear, cmd)` | After initial display | Sends only the specified commands without re-calling `build()` |

The `show()` method is called automatically when you call `setCustomHud()`. Use `update()` for all subsequent changes.

### UICommandBuilder Method Support

All UICommandBuilder methods work in both `build()` and `update()`:

| Method | Description |
|--------|-------------|
| `set(selector, value)` | Set element property (String, boolean, int, float, etc.) |
| `setNull(selector)` | Set property to null |
| `setObject(selector, obj)` | Set arbitrary object |
| `clear(selector)` | Clear element contents |
| `remove(selector)` | Remove element from DOM |
| `append(path)` | Append .ui file to root |
| `append(selector, path)` | Append .ui file to element |
| `appendInline(selector, dsl)` | Append inline DSL markup |
| `insertBefore(selector, path)` | Insert .ui file before element |
| `insertBeforeInline(selector, dsl)` | Insert inline DSL before element |

### Element Targeting Syntax

Target elements using `#ElementId.Property` syntax:

```java
UICommandBuilder cmd = new UICommandBuilder();

// Set text content
cmd.set("#HealthLabel.Text", "Health: 100");

// Set visibility
cmd.set("#WarningIcon.Visible", false);

// Set numeric values
cmd.set("#ProgressBar.Value", 0.75f);

// Set colors (as hex string)
cmd.set("#StatusLabel.Style.TextColor", "#FF0000");

// Append to container
cmd.append("#ItemContainer", "Components/Item.ui");

// Clear container contents
cmd.clear("#NotificationList");

// Remove specific element
cmd.remove("#TempMessage");
```

### Event Handling

**CustomUIHud does NOT support event handling.** The `build()` method only receives `UICommandBuilder`, not `UIEventBuilder`.

For UIs that need to respond to user interaction (button clicks, input changes, etc.), use [CustomUIPage](#customuipage) instead.

| Feature | CustomUIHud | CustomUIPage |
|---------|-------------|--------------|
| Event handling | ❌ No | ✅ Yes |
| `build()` signature | `build(UICommandBuilder)` | `build(Ref, UICommandBuilder, UIEventBuilder, Store)` |
| `handleDataEvent()` | Not available | Override to handle events |

### Multiple HUDs

**Only one CustomUIHud can be active per player.** The `HudManager` stores a single `customHud` reference. Calling `setCustomHud()` replaces any existing custom HUD.

To display multiple HUD elements simultaneously:
1. **Combine in one HUD:** Include all elements in a single CustomUIHud with multiple containers
2. **Use native components:** Combine CustomUIHud with built-in `HudComponent` elements

```java
// Example: Combined HUD with multiple sections
public class CombinedHud extends CustomUIHud {
    @Override
    protected void build(UICommandBuilder cmd) {
        cmd.append("CombinedHud.ui");  // Contains both status and minimap sections
    }
}
```

### .ui File Example (StatusHud.ui)
```
Group {
    Anchor: (Top: 10, Right: 10, Width: 200, Height: 80);
    Background: (Color: #000000(0.5));
    Padding: (Full: 10);
    LayoutMode: Top;

    Label #HealthLabel {
        Style: (FontSize: 16, TextColor: #FF4444);
        Text: "Health: 100";
    }

    Label #ManaLabel {
        Anchor: (Top: 5);
        Style: (FontSize: 16, TextColor: #4444FF);
        Text: "Mana: 100";
    }
}
```

### Manifest Requirements

CustomUIHud requires the plugin manifest to include:

```json
{
    "Group": "YourGroup",
    "Name": "YourPlugin",
    "Main": "your.package.YourPlugin",
    "IncludesAssetPack": true
}
```

The `"IncludesAssetPack": true` setting is **required** for any plugin using custom `.ui` files.

### Removing Custom HUD
To remove a custom HUD, set it to null or reset the HUD:

```java
hud.setCustomHud(playerRef, null);
// Or reset everything:
hud.resetHud(playerRef);
```

### Managing HUD State Across Players

When managing HUDs for multiple players (e.g., from commands), store HUD references in a thread-safe collection:

> **Reconnect caveat:** a player who rejoins keeps the same `UUID` but gets a **new `PlayerRef`**.
> The `computeIfAbsent` below returns the *stale* HUD (bound to the dead connection), so the overlay
> won't reappear on the second join. Either remove the entry on `PlayerDisconnectEvent` (the
> `onPlayerDisconnect` hook below does this — make sure it's actually wired up), or compare the stored
> HUD's [`getPlayerRef()`](#customuihud) to the player's current `PlayerRef` and rebuild on mismatch.

```java
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public class StatusHudManager {
    // Thread-safe storage for HUD instances by player UUID
    private static final ConcurrentHashMap<UUID, StatusHud> playerHuds = new ConcurrentHashMap<>();

    /**
     * Show HUD for a player, creating if necessary.
     */
    public static void showHud(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef) {
        UUID playerId = playerRef.getUuid();
        Player player = store.getComponent(ref, Player.getComponentType());

        // Get or create HUD instance
        StatusHud hud = playerHuds.computeIfAbsent(playerId, id -> new StatusHud(playerRef));

        // Register with HudManager
        player.getHudManager().setCustomHud(playerRef, hud);
    }

    /**
     * Update HUD values for a player.
     */
    public static void updateHud(UUID playerId, int health, int mana) {
        StatusHud hud = playerHuds.get(playerId);
        if (hud != null) {
            UICommandBuilder cmd = new UICommandBuilder();
            cmd.set("#HealthLabel.Text", "Health: " + health);
            cmd.set("#ManaLabel.Text", "Mana: " + mana);
            hud.update(false, cmd);
        }
    }

    /**
     * Hide and remove HUD for a player.
     */
    public static void hideHud(PlayerRef playerRef, Player player) {
        UUID playerId = playerRef.getUUID();
        playerHuds.remove(playerId);
        player.getHudManager().setCustomHud(playerRef, null);
    }

    /**
     * Clean up when player disconnects.
     */
    public static void onPlayerDisconnect(UUID playerId) {
        playerHuds.remove(playerId);
    }
}
```

**Usage from commands:**
```java
public class HudCommand extends AbstractPlayerCommand {
    private final Arg<Mode> modeArg;

    public enum Mode { SHOW, HIDE }

    public HudCommand() {
        super("statushud", "Toggle status HUD");
        modeArg = withRequiredArg("mode", "show or hide",
            ArgTypes.forEnum("mode", Mode.class));
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        Player player = store.getComponent(ref, Player.getComponentType());
        Mode mode = ctx.get(modeArg);

        if (mode == Mode.SHOW) {
            StatusHudManager.showHud(store, ref, playerRef);
            playerRef.sendMessage(Message.raw("Status HUD enabled"));
        } else {
            StatusHudManager.hideHud(playerRef, player);
            playerRef.sendMessage(Message.raw("Status HUD disabled"));
        }
    }
}
```

**Key points:**
- Use `ConcurrentHashMap` for thread-safety (commands may execute concurrently)
- Key by player UUID, not PlayerRef (refs may change between sessions)
- Clean up HUD references when players disconnect to prevent memory leaks
- Store references allow updating HUD values dynamically without recreating

---

## Choosing Between CustomUIPage and CustomUIHud

| Feature | CustomUIPage | CustomUIHud |
|---------|--------------|-------------|
| **Display Mode** | Full-screen overlay | Persistent overlay |
| **Blocks Gameplay** | Yes (modal) | No (non-blocking) |
| **Event Handling** | ✅ Yes (`UIEventBuilder`) | ❌ No |
| **User Can Dismiss** | Yes (ESC key, configurable) | No (must remove programmatically) |
| **Typical Use Cases** | Menus, inventories, dialogs | Health bars, status indicators, minimaps |
| **Lifetime** | Temporary (opened/closed) | Persistent while active |

**Use CustomUIPage when:**
- User needs to interact with buttons, inputs, or other controls
- UI should pause or overlay gameplay
- UI is temporary (settings menu, inventory screen)

**Use CustomUIHud when:**
- Displaying passive information (health, mana, score)
- UI should not interrupt gameplay
- Information needs to persist on screen

---

## HotbarManager
**Package:** `com.hypixel.hytale.server.core.entity.entities.player`

Manage player hotbar configurations.

```java
// Constants
static final int HOTBARS_MAX

// Save/Load hotbar configurations
void saveHotbar(Ref<EntityStore> ref, short index, ComponentAccessor<EntityStore> accessor)
void loadHotbar(Ref<EntityStore> ref, short index, ComponentAccessor<EntityStore> accessor)

// State
int getCurrentHotbarIndex()
boolean getIsCurrentlyLoadingHotbar()
```

---

## File Browser System

### FileBrowserConfig
**Package:** `com.hypixel.hytale.server.core.ui.browser`

Configuration record for file browser UI.

```java
// Builder pattern
static FileBrowserConfig.Builder builder()

// Accessor methods
String listElementId()
String rootSelectorId()
String searchInputId()
String currentPathId()
List<RootEntry> roots()
Set<String> allowedExtensions()
boolean enableRootSelector()
boolean enableSearch()
boolean enableDirectoryNav()
boolean enableMultiSelect()
int maxResults()
FileListProvider customProvider()
```

### FileBrowserConfig.Builder

```java
Builder listElementId(String id)
Builder rootSelectorId(String id)
Builder searchInputId(String id)
Builder currentPathId(String id)
Builder roots(List<RootEntry> roots)
Builder allowedExtensions(Set<String> extensions)
Builder enableRootSelector(boolean enable)
Builder enableSearch(boolean enable)
Builder enableDirectoryNav(boolean enable)
Builder enableMultiSelect(boolean enable)
Builder maxResults(int max)
Builder customProvider(FileListProvider provider)
FileBrowserConfig build()
```

### ServerFileBrowser
**Package:** `com.hypixel.hytale.server.core.ui.browser`

Server-side file browser implementation.

```java
// Constructors
ServerFileBrowser(FileBrowserConfig config)
ServerFileBrowser(FileBrowserConfig config, Path rootPath, Path currentPath)

// Build UI
void buildRootSelector(UICommandBuilder cmdBuilder, UIEventBuilder eventBuilder)
void buildSearchInput(UICommandBuilder cmdBuilder, UIEventBuilder eventBuilder)
void buildCurrentPath(UICommandBuilder cmdBuilder)
void buildFileList(UICommandBuilder cmdBuilder, UIEventBuilder eventBuilder)
void buildUI(UICommandBuilder cmdBuilder, UIEventBuilder eventBuilder)

// Event Handling
boolean handleEvent(FileBrowserEventData eventData)

// Navigation
Path getRoot()
void setRoot(Path path)
Path getCurrentDir()
void setCurrentDir(Path path)
String getSearchQuery()
void setSearchQuery(String query)
void navigateUp()
void navigateTo(Path path)

// Selection
Set<String> getSelectedItems()
void addSelection(String item)
void clearSelection()

// Utility
FileBrowserConfig getConfig()
```

### Usage Example
```java
FileBrowserConfig config = FileBrowserConfig.builder()
    .listElementId("file-list")
    .enableSearch(true)
    .enableDirectoryNav(true)
    .allowedExtensions(Set.of("json", "txt"))
    .maxResults(50)
    .build();

ServerFileBrowser browser = new ServerFileBrowser(config);

UICommandBuilder cmd = new UICommandBuilder();
UIEventBuilder events = new UIEventBuilder();
browser.buildUI(cmd, events);
```

---

## WindowCloseEvent
**Class:** `com.hypixel.hytale.server.core.entity.entities.player.windows.Window.WindowCloseEvent`

This is an inner class of `Window` (`Window.WindowCloseEvent`), not a standalone class.

Event fired when a player window is closed. Implements `IEvent<Void>`.

This is a minimal event that signals window closure. It does not provide additional methods beyond the basic event interface.

### Usage Example
```java
import com.hypixel.hytale.server.core.entity.entities.player.windows.Window;

@Override
protected void setup() {
    getEventRegistry().register(Window.WindowCloseEvent.class, event -> {
        System.out.println("A window was closed");
    });
}
```

---

## Supporting Classes

### LocalizableString
Translatable UI strings with parameter support.

### DropdownEntryInfo
Dropdown menu entry configuration.

### ItemGridSlot
Inventory grid slot definition for UI display.

### PatchStyle
UI styling/theming support for 9-slice patches.

---

## Usage Examples

### Create and Update Custom UI
```java
@Override
protected void execute(CommandContext ctx, Store<EntityStore> store,
                      Ref<EntityStore> ref, PlayerRef playerRef, World world) {
    Player player = store.getComponent(ref, Player.getComponentType());

    // Build UI commands
    UICommandBuilder builder = new UICommandBuilder();
    builder.set("score.value", 100)
           .set("player.name", playerRef.getUsername())
           .append("MyUI.ui");  // Load .ui file from Common/UI/Custom/

    // Build event handlers
    UIEventBuilder events = new UIEventBuilder();
    events.addEventBinding(CustomUIEventBindingType.Activating, "button");

    // Send to client via managers
    // Implementation depends on specific UI type (Page, Window, HUD)
}
```

### Show/Hide HUD Components
```java
Player player = store.getComponent(ref, Player.getComponentType());
HudManager hud = player.getHudManager();

// Hide all HUD
hud.setVisibleHudComponents(playerRef);

// Show specific components
hud.showHudComponents(playerRef, HudComponent.Health, HudComponent.Hotbar);
```

### Open Custom Page
```java
Player player = store.getComponent(ref, Player.getComponentType());
PageManager pages = player.getPageManager();

CustomUIPage customPage = new MyCustomPage(playerRef);
pages.openCustomPage(ref, store, customPage);
```

### Window Management
```java
Player player = store.getComponent(ref, Player.getComponentType());
WindowManager windows = player.getWindowManager();

Window inventoryWindow = new MyCustomWindow(WindowType.Container);
OpenWindow opened = windows.openWindow(ref, inventoryWindow, store);

// Later, close it
windows.closeWindow(ref, opened.getId(), store);
```

---

## Notes

- Window/Page/HUD managers handle network synchronization automatically
- Use `Value.ref()` for dynamic bindings that update when document values change
- File browser provides secure path resolution to prevent directory traversal

---

## Gotchas & Errors

Backtick-quoted error strings below are literal messages thrown by the UI system. The first two were verified against the build-12 `HytaleServer.jar`; the rest were observed at runtime (build-12) and may shift between builds.

- **`CustomUIPage doesn't support events!`** → you registered an event binding (or an event was dispatched) on a page whose `build()` override only takes `UICommandBuilder` — the display-only `BasicCustomUIPage` form has no `UIEventBuilder`. Fix: override the four-argument `build(Ref, UICommandBuilder, UIEventBuilder, Store)` and register bindings there (see [Event Handling in Custom Pages](#event-handling-in-custom-pages)).
- **Symptom:** a second `setCustomHud()` call makes your first custom HUD disappear → `HudManager` stores a single `customHud` per player, so each call replaces the previous one. Fix: combine elements into one `CustomUIHud`, and pass `null` to `setCustomHud()` to remove it (see [Multiple HUDs](#multiple-huds)).
- **Symptom:** a `CustomUIHud` ignores `addEventBinding`/click handling → `CustomUIHud.build()` receives only `UICommandBuilder`, never `UIEventBuilder`; HUDs cannot handle events. Fix: use a [`CustomUIPage`](#customuipage) for interactive UI (see [Event Handling](#event-handling)).
- **Symptom:** a `CustomUIHud` appears but the player gets a mouse cursor and can no longer mouse-look → any hit-testable element (a `Group` with a `Background`, `Label`s, etc.) grabs the pointer. A HUD has no event handling, so it should never be a hit-test target. Fix: set **`HitTestVisible: false`** on the root element *and its children* in the `.ui` (the engine's own `Common/UI/Custom/Pages/EntitySpawnPage.ui` does this).
- **`failed to apply customui hud commands`** (client then disconnects) → you passed a `Message` to `UICommandBuilder.set(selector, value)` in a **HUD** (`build()`/`update()`). The `set(String, Message)` overload is fine for *pages* but not for the HUD layer. Fix: resolve text to a plain `String` before `set(...)`; for a translation key, resolve it server-side ([i18n](i18n.md#resolving-a-key-to-text-server-side)) — you can't defer localization to the client in a HUD label.
- **Symptom:** `IllegalStateException: Assert not in thread!` (`ForkJoinPool.commonPool-worker-N`) when attaching a HUD or reading the store → you ran `setCustomHud(...)`/store access off the world thread, typically from a global event consumer. Fix: attach from an ECS system tick, a command, or `world.execute(Runnable)` (see [Obtaining ECS Context](#obtaining-ecs-context-for-ui-operations)).
- **Symptom:** a UUID-keyed HUD doesn't reappear after a player reconnects → the stored HUD is bound to the player's old `PlayerRef`. Fix: prune on `PlayerDisconnectEvent`, or rebuild when the stored HUD's `getPlayerRef()` differs from the current one (see [Managing HUD State Across Players](#managing-hud-state-across-players)).

---

## Related Documentation

- [UI Overview](ui.md) - System architecture and quick start
- [Elements](ui-elements.md) - All element types
- [Styling](ui-styling.md) - Layout and visual styling
- [Templates](ui-templates.md) - Variables and localization
- [Plugin Lifecycle](plugin-lifecycle.md) - Plugin setup
- [Player API](player.md) - Player events

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
