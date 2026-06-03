package com.stella.client.feature;

public enum FeatureCategory {
    HUD("HUD"),
    VISUAL("Visual"),
    GAMEPLAY("Gameplay");

    private final String displayName;

    FeatureCategory(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }
}
