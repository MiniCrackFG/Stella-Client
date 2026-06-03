package com.stella.client.feature.impl;

import com.mojang.blaze3d.platform.InputConstants;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.ui.StellaMenuHandler;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.gui.GuiGraphics;
import org.lwjgl.glfw.GLFW;

public class FreeLookFeature extends Feature {
    private static FreeLookFeature INSTANCE;

    private boolean active;
    private float bodyYaw;
    private float bodyPitch;
    private float freelookYaw;
    private float freelookPitch;

    public FreeLookFeature() {
        super("freelook", "Freelook", FeatureCategory.GAMEPLAY);
        INSTANCE = this;
        keybind = KeyBindingHelper.registerKeyBinding(new KeyMapping(
                "key.stella.freelook",
                InputConstants.Type.KEYSYM,
                GLFW.GLFW_KEY_LEFT_ALT,
                StellaMenuHandler.CATEGORY
        ));
    }

    public static FreeLookFeature getInstance() {
        return INSTANCE;
    }

    @Override
    public void onStartTick() {
        if (mc.player == null) return;

        boolean pressed = keybind != null && keybind.isDown();

        if (pressed && !active) {
            active = true;
            bodyYaw = mc.player.getYRot();
            bodyPitch = mc.player.getXRot();
            freelookYaw = bodyYaw;
            freelookPitch = bodyPitch;
        }

        if (active) {
            mc.player.setYRot(bodyYaw);
            mc.player.setXRot(bodyPitch);
        }
    }

    @Override
    public void onTick() {
        if (mc.player == null) return;

        if (!active && keybind != null && !keybind.isDown()) return;

        if (active && keybind != null && !keybind.isDown()) {
            active = false;
            mc.player.setYRot(freelookYaw);
            mc.player.setXRot(freelookPitch);
        }
    }

    public void addRotationDelta(double yawDelta, double pitchDelta) {
        if (!active) return;
        freelookYaw = (float) ((double) freelookYaw + yawDelta);
        freelookPitch = (float) Math.clamp((double) freelookPitch + pitchDelta, -90.0, 90.0);
    }

    @Override
    public void onRender(GuiGraphics g, float delta) {
        if (!active) return;
        int sw = mc.getWindow().getGuiScaledWidth();
        String text = "§b§l✦ Freelook";
        g.drawString(mc.font, text, sw / 2 - mc.font.width(text) / 2, 8, 0xFFFFFFFF);
    }

    public boolean isActive() { return active; }
    public float getCameraYaw() { return freelookYaw; }
    public float getCameraPitch() { return freelookPitch; }
}
