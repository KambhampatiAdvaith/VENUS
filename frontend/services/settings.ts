"use client";

export const SETTINGS_STORAGE_KEY = "venus_settings";


export type VenusSettings = {
    refreshInterval: string;
    alertThreshold: number;
    theme: string;
    notificationsEnabled: boolean;
};


export const defaultSettings: VenusSettings = {
    refreshInterval: "10",
    alertThreshold: 80,
    theme: "dark",
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
        return {
            ...defaultSettings,
            ...JSON.parse(storedSettings),
        };
    } catch {
        return defaultSettings;
    }
}


export function getRefreshIntervalMs(): number {
    const refreshSeconds = Number(readSettings().refreshInterval);

    if (!Number.isFinite(refreshSeconds) || refreshSeconds <= 0) {
        return Number(defaultSettings.refreshInterval) * 1000;
    }

    return refreshSeconds * 1000;
}
