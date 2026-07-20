package hytale.examples.events;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * An ECS event system: runs on the world thread when an entity matching
 * getQuery() fires a BreakBlockEvent. The (index, chunk) pair addresses the
 * breaking entity, so components are read straight off the archetype chunk —
 * no global lookups needed.
 *
 * BreakBlockEvent extends CancellableEcsEvent: call event.setCancelled(true)
 * to veto the break (e.g. region protection).
 */
public class BreakBlockNotifierSystem extends EntityEventSystem<EntityStore, BreakBlockEvent> {

    public BreakBlockNotifierSystem() {
        super(BreakBlockEvent.class);
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk,
                       Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       BreakBlockEvent event) {
        Player player = chunk.getComponent(index, Player.getComponentType());
        if (player == null) {
            return; // an NPC or other non-player entity broke the block
        }
        // Player itself has no sendMessage — chat goes through its PlayerRef.
        player.getPlayerRef().sendMessage(Message.raw(
            "You broke " + event.getBlockType().getId()
                + " at " + event.getTargetBlock().toString()));
    }

    @Override
    public Query<EntityStore> getQuery() {
        // ComponentType implements Query — only entities with a Player
        // component reach handle().
        return Player.getComponentType();
    }
}
