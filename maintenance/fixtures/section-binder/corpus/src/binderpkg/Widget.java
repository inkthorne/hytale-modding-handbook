package binderpkg;

public class Widget {
    public static final BuilderCodec<Widget> CODEC = ((BuilderCodec.Builder)((BuilderCodec.Builder)
        BuilderCodec.builder(Widget.class, Widget::new)
        .append(new KeyedCodec("Name", Codec.STRING), (w, v) -> {}, w -> null).add())
        .append(new KeyedCodec("Size", Codec.INT, true), (w, v) -> {}, w -> null).add())
        .build();
}
