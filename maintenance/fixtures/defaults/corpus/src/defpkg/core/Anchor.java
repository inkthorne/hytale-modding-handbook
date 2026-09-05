package defpkg.core;

/** The REAL parent for `defpkg.other.Far`. Neither `defpkg/other/` nor `defpkg/`
 *  contains an `Anchor.java`, so no directory walk from the child can reach here;
 *  a decoy of the same simple name sits in `defpkg/decoy/`. The import is the only
 *  evidence, and it is written down in the child. */
public class Anchor {
    public static final BuilderCodec<Anchor> ABSTRACT_CODEC = BuilderCodec.abstractBuilder(Anchor.class)
        .append(new KeyedCodec<Integer>("Depth", Codec.INT), (o, s) -> {
            o.depth = s.intValue();
        }, o -> Integer.valueOf(o.depth)).add()
        .build();

    private int depth = 9;
}
