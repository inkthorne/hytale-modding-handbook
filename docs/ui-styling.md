# UI Styling & Layout

**Doc type:** UI DSL · **Assets:** `Common/UI`

Complete reference for positioning, layout, and visual styling in Hytale's UI DSL.

---

## Quick Navigation

| Topic | Description |
|-------|-------------|
| [Anchor System](#anchor-system) | Element positioning and sizing |
| [LayoutMode](#layoutmode) | Child element arrangement |
| [Padding](#padding) | Internal spacing |
| [Backgrounds](#backgrounds) | Colors, textures, 9-slice patches |
| [Style Properties](#style-properties) | Font, color, alignment |
| [State-Based Styling](#state-based-styling) | Interactive element states |

**Related:** [Elements](ui-elements.md) | [Templates & Variables](ui-templates.md) | [Java API](ui-api.md) | [UI Overview](ui.md)

---

## Overview

Defined in `.ui` DSL files under `Common/UI`, this page covers the properties that position, lay out, and style elements:
- `Anchor` — element positioning and sizing
- `LayoutMode` — arrangement of child elements
- `Padding` — internal spacing
- `Background` — colors, textures, and 9-slice patches
- `Style` — font, color, and alignment
- State-based styling for interactive element states

## Architecture
```
Element
├── Anchor      (Width/Height/Top/Bottom/Left/Right/Min/Max, Full key)
├── LayoutMode  (child arrangement; Full, Top, CenterMiddle, etc.)
├── Padding     (internal spacing)
├── Background  (Color / texture / 9-slice patch)
└── Style       (FontSize, TextColor, alignment)
      └── State-based styling (Default, Hovered, Pressed, …)
```

## Key Classes

These are DSL styling properties (not Java classes); the table lists the key properties documented on this page.

| Property | Applies to | Description |
|----------|-----------|-------------|
| `Anchor` | Any element | Positioning and sizing within the parent |
| `LayoutMode` | Containers | How child elements are arranged |
| `Padding` | Containers | Internal spacing around content |
| `Background` | Any element | Background color, texture, or 9-slice patch |
| `Style` | Text/controls | Font, color, and alignment settings |
| State blocks | Interactive elements | Per-state styling (e.g. `Default`, `Hovered`) |

---

## Anchor System

The `Anchor` property controls element positioning and sizing within its parent.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `Width` | Number | Fixed width in pixels |
| `Height` | Number | Fixed height in pixels |
| `Top` | Number | Distance from parent's top edge |
| `Bottom` | Number | Distance from parent's bottom edge |
| `Left` | Number | Distance from parent's left edge |
| `Right` | Number | Distance from parent's right edge |
| `MinWidth` | Number | Minimum width constraint |
| `MaxWidth` | Number | Maximum width constraint |

### Filling the Parent

There is no standalone `Anchor: Full;` preset. To make an element fill its parent, use
one of these real forms:

- Set `LayoutMode: Full;` on the element, **or**
- Use `Full` as an **Anchor key** inside the parentheses: `Anchor: (Full: 0);` (the value
  is an inset; `Full: 0` means flush to all edges).

```
Anchor: (Full: 0);              // fill parent, no inset
Anchor: (Full: 0, Width: 64, Height: 64);   // centered fixed box
LayoutMode: Full;               // fill via layout mode
```

### Examples

**Fixed Size:**
```
Anchor: (Width: 300, Height: 100);
```

**Fixed Size with Offset:**
```
Anchor: (Width: 300, Height: 100, Top: 20);
```

**Fill Parent:**
```
Anchor: (Full: 0);
```

**Position from Edges:**
```
Anchor: (Left: 10, Right: 10, Top: 20, Bottom: 20);
```

**Using Variables:**
```
@ButtonHeight = 44;
Anchor: (Width: 150, Height: @ButtonHeight);
```

---

## LayoutMode

The `LayoutMode` property controls how child elements are arranged within a container.

### Values

| Value | Description |
|-------|-------------|
| `Top` | Stack children from top downward |
| `Left` | Stack children from left to right |
| `Middle` | Vertically center children |
| `Center` | Horizontally center children |
| `Bottom` | Stack children from bottom upward |
| `Right` | Stack children from right to left |
| `Full` | Fill entire parent area |
| `CenterMiddle` | Center both horizontally and vertically |
| `MiddleCenter` | Center both horizontally and vertically (alternate) |
| `TopScrolling` | Top layout with vertical scrolling |
| `LeftCenterWrap` | Left-aligned with center wrapping |

**Note:** `Top` and `Left` are the most commonly used values for stacking layouts.

### Examples

**Vertical Stack:**
```
Group #VerticalContainer {
    LayoutMode: Top;

    Label { Text: "First"; }
    Label { Text: "Second"; }
    Label { Text: "Third"; }
}
```

**Horizontal Stack:**
```
Group #HorizontalContainer {
    LayoutMode: Left;

    Button #Btn1 { Anchor: (Width: 50, Height: 50); }
    Button #Btn2 { Anchor: (Width: 50, Height: 50); }
}
```

**Centered Content:**
```
Group {
    LayoutMode: CenterMiddle;
    Anchor: (Full: 0);

    Group #CenteredPanel {
        Anchor: (Width: 400, Height: 300);
    }
}
```

### FlexWeight

Use `FlexWeight` for proportional sizing within a layout:

```
Group #Container {
    LayoutMode: Left;

    Group #Sidebar {
        FlexWeight: 1;  // Takes 1/4 of space
    }
    Group #Content {
        FlexWeight: 3;  // Takes 3/4 of space
    }
}
```

---

## Padding

The `Padding` property controls internal spacing between an element's bounds and its children.

### Formats

| Format | Description |
|--------|-------------|
| `Full` | Equal padding on all sides |
| `Horizontal` | Left and right padding |
| `Vertical` | Top and bottom padding |
| `Top`, `Bottom`, `Left`, `Right` | Individual sides |

### Examples

**Equal Padding:**
```
Padding: (Full: 20);
```

**Horizontal and Vertical:**
```
Padding: (Horizontal: 20, Vertical: 10);
```

**Individual Sides:**
```
Padding: (Top: 10, Bottom: 10, Left: 20, Right: 20);
```

**Combined:**
```
Padding: (Full: 10, Left: 20);  // 10 all sides, but 20 on left
```

---

## Backgrounds

The `Background` property supports multiple formats for colors, images, and 9-slice patches.

### Color Format

Colors use hex format with optional alpha:
- `#RRGGBB` - Solid color
- `#RRGGBB(alpha)` - Color with alpha (0.0 to 1.0)

**Examples:**
```
Background: #333333;              // Solid dark gray
Background: #000000(0.5);         // Semi-transparent black
Background: (Color: #1a1a2e(0.95));  // Object format with alpha
```

### Texture Background

Simple texture path:
```
Background: "Common/UI/Shared/Panel.png";
```

### Object Format

Explicit color object:
```
Background: (Color: #000000(0.7));
```

### 9-Slice Patches (PatchStyle)

For scalable UI elements like buttons and panels. A patch is authored either as a bare
`(TexturePath: ..., Border: ...)` object on `Background`, or explicitly with the
`PatchStyle(...)` constructor (common in `Common.ui`).

**Uniform Border** (single value applied to all four edges — the most common form):
```
Background: (TexturePath: "Common/ContainerPatch.png", Border: 23);
```

**Axis Borders** (separate horizontal and vertical insets):
```
Background: (
    TexturePath: "Common/ContainerHeaderNoRunes.png",
    HorizontalBorder: 35,
    VerticalBorder: 0
);
```

**Explicit `PatchStyle` constructor** (as used for button backgrounds in `Common.ui`):
```
@DefaultButtonDefaultBackground = PatchStyle(
    TexturePath: "Common/Buttons/Primary.png",
    VerticalBorder: 12,
    HorizontalBorder: 80
);
```

> Only `Border` (uniform), `VerticalBorder`, and `HorizontalBorder` exist. There are no
> per-side `BorderTop` / `BorderBottom` / `BorderLeft` / `BorderRight` keys.

**Note:** 9-slice patches allow textures to scale without distorting corners or edges.

---

## Style Properties

The `Style` property controls text and visual appearance for Label and other text elements.

### Font Properties

| Property | Type | Description |
|----------|------|-------------|
| `FontSize` | Number | Text size in pixels |
| `FontName` | String | Font family name |
| `RenderBold` | Boolean | Bold text rendering |
| `RenderUppercase` | Boolean | Uppercase text transform |
| `LetterSpacing` | Number | Space between characters |

### Color Properties

| Property | Type | Description |
|----------|------|-------------|
| `TextColor` | Color | Text color |
| `OutlineColor` | Color | Text outline color |

### Alignment Properties

| Property | Values | Description |
|----------|--------|-------------|
| `HorizontalAlignment` | `Start`, `Center`, `End` | Horizontal text alignment |
| `VerticalAlignment` | `Start`, `Center`, `End` | Vertical text alignment |

### Text Properties

| Property | Type | Description |
|----------|------|-------------|
| `Wrap` | Boolean | Enable text wrapping |
| `ShrinkTextToFit` | Boolean | Shrink font size to fit available space |
| `MinShrinkTextToFitFontSize` | Number | Lower bound when `ShrinkTextToFit` is on |

### Other Element-Level Styling Properties

These appear directly on elements (not inside the font `Style` object) in real `.ui`
files and are useful when authoring:

| Property | Applies To | Description |
|----------|-----------|-------------|
| `MaskTexturePath` | Label, CircularProgressBar, etc. | Texture used to mask/gradient the element's render |
| `PlaceholderStyle` | TextField, NumberField, MultilineTextField, CompactTextField | Style for placeholder text |
| `TooltipText` | TabButton and other interactive elements | Hover tooltip text (string or loc key) |
| `Sounds` | Inside an interactive `Style` block | Sound triggers (`Activate`, `MouseHover`) — see [Sound States](#sound-states) |

### Example

```
Label #Title {
    Style: (
        FontSize: 28,
        TextColor: #e94560,
        HorizontalAlignment: Center,
        RenderBold: true,
        LetterSpacing: 2
    );
    Text: "Welcome";
}
```

### Using Style Variables

Define reusable styles with variables:

```
@TitleStyle = (FontSize: 28, TextColor: #ffffff, RenderBold: true);
@SubtitleStyle = (FontSize: 16, TextColor: #aaaaaa);

Label #Title {
    Style: @TitleStyle;
    Text: "Main Title";
}

Label #Subtitle {
    Style: @SubtitleStyle;
    Text: "Subtitle text";
}
```

---

## State-Based Styling

Interactive elements like buttons can have different styles for different interaction states.

### Available Visual States

These keys appear inside a `Style: (...)` block to define per-state appearance:

| State | Description |
|-------|-------------|
| `Default` | Normal/idle state |
| `Hovered` | Mouse hovering over element |
| `Pressed` | Element being clicked/pressed |
| `Disabled` | Element is disabled |

### Sound States

Interactive styles can also carry a nested `Sounds: (...)` block. Its keys are **not** the
visual states above — they are sound-event triggers:

| Sound Key | Triggered When |
|-----------|----------------|
| `Activate` | The element is activated/clicked |
| `MouseHover` | The pointer moves over the element |

```
Style: (
    Default: (Background: "Common/Buttons/Primary.png"),
    Hovered: (Background: "Common/Buttons/Primary_Hovered.png"),
    Sounds: (
        Activate: (SoundPath: "Sounds/ButtonsLightActivate.ogg", Volume: 4),
        MouseHover: (SoundPath: "Sounds/ButtonsLightHover.ogg", Volume: 6)
    )
);
```

In `Common.ui`, button styles pull these in from `Sounds.ui`, e.g.
`Sounds: $Sounds.@ButtonsLight`.

### Button Syntax

For `Button` elements:

```
Button #MyButton {
    Anchor: (Width: 100, Height: 40);
    Style: (
        Default: (Background: #333333);
        Hovered: (Background: #444444);
        Pressed: (Background: #222222);
        Disabled: (Background: #111111);
    );
}
```

### TextButton Syntax

**Important:** `TextButton` requires `LabelStyle` nested inside each state for text styling:

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
        ),
        Pressed: (
            Background: (Color: #0a2040),
            LabelStyle: (FontSize: 18, TextColor: #cccccc, HorizontalAlignment: Center)
        ),
        Disabled: (
            Background: (Color: #333333),
            LabelStyle: (FontSize: 18, TextColor: #666666, HorizontalAlignment: Center)
        )
    );
    Text: "Click Me";
}
```

### Styling Differences

| Element Type | Style Format |
|--------------|--------------|
| `Label` | Direct style: `Style: (FontSize: 24, TextColor: #ffffff)` |
| `Button` | State-based: `Style: (Default: (Background: ...), Hovered: (...))` |
| `TextButton` | State-based with LabelStyle: `Style: (Default: (LabelStyle: (...)))` |

### Reusable Button Styles

Define button styles as variables:

```
@PrimaryButtonStyle = (
    Default: (
        Background: (Color: #3498db),
        LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)
    ),
    Hovered: (
        Background: (Color: #5dade2),
        LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)
    )
);

@DangerButtonStyle = (
    Default: (
        Background: (Color: #e74c3c),
        LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)
    ),
    Hovered: (
        Background: (Color: #ec7063),
        LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)
    )
);

TextButton #SaveButton {
    Style: @PrimaryButtonStyle;
    Text: "Save";
}

TextButton #DeleteButton {
    Style: @DangerButtonStyle;
    Text: "Delete";
}
```

---

## Complete Example

A panel demonstrating various styling concepts:

```
@PanelBackground = (Color: #1a1a2e(0.95));
@TitleStyle = (FontSize: 28, TextColor: #e94560, HorizontalAlignment: Center, RenderBold: true);
@TextStyle = (FontSize: 16, TextColor: #aaaaaa, HorizontalAlignment: Center);

Group {
    LayoutMode: CenterMiddle;
    Anchor: (Full: 0);
    Background: (Color: #000000(0.7));

    Group #MainPanel {
        Anchor: (Width: 400, Height: 300);
        Background: @PanelBackground;
        Padding: (Full: 20);
        LayoutMode: Top;

        Label #Title {
            Style: @TitleStyle;
            Text: "Settings";
        }

        Label #Description {
            Anchor: (Top: 10);
            Style: @TextStyle;
            Text: "Configure your preferences";
        }

        Group #ButtonRow {
            Anchor: (Height: 50, Top: 20);
            LayoutMode: Center;

            TextButton #SaveButton {
                Anchor: (Width: 120, Height: 40);
                Style: (
                    Default: (
                        Background: (Color: #27ae60),
                        LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)
                    ),
                    Hovered: (
                        Background: (Color: #2ecc71),
                        LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)
                    )
                );
                Text: "Save";
            }
        }
    }
}
```

---

## Related Documentation

- [UI Overview](ui.md) - System architecture and quick start
- [Elements](ui-elements.md) - All element types
- [Templates & Variables](ui-templates.md) - Imports, variables, localization
- [Java API](ui-api.md) - Server-side API reference
