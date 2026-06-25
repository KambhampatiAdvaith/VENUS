"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getRefreshIntervalMs } from "../services/settings";


type AutoRefreshControlsProps = {
    label?: string;
};


function formatRefreshTime(date: Date): string {
    return date.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });
}


export default function AutoRefreshControls({
    label = "Refresh",
}: AutoRefreshControlsProps) {
    const router = useRouter();
    const [lastRefreshedAt, setLastRefreshedAt] = useState("");
    const [refreshing, setRefreshing] = useState(false);


    const refreshPage = useCallback(() => {
        setRefreshing(true);
        router.refresh();
        setLastRefreshedAt(formatRefreshTime(new Date()));
        window.setTimeout(() => setRefreshing(false), 300);
    }, [router]);


    useEffect(() => {
        const timer = window.setTimeout(() => {
            setLastRefreshedAt(formatRefreshTime(new Date()));
        }, 0);

        const interval = window.setInterval(refreshPage, getRefreshIntervalMs());

        return () => {
            window.clearTimeout(timer);
            window.clearInterval(interval);
        };
    }, [refreshPage]);


    return (
        <div className="flex flex-col items-start md:items-end gap-2">
            <button
                type="button"
                onClick={refreshPage}
                disabled={refreshing}
                className="rounded-lg bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 disabled:text-slate-400 px-4 py-2 font-semibold transition"
            >
                {refreshing ? "Refreshing..." : label}
            </button>

            <p className="text-slate-400 text-sm">
                Last refreshed at: {lastRefreshedAt || "Loading..."}
            </p>
        </div>
    );
}
