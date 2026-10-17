package beams.probe;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.server.core.modules.interaction.InteractionModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import javax.annotation.Nonnull;

/** Logs why an entity with an InteractionManager (the probe's host) is removed. */
final class HostWatch extends RefSystem<EntityStore> {
    @Override
    public Query<EntityStore> getQuery() {
        return InteractionModule.get().getInteractionManagerComponent();
    }

    @Override
    public void onEntityAdded(@Nonnull Ref<EntityStore> ref, @Nonnull AddReason reason,
                              @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
        Log.p("InteractionManager entity ADDED reason=%s ref=%s", reason, ref);
    }

    @Override
    public void onEntityRemove(@Nonnull Ref<EntityStore> ref, @Nonnull RemoveReason reason,
                               @Nonnull Store<EntityStore> store, @Nonnull CommandBuffer<EntityStore> buffer) {
        Log.p("InteractionManager entity REMOVED reason=%s ref=%s", reason, ref);
        if (Boolean.getBoolean("beams.probe.stack")) {
            StackTraceElement[] frames = new Throwable().getStackTrace();
            for (int i = 1; i < Math.min(frames.length, 12); i++) {
                Log.p("  at %s", frames[i]);
            }
        }
    }
}
