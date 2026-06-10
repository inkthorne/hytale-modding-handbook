---
title: "Camera Control"
description: "Server-controlled camera in Hytale — the SetServerCamera packet and ServerCameraSettings struct for top-down / side-scroller / custom views, the built-in /player camera commands, and the JSON Camera interaction."
seo:
  type: TechArticle
---

# Camera Control

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Items` · **Verified against 0.5.4**

The server can take control of a player's camera — pulling it back into a zoomed-out
**top-down** or **side-scroller** view, repositioning it, locking its orientation, and
showing a mouse cursor for click-on-ground targeting. This powers the built-in
`/player camera topdown|sidescroller|reset` commands, and the same API is available to
plugins by sending one packet.

There are two distinct surfaces, and they do different things:

| Surface | What it does | Where |
|---------|--------------|-------|
| [`SetServerCamera` packet](#the-setservercamera-packet) (code) | Full control: zoom, reposition, lock orientation, cursor, movement remap | Java — send per-player |
| [`Camera` interaction](#the-camera-interaction-json) (JSON) | Swap first/third **perspective** only (cannot zoom or reposition) | `Interactions` JSON |

> [!WARNING]
> This is **engine-internal protocol API**, not a blessed/stable modding surface. The
> packet shape and `ServerCameraSettings` field set are read straight from
> `HytaleServer.jar` and **may shift between Hytale builds**. Field *names, types, and
> defaults* below are verified from bytecode; the client-side *effect* of several fields is
> inferred and flagged as such — verify live before relying on it.

---

## The `SetServerCamera` packet

**Package:** `com.hypixel.hytale.protocol.packets.camera` · implements `ToClientPacket`

This is the only way to get a zoomed-out / repositioned camera. (The JSON
[`Camera` interaction](#the-camera-interaction-json) can swap perspective but cannot zoom.)

```java
new SetServerCamera(
    ClientCameraView clientCameraView,   // FirstPerson | ThirdPerson | Custom
    boolean          isLocked,           // true = held under server control
    ServerCameraSettings cameraSettings  // null = clear / restore the player's normal camera
);
```

Send it to one player through their packet handler:

```java
playerRef.getPacketHandler().writeNoCache(packet);
```

`writeNoCache` writes the packet to that player's connection without caching it (the engine's
own camera commands use `writeNoCache`; a plain `write` also exists on `PacketHandler`). Get
the handler via [`PlayerRef.getPacketHandler()`](entities.md#playerref).

### `ClientCameraView`

**Package:** `com.hypixel.hytale.protocol`

| Value | Notes |
|-------|-------|
| `FirstPerson` | Default view |
| `ThirdPerson` | Standard third-person |
| `Custom` | Driven by the attached `ServerCameraSettings` |

**Every built-in command uses `Custom`** + a settings struct. Whether `FirstPerson` /
`ThirdPerson` do anything useful with a non-null settings payload is untested — no shipped
code exercises that combination.

### Clearing the camera

A `null` settings payload restores the player's normal camera. This is the "off" switch:

```java
playerRef.getPacketHandler().writeNoCache(
    new SetServerCamera(ClientCameraView.Custom, false /* isLocked */, null /* settings */));
```

The per-player [`CameraManager`](#cameramanager) component sends exactly this from its
`resetCamera(PlayerRef)` helper.

---

## `ServerCameraSettings`

**Package:** `com.hypixel.hytale.protocol`

A plain mutable struct: no-arg constructor (then assign public fields), a copy constructor, and
a full 30-arg all-fields constructor. The table lists the **default** each field holds after
`new ServerCameraSettings()` — note several differ from the all-zero you might assume (e.g. the
lerp speeds and `speedModifier` default to `1.0`, `isFirstPerson` to `true`).

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `positionLerpSpeed` | `float` | `1.0` | Camera move smoothing; presets use `0.2` |
| `rotationLerpSpeed` | `float` | `1.0` | Camera rotate smoothing; presets use `0.2` |
| `distance` | `float` | `0.0` | **Pullback distance in blocks — the main zoom/height dial.** topdown=`20`, sidescroller=`15` |
| `speedModifier` | `float` | `1.0` | Movement-speed scale *(effect inferred; presets leave it `1.0`)* |
| `allowPitchControls` | `boolean` | `false` | Lets the player tilt the camera *(effect inferred)* |
| `displayCursor` | `boolean` | `false` | Show a mouse cursor instead of the crosshair; presets set `true` |
| `displayReticle` | `boolean` | `false` | Show an aim reticle *(effect inferred)* |
| `mouseInputTargetType` | `MouseInputTargetType` | `Any` | `Any \| Block \| Entity \| None` — what the cursor can target *(effect inferred)* |
| `sendMouseMotion` | `boolean` | `false` | Stream mouse motion back to the server; the demo cam sets `true` |
| `skipCharacterPhysics` | `boolean` | `false` | *(effect inferred)* |
| `isFirstPerson` | `boolean` | `true` | Presets set `false` |
| `movementForceRotationType` | `MovementForceRotationType` | `AttachedToHead` | `AttachedToHead \| CameraRotation \| Custom`; presets use `Custom` |
| `movementForceRotation` | `Direction` | `null` | Movement frame when type=`Custom` *(effect inferred)* |
| `attachedToType` | `AttachedToType` | `LocalPlayer` | `LocalPlayer \| EntityId \| None` *(effect inferred)* |
| `attachedToEntityId` | `int` | `0` | Target entity when `attachedToType=EntityId` *(effect inferred)* |
| `eyeOffset` | `boolean` | `false` | Presets set `true` *(offsets to eye height — inferred)* |
| `positionDistanceOffsetType` | `PositionDistanceOffsetType` | `DistanceOffset` | `DistanceOffset \| DistanceOffsetRaycast \| None`; presets use `DistanceOffset` (camera sits `distance` away along rotation; the `Raycast` variant presumably stops at terrain) |
| `positionOffset` | `Position` | `null` | *(effect inferred)* |
| `rotationOffset` | `Direction` | `null` | *(effect inferred)* |
| `positionType` | `PositionType` | `AttachedToPlusOffset` | `AttachedToPlusOffset \| Custom` *(effect inferred)* |
| `position` | `Position` | `null` | *(effect inferred)* |
| `rotationType` | `RotationType` | `AttachedToPlusOffset` | `AttachedToPlusOffset \| Custom`; presets use `Custom` (fixed world-space orientation that does **not** follow player look) |
| `rotation` | `Direction` | `null` | **Camera orientation, in radians.** topdown=`(0, -π/2, 0)` = straight down. Fields are `(yaw, pitch, roll)` — so the middle component is pitch |
| `canMoveType` | `CanMoveType` | `AttachedToLocalPlayer` | `AttachedToLocalPlayer \| Always` *(effect inferred)* |
| `applyMovementType` | `ApplyMovementType` | `CharacterController` | `CharacterController \| Position` *(effect inferred)* |
| `movementMultiplier` | `Vector3fc` | `null` | sidescroller sets `(1,1,0)` to kill one movement axis |
| `applyLookType` | `ApplyLookType` | `LocalPlayerLookOrientation` | `LocalPlayerLookOrientation \| Rotation` *(effect inferred)* |
| `lookMultiplier` | `Vector2fc` | `null` | *(effect inferred)* |
| `mouseInputType` | `MouseInputType` | `LookAtTarget` | `LookAtTarget \| LookAtTargetBlock \| LookAtTargetEntity \| LookAtPlane`; presets use `LookAtPlane` (project the cursor onto a plane → click-on-ground targeting) |
| `planeNormal` | `Vector3fc` | `null` | The `LookAtPlane` plane normal; topdown=`(0,1,0)` (ground), sidescroller=`(0,0,1)` |

> [!NOTE]
> **`rotation` is in radians here.** The camera-packet path assigns a `Direction` directly
> (`new Direction(0f, -1.5707964f, 0f)` ≈ −90° pitch), so the values are raw radians — unlike
> the degrees-based `Direction` used in JSON assets (see [Networking → Direction](networking.md#direction)).
> The component order is `(yaw, pitch, roll)`; pitch `−π/2` points the camera straight down.

The nullable vector/`Direction`/`Position` fields (`rotation`, `movementMultiplier`,
`planeNormal`, the offsets, …) are genuinely optional on the wire — leaving them `null` sends a
zeroed slot, so only set the ones a given view needs.

---

## Built-in command recipes

`/player camera` is an `AbstractCommandCollection` under the `/player` command, with subcommands
`reset`, `topdown`, `sidescroller`, and `demo`. Each is an
[`AbstractTargetPlayerCommand`](commands.md#abstracttargetplayercommand): it takes an **optional
`player` argument** — with no argument it targets the sender (who must be a player); naming
another player requires the `<command>.other` permission. These are the canonical,
copy-this recipes for the API above.

### `/player camera topdown`

Zoomed-out straight-down view with a ground cursor:

```java
ServerCameraSettings s = new ServerCameraSettings();
s.positionLerpSpeed = 0.2f;
s.rotationLerpSpeed = 0.2f;
s.distance = 20.0f;
s.displayCursor = true;
s.isFirstPerson = false;
s.movementForceRotationType = MovementForceRotationType.Custom;
s.eyeOffset = true;
s.positionDistanceOffsetType = PositionDistanceOffsetType.DistanceOffset;
s.rotationType = RotationType.Custom;
s.rotation = new Direction(0f, -1.5707964f, 0f);   // pitch -90° (straight down)
s.mouseInputType = MouseInputType.LookAtPlane;
s.planeNormal = new Vector3f(0f, 1f, 0f);           // ground plane
playerRef.getPacketHandler().writeNoCache(
    new SetServerCamera(ClientCameraView.Custom, true /* isLocked */, s));
```

### `/player camera sidescroller`

Same shape as topdown but pulled in to `distance=15`, with **no** `rotation` set (default),
movement locked to two axes, and a vertical (`Z`) targeting plane:

```java
ServerCameraSettings s = new ServerCameraSettings();
s.positionLerpSpeed = 0.2f;
s.rotationLerpSpeed = 0.2f;
s.distance = 15.0f;
s.displayCursor = true;
s.isFirstPerson = false;
s.movementForceRotationType = MovementForceRotationType.Custom;
s.movementMultiplier = new Vector3f(1f, 1f, 0f);    // kill the third movement axis
s.eyeOffset = true;
s.positionDistanceOffsetType = PositionDistanceOffsetType.DistanceOffset;
s.rotationType = RotationType.Custom;
s.mouseInputType = MouseInputType.LookAtPlane;
s.planeNormal = new Vector3f(0f, 0f, 1f);
playerRef.getPacketHandler().writeNoCache(
    new SetServerCamera(ClientCameraView.Custom, true, s));
```

### `/player camera reset`

The toggle-off — `Custom`, **not** locked, `null` settings:

```java
playerRef.getPacketHandler().writeNoCache(
    new SetServerCamera(ClientCameraView.Custom, false, null));
```

### `CameraDemo` — the apply-on-join + event pattern

`/player camera demo activate|deactivate` toggles a hidden demo: it registers
`PlayerConnect` / `PlayerMouseButton` / `PlayerInteract` handlers and re-pushes a topdown-style
settings struct (`distance=20`, plus `sendMouseMotion=true`) to **every** player on connect,
then uses the streamed mouse state to place/remove blocks under the cursor. On `deactivate` it
calls `resetCamera` on each player. It's a useful reference for **applying a custom camera as
players join and reacting to cursor clicks** — see [the toggle pattern below](#toggle-pattern).

---

## Worked example: high third-person / MOBA (League-style) view

A MOBA camera is an *angled* overhead — not straight down — with a fixed (non-rotating)
orientation, the cursor visible, and click-on-ground targeting. The topdown preset already
provides everything except the angle, so derive it by softening the pitch and pulling the
distance in:

```java
ServerCameraSettings s = new ServerCameraSettings();
s.positionLerpSpeed = 0.2f;
s.rotationLerpSpeed = 0.2f;
s.distance = 16.0f;                          // pull in from topdown's 20
s.displayCursor = true;
s.isFirstPerson = false;
s.movementForceRotationType = MovementForceRotationType.Custom;
s.eyeOffset = true;
s.positionDistanceOffsetType = PositionDistanceOffsetType.DistanceOffset;
s.rotationType = RotationType.Custom;
s.rotation = new Direction(0f, -1.05f, 0f);  // ~ -60° pitch → angled overhead (vs topdown's -90°)
s.allowPitchControls = false;                // lock the angle (effect INFERRED)
s.mouseInputType = MouseInputType.LookAtPlane;
s.planeNormal = new Vector3f(0f, 1f, 0f);
playerRef.getPacketHandler().writeNoCache(
    new SetServerCamera(ClientCameraView.Custom, true, s));
```

The pitch and distance are a starting point, not engine values — tune live. Good ranges to try:
`distance` ≈ 12–20, pitch ≈ −50°…−70° (≈ −0.87…−1.22 rad).

---

## CameraManager

**Package:** `com.hypixel.hytale.server.core.entity.entities.player`

A per-player ECS `Component` the engine attaches to every player. It tracks mouse-button state
and the last cursor target (populated when `sendMouseMotion` is on), and provides the reset
helper.

```java
CameraManager cm = playerRef.getComponent(CameraManager.getComponentType());
if (cm != null) {
    cm.resetCamera(playerRef);  // sends SetServerCamera(Custom, false, null) + clears mouse state
}
```

| Member | Description |
|--------|-------------|
| `static ComponentType<EntityStore, CameraManager> getComponentType()` | The component type, for `getComponent(...)` |
| `void resetCamera(PlayerRef ref)` | Send the clear packet and forget mouse state |
| `MouseButtonState getMouseButtonState(MouseButtonType)` | Current state of a mouse button |
| `Vector3i getLastMouseButtonPressedPosition(MouseButtonType)` | Block the cursor was over when pressed |
| `Vector3i getLastMouseButtonReleasedPosition(MouseButtonType)` | Block the cursor was over when released |
| `Vector3i getLastTargetBlock()` / `Vector2dc getLastScreenPoint()` | Last cursor target block / screen point |

> If you want your camera state to participate in ECS like the engine's does, store it in your
> own per-player component; otherwise a plugin-side `Set<UUID>` of "who's in the custom view" is
> enough (see below).

---

## Toggle pattern

The camera has no single toggle — "off" is its own packet (`Custom, false, null`). So a toggle is
per-player state plus a trigger:

1. **Track who's in the custom view** — a `Set` keyed by player UUID, or a custom per-player
   `Component` if you want ECS participation like `CameraManager`.
2. **Trigger via a registered command** (mirrors the engine — simplest) or an item interaction
   that calls into plugin code. The JSON [`Camera` interaction](#the-camera-interaction-json)
   alone cannot express a zoomed view, so a zoomed toggle must run Java.
3. **Always reset on logout and death.** Because `isLocked=true` holds the camera under server
   control, a player who disconnects while in the view can be stranded in it on rejoin. Send the
   reset packet from a `PlayerDisconnectEvent` handler (and on death) for everyone you've tracked.

```java
// Sketch: a registered command that toggles the topdown view, with logout cleanup.
private final Set<UUID> inView = ConcurrentHashMap.newKeySet();

void toggle(PlayerRef playerRef, UUID uuid) {
    if (inView.remove(uuid)) {
        playerRef.getPacketHandler().writeNoCache(
            new SetServerCamera(ClientCameraView.Custom, false, null));     // off
    } else {
        inView.add(uuid);
        playerRef.getPacketHandler().writeNoCache(
            new SetServerCamera(ClientCameraView.Custom, true, topdown())); // on
    }
}

// In setup(): clear on disconnect so isLocked never strands a player.
events.register(PlayerDisconnectEvent.class, e -> inView.remove(e.getPlayerRef().getUuid()));
```

---

## The `Camera` interaction (JSON)

A `Camera`-type interaction inside an item's `Interactions` chain can switch the player between
first- and third-person **perspective**. It **cannot** zoom or reposition — that is the
[packet path](#the-setservercamera-packet) only.

Real shipped example — `Server/Item/Items/_Debug/Test_Camera_Item.json` (the only asset in 0.5.4
that uses this interaction type, and it only exercises `ForcePerspective`):

```json
"Next": {
  "Type": "Camera",
  "Action": "ForcePerspective",
  "Perspective": "Third",
  "CameraInteractionTime": 5
}
```

Keys (verified against the `CameraInteraction` codec; the interaction is a `SimpleInteraction`, so
it also accepts all of [Simple's inherited keys](interactions-combat.md#inherited-properties-from-interaction)
such as `Effects`, `RunTime`, `Next`, `Failed`):

| JSON key | Type / values | Default | Codec description |
|----------|---------------|---------|-------------------|
| `Action` | `ForcePerspective \| Orbit \| Transition` | `ForcePerspective` | "What kind of camera action should we take" |
| `Perspective` | `First \| Third` | `First` | "What camera perspective we want this interaction to take place in" |
| `PersistCameraState` | boolean | `false` | "Should the camera state from this interaction persist to the next camera interaction. If the next interaction is null or not a camera interaction then this field does nothing." |
| `CameraInteractionTime` | float (seconds) | `0` | "How long this camera action lasts for" |

> **Open questions (JSON side).** Only `ForcePerspective` is exercised by a shipped asset; the
> JSON parameters that `Orbit` and `Transition` expect are unknown. `PersistCameraState` is the
> confirmed JSON key for the persist flag.

### The `Camera` property (keyframe arrays)

Separately from the `Camera` interaction *type*, **any** interaction carries an optional `Camera`
*property* of type `InteractionCameraSettings` (the row noted on
[Combat & Effects Interactions](interactions-combat.md#inherited-properties-from-interaction)).
It holds two keyframe arrays that animate the camera while the interaction runs:

```json
"Camera": {
  "FirstPerson": [
    { "Time": 0.1, "Position": [0, 0, 0], "Rotation": [0, 0, 0] }
  ],
  "ThirdPerson": [
    { "Time": 0.1, "Position": [0, 0, 0], "Rotation": [0, 0, 0] }
  ]
}
```

Each keyframe (`InteractionCamera`):

| JSON key | Type | Default | Notes |
|----------|------|---------|-------|
| `Time` | float | `0.1` | Seconds; **must be > 0**, and entries in each array must be in strictly increasing `Time` order (validator rejects ties/out-of-order) |
| `Position` | `Vector3f` | `[0,0,0]` | Camera offset; non-null |
| `Rotation` | `Direction` | `[0,0,0]` | **In degrees** — the codec multiplies each component by π/180 on load (yaw/pitch/roll). Non-null |

> **No shipped asset uses these `FirstPerson`/`ThirdPerson` keyframe arrays on an interaction**
> in 0.5.4 (the `"Camera"` blocks you'll find in `Server/Models/**` are a *different*, model-camera
> schema with `PositionOffset` / `Yaw` / `Pitch`). The schema above is verified from the codec, but
> has no in-game example to copy.

---

## Adjacent camera systems

Out of scope for the packet/interaction surface above, but worth knowing they exist:

- **Fly / spectator cam** — packets `SetFlyCameraMode` / `RequestFlyCameraMode`, module
  `FlyCameraModule`. A separate mechanism from `SetServerCamera`; not documented here.
- **Camera shake / effects** — an asset family under `Server/Camera/CameraEffect/**` (per-weapon
  swings like `Battleaxe`, `Sword`, `Unarmed`, plus `Damage`, `Impact`, `NPC`), `Server/Camera/CameraShake`,
  and `Server/Camera/ViewBobbing`. The `Effects.CameraEffect` string on an interaction
  ([Combat & Effects → Effects](interactions-combat.md#effects-configuration)) references one of
  these by id. Protocol/runtime types include `CameraShake`, `CameraShakeConfig`,
  `CameraShakeEffect`, and the `UpdateCameraShake` packet.
- **Per-model camera** — a model's own `Camera` block (`CameraSettings`: `PositionOffset`, and
  `Yaw`/`Pitch` as `CameraAxis` head-look limits) is distinct from everything above.

---

## Gotchas & Errors

- **A locked camera with no reset strands the player.** `isLocked=true` keeps the camera under
  server control; if the player disconnects (or dies) while in a custom view and you never send
  the `null`-settings reset, they can come back stuck. Reset on `PlayerDisconnectEvent` and on
  death. ([toggle pattern](#toggle-pattern))
- **`rotation` is radians in the packet, degrees in JSON.** `ServerCameraSettings.rotation` takes
  raw radians (`-π/2` for straight down); the JSON keyframe `Rotation` is authored in degrees and
  converted by the codec. Mixing them up rotates the camera by a factor of ~57.
- **Defaults aren't all zero.** `new ServerCameraSettings()` starts with `positionLerpSpeed`,
  `rotationLerpSpeed`, and `speedModifier` at `1.0` and `isFirstPerson` at `true`. If you copy only
  part of a preset, the rest are these defaults, not zeros.
- **The JSON `Camera` interaction can't zoom.** It only flips perspective. For a zoomed/repositioned
  view you must send `SetServerCamera` from Java.
- **`Time` keyframes must strictly increase.** Two entries with equal (or descending) `Time` in a
  `FirstPerson`/`ThirdPerson` array fail validation (`Camera entry with time: <t> conflicts with another entry`).

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
