package hytale.examples.commands;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Simplest possible command - no arguments, just sends a message.
 * Usage: /hello
 */
public class HelloCommand extends AbstractPlayerCommand {

    public HelloCommand() {
        super("hello", "Sends a friendly greeting");
    }

    // By default each command auto-generates a permission node (here "hello")
    // that only ops hold (the OP group carries the '*' wildcard), so a normal
    // player gets "no permission". Returning false skips node generation, leaving
    // the command open to everyone. Use requirePermission("...") to gate instead.
    @Override
    protected boolean canGeneratePermission() {
        return false;
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        playerRef.sendMessage(Message.raw("Hello, " + playerRef.getUsername() + "!"));
    }
}
