package com.stella.client.feature;

import com.stella.client.feature.impl.*;

import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.GuiGraphics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class FeatureManager {
    private static final Logger LOGGER = LoggerFactory.getLogger("FeatureManager");
    private static final FeatureManager INSTANCE = new FeatureManager();
    private final List<Feature> features = new ArrayList<>();

    public static FeatureManager getInstance() {
        return INSTANCE;
    }

    @SuppressWarnings("deprecation")
    public void init() {
        register(new KeystrokesFeature());
        register(new HudFeature());
        register(new ZoomFeature());
        register(new FreeLookFeature());
        register(new FullbrightFeature());
        register(new PingDisplayFeature());
        register(new ArmorHudFeature());
        register(new PotionTimersFeature());
        register(new ToggleSprintFeature());
        register(new ToggleSneakFeature());
        register(new AutoToolFeature());
        register(new AutoEatFeature());
        register(new FreecamFeature());
        register(new CustomCrosshairFeature());
        register(new TimeChangerFeature());
        register(new WeatherChangerFeature());
        register(new MotionBlurFeature());
        register(new NametagsFeature());
        register(new FastPlaceFeature());
        register(new WaypointsFeature());

        HudRenderCallback.EVENT.register((guiGraphics, deltaTracker) -> {
            onHudRender(guiGraphics, (DeltaTracker) deltaTracker);
        });
        ClientTickEvents.START_CLIENT_TICK.register(client -> {
            for (var f : features) {
                if (f.isEnabled()) f.onStartTick();
            }
        });
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            for (var f : features) {
                if (f.isEnabled()) f.onTick();
            }
        });

        LOGGER.info("FeatureManager initialized with {} features", features.size());
    }

    private void register(Feature feature) {
        features.add(feature);
        if (feature.isEnabled()) {
            try {
                feature.onEnable();
            } catch (Exception e) {
                LOGGER.warn("Error enabling feature {}: {}", feature.getId(), e.getMessage());
            }
        }
    }

    public List<Feature> getFeatures() {
        return features;
    }

    public List<Feature> getFeaturesByCategory(FeatureCategory category) {
        return features.stream().filter(f -> f.getCategory() == category).toList();
    }

    @SuppressWarnings("unchecked")
    public <T extends Feature> T getFeature(String id) {
        return (T) features.stream().filter(f -> f.getId().equals(id)).findFirst().orElse(null);
    }

    private void onHudRender(GuiGraphics guiGraphics, DeltaTracker deltaTracker) {
        float delta = (float) deltaTracker.getRealtimeDeltaTicks();
        for (var f : features) {
            if (f.isEnabled()) {
                try {
                    f.onRender(guiGraphics, delta);
                } catch (Exception e) {
                    LOGGER.warn("Error rendering feature {}: {}", f.getId(), e.getMessage());
                }
            }
        }
    }
}
