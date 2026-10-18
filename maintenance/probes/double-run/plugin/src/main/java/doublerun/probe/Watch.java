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
    /** Entities that carry the newer Projectile component (what ProjectileModule.spawnProjectile builds for the Projectile interaction). */
    static final AtomicInteger PROJECTILES_NEW = new AtomicInteger();
    /** BreakBlockEvents raised, whoever breaks (DestroyBlock's performBlockBreak invokes one per call that finds a block). */
    static final AtomicInteger BREAKS = new AtomicInteger();
    static final AtomicInteger BEAMS_ADDED = new AtomicInteger();
    static final AtomicInteger BEAMS_SET = new AtomicInteger();
    /** Teleport components added (ExitInstance queues addComponent(Teleport)). */
    static final AtomicInteger TELEPORTS_ADDED = new AtomicInteger();
    static final AtomicInteger DAMAGE_RAISED = new AtomicInteger();
    static final AtomicInteger DAMAGE_DELIVERED = new AtomicInteger();
    /** Damage events at the TARGET whose source is not an entity (Explode's environment source): raised, and delivered after the filters. */
    static final AtomicInteger DAMAGE_OTHER_RAISED = new AtomicInteger();
    static final AtomicInteger DAMAGE_OTHER_DELIVERED = new AtomicInteger();
    /** The entity whose damage events DAMAGE_OTHER_* count; set by Driver. */
    static volatile Ref<EntityStore> TARGET;

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
            } else if (chunk.getReferenceTo(index).equals(TARGET)) {
                DAMAGE_OTHER_RAISED.incrementAndGet();
                Log.p("Damage RAISED(other) on %s amount=%s source=%s", chunk.getReferenceTo(index), damage.getAmount(), damage.getSource());
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
            } else if (!(damage.getSource() instanceof com.hypixel.hytale.server.core.modules.entity.damage.Damage.EntitySource)
                       && !damage.isCancelled() && chunk.getReferenceTo(index).equals(TARGET)) {
                DAMAGE_OTHER_DELIVERED.incrementAndGet();
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

    static final class ProjectilesNew extends RefSystem<EntityStore> {
        @Override
        public Query<EntityStore> getQuery() {
            return com.hypixel.hytale.server.core.modules.projectile.component.Projectile.getComponentType();
        }

        @Override
        public void onEntityAdded(@Nonnull Ref<EntityStore> ref, @Nonnull AddReason reason,
                                  @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("Projectile (new component) ADDED reason=%s ref=%s n=%d", reason, ref, PROJECTILES_NEW.incrementAndGet());
        }

        @Override
        public void onEntityRemove(@Nonnull Ref<EntityStore> ref, @Nonnull RemoveReason reason,
                                   @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
        }
    }

    static final class Breaks extends com.hypixel.hytale.component.system.EntityEventSystem<EntityStore, com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent> {
        Breaks() {
            super(com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent.class);
        }

        @Override
        public void handle(int index, @Nonnull com.hypixel.hytale.component.ArchetypeChunk<EntityStore> chunk, @Nonnull Store<EntityStore> store,
                           @Nonnull CommandBuffer<EntityStore> buffer, @Nonnull com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent event) {
            Log.p("BreakBlockEvent n=%d block=%s at %s", BREAKS.incrementAndGet(), event.getBlockType().getId(), event.getTargetBlock());
        }

        @Nonnull
        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
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

    static final class Teleports extends RefChangeSystem<EntityStore, com.hypixel.hytale.server.core.modules.entity.teleport.Teleport> {
        @Nonnull
        @Override
        public Query<EntityStore> getQuery() {
            return com.hypixel.hytale.server.core.modules.entity.teleport.Teleport.getComponentType();
        }

        @Nonnull
        @Override
        public ComponentType<EntityStore, com.hypixel.hytale.server.core.modules.entity.teleport.Teleport> componentType() {
            return com.hypixel.hytale.server.core.modules.entity.teleport.Teleport.getComponentType();
        }

        @Override
        public void onComponentAdded(@Nonnull Ref<EntityStore> ref, @Nonnull com.hypixel.hytale.server.core.modules.entity.teleport.Teleport component,
                                     @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
            Log.p("Teleport ADDED ref=%s n=%d", ref, TELEPORTS_ADDED.incrementAndGet());
        }

        @Override
        public void onComponentSet(@Nonnull Ref<EntityStore> ref, com.hypixel.hytale.server.core.modules.entity.teleport.Teleport oldComponent,
                                   @Nonnull com.hypixel.hytale.server.core.modules.entity.teleport.Teleport newComponent, @Nonnull Store<EntityStore> store,
                                   @Nonnull CommandBuffer<EntityStore> buffer) {
        }

        @Override
        public void onComponentRemoved(@Nonnull Ref<EntityStore> ref, @Nonnull com.hypixel.hytale.server.core.modules.entity.teleport.Teleport component,
                                       @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
        }
    }
}
