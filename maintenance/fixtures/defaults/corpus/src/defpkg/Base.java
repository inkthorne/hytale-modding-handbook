package defpkg;

/** A base class: it owns a codec chain AND the fields two of its subclasses set. */
public class Base {
    public static final BuilderCodec<Base> ABSTRACT_CODEC = BuilderCodec.abstractBuilder(Base.class, Base::new)
        .append(new KeyedCodec<String>("Label", Codec.STRING), (o, s) -> {
            o.label = s;
        }, o -> o.label).add()
        .append(new KeyedCodec<Integer>("Retries", Codec.INT), (o, s) -> {
            o.retries = s.intValue();
        }, o -> Integer.valueOf(o.retries)).add()
        .build();

    private String label = "base";
    private int retries = 3;
    /** Declared here, set by a SUBCLASS's chain — the walk must search every hop
     *  for the field, not only the hop whose chain named the key. */
    protected double shared;
}
