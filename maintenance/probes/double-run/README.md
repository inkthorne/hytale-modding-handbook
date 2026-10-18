# Double-run probes

What happens to an interaction's work on a manager that has no remote client (an NPC's, an NPC-fired
projectile's, a host entity's). Build 0.7.2 (`jar_sha=23f71f03763422ce`), probed 2026-10-17. Everything
runs headless: no client, no user.

Two things are here. `census.py` (and `usage.py`) read the decompiled source and decide, for every
registered interaction type, which pass reaches its work. The plugin and `run.sh` then **measure** the
effect at a target for a calibration set of shipped types, each with its controls. The census is
**read**; the calibration runs are **measured**. The page `docs/interactions-double-run.md` marks every statement
with one or the other.

```bash
python3 -I maintenance/probes/double-run/census.py            # the census; --check prints only the denominator
python3 -I maintenance/probes/double-run/usage.py             # the 13b population: which types NPC, encounter and ability chains and the engine's own chain starters reach, and on which manager; --tables FILE writes the page's tables (FILE must resolve outside the repository and is not --table: exit 2 otherwise)
python3 -I maintenance/probes/double-run/usage-test.py "$WORK"   # plant item edges, carriers, routes and table defects in a small tree; usage.py must see each, and only those (87 checks)
python3 -I maintenance/probes/double-run/usage-mutations.py "$WORK" [FROM TO]  # delete each of 22 guards in a copy of usage.py; usage-test.py must go red on each (22 caught in 419 s on a loaded machine; also takes --assets DIR --src DIR)
maintenance/probes/double-run/build.sh                         # plugin/build/libs/double-run-probe.jar
maintenance/probes/double-run/run.sh "$SCRATCH" Damage1.npc    # one case; see the header of run.sh
maintenance/probes/double-run/verdicts.sh "$SCRATCH"           # judge the logs (49 PASS on the pass quoted below; 24 of them are 13a's, 22 the first 13b pass's, 3 the review's ExitInstance)
maintenance/probes/double-run/verdicts-test.sh "$SCRATCH" "$WORK"  # sabotage the logs; each damage must turn its verdict red (146 damages; VT_ONLY=REGEX runs the matching ones)
maintenance/probes/double-run/verdicts-mutations.sh "$SCRATCH" "$WORK" [FROM TO]  # damage the judge: each 13b guard removed in turn must turn a sabotage red (54 guards)
python3 -I maintenance/probes/double-run/census-test.py "$WORK"    # plant defects in a copy of the source; census.py must see each
maintenance/probes/beams/guard-test.sh "$WORK" "$PWD/maintenance/probes/double-run/run.sh" .double-run-case "Log1 Damage1.npc remote"
```

**What `verify-docs.sh` runs of this (item 14).** The static half: the section "The double-run table matches the population and the source"
runs `usage.py`, `census.py`, `census-test.py` and `usage-test.py` on every run, on the caches `verify-docs.sh` itself resolves, and goes red when
`usage.py` exits non-zero or does not print its `unknown: N (limit 5); 0 problem(s)` line; when the stdout of `census.py` or `usage.py` differs
from `census-0.7.2.txt` or `usage-0.7.2.txt` (but for the `source: ` and `assets: ` lines, which name the cache); when the span of
`docs/interactions-double-run.md` between `### The population (counted)` and `### Outcomes that depend on a field` differs from the
`usage.py --tables` output by a row, a heading or an order; or when either control exits non-zero, lacks its `---- 0 failed` line or prints fewer
PASS lines than its floor (16 and 87). `check-double-run-fixture.py` tests that section (54 cases, 73 mutations). **Not run:** the measuring half
(`run.sh`, `verdicts.sh`, `verdicts-test.sh`, `verdicts-mutations.sh`) and `usage-mutations.py` (419 s). **Not covered even when it is green:** the prose
figures outside the seven tables (the population paragraph, the per-field counts table, "13 measured, 45 read"), the `file:line` pins in the page's
prose (a table row's deciding hook is checked, its prose pin is not), and the coarse `sim` check (LOW-A below). **At a game update** the section goes red
after `build-jar-cache.sh`: the census `build:` line, the verdict table, the page's tables and both snapshots move, and so do `census-test.py`'s six
README labels and `usage-test.py`'s pins. Re-read what moved and re-commit them; nothing regenerates them, because a regenerated snapshot certifies itself.

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
   over-approximation: only the variables a root names run). **48 of 135** types from these seeds (`ModifyInventory` 15
   objects, `ChangeStat` 102 since the review keyed an object by the file that defines it; 17 and 114 before), and **58
   of 135** with the engine's own chain starters of the review section below added (`ChangeStat` 106). Encounter seeds
   (`EncounterManager`) are included and add no type; `WorldEvent` seeds add none; dropping `Item/Interactions/Tests` from
   the nodes loses none of the 13a graph's types and, of the run-reached ones, `PlaceBlock` (printed on every run).
3. **The item-only types**: the 9 in population 1 and not in 2 (10 before the routes: `SpawnNPC` is back through the block
   routes), each with the shortest path from a seed and the field its item edge sits in. `DurabilityCondition` and
   `MovementCondition` are among the 12 that fall out without item edges and come back because an NPC holds a weapon whose
   `Attack` root uses them.

**Runs on** (R6). Every state of the walk carries the manager the chain runs on: `NPC` (an NPC seed; a projectile it
fires runs `ProjectileSpawn` on the NPC's manager), `encounter`, `A-caster` (an ability seed: the caster's manager, which for a
player has a remote client and runs ONE pass, `AbilityChargeActivator.java:105-125`), `host` (under an object whose
`Type` is `SpawnInteraction`) and `A-entity` (under `SpawnAbilityEntity`, `LaunchAbilityProjectile` or
`SplitAbilityProjectile`: `AbilityEntitySpawner.java:59`, `AbilityProjectileLauncher.java:102`, built with
`new InteractionManager(null, ...)`) and the five route labels of the review section (`NPC collision`, `NPC block break`,
`NPC stat effect`, `NPC trigger volume`, `NPC held item`: each the NPC's own manager, reached by that route). A shared file
gets every label that reaches it. 6 of the 58 types are reached only as `A-caster` (`ApplyAbilityEffects`, `AttachBeam`,
`GrantAbilityCharges`, `GroundedCondition`, `LaunchAbilityProjectile`, `SpawnAbilityEntity`); the other 52 run on a manager
with no remote client. (This paragraph said "5 of the 48 ... the other 43" until the review of b0b119a..c4e97d1, LOW-3: it
left `AttachBeam` out of the list, and the page and the output of `usage.py` already said 6 and 42.)

The per-field counts the page quotes (ChangeStat `Behaviour`: `Add` 4, `Set` 35, `Min` 14, absent 53 over the 106
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

## Item 13b results (2026-10-17, same build, java 25.0.4.1, `HytaleServer.jar` 0.7.2)

**The pass.** 68 server runs (the boot, then 67 cases), 19-25 s each, in a scratch directory outside the repo, with
`--auth-mode offline`, `--disable-sentry`, `--bind 127.0.0.1:5599`, under `timeout`, one at a time: the 13a cases again
(the harness changed under them: new counters in the result line, the colour-stripped log cache in the judge) and the 13b cases.
`verdicts.sh`: **46 PASS, 0 failed, 0 void** (24 from 13a, 22 new). The cases and the controls:

| Type | Cases | Unit control (flagged host) | Dose / sensitivity control | NPC-shaped | Real `Chicken` | Verdict |
|------|-------|-----------------------------|----------------------------|------------|----------------|---------|
| `Explode` | `Explode1/2.remote`, `Explode1.npc`, `.realnpc` | health -1.0, 1 `Damage` event (environment source) at the `Sheep` | two copies: -2.0, 2 events | **-2.0, 2 events** | 2 events | **doubled** |
| `TriggerCooldown` | `Cooldown1/2.remote`, `Cooldown1.npc`, `CooldownOne1.remote/npc`, `Cooldown1.realnpc` | 3 charges: 1 used | two copies: 2 used | **3 charges: 2 used; 1 charge: 1 used** | 2 of 3 used | **doubled with 3 charges, the same result twice with 1** |
| `ApplyForce` | `Force1/2.remote`, `Force1/2.npc` | the flagged manager applies **+0.0** (no simulation pass; the client applies it) | two copies on the NPC-shaped manager: +10.0 | **+5.0 (the configured force, once)** | not run (the NPC's physics consumes the velocity) | **once** |
| `Repeat` | `Repeat1/2.remote`, `Repeat1.npc`, `.realnpc` | 1 forked projectile | two `Repeat`: 2 | **1** | 1 | **guarded** |
| `ClearEntityEffect` | `Clear0.npc`, `Clear1.remote`, `Clear1.npc`, `.realnpc` | effect cleared | negative control: a chain that clears nothing leaves it (1.0) | **cleared** | cleared | **the same result twice** (end state; the second removal cannot be counted) |
| `Projectile` | `Proj1/2.remote`, `Proj1/2.npc`, `Proj1.realnpc` | the flagged manager spawns **0** (the client spawns it) and the chain ends `Failed` | two copies on the NPC-shaped manager: 2 | **1** | 1 | **once** |
| `ModifyInventory` `AdjustHeldItemQuantity` -1 | `InvAdjSelf1/2.remote`, `InvAdjSelf1.npc`, `InvAdjOneSelf1.remote/npc` | stack of 5: -1; stack of 1: -1 | two copies: -2 | **stack of 5: -2, stack of 1: -1**; no desync | not run (no hotbar) | **doubled** (the same result with a stack of 1) |
| `DestroyBlock` | `Destroy1/2.remote`, `Destroy1.npc`, `.realnpc` | 1 `BreakBlockEvent`, block 953 -> 0 | the dose cannot be made at one block: two copies raise 1 event, the second finds air | **1 event, block gone** | 1 event | **the same result twice** |

`verdicts.sh` requires, for every row, the unit control, the dose control or its stated substitute, the abort/state check of
`flawed()` on every run (`ApplyForce`, `Repeat` and `Projectile` remote controls end `Failed`: their chains wait for a client that
never comes, after the effect has landed, or, for `ApplyForce` and `Projectile`, without an effect at all), and for the real-NPC
rows the manager line. `ApplyForce` and `Projectile` have no flagged unit: a flagged manager has no simulation pass and the
client does the work, so the unit is the configured force (5.0) and the dose control is two copies on the same NPC-shaped manager.

**Predictions against measurements** (those committed in `9cbc36d` before any run; the harness cases they name did not exist then):

| Prediction | Measured | |
|------------|----------|-|
| `Explode`: doubled | doubled | held |
| `TriggerCooldown`: doubled with 3 charges, the same result twice with 1 | exactly that | held |
| `ApplyForce`: once, "1 instruction queued, **as flagged**" | once (+5.0, two copies +10.0); **the flagged manager applies +0.0** | the verdict held; "as flagged" is **refuted** (the flagged control reads 0, the instrument had to read the velocity, not the queue: `GenericVelocityInstructionSystem` empties the queue every tick) |
| `Repeat`: guarded | guarded | held |
| `ClearEntityEffect`: the same result twice | the same end state | held |
| `DestroyBlock`: **breaks twice** (read; "may change nothing") | **1 `BreakBlockEvent`; the second pass finds air** (`BlockHarvestUtils.java:172`) | **refuted**, and the advisor's reading too |
| `TriggerSpawnMarkers`: **triggers twice** (read) | not run (needs a spawn marker); reading `SpawnMarkerEntity.trigger`: it returns false while `spawnCount > 0` (`:816`), which the first trigger sets (`:402`), so each marker fires once | **refuted by reading**: the verdict is *guarded*, still read |
| `Simple`, `StatsCondition`, `Interrupt` | not run | read; unchanged |
| the held-slot walk: empty | 0 candidates among 17 `ModifyInventory` objects | held |

Added after the predictions were committed, so **not pre-registered**: `Projectile` (the most used NPC projectile launcher, 145 objects;
reading: `simulateFirstRun` only records the aim), `ModifyInventory`'s `AdjustHeldItemQuantity` (reading: `setHeldItem` keeps the
item-change check quiet, so no desync, and `firstRun` runs again; it was written down only in the verdict table) and the real-NPC runs
of the others. The calibration rule (R4) did not fire: the three calibration types agreed on their verdicts, and no read verdict rests on the flagged control of
`ApplyForce`. `DestroyBlock` is not a calibration type; the read verdicts that rest on "a second pass finds the world already changed"
are `DestroyBlock` itself (measured) and none other: `BreakBlock`, `ChangeState` and `PlaceFluid` are `once` because their simulation hook is empty.

**The held-slot walk (R2; `usage.py`, section 5).** The class chains of the run-reached types (48 at the time, 58 since the review) were scanned for calls that write an inventory slot
(`setActiveSlot`, `setItemStackForSlot`, `removeItemStackFromSlot`, `removeItemStack`, `addItemStack`, `addOrDropItemStack`, `moveItemStack`,
`putItemStack`, `replaceItemStackInSlot`): only `ModifyInventory` writes one directly (`PlaceBlock` and `PlaceFluid` call `setHeldItem` and write through
`BlockPlaceUtils`; `EquipItem` and `ChangeActiveSlot` write the slot but are item-only). Of its run-reached objects (**17** at the time, **15** since the review keyed an object by the file that defines it), **14** (now **12**) carry `RequiredGameMode`
(`Adventure`: the arrow chains) and are inert on a manager with no `Player` component (`ModifyInventoryInteraction.java:97`), **3** use `AdjustHeldItemQuantity`
-1 (`Skeleton_Elite_Shield_Guard_Broken_Effects` with `Ignore`, `Tests/ModifyInventory`, `Item_Throw`), which calls `context.setHeldItem` (`:113`) and never trips the
item-change check, and **0** write `ItemToRemove`, `ItemToAdd` or the durability without a gate. So the desync of 13a (a `Server` wait, owner == entity, a write
that bypasses `setHeldItem`) has **no shipped instance**; no real-NPC reproduction was attempted. What the walk found instead is the doubled consumption above.
`usage-test.py` plants an ungated `ItemToRemove` (must be the one candidate), a gated one and a gated one inherited through `Parent` (inert), both `Adjust` paths (cannot trip) and a
write under `Ignore`.

**The population and the table** are in `usage-0.7.2.txt` and `verdict-table.tsv`. At the end of 13b: 48 run-reached types of 135 (the 13a count of 58 included 10 reachable only through
a field that names an item); 12 measured, 36 read, 0 unknown; doubled 3, refuses 1, the same result twice 4, guarded 4, once 20, flow 8, reads 7, none 1. **Since the review of
b0b119a..c4e97d1: 58 types, 13 measured, 45 read, 0 unknown**; doubled 3 (`ChangeStat`, `ModifyInventory`, `Explode`), refuses 2 (`AttachBeam`, which no shipped chain reaches on a manager with no
remote client: its one object is in a `ProjectileSpawn` chain, which runs on the shooter's manager; and `ExitInstance`, measured), the same result twice 4, guarded 4, once 24, flow 8, reads 7,
none 6. `usage.py` re-checks the table against the population and the source on every run: a type without a row, a row for a type not run-reached, a duplicate row, a deciding hook that is not
declared at its recorded line, a deciding file that is not in the type's class chain, an outcome that its census `sim` label cannot carry, a word outside the vocabularies, more than 5 unknowns.

**What the tests are.** `verdicts-test.sh` damages the logs one way at a time (122 damages at the end of 13b, 146 since the review; at the end of 13b 68 of them were new: each new verdict has its dose, unit,
negative, sensitivity, abort, state, exception and real-NPC manager controls broken in turn). `verdicts-mutations.sh` damages the judge: it replaces each guard of the 13b part of
`verdicts.sh` with `false` (one at a time, 46 guards; 54 since the review) and requires the damaged judge to go red, either on the unharmed run (the guard is a verdict's own gate) or on one of the block's sabotages.
The first pass found 20 guards that survived: 13 because the block filter did not select the sabotage that covers them (the labels named the case, not the type; the filter and the labels were fixed), and 7 because no sabotage existed (the exception check of five blocks, the abort of `InvAdjOneSelf1.npc`, the aborted control runs of `DestroyBlock`; added). The second pass left none: 46 guards, 46 caught (36 by one of the block's sabotages, 10 because the unharmed logs already turn the damaged judge red, the guard being a verdict's own gate).
`usage-test.py` (41 checks at the end of 13b, 82 since the review) plants the bait, held weapons with and without the tag, `Compute`, `Parent`, off-hand, a key outside `AttackType`, `InteractionVars`, the three carriers, an ability
projectile's `ProjectileSpawn` and `ProjectileHit`, the held-slot walk cases and the table variants, and was run against mutated copies of `usage.py`.

## Review of b0b119a..c4e97d1 (what changed, with the measurements)

**MAJOR-1: the population missed the chains the engine starts itself.** The walk followed asset strings from NPC, encounter, ability and held-weapon files. Some chains are started by
the engine, on an entity's own manager, from a field of a block, a stat or a volume, and no NPC file names them. Re-derived by listing every caller of `initChain`, `queueExecuteChain`,
`executeChain` and `startChain` in the decompiled source (24 files) and reading each for the manager it runs on, instead of adding the three routes the reviewer's `routes.py` found.
Each route is a seed with its own label in the "runs on" column; `usage-test.py` plants one of each with a decoy and shows the walk without the routes reaches none of them.

| Route (label) | What starts the chain, and the line that decides it | Seeds at 0.7.2 | Types it adds |
|---------------|-----------------------------------------------------|---------------:|---------------|
| NPC collision | `Collision`, `CollisionEnter`, `CollisionLeave` of the block or fluid the entity moves into. `MotionControllerBase.processTriggers` (`:1138`; `EnableTriggers` defaults to true, `:142`) is called by every NPC motion controller (`MotionControllerWalk`, `Fly`, `Dive`, `Base`), and reaches `CollisionResult.defaultTriggerBlocksProcessing` (`:262-334`, `entity instanceof LivingEntity`) and `doCollisionInteraction` (`:336`) on the colliding entity's manager. A state variant of a block carries its own `Interactions` | 58 files | 10: `ChangeBlock`, `ExitInstance`, `HubPortal`, `LaunchPad`, `Portal`, `PortalReturn`, `SpawnNPC`, `TeleportConfigInstance`, `TeleportInstance`, `Teleporter` |
| NPC block break | `OnBreak`, `OnBreakImpact`. `DestroyBlockInteraction` passes the owning entity as the breaker (`:40-42`), `BlockHarvestUtils.fireOnBreakInteraction` (`:849`) and `queueBlockInteraction` (`:863`) run the root on the breaker's manager, or on a host when the breaker has none (`:872`) | 2 files (the two spider cocoons) | none new (`SpawnNPC`) |
| NPC stat effect | `MinValueEffects` / `MaxValueEffects`. `EntityStatsSystems.Changes` (`:244-253`) queries every living entity with a manager and `runInteractions` (`:327-336`) runs the root on it; `EntityStatMap.update` allocates every stat type for every entity | 3 files (`Immunity`, `Stamina`, `GlidingActive`) | none |
| NPC trigger volume | `RunRootInteraction` effects: `RunRootInteractionEffect.execute` (`:41-64`) runs on `TriggerContext.getEntityRef()`. `TriggerVolumeTickingSystem` filters the entities of a volume by `TargetTypes` (`:344`), and `resolveTargetType` returns `NPC` for anything that is not a player, an item drop or a projectile (`:791-801`). A queued `SIGNAL_RECEIVED` has no target filter: its actor is whoever sent the signal (`SendSignalEffect`, `SignalNearbyVolumesInteraction`, `ActionSignalTaggedVolumes`), and `Dungeon_Feastmaster_Charge_HitBlock` (an NPC chain) signals the `FoodPile` volumes whose root `Root_NPC_Dungeon_Feastmaster_Pile_Crash` then runs on that NPC | 12 root files, from 40 of the 51 `RunRootInteraction` effects in `Server/` (volume assets, `Instances/*/resources/TriggerVolumeData.json`, prefabs) | none new |
| NPC held item | `Held`, `HeldOffhand`, `Equipped`. `NPCInteractionSystems.TickHeldInteractionsSystem` (`:49-55`) calls `tryRunHeldInteraction` (`InteractionManager.java:1177`) for the active hotbar item, the active utility item and each armor slot, every tick | 0: four items carry one (`Debug_Continue`, `Debug_Continue_Equip`, `Debug_Continue_Equip_Legs`, `Weapon_Bomb_Continuous`) and no NPC file names them (the held and worn strings, 210 of them, were read through `Compute` parameters) | none |

The 11 other `RunRootInteraction` effects belong to volumes whose `TargetTypes` is only `Player` and fire on `ENTER`, `TICK` or `BLOCK_USED`; they run on the player. That includes
`Forgotten_Temple_Persistance_Resync` (`GameFlagCondition`), which the reviewer's volume seed ran: the seed took every root, whatever its target. Read and found to start no chain on a manager
with no remote client, each with the line that decides it:

| Caller | Why it is empty or already covered |
|--------|-----------------------------------|
| `DeathSystems` (`:549`) | The root is `Interactions.getInteractionId(Death)`; for an NPC, `RoleBuilderSystem.java:160-161` sets it from the role's `DeathInteraction`, a string in 3 role files that the walk follows (`usage.py` section 2b: 3 of 3 reached). The unarmed fallback `Item/Unarmed/Interactions/Empty.json` has no `Death` root |
| `InventoryUtils.moveItem`, `SwapFrom` (`:250`) | Reached only inside `if (playerComponent != null && hotbarComponent != null && ...)` (`:219`): a player moving an item |
| `ChangeActiveSlot`, `SwapTo` fork | Item-only: only an NPC field that names an item reaches the type |
| `GameModeTypeState` (`:263`) | A game-mode swap of a player |
| `PlayerItemEntityPickupSystem` (`:123`) | Queries the player spatial structure |
| `BlockInteractionUtils.runRootInteractionOnBlock` (`:55`) | Called by `OpenChapterRewardsInteraction` and `ConfirmationPage` (a player's confirmation page) |
| `DamageSystems` Wielding (`:514`) | `BlockedInteractions` is a string field of the `Wielding` interaction, already an edge of the walk |
| `ProjectileModule` (`:220`), `StandardPhysicsProvider` (`:194,222`), `AbilityEntityRepeatSystem` (`:66`), `AbilityChargeActivator` | Roots named by projectile configs and ability assets, which are seeds |
| `ActionAttack`, `ActionBlockHitInteraction`, `ActionEntityHitInteraction`, `ActionCombatAbility`, `AbilityCombatAction`, `BodyMotionCharge`, `ActionSpawnInteraction` | Roots named by strings of NPC files, which are seeds |

The population is 58 types: the 48 from the asset strings, plus the 10 of the collision route. 6 are reached only as an ability caster, 52 run on a manager with no remote client. Dropping
`Item/Interactions/Tests` from the nodes loses `PlaceBlock` (only `Test_Place_Block` reaches it); the shortest path to `ChangeBlock` and `TeleportInstance` runs through a test interaction
(`Item/Interactions/Tests/ChangeBlock`, `.../TeleportInstance`), but dropping that directory loses neither. New verdicts, all in `verdict-table.tsv` with the deciding line: `ExitInstance` **refuses** (measured below);
`HubPortal`, `Portal`, `PortalReturn`, `TeleportConfigInstance`, `TeleportInstance` **none** (each returns or fails when the entity has no `Player` or `PlayerRef` component, and a manager with no
remote client has none: `HubPortalInteraction.java:81-84`, `EnterPortalInteraction.java:68-71`, `ReturnPortalInteraction.java:45-53`, `TeleportConfigInstanceInteraction.java:58-61`,
`TeleportInstanceInteraction.java:120-123`); `LaunchPad`, `SpawnNPC`, `Teleporter`, `ChangeBlock` **once** (the server hook does the work, the simulation hook is empty or only reads or copies the server state).
No new type is doubled or desyncs. `unknown`: 0 (limit 5).

**ExitInstance, measured** (4 runs; `Exit1.remote`, `Exit2.remote`, `Exit1.npc`, `Exit1.realnpc`, controls and sabotages as for `AttachBeam`). Read before the run: `firstRun` reaches
`InstancesPlugin.exitInstance` (`ExitInstanceInteraction.java:46`), which queues `ensureAndGetComponent(TeleportHistory)` and `addComponent(Teleport)` (`InstancesPlugin.java:418,423`); the guard
on the `Teleport` archetype in `firstRun` (`:43`) reads the store through `commandBuffer.getArchetype` (`CommandBuffer.java:66-68`), which the first pass's queued adds have not changed, so the second
pass queues both again: **refuses**. Measured: flagged unit control 1 `Teleport` added, no exception, chain `Finished`; the dose control (two on the flagged manager) 1 added and then
`Entity already contains component type`; the NPC-shaped host and a real `Chicken` (its own `NPCInteractionSimulationHandler` manager) 1 added and then the exception, on the world thread, and the
world reloads. **Changed by the run:** the component the exception names is `TeleportHistory`, not `Teleport`: the second `ensureAndGetComponent` is the first queued add to collide. The
verdict held, the line did not. The harness needs an `InstanceEntityConfig` return point on the subject (`dr.instanceReturn`): with none, in a world that is not an instance, `exitInstance` throws
`Player is not in an instance` (`InstancesPlugin.java:384`) from the first pass and the double run never shows. The prediction was written in the reading above, before the run, but not committed before it.

**MINOR-1: `TriggerSpawnMarkers` is "guarded" only when the spawn succeeds and `Count` is 0.** With `Count` above 0 the reservoir sample (`TriggerSpawnMarkersInteraction.java:69`) runs in each pass and
can pick different markers, up to `2 x Count` (`npc-spawning.md` already said so); and `spawnCount` is set only on success (`SpawnMarkerEntity.java:402`), so a spawn that fails leaves it at 0, both
passes try, and `fail()` (`:759-776`) counts both: the marker is marked validation-failed after 3 summons instead of 5 (`nextFailRemovesMarker`, `:783`). Read, not run (no spawn marker in the harness). The
row and the page's field table say both; `usage.py` now counts `Count` over the population (2 objects, both absent).

**MINOR-2: an object is keyed by the file that defines it.** `usage.py` keyed objects by (the held item's own file, path), and a held item's `InteractionVars` are merged from its `Parent` chain, so
a template two held children inherit was counted once per child (`Template_Weapon_Crossbow` under `Weapon_Crossbow_Iron` and `Weapon_Crossbow_Ancient_Steel`). `Assets.by_definer` credits each var to the
nearest file in the chain that defines it (a var every held child overrides is not counted: its template version never runs). 4,272 rows are 4,127 distinct objects, the figure the reviewer's
`dupcount.py` reaches by a route that shares no code with `usage.py`; `usage-test.py` asserts 4,127. Moved: `ChangeStat` 114 -> 102 objects (90 on a manager with no remote client), `ModifyInventory` 17 ->
15 (12 gated), `Projectile` 145 -> 125, `Simple` 1,247 -> 1,185, `DamageEntity` 761 -> 748, `Serial` 132 -> 120, `ApplyEffect` 155 -> 142, `Charging` 33 -> 26, `Wielding` 60 -> 57, `DurabilityCondition` 8 -> 7.
**Why the run-reached `Projectile` count (145) was larger than the all-edges count (99):** it was not a subset. The 13a graph had no encounter seeds (26 `Projectile` objects are reached only from
`Server/EncounterManager`), and the child-keyed duplicates added 20 (145 = 99 + 26 + 20). Keyed by definer, and with the encounter seeds in the all-edges walk, every one of the 4,127 objects is also an object
of the all-edges walk (`usage-test.py`: 0 outside, `Projectile` 125 of 125). With the routes the run-reached walk is no longer a subset: the volume route adds objects (`Projectile` 126) that no
asset string reaches.

**MINOR-3: the table check rejects a wrong row.** `check_table` accepted `ChangeStat = once` citing `ApplyEffectInteraction.java:91` `simulateFirstRun`, and `Explode = once`, with 0 problems and exit 0,
because its only per-row source check was that the hook is declared at the recorded line. It now also requires (a) the deciding file to be in the type's census class chain (`Chain(type).classes`) and (b) the
outcome to be one its census `sim` label can carry. The mapping, printed by `usage.py` on every run and decided from what each outcome claims, then checked against all 58 rows (none falls outside):
an effect run by both passes (`doubled`, `desync`, `refuses`, `same-twice`) needs `firstRun`, `firstRun+`, `tick0` or `tick0+` (the simulation pass reaches the server pass's method again); `guarded`
those or `own`, `own+`; `once` needs `no-op`, `own`, `own+`, `tick0+`, `via-*:no-op` or `via-*:other`; `flow` needs `own`, `own+`, `tick0+`, `via-*:no-op` or `via-*:other`; `reads`, `none` and
`unknown` take any. The rows by (outcome, sim) are printed too. `usage-test.py` plants the reviewer's rows and shows the old per-row rule accepts all three.

**MINOR-4, LOW-1.** `realverdict` now has the `Exception in thread` guard and the Destroy real-NPC verdict reads `block_id_before` and `block_id_after`; sabotages and mutations for both. **LOW-2.** The `Interrupt`
row's reason ("a second pass finds none") was false: `cancelChains` sets `Failed` and sends a cancel packet but removes no chain (`InteractionManager.java:1007-1014`), so the second pass cancels the same
chains again to the same end state (a target manager with a `PlayerRef` gets a second `CancelInteractionChain`); the verdict (the same result twice) holds. **Corrections to the page's rows (NITs):** `Wielding`'s
`simulateTick0` also calls `super.simulateTick0` (`ChargingInteraction`'s, `WieldingInteraction.java:194`); `Charging` writes `DamageDataComponent.setLastChargeTime` in `tick0` (`:219`), so its Write is "direct", not
"none"; the page's controls are stated per type; and the bucketing rule (a type is filed under its worst case on a manager with no remote client) is stated. A correction to the commit message of the
usage.py commit of this review: it says `usage-test.py` has 106 checks; it has 82 (the count was a guess before the run).

**The review's verify pass (c4e97d1..eb443c2) left two gaps, recorded rather than closed.** LOW-A: the `sim` mapping above lets `none`, `reads` and `unknown` take any label, and cannot separate `doubled`, `same-twice` and `refuses`; a planted `Explode = none` with `ChangeStat = reads` passes with 0 problems. A `none` row's real ground is a `Player`/`PlayerRef` guard, which no `sim` label expresses; checking that line like the hook line would close it. LOW-B: the `ExitInstance` verdicts count `Teleport` adds on every entity (`Watch.Teleports`) and the refusal line names no entity, so a stray add on another entity would still pass; in the measured runs the add is the subject's (in `Exit1.realnpc` the Chicken's index moved from 7 to 5 when two other entities unloaded, `Store.java:676-683`), and no sabotage plants two adds. The verify pass also fixed one stale figure: the `ModifyInventory` row said 14 of 17 gated objects, from before objects were keyed by their defining file; it is 12 of 15.

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
- **Review of b0b119a..c4e97d1: "the population is 48 types" (MAJOR-1).** It was the types asset strings reach. The engine's own chain starters add 10 (58 in all), found by listing the callers of
  `initChain` and not by following strings. One of the 10, `ExitInstance`, refuses (measured); the other nine land once or return for want of a `Player` component. The 13b figures that the 48 carried
  (12 measured, 36 read; ChangeStat 114 objects, 102 on such a manager; ModifyInventory 17, 14 gated) are 13, 45, 106 (94), 15 (12) now.
- **Review: "the run-reached Projectile count is larger than the all-edges count" (MINOR-2).** Not a subset: the all-edges walk had no encounter seeds (26 objects) and the child-keyed duplicates added 20. Both are
  gone from the base walk (see the review section).
- **Review: ExitInstance's read, "the second add of `Teleport` throws".** The exception names `TeleportHistory` (the second `ensureAndGetComponent` collides first). The verdict held.
- **13b: `DestroyBlock` "breaks twice" (the advisor's reading, R3).** Measured: 1 `BreakBlockEvent`, the block gone; the second `performBlockBreak`
  returns at `targetBlockTypeId == 0` (`BlockHarvestUtils.java:172`). *The same result twice.*
- **13b: `TriggerSpawnMarkers` "triggers twice" (R3).** Read, not run: `SpawnMarkerEntity.trigger` returns false while `spawnCount > 0` (`:816`) and the first trigger sets it (`:402`). *Guarded per marker.*
- **13b: `ApplyForce` "1 instruction, as flagged".** The verdict (once) held; the flagged control reads zero, since a flagged manager has no simulation pass. The first cut counted the queued
  instructions (0 everywhere): `GenericVelocityInstructionSystem` empties the queue every tick and adds it into the velocity, so the harness reads the host's vertical velocity.
- **13b: `Projectile` read 0 projectiles on every case.** It spawns an entity with the newer `Projectile` component, not `ProjectileComponent` (what `Watch.Projectiles` counted);
  a second counter (`projectiles_new`) was added. The flagged control still reads 0, now for the reason in the table.
- **13b: the first label walk put `AttachBeam` on an ability projectile's own manager** (it sits in the chain-hook projectile's config). It is under `ProjectileSpawn`, which runs on the shooter's
  manager (`ProjectileModule.onProjectileSpawnInteraction`, `:206`); only `ProjectileHit` and `ProjectileMiss` run on the projectile's. `usage.py` now keeps the caster's label under `ProjectileSpawn`
  (planted and tested). Without that fix the table would have listed a shipped refusal that no chain reaches.
- **13b harness defects.** `verdicts-test.sh` copied each case directory (a gigabyte for 68 cases) for every one of its damages; it copies the logs and result files now.
  `verdicts-mutations.sh`'s first pass listed the real-NPC guards a second time under the last block, and counted a mutation that turned the unharmed run red as caught without saying so; it now reports which.
- **Prediction citations.** Every `file:line` here is of the decompiled cache; the engine's stack frames differ
  (`InteractionManager.java:1128`, `:862`, `:865` for `simulationTick`, `doTickChain` in a stack trace of `Log1.npc`).

## Files

| File | What it is |
|------|------------|
| `census.py`, `census-0.7.2.txt` | The census and its output at 0.7.2 (re-run at the next build and diff) |
| `census-test.py` | Plants sixteen defects in a copy of the source; the census must see each and nothing else |
| `usage.py`, `usage-0.7.2.txt` | The 13b population (run-reached types, item-only types, the manager each runs on, the five routes no asset string names, per-field counts); `--tables FILE` writes the page's tables |
| `usage-test.py` | Plants the defects above, the routes with their decoys, the shared template and the wrong table rows in a small asset tree and requires `usage.py` to see each (87 checks); reproduces 58/46/12 and 4,127 on the real assets |
| `usage-mutations.py` | Deletes each of 22 guards of `usage.py` in a copy and requires `usage-test.py` to go red (all 22 do; 419 s in all on a loaded machine, so it stays by hand) |
| `build.sh`, `run.sh` | Build the plugin; run one case (header lists them) with the scratch guard of `../beams/run.sh` |
| `verdicts.sh`, `verdicts-test.sh` | Judge the logs; VOID when a control fails, FAIL when a run does not count (an aborted tick, the wrong chain state, a subject that was not on an NPC manager). The test damages the logs one way at a time (146 damages since the review) |
| `verdicts-mutations.sh` | Damages the judge instead: replaces each 13b guard of `verdicts.sh` with `false` (54 since the review), one at a time, and requires the sabotages of that block to go red |
| `verdict-table.tsv` | The 13b verdict for each of the 58 run-reached types (outcome, read or measured, how the write lands, the deciding hook and line); `usage.py` re-checks it against the population and the source |
| `plugin/` | The probe plugin: `Driver` (stages one case), `Watch` (counters at the target), the three `ProbeLog*` types and `ProbeInvNone` (`ModifyInventory` with the wait changed to `None`), and the `DR_*` root interactions |
| `../beams/guard-test.sh` | Tests the shared guard; takes this directory's `run.sh` and marker as arguments (and still passes for the beams `run.sh`) |
