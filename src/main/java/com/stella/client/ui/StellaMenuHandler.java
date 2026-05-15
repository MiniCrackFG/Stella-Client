package com.stella.client.ui;

import com.mojang.blaze3d.platform.InputConstants;
import com.stella.client.StellaClientMod;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;

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

        StellaClientMod.LOGGER.info("Stella menu handler registered (press O to open)");
    }

    private static void openMenu(Minecraft client) {
        if (client.screen instanceof StellaScreen) return;
        client.setScreen(new StellaScreen());
    }
}
