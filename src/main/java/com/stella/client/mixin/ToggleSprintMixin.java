package com.stella.client.mixin;

import com.stella.client.feature.FeatureManager;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.KeyboardInput;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(KeyboardInput.class)
public class ToggleSprintMixin {
    private static boolean sprintToggled;

    @Inject(method = "tick", at = @At("TAIL"))
    private void onTick(boolean slowDown, float f, CallbackInfo ci) {
        try {
            var toggleSprint = FeatureManager.getInstance().getFeature("toggle_sprint");
            if (toggleSprint == null || !toggleSprint.isEnabled()) return;

            var mc = Minecraft.getInstance();
            if (mc.player == null) return;

            if (mc.options.keySprint.isDown()) {
                sprintToggled = !sprintToggled;
            }

            if (sprintToggled) {
                mc.player.setSprinting(true);
            }
        } catch (Exception ignored) {}
    }
}
