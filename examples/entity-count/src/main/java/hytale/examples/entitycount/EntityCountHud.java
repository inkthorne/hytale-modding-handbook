package hytale.examples.entitycount;

import com.hypixel.hytale.server.core.entity.entities.player.hud.CustomUIHud;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;

/**
 * The on-screen overlay that shows the entity counts.
 *
 * <p>A {@link CustomUIHud} is a panel drawn on top of a single player's screen.
 * Its visual layout lives in a separate {@code .ui} file
 * ({@code Common/UI/Custom/EntityCountHud.ui}); this class loads that file and
 * later updates the text inside it.
 *
 * <p>This class is deliberately "dumb": it knows how to draw and how to change
 * its labels, but it never figures out the numbers itself. They are pushed in by
 * {@link EntityCountTickingSystem} via {@link #updateCounts}.
 */
public class EntityCountHud extends CustomUIHud {

    // The last numbers we showed. We keep them so updateCounts can skip doing
    // anything when nothing has changed (see below).
    private int lastTotal = -1;
    private int lastPlayers = -1;
    private int lastNpcs = -1;
    private int lastOther = -1;

    public EntityCountHud(PlayerRef playerRef) {
        super(playerRef);
    }

    /**
     * Builds the HUD's initial contents. Called once when the HUD is shown. Here
     * we just load the layout from the {@code .ui} file (the path is relative to
     * the {@code Common/UI/Custom/} folder).
     */
    @Override
    protected void build(UICommandBuilder cmd) {
        cmd.append("EntityCountHud.ui");
    }

    /**
     * Updates the four numbers shown on the HUD. Called by the ticking system.
     *
     * @param total   total number of entities in the world
     * @param players entities that have a {@code Player} component
     * @param npcs    entities that have an {@code NPCEntity} component
     * @param other   everything else (projectiles, dropped items, and so on)
     */
    public void updateCounts(int total, int players, int npcs, int other) {
        // The counts barely change most of the time. If they're identical to last
        // time, do nothing — that avoids sending a pointless update to the client.
        if (total == lastTotal && players == lastPlayers
                && npcs == lastNpcs && other == lastOther) {
            return;
        }
        lastTotal = total;
        lastPlayers = players;
        lastNpcs = npcs;
        lastOther = other;

        // A UICommandBuilder is a list of changes to apply to the HUD. Each set()
        // targets one label by id ("#TotalLabel", defined in the .ui file) and
        // changes its Text. update() then sends those changes to the player.
        UICommandBuilder cmd = new UICommandBuilder();
        cmd.set("#TotalLabel.Text", "Total: " + total);
        cmd.set("#PlayerLabel.Text", "Players: " + players);
        cmd.set("#NpcLabel.Text", "NPCs: " + npcs);
        cmd.set("#OtherLabel.Text", "Other: " + other);
        update(false, cmd); // false = change only these labels, leave the rest as-is
    }
}
