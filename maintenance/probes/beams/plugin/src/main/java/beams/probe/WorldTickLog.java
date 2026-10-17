package beams.probe;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import javax.annotation.Nonnull;

/** One line per second of world time while it ticks: proof of life after a fault. */
final class WorldTickLog extends TickingSystem<EntityStore> {
    private long ticks;

    @Override
    public void tick(float dt, int systemIndex, @Nonnull Store<EntityStore> store) {
        if (++ticks % 30 == 0) {
            Log.p("world tick %d world=%s", ticks, store.getExternalData().getWorld().getName());
        }
    }
}
