package com.stella.client.mixin;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Screen.class)
public class ScreenMixin {
    @Inject(method = "renderBackground", at = @At("TAIL"))
    private void onRenderBackground(GuiGraphics g, int mx, int my, float delta, CallbackInfo ci) {
        Screen self = (Screen) (Object) this;
        g.fill(0, 0, self.width, self.height, 0x220A0A2E);
    }
}
