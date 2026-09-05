# Page A

Registry-resolved and asset-resolved values.

```json
{ "Type": "Alpha", "Nested": { "Type": "Gamma" } }
```

Tab-separated in the assets, space-separated here:

```json
{ "Type": "Delta" }
```

This page registers its own type, so `Epsilon` is legitimate here:

```java
Foo.CODEC.register("Epsilon", EpsilonFoo.class, EpsilonFoo.CODEC);
```

```json
{ "Type": "Epsilon" }
```
