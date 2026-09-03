---
title: "Codecs API"
description: "Serialize Hytale Java values with codecs — convert to/from BsonValue via the Codec<T> interface and the ExtraInfo context carrying validation, version, and key-path data."
seo:
  type: TechArticle
---

# Codecs API

**Doc type:** Java API · **Verified against 0.5.9**

Hytale uses a codec-based serialization system for data persistence, configuration, and asset loading. It is built on **BSON** (`org.bson.BsonValue` / `org.bson.BsonDocument`) and can also read JSON directly.

## Overview
**Package:** `com.hypixel.hytale.codec`

A codec converts a Java value to/from a `BsonValue`. Encoding and decoding always take an `ExtraInfo` context object (`com.hypixel.hytale.codec.ExtraInfo`) that carries validation results, version info, key paths, and a small metadata map.

## Architecture
```
Codec<T> (base interface, extends RawJsonCodec + SchemaConvertable)
├── Built-in singletons (Codec.STRING, Codec.INTEGER, arrays, Path/Instant/UUID, ...)
├── KeyedCodec<T>             a codec bound to a named key
├── BuilderCodec<T>           field-by-field codec for plain objects
│   └── BuilderCodec.builder(...)  fluent factory (KeyedCodec + setter/getter)
└── Codec Map Types (polymorphic / lookup dispatch)
    ├── StringCodecMapCodec<T, C>     dispatch on a string "Type" key
    ├── AssetCodecMapCodec<K, T>      dispatch keyed by asset
    └── MapKeyMapCodec<V>             map-key dispatch
        └── CodecMapRegistry<T, C>    plugin registry binding ids → codecs
ExtraInfo                       per-encode/decode context (validation, version, paths)
```

## Key Classes

| Class | Location | Description |
|-------|----------|-------------|
| `Codec<T>` | `codec` | Base interface; encode/decode a value to/from `BsonValue` |
| `KeyedCodec<T>` | `codec` | A codec associated with a named key |
| `BuilderCodec<T>` | `codec.builder` | Field-by-field codec for plain Java objects |
| `ExtraInfo` | `codec` | Encode/decode context (validation, version, key paths, metadata) |
| `StringCodecMapCodec<T, C>` | `codec` | Polymorphic dispatch on a string type key |
| `AssetCodecMapCodec<K, T>` | `codec` | Polymorphic dispatch keyed by asset |
| `MapKeyMapCodec<V>` | `codec` | Map-key-based dispatch codec |
| `CodecMapRegistry<T, C>` | `server.core.plugin.registry` | Registers custom types (id → class + codec) |
| `ProtocolCodecs` | `server.core.codec` | Pre-built codec constants for protocol types (colors, ranges, game mode, …) |
| `ColorCodec` | `server.core.codec.protocol` | `Codec<Color>` reading `#RGB` / `#RRGGBB` / `rgb(R,G,B)` strings |
| `WeightedMapCodec<T>` | `server.core.codec` | Codec for an `IWeightedMap<T>` of weighted elements |
| `PairCodec` | `server.core.codec` | Holder for codec-backed pair types (`IntegerPair`, `IntegerStringPair`) |
| `LayerEntryCodec` | `server.core.codec` | Codec-backed depth→material layer entry (scripted-brush layers) |
| `BsonUtil` | `server.core.util` | Static BSON read/write helpers (bytes, files, JSON translation) |
| `HashUtil` | `server.core.util` | `sha256(byte[])` → hex string |
| `FileUtil` | `server.core.util.io` | Filesystem helpers (atomic writes, zip extraction, directory copy/delete) |
| `MemorySegmentUtil` | `server.core.util.io` | `java.lang.foreign` helpers (endian layouts, UTF strings, packed numbers) |

---

## Core Codec Types

### Codec<T>
**Package:** `com.hypixel.hytale.codec`

Base interface for all codecs. It extends `RawJsonCodec<T>` and `SchemaConvertable<T>`.

```java
public interface Codec<T> extends RawJsonCodec<T>, SchemaConvertable<T> {
    // Decode a value from a BsonValue
    T decode(BsonValue value, ExtraInfo extraInfo);
    default T decode(BsonValue value);          // uses a fresh ExtraInfo

    // Encode a value to a BsonValue
    BsonValue encode(T value, ExtraInfo extraInfo);
    default BsonValue encode(T value);          // uses a fresh ExtraInfo

    // Read directly from JSON (used during asset loading)
    default T decodeJson(RawJsonReader reader, ExtraInfo extraInfo) throws IOException;
}
```

> Note: there is no `DynamicOps`, `DataResult`, or `Pair` in this API. Decode failures throw exceptions (e.g. `org.bson.BsonSerializationException`) rather than returning a result wrapper.

---

## Built-in Codecs

`Codec` exposes pre-built singleton instances as static fields. Their exact field types are concrete classes, but they are all `Codec<T>`.

### Primitive / simple codecs
```java
Codec.BOOLEAN     // Codec<Boolean>  (BooleanCodec)
Codec.BYTE        // Codec<Byte>     (ByteCodec)
Codec.SHORT       // Codec<Short>    (ShortCodec)
Codec.INTEGER     // Codec<Integer>  (IntegerCodec)
Codec.LONG        // Codec<Long>     (LongCodec)
Codec.FLOAT       // Codec<Float>    (FloatCodec)
Codec.DOUBLE      // Codec<Double>   (DoubleCodec)
Codec.STRING      // Codec<String>   (StringCodec)
```

> The constants are `BOOLEAN` and `INTEGER` — there is no `Codec.BOOL` or `Codec.INT`.

### Array codecs
```java
Codec.BYTE_ARRAY     // Codec<byte[]>
Codec.DOUBLE_ARRAY   // DoubleArrayCodec
Codec.FLOAT_ARRAY    // FloatArrayCodec
Codec.INT_ARRAY      // IntArrayCodec
Codec.LONG_ARRAY     // LongArrayCodec
Codec.STRING_ARRAY   // ArrayCodec<String>
```

### Other built-ins
```java
Codec.BSON_DOCUMENT  // Codec for a raw BsonDocument
Codec.PATH           // FunctionCodec<String, Path>
Codec.INSTANT        // FunctionCodec<String, Instant>
Codec.DURATION       // FunctionCodec<String, Duration>
Codec.DURATION_SECONDS // FunctionCodec<Double, Duration>
Codec.LOG_LEVEL      // FunctionCodec<String, java.util.logging.Level>
Codec.UUID_BINARY    // UUIDBinaryCodec
Codec.UUID_STRING    // FunctionCodec<String, UUID>
```

### Building collection / enum codecs
There is no `Codec.list(...)` or `Codec.unboundedMap(...)`. Collection codecs are concrete classes you construct directly:

```java
// Array of T (com.hypixel.hytale.codec.codecs.array.ArrayCodec)
ArrayCodec<String> stringArray = new ArrayCodec<>(Codec.STRING, String[]::new);

// Set of V (com.hypixel.hytale.codec.codecs.set.SetCodec)
SetCodec<String, Set<String>> stringSet =
    new SetCodec<>(Codec.STRING, HashSet::new, false);

// Map<String, V> (com.hypixel.hytale.codec.codecs.map.MapCodec)
MapCodec<String, Integer, Map<String, Integer>> stringIntMap =
    new MapCodec<>(Codec.INTEGER, HashMap::new);

// Enum (com.hypixel.hytale.codec.codecs.EnumCodec)
EnumCodec<MyEnum> enumCodec = new EnumCodec<>(MyEnum.class);
```

---

### KeyedCodec<T>
**Package:** `com.hypixel.hytale.codec`

A concrete class that pairs a child `Codec<T>` with a string key. It reads/writes that key inside a `BsonDocument` and is the building block for object fields and for `ItemStack` metadata.

```java
public class KeyedCodec<T> {
    public KeyedCodec(String key, Codec<T> codec);
    public KeyedCodec(String key, Codec<T> codec, boolean required);
    public KeyedCodec(String key, Codec<T> codec, boolean required, boolean ...);

    public String getKey();
    public Codec<T> getChildCodec();
    public boolean isRequired();

    // Read this key out of a document
    public T getNow(BsonDocument doc);
    public T getOrNull(BsonDocument doc);
    public Optional<T> get(BsonDocument doc);
    public T getOrDefault(BsonDocument doc, ExtraInfo info, T fallback);

    // Write this key into a document
    public void put(BsonDocument doc, T value);
}
```

#### Usage with ItemStack Metadata
`ItemStack` stores metadata as a `BsonDocument`, and a `KeyedCodec` is used to read/write a single entry.

```java
// "MyData" is the BSON key; MyData.CODEC is a Codec<MyData>
public static final KeyedCodec<MyData> MY_DATA =
    new KeyedCodec<>("MyData", MyData.CODEC);

// Store on an ItemStack (returns a new ItemStack)
ItemStack stamped = itemStack.withMetadata(MY_DATA, myDataInstance);

// Retrieve (null if absent)
MyData data = stamped.getFromMetadataOrNull(MY_DATA);
```

`ItemStack` also offers `withMetadata(String key, Codec<T>, T)` and
`getFromMetadataOrNull(String key, Codec<T>)` if you prefer not to keep a `KeyedCodec`.

---

## BuilderCodec — codecs for objects

### BuilderCodec<T>
**Package:** `com.hypixel.hytale.codec.builder`

`BuilderCodec` is a concrete `Codec<T>` (it also implements `DirectDecodeCodec`, `InheritCodec`, and `ValidatableCodec`). It is the standard way to define a codec for a plain Java object. You build one with the static `builder(...)` factory and a fluent API; each field is a `KeyedCodec` plus a setter (`BiConsumer<T, F>`) and a getter (`Function<T, F>`).

```java
public class BuilderCodec<T> implements Codec<T>, ... {
    // Factory: the class plus a no-arg supplier that creates a blank instance
    public static <T> Builder<T> builder(Class<T> type, Supplier<T> supplier);

    // The default/blank instance produced by the supplier
    public T getDefaultValue();
    public T getDefaultValue(ExtraInfo extraInfo);

    public Class<T> getInnerClass();
    public BsonDocument encode(T value, ExtraInfo extraInfo);
    public T decode(BsonValue value, ExtraInfo extraInfo);
}
```

The fluent `Builder<T>` (returned by `builder(...)`) offers, among others:

```java
// Add a field; returns a FieldBuilder you finish with .add()
<F> FieldBuilder append(KeyedCodec<F> codec, BiConsumer<T, F> setter, Function<T, F> getter);

// Add a field directly without the FieldBuilder step
<F> Builder<T> addField(KeyedCodec<F> codec, BiConsumer<T, F> setter, Function<T, F> getter);

Builder<T> documentation(String doc);
Builder<T> versioned();
Builder<T> afterDecode(BiConsumer<T, ExtraInfo> action);
Builder<T> validator(BiConsumer<T, ValidationResults> validator);
BuilderCodec<T> build();
```

`FieldBuilder` (returned by `append`) lets you attach per-field options, then `add()` returns to the `Builder`:

```java
FieldBuilder addValidator(Validator<? super F> validator);
FieldBuilder setVersionRange(int min, int max);
FieldBuilder documentation(String doc);
Builder<T> add();
```

> There is no `BuilderCodec.getDefault()` — the method is `getDefaultValue()`. `BuilderCodec` is a class, not an interface, so you do not implement it anonymously; you build instances with `BuilderCodec.builder(...)`.

#### Defining a CODEC for an object

This is the real idiom used throughout the codebase (e.g. `InteractionConfiguration.CODEC`):

```java
public class MyConfig {
    private boolean enabled = true;
    private int maxConnections = 100;
    private String welcomeMessage = "Welcome!";

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean v) { this.enabled = v; }
    public int getMaxConnections() { return maxConnections; }
    public void setMaxConnections(int v) { this.maxConnections = v; }
    public String getWelcomeMessage() { return welcomeMessage; }
    public void setWelcomeMessage(String v) { this.welcomeMessage = v; }

    public static final BuilderCodec<MyConfig> CODEC =
        BuilderCodec.builder(MyConfig.class, MyConfig::new)
            .append(new KeyedCodec<>("Enabled", Codec.BOOLEAN),
                    MyConfig::setEnabled, MyConfig::isEnabled)
            .add()
            .append(new KeyedCodec<>("MaxConnections", Codec.INTEGER),
                    MyConfig::setMaxConnections, MyConfig::getMaxConnections)
            .add()
            .append(new KeyedCodec<>("WelcomeMessage", Codec.STRING),
                    MyConfig::setWelcomeMessage, MyConfig::getWelcomeMessage)
            .add()
            .build();
}
```

Defaults come from the fields' initial values in the supplied blank instance (`MyConfig::new`) — missing keys simply keep those values.

> **See also:** [Plugin Configuration](plugin-lifecycle.md#configuration)

---

## Parent Inheritance (`InheritCodec`)

`BuilderCodec` implements `InheritCodec`, which is what resolves the `"Parent": "<id>"` field
pervasive in JSON assets (items, interactions, sound events, audio categories, …). When an asset
declares a parent, the loader builds the parent instance first, then **deep-merges** the child's
document over it via `BuilderCodec.decodeAndInherit(...)`. The merge is recursive and field-by-field:

| Child document | Result |
|----------------|--------|
| Field **absent** | keeps the parent's value |
| **Scalar / string** present | replaces the parent's value |
| **Nested object** present (a field whose codec is itself a `BuilderCodec`) | **recurses** — merges key-by-key against the parent's object, so a *partial* object keeps the parent's other keys |
| **Array / list** present | **replaces wholesale** — lists are not keyed, so there is no element-level merge |
| **`null`** present | **suppresses** the inherited field — explicitly clears a value the parent set |

The `null` rule is the inverse of "absent": omitting a field keeps the parent's value, while
`"<field>": null` removes it. Verified with `Metal_Bronze_Ornate` (`Parent`: `Rock_Gold_Brick_Ornate`)
setting `"Recipe": null` to make an otherwise-craftable item un-craftable in the variant.

The array rule is the common gotcha: a partial `Specs` / `Layers` / `Input` / `Children` array
**overwrites** the parent's entire list rather than appending to it. To keep the parent's elements
plus your own, re-list all of them in the child.

The nested-object rule is what makes partial overrides ergonomic. A child `DamageEffects` that sets
only `WorldSoundEventId`, for example, keeps the parent's `Knockback`, `WorldParticles`, and
`CameraEffect`:

```json
// parent interaction's DamageEffects: { Knockback, WorldParticles, CameraEffect }
// child override:
{
  "DamageEffects": {
    "WorldSoundEventId": "SFX_Sword_T2_Impact"
  }
}
// merged result: Knockback + WorldParticles + CameraEffect (parent) + WorldSoundEventId (child)
```

> **`Parent` inheritance and asset-pack override are different mechanisms.** `Parent` is a
> deep merge *within a single asset definition* (this section). Shipping a file at the *same id* as
> another asset is a *whole-asset replace across assets* — see
> [Assets API → Overriding base-game assets](assets.md#overriding-base-game-assets).

---

## Plugin Configuration

`PluginBase` loads config through a `BuilderCodec<T>`. Note the return type is `Config<T>` (`com.hypixel.hytale.server.core.util.Config`), **not** `T`.

```java
protected final <T> Config<T> withConfig(BuilderCodec<T> codec);
protected final <T> Config<T> withConfig(String name, BuilderCodec<T> codec);
```

`Config<T>` exposes:

```java
public class Config<T> {
    public CompletableFuture<T> load();   // load from disk (or defaults)
    public T get();                       // current value
    public CompletableFuture<Void> save();
}
```

Usage in a plugin:

```java
@Override
protected void setup() {
    Config<MyConfig> config = withConfig(MyConfig.CODEC);
    config.load().thenAccept(loaded -> {
        if (loaded.isEnabled()) {
            // plugin enabled
        }
    });
}
```

---

## Codec Map Types (polymorphic / lookup codecs)

These map a string discriminator (a `"Type"`-style key) or a class to a child codec, so a document can select which concrete codec deserializes it.

### StringCodecMapCodec<T, C>
**Package:** `com.hypixel.hytale.codec.lookup`

Abstract base for codecs that dispatch on a string key. It is **abstract** — you do not instantiate it directly with `new StringCodecMapCodec<>("Type", SomeClass.class)`. Concrete subclasses (such as `AssetCodecMapCodec`) provide a usable implementation. Its constructors take the discriminator key and flags:

```java
public abstract class StringCodecMapCodec<T, C extends Codec<? extends T>>
        extends ACodecMapCodec<String, T, C> {
    public StringCodecMapCodec();
    public StringCodecMapCodec(String typeKey);
    public StringCodecMapCodec(String typeKey, boolean ...);

    // register a concrete type under a string id
    public StringCodecMapCodec<T, C> register(Priority p, String id,
                                              Class<? extends T> type, C codec);
}
```

### AssetCodecMapCodec<K, T>
**Package:** `com.hypixel.hytale.assetstore.codec`

A concrete `StringCodecMapCodec` for polymorphic JSON assets (`T extends JsonAsset<K>`). This is what real assets such as `Interaction.CODEC` use. Its constructor takes the **key codec plus id and asset-data getters/setters** (5 args, or 6 with a leading type-key string) — **not** a single `MyAsset.CODEC`:

```java
public class AssetCodecMapCodec<K, T extends JsonAsset<K>>
        extends StringCodecMapCodec<T, AssetBuilderCodec<K, T>>
        implements AssetCodec<K, T> {

    public AssetCodecMapCodec(
        Codec<K> keyCodec,
        BiConsumer<T, K> idSetter,
        Function<T, K> idGetter,
        BiConsumer<T, AssetExtraInfo.Data> dataSetter,
        Function<T, AssetExtraInfo.Data> dataGetter);

    // 6-arg variant adds a leading type-key String

    // register a concrete asset subtype (the child is an AssetBuilderCodec)
    public AssetCodecMapCodec<K, T> register(String id,
        Class<? extends T> type, BuilderCodec<? extends T> codec);
}
```

### MapKeyMapCodec<V>
**Package:** `com.hypixel.hytale.codec.lookup`

A concrete map codec keyed by `Class<? extends V>`. The constructor is **no-arg**; you register types after construction via `register(Class, String, Codec)`:

```java
public class MapKeyMapCodec<V> extends AMapProvidedMapCodec<...> {
    public MapKeyMapCodec();
    public MapKeyMapCodec(boolean ...);

    public <T extends V> void register(Class<T> type, String id, Codec<T> codec);
    public <T extends V> void unregister(Class<T> type);

    public Class<? extends V> getKeyForId(String id);
    public V decodeById(String id, BsonValue value, ExtraInfo info);
}
```

---

## Registering Custom Types via the Plugin Registry

### CodecMapRegistry<T, C>
**Package:** `com.hypixel.hytale.server.core.plugin.registry`

A plugin obtains a registry for a given map codec through `PluginBase.getCodecRegistry(...)`, then registers concrete types. Registration is **3-arg**: `register(String id, Class<? extends T> type, C codec)` — note the explicit `Class` argument (there is no 2-arg `register("name", instance)`).

```java
public class CodecMapRegistry<T, C extends Codec<? extends T>> implements IRegistry {
    public CodecMapRegistry<T, C> register(String id,
        Class<? extends T> type, C codec);
    public CodecMapRegistry<T, C> register(Priority p, String id,
        Class<? extends T> type, C codec);
    public void shutdown();
}
```

`PluginBase` provides overloads of `getCodecRegistry` for each map-codec kind:

```java
// for a StringCodecMapCodec<T, C>
<T, C extends Codec<? extends T>> CodecMapRegistry<T, C>
    getCodecRegistry(StringCodecMapCodec<T, C> mapCodec);

// for an AssetCodecMapCodec<K, T>
<K, T extends JsonAsset<K>> CodecMapRegistry.Assets<T, ?>
    getCodecRegistry(AssetCodecMapCodec<K, T> mapCodec);

// for a MapKeyMapCodec<V>
<V> MapKeyMapRegistry<V> getCodecRegistry(MapKeyMapCodec<V> mapCodec);
```

#### Example: registering a custom type into an existing string-dispatched system

```java
@Override
protected void setup() {
    // SomeBase.MAP_CODEC is a StringCodecMapCodec<SomeBase, Codec<? extends SomeBase>>
    CodecMapRegistry<SomeBase, Codec<? extends SomeBase>> registry =
        getCodecRegistry(SomeBase.MAP_CODEC);

    // documents with this id now decode with MyType.CODEC
    registry.register("MyType", MyType.class, MyType.CODEC);
}
```

> Registration must occur during `setup()`, before asset loading completes. Built-in types are registered by server modules before plugins load.

---

## Custom Assets with Codecs

Real asset classes implement `JsonAsset<K>` (which requires `K getId()`) and expose their codec as an `AssetBuilderCodec` (a `BuilderCodec` subclass). Polymorphic asset families (like `Interaction`) expose an `AssetCodecMapCodec` as their `CODEC`.

For example, `com.hypixel.hytale.server.core.asset.type.item.config.CraftingRecipe` and
`com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType` both declare:

```java
public static final AssetBuilderCodec<String, ThatAsset> CODEC;
```

`AssetBuilderCodec` is built like a `BuilderCodec`, but its `builder(...)` factory additionally takes the key codec and the id/data getters and setters:

```java
public static <K, T extends JsonAsset<K>> AssetBuilderCodec.Builder<K, T> builder(
    Class<T> type,
    Supplier<T> supplier,
    Codec<K> keyCodec,
    BiConsumer<T, K> idSetter,
    Function<T, K> idGetter,
    BiConsumer<T, AssetExtraInfo.Data> dataSetter,
    Function<T, AssetExtraInfo.Data> dataGetter);
```

You then chain `.append(...).add()` for each field exactly as with `BuilderCodec`.

> **See also:** [Assets API - Creating Custom Asset Types](assets.md#creating-custom-asset-types) for the complete guide.

---

## Server-Side Codec Helpers

**Package:** `com.hypixel.hytale.server.core.codec`

Ready-made codecs for common server/protocol value types, so you don't hand-roll them in a `BuilderCodec` field.

### ProtocolCodecs

`com.hypixel.hytale.server.core.codec.ProtocolCodecs` is a `final` holder class whose `public static final` constants are pre-built codecs for `com.hypixel.hytale.protocol` types. Use them directly as the codec in a `KeyedCodec`:

```java
public static final ColorCodec COLOR;                              // Codec<Color>
public static final ArrayCodec<Color> COLOR_ARRAY;
public static final ColorAlphaCodec COLOR_ALPHA;                   // was misspelled COLOR_AlPHA before 0.6.3
public static final BuilderCodec<ColorLight> COLOR_LIGHT;
public static final BuilderCodec<Direction> DIRECTION;
public static final EnumCodec<GameMode> GAMEMODE;
public static final EnumCodec<GameMode> GAMEMODE_LEGACY;
public static final BuilderCodec<Size> SIZE;
public static final BuilderCodec<IntersectionHighlight> INTERSECTION_HIGHLIGHT;
public static final BuilderCodec<SavedMovementStates> SAVED_MOVEMENT_STATES;
public static final BuilderCodec<Range> RANGE;                     // int Min/Max
public static final BuilderCodec<Rangeb> RANGEB;                   // byte Min/Max
public static final BuilderCodec<Rangef> RANGEF;                   // float Min/Max
public static final BuilderCodec<RangeVector2f> RANGE_VECTOR2F;
public static final BuilderCodec<RangeVector3f> RANGE_VECTOR3F;
public static final BuilderCodec<InitialVelocity> INITIAL_VELOCITY;
public static final BuilderCodec<UVMotion> UV_MOTION;
public static final BuilderCodec<ItemAnimation> ITEM_ANIMATION_CODEC;
public static final EnumCodec<EasingType> EASING_TYPE_CODEC;
public static final EnumCodec<ChangeStatBehaviour> CHANGE_STAT_BEHAVIOUR_CODEC;
public static final EnumCodec<AccumulationMode> ACCUMULATION_MODE_CODEC;
public static final EnumCodec<ChangeVelocityType> CHANGE_VELOCITY_TYPE_CODEC;
public static final BuilderCodec<RailPoint> RAIL_POINT_CODEC;
public static final BuilderCodec<RailConfig> RAIL_CONFIG_CODEC;
```

> The alpha-color constant is **`COLOR_ALPHA`** as of 0.6.3. Through 0.5.x it was misspelled `COLOR_AlPHA` (lowercase `l`) in the jar; the old name was removed by 0.6.3, so code written against it no longer compiles — rename to `ProtocolCodecs.COLOR_ALPHA`.

### ColorCodec

**Package:** `com.hypixel.hytale.server.core.codec.protocol`

A `Codec<com.hypixel.hytale.protocol.Color>`. Encodes to a `#RRGGBB` hex string; decodes `#RGB`, `#RRGGBB`, or `rgb(R,G,B)` strings (via [`ColorParseUtil`](assets.md#colorparseutil)). An unparseable string throws a `CodecException`: `Invalid color format, expected: #RGB, #RRGGBB or rgb(R,G,B)`. Normally reached through `ProtocolCodecs.COLOR` rather than `new ColorCodec()`.

> **`CodecException` messages carry the key path.** When a codec throws with an `ExtraInfo` in hand, `getMessage()` is the bare message plus the offending key and source (`<message> '<key>' \nFrom: '<value>'`). As of 0.6.3 `CodecException.getRawMessage()` returns the bare message on its own — match on that (or on a fragment) rather than on the full `getMessage()` text.

### WeightedMapCodec<T>

A `Codec<IWeightedMap<T>>` (`com.hypixel.hytale.common.map.IWeightedMap`) for `T extends IWeightedElement` — the JSON form is an array of weighted-element documents. Used by asset families like drop containers and spawn markers.

```java
public class WeightedMapCodec<T extends IWeightedElement>
        implements Codec<IWeightedMap<T>>, WrappedCodec<T> {
    public WeightedMapCodec(Codec<T> codec, T[] emptyKeys);
    public Codec<T> getChildCodec();
}
```

### PairCodec

A holder class for codec-backed pair types; the nested classes are what you use. Both serialize as `{"Left": …, "Right": …}` (both keys required) and convert to/from a fastutil `Pair`:

```java
public class PairCodec.IntegerPair {
    public static final BuilderCodec<PairCodec.IntegerPair> CODEC;
    public IntegerPair(Integer left, Integer right);
    public Pair<Integer, Integer> toPair();
    public static IntegerPair fromPair(Pair<Integer, Integer> pair);
    public Integer getLeft();
    public Integer getRight();
}

public class PairCodec.IntegerStringPair {
    public static final BuilderCodec<PairCodec.IntegerStringPair> CODEC;
    public IntegerStringPair(Integer left, String right);
    public Pair<Integer, String> toPair();
    public static IntegerStringPair fromPair(Pair<Integer, String> pair);
    public Integer getLeft();
    public String getRight();
}
```

### LayerEntryCodec

A codec-backed *depth → material* layer entry, used by the scripted-brush `Layer` / `HeightmapLayer` operations (an array under a `Layers` key). Despite the JSON key names, `Left` is the layer **depth** (int, required) and `Right` is the **material id** (string, required); `UseToolArg` and `Skip` are optional booleans.

```java
public class LayerEntryCodec {
    public static final BuilderCodec<LayerEntryCodec> CODEC;
    public LayerEntryCodec(Integer depth, String material, boolean useToolArg);
    public Integer getDepth();       // JSON key "Left"
    public String getMaterial();     // JSON key "Right"
    public boolean isUseToolArg();
    public boolean isSkip();
}
```

---

## Serialization & I/O Utilities

Static helper classes in `com.hypixel.hytale.server.core.util` that pair naturally with codec work.

### BsonUtil

**Package:** `com.hypixel.hytale.server.core.util`

Static helpers for moving `BsonDocument`s between bytes, files, and JSON. The file operations return `CompletableFuture`s (async I/O); `writeSync` is the blocking codec-to-file shortcut.

```java
// bytes / buffers
public static byte[] writeToBytes(BsonDocument doc);
public static int encodeInto(BsonDocument doc, BasicOutputBuffer out);  // 0.6.3+: bytes written
public static BsonDocument readFromBytes(byte[] bytes);
public static BsonDocument readFromBuffer(ByteBuffer buffer);
public static BsonDocument readFromBinaryStream(ByteBuffer buffer);
public static void writeToBinaryStream(DataOutputStream out, BsonDocument doc) throws IOException;

// files (async)
public static CompletableFuture<Void> writeDocument(Path path, BsonDocument doc);
public static CompletableFuture<Void> writeDocument(Path path, BsonDocument doc, boolean backup);
public static CompletableFuture<BsonDocument> readDocument(Path path);
public static CompletableFuture<BsonDocument> readDocument(Path path, boolean backup);
public static BsonDocument readDocumentNow(Path path);              // blocking
public static CompletableFuture<BsonDocument> readDocumentBak(Path path);

// JSON bridges
public static BsonValue translateJsonToBson(com.google.gson.JsonElement json);
public static com.google.gson.JsonElement translateBsonToJson(BsonDocument doc);
public static String toJson(BsonDocument doc);

// JSON string -> BsonDocument with a nesting cap (0.6.3+); default maxDepth = 256
public static BsonDocument parseWithMaxDepth(String json);
public static BsonDocument parseWithMaxDepth(String json, int maxDepth);

// encode a value with its codec and write it, synchronously
public static <T> void writeSync(Path path, Codec<T> codec, T value, HytaleLogger logger) throws IOException;
```

`parseWithMaxDepth` (0.6.3+) is the safe way to turn **untrusted** JSON text into a `BsonDocument`: it reads through `com.hypixel.hytale.server.core.util.DepthLimitedJsonReader`, which counts document/array nesting and throws `DepthLimitedJsonReader.MaxDepthExceededException` (`JSON nesting exceeded the maximum allowed depth of <N>`) once the cap is passed. The engine uses it for JSON that arrives over the wire (asset-editor edits, anchor-action payloads); ordinary asset loading goes through `RawJsonReader` and is **not** depth-limited by it.

### HashUtil

One method: `HashUtil.sha256(byte[])` returns the SHA-256 digest as a lowercase hex `String`. This is the same hash used for common-asset identity (see [Assets API → Common Assets](assets.md#common-assets-java-api)).

### FileUtil

**Package:** `com.hypixel.hytale.server.core.util.io`

Filesystem helpers used throughout asset and save handling. `writeStringAtomic` writes to a temp file then `atomicMove`s it into place, so readers never observe a half-written file.

```java
public static final Pattern INVALID_FILENAME_CHARACTERS;

public static void copyDirectory(Path from, Path to) throws IOException;
public static void moveDirectoryContents(Path from, Path to, CopyOption... options) throws IOException;
public static void deleteDirectory(Path dir) throws IOException;    // recursive
public static void extractZip(Path zip, Path target) throws IOException;
public static void extractZip(InputStream zip, Path target) throws IOException;
public static void writeStringAtomic(Path path, String content) throws IOException;  // backup = true
public static void writeStringAtomic(Path path, String content, boolean backup) throws IOException; // backup: keep old file as .bak
public static void atomicMove(Path from, Path to) throws IOException;
```

### MemorySegmentUtil

**Package:** `com.hypixel.hytale.server.core.util.io`

Helpers for `java.lang.foreign.MemorySegment` I/O (Java FFM API): explicit-endian `ValueLayout` constants (`SHORT_BE`/`SHORT_LE`, `INT_BE`/`INT_LE`, `LONG_BE`/`LONG_LE`, `FLOAT_BE`/`FLOAT_LE`), length-prefixed UTF-8 strings, and variable-width packed integers.

```java
public static final int MAX_UNSIGNED_SHORT_VALUE = 65535;

public static int utf8Size(String value);                      // encoded size incl. length prefix
public static int utf8Size(MemorySegment segment, long offset); // size of the string at offset
public static int writeUTF(MemorySegment segment, long offset, String value);
public static String readUTF(MemorySegment segment, long offset);
public static void writeNumber(MemorySegment segment, int offset, int bytes, int value); // bytes = 1, 2, or 4
public static int readNumber(MemorySegment segment, int offset, int bytes);
```

---

## Notes
- Codecs operate on `org.bson.BsonValue` / `org.bson.BsonDocument`; JSON is read via `decodeJson`.
- Every encode/decode call carries an `ExtraInfo` context (validation, version, key path).
- Use `BuilderCodec.builder(...)` for object/config codecs; defaults come from the blank instance the supplier creates.
- `KeyedCodec` is the unit for object fields and for `ItemStack` metadata.
- `StringCodecMapCodec`, `AssetCodecMapCodec`, and `MapKeyMapCodec` provide polymorphic dispatch; register concrete types through `getCodecRegistry(...)` during `setup()`.
- Decode errors throw exceptions (e.g. `BsonSerializationException`); there is no `DataResult` wrapper.

---

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the codec system (verified against `HytaleServer.jar`).

- **`codec parameter can't be null`** / **`encode parameter can't be null`** / **`decode parameter can't be null`** → a null was passed where a codec or the value/document to encode/decode was required. Fix: ensure the codec and target are non-null before the call.
- **`This BuilderCodec is for an abstract or direct codec. To use this codec you must specify an existing object to decode into.`** → you called the no-argument decode on an abstract/direct `BuilderCodec` that has no blank-instance supplier. Fix: decode into an existing instance, or build the codec from a concrete supplier (`BuilderCodec.builder(...)`).
- **`Codec key is already registered. Given:`** → two types were registered under the same id in a codec map. Fix: give each registered type a unique id in `register(id, type, codec)`.
- **`Expected a JSON object`** → a JSON value was decoded where an object (`{...}`) was required, but the element was a scalar/array/null. Fix: pass an object node to the object codec.
- **`JSON config cannot be null when creating builder`** → `withConfig(...)` / builder creation received a null JSON config source. Fix: provide a non-null config.
- **`Codec cannot be null if persistence is enabled.`** → persistence was enabled but no codec was supplied to serialize the persisted value. Fix: pass a codec, or disable persistence.
- **`VarInt cannot encode negative values:`** → a negative number was written as a VarInt. Fix: VarInts are unsigned; use a signed/zigzag encoding for values that can be negative.
- **`JSON nesting exceeded the maximum allowed depth of`** (0.6.3+) → `BsonUtil.parseWithMaxDepth` hit its nesting cap (default 256) on a deeply nested JSON string. Fix: flatten the payload, or pass a larger `maxDepth` if the depth is legitimate.
- **Symptom:** custom polymorphic types fail to resolve with a *"Failed to find codec for"* style error → the concrete type was never registered. Fix: register each subtype via `getCodecRegistry(...)` during `setup()` using the 3-arg `register(id, type, codec)` (there is no 2-arg `register("name", instance)`).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
