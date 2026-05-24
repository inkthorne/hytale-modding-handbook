package hytale.examples.ui;

import hytale.examples.ui.pages.SimpleMenuPage;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Opens a custom UI page for the player.
 * Usage: /menu
 *
 * <p>A "page" is a full-screen interface the player opens and dismisses (unlike a
 * HUD overlay, which stays on screen during play — see {@link StatusHudCommand}).
 * Pages are shown through the player's page manager; the page itself decides what
 * to draw and when it can be closed (here, {@code CanDismiss} / press ESC).
 */
public class MenuCommand extends AbstractPlayerCommand {

    public MenuCommand() {
        super("menu", "Opens a custom menu");
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
        Player player = store.getComponent(ref, Player.getComponentType());
        SimpleMenuPage page = new SimpleMenuPage(playerRef);
        // Hand the page to the player's page manager to display it.
        player.getPageManager().openCustomPage(ref, store, page);
    }
}
