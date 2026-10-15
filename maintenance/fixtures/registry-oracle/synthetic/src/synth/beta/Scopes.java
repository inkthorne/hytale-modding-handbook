package synth.beta;

// Scopes that end, and scopes that never open a block (added after the second review pass).
public class Scopes {
    public static final CodecMapCodec<Scopes> CODEC = new CodecMapCodec();

    // lambda parameters in FIELD INITIALISERS, where no block exists to carry the check:
    // untyped, multi-parameter, typed. All three shadow the field: excluded
    static java.util.function.Consumer<CodecMapCodec<Scopes>> a = CODEC -> CODEC.register("UntypedLambdaInField", A.class, A.CODEC);
    static java.util.function.BiConsumer<Object, CodecMapCodec<Scopes>> b = (x, CODEC) -> CODEC.register("MultiLambdaInField", A.class, A.CODEC);
    static java.util.function.Consumer<CodecMapCodec<Scopes>> c = (CodecMapCodec<Scopes> CODEC) -> CODEC.register("TypedLambdaInField", A.class, A.CODEC);

    static void typedLambdaInMethod() {
        java.util.function.Consumer<CodecMapCodec<Scopes>> d = (CodecMapCodec<Scopes> CODEC) -> CODEC.register("TypedLambdaInMethod", B.class, B.CODEC);
        // the typed lambda's parameter ended with its body: this binds to the field
        CODEC.register("AfterTypedLambda", B.class, B.CODEC);
    }

    static void catchParameter() {
        try {
            run();
        } catch (RuntimeException CODEC) {
            CODEC.register("CatchParam", C.class, C.CODEC);
        }
        // a catch parameter is scoped to its block: this binds to the field
        CODEC.register("AfterCatch", C.class, C.CODEC);
    }

    // a text block holds quotes and newlines; the registration spelled in it is not one. The
    // two lines matter: the first is visible to a masker that stops string contents at a line end,
    // the second (its stray quote) to one that lets strings span lines, because the pairing shifts
    // by one and the call lands outside any string
    static final String DOC = """
        say CODEC.register("InTextBlockA", D.class, D.CODEC);
        say" CODEC.register("InTextBlockB", D.class, D.CODEC);
        """;

    static {
        CODEC.register("AfterTextBlock", D.class, D.CODEC);
    }
}
