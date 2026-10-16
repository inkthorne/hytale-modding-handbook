/*
 * Synthetic stub of the codec library's base class. registry_miner READS the default
 * discriminator key from the delegating constructor below; the real library's
 * default is "Id", and this stub deliberately says "Disc" so that a miner which assumed "Id"
 * would come out wrong here instead of right by coincidence.
 */
package synth.lib;

public abstract class ACodecMapCodec<K, T, C> {
    public ACodecMapCodec(Codec<K> keyCodec) {
        this(keyCodec, false);
    }

    public ACodecMapCodec(Codec<K> keyCodec, boolean allowDefault) {
        this("Disc", keyCodec, allowDefault);
    }

    public ACodecMapCodec(String key, Codec<K> keyCodec, boolean allowDefault) {
        this.key = key;
    }
}
