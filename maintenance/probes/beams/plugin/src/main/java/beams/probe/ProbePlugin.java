package beams.probe;

import com.hypixel.hytale.server.core.HytaleServer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.events.AllWorldsLoadedEvent;
import java.util.concurrent.TimeUnit;

/**
 * Probe plugin for maintenance/probes/beams. Always on: the BeamComponent and projectile
 * observers. Headless runs choose tasks with -Dbeams.probe=a,b,c:
 *
 *   c6              log the beam index each AttachBeam interaction resolved at load
 *   c3              serialize BeamsUpdate packets with 96, 97 and non-ASCII node names
 *   world:<config>  spawn a host entity and fire the named ProjectileConfig from it
 *   ticklog         log one line per second of world time
 *
 * -Dbeams.probe.reload=FILE (with c6): rewrite the interaction file FILE while the server runs
 * and run c6 again once the file watcher has reloaded it.
 *
 * A run that names any task shuts the server down -Dbeams.probe.exitMs (default 20000)
 * after the worlds are loaded, or at once when it names no world task.
 */
public class ProbePlugin extends JavaPlugin {
    public ProbePlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        Log.mark("setup");
        getCodecRegistry(Interaction.CODEC).register("ProbeLog", ProbeLogInteraction.class, ProbeLogInteraction.CODEC);
        getEntityStoreRegistry().registerSystem(new BeamWatch.Changes());
        getEntityStoreRegistry().registerSystem(new BeamWatch.Tick());
        getEntityStoreRegistry().registerSystem(new ProjectileWatch());
        getEntityStoreRegistry().registerSystem(new HostWatch());
        if (tasks().contains("ticklog")) {
            getEntityStoreRegistry().registerSystem(new WorldTickLog());
        }
    }

    private static String tasks() {
        return System.getProperty("beams.probe", "");
    }

    @Override
    protected void start() {
        Log.mark("start");
        String mode = tasks();
        Log.p("plugin started, beams.probe='%s'", mode);
        if (mode.isEmpty()) {
            return;
        }
        String worldConfig = null;
        for (String task : mode.split(",")) {
            if (task.equals("c6")) {
                Tasks.c6();
            } else if (task.equals("c3")) {
                Tasks.c3();
            } else if (task.startsWith("world:")) {
                worldConfig = task.substring("world:".length());
            }
        }
        String reload = System.getProperty("beams.probe.reload");
        if (reload != null) {
            Tasks.reload(reload);
            return;
        }
        if (worldConfig == null) {
            Log.p("no world task, shutting down");
            HytaleServer.get().shutdownServer();
            return;
        }
        final String config = worldConfig;
        long exitMs = Long.getLong("beams.probe.exitMs", 20000L);
        getEventRegistry().registerGlobal(AllWorldsLoadedEvent.class, event -> {
            Log.p("AllWorldsLoadedEvent, driving %s in 3 s", config);
            HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> Tasks.drive(config), 3, TimeUnit.SECONDS);
            HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> {
                Log.p("exit timer fired after %d ms, shutting down", exitMs);
                HytaleServer.get().shutdownServer();
            }, exitMs, TimeUnit.MILLISECONDS);
        });
    }
}
