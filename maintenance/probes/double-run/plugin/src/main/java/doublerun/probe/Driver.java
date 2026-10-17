package doublerun.probe;

import com.hypixel.hytale.component.Archetype;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.shape.Box;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.HytaleServer;
import com.hypixel.hytale.server.core.entity.InteractionChain;
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
        if (inventory) {
            store.addComponent(h, InventoryComponent.Hotbar.getComponentType(), new InventoryComponent.Hotbar((short) 9));
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
        final float tHealth0 = stat(store, target, healthIndex);
        final float tStat0 = stat(store, target, statIndex);
        final float sStat0 = stat(store, subject, statIndex);
        final float inv0 = inventoryItems(store, owner);
        final int proj0 = Watch.PROJECTILES.get();
        final int beams0 = Watch.BEAMS_ADDED.get();
        final int raised0 = Watch.DAMAGE_RAISED.get();
        final int delivered0 = Watch.DAMAGE_DELIVERED.get();
        Log.p("DR before case=%s manager=%s target_health=%s target_%s=%s subject_%s=%s inv_items=%s projectiles=%d beams_added=%d",
            rootId, manager, tHealth0, statId, tStat0, statId, sStat0, inv0, proj0, beams0);

        // real NPC or self: the context ActionAttack builds (owner == entity). Otherwise the proxy context
        // ActionSpawnInteraction builds: entity = the host, owner = another entity.
        InteractionContext ctx = real || self
            ? InteractionContext.forInteraction(im, subject, InteractionType.Primary, store)
            : InteractionContext.forProxyEntity(im, owner, subject, store);
        if (target != null) {
            ctx.getMetaStore().putMetaObject(Interaction.TARGET_ENTITY, target);
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
                    + " inv_items_delta=%s projectiles=%d beams_added=%d damage_raised=%d damage_delivered=%d chain_server_state=%s chains_left=%d",
                rootId, manager, self, tHealth1 - tHealth0, statId, tStat1 - tStat0, statId, sStat1 - sStat0,
                inventoryItems(store, owner) - inv0, Watch.PROJECTILES.get() - proj0, Watch.BEAMS_ADDED.get() - beams0,
                Watch.DAMAGE_RAISED.get() - raised0, Watch.DAMAGE_DELIVERED.get() - delivered0,
                chain.getServerState(), im.getChains().size());
        };
        HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> world.execute(collect), settleMs, TimeUnit.MILLISECONDS);
        // If the world thread died, world.execute never runs. The counters are atomics and can still be read.
        HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> Log.p("DR FALLBACK case=%s manager=%s projectiles=%d beams_added=%d (read from the scheduler thread)",
            rootId, manager, Watch.PROJECTILES.get() - proj0, Watch.BEAMS_ADDED.get() - beams0), settleMs + 2500, TimeUnit.MILLISECONDS);
    }
}
