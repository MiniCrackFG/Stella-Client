package com.stella.client.mixin;

import com.stella.client.feature.FeatureManager;
import com.stella.client.feature.impl.ZoomFeature;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.Camera;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(GameRenderer.class)
public class GameRendererMixin {
    @Inject(method = "getFov", at = @At("RETURN"), cancellable = true)
    private void onGetFov(Camera camera, float tickDelta, boolean useFOVSetting, CallbackInfoReturnable<Float> cir) {
        var zoom = FeatureManager.getInstance().getFeature("zoom");
        if (zoom != null && zoom.isEnabled()) {
            double mult = ((ZoomFeature) zoom).getFovMultiplier();
            if (mult < 1.0) {
                cir.setReturnValue((float) (cir.getReturnValue() * mult));
            }
        }
    }
}
