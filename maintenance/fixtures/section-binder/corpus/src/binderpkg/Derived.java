package binderpkg;

public class Derived {
    public static final BuilderCodec<Derived> CODEC = ((BuilderCodec.Builder)
        BuilderCodec.builder(Derived.class, Derived::new, Based.ABSTRACT_CODEC)
        .append(new KeyedCodec("Own", Codec.INT), (d, v) -> {}, d -> null).add())
        .build();
}
