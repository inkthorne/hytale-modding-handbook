package fixturepkg.lib;

// Stub of the codec library's base class: a no-key CodecMapCodec() lands under "Id", as the real
// library's does (ACodecMapCodec.java:51-56). The miner READS this default.
public abstract class ACodecMapCodec<K, T, C> {
    public ACodecMapCodec(Codec<K> keyCodec, boolean allowDefault) {
        this("Id", keyCodec, allowDefault);
    }
}
