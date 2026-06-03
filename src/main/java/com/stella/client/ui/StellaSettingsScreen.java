package com.stella.client.ui;

import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.FeatureManager;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.AbstractButton;
import net.minecraft.client.gui.narration.NarrationElementOutput;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.InputWithModifiers;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.network.chat.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

public class StellaSettingsScreen extends Screen {
    private static final Logger LOGGER = LoggerFactory.getLogger("StellaSettings");
    private static final int SIDEBAR_W = 120;
    private static final int PANEL_W = 360;
    private static final int PANEL_H = 360;

    private final Screen parent;
    private int gx, gy;
    private FeatureCategory selected = FeatureCategory.HUD;
    private List<Feature> features;
    private int scrollY;

    public StellaSettingsScreen(Screen parent) {
        super(Component.literal("Stella Features"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        int tw = SIDEBAR_W + PANEL_W;
        gx = (width - tw) / 2;
        gy = (height - PANEL_H) / 2;

        var cats = FeatureCategory.values();
        int sy = gy + 40;
        for (int i = 0; i < cats.length; i++) {
            addRenderableWidget(new SidebarEntry(gx + 6, sy + i * 38, SIDEBAR_W - 12, 32, cats[i]));
        }

        addRenderableWidget(new StellaScreen.StellaButton(
                gx + SIDEBAR_W + PANEL_W - 90, gy + PANEL_H - 32, 80, 26,
                "Back",
                () -> minecraft.setScreen(parent)));

        addRenderableWidget(new StellaScreen.StellaButton(
                gx + SIDEBAR_W + 12, gy + PANEL_H - 32, 120, 26,
                "✎ HUD Editor",
                () -> minecraft.setScreen(new HudEditorScreen(this))));

        updateFeatures();
    }

    private void updateFeatures() {
        features = FeatureManager.getInstance().getFeaturesByCategory(selected);
    }

    @Override
    public void renderBackground(GuiGraphics g, int mx, int my, float delta) {
        g.fill(0, 0, width, height, 0xAA0A0A1A);
    }

    @Override
    public void render(GuiGraphics g, int mx, int my, float delta) {
        int pr = gx + SIDEBAR_W + PANEL_W;
        int pb = gy + PANEL_H;

        g.fill(gx, gy, pr, pb, 0xE0101028);
        g.fill(gx, gy, pr, gy + 2, 0xFF6B8CFF);

        int se = gx + SIDEBAR_W;
        g.fill(se, gy + 2, se + 1, pb, 0x301A1A3E);

        g.drawCenteredString(font, Component.literal("§l" + selected.getDisplayName()),
                gx + SIDEBAR_W + PANEL_W / 2, gy + 16, 0xFFFFFFFF);

        if (features != null) {
            int y = gy + 36 - scrollY;
            int x = gx + SIDEBAR_W + 12;
            int w = PANEL_W - 24;
            int clipMax = pb - 10;

            beginScissor(g, gx + SIDEBAR_W + 4, gy + 36, pr - 4, clipMax);

            for (var f : features) {
                if (y + 24 < gy + 36 || y > clipMax) {
                    y += 28;
                    var s = f.getSettings();
                    if (s != null && !s.isEmpty()) {
                        y += 6;
                        for (var o : s) y += o.getHeight() + 2;
                        y += 4;
                    }
                    continue;
                }

                boolean hover = mx >= x && mx < x + w && my >= y && my < y + 24;
                boolean en = f.isEnabled();

                if (hover) g.fill(x, y, x + w, y + 24, 0x20FFFFFF);
                g.drawString(font, Component.literal(f.getName()), x + 6, y + 8, en ? 0xFFFFFFFF : 0xFF888888);

                int tx = x + w - 36, ty = y + 5, tw = 30, th = 14;
                int bg = en ? 0xFF6B8CFF : 0xFF333355;
                g.fill(tx, ty, tx + tw, ty + th, bg);
                g.fill(tx + 1, ty + 1, tx + tw - 1, ty + th - 1, en ? 0xFF8AA9FF : 0xFF444466);
                int knob = en ? tx + tw - 11 : tx + 1;
                g.fill(knob, ty + 2, knob + 9, ty + th - 2, 0xFFFFFFFF);

                y += 28;

                var settings = f.getSettings();
                if (settings != null && !settings.isEmpty()) {
                    y += 2;
                    g.fill(x, y, x + w, y + 1, 0x20FFFFFF);
                    y += 4;
                    for (var o : settings) {
                        o.render(g, x, y, w, mx, my, delta);
                        y += o.getHeight() + 2;
                    }
                    y += 4;
                }
            }

            endScissor(g);
        }

        super.render(g, mx, my, delta);
    }

    private void beginScissor(GuiGraphics g, int x, int y, int w, int h) {
        g.enableScissor(x, y, w, h);
    }

    private void endScissor(GuiGraphics g) {
        g.disableScissor();
    }

    @Override
    public boolean mouseScrolled(double mx, double my, double sx, double sy) {
        if (features == null) return false;
        int contentH = 0;
        for (var f : features) {
            contentH += 28;
            var s = f.getSettings();
            if (s != null && !s.isEmpty()) {
                contentH += 6;
                for (var o : s) contentH += o.getHeight() + 2;
                contentH += 4;
            }
        }
        int maxScroll = Math.max(0, contentH - (PANEL_H - 50));
        scrollY = (int) Math.clamp(scrollY - sy * 20, 0, maxScroll);
        return true;
    }

    @Override
    public boolean mouseClicked(MouseButtonEvent event, boolean consumed) {
        double mx = event.x();
        double my = event.y();
        if (features != null) {
            int y = gy + 36 - scrollY;
            int x = gx + SIDEBAR_W + 12;
            int w = PANEL_W - 24;

            for (var f : features) {
                if (mx >= x && mx < x + w && my >= y && my < y + 24) {
                    f.toggle();
                    return true;
                }
                y += 28;

                var settings = f.getSettings();
                if (settings != null && !settings.isEmpty()) {
                    y += 2 + 4;
                    for (var o : settings) {
                        if (o.mouseClicked(mx, my, x, y, w)) return true;
                        y += o.getHeight() + 2;
                    }
                    y += 4;
                }
            }
        }
        return super.mouseClicked(event, consumed);
    }

    @Override
    public boolean keyPressed(KeyEvent keyEvent) {
        if (keyEvent.key() == 256) { minecraft.setScreen(parent); return true; }
        return super.keyPressed(keyEvent);
    }

    @Override
    public boolean isPauseScreen() { return false; }

    private class SidebarEntry extends AbstractButton {
        private final FeatureCategory cat;
        private float hoverT;

        public SidebarEntry(int x, int y, int w, int h, FeatureCategory cat) {
            super(x, y, w, h, Component.literal(cat.getDisplayName()));
            this.cat = cat;
        }

        @Override
        public void onPress(InputWithModifiers input) {
            selected = cat;
            scrollY = 0;
            updateFeatures();
        }

        @Override
        protected void renderContents(GuiGraphics g, int mx, int my, float delta) {
            boolean sel = cat == selected;
            boolean hover = isHoveredOrFocused();
            hoverT += (hover ? 1 : -1) * delta * 6;
            hoverT = Math.clamp(hoverT, 0, 1);

            int bg = sel ? 0xFF2A2A5A : ((int) (0x30 * hoverT) << 24);
            if (sel || hoverT > 0.01f) {
                g.fill(getX(), getY(), getX() + getWidth(), getY() + getHeight(), bg);
            }
            if (sel) {
                g.fill(getX(), getY(), getX() + 3, getY() + getHeight(), 0xFF6B8CFF);
            }

            int gray = 0xAA + (int) (0x55 * hoverT);
            int color = sel ? 0xFFFFFFFF : (gray << 24) | 0xAAAAAA;
            g.drawString(font, getMessage(), getX() + 10, getY() + (getHeight() - 8) / 2, color);
        }

        @Override
        protected void updateWidgetNarration(NarrationElementOutput out) {}
    }
}
