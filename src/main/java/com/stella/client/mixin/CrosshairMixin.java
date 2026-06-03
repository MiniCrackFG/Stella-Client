package com.stella.client.mixin;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.FeatureManager;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.GuiGraphics;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Gui.class)
public class CrosshairMixin {
    @Inject(method = "renderCrosshair", at = @At("HEAD"), cancellable = true)
    private void onRenderCrosshair(GuiGraphics g, DeltaTracker delta, CallbackInfo ci) {
        try {
            var crosshair = FeatureManager.getInstance().getFeature("custom_crosshair");
            if (crosshair == null || !crosshair.isEnabled()) return;

            var mc = Minecraft.getInstance();
            int w = mc.getWindow().getGuiScaledWidth();
            int h = mc.getWindow().getGuiScaledHeight();
            int cx = w / 2;
            int cy = h / 2;

            int size = StellaConfig.getInstance().get("crosshair.size", 8);
            int thickness = StellaConfig.getInstance().get("crosshair.thickness", 2);
            int gap = StellaConfig.getInstance().get("crosshair.gap", 2);
            boolean dot = StellaConfig.getInstance().get("crosshair.dot", false);

            int color = 0xFFFFFFFF;
            g.fill(cx - thickness / 2, cy - gap - size, cx + thickness / 2 + 1, cy - gap, color);
            g.fill(cx - thickness / 2, cy + gap, cx + thickness / 2 + 1, cy + gap + size, color);
            g.fill(cx - gap - size, cy - thickness / 2, cx - gap, cy + thickness / 2 + 1, color);
            g.fill(cx + gap, cy - thickness / 2, cx + gap + size, cy + thickness / 2 + 1, color);

            if (dot) g.fill(cx - 1, cy - 1, cx + 2, cy + 2, color);

            ci.cancel();
        } catch (Exception ignored) {}
    }
}
