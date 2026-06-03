package com.stella.client.ui;

import com.stella.client.StellaClientMod;
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
    private static final int PANEL_W = 360;
    private static final int PANEL_H = 340;

    private int panelX, panelY;

    public StellaScreen() {
        super(Component.literal("Stella Client"));
    }

    @Override
    protected void init() {
        panelX = (width - PANEL_W) / 2;
        panelY = (height - PANEL_H) / 2;

        int cx = width / 2;
        int by = panelY + 105;

        addRenderableWidget(new StellaButton(cx - 100, by, 200, 36,
                "⚡ Features",
                () -> minecraft.setScreen(new StellaSettingsScreen(this))));

        addRenderableWidget(new StellaButton(cx - 100, by + 48, 200, 36,
                "🔧 Settings",
                () -> minecraft.setScreen(new StellaClientSettingsScreen(this))));

        addRenderableWidget(new StellaButton(cx - 100, by + 96, 200, 36,
                "✕ Close",
                this::onClose));
    }

    @Override
    public void renderBackground(GuiGraphics g, int mx, int my, float delta) {
        g.fill(0, 0, width, height, 0xAA0A0A1A);
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        int pr = panelX + PANEL_W;
        int pb = panelY + PANEL_H;

        g.fill(panelX, panelY, pr, pb, 0xE0101028);
        g.fill(panelX, panelY, pr, panelY + 2, 0xFF6B8CFF);
        g.fill(panelX, panelY, panelX + 2, pb, 0x206B8CFF);
        g.fill(pr - 2, panelY, pr, pb, 0x206B8CFF);

        int cx = width / 2;

        g.drawCenteredString(font, Component.literal("§lStella Client"),
                cx, panelY + 28, 0xFFFFFFFF);

        g.fill(panelX + 80, panelY + 48, pr - 80, panelY + 49, 0x30FFFFFF);

        var conn = StellaClient.getInstance().getConnection();
        boolean connected = conn.isConnected();
        int sc = connected ? 0xFF55FF55 : 0xFFFF5555;
        g.drawCenteredString(font,
                Component.literal((connected ? "●" : "○") + " " + (connected ? "Connected" : "Disconnected")),
                cx, panelY + 62, sc);

        g.fill(panelX + 80, panelY + 78, pr - 80, panelY + 79, 0x30FFFFFF);

        g.drawCenteredString(font,
                Component.literal("v" + StellaClientMod.MOD_VERSION),
                cx, panelY + PANEL_H - 20, 0xFF444466);

        super.render(g, mx, my, delta);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) { onClose(); return true; }
        return super.keyPressed(keyEvent);
    }

    @Override
    public boolean isPauseScreen() { return false; }

    public static class StellaButton extends AbstractButton {
        private static final int NORM = 0x802A2A5A;
        private static final int HOV = 0xCC3A3A7A;
        private static final int TNORM = 0xFFCCCCCC;
        private static final int THOV = 0xFFFFFFFF;

        private final Runnable onClick;
        private float hoverT;

        public StellaButton(int x, int y, int w, int h, String label, Runnable onClick) {
            super(x, y, w, h, Component.literal(label));
            this.onClick = onClick;
        }

        @Override
        public void onPress(InputWithModifiers input) {
            onClick.run();
        }

        @Override
        protected void renderContents(GuiGraphics g, int mx, int my, float delta) {
            if (!visible) return;

            boolean hovered = isHoveredOrFocused();
            hoverT += (hovered ? 1 : -1) * delta * 5;
            hoverT = Math.clamp(hoverT, 0, 1);

            int bg = lerpColor(NORM, HOV, hoverT);
            int tc = lerpColor(TNORM, THOV, hoverT);

            g.fill(getX(), getY(), getX() + getWidth(), getY() + getHeight(), bg);

            int accentH = (int) (2 + hoverT * 2);
            g.fill(getX(), getY(), getX() + getWidth(), getY() + accentH, 0xFF6B8CFF);

            if (hovered) {
                g.fill(getX(), getY(), getX() + getWidth(), getY() + getHeight(), 0x106B8CFF);
            }

            g.drawCenteredString(Minecraft.getInstance().font, getMessage(),
                    getX() + getWidth() / 2, getY() + (getHeight() - 8) / 2, tc);
        }

        private static int lerpColor(int a, int b, float t) {
            int ar = (a >> 16) & 0xFF, ag = (a >> 8) & 0xFF, ab = a & 0xFF, aa = (a >> 24) & 0xFF;
            int br = (b >> 16) & 0xFF, bg = (b >> 8) & 0xFF, bb = b & 0xFF, ba = (b >> 24) & 0xFF;
            int r = (int) (ar + (br - ar) * t);
            int g_ = (int) (ag + (bg - ag) * t);
            int bl = (int) (ab + (bb - ab) * t);
            int a_ = (int) (aa + (ba - aa) * t);
            return (a_ << 24) | (r << 16) | (g_ << 8) | bl;
        }

        @Override
        protected void updateWidgetNarration(NarrationElementOutput out) {}
    }
}
