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
 *           THROW (decode threw before validation finished; detail = type: message),
 *           NOCODEC (no static field of that name holding a BuilderCodec),
 *           ABSTRACT (BuilderCodec without a supplier),
 *           INIT (class initialisation failed; detail = cause)
 * Exit 0 always: classification is data, not a verdict (effective-required.py judges).
 */
public class EffectiveRequired {
    public static class Dummy implements JsonAsset<String> {
        public String getId() { return "probe"; }
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
                    TreeSet<String> keys = new TreeSet<>();
                    for (String ln : e.getMessage().split("\n"))
                        if (ln.startsWith("Key: ")) keys.add(ln.substring(5).trim());
                    status = "KEYS"; detail = String.join(",", keys);
                    if (keys.isEmpty()) { status = "THROW"; detail = "CodecValidationException without a Key line: " + e.getMessage().replace('\n', ' '); }
                }
            } catch (ExceptionInInitializerError | NoClassDefFoundError e) {
                status = "INIT"; detail = String.valueOf(e.getCause() != null ? e.getCause() : e).replace('\n', ' ');
            } catch (Throwable t) {
                status = "THROW"; detail = t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage()).lines().findFirst().orElse("");
            }
            System.out.println(name + "\t" + status + "\t" + detail);
        }
    }
}
