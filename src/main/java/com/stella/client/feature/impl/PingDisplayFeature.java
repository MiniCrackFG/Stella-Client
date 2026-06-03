package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;

import java.util.List;

public class PingDisplayFeature extends Feature {
    public PingDisplayFeature() {
        super("ping", "Ping Display", FeatureCategory.HUD);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Slider("Scale", "ping.scale", 50, 200, 5, "%"));
    }

    @Override
    public boolean isHudElement() { return true; }

    @Override
    public int getHudX() { return StellaConfig.getInstance().get("ping.x", 4); }
    @Override
    public int getHudY() { return StellaConfig.getInstance().get("ping.y", 80); }
    @Override
    public void setHudX(int x) { StellaConfig.getInstance().set("ping.x", x); }
    @Override
    public void setHudY(int y) { StellaConfig.getInstance().set("ping.y", y); }

    @Override
    public float getHudScale() {
        return StellaConfig.getInstance().get("ping.scale", 100) / 100f;
    }
    @Override
    public void setHudScale(float s) {
        StellaConfig.getInstance().set("ping.scale", Math.round(s * 100));
    }

    @Override
    public HudBounds getHudBounds() {
        float sc = getHudScale();
        return new HudBounds(getHudX(), getHudY(), (int)(80 * sc), (int)(10 * sc));
    }

    @Override
    public void onRender(GuiGraphics g, float delta) {
        float sc = getHudScale();
        int x = getHudX();
        int y = getHudY();

        int ping = 0;
        if (mc.getConnection() != null && mc.player != null) {
            var info = mc.getConnection().getPlayerInfo(mc.player.getUUID());
            if (info != null) ping = info.getLatency();
        }

        String color = ping < 100 ? "§a" : ping < 200 ? "§e" : "§c";
        g.drawString(mc.font, Component.literal("§fPing: " + color + ping + "ms"), x, y, 0xFFFFFFFF);
    }
}
