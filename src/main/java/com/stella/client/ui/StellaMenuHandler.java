package com.stella.client.ui;

import com.mojang.blaze3d.platform.InputConstants;
import com.stella.client.StellaClientMod;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

public class StellaMenuHandler {
    private static KeyMapping menuKeyBinding;

    public static void register() {
        menuKeyBinding = KeyBindingHelper.registerKeyBinding(new KeyMapping(
                "key.stella.open_menu",
                InputConstants.Type.KEYSYM,
                79,
                KeyMapping.Category.MISC
        ));

        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (menuKeyBinding.consumeClick()) {
                openMenu(client);
            }
        });

        UseBlockCallback.EVENT.register((player, world, hand, hitResult) -> {
            if (isTrigger(player, hand)) {
                openMenu(Minecraft.getInstance());
                return InteractionResult.FAIL;
            }
            return InteractionResult.PASS;
        });

        UseItemCallback.EVENT.register((player, world, hand) -> {
            if (isTrigger(player, hand)) {
                openMenu(Minecraft.getInstance());
                return InteractionResult.FAIL;
            }
            return InteractionResult.PASS;
        });

        StellaClientMod.LOGGER.info("Stella menu handler registered (Shift+RightClick or O)");
    }

    private static boolean isTrigger(Player player, InteractionHand hand) {
        if (hand != InteractionHand.MAIN_HAND) return false;
        if (!player.isShiftKeyDown()) return false;
        ItemStack stack = player.getItemInHand(hand);
        return stack.isEmpty();
    }

    private static void openMenu(Minecraft client) {
        if (client.screen instanceof StellaScreen) return;
        client.setScreen(new StellaScreen());
    }
}
