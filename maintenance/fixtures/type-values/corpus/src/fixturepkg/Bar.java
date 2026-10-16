package fixturepkg;

// A registry keyed "Op": a DOMINANT key (the shipped values under it are its registered names),
// so a value under "Op" that nobody registers FAILS, and a Type name filed under "Op" FAILS.
public class Bar {
    public static final CodecMapCodec<Bar> CODEC = new CodecMapCodec("Op");

    public static void setup() {
        Bar.CODEC.register("Plus", PlusBar.class, PlusBar.CODEC);
        Bar.CODEC.register("Minus", MinusBar.class, MinusBar.CODEC);
    }
}
