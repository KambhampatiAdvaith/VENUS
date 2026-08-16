"use client";

export const SETTINGS_STORAGE_KEY = "venus_settings";


export type VenusTheme = "dark" | "light";


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


export function normalizeTheme(theme: unknown): VenusTheme {
    return theme === "light" ? "light" : "dark";
}


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
            theme: normalizeTheme(parsedSettings.theme),
        };
    } catch {
        return defaultSettings;
    }
}


export function applyTheme(theme: unknown): VenusTheme {
    const normalizedTheme = normalizeTheme(theme);

    if (typeof document === "undefined") {
        return normalizedTheme;
    }

    document.documentElement.dataset.theme = normalizedTheme;
    document.documentElement.classList.toggle("dark", normalizedTheme === "dark");
    document.documentElement.classList.toggle("light", normalizedTheme === "light");

    return normalizedTheme;
}


export function writeSettings(settings: VenusSettings): VenusSettings {
    const normalizedSettings: VenusSettings = {
        ...defaultSettings,
        ...settings,
        theme: normalizeTheme(settings.theme),
    };

    if (typeof window !== "undefined") {
        window.localStorage.setItem(
            SETTINGS_STORAGE_KEY,
            JSON.stringify(normalizedSettings),
        );
    }

    applyTheme(normalizedSettings.theme);
    return normalizedSettings;
}


export function getRefreshIntervalMs(): number {
    const refreshSeconds = Number(readSettings().refreshInterval);

    if (!Number.isFinite(refreshSeconds) || refreshSeconds <= 0) {
        return Number(defaultSettings.refreshInterval) * 1000;
    }

    return refreshSeconds * 1000;
}
