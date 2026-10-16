package synth.gamma;

// FORM 3: registerCoreComponentType. Not a codec; the key is the type tag of the BuilderFactory,
// BuilderFactory.DEFAULT_TYPE ("Variant" in synth/lib), and the factory below is built with that
// literal so the recount can read the same fact by a route that does not go through the constant.
public class Form3 {
    static void init(NPCPlugin plugin) {
        plugin.registerCoreComponentType("WidgetName", BuilderWidget::new);
    }

    static BuilderFactory<Widget> factory() {
        return new BuilderFactory<Widget>(Widget.class, "Variant");
    }
}
