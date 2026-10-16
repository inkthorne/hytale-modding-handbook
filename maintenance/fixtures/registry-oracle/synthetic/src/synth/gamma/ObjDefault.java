package synth.gamma;

// ObjectCodecMapCodec with a Codec first argument: the no-key spelling, so the DEFAULT key.
public class ObjDefault {
    public static final ObjectCodecMapCodec<Mode, ObjDefault> CODEC = new ObjectCodecMapCodec(new EnumCodec<Mode>(Mode.class));

    static {
        CODEC.register("ObjDefaultName", E5.class, E5.CODEC);
    }
}
