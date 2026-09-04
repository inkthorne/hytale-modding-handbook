**Doc type:** JSON asset format

### Alpha Interaction

**Package:** `com.hypixel.hytale.server.core.foo.AlphaInteraction`

| Property | Type |
|---|---|
| `X` | int |

### Beta Interaction

**Package:** `com.hypixel.hytale.server.core.foo.BetaInteraction`

| Property | Type |
|---|---|
| `Y` | int |

## Driving Alpha from Java

```java
AlphaInteraction a = new AlphaInteraction();
BetaInteraction b = a.toBeta();
```
