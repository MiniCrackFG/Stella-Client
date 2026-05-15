package com.stella.client.ui;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Items;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

public class StellaModsScreen extends Screen {
    private static final int PANEL_WIDTH = 380;
    private static final int PANEL_HEIGHT = 320;
    private static final int ENTRY_HEIGHT = 24;

    private final Screen parent;
    private int panelX, panelY;
    private int scrollOffset = 0;
    private List<ModEntry> mods = new ArrayList<>();

    private record ModEntry(String name, long size) {}

    public StellaModsScreen(Screen parent) {
        super(Component.literal("Installed Mods"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        panelX = (width - PANEL_WIDTH) / 2;
        panelY = (height - PANEL_HEIGHT) / 2;
        mods = scanMods();

        addRenderableWidget(new StellaScreen.ModernButton(
                width / 2 - 40, panelY + PANEL_HEIGHT - 32, 80, 24,
                Component.literal("Back"),
                () -> minecraft.setScreen(parent)));
    }

    private List<ModEntry> scanMods() {
        var list = new ArrayList<ModEntry>();
        var modsDir = new File(Minecraft.getInstance().gameDirectory, "mods");
        if (!modsDir.exists()) return list;
        var jars = modsDir.listFiles((dir, name) -> name.endsWith(".jar"));
        if (jars == null) return list;
        for (var f : jars) {
            list.add(new ModEntry(f.getName(), f.length()));
        }
        list.sort((a, b) -> a.name().compareToIgnoreCase(b.name()));
        return list;
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double scrollX, double scrollY) {
        int maxScroll = Math.max(0, mods.size() * ENTRY_HEIGHT - (PANEL_HEIGHT - 60));
        scrollOffset = Math.clamp(scrollOffset - (int)scrollY * ENTRY_HEIGHT, 0, maxScroll);
        return true;
    }

    @Override
    public void renderBackground(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(0, 0, width, height, 0x88000000);
    }

    @Override
    public void render(GuiGraphics guiGraphics, int mouseX, int mouseY, float delta) {
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + PANEL_HEIGHT, 0xC81A1A2E);
        guiGraphics.fill(panelX, panelY, panelX + PANEL_WIDTH, panelY + 1, 0xFF6B8CFF);
        guiGraphics.drawCenteredString(font, Component.literal("Mods (" + mods.size() + ")"),
                width / 2, panelY + 18, 0xFFFFFF);

        int y = panelY + 44;
        int x = panelX + 20;
        int visibleMax = panelY + PANEL_HEIGHT - 40;

        for (int i = 0; i < mods.size(); i++) {
            int drawY = y + i * ENTRY_HEIGHT - scrollOffset;
            if (drawY + ENTRY_HEIGHT < panelY + 40 || drawY > visibleMax) continue;

            var mod = mods.get(i);
            String sizeStr = mod.size() > 1024 * 1024
                    ? String.format("%.1f MB", mod.size() / (1024.0 * 1024.0))
                    : String.format("%.0f KB", mod.size() / 1024.0);

            if (drawY + ENTRY_HEIGHT <= visibleMax) {
                if (mouseY >= drawY && mouseY < drawY + ENTRY_HEIGHT && mouseX >= x && mouseX < x + PANEL_WIDTH - 60) {
                    guiGraphics.fill(x, drawY, x + PANEL_WIDTH - 60, drawY + ENTRY_HEIGHT, 0x30FFFFFF);
                }
            }
            guiGraphics.drawString(font, Component.literal(mod.name()),
                    x + 4, drawY + 6, 0xCCCCCC);
            guiGraphics.drawString(font, Component.literal(sizeStr),
                    x + PANEL_WIDTH - 100, drawY + 6, 0x666666);
        }

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
