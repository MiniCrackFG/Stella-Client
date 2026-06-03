package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;

import java.util.List;

public class WeatherChangerFeature extends Feature {
    public WeatherChangerFeature() {
        super("weather_changer", "Weather Changer", FeatureCategory.VISUAL);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Select("Mode", "weather_changer.mode", new String[]{"Clear", "Rain", "Thunder"})
        );
    }
}
