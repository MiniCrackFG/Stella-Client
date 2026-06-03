package com.stella.client.feature;

import com.stella.client.config.StellaConfig;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;

import java.util.List;

public abstract class Feature {
    protected final String id;
    protected final String name;
    protected final FeatureCategory category;
    protected final Minecraft mc;
    protected KeyMapping keybind;

    public Feature(String id, String name, FeatureCategory category) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.mc = Minecraft.getInstance();
    }

    public String getId() { return id; }
    public String getName() { return name; }
    public FeatureCategory getCategory() { return category; }
    public KeyMapping getKeybind() { return keybind; }

    public boolean isEnabled() {
        return StellaConfig.getInstance().get("feature." + id, false);
    }

    public void setEnabled(boolean enabled) {
        StellaConfig.getInstance().set("feature." + id, enabled);
        if (enabled) onEnable();
        else onDisable();
    }

    public boolean toggle() {
        boolean next = !isEnabled();
        setEnabled(next);
        return next;
    }

    public void onEnable() {}
    public void onDisable() {}
    public void onStartTick() {}
    public void onTick() {}
    public void onRender(GuiGraphics guiGraphics, float delta) {}

    public List<SettingsOption> getSettings() { return List.of(); }

    public boolean isHudElement() { return false; }
    public HudBounds getHudBounds() { return null; }
    public void setHudX(int x) {}
    public void setHudY(int y) {}
    public int getHudX() { return 0; }
    public int getHudY() { return 0; }
    public void setHudScale(float scale) {}
    public float getHudScale() { return 1.0f; }
    public void renderForEditor(GuiGraphics g, float delta) { onRender(g, delta); }

    public record HudBounds(int x, int y, int width, int height) {}
}
