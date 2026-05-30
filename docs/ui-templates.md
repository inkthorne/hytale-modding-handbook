---
title: "UI Templates, Variables & Localization"
description: "Advanced Hytale .ui DSL — file imports for libraries like Common.ui, instantiating named templates, variables for shared constants, the spread operator, and localization."
seo:
  type: TechArticle
---

# UI Templates, Variables & Localization

**Doc type:** UI DSL · **Assets:** `Common/UI` · **Verified against 0.5.3**

Advanced DSL features for reusable UI components and localization.

---

## Quick Navigation

| Topic | Description |
|-------|-------------|
| [File Imports](#file-imports) | Import external .ui files |
| [Template Instantiation](#template-instantiation) | Instantiate named templates from imports |
| [Variables](#variables) | Define and use variables |
| [Spread Operator](#spread-operator) | Compose styles and properties |
| [Localization](#localization) | Translatable text strings |
| [Element References](#element-references) | Reference elements by ID |
| [Patterns](#patterns--best-practices) | Reusable component patterns |

**Related:** [Elements](ui-elements.md) | [Styling](ui-styling.md) | [Java API](ui-api.md) | [UI Overview](ui.md)

---

## Overview

Advanced `.ui` DSL features (assets under `Common/UI`) for reuse and localization:
- File imports (`$Var = "path/to/file.ui";`) to pull in libraries like `Common.ui`
- Instantiating named templates from imports (`$File.@Template`)
- Variables (`@Name = value;`) for shared constants
- The spread operator (`...`) to compose styles and properties
- Localization of translatable text strings
- Element references by ID

## Architecture
```
Import          $Var = "path/to/file.ui";
└── Member access   $File.@Name
      ├── Template instantiation : $File.@Template #Id { @Param = ...; }
      └── Value/style read       : $File.@SomeValue

Variables   @Name = value;   (referenced as @Name)
Spread      ( ...@BaseStyle, Override: value )   (compose styles/props)
Localization + element references (by #Id)
```

## Key Classes

These are DSL constructs (not Java classes); the table lists the key features documented on this page.

| Construct | Syntax | Description |
|-----------|--------|-------------|
| File import | `$Var = "file.ui";` | Import an external `.ui` file into a variable |
| Member access | `$File.@Name` | Read a value/style or instantiate a template from an import |
| Template instantiation | `$File.@Template #Id { ... }` | Use a named template as an element type |
| Variable | `@Name = value;` | Define a reusable value |
| Spread operator | `( ...@Base, Override: v )` | Compose styles/properties |
| Element reference | `#Id` | Reference an element by ID |

---

## File Imports

Import an external `.ui` file into a variable, then access the named templates and
values it defines via member access (`$File.@Member`). This is how the built-in
`Common.ui` library is reused across nearly every page.

### Syntax

```
$VarName = "path/to/file.ui";
```

### Path Resolution

Paths are relative to the current `.ui` file location:

```
$Common = "../Common.ui";              // Parent directory
$C = "../../../Common.ui";             // Several levels up
$Sounds = "Sounds.ui";                 // Same directory
$CV = "../CodeViewer.ui";              // Sibling file
```

> An imported file is **not** itself an element. You do not write
> `$VarName #Id { ... }`. Instead you reach into it with `.@Name` to instantiate a
> named template or read a value defined inside that file.

### Accessing Members of an Import

A file like `Common.ui` defines many named members with `@Name = ...`. After import,
reference them with `$File.@Name`:

```
$C = "../Common.ui";

// Read a value/style defined in Common.ui
Style: (...$C.@DefaultLabelStyle, RenderBold: true);
TextColor: $C.@ColorGrayCaption;
Style: $C.@DefaultColorPickerDropdownBoxStyle;
```

---

## Template Instantiation

Importing a file gives you access to its **named element templates**. A template is a
file member whose value is an element block, for example in `Common.ui`:

```
@TextButton = TextButton {
    @Anchor = Anchor();
    @Text = "";
    Style: ( ...@DefaultTextButtonStyle );
    Anchor: (...@Anchor, Height: @DefaultButtonHeight);
    Text: @Text;
};
```

### Syntax

Instantiate a template by writing `$File.@Template` as if it were an element type,
optionally giving the instance an ID and a body:

```
$C.@TemplateName #InstanceId {
    @PropName = value;   // override a template parameter
    Property: value;     // set/override a normal element property
}
```

The `@PropName = value;` form (no `:`) overrides a **template parameter** — one of the
`@Var = ...` declarations at the top of the template's body (such as `@Anchor`, `@Text`,
`@Title`, `@Checked`). The `Property: value;` form sets a normal element property the
same way as on any element.

### Example

**Pages/MyPage.ui:**
```
$C = "../Common.ui";

$C.@PageOverlay {
    $C.@DecoratedContainer {
        $C.@Title {
            @Text = %server.customUI.myPage.title;
        }

        $C.@TextButton #SaveButton {
            @Anchor = (Width: 220);
            @Text = %server.customUI.myPage.save;
        }

        $C.@CheckBoxWithLabel #EnableOption {
            @Text = %server.customUI.myPage.enable;
            @Checked = true;
        }
    }
}
```

### Common Templates in `Common.ui`

These are real templates available via `$C.@Name` after `$C = "../Common.ui";`:

| Template | Purpose |
|----------|---------|
| `@TextButton` / `@SecondaryTextButton` / `@TertiaryTextButton` | Styled text buttons (parameters: `@Anchor`, `@Text`, `@Sounds`) |
| `@Button` / `@SecondaryButton` / `@CancelButton` | Styled icon buttons |
| `@Title` / `@Subtitle` | Title and subtitle labels (parameter: `@Text`, `@Alignment`) |
| `@CheckBox` / `@CheckBoxWithLabel` | Checkbox (parameters: `@Checked`, `@Text`, `@LabelStyle`) |
| `@TextField` / `@NumberField` / `@MultilineTextField` | Input fields (parameter: `@Anchor`) |
| `@DropdownBox` | Dropdown (parameter: `@Anchor`) |
| `@Slider` / `@FloatSlider` | Sliders (parameter: `@Anchor`) |
| `@ProgressBar` / `@CircularProgressBar` | Progress indicators (parameters: `@Anchor`, `@Size`) |
| `@Container` / `@DecoratedContainer` / `@SimpleContainer` | Panels with `#Title`/`#Content` slots |
| `@PageOverlay` | Dimmed full-screen overlay backdrop |
| `@BackButton` / `@DefaultSpinner` | Back button row, animated spinner |

### Filling Template Slots

Some container templates (such as `@Container` and `@DecoratedContainer`) define named
inner regions like `#Title` and `#Content`. Target them by ID inside the instance body
to inject children:

```
$C.@Container {
    Anchor: (Width: 400, Height: 110);

    #Title {
        $C.@Title { @Text = %server.customUI.myPage.title; }
    }

    #Content {
        Label {
            Text: %server.customUI.myPage.body;
            Style: (FontSize: 13, TextColor: $C.@ColorDefaultLabel, Wrap: true);
        }
    }
}
```

---

## Variables

Define reusable values for consistency across your UI.

### Syntax

```
@VarName = value;
```

### Variable Types

**Numeric:**
```
@ButtonHeight = 44;
@PanelWidth = 400;
@Padding = 20;
```

**Color:**
```
@PrimaryColor = #3498db;
@DangerColor = #e74c3c;
@TextColor = #ffffff;
@BackgroundAlpha = 0.95;
```

**Style Objects:**
```
@TitleStyle = (FontSize: 28, TextColor: #ffffff, RenderBold: true);
@SubtitleStyle = (FontSize: 16, TextColor: #aaaaaa, HorizontalAlignment: Center);
```

**Background Objects:**
```
@PanelBackground = (Color: #1a1a2e(0.95));
@ButtonBackground = (TexturePath: "Common/UI/Shared/Button.png", Border: 10);
```

**Complete State Styles:**
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
```

### Typed Constructors

Many variables are not bare values but **typed constructors** — the value is the name of
a style/data type followed by its arguments in parentheses. This is the dominant form for
styling values in `Common.ui`. Examples taken from real files:

```
@DefaultLabelStyle = (FontSize: 16, TextColor: #96a9be);          // anonymous object

@SubtitleStyle = LabelStyle(FontSize: 15, RenderUppercase: true, TextColor: #96a9be);
@InputBoxBackground = PatchStyle(TexturePath: "Common/InputBox.png", Border: 16);
@DefaultTextButtonStyle = TextButtonStyle(
    Default: (Background: @DefaultButtonDefaultBackground, LabelStyle: @DefaultButtonLabelStyle),
    Hovered: (Background: @DefaultButtonHoveredBackground, LabelStyle: @DefaultButtonLabelStyle)
);
@DefaultDropdownBoxStyle = DropdownBoxStyle( /* ... */ );
@ContentPadding = Padding(Full: 17, Top: 8);
@TopTabAnchor = Anchor(Width: 82, Height: 62, Right: 5, Bottom: -14);
```

Common constructor types seen in `Common.ui` include `LabelStyle`, `PatchStyle`,
`ButtonStyle`, `TextButtonStyle`, `DropdownBoxStyle`, `SliderStyle`, `ScrollbarStyle`,
`CheckBoxStyle`, `ColorPickerStyle`, `TabStyleState`, `TabNavigationStyle`,
`TextTooltipStyle`, `Anchor`, and `Padding`. An anonymous `(...)` object (no type name)
is also valid where the type can be inferred from the property it is assigned to.

### Using Variables

Reference variables with `@` prefix:

```
@ButtonHeight = 44;
@PrimaryColor = #3498db;
@TitleStyle = (FontSize: 24, TextColor: #ffffff);

Group #Panel {
    Anchor: (Width: 400, Height: 300);
    Padding: (Full: @Padding);
    Background: (Color: @PrimaryColor);

    Label #Title {
        Style: @TitleStyle;
        Text: "Hello";
    }

    TextButton #Submit {
        Anchor: (Width: 150, Height: @ButtonHeight);
        Style: @PrimaryButtonStyle;
        Text: "Submit";
    }
}
```

### Variable Scope

Variables defined at the top of a `.ui` file are available throughout that file:

```
// Variables defined here are file-scoped
@HeaderHeight = 60;
@FooterHeight = 40;
@ContentPadding = 20;

Group {
    LayoutMode: Top;

    Group #Header {
        Anchor: (Height: @HeaderHeight);
    }

    Group #Content {
        FlexWeight: 1;
        Padding: (Full: @ContentPadding);
    }

    Group #Footer {
        Anchor: (Height: @FooterHeight);
    }
}
```

---

## Spread Operator

Spread properties from a variable into an element.

### Syntax

```
...@VariableName            // spread a local variable
...$File.@VariableName      // spread a member of an imported file
```

The cross-file form `...$File.@Var` is common — it spreads a style or property object
defined in an imported file (e.g. `Common.ui` or `Sounds.ui`) into the current object:

```
$C = "../Common.ui";

Style: (
    ...$C.@DefaultTextButtonStyle,
    Sounds: ( ...$Sounds.@ButtonsLight )
);
```

### Example

```
@CommonPanelProps = (
    Padding: (Full: 20),
    Background: (Color: #1a1a2e(0.95)),
    LayoutMode: Top
);

Group #Panel1 {
    Anchor: (Width: 300, Height: 200);
    ...@CommonPanelProps   // Spreads Padding, Background, LayoutMode
}

Group #Panel2 {
    Anchor: (Width: 400, Height: 300);
    ...@CommonPanelProps   // Same properties applied
}
```

### Composing Styles

Combine multiple variable spreads:

```
@BaseStyle = (FontSize: 16, TextColor: #ffffff);
@CenteredStyle = (HorizontalAlignment: Center);
@BoldStyle = (RenderBold: true);

Label #CenteredTitle {
    Style: (
        ...@BaseStyle,
        ...@CenteredStyle,
        ...@BoldStyle,
        FontSize: 24  // Override specific property
    );
    Text: "Title";
}
```

---

## Localization

Use localization keys for translatable text.

### Syntax

```
Text: %namespace.key;
```

### Example

```
Label #WelcomeMessage {
    Style: (FontSize: 18, TextColor: #ffffff);
    Text: %server.customUI.welcomeMessage;
}

Label #ButtonLabel {
    Text: %server.customUI.submitButton;
}
```

### Server-Side Registration

Localization keys are registered server-side. See [Internationalization](i18n.md) for details.

```java
// In your plugin setup
LocalizationManager localization = server.getLocalizationManager();
localization.register("server.customUI.welcomeMessage", "Welcome to the server!");
localization.register("server.customUI.submitButton", "Submit");
```

### Dynamic Text with Placeholders

For dynamic content, use server-side string formatting:

```java
UICommandBuilder cmd = new UICommandBuilder();
cmd.set("#playerName.Text", "Welcome, " + playerName + "!");
```

### Best Practices

1. Use descriptive namespace paths: `server.customUI.pageName.elementPurpose`
2. Keep keys consistent across your plugin
3. Provide fallback text in the registration

---

## Element References

Reference elements by their ID for event binding and dynamic updates.

### Syntax

```
#ElementId
```

### Element Targeting Syntax

The full targeting syntax is `#ElementId.Property` where:
- `#ElementId` — The element's ID (defined in .ui file as `Element #MyId { ... }`)
- `.Property` — The property path to set

**Common property patterns:**

| Target | Syntax | Example |
|--------|--------|---------|
| Text content | `#Id.Text` | `cmd.set("#Label.Text", "Hello")` |
| Visibility | `#Id.Visible` | `cmd.set("#Panel.Visible", false)` |
| Numeric value | `#Id.Value` | `cmd.set("#Progress.Value", 0.5f)` |
| Style property | `#Id.Style.Property` | `cmd.set("#Label.Style.TextColor", "#FF0000")` |
| Nested property | `#Id.Parent.Child` | `cmd.set("#Button.Style.Default.Background.Color", "#3498db")` |

### In Event Bindings

```java
// Server-side event registration (element ID only, no # prefix)
eventBuilder.addEventBinding(CustomUIEventBindingType.Activating, "MyButton");
eventBuilder.addEventBinding(CustomUIEventBindingType.ValueChanged, "SearchInput");
```

> **Note:** Event bindings use element IDs **without** the `#` prefix.

### In UICommandBuilder

```java
UICommandBuilder cmd = new UICommandBuilder();

// Set text properties
cmd.set("#PlayerName.Text", playerName);
cmd.set("#Score.Text", String.valueOf(score));

// Set visibility
cmd.set("#WarningIcon.Visible", true);
cmd.set("#LoadingPanel.Visible", false);

// Set numeric values
cmd.set("#HealthBar.Value", 0.85f);
cmd.set("#ExperienceBar.Value", currentXp / maxXp);

// Set boolean properties
cmd.set("#Checkbox.Checked", true);

// Append to specific element
cmd.append("#Container", "Components/ListItem.ui");

// Append inline DSL
cmd.appendInline("#List", "Label { Text: \"New Item\"; }");

// Insert before element
cmd.insertBefore("#Footer", "Components/Divider.ui");

// Clear element contents (removes children)
cmd.clear("#ItemList");

// Remove element entirely
cmd.remove("#OldElement");
```

### In .ui Files

Elements with IDs can be targeted for dynamic updates:

```
Group #StatusPanel {
    Label #StatusText {
        Style: (FontSize: 14, TextColor: #ffffff);
        Text: "Loading...";  // Will be updated server-side
    }

    ProgressBar #LoadingBar {
        Anchor: (Width: 200, Height: 10);
        Value: 0;  // Will be updated server-side
    }

    Group #IconContainer {
        // Container for dynamically added icons
    }
}
```

```java
// Update text and progress
cmd.set("#StatusText.Text", "Connected!");
cmd.set("#LoadingBar.Value", 1.0f);

// Add icon to container
cmd.append("#IconContainer", "Components/StatusIcon.ui");

// Clear and rebuild list
cmd.clear("#IconContainer");
cmd.append("#IconContainer", "Components/NewIcon.ui");
```

### ID Requirements

1. **Root element cannot have an ID** — The outermost `Group` must be anonymous
2. **IDs must be unique** — Within a single UI hierarchy
3. **Case-sensitive** — `#myButton` and `#MyButton` are different elements

```
// Correct: Anonymous root, named children
Group {
    Group #Panel {
        Label #Title { Text: "Hello"; }
    }
}

// Wrong: Root cannot have ID
Group #Root {  // This will fail!
    // ...
}
```

---

## Patterns & Best Practices

### Reusable Component Files

Create a library of reusable components:

**Components/Buttons.ui:**
```
@PrimaryStyle = (
    Default: (Background: (Color: #3498db), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)),
    Hovered: (Background: (Color: #5dade2), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center))
);

@SecondaryStyle = (
    Default: (Background: (Color: #95a5a6), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)),
    Hovered: (Background: (Color: #bdc3c7), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center))
);

@DangerStyle = (
    Default: (Background: (Color: #e74c3c), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center)),
    Hovered: (Background: (Color: #ec7063), LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center))
);
```

### Theme Variables

Create a theme file for consistent styling:

**Theme.ui:**
```
// Colors
@ColorPrimary = #3498db;
@ColorSecondary = #2ecc71;
@ColorDanger = #e74c3c;
@ColorWarning = #f39c12;
@ColorBackground = #1a1a2e;
@ColorText = #ffffff;
@ColorTextMuted = #aaaaaa;

// Typography
@FontSizeSmall = 12;
@FontSizeMedium = 16;
@FontSizeLarge = 24;
@FontSizeTitle = 32;

// Spacing
@SpacingSmall = 8;
@SpacingMedium = 16;
@SpacingLarge = 24;

// Common Styles
@TextStyle = (FontSize: @FontSizeMedium, TextColor: @ColorText);
@MutedTextStyle = (FontSize: @FontSizeSmall, TextColor: @ColorTextMuted);
@TitleStyle = (FontSize: @FontSizeTitle, TextColor: @ColorText, RenderBold: true);
```

**Using the theme:**

Members defined in another file are accessed with the `$File.@Name` form, not bare `@Name`:

```
$Theme = "../Theme.ui";

Group {
    Background: (Color: $Theme.@ColorBackground(0.95));
    Padding: (Full: $Theme.@SpacingLarge);

    Label #Title {
        Style: $Theme.@TitleStyle;
        Text: "Settings";
    }

    Label #Description {
        Style: $Theme.@MutedTextStyle;
        Text: "Configure your preferences";
    }
}
```

### Common Mistakes

**Wrong: Using direct style on TextButton**
```
// This won't work!
TextButton {
    Style: (FontSize: 16, TextColor: #ffffff);  // WRONG
    Text: "Click";
}
```

**Right: Using state-based style with LabelStyle**
```
TextButton {
    Style: (
        Default: (LabelStyle: (FontSize: 16, TextColor: #ffffff, HorizontalAlignment: Center))
    );
    Text: "Click";
}
```

**Wrong: Adding ID to root Group**
```
// This won't work!
Group #RootPanel {  // WRONG - root cannot have ID
    // content
}
```

**Right: Anonymous root, named children**
```
Group {  // No ID on root
    Group #Panel {  // ID on children is fine
        // content
    }
}
```

**Wrong: Event handlers in .ui files**
```
// This syntax is NOT supported!
Button #MyButton {
    OnActivating: (SendData: "clicked");  // WRONG
}
```

**Right: Register events server-side**
```java
// In your CustomUIPage build method
eventBuilder.addEventBinding(CustomUIEventBindingType.Activating, "MyButton");
```

---

## Gotchas & Errors

- **Symptom:** a `%namespace.key` displays as the literal key text on the client → the key was never registered server-side. Fix: register it (see [Server-Side Registration](#server-side-registration) and [Internationalization](i18n.md)), and provide fallback text.
- **Symptom:** an event binding or `cmd.set("#Id…")` targets an element that "exists" but never updates → element IDs are **case-sensitive**, so `#myButton` and `#MyButton` are different elements. Fix: match the exact casing used in the `.ui` file (see [ID Requirements](#id-requirements)).
- **Symptom:** `addEventBinding`/`cmd.set` silently does nothing for an ID you copied from a binding call → command/targeting selectors need the leading `#` (`cmd.set("#MyButton.Text", …)`), but event-binding IDs are passed **without** `#` (`addEventBinding(…, "MyButton")`). Fix: use `#` only in targeting selectors, not in `addEventBinding` IDs.

---

## Related Documentation

- [UI Overview](ui.md) - System architecture and quick start
- [Elements](ui-elements.md) - All element types
- [Styling](ui-styling.md) - Layout and visual styling
- [Java API](ui-api.md) - Server-side API reference
- [Internationalization](i18n.md) - Localization system
