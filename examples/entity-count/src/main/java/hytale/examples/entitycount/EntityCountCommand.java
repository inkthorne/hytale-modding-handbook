package hytale.examples.entitycount;

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

import java.util.UUID;

/**
 * The {@code /entitycount <show|hide>} command, which turns the HUD overlay on
 * or off for the player who runs it.
 *
 * <p>Notice what this class does NOT do: it never counts anything. Its only job
 * is to create or remove the HUD and remember the choice in {@link HudRegistry}.
 * The live numbers are filled in separately by {@link EntityCountTickingSystem}.
 * Keeping "respond to the player" and "do work every tick" in different classes
 * is a common, tidy way to structure a plugin.
 *
 * <p>We extend {@link AbstractPlayerCommand}, the base class for commands that
 * only make sense when a player runs them (it hands us the player automatically).
 */
public class EntityCountCommand extends AbstractPlayerCommand {

    // The two things a player can type after the command name. Using an enum
    // means Hytale validates the argument for us and even tab-completes it.
    private enum Mode { show, hide }

    private final RequiredArg<Mode> modeArg;
    private final HudRegistry registry;

    public EntityCountCommand(HudRegistry registry) {
        // First argument is the command name (what players type after "/").
        super("entitycount", "Toggle the live entity-count HUD");
        this.registry = registry;

        // Declare a required argument named "mode". Because it is required, the
        // command won't run unless the player provides a valid value.
        modeArg = withRequiredArg("mode", "show or hide", ArgTypes.forEnum("mode", Mode.class));
    }

    // By default Hytale auto-creates a permission for each command, which means
    // only operators can run it. Returning false skips that so any player can try
    // this example. Real plugins usually leave permissions on.
    @Override
    protected boolean canGeneratePermission() {
        return false;
    }

    /**
     * Runs when a player types the command. Hytale gives us several things:
     *
     * @param ctx       the parsed command, used to read arguments
     * @param store     the world's table of all entities and their data
     * @param ref       a handle pointing to the entity that ran the command (the player)
     * @param playerRef a lightweight reference to that player (UUID, messaging, HUD)
     * @param world     the world the player is in
     */
    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                           Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        // Read the "mode" argument the player typed (show or hide).
        Mode mode = ctx.get(modeArg);

        // "ref" points at the player entity; getComponent pulls out its Player
        // data, which is what gives us access to the HUD.
        Player player = store.getComponent(ref, Player.getComponentType());

        // Every player has a unique ID. We use it as the key to track HUDs.
        UUID playerId = playerRef.getUuid();

        switch (mode) {
            case show -> showHud(player, playerRef, playerId);
            case hide -> hideHud(player, playerRef, playerId);
        }
    }

    private void showHud(Player player, PlayerRef playerRef, UUID playerId) {
        // Don't stack a second HUD on top of one already showing.
        if (registry.contains(playerId)) {
            playerRef.sendMessage(Message.raw("Entity-count HUD is already visible"));
            return;
        }

        // Create the overlay and attach it to the player's screen.
        EntityCountHud hud = new EntityCountHud(playerRef);
        player.getHudManager().addCustomHud(playerRef, hud);

        // Remember it so the ticking system knows to update this player's HUD.
        registry.put(playerId, hud);

        playerRef.sendMessage(Message.raw("Entity-count HUD shown — numbers update live"));
    }

    private void hideHud(Player player, PlayerRef playerRef, UUID playerId) {
        // Remove the custom HUD from the player's screen by its key.
        player.getHudManager().removeCustomHud(playerRef, EntityCountHud.KEY);

        // Stop tracking them so the ticking system leaves them alone.
        registry.remove(playerId);

        playerRef.sendMessage(Message.raw("Entity-count HUD hidden"));
    }
}
