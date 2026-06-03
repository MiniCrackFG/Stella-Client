package com.stella.client.mixin;

import com.stella.client.feature.FeatureManager;
import com.stella.client.config.StellaConfig;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Level.class)
public class WeatherChangerMixin {
    @Inject(method = "getRainLevel", at = @At("HEAD"), cancellable = true)
    private void onGetRainLevel(float delta, CallbackInfoReturnable<Float> cir) {
        try {
            var weather = FeatureManager.getInstance().getFeature("weather_changer");
            if (weather == null || !weather.isEnabled()) return;
            String mode = StellaConfig.getInstance().get("weather_changer.mode", "Clear");
            cir.setReturnValue("Rain".equals(mode) || "Thunder".equals(mode) ? 1.0f : 0.0f);
        } catch (Exception ignored) {}
    }

    @Inject(method = "getThunderLevel", at = @At("HEAD"), cancellable = true)
    private void onGetThunderLevel(float delta, CallbackInfoReturnable<Float> cir) {
        try {
            var weather = FeatureManager.getInstance().getFeature("weather_changer");
            if (weather == null || !weather.isEnabled()) return;
            String mode = StellaConfig.getInstance().get("weather_changer.mode", "Clear");
            cir.setReturnValue("Thunder".equals(mode) ? 1.0f : 0.0f);
        } catch (Exception ignored) {}
    }
}
