package hytale.examples.itemrespawner;

import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.CustomPageLifetime;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.OpenCustomUIInteraction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;

/**
 * Entry point: registers the block-entity component, the ticking system, and the
 * settings GUI that brings the Item Respawner block to life.
 *
 * <p>Three registrations make up the whole wiring:
 * <ol>
 *   <li><b>The component.</b> {@code registerComponent} on the <b>chunk-store</b>
 *       registry binds {@link ItemRespawner} to the JSON key {@code "ItemRespawner"}
 *       (the object under {@code BlockType.BlockEntity.Components} in the block
 *       JSON) and returns the {@link ComponentType} handle.</li>
 *   <li><b>The system.</b> {@link ItemRespawnerSystem} ticks over every placed
 *       spawner.</li>
 *   <li><b>The settings page.</b>
 *       {@code OpenCustomUIInteraction.registerBlockEntityCustomPage} binds the
 *       block's {@code Use} → {@code OpenCustomUI} page id {@code "ItemRespawner"}
 *       to {@link ItemRespawnerSettingsPage}. The supplier is handed the targeted
 *       block-entity's {@code Ref}; it reads the block's components off that ref
 *       and constructs the page bound to that specific block.</li>
 * </ol>
 */
public class ItemRespawnerPlugin extends JavaPlugin {

    public ItemRespawnerPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        ComponentType<ChunkStore, ItemRespawner> type = getChunkStoreRegistry()
                .registerComponent(ItemRespawner.class, "ItemRespawner", ItemRespawner.CODEC);

        getChunkStoreRegistry().registerSystem(new ItemRespawnerSystem(type));

        // Bind the block's "Use" (press F) OpenCustomUI page to a settings page
        // built from the targeted block-entity's own components.
        OpenCustomUIInteraction.registerBlockEntityCustomPage(
                this, ItemRespawnerSettingsPage.class, "ItemRespawner",
                (playerRef, blockRef) -> {
                    Store<ChunkStore> chunkStore = blockRef.getStore();
                    BlockModule.BlockStateInfo info =
                            chunkStore.getComponent(blockRef, BlockModule.BlockStateInfo.getComponentType());
                    ItemRespawner state = chunkStore.getComponent(blockRef, type);
                    if (info == null || state == null) {
                        return null;
                    }
                    return new ItemRespawnerSettingsPage(
                            playerRef, info, state, CustomPageLifetime.CanDismissOrCloseThroughInteraction);
                });

        getLogger().atInfo().log("ItemRespawner example plugin loaded!");
    }
}
