# UI Elements Reference

**Doc type:** UI DSL · **Assets:** `Common/UI`

Comprehensive reference for all UI element types in Hytale's DSL.

---

## Quick Navigation

| Category | Elements |
|----------|----------|
| [Container](#container-elements) | Group |
| [Text](#text-elements) | Label, TimerLabel, HotkeyLabel |
| [Button](#button-elements) | Button, TextButton, BackButton, ActionButton |
| [Input](#input-elements) | TextField, CompactTextField, MultilineTextField, NumberField, CheckBox, Slider, FloatSlider, DropdownBox, ColorPickerDropdownBox |
| [Display](#display-elements) | Sprite, AssetImage, ItemSlot, ProgressBar, CircularProgressBar |
| [Navigation](#navigation-elements) | TabNavigation, TabButton |

**Related:** [Styling & Layout](ui-styling.md) | [Templates & Variables](ui-templates.md) | [Java API](ui-api.md) | [UI Overview](ui.md)

> **Templates vs. bare elements.** Several controls (checkboxes, dropdowns, input fields,
> sliders, progress bars, styled buttons) are almost always used through the named
> templates in `Common.ui` — e.g. `$C.@CheckBox`, `$C.@DropdownBox`, `$C.@TextField` —
> rather than as bare element tags. The template supplies the required style/background.
> Sections below show both the underlying element's properties and the template form.
> See [Templates & Variables](ui-templates.md#template-instantiation).

---

## Overview

Defined in `.ui` DSL files under `Common/UI` and provides element types for:
- Containers and layout (`Group`)
- Text display (`Label`, `TimerLabel`, `HotkeyLabel`)
- Buttons (`Button`, `TextButton`, `BackButton`, `ActionButton`)
- Inputs (`TextField`, `CheckBox`, `Slider`, `DropdownBox`, `NumberField`, and more)
- Display widgets (`Sprite`, `AssetImage`, `ItemSlot`, `ProgressBar`, `CircularProgressBar`)
- Navigation (`TabNavigation`, `TabButton`)

## Architecture
```
Group (container)
├── Text         : Label, TimerLabel, HotkeyLabel
├── Button       : Button, TextButton, BackButton, ActionButton
├── Input        : TextField, CompactTextField, MultilineTextField,
│                  NumberField, CheckBox, Slider, FloatSlider,
│                  DropdownBox, ColorPickerDropdownBox
├── Display      : Sprite, AssetImage, ItemSlot, ProgressBar, CircularProgressBar
└── Navigation   : TabNavigation, TabButton

Many controls are instantiated via named templates in Common.ui (e.g. $C.@CheckBox)
rather than as bare element tags — see Templates & Variables.
```

## Key Classes

These are DSL element types (not Java classes); the table lists the key element categories documented on this page.

| Element | Category | Description |
|---------|----------|-------------|
| `Group` | Container | Groups and lays out child elements; root `Group` must be ID-less |
| `Label` | Text | Static or dynamic text display |
| `TimerLabel` / `HotkeyLabel` | Text | Countdown text and hotkey-hint text |
| `Button` / `TextButton` / `BackButton` / `ActionButton` | Button | Clickable controls |
| `TextField` / `NumberField` / `CheckBox` / `Slider` / `DropdownBox` | Input | User input controls |
| `Sprite` / `AssetImage` / `ItemSlot` | Display | Image and item-slot display |
| `ProgressBar` / `CircularProgressBar` | Display | Progress indicators |
| `TabNavigation` / `TabButton` | Navigation | Tabbed navigation |

---

## Container Elements

### Group

Basic container for grouping and laying out child elements.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `LayoutMode` | Enum | Child layout mode |
| `Padding` | Padding | Internal spacing |
| `Background` | Background | Background color/texture |
| `Visible` | Boolean | Visibility state |
| `FlexWeight` | Number | Flex layout weight |
| `Opacity` | Number | Opacity (0.0 to 1.0) |

**Example:**
```
Group #MyContainer {
    Anchor: (Width: 400, Height: 300);
    LayoutMode: Top;
    Padding: (Full: 20);
    Background: (Color: #1a1a2e(0.95));
}
```

**Important:** The root `Group` in a `.ui` file must NOT have an ID. Named elements go inside it:

```
Group {
    LayoutMode: CenterMiddle;

    Group #Panel {
        // Named elements go here
    }
}
```

---

## Text Elements

### Label

Static or dynamic text display.

| Property | Type | Description |
|----------|------|-------------|
| `Text` | String | Text content |
| `Style` | Style | Text styling |
| `Anchor` | Anchor | Position and size |
| `Visible` | Boolean | Visibility state |
| `Opacity` | Number | Opacity (0.0 to 1.0) |

**Example:**
```
Label #Title {
    Style: (FontSize: 28, TextColor: #e94560, HorizontalAlignment: Center, RenderBold: true);
    Text: "Welcome";
}
```

**With Localization:**
```
Label #WelcomeText {
    Style: (FontSize: 16, TextColor: #ffffff);
    Text: %server.customUI.welcomeMessage;
}
```

**Note:** Label uses direct styling, not state-based styling. See [Styling](ui-styling.md#style-properties) for all style properties.

---

### TimerLabel

Label that counts down from a number of seconds.

| Property | Type | Description |
|----------|------|-------------|
| `Seconds` | Number | Countdown duration in seconds (expressions allowed, e.g. `15 * 60`) |
| `Style` | Style | Text styling |
| `Anchor` | Anchor | Position and size |

**Example** (from `Common/UI/Custom/Hud/TimeLeft.ui`):
```
TimerLabel #TimeLabel {
    Style: (FontSize: 32, Alignment: Center);
    Seconds: 15 * 60;
}
```

---

### HotkeyLabel

Displays the key currently bound to an input binding (auto-updates with the player's
keybind settings).

| Property | Type | Description |
|----------|------|-------------|
| `InputBindingKey` | String | Name of the input binding to display |
| `Anchor` | Anchor | Position and size |
| `Style` | Style | Text styling |

**Example** (from the builder tools legend UI):
```
HotkeyLabel #ToggleLegendKey {
    InputBindingKey: "ToggleBuilderToolsLegend";
}
```

---

## Button Elements

### Button

Basic icon-based clickable button.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Style` | StateStyle | State-based styling |
| `Icon` | String | Icon asset path |
| `Visible` | Boolean | Visibility state |

**Example:**
```
Button #CloseBtn {
    Anchor: (Width: 32, Height: 32);
    Style: (
        Default: (Background: (Color: #333333));
        Hovered: (Background: (Color: #444444));
    );
    Icon: "Common/UI/Icons/Close.png";
}
```

**Note:** Button click events must be registered server-side via `UIEventBuilder.addEventBinding()`. See [Java API](ui-api.md#uieventbuilder).

---

### TextButton

Button with text content. Requires state-based styling with `LabelStyle`.

| Property | Type | Description |
|----------|------|-------------|
| `Text` | String | Button text |
| `Anchor` | Anchor | Position and size |
| `Style` | StateStyle | State-based styling (requires `LabelStyle`) |
| `Visible` | Boolean | Visibility state |

**Example:**
```
TextButton #ActionButton {
    Anchor: (Width: 150, Height: 44);
    Style: (
        Default: (
            Background: (Color: #0f3460),
            LabelStyle: (FontSize: 18, TextColor: #ffffff, HorizontalAlignment: Center)
        ),
        Hovered: (
            Background: (Color: #1a5a90),
            LabelStyle: (FontSize: 18, TextColor: #ffffff, HorizontalAlignment: Center)
        )
    );
    Text: "Click Me";
}
```

**Important:** TextButton requires `LabelStyle` inside each state for text styling. Direct `Style` properties like `FontSize` will not work - they must be nested within `LabelStyle`.

---

### BackButton

Navigation back button with built-in styling.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Style` | StateStyle | State-based styling |
| `Visible` | Boolean | Visibility state |

**Example:**
```
BackButton #Back {
    Anchor: (Width: 100, Height: 40);
}
```

**Note:** `Common.ui` provides a `@BackButton` template (a positioned row containing a
`BackButton`). Instantiate it with `$C.@BackButton { ... }`.

---

### ActionButton

Button paired with a keybinding label, used for paged/legend controls.

| Property | Type | Description |
|----------|------|-------------|
| `KeyBindingLabel` | String | Key text shown on the button (e.g. `"J"`) |
| `Disabled` | Boolean | Disabled state |
| `Anchor` | Anchor | Position and size |

**Example** (from the builder tools legend UI):
```
ActionButton #PreviousPage {
    Disabled: true;
    KeyBindingLabel: "J";
}
```

---

## Input Elements

### TextField

Single-line text input field. In practice it is instantiated through the `Common.ui`
`@TextField` template, which supplies the background and placeholder styling; the
template parameter is `@Anchor`.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `PlaceholderText` | String / loc key | Placeholder text shown when empty |
| `Style` | Style | Input text styling |
| `PlaceholderStyle` | Style | Placeholder text styling |
| `Background` | Background | Field background (supplied by template) |

**Example** (template form, from the UI gallery):
```
$C = "../Common.ui";

$C.@TextField #TextField1 {
    @Anchor = (Width: 300, Right: 20);
    PlaceholderText: %server.customUI.inputs.textFieldPlaceholder;
}
```

**Note:** Use `CustomUIEventBindingType.ValueChanged` to receive input changes server-side.

---

### CompactTextField

Smaller text input that can collapse to an icon and expand on focus (used for search
boxes).

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `CollapsedWidth` | Number | Width when collapsed |
| `ExpandedWidth` | Number | Width when expanded |
| `PlaceholderText` | String / loc key | Placeholder text |
| `Style` | Style | Input text styling |
| `PlaceholderStyle` | Style | Placeholder text styling |
| `Decoration` | Object | Per-state icon / clear-button decoration |

**Example:**
```
CompactTextField #SearchInput {
    Anchor: (Height: 30, Width: 200);
    CollapsedWidth: 34;
    ExpandedWidth: 200;
    PlaceholderText: %server.customUI.searchPlaceholder;
    Style: (FontSize: 14);
    PlaceholderStyle: (TextColor: #3d5a85, RenderUppercase: true, FontSize: 12);
}
```

---

### MultilineTextField

Multi-line text input with its own scrollbar. Instantiated through the `@MultilineTextField`
template (parameter `@Anchor`).

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `PlaceholderText` | String / loc key | Placeholder text |
| `Style` | Style | Input text styling |
| `PlaceholderStyle` | Style | Placeholder text styling |
| `ScrollbarStyle` | ScrollbarStyle | Scrollbar styling (supplied by template) |

**Example:**
```
$C.@MultilineTextField #MultilineField {
    @Anchor = (Width: 400, Height: 80, Bottom: 8, Left: 0);
    PlaceholderText: %server.customUI.inputs.multilinePlaceholder;
}
```

---

### NumberField

Numeric input field. Instantiated through the `@NumberField` template (parameter
`@Anchor`).

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Value` | Number | Current numeric value |
| `Format` | Object | Numeric formatting, e.g. `(MaxDecimalPlaces: 3, Step: 0.1)` |
| `Style` | Style | Input text styling |

**Example:**
```
$C.@NumberField #NumberField1 {
    @Anchor = (Width: 150, Right: 20);
    Value: 10;
}
```

---

### CheckBox

Boolean toggle checkbox. The checked state property is `Value` (boolean). Instantiated
through the `@CheckBox` template, or `@CheckBoxWithLabel` for a checkbox with an adjacent
text label.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Value` | Boolean | Current checked state |
| `Style` | CheckBoxStyle | Checkbox styling (supplied by template) |

**`@CheckBox` example:**
```
$C.@CheckBox #CheckBox1 {
    Value: true;
}
```

**`@CheckBoxWithLabel` example** (parameters `@Text`, `@Checked`, `@LabelStyle`):
```
$C.@CheckBoxWithLabel #EnableFeature {
    @Text = %server.customUI.enableFeature;
    @Checked = true;
}
```

---

### Slider

Range slider control. Instantiated through the `@Slider` template (parameter `@Anchor`).
For fractional/float values use [`FloatSlider`](#floatslider).

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Style` | SliderStyle | Slider styling (supplied by template) |

**Example:**
```
$C.@Slider #VolumeSlider {
    @Anchor = (Width: 200);
}
```

---

### FloatSlider

Slider variant for floating-point values. Instantiated through the `@FloatSlider`
template (parameter `@Anchor`).

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Style` | SliderStyle | Slider styling (supplied by template) |

**Example:**
```
$C.@FloatSlider #OpacitySlider {
    @Anchor = (Width: 200);
}
```

---

### DropdownBox

Dropdown selection menu. Instantiated through the `@DropdownBox` template (parameter
`@Anchor`). Options are declared inline as `DropdownEntry` child elements; the current
selection is set with `Value`.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Value` | String | Value of the currently selected entry |
| `Style` | DropdownBoxStyle | Dropdown styling (supplied by template) |

**Example:**
```
$C.@DropdownBox #Dropdown1 {
    @Anchor = (Width: 250, Right: 20);
    Value: "Option_2";

    DropdownEntry {
        Value: "Option_1";
        Text: %server.customUI.option1;
    }
    DropdownEntry {
        Value: "Option_2";
        Text: %server.customUI.option2;
    }
}
```

**Note:** Options can also be populated/updated server-side via `UICommandBuilder`.

---

### DropdownEntry

A single selectable entry inside a `DropdownBox`.

| Property | Type | Description |
|----------|------|-------------|
| `Value` | String | Entry value (matched against the dropdown's `Value`) |
| `Text` | String / loc key | Display label |

---

### ColorPickerDropdownBox

A color swatch that opens a color-picker panel. Uses the `@DefaultColorPickerDropdownBoxStyle`
style from `Common.ui`.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Color` | Color | Current/selected color |
| `Style` | ColorPickerDropdownBoxStyle | Picker styling |

**Example:**
```
ColorPickerDropdownBox #ColorPicker1 {
    Anchor: (Width: 32, Height: 32, Right: 15);
    Style: $C.@DefaultColorPickerDropdownBoxStyle;
    Color: #ff5555;
}
```

---

## Display Elements

### Sprite

Image/sprite display.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Texture` | String | Texture asset path |
| `Color` | Color | Tint color |
| `Visible` | Boolean | Visibility state |

**Example:**
```
Sprite #Logo {
    Anchor: (Width: 128, Height: 128);
    Texture: "Common/UI/Images/Logo.png";
}
```

---

### AssetImage

Image display that resolves a texture by path, with a fallback when missing.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `TexturePath` | String | Texture/asset path to display |
| `FallbackTexturePath` | String | Texture shown when the asset is unavailable |
| `Visible` | Boolean | Visibility state |

**Example** (from the Memories UI):
```
AssetImage #Icon {
    Anchor: (Width: 128, Height: 128);
    FallbackTexturePath: "UI/Custom/Pages/Memories/MissingIcon.png";
}
```

---

### ItemSlot

Inventory item slot display. Renders the slot background, optional quality background, and
the item icon.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `ShowQuantity` | Boolean | Display the item count |
| `ShowQualityBackground` | Boolean | Show the rarity/quality background |

**Example** (from `DroppedItemSlot.ui`):
```
ItemSlot #ItemIcon {
    Anchor: (Full: 0, Height: 64, Width: 64);
    ShowQualityBackground: true;
    ShowQuantity: false;
}
```

**Note:** Use `CustomUIEventBindingType.SlotClicking` for slot click events.

---

### ProgressBar

Horizontal progress bar. Texture-driven (it uses fill/background/effect textures rather
than plain colors). Instantiated through the `@ProgressBar` template (parameter `@Anchor`),
which supplies the textures.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Value` | Number | Current value (0.0 to 1.0) |
| `Background` | Background | Track texture/background |
| `BarTexturePath` | String | Fill texture |
| `EffectTexturePath` | String | Optional effect overlay texture |
| `EffectWidth` / `EffectHeight` / `EffectOffset` | Number | Effect overlay sizing/offset |
| `Color` | Color | Tint color |
| `Style` | Style | Bar styling |

**Example** (template form):
```
$C.@ProgressBar #ProgressBar75 {
    @Anchor = (Bottom: 4, Left: 0);
    Value: 0.75;
}
```

---

### CircularProgressBar

Circular/radial progress indicator. Instantiated through the `@CircularProgressBar`
template (parameters `@Anchor`, `@Size`), which supplies the mask texture.

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Value` | Number | Current value (0.0 to 1.0) |
| `Background` | Color | Track/background color |
| `Color` | Color | Fill color |
| `MaskTexturePath` | String | Mask texture defining the ring shape |

**Example:**
```
$C.@CircularProgressBar #CircularProgress1 {
    @Anchor = (Right: 20);
    Value: 0.66;
    Color: #4a7caa;
}
```

Bare-element form (showing the underlying properties):
```
CircularProgressBar {
    Anchor: (Width: 48, Height: 48);
    Value: 0.66;
    Background: #1a2030;
    Color: #4a7caa;
}
```

---

## Navigation Elements

### TabNavigation

A tab bar plus the logic that switches the visible tab. Contains `TabButton` children and
uses a `TabNavigationStyle` (e.g. `$C.@TopTabsStyle` or `$C.@HeaderTabsStyle`).

| Property | Type | Description |
|----------|------|-------------|
| `Anchor` | Anchor | Position and size |
| `Style` | TabNavigationStyle | Tab styling |
| `SelectedTab` | String | `Id` of the initially selected tab |

### TabButton

A single tab within a `TabNavigation`.

| Property | Type | Description |
|----------|------|-------------|
| `Id` | String | Tab identifier (referenced by `SelectedTab`) |
| `Icon` | String | Tab icon texture path |
| `TooltipText` | String / loc key | Hover tooltip |

**Example** (from the UI gallery):
```
TabNavigation #TopTabs {
    Anchor: (Height: 66, Left: 2, Right: 0);
    Style: $C.@TopTabsStyle;
    SelectedTab: "Tab1";

    TabButton {
        Icon: "Common/RecipesIcon.png";
        TooltipText: %server.customUI.navigation.tabOne;
        Id: "Tab1";
    }
    TabButton {
        Icon: "Common/RecipesIcon.png";
        TooltipText: %server.customUI.navigation.tabTwo;
        Id: "Tab2";
    }
}
```

---

## Related Documentation

- [UI Overview](ui.md) - System architecture and quick start
- [Styling & Layout](ui-styling.md) - Anchor, padding, colors, state-based styling
- [Templates & Variables](ui-templates.md) - Imports, variables, localization
- [Java API](ui-api.md) - Server-side API reference
