"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createWebSocketClient, LiveEvent } from "../services/websocket";


type LiveUpdateBannerProps = {
    /**
     * Which WebSocket event types should trigger a page refresh.
     * Defaults to all event types.
     */
    listenTo?: string[];
};


/**
 * Client component that connects to the V.E.N.U.S WebSocket feed and
 * calls router.refresh() when a relevant live event arrives.
 *
 * The existing server-component data fetch acts as the authoritative
 * source; this banner simply re-triggers it when the backend publishes
 * new data, giving real-time feel without breaking the SSR fallback.
 *
 * If the WebSocket server is unavailable the banner shows a "disconnected"
 * indicator and the page continues to work via the existing polling refresh.
 */
export default function LiveUpdateBanner({
    listenTo,
}: LiveUpdateBannerProps) {
    const router = useRouter();
    const [connected, setConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<string | null>(null);
    const clientRef = useRef<ReturnType<typeof createWebSocketClient> | null>(
        null,
    );

    useEffect(() => {
        const client = createWebSocketClient(
            (event: LiveEvent) => {
                const shouldRefresh =
                    !listenTo || listenTo.includes(event.event);

                if (shouldRefresh) {
                    setLastEvent(event.event);
                    router.refresh();
                }
            },
            {
                onOpen: () => setConnected(true),
                onClose: () => setConnected(false),
            },
        );

        clientRef.current = client;
        client.connect();

        return () => {
            client.disconnect();
        };
    }, [router, listenTo]);

    if (!connected) {
        return (
            <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-400">
                <span className="inline-block h-2 w-2 rounded-full bg-slate-500" />
                Live updates: connecting…
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-600/40 bg-emerald-600/10 px-3 py-2 text-sm text-emerald-300">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            Live updates active
            {lastEvent ? (
                <span className="text-emerald-400/70">
                    · last: {lastEvent}
                </span>
            ) : null}
        </div>
    );
}
