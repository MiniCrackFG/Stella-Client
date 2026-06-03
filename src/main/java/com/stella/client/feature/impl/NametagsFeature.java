package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class NametagsFeature extends Feature {
    public NametagsFeature() {
        super("nametags", "Better Nametags", FeatureCategory.VISUAL);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Toggle("Show Armor", "nametags.armor"),
            new SettingsOption.Toggle("Show Health", "nametags.health"),
            new SettingsOption.Toggle("Show Ping", "nametags.ping"),
            new SettingsOption.Toggle("Show Distance", "nametags.distance"),
            new SettingsOption.Slider("Scale", "nametags.scale", 50, 200, 5, "%")
        );
    }
}
