package synth.gamma;

// Two registries in ONE file that both declare TYPE_CODEC, with different keys. The declaration
// is bound to its class chain, so the nested one is not read as the outer one (or the reverse).
public class Pair {
    public static final CodecMapCodec<Pair> TYPE_CODEC = new CodecMapCodec("OuterKey");

    public static class Inner {
        public static final CodecMapCodec<Inner> TYPE_CODEC = new CodecMapCodec("InnerKey");

        static {
            TYPE_CODEC.register("InnerName", E12.class, E12.CODEC);
        }
    }

    static {
        TYPE_CODEC.register("OuterName", E13.class, E13.CODEC);
    }
}
