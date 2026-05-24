---
title: "Documentation Index"
description: "Index of the Hytale Modding Handbook — find the reference page for commands, items, world generation, UI, NPCs, interactions, and the rest of the API."
seo:
  type: TechArticle
---

# Documentation Index

**Doc type:** Index

Complete reference for finding the right documentation file. For a beginner-friendly introduction, see [Overview](00-overview.md).

## Quick Reference Table

| File | Description |
|------|-------------|
| [02-structure.md](02-structure.md) | Pack vs plugin directory structure, Server/ vs Common/ directories, and manifest configuration. |
| [interactions.md](interactions.md) | Comprehensive reference for entity interactions including combo systems, combat effects, control flow, and world manipulation. |
| [interactions-operations.md](interactions-operations.md) | Low-level Operation system that powers interaction execution, including OperationsBuilder and label-based flow control. |
| [interactions-context.md](interactions-context.md) | InteractionContext API for accessing entities, items, meta store, and InteractionVars during interaction execution. |
| [items.md](items.md) | Item definitions including weapons, consumables, and equipment with inheritance system and InteractionVars customization. |
| [plugin-lifecycle.md](plugin-lifecycle.md) | Documents the complete plugin lifecycle from initialization through shutdown, including setup phases, event registration, and logging. |
| [commands.md](commands.md) | Details the command system for creating player commands with arguments, permissions, subcommands, and built-in argument types. |
| [entities.md](entities.md) | Covers the entity system including Player and Entity classes, entity stats, velocity management, and interaction chains. |
| [player.md](player.md) | Describes player-specific functionality including messaging, permissions, connect/disconnect events, and interaction events. |
| [world.md](world.md) | Comprehensive world management API covering the World class, chunks, chunk tracking, configuration, and lifecycle events. |
| [universe-saves.md](universe-saves.md) | Save / universe format for dedicated servers: per-world config.json, binding a world to a WorldStructure, the Defaults.World spawn selection, IsPvpEnabled, and the CreativeHub crossroads. |
| [events.md](events.md) | Core event system documentation covering registration methods, event priorities, keyed vs non-keyed events, and ECS patterns. |
| [components.md](components.md) | Entity Component System (ECS) documentation including Store, Ref, queries, CommandBuffer, and ticking systems. |
| [permissions.md](permissions.md) | Covers permission checking for players and commands, plus permission-related events like group changes. |
| [inventory.md](inventory.md) | Complete inventory management API including item stacks, containers, transactions, crafting recipes, and related events. |
| [tasks.md](tasks.md) | Documents the task registration system for tracking async futures and scheduled tasks throughout plugin lifecycle. |
| [ui.md](ui.md) | UI system covering pages, windows, HUD, DSL syntax, elements, styling, and Java API. |
| [blocks.md](blocks.md) | Covers the block system including block states, BlockType properties, block events (place/break/use/damage), and world access. |
| [assets.md](assets.md) | Asset registry system for custom assets, asset stores, built-in asset access, and asset lifecycle events. |
| [codecs.md](codecs.md) | BSON-based serialization system using codecs for data persistence and configuration loading, including BuilderCodec patterns. |
| [networking.md](networking.md) | Network serialization types including NetworkSerializable interface, Direction rotation class, and sync modes. |
| [prefabs.md](prefabs.md) | Prefab system for placing pre-defined block/entity selections including transformations, placement, and prefab events. |
| [math.md](math.md) | Comprehensive math library with vectors (Vector3d/f/i/l), matrices, transforms, Box AABB, and utility methods. |
| [projectiles.md](projectiles.md) | Projectile spawning and management including ProjectileConfig assets, physics simulation, and projectile components. |
| [collision.md](collision.md) | Collision detection and querying system for block and character collisions, results, and material-based filtering. |
| [fluids.md](fluids.md) | Fluid asset type documentation for water, lava, and other fluids with damage and interaction properties. |
| [combat.md](combat.md) | Combat system covering damage events, damage causes, knockback mechanics, blocking/wielding, and kill feed customization. |
| [npc.md](npc.md) | NPC loading events and metadata including BuilderInfo for loaded NPCs and sensor event systems for AI. |
| [npc-roles.md](npc-roles.md) | NPC role asset definitions including templates, variants, behaviors, attitudes, and spawning configurations. |
| [drops.md](drops.md) | Drop/loot table system for blocks, NPCs, containers, and prefabs with weighted selection and modular composition. |
| [adventure.md](adventure.md) | Adventure gameplay features including instance discovery, zone discovery, treasure chest opening, and world map tracking. |
| [asset-editor.md](asset-editor.md) | Asset editor events for button activation, asset creation, client disconnects, and autocomplete/dataset requests. |
| [i18n.md](i18n.md) | Localization system with GenerateDefaultLanguageEvent for registering plugin translations during server startup. |
| [singleplayer.md](singleplayer.md) | Singleplayer-specific functionality with SingleplayerRequestAccessEvent for handling local server access requests. |
| [audio.md](audio.md) | Audio system documentation covering sound events, audio categories, ambience, reverb, EQ, and integration with other systems. |
| [worldgen.md](worldgen.md) | World generation system overview including zones, biomes, terrain layers, caves, and structure placement. |
| [blockyanim-format.md](blockyanim-format.md) | Block animation (.blockyanim) file format for animating block states like doors, chests, and lights. |

## By Documentation Type

Docs are tagged with a `**Doc type:**` line. This groups them by what they document (and how each is verified — see `maintenance/scripts/verify-docs.sh`).

### Java API
_Documents Java classes/methods — verify with `javap` against `HytaleServer.jar`._

[Adventure API](adventure.md)  [Asset Editor Events API](asset-editor.md)  [Assets API](assets.md)  [Codecs API](codecs.md)  [Collision API](collision.md)  [Commands API](commands.md)  [Components (ECS) API](components.md)  [Entities API](entities.md)  [Events API](events.md)  [Fluids API](fluids.md)  [InteractionContext](interactions-context.md)  [Inventory API](inventory.md)  [Localization (i18n) API](i18n.md)  [Math / Vector API](math.md)  [NPC API](npc.md)  [Networking API](networking.md)  [Operation System](interactions-operations.md)  [Permissions API](permissions.md)  [Player API](player.md)  [Plugin Lifecycle API](plugin-lifecycle.md)  [Projectiles API](projectiles.md)  [Singleplayer API](singleplayer.md)  [Tasks API](tasks.md)  [UI Java API](ui-api.md)  [World API](world.md)

### JSON asset format
_Documents on-disk JSON asset file formats — verify against the extracted `Assets.zip`._

[Audio System](audio.md)  [Biome System](worldgen-biomes.md)  [Block Animation Format (.blockyanim)](blockyanim-format.md)  [Block Items](items-blocks.md)  [Block Model Format (.blockymodel)](blockymodel-format.md)  [Caves](worldgen-caves.md)  [Combat & Effects Interactions](interactions-combat.md)  [Combo System Interactions](interactions-combo.md)  [Consumable Items](items-consumables.md)  [Control Flow Interactions](interactions-flow.md)  [Drop System](drops.md)  [Effects & Stats Reference](effects-stats.md)  [Entity & World Interactions](interactions-world.md)  [Item Definitions](items.md)  [NPC Roles](npc-roles.md)  [Prefab Categories](prefabs-categories.md)  [Props & Structure Placement](worldgen-prefabs.md)  [Terrain Density Graphs](worldgen-terrain.md)  [Tool Items](items-tools.md)  [Weapon Items](items-weapons.md)  [Universes & Save Format](universe-saves.md)  [World Generation](worldgen.md)  [World Structures (Zones)](worldgen-zones.md)

### UI DSL
_Documents the `.ui` curly-brace DSL — verify against real `.ui` files._

[UI Elements Reference](ui-elements.md)  [UI Styling & Layout](ui-styling.md)  [UI Templates, Variables & Localization](ui-templates.md)

### Java API + JSON asset format
_Covers both a Java API and a JSON asset format for the same topic._

[Block Definitions](blocks.md)  [Combat API](combat.md)  [Crafting System](items-crafting.md)  [Interactions API](interactions.md)  [Prefabs API](prefabs.md)

### Guides & Overviews

[Getting Started with Hytale Modding](00-overview.md)  [Pack vs Plugin Directory Structure](02-structure.md)  [UI System](ui.md)

## Asset Type Index

JSON asset types used in Hytale's data-driven systems.

**Interactions - Combo Systems**
[ChainingInteraction](interactions-combo.md#chaininginteraction), [FirstClickInteraction](interactions-combo.md#firstclickinteraction), [ChargingInteraction](interactions-combo.md#charginginteraction), [ChainFlagInteraction](interactions-combo.md#chainflaginteraction), [CancelChainInteraction](interactions-combo.md#cancelchaininteraction)

**Interactions - Combat & Effects**
[SimpleInteraction](interactions-combat.md#simpleinteraction), [Selector](interactions-combat.md#selector), [DamageEntity](interactions-combat.md#damageentity), [ApplyForce](interactions-combat.md#applyforce), [ApplyEffect](interactions-combat.md#applyeffect), [ClearEntityEffect](interactions-combat.md#clearentityeffect), [ChangeStat](interactions-combat.md#changestat), [InterruptInteraction](interactions-combat.md#interruptinteraction)

**Interactions - Control Flow**
[Serial](interactions-flow.md#serial), [Parallel](interactions-flow.md#parallel), [Condition](interactions-flow.md#condition), [StatsCondition](interactions-flow.md#statscondition), [EffectCondition](interactions-flow.md#effectcondition), [BlockCondition](interactions-flow.md#blockcondition), [CooldownCondition](interactions-flow.md#cooldowncondition), [MovementCondition](interactions-flow.md#movementcondition), [PlacementCountCondition](interactions-flow.md#placementcountcondition), [Repeat](interactions-flow.md#repeat), [Replace](interactions-flow.md#replace)

**Interactions - Target Selectors**
[AOECircle](interactions-combat.md#aoecircle-area-of-effect), [Raycast](interactions-combat.md#raycast-straight-line), [Stab](interactions-combat.md#stab-thrust-attacks), [Horizontal](interactions-combat.md#horizontal-sweeping-attacks)

**Interactions - Entity & World**
[SpawnPrefab](interactions-world.md#spawnprefab), [RemoveEntity](interactions-world.md#removeentity), [LaunchProjectile](interactions-world.md#launchprojectile), [SendMessage](interactions-world.md#sendmessage), [OpenPage](interactions-world.md#ui-interactions), [OpenCustomUI](interactions-world.md#ui-interactions), [EquipItem](interactions-world.md#inventory-interactions), [ModifyInventory](interactions-world.md#inventory-interactions), [BreakBlock](interactions-world.md#block-interactions), [PlaceBlock](interactions-world.md#block-interactions), [ChangeState](interactions-world.md#changestate), [LaunchPadInteraction](interactions-world.md#launchpadinteraction), [WieldingInteraction](interactions-world.md#wieldinginteraction)

**Items - Weapon Templates**
[Template_Weapon_Sword](items-weapons.md#template_weapon_sword), [Template_Weapon_Daggers](items-weapons.md#template_weapon_daggers), [Template_Weapon_Shield](items-weapons.md#template_weapon_shield), [Template_Weapon_Battleaxe](items-weapons.md#template_weapon_battleaxe), [Template_Weapon_Shortbow](items-weapons.md#template_weapon_shortbow), [Template_Weapon_Mace](items-weapons.md#template_weapon_mace), [Template_Weapon_Crossbow](items-weapons.md#template_weapon_crossbow)

**Items - Crafting System**
[Bench_WorkBench](items-crafting.md#bench_workbench), [Bench_Weapon](items-crafting.md#bench_weapon), [Bench_Armour](items-crafting.md#bench_armour), [Bench_Alchemy](items-crafting.md#bench_alchemy), [Bench_Furnace](items-crafting.md#bench_furnace), [Bench_Campfire](items-crafting.md#bench_campfire), [Bench_Salvage](items-crafting.md#bench_salvage), [Bench_Tannery](items-crafting.md#bench_tannery), [Bench_Armory](items-crafting.md#bench_armory)

**Audio**
[SoundEvents](audio.md#soundevents), [AudioCategories](audio.md#audiocategories), [AmbienceFX](audio.md#ambiencefx), [EQ](audio.md#eq-equalizer), [Reverb](audio.md#reverb), [ItemSounds](audio.md#itemsounds), [SoundSets](audio.md#soundsets)

**World Generation - Zones & Biomes**
[Zone](worldgen-zones.md#top-level-structure), [Biome Assignment](worldgen-zones.md#biome-assignment-noiserange), [Density](worldgen-zones.md#density), [SpawnPositions](worldgen-zones.md#spawnpositions), [Biome](worldgen-biomes.md#top-level-structure), [Terrain](worldgen-biomes.md#terrain), [MaterialProvider](worldgen-biomes.md#materialprovider)

**World Generation - Biome Providers**
[MaterialProvider](worldgen-biomes.md#materialprovider), [Props](worldgen-biomes.md#props), [EnvironmentProvider](worldgen-biomes.md#environmentprovider), [TintProvider](worldgen-biomes.md#tintprovider)

**World Generation - Terrain**
[DAOTerrain node](worldgen-terrain.md#the-daoterrain-node), [Density node families](worldgen-terrain.md#density-node-families), [Noise nodes](worldgen-terrain.md#noise-nodes), [BaseHeight](worldgen-terrain.md#baseheight), [MaterialProvider](worldgen-terrain.md#materialprovider)

**World Generation - Caves**
[How carving works](worldgen-caves.md#how-carving-works), [Anatomy of a cave field](worldgen-caves.md#anatomy-of-a-cave-field), [Building blocks](worldgen-caves.md#building-blocks), [Volcanic example](worldgen-caves.md#volcanic-example)

**World Generation - Prefabs**
[Biome Props array](worldgen-prefabs.md#biome-props-array), [Assignment node types](worldgen-prefabs.md#assignment-node-types), [Prop types](worldgen-prefabs.md#prop-types), [Positions & PropDistributions](worldgen-prefabs.md#positions--propdistributions)

---

## Java Class Index

**Core Plugin**
[JavaPlugin](plugin-lifecycle.md), [PluginBase](plugin-lifecycle.md), [BootEvent](plugin-lifecycle.md), [ShutdownEvent](plugin-lifecycle.md), [PrepareUniverseEvent](plugin-lifecycle.md), [PluginSetupEvent](plugin-lifecycle.md), [PluginState](plugin-lifecycle.md), [PluginIdentifier](plugin-lifecycle.md), [PluginManifest](plugin-lifecycle.md), [HytaleLogger](plugin-lifecycle.md)

**Commands**
[AbstractPlayerCommand](commands.md), [AbstractWorldCommand](commands.md), [AbstractTargetPlayerCommand](commands.md), [CommandContext](commands.md), [CommandSender](commands.md), [CommandOwner](commands.md), [CommandRegistration](commands.md), [ArgumentType](commands.md), [SingleArgumentType](commands.md), [ArgTypes](commands.md)

**Entities**
[PlayerRef](entities.md), [Player](entities.md), [Velocity](entities.md), [EntityStatMap](entities.md), [StatModifiersManager](entities.md), [EntityEvent](entities.md), [EntityRemoveEvent](entities.md), [InteractionManager](entities.md)

**Player Events & Messaging**
[PlayerConnectEvent](player.md), [PlayerDisconnectEvent](player.md), [PlayerInteractEvent](player.md), [InteractionType](player.md), [Message](player.md), [FormattedMessage](player.md), [GameMode](player.md), [ChangeGameModeEvent](player.md), [HiddenPlayersManager](player.md)

**World & Chunks**
[World](world.md), [WorldChunk](world.md), [ChunkTracker](world.md), [ChunkVisibility](world.md), [ChunkFlag](world.md), [WorldEvent](world.md), [AddWorldEvent](world.md), [ChunkEvent](world.md), [ChunkSaveEvent](world.md), [ChunkPreLoadProcessEvent](world.md), [MoonPhaseChangeEvent](world.md), [GameplayConfig](world.md), [WorldConfig](world.md), [DeathConfig](world.md), [ClientFeature](world.md)

**Event System**
[EventRegistry](events.md), [EventRegistration](events.md), [EventPriority](events.md), [EntityEventSystem](events.md), [IBaseEvent](events.md), [IEvent](events.md), [IAsyncEvent](events.md), [ICancellable](events.md), [EcsEvent](events.md), [CancellableEcsEvent](events.md), [ICancellableEcsEvent](events.md)

**ECS**
[Store](components.md), [Ref](components.md), [Component](components.md), [Query](components.md), [CommandBuffer](components.md), [EntityStore](components.md), [ChunkStore](components.md), [ComponentRegistry](components.md), [TransformComponent](components.md), [Holder](components.md), [Archetype](components.md), [EntityTickingSystem](components.md)

**Permissions**
[PermissionHolder](permissions.md), [PlayerGroupEvent](permissions.md), [PlayerPermissionChangeEvent](permissions.md)

**Inventory & Crafting**
[Inventory](inventory.md), [ItemStack](inventory.md), [Item](inventory.md), [ItemContainer](inventory.md), [CombinedItemContainer](inventory.md), [SmartMoveType](inventory.md), [SortType](inventory.md), [FilterType](inventory.md), [FilterActionType](inventory.md), [SlotFilter](inventory.md), [ActionType](inventory.md), [ItemStackTransaction](inventory.md), [CraftingRecipe](inventory.md), [MaterialQuantity](inventory.md), [ResourceQuantity](inventory.md), [BenchRequirement](inventory.md), [BenchType](inventory.md), [DropItemEvent](inventory.md), [SwitchActiveSlotEvent](inventory.md), [InteractivelyPickupItemEvent](inventory.md), [InventoryChangeEvent](inventory.md), [CraftRecipeEvent](inventory.md)

**Tasks**
[TaskRegistry](tasks.md), [TaskRegistration](tasks.md)

**UI**
[UICommandBuilder](ui-api.md), [UIEventBuilder](ui-api.md), [WindowManager](ui-api.md), [PageManager](ui-api.md), [HudManager](ui-api.md), [HotbarManager](ui-api.md), [Window](ui-api.md), [WindowType](ui-api.md), [OpenWindow](ui-api.md), [Page](ui-api.md), [CustomUIPage](ui-api.md), [HudComponent](ui-api.md), [CustomUIEventBindingType](ui-api.md)

**Blocks**
[BlockType](blocks.md), [BlockMaterial](blocks.md), [Rotation](blocks.md), [RotationTuple](blocks.md), [PlaceBlockEvent](blocks.md), [BreakBlockEvent](blocks.md), [DamageBlockEvent](blocks.md), [UseBlockEvent](blocks.md)

**Assets**
[AssetRegistry](assets.md), [Model](assets.md), [ModelAsset](assets.md), [AssetPackRegisterEvent](assets.md), [AssetPackUnregisterEvent](assets.md), [LoadAssetEvent](assets.md), [CommonAssetMonitorEvent](assets.md), [SendCommonAssetsEvent](assets.md), [PathEvent](assets.md)

**Interactions**
[Interaction](interactions.md), [SimpleInteraction](interactions.md), [SimpleInstantInteraction](interactions.md), [Operation](interactions-operations.md), [OperationsBuilder](interactions-operations.md), [InteractionContext](interactions-context.md), [CooldownHandler](interactions.md#cooldown-system), [InteractionRules](interactions.md#interactionrules)

**Networking**
[NetworkSerializable](networking.md), [Direction](networking.md), [WaitForDataFrom](networking.md)

**Prefabs**
[PrefabStore](prefabs.md), [BlockSelection](prefabs.md), [PrefabRotation](prefabs.md), [PrefabEntry](prefabs.md), [PrefabWeights](prefabs.md), [PrefabPasteEvent](prefabs.md), [PrefabPlaceEntityEvent](prefabs.md)

**Math**
[Vector3d](math.md), [Vector3f](math.md), [Vector3i](math.md), [Vector3l](math.md), [Vector2d](math.md), [Vector2i](math.md), [Vector4d](math.md), [Matrix4d](math.md), [Transform](math.md), [Box](math.md), [Axis](math.md), [MathUtil](math.md)

**Codecs**
[Codec](codecs.md), [BuilderCodec](codecs.md), [KeyedCodec](codecs.md)

**Projectiles**
[ProjectileModule](projectiles.md), [ProjectileConfig](projectiles.md), [PhysicsConfig](projectiles.md), [StandardPhysicsConfig](projectiles.md), [ImpactConsumer](projectiles.md), [BounceConsumer](projectiles.md), [StandardPhysicsProvider](projectiles.md), [PredictedProjectile](projectiles.md), [BallisticData](projectiles.md), [BallisticDataProvider](projectiles.md), [ProjectileInteraction](projectiles.md)

**Collision**
[CollisionModule](collision.md), [CollisionResult](collision.md), [BlockCollisionData](collision.md), [CollisionConfig](collision.md), [CollisionFilter](collision.md), [CollisionMaterial](collision.md), [BasicCollisionData](collision.md), [BoxCollisionData](collision.md), [IBlockCollisionEvaluator](collision.md), [BoxBlockIntersectionEvaluator](collision.md), [CollisionModuleConfig](collision.md), [CollisionDataArray](collision.md), [CollisionResultComponent](collision.md)

**Fluids**
[Fluid](fluids.md)

**Combat**
[Damage](combat.md), [DamageEventSystem](combat.md), [Damage.Source](combat.md), [Damage.EntitySource](combat.md), [DamageDataComponent](combat.md), [DamageCause](combat.md), [KillFeedEvent](combat.md)

**NPCs**
[AllNPCsLoadedEvent](npc.md), [LoadedNPCEvent](npc.md), [BuilderInfo](npc.md), [SensorEvent](npc.md), [SensorEntityEvent](npc.md), [EventSearchType](npc.md)

**Adventure**
[DiscoverInstanceEvent](adventure.md), [DiscoverZoneEvent](adventure.md), [TreasureChestOpeningEvent](adventure.md), [InstanceDiscoveryConfig](adventure.md), [WorldMapTracker](adventure.md), [ZoneDiscoveryInfo](adventure.md)

**Asset Editor**
[EditorClientEvent](asset-editor.md), [AssetEditorActivateButtonEvent](asset-editor.md), [AssetEditorAssetCreatedEvent](asset-editor.md), [AssetEditorClientDisconnectEvent](asset-editor.md), [AssetEditorSelectAssetEvent](asset-editor.md), [AssetEditorFetchAutoCompleteDataEvent](asset-editor.md), [AssetEditorRequestDataSetEvent](asset-editor.md)

**Localization**
[GenerateDefaultLanguageEvent](i18n.md)

**Singleplayer**
[SingleplayerRequestAccessEvent](singleplayer.md)

## Topic Groups

**Core** - Essential plugin development
- 02-structure.md - Pack vs plugin directory structure and manifest configuration
- plugin-lifecycle.md - Plugin entry point, setup, and server lifecycle events
- commands.md - Slash commands
- entities.md - Players, entities, stats, velocity, and entity events
- player.md - Player events and messaging
- world.md - World access, world events, and chunk events
- universe-saves.md - Save/universe format, dedicated-server config, and binding worlds to structures
- events.md - Core event system patterns
- components.md - ECS system

**Systems** - Game systems integration
- permissions.md - Permission checks and permission events
- inventory.md - Items, inventory, and crafting
- tasks.md - Async scheduling
- ui.md - Player UI
- blocks.md - Block manipulation and block events
- blockyanim-format.md - Block animation file format
- assets.md - Asset registry, models, and asset events
- interactions.md - Interaction system (attacks, abilities)
- interactions-operations.md - Operation execution model and flow control
- interactions-context.md - InteractionContext data access API
- projectiles.md - Projectile spawning and physics
- collision.md - Collision detection and queries
- fluids.md - Fluid types and properties
- audio.md - Sound events, ambience, and audio mixing
- i18n.md - Localization events
- singleplayer.md - Singleplayer events

**Networking** - Network communication
- networking.md - Serialization, protocol types

**Editor** - Development tools
- asset-editor.md - Asset editor events

**Combat & NPCs** - Combat and AI systems
- combat.md - Damage system, damage events, kill feed
- npc.md - NPC loading, AI sensors
- npc-roles.md - NPC role definitions, behaviors, spawning
- drops.md - Loot tables for NPCs, blocks, containers

**Adventure** - Adventure gameplay features
- adventure.md - Instance discovery, treasure chests

**Data** - Serialization
- codecs.md - Data encoding/decoding

**Utilities** - Helper systems
- prefabs.md - Prefab loading, placement, and events
- math.md - Vectors, matrices, quaternions, shapes

**World Generation** - Procedural terrain and structure generation
- worldgen.md - World generation overview, pipeline, zones, biomes, terrain, caves, and prefabs
