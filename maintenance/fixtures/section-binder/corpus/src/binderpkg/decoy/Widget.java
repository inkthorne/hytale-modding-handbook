package binderpkg.decoy;

// A DECOY: same simple name as binderpkg.Widget, no codec. Its only job is to make
// `Widget` ambiguous by filename, which is how the real parent walk failed —
// two SimpleInteraction.java exist (protocol and interaction.config), so a
// unique-filename lookup refused to resolve and the walk stopped at the first hop.
public class Widget {
    public int unrelated;
}
