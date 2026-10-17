package doublerun.probe;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;

/**
 * A probe interaction that extends SimpleInstantInteraction and overrides nothing but firstRun,
 * so it is exactly what a plugin author writes first. firstRun writes one line. With -Ddr.stack=true
 * the line carries the frames that called it, so the log shows the frames; `pass=` is read off them (simulationTick or serverTick).
 *
 * This is NOT a measurement of a shipped type's effect: its effect is one log line. It shows that the
 * manager runs the hook twice; the effect at a target is measured with shipped types.
 */
public class ProbeLogInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<ProbeLogInteraction> CODEC = BuilderCodec
        .builder(ProbeLogInteraction.class, ProbeLogInteraction::new, SimpleInstantInteraction.CODEC)
        .appendInherited(new KeyedCodec<String>("Message", Codec.STRING),
            (o, i) -> o.message = i, o -> o.message, (o, p) -> o.message = p.message)
        .add()
        .build();

    protected String message = "";

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        Log.p("ProbeLog message='%s' pass=%s type=%s entity=%s owner=%s", message, ProbeLogServerInteraction.pass(), type,
            context.getEntity(), context.getOwningEntity());
        if (Boolean.getBoolean("dr.stack")) {
            StackTraceElement[] frames = new Throwable().getStackTrace();
            for (int i = 1; i < Math.min(frames.length, 8); i++) {
                Log.p("  at %s", frames[i]);
            }
        }
    }
}
