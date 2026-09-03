---
title: "Encounter Manager"
description: "Hytale's Encounter Manager (0.6.3+) — script multi-NPC encounters as Server/EncounterManager JSON using the NPC instruction DSL, with encounter-scoped actions for boss bars, music, audio state, role changes, member tracking and world-event signals."
seo:
  type: TechArticle
---

# Encounter Manager

**Doc type:** Java API + JSON asset format · **Assets:** `Server/EncounterManager` · **Verified against 0.6.3**

New as of 0.6.3. An **encounter** is an invisible manager entity that runs an NPC-style **instruction tree** on
behalf of a group of NPCs: it can trigger nearby spawners, keep a roster of the NPCs it spawned, drive a shared boss
bar and music/audio state for the players fighting them, swap NPC roles mid-fight, and **signal a world event**
when it is done. The format reuses the sensors/actions/instructions DSL documented for NPC roles — see
[NPC Roles → Behavior System (Instructions)](npc-roles.md#behavior-system-instructions) — and adds a handful of
encounter-specific core components. `EncounterManagerPlugin` (`com.hypixel.hytale.builtin.encountermanager`) owns
the runtime.

Shipped examples: `Server/EncounterManager/Example_Encounter.json`, `Example_Boss.json`,
`Example_State_Transitions.json`, `Example_Variant.json` (+ `_Base`), `Example_Macro_*`, `Example_Beacon_*`,
`Example_Portal_Drain.json`, `Example_Block_Sensor.json`, `Example_Points.json`, and
`Test_Signal_Encounter.json` (pairs with `Server/WorldEvent/Event/Test_Signal_Complete.json`). Reusable macros live
in `Server/EncounterManager/Macros/` and `Examples/`.

## Key classes

| Class | Package (`com.hypixel.hytale.builtin.encountermanager…`) | Role |
|-------|-----------------------------------------------------------|------|
| `EncounterManagerPlugin` | (root) | Registers the asset path (`ASSET_PATH = "Server/EncounterManager"`, category `"EncounterManager"`), the builder factory, components, systems and `/encounter` |
| `EncounterManager` | (root) | The component (`EntityStore`, codec id `"EncounterManager"`) on the manager entity: encounter id/index, root `Instruction`, lifecycle hooks |
| `BuilderEncounterManager`, `BuilderEncounterManagerVariant`, `BuilderEncounterManagerAbstract` | (root) | The asset builders behind `"Type": "Generic"` / `"Variant"` |
| `EncounterMembers`, `EncounterAudioState`, `EncounterBossBarState` | (root) | Runtime components: tracked NPC roster (with TTL), desired music/audio axes, boss-bar target |
| `EncounterManagerSystems`, `EncounterMemberSystems` | (root) | Build/activate/tick/lifecycle/teleport systems and the per-tick member + player-state sync |
| `EncounterCommand` | (root) | `/encounter add <encounter>` — spawns a manager entity at the player |
| `npc.Action*`, `npc.EncounterMemberCollector` (+ `npc.builders.*`) | `.npc` | The encounter-specific core components (table below) |

## Asset format — `Server/EncounterManager/<Id>.json`

```json
{
  "Class": "EncounterManager",
  "Type": "Generic",
  "CleanupOnRemove": true,
  "StateTransitions": [
    {
      "States": [ { "From": [], "To": [ "Active" ] } ],
      "Actions": [
        { "Type": "Log", "Message": "[Encounter] --> ACTIVE: round starting" },
        { "Type": "TimerStart", "Name": "RoundTimer", "StartValueRange": [ 5, 5 ], "RestartValueRange": [ 5, 5 ] }
      ]
    }
  ],
  "Instructions": [
    {
      "Sensor": { "Type": "Player", "Range": 8 },
      "Instructions": [
        {
          "Sensor": { "Type": "Any", "Once": true },
          "Actions": [
            { "Type": "TriggerSpawners", "Range": 40, "Count": 2 },
            { "Type": "Log", "Message": "Encounter Manager Example: Spawned first round!" }
          ]
        }
      ]
    }
  ]
}
```

| Key | Meaning |
|-----|---------|
| `Class` | Always `"EncounterManager"` — the builder category (the asset is loaded by the NPC plugin's `BuilderManager`, like a role) |
| `Type` | `"Generic"` for a full definition; `"Variant"` for a derived one (`Reference` + `Modify`, below) |
| `Instructions` | The instruction tree — same `Sensor` / `Actions` / nested `Instructions` / `Continue` / `Once` shape as an NPC role |
| `StateTransitions` | Actions to run when the encounter's **state** changes: each entry has `States` (`[{ "From": [...], "To": [...] }]`, empty `From` = any) and `Actions` |
| `CleanupOnRemove` | Remove the encounter's tracked members when the manager entity is removed (`EncounterManager.isCleanupOnRemove()`) |

### Variants and macros

A **variant** derives from another encounter asset and overrides named parameters:

```json
{
  "Class": "EncounterManager",
  "Type": "Variant",
  "Reference": "Example_Variant_Base",
  "Modify": { "LogMessage": "…overridden…", "TriggerRange": 60 }
}
```

The base declares the parameters it exposes and reads them with `{ "Compute": "<Name>" }` — the same
`Interface` / `Parameters` / `Compute` macro mechanism the NPC instruction DSL uses (see
[NPC Roles → Variants](npc-roles.md#variants)). `Example_Forwarded_Slot_*` and `Encounter_Macro_*` show nested
macros and forwarded slots.

## Encounter-specific core components

Registered by `EncounterManagerPlugin.setup()` via `registerCoreComponentType(...)`, so they are used with
`"Type": "<name>"` inside `Actions` / `Sensor` exactly like the built-in NPC ones:

| `Type` | Kind | Keys | Effect |
|--------|------|------|--------|
| `TriggerSpawners` | action (NPC core, `server.npc.corecomponents.world`) | `Range`, `Count` | Fire up to `Count` NPC spawners within `Range` of the manager — the standard way an encounter brings its NPCs in |
| `EncounterMembers` | sensor | `RememberFor` | Collects NPCs spawned for this encounter into `EncounterMembers` (each stamped with a TTL of `RememberFor` seconds) and reports on them |
| `SetEncounterBossBar` | action | `Name` | Show a boss bar for the encounter's current target to nearby players (`EncounterBossBarState.setTracked`) |
| `ClearEncounterBossBar` | action | — | Hide it (`EncounterBossBarState.clear`) |
| `StartEncounterMusic` | action | `MusicContainer` | Play a music container for players in the encounter (`EncounterAudioState.setDesiredMusicIndex`) |
| `StopEncounterMusic` | action | — | Stop it |
| `SetEncounterAudioState` | action | `AudioState`, `Value`, `Curve`, `FadeMs` | Drive an audio-state axis (e.g. intensity) with a fade (`EncounterAudioState.setDesiredAxisValue`) |
| `ChangeTargetRole` | action | `Role`, `State`, `ChangeAppearance`, `DetachFromSpawning` | Swap the current target NPC's role (and optionally its appearance) — phase changes for bosses |
| `SetTargetNPCInvulnerable` | action | `Invulnerable` | Toggle invulnerability on the target NPC |
| `SignalWorldEvent` | action | `SignalId` | `store.invoke(ref, new WorldEventSignal(null, signalId))` — completes any [world event](world-events.md) `SignalCondition` waiting on that id |

The member/audio/boss-bar state is applied to players by `EncounterMemberSystems.Tick` each tick
(`applyToPlayer` / `revertPlayer` on the two state components), so a player who walks away gets their music and
boss bar reverted without the asset having to do it.

## Runtime and placement

- The manager is an entity carrying `EncounterManager` (`getComponentType()`) plus a `TransformComponent`.
  `EncounterManagerSystems.BuilderSystem.onEntityAdd` resolves the asset by `getEncounterId()` through the NPC
  plugin's `BuilderManager`, refuses anything whose builder category is not `EncounterManager`
  (`Encounter manager references unknown or invalid asset '%s'`), builds the instruction tree
  (`createAndAttach`), gives the entity a `SpawnLineage` if it lacks one, and calls `spawned(holder)`.
- `/encounter add <encounter>` (player-only) creates one at the player's position with a `Nameplate` showing the
  id, `HiddenFromAdventurePlayers`, and the `Encounter_Marker` model (`EncounterManagerPlugin.MARKER_MODEL`) so
  it is visible to builders but not to adventure-mode players. Encounters placed in prefabs are the same entity
  saved with the prefab.
- `EncounterManager` exposes the lifecycle it participates in: `tick(ref, dt, store)`, `spawned(holder)`,
  `unloaded(...)`, `removed(...)`, `teleported(ref, accessor, fromWorld, toWorld)`, plus `getRootInstruction()`,
  `getEncounterId()` / `getEncounterIndex()`, `isBuilt()`, `resetRuntime()`.
- `EncounterMembers`: `stampMember(ref, ttlSeconds)`, `getMemberTtl()`, `isEmpty()`, `clearMembers()`.
- The plugin also registers a **beacon receiver provider** so the NPC `Beacon` sensors/actions can target
  encounter managers (`Example_Beacon_Sender.json` / `Example_Beacon_Receiver.json`).

## Gotchas

- **`Class` must be `EncounterManager`.** The asset is loaded through the NPC builder registry; a role file dropped
  into `Server/EncounterManager` (or vice versa) fails with `Encounter manager references unknown or invalid asset`.
- **Signals are world-wide.** `SignalWorldEvent` sends `WorldEventSignal(null, id)` — every running world event with
  a `SignalCondition` on that id completes, not just "the one nearby". Namespace your signal ids.
- **Members expire.** `EncounterMembers` entries carry a TTL (`RememberFor`); an NPC not re-stamped by the collector
  sensor drops off the roster and stops receiving boss-bar/music sync.
- **Player state is reverted, not cleared.** Music/audio/boss-bar changes are applied and reverted per player each
  tick by `EncounterMemberSystems.Tick`; if you remove the manager entity mid-fight, `CleanupOnRemove` controls
  whether tracked members are cleaned up with it.

> **See also:** [World Events](world-events.md), [NPC Roles](npc-roles.md), [Audio](audio.md), [Prefabs](prefabs.md).
