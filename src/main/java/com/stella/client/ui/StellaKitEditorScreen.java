package com.stella.client.ui;

import com.stella.client.StellaClientMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;

public class StellaKitEditorScreen extends Screen {
    private static final int PANEL_W = 400;
    private static final int PANEL_H = 300;

    private final Screen parent;

    public StellaKitEditorScreen(Screen parent) {
        super(Component.literal("Stella"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int gx = (width - PANEL_W) / 2;
        int gy = (height - PANEL_H) / 2;
        int cx = width / 2;

        addRenderableWidget(new StellaScreen.StellaButton(cx - 90, gy + 100, 180, 36,
                "⚡ Mods",
                () -> minecraft.setScreen(new StellaSettingsScreen(this))));

        addRenderableWidget(new StellaScreen.StellaButton(cx - 90, gy + 148, 180, 36,
                "🔧 Settings",
                () -> minecraft.setScreen(new StellaClientSettingsScreen(this))));

        addRenderableWidget(new StellaScreen.StellaButton(cx - 90, gy + 196, 180, 36,
                "✕ Close",
                this::onClose));
    }

    @Override
    public void renderBackground(GuiGraphics g, int mx, int my, float delta) {
        g.fill(0, 0, width, height, 0xCC0A0A1A);
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        int gx = (width - PANEL_W) / 2;
        int gy = (height - PANEL_H) / 2;
        int cx = width / 2;

        g.fill(gx, gy, gx + PANEL_W, gy + PANEL_H, 0xE0101028);
        g.fill(gx, gy, gx + PANEL_W, gy + 2, 0xFF6B8CFF);
        g.fill(gx, gy + PANEL_H - 2, gx + PANEL_W, gy + PANEL_H, 0x206B8CFF);

        g.drawCenteredString(font, Component.literal("§lSTELLA"),
                cx, gy + 30, 0xFFFFFFFF);
        g.drawCenteredString(font, Component.literal("§7Client Mod · v" + StellaClientMod.MOD_VERSION),
                cx, gy + 52, 0xFF666688);

        g.fill(gx + 60, gy + 68, gx + PANEL_W - 60, gy + 69, 0x30FFFFFF);

        super.render(g, mx, my, delta);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) { onClose(); return true; }
        return super.keyPressed(keyEvent);
    }

    @Override
    public boolean isPauseScreen() { return false; }
}
