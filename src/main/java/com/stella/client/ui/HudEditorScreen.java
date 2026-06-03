package com.stella.client.ui;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.Feature.HudBounds;
import com.stella.client.feature.FeatureManager;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.network.chat.Component;

import java.util.ArrayList;
import java.util.List;

public class HudEditorScreen extends Screen {
    private static final int[] COLORS = {0xFF6B8CFF, 0xFF4CAF50, 0xFFFF9800, 0xFFE91E63, 0xFF9C27B0};
    private static final int HANDLE = 10;
    private static final int M_H = 30;

    private final Screen parent;
    private final List<Feature> hudFeatures = new ArrayList<>();
    private Feature dragging;
    private int dragOffX, dragOffY;
    private Feature resizing;
    private int resizeStartX, resizeStartY;
    private float resizeStartScale;

    public HudEditorScreen(Screen parent) {
        super(Component.literal("HUD Editor"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        hudFeatures.clear();
        for (var f : FeatureManager.getInstance().getFeatures()) {
            if (f.isHudElement() && f.isEnabled()) {
                hudFeatures.add(f);
            }
        }
    }

    @Override
    public void renderBackground(GuiGraphics g, int mx, int my, float delta) {
        g.fill(0, 0, width, height, 0xAA0A0A1A);
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        int cx = width / 2;
        g.drawCenteredString(font, Component.literal("§lHUD Editor"), cx, 8, 0xFFFFFFFF);
        g.drawCenteredString(font, Component.literal("§7Drag to move · Bottom-right corner to resize · ESC to save"),
                cx, 22, 0xFF888888);

        StellaConfig.getInstance().save();

        for (int i = 0; i < hudFeatures.size(); i++) {
            var f = hudFeatures.get(i);
            HudBounds b = f.getHudBounds();
            if (b == null) continue;

            int color = COLORS[i % COLORS.length];
            int x = b.x(), y = b.y(), w = b.width(), h = b.height();

            f.renderForEditor(g, delta);

            g.fill(x - 2, y - 2, x + w + 2, y, color);
            g.fill(x - 2, y, x, y + h, color);
            g.fill(x + w, y, x + w + 2, y + h, color);
            g.fill(x - 2, y + h, x + w + 2, y + h + 2, color);

            String label = "§l" + f.getName();
            int lw = font.width(label) + 8;
            int ly = y - 12;
            g.fill(x - 2, ly, x - 2 + lw, ly + 10, 0xCC000000);
            g.fill(x - 2, ly, x - 2 + lw, ly + 1, color);
            g.drawString(font, Component.literal(label), x + 2, ly + 1, color);

            int hx = x + w - HANDLE + 2;
            int hy = y + h - HANDLE + 2;
            g.fill(hx, hy, hx + HANDLE, hy + HANDLE, 0xCC000000);
            g.fill(hx, hy, hx + HANDLE, hy + HANDLE - 1, color);
            g.fill(hx, hy, hx + HANDLE - 1, hy + HANDLE, color);

            String pct = String.format("%.0f%%", f.getHudScale() * 100);
            g.drawString(font, Component.literal(pct), hx + 1, hy + 1, 0xFFFFFFFF);
        }

        if (dragging != null) {
            String info = "§7" + dragging.getName() + ": §fX=" + dragging.getHudX() + " §fY=" + dragging.getHudY();
            g.drawCenteredString(font, Component.literal(info), cx, height - M_H + 8, 0xFFFFFFFF);
        }

        super.render(g, mx, my, delta);
    }

    @Override
    public boolean mouseClicked(MouseButtonEvent event, boolean consumed) {
        double mx = event.x();
        double my = event.y();
        if (consumed) return true;

        for (int i = hudFeatures.size() - 1; i >= 0; i--) {
            var f = hudFeatures.get(i);
            HudBounds b = f.getHudBounds();
            if (b == null) continue;

            int hx = b.x() + b.width() - HANDLE + 2;
            int hy = b.y() + b.height() - HANDLE + 2;

            if (mx >= hx && mx < hx + HANDLE && my >= hy && my < hy + HANDLE) {
                resizing = f;
                resizeStartX = (int) mx;
                resizeStartY = (int) my;
                resizeStartScale = f.getHudScale();
                return true;
            }

            if (mx >= b.x() - 2 && mx < b.x() + b.width() + 2 &&
                my >= b.y() - 2 && my < b.y() + b.height() + 2) {
                dragging = f;
                dragOffX = (int) mx - f.getHudX();
                dragOffY = (int) my - f.getHudY();
                return true;
            }
        }
        return super.mouseClicked(event, consumed);
    }

    @Override
    public boolean mouseDragged(MouseButtonEvent event, double dx, double dy) {
        if (dragging != null) {
            int nx = (int) (event.x() - dragOffX);
            int ny = (int) (event.y() - dragOffY);
            dragging.setHudX(nx);
            dragging.setHudY(ny);
            return true;
        }
        if (resizing != null) {
            HudBounds b = resizing.getHudBounds();
            int totalDelta = (int) (event.x() - resizeStartX + event.y() - resizeStartY);
            float newScale = Math.clamp(resizeStartScale + totalDelta * 0.005f, 0.3f, 3.0f);
            resizing.setHudScale(newScale);
            return true;
        }
        return super.mouseDragged(event, dx, dy);
    }

    @Override
    public boolean mouseReleased(MouseButtonEvent event) {
        if (dragging != null || resizing != null) {
            StellaConfig.getInstance().save();
            dragging = null;
            resizing = null;
            return true;
        }
        return super.mouseReleased(event);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) {
            StellaConfig.getInstance().save();
            minecraft.setScreen(parent);
            return true;
        }
        return super.keyPressed(keyEvent);
    }

    @Override
    public boolean isPauseScreen() { return false; }
}
