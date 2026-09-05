package defpkg;

/** Its `chain.parent` is a BARE FIELD NAME with no receiver — another codec on this
 *  same class. `partition('.')` turns that into a class name and the walk goes
 *  looking for `ABSTRACT_CODEC.java`, which cannot exist. */
public class Charged {
    public static final BuilderCodec<Charged> ABSTRACT_CODEC = BuilderCodec.abstractBuilder(Charged.class)
        .append(new KeyedCodec<Integer>("Volts", Codec.INT), (o, s) -> {
            o.volts = s.intValue();
        }, o -> Integer.valueOf(o.volts)).add()
        .build();

    public static final BuilderCodec<Charged> CODEC = BuilderCodec.builder(Charged.class, Charged::new, ABSTRACT_CODEC)
        .append(new KeyedCodec<Integer>("Amps", Codec.INT), (o, s) -> {
            o.amps = s.intValue();
        }, o -> Integer.valueOf(o.amps)).add()
        .build();

    private int volts = 240;
    private int amps = 13;
}
