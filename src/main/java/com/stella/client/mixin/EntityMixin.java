package com.stella.client.mixin;

import com.stella.client.feature.impl.FreeLookFeature;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Entity.class)
public class EntityMixin {
    @Inject(method = "turn", at = @At("HEAD"), cancellable = true)
    private void onTurn(double yawDelta, double pitchDelta, CallbackInfo ci) {
        FreeLookFeature fl = FreeLookFeature.getInstance();
        if (fl != null && fl.isActive()) {
            fl.addRotationDelta(yawDelta, pitchDelta);
            ci.cancel();
        }
    }
}
