package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;

public class FullbrightFeature extends Feature {
    private static final double MAX_GAMMA = 15.0;
    private Double previousGamma;

    public FullbrightFeature() {
        super("fullbright", "Fullbright", FeatureCategory.VISUAL);
    }

    @Override
    public void onEnable() {
        if (mc.options != null) {
            previousGamma = mc.options.gamma().get();
            mc.options.gamma().set(MAX_GAMMA);
        }
    }

    @Override
    public void onDisable() {
        if (previousGamma != null && mc.options != null) {
            mc.options.gamma().set(previousGamma);
            previousGamma = null;
        }
    }
}
