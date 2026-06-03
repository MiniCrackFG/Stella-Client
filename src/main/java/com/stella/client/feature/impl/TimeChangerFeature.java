package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class TimeChangerFeature extends Feature {
    public TimeChangerFeature() {
        super("time_changer", "Time Changer", FeatureCategory.VISUAL);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Select("Mode", "time_changer.mode", new String[]{"Day", "Noon", "Sunset", "Night", "Midnight"}),
            new SettingsOption.Slider("Speed", "time_changer.speed", 0, 100, 1, "x")
        );
    }

    public long getOverrideTime() {
        String mode = com.stella.client.config.StellaConfig.getInstance().get("time_changer.mode", "Day");
        return switch (mode) {
            case "Noon" -> 6000;
            case "Sunset" -> 12000;
            case "Night" -> 13000;
            case "Midnight" -> 18000;
            default -> 1000;
        };
    }
}
