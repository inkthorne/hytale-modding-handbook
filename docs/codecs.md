---
title: "Codecs API"
description: "Serialize Hytale Java values with codecs — convert to/from BsonValue via the Codec<T> interface and the ExtraInfo context carrying validation, version, and key-path data."
seo:
  type: TechArticle
---

# Codecs API

**Doc type:** Java API · **Verified against 0.5.0**

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

## Notes
- Codecs operate on `org.bson.BsonValue` / `org.bson.BsonDocument`; JSON is read via `decodeJson`.
- Every encode/decode call carries an `ExtraInfo` context (validation, version, key path).
- Use `BuilderCodec.builder(...)` for object/config codecs; defaults come from the blank instance the supplier creates.
- `KeyedCodec` is the unit for object fields and for `ItemStack` metadata.
- `StringCodecMapCodec`, `AssetCodecMapCodec`, and `MapKeyMapCodec` provide polymorphic dispatch; register concrete types through `getCodecRegistry(...)` during `setup()`.
- Decode errors throw exceptions (e.g. `BsonSerializationException`); there is no `DataResult` wrapper.
</content>
</invoke>

## Gotchas & Errors

Backtick-quoted error strings below are the literal messages thrown by the build-12 codec system (verified against `HytaleServer.jar`).

- **`codec parameter can't be null`** / **`encode parameter can't be null`** / **`decode parameter can't be null`** → a null was passed where a codec or the value/document to encode/decode was required. Fix: ensure the codec and target are non-null before the call.
- **`This BuilderCodec is for an abstract or direct codec. To use this codec you must specify an existing object to decode into.`** → you called the no-argument decode on an abstract/direct `BuilderCodec` that has no blank-instance supplier. Fix: decode into an existing instance, or build the codec from a concrete supplier (`BuilderCodec.builder(...)`).
- **`Codec key is already registered. Given:`** → two types were registered under the same id in a codec map. Fix: give each registered type a unique id in `register(id, type, codec)`.
- **`Expected a JSON object`** → a JSON value was decoded where an object (`{...}`) was required, but the element was a scalar/array/null. Fix: pass an object node to the object codec.
- **`JSON config cannot be null when creating builder`** → `withConfig(...)` / builder creation received a null JSON config source. Fix: provide a non-null config.
- **`Codec cannot be null if persistence is enabled.`** → persistence was enabled but no codec was supplied to serialize the persisted value. Fix: pass a codec, or disable persistence.
- **`VarInt cannot encode negative values:`** → a negative number was written as a VarInt. Fix: VarInts are unsigned; use a signed/zigzag encoding for values that can be negative.
- **Symptom:** custom polymorphic types fail to resolve with a *"Failed to find codec for"* style error → the concrete type was never registered. Fix: register each subtype via `getCodecRegistry(...)` during `setup()` using the 3-arg `register(id, type, codec)` (there is no 2-arg `register("name", instance)`).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
