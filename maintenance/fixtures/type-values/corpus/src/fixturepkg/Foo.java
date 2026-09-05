package fixturepkg;

public class Foo {
    public static final CodecMapCodec<Foo> CODEC = new CodecMapCodec("Type");

    public static void setup() {
        Foo.CODEC.register("Alpha", AlphaFoo.class, AlphaFoo.CODEC);
        Foo.CODEC.register("Beta", BetaFoo.class, BetaFoo.CODEC);
    }
}
