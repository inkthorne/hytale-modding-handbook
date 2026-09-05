---
title: "Mounts & Seating"
description: "Hytale's mount system — ride NPCs, sit on block seats and drive minecarts. The Mount, Seating and SpawnMinecart interactions, the BlockMountAPI, the MountedComponent / MountedByComponent pair, the NPC Mount action, and the /mount commands."
seo:
  type: TechArticle
---

# Mounts & Seating

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item`, `Server/NPC` · **Verified against 0.6.3**

Three different things in Hytale are the same system underneath: **riding an NPC**, **sitting on a
block**, and **driving a minecart**. All three end with a `MountedComponent` on the rider and a
`MountedByComponent` on whatever is being ridden, and all three are driven from JSON — an
interaction on an item or block, or an action in an NPC role.

`MountPlugin` (`com.hypixel.hytale.builtin.mounts`) owns the runtime. It is a **bundled plugin,
not a core one**, so everything on this page exists only when it is loaded — see the
[interaction registry](interactions.md#complete-type-registry).

## Packages and key classes

| Class | Package (`com.hypixel.hytale.builtin.mounts…`) | Role |
|-------|--------------------------------------------------|------|
| `MountPlugin` | (root) | Registers the components, systems, interactions, the NPC `Mount` action and the `/mount` command |
| `BlockMountAPI` | (root) | Static entry point for mounting an entity onto a **block** seat |
| `MountedComponent` | (root) | On the **rider**: what it is mounted to, the attachment offset, the controller |
| `MountedByComponent` | (root) | On the **mount**: the list of passengers |
| `BlockMountComponent` | (root) | `ChunkStore` component marking an occupied block seat |
| `NPCMountComponent` | (root) | On a mountable NPC; JSON key `OriginalRoleIndex` |
| `MinecartComponent` | `minecart` | Marks a spawned minecart entity |
| `MountSystems` | (root) | The bulk of the behaviour — input, teleport, death, tracking, minecart hits |
| `NPCMountSystems` | (root) | NPC-specific dismount rules |
| `ActionMount` / `BuilderActionMount` | `npc`, `npc.builders` | The NPC core-component action, registered as `"Mount"` |
| `MountGamePacketHandler` | (root) | Client→server mount packets |

## The three JSON entry points

> **`"Type": "Mount"` means two different things.** As an **interaction** it takes
> `AttachmentOffset` and `Controller`. As an **NPC action** — a core component registered by
> `NPCPlugin.registerCoreComponentType("Mount", …)` — it takes `AnchorX`, `AnchorY`, `AnchorZ`
> and `MovementConfig`. Different registries, same string. Of the three shipped assets containing
> `"Type": "Mount"`, **two are the NPC action** (`Template_Livestock.json`,
> `Component_Instruction_Interaction_Mount.json`) and only `Rail_Kart.json` is the interaction.

### Mount (interaction)

**Package:** `com.hypixel.hytale.builtin.mounts.interactions.MountInteraction`

Mounts the interacting entity onto the **target entity**. Extends `SimpleInstantInteraction`.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `AttachmentOffset` | vec3 | no | Where the rider sits relative to the mount. Defaults to `0,0,0` |
| `Controller` | string | **yes** (`Validators.nonNull()`) | `Minecart` or `BlockMount` — the two `MountController` values |

Behavior:

- **It toggles.** If the entity already has a `MountedComponent`, the component is removed and the
  interaction ends `Failed` — so a second use dismounts, and a `Failed` branch will fire on the
  dismount, not only on a genuine failure.
- Fails with no target entity, and fails the server-side range check
  (`InteractionValidation.canPlayerInteractWithEntity`), which logs at `WARNING` with the entity name.
- Fails if the target already carries a `MountedByComponent` with a non-empty passenger list — one
  rider per mount.

### Seating (interaction)

**Package:** `com.hypixel.hytale.builtin.mounts.interactions.SeatingInteraction`

Sits the player on the **targeted block**. Extends
[SimpleBlockInteraction](interactions.md#simpleblockinteraction) and takes **no properties** —
codec doc: "Arranges perfect seating accommodations". The whole of the shipped
`Server/Item/Interactions/Block/Block_Seat.json` is:

```json
{
  "Type": "Seating"
}
```

It delegates to `BlockMountAPI.mountOnBlock` and reacts to the result: on `ALREADY_MOUNTED` it
plays `SFX_Creative_Play_Add_Mask` to the player; on success it plays the block's own `Walk` sound
from its `BlockSoundSet`; on any other failure it sends `server.interactions.didNotMount` with the
failure state as the `state` parameter.

### SpawnMinecart (interaction)

**Package:** `com.hypixel.hytale.builtin.mounts.interactions.SpawnMinecartInteraction`

Spawns a minecart entity on the targeted block. Extends `SimpleBlockInteraction`.

| Property | Type | Description |
|----------|------|-------------|
| `Model` | string | Model asset id for the cart. Validated against `ModelAsset`; an unresolvable id falls back to `ModelAsset.DEBUG` rather than failing |
| `CartInteractions` | object | Map of `InteractionType` → interaction, attached to the spawned cart. This is how the cart becomes rideable |

`Server/Item/Items/Rail/Rail_Kart.json` is the only shipped use, and it shows the pattern the two
interactions form together — spawn the cart, then give the cart a `Use` chain that mounts whoever
uses it:

```json
{
  "Type": "SpawnMinecart",
  "Model": "Minecart",
  "Next": {
    "Type": "ModifyInventory",
    "RequiredGameMode": "Adventure",
    "AdjustHeldItemQuantity": -1
  },
  "CartInteractions": {
    "Use": {
      "Interactions": [
        {
          "Type": "Mount",
          "AttachmentOffset": { "X": 0, "Y": 1, "Z": 0.3 },
          "Controller": "Minecart"
        }
      ]
    }
  }
}
```

Behavior worth knowing: the cart **snaps to the rail** if the target block has a `RailConfig` —
the interaction projects the spawn point onto the nearest rail segment within `0.8` blocks and
takes that segment's direction as the cart's yaw and pitch, flipping it to face the way the player
is looking. With no rail config it instead sits the cart on top of the block's bounding box. The
cart records the item it was spawned from in its `MinecartComponent`.

### Mount (NPC action)

Registered by `MountPlugin` as an NPC core component, so it appears in a role's `Instructions`
rather than in an item's interaction chain — see [NPC Roles](npc-roles.md).

| Property | Description |
|----------|-------------|
| `AnchorX` / `AnchorY` / `AnchorZ` | Rider attachment offset, usually `Compute`d from role parameters |
| `MovementConfig` | Movement config the NPC switches to while ridden |

`Template_Livestock.json` wires it behind a `HasInteracted` sensor, which is how a tamed animal
becomes rideable:

```json
{
  "Type": "Mount",
  "AnchorX": { "Compute": "MountAnchorX" },
  "AnchorY": { "Compute": "MountAnchorY" },
  "AnchorZ": { "Compute": "MountAnchorZ" },
  "MovementConfig": { "Compute": "MountMovementConfig" }
}
```

## BlockMountAPI (Java)

**Package:** `com.hypixel.hytale.builtin.mounts.BlockMountAPI`

The one public entry point for seating an entity on a block. Both `SeatingInteraction` and
[the `Bed` interaction](player.md#bed-interaction) go through it.

```java
static BlockMountAPI.BlockMountResult mountOnBlock(
        Ref<EntityStore> entity, CommandBuffer<EntityStore> commandBuffer,
        Vector3i blockPosition, Vector3d whereWasHit)
```

`BlockMountResult` is a **sealed interface** with two implementations, so the result is
exhaustively switchable:

| Result | Meaning |
|--------|---------|
| `BlockMountAPI.Mounted` | A record of `(BlockType blockType, MountedComponent component)` — the seat that was taken |
| `BlockMountAPI.DidNotMount` | An enum of seven failure reasons |

`DidNotMount` values: `CHUNK_NOT_FOUND`, `CHUNK_REF_NOT_FOUND`, `BLOCK_REF_NOT_FOUND`,
`INVALID_BLOCK`, `ALREADY_MOUNTED`, `UNKNOWN_BLOCKMOUNT_TYPE`, `NO_MOUNT_POINT_FOUND`.

`whereWasHit` matters: it is the point the player actually clicked, and it selects **which** seat
of a multi-seat block is taken. Callers pass the raw target block position plus `0.5` on each axis
(the block centre) when they have no finer hit information.

The seats themselves are block data, not mount data — the `Seats` and `Beds` arrays of a
`BlockType`, each entry an [offset and yaw](blocks-java-api.md#blockmountpoint). A block with no matching
entry yields `NO_MOUNT_POINT_FOUND`.

## Components

| Component | Store | Notes |
|-----------|-------|-------|
| `MountedComponent` | `EntityStore` | On the **rider**. Constructed `new MountedComponent(target, attachmentOffset, controller)` |
| `MountedByComponent` | `EntityStore` | On the **mount**; `getPassengers()` is what `MountInteraction` checks for occupancy |
| `BlockMountComponent` | `ChunkStore` | Marks the occupied block seat; `MountSystems.RemoveBlockSeat` clears it when the block goes |
| `NPCMountComponent` | `EntityStore` | Registered under the JSON name `"Mount"`. One key, `OriginalRoleIndex` — the role to restore when the NPC is dismounted |
| `MinecartComponent` | `EntityStore` | Registered under `"Minecart"`; remembers the item id the cart came from |

The rider/mount split is the thing to hold onto: **`MountedComponent` is on the rider and points
at the mount; `MountedByComponent` is on the mount and lists riders.** `MountSystems.TrackedMounted`
keeps the pair consistent, and `RemoveMountedBy` / `RemoveMounted` unwind it.

Dismount is not one code path but a set of systems, which is worth knowing before adding your own:
`NPCMountSystems` dismounts on **player death**, on the player entering **spectator mode**, on the
**mount's** death, and on player removal; `MountSystems` additionally handles the mounted entity's
own death, spectating, and teleports (`TeleportMountedEntity` moves the rider with the mount).

## Commands

`/mount` is a **command collection** — it takes no action itself, and its subcommands are what run.
The collection requires the `hytale:WorldEditor` permission group.

| Command | Permission | Description |
|---------|-----------|-------------|
| `/mount dismount` | inherits `hytale:WorldEditor` | Dismount yourself. A nested `other` form takes a required player argument to dismount someone else |
| `/mount check` | `hytale:Adventurer` | Report mount state |

> Note the spelling: there is no top-level `/dismount` or `/mountcheck`. The subcommand is
> registered as `check`, not `mountcheck`, so the full form is `/mount check`.

## Related

- [Interactions API](interactions.md) — the interaction system these three types plug into
- [NPC Roles](npc-roles.md) — where the `Mount` **action** lives
- [Block Items](items-blocks.md) and [blocks-java-api.md](blocks-java-api.md#blockmountpoint) — `Seats` / `Beds` mount points
- [player.md → Bed Interaction](player.md#bed-interaction) — the other `BlockMountAPI` caller
