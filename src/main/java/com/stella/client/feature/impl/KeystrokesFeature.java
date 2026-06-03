package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.client.gui.GuiGraphics;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;

public class KeystrokesFeature extends Feature {
    private static final int BASE_KEY = 22;
    private static final int GAP = 2;
    private static final int KEYS_W = BASE_KEY * 3 + GAP * 2;
    private static final int KEYS_H = BASE_KEY * 2 + GAP;
    private static final int MB_H = BASE_KEY + 8;

    private final Deque<Long> leftClicks = new ArrayDeque<>();
    private final Deque<Long> rightClicks = new ArrayDeque<>();
    private boolean prevAttack;
    private boolean prevUse;
    private float time;

    public KeystrokesFeature() {
        super("keystrokes", "Keystrokes", FeatureCategory.HUD);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(new SettingsOption.Slider("Scale", "keystrokes.scale", 50, 200, 5, "%"));
    }

    @Override
    public boolean isHudElement() { return true; }

    @Override
    public int getHudX() { return StellaConfig.getInstance().get("keystrokes.x", 10); }
    @Override
    public int getHudY() { return StellaConfig.getInstance().get("keystrokes.y", 10); }
    @Override
    public void setHudX(int x) { StellaConfig.getInstance().set("keystrokes.x", x); }
    @Override
    public void setHudY(int y) { StellaConfig.getInstance().set("keystrokes.y", y); }

    @Override
    public float getHudScale() {
        return StellaConfig.getInstance().get("keystrokes.scale", 100) / 100f;
    }
    @Override
    public void setHudScale(float s) {
        StellaConfig.getInstance().set("keystrokes.scale", Math.round(s * 100));
    }

    @Override
    public HudBounds getHudBounds() {
        float sc = getHudScale();
        int w = (int) (Math.max(KEYS_W, (KEYS_W / 2) + GAP) * sc);
        int h = (int) ((KEYS_H + 4 + MB_H) * sc);
        return new HudBounds(getHudX(), getHudY(), w, h);
    }

    @Override
    public void onTick() {
        time += 0.05f;
        long now = System.currentTimeMillis();
        while (!leftClicks.isEmpty() && leftClicks.peek() < now - 1000) leftClicks.poll();
        while (!rightClicks.isEmpty() && rightClicks.peek() < now - 1000) rightClicks.poll();

        boolean attack = mc.options.keyAttack.isDown();
        boolean use = mc.options.keyUse.isDown();

        if (attack && !prevAttack) leftClicks.add(now);
        if (use && !prevUse) rightClicks.add(now);

        prevAttack = attack;
        prevUse = use;
    }

    @Override
    public void onRender(GuiGraphics g, float delta) {
        float sc = getHudScale();
        int x = getHudX();
        int y = getHudY();
        int ks = (int) (BASE_KEY * sc);
        int gp = (int) (GAP * sc);

        int cx = x + ks + gp;
        drawSpaceKey(g, cx, y, ks, "W", mc.options.keyUp.isDown());
        drawSpaceKey(g, x, y + ks + gp, ks, "A", mc.options.keyLeft.isDown());
        drawSpaceKey(g, cx, y + ks + gp, ks, "S", mc.options.keyDown.isDown());
        drawSpaceKey(g, x + (ks + gp) * 2, y + ks + gp, ks, "D", mc.options.keyRight.isDown());

        int mbY = y + (int) ((KEYS_H + 4) * sc);
        int mbW = (int) ((KEYS_W - GAP) / 2 * sc);
        drawSpaceMouse(g, x, mbY, mbW, ks, "LMB", mc.options.keyAttack.isDown(), leftClicks.size());
        drawSpaceMouse(g, x + mbW + gp, mbY, mbW, ks, "RMB", mc.options.keyUse.isDown(), rightClicks.size());
    }

    private int glowColor(int color, float intensity) {
        int r = (color >> 16) & 0xFF;
        int g = (color >> 8) & 0xFF;
        int b = color & 0xFF;
        r = Math.min(255, (int) (r * intensity));
        g = Math.min(255, (int) (g * intensity));
        b = Math.min(255, (int) (b * intensity));
        return (r << 16) | (g << 8) | b;
    }

    private void drawSpaceKey(GuiGraphics g, int x, int y, int size, String label, boolean pressed) {
        int bg = pressed ? 0xCC0044AA : 0x500A0A2E;
        int border = pressed ? 0xFF00DDFF : 0x603366AA;
        int textColor = pressed ? 0xFF00DDFF : 0xFF5588BB;

        g.fill(x, y, x + size, y + size, bg);
        g.fill(x, y, x + size, y + 1, border);
        g.fill(x, y, x + 1, y + size, border);
        g.fill(x + size - 1, y, x + size, y + size, border);
        g.fill(x, y + size - 1, x + size, y + size, border);

        if (pressed) {
            for (int i = 1; i < 4; i++) {
                int glow = 0x0800DDFF;
                g.fill(x - i, y - i, x + size + i, y - i + 1, glow);
                g.fill(x - i, y + size + i - 1, x + size + i, y + size + i, glow);
                g.fill(x - i, y - i + 1, x - i + 1, y + size + i - 1, glow);
                g.fill(x + size + i - 1, y - i + 1, x + size + i, y + size + i - 1, glow);
            }
        }

        g.drawString(mc.font, label, x + (size - mc.font.width(label)) / 2, y + (size - 8) / 2, textColor);
    }

    private void drawSpaceMouse(GuiGraphics g, int x, int y, int w, int keySize, String label, boolean pressed, int cps) {
        int h = keySize + 8;
        int bg = pressed ? 0xCC0044AA : 0x500A0A2E;
        int border = pressed ? 0xFF00DDFF : 0x603366AA;
        int textColor = pressed ? 0xFF00DDFF : 0xFF5588BB;

        g.fill(x, y, x + w, y + h, bg);
        g.fill(x, y, x + w, y + 1, border);

        if (pressed) {
            for (int i = 1; i < 3; i++) {
                int glow = 0x0800DDFF;
                g.fill(x - i, y - i, x + w + i, y - i + 1, glow);
                g.fill(x - i, y + h + i - 1, x + w + i, y + h + i, glow);
                g.fill(x - i, y - i + 1, x - i + 1, y + h + i - 1, glow);
                g.fill(x + w + i - 1, y - i + 1, x + w + i, y + h + i - 1, glow);
            }
        }

        String cpsStr = cps + " CPS";
        g.drawString(mc.font, label, x + (w - mc.font.width(label)) / 2, y + 3, textColor);
        g.drawString(mc.font, "§7" + cpsStr, x + (w - mc.font.width(cpsStr)) / 2, y + keySize / 2 + 4, 0xFF888888);
    }
}
