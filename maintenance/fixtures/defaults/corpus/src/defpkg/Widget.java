package defpkg;

public class Widget extends Base {
    public static final BuilderCodec<Widget> CODEC = BuilderCodec.builder(Widget.class, Widget::new, Base.ABSTRACT_CODEC)
        .append(new KeyedCodec<Double>("Radius", Codec.DOUBLE), (o, s) -> {
            o.radius = s;
        }, o -> o.radius).add()
        .append(new KeyedCodec<Float>("Ratio", Codec.FLOAT), (o, s) -> {
            o.ratio = s.floatValue();
        }, o -> Float.valueOf(o.ratio)).add()
        .append(new KeyedCodec<Integer>("Count", Codec.INT), (o, s) -> {
            o.count = s.intValue();
        }, o -> Integer.valueOf(o.count)).add()
        .append(new KeyedCodec<Boolean>("Enabled", Codec.BOOL), (o, s) -> {
            o.enabled = s.booleanValue();
        }, o -> Boolean.valueOf(o.enabled)).add()
        .append(new KeyedCodec<String>("Name", Codec.STRING), (o, s) -> {
            o.name = s;
        }, o -> o.name).add()
        .append(new KeyedCodec<String>("Mode", Codec.STRING), (o, s) -> {
            o.mode = Mode.valueOf(s);
        }, o -> o.mode.name()).add()
        .append(new KeyedCodec<Double>("Shared", Codec.DOUBLE), (o, s) -> {
            o.shared = s;
        }, o -> o.shared).add()
        .append(new KeyedCodec<Float>("Grace", Codec.FLOAT), (o, s) -> {
            o.graceStart = s.floatValue();
            o.graceEnd = s.floatValue();
        }, o -> Float.valueOf(o.graceStart)).add()
        .append(new KeyedCodec<String>("Quoted", Codec.STRING), (o, s) -> {
            o.quoted = Mode.valueOf(s);
        }, o -> o.quoted.name()).add()
        .append(new KeyedCodec<String>("Cased", Codec.STRING), (o, s) -> {
            o.cased = Target.valueOf(s);
        }, o -> o.cased.name()).add()
        .append(new KeyedCodec<Boolean>("Boxed", Codec.BOOL), (o, s) -> {
            o.boxed = s;
        }, o -> o.boxed).add()
        .append(new KeyedCodec<Integer>("BoxedNum", Codec.INT), (o, s) -> {
            o.boxedNum = s;
        }, o -> o.boxedNum).add()
        .append(new KeyedCodec<String>("Tag", Codec.STRING), Widget::applyTag, o -> o.tag).add()
        .append(new KeyedCodec<String>("Extras", Codec.STRING), (o, s) -> {
            o.extras.add(s);
        }, o -> o.extras).add()
        .build();

    private double radius = 1.5;
    private float ratio = 30.0f;
    private int count;
    private boolean enabled;
    private String name;
    private Mode mode = Mode.Fast;
    private float graceStart = 2.0f;
    private float graceEnd = 9.0f;
    private Mode quoted = Mode.Fast;
    private Target cased = Target.USER;
    private Boolean boxed;
    private Integer boxedNum;
    private String tag = "t";
    private java.util.List<String> extras = new java.util.ArrayList<>();

    private static void applyTag(Widget o, String s) {
        o.tag = s;
    }
}
