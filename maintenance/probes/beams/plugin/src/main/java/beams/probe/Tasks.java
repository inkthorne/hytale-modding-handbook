package beams.probe;

import com.hypixel.hytale.assetstore.map.IndexedLookupTableAssetMap;
import com.hypixel.hytale.builtin.beam.asset.Beam;
import com.hypixel.hytale.builtin.beam.interaction.AttachBeamInteraction;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.BeamInstance;
import com.hypixel.hytale.protocol.BeamsUpdate;
import com.hypixel.hytale.protocol.io.PacketIO;
import com.hypixel.hytale.server.core.modules.interaction.IInteractionSimulationHandler;
import com.hypixel.hytale.server.core.modules.interaction.host.InteractionHost;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.projectile.ProjectileModule;
import com.hypixel.hytale.server.core.modules.projectile.config.ProjectileConfig;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.lang.foreign.Arena;
import java.lang.foreign.MemorySegment;
import java.lang.foreign.ValueLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.TreeMap;
import org.joml.Vector3d;

/** The headless tasks. Each prints PROBE lines; the README quotes the ones that decide a claim. */
final class Tasks {
    private Tasks() {
    }

    // ---- C6: what index did each AttachBeam resolve at load? ----

    static void c6() {
        IndexedLookupTableAssetMap<String, Beam> beams = Beam.getAssetMap();
        Log.p("c6 sentinel: Beam 'NoSuchBeam' getIndex=%d (Integer.MIN_VALUE=%d)",
            beams.getIndex("NoSuchBeam"), Integer.MIN_VALUE);
        for (Map.Entry<String, Beam> e : new TreeMap<>(beams.getAssetMap()).entrySet()) {
            Log.p("c6 Beam id='%s' index=%d texture=%s", e.getKey(), beams.getIndex(e.getKey()), e.getValue().getTexture());
        }
        int seen = 0;
        try {
            Field idField = AttachBeamInteraction.class.getDeclaredField("beamConfigId");
            Field indexField = AttachBeamInteraction.class.getDeclaredField("beamIndex");
            idField.setAccessible(true);
            indexField.setAccessible(true);
            for (Map.Entry<String, Interaction> e : new TreeMap<>(Interaction.getAssetMap().getAssetMap()).entrySet()) {
                if (!(e.getValue() instanceof AttachBeamInteraction attach)) {
                    continue;
                }
                seen++;
                String configId = (String) idField.get(attach);
                int resolved = indexField.getInt(attach);
                Log.p("c6 AttachBeam interaction id='%s' BeamConfig='%s' resolvedBeamIndex=%d"
                        + " (now getIndex(BeamConfig)=%d) interactionStoreIndex=%d",
                    e.getKey(), configId, resolved, beams.getIndex(configId),
                    Interaction.getAssetMap().getIndex(e.getKey()));
            }
        } catch (ReflectiveOperationException ex) {
            Log.p("c6 reflection failed: %s", ex);
        }
        Log.p("c6 done, %d AttachBeam interaction(s) seen", seen);
    }

    /** Rewrite an interaction file (a new key, so the asset differs) and read the indexes again. */
    static void reload(String file) {
        java.nio.file.Path path = java.nio.file.Path.of(file);
        com.hypixel.hytale.server.core.HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> {
            try {
                String text = java.nio.file.Files.readString(path);
                java.nio.file.Files.writeString(path, text.replace("\"Type\": \"AttachBeam\",", "\"Type\": \"AttachBeam\",\n  \"Scale\": 2.0,"));
                Log.p("reload: rewrote %s", path);
            } catch (java.io.IOException e) {
                Log.p("reload: could not rewrite %s: %s", path, e);
            }
        }, 4, java.util.concurrent.TimeUnit.SECONDS);
        com.hypixel.hytale.server.core.HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> {
            Log.p("reload: reading the indexes again, 12 s after start");
            c6();
            com.hypixel.hytale.server.core.HytaleServer.get().shutdownServer();
        }, 12, java.util.concurrent.TimeUnit.SECONDS);
    }

    // ---- C3 server half: BeamsUpdate with long and non-ASCII node names ----

    static void c3() {
        String ninetySix = "N".repeat(96);
        String ninetySeven = "N".repeat(97);
        c3Case("valid R-Attachment (control)", "R-Attachment");
        c3Case("96 bytes (boundary)", ninetySix);
        c3Case("97 bytes", ninetySeven);
        c3Case("e-acute (U+00E9)", "café");
        c3Case("CJK", "日本");
        c3Case("96 ASCII + 1 e-acute (96 chars? 97 chars)", "N".repeat(96) + "é");
    }

    private static void c3Case(String label, String nodeName) {
        BeamInstance beam = new BeamInstance(1, 0.25f, null, PacketIO.ZERO_VECTOR3, 0.25f, 7,
            nodeName, PacketIO.ZERO_VECTOR3, null);
        BeamsUpdate update = new BeamsUpdate(new BeamInstance[] {beam});
        try (Arena arena = Arena.ofConfined()) {
            MemorySegment mem = arena.allocate(4096);
            int written = update.serialize(mem, 0);
            BeamsUpdate back = BeamsUpdate.toObject(mem.asSlice(0, written));
            String read = back.beams[0].targetNodeName;
            Log.p("c3 case='%s' charLength=%d utf8Length=%d serialize=OK bytes=%d readBack.length=%d readBack='%s' readBackHex=%s",
                label, nodeName.length(), nodeName.getBytes(StandardCharsets.UTF_8).length, written,
                read.length(), read.length() > 16 ? read.substring(0, 16) + "..." : read, hex(read));
        } catch (Throwable t) {
            Log.p("c3 case='%s' charLength=%d serialize=THREW %s: %s", label, nodeName.length(), t.getClass().getName(), t.getMessage());
        }
    }

    private static String hex(String s) {
        byte[] b = s.getBytes(StandardCharsets.ISO_8859_1);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < Math.min(b.length, 8); i++) {
            sb.append(String.format("%02x", b[i]));
        }
        return b.length > 8 ? sb + "..." : sb.toString();
    }

    // ---- C1: fire a ProjectileConfig from a host entity ----

    /** No charging, no state: the host only needs a manager to run the ProjectileSpawn chain on. */
    private static final class NoSim implements IInteractionSimulationHandler {
        @Override
        public void setState(com.hypixel.hytale.protocol.InteractionType type, boolean state) {
        }

        @Override
        public boolean isCharging(boolean firstRun, float time, com.hypixel.hytale.protocol.InteractionType type,
                                  com.hypixel.hytale.server.core.entity.InteractionContext context,
                                  Ref<EntityStore> ref,
                                  com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler cooldownHandler) {
            return false;
        }

        @Override
        public boolean shouldCancelCharging(boolean firstRun, float time, com.hypixel.hytale.protocol.InteractionType type,
                                            com.hypixel.hytale.server.core.entity.InteractionContext context,
                                            Ref<EntityStore> ref,
                                            com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler cooldownHandler) {
            return false;
        }

        @Override
        public float getChargeValue(boolean firstRun, float time, com.hypixel.hytale.protocol.InteractionType type,
                                    com.hypixel.hytale.server.core.entity.InteractionContext context,
                                    Ref<EntityStore> ref,
                                    com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler cooldownHandler) {
            return 0.0f;
        }
    }

    static void drive(String configId) {
        World world = Universe.get().getDefaultWorld();
        if (world == null) {
            Log.p("drive: no default world");
            return;
        }
        // A headless world has no player, so no chunk is loaded. An entity in an unloaded chunk is
        // removed with reason UNLOAD; load the spawn chunk as a ticking one (flag 4; a joining player passes 32, World:738): a non-ticking chunk removes the entity (UpdateLocationSystems).
        Vector3d spawn = new Vector3d(0.0, 150.0, 0.0);
        var provider = world.getWorldConfig().getSpawnProvider();
        if (provider != null && provider.getSpawnPoints().length > 0) {
            spawn = new Vector3d(provider.getSpawnPoints()[0].getPosition());
        }
        spawn.y += 3.0;
        Log.p("drive: loading the section at %s", spawn);
        // flag 4 asks for a ticking section. A section no player tracks stays NonTicking otherwise,
        // and UpdateLocationSystems removes an entity added to one with reason UNLOAD.
        world.getChunkStore().getChunkSectionReferenceAtBlockAsync((int) spawn.x, (int) spawn.y, (int) spawn.z, 4)
            .thenAcceptAsync(sectionRef -> {
                boolean nonTicking = world.getChunkStore().getStore().getArchetype(sectionRef)
                    .contains(com.hypixel.hytale.server.core.universe.world.storage.ChunkStore.REGISTRY.getNonTickingComponentType());
                Log.p("drive: section loaded %s, NonTicking=%s", sectionRef, nonTicking);
                try {
                    fire(world, configId);
                } catch (Throwable t) {
                    Log.p("drive: fire threw %s", t);
                    t.printStackTrace();
                }
            }, world);
    }

    private static void fire(World world, String configId) {
        {
            Store<EntityStore> store = world.getEntityStore().getStore();
            ProjectileConfig config = ProjectileConfig.getAssetMap().getAsset(configId);
            if (config == null) {
                Log.p("drive: no ProjectileConfig '%s'", configId);
                return;
            }
            Vector3d position = new Vector3d(0.0, 150.0, 0.0);
            var spawnProvider = world.getWorldConfig().getSpawnProvider();
            if (spawnProvider != null && spawnProvider.getSpawnPoints().length > 0) {
                position = new Vector3d(spawnProvider.getSpawnPoints()[0].getPosition());
                position.y += 3.0;   // inside the section of the spawn point, which is the one that was loaded
            }
            Log.p("drive: position %s", position);
            final Vector3d startPosition = position;
            Ref<EntityStore> host = InteractionHost.spawnHost(store, startPosition, new Rotation3f(), 120.0f, new NoSim());
            // InteractionHostCleanupSystem removes a host whose chain is null on its first tick,
            // before a 0.2 s Simple could finish. Drop the marker; the entity keeps its manager.
            store.removeComponent(host, InteractionHost.getComponentType());
            var manager = store.getComponent(host,
                com.hypixel.hytale.server.core.modules.interaction.InteractionModule.get().getInteractionManagerComponent());
            // A player's InteractionManager is built with a PlayerRef, so hasRemoteClient is true;
            // an NPC's and an InteractionHost's is built with null, so it is false. The flag is the
            // only difference this probe changes.
            if (Boolean.getBoolean("beams.probe.remoteClient")) {
                manager.setHasRemoteClient(true);
            }
            Log.p("drive: host %s, firing '%s' from it, hasRemoteClient=%s", host, configId,
                Boolean.getBoolean("beams.probe.remoteClient"));
            boolean[] fired = {false};
            store.forEachChunk(com.hypixel.hytale.server.core.modules.interaction.InteractionModule.get().getInteractionManagerComponent(), (chunk, buffer) -> {
                if (fired[0]) {
                    return;
                }
                fired[0] = true;
                Ref<EntityStore> projectile = ProjectileModule.get().spawnProjectile(
                    host, buffer, config, new Vector3d(startPosition), new Vector3d(0.0, 0.0, 1.0));
                Log.p("drive: spawnProjectile returned %s", projectile);
            });
            Log.p("drive: forEachChunk returned (command buffer consumed)");
        }
    }
}
