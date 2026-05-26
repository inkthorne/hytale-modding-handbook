package hytale.examples.itemrespawner;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.block.BlockModule;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.WorldChunk;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Runs every tick over each placed Item Respawner block and keeps it stocked: if
 * the previously-spawned item is gone and the configured delay has elapsed, it
 * drops a fresh one on top of the pedestal.
 *
 * <p>This ticks over the {@link ChunkStore} — the same ECS store the engine's own
 * fluid ticker runs on — by extending {@code EntityTickingSystem<ChunkStore>} and
 * registering with {@code getChunkStoreRegistry()} (see {@link ItemRespawnerPlugin}).
 * {@link #getQuery()} restricts the tick to block-entities carrying both our
 * {@link ItemRespawner} component and the engine's {@code BlockStateInfo} (which
 * every placed block-entity has, and which tells us where the block is).
 *
 * <p>The item itself is a dropped-item <i>entity</i>, so it lives in the
 * {@code EntityStore}, reached through the {@link World}. Because this tick
 * mutates the {@code EntityStore}, we keep it single-threaded (see
 * {@link #isParallel}).
 */
public class ItemRespawnerSystem extends EntityTickingSystem<ChunkStore> {

    private final ComponentType<ChunkStore, ItemRespawner> type;
    private final Query<ChunkStore> query;

    public ItemRespawnerSystem(ComponentType<ChunkStore, ItemRespawner> type) {
        this.type = type;
        this.query = Query.and(type, BlockModule.BlockStateInfo.getComponentType());
    }

    @Override
    public Query<ChunkStore> getQuery() {
        return query;
    }

    // We spawn entities into the EntityStore from here, so run on a single thread.
    @Override
    public boolean isParallel(int chunkCount, int entityCount) {
        return false;
    }

    @Override
    public void tick(float deltaTime, int index, ArchetypeChunk<ChunkStore> chunk,
                     Store<ChunkStore> store, CommandBuffer<ChunkStore> buffer) {
        ItemRespawner spawner = chunk.getComponent(index, type);
        if (spawner == null) {
            return;
        }
        BlockModule.BlockStateInfo info = chunk.getComponent(index, BlockModule.BlockStateInfo.getComponentType());
        if (info == null) {
            return;
        }

        // Resolve the block's world coordinates. BlockStateInfo gives a reference
        // to the owning chunk plus the block's packed index within it; ChunkUtil
        // unpacks that index, and we offset x/z by the chunk's world origin.
        Ref<ChunkStore> chunkRef = info.getChunkRef();
        if (!chunkRef.isValid()) {
            return;
        }
        WorldChunk worldChunk = store.getComponent(chunkRef, WorldChunk.getComponentType());
        if (worldChunk == null) {
            return;
        }
        int blockIndex = info.getIndex();
        int x = ChunkUtil.worldCoordFromLocalCoord(worldChunk.getX(), ChunkUtil.xFromBlockInColumn(blockIndex));
        int y = ChunkUtil.yFromBlockInColumn(blockIndex);
        int z = ChunkUtil.worldCoordFromLocalCoord(worldChunk.getZ(), ChunkUtil.zFromBlockInColumn(blockIndex));

        World world = store.getExternalData().getWorld();
        EntityStore entityStore = world.getEntityStore();
        Store<EntityStore> entities = entityStore.getStore();

        // After a reload our transient Ref is gone, but the item itself was saved
        // with the world. Re-acquire it from the persisted UUID so we don't forget
        // — and duplicate — it.
        Ref<EntityStore> ref = spawner.getSpawnedRef();
        if ((ref == null || !ref.isValid()) && spawner.getSpawnedUuid() != null) {
            ref = entityStore.getRefFromUUID(spawner.getSpawnedUuid());
            spawner.setSpawnedRef(ref);
        }

        // "Only if not already present": if our last drop still exists, there's
        // nothing to do. Ref.isValid() is true while the item lives and flips to
        // false once it's picked up or despawns.
        if (ref != null && ref.isValid()) {
            // Capture the UUID for persistence once the engine assigns it to the
            // fresh drop (it's null for a tick or so right after spawning).
            if (spawner.getSpawnedUuid() == null) {
                var uuid = entities.getComponent(ref, com.hypixel.hytale.server.core.entity.UUIDComponent.getComponentType());
                if (uuid != null && uuid.getUuid() != null) {
                    spawner.setSpawnedUuid(uuid.getUuid());
                }
            }
            spawner.setSecondsSinceMissing(0.0f);
            return;
        }

        // The item is gone. Forget it, then count up the delay; respawn only once
        // the interval has elapsed.
        spawner.setSpawnedRef(null);
        spawner.setSpawnedUuid(null);
        float elapsed = spawner.getSecondsSinceMissing() + deltaTime;
        if (elapsed < spawner.getIntervalSeconds()) {
            spawner.setSecondsSinceMissing(elapsed);
            return;
        }

        // Drop the configured item as a pickup, resting on top of the pedestal.
        ItemStack stack = new ItemStack(spawner.getItem(), 1);
        Vector3d position = new Vector3d(x + 0.5, y + 1.1, z + 0.5);
        Holder<EntityStore> drop = ItemComponent.generateItemDrop(
                entities, stack, position, new Rotation3f(), 0.0f, 0.0f, 0.0f);
        if (drop == null) {
            // Bad item id (or empty stack). Back off so we don't spin every tick.
            spawner.setSecondsSinceMissing(0.0f);
            return;
        }
        // Remember the drop so the existence check above can see it's still there.
        // Its UUID gets captured on a later tick, once the engine assigns one.
        spawner.setSpawnedRef(entities.addEntity(drop, AddReason.SPAWN));
        spawner.setSecondsSinceMissing(0.0f);
    }
}
