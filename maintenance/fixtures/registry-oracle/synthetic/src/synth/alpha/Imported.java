package synth.alpha;

import static synth.alpha.Outer.CODEC;

// CODEC is a STATIC IMPORT: no enclosing class declares it, and nothing here inherits, so the
// walk reaches the top and the site is UNRESOLVED (a different road to the same verdict).
public class Imported {
    static {
        CODEC.register("ViaStaticImport", S.class, S.CODEC);
    }
}
