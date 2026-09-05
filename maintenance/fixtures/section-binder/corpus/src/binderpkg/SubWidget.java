package binderpkg;

public class SubWidget {
    public static final BuilderCodec<SubWidget> CODEC = ((BuilderCodec.Builder)
        BuilderCodec.builder(SubWidget.class, SubWidget::new, Widget.CODEC)
        .append(new KeyedCodec("Extra", Codec.INT), (w, v) -> {}, w -> null).add())
        .build();
}
