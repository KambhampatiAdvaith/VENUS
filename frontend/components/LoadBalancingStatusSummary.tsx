"use client";

import { useEffect, useState } from "react";
import { NodeStatus } from "../services/api";
import { defaultSettings, readSettings } from "../services/settings";


type LoadBalancingStatusSummaryProps = {
    nodes: NodeStatus[];
};


function getLoadStatus(load: number | null, alertThreshold: number): string {
    if (load === null) {
        return "Unknown";
    }

    if (load >= alertThreshold) {
        return "Overloaded";
    }

    if (load >= Math.max(0, alertThreshold - 15)) {
        return "High Load";
    }

    if (load >= 40) {
        return "Balanced";
    }

    return "Low Load";
}


function getStatusColor(status: string): string {
    if (status === "Balanced" || status === "Low Load") {
        return "text-green-400";
    }

    if (status === "High Load") {
        return "text-yellow-400";
    }

    if (status === "Overloaded") {
        return "text-red-400";
    }

    return "text-slate-400";
}


function getRecommendedAction(
    nodes: NodeStatus[],
    alertThreshold: number,
): string {
    if (nodes.length === 0) {
        return "No node data available.";
    }

    const sortedNodes = [...nodes].sort(
        (a, b) => (b.load ?? 0) - (a.load ?? 0)
    );

    const highestLoadNode = sortedNodes[0];
    const lowestLoadNode = sortedNodes[sortedNodes.length - 1];

    if ((highestLoadNode.load ?? 0) < Math.max(0, alertThreshold - 10)) {
        return "Grid load is currently balanced. No load transfer required.";
    }

    return `Recommend shifting load from Substation ${highestLoadNode.node} to Substation ${lowestLoadNode.node}.`;
}


export default function LoadBalancingStatusSummary({
    nodes,
}: LoadBalancingStatusSummaryProps) {
    const [alertThreshold, setAlertThreshold] = useState(
        defaultSettings.alertThreshold,
    );


    useEffect(() => {
        const timer = window.setTimeout(() => {
            setAlertThreshold(readSettings().alertThreshold);
        }, 0);

        return () => window.clearTimeout(timer);
    }, []);


    const recommendedAction = getRecommendedAction(nodes, alertThreshold);

    return (
        <>
            <div className="mb-4 rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-400">
                Local alert threshold: {alertThreshold}% load
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                {nodes.length === 0 ? (
                    <div className="bg-slate-900 rounded-xl p-6 border border-slate-800 text-slate-400">
                        No load balancing data available.
                    </div>
                ) : (
                    nodes.map((node) => {
                        const status = getLoadStatus(node.load, alertThreshold);

                        return (
                            <div
                                key={node.node}
                                className="bg-slate-900 rounded-xl p-6 border border-slate-800"
                            >
                                <h3 className="text-slate-400">
                                    Substation {node.node}
                                </h3>

                                <p className="text-3xl font-bold mt-2">
                                    {node.load !== null ? `${node.load}%` : "N/A"}
                                </p>

                                <p className={`${getStatusColor(status)} mt-2`}>
                                    {status}
                                </p>
                            </div>
                        );
                    })
                )}
            </div>

            <div className="mt-8 bg-slate-900 rounded-xl p-6 border border-slate-800">
                <h2 className="text-2xl font-bold mb-2">
                    Load Balancing Recommendation
                </h2>

                <p className="text-slate-300">
                    {recommendedAction}
                </p>
            </div>

            <div className="mt-8 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
                <div className="p-6 border-b border-slate-800">
                    <h2 className="text-2xl font-bold">
                        Distribution Summary
                    </h2>
                </div>

                <table className="w-full border-collapse">
                    <thead>
                        <tr className="bg-slate-800">
                            <th className="p-4 text-left border border-slate-700">Zone</th>
                            <th className="p-4 text-left border border-slate-700">Current Load</th>
                            <th className="p-4 text-left border border-slate-700">Capacity</th>
                            <th className="p-4 text-left border border-slate-700">Status</th>
                            <th className="p-4 text-left border border-slate-700">Voltage</th>
                            <th className="p-4 text-left border border-slate-700">Frequency</th>
                        </tr>
                    </thead>

                    <tbody>
                        {nodes.length === 0 ? (
                            <tr>
                                <td
                                    colSpan={6}
                                    className="p-6 text-center text-slate-400 border border-slate-700"
                                >
                                    No distribution records available.
                                </td>
                            </tr>
                        ) : (
                            nodes.map((node) => {
                                const status = getLoadStatus(node.load, alertThreshold);

                                return (
                                    <tr
                                        key={node.node}
                                        className="hover:bg-slate-800 transition"
                                    >
                                        <td className="p-4 border border-slate-700">
                                            Substation {node.node}
                                        </td>

                                        <td className="p-4 border border-slate-700">
                                            {node.load !== null ? `${node.load}%` : "N/A"}
                                        </td>

                                        <td className="p-4 border border-slate-700">
                                            100%
                                        </td>

                                        <td className={`p-4 border border-slate-700 ${getStatusColor(status)}`}>
                                            {status}
                                        </td>

                                        <td className="p-4 border border-slate-700">
                                            {node.voltage !== null ? `${node.voltage} V` : "N/A"}
                                        </td>

                                        <td className="p-4 border border-slate-700">
                                            {node.frequency !== null ? `${node.frequency} Hz` : "N/A"}
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
        </>
    );
}
