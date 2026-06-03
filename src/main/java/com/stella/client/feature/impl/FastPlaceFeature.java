package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class FastPlaceFeature extends Feature {
    public FastPlaceFeature() {
        super("fast_place", "Fast Place", FeatureCategory.GAMEPLAY);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Slider("Delay", "fast_place.delay", 0, 4, 1, "tick")
        );
    }
}
