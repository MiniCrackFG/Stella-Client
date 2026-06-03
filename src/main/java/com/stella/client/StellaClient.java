package com.stella.client;

import com.stella.client.feature.FeatureManager;
import com.stella.client.network.StellaConnection;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class StellaClient {
    private static final Logger LOGGER = LoggerFactory.getLogger("StellaClient");
    private static final StellaClient INSTANCE = new StellaClient();

    private StellaConnection connection;
    private boolean initialized = false;

    public static StellaClient getInstance() {
        return INSTANCE;
    }

    public void init() {
        if (initialized) return;
        initialized = true;

        LOGGER.info("Initializing Stella Client instance");

        connection = new StellaConnection("ws://localhost:17523");
        FeatureManager.getInstance().init();

        ClientLifecycleEvents.CLIENT_STOPPING.register(client -> {
            LOGGER.info("Shutting down Stella Client");
            connection.disconnect();
        });
    }

    public StellaConnection getConnection() {
        return connection;
    }

    public boolean isInitialized() {
        return initialized;
    }
}
