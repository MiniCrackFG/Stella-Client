package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.world.effect.MobEffectInstance;

import java.util.List;

public class PotionTimersFeature extends Feature {
    public PotionTimersFeature() {
        super("potion_timers", "Potion Timers", FeatureCategory.HUD);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Slider("Scale", "potion_timers.scale", 50, 200, 5, "%"));
    }

    @Override
    public boolean isHudElement() { return true; }

    @Override
    public int getHudX() { return StellaConfig.getInstance().get("potion_timers.x", 4); }
    @Override
    public int getHudY() { return StellaConfig.getInstance().get("potion_timers.y", 100); }
    @Override
    public void setHudX(int x) { StellaConfig.getInstance().set("potion_timers.x", x); }
    @Override
    public void setHudY(int y) { StellaConfig.getInstance().set("potion_timers.y", y); }

    @Override
    public float getHudScale() {
        return StellaConfig.getInstance().get("potion_timers.scale", 100) / 100f;
    }
    @Override
    public void setHudScale(float s) {
        StellaConfig.getInstance().set("potion_timers.scale", Math.round(s * 100));
    }

    @Override
    public HudBounds getHudBounds() {
        float sc = getHudScale();
        return new HudBounds(getHudX(), getHudY(), (int)(80 * sc), (int)(30 * sc));
    }

    @Override
    public void onRender(GuiGraphics g, float delta) {
        if (mc.player == null) return;

        float sc = getHudScale();
        int x = getHudX();
        int y = getHudY();

        var effects = mc.player.getActiveEffects();
        int i = 0;
        for (MobEffectInstance effect : effects) {
            String name = effect.getEffect().value().getDisplayName().getString();
            int duration = effect.getDuration() / 20;
            int minutes = duration / 60;
            int seconds = duration % 60;
            String time = String.format("%d:%02d", minutes, seconds);
            int amp = effect.getAmplifier() + 1;

            String color = effect.getEffect().value().getCategory().getTooltipFormatting().toString();
            g.drawString(mc.font, Component.literal(color + name + " " + amp + " §7" + time),
                x, y + i * 10, 0xFFFFFFFF);
            i++;
        }
    }
}
