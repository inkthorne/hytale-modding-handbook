---
title: "Deployables"
description: "Hytale's deployable system — player-placed turrets, AoE totems and traps. The DeployableConfig registry (Trap, TrapSpawner, Aoe, Turret), the three SpawnDeployable interactions, the owner/projectile components and the DeployableSpawner asset store."
seo:
  type: TechArticle
---

# Deployables

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item`, `Server/ProjectileConfigs` · **Verified against 0.6.3**

A **deployable** is a temporary, player-owned entity placed into the world by an interaction — the
crossbow turret, the healing and slowness totems, the fire trap. `DeployablesPlugin`
(`com.hypixel.hytale.builtin.deployables`) owns the runtime. Like [mounts](mounts.md) it is a
bundled plugin, not a core one, so none of these `Type` strings exist unless it is loaded.

The shape is always the same: an interaction carries a **`Config`** object, that config's `"Type"`
selects one of four behaviours, and the interaction decides only *where* the thing lands.

> **Two classes are named `DeployableConfig`.** `com.hypixel.hytale.builtin.deployables.config.DeployableConfig`
> is the codec-bearing one this page documents; `com.hypixel.hytale.protocol.DeployableConfig` is
> the wire form and carries no codec. The bare simple name is ambiguous in any context that could
> mean either.

## Packages and key classes

| Class | Package (`com.hypixel.hytale.builtin.deployables…`) | Role |
|-------|-------------------------------------------------------|------|
| `DeployablesPlugin` | (root) | Registers the four configs, three interactions, four components, three systems and the `DeployableSpawner` asset store |
| `DeployableConfig` | `config` | Abstract base; 19 shared keys and the `"Type"` discriminator |
| `DeployableTrapConfig` / `DeployableTrapSpawnerConfig` / `DeployableAoeConfig` / `DeployableTurretConfig` | `config` | The four registered behaviours |
| `DeployableSpawner` | `config` | Asset store under `DeployableSpawners` |
| `DeployablesUtils` | (root) | `spawnDeployable(commandBuffer, store, config, deployer, position, rotation, face)` — the single spawn entry point all three interactions call |
| `DeployableComponent` | `component` | The deployable entity itself |
| `DeployableOwnerComponent` | `component` | On the **deployer**, tracking what they have out |
| `DeployableProjectileComponent` / `DeployableProjectileShooterComponent` | `component` | Turret projectiles and the turret that fired them |
| `DeployablesSystem` | `system` | `DeployableTicker`, `DeployableRegisterer`, `DeployableOwnerTicker` |

## The four config types

All four extend the same base, so every key in the base table below is legal on any of them.

### Shared keys (`DeployableConfig`)

**Package:** `com.hypixel.hytale.builtin.deployables.config.DeployableConfig`

Nineteen keys; **`Model` is the only required one** (`Validators.nonNull()` plus an
`ModelAsset` validator).

| Property | Type | Description |
|----------|------|-------------|
| `Id` | string | Identifier used for live-count bookkeeping |
| `Model` | string | **Required.** Model asset for the deployed entity |
| `ModelPreview` | string | Model shown while aiming the placement |
| `ModelScale` | float | Scale multiplier |
| `MaxLiveCount` | int | How many of this `Id` one owner may have out at once |
| `LiveDuration` | float | Seconds before it despawns |
| `Invulnerable` | boolean | Ignore incoming damage |
| `Stats` | object | Map of stat id → `StatConfig` (below) — this is how a turret gets health |
| `HitboxCollisionConfig` | string | Named collision config, validated against `HitboxCollisionConfig` |
| `AllowPlaceOnWalls` | boolean | Permit non-floor surfaces. Read by `SpawnDeployableFromRaycast` |
| `CountTowardsGlobalLimit` | boolean | Whether it counts against the global deployable cap |
| `DeploySoundEventId` | string | One-shot mono sound on deploy |
| `DespawnSoundEventId` | string | One-shot mono sound on despawn |
| `DieSoundEventId` | string | One-shot mono sound on death |
| `AmbientSoundEventId` | string | **Looping** mono sound while alive |
| `SpawnParticles` / `DespawnParticles` | array | Particle systems on spawn / despawn |
| `DebugVisuals` / `WireframeDebugVisuals` | boolean | Development rendering aids |

The four sound keys carry validators that constrain the *kind* of sound event: the three one-shots
require `SoundEventValidators.ONESHOT`, `AmbientSoundEventId` requires `LOOPING`, and all four
require `MONO`. A stereo or looping event in a one-shot slot fails at asset load, not at play time.

#### StatConfig (nested)

`Stats` maps a stat id to a `StatConfig`, a nested class with a private codec — it is not a
registered type of its own, and has two keys:

| Property | Type | Description |
|----------|------|-------------|
| `Max` | float | **Required** (`Validators.nonNull()`), and additionally validated `greaterThan` |
| `Initial` | float | Starting value; optional |

A key table for `Stats` alone would miss both the requiredness and the range constraint, which is
why it is spelled out here. The shipped turret uses `"Stats": { "Health": { "Initial": 25, "Max": 25 } }`.

### `"Type": "Aoe"`

**Package:** `com.hypixel.hytale.builtin.deployables.config.DeployableAoeConfig` · 12 own keys, **none required**

A damage-over-time volume that can grow or shrink.

| Property | Type | Description |
|----------|------|-------------|
| `Shape` | string | Volume shape (`Cylinder` in the shipped asset) |
| `StartRadius` / `EndRadius` | float | Radius at spawn and at the end of `RadiusChangeTime` |
| `Height` | float | Volume height |
| `RadiusChangeTime` | float | Seconds to interpolate from start to end radius |
| `DamageInterval` | float | Seconds between damage ticks |
| `DamageAmount` | float | Damage per tick |
| `DamageCause` | string | Damage cause id |
| `ApplyEffects` | array | Entity effects applied on each tick |
| `AttackOwner` / `AttackTeam` / `AttackEnemies` | boolean | Who the volume is allowed to hit |

### `"Type": "Turret"`

**Package:** `com.hypixel.hytale.builtin.deployables.config.DeployableTurretConfig` · 19 own keys, **one required** — `ProjectileConfig`

An auto-targeting shooter.

| Property | Type | Description |
|----------|------|-------------|
| `ProjectileConfig` | object | **Required.** The projectile it fires — see [projectiles.md](projectiles.md) |
| `ProjectileSpawnOffsets` | map | Named spawn offsets for the projectile. **Not required** — see the gotcha below |
| `DetectionRadius` / `TrackableRadius` | float | Where it acquires targets, and how far it keeps tracking one |
| `RotationSpeed` | float | How fast it turns to face a target |
| `PreferOwnerTarget` | boolean | Prefer whatever the owner is attacking |
| `DeployDelay` | float | Seconds after landing before it becomes active |
| `Ammo` | int | Total shots; each projectile consumes one |
| `ShotInterval` | float | Seconds between shots within a burst |
| `BurstCount` / `BurstCooldown` | int / float | Shots per burst, and the pause after one |
| `ProjectileDamage` | float | Damage per projectile |
| `Knockback` | object | Knockback applied on hit |
| `TargetOffset` | vec3 | Aim point relative to the target's origin |
| `CanShootOwner` | boolean | Whether the owner is a valid target |
| `DoLineOfSightTest` | boolean | Require an unobstructed line before firing |
| `RespectTeams` | boolean | Exclude teammates |
| `ProjectileHitWorldSoundEventId` / `ProjectileHitLocalSoundEventId` | string | Impact sounds |

> **Gotcha — `ProjectileSpawnOffsets` is *not* required, and its declaration looks as if it is.**
> It is written `new KeyedCodec("ProjectileSpawnOffsets", new MapCodec<Vector3d, Object2ObjectOpenHashMap>(…, true))`
> — two arguments, with the trailing `true` belonging to the inner `MapCodec`, not to the
> `KeyedCodec`. The visually identical three-argument form *would* make a key required. Reading
> the trailing `true` as the outer codec's third argument is a documented trap in both directions;
> only `ProjectileConfig`, which carries `Validators.nonNull()`, is required here.

### `"Type": "Trap"` and `"Type": "TrapSpawner"`

**Packages:** `…config.DeployableTrapConfig` (3 own keys, none required) and
`…config.DeployableTrapSpawnerConfig` (1 key, required)

| Type | Property | Description |
|------|----------|-------------|
| `Trap` | `FuzeDuration` | Seconds between trigger and effect |
| `Trap` | `ActiveDuration` | How long it stays armed |
| `Trap` | `DestroyOnTriggered` | Remove the trap once it fires |
| `TrapSpawner` | `DeployableConfig` | **Required.** The nested config this spawner deploys |

> **Neither has a shipped use.** Of the four registered types, only `Aoe` and `Turret` appear in
> 0.6.3 assets — the fire trap is an `Aoe`, despite its name and file path. `Trap` and
> `TrapSpawner` are registered, loadable and undocumented by example, so treat the key lists above
> as the codec's word rather than as patterns validated by shipped content.

## The three interactions

Each carries the same `Config`; they differ only in where the deployable lands.

| `Type` | Placement | Own keys |
|--------|-----------|----------|
| `SpawnDeployableFromRaycast` | Where the player is aiming, client-supplied | `Config` (**required**), `PreviewStatConditions`, `MaxPlacementDistance` |
| `SpawnDeployableAtHitLocation` | The chain's `hitLocation` / `hitNormal` | `Config` (**required**) |
| `SpawnDeployableAtLocation` | A fixed offset from the entity or the target block | `Config`, `Offset`, `RotationYaw`, `OriginSource`, `OffsetRotationMode`, `DeployableRotationMode` — **all six required** |

`SpawnDeployableAtLocation` is unusual in requiring every one of its keys: all six carry
`Validators.nonNull()`. `OriginSource`, `OffsetRotationMode` and `DeployableRotationMode` are the
enums documented in [interactions.md](interactions.md#originsource-enum).

`SpawnDeployableFromRaycast` does the most work of the three:

- **It can refuse to place.** `PreviewStatConditions` is a map of stat id → cost checked before
  anything spawns; if the deployer cannot afford it the interaction ends `Failed`.
- **Distance and surface are enforced together.** The raycast hit must be within
  `MaxPlacementDistance`, and unless the config sets `AllowPlaceOnWalls` the surface normal must be
  within `0.01` of straight up. Failing either simply spawns nothing — the interaction does *not*
  end `Failed` in that case, so a `Failed` branch will not fire on a rejected surface.
- With no raycast hit it falls back to the deployer's own position; with no raycast **normal** it
  returns without spawning.

The fire trap shows the whole pattern, config inline
(`Server/Item/Interactions/Weapons/Stick/Magic/Trap/Weapon_Stick_Fire_Spawn_Trap.json`, abridged):

```json
{
  "Type": "SpawnDeployableFromRaycast",
  "Config": {
    "Type": "Aoe",
    "Id": "FireTrap",
    "Model": "Deployable_Fire_Trap",
    "ModelPreview": "Deployable_Fire_Trap_Preview",
    "MaxLiveCount": 3,
    "LiveDuration": 5,
    "Invulnerable": true,
    "Shape": "Cylinder",
    "StartRadius": 1,
    "EndRadius": 5,
    "Height": 2,
    "RadiusChangeTime": 4,
    "DamageInterval": 2,
    "DamageAmount": 1,
    "DamageCause": "Fire",
    "ApplyEffects": ["Flame_Staff_Burn"],
    "AttackOwner": false,
    "AttackTeam": false
  },
  "MaxPlacementDistance": 20,
  "PreviewStatConditions": { "DeployablePreview": 1 }
}
```

The turret arrives differently — its config rides on a **projectile's** `ProjectileMiss` chain, so
the turret is deployed where the thrown item lands
(`Server/ProjectileConfigs/Weapons/Deployables/Projectile_Config_Turret_Deploy.json`):

```json
{
  "Interactions": {
    "ProjectileMiss": {
      "Interactions": [
        {
          "Type": "SpawnDeployableAtHitLocation",
          "Config": {
            "Type": "Turret",
            "Id": "Turret",
            "Model": "Crossbow_Turret",
            "HitboxCollisionConfig": "HardCollision",
            "DeployDelay": 2,
            "LiveDuration": 14,
            "DetectionRadius": 20,
            "TrackableRadius": 25,
            "Stats": { "Health": { "Initial": 25, "Max": 25 } }
          }
        }
      ]
    }
  }
}
```

## Components and systems

| Component | On | Notes |
|-----------|----|-------|
| `DeployableComponent` | the deployable | Its config, owner and remaining lifetime |
| `DeployableOwnerComponent` | the **deployer** | What they have out; how `MaxLiveCount` is enforced |
| `DeployableProjectileComponent` | a turret projectile | Marks a projectile as turret-fired |
| `DeployableProjectileShooterComponent` | the turret | Links back to projectiles in flight |

Three systems drive them: `DeployableTicker` (lifetime, AoE damage intervals, turret targeting and
firing), `DeployableRegisterer` (registration on spawn) and `DeployableOwnerTicker` (owner-side
bookkeeping and expiry).

The shipped items that use all this are `Weapon_Deployable_Healing_Totem`,
`Weapon_Deployable_Slowness_Totem` and `Weapon_Deployable_Turret`, plus the debug
`Debug_Stick_Spawn_Deployable`.

## Related

- [Interactions API](interactions.md) — the three `SpawnDeployable*` types in the full registry
- [Projectiles](projectiles.md) — `ProjectileConfig`, which the turret requires
- [Mounts & Seating](mounts.md) — the other bundled subsystem in this shape
- [Effects & Stats](effects-stats.md) — the ids used by `Stats` and `ApplyEffects`
