package com.stella.client.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import com.stella.client.StellaClientMod;
import net.minecraft.client.Minecraft;

import java.io.FileReader;
import java.io.FileWriter;
import java.lang.reflect.Type;
import java.util.HashMap;
import java.util.Map;

public class StellaConfig {
    private static final Type TYPE = new TypeToken<Map<String, Object>>() {}.getType();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static StellaConfig instance;

    private final java.nio.file.Path path;
    private final Map<String, Object> data = new HashMap<>();

    public StellaConfig(java.nio.file.Path path) {
        this.path = path;
    }

    public static StellaConfig getInstance() {
        if (instance == null) {
            instance = new StellaConfig(Minecraft.getInstance().gameDirectory.toPath().resolve("config/stella-client.json"));
            instance.load();
        }
        return instance;
    }

    @SuppressWarnings("unchecked")
    public <T> T get(String key, T defaultValue) {
        Object val = data.get(key);
        if (val == null) return defaultValue;
        if (defaultValue instanceof Integer && val instanceof Number) {
            return (T) (Integer) ((Number) val).intValue();
        }
        if (defaultValue instanceof Float && val instanceof Number) {
            return (T) (Float) ((Number) val).floatValue();
        }
        if (defaultValue instanceof Double && val instanceof Number) {
            return (T) (Double) ((Number) val).doubleValue();
        }
        return (T) val;
    }

    public void set(String key, Object value) {
        data.put(key, value);
    }

    public boolean toggle(String key) {
        boolean current = get(key, true);
        boolean next = !current;
        data.put(key, next);
        save();
        return next;
    }

    public java.nio.file.Path getPath() { return path; }

    public void load() {
        try (var reader = new FileReader(path.toFile())) {
            Map<String, Object> loaded = GSON.fromJson(reader, TYPE);
            if (loaded != null) {
                data.putAll(loaded);
            }
        } catch (Exception e) {
            StellaClientMod.LOGGER.warn("Could not load config: {}", e.getMessage());
        }
    }

    public void save() {
        try {
            path.toFile().getParentFile().mkdirs();
            try (var writer = new FileWriter(path.toFile())) {
                GSON.toJson(data, writer);
            }
        } catch (Exception e) {
            StellaClientMod.LOGGER.error("Could not save config: {}", e.getMessage());
        }
    }
}
