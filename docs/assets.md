# Assets API

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

> **See also:** [Codecs API](codecs.md#builtin-codecs)

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

A `JsonAsset<K>` exposes its key via `getId()`. The codec is a `BuilderCodec` built with the
`BuilderCodec.builder(...)` factory: it needs a no-arg constructor (the blank-instance supplier)
and a setter/getter pair for each field. See [Codecs API - BuilderCodec](codecs.md#buildercodec--codecs-for-objects).

```java
public class MyAsset implements JsonAsset<String> {
    private String id;
    private String name;
    private int value;

    // Codec for serialization — built field-by-field with BuilderCodec
    public static final BuilderCodec<MyAsset> CODEC =
        BuilderCodec.builder(MyAsset.class, MyAsset::new)
            .append(new KeyedCodec<>("Id", Codec.STRING),
                    MyAsset::setId, MyAsset::getId)
            .add()
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

    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getValue() { return value; }
    public void setValue(int value) { this.value = value; }
}
```

---

## Asset Store Pattern

Create a custom asset store:

```java
public class MyAssetStore extends AssetStore<String, MyAsset, DefaultAssetMap<String, MyAsset>> {
    public MyAssetStore() {
        super(MyAsset.class, DefaultAssetMap.class, MyAsset.CODEC);
    }
}
```

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

```java
package com.example.spells;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.assetstore.JsonAsset;

public class SpellDefinition implements JsonAsset<String> {
    private String id;
    private String name;
    private int manaCost;
    private float cooldown;
    // Field initializers supply the defaults; a missing "Effect" key keeps "none"
    private String effect = "none";

    public static final BuilderCodec<SpellDefinition> CODEC =
        BuilderCodec.builder(SpellDefinition.class, SpellDefinition::new)
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

    // BuilderCodec needs a no-arg constructor for the blank instance
    public SpellDefinition() {
    }

    // JsonAsset requires getId(); the loader sets it from the filename
    @Override
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

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

**2. Define the Asset Store**

```java
package com.example.spells;

import com.hypixel.hytale.server.core.asset.AssetStore;
import com.hypixel.hytale.server.core.asset.DefaultAssetMap;

public class SpellStore extends AssetStore<String, SpellDefinition, DefaultAssetMap<String, SpellDefinition>> {

    // Singleton for easy access
    private static SpellStore instance;

    public SpellStore() {
        super(SpellDefinition.class, DefaultAssetMap.class, SpellDefinition.CODEC);
        instance = this;
    }

    public static SpellStore getInstance() {
        return instance;
    }

    // AssetStore provides:
    // - get(String key) - retrieve by key
    // - getAssetMap() - access underlying map
    // - contains(String key) - check existence
}
```

**3. Create JSON Asset Files**

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

**4. Register in Plugin Setup**

```java
package com.example.spells;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;

public class SpellsPlugin extends JavaPlugin {

    @Override
    protected void setup() {
        // Create and register the asset store
        SpellStore spellStore = new SpellStore();
        getAssetRegistry().register(spellStore);

        // Assets are automatically loaded from Server/Spells/*.json
    }
}
```

**5. Access Assets at Runtime**

```java
// In a command or event handler
public void castSpell(Player player, String spellName) {
    SpellDefinition spell = SpellStore.getInstance().get(spellName);

    if (spell == null) {
        player.sendMessage("Unknown spell: " + spellName);
        return;
    }

    if (player.getMana() < spell.getManaCost()) {
        player.sendMessage("Not enough mana! Need " + spell.getManaCost());
        return;
    }

    // Cast the spell
    player.consumeMana(spell.getManaCost());
    player.sendMessage("Casting " + spell.getName() + "!");

    // Apply cooldown
    player.applyCooldown("spell:" + spellName, spell.getCooldown());
}
```

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

> **See also:** [Codecs API - Polymorphic Type Dispatch](codecs.md#polymorphic-type-dispatch)

---

## Usage Examples

### Register Custom Assets
```java
@Override
protected void setup() {
    // Register your asset store
    MyAssetStore assetStore = new MyAssetStore();
    getAssetRegistry().register(assetStore);
}
```

### Access Registered Assets
```java
// Get asset by key
MyAsset asset = assetStore.get("my_asset_id");

// Check if asset exists
if (assetStore.contains("my_asset_id")) {
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

## Asset Loading

Assets are loaded during server startup:
1. Built-in assets are loaded first
2. Plugin assets are loaded during plugin `setup()` phase
3. Assets can be accessed after all plugins are set up

---

## Notes
- Assets are typically JSON-based configurations
- Register custom assets during plugin `setup()`
- Asset loading happens through codec serialization
- Use the appropriate codec type for your asset structure
- Assets persist across server restarts (stored in data files)
- Explore specific asset type packages for detailed APIs
- For a complete guide on creating custom assets, see [Creating Custom Asset Types](#creating-custom-asset-types)
- For polymorphic assets with type dispatch, see [Codecs API - Polymorphic Type Dispatch](codecs.md#polymorphic-type-dispatch)

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
