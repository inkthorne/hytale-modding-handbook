package synth.alpha;

// Shapes NEITHER spelling covers. They are counted (RESIDUE), never mined: a miner that
// silently skipped them would report a clean run over registrations it cannot see.
public class Residue {
    void held(PluginBase plugin) {
        // a registry held in a variable, then registered through the variable
        var registry = plugin.getCodecRegistry(Outer.CODEC);
        registry.register("ViaVariable", S.class, S.CODEC);
    }

    void computedArgument(PluginBase plugin) {
        // the argument is not a field: which registry this is cannot be read off the text
        plugin.getCodecRegistry(Residue.pick()).register("ViaCall", T.class, T.CODEC);
    }

    // a method that TAKES a codec is a declaration, not a registration
    <A> MapRegistry<A> getCodecRegistry(StringCodecMapCodec<A, ?> mapCodec) {
        return null;
    }
}
