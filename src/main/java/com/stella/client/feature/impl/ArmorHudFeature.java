package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class ArmorHudFeature extends Feature {
    public ArmorHudFeature() {
        super("armor_hud", "Armor HUD", FeatureCategory.HUD);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Slider("Scale", "armor.scale", 50, 200, 5, "%"),
            new SettingsOption.Toggle("Show Durability", "armor.durability")
        );
    }

    @Override
    public boolean isHudElement() { return true; }

    @Override
    public int getHudX() { return StellaConfig.getInstance().get("armor.x", 4); }
    @Override
    public int getHudY() { return StellaConfig.getInstance().get("armor.y", 60); }
    @Override
    public void setHudX(int x) { StellaConfig.getInstance().set("armor.x", x); }
    @Override
    public void setHudY(int y) { StellaConfig.getInstance().set("armor.y", y); }

    @Override
    public float getHudScale() {
        return StellaConfig.getInstance().get("armor.scale", 100) / 100f;
    }
    @Override
    public void setHudScale(float s) {
        StellaConfig.getInstance().set("armor.scale", Math.round(s * 100));
    }

    @Override
    public HudBounds getHudBounds() {
        float sc = getHudScale();
        return new HudBounds(getHudX(), getHudY(), (int)(80 * sc), (int)(40 * sc));
    }

    @Override
    public void onRender(GuiGraphics g, float delta) {
        if (mc.player == null) return;

        float sc = getHudScale();
        int x = getHudX();
        int y = getHudY();
        boolean showDur = StellaConfig.getInstance().get("armor.durability", true);

        EquipmentSlot[] slots = {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};
        for (int i = 0; i < 4; i++) {
            ItemStack stack = mc.player.getItemBySlot(slots[i]);
            int ix = x + (3 - i) * 18;
            int iy = y;

            g.renderItem(stack, (int)(ix * sc), (int)(iy * sc));
            g.renderItemDecorations(mc.font, stack, (int)(ix * sc), (int)(iy * sc));

            if (showDur && stack.isDamageableItem()) {
                int maxDmg = stack.getMaxDamage();
                int dmg = stack.getDamageValue();
                int dur = maxDmg - dmg;
                int pct = (int)((float)dur / maxDmg * 100);
                String color = pct > 50 ? "§a" : pct > 20 ? "§e" : "§c";
                g.drawString(mc.font, Component.literal(color + pct + "%"),
                    (int)(ix * sc), (int)((iy + 16) * sc), 0xFFFFFFFF);
            }
        }
    }
}
