package com.stella.client.feature;

import com.stella.client.config.StellaConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;

public abstract class SettingsOption {
    protected final String label;
    protected final String configKey;
    protected final Minecraft mc;

    public SettingsOption(String label, String configKey) {
        this.label = label;
        this.configKey = configKey;
        this.mc = Minecraft.getInstance();
    }

    public abstract void render(GuiGraphics g, int x, int y, int w, int mouseX, int mouseY, float delta);
    public abstract boolean mouseClicked(double mx, double my, int x, int y, int w);
    public abstract int getHeight();

    public static class Select extends SettingsOption {
        private final String[] values;

        public Select(String label, String configKey, String[] values) {
            super(label, configKey);
            this.values = values;
        }

        @Override
        public int getHeight() { return 22; }

        @Override
        public void render(GuiGraphics g, int x, int y, int w, int mouseX, int mouseY, float delta) {
            String current = StellaConfig.getInstance().get(configKey, values[0]);
            g.drawString(mc.font, label + ":", x + 4, y + 7, 0xFFAAAAAA);

            int bx = x + w - 110;
            int bw = 106;
            int by = y + 2;
            int bh = getHeight() - 4;

            g.fill(bx, by, bx + bw, by + bh, 0x90000000);
            g.fill(bx, by, bx + bw, by + 1, 0x406B8CFF);
            g.fill(bx, by, bx + 1, by + bh, 0x406B8CFF);

            String display = current.replace("_", " ");
            display = display.substring(0, 1).toUpperCase() + display.substring(1).toLowerCase();
            g.drawCenteredString(mc.font, display, bx + bw / 2, by + (bh - 8) / 2, 0xFFCCCCCC);
        }

        @Override
        public boolean mouseClicked(double mx, double my, int x, int y, int w) {
            int bx = x + w - 110;
            int bw = 106;
            int by = y + 2;
            int bh = getHeight() - 4;
            if (mx >= bx && mx < bx + bw && my >= by && my < by + bh) {
                String current = StellaConfig.getInstance().get(configKey, values[0]);
                int idx = -1;
                for (int i = 0; i < values.length; i++) {
                    if (values[i].equals(current)) { idx = i; break; }
                }
                String next = values[(idx + 1) % values.length];
                StellaConfig.getInstance().set(configKey, next);
                StellaConfig.getInstance().save();
                return true;
            }
            return false;
        }
    }

    public static class Slider extends SettingsOption {
        private final float min, max, step;
        private final String suffix;

        public Slider(String label, String configKey, float min, float max, float step, String suffix) {
            super(label, configKey);
            this.min = min; this.max = max; this.step = step;
            this.suffix = suffix;
        }

        @Override
        public int getHeight() { return 22; }

        @Override
        public void render(GuiGraphics g, int x, int y, int w, int mouseX, int mouseY, float delta) {
            float current = StellaConfig.getInstance().get(configKey, min);
            g.drawString(mc.font, label + ":", x + 4, y + 7, 0xFFAAAAAA);

            int sx = x + w - 150;
            int sw = 146;
            int sy = y + 4;
            int sh = getHeight() - 8;

            float pct = (current - min) / (max - min);
            int fillEnd = (int) (sx + sw * pct);

            g.fill(sx, sy, sx + sw, sy + sh, 0x90000000);
            g.fill(sx, sy, fillEnd, sy + sh, 0x906B8CFF);

            String text = String.format("%.0f%s", current, suffix);
            g.drawCenteredString(mc.font, text, sx + sw / 2, sy + (sh - 8) / 2, 0xFFFFFFFF);
        }

        @Override
        public boolean mouseClicked(double mx, double my, int x, int y, int w) {
            int sx = x + w - 150;
            int sw = 146;
            int sy = y + 4;
            int sh = getHeight() - 8;

            if (mx >= sx && mx < sx + sw && my >= sy && my < sy + sh) {
                float pct = (float) ((mx - sx) / sw);
                float val = min + pct * (max - min);
                val = Math.round(val / step) * step;
                val = Math.min(max, Math.max(min, val));
                StellaConfig.getInstance().set(configKey, val);
                StellaConfig.getInstance().save();
                return true;
            }
            return false;
        }
    }

    public static class Toggle extends SettingsOption {
        public Toggle(String label, String configKey) {
            super(label, configKey);
        }

        @Override
        public int getHeight() { return 18; }

        @Override
        public void render(GuiGraphics g, int x, int y, int w, int mouseX, int mouseY, float delta) {
            boolean enabled = StellaConfig.getInstance().get(configKey, false);
            g.drawString(mc.font, label, x + 4, y + 5, 0xFFAAAAAA);

            int tx = x + w - 50;
            int tw = 46;
            int ty = y + 2;
            int th = getHeight() - 4;

            int bg = enabled ? 0xFF4CAF50 : 0xFF444444;
            g.fill(tx, ty, tx + tw, ty + th, bg);
            g.fill(tx + 1, ty + 1, tx + tw - 1, ty + th - 1, enabled ? 0xFF66BB6A : 0xFF555555);

            int knobX = enabled ? tx + tw - 13 : tx + 3;
            g.fill(knobX, ty + 3, knobX + 9, ty + th - 3, 0xFFFFFFFF);
        }

        @Override
        public boolean mouseClicked(double mx, double my, int x, int y, int w) {
            int tx = x + w - 50;
            int tw = 46;
            int ty = y + 2;
            int th = getHeight() - 4;
            if (mx >= tx && mx < tx + tw && my >= ty && my < ty + th) {
                boolean current = StellaConfig.getInstance().get(configKey, false);
                StellaConfig.getInstance().set(configKey, !current);
                StellaConfig.getInstance().save();
                return true;
            }
            return false;
        }
    }
}
