package synth.gamma;

// ObjectCodecMapCodec with a string first argument: that is the key.
public class ObjKeyed {
    public static final ObjectCodecMapCodec<String, ObjKeyed> CODEC = new ObjectCodecMapCodec("Op2", new StringOrBlank(), true, false);

    static {
        CODEC.register("ObjKeyedName", E6.class, E6.CODEC);
    }
}
