package hytale.examples.ui;

import com.hypixel.hytale.server.core.entity.entities.player.hud.CustomUIHud;
import com.hypixel.hytale.server.core.ui.builder.UICommandBuilder;
import com.hypixel.hytale.server.core.universe.PlayerRef;

/**
 * A custom HUD overlay displaying player status information.
 * Demonstrates how to create persistent HUD elements with dynamic updates.
 *
 * <p>Key concepts demonstrated:
 * <ul>
 *   <li>Extending CustomUIHud for persistent HUD overlays</li>
 *   <li>Loading UI from .ui files in build()</li>
 *   <li>Dynamic updates using update(false, cmd)</li>
 *   <li>Element targeting with #ElementId.Property syntax</li>
 * </ul>
 *
 * See {@code docs/ui-api.md} (CustomUIHud section) in the repository root for full documentation.
 */
public class StatusHud extends CustomUIHud {

    /** Stable key identifying this HUD on the player; pass to removeCustomHud() to hide it. */
    public static final String KEY = "status-hud";

    public StatusHud(PlayerRef playerRef) {
        super(playerRef, KEY);
    }

    @Override
    protected void build(UICommandBuilder cmd) {
        // Load UI from .ui file (path relative to Common/UI/Custom/)
        cmd.append("StatusHud.ui");
    }

    /**
     * Updates the health and mana display values.
     *
     * <p>This method demonstrates dynamic HUD updates using {@code update(false, cmd)}.
     * The {@code false} parameter means commands are applied incrementally without
     * clearing existing content.
     *
     * <p>Example usage:
     * <pre>{@code
     * StatusHud hud = playerHuds.get(player.getUUID());
     * if (hud != null) {
     *     hud.updateStats(player.getHealth(), player.getMana());
     * }
     * }</pre>
     *
     * @param health the current health value to display
     * @param mana the current mana value to display
     */
    public void updateStats(int health, int mana) {
        UICommandBuilder cmd = new UICommandBuilder();
        cmd.set("#HealthLabel.Text", "Health: " + health);
        cmd.set("#ManaLabel.Text", "Mana: " + mana);
        update(false, cmd);  // false = apply incrementally, don't clear existing content
    }

    /**
     * Updates only the health display value.
     *
     * @param health the current health value to display
     */
    public void updateHealth(int health) {
        UICommandBuilder cmd = new UICommandBuilder();
        cmd.set("#HealthLabel.Text", "Health: " + health);
        update(false, cmd);
    }

    /**
     * Updates only the mana display value.
     *
     * @param mana the current mana value to display
     */
    public void updateMana(int mana) {
        UICommandBuilder cmd = new UICommandBuilder();
        cmd.set("#ManaLabel.Text", "Mana: " + mana);
        update(false, cmd);
    }
}
