package hytale.examples.entitycount;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.NPCMarkerComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The heart of the example: code that runs every game tick.
 *
 * <p>A "tick" is the server's heartbeat — it updates the world many times per
 * second (think of it like a frame). To run code on that heartbeat you write a
 * <b>ticking system</b> and register it (see {@link EntityCountPlugin#setup()}).
 *
 * <p>Hytale stores entities using an Entity Component System (ECS). The short
 * version: an entity is just an id, and what it "is" comes from the
 * <b>components</b> attached to it (a {@code Player} component, an
 * {@code NPCMarkerComponent}, and so on). You don't ask "what type is this
 * entity?" — you ask "which components does it have?". That is exactly how we
 * count below.
 *
 * <p>This system extends {@link EntityTickingSystem}. The engine calls our
 * {@link #tick} method once per matching entity, every tick, on the world's own
 * thread — so it is safe to read the entity {@code Store} directly here without
 * worrying about threads.
 *
 * @see EntityCountHud
 */
public class EntityCountTickingSystem extends EntityTickingSystem<EntityStore> {

    // How often to refresh a player's HUD. tick() runs dozens of times a second;
    // updating the on-screen numbers that often would be wasteful, so we batch it
    // down to four times a second.
    private static final float UPDATE_INTERVAL_SECONDS = 0.25f;

    private final HudRegistry registry;

    // Tracks, per player, how much time has passed since we last refreshed their
    // HUD. Used purely for the throttling described above.
    private final Map<UUID, Float> elapsedByPlayer = new ConcurrentHashMap<>();

    public EntityCountTickingSystem(HudRegistry registry) {
        this.registry = registry;
    }

    /**
     * Decides which entities this system runs on. Returning the {@code Player}
     * component type means {@link #tick} is only called for player entities — so
     * "once per tick per online player", which is exactly what we want since each
     * player has their own HUD.
     */
    @Override
    public Query<EntityStore> getQuery() {
        return Player.getComponentType();
    }

    /**
     * Called by the engine once per matching entity, every tick.
     *
     * @param deltaTime seconds since the previous tick (used for throttling)
     * @param index     which entity in the {@code chunk} we are looking at
     * @param chunk     a batch of entities; read this entity's components from it
     * @param store     the world's full table of entities — what we count
     * @param buffer    for queued changes (unused here; we only read)
     */
    @Override
    public void tick(float deltaTime, int index, ArchetypeChunk<EntityStore> chunk,
                     Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        // Get THIS player's id. PlayerRef holds the player's identity and lives on
        // the same entity as the Player component, so we read it from the chunk.
        PlayerRef playerRef = chunk.getComponent(index, PlayerRef.getComponentType());
        if (playerRef == null) {
            return;
        }
        UUID playerId = playerRef.getUuid();

        // Skip players who don't have the HUD open — there's nothing to update.
        EntityCountHud hud = registry.get(playerId);
        if (hud == null) {
            elapsedByPlayer.remove(playerId); // tidy up their throttle timer
            return;
        }

        // Throttle: add up elapsed time and only continue once a quarter-second
        // has passed for this player; otherwise save the time and stop here.
        float elapsed = elapsedByPlayer.getOrDefault(playerId, 0.0f) + deltaTime;
        if (elapsed < UPDATE_INTERVAL_SECONDS) {
            elapsedByPlayer.put(playerId, elapsed);
            return;
        }
        elapsedByPlayer.put(playerId, 0.0f); // reset for the next interval

        // Count entities by asking the store how many carry a given component.
        // This is the ECS idea in action: classify entities by their components.
        int total = store.getEntityCount();                                        // every entity
        int players = store.getEntityCountFor(Player.getComponentType());          // has Player
        int npcs = store.getEntityCountFor(NPCMarkerComponent.getComponentType()); // has NPC marker

        // Whatever is left over: projectiles, dropped items, and internal
        // entities the engine keeps. (max(0, ...) is just a safety net.)
        int other = Math.max(0, total - players - npcs);

        // Hand the numbers to the HUD, which displays them.
        hud.updateCounts(total, players, npcs, other);
    }
}
