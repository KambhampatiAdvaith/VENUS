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


export default function Settings() {
  const [settings, setSettings] = useState<VenusSettings>(defaultSettings);
  const [savedMessage, setSavedMessage] = useState("");


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
  }


  function saveSettings() {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    setSavedMessage("Settings saved successfully.");
  }


  function resetSettings() {
    setSettings(defaultSettings);
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(defaultSettings));
    setSavedMessage("Settings reset to default V.E.N.U.S configuration.");
  }


  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <h1 className="text-4xl font-bold mb-2">
          Dashboard Preferences
        </h1>

        <p className="text-slate-400 mb-8">
          Configure local browser preferences for dashboard polling and frontend load alerts.
        </p>

        <div className="bg-slate-900 rounded-xl p-6 space-y-6 border border-slate-800">
          <div>
            <label className="block mb-2 text-slate-300">
              Dashboard Refresh Interval
            </label>

            <select
              value={settings.refreshInterval}
              onChange={(event) =>
                updateSetting("refreshInterval", event.target.value)
              }
              className="w-full bg-slate-800 p-3 rounded-lg border border-slate-700"
            >
              <option value="5">
                5 Seconds
              </option>

              <option value="10">
                10 Seconds
              </option>

              <option value="30">
                30 Seconds
              </option>

              <option value="60">
                1 Minute
              </option>
            </select>
          </div>

          <div>
            <label className="block mb-2 text-slate-300">
              Alert Threshold
            </label>

            <input
              type="number"
              min={1}
              max={100}
              value={settings.alertThreshold}
              onChange={(event) =>
                updateSetting("alertThreshold", Number(event.target.value))
              }
              className="w-full bg-slate-800 p-3 rounded-lg border border-slate-700"
            />

            <p className="text-slate-500 text-sm mt-2">
              Load balancing cards use this local threshold to mark nodes as overloaded when backend status does not provide a threshold.
            </p>
          </div>

          <div>
            <label className="block mb-2 text-slate-300">
              Theme
            </label>

            <select
              value={settings.theme}
              onChange={(event) =>
                updateSetting("theme", event.target.value)
              }
              className="w-full bg-slate-800 p-3 rounded-lg border border-slate-700"
            >
              <option value="dark">
                Dark Mode
              </option>
            </select>
          </div>

          <div className="flex items-center justify-between bg-slate-800 p-4 rounded-lg border border-slate-700">
            <div>
              <h2 className="font-semibold">
                Fault Notifications
              </h2>

              <p className="text-slate-400 text-sm">
                Enable alert indicators for V.E.N.U.S fault events.
              </p>
            </div>

            <input
              type="checkbox"
              checked={settings.notificationsEnabled}
              onChange={(event) =>
                updateSetting("notificationsEnabled", event.target.checked)
              }
              className="w-5 h-5"
            />
          </div>

          <div className="flex gap-4">
            <button
              onClick={saveSettings}
              className="bg-blue-600 hover:bg-blue-700 px-5 py-3 rounded-lg font-semibold transition"
            >
              Save Settings
            </button>

            <button
              onClick={resetSettings}
              className="bg-slate-800 hover:bg-slate-700 px-5 py-3 rounded-lg font-semibold transition"
            >
              Reset Defaults
            </button>
          </div>

          {savedMessage && (
            <p className="text-green-400">
              {savedMessage}
            </p>
          )}
        </div>
      </main>
    </div>
  );
}