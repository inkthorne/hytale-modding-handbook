# UI Example Plugin

Demonstrates the Hytale UI system with custom pages and HUD management.

## Commands

### `/menu`
Opens a simple custom UI page.

The page demonstrates:
- Loading a `.ui` definition file
- Using `CanDismiss` lifetime (press ESC to close)

### `/hud <show|hide>`
Toggles HUD components visibility.

**Examples:**
- `/hud show` - Shows hotbar, health, and reticle
- `/hud hide` - Hides all HUD components

### `/statushud <show|hide|update>`
Toggles a custom HUD overlay (`StatusHud`, a `CustomUIHud`) showing health/mana.

- `/statushud show` - Creates a `StatusHud`, registers it via `player.getHudManager().setCustomHud(playerRef, statusHud)`, and stores it in a per-player `ConcurrentHashMap<UUID, StatusHud>` for later updates.
- `/statushud update` - Looks up the stored HUD and calls `hud.updateStats(health, mana)` with sample values (a real plugin would pull these from game state).
- `/statushud hide` - Calls `setCustomHud(playerRef, null)` and removes the map entry.

> **Gotcha:** Only one `CustomUIHud` can be active per player at a time —
> calling `setCustomHud()` replaces any existing custom HUD.

## Building

```batch
build.bat
```

Or:

```batch
gradlew build
```

## Installation

Copy `build/libs/example-ui.jar` to:
```
%APPDATA%\Hytale\UserData\Mods\
```

**Important:** The manifest.json must have `"IncludesAssetPack": true` for the `.ui` file to load.

## Code Structure

- `UIPlugin.java` - Main plugin class, registers commands
- `MenuCommand.java` - Opens the custom menu page
- `HudCommand.java` - Toggles HUD visibility
- `StatusHudCommand.java` - Toggles/updates the custom status HUD overlay
- `StatusHud.java` - `CustomUIHud` subclass with dynamic `updateStats(...)` updates
- `pages/SimpleMenuPage.java` - Custom page implementation
- `Common/UI/Custom/SimpleMenuPage.ui` - Menu page UI definition (DSL format)
- `Common/UI/Custom/StatusHud.ui` - Status HUD UI definition (DSL format)

## UI File Format

The `SimpleMenuPage.ui` uses Hytale's curly-brace DSL format:

```
Group {
    LayoutMode: Center;

    Group #MenuContainer {
        Anchor: (Width: 400, Height: 200);
        Background: (Color: #333333(0.9));
        LayoutMode: Top;
        Padding: (Full: 20);

        Label #Title {
            Style: (FontSize: 24, TextColor: #FFFFFF, HorizontalAlignment: Center);
            Text: "Simple Menu";
        }

        Label #Subtitle {
            Anchor: (Top: 20);
            Style: (FontSize: 16, TextColor: #AAAAAA, HorizontalAlignment: Center);
            Text: "Press ESC to close";
        }
    }
}
```

**Note:** The root `Group` must NOT have an ID. Named elements go inside it.

This is the shipped, display-only page. To make it interactive, add a `Button`
with an `OnActivating: { SendData: "..."; }` handler and override
`handleDataEvent(...)` on the page (shown below) to receive the event.

## Key API Patterns

### Custom Page
The shipped `SimpleMenuPage` is display-only — it loads the `.ui` file and
nothing more:
```java
public class SimpleMenuPage extends BasicCustomUIPage {
    public SimpleMenuPage(PlayerRef playerRef) {
        super(playerRef, CustomPageLifetime.CanDismiss);
    }

    @Override
    public void build(UICommandBuilder cmd) {
        cmd.append("SimpleMenuPage.ui");
    }
}
```

To handle events from interactive elements (see the `Button`/`SendData` note
above), override `handleDataEvent` — this is *extending* the example, not part
of the shipped page:
```java
@Override
public void handleDataEvent(Ref<EntityStore> ref, Store<EntityStore> store, String data) {
    // Handle events from UI (e.g. data == "button_clicked")
}
```

### Opening a Page
```java
Player player = store.getComponent(ref, Player.getComponentType());
player.getPageManager().openCustomPage(ref, store, new MyPage(playerRef));
```

### HUD Control
```java
Player player = store.getComponent(ref, Player.getComponentType());
player.getHudManager().setVisibleHudComponents(playerRef,
    HudComponent.Hotbar,
    HudComponent.Health);
```
