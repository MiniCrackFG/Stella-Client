package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class AutoEatFeature extends Feature {
    private int prevSlot = -1;
    private boolean eating;

    public AutoEatFeature() {
        super("auto_eat", "Auto Eat", FeatureCategory.GAMEPLAY);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Slider("Health Threshold", "auto_eat.health", 1, 20, 1, "❤"),
            new SettingsOption.Toggle("Search Inventory", "auto_eat.inventory")
        );
    }

    @Override
    public void onTick() {
        if (mc.player == null) return;

        if (eating) {
            if (!mc.player.isUsingItem()) {
                eating = false;
                if (prevSlot != -1) {
                    mc.player.getInventory().setSelectedSlot(prevSlot);
                    prevSlot = -1;
                }
            }
            return;
        }

        if (mc.player.isUsingItem()) return;
        if (!mc.player.getFoodData().needsFood()) return;

        for (int i = 0; i < 9; i++) {
            ItemStack stack = mc.player.getInventory().getItem(i);
            if (isFood(stack)) {
                prevSlot = mc.player.getInventory().getSelectedSlot();
                mc.player.getInventory().setSelectedSlot(i);
                mc.options.keyUse.setDown(true);
                eating = true;
                return;
            }
        }

        boolean searchInv = StellaConfig.getInstance().get("auto_eat.inventory", true);
        if (searchInv) {
            for (int i = 9; i < 36; i++) {
                ItemStack stack = mc.player.getInventory().getItem(i);
                if (isFood(stack)) {
                    prevSlot = mc.player.getInventory().getSelectedSlot();
                    mc.player.getInventory().setSelectedSlot(i < 9 ? i : 0);
                    eating = true;
                    return;
                }
            }
        }
    }

    private boolean isFood(ItemStack stack) {
        FoodProperties food = stack.get(net.minecraft.core.component.DataComponents.FOOD);
        return food != null && !stack.is(net.minecraft.world.item.Items.CHORUS_FRUIT);
    }
}
