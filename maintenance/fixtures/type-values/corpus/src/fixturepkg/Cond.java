package fixturepkg;

// The "Id" decision, in miniature. `new CodecMapCodec()` takes the default key, read from the
// stub in lib/ as "Id". "Id" is also the plain id field of every asset, so it is a MIXED key:
// `"Id": "Alive2"` is CONFIRMED here and `"Id": "Workbench"` (an ordinary id) is UNCHECKED.
public class Cond {
    public static final CodecMapCodec<Cond> CODEC = new CodecMapCodec();

    public static void setup() {
        Cond.CODEC.register("Alive2", AliveCond.class, AliveCond.CODEC);
    }
}
