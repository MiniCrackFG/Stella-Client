package com.stella.client.mixin;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.AbstractButton;
import net.minecraft.client.gui.components.SpriteIconButton;
import net.minecraft.client.gui.screens.TitleScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(AbstractButton.class)
public class AbstractButtonMixin {
    @Inject(method = "renderWidget", at = @At("HEAD"), cancellable = true)
    private void onRenderWidget(GuiGraphics g, int mx, int my, float delta, CallbackInfo ci) {
        if (((Object) this) instanceof SpriteIconButton) return;

        AbstractButton btn = (AbstractButton) (Object) this;
        boolean titleScreen = Minecraft.getInstance().screen instanceof TitleScreen;

        if (titleScreen) {
            boolean small = btn.getWidth() <= 28 && btn.getHeight() <= 28;
            if (small) {
                ci.cancel();
                return;
            }
            int x = btn.getX(), y = btn.getY(), w = btn.getWidth(), h = btn.getHeight();
            boolean hover = btn.isHoveredOrFocused();

            int bg = hover ? 0xCC2A1A4E : 0x801A1A2E;
            int tc = hover ? 0xFFFFFFFF : 0xFFE0E0E0;
            int line = hover ? 0xFFA855F7 : 0x60A855F7;
            int glow = hover ? 0x15A855F7 : 0;

            g.fill(x, y, x + w, y + h, bg);
            g.fill(x, y, x + w, y + 2, line);
            g.fill(x, y + h - 1, x + w, y + h, 0x33000000);
            if (glow != 0) {
                g.fill(x, y, x + w, y + h, glow);
            }

            g.drawCenteredString(Minecraft.getInstance().font, btn.getMessage(),
                    x + w / 2, y + (h - 8) / 2, tc);

            ci.cancel();
            return;
        }

        int x = btn.getX(), y = btn.getY(), w = btn.getWidth(), h = btn.getHeight();
        boolean hover = btn.isHoveredOrFocused();

        int bg = hover ? 0xCC3A3A7A : 0x802A2A5A;
        int tc = hover ? 0xFFFFFFFF : 0xFFCCCCCC;
        int line = 0xFF6B8CFF;
        int glow = hover ? 0x106B8CFF : 0;

        g.fill(x, y, x + w, y + h, bg);
        g.fill(x, y, x + w, y + 1, line);
        g.fill(x, y + h - 1, x + w, y + h, 0x33000000);
        if (glow != 0) {
            g.fill(x, y, x + w, y + h, glow);
        }

        g.drawCenteredString(Minecraft.getInstance().font, btn.getMessage(),
                x + w / 2, y + (h - 8) / 2, tc);

        ci.cancel();
    }
}
