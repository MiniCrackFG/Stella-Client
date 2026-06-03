package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class WaypointsFeature extends Feature {
    public WaypointsFeature() {
        super("waypoints", "Waypoints", FeatureCategory.VISUAL);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Toggle("Render in World", "waypoints.world"),
            new SettingsOption.Toggle("Show Distance", "waypoints.distance"),
            new SettingsOption.Slider("Scale", "waypoints.scale", 50, 200, 5, "%")
        );
    }
}
