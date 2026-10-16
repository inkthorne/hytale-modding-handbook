package synth.gamma;

// NOT an enum. It has a static field called Gamma, and an earlier member whose TYPE is also
// spelled Gamma, so a reader that skipped the "is this an enum" check and took the first
// identifier of each comma-separated piece would find Gamma here. Plain.Gamma.name() is
// whatever Plain.name() returns, which is not the field's name.
public class Plain {
    Gamma holder;
    public static final Plain Gamma = new Plain();

    public String name() {
        return "not-the-field-name";
    }
}
