package com.stella.client.network;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class StellaConnection {
    private static final Logger LOGGER = LoggerFactory.getLogger("StellaConnection");

    private final String serverUrl;
    private WebSocket webSocket;
    private HttpClient httpClient;
    private ScheduledExecutorService executor;
    private boolean connected = false;

    public StellaConnection(String serverUrl) {
        this.serverUrl = serverUrl;
    }

    public void connect() {
        if (connected) return;

        httpClient = HttpClient.newHttpClient();
        executor = Executors.newSingleThreadScheduledExecutor();

        LOGGER.info("Connecting to {}", serverUrl);

        httpClient.newWebSocketBuilder()
                .buildAsync(URI.create(serverUrl), new WebSocketListener())
                .thenAccept(ws -> {
                    this.webSocket = ws;
                    this.connected = true;
                    LOGGER.info("Connected to Stella server");
                    startHeartbeat();
                })
                .exceptionally(error -> {
                    LOGGER.error("Failed to connect: {}", error.getMessage());
                    scheduleReconnect();
                    return null;
                });
    }

    public void disconnect() {
        connected = false;
        if (webSocket != null) {
            webSocket.sendClose(1000, "Client shutting down");
            webSocket = null;
        }
        if (executor != null) {
            executor.shutdown();
            executor = null;
        }
    }

    public void send(String message) {
        if (webSocket != null && connected) {
            webSocket.sendText(message, true);
        }
    }

    public boolean isConnected() {
        return connected;
    }

    private void scheduleReconnect() {
        if (executor != null && !executor.isShutdown()) {
            executor.schedule(this::connect, 5, TimeUnit.SECONDS);
        }
    }

    private void startHeartbeat() {
        if (executor != null && !executor.isShutdown()) {
            executor.scheduleAtFixedRate(() -> {
                if (connected) {
                    send("{\"type\":\"ping\"}");
                }
            }, 30, 30, TimeUnit.SECONDS);
        }
    }

    private class WebSocketListener implements WebSocket.Listener {
        @Override
        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
            var message = data.toString();
            LOGGER.debug("Received: {}", message);
            handleMessage(message);
            return WebSocket.Listener.super.onText(webSocket, data, last);
        }

        @Override
        public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
            LOGGER.info("Connection closed: {} {}", statusCode, reason);
            connected = false;
            scheduleReconnect();
            return WebSocket.Listener.super.onClose(webSocket, statusCode, reason);
        }

        @Override
        public void onError(WebSocket webSocket, Throwable error) {
            LOGGER.error("WebSocket error: {}", error.getMessage());
            connected = false;
            scheduleReconnect();
        }
    }

    private void handleMessage(String message) {
        // TODO: Implement message handling
    }
}
