package doublerun.probe;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.ModifyInventoryInteraction;
import javax.annotation.Nonnull;

/**
 * ModifyInventory with getWaitForDataFrom() changed from Server to None, nothing else. The pass order is then
 * simulation first, server second: the simulation pass does the work, and the server pass sees the changed held
 * item (Interaction.tickInternal) and ends the chain as ItemChanged. See the README, "Pass order decides the
 * item-change outcome".
 */
public class ProbeInvNoneInteraction extends ModifyInventoryInteraction {
    public static final BuilderCodec<ProbeInvNoneInteraction> CODEC = BuilderCodec
        .builder(ProbeInvNoneInteraction.class, ProbeInvNoneInteraction::new, ModifyInventoryInteraction.CODEC)
        .build();

    @Override
    @Nonnull
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.None;
    }
}
