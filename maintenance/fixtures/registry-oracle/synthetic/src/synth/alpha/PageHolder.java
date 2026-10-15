package synth.alpha;

public class PageHolder {
    public static final CodecMapCodec<PageSupplier> PAGE_CODEC = new CodecMapCodec();

    // form 2, unqualified; the id is a parameter (indirect), and the second statement CHAINS
    public static void registerPage(PluginBase plugin, String id, PageSupplier supplier) {
        plugin.getCodecRegistry(PAGE_CODEC).register(id, supplier.getClass(), BuilderCodec.builder(L.class, () -> supplier).build());
    }

    public static void registerTwo(PluginBase plugin) {
        plugin.getCodecRegistry(PAGE_CODEC).register("Chained", M.class, M.CODEC).register("Chained2", N.class, N.CODEC);
    }
}
