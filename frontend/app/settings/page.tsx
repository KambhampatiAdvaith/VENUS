"use client";

import { useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import {
  defaultSettings,
  readSettings,
  SETTINGS_STORAGE_KEY,
  VenusSettings,
} from "../../services/settings";


const REFRESH_INTERVAL_LABELS: Record<string, string> = {
  "5": "5 seconds",
  "10": "10 seconds",
  "30": "30 seconds",
  "60": "1 minute",
};


function clampAlertThreshold(value: number): number {
  if (!Number.isFinite(value)) return defaultSettings.alertThreshold;
  return Math.min(100, Math.max(1, Math.round(value)));
}


export default function Settings() {
  const [settings, setSettings] = useState<VenusSettings>(defaultSettings);
  const [savedMessage, setSavedMessage] = useState("");
  const [savedIsWarning, setSavedIsWarning] = useState(false);


  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSettings(readSettings());
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);


  function updateSetting<K extends keyof VenusSettings>(
    key: K,
    value: VenusSettings[K]
  ) {
    setSettings((currentSettings) => ({
      ...currentSettings,
      [key]: value,
    }));

    setSavedMessage("");
    setSavedIsWarning(false);
  }


  function saveSettings() {
    const previousSettings = readSettings();
    const clamped = clampAlertThreshold(settings.alertThreshold);
    const settingsToSave: VenusSettings = { ...settings, alertThreshold: clamped };

    setSettings(settingsToSave);
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settingsToSave));
    setSavedIsWarning(false);

    if (previousSettings.refreshInterval !== settingsToSave.refreshInterval) {
      setSavedMessage(
        "Settings saved. Refresh interval changes apply after reloading or navigating to an auto-refresh page."
      );
      return;
    }

    setSavedMessage("Settings saved successfully.");
  }


  function resetSettings() {
    const previousSettings = readSettings();

    setSettings(defaultSettings);
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(defaultSettings));
    setSavedIsWarning(false);

    if (previousSettings.refreshInterval !== defaultSettings.refreshInterval) {
      setSavedMessage(
        "Settings reset. Refresh interval changes apply after reloading or navigating to an auto-refresh page."
      );
      return;
    }

    setSavedMessage("Settings reset to default V.E.N.U.S configuration.");
  }


  const thresholdOutOfRange =
    !Number.isFinite(settings.alertThreshold) ||
    settings.alertThreshold < 1 ||
    settings.alertThreshold > 100;

  const refreshLabel =
    REFRESH_INTERVAL_LABELS[settings.refreshInterval] ??
    `${settings.refreshInterval}s`;


  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <h1 className="text-4xl font-bold mb-2">
          Settings
        </h1>

        <p className="text-slate-400 mb-6">
          Operator preferences for live dashboard behaviour and load-alert visibility.
        </p>

        {/* Operator info banner */}
        <div className="mb-6 rounded-xl border border-blue-500/40 bg-blue-500/10 p-4 text-blue-200">
          <p className="font-semibold">
            Operator dashboard preferences
          </p>
          <p className="text-sm mt-1">
            These controls adjust how the dashboard polls the backend and when nodes are flagged as overloaded. They are saved in this browser only and do not affect backend configuration, Kafka/MQTT pipeline, or database schema.
          </p>
        </div>

        {/* Current settings summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <div className="bg-slate-900 rounded-xl p-5 border border-slate-800">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
              Refresh Interval
            </p>
            <p className="text-2xl font-bold text-white">
              {refreshLabel}
            </p>
            <p className="text-slate-500 text-xs mt-1">
              Auto-refresh pages poll backend on this interval
            </p>
          </div>

          <div className="bg-slate-900 rounded-xl p-5 border border-slate-800">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-1">
              Alert Threshold
            </p>
            <p className="text-2xl font-bold text-white">
              {settings.alertThreshold}%
            </p>
            <p className="text-slate-500 text-xs mt-1">
              Frontend load-alert level for balancing cards
            </p>
          </div>
        </div>

        {/* Section 1 — Live dashboard behaviour */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-slate-200 mb-3">
            Live Dashboard Behaviour
          </h2>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 space-y-2">
            <label className="block text-slate-300 font-medium">
              Dashboard Refresh Interval
            </label>

            <select
              value={settings.refreshInterval}
              onChange={(event) =>
                updateSetting("refreshInterval", event.target.value)
              }
              className="w-full bg-slate-800 p-3 rounded-lg border border-slate-700 text-white"
            >
              <option value="5">5 Seconds</option>
              <option value="10">10 Seconds</option>
              <option value="30">30 Seconds</option>
              <option value="60">1 Minute</option>
            </select>

            <p className="text-slate-500 text-sm">
              Pages with auto-refresh (dashboard, telemetry, nodes) re-fetch backend data on this interval. Changes take effect after navigating to or reloading an auto-refresh page.
            </p>
          </div>
        </section>

        {/* Section 2 — Load alert behaviour */}
        <section className="mb-6">
          <h2 className="text-lg font-semibold text-slate-200 mb-3">
            Load Alert Behaviour
          </h2>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 space-y-2">
            <label className="block text-slate-300 font-medium">
              Alert Threshold (1–100%)
            </label>

            <input
              type="number"
              min={1}
              max={100}
              value={settings.alertThreshold}
              onChange={(event) =>
                updateSetting("alertThreshold", Number(event.target.value))
              }
              className={`w-full bg-slate-800 p-3 rounded-lg border text-white ${
                thresholdOutOfRange ? "border-yellow-500" : "border-slate-700"
              }`}
            />

            {thresholdOutOfRange && (
              <div className="rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-3 text-yellow-200 text-sm">
                Value must be between 1 and 100. It will be clamped to the valid range when saved.
              </div>
            )}

            <p className="text-slate-500 text-sm">
              Load-balancing cards use this threshold to mark nodes as overloaded when the backend does not supply its own threshold value. Recommended range: 70–90%.
            </p>
          </div>
        </section>

        {/* Section 3 — Operational tips */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-slate-200 mb-3">
            Operational Tips
          </h2>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 text-slate-400 text-sm space-y-2">
            <p>
              <span className="text-slate-300 font-medium">Refresh interval</span> — use a short interval (5–10 s) when monitoring live telemetry flowing through the MQTT → Kafka → backend pipeline. Increase the interval to reduce polling load during idle observation.
            </p>
            <p>
              <span className="text-slate-300 font-medium">Alert threshold</span> — set to 70–80% to see realistic overload indicators when the substation simulators are running. The load-balancing page highlights nodes whose reported load exceeds this value, making it easy to spot and respond to overload events.
            </p>
          </div>
        </section>

        {/* Save / reset actions and feedback banner */}
        <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 space-y-4">
          <div className="flex flex-wrap gap-4">
            <button
              onClick={saveSettings}
              className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold transition"
            >
              Save Settings
            </button>

            <button
              onClick={resetSettings}
              className="bg-slate-700 hover:bg-slate-600 px-6 py-3 rounded-lg font-semibold transition"
            >
              Reset to Defaults
            </button>
          </div>

          {savedMessage && (
            <div
              className={`rounded-xl border p-4 text-sm ${
                savedIsWarning
                  ? "border-yellow-500/40 bg-yellow-500/10 text-yellow-200"
                  : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              }`}
            >
              <p className="font-semibold">
                {savedIsWarning ? "Notice" : "Saved"}
              </p>
              <p className="mt-1">{savedMessage}</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}