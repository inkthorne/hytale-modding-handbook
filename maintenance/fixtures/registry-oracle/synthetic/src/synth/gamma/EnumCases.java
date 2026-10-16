package synth.gamma;

import synth.delta.Level;

// `E.C.name()` ids. Enum.name() is final, so it is exactly the constant's spelling and the site
// is CLOSED when E resolves to an enum declared in the tree and C is one of its constants.
// Everything else stays OPEN (no-name). Names that close: Alpha, Beta, Low, Red.
public class EnumCases {
    public static final CodecMapCodec<EnumCases> CODEC = new CodecMapCodec("Mode3");

    // an enum declared IN THIS FILE and reached by its bare name: no import, no file of its own
    enum Color {
        Red,
        Blue
    }

    static {
        CODEC.register(Mode.Alpha.name(), F1.class, F1.CODEC);         // same package, constant with an argument: closes
        CODEC.register(Mode.Beta.name(), F2.class, F2.CODEC);          // constant with a body: closes
        CODEC.register(Level.Low.name(), F3.class, F3.CODEC);          // through an import: closes
        CODEC.register(Color.Red.name(), F4.class, F4.CODEC);          // nested in this file: closes
        CODEC.register(Mode.Epsilon.name(), F5.class, F5.CODEC);       // Mode has no Epsilon: open
        CODEC.register(Plain.Gamma.name(), F6.class, F6.CODEC);        // Plain is not an enum: open
        CODEC.register(Mode.Gamma9.toString(), F7.class, F7.CODEC);    // toString() is overridable: open
        CODEC.register((Object)Mode.Delta9, F8.class, F8.CODEC);       // through the key codec: open
    }
}
