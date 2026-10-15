import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.JsonAsset;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.ExtraInfo;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.builder.BuilderField;
import com.hypixel.hytale.codec.codecs.map.MapCodec;
import com.hypixel.hytale.codec.record.RecordCodec;
import com.hypixel.hytale.codec.util.RawJsonReader;
import com.hypixel.hytale.codec.validation.Validators;
import com.hypixel.hytale.logger.HytaleLogger;
import org.bson.BsonDocument;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.Callable;
import java.util.function.*;

/**
 * Live measurement of what "required" means for a codec key, against the installed
 * HytaleServer.jar.  See maintenance/probes/requiredness/run.sh and
 * maintenance/registry-oracle-notes.md (requiredness section).
 *
 * Every configuration is one key "A" on a freshly built codec.  Each is decoded on four
 * paths with three documents.  A cell records exactly what came back: an exception
 * (type + first line of message) or the decoded value.
 *
 *   P1  asset JSON   AssetBuilderCodec.decodeJsonAsset (parent = null) then
 *                    ExtraInfo.getValidationResults().logOrThrowValidatorExceptions,
 *                    the sequence AssetStore.decode runs
 *   P2  BuilderCodec.decode(BsonValue, ExtraInfo)
 *   P3  BuilderCodec.decodeAndInherit(BsonDocument, null parent, ExtraInfo)
 *   P4  BuilderCodec.decodeJson(RawJsonReader, ExtraInfo)
 *
 * Exit 0 = matrix printed and every pinned expectation held.
 * Exit 2 = the negative control did not reproduce the defect: the run is VOID.
 * Exit 1 = a pinned expectation changed (the game's behaviour moved).
 */
public class RequirednessProbe {

    public static class Doc implements JsonAsset<String> {
        public String id;
        public AssetExtraInfo.Data data;
        public String s;
        public Integer i;
        public String[] arr;
        public Map<String, String> map;
        public String getId() { return id; }
    }

    public record RecS(String a) {}
    public record RecI(int a) {}

    enum Kind { STRING, INTEGER, ARRAY, MAP }
    enum Val { NONE, NONNULL, NONEMPTY_ARRAY, NONEMPTY_MAP, NN_ELEMENTS }

    record Config(String id, String desc, Kind kind, boolean flag, Val val, boolean preset) {}

    /** -Dprobe.sabotage=1 silently drops every nonNull: the negative control must then report VOID (exit 2). */
    static final boolean SABOTAGE = System.getProperty("probe.sabotage") != null;

    static final String[] DOCS = {"missing", "null", "value"};

    static String doc(Kind k, String which) {
        return switch (which) {
            case "missing" -> "{}";
            case "null" -> "{\"A\": null}";
            default -> switch (k) {
                case STRING -> "{\"A\": \"x\"}";
                case INTEGER -> "{\"A\": 5}";
                case ARRAY -> "{\"A\": [\"x\"]}";
                case MAP -> "{\"A\": {\"k\": \"v\"}}";
            };
        };
    }

    // ---- building a one-key codec -----------------------------------------------------

    @SuppressWarnings({"unchecked", "rawtypes"})
    static BuilderCodec<Doc> build(Config c, boolean asset, boolean inherited) {
        KeyedCodec kc;
        BiConsumer set;
        Function get;
        Consumer<Doc> preset;
        switch (c.kind) {
            case STRING -> {
                kc = new KeyedCodec<String>("A", Codec.STRING, c.flag);
                set = (BiConsumer<Doc, String>) (d, v) -> d.s = v;
                get = (Function<Doc, String>) d -> d.s;
                preset = d -> d.s = "preset";
            }
            case INTEGER -> {
                kc = new KeyedCodec<Integer>("A", Codec.INTEGER, c.flag);
                set = (BiConsumer<Doc, Integer>) (d, v) -> d.i = v;
                get = (Function<Doc, Integer>) d -> d.i;
                preset = d -> d.i = 7;
            }
            case ARRAY -> {
                kc = new KeyedCodec<String[]>("A", Codec.STRING_ARRAY, c.flag);
                set = (BiConsumer<Doc, String[]>) (d, v) -> d.arr = v;
                get = (Function<Doc, String[]>) d -> d.arr;
                preset = d -> d.arr = new String[] {"preset"};
            }
            default -> {
                kc = new KeyedCodec<Map<String, String>>("A",
                        new MapCodec<String, HashMap<String, String>>(Codec.STRING, HashMap::new), c.flag);
                set = (BiConsumer<Doc, Map<String, String>>) (d, v) -> d.map = v;
                get = (Function<Doc, Map<String, String>>) d -> d.map;
                preset = d -> d.map = new HashMap<>(Map.of("preset", "v"));
            }
        }
        final BiConsumer fset = set;
        final Function fget = get;
        final Consumer<Doc> fpreset = preset;
        final boolean usePreset = c.preset;
        Supplier<Doc> sup = () -> {
            Doc d = new Doc();
            if (usePreset) fpreset.accept(d);
            return d;
        };
        BiConsumer<Doc, Doc> inherit = (t, p) -> fset.accept(t, fget.apply(p));

        if (asset) {
            AssetBuilderCodec.Builder b = AssetBuilderCodec.builder(Doc.class, sup, Codec.STRING,
                    (BiConsumer<Doc, String>) (d, k) -> d.id = k, (Function<Doc, String>) d -> d.id,
                    (BiConsumer<Doc, AssetExtraInfo.Data>) (d, x) -> d.data = x,
                    (Function<Doc, AssetExtraInfo.Data>) d -> d.data);
            BuilderField.FieldBuilder fb = inherited
                    ? b.appendInherited(kc, fset, fget, inherit)
                    : b.append(kc, fset, fget);
            addValidator(fb, c.val).add();
            return b.build();
        }
        BuilderCodec.Builder b = BuilderCodec.builder(Doc.class, sup);
        BuilderField.FieldBuilder fb = inherited
                ? b.appendInherited(kc, fset, fget, inherit)
                : b.append(kc, fset, fget);
        addValidator(fb, c.val).add();
        return b.build();
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static BuilderField.FieldBuilder addValidator(BuilderField.FieldBuilder fb, Val v) {
        return switch (v) {
            case NONE -> fb;
            case NONNULL -> SABOTAGE ? fb : fb.addValidator(Validators.nonNull());
            case NONEMPTY_ARRAY -> fb.addValidator(Validators.nonEmptyArray());
            case NONEMPTY_MAP -> fb.addValidator(Validators.nonEmptyMap());
            case NN_ELEMENTS -> fb.addValidator(Validators.nonNullArrayElements());
        };
    }

    // ---- cells ------------------------------------------------------------------------

    static String show(Object o) {
        if (o == null) return "null";
        if (o instanceof Object[] a) return Arrays.toString(a);
        return String.valueOf(o);
    }

    static String describe(Doc d, Kind k) {
        return switch (k) {
            case STRING -> "A=" + show(d.s);
            case INTEGER -> "A=" + show(d.i);
            case ARRAY -> "A=" + show(d.arr);
            case MAP -> "A=" + show(d.map);
        };
    }

    static String first(Throwable t) {
        Throwable root = t;
        String msg = t.getMessage() == null ? "" : t.getMessage();
        // CodecExceptions wrap; report the outer type, but the first line naming the real cause
        String line = msg.lines().filter(l -> !l.isBlank()).findFirst().orElse("");
        String detail = msg.lines().filter(l -> l.contains("Can't be null") || l.contains("can't be empty")
                || l.contains("FAIL")).findFirst().map(String::strip).orElse("");
        Throwable cause = t.getCause();
        String causeStr = cause == null ? "" : " <- " + cause.getClass().getSimpleName() + ": "
                + String.valueOf(cause.getMessage()).lines().findFirst().orElse("");
        return root.getClass().getSimpleName() + ": " + line + (detail.isEmpty() ? "" : " [" + detail + "]") + causeStr;
    }

    static final HytaleLogger LOG = HytaleLogger.getLogger();

    /** P1; returns the cell text. phase marker distinguishes a decode-time throw from logOrThrow. */
    static String p1(AssetBuilderCodec<String, Doc> codec, String json, Kind k, Doc parent) {
        String phase = "decode";
        try {
            AssetExtraInfo<String> ei = new AssetExtraInfo<>(new AssetExtraInfo.Data(Doc.class, "probe", parent == null ? null : "parent"));
            RawJsonReader r = RawJsonReader.fromBuffer(json.toCharArray());
            r.consumeWhiteSpace();
            Doc d = parent == null ? codec.decodeJsonAsset(r, ei) : codec.decodeAndInheritJsonAsset(r, parent, ei);
            phase = "logOrThrow";
            ei.getValidationResults().logOrThrowValidatorExceptions(LOG);
            return "OK " + describe(d, k);
        } catch (Throwable t) {
            return "THROW@" + phase + " " + first(t);
        }
    }

    static String p2(BuilderCodec<Doc> codec, String json, Kind k) {
        try {
            return "OK " + describe(codec.decode(BsonDocument.parse(json), new ExtraInfo()), k);
        } catch (Throwable t) { return "THROW " + first(t); }
    }

    static String p3(BuilderCodec<Doc> codec, String json, Kind k) {
        try {
            return "OK " + describe(codec.decodeAndInherit(BsonDocument.parse(json), (Doc) null, new ExtraInfo()), k);
        } catch (Throwable t) { return "THROW " + first(t); }
    }

    static String p4(BuilderCodec<Doc> codec, String json, Kind k) {
        try {
            RawJsonReader r = RawJsonReader.fromBuffer(json.toCharArray());
            r.consumeWhiteSpace();
            return "OK " + describe(codec.decodeJson(r, new ExtraInfo()), k);
        } catch (Throwable t) { return "THROW " + first(t); }
    }

    static boolean threw(String cell) { return cell.startsWith("THROW"); }

    // ---- main -------------------------------------------------------------------------

    static final Map<String, String> CELLS = new LinkedHashMap<>();   // "cfg|path|doc" -> text
    static final List<String> FAILED = new ArrayList<>();

    static void record(String cfg, String path, String doc, String text) {
        CELLS.put(cfg + "|" + path + "|" + doc, text);
        System.out.printf("%-6s %-4s %-8s %s%n", cfg, path, doc, text);
    }

    static void expect(boolean ok, String what) {
        if (!ok) { FAILED.add(what); System.out.println("  EXPECTATION CHANGED: " + what); }
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        List<Config> cfgs = new ArrayList<>();
        for (Kind k : new Kind[] {Kind.STRING, Kind.INTEGER}) {
            String s = k == Kind.STRING ? "S" : "I";
            cfgs.add(new Config("a" + s, "true flag only, " + k, k, true, Val.NONE, false));
            cfgs.add(new Config("b" + s, "false + nonNull, " + k, k, false, Val.NONNULL, false));
            cfgs.add(new Config("c" + s, "true + nonNull, " + k, k, true, Val.NONNULL, false));
            cfgs.add(new Config("d" + s, "neither, " + k, k, false, Val.NONE, false));
        }
        cfgs.add(new Config("e", "nonEmptyArray() on array", Kind.ARRAY, false, Val.NONEMPTY_ARRAY, false));
        cfgs.add(new Config("f", "nonEmptyMap() on map", Kind.MAP, false, Val.NONEMPTY_MAP, false));
        cfgs.add(new Config("g", "nonNullArrayElements() on array", Kind.ARRAY, false, Val.NN_ELEMENTS, false));
        cfgs.add(new Config("dA", "neither, array (control for e/g)", Kind.ARRAY, false, Val.NONE, false));
        // field holds a non-null value before decoding (a constructor default)
        cfgs.add(new Config("hS", "nonNull + default-initialised field", Kind.STRING, false, Val.NONNULL, true));
        cfgs.add(new Config("iS", "true flag only + default-initialised field", Kind.STRING, true, Val.NONE, true));
        cfgs.add(new Config("jA", "nonEmptyArray + default-initialised field", Kind.ARRAY, false, Val.NONEMPTY_ARRAY, true));

        System.out.println("# cfg    path doc      result");
        for (Config c : cfgs) {
            System.out.println("## " + c.id + ": " + c.desc);
            AssetBuilderCodec<String, Doc> ac = (AssetBuilderCodec<String, Doc>) build(c, true, false);
            BuilderCodec<Doc> bc = build(c, false, false);
            for (String d : DOCS) {
                String json = doc(c.kind, d);
                record(c.id, "P1", d, p1(ac, json, c.kind, null));
                record(c.id, "P2", d, p2(bc, json, c.kind));
                record(c.id, "P3", d, p3(bc, json, c.kind));
                record(c.id, "P4", d, p4(bc, json, c.kind));
            }
        }

        // ---- inheritance: appendInherited + a parent that holds a value ----------------
        System.out.println("## P1i: asset JSON with a Parent that carries A (appendInherited)");
        for (Config c : cfgs) {
            if (c.kind != Kind.STRING || c.preset) continue;
            AssetBuilderCodec<String, Doc> ac = (AssetBuilderCodec<String, Doc>) build(c, true, true);
            Doc parent = new Doc(); parent.s = "fromParent";
            record(c.id, "P1i", "missing", p1(ac, "{}", Kind.STRING, parent));
            record(c.id, "P1i", "null", p1(ac, "{\"A\": null}", Kind.STRING, parent));
        }


        // ---- RecordCodec: a different class with its own machinery (RecordField.validateRequiredArg) ----
        System.out.println("## RecordCodec: `true` flag / nonNull via Options lambda / nonNull as direct Validator arg");
        Object[][] recCfgs = {
            {"rS-a",  "record String, true flag only", true, "none"},
            {"rS-b",  "record String, nonNull via opts lambda", false, "opts"},
            {"rS-bv", "record String, nonNull as direct Validator argument", false, "direct"},
            {"rS-c",  "record String, true + nonNull via opts", true, "opts"},
            {"rS-d",  "record String, neither", false, "none"},
        };
        for (Object[] rc : recCfgs) {
            String id = (String) rc[0];
            System.out.println("## " + id + ": " + rc[1]);
            RecordCodec<RecS> codec = buildRecS((boolean) rc[2], (String) rc[3]);
            for (String d : DOCS) {
                String json = doc(Kind.STRING, d);
                record(id, "P2", d, recCell(() -> codec.decode(BsonDocument.parse(json), new ExtraInfo())));
                record(id, "P4", d, recCell(() -> {
                    RawJsonReader r = RawJsonReader.fromBuffer(json.toCharArray()); r.consumeWhiteSpace();
                    return codec.decodeJson(r, new ExtraInfo());
                }));
            }
        }
        System.out.println("## rI-*: record with a primitive int component");
        for (Object[] rc : new Object[][] {{"rI-a", true, "none"}, {"rI-b", false, "opts"}, {"rI-d", false, "none"}}) {
            String id = (String) rc[0];
            RecordCodec<RecI> codec = buildRecI((boolean) rc[1], (String) rc[2]);
            for (String d : DOCS) {
                String json = doc(Kind.INTEGER, d);
                record(id, "P2", d, recCell(() -> codec.decode(BsonDocument.parse(json), new ExtraInfo())));
                record(id, "P4", d, recCell(() -> {
                    RawJsonReader r = RawJsonReader.fromBuffer(json.toCharArray()); r.consumeWhiteSpace();
                    return codec.decodeJson(r, new ExtraInfo());
                }));
            }
        }

        // ---- real shipped codecs --------------------------------------------------------
        System.out.println("## REAL codecs, shipped asset JSON with one key deleted");
        String assets = args.length > 0 ? args[0] : System.getProperty("user.home") + "/.cache/hytale-assets";
        try {
            Path wall = Path.of(assets, "Server/Item/CustomConnectedBlockTemplates/WallConnectedBlockTemplate.json");
            BsonDocument full = BsonDocument.parse(Files.readString(wall));
            BsonDocument noShapes = full.clone(); noShapes.remove("Shapes");
            // The plugin-less JVM has not run ConnectedBlocksModule.setup, so the polymorphic "Type": "Custom"
            // the shipped asset uses is unregistered and the control decode would fail for that reason alone.
            // Register it exactly as ConnectedBlocksModule.java:61 does; nothing else is needed.
            com.hypixel.hytale.server.core.universe.world.connectedblocks.CustomTemplateConnectedBlockPattern.CODEC.register(
                    "Custom", com.hypixel.hytale.server.core.universe.world.connectedblocks.CustomConnectedBlockPattern.class,
                    com.hypixel.hytale.server.core.universe.world.connectedblocks.CustomConnectedBlockPattern.CODEC);
            var codec = com.hypixel.hytale.server.core.universe.world.connectedblocks.CustomConnectedBlockTemplateAsset.CODEC;
            for (var e : new LinkedHashMap<String, BsonDocument>() {{ put("full", full); put("no-Shapes", noShapes); }}.entrySet()) {
                // exactly what AssetStore.decode does with a parentless document
                String cell;
                try {
                    AssetExtraInfo<String> ei = new AssetExtraInfo<>(new AssetExtraInfo.Data(
                            com.hypixel.hytale.server.core.universe.world.connectedblocks.CustomConnectedBlockTemplateAsset.class, "Probe", null));
                    RawJsonReader r = RawJsonReader.fromBuffer(e.getValue().toString().toCharArray());
                    r.consumeWhiteSpace();
                    var a = codec.decodeJsonAsset(r, ei);
                    ei.getValidationResults().logOrThrowValidatorExceptions(LOG);
                    cell = "OK decoded; Shapes field = " + (shapesOf(a) == null ? "null" : shapesOf(a).size() + " shape(s)");
                } catch (Throwable t) { cell = "THROW " + first(t); }
                record("R1", "P1", e.getKey(), cell);
                try {
                    var a = codec.decode(e.getValue(), new ExtraInfo());
                    record("R1", "P2", e.getKey(), "OK decoded; Shapes field = " + (shapesOf(a) == null ? "null" : shapesOf(a).size() + " shape(s)"));
                } catch (Throwable t) { record("R1", "P2", e.getKey(), "THROW " + first(t)); }
            }
        } catch (Throwable t) {
            System.out.println("R1 not runnable: " + first(t));
            t.printStackTrace(System.out);
        }
        try {
            // a real nonNull key: PluginManifest.Name (non-asset BuilderCodec)
            var m = com.hypixel.hytale.common.plugin.PluginManifest.CODEC;
            record("R2", "P2", "missing-Name", describeManifest(() -> m.decode(BsonDocument.parse("{\"Group\":\"g\"}"), new ExtraInfo())));
            record("R2", "P2", "with-Name", describeManifest(() -> m.decode(BsonDocument.parse("{\"Name\":\"n\"}"), new ExtraInfo())));
        } catch (Throwable t) { System.out.println("R2 not runnable: " + first(t)); }

        // ---- verdict ----------------------------------------------------------------------
        String neg = CELLS.get("bS|P1|missing");
        System.out.println();
        System.out.println("NEGATIVE CONTROL  bS|P1|missing = " + neg);
        if (neg == null || !neg.startsWith("THROW@logOrThrow") || !neg.contains("CodecValidationException")) {
            System.out.println("VOID: nonNull on an omitted key did not throw CodecValidationException at logOrThrowValidatorExceptions.");
            System.exit(2);
        }
        // the question: does the `true` flag ALONE (aS, aI, iS) ever make an omitted key fail?
        boolean flagAloneFailsMissing = false;
        for (String cfg : new String[] {"aS", "aI", "iS"})
            for (String p : new String[] {"P1", "P2", "P3", "P4"})
                flagAloneFailsMissing |= threw(CELLS.get(cfg + "|" + p + "|missing"));
        System.out.println("true flag alone makes an OMITTED key fail on any path: " + flagAloneFailsMissing);
        boolean flagAloneFailsNull = false;
        for (String cfg : new String[] {"aS", "aI"})
            for (String p : new String[] {"P1", "P2", "P3", "P4"})
                flagAloneFailsNull |= threw(CELLS.get(cfg + "|" + p + "|null"));
        System.out.println("true flag alone makes an explicit null fail on any path: " + flagAloneFailsNull);

        // ---- pinned expectations (the measured behaviour of build 0.7.2) -----------------
        for (String p : new String[] {"P1", "P2", "P3", "P4"}) {
            for (String cfg : new String[] {"bS", "bI", "cS", "cI", "e", "f"})
                expect(threw(CELLS.get(cfg + "|" + p + "|missing")), cfg + " " + p + " missing must fail");
            for (String cfg : new String[] {"aS", "aI", "dS", "dI", "g", "dA", "hS", "iS", "jA"})
                expect(!threw(CELLS.get(cfg + "|" + p + "|missing")), cfg + " " + p + " missing must pass");
            for (String cfg : new String[] {"aS", "aI", "bS", "bI", "cS", "cI", "dS", "dI", "e", "f", "g", "dA", "hS", "iS", "jA"})
                expect(!threw(CELLS.get(cfg + "|" + p + "|value")), cfg + " " + p + " valid value must pass");
        }
        for (String p : new String[] {"P2", "P4"}) {
            for (String cfg : new String[] {"rS-b", "rS-bv", "rS-c"})
                expect(threw(CELLS.get(cfg + "|" + p + "|missing")), cfg + " " + p + " missing must fail");
            for (String cfg : new String[] {"rS-a", "rS-d", "rI-a", "rI-b", "rI-d"})
                expect(!threw(CELLS.get(cfg + "|" + p + "|missing")), cfg + " " + p + " missing must pass");
        }
        // the real-codec control: the intact shipped asset must decode, else the no-Shapes row proves nothing
        expect(CELLS.containsKey("R1|P1|full") && !threw(CELLS.get("R1|P1|full")), "R1 intact shipped asset must decode on P1");
        expect(CELLS.containsKey("R1|P1|no-Shapes") && !threw(CELLS.get("R1|P1|no-Shapes")), "R1 without the true-flag-only Shapes must decode on P1");
        expect(CELLS.containsKey("R2|P2|missing-Name") && threw(CELLS.get("R2|P2|missing-Name")), "PluginManifest without Name must fail");
        expect(!flagAloneFailsMissing, "the true flag alone must not reject an omitted key (hypothesis)");
        System.out.println(FAILED.isEmpty() ? "PINNED EXPECTATIONS: all held" : "PINNED EXPECTATIONS: " + FAILED.size() + " changed");
        System.exit(FAILED.isEmpty() ? 0 : 1);
    }


    static String recCell(Callable<Object> c) {
        try { return "OK " + c.call(); } catch (Throwable t) { return "THROW " + first(t); }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static RecordCodec<RecS> buildRecS(boolean flag, String how) {
        KeyedCodec<String> kc = new KeyedCodec<>("A", Codec.STRING, flag);
        Function<RecS, String> acc = RecS::a;
        RecordCodec.Builder0<RecS> b = RecordCodec.builder(RecS.class);
        return switch (how) {
            case "opts" -> b.append(kc, acc, (Consumer<com.hypixel.hytale.codec.record.RecordField.Options<String>>) o -> o.addValidator(Validators.nonNull())).build(RecS::new);
            case "direct" -> b.append(kc, acc, Validators.<String>nonNull()).build(RecS::new);
            default -> b.append(kc, acc).build(RecS::new);
        };
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static RecordCodec<RecI> buildRecI(boolean flag, String how) {
        KeyedCodec<Integer> kc = new KeyedCodec<>("A", Codec.INTEGER, flag);
        Function<RecI, Integer> acc = RecI::a;
        RecordCodec.Builder0<RecI> b = RecordCodec.builder(RecI.class);
        return switch (how) {
            case "opts" -> b.append(kc, acc, (Consumer<com.hypixel.hytale.codec.record.RecordField.Options<Integer>>) o -> o.addValidator(Validators.nonNull())).build(RecI::new);
            default -> b.append(kc, acc).build(RecI::new);
        };
    }

    @SuppressWarnings("unchecked")
    static Map<String, ?> shapesOf(Object a) throws Exception {
        var f = a.getClass().getDeclaredField("connectedBlockShapes");
        f.setAccessible(true);
        return (Map<String, ?>) f.get(a);
    }

    static String describeManifest(Callable<Object> c) {
        try { c.call(); return "OK decoded"; } catch (Throwable t) { return "THROW " + first(t); }
    }
}
