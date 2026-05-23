# Math / Vector API

## Overview

Hytale provides a comprehensive math library including vectors, matrices, quaternions, shapes, and utilities.

### Core Types

| Class | Precision | Primary Use |
|-------|-----------|-------------|
| `Vector3d` | double | Positions, velocities, directions |
| `Vector3f` | float | Rotations (pitch/yaw/roll) |
| `Vector3i` | int | Block positions |
| `Vector2d` | double | 2D positions |
| `Vector2i` | int | 2D grid positions |
| `Transform` | mixed | Position (Vector3d) + Rotation (Vector3f) |

### Advanced Types

| Class | Description |
|-------|-------------|
| `Matrix4d` | 4x4 transformation matrix (translate, rotate, scale, project) |
| `Box` | Axis-aligned bounding box (AABB) |
| `Axis` | Enum for X, Y, Z axes |
| `MathUtil` | Static math utilities |

## Vector3d

**Package:** `com.hypixel.hytale.math.vector`

Double-precision 3D vector. Used for entity positions, velocities, and directions.

### Creating Vectors

```java
// Direct construction (if available)
Vector3d pos = new Vector3d(10.0, 64.0, -5.0);

// From Transform
Transform transform = playerRef.getTransform();
Vector3d position = transform.getPosition();

// From TransformComponent
TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());
Vector3d entityPos = tc.getPosition();

// Clone existing
Vector3d copy = original.clone();
```

### Static Methods

```java
// Combine two vectors
Vector3d sum = Vector3d.add(a, b);
Vector3d sum = Vector3d.add(a, b, result);  // Store in result

// Direction from one point to another
Vector3d dir = Vector3d.directionTo(from, to);
Vector3d dir = Vector3d.directionTo(blockPos, targetPos);  // Vector3i to Vector3d

// Linear interpolation
Vector3d mid = Vector3d.lerp(start, end, 0.5);        // Clamped t to [0,1]
Vector3d pos = Vector3d.lerpUnclamped(start, end, t); // Unclamped

// Component-wise min/max
Vector3d lower = Vector3d.min(a, b);
Vector3d upper = Vector3d.max(a, b);

// Format for display
String str = Vector3d.formatShortString(vec);
```

### Instance Methods - Getters/Setters

```java
double x = vec.getX();
double y = vec.getY();
double z = vec.getZ();

vec.setX(10.0);
vec.setY(64.0);
vec.setZ(-5.0);
```

### Instance Methods - Assignment

```java
// Assign modifies the vector in-place and returns this
vec.assign(x, y, z);
vec.assign(x, y);        // Sets x, y; z unchanged
vec.assign(value);       // Sets all components to value
vec.assign(other);       // Copy from Vector3d
vec.assign(doubleArray); // From double[]
vec.assign(floatArray);  // From float[]
```

### Instance Methods - Arithmetic

All arithmetic methods modify in-place and return `this` for chaining.

```java
// Addition
vec.add(x, y, z);
vec.add(value);        // Add scalar to all components
vec.add(other);        // Add Vector3d
vec.add(blockPos);     // Add Vector3i
vec.addScaled(dir, scale);  // vec += dir * scale

// Subtraction
vec.subtract(x, y, z);
vec.subtract(value);
vec.subtract(other);
vec.subtract(blockPos);

// Scaling
vec.scale(factor);     // Multiply all components
vec.scale(other);      // Component-wise multiply
vec.negate();          // Flip sign
```

### Instance Methods - Vector Math

```java
// Length
double len = vec.length();
double lenSq = vec.squaredLength();  // Faster, avoids sqrt

// Normalize
vec.normalize();       // Make unit length
vec.setLength(5.0);    // Set to specific length
vec.clampLength(max);  // Cap length at max

// Dot product
double dot = vec.dot(other);

// Cross product
vec.cross(other);               // Modify in-place
vec.cross(a, b);                // Set this = a × b

// Distance
double dist = vec.distanceTo(other);
double dist = vec.distanceTo(x, y, z);
double dist = vec.distanceTo(blockPos);
double distSq = vec.distanceSquaredTo(other);  // Faster
```

### Instance Methods - Rotation

```java
// Rotate around axes (angle in radians)
vec.rotateX(angle);
vec.rotateY(angle);
vec.rotateZ(angle);
```

### Instance Methods - Rounding

```java
vec.floor();  // Round down each component
vec.ceil();   // Round up each component
```

### Instance Methods - Utility

```java
// Near-zero checks
boolean nearZero = vec.closeToZero(epsilon);
vec.clipToZero(epsilon);  // Set components < epsilon to 0

// Validity checks
boolean valid = vec.isFinite();
boolean inside = vec.isInside(maxX, maxY, maxZ);

// Conversion
Vector3f floatVec = vec.toVector3f();
Vector3i intVec = vec.toVector3i();  // Truncates

// Comparison
boolean same = vec.equals(other);
```

> **See also:** [Transform Component](components.md#transformcomponent)

---

## Vector3f

**Package:** `com.hypixel.hytale.math.vector`

Float-precision 3D vector. Primarily used for rotations (pitch, yaw, roll).

### Rotation Conventions

Vector3f stores rotation as (pitch, yaw, roll):
- **X (Pitch)**: Looking up/down (-90 to 90)
- **Y (Yaw)**: Compass direction (0-360)
- **Z (Roll)**: Tilt left/right

```java
// Rotation aliases
float pitch = rotation.getPitch();  // Same as getX()
float yaw = rotation.getYaw();      // Same as getY()
float roll = rotation.getRoll();    // Same as getZ()

rotation.setPitch(45.0f);
rotation.setYaw(180.0f);
rotation.setRoll(0.0f);

rotation.addPitch(5.0f);
rotation.addYaw(-10.0f);
rotation.addRoll(2.0f);
```

### Static Methods

```java
// Arithmetic
Vector3f sum = Vector3f.add(a, b);
Vector3f sum = Vector3f.add(a, b, result);
Vector3f dir = Vector3f.directionTo(from, to);

// Interpolation
Vector3f mid = Vector3f.lerp(start, end, 0.5f);
Vector3f pos = Vector3f.lerpUnclamped(start, end, t);

// Angle interpolation (handles wrap-around)
Vector3f rot = Vector3f.lerpAngle(startRot, endRot, 0.5f);
Vector3f rot = Vector3f.lerpAngle(startRot, endRot, 0.5f, result);

// Look direction
Vector3f rotation = Vector3f.lookAt(targetPosition);
Vector3f rotation = Vector3f.lookAt(targetPosition, result);

// Min/max
Vector3f lower = Vector3f.min(a, b);
Vector3f upper = Vector3f.max(a, b);
```

### Instance Methods

Shares most methods with Vector3d (using float instead of double):
- `getX/Y/Z()`, `setX/Y/Z()`
- `assign()`, `add()`, `subtract()`, `scale()`
- `length()`, `normalize()`, `dot()`, `cross()`
- `distanceTo()`, `rotateX/Y/Z()`
- `floor()`, `ceil()`, `clone()`

### Axis Rotation

```java
// Flip rotation on an axis
rotation.flipRotationOnAxis(Axis.Y);

// Add rotation increments
rotation.addRotationOnAxis(Axis.Y, 90);  // int degrees
```

### Conversion

```java
Vector3d doubleVec = floatVec.toVector3d();
```

---

## Vector3i

**Package:** `com.hypixel.hytale.math.vector`

Integer 3D vector. Used for block positions.

### Static Methods

```java
Vector3i sum = Vector3i.add(a, b);
Vector3i sum = Vector3i.add(a, b, result);
Vector3i dir = Vector3i.directionTo(from, to);
Vector3i lower = Vector3i.min(a, b);
Vector3i upper = Vector3i.max(a, b);
```

### Instance Methods

Similar to Vector3d but with int types:

```java
int x = vec.getX();
int y = vec.getY();
int z = vec.getZ();

vec.setX(10);
vec.setY(64);
vec.setZ(-5);

vec.assign(x, y, z);
vec.assign(other);

vec.add(x, y, z);
vec.add(other);
vec.addScaled(dir, scale);

vec.subtract(x, y, z);
vec.subtract(other);

vec.scale(factor);     // int
vec.scale(factor);     // double (truncates)
vec.scale(other);      // Component-wise
vec.negate();

double len = vec.length();
int lenSq = vec.squaredLength();

vec.normalize();       // Truncates to int
vec.setLength(len);
vec.clampLength(max);

int dot = vec.dot(other);
vec.cross(other);

double dist = vec.distanceTo(other);
int distSq = vec.distanceSquaredTo(other);
```

### Conversion

```java
Vector3d doubleVec = intVec.toVector3d();
Vector3f floatVec = intVec.toVector3f();
Vector3l longVec = intVec.toVector3l();
```

---

## Vector3l

**Package:** `com.hypixel.hytale.math.vector`

Long-precision 3D vector. Similar API to Vector3i but with `long` components. Useful for large coordinate values.

### Constants

```java
Vector3l.ZERO
Vector3l.UP, Vector3l.DOWN        // Y axis (aliases: POS_Y, NEG_Y)
Vector3l.FORWARD, Vector3l.BACKWARD  // Z axis (aliases: NEG_Z, POS_Z)
Vector3l.RIGHT, Vector3l.LEFT     // X axis (aliases: POS_X, NEG_X)
Vector3l.NORTH, Vector3l.SOUTH    // Z axis aliases
Vector3l.EAST, Vector3l.WEST      // X axis aliases
Vector3l.ALL_ONES
Vector3l.MIN, Vector3l.MAX        // Long min/max values
```

### Direction Arrays

```java
Vector3l[] BLOCK_SIDES       // 6 face directions
Vector3l[] BLOCK_EDGES       // 12 edge directions
Vector3l[] BLOCK_CORNERS     // 8 corner directions
Vector3l[][] BLOCK_PARTS     // All block parts
Vector3l[] CARDINAL_DIRECTIONS  // 4 horizontal directions
```

### Instance Methods

Same pattern as Vector3i but with long types:

```java
long x = vec.getX();
long y = vec.getY();
long z = vec.getZ();

vec.setX(10L);
vec.setY(64L);
vec.setZ(-5L);

vec.assign(x, y, z);
vec.assign(other);

vec.add(x, y, z);
vec.add(other);
vec.addScaled(dir, scale);

vec.subtract(x, y, z);
vec.subtract(other);

vec.scale(factor);     // long
vec.scale(factor);     // double (truncates)
vec.scale(other);      // Component-wise
vec.negate();

double len = vec.length();
long lenSq = vec.squaredLength();

vec.normalize();
vec.setLength(len);
vec.clampLength(max);

long dot = vec.dot(other);
vec.cross(other);

double dist = vec.distanceTo(other);
long distSq = vec.distanceSquaredTo(other);
```

### Conversion

```java
Vector3i intVec = longVec.toVector3i();
Vector3d doubleVec = longVec.toVector3d();
```

### Static Methods

```java
Vector3l sum = Vector3l.add(a, b);
Vector3l sum = Vector3l.add(a, b, result);
Vector3l dir = Vector3l.directionTo(from, to);
Vector3l lower = Vector3l.min(a, b);
Vector3l upper = Vector3l.max(a, b);
```

---

## Transform

**Package:** `com.hypixel.hytale.math.vector`

Combines position (Vector3d) and rotation (Vector3f) into a single value type.

### Getting Transform

```java
// From PlayerRef
Transform transform = playerRef.getTransform();

// From TransformComponent
TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());
Transform transform = tc.getTransform();
```

### Accessing Components

```java
Vector3d position = transform.getPosition();
Vector3f rotation = transform.getRotation();

transform.setPosition(newPos);
transform.setRotation(newRot);
```

### Direction Calculations

```java
// Get facing direction as unit vector
Vector3d direction = transform.getDirection();

// Get facing direction from angles (static)
Vector3d dir = Transform.getDirection(pitch, yaw);

// Get axis-aligned direction (nearest cardinal)
Axis axis = transform.getAxis();
Vector3i axisDir = transform.getAxisDirection();
Vector3i axisDir = transform.getAxisDirection(pitch, yaw);
```

### Utility

```java
transform.assign(other);
Transform copy = transform.clone();
```

### Static Helper

```java
// Apply masked relative transform (advanced use)
Transform.applyMaskedRelativeTransform(transform, mask, posOffset, rotOffset, result);
```

---

## TransformComponent

**Package:** `com.hypixel.hytale.server.core.modules.entity.component`

ECS component that stores an entity's position and rotation. Unlike `Transform` (a value type), this is a live component attached to an entity.

### Getting the Component

```java
TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());

// Or in chunk iteration
TransformComponent tc = chunk.getComponent(index, TransformComponent.getComponentType());
```

### Reading Position/Rotation

```java
Vector3d pos = tc.getPosition();
Vector3f rot = tc.getRotation();
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

### Chunk Information

```java
WorldChunk chunk = tc.getChunk();
Ref chunkRef = tc.getChunkRef();
tc.setChunkLocation(chunkRef, chunk);
tc.markChunkDirty(accessor);
```

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
TransformComponent myTc = store.getComponent(myRef, TransformComponent.getComponentType());
TransformComponent targetTc = store.getComponent(targetRef, TransformComponent.getComponentType());

Vector3d myPos = myTc.getPosition();
Vector3d targetPos = targetTc.getPosition();
Vector3d direction = Vector3d.directionTo(myPos, targetPos);
```

### Apply Knockback

```java
Vector3d knockback = direction.clone().normalize().scale(knockbackForce);
knockback.setY(upwardForce);  // Add vertical component

Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
velocity.addInstruction(knockback, new VelocityConfig(), ChangeVelocityType.Add);
```

### Check Distance

```java
Vector3d posA = transformA.getPosition();
Vector3d posB = transformB.getPosition();

// Use squared distance for comparisons (faster)
double distSq = posA.distanceSquaredTo(posB);
if (distSq < radius * radius) {
    // Within radius
}
```

### Get Block Position from Entity

```java
Vector3d entityPos = tc.getPosition();
Vector3i blockPos = entityPos.toVector3i();  // Truncates to block coordinates
```

### Look At Target

```java
Transform myTransform = playerRef.getTransform();
Vector3d targetPos = targetEntity.getPosition();

Vector3f lookRotation = Vector3f.lookAt(
    targetPos.clone().subtract(myTransform.getPosition())
);
```

---

## Vector2d

**Package:** `com.hypixel.hytale.math.vector`

Double-precision 2D vector.

### Constants

```java
Vector2d.ZERO      // (0, 0)
Vector2d.UP        // (0, 1)  - same as POS_Y
Vector2d.DOWN      // (0, -1) - same as NEG_Y
Vector2d.RIGHT     // (1, 0)  - same as POS_X
Vector2d.LEFT      // (-1, 0) - same as NEG_X
Vector2d.ALL_ONES  // (1, 1)
Vector2d.DIRECTIONS // Array of cardinal directions
```

### Methods

Same pattern as Vector3d but in 2D:
- `getX()`, `getY()`, `setX()`, `setY()`
- `assign()`, `add()`, `subtract()`, `scale()`, `negate()`
- `dot()`, `length()`, `squaredLength()`, `normalize()`
- `distanceTo()`, `distanceSquaredTo()`
- `lerp()`, `lerpUnclamped()`, `min()`, `max()`
- `floor()`, `ceil()`, `clipToZero()`, `closeToZero()`

---

## Vector2i

**Package:** `com.hypixel.hytale.math.vector`

Integer 2D vector. Same API as Vector2d but with int types.

---

## Matrix4d

**Package:** `com.hypixel.hytale.math.matrix`

Full-featured 4x4 transformation matrix. Supports translation, rotation, scaling, and projection.

### Construction

```java
Matrix4d matrix = new Matrix4d();           // Identity
Matrix4d copy = new Matrix4d(other);        // Copy
Matrix4d fromData = new Matrix4d(double[]); // From 16-element array
```

### Element Access

```java
// By flat index (0-15)
double val = matrix.get(index);
matrix.set(index, value);
matrix.add(index, value);

// By row/column (0-3 each)
double val = matrix.get(row, col);
matrix.set(row, col, value);
matrix.add(row, col, value);

// Index constants
Matrix4d.M00, M01, M02, M03  // Row 0
Matrix4d.M10, M11, M12, M13  // Row 1
Matrix4d.M20, M21, M22, M23  // Row 2
Matrix4d.M30, M31, M32, M33  // Row 3
```

### Transformations

```java
matrix.identity();                    // Reset to identity
matrix.translate(vec3d);              // Translate by vector
matrix.translate(x, y, z);            // Translate by components
matrix.scale(x, y, z);                // Scale

// Rotation
matrix.setRotateEuler(pitch, yaw, roll);
matrix.rotateEuler(pitch, yaw, roll, result);
matrix.setRotateAxis(angle, axisX, axisY, axisZ);
matrix.rotateAxis(angle, axisX, axisY, axisZ, result);
```

### Matrix Operations

```java
matrix.assign(other);                 // Copy from other matrix
matrix.multiply(other);               // this = this * other
boolean success = matrix.invert();    // Invert in-place
```

### Vector Multiplication

```java
// Transform a position (applies translation)
Vector3d transformed = matrix.multiplyPosition(vec3d);
Vector3d transformed = matrix.multiplyPosition(vec3d, result);

// Transform a direction (ignores translation)
Vector3d transformed = matrix.multiplyDirection(vec3d);

// Full 4D multiply
Vector4d transformed = matrix.multiply(vec4d);
Vector4d transformed = matrix.multiply(vec4d, result);
```

### Projection Matrices

```java
// Orthographic projection
matrix.projectionOrtho(left, right, bottom, top, near, far);

// Perspective projection
matrix.projectionFrustum(left, right, bottom, top, near, far);
matrix.projectionCone(fov, aspect, near, far);
```

### View Matrices

```java
// Look at target position
matrix.viewTarget(eyeX, eyeY, eyeZ, targetX, targetY, targetZ, upX, upY, upZ);

// Look in direction
matrix.viewDirection(eyeX, eyeY, eyeZ, dirX, dirY, dirZ, upX, upY, upZ);
```

### Data Export

```java
double[] data = matrix.getData();      // 16-element double array
float[] floatData = matrix.asFloatData(); // 16-element float array
```

---

## Vector4d

**Package:** `com.hypixel.hytale.math.vector`

4D double vector for homogeneous coordinates. Used with `Matrix4d` for 4D transformations and perspective projection.

In homogeneous coordinates:
- **w = 1**: Represents a position (affected by translation)
- **w = 0**: Represents a direction (not affected by translation)

### Fields

```java
double x, y, z, w
```

### Component Constants

```java
Vector4d.COMPONENT_X  // 0
Vector4d.COMPONENT_Y  // 1
Vector4d.COMPONENT_Z  // 2
Vector4d.COMPONENT_W  // 3
```

### Constructors

```java
Vector4d vec = new Vector4d();                    // All zeros
Vector4d vec = new Vector4d(x, y, z, w);
```

### Static Factory Methods

```java
// Create position (w = 1)
Vector4d pos = Vector4d.newPosition(x, y, z);
Vector4d pos = Vector4d.newPosition(vec3d);

// Create direction (w = 0)
Vector4d dir = Vector4d.newDirection(x, y, z);
```

### Methods

```java
// Set w component
Vector4d setPosition()   // Sets w = 1
Vector4d setDirection()  // Sets w = 0

// Assignment
Vector4d assign(other)
Vector4d assign(x, y, z, w)

// Interpolation
Vector4d lerp(other, t, result)

// Component access
double val = vec.get(Vector4d.COMPONENT_X);

// Perspective projection
void perspectiveTransform()  // Divide xyz by w
boolean isInsideFrustum()    // Check if inside view frustum
```

### Usage with Matrix4d

```java
// Transform a 3D position through a 4x4 matrix
Matrix4d matrix = ...;
Vector4d pos = Vector4d.newPosition(x, y, z);
Vector4d result = matrix.multiply(pos);

// For perspective projection, divide by w
result.perspectiveTransform();
// Now result.x/y/z are in normalized device coordinates
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
Vector3i dir = axis.getDirection();  // Unit vector along axis

// Rotate vectors around this axis
axis.rotate(Vector3i vec, int steps);  // 90° increments
axis.rotate(Vector3d vec, int steps);
axis.rotate(Vector3i vec);             // Single 90° rotation
axis.rotate(Vector3d vec);

// Flip vectors on this axis
axis.flip(Vector3i vec);
axis.flip(Vector3d vec);

// Flip rotation component
axis.flipRotation(Vector3f rotation);
```

---

## Box (AABB)

**Package:** `com.hypixel.hytale.math.shape`

Axis-Aligned Bounding Box for collision detection and spatial queries.

### Construction

```java
Box box = new Box();                              // Empty
Box box = new Box(min, max);                      // From Vector3d corners
Box box = new Box(minX, minY, minZ, maxX, maxY, maxZ);
Box box = Box.cube(center, size);                 // Cube at position
Box box = Box.centeredCube(center, size);         // Centered cube
Box box = Box.horizontallyCentered(width, height, depth);

Box.UNIT  // Unit box constant
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
box.normalize();  // Ensure min < max

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
box.union(other);           // Expand to include other
box.minkowskiSum(other);    // Minkowski sum
box.sweep(direction);       // Expand along direction
```

### Block Iteration

```java
// Iterate all blocks within the box
box.forEachBlock(offsetX, offsetY, offsetZ, scale, (x, y, z) -> {
    // Process block at x, y, z
    return true;  // Continue iteration
});
```

> **See also:** [Collision API](collision.md#box-collision-detection)

---

## MathUtil

**Package:** `com.hypixel.hytale.math.util`

Static utility methods for common math operations.

### Constants

```java
MathUtil.EPSILON_DOUBLE  // Small double for comparisons
MathUtil.EPSILON_FLOAT   // Small float for comparisons
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
```

### Angle Utilities

```java
float wrapped = MathUtil.wrapAngle(angle);  // Wrap to valid range
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

### Distance to Line

```java
double distSq = MathUtil.distanceToLineSq(px, py, x1, y1, x2, y2);
double distSq = MathUtil.distanceToInfLineSq(px, py, x1, y1, x2, y2);
int side = MathUtil.sideOfLine(px, py, x1, y1, x2, y2);  // Which side of line
```

### Bit Packing

```java
int packed = MathUtil.packInt(left, right);
int left = MathUtil.unpackLeft(packed);
int right = MathUtil.unpackRight(packed);

long packed = MathUtil.packLong(left, right);
```

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
