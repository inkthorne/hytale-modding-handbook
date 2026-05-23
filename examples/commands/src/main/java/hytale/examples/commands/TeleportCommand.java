package hytale.examples.commands;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.math.vector.Vector3d;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.arguments.types.RelativeDoublePosition;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;

/**
 * Command with a position argument demonstrating argument parsing.
 * Usage: /tp <x> <y> <z>
 * Supports relative coordinates: /tp ~10 ~ ~-5
 */
public class TeleportCommand extends AbstractPlayerCommand {

    private final RequiredArg<RelativeDoublePosition> positionArg;

    public TeleportCommand() {
        super("tp", "Teleport to a position");
        positionArg = withRequiredArg("position", "Target position", ArgTypes.RELATIVE_POSITION);
    }

    // Skip the auto-generated permission node so any player can run this example
    // (otherwise it requires op). See HelloCommand for the full rationale.
    @Override
    protected boolean canGeneratePermission() {
        return false;
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        RelativeDoublePosition relPos = ctx.get(positionArg);
        Transform current = playerRef.getTransform();
        Vector3d targetPos = relPos.getRelativePosition(current.getPosition(), world);

        // Add Teleport component - processed by TeleportSystems to actually move the player
        Teleport teleport = Teleport.createForPlayer(world, targetPos, current.getRotation());
        store.addComponent(ref, Teleport.getComponentType(), teleport);

        playerRef.sendMessage(Message.raw("Teleported to " + formatPosition(targetPos)));
    }

    private String formatPosition(Vector3d pos) {
        return String.format("%.1f, %.1f, %.1f", pos.getX(), pos.getY(), pos.getZ());
    }
}
