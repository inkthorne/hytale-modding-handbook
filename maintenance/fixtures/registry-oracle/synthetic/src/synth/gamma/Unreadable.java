package synth.gamma;

// UNKNOWN key: the key is a constant that lives in another class, which this reader does not
// follow. Counted and pinned, never guessed (a guessed "Disc" here would put its names into the
// wrong key's oracle).
public class Unreadable {
    public static final CodecMapCodec<Unreadable> CODEC = new CodecMapCodec(Other.KEY);

    static {
        CODEC.register("UnreadableName", E9.class, E9.CODEC);
    }
}
