"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import LiveAnalysisCard from "../../components/LiveAnalysisCard";
import {
  api,
  PredictionMetrics,
  PredictionRecord,
} from "../../services/api";
import { getRefreshIntervalMs } from "../../services/settings";
import { createWebSocketClient } from "../../services/websocket";

const PAGE_SIZE = 10;

function formatFaultName(fault: string): string {
  if (!fault) {
    return "Unknown";
  }

  return fault
    .replace("ai_predicted_", "")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatTimestamp(timestamp: string): string {
  if (!timestamp) {
    return "N/A";
  }

  return new Date(timestamp).toLocaleString();
}

function getProbabilityColor(probability: number): string {
  if (probability >= 0.8) {
    return "text-red-400";
  }

  if (probability >= 0.5) {
    return "text-yellow-400";
  }

  return "text-green-400";
}

export default function Predictions() {
  const [latestPredictions, setLatestPredictions] = useState<PredictionRecord[]>([]);
  const [predictionMetrics, setPredictionMetrics] = useState<PredictionMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [runError, setRunError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("");
  const [showHighRiskOnly, setShowHighRiskOnly] = useState(false);
  const [showFaultOnly, setShowFaultOnly] = useState(false);
  const [page, setPage] = useState(1);

  const loadPredictions = useCallback(async () => {
    try {
      const [latestRows, metrics] = await Promise.all([
        api.getLatestPredictions(),
        api.getPredictionMetrics(),
      ]);
      setLatestPredictions(latestRows);
      setPredictionMetrics(metrics);
      setFetchError(false);
      setLastUpdated(new Date().toLocaleString());
    } catch (error) {
      console.error("Failed to fetch latest AI predictions:", error);
      setFetchError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  async function runPredictionCycle() {
    try {
      setRunning(true);
      setLoading(true);
      setRunError(false);
      await api.runPredictions();
      await loadPredictions();
    } catch (error) {
      console.error("Failed to run AI prediction cycle:", error);
      setRunError(true);
      setLoading(false);
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadPredictions();
    }, 0);

    const interval = setInterval(() => {
      void loadPredictions();
    }, getRefreshIntervalMs());

    return () => {
      window.clearTimeout(timer);
      clearInterval(interval);
    };
  }, [loadPredictions]);

  useEffect(() => {
    const ws = createWebSocketClient((event) => {
      if (event.event === "prediction" || event.event === "fault") {
        void loadPredictions();
      }
    });

    ws.connect();
    return () => ws.disconnect();
  }, [loadPredictions]);

  const filteredPredictions = useMemo(() => {
    return latestPredictions.filter((prediction) => {
      if (showHighRiskOnly && prediction.probability < 0.8) {
        return false;
      }

      if (showFaultOnly && prediction.predicted_fault === "normal") {
        return false;
      }

      return true;
    });
  }, [latestPredictions, showFaultOnly, showHighRiskOnly]);

  const totalPages = Math.max(1, Math.ceil(filteredPredictions.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageRows = filteredPredictions.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  const predictedFaults = latestPredictions.filter(
    (prediction) => prediction.predicted_fault !== "normal" || prediction.anomaly,
  ).length;

  const highRiskCount = latestPredictions.filter(
    (prediction) =>
      prediction.anomaly ||
      (prediction.predicted_fault !== "normal" && prediction.probability >= 0.8),
  ).length;

  const averageRisk = predictionMetrics != null
    ? predictionMetrics.risk_score
    : latestPredictions.length > 0
      ? (latestPredictions.reduce(
        (sum, prediction) => sum + prediction.probability,
        0,
      ) / latestPredictions.length) * 100
      : 0;

  const systemRiskLevel = predictionMetrics?.system_risk_level ?? "unknown";

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">
      <Sidebar />

      <main className="flex-1 p-8">
        <Navbar />

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2">AI Predictions</h1>
            <p className="text-slate-400">
              Latest per-substation AI outcomes with focused risk filters.
            </p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <button
              type="button"
              onClick={runPredictionCycle}
              disabled={running}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-semibold transition"
            >
              {running ? "Running..." : "Refresh Now"}
            </button>
            <p className="text-slate-400 text-sm">
              {lastUpdated
                ? `Last updated: ${lastUpdated}`
                : "Live refresh active · awaiting first sync..."}
            </p>
          </div>
        </div>

        {fetchError && (
          <div className="mb-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-red-300">
            <p className="font-semibold">Unable to load predictions</p>
            <p className="text-sm mt-1">
              The backend could not be reached. Make sure the V.E.N.U.S backend is running and try refreshing.
            </p>
          </div>
        )}

        {!fetchError && !loading && (
          <LiveAnalysisCard
            title="Live AI Analysis"
            headline={latestPredictions.length === 0 ? "No predictions yet" : `System risk level: ${systemRiskLevel}`}
            subtext={lastUpdated ? `Latest per-substation snapshot refreshed at ${lastUpdated}.` : undefined}
            metrics={[
              {
                label: "Predictions analysed (latest per-substation)",
                value: String(latestPredictions.length),
              },
              {
                label: "Predicted faults (latest per-substation)",
                value: String(predictionMetrics?.predicted_faults ?? predictedFaults),
              },
              {
                label: "High-risk predictions (probability ≥ 0.8)",
                value: String(highRiskCount),
              },
              {
                label: "Average risk (latest predictions)",
                value: `${averageRisk.toFixed(2)}%`,
              },
            ]}
          />
        )}

        {runError && (
          <div className="mb-6 rounded-xl border border-yellow-500/40 bg-yellow-500/10 p-4 text-yellow-300">
            <p className="font-semibold">Prediction cycle failed</p>
            <p className="text-sm mt-1">
              The AI prediction cycle could not complete. Check that the backend is running and telemetry data is available.
            </p>
          </div>
        )}

        <div className="mb-4 flex flex-wrap gap-3">
          <label className="inline-flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={showHighRiskOnly}
              onChange={(event) => {
                setShowHighRiskOnly(event.target.checked);
                setPage(1);
              }}
            />
            High-risk only (risk &gt;= 0.8)
          </label>

          <label className="inline-flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={showFaultOnly}
              onChange={(event) => {
                setShowFaultOnly(event.target.checked);
                setPage(1);
              }}
            />
            Predicted fault only (predicted_fault != normal)
          </label>
        </div>

        <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden overflow-x-auto">
          <div className="p-6 border-b border-slate-800">
            <h2 className="text-2xl font-bold">Latest Per-Substation Predictions</h2>
            <p className="text-slate-400 mt-1">
              One latest prediction row per substation from <code>/predictions/latest</code>.
            </p>
          </div>

          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-800">
                <th className="p-4 text-left border border-slate-700">Substation</th>
                <th className="p-4 text-left border border-slate-700">Predicted Fault</th>
                <th className="p-4 text-left border border-slate-700">Probability</th>
                <th className="p-4 text-left border border-slate-700">Anomaly</th>
                <th className="p-4 text-left border border-slate-700">Anomaly Score</th>
                <th className="p-4 text-left border border-slate-700">Timestamp</th>
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-slate-400 border border-slate-700">
                    Loading AI prediction records...
                  </td>
                </tr>
              ) : pageRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-slate-400 border border-slate-700">
                    No predictions match the selected filters.
                  </td>
                </tr>
              ) : (
                pageRows.map((prediction) => (
                  <tr key={prediction.id} className="hover:bg-slate-800 transition">
                    <td className="p-4 border border-slate-700">Substation {prediction.substation}</td>
                    <td className="p-4 border border-slate-700">{formatFaultName(prediction.predicted_fault)}</td>
                    <td className={`p-4 border border-slate-700 font-semibold ${getProbabilityColor(prediction.probability)}`}>
                      {(prediction.probability * 100).toFixed(2)}%
                    </td>
                    <td className="p-4 border border-slate-700">{prediction.anomaly ? "Detected" : "Normal"}</td>
                    <td className="p-4 border border-slate-700">{(prediction.anomaly_score * 100).toFixed(2)}%</td>
                    <td className="p-4 border border-slate-700 text-sm text-slate-300">{formatTimestamp(prediction.timestamp)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          <div className="flex items-center justify-between border-t border-slate-800 p-4 text-sm text-slate-300">
            <span>
              Page {currentPage} of {totalPages} · {filteredPredictions.length} filtered row{filteredPredictions.length !== 1 ? "s" : ""}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded border border-slate-700 px-3 py-1 disabled:opacity-40"
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <button
                type="button"
                className="rounded border border-slate-700 px-3 py-1 disabled:opacity-40"
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                disabled={currentPage >= totalPages}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
