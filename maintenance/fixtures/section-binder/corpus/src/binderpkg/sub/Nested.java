package binderpkg.sub;

public class Nested {
    public static final BuilderCodec<Nested> CODEC = ((BuilderCodec.Builder)
        BuilderCodec.builder(Nested.class, Nested::new)
        .append(new KeyedCodec("Depth", Codec.INT), (n, v) -> {}, n -> null).add())
        .build();
}
