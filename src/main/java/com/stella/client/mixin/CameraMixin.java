package com.stella.client.mixin;

import com.stella.client.feature.impl.FreeLookFeature;
import net.minecraft.client.Camera;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Camera.class)
public class CameraMixin {
    @Shadow private float yRot;
    @Shadow private float xRot;

    @Inject(method = "setup", at = @At("TAIL"))
    private void onSetupTail(CallbackInfo ci) {
        FreeLookFeature fl = FreeLookFeature.getInstance();
        if (fl != null && fl.isActive()) {
            yRot = fl.getCameraYaw();
            xRot = fl.getCameraPitch();
        }
    }
}
