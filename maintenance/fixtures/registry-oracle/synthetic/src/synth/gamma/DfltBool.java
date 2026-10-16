package synth.gamma;

// DEFAULT key through the (boolean allowDefault) overload of another family.
public class DfltBool {
    public static final BuilderCodecMapCodec<DfltBool> CODEC = new BuilderCodecMapCodec(true);

    static {
        CODEC.register("DefaultBoolName", E3.class, E3.CODEC);
    }
}
