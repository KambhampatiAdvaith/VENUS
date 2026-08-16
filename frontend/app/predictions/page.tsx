"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import { api, PredictionRecord, PredictionMetrics } from "../../services/api";
import { getRefreshIntervalMs } from "../../services/settings";
import { createWebSocketClient } from "../../services/websocket";


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


function getRiskLevel(prediction: PredictionRecord): string {
    if (prediction.anomaly) {
        return "High";
    }

    if (prediction.predicted_fault === "normal") {
        return "Low";
    }

    if (prediction.probability >= 0.8) {
        return "High";
    }

    if (prediction.probability >= 0.5) {
        return "Medium";
    }

    return "Low";
}


function getRiskColor(riskLevel: string): string {
    if (riskLevel === "High") {
        return "text-red-400";
    }

    if (riskLevel === "Medium") {
        return "text-yellow-400";
    }

    return "text-green-400";
}


export default function Predictions() {
    const [predictions, setPredictions] = useState<PredictionRecord[]>([]);
    const [predictionMetrics, setPredictionMetrics] = useState<PredictionMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [lastUpdated, setLastUpdated] = useState("");
    const [fetchError, setFetchError] = useState(false);
    const [runError, setRunError] = useState(false);


    const loadPredictions = useCallback(async () => {
        try {
            const [predictionRecords, metrics] = await Promise.all([
                api.getPredictions(50),
                api.getPredictionMetrics(),
            ]);
            setPredictions(predictionRecords);
            setPredictionMetrics(metrics);
            setFetchError(false);
            setLastUpdated(
                new Date().toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                })
            );
        } catch (error) {
            console.error("Failed to fetch AI predictions:", error);
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
        const ws = createWebSocketClient(
            (event) => {
                if (event.event === "prediction" || event.event === "fault") {
                    void loadPredictions();
                }
            },
        );

        ws.connect();

        return () => {
            ws.disconnect();
        };
    }, [loadPredictions]);


    const predictedFaults = predictions.filter(
        (prediction) =>
            prediction.predicted_fault !== "normal" || prediction.anomaly
    );

    const averageRiskScore =
        predictionMetrics != null
            ? predictionMetrics.risk_score
            : predictions.length > 0
                ? predictions.reduce(
                    (sum, prediction) => sum + prediction.probability,
                    0
                ) / predictions.length
                : 0;

    const highRiskCount = predictions.filter(
        (prediction) =>
            prediction.anomaly ||
            (prediction.predicted_fault !== "normal" &&
                prediction.probability >= 0.8)
    ).length;

    const systemRiskLevel =
        predictionMetrics != null
            ? predictionMetrics.system_risk_level
            : highRiskCount > 0
                ? "High"
                : predictedFaults.length > 0
                    ? "Medium"
                    : "Low";

    const summaryPredictedFaults =
        predictionMetrics != null
            ? predictionMetrics.predicted_faults
            : predictedFaults.length;


    return (
        <div className="flex min-h-screen bg-slate-950 text-white">
            <Sidebar />

            <main className="flex-1 p-8">
                <Navbar />

                <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between mb-8">
                    <div>
                        <h1 className="text-4xl font-bold mb-2">
                            AI Predictions
                        </h1>

                        <p className="text-slate-400">
                            V.E.N.U.S predictive fault detection and anomaly analysis
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
                                ? `Live refresh active · synced at ${lastUpdated}`
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

                {!fetchError && !loading ? (
                    <div className="mb-8 rounded-xl border border-cyan-500/40 bg-cyan-500/10 p-4 text-cyan-100">
                        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                            <div>
                                <p className="text-sm uppercase tracking-wide text-cyan-300">
                                    Live AI Analysis
                                </p>
                                <p className="text-xl font-bold">
                                    {predictions.length === 0
                                        ? "No predictions yet — run a prediction cycle"
                                        : `Risk level: ${systemRiskLevel}`}
                                </p>
                                <p className="mt-1 text-sm text-cyan-200/80">
                                    {predictions.length > 0
                                        ? `${predictions.length} prediction${predictions.length !== 1 ? "s" : ""} analysed · summary from latest per-substation metrics · auto-refreshes on new events.`
                                        : "Click \u201cRefresh Now\u201d or wait for a scheduled prediction cycle."}
                                </p>
                            </div>

                            {predictions.length > 0 ? (
                                <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
                                    <div>
                                        <p className="text-cyan-300">Predictions</p>
                                        <p className="font-semibold">{predictions.length}</p>
                                    </div>
                                    <div>
                                        <p className="text-cyan-300">Predicted Faults</p>
                                        <p className="font-semibold">{predictedFaults.length}</p>
                                    </div>
                                    <div>
                                        <p className="text-cyan-300">High Risk</p>
                                        <p className="font-semibold">{highRiskCount}</p>
                                    </div>
                                    <div>
                                        <p className="text-cyan-300">Avg Risk Score</p>
                                        <p className="font-semibold">
                                            {(averageRiskScore * 100).toFixed(1)}%
                                        </p>
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    </div>
                ) : null}

                {runError && (
                    <div className="mb-6 rounded-xl border border-yellow-500/40 bg-yellow-500/10 p-4 text-yellow-300">
                        <p className="font-semibold">Prediction cycle failed</p>
                        <p className="text-sm mt-1">
                            The AI prediction cycle could not complete. Check that the backend is running and telemetry data is available.
                        </p>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                        <h3 className="text-slate-400">
                            Predicted Faults
                        </h3>

                        <p className="text-3xl font-bold mt-2">
                            {summaryPredictedFaults}
                        </p>
                    </div>

                    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                        <h3 className="text-slate-400">
                            Average Confidence
                        </h3>

                        <p className="text-3xl font-bold mt-2">
                            {(averageRiskScore * 100).toFixed(2)}%
                        </p>
                    </div>

                    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                        <h3 className="text-slate-400">
                            System Risk Level
                        </h3>

                        <p className={`text-3xl font-bold mt-2 ${getRiskColor(systemRiskLevel)}`}>
                            {systemRiskLevel}
                        </p>
                    </div>
                </div>

                <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden overflow-x-auto">
                    <div className="p-6 border-b border-slate-800">
                        <h2 className="text-2xl font-bold">
                            Latest AI Prediction Records
                        </h2>

                        <p className="text-slate-400 mt-1">
                            Predictions generated from telemetry using Isolation Forest and XGBoost
                        </p>
                    </div>

                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-slate-800">
                                <th className="p-4 text-left border border-slate-700">
                                    Node
                                </th>

                                <th className="p-4 text-left border border-slate-700">
                                    Predicted Fault
                                </th>

                                <th className="p-4 text-left border border-slate-700">
                                    Probability
                                </th>

                                <th className="p-4 text-left border border-slate-700">
                                    Anomaly
                                </th>

                                <th className="p-4 text-left border border-slate-700">
                                    Anomaly Score
                                </th>

                                <th className="p-4 text-left border border-slate-700">
                                    Risk Level
                                </th>

                                <th className="p-4 text-left border border-slate-700">
                                    Timestamp
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {loading ? (
                                <tr>
                                    <td
                                        colSpan={7}
                                        className="p-6 text-center text-slate-400 border border-slate-700"
                                    >
                                        Loading AI prediction records...
                                    </td>
                                </tr>
                            ) : predictions.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={7}
                                        className="p-6 border border-slate-700"
                                    >
                                        <p className="font-semibold text-slate-300">No AI prediction records yet</p>
                                        <p className="text-sm mt-1 text-slate-400">
                                            Run a prediction cycle to generate results, or ensure telemetry data is available first:
                                        </p>
                                        <p className="text-sm mt-1 font-mono text-slate-500">
                                            POST /telemetry/simulate/normal → then click &quot;Refresh Now&quot;
                                        </p>
                                    </td>
                                </tr>
                            ) : (
                                predictions.map((prediction) => {
                                    const riskLevel = getRiskLevel(prediction);

                                    return (
                                        <tr
                                            key={prediction.id}
                                            className="hover:bg-slate-800 transition"
                                        >
                                            <td className="p-4 border border-slate-700">
                                                Substation {prediction.substation}
                                            </td>

                                            <td className="p-4 border border-slate-700">
                                                {formatFaultName(prediction.predicted_fault)}
                                            </td>

                                            <td
                                                className={`p-4 border border-slate-700 font-semibold ${getProbabilityColor(
                                                    prediction.probability
                                                )}`}
                                            >
                                                {(prediction.probability * 100).toFixed(2)}%
                                            </td>

                                            <td className="p-4 border border-slate-700">
                                                {prediction.anomaly ? (
                                                    <span className="text-red-400">
                                                        Detected
                                                    </span>
                                                ) : (
                                                    <span className="text-green-400">
                                                        Normal
                                                    </span>
                                                )}
                                            </td>

                                            <td className="p-4 border border-slate-700">
                                                {(prediction.anomaly_score * 100).toFixed(2)}%
                                            </td>

                                            <td
                                                className={`p-4 border border-slate-700 font-semibold ${getRiskColor(
                                                    riskLevel
                                                )}`}
                                            >
                                                {riskLevel}
                                            </td>

                                            <td className="p-4 border border-slate-700 text-sm text-slate-300">
                                                {formatTimestamp(prediction.timestamp)}
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </main>
        </div>
    );
}