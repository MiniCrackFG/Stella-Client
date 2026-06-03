package com.stella.client.mixin;

import com.stella.client.feature.FeatureManager;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.KeyboardInput;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(KeyboardInput.class)
public class ToggleSneakMixin {
    private static boolean sneakToggled;
    private static boolean wasShiftDown;

    @Inject(method = "tick", at = @At("TAIL"))
    private void onTick(boolean slowDown, float f, CallbackInfo ci) {
        try {
            var toggleSneak = FeatureManager.getInstance().getFeature("toggle_sneak");
            if (toggleSneak == null || !toggleSneak.isEnabled()) return;

            var mc = Minecraft.getInstance();
            if (mc.player == null) return;

            boolean shiftDown = mc.options.keyShift.isDown();
            if (shiftDown && !wasShiftDown) {
                sneakToggled = !sneakToggled;
            }
            wasShiftDown = shiftDown;

            mc.player.setShiftKeyDown(sneakToggled || shiftDown);
        } catch (Exception ignored) {}
    }
}
