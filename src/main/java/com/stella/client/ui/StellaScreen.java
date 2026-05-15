package com.stella.client.ui;

import com.stella.client.StellaClient;
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
    private static final int PANEL_HEIGHT = 280;

    private int panelX, panelY;

    public StellaScreen() {
        super(Component.literal("Stella Client"));
    }

    @Override
    protected void init() {
        panelX = (width - PANEL_WIDTH) / 2;
        panelY = (height - PANEL_HEIGHT) / 2;

        int cx = width / 2;
        int by = panelY + 130;

        addRenderableWidget(new ModernButton(cx - 90, by, 180, 32,
                Component.literal("Connect to Stella"),
                () -> StellaClient.getInstance().getConnection().connect()));

        addRenderableWidget(new ModernButton(cx - 90, by + 42, 180, 32,
                Component.literal("Settings"),
                () -> {}));

        addRenderableWidget(new ModernButton(cx - 90, by + 84, 180, 32,
                Component.literal("Close"),
                () -> onClose()));
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(0, 0, width, height, 0x88000000);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        renderBackground(guiGraphics, mouseX, mouseY, delta);

        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + PANEL_HEIGHT, 0xC81A1A2E);
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + 1, 0xFF6B8CFF);

        int cx = width / 2;
        guiGraphics.drawCenteredString(font, Component.literal("Stella Client"),
                cx, panelY + 30, 0xFFFFFF);

        var connected = StellaClient.getInstance().getConnection().isConnected();
        int statusColor = connected ? 0x55FF55 : 0xFF5555;
        String statusText = connected ? "● Connected" : "● Disconnected";
        guiGraphics.drawCenteredString(font, Component.literal(statusText),
                cx, panelY + 55, statusColor);

        guiGraphics.fill(panelX + 40, panelY + PANEL_HEIGHT - 30, panelX + PANEL_WIDTH - 40, panelY + PANEL_HEIGHT - 29, 0x96333355);

        super.render(guiGraphics, mouseX, mouseY, delta);
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        int code = keyEvent.key();
        if (code == 344 || code == 340) {
            onClose();
            return true;
        }
        return super.keyPressed(keyEvent);
    }

    private static class ModernButton extends AbstractButton {
        private static final int NORMAL = 0x802A2A4A;
        private static final int HOVERED = 0xCC3A3A6A;

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

            int color = isHoveredOrFocused() ? 0xFFFFFF : 0xAAAAAA;
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
