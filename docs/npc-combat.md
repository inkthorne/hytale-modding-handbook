---
title: "NPC Combat"
description: "How Hytale NPCs fight — the two melee paths (instruction-driven attacks without a Combat Action Evaluator, and CAE-driven combat), and the CAE's action selection, ranges and cooldowns."
seo:
  type: TechArticle
---

# NPC Combat

**Doc type:** Java API + JSON asset format · **Assets:** `Server/NPC` · **Verified against 0.6.3**

Split out of [npc-roles.md](npc-roles.md) at the 2026-09-04 seam. Hytale has **two** NPC melee paths and the choice matters; this page covers both, and the Combat Action Evaluator that drives the second. Role definitions, sensors and instructions stay in [npc-roles.md](npc-roles.md).

## Melee attacks without a CAE

Hytale has **two** NPC melee paths, and the choice matters:

- The **[CAE](#combat-action-evaluator-cae)** path (`_CombatConfig: CAE_…`, with `Ability` assets) — for intelligent, multi-ability combatants like Goblins.
- A far lighter **interaction-var chain** that vanilla animals use (livestock, undead chicken) — no CAE, no `Ability` assets, just a single scripted swing on an otherwise non-combat creature. This is what the rest of this section documents.

To give a creature the lightweight melee:

- Set a role field **`"Attack": "<RootInteraction>"`** (e.g. `Root_NPC_Attack_Melee`) — also settable inline on the `Attack` action.
- Run a **[`Type: "Attack"` action](npc-roles.md#the-attack-action)** inside the role's `Instructions` (typically inside an [`ActionsBlocking`](npc-roles.md#actionlist-blocking-semantics-multi-tick-sequences) windup sequence) to perform the swing.
- Customize damage / animation / hit-geometry purely by overriding **named interaction vars** under the role's **`InteractionVars`** — spelled **`_InteractionVars`** inside a `Variant`'s `Modify` (next subsection) — no CAE.

Neutral animals ship with this machinery **off by default**: `Template_Animal_Neutral` exposes `Attack` (default `""`) and `AttackWhenStartled` (default `false`) and has a dormant "startled" retaliation in its `Flee` state. Set `AttackWhenStartled: true` plus an `Attack` interaction to enable it. The cleanest "give a creature a bite" exemplar is `Server/NPC/Roles/Undead/Chicken_Undead.json` (a `Template_Predator` variant that sets `"Attack": "Root_NPC_Attack_Melee"` and overrides the start anim + damage). The instruction pattern itself lives in `Template_Predator.json`: a target-in-`AttackDistance` + line-of-sight gate, `HeadMotion: Aim`, `ActionsBlocking`, then `Timeout (pre-delay) → Attack → Timeout (post-delay)`.

### The interaction-var chain

`Attack: "Root_NPC_Attack_Melee"` walks a chain of interactions (under `Server/Item/…/NPCs/`), each of which `Replace`s a **named var** with a default you can override at the role level:

| Interaction | Sets var | Default | Overriding it customizes |
|---|---|---|---|
| `RootInteractions/NPCs/Root_NPC_Attack_Melee` | `Melee_Start` | `NPC_Attack_Melee_Simple` | the whole start (anim set + timing) |
| `Interactions/NPCs/NPC_Attack_Melee_Simple` | `Melee_Selector` | `NPC_Attack_Selector_Left` | the **hit geometry** (see below) |
| `Interactions/NPCs/NPC_Attack_Selector_Left` (`HitEntity`) | `Melee_Damage` | `NPC_Attack_Melee_Damage` | **damage + DamageEffects** |
| `Interactions/NPCs/NPC_Attack_Melee_Damage` | — (`Parent: DamageEntityParent`) | — | base: `DamageCalculator` (Physical 5) + `DamageEffects` (knockback, `WorldSoundEventId`, `WorldParticles`) |

A role overrides any link by declaring the var in its interaction-vars block. The selector's `HitEntity` does `{"Type":"Replace","Var":"Melee_Damage","DefaultValue":{…}}`, so a role-level `Melee_Damage` wins (vanilla `Chicken_Undead` notes in its override: *"When NPC overrides the InteractionVars, this info in Template not applicable anymore"*).

> **⚠️ The key name differs by role type.** `BuilderRole` reads **`InteractionVars`** at a role's top level — that is what the templates use (`Template_Animal_Neutral`, `Template_Predator`, `Template_Livestock`, `Template_Intelligent`, …), and it is what a `Generic` role uses. Inside a **`Variant`'s `Modify`** the same block is spelled **`_InteractionVars`** with the leading underscore, the same convention as `_CombatConfig`; every shipped variant that customises its bite (`Cow.json`, `Chicken_Undead.json`, ~94 files) uses `_InteractionVars`. Using the wrong one for the role type silently does nothing, or drops the role.

Example — lighten the bite to 2 physical, keep the default start/selector (shown as a `Variant` would write it):

```json
"_InteractionVars": {
  "Melee_Damage": {
    "Interactions": [
      { "Parent": "NPC_Attack_Melee_Damage",
        "DamageCalculator": { "Type": "Absolute", "BaseDamage": { "Physical": 2 }, "RandomPercentageModifier": 0.1 } }
    ]
  }
}
```

> This `Replace` / `Var` / `DefaultValue` override-by-name mechanism is general to interactions — see [Interactions](interactions.md). The damage interaction itself is documented in [Combat](combat.md).

### Melee hits are directional swept arcs — NPCs can miss

`NPC_Attack_Selector_Left.json` is a `Type: Selector` whose geometry is a **humanoid sword-swing arc**:

```json
"Selector": {
  "Id": "Horizontal", "Direction": "ToLeft", "TestLineOfSight": true,
  "ExtendTop": 0.5, "ExtendBottom": 0.5, "StartDistance": 0.1, "EndDistance": 3.5,
  "Length": 30, "RollOffset": 0, "YawStartOffset": -15
}
```

It's a narrow (~30°), side-offset wedge swept over the interaction's `RunTime` (0.25 s) **in front of the NPC's body**, reaching 0.1–3.5 blocks, ±0.5 vertical, requiring line of sight. Because the arc is **body-relative**, a custom NPC **whiffs if its body isn't facing the target at strike time** — and `HeadMotion: Aim`/`Watch` alone is *not* enough: a head motion only blends the *body* when the active motion set no yaw and the head exceeds the camera yaw limit (see [Facing](npc-roles.md#facing-orientation-is-emergent-from-the-active-motion)), so over a yaw-setting attack motion it turns the head only. It also misses if the target leaves `EndDistance`, strafes out of the arc mid-sweep, or breaks line of sight.

So "why does my NPC sometimes not connect?" has a real mechanical answer: melee is a swept directional hitbox, not a homing hit. Two fixes:

- **Rotate the body onto the target before the swing.** Add a `Seek` body-motion + a longer windup (`Timeout`) so the NPC turns onto the target *before* `Attack` fires. (Coming out of a circling/orbit motion an NPC faces its *tangential* heading ~90° off the target; turning ~90° took ≈0.6 s of windup in testing — 0.35 s under-rotated and missed.)
- **Widen the arc.** Override `Melee_Selector` with a larger `Length`, a forward-centered `YawStartOffset`, and bigger `ExtendTop`/`ExtendBottom`.

### Serializing a flock swarm — native take-turns can't hard-gate it

The flock "take-turns" pattern (`Component_Instruction_Combat_Flock_Take_Turns`) passes an attack "baton" via flock beacons (`Message_Attack`) carrying a `Retreat` flag and a turn timer. But it only *influences positioning* — it does **not** hard-gate the attack:

- `Template_Predator`'s combat-attack instruction is gated only on "target within `AttackDistance` + line-of-sight." It does **not** check the take-turns `Retreat` flag.
- So `Component_Instruction_Combat_Flock_Take_Turns` only *moves* non-attackers out toward the combat-turn distance; any member still in range still swings. Against a stationary, surrounded player you therefore get **multiple simultaneous attackers** regardless.
- `CombatTurnAttackWeight` is a **percent chance to attack per turn** (per its own parameter description), **not** a count of attackers — despite some field descriptions miscalling it a count.

To truly serialize a swarm down to one attacker, gate the **attack decision itself** in a custom `Type: "Generic"` role (a `Variant`'s `Modify` cannot carry `Instructions` — see the [Variants gotcha](npc-roles.md#variants)) on a shared signal. The cleanest signal is a [custom token sensor](npc-roles.md#registering-a-custom-sensor) that is true for exactly one flock member at a time: gate the attack branch via `And[Player, <token>]`, and let non-holders fall through to a `MaintainDistance` hold branch.

Practical combat-role lessons (all confirmed in-game):

- **Gate the attack on actual bite/attack range, not just on "it's my turn."** Otherwise the turn-holder swings at air while still out of range and wastes its turn — add an inner short-range `Player` gate so it approaches first.
- **Hold position through the swing before transitioning** (e.g. to a retreat). A [`Type: "Attack"` action](npc-roles.md#the-attack-action) only *starts* the interaction chain; damage lands partway through it. Use an [`ActionsBlocking`](npc-roles.md#actionlist-blocking-semantics-multi-tick-sequences) sequence like `[Attack, Timeout ~0.45s, <transition>]` to stay in range and facing until the hit lands — otherwise the NPC moves away mid-swing and whiffs.
- **For one action per turn, prefer a per-NPC [`Flag`](npc-roles.md#flags-setflag--flag)** (`SetFlag` / `Flag`) over relying on an attack-pause cooldown, especially when you also want to change behavior *after* the action.

---

## Combat Action Evaluator (CAE)

The CAE system provides intelligent combat decision-making. Found in `Server/NPC/Balancing/`. A role references its CAE through the `_CombatConfig` field (see the Goblin Scrapper variant above). For the lighter, non-CAE animal melee path, see [Melee attacks without a CAE](#melee-attacks-without-a-cae).

### CAE Structure

A CAE file has `"Type": "CombatActionEvaluator"` at the top and wraps its evaluation logic in a nested `CombatActionEvaluator` object. That object holds:

- `RunConditions`: conditions that gate whether the evaluator runs at all.
- `MinRunUtility` / `MinActionUtility`: utility thresholds.
- `AvailableActions`: an object keyed by action name. Each action has a `Type` (commonly `Ability`), a `Target`, an `Ability` reference, an `AttackDistanceRange`, a `PostExecuteDistanceRange` (the distance to hold *after* the action), optional `Description`/`InteractionVars`/`ChargeFor`/`WeaponSlot`/`SubState`, and a `Conditions` array.
- `ActionSets`: an object keyed by set name (not an array). Each set defines `BasicAttacks` (`Attacks`, `MaxRange`, `Timeout`, `CooldownRange`, optional `Randomise` and `InteractionVars`) and an `Actions` list of available action names.

```json
{
    "Type": "CombatActionEvaluator",
    "TargetMemoryDuration": 5,
    "CombatActionEvaluator": {
        "RunConditions": [
            {
                "Type": "TimeSinceLastUsed",
                "Curve": { "ResponseCurve": "Linear", "XRange": [ 0, 5 ] }
            },
            { "Type": "Randomiser", "MinValue": 0.9, "MaxValue": 1 }
        ],
        "MinRunUtility": 0.5,
        "MinActionUtility": 0.01,
        "AvailableActions": {
            "Melee": {
                "Type": "Ability",
                "WeaponSlot": 0,
                "SubState": "Default",
                "Ability": "Goblin_Scrapper_Attack",
                "Target": "Hostile",
                "AttackDistanceRange": [ 2.5, 2.5 ],
                "Conditions": [
                    {
                        "Type": "TimeSinceLastUsed",
                        "Curve": { "ResponseCurve": "Linear", "XRange": [ 0, 1 ] }
                    }
                ]
            },
            "Ranged": {
                "Type": "Ability",
                "WeaponSlot": 0,
                "SubState": "Ranged",
                "Ability": "Goblin_Scrapper_Rubble_Throw",
                "Target": "Hostile",
                "AttackDistanceRange": [ 15, 15 ],
                "Conditions": [
                    {
                        "Type": "TargetDistance",
                        "Curve": { "ResponseCurve": "SimpleLogistic", "XRange": [ 0, 15 ] }
                    }
                ]
            }
        },
        "ActionSets": {
            "Default": {
                "BasicAttacks": {
                    "Attacks": [ "Goblin_Scrapper_Attack" ],
                    "MaxRange": 2.5,
                    "Timeout": 0.5,
                    "CooldownRange": [ 0.001, 0.001 ]
                },
                "Actions": [ "SwingDown", "Ranged" ]
            }
        }
    }
}
```

### Response Curves

A condition maps its raw input to a 0–1 utility through a `Curve`. **The `Curve` field has two different shapes depending on the condition's base class** — getting this wrong is the usual cause of a CAE failing to load:

| Base class | Conditions | `Curve` shape |
|---|---|---|
| `ScaledCurveCondition` | `TimeSinceLastUsed`, `TargetDistance`, `NearbyCount`, `TimeOfDay`, `OwnStatAbsolute`, `TargetStatAbsolute`, `RecentSustainedDamage`, `TotalSustainedDamage`, `KnownTargetCount` | an **object** — the input is un-normalised, so the curve carries the scaling. |
| `CurveCondition` | `OwnStatPercent`, `TargetStatPercent` | a **plain string** naming a response-curve asset — the input is already 0–1. |
| `SimpleCondition` / `Condition` | `HasTarget`, `IsInState`, `LineOfSight`, `TargetMovementState`, `SelfHasEffect`, `TargetHasEffect`, `Randomiser` | no `Curve` at all. |

```json
"Conditions": [
    { "Type": "TargetDistance",  "Curve": { "ResponseCurve": "SimpleLogistic", "XRange": [ 0, 15 ] } },
    { "Type": "OwnStatPercent",  "Stat": "Health", "Curve": "ReverseLinear" }
]
```

The object form is a `ScaledResponseCurve`, whose own `Type` selects between two implementations (the default may be omitted):

| `Type` | Class | Keys |
|--------|-------|------|
| *(omitted)* / `Default` | `ScaledXResponseCurve` | `ResponseCurve` (asset id) + `XRange` `[min, max]` — rescales x into the named curve. |
| `Switch` | `ScaledSwitchResponseCurve` | `SwitchPoint`, `InitialState` (y before it), `FinalState` (y at/after it) — a step function. Used by 22 shipped CAEs, not just tests. |

`ResponseCurve` values are **assets** under `Server/ResponseCurves/`, so the set is extensible. Each asset picks one of three families — `Exponential` (`Slope`, `Exponent`, `HorizontalShift`, `VerticalShift`), `Logistic` (`Ceiling`, `RateOfChange`, `HorizontalShift`, `VerticalShift`) or `SineWave` (`Amplitude`, `Frequency`, `HorizontalShift`, `VerticalShift`). Those that ship:

| Response Curve | Family | Shape |
|----------------|--------|-------|
| `Linear` | Exponential | `y = x` (slope 1, exponent 1) |
| `ReverseLinear` | Exponential | `y = 1 − x` (slope −1, x-shift 1) |
| `Quadratic` / `TestExponential` | Exponential | `y = x²` — slow start, fast finish |
| `InverseExponential` | Exponential | exponent `0.28` — a *root* curve: rises fast, then flattens (**not** a falloff) |
| `ConstantMidpoint` | Exponential | slope `0`, y-shift `0.5` — constant `0.5` |
| `SimpleLogistic` / `TestLogistic` | Logistic | ascending S-curve centred at `0.5` |
| `SimpleDescendingLogistic` | Logistic | descending S-curve centred at `0.5` |
| `LateRise` | Logistic | stays near 0, rises sharply at `0.8` |
| `LateFalloff` | Logistic | stays near 1, drops sharply at `0.8` |
| `SimpleParabola` | SineWave | half sine over the range — peaks mid-range, 0 at both ends |

### Condition Types

Conditions (in both `RunConditions` and per-action `Conditions`) use a `Type`. Common types:

| Condition Type | Description |
|----------------|-------------|
| `TimeSinceLastUsed` | Time elapsed since the action last ran |
| `TargetDistance` | Distance to the current target |
| `Randomiser` | Random value between `MinValue` and `MaxValue` |
| `OwnStatPercent` / `OwnStatAbsolute` | NPC's own stat as a percentage / absolute value |
| `TargetStatPercent` / `TargetStatAbsolute` | Target's stat as a percentage / absolute value |
| `RecentSustainedDamage` / `TotalSustainedDamage` | Damage taken recently / in total |
| `NearbyCount` / `KnownTargetCount` | Counts of nearby / remembered entities |
| `HasTarget` | Whether a target exists at all |
| `IsInState` | Whether the NPC is in a given state |
| `LineOfSight` | Whether the target is in line of sight |
| `TimeOfDay` | Current world time |
| `TargetMovementState` | Target's movement state |
| `SelfHasEffect` / `TargetHasEffect` | Entity-effect presence on self / target |

The first three groups come from `Condition.CODEC` in `server.npc.decisionmaker`; `RecentSustainedDamage`, `TotalSustainedDamage` and `KnownTargetCount` are registered by `NPCCombatActionEvaluatorPlugin` and therefore only exist where the CAE plugin is loaded.
