# Item Respawner Example Plugin

Demonstrates a **stateful, editable placeable block** — the combination no other
example covers: a custom block, a custom **block-entity component**, a **ticking
system over the chunk store**, **spawning an item-entity**, **persisting** that
across reloads, and a **press-F settings GUI** that edits the block's state in
the world.

Place the pedestal and it drops an item (a crossbow by default) on top, then
**respawns it on an interval — but only when the previous one is gone**
(Quake-style item respawn). Press **F** on the pedestal to open a GUI and change
which item it spawns and how long the delay is.

This example wires together several ideas:

- a **block-item with a `BlockEntity`** (`Item_Respawner_Block.json`) — a visible
  pedestal (a marble pillar-base model) whose `BlockEntity` attaches the component,
- a **`Component<ChunkStore>`** (`ItemRespawner`) — per-block state, saved with the
  chunk via a `BuilderCodec`,
- a **`EntityTickingSystem<ChunkStore>`** (`ItemRespawnerSystem`) — runs every tick
  over each placed pedestal, the same base the engine's fluid ticker uses,
- **item-entity spawning** — `ItemComponent.generateItemDrop(...)` +
  `Store.addEntity(...)` to materialise an `ItemStack` as a world pickup,
- **cross-reload identity** — persisting the spawned item's UUID so the block
  re-finds it after a reload instead of duplicating it,
- a **press-F custom UI page** bound to the block — `InteractiveCustomUIPage`
  registered via `OpenCustomUIInteraction.registerBlockEntityCustomPage`, which
  reads the block's component, shows a form, and writes edits back.

## What you'll see

1. Obtain the **Item Respawner** (creative inventory → search "Item Respawner",
   or `/give <player> Item_Respawner_Block 1`) and place it — a marble pedestal.
2. A crossbow drops on top within a tick.
3. **Press F** on the pedestal → a settings GUI with an **item id** field and a
   **respawn delay** field. Change them and hit *Save Changes*.
4. Pick the item up — a replacement appears after the configured delay, **and not
   before**; the new settings apply on the next respawn.
5. Leave the world and return — the same single item is still there (no
   duplicate), and your edits persisted.

## How it works

| Piece | Role |
|-------|------|
| `Item_Respawner_Block.json` | Block-item definition. `BlockType.BlockEntity.Components.ItemRespawner` attaches the component to every placed instance; `Use → OpenCustomUI` opens the settings page on press-F. The visible model is a shipped marble pillar-base. |
| `ItemRespawner` | `Component<ChunkStore>` holding the config (`Item`, `IntervalSeconds`) and the spawned item's identity. A `BuilderCodec` persists it with the chunk. |
| `ItemRespawnerSystem` | `EntityTickingSystem<ChunkStore>`. Each tick, per placed pedestal: resolves the block's world position, checks whether its item still exists, and respawns it once the interval elapses. |
| `ItemRespawnerSettingsPage` | `InteractiveCustomUIPage` bound to the block. `build()` seeds the form from the component; `handleDataEvent()` writes edits back and calls `markNeedsSaving()`. |
| `ItemRespawnerSettingsData` | The codec-backed payload the Save button submits. |
| `ItemRespawnerPlugin` | Registers the component (binding the JSON key `"ItemRespawner"`), the system, and the settings page. |

The component is registered against `getChunkStoreRegistry()` (not the entity
store) because block-entity state lives on the `ChunkStore` and is saved with the
chunk. The spawned item, by contrast, is a normal entity in the `EntityStore`,
reached via `world.getEntityStore()`.

### The "only if not already present" rule

The system holds the live `Ref` of the item it spawned; `Ref.isValid()` is true
while the item exists and flips false the instant it's picked up or despawns. To
survive a world reload (where the transient `Ref` is lost but the dropped item
was saved), it also **persists the item's UUID** and re-acquires the `Ref` via
`EntityStore.getRefFromUUID(...)` on load — the same pattern the engine's own
mob/coop spawner blocks use. Without this, a reload would forget the existing
item and spawn a duplicate.

> **Note:** a freshly-spawned drop doesn't get its UUID until the engine processes
> it a tick or so later, so the UUID is captured lazily on a later tick (the live
> `Ref` covers the gap). This is why the component stores both a transient `Ref`
> and a persisted `UUID`.

### The press-F settings GUI

The block JSON wires its `Use` interaction to `OpenCustomUI` with page id
`"ItemRespawner"`. The plugin binds that id with
`OpenCustomUIInteraction.registerBlockEntityCustomPage(...)`: the supplier is
handed the targeted block-entity's `Ref`, reads its `BlockStateInfo` +
`ItemRespawner` components, and constructs the page bound to that specific block.
`build()` loads the `.ui` layout and seeds the fields; the Save button submits the
values, which the base decodes into an `ItemRespawnerSettingsData` and passes to
`handleDataEvent()`, where they're written to the component and persisted with
`BlockStateInfo.markNeedsSaving()`.

## Configuring it (defaults)

The two fields in the block JSON seed the component; both are then editable in
the GUI:

```json
"BlockEntity": {
  "Components": {
    "ItemRespawner": { "Item": "Weapon_Crossbow_Iron", "IntervalSeconds": 20 }
  }
}
```

- `Item` — the item id to spawn (any valid item id, case-sensitive).
- `IntervalSeconds` — delay before respawning once the item is gone.

## Building

```bash
./gradlew build     # portable
```

On Windows use `build.bat`.

## Installation

```bash
./deploy.sh     # Linux / bash
deploy.bat      # Windows
```

Or copy `build/libs/example-item-respawner.jar` to your Mods folder manually.

**Important:** `manifest.json` must have `"IncludesAssetPack": true` so the
bundled block JSON, language entries, and `.ui` page load.

## Code structure

- `ItemRespawnerPlugin.java` — registers the component, the ticking system, and the settings page
- `ItemRespawner.java` — the `Component<ChunkStore>` block-entity state + its persistence codec
- `ItemRespawnerSystem.java` — the `EntityTickingSystem<ChunkStore>` that spawns/respawns the item
- `ItemRespawnerSettingsPage.java` — the press-F `InteractiveCustomUIPage`
- `ItemRespawnerSettingsData.java` — the codec-backed form payload
- `Server/Item/Items/Tool/Item_Respawner_Block.json` — the pedestal block-item that carries the component
- `Server/Languages/en-US/server.lang` — display name, description, and GUI labels
- `Common/UI/Custom/Pages/ItemRespawnerSettingsPage.ui` — the settings form layout

## Related docs

- [`docs/blocks.md`](../../docs/blocks.md#custom-block-entity-components) — the verified custom block-entity component, item-spawning, and press-F GUI recipe
- [`docs/components.md`](../../docs/components.md) — ECS, `ChunkStore`, queries, and ticking systems
- [`docs/ui-api.md`](../../docs/ui-api.md) — `UICommandBuilder` / `UIEventBuilder` and custom UI pages
