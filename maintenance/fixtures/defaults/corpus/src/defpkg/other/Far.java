package defpkg.other;

import defpkg.core.Anchor;

/** Its parent's simple name is AMBIGUOUS — `Anchor.java` exists in `defpkg/core/`
 *  and `defpkg/decoy/` — and this file lives under neither, so no upward directory
 *  walk can reach the right one. That is the real shape: ten of the gate's classes
 *  name `SimpleBlockInteraction.CODEC`, two files carry that name, and the children
 *  sit under `builtin/adventure/…`, an ancestor of neither. */
public class Far extends Anchor {
    public static final BuilderCodec<Far> CODEC = BuilderCodec.builder(Far.class, Far::new, Anchor.ABSTRACT_CODEC)
        .append(new KeyedCodec<Integer>("Distance", Codec.INT), (o, s) -> {
            o.distance = s.intValue();
        }, o -> Integer.valueOf(o.distance)).add()
        .build();

    private int distance = 42;
}
