package synth.alpha;

// CODEC is INHERITED from Outer. There is no superclass rule, so this site is UNRESOLVED:
// reported, never entered into Outer.CODEC.
public class Child
extends Outer {
    static {
        CODEC.register("Inherited", R.class, R.CODEC);
    }
}
