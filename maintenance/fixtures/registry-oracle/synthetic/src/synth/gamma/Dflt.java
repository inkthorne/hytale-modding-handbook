package synth.gamma;

// DEFAULT key: no argument. The family's default is READ from synth/lib/ACodecMapCodec.java
// ("Disc"), which is not the real library's "Id".
public class Dflt {
    public static final CodecMapCodec<Dflt> CODEC = new CodecMapCodec();

    static {
        CODEC.register("DefaultName", E2.class, E2.CODEC);
    }
}
