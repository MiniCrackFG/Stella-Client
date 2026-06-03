package com.stella.client.ui;

import com.mojang.blaze3d.platform.InputConstants;
import com.stella.client.StellaClientMod;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.Identifier;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.List;

public class StellaMenuHandler {
    public static final KeyMapping.Category CATEGORY = KeyMapping.Category.register(Identifier.fromNamespaceAndPath("stella-client", "category"));

    private static KeyMapping menuKeyBinding;

    public static void register() {
        menuKeyBinding = KeyBindingHelper.registerKeyBinding(new KeyMapping(
                "key.stella.open_menu",
                InputConstants.Type.KEYSYM,
                InputConstants.KEY_RSHIFT,
                CATEGORY
        ));

        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.player == null) return;
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

        StellaClientMod.LOGGER.info("Stella menu handler registered");
    }

    private static boolean isTrigger(Player player, InteractionHand hand) {
        if (hand != InteractionHand.MAIN_HAND) return false;
        if (!player.isShiftKeyDown()) return false;
        ItemStack stack = player.getItemInHand(hand);
        return stack.isEmpty();
    }

    private static final List<Class<?>> STELLA_SCREENS = List.of(
            StellaKitEditorScreen.class, StellaSettingsScreen.class,
            StellaClientSettingsScreen.class, HudEditorScreen.class);

    private static void openMenu(Minecraft client) {
        for (var cls : STELLA_SCREENS) {
            if (cls.isInstance(client.screen)) return;
        }
        client.setScreen(new StellaKitEditorScreen(client.screen));
    }
}
