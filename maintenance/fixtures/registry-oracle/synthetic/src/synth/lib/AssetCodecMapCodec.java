/*
 * Synthetic stub: the no-key constructor passes a fixed key to super (the real library says "Type",
 * and this says something else so an assumed default is caught). The keyed one passes its key.
 */
package synth.lib;

public class AssetCodecMapCodec<K, T> extends ACodecMapCodec<K, T, Codec<T>> {
    public AssetCodecMapCodec(Codec<K> idCodec, BiConsumer<T, K> idSetter) {
        super("Form");
    }

    public AssetCodecMapCodec(String key, Codec<K> idCodec, BiConsumer<T, K> idSetter) {
        super(key);
    }
}
