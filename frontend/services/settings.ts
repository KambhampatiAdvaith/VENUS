"use client";

export const SETTINGS_STORAGE_KEY = "venus_settings";


export type VenusSettings = {
    refreshInterval: string;
    alertThreshold: number;
    notificationsEnabled: boolean;
};


export const defaultSettings: VenusSettings = {
    refreshInterval: "10",
    alertThreshold: 80,
    notificationsEnabled: true,
};


export function readSettings(): VenusSettings {
    if (typeof window === "undefined") {
        return defaultSettings;
    }

    const storedSettings = window.localStorage.getItem(SETTINGS_STORAGE_KEY);

    if (!storedSettings) {
        return defaultSettings;
    }

    try {
        const parsedSettings = JSON.parse(storedSettings);

        return {
            refreshInterval: parsedSettings.refreshInterval ?? defaultSettings.refreshInterval,
            alertThreshold: parsedSettings.alertThreshold ?? defaultSettings.alertThreshold,
            notificationsEnabled:
                parsedSettings.notificationsEnabled ?? defaultSettings.notificationsEnabled,
        };
    } catch {
        return defaultSettings;
    }
}


export function writeSettings(settings: VenusSettings): VenusSettings {
    const normalizedSettings: VenusSettings = {
        refreshInterval: settings.refreshInterval,
        alertThreshold: settings.alertThreshold,
        notificationsEnabled: settings.notificationsEnabled,
    };

    if (typeof window !== "undefined") {
        window.localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify(normalizedSettings),
        );
    }

    return normalizedSettings;
}


export function getRefreshIntervalMs(): number {
    const refreshSeconds = Number(readSettings().refreshInterval);

    if (!Number.isFinite(refreshSeconds) || refreshSeconds <= 0) {
        return Number(defaultSettings.refreshInterval) * 1000;
    }

    return refreshSeconds * 1000;
}
