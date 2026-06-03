package com.stella.client.mixin;

import com.stella.client.StellaClientMod;
import com.stella.client.StellaClient;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.Identifier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.ArrayList;
import java.util.List;

@Mixin(TitleScreen.class)
public class TitleScreenMixin {
    private static final Identifier ICONS = Identifier.fromNamespaceAndPath("stella", "textures/gui/icons.png");
    private static final int ICON_SIZE = 22;
    private static final int ICON_GAP = 8;
    private static final int CELL = 32;
    private static final int SHEET_W = 256;
    private static final int SHEET_H = 32;

    @Unique
    private final List<IconButton> stellaIconButtons = new ArrayList<>();

    @Inject(method = "init", at = @At("TAIL"))
    private void onInit(CallbackInfo ci) {
        var self = (TitleScreen) (Object) this;
        int cx = self.width / 2;
        int h = self.height;

        stellaIconButtons.clear();

        var renderables = ((ScreenAccessor) self).stella_getRenderables();

        // Primera pasada: identificar y reposicionar botones principales
        for (var r : renderables) {
            if (!(r instanceof AbstractWidget widget)) continue;

            String key = null;
            var contents = widget.getMessage().getContents();
            if (contents instanceof TranslatableContents translatable) {
                key = translatable.getKey();
            }

            if ("menu.singleplayer".equals(key)) {
                widget.setMessage(Component.literal("▶ PLAY"));
                widget.setX(cx - 100);
                widget.setY(h / 2 - 52); // subido 12px
                widget.setWidth(200);
                widget.setHeight(30);
                continue;
            }

            if ("menu.multiplayer".equals(key)) {
                widget.setMessage(Component.literal("Multiplayer"));
                widget.setX(cx - 100);
                widget.setY(h / 2 - 52 + 38);
                widget.setWidth(200);
                widget.setHeight(30);
                continue;
            }

            if ("menu.online".equals(key)) {
                widget.setMessage(Component.literal("Online"));
                widget.setX(cx - 100);
                widget.setY(h / 2 - 52 + 76);
                widget.setWidth(200);
                widget.setHeight(30);
                continue;
            }

            int iconIdx = -1;
            String label2 = null;
            if ("menu.options".equals(key)) { iconIdx = 0; label2 = "Options"; }
            else if ("menu.language".equals(key)) { iconIdx = 1; label2 = "Language"; }
            else if (key != null && key.contains("accessibility")) { iconIdx = 2; label2 = "Accessibility"; }
            else if ("menu.quit".equals(key)) { iconIdx = 4; label2 = "Quit"; }
            else if (widget.getWidth() <= 28 && widget.getHeight() <= 28) { iconIdx = 5; label2 = key != null ? key.replace("menu.", "") : ""; }
            
            if (iconIdx >= 0) {
                stellaIconButtons.add(new IconButton(widget, iconIdx, label2));
            } else {
                // Ocultar botones no reconocidos (mods, realm, etc.)
                widget.setWidth(0);
                widget.setHeight(0);
            }
        }

        int totalW = stellaIconButtons.size() * ICON_SIZE + Math.max(0, stellaIconButtons.size() - 1) * ICON_GAP;
        int iconStartX = cx - totalW / 2;
        int iconAreaStartY = h - 85;

        for (int i = 0; i < stellaIconButtons.size(); i++) {
            var ib = stellaIconButtons.get(i);
            ib.widget.setX(iconStartX + i * (ICON_SIZE + ICON_GAP));
            ib.widget.setY(iconAreaStartY);
            ib.widget.setWidth(ICON_SIZE);
            ib.widget.setHeight(ICON_SIZE);
        }
    }

    @Inject(method = "render", at = @At("HEAD"), cancellable = true)
    private void onRender(GuiGraphics g, int mx, int my, float delta, CallbackInfo ci) {
        var self = (TitleScreen) (Object) this;
        int w = self.width;
        int h = self.height;
        int cx = w / 2;

        g.fillGradient(0, 0, w, h, 0xFF0A0A0A, 0xFF1A0A2E);

        int logoY = h / 2 - 130;

        g.fill(cx - 150, logoY - 20, cx + 150, logoY + 80, 0x15A855F7);
        g.fill(cx - 80, logoY - 5, cx + 80, logoY + 60, 0x1DA855F7);

        long t = System.currentTimeMillis();
        for (int i = 0; i < 80; i++) {
            int sx = (int) (Math.sin(i * 7.3 + t * 0.0003) * w * 0.45 + w * 0.5);
            int sy = (int) (Math.cos(i * 11.7 + t * 0.0002) * h * 0.45 + h * 0.5);
            int a = 0x10 + (int) (Math.sin(i * 3.1 + t * 0.001) * 0x10);
            int alpha = Math.clamp(a, 4, 40);
            g.fill(sx, sy, sx + 2, sy + 2, (alpha << 24) | 0xA855F7);
        }

        g.drawCenteredString(Minecraft.getInstance().font, Component.literal("✶"),
                cx, logoY - 16, 0xFFE6F1FF);
        g.drawCenteredString(Minecraft.getInstance().font, Component.literal("§lSTELLA"),
                cx, logoY, 0xFFFFFFFF);
        g.drawCenteredString(Minecraft.getInstance().font, Component.literal("§7Client Mod"),
                cx, logoY + 18, 0xFF888899);
        g.fill(cx - 70, logoY + 32, cx + 70, logoY + 33, 0x40A855F7);

        for (var r : ((ScreenAccessor) self).stella_getRenderables()) {
            r.render(g, mx, my, delta);
        }

        int totalW = stellaIconButtons.size() * ICON_SIZE + Math.max(0, stellaIconButtons.size() - 1) * ICON_GAP;
        int iconStartX = cx - totalW / 2;
        int iconAreaStartY = h - 85;

        for (int i = 0; i < stellaIconButtons.size(); i++) {
            var ib = stellaIconButtons.get(i);
            int ix = iconStartX + i * (ICON_SIZE + ICON_GAP);
            int iy = iconAreaStartY;

            boolean hovered = mx >= ix && mx < ix + ICON_SIZE && my >= iy && my < iy + ICON_SIZE;

            if (hovered) {
                g.fill(ix - 2, iy - 2, ix + ICON_SIZE + 2, iy + ICON_SIZE + 2, 0x25A855F7);

                var font = Minecraft.getInstance().font;
                String label = ib.label;
                int lw = font.width(label);
                int lx = ix + ICON_SIZE / 2 - lw / 2;
                int ly = iy - 13;
                g.fill(lx - 3, ly - 2, lx + lw + 3, ly + 10, 0xCC0A0A0A);
                g.fill(lx - 3, ly - 2, lx + lw + 3, ly - 1, 0xFFA855F7);
                g.drawString(font, Component.literal(label), lx, ly, 0xFFFFFFFF);
            }

            g.blit(RenderPipelines.GUI_TEXTURED, ICONS, ix, iy,
                    ib.iconIdx * CELL + (CELL - ICON_SIZE) / 2f,
                    (CELL - ICON_SIZE) / 2f,
                    ICON_SIZE, ICON_SIZE, SHEET_W, SHEET_H);
        }

        var conn = StellaClient.getInstance().getConnection();
        boolean connected = conn.isConnected();
        g.drawCenteredString(Minecraft.getInstance().font,
                Component.literal("§7v" + StellaClientMod.MOD_VERSION + " · " +
                        (connected ? "§a●" : "§c○") + " " +
                        (connected ? "Connected" : "Disconnected")),
                cx, h - 18, 0xFFFFFFFF);

        ci.cancel();
    }

    @Unique
    private record IconButton(AbstractWidget widget, int iconIdx, String label) {}
}
