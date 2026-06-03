package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class ToggleSprintFeature extends Feature {
    private boolean sprintToggled;
    private boolean wasKeyDown;

    public ToggleSprintFeature() {
        super("toggle_sprint", "Toggle Sprint", FeatureCategory.GAMEPLAY);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Toggle("Enabled", "toggle_sprint.enabled"));
    }

    @Override
    public void onTick() {
        if (mc.player == null) return;

        boolean keyDown = mc.options.keySprint.isDown();

        if (keyDown && !wasKeyDown) {
            sprintToggled = !sprintToggled;
        }
        wasKeyDown = keyDown;

        if (sprintToggled) {
            mc.player.setSprinting(true);
        }
    }
}
