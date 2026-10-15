package synth.beta;

public class Multi {
    // two declarators in one static declaration: CODEC is the SECOND, and is static
    public static final CodecMapCodec<Multi> OTHER_CODEC = new CodecMapCodec(), CODEC = new CodecMapCodec();
    // an INSTANCE field named like a codec: a real registry field, but not the static one
    private final CodecMapCodec<Multi> ITEM_CODEC = new CodecMapCodec();

    static {
        CODEC.register("MultiDeclarator", A.class, A.CODEC);
    }

    void inst() {
        ITEM_CODEC.register("InstanceField", B.class, B.CODEC);
    }
}
