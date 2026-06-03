package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class MotionBlurFeature extends Feature {
    public MotionBlurFeature() {
        super("motion_blur", "Motion Blur", FeatureCategory.VISUAL);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Slider("Intensity", "motion_blur.intensity", 1, 100, 1, "%")
        );
    }

    @Override
    public void onEnable() {
    }

    @Override
    public void onDisable() {
    }
}
