package beams.probe;

import com.hypixel.hytale.logger.HytaleLogger;

/** Every probe line starts with "PROBE " so a run's log can be filtered with one grep. */
final class Log {
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    private Log() {
    }

    /**
     * A WARNING-level marker. A --shutdown-after-validate run logs only WARNING and above, so an
     * INFO line cannot show that a phase ran there. setup() and start() each write one.
     */
    static void mark(String phase) {
        LOGGER.atWarning().log("%s", "PROBE-MARK " + phase);
    }

    static void p(String format, Object... args) {
        LOGGER.atInfo().log("%s", "PROBE " + String.format(format, args));
    }
}
