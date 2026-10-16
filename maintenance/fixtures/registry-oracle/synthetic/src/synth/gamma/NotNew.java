package synth.gamma;

// UNKNOWN key, the other road: the field is not initialised with `new`, so there is no
// constructor call to read a key from.
public class NotNew {
    public static final CodecMapCodec<NotNew> CODEC = Factories.make();

    static {
        CODEC.register("NotNewName", E10.class, E10.CODEC);
    }
}
