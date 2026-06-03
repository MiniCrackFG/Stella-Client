package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class ToggleSneakFeature extends Feature {
    private boolean sneakToggled;
    private boolean wasShiftDown;

    public ToggleSneakFeature() {
        super("toggle_sneak", "Toggle Sneak", FeatureCategory.GAMEPLAY);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Toggle("Enabled", "toggle_sneak.enabled"));
    }

    @Override
    public void onTick() {
        if (mc.player == null) return;

        boolean shiftDown = mc.options.keyShift.isDown();

        if (shiftDown && !wasShiftDown) {
            sneakToggled = !sneakToggled;
        }
        wasShiftDown = shiftDown;

        if (sneakToggled || shiftDown) {
            mc.player.setShiftKeyDown(true);
        }
    }
}
