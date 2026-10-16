package synth.gamma;

// An ENUM in the registering file's own package: constants may take arguments, a body, or an
// annotation, and the list ends at the first top-level `;`.
public enum Mode {
    Alpha(0),
    Beta {
        @Override
        int weight() { return 2; }
    },
    @Deprecated Gamma9,
    Delta9;

    int weight() { return 1; }
}
