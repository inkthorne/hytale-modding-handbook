package synth.beta;

public class InstShadow {
    public static final CodecMapCodec<InstShadow> CODEC = new CodecMapCodec();

    // a nested class with an INSTANCE field of the same name: Java binds the simple name
    // to that field, not to InstShadow.CODEC, so the call is excluded (instance-field)
    public class Inner {
        private final CodecMapCodec<Inner> CODEC = new CodecMapCodec();

        void init() {
            CODEC.register("InstanceShadowsOuter", A.class, A.CODEC);
        }
    }
}
