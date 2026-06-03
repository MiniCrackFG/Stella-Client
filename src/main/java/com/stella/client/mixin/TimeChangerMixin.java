package com.stella.client.mixin;

import com.stella.client.feature.FeatureManager;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Level.class)
public class TimeChangerMixin {
    @Inject(method = "getDayTime", at = @At("HEAD"), cancellable = true)
    private void onGetDayTime(CallbackInfoReturnable<Long> cir) {
        try {
            var mgr = FeatureManager.getInstance();
            var time = mgr.getFeature("time_changer");
            if (time != null && time.isEnabled()) {
                cir.setReturnValue(((com.stella.client.feature.impl.TimeChangerFeature)time).getOverrideTime());
            }
        } catch (Exception ignored) {}
    }
}
