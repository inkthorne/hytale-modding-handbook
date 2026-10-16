package synth.gamma;

// The key is a static final String of THIS file, resolved through the per-file constant table.
public class ConstKey {
    static final String KEY = "Konst";
    public static final CodecMapCodec<ConstKey> CODEC = new CodecMapCodec(KEY);

    static {
        CODEC.register("ConstKeyName", E4.class, E4.CODEC);
    }
}
