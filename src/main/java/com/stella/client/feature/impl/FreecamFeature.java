package com.stella.client.feature.impl;

import com.stella.client.config.StellaConfig;
import com.stella.client.feature.Feature;
import com.stella.client.feature.FeatureCategory;
import com.stella.client.feature.SettingsOption;
import net.minecraft.client.CameraType;

import java.util.List;

public class FreecamFeature extends Feature {
    private double x, y, z;
    private float yaw, pitch;
    private boolean prevFlying, prevMayfly, prevNoClip;
    private float prevFlySpeed;

    public FreecamFeature() {
        super("freecam", "Freecam", FeatureCategory.GAMEPLAY);
    }

    @Override
    public List<SettingsOption> getSettings() {
        return List.of(
            new SettingsOption.Slider("Speed", "freecam.speed", 1, 20, 1, ""),
            new SettingsOption.Toggle("Hands", "freecam.hands")
        );
    }

    @Override
    public void onEnable() {
        if (mc.player == null) return;

        x = mc.player.getX();
        y = mc.player.getY();
        z = mc.player.getZ();
        yaw = mc.player.getYRot();
        pitch = mc.player.getXRot();

        prevFlying = mc.player.getAbilities().flying;
        prevMayfly = mc.player.getAbilities().mayfly;
        prevNoClip = mc.player.noPhysics;
        prevFlySpeed = mc.player.getAbilities().getFlyingSpeed();
    }

    @Override
    public void onDisable() {
        if (mc.player == null) return;

        mc.player.getAbilities().flying = prevFlying;
        mc.player.getAbilities().mayfly = prevMayfly;
        mc.player.noPhysics = prevNoClip;
        mc.player.getAbilities().setFlyingSpeed(prevFlySpeed);

        mc.player.setPos(x, y, z);
        mc.player.setYRot(yaw);
        mc.player.setXRot(pitch);
    }

    @Override
    public void onTick() {
        if (mc.player == null) return;

        mc.player.getAbilities().flying = true;
        mc.player.getAbilities().mayfly = true;
        mc.player.noPhysics = true;
        mc.player.getAbilities().setFlyingSpeed(0.05f);

        float speed = StellaConfig.getInstance().get("freecam.speed", 10) / 10f;
        double velX = 0, velY = 0, velZ = 0;

        yaw = mc.player.getYRot();
        pitch = mc.player.getXRot();

        var forward = net.minecraft.world.phys.Vec3.directionFromRotation(0, yaw);
        var right = net.minecraft.world.phys.Vec3.directionFromRotation(0, yaw + 90);

        if (mc.options.keyUp.isDown()) { velX += forward.x * speed; velZ += forward.z * speed; }
        if (mc.options.keyDown.isDown()) { velX -= forward.x * speed; velZ -= forward.z * speed; }
        if (mc.options.keyLeft.isDown()) { velX -= right.x * speed; velZ -= right.z * speed; }
        if (mc.options.keyRight.isDown()) { velX += right.x * speed; velZ += right.z * speed; }

        if ((mc.options.keyUp.isDown() || mc.options.keyDown.isDown()) &&
            (mc.options.keyLeft.isDown() || mc.options.keyRight.isDown())) {
            velX *= 0.7071;
            velZ *= 0.7071;
        }

        if (mc.options.keyJump.isDown()) velY += speed;
        if (mc.options.keyShift.isDown()) velY -= speed;

        x += velX;
        y += velY;
        z += velZ;

        mc.player.setPos(x, y, z);
        mc.player.setYRot(yaw);
        mc.player.setXRot(pitch);
    }

    public double getX() { return x; }
    public double getY() { return y; }
    public double getZ() { return z; }
    public float getYaw() { return yaw; }
    public float getPitch() { return pitch; }
}
