package hytale.examples.ui;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.HudComponent;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Toggles HUD components on/off.
 * Usage: /hud <show|hide>
 *
 * <p>This toggles Hytale's <i>built-in</i> HUD pieces (hotbar, health, reticle, ...)
 * via {@code setVisibleHudComponents}, which takes the full set that should be
 * visible — so passing no components hides everything. This is distinct from a
 * <i>custom</i> HUD overlay you draw yourself (see {@link StatusHudCommand}).
 */
public class HudCommand extends AbstractPlayerCommand {

    private enum Mode { show, hide }

    private final RequiredArg<Mode> modeArg;

    public HudCommand() {
        super("hud", "Toggle HUD visibility");
        modeArg = withRequiredArg("mode", "show or hide", ArgTypes.forEnum("mode", Mode.class));
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

        if (mode == Mode.show) {
            player.getHudManager().setVisibleHudComponents(playerRef,
                HudComponent.Hotbar,
                HudComponent.Health,
                HudComponent.Reticle);
            playerRef.sendMessage(Message.raw("HUD components shown"));
        } else {
            // No components in the visible set = everything hidden.
            player.getHudManager().setVisibleHudComponents(playerRef);
            playerRef.sendMessage(Message.raw("HUD components hidden"));
        }
    }
}
