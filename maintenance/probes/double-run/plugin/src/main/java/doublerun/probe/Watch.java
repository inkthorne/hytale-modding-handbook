package doublerun.probe;

import com.hypixel.hytale.builtin.beam.BeamComponent;
import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefChangeSystem;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.entity.entities.ProjectileComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.concurrent.atomic.AtomicInteger;
import javax.annotation.Nonnull;

/** Counters at the target of an effect: how many projectile entities appeared, how many BeamComponents were added. */
final class Watch {
    static final AtomicInteger PROJECTILES = new AtomicInteger();
    static final AtomicInteger BEAMS_ADDED = new AtomicInteger();
    static final AtomicInteger BEAMS_SET = new AtomicInteger();
    static final AtomicInteger DAMAGE_RAISED = new AtomicInteger();
    static final AtomicInteger DAMAGE_DELIVERED = new AtomicInteger();

    private Watch() {
    }

    /** Why an entity with a NetworkId (the host, an NPC) leaves the store: the reason is the diagnosis of a lost subject. */
    static final class Lifecycle extends RefSystem<EntityStore> {
        @Override
        public Query<EntityStore> getQuery() {
            return com.hypixel.hytale.server.core.modules.interaction.InteractionModule.get().getInteractionManagerComponent();
        }

        @Override
        public void onEntityAdded(@Nonnull Ref<EntityStore> ref, @Nonnull AddReason reason,
                                  @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("entity with an InteractionManager ADDED reason=%s ref=%s", reason, ref);
        }

        @Override
        public void onEntityRemove(@Nonnull Ref<EntityStore> ref, @Nonnull RemoveReason reason,
                                   @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("entity with an InteractionManager REMOVED reason=%s ref=%s", reason, ref);
            if (Boolean.getBoolean("dr.stack")) {
                StackTraceElement[] frames = new Throwable().getStackTrace();
                for (int i = 1; i < Math.min(frames.length, 14); i++) {
                    Log.p("  at %s", frames[i]);
                }
            }
        }
    }

    /** Damage events as they are raised, before the filter group can cancel them. */
    static final class DamageRaised extends com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem {
        @Override
        public com.hypixel.hytale.component.SystemGroup<EntityStore> getGroup() {
            return com.hypixel.hytale.server.core.modules.entity.damage.DamageModule.get().getGatherDamageGroup();
        }

        @Nonnull
        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public void handle(int index, @Nonnull com.hypixel.hytale.component.ArchetypeChunk<EntityStore> chunk, @Nonnull Store<EntityStore> store,
                           @Nonnull CommandBuffer<EntityStore> buffer, @Nonnull com.hypixel.hytale.server.core.modules.entity.damage.Damage damage) {
            if (damage.getSource() instanceof com.hypixel.hytale.server.core.modules.entity.damage.Damage.EntitySource) {
                DAMAGE_RAISED.incrementAndGet();
                Log.p("Damage RAISED on %s amount=%s source=%s", chunk.getReferenceTo(index), damage.getAmount(), damage.getSource());
            }
        }
    }

    /** Every Damage event after the filters have run: what amount reached which entity, and whether a filter cancelled it. */
    static final class DamageSeen extends com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem {
        @Override
        public com.hypixel.hytale.component.SystemGroup<EntityStore> getGroup() {
            return com.hypixel.hytale.server.core.modules.entity.damage.DamageModule.get().getInspectDamageGroup();
        }

        @Nonnull
        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public void handle(int index, @Nonnull com.hypixel.hytale.component.ArchetypeChunk<EntityStore> chunk, @Nonnull Store<EntityStore> store,
                           @Nonnull CommandBuffer<EntityStore> buffer, @Nonnull com.hypixel.hytale.server.core.modules.entity.damage.Damage damage) {
            if (damage.getSource() instanceof com.hypixel.hytale.server.core.modules.entity.damage.Damage.EntitySource && !damage.isCancelled()) {
                DAMAGE_DELIVERED.incrementAndGet();
            }
            Log.p("Damage event on %s amount=%s cancelled=%s source=%s", chunk.getReferenceTo(index), damage.getAmount(),
                damage.isCancelled(), damage.getSource());
        }
    }

    static final class Projectiles extends RefSystem<EntityStore> {
        @Override
        public Query<EntityStore> getQuery() {
            return ProjectileComponent.getComponentType();
        }

        @Override
        public void onEntityAdded(@Nonnull Ref<EntityStore> ref, @Nonnull AddReason reason,
                                  @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("ProjectileComponent ADDED reason=%s ref=%s n=%d", reason, ref, PROJECTILES.incrementAndGet());
        }

        @Override
        public void onEntityRemove(@Nonnull Ref<EntityStore> ref, @Nonnull RemoveReason reason,
                                   @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
        }
    }

    static final class Beams extends RefChangeSystem<EntityStore, BeamComponent> {
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
            Log.p("BeamComponent ADDED ref=%s beams=%d n=%d", ref, component.getBeams().size(), BEAMS_ADDED.incrementAndGet());
        }

        @Override
        public void onComponentSet(@Nonnull Ref<EntityStore> ref, BeamComponent oldComponent,
                                   @Nonnull BeamComponent newComponent, @Nonnull Store<EntityStore> store,
                                   @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("BeamComponent SET ref=%s beams=%d n=%d", ref, newComponent.getBeams().size(), BEAMS_SET.incrementAndGet());
        }

        @Override
        public void onComponentRemoved(@Nonnull Ref<EntityStore> ref, @Nonnull BeamComponent component,
                                       @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
        }
    }
}
