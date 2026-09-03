---
title: "Math / Vector API"
description: "Hytale's Java math library — JOML vectors (Vector3d/Vector3f/Vector3i), the Vector*Util companion classes, Rotation3f, Transform, Location, shapes, and utilities for positions, velocities, directions, and rotations."
seo:
  type: TechArticle
---

# Math / Vector API

**Doc type:** Java API · **Verified against 0.5.9**

## Overview

Hytale's math is built on **[JOML](https://github.com/JOML-CI/JOML) (`org.joml`)** — the vectors, matrices, and
quaternions you pass around are plain JOML types (`Vector3d`, `Vector3f`, `Vector3i`, `Matrix4d`, …). Hytale-specific
**constants and helpers** that JOML doesn't ship live in companion `*Util` classes under
`com.hypixel.hytale.math.vector` (`Vector3dUtil`, `Vector3iUtil`, …). Rotations are **not** a vector — they use the
dedicated `Rotation3f` type.

> [!IMPORTANT]
> Update 5 migrated the math library to JOML. The old custom vector classes that lived under the
> `math.vector` package (the former `Vector3d` / `Vector3f` / `Vector3i` / `Vector3l` / `Vector2d` / `Vector2i` /
> `Vector4d`) and the old `math.matrix` `Matrix4d` no longer exist. If you are porting older code:
> - former `math.vector` `Vector3d` → **`org.joml.Vector3d`** (likewise `Vector3f`, `Vector3i`, `Vector2d`, `Vector2i`, `Vector4d`)
> - a `Vector3f` used as a **rotation** → **`Rotation3f`** (in `com.hypixel.hytale.math.vector`)
> - static helpers/constants that used to hang off the vector class itself now live on the companion: e.g. **`Vector3dUtil.ZERO`** and **`Vector3dUtil.directionTo(...)`**
> - accessors `getX()/getY()/getZ()` → JOML `x()/y()/z()` (or the public `x`/`y`/`z` fields)
> - `assign(...)` → `set(...)`, `subtract(...)` → `sub(...)`, `scale(...)` → `mul(...)`, `addScaled(d, s)` → `fma(s, d)`
> - `distanceTo` → `distance`, `distanceSquaredTo` → `distanceSquared`

### Core Types

| Class | Package | Precision | Primary Use |
|-------|---------|-----------|-------------|
| `Vector3d` | `org.joml` | double | Positions, velocities, directions |
| `Vector3i` | `org.joml` | int | Block positions |
| `Vector3f` | `org.joml` | float | Float 3D data |
| `Vector2d` / `Vector2i` | `org.joml` | double / int | 2D positions, grid positions |
| `Vector4d` | `org.joml` | double | Homogeneous coords (matrix transforms) |
| `Rotation3f` | `math.vector` | float | Rotations (pitch / yaw / roll) |
| `Transform` | `math.vector` | mixed | Position (`Vector3d`) + rotation (`Rotation3f`) |
| `Location` | `math.vector` | mixed | World name + position + rotation |

### Advanced Types

| Class | Package | Description |
|-------|---------|-------------|
| `Matrix4d` | `org.joml` | 4x4 transformation matrix (translate, rotate, scale, project) |
| `Box` | `math.shape` | Axis-aligned bounding box (AABB) |
| `Axis` | `math` | Enum for X, Y, Z axes |
| `MathUtil` | `math.util` | Static scalar math utilities |
| `Vector3dUtil` / `Vector3iUtil` / … | `math.vector` | Constants + helpers for the JOML vector types |

## Architecture
```
org.joml                                             JOML vectors / matrices / quaternions
├── Vector3d / Vector3f / Vector3i                   3D vectors (double/float/int)
├── Vector2d / Vector2i                              2D vectors
├── Vector4d                                         4D vector (matrix transforms)
└── Matrix4d                                         4x4 transformation matrix

com.hypixel.hytale.math
├── vector
│   ├── Vector3dUtil / Vector3iUtil / Vector2dUtil   constants + helpers for the JOML types
│   ├── Vector3fUtil / Vector4dUtil / Matrix*        (companions; see Matrix4dUtil under math.matrix)
│   ├── VectorBoxUtil / VectorSphereUtil              filter position collections by box / sphere volume
│   ├── Rotation3f / Rotation3fc                      rotation (pitch/yaw/roll); read-only view interface
│   ├── Transform                                     position (Vector3d) + rotation (Rotation3f)
│   └── Location                                      world + position + rotation
├── matrix.Matrix4dUtil                               Matrix4d → float[] helper
├── shape.Box                                         axis-aligned bounding box (AABB)
├── raycast.RaycastAABB                               ray-vs-AABB intersection
├── util.MathUtil                                     static scalar math utilities
├── util.FastRandom / HashUtil / TrigMathUtil         fast seedable RNG · coordinate hashing · table trig
├── iterator.LineIterator / SpiralIterator            block-line walk · outward chunk spiral
├── random.RandomExtra                                convenience sampling (ThreadLocalRandom)
├── codec.Vector3iArrayCodec / IntRangeArrayCodec     [x, y, z] / [min, max] array codecs
├── Axis                                              X / Y / Z enum
└── Range                                             numeric range

(server-side ECS) server.core.modules.entity.component.TransformComponent
```

## JOML vectors in one minute

JOML methods follow a consistent convention worth internalising:

- **Mutating vs. result-into-dest.** Most operations have two overloads. `a.add(b)` mutates `a` in place and returns
  `this` (chainable). `a.add(b, dest)` writes the result into `dest` and leaves `a` untouched. Use the dest overload
  when you must not clobber a shared/source vector.
- **Read-only interfaces.** `Vector3dc` / `Vector3ic` / `Vector3fc` (the `c` = "const") are read-only views.
  Hytale's constants and many API parameters are typed against them. A mutable `Vector3d` *is* a `Vector3dc`, so you
  can pass one anywhere a `Vector3dc` is wanted; to mutate a `Vector3dc` you've been handed, copy it first
  (`new Vector3d(thatConst)`).
- **Accessors.** `v.x()`, `v.y()`, `v.z()` (or the public `v.x`/`v.y`/`v.z` fields).

```java
Vector3d a = new Vector3d(1, 64, -5);
Vector3d b = new Vector3d(2, 0, 3);

a.add(b);                      // a is now (3, 64, -2)
Vector3d sum = a.add(b, new Vector3d());   // sum = a+b; a unchanged
double dist = a.distance(b);
double d = a.dot(b);
a.normalize();                 // unit length, in place
```

## Vector3d

**Package:** `org.joml`

Double-precision 3D vector — entity positions, velocities, directions.

### Creating Vectors

```java
Vector3d pos = new Vector3d(10.0, 64.0, -5.0);
Vector3d origin = new Vector3d();          // (0, 0, 0)
Vector3d copy = new Vector3d(other);       // copy of a Vector3d / Vector3dc

// From Transform
Transform transform = playerRef.getTransform();
Vector3d position = transform.getPosition();

// From TransformComponent
TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());
Vector3d entityPos = tc.getPosition();
```

### Accessors & Assignment

```java
double x = vec.x();      // also vec.y(), vec.z(); or the public fields vec.x / vec.y / vec.z

vec.set(10.0, 64.0, -5.0);   // assign components (replaces old assign())
vec.set(other);              // copy from another vector
vec.setComponent(0, 10.0);   // by index (0=x, 1=y, 2=z)
```

### Arithmetic

Every method below has a "mutate in place" form and a "write into dest" form (see
[JOML vectors in one minute](#joml-vectors-in-one-minute)).

```java
vec.add(x, y, z);              // or add(other) / add(other, dest)
vec.sub(other);                // subtract (was subtract())
vec.mul(factor);               // scale all components (was scale())
vec.mul(other);                // component-wise multiply
vec.fma(scale, dir);           // vec += dir * scale  (was addScaled())
vec.negate();                  // flip sign
```

### Vector Math

```java
double len   = vec.length();
double lenSq = vec.lengthSquared();   // faster, avoids sqrt

vec.normalize();                      // unit length, in place
vec.normalize(5.0);                   // scale to a specific length

double dot = vec.dot(other);
vec.cross(other);                     // in place; or cross(other, dest)

double dist   = vec.distance(other);        // was distanceTo()
double distSq = vec.distanceSquared(other); // was distanceSquaredTo(); faster

vec.min(other);   // component-wise min, in place
vec.max(other);   // component-wise max, in place
vec.lerp(other, 0.5);   // linear interpolation toward other
```

### Rounding & Conversion

```java
vec.floor();   // round each component down (in place)
vec.ceil();    // round each component up
vec.absolute();

Vector3i blockPos = Vector3dUtil.toVector3i(vec);   // FLOORS each component (MathUtil.floor), so -0.5 → -1
Vector3f floatVec = new Vector3f(vec);              // JOML cross-construction
```

> **See also:** [Transform Component](components.md#transformcomponent)

---

## Vector3dUtil

**Package:** `com.hypixel.hytale.math.vector`

Companion class holding the Hytale-specific **constants** and **helpers** for `Vector3d` that JOML itself doesn't
provide. (`Vector3iUtil`, `Vector2dUtil`, `Vector3fUtil`, `Vector4dUtil` are the analogous companions for the other
JOML types.)

### Constants

All are typed `Vector3dc` (read-only). Copy into a `new Vector3d(...)` if you need to mutate.

```java
Vector3dUtil.ZERO
Vector3dUtil.UP, Vector3dUtil.DOWN            // Y axis (aliases POS_Y / NEG_Y)
Vector3dUtil.FORWARD, Vector3dUtil.BACKWARD   // Z axis (aliases NEG_Z / POS_Z)
Vector3dUtil.RIGHT, Vector3dUtil.LEFT         // X axis (aliases POS_X / NEG_X)
Vector3dUtil.NORTH, Vector3dUtil.SOUTH        // Z axis aliases
Vector3dUtil.EAST, Vector3dUtil.WEST          // X axis aliases
Vector3dUtil.ALL_ONES
Vector3dUtil.MIN, Vector3dUtil.MAX            // component extremes
```

### Helpers

```java
// Unit direction from one point to another
Vector3d dir = Vector3dUtil.directionTo(from, to);

// Direction from yaw/pitch angles, written into dest
Vector3d dir = Vector3dUtil.setYawPitch(yaw, pitch, new Vector3d());

// Display formatting
String str = Vector3dUtil.formatShortString(vec);

// Conversion / near-zero handling
Vector3i blockPos = Vector3dUtil.toVector3i(vec);   // floors each component (correct for block coords)
Vector3dUtil.clipToZero(vec, epsilon);        // any component with |v| <= epsilon becomes 0 (in place)
boolean nearZero = Vector3dUtil.closeToZero(vec, epsilon);   // every component within +/- epsilon of 0
Vector3dUtil.sanitizeNonFinite(vec);          // 0.6.3+: NaN/Infinite components → 0 (in place)

// 0.6.3+: quadratic Bézier point at t in [0, 1], written into dest
Vector3d p = Vector3dUtil.quadraticBezier(p0, control, p2, t, new Vector3d());
```

### Codec

```java
Vector3dUtil.CODEC            // BuilderCodec<Vector3d> — for JSON/network serialization
Vector3dUtil.AS_ARRAY_CODEC   // serializes as a [x, y, z] array
```

---

## Vector3i

**Package:** `org.joml`

Integer 3D vector — block positions. Same JOML conventions as `Vector3d` (`x()/y()/z()`, `set`, `add`, `sub`, `mul`,
`distance`, `gridDistance`, mutate-or-dest overloads).

```java
Vector3i block = new Vector3i(10, 64, -5);
block.add(0, 1, 0);                 // move up one block
Vector3d asDouble = Vector3iUtil.toVector3d(block);
```

### Vector3iUtil

**Package:** `com.hypixel.hytale.math.vector`

Constants and helpers for `Vector3i`.

```java
// Constants (Vector3ic)
Vector3iUtil.ZERO, Vector3iUtil.UP, Vector3iUtil.DOWN, Vector3iUtil.ALL_ONES, …
Vector3iUtil.MIN, Vector3iUtil.MAX

// Block-face direction arrays
Vector3iUtil.BLOCK_SIDES      // 6 face directions
Vector3iUtil.BLOCK_EDGES      // 12 edge directions
Vector3iUtil.BLOCK_CORNERS    // 8 corner directions
Vector3iUtil.BLOCK_PARTS      // all parts, grouped

// Helpers
Vector3i lower = Vector3iUtil.min(a, b);
Vector3i upper = Vector3iUtil.max(a, b);
Vector3d asDouble = Vector3iUtil.toVector3d(blockPos);
long cells = Vector3iUtil.inclusiveBoxVolume(minX, minY, minZ, maxX, maxY, maxZ);  // 0.6.3+: block count, both corners inclusive
```

---

## Vector3f

**Package:** `org.joml`

Float `Vector3f` and the 2D/4D JOML vectors (`Vector2d`, `Vector2i`, `Vector4d`) follow the same conventions as
`Vector3d` above (JOML supplies the arithmetic; Hytale adds the `*Util` companions).

- `Vector3fUtil.ZERO` and `Vector3fUtil.CODEC` are the float companions (JOML supplies the float arithmetic).
- `Vector2dUtil` adds 2D constants (`ZERO`, `UP`, `DOWN`, `LEFT`, `RIGHT`, …) and `Vector2dUtil.DIRECTIONS` (cardinal array).
- `Vector4d` is used for homogeneous coordinates with `Matrix4d`. `Vector4dUtil.perspectiveTransform(vec4d)` divides
  xyz by w, and `Vector4dUtil.isInsideFrustum(vec4d)` tests the view frustum.

---

## Rotation3f

**Package:** `com.hypixel.hytale.math.vector`

A rotation expressed as **(pitch, yaw, roll)** in degrees. This replaces the old "Vector3f as rotation" usage — a
rotation is now its own type, with a read-only view interface `Rotation3fc`.

### Conventions

- **X / pitch**: look up/down (−90 to 90)
- **Y / yaw**: compass direction (0–360)
- **Z / roll**: tilt left/right

### Constants

```java
Rotation3f.ZERO       // (0, 0, 0)
Rotation3f.IDENTITY
Rotation3f.NaN
```

### Construction & Accessors

```java
Rotation3f rot = new Rotation3f();                // zero rotation
Rotation3f rot = new Rotation3f(pitch, yaw, roll);
Rotation3f copy = new Rotation3f(otherRotation);  // from Rotation3fc

float pitch = rot.pitch();   // == rot.x()
float yaw   = rot.yaw();     // == rot.y()
float roll  = rot.roll();    // == rot.z()

rot.setPitch(45.0f);   // also setYaw / setRoll, and setX / setY / setZ
rot.addPitch(5.0f);    // also addYaw / addRoll
```

### Arithmetic & Axis Helpers

```java
rot.set(pitch, yaw, roll);     // also set(Rotation3fc) / set(float[])
rot.add(otherRotation);        // also add(p, y, r)
rot.sub(otherRotation);
rot.mul(factor);
rot.negate();

rot.addRotationOnAxis(Axis.Y, 90);   // int degrees
rot.flipRotationOnAxis(Axis.Y);
```

### Interpolation & Look-At (static)

```java
Rotation3f mid = Rotation3f.lerp(start, end, 0.5f);
Rotation3f pos = Rotation3f.lerpUnclamped(start, end, t);
Rotation3f rot = Rotation3f.lerpAngle(start, end, 0.5f);   // handles wrap-around
Rotation3f rot = Rotation3f.lerpAngle(start, end, 0.5f, result);

// Rotation that faces a direction vector (parameters are read-only Vector3dc, so any Vector3d works)
Rotation3f look = Rotation3f.lookAt(directionVec3d);
Rotation3f look = Rotation3f.lookAt(directionVec3d, result);
Rotation3f look = Rotation3f.lookAt(dx, dy, dz);              // 0.6.3+: component form
Rotation3f look = Rotation3f.lookAt(fromPos, toPos);          // 0.6.3+: from one point toward another
Rotation3f look = Rotation3f.lookAt(fromPos, toPos, result);  //        (also with a result parameter)
```

### Non-finite guard

```java
boolean ok = rot.isFinite();   // false if any component is NaN/Infinite
rot.sanitizeNonFinite();       // 0.6.3+: replace NaN/Infinite components with 0, in place
```

### Applying a Rotation

```java
// Rotate a vector by this rotation
Vector3d rotated = rot.transform(new Vector3d(0, 0, 1));   // in place; or transform(src, dest)

// As a JOML quaternion (e.g. for matrix math)
Quaterniond q = rot.getQuaternion(new Quaterniond());
```

---

## Transform

**Package:** `com.hypixel.hytale.math.vector`

Combines position (`Vector3d`) and rotation (`Rotation3f`) into a single value type.

### Getting Transform

```java
Transform transform = playerRef.getTransform();

// From TransformComponent
TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());
Transform transform = tc.getTransform();

// Construction
Transform t = new Transform(x, y, z);
Transform t = new Transform(x, y, z, pitch, yaw, roll);
Transform t = new Transform(positionVec3d, rotation);
```

### Accessing Components

```java
Vector3d position = transform.getPosition();
Rotation3f rotation = transform.getRotation();

transform.setPosition(newPos);   // accepts Vector3dc
transform.setRotation(newRot);   // accepts Rotation3fc
```

### Direction Calculations

```java
// Facing direction as a unit vector
Vector3d direction = transform.getDirection();

// Facing direction from angles (static)
Vector3d dir = Transform.getDirection(pitch, yaw);

// Nearest cardinal direction
Axis axis = transform.getAxis();
Vector3i axisDir = transform.getAxisDirection();
Vector3i axisDir = transform.getAxisDirection(pitch, yaw);
```

### Relative-Transform Flags

`Transform` carries bit-flag constants for masked relative application (used by commands/tools):
`X_IS_RELATIVE`, `Y_IS_RELATIVE`, `Z_IS_RELATIVE`, `YAW_IS_RELATIVE`, `PITCH_IS_RELATIVE`, `ROLL_IS_RELATIVE`,
`RELATIVE_TO_BLOCK`.

```java
Transform.applyMaskedRelativeTransform(base, mask, posOffset, rotOffset, blockOffset);
```

---

## Location

**Package:** `com.hypixel.hytale.math.vector`

A `Transform` plus the **world** it lives in: world name + position (`Vector3d`) + rotation (`Rotation3f`). Useful
when a position only makes sense alongside which world it's in (waypoints, homes, saved spots).

```java
Location loc = new Location("world", x, y, z);
Location loc = new Location("world", x, y, z, pitch, yaw, roll);
Location loc = new Location("world", transform);

String world      = loc.getWorld();
Vector3d position = loc.getPosition();
Rotation3f rot    = loc.getRotation();
Vector3d facing   = loc.getDirection();
Axis axis         = loc.getAxis();

Transform transform = loc.toTransform();   // drop the world name
```

---

## TransformComponent

**Package:** `com.hypixel.hytale.server.core.modules.entity.component`

ECS component that stores an entity's position and rotation. Unlike `Transform` (a value type), this is a live
component attached to an entity.

### Getting the Component

```java
TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());

// Or in chunk iteration
TransformComponent tc = chunk.getComponent(index, TransformComponent.getComponentType());
```

### Reading Position/Rotation

```java
Vector3d pos = tc.getPosition();
Rotation3f rot = tc.getRotation();
Transform transform = tc.getTransform();
```

### Modifying Position/Rotation

```java
// Regular updates (interpolated on client)
tc.setPosition(newPos);
tc.setRotation(newRot);

// Instant teleport (no interpolation)
tc.teleportPosition(newPos);
tc.teleportRotation(newRot);
```

### Chunk-section linkage (0.6.3+)

The component also records which **chunk section** (32×32×32 `ChunkSection` entity in the `ChunkStore`) the entity currently lives in — engine-maintained, but readable when you need the section's ECS `Ref`:

```java
Ref<ChunkStore> section = tc.getSectionRef();   // null until the entity has been placed in a loaded section
tc.setSectionLocation(sectionRef);              // engine-side: called when the entity crosses a section boundary
```

The 0.5.9 column-chunk accessors `getChunk()` / `getChunkRef()` / `setChunkLocation(...)` / `markChunkDirty(...)` were removed by 0.6.3 (the world moved from column `WorldChunk` tracking to per-section tracking); `getSectionRef()` is the replacement.

### Transform vs TransformComponent

| Aspect | Transform | TransformComponent |
|--------|-----------|-------------------|
| Type | Value object | ECS Component |
| Storage | Local variable | Entity store |
| From PlayerRef | `playerRef.getTransform()` | N/A |
| From Store | N/A | `store.getComponent(ref, ...)` |
| Mutability | Modify affects local copy | Modify affects entity |

---

## Common Patterns

### Calculate Direction Between Entities

```java
Vector3d myPos = myTc.getPosition();
Vector3d targetPos = targetTc.getPosition();
Vector3d direction = Vector3dUtil.directionTo(myPos, targetPos);
```

### Apply Knockback

```java
// Copy first so we don't mutate the shared direction vector
Vector3d knockback = new Vector3d(direction).normalize().mul(knockbackForce);
knockback.y = upwardForce;   // add vertical component (public field)

Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
velocity.addInstruction(knockback, new VelocityConfig(), ChangeVelocityType.Add);
```

### Check Distance

```java
Vector3d posA = transformA.getPosition();
Vector3d posB = transformB.getPosition();

// Use squared distance for comparisons (faster)
double distSq = posA.distanceSquared(posB);
if (distSq < radius * radius) {
    // Within radius
}
```

### Get Block Position from Entity

```java
Vector3d entityPos = tc.getPosition();
Vector3i blockPos = Vector3dUtil.toVector3i(entityPos);   // floors each component — correct on both sides of 0
```

### Look At Target

```java
Transform myTransform = playerRef.getTransform();
Vector3d targetPos = targetEntity.getPosition();

Vector3d toTarget = new Vector3d(targetPos).sub(myTransform.getPosition());
Rotation3f lookRotation = Rotation3f.lookAt(toTarget);
```

---

## Matrix4d

**Package:** `org.joml`

Hytale uses JOML's full-featured `Matrix4d` directly (translation, rotation, scaling, projection, view matrices —
see the [JOML docs](https://github.com/JOML-CI/JOML)). Hytale adds one companion helper:

```java
// 16-element float[] (column-major) — handy for shipping a matrix to the client/GPU
float[] data = Matrix4dUtil.asFloatData(matrix);
```

---

## Axis

**Package:** `com.hypixel.hytale.math`

Enum representing the three coordinate axes.

### Values

```java
Axis.X
Axis.Y
Axis.Z
```

### Methods

```java
Vector3ic dir = axis.getDirection();   // unit vector along the axis (read-only)

// Rotate vectors around this axis (90° increments)
axis.rotate(Vector3i vec, int steps);
axis.rotate(Vector3d vec, int steps);
axis.rotate(Vector3i vec);             // single 90° rotation
axis.rotate(Vector3d vec);

// Flip vectors on this axis
axis.flip(Vector3i vec);
axis.flip(Vector3d vec);

// Flip a rotation component
axis.flipRotation(Rotation3f rotation);
```

---

## Box (AABB)

**Package:** `com.hypixel.hytale.math.shape`

Axis-Aligned Bounding Box for collision detection and spatial queries. Its `min` / `max` corners are
`org.joml.Vector3d`.

### Construction

```java
Box box = new Box();                              // empty
Box box = new Box(min, max);                      // from Vector3d corners
Box box = new Box(minX, minY, minZ, maxX, maxY, maxZ);
Box box = Box.cube(center, size);                 // cube at position
Box box = Box.centeredCube(center, size);         // centered cube
Box box = Box.horizontallyCentered(width, height, depth);

Box.UNIT  // unit box constant
```

### Dimensions

```java
double w = box.width();    // X extent
double h = box.height();   // Y extent
double d = box.depth();    // Z extent
double dim = box.dimension(Axis.Y);

double vol = box.getVolume();
double thick = box.getThickness();
double maxExtent = box.getMaximumExtent();
boolean hasVol = box.hasVolume();
```

### Center Points

```java
double mx = box.middleX();
double my = box.middleY();
double mz = box.middleZ();
```

### Modification

```java
box.assign(other);
box.assign(minX, minY, minZ, maxX, maxY, maxZ);
box.setMinMax(min, max);
box.setEmpty();
box.normalize();  // ensure min < max

box.offset(x, y, z);
box.offset(vec3d);
box.scale(factor);
box.expand(amount);
box.extend(x, y, z);

box.rotateX(angle);
box.rotateY(angle);
box.rotateZ(angle);
```

### Collision Detection

```java
boolean hit = box.isIntersecting(other);
boolean contains = box.containsPosition(x, y, z);
boolean contains = box.containsBlock(x, y, z);
boolean intersects = box.intersectsLine(start, end);
```

### Combining Boxes

```java
box.union(other);           // expand to include other
box.minkowskiSum(other);    // Minkowski sum
box.sweep(direction);       // expand along direction
```

### Block Iteration

```java
// Iterate all blocks within the box
box.forEachBlock(offsetX, offsetY, offsetZ, scale, (x, y, z) -> {
    // Process block at x, y, z
    return true;  // continue iteration
});
```

> **See also:** [Collision API](collision.md#boxcollisiondata)

---

## Block Shape Iteration

**Package:** `com.hypixel.hytale.math.block`

A family of static utilities that enumerate the integer block coordinates forming a geometric shape — spheres, cubes, cones, cylinders, domes, pyramids, tori, and diamonds. These are the math behind builder-tool brushes: they generate coordinates only and have **no world dependency**, so you pair them with your own chunk/world block-set calls (see [World block access](blocks.md#world-block-access)) to actually place or inspect blocks.

Each call is a zero-allocation visitor: it invokes a `TriIntObjPredicate<T>` once per block position, threading a caller-supplied context object `T` through every callback so no lambda capture is needed on hot paths.

### Key Classes

| Class | Shape |
|-------|-------|
| `BlockSphereUtil` | Solid/surface sphere (also `forEachBlockExact` with a `double` radius) |
| `BlockCubeUtil` | Axis-aligned box (int args or two `Vector3i` corners) |
| `BlockConeUtil` | Cone, plus `forEachBlockInverted` for an upside-down cone |
| `BlockCylinderUtil` | Cylinder |
| `BlockDomeUtil` | Hemisphere (dome) |
| `BlockInvertedDomeUtil` | Inverted hemisphere |
| `BlockPyramidUtil` | Pyramid |
| `BlockTorusUtil` | Torus |
| `BlockDiamondUtil` | Octahedron (diamond) |
| `BlockUtil` | Block-coordinate packing helpers (below) — not a shape |

### The callback contract

```java
// com.hypixel.hytale.function.predicate.TriIntObjPredicate<T>
boolean test(int x, int y, int z, T context);   // return true to continue, false to stop early
```

Every overload has the same shape:

```
forEachBlock(originX, originY, originZ, <dimensions…>, [thickness], [flags…], context, callback)
```

- The leading three `int`s are the **origin**. Every shape is centred on it in X/Z, but the **vertical
  anchoring differs per shape** — see the table. (The one overload that takes no origin is
  `BlockCubeUtil.forEachBlock(Vector3i pointOne, Vector3i pointTwo, …)`, which takes two opposite
  corners in either order and normalises them internally.)
- The **dimension** `int`s that follow differ per shape (table below) and must be `> 0`: every
  utility except `BlockCubeUtil` throws `IllegalArgumentException` on a zero or negative
  radius/height. `BlockCubeUtil` is the exception — it validates nothing, so a bad extent degenerates
  silently rather than throwing.
- An optional `thickness` `int` turns the shape into a shell of that many blocks; `thickness < 1`
  falls through to the solid form.
- Trailing `boolean`s are, in order: `capped` (`cappedTop`/`cappedBottom` on `BlockCubeUtil`) — close
  the shell's ends; `hollow` (`BlockCubeUtil` only) — emit the **interior** instead of the shell;
  `evenXZ` / `evenY` (spelled `evenH` on the height-based shapes) — shrink the positive side by one so
  the span is an even number of blocks.
- Return type is `boolean` (`true` = iteration ran to completion) on `BlockCubeUtil`,
  `BlockCylinderUtil`, `BlockDomeUtil`, `BlockInvertedDomeUtil`, `BlockTorusUtil`, `BlockDiamondUtil`
  and the three-radius `BlockSphereUtil` overloads; `void` on `BlockConeUtil`, `BlockPyramidUtil` and
  `BlockSphereUtil`'s single-`radius` / `forEachBlockExact` overloads.

| Class | Dimensions after the origin | Vertical extent relative to `originY` |
|-------|-----------------------------|----------------------------------------|
| `BlockSphereUtil` | `radius`, or `radiusX, radiusY, radiusZ`, or `forEachBlockExact(…, double radius, …)` | centred: `-radiusY … +radiusY` |
| `BlockDiamondUtil` | `radiusX, radiusY, radiusZ` | centred: `-radiusY … +radiusY` |
| `BlockTorusUtil` | `outerRadius, minorRadius` | centred: `-minorRadius … +minorRadius` |
| `BlockCubeUtil` | `radiusX, height, radiusZ` | centred: `±height / 2` |
| `BlockCylinderUtil` / `BlockConeUtil` / `BlockPyramidUtil` | `radiusX, height, radiusZ` (**height** in the middle slot, not `radiusY`) | origin is the **base**: `0 … height - 1`, growing up |
| `BlockDomeUtil` | `radiusX, radiusY, radiusZ` | origin is the base: `0 … radiusY`, growing up |
| `BlockInvertedDomeUtil` | `radiusX, radiusY, radiusZ` | origin is the top: `0 … -radiusY`, growing **down** |

`BlockConeUtil.forEachBlockInverted` / `BlockPyramidUtil.forEachBlockInverted` keep the same upward
`0 … height - 1` band and only flip which end tapers.

```java
// Enumerate every block position inside a radius-5 sphere centered at (cx, cy, cz).
// The context object (here a counter) is threaded through to avoid lambda capture.
int[] count = {0};
BlockSphereUtil.forEachBlock(cx, cy, cz, 5, count, (x, y, z, ctr) -> {
    ctr[0]++;
    // place / inspect the block at (x, y, z) via your World or chunk accessor here
    return true;   // return false to stop iterating early
});
```

> **Gotcha:** `BlockCubeUtil`'s `hollow` flag reads backwards from its name. With `thickness >= 1`
> and `hollow == false` you get the **shell**; `hollow == true` emits the **interior** the shell
> encloses. Pass `thickness = 0` when you just want every block in the volume.

### BlockUtil — coordinate packing

`BlockUtil` packs a block position into a single `long` key (handy for maps/sets of block positions):

```java
long key = BlockUtil.pack(x, y, z);        // also packUnchecked(x, y, z)
int bx = BlockUtil.unpackX(key);
int by = BlockUtil.unpackY(key);
int bz = BlockUtil.unpackZ(key);
Vector3i pos = new Vector3i(bx, by, bz);   // pack(Vector3i)/unpack(long) were removed by 0.6.3 — only the per-axis forms remain
```

---

## Line & Spiral Iteration

**Package:** `com.hypixel.hytale.math.iterator`

Two iterators for walking positions in a pattern — a straight block line in 3D, and an outward chunk spiral. Like the [block shape utilities](#block-shape-iteration), they generate coordinates only (no world dependency); pair them with [world block access](blocks.md#world-block-access) or your chunk-loading calls to act on the results.

### LineIterator

A 3D Bresenham line walk: visits every integer block position from `(x1, y1, z1)` to `(x2, y2, z2)`, both endpoints inclusive. Implements `java.util.Iterator<Vector3i>`; each `next()` returns a **freshly allocated** `Vector3i`, so it's safe to keep the positions you're handed.

```java
LineIterator line = new LineIterator(x1, y1, z1, x2, y2, z2);
while (line.hasNext()) {
    Vector3i pos = line.next();
    // place / inspect the block at pos
}
```

Reach for it when you need the blocks *between* two points — beam effects, drawing block lines, coarse line-of-sight sampling over block positions. (For precise ray-vs-box math use [RaycastAABB](#raycastaabb) instead.)

### SpiralIterator

Walks **chunk coordinates** in an outward square spiral around a center chunk — the "process the nearest chunks first" pattern (view-distance scans, pregeneration, searching outward for a target chunk).

`next()` returns the chunk position packed into a `long` (the same packed chunk index `ChunkUtil` uses — unpack with `ChunkUtil.xOfChunkIndex(packed)` / `ChunkUtil.zOfChunkIndex(packed)`).

```java
SpiralIterator spiral = new SpiralIterator(centerChunkX, centerChunkZ, 8);  // out to ring 8 → (2*8+1)² chunks
while (spiral.hasNext()) {
    long packed = spiral.next();
    int cx = ChunkUtil.xOfChunkIndex(packed);
    int cz = ChunkUtil.zOfChunkIndex(packed);
    // visit chunk (cx, cz) — nearest rings first
}
```

- The 4-arg form `new SpiralIterator(chunkX, chunkZ, radiusFrom, radiusTo)` skips everything within ring `radiusFrom` (resume an outward scan without re-walking the middle).
- The no-arg constructor plus `init(chunkX, chunkZ, radiusTo)` / `reset()` let one instance be reused; calling `next()` before `init` throws `IllegalStateException` (`isSetup()` to check).
- Progress: `getIndex()` / `getMaxIndex()` (spiral cell counter) and `getCurrentRadius()` / `getCompletedRadius()` (ring counter). Radii are validated — `radiusTo` must be > 0, > `radiusFrom`, and ≤ `SpiralIterator.MAX_RADIUS`.

---

## VectorBoxUtil & VectorSphereUtil

**Package:** `com.hypixel.hytale.math.vector`

Volume-membership helpers over **collections of positions**: each `forEachVector` overload walks an `Iterable` (or fastutil `Int2ObjectMap`) and invokes your callback only for elements whose `Vector3d` position lies inside a box or sphere around an origin point. This is the cheap "who's near this point" sweep — a linear filter over a list you already have, no spatial index required.

Both classes share one API shape:

```java
// Iterable<Vector3d> filtered directly
VectorSphereUtil.forEachVector(positions, cx, cy, cz, radius, pos -> {
    // pos is within `radius` of (cx, cy, cz)
});

// Arbitrary objects + a position extractor (Function<T, Vector3d>)
VectorBoxUtil.forEachVector(trackedEntities, positionFn, cx, cy, cz, halfExtent, entity -> {
    // entity's position is inside the box
});

// One-off membership checks
boolean inSphere = VectorSphereUtil.isInside(cx, cy, cz, radius, pos);
boolean inBox    = VectorBoxUtil.isInside(cx, cy, cz, halfExtent, pos);
```

- **Box** (`VectorBoxUtil`): the size arguments are **apothems** (half-extents) around the origin — one uniform value, three per-axis values, or six signed min/max offsets for an asymmetric box.
- **Sphere** (`VectorSphereUtil`): one radius, or three per-axis radii (an axis-aligned ellipsoid).
- Further overloads take a `BiConsumer` / `TriConsumer` (or `IntObjectConsumer` / `IntBiObjectConsumer` / `IntTriObjectConsumer` for the `Int2ObjectMap` forms) that thread one or two caller-supplied context objects into the callback — the same no-lambda-capture pattern as [block shape iteration](#block-shape-iteration).

---

## MathUtil

**Package:** `com.hypixel.hytale.math.util`

Static utility methods for common scalar math operations.

### Constants

```java
MathUtil.EPSILON_DOUBLE       // small double for comparisons
MathUtil.EPSILON_FLOAT        // small float for comparisons
MathUtil.ZERO_LENGTH_EPSILON  // 1.0E-8 — "is this vector effectively zero-length" threshold (0.6.3+)
```

### Rounding

```java
int floor = MathUtil.floor(double);
int ceil = MathUtil.ceil(double);
int fast = MathUtil.fastRound(float);
long fast = MathUtil.fastRound(double);
int fastFloor = MathUtil.fastFloor(float);
int fastCeil = MathUtil.fastCeil(float);
double rounded = MathUtil.round(value, decimalPlaces);
```

### Clamping

```java
double clamped = MathUtil.clamp(value, min, max);
float clamped = MathUtil.clamp(value, min, max);
int clamped = MathUtil.clamp(value, min, max);
long clamped = MathUtil.clamp(value, min, max);
long product = MathUtil.saturatedMultiply(a, b);   // 0.6.3+: a*b clamped to Long.MIN/MAX instead of overflowing
```

### Random

```java
int rand = MathUtil.randomInt(min, max);
double rand = MathUtil.randomDouble(min, max);
float rand = MathUtil.randomFloat(min, max);
```

### Interpolation

```java
float lerped = MathUtil.lerp(a, b, t);
double lerped = MathUtil.lerp(a, b, t);
float lerped = MathUtil.lerpUnclamped(a, b, t);
float angleLerp = MathUtil.lerpAngle(fromAngle, toAngle, t);
float seeded = MathUtil.seededLerp(a, b, seed);   // 0.6.3+: lerp at a deterministic t derived from a long seed
```

### Angle Utilities

```java
float wrapped = MathUtil.wrapAngle(angle);  // wrap to valid range
float dist = MathUtil.shortAngleDistance(from, to);
double cmp = MathUtil.compareAngle(a, b);
```

### Near-Zero Checks

```java
double clipped = MathUtil.clipToZero(value);
double clipped = MathUtil.clipToZero(value, epsilon);
boolean near = MathUtil.closeToZero(value);
boolean near = MathUtil.closeToZero(value, epsilon);
boolean within = MathUtil.within(a, b, tolerance);
```

### Length Calculations

```java
double len = MathUtil.length(x, y);
double len = MathUtil.length(x, y, z);
double lenSq = MathUtil.lengthSquared(x, y);
double lenSq = MathUtil.lengthSquared(x, y, z);
```

### Min/Max

```java
double min = MathUtil.minValue(a, b, c);
double max = MathUtil.maxValue(a, b, c);
double max = MathUtil.maxValue(a, b, c, d);
int abs = MathUtil.abs(int);
```

### Vector Rotation

```java
Vector3i rotated = MathUtil.rotateVectorYAxis(vec3i, steps, clockwise);
Vector3d rotated = MathUtil.rotateVectorYAxis(vec3d, steps, clockwise);
```

### Hit-Normal Helpers

```java
Rotation3f rot = MathUtil.getRotationForHitNormal(normalVec3d);
String name = MathUtil.getNameForHitNormal(normalVec3d);
```

### Distance to Line

```java
double distSq = MathUtil.distanceToLineSq(px, py, x1, y1, x2, y2);
double distSq = MathUtil.distanceToInfLineSq(px, py, x1, y1, x2, y2);
int side = MathUtil.sideOfLine(px, py, x1, y1, x2, y2);  // which side of line
```

### Bit Packing

```java
int packed = MathUtil.packInt(left, right);
int left = MathUtil.unpackLeft(packed);
int right = MathUtil.unpackRight(packed);

long packed = MathUtil.packLong(left, right);
```

---

## FastRandom & RandomExtra

**Packages:** `com.hypixel.hytale.math.util` (`FastRandom`) · `com.hypixel.hytale.math.random` (`RandomExtra`)

### FastRandom

A drop-in `java.util.Random` subclass running the same 48-bit LCG **without the thread-safety machinery** — the same numbers for the same seed as `java.util.Random`, with less overhead. Use it wherever an API wants a `java.util.Random` and you need a fast, **deterministic, seedable** stream on a single thread (reproducible generation, replayable rolls).

```java
Random random = new FastRandom(seed);   // deterministic per seed
Random random = new FastRandom();       // randomly seeded
random.setSeed(seed);                   // restart the stream
int roll = random.nextInt(6);           // inherited java.util.Random methods work as usual
```

> [!WARNING]
> Two exceptions to "drop-in": it is **not thread-safe** (unsynchronized state — keep one instance per thread), and `FastRandom.nextGaussian()` **throws `UnsupportedOperationException`**.

### RandomExtra

Static convenience sampling on top of `ThreadLocalRandom` — thread-safe but **not seedable** (use `FastRandom` when you need determinism). Reach for it to cut the usual random-value boilerplate:

```java
double d = RandomExtra.randomRange(0.5, 2.0);   // also float / long overloads
int i    = RandomExtra.randomRange(1, 6);       // int range: BOTH ends inclusive
int j    = RandomExtra.randomRange(bound);      // 0 (inclusive) .. bound (exclusive)
double e = RandomExtra.randomRange(minMax);     // double[] / float[] / int[] as {min, max}
boolean flip = RandomExtra.randomBoolean();
Duration wait = RandomExtra.randomDuration(minDuration, maxDuration);
double c = RandomExtra.randomBinomial();        // difference of two rolls: (-1, 1), biased toward 0

// Collections
T pick = RandomExtra.randomElement(list);                          // uniform pick from a List
T drop = RandomExtra.randomWeightedElement(items, weightFn);       // ToDoubleFunction<T> weights
T drop2 = RandomExtra.randomIntWeightedElement(items, intWeightFn);
int idx = RandomExtra.pickWeightedIndex(weights);                  // double[] of weights
RandomExtra.reservoirSample(source, filter, sampleCount, results); // uniform sample of a filtered List
int n = RandomExtra.reservoirSample(population, sampleCount, outIndices); // 0.6.3+: int indices 0..population-1 into outIndices[]

// Vectors
RandomExtra.jitter(vec, maxRange);   // adds a random 0..maxRange to each component, in place
```

Weighted variants also accept a `Predicate` filter (`randomWeightedElementFiltered`) or a precomputed total weight so the summing pass can be skipped; they return `null` for an empty/zero-weight collection.

> [!NOTE]
> `jitter` offsets each component by `[0, maxRange)` — the jitter is **not centered** on the input position (it only ever shifts toward +X/+Y/+Z), and it mutates the vector in place.

---

## RaycastAABB

**Package:** `com.hypixel.hytale.math.raycast`

Ray-box intersection testing.

```java
// Returns distance to intersection, or negative if no hit
double dist = RaycastAABB.intersect(
    rayOriginX, rayOriginY, rayOriginZ,
    rayDirX, rayDirY, rayDirZ,
    boxMinX, boxMinY, boxMinZ,
    boxMaxX, boxMaxY, boxMaxZ
);

// With callback for hit information
RaycastAABB.intersect(
    rayOriginX, rayOriginY, rayOriginZ,
    rayDirX, rayDirY, rayDirZ,
    boxMinX, boxMinY, boxMinZ,
    boxMaxX, boxMaxY, boxMaxZ,
    (hitDist, normalX, normalY, normalZ) -> {
        // Handle hit
    }
);
```

---

## Range

**Package:** `com.hypixel.hytale.math`

Simple min/max range container.

```java
Range range = new Range(min, max);
float min = range.getMin();
float max = range.getMax();
```

Also available: `FloatRange`, `IntRange` in `com.hypixel.hytale.math.range`

---

## Minor Utilities & Codecs

Smaller helpers you'll mostly meet in passing:

| Class | Package | What it is |
|-------|---------|------------|
| `HashUtil` | `math.util` | Stateless coordinate hashing: `hash(...)` / `rehash(...)` mix 1–4 `long`s into a hash; `random(...)` maps them to a deterministic `double` in `[0, 1)` and `randomInt(l1, l2, l3, bound)` to an `int`. Same inputs → same value, so it gives position/seed-keyed "randomness" with no RNG object at all. `hashUuid(uuid)` folds a `UUID` to a `long`. |
| `TrigMathUtil` | `math.util` | Lookup-table float trig: `sin` / `cos` (with `float` and `double` overloads), `atan2`, `atan`, `asin`, plus float constants `PI`, `PI_HALF`, `PI_QUARTER`, `PI2`, `PI4`, `radToDeg`, `degToRad`. Faster but lower-precision than `java.lang.Math`. |
| `IntRangeArrayCodec` | `math.codec` | `Codec<IntRange>` that (de)serializes an `IntRange` as a two-element `[min, max]` array (both inclusive) — for codec schemas that want the compact array form. |
| `Vector3iArrayCodec` | `math.codec` | `Codec<Vector3i>` for the `[x, y, z]` array form. **Deprecated** — prefer `Vector3iUtil.CODEC` in new code. |
| `PositionUtil` | `server.core.util` | Bridges math types ↔ network packet types (`com.hypixel.hytale.protocol`): `toPositionPacket` / `toVector3d`, `toDirectionPacket` / `toRotation`, `toTransformPacket` / `toTransform`, plus `assign(...)` / `equals(...)` overloads for updating and comparing packet structs without reallocating. |

---

## Gotchas & Errors

Backtick-quoted error strings below are literal messages in the 0.6.3 `HytaleServer.jar` (the vector-format ones come from the NPC spawn command's coordinate parser, the plane one from the world generator's plane density asset).

- **`Invalid Vector3f format: must be three comma-separated floats`** / **`Invalid Vector3d format: must be three comma-separated doubles`** → a string-form vector did not parse as exactly three comma-separated numbers. Fix: format as `x,y,z` (e.g. `1.0,2.0,3.0`).
- **`Plane normal can't be a zero vector.`** → a plane was constructed from a zero-length normal. Fix: pass a non-zero (ideally unit-length) normal.
- **Mutation gotcha (JOML):** `a.add(b)`, `a.normalize()`, `a.mul(f)` and friends modify `a` **in place** and return it. If `a` is a shared vector (a constant from a `*Util` class, or a position you didn't copy), you'll corrupt it. Fix: copy first (`new Vector3d(a)`) or use the dest overload (`a.add(b, new Vector3d())`). The `*Util` constants are typed `Vector3dc`/`Vector3ic` (read-only) precisely to make accidental mutation a compile error.

---

> **Authoritative signatures:** see the [official server API reference](https://release.server.docs.hytale.com) (auto-generated, always current). This page adds the descriptions, context, and examples it lacks.
