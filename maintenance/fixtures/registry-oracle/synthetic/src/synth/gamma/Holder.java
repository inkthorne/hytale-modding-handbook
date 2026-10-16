package synth.gamma;

// A NESTED interface registered into by its bare name from the class that holds it. The miner
// resolves the receiver `Marker` to synth.gamma.Marker, a file that does not exist; the key is
// then read from the files that register into it, which is where the real
// WorldMapManager.MarkerReference is declared.
public class Holder {
    public interface Marker {
        CodecMapCodec<Marker> CODEC = new CodecMapCodec("MarkKey");
    }

    static void init() {
        Marker.CODEC.register("MarkName", E14.class, E14.CODEC);
    }
}
