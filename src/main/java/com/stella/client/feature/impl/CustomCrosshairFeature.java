package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class CustomCrosshairFeature extends Feature {
    public CustomCrosshairFeature() {
        super("custom_crosshair", "Custom Crosshair", FeatureCategory.VISUAL);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Slider("Size", "crosshair.size", 4, 20, 1, "px"),
            new SettingsOption.Slider("Thickness", "crosshair.thickness", 1, 5, 1, "px"),
            new SettingsOption.Slider("Gap", "crosshair.gap", 0, 10, 1, "px"),
            new SettingsOption.Toggle("Dot", "crosshair.dot")
        );
    }
}
