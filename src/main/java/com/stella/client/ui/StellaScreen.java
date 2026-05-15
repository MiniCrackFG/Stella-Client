package com.stella.client.ui;

import com.stella.client.StellaClient;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class StellaScreen extends Screen {
    private static final int TITLE_COLOR = 0xFFFFFF;
    private static final int ACCENT_COLOR = 0x6B8CFF;

    public StellaScreen() {
        super(Component.literal("Stella Client"));
    }

    @Override
    protected void init() {
        int centerX = width / 2;
        int centerY = height / 2;

        addRenderableWidget(Button.builder(
                Component.literal("Connect to Stella"),
                button -> StellaClient.getInstance().getConnection().connect()
        ).bounds(centerX - 75, centerY - 30, 150, 20).build());

        addRenderableWidget(Button.builder(
                Component.literal("Settings"),
                button -> {}
        ).bounds(centerX - 75, centerY, 150, 20).build());

        addRenderableWidget(Button.builder(
                Component.literal("About"),
                button -> {}
        ).bounds(centerX - 75, centerY + 30, 150, 20).build());

        addRenderableWidget(Button.builder(
                Component.literal("Back"),
                button -> onClose()
        ).bounds(centerX - 75, centerY + 60, 150, 20).build());
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        super.render(guiGraphics, mouseX, mouseY, delta);

        int centerX = width / 2;
        int titleY = height / 2 - 80;

        guiGraphics.drawCenteredString(
                font,
                Component.literal("Stella Client"),
                centerX, titleY, TITLE_COLOR
        );

        var statusText = StellaClient.getInstance().getConnection().isConnected()
                ? Component.literal("Connected").withColor(0x55FF55)
                : Component.literal("Disconnected").withColor(0xFF5555);
        guiGraphics.drawCenteredString(
                font,
                Component.literal("Status: ").append(statusText),
                centerX, titleY + 20, 0xAAAAAA
        );
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
