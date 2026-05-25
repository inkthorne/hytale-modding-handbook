package hytale.examples.itemrespawner;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomPageLifetime;
import com.hypixel.hytale.protocol.packets.interface_.CustomUIEventBindingType;
import com.hypixel.hytale.server.core.entity.entities.player.pages.InteractiveCustomUIPage;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.ui.builder.EventData;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.ui.builder.UIEventBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * The settings GUI opened by pressing F on an Item Respawner block.
 *
 * <p>The block's JSON wires its {@code Use} interaction to
 * {@code OpenCustomUI} with page id {@code "ItemRespawner"};
 * {@link ItemRespawnerPlugin} binds that id to this page, constructing it from
 * the targeted block-entity's {@code BlockStateInfo} and {@link ItemRespawner}
 * component. So this page is always bound to one specific placed block.
 *
 * <p>{@link InteractiveCustomUIPage} handles the round-trip: {@link #build} loads
 * the {@code .ui} layout, seeds each field's value from the component, and binds
 * the Save button to send the field values back; the base then decodes them into
 * an {@link ItemRespawnerSettingsData} (via the codec passed to {@code super})
 * and calls {@link #handleDataEvent}, where we write them onto the component and
 * mark it for saving.
 */
public class ItemRespawnerSettingsPage extends InteractiveCustomUIPage<ItemRespawnerSettingsData> {

    private final BlockModule.BlockStateInfo info;
    private final ItemRespawner state;

    public ItemRespawnerSettingsPage(PlayerRef playerRef, BlockModule.BlockStateInfo info,
                                     ItemRespawner state, CustomPageLifetime lifetime) {
        super(playerRef, lifetime, ItemRespawnerSettingsData.CODEC);
        this.info = info;
        this.state = state;
    }

    @Override
    public void build(Ref<EntityStore> playerRef, UICommandBuilder cmd, UIEventBuilder evt,
                      Store<EntityStore> store) {
        // Load the form layout (path is relative to Common/UI/Custom/).
        cmd.append("Pages/ItemRespawnerSettingsPage.ui");

        // Seed each input with the block's current configuration.
        cmd.set("#Item.Value", state.getItem());
        cmd.set("#IntervalSeconds.Value", (double) state.getIntervalSeconds());

        // On Save, send each input's value back keyed for ItemRespawnerSettingsData.
        EventData data = new EventData()
                .append("@Item", "#Item.Value")
                .append("@IntervalSeconds", "#IntervalSeconds.Value");
        evt.addEventBinding(CustomUIEventBindingType.Activating, "#SaveButton", data);
    }

    @Override
    public void handleDataEvent(Ref<EntityStore> playerRef, Store<EntityStore> store,
                                ItemRespawnerSettingsData data) {
        if (data.getItem() != null && !data.getItem().isBlank()) {
            state.setItem(data.getItem().trim());
        }
        int interval = (int) Math.round(data.getIntervalSeconds());
        if (interval > 0) {
            state.setIntervalSeconds(interval);
        }
        // Persist the edited block-entity state with its chunk. The new values
        // take effect on the next respawn.
        info.markNeedsSaving();
        close();
    }
}
