"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "../../components/Sidebar";
import Navbar from "../../components/Navbar";
import { api, PredictionRecord } from "../../services/api";
import { getRefreshIntervalMs } from "../../services/settings";


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
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [lastUpdated, setLastUpdated] = useState("");


    const loadPredictions = useCallback(async () => {
        try {
            const predictionRecords = await api.getPredictions(50);
            setPredictions(predictionRecords);
            setLastUpdated(
                new Date().toLocaleTimeString("en-GB", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                })
            );
        } catch (error) {
            console.error("Failed to fetch AI predictions:", error);
        } finally {
            setLoading(false);
        }
    }, []);


    async function runPredictionCycle() {
        try {
            setRunning(true);
            setLoading(true);
            await api.runPredictions();
            await loadPredictions();
        } catch (error) {
            console.error("Failed to run AI prediction cycle:", error);
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


    const predictedFaults = predictions.filter(
        (prediction) =>
            prediction.predicted_fault !== "normal" || prediction.anomaly
    );

    const averageRiskScore =
        predictions.length > 0
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
        highRiskCount > 0
            ? "High"
            : predictedFaults.length > 0
                ? "Medium"
                : "Low";


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
                            Last updated: {lastUpdated || "Loading..."}
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800">
                        <h3 className="text-slate-400">
                            Predicted Faults
                        </h3>

                        <p className="text-3xl font-bold mt-2">
                            {predictedFaults.length}
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

                <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
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
                                        className="p-6 text-center text-slate-400 border border-slate-700"
                                    >
                                        No AI prediction records available.
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