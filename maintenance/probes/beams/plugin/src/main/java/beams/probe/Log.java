package beams.probe;

import com.hypixel.hytale.logger.HytaleLogger;

/** Every probe line starts with "PROBE " so a run's log can be filtered with one grep. */
final class Log {
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    private Log() {
    }

    static void p(String format, Object... args) {
        LOGGER.atInfo().log("%s", "PROBE " + String.format(format, args));
    }
}
