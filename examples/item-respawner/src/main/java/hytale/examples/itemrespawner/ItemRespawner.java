package hytale.examples.itemrespawner;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.UUID;

/**
 * The state that lives on a placed Item Respawner block.
 *
 * <p>Hytale stores per-block data as a <b>block-entity component</b>: a
 * {@link Component} parameterised with {@link ChunkStore} (the ECS store backing
 * chunks and blocks, as opposed to the {@code EntityStore} that holds players,
 * mobs, and dropped items). When the block is placed, the engine creates a
 * block-entity carrying every component listed under
 * {@code BlockType.BlockEntity.Components} in the item JSON — keyed by the name
 * we register the component under (see {@link ItemRespawnerPlugin}). So the JSON
 * key {@code "ItemRespawner"} maps to this class.
 *
 * <p>Persisted fields (via {@link #CODEC}) are the configuration — which
 * {@code Item} to spawn and the {@code IntervalSeconds} delay — plus the UUID of
 * the item we last spawned. Persisting that UUID is what stops the respawner from
 * forgetting (and duplicating) its item when the world reloads: on load it
 * re-finds the still-existing drop by UUID instead of spawning another. The live
 * {@link Ref} is a transient handle valid only within one session.
 */
public class ItemRespawner implements Component<ChunkStore> {

    /**
     * Tells the engine how to read this component from (and write it to) the
     * chunk save. Each persisted field is a {@link KeyedCodec} (JSON key + how to
     * encode its value) paired with a setter and a getter. Fields absent from the
     * data keep the defaults below — so a freshly-placed block starts with none
     * of the runtime UUID.
     */
    public static final BuilderCodec<ItemRespawner> CODEC = BuilderCodec.builder(ItemRespawner.class, ItemRespawner::new)
            .addField(
                    new KeyedCodec<>("Item", Codec.STRING),
                    (ItemRespawner s, String v) -> s.item = v,
                    (ItemRespawner s) -> s.item)
            .addField(
                    new KeyedCodec<>("IntervalSeconds", Codec.INTEGER),
                    (ItemRespawner s, Integer v) -> s.intervalSeconds = v,
                    (ItemRespawner s) -> s.intervalSeconds)
            .addField(
                    new KeyedCodec<>("SpawnedUuid", Codec.UUID_BINARY),
                    (ItemRespawner s, UUID v) -> s.spawnedUuid = v,
                    (ItemRespawner s) -> s.spawnedUuid)
            .build();

    // --- configuration (persisted; editable in-world via the settings GUI) ---
    private String item = "Weapon_Crossbow_Iron";
    private int intervalSeconds = 20;

    // --- identity of the spawned item ---
    // Persisted: the UUID of the drop we last spawned, so we can re-find it after
    // a reload. Assigned lazily (a fresh drop's UUID isn't set until the engine
    // processes it a tick or so later), so it may briefly stay null after a spawn
    // — the transient Ref below covers that window.
    private UUID spawnedUuid;
    // Transient: the live handle to that drop this session. Ref.isValid() flips to
    // false the instant the item is picked up or despawns. Lost on reload.
    private Ref<EntityStore> spawnedRef;

    // Transient: seconds counted up since the item went missing. Starts high so
    // the first tick spawns immediately instead of waiting a full interval.
    private float secondsSinceMissing = Float.MAX_VALUE;

    public ItemRespawner() {
    }

    public String getItem() {
        return item;
    }

    public void setItem(String item) {
        this.item = item;
    }

    public int getIntervalSeconds() {
        return intervalSeconds;
    }

    public void setIntervalSeconds(int intervalSeconds) {
        this.intervalSeconds = intervalSeconds;
    }

    public UUID getSpawnedUuid() {
        return spawnedUuid;
    }

    public void setSpawnedUuid(UUID spawnedUuid) {
        this.spawnedUuid = spawnedUuid;
    }

    public Ref<EntityStore> getSpawnedRef() {
        return spawnedRef;
    }

    public void setSpawnedRef(Ref<EntityStore> spawnedRef) {
        this.spawnedRef = spawnedRef;
    }

    public float getSecondsSinceMissing() {
        return secondsSinceMissing;
    }

    public void setSecondsSinceMissing(float secondsSinceMissing) {
        this.secondsSinceMissing = secondsSinceMissing;
    }

    /**
     * Components must be cloneable — the engine clones the JSON-defined template
     * to make each placed block's own instance. We copy the persisted fields; the
     * transient handle and timer start fresh.
     */
    @Override
    public ItemRespawner clone() {
        ItemRespawner copy = new ItemRespawner();
        copy.item = this.item;
        copy.intervalSeconds = this.intervalSeconds;
        copy.spawnedUuid = this.spawnedUuid;
        return copy;
    }
}
