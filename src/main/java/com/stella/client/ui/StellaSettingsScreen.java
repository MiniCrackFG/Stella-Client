package com.stella.client.ui;

import com.stella.client.StellaClient;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;

public class StellaSettingsScreen extends Screen {
    private static final int PANEL_WIDTH = 320;
    private static final int PANEL_HEIGHT = 260;

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
        int cx = width / 2;
        int by = panelY + 80;

        addRenderableWidget(new StellaScreen.ModernButton(cx - 80, by, 160, 28,
                Component.literal("Auto-Connect: ON"),
                () -> {
                    var conn = StellaClient.getInstance().getConnection();
                    if (conn.isConnected()) { conn.disconnect(); }
                    else { conn.connect(); }
                }));

        addRenderableWidget(new StellaScreen.ModernButton(cx - 80, by + 38, 160, 28,
                Component.literal("Reconnect: 5s"),
                () -> {}));

        addRenderableWidget(new StellaScreen.ModernButton(cx - 80, by + 76, 160, 28,
                Component.literal("Back"),
                () -> minecraft.setScreen(parent)));
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(0, 0, width, height, 0x88000000);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + PANEL_HEIGHT, 0xC81A1A2E);
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + 1, 0xFF6B8CFF);
        guiGraphics.drawCenteredString(font, Component.literal("Settings"),
                width / 2, panelY + 25, 0xFFFFFF);

        var conn = StellaClient.getInstance().getConnection();
        String status = conn.isConnected() ? "§a● Connected" : "§7○ Disconnected";
        guiGraphics.drawCenteredString(font, Component.literal("Server: " + status),
                width / 2, panelY + 50, 0xAAAAAA);

        super.render(guiGraphics, mouseX, mouseY, delta);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) {
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
