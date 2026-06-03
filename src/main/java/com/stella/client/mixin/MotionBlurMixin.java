package com.stella.client.mixin;

import com.stella.client.feature.FeatureManager;
import com.stella.client.feature.impl.MotionBlurFeature;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.renderer.GameRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(GameRenderer.class)
public class MotionBlurMixin {
    @Inject(
        method = "render",
        at = @At(
            value = "INVOKE",
            target = "Lnet/minecraft/client/renderer/GameRenderer;renderLevel(Lnet/minecraft/client/DeltaTracker;)V",
            shift = At.Shift.AFTER
        )
    )
    private void afterRenderLevel(DeltaTracker delta, boolean bl, CallbackInfo ci) {
        try {
            var feat = FeatureManager.getInstance().getFeature("motion_blur");
            if (feat instanceof MotionBlurFeature blur && blur.isEnabled()) {
                ((GameRendererInvoker)(Object)this).invokeProcessBlurEffect();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
