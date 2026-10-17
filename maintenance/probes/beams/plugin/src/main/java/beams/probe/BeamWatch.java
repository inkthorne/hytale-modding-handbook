package beams.probe;

import com.hypixel.hytale.builtin.beam.AttachedBeam;
import com.hypixel.hytale.builtin.beam.BeamComponent;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefChangeSystem;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.tracker.NetworkId;
import com.hypixel.hytale.server.core.modules.projectile.component.PredictedProjectile;
import com.hypixel.hytale.server.core.modules.projectile.component.Projectile;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import javax.annotation.Nonnull;

/** The observer: which entity gains, changes and loses a BeamComponent, and what it holds. */
final class BeamWatch {
    private BeamWatch() {
    }

    static String who(Ref<EntityStore> ref, ComponentAccessor<EntityStore> store) {
        NetworkId net = store.getComponent(ref, NetworkId.getComponentType());
        boolean player = store.getComponent(ref, Player.getComponentType()) != null;
        boolean projectile = store.getComponent(ref, Projectile.getComponentType()) != null;
        boolean predicted = store.getComponent(ref, PredictedProjectile.getComponentType()) != null;
        return "ref=" + ref + " networkId=" + (net == null ? "none" : net.getId())
            + " player=" + player + " projectile=" + projectile + " predictedProjectile=" + predicted;
    }

    static String beams(ComponentAccessor<EntityStore> store, BeamComponent component) {
        List<AttachedBeam> list = component.getBeams();
        StringBuilder sb = new StringBuilder("n=").append(list.size()).append(" [");
        for (AttachedBeam b : list) {
            NetworkId target = b.targetEntity() == null || !b.targetEntity().isValid() ? null
                : store.getComponent(b.targetEntity(), NetworkId.getComponentType());
            sb.append("{index=").append(b.beamIndex())
                .append(" srcScale=").append(b.sourceScale())
                .append(" tgtScale=").append(b.targetScale())
                .append(" srcNode=").append(b.sourceNode())
                .append(" tgtNode=").append(b.targetNode())
                .append(" tgtNetworkId=").append(b.targetEntity() == null ? "-" : target == null ? "none/invalid" : target.getId())
                .append(" tgtPos=").append(b.targetPosition())
                .append("}");
        }
        return sb.append("]").toString();
    }

    static class Changes extends RefChangeSystem<EntityStore, BeamComponent> {
        @Nonnull
        @Override
        public Query<EntityStore> getQuery() {
            return BeamComponent.getComponentType();
        }

        @Nonnull
        @Override
        public ComponentType<EntityStore, BeamComponent> componentType() {
            return BeamComponent.getComponentType();
        }

        @Override
        public void onComponentAdded(@Nonnull Ref<EntityStore> ref, @Nonnull BeamComponent component,
                                     @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("BeamComponent ADDED %s %s", who(ref, buffer), beams(buffer, component));
        }

        @Override
        public void onComponentSet(@Nonnull Ref<EntityStore> ref, BeamComponent oldComponent,
                                   @Nonnull BeamComponent newComponent, @Nonnull Store<EntityStore> store,
                                   @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("BeamComponent SET %s %s", who(ref, buffer), beams(buffer, newComponent));
        }

        @Override
        public void onComponentRemoved(@Nonnull Ref<EntityStore> ref, @Nonnull BeamComponent component,
                                       @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("BeamComponent REMOVED %s %s", who(ref, buffer), beams(buffer, component));
        }
    }

    /** Logs the beam list of every entity that has one, once, and again whenever it changes. */
    static class Tick extends EntityTickingSystem<EntityStore> {
        private final Map<Ref<EntityStore>, String> last = new ConcurrentHashMap<>();

        @Nonnull
        @Override
        public Query<EntityStore> getQuery() {
            return BeamComponent.getComponentType();
        }

        @Override
        public void tick(float dt, int index, @Nonnull ArchetypeChunk<EntityStore> chunk,
                         @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            BeamComponent component = chunk.getComponent(index, BeamComponent.getComponentType());
            Ref<EntityStore> ref = chunk.getReferenceTo(index);
            String now = beams(store, component);
            if (!now.equals(last.put(ref, now))) {
                Log.p("BeamComponent STATE %s %s", who(ref, store), now);
            }
        }
    }
}
