package com.stella.client.network;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.stella.client.StellaClientMod;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.WebSocket;
import java.util.ArrayDeque;
import java.util.Map;
import java.util.Queue;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

public class StellaConnection {
    private static final Logger LOGGER = LoggerFactory.getLogger("StellaConnection");
    private static final Gson GSON = new Gson();

    private final String serverUrl;
    private final Map<String, Consumer<JsonObject>> listeners = new ConcurrentHashMap<>();
    private final Queue<String> messageQueue = new ArrayDeque<>();
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final AtomicBoolean connecting = new AtomicBoolean(false);

    private WebSocket webSocket;
    private ScheduledExecutorService executor;
    private int reconnectAttempt = 0;

    public StellaConnection(String serverUrl) {
        this.serverUrl = serverUrl;
    }

    public void connect() {
        if (connected.get() || connecting.getAndSet(true)) return;

        var httpClient = HttpClient.newHttpClient();
        executor = Executors.newSingleThreadScheduledExecutor();

        LOGGER.info("Connecting to {}", serverUrl);

        httpClient.newWebSocketBuilder()
                .buildAsync(URI.create(serverUrl), new WebSocketListener())
                .thenAccept(ws -> {
                    this.webSocket = ws;
                    connected.set(true);
                    connecting.set(false);
                    reconnectAttempt = 0;
                    LOGGER.info("Connected to Stella server");
                    flushQueue();
                    startHeartbeat();
                })
                .exceptionally(error -> {
                    connecting.set(false);
                    LOGGER.error("Failed to connect: {}", error.getMessage());
                    scheduleReconnect();
                    return null;
                });
    }

    public void disconnect() {
        connected.set(false);
        connecting.set(false);
        if (webSocket != null) {
            webSocket.sendClose(1000, "Client shutting down");
            webSocket = null;
        }
        shutdownExecutor();
    }

    public void send(String message) {
        if (webSocket != null && connected.get()) {
            webSocket.sendText(message, true);
        } else {
            synchronized (messageQueue) {
                if (messageQueue.size() < 64) {
                    messageQueue.add(message);
                }
            }
        }
    }

    public void send(JsonObject message) {
        send(GSON.toJson(message));
    }

    public boolean isConnected() {
        return connected.get();
    }

    public void on(String type, Consumer<JsonObject> handler) {
        listeners.put(type, handler);
    }

    public void off(String type) {
        listeners.remove(type);
    }

    private void flushQueue() {
        synchronized (messageQueue) {
            String msg;
            while ((msg = messageQueue.poll()) != null) {
                webSocket.sendText(msg, true);
            }
        }
    }

    private void scheduleReconnect() {
        if (executor == null || executor.isShutdown()) return;
        reconnectAttempt++;
        int delay = Math.min(5 * reconnectAttempt, 60);
        LOGGER.info("Reconnecting in {}s (attempt {})", delay, reconnectAttempt);
        executor.schedule(this::connect, delay, TimeUnit.SECONDS);
    }

    private void startHeartbeat() {
        if (executor == null || executor.isShutdown()) return;
        executor.scheduleAtFixedRate(() -> {
            if (connected.get()) {
                var ping = new JsonObject();
                ping.addProperty("type", "ping");
                send(ping);
            }
        }, 30, 30, TimeUnit.SECONDS);
    }

    private void shutdownExecutor() {
        if (executor != null) {
            executor.shutdown();
            executor = null;
        }
    }

    private void handleMessage(String message) {
        try {
            var json = GSON.fromJson(message, JsonObject.class);
            if (json == null || !json.has("type")) return;

            String type = json.get("type").getAsString();
            LOGGER.debug("Handling message type: {}", type);

            switch (type) {
                case "ping" -> {
                    var pong = new JsonObject();
                    pong.addProperty("type", "pong");
                    send(pong);
                }
                case "announcement" -> {
                    String text = json.get("text").getAsString();
                    Minecraft.getInstance().execute(() -> {
                        var player = Minecraft.getInstance().player;
                        if (player != null) {
                            player.displayClientMessage(
                                    Component.literal("§d[Stella] §f" + text), false);
                        }
                    });
                }
                case "command" -> {
                    String command = json.get("command").getAsString();
                    Minecraft.getInstance().execute(() -> {
                        if (Minecraft.getInstance().player != null) {
                            Minecraft.getInstance().player.connection.sendCommand(command);
                        }
                    });
                }
                case "update_mods" -> {
                    LOGGER.info("Mod update signal received");
                    StellaClientMod.LOGGER.info("Mods should be refreshed");
                }
                default -> {
                    var handler = listeners.get(type);
                    if (handler != null) {
                        handler.accept(json);
                    }
                }
            }
        } catch (JsonParseException e) {
            LOGGER.warn("Invalid JSON from server: {}", e.getMessage());
        } catch (Exception e) {
            LOGGER.error("Error handling message: {}", e.getMessage());
        }
    }

    private class WebSocketListener implements WebSocket.Listener {
        @Override
        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
            handleMessage(data.toString());
            return WebSocket.Listener.super.onText(webSocket, data, last);
        }

        @Override
        public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
            LOGGER.info("Connection closed: {} {}", statusCode, reason);
            connected.set(false);
            scheduleReconnect();
            return WebSocket.Listener.super.onClose(webSocket, statusCode, reason);
        }

        @Override
        public void onError(WebSocket webSocket, Throwable error) {
            LOGGER.error("WebSocket error: {}", error.getMessage());
            connected.set(false);
            scheduleReconnect();
        }
    }
}
