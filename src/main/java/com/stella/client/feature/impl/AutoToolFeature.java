package com.stella.client.feature.impl;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class AutoToolFeature extends Feature {
    private int prevSlot = -1;
    private boolean switched;

    public AutoToolFeature() {
        super("auto_tool", "Auto Tool", FeatureCategory.GAMEPLAY);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Toggle("Silent", "auto_tool.silent"));
    }

    @Override
    public void onTick() {
        if (mc.player == null || mc.hitResult == null) {
            reset();
            return;
        }

        if (!mc.options.keyAttack.isDown()) {
            reset();
            return;
        }

        if (mc.hitResult.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK) {
            reset();
            return;
        }

        BlockPos pos = net.minecraft.core.BlockPos.containing(mc.hitResult.getLocation());
        var state = mc.player.level().getBlockState(pos);

        int bestSlot = -1;
        float bestSpeed = 1.0f;

        for (int i = 0; i < 9; i++) {
            ItemStack stack = mc.player.getInventory().getItem(i);
            float speed = stack.getDestroySpeed(state);
            if (speed > bestSpeed) {
                bestSpeed = speed;
                bestSlot = i;
            }
        }

        if (bestSlot == -1 || bestSlot == mc.player.getInventory().getSelectedSlot()) return;

        if (!switched) {
            prevSlot = mc.player.getInventory().getSelectedSlot();
        }
        mc.player.getInventory().setSelectedSlot(bestSlot);
        switched = true;
    }

    private void reset() {
        if (switched && prevSlot != -1) {
            mc.player.getInventory().setSelectedSlot(prevSlot);
        }
        switched = false;
        prevSlot = -1;
    }
}
