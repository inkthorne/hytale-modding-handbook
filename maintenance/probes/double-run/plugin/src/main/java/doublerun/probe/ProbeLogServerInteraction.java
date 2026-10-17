package doublerun.probe;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;

/** ProbeLog with getWaitForDataFrom() = Server: the pass order (server pass first) is read off the order of its lines. */
public class ProbeLogServerInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<ProbeLogServerInteraction> CODEC = BuilderCodec
        .builder(ProbeLogServerInteraction.class, ProbeLogServerInteraction::new, SimpleInstantInteraction.CODEC)
        .appendInherited(new KeyedCodec<String>("Message", Codec.STRING),
            (o, i) -> o.message = i, o -> o.message, (o, p) -> o.message = p.message)
        .add()
        .build();

    protected String message = "";

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        String pass = pass();
        Log.p("ProbeLogS message='%s' pass=%s", message, pass);
    }

    /** Which pass called us: the frames of the calling stack contain simulationTick or serverTick. */
    static String pass() {
        for (StackTraceElement f : new Throwable().getStackTrace()) {
            if (f.getMethodName().equals("simulationTick")) {
                return "simulation";
            }
            if (f.getMethodName().equals("serverTick")) {
                return "server";
            }
        }
        return "?";
    }
}
