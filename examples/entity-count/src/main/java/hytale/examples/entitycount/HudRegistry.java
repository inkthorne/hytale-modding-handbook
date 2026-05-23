package hytale.examples.entitycount;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * A simple lookup table of which players currently have the HUD open, keyed by
 * the player's UUID.
 *
 * <p>It connects the two halves of the example: {@link EntityCountCommand} adds
 * and removes entries as players show/hide the HUD, and
 * {@link EntityCountTickingSystem} reads it every tick to find each player's HUD.
 * Both are given the same instance (created in {@link EntityCountPlugin#setup()})
 * so they stay in sync.
 *
 * <p>We use a {@link ConcurrentHashMap} because the command and the ticking
 * system can touch this map from different threads.
 */
public class HudRegistry {

    private final Map<UUID, EntityCountHud> huds = new ConcurrentHashMap<>();

    /** Remembers the HUD now shown for a player. */
    public void put(UUID playerId, EntityCountHud hud) {
        huds.put(playerId, hud);
    }

    /** Returns the player's HUD, or {@code null} if they don't have one open. */
    public EntityCountHud get(UUID playerId) {
        return huds.get(playerId);
    }

    /** Returns {@code true} if the player already has the HUD open. */
    public boolean contains(UUID playerId) {
        return huds.containsKey(playerId);
    }

    /** Forgets the player's HUD (called when they hide it). */
    public void remove(UUID playerId) {
        huds.remove(playerId);
    }
}
