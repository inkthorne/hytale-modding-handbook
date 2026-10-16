package synth.gamma;

// Discriminator key cases. Each class holds ONE registry and registers a single name into it
// with the bare spelling. Expected (key, how) is in registries.json under "synthetic".
//
// EXPLICIT key: the first argument is a string literal.
public class Explicit {
    public static final CodecMapCodec<Explicit> CODEC = new CodecMapCodec("Mode");

    static {
        CODEC.register("ExplicitName", E1.class, E1.CODEC);
    }
}
