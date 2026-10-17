package beams.probe;

import com.hypixel.hytale.builtin.beam.BeamComponent;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * An interaction whose firstRun logs synchronously. AttachBeam queues its effect on the
 * command buffer, so a queued effect cannot show how far a chain got. This one writes
 * its line while the chain is running.
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
        Ref<EntityStore> entity = context.getEntity();
        Ref<EntityStore> owner = context.getOwningEntity();
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        // Committed state only: a queued addComponent is not applied until the buffer is consumed.
        boolean committed = buffer != null && entity.isValid()
            && buffer.getComponent(entity, BeamComponent.getComponentType()) != null;
        Log.p("ProbeLog message='%s' type=%s entity=%s owner=%s beamComponentCommittedNow=%s",
            message, type, entity, owner, committed);
        if (Boolean.getBoolean("beams.probe.stack")) {
            StackTraceElement[] frames = new Throwable().getStackTrace();
            for (int i = 1; i < Math.min(frames.length, 14); i++) {
                Log.p("  at %s", frames[i]);
            }
        }
    }
}
