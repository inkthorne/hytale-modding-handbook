package binderpkg;

public class Based {
    // The parent's codec field is NOT called CODEC. Interaction.ABSTRACT_CODEC is
    // the real case: a walk that keeps the receiver and drops the field name parses
    // the wrong field, or none.
    public static final BuilderCodec<Based> ABSTRACT_CODEC = ((BuilderCodec.Builder)
        BuilderCodec.builder(Based.class, Based::new)
        .append(new KeyedCodec("Inherited", Codec.STRING), (b, v) -> {}, b -> null).add())
        .build();
}
