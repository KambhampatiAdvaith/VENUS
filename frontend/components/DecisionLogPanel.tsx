"use client";

import { useEffect, useState } from "react";
import {
    api,
    LoadBalancingDecisionLog,
    LoadBalancingDecisionLogSummary,
} from "../services/api";


const fallbackSummary: LoadBalancingDecisionLogSummary = {
    status: "empty",
    total_decisions: 0,
    executed_decisions: 0,
    pending_decisions: 0,
    rejected_decisions: 0,
    automatic_decisions: 0,
    manual_decisions: 0,
    approval_mode_decisions: 0,
};


function formatDateTime(timestamp: string | null): string {
    if (!timestamp) {
        return "N/A";
    }

    return new Date(timestamp).toLocaleString();
}


function formatLabel(value: string): string {
    if (!value) {
        return "Unknown";
    }

    return value
        .replace(/_/g, " ")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}


function getStatusColor(status: string): string {
    if (status === "executed" || status === "successful") {
        return "text-green-400";
    }

    if (status === "pending") {
        return "text-yellow-400";
    }

    if (status === "rejected" || status === "ineffective") {
        return "text-red-400";
    }

    return "text-slate-400";
}


export default function DecisionLogPanel() {
    const [decisionLogs, setDecisionLogs] = useState<LoadBalancingDecisionLog[]>([]);
    const [summary, setSummary] =
        useState<LoadBalancingDecisionLogSummary>(fallbackSummary);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);


    async function loadDecisionLogs() {
        try {
            setLoading(true);
            setError(null);

            const [logsResponse, summaryResponse] = await Promise.all([
                api.getLoadBalancingDecisionLog(10),
                api.getLoadBalancingDecisionLogSummary(),
            ]);

            setDecisionLogs(logsResponse);
            setSummary(summaryResponse);
        } catch (currentError) {
            console.error(currentError);
            setError("Failed to load decision audit log.");
        } finally {
            setLoading(false);
        }
    }


    useEffect(() => {
        void loadDecisionLogs();
    }, []);


    return (
        <section className="mt-10">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-5">
                <div>
                    <h2 className="text-2xl font-bold">
                        Decision Audit Trail
                    </h2>

                    <p className="text-slate-400 text-sm mt-1">
                        Formal operational log of prediction triggers, balancing decisions, operator workflow, and observed results.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={loadDecisionLogs}
                    disabled={loading}
                    className="rounded-lg bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 disabled:text-slate-400 px-4 py-2 font-semibold transition"
                >
                    {loading ? "Refreshing..." : "Refresh Audit Log"}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                <div className="bg-slate-900 rounded-xl p-6 border border-blue-500/40">
                    <h3 className="text-slate-400">
                        Total Decisions
                    </h3>

                    <p className="text-4xl font-bold mt-4 text-blue-400">
                        {summary.total_decisions}
                    </p>

                    <p className="text-slate-500 text-sm mt-2">
                        Logged balancing decisions
                    </p>
                </div>

                <div className="bg-slate-900 rounded-xl p-6 border border-green-500/40">
                    <h3 className="text-slate-400">
                        Executed
                    </h3>

                    <p className="text-4xl font-bold mt-4 text-green-400">
                        {summary.executed_decisions}
                    </p>

                    <p className="text-slate-500 text-sm mt-2">
                        Approved or directly executed
                    </p>
                </div>

                <div className="bg-slate-900 rounded-xl p-6 border border-yellow-500/40">
                    <h3 className="text-slate-400">
                        Pending
                    </h3>

                    <p className="text-4xl font-bold mt-4 text-yellow-400">
                        {summary.pending_decisions}
                    </p>

                    <p className="text-slate-500 text-sm mt-2">
                        Awaiting operator review
                    </p>
                </div>

                <div className="bg-slate-900 rounded-xl p-6 border border-red-500/40">
                    <h3 className="text-slate-400">
                        Rejected
                    </h3>

                    <p className="text-4xl font-bold mt-4 text-red-400">
                        {summary.rejected_decisions}
                    </p>

                    <p className="text-slate-500 text-sm mt-2">
                        Rejected recommendations
                    </p>
                </div>
            </div>

            {error ? (
                <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-300 text-sm">
                    {error}
                </div>
            ) : null}

            <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="p-6 border-b border-slate-800">
                    <h3 className="text-xl font-bold">
                        Operational Decision Log
                    </h3>

                    <p className="text-slate-400 text-sm mt-1">
                        Each entry records the complete chain from trigger to observed outcome.
                    </p>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                        <thead>
                            <tr className="bg-slate-800">
                                <th className="p-4 text-left border border-slate-700">ID</th>
                                <th className="p-4 text-left border border-slate-700">Trigger</th>
                                <th className="p-4 text-left border border-slate-700">Decision</th>
                                <th className="p-4 text-left border border-slate-700">Workflow</th>
                                <th className="p-4 text-left border border-slate-700">Status</th>
                                <th className="p-4 text-left border border-slate-700">Result</th>
                                <th className="p-4 text-left border border-slate-700">Time</th>
                            </tr>
                        </thead>

                        <tbody>
                            {decisionLogs.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={7}
                                        className="p-6 text-center text-slate-400 border border-slate-700"
                                    >
                                        No decision log entries available.
                                    </td>
                                </tr>
                            ) : (
                                decisionLogs.map((entry) => (
                                    <tr
                                        key={entry.decision_id}
                                        className="hover:bg-slate-800 transition align-top"
                                    >
                                        <td className="p-4 border border-slate-700 text-slate-300 font-semibold">
                                            #{entry.decision_id}
                                        </td>

                                        <td className="p-4 border border-slate-700 min-w-[260px]">
                                            <p className="text-slate-200">
                                                {entry.prediction_trigger}
                                            </p>
                                        </td>

                                        <td className="p-4 border border-slate-700 min-w-[240px]">
                                            <p className="text-cyan-300">
                                                {entry.decision_taken}
                                            </p>

                                            <p className="text-xs text-slate-500 mt-2">
                                                Load: {entry.before.source_load}% → {entry.after.source_load}%
                                            </p>

                                            <p className="text-xs text-slate-500 mt-1">
                                                Risk: {entry.before.risk_score} → {entry.after.risk_score}
                                            </p>
                                        </td>

                                        <td className="p-4 border border-slate-700 min-w-[220px]">
                                            <p className="text-slate-300">
                                                {entry.operator_workflow}
                                            </p>

                                            <p className="text-xs text-slate-500 mt-2">
                                                Mode: {formatLabel(entry.execution_mode)}
                                            </p>
                                        </td>

                                        <td
                                            className={`p-4 border border-slate-700 font-semibold ${getStatusColor(
                                                entry.action_status
                                            )}`}
                                        >
                                            {formatLabel(entry.action_status)}
                                        </td>

                                        <td className="p-4 border border-slate-700 min-w-[260px]">
                                            <p className={getStatusColor(entry.effectiveness)}>
                                                {entry.result_observed}
                                            </p>

                                            <p className="text-xs text-slate-500 mt-2">
                                                Effectiveness: {formatLabel(entry.effectiveness)}
                                            </p>
                                        </td>

                                        <td className="p-4 border border-slate-700 text-sm text-slate-300 min-w-[180px]">
                                            {formatDateTime(entry.timestamp)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="p-5 border-t border-slate-800 bg-slate-950/40">
                    <p className="text-sm text-slate-400">
                        Audit trail supports traceability for autonomous, manual, and supervised approval workflows.
                    </p>
                </div>
            </div>
        </section>
    );
}