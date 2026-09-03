---
title: "Assets API"
description: "Work with Hytale assets in Java — the central HytaleAssetStore, per-type AssetMap lookups, and a plugin-facing AssetRegistry for registering custom asset stores."
seo:
  type: TechArticle
---

# Assets API

**Doc type:** Java API · **Verified against 0.6.3**

The assets system loads, registers, and looks up data-driven game content (items, blocks, models, and custom plugin types) backed by JSON files and codec serialization.

## Overview

Implemented in `com.hypixel.hytale.server.core.asset` (with the registry in `...plugin.registry` and the map types in `com.hypixel.hytale.assetstore`) and provides:
- A central asset store (`HytaleAssetStore`) and per-type `AssetMap` lookups
- A plugin-facing `AssetRegistry` for registering custom asset stores during `setup()`
- JSON-backed asset definitions via `JsonAssetWithMap<K, M>` and `AssetBuilderCodec`
- Built-in asset type configs (item, blocktype, model, particle, gameplay)
- Prefab storage (`PrefabStore`) for entity prefabs
- Asset lifecycle events (pack register/unregister, load, file monitoring)

## Architecture
```
AssetRegistry (plugin entry: getAssetRegistry())
├── HytaleAssetStore (central server-side storage)
│   └── AssetStore<K, T, M>  (per-type stores)
│       └── AssetMap<K, T>
│           ├── DefaultAssetMap (recommended)
│           └── IndexedLookupTableAssetMap (indexed lookups)
├── JsonAssetWithMap<K, M> (AssetBuilderCodec-serialized definitions)
├── Built-in asset types (item / blocktype / model / particle / gameplay)
├── PrefabStore (entity prefabs)
└── Asset Events (AssetPackRegister/Unregister, LoadAsset, monitor events)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `AssetRegistry` | `server.core.plugin.registry` | Registers custom asset stores; obtained via `getAssetRegistry()` |
| `HytaleAssetStore` | `server.core.asset` | Central server-side asset storage |
| `AssetStore<K, T, M>` | `assetstore` | Base class for a per-type asset store |
| `AssetMap<K, T>` | `assetstore` | Lookup map for loaded assets (`getAsset(key)`) |
| `DefaultAssetMap<K, T>` | `assetstore.map` | Standard HashMap-backed map (recommended) |
| `IndexedLookupTableAssetMap<K, T>` | `assetstore.map` | Array-backed map for integer-indexed lookups |
| `JsonAsset<K>` | `assetstore` | Base interface for JSON-loaded assets; exposes `getId()` |
| `JsonAssetWithMap<K, M>` | `assetstore.map` | `JsonAsset` subinterface tying an asset type to its `AssetMap` — store-loaded assets implement this |
| `AssetBuilderCodec<K, T>` | `assetstore.codec` | `BuilderCodec` subclass for assets — binds the id and loader bookkeeping on top of the payload fields |
| `AssetRegistry` (static) | `assetstore` | Static store lookup (`getAssetStore(Class)`); a *different class* from the plugin-facing registry above, same name |
| `PrefabStore` | `server.core.prefab` | Stores and manages entity prefabs |
| `Model` | `server.core.asset.type.model.config` | 3D model configuration for entities, items, projectiles |
| `AssetPackRegisterEvent` | `server.core.asset` | Fired when an asset pack is registered |
| `LoadAssetEvent` | `server.core.asset` | Fired during the asset loading phase (priority-based) |
| `CommonAssetModule` | `server.core.asset.common` | Module managing binary common assets (`Common/…`) and streaming them to clients |
| `CommonAssetRegistry` | `server.core.asset.common` | Static name/hash lookup of registered common assets |
| `FileCommonAsset` | `server.core.asset.common.asset` | A common asset backed by a file on disk (lazy blob read) |
| `WordList` | `server.core.asset.type.wordlist` | Word-list asset; picks random translation keys (e.g. warp names) |
| `ColorParseUtil` | `server.core.asset.util` | Parse/format `#RRGGBB` / `rgb(...)` / `rgba(...)` color strings |

## AssetRegistry
**Package:** `com.hypixel.hytale.server.core.plugin.registry`

Register custom assets. Access via `getAssetRegistry()` in your plugin.

### Methods
```java
// Register an asset store
<K, T extends JsonAssetWithMap<K, M>, M extends AssetMap<K, T>, S extends AssetStore<K, T, M>>
AssetRegistry register(S store)

// Shutdown (called automatically)
void shutdown()
```

---

## Related Registries

From `PluginBase`, you also have access to codec registries:

```java
// Asset registry
AssetRegistry getAssetRegistry()

// String-keyed codec registry
<T, C extends Codec<? extends T>> CodecMapRegistry<T, C>
    getCodecRegistry(StringCodecMapCodec<T, C> codec)

// Asset-keyed codec registry
<K, T extends JsonAsset<K>> CodecMapRegistry.Assets<T, ?>
    getCodecRegistry(AssetCodecMapCodec<K, T> codec)

// Map-keyed codec registry
<V> MapKeyMapRegistry<V> getCodecRegistry(MapKeyMapCodec<V> codec)
```

---

## Asset Store
**Package:** `com.hypixel.hytale.server.core.asset`

`HytaleAssetStore` - Central asset storage for the server.

Assets are not retrieved directly from `HytaleAssetStore`. Each asset type's config class exposes a static `getAssetMap()`, and the returned `AssetMap` (`com.hypixel.hytale.assetstore.AssetMap`) provides the lookup:

```java
// Retrieval pattern: <ConfigClass>.getAssetMap().getAsset(key)
// AssetMap exposes:
T getAsset(K key)                    // returns null if the key is absent
T getAsset(String assetPack, K key)  // pack-scoped lookup
```

---

## Prefab Store
**Package:** `com.hypixel.hytale.server.core.prefab`

`PrefabStore` - Store and manage entity prefabs.

See [Prefabs Documentation](prefabs.md) for detailed usage.

---

## Asset Types
**Package:** `com.hypixel.hytale.server.core.asset.type`

Common asset type configurations:

| Subpackage | Description |
|------------|-------------|
| `item/` | Item definitions and properties |
| `blocktype/` | Block type configurations |
| `model/` | 3D model definitions |
| `particle/` | Particle effect configurations |
| `gameplay/` | Gameplay configuration assets |

> **See also:** [Codecs API](codecs.md#built-in-codecs)

---

## Model
**Package:** `com.hypixel.hytale.server.core.asset.type.model.config`

Represents a 3D model configuration for entities, items, and projectiles.

**Implements:** `NetworkSerializable<Model>`

### Constants
```java
static final String UNKNOWN_TEXTURE;  // Fallback texture ID
```

### Key Methods
```java
// Identity
String getModelAssetId()        // Asset ID reference
String getModel()               // Model file path
String getTexture()             // Texture file path

// Scale and transforms
float getScale()

// Bounding boxes
Box getBoundingBox()
Box getBoundingBox(MovementStates states)
Box getCrouchBoundingBox()

// Eye height
float getEyeHeight()
float getEyeHeight(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor)
float getCrouchOffset()

// Gradients (color variations)
String getGradientSet()
String getGradientId()

// Attachments (items, accessories)
ModelAttachment[] getAttachments()
Map<String, String> getRandomAttachmentIds()

// Animations
Map<String, ModelAsset.AnimationSet> getAnimationSetMap()
String getFirstBoundAnimationId(String... animationNames)
String getFirstBoundAnimationId(String set, String name)

// Visual effects
ColorLight getLight()           // Emissive lighting
ModelParticle[] getParticles()  // Particle effects
ModelTrail[] getTrails()        // Trail effects
CameraSettings getCamera()      // Camera configuration

// Physics
PhysicsValues getPhysicsValues()

// Detail boxes (hitboxes, selection boxes)
Map<String, DetailBox[]> getDetailBoxes()

// Phobia settings (accessibility)
Phobia getPhobia()
String getPhobiaModelAssetId()

// Network
Model toPacket()
Model.ModelReference toReference()
```

### Static Factory Methods
```java
// Create models from ModelAsset with different scaling
static Model createRandomScaleModel(ModelAsset asset)
static Model createStaticScaledModel(ModelAsset asset, float scale)
static Model createUnitScaleModel(ModelAsset asset)
static Model createUnitScaleModel(ModelAsset asset, Box boundingBox)
static Model createScaledModel(ModelAsset asset, float scale)
static Model createScaledModel(ModelAsset asset, float scale, Map<String, String> attachments)
static Model createScaledModel(ModelAsset asset, float scale, Map<String, String> attachments, Box boundingBox)
static Model createScaledModel(ModelAsset asset, float scale, Map<String, String> attachments, Box boundingBox, boolean flag)
```

### Usage Example
```java
// Get model from a projectile config
ProjectileConfig config = ProjectileConfig.getAssetMap().getAsset("arrow");
Model model = config.getModel();

// Access model properties
float scale = model.getScale();
Box bounds = model.getBoundingBox();
String texture = model.getTexture();

// Get particle effects
ModelParticle[] particles = model.getParticles();

// Check animations
Map<String, ModelAsset.AnimationSet> animations = model.getAnimationSetMap();
String idleAnim = model.getFirstBoundAnimationId("idle", "default");
```

> **See also:** [Projectiles API](projectiles.md#projectileconfig)

---

## JSON Asset Pattern

Assets in Hytale typically follow a JSON-based pattern with codec serialization. For a complete implementation guide, see [Creating Custom Asset Types](#creating-custom-asset-types).

An asset that lives in an asset store implements `JsonAssetWithMap<K, M>` — a `JsonAsset<K>`
subinterface that names the `AssetMap` type storing it — and exposes its key via `getId()`. Its
codec is an **`AssetBuilderCodec<K, T>`**: a `BuilderCodec` subclass whose `builder(...)` factory
additionally binds the asset id and a slot for the loader's `AssetExtraInfo.Data` bookkeeping.
Payload fields are then appended exactly like any other `BuilderCodec` — `.append(...).add()`
per field, plus a no-arg constructor for the blank instance
(see [Codecs API - BuilderCodec](codecs.md#buildercodec--codecs-for-objects)):

```java
public class MyAsset implements JsonAssetWithMap<String, DefaultAssetMap<String, MyAsset>> {
    private String id;                 // set by the loader (filename without extension)
    private AssetExtraInfo.Data data;  // loader bookkeeping — the codec needs somewhere to put it
    private String name;
    private int value;

    public static final AssetBuilderCodec<String, MyAsset> CODEC =
        AssetBuilderCodec.builder(MyAsset.class, MyAsset::new,
                Codec.STRING,                        // key codec
                (a, id) -> a.id = id, a -> a.id,     // id setter / getter
                (a, d) -> a.data = d, a -> a.data)   // AssetExtraInfo.Data setter / getter
            .append(new KeyedCodec<>("Name", Codec.STRING),
                    MyAsset::setName, MyAsset::getName)
            .add()
            .append(new KeyedCodec<>("Value", Codec.INTEGER),
                    MyAsset::setValue, MyAsset::getValue)
            .add()
            .build();

    // BuilderCodec needs a no-arg constructor to create the blank instance
    public MyAsset() {
    }

    @Override
    public String getId() {
        return id;
    }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getValue() { return value; }
    public void setValue(int value) { this.value = value; }
}
```

The seven-argument `builder(...)` signature is genuinely clunky: you must hand it an id
setter/getter pair and an `AssetExtraInfo.Data` setter/getter pair even though your own code never
touches either field — only the loader does, during decode. Every built-in asset class
(`TriggerEffectAsset`, `ReputationRank`, …) carries these same two fields; copy the shape.

---

## Asset Store Pattern

You do **not** subclass `AssetStore` — its only public constructor takes a `Builder`, and no
built-in plugin defines a store subclass. Instead, build a `HytaleAssetStore`
(`com.hypixel.hytale.server.core.asset.HytaleAssetStore`) with its static builder and register it
during `setup()`:

```java
getAssetRegistry().register(
    HytaleAssetStore.builder(MyAsset.class, new DefaultAssetMap<>())
        .setPath("MyAssets")             // loads Server/MyAssets/*.json
        .setCodec(MyAsset.CODEC)         // the AssetBuilderCodec
        .setKeyFunction(MyAsset::getId)
        .build());
```

The two-argument `builder(Class<T>, M)` overload is for `String`-keyed assets (the normal case); a
three-argument overload `builder(Class<K>, Class<T>, M)` exists for other key types. Beyond the
required `setPath` / `setCodec` / `setKeyFunction`, the builder offers `setExtension(String)`,
`loadsAfter(Class...)` / `loadsBefore(Class...)` (load-order dependencies between asset types),
`preLoadAssets(List<T>)` (code-defined assets), and `unmodifiable()`.

> **Note:** Most plugins should use `DefaultAssetMap` rather than creating a custom AssetMap implementation. See the complete guide below.

---

## Creating Custom Asset Types

This section provides a complete guide to creating custom JSON-populated asset types for your plugin.

### When to Create Custom Assets

Create a custom asset type when you need:
- Data-driven definitions loaded from JSON files
- Multiple instances of the same structure (e.g., spell definitions, item configs)
- Hot-reloadable content without code changes

For simple configuration, use `BuilderCodec` with `withConfig()` instead. See [Plugin Configuration](plugin-lifecycle.md#configuration).

### Asset File Structure

Plugin assets are placed in `src/main/resources/` and require manifest configuration.

**Folder Structure:**
```
src/main/resources/
├── manifest.json                    # Must include "IncludesAssetPack": true
├── Server/
│   └── Spells/                      # Your asset type folder
│       ├── Fireball.json
│       ├── IceBlast.json
│       └── Heal.json
└── Common/                          # For client-shared assets (UI, etc.)
    └── UI/
        └── Custom/
            └── MyPage.ui
```

**manifest.json Requirements:**
```json
{
  "Group": "MyPlugin",
  "Name": "SpellsPlugin",
  "Main": "com.example.SpellsPlugin",
  "IncludesAssetPack": true
}
```

The `"IncludesAssetPack": true` flag tells the server to scan your plugin's resources for asset files.

**Asset Discovery:**
- Server assets: `Server/[AssetType]/` folder
- Common assets: `Common/[AssetType]/` folder
- Asset keys default to the filename without extension (e.g., `Fireball.json` → key `"Fireball"`)

### AssetMap Implementations

`AssetMap` stores loaded assets for lookup. Most plugins should use the built-in implementation:

**`DefaultAssetMap<K, T>`** - Standard map-based storage (recommended):
```java
// Uses HashMap internally, suitable for most use cases
DefaultAssetMap<String, SpellDefinition>
```

**`IndexedLookupTableAssetMap<K, T>`** - Array-backed storage for O(1) indexed lookups:
```java
// Used internally by systems like Interaction that need index-based access
// Only use if you need integer-indexed lookups
IndexedLookupTableAssetMap<String, MyAsset>
```

**When to use each:**

| Use Case | AssetMap Type |
|----------|---------------|
| Most plugins | `DefaultAssetMap` |
| Need integer index lookups | `IndexedLookupTableAssetMap` |
| Custom lookup requirements | Extend `AssetMap` |

### Complete Working Example

Here's a full implementation of a custom "Spell" asset system:

**1. Define the Asset Class**

The class implements `JsonAssetWithMap<String, DefaultAssetMap<String, SpellDefinition>>` and
declares an `AssetBuilderCodec`. It also caches its own store lookup in a static `getAssetMap()`
helper — the exact shape the built-in `WordList` asset uses — so callers have one obvious
retrieval point:

```java
package com.example.spells;

import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.assetstore.AssetStore;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;

public class SpellDefinition
        implements JsonAssetWithMap<String, DefaultAssetMap<String, SpellDefinition>> {

    private String id;                 // set by the loader (filename without extension)
    private AssetExtraInfo.Data data;  // loader bookkeeping — required by the codec
    private String name;
    private int manaCost;
    private float cooldown;
    // Field initializers supply the defaults; a missing "Effect" key keeps "none"
    private String effect = "none";

    public static final AssetBuilderCodec<String, SpellDefinition> CODEC =
        AssetBuilderCodec.builder(SpellDefinition.class, SpellDefinition::new,
                Codec.STRING,                                     // key codec
                (a, id) -> a.id = id, a -> a.id,                  // id setter / getter
                (a, d) -> a.data = d, a -> a.data)                // AssetExtraInfo.Data setter / getter
            .append(new KeyedCodec<>("Name", Codec.STRING),
                    SpellDefinition::setName, SpellDefinition::getName)
            .add()
            .append(new KeyedCodec<>("ManaCost", Codec.INTEGER),
                    SpellDefinition::setManaCost, SpellDefinition::getManaCost)
            .add()
            .append(new KeyedCodec<>("Cooldown", Codec.FLOAT),
                    SpellDefinition::setCooldown, SpellDefinition::getCooldown)
            .add()
            .append(new KeyedCodec<>("Effect", Codec.STRING),
                    SpellDefinition::setEffect, SpellDefinition::getEffect)
            .add()
            .build();

    // Cached store handle — resolved lazily because the store only exists
    // once the owning plugin's setup() has registered it (see step 3).
    private static AssetStore<String, SpellDefinition, DefaultAssetMap<String, SpellDefinition>> store;

    public static DefaultAssetMap<String, SpellDefinition> getAssetMap() {
        if (store == null) {
            store = AssetRegistry.getAssetStore(SpellDefinition.class);
        }
        return store.getAssetMap();
    }

    // BuilderCodec needs a no-arg constructor for the blank instance
    public SpellDefinition() {
    }

    // JsonAsset requires getId(); the loader sets the id from the filename
    @Override
    public String getId() { return id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getManaCost() { return manaCost; }
    public void setManaCost(int manaCost) { this.manaCost = manaCost; }
    public float getCooldown() { return cooldown; }
    public void setCooldown(float cooldown) { this.cooldown = cooldown; }
    public String getEffect() { return effect; }
    public void setEffect(String effect) { this.effect = effect; }
}
```

> **Naming gotcha:** the `AssetRegistry` imported here for retrieval is the **static**
> `com.hypixel.hytale.assetstore.AssetRegistry`. It is a *different class* from the plugin-facing
> `com.hypixel.hytale.server.core.plugin.registry.AssetRegistry` you get from `getAssetRegistry()`
> in step 3. They share a name and nothing else — mixing up the imports is an easy mistake.

**2. Create JSON Asset Files**

`src/main/resources/Server/Spells/Fireball.json`:
```json
{
  "Name": "Fireball",
  "ManaCost": 25,
  "Cooldown": 3.0,
  "Effect": "fire_burst"
}
```

`src/main/resources/Server/Spells/Heal.json`:
```json
{
  "Name": "Healing Light",
  "ManaCost": 15,
  "Cooldown": 5.0,
  "Effect": "regeneration"
}
```

**3. Register in Plugin Setup**

There is no store subclass to write — build a `HytaleAssetStore` with its builder and hand it to
the plugin's asset registry:

```java
package com.example.spells;

import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.server.core.asset.HytaleAssetStore;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;

public class SpellsPlugin extends JavaPlugin {

    public SpellsPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        // Build and register the asset store.
        // Assets are then loaded from Server/Spells/*.json automatically.
        getAssetRegistry().register(
            HytaleAssetStore.builder(SpellDefinition.class, new DefaultAssetMap<>())
                .setPath("Spells")
                .setCodec(SpellDefinition.CODEC)
                .setKeyFunction(SpellDefinition::getId)
                .build());
    }
}
```

**4. Access Assets at Runtime**

Retrieval goes through the store's `AssetMap`. With the `getAssetMap()` helper from step 1:

```java
// In a command or event handler; spellName came from user input,
// playerRef is the PlayerRef of the caster (see the Commands docs)
SpellDefinition spell = SpellDefinition.getAssetMap().getAsset(spellName);

if (spell == null) {
    playerRef.sendMessage(Message.raw("Unknown spell: " + spellName));
    return;
}

// A SpellDefinition is plain data — mana pools, cooldown tracking, and the
// actual effect are your plugin's job; the asset only supplies the numbers.
playerRef.sendMessage(Message.raw("Casting " + spell.getName()
        + " (" + spell.getManaCost() + " mana, "
        + spell.getCooldown() + "s cooldown)"));
```

Without the helper, the raw lookup is
`AssetRegistry.getAssetStore(SpellDefinition.class).getAssetMap().getAsset(key)` (the static
`assetstore.AssetRegistry`). Either way, the lookup only works after the registering plugin's
`setup()` has run — the registry is one global class-keyed map, not scoped per plugin.

### Adding Polymorphic Types

If your asset system needs multiple subtypes (e.g., different spell categories with different fields),
use type dispatch with a `StringCodecMapCodec`. `StringCodecMapCodec` is **abstract**, so you declare a
small concrete subclass for your family rather than instantiating it directly. Each subtype is a plain
class with a `BuilderCodec`, registered by id during `setup()`. See
[Codecs API - Codec Map Types](codecs.md#codec-map-types-polymorphic--lookup-codecs).

```java
// Base interface
public interface SpellEffect {
    void apply(Player caster, Entity target);

    // Concrete dispatcher: documents are dispatched on their "Type" key
    final class TypeCodec extends StringCodecMapCodec<SpellEffect, Codec<? extends SpellEffect>> {
        TypeCodec() { super("Type"); }
    }

    TypeCodec TYPE_CODEC = new TypeCodec();
}

// Damage effect implementation
public class DamageSpellEffect implements SpellEffect {
    private int damage;

    public static final BuilderCodec<DamageSpellEffect> CODEC =
        BuilderCodec.builder(DamageSpellEffect.class, DamageSpellEffect::new)
            .append(new KeyedCodec<>("Damage", Codec.INTEGER),
                    DamageSpellEffect::setDamage, DamageSpellEffect::getDamage)
            .add()
            .build();

    public DamageSpellEffect() {
    }

    public int getDamage() { return damage; }
    public void setDamage(int damage) { this.damage = damage; }

    @Override
    public void apply(Player caster, Entity target) {
        target.damage(damage);
    }
}

// Register in setup() — register(...) takes the id, the concrete class, and the codec
@Override
protected void setup() {
    CodecMapRegistry<SpellEffect, Codec<? extends SpellEffect>> registry =
        getCodecRegistry(SpellEffect.TYPE_CODEC);

    registry.register("Damage", DamageSpellEffect.class, DamageSpellEffect.CODEC);
    registry.register("Heal", HealSpellEffect.class, HealSpellEffect.CODEC);
}
```

JSON with type dispatch:
```json
{
  "Type": "Damage",
  "Damage": 50
}
```

> **See also:** [Codecs API - Polymorphic Type Dispatch](codecs.md#codec-map-types-polymorphic--lookup-codecs)

---

## Usage Examples

### Register Custom Assets
```java
@Override
protected void setup() {
    // Build and register the store for your asset type
    getAssetRegistry().register(
        HytaleAssetStore.builder(MyAsset.class, new DefaultAssetMap<>())
            .setPath("MyAssets")
            .setCodec(MyAsset.CODEC)
            .setKeyFunction(MyAsset::getId)
            .build());
}
```

### Access Registered Assets
```java
// Look up the registered store — static com.hypixel.hytale.assetstore.AssetRegistry
AssetStore<String, MyAsset, DefaultAssetMap<String, MyAsset>> store =
    AssetRegistry.getAssetStore(MyAsset.class);

// Get an asset by key — null if absent
MyAsset asset = store.getAssetMap().getAsset("my_asset_id");

if (asset != null) {
    // Use asset
}
```

### Using Codec Registries
```java
@Override
protected void setup() {
    // SomeBase.TYPE_CODEC is a StringCodecMapCodec<SomeBase, Codec<? extends SomeBase>>
    CodecMapRegistry<SomeBase, Codec<? extends SomeBase>> registry =
        getCodecRegistry(SomeBase.TYPE_CODEC);

    // register(id, concrete class, codec) — documents with this id decode with MyType.CODEC
    registry.register("MyType", MyType.class, MyType.CODEC);
}
```

---

## Built-in Asset Access

Built-in Hytale assets are retrieved through each asset type's static `getAssetMap()`, then `getAsset(key)`:

```java
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;

// Get a block type by key
BlockType stone = BlockType.getAssetMap().getAsset("stone");

// Get an item definition by key (the item config class is named Item)
Item sword = Item.getAssetMap().getAsset("sword");
```

`getAsset(key)` returns `null` if the key is absent. A pack-scoped overload `getAsset(String assetPack, K key)` is also available.

---

## Common Assets (Java API)

**Package:** `com.hypixel.hytale.server.core.asset.common`

*Common assets* are the **binary** files under a pack's `Common/` tree (textures, models, sounds, `.ui` files, …) — as opposed to the JSON assets above. Each is a `CommonAsset` identified by its **name** (path relative to `Common/`, e.g. `UI/Custom/MyHud.ui`) and a **SHA-256 hash** (64-char hex, `CommonAsset.HASH_LENGTH`); the server sends them to clients by hash. Packs' `Common/` trees are indexed automatically at load, so most plugins never touch this API — reach for it to look up, hot-add, or re-send a binary asset at runtime.

### CommonAssetModule

The `JavaPlugin` module that owns common-asset loading, file monitoring, and client streaming. Obtain it with `CommonAssetModule.get()`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `get()` | `CommonAssetModule` | Static module singleton |
| `addCommonAsset(String pack, T asset)` | `void` | Register (or hot-reload) a `CommonAsset` under a pack name; broadcasts the change to connected clients and shows a reload notification |
| `addCommonAsset(String pack, T asset, boolean log)` | `void` | Same, optionally without the log line |
| `getRequiredAssets()` | `Asset[]` | Packet forms of every registered asset (what a joining client is told about) |
| `sendAssetsToPlayer(PacketHandler, Asset[], boolean forceRebuild)` | `void` | Stream specific assets (by hash) to one client; `null` array = all assets |
| `sendAsset(CommonAsset, boolean forceRebuild)` | `void` | Broadcast one asset to all clients |
| `sendAssets(List<CommonAsset>, boolean forceRebuild)` | `void` | Broadcast several assets |

### CommonAssetRegistry

Static lookup of everything `CommonAssetModule` has registered. All methods are `static`.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getByName(String name)` | `CommonAsset` | The active asset for a `Common/`-relative name (`null` if absent) |
| `getByHash(String hash)` | `CommonAsset` | Look up by SHA-256 hex hash |
| `hasCommonAsset(String name)` | `boolean` | Whether a name is registered |
| `hasCommonAsset(AssetPack pack, String name)` | `boolean` | Whether a specific pack supplies the name |
| `getCommonAssetsStartingWith(String pack, String prefix)` | `List<CommonAsset>` | Prefix scan (e.g. everything under `UI/Custom/`) |
| `getDuplicateAssetCount()` | `int` | How many names are supplied by more than one pack |
| `getDuplicatedAssets()` | `Map<String, List<PackAsset>>` | The colliding entries (`PackAsset` = pack name + asset) |

When two packs supply the same name, the **last registration wins** as the active asset — the same last-load-wins rule as [JSON asset overrides](#overriding-base-game-assets).

### FileCommonAsset

**Package:** `com.hypixel.hytale.server.core.asset.common.asset`

The standard `CommonAsset` implementation: backed by a file on disk, whose bytes are read lazily (and asynchronously) when a client actually needs the blob.

```java
public class FileCommonAsset extends CommonAsset {
    public FileCommonAsset(Path file, String name, byte[] bytes);              // hash computed from bytes
    public FileCommonAsset(Path file, String name, String hash, byte[] bytes); // known hash (bytes may be null)
    public Path getFile();
}
```

```java
import com.hypixel.hytale.server.core.asset.common.CommonAssetModule;
import com.hypixel.hytale.server.core.asset.common.asset.FileCommonAsset;

// Hot-add a binary asset at runtime and push it to connected clients
byte[] bytes = Files.readAllBytes(path);
CommonAssetModule.get().addCommonAsset("MyPack",
    new FileCommonAsset(path, "UI/Custom/MyHud.ui", bytes));
```

The inherited `CommonAsset` surface: `getName()`, `getHash()`, `getBlob()` (a `CompletableFuture<byte[]>`), `toPacket()`, and the static `CommonAsset.hash(byte[])` (SHA-256 hex, same as [`HashUtil.sha256`](codecs.md#hashutil)).

---

## WordList

**Package:** `com.hypixel.hytale.server.core.asset.type.wordlist`

A small JSON asset type holding an array of **translation keys** (resolved through the `wordlists` translation file), used to pick random display names — e.g. a teleporter's `WarpNameWordList` picks default warp names. It is a `JsonAssetWithMap<String, DefaultAssetMap<…>>` like other JSON assets.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetMap()` | `DefaultAssetMap<String, WordList>` | Static asset map |
| `getWordList(String id)` | `WordList` | Static shortcut; returns an empty word list for an unknown id |
| `getId()` | `String` | Asset id |
| `pickTranslationKey(Random, Set<String> usedTranslated, String language)` | `String` | Random key whose *translated* text (lower-cased, in `language`) is not in the used set; `null` if exhausted |
| `pickDefaultLanguage(Random, Set<String> usedTranslated)` | `String` | Convenience: picks against `en-US` and returns the translated text itself |

---

## Asset Utility Classes

### ColorParseUtil

**Package:** `com.hypixel.hytale.server.core.asset.util`

Static parsing/formatting between color strings and the protocol `Color` / `ColorAlpha` types. This is what backs [`ProtocolCodecs.COLOR`](codecs.md#protocolcodecs) and the color fields you see across JSON assets. The most useful members:

```java
// parse (null on failure)
public static Color parseColor(String value);           // "#RGB", "#RRGGBB", "rgb(R,G,B)"
public static ColorAlpha parseColorAlpha(String value);  // adds "#RRGGBBAA" / "rgba(R,G,B,A)"
public static Color hexStringToColor(String hex);
public static Color rgbStringToColor(String rgb);
public static int hexStringToRGBInt(String hex);
public static int hexAlphaStringToRGBAInt(String hex);

// format
public static String colorToHexString(Color color);           // "#RRGGBB"
public static String colorToHexAlphaString(ColorAlpha color); // "#RRGGBBAA"
public static int colorToARGBInt(Color color);
public static Color argbIntToColor(int argb);                 // inverse of colorToARGBInt (0.6.3+)

// image analysis (0.6.3+): dominant color of an image file as a "#RRGGBB" string
public static String computeDominantColor(Path imageFile) throws Exception;

// pre-compiled patterns
public static final Pattern HEX_COLOR_PATTERN;
public static final Pattern HEX_ALPHA_COLOR_PATTERN;
public static final Pattern RGB_COLOR_PATTERN;
public static final Pattern RGBA_COLOR_PATTERN;
```

The `read*` variants (`readColor(RawJsonReader)`, `readColorAlpha(...)`, …) are the same conversions for use inside a codec's `decodeJson`.

### TempAssetIdUtil

**Package:** `com.hypixel.hytale.server.core.util`

> **Deprecated (`forRemoval = true`)** — a temporary holder of well-known asset id constants; don't build new code on it.

String constants for a handful of hard-wired ids (`SOIL_GRASS`, `SOUND_EVENT_ITEM_BREAK`, `SOUND_EVENT_PLAYER_PICKUP_ITEM`, `PARTICLE_SPLASH`, `DEFAULT_PLAYER_MODEL_NAME`, …) plus `getSoundEventIndex(String)`, which resolves a sound-event id to its index but **falls back to `0` with a warning** for unknown ids — prefer the explicit resolve-and-guard pattern in [Audio → Resolving a sound-event index](audio.md#resolving-a-sound-event-index).

---

## Asset Loading

Assets are loaded during server startup:
1. Built-in assets are loaded first
2. Plugin assets are loaded during plugin `setup()` phase
3. Assets can be accessed after all plugins are set up

---

## Overriding Base-Game Assets

A plugin or pack can **replace a base-game asset** by shipping a resource at the **same id** as a
vanilla one. Asset keys are the filename without extension, and ids resolve globally rather than by
folder (see [Pack Structure](02-structure.md#pack-structure)), so a file at
`src/main/resources/Server/Item/Items/Weapon/Sword/Weapon_Sword_Wood.json` registers under the key
`Weapon_Sword_Wood` and takes the place of the vanilla sword of that id.

**This is a whole-asset replace, not a merge with the vanilla file.** Your file *becomes* that id and
then resolves its own `Parent` from scratch. Any field you omit falls back to the **`Parent`** (e.g.
`Template_Weapon_Sword`), **not** to the vanilla file's value. So if the vanilla asset set its own
deltas over the template (`Model` / `Texture` / `Icon` / `Quality` / `ItemLevel`, …), you must
re-copy those into your override or they revert to the template's defaults. This is the opposite of
`Parent` inheritance, which *is* a deep merge — see
[Codecs API → Parent Inheritance](codecs.md#parent-inheritance-inheritcodec).

### Load order and precedence

Precedence is **last-load-wins**, and base-game assets load before mods:

- Built-in assets load first; the server then loads packs from the Mods directory
  (`AssetModule.loadPacksFromDirectory`). Each load `put`s into the asset map, overwriting any
  existing key — so a pack's same-id asset wins over the base-game one. The replace is **silent**
  (no duplicate-id warning is logged).
- **Order *among* multiple packs is not a documented guarantee.** The loader iterates the Mods
  directory with an *unsorted* `DirectoryStream` (filesystem order), so do **not** rely on one pack
  overriding *another pack's* id — only the base-game-vs-pack precedence is dependable.

---

## Notes
- Assets are typically JSON-based configurations
- Register custom assets during plugin `setup()`
- Asset loading happens through codec serialization
- Use the appropriate codec type for your asset structure
- Assets persist across server restarts (stored in data files)
- Explore specific asset type packages for detailed APIs
- For a complete guide on creating custom assets, see [Creating Custom Asset Types](#creating-custom-asset-types)
- For polymorphic assets with type dispatch, see [Codecs API - Polymorphic Type Dispatch](codecs.md#codec-map-types-polymorphic--lookup-codecs)

---

## Asset Events

Events related to asset pack lifecycle, loading, and file monitoring.

### Event Summary

| Class | Package | Key Type | Description |
|-------|---------|----------|-------------|
| `AssetPackRegisterEvent` | `...core.asset` | `Void` | Asset pack registered |
| `AssetPackUnregisterEvent` | `...core.asset` | `Void` | Asset pack unregistered |
| `LoadAssetEvent` | `...core.asset` | `Void` | Assets loaded (has priority constants) |
| `CommonAssetMonitorEvent` | `...core.asset.common.events` | `Void` | Common asset file monitoring |
| `SendCommonAssetsEvent` | `...core.asset.common.events` | `Void` | Async - sending assets to client |
| `PathEvent` | `...core.asset.monitor` | N/A | File path change monitoring |

---

### AssetPackRegisterEvent

**Package:** `com.hypixel.hytale.server.core.asset`

Fired when an asset pack is registered with the server.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetPack()` | `AssetPack` | The registered asset pack |

---

### AssetPackUnregisterEvent

**Package:** `com.hypixel.hytale.server.core.asset`

Fired when an asset pack is unregistered from the server.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getAssetPack()` | `AssetPack` | The unregistered asset pack |

---

### LoadAssetEvent

**Package:** `com.hypixel.hytale.server.core.asset`

Fired during asset loading phase. Supports priority-based loading order.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getBootStart()` | `long` | Boot start timestamp |
| `isShouldShutdown()` | `boolean` | Whether shutdown was requested |
| `getReasons()` | `List<String>` | Failure reasons |
| `failed(boolean, String)` | `void` | Mark asset loading as failed |

**Priority Constants:**

| Constant | Description |
|----------|-------------|
| `PRIORITY_LOAD_COMMON` | Load common assets first |
| `PRIORITY_LOAD_REGISTRY` | Load registry assets |
| `PRIORITY_LOAD_LATE` | Load late-stage assets |

---

### CommonAssetMonitorEvent

**Package:** `com.hypixel.hytale.server.core.asset.common.events`

Extends `AssetMonitorEvent<Void>`. Fired when common asset files are changed. Constructor takes lists of created, modified, deleted, and moved paths.

---

### SendCommonAssetsEvent

**Package:** `com.hypixel.hytale.server.core.asset.common.events`

Async event fired when sending assets to clients.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getPacketHandler()` | `PacketHandler` | Network handler |
| `getRequestedAssets()` | `Asset[]` | Assets being sent |

---

### PathEvent

**Package:** `com.hypixel.hytale.server.core.asset.monitor`

Represents a file path change event for asset monitoring.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `getEventKind()` | `EventKind` | Type of path event |
| `getTimestamp()` | `long` | Event timestamp |

---

### Asset Events Registration Example

```java
import com.hypixel.hytale.server.core.asset.*;

@Override
protected void setup() {
    // Listen for asset pack registration
    getEventRegistry().register(AssetPackRegisterEvent.class, event -> {
        System.out.println("Asset pack registered: " + event.getAssetPack());
    });

    // Listen for asset loading with priority
    getEventRegistry().register(LoadAssetEvent.PRIORITY_LOAD_LATE,
        LoadAssetEvent.class, event -> {
        if (event.isShouldShutdown()) {
            System.out.println("Asset loading aborted: " + event.getReasons());
        }
    });
}
```

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the asset system (verified against `HytaleServer.jar`).

- **`assetPackSubPath cannot be null when assetPackMode is enabled`** → asset-pack mode was turned on without a sub-path for the pack's files. Fix: supply the pack sub-path, or leave asset-pack mode disabled.
- **Symptom:** your plugin's JSON files under `Server/[Type]/` are never loaded → the manifest is missing the asset-pack flag. Fix: add `"IncludesAssetPack": true` to `manifest.json` so the server scans your resources (see [Creating Custom Asset Types](#creating-custom-asset-types)).
- **Symptom:** an asset id with the wrong case resolves loosely server-side but renders as a `?` placeholder on the client → asset/item ids are **case-sensitive on the client**. Fix: use the exact asset-file casing (e.g. `Plant_Fruit_Apple`, not `plant_fruit_apple`).
- **Symptom:** an asset pack warns or fails to load after a game update → the manifest's `ServerVersion` range no longer admits the running server. As of Update 5 `AssetModule` validates packs through the same path as plugins — `PluginManifest.getServerVersion()` is a **`SemverRange`** checked by `checkServerVersionCompatibility(...)`, *not* a `String.equals` against the exact build. Fix: pin a range that covers the target (`^0.5.0`), so you don't have to re-pin every patch (see [docs/02-structure.md → ServerVersion](02-structure.md#serverversion-target-server-version)).
- **Symptom:** an asset is found under an unexpected key → asset keys default to the **filename without extension** (`Fireball.json` → key `"Fireball"`). Fix: name the file to match the key you intend to look up.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
