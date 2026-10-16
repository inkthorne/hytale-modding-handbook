package synth.gamma;

// AssetCodecMapCodec without a key: its own default ("Form" in synth/lib), not the string family's.
public class AssetDefault {
    public static final AssetCodecMapCodec<String, AssetDefault> CODEC = new AssetCodecMapCodec<String, AssetDefault>(Codec.STRING, (t, k) -> t.id = k);

    static {
        CODEC.register("AssetDefaultName", E7.class, E7.CODEC);
    }
}
