package com.stella.client.feature.impl;

import com.mojang.blaze3d.platform.InputConstants;
import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import com.stella.client.ui.StellaMenuHandler;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.KeyMapping;
import org.lwjgl.glfw.GLFW;

import java.util.List;

public class ZoomFeature extends Feature {
    private double currentFov = 1.0;
    private double targetFov = 1.0;
    private static final double ZOOM_FACTOR = 0.15;
    private static final double BASE_SPEED = 0.35;

    public ZoomFeature() {
        super("zoom", "Zoom", FeatureCategory.GAMEPLAY);
        keybind = KeyBindingHelper.registerKeyBinding(new KeyMapping(
                "key.stella.zoom",
                InputConstants.Type.KEYSYM,
                GLFW.GLFW_KEY_C,
                StellaMenuHandler.CATEGORY
        ));
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Slider("Zoom Speed", "zoom.speed", 1, 20, 1, ""));
    }

    @Override
    public void onTick() {
        boolean pressed = keybind != null && keybind.isDown();
        targetFov = pressed ? ZOOM_FACTOR : 1.0;
    }

    public double getFovMultiplier() {
        int speed = StellaConfig.getInstance().get("zoom.speed", 10);
        double frameSpeed = BASE_SPEED * speed / 10.0;
        currentFov += (targetFov - currentFov) * frameSpeed;
        if (Math.abs(currentFov - targetFov) < 0.0005) {
            currentFov = targetFov;
        }
        return currentFov;
    }
}
