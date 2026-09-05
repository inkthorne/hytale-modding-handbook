---
title: "Connected Blocks"
description: "Hytale's connected-block system — ConnectedBlockRuleSet types, shape configs and neighbour rules, plus the patterned rule sets that drive multi-block structures like roofs and walls."
seo:
  type: TechArticle
---

# Connected Blocks

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item` · **Verified against 0.6.3**

Split out of [blocks.md](blocks.md) at the seam recorded in `maintenance/page-size-arrears.txt`.
Connected blocks pick their model and state from their neighbours: a block opts in through
`BlockType.ConnectedBlockRuleSet`, and this page covers the four rule-set types, the shape configs
and neighbour rules they read, and the **patterned** rule sets that drive multi-block structures.
The `BlockType` object that carries `ConnectedBlockRuleSet` is documented in
[blocks.md](blocks.md); the Java classes behind it are in
[blocks-java-api.md](blocks-java-api.md).

---

## Connected Block Templates

Connected blocks automatically select models and states based on neighboring blocks. A block
opts in through `BlockType.ConnectedBlockRuleSet`, a `Type`-tagged object. `ConnectedBlocksModule`
registers four rule-set types:

| `Type` | Java class | Notes |
|--------|-----------|-------|
| `Stair` | `StairConnectedBlockRuleSet` | Built-in stair corner/inverted-corner solver (~163 shipped blocks) |
| `Roof` | `RoofConnectedBlockRuleSet` | Built-in roof solver, adds a `Topper` (~241) |
| `CustomTemplate` | `CustomTemplateConnectedBlockRuleSet` | Data-driven; points at a template in `Server/Item/CustomConnectedBlockTemplates/` (~135) |
| `Patterned` | `PatternedConnectedBlockRuleSet` | Data-driven rule/shape trees; see [Patterned Connected Block Rule Sets](#patterned-connected-block-rule-sets) (new in 0.6.3, no shipped block uses it yet) |

The `CustomTemplate` form is described below; 11 templates ship:

| Template | Description |
|----------|-------------|
| `DoorConnectedBlockTemplate` | Door orientation and state |
| `DoorLargeConnectedBlockTemplate` | Large/double door connections |
| `ChestConnectedBlockTemplate` | Chest orientation |
| `RailsConnectedBlockTemplate` | Railway track connections |
| `WallConnectedBlockTemplate` | Wall/fence post connections |
| `PillarConnectedBlockTemplate` | Pillar stacking |
| `RoofConnectedBlockTemplate` | Roof tile connections |
| `BranchConnectedBlockTemplate` | Organic branch connections |
| `BookshelfConnectedBlockTemplate` | Bookshelf groupings |
| `CobbleCornerConnectedBlockTemplate` | Corner piece connections |
| `VillageConnectedBlockTemplate` | Village structure connections |

### Using a Connected Template

Reference the template by asset id and map every shape key it declares to a block
(`Build_Grey_Fence`; a `*` prefix references another block's state definitions):

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "CustomTemplate",
      "TemplateShapeAssetId": "WallConnectedBlockTemplate",
      "TemplateShapeBlockPatterns": {
        "Straight": "Build_Grey_Fence",
        "Corner": "*Build_Grey_Fence_State_Definitions_Corner"
      }
    }
  }
}
```

`TemplateShapeAssetId` is validated against the `CustomConnectedBlockTemplateAsset` store, and
`TemplateShapeBlockPatterns` values are `BlockPattern`s — the codec's own documentation is *"You
must specify all shapes as a BlockPattern. The shapes are as outlined in the keys of the
ShapeTemplateAsset's map."*

### Template Structure

Templates define shape patterns and the tags neighbors match on:

```json
{
  "ConnectsToOtherMaterials": true,
  "DefaultShape": "Straight",
  "Shapes": {
    "Straight": {
      "FaceTags": {
        "East": ["FenceConnection"],
        "West": ["FenceConnection"]
      },
      "PatternsToMatchAnyOf": []
    },
    "Corner": {
      "FaceTags": {
        "West": ["FenceConnection"],
        "South": ["FenceConnection"]
      },
      "PatternsToMatchAnyOf": [
        {
          "Type": "Custom",
          "AllowedPatternTransformations": { "IsCardinallyRotatable": true },
          "RulesToMatch": [
            { "Position": { "X": -1, "Y": 0, "Z": 0 },
              "IncludeOrExclude": "Include",
              "FaceTags": { "East": ["FenceConnection"] } },
            { "Position": { "X": 0, "Y": 0, "Z": 1 },
              "IncludeOrExclude": "Include",
              "FaceTags": { "North": ["FenceConnection"] } },
            { "Position": { "X": 1, "Y": 0, "Z": 0 },
              "IncludeOrExclude": "Exclude",
              "FaceTags": { "West": ["FenceConnection"] } },
            { "Position": { "X": 0, "Y": 0, "Z": -1 },
              "IncludeOrExclude": "Exclude",
              "FaceTags": { "South": ["FenceConnection"] } }
          ]
        }
      ]
    },
    "Gate": { },
    "T_Junction": { },
    "Cross_Junction": { }
  }
}
```
*(abridged from `WallConnectedBlockTemplate.json`. `DefaultShape` is what wins when nothing matches,
so `Straight` needs no pattern of its own; `Corner` matches "connected west and south, not east and
not north" and `IsCardinallyRotatable` supplies the other three orientations.)*

The template asset has exactly four top-level keys (`CustomConnectedBlockTemplateAsset.CODEC`):

| Property | Type | Description |
|----------|------|-------------|
| `ConnectsToOtherMaterials` | boolean | Connect to blocks driven by a different template |
| `DefaultShape` | string | Shape used when no pattern matches |
| `DontUpdateAfterInitialPlacement` | boolean | Freeze the shape after placement (drives `CustomTemplateConnectedBlockRuleSet.onlyUpdateOnPlacement`) |
| `Shapes` | object | Map of shape name → `{ FaceTags, PatternsToMatchAnyOf }` |

Each entry of `Shapes` (`ConnectedBlockShape`) has two keys:

| Property | Type | Description |
|----------|------|-------------|
| `FaceTags` | object | Per-direction (`North`/`East`/`South`/`West`/`Up`/`Down`) tag arrays this shape exposes to neighbors |
| `PatternsToMatchAnyOf` | array | Patterns; the shape wins if any one of them matches |

Each pattern is `Type`-tagged; the only registered type is `Custom` (`CustomConnectedBlockPattern`):

| Property | Type | Description |
|----------|------|-------------|
| `AllowedPatternTransformations` | object | `PatternRotationDefinition` — `IsCardinallyRotatable`, `MirrorX`, `MirrorZ`; which transforms of the rule set are tried |
| `RulesToMatch` | array | `ConnectedBlockPatternRule` entries, all of which must hold |
| `TransformRulesToOrientation` | boolean | Rotate the rules by the block's own orientation before testing |
| `RequireFaceTagsMatchingRoll` | boolean | Require the neighbor's roll to line up when comparing face tags |
| `YawToApplyAddReplacedBlockType` | enum | `Rotation` (`None`/`Ninety`/`OneEighty`/`TwoSeventy`) applied to the resulting block |
| `OnlyOnPlacement` / `OnlyOnUpdate` | boolean | Restrict when the pattern is evaluated |

Each rule in `RulesToMatch` (`ConnectedBlockPatternRule`):

| Property | Type | Description |
|----------|------|-------------|
| `Position` | object | `{X, Y, Z}` block offset from the block being solved (default `0,0,0`) |
| `IncludeOrExclude` | enum | **Required.** `Include` (the neighbor must match) or `Exclude` (must not) |
| `FaceTags` | object | Face tags the neighbor must expose toward this block |
| `BlockTypes` | array | Block type keys the neighbor may be |
| `BlockTypeLists` | array | `Server/BlockTypeList/` asset ids the neighbor must belong to |
| `Shapes` | array | `BlockPattern.BlockEntry` set naming the shape blocks that satisfy the rule |
| `PlacementNormals` | array | `Up`/`Down`/`North`/`East`/`South`/`West` — codec doc: *"Queries the face the block was placed against"* |

> There is no `MaterialName` key on a template asset — that key belongs to the `Roof`
> rule set on the block itself (see [items-blocks.md](items-blocks.md#connected-blocks)).

---

## Patterned Connected Block Rule Sets

0.6.3 adds a second data-driven connected-block system alongside
[`CustomTemplate`](#connected-block-templates). Where a `CustomTemplate` asset hard-codes a
fixed shape vocabulary and matches neighbors by face tag, a **patterned** rule set is a
composable rule tree: boolean `And` / `Or` / `Not` nodes over two leaf predicates (face tags
and neighbor shapes), evaluated against a rotatable pattern of block offsets.

> **Nothing in 0.6.3 ships as a patterned rule set.** `Server/Item/ConnectedBlockRuleSets/`
> — the directory the asset store reads — does not exist in `Assets.zip`, and all ~554
> connected blocks still use `Stair`, `Roof` or `CustomTemplate`. The system is fully wired
> (assets, codecs, client packets) and available to plugins, but there is no shipped example
> to copy. Read the JSON below accordingly: **key names, types and requiredness are
> codec-certain** — they are taken from the codec builders and their own documentation strings,
> the same normative source every JSON page here relies on. What is *not* corroborated is
> **nesting and composition** (how deeply rules and shapes nest in practice) and **runtime
> semantics** (what a given combination actually renders). Trust the keys; test the shapes.

### The two halves

| Half | Class | Where |
|------|-------|-------|
| **Rule set asset** — the shared shape/pattern vocabulary | `PatternedConnectedBlockRuleSetAsset` | `Server/Item/ConnectedBlockRuleSets/<Id>.json` |
| **Per-block binding** — which concrete blocks/states play each shape | `PatternedConnectedBlockRuleSet` | `BlockType.ConnectedBlockRuleSet` with `"Type": "Patterned"` |

Many blocks can share one asset; each supplies its own block/state mapping. The asset store
loads after `TagPattern` and before `BlockType`, and a `ConnectedBlockRuleSetPacketGenerator`
replicates the whole asset (patterns, shapes, face tags) to clients so they can predict the
shape locally.

### The per-block binding

```json
{
  "BlockType": {
    "ConnectedBlockRuleSet": {
      "Type": "Patterned",
      "RuleSetId": "MyFenceRuleSet",
      "TemplatedShapes": {
        "Straight": { "State": "default" },
        "Corner": { "State": "Corner" },
        "Gate": { "Block": "My_Fence_Gate" }
      }
    }
  }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `RuleSetId` | string | **Required.** Id of a `PatternedConnectedBlockRuleSetAsset`; codec doc: *"The name of a ConnectedBlockRuleSetAsset asset"* |
| `TemplatedShapes` | object | **Required.** Shape name → `ConnectedBlockOutput`. `State` picks a state definition on this block (`"default"` = the base block); `Block` names a different block type entirely. Both are optional and may be combined |

`PatternedConnectedBlockRuleSet` resolves this map in both directions when block types load
(`updateCachedBlockTypes`): shape name → concrete block index for output, and block index →
shape name so `getShapeIdForBlockType(int)` can tell a neighbor which shape a placed block is
currently playing. Unlike the other rule-set types it always returns `false` from
`onlyUpdateOnPlacement()`, so patterned blocks re-solve on every neighbor update.

### The rule-set asset

```json
{
  "UpdateMode": "PlaceUpdate",
  "Shapes": {
    "Straight": {
      "Type": "Templated",
      "TemplateId": "Straight",
      "FaceTags": { "East": ["FenceConnection"], "West": ["FenceConnection"] }
    },
    "Corner": {
      "Type": "Templated",
      "TemplateId": "Corner",
      "RelativeRotation": { "Yaw": "Ninety" },
      "FaceTags": { "West": ["FenceConnection"], "South": ["FenceConnection"] }
    }
  },
  "Patterns": [
    {
      "Output": { "ShapeId": "Corner" },
      "TransformRulesWithOrientation": false,
      "RotationTransforms": [ { "Yaw": "All" } ],
      "Rule": {
        "Type": "And",
        "Rules": [
          { "Type": "FaceTag", "MatchType": "All",
            "PositionOffset": { "X": -1, "Y": 0, "Z": 0 },
            "FaceTags": { "East": ["FenceConnection"] } },
          { "Type": "Not",
            "Rule": { "Type": "Shape", "ShapeId": "Straight",
                      "PositionOffset": { "X": 1, "Y": 0, "Z": 0 } } }
        ]
      }
    },
    { "Output": { "ShapeId": "Straight" } }
  ]
}
```

| Key | Type | Description |
|-----|------|-------------|
| `Patterns` | array | **Required.** `ConnectedBlockPatternConfig[]`, tried in array order; the first pattern whose rule passes wins |
| `Shapes` | object | **Required.** Shape name → `ConnectedBlockShapeConfig` (`Type`-tagged, see below) |
| `UpdateMode` | enum | `PlaceUpdate` (default), `UpdatePlaceUpdate`, or `IgnoreUpdates`. Overrides `ConnectedBlockRuleSet.getUpdateMode()` for every block using the asset |

A pattern with **no** `Rule` matches unconditionally — put one last in `Patterns` as the
fallback shape (the `CustomTemplate` equivalent of `DefaultShape`).

### Pattern entries

| Key | Type | Description |
|-----|------|-------------|
| `Rule` | object | **Required in practice** — omit only for the catch-all fallback. A `ConnectedBlockRule` tree |
| `Output` | object | `ConnectedBlockPatternOutput` — `{ "ShapeId": "<key in Shapes>" }`. A pattern with no `Output` is skipped |
| `RotationTransforms` | array | Rotation groups to try; each is `{ "Yaw": …, "Pitch": …, "Roll": … }` with `None` / `Ninety` / `OneEighty` / `TwoSeventy` / `All`. Expanded to the cartesian product; defaults to the identity rotation only |
| `TransformRulesWithOrientation` | boolean | When `true`, each candidate rotation is composed with the block's own placed rotation before the rule is tested |

The winning rotation is what the block is placed at: the result rotation is the matching
transform composed with the output shape's `RelativeRotation`. This is how one rule expresses
all four cardinal variants of a corner — write the rule once for the `Yaw: None` case and list
`"RotationTransforms": [ { "Yaw": "All" } ]`.

### Rules

`Rule` objects are `Type`-tagged (`ConnectedBlockRule.CODEC`). Five types are registered:

| `Type` | Class | Keys | Behavior |
|--------|-------|------|----------|
| `And` | `ConnectedBlockAndRule` | `Rules` (required array) | All children must pass; a `null`/empty list passes |
| `Or` | `ConnectedBlockOrRule` | `Rules` (required array) | Any child passes; an empty list fails |
| `Not` | `ConnectedBlockNotRule` | `Rule` (required) | Inverts the child; a missing child fails |
| `FaceTag` | `ConnectedBlockFaceTagRule` | `PositionOffset`, `FaceTags` (required), `MatchType` (required) | Codec doc: *"A connected block rule that checks if there are face tags present from adjacent blocks"* |
| `Shape` | `ConnectedBlockShapeRule` | `PositionOffset`, `ShapeId` (required), `AllowedRotations` | Codec doc: *"A connected block rule that checks if the neighbor at a position offset resolves to a specific shape"* |

`MatchType` on a face-tag rule is `Any` or `All` (`MatchType` enum) — whether *one* listed
direction must be satisfied or *every* one. Within a single direction the tags always match
as a conjunction, and an empty tag array for a direction never matches.

`AllowedRotations` on a shape rule is a single rotation group (same `Yaw`/`Pitch`/`Roll`
shape as `RotationTransforms` entries); codec doc: *"Rotations the neighbor's shape may have.
When omitted, any rotation matches."*

`PositionOffset` is a `{X, Y, Z}` offset in the pattern's **rotated** frame — the active
rotation transform is applied to it before the lookup, which is what makes one authored rule
cover every listed rotation.

### Shapes

`Shapes` values are `Type`-tagged (`ConnectedBlockShapeConfig.CODEC`). Every shape accepts
two shared keys from `ConnectedBlockShapeConfig.BASE_CODEC`:

| Key | Type | Description |
|-----|------|-------------|
| `FaceTags` | object | `ConnectedBlockFaceTags` — per-direction (`North`/`East`/`South`/`West`/`Up`/`Down`) string arrays this shape advertises to neighbors |
| `RelativeRotation` | object | `BlockRotationConfig` — `{ "Yaw": …, "Pitch": …, "Roll": … }`, each a `Rotation` (`None` default). Composed into the placed rotation and un-applied when comparing a neighbor's face tags |

plus one discriminating key:

| `Type` | Class | Key | Matches a block when… |
|--------|-------|-----|------------------------|
| `Block` | `ConnectedBlockBlockTypeShape` | `Block` (required, validated block key) | its id equals `Block`. Codec doc: *"The block id this shape matches"* |
| `TagPattern` | `ConnectedBlockTagShape` | `TagPattern` (required, validated) | its tags satisfy the named `TagPattern` asset. Codec doc: *"A tag pattern to match blocks"* |
| `Templated` | `ConnectedBlockTemplatedShape` | `TemplateId` (required) | the block's own `TemplatedShapes` map binds it to this shape name. Codec doc: *"Key in the block type's TemplatedShapes map"* |

`Templated` is the shape type that pairs with the `TemplatedShapes` binding above: it lets one
rule-set asset be reused by many block families, each mapping the shared shape names onto its
own blocks/states. `Block` and `TagPattern` are absolute — they match a specific block or tag
pattern regardless of which rule set the neighbor uses.

> **Gotchas**
> - **A shape only participates if the block resolves to it.** `ConnectedBlockContext.getShapeForBlockType`
>   walks the *neighbor's* rule set when the neighbor is also `Patterned`, and falls back to
>   this rule set otherwise. A neighbor on a `Stair`/`Roof`/`CustomTemplate` rule set can only
>   be matched by a `Block` or `TagPattern` shape, never a `Templated` one.
> - **Only a 3×3×3 region is fast.** `ConnectedBlockContext` pre-caches the 27 blocks around
>   the origin; offsets outside that range fall back to a per-lookup chunk-section fetch. Keep
>   `PositionOffset` values within ±1 where you can.
> - **Filler blocks read as air.** A position occupied by the filler half of a multi-block
>   reports `null` block type, so a `FaceTag`/`Shape` rule there fails rather than matching the
>   anchor block.
> - **Order is significance.** `Patterns` is first-match-wins, so list the most specific
>   pattern first and the unconditional fallback last.

### Java surface

```java
// com.hypixel.hytale.server.core.universe.world.connectedblocks.config

// PatternedConnectedBlockRuleSetAsset
static DefaultAssetMap<String, PatternedConnectedBlockRuleSetAsset> getAssetMap()
static AssetStore<String, PatternedConnectedBlockRuleSetAsset,
        DefaultAssetMap<String, PatternedConnectedBlockRuleSetAsset>> getAssetStore()
String getId()
ConnectedBlockPatternConfig[] getPatterns()
Map<String, ConnectedBlockShapeConfig> getShapes()
ConnectedBlockUpdateMode getUpdateMode()
ConnectedBlockRuleSetAsset toPacket()          // com.hypixel.hytale.protocol type

// PatternedConnectedBlockRuleSet  (extends ConnectedBlockRuleSet)
PatternedConnectedBlockRuleSetAsset getRuleSetAsset()
String getShapeIdForBlockType(int blockTypeKey)   // null if this block plays no shape
boolean onlyUpdateOnPlacement()                   // always false
Optional<ConnectedBlocksUtil.ConnectedBlockResult> getConnectedBlockType(
        ChunkStore store, Vector3ic blockCoordinate, BlockType blockType,
        int rotation, Vector3ic placementNormal, boolean isPlacement)

// ConnectedBlockPatternConfig
ConnectedBlockRule getRule()
ConnectedBlockPatternOutput getOutput()
List<RotationTuple> getAllowedTransformRotations()
boolean isTransformRulesWithOrientation()

// ConnectedBlockFaceTags
boolean contains(Vector3i direction, String blockFaceTag)
Set<String> getBlockFaceTags(Vector3i direction)
Map<Vector3ic, HashSet<String>> getBlockFaceTags()
Set<Vector3ic> getDirections()
```

`ConnectedBlockRule` itself is `abstract` with one abstract method,
`boolean check(ConnectedBlockRule.Context)`, plus `toPacket()`. To add a rule type from a
plugin, subclass it, give it a `BuilderCodec`, and register the codec on
`ConnectedBlockRule.CODEC` (a `CodecMapCodec` keyed on `"Type"`) — the same pattern
`ConnectedBlocksModule.setup()` uses for the five built-ins. `ConnectedBlockShapeConfig`
works the same way via its own `CODEC` and `BASE_CODEC`.

`ConnectedBlockRule.Context` (implemented by `ConnectedBlockContext`) is what a custom rule
gets to query:

```java
BlockType getLocalBlockType(Vector3ic position)                  // null = air/filler/unloaded
RotationTuple getLocalRotation(Vector3ic position)
ConnectedBlockShapeConfig getShapeForBlockType(BlockType blockType)
ConnectedBlockShapeConfig getShapeById(String shapeId)
```

---

## Related Documentation

- [Block Definitions](blocks.md) - The `BlockType` JSON that opts a block in
- [Blocks Java API](blocks-java-api.md) - `BlockType`, events and world block access
- [Block Items](items-blocks.md) - Furniture, containers, crafting benches
- [Items](items.md) - Item system and inheritance
