package doublerun.probe;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;

/** ProbeLog that also overrides simulateFirstRun with an empty body: the one-line fix for a server-only effect. */
public class ProbeLogQuietInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<ProbeLogQuietInteraction> CODEC = BuilderCodec
        .builder(ProbeLogQuietInteraction.class, ProbeLogQuietInteraction::new, SimpleInstantInteraction.CODEC)
        .appendInherited(new KeyedCodec<String>("Message", Codec.STRING),
            (o, i) -> o.message = i, o -> o.message, (o, p) -> o.message = p.message)
        .add()
        .build();

    protected String message = "";

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        Log.p("ProbeLogQ message='%s'", message);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // nothing: the simulation pass does no work, so firstRun runs once (in the server pass)
    }
}
