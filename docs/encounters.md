---
title: "Encounter Manager"
description: "Hytale's Encounter Manager (0.6.3+) — script multi-NPC encounters as Server/EncounterManager JSON using the NPC instruction DSL, with encounter-scoped actions for boss bars, music, audio state, weather, rewards, role changes, member tracking and world-event signals."
seo:
  type: TechArticle
---

# Encounter Manager

**Doc type:** Java API + JSON asset format · **Assets:** `Server/EncounterManager` · **Verified against 0.7.2**

New as of 0.6.3. An **encounter** is an invisible manager entity that runs an NPC-style **instruction tree** on
behalf of a group of NPCs: it can trigger nearby spawn markers, keep a roster of the **players** taking part, drive
a shared boss bar and music/audio state for them, swap NPC roles mid-fight, and **signal a world event** when it is
done. The format reuses the sensors/actions/instructions DSL documented for NPC roles — see
[NPC Roles → Behavior System (Instructions)](npc-roles.md#behavior-system-instructions) — and adds a handful of
encounter-specific core components. `EncounterManagerPlugin` (`com.hypixel.hytale.builtin.encountermanager`) owns
the runtime.

Shipped examples live in `Server/EncounterManager/Examples/`: `Example_Encounter.json`, `Example_Boss.json`,
`Example_State_Transitions.json`, `Example_Variant.json` (+ `_Base`), `Example_Macro_*`, `Example_Beacon_*`,
`Example_Portal_Drain.json`, `Example_Block_Sensor.json`, `Example_Points.json`, and
`Test_Signal_Encounter.json` (pairs with `Server/WorldEvent/Event/Test_Signal_Complete.json`). The game's own
encounters sit beside them in topic folders — `Goblin_Gobliterator/`, `Dungeon_Feastmaster/`, `Environment/`,
`Music/`, `NPC/Elite/`, and `WorldEvent/` (the encounters world events spawn). Reusable macros live in `Macros/`,
in each topic folder's own `Macros/`, and in `Examples/`. (Before 0.7.2 the examples sat at the top level of
`Server/EncounterManager/`; they moved into `Examples/` with their ids unchanged.)

## Key classes

| Class | Package (`com.hypixel.hytale.builtin.encountermanager…`) | Role |
|-------|-----------------------------------------------------------|------|
| `EncounterManagerPlugin` | (root) | Registers the asset path (`ASSET_PATH = "Server/EncounterManager"`, category `"EncounterManager"`), the builder factory, components, systems and `/encounter` |
| `EncounterManager` | (root) | The component (`EntityStore`, codec id `"EncounterManager"`) on the manager entity: encounter id/index, root `Instruction`, lifecycle hooks |
| `BuilderEncounterManager`, `BuilderEncounterManagerAbstract`, `BuilderEncounterManagerVariant` | (root) | The asset builders behind `"Type"`: `"Generic"` / `"Abstract"` / `"Variant"` |
| `EncounterMembers` | (root) | Runtime component: the roster of **players** taking part, each with a TTL |
| `EncounterAudioState`, `EncounterBossBarState`, `EncounterWeatherState` | (root) | The roster's **consumers** (`EncounterMemberConsumer`, a `Component<EntityStore>` since 0.7.2): the desired music/audio axes, the boss-bar target, and the weather override. `EncounterManagerPlugin.getMemberConsumerTypes()` lists all three |
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
| `Type` | `"Generic"` — a complete, spawnable encounter. `"Abstract"` — a base that exists only to be referenced by a `Variant`; same shape as `Generic` but not spawnable on its own. `"Variant"` — a derived one (`Reference` + `Modify`, below). All three are registered by `EncounterManagerPlugin.setup()`; the shipped tree uses 25 `Generic`, 5 `Abstract`, 16 `Variant` |
| `Instructions` | The instruction tree — same `Sensor` / `Actions` / nested `Instructions` / `Continue` / `Once` shape as an NPC role |
| `StartState`, `Debug` | Shared with NPC roles (both come from `SupportConfigBuilder`): the state the encounter begins in — which is what makes `StateTransitions` meaningful — and a debug label. See [NPC Roles](npc-roles.md#states) |
| `StateTransitions` | Actions to run when the encounter's **state** changes: each entry has `States` (`[{ "From": [...], "To": [...] }]`) and `Actions`. An absent **or** empty `From` *or* `To` means "any main state", and a pairing where from and to resolve to the same state is skipped — a transition never fires onto itself |
| `CleanupOnRemove` | Default **`false`**. "Remove everything this encounter spawned when the encounter is removed" — when true, removing the manager entity also removes **every entity sharing its spawn lineage**, transitively (what it spawned, and what those spawned in turn). **Does not apply when the encounter merely unloads** — only on actual removal. This is what the `SpawnLineage` below is for |

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

The base declares the parameters it exposes in a `Parameters` block and reads them with `{ "Compute": "<Name>" }` —
the same `Interface` / `Parameters` / `Compute` macro mechanism the NPC instruction DSL uses (see
[NPC Roles → Variants](npc-roles.md#variants)). A base written purely to be derived from is
**`"Type": "Abstract"`**, not `"Generic"` — the shipped `Example_Variant_Base.json` referenced above is exactly
that. `Example_Forwarded_Slot_*` and `Encounter_Macro_*` show nested macros and forwarded slots.

## Encounter-specific core components

Registered by `EncounterManagerPlugin.setup()` via `registerCoreComponentType(...)`: eleven actions and the
`EncounterMembers` collector. **All twelve are restricted to encounter instruction contexts**
(`requireInstructionType(InstructionType.Encounter)`) — they cannot be used in an NPC role. Eleven of them are legal
only inside the encounter's `Instructions` tree; `SignalWorldEvent` alone also accepts
`InstructionType.EncounterStateTransitions`, so it is **the only one of these usable inside a `StateTransitions` →
`Actions` block**.

The table also lists `TriggerSpawners`, because it is the standard way an encounter brings its NPCs in. It is an
ordinary NPC core action registered by `NPCPlugin`, carries no instruction-type restriction, and is legal in an NPC
role too.

| `Type` | Keys (required / *default*) | Effect |
|--------|------------------------------|--------|
| `TriggerSpawners` | `Range` **required** (>0); `SpawnMarker` *none*; `Count` *0*; `TargetSlot` *none*; `Rebind` *false* | Trigger NPC spawn markers within `Range` of the manager — the standard way an encounter brings its NPCs in. See the note below on `Count` and on binding a target |
| `SetEncounterBossBar` | `Name` *none*; `HardMode` *false* | Show a boss bar for the encounter's current target to the tracked members (`EncounterBossBarState.setTracked`). `Name` is a localization key; **without it the target's display name is used, which is not translated**. `HardMode` marks the bar as hard mode; each call sets it afresh, so a later `SetEncounterBossBar` without it turns hard mode back off |
| `ClearEncounterBossBar` | — | Hide it (`EncounterBossBarState.clear`) |
| `StartEncounterMusic` | `MusicContainer` **required** | Play a music container for the tracked members (`EncounterAudioState.setDesiredMusicIndex`) |
| `StopEncounterMusic` | — | Stop it |
| `SetEncounterAudioState` | `AudioState` **required**, `Value` **required**; `FadeMs` *-1*; `Curve` *none* | Drive an audio-state axis (e.g. intensity) for the tracked members (`EncounterAudioState.setDesiredAxisValue`). `AudioState` must be a **Server-authority** axis (validator-enforced); `FadeMs` of `-1` means "use the axis's own transition"; `Curve` only applies when `FadeMs` is set |
| `ChangeTargetRole` | `Role` **required**; `ChangeAppearance` ***true***; `State` *none*; `DetachFromSpawning` *false* | Swap the current target NPC's role — phase changes for bosses. `State` sets a main state on the target after the change; `DetachFromSpawning` removes it from world-spawn population tracking and despawning |
| `SetTargetNPCInvulnerable` | `Invulnerable` **required** | Toggle invulnerability on the target NPC |
| `SetEncounterWeather` | `Weather` **required**; `TransitionSeconds` *2.0* (>0) | Override the weather each tracked member sees (`EncounterWeatherState.setDesiredWeather`). `Weather` is a `Server/Weathers` asset id; `TransitionSeconds` is the sky's cross-fade, both into this weather and back out of it. A player whose weather override another encounter already holds keeps that one (`WeatherTracker.tryClaimOverride` is first-come) |
| `ClearEncounterWeather` | — | Return the tracked members to their normal weather (`EncounterWeatherState.clearDesiredWeather`) |
| `GrantReward` | `Reward` **required** | Grant a reward to every tracked member (`RewardModule.grantReward` per member). `Reward` is a `Server/Rewards` asset id, checked at load by `RewardExistsValidator` — see [Rewards](#rewards) |
| `SignalWorldEvent` | `SignalId` **required**, non-empty | `store.invoke(ref, new WorldEventSignal(null, signalId))` — completes any [world event](world-events.md) `SignalCondition` waiting on that id |

> **`Count` defaults to 0, and 0 means *all*.** `TriggerSpawners` without an explicit `Count` fires *every* matching
> spawn marker in `Range`, not one. Set `Count` deliberately.

### Binding the target: `TargetSlot`

`SetEncounterBossBar`, `ChangeTargetRole` and `SetTargetNPCInvulnerable` all act on "the target", which is a
**marked-target slot** (the NPC role system's mechanism — see
[NPC Roles → Marked targets](npc-roles.md#marked-targets-lockedtarget-and-the-target-sensor)). An encounter fills
that slot when it spawns the NPC: `TriggerSpawners` takes `TargetSlot` ("a target slot to place the first spawned
NPC in") and `Rebind` ("whether the target slot rebinds to the spawned entity, so it survives short reloads or role
changes"). `Example_Boss.json` uses `"TargetSlot": "Boss", "Rebind": true` and every later boss action resolves
through it.

### Tracking the audience: the `EncounterMembers` collector

`EncounterMembers` is **not** a sensor and does **not** track NPCs. It is an `ISensorEntityCollector` that goes in
the `Collector` slot of an ordinary sensor, and it collects the **players** that sensor matched — non-players are
rejected outright. Every shipped user puts it on a `Player` sensor; `Example_Boss.json` writes it like this:

```json
"Sensor": {
  "Type": "Player",
  "Range": 30,
  "Collector": { "Type": "EncounterMembers" }
}
```

| Key | Default | Meaning |
|-----|---------|---------|
| `RememberFor` | `0.5` (>0) | "Seconds a player remains a member after the sensor last matched them before being reverted". The shipped music encounters raise it to `2.5`, and `Encounter_Dungeon_Goblin_Void_Reveal.json` to `5` and `600` |

That roster **is the audience**: `EncounterMemberSystems.Tick` walks `EncounterMembers.getMemberTtl()` and calls
`applyToPlayer` / `revertPlayer` on each consumer — the audio, boss-bar and weather state — so a player who walks
out of the sensor's range has their music, boss bar and weather reverted once their TTL lapses, without the asset having to do anything. Nothing is
proximity-tested at apply time — the collector's sensor `Range` is what defines "in the encounter".

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

## Rewards

New in 0.7.2. A **reward** is a JSON asset under `Server/Rewards/`, keyed by file name and polymorphic on `"Type"`.
The `Rewards` built-in plugin (`RewardModule`, package `com.hypixel.hytale.builtin.rewards`, manifest id
`Hytale:Rewards`) registers the store in `setup()` along with the one built-in type. `EncounterManager` and `NPC` both
declare `Hytale:Rewards` as a dependency, and `GrantReward` is the only shipped caller.

| `Type` | Class | Keys | Effect |
|--------|-------|------|--------|
| `Entitlement` | `EntitlementReward` | `EntitlementId` (string) — required: `Validators.nonNull()` plus `nonEmptyString()` | Sends the player's client a `SelfGrantEntitlement` packet carrying the id, asking it to grant itself that entitlement. That packet is the whole effect on the server side |

The one shipped reward is `Server/Rewards/Reward_Cosmetics_Chapter1.json`:

```json
{
  "Type": "Entitlement",
  "EntitlementId": "cosmetics.chapter_1.boss"
}
```

The Goblin Gobliterator boss fight grants it on a win, from
`Server/EncounterManager/Goblin_Gobliterator/Templates/Template_Goblin_Gobliterator_Encounter.json`:

```json
{
  "$Comment": "Grants the win reward to every encounter member.",
  "Type": "GrantReward",
  "Reward": "Reward_Cosmetics_Chapter1"
}
```

**Granting from Java.** `RewardModule.get().grantReward(rewardId, playerRef)` looks the id up in
`RewardAsset.getAssetMap()` and calls the asset's `grant(PlayerRef)`. It returns `false`, logging a WARNING, for a
`null` id, an unknown id (`Unknown reward %s requested for %s`), or a `grant` that throws (`Reward %s failed for %s`;
the exception is caught there). The module keeps no record of what it granted, and `GrantReward` grants again each
time the action runs. The shipped boss fight runs it in the same action list that sets its `Encounter_Live` flag to
`false`, which is what keeps it to one grant per win. The chapter-complete page
([`OpenChapterRewards`](interactions.md#openchapterrewards)) only displays reward tiles and grants nothing.

**A custom reward type.** Extend `RewardAsset`, implement `grant(PlayerRef)`, and register the class against
`RewardAsset.CODEC` in your plugin's `setup()`, which is how `RewardModule.setup()` registers `Entitlement`. List
`"Hytale:Rewards": "*"` under `Dependencies` in your manifest so the reward store exists first. The codec copies
`EntitlementReward.CODEC`'s shape:

```java
package com.example.rewards;

import com.hypixel.hytale.builtin.rewards.asset.RewardAsset;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.validation.Validators;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import javax.annotation.Nonnull;

public class ChatMessageReward extends RewardAsset {
    public static final BuilderCodec<ChatMessageReward> CODEC =
        BuilderCodec.builder(ChatMessageReward.class, ChatMessageReward::new)
            .appendInherited(new KeyedCodec<>("MessageKey", Codec.STRING),
                (reward, key) -> reward.messageKey = key,
                reward -> reward.messageKey,
                (reward, parent) -> reward.messageKey = parent.messageKey)
            .addValidator(Validators.nonNull())
            .addValidator(Validators.nonEmptyString())
            .documentation("Localization key of the chat message sent to the player.")
            .add()
            .build();

    protected String messageKey;

    @Override
    public void grant(@Nonnull PlayerRef playerRef) {
        playerRef.sendMessage(Message.translation(this.messageKey));
    }
}
```

```java
package com.example.rewards;

import com.hypixel.hytale.builtin.rewards.RewardModule;
import com.hypixel.hytale.builtin.rewards.asset.RewardAsset;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.PlayerRef;

public class RewardsPlugin extends JavaPlugin {
    public RewardsPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        getCodecRegistry(RewardAsset.CODEC)
            .register("ChatMessage", ChatMessageReward.class, ChatMessageReward.CODEC);
    }

    // Callable from any of your systems or commands once assets have loaded.
    public static boolean grantWelcome(PlayerRef playerRef) {
        return RewardModule.get().grantReward("Reward_Welcome", playerRef);
    }
}
```

A pack then ships `Server/Rewards/Reward_Welcome.json` as `{ "Type": "ChatMessage", "MessageKey": "server.myplugin.welcome" }`,
with the text in its `Server/Languages/en-US/server.lang` as `myplugin.welcome = …` (the `server.` prefix names that
file), and an encounter can hand it out with `{ "Type": "GrantReward", "Reward": "Reward_Welcome" }`.

## Gotchas

- **No collector means no audience.** `SetEncounterBossBar`, `StartEncounterMusic`, `SetEncounterAudioState`,
  `SetEncounterWeather` and `GrantReward` act on the tracked members, and `EncounterMemberSystems.Tick` returns immediately when the roster is empty. An
  encounter with no `Collector` on any sensor therefore runs its whole script and affects **nobody**, silently.
- **Members expire.** Roster entries carry a TTL (`RememberFor`, default `0.5s`); a player the collector's sensor
  stops matching drops off and has their boss bar, music and weather reverted.
- **Only `SignalWorldEvent` works in `StateTransitions`.** The other eleven encounter components require
  `InstructionType.Encounter` and are rejected in a `StateTransitions` → `Actions` block.
- **Signals are world-wide.** `SignalWorldEvent` sends `WorldEventSignal(null, id)` — every running world event with
  a `SignalCondition` on that id completes, not just "the one nearby". Namespace your signal ids.
- **`CleanupOnRemove` is transitive, and unload is not removal.** It removes every entity sharing the encounter's
  spawn lineage — what it spawned and what those spawned in turn — but only on actual removal; a chunk unload
  leaves everything in place.
- **`Class`, not the folder, decides what a file is.** Encounters and instruction macros share the tree: 21 of
  the 67 shipped assets are `"Class": "Instruction"` files, all of them in a `Macros/` or `Examples/` folder, while
  `Examples/` and every topic folder also hold encounters. The schema registration covers both
  (`EncounterManager/*.json` and `EncounterManager/**/*.json`). `registerAssetPath` only sets a *default* category
  for the path; `Class` overrides it per file.
- **`Encounter manager references unknown or invalid asset '%s'` is not a misfiled-asset error.** It is logged by
  `EncounterManagerSystems.BuilderSystem` when an already-spawned encounter *entity* names a builder that no longer
  exists or whose category is not `EncounterManager` — a dangling reference after a rename or deletion. The sibling
  string on a build exception is `Failed to build encounter manager '%s'`.
- **Encounters hot-reload.** Editing an asset re-registers its builder and `reloadEncounters` removes and re-adds
  every live encounter entity on that index (calling `resetRuntime()` and dropping `NetworkId` in between), so a
  running encounter restarts rather than needing a server bounce.

> **See also:** [World Events](world-events.md), [NPC Roles](npc-roles.md), [Audio](audio.md), [Prefabs](prefabs.md).
