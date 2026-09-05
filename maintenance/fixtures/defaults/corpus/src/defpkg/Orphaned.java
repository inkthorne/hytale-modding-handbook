package defpkg;

/** Its parent does not exist anywhere in the tree. Nothing can resolve this, and
 *  that is the point: the walk must RECORD that it stopped, with a reason. */
public class Orphaned extends Ghost {
    public static final BuilderCodec<Orphaned> CODEC = BuilderCodec.builder(Orphaned.class, Orphaned::new, Ghost.CODEC)
        .append(new KeyedCodec<Integer>("Own", Codec.INT), (o, s) -> {
            o.own = s.intValue();
        }, o -> Integer.valueOf(o.own)).add()
        .build();

    private int own = 5;
}
