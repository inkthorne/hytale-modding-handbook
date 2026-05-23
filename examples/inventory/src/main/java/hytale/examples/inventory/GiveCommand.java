package hytale.examples.inventory;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.inventory.transaction.ItemStackTransaction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Give items to the player's inventory.
 * Usage: /give <item> <quantity>
 * Examples:
 *   /give hytale:wooden_sword 1
 *   /give hytale:apple 10
 */
public class GiveCommand extends AbstractPlayerCommand {

    private final RequiredArg<String> itemArg;
    private final RequiredArg<Integer> quantityArg;

    public GiveCommand() {
        super("give", "Add items to your inventory");
        itemArg = withRequiredArg("item", "Item ID (e.g., hytale:wooden_sword)", ArgTypes.STRING);
        quantityArg = withRequiredArg("quantity", "Number of items", ArgTypes.INTEGER);
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
        String itemId = ctx.get(itemArg);
        int quantity = ctx.get(quantityArg);

        if (quantity < 1) {
            playerRef.sendMessage(Message.raw("Quantity must be at least 1"));
            return;
        }

        ItemStack itemStack = new ItemStack(itemId, quantity);

        // Validate item exists
        if (itemStack.getItem() == Item.UNKNOWN) {
            playerRef.sendMessage(Message.raw("Unknown item: " + itemId));
            return;
        }

        // Use combined container that tries hotbar first, then storage
        CombinedItemContainer combined = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_FIRST);
        ItemStackTransaction result = combined.addItemStack(itemStack);

        ItemStack remainder = result.getRemainder();
        int added = quantity - (remainder != null ? remainder.getQuantity() : 0);

        if (added == quantity) {
            playerRef.sendMessage(Message.raw("Added " + quantity + "x " + itemId));
        } else if (added > 0) {
            playerRef.sendMessage(Message.raw("Added " + added + "x " + itemId
                + " (inventory full, " + remainder.getQuantity() + " could not fit)"));
        } else {
            playerRef.sendMessage(Message.raw("Inventory full - could not add items"));
        }
    }
}
