package defpkg;

/** A base class: it owns a codec chain AND the fields two of its subclasses set.
 *
 *  NOTE THE ARITY. `BuilderCodec.abstractBuilder` takes `(Class)` or
 *  `(Class, ParentCodec)` — never a constructor reference, which only
 *  `BuilderCodec.builder(Class, Ctor, ParentCodec)` takes. This file wrote
 *  `abstractBuilder(Base.class, Base::new)` at first; the parser then read
 *  `Base::new` as the parent, a receiver-less name, and the receiver-less branch
 *  silently absorbed it. Every case still passed. A fixture modelling a shape the
 *  corpus does not contain tests the wrong thing, and it hides the branch it was
 *  meant to exercise. Verified against all 96 abstractBuilder call sites in
 *  build-26. */
public class Base {
    public static final BuilderCodec<Base> ABSTRACT_CODEC = BuilderCodec.abstractBuilder(Base.class)
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
