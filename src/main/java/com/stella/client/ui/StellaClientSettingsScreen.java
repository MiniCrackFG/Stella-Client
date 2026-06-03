package com.stella.client.ui;

import com.stella.client.StellaClient;
import com.stella.client.StellaClientMod;
import com.stella.client.config.StellaConfig;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;

public class StellaClientSettingsScreen extends Screen {
    private static final int PANEL_W = 340;
    private static final int PANEL_H = 260;

    private final Screen parent;
    private int gx, gy;

    public StellaClientSettingsScreen(Screen parent) {
        super(Component.literal("Client Settings"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        gx = (width - PANEL_W) / 2;
        gy = (height - PANEL_H) / 2;

        int cx = width / 2;
        int by = gy + 100;

        addRenderableWidget(new StellaScreen.StellaButton(cx - 100, by, 200, 34,
                "Reset to Defaults",
                this::resetDefaults));

        addRenderableWidget(new StellaScreen.StellaButton(cx - 100, by + 48, 200, 34,
                "✕ Close",
                () -> minecraft.setScreen(parent)));
    }

    private void resetDefaults() {
        var file = StellaConfig.getInstance().getPath().toFile();
        if (file.exists()) file.delete();
        StellaConfig.getInstance().load();
        minecraft.setScreen(parent);
    }

    @Override
    public void renderBackground(GuiGraphics g, int mx, int my, float delta) {
        g.fill(0, 0, width, height, 0xAA0A0A1A);
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        int pr = gx + PANEL_W;
        int pb = gy + PANEL_H;

        g.fill(gx, gy, pr, pb, 0xE0101028);
        g.fill(gx, gy, pr, gy + 2, 0xFF6B8CFF);

        int cx = width / 2;
        g.drawCenteredString(font, Component.literal("§lClient Settings"),
                cx, gy + 28, 0xFFFFFFFF);

        g.fill(gx + 80, gy + 48, pr - 80, gy + 49, 0x30FFFFFF);

        var conn = StellaClient.getInstance().getConnection();
        boolean connected = conn.isConnected();
        int sc = connected ? 0xFF55FF55 : 0xFFFF5555;
        g.drawCenteredString(font,
                Component.literal((connected ? "●" : "○") + " " + (connected ? "Connected" : "Disconnected")),
                cx, gy + 65, sc);

        g.drawCenteredString(font,
                Component.literal("v" + StellaClientMod.MOD_VERSION),
                cx, gy + PANEL_H - 18, 0xFF444466);

        super.render(g, mx, my, delta);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) { minecraft.setScreen(parent); return true; }
        return super.keyPressed(keyEvent);
    }

    @Override
    public boolean isPauseScreen() { return false; }
}
