package com.stella.client.ui;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;

public class StellaSettingsScreen extends Screen {
    private static final int PANEL_WIDTH = 320;
    private static final int PANEL_HEIGHT = 200;

    private final Screen parent;
    private int panelX, panelY;

    public StellaSettingsScreen(Screen parent) {
        super(Component.literal("Stella Settings"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        panelX = (width - PANEL_WIDTH) / 2;
        panelY = (height - PANEL_HEIGHT) / 2;

        addRenderableWidget(new StellaScreen.ModernButton(
                width / 2 - 60, panelY + 110, 120, 28,
                Component.literal("Back"),
                () -> minecraft.setScreen(parent)));
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(0, 0, width, height, 0x88000000);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(0, 0, width, height, 0x88000000);

        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + PANEL_HEIGHT, 0xC81A1A2E);
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + 1, 0xFF6B8CFF);

        guiGraphics.drawCenteredString(font, Component.literal("Settings"),
                width / 2, panelY + 25, 0xFFFFFF);

        guiGraphics.drawCenteredString(font,
                Component.literal("More options coming soon..."),
                width / 2, panelY + 70, 0x666666);

        super.render(guiGraphics, mouseX, mouseY, delta);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        int code = keyEvent.key();
        if (code == 344 || code == 340 || code == 256) {
            minecraft.setScreen(parent);
            return true;
        }
        return super.keyPressed(keyEvent);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
