import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.JsonAsset;
import com.hypixel.hytale.codec.ExtraInfo;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.exception.CodecValidationException;
import com.hypixel.hytale.logger.HytaleLogger;
import org.bson.BsonDocument;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * For each class named in the input file, decode an EMPTY document through its static
 * CODEC with a collecting ExtraInfo (the way asset loading does) and report which keys
 * the engine itself says failed. That set is the measured answer to "which keys are
 * required": no reading of validators, defaults or hooks is involved, so it cannot share
 * a failure mode with the static parser.
 *
 * Input: one class name per line, optionally `name#FIELD` to read a codec field other than
 * CODEC. A dotted name is tried as written, then with trailing dots turned into `$` (nested
 * classes). Output, one TSV line per entry:
 *   class <TAB> status <TAB> detail
 *   status: KEYS (detail = failing keys, comma separated; empty = decodes clean),
 *           CODEC_LEVEL (validation failed with no key attached: a codec-level validator or
 *             afterDecode hook rejected the empty document, which no per-key attribute can see),
 *           KEYS with a trailing `|CODEC_LEVEL`: keys failed AND a key-less holder did too,
 *           THROW (decode threw before validation finished; detail = top frame | type: message),
 *           NOCODEC (no static field of that name holding a BuilderCodec),
 *           ABSTRACT (BuilderCodec without a supplier),
 *           INIT (class initialisation failed; detail = cause)
 * Exit 0 always: classification is data, not a verdict (effective-required.py judges).
 */
public class EffectiveRequired {
    public static class Dummy implements JsonAsset<String> {
        public String getId() { return "probe"; }
    }

    record Parsed(TreeSet<String> keys, boolean hook) {}

    /** Parse a CodecValidationException message as holders: an optional `Key: x` line, `Results:`, then
     *  one line per result, `\tFAIL: ...` or `\tWARNING: ...`. Only a holder with a FAIL rejected the
     *  document (warn-only holders are listed but do not throw); a failing holder with no preceding Key
     *  line is a codec-level hook. */
    static Parsed parse(String message) {
        TreeSet<String> keys = new TreeSet<>();
        boolean hook = false, inBlock = false, blockKeyed = false, blockFailed = false;
        String pending = null, blockKey = null;
        for (String ln : (message + "\nEND").split("\n")) {
            boolean boundary = ln.startsWith("Key: ") || ln.equals("Results:") || ln.equals("END");
            if (boundary && inBlock && blockFailed) {
                if (blockKeyed) keys.add(blockKey); else hook = true;
            }
            if (ln.startsWith("Key: ")) { pending = ln.substring(5).trim(); inBlock = false; blockFailed = false; }
            else if (ln.equals("Results:")) { inBlock = true; blockFailed = false; blockKeyed = pending != null; blockKey = pending; pending = null; }
            else if (inBlock && ln.startsWith("\tFAIL")) blockFailed = true;
        }
        return new Parsed(keys, hook);
    }

    /** Build real ValidationResults holders (warn-only keyed, failing keyed, warn-only key-less, failing key-less) and
     *  check parse() against them. A parser that counts holders instead of failures misclassifies the warn-only ones. */
    static boolean selfTest() {
        HytaleLogger log = HytaleLogger.getLogger();
        boolean ok = true;
        for (int variant = 0; variant < 3; variant++) {
            AssetExtraInfo<String> ei = new AssetExtraInfo<>(new AssetExtraInfo.Data(Dummy.class, "probe", null));
            var vr = ei.getValidationResults();
            ei.pushKey("Warned"); vr.warn("w"); vr._processValidationResults(); ei.popKey();
            ei.pushKey("Failed"); vr.fail("f"); vr._processValidationResults(); ei.popKey();
            vr.warn("w-root"); vr._processValidationResults();                  // warn-only key-less holder
            if (variant == 1) { vr.fail("f-root"); vr._processValidationResults(); }   // failing key-less holder
            if (variant == 2) { ei.pushKey("Failed2"); vr.fail("f2"); vr._processValidationResults(); ei.popKey(); }
            try { vr.logOrThrowValidatorExceptions(log); ok = false; System.err.println("self-test: nothing thrown"); }
            catch (CodecValidationException e) {
                Parsed pr = parse(e.getMessage());
                TreeSet<String> want = new TreeSet<>(variant == 2 ? List.of("Failed", "Failed2") : List.of("Failed"));
                boolean wantHook = variant == 1;
                if (!pr.keys().equals(want) || pr.hook() != wantHook) {
                    ok = false;
                    System.err.println("self-test variant " + variant + ": got keys " + pr.keys() + " hook " + pr.hook() + ", want " + want + " hook " + wantHook);
                }
            }
        }
        return ok;
    }

    static Class<?> load(String cn) throws ClassNotFoundException {
        ClassNotFoundException first = null;
        String cur = cn;
        while (true) {
            try { return Class.forName(cur, true, EffectiveRequired.class.getClassLoader()); }
            catch (ClassNotFoundException e) { if (first == null) first = e; }
            int dot = cur.lastIndexOf('.');
            if (dot < 0) throw first;
            cur = cur.substring(0, dot) + "$" + cur.substring(dot + 1);
        }
    }

    public static void main(String[] args) throws Exception {
        HytaleLogger log = HytaleLogger.getLogger();
        if (args[0].equals("--self-test")) { System.out.println(selfTest() ? "SELFTEST ok" : "SELFTEST FAILED"); return; }
        for (String name : Files.readAllLines(Path.of(args[0]))) {
            name = name.trim();
            if (name.isEmpty()) continue;
            String status, detail = "";
            try {
                String field = "CODEC", cn = name;
                int hash = name.indexOf('#');
                if (hash >= 0) { field = name.substring(hash + 1); cn = name.substring(0, hash); }
                Class<?> cls = load(cn);
                Object f;
                try {
                    // private/protected codecs exist (SpawnNPCInteraction.WeightedNPCSpawn.CODEC)
                    java.lang.reflect.Field fld = cls.getDeclaredField(field);
                    fld.setAccessible(true);
                    f = fld.get(null);
                }
                catch (NoSuchFieldException e) { f = null; }
                if (!(f instanceof BuilderCodec<?> c)) {
                    System.out.println(name + "\tNOCODEC\t"); continue;
                }
                if (c.getSupplier() == null) { System.out.println(name + "\tABSTRACT\t"); continue; }
                AssetExtraInfo<String> ei = new AssetExtraInfo<>(new AssetExtraInfo.Data(Dummy.class, "probe", null));
                try {
                    c.decode(BsonDocument.parse("{}"), ei);
                    ei.getValidationResults().logOrThrowValidatorExceptions(log);
                    status = "KEYS";
                } catch (CodecValidationException e) {
                    Parsed pr = parse(e.getMessage());
                    TreeSet<String> keys = pr.keys;
                    boolean hook = pr.hook;
                    status = "KEYS"; detail = String.join(",", keys);
                    if (keys.isEmpty()) { status = "CODEC_LEVEL"; detail = e.getMessage().replace('\n', ' '); }
                    else if (hook) detail += "|CODEC_LEVEL";
                }
            } catch (ExceptionInInitializerError | NoClassDefFoundError e) {
                status = "INIT"; detail = String.valueOf(e.getCause() != null ? e.getCause() : e).replace('\n', ' ');
            } catch (Throwable t) {
                // The first stack frame says WHERE it threw: a frame in the codec's own class is its
                // validator/afterDecode hook crashing on the empty document (BlockSpawnerTable: a
                // validator that dereferences Entries); a frame elsewhere is an unbooted singleton.
                StackTraceElement[] st = t.getStackTrace();
                StringBuilder fb = new StringBuilder();
                for (int i = 0; i < Math.min(4, st.length); i++) fb.append(i == 0 ? "" : " < ").append(st[i].getClassName().replaceFirst(".*\\.", "")).append('.').append(st[i].getMethodName());
                String frame = fb.length() > 0 ? fb.toString() : "?";
                status = "THROW"; detail = frame + " | " + t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage()).lines().findFirst().orElse("");
            }
            System.out.println(name + "\t" + status + "\t" + detail);
        }
    }
}
