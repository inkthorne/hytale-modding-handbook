package hytale.examples.inventory;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.RequiredArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Clear inventory sections.
 * Usage: /inv-clear <section>
 * Examples:
 *   /inv-clear all - Clear entire inventory
 *   /inv-clear hotbar - Clear only hotbar
 *   /inv-clear storage - Clear only storage
 *
 * <p>A player's inventory is not one object: each section (hotbar, storage,
 * armor, ...) is a separate component. This example shows the two ways to reach
 * them — a combined view spanning several sections at once
 * ({@code InventoryComponent.getCombined(...)}), or one section's container via
 * its component type ({@code InventoryComponent.Hotbar.getComponentType()}).
 */
public class ClearCommand extends AbstractPlayerCommand {

    private final RequiredArg<String> sectionArg;

    public ClearCommand() {
        super("inv-clear", "Clear inventory sections");
        sectionArg = withRequiredArg("section", "Section to clear (all/hotbar/storage/armor/utility/tools/backpack)", ArgTypes.STRING);
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
        String section = ctx.get(sectionArg).toLowerCase();

        if (section.equals("all")) {
            // EVERYTHING is a combined view over every section; clearing it
            // empties the whole inventory in one call.
            InventoryComponent.getCombined(store, ref, InventoryComponent.EVERYTHING).clear();
            playerRef.sendMessage(Message.raw("Cleared entire inventory"));
            return;
        }

        ItemContainer container = getSectionContainer(store, ref, section);

        if (container == null) {
            playerRef.sendMessage(Message.raw("Unknown section: " + section
                + ". Valid sections: all, hotbar, storage, armor, utility, tools, backpack"));
            return;
        }

        container.clear();
        playerRef.sendMessage(Message.raw("Cleared " + section));
    }

    private ItemContainer getSectionContainer(Store<EntityStore> store, Ref<EntityStore> ref, String section) {
        // Each section is its own component type; getComponent(...).getInventory()
        // returns that section's ItemContainer.
        var type = switch (section) {
            case "hotbar" -> InventoryComponent.Hotbar.getComponentType();
            case "storage" -> InventoryComponent.Storage.getComponentType();
            case "armor" -> InventoryComponent.Armor.getComponentType();
            case "utility" -> InventoryComponent.Utility.getComponentType();
            case "tools" -> InventoryComponent.Tool.getComponentType();
            case "backpack" -> InventoryComponent.Backpack.getComponentType();
            default -> null;
        };
        return type == null ? null : store.getComponent(ref, type).getInventory();
    }
}
