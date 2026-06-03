package com.stella.client.mixin;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.FeatureManager;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public class FastPlaceMixin {
    @Shadow private int rightClickDelay;

    @Inject(method = "startUseItem", at = @At("TAIL"))
    private void afterStartUseItem(CallbackInfo ci) {
        try {
            var fastPlace = FeatureManager.getInstance().getFeature("fast_place");
            if (fastPlace != null && fastPlace.isEnabled()) {
                int delay = StellaConfig.getInstance().get("fast_place.delay", 0);
                rightClickDelay = Math.max(0, delay);
            }
        } catch (Exception ignored) {}
    }
}
