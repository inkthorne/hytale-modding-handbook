package doublerun.probe;

import com.hypixel.hytale.component.Archetype;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.shape.Box;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.HytaleServer;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.entity.InteractionChain;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.movement.MovementStatesComponent;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.InteractionManager;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.BoundingBox;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.EntityStatType;
import com.hypixel.hytale.server.core.modules.interaction.InteractionModule;
import com.hypixel.hytale.server.core.modules.interaction.host.InteractionHost;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.ChunkSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.role.support.CombatSupport;
import com.hypixel.hytale.server.npc.interactions.NPCInteractionSimulationHandler;
import java.util.concurrent.TimeUnit;
import org.joml.Vector3d;

/**
 * Stages one case and measures it. Cases are chosen by system properties (run.sh sets them):
 *
 *   dr.root         RootInteraction id from this plugin's pack (Server/Item/RootInteractions/DR_*.json)
 *   dr.manager      npc      a host entity built the way ActionSpawnInteraction builds one: a manager made with
 *                            new InteractionManager(null, new NPCInteractionSimulationHandler()), no remote client
 *                   remote   the same host, then setHasRemoteClient(true): what a player's manager looks like
 *                   realnpc  a shipped NPC role spawned headless; the chain runs on ITS OWN manager, started the way
 *                            ActionAttack starts one (forInteraction + initChain + queueExecuteChain)
 *   dr.subjectRole  role for dr.manager=realnpc (default Chicken)
 *   dr.targetRole   role of a second NPC to act on ("none" for no target; default Chicken). A real NPC must not
 *                   hit its own species: NPCDamageSystems.FilterDamageSystem cancels damage from a source in the
 *                   target's DisableDamageGroups ("Self" for livestock) unless the source deals friendly damage
 *   dr.stat         EntityStatType id read on the context entity and the target before and after (default SignatureCharges)
 *   dr.inventory    true: give the OWNER entity a 9-slot Hotbar and Storage, so a type that writes to the owner's
 *                   inventory (ModifyInventory) has somewhere to write; inv_items is the total quantity in both
 *   dr.self         true: owner == the running entity (no proxy): the context ActionAttack builds for an NPC's own
 *                   chain. Default false: a second host is the owner, the proxy context ActionSpawnInteraction builds
 *   dr.settleMs     milliseconds from chain start to the reading (default 3000)
 *   dr.exitMs       milliseconds after worlds loaded to shut down (default 12000)
 *   dr.stack        true: ProbeLog writes the frames that called it
 *   dr.held         ID:N: the OWNER's active Hotbar slot (0) holds N of item ID (with dr.inventory), so the context ActionAttack builds
 *                   (owner == entity) has a held item for ModifyInventory's AdjustHeldItemQuantity to change
 *   dr.destroyBlock true: the context's TARGET_BLOCK is the first solid block below the host (DestroyBlock); the RESULT line reports
 *                   break_events (BreakBlockEvents raised) and block_id_before / block_id_after at that block
 *   dr.cooldownId   a cooldown id: the RESULT line reports cooldown_charges, the charges that cooldown has left on the
 *                   running entity's manager (read by reflection; NaN when there is none). The 13b TriggerCooldown cases
 *   dr.velocity     true: the host gets a Velocity and a MovementStatesComponent; the RESULT line reports force_instructions,
 *                   the vertical velocity of the host (the sum of the applied instructions; a host has no physics, so nothing else moves it). The name is kept from the first cut that counted queued instructions
 *   dr.instanceReturn true: the SUBJECT gets an InstanceEntityConfig whose return point is the default world, so ExitInstance (InstancesPlugin.exitInstance)
 *                   reaches its addComponent(Teleport) in a world that is not an instance; the RESULT line reports teleports_added
 *   dr.effect       an EntityEffect id: it is applied to the TARGET (infinitely) before the chain starts; the RESULT line
 *                   reports effect_present, 1 or 0 at the target
 *
 * Every figure is read AT the target: the target's health, the context entity's stat, the count of projectile
 * entities that appeared, the count of BeamComponents added. A count of firstRun calls is not a measurement of any
 * shipped type and is not made here.
 *
 * Provenance: the section load, the second thread hand-off and the "drop the host's InteractionHost marker" step
 * are the three workarounds of maintenance/probes/beams (Tasks.drive); see that README.
 */
final class Driver {
    private Driver() {
    }

    static String prop(String k, String d) {
        return System.getProperty(k, d);
    }

    static void run() {
        World world = Universe.get().getDefaultWorld();
        if (world == null) {
            Log.p("DR no default world");
            return;
        }
        Vector3d spawn = new Vector3d(0.0, 150.0, 0.0);
        var provider = world.getWorldConfig().getSpawnProvider();
        if (provider != null && provider.getSpawnPoints().length > 0) {
            spawn = new Vector3d(provider.getSpawnPoints()[0].getPosition());
        }
        spawn.y += 3.0;
        final Vector3d base = spawn;
        Log.p("DR loading the 3x3x3 sections around %s", base);
        // flag 4: a ticking section. A headless world has no player, so no chunk is loaded, and an entity added to a
        // NonTicking section is removed with reason UNLOAD. Three things were learned the hard way (the README has
        // the numbers): an NPC that falls or walks into a section that is not loaded is removed with UNLOAD (the
        // spawn point is often within a few blocks of a section boundary, so one section is not enough: 3x3x3);
        // a section no player tracks is unloaded when its keep-alive timer runs out (so addKeepLoaded); and the
        // active timer turns it NonTicking (so it is reset).
        java.util.List<java.util.concurrent.CompletableFuture<Void>> loads = new java.util.ArrayList<>();
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                for (int dz = -1; dz <= 1; dz++) {
                    loads.add(world.getChunkStore()
                        .getChunkSectionReferenceAtBlockAsync((int) base.x + 32 * dx, (int) base.y + 32 * dy, (int) base.z + 32 * dz, 4)
                        .thenAcceptAsync(sectionRef -> {
                            ChunkSection section = world.getChunkStore().getStore().getComponent(sectionRef, ChunkSection.getComponentType());
                            section.addKeepLoaded();
                            section.resetKeepAlive();
                            section.resetActiveTimer();
                        }, world));
                }
            }
        }
        java.util.concurrent.CompletableFuture.allOf(loads.toArray(new java.util.concurrent.CompletableFuture[0]))
            .thenAcceptAsync(v -> {
                Log.p("DR %d sections loaded", loads.size());
                try {
                    stage(world, base);
                } catch (Throwable t) {
                    Log.p("DR stage threw %s", t);
                    t.printStackTrace();
                }
            }, world);
    }

    private static Ref<EntityStore> spawnNpc(Store<EntityStore> store, String role, Vector3d pos) {
        NPCPlugin npc = NPCPlugin.get();
        int index = npc.getIndex(role);
        if (index < 0) {
            Log.p("DR no NPC role '%s'", role);
            return null;
        }
        var pair = npc.spawnEntity(store, index, pos, new Rotation3f(), null, null);
        return pair == null ? null : pair.first();
    }

    static float stat(Store<EntityStore> store, Ref<EntityStore> ref, int index) {
        if (ref == null || !ref.isValid() || index < 0) {
            return Float.NaN;
        }
        EntityStatMap map = store.getComponent(ref, EntityStatMap.getComponentType());
        if (map == null) {
            return Float.NaN;
        }
        EntityStatValue v = map.get(index);
        return v == null ? Float.NaN : v.get();
    }

    /** Total quantity of all items in the entity's Hotbar and Storage; NaN when it has neither. */
    static float inventoryItems(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref == null || !ref.isValid()) {
            return Float.NaN;
        }
        var hotbar = store.getComponent(ref, InventoryComponent.Hotbar.getComponentType());
        var storage = store.getComponent(ref, InventoryComponent.Storage.getComponentType());
        if (hotbar == null && storage == null) {
            return Float.NaN;
        }
        int total = 0;
        for (ItemContainer c : new ItemContainer[] {hotbar == null ? null : hotbar.getInventory(), storage == null ? null : storage.getInventory()}) {
            if (c == null) {
                continue;
            }
            for (short slot = 0; slot < c.getCapacity(); slot++) {
                ItemStack st = c.getItemStack(slot);
                if (st != null && !st.isEmpty()) {
                    total += st.getQuantity();
                }
            }
        }
        return total;
    }

    /** Charges left of the cooldown {@code id} on {@code im}'s CooldownHandler; both the handler and the count are private, so by reflection. NaN when absent. */
    static float cooldownCharges(InteractionManager im, String id) {
        if (id == null) {
            return Float.NaN;
        }
        try {
            java.lang.reflect.Field hf = InteractionManager.class.getDeclaredField("cooldownHandler");
            hf.setAccessible(true);
            var handler = (com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler) hf.get(im);
            var cd = handler.getCooldown(id);
            if (cd == null) {
                return Float.NaN;
            }
            java.lang.reflect.Field cf = cd.getClass().getDeclaredField("chargeCount");
            cf.setAccessible(true);
            return cf.getInt(cd);
        } catch (ReflectiveOperationException e) {
            Log.p("DR cooldownCharges failed: %s", e);
            return Float.NaN;
        }
    }

    /** The id of the block at x,y,z read through its chunk section (World lost its block getters in 0.7.x); -1 when the section is not loaded. */
    static int blockId(World world, int x, int y, int z) {
        var chunkStore = world.getChunkStore();
        var ref = chunkStore.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return -1;
        }
        var section = chunkStore.getStore().getComponent(ref, com.hypixel.hytale.server.core.universe.world.chunk.section.BlockSection.getComponentType());
        return section == null ? -1 : section.get(x, y, z);
    }

    static float forceInstructions(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref == null || !ref.isValid()) {
            return Float.NaN;
        }
        Velocity v = store.getComponent(ref, Velocity.getComponentType());
        // GenericVelocityInstructionSystem consumes the instructions each tick and adds them into the velocity; a host has no physics,
        // so the velocity keeps the sum: the vertical component is the read-out. (The queue itself is empty by the time we look.)
        return v == null ? Float.NaN : (float) v.getY() + v.getInstructions().size();
    }

    static float effectPresent(Store<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        if (ref == null || !ref.isValid() || effectId == null) {
            return Float.NaN;
        }
        EffectControllerComponent ec = store.getComponent(ref, EffectControllerComponent.getComponentType());
        return ec == null ? Float.NaN : (ec.hasEffect(EntityEffect.getAssetMap().getIndex(effectId)) ? 1.0f : 0.0f);
    }

    private static Ref<EntityStore> spawnHostEntity(Store<EntityStore> store, Vector3d pos, boolean inventory, String what) {
        Ref<EntityStore> h = InteractionHost.spawnHost(store, pos, new Rotation3f(), 120.0f, new NPCInteractionSimulationHandler());
        // InteractionHostCleanupSystem removes a host whose chain is null on its first tick. Drop the marker so
        // the host (and the stat we read from it) outlives the chain; the entity keeps its manager.
        store.removeComponent(h, InteractionHost.getComponentType());
        // InteractionHost.spawnHost gives the host no BoundingBox. An NPC that is hit by a chain this host runs
        // steers away from the attacker, and BodyMotionFindWithTarget.canComputeMotion throws a NullPointerException
        // for the missing box ("Failed to tick NPC"), which ends the NPC. The box is the one difference from
        // spawnHost, for every host case, so the damaged target survives to be read.
        store.addComponent(h, BoundingBox.getComponentType(), new BoundingBox(new Box(-0.3, 0.0, -0.3, 0.3, 0.6, 0.3)));
        if (Boolean.getBoolean("dr.velocity")) {
            // ApplyForce reads the entity's Velocity and MovementStatesComponent; spawnHost gives the host neither.
            store.addComponent(h, Velocity.getComponentType(), new Velocity());
            store.addComponent(h, MovementStatesComponent.getComponentType(), new MovementStatesComponent());
        }
        if (inventory) {
            InventoryComponent.Hotbar hotbar = new InventoryComponent.Hotbar((short) 9);
            String held = prop("dr.held", null);
            if (held != null && what.equals("subject")) {
                String[] parts = held.split(":");
                hotbar.getInventory().setItemStackForSlot((short) 0, new ItemStack(parts[0], Integer.parseInt(parts[1])));
            }
            store.addComponent(h, InventoryComponent.Hotbar.getComponentType(), hotbar);
            store.addComponent(h, InventoryComponent.Storage.getComponentType(), new InventoryComponent.Storage((short) 9));
        }
        Log.p("DR %s (host entity) %s inventory=%s", what, h, inventory);
        return h;
    }

    private static void stage(World world, Vector3d base) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        String rootId = prop("dr.root", null);
        String manager = prop("dr.manager", "npc");
        String subjectRole = prop("dr.subjectRole", "Chicken");
        String targetRole = prop("dr.targetRole", "Chicken");
        String statId = prop("dr.stat", "SignatureCharges");
        long settleMs = Long.parseLong(prop("dr.settleMs", "3000"));
        boolean inventory = Boolean.getBoolean("dr.inventory");
        boolean self = Boolean.getBoolean("dr.self");
        RootInteraction root = RootInteraction.getAssetMap().getAsset(rootId);
        if (root == null) {
            Log.p("DR FATAL no RootInteraction '%s' in the asset store", rootId);
            return;
        }
        int statIndex = EntityStatType.getAssetMap().getIndex(statId);
        int healthIndex = EntityStatType.getAssetMap().getIndex("Health");

        Ref<EntityStore> target = null;
        if (!"none".equals(targetRole)) {
            // Stay inside the sections that were loaded; step toward the side with room.
            double col = ((Math.floor(base.x) % 32) + 32) % 32;
            target = spawnNpc(store, targetRole, new Vector3d(base.x + (col < 24 ? 3.0 : -3.0), base.y, base.z));
            Log.p("DR target %s role=%s", target, targetRole);
        }
        final Ref<EntityStore> targetRef = target;
        Watch.TARGET = targetRef;
        if (!"none".equals(targetRole) && (targetRef == null || !targetRef.isValid())) {
            Log.p("DR FATAL the target NPC is not valid right after spawning");
            return;
        }

        // subject: the entity whose InteractionManager runs the chain. owner: the entity the chain's
        // getOwningEntity() names, and the one ModifyInventory writes to.
        Ref<EntityStore> subject;
        Ref<EntityStore> owner;
        boolean real = manager.equals("realnpc");
        if (real) {
            subject = spawnNpc(store, subjectRole, base);
            Log.p("DR subject (real NPC) %s role=%s", subject, subjectRole);
            if (subject == null) {
                return;
            }
            owner = subject;
        } else {
            subject = spawnHostEntity(store, base, inventory && self, "subject");
            // A host started by ActionSpawnInteraction runs for an owner that is a different entity (the NPC): the
            // context is a PROXY context (owner != entity). self=true makes owner == entity instead.
            owner = self ? subject : spawnHostEntity(store, new Vector3d(base.x, base.y, base.z + 1.0), inventory, "owner");
        }
        final Ref<EntityStore> subjectRef = subject;
        final Ref<EntityStore> ownerRef = owner;
        InteractionManager im = store.getComponent(subjectRef, InteractionModule.get().getInteractionManagerComponent());
        if (im == null) {
            Log.p("DR FATAL subject has no InteractionManager");
            return;
        }
        if (manager.equals("remote")) {
            im.setHasRemoteClient(true);
        }
        Log.p("DR manager=%s self=%s simulationHandler=%s", manager, self, im.getInteractionSimulationHandler().getClass().getSimpleName());
        if (real) {
            Archetype<EntityStore> arch = store.getArchetype(subjectRef);
            StringBuilder sb = new StringBuilder();
            for (int i = arch.getMinIndex(); i < arch.length(); i++) {
                var ct = arch.get(i);
                if (ct != null) {
                    sb.append(ct.getTypeClass().getSimpleName()).append(' ');
                }
            }
            Log.p("DR subject archetype: %s", sb);
        }

        // Let the NPCs finish their own set-up before the chain starts.
        long startAfter = real || targetRef != null ? 1500 : 200;
        if (Boolean.getBoolean("dr.instanceReturn")) {
            // exitInstance(): the entity's own InstanceEntityConfig return point, else the world's (and a world that is not an instance throws "Player is not in an instance")
            var cfg = store.ensureAndGetComponent(subjectRef, com.hypixel.hytale.builtin.instances.config.InstanceEntityConfig.getComponentType());
            cfg.setReturnPoint(new com.hypixel.hytale.builtin.instances.config.WorldReturnPoint(world.getWorldConfig().getUuid(),
                new com.hypixel.hytale.math.vector.Transform(base.x, base.y, base.z, 0.0f, 0.0f, 0.0f), false, null, null));
            Log.p("DR subject has an InstanceEntityConfig return point in world %s", world.getName());
        }
        final InteractionManager manager0 = im;
        HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> world.execute(() -> {
            try {
                startChain(world, store, manager0, subjectRef, ownerRef, targetRef, root, rootId, manager, real, self, statIndex, healthIndex, statId, settleMs);
            } catch (Throwable t) {
                Log.p("DR startChain threw %s", t);
                t.printStackTrace();
            }
        }), startAfter, TimeUnit.MILLISECONDS);
    }

    private static void startChain(World world, Store<EntityStore> store, InteractionManager im, Ref<EntityStore> subject,
                                   Ref<EntityStore> owner, Ref<EntityStore> target, RootInteraction root, String rootId,
                                   String manager, boolean real, boolean self,
                                   int statIndex, int healthIndex, String statId, long settleMs) {
        if (!subject.isValid() || !owner.isValid()) {
            Log.p("DR FATAL subject or owner is no longer valid before the chain starts");
            return;
        }
        if (target != null && !target.isValid()) {
            Log.p("DR FATAL the target is no longer valid before the chain starts");
            return;
        }
        final String effectId = prop("dr.effect", null);
        final String cooldownId = prop("dr.cooldownId", null);
        if (effectId != null) {
            EffectControllerComponent ec = store.getComponent(target, EffectControllerComponent.getComponentType());
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            if (ec == null || effect == null) {
                Log.p("DR FATAL cannot apply effect '%s' to the target (controller %s, effect %s)", effectId, ec, effect);
                return;
            }
            ec.addInfiniteEffect(target, EntityEffect.getAssetMap().getIndex(effectId), effect, store);
        }
        final String destroy = prop("dr.destroyBlock", null);
        int[] blockPos = null;
        if (destroy != null) {
            Vector3d sp = store.getComponent(subject, com.hypixel.hytale.server.core.modules.entity.component.TransformComponent.getComponentType()).getPosition();
            int bx = (int) Math.floor(sp.x), bz = (int) Math.floor(sp.z);
            for (int by = (int) Math.floor(sp.y) - 1; by > 0 && blockPos == null; by--) {
                if (blockId(world, bx, by, bz) > 0) {
                    blockPos = new int[] {bx, by, bz};
                }
            }
            if (blockPos == null) {
                Log.p("DR FATAL no solid block below the host");
                return;
            }
        }
        final int[] blockAt = blockPos;
        final int blockBefore = blockAt == null ? -1 : blockId(world, blockAt[0], blockAt[1], blockAt[2]);
        final int breaks0 = Watch.BREAKS.get();
        final float tHealth0 = stat(store, target, healthIndex);
        final float tStat0 = stat(store, target, statIndex);
        final float sStat0 = stat(store, subject, statIndex);
        final float inv0 = inventoryItems(store, owner);
        final int proj0 = Watch.PROJECTILES.get();
        final int projNew0 = Watch.PROJECTILES_NEW.get();
        final int beams0 = Watch.BEAMS_ADDED.get();
        final int teleports0 = Watch.TELEPORTS_ADDED.get();
        final int raised0 = Watch.DAMAGE_RAISED.get();
        final int delivered0 = Watch.DAMAGE_DELIVERED.get();
        final int otherRaised0 = Watch.DAMAGE_OTHER_RAISED.get();
        final int otherDelivered0 = Watch.DAMAGE_OTHER_DELIVERED.get();
        final float charges0 = cooldownCharges(im, cooldownId);
        final float instr0 = forceInstructions(store, subject);
        final float effect0 = effectPresent(store, target, effectId);
        Log.p("DR before case=%s manager=%s target_health=%s target_%s=%s subject_%s=%s inv_items=%s projectiles=%d beams_added=%d"
                + " cooldown_charges=%s force_instructions=%s effect_present=%s",
            rootId, manager, tHealth0, statId, tStat0, statId, sStat0, inv0, proj0, beams0, charges0, instr0, effect0);

        // real NPC or self: the context ActionAttack builds (owner == entity). Otherwise the proxy context
        // ActionSpawnInteraction builds: entity = the host, owner = another entity.
        InteractionContext ctx = real || self
            ? InteractionContext.forInteraction(im, subject, InteractionType.Primary, store)
            : InteractionContext.forProxyEntity(im, owner, subject, store);
        if (target != null) {
            ctx.getMetaStore().putMetaObject(Interaction.TARGET_ENTITY, target);
        }
        if (blockAt != null) {
            ctx.getMetaStore().putMetaObject(Interaction.TARGET_BLOCK, new com.hypixel.hytale.protocol.BlockPosition(blockAt[0], blockAt[1], blockAt[2]));
            Log.p("DR target block %d,%d,%d id=%d", blockAt[0], blockAt[1], blockAt[2], blockBefore);
        }
        InteractionChain chain = im.initChain(InteractionType.Primary, ctx, root, false);
        im.queueExecuteChain(chain);
        if (real) {
            // ActionAttack does this after queueing (ActionAttack.java:221).
            CombatSupport.get(subject, store).setExecutingAttack(chain, false, 0.0);
        }
        Log.p("DR chain queued case=%s manager=%s self=%s", rootId, manager, self);

        Runnable collect = () -> {
            float tHealth1 = stat(store, target, healthIndex);
            float tStat1 = stat(store, target, statIndex);
            float sStat1 = stat(store, subject, statIndex);
            Log.p("DR RESULT case=%s manager=%s self=%s target_health_delta=%s target_%s_delta=%s subject_%s_delta=%s"
                    + " inv_items_delta=%s projectiles=%d beams_added=%d damage_raised=%d damage_delivered=%d"
                    + " break_events=%d block_id_before=%d block_id_after=%d projectiles_new=%d damage_other_raised=%d damage_other_delivered=%d cooldown_charges=%s cooldown_charges_before=%s force_instructions=%s effect_present=%s"
                    + " teleports_added=%d chain_server_state=%s chains_left=%d",
                rootId, manager, self, tHealth1 - tHealth0, statId, tStat1 - tStat0, statId, sStat1 - sStat0,
                inventoryItems(store, owner) - inv0, Watch.PROJECTILES.get() - proj0, Watch.BEAMS_ADDED.get() - beams0,
                Watch.DAMAGE_RAISED.get() - raised0, Watch.DAMAGE_DELIVERED.get() - delivered0,
                Watch.BREAKS.get() - breaks0, blockBefore, blockAt == null ? -1 : blockId(world, blockAt[0], blockAt[1], blockAt[2]),
                Watch.PROJECTILES_NEW.get() - projNew0, Watch.DAMAGE_OTHER_RAISED.get() - otherRaised0, Watch.DAMAGE_OTHER_DELIVERED.get() - otherDelivered0,
                cooldownCharges(im, cooldownId), charges0, forceInstructions(store, subject) - instr0, effectPresent(store, target, effectId),
                Watch.TELEPORTS_ADDED.get() - teleports0, chain.getServerState(), im.getChains().size());
        };
        HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> world.execute(collect), settleMs, TimeUnit.MILLISECONDS);
        // If the world thread died, world.execute never runs. The counters are atomics and can still be read.
        HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> Log.p("DR FALLBACK case=%s manager=%s projectiles=%d beams_added=%d teleports_added=%d (read from the scheduler thread)",
            rootId, manager, Watch.PROJECTILES.get() - proj0, Watch.BEAMS_ADDED.get() - beams0, Watch.TELEPORTS_ADDED.get() - teleports0), settleMs + 2500, TimeUnit.MILLISECONDS);
    }
}
