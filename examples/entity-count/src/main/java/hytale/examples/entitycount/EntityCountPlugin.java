package hytale.examples.entitycount;

import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;

/**
 * The main class of the plugin — the entry point the server loads first.
 *
 * <p>Every Hytale plugin has one class that extends {@link JavaPlugin}, named in
 * {@code manifest.json} under {@code "Main"}. The server creates it once at
 * startup and calls {@link #setup()}.
 *
 * <p>This example is split into four small classes so each does one job:
 * <ul>
 *   <li>{@link EntityCountCommand} — the {@code /entitycount} command players type</li>
 *   <li>{@link EntityCountTickingSystem} — runs every tick and counts entities</li>
 *   <li>{@link EntityCountHud} — the on-screen overlay that shows the numbers</li>
 *   <li>{@link HudRegistry} — a shared list of who currently has the HUD open</li>
 * </ul>
 */
public class EntityCountPlugin extends JavaPlugin {

    // The server passes in this "init" object when it creates the plugin.
    // You don't use it directly — just hand it to the parent class.
    public EntityCountPlugin(JavaPluginInit init) {
        super(init);
    }

    /**
     * Called once when the plugin loads. This is where you register everything
     * the plugin provides: commands, systems, event handlers, and so on.
     */
    @Override
    protected void setup() {
        // One registry, shared by both the command and the system, so they agree
        // on which players currently have the HUD open.
        HudRegistry registry = new HudRegistry();

        // Make "/entitycount" available to players.
        getCommandRegistry().registerCommand(new EntityCountCommand(registry));

        // Tell the engine to run our system every tick (see EntityCountTickingSystem).
        getEntityStoreRegistry().registerSystem(new EntityCountTickingSystem(registry));

        // Shows up in the server console — handy for confirming the plugin loaded.
        getLogger().atInfo().log("EntityCount example plugin loaded!");
    }
}
