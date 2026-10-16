package synth.gamma;

// MapKeyMapCodec: the registered names are the JSON object's KEYS. There is no discriminator
// key, so it is neither a key nor UNKNOWN.
public class MapKeyed {
    public static final MapKeyMapCodec<MapKeyed> PLUGIN_CODEC = new MapKeyMapCodec(true);

    static {
        PLUGIN_CODEC.register(E11.class, "MapKeyedName", E11.CODEC);
    }
}
