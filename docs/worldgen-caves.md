# Caves

Hytale caves are **not** a separate "cave type / cave node / corridor" system. A cave is simply a
**density field** that goes negative inside the volume you want hollow, combined into a biome's
terrain density with `Min`. Wherever the cave field is lower than the surface field, the surface
field is overridden and that cell becomes empty — i.e. carved out.

In other words: caves use exactly the same density node graph vocabulary as
[terrain](worldgen-terrain.md) (`SimplexNoise2D`, `CurveMapper`, `Sum`, `Min`, `Max`, `Mix`,
`Normalizer`, `Pow`, `Abs`, `Inverter`, `BaseHeight`, `Cache`, `Imported`, `Constant`).

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Where caves live](#where-caves-live) | Canonical asset paths |
| [How carving works](#how-carving-works) | `Min` against terrain |
| [Anatomy of a cave field](#anatomy-of-a-cave-field) | Plains1_Caves_Terrain |
| [Building blocks](#building-blocks) | Floors, ceilings, walls, snakes |
| [Volcanic example](#volcanic-example) | A different carving style |
| [What does NOT exist](#what-does-not-exist) | Removed fictional schema |

---

## Where caves live

| Content | Path |
|---------|------|
| Cave density fields | `Server/HytaleGenerator/Density/*_Caves_*.json` |

Observed cave density files:

```
Server/HytaleGenerator/Density/Plains1_Caves_Terrain.json
Server/HytaleGenerator/Density/Plains1_Caves_Deeproot_Terrain.json
Server/HytaleGenerator/Density/Plains1_Caves_Mountains.json
Server/HytaleGenerator/Density/Volcanic1_Caves_Terrain.json
```

Each is a self-contained density graph with a root that `ExportAs` a name. Biomes then pull that
name in. For example `Plains1_Caves_Terrain.json` exports `"Plains1_Caves_Terrain"`, and
`Biomes/Plains1/Plains1_Oak.json` imports it.

---

## How carving works

The terrain root in `Plains1_Oak.json` is a `Min` node:

```json
"Density": {
  "Type": "Min",
  "Inputs": [
    { "Type": "Imported", "Name": "Plains1_Caves_Terrain" },
    { "Type": "Mix", "ExportAs": "Plains1_Oak_Terrain_Field", "Inputs": [ ... surface ... ] }
  ]
}
```

`Min` returns the smaller of the two inputs. The surface field is positive (solid) below ground.
The cave field is engineered to dip **below** the surface value (often strongly negative) along
the tunnels and chambers; where it does, `Min` selects it and the cell reads as empty. Everywhere
else the cave field stays high enough that the surface field wins and the ground is untouched.

There is no separate carve pass, no priority table, no corridor graph — carving is just this one
`Min`.

---

## Anatomy of a cave field

`Server/HytaleGenerator/Density/Plains1_Caves_Terrain.json` is the reference example. Its root is
a `Cache` (capacity 3) that exports `"Plains1_Caves_Terrain"`, wrapping a `Mix`:

```json
{
  "Type": "Cache",
  "ExportAs": "Plains1_Caves_Terrain",
  "Capacity": 3,
  "Inputs": [ { "Type": "Mix", "Inputs": [ /* Max(...), Constant 1, CurveMapper(...) */ ] } ]
}
```

The editor groups (preserved in `$NodeEditorMetadata.$Groups`) name the parts of the field, which
is the clearest description of how a cave is composed in practice:

- **Snake Floors** — a `SimplexNoise2D` (`Seed: "Cave-Floor"`, `Scale: 300`) shaped by a
  `CurveMapper` over `BaseHeight Base` so the field defines a winding floor height.
- **Snake Ceilings** — another noise + `CurveMapper(BaseHeight)` defining the ceiling.
- **Snake Walls** — a `Pow`/`Abs`/`Normalizer` chain over a `SimplexNoise2D`
  (`Seed: "Caves-Snakes"`) that pinches the tunnel width.
- **Cavern Ceilings** — a `Sum` of a `CurveMapper(BaseHeight)` and a `SimplexNoise2D`
  (`Seed: "Caves-Ceilings"`).

These are combined with `Max`, `Min`, `Sum`, and `Inverter` nodes — the same families documented
in [worldgen-terrain.md](worldgen-terrain.md).

---

## Building blocks

The recurring idioms in cave fields:

### Confine carving to a depth band

A `CurveMapper` fed by `BaseHeight` (`Distance: true`) maps altitude to a multiplier so caves only
appear in a vertical range. From `Plains1_Caves_Terrain.json`:

```json
{
  "Type": "CurveMapper",
  "Curve": { "Type": "Manual", "Points": [
    { "In": -90, "Out": 1 },
    { "In": -80, "Out": 0 },
    { "In": 50,  "Out": 0 },
    { "In": 60,  "Out": 1 }
  ]},
  "Inputs": [ { "Type": "BaseHeight", "BaseHeightName": "Base", "Distance": true } ]
}
```

This produces `0` (no influence) through the mid-depths and rises to `1` near the top and bottom,
walling caves off from the surface and from bedrock.

### Tunnel shape from noise

A `SimplexNoise2D` defines the meander; a `CurveMapper` over `BaseHeight` ties the noise to a
floor or ceiling height:

```json
{
  "Type": "SimplexNoise2D",
  "ExportAs": "Plains1_Mountains_Cave_Snakes",
  "Lacunarity": 4, "Persistence": 0.25, "Octaves": 3,
  "Scale": 300, "Seed": "Cave-Floor"
}
```

### Wall pinch with Pow/Abs

```json
{
  "Type": "Pow", "Exponent": 3,
  "Inputs": [ { "Type": "Normalizer", "FromMin": 0, "FromMax": 1, "ToMin": 0.3, "ToMax": 1,
    "Inputs": [ { "Type": "Abs", "Inputs": [
      { "Type": "SimplexNoise2D", "Scale": 75, "Seed": "Caves-Snakes" } ] } ] } ]
}
```

`Abs` of noise gives a value near zero along the noise's zero-crossings (the tunnel center) and
larger away from them; `Pow` sharpens that into a narrow corridor.

---

## Volcanic example

`Server/HytaleGenerator/Density/Volcanic1_Caves_Terrain.json` shows a different recipe but the same
mechanics. Its root `Mix` combines a `Constant -1`, a `Sum`, and clamped/inverted noise. The
carving band here is shaped by a four-point `CurveMapper`:

```json
{
  "Type": "CurveMapper",
  "Curve": { "Type": "Manual", "Points": [
    { "In": -0.25, "Out": -1 },
    { "In": -0.02, "Out": 1 },
    { "In":  0.02, "Out": 1 },
    { "In":  0.25, "Out": -1 }
  ]}
}
```

This maps a noise value near zero to `1` and pushes the extremes to `-1`, producing thin sheet-like
hollows along the noise's zero band — a stylistically different cave from the Plains "snakes", built
with the identical node types.

---

## What does NOT exist

The previous version of this document described a fictional cave system. None of these appear in
any asset file and they are not part of the format:

`CaveType`, `CaveNodeType`, `CaveNodeShape` (cylinder/ellipsoid/pipe/etc.),
`CaveNodeChildEntry`/corridors, `CaveNodeCoverEntry`, `CavePrefabContainer`, `CavePopulator`,
`EntryNode`, `PitchRange`/`YawRange`, `FluidLevel`/`FluidType` cave flooding, and the
`Server/WorldGen/Cave/` or `Server/WorldGen/CaveNode/` directories. Caves are density fields under
`Server/HytaleGenerator/Density/` combined into terrain with `Min`.

(Decorations and encounters *inside* caves — boulders, moss, mobs — are placed by ordinary prop
`Props[]`/`Assignments` entries, e.g. `Plains1_Oak_Cave_Boulders`, `Plains1_Oak_Cave_Moss`,
`Plains1_Oak_Cave_Encounters`. See [worldgen-prefabs.md](worldgen-prefabs.md).)

---

## Related Documentation

- [Terrain Density Graphs](worldgen-terrain.md) - The density node vocabulary caves reuse
- [World Generation Overview](worldgen.md) - Node-graph system
- [Prefabs / Props](worldgen-prefabs.md) - Placing cave decorations and encounters
