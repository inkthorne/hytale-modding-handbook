package doublerun.probe;

import com.hypixel.hytale.server.core.HytaleServer;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.events.AllWorldsLoadedEvent;
import java.util.concurrent.TimeUnit;

/**
 * Probe plugin for maintenance/probes/double-run. It registers four interaction types of its own: ProbeLog (extends
 * SimpleInstantInteraction and overrides firstRun only: what a plugin author writes first), ProbeLogS (the same with
 * getWaitForDataFrom() = Server), ProbeLogQ (also overrides simulateFirstRun with an empty body) and ProbeInvNone
 * (ModifyInventory with the wait changed to None). It also registers the counters of Watch, and, when -Ddr.root is set, stages one case with Driver (see its header for the
 * properties). The server shuts itself down -Ddr.exitMs after the worlds are loaded. With no -Ddr.root it shuts
 * down at once (run.sh's `boot` case uses --boot-command stop instead).
 */
public class DrPlugin extends JavaPlugin {
    public DrPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        Log.mark("setup");
        getCodecRegistry(Interaction.CODEC).register("ProbeLog", ProbeLogInteraction.class, ProbeLogInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register("ProbeLogS", ProbeLogServerInteraction.class, ProbeLogServerInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register("ProbeLogQ", ProbeLogQuietInteraction.class, ProbeLogQuietInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register("ProbeInvNone", ProbeInvNoneInteraction.class, ProbeInvNoneInteraction.CODEC);
        getEntityStoreRegistry().registerSystem(new Watch.Projectiles());
        getEntityStoreRegistry().registerSystem(new Watch.ProjectilesNew());
        getEntityStoreRegistry().registerSystem(new Watch.Breaks());
        getEntityStoreRegistry().registerSystem(new Watch.Lifecycle());
        getEntityStoreRegistry().registerSystem(new Watch.DamageSeen());
        getEntityStoreRegistry().registerSystem(new Watch.DamageRaised());
        getEntityStoreRegistry().registerSystem(new Watch.Beams());
        getEntityStoreRegistry().registerSystem(new Watch.Teleports());
    }

    @Override
    protected void start() {
        Log.mark("start");
        String root = System.getProperty("dr.root");
        Log.p("plugin started, dr.root='%s' dr.manager='%s'", root, System.getProperty("dr.manager", "npc"));
        if (root == null) {
            Log.p("no dr.root, shutting down");
            HytaleServer.get().shutdownServer();
            return;
        }
        long exitMs = Long.getLong("dr.exitMs", 12000L);
        getEventRegistry().registerGlobal(AllWorldsLoadedEvent.class, event -> {
            Log.p("AllWorldsLoadedEvent, driving %s in 3 s", root);
            HytaleServer.SCHEDULED_EXECUTOR.schedule(Driver::run, 3, TimeUnit.SECONDS);
            HytaleServer.SCHEDULED_EXECUTOR.schedule(() -> {
                Log.p("exit timer fired after %d ms, shutting down", exitMs);
                HytaleServer.get().shutdownServer();
            }, exitMs, TimeUnit.MILLISECONDS);
        });
    }
}
