"use client";

export const SETTINGS_STORAGE_KEY = "venus_settings";


export type VenusTheme = "dark";


export type VenusSettings = {
    refreshInterval: string;
    alertThreshold: number;
    theme: VenusTheme;
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
        const parsedSettings = JSON.parse(storedSettings);

        return {
            ...defaultSettings,
            ...parsedSettings,
            theme: "dark" as VenusTheme,
        };
    } catch {
        return defaultSettings;
    }
}


export function applyDarkTheme(): void {
    if (typeof document !== "undefined") {
        document.documentElement.dataset.theme = "dark";
        document.documentElement.classList.add("dark");
        document.documentElement.classList.remove("light");
    }
}


export function writeSettings(settings: VenusSettings): VenusSettings {
    const normalizedSettings: VenusSettings = {
        ...defaultSettings,
        ...settings,
        theme: "dark",
    };

    if (typeof window !== "undefined") {
        window.localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify(normalizedSettings),
        );
    }

    applyDarkTheme();
    return normalizedSettings;
}


export function getRefreshIntervalMs(): number {
    const refreshSeconds = Number(readSettings().refreshInterval);

    if (!Number.isFinite(refreshSeconds) || refreshSeconds <= 0) {
        return Number(defaultSettings.refreshInterval) * 1000;
    }

    return refreshSeconds * 1000;
}
