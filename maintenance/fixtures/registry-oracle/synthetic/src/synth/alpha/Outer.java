/*
 * Synthetic fixture for registry_miner / hand-registry-recount: written by hand,
 * shaped like CFR output, NOT decompiled from the game. Every site below is
 * annotated with what a correct binder must do with it; the expected figures are
 * in maintenance/fixtures/registry-oracle/registries.json under "synthetic".
 */
package synth.alpha;

public class Outer {
    public static final CodecMapCodec<Outer> CODEC = new CodecMapCodec();
    // braces inside a string must not open or close a scope
    static final String BRACES = "}}}{{{";

    static {
        CODEC.register("OuterA", A.class, A.CODEC);
        CODEC.register((Object)"CastLit", B.class, B.CODEC);
    }

    // a nested class registering into the OUTER class's field, which it does not declare
    public static class Inner {
        static void init() {
            CODEC.register("InnerToOuter", C.class, C.CODEC);
        }
    }

    // a nested class declaring its OWN field of the same name: its sites bind to IT
    public static class Own {
        public static final CodecMapCodec<Own> CODEC = new CodecMapCodec();

        static {
            CODEC.register("OwnField", D.class, D.CODEC);
        }

        // doubly nested, declares nothing: binds to Own (the innermost DECLARING class), not Outer
        public static class Deeper {
            static void init() {
                CODEC.register("DeeperToOwn", E.class, E.CODEC);
            }
        }
    }

    // a LOCAL variable shadows the static field: not a registration into it
    static void shadowedByLocal() {
        CodecMapCodec<Outer> CODEC = Outer.makeLocal();
        CODEC.register("ShadowedLocal", F.class, F.CODEC);
    }

    // a PARAMETER shadows it as well
    static void shadowedByParameter(CodecMapCodec<Outer> CODEC) {
        CODEC.register("ShadowedParam", G.class, G.CODEC);
    }

    // the shadow above has ended with its method: this binds to the static field again
    static void notShadowed() {
        CODEC.register("AfterShadow", H.class, H.CODEC);
    }

    // instance receivers are not the static registry
    void viaInstance() {
        this.CODEC.register("ViaThis", I.class, I.CODEC);
        super.CODEC.register("ViaSuper", J.class, J.CODEC);
    }
}
