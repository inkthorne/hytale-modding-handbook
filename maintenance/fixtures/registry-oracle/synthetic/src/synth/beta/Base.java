package synth.beta;

public class Base {
    public static final CodecMapCodec<Base> CODEC = new CodecMapCodec();

    static {
        Base.CODEC.register("BaseQualified", Z.class, Z.CODEC);
    }
}
