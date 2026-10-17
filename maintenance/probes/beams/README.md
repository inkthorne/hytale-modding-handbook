# Beams probes

Runs that settle the claims `docs/beams.md` marked "not verified". Build 0.7.2 (revision
`d769dc3d57881261a62858e1394f0e4de9a21eca`), measured 2026-10-17. Everything here runs headless:
no client, no user. The claims that need a client are in [PHASE-G.md](PHASE-G.md) and were not run.

The server runs from a scratch cwd with a scratch `--universe`, `--bind 127.0.0.1:5599`,
`--auth-mode offline`, `--disable-sentry` and under `timeout`. Nothing under the launcher install or
`UserData` is written. Raw logs stay in the scratch directory; this file quotes the lines that decide.

```bash
maintenance/probes/beams/build.sh                  # plugin/build/libs/beams-probe.jar
maintenance/probes/beams/run.sh "$SCRATCH" CASE    # CASE: see the header of run.sh
```

## Predictions, written before the C5, C6, C1 and C3 runs

R4 (the boot measurement) ran first and has no prediction: it asks whether the server boots at all.
The predictions below were written after reading the decompiled source and before any case below
was run.

**C5. A pack's own texture under `Common/Beams/` passes `TEXTURE_BEAM`.**
`CommonAssetValidator.accept` (`server/core/asset/common/CommonAssetValidator.java`) checks three
things in order: the path starts with a root from `[Beams/, Trails/]`, the path ends in `png`, and
`CommonAssetRegistry.hasCommonAsset` knows it. I expect:

- `c5-positive` (pack-local `Common/Beams/Probe_Own.png`): exit 0.
- `c5-outside` (`Textures/Probe_Own.png`, file present): nonzero, with
  `Common Asset 'Textures/Probe_Own.png' must be within the root: [Beams/, Trails/]` and no other
  message.
- `c5-nonpng` (`Beams/Probe_Own.jpg`, file present): nonzero, with
  `Common Asset 'Beams/Probe_Own.jpg' must have the extension png` and no other message.
- `c5-missing` (`Beams/Probe_Missing.png`, no file): nonzero, with
  `Common Asset 'Beams/Probe_Missing.png' doesn't exist!`.
- `c5-trails` (shipped `Trails/Fire.png`): exit 0.

What could make the positive fail: a pack's `Common/` registering with the registry after the
`Beam` store validates. The negative controls cannot tell, because they fail for their own reasons.
So the positive is also read from a booted store (the `c6` run logs the `Probe_Own` beam and its
index).

**C6. An inline `BeamConfig` object gets index `Integer.MIN_VALUE`.**
`Beam.CHILD_ASSET_CODEC` is a `ContainedAssetCodec`. Its `decodeJson` only queues the object with
`addContainedAsset` and returns a generated id. `AttachBeamInteraction.processConfig` runs in
`afterDecode`, before the queued `Beam` is loaded, so `Beam.getAssetMap().getIndex(generatedId)`
returns `Integer.MIN_VALUE`. I expect, for both shapes (a standalone Interaction file, and an
`AttachBeam` inline in a `ProjectileConfig`'s `ProjectileSpawn`):

- the interaction is present in the map (the existence check passes);
- its `beamIndex` is `Integer.MIN_VALUE` on this first load;
- the named-id control (`Probe_Named`) has an index of 0 or more;
- the sentinel (`NoSuchBeam`) is `Integer.MIN_VALUE`, so the sentinel and the inline case are the
  same value;
- the generated `Beam` does exist after load, with a real index, so the stale value is only in the
  interaction.

Not predicted, so not claimed: whether a reload fixes it. See the reload section below.

**C1. A second `AttachBeam` on an entity that already has a `BeamComponent`.**
`AttachBeamInteraction.firstRun` queues `commandBuffer.addComponent(...)`
(`builtin/beam/interaction/AttachBeamInteraction.java`). The command runs when the buffer is
consumed (`component/CommandBuffer.java:407`, `consume()`): `Store.datachunk_addComponent`
(`component/Store.java:2152`) throws `IllegalArgumentException("Entity already contains component
type: ...")` for the second one. `InteractionSystems.TickInteractionManagerSystem` has a
`catch (Throwable)` (`modules/interaction/system/InteractionSystems.java:255`), but it wraps only
`interactionManager.tick`, and the throw happens later, when the system's command buffer is consumed.
Nothing on that path catches, so it reaches the world thread's `catch (Throwable t)` in
`server/core/util/thread/TickingThread.java:89`. I expect:

- `c1-control` (one `AttachBeam`): no exception, exactly one `BeamComponent ADDED` line for the
  projectile, both `ProbeLog` lines (same tick and 0.2 s later), world ticks on.
- `c1-double` (two `AttachBeam`, then `ProbeLog`, then a 0.2 s `Simple` and a second `ProbeLog`):
  - the same-tick `ProbeLog` line IS written, because both `addComponent` calls are only queued
    while the chain runs, and `ProbeLog` writes synchronously. So that line does not show that the
    chain survives; it shows the chain ran to its end in one tick before the buffer was consumed.
  - one `BeamComponent ADDED` line (the first command), then the `IllegalArgumentException`
    logged by the world thread: `Exception in thread WorldThread...` with the text above.
  - the 0.2 s `ProbeLog` line is NOT written: the world thread is dead by then.
  - the `world tick` lines stop. The world is removed as crashed. The default world's crash policy
    is `Reload` on a dedicated server (`WorldCrashRecoveryHandler.defaultWorldMode`; `None` in
    singleplayer), so the headless run should log `Reloading crashed world 'default' in 5
    second(s)`, and the tick lines resume on the new world.
  - players, had there been any, are disconnected (`World.stopIndividualWorld`, `worldCrashed`).

**C3, server half. `BeamsUpdate` with a long or non-ASCII node name.**
`PacketIO.writeVarAsciiString(MemorySegment, ...)` encodes with `String.getBytes(ASCII)` and throws
`ProtocolException("String exceeds max bytes: <n> > 96")` above 96 bytes. I expect: 12 bytes
(`R-Attachment`) and 96 bytes serialize and read back unchanged; 97 bytes throws exactly that text
with `97 > 96`; `café` serializes and reads back as `caf?`, the byte `0x3f`, with no error.

## Results

All figures below are from one pass on 2026-10-17 (java 25.0.4.1, `HytaleServer.jar` 0.7.2). Paths are
shortened to `$S`, the scratch directory. `verdicts.sh "$S"` re-reads the logs and prints one PASS or
FAIL per verdict below; it prints VOID (exit 2) when a control did not hold. It was run against this
pass: 0 failed, 0 void. It was also run against a copy with a control sabotaged (an exception line
added to `c1-control.log`) and one message edited: it printed VOID and FAIL for those and no PASS for
them. A missing log is a FAIL, not a skip.

## R4. Does the server boot headless? Yes

```bash
run.sh "$S" boot
# java -jar HytaleServer.jar --assets .../Assets.zip --auth-mode offline --disable-sentry \
#      --bind 127.0.0.1:5599 --universe $S/boot/universe --mods $S/boot/mods --boot-command stop
```

`exit=0 seconds=7`. Log: `Setup phase completed! Boot time 2sec 377ms`, then
`Hytale Server Booted! [Multiplayer, Fresh Universe] took 6sec 634ms`. The default world is created
in the scratch universe. Port 5599 was free; the game was not running.

`--shutdown-after-validate` stops before plugin `start()`. With the probe plugin installed,
`validate-plugin` ran 61 s, exit 0, and its log has 0 `PROBE` lines (`HytaleServer.boot`, line 323 of the
decompiled source, checks the flag before `pluginManager.start()`). So a validate run never reaches a
plugin. A plugin run ends by the plugin calling `HytaleServer.get().shutdownServer()` after logging.

Cost per run (`exit` and seconds as `run.sh` printed them):

| Run | Seconds |
|-----|---------|
| `boot`, `c6`, `c3` | 7 |
| `c5-outside`, `c5-nonpng`, `c5-missing` (fail while loading the pack) | 7 each |
| `c5-0`, `c5-positive`, `c5-trails`, `validate-plugin` (pass: the whole validation runs) | 60 to 63 each |
| `c6-reload`, `c6-chain` | 19 each |
| `c1-control`, `c1-npc` | 32 to 33 |
| `c1-double` | 38 |

A full pass is about 7 minutes. The plugin cases need `build.sh` first.

## C5. A pack's own texture under `Common/Beams/`

Run 0 first: `run.sh "$S" c5-0` (`--validate-assets --shutdown-after-validate`, empty mods dir):
`exit=0 seconds=60`. The shipped tree validates clean, so the exit status of the runs below is
evidence. (It has warnings; none is an error.)

| Case | Pack content | Exit | Lines that settle it |
|------|--------------|------|----------------------|
| `c5-outside` (control) | `Common/Textures/Probe_Own.png` present; `TexturePath: Textures/Probe_Own.png` | 6 | `FAIL: Common Asset 'Textures/Probe_Own.png' must be within the root: [Beams/, Trails/]`, the only `FAIL:` line |
| `c5-nonpng` (control) | `Common/Beams/Probe_Own.jpg` present | 6 | `FAIL: Common Asset 'Beams/Probe_Own.jpg' must have the extension png`, the only `FAIL:` line |
| `c5-missing` (control) | `Beams/Probe_Missing.png`, no file | 6 | `FAIL: Common Asset 'Beams/Probe_Missing.png' doesn't exist!`, the only `FAIL:` line |
| `c5-trails` (positive control) | `TexturePath: Trails/Fire.png`, a shipped texture | 0 | no `FAIL:` line |
| `c5-positive` | `Common/Beams/Probe_Own.png` (4x4 PNG, 75 bytes) in the pack; `TexturePath: Beams/Probe_Own.png` | 0 | no `FAIL:` line |

Each failing case also ends with `Asset validation FAILED with 1 reason(s): Mod probe:Probe C5 failed
to load. Check for mod updates or contact the mod author.`, and the log shows the whole block:

```text
[AssetStore|Beam] Failed to validate asset: Probe_Own, $S/c5-outside/mods/Probe_C5/Server/Entity/Beams/Probe_Own.json, ...
Id: Probe_Own
Key: TexturePath
Results:
	FAIL: Common Asset 'Textures/Probe_Own.png' must be within the root: [Beams/, Trails/]
```

A second route to the positive: the `c6` run boots the store from the probe jar's pack, which carries
the same `Beams/Probe_Own.png`, and logs `Beam id='Probe_Own' index=4 texture=Beams/Probe_Own.png`.
`validate-plugin` validated that jar pack: exit 0.

The validation reaches a pack asset: three controls failed on a pack-local `Beam` for their own,
distinct reasons, so a validate run does see `Probe_Own`. The one thing the controls could not show
is that a pack's `Common/` is registered before the `Beam` store validates; the positive passing
shows it (its only way to pass is `CommonAssetRegistry.hasCommonAsset('Beams/Probe_Own.png')`).

**Verdict C5: confirmed.** A pack-local texture under `Common/Beams/` passes `TEXTURE_BEAM`, from a
directory pack and from a jar pack. The three quoted messages are exact, and each came alone.

## C6. An inline `BeamConfig`

Cases: `c6` (boot with the probe plugin; the jar's pack carries every asset below), `c6-reload`,
`c6-chain`. The plugin reads the `beamIndex` field of every `AttachBeamInteraction` in the
`Interaction` store by reflection, once `start()` runs (assets are loaded by then), and the index of
the `Beam` each one names.

Controls first (from `c6.log`):

```text
PROBE c6 sentinel: Beam 'NoSuchBeam' getIndex=-2147483648 (Integer.MIN_VALUE=-2147483648)
PROBE c6 AttachBeam interaction id='Probe_C6_Named' BeamConfig='Probe_Named' resolvedBeamIndex=5 (now getIndex(BeamConfig)=5) ...
PROBE c6 AttachBeam interaction id='**Projectile_Config_Hookshot_Interactions_ProjectileSpawn_Interactions_0' BeamConfig='Rope' resolvedBeamIndex=0 ...
```

The sentinel is the MIN_VALUE a missing beam gets. The named-id control and the shipped Hookshot both
got a real index.

The inline cases, in both shapes:

```text
PROBE c6 Beam id='*Probe_C6_Inline_BeamConfig' index=6 texture=Trails/Fire.png
PROBE c6 AttachBeam interaction id='Probe_C6_Inline' BeamConfig='*Probe_C6_Inline_BeamConfig' resolvedBeamIndex=-2147483648 (now getIndex(BeamConfig)=6) ...
PROBE c6 Beam id='***Probe_C6_Inline_Interactions_ProjectileSpawn_Interactions_0_BeamConfig' index=7 texture=Trails/Fire.png
PROBE c6 AttachBeam interaction id='**Probe_C6_Inline_Interactions_ProjectileSpawn_Interactions_0' BeamConfig='***Probe_C6_Inline_Interactions_ProjectileSpawn_Interactions_0_BeamConfig' resolvedBeamIndex=-2147483648 (now getIndex(BeamConfig)=7) ...
```

- The first is a standalone Interaction file, `Server/Item/Interactions/Probe_C6_Inline.json`. The
  second is an `AttachBeam` inline in a `ProjectileConfig`'s `ProjectileSpawn`, the shipped shape.
- Both interactions are in the store, so the load-time existence check passed.
- Both contained `Beam` assets were loaded, with real indexes (6 and 7), after the interaction had
  already resolved its index. The generated ids are `*` plus the container's id, one more star per
  level of nesting.
- `resolvedBeamIndex` is MIN_VALUE in both.

End to end, `c6-chain` fires the inline projectile from the player-like host and the observer logs
the component the interaction created:

```text
PROBE BeamComponent ADDED ref=... projectile=true predictedProjectile=false n=1 [{index=-2147483648 srcScale=1.0 tgtScale=1.0 srcNode=null tgtNode=null tgtNetworkId=2 tgtPos=null}]
```

Reload (`c6-reload`): a directory pack holds `Probe_R_Inline.json` (inline `BeamConfig`). Four seconds
after start the plugin rewrote it, adding `"Scale": 2.0`; the file watcher logged
`[AssetStore|Interaction] Reloading assets: [$S/c6-reload/mods/Probe_Reload/Server/Item/Interactions/Probe_R_Inline.json]`
and, at 12 s:

```text
PROBE c6 AttachBeam interaction id='Probe_R_Inline' BeamConfig='*Probe_R_Inline_BeamConfig' resolvedBeamIndex=-2147483648 ...   (at boot)
PROBE c6 AttachBeam interaction id='Probe_R_Inline' BeamConfig='*Probe_R_Inline_BeamConfig' resolvedBeamIndex=8 ...            (after the reload)
```

On a reload the contained `Beam` from the first load is already in the store, so the index resolves.
That makes the failure easy to miss in development: save the file once and it works, then a fresh
server start breaks it again.

**Verdict C6: confirmed, in both shapes, at boot.** The interaction exists (the existence sentence
holds), `beamIndex` is `Integer.MIN_VALUE`, and the `BeamComponent` it makes carries it. A reload of
the same file in a running server resolves a real index. What the client draws for beam index
`-2147483648` was not observed.

## C1. A second `AttachBeam` on an entity that already has a `BeamComponent`

Predictions are above. The driver is `Tasks.drive`: spawn a host entity with
`InteractionHost.spawnHost` (then drop its `InteractionHost` marker, because
`InteractionHostCleanupSystem` removes a host with no chain on its first tick), load its section as a
ticking one (an entity in a `NonTicking` section is removed with reason UNLOAD), and call
`ProjectileModule.spawnProjectile` from inside `Store.forEachChunk`. The projectile's
`ProjectileSpawn` chain then runs through the host's `InteractionManager` in the world's own tick.
Nothing here queues `addComponent` by hand.

```bash
run.sh "$S" c1-control   # player-like manager; Probe_C1_Control: AttachBeam, ProbeLog, 0.2 s, ProbeLog
run.sh "$S" c1-double    # player-like manager; Probe_C1_Double: AttachBeam, AttachBeam, ProbeLog, 0.2 s, ProbeLog
run.sh "$S" c1-npc       # manager as an NPC's; Probe_C1_Control (one AttachBeam)
```

**What the first run refuted.** The first `Probe_C1_Control` run (one `AttachBeam`) threw the same
exception as the two-`AttachBeam` chain, and `ProbeLog` wrote its line twice. The stack trace of
`ProbeLog` (run with `PROBE_STACK=1`) shows why:

```text
PROBE ProbeLog message='control: after the one AttachBeam, same tick' ...
PROBE   at ...SimpleInstantInteraction.simulateFirstRun(SimpleInstantInteraction.java:57)
PROBE   at ...InteractionManager.simulationTick(InteractionManager.java:1128)
PROBE   at ...InteractionManager.doTickChain(InteractionManager.java:862)
PROBE ProbeLog message='control: after the one AttachBeam, same tick' ...
PROBE   at ...SimpleInstantInteraction.tick0(SimpleInstantInteraction.java:32)
PROBE   at ...InteractionManager.serverTick(InteractionManager.java:1023)
PROBE   at ...InteractionManager.doTickChain(InteractionManager.java:865)
```

An `InteractionManager` built without a `PlayerRef` has `hasRemoteClient == false`. For such a
manager `executeChain0` runs a simulation tick and then a server tick for each operation
(`InteractionManager.java:486-499`, decompiled-source lines), and
`SimpleInstantInteraction.simulateFirstRun` calls `firstRun` unless a subclass overrides it
(`SimpleInstantInteraction.java:49-51`). `AttachBeamInteraction` does not. So `firstRun` runs twice and
queues two `addComponent` calls. An NPC's manager is built with `null` (`NPCInteractionSystems.java:83`),
and so is an `InteractionHost`'s (`InteractionHost.java:51`); a player's has its `PlayerRef`
(`InteractionSystems.java:216`). The host in `c1-npc` is therefore the same shape as an NPC for this
branch. No real NPC was run.

The valid control needs a manager that runs `firstRun` once. `-Dbeams.probe.remoteClient=true` calls
`InteractionManager.setHasRemoteClient(true)` on the host (`@Deprecated(forRemoval)`; it is the only
difference from `c1-npc`). That is an approximation of a player's manager, not a player: no player
chain was run.

Results (`seconds=32`, `38`, `32`):

| Case | `ProbeLog` same tick | `BeamComponent ADDED` | Exception | 0.2 s `ProbeLog` | World |
|------|----------------------|------------------------|-----------|-------------------|-------|
| `c1-control` | 1, `beamComponentCommittedNow=false` | 1 | none | 1, `beamComponentCommittedNow=true` | ticks on |
| `c1-double` | 1, `beamComponentCommittedNow=false` | 1 | `IllegalArgumentException: Entity already contains component type: ...BeamComponent...` | never | stops, reloaded 5 s later |
| `c1-npc` | 2 | 1 | the same | never | stops, reloaded 5 s later |

`c1-double`, the lines in order:

```text
PROBE ProbeLog message='double: after the second AttachBeam, same tick' type=ProjectileSpawn ... beamComponentCommittedNow=false
PROBE BeamComponent ADDED ref=... networkId=3 player=false projectile=true predictedProjectile=false n=1 [{index=5 ... tgtNetworkId=2 ...}]
[SEVERE] [Hytale] Exception in thread Thread[#128,WorldThread - default,5,InnocuousForkJoinWorkerThreadGroup]:
java.lang.IllegalArgumentException: Entity already contains component type: ComponentType{... typeClass=class com.hypixel.hytale.builtin.beam.BeamComponent, index=100}
	at com.hypixel.hytale.component.Store.datachunk_addComponent(Store.java:2792)
	at com.hypixel.hytale.component.Store.addComponent(Store.java:1370)
	at com.hypixel.hytale.component.CommandBuffer.lambda$addComponent$1(CommandBuffer.java:526)
	at com.hypixel.hytale.component.CommandBuffer.consume(CommandBuffer.java:669)
	at com.hypixel.hytale.component.Store.tick(Store.java:2403)
	at com.hypixel.hytale.component.system.tick.ArchetypeTickingSystem.tick(ArchetypeTickingSystem.java:36)
	at com.hypixel.hytale.component.Store.tickInternal(Store.java:2349)
	at com.hypixel.hytale.component.Store.tick(Store.java:2319)
	at com.hypixel.hytale.server.core.universe.world.World.tick(World.java:442)
	at com.hypixel.hytale.server.core.util.thread.TickingThread.run(TickingThread.java:103)
[INFO] [World|default] Stopping world default...
[INFO] [World|default] Removing individual world: default
[INFO] [WorldCrashRecoveryHandler] Reloading crashed world 'default' in 5 second(s) (attempt 1 of 3)
```

The world-tick line (one per second of world time) read `tick 120` at 15:23:02, the crash at 15:23:03,
`tick 150` at 15:23:09: a 6 s gap where every other pair is 1 s apart.

- The exception is thrown by `CommandBuffer.consume` from `Store.tick`, after the system pass. Nothing
  catches it before `TickingThread.run`, which logs it and ends the world thread, exactly as predicted.
  (The line numbers in the stack are the engine's source lines. The numbers in the predictions above
  are lines of the decompiled cache, which differ.)
- The chain does run to its end in the tick: the same-tick `ProbeLog` after the second `AttachBeam`
  is written, because both `addComponent` calls were only queued. What the throw prevents is
  everything after the tick: the 0.2 s `ProbeLog` never fires, and no later tick runs in that world.
- The first `AttachBeam` is applied; the second throws. One `ADDED` line, with the first beam.
- The dedicated server reloads the default world 5 s later, as predicted
  (`WorldCrashRecoveryHandler.defaultWorldMode`: `Reload` unless singleplayer). The line
  `Reloading crashed world 'default' in 5 second(s)` is **also** written on a plain shutdown (every
  run ends with it, e.g. `boot`'s `stop`), so by itself it does not show a crash. The exception line
  and the 6 s tick gap do.
- Players were not simulated (no client). From `World.stopIndividualWorld` (decompiled source, `World.java:244-270`, the
  default-world branch at `:265-269`): each player is sent a disconnect whose message is
  `server.general.disconnect.worldCrashed` (`worldCrashedCause`, naming the plugin, when a third-party plugin is on the
  stack). Read, not run.

**Verdicts C1 (one per sub-question):**

1. Does it throw? **Yes**: `IllegalArgumentException: Entity already contains component type:
   ...BeamComponent...`, from `CommandBuffer.consume`.
2. Is it logged, with what text? **Yes**, `SEVERE`, `Exception in thread Thread[#128,WorldThread -
   default,...]:` and the text above, with the stack above.
3. Does the chain continue to `Next`? **The chain ran to its end in the tick** (the synchronous
   `ProbeLog` after the second `AttachBeam` fired once); a `Next` that waits for a later tick, and
   anything queued behind the throwing command in the same buffer, **does not run**.
4. Does the world keep ticking? **No.** The world thread ends. On a dedicated server the default world
   is reloaded after 5 s (tick lines resume, state is gone). Players are disconnected (read).
5. Is the double-add the only cause? **No.** A manager without a `PlayerRef` (NPC, host entity)
   runs `firstRun` twice, so **a single `AttachBeam` crashes the world** there (`c1-npc`; a stand-in for
   an NPC, not an NPC).

## C2. Does a client-predicted Hookshot shot get a rope? Source trace; the answer needs a client

No headless run. What the source says (decompiled-source line numbers, `com/hypixel/hytale/server/core`):

1. `ProjectileInteraction.firstRun` (`modules/projectile/interaction/ProjectileInteraction.java:111-113`)
   takes `generatedUUID` from the client's sync data when present, and passes it to
   `ProjectileModule.spawnProjectile(generatedUUID, ...)` (`:129`). `getWaitForDataFrom()` is `Client`
   (`:91`), so the chain waits for the client's data.
2. `spawnProjectile` (`modules/projectile/ProjectileModule.java:169,183-184`) with a non-null
   `predictionId` gives the projectile a `UUIDComponent` and a `PredictedProjectile`, and at `:200`
   starts the `ProjectileSpawn` chain **only if `predictionId == null`**. So the server does not
   start it for a predicted shot. (This part was in the page already.)
3. The server runs it when the client sends it. `InteractionManager.syncStart`
   (`entity/InteractionManager.java:730-750`): a chain packet carrying `data.proxyId` is looked up with
   `getRefFromUUID(proxyId)` (the prediction id is that projectile's `UUIDComponent`), checked with
   `InteractionValidation.isAccessibleProxyTarget` (`modules/interaction/interaction/util/InteractionValidation.java:119-141`), and, if it passes, run as
   `InteractionContext.forProxyEntity(this, ref, proxyTarget, commandBuffer)` (`:750`).
   `isAccessibleProxyTarget` requires: the type is one of `ProjectileSpawn`, `ProjectileHit`,
   `ProjectileMiss`, `ProjectileBounce` (`:34`); the proxy has a `PredictedProjectile`; the requester has
   a `UUIDComponent`; the proxy has `StandardPhysicsProvider`; and the requester's UUID equals the
   physics provider's creator UUID.
4. In that context the running entity is the projectile and the owner is the player
   (`InteractionContext.forProxyEntity(manager, entityRef, runningForEntity, ...)`,
   `entity/InteractionContext.java:428`, and `getRootInteractionId` reads the `Interactions` component of
   `runningForEntity`, `:363-375`). That is the same `User` / `Owner` pair as the server-started chain.
   So `AttachBeam` with `TargetEntity: Owner` would add a `BeamComponent` to the predicted projectile and
   end at the player.

So the rope exists on the server for a predicted shot **if and only if the client sends the
`ProjectileSpawn` chain with the proxy id**. Whether it does for the Hookshot, and whether the rope
then draws, is not in the source. [PHASE-G.md](PHASE-G.md) logs two lines for it. "Other viewers" cannot be
observed in singleplayer.

**Verdict C2: not settled; the path exists in the server and is documented; the client half is open.**

## C3. A node name the model lacks or a name over 96 bytes

Server half, `run.sh "$S" c3` (7 s). The plugin serializes a `BeamsUpdate` with one `BeamInstance`
into a `MemorySegment` and reads it back with `BeamsUpdate.toObject`:

```text
PROBE c3 case='valid R-Attachment (control)' charLength=12 utf8Length=12 serialize=OK bytes=75 readBack.length=12 readBack='R-Attachment' ...
PROBE c3 case='96 bytes (boundary)' charLength=96 utf8Length=96 serialize=OK bytes=159 readBack.length=96 ...
PROBE c3 case='97 bytes' charLength=97 serialize=THREW com.hypixel.hytale.protocol.io.ProtocolException: String exceeds max bytes: 97 > 96
PROBE c3 case='e-acute (U+00E9)' charLength=4 utf8Length=5 serialize=OK bytes=67 readBack.length=4 readBack='caf?' readBackHex=6361663f
PROBE c3 case='CJK' charLength=2 utf8Length=6 serialize=OK bytes=65 readBack.length=2 readBack='??' readBackHex=3f3f
PROBE c3 case='96 ASCII + 1 e-acute (96 chars? 97 chars)' charLength=97 serialize=THREW com.hypixel.hytale.protocol.io.ProtocolException: String exceeds max bytes: 97 > 96
```

- The limit counts bytes after the ASCII conversion, so it counts characters: two CJK characters are two
  bytes (`3f3f`), not six, and `96 N + é` is 97 and throws.
- The valid name round-trips, so the harness can read a name back.

**Verdicts C3, server half:** the 97-byte `ProtocolException` text is exactly as the page says;
a non-ASCII name serializes without error and reads back as `?` per character. Confirmed.

**Not run (client):** what the client draws for a node the model lacks, and what a viewer sees when the
update that would carry a 97-byte name throws. Read only: `PacketEncoder.encode`
(`protocol/io/netty/PacketEncoder.java`) calls `PacketIO.writeFramedPacket` with no catch, so the throw
leaves the Netty pipeline; `HytaleChannelInitializer.exceptionCaught`
(`server/core/io/netty/HytaleChannelInitializer.java:127-136`) answers an exception in the pipeline with a
`ServerDisconnect` (`internalServerError`, `Crash`) and closes the connection. Whether a failed outbound
write reaches that handler was not run. See [PHASE-G.md](PHASE-G.md) for the observation, which is a
kick risk and sits last.

## C4. `Scale` is the beam's width

Not run: a width needs eyes. [PHASE-G.md](PHASE-G.md).

## Refuted or changed by the runs

- **Prediction: `c1-control` (one `AttachBeam`) throws nothing.** It threw. The driver used a manager
  that runs each instant interaction twice (no `PlayerRef`). Recorded above as a finding; the control
  was rebuilt around `setHasRemoteClient(true)`.
- **Prediction: the line `Reloading crashed world` marks a crash.** It is also logged on every plain
  shutdown (`boot`, `c6`, `c3`, `c1-control`).
- **Prediction citations: lines `Store.java:2152`, `CommandBuffer.java:407`.** Lines of the decompiled
  cache; the engine's stack says `Store.java:2792` and `CommandBuffer.java:669`.
- **Pre-check of the driver:** a host in an unloaded or `NonTicking` section is removed on add
  (`UPDATE_LOCATION`, reason UNLOAD); a host with no chain is removed by `InteractionHostCleanupSystem`
  on its first tick. Both gave a silent non-run before they were handled; a result from a run in which
  `drive: spawnProjectile returned` is missing is not a result.

## Files

| File | What it is |
|------|------------|
| `build.sh` | Builds `plugin/build/libs/beams-probe.jar` with the examples' Gradle wrapper |
| `run.sh` | One headless case in a scratch dir (header lists the cases) |
| `verdicts.sh` | Judges the logs; VOID when a control fails |
| `plugin/` | The probe plugin and its asset pack (not an example; not in the example-build gate) |
| `PHASE-G.md` | The script for the user, for what needs a client. Not run |
