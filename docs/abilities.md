---
title: "Abilities and Runes"
description: "Hytale's rune-ability system (0.7.2+) — core and support rune items (the Item Ability block), the ability slots and rune bag, ability attributes that support runes modify, ability keywords and elements, the ten AbilitiesPlugin interaction types, the ability bench, and the Java entry points."
seo:
  type: TechArticle
---

# Abilities and Runes

**Doc type:** Java API + JSON asset format · **Assets:** `Server/Item/Items/Rune`, `Server/Abilities/Keywords`, `Server/Abilities/Elements` · **Verified against 0.7.2**

New in 0.7.2. An **ability** is a rune item whose `Ability` block says what it casts. A **core** rune
names a root interaction to cast, a cooldown and a resource cost. A **support** rune sits beside a
core rune and modifies it: it scales the core's named **ability attributes** (`Damage`, `AoeScale`,
`Duration`, …), adds on-hit effects, or converts its elemental damage. Players arrange runes on the
**ability bench**, into six ability slots that form two lines of one core and two supports, and fire
the two lines with the `Ability2` and `Ability3` inputs while holding a weapon.

The system is split between core code and a bundled plugin:

- **Core** (always loaded): the item `Ability` key (`ItemAbility`, `CoreItemAbility`,
  `SupportItemAbility`), the `Server/Abilities/Keywords` store (`AbilityKeyword`), the
  `AbilitySlots` and `RuneBag` inventory sections, the cast snapshot (`ImpactModifiers`,
  registered by `ProjectileModule`), and the attribute keys on existing interactions
  (`DamageAttribute`, `SizeAttribute`, `UseAbilityCost`, …).
- **`AbilitiesPlugin`** (`com.hypixel.hytale.builtin.abilities`, manifest identity
  `Hytale:Abilities`, depends on `Hytale:EntityModule`, `Hytale:InteractionModule` and `Hytale:NPC`):
  the `Server/Abilities/Elements` store, the ten ability interaction types, six ECS components,
  their systems, the bench intro page, and the `/abilities` command. It is absent from
  `Constants.CORE_PLUGINS`, so every interaction type on this page exists only while the plugin is
  loaded. A plugin that registers content against it should declare
  `"Dependencies": { "Hytale:Abilities": "*" }`.

---

## Overview

How one cast flows, using the shipped `Rune_Fireball` (full walkthrough in
[The Fireball rune, end to end](#the-fireball-rune-end-to-end)):

1. The player puts `Rune_Fireball` in slot 0 of their ability slots and, optionally, support runes in
   slots 1 and 2. The slot filters accept a support only when it supports the core
   (see [Ability Slots and the Rune Bag](#ability-slots-and-the-rune-bag)).
2. With a weapon in the active hotbar slot, the player fires `Ability2`.
   `InteractionContext.forInteraction` builds the context from the ability slots (section `-11`,
   slot 0) and the chain runs the core's `Cast` root, `Root_Ability_Fireball`
   ([details](interactions-context.md#ability-slots-072)).
3. As the chain starts, `AbilityCastSnapshotSystem` stores an `ImpactModifiers` snapshot in the
   chain's meta store: the core's `Attributes`, modified by each supporting rune in the line, plus the
   supports' `OnHitEffects` and `ConvertElement`.
4. The cast chain gates and spends the rune's `Cost` (`StatsCondition` / `ChangeStat` with
   `UseAbilityCost`), arms its `Cooldown` (`TriggerCooldown` with `UseAbilityCooldown`), and
   launches a projectile with `LaunchAbilityProjectile`.
5. The projectile carries the snapshot as an `ImpactModifiers` component. Its hit chain reads the
   attributes through `*Attribute` keys (`SizeAttribute: "AoeScale"` on the selector,
   `DamageAttribute: "Damage"` on the damage), and damage it deals applies the supports' on-hit
   effects and element conversion.

---

## Key Classes

| Class | Package | Description |
|-------|---------|-------------|
| `ItemAbility` | `server.core.asset.type.item.config` | The item `Ability` block: a codec map keyed by `Slot` (`Core` or `Support`) |
| `CoreItemAbility` | `server.core.asset.type.item.config` | A castable ability: cooldown, cost, keywords, attributes, `Cast` root |
| `SupportItemAbility` | `server.core.asset.type.item.config` | A modifier rune: keyword gates, attribute modifiers, on-hit effects, element conversion |
| `AbilityKeyword` | `server.core.asset.type.item.config` | Asset in `Server/Abilities/Keywords`; the tags support runes gate on |
| `InventoryComponent.AbilitySlots` | `server.core.inventory` | Section `-11`: six ability slots, two lines of three |
| `InventoryComponent.RuneBag` | `server.core.inventory` | Section `-12`: a 50-slot bag that accepts only ability items |
| `ImpactModifiers` | `server.core.modules.projectile.component` | The resolved attributes, on-hit effects and element of one cast; a meta object and a component |
| `AbilityCastUtil` | `server.core.modules.interaction.interaction.util` | Resolves the casting ability and its cost from an `InteractionContext` |
| `AbilityAttributeBinding` | `server.core.modules.interaction.interaction.config.data` | Interface of every interaction that reads an ability attribute |
| `AbilitiesPlugin` | `builtin.abilities` | The plugin: interaction types, components, systems, command |
| `Element` | `builtin.abilities.element` | Asset in `Server/Abilities/Elements`: element states and reactions |
| `AbilityKeywordAudit` | `builtin.abilities.keyword` | The `--validate-assets` check of keyword promises |
| `AbilityCharges` | `builtin.abilities.trigger` | Component holding the armed charges of `GrantAbilityCharges` buffs |
| `AbilityBenchIntro` | `builtin.abilities.component` | Persisted component: has this player seen the bench intro |

All packages are under `com.hypixel.hytale`.

---

## Rune Items (`Ability`)

An item becomes a rune through its `Ability` key, which `Item.CODEC` reads with `appendInherited`, so
a child item inherits its parent's ability. `Item.getAbility()` returns it, or `null`. Shipped runes
live in `Server/Item/Items/Rune/Ability/` (core) and `Server/Item/Items/Rune/Modifier/` (support).
Like any item they must sit under `Server/Item/Items/`, but the subfolder below it is free: the `Slot`
value decides the kind. `Rune_Empty` in the `Ability` folder
has no `Ability` block at all.

### ItemAbility

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.ItemAbility`

`ItemAbility.CODEC` is a `CodecMapCodec` keyed by `"Slot"`, with two registrations taken from the
`AbilitySlot` enum: `Core` → `CoreItemAbility` and `Support` → `SupportItemAbility`.
`ItemAbility.getSlot()` returns the enum value.

### CoreItemAbility

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.CoreItemAbility`

`"Slot": "Core"`. No key carries a `nonNull` validator.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Cooldown` | float | `0.0` | Seconds between casts. Codec doc: "The single source: the cast chain arms it with TriggerCooldown { UseAbilityCooldown: true }." The cast's `Cooldown` attribute multiplies it |
| `Cost` | float | `0.0` | Resource cost per cast, gated and spent by the cast chain through `UseAbilityCost`. The cast's `Cost` attribute multiplies it |
| `CostType` | enum | `Mana` | The stat the cost is taken from: `None`, `Mana`, `Stamina` or `Health` |
| `Weapons` | string[] | — | Weapon families (`Family` item tags, e.g. `Staff`, `Sword`) of which the caster must hold one. Absent or empty: any weapon |
| `AbilityKeywords` | string[] | — | [Ability keyword](#ability-keywords) ids, validated late against the keyword store. Keywords are flat, so list every keyword the ability counts as; the tooltip lists them in this order |
| `Attributes` | map string → float | — | Named [ability attributes](#ability-attributes) the cast chain binds to and support runes modify |
| `Cast` | root interaction | — | The root interaction cast from the ability slot, late-validated. Inline or a root-interaction id |

The `Cast` root runs only from an ability slot. Codec doc: "Abilities cast only from the bench; an
ability item held in the hand exposes no interactions."

**Weapon gate.** `CoreItemAbility.canUseWith(ItemStack)` takes the active hotbar item. It fails for an
empty hand and for an item with no `Weapon` block, passes for any weapon when `Weapons` is empty, and
otherwise passes when the item's expanded tags hold `Family=<name>` for one of the listed names. No
shipped rune sets `Weapons`. When the check fails while a hotbar item is held, the chain still runs
from the ability slot, with no ability item and no root, so the input does nothing.

From `Server/Item/Items/Rune/Ability/Rune_Fireball.json` (the `Ability` block only):

```json
"Ability": {
  "Slot": "Core",
  "Cooldown": 2,
  "Cost": 30,
  "CostType": "Mana",
  "AbilityKeywords": ["Damage", "Elemental", "Fire", "Projectile", "Aoe"],
  "Cast": "Root_Ability_Fireball"
}
```

The rest of that file is an ordinary item: `MaxStack: 1`, the shared model
`Items/Runes/Rune_Ability.blockymodel` with a per-rune texture, and a `Recipe` at the
`GoblinLab_Workbench`.

### SupportItemAbility

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.SupportItemAbility`

`"Slot": "Support"`. No key carries a `nonNull` validator; the three keyword arrays and `OnHitEffects`
reject null elements.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `RequiresAnyAbilityKeyword` | string[] | — | The core must carry at least one of these keywords. Absent or empty: no constraint |
| `RequiresAllAbilityKeywords` | string[] | — | The core must carry every one of these keywords |
| `ExcludesAnyAbilityKeyword` | string[] | — | The core must carry none of these keywords |
| `AttributeModifiers` | map string → modifier[] | — | Modifiers applied to the core's attributes by name. Each modifier is a `StaticModifier` object: `CalculationType` (`Additive` or `Multiplicative`, required) and `Amount` |
| `OnHitEffects` | string[] | — | `EntityEffect` ids applied to every entity the ability damages (late-validated) |
| `ConvertElement` | string | — | A `DamageCause` id (late-validated against the damage causes, e.g. `Wind`): the ability's elemental damage converts to it. Damage numbers and ability particles recolor to match |

`SupportItemAbility.supports(CoreItemAbility)` is the gate the slot filter and the snapshot both use:
all three keyword tests must pass. Keyword ids that do not resolve are dropped when the rune loads.

**How a line resolves.** `ImpactModifiers.collect` walks the two slots after the core, left to right,
and skips any support that `supports(core)` rejects. For each modifier map entry it starts from the
core's value for that attribute, **or `1` when the core omits it**, and applies the modifiers in order:
`Additive` adds `Amount`, `Multiplicative` multiplies by it. `OnHitEffects` from both supports are
concatenated, and the rightmost `ConvertElement` wins. Because the base is `1`, a rune can modify an
attribute the core never declares: `Rune_Aoe_Up` multiplies `AoeScale` on `Rune_Fireball`, which has
no `Attributes` block, to `1.6`.

From `Server/Item/Items/Rune/Modifier/Rune_Rend.json`:

```json
"Ability": {
  "Slot": "Support",
  "RequiresAnyAbilityKeyword": ["Damage"],
  "ExcludesAnyAbilityKeyword": ["Poison"],
  "AttributeModifiers": {
    "Damage":   [{ "CalculationType": "Multiplicative", "Amount": 0.8 }],
    "Cooldown": [{ "CalculationType": "Multiplicative", "Amount": 1.25 }],
    "Cost":     [{ "CalculationType": "Multiplicative", "Amount": 1.2 }]
  },
  "OnHitEffects": ["Rend"]
}
```

### Shipped runes

24 items carry an `Ability` block in 0.7.2: 9 core and 15 support, of which 2 core and 4 support sit
in `_Debug` folders. Core runes (all cost `Mana`):

| Item | Cooldown | Cost | `AbilityKeywords` | `Attributes` | `Cast` |
|------|----------|------|-------------------|--------------|--------|
| `Rune_ChainHook` | 6 | 50 | Damage, Physical, Projectile, Duration | `Duration` 0.8 | `Root_Ability_ChainHook` |
| `Rune_ChargedShot` | 4 | 35 | Damage, Elemental, Water, Projectile, Charged, Duration | `Duration` 2, `FreezeDuration` 1.5, `ShortFreezeDuration` 0.8, `Fork` 3, `SplitChildDamage` 0.35, `SplitChildScale` 0.5, `SplitChildFreezeDuration` 0.02 | `Root_Ability_ChargedShot` |
| `Rune_Enrage` | 4 | 45 | Buff, Duration | `Duration` 8 | `Root_Ability_Enrage` |
| `Rune_Fireball` | 2 | 30 | Damage, Elemental, Fire, Projectile, Aoe | — | `Root_Ability_Fireball` |
| `Rune_GroundSlam` | 5 | 40 | Damage, Elemental, Earth, Melee, Aoe | — | `Root_Ability_GroundSlam` |
| `Rune_PoisonImbue` | 4 | 40 | Buff, Damage, Poison, Duration | `Duration` 6 | `Root_Ability_PoisonImbue` |
| `Rune_WindStrike` | 2 | 30 | Buff, Damage, Elemental, Wind, Aoe, Duration | `Duration` 8 | `Root_Ability_WindStrike` |
| `Debug_Rune_Frostbolt` | 4 | 20 | Damage, Elemental, Water, Projectile, Aoe | — | `Root_Debug_Ability_Frostbolt` |
| `Debug_Rune_Tornado` | 8 | 15 | Damage, Elemental, Wind, Aoe, Duration | `Duration` 5 | `Root_Debug_Ability_Tornado` |

Support runes (× is `Multiplicative`, + is `Additive`):

| Item | Keyword gate | `AttributeModifiers` | Other |
|------|--------------|----------------------|-------|
| `Rune_Aoe_Up` | any of Aoe | ProjectileSize ×2.5, AoeScale ×1.6, Damage ×1.4, Speed ×0.5, Cost ×1.6 | — |
| `Rune_Convert_Lightning` | any of Elemental | — | `ConvertElement`: `Lightning` |
| `Rune_Convert_Wind` | any of Elemental | — | `ConvertElement`: `Wind` |
| `Rune_Damage_Up` | any of Damage | Damage ×1.5 | — |
| `Rune_Duration_Up` | any of Buff | Duration ×1.5, Cost ×1.3, Cooldown ×1.6 | — |
| `Rune_Fork` | any of Projectile | SplitChildDamage ×0.7, SplitChildScale ×0.7, SplitChildAoeScale ×0.7, Cooldown ×1.2, Fork +2, Cost ×1.25 | — |
| `Rune_Quickening` | any of Aoe, Buff | Cooldown ×0.7, Speed ×1.4, Damage ×0.75, Cost ×0.8, Duration ×0.8 | — |
| `Rune_Rend` | any of Damage; none of Poison | Damage ×0.8, Cooldown ×1.25, Cost ×1.2 | on hit: `Rend` |
| `Rune_Ricochet` | any of Projectile | Speed ×1.4, SplitChildDamage ×0.8, Cooldown ×1.3, Ricochet +2, Cost ×1.25 | — |
| `Rune_Thrift` | — | Damage ×0.8, Cost ×0.75 | — |
| `Rune_Wither` | any of Damage; none of Poison | Damage ×0.7, Cooldown ×1.3, Cost ×1.2 | on hit: `Wither` |
| `Debug_Rune_Burning` | any of Damage | — | on hit: `Burn` |
| `Debug_Rune_Fork` | any of Projectile | Fork +2, SplitChildDamage ×0.5, SplitChildScale ×0.5 | — |
| `Debug_Rune_Speed` | — | Speed ×0.35, AoeScale ×3, ProjectileSize ×2, Cost ×0.5, Cooldown ×0.5 | — |
| `Debug_Rune_Test` | — | — | — |

---

## Ability Attributes

An attribute is a named float. Nothing registers the names: a core declares some in `Attributes`, a
support modifies any name it likes, and an interaction reads one by naming it in an `*Attribute` key.
A name that nothing reads does nothing. `ImpactModifiers.getAttribute(name, fallback)` returns the
fallback for a name the cast lacks, and every reader passes a fallback that leaves its authored value
unchanged, so attribute keys are inert outside ability chains.

Where the values are found. `ImpactModifiers.resolve(context, actingRef, accessor)` returns the cast
snapshot from the chain's meta store (`ImpactModifiers.CAST_SNAPSHOT`) when there is one, else the
acting entity's `ImpactModifiers` component. Ability projectiles, ability entities and
`GrantAbilityCharges` activations all carry the cast's values forward, so their chains resolve the
same numbers.

Names the engine reads by itself, whatever the interactions say:

| Attribute | Read by | Effect |
|-----------|---------|--------|
| `Cost` | `AbilityCastUtil.resolveCostMap` | Multiplies the rune's `Cost` (see [Ability Costs](interactions-flow.md#ability-costs)) |
| `Cooldown` | `TriggerCooldown` with `UseAbilityCooldown` | Multiplies the rune's `Cooldown` |
| `Fork` | `LaunchAbilityProjectile` | Rounded; 2 or more makes the projectile split into that many on its first entity hit |
| `Ricochet` | `LaunchAbilityProjectile` | Rounded; 2 or more makes the projectile chain that many total hits |
| `RicochetRange` | `SplitAbilityProjectile` | Replaces the interaction's `RicochetRange` |
| `SplitChild<X>` | `SplitAbilityProjectile` | Multiplies each child projectile's `<X>` attribute at every split; `SplitChildScale` multiplies the child's flight scale |

Every other name is read through a binding key. The keys on the ability interactions are in the
tables under [Ability Interactions](#ability-interactions); the keys added to existing interactions
are `DamageAttribute` on `DamageEntity`, `DurationAttribute` on `ApplyEffect`, `SizeAttribute` on
the `AOECircle` and `Stab` selectors and `DistanceAttribute` on `Raycast`, documented in
[Ability Attribute Keys](interactions-combat.md#ability-attribute-keys). The table for each key says
whether its attribute **replaces** the authored value or **multiplies** it.

Shipped bindings in 0.7.2, by key and attribute: `DamageAttribute: "Damage"` (12 files),
`SpeedAttribute: "Speed"` (9), `ScaleAttribute: "AoeScale"` (6), `DurationAttribute: "Duration"` (6),
`SizeAttribute: "AoeScale"` (5), `ScaleAttribute: "ProjectileSize"` (5), and one each of
`LifetimeAttribute: "Duration"`, `EffectDurationAttribute: "Duration"`,
`DurationAttribute: "FreezeDuration"` and `DurationAttribute: "ShortFreezeDuration"`.

---

## Ability Slots and the Rune Bag

Two inventory sections hold runes. Both are `InventoryComponent` subclasses registered by
`EntityModule` (see [Inventory sections as components](inventory.md#inventory-sections-as-components)),
and the player init system in `PlayerSystems` ensures every player has both, at the capacities below.

| Section | Id | Component | Capacity | Slot filters |
|---------|----|-----------|----------|--------------|
| Ability slots | `-11` (`InventoryComponent.ABILITIES_SECTION_ID`) | `InventoryComponent.AbilitySlots`, persisted as `AbilitySlotsInventory` | 6 (`InventoryComponent.DEFAULT_ABILITIES_CAPACITY`) | `AbilityCoreSlotFilter` on slots 0 and 3, `AbilitySupportSlotFilter` on the rest |
| Rune bag | `-12` (`InventoryComponent.RUNE_BAG_SECTION_ID`) | `InventoryComponent.RuneBag`, persisted as `RuneBagInventory` | 50 (`InventoryComponent.DEFAULT_RUNE_BAG_CAPACITY`) | `AbilityItemAddFilter` on every slot |

**Layout.** The ability slots are two lines of `InventoryComponent.ABILITIES_LINE_WIDTH` (3) slots:
slot 0 is the first line's core and slots 1–2 its supports; slot 3 is the second line's core and
slots 4–5 its supports. `Ability2` casts line one (slot 0) and `Ability3` casts line two (slot 3).
`Ability1` and `Ability4` are untouched by the system.

**Filters** (they test adds only; removing and dropping always pass):

- `AbilityCoreSlotFilter` accepts an item whose ability is a `CoreItemAbility`, and refuses a second
  copy of a rune already equipped as the core of another line.
- `AbilitySupportSlotFilter` accepts a `SupportItemAbility` only when its line's core slot holds a
  core rune that it supports, and refuses a second copy of the same rune on that line.
- `AbilityItemAddFilter` (rune bag) accepts any item that has an `Ability` block.

**Changing a core evicts its supports.** When a core rune leaves its slot, or is replaced by a
different core, `InventoryUtils` collects the line's supports that the new core does not support (all
of them when the slot empties) and moves them to the rune bag, then storage, then the hotbar. If those
sections lack enough empty slots for every evicted rune, the move is refused.

**Quick-move.** While the ability bench window is open, a quick-move (`SmartMoveType`
`PutInHotbarOrWindow`) of a rune out of one of the player's own sections tries the open window, that
is the ability slots and their filters, first. When the window takes none of it and the rune came from
outside the rune bag, it goes to the rune bag next.

`InventoryComponent.EVERYTHING` leaves out both sections, so a combined-inventory sweep (clearing a
player, counting items) never sees equipped or bagged runes.

---

## The Ability Bench

The bench is a window. `OpenAbilityBenchInteraction.openBench(ref, store)` opens
`Page.Bench` with an `AbilityBenchWindow` (`WindowType.AbilityBench`) over the player's own
`AbilitySlots` container. Any block becomes a bench by running `OpenAbilityBench` from its `Use`
interaction. The shipped bench is `Bench_Abilities` (Runebinder's Lattice), whose block `Use` chain
shows the full pattern, from `Server/Item/Items/Bench/Bench_Abilities.json`:

```json
"Interactions": {
  "Use": {
    "Interactions": [
      {
        "Type": "MarkAbilityBenchIntroSeen",
        "Next": {
          "Type": "Simple",
          "Effects": { "LocalSoundEventId": "SFX_Runebinders_Lattice_Unlock_Local" },
          "Next": { "Type": "OpenCustomUI", "Page": { "Id": "AbilityBenchIntro" } }
        },
        "Failed": { "Type": "OpenAbilityBench" }
      }
    ]
  }
}
```

The three pieces:

| Piece | What it does |
|-------|--------------|
| `MarkAbilityBenchIntroSeen` (interaction) | Codec doc: "Marks the ability bench intro as seen. Runs Next the first time the player uses it, and Failed on every later use." It adds an `AbilityBenchIntro` component if the player has none. No keys |
| `AbilityBenchIntro` (custom page) | Registered with `OpenCustomUIInteraction.registerSimple`, so `OpenCustomUI` opens it by `Id`. It shows `Pages/Abilities/AbilityBenchIntro.ui`; its `#DiscoverRunesButton` opens the bench |
| `OpenAbilityBench` (interaction) | Codec doc: "Opens the ability bench for the using player, over their own ability slots. Author as any block's Use interaction to make that block the bench." No keys |

The `AbilityBenchIntro` component is persisted under the id `AbilityBenchIntro`, with one boolean key,
`Seen`.

### `/abilities`

`AbilitiesCommand`, a player command:

| Command | Effect |
|---------|--------|
| `/abilities` | Opens the ability bench, as `OpenAbilityBench` does |
| `/abilities give` | Gives one of every item with an `Ability` block, sorted by id (24 in 0.7.2), and reports the count. The `server.lang` strings call these "debug" items, but the command takes every rune, shipped or modded |
| `/abilities resetintro` | Removes the `AbilityBenchIntro` component, so the next `MarkAbilityBenchIntroSeen` takes its `Next` branch again |

---

## Ability Keywords

Keywords are the tags support runes gate on. A core rune lists the ones it carries in
`AbilityKeywords`; a support rune tests them with its three keyword arrays.

### AbilityKeyword

**Package:** `com.hypixel.hytale.server.core.asset.type.item.config.AbilityKeyword`

Stored in `Server/Abilities/Keywords/<Id>.json` by a core asset store (`AssetRegistryLoader`), which
loads before `Item`. The file name is the id.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Name` | string | — | **Required** (`Validators.nonNull()`). Localization key of the display name; shipped keywords use `server.ui.abilityKeywords.<Id>` |
| `ShowOnTooltip` | boolean | `true` | List the keyword on the tooltip of runes that carry it. A keyword that only gates support runes hides itself |
| `RequiredAttributes` | string[] | — | Attribute names. A core rune carrying this keyword must bind at least one of them somewhere in its cast chain. Checked only by the [audit](#abilitykeywordaudit) |
| `RequiredInteractions` | string[] | — | Interaction `Type` names. A core rune carrying this keyword must use at least one of them in its cast chain. Checked only by the audit |

The 14 shipped keywords:

| Keyword | `ShowOnTooltip` | Promise |
|---------|-----------------|---------|
| `Aoe` | `true` | `RequiredAttributes`: `AoeScale` |
| `Buff` | `true` | — |
| `Charged` | `true` | — |
| `Damage` | `false` | `RequiredAttributes`: `Damage` |
| `Duration` | `true` | `RequiredAttributes`: `Duration` |
| `Earth` | `true` | — |
| `Elemental` | `false` | — |
| `Fire` | `true` | — |
| `Melee` | `true` | — |
| `Physical` | `true` | — |
| `Poison` | `true` | — |
| `Projectile` | `true` | `RequiredInteractions`: `LaunchAbilityProjectile` |
| `Water` | `true` | — |
| `Wind` | `true` | — |

### AbilityKeywordAudit

**Package:** `com.hypixel.hytale.builtin.abilities.keyword.AbilityKeywordAudit`

`AbilitiesPlugin` runs `AbilityKeywordAudit.run` on every `LoadAssetEvent`, but the audit does
nothing unless the server was started with `--validate-assets`. With that flag:

- Every core rune's cast chain is walked from its `Cast` root, following each
  `LaunchAbilityProjectile` into its `ProjectileConfig`'s interaction roots, each
  `GrantAbilityCharges` into its `PerActivationInteraction`, and each `SpawnAbilityEntity` into its
  `Repeats` chains. The walk collects the interaction types used and the attributes bound.
- These are **violations**: a keyword whose `RequiredInteractions` names an unregistered type; a core
  rune carrying a keyword whose promise its chain does not keep; a support rune requiring
  (`RequiresAny…` / `RequiresAll…`) a keyword that no core rune carries. Each is logged as a warning,
  and any violation **fails the asset load and shuts the server down** with "Ability keywords: N
  contract violation(s)".
- A keyword that no rune uses is logged as a warning only: "Ability keyword '%s' is not used by any
  rune".

So a modded keyword with a promise is checked only on a `--validate-assets` run, and on that run a
broken promise is fatal.

---

## Elements

### Element

**Package:** `com.hypixel.hytale.builtin.abilities.element.Element`

Stored in `Server/Abilities/Elements/<Id>.json` by a store `AbilitiesPlugin` registers, loading after
`DamageCause` and `EntityEffect`. An element ties a damage cause to an **element state**: any
`EntityEffect` whose `Tags` hold `"Element": ["<ElementId>"]` (`Element.EFFECT_TAG_KEY`).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `DamageCause` | string | — | **Required** (`Validators.nonNull()`), late-validated. The damage cause that counts as this element |
| `OnHitEffect` | string | — | `EntityEffect` id, late-validated. Codec doc: "the status a damaging hit of this element applies to its victim". No code in the 0.7.2 jar reads it (bytecode search: only `Element` itself references the field and its getter), so setting it has no effect |
| `Reactions` | map string → reaction | — | Keyed by the **triggering** element id. What happens when a victim carrying this element's state takes damage of that other element |

Each `Reactions` value (`Element.Reaction`):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Effect` | string | — | **Required** (`Validators.nonNull()`), late-validated. `EntityEffect` applied to the victim, credited to the attacker |
| `ConsumeState` | boolean | `true` | Remove the victim's element-state effect that reacted |

**How a reaction fires.** `ReactionDamageSystem` handles every damage event with an amount above `0`
on an entity that has active effects. It maps the damage cause to its element, walking up the cause's
`Inherits` chain until some element names it. It then takes the first element (in asset-map order)
that has a reaction to that trigger and whose state the victim carries, applies the reaction's
`Effect`, and with `ConsumeState` removes the state effect. Any damage of the right cause triggers a
reaction, ability or not.

**Shipped content.** Five elements ship, `Earth`, `Fire`, `Lightning`, `Water` and `Wind`, each a single
`DamageCause` line naming the same-named damage cause, and none declares `Reactions` or `OnHitEffect`.
Three effects carry an element state: `Ability_Frost_Slow`, `Ability_Frost_Chill` and
`Ability_Frost_Freeze`, all tagged `Water`. So in 0.7.2 the reaction machinery is present and unused
by shipped assets.

A reaction is added by overriding an element. This example (unshipped, `MyMod_` effect id) makes
lightning damage on a frosted victim apply a mod effect and clear the frost:

```json
{
  "DamageCause": "Water",
  "Reactions": {
    "Lightning": { "Effect": "MyMod_Electrocuted", "ConsumeState": true }
  }
}
```

saved as `Server/Abilities/Elements/Water.json` in the mod's asset pack.

**Element conversion is separate.** A support rune's `ConvertElement` names a damage cause directly,
and the Element store plays no part in it. `DamageEntity` re-keys every damage entry whose cause is or
inherits the `Elemental` damage cause to the converting cause; physical damage stays as it is. The
shipped elemental causes (`Earth`, `Fire`, `Ice`, `Lightning`, `Poison`, `Water`, `Wind`) all inherit
`Elemental`. Ability particles and trails tinted by a conversion take the converting cause's
`DamageTextColor`.

---

## Ability Interactions

Ten `Type` strings arrived in 0.7.2, all registered by `AbilitiesPlugin`, so each exists only while
that plugin is loaded; the [Complete Type Registry](interactions.md#complete-type-registry) lists
them with the other types. `OpenAbilityBench` and `MarkAbilityBenchIntroSeen` are covered under
[The Ability Bench](#the-ability-bench). The other eight follow. All extend
[SimpleInstantInteraction](interactions.md#simpleinstantinteraction). Seven act on the server only:
each leaves `simulateFirstRun` empty. `GroundedCondition` runs its check in both.

**Which manager runs a cast.** The cast chain runs on the caster's `InteractionManager` (`AbilityChargeActivator.java:105-126`); a player's has a remote client and runs each operation once. Two chains run elsewhere: the `Repeats` chains of a `SpawnAbilityEntity` run on the entity's own manager (`AbilityEntityRepeatSystem.java:49-67`), and the `ProjectileHit` and `ProjectileMiss` chains of an ability projectile run on the projectile's own manager. Both are built with `new InteractionManager(null, ...)` (`AbilityEntitySpawner.java:59`, `AbilityProjectileLauncher.java:102`), which has no remote client, so there the server runs every operation twice: `Explode` and a `ChangeStat` `Add` land twice. The projectile's `ProjectileSpawn` chain runs on the caster's. See [the double run](interactions-double-run.md#what-each-of-the-48-types-does).

### LaunchAbilityProjectile

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.LaunchAbilityProjectileInteraction`

Codec doc: "Launches a server-side projectile along the caster's look. Its hit chain runs where it
lands; with Pierce it flies through entities (hit chain per entity crossed) and its miss chain runs
once where its course ends." The projectile itself is an ordinary `ProjectileConfig` asset
([projectiles.md](projectiles.md)), whose `ProjectileHit` / `ProjectileMiss` chains do the work. The
keys are declared by `AbilityProjectileConfig.appendCodec`, outside the interaction's own chain.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Projectile` | string | — | **Required** (`Validators.nonNull()`). The `ProjectileConfig` id, late-validated against the loaded configs |
| `IgnorePitch` | boolean | `false` | Fire level with the ground, ignoring the caster's look pitch (a ground wave) |
| `Pierce` | boolean | `false` | Fly through entities, running the hit chain once per entity crossed |
| `Distance` | float | `8.0` | Piercing only: how far the projectile travels before its course ends |
| `SizeAttribute` | string | — | Attribute that **multiplies** `Distance` |
| `Lifetime` | float | `4.0` | Maximum flight time in seconds. A piercing projectile ends its course there and runs its miss chain; any other projectile despawns silently |
| `Scale` | float | `1.0` | Base uniform scale of the projectile's model and hit volume |
| `ScaleAttribute` | string | — | Attribute that **multiplies** `Scale` |
| `SpeedAttribute` | string | — | Attribute that **multiplies** the `ProjectileConfig`'s `LaunchForce` |
| `Spectral` | boolean | `false` | Fly through blocks. When false an obstacle stops the flight: a piercing projectile ends its course, any other impacts |
| `TrailParticles` | string | — | Particle system burst repeatedly along the flight path |
| `TrailInterval` | float | `0.15` | Seconds between trail bursts. Trail bursts only run while this is above `0` |
| `TrailScale` | float | `1.0` | Base trail scale, multiplied by the projectile's resolved scale |
| `TrailColor` | color | — | Tint for greyscale (`_GS`) trail textures; an element conversion on the cast overrides it |

The launch copies the cast's attributes, on-hit effects and element onto the projectile as an
`ImpactModifiers` component, and tags it for [SplitAbilityProjectile](#splitabilityprojectile): a
cast whose `Fork` attribute rounds to 2 or more, or whose `Ricochet` attribute does, gets an
`AbilityProjectileSplit` component. An unknown `Projectile` id logs `Ability projectile launch
misconfigured: projectile config '%s' not found` and launches nothing. From
`Server/Item/Interactions/Abilities/GroundSlam/Ability_GroundSlam_Cast.json`, minus its `Effects`:

```json
{
  "Type": "LaunchAbilityProjectile",
  "Projectile": "Projectile_Config_GroundSlam",
  "IgnorePitch": true,
  "Pierce": true,
  "Distance": 6,
  "ScaleAttribute": "AoeScale",
  "SpeedAttribute": "Speed",
  "Lifetime": 2,
  "TrailParticles": "Ability_GroundSlam_Line",
  "TrailInterval": 0.03,
  "TrailScale": 1.2,
  "TrailColor": "#8a5a2c"
}
```

Nine shipped files use the type, all under `Server/Item/Interactions/Abilities/`; their
`ProjectileConfig`s are in `Server/ProjectileConfigs/Abilities/`.

### SplitAbilityProjectile

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.SplitAbilityProjectileInteraction`

Splits an ability projectile on its first entity hit. Author it in a `ProjectileConfig`'s
`ProjectileHit` chain; it reads the executing entity as the projectile and does nothing unless that
projectile carries the `AbilityProjectileSplit` component that
[LaunchAbilityProjectile](#launchabilityprojectile) adds. Codec doc: "Fork counts the projectiles the
flight splits into; Ricochet counts the chain's total hits. Both attributes rest at the implicit base
1." A **fork** fans that many children out around the flight direction. A **ricochet** relaunches one
child at the nearest damageable entity within range that this chain has not already hit. A projectile
with both forks first, and each fork child keeps the remaining ricochet hits. Each child skips the
entities already hit. A cast attribute named `SplitChild<X>` multiplies the child's `X` attribute at
every split (`SplitChildScale` multiplies the child's flight scale instead), so the effect compounds
down the chain.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ForkSpread` | float | `30.0` | Degrees between adjacent fork children; an odd count keeps one child on the original line |
| `RicochetRange` | float | `6.0` | Search radius for the next ricochet target. A `RicochetRange` attribute **replaces** it (and support modifiers grow that attribute from `1`, not from this value) |

Two shipped uses: `Server/Item/Interactions/Abilities/Ability_Split.json`, which is the bare
`{ "Type": "SplitAbilityProjectile" }` that `Projectile_Config_Ability_Fireball` puts first in its
`ProjectileHit` chain, and `ChargedShot/Ability_ChargedShot_Shatter.json`, which sets
`"ForkSpread": 22.5`. A `Fork` or `Ricochet` rune does nothing for an ability whose projectile's hit
chain lacks this interaction.

### ApplyAbilityEffects

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.ApplyAbilityEffectsInteraction`

Applies **one** of `Effects` to the target entity per run. It takes the first listed effect the target
does not carry; if the target carries them all, it takes the one closest to expiring. Several entries
therefore act as stacks of one debuff, each with its own duration. The effect is credited to the
owning entity when there is one, else to the executing entity. The interaction does nothing without a
target entity or when the target has no `EffectControllerComponent`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Effects` | string[] | — | `EntityEffect` ids, one per stack (late-validated) |
| `Duration` | float | `0.0` | Stack duration in seconds; `0` uses the effect's own duration. A positive value applies with `OverlapBehavior.OVERWRITE` |
| `DurationAttribute` | string | — | Attribute that **replaces** `Duration` |
| `DamageAttribute` | string | — | Attribute that **multiplies** the applied stack's damage over time (base 1) |
| `RuneEffects` | boolean | `false` | Also apply the support runes' on-hit effects |

Set `RuneEffects` only on a hit that deals no damage. The codec doc warns that damaging hits already
apply those effects, "and setting this there applies them twice." No shipped asset sets it. The type's
one shipped use is the `PerActivationInteraction` of the [GrantAbilityCharges](#grantabilitycharges)
example below.

### GrantAbilityCharges

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.GrantAbilityChargesInteraction`

A buff that arms charges on the caster. Codec doc: "Applies a buff effect to the caster and arms
ability charges: while the effect is active, each firing of Trigger spends a charge and runs
PerActivationInteraction on the caster with the cast's rune values in context." The charges are an
`AbilityCharges` component entry tied to the effect, and they end with it.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Effect` | string | — | **Required** (`Validators.nonNull()`). The `EntityEffect` put on the caster, looked up only when the interaction runs |
| `Duration` | float | `0.0` | Buff duration in seconds; `0` uses the effect's own duration |
| `DurationAttribute` | string | — | Attribute that **replaces** `Duration` |
| `Trigger` | enum | `OnPrimaryActivation` | `OnPrimaryActivation`: a weapon attack is released, hit or miss, and the chain runs with no target. `OnHit`: a weapon attack lands, and the chain runs with the victim as target entity |
| `MaxCharges` | int | `0` | Activations before the buff ends; `0` means unlimited for the buff's duration |
| `PerActivationInteraction` | root interaction | — | **Required** (`Validators.nonNull()`). Inline `{ "Interactions": [...] }` or a root-interaction id, late-validated |

What counts as a firing, from the three trigger systems:

- `OnPrimaryActivation` fires when a `Primary` chain starts whose root interaction lacks the `Ranged`
  tag (a melee swing), or when a `Primary` weapon attack launches a projectile.
- `OnHit` fires on uncancelled, unblocked damage from the caster's `Primary` chain, or from a
  projectile that a `Primary` weapon attack launched.
- Either way, the charge fires only while the caster's active hotbar item is a weapon the source rune
  accepts (its `Weapons` gate). The chain then runs as a `ProjectileHit` chain with the victim as
  target, or a `ProjectileMiss` chain without one.

A recast with the same `Effect` replaces the earlier entry. When `MaxCharges` runs out, the buff
effect is removed. An `Effect` id that does not resolve logs `GrantAbilityCharges misconfigured:
effect '%s' not found or PerActivationInteraction missing` at run time and grants nothing. From
`Server/Item/Interactions/Abilities/PoisonImbue/Ability_PoisonImbue_Cast.json`, trimmed:

```json
{
  "Type": "GrantAbilityCharges",
  "Effect": "Ability_Poison_Imbue_Buff",
  "Duration": 8,
  "Trigger": "OnHit",
  "PerActivationInteraction": {
    "Interactions": [
      {
        "Type": "ApplyAbilityEffects",
        "Effects": ["Ability_Poison_Stack_A", "Ability_Poison_Stack_B", "Ability_Poison_Stack_C"],
        "Duration": 6,
        "DurationAttribute": "Duration",
        "DamageAttribute": "Damage"
      }
    ]
  }
}
```

(The shipped asset wraps the `ApplyAbilityEffects` in an `EffectCondition` that skips targets carrying
`Antidote`.) The other shipped use, `WindStrike/Ability_WindStrike_Cast.json`, uses
`OnPrimaryActivation`.

### PullEntityAbility

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.PullEntityAbilityInteraction`

Reels the target entity toward the caster, the owning entity when there is one, by putting a
`PulledByAbility` component on the target that `AbilityPullSystem` then drives. Codec doc: "an optional
hooked delay, then a drag lasting a fixed time from any range, stopping at reach. A victim guarding
toward the caster resists the whole pull." The guard test reads the victim's current `Wielding`
interaction: one with no angled-guard config resists from every direction, and an angled guard resists
only within its arc. A resisted or oversized victim also skips `Effect`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Delay` | float | `0.0` | Seconds the victim stays hooked before the reel starts |
| `ReelTime` | float | `0.4` | Seconds the drag takes, whatever the range. Speed is recomputed each tick from the distance and time left |
| `Arc` | float | `1.5` | Upward bow of the drag path in blocks, easing down to the caster's feet on approach |
| `StopRange` | float | `1.5` | Distance from the caster, to the victim's bounding-box edge, at which the reel lets go |
| `MaxTargetWidth` | float | `0.0` | Widest victim (bounding-box width or depth) the pull can move; `0` means no limit |
| `Effect` | string | — | `EntityEffect` applied to the victim when the pull takes hold (late-validated) |
| `EffectDuration` | float | `0.0` | Effect duration in seconds; `0` uses the effect's own |
| `EffectDurationAttribute` | string | — | Attribute that **replaces** `EffectDuration` |

One shipped use, `Server/Item/Interactions/Abilities/ChainHook/Ability_ChainHook_Hit.json`, which
sets every key: `"Delay": 0.25`, `"ReelTime": 0.35`, `"Arc": 3.0`, `"StopRange": 1.5`,
`"MaxTargetWidth": 2.0`, `"Effect": "Ability_Hooked"`, `"EffectDuration": 0.8`,
`"EffectDurationAttribute": "Duration"`.

### SpawnAbilityEntity

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.SpawnAbilityEntityInteraction`

Codec doc: "Spawns a stationary ability entity (e.g. a tornado) at the point the caster aims at. It
lives for Lifetime seconds and re-runs each of its Repeats chains at its own interval. Damage against
it is ignored." The entity carries the cast's attributes, so its repeat chains resolve them too.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Model` | string | — | **Required** (`Validators.nonNull()`). A model asset id; its hitbox is what other abilities target. An unknown id logs `SpawnAbilityEntity misconfigured: model '%s' not found` at run time |
| `Repeats` | object[] | — | **Required** (`Validators.nonNull()`, plus `Validators.nonEmptyArray()`). The repeating chains, shape below |
| `Lifetime` | float | `5.0` | Seconds the entity lives |
| `LifetimeAttribute` | string | — | Attribute that **replaces** `Lifetime` |
| `ScaleAttribute` | string | — | Attribute that uniformly scales the model and hitbox (base 1) |
| `Range` | double | `20.0` | Furthest placement; aiming at nothing places the entity at this range along the aim line |

Each `Repeats` entry (`SpawnAbilityEntityInteraction.RepeatConfig`):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Chain` | root interaction | — | **Required** (`Validators.nonNull()`), late-validated. Inline `{ "Interactions": [...] }` or a **root**-interaction id. Codec doc: "The id of a plain interaction file does NOT work: only root-shaped assets register as chain roots." |
| `Interval` | float | `0.5` | Seconds between runs, validated `> 0` |

Its one shipped use is a debug ability, `Server/Item/Interactions/Abilities/_Debug/Debug_Ability_Tornado_Cast.json`, minus its `Next`:

```json
{
  "Type": "SpawnAbilityEntity",
  "Model": "Tornado",
  "Repeats": [
    { "Interval": 0.25, "Chain": { "Interactions": ["Debug_Ability_Tornado_Pull"] } },
    { "Interval": 1, "Chain": { "Interactions": ["Debug_Ability_Tornado_Damage"] } }
  ],
  "Lifetime": 5,
  "LifetimeAttribute": "Duration",
  "ScaleAttribute": "AoeScale",
  "Range": 20
}
```

### TriggerAbilityFX

**Package:** `com.hypixel.hytale.builtin.abilities.interaction.TriggerAbilityFXInteraction`

Spawns a particle system and/or plays a 3D sound at the chain's `HIT_LOCATION`, falling back to the
executing entity's position. Codec doc: "Use this instead of Effects in server-simulated chains: their
Effects never reach a client." That covers chains run on a projectile, on an ability entity, or as a
`PerActivationInteraction`. With neither `SystemId` nor `SoundEventId` set it does nothing.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `SystemId` | string | — | Particle system id, validated at load |
| `SoundEventId` | string | — | Sound event, validated at load and required to be **mono** |
| `Scale` | float | `1.0` | Base particle scale |
| `ScaleAttribute` | string | — | Attribute that **multiplies** `Scale` |
| `Color` | color | — | Tint for greyscale (`_GS`) particle textures; an element conversion on the cast overrides it |

A tinted burst, whether from `Color` or from an element, is sent only to players within 75 blocks. From
`Server/Item/Interactions/Abilities/GroundSlam/Ability_GroundSlam_Spike.json`, minus its `Next`:

```json
{
  "Type": "TriggerAbilityFX",
  "SystemId": "Ability_GroundSlam_Spike",
  "SoundEventId": "SFX_Ability_Ground_Slam_Spike_Erupt",
  "Scale": 3,
  "ScaleAttribute": "AoeScale",
  "Color": "#8a5a2c"
}
```

Eight shipped files use the type: six ability files and two cinematic NPC roots,
`Root_NPC_Cinematic_Dragon_Void_Dissolve.json` and `Root_NPC_Cinematic_Shrouded_Figure_Dissolve.json`
in `Server/Item/RootInteractions/NPCs/Cinematic/`.

### GroundedCondition

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.none.GroundedConditionInteraction`

Codec doc: "Fails the chain unless the caster stands on ground (or within Tolerance blocks above it).
Author the fail feedback on Failed. Swimming, climbing and falling all fail." The class sits in the
core `config.none` package, yet `AbilitiesPlugin` registers it, so it shares the plugin's
availability. Unlike the other ability types it runs its check on the client as well.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `Tolerance` | float | `0.0` | Also pass when a solid block lies within this many blocks below the caster's feet; `0` is strict on-ground only. Validated `>= 0` |

Two shipped uses: `Ability_GroundSlam_Cast.json` opens with `"Tolerance": 1` and `"Failed":
"Ability_Cast_Fail"`, and `Template_Glider` uses it with no tolerance.

---

## The Fireball rune, end to end

Every file below ships in 0.7.2. Paths are under `Server/`.

**1. The rune** (`Item/Items/Rune/Ability/Rune_Fireball.json`) is shown under
[CoreItemAbility](#coreitemability): cooldown 2, cost 30 Mana, five keywords, `Cast:
"Root_Ability_Fireball"`.

**2. The root** (`Item/RootInteractions/Abilities/Root_Ability_Fireball.json`):

```json
{
  "Interactions": ["Ability_Fireball_Cast"],
  "RequireNewClick": true,
  "Tags": { "Attack": ["Ranged"] }
}
```

**3. The cast** (`Item/Interactions/Abilities/Fireball/Ability_Fireball_Cast.json`, `Effects` and
the charge-up `Simple` trimmed). It gates on the cost, then forks the cooldown and the spend alongside
the launch:

```json
{
  "Type": "StatsCondition",
  "UseAbilityCost": true,
  "Failed": "Ability_Cast_Fail",
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Interactions": [
          { "Type": "Simple", "RunTime": 0.87 },
          {
            "Type": "LaunchAbilityProjectile",
            "Projectile": "Projectile_Config_Ability_Fireball",
            "Scale": 1.5,
            "ScaleAttribute": "ProjectileSize",
            "SpeedAttribute": "Speed",
            "Lifetime": 0.5
          }
      ] },
      { "Interactions": [ { "Type": "TriggerCooldown", "UseAbilityCooldown": true } ] },
      { "Interactions": [ { "Type": "ChangeStat", "UseAbilityCost": true } ] }
    ]
  }
}
```

`Ability_Cast_Fail` is a `Simple` with `"RunTime": 0.2`. The cost and cooldown keys are documented at
[Ability Costs](interactions-flow.md#ability-costs) and in the `TriggerCooldown` section of
[interactions-flow.md](interactions-flow.md).

**4. The projectile** (`ProjectileConfigs/Abilities/Projectile_Config_Ability_Fireball.json`)
inherits the staff fireball and replaces its chains. `Ability_Split` comes first, so `Rune_Fork` and
`Rune_Ricochet` work on this ability:

```json
{
  "Parent": "Projectile_Config_Fireball",
  "Model": "Ability_Fireball",
  "Interactions": {
    "ProjectileHit": {
      "Interactions": [
        "Ability_Split",
        "Ability_Fireball_Impact",
        "Weapon_Stick_Fire_Projectile_Despawn_Delay",
        "Weapon_Stick_Fire_Projectile_Despawn"
      ]
    },
    "ProjectileMiss": {
      "Interactions": [
        "Ability_Fireball_Impact",
        "Weapon_Stick_Fire_Projectile_Despawn_Delay",
        "Weapon_Stick_Fire_Projectile_Despawn"
      ]
    }
  }
}
```

**5. The impact** (`Item/Interactions/Abilities/Fireball/Ability_Fireball_Impact.json`) plays its
explosion through `TriggerAbilityFX`, since a projectile's chain is server-simulated, and both the
explosion and the hit radius grow with `AoeScale`:

```json
{
  "Type": "TriggerAbilityFX",
  "SystemId": "Explosion_Big",
  "SoundEventId": "SFX_Fireball_Death",
  "ScaleAttribute": "AoeScale",
  "Next": {
    "Type": "Selector",
    "RunTime": 0.05,
    "Selector": { "Id": "AOECircle", "Range": 2.5, "SizeAttribute": "AoeScale" },
    "HitEntity": { "Interactions": ["Ability_Fireball_Hit"] }
  }
}
```

**6. The hit** (`Item/Interactions/Abilities/Fireball/Ability_Fireball_Hit.json`):

```json
{
  "Parent": "DamageEntityParent_Hit_Interrupt",
  "DamageCalculator": { "BaseDamage": { "Fire": 28 } },
  "DamageAttribute": "Damage"
}
```

With `Rune_Damage_Up` and `Rune_Convert_Wind` in the line, the snapshot holds `Damage` 1.5 and the
conversion to `Wind`: the hit deals 42 `Wind` damage in place of 28 `Fire` (before armor), and the
explosion burst is tinted with the `Wind` damage cause's `DamageTextColor`. The audit is satisfied too: the chain uses `LaunchAbilityProjectile`
(`Projectile`), binds `AoeScale` (`Aoe`) and binds `Damage` (`Damage`).

---

## Example: a custom core rune

An unshipped sketch with `MyMod_` ids, reusing the shipped fireball projectile, art and fail
interaction. It shows the minimum a mod adds: a rune item, a root, and a cast chain. Three files in
the mod's asset pack:

`Server/Item/Items/Rune/MyMod_Rune_Firebolt.json`:

```json
{
  "TranslationProperties": { "Name": "server.items.MyMod_Rune_Firebolt.name" },
  "Icon": "Icons/ItemsGenerated/Rune_Fireball.png",
  "Model": "Items/Runes/Rune_Ability.blockymodel",
  "Texture": "Items/Runes/Rune_Textures/Rune_Ability_Fireball.png",
  "Quality": "Rare",
  "MaxStack": 1,
  "Ability": {
    "Slot": "Core",
    "Cooldown": 1,
    "Cost": 15,
    "CostType": "Mana",
    "AbilityKeywords": ["Damage", "Elemental", "Fire", "Projectile", "Aoe"],
    "Cast": "Root_MyMod_Ability_Firebolt"
  }
}
```

`Server/Item/RootInteractions/MyMod/Root_MyMod_Ability_Firebolt.json`:

```json
{
  "Interactions": ["MyMod_Ability_Firebolt_Cast"],
  "RequireNewClick": true
}
```

`Server/Item/Interactions/MyMod/MyMod_Ability_Firebolt_Cast.json`:

```json
{
  "Type": "StatsCondition",
  "UseAbilityCost": true,
  "Failed": "Ability_Cast_Fail",
  "Next": {
    "Type": "Parallel",
    "Interactions": [
      { "Interactions": [
          {
            "Type": "LaunchAbilityProjectile",
            "Projectile": "Projectile_Config_Ability_Fireball",
            "ScaleAttribute": "ProjectileSize",
            "SpeedAttribute": "Speed",
            "Lifetime": 0.5
          }
      ] },
      { "Interactions": [ { "Type": "TriggerCooldown", "UseAbilityCooldown": true } ] },
      { "Interactions": [ { "Type": "ChangeStat", "UseAbilityCost": true } ] }
    ]
  }
}
```

To limit the rune to staves, add `"Weapons": ["Staff"]` to its `Ability` block: the value is a
`Family` tag name, matched against the held weapon. The keyword list copies
`Rune_Fireball`'s, whose promises the reused projectile chain keeps. Add the name to
`Server/Languages/en-US/server.lang` as `items.MyMod_Rune_Firebolt.name`.

---

## Java API

### AbilitiesPlugin

**Package:** `com.hypixel.hytale.builtin.abilities.AbilitiesPlugin`

```java
static AbilitiesPlugin get()
ComponentType<EntityStore, AbilityCharges>         getAbilityChargesComponentType()
ComponentType<EntityStore, AbilityBenchIntro>      getAbilityBenchIntroComponentType()
ComponentType<EntityStore, AbilityEntityRepeat>    getAbilityEntityRepeatComponentType()
ComponentType<EntityStore, AbilityProjectileTrail> getAbilityProjectileTrailComponentType()
ComponentType<EntityStore, PulledByAbility>        getPulledByAbilityComponentType()
ComponentType<EntityStore, AbilityProjectileSplit> getAbilityProjectileSplitComponentType()
```

Of the six components only `AbilityBenchIntro` has a codec and persists. The other five are runtime
state, registered with a supplier that throws, so they are created only by the systems that own them.
Each of the six also exposes a static `getComponentType()`: `AbilityCharges.getComponentType()`,
`AbilityBenchIntro.getComponentType()`, `AbilityEntityRepeat.getComponentType()`,
`AbilityProjectileTrail.getComponentType()`, `PulledByAbility.getComponentType()` and
`AbilityProjectileSplit.getComponentType()`.

### ImpactModifiers

**Package:** `com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers`

Both a component (on ability projectiles and ability entities) and a meta object, under two keys:
`ImpactModifiers.CAST_SNAPSHOT` in an interaction context's meta store, and
`ImpactModifiers.DAMAGE_MODIFIERS` on a `Damage` event, where `DamageEntity` puts it for
`RuneEffectDamageSystem` to apply the on-hit effects.

```java
static ComponentType<EntityStore, ImpactModifiers> getComponentType()
static ImpactModifiers collect(InteractionContext context, Ref<EntityStore> casterRef, ComponentAccessor<EntityStore> accessor)
static void snapshotForCast(InteractionContext context, ComponentAccessor<EntityStore> accessor)
static ImpactModifiers resolve(InteractionContext context, Ref<EntityStore> actingRef, ComponentAccessor<EntityStore> accessor)
float getAttribute(String name, float fallback)
Map<String, Float> getAttributes()
String[] getOnHitEffectIds()
String getElementalCauseId()
```

`ImpactModifiers.collect` returns `null` unless the context is an ability-slot context (held-item
section `-11`) holding a core rune, and also `null` when the line yields no attributes, effects or
element. `ImpactModifiers.resolve` is what a custom interaction should call to read the values the
way the shipped ones do.

### AbilityCastUtil

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.util.AbilityCastUtil`

```java
static final String COST_ATTRIBUTE = "Cost"
static final String COOLDOWN_ATTRIBUTE = "Cooldown"
static CoreItemAbility castAbility(InteractionContext context)            // the casting core rune, or null
static Int2FloatMap resolveCostMap(InteractionContext context, boolean negate)
```

`AbilityCastUtil.castAbility` returns the core rune only in an ability-slot context.
`AbilityCastUtil.resolveCostMap` builds the one-entry stat map that `UseAbilityCost` uses; it returns
`null` for a zero cost, `CostType: None`, an unknown stat, or a caster in Creative.

### AbilityAttributeBinding

**Package:** `com.hypixel.hytale.server.core.modules.interaction.interaction.config.data.AbilityAttributeBinding`

```java
void collectAbilityAttributes(Consumer<String> out)
static void collect(Consumer<String> out, String attribute)   // skips null
```

Implement it on a custom interaction that reads attributes, so the [keyword audit](#abilitykeywordaudit)
counts its bindings toward a keyword's `RequiredAttributes`.

### Reading a player's equipped abilities

A fragment, inside a system or command that holds a `Store<EntityStore>` and the player's `Ref`:

```java
InventoryComponent.AbilitySlots slots =
        store.getComponent(ref, InventoryComponent.AbilitySlots.getComponentType());
if (slots != null) {
    ItemContainer container = slots.getInventory();
    for (short core = 0; core < container.getCapacity(); core += InventoryComponent.ABILITIES_LINE_WIDTH) {
        ItemStack stack = container.getItemStack(core);
        if (stack != null && stack.getItem().getAbility() instanceof CoreItemAbility ability) {
            String castRoot = ability.getCastRootId();     // e.g. "Root_Ability_Fireball"
            float cooldown = ability.getCooldownS();
            // the supports for this line sit in slots core + 1 and core + 2
        }
    }
}
```

To open the bench from code, call `OpenAbilityBenchInteraction.openBench(ref, store)` on the world
thread.

---

## Gotchas & Errors

- **Symptom:** pressing the ability key does nothing, with a core rune equipped → the active hotbar
  item is a non-weapon, or a weapon outside the rune's `Weapons` families. The chain runs from the
  ability slot with no root. Fix: hold a weapon (an item with a `Weapon` block) that the rune accepts.
- **Symptom (0.7.2):** a held item's own `Ability2` / `Ability3` interactions stopped firing → while
  any hotbar item is held, those two inputs run from the ability slots. Only an empty hand with no
  qualifying rune falls back to the item bindings; see
  [Ability slots](interactions-context.md#ability-slots-072). `Ability1` and `Ability4` are
  unaffected.
- **Symptom:** a support rune will not go into a slot → its line's core is empty, the core lacks a
  keyword the support requires (or carries one it excludes), or the same support is already on that
  line. Fix: check the gate against the core's `AbilityKeywords`.
- **Symptom:** a core rune will not move → the same rune is already the core of the other line, or
  its displaced supports have nowhere to go (rune bag, storage and hotbar full).
- **Symptom:** `Rune_Fork` / `Rune_Ricochet` have no effect on a custom ability → the projectile's
  `ProjectileHit` chain lacks `SplitAbilityProjectile`. Fix: put `"Ability_Split"` first in it, as
  `Projectile_Config_Ability_Fireball` does.
- **Symptom:** a support modifier gives an unexpected number → modifiers start from the core's
  declared value, or from `1` when the core omits the attribute. An `Additive` `Fork` of `+2` on a
  core with no `Fork` attribute yields 3 children, and a `RicochetRange` attribute replaces the
  authored range with a value grown from `1`.
- **Symptom:** particles or sounds in a projectile's hit chain never appear → `Effects` in
  server-simulated chains never reach a client. Fix: use `TriggerAbilityFX`.
- **Symptom:** on-hit effects apply twice → `RuneEffects: true` on an `ApplyAbilityEffects` in a chain
  that also deals damage. Damage already applies them.
- **Symptom:** a repeat chain of `SpawnAbilityEntity` fails validation → `Chain` names a plain
  interaction file. Fix: inline `{ "Interactions": ["<id>"] }` or point at a `Root_` asset.
- **Symptom:** the server shuts down during boot logging "Asset validation FAILED", with a reason
  starting "Ability keywords: N contract violation(s)" → a `--validate-assets` run found a broken
  keyword promise. The reason lists each rune and keyword.
- **Symptom:** an element's `OnHitEffect` never applies → no code reads it in 0.7.2. Fix: put the
  effect in a support rune's `OnHitEffects`, or in the ability's own hit chain.
- **Symptom:** a rune with no `CostType` drains mana → the default is `Mana`. Set `"CostType": "None"`
  or leave `Cost` at `0` for a free ability. Players in Creative never pay.
- **Symptom:** two runes share one cooldown → `UseAbilityCooldown` keys the cooldown by the rune's
  `Cast` root id, so runes with the same `Cast` share it.

---

## Related

- [Interactions API](interactions.md) — the type registry and root interactions
- [InteractionContext → Ability slots](interactions-context.md#ability-slots-072) — how `Ability2` / `Ability3` pick the ability slot
- [Ability Costs](interactions-flow.md#ability-costs) — `UseAbilityCost` on `StatsCondition` and `ChangeStat`
- [Ability Attribute Keys](interactions-combat.md#ability-attribute-keys) — attribute keys on `DamageEntity`, `ApplyEffect` and the selectors
- [Projectiles API](projectiles.md) — `ProjectileConfig`, physics and `ImpactModifiers` on launched projectiles
- [Inventory API](inventory.md) — inventory sections, containers and slot filters
- [Item Definitions](items.md) — the item asset the `Ability` key lives on
- [Effects & Stats](effects-stats.md) — `EntityEffect` assets, `StaticModifier`, and the `Mana` / `Stamina` / `Health` stats
