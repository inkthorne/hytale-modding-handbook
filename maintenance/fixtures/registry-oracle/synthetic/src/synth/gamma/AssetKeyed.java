package synth.gamma;

// AssetCodecMapCodec with a key as its first argument.
public class AssetKeyed {
    public static final AssetCodecMapCodec<String, AssetKeyed> CODEC = new AssetCodecMapCodec<String, AssetKeyed>("Opx", Codec.STRING, (t, k) -> t.id = k);

    static {
        CODEC.register("AssetKeyedName", E8.class, E8.CODEC);
    }
}
