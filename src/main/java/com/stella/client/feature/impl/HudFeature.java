package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import com.stella.client.mixin.MinecraftAccessor;
import net.minecraft.client.gui.GuiGraphics;

import java.util.List;

public class HudFeature extends Feature {
    public HudFeature() {
        super("hud", "HUD Info", FeatureCategory.HUD);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
                new SettingsOption.Slider("Scale", "hud.scale", 50, 200, 5, "%"),
                new SettingsOption.Toggle("Show FPS", "hud.fps"),
                new SettingsOption.Toggle("Show Coords", "hud.coords"),
                new SettingsOption.Toggle("Show Direction", "hud.direction"),
                new SettingsOption.Toggle("Show Biome", "hud.biome")
        );
    }

    @Override
    public boolean isHudElement() { return true; }

    @Override
    public int getHudX() { return StellaConfig.getInstance().get("hud.x", 4); }
    @Override
    public int getHudY() { return StellaConfig.getInstance().get("hud.y", 4); }
    @Override
    public void setHudX(int x) { StellaConfig.getInstance().set("hud.x", x); }
    @Override
    public void setHudY(int y) { StellaConfig.getInstance().set("hud.y", y); }

    @Override
    public float getHudScale() {
        return StellaConfig.getInstance().get("hud.scale", 100) / 100f;
    }
    @Override
    public void setHudScale(float s) {
        StellaConfig.getInstance().set("hud.scale", Math.round(s * 100));
    }

    @Override
    public HudBounds getHudBounds() {
        int lines = 0;
        var config = StellaConfig.getInstance();
        if (config.get("hud.fps", true)) lines++;
        if (config.get("hud.coords", true)) lines++;
        if (config.get("hud.direction", true)) lines++;
        if (config.get("hud.biome", false)) lines++;
        int h = lines * 10;
        int w = 150;
        return new HudBounds(getHudX(), getHudY(), (int)(w * getHudScale()), (int)(h * getHudScale()));
    }

    @Override
    public void onRender(GuiGraphics g, float delta) {
        var config = StellaConfig.getInstance();
        float sc = getHudScale();
        int x = getHudX();
        int y = getHudY();

        if (config.get("hud.fps", true)) {
            int fps = ((MinecraftAccessor) mc).getFps();
            g.drawString(mc.font, "§fFPS: §e" + fps, x, y, 0xFFFFFFFF);
            y += (int)(10 * sc);
        }

        if (config.get("hud.coords", true) && mc.player != null) {
            var pos = mc.player.blockPosition();
            String text = String.format("§fXYZ: §e%d §7/ §e%d §7/ §e%d", pos.getX(), pos.getY(), pos.getZ());
            g.drawString(mc.font, text, x, y, 0xFFFFFFFF);
            y += (int)(10 * sc);
        }

        if (config.get("hud.direction", true) && mc.player != null) {
            String d = mc.player.getDirection().getName();
            String label = d.substring(0, 1).toUpperCase() + d.substring(1);
            g.drawString(mc.font, "§fFacing: §e" + label, x, y, 0xFFFFFFFF);
            y += (int)(10 * sc);
        }

        if (config.get("hud.biome", false) && mc.player != null && mc.level != null) {
            var biome = mc.level.getBiome(mc.player.blockPosition());
            String name = biome.getRegisteredName();
            if (name.contains(":")) name = name.split(":")[1];
            g.drawString(mc.font, "§fBiome: §e" + name, x, y, 0xFFFFFFFF);
        }
    }
}
