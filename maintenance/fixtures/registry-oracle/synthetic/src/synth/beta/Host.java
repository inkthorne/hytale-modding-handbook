/*
 * Synthetic: the cases Java resolves differently from "innermost class declaring the name".
 * Added after the 2026-10-15 review, whose reproduction showed both scripts binding the
 * first five of these to Host.CODEC.
 */
package synth.beta;

public class Host {
    public static final CodecMapCodec<Host> CODEC = new CodecMapCodec();

    static {
        // CONTROL: plainly binds to Host.CODEC
        CODEC.register("Control", A.class, A.CODEC);
    }

    // a nested class that INHERITS a CODEC from Base: Java binds the simple name to
    // Base.CODEC before looking outward, and no rule here finds out, so it is UNRESOLVED
    public static class Inheritor extends Base {
        static void init() {
            CODEC.register("InheritShadowsOuter", B.class, B.CODEC);
        }
    }

    // an anonymous class extending Base: same rule
    static Object anon() {
        return new Base() {
            void f() {
                CODEC.register("AnonShadowsOuter", C.class, C.CODEC);
            }
        };
    }

    // an untyped lambda parameter named CODEC shadows the field, expression body
    static java.util.function.Consumer<CodecMapCodec<Host>> lam() {
        return CODEC -> CODEC.register("LambdaParam", D.class, D.CODEC);
    }

    // ... and block body
    static java.util.function.Consumer<CodecMapCodec<Host>> blockLam() {
        return CODEC -> {
            CODEC.register("BlockLambdaParam", D.class, D.CODEC);
        };
    }

    // the lambda's parameter is out of scope once its statement ends: binds to Host
    static void afterLambda() {
        java.util.function.Consumer<Object> c = CODEC -> CODEC.hashCode();
        CODEC.register("AfterLambda", E.class, E.CODEC);
    }

    // a registration spelled in a comment is not a registration:
    // CODEC.register("InComment", E.class, E.CODEC);
    /* nor in a block comment: CODEC.register("InBlockComment", E.class, E.CODEC); */

    // nor in a string literal
    static final String DOC = "CODEC.register(\"InString\", F.class, F.CODEC);";

    // a local in a SIBLING block that has already closed does not shadow
    static void sibling() {
        {
            CodecMapCodec<Host> CODEC = null;
        }
        CODEC.register("AfterSiblingBlock", G.class, G.CODEC);
    }

    // a local in an ENCLOSING block (not the innermost one) does shadow
    static void enclosing(boolean flag) {
        CodecMapCodec<Host> CODEC = null;
        if (flag) {
            CODEC.register("EnclosingBlockLocal", H.class, H.CODEC);
        }
    }
}
