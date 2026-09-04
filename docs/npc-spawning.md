---
title: "NPC Spawning"
description: "How Hytale spawns NPCs — spawn beacons under Server/NPC/Spawn/Beacons, companion block spawners, manual spawn markers fired by TriggerSpawnMarkers, and the SpawnNPC interaction with its weighted roles, scatter and clearance rules."
seo:
  type: TechArticle
---

# NPC Spawning

**Doc type:** Java API + JSON asset format · **Assets:** `Server/NPC` · **Verified against 0.6.3**

Split out of [npc-roles.md](npc-roles.md) at the 2026-09-04 seam. Four ways NPCs enter the world: **spawn beacons** (ambient, environment-filtered), **companion block spawners** (a block that keeps an NPC alive nearby), **manual spawn markers** (a placed marker that stays inert until an interaction fires it) and the **`SpawnNPC` interaction** (an item or block chain spawning on demand). Role definitions themselves stay in [npc-roles.md](npc-roles.md).

## Spawn Beacons

Spawn beacons configure where and how NPCs spawn in the world. Found in `Server/NPC/Spawn/Beacons/`. A beacon is a plain object (no `Type` wrapper). NPC entries in the `NPCs` array reference roles by an `Id` field, not `Role`.

### Beacon Properties

| Property | Type | Description |
|----------|------|-------------|
| `Environments` | Array | Biome/environment filters (e.g. `Env_Zone1_Caves_Volcanic_T1`) |
| `MinDistanceFromPlayer` | Number | Minimum player distance for spawning |
| `MaxSpawnedNPCs` | Number | Maximum concurrent spawns |
| `ConcurrentSpawnsRange` | Array | `[min, max]` NPCs spawned per cycle |
| `SpawnAfterGameTimeRange` | Array | `[min, max]` game-time durations before spawning (e.g. `PT20M`) |
| `NPCSpawnState` | String | State the NPC starts in when spawned |
| `SpawnRadius` | Number | Spawn area radius |
| `BeaconRadius` | Number | Beacon activation radius |
| `NPCs` | Array | NPC spawn entries — per entry `Id`, `Weight`, and optional `SpawnBlockSet`, `Flock`, `MovementModes`, `SpawnFluidTag`, `EnableSafeSpawning` (`RoleSpawnParameters`) |
| `LightRanges` | Object | Light level requirements (`Light: [min, max]`) |
| `Weight` | Number | Per-entry spawn weight |
| `TargetDistanceFromPlayer` | Number | Preferred distance from the player to place the spawn |
| `NPCIdleDespawnTime` | Number | Seconds an idle spawned NPC survives before despawning |
| `BeaconVacantDespawnGameTime` | String | ISO-8601 game-time duration a vacant beacon keeps its NPCs (e.g. `PT15M`) |
| `TargetSlot` | String | Marked-target slot to pre-fill on the spawned NPC (see [Marked targets](npc-roles.md#marked-targets-lockedtarget-and-the-target-sensor)) |

### Beacon Example

**Example: `Spawn/Beacons/Zone1/Zone1_Cave_Tier1/Zone1_Cave_Volcanic_T1_Goblin.json`** (abridged — the shipped file also sets `NPCIdleDespawnTime`, `BeaconVacantDespawnGameTime` and `TargetDistanceFromPlayer`)

```json
{
    "Environments": [ "Env_Zone1_Caves_Volcanic_T1" ],
    "MinDistanceFromPlayer": 15,
    "MaxSpawnedNPCs": 2,
    "ConcurrentSpawnsRange": [ 1, 2 ],
    "SpawnAfterGameTimeRange": [ "PT20M", "PT60M" ],
    "BeaconRadius": 70,
    "SpawnRadius": 50,
    "NPCs": [
        { "Weight": 75, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Scrapper" },
        { "Weight": 15, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Lobber" },
        { "Weight": 5, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Hermit" },
        { "Weight": 5, "SpawnBlockSet": "Volcanic", "Id": "Goblin_Miner" }
    ],
    "LightRanges": {
        "Light": [ 0, 7 ]
    }
}
```

A minimal beacon can also start an NPC in a chosen state:

```json
{
    "Environments": [],
    "NPCs": [
        { "Weight": 1, "Id": "Edible_Goblin_Scrapper" }
    ],
    "SpawnAfterGameTimeRange": [ "PT5M", "PT10M" ],
    "NPCSpawnState": "Seek"
}
```

### Zone-Based Organization

Spawn beacons are organized by zone (`Zone1` through `Zone4`), with subfolders by tier and biome, plus `Portals` and `Tests` directories and a handful of loose beacons (`Edible_*`, `Goblin_Duke_Phase_*`) at the top level:

```
Server/NPC/Spawn/Beacons/
├── Zone1/
│   ├── Zone1_Cave_Tier1/
│   ├── Zone1_Cave_Tier2/
│   └── ...
├── Zone2/
├── Zone3/
├── Zone4/
├── Portals/
└── Tests/
```

---

## Companion Block Spawners

A spawn beacon spawns NPCs from the *environment*. A **companion block spawner** spawns one
from a *player-built structure*: place a designated block, surround it with the blocks a
recipe asks for, and an NPC moves in and stays as long as the setup survives. New in 0.6.3
(`com.hypixel.hytale.builtin.companionblockspawner`).

The codec's own description is the clearest statement of the contract:

> *"A configuration that spawns a companion NPC when a spawner block and all of its required
> surrounding blocks are present within a radius. Requirement blocks are claimed exclusively
> (two spawners can't share one). While the setup holds, the referenced spawn marker keeps the
> companion alive (re-spawning it on death); breaking the setup despawns it."*

### The recipe asset

**Location:** `Server/NPC/Spawn/CompanionBlockSpawners/<Id>.json`
(`CompanionBlockSpawnerRecipe`, loaded after `SpawnMarker`, `BlockSet`, `BlockType` and `Item`)

**`Server/NPC/Spawn/CompanionBlockSpawners/Debug_Companion_Spawner.json`** — one of the two
shipped examples, verbatim:

```json
{
  "SpawnerBlockTypeKey": "Debug_Companion_Block_Spawner",
  "Radius": 6.0,
  "RequiredBlocks": [
    {
      "MatchBy": "Tag",
      "Value": "Bed",
      "Count": 1
    }
  ],
  "SpawnMarker": "Debug_Companion_Kweebec"
}
```

`Debug_Companion_Spawner_Explicit.json` is the same recipe with
`"MatchBy": "BlockId", "Value": "Debug_Companion_Block_Spawner_Requirement"` — the two files
exist to exercise both match modes.

| Key | Type | Description |
|-----|------|-------------|
| `SpawnerBlockTypeKey` | string | **Required, validated.** Block type key of the block that hosts the companion |
| `Radius` | number | **> 0.** Search radius in blocks for the required blocks (default `1.0`) |
| `RequiredBlocks` | array | **Required, non-empty.** The requirement blocks and their counts |
| `SpawnMarker` | string | **Required, validated.** Id of a `Server/NPC/Spawn/Markers/` asset defining the companion |

Each `RequiredBlocks` entry — *"A required block - how it is matched (MatchBy) and the value
to match (Value) - plus the minimum count of it within the recipe radius."*

| Key | Type | Description |
|-----|------|-------------|
| `MatchBy` | enum | **Required.** `BlockId` (exact block type key) or `Tag` (block tag) |
| `Value` | string | The block key, or a tag such as `"Bed"` / `"Family=Crude"` |
| `Count` | integer | **> 0.** Minimum matching blocks within `Radius` (default `1`) |

The four top-level keys are inheritable, so a family of recipes can share a `Parent` template
the way items do (see [items.md](items.md#inheritance-system)).

The referenced marker is an ordinary spawn-marker asset —
`Server/NPC/Spawn/Markers/Debug_Companion_Kweebec.json` is just:

```json
{
  "NPCs": [
    { "Name": "Temple_Kweebec_Static", "Weight": 1, "RealtimeRespawnTime": 30 }
  ],
  "RealtimeRespawn": true,
  "DeactivationDistance": 48
}
```

### How it resolves

1. **Index.** On start (and whenever recipes, or block types, load or unload)
   `CompanionBlockSpawnerRecipeCompendium` rebuilds: it validates every recipe, expands each
   `Tag` entry to the concrete block keys carrying that tag, and drops any recipe whose spawner
   block, required block or spawn marker does not resolve — logging the reason at `SEVERE`.
2. **Component injection.** The plugin then *injects* a `CompanionBlockSpawnerBlock`
   chunk-store component into the `BlockType` of every participating key — the spawner blocks
   **and** the ingredient blocks. **You do not add anything to the block JSON**; naming a block
   in a recipe is what makes it a block entity.
3. **Evaluation.** `CompanionBlockSpawnerSystems.AddOrRemove` reacts to those block entities
   appearing and disappearing, and `ReconcileTick` re-checks each active spawner roughly every
   30 s (jittered ±25 %). Candidates are found through a KD-tree
   (`CompanionBlockSpawnerSpatialSystem`) keyed on block position.
4. **Claiming.** When every `RequiredBlocks` entry is satisfied, the matching blocks are
   claimed by writing the spawner's position into their `ClaimedByBlock` field. Blocks already
   claimed by another spawner are invisible to this one — that is the "claimed exclusively"
   rule.
5. **Marker placement.** `CompanionBlockSpawnerSupport.createMarker` picks a weighted
   configuration from the marker, resolves its NPC role, and searches outward for a spawnable
   tile — rings 1–4 around the spawner, preferring 2 blocks below through the spawner's own
   level before trying 1 block above. It then creates a `SpawnMarkerEntity` carrying a
   `CompanionSpawnerMarkerReference` back to the spawner block, and the normal spawn-marker
   machinery takes over from there.
6. **Teardown.** Breaking the spawner (or enough of the requirement blocks) clears every claim,
   removes the marker, and removes the companions the marker spawned. A `MarkerHeartbeat`
   entity system sweeps up orphaned markers whose origin block is gone or now points at a
   different marker.

### Java surface

```java
// com.hypixel.hytale.builtin.companionblockspawner
static CompanionBlockSpawnerPlugin CompanionBlockSpawnerPlugin.get()

// config.CompanionBlockSpawnerRecipe
static DefaultAssetMap<String, CompanionBlockSpawnerRecipe> getAssetMap()
String getId()
String getSpawnerBlockTypeKey()
double getRadius()
CompanionBlockSpawnerRecipe.RequiredBlock[] getRequiredBlocks()
String getSpawnMarker()

// CompanionBlockSpawnerBlock  (Component<ChunkStore>, on the spawner and ingredient blocks)
static ComponentType<ChunkStore, CompanionBlockSpawnerBlock> getComponentType()
PersistentRef getMarkerRef()
boolean hasMarker()
Vector3i getClaimedByBlock()

// CompanionSpawnerMarkerReference  (Component<EntityStore>, on the marker entity)
static ComponentType<EntityStore, CompanionSpawnerMarkerReference> getComponentType()
Vector3i getSpawnerPosition()
```

`CompanionBlockSpawnerRecipeCompendium` exposes `getEntryKeySets(recipe)`, `getMaxRadius()`
and `isEmpty()` publicly; the compendium instance itself is package-private, so read recipes
through `CompanionBlockSpawnerRecipe.getAssetMap()`.

> **Gotchas**
> - **The spawner block needs no JSON changes.** `Server/Item/Items/_Debug/Debug_Companion_Block_Spawner.json`
>   is a plain crate — no `BlockEntity`, no flags. The recipe naming it is the whole opt-in.
> - **A recipe with an unresolvable reference is dropped silently from the player's view.**
>   It is logged at `SEVERE` and simply never spawns anything; check the server log rather than
>   assuming the mechanic is broken.
> - **Ingredient blocks are consumed exclusively.** Two spawners cannot share one bed. A second
>   spawner in range of the same requirement blocks will never activate until the first one is
>   broken.
> - **World config still gates the spawn.** If the world has `SpawningNPC` or
>   `SpawnMarkersEnabled` off, the marker is created but no companion appears; the module logs
>   this explicitly at `FINE`.
> - **The marker needs a free tile within 4 blocks.** If `SpawningContext` finds nowhere
>   spawnable in rings 1–4 (and within −2/+1 blocks of the spawner's height), no marker is
>   created and the spawner stays inactive.

---

## SpawnNPC Interaction

**Package:** `com.hypixel.hytale.server.npc.interactions.SpawnNPCInteraction` · registered by
`NPCPlugin`

Spawns NPCs from an interaction chain — the egg-spawner items, the Scarak eggsack burst, and the
spellbook all use it. Codec doc: "Spawns an NPC on the block that is being interacted with."
Extends [SimpleBlockInteraction](interactions.md#simpleblockinteraction), so the spawn is
positioned relative to the **targeted block**, not the interacting entity.

**None of its 14 keys is required** — neither by a `true` third argument nor by
`Validators.nonNull()`. That is deliberate rather than lax: `EntityId` can be omitted because
`WeightedEntityIds` supplies the role instead. Several keys are still validated at load, so
"optional" does not mean "unconstrained".

| Property | Type | Default | Description / load-time validation |
|----------|------|---------|-------------------------------------|
| `EntityId` | string | — | Role id of the NPC to spawn. Validated by `NPCRoleValidator`, so a bad id fails at load even though the key is optional |
| `WeightedEntityIds` | array | — | Weighted roles; one entry is picked per spawn roll. **Supersedes `EntityId`** when present. Entry shape below |
| `SpawnOffset` | vec3 | `0,0,0` | Offset from the block's centre, rotated by the block's rotation |
| `SpawnYawOffset` | float | `0` | Yaw offset added to the block's yaw. **In degrees** — see the gotcha below |
| `SpawnChance` | float | `1.0` | Probability the spawn happens at all |
| `AlternateSpawnMaxSearchDistance` | int | `0` | On `FAIL_INVALID_POSITION`, try adjacent columns along the horizontal cardinal axis toward the player, up to this many block steps. `0` disables. Distance is along that axis only, not a Euclidean radius. Validated `min(0)` |
| `SpawnCount` | int[2] | `[1,1]` | `[min, max]` spawns per trigger; with `WeightedEntityIds` it is the number of *rolls*. Validated: exactly 2 entries, each in `1..100`, weakly monotonic — so `[5,2]` fails at load |
| `DistanceRange` | double[2] | `[0,0]` | `[min, max]` random horizontal scatter per NPC. Validated: exactly 2 entries, each `>= 0`, weakly monotonic |
| `SpawnState` | string | — | Optional state to set on the spawned NPC |
| `SpawnSubState` | string | — | Optional sub-state; **only used when `SpawnState` is also set** |
| `SpawnVelocity` | double | `0` | Random horizontal velocity magnitude in a random XZ direction. `0` disables |
| `AllowMidAirSpawn` | boolean | `false` | Still validates physical space but skips the ground-seeking column search on failure — for NPCs emerging from hanging blocks |
| `CenterHitboxOnPosition` | boolean | `false` | Centre the collision box on the computed position rather than placing its feet there |
| `RequireFullCubeClearance` | boolean | **`true`** | When true every non-air block blocks the spawn. When false only full-cube blocks do, letting NPCs emerge past ropes, plants and cocoons. The only boolean here defaulting true |

### WeightedEntityIds entries

Each entry is a `WeightedNPCSpawn` with **three** keys, and it is the clearest example in the
codebase of requiredness arriving in two different forms within one chain:

| Property | Type | Required by | Description |
|----------|------|-------------|-------------|
| `Id` | string | `Validators.nonNull()` **only** | Role id of the NPC. Also validated by `NPCRoleValidator` |
| `Weight` | double | **both** a `true` third argument to `KeyedCodec` *and* `Validators.nonNull()` | Relative weight against the sum of all weights. Validated `greaterThan(0.0)` |
| `CountRange` | int[2] | not required | `[min, max]` of *this* entry to spawn when picked. Validated: 2 entries, each `1..100`, weakly monotonic |

Both forms have to be read: a key can be required by the codec's third argument, by a
`Validators.nonNull()` that attaches *after* `append(...)` closes, or — as `Weight` shows — by
both at once.

The simplest shipped use pins one role and lifts it half a block off the target
(`Server/Item/Items/EggSpawner/Egg_Spawner_Trork.json`):

```json
{
  "Type": "SpawnNPC",
  "EntityId": "Trork_Warrior",
  "SpawnOffset": { "X": 0, "Y": 0.5, "Z": 0 }
}
```

`Server/Item/Interactions/SpawnNPC/` ships a reusable chain built from
[`Replace`](interactions-flow.md#replace) slots, so an item customises the spawn through
`InteractionVars` rather than by redefining the interaction — `SpawnNPC_BlockCondition` (default:
no block restriction; a `Water_Source`/`Water` variant ships alongside), `SpawnNPC_Effects`
(default: a `Throw` animation) and `SpawnNPC_Entity`, which the chain's own comment marks as the
one an item **must** provide. The chain ends in a `ModifyInventory` that consumes one item.

Behavior notes:

- **Spawn position** is `blockCentre + rotate(SpawnOffset, blockRotation) + blockPosition`, and
  rotation is the block's yaw plus `SpawnYawOffset`. A block with no rotation still contributes
  its centre, so `SpawnOffset` of `0,0,0` spawns inside the block.
- **`SpawnCount` means rolls, not NPCs, once `WeightedEntityIds` is set.** The codec says so
  itself — "With `WeightedEntityIds` this is the number of weighted rolls (each roll spawns the
  picked entry's own `CountRange`)". So `SpawnCount` `[2,2]` against entries with `CountRange`
  `[3,3]` yields six NPCs, not two.

> **Gotcha — `SpawnYawOffset` is in degrees, and the engine's own codec documentation says
> radians.** The implementation applies `Math.toRadians(spawnYawOffset)` before adding it to the
> block's yaw, so the value is degrees; the codec's description string ("The yaw rotation offset
> in radians…") is wrong, and it is the string an asset editor would surface. Both shipped assets
> that use the key — `Block_Scarack_Eggsacks_Burst.json` and `Block_Coffin_Open.json` — pass
> `"SpawnYawOffset": 180` to face the spawned NPC away from the block, and 2 of 2 uses only make
> sense as degrees. Trusting the codec doc puts the NPC out by a factor of about 57.

---

## Manual Spawn Markers

Spawn markers are the fourth spawn source: assets under `Server/NPC/Spawn/Markers/`, placed by
worldgen and prefabs, each carrying a weighted `NPCs` list. Most re-arm on their own timer. A marker
that sets **`"ManualTrigger": true`** never does — it sits inert until something fires it, and
`TriggerSpawnMarkers` is what fires it. **Nine of the shipped markers are manual**:
`Skeleton_Knight_Manual`, `Spirit_Root_Manual`, `Trork_Chieftain_Backup`,
`Outlander_Marauder_Backup`, `Welcome_Animal`, `Test_Boss_Marker`, `Test_Manual_Marker`,
`Test_Objective_Spawn_Marker` and `Test_Skeleton_Stones`.

The marker asset itself
(`com.hypixel.hytale.server.spawning.assets.spawnmarker.config.SpawnMarker`) is not otherwise
documented in this handbook — `ManualTrigger` is described here only because it is the key that
decides whether the interaction can see a marker at all.

### TriggerSpawnMarkers

**Package:** `com.hypixel.hytale.server.spawning.interactions.TriggerSpawnMarkersInteraction` ·
registered by `SpawningPlugin`

Fires manual spawn markers around the **entity running the interaction**. It extends
[SimpleInstantInteraction](interactions.md#simpleinstantinteraction) and reads
`context.getEntity()`, so the search is a sphere centred on that entity's own position — unlike
[`SpawnNPC`](#spawnnpc-interaction), nothing here is relative to a targeted block.

| Property | Type | Default | Description / load-time validation |
|----------|------|---------|-------------------------------------|
| `MarkerType` | string | — | Marker asset id to fire, validated against the `SpawnMarker` asset map so a bad id fails at load. **Omit it to fire every manual marker in range**, whatever its type |
| `Range` | double | `10.0` | Search radius in blocks. Validated `greaterThan(0.0)` |
| `Count` | int | `0` | Maximum number of markers to fire. Validated `greaterThanOrEqual(0)` |

**None of the three is required** — neither by a `true` third argument to `KeyedCodec` nor by
`Validators.nonNull()`. The defaults are a live configuration, not a degenerate one: with no keys at
all the interaction fires every manual marker within 10 blocks.

Two of the three shipped uses are summon chains that run the interaction from inside a
[`Serial`](interactions-flow.md#serial) block behind an animation:

```json
{
  "Type": "TriggerSpawnMarkers",
  "MarkerType": "Spirit_Root_Manual",
  "Range": 30
}
```

`Hedera_Summon.json` and `Skeleton_Burnt_Praetorian_Summon.json` each pin one `MarkerType` at
`Range` 30. The third, the debug item `Test_Spawn_Marker_Trigger.json`, is not a chain at all — it
runs the interaction straight from `Primary` and sets `Range` only, so it fires whatever manual
markers happen to be nearby.

Behavior notes:

- **A marker is eligible only if all three tests pass**: `ManualTrigger` is true, its centre is
  within `Range` (compared as squared distance, so `Range` is exact), and its id equals `MarkerType`
  when that key is set. The coarse spatial query widens to `(int) Range + 1` first and the exact
  test then narrows it back, so a fractional `Range` is not quietly rounded up.
- **`Count` picks at random, not by distance.** Above zero, the eligible markers are reservoir-sampled
  down to `Count`, so `Count: 1` inside a cluster of five fires an arbitrary one of them rather than
  the closest.
- **A marker that already has live NPCs will not re-fire.** `SpawnMarkerEntity.trigger()` returns
  false while its spawn count is above zero, so repeatedly using a summon item does not stack more
  NPCs onto the same marker — it re-arms only as the ones it spawned are removed.

> **Gotcha — `"Count": 0` means *all* markers, not *no* markers.** Zero is the default and the
> "unlimited" sentinel at once: the implementation branches on `count == 0` into a loop over every
> eligible marker, and only the `count > 0` branch samples a subset. Writing `"Count": 0` to disable
> a trigger does the opposite of what it reads like, and the validator (`greaterThanOrEqual(0)`)
> accepts it without comment. There is no value that fires nothing; omit the interaction instead.
