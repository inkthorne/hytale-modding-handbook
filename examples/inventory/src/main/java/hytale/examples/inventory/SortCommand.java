package hytale.examples.inventory;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.Inventory;
import com.hypixel.hytale.server.core.inventory.container.SortType;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Sort the storage inventory.
 * Usage: /sort <type>
 * Examples:
 *   /sort name - Sort alphabetically
 *   /sort type - Sort by item type
 *   /sort rarity - Sort by rarity
 */
public class SortCommand extends AbstractPlayerCommand {

    private final RequiredArg<String> sortTypeArg;

    public SortCommand() {
        super("sort", "Sort storage inventory");
        sortTypeArg = withRequiredArg("type", "Sort type (name/type/rarity)", ArgTypes.STRING);
    }

    @Override
    protected void execute(CommandContext ctx, Store<EntityStore> store,
                          Ref<EntityStore> ref, PlayerRef playerRef, World world) {
        String sortTypeStr = ctx.get(sortTypeArg).toUpperCase();

        SortType sortType;
        try {
            sortType = SortType.valueOf(sortTypeStr);
        } catch (IllegalArgumentException e) {
            playerRef.sendMessage(Message.raw("Unknown sort type: " + sortTypeStr.toLowerCase()
                + ". Valid types: name, type, rarity"));
            return;
        }

        Player player = store.getComponent(ref, Player.getComponentType());
        Inventory inventory = player.getInventory();

        inventory.getStorage().sortItems(sortType);
        playerRef.sendMessage(Message.raw("Sorted storage by " + sortType.name().toLowerCase()));
    }
}
