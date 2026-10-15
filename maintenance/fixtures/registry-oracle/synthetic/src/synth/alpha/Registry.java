package synth.alpha;

// interface fields are implicitly static: no `static` appears on the declaration
public interface Registry {
    CodecMapCodec<Registry> CODEC = new CodecMapCodec();

    public static void init() {
        CODEC.register(Priority.DEFAULT, (Object)"", O.class, O.BASE_CODEC);
        CODEC.register("IfaceField", P.class, P.CODEC);
        CODEC.register(Slot.Core.name(), Q.class, Q.CODEC);
    }
}
