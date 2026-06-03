package com.stella.client.mixin;

import com.mojang.blaze3d.resource.GraphicsResourceAllocator;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.resources.Identifier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(GameRenderer.class)
public interface GameRendererAccessor {
    @Accessor("resourcePool")
    GraphicsResourceAllocator getResourcePool();

    @Accessor("postEffectId")
    void setPostEffectId(Identifier id);
}
