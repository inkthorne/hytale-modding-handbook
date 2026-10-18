# Double-run probes

What happens to an interaction's work on a manager that has no remote client (an NPC's, an NPC-fired
projectile's, a host entity's). Build 0.7.2 (`jar_sha=23f71f03763422ce`), probed 2026-10-17. Everything
runs headless: no client, no user.

Two things are here. `census.py` (and `usage.py`) read the decompiled source and decide, for every
registered interaction type, which pass reaches its work. The plugin and `run.sh` then **measure** the
effect at a target for a calibration set of shipped types, each with its controls. The census is
**read**; the calibration runs are **measured**. The page `docs/interactions.md` marks every statement
with one or the other.

```bash
python3 -I maintenance/probes/double-run/census.py            # the census; --check prints only the denominator
python3 -I maintenance/probes/double-run/usage.py             # the 13b population: which types NPC, encounter and ability chains reach, and on which manager
python3 -I maintenance/probes/double-run/usage-test.py "$WORK"   # plant item edges and carriers in a small tree; usage.py must count only the held, Attack-tagged ones
maintenance/probes/double-run/build.sh                         # plugin/build/libs/double-run-probe.jar
maintenance/probes/double-run/run.sh "$SCRATCH" Damage1.npc    # one case; see the header of run.sh
maintenance/probes/double-run/verdicts.sh "$SCRATCH"           # judge the logs (24 PASS on the pass quoted below)
maintenance/probes/double-run/verdicts-test.sh "$SCRATCH" "$WORK"  # sabotage the logs; each damage must turn its verdict red
python3 -I maintenance/probes/double-run/census-test.py "$WORK"    # plant defects in a copy of the source; census.py must see each
maintenance/probes/beams/guard-test.sh "$WORK" "$PWD/maintenance/probes/double-run/run.sh" .double-run-case "Log1 Damage1.npc remote"
```

## The mechanism, in one paragraph (read; file:line are of the decompiled cache)

`InteractionManager.doTickChain` (`entity/InteractionManager.java:454`) runs two passes per operation
when the manager has no remote client (`hasRemoteClient`, set `playerRef != null` at `:115`):
`simulationTick` (`:644`, calls `Operation.simulateTick`) and `serverTick` (`:536`, calls
`Operation.tick`, then `Operation.handle`). The order comes from the operation's
`getWaitForDataFrom()` (`:486-497`): `None` and `Client` run simulation then server; `Server` runs
server then simulation. "Server" there is `serverTick` as a whole, `tick` (`:591`) and then `handle` (`:602`), so
for a `Server` wait the simulation pass (`:496`) runs after `handle` as well. A player's manager is built with a `PlayerRef`, so it runs the server pass only.
The two passes share one `InteractionEntry` and so one instance store (`InteractionContext.getInstanceStore`,
`InteractionContext.java:306`, `InteractionEntry.java:37`), but keep separate state and timestamps
(`InteractionEntry.java:73-83`), so `firstRun` is true in both. `Interaction.tick` and
`Interaction.simulateTick` are `final` (`Interaction.java:234,263`): both run `tickInternal` and then the
type's `tick0` or `simulateTick0`. `SimpleInstantInteraction.simulateTick0` calls `simulateFirstRun`
(`SimpleInstantInteraction.java:40`), whose default calls `firstRun` (`:49-51`).

## Predictions, written before the verdict runs

Written after reading the source and after one exploratory run (`Log1.npc` with `DR_STACK=1`, to see that
the harness works and which frames call a `firstRun`). That run showed the two passes and measured no
effect. Nothing below was run as a verdict before this section was written.

The unit of every effect is read from the remote-client control, not assumed (health -3 per
`DR_Damage`, 1 projectile, +5 `SignatureCharges`, 1 `Food_Egg`, 1 `BeamComponent`).

| Case | Manager | Prediction (effect at the target) | Why (read) |
|------|---------|-----------------------------------|------------|
| `Damage1` | npc | **1 hit**: target health -3 | `DamageEntityInteraction.simulateTick0` (`:195`) runs `tick0`, which stores `QUEUED_DAMAGE` in the instance store (`:510`); the server pass finds it and calls only `processDamage` (`:180`). Guarded |
| `Launch1` | npc | **1 projectile entity** | `LaunchProjectileInteraction.simulateFirstRun` (`:141`) is empty |
| `Beam1` | npc | **refuses**: 1 `BeamComponent` ADDED, then `IllegalArgumentException: Entity already contains component type`, world thread ends | `AttachBeamInteraction` does not override `simulateFirstRun`; `addComponent` is queued twice (item 12 measured this on a host) |
| `Stat1` | npc | **doubled**: `SignatureCharges` +10 | `ChangeStatInteraction` does not override `simulateFirstRun`; `processStatChanges` adds directly (`EntityStatMap.addStatValue`, behaviour `Add` by default) |
| `Inv1` (Server wait) | npc, proxy context (owner is a second entity, as `ActionSpawnInteraction` builds it) | **doubled**: 2 `Food_Egg` in the host's inventory | `ModifyInventoryInteraction` waits for `Server`, does not override `simulateFirstRun`; `addOrDropItemStack` twice |
| `InvSelf1` (Server wait) | npc, owner == running entity (the context `ActionAttack` builds) | **1** egg, not 2 (added after the first runs, see below): the second pass is skipped by the item-change check | `Interaction.tickInternal` (`Interaction.java:288-300`, runs in both passes): when the held slot of the context holds a different item from the one the context was built with, `data.state = ItemChanged` and `tick0`/`simulateTick0` is not called. The first pass puts the egg in the held slot. A proxy context (owner != entity) skips this check (`proxyContext`) |
| `LogS1` (Server wait) | npc | 2 lines, the first `pass=server`, the second `pass=simulation` | `doTickChain` `:489-497` |
| `Log1` | npc | 2 lines (`pass=simulation`, then `pass=server`) | `SimpleInstantInteraction` |
| `LogQ1` | npc | 1 line | `ProbeLogQ` overrides `simulateFirstRun` with an empty body |

Controls, each with a prediction:

- **Remote-client control (R4).** Each of the above on `remote` (`setHasRemoteClient(true)`) reads exactly
  the unit: 1 hit, 1 projectile, +5, 1 egg, 1 beam with no exception, 1 `Log1` line. This applies to
  `Damage1`, `Launch1`, `Beam1`, `Stat1`, `Inv1`, `Log1`: all wait for `None` or `Server`. `Damage1` has
  `needsRemoteSync() == true`, so its chain on a flagged manager waits for a client to finish it; the
  effect lands before that, and the chain is cancelled by timeout (`getOperationTimeoutThreshold`).
- **Dose control (R3).** The same type twice in one chain on `remote` reads 2 units (`Damage2` -6,
  `Launch2` 2 projectiles, `Stat2` +10, `Inv2` 2 eggs). `Beam2` reads 1 `ADDED` and the exception, which is
  the instrument seeing the refusal. A dose control that reads 1 where 2 is expected (a hit-protection
  window swallowing the second hit, say) makes the verdict VOID, not PASS.
- **Negative control (R3).** `Launch1.npc` must read 1 while `Stat1.npc` reads 2: the same manager and
  harness, the instrument sees a 2 where there is one.
- **Exception control.** No `Exception in thread` in any run except `Beam2.remote`, `Beam1.npc` and `Beam1.realnpc`.
- **Abort control (review of 41db9fe..5be0ad0, MINOR-3).** A run counts only if its tick was not aborted and its
  chain ended in the state its prediction names (`flawed()` in `verdicts.sh`). Abort lines: `not in sync`, a caught
  `Exception while ticking entity interactions! Removing!`, an entity `REMOVED reason=REMOVE`. Wanted
  `chain_server_state`: `Finished` for every run, except the `DamageEntity` remote controls (`Failed`: the chain waits for a
  client that never comes, after the effect has landed), `InvSelf1.npc` (`NotFinished`, with the three abort lines
  predicted), `InvNoneSelf1.npc` (`ItemChanged`) and the `AttachBeam` refusals (no state: the world thread dies before the
  RESULT line, only the abort lines are read). A control run that does not count is VOID, a verdict run that does not count is
  a FAIL. Before this, `verdicts.sh` read only `Exception in thread`, and a caught desync that removed the subject passed.
- **Manager control (LOW-1).** Every real-NPC case (`Log1`, `Stat1`, `Damage1`, `Beam1`) requires the driver's line
  `manager=realnpc self=false simulationHandler=NPCInteractionSimulationHandler`; before this only `Log1.realnpc` did.

Real NPC (fidelity check; `Log1.realnpc`, `Stat1.realnpc`, `Damage1.realnpc`): a shipped `Chicken`
spawned headless in a ticking section with no player; the chain runs on **its own** manager, started the
way `ActionAttack` starts one. Prediction: the NPC's manager runs the chain (it has an
`InteractionManager` with `NPCInteractionSimulationHandler`, and `TickInteractionManagerSystem` ticks every
entity with a manager), so `Log1.realnpc` reads 2 lines and `Stat1.realnpc` +10. `Damage1.realnpc`
(target: a second Chicken) reads 1 hit. If the NPC does not tick headless, that is the finding and the
host driver's fidelity stays an argument from source.

The R6 sample (fixed before the verdicts, from `usage.py` and a reading of the candidates): the most used
type that is doubled and is not `DamageEntity` is **`ChangeStat`** (123 NPC-reachable objects, 12 ability).
`Simple` is more used but only moves state; the conditions (`StatsCondition`, `EffectCondition`) only read.
That fixes one doubled type for 13a. The Server-wait type is `ModifyInventory` (38 NPC-reachable objects).

**Added after the first full pass, before it was re-run** (`Inv2.remote` read 1, not 2, and its chain ended
`ItemChanged`; reading `tickInternal` explained it, and `InvSelf1` was written to test that explanation).
The first `Inv*` runs used one host as both owner and running entity; every `Inv1`/`Inv2` verdict below is
from the proxy-context version. The same first pass also lost its NPCs at random (a falling NPC left the loaded
section and was removed with `UNLOAD`; fix: load 3x3x3 sections and keep them loaded), and showed that the host
needs a `BoundingBox` or the damaged NPC's AI throws. Those are harness defects, recorded under "Refuted or
changed" below.

`Damage1.realnpc` needs `CombatSupport.setExecutingAttack(chain, false, 0.0)` after the chain is queued, as
`ActionAttack` does (`ActionAttack.java:221`; `Driver.java` makes the same call). The first draft passed `true` for
`damageFriendlies`, because `NPCDamageSystems.FilterDamageSystem` cancels damage from an NPC source that belongs
to the target's group unless the source deals friendly damage, and the target was a second Chicken; that was
replaced by a target of another species (a Sheep, see "Refuted or changed"), so the call is the plain one.
Prediction: one hit (-3).

`InvIgnoreSelf1` (added after `InvSelf1` desynced, to isolate the cause): the same chain as `InvSelf1` with
`"OnItemChangeBehavior": "Ignore"` on the interaction. Prediction: the item-change check is skipped, so both
passes run: **2** eggs, no `not in sync` line, no removal. If it still desyncs, the explanation (the item-change
check) is wrong.

`Beam1.realnpc` (added so that the claim in `docs/beams.md` that "no real NPC was run" can be replaced by a
measurement): `AttachBeam` once, on the real Chicken's own manager. Prediction: refuses, as on the host: one
`BeamComponent` ADDED, then `Entity already contains component type` on the world thread.

`InvNoneSelf1` (added after review, MINOR-1; the reviewer ran it before this harness had it, so this is not a
pre-registered prediction but the reading of the source that explained that run): `ModifyInventory` with only
`getWaitForDataFrom()` changed to `None`, owner == the running entity. The simulation pass runs first and puts the item
in the held slot; the server pass sees the changed item and `Interaction.tick` throws `ChainCancelledException(ItemChanged)`,
which the manager catches. Prediction: **1** item (the same as the remote control), `chain_server_state=ItemChanged`,
no `not in sync`, no removal. Unit control: `InvNoneSelf1.remote` reads 1 and finishes. Negative control: `InvSelf1.npc`
(the `Server` wait) desyncs on the same harness.

`StatSet1` (added after review, MINOR-2; the page had generalised the `Add` sample to every `ChangeStat`): `ChangeStat`
with `"Behaviour": "Set"` and `SignatureCharges` 5. `processStatChanges` calls `setStatValue`, which writes the value, so
the second pass changes nothing. Prediction (written before the run): **+5.0** on the NPC-shaped manager, as on
`remote`, while `Stat1.npc` (`Add`, same harness) reads +10.0. No dose control: setting twice reads one unit by
construction; the sensitivity control is that `Add` on the same harness does read two. `Min` and `Max` are read from
source (`minStatValue`, `maxStatValue`) and not measured. Shipped usage, counted from the extracted `Assets.zip`: of
the 206 objects with `"Type": "ChangeStat"` in `Server/` (every `.json` that parses, any depth; the 6,030 files that
do not parse are under `World/` and `Prefabs/` and none names `ChangeStat`), `Behaviour` is absent in 98, `Add` in 5,
`Set` in 89, `Min` in 14 and `Max` in none.

## Item 13b predictions (written and committed before any 13b measurement)

Written after reading the sources named below and after the population (`usage.py`, above) was fixed. No 13b run
had been made when this section was committed; the harness cases it names did not yet exist. File:line are of the
decompiled cache. A prediction that a measurement refutes stays here, with the number, under "Refuted or changed".

**The measured types and the calibration set (R3, R4).** Units are read from the remote-client control, as in 13a.

| Type | Case | Prediction on the NPC-shaped manager | Read, from |
|------|------|--------------------------------------|------------|
| `Explode` | `Explode1` (`Config`: `DamageEntities` true, `DamageBlocks` false, a Sheep target 3 blocks away) | **doubled**: the Sheep's health delta is 2 x the unit, and 2 `Damage` events (environment source) are raised where the flagged manager raises 1 | `ExplodeInteraction.firstRun` (`:52-91`) is a `SimpleInstantInteraction` that does not override `simulateFirstRun`, so both passes run it; `ExplosionUtils.processTargetEntity` calls `DamageSystems.executeDamage` directly (`:255`), and block damage would be `performBlockDamage` (`:166`); nothing is stored in the instance store |
| `TriggerCooldown` | `Cooldown1` (a cooldown of 3 charges), `CooldownOne1` (the default, 1 charge) | **doubled with 3 charges**: 1 charge left where the flagged manager leaves 2; **the same result twice with 1 charge**: 0 left, as flagged | `TriggerCooldownInteraction.resetCooldown` ends in `cooldown.deductCharge()` (`:106-109`), and `deductCharge` subtracts one while `chargeCount > 0` (`CooldownHandler.java:101-103`); `resetCooldown` and `setCooldownMax` are idempotent. The outcome depends on the charge count |
| `ApplyForce` (calibration) | `Force1` (a `Velocity` component on the host) | **once**: 1 instruction queued, as flagged | the force is applied only in `simulateTick0` (`:195-224`, `if (firstRun \|\| duration > 0 && time < duration)`); `tick0` returns on `firstRun` (`:158-160`) and later reads the client state the simulation pass stored. Duration 0: one pass applies it |
| `Repeat` (calibration) | `Repeat1` (a fork of `LaunchProjectile`; `Repeat` 1) | **guarded**: 1 projectile, as flagged | `RepeatInteraction.tick0` forks (`:80`) and stores `FORKED_CHAIN` in the instance store; `simulateTick0` (`:89-114`) only reads it. The simulation pass runs first and finds no chain; the server pass forks |
| `ClearEntityEffect` (calibration) | `Clear1` (an effect applied to the Sheep first, then cleared) | **the same result twice**: the effect is gone, as flagged | `firstRun` calls `removeEffect` (`ClearEntityEffectInteraction.java:50`); removing an absent effect changes nothing. The harness cannot count the second removal: this is a claim about the end state |
| `TriggerSpawnMarkers` | not run | **triggers twice** (read) | `firstRun` queues `trigger` (`:64,74`) in each pass; with `Count` > 0 the reservoir sample (`:69`) can pick different markers in each pass. Needs a spawn marker in range |
| `DestroyBlock` | tried only if the harness can give it a target block cheaply | **breaks twice** (read): `performBlockBreak` runs in both passes (`:59`) | the second pass finds the block already gone and may change nothing: the page will say which |
| `Simple` | not run | **no server-side effect of its own** (read) | `SimpleInteraction.tick0` only jumps to the failed label (`:55-58`); `simulateTick0` calls it with the server-failed state copied in for a `Server` wait |
| `StatsCondition` | not run | **reads only** (read) | `firstRun` (`:36-47`) reads the stat map and sets `Failed`; running it twice reads the same stats unless the first pass's `ChangeStat` changed them. In the shipped chains the stat gate runs before the `ChangeStat` that spends |
| `Interrupt` | not run | **the same result twice** (read, with a doubt: it cancels the chains of the target entity, which may include the chain running it) | `firstRun` (`InterruptInteraction.java:64-81`) |

The calibration rule (R4): if a measured calibration type disagrees with its prediction, every read verdict resting on
the same mechanism is downgraded to `unknown` on the page. The mechanisms the read verdicts rest on:

- **M-sim-empty**: `simulateFirstRun` or `simulateTick0` is empty, so the work runs once (`LaunchProjectile` measured in 13a).
- **M-firstrun-again**: the default `simulateFirstRun` calls `firstRun` again, so a non-idempotent `firstRun` runs twice
  (`ChangeStat`, `ModifyInventory` measured in 13a; `Explode`, `TriggerCooldown` here).
- **M-guard**: the type's own code runs its effect once, behind a first-run test or the instance store (`DamageEntity`
  in 13a; `ApplyForce` and `Repeat` here).
- **M-idempotent**: the effect is a write that a second call leaves as it is (`ChangeStat` `Set` in 13a; `ClearEntityEffect` here).
- **M-reads**: the type only reads state and chooses a branch (`StatsCondition`, `EffectCondition`, ...); no measurement.

**The held-slot walk (R2), predicted.** Reading `Interaction.tickInternal` (`:288-291`), a desync needs three things at
once: the held item no longer matches `context.getHeldItem()`, `OnItemChangeBehavior` is not `Ignore`, and the
context is not a proxy. `ModifyInventory`'s `AdjustHeldItemQuantity` and durability paths call `context.setHeldItem`
(`:113,149`) and so do not trip it; `ItemToRemove` / `ItemToAdd` (`:101,118-119`) and `EquipItem` (`EquipItemInteraction.java:62`) can.
Prediction: zero shipped run-reached operations that write the held slot or the active slot without
`context.setHeldItem` under a `Server` wait with the owner the running entity and a behaviour other than `Ignore`. The one
shipped `ModifyInventory` case (`Skeleton_Elite_Shield_Guard_Broken_Effects`, `/Failed/Interactions[0]`) has
`AdjustHeldItemQuantity` -1 and `Ignore`. A desync is tried on a real NPC only if the walk finds a hit.

## Results (one pass, 2026-10-17, java 25.0.4.1, `HytaleServer.jar` 0.7.2)

`verdicts.sh` on the final pass: **24 PASS, 0 failed, 0 void**. The final pass is 32 server runs (the boot, then
31 cases), 628 s in all, 19-24 s each (the boot 7 s), re-run after the review fixes (the pass quoted before them was 22 PASS in 28 runs), in a scratch directory outside the repo, `--auth-mode offline`,
`--disable-sentry`, `--bind 127.0.0.1:5599`, under `timeout`. Earlier passes were discarded after the harness
changes listed under "Refuted or changed"; none of their numbers is quoted here.

### The census (read; `census.py`, output kept in `census-0.7.2.txt`)

Population: the `Interaction.CODEC` registry as `registry_miner.py` reads it: **135 names, 135 distinct,
closed, key `Type`**. The miner records names, not classes, so the class is parsed from each
`.register(name, X.class, ...)` call: **135 classes parsed, 0 unparsed, 0 classes carrying more than one name,
0 superclass chains that did not reach `Interaction`**. (The first cut matched the register call by line and
reported 121 classes and six classes carrying several names; one line of `WorldEventsPlugin` chains five
registrations. It now matches by the id argument the miner recorded.) 78 names are classes that extend
`SimpleInstantInteraction` (the predicate: `SimpleInstantInteraction` is in the class's superclass chain); the other 57
are not, and of those 21 declare both `tick0` and `simulateTick0` themselves, while 36 inherit `simulateTick0` (30 from
`SimpleBlockInteraction`, 3 from `DragPlaceBlockInteraction`, 3 from `SimpleInteraction`) and 31 inherit `tick0` (28 from
`SimpleBlockInteraction`, 3 from `DragPlaceBlockInteraction`); counted from the `hooks` lines of `census-0.7.2.txt`.

What the simulation pass reaches (`sim`, counted in names; they add up to 135):

| `sim` | Names | Meaning |
|-------|------:|---------|
| `firstRun` | 56 | `SimpleInstantInteraction.simulateFirstRun` is not overridden: the default calls `firstRun` again |
| `no-op` | 21 | `simulateFirstRun` (or `simulateTick0`) is empty: the work runs in the server pass only |
| `tick0` | 2 | `simulateTick0` calls `tick0`: `DamageEntity`, `PlaceModeSelect` |
| `tick0+` | 12 | `simulateTick0` wraps `tick0` in other code: `Simple`, `Condition`, `Repeat`, `ApplyForce`, `Camera`, `BuilderTool`, five placement types, `CarryPlaceBlock` |
| `via-simulateInteractWithBlock:no-op` | 25 | block interactions whose simulate hook is empty |
| `via-simulateInteractWithBlock:other` | 5 | block interactions with a real simulate hook: `BlockCondition`, `ChangeBlock`, `PortalReturn`, `Teleporter`, `UseBlock` |
| `own`, `own+` | 13, 1 | a different body from the server pass (the control-flow types, `Charging`, `Wielding`, ...) |

`getWaitForDataFrom`: `None` 70, `Client` 40, `Server` 25. The pass order follows it: `Server` runs the server pass first.

The census does **not** say whether running a hook twice changes the world. 70 names reach the server pass's
method again (`firstRun`, `tick0`, `tick0+`); classifying the effect of each is item 13b. The census was
checked by `census-test.py`: a copy of the source with a defect planted in one class, run through
`census.py`, must move exactly that row to the expected label (sixteen defects, all seen, no other row moved: six at the first pass, and since the review ten more, one per label
path a real build does not reach: `super.simulateFirstRun`, a direct `firstRun` call, `+` around either, `tick0+`, `own`,
`own+` -> `own`, the block hook gaining a body, and a base class change that moves two rows).
The first run of that test failed on a defect the census mislabelled (`simulateFirstRun` calling `firstRun`
with other code was `via-firstRun:other`; it is `firstRun+` now). The review found two more shapes mislabelled
(`simulateFirstRun { super.simulateFirstRun(...); }` was `own`; a `simulateTick0` calling `this.firstRun` was
`via-firstRun:other`); `census-0.7.2.txt` is byte-identical before and after that fix, since neither exists at 0.7.2.

Managers with no `PlayerRef` (read; `new InteractionManager(null, ...)`): NPCs (`NPCInteractionSystems.java:83`,
`NPCInteractionSimulationHandler`), `InteractionHost.spawnHost` (`InteractionHost.java:51`; its callers are
`ActionSpawnInteraction` and `BlockHarvestUtils.java:893`), `EncounterManager.java:106`,
`AbilityEntitySpawner.java:59` and `AbilityProjectileLauncher.java:102`. A player's is
`InteractionSystems.java:216`. A projectile's `ProjectileSpawn` chain runs on its **creator's** manager
(`ProjectileModule.onProjectileSpawnInteraction`, `:206`): an NPC's, for an NPC-fired projectile.

### The population (`usage.py`, output in `usage-0.7.2.txt`; item 13b, fixed before any 13b measurement)

13a's sample was "58 of 135 types are reached", counted over a graph in which **any string equal to an asset id
is an edge, items included**. That over-counts: an NPC's `AttractiveItemSet`, `Items`, `ProduceItem` or
`HarvestInteractionRequiredItems` names an item and starts no chain. Without item edges 12 of the 58 fall out, and
`ModifyInventory` goes from 38 objects to 2 and `ChangeStat` from 135 to 25. `usage.py` now prints three populations:

1. **The 13a population** (all-edges): 58 of 135 types; `ModifyInventory` 38, `ChangeStat` 135. Kept so the figure reproduces.
2. **The run-reached population**: an `Item/Items` id is an edge only when the item is *held* (the role's `HotbarItems`
   and `OffHandItems`, and the parameters they `Compute` from: `Weapons`, `OffHand`, `Weapon`, `HotbarItems`, read from
   the roles, found at the role's top level, in `Modify.NAME` and in `Parameters.NAME.Value`) and its root for one of
   the NPC `AttackType` keys (`Primary`, `Secondary`, `Ability1`-`4`) is tagged `Attack` (`ActionAttack.java:148-160`:
   with no `Attack` set an NPC runs the held item's root, and only a root tagged `Attack`). The item's `Interactions`
   resolve through its `Parent`; its `InteractionVars` (and its parents') are counted as part of the chain (an
   over-approximation: only the variables a root names run). **48 of 135** types; `ModifyInventory` 17, `ChangeStat`
   114. Encounter seeds (`EncounterManager`) are included and add no type; `WorldEvent` seeds add none; dropping
   `Item/Interactions/Tests` loses none (printed on every run).
3. **The item-only types**: the 10 in population 1 and not in 2, each with the shortest path from a seed and the field its
   item edge sits in. `DurabilityCondition` and `MovementCondition` are among the 12 that fall out without item edges and
   come back because an NPC holds a weapon whose `Attack` root uses them.

**Runs on** (R6). Every state of the walk carries the manager the chain runs on: `NPC` (an NPC seed; a projectile it
fires runs `ProjectileSpawn` on the NPC's manager), `encounter`, `A-caster` (an ability seed: the caster's manager, which for a
player has a remote client and runs ONE pass, `AbilityChargeActivator.java:105-125`), `host` (under an object whose
`Type` is `SpawnInteraction`) and `A-entity` (under `SpawnAbilityEntity`, `LaunchAbilityProjectile` or
`SplitAbilityProjectile`: `AbilityEntitySpawner.java:59`, `AbilityProjectileLauncher.java:102`, built with
`new InteractionManager(null, ...)`). A shared file gets every label that reaches it. 5 of the 48 types are reached
only as `A-caster` (`ApplyAbilityEffects`, `GrantAbilityCharges`, `GroundedCondition`, `LaunchAbilityProjectile`,
`SpawnAbilityEntity`); the other 43 run on a manager with no remote client.

The per-field counts the page quotes (ChangeStat `Behaviour`: `Add` 4, `Set` 33, `Min` 14, absent 63 over the 114
run-reached objects; 206 over all of `Server/`, the figure 13a quoted) are taken over this population.
`usage-test.py` plants an `AttractiveItemSet` bait, a held weapon with and without an `Attack` root, a weapon held
through `Compute`, one that inherits its `Interactions`, an off-hand item, a key outside `AttackType`, `InteractionVars`
and the three carriers, runs three sabotages that must each move exactly the named types, shows the 13a rule counts
the bait (the negative control), reproduces the 58/46/12 figures on the real assets, and was run against nine
mutated copies of `usage.py` (each guard deleted: the tag test, the `Compute` names, the `AttackType` keys, the parent
chain, the carriers, the droplist and missing-id counts, the `InteractionVars`), each of which turns at least one check red.

### Calibration set (measured; effect at the target, `verdicts.sh`)

Units are read from the remote-client control. `remote` is `setHasRemoteClient(true)` on the same host.

| Type | `remote` x1 | `remote` x2 (dose) | NPC-shaped x1 | Verdict |
|------|-------------|--------------------|---------------|---------|
| `DamageEntity` (target health) | -3.0 | -6.0 | **-3.0** | **once (guarded)**. 1 `Damage` event raised and delivered; the remote runs raise 1 and 2 |
| `LaunchProjectile` (projectile entities) | 1 | 2 | **1** | **once** |
| `ChangeStat` (`SignatureCharges`) | +5.0 | +10.0 | **+10.0** | **doubled** |
| `ModifyInventory` (items in the owner's inventory; Server wait) | 1 | 2 | **2** | **doubled** (proxy context) |
| `AttachBeam` (`BeamComponent`s) | 1 ADDED, no exception | 1 ADDED, then `Entity already contains component type` | **1 ADDED, then the same exception on the world thread** | **refuses**; the world reloads 5 s later (`Reloaded crashed world 'default'`) |
| `ChangeStat` with `Behaviour` `Set` (`StatSet1`) | +5.0 | not run (a Set has no dose) | **+5.0** | **the same result twice**: one unit, where `Add` on the same harness reads two |
| `ModifyInventory` with the wait changed to `None` (owner == the running entity; `InvNoneSelf1`) | 1, chain `Finished` | not run | **1**, chain `ItemChanged` | **once**: the simulation pass does the work, the server pass is cancelled as `ItemChanged`; no desync, entity kept |

Plugin-written types (their declared effect is one log line, so these are lines, not world effects):

| Type | `remote` | NPC-shaped | Reads |
|------|----------|------------|-------|
| `ProbeLog` (overrides `firstRun`) | 1 line, `pass=server sim=false` | 2 lines: `pass=simulation sim=true`, then `pass=server sim=false` | the default |
| `ProbeLogS` (also waits for `Server`) | not run | 2 lines: `pass=server sim=false`, then `pass=simulation sim=true` | the pass order |
| `ProbeLogQ` (also overrides `simulateFirstRun` with an empty body) | not run | 1 line | the fix |

Controls: unit control (one on `remote` reads one unit) and dose control (two on `remote` read two) held for
`DamageEntity`, `LaunchProjectile`, `ChangeStat`, `ModifyInventory`; for `AttachBeam` the dose control is the
instrument seeing an add and then the refusal. The negative control is `Launch1.npc` reading 1 and
`Stat1.npc` reading 2 on the same manager with the same harness. The sabotage test (`verdicts-test.sh`)
turned each of 54 damages into the VOID or FAIL it should be (dose control broken, unit control broken, a doubled damage
read, a guarded read, a refusal line deleted, a pass deleted, a log missing, a stray exception; and since the review: each
abort line and the wrong chain state on verdict runs and on control runs, the real-NPC manager, the `InvNoneSelf1`
verdict, the `StatSet1` verdict, the `sim=` flag), and the unharmed copy stayed at 24 PASS.

`sim=` is `context.getEntry().isUseSimulationState()`, the one thing an interaction can read about its pass (both
accessors are public: `InteractionContext.java:199`, `InteractionEntry.java:86`). It is printed by `ProbeLog` and `ProbeLogS`,
and `pass=` is read off the calling stack (`simulationTick` or `serverTick`) by a different route, so the two must
agree: `verdicts.sh` requires `true`, `false` for `Log1.npc` and `Log1.realnpc`, `false`, `true` for `LogS1.npc`, and
`false` for `Log1.remote`. Measured (review of 41db9fe..5be0ad0, LOW-5): all four agree.

### Item-change check and the pass order (measured; the cause isolated)

`ModifyInventory` with the owner == the running entity (the context `ActionAttack` builds; `InvSelf1`):

```text
SEVERE [InteractionSystems$TickInteractionManagerSystem] Exception while ticking entity interactions! Removing!
java.lang.IllegalStateException: Simulation and server tick are not in sync (operation position).
Root: DR_Inv1
Counter: 1 vs 0
```

and the entity is removed (`REMOVED reason=REMOVE`). The same chain on `remote` reads 1 egg and no exception.
With `"OnItemChangeBehavior": "Ignore"` on the interaction (`InvIgnoreSelf1`) there is no exception and the NPC-shaped
manager reads **2** eggs, the remote 1. So the item-change check in `Interaction.tickInternal` (`Interaction.java:288-300`;
skipped for a proxy context, where owner != entity) is what made the pass diverge: the first pass puts the egg in the
held slot, the second pass sees a changed held item and does not advance the simulated operation counter. The
exception is caught by `TickInteractionManagerSystem` (`InteractionSystems.java:255`), which **removes the entity
that runs the chain**. Measured on a host; the same path serves an NPC (read).

**Only with a `Server` wait.** `ModifyInventory` waits for `Server`, so the server pass runs first and the
simulation pass is the second one, and `Interaction.simulateTick` has no `ItemChanged` case. With only
`getWaitForDataFrom()` changed to `None` (the plugin's `ProbeInvNone`, case `InvNoneSelf1`; the reviewer ran it first,
then it was rebuilt into this harness) the order is reversed: the simulation pass runs first and does the work, the
server pass sees the changed held item, and `Interaction.tick` throws `ChainCancelledException(ItemChanged)`
(`Interaction.java:256-258`), which `InteractionManager` catches at `:376` and only ends the chain with. Result on the
NPC-shaped manager, owner == entity: `inv_items_delta` **1.0** (the same as `InvNoneSelf1.remote`), `chain_server_state=ItemChanged`
(remote: `Finished`), no `not in sync`, no `Removing!`, the host not removed. `InvSelf1.npc` (the `Server` wait) is the negative control
on the same harness and still desyncs and removes the entity. A `Client` wait is read, not measured: `doTickChain`
orders it as `None`.

### Real NPC (fidelity; a Chicken spawned headless in a ticking section, no player)

| Case | Result |
|------|--------|
| `Log1.realnpc` | the Chicken's own manager is an `InteractionManager` with `NPCInteractionSimulationHandler`; 2 lines, `pass=simulation` then `pass=server`, as on the host |
| `Stat1.realnpc` | `SignatureCharges` +10.0 = 2 x the +5.0 unit: doubled, as on the host |
| `Damage1.realnpc` (a Chicken hits a Sheep) | health -3.0 = the unit; 1 `Damage` event raised and delivered: once, as on the host |
| `Beam1.realnpc` | 1 `BeamComponent` ADDED, then `Entity already contains component type` on the world thread: refuses, as on the host |

An NPC spawns, ticks and runs a chain headless in a section kept loaded with `addKeepLoaded` and
`resetActiveTimer`; no player is needed. The host driver agreed with the real NPC on all four. What the host does
not reproduce: the real NPC's group filter (below) and its own AI.

## Refuted or changed by the runs

- **The page's reading "a held-slot change from an interaction that runs for its own entity desyncs an NPC-shaped
  manager and removes the entity" (452604c; review of 41db9fe..5be0ad0, MINOR-1).** It held for the one sample, a
  `Server` wait, where the server pass runs first. `InvNoneSelf1.npc`, the same chain with only the wait changed to
  `None`, measured **1.0** item, `chain_server_state=ItemChanged`, no `not in sync`, no `Removing!`, no removal: the
  desync is the property of the pass order (the simulation pass is second and does not throw on `ItemChanged`), not of the held slot.
  The page now says so for each wait.
- **Prediction `InvSelf1.npc` = 1 egg (the second pass skipped cleanly).** Measured: desync and removal of the
  entity (above). The explanation (the item-change check) held; "cleanly" did not.
- **First `Inv` design (owner == entity for every `Inv` case).** `Inv2.remote`'s dose control read 1 and its chain
  ended `ItemChanged`: the second `ModifyInventory` of one chain sees the first one's egg in the held slot. VOID, not a
  finding about doubling. The proxy owner (a second host, as `ActionSpawnInteraction` has) is the shape under which
  `Inv1`/`Inv2` were measured.
- **A host needs a `BoundingBox` (harness defect).** The first damaged Chicken was gone at the reading (health `NaN`) and the log held
  `Failed to tick NPC: Chicken`: `BodyMotionFindWithTarget.canComputeMotion` threw `NullPointerException ... "targetEntityBoundingBoxComponent" is null` ("Failed to tick NPC") because `InteractionHost.spawnHost`
  gives the host none. Every host case now carries a box. So an NPC that a host's chain damages can end in that
  exception (one run; not isolated further, and not checked against a box-less host that does not damage).
- **An NPC outside the loaded sections is removed with `UNLOAD` (harness defect).** One loaded section was not enough: the
  spawn point is often within a few blocks of a section edge, and a Chicken that fell or stepped across it was removed (in the first full pass 6 of 23 runs
  logged `DR FATAL`: the target or subject was no longer valid when the chain was to start). The driver now loads 3x3x3 sections, keeps them loaded (`ChunkSection.addKeepLoaded`) and
  resets their timers (a section no player tracks is unloaded after 15 polls). 8 of 8 `Damage1.npc` runs then kept their target.
- **A real NPC does not hit its own species (harness defect).** `Damage1.realnpc` first read 0.0 with 1 event raised and none
  delivered: `NPCDamageSystems.FilterDamageSystem` cancels damage from an NPC in the target's `DisableDamageGroups`
  (`Self` for livestock). The target is a Sheep. `ActionAttack`'s `damageFriendlies` would also lift it.
- **First `Beam` runs lost their target** (same section defect) and the first `Log1.realnpc` read VOID (the verdict's grep
  predated the `self=` field of the driver's line).
- **Prediction citations.** Every `file:line` here is of the decompiled cache; the engine's stack frames differ
  (`InteractionManager.java:1128`, `:862`, `:865` for `simulationTick`, `doTickChain` in a stack trace of `Log1.npc`).

## Files

| File | What it is |
|------|------------|
| `census.py`, `census-0.7.2.txt` | The census and its output at 0.7.2 (re-run at the next build and diff) |
| `census-test.py` | Plants sixteen defects in a copy of the source; the census must see each and nothing else |
| `usage.py`, `usage-0.7.2.txt` | The 13b population (run-reached types, item-only types, the manager each runs on, per-field counts) |
| `usage-test.py` | Plants the defects above in a small asset tree and requires `usage.py` to see each; reproduces 58/46/12 on the real assets |
| `build.sh`, `run.sh` | Build the plugin; run one case (header lists them) with the scratch guard of `../beams/run.sh` |
| `verdicts.sh`, `verdicts-test.sh` | Judge the logs; VOID when a control fails, FAIL when a run does not count (an aborted tick, the wrong chain state, a subject that was not on an NPC manager). The test damages the logs one way at a time (54 damages) |
| `plugin/` | The probe plugin: `Driver` (stages one case), `Watch` (counters at the target), the three `ProbeLog*` types and `ProbeInvNone` (`ModifyInventory` with the wait changed to `None`), and the `DR_*` root interactions |
| `../beams/guard-test.sh` | Tests the shared guard; takes this directory's `run.sh` and marker as arguments (and still passes for the beams `run.sh`) |
