"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    api,
    LoadBalancingAction,
} from "../services/api";


type LoadBalancingMutationResult = {
    status: string;
    reason?: string;
    message?: string;
    action?: LoadBalancingAction | null;
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


export default function LoadBalancingControls() {
    const router = useRouter();

    const [pendingActions, setPendingActions] = useState<LoadBalancingAction[]>([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [lastRefreshedAt, setLastRefreshedAt] = useState("");


    const loadPendingActions = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const actions = await api.getPendingLoadBalancingActions(10);

            setPendingActions(actions);
            setLastRefreshedAt(new Date().toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }));
        } catch (currentError) {
            console.error(currentError);
            setError("Failed to load pending recommendations.");
        } finally {
            setLoading(false);
        }
    }, []);


    async function createRecommendation() {
        try {
            setLoading(true);
            setError(null);
            setMessage(null);

            const result =
                await api.createLoadBalancingRecommendation() as LoadBalancingMutationResult;

            if (result.status === "pending_approval") {
                setMessage("New load balancing recommendation created.");
            } else if (result.status === "no_action") {
                setMessage(result.reason || "No balancing recommendation was needed.");
            } else {
                setMessage(result.reason || "Recommendation request completed.");
            }

            await loadPendingActions();
            router.refresh();
        } catch (currentError) {
            console.error(currentError);
            setError("Failed to create recommendation.");
        } finally {
            setLoading(false);
        }
    }


    async function approveAction(actionId: number) {
        try {
            setLoading(true);
            setError(null);
            setMessage(null);

            const result =
                await api.approveLoadBalancingAction(actionId) as LoadBalancingMutationResult;

            if (result.status === "approved") {
                setMessage(`Action ${actionId} approved and executed.`);
            } else {
                setMessage(result.message || `Action ${actionId} approval request completed.`);
            }

            await loadPendingActions();
            router.refresh();
        } catch (currentError) {
            console.error(currentError);
            setError(`Failed to approve action ${actionId}.`);
        } finally {
            setLoading(false);
        }
    }


    async function rejectAction(actionId: number) {
        try {
            setLoading(true);
            setError(null);
            setMessage(null);

            const result =
                await api.rejectLoadBalancingAction(actionId) as LoadBalancingMutationResult;

            if (result.status === "rejected") {
                setMessage(`Action ${actionId} rejected.`);
            } else {
                setMessage(result.message || `Action ${actionId} rejection request completed.`);
            }

            await loadPendingActions();
            router.refresh();
        } catch (currentError) {
            console.error(currentError);
            setError(`Failed to reject action ${actionId}.`);
        } finally {
            setLoading(false);
        }
    }


    useEffect(() => {
        const timer = window.setTimeout(() => {
            void loadPendingActions();
        }, 0);

        window.addEventListener("venus-load-balancing-refresh", loadPendingActions);

        return () => {
            window.clearTimeout(timer);
            window.removeEventListener("venus-load-balancing-refresh", loadPendingActions);
        };
    }, [loadPendingActions]);


    return (
        <div className="mt-6 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
            <div className="p-6 border-b border-slate-800">
                <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                    <div>
                        <h3 className="text-xl font-bold">
                            Operator Approval Controls
                        </h3>

                        <p className="text-slate-400 text-sm mt-1">
                            Create supervised recommendations and approve or reject pending load balancing actions.
                        </p>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3">
                        <button
                            type="button"
                            onClick={createRecommendation}
                            disabled={loading}
                            className="rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-400 px-4 py-2 font-semibold transition"
                        >
                            {loading ? "Working..." : "Create Recommendation"}
                        </button>

                        <button
                            type="button"
                            onClick={loadPendingActions}
                            disabled={loading}
                            className="rounded-lg bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 disabled:text-slate-400 px-4 py-2 font-semibold transition"
                        >
                            Refresh Pending
                        </button>
                    </div>
                </div>

                <p className="mt-3 text-sm text-slate-400">
                    Pending actions last refreshed at: {lastRefreshedAt || "Loading..."}
                </p>

                {message ? (
                    <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3 text-green-300 text-sm">
                        {message}
                    </div>
                ) : null}

                {error ? (
                    <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-300 text-sm">
                        {error}
                    </div>
                ) : null}
            </div>

            <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                    <thead>
                        <tr className="bg-slate-800">
                            <th className="p-4 text-left border border-slate-700">ID</th>
                            <th className="p-4 text-left border border-slate-700">Action</th>
                            <th className="p-4 text-left border border-slate-700">Load Shift</th>
                            <th className="p-4 text-left border border-slate-700">Source Load</th>
                            <th className="p-4 text-left border border-slate-700">Target Load</th>
                            <th className="p-4 text-left border border-slate-700">Risk</th>
                            <th className="p-4 text-left border border-slate-700">Created</th>
                            <th className="p-4 text-left border border-slate-700">Controls</th>
                        </tr>
                    </thead>

                    <tbody>
                        {pendingActions.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={8}
                                    className="p-6 text-center text-slate-400 border border-slate-700"
                                >
                                    No pending recommendations.
                                </td>
                            </tr>
                        ) : (
                            pendingActions.map((action) => (
                                <tr
                                    key={action.id}
                                    className="hover:bg-slate-800 transition"
                                >
                                    <td className="p-4 border border-slate-700 text-slate-300">
                                        #{action.id}
                                    </td>

                                    <td className="p-4 border border-slate-700">
                                        <div className="font-semibold">
                                            {action.source_node} → {action.target_node}
                                        </div>

                                        <div className="text-xs text-slate-500 mt-1">
                                            {formatLabel(action.execution_mode)} mode
                                        </div>
                                    </td>

                                    <td className="p-4 border border-slate-700 text-cyan-400 font-semibold">
                                        {action.load_shifted}%
                                    </td>

                                    <td className="p-4 border border-slate-700">
                                        {action.source_load_before}% → {action.source_load_after}%
                                    </td>

                                    <td className="p-4 border border-slate-700">
                                        {action.target_load_before}% → {action.target_load_after}%
                                    </td>

                                    <td className="p-4 border border-slate-700">
                                        {action.risk_before} → {action.risk_after}
                                    </td>

                                    <td className="p-4 border border-slate-700 text-sm text-slate-300">
                                        {formatDateTime(action.created_at)}
                                    </td>

                                    <td className="p-4 border border-slate-700">
                                        <div className="flex flex-col sm:flex-row gap-2">
                                            <button
                                                type="button"
                                                onClick={() => approveAction(action.id)}
                                                disabled={loading}
                                                className="rounded-md bg-green-600 hover:bg-green-500 disabled:bg-slate-700 disabled:text-slate-400 px-3 py-2 text-sm font-semibold transition"
                                            >
                                                Approve
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() => rejectAction(action.id)}
                                                disabled={loading}
                                                className="rounded-md bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:text-slate-400 px-3 py-2 text-sm font-semibold transition"
                                            >
                                                Reject
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {pendingActions.length > 0 ? (
                <div className="p-5 border-t border-slate-800 bg-slate-950/40">
                    <p className="text-sm text-slate-400">
                        Pending recommendations are generated by the V.E.N.U.S decision engine but require operator approval before being marked as executed.
                    </p>
                </div>
            ) : null}
        </div>
    );
}