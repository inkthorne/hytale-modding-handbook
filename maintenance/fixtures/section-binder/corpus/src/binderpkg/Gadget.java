package binderpkg;

public class Gadget {
    public static final BuilderCodec<Gadget> CODEC = ((BuilderCodec.Builder)
        BuilderCodec.builder(Gadget.class, Gadget::new)
        .append(new KeyedCodec("Colour", Codec.STRING), (g, v) -> {}, g -> null).add())
        .build();
}
