# Phase G: what needs a client

Not run. This is the script for a person at the game. Each step names what to look at and which
`PROBE` lines the server log will hold, so the evidence does not rest on a description alone. The
headless half is in [README.md](README.md).

C1 (a second `AttachBeam`) is not here on purpose: the headless run showed it ends the world thread,
and a player's world would go down.

## Set-up (done by whoever deploys, with the game closed)

1. Build: `maintenance/probes/beams/build.sh` gives `maintenance/probes/beams/plugin/build/libs/beams-probe.jar`.
2. Create a **new throwaway save** in the launcher (Creative, any name; `phaseg` below). Do not use a
   save you want to keep. Quit the game.
3. Copy the jar to `UserData/Mods/`, and in `UserData/Saves/phaseg/config.json` add the entry
   `"Mods": { "probe:Beams Probe": { "Enabled": true } }` (the key is the manifest's `Group` and `Name`).
4. Remember exactly what was added, to take it out afterwards: the jar, and that one config entry.
   Deleting the save removes the rest. Nothing else is written. The jar is a plugin and an asset pack
   in one: it adds the `ProbeLog` interaction type (unused here), six `Probe_*` assets and the logging
   systems below.

The plugin writes a `PROBE` line whenever any entity gains, changes or loses a `BeamComponent`
(`BeamComponent ADDED|SET|REMOVED|STATE`, with the entity's network id, whether it is a player, a
projectile or a predicted projectile, and every beam's index, scales, nodes and target) and whenever a
projectile entity is added (`Projectile ADDED ... predictedProjectile=true|false`). The server log is
`UserData/Saves/phaseg/logs/<timestamp>_server.log`. After the session:

```bash
grep -E 'PROBE|Exception|SEVERE' UserData/Saves/phaseg/logs/*_server.log
```

## Steps

Start the game, load `phaseg`, and open chat. Keep the order.

### 0. Permission and the observer (R8)

1. `/beam clear`. The reply must be **You have no beams to remove.** That proves you hold
   `hytale:WorldEditor`. If it says you may not use the command, run `/op self` (save owner only) and
   repeat. Do not go on until this reply appears.
2. `/beam position Rope`. Reply: **Attached the beam.** A rope should run from you to a point 5 blocks
   above you. In the log there must now be a line `PROBE BeamComponent ADDED ... player=true ...`
   (and a `STATE` line with the beam). **If it is missing, stop: the observer is blind, and every
   line below would mean nothing.**
3. `/beam clear`. Reply: **Removed your beams.** The log gets `BeamComponent REMOVED ... player=true`.

### 1. C4: does `Scale` set the width? (R6)

Look at the beams from the side, a few blocks away. `/beam spawn` makes a free-standing vertical beam
at your feet that lasts `--lifetime` seconds. Take a screenshot of all three together if you can.

1. `/beam spawn Rope --length=8 --scale=0.1 --lifetime=120`
2. Walk about 4 blocks sideways. `/beam spawn Rope --length=8 --scale=3 --lifetime=120`
3. Walk about 4 blocks sideways again. `/beam spawn Rope --length=8 --scale=0.1 --targetScale=3 --lifetime=120`

For each beam, answer one word: **thin**, **thick**, **same**, or **tapered** (thin at one end, thick
at the other). If the beams look the same width but the texture is stretched or repeated differently,
say that instead of "same". The log has a `BeamComponent STATE ... networkId=...` line for each, with
`srcScale` and `tgtScale`, so the server side of each number is on record. Only a taper in the third
beam says that the two scales are widths at the two ends. The beams despawn on their own after two minutes;
leave them until you have the screenshot.

### 2. C3: a node name the model lacks (client half)

Spawn a cow near you: `/npc spawn Cow`. Stand so the cow is in view (the crosshair on it), and run each
line, then `/beam clear` after each. Say what happens on screen and look at the log.

1. Positive control, a node the cow has: `/beam entity Rope --targetNode=Pelvis`. The rope should
   end on the cow's middle. If it does not appear at all, stop and report that; the steps below cannot be
   read.
2. `/beam entity Rope --targetNode=NoSuchNode`. Where does the rope end: on the cow's feet or origin, on
   its middle, or does no rope draw? Does the game complain?
3. A non-ASCII name, which the server turns into `Caf?`: `/beam entity Rope --targetNode=Café`. The
   expected result is the same as step 2.
4. **Last, because it may disconnect you.** A name of 97 characters (one over the wire limit):
   `/beam entity Rope --targetNode=NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN`
   The server cannot serialize this update (headless: `ProtocolException: String exceeds max
   bytes: 97 > 96`). Does the rope appear? Are you disconnected, and with what message? Does the game
   stay on the world but the beam never show? Look at the log for an `Exception` or `WARN` line at
   that moment; copy it whole.

The log has a `BeamComponent STATE ... player=true ... tgtNode=...` line for steps 1 to 4 (the player
carries the beam), so the node names the server held are on record.

### 3. C2: does a predicted Hookshot shot get a rope?

`/give Tool_Hookshot`, put it in your hand and fire it at a wall about 10 blocks away (and once at the
sky). Look at the screen: does a rope run from your hand (or body) to the hook while it flies? Does the
hook fly? Does the rope stay until the hook is removed (half a second after the shot, per the page)?

The two log lines that decide it, from the moment of the shot:

- `PROBE Projectile ADDED reason=SPAWN ... projectile=true predictedProjectile=true|false`: whether the
  Hookshot's projectile carries `PredictedProjectile`.
- `PROBE BeamComponent ADDED ref=... projectile=true predictedProjectile=true|false ...`: whether a
  `BeamComponent` was added to that projectile on the server.

How to read them:

| `predictedProjectile` | `BeamComponent ADDED` on the projectile | Meaning |
|-----------------------|------------------------------------------|---------|
| `true` | yes | The client sent the `ProjectileSpawn` chain; the server ran `AttachBeam` for the predicted shot. |
| `true` | no | A predicted shot with no rope on the server. Then the rope on screen, if any, is drawn some other way. |
| `false` | yes | The shot was not predicted; the server started the chain itself. |
| `false` | no | Neither. Report what the screen showed. |

"Other viewers" cannot be seen in singleplayer and stays unverified.

## What to send back

- The `grep` output above (or the whole log).
- Screenshots of step 1 (all three beams), and a line for each of steps 2 and 3 saying what you saw.
- Anything that disconnected you, with the message.

## Taking it out

Delete the jar from `UserData/Mods/` and the `probe:Beams Probe` entry from the save's `config.json`
(or delete the `phaseg` save, then only the jar is left). The jar adds nothing else.
