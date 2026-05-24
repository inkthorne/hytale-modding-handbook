# UI System

**Doc type:** Guide

Hytale provides a comprehensive UI system for creating custom interfaces. UIs are defined using a curly-brace DSL format and managed through server-side Java APIs.

---

## Quick Navigation

| Document | Description |
|----------|-------------|
| [Elements](ui-elements.md) | All element types (Group, Label, Button, TextField, etc.) |
| [Styling & Layout](ui-styling.md) | Anchor, padding, colors, state-based styling |
| [Templates & Variables](ui-templates.md) | Imports, variables, localization |
| [Java API](ui-api.md) | UICommandBuilder, UIEventBuilder, PageManager, HudManager |

---

## Overview

**Package:** `com.hypixel.hytale.server.core.ui`

The UI system consists of:

- **DSL Files** (`.ui`) - Define UI structure and styling
- **Java API** - Build commands, handle events, manage pages/windows/HUD
- **Asset Pack** - Textures and resources for UI elements

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Server                           │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │  CustomUIPage   │───▶│  UICommandBuilder   │    │
│  │  (Java class)   │    │  UIEventBuilder     │    │
│  └─────────────────┘    └─────────────────────┘    │
│           │                       │                 │
│           ▼                       ▼                 │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │   .ui Files     │    │   Network Sync      │    │
│  │ (DSL definition)│    │   (automatic)       │    │
│  └─────────────────┘    └─────────────────────┘    │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                    Client                           │
│  ┌─────────────────────────────────────────────┐   │
│  │              Rendered UI                     │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Architecture
```
Player
├── PageManager        (full-screen pages)
│   └── CustomUIPage / BasicCustomUIPage  (plugin-defined pages)
├── WindowManager      (overlay windows)
│   └── Window         (Container, crafting, etc.)
└── HudManager         (always-visible HUD)
    ├── HudComponent   (built-in native elements)
    └── CustomUIHud    (plugin overlay)

Build pipeline (shared by pages/windows/HUD):
.ui DSL file  ──append()──▶  UICommandBuilder  ──▶  client render
                            UIEventBuilder     ──▶  server event handling
```

## Key Classes
| Class | Location | Description |
|-------|----------|-------------|
| `BasicCustomUIPage` | `server.core.entity.entities.player.pages` | Base class for plugin-defined full-screen pages |
| `CustomUIHud` | `server.core.entity.entities.player.hud` | Base class for persistent custom HUD overlays |
| `UICommandBuilder` | `server.core.ui.builder` | Builds UI update commands (append, set, clear) |
| `UIEventBuilder` | `server.core.ui.builder` | Registers server-side event bindings |
| `PageManager` | `server.core.entity.entities.player.pages` | Opens and closes full-screen pages |
| `WindowManager` | `server.core.entity.entities.player.windows` | Manages overlay windows |
| `HudManager` | `server.core.entity.entities.player.hud` | Controls HUD component visibility and custom HUD |

---

## Quick Start

### 1. Create a .ui File

**Location:** `src/main/resources/Common/UI/Custom/MyPage.ui`

```
Group {
    LayoutMode: CenterMiddle;
    Anchor: Full;
    Background: (Color: #000000(0.7));

    Group #Panel {
        Anchor: (Width: 400, Height: 200);
        Background: (Color: #1a1a2e(0.95));
        Padding: (Full: 20);
        LayoutMode: Top;

        Label #Title {
            Style: (FontSize: 28, TextColor: #e94560, HorizontalAlignment: Center);
            Text: "Hello World";
        }

        Label #Subtitle {
            Anchor: (Top: 10);
            Style: (FontSize: 16, TextColor: #aaaaaa, HorizontalAlignment: Center);
            Text: "Press ESC to close";
        }
    }
}
```

### 2. Create a Custom Page Class

```java
public class MyPage extends BasicCustomUIPage {
    public MyPage(PlayerRef playerRef) {
        super(playerRef, CustomPageLifetime.CanDismiss);
    }

    @Override
    public void build(UICommandBuilder cmd) {
        cmd.append("MyPage.ui");
    }
}
```

### 3. Open the Page

```java
Player player = store.getComponent(ref, Player.getComponentType());
player.getPageManager().openCustomPage(ref, store, new MyPage(playerRef));
```

### 4. Update Manifest

Add to your `manifest.json`:

```json
{
    "Group": "MyPlugin",
    "Name": "MyPlugin",
    "Main": "com.example.MyPlugin",
    "IncludesAssetPack": true
}
```

---

## DSL Syntax Summary

### Basic Structure

```
ElementType #OptionalId {
    Property: value;
    Property: (nested: properties);

    ChildElement {
        // ...
    }
}
```

### Key Rules

1. **Root Group has no ID** - The outermost `Group` must be anonymous
2. **Properties end with semicolon** - `Property: value;`
3. **Nested properties use parentheses** - `Style: (FontSize: 24, TextColor: #ffffff);`
4. **Colors use hex format** - `#RRGGBB` or `#RRGGBB(alpha)`
5. **Events registered server-side** - No `OnActivating` in .ui files

### Common Patterns

**Centered Panel:**
```
Group {
    LayoutMode: CenterMiddle;
    Anchor: Full;

    Group #Panel {
        Anchor: (Width: 400, Height: 300);
        // content
    }
}
```

**Vertical Stack:**
```
Group {
    LayoutMode: Top;
    Padding: (Full: 10);

    Label { Text: "First"; }
    Label { Text: "Second"; }
}
```

**Button with Hover State:**
```
TextButton #MyButton {
    Anchor: (Width: 150, Height: 44);
    Style: (
        Default: (Background: (Color: #3498db), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)),
        Hovered: (Background: (Color: #5dade2), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center))
    );
    Text: "Click Me";
}
```

---

## File Requirements

### Directory Structure

```
src/main/resources/
└── Common/
    └── UI/
        └── Custom/
            ├── MyPage.ui
            ├── Components/
            │   └── Button.ui
            └── Theme.ui
```

### Manifest Configuration

Plugins with UI assets must include:

```json
{
    "IncludesAssetPack": true
}
```

### File Paths in Code

Paths are relative to `Common/UI/Custom/`:

```java
cmd.append("MyPage.ui");                  // Common/UI/Custom/MyPage.ui
cmd.append("Pages/Settings.ui");          // Common/UI/Custom/Pages/Settings.ui
cmd.append("#container", "Item.ui");      // Append to element
```

---

## UI Types

| Type | Description | Manager |
|------|-------------|---------|
| **Page** | Full-screen UI (inventory, settings) | `PageManager` |
| **Window** | Overlay UI (crafting, containers) | `WindowManager` |
| **HUD** | Always-visible elements (health, hotbar) | `HudManager` |

### Pages

Full-screen interfaces that replace the game view:

```java
PageManager pages = player.getPageManager();
pages.openCustomPage(ref, store, new MyCustomPage(playerRef));
pages.setPage(ref, store, Page.None);  // Close
```

### Windows

Overlay UIs that appear over the game:

```java
WindowManager windows = player.getWindowManager();
OpenWindow opened = windows.openWindow(new MyWindow(WindowType.Container));
windows.closeWindow(opened.getId());
```

### HUD

Always-visible interface elements:

```java
HudManager hud = player.getHudManager();
hud.setVisibleHudComponents(playerRef, HudComponent.Hotbar, HudComponent.Health);
hud.hideHudComponents(playerRef, HudComponent.Chat);
```

---

## Event Handling

UI events are handled server-side:

### Register Events

```java
@Override
public void build(Ref<EntityStore> ref, UICommandBuilder cmdBuilder,
                  UIEventBuilder eventBuilder, Store<EntityStore> store) {
    cmdBuilder.append("MyPage.ui");
    eventBuilder.addEventBinding(CustomUIEventBindingType.Activating, "MyButton");
    eventBuilder.addEventBinding(CustomUIEventBindingType.ValueChanged, "MyInput");
}
```

### Handle Events

```java
@Override
public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, String data) {
    switch (data) {
        case "MyButton" -> handleButtonClick(ref, store);
        case "MyInput" -> handleInputChange(ref, store);
    }
}
```

### Common Event Types

| Event | Use Case |
|-------|----------|
| `Activating` | Button clicks |
| `ValueChanged` | Input field changes |
| `SlotClicking` | Inventory slot clicks |
| `MouseEntered` / `MouseExited` | Hover effects |

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [Elements](ui-elements.md) | Group, Label, Button, TextField, Slider, etc. |
| [Styling & Layout](ui-styling.md) | Anchor, Padding, Background, State-based styling |
| [Templates & Variables](ui-templates.md) | File imports, variables, localization |
| [Java API](ui-api.md) | UICommandBuilder, PageManager, WindowManager, HudManager |
| [Plugin Lifecycle](plugin-lifecycle.md) | Plugin setup and registration |
| [Internationalization](i18n.md) | Localization system |
