package hytale.examples.ui;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Toggles a custom status HUD overlay on/off with support for dynamic updates.
 *
 * <p>Usage: /statushud &lt;show|hide|update&gt;
 *
 * <p>This command demonstrates the recommended pattern for managing CustomUIHud instances:
 * <ul>
 *   <li>Store HUD references in a map keyed by player UUID</li>
 *   <li>Access stored HUDs to call update methods</li>
 *   <li>Clean up references when HUD is hidden</li>
 * </ul>
 *
 * <p><b>Important:</b> Only one CustomUIHud can be active per player at a time.
 * Calling {@code setCustomHud()} replaces any existing custom HUD.
 *
 * @see StatusHud
 */
public class StatusHudCommand extends AbstractPlayerCommand {

    private enum Mode { show, hide, update }

    private final RequiredArg<Mode> modeArg;

    /**
     * Stores active HUD references by player UUID.
     *
     * <p>This pattern allows you to:
     * <ul>
     *   <li>Access HUD instances to call update methods like {@link StatusHud#updateStats(int, int)}</li>
     *   <li>Check if a player already has an active HUD</li>
     *   <li>Clean up references when players disconnect or hide their HUD</li>
     * </ul>
     *
     * <p>Uses ConcurrentHashMap for thread-safety as commands may execute concurrently.
     */
    private final Map<UUID, StatusHud> playerHuds = new ConcurrentHashMap<>();

    public StatusHudCommand() {
        super("statushud", "Toggle custom status HUD overlay");
        modeArg = withRequiredArg("mode", "show, hide, or update", ArgTypes.forEnum("mode", Mode.class));
    }

    // Skip the auto-generated permission node so any player can run this example
    // (otherwise it requires op). See commands example's HelloCommand for details.
    @Override
    protected boolean canGeneratePermission() {
        return false;
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        Mode mode = ctx.get(modeArg);
        Player player = store.getComponent(ref, Player.getComponentType());
        UUID playerId = playerRef.getUuid();

        switch (mode) {
            case show -> showHud(player, playerRef, playerId);
            case hide -> hideHud(player, playerRef, playerId);
            case update -> updateHud(playerRef, playerId);
        }
    }

    private void showHud(Player player, PlayerRef playerRef, UUID playerId) {
        // Check if player already has an active HUD
        if (playerHuds.containsKey(playerId)) {
            playerRef.sendMessage(Message.raw("Status HUD is already visible"));
            return;
        }

        // Create and register the HUD
        StatusHud statusHud = new StatusHud(playerRef);
        player.getHudManager().setCustomHud(playerRef, statusHud);

        // Store reference for later updates
        playerHuds.put(playerId, statusHud);

        playerRef.sendMessage(Message.raw("Custom status HUD shown"));
    }

    private void hideHud(Player player, PlayerRef playerRef, UUID playerId) {
        // Remove from HudManager
        player.getHudManager().setCustomHud(playerRef, null);

        // Clean up our reference
        playerHuds.remove(playerId);

        playerRef.sendMessage(Message.raw("Custom status HUD hidden"));
    }

    private void updateHud(PlayerRef playerRef, UUID playerId) {
        StatusHud hud = playerHuds.get(playerId);

        if (hud == null) {
            playerRef.sendMessage(Message.raw("No active HUD. Use '/statushud show' first."));
            return;
        }

        // Demonstrate dynamic update with sample values
        // In a real plugin, you would get these from game state
        int sampleHealth = (int) (Math.random() * 100);
        int sampleMana = (int) (Math.random() * 100);

        hud.updateStats(sampleHealth, sampleMana);
        playerRef.sendMessage(Message.raw("HUD updated - Health: " + sampleHealth + ", Mana: " + sampleMana));
    }

    /**
     * Gets the active StatusHud for a player, if any.
     *
     * <p>This method can be used by other parts of your plugin to access
     * a player's HUD for updates.
     *
     * @param playerId the player's UUID
     * @return the active StatusHud, or null if none is active
     */
    public StatusHud getPlayerHud(UUID playerId) {
        return playerHuds.get(playerId);
    }

    /**
     * Removes a player's HUD reference.
     *
     * <p>Call this when a player disconnects to prevent memory leaks.
     *
     * @param playerId the player's UUID
     */
    public void cleanupPlayer(UUID playerId) {
        playerHuds.remove(playerId);
    }
}
