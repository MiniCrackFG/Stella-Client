package com.stella.client;

import com.stella.client.ui.StellaMenuHandler;
import net.fabricmc.api.ClientModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class StellaClientMod implements ClientModInitializer {
    public static final String MOD_ID = "stella-client";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitializeClient() {
        LOGGER.info("Stella Client initializing...");
        StellaClient.getInstance().init();
        StellaMenuHandler.register();
        LOGGER.info("Stella Client initialized!");
    }
}
