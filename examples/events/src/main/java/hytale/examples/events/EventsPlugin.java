package hytale.examples.events;

import com.hypixel.hytale.event.EventRegistration;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.player.PlayerConnectEvent;
import com.hypixel.hytale.server.core.event.events.player.PlayerDisconnectEvent;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;

/**
 * Demonstrates the two event mechanisms side by side:
 *
 * 1. The global event bus (getEventRegistry().register(...)) for server-level
 *    events like PlayerConnectEvent / PlayerDisconnectEvent. Handlers run
 *    outside the ECS; keep the EventRegistration if you may unregister later.
 *
 * 2. ECS event systems (getEntityStoreRegistry().registerSystem(...)) for
 *    per-entity gameplay events like BreakBlockEvent — see
 *    BreakBlockNotifierSystem.
 */
public class EventsPlugin extends JavaPlugin {

    private EventRegistration<Void, PlayerConnectEvent> connectRegistration;

    public EventsPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        // Global bus: welcome each player as they connect. PlayerConnectEvent
        // is a non-keyed event, so plain register() (not registerGlobal).
        connectRegistration = getEventRegistry().register(PlayerConnectEvent.class, event -> {
            event.getPlayerRef().sendMessage(
                Message.raw("Welcome, " + event.getPlayerRef().getUsername() + "!"));
        });

        // Global bus: log disconnects with the engine-provided reason.
        getEventRegistry().register(PlayerDisconnectEvent.class, event -> {
            getLogger().atInfo().log("%s disconnected (%s)",
                event.getPlayerRef().getUsername(), event.getDisconnectReason());
        });

        // ECS: react to block breaks on the world thread, with entity context.
        getEntityStoreRegistry().registerSystem(new BreakBlockNotifierSystem());

        getLogger().atInfo().log("EventsExample plugin loaded!");
    }
}
