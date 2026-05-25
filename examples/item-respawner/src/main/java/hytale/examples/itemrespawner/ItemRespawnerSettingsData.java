package hytale.examples.itemrespawner;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * The typed payload submitted by the settings GUI's Save button.
 *
 * <p>{@link InteractiveCustomUIPage} decodes the form submission into one of
 * these using {@link #CODEC}. Each codec key is the {@code @}-prefixed name the
 * page binds a UI element's value to (see
 * {@code ItemRespawnerSettingsPage.build}): the Save button sends
 * {@code #Item.Value} as {@code @Item} and {@code #IntervalSeconds.Value} as
 * {@code @IntervalSeconds}. The interval arrives as a double (number fields are
 * numeric) and is rounded to a whole number of seconds when applied.
 */
public class ItemRespawnerSettingsData {

    public static final BuilderCodec<ItemRespawnerSettingsData> CODEC =
            BuilderCodec.builder(ItemRespawnerSettingsData.class, ItemRespawnerSettingsData::new)
                    .addField(
                            new KeyedCodec<>("@Item", Codec.STRING),
                            (ItemRespawnerSettingsData d, String v) -> d.item = v,
                            (ItemRespawnerSettingsData d) -> d.item)
                    .addField(
                            new KeyedCodec<>("@IntervalSeconds", Codec.DOUBLE),
                            (ItemRespawnerSettingsData d, Double v) -> d.intervalSeconds = v,
                            (ItemRespawnerSettingsData d) -> d.intervalSeconds)
                    .build();

    private String item = "";
    private double intervalSeconds;

    public ItemRespawnerSettingsData() {
    }

    public String getItem() {
        return item;
    }

    public double getIntervalSeconds() {
        return intervalSeconds;
    }
}
