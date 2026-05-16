package com.stella.client.ui;

import com.stella.client.StellaClient;
import com.stella.client.StellaClientMod;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.AbstractButton;
import net.minecraft.client.gui.narration.NarrationElementOutput;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.InputWithModifiers;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;

public class StellaScreen extends Screen {
    private static final int PANEL_WIDTH = 320;
    private static final int PANEL_HEIGHT = 300;

    private int panelX, panelY;

    public StellaScreen() {
        super(Component.literal("Stella Client"));
    }

    @Override
    protected void init() {
        panelX = (width - PANEL_WIDTH) / 2;
        panelY = (height - PANEL_HEIGHT) / 2;

        int cx = width / 2;
        int by = panelY + 110;

        addRenderableWidget(new ModernButton(cx - 90, by, 180, 32,
                Component.literal("Open Mods"),
                () -> minecraft.setScreen(new StellaModsScreen(this))));

        addRenderableWidget(new ModernButton(cx - 90, by + 42, 180, 32,
                Component.literal("Settings"),
                () -> minecraft.setScreen(new StellaSettingsScreen(this))));

        addRenderableWidget(new ModernButton(cx - 90, by + 84, 180, 32,
                Component.literal("Close"),
                this::onClose));
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(0, 0, width, height, 0x88000000);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + PANEL_HEIGHT, 0xC81A1A2E);
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + 1, 0xFF6B8CFF);

        int cx = width / 2;
        guiGraphics.drawCenteredString(font, Component.literal("Stella Client"),
                cx, panelY + 25, 0xFFFFFFFF);

        var conn = StellaClient.getInstance().getConnection();
        boolean connected = conn.isConnected();
        int statusColor = connected ? 0xFF55FF55 : 0xFFFF5555;
        guiGraphics.drawCenteredString(font,
                Component.literal((connected ? "●" : "○") + " " + (connected ? "Connected" : "Disconnected")),
                cx, panelY + 48, statusColor);

        guiGraphics.fill(panelX + 40, panelY + PANEL_HEIGHT - 35, panelX + PANEL_WIDTH - 40, panelY + PANEL_HEIGHT - 34, 0x96333355);
        guiGraphics.drawCenteredString(font,
                Component.literal("v" + StellaClientMod.MOD_VERSION),
                cx, panelY + PANEL_HEIGHT - 22, 0xFF555555);

        super.render(guiGraphics, mouseX, mouseY, delta);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) {
            onClose();
            return true;
        }
        return super.keyPressed(keyEvent);
    }

    public static class ModernButton extends AbstractButton {
        private static final int NORMAL = 0x802A2A4A;
        private static final int HOVERED = 0xCC3A3A6A;
        private static final int TEXT_NORMAL = 0xFFCCCCCC;
        private static final int TEXT_HOVERED = 0xFFFFFFFF;

        private final Runnable onClick;

        public ModernButton(int x, int y, int w, int h, Component message, Runnable onClick) {
            super(x, y, w, h, message);
            this.onClick = onClick;
        }

        @Override
        protected void renderContents(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
            if (!visible) return;

            int bg = isHoveredOrFocused() ? HOVERED : NORMAL;
            guiGraphics.fill(getX(), getY(), getX() + getWidth(), getY() + getHeight(), bg);
            guiGraphics.fill(getX(), getY(), getX() + getWidth(), getY() + 1, 0xFF6B8CFF);

            int color = isHoveredOrFocused() ? TEXT_HOVERED : TEXT_NORMAL;
            guiGraphics.drawCenteredString(Minecraft.getInstance().font, getMessage(),
                    getX() + getWidth() / 2, getY() + (getHeight() - 8) / 2, color);
        }

        @Override
        public void onPress(InputWithModifiers input) {
            onClick.run();
        }

        @Override
        protected void updateWidgetNarration(NarrationElementOutput narrationElementOutput) {
        }
    }
}
